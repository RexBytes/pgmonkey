import pytest
from unittest.mock import patch, MagicMock
from pgmonkey.connections.postgres.pool_connection import PGPoolConnection


class TestPGPoolConnectionInit:

    def test_stores_config_and_pool_settings(self):
        conn = PGPoolConnection({'host': 'localhost'}, {'min_size': 2, 'max_size': 10})
        assert conn.config == {'host': 'localhost'}
        assert conn.pool_settings == {'min_size': 2, 'max_size': 10}
        assert conn.pool is None

    def test_default_pool_settings_empty(self):
        conn = PGPoolConnection({'host': 'localhost'})
        assert conn.pool_settings == {}

    def test_stores_sync_settings(self):
        conn = PGPoolConnection({'host': 'localhost'}, sync_settings={'statement_timeout': '30000'})
        assert conn.sync_settings == {'statement_timeout': '30000'}

    def test_default_sync_settings_empty(self):
        conn = PGPoolConnection({'host': 'localhost'})
        assert conn.sync_settings == {}

    def test_thread_local_initialized(self):
        conn = PGPoolConnection({'host': 'localhost'})
        assert conn._get_conn() is None


class TestPGPoolConnectionConnect:

    @patch('pgmonkey.connections.postgres.pool_connection.psycopg_conninfo')
    @patch('pgmonkey.connections.postgres.pool_connection.ConnectionPool')
    def test_creates_pool(self, mock_pool_cls, mock_conninfo):
        mock_conninfo.make_conninfo.return_value = 'host=localhost'
        conn = PGPoolConnection({'host': 'localhost'}, {'min_size': 2})
        conn.connect()

        mock_pool_cls.assert_called_once_with(conninfo='host=localhost', min_size=2)
        assert conn.pool is not None

    @patch('pgmonkey.connections.postgres.pool_connection.psycopg_conninfo')
    @patch('pgmonkey.connections.postgres.pool_connection.ConnectionPool')
    def test_idempotent(self, mock_pool_cls, mock_conninfo):
        mock_conninfo.make_conninfo.return_value = 'conninfo'
        conn = PGPoolConnection({'host': 'localhost'})
        conn.connect()
        conn.connect()
        mock_pool_cls.assert_called_once()

    @patch('pgmonkey.connections.postgres.pool_connection.psycopg_conninfo')
    @patch('pgmonkey.connections.postgres.pool_connection.ConnectionPool')
    def test_sync_settings_sets_configure_callback(self, mock_pool_cls, mock_conninfo):
        mock_conninfo.make_conninfo.return_value = 'host=localhost'
        conn = PGPoolConnection(
            {'host': 'localhost'}, {'min_size': 2},
            sync_settings={'statement_timeout': '30000'}
        )
        conn.connect()

        call_kwargs = mock_pool_cls.call_args[1]
        assert 'configure' in call_kwargs
        assert callable(call_kwargs['configure'])


class TestPGPoolConnectionDisconnect:

    @patch('pgmonkey.connections.postgres.pool_connection.psycopg_conninfo')
    @patch('pgmonkey.connections.postgres.pool_connection.ConnectionPool')
    def test_closes_pool(self, mock_pool_cls, mock_conninfo):
        mock_conninfo.make_conninfo.return_value = 'conninfo'
        conn = PGPoolConnection({'host': 'localhost'})
        conn.connect()
        conn.disconnect()

        mock_pool_cls.return_value.close.assert_called_once()
        assert conn.pool is None

    def test_noop_when_no_pool(self):
        conn = PGPoolConnection({'host': 'localhost'})
        conn.disconnect()


class TestPGPoolConnectionCursorCommitRollback:

    def test_cursor_raises_without_active_connection(self):
        conn = PGPoolConnection({'host': 'localhost'})
        with pytest.raises(Exception, match="No active connection"):
            conn.cursor()

    def test_commit_noop_without_connection(self):
        conn = PGPoolConnection({'host': 'localhost'})
        conn.commit()

    def test_rollback_noop_without_connection(self):
        conn = PGPoolConnection({'host': 'localhost'})
        conn.rollback()

    def test_commit_delegates_to_pool_conn(self):
        mock_conn = MagicMock()
        conn = PGPoolConnection({'host': 'localhost'})
        conn._set_conn(mock_conn)
        conn.commit()
        mock_conn.commit.assert_called_once()

    def test_rollback_delegates_to_pool_conn(self):
        mock_conn = MagicMock()
        conn = PGPoolConnection({'host': 'localhost'})
        conn._set_conn(mock_conn)
        conn.rollback()
        mock_conn.rollback.assert_called_once()


class TestPGPoolConnectionCheckOnCheckout:

    @patch('pgmonkey.connections.postgres.pool_connection.psycopg_conninfo')
    @patch('pgmonkey.connections.postgres.pool_connection.ConnectionPool')
    def test_check_on_checkout_sets_check_callback(self, mock_pool_cls, mock_conninfo):
        mock_conninfo.make_conninfo.return_value = 'host=localhost'
        conn = PGPoolConnection({'host': 'localhost'}, {'min_size': 2, 'check_on_checkout': True})
        conn.connect()

        call_kwargs = mock_pool_cls.call_args[1]
        assert 'check' in call_kwargs
        assert callable(call_kwargs['check'])
        assert 'check_on_checkout' not in call_kwargs

    @patch('pgmonkey.connections.postgres.pool_connection.psycopg_conninfo')
    @patch('pgmonkey.connections.postgres.pool_connection.ConnectionPool')
    def test_check_on_checkout_false_no_callback(self, mock_pool_cls, mock_conninfo):
        mock_conninfo.make_conninfo.return_value = 'host=localhost'
        conn = PGPoolConnection({'host': 'localhost'}, {'min_size': 2, 'check_on_checkout': False})
        conn.connect()

        call_kwargs = mock_pool_cls.call_args[1]
        assert 'check' not in call_kwargs
        assert 'check_on_checkout' not in call_kwargs


class TestPGPoolConnectionConninfo:

    @patch('pgmonkey.connections.postgres.pool_connection.psycopg_conninfo')
    def test_uses_make_conninfo(self, mock_conninfo):
        mock_conninfo.make_conninfo.return_value = 'host=localhost dbname=test'
        result = PGPoolConnection.construct_conninfo({'host': 'localhost', 'dbname': 'test'})
        mock_conninfo.make_conninfo.assert_called_once_with(host='localhost', dbname='test')
        assert result == 'host=localhost dbname=test'


class TestPGPoolConnectionThreadSafety:
    """Verify that _conn is stored in thread-local storage."""

    def test_conn_is_thread_local(self):
        """_get_conn and _set_conn use thread-local storage."""
        conn = PGPoolConnection({'host': 'localhost'})
        assert conn._get_conn() is None
        mock = MagicMock()
        conn._set_conn(mock)
        assert conn._get_conn() is mock
        conn._set_conn(None)
        assert conn._get_conn() is None
