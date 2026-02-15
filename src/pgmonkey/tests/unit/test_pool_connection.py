import pytest
from unittest.mock import patch, MagicMock
from pgmonkey.connections.postgres.pool_connection import PGPoolConnection


class TestPGPoolConnectionInit:

    def test_stores_config_and_pool_settings(self):
        conn = PGPoolConnection({'host': 'localhost'}, {'min_size': 2, 'max_size': 10})
        assert conn.config == {'host': 'localhost'}
        assert conn.pool_settings == {'min_size': 2, 'max_size': 10}
        assert conn.pool is None
        assert getattr(conn._local, 'pool_conn_ctx', None) is None

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


class TestPGPoolConnectionContextManager:

    def test_enter_stores_pool_conn_ctx(self):
        """__enter__ should store the pool context manager in thread-local, not discard it."""
        mock_pool = MagicMock()
        mock_pool_ctx = MagicMock()
        mock_raw_conn = MagicMock()
        mock_pool.connection.return_value = mock_pool_ctx
        mock_pool_ctx.__enter__ = MagicMock(return_value=mock_raw_conn)

        conn = PGPoolConnection({'host': 'localhost'})
        conn.pool = mock_pool
        result = conn.__enter__()

        assert conn._local.pool_conn_ctx is mock_pool_ctx
        assert conn._get_conn() is mock_raw_conn
        assert result is conn

    def test_exit_delegates_to_pool_ctx_not_raw_conn(self):
        """__exit__ should call __exit__ on the pool CM (returns conn to pool),
        not on the raw connection (which would close it)."""
        mock_pool_ctx = MagicMock()
        mock_raw_conn = MagicMock()

        conn = PGPoolConnection({'host': 'localhost'})
        conn._local.pool_conn_ctx = mock_pool_ctx
        conn._set_conn(mock_raw_conn)

        conn.__exit__(None, None, None)

        mock_raw_conn.commit.assert_called_once()
        mock_pool_ctx.__exit__.assert_called_once_with(None, None, None)
        # Raw connection's __exit__ should NOT be called
        mock_raw_conn.__exit__.assert_not_called()
        assert conn._get_conn() is None
        assert conn._local.pool_conn_ctx is None

    def test_exit_rollback_on_exception(self):
        """__exit__ should rollback on exception, then delegate to pool CM."""
        mock_pool_ctx = MagicMock()
        mock_raw_conn = MagicMock()

        conn = PGPoolConnection({'host': 'localhost'})
        conn._local.pool_conn_ctx = mock_pool_ctx
        conn._set_conn(mock_raw_conn)

        exc = ValueError("test")
        conn.__exit__(ValueError, exc, None)

        mock_raw_conn.rollback.assert_called_once()
        mock_raw_conn.commit.assert_not_called()
        mock_pool_ctx.__exit__.assert_called_once_with(ValueError, exc, None)

    def test_exit_cleans_up_even_on_commit_error(self):
        """Pool CM cleanup should happen even if commit raises."""
        mock_pool_ctx = MagicMock()
        mock_raw_conn = MagicMock()
        mock_raw_conn.commit.side_effect = Exception("commit failed")

        conn = PGPoolConnection({'host': 'localhost'})
        conn._local.pool_conn_ctx = mock_pool_ctx
        conn._set_conn(mock_raw_conn)

        with pytest.raises(Exception, match="commit failed"):
            conn.__exit__(None, None, None)

        mock_pool_ctx.__exit__.assert_called_once()
        assert conn._get_conn() is None
        assert conn._local.pool_conn_ctx is None


class TestPGPoolConnectionConninfo:

    @patch('pgmonkey.connections.postgres.pool_connection.psycopg_conninfo')
    def test_uses_make_conninfo(self, mock_conninfo):
        mock_conninfo.make_conninfo.return_value = 'host=localhost dbname=test'
        result = PGPoolConnection.construct_conninfo({'host': 'localhost', 'dbname': 'test'})
        mock_conninfo.make_conninfo.assert_called_once_with(host='localhost', dbname='test')
        assert result == 'host=localhost dbname=test'


class TestPGPoolConnectionThreadSafety:
    """Verify that _conn and _pool_conn_ctx are stored in thread-local storage."""

    def test_conn_is_thread_local(self):
        """_get_conn and _set_conn use thread-local storage."""
        conn = PGPoolConnection({'host': 'localhost'})
        assert conn._get_conn() is None
        mock = MagicMock()
        conn._set_conn(mock)
        assert conn._get_conn() is mock
        conn._set_conn(None)
        assert conn._get_conn() is None

    def test_pool_conn_ctx_is_thread_local(self):
        """_pool_conn_ctx must be thread-local to prevent cross-thread corruption."""
        import threading

        conn = PGPoolConnection({'host': 'localhost'})

        # Set up mock pool
        mock_pool = MagicMock()

        def make_ctx():
            ctx = MagicMock()
            raw = MagicMock()
            ctx.__enter__ = MagicMock(return_value=raw)
            ctx.__exit__ = MagicMock(return_value=False)
            return ctx

        mock_pool.connection = MagicMock(side_effect=make_ctx)
        conn.pool = mock_pool

        results = {}

        def thread_work(thread_id):
            """Each thread enters and checks its own pool_conn_ctx."""
            conn.__enter__()
            # Record this thread's pool_conn_ctx
            results[thread_id] = conn._local.pool_conn_ctx
            # Small sleep to let threads overlap
            import time
            time.sleep(0.01)
            conn.__exit__(None, None, None)

        t1 = threading.Thread(target=thread_work, args=(1,))
        t2 = threading.Thread(target=thread_work, args=(2,))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        # Each thread should have gotten its own pool_conn_ctx (not the same object)
        assert results[1] is not results[2]
