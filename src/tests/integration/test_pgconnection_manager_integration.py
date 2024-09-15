import asyncio
import pytest
from pgmonkey import PGConnectionManager


@pytest.mark.asyncio
async def test_database_connection(config_file, config_name):
    """Test real database connection with the provided config."""
    connection_manager = PGConnectionManager()
    connection = await connection_manager.get_database_connection(config_file)

    try:
        if connection.connection_type in ['async', 'async_pool']:
            async with connection as conn:
                async with conn.connection.cursor() as cur:
                    await cur.execute('SELECT version();')
                    version = await cur.fetchone()
                    assert version is not None, f"{config_name}: No version returned"
                    print(f"{config_name}: {version}")
        else:
            with connection as conn:
                with conn.connection.cursor() as cur:
                    cur.execute('SELECT version();')
                    version = cur.fetchone()
                    assert version is not None, f"{config_name}: No version returned"
                    print(f"{config_name}: {version}")
    finally:
        await connection.disconnect() if asyncio.iscoroutinefunction(connection.disconnect) else connection.disconnect()


@pytest.mark.asyncio
async def test_real_connections():
    """Test all real database connections using various configuration files."""
    base_dir = '/home/ubuntu/myconnectionconfigs/'  # Corrected path for configs on Jenkins node
    config_files = {
        'pg_async_pool.yaml': base_dir + 'pg_async_pool.yaml',
        'pg_async.yaml': base_dir + 'pg_async.yaml',
        'pg_normal.yaml': base_dir + 'pg_normal.yaml',
        'pg_pool.yaml': base_dir + 'pg_pool.yaml'
    }

    for config_name, config_file in config_files.items():
        print(f"Testing connection with config: {config_name}")
        await test_database_connection(config_file, config_name)
