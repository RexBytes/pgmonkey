import os
import pytest
import yaml
import tempfile

from pgmonkey.common.utils.envutils import (
    resolve_env_vars,
    EnvInterpolationError,
    SENSITIVE_KEYS,
    _is_sensitive_key,
)
from pgmonkey.common.utils.redaction import redact_config, REDACTED
from pgmonkey.common.utils.configutils import load_config


# ---------------------------------------------------------------------------
# _is_sensitive_key
# ---------------------------------------------------------------------------

class TestIsSensitiveKey:

    def test_password_is_sensitive(self):
        assert _is_sensitive_key('password') is True

    def test_sslkey_is_sensitive(self):
        assert _is_sensitive_key('sslkey') is True

    def test_sslcert_is_sensitive(self):
        assert _is_sensitive_key('sslcert') is True

    def test_sslrootcert_is_sensitive(self):
        assert _is_sensitive_key('sslrootcert') is True

    def test_token_substring_is_sensitive(self):
        assert _is_sensitive_key('api_token') is True
        assert _is_sensitive_key('TOKEN_VALUE') is True

    def test_secret_substring_is_sensitive(self):
        assert _is_sensitive_key('my_secret_key') is True

    def test_credential_substring_is_sensitive(self):
        assert _is_sensitive_key('db_credential') is True

    def test_host_is_not_sensitive(self):
        assert _is_sensitive_key('host') is False

    def test_port_is_not_sensitive(self):
        assert _is_sensitive_key('port') is False

    def test_dbname_is_not_sensitive(self):
        assert _is_sensitive_key('dbname') is False


# ---------------------------------------------------------------------------
# resolve_env_vars - inline ${VAR} / ${VAR:-default}
# ---------------------------------------------------------------------------

class TestResolveInlineVars:

    def test_simple_var_substitution(self, monkeypatch):
        monkeypatch.setenv('PGHOST', 'db.example.com')
        config = {'connection_settings': {'host': '${PGHOST}'}}
        result = resolve_env_vars(config)
        assert result['connection_settings']['host'] == 'db.example.com'

    def test_var_with_default(self, monkeypatch):
        monkeypatch.delenv('PGHOST', raising=False)
        config = {'connection_settings': {'host': '${PGHOST:-localhost}'}}
        result = resolve_env_vars(config)
        assert result['connection_settings']['host'] == 'localhost'

    def test_var_with_empty_default(self, monkeypatch):
        monkeypatch.delenv('MYVAR', raising=False)
        config = {'connection_settings': {'host': '${MYVAR:-}'}}
        result = resolve_env_vars(config)
        assert result['connection_settings']['host'] == ''

    def test_set_var_overrides_default(self, monkeypatch):
        monkeypatch.setenv('PGHOST', 'prod.db.com')
        config = {'connection_settings': {'host': '${PGHOST:-localhost}'}}
        result = resolve_env_vars(config)
        assert result['connection_settings']['host'] == 'prod.db.com'

    def test_missing_var_no_default_raises(self, monkeypatch):
        monkeypatch.delenv('MISSING_VAR', raising=False)
        config = {'connection_settings': {'host': '${MISSING_VAR}'}}
        with pytest.raises(EnvInterpolationError, match="MISSING_VAR"):
            resolve_env_vars(config)

    def test_multiple_vars_in_one_string(self, monkeypatch):
        monkeypatch.setenv('PGHOST', 'db.example.com')
        monkeypatch.setenv('PGPORT', '5433')
        config = {'connection_settings': {'conninfo': '${PGHOST}:${PGPORT}'}}
        result = resolve_env_vars(config)
        assert result['connection_settings']['conninfo'] == 'db.example.com:5433'

    def test_non_string_values_pass_through(self):
        config = {'pool_settings': {'min_size': 5, 'max_size': 20}}
        result = resolve_env_vars(config)
        assert result == config

    def test_no_interpolation_without_dollar_brace(self):
        config = {'connection_settings': {'host': 'plain-value'}}
        result = resolve_env_vars(config)
        assert result['connection_settings']['host'] == 'plain-value'

    def test_var_name_with_underscores(self, monkeypatch):
        monkeypatch.setenv('MY_DB_HOST_NAME', 'custom.host')
        config = {'connection_settings': {'host': '${MY_DB_HOST_NAME}'}}
        result = resolve_env_vars(config)
        assert result['connection_settings']['host'] == 'custom.host'


# ---------------------------------------------------------------------------
# resolve_env_vars - sensitive key defaults
# ---------------------------------------------------------------------------

class TestSensitiveKeyDefaults:

    def test_password_default_disallowed_by_default(self, monkeypatch):
        monkeypatch.delenv('PGPASSWORD', raising=False)
        config = {'connection_settings': {'password': '${PGPASSWORD:-fallback}'}}
        with pytest.raises(EnvInterpolationError, match="sensitive key"):
            resolve_env_vars(config)

    def test_password_default_allowed_when_opted_in(self, monkeypatch):
        monkeypatch.delenv('PGPASSWORD', raising=False)
        config = {'connection_settings': {'password': '${PGPASSWORD:-fallback}'}}
        result = resolve_env_vars(config, allow_sensitive_defaults=True)
        assert result['connection_settings']['password'] == 'fallback'

    def test_password_from_env_resolves(self, monkeypatch):
        monkeypatch.setenv('PGPASSWORD', 'secret123')
        config = {'connection_settings': {'password': '${PGPASSWORD}'}}
        result = resolve_env_vars(config)
        assert result['connection_settings']['password'] == 'secret123'

    def test_sslkey_default_disallowed(self, monkeypatch):
        monkeypatch.delenv('SSL_KEY', raising=False)
        config = {'connection_settings': {'sslkey': '${SSL_KEY:-/tmp/key}'}}
        with pytest.raises(EnvInterpolationError, match="sensitive key"):
            resolve_env_vars(config)

    def test_non_sensitive_key_allows_default(self, monkeypatch):
        monkeypatch.delenv('PGHOST', raising=False)
        config = {'connection_settings': {'host': '${PGHOST:-localhost}'}}
        result = resolve_env_vars(config)
        assert result['connection_settings']['host'] == 'localhost'


# ---------------------------------------------------------------------------
# resolve_env_vars - structured from_env / from_file
# ---------------------------------------------------------------------------

class TestStructuredReferences:

    def test_from_env_resolves(self, monkeypatch):
        monkeypatch.setenv('DB_PASSWORD', 'secret456')
        config = {'connection_settings': {'password': {'from_env': 'DB_PASSWORD'}}}
        result = resolve_env_vars(config)
        assert result['connection_settings']['password'] == 'secret456'

    def test_from_env_missing_raises(self, monkeypatch):
        monkeypatch.delenv('DB_PASSWORD', raising=False)
        config = {'connection_settings': {'password': {'from_env': 'DB_PASSWORD'}}}
        with pytest.raises(EnvInterpolationError, match="DB_PASSWORD.*from_env"):
            resolve_env_vars(config)

    def test_from_file_resolves(self, tmp_path):
        secret_file = tmp_path / "db_password"
        secret_file.write_text("file_secret\n")
        config = {'connection_settings': {'password': {'from_file': str(secret_file)}}}
        result = resolve_env_vars(config)
        # Trailing newline should be trimmed
        assert result['connection_settings']['password'] == 'file_secret'

    def test_from_file_preserves_content_without_trailing_newline(self, tmp_path):
        secret_file = tmp_path / "db_password"
        secret_file.write_text("no_newline")
        config = {'connection_settings': {'password': {'from_file': str(secret_file)}}}
        result = resolve_env_vars(config)
        assert result['connection_settings']['password'] == 'no_newline'

    def test_from_file_missing_raises(self):
        config = {'connection_settings': {'password': {'from_file': '/nonexistent/path'}}}
        with pytest.raises(EnvInterpolationError, match="not found"):
            resolve_env_vars(config)

    def test_regular_dict_not_treated_as_ref(self):
        config = {'pool_settings': {'min_size': 5, 'max_size': 20}}
        result = resolve_env_vars(config)
        assert result == config

    def test_dict_with_extra_keys_not_treated_as_ref(self, monkeypatch):
        """A dict with from_env plus other keys is treated as a normal nested dict."""
        monkeypatch.setenv('SOME_VAR', 'value')
        config = {'connection_settings': {'password': {'from_env': 'SOME_VAR', 'extra': 'key'}}}
        result = resolve_env_vars(config)
        # Should be treated as a nested dict, not a structured ref
        assert isinstance(result['connection_settings']['password'], dict)


# ---------------------------------------------------------------------------
# resolve_env_vars - list values
# ---------------------------------------------------------------------------

class TestListInterpolation:

    def test_list_items_interpolated(self, monkeypatch):
        monkeypatch.setenv('HOST1', 'a.example.com')
        monkeypatch.setenv('HOST2', 'b.example.com')
        config = {'hosts': ['${HOST1}', '${HOST2}']}
        result = resolve_env_vars(config)
        assert result['hosts'] == ['a.example.com', 'b.example.com']

    def test_list_non_string_items_pass_through(self):
        config = {'ports': [5432, 5433]}
        result = resolve_env_vars(config)
        assert result['ports'] == [5432, 5433]


# ---------------------------------------------------------------------------
# resolve_env_vars - does not mutate input
# ---------------------------------------------------------------------------

class TestNoMutation:

    def test_original_config_unchanged(self, monkeypatch):
        monkeypatch.setenv('PGHOST', 'resolved.host')
        config = {'connection_settings': {'host': '${PGHOST}'}}
        original_host = config['connection_settings']['host']
        resolve_env_vars(config)
        assert config['connection_settings']['host'] == original_host


# ---------------------------------------------------------------------------
# resolve_env_vars - non-dict input
# ---------------------------------------------------------------------------

class TestNonDictInput:

    def test_non_dict_returns_as_is(self):
        assert resolve_env_vars('just a string') == 'just a string'
        assert resolve_env_vars(42) == 42
        assert resolve_env_vars(None) is None


# ---------------------------------------------------------------------------
# redact_config
# ---------------------------------------------------------------------------

class TestRedactConfig:

    def test_password_redacted(self):
        config = {'connection_settings': {'password': 'secret', 'host': 'localhost'}}
        result = redact_config(config)
        assert result['connection_settings']['password'] == REDACTED
        assert result['connection_settings']['host'] == 'localhost'

    def test_sslkey_redacted(self):
        config = {'connection_settings': {'sslkey': '/path/to/key'}}
        result = redact_config(config)
        assert result['connection_settings']['sslkey'] == REDACTED

    def test_sslcert_redacted(self):
        config = {'connection_settings': {'sslcert': '/path/to/cert'}}
        result = redact_config(config)
        assert result['connection_settings']['sslcert'] == REDACTED

    def test_sslrootcert_redacted(self):
        config = {'connection_settings': {'sslrootcert': '/path/to/ca'}}
        result = redact_config(config)
        assert result['connection_settings']['sslrootcert'] == REDACTED

    def test_token_key_redacted(self):
        config = {'connection_settings': {'api_token': 'tok_abc123'}}
        result = redact_config(config)
        assert result['connection_settings']['api_token'] == REDACTED

    def test_empty_password_not_redacted(self):
        config = {'connection_settings': {'password': ''}}
        result = redact_config(config)
        assert result['connection_settings']['password'] == ''

    def test_none_password_not_redacted(self):
        config = {'connection_settings': {'password': None}}
        result = redact_config(config)
        assert result['connection_settings']['password'] is None

    def test_non_sensitive_keys_preserved(self):
        config = {'connection_settings': {'host': 'db.com', 'port': '5432', 'dbname': 'mydb'}}
        result = redact_config(config)
        assert result == config

    def test_does_not_mutate_original(self):
        config = {'connection_settings': {'password': 'secret'}}
        redact_config(config)
        assert config['connection_settings']['password'] == 'secret'

    def test_non_dict_returns_as_is(self):
        assert redact_config('string') == 'string'
        assert redact_config(42) == 42


# ---------------------------------------------------------------------------
# load_config
# ---------------------------------------------------------------------------

class TestLoadConfig:

    def test_loads_yaml_without_interpolation(self, tmp_path):
        config_file = tmp_path / "test.yaml"
        config_file.write_text(yaml.dump({
            'connection_type': 'normal',
            'connection_settings': {'host': '${PGHOST}', 'password': 'plain'},
        }))
        result = load_config(str(config_file), resolve_env=False)
        # Should NOT resolve the ${PGHOST} reference
        assert result['connection_settings']['host'] == '${PGHOST}'

    def test_loads_yaml_with_interpolation(self, tmp_path, monkeypatch):
        monkeypatch.setenv('PGHOST', 'resolved.host')
        monkeypatch.setenv('PGPASSWORD', 'resolved_pass')
        config_file = tmp_path / "test.yaml"
        config_file.write_text(yaml.dump({
            'connection_type': 'normal',
            'connection_settings': {
                'host': '${PGHOST}',
                'password': '${PGPASSWORD}',
            },
        }))
        result = load_config(str(config_file), resolve_env=True)
        assert result['connection_settings']['host'] == 'resolved.host'
        assert result['connection_settings']['password'] == 'resolved_pass'

    def test_normalizes_old_format(self, tmp_path):
        config_file = tmp_path / "old.yaml"
        config_file.write_text(yaml.dump({
            'postgresql': {
                'connection_type': 'normal',
                'connection_settings': {'host': 'localhost'},
            }
        }))
        with pytest.warns(DeprecationWarning, match="postgresql"):
            result = load_config(str(config_file))
        assert result['connection_type'] == 'normal'

    def test_allow_sensitive_defaults_via_load_config(self, tmp_path, monkeypatch):
        monkeypatch.delenv('PGPASSWORD', raising=False)
        config_file = tmp_path / "test.yaml"
        config_file.write_text(yaml.dump({
            'connection_type': 'normal',
            'connection_settings': {'password': '${PGPASSWORD:-devpass}'},
        }))
        result = load_config(str(config_file), resolve_env=True,
                             allow_sensitive_defaults=True)
        assert result['connection_settings']['password'] == 'devpass'

    def test_sensitive_default_blocked_by_default_via_load_config(self, tmp_path, monkeypatch):
        monkeypatch.delenv('PGPASSWORD', raising=False)
        config_file = tmp_path / "test.yaml"
        config_file.write_text(yaml.dump({
            'connection_type': 'normal',
            'connection_settings': {'password': '${PGPASSWORD:-devpass}'},
        }))
        with pytest.raises(EnvInterpolationError, match="sensitive key"):
            load_config(str(config_file), resolve_env=True)

    def test_missing_var_raises_on_resolve(self, tmp_path, monkeypatch):
        monkeypatch.delenv('MISSING', raising=False)
        config_file = tmp_path / "test.yaml"
        config_file.write_text(yaml.dump({
            'connection_type': 'normal',
            'connection_settings': {'host': '${MISSING}'},
        }))
        with pytest.raises(EnvInterpolationError, match="MISSING"):
            load_config(str(config_file), resolve_env=True)

    def test_from_file_via_load_config(self, tmp_path):
        secret_file = tmp_path / "secret"
        secret_file.write_text("file_password\n")
        # Write YAML manually to preserve from_file structure
        config_file = tmp_path / "test.yaml"
        config_file.write_text(
            "connection_type: 'normal'\n"
            "connection_settings:\n"
            f"  password:\n"
            f"    from_file: {str(secret_file)}\n"
            "  host: 'localhost'\n"
        )
        result = load_config(str(config_file), resolve_env=True)
        assert result['connection_settings']['password'] == 'file_password'


# ---------------------------------------------------------------------------
# Integration: resolve_env_vars with full pgmonkey config
# ---------------------------------------------------------------------------

class TestFullConfigInterpolation:

    def test_full_config_with_env_vars(self, monkeypatch):
        monkeypatch.setenv('PGUSER', 'admin')
        monkeypatch.setenv('PGPASSWORD', 's3cret')
        monkeypatch.setenv('PGHOST', 'db.prod.internal')
        monkeypatch.setenv('PGPORT', '5433')
        monkeypatch.setenv('PGDATABASE', 'appdb')

        config = {
            'connection_type': 'normal',
            'connection_settings': {
                'user': '${PGUSER}',
                'password': '${PGPASSWORD}',
                'host': '${PGHOST}',
                'port': '${PGPORT}',
                'dbname': '${PGDATABASE}',
                'sslmode': 'prefer',
                'connect_timeout': '10',
            },
            'pool_settings': {
                'min_size': 5,
                'max_size': 20,
            },
        }

        result = resolve_env_vars(config)
        cs = result['connection_settings']
        assert cs['user'] == 'admin'
        assert cs['password'] == 's3cret'
        assert cs['host'] == 'db.prod.internal'
        assert cs['port'] == '5433'
        assert cs['dbname'] == 'appdb'
        assert cs['sslmode'] == 'prefer'
        # Non-interpolated values unchanged
        assert result['pool_settings'] == {'min_size': 5, 'max_size': 20}

    def test_mixed_static_and_env_values(self, monkeypatch):
        monkeypatch.setenv('PGPASSWORD', 'secret')
        config = {
            'connection_settings': {
                'host': 'localhost',
                'password': '${PGPASSWORD}',
                'port': '5432',
            },
        }
        result = resolve_env_vars(config)
        assert result['connection_settings']['host'] == 'localhost'
        assert result['connection_settings']['password'] == 'secret'
        assert result['connection_settings']['port'] == '5432'


# ---------------------------------------------------------------------------
# PGConnectionManager.get_database_connection with resolve_env
# ---------------------------------------------------------------------------

class TestManagerResolveEnv:

    def test_resolve_env_param_exists(self):
        """Verify the resolve_env parameter is accepted."""
        from pgmonkey.managers.pgconnection_manager import PGConnectionManager
        import inspect
        sig = inspect.signature(PGConnectionManager.get_database_connection)
        assert 'resolve_env' in sig.parameters

    def test_resolve_env_from_dict_param_exists(self):
        """Verify the resolve_env parameter is accepted on dict method."""
        from pgmonkey.managers.pgconnection_manager import PGConnectionManager
        import inspect
        sig = inspect.signature(PGConnectionManager.get_database_connection_from_dict)
        assert 'resolve_env' in sig.parameters

    def test_allow_sensitive_defaults_param_exists(self):
        """Verify allow_sensitive_defaults is accepted on file-based method."""
        from pgmonkey.managers.pgconnection_manager import PGConnectionManager
        import inspect
        sig = inspect.signature(PGConnectionManager.get_database_connection)
        assert 'allow_sensitive_defaults' in sig.parameters

    def test_allow_sensitive_defaults_from_dict_param_exists(self):
        """Verify allow_sensitive_defaults is accepted on dict-based method."""
        from pgmonkey.managers.pgconnection_manager import PGConnectionManager
        import inspect
        sig = inspect.signature(PGConnectionManager.get_database_connection_from_dict)
        assert 'allow_sensitive_defaults' in sig.parameters


# ---------------------------------------------------------------------------
# EnvInterpolationError messages - no secret values leaked
# ---------------------------------------------------------------------------

class TestErrorMessages:

    def test_missing_var_error_names_var_not_value(self, monkeypatch):
        monkeypatch.delenv('SECRET_VAR', raising=False)
        config = {'connection_settings': {'password': '${SECRET_VAR}'}}
        with pytest.raises(EnvInterpolationError) as exc_info:
            resolve_env_vars(config)
        # Error should mention the var name and key, but not any resolved value
        assert 'SECRET_VAR' in str(exc_info.value)
        assert 'password' in str(exc_info.value)

    def test_sensitive_default_error_does_not_leak_default(self, monkeypatch):
        monkeypatch.delenv('PGPASSWORD', raising=False)
        config = {'connection_settings': {'password': '${PGPASSWORD:-fallback_secret}'}}
        with pytest.raises(EnvInterpolationError) as exc_info:
            resolve_env_vars(config)
        # The error should mention it's a sensitive key, not the fallback value
        assert 'sensitive key' in str(exc_info.value)

    def test_from_file_error_names_path(self):
        config = {'connection_settings': {'password': {'from_file': '/no/such/file'}}}
        with pytest.raises(EnvInterpolationError) as exc_info:
            resolve_env_vars(config)
        assert '/no/such/file' in str(exc_info.value)
        assert 'from_file' in str(exc_info.value)


# ---------------------------------------------------------------------------
# Top-level re-exports
# ---------------------------------------------------------------------------

class TestTopLevelExports:

    def test_redact_config_importable_from_pgmonkey(self):
        """Verify redact_config is re-exported from the top-level package."""
        from pgmonkey import redact_config as top_level_redact
        from pgmonkey.common.utils.redaction import redact_config as internal_redact
        assert top_level_redact is internal_redact

    def test_redact_config_works_via_top_level_import(self):
        """Verify the re-exported redact_config actually works."""
        from pgmonkey import redact_config
        config = {'connection_settings': {'password': 'secret', 'host': 'localhost'}}
        result = redact_config(config)
        assert result['connection_settings']['password'] == '***REDACTED***'
        assert result['connection_settings']['host'] == 'localhost'
