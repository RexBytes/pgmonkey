import warnings
from psycopg_pool import AsyncConnectionPool
from .base_connection import PostgresBaseConnection


class PGAsyncPoolConnection(PostgresBaseConnection):
    def __init__(self, config, pool_settings=None):
        super().__init__()  # Call super if the base class has an __init__ method
        self.config = config
        self.pool_settings = pool_settings or {}
        self.pool = None
        self._conn = None

    def construct_dsn(self):
        """Assuming self.config directly contains connection info as a dict."""
        # This assumes all keys in self.config are for the connection,
        # adjust if your config includes other types of settings.
        return " ".join([f"{k}={v}" for k, v in self.config.items()])

    # Suppress the psycopg RuntimeWarning
    warnings.filterwarnings('ignore', category=RuntimeWarning, module='psycopg_pool')

    async def connect(self):
        dsn = self.construct_dsn()
        # Initialize AsyncConnectionPool with DSN and any pool-specific settings
        self.pool = AsyncConnectionPool(conninfo=dsn, **self.pool_settings)
        await self.pool.open()

    async def __aenter__(self):
        if not self.pool:
            await self.connect()
        # Acquire a connection from the pool
        self._conn = await self.pool.connection().__aenter__()
        return self._conn  # Return the actual connection for use in `async with`

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Release the connection back to the pool
        await self._conn.__aexit__(exc_type, exc_val, exc_tb)
        await self.disconnect()

    async def test_connection(self):
        if not self.pool:
            await self.connect()

        # Test a single connection to ensure the pool is working
        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute('SELECT 1;')
                print("Async pool connection successful: ", await cur.fetchone())

        # Retrieve pool settings directly from self.pool_settings, assuming they were passed correctly
        pool_min_size = self.pool_settings.get('min_size', 1)  # Defaulting to 1 if not set
        pool_max_size = self.pool_settings.get('max_size', 10)  # Defaulting to 10 if not set
        num_connections_to_test = min(pool_max_size, pool_min_size + 1)  # +1 to the minimum if possible

        connections = []

        try:
            # Test pooling by acquiring multiple connections asynchronously
            for _ in range(num_connections_to_test):
                # Use async with for each connection from the pool
                async with self.pool.connection() as connection:
                    connections.append(connection)

            print(f"Pooling test successful: Acquired {len(connections)} connections out of a possible {pool_max_size}")

        except Exception as e:
            print(f"Pooling test failed: {e}")
        finally:
            # Ensure all connections are returned to the pool
            # Since async with ensures automatic closing, this part may not be needed
            # But for safety, ensure connections are handled properly
            for conn in connections:
                await conn.close()

        # Check if we acquired the correct number of connections
        if len(connections) == num_connections_to_test:
            print(f"Async pooling tested successfully with {len(connections)} concurrent connections.")
        else:
            print(f"Async pooling test did not pass, only {len(connections)} connections acquired.")

    async def disconnect(self):
        if self.pool:
            await self.pool.close()
            self.pool = None
