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

    def test_prints_unsupported_message_psycopg(self, sample_config_file, capsys):
        gen = ConnectionCodeGenerator()
        gen.generate_connection_code(sample_config_file, 'invalid_type', library='psycopg')
        output = capsys.readouterr().out
        assert "Unsupported connection type" in output


# -- Native psycopg library tests ------------------------------------------

class TestCodeGeneratorPsycopgNormal:

    def test_generates_psycopg_normal_code(self, sample_config_file, capsys):
        gen = ConnectionCodeGenerator()
        gen.generate_connection_code(sample_config_file, 'normal', library='psycopg')
        output = capsys.readouterr().out
        assert "psycopg" in output.lower()
        assert "import psycopg" in output
        assert "psycopg.connect" in output
        assert "PGConnectionManager" not in output


class TestCodeGeneratorPsycopgPool:

    def test_generates_psycopg_pool_code(self, sample_config_file, capsys):
        gen = ConnectionCodeGenerator()
        gen.generate_connection_code(sample_config_file, 'pool', library='psycopg')
        output = capsys.readouterr().out
        assert "psycopg_pool" in output.lower()
        assert "ConnectionPool" in output
        assert "make_conninfo" in output
        assert "PGConnectionManager" not in output


class TestCodeGeneratorPsycopgAsync:

    def test_generates_psycopg_async_code(self, sample_config_file, capsys):
        gen = ConnectionCodeGenerator()
        gen.generate_connection_code(sample_config_file, 'async', library='psycopg')
        output = capsys.readouterr().out
        assert "AsyncConnection" in output
        assert "await" in output
        assert "async_settings" in output
        assert "PGConnectionManager" not in output

    def test_uses_sql_identifier_for_set(self, sample_config_file, capsys):
        """Generated async psycopg code should use sql.Identifier for SET statements."""
        gen = ConnectionCodeGenerator()
        gen.generate_connection_code(sample_config_file, 'async', library='psycopg')
        output = capsys.readouterr().out
        assert "sql.SQL" in output
        assert "sql.Identifier" in output


class TestCodeGeneratorPsycopgAsyncPool:

    def test_generates_psycopg_async_pool_code(self, sample_config_file, capsys):
        gen = ConnectionCodeGenerator()
        gen.generate_connection_code(sample_config_file, 'async_pool', library='psycopg')
        output = capsys.readouterr().out
        assert "AsyncConnectionPool" in output
        assert "await" in output
        assert "configure" in output
        assert "PGConnectionManager" not in output

    def test_uses_sql_identifier_for_set(self, sample_config_file, capsys):
        """Generated async pool psycopg code should use sql.Identifier for SET statements."""
        gen = ConnectionCodeGenerator()
        gen.generate_connection_code(sample_config_file, 'async_pool', library='psycopg')
        output = capsys.readouterr().out
        assert "sql.SQL" in output
        assert "sql.Identifier" in output


class TestCodeGeneratorPathEscaping:

    def test_single_quote_in_path_produces_valid_python(self, sample_config, tmp_path, capsys):
        """Paths with single quotes must not break the generated code."""
        config_dir = tmp_path / "o'brien"
        config_dir.mkdir()
        config_file = config_dir / "config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(sample_config, f, sort_keys=False)

        gen = ConnectionCodeGenerator()
        gen.generate_connection_code(str(config_file), 'normal')
        output = capsys.readouterr().out

        # Find the config_file_path assignment line and verify it compiles
        for line in output.splitlines():
            stripped = line.strip()
            if stripped.startswith("config_file_path = "):
                compile(stripped, "<generated>", "exec")  # raises SyntaxError if broken
                assert "o'brien" in stripped
                return
        pytest.fail("config_file_path assignment not found in output")


class TestCodeGeneratorLibraryDefault:

    def test_defaults_to_pgmonkey(self, sample_config_file, capsys):
        """Without library arg, should generate pgmonkey code (backward compat)."""
        gen = ConnectionCodeGenerator()
        gen.generate_connection_code(sample_config_file, 'normal')
        output = capsys.readouterr().out
        assert "PGConnectionManager" in output
