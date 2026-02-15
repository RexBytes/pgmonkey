import logging
import pytest
from pgmonkey.connections.postgres.postgres_connection_factory import PostgresConnectionFactory
from pgmonkey.connections.postgres.normal_connection import PGNormalConnection
from pgmonkey.connections.postgres.pool_connection import PGPoolConnection
from pgmonkey.connections.postgres.async_connection import PGAsyncConnection
from pgmonkey.connections.postgres.async_pool_connection import PGAsyncPoolConnection


class TestPostgresConnectionFactory:

    def test_filter_config_strips_empty_string_values(self, sample_config):
        """Empty string values like sslcert='' should be stripped from filtered config."""
        factory = PostgresConnectionFactory(sample_config, 'normal')
        assert 'sslcert' not in factory.config
        assert 'sslkey' not in factory.config
        assert 'sslrootcert' not in factory.config

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

    def test_filter_config_preserves_none_but_not_empty_string(self, sample_config):
        """None values should be kept (is not None check), empty strings should be stripped."""
        # None values are preserved by the `is not None` check
        sample_config['postgresql']['connection_settings']['keepalives'] = None
        factory = PostgresConnectionFactory(sample_config, 'normal')
        assert 'keepalives' not in factory.config

    def test_filter_config_preserves_zero_values(self, sample_config):
        """Zero values like keepalives=0 should NOT be silently dropped."""
        sample_config['postgresql']['connection_settings']['keepalives'] = 0
        factory = PostgresConnectionFactory(sample_config, 'normal')
        assert factory.config['keepalives'] == 0

    def test_extracts_pool_settings(self, sample_config):
        factory = PostgresConnectionFactory(sample_config, 'pool')
        assert factory.pool_settings == {'min_size': 2, 'max_size': 10, 'max_idle': 300, 'max_lifetime': 3600}

    def test_extracts_sync_settings(self, sample_config):
        factory = PostgresConnectionFactory(sample_config, 'normal')
        assert factory.sync_settings['statement_timeout'] == '30000'

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

    def test_missing_sync_settings_defaults_to_empty(self, sample_config):
        del sample_config['postgresql']['sync_settings']
        factory = PostgresConnectionFactory(sample_config, 'normal')
        assert factory.sync_settings == {}

    def test_get_connection_normal(self, sample_config):
        factory = PostgresConnectionFactory(sample_config, 'normal')
        conn = factory.get_connection()
        assert isinstance(conn, PGNormalConnection)
        assert conn.connection_type == 'normal'

    def test_get_connection_normal_receives_sync_settings(self, sample_config):
        factory = PostgresConnectionFactory(sample_config, 'normal')
        conn = factory.get_connection()
        assert conn.sync_settings == sample_config['postgresql']['sync_settings']

    def test_get_connection_pool(self, sample_config):
        factory = PostgresConnectionFactory(sample_config, 'pool')
        conn = factory.get_connection()
        assert isinstance(conn, PGPoolConnection)
        assert conn.connection_type == 'pool'

    def test_get_connection_pool_receives_sync_settings(self, sample_config):
        factory = PostgresConnectionFactory(sample_config, 'pool')
        conn = factory.get_connection()
        assert conn.sync_settings == sample_config['postgresql']['sync_settings']

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


class TestAutocommitConfig:

    def test_autocommit_true_set_on_connection(self, sample_config):
        sample_config['postgresql']['connection_settings']['autocommit'] = True
        factory = PostgresConnectionFactory(sample_config, 'normal')
        conn = factory.get_connection()
        assert conn.autocommit is True

    def test_autocommit_false_set_on_connection(self, sample_config):
        sample_config['postgresql']['connection_settings']['autocommit'] = False
        factory = PostgresConnectionFactory(sample_config, 'normal')
        conn = factory.get_connection()
        assert conn.autocommit is False

    def test_autocommit_not_set_leaves_default(self, sample_config):
        factory = PostgresConnectionFactory(sample_config, 'normal')
        conn = factory.get_connection()
        assert conn.autocommit is None

    def test_autocommit_removed_from_connection_config(self, sample_config):
        """autocommit should not be passed as a psycopg connection parameter."""
        sample_config['postgresql']['connection_settings']['autocommit'] = True
        factory = PostgresConnectionFactory(sample_config, 'normal')
        assert 'autocommit' not in factory.config
