from pathlib import Path
import yaml
from importlib import resources
from pgmonkey.tools.database_connection_tester import DatabaseConnectionTester
import asyncio
from .settings_manager import SettingsManager
from pgmonkey.common.utils.pathutils import PathUtils


class PGConfigManager:
    def __init__(self):
        self.path_utils = PathUtils()
        self.settings_manager = SettingsManager()
        self.templates = {'pg': 'postgres.yaml'}

    def load_template(self, template_filename):
        """Load a YAML configuration template from a file within the package."""
        with resources.files(f"{self.settings_manager.settings['appPackageName']}.common.templates").joinpath(
                template_filename) as path, \
                resources.as_file(path) as config_file, \
                open(config_file, 'r') as file:
            return yaml.safe_load(file)

    def get_config_template(self, database_type):
        """Retrieve the configuration template based on the database type."""
        if database_type in self.templates:
            return self.load_template(self.templates[database_type])
        else:
            raise ValueError(f'Unsupported database type. Supported types are: {", ".join(self.templates.keys())}')

    def get_config_template_text(self, database_type):
        """Retrieve the configuration template as raw text based on the database type."""
        if database_type in self.templates:
            template_filename = self.templates[database_type]
            package_path = f"{self.settings_manager.settings['appPackageName']}.common.templates"
            with resources.files(package_path).joinpath(template_filename) as path, \
                    resources.as_file(path) as config_file:
                with open(config_file, 'r') as file:
                    return file.read()
        else:
            raise ValueError(f'Unsupported database type. Supported types are: {", ".join(self.templates.keys())}')

    def write_config_template(self, file_path, config_data):
        """Write the configuration template data to a file."""
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w') as f:
            yaml.dump(config_data, f, sort_keys=False, default_flow_style=False, width=1000)
        print(f'New configuration template created: {file_path}')

    def write_config_template_text(self, file_path, config_text):
        """Write the configuration template text to a file, preserving all formatting."""
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w') as f:
            f.write(config_text)
        print(f'New configuration template created: {file_path}')

    def test_connection(self, config_file_path):
        """Test database connection using a configuration file."""

        # Step 1: Determine the database type.
        with open(config_file_path, 'r') as config_file:
            config_data = yaml.safe_load(config_file)
        database_type = next(iter(config_data))
        print(f"{database_type} database config file has been detected...")

        # Step 2:
        integration_tester = DatabaseConnectionTester()

        if database_type == 'postgresql':
            asyncio.run(integration_tester.test_postgresql_connection(config_file_path))
        else:
            print(f"Unsupported database type: {database_type}")
