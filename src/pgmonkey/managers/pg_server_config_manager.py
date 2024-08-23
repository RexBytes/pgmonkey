import yaml
from pgmonkey.serversettings.postgres_server_config_generator import PostgresServerConfigGenerator

class PGServerConfigManager:
    def __init__(self):
        pass

    def get_server_config(self, config_file_path):
        # Need to detect the database type from the config file.
        with open(config_file_path, 'r') as f:
            config_data_dictionary = yaml.safe_load(f)
        database_type = next(iter(config_data_dictionary))

        if database_type == 'postgresql':
            #print("postgres detected")
            self.get_postgres_server_config(config_file_path)
        else:
            raise ValueError(f"Unsupported database type: {database_type}")

    def get_postgres_server_config(self, config_file_path):
        postgresconfiggenerator = PostgresServerConfigGenerator(config_file_path)
        postgresconfiggenerator.generate_pg_hba_entry()
        postgresconfiggenerator.generate_pg_hba_entry()
        postgresconfiggenerator.print_configurations()
