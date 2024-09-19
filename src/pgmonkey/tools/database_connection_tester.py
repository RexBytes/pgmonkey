from pgmonkey.managers.pgconnection_manager import PGConnectionManager
import yaml

class DatabaseConnectionTester:
    def __init__(self):
        self.pgconnection_manager = PGConnectionManager()

    async def load_config(self, config_file_path):
        # Load the YAML configuration from the provided file path
        with open(config_file_path, 'r') as file:
            config = yaml.safe_load(file)
        return config


    async def test_postgresql_connection(self, config_file_path):
        try:
            # Load the configuration from the YAML file
            config = await self.load_config(config_file_path)

            # Retrieve the connection type from the YAML config
            connection_type = config['postgresql']['connection_type']

            # Retrieve the database connection using the config file
            connection = await self.pgconnection_manager.get_database_connection(config_file_path)

            # Check if the connection type is async or sync based on the config file
            if connection_type in ['async', 'async_pool']:
                # Asynchronous connections, await the test_connection method
                await connection.test_connection()
            else:
                # Synchronous connections, just call test_connection
                connection.test_connection()

            print("Connection test completed successfully.")

        except Exception as e:
            print(f"An error occurred while testing the connection: {e}")
