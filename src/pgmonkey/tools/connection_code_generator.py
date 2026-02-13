import yaml


class ConnectionCodeGenerator:
    def __init__(self):
        pass

    def generate_connection_code(self, config_file_path, connection_type=None):
        """Generate example Python code for the given connection type.

        Args:
            config_file_path: Path to the YAML configuration file.
            connection_type: Optional connection type override. If None, uses config file value.
        """
        try:
            with open(config_file_path, 'r') as file:
                config = yaml.safe_load(file)

            resolved_type = connection_type or config['postgresql'].get('connection_type', 'normal')

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

        except Exception as e:
            print(f"An error occurred while generating the connection code: {e}")

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
