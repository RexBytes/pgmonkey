from pgmonkey.managers.pgconnection_manager import PGConnectionManager
from pgmonkey.common.utils.configutils import normalize_config


class DatabaseConnectionTester:
    def __init__(self):
        self.pgconnection_manager = PGConnectionManager()

    async def test_async_postgresql_connection(self, config_file_path, connection_type,
                                               resolve_env=False,
                                               allow_sensitive_defaults=False):
        """Test an asynchronous PostgreSQL connection."""
        connection = await self.pgconnection_manager.get_database_connection(
            config_file_path, connection_type, resolve_env=resolve_env,
            allow_sensitive_defaults=allow_sensitive_defaults,
        )
        await connection.test_connection()
        print("Async connection test completed successfully.")
        await connection.disconnect()

    def test_sync_postgresql_connection(self, config_file_path, connection_type,
                                        resolve_env=False,
                                        allow_sensitive_defaults=False):
        """Test a synchronous PostgreSQL connection."""
        connection = self.pgconnection_manager.get_database_connection(
            config_file_path, connection_type, resolve_env=resolve_env,
            allow_sensitive_defaults=allow_sensitive_defaults,
        )
        connection.test_connection()
        print("Sync connection test completed successfully.")
        connection.disconnect()

    async def test_postgresql_connection(self, config_file_path, connection_type=None,
                                         resolve_env=False,
                                         allow_sensitive_defaults=False):
        """Test a PostgreSQL connection of the given type.

        Args:
            config_file_path: Path to the YAML configuration file.
            connection_type: Connection type to test. If None, uses the config file default.
            resolve_env: If True, resolve environment variable references in the config.
            allow_sensitive_defaults: If True, allow ${VAR:-default} for sensitive keys.
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
                await self.test_async_postgresql_connection(
                    config_file_path, connection_type, resolve_env=resolve_env,
                    allow_sensitive_defaults=allow_sensitive_defaults,
                )
            else:
                self.test_sync_postgresql_connection(
                    config_file_path, connection_type, resolve_env=resolve_env,
                    allow_sensitive_defaults=allow_sensitive_defaults,
                )

        except Exception as e:
            print(f"An error occurred while testing the connection: {e}")
