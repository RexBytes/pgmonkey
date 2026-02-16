# pgmonkey v3.0.0 Release Notes

## A Simpler, Safer, Stronger pgmonkey

pgmonkey v3.0.0 is here - and it's our biggest release yet! This version brings a cleaner
config format, a hardened connection layer, and dozens of fixes that make pgmonkey more
reliable than ever. Whether you're running a quick script or powering a production service,
v3.0.0 has something great for you.

## Highlights

### Simplified YAML Configuration

Say goodbye to the extra `postgresql:` wrapper! Your config files are now cleaner and easier
to read. Settings live at the root level - no more unnecessary nesting.

**Before (v2.x):**
```yaml
postgresql:
  connection_type: 'normal'
  connection_settings:
    host: 'localhost'
    dbname: 'mydb'
```

**Now (v3.0.0):**
```yaml
connection_type: 'normal'
connection_settings:
  host: 'localhost'
  dbname: 'mydb'
```

Already have v2.x config files? No problem - pgmonkey auto-detects the old format and
handles it seamlessly with a friendly deprecation notice guiding you to update at your pace.

### Rock-Solid Connection Safety

We took a hard look at every connection path and made sure nothing slips through the cracks:

- **Pool connections done right** - The sync pool context manager now correctly returns
  connections to the pool on exit, fixing a double-commit bug and preventing connection leaks.
  Thread safety is guaranteed with per-thread context tracking via `threading.local`.

- **No more connection leaks** - Normal and async connections now use `try/finally` in their
  exit handlers, so `disconnect()` always runs - even if commit or rollback throws an exception.

- **Async pool isolation** - Each `PGAsyncPoolConnection` instance now has its own
  `ContextVar` storage, so nested `async with` blocks on different pool instances never
  interfere with each other.

- **Smarter caching** - The connection cache key now includes the connection type, so
  requesting the same config as `'normal'` vs `'pool'` correctly returns different cached
  connections.

### SQL Injection Protection for GUC Settings

All four connection types (normal, pool, async, async_pool) now use psycopg's safe SQL
composition (`sql.SQL` / `sql.Identifier`) for `SET` commands. The generated code templates
teach the same safe pattern, so your team builds good habits from day one.

### Bulletproof Config Handling

- Empty passwords (`password: ''`) and zero values (`keepalives: 0`) are no longer silently
  dropped. The config filter now uses `is not None` to preserve every valid value you set.
- `max_size` in pool settings gracefully handles string values from YAML (`"10"` with quotes)
  by casting to `int`.
- File paths with special characters (like `o'brien`) are properly escaped in generated code
  via `repr()`.

### CSV Import/Export Improvements

- **BOM detection fixed** - UTF-32 BOMs are now correctly detected before UTF-16 BOMs,
  preventing misidentification of UTF-32 encoded files.
- **Accurate progress bars** - The CSV exporter now counts actual rows instead of byte chunks,
  giving you a truthful progress bar during large exports.

### Server Audit Fixes

- **No more NULL crashes** - If `pg_settings` returns NULL for a setting value, the audit
  gracefully reports `UNKNOWN` status instead of crashing.
- **Correct HBA recommendations** - For SSL-enabled connections, the audit now recommends
  `hostssl ... md5` instead of the incorrectly blocking `host ... reject` rule.

## New Dependencies

| Dependency | Version | Purpose |
|---|---|---|
| `chardet` | >= 5.2.0, < 6.0.0 | Character encoding detection for CSV imports |
| `tqdm` | >= 4.64.0, < 5.0.0 | Progress bars for CSV import/export operations |

## Backward Compatibility

The simplified YAML config is the only breaking change - and it's handled gracefully.
Old-format configs with the `postgresql:` wrapper key are auto-detected and unwrapped at
runtime with a `DeprecationWarning`. Your existing configs will keep working while you
transition to the new format.

All Python APIs remain unchanged. No code changes needed in your application.

## Compatibility

| Dependency | Supported Versions |
|---|---|
| Python | 3.10, 3.11, 3.12, 3.13 |
| psycopg[binary] | >= 3.1.20, < 4.0.0 |
| psycopg_pool | >= 3.1.9, < 4.0.0 |
| PyYAML | >= 6.0.2, < 7.0.0 |
| chardet | >= 5.2.0, < 6.0.0 |
| tqdm | >= 4.64.0, < 5.0.0 |

## Test Suite

229 unit tests (up from 180 in v2.3.0), all passing. New tests cover thread safety, async
context isolation, SQL composition safety, config edge cases, BOM detection ordering, and
export progress accuracy.

## Thank You

This release reflects a thorough, multi-round security and reliability review. Every
connection type, every edge case, every generated code template was scrutinized and
strengthened. pgmonkey v3.0.0 is the most robust version we've ever shipped - enjoy!

---

# pgmonkey v2.3.0 Release Notes

## Overview

pgmonkey v2.3.0 adds live server settings auditing via the new `--audit` flag on the `pgserverconfig` CLI command. This feature connects to a running PostgreSQL server, queries its current configuration, and compares it against recommended settings.

## What's New

### Server Settings Audit (`--audit`)

The `pgserverconfig` CLI command now supports an `--audit` flag that connects to the live server and compares current settings against recommendations:

```bash
pgmonkey pgserverconfig --filepath config.yaml --audit
```

- Queries `pg_settings` for `max_connections`, `ssl`, `ssl_cert_file`, `ssl_key_file`, `ssl_ca_file`
- Displays a comparison table: Setting, Recommended, Current, Source, Status (OK / MISMATCH / REVIEW / UNKNOWN)
- Inspects `pg_hba_file_rules` (PostgreSQL 15+) when available
- Gracefully handles permission errors - falls back to recommendations only
- Entirely read-only - no server settings are modified

Without `--audit`, the command works exactly as before.

## Compatibility

No breaking API changes. All existing code continues to work as before.

| Dependency | Supported Versions |
|---|---|
| Python | 3.10, 3.11, 3.12, 3.13 |
| psycopg[binary] | >= 3.1.20, < 4.0.0 |
| psycopg_pool | >= 3.1.9, < 4.0.0 |
| PyYAML | >= 6.0.2, < 7.0.0 |

## Test Suite

180 unit tests (up from 149 in v2.2.0), all passing. New tests cover:

- Server settings inspector (permission handling, comparison logic, HBA rules)
- Audit output formatting (comparison table, fallback on permission denied)

## Files Changed

- `src/pgmonkey/cli/cli_pg_server_config_subparser.py` - `--audit` CLI argument
- `src/pgmonkey/serversettings/postgres_server_settings_inspector.py` - New: queries live server pg_settings and pg_hba_file_rules
- `src/pgmonkey/serversettings/postgres_server_config_generator.py` - Audit comparison output
- `src/pgmonkey/managers/pg_server_config_manager.py` - Audit connection and fallback logic
- `src/pgmonkey/tests/unit/test_server_settings_inspector.py` - 26 new tests
- `src/pgmonkey/tests/unit/test_server_config_generator.py` - 5 new audit tests
- `README.md` - Documentation updates
- `docs/` - Website documentation updates

---

# pgmonkey v2.2.0 Release Notes

## Overview

pgmonkey v2.2.0 improves robustness with bug fixes across connection management, adds config validation, introduces `check_on_checkout` and `timeout` pool settings, applies `async_settings` to async pool connections, replaces `print()` with proper `logging`, and adds native psycopg/psycopg_pool code generation via `--library psycopg`.

## What's New

### Native psycopg Code Generation (`--library psycopg`)

The `generate-code` CLI command now supports a `--library` flag with two choices:

- `pgmonkey` (default) - generates code using pgmonkey's `PGConnectionManager`.
- `psycopg` - generates code using `psycopg` and `psycopg_pool` directly, reading connection settings from the same YAML config file.

All four connection types (`normal`, `pool`, `async`, `async_pool`) have native psycopg templates.

```bash
# Generate native psycopg pool code
pgmonkey pgconfig generate-code --filepath config.yaml --connection-type pool --library psycopg
```

### Bug Fixes

- **Race condition in connection caching** - Fixed with double-check locking pattern. Two threads hitting the same config simultaneously no longer both create connections (one leaking).
- **`NormalConnection.transaction()` disconnect** - Removed `disconnect()` from the `finally` block. Connection lifecycle is now managed externally, consistent with pool connections.
- **Pool `test_connection()` false positive** - Now uses `ExitStack` to hold connections concurrently, properly validating pool capacity instead of sequentially acquiring and returning.
- **`async_settings` not applied to `async_pool`** - GUC settings (`statement_timeout`, `lock_timeout`, etc.) are now applied to every async pool connection via psycopg_pool's `configure` callback.

### Logging Instead of `print()`

All connection classes now use `logging.getLogger(__name__)` instead of `print()`. This follows Python library best practices - users can control output via standard logging configuration. CLI output still uses `print()` where appropriate.

### Config Validation

- Unknown keys in `connection_settings` now produce a warning log message listing the unrecognized keys along with the valid keys.
- Pool settings (`pool_settings` and `async_pool_settings`) are validated: `min_size` cannot exceed `max_size` (raises `ValueError`).

### New Pool Configuration Options

Two new pool settings for both `pool_settings` and `async_pool_settings`:

| Parameter | Description | Default |
|-----------|-------------|---------|
| `timeout` | Seconds to wait for a connection from the pool before raising an error | `30` |
| `check_on_checkout` | Validate connections with `SELECT 1` before handing to caller | `false` |

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

149 unit tests (up from 132 in v2.1.0), all passing. New tests cover:

- Logging output (`caplog`) instead of `print()` (`capsys`)
- `NormalConnection.transaction()` commit/rollback without disconnect
- `check_on_checkout` pool configuration
- Config validation (unknown keys warning, pool range validation)
- `async_settings` passthrough to async pool connections
- Native psycopg code generation for all 4 connection types
- Backward compatibility (default library is pgmonkey)

## Files Changed

- `src/pgmonkey/connections/postgres/normal_connection.py` - Logging, transaction fix
- `src/pgmonkey/connections/postgres/async_connection.py` - Logging
- `src/pgmonkey/connections/postgres/pool_connection.py` - Logging, ExitStack test, check_on_checkout
- `src/pgmonkey/connections/postgres/async_pool_connection.py` - Logging, async_settings configure callback, check_on_checkout
- `src/pgmonkey/connections/postgres/postgres_connection_factory.py` - Config validation, async_settings passthrough
- `src/pgmonkey/managers/pgconnection_manager.py` - Logging, double-check locking
- `src/pgmonkey/common/templates/postgres.yaml` - timeout, check_on_checkout
- `src/pgmonkey/tools/connection_code_generator.py` - Native psycopg templates, library dispatch
- `src/pgmonkey/managers/pgcodegen_manager.py` - Library parameter
- `src/pgmonkey/cli/cli_pgconfig_subparser.py` - `--library` CLI argument
- `src/pgmonkey/tests/unit/` - Updated and new test files
- `PROJECTSCOPE.md` - New project scope document
- `README.md` - Documentation updates
- `docs/` - Website documentation updates

---

# pgmonkey v2.1.0 Release Notes

## Overview

pgmonkey v2.1.0 adds always-on connection caching to prevent pool storms, fixes a critical async pool lifecycle bug, and introduces best practice documentation with production-ready code recipes.

## What's New

### Always-On Connection Caching

Connections and pools are now automatically cached by config content. Repeated calls to `get_database_connection()` with the same configuration return the existing connection or pool instead of creating a new one.

This prevents "pool storms" - a common pitfall where each call inadvertently opens a brand-new connection pool, quickly exhausting database server connections.

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

Now, `async with` borrows a connection from the pool and returns it when the block exits - matching how the sync pool (`PGPoolConnection`) already works. The pool stays open for reuse across multiple `async with` blocks. Clean exits auto-commit; exceptions auto-rollback.

`cursor()` and `transaction()` are now dual-mode: inside an `async with` block they use the already-acquired connection; outside they acquire their own connection from the pool (standalone usage).

### Best Practice Documentation

New documentation covering production-ready usage patterns:

- **Best Practices page** (`docs/best_practices.html`) - Code recipes for all 4 connection types, Flask and FastAPI app-level design patterns, cache management API reference, and a quick reference table.
- **README section** - Best Practice Recipes with app-level patterns and cache management reference.
- Navigation updated across all doc pages.

## Compatibility

No breaking API changes. All existing code continues to work as before - caching is transparent and automatic. The `force_reload` parameter is the only new parameter on existing methods, and it defaults to `False`.

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

- `src/pgmonkey/managers/pgconnection_manager.py` - Connection caching, atexit cleanup, cache management API
- `src/pgmonkey/connections/postgres/async_pool_connection.py` - Async pool lifecycle fix
- `src/pgmonkey/tests/unit/test_connection_caching.py` - 19 new tests
- `docs/best_practices.html` - New documentation page
- `docs/index.html` - Navigation update
- `docs/reference.html` - Navigation update, test count update
- `README.md` - Best Practice Recipes section
- `ISSUES.md` - Internal issue tracker (not published)
- `pyproject.toml` - Version bump to 2.1.0
