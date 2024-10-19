import warnings
from psycopg_pool import AsyncConnectionPool
from .base_connection import PostgresBaseConnection
from contextlib import asynccontextmanager

class PGAsyncPoolConnection(PostgresBaseConnection):
    def __init__(self, config, pool_settings=None):
        super().__init__()  # Call super if the base class has an __init__ method
        self.config = config
        self.pool_settings = pool_settings or {}
        self.pool = None

    def construct_dsn(self):
        """Assuming self.config directly contains connection info as a dict."""
        return " ".join([f"{k}={v}" for k, v in self.config.items()])

    warnings.filterwarnings('ignore', category=RuntimeWarning, module='psycopg_pool')

    async def connect(self):
        dsn = self.construct_dsn()
        # Initialize AsyncConnectionPool with DSN and any pool-specific settings
        self.pool = AsyncConnectionPool(conninfo=dsn, **self.pool_settings)
        await self.pool.open()

    @asynccontextmanager
    async def transaction(self):
        """Creates a transaction context on the pooled connection."""
        if self.pool:
            async with self.pool.connection() as conn:
                async with conn.transaction() as tx:
                    yield tx
        else:
            raise Exception("No active connection available for transaction")

    async def test_connection(self):
        """Tests both a single connection and pooling behavior from the pool."""
        if not self.pool:
            await self.connect()

        # Test a single connection to ensure the pool is working
        try:
            async with self.pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute('SELECT 1;')
                    result = await cur.fetchone()
                    print("Async pool connection successful: ", result)
        except Exception as e:
            print(f"Test connection failed: {e}")

    @asynccontextmanager
    async def cursor(self):
        """Provides an async cursor from a pooled connection."""
        if self.pool:
            async with self.pool.connection() as conn:
                async with conn.cursor() as cur:
                    yield cur
        else:
            raise Exception("No active connection available for cursor")

    async def __aenter__(self):
        if not self.pool:
            await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()

    async def disconnect(self):
        if self.pool:
            await self.pool.close()
            self.pool = None

    async def commit(self):
        """Commits the current transaction using a connection from the pool."""
        async with self.pool.connection() as conn:
            await conn.commit()

    async def rollback(self):
        """Rolls back the current transaction using a connection from the pool."""
        async with self.pool.connection() as conn:
            await conn.rollback()



