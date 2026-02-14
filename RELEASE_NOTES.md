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
