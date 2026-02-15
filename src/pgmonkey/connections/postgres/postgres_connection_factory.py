import logging
from pgmonkey.connections.postgres.normal_connection import PGNormalConnection
from pgmonkey.connections.postgres.pool_connection import PGPoolConnection
from pgmonkey.connections.postgres.async_connection import PGAsyncConnection
from pgmonkey.connections.postgres.async_pool_connection import PGAsyncPoolConnection

logger = logging.getLogger(__name__)


class PostgresConnectionFactory:

    VALID_CONNECTION_KEYS = [
        'user', 'password', 'host', 'port', 'dbname', 'sslmode',
        'sslcert', 'sslkey', 'sslrootcert', 'connect_timeout',
        'application_name', 'keepalives', 'keepalives_idle',
        'keepalives_interval', 'keepalives_count',
    ]

    def __init__(self, config, connection_type):
        self.connection_type = connection_type
        self.config = self._filter_config(config['postgresql']['connection_settings'])
        self.pool_settings = config['postgresql'].get('pool_settings', {}) or {}
        self.async_settings = config['postgresql'].get('async_settings', {}) or {}
        self.async_pool_settings = config['postgresql'].get('async_pool_settings', {}) or {}
        self._validate_pool_settings()

    def _filter_config(self, config):
        """Filter the config dictionary to include only valid psycopg connection parameters."""
        unknown_keys = set(config.keys()) - set(self.VALID_CONNECTION_KEYS)
        if unknown_keys:
            logger.warning(
                "Unknown connection settings ignored: %s. "
                "Valid keys: %s",
                ', '.join(sorted(unknown_keys)),
                ', '.join(self.VALID_CONNECTION_KEYS),
            )
        return {key: config[key] for key in self.VALID_CONNECTION_KEYS if key in config and config[key] is not None}

    def _validate_pool_settings(self):
        """Validate pool configuration ranges."""
        for label, settings in [
            ('pool_settings', self.pool_settings),
            ('async_pool_settings', self.async_pool_settings),
        ]:
            if not settings:
                continue
            min_size = settings.get('min_size')
            max_size = settings.get('max_size')
            if min_size is not None and max_size is not None and min_size > max_size:
                raise ValueError(
                    f"{label}: min_size ({min_size}) cannot be greater than max_size ({max_size})"
                )

    def get_connection(self):
        if self.connection_type == 'normal':
            connection = PGNormalConnection(self.config)
        elif self.connection_type == 'pool':
            connection = PGPoolConnection(self.config, self.pool_settings)
        elif self.connection_type == 'async':
            connection = PGAsyncConnection(self.config, self.async_settings)
        elif self.connection_type == 'async_pool':
            connection = PGAsyncPoolConnection(self.config, self.async_pool_settings, self.async_settings)
        else:
            raise ValueError(f"Unsupported connection type: {self.connection_type}")

        connection.connection_type = self.connection_type
        return connection
