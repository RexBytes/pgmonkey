from pgmonkey.managers.pgconnection_manager import PGConnectionManager
from pgmonkey.common.utils.configutils import normalize_config


class DatabaseConnectionTester:
    def __init__(self):
        self.pgconnection_manager = PGConnectionManager()

    async def test_async_postgresql_connection(self, config_file_path, connection_type):
        """Test an asynchronous PostgreSQL connection."""
        connection = await self.pgconnection_manager.get_database_connection(config_file_path, connection_type)
        await connection.test_connection()
        print("Async connection test completed successfully.")
        await connection.disconnect()

    def test_sync_postgresql_connection(self, config_file_path, connection_type):
        """Test a synchronous PostgreSQL connection."""
        connection = self.pgconnection_manager.get_database_connection(config_file_path, connection_type)
        connection.test_connection()
        print("Sync connection test completed successfully.")
        connection.disconnect()

    async def test_postgresql_connection(self, config_file_path, connection_type=None):
        """Test a PostgreSQL connection of the given type.

        Args:
            config_file_path: Path to the YAML configuration file.
            connection_type: Connection type to test. If None, uses the config file default.
        """
        try:
            # Determine effective connection type
            if connection_type is None:
                import yaml
                with open(config_file_path, 'r') as file:
                    config = yaml.safe_load(file)
                config = normalize_config(config)
                connection_type = config.get('connection_type', 'normal')

            if connection_type in ('async', 'async_pool'):
                await self.test_async_postgresql_connection(config_file_path, connection_type)
            else:
                self.test_sync_postgresql_connection(config_file_path, connection_type)

        except Exception as e:
            print(f"An error occurred while testing the connection: {e}")
