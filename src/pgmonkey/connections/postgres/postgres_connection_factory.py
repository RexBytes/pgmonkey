from pgmonkey.connections.postgres.normal_connection import PGNormalConnection
from pgmonkey.connections.postgres.pool_connection import PGPoolConnection
from pgmonkey.connections.postgres.async_connection import PGAsyncConnection
from pgmonkey.connections.postgres.async_pool_connection import PGAsyncPoolConnection


class PostgresConnectionFactory:
    def __init__(self, config):
        self.connection_type = config['postgresql']['connection_type']
        self.config = self.filter_config(config['postgresql']['connection_settings'])
        self.pool_settings = config['postgresql'].get('pool_settings', {})
        self.async_settings = config['postgresql'].get('async_settings', {})
        self.async_pool_settings = config['postgresql'].get('async_pool_settings', {})

    @staticmethod
    def filter_config(config):
        # List of valid psycopg connection parameters
        valid_keys = ['user', 'password', 'host', 'port', 'dbname', 'sslmode', 'sslcert', 'sslkey', 'sslrootcert',
                      'connect_timeout', 'application_name', 'keepalives', 'keepalives_idle', 'keepalives_interval',
                      'keepalives_count']
        # Filter the config dictionary to include only the valid keys
        return {key: config[key] for key in valid_keys if key in config}

    def get_connection(self):
        # print(self.config)
        connection_type = self.connection_type

        if connection_type == 'normal':
            # Only connection_settings are needed for a normal connection
            return PGNormalConnection(self.config)
        elif connection_type == 'pool':
            # Merge connection_settings with pool_settings
            return PGPoolConnection(self.config, self.pool_settings)
        elif connection_type == 'async':
            # Merge connection_settings with async_settings
            return PGAsyncConnection(self.config, post_connect_async_settings=self.async_settings)
        elif connection_type == 'async_pool':
            # Merge connection_settings with async_pool_settings
            return PGAsyncPoolConnection(config=self.config, pool_settings=self.async_pool_settings)
        else:
            raise ValueError(f"Unsupported connection type: {connection_type}")
