import yaml


class ConnectionCodeGenerator:
    def __init__(self):
        pass

    def generate_connection_code(self, config_file_path, connection_type=None, library='pgmonkey'):
        """Generate example Python code for the given connection type.

        Args:
            config_file_path: Path to the YAML configuration file.
            connection_type: Optional connection type override. If None, uses config file value.
            library: Target library - 'pgmonkey' (default) or 'psycopg'.
        """
        try:
            with open(config_file_path, 'r') as file:
                config = yaml.safe_load(file)

            resolved_type = connection_type or config['postgresql'].get('connection_type', 'normal')

            if library == 'psycopg':
                self._generate_psycopg(config_file_path, resolved_type)
            else:
                self._generate_pgmonkey(config_file_path, resolved_type)

        except Exception as e:
            print(f"An error occurred while generating the connection code: {e}")

    def _generate_pgmonkey(self, config_file_path, resolved_type):
        """Dispatch to pgmonkey code templates."""
        if resolved_type == 'normal':
            self._print_normal_example(config_file_path)
        elif resolved_type == 'pool':
            self._print_pool_example(config_file_path)
        elif resolved_type == 'async':
            self._print_async_example(config_file_path)
        elif resolved_type == 'async_pool':
            self._print_async_pool_example(config_file_path)
        else:
            print(f"Unsupported connection type: {resolved_type}")

    def _generate_psycopg(self, config_file_path, resolved_type):
        """Dispatch to native psycopg/psycopg_pool code templates."""
        if resolved_type == 'normal':
            self._print_normal_psycopg_example(config_file_path)
        elif resolved_type == 'pool':
            self._print_pool_psycopg_example(config_file_path)
        elif resolved_type == 'async':
            self._print_async_psycopg_example(config_file_path)
        elif resolved_type == 'async_pool':
            self._print_async_pool_psycopg_example(config_file_path)
        else:
            print(f"Unsupported connection type: {resolved_type}")

    def _print_normal_example(self, config_file_path):
        example_code = f"""
# Example: Normal synchronous connection using pgmonkey
# One config file serves all connection types - just pass the type you need.

from pgmonkey import PGConnectionManager

def main():
    connection_manager = PGConnectionManager()
    config_file_path = '{config_file_path}'

    # Get a normal (synchronous) PostgreSQL connection
    connection = connection_manager.get_database_connection(config_file_path, 'normal')

    # Use the connection
    with connection as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT 1;')
            print(cur.fetchone())

if __name__ == "__main__":
    main()
        """
        print("Generated normal synchronous connection code using pgmonkey:")
        print(example_code)

    def _print_pool_example(self, config_file_path):
        example_code = f"""
# Example: Pooled synchronous connection using pgmonkey
# One config file serves all connection types - just pass the type you need.

from pgmonkey import PGConnectionManager

def main():
    connection_manager = PGConnectionManager()
    config_file_path = '{config_file_path}'

    # Get a pooled PostgreSQL connection
    pool_connection = connection_manager.get_database_connection(config_file_path, 'pool')

    # Use the pool - each 'with' block acquires and releases a connection
    with pool_connection as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT 1;')
            print(cur.fetchone())

if __name__ == "__main__":
    main()
        """
        print("Generated pooled synchronous connection code using pgmonkey:")
        print(example_code)

    def _print_async_example(self, config_file_path):
        example_code = f"""
# Example: Asynchronous connection using pgmonkey
# One config file serves all connection types - just pass the type you need.

import asyncio
from pgmonkey import PGConnectionManager

async def main():
    connection_manager = PGConnectionManager()
    config_file_path = '{config_file_path}'

    # Get an async PostgreSQL connection
    connection = await connection_manager.get_database_connection(config_file_path, 'async')

    # Use the connection asynchronously
    async with connection as conn:
        async with conn.cursor() as cur:
            await cur.execute('SELECT 1;')
            result = await cur.fetchone()
            print(result)

if __name__ == "__main__":
    asyncio.run(main())
        """
        print("Generated asynchronous connection code using pgmonkey:")
        print(example_code)

    def _print_async_pool_example(self, config_file_path):
        example_code = f"""
# Example: Asynchronous pooled connection using pgmonkey
# One config file serves all connection types - just pass the type you need.

import asyncio
from pgmonkey import PGConnectionManager

async def main():
    connection_manager = PGConnectionManager()
    config_file_path = '{config_file_path}'

    # Get an async pooled PostgreSQL connection
    pool_connection = await connection_manager.get_database_connection(config_file_path, 'async_pool')

    # Use the pool - each 'async with' cursor block acquires and releases a connection
    async with pool_connection as conn:
        async with conn.cursor() as cur:
            await cur.execute('SELECT 1;')
            result = await cur.fetchone()
            print(result)

if __name__ == "__main__":
    asyncio.run(main())
        """
        print("Generated asynchronous pooled connection code using pgmonkey:")
        print(example_code)

    # -- Native psycopg / psycopg_pool templates ----------------------------

    def _print_normal_psycopg_example(self, config_file_path):
        example_code = f"""
# Example: Normal synchronous connection using psycopg
# Reads connection settings from your pgmonkey YAML config file.

import yaml
import psycopg

def main():
    config_file_path = '{config_file_path}'

    with open(config_file_path, 'r') as f:
        config = yaml.safe_load(f)

    conn_settings = config['postgresql']['connection_settings']
    # Filter out empty values (e.g. blank SSL cert paths)
    conn_params = {{k: v for k, v in conn_settings.items() if v}}

    with psycopg.connect(**conn_params) as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT 1;')
            print(cur.fetchone())

if __name__ == "__main__":
    main()
        """
        print("Generated normal synchronous connection code using psycopg:")
        print(example_code)

    def _print_pool_psycopg_example(self, config_file_path):
        example_code = f"""
# Example: Pooled synchronous connection using psycopg_pool
# Reads connection and pool settings from your pgmonkey YAML config file.

import yaml
from psycopg import conninfo
from psycopg_pool import ConnectionPool

def main():
    config_file_path = '{config_file_path}'

    with open(config_file_path, 'r') as f:
        config = yaml.safe_load(f)

    conn_settings = config['postgresql']['connection_settings']
    conn_params = {{k: v for k, v in conn_settings.items() if v}}
    pool_settings = config['postgresql'].get('pool_settings', {{}})

    # Remove pgmonkey-specific keys that psycopg_pool does not accept
    pool_settings.pop('check_on_checkout', None)

    conninfo_str = conninfo.make_conninfo(**conn_params)
    pool = ConnectionPool(conninfo=conninfo_str, **pool_settings)

    try:
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT 1;')
                print(cur.fetchone())
    finally:
        pool.close()

if __name__ == "__main__":
    main()
        """
        print("Generated pooled synchronous connection code using psycopg_pool:")
        print(example_code)

    def _print_async_psycopg_example(self, config_file_path):
        example_code = f"""
# Example: Asynchronous connection using psycopg (AsyncConnection)
# Reads connection and async settings from your pgmonkey YAML config file.

import asyncio
import yaml
from psycopg import AsyncConnection

async def main():
    config_file_path = '{config_file_path}'

    with open(config_file_path, 'r') as f:
        config = yaml.safe_load(f)

    conn_settings = config['postgresql']['connection_settings']
    conn_params = {{k: v for k, v in conn_settings.items() if v}}
    async_settings = config['postgresql'].get('async_settings', {{}})

    async with await AsyncConnection.connect(**conn_params) as conn:
        # Apply GUC settings (statement_timeout, lock_timeout, etc.)
        for setting, value in async_settings.items():
            await conn.execute(f"SET {{setting}} = %s", (str(value),))

        async with conn.cursor() as cur:
            await cur.execute('SELECT 1;')
            result = await cur.fetchone()
            print(result)

if __name__ == "__main__":
    asyncio.run(main())
        """
        print("Generated asynchronous connection code using psycopg:")
        print(example_code)

    def _print_async_pool_psycopg_example(self, config_file_path):
        example_code = f"""
# Example: Asynchronous pooled connection using psycopg_pool (AsyncConnectionPool)
# Reads connection, pool, and async settings from your pgmonkey YAML config file.

import asyncio
import yaml
from psycopg import conninfo
from psycopg_pool import AsyncConnectionPool

async def main():
    config_file_path = '{config_file_path}'

    with open(config_file_path, 'r') as f:
        config = yaml.safe_load(f)

    conn_settings = config['postgresql']['connection_settings']
    conn_params = {{k: v for k, v in conn_settings.items() if v}}
    pool_settings = config['postgresql'].get('async_pool_settings', {{}})
    async_settings = config['postgresql'].get('async_settings', {{}})

    # Remove pgmonkey-specific keys that psycopg_pool does not accept
    pool_settings.pop('check_on_checkout', None)

    conninfo_str = conninfo.make_conninfo(**conn_params)

    # Optional: configure callback to apply GUC settings to each connection
    async def configure(conn):
        for setting, value in async_settings.items():
            await conn.execute(f"SET {{setting}} = %s", (str(value),))

    pool = AsyncConnectionPool(
        conninfo=conninfo_str,
        configure=configure if async_settings else None,
        **pool_settings,
    )
    await pool.open()

    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute('SELECT 1;')
                result = await cur.fetchone()
                print(result)
    finally:
        await pool.close()

if __name__ == "__main__":
    asyncio.run(main())
        """
        print("Generated asynchronous pooled connection code using psycopg_pool:")
        print(example_code)
