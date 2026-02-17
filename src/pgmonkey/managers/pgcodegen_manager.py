import yaml
from pgmonkey.tools.connection_code_generator import ConnectionCodeGenerator
from .settings_manager import SettingsManager
from pgmonkey.common.utils.pathutils import PathUtils
from pgmonkey.common.utils.configutils import normalize_config


class PGCodegenManager:
    def __init__(self):
        self.path_utils = PathUtils()
        self.settings_manager = SettingsManager()
        self.connection_code_generator = ConnectionCodeGenerator()

    def generate_connection_code(self, config_file_path, connection_type=None,
                                 library='pgmonkey', resolve_env=False):
        """Generate Python connection code using the configuration file.

        Args:
            config_file_path: Path to the YAML configuration file.
            connection_type: Optional connection type override.
            library: Target library - 'pgmonkey' (default) or 'psycopg'.
            resolve_env: Accepted for CLI consistency but not used here -
                generated code templates are static examples.
        """
        with open(config_file_path, 'r') as file:
            config_data = yaml.safe_load(file)
        normalize_config(config_data)  # validates format, warns if old style

        print("postgresql database config file has been detected...")

        self.connection_code_generator.generate_connection_code(
            config_file_path, connection_type, library=library,
        )
