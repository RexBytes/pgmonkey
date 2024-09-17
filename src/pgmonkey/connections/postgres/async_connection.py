from psycopg import AsyncConnection, OperationalError
from .base_connection import BaseConnection


class PGAsyncConnection(BaseConnection):
    def __init__(self, config, post_connect_async_settings=None):
        super().__init__()
        self.config = config
        # This dictionary can contain settings to be applied after the connection is established
        self.post_connect_async_settings = post_connect_async_settings or {}
        self.connection: AsyncConnection = None

    async def connect(self):
        """Establishes an asynchronous database connection."""
        if self.connection is None or self.connection.closed:
            self.connection = await AsyncConnection.connect(**self.config)
            await self.apply_post_connect_settings()

    async def apply_post_connect_settings(self):
        """Applies any settings that need to be set after the connection is established."""
        for setting, value in self.post_connect_async_settings.items():
            # This example assumes settings can be applied directly as attributes
            # Adjust this method based on the actual async settings and their required handling
            setattr(self.connection, setting, value)

    async def __aenter__(self):
        if self.connection is None or self.connection.closed:
            await self.connect()
        return self.connection

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()

    async def test_connection(self):
        """Tests the asynchronous database connection."""
        if self.connection is None or self.connection.closed:
            await self.connect()
        async with self.connection.cursor() as cur:
            await cur.execute('SELECT 1;')
            result = await cur.fetchone()
            print("Async connection successful: ", result)

    async def disconnect(self):
        """Closes the asynchronous database connection."""
        if self.connection and not self.connection.closed:
            await self.connection.close()
            self.connection = None
