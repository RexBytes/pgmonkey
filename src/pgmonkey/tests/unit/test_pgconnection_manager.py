import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from pgmonkey.managers.pgconnection_manager import PGConnectionManager, VALID_CONNECTION_TYPES


class TestPGConnectionManager:

    def test_valid_connection_types_constant(self):
        assert VALID_CONNECTION_TYPES == ('normal', 'pool', 'async', 'async_pool')

    # --- Type resolution tests ---

    @patch('pgmonkey.managers.pgconnection_manager.PostgresConnectionFactory')
    def test_get_connection_uses_config_default(self, mock_factory_cls, sample_config):
        """When no connection_type is passed, the YAML value is used."""
        mock_conn = MagicMock()
        mock_factory_cls.return_value.get_connection.return_value = mock_conn

        manager = PGConnectionManager()
        manager._get_postgresql_connection_sync(sample_config, 'normal')

        mock_factory_cls.assert_called_once_with(sample_config, 'normal')

    @patch('pgmonkey.managers.pgconnection_manager.PostgresConnectionFactory')
    def test_get_connection_override_type(self, mock_factory_cls, sample_config):
        """Explicit connection_type should override the config file value."""
        mock_conn = MagicMock()
        mock_factory_cls.return_value.get_connection.return_value = mock_conn

        manager = PGConnectionManager()
        result = manager._get_connection(sample_config, 'pool')

        mock_factory_cls.assert_called_once_with(sample_config, 'pool')

    def test_get_connection_defaults_to_normal_when_missing(self):
        """When connection_type is absent from config and not passed, default to 'normal'."""
        config = {'postgresql': {'connection_settings': {'user': 'test', 'host': 'localhost', 'dbname': 'db'}}}

        manager = PGConnectionManager()
        with patch('pgmonkey.managers.pgconnection_manager.PostgresConnectionFactory') as mock_factory_cls:
            mock_conn = MagicMock()
            mock_factory_cls.return_value.get_connection.return_value = mock_conn
            manager._get_connection(config, None)
            mock_factory_cls.assert_called_once_with(config, 'normal')

    def test_get_connection_invalid_type_raises(self, sample_config):
        manager = PGConnectionManager()
        with pytest.raises(ValueError, match="Unsupported connection type: 'banana'"):
            manager._get_connection(sample_config, 'banana')

    # --- Sync path tests ---

    @patch('pgmonkey.managers.pgconnection_manager.PostgresConnectionFactory')
    def test_sync_connection_calls_connect(self, mock_factory_cls, sample_config):
        mock_conn = MagicMock()
        mock_factory_cls.return_value.get_connection.return_value = mock_conn

        manager = PGConnectionManager()
        result = manager._get_postgresql_connection_sync(sample_config, 'normal')

        mock_conn.connect.assert_called_once()
        assert result is mock_conn

    # --- Async path tests ---

    @pytest.mark.asyncio
    @patch('pgmonkey.managers.pgconnection_manager.PostgresConnectionFactory')
    async def test_async_connection_calls_connect(self, mock_factory_cls, sample_config):
        mock_conn = AsyncMock()
        mock_factory_cls.return_value.get_connection.return_value = mock_conn

        manager = PGConnectionManager()
        result = await manager._get_postgresql_connection_async(sample_config, 'async')

        mock_conn.connect.assert_called_once()
        assert result is mock_conn

    # --- File-based API tests ---

    @patch('pgmonkey.managers.pgconnection_manager.PostgresConnectionFactory')
    def test_get_database_connection_from_file(self, mock_factory_cls, sample_config_file):
        mock_conn = MagicMock()
        mock_factory_cls.return_value.get_connection.return_value = mock_conn

        manager = PGConnectionManager()
        result = manager.get_database_connection(sample_config_file, 'normal')

        assert result is mock_conn
        mock_conn.connect.assert_called_once()

    @patch('pgmonkey.managers.pgconnection_manager.PostgresConnectionFactory')
    def test_get_database_connection_from_file_uses_yaml_default(self, mock_factory_cls, sample_config_file):
        """Without explicit type, uses connection_type from the YAML file."""
        mock_conn = MagicMock()
        mock_factory_cls.return_value.get_connection.return_value = mock_conn

        manager = PGConnectionManager()
        result = manager.get_database_connection(sample_config_file)

        # sample_config has connection_type: 'normal'
        mock_factory_cls.assert_called_once()
        call_args = mock_factory_cls.call_args
        assert call_args[0][1] == 'normal'

    # --- Dict-based API tests ---

    @patch('pgmonkey.managers.pgconnection_manager.PostgresConnectionFactory')
    def test_get_database_connection_from_dict(self, mock_factory_cls, sample_config):
        mock_conn = MagicMock()
        mock_factory_cls.return_value.get_connection.return_value = mock_conn

        manager = PGConnectionManager()
        result = manager.get_database_connection_from_dict(sample_config, 'pool')

        assert result is mock_conn
        mock_factory_cls.assert_called_once_with(sample_config, 'pool')

    # --- Routing tests ---

    @patch.object(PGConnectionManager, '_get_postgresql_connection_sync')
    def test_normal_routes_to_sync(self, mock_sync, sample_config):
        manager = PGConnectionManager()
        manager._get_connection(sample_config, 'normal')
        mock_sync.assert_called_once_with(sample_config, 'normal')

    @patch.object(PGConnectionManager, '_get_postgresql_connection_sync')
    def test_pool_routes_to_sync(self, mock_sync, sample_config):
        manager = PGConnectionManager()
        manager._get_connection(sample_config, 'pool')
        mock_sync.assert_called_once_with(sample_config, 'pool')

    @pytest.mark.asyncio
    @patch.object(PGConnectionManager, '_get_postgresql_connection_async', new_callable=AsyncMock)
    async def test_async_routes_to_async(self, mock_async, sample_config):
        manager = PGConnectionManager()
        await manager._get_connection(sample_config, 'async')
        mock_async.assert_called_once_with(sample_config, 'async')

    @pytest.mark.asyncio
    @patch.object(PGConnectionManager, '_get_postgresql_connection_async', new_callable=AsyncMock)
    async def test_async_pool_routes_to_async(self, mock_async, sample_config):
        manager = PGConnectionManager()
        await manager._get_connection(sample_config, 'async_pool')
        mock_async.assert_called_once_with(sample_config, 'async_pool')
