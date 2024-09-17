import yaml
from pgmonkey.connections.postgres.postgres_connection_factory import PostgresConnectionFactory


class PGConnectionManager:
    def __init__(self):
        pass

    async def get_database_connection(self, config_file_path):
        """Establish a PostgreSQL database connection using a configuration file."""
        with open(config_file_path, 'r') as f:
            config_data_dictionary = yaml.safe_load(f)

        return await self.get_postgresql_connection(config_data_dictionary)

    async def get_postgresql_connection(self, config_data_dictionary):
        """Create and return PostgreSQL connection based on the configuration."""
        factory = PostgresConnectionFactory(config_data_dictionary)
        connection = factory.get_connection()

        # Determine whether to use async or sync connect
        connection_type = config_data_dictionary['postgresql']['connection_type']
        if connection_type in ['normal', 'pool']:
            connection.connect()  # Synchronous connection
        elif connection_type in ['async', 'async_pool']:
            await connection.connect()  # Asynchronous connection
        else:
            raise ValueError(f"Unsupported connection type: {connection_type}")

        return connection


