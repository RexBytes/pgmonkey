import pytest
from pgmonkey.managers.settings_manager import SettingsManager


class TestSettingsManagerInit:

    def test_loads_settings(self):
        manager = SettingsManager()
        assert manager.settings is not None
        assert isinstance(manager.settings, dict)

    def test_has_package_name(self):
        manager = SettingsManager()
        assert manager.package_name == 'pgmonkey'

    def test_settings_contain_app_package_name(self):
        manager = SettingsManager()
        assert 'appPackageName' in manager.settings


class TestSettingsManagerMissingFile:

    def test_missing_file_raises(self):
        with pytest.raises(FileNotFoundError):
            SettingsManager('nonexistent_file.yaml')
