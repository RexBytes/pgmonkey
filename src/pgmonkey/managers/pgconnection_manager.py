import yaml
from pgmonkey.connections.postgres.postgres_connection_factory import PostgresConnectionFactory

VALID_CONNECTION_TYPES = ('normal', 'pool', 'async', 'async_pool')


class PGConnectionManager:
    def __init__(self):
        pass

    def get_database_connection(self, config_file_path, connection_type=None):
        """Establish a PostgreSQL database connection using a configuration file.

        Args:
            config_file_path: Path to the YAML configuration file.
            connection_type: Optional override for connection type.
                If not provided, uses the value from the config file.
                Options: 'normal', 'pool', 'async', 'async_pool'
        """
        with open(config_file_path, 'r') as f:
            config_data_dictionary = yaml.safe_load(f)

        return self._get_connection(config_data_dictionary, connection_type)

    def get_database_connection_from_dict(self, config_data_dictionary, connection_type=None):
        """Establish a PostgreSQL database connection using an in-memory configuration dictionary.

        Args:
            config_data_dictionary: Configuration dictionary.
            connection_type: Optional override for connection type.
                If not provided, uses the value from the config dictionary.
                Options: 'normal', 'pool', 'async', 'async_pool'
        """
        return self._get_connection(config_data_dictionary, connection_type)

    def _get_connection(self, config_data_dictionary, connection_type=None):
        """Helper function to establish a connection using a dictionary."""
        resolved_type = connection_type or config_data_dictionary['postgresql'].get('connection_type', 'normal')

        if resolved_type not in VALID_CONNECTION_TYPES:
            raise ValueError(
                f"Unsupported connection type: '{resolved_type}'. "
                f"Valid types: {', '.join(VALID_CONNECTION_TYPES)}"
            )

        if resolved_type in ('normal', 'pool'):
            return self._get_postgresql_connection_sync(config_data_dictionary, resolved_type)
        else:
            return self._get_postgresql_connection_async(config_data_dictionary, resolved_type)

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
