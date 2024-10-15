import yaml
from pgmonkey.connections.postgres.postgres_connection_factory import PostgresConnectionFactory


class PGConnectionManager:
    def __init__(self):
        pass

    def get_database_connection(self, config_file_path):
        """Establish a PostgreSQL database connection using a configuration file."""
        with open(config_file_path, 'r') as f:
            config_data_dictionary = yaml.safe_load(f)

        return self._get_connection(config_data_dictionary)

    def get_database_connection_from_dict(self, config_data_dictionary):
        """Establish a PostgreSQL database connection using an in-memory configuration dictionary."""
        return self._get_connection(config_data_dictionary)

    def _get_connection(self, config_data_dictionary):
        """Helper function to establish a connection using a dictionary."""
        connection_type = config_data_dictionary['postgresql']['connection_type']

        if connection_type in ['normal', 'pool']:
            return self.get_postgresql_connection_sync(config_data_dictionary)
        elif connection_type in ['async', 'async_pool']:
            return self.get_postgresql_connection_async(config_data_dictionary)
        else:
            raise ValueError(f"Unsupported connection type: {connection_type}")

    def get_postgresql_connection_sync(self, config_data_dictionary):
        """Create and return synchronous PostgreSQL connection based on the configuration."""
        factory = PostgresConnectionFactory(config_data_dictionary)
        connection = factory.get_connection()
        connection.connect()  # Synchronous connection
        return connection

    async def get_postgresql_connection_async(self, config_data_dictionary):
        """Create and return asynchronous PostgreSQL connection based on the configuration."""
        factory = PostgresConnectionFactory(config_data_dictionary)
        connection = factory.get_connection()
        await connection.connect()  # Asynchronous connection
        return connection



