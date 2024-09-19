from pgmonkey.managers.pgconnection_manager import PGConnectionManager

class DatabaseConnectionTester:
    def __init__(self):
        self.pgconnection_manager = PGConnectionManager()

    async def test_postgresql_connection(self, config_file_path):
        try:
            # Retrieve the database connection; assume it's already prepared to be used as an async context manager
            connection = await self.pgconnection_manager.get_database_connection(config_file_path)

            connection.test_connection()

        except Exception as e:
            print(f"An error occurred while testing the connection: {e}")
