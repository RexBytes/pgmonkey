import asyncio
import psycopg
import psycopg_pool
import yaml
import sys
import pytest
from pgmonkey import PGConnectionManager



# Print version information at the start of the test
def print_version_info():
    print(f"Python version: {sys.version}")
    print(f"psycopg version: {psycopg.__version__}")
    print(f"psycopg_pool version: {psycopg_pool.__version__}")
    print(f"PyYAML version: {yaml.__version__}")

@pytest.mark.asyncio
@pytest.mark.parametrize("config_file, config_name", [
    ("/home/ubuntu/myconnectionconfigs/pg_async_pool.yaml", "pg_async_pool.yaml"),
    ("/home/ubuntu/myconnectionconfigs/pg_async.yaml", "pg_async.yaml"),
    ("/home/ubuntu/myconnectionconfigs/pg_normal.yaml", "pg_normal.yaml"),
    ("/home/ubuntu/myconnectionconfigs/pg_pool.yaml", "pg_pool.yaml"),
])
async def test_database_connection(config_file, config_name):
    """Test real database connection with the provided config."""
    print_version_info()  # Print version information at the start

    connection_manager = PGConnectionManager()
    connection = await connection_manager.get_database_connection(config_file)

    try:
        if connection.connection_type in ['async', 'async_pool']:
            async with connection as conn:
                async with conn.cursor() as cur:
                    await cur.execute('SELECT version();')
                    version = await cur.fetchone()
                    assert version is not None, f"{config_name}: No version returned"
                    print(f"{config_name}: {version}")
        else:
            with connection as conn:
                with conn.cursor() as cur:
                    cur.execute('SELECT version();')
                    version = cur.fetchone()
                    assert version is not None, f"{config_name}: No version returned"
                    print(f"{config_name}: {version}")
    finally:
        await connection.disconnect() if asyncio.iscoroutinefunction(connection.disconnect) else connection.disconnect()




