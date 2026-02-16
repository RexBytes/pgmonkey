# pgmonkey - Project Scope

> **One job: get Python code connected to PostgreSQL, cleanly.**

pgmonkey is a focused PostgreSQL connection management library. It wraps
[psycopg 3](https://www.psycopg.org/psycopg3/) and
[psycopg_pool](https://www.psycopg.org/psycopg3/docs/api/pool.html) behind a
single YAML config file, provides four connection types (`normal`, `pool`,
`async`, `async_pool`), and stays out of the way.

This document defines what pgmonkey **is**, what it **is not**, and where the
boundary sits. Use it when evaluating feature requests, reviewing pull requests,
or deciding whether a change belongs here or in userland.

---

## Core Responsibilities

These are the things pgmonkey owns:

| Area | What pgmonkey does |
|---|---|
| **Connection lifecycle** | Connect, disconnect, commit, rollback, cursor, context managers. |
| **Connection pooling** | Expose psycopg_pool's `ConnectionPool` and `AsyncConnectionPool` with sane defaults. |
| **YAML configuration** | One file drives connection settings, pool sizing, SSL, and GUC params. |
| **Connection caching** | Cache connections/pools by config hash so repeated calls reuse the same instance. |
| **Thread safety** | Protect the cache with locks; support concurrent sync and async callers. |
| **Automatic cleanup** | atexit handler + explicit `clear_cache()` / `clear_cache_async()`. |
| **Config validation** | Warn on unknown connection keys; reject invalid pool ranges (min > max). |
| **Health checks** | Optional `check_on_checkout` (SELECT 1) on pool connections. |
| **GUC settings** | Apply `async_settings` (statement_timeout, lock_timeout, etc.) to async and async_pool connections. |
| **CLI utilities** | Create configs, test connections, generate example code, generate server-side config suggestions. |
| **CSV import/export** | Bulk-load CSV into a table; export a table to CSV. Simple, no transforms. |
| **Code generation** | Print working Python examples for each connection type given a config file. |
| **Server config hints** | Generate recommended `pg_hba.conf` / `postgresql.conf` snippets from client config. |
| **Server settings audit** | Query live server `pg_settings` and `pg_hba_file_rules` (read-only) to compare current values against recommendations. Gracefully handles permission errors. |

---

## Explicit Non-Goals

These are the things pgmonkey will **never** do. If a feature request falls
here, the answer is "solve it in userland" or "use a dedicated tool."

### No ORM or Query Builder

pgmonkey hands you a raw `psycopg` cursor. You write SQL. We don't generate
queries, map objects to rows, or manage result sets. Use SQLAlchemy, Django ORM,
or raw SQL.

### No Database Migrations

We manage connections, not schemas. No DDL generation, version tracking, or
migration runners. Use Alembic, Flyway, or pg_dump/pg_restore.

### No Secrets Management

Passwords live in the YAML file (or are injected by the caller before passing
the config dict). pgmonkey does not read environment variables, integrate with
vaults, or do config interpolation. Solve this with `os.environ`,
`pydantic-settings`, SOPS, or whatever your stack uses - then hand the resolved
dict to `get_database_connection_from_dict()`.

### No Multi-Host / Failover / Replica Routing

pgmonkey connects to **one** PostgreSQL endpoint per config. No primary
detection, read-replica routing, connection-level failover, or health-check
orchestration. Use PgBouncer, Pgpool-II, or your cloud provider's proxy for
that.

### No Retry Policies or Transaction Profiles

We provide `transaction()` context managers. We don't wrap them with automatic
retries, backoff, deadlock detection, or isolation-level presets. That's
application logic.

### No Observability Stack

pgmonkey uses Python's `logging` module (`logging.getLogger(__name__)`). We
don't emit metrics, histograms, OpenTelemetry spans, or redacted query logs.
Instrument at the application layer using psycopg's `trace` callback or your
APM.

### No Adaptive Pool Sizing

Pool sizes are static (`min_size` / `max_size`). No runtime scaling, no
connection-count heuristics, no machine-learning-based tuning.

### No Support for Non-PostgreSQL Databases

The name says it. MySQL, SQLite, Oracle, etc. are out of scope.

---

## Design Principles

These guide day-to-day decisions:

1. **Thin wrapper, not an abstraction layer.** psycopg is excellent. pgmonkey
   adds config-driven setup, caching, and lifecycle management - not a new API
   on top of cursors.

2. **YAML is the interface.** Users should be able to switch from `normal` to
   `async_pool` by changing one line in the config, not by rewriting Python
   code.

3. **No surprises.** Context managers behave like Python developers expect:
   commit on clean exit, rollback on exception. Pools return connections, they
   don't close them.

4. **Minimal dependencies.** psycopg, psycopg_pool, PyYAML, chardet, tqdm.
   That's the full list. No web frameworks, no async runtimes, no utility
   mega-packages.

5. **Fail loud on misconfiguration, fail safe on teardown.** Raise `ValueError`
   for bad pool settings. Swallow exceptions during atexit cleanup.

6. **Logging, not printing.** Library code uses `logging`. CLI code can use
   `print()` for user-facing output.

7. **Tests don't need a database.** Unit tests mock psycopg. Integration tests
   are gated behind a real PostgreSQL instance and are opt-in.

---

## Architecture Boundaries

```
┌─────────────────────────────────────────────────────┐
│                    User Code                        │
│  (SQL, transactions, retries, business logic)       │
└────────────────────────┬────────────────────────────┘
                         │ get_database_connection()
                         │ get_database_connection_from_dict()
┌────────────────────────▼────────────────────────────┐
│              PGConnectionManager                    │
│  (caching, routing, atexit, thread safety)          │
└────────────────────────┬────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────┐
│           PostgresConnectionFactory                 │
│  (config filtering, validation, type dispatch)      │
└──┬──────────┬──────────┬──────────┬─────────────────┘
   │          │          │          │
   ▼          ▼          ▼          ▼
 Normal     Pool      Async    AsyncPool
  Conn      Conn      Conn      Conn
   │          │          │          │
   └──────────┴──────────┴──────────┘
                  │
         psycopg / psycopg_pool
                  │
              PostgreSQL
```

**Above the line** (user code): SQL, retries, error handling, secrets, migrations.
pgmonkey doesn't touch this.

**Below the line** (psycopg): Wire protocol, type adaptation, COPY, notifications.
pgmonkey delegates to this.

**On the line** (pgmonkey): Config → Connection → Cache → Cleanup. That's it.

---

## CLI Scope

| Command | Purpose | Boundary |
|---|---|---|
| `pgconfig create` | Generate a YAML template | Template only - doesn't write credentials |
| `pgconfig test` | Validate a connection works | SELECT 1 - doesn't inspect schema |
| `pgconfig generate-code` | Print Python example | Starter code - not a code generator framework |
| `pgserverconfig` | Suggest server-side settings | Recommendations - not an installer |
| `pgserverconfig --audit` | Compare live server settings against recommendations | Read-only queries - never modifies server settings |
| `pgimport` | Load CSV into a table | Bulk insert - no transforms, joins, or upserts |
| `pgexport` | Dump a table to CSV | Full table - no WHERE clauses or joins |

CLI commands are thin wrappers around manager classes. They handle argument
parsing and print output. Business logic lives in `managers/` and `tools/`.

---

## What Belongs in a Pull Request

**Yes:**
- Bug fixes in connection lifecycle, caching, or pool behavior
- Exposing existing psycopg/psycopg_pool parameters through config
- Improving error messages or validation
- Adding tests (unit or integration)
- Documentation improvements
- Performance improvements to existing paths
- Logging improvements

**Maybe (needs discussion):**
- New connection settings (must be native psycopg params)
- New CLI subcommands (must fit the "config + connect" theme)
- New pool parameters (must be native psycopg_pool params)

**No:**
- ORM features, query builders, or result mappers
- Multi-database support
- Secrets/vault integration
- Retry/circuit-breaker logic
- Metrics/tracing/APM integration
- Adaptive pool sizing
- Features that add new runtime dependencies

---

## Version & Compatibility

- **Current version:** 2.2.0
- **Python:** 3.10+
- **psycopg:** >=3.1.20, <4.0.0
- **psycopg_pool:** >=3.1.9, <4.0.0
- **License:** MIT

---

*This document is the canonical reference for project scope decisions.
When in doubt, refer here. If a feature isn't listed in
"Core Responsibilities," it probably doesn't belong.*
