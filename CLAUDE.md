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
- Config filter uses `is not None` (not truthiness) to preserve valid falsy values like empty passwords, keepalives=0
- SET statements for GUC settings use `psycopg.sql.SQL`/`sql.Identifier` for safe identifier quoting

## Test Commands
```bash
python -m pytest src/pgmonkey/tests/unit/ -v       # unit tests (188 tests)
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
**Files:** `connections/postgres/async_connection.py`, `connections/postgres/async_pool_connection.py`,
`tools/connection_code_generator.py`
**Problem:** GUC SET statements used `f"SET {setting} = %s"` — the setting name (an SQL identifier)
was interpolated via f-string. While the values come from the user's own config, this is bad
practice and the generated example code taught users unsafe patterns.
**Fix:** Changed to `sql.SQL("SET {} = %s").format(sql.Identifier(setting))` using psycopg's
safe SQL composition. Applied to both production code and generated code templates.

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
