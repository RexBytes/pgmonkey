import pytest
from unittest.mock import patch, MagicMock
from pgmonkey.connections.postgres.pool_connection import PGPoolConnection


class TestPGPoolConnectionInit:

    def test_stores_config_and_pool_settings(self):
        conn = PGPoolConnection({'host': 'localhost'}, {'min_size': 2, 'max_size': 10})
        assert conn.config == {'host': 'localhost'}
        assert conn.pool_settings == {'min_size': 2, 'max_size': 10}
        assert conn.pool is None
        assert conn._conn is None

    def test_default_pool_settings_empty(self):
        conn = PGPoolConnection({'host': 'localhost'})
        assert conn.pool_settings == {}


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
        conn._conn = mock_conn
        conn.commit()
        mock_conn.commit.assert_called_once()

    def test_rollback_delegates_to_pool_conn(self):
        mock_conn = MagicMock()
        conn = PGPoolConnection({'host': 'localhost'})
        conn._conn = mock_conn
        conn.rollback()
        mock_conn.rollback.assert_called_once()


class TestPGPoolConnectionConninfo:

    @patch('pgmonkey.connections.postgres.pool_connection.psycopg_conninfo')
    def test_uses_make_conninfo(self, mock_conninfo):
        mock_conninfo.make_conninfo.return_value = 'host=localhost dbname=test'
        result = PGPoolConnection.construct_conninfo({'host': 'localhost', 'dbname': 'test'})
        mock_conninfo.make_conninfo.assert_called_once_with(host='localhost', dbname='test')
        assert result == 'host=localhost dbname=test'
