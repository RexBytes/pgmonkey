import yaml
from pgmonkey.serversettings.postgres_server_config_generator import PostgresServerConfigGenerator
from pgmonkey.managers.pgconnection_manager import PGConnectionManager


class PGServerConfigManager:
    def __init__(self):
        pass

    def get_server_config(self, config_file_path):
        """Detect the database type and generate server configuration."""
        with open(config_file_path, 'r') as f:
            config_data_dictionary = yaml.safe_load(f)
        database_type = next(iter(config_data_dictionary))

        if database_type == 'postgresql':
            self._get_postgres_server_config(config_file_path)
        else:
            raise ValueError(f"Unsupported database type: {database_type}")

    def audit_server_config(self, config_file_path):
        """Connect to the live server and audit settings against recommendations."""
        with open(config_file_path, 'r') as f:
            config_data_dictionary = yaml.safe_load(f)
        database_type = next(iter(config_data_dictionary))

        if database_type == 'postgresql':
            self._audit_postgres_server_config(config_file_path, config_data_dictionary)
        else:
            raise ValueError(f"Unsupported database type: {database_type}")

    def _get_postgres_server_config(self, config_file_path):
        generator = PostgresServerConfigGenerator(config_file_path)
        generator.print_configurations()

    def _audit_postgres_server_config(self, config_file_path, config_data_dictionary):
        generator = PostgresServerConfigGenerator(config_file_path)
        if not generator.config:
            return

        connection_manager = PGConnectionManager()
        connection = None
        try:
            connection = connection_manager.get_database_connection_from_dict(
                config_data_dictionary, connection_type='normal'
            )
            generator.print_configurations_with_audit(connection)
        except Exception as e:
            print(f"\nCould not connect to server for audit: {e}")
            print("Falling back to recommendations only.\n")
            generator.print_configurations()
        finally:
            if connection:
                try:
                    connection.disconnect()
                except Exception:
                    pass
