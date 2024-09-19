import yaml
from pgmonkey.tools.connection_code_generator import ConnectionCodeGenerator
from .settings_manager import SettingsManager
from pgmonkey.common.utils.pathutils import PathUtils

class PGCodegenManager:
    def __init__(self):
        self.path_utils = PathUtils()
        self.settings_manager = SettingsManager()
        self.connection_code_generator = ConnectionCodeGenerator()

    def load_config(self, config_file_path):
        """Load a YAML configuration file."""
        with open(config_file_path, 'r') as file:
            config_data = yaml.safe_load(file)
        return config_data

    def generate_connection_code(self, config_file_path):
        """Generate Python connection code using the configuration file."""
        # Load the YAML configuration
        config_data = self.load_config(config_file_path)
        database_type = next(iter(config_data))

        print(f"{database_type} database config file has been detected...")

        if database_type == 'postgresql':
            # Call the code generator to create Python code
            self.connection_code_generator.generate_connection_code(config_file_path)
        else:
            print(f"Unsupported database type: {database_type}")
