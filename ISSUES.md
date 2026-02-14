# pgmonkey — Internal Issue Tracker

This file tracks structural issues identified in pgmonkey, their fixes, and rationale.
It is for maintainer reference only and is not published on the website.

---

## Issue #1: Connection Caching Was Opt-In (Pool Storm Risk)

**Status:** Fixed
**Severity:** High
**Affected versions:** < 2.0.0 (and originally in 2.0.0 before this patch)
**Affected types:** All (normal, pool, async, async_pool)

### Problem

`PGConnectionManager` created a brand-new connection or pool on every call to
`get_database_connection()` / `get_database_connection_from_dict()`. For pooled
connection types, this meant each call opened an entirely new pool instead of
reusing the existing one — a classic "pool storm" that could exhaust database
server connections.

### Fix

Connection caching is now always-on. Connections are keyed by a SHA-256 hash of
the full config dictionary (sorted, deterministic). Repeated calls with the same
config return the cached instance. A `force_reload=True` parameter is available
to explicitly replace a cached connection when needed.

An `atexit` handler performs best-effort cleanup of all cached connections at
process exit.

### Files Changed

- `src/pgmonkey/managers/pgconnection_manager.py` — Added `_cache`, `_cache_lock`,
  `_config_hash()`, `_register_atexit()`, `_cleanup_at_exit()`, `cache_info`,
  `clear_cache()`, `clear_cache_async()`.
- `src/pgmonkey/tests/unit/test_connection_caching.py` — New test file covering
  sync caching, async caching, force reload, atexit cleanup, config hashing.

---

## Issue #2: Async Pool `__aexit__` Destroyed the Entire Pool

**Status:** Fixed
**Severity:** High
**Affected versions:** All prior versions and original 2.0.0
**Affected types:** `async_pool`

### Problem

`PGAsyncPoolConnection.__aexit__()` called `self.disconnect()`, which closes
the entire `AsyncConnectionPool`. This meant that after a single `async with`
block, the pool was destroyed and could not be reused. Users who followed the
standard context-manager pattern (`async with pool_conn:`) would unknowingly
kill their pool on every use.

The sync pool (`PGPoolConnection`) did not have this problem — its `__exit__`
correctly borrows and returns a connection from the pool.

### Fix

Rewrote `__aenter__` / `__aexit__` to mirror the sync pool's borrow/return
pattern:

- `__aenter__`: Acquires a connection from the pool via `pool.connection()`.
  Stores the connection context and raw connection in `_pool_conn_ctx` and
  `_conn`.
- `__aexit__`: Commits or rolls back the acquired connection, then returns it
  to the pool via `_pool_conn_ctx.__aexit__()`. The pool itself remains open.

Also made `cursor()` and `transaction()` dual-mode:
- Inside a context manager: uses the already-acquired `_conn`.
- Standalone: acquires its own connection from the pool (old behavior).

### Files Changed

- `src/pgmonkey/connections/postgres/async_pool_connection.py` — Rewrote
  `__aenter__`, `__aexit__`, `cursor()`, `transaction()`, `commit()`, `rollback()`.
- `src/pgmonkey/tests/unit/test_connection_caching.py` — Added
  `TestAsyncPoolContextManager` with 4 tests.

---

## Issue #3: Sync Pool `__exit__` Calls `disconnect()` (By Design, But Noteworthy)

**Status:** Documented / Monitor
**Severity:** Low
**Affected types:** `pool`

### Observation

`PGPoolConnection.__exit__()` calls `self._conn.close()` to return the
borrowed connection to the pool — this is correct. However, the pool itself
is never explicitly closed unless `disconnect()` is called or the atexit
handler runs.

With always-on caching and the atexit handler, this is handled correctly.
The pool lives in the cache for the lifetime of the process and is cleaned
up at exit.

No code change needed — this is working as intended. Noting it here so
future maintainers understand the lifecycle.

---

## Issue #4: Async Pool `commit()` / `rollback()` Were No-Ops

**Status:** Fixed (as part of Issue #2)
**Severity:** Medium
**Affected versions:** 2.0.0 (original)
**Affected types:** `async_pool`

### Problem

`PGAsyncPoolConnection.commit()` and `rollback()` checked `if self._conn`
but `_conn` was never set outside the context manager. This meant manual
commit/rollback calls outside `async with` were silently ignored.

### Fix

With the Issue #2 fix, `_conn` is now set during `__aenter__` and cleared
during `__aexit__`. Inside a context manager block, `commit()` and
`rollback()` correctly operate on the acquired connection.

Outside a context manager, they remain no-ops (there is no connection to
commit/rollback), which is the correct behavior — callers should use
`async with` or the `cursor()` / `transaction()` context managers.

---

## Issue #5: Documentation Gaps — No Best Practice Recipes

**Status:** Fixed
**Severity:** Medium
**Affected types:** All

### Problem

The documentation showed basic usage but did not provide production-ready
code recipes or explain how pgmonkey's built-in features (caching, pool
lifecycle management) protect users from common pitfalls.

### Fix

Added:
- `docs/best_practices.html` — Styled documentation page with complete
  code recipes for all 4 connection types, plus app-level design patterns
  (Flask sync, FastAPI async).
- README section "Best Practice Recipes" with the same content.
- Navigation links added to `docs/index.html` and `docs/reference.html`.
