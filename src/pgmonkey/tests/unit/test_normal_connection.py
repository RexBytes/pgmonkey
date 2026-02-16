import logging
import pytest
from unittest.mock import patch, MagicMock
from psycopg import sql
from pgmonkey.connections.postgres.normal_connection import PGNormalConnection


class TestPGNormalConnectionInit:

    def test_stores_config(self):
        conn = PGNormalConnection({'host': 'localhost', 'dbname': 'test'})
        assert conn.config == {'host': 'localhost', 'dbname': 'test'}
        assert conn.connection is None

    def test_stores_sync_settings(self):
        settings = {'statement_timeout': '30000'}
        conn = PGNormalConnection({'host': 'localhost'}, sync_settings=settings)
        assert conn.sync_settings == settings

    def test_default_sync_settings_empty(self):
        conn = PGNormalConnection({'host': 'localhost'})
        assert conn.sync_settings == {}


class TestPGNormalConnectionConnect:

    @patch('pgmonkey.connections.postgres.normal_connection.connect')
    def test_creates_connection(self, mock_connect):
        mock_pg_conn = MagicMock(closed=False)
        mock_connect.return_value = mock_pg_conn

        conn = PGNormalConnection({'host': 'localhost'})
        conn.connect()

        mock_connect.assert_called_once_with(autocommit=False, host='localhost')
        assert conn.connection is mock_pg_conn

    @patch('pgmonkey.connections.postgres.normal_connection.connect')
    def test_skips_if_already_connected(self, mock_connect):
        mock_connect.return_value = MagicMock(closed=False)

        conn = PGNormalConnection({'host': 'localhost'})
        conn.connect()
        conn.connect()

        mock_connect.assert_called_once()

    @patch('pgmonkey.connections.postgres.normal_connection.connect')
    def test_autocommit_passed_to_connect(self, mock_connect):
        mock_pg_conn = MagicMock(closed=False)
        mock_connect.return_value = mock_pg_conn

        conn = PGNormalConnection({'host': 'localhost'})
        conn.autocommit = True
        conn.connect()

        mock_connect.assert_called_once_with(autocommit=True, host='localhost')


class TestPGNormalConnectionSyncSettings:

    @patch('pgmonkey.connections.postgres.normal_connection.connect')
    def test_applies_sync_settings_on_connect(self, mock_connect):
        mock_pg_conn = MagicMock(closed=False)
        mock_connect.return_value = mock_pg_conn

        settings = {'statement_timeout': '30000', 'lock_timeout': '10000'}
        conn = PGNormalConnection({'host': 'localhost'}, sync_settings=settings)
        conn.connect()

        calls = mock_pg_conn.execute.call_args_list
        assert len(calls) == 2
        assert calls[0][0][0] == sql.SQL("SET {} = %s").format(sql.Identifier('statement_timeout'))
        assert calls[0][0][1] == ('30000',)
        assert calls[1][0][0] == sql.SQL("SET {} = %s").format(sql.Identifier('lock_timeout'))
        assert calls[1][0][1] == ('10000',)

    @patch('pgmonkey.connections.postgres.normal_connection.connect')
    def test_warns_on_bad_setting(self, mock_connect, caplog):
        mock_pg_conn = MagicMock(closed=False)
        mock_pg_conn.execute.side_effect = Exception("bad setting")
        mock_connect.return_value = mock_pg_conn

        conn = PGNormalConnection({'host': 'localhost'}, sync_settings={'bad': 'value'})
        with caplog.at_level(logging.WARNING):
            conn.connect()

        assert "Could not apply setting" in caplog.text


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

    def test_raises_when_no_connection(self):
        """cursor() should raise a clear error when connection is None."""
        conn = PGNormalConnection({'host': 'localhost'})
        with pytest.raises(Exception, match="No active connection"):
            conn.cursor()


class TestPGNormalConnectionContextManager:

    @patch('pgmonkey.connections.postgres.normal_connection.connect')
    def test_commits_on_success_and_disconnects(self, mock_connect):
        """__exit__ should commit then disconnect to prevent connection leaks."""
        mock_pg_conn = MagicMock(closed=False)
        mock_connect.return_value = mock_pg_conn

        conn = PGNormalConnection({'host': 'localhost'})
        with conn as c:
            assert c is conn

        mock_pg_conn.commit.assert_called_once()
        mock_pg_conn.close.assert_called_once()
        assert conn.connection is None

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

    @patch('pgmonkey.connections.postgres.normal_connection.connect')
    def test_disconnect_called_even_if_commit_raises(self, mock_connect):
        """disconnect() must be called even if commit() raises (e.g. network error)."""
        mock_pg_conn = MagicMock(closed=False)
        mock_pg_conn.commit.side_effect = Exception("connection lost")
        mock_connect.return_value = mock_pg_conn

        conn = PGNormalConnection({'host': 'localhost'})
        with pytest.raises(Exception, match="connection lost"):
            with conn:
                pass

        mock_pg_conn.close.assert_called_once()

    @patch('pgmonkey.connections.postgres.normal_connection.connect')
    def test_disconnect_called_even_if_rollback_raises(self, mock_connect):
        """disconnect() must be called even if rollback() raises (e.g. network error)."""
        mock_pg_conn = MagicMock(closed=False)
        mock_pg_conn.rollback.side_effect = Exception("connection lost")
        mock_connect.return_value = mock_pg_conn

        conn = PGNormalConnection({'host': 'localhost'})
        with pytest.raises(Exception, match="connection lost"):
            with conn:
                raise ValueError("original error")

        mock_pg_conn.close.assert_called_once()


class TestPGNormalConnectionTransaction:

    @patch('pgmonkey.connections.postgres.normal_connection.connect')
    def test_transaction_does_not_disconnect(self, mock_connect):
        """transaction() should not close the connection - lifecycle is managed externally."""
        mock_pg_conn = MagicMock(closed=False)
        mock_connect.return_value = mock_pg_conn

        conn = PGNormalConnection({'host': 'localhost'})
        conn.connect()
        with conn.transaction():
            pass

        mock_pg_conn.commit.assert_called_once()
        mock_pg_conn.close.assert_not_called()
        assert conn.connection is mock_pg_conn

    @patch('pgmonkey.connections.postgres.normal_connection.connect')
    def test_transaction_rollbacks_on_error(self, mock_connect):
        mock_pg_conn = MagicMock(closed=False)
        mock_connect.return_value = mock_pg_conn

        conn = PGNormalConnection({'host': 'localhost'})
        conn.connect()
        with pytest.raises(ValueError):
            with conn.transaction():
                raise ValueError("test")

        mock_pg_conn.rollback.assert_called_once()
        mock_pg_conn.commit.assert_not_called()
        mock_pg_conn.close.assert_not_called()

    @patch('pgmonkey.connections.postgres.normal_connection.connect')
    def test_transaction_yields_self(self, mock_connect):
        mock_pg_conn = MagicMock(closed=False)
        mock_connect.return_value = mock_pg_conn

        conn = PGNormalConnection({'host': 'localhost'})
        conn.connect()
        with conn.transaction() as tx:
            assert tx is conn


class TestPGNormalConnectionTestConnection:

    @patch('pgmonkey.connections.postgres.normal_connection.connect')
    def test_logs_success(self, mock_connect, caplog):
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (1,)
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_pg_conn = MagicMock(closed=False)
        mock_pg_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_pg_conn

        conn = PGNormalConnection({'host': 'localhost'})
        conn.connect()
        with caplog.at_level(logging.INFO):
            conn.test_connection()

        assert "Connection successful" in caplog.text
