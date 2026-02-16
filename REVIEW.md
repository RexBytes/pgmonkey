# pgmonkey Code Review - Pool Abstraction and Best Practices

## Overview

Review of pgmonkey v2.1.0 codebase, documentation, tests, and packaging.
Includes assessment of an external review with prioritized recommendations.

---

## Bugs and Issues Found in the Current Code

### 1. Race condition in connection caching

**File:** `src/pgmonkey/managers/pgconnection_manager.py:145-168`

The cache lock is released between the cache-miss check and the connection
creation/storage. Two threads hitting the same config simultaneously can both
get cache misses, both create connections, and one gets silently overwritten
(leaked):

```python
with self._cache_lock:          # Lock acquired
    if cache_key in self._cache:
        ...
                                # Lock released here
self._register_atexit()
# ... connection created outside lock ...
with self._cache_lock:          # Lock re-acquired to store
    self._cache[cache_key] = connection
```

Thread A and Thread B both pass the cache check, both create a pool, Thread A
stores first, Thread B overwrites it. Thread A's pool is never cleaned up.

**Fix:** Use a per-key lock or sentinel pattern so only one thread creates a
connection for a given cache key.

### 2. `NormalConnection.transaction()` always disconnects

**File:** `src/pgmonkey/connections/postgres/normal_connection.py:42-52`

The `finally` block calls `self.disconnect()`, which means every `transaction()`
call destroys the connection. For cached connections, this is surprising - the
user gets back a dead connection from the cache on next use.

**Fix:** Remove `disconnect()` from the `finally` block in `transaction()`.
Let the connection lifecycle be managed by the context manager or explicit
`disconnect()` calls, consistent with how pool connections work.

### 3. Pool `test_connection()` logic error

**File:** `src/pgmonkey/connections/postgres/pool_connection.py:39-56`

Connections are acquired inside `with` blocks and appended to a list, but each
`with` block returns the connection to the pool before the next iteration.
The `len(connections)` check doesn't validate concurrent pool capacity - it only
tests that the loop completed N times sequentially.

### 4. `async_settings` not applied for `async_pool` connections

`PGAsyncConnection` applies GUC settings via `_apply_async_settings()` after
connect. `PGAsyncPoolConnection` does not apply any session-level settings to
borrowed connections. If a user expects `statement_timeout` to work in async
pool mode, it silently won't.

**Fix:** Apply GUC settings on each connection checkout (via psycopg_pool's
`configure` callback), or document this as a known limitation.

### 5. All observability uses `print()` instead of `logging`

Every connection type uses `print()` for diagnostics. Libraries should never
print to stdout - they should use `logging.getLogger(__name__)` so users can
control output via standard logging configuration.

---

## Assessment of the External Review

### Agree - High value, fits pgmonkey's scope

- **Config validation/linting:** Highest-impact, lowest-effort improvement.
  `_filter_config()` silently drops unknown keys. A typo like `hosst` is
  ignored with a cryptic connection failure later. Add unknown-key warnings
  and range checks (e.g., `min_size > max_size`). Skip opinionated warnings
  about sslmode - pgmonkey shouldn't judge deployment topology.

- **Pre-ping / stale connection recovery:** Valid, but psycopg_pool already
  has a `check` parameter on `ConnectionPool` and `AsyncConnectionPool`.
  Just expose it in the YAML config. No custom implementation needed.

### Partially agree - Valid need, scope should be smaller

- **Retry policy:** pgmonkey manages connections, not query execution. Adding
  retry means wrapping `cursor.execute()`, changing the architecture from
  connection-layer to query-layer. Better approach: provide an importable
  retry decorator as a separate utility.

- **Observability:** "Query duration histograms, pool gauges, SQL redaction"
  describes an APM system. Right-sized version: replace `print()` with
  `logging`, and add optional lifecycle event callbacks (`on_connect`,
  `on_checkout`, `on_checkin`, `on_disconnect`).

- **Checkout-time protection:** psycopg_pool's `ConnectionPool` already has
  a `timeout` parameter. pgmonkey doesn't expose it. Just surface it in the
  config.

### Disagree - Out of scope

- **Secrets abstraction:** General configuration concern, not PostgreSQL-specific.
  Users solve this with `os.environ`, `pydantic-settings`, `sops`, etc. before
  calling pgmonkey. Adding `${ENV_VAR}` interpolation creates a parallel config
  resolution system that competes with existing tools.

- **Failover/read-replica routing:** Fundamentally different product. Requires
  query parsing, health checking, lag detection, and routing logic. Overlaps
  with PgBouncer/ProxySQL. Would triple codebase complexity.

- **Transaction helper policies:** `transaction(profile="readonly_analytics")`
  hides SQL behind an opinionated abstraction. Users who need specific isolation
  levels already know the SET command. Extend the existing `async_settings`
  pattern instead.

---

## Recommended Priority Order

| Priority | Item | Effort | Impact |
|----------|------|--------|--------|
| 1 | Replace `print()` with `logging` | Low | High - production-blocking |
| 2 | Fix race condition in caching | Low | High - correctness |
| 3 | Config validation (unknown keys, range checks) | Low | High - DX |
| 4 | Expose `check` param for pool health checks | Low | Medium - operational |
| 5 | Expose pool `timeout` param in config | Low | Medium - operational |
| 6 | Fix `NormalConnection.transaction()` disconnect | Low | Medium - correctness |
| 7 | Apply `async_settings` to async_pool connections | Medium | Medium - consistency |
| 8 | Lifecycle event callbacks | Medium | Medium - extensibility |
| 9 | Importable retry decorator (separate utility) | Medium | Medium - convenience |

Items 1-6 are small changes that fix real problems.
Items 7-9 are modest features that extend the existing architecture naturally.

---

## Summary

The external review correctly identifies what problems exist but oversizes
several solutions. Secrets management, replica routing, and a full observability
stack would turn pgmonkey from a focused connection library into database
middleware - a different product.

The concrete bugs (race condition, transaction disconnect, async_settings gap)
should be fixed before adding any new abstractions. Fixing correctness issues
is always higher priority than new features.
