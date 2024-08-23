from psycopg_pool import AsyncConnectionPool
from .base_connection import PostgresBaseConnection


class PGAsyncPoolConnection(PostgresBaseConnection):
    def __init__(self, config, pool_settings=None):
        super().__init__()  # Call super if the base class has an __init__ method
        self.config = config
        self.pool_settings = pool_settings or {}
        self.pool = None

    def construct_dsn(self):
        """Assuming self.config directly contains connection info as a dict."""
        # This assumes all keys in self.config are for the connection,
        # adjust if your config includes other types of settings.
        return " ".join([f"{k}={v}" for k, v in self.config.items()])

    async def connect(self):
        dsn = self.construct_dsn()
        # Initialize AsyncConnectionPool with DSN and any pool-specific settings
        self.pool = AsyncConnectionPool(conninfo=dsn, **self.pool_settings)
        await self.pool.open()

    async def __aenter__(self):
        if not self.pool:
            await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()

    async def test_connection(self):
        if not self.pool:
            await self.connect()
        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute('SELECT 1;')
                print("Async pool connection successful: ", await cur.fetchone())

    async def disconnect(self):
        if self.pool:
            await self.pool.close()
            self.pool = None
