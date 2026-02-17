# pgmonkey - Claude Code Memory

## Project Overview
PostgreSQL connection management library providing normal, pool, async, and async_pool
connection types. Includes CLI tools for config generation, server settings audit,
connection testing, and code generation.

## Architecture
- `connections/postgres/` - Connection implementations (normal, pool, async, async_pool)
- `managers/` - High-level managers (PGConnectionManager with caching, config, codegen, audit)
- `serversettings/` - Server audit: inspector queries pg_settings/pg_hba_file_rules, generator prints comparisons
- `tools/` - Code generator, CSV import/export, connection tester
- `cli/` - Argparse-based CLI subcommands
- `common/utils/envutils.py` - Env var interpolation engine (${VAR}, from_env, from_file)
- `common/utils/redaction.py` - Config redaction utility for safe logging

## Key Design Decisions
- Connections are cached by config content hash in PGConnectionManager with thread-safe locking
- Pool connections store `_pool_conn_ctx` to properly return connections to the pool on __exit__
- All connection __exit__ methods use try/finally to guarantee disconnect() even if commit/rollback fails
- Config filter uses `is not None` (not truthiness) to preserve valid falsy values like empty passwords, keepalives=0
- SET statements for GUC settings use `psycopg.sql.SQL`/`sql.Identifier` for safe identifier quoting
- Env interpolation is opt-in (`resolve_env=False` by default) - existing configs are not affected

## Config Format (v3.0.0+)
The YAML config no longer uses a top-level `postgresql:` wrapper key. Settings are at the
root level: `connection_type`, `connection_settings`, `pool_settings`, etc. Old-format configs
with the `postgresql:` key are auto-detected and unwrapped with a DeprecationWarning via
`common/utils/configutils.py:normalize_config()`.

## Style Guide
- Never use em dashes in documentation or code comments. Use a regular hyphen-minus (`-`) instead. This includes the literal Unicode character (`—`, U+2014) and HTML entity equivalents (`&mdash;`, `&#8212;`, `&#x2014;`).

## Test Commands
```bash
python -m pytest src/pgmonkey/tests/unit/ -v       # unit tests (327 tests)
python -m pytest src/pgmonkey/tests/unit/ -v -x     # stop on first failure
```

## Bug Fixes Applied (2026-02-15 review)

### Fix #1 & #4: Sync pool __exit__ double-commit + discarded context manager
**Files:** `connections/postgres/pool_connection.py`
**Problem:** `__enter__` did `self._conn = self.pool.connection().__enter__()` which discarded
the pool context manager. `__exit__` then called `self._conn.__exit__()` which invoked the raw
psycopg Connection's __exit__ - this double-committed transactions AND closed the underlying
connection instead of returning it to the pool.
**Fix:** Added `_pool_conn_ctx` field (mirroring async_pool_connection.py). `__enter__` stores
the pool CM, `__exit__` delegates to the pool CM for proper return-to-pool behavior.

### Fix #2: NULL crash in audit _evaluate_status
**File:** `serversettings/postgres_server_settings_inspector.py`
**Problem:** If pg_settings returned NULL for a setting value, `current.lower()` raised
`AttributeError`. The broad `except Exception` in pg_server_config_manager.py masked this as
"Falling back to recommendations only" with no indication of the real cause.
**Fix:** Added `if current is None: return 'UNKNOWN'` guard at the top of `_evaluate_status`.

### Fix #3: Empty password / falsy values silently dropped
**File:** `connections/postgres/postgres_connection_factory.py`
**Problem:** `_filter_config` used `if config[key]` which dropped empty strings (valid passwords),
integer 0 (valid for keepalives), and False values. An empty `password: ''` would silently vanish,
causing mysterious authentication failures.
**Fix:** Changed filter to `if config[key] is not None`. Only None values are now excluded.
psycopg/libpq treats empty strings as "use default" for most parameters.

### Fix #6: SQL setting name not parameterized (injection risk in identifier)
**Files:** `connections/postgres/normal_connection.py`, `connections/postgres/pool_connection.py`,
`connections/postgres/async_connection.py`, `connections/postgres/async_pool_connection.py`,
`tools/connection_code_generator.py`
**Problem:** GUC SET statements used `f"SET {setting} = %s"` - the setting name (an SQL identifier)
was interpolated via f-string. While the values come from the user's own config, this is bad
practice and the generated example code taught users unsafe patterns.
**Fix:** Changed to `sql.SQL("SET {} = %s").format(sql.Identifier(setting))` using psycopg's
safe SQL composition. Applied to all four connection types and generated code templates.

### Fix #7: Falsy config values filtered in generated code
**File:** `tools/connection_code_generator.py`
**Problem:** Generated psycopg code templates used `{k: v for k, v in conn_settings.items() if v}`
which would drop `port: 0`, `keepalives: 0`, `password: ''`, etc.
**Fix:** Changed to `if v is not None` in all four generated templates.

### Minor: redundant if-check in CLI handler
**File:** `cli/cli_pg_server_config_subparser.py`
**Problem:** `if args.filepath:` guard was redundant since `--filepath` is `required=True`.
**Fix:** Removed the unnecessary nesting.

### Non-issue: cache_info 'unknown' (false positive)
`postgres_connection_factory.py:66` already sets `connection.connection_type = self.connection_type`
on every connection, so `getattr(conn, 'connection_type', 'unknown')` in cache_info works correctly.

## Bug Fixes Applied (2026-02-15 second review)

### Fix: normal_connection + async_connection __exit__ connection leak
**Files:** `connections/postgres/normal_connection.py`, `connections/postgres/async_connection.py`
**Problem:** `__exit__`/`__aexit__` called commit/rollback then disconnect sequentially. If
commit() or rollback() raised (e.g. network error), disconnect() was never called - the connection
leaked. Pool connections already had try/finally from the first fix round; normal and async did not.
**Fix:** Wrapped commit/rollback in try/finally to guarantee disconnect() is always called.

### Fix: max_size string type crash in config generator
**File:** `serversettings/postgres_server_config_generator.py`
**Problem:** `max_size * 1.1` crashed with TypeError if max_size was a string (e.g. YAML
`max_size: "10"` with quotes). While unquoted YAML parses as int, quoted values are strings.
**Fix:** Added `int()` cast around `pool_settings.get('max_size', 0)` values.

### Fix: Unescaped config_file_path in generated code templates
**File:** `tools/connection_code_generator.py`
**Problem:** All 8 code templates used `config_file_path = '{config_file_path}'` which broke
if the path contained single quotes (e.g. `/home/o'brien/config.yaml`).
**Fix:** Changed to `{repr(config_file_path)}` which produces properly escaped Python string
literals regardless of quote characters in the path.

## Bug Fixes Applied (2026-02-15 third review)

### Fix: GUC SET f-string in sync connections (Fix #6 incomplete)
**Files:** `connections/postgres/normal_connection.py`, `connections/postgres/pool_connection.py`
**Problem:** Fix #6 was only applied to async_connection.py and async_pool_connection.py.
The sync counterparts (normal_connection.py and pool_connection.py) still used
`f"SET {setting} = %s"` for GUC settings - the same unsafe f-string interpolation pattern.
**Fix:** Added `sql` import from psycopg and changed to
`sql.SQL("SET {} = %s").format(sql.Identifier(setting))` in both files, matching the async
implementations. Updated corresponding test assertions.

### Fix: BOM detection order in CSV importer
**File:** `tools/csv_data_importer.py`
**Problem:** `_detect_bom()` checked UTF-16-LE BOM (`\xff\xfe`) before UTF-32-LE BOM
(`\xff\xfe\x00\x00`). Since the UTF-32-LE BOM starts with the same two bytes as UTF-16-LE,
any UTF-32-LE encoded file would be misdetected as UTF-16-LE.
**Fix:** Reordered BOM checks: UTF-32 BOMs (4 bytes) are now checked before UTF-16 BOMs
(2 bytes), ensuring longer matches take priority.

### Fix: CSV exporter progress bar counting chunks instead of rows
**File:** `tools/csv_data_exporter.py`
**Problem:** `_sync_export()` iterated over COPY TO chunks (byte buffers) and called
`progress.update(1)` per chunk, but the progress bar total was set to the actual row count.
Since chunks can contain multiple rows, the bar severely underreported progress.
**Fix:** Changed to `progress.update(bytes(data).count(b'\n'))` to count newline-terminated
rows within each chunk for accurate progress tracking.

## Bug Fixes Applied (2026-02-15 fourth review)

### Fix: _pool_conn_ctx not thread-safe in pool_connection
**File:** `connections/postgres/pool_connection.py`
**Problem:** `_pool_conn_ctx` was stored as a regular instance attribute, but pool connections
are designed for multi-threaded use (the borrowed connection was already in `threading.local`).
When two threads called `__enter__`/`__exit__` concurrently on the same PGPoolConnection, they
overwrote each other's pool context manager - one thread would exit another thread's CM,
causing connection leaks and double-exits.
**Fix:** Moved `_pool_conn_ctx` into `self._local` (the existing `threading.local` instance),
making it per-thread just like the borrowed connection. Added a thread-safety test.

### Fix: Cache key missing connection_type
**File:** `managers/pgconnection_manager.py`
**Problem:** `_config_hash()` only hashed the config dictionary. The resolved `connection_type`
was not included in the cache key. Calling `get_database_connection` with the same config but
different `connection_type` overrides (e.g. `'normal'` vs `'pool'`) returned the wrong cached
connection - whichever type was created first would be returned for all subsequent calls.
**Fix:** Appended `':' + resolved_type` to the cache key so each connection type gets its own
cache entry.

### Fix: Module-level ContextVars shared across all async pool instances
**File:** `connections/postgres/async_pool_connection.py`
**Problem:** `_async_pool_conn` and `_async_pool_conn_ctx` were module-level `ContextVar`s,
shared across ALL `PGAsyncPoolConnection` instances. Nested `async with` on two different
pool instances in the same async task would clobber each other's connection references,
causing incorrect commit/rollback and potential connection leaks.
**Fix:** Replaced with per-instance ContextVars (`self._pool_conn`, `self._pool_conn_ctx`)
created in `__init__` with unique names using `id(self)`. Each instance now has isolated
async-task-local state. Added a test verifying nested instances don't interfere.

### Fix: pg_hba recommendation generated `host ... reject` for SSL modes
**File:** `serversettings/postgres_server_config_generator.py`
**Problem:** For non-verify SSL modes (prefer/require/allow), `generate_pg_hba_entry()` produced
`host all all {address} reject` - a `host` rule with `reject` method blocks ALL connections
(both SSL and non-SSL) from the subnet, which would prevent the very connection the user is
trying to make.
**Fix:** Changed to `hostssl all all {address} md5` which correctly recommends allowing
SSL-only connections with password authentication. The `hostssl` type ensures only encrypted
connections are permitted, matching the intent of using a non-disable SSL mode.

## Bug Fixes Applied (2026-02-16 v3.1.0 review)

### Fix: normal_connection.cursor() crashes with AttributeError when no connection
**File:** `connections/postgres/normal_connection.py`
**Problem:** `cursor()` called `self.connection.cursor()` without checking if `self.connection`
is None. If called before `connect()` or after `disconnect()`, this raised an unhelpful
`AttributeError: 'NoneType' object has no attribute 'cursor'`. The other three connection
types (pool, async, async_pool) all had proper None guards with clear error messages.
**Fix:** Added `if self.connection:` guard matching the pattern used by pool_connection and
async_connection. Raises `Exception("No active connection available to create a cursor")`
when connection is None.

### Fix: pg_hba recommendations use deprecated md5 authentication
**File:** `serversettings/postgres_server_config_generator.py`
**Problem:** `generate_pg_hba_entry()` hardcoded `md5` as the authentication method in all
generated pg_hba.conf entries. MD5 authentication is deprecated in PostgreSQL 14+ and the
default has been `scram-sha-256` since PostgreSQL 10. Recommending `md5` could lead users
to configure weaker authentication or fail on newer PostgreSQL versions.
**Fix:** Changed all `md5` references to `scram-sha-256` in generated pg_hba.conf entries,
including both the verify-ca/verify-full entries (with clientcert) and the non-verify SSL
mode entries (hostssl without clientcert).

### Fix: sys.exit(0) in CSV importer/exporter library code
**Files:** `tools/csv_data_importer.py`, `tools/csv_data_exporter.py`,
`cli/cli_import_subparser.py`, `cli/cli_export_subparser.py`
**Problem:** Both `_prepopulate_import_config()` and `_prepopulate_export_config()` called
`sys.exit(0)` after auto-generating config files. This terminated the entire Python process,
which is hostile to anyone using pgmonkey as a library. It also bypassed context manager
cleanup (the exporter opens a database connection before hitting `sys.exit`, leaking it).
**Fix:** Created `ConfigFileCreatedError` exception in `common/exceptions.py`. The CSV tools
now raise this exception instead of calling `sys.exit()`. The CLI handlers catch it and
print the message cleanly. Library users can catch `ConfigFileCreatedError` to handle
config-file creation gracefully in their own code.

### Fix: table_name.split('.') crashes on multi-dot names
**Files:** `tools/csv_data_importer.py`, `tools/csv_data_exporter.py`
**Problem:** Both CSV tools used `table_name.split('.')` to separate schema from table name.
If a table name contained more than one dot (e.g. `catalog.schema.table`), this raised
`ValueError: too many values to unpack`.
**Fix:** Changed to `table_name.split('.', 1)` to only split on the first dot. The schema
portion gets the part before the first dot; the table portion gets everything after.

### Fix: Shadowed imports in csv_data_importer._sync_ingest
**File:** `tools/csv_data_importer.py`
**Problem:** `_sync_ingest()` contained `import csv` and `import sys` at lines 232-233 that
shadowed the module-level imports of the same modules. While functionally harmless, this
was confusing and unnecessary.
**Fix:** Removed the redundant local imports.

### Fix: Stale version in PROJECTSCOPE.md
**File:** `PROJECTSCOPE.md`
**Problem:** The Version & Compatibility section still listed `Current version: 2.2.0`,
which was two major versions behind.
**Fix:** Updated to `3.1.0`.

## Bug Fixes Applied (2026-02-16 review feedback)

### Fix: StopIteration crash on small CSV files
**File:** `tools/csv_data_importer.py`
**Problem:** Phase 1 sampling in `_sync_ingest()` used
`[next(file).strip() for _ in range(5)]` which raises `StopIteration` if the CSV has
fewer than 5 lines. Any small CSV (e.g. header-only, or 2-3 rows) would crash the import.
**Fix:** Replaced with `for _, line in zip(range(5), file)` which safely stops at EOF.

### Fix: auto_create_table config setting ignored
**File:** `tools/csv_data_importer.py`
**Problem:** `auto_create_table` was loaded from import config into `self.auto_create_table`
but never checked. The code unconditionally created the table when it didn't exist, making
the config option a no-op.
**Fix:** Added a guard that raises `ValueError` when the table doesn't exist and
`auto_create_table` is `False`, before calling `_create_table_sync`.

### Fix: Unnecessary asyncio.run() wrapping purely sync code
**Files:** `tools/csv_data_importer.py`, `tools/csv_data_exporter.py`,
`managers/pgimport_manager.py`, `managers/pgexport_manager.py`
**Problem:** `CSVDataImporter.run()` and `CSVDataExporter.run()` were `async def` methods
containing zero `await` calls - they only performed sync operations. The managers then
called them via `asyncio.run()`, adding pointless overhead and crashing when called from
within an existing event loop (e.g. Jupyter notebooks, async frameworks).
**Fix:** Changed `run()` to regular `def` methods. Removed `asyncio` import from both
managers and changed `asyncio.run(importer.run())` to `importer.run()`.

## Feature: Environment Variable Interpolation (v3.4.0)

### Overview
Opt-in `${VAR}` / `${VAR:-default}` substitution and structured `from_env` / `from_file`
secret references for YAML configs. Disabled by default (`resolve_env=False`).

### New Files
- `common/utils/envutils.py` - Core interpolation engine: `resolve_env_vars()`,
  `EnvInterpolationError`, `SENSITIVE_KEYS`, `_is_sensitive_key()`
- `common/utils/redaction.py` - `redact_config()` masks sensitive values for logging

### Modified Files
- `__init__.py` - Exports `load_config` and `EnvInterpolationError`
- `common/utils/configutils.py` - New `load_config()` function
- `managers/pgconnection_manager.py` - `resolve_env` parameter on both `get_database_connection()`
  and `get_database_connection_from_dict()`
- `managers/pgconfig_manager.py` - `resolve_env` threaded through `test_connection()`
- `managers/pgcodegen_manager.py` - `resolve_env` accepted for CLI consistency
- `tools/database_connection_tester.py` - `resolve_env` threaded through all test methods
- `cli/cli_pgconfig_subparser.py` - `--resolve-env` flag on `test` and `generate-code`
- `common/templates/postgres.yaml` - Interpolation docs at end of template (advanced section)

### Design Decisions
- Interpolation runs AFTER `normalize_config()` (old-format unwrapping), BEFORE connection creation
- Sensitive keys (`password`, `sslkey`, `sslcert`, `sslrootcert`, plus token/secret/credential
  substrings) disallow `${VAR:-default}` by default to prevent accidental fallback passwords
- `from_file` trims trailing newline (Kubernetes Secret convention)
- `resolve_env_vars()` returns a new dict (never mutates input)
- Error messages name the missing variable/file and config key path, never the resolved value
- 63 unit tests in `tests/unit/test_env_interpolation.py`

## Env Interpolation API Cleanup (v3.5.0)

### allow_sensitive_defaults exposed end-to-end
**Files:** `managers/pgconnection_manager.py`, `managers/pgconfig_manager.py`,
`tools/database_connection_tester.py`, `cli/cli_pgconfig_subparser.py`
**Problem:** `load_config()` accepted `allow_sensitive_defaults` but
`PGConnectionManager.get_database_connection()` did not - it always hardcoded `False`.
Users going through the manager (the primary API) could not use `${PGPASSWORD:-devpass}`
for local dev convenience.
**Fix:** Added `allow_sensitive_defaults=False` parameter to both `get_database_connection()`
and `get_database_connection_from_dict()`, threaded through the connection tester, config
manager, and CLI (`--allow-sensitive-defaults` flag on `pgconfig test`).

### Removed no-op strict parameter
**Files:** `common/utils/envutils.py`, `common/utils/configutils.py`
**Problem:** `resolve_env_vars()` and `load_config()` accepted a `strict` parameter
documented as "reserved for future use" but it was a complete no-op - accepted, propagated
recursively, but never checked. This confused users who set `strict=True` expecting validation.
**Fix:** Removed the `strict` parameter from both functions.

### Re-exported redact_config from top-level package
**File:** `__init__.py`
**Problem:** `redact_config` was only importable from `pgmonkey.common.utils.redaction`,
which felt like reaching into internals.
**Fix:** Added `from .common.utils.redaction import redact_config` to `__init__.py`.
Users can now `from pgmonkey import redact_config`.

### Docs: cache behavior note with resolve_env
**File:** `docs/best_practices.html`
**Note:** Added a paragraph in the Cache Management section explaining that when
`resolve_env=True`, the cache key is computed from resolved config values. Changed env
vars produce new cache keys (new connections). Old connections stay cached until
`clear_cache()` or process exit.

## Bug Fixes Applied (2026-02-17 review)

### Fix: AsyncConnectionPool deprecation warning (auto-open in constructor)
**Files:** `connections/postgres/async_pool_connection.py`, `tools/connection_code_generator.py`
**Problem:** `AsyncConnectionPool(conninfo=conninfo, **kwargs)` auto-opened the pool in the
constructor (deprecated in psycopg_pool, will be removed in a future release). The previous
workaround suppressed the RuntimeWarning with `warnings.catch_warnings()` rather than fixing
the root cause. The pool was effectively opened twice - once in the constructor, once by the
explicit `await self.pool.open()`.
**Fix:** Added `open=False` to the constructor call so the pool is created without auto-opening.
The existing `await self.pool.open()` then does the only open. Removed the warning suppression
hack and the unused `import warnings`. Also updated the generated psycopg code template to
include `open=False` so users learn the correct pattern.
