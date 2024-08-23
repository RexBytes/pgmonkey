import yaml
from pathlib import Path


class SettingsManager:
    def __init__(self, settings_filename='app_settings.yaml'):
        # Path to the default settings file, it's in the package structure.
        self.settings_file = Path(__file__).resolve().parents[1] / 'settings' / settings_filename
        # Load settings from the default settings file from package structure
        self.settings = self.load_initial_settings()
        # Use the package name from the settings
        self.package_name = self.settings.get('appPackageName')

    def load_initial_settings(self):
        """Load initial settings from app_settings.yaml located in the same directory as this class."""
        if not self.settings_file.exists():
            raise FileNotFoundError(f"Could not find the settings file {self.settings_file}")
        with open(self.settings_file, "r") as file:
            return yaml.safe_load(file)

    def print_hello_world(self):
        print(f"{self.package_name} says \"Hello World\" - This is a place holder for the settings cli class.")
