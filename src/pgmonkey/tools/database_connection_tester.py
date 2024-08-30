from pgmonkey.managers.pgconnection_manager import PGConnectionManager
import yaml


class DatabaseConnectionTester:
    def __init__(self):
        self.pgconnection_manager = PGConnectionManager()

    async def test_postgresql_connection(self, config_file_path):
        try:
            # Retrieve the database connection; assume it's already prepared to be used as an async context manager
            connection = await self.pgconnection_manager.get_database_connection(config_file_path)

            # Read the configuration file to determine the connection type
            with open(config_file_path, 'r') as config_file:
                config = yaml.safe_load(config_file)

            if config['postgresql']['connection_type'] in ['normal', 'pool']:
                with connection as sync_connection:
                    sync_connection.test_connection()
            elif config['postgresql']['connection_type'] in ['async', 'async_pool']:
                async with connection as async_connection:
                    await async_connection.test_connection()

        except Exception as e:
            print(f"An error occurred while testing the connection: {e}")
