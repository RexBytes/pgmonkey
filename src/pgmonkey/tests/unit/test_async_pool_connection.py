import pytest
from unittest.mock import patch, AsyncMock, MagicMock

pytest.importorskip("pytest_asyncio")

from pgmonkey.connections.postgres.async_pool_connection import (
    PGAsyncPoolConnection, _async_pool_conn, _async_pool_conn_ctx,
)


class TestPGAsyncPoolConnectionInit:

    def test_stores_config_and_settings(self):
        conn = PGAsyncPoolConnection({'host': 'localhost'}, {'min_size': 2, 'max_size': 10})
        assert conn.config == {'host': 'localhost'}
        assert conn.async_pool_settings == {'min_size': 2, 'max_size': 10}
        assert conn.async_settings == {}
        assert conn.pool is None

    def test_stores_async_settings(self):
        conn = PGAsyncPoolConnection(
            {'host': 'localhost'},
            {'min_size': 2},
            {'statement_timeout': '30000'},
        )
        assert conn.async_settings == {'statement_timeout': '30000'}

    def test_default_settings_empty(self):
        conn = PGAsyncPoolConnection({'host': 'localhost'})
        assert conn.async_pool_settings == {}
        assert conn.async_settings == {}

    def test_no_instance_conn_attribute(self):
        """_conn is now stored in ContextVar, not on the instance."""
        conn = PGAsyncPoolConnection({'host': 'localhost'})
        assert not hasattr(conn, '_conn')
        assert not hasattr(conn, '_pool_conn_ctx')


class TestPGAsyncPoolConnectionConnect:

    @pytest.mark.asyncio
    @patch('pgmonkey.connections.postgres.async_pool_connection.psycopg_conninfo')
    @patch('pgmonkey.connections.postgres.async_pool_connection.AsyncConnectionPool')
    async def test_creates_pool_and_opens(self, mock_pool_cls, mock_conninfo):
        mock_conninfo.make_conninfo.return_value = 'host=localhost'
        mock_pool = AsyncMock()
        mock_pool_cls.return_value = mock_pool

        conn = PGAsyncPoolConnection({'host': 'localhost'}, {'min_size': 2})
        await conn.connect()

        mock_pool_cls.assert_called_once_with(conninfo='host=localhost', min_size=2)
        mock_pool.open.assert_called_once()


class TestPGAsyncPoolConnectionDisconnect:

    @pytest.mark.asyncio
    @patch('pgmonkey.connections.postgres.async_pool_connection.psycopg_conninfo')
    @patch('pgmonkey.connections.postgres.async_pool_connection.AsyncConnectionPool')
    async def test_closes_pool(self, mock_pool_cls, mock_conninfo):
        mock_conninfo.make_conninfo.return_value = 'conninfo'
        mock_pool = AsyncMock()
        mock_pool_cls.return_value = mock_pool

        conn = PGAsyncPoolConnection({'host': 'localhost'})
        await conn.connect()
        await conn.disconnect()

        mock_pool.close.assert_called_once()
        assert conn.pool is None


class TestPGAsyncPoolConnectionCommitRollback:

    @pytest.mark.asyncio
    async def test_commit_is_noop_when_no_contextvar(self):
        """commit() is a no-op when no connection is stored in ContextVar."""
        conn = PGAsyncPoolConnection({'host': 'localhost'})
        await conn.commit()

    @pytest.mark.asyncio
    async def test_rollback_is_noop_when_no_contextvar(self):
        conn = PGAsyncPoolConnection({'host': 'localhost'})
        await conn.rollback()


class TestPGAsyncPoolConnectionConninfo:

    @patch('pgmonkey.connections.postgres.async_pool_connection.psycopg_conninfo')
    def test_uses_make_conninfo(self, mock_conninfo):
        mock_conninfo.make_conninfo.return_value = 'host=localhost'
        result = PGAsyncPoolConnection.construct_conninfo({'host': 'localhost'})
        mock_conninfo.make_conninfo.assert_called_once_with(host='localhost')
        assert result == 'host=localhost'


class TestPGAsyncPoolConnectionContextVar:
    """Verify that _conn is stored in ContextVar, not on the instance."""

    @pytest.mark.asyncio
    async def test_contextvar_used_for_conn(self):
        """__aenter__ stores connection in ContextVar, __aexit__ clears it."""
        mock_inner_conn = MagicMock()
        mock_inner_conn.commit = AsyncMock()
        mock_inner_conn.rollback = AsyncMock()

        mock_pool_ctx = AsyncMock()
        mock_pool_ctx.__aenter__ = AsyncMock(return_value=mock_inner_conn)
        mock_pool_ctx.__aexit__ = AsyncMock(return_value=False)

        pool_conn = PGAsyncPoolConnection({'host': 'localhost'})
        pool_conn.pool = MagicMock()
        pool_conn.pool.connection = MagicMock(return_value=mock_pool_ctx)

        # Before entering: no connection in ContextVar
        assert _async_pool_conn.get() is None

        async with pool_conn:
            # Inside context: connection is in ContextVar
            assert _async_pool_conn.get() is mock_inner_conn

        # After exiting: ContextVar cleared
        assert _async_pool_conn.get() is None

    @pytest.mark.asyncio
    async def test_context_manager_does_not_close_pool(self):
        """async with pool: should return connection to pool, not close it."""
        mock_inner_conn = MagicMock()
        mock_inner_conn.commit = AsyncMock()
        mock_inner_conn.rollback = AsyncMock()

        mock_pool_ctx = AsyncMock()
        mock_pool_ctx.__aenter__ = AsyncMock(return_value=mock_inner_conn)
        mock_pool_ctx.__aexit__ = AsyncMock(return_value=False)

        pool_conn = PGAsyncPoolConnection({'host': 'localhost'})
        pool_conn.pool = MagicMock()
        pool_conn.pool.connection = MagicMock(return_value=mock_pool_ctx)

        async with pool_conn:
            pass

        # Pool must NOT be closed
        assert pool_conn.pool is not None
        pool_conn.pool.close.assert_not_called()
        # Connection returned via pool context manager exit
        mock_pool_ctx.__aexit__.assert_awaited_once()
        # Commit on clean exit
        mock_inner_conn.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_context_manager_rollback_on_exception(self):
        """async with pool: should rollback on exception, still return connection."""
        mock_inner_conn = MagicMock()
        mock_inner_conn.commit = AsyncMock()
        mock_inner_conn.rollback = AsyncMock()

        mock_pool_ctx = AsyncMock()
        mock_pool_ctx.__aenter__ = AsyncMock(return_value=mock_inner_conn)
        mock_pool_ctx.__aexit__ = AsyncMock(return_value=False)

        pool_conn = PGAsyncPoolConnection({'host': 'localhost'})
        pool_conn.pool = MagicMock()
        pool_conn.pool.connection = MagicMock(return_value=mock_pool_ctx)

        with pytest.raises(ValueError):
            async with pool_conn:
                raise ValueError("test error")

        # Pool must NOT be closed
        assert pool_conn.pool is not None
        # Rollback on exception, not commit
        mock_inner_conn.rollback.assert_awaited_once()
        mock_inner_conn.commit.assert_not_awaited()
        # Connection still returned to pool
        mock_pool_ctx.__aexit__.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_context_manager_reusable(self):
        """Pool should be reusable across multiple async with blocks."""
        mock_inner_conn = MagicMock()
        mock_inner_conn.commit = AsyncMock()
        mock_inner_conn.rollback = AsyncMock()

        def make_ctx():
            ctx = AsyncMock()
            ctx.__aenter__ = AsyncMock(return_value=mock_inner_conn)
            ctx.__aexit__ = AsyncMock(return_value=False)
            return ctx

        pool_conn = PGAsyncPoolConnection({'host': 'localhost'})
        pool_conn.pool = MagicMock()
        pool_conn.pool.connection = MagicMock(side_effect=[make_ctx(), make_ctx()])

        # First use
        async with pool_conn:
            pass

        # Second use - pool should still be alive
        async with pool_conn:
            pass

        assert pool_conn.pool is not None
        assert pool_conn.pool.connection.call_count == 2

    @pytest.mark.asyncio
    async def test_cursor_uses_acquired_conn_inside_context(self):
        """cursor() should use ContextVar conn when inside async with, not acquire new."""
        mock_cursor = AsyncMock()
        mock_inner_conn = MagicMock()
        mock_inner_conn.commit = AsyncMock()
        mock_inner_conn.cursor = MagicMock(return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=mock_cursor),
            __aexit__=AsyncMock(return_value=False),
        ))

        mock_pool_ctx = AsyncMock()
        mock_pool_ctx.__aenter__ = AsyncMock(return_value=mock_inner_conn)
        mock_pool_ctx.__aexit__ = AsyncMock(return_value=False)

        pool_conn = PGAsyncPoolConnection({'host': 'localhost'})
        pool_conn.pool = MagicMock()
        pool_conn.pool.connection = MagicMock(return_value=mock_pool_ctx)

        async with pool_conn:
            async with pool_conn.cursor() as cur:
                assert cur is mock_cursor

        # pool.connection() called once (for __aenter__), not again for cursor()
        pool_conn.pool.connection.assert_called_once()

    @pytest.mark.asyncio
    async def test_transaction_yields_self(self):
        """transaction() should yield self for consistency with sync types."""
        mock_inner_conn = MagicMock()
        mock_inner_conn.commit = AsyncMock()
        mock_inner_conn.transaction = MagicMock(return_value=AsyncMock(
            __aenter__=AsyncMock(),
            __aexit__=AsyncMock(return_value=False),
        ))

        mock_pool_ctx = AsyncMock()
        mock_pool_ctx.__aenter__ = AsyncMock(return_value=mock_inner_conn)
        mock_pool_ctx.__aexit__ = AsyncMock(return_value=False)

        pool_conn = PGAsyncPoolConnection({'host': 'localhost'})
        pool_conn.pool = MagicMock()
        pool_conn.pool.connection = MagicMock(return_value=mock_pool_ctx)

        async with pool_conn:
            async with pool_conn.transaction() as tx:
                assert tx is pool_conn
