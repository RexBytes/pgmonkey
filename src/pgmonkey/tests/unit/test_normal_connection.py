import pytest
from unittest.mock import patch, MagicMock
from pgmonkey.connections.postgres.normal_connection import PGNormalConnection


class TestPGNormalConnectionInit:

    def test_stores_config(self):
        conn = PGNormalConnection({'host': 'localhost', 'dbname': 'test'})
        assert conn.config == {'host': 'localhost', 'dbname': 'test'}
        assert conn.connection is None


class TestPGNormalConnectionConnect:

    @patch('pgmonkey.connections.postgres.normal_connection.connect')
    def test_creates_connection(self, mock_connect):
        mock_pg_conn = MagicMock(closed=False)
        mock_connect.return_value = mock_pg_conn

        conn = PGNormalConnection({'host': 'localhost'})
        conn.connect()

        mock_connect.assert_called_once_with(host='localhost')
        assert conn.connection is mock_pg_conn

    @patch('pgmonkey.connections.postgres.normal_connection.connect')
    def test_skips_if_already_connected(self, mock_connect):
        mock_connect.return_value = MagicMock(closed=False)

        conn = PGNormalConnection({'host': 'localhost'})
        conn.connect()
        conn.connect()

        mock_connect.assert_called_once()


class TestPGNormalConnectionDisconnect:

    @patch('pgmonkey.connections.postgres.normal_connection.connect')
    def test_closes_connection(self, mock_connect):
        mock_pg_conn = MagicMock(closed=False)
        mock_connect.return_value = mock_pg_conn

        conn = PGNormalConnection({'host': 'localhost'})
        conn.connect()
        conn.disconnect()

        mock_pg_conn.close.assert_called_once()
        assert conn.connection is None

    def test_noop_when_no_connection(self):
        conn = PGNormalConnection({'host': 'localhost'})
        conn.disconnect()


class TestPGNormalConnectionCommitRollback:

    @patch('pgmonkey.connections.postgres.normal_connection.connect')
    def test_commit(self, mock_connect):
        mock_pg_conn = MagicMock(closed=False)
        mock_connect.return_value = mock_pg_conn

        conn = PGNormalConnection({'host': 'localhost'})
        conn.connect()
        conn.commit()

        mock_pg_conn.commit.assert_called_once()

    @patch('pgmonkey.connections.postgres.normal_connection.connect')
    def test_rollback(self, mock_connect):
        mock_pg_conn = MagicMock(closed=False)
        mock_connect.return_value = mock_pg_conn

        conn = PGNormalConnection({'host': 'localhost'})
        conn.connect()
        conn.rollback()

        mock_pg_conn.rollback.assert_called_once()

    def test_commit_noop_when_no_connection(self):
        conn = PGNormalConnection({'host': 'localhost'})
        conn.commit()

    def test_rollback_noop_when_no_connection(self):
        conn = PGNormalConnection({'host': 'localhost'})
        conn.rollback()


class TestPGNormalConnectionCursor:

    @patch('pgmonkey.connections.postgres.normal_connection.connect')
    def test_returns_cursor(self, mock_connect):
        mock_cursor = MagicMock()
        mock_pg_conn = MagicMock(closed=False)
        mock_pg_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_pg_conn

        conn = PGNormalConnection({'host': 'localhost'})
        conn.connect()
        assert conn.cursor() is mock_cursor


class TestPGNormalConnectionContextManager:

    @patch('pgmonkey.connections.postgres.normal_connection.connect')
    def test_commits_on_success(self, mock_connect):
        mock_pg_conn = MagicMock(closed=False)
        mock_connect.return_value = mock_pg_conn

        conn = PGNormalConnection({'host': 'localhost'})
        with conn as c:
            assert c is conn

        mock_pg_conn.commit.assert_called_once()
        mock_pg_conn.close.assert_called_once()

    @patch('pgmonkey.connections.postgres.normal_connection.connect')
    def test_rollbacks_on_error(self, mock_connect):
        mock_pg_conn = MagicMock(closed=False)
        mock_connect.return_value = mock_pg_conn

        conn = PGNormalConnection({'host': 'localhost'})
        with pytest.raises(ValueError):
            with conn:
                raise ValueError("test")

        mock_pg_conn.rollback.assert_called_once()
        mock_pg_conn.commit.assert_not_called()


class TestPGNormalConnectionTestConnection:

    @patch('pgmonkey.connections.postgres.normal_connection.connect')
    def test_prints_success(self, mock_connect, capsys):
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (1,)
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_pg_conn = MagicMock(closed=False)
        mock_pg_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_pg_conn

        conn = PGNormalConnection({'host': 'localhost'})
        conn.connect()
        conn.test_connection()

        assert "Connection successful" in capsys.readouterr().out
