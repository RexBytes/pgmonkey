import pytest
from unittest.mock import patch, AsyncMock

pytest.importorskip("pytest_asyncio")

from pgmonkey.connections.postgres.async_pool_connection import PGAsyncPoolConnection


class TestPGAsyncPoolConnectionInit:

    def test_stores_config_and_settings(self):
        conn = PGAsyncPoolConnection({'host': 'localhost'}, {'min_size': 2, 'max_size': 10})
        assert conn.config == {'host': 'localhost'}
        assert conn.async_pool_settings == {'min_size': 2, 'max_size': 10}
        assert conn.pool is None

    def test_default_settings_empty(self):
        conn = PGAsyncPoolConnection({'host': 'localhost'})
        assert conn.async_pool_settings == {}


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
    async def test_commit_is_noop(self):
        conn = PGAsyncPoolConnection({'host': 'localhost'})
        await conn.commit()

    @pytest.mark.asyncio
    async def test_rollback_is_noop(self):
        conn = PGAsyncPoolConnection({'host': 'localhost'})
        await conn.rollback()


class TestPGAsyncPoolConnectionConninfo:

    @patch('pgmonkey.connections.postgres.async_pool_connection.psycopg_conninfo')
    def test_uses_make_conninfo(self, mock_conninfo):
        mock_conninfo.make_conninfo.return_value = 'host=localhost'
        result = PGAsyncPoolConnection.construct_conninfo({'host': 'localhost'})
        mock_conninfo.make_conninfo.assert_called_once_with(host='localhost')
        assert result == 'host=localhost'
