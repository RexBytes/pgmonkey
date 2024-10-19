from psycopg import AsyncConnection, OperationalError
from .base_connection import PostgresBaseConnection
from contextlib import asynccontextmanager

class PGAsyncConnection(PostgresBaseConnection):
    def __init__(self, config, post_connect_async_settings=None):
        super().__init__()
        self.config = config
        self.post_connect_async_settings = post_connect_async_settings or {}
        self.connection: AsyncConnection = None

    async def connect(self):
        """Establishes an asynchronous database connection."""
        if self.connection is None or self.connection.closed:
            self.connection = await AsyncConnection.connect(**self.config)
            await self.apply_post_connect_settings()

    async def apply_post_connect_settings(self):
        """Applies settings as attributes to the connection object after it is established."""
        for setting, value in self.post_connect_async_settings.items():
            if hasattr(self.connection, setting):
                setattr(self.connection, setting, value)
            else:
                print(f"Warning: The setting '{setting}' is not applicable for this connection")

    async def test_connection(self):
        """Tests the asynchronous database connection."""
        try:
            async with self.cursor() as cur:
                await cur.execute('SELECT 1;')
                result = await cur.fetchone()
                print("Async connection successful: ", result)
        except OperationalError as e:
            print(f"Connection failed: {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

    async def disconnect(self):
        """Closes the asynchronous database connection."""
        if self.connection and not self.connection.closed:
            await self.connection.close()
            self.connection = None

    async def commit(self):
        """Commits the current transaction."""
        if self.connection and not self.connection.closed:
            await self.connection.commit()

    async def rollback(self):
        """Rolls back the current transaction."""
        if self.connection and not self.connection.closed:
            await self.connection.rollback()

    @asynccontextmanager
    async def transaction(self):
        """Creates a transaction context on the async connection."""
        if self.connection:
            async with self.connection.transaction():
                yield  # Let the context handle commit/rollback automatically.
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
        if exc_type:
            await self.rollback()
        else:
            await self.commit()
        await self.disconnect()


