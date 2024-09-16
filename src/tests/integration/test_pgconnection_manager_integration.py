import asyncio
import pytest
from pgmonkey import PGConnectionManager


@pytest.mark.asyncio
@pytest.mark.parametrize("config_file, config_name", [
    ("/home/ubuntu/myconnectionconfigs/pg_async_pool.yaml", "pg_async_pool.yaml"),
    ("/home/ubuntu/myconnectionconfigs/pg_async.yaml", "pg_async.yaml"),
    ("/home/ubuntu/myconnectionconfigs/pg_normal.yaml", "pg_normal.yaml"),
    ("/home/ubuntu/myconnectionconfigs/pg_pool.yaml", "pg_pool.yaml"),
])
async def test_database_connection(config_file, config_name):
    """Test real database connection with the provided config."""
    connection_manager = PGConnectionManager()
    connection = await connection_manager.get_database_connection(config_file)

    try:
        # Async pool connection
        if connection.connection_type == 'async_pool':
            async with connection.pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute('SELECT version();')
                    version = await cur.fetchone()
                    assert version is not None, f"{config_name}: No version returned"
                    print(f"{config_name}: {version}")
        # Async connection
        elif connection.connection_type == 'async':
            async with connection.connection.cursor() as cur:
                await cur.execute('SELECT version();')
                version = await cur.fetchone()
                assert version is not None, f"{config_name}: No version returned"
                print(f"{config_name}: {version}")
        # Connection pool
        elif connection.connection_type == 'pool':
            with connection.pool.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute('SELECT version();')
                    version = cur.fetchone()
                    assert version is not None, f"{config_name}: No version returned"
                    print(f"{config_name}: {version}")
        # Normal connection
        elif connection.connection_type == 'normal':
            with connection.connection.cursor() as cur:
                cur.execute('SELECT version();')
                version = cur.fetchone()
                assert version is not None, f"{config_name}: No version returned"
                print(f"{config_name}: {version}")
    finally:
        # Close connection
        await connection.disconnect() if asyncio.iscoroutinefunction(connection.disconnect) else connection.disconnect()




