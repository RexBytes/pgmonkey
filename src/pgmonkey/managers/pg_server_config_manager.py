import yaml
from pgmonkey.serversettings.postgres_server_config_generator import PostgresServerConfigGenerator


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

    def _get_postgres_server_config(self, config_file_path):
        generator = PostgresServerConfigGenerator(config_file_path)
        generator.print_configurations()
