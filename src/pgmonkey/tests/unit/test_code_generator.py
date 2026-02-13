import pytest
import yaml
from pgmonkey.tools.connection_code_generator import ConnectionCodeGenerator


class TestCodeGeneratorNormal:

    def test_generates_normal_code(self, sample_config_file, capsys):
        gen = ConnectionCodeGenerator()
        gen.generate_connection_code(sample_config_file, 'normal')
        output = capsys.readouterr().out
        assert "normal synchronous" in output.lower()
        assert "get_database_connection" in output
        assert "'normal'" in output


class TestCodeGeneratorPool:

    def test_generates_pool_code(self, sample_config_file, capsys):
        gen = ConnectionCodeGenerator()
        gen.generate_connection_code(sample_config_file, 'pool')
        output = capsys.readouterr().out
        assert "pooled" in output.lower()
        assert "'pool'" in output


class TestCodeGeneratorAsync:

    def test_generates_async_code(self, sample_config_file, capsys):
        gen = ConnectionCodeGenerator()
        gen.generate_connection_code(sample_config_file, 'async')
        output = capsys.readouterr().out
        assert "async" in output.lower()
        assert "await" in output
        assert "'async'" in output


class TestCodeGeneratorAsyncPool:

    def test_generates_async_pool_code(self, sample_config_file, capsys):
        gen = ConnectionCodeGenerator()
        gen.generate_connection_code(sample_config_file, 'async_pool')
        output = capsys.readouterr().out
        assert "async" in output.lower()
        assert "'async_pool'" in output


class TestCodeGeneratorDefaultType:

    def test_uses_config_file_default_when_no_override(self, sample_config_file, capsys):
        """sample_config has connection_type: 'normal', so should generate normal code."""
        gen = ConnectionCodeGenerator()
        gen.generate_connection_code(sample_config_file, None)
        output = capsys.readouterr().out
        assert "normal synchronous" in output.lower()


class TestCodeGeneratorUnsupportedType:

    def test_prints_unsupported_message(self, sample_config_file, capsys):
        gen = ConnectionCodeGenerator()
        gen.generate_connection_code(sample_config_file, 'invalid_type')
        output = capsys.readouterr().out
        assert "Unsupported connection type" in output
