import pytest
import yaml
from unittest.mock import patch, MagicMock
from pgmonkey.tools.csv_data_exporter import CSVDataExporter
from pgmonkey.common.exceptions import ConfigFileCreatedError


class TestCSVDataExporterInit:

    def test_schema_table_split(self, tmp_path):
        """table_name with a dot should split into schema and table."""
        config_file = tmp_path / "conn.yaml"
        config_file.write_text(yaml.dump({
            'connection_type': 'normal',
            'connection_settings': {'host': 'localhost', 'dbname': 'test'},
        }))
        export_config = tmp_path / "export.yaml"
        export_config.write_text(yaml.dump({
            'delimiter': ',', 'quotechar': '"', 'encoding': 'utf-8',
        }))

        exporter = CSVDataExporter(
            str(config_file), "myschema.mytable",
            csv_file=str(tmp_path / "out.csv"),
            export_config_file=str(export_config),
        )
        assert exporter.schema_name == "myschema"
        assert exporter.table_name == "mytable"

    def test_default_schema_is_public(self, tmp_path):
        """table_name without a dot should default schema to 'public'."""
        config_file = tmp_path / "conn.yaml"
        config_file.write_text(yaml.dump({
            'connection_type': 'normal',
            'connection_settings': {'host': 'localhost', 'dbname': 'test'},
        }))
        export_config = tmp_path / "export.yaml"
        export_config.write_text(yaml.dump({
            'delimiter': ',', 'quotechar': '"', 'encoding': 'utf-8',
        }))

        exporter = CSVDataExporter(
            str(config_file), "mytable",
            csv_file=str(tmp_path / "out.csv"),
            export_config_file=str(export_config),
        )
        assert exporter.schema_name == "public"
        assert exporter.table_name == "mytable"

    def test_multi_dot_table_name(self, tmp_path):
        """table_name with multiple dots should only split on the first dot."""
        config_file = tmp_path / "conn.yaml"
        config_file.write_text(yaml.dump({
            'connection_type': 'normal',
            'connection_settings': {'host': 'localhost', 'dbname': 'test'},
        }))
        export_config = tmp_path / "export.yaml"
        export_config.write_text(yaml.dump({
            'delimiter': ',', 'quotechar': '"', 'encoding': 'utf-8',
        }))

        exporter = CSVDataExporter(
            str(config_file), "catalog.schema.table",
            csv_file=str(tmp_path / "out.csv"),
            export_config_file=str(export_config),
        )
        assert exporter.schema_name == "catalog"
        assert exporter.table_name == "schema.table"

    def test_tab_delimiter_unescaped(self, tmp_path):
        """Tab delimiter specified as literal backslash-t should be converted to real tab."""
        config_file = tmp_path / "conn.yaml"
        config_file.write_text(yaml.dump({
            'connection_type': 'normal',
            'connection_settings': {'host': 'localhost', 'dbname': 'test'},
        }))
        export_config = tmp_path / "export.yaml"
        export_config.write_text(yaml.dump({
            'delimiter': r'\t', 'quotechar': '"', 'encoding': 'utf-8',
        }))

        exporter = CSVDataExporter(
            str(config_file), "mytable",
            csv_file=str(tmp_path / "out.csv"),
            export_config_file=str(export_config),
        )
        assert exporter.delimiter == '\t'


class TestExportConfigCreation:

    @patch('pgmonkey.tools.csv_data_exporter.PGConnectionManager')
    def test_config_file_created_when_missing(self, mock_mgr_cls, tmp_path):
        """When no export config exists, it should be auto-created and raise ConfigFileCreatedError."""
        config_file = tmp_path / "conn.yaml"
        config_file.write_text(yaml.dump({
            'connection_type': 'normal',
            'connection_settings': {'host': 'localhost', 'dbname': 'test'},
        }))

        # Mock the connection manager to return a mock connection
        mock_mgr = MagicMock()
        mock_mgr_cls.return_value = mock_mgr
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = ('UTF8',)
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_mgr.get_database_connection.return_value = mock_conn

        csv_file = str(tmp_path / "out.csv")
        with pytest.raises(ConfigFileCreatedError):
            CSVDataExporter(str(config_file), "mytable", csv_file=csv_file)

        # The export config file should have been created
        export_config = tmp_path / "out.yaml"
        assert export_config.exists()


class TestResolveConnectionType:

    def test_normal_type_stays_normal(self):
        assert CSVDataExporter._resolve_export_connection_type({'connection_type': 'normal'}) == 'normal'

    def test_async_type_becomes_normal(self):
        assert CSVDataExporter._resolve_export_connection_type({'connection_type': 'async'}) == 'normal'

    def test_async_pool_type_becomes_normal(self):
        assert CSVDataExporter._resolve_export_connection_type({'connection_type': 'async_pool'}) == 'normal'
