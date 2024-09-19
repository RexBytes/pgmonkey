import yaml


class ConnectionCodeGenerator:
    def __init__(self):
        pass

    def load_config(self, config_file_path):
        """Loads the YAML configuration from the provided file path."""
        with open(config_file_path, 'r') as file:
            config = yaml.safe_load(file)
        return config

    def generate_connection_code(self, config_file_path):
        try:
            # Load the configuration from the YAML file
            config = self.load_config(config_file_path)

            # Retrieve the connection type from the YAML config
            connection_type = config['postgresql']['connection_type']

            # Print appropriate Python example based on the connection type
            if connection_type == 'normal':
                self.print_normal_example(config_file_path)
            elif connection_type == 'pool':
                self.print_pool_example(config_file_path, config)
            elif connection_type == 'async':
                self.print_async_example(config_file_path)
            elif connection_type == 'async_pool':
                self.print_async_pool_example(config_file_path, config)
            else:
                print(f"Unsupported connection type: {connection_type}")

        except Exception as e:
            print(f"An error occurred while generating the connection code: {e}")

    def print_normal_example(self, config_file_path):
        """Prints an example for a normal synchronous connection."""
        example_code = f"""
# Example Python code for a normal synchronous connection using pgmonkey

from pgmonkey import PGConnectionManager

def main():
    connection_manager = PGConnectionManager()
    config_file_path = '{config_file_path}'

    # Get the PostgreSQL connection
    connection = connection_manager.get_database_connection(config_file_path)

    
    # Use the connection synchronously
    with connection as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT 1;')
            print(cur.fetchone())

if __name__ == "__main__":
    main()
        """
        print("Generated normal synchronous connection code using pgmonkey:")
        print(example_code)

    def print_pool_example(self, config_file_path, config):
        """Prints an example for a pooled synchronous connection, adjusting the pool size from the config."""
        pool_settings = config['postgresql'].get('pool_settings', {})
        min_size = pool_settings.get('min_size', 1)
        max_size = pool_settings.get('max_size', 10)
        num_connections = min(max_size, min_size + 1)

        example_code = f"""
# Example Python code for a pooled synchronous connection using pgmonkey

from pgmonkey import PGConnectionManager

def main():
    connection_manager = PGConnectionManager()
    config_file_path = '{config_file_path}'

    # Get the PostgreSQL connection from the pool
    connections = [connection_manager.get_database_connection(config_file_path) for _ in range({num_connections})]

    
    # Use each connection
    for i, conn in enumerate(connections):
        with conn as connection:
            with connection.cursor() as cur:
                cur.execute('SELECT 1;')
                print(f"Connection {{i+1}}: {{cur.fetchone()}}")

if __name__ == "__main__":
    main()
        """
        print("Generated pooled synchronous connection code using pgmonkey:")
        print(example_code)

    def print_async_example(self, config_file_path):
        """Prints an example for an asynchronous connection."""
        example_code = f"""
# Example Python code for an asynchronous connection using pgmonkey

import asyncio
from pgmonkey import PGConnectionManager

async def main():
    connection_manager = PGConnectionManager()
    config_file_path = '{config_file_path}'

    # Get the PostgreSQL connection asynchronously
    connection = await connection_manager.get_database_connection(config_file_path)

    
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

    def print_async_pool_example(self, config_file_path, config):
        """Prints an example for an asynchronous pooled connection, adjusting the pool size from the config."""
        async_pool_settings = config['postgresql'].get('async_pool_settings', {})
        min_size = async_pool_settings.get('min_size', 1)
        max_size = async_pool_settings.get('max_size', 10)
        num_connections = min(max_size, min_size + 1)

        example_code = f"""
# Example Python code for an asynchronous pooled connection using pgmonkey

import asyncio
from pgmonkey import PGConnectionManager

async def main():
    connection_manager = PGConnectionManager()
    config_file_path = '{config_file_path}'

    # Acquire {num_connections} connections asynchronously from the pool
    connections = [await connection_manager.get_database_connection(config_file_path) for _ in range({num_connections})]

    # Use each connection asynchronously
    for i, connection in enumerate(connections):
        async with connection as conn:
            async with conn.cursor() as cur:
                await cur.execute('SELECT 1;')
                result = await cur.fetchone()
                print(f"Connection {{i+1}}: {{result}}")

if __name__ == "__main__":
    asyncio.run(main())
        """
        print("Generated asynchronous pooled connection code using pgmonkey:")
        print(example_code)

