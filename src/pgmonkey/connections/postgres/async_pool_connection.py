import warnings
from psycopg_pool import AsyncConnectionPool
from psycopg import conninfo as psycopg_conninfo
from .base_connection import PostgresBaseConnection
from contextlib import asynccontextmanager

warnings.filterwarnings('ignore', category=RuntimeWarning, module='psycopg_pool')


class PGAsyncPoolConnection(PostgresBaseConnection):
    def __init__(self, config, async_pool_settings=None):
        self.config = config
        self.async_pool_settings = async_pool_settings or {}
        self.pool = None

    @staticmethod
    def construct_conninfo(config):
        """Constructs a properly escaped connection info string from the config dictionary."""
        return psycopg_conninfo.make_conninfo(**config)

    async def connect(self):
        """Initialize the async connection pool."""
        if self.pool is None:
            conninfo = self.construct_conninfo(self.config)
            self.pool = AsyncConnectionPool(conninfo=conninfo, **self.async_pool_settings)
            await self.pool.open()

    async def test_connection(self):
        """Tests a single connection from the async pool."""
        if not self.pool:
            await self.connect()

        try:
            async with self.pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute('SELECT 1;')
                    result = await cur.fetchone()
                    print("Async pool connection successful: ", result)
        except Exception as e:
            print(f"Test connection failed: {e}")

    async def disconnect(self):
        if self.pool:
            await self.pool.close()
            self.pool = None

    async def commit(self):
        """No-op for pool connections. Transactions are committed within cursor/transaction contexts."""
        pass

    async def rollback(self):
        """No-op for pool connections. Transactions are rolled back within cursor/transaction contexts."""
        pass

    @asynccontextmanager
    async def transaction(self):
        """Creates a transaction context on a pooled connection."""
        if self.pool:
            async with self.pool.connection() as conn:
                async with conn.transaction() as tx:
                    yield tx
        else:
            raise Exception("No active pool available for transaction")

    @asynccontextmanager
    async def cursor(self):
        """Provides an async cursor from a pooled connection."""
        if self.pool:
            async with self.pool.connection() as conn:
                async with conn.cursor() as cur:
                    yield cur
        else:
            raise Exception("No active pool available for cursor")

    async def __aenter__(self):
        if not self.pool:
            await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()
