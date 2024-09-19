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

    async def test_async_postgresql_connection(self, config_file_path):
        """Test an asynchronous PostgreSQL connection."""
        connection = await self.pgconnection_manager.get_database_connection(config_file_path)
        await connection.test_connection()
        print("Async connection test completed successfully.")
        await connection.disconnect()

    def test_sync_postgresql_connection(self, config_file_path):
        """Test a synchronous PostgreSQL connection."""
        connection = self.pgconnection_manager.get_database_connection(config_file_path)
        connection.test_connection()
        print("Sync connection test completed successfully.")
        connection.disconnect()

    async def test_postgresql_connection(self, config_file_path):
        """Determine if the connection is async or sync and run the correct test."""
        try:
            # Load the configuration to check connection type
            config = await self.load_config(config_file_path)
            connection_type = config['postgresql']['connection_type']

            # Test async or sync based on connection type
            if connection_type in ['async', 'async_pool']:
                await self.test_async_postgresql_connection(config_file_path)
            else:
                self.test_sync_postgresql_connection(config_file_path)

        except Exception as e:
            print(f"An error occurred while testing the connection: {e}")
