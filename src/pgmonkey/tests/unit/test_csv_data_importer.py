import csv
import os
import pytest
import yaml
from unittest.mock import patch, MagicMock
from pgmonkey.tools.csv_data_importer import CSVDataImporter
from pgmonkey.common.exceptions import ConfigFileCreatedError


class TestCSVDataImporterInit:

    def test_schema_table_split(self, tmp_path):
        """table_name with a dot should split into schema and table."""
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("col1,col2\na,b\n")
        config_file = tmp_path / "data.yaml"
        config_file.write_text(yaml.dump({
            'has_headers': True, 'auto_create_table': True,
            'enforce_lowercase': True, 'delimiter': ',',
            'quotechar': '"', 'encoding': 'utf-8',
        }))

        importer = CSVDataImporter(
            str(tmp_path / "conn.yaml"), str(csv_file),
            "myschema.mytable", str(config_file),
        )
        assert importer.schema_name == "myschema"
        assert importer.table_name == "mytable"

    def test_default_schema_is_public(self, tmp_path):
        """table_name without a dot should default schema to 'public'."""
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("col1,col2\na,b\n")
        config_file = tmp_path / "data.yaml"
        config_file.write_text(yaml.dump({
            'has_headers': True, 'auto_create_table': True,
            'enforce_lowercase': True, 'delimiter': ',',
            'quotechar': '"', 'encoding': 'utf-8',
        }))

        importer = CSVDataImporter(
            str(tmp_path / "conn.yaml"), str(csv_file),
            "mytable", str(config_file),
        )
        assert importer.schema_name == "public"
        assert importer.table_name == "mytable"

    def test_multi_dot_table_name(self, tmp_path):
        """table_name with multiple dots should only split on the first dot."""
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("col1\na\n")
        config_file = tmp_path / "data.yaml"
        config_file.write_text(yaml.dump({
            'has_headers': True, 'auto_create_table': True,
            'enforce_lowercase': True, 'delimiter': ',',
            'quotechar': '"', 'encoding': 'utf-8',
        }))

        importer = CSVDataImporter(
            str(tmp_path / "conn.yaml"), str(csv_file),
            "catalog.schema.table", str(config_file),
        )
        assert importer.schema_name == "catalog"
        assert importer.table_name == "schema.table"

    def test_config_file_created_when_missing(self, tmp_path):
        """When no import config exists, it should be auto-created and raise ConfigFileCreatedError."""
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("col1,col2\na,b\n")

        with pytest.raises(ConfigFileCreatedError):
            CSVDataImporter(
                str(tmp_path / "conn.yaml"), str(csv_file),
                "mytable",
            )

        # The config file should have been created
        auto_config = tmp_path / "data.yaml"
        assert auto_config.exists()


class TestBOMDetection:

    def _make_importer(self, tmp_path):
        """Helper to create an importer with a pre-existing config."""
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("col1\na\n")
        config_file = tmp_path / "data.yaml"
        config_file.write_text(yaml.dump({
            'has_headers': True, 'auto_create_table': True,
            'enforce_lowercase': True, 'delimiter': ',',
            'quotechar': '"', 'encoding': 'utf-8',
        }))
        return CSVDataImporter(
            str(tmp_path / "conn.yaml"), str(csv_file),
            "mytable", str(config_file),
        )

    def test_utf8_bom(self, tmp_path):
        importer = self._make_importer(tmp_path)
        csv_file = tmp_path / "data.csv"
        csv_file.write_bytes(b'\xef\xbb\xbfcol1\n')
        assert importer._detect_bom() == 'utf-8-sig'

    def test_utf16_le_bom(self, tmp_path):
        importer = self._make_importer(tmp_path)
        csv_file = tmp_path / "data.csv"
        csv_file.write_bytes(b'\xff\xfec\x00o\x00l\x001\x00\n\x00')
        assert importer._detect_bom() == 'utf-16-le'

    def test_utf16_be_bom(self, tmp_path):
        importer = self._make_importer(tmp_path)
        csv_file = tmp_path / "data.csv"
        csv_file.write_bytes(b'\xfe\xff\x00c\x00o\x00l\x001\x00\n')
        assert importer._detect_bom() == 'utf-16-be'

    def test_utf32_le_bom(self, tmp_path):
        importer = self._make_importer(tmp_path)
        csv_file = tmp_path / "data.csv"
        csv_file.write_bytes(b'\xff\xfe\x00\x00c\x00\x00\x00')
        assert importer._detect_bom() == 'utf-32-le'

    def test_utf32_be_bom(self, tmp_path):
        importer = self._make_importer(tmp_path)
        csv_file = tmp_path / "data.csv"
        csv_file.write_bytes(b'\x00\x00\xfe\xffc\x00\x00\x00')
        assert importer._detect_bom() == 'utf-32-be'

    def test_utf32_le_not_misdetected_as_utf16_le(self, tmp_path):
        """UTF-32-LE BOM starts with same bytes as UTF-16-LE. Must detect UTF-32 first."""
        importer = self._make_importer(tmp_path)
        csv_file = tmp_path / "data.csv"
        csv_file.write_bytes(b'\xff\xfe\x00\x00data')
        assert importer._detect_bom() == 'utf-32-le'

    def test_no_bom_returns_none(self, tmp_path):
        importer = self._make_importer(tmp_path)
        csv_file = tmp_path / "data.csv"
        csv_file.write_bytes(b'col1,col2\na,b\n')
        assert importer._detect_bom() is None


class TestColumnNameFormatting:

    def _make_importer(self, tmp_path, csv_content="col1\na\n"):
        csv_file = tmp_path / "data.csv"
        csv_file.write_text(csv_content)
        config_file = tmp_path / "data.yaml"
        config_file.write_text(yaml.dump({
            'has_headers': True, 'auto_create_table': True,
            'enforce_lowercase': True, 'delimiter': ',',
            'quotechar': '"', 'encoding': 'utf-8',
        }))
        return CSVDataImporter(
            str(tmp_path / "conn.yaml"), str(csv_file),
            "mytable", str(config_file),
        )

    def test_spaces_replaced_with_underscores(self, tmp_path):
        importer = self._make_importer(tmp_path)
        result = importer._format_column_names(["First Name", "Last Name"])
        assert result == ["first_name", "last_name"]

    def test_special_chars_replaced(self, tmp_path):
        importer = self._make_importer(tmp_path)
        result = importer._format_column_names(["email@address", "phone#"])
        assert result == ["email_address", "phone_"]

    def test_empty_columns_skipped(self, tmp_path):
        importer = self._make_importer(tmp_path)
        result = importer._format_column_names(["name", "", "age"])
        assert result == ["name", "age"]

    def test_valid_column_name(self, tmp_path):
        importer = self._make_importer(tmp_path)
        assert importer._is_valid_column_name("valid_name")
        assert importer._is_valid_column_name("_private")
        assert not importer._is_valid_column_name("123invalid")


class TestResolveConnectionType:

    def test_normal_type_stays_normal(self):
        assert CSVDataImporter._resolve_import_connection_type({'connection_type': 'normal'}) == 'normal'

    def test_pool_type_becomes_normal(self):
        assert CSVDataImporter._resolve_import_connection_type({'connection_type': 'pool'}) == 'normal'

    def test_async_type_becomes_normal(self):
        assert CSVDataImporter._resolve_import_connection_type({'connection_type': 'async'}) == 'normal'

    def test_async_pool_type_becomes_normal(self):
        assert CSVDataImporter._resolve_import_connection_type({'connection_type': 'async_pool'}) == 'normal'
