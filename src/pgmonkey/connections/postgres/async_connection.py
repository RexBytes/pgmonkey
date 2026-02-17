import logging
from psycopg import AsyncConnection, OperationalError, sql
from .base_connection import PostgresBaseConnection
from contextlib import asynccontextmanager
from typing import Optional

logger = logging.getLogger(__name__)


class PGAsyncConnection(PostgresBaseConnection):
    def __init__(self, config, async_settings=None):
        self.config = config
        self.async_settings = async_settings or {}
        self.autocommit = None
        self.connection: Optional[AsyncConnection] = None

    async def connect(self):
        """Establishes an asynchronous database connection."""
        if self.connection is None or self.connection.closed:
            self.connection = await AsyncConnection.connect(
                autocommit=bool(self.autocommit), **self.config
            )
            await self._apply_async_settings()

    async def _apply_async_settings(self):
        """Applies PostgreSQL GUC settings via SET commands after connection is established."""
        for setting, value in self.async_settings.items():
            try:
                await self.connection.execute(sql.SQL("SET {} = {}").format(sql.Identifier(setting), sql.Literal(str(value))))
            except Exception as e:
                logger.warning("Could not apply setting '%s': %s", setting, e)

    async def test_connection(self):
        """Tests the asynchronous database connection."""
        try:
            async with self.cursor() as cur:
                await cur.execute('SELECT 1;')
                result = await cur.fetchone()
                logger.info("Async connection successful: %s", result)
        except OperationalError as e:
            logger.error("Connection failed: %s", e)
        except Exception as e:
            logger.error("An unexpected error occurred: %s", e)

    async def disconnect(self):
        """Closes the asynchronous database connection."""
        if self.connection and not self.connection.closed:
            await self.connection.close()
            self.connection = None

    async def commit(self):
        if self.connection and not self.connection.closed:
            await self.connection.commit()

    async def rollback(self):
        if self.connection and not self.connection.closed:
            await self.connection.rollback()

    @asynccontextmanager
    async def transaction(self):
        """Creates a transaction context on the async connection."""
        if self.connection:
            async with self.connection.transaction():
                yield self
        else:
            raise Exception("No active connection available for transaction")

    @asynccontextmanager
    async def cursor(self):
        """Returns an async cursor object as a context manager."""
        if self.connection:
            async with self.connection.cursor() as cur:
                yield cur
        else:
            raise Exception("No active connection available to create a cursor")

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        try:
            if exc_type:
                await self.rollback()
            else:
                await self.commit()
        finally:
            await self.disconnect()
