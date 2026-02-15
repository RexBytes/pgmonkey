import logging
import pytest
from pgmonkey.connections.postgres.postgres_connection_factory import PostgresConnectionFactory
from pgmonkey.connections.postgres.normal_connection import PGNormalConnection
from pgmonkey.connections.postgres.pool_connection import PGPoolConnection
from pgmonkey.connections.postgres.async_connection import PGAsyncConnection
from pgmonkey.connections.postgres.async_pool_connection import PGAsyncPoolConnection


class TestPostgresConnectionFactory:

    def test_filter_config_keeps_empty_strings(self, sample_config):
        """Empty string values like sslcert='' should be kept (psycopg/libpq treats them as unset)."""
        factory = PostgresConnectionFactory(sample_config, 'normal')
        assert factory.config['sslcert'] == ''
        assert factory.config['sslkey'] == ''
        assert factory.config['sslrootcert'] == ''

    def test_filter_config_strips_none_values(self, sample_config):
        """None values should be stripped from filtered config."""
        sample_config['postgresql']['connection_settings']['password'] = None
        factory = PostgresConnectionFactory(sample_config, 'normal')
        assert 'password' not in factory.config

    def test_filter_config_keeps_valid_values(self, sample_config, filtered_connection_settings):
        """Non-empty connection settings should be preserved."""
        factory = PostgresConnectionFactory(sample_config, 'normal')
        assert factory.config == filtered_connection_settings

    def test_filter_config_ignores_unknown_keys(self, sample_config):
        """Keys not in VALID_CONNECTION_KEYS should be stripped."""
        sample_config['postgresql']['connection_settings']['unknown_key'] = 'value'
        factory = PostgresConnectionFactory(sample_config, 'normal')
        assert 'unknown_key' not in factory.config

    def test_filter_config_warns_on_unknown_keys(self, sample_config, caplog):
        """Unknown keys should produce a warning log."""
        sample_config['postgresql']['connection_settings']['hosst'] = 'localhost'
        with caplog.at_level(logging.WARNING):
            factory = PostgresConnectionFactory(sample_config, 'normal')
        assert 'hosst' in caplog.text
        assert "Unknown connection settings ignored" in caplog.text

    def test_extracts_pool_settings(self, sample_config):
        factory = PostgresConnectionFactory(sample_config, 'pool')
        assert factory.pool_settings == {'min_size': 2, 'max_size': 10, 'max_idle': 300, 'max_lifetime': 3600}

    def test_extracts_async_settings(self, sample_config):
        factory = PostgresConnectionFactory(sample_config, 'async')
        assert factory.async_settings['statement_timeout'] == '30000'

    def test_extracts_async_pool_settings(self, sample_config):
        factory = PostgresConnectionFactory(sample_config, 'async_pool')
        assert factory.async_pool_settings == {'min_size': 2, 'max_size': 10, 'max_idle': 300, 'max_lifetime': 3600}

    def test_missing_pool_settings_defaults_to_empty(self, sample_config):
        del sample_config['postgresql']['pool_settings']
        factory = PostgresConnectionFactory(sample_config, 'pool')
        assert factory.pool_settings == {}

    def test_get_connection_normal(self, sample_config):
        factory = PostgresConnectionFactory(sample_config, 'normal')
        conn = factory.get_connection()
        assert isinstance(conn, PGNormalConnection)
        assert conn.connection_type == 'normal'

    def test_get_connection_pool(self, sample_config):
        factory = PostgresConnectionFactory(sample_config, 'pool')
        conn = factory.get_connection()
        assert isinstance(conn, PGPoolConnection)
        assert conn.connection_type == 'pool'

    def test_get_connection_async(self, sample_config):
        factory = PostgresConnectionFactory(sample_config, 'async')
        conn = factory.get_connection()
        assert isinstance(conn, PGAsyncConnection)
        assert conn.connection_type == 'async'

    def test_get_connection_async_pool(self, sample_config):
        factory = PostgresConnectionFactory(sample_config, 'async_pool')
        conn = factory.get_connection()
        assert isinstance(conn, PGAsyncPoolConnection)
        assert conn.connection_type == 'async_pool'

    def test_get_connection_async_pool_receives_async_settings(self, sample_config):
        """async_pool connections should receive async_settings for GUC configuration."""
        factory = PostgresConnectionFactory(sample_config, 'async_pool')
        conn = factory.get_connection()
        assert conn.async_settings == sample_config['postgresql']['async_settings']

    def test_get_connection_invalid_type_raises(self, sample_config):
        factory = PostgresConnectionFactory(sample_config, 'invalid')
        with pytest.raises(ValueError, match="Unsupported connection type"):
            factory.get_connection()

    def test_connection_type_stored_on_factory(self, sample_config):
        factory = PostgresConnectionFactory(sample_config, 'pool')
        assert factory.connection_type == 'pool'


class TestPoolSettingsValidation:

    def test_min_size_greater_than_max_size_raises(self, sample_config):
        sample_config['postgresql']['pool_settings'] = {'min_size': 20, 'max_size': 5}
        with pytest.raises(ValueError, match="min_size .* cannot be greater than max_size"):
            PostgresConnectionFactory(sample_config, 'pool')

    def test_async_pool_min_greater_than_max_raises(self, sample_config):
        sample_config['postgresql']['async_pool_settings'] = {'min_size': 20, 'max_size': 5}
        with pytest.raises(ValueError, match="min_size .* cannot be greater than max_size"):
            PostgresConnectionFactory(sample_config, 'async_pool')

    def test_valid_pool_settings_pass(self, sample_config):
        sample_config['postgresql']['pool_settings'] = {'min_size': 2, 'max_size': 10}
        factory = PostgresConnectionFactory(sample_config, 'pool')
        assert factory.pool_settings == {'min_size': 2, 'max_size': 10}

    def test_equal_min_max_passes(self, sample_config):
        sample_config['postgresql']['pool_settings'] = {'min_size': 5, 'max_size': 5}
        factory = PostgresConnectionFactory(sample_config, 'pool')
        assert factory.pool_settings['min_size'] == factory.pool_settings['max_size']
