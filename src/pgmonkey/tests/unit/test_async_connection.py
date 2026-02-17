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

    def test_default_autocommit_none(self):
        conn = PGAsyncConnection({'host': 'localhost'})
        assert conn.autocommit is None


class TestPGAsyncConnectionConnect:

    @pytest.mark.asyncio
    @patch('pgmonkey.connections.postgres.async_connection.AsyncConnection')
    async def test_creates_connection(self, mock_cls):
        mock_pg = AsyncMock(closed=False)
        mock_pg.execute = AsyncMock()
        mock_cls.connect = AsyncMock(return_value=mock_pg)

        conn = PGAsyncConnection({'host': 'localhost'}, {})
        await conn.connect()

        mock_cls.connect.assert_called_once_with(autocommit=False, host='localhost')
        assert conn.connection is mock_pg

    @pytest.mark.asyncio
    @patch('pgmonkey.connections.postgres.async_connection.AsyncConnection')
    async def test_autocommit_passed_to_connect(self, mock_cls):
        mock_pg = AsyncMock(closed=False)
        mock_pg.execute = AsyncMock()
        mock_cls.connect = AsyncMock(return_value=mock_pg)

        conn = PGAsyncConnection({'host': 'localhost'}, {})
        conn.autocommit = True
        await conn.connect()

        mock_cls.connect.assert_called_once_with(autocommit=True, host='localhost')


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
        # SET statements now use sql.SQL/sql.Identifier for safe identifier quoting
        assert calls[0][0][0].as_string(None) == 'SET "statement_timeout" = \'30000\''
        assert calls[1][0][0].as_string(None) == 'SET "lock_timeout" = \'10000\''

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


class TestPGAsyncConnectionContextManager:

    @pytest.mark.asyncio
    @patch('pgmonkey.connections.postgres.async_connection.AsyncConnection')
    async def test_aexit_commits_and_disconnects(self, mock_cls):
        """__aexit__ should commit then disconnect to prevent connection leaks."""
        mock_pg = AsyncMock(closed=False)
        mock_pg.execute = AsyncMock()
        mock_pg.commit = AsyncMock()
        mock_cls.connect = AsyncMock(return_value=mock_pg)

        conn = PGAsyncConnection({'host': 'localhost'}, {})
        async with conn:
            pass

        mock_pg.commit.assert_awaited_once()
        mock_pg.close.assert_awaited_once()
        assert conn.connection is None

    @pytest.mark.asyncio
    @patch('pgmonkey.connections.postgres.async_connection.AsyncConnection')
    async def test_aexit_rollback_on_error(self, mock_cls):
        mock_pg = AsyncMock(closed=False)
        mock_pg.execute = AsyncMock()
        mock_pg.rollback = AsyncMock()
        mock_cls.connect = AsyncMock(return_value=mock_pg)

        conn = PGAsyncConnection({'host': 'localhost'}, {})
        with pytest.raises(ValueError):
            async with conn:
                raise ValueError("test")

        mock_pg.rollback.assert_awaited_once()
        mock_pg.commit.assert_not_awaited()


class TestPGAsyncConnectionTransaction:

    @pytest.mark.asyncio
    @patch('pgmonkey.connections.postgres.async_connection.AsyncConnection')
    async def test_transaction_yields_self(self, mock_cls):
        """transaction() should yield self for consistency across all types."""
        mock_pg = AsyncMock(closed=False)
        mock_pg.execute = AsyncMock()
        mock_pg.transaction = lambda: AsyncMock(
            __aenter__=AsyncMock(),
            __aexit__=AsyncMock(return_value=False),
        )
        mock_cls.connect = AsyncMock(return_value=mock_pg)

        conn = PGAsyncConnection({'host': 'localhost'}, {})
        await conn.connect()
        async with conn.transaction() as tx:
            assert tx is conn
