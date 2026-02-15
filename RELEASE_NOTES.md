# pgmonkey v2.2.0 Release Notes

## Overview

pgmonkey v2.2.0 improves robustness with bug fixes across connection management, adds config validation, introduces `check_on_checkout` and `timeout` pool settings, applies `async_settings` to async pool connections, replaces `print()` with proper `logging`, adds native psycopg/psycopg_pool code generation via `--library psycopg`, and adds live server settings auditing via `--audit`.

## What's New

### Native psycopg Code Generation (`--library psycopg`)

The `generate-code` CLI command now supports a `--library` flag with two choices:

- `pgmonkey` (default) — generates code using pgmonkey's `PGConnectionManager`.
- `psycopg` — generates code using `psycopg` and `psycopg_pool` directly, reading connection settings from the same YAML config file.

All four connection types (`normal`, `pool`, `async`, `async_pool`) have native psycopg templates.

```bash
# Generate native psycopg pool code
pgmonkey pgconfig generate-code --filepath config.yaml --connection-type pool --library psycopg
```

### Bug Fixes

- **Race condition in connection caching** — Fixed with double-check locking pattern. Two threads hitting the same config simultaneously no longer both create connections (one leaking).
- **`NormalConnection.transaction()` disconnect** — Removed `disconnect()` from the `finally` block. Connection lifecycle is now managed externally, consistent with pool connections.
- **Pool `test_connection()` false positive** — Now uses `ExitStack` to hold connections concurrently, properly validating pool capacity instead of sequentially acquiring and returning.
- **`async_settings` not applied to `async_pool`** — GUC settings (`statement_timeout`, `lock_timeout`, etc.) are now applied to every async pool connection via psycopg_pool's `configure` callback.

### Logging Instead of `print()`

All connection classes now use `logging.getLogger(__name__)` instead of `print()`. This follows Python library best practices — users can control output via standard logging configuration. CLI output still uses `print()` where appropriate.

### Config Validation

- Unknown keys in `connection_settings` now produce a warning log message listing the unrecognized keys along with the valid keys.
- Pool settings (`pool_settings` and `async_pool_settings`) are validated: `min_size` cannot exceed `max_size` (raises `ValueError`).

### New Pool Configuration Options

Two new pool settings for both `pool_settings` and `async_pool_settings`:

| Parameter | Description | Default |
|-----------|-------------|---------|
| `timeout` | Seconds to wait for a connection from the pool before raising an error | `30` |
| `check_on_checkout` | Validate connections with `SELECT 1` before handing to caller | `false` |

### Server Settings Audit (`--audit`)

The `pgserverconfig` CLI command now supports an `--audit` flag that connects to the live server and compares current settings against recommendations:

```bash
pgmonkey pgserverconfig --filepath config.yaml --audit
```

- Queries `pg_settings` for `max_connections`, `ssl`, `ssl_cert_file`, `ssl_key_file`, `ssl_ca_file`
- Displays a comparison table: Setting, Recommended, Current, Source, Status (OK / MISMATCH / REVIEW / UNKNOWN)
- Inspects `pg_hba_file_rules` (PostgreSQL 15+) when available
- Gracefully handles permission errors — falls back to recommendations only
- Entirely read-only — no server settings are modified

Without `--audit`, the command works exactly as before.

### Project Scope Document

Added `PROJECTSCOPE.md` defining core responsibilities, explicit non-goals, design principles, architecture boundaries, and PR guidelines.

## Compatibility

No breaking API changes. All existing code continues to work as before.

| Dependency | Supported Versions |
|---|---|
| Python | 3.10, 3.11, 3.12, 3.13 |
| psycopg[binary] | >= 3.1.20, < 4.0.0 |
| psycopg_pool | >= 3.1.9, < 4.0.0 |
| PyYAML | >= 6.0.2, < 7.0.0 |

## Test Suite

180 unit tests (up from 132 in v2.1.0), all passing. New tests cover:

- Logging output (`caplog`) instead of `print()` (`capsys`)
- `NormalConnection.transaction()` commit/rollback without disconnect
- `check_on_checkout` pool configuration
- Config validation (unknown keys warning, pool range validation)
- `async_settings` passthrough to async pool connections
- Native psycopg code generation for all 4 connection types
- Backward compatibility (default library is pgmonkey)
- Server settings inspector (permission handling, comparison logic, HBA rules)
- Audit output formatting (comparison table, fallback on permission denied)

## Files Changed

- `src/pgmonkey/connections/postgres/normal_connection.py` — Logging, transaction fix
- `src/pgmonkey/connections/postgres/async_connection.py` — Logging
- `src/pgmonkey/connections/postgres/pool_connection.py` — Logging, ExitStack test, check_on_checkout
- `src/pgmonkey/connections/postgres/async_pool_connection.py` — Logging, async_settings configure callback, check_on_checkout
- `src/pgmonkey/connections/postgres/postgres_connection_factory.py` — Config validation, async_settings passthrough
- `src/pgmonkey/managers/pgconnection_manager.py` — Logging, double-check locking
- `src/pgmonkey/common/templates/postgres.yaml` — timeout, check_on_checkout
- `src/pgmonkey/tools/connection_code_generator.py` — Native psycopg templates, library dispatch
- `src/pgmonkey/managers/pgcodegen_manager.py` — Library parameter
- `src/pgmonkey/cli/cli_pgconfig_subparser.py` — `--library` CLI argument
- `src/pgmonkey/cli/cli_pg_server_config_subparser.py` — `--audit` CLI argument
- `src/pgmonkey/serversettings/postgres_server_settings_inspector.py` — New: queries live server pg_settings and pg_hba_file_rules
- `src/pgmonkey/serversettings/postgres_server_config_generator.py` — Audit comparison output
- `src/pgmonkey/managers/pg_server_config_manager.py` — Audit connection and fallback logic
- `src/pgmonkey/tests/unit/` — Updated and new test files
- `PROJECTSCOPE.md` — New project scope document
- `README.md` — Documentation updates
- `docs/` — Website documentation updates

---

# pgmonkey v2.1.0 Release Notes

## Overview

pgmonkey v2.1.0 adds always-on connection caching to prevent pool storms, fixes a critical async pool lifecycle bug, and introduces best practice documentation with production-ready code recipes.

## What's New

### Always-On Connection Caching

Connections and pools are now automatically cached by config content. Repeated calls to `get_database_connection()` with the same configuration return the existing connection or pool instead of creating a new one.

This prevents "pool storms" — a common pitfall where each call inadvertently opens a brand-new connection pool, quickly exhausting database server connections.

**New API:**

| Method / Parameter | Description |
|---|---|
| `manager.cache_info` | Returns cache size and connection types |
| `manager.clear_cache()` | Disconnects all cached connections (sync) |
| `await manager.clear_cache_async()` | Disconnects all cached connections (async) |
| `force_reload=True` | Replace a cached connection with a fresh one |

Cache keys are computed from a SHA-256 hash of the full config dictionary, so different configs get different cache entries regardless of file path. The cache is thread-safe and protected by a threading lock.

An `atexit` handler automatically performs best-effort cleanup of all cached connections when the process exits.

### Async Pool Lifecycle Fix

**Fixed:** `async with pool_connection:` no longer destroys the pool on exit.

Previously, `PGAsyncPoolConnection.__aexit__()` called `disconnect()`, which closed the entire `AsyncConnectionPool`. This meant the pool was destroyed after a single `async with` block and could not be reused.

Now, `async with` borrows a connection from the pool and returns it when the block exits — matching how the sync pool (`PGPoolConnection`) already works. The pool stays open for reuse across multiple `async with` blocks. Clean exits auto-commit; exceptions auto-rollback.

`cursor()` and `transaction()` are now dual-mode: inside an `async with` block they use the already-acquired connection; outside they acquire their own connection from the pool (standalone usage).

### Best Practice Documentation

New documentation covering production-ready usage patterns:

- **Best Practices page** (`docs/best_practices.html`) — Code recipes for all 4 connection types, Flask and FastAPI app-level design patterns, cache management API reference, and a quick reference table.
- **README section** — Best Practice Recipes with app-level patterns and cache management reference.
- Navigation updated across all doc pages.

## Compatibility

No breaking API changes. All existing code continues to work as before — caching is transparent and automatic. The `force_reload` parameter is the only new parameter on existing methods, and it defaults to `False`.

| Dependency | Supported Versions |
|---|---|
| Python | 3.10, 3.11, 3.12, 3.13 |
| psycopg[binary] | >= 3.1.20, < 4.0.0 |
| psycopg_pool | >= 3.1.9, < 4.0.0 |
| PyYAML | >= 6.0.2, < 7.0.0 |

## Test Suite

132 unit tests (up from 113 in v2.0.0), all passing. New tests cover:

- Sync and async connection caching (same config returns cached instance)
- `force_reload` disconnects old and creates new
- Cache info and clear cache
- `connection_type` override with caching
- atexit cleanup (including error handling)
- Config hash stability and key-order independence
- Async pool context manager (borrow/return, rollback on exception, reusability, cursor inside context)

## Files Changed

- `src/pgmonkey/managers/pgconnection_manager.py` — Connection caching, atexit cleanup, cache management API
- `src/pgmonkey/connections/postgres/async_pool_connection.py` — Async pool lifecycle fix
- `src/pgmonkey/tests/unit/test_connection_caching.py` — 19 new tests
- `docs/best_practices.html` — New documentation page
- `docs/index.html` — Navigation update
- `docs/reference.html` — Navigation update, test count update
- `README.md` — Best Practice Recipes section
- `ISSUES.md` — Internal issue tracker (not published)
- `pyproject.toml` — Version bump to 2.1.0
