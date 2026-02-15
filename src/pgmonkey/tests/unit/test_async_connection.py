import logging
import pytest
from unittest.mock import patch, AsyncMock

pytest.importorskip("pytest_asyncio")

from pgmonkey.connections.postgres.async_connection import PGAsyncConnection


class TestPGAsyncConnectionInit:

    def test_stores_config_and_settings(self):
        conn = PGAsyncConnection({'host': 'localhost'}, {'statement_timeout': '30000'})
        assert conn.config == {'host': 'localhost'}
        assert conn.async_settings == {'statement_timeout': '30000'}
        assert conn.connection is None

    def test_default_async_settings_empty(self):
        conn = PGAsyncConnection({'host': 'localhost'})
        assert conn.async_settings == {}


class TestPGAsyncConnectionConnect:

    @pytest.mark.asyncio
    @patch('pgmonkey.connections.postgres.async_connection.AsyncConnection')
    async def test_creates_connection(self, mock_cls):
        mock_pg = AsyncMock(closed=False)
        mock_pg.execute = AsyncMock()
        mock_cls.connect = AsyncMock(return_value=mock_pg)

        conn = PGAsyncConnection({'host': 'localhost'}, {})
        await conn.connect()

        mock_cls.connect.assert_called_once_with(host='localhost')
        assert conn.connection is mock_pg


class TestPGAsyncConnectionApplySettings:

    @pytest.mark.asyncio
    @patch('pgmonkey.connections.postgres.async_connection.AsyncConnection')
    async def test_issues_set_commands(self, mock_cls):
        mock_pg = AsyncMock(closed=False)
        mock_pg.execute = AsyncMock()
        mock_cls.connect = AsyncMock(return_value=mock_pg)

        settings = {'statement_timeout': '30000', 'lock_timeout': '10000'}
        conn = PGAsyncConnection({'host': 'localhost'}, settings)
        await conn.connect()

        calls = mock_pg.execute.call_args_list
        assert len(calls) == 2
        assert calls[0][0][0] == 'SET statement_timeout = %s'
        assert calls[0][0][1] == ('30000',)
        assert calls[1][0][0] == 'SET lock_timeout = %s'
        assert calls[1][0][1] == ('10000',)

    @pytest.mark.asyncio
    @patch('pgmonkey.connections.postgres.async_connection.AsyncConnection')
    async def test_warns_on_bad_setting(self, mock_cls, caplog):
        mock_pg = AsyncMock(closed=False)
        mock_pg.execute = AsyncMock(side_effect=Exception("bad setting"))
        mock_cls.connect = AsyncMock(return_value=mock_pg)

        conn = PGAsyncConnection({'host': 'localhost'}, {'bad_setting': 'value'})
        with caplog.at_level(logging.WARNING):
            await conn.connect()

        assert "Could not apply setting" in caplog.text


class TestPGAsyncConnectionDisconnect:

    @pytest.mark.asyncio
    @patch('pgmonkey.connections.postgres.async_connection.AsyncConnection')
    async def test_closes_connection(self, mock_cls):
        mock_pg = AsyncMock(closed=False)
        mock_pg.execute = AsyncMock()
        mock_cls.connect = AsyncMock(return_value=mock_pg)

        conn = PGAsyncConnection({'host': 'localhost'}, {})
        await conn.connect()
        await conn.disconnect()

        mock_pg.close.assert_called_once()
        assert conn.connection is None


class TestPGAsyncConnectionCommitRollback:

    @pytest.mark.asyncio
    async def test_commit_noop_when_no_connection(self):
        conn = PGAsyncConnection({'host': 'localhost'})
        await conn.commit()

    @pytest.mark.asyncio
    async def test_rollback_noop_when_no_connection(self):
        conn = PGAsyncConnection({'host': 'localhost'})
        await conn.rollback()
