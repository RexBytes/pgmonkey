import logging
import warnings
from psycopg_pool import AsyncConnectionPool
from psycopg import conninfo as psycopg_conninfo
from .base_connection import PostgresBaseConnection
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

warnings.filterwarnings('ignore', category=RuntimeWarning, module='psycopg_pool')


class PGAsyncPoolConnection(PostgresBaseConnection):
    def __init__(self, config, async_pool_settings=None, async_settings=None):
        self.config = config
        self.async_pool_settings = async_pool_settings or {}
        self.async_settings = async_settings or {}
        self.pool = None
        self._conn = None
        self._pool_conn_ctx = None

    @staticmethod
    def construct_conninfo(config):
        """Constructs a properly escaped connection info string from the config dictionary."""
        return psycopg_conninfo.make_conninfo(**config)

    async def connect(self):
        """Initialize the async connection pool."""
        if self.pool is None:
            conninfo = self.construct_conninfo(self.config)
            kwargs = dict(self.async_pool_settings)

            check_on_checkout = kwargs.pop('check_on_checkout', False)
            if check_on_checkout:
                async def _check(conn):
                    await conn.execute("SELECT 1")
                kwargs['check'] = _check

            if self.async_settings:
                async_settings = self.async_settings
                async def _configure(conn):
                    for setting, value in async_settings.items():
                        try:
                            await conn.execute(f"SET {setting} = %s", (str(value),))
                        except Exception as e:
                            logger.warning("Could not apply setting '%s': %s", setting, e)
                kwargs['configure'] = _configure

            self.pool = AsyncConnectionPool(conninfo=conninfo, **kwargs)
            await self.pool.open()

    async def test_connection(self):
        """Tests a single connection from the async pool."""
        if not self.pool:
            await self.connect()

        try:
            async with self.pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute('SELECT 1;')
                    result = await cur.fetchone()
                    logger.info("Async pool connection successful: %s", result)
        except Exception as e:
            logger.error("Test connection failed: %s", e)

    async def disconnect(self):
        if self.pool:
            await self.pool.close()
            self.pool = None

    async def commit(self):
        """Commits the current transaction on the acquired connection."""
        if self._conn:
            await self._conn.commit()

    async def rollback(self):
        """Rolls back the current transaction on the acquired connection."""
        if self._conn:
            await self._conn.rollback()

    @asynccontextmanager
    async def transaction(self):
        """Creates a transaction context on a pooled connection."""
        if self._conn:
            # Inside __aenter__/__aexit__ context - use the acquired connection
            async with self._conn.transaction() as tx:
                yield tx
        elif self.pool:
            # Standalone usage - acquire connection from pool
            async with self.pool.connection() as conn:
                async with conn.transaction() as tx:
                    yield tx
        else:
            raise Exception("No active pool available for transaction")

    @asynccontextmanager
    async def cursor(self):
        """Provides an async cursor from a pooled connection."""
        if self._conn:
            # Inside __aenter__/__aexit__ context - use the acquired connection
            async with self._conn.cursor() as cur:
                yield cur
        elif self.pool:
            # Standalone usage - acquire connection from pool
            async with self.pool.connection() as conn:
                async with conn.cursor() as cur:
                    yield cur
        else:
            raise Exception("No active pool available for cursor")

    async def __aenter__(self):
        if not self.pool:
            await self.connect()
        self._pool_conn_ctx = self.pool.connection()
        self._conn = await self._pool_conn_ctx.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        try:
            if exc_type:
                if self._conn:
                    await self._conn.rollback()
            else:
                if self._conn:
                    await self._conn.commit()
        finally:
            if self._pool_conn_ctx:
                await self._pool_conn_ctx.__aexit__(exc_type, exc_val, exc_tb)
            self._conn = None
            self._pool_conn_ctx = None
