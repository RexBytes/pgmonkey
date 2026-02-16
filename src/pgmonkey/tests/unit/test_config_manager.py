import pytest
import yaml
from pathlib import Path
from unittest.mock import patch, MagicMock
from pgmonkey.managers.pgconfig_manager import PGConfigManager


class TestPGConfigManagerInit:

    def test_templates_include_pg(self):
        manager = PGConfigManager()
        assert 'pg' in manager.templates
        assert manager.templates['pg'] == 'postgres.yaml'


class TestPGConfigManagerGetTemplate:

    def test_get_template_returns_dict(self):
        manager = PGConfigManager()
        template = manager.get_config_template('pg')
        assert isinstance(template, dict)
        assert 'connection_settings' in template

    def test_get_template_invalid_type_raises(self):
        manager = PGConfigManager()
        with pytest.raises(ValueError, match="Unsupported database type"):
            manager.get_config_template('mysql')


class TestPGConfigManagerGetTemplateText:

    def test_returns_string(self):
        manager = PGConfigManager()
        text = manager.get_config_template_text('pg')
        assert isinstance(text, str)
        assert 'connection_type' in text
        assert 'connection_settings' in text

    def test_preserves_comments(self):
        manager = PGConfigManager()
        text = manager.get_config_template_text('pg')
        assert '#' in text  # Comments should be preserved


class TestPGConfigManagerWriteTemplate:

    def test_writes_yaml_file(self, tmp_path):
        manager = PGConfigManager()
        filepath = tmp_path / "test_config.yaml"
        config = {'connection_type': 'normal'}
        manager.write_config_template(filepath, config)

        assert filepath.exists()
        with open(filepath) as f:
            loaded = yaml.safe_load(f)
        assert loaded == config

    def test_creates_parent_dirs(self, tmp_path):
        manager = PGConfigManager()
        filepath = tmp_path / "subdir" / "deep" / "config.yaml"
        config = {'connection_type': 'normal'}
        manager.write_config_template(filepath, config)
        assert filepath.exists()


class TestPGConfigManagerWriteTemplateText:

    def test_writes_text_file(self, tmp_path):
        manager = PGConfigManager()
        filepath = tmp_path / "test_config.yaml"
        text = "connection_type: 'normal'\n"
        manager.write_config_template_text(filepath, text)

        assert filepath.exists()
        assert filepath.read_text() == text


class TestPGConfigManagerTestConnection:

    @patch('pgmonkey.managers.pgconfig_manager.DatabaseConnectionTester')
    @patch('pgmonkey.managers.pgconfig_manager.asyncio')
    def test_calls_tester_with_type(self, mock_asyncio, mock_tester_cls, sample_config_file, capsys):
        mock_tester = MagicMock()
        mock_tester_cls.return_value = mock_tester

        manager = PGConfigManager()
        manager.test_connection(sample_config_file, 'pool')

        output = capsys.readouterr().out
        assert "postgresql" in output

        mock_asyncio.run.assert_called_once()
        call_args = mock_asyncio.run.call_args[0][0]
        # Verify the tester was constructed
        mock_tester_cls.assert_called_once()
