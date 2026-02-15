# pgmonkey - Claude Code Memory

## Project Overview
PostgreSQL connection management library providing normal, pool, async, and async_pool
connection types. Includes CLI tools for config generation, server settings audit,
connection testing, and code generation.

## Architecture
- `connections/postgres/` — Connection implementations (normal, pool, async, async_pool)
- `managers/` — High-level managers (PGConnectionManager with caching, config, codegen, audit)
- `serversettings/` — Server audit: inspector queries pg_settings/pg_hba_file_rules, generator prints comparisons
- `tools/` — Code generator, CSV import/export, connection tester
- `cli/` — Argparse-based CLI subcommands

## Key Design Decisions
- Connections are cached by config content hash in PGConnectionManager with thread-safe locking
- Pool connections store `_pool_conn_ctx` to properly return connections to the pool on __exit__
- All connection __exit__ methods use try/finally to guarantee disconnect() even if commit/rollback fails
- Config filter uses `is not None` (not truthiness) to preserve valid falsy values like empty passwords, keepalives=0
- SET statements for GUC settings use `psycopg.sql.SQL`/`sql.Identifier` for safe identifier quoting

## Test Commands
```bash
python -m pytest src/pgmonkey/tests/unit/ -v       # unit tests (192 tests)
python -m pytest src/pgmonkey/tests/unit/ -v -x     # stop on first failure
```

## Bug Fixes Applied (2026-02-15 review)

### Fix #1 & #4: Sync pool __exit__ double-commit + discarded context manager
**Files:** `connections/postgres/pool_connection.py`
**Problem:** `__enter__` did `self._conn = self.pool.connection().__enter__()` which discarded
the pool context manager. `__exit__` then called `self._conn.__exit__()` which invoked the raw
psycopg Connection's __exit__ — this double-committed transactions AND closed the underlying
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
**Problem:** GUC SET statements used `f"SET {setting} = %s"` — the setting name (an SQL identifier)
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
commit() or rollback() raised (e.g. network error), disconnect() was never called — the connection
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
`f"SET {setting} = %s"` for GUC settings — the same unsafe f-string interpolation pattern.
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
overwrote each other's pool context manager — one thread would exit another thread's CM,
causing connection leaks and double-exits.
**Fix:** Moved `_pool_conn_ctx` into `self._local` (the existing `threading.local` instance),
making it per-thread just like the borrowed connection. Added a thread-safety test.

### Fix: Cache key missing connection_type
**File:** `managers/pgconnection_manager.py`
**Problem:** `_config_hash()` only hashed the config dictionary. The resolved `connection_type`
was not included in the cache key. Calling `get_database_connection` with the same config but
different `connection_type` overrides (e.g. `'normal'` vs `'pool'`) returned the wrong cached
connection — whichever type was created first would be returned for all subsequent calls.
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
`host all all {address} reject` — a `host` rule with `reject` method blocks ALL connections
(both SSL and non-SSL) from the subnet, which would prevent the very connection the user is
trying to make.
**Fix:** Changed to `hostssl all all {address} md5` which correctly recommends allowing
SSL-only connections with password authentication. The `hostssl` type ensures only encrypted
connections are permitted, matching the intent of using a non-disable SSL mode.
