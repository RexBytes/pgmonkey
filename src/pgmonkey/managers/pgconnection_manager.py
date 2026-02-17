import yaml
import json
import hashlib
import atexit
import asyncio
import logging
import threading
import warnings
from pgmonkey.connections.postgres.postgres_connection_factory import PostgresConnectionFactory
from pgmonkey.common.utils.configutils import normalize_config
from pgmonkey.common.utils.envutils import resolve_env_vars

logger = logging.getLogger(__name__)

VALID_CONNECTION_TYPES = ('normal', 'pool', 'async', 'async_pool')


class PGConnectionManager:
    """Manages PostgreSQL database connections with built-in caching and lifecycle management.

    Connections are automatically cached by config content. Repeated calls with the same
    config return the existing connection/pool. Cached connections are cleaned up at
    process exit via an atexit handler.
    """

    def __init__(self):
        self._cache = {}
        self._cache_lock = threading.Lock()
        self._atexit_registered = False

    # -- Cache key computation --------------------------------------------------

    @staticmethod
    def _config_hash(config_data_dictionary):
        """Compute a stable hash of the config dictionary for cache keying."""
        config_str = json.dumps(config_data_dictionary, sort_keys=True, default=str)
        return hashlib.sha256(config_str.encode()).hexdigest()

    # -- atexit hook ------------------------------------------------------------

    def _register_atexit(self):
        """Register the atexit cleanup handler (once per manager instance)."""
        if not self._atexit_registered:
            atexit.register(self._cleanup_at_exit)
            self._atexit_registered = True

    def _cleanup_at_exit(self):
        """Best-effort cleanup of all cached connections at process exit."""
        with self._cache_lock:
            async_connections = []
            for connection in self._cache.values():
                try:
                    if asyncio.iscoroutinefunction(connection.disconnect):
                        async_connections.append(connection)
                    else:
                        connection.disconnect()
                except Exception:
                    pass

            if async_connections:
                self._close_async_connections_sync(async_connections, warn=True)

            self._cache.clear()

    @staticmethod
    def _close_async_connections_sync(connections, warn=False):
        """Best-effort synchronous close of async connections using a temporary event loop."""
        async def _close_all():
            for conn in connections:
                try:
                    await conn.disconnect()
                except Exception:
                    pass

        try:
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(_close_all())
            finally:
                loop.close()
        except Exception:
            if warn:
                warnings.warn(
                    "pgmonkey: Could not cleanly close async cached connections at exit. "
                    "Call disconnect() or use context managers for proper cleanup.",
                    ResourceWarning,
                    stacklevel=2
                )

    # -- Public connection API --------------------------------------------------

    def get_database_connection(self, config_file_path, connection_type=None,
                                force_reload=False, resolve_env=False,
                                allow_sensitive_defaults=False):
        """Establish a PostgreSQL database connection using a configuration file.

        Connections are cached by config content. Repeated calls with the same
        (unchanged) config return the existing connection/pool.

        Args:
            config_file_path: Path to the YAML configuration file.
            connection_type: Optional override for connection type.
                If not provided, uses the value from the config file.
                Options: 'normal', 'pool', 'async', 'async_pool'
            force_reload: If True, close the existing cached connection and
                create a fresh one.
            resolve_env: If True, resolve ``${VAR}`` patterns and
                ``from_env``/``from_file`` references in the config before
                connecting.
            allow_sensitive_defaults: If True (and *resolve_env* is True),
                ``${VAR:-default}`` is permitted even for sensitive keys
                like ``password``.  Default is False for safety.

        Returns:
            A connection object (sync types) or a coroutine (async types - must be awaited).
        """
        with open(config_file_path, 'r') as f:
            config_data_dictionary = yaml.safe_load(f)

        config_data_dictionary = normalize_config(config_data_dictionary)
        if resolve_env:
            config_data_dictionary = resolve_env_vars(
                config_data_dictionary,
                allow_sensitive_defaults=allow_sensitive_defaults,
            )
        return self._get_connection(config_data_dictionary, connection_type, force_reload=force_reload)

    def get_database_connection_from_dict(self, config_data_dictionary, connection_type=None,
                                          force_reload=False, resolve_env=False,
                                          allow_sensitive_defaults=False):
        """Establish a PostgreSQL database connection using an in-memory configuration dictionary.

        Connections are cached by config content. Repeated calls with the same
        config return the existing connection/pool.

        Args:
            config_data_dictionary: Configuration dictionary.
            connection_type: Optional override for connection type.
                If not provided, uses the value from the config dictionary.
                Options: 'normal', 'pool', 'async', 'async_pool'
            force_reload: If True, close the existing cached connection and
                create a fresh one.
            resolve_env: If True, resolve ``${VAR}`` patterns and
                ``from_env``/``from_file`` references in the config before
                connecting.
            allow_sensitive_defaults: If True (and *resolve_env* is True),
                ``${VAR:-default}`` is permitted even for sensitive keys
                like ``password``.  Default is False for safety.

        Returns:
            A connection object (sync types) or a coroutine (async types - must be awaited).
        """
        config_data_dictionary = normalize_config(config_data_dictionary)
        if resolve_env:
            config_data_dictionary = resolve_env_vars(
                config_data_dictionary,
                allow_sensitive_defaults=allow_sensitive_defaults,
            )
        return self._get_connection(config_data_dictionary, connection_type, force_reload=force_reload)

    # -- Internal routing -------------------------------------------------------

    def _get_connection(self, config_data_dictionary, connection_type=None, force_reload=False):
        """Route to sync or async connection creation, with caching."""
        resolved_type = connection_type or config_data_dictionary.get('connection_type', 'normal')

        if resolved_type not in VALID_CONNECTION_TYPES:
            raise ValueError(
                f"Unsupported connection type: '{resolved_type}'. "
                f"Valid types: {', '.join(VALID_CONNECTION_TYPES)}"
            )

        is_async = resolved_type in ('async', 'async_pool')

        cache_key = self._config_hash(config_data_dictionary) + ':' + resolved_type
        old_connection = None

        with self._cache_lock:
            if cache_key in self._cache:
                if not force_reload:
                    cached = self._cache[cache_key]
                    if is_async:
                        return self._wrap_async(cached)
                    return cached
                else:
                    old_connection = self._cache.pop(cache_key)
        self._register_atexit()

        if is_async:
            return self._create_async_connection(
                config_data_dictionary, resolved_type, cache_key,
                old_connection, force_reload,
            )
        else:
            # Disconnect the old cached connection if force_reload
            if old_connection:
                try:
                    old_connection.disconnect()
                except Exception:
                    pass

            connection = self._get_postgresql_connection_sync(config_data_dictionary, resolved_type)

            # Double-check: another thread may have cached a connection while
            # we were creating ours (race between concurrent cache misses).
            with self._cache_lock:
                if cache_key in self._cache and not force_reload:
                    # Another thread beat us - discard ours, use theirs.
                    try:
                        connection.disconnect()
                    except Exception:
                        pass
                    return self._cache[cache_key]
                self._cache[cache_key] = connection
            return connection

    @staticmethod
    async def _wrap_async(connection):
        """Wrap a cached connection in a coroutine so the caller can still await it."""
        return connection

    async def _create_async_connection(self, config_data_dictionary, connection_type,
                                       cache_key, old_connection=None, force_reload=False):
        """Create an async connection, optionally disconnecting the old one and caching the new one."""
        if old_connection:
            try:
                if asyncio.iscoroutinefunction(old_connection.disconnect):
                    await old_connection.disconnect()
                else:
                    old_connection.disconnect()
            except Exception:
                pass

        connection = await self._get_postgresql_connection_async(config_data_dictionary, connection_type)

        # Double-check: another coroutine may have cached a connection while
        # we were creating ours (race between concurrent cache misses).
        discard = None
        with self._cache_lock:
            if cache_key in self._cache and not force_reload:
                discard = connection
                connection = self._cache[cache_key]
            else:
                self._cache[cache_key] = connection

        if discard is not None:
            try:
                await discard.disconnect()
            except Exception:
                pass

        return connection

    def _get_postgresql_connection_sync(self, config_data_dictionary, connection_type):
        """Create and return synchronous PostgreSQL connection based on the configuration."""
        factory = PostgresConnectionFactory(config_data_dictionary, connection_type)
        connection = factory.get_connection()
        connection.connect()
        return connection

    async def _get_postgresql_connection_async(self, config_data_dictionary, connection_type):
        """Create and return asynchronous PostgreSQL connection based on the configuration."""
        factory = PostgresConnectionFactory(config_data_dictionary, connection_type)
        connection = factory.get_connection()
        await connection.connect()
        return connection

    # -- Cache management -------------------------------------------------------

    @property
    def cache_info(self):
        """Return information about the current cache state.

        Returns:
            dict with 'size' (number of cached connections) and 'connection_types'
            mapping truncated cache keys to their connection type strings.
        """
        with self._cache_lock:
            return {
                'size': len(self._cache),
                'connection_types': {
                    key[:12]: getattr(conn, 'connection_type', 'unknown')
                    for key, conn in self._cache.items()
                },
            }

    def clear_cache(self):
        """Close all cached connections and clear the cache.

        Sync connections are closed immediately. Async connections are closed
        via a temporary event loop. If you are already inside an async context,
        use clear_cache_async() instead.
        """
        with self._cache_lock:
            async_connections = []
            for connection in self._cache.values():
                try:
                    if asyncio.iscoroutinefunction(connection.disconnect):
                        async_connections.append(connection)
                    else:
                        connection.disconnect()
                except Exception:
                    pass

            if async_connections:
                self._close_async_connections_sync(async_connections, warn=True)

            self._cache.clear()

    async def clear_cache_async(self):
        """Close all cached connections and clear the cache (async version).

        Use this when calling from an async context (e.g. inside an event loop).
        For sync contexts, use clear_cache() instead.
        """
        with self._cache_lock:
            for connection in self._cache.values():
                try:
                    if asyncio.iscoroutinefunction(connection.disconnect):
                        await connection.disconnect()
                    else:
                        connection.disconnect()
                except Exception:
                    pass
            self._cache.clear()
