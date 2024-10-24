# Getting Started with pgmonkey: A Comprehensive Guide

**pgmonkey** is a powerful Python library designed to simplify and manage PostgreSQL database connections. It supports various connection types, authentication methods (including SSL and certificate-based authentication), and provides a flexible, configuration-driven approach to managing database connections. In addition to its robust Python API, **pgmonkey** includes a command-line interface (CLI) for easy management of database configurations and connections.

This tutorial will walk you through the process of installing **pgmonkey**, creating YAML configuration files, understanding the available authentication methods, using the CLI, and using the library to manage different types of database connections.

## Table of Contents

1. [Installation](#installation)
2. [Setting Up YAML Configuration Files](#setting-up-yaml-configuration-files)
   - [Basic Connection Options](#basic-connection-options)
   - [Connection Pooling Options](#connection-pooling-options)
   - [Asynchronous Connection Options](#asynchronous-connection-options)
3. [Supported Authentication Methods](#supported-authentication-methods)
   - [Password-Based Authentication](#password-based-authentication)
   - [SSL/TLS Encryption](#ssltls-encryption)
   - [Certificate-Based Authentication](#certificate-based-authentication)
4. [Using the pgmonkey CLI](#using-the-pgmonkey-cli)
   - [Available CLI Commands](#available-cli-commands)
   - [Creating a PostgreSQL Configuration Template](#creating-a-postgresql-configuration-template)
   - [Testing a Database Connection](#testing-a-database-connection)
5. [Using pgmonkey in Python](#using-pgmonkey-in-python)
   - [Establishing a Connection](#establishing-a-connection)
   - [Running Database Queries](#running-database-queries)
   - [Handling Different Connection Types](#handling-different-connection-types)
6. [Importing and Exporting Data](#importing-and-exporting-data)
   - [Importing Data](#importing-data)
   - [Exporting Data](#exporting-data)
7. [Example Use Case: Testing Multiple Connections](#example-use-case-testing-multiple-connections)
8. [Example Use Case:  Test Pooling Capability](#example-use-case-test-pooling-capability)
9. [Conclusion](#conclusion)

## Installation

To get started with **pgmonkey**, you can install it via PyPI by running the following command:

```bash
pip install pgmonkey
```

Alternatively, you can clone the repository from GitHub:

```bash
git clone https://github.com/RexBytes/pgmonkey.git
cd pgmonkey
pip install .
```

## Setting Up YAML Configuration Files

**pgmonkey** uses YAML files to manage and configure database connections. These configuration files allow you to define various settings, including the type of connection, SSL options, and authentication methods.

### Basic Connection Options

Here’s a basic YAML configuration for a normal (synchronous) PostgreSQL connection:

```yaml
postgresql:
  connection_type: 'normal'  # Options: 'normal', 'pool', 'async', 'async_pool'
  connection_settings:
    connectionName: 'normal_connection'
    description: 'Default PostgreSQL connection setup'
    user: 'your_user'
    password: 'your_password'
    host: 'localhost'
    port: 5432
    dbname: 'your_database'
    sslmode: 'prefer'  # Options: disable, allow, prefer, require, verify-ca, verify-full
    connect_timeout: 10  # Maximum wait for connection, in seconds
    application_name: 'pgmonkey_app'
    keepalives: 1  # Enable TCP keepalives
    keepalives_idle: 60  # Seconds before sending a keepalive probe
    keepalives_interval: 15  # Seconds between keepalive probes
    keepalives_count: 5  # Maximum keepalive probes before closing connection
```

### Connection Pooling Options

If you want to utilize connection pooling, you can extend the configuration like this:

```yaml
postgresql:
  connection_type: 'pool'
  connection_settings:
    connectionName: 'pool_connection'
    user: 'your_user'
    password: 'your_password'
    host: 'localhost'
    port: 5432
    dbname: 'your_database'
    sslmode: 'prefer'
  pool_settings:
    min_size: 5  # Minimum number of connections in the pool
    max_size: 20  # Maximum number of connections in the pool
    max_idle: 300  # Time (seconds) a connection can remain idle before being closed
    max_lifetime: 3600  # Maximum time (seconds) a connection can be reused
```

### Asynchronous Connection Options

For applications requiring asynchronous database operations, **pgmonkey** supports async connections:

```yaml
postgresql:
  connection_type: 'async'
  connection_settings:
    connectionName: 'async_connection'
    user: 'your_user'
    password: 'your_password'
    host: 'localhost'
    port: 5432
    dbname: 'your_database'
    sslmode: 'require'
  async_settings:
    idle_in_transaction_session_timeout: '5000'  # Timeout for idle in transaction
    statement_timeout: '30000'  # Cancel statements exceeding 30 seconds
    lock_timeout: '10000'  # Timeout for acquiring locks
    work_mem: '256MB'  # Memory for sort operations and more
```

For asynchronous connections with pooling:

```yaml
postgresql:
  connection_type: 'async_pool'
  connection_settings:
    connectionName: 'async_pool_connection'
    user: 'your_user'
    password: 'your_password'
    host: 'localhost'
    port: 5432
    dbname: 'your_database'
    sslmode: 'require'
  async_pool_settings:
    min_size: 5
    max_size: 20
    max_idle: 300
    max_lifetime: 3600
```

## Supported Authentication Methods

**pgmonkey** supports various PostgreSQL authentication methods, including password-based authentication, SSL/TLS encryption, and certificate-based authentication. Here’s a breakdown of each:

### Password-Based Authentication

This is the most common authentication method. The user’s credentials (username and password) are sent to the PostgreSQL server, where they are validated.

Example configuration:

```yaml
postgresql:
  connection_type: 'normal'
  connection_settings:
    user: 'your_user'
    password: 'your_password'
    host: 'localhost'
    dbname: 'your_database'
```

### SSL/TLS Encryption

SSL/TLS is used to encrypt the connection between your application and the PostgreSQL server, providing security over the network. **pgmonkey** supports various SSL modes:

- `disable`: No SSL.
- `allow`: Attempt SSL connection, fall back to non-SSL if unavailable.
- `prefer`: Attempt SSL connection, fall back to non-SSL if not supported by the server.
- `require`: Require SSL connection.
- `verify-ca`: Require SSL connection and verify the server’s certificate is signed by a trusted CA.
- `verify-full`: Require SSL connection, verify server’s certificate, and ensure the hostname matches.

Example configuration:

```yaml
postgresql:
  connection_type: 'normal'
  connection_settings:
    user: 'your_user'
    password: 'your_password'
    host: 'localhost'
    dbname: 'your_database'
    sslmode: 'require'
    sslrootcert: '/path/to/ca.crt'  # Path to the CA certificate
```

### Certificate-Based Authentication

Certificate-based authentication uses SSL client certificates for authentication instead of or in addition to passwords. This method is highly secure and often used in enterprise environments.

Example configuration:

```yaml
postgresql:
  connection_type: 'normal'
  connection_settings:
    user: 'your_user'
    password: 'your_password'  # Can be optional if using cert authentication only
    host: 'localhost'
    dbname: 'your_database'
    sslmode: 'verify-full'
    sslcert: '/path/to/client.crt'  # Path to the client certificate
    sslkey: '/path/to/client.key'  # Path to the client key
    sslrootcert: '/path/to/ca.crt'  # Path to the root CA certificate
```

This configuration ensures that:
- The connection is encrypted using SSL/TLS.
- The server’s certificate is verified against the specified CA.
- The client authenticates using its own certificate.

## Using the pgmonkey CLI

In addition to the Python API, **pgmonkey** provides a command-line interface (CLI) that allows you to manage your PostgreSQL configurations and connections directly from the terminal. This section will cover the available CLI commands and how to use them.

### Available CLI Commands

Here are the main CLI commands that **pgmonkey** offers:

- `pgmonkey settings`: Manage application settings.
- `pgmonkey pgconfig`: Manage PostgreSQL configurations.
  - `create`: Create a new database configuration file.
  - `test`: Test the database connection using a configuration file.
- `pgmonkey pgserverconfig`: Generate suggested server configuration entries for PostgreSQL.

You can access the help for any command by running:

```bash
pgmonkey --help
```

### Creating a PostgreSQL Configuration Template

To create a new PostgreSQL configuration template using the CLI, you can use the `pgconfig create` command. This command generates a YAML configuration file with a basic template that you can customize.

Example:

```bash
pgmonkey pgconfig create --type pg --filepath /path/to/your/config.yaml
```

In this command:
- `--type pg`: Specifies that the configuration is for PostgreSQL.
- `--filepath /path/to/your/config.yaml`: Specifies the path where the new configuration file will be created.

After running this command, you will have a basic YAML configuration file at the specified location. You can then edit this file to customize the connection settings as needed.

### Testing a Database Connection



Once you have a configuration file, you can test the connection directly from the command line using the `pgconfig test` command. This is useful for verifying that your connection settings are correct before integrating them into your application.

Example:

```bash
pgmonkey pgconfig test --connconfig /path/to/your/config.yaml
```

This command will attempt to connect to the PostgreSQL database using the settings in the specified YAML file. If the connection is successful, it will print the PostgreSQL version and other relevant information.

## Using pgmonkey in Python

After setting up your configuration files and testing them with the CLI, you can use **pgmonkey** in your Python applications.

### Establishing a Connection

Here’s a basic example of how to load a connection configuration and establish a connection using **pgmonkey**:

```python
import asyncio
from pgmonkey import PGConnectionManager

async def main():
    config_file = '/path/to/your/configs/pg_async.yaml'
    connection_manager = PGConnectionManager()

    # Check if connection should be asynchronous or synchronous
    if 'async' in config_file:
        connection = await connection_manager.get_database_connection(config_file)
    else:
        connection = connection_manager.get_database_connection(config_file)  # Sync connection

    try:
        # Handle async connection types
        if connection.connection_type in ['async', 'async_pool']:
            async with connection as conn:
                async with conn.cursor() as cur:
                    await cur.execute('SELECT version();')
                    print(await cur.fetchone())

        # Handle sync connection types
        else:
            with connection as conn:
                with conn.cursor() as cur:
                    cur.execute('SELECT version();')
                    print(cur.fetchone())

    finally:
        await connection.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
```

### Running Database Queries

The example above demonstrates how to run a basic query (`SELECT version();`) to check the PostgreSQL server version. You can replace this query with any SQL command relevant to your use case.

### Handling Different Connection Types

**pgmonkey** dynamically detects the connection type based on the YAML configuration and manages it accordingly.

For example, for a synchronous connection:

```python
if connection.connection_type == 'normal':
    # Handle synchronous connection
```

For an asynchronous pooled connection:

```python
if connection.connection_type == 'async_pool':
    # Handle asynchronous pooled connection
```

## Importing and Exporting Data

pgmonkey provides an easy way to import and export data to and from PostgreSQL using CSV or text files. This functionality is available via the `pgimport` and `pgexport` commands in the CLI.

### Importing Data

To import data from a CSV or text file into a PostgreSQL table, you can use the `pgimport` command. You need to specify the table name, the path to the YAML configuration file, and the file to import.

**Usage**:

```bash
pgmonkey pgimport --table <TABLE> --connconfig <CONFIG_FILE> --import_file <IMPORT_FILE>
```

**Options**:
- `--table <TABLE>`: The name of the table to import the data into. You can specify it as `schema.table` or just `table`.
- `--connconfig <CONFIG_FILE>`: The path to the YAML configuration file that contains the connection details.
- `--import_file <IMPORT_FILE>`: The path to the CSV or text file you wish to import. TSV, PSV etc...

**Example**:

```bash
pgmonkey pgimport --table public.my_table --connconfig /path/to/connection_config.yaml --import_file <CSV_FILE>
```

**Note**: If an import configuration (YAML) doesn't exist, pgmonkey will automatically generate a template for you. You can then modify this template to adjust settings like column mapping, delimiter, or encoding before rerunning the import command.

### Exporting Data

You can also export data from a PostgreSQL table into a CSV file using the `pgexport` command.

**Usage**:

```bash
pgmonkey pgexport --table <TABLE> --connconfig <CONFIG_FILE> [--export_file <CSV_FILE>]
```

**Options**:
- `--table <TABLE>`: The name of the table you want to export. You can specify it as `schema.table` or just `table`.
- `--connconfig <CONFIG_FILE>`: The path to the YAML configuration file with the database connection details.
- `--export_file <CSV_FILE>` (optional): The path to the CSV file where the data will be exported. If not provided, a default file will be generated with the table name.

**Example**:

```bash
pgmonkey pgexport --table public.my_table --connconfig /path/to/connection_config.yaml --export_file /path/to/output.csv
```

This will export the contents of the specified table into the CSV file. If no output file is specified, pgmonkey will create one with a default name based on the table.

### Notes:
- Ensure that your YAML configuration file specifies the correct database connection settings for both import and export operations.
- You can modify the generated YAML template to fine-tune import/export options such as delimiters or encodings.



## Example Use Case: Testing Multiple Connections

Let’s create a script that tests multiple database connections using different configurations:

```python
import asyncio
from pgmonkey import PGConnectionManager

# Function to test asynchronous connections
async def test_async_connection(connection, config_name):
    """Test an asynchronous database connection."""
    async with connection as conn:
        async with conn.cursor() as cur:
            await cur.execute('SELECT version();')
            print(f"{config_name}: {await cur.fetchone()}")

# Function to test synchronous connections
def test_sync_connection(connection, config_name):
    """Test a synchronous database connection."""
    with connection as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT version();')
            print(f"{config_name}: {cur.fetchone()}")

async def test_database_connection(config_file, config_name):
    """Determine connection type and test accordingly."""
    connection_manager = PGConnectionManager()

    # Check if the connection is async or sync
    if 'async' in config_file:
        connection = await connection_manager.get_database_connection(config_file)
    else:
        connection = connection_manager.get_database_connection(config_file)  # Sync connection

    try:
        # Handle async connection
        if connection.connection_type in ['async', 'async_pool']:
            await test_async_connection(connection, config_name)
        # Handle sync connection
        else:
            test_sync_connection(connection, config_name)
    finally:
        # Disconnect appropriately based on async/sync
        if asyncio.iscoroutinefunction(connection.disconnect):
            await connection.disconnect()
        else:
            connection.disconnect()

def main():
    base_dir = '/path/to/your/configs/'
    config_files = {
        'pg_async_pool.yaml': base_dir + 'pg_async_pool.yaml',
        'pg_async.yaml': base_dir + 'pg_async.yaml',
        'pg_normal.yaml': base_dir + 'pg_normal.yaml',
        'pg_pool.yaml': base_dir + 'pg_pool.yaml'
    }

    # Run each connection test
    for config_name, config_file in config_files.items():
        print(f"Testing connection with config: {config_name}")
        asyncio.run(test_database_connection(config_file, config_name))

if __name__ == "__main__":
    main()
```

This script loops through multiple configurations and tests each connection, printing the PostgreSQL version to confirm that the connection works as expected.

## Example Use Case:  Test Pooling Capability

In the following script we test the pooling capability by creating
5 connections taken from the pool.  Make sure your config file specifies enough pool connections.

```python
import asyncio
from pgmonkey import PGConnectionManager

# Function to test multiple async pool connections
async def test_multiple_async_pool_connections(config_file, num_connections):
    connection_manager = PGConnectionManager()
    connections = []

    # Acquire multiple async connections from the pool
    for _ in range(num_connections):
        connection = await connection_manager.get_database_connection(config_file)
        connections.append(connection)

    try:
        # Use each async connection
        for idx, connection in enumerate(connections):
            async with connection as conn:
                async with conn.cursor() as cur:
                    await cur.execute('SELECT version();')
                    version = await cur.fetchone()
                    print(f"Async Connection {idx + 1}: {version}")
    finally:
        # Disconnect all async connections
        for connection in connections:
            await connection.disconnect()

# Function to test multiple sync pool connections
def test_multiple_sync_pool_connections(config_file, num_connections):
    connection_manager = PGConnectionManager()
    connections = []

    # Acquire multiple sync connections from the pool
    for _ in range(num_connections):
        connection = connection_manager.get_database_connection(config_file)  # Sync call
        connections.append(connection)

    try:
        # Use each sync connection
        for idx, connection in enumerate(connections):
            with connection as conn:
                with conn.cursor() as cur:
                    cur.execute('SELECT version();')
                    version = cur.fetchone()
                    print(f"Sync Connection {idx + 1}: {version}")
    finally:
        # Disconnect all sync connections
        for connection in connections:
            connection.disconnect()

async def main():
    base_dir = '/path/to/your/connection/configs/'
    config_files = {
        'async_pool': base_dir + 'pg_async_pool.yaml',
        'pool': base_dir + 'pg_pool.yaml'
    }

    num_connections = 5  # Number of connections to checkout from the pool

    print("Testing async pool connections:")
    await test_multiple_async_pool_connections(config_files['async_pool'], num_connections)

    print("\nTesting sync pool connections:")
    test_multiple_sync_pool_connections(config_files['pool'], num_connections)

if __name__ == "__main__":
    asyncio.run(main())
```

## Conclusion

**pgmonkey** is a versatile and powerful tool for managing PostgreSQL connections in Python. With support for various authentication methods, including SSL/TLS and certificate-based authentication, as well as both synchronous and asynchronous connections, it’s designed to fit a wide range of use cases. The built-in CLI makes it easy to manage configurations and test connections directly from the command line, further enhancing its usability.

By following this tutorial, you should now be able to set up and manage your database connections with ease, both through the CLI and within your Python applications.

For more detailed documentation and to contribute, visit the **pgmonkey** [GitHub repository](https://github.com/RexBytes/pgmonkey).

Happy coding!


## Generating Recommended Server Configuration Entries

In addition to managing client-side database connections, **pgmonkey** can also assist with server-side configurations. While it doesn’t generate the entire PostgreSQL server configuration file (`postgresql.conf`), it provides you with the specific entries that are required or recommended based on your connection settings. This is particularly useful for ensuring that your PostgreSQL server is properly configured to work with the settings specified in your **pgmonkey** configuration file.

### How It Works

The `pgserverconfig` command analyzes your existing **pgmonkey** configuration file and generates the recommended entries for your `postgresql.conf` and `pg_hba.conf` files. These recommendations ensure compatibility with the connection settings you’ve specified, such as SSL requirements, connection pooling, and other critical parameters.

### Using the CLI to Generate Server Config Recommendations

To generate server configuration recommendations, you can use the `pgserverconfig` command from the **pgmonkey** CLI. This command reads your configuration file and outputs the necessary settings for your PostgreSQL server configuration files.

#### Example Command

```bash
pgmonkey pgserverconfig --filepath /path/to/your/config.yaml
```

In this command:
- `--filepath /path/to/your/config.yaml`: Specifies the path to the **pgmonkey** configuration file you want to analyze.

#### Output Example

When you run the command, **pgmonkey** will analyze the configuration file and provide you with entries like the following:

```plaintext
1) Database type detected: PostgreSQL

2) Minimal database server settings needed for this config file:

   a) pg_hba.conf:

TYPE  DATABASE  USER  ADDRESS          METHOD  OPTIONS
hostssl all     all   192.168.0.0/24   md5     clientcert=verify-full

   b) postgresql.conf:

max_connections = 22
ssl = on
ssl_cert_file = 'server.crt'
ssl_key_file = 'server.key'
ssl_ca_file = 'ca.crt'

Please check the following files on your system and ensure that the appropriate settings are applied: pg_hba.conf, postgresql.conf. Ensure that the network ADDRESS matches your network subnet and review all configurations.
```

### What the Output Means

- **`pg_hba.conf` Entries**: These entries configure client authentication, ensuring that the server only allows connections that match the specified criteria, such as SSL client certificates and network addresses.

- **`postgresql.conf` Entries**: These entries configure server settings like `max_connections`, SSL settings, and other parameters that are crucial for the server to handle the types of connections you’ve configured in **pgmonkey**.

### Applying the Recommendations

Once you have the recommended entries:
1. Open your PostgreSQL server configuration files (`pg_hba.conf` and `postgresql.conf`).
2. Add or modify the settings as per the recommendations provided by **pgmonkey**.
3. Restart your PostgreSQL server to apply the changes.

### Why This Is Important

Ensuring that your server is configured correctly is crucial for the smooth operation of your database connections. Misconfigurations can lead to connection failures, security vulnerabilities, or performance issues. By using **pgmonkey** to generate these recommendations, you can be confident that your server is set up to work optimally with the connection settings you’ve defined.
