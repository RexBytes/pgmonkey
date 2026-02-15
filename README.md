# Getting Started with pgmonkey

**pgmonkey** is a Python library for managing PostgreSQL database connections. It supports normal, pooled, async, and async-pooled connections using a single YAML configuration file. Authentication methods include password, SSL/TLS, and certificate-based authentication. A CLI is included for managing configurations and testing connections.

## Table of Contents

1. [Installation](#installation)
2. [One Config File, All Connection Types](#one-config-file-all-connection-types)
3. [YAML Configuration Reference](#yaml-configuration-reference)
   - [Connection Settings](#connection-settings)
   - [Pool Settings](#pool-settings)
   - [Async Settings](#async-settings)
   - [Async Pool Settings](#async-pool-settings)
4. [Authentication Methods](#authentication-methods)
   - [Password-Based Authentication](#password-based-authentication)
   - [SSL/TLS Encryption](#ssltls-encryption)
   - [Certificate-Based Authentication](#certificate-based-authentication)
5. [Using the CLI](#using-the-cli)
   - [Creating a Configuration Template](#creating-a-configuration-template)
   - [Testing a Connection](#testing-a-connection)
   - [Generating Python Code](#generating-python-code)
   - [Server Configuration Recommendations](#server-configuration-recommendations)
   - [Importing and Exporting Data](#importing-and-exporting-data)
6. [Using pgmonkey in Python](#using-pgmonkey-in-python)
   - [Normal (Synchronous) Connection](#normal-synchronous-connection)
   - [Pooled Connection](#pooled-connection)
   - [Async Connection](#async-connection)
   - [Async Pooled Connection](#async-pooled-connection)
   - [Using the Config File Default](#using-the-config-file-default)
   - [Transactions, Commit, and Rollback](#transactions-commit-and-rollback)
7. [Best Practice Recipes](#best-practice-recipes)
8. [Testing All Connection Types](#testing-all-connection-types)
9. [Testing Pool Capacity](#testing-pool-capacity)
10. [Running the Test Suite](#running-the-test-suite)

## Installation

Install from PyPI:

```bash
pip install pgmonkey
```

Or install from source:

```bash
git clone https://github.com/RexBytes/pgmonkey.git
cd pgmonkey
pip install .
```

To install with test dependencies:

```bash
pip install pgmonkey[test]
```

## One Config File, All Connection Types

In v2.0.0, pgmonkey uses a **single YAML configuration file** for all connection types. Instead of maintaining separate config files for normal, pool, async, and async_pool connections, you define everything in one file and specify the connection type when you call the API:

```python
from pgmonkey import PGConnectionManager

manager = PGConnectionManager()

# Same config file, different connection types
conn = manager.get_database_connection('config.yaml', 'normal')
conn = manager.get_database_connection('config.yaml', 'pool')
conn = await manager.get_database_connection('config.yaml', 'async')
conn = await manager.get_database_connection('config.yaml', 'async_pool')
```

The `connection_type` parameter is optional. If omitted, pgmonkey uses the `connection_type` value from the YAML file (which defaults to `'normal'`).

## YAML Configuration Reference

Here is the full configuration template. You only need to fill in the sections relevant to the connection types you plan to use.

```yaml
postgresql:
  # Default connection type when none is specified in the API call.
  # Options: 'normal', 'pool', 'async', 'async_pool'
  # You can override this per-call:
  #   manager.get_database_connection('config.yaml', 'pool')
  connection_type: 'normal'

  connection_settings:
    user: 'postgres'
    password: 'password'
    host: 'localhost'
    port: '5432'
    dbname: 'mydatabase'
    sslmode: 'prefer'  # Options: disable, allow, prefer, require, verify-ca, verify-full
    sslcert: ''  # Path to the client SSL certificate, if needed
    sslkey: ''  # Path to the client SSL key, if needed
    sslrootcert: ''  # Path to the root SSL certificate, if needed
    connect_timeout: '10'  # Maximum wait for connection, in seconds
    application_name: 'myapp'
    keepalives: '1'  # Enable TCP keepalives (1=on, 0=off)
    keepalives_idle: '60'  # Seconds before sending a keepalive probe
    keepalives_interval: '15'  # Seconds between keepalive probes
    keepalives_count: '5'  # Max keepalive probes before closing the connection

  # Settings for 'pool' connection type
  pool_settings:
    min_size: 5
    max_size: 20
    timeout: 30  # Seconds to wait for a connection from the pool before raising an error
    max_idle: 300  # Seconds a connection can remain idle before being closed
    max_lifetime: 3600  # Seconds a connection can be reused
    check_on_checkout: false  # Validate connections with SELECT 1 before handing to caller

  # Settings for 'async' connection type (applied via SET commands on connection)
  # These settings are also applied to 'async_pool' connections via a configure callback.
  async_settings:
    idle_in_transaction_session_timeout: '5000'  # Timeout for idle in transaction (ms)
    statement_timeout: '30000'  # Cancel statements exceeding this time (ms)
    lock_timeout: '10000'  # Timeout for acquiring locks (ms)
    # work_mem: '256MB'  # Memory for sort operations and more

  # Settings for 'async_pool' connection type
  async_pool_settings:
    min_size: 5
    max_size: 20
    timeout: 30  # Seconds to wait for a connection from the pool before raising an error
    max_idle: 300
    max_lifetime: 3600
    check_on_checkout: false  # Validate connections with SELECT 1 before handing to caller
```

### Connection Settings

| Parameter | Description | Example |
|-----------|-------------|---------|
| `user` | Username for the PostgreSQL database | `'postgres'` |
| `password` | Password for the database user | `'password'` |
| `host` | Database server host address | `'localhost'` |
| `port` | Database server port | `'5432'` |
| `dbname` | Name of the database to connect to | `'mydatabase'` |
| `sslmode` | SSL mode (disable, allow, prefer, require, verify-ca, verify-full) | `'prefer'` |
| `sslcert` | Path to the client SSL certificate | `'/path/to/client.crt'` |
| `sslkey` | Path to the client SSL key | `'/path/to/client.key'` |
| `sslrootcert` | Path to the root SSL certificate | `'/path/to/ca.crt'` |
| `connect_timeout` | Maximum wait for connection in seconds | `'10'` |
| `application_name` | Application name reported to PostgreSQL | `'myapp'` |
| `keepalives` | Enable TCP keepalives (1=on, 0=off) | `'1'` |
| `keepalives_idle` | Seconds before sending a keepalive probe | `'60'` |
| `keepalives_interval` | Seconds between keepalive probes | `'15'` |
| `keepalives_count` | Max keepalive probes before closing | `'5'` |

### Pool Settings

Used by `pool` connection type.

| Parameter | Description | Example |
|-----------|-------------|---------|
| `min_size` | Minimum number of connections in the pool | `5` |
| `max_size` | Maximum number of connections in the pool | `20` |
| `timeout` | Seconds to wait for a connection from the pool before raising an error | `30` |
| `max_idle` | Seconds a connection can remain idle before being closed | `300` |
| `max_lifetime` | Seconds a connection can be reused | `3600` |
| `check_on_checkout` | Validate connections with `SELECT 1` before handing to caller | `false` |

### Async Settings

Used by `async` and `async_pool` connection types. These are applied via SQL `SET` commands when the connection is established. For `async_pool`, they are applied to each connection via a psycopg_pool `configure` callback.

| Parameter | Description | Example |
|-----------|-------------|---------|
| `idle_in_transaction_session_timeout` | Timeout for idle in transaction (ms) | `'5000'` |
| `statement_timeout` | Cancel statements exceeding this time (ms) | `'30000'` |
| `lock_timeout` | Timeout for acquiring locks (ms) | `'10000'` |
| `work_mem` | Memory for sort operations | `'256MB'` |

### Async Pool Settings

Used by `async_pool` connection type. Same parameters as pool settings. The `async_settings` section (above) is also applied to async pool connections.

| Parameter | Description | Example |
|-----------|-------------|---------|
| `min_size` | Minimum connections in the async pool | `5` |
| `max_size` | Maximum connections in the async pool | `20` |
| `timeout` | Seconds to wait for a connection from the pool before raising an error | `30` |
| `max_idle` | Seconds a connection can remain idle | `300` |
| `max_lifetime` | Seconds a connection can be reused | `3600` |
| `check_on_checkout` | Validate connections with `SELECT 1` before handing to caller | `false` |

## Authentication Methods

### Password-Based Authentication

The most common method. Credentials are sent to the PostgreSQL server for validation.

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

SSL/TLS encrypts the connection between your application and the PostgreSQL server. pgmonkey supports these SSL modes:

- `disable`: No SSL.
- `allow`: Attempt SSL, fall back to non-SSL if unavailable.
- `prefer`: Attempt SSL, fall back to non-SSL if not supported.
- `require`: Require SSL connection.
- `verify-ca`: Require SSL and verify the server's certificate is signed by a trusted CA.
- `verify-full`: Require SSL, verify certificate, and ensure the hostname matches.

```yaml
postgresql:
  connection_type: 'normal'
  connection_settings:
    user: 'your_user'
    password: 'your_password'
    host: 'localhost'
    dbname: 'your_database'
    sslmode: 'require'
    sslrootcert: '/path/to/ca.crt'
```

### Certificate-Based Authentication

Uses SSL client certificates for authentication. Highly secure and often used in enterprise environments.

```yaml
postgresql:
  connection_type: 'normal'
  connection_settings:
    user: 'your_user'
    password: 'your_password'
    host: 'localhost'
    dbname: 'your_database'
    sslmode: 'verify-full'
    sslcert: '/path/to/client.crt'
    sslkey: '/path/to/client.key'
    sslrootcert: '/path/to/ca.crt'
```

## Using the CLI

pgmonkey provides a command-line interface for managing configurations and connections.

```bash
pgmonkey --help
```

### Creating a Configuration Template

Generate a YAML configuration template:

```bash
pgmonkey pgconfig create --type pg --filepath /path/to/config.yaml
```

This creates a configuration file with all available settings and sensible defaults. Edit the file to customize your connection settings.

### Testing a Connection

Test a connection using your configuration file:

```bash
# Test using the connection_type from the config file
pgmonkey pgconfig test --connconfig /path/to/config.yaml

# Test a specific connection type (overrides config file)
pgmonkey pgconfig test --connconfig /path/to/config.yaml --connection-type pool
pgmonkey pgconfig test --connconfig /path/to/config.yaml --connection-type async
```

The `--connection-type` flag accepts: `normal`, `pool`, `async`, `async_pool`.

### Generating Python Code

Generate example Python code for a connection type:

```bash
# Generate code using the config file's default connection type
pgmonkey pgconfig generate-code --filepath /path/to/config.yaml

# Generate code for a specific connection type
pgmonkey pgconfig generate-code --filepath /path/to/config.yaml --connection-type async_pool

# Generate code using native psycopg/psycopg_pool instead of pgmonkey
pgmonkey pgconfig generate-code --filepath /path/to/config.yaml --connection-type pool --library psycopg
```

The `--library` flag controls which library the generated code targets:

- `pgmonkey` (default) — generates code using pgmonkey's `PGConnectionManager`.
- `psycopg` — generates code using `psycopg` and `psycopg_pool` directly, reading connection settings from the same YAML config file.

### Server Configuration Recommendations

Generate recommended PostgreSQL server configuration entries based on your config file:

```bash
pgmonkey pgserverconfig --filepath /path/to/config.yaml
```

This analyzes your configuration and outputs recommended entries for `postgresql.conf` and `pg_hba.conf`:

```
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
```

### Importing and Exporting Data

**Import data** from a CSV or text file into a PostgreSQL table:

```bash
pgmonkey pgimport --table public.my_table --connconfig /path/to/config.yaml --import_file /path/to/data.csv
```

If an import configuration file doesn't exist, pgmonkey generates a template you can edit to adjust column mapping, delimiter, and encoding.

**Export data** from a PostgreSQL table to a CSV file:

```bash
pgmonkey pgexport --table public.my_table --connconfig /path/to/config.yaml --export_file /path/to/output.csv
```

If `--export_file` is omitted, a default file is generated using the table name.

## Using pgmonkey in Python

### Normal (Synchronous) Connection

```python
from pgmonkey import PGConnectionManager

def main():
    manager = PGConnectionManager()
    connection = manager.get_database_connection('config.yaml', 'normal')

    with connection as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT version();')
            print(cur.fetchone())

if __name__ == "__main__":
    main()
```

### Pooled Connection

```python
from pgmonkey import PGConnectionManager

def main():
    manager = PGConnectionManager()
    pool_connection = manager.get_database_connection('config.yaml', 'pool')

    # Each 'with' block acquires and releases a connection from the pool
    with pool_connection as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT version();')
            print(cur.fetchone())

if __name__ == "__main__":
    main()
```

### Async Connection

```python
import asyncio
from pgmonkey import PGConnectionManager

async def main():
    manager = PGConnectionManager()
    connection = await manager.get_database_connection('config.yaml', 'async')

    async with connection as conn:
        async with conn.cursor() as cur:
            await cur.execute('SELECT version();')
            print(await cur.fetchone())

if __name__ == "__main__":
    asyncio.run(main())
```

### Async Pooled Connection

```python
import asyncio
from pgmonkey import PGConnectionManager

async def main():
    manager = PGConnectionManager()
    pool_connection = await manager.get_database_connection('config.yaml', 'async_pool')

    # Each 'async with' cursor block acquires and releases a connection from the pool
    async with pool_connection as conn:
        async with conn.cursor() as cur:
            await cur.execute('SELECT version();')
            print(await cur.fetchone())

if __name__ == "__main__":
    asyncio.run(main())
```

### Using the Config File Default

If you omit the `connection_type` parameter, pgmonkey uses the value from your YAML file:

```python
# Uses whatever connection_type is set in config.yaml (defaults to 'normal')
connection = manager.get_database_connection('config.yaml')
```

### Transactions, Commit, and Rollback

pgmonkey connections support transactions via context managers:

```python
# Synchronous transaction
with connection as conn:
    with conn.transaction():
        with conn.cursor() as cur:
            cur.execute('INSERT INTO my_table (name) VALUES (%s)', ('Alice',))
            cur.execute('SELECT * FROM my_table WHERE name = %s', ('Alice',))
            print(cur.fetchall())

# Asynchronous transaction
async with connection as conn:
    async with conn.transaction():
        async with conn.cursor() as cur:
            await cur.execute('INSERT INTO my_table (name) VALUES (%s)', ('Alice',))
            await cur.execute('SELECT * FROM my_table WHERE name = %s', ('Alice',))
            print(await cur.fetchall())
```

Manual commit and rollback are available when not using the transaction context:

```python
# Manual commit
async with connection as conn:
    async with conn.cursor() as cur:
        await cur.execute('UPDATE my_table SET name = %s WHERE id = %s', ('Doe', 1))
    await conn.commit()

# Manual rollback on error
try:
    async with connection as conn:
        async with conn.cursor() as cur:
            await cur.execute('DELETE FROM my_table WHERE id = %s', (1,))
        await conn.commit()
except Exception as e:
    await conn.rollback()
```

## Best Practice Recipes

pgmonkey handles several production concerns behind the scenes so you don't have to:

- **Connection caching** — Connections and pools are cached by config content (SHA-256 hash). Repeated calls with the same config return the existing instance, preventing "pool storms" where each call opens a new pool.
- **Async pool lifecycle** — `async with pool_conn:` borrows a connection from the pool and returns it when the block exits. The pool stays open for reuse. Auto-commits on clean exit, rolls back on exception.
- **atexit cleanup** — All cached connections are automatically closed when the process exits.
- **Thread-safe caching** — The connection cache is protected by a threading lock with double-check locking to prevent race conditions.
- **Config validation** — Unknown connection setting keys produce a warning log message. Pool settings are validated (e.g., `min_size` cannot exceed `max_size`).

### App-Level Pattern: Sync Database Class (Flask)

```python
from pgmonkey import PGConnectionManager

class Database:
    def __init__(self, config_path):
        self.manager = PGConnectionManager()
        self.config_path = config_path
        # Pool is created on first call, cached thereafter
        self.pool = self.manager.get_database_connection(config_path, 'pool')

    def fetch_one(self, query, params=None):
        with self.pool as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                return cur.fetchone()

    def fetch_all(self, query, params=None):
        with self.pool as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                return cur.fetchall()

    def execute(self, query, params=None):
        with self.pool as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)

# Usage in Flask
from flask import Flask

app = Flask(__name__)
db = Database('/path/to/config.yaml')

@app.route('/users')
def list_users():
    rows = db.fetch_all('SELECT id, name FROM users ORDER BY id;')
    return {'users': [{'id': r[0], 'name': r[1]} for r in rows]}
```

### App-Level Pattern: Async Database Class (FastAPI)

```python
import asyncio
from pgmonkey import PGConnectionManager

class AsyncDatabase:
    def __init__(self, config_path):
        self.manager = PGConnectionManager()
        self.config_path = config_path
        self.pool = None

    async def connect(self):
        self.pool = await self.manager.get_database_connection(
            self.config_path, 'async_pool'
        )

    async def disconnect(self):
        await self.manager.clear_cache_async()

    async def fetch_one(self, query, params=None):
        async with self.pool as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, params)
                return await cur.fetchone()

    async def fetch_all(self, query, params=None):
        async with self.pool as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, params)
                return await cur.fetchall()

    async def execute(self, query, params=None):
        async with self.pool as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, params)

# Usage in FastAPI
from fastapi import FastAPI

app = FastAPI()
db = AsyncDatabase('/path/to/config.yaml')

@app.on_event("startup")
async def startup():
    await db.connect()

@app.on_event("shutdown")
async def shutdown():
    await db.disconnect()

@app.get("/orders")
async def list_orders():
    rows = await db.fetch_all('SELECT id, total FROM orders ORDER BY id;')
    return {"orders": [{"id": r[0], "total": r[1]} for r in rows]}
```

### Cache Management

| Method | Description |
|--------|-------------|
| `manager.cache_info` | Returns dict with `size` and `connection_types` of cached connections |
| `manager.clear_cache()` | Disconnects all cached connections (sync) |
| `await manager.clear_cache_async()` | Disconnects all cached connections (async) |
| `force_reload=True` | Pass to `get_database_connection()` to replace a cached connection |

### Quick Reference

| Type | Best For | Cached? | Context Manager |
|------|----------|---------|-----------------|
| `normal` | Scripts, CLI tools | Yes | `with conn:` |
| `pool` | Flask, Django, threaded apps | Yes | `with pool:` borrows/returns |
| `async` | Async scripts | Yes | `async with conn:` |
| `async_pool` | FastAPI, aiohttp, high concurrency | Yes | `async with pool:` borrows/returns |

For full recipes with code examples for every connection type, see the [Best Practices](https://rexbytes.github.io/pgmonkey/best_practices.html) documentation page.

## Testing All Connection Types

Test all four connection types using a single config file:

```python
import asyncio
from pgmonkey import PGConnectionManager

def test_sync(manager, config_file, connection_type):
    connection = manager.get_database_connection(config_file, connection_type)
    with connection as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT version();')
            print(f"{connection_type}: {cur.fetchone()}")

async def test_async(manager, config_file, connection_type):
    connection = await manager.get_database_connection(config_file, connection_type)
    async with connection as conn:
        async with conn.cursor() as cur:
            await cur.execute('SELECT version();')
            print(f"{connection_type}: {await cur.fetchone()}")

async def main():
    manager = PGConnectionManager()
    config_file = '/path/to/config.yaml'

    # Test synchronous connections
    test_sync(manager, config_file, 'normal')
    test_sync(manager, config_file, 'pool')

    # Test asynchronous connections
    await test_async(manager, config_file, 'async')
    await test_async(manager, config_file, 'async_pool')

if __name__ == "__main__":
    asyncio.run(main())
```

## Testing Pool Capacity

Test pooling by acquiring multiple connections from the same pool:

```python
import asyncio
from pgmonkey import PGConnectionManager

async def test_async_pool(config_file, num_connections):
    manager = PGConnectionManager()
    connections = []

    for _ in range(num_connections):
        connection = await manager.get_database_connection(config_file, 'async_pool')
        connections.append(connection)

    for idx, connection in enumerate(connections):
        async with connection as conn:
            async with conn.cursor() as cur:
                await cur.execute('SELECT version();')
                version = await cur.fetchone()
                print(f"Async pool connection {idx + 1}: {version}")

    for connection in connections:
        await connection.disconnect()

def test_sync_pool(config_file, num_connections):
    manager = PGConnectionManager()
    connections = []

    for _ in range(num_connections):
        connection = manager.get_database_connection(config_file, 'pool')
        connections.append(connection)

    for idx, connection in enumerate(connections):
        with connection as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT version();')
                version = cur.fetchone()
                print(f"Sync pool connection {idx + 1}: {version}")

    for connection in connections:
        connection.disconnect()

async def main():
    config_file = '/path/to/config.yaml'
    num_connections = 5

    print("Testing async pool:")
    await test_async_pool(config_file, num_connections)

    print("\nTesting sync pool:")
    test_sync_pool(config_file, num_connections)

if __name__ == "__main__":
    asyncio.run(main())
```

## Running the Test Suite

pgmonkey includes a comprehensive unit test suite that runs without a database connection.

Install test dependencies:

```bash
pip install pgmonkey[test]
```

Run the tests:

```bash
pytest
```

The test suite uses mocks and covers all connection types, the connection factory, configuration management, code generation (both pgmonkey and native psycopg), config validation, and server config generation.

---

For more information, visit the [GitHub repository](https://github.com/RexBytes/pgmonkey).
