"""Unit tests for PGConnectionManager connection caching, atexit cleanup,
and connection type context manager behavior.

These tests use mocks - no real database required.
"""

import asyncio
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from pgmonkey.managers.pgconnection_manager import PGConnectionManager
from pgmonkey.connections.postgres.async_pool_connection import PGAsyncPoolConnection


# -- Helpers ----------------------------------------------------------------

def _sync_config(conn_type='pool'):
    return {
        'postgresql': {
            'connection_type': conn_type,
            'connection_settings': {
                'user': 'test',
                'password': 'test',
                'host': 'localhost',
                'port': 5432,
                'dbname': 'testdb',
            },
            'pool_settings': {'min_size': 1, 'max_size': 5},
        }
    }


def _async_config(conn_type='async_pool'):
    return {
        'postgresql': {
            'connection_type': conn_type,
            'connection_settings': {
                'user': 'test',
                'password': 'test',
                'host': 'localhost',
                'port': 5432,
                'dbname': 'testdb',
            },
            'async_pool_settings': {'min_size': 1, 'max_size': 5},
        }
    }


def _make_sync_connection():
    """Create a mock sync connection object."""
    conn = MagicMock()
    conn.connection_type = 'pool'
    conn.disconnect = MagicMock()
    conn.connect = MagicMock()
    return conn


def _make_async_connection():
    """Create a mock async connection object."""
    conn = MagicMock()
    conn.connection_type = 'async_pool'
    conn.disconnect = AsyncMock()
    conn.connect = AsyncMock()
    return conn


# -- Sync caching tests ----------------------------------------------------

class TestSyncCaching:

    @patch.object(PGConnectionManager, '_get_postgresql_connection_sync')
    def test_same_config_returns_cached_instance(self, mock_get_sync):
        mock_conn = _make_sync_connection()
        mock_get_sync.return_value = mock_conn
        manager = PGConnectionManager()
        config = _sync_config()

        conn1 = manager.get_database_connection_from_dict(config)
        conn2 = manager.get_database_connection_from_dict(config)

        assert conn1 is conn2
        assert mock_get_sync.call_count == 1  # Only created once

    @patch.object(PGConnectionManager, '_get_postgresql_connection_sync')
    def test_different_configs_get_different_cache_entries(self, mock_get_sync):
        mock_get_sync.side_effect = [_make_sync_connection(), _make_sync_connection()]
        manager = PGConnectionManager()

        config_a = _sync_config('pool')
        config_b = _sync_config('normal')

        conn_a = manager.get_database_connection_from_dict(config_a)
        conn_b = manager.get_database_connection_from_dict(config_b)

        assert conn_a is not conn_b
        assert manager.cache_info['size'] == 2

    @patch.object(PGConnectionManager, '_get_postgresql_connection_sync')
    def test_force_reload_disconnects_old_and_creates_new(self, mock_get_sync):
        old_conn = _make_sync_connection()
        new_conn = _make_sync_connection()
        mock_get_sync.side_effect = [old_conn, new_conn]
        manager = PGConnectionManager()
        config = _sync_config()

        conn1 = manager.get_database_connection_from_dict(config)
        assert conn1 is old_conn

        conn2 = manager.get_database_connection_from_dict(config, force_reload=True)
        assert conn2 is new_conn
        assert conn2 is not conn1
        old_conn.disconnect.assert_called_once()

    @patch.object(PGConnectionManager, '_get_postgresql_connection_sync')
    def test_cache_info(self, mock_get_sync):
        mock_conn = _make_sync_connection()
        mock_get_sync.return_value = mock_conn
        manager = PGConnectionManager()

        assert manager.cache_info['size'] == 0
        manager.get_database_connection_from_dict(_sync_config())
        info = manager.cache_info
        assert info['size'] == 1
        assert 'pool' in info['connection_types'].values()

    @patch.object(PGConnectionManager, '_get_postgresql_connection_sync')
    def test_clear_cache_disconnects_all(self, mock_get_sync):
        conn1 = _make_sync_connection()
        conn2 = _make_sync_connection()
        mock_get_sync.side_effect = [conn1, conn2]
        manager = PGConnectionManager()

        manager.get_database_connection_from_dict(_sync_config('pool'))
        manager.get_database_connection_from_dict(_sync_config('normal'))
        assert manager.cache_info['size'] == 2

        manager.clear_cache()
        assert manager.cache_info['size'] == 0
        conn1.disconnect.assert_called_once()
        conn2.disconnect.assert_called_once()

    @patch.object(PGConnectionManager, '_get_postgresql_connection_sync')
    def test_connection_type_override(self, mock_get_sync):
        mock_conn = _make_sync_connection()
        mock_get_sync.return_value = mock_conn
        manager = PGConnectionManager()

        # Config says 'pool' but we override to 'normal'
        conn = manager.get_database_connection_from_dict(_sync_config('pool'), connection_type='normal')
        assert conn is mock_conn
        # Verify factory was called with the override type
        mock_get_sync.assert_called_once()

    @patch.object(PGConnectionManager, '_get_postgresql_connection_sync')
    def test_different_connection_type_override_gets_separate_cache_entry(self, mock_get_sync):
        """Same config dict with different connection_type overrides should NOT share cache."""
        conn_normal = _make_sync_connection()
        conn_normal.connection_type = 'normal'
        conn_pool = _make_sync_connection()
        conn_pool.connection_type = 'pool'
        mock_get_sync.side_effect = [conn_normal, conn_pool]
        manager = PGConnectionManager()
        config = _sync_config('pool')

        # First call with override to 'normal'
        result1 = manager.get_database_connection_from_dict(config, connection_type='normal')
        assert result1 is conn_normal

        # Second call with default type ('pool' from config)
        result2 = manager.get_database_connection_from_dict(config)
        assert result2 is conn_pool

        # They must be different connections
        assert result1 is not result2
        assert manager.cache_info['size'] == 2


# -- Async caching tests ---------------------------------------------------

class TestAsyncCaching:

    @pytest.mark.asyncio
    async def test_same_config_returns_cached_async_instance(self):
        mock_conn = _make_async_connection()
        manager = PGConnectionManager()
        config = _async_config()

        with patch.object(manager, '_get_postgresql_connection_async', new_callable=AsyncMock, return_value=mock_conn):
            conn1 = await manager.get_database_connection_from_dict(config)
            conn2 = await manager.get_database_connection_from_dict(config)

        assert conn1 is conn2

    @pytest.mark.asyncio
    async def test_force_reload_disconnects_old_async(self):
        old_conn = _make_async_connection()
        new_conn = _make_async_connection()
        manager = PGConnectionManager()
        config = _async_config()

        with patch.object(manager, '_get_postgresql_connection_async', new_callable=AsyncMock,
                          side_effect=[old_conn, new_conn]):
            conn1 = await manager.get_database_connection_from_dict(config)
            assert conn1 is old_conn

            conn2 = await manager.get_database_connection_from_dict(config, force_reload=True)
            assert conn2 is new_conn
            old_conn.disconnect.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_clear_cache_async(self):
        mock_conn = _make_async_connection()
        manager = PGConnectionManager()
        config = _async_config()

        with patch.object(manager, '_get_postgresql_connection_async', new_callable=AsyncMock, return_value=mock_conn):
            await manager.get_database_connection_from_dict(config)

        assert manager.cache_info['size'] == 1
        await manager.clear_cache_async()
        assert manager.cache_info['size'] == 0
        mock_conn.disconnect.assert_awaited_once()


# -- atexit hook tests ------------------------------------------------------

class TestAtexitCleanup:

    @patch.object(PGConnectionManager, '_get_postgresql_connection_sync')
    def test_atexit_registered_on_first_connection(self, mock_get_sync):
        mock_get_sync.return_value = _make_sync_connection()
        manager = PGConnectionManager()

        assert not manager._atexit_registered
        manager.get_database_connection_from_dict(_sync_config())
        assert manager._atexit_registered

    @patch.object(PGConnectionManager, '_get_postgresql_connection_sync')
    def test_cleanup_at_exit_closes_sync_connections(self, mock_get_sync):
        mock_conn = _make_sync_connection()
        mock_get_sync.return_value = mock_conn
        manager = PGConnectionManager()

        manager.get_database_connection_from_dict(_sync_config())
        manager._cleanup_at_exit()

        mock_conn.disconnect.assert_called_once()
        assert manager.cache_info['size'] == 0

    @patch.object(PGConnectionManager, '_get_postgresql_connection_sync')
    def test_cleanup_at_exit_handles_disconnect_errors(self, mock_get_sync):
        mock_conn = _make_sync_connection()
        mock_conn.disconnect.side_effect = RuntimeError("connection already closed")
        mock_get_sync.return_value = mock_conn
        manager = PGConnectionManager()

        manager.get_database_connection_from_dict(_sync_config())
        # Should not raise
        manager._cleanup_at_exit()
        assert manager.cache_info['size'] == 0


# -- Config hash tests ------------------------------------------------------

class TestConfigHash:

    def test_same_config_produces_same_hash(self):
        config = _sync_config()
        h1 = PGConnectionManager._config_hash(config)
        h2 = PGConnectionManager._config_hash(config)
        assert h1 == h2

    def test_different_config_produces_different_hash(self):
        config_a = _sync_config('pool')
        config_b = _sync_config('normal')
        h1 = PGConnectionManager._config_hash(config_a)
        h2 = PGConnectionManager._config_hash(config_b)
        assert h1 != h2

    def test_key_order_does_not_matter(self):
        config_a = {'postgresql': {'connection_type': 'pool', 'connection_settings': {'host': 'a', 'port': 5432}}}
        config_b = {'postgresql': {'connection_settings': {'port': 5432, 'host': 'a'}, 'connection_type': 'pool'}}
        assert PGConnectionManager._config_hash(config_a) == PGConnectionManager._config_hash(config_b)


# -- Async pool context manager tests --------------------------------------

class TestAsyncPoolContextManager:
    """Verify async pool __aenter__/__aexit__ acquires/returns a connection
    from the pool instead of closing the entire pool."""

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
        """cursor() should use _conn when inside async with, not acquire new."""
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
