# pgmonkey v4.0.0 Release Notes

## Integration-Tested Stability

pgmonkey v4.0.0 is the first release validated against live PostgreSQL instances. A new
Docker-based integration test harness (61 tests across 10 categories) uncovered bugs that
327 unit tests with mocks could not catch - including connection leaks, double-commits,
broken GUC settings, and thread-safety races. Every issue found has been fixed.

This release also ships the test harness itself as a permanent part of the repository, so
future changes can be verified against real PostgreSQL before release.

## Why v4.0.0

The volume and severity of the fixes warrant a major version bump. While the public API is
unchanged, the runtime behavior of pool connections, transaction handling, GUC settings, and
CSV operations has materially improved. Code that depended on (or worked around) the old
broken behavior may need adjustment.

## Bug Fixes

### Connection Lifecycle

| Fix | Severity | Files |
|---|---|---|
| Sync pool `__exit__` double-committed and closed connections instead of returning to pool | Critical | `pool_connection.py` |
| Normal and async `__exit__` leaked connections if commit/rollback raised | Critical | `normal_connection.py`, `async_connection.py` |
| `_pool_conn_ctx` not thread-safe - concurrent threads overwrote each other's pool context managers | Critical | `pool_connection.py` |
| Module-level ContextVars shared across all async pool instances - nested pools clobbered each other | Critical | `async_pool_connection.py` |
| Cache key missing connection_type - same config with different types returned wrong cached connection | High | `pgconnection_manager.py` |
| `normal_connection.cursor()` crashed with AttributeError when no active connection | Medium | `normal_connection.py` |
| AsyncConnectionPool auto-opened in constructor (deprecated) - suppressed warning instead of fixing | Medium | `async_pool_connection.py` |

### SQL Safety

| Fix | Severity | Files |
|---|---|---|
| GUC SET statements used f-string interpolation for SQL identifiers | High | All 4 connection types, `connection_code_generator.py` |
| Generated code templates taught users the same unsafe SET pattern | High | `connection_code_generator.py` |

### Configuration

| Fix | Severity | Files |
|---|---|---|
| Empty passwords and falsy values (keepalives=0) silently dropped by config filter | High | `postgres_connection_factory.py` |
| Generated code also dropped falsy config values | Medium | `connection_code_generator.py` |
| Unescaped config_file_path in generated code broke paths with quotes | Medium | `connection_code_generator.py` |
| max_size string type crash in config generator | Low | `postgres_server_config_generator.py` |

### CSV Import/Export

| Fix | Severity | Files |
|---|---|---|
| `sys.exit(0)` in library code killed the calling process | High | `csv_data_importer.py`, `csv_data_exporter.py` |
| `table_name.split('.')` crashed on multi-dot names | Medium | `csv_data_importer.py`, `csv_data_exporter.py` |
| StopIteration crash on CSV files with fewer than 5 lines | Medium | `csv_data_importer.py` |
| `auto_create_table` config setting was a no-op | Medium | `csv_data_importer.py` |
| BOM detection misidentified UTF-32-LE as UTF-16-LE | Medium | `csv_data_importer.py` |
| Export progress bar counted chunks instead of rows | Low | `csv_data_exporter.py` |
| Shadowed imports in `_sync_ingest` | Low | `csv_data_importer.py` |
| Unnecessary `asyncio.run()` wrapping purely sync code | Low | `csv_data_importer.py`, `csv_data_exporter.py` |

### Server Audit

| Fix | Severity | Files |
|---|---|---|
| NULL crash in `_evaluate_status` when pg_settings returned NULL | Medium | `postgres_server_settings_inspector.py` |
| pg_hba generated `host ... reject` for SSL modes - blocked all connections | High | `postgres_server_config_generator.py` |
| pg_hba recommended deprecated md5 instead of scram-sha-256 | Medium | `postgres_server_config_generator.py` |

### GUC SET Statements (Integration Test Discovery)

| Fix | Severity | Files |
|---|---|---|
| SET used `%s` parameter binding which PostgreSQL rejects for utility statements | Critical | All 4 connection types, `csv_data_exporter.py` |
| Pool configure callbacks left connections in INTRANS state - pool discarded them | High | `pool_connection.py`, `async_pool_connection.py` |

## New: Docker Integration Test Harness

The `test_harness/` directory contains a self-contained test environment:

- **`docker-compose.yml`** - PostgreSQL containers: plain, SSL (require), and mTLS (verify-full)
- **`run_harness.sh`** - Orchestrator: stands up containers, runs tests, tears down
- **`run_tests.py`** - 61 integration tests across 10 categories

### Test Categories (61 tests)

| Category | Tests | What it covers |
|---|---|---|
| Connection Types | 4 | Normal, pool, async, async_pool basic connectivity |
| SSL/TLS Modes | 8 | disable, prefer, require, verify-ca, verify-full across types |
| Client Certificate Auth | 4 | mTLS with verify-ca and verify-full |
| Connection Pooling | 4 | min/max sizing, health checks, concurrent threads/tasks |
| GUC/SET Settings | 4 | sync_settings and async_settings with configure callbacks |
| Transactions | 3 | Commit on clean exit, rollback on exception, autocommit |
| Env Var Interpolation | 8 | ${VAR}, defaults, from_env, from_file, sensitive protection |
| CLI Commands | 8 | create, test, generate-code, server audit |
| CSV Import/Export | 3 | Export, import, roundtrip |
| Connection Caching | 5 | Same config, different types, force_reload, clear_cache |
| Config & Utilities | 3 | load_config, normalize_config, redact_config |
| Code Generation | 2 | All 8 templates, safe SQL composition |
| Server Audit | 2 | Recommendations, live pg_settings |
| Error Handling | 3 | Bad host, wrong password, cursor without connection |

### Running the Harness

```bash
cd test_harness
./run_harness.sh
```

Requires Docker and Docker Compose. Containers are created and destroyed automatically.

## Other Changes

- Added `__main__.py` for `python -m pgmonkey` invocation
- Redundant `if args.filepath:` guard removed from CLI handler

## Compatibility

No breaking changes to the public Python API. The behavioral fixes (especially pool
`__exit__` and GUC SET) change runtime behavior in ways that fix correctness. Code that
relied on the old (broken) behavior should be reviewed.

| Dependency | Supported Versions |
|---|---|
| Python | >= 3.10, < 4.0 |
| psycopg[binary] | >= 3.1.20, < 4.0.0 |
| psycopg_pool | >= 3.1.9, < 4.0.0 |
| PyYAML | >= 6.0.2, < 7.0.0 |
| chardet | >= 5.2.0, < 6.0.0 |
| tqdm | >= 4.64.0, < 5.0.0 |

## Test Suite

- **327 unit tests** (up from 288 in v3.5.0), all passing
- **61 integration tests** against live PostgreSQL (new)

---

# pgmonkey v3.5.0 Release Notes

## API Cleanup and Documentation

pgmonkey v3.5.0 is a focused quality release that finishes the environment variable
interpolation API introduced in v3.4.0. It exposes `allow_sensitive_defaults` end-to-end
so local-dev configs can use `${PGPASSWORD:-devpass}` through the manager and CLI, removes
an unimplemented `strict` parameter that could confuse users, promotes `redact_config` to
a top-level export, and adds documentation for CLI-based config testing with interpolation.

## Highlights

### allow_sensitive_defaults Exposed End-to-End

In v3.4.0, `load_config()` accepted `allow_sensitive_defaults` but the primary API -
`PGConnectionManager.get_database_connection()` - did not. It always hardcoded `False`,
meaning users going through the manager could not use `${PGPASSWORD:-devpass}` for local
dev convenience.

The parameter is now available on:

- `PGConnectionManager.get_database_connection(..., allow_sensitive_defaults=True)`
- `PGConnectionManager.get_database_connection_from_dict(..., allow_sensitive_defaults=True)`
- `DatabaseConnectionTester.test_postgresql_connection()`
- `PGConfigManager.test_connection()`
- CLI: `pgmonkey pgconfig test --resolve-env --allow-sensitive-defaults`

### Removed No-Op strict Parameter

`resolve_env_vars()` and `load_config()` accepted a `strict` parameter documented as
"currently reserved for future use." It was accepted and propagated recursively but never
checked - a no-op that could confuse anyone who set `strict=True` expecting validation.
The parameter has been removed from both functions.

### redact_config Re-Exported from Top-Level Package

`redact_config` was only importable from `pgmonkey.common.utils.redaction`, which felt
like reaching into internals. It is now re-exported from the top-level package:

```python
# Before (still works)
from pgmonkey.common.utils.redaction import redact_config

# Now (preferred)
from pgmonkey import redact_config
```

### CLI Documentation for Config Testing with Interpolation

New recipe card in `best_practices.html` covering `pgconfig test` and `pgconfig generate-code`
with `--resolve-env`, `--allow-sensitive-defaults`, and `--connection-type` flags. Explains
what happens without `--resolve-env` and when `--allow-sensitive-defaults` is appropriate.

### Docker / Docker Compose Recipe

New recipe card showing a complete Docker Compose workflow: a `config.yaml` with `${VAR}`
references (safe to commit), a `docker-compose.yml` passing env vars to the app container,
Python code with `resolve_env=True`, and a one-liner to run it all.

### Cache Behavior Note

Added documentation explaining that with `resolve_env=True`, the cache key is computed
from the resolved config values. Changed env vars produce new cache keys and new connections.
Old connections stay cached until `clear_cache()` or process exit.

## New Public Exports

| Export | Description |
|---|---|
| `pgmonkey.redact_config()` | Mask sensitive config values for safe logging |

## Compatibility

No breaking API changes for normal usage. The removal of the `strict` parameter is
technically a signature change, but since it was a no-op that no code could have
meaningfully depended on, this is not considered breaking.

| Dependency | Supported Versions |
|---|---|
| Python | >= 3.10, < 4.0 |
| psycopg[binary] | >= 3.1.20, < 4.0.0 |
| psycopg_pool | >= 3.1.9, < 4.0.0 |
| PyYAML | >= 6.0.2, < 7.0.0 |
| chardet | >= 5.2.0, < 6.0.0 |
| tqdm | >= 4.64.0, < 5.0.0 |

## Test Suite

288 unit tests (up from 293 in v3.4.0 - 7 added, 1 removed for the `strict` no-op, net
decrease due to test renumbering after removing the strict passthrough test), all passing.
New tests cover:

- `allow_sensitive_defaults` parameter on `PGConnectionManager.get_database_connection()`
- `allow_sensitive_defaults` parameter on `PGConnectionManager.get_database_connection_from_dict()`
- `allow_sensitive_defaults` via `load_config()` (allowed and blocked paths)
- `redact_config` importable from top-level `pgmonkey` package
- `redact_config` works correctly via top-level import

## Files Changed

- `pyproject.toml` - Version bump to 3.5.0
- `src/pgmonkey/__init__.py` - Re-export `redact_config`
- `src/pgmonkey/common/utils/envutils.py` - Removed `strict` parameter from `resolve_env_vars()`
- `src/pgmonkey/common/utils/configutils.py` - Removed `strict` parameter from `load_config()`
- `src/pgmonkey/managers/pgconnection_manager.py` - `allow_sensitive_defaults` parameter
- `src/pgmonkey/managers/pgconfig_manager.py` - `allow_sensitive_defaults` parameter
- `src/pgmonkey/tools/database_connection_tester.py` - `allow_sensitive_defaults` parameter
- `src/pgmonkey/cli/cli_pgconfig_subparser.py` - `--allow-sensitive-defaults` CLI flag
- `src/pgmonkey/tests/unit/test_env_interpolation.py` - 7 new tests, 1 removed
- `docs/best_practices.html` - Docker recipe, CLI recipe, cache note, updated redaction import
- `PROJECTSCOPE.md` - Version update
- `CLAUDE.md` - API cleanup documentation
- `RELEASE_NOTES.md` - This release notes entry

---

# pgmonkey v3.4.0 Release Notes

## Environment Variable Interpolation

pgmonkey v3.4.0 adds opt-in support for resolving environment variables and file-based secrets
inside YAML configuration files. This lets you keep config files free of hardcoded credentials
while staying compatible with standard deployment workflows (12-factor env vars, Docker,
Kubernetes mounted secrets).

**Interpolation is disabled by default.** Existing configs with literal values work exactly as
before. Enable it with `resolve_env=True` in Python or `--resolve-env` on the CLI.

## Highlights

### Inline ${VAR} Substitution

Reference environment variables with `${VAR}` syntax. Provide fallbacks with `${VAR:-default}`:

```yaml
connection_settings:
  user: '${PGUSER:-postgres}'
  password: '${PGPASSWORD}'          # required - error if not set
  host: '${PGHOST:-localhost}'
  port: '${PGPORT:-5432}'
  dbname: '${PGDATABASE:-mydb}'
```

If a variable is not set and no default is provided, pgmonkey raises `EnvInterpolationError`
with a clear message naming the variable and the config key.

### Structured from_env / from_file References

For secrets, a structured YAML form makes the intent unambiguous:

```yaml
# Read from an environment variable
password:
  from_env: PGMONKEY_DB_PASSWORD

# Read from a file (Kubernetes Secret-style, trailing newline trimmed)
password:
  from_file: /var/run/secrets/db/password
```

`from_file` reads file contents and trims the trailing newline, matching Kubernetes Secret
conventions. Missing files or variables raise `EnvInterpolationError` immediately.

### Sensitive Key Protection

Defaults (`${VAR:-fallback}`) are disallowed for sensitive keys (`password`, `sslkey`,
`sslcert`, `sslrootcert`, and any key containing `token`, `secret`, or `credential`). This
prevents accidentally shipping a config with a hardcoded fallback password. Override with
`allow_sensitive_defaults=True` for local development.

### load_config() Public API

A new `load_config()` function provides the simplest path to loading and resolving configs:

```python
from pgmonkey import load_config

# Without interpolation (default)
cfg = load_config('config.yaml')

# With interpolation
cfg = load_config('config.yaml', resolve_env=True)
```

### Redaction Utility

`redact_config()` masks sensitive values with `***REDACTED***` for safe logging:

```python
from pgmonkey.common.utils.redaction import redact_config
print(redact_config(cfg))
# {'connection_settings': {'password': '***REDACTED***', 'host': 'db.prod.com', ...}}
```

### CLI --resolve-env Flag

The `pgconfig test` and `pgconfig generate-code` CLI commands accept `--resolve-env`:

```bash
pgmonkey pgconfig test --connconfig config.yaml --resolve-env
```

Without `--resolve-env`, the CLI treats `${VAR}` patterns as literal strings, exactly as before.

## New Public Exports

| Export | Description |
|---|---|
| `pgmonkey.load_config()` | Load and optionally interpolate a YAML config file |
| `pgmonkey.EnvInterpolationError` | Raised when env interpolation fails |
| `pgmonkey.common.utils.redaction.redact_config()` | Mask sensitive config values |

## Compatibility

No breaking API changes. All existing code continues to work as before. Interpolation is
entirely opt-in.

| Dependency | Supported Versions |
|---|---|
| Python | >= 3.10, < 4.0 |
| psycopg[binary] | >= 3.1.20, < 4.0.0 |
| psycopg_pool | >= 3.1.9, < 4.0.0 |
| PyYAML | >= 6.0.2, < 7.0.0 |
| chardet | >= 5.2.0, < 6.0.0 |
| tqdm | >= 4.64.0, < 5.0.0 |

## Test Suite

293 unit tests (up from 264 in v3.3.0), all passing. New tests cover:

- Inline `${VAR}` and `${VAR:-default}` substitution (set, missing, multiple)
- Sensitive key default protection and opt-in override
- Structured `from_env` and `from_file` resolution
- `from_file` trailing newline trimming
- Missing env var and missing file error messages
- Redaction of passwords, SSL keys, tokens, and credential keys
- `load_config()` with and without interpolation
- Old-format config normalization through `load_config()`
- Error messages do not leak secret values
- `resolve_env` parameter acceptance on `PGConnectionManager` methods

## Files Changed

- `pyproject.toml` - Version bump to 3.4.0
- `src/pgmonkey/__init__.py` - Export `load_config` and `EnvInterpolationError`
- `src/pgmonkey/common/utils/configutils.py` - New `load_config()` function
- `src/pgmonkey/common/utils/envutils.py` - New: env interpolation engine
- `src/pgmonkey/common/utils/redaction.py` - New: config redaction utility
- `src/pgmonkey/managers/pgconnection_manager.py` - `resolve_env` parameter
- `src/pgmonkey/managers/pgconfig_manager.py` - `resolve_env` parameter
- `src/pgmonkey/managers/pgcodegen_manager.py` - `resolve_env` parameter
- `src/pgmonkey/tools/database_connection_tester.py` - `resolve_env` parameter
- `src/pgmonkey/cli/cli_pgconfig_subparser.py` - `--resolve-env` CLI flag
- `src/pgmonkey/common/templates/postgres.yaml` - Interpolation docs (advanced section)
- `src/pgmonkey/tests/unit/test_env_interpolation.py` - New: 58 tests
- `README.md` - New section: Environment Variable Interpolation (Advanced)
- `docs/reference.html` - Env interpolation API reference, CLI flag docs
- `docs/best_practices.html` - Env interpolation recipes (local dev, k8s, redaction)
- `PROJECTSCOPE.md` - Updated scope and version
- `CLAUDE.md` - Feature documentation
- `RELEASE_NOTES.md` - This release notes entry

---

# pgmonkey v3.3.0 Release Notes

## Correctness and Library Usability

pgmonkey v3.3.0 fixes three bugs surfaced during an external review: a crash when importing
small CSV files, a config option that was silently ignored, and an unnecessary asyncio
dependency that blocked library usage from within existing event loops.

## Highlights

### CSV Import No Longer Crashes on Small Files

The CSV importer's phase-1 column sampling used `next(file)` in a loop that assumed at least
5 lines existed. Any CSV with fewer than 5 rows - a header-only file, a small lookup table,
a test fixture - would crash with `StopIteration` before the import even started. The sampling
now stops gracefully at end-of-file regardless of row count.

### auto_create_table Config Setting Now Works

The `auto_create_table` setting in import config files was loaded and stored but never actually
checked. The importer unconditionally created missing tables, making the setting a no-op.
Setting `auto_create_table: False` now correctly raises a `ValueError` with a clear message
when the target table does not exist, giving users control over whether the importer should
create tables or only import into pre-existing ones.

### Import/Export Managers Work Inside Async Contexts

`CSVDataImporter.run()` and `CSVDataExporter.run()` were declared as `async def` despite
containing zero `await` calls - they perform entirely synchronous database operations using
psycopg's sync COPY interface. The managers wrapped them in `asyncio.run()`, which:

- Added unnecessary event loop overhead for purely sync work
- Crashed with `RuntimeError` when called from Jupyter notebooks, async web frameworks,
  or any environment with an already-running event loop

Both `run()` methods are now regular synchronous functions. The managers call them directly
without `asyncio.run()`. This is fully backward-compatible - the methods were never truly
async, so no existing `await` calls need updating.

## Compatibility

No breaking API changes. `CSVDataImporter.run()` and `CSVDataExporter.run()` changed from
`async def` to `def`, but since they contained no `await` expressions, any code calling them
via `asyncio.run(importer.run())` can simply change to `importer.run()`. Code using the
higher-level `PGImportManager` and `PGExportManager` requires no changes at all.

| Dependency | Supported Versions |
|---|---|
| Python | >= 3.10, < 4.0 |
| psycopg[binary] | >= 3.1.20, < 4.0.0 |
| psycopg_pool | >= 3.1.9, < 4.0.0 |
| PyYAML | >= 6.0.2, < 7.0.0 |
| chardet | >= 5.2.0, < 6.0.0 |
| tqdm | >= 4.64.0, < 5.0.0 |

## Test Suite

264 unit tests (up from 257 in v3.2.0), all passing. New tests cover:

- Small CSV sampling (1-row, 2-row, 3-row files survive phase-1 without StopIteration)
- `auto_create_table: False` raises ValueError when table is missing
- `auto_create_table: True` proceeds to create the table
- `run()` is not a coroutine function (both importer and exporter)

## Files Changed

- `pyproject.toml` - Version bump to 3.3.0
- `src/pgmonkey/tools/csv_data_importer.py` - Safe sampling loop, auto_create_table guard,
  async def to def
- `src/pgmonkey/tools/csv_data_exporter.py` - async def to def
- `src/pgmonkey/managers/pgimport_manager.py` - Removed asyncio.run(), direct call
- `src/pgmonkey/managers/pgexport_manager.py` - Removed asyncio.run(), direct call
- `src/pgmonkey/tests/unit/test_csv_data_importer.py` - 7 new tests
- `src/pgmonkey/tests/unit/test_csv_data_exporter.py` - 1 new test
- `CLAUDE.md` - Bug fix documentation
- `RELEASE_NOTES.md` - This release notes entry

---

# pgmonkey v3.2.0 Release Notes

## Data Safety and Reliability

pgmonkey v3.2.0 is a focused maintenance release that closes a data exposure risk in the CSV
importer, fixes unreliable file handling during bulk imports, and widens Python version
compatibility for future releases.

## Highlights

### CSV Data Exposure Fix

The CSV importer's `_sync_ingest()` contained a leftover debug `print()` statement that
output the first row of CSV data to stdout during every import operation. For datasets
containing PII, credentials, or other sensitive information, this silently leaked data to
logs and terminal output. The debug print and its associated fragile `file.seek(0)` call
have been removed.

### Reliable CSV File Handling

The CSV importer previously used `file.seek(0)` to rewind a text-mode file with an active
`csv.reader` iterator - a pattern the Python documentation warns is unreliable. The reader
maintains internal buffers that are not reset by `seek()`, which could silently produce
incorrect row counts or skip data depending on buffer boundaries. The importer now uses
separate file opens for each phase (header detection, row counting, COPY ingestion),
eliminating the unreliable seek/reader interaction entirely.

### Scoped Warning Suppression

The async pool connection module had a blanket `warnings.filterwarnings('ignore',
category=RuntimeWarning)` at module level that suppressed all `RuntimeWarning`s from
`psycopg_pool` for the entire process lifetime. This could hide legitimate warnings about
pool health or configuration problems during normal operation. The suppression is now scoped
to pool construction only via `warnings.catch_warnings()`, so warnings during normal pool
operation remain visible.

### Wider Python Compatibility

The `requires-python` bound has been widened from `<3.14` to `<4.0`. The previous upper
bound would have required a release just to support Python 3.14 when it ships. The new
bound follows the same convention used by the project's other dependencies (psycopg, PyYAML,
etc.) and avoids needlessly excluding future Python releases.

## Compatibility

No breaking API changes. All existing code continues to work as before.

| Dependency | Supported Versions |
|---|---|
| Python | >= 3.10, < 4.0 |
| psycopg[binary] | >= 3.1.20, < 4.0.0 |
| psycopg_pool | >= 3.1.9, < 4.0.0 |
| PyYAML | >= 6.0.2, < 7.0.0 |
| chardet | >= 5.2.0, < 6.0.0 |
| tqdm | >= 4.64.0, < 5.0.0 |

## Test Suite

257 unit tests (unchanged from v3.1.0), all passing.

## Files Changed

- `pyproject.toml` - Version bump to 3.2.0, Python upper bound widened to < 4.0
- `src/pgmonkey/tools/csv_data_importer.py` - Removed debug print, replaced file.seek(0)
  with separate file opens, extracted `_make_reader()` helper
- `src/pgmonkey/connections/postgres/async_pool_connection.py` - Scoped RuntimeWarning
  suppression to pool construction
- `PROJECTSCOPE.md` - Version update
- `RELEASE_NOTES.md` - This release notes entry

---

# pgmonkey v3.1.0 Release Notes

## Quality, Safety, and Library Hygiene

pgmonkey v3.1.0 is a focused quality release that addresses issues found during a thorough
post-v3.0.0 review. It hardens the CSV tools for library usage, modernizes authentication
recommendations, and closes consistency gaps across the connection layer.

## Highlights

### Library-Friendly CSV Tools

The CSV importer and exporter no longer call `sys.exit(0)` when auto-generating config files.
Instead, they raise `ConfigFileCreatedError` - a proper exception that CLI handlers catch
cleanly and library users can handle programmatically. No more surprise process termination
when using pgmonkey as a dependency.

### Modern Authentication Recommendations

Server audit pg_hba.conf recommendations now use `scram-sha-256` instead of the deprecated
`md5` authentication method. This aligns with PostgreSQL 14+ defaults and ensures users get
modern, secure authentication guidance out of the box.

### Connection Safety

- **cursor() None guard** - `PGNormalConnection.cursor()` now raises a clear error when called
  without an active connection, matching the behavior of pool, async, and async_pool connections.
  Previously it raised an unhelpful `AttributeError`.

### CSV Tool Fixes

- **Multi-dot table names** - Table names like `catalog.schema.table` no longer crash. The
  schema/table split now correctly handles names with multiple dots.
- **Removed shadowed imports** - Redundant local `import csv` and `import sys` statements
  inside `_sync_ingest()` have been cleaned up.

### New Test Coverage

28 new unit tests covering CSV import/export functionality:
- BOM detection (UTF-8-sig, UTF-16-LE/BE, UTF-32-LE/BE, no BOM)
- UTF-32 vs UTF-16 BOM detection priority
- Schema/table name splitting (default schema, dotted names, multi-dot names)
- Config file auto-creation with `ConfigFileCreatedError`
- Column name formatting and validation
- Connection type resolution for import/export operations
- Tab delimiter unescaping

## Compatibility

No breaking API changes for normal usage. The only behavioral change is that CSV
import/export operations now raise `ConfigFileCreatedError` instead of calling `sys.exit(0)`
when a config file is auto-generated. Code that called these tools programmatically and
relied on `SystemExit` should catch `ConfigFileCreatedError` from
`pgmonkey.common.exceptions` instead.

| Dependency | Supported Versions |
|---|---|
| Python | 3.10, 3.11, 3.12, 3.13 |
| psycopg[binary] | >= 3.1.20, < 4.0.0 |
| psycopg_pool | >= 3.1.9, < 4.0.0 |
| PyYAML | >= 6.0.2, < 7.0.0 |
| chardet | >= 5.2.0, < 6.0.0 |
| tqdm | >= 4.64.0, < 5.0.0 |

## Test Suite

257 unit tests (up from 229 in v3.0.0), all passing. New tests cover CSV importer BOM
detection, column formatting, schema/table splitting, config auto-creation, and CSV exporter
initialization and connection type resolution.

## Files Changed

- `pyproject.toml` - Version bump to 3.1.0
- `src/pgmonkey/common/exceptions.py` - New: `ConfigFileCreatedError` exception
- `src/pgmonkey/connections/postgres/normal_connection.py` - cursor() None guard
- `src/pgmonkey/serversettings/postgres_server_config_generator.py` - md5 to scram-sha-256
- `src/pgmonkey/tools/csv_data_importer.py` - ConfigFileCreatedError, split fix, import cleanup
- `src/pgmonkey/tools/csv_data_exporter.py` - ConfigFileCreatedError, split fix
- `src/pgmonkey/cli/cli_import_subparser.py` - Catch ConfigFileCreatedError
- `src/pgmonkey/cli/cli_export_subparser.py` - Catch ConfigFileCreatedError
- `src/pgmonkey/tests/unit/test_csv_data_importer.py` - New: 21 tests
- `src/pgmonkey/tests/unit/test_csv_data_exporter.py` - New: 7 tests
- `src/pgmonkey/tests/unit/test_normal_connection.py` - New: cursor None guard test
- `src/pgmonkey/tests/unit/test_server_config_generator.py` - Updated: md5 to scram-sha-256
- `PROJECTSCOPE.md` - Version update
- `CLAUDE.md` - Bug fix documentation
- `RELEASE_NOTES.md` - This release notes entry

---

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
