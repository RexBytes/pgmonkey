import yaml
from pgmonkey.tools.connection_code_generator import ConnectionCodeGenerator
from .settings_manager import SettingsManager
from pgmonkey.common.utils.pathutils import PathUtils


class PGCodegenManager:
    def __init__(self):
        self.path_utils = PathUtils()
        self.settings_manager = SettingsManager()
        self.connection_code_generator = ConnectionCodeGenerator()

    def generate_connection_code(self, config_file_path, connection_type=None, library='pgmonkey'):
        """Generate Python connection code using the configuration file.

        Args:
            config_file_path: Path to the YAML configuration file.
            connection_type: Optional connection type override.
            library: Target library - 'pgmonkey' (default) or 'psycopg'.
        """
        with open(config_file_path, 'r') as file:
            config_data = yaml.safe_load(file)
        database_type = next(iter(config_data))

        print(f"{database_type} database config file has been detected...")

        if database_type == 'postgresql':
            self.connection_code_generator.generate_connection_code(
                config_file_path, connection_type, library=library,
            )
        else:
            print(f"Unsupported database type: {database_type}")
