import asyncio
import os
import psycopg
import psycopg_pool
import yaml
import sys
import pytest
from pgmonkey import PGConnectionManager

pytest.importorskip("pytest_asyncio")

# Config file path from environment variable - set PGMONKEY_TEST_CONFIG to your YAML config path.
CONFIG_FILE = os.environ.get("PGMONKEY_TEST_CONFIG")
if CONFIG_FILE is None:
    pytest.skip(
        "PGMONKEY_TEST_CONFIG environment variable not set - skipping integration tests",
        allow_module_level=True,
    )


def print_version_info():
    print(f"Python version: {sys.version}")
    print(f"psycopg version: {psycopg.__version__}")
    print(f"psycopg_pool version: {psycopg_pool.__version__}")
    print(f"PyYAML version: {yaml.__version__}")


@pytest.mark.asyncio
@pytest.mark.parametrize("connection_type", [
    "normal",
    "pool",
    "async",
    "async_pool",
])
async def test_database_connection(connection_type):
    """Test all connection types from a single config file."""
    print_version_info()

    connection_manager = PGConnectionManager()

    if connection_type in ('async', 'async_pool'):
        connection = await connection_manager.get_database_connection(CONFIG_FILE, connection_type)
    else:
        connection = connection_manager.get_database_connection(CONFIG_FILE, connection_type)

    try:
        if connection_type in ('async', 'async_pool'):
            async with connection as conn:
                async with conn.cursor() as cur:
                    await cur.execute('SELECT version();')
                    version = await cur.fetchone()
                    assert version is not None, f"{connection_type}: No version returned"
                    print(f"{connection_type}: {version}")
        else:
            with connection as conn:
                with conn.cursor() as cur:
                    cur.execute('SELECT version();')
                    version = cur.fetchone()
                    assert version is not None, f"{connection_type}: No version returned"
                    print(f"{connection_type}: {version}")
    finally:
        if asyncio.iscoroutinefunction(connection.disconnect):
            await connection.disconnect()
        else:
            connection.disconnect()
