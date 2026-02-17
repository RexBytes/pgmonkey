#!/usr/bin/env python3
"""
pgmonkey Integration Test Harness
=================================
Tests all pgmonkey features against real PostgreSQL instances.
Outputs results to report.md.

Prerequisites:
    - Three PostgreSQL instances running via docker-compose (see run_harness.sh)
    - SSL certificates generated in certs/
    - pgmonkey installed (pip install -e .)
"""

import sys
import os
import time
import asyncio
import traceback
import tempfile
import subprocess
import threading
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass
from typing import List, Callable

# ---------------------------------------------------------------------------
# Paths and configuration
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).parent.parent
HARNESS_DIR = Path(__file__).parent
CERTS_DIR = HARNESS_DIR / "certs"
CONFIGS_DIR = HARNESS_DIR / "configs"
REPORT_FILE = HARNESS_DIR / "report.md"

# Docker-mapped ports
PG_PLAIN_PORT = 5441
PG_SSL_PORT = 5442
PG_CLIENTCERT_PORT = 5443

# Shared credentials (match scripts/init_db.sql)
DB_NAME = "pgmonkey_test"
DB_USER = "pgmonkey_user"
DB_PASS = "pgmonkey_pass"

# Add project source to path
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import yaml  # noqa: E402


# ---------------------------------------------------------------------------
# Test result tracking
# ---------------------------------------------------------------------------
@dataclass
class TestResult:
    category: str
    name: str
    passed: bool
    detail: str
    duration_ms: float
    error: str = ""


# ---------------------------------------------------------------------------
# YAML config helpers
# ---------------------------------------------------------------------------
def _base_config(port, conn_type="normal", sslmode="prefer", extra_conn=None,
                 sync_settings=None, pool_settings=None,
                 async_settings=None, async_pool_settings=None):
    """Build a pgmonkey YAML config dict."""
    conn = {
        "user": DB_USER,
        "password": DB_PASS,
        "host": "localhost",
        "port": str(port),
        "dbname": DB_NAME,
        "sslmode": sslmode,
        "connect_timeout": "10",
    }
    if extra_conn:
        conn.update(extra_conn)
    cfg = {
        "connection_type": conn_type,
        "connection_settings": conn,
    }
    if sync_settings:
        cfg["sync_settings"] = sync_settings
    if pool_settings:
        cfg["pool_settings"] = pool_settings
    if async_settings:
        cfg["async_settings"] = async_settings
    if async_pool_settings:
        cfg["async_pool_settings"] = async_pool_settings
    return cfg


def write_config(name, cfg):
    """Write a YAML config file and return its path."""
    CONFIGS_DIR.mkdir(exist_ok=True)
    path = CONFIGS_DIR / f"{name}.yaml"
    with open(path, "w") as f:
        yaml.dump(cfg, f, default_flow_style=False)
    return str(path)


def _run_cli(*args, timeout=30):
    """Run pgmonkey CLI and return (returncode, stdout, stderr)."""
    cmd = [sys.executable, "-m", "pgmonkey"] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True,
                            timeout=timeout, cwd=str(PROJECT_ROOT))
    return result.returncode, result.stdout, result.stderr


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------
class TestHarness:
    def __init__(self):
        self.results: List[TestResult] = []
        self.start_time = time.monotonic()

    # -- runners --

    def run_sync(self, category: str, name: str, func: Callable, *args, **kwargs):
        start = time.monotonic()
        try:
            detail = func(*args, **kwargs)
            ms = (time.monotonic() - start) * 1000
            self.results.append(TestResult(category, name, True, detail or "OK", ms))
            self._log(True, name, ms)
        except Exception as e:
            ms = (time.monotonic() - start) * 1000
            tb = traceback.format_exc()
            self.results.append(TestResult(category, name, False, str(e), ms, tb))
            self._log(False, name, ms, str(e))

    def run_async(self, category: str, name: str, coro_func: Callable, *args, **kwargs):
        start = time.monotonic()
        try:
            detail = asyncio.run(coro_func(*args, **kwargs))
            ms = (time.monotonic() - start) * 1000
            self.results.append(TestResult(category, name, True, detail or "OK", ms))
            self._log(True, name, ms)
        except Exception as e:
            ms = (time.monotonic() - start) * 1000
            tb = traceback.format_exc()
            self.results.append(TestResult(category, name, False, str(e), ms, tb))
            self._log(False, name, ms, str(e))

    @staticmethod
    def _log(passed, name, ms, error=""):
        tag = "PASS" if passed else "FAIL"
        icon = "+" if passed else "!"
        print(f"  [{icon}] {tag}  {name}  ({ms:.0f}ms)")
        if error:
            # Truncate long error messages for console output
            short = error.replace("\n", " ")[:120]
            print(f"          {short}")

    # ======================================================================
    # TEST CATEGORIES
    # ======================================================================

    # ------------------------------------------------------------------
    # 1. Connection Types (plain, password auth)
    # ------------------------------------------------------------------
    def test_connection_types(self):
        cat = "Connection Types"
        print(f"\n--- {cat} ---")

        # Normal
        def t_normal():
            from pgmonkey import PGConnectionManager
            mgr = PGConnectionManager()
            cfg_path = write_config("normal_plain", _base_config(PG_PLAIN_PORT, "normal", "disable"))
            with mgr.get_database_connection(cfg_path) as conn:
                cur = conn.cursor()
                cur.execute("SELECT count(*) FROM test_data")
                count = cur.fetchone()[0]
                assert count == 5, f"Expected 5 rows, got {count}"
            mgr.clear_cache()
            return f"Queried test_data, got {count} rows"
        self.run_sync(cat, "Normal connection (plain)", t_normal)

        # Pool
        def t_pool():
            from pgmonkey import PGConnectionManager
            mgr = PGConnectionManager()
            cfg_path = write_config("pool_plain", _base_config(
                PG_PLAIN_PORT, "pool", "disable",
                pool_settings={"min_size": 2, "max_size": 5, "timeout": 10}
            ))
            with mgr.get_database_connection(cfg_path) as conn:
                cur = conn.cursor()
                cur.execute("SELECT version()")
                ver = cur.fetchone()[0]
            mgr.clear_cache()
            return f"Pool connection OK, PG version: {ver[:40]}..."
        self.run_sync(cat, "Pool connection (plain)", t_pool)

        # Async
        async def t_async():
            from pgmonkey import PGConnectionManager
            mgr = PGConnectionManager()
            cfg_path = write_config("async_plain", _base_config(PG_PLAIN_PORT, "async", "disable"))
            async with await mgr.get_database_connection(cfg_path) as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT count(*) FROM test_data")
                    row = await cur.fetchone()
                    assert row[0] == 5
            await mgr.clear_cache_async()
            return f"Async query OK, got {row[0]} rows"
        self.run_async(cat, "Async connection (plain)", t_async)

        # Async pool
        async def t_async_pool():
            from pgmonkey import PGConnectionManager
            mgr = PGConnectionManager()
            cfg_path = write_config("async_pool_plain", _base_config(
                PG_PLAIN_PORT, "async_pool", "disable",
                async_pool_settings={"min_size": 2, "max_size": 5, "timeout": 10}
            ))
            async with await mgr.get_database_connection(cfg_path) as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT 1 AS alive")
                    row = await cur.fetchone()
                    assert row[0] == 1
            await mgr.clear_cache_async()
            return "Async pool connection OK"
        self.run_async(cat, "Async pool connection (plain)", t_async_pool)

    # ------------------------------------------------------------------
    # 2. SSL/TLS modes
    # ------------------------------------------------------------------
    def test_ssl_modes(self):
        cat = "SSL/TLS Modes"
        print(f"\n--- {cat} ---")

        def make_ssl_test(mode, conn_type="normal"):
            """Factory for SSL mode tests."""
            def test_fn():
                from pgmonkey import PGConnectionManager
                mgr = PGConnectionManager()
                extra = {}
                if mode in ("verify-ca", "verify-full"):
                    extra["sslrootcert"] = str(CERTS_DIR / "ca.crt")
                cfg_path = write_config(
                    f"{conn_type}_ssl_{mode.replace('-', '_')}",
                    _base_config(PG_SSL_PORT, conn_type, mode, extra_conn=extra,
                                 pool_settings={"min_size": 2, "max_size": 5, "timeout": 10}
                                 if conn_type == "pool" else None)
                )
                with mgr.get_database_connection(cfg_path) as conn:
                    cur = conn.cursor()
                    cur.execute("SHOW ssl")
                    ssl_val = cur.fetchone()[0]
                    cur.execute("SELECT count(*) FROM test_data")
                    count = cur.fetchone()[0]
                    assert count == 5
                mgr.clear_cache()
                return f"ssl={ssl_val}, queried OK"
            return test_fn

        async def make_async_ssl_test(mode, conn_type="async"):
            from pgmonkey import PGConnectionManager
            mgr = PGConnectionManager()
            extra = {}
            if mode in ("verify-ca", "verify-full"):
                extra["sslrootcert"] = str(CERTS_DIR / "ca.crt")
            settings = None
            if conn_type == "async_pool":
                settings = {"min_size": 2, "max_size": 5, "timeout": 10}
            cfg_path = write_config(
                f"{conn_type}_ssl_{mode.replace('-', '_')}",
                _base_config(PG_SSL_PORT, conn_type, mode, extra_conn=extra,
                             async_pool_settings=settings)
            )
            async with await mgr.get_database_connection(cfg_path) as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT count(*) FROM test_data")
                    row = await cur.fetchone()
                    assert row[0] == 5
            await mgr.clear_cache_async()
            return f"Async SSL {mode} OK"

        # Normal connection - all SSL modes
        for mode in ("disable", "prefer", "require", "verify-ca", "verify-full"):
            self.run_sync(cat, f"Normal sslmode={mode}", make_ssl_test(mode))

        # Pool with require
        self.run_sync(cat, "Pool sslmode=require", make_ssl_test("require", "pool"))

        # Async with require
        self.run_async(cat, "Async sslmode=require",
                       lambda: make_async_ssl_test("require", "async"))

        # Async pool with require
        self.run_async(cat, "Async pool sslmode=require",
                       lambda: make_async_ssl_test("require", "async_pool"))

    # ------------------------------------------------------------------
    # 3. Client Certificate Authentication
    # ------------------------------------------------------------------
    def test_client_certificates(self):
        cat = "Client Certificate Auth"
        print(f"\n--- {cat} ---")

        def make_cert_test(sslmode, conn_type="normal"):
            def test_fn():
                from pgmonkey import PGConnectionManager
                mgr = PGConnectionManager()
                extra = {
                    "sslcert": str(CERTS_DIR / "client.crt"),
                    "sslkey": str(CERTS_DIR / "client.key"),
                    "sslrootcert": str(CERTS_DIR / "ca.crt"),
                }
                pool_s = None
                if conn_type == "pool":
                    pool_s = {"min_size": 2, "max_size": 5, "timeout": 10}
                cfg_path = write_config(
                    f"{conn_type}_clientcert_{sslmode.replace('-', '_')}",
                    _base_config(PG_CLIENTCERT_PORT, conn_type, sslmode,
                                 extra_conn=extra, pool_settings=pool_s)
                )
                with mgr.get_database_connection(cfg_path) as conn:
                    cur = conn.cursor()
                    cur.execute("SELECT current_user, count(*) FROM test_data GROUP BY 1")
                    row = cur.fetchone()
                    assert row[0] == DB_USER
                    assert row[1] == 5
                mgr.clear_cache()
                return f"Client cert auth OK (user={row[0]})"
            return test_fn

        async def async_cert_test(sslmode):
            from pgmonkey import PGConnectionManager
            mgr = PGConnectionManager()
            extra = {
                "sslcert": str(CERTS_DIR / "client.crt"),
                "sslkey": str(CERTS_DIR / "client.key"),
                "sslrootcert": str(CERTS_DIR / "ca.crt"),
            }
            cfg_path = write_config(
                f"async_clientcert_{sslmode.replace('-', '_')}",
                _base_config(PG_CLIENTCERT_PORT, "async", sslmode, extra_conn=extra)
            )
            async with await mgr.get_database_connection(cfg_path) as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT current_user")
                    row = await cur.fetchone()
                    assert row[0] == DB_USER
            await mgr.clear_cache_async()
            return f"Async client cert auth OK (user={row[0]})"

        self.run_sync(cat, "Normal verify-ca + client cert", make_cert_test("verify-ca"))
        self.run_sync(cat, "Normal verify-full + client cert", make_cert_test("verify-full"))
        self.run_sync(cat, "Pool verify-ca + client cert", make_cert_test("verify-ca", "pool"))
        self.run_async(cat, "Async verify-ca + client cert",
                       lambda: async_cert_test("verify-ca"))

    # ------------------------------------------------------------------
    # 4. Connection Pooling features
    # ------------------------------------------------------------------
    def test_pool_features(self):
        cat = "Connection Pooling"
        print(f"\n--- {cat} ---")

        # Pool min/max sizing
        def t_pool_sizing():
            from pgmonkey import PGConnectionManager
            mgr = PGConnectionManager()
            cfg_path = write_config("pool_sizing", _base_config(
                PG_PLAIN_PORT, "pool", "disable",
                pool_settings={"min_size": 1, "max_size": 3, "timeout": 10}
            ))
            with mgr.get_database_connection(cfg_path) as conn:
                cur = conn.cursor()
                cur.execute("SELECT 1")
                assert cur.fetchone()[0] == 1
            mgr.clear_cache()
            return "Pool min_size=1, max_size=3 OK"
        self.run_sync(cat, "Pool min/max sizing", t_pool_sizing)

        # Pool with health check
        def t_pool_healthcheck():
            from pgmonkey import PGConnectionManager
            mgr = PGConnectionManager()
            cfg_path = write_config("pool_healthcheck", _base_config(
                PG_PLAIN_PORT, "pool", "disable",
                pool_settings={
                    "min_size": 1, "max_size": 3,
                    "timeout": 10, "check_on_checkout": True
                }
            ))
            with mgr.get_database_connection(cfg_path) as conn:
                cur = conn.cursor()
                cur.execute("SELECT 'healthcheck_ok'")
                val = cur.fetchone()[0]
                assert val == "healthcheck_ok"
            mgr.clear_cache()
            return "Pool with check_on_checkout=true OK"
        self.run_sync(cat, "Pool health check on checkout", t_pool_healthcheck)

        # Pool concurrent thread access
        def t_pool_threads():
            from pgmonkey import PGConnectionManager
            mgr = PGConnectionManager()
            cfg_path = write_config("pool_threads", _base_config(
                PG_PLAIN_PORT, "pool", "disable",
                pool_settings={"min_size": 2, "max_size": 8, "timeout": 10}
            ))
            errors = []
            results = []

            def worker(thread_id):
                try:
                    with mgr.get_database_connection(cfg_path) as conn:
                        cur = conn.cursor()
                        cur.execute("SELECT pg_backend_pid()")
                        pid = cur.fetchone()[0]
                        results.append((thread_id, pid))
                except Exception as e:
                    errors.append((thread_id, str(e)))

            threads = [threading.Thread(target=worker, args=(i,)) for i in range(6)]
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=30)

            mgr.clear_cache()
            if errors:
                raise AssertionError(f"Thread errors: {errors}")
            pids = {r[1] for r in results}
            return f"6 threads OK, {len(pids)} distinct backend PIDs"
        self.run_sync(cat, "Pool concurrent threads (6)", t_pool_threads)

        # Async pool concurrent tasks
        async def t_async_pool_tasks():
            from pgmonkey import PGConnectionManager
            mgr = PGConnectionManager()
            cfg_path = write_config("async_pool_tasks", _base_config(
                PG_PLAIN_PORT, "async_pool", "disable",
                async_pool_settings={"min_size": 2, "max_size": 8, "timeout": 10}
            ))

            async def task(task_id):
                async with await mgr.get_database_connection(cfg_path) as conn:
                    async with conn.cursor() as cur:
                        await cur.execute("SELECT pg_backend_pid()")
                        row = await cur.fetchone()
                        return (task_id, row[0])

            results = await asyncio.gather(*[task(i) for i in range(6)])
            await mgr.clear_cache_async()
            pids = {r[1] for r in results}
            return f"6 async tasks OK, {len(pids)} distinct backend PIDs"
        self.run_async(cat, "Async pool concurrent tasks (6)", t_async_pool_tasks)

    # ------------------------------------------------------------------
    # 5. GUC/SET Settings
    # ------------------------------------------------------------------
    def test_guc_settings(self):
        cat = "GUC/SET Settings"
        print(f"\n--- {cat} ---")

        def t_normal_guc():
            from pgmonkey import PGConnectionManager
            mgr = PGConnectionManager()
            cfg_path = write_config("normal_guc", _base_config(
                PG_PLAIN_PORT, "normal", "disable",
                sync_settings={
                    "statement_timeout": "5000",
                    "lock_timeout": "3000",
                    "work_mem": "16MB",
                }
            ))
            with mgr.get_database_connection(cfg_path) as conn:
                cur = conn.cursor()
                cur.execute("SHOW statement_timeout")
                st = cur.fetchone()[0]
                cur.execute("SHOW lock_timeout")
                lt = cur.fetchone()[0]
                cur.execute("SHOW work_mem")
                wm = cur.fetchone()[0]
            mgr.clear_cache()
            return f"statement_timeout={st}, lock_timeout={lt}, work_mem={wm}"
        self.run_sync(cat, "Normal conn sync_settings", t_normal_guc)

        def t_pool_guc():
            from pgmonkey import PGConnectionManager
            mgr = PGConnectionManager()
            cfg_path = write_config("pool_guc", _base_config(
                PG_PLAIN_PORT, "pool", "disable",
                sync_settings={"statement_timeout": "7000", "work_mem": "32MB"},
                pool_settings={"min_size": 1, "max_size": 3, "timeout": 10}
            ))
            with mgr.get_database_connection(cfg_path) as conn:
                cur = conn.cursor()
                cur.execute("SHOW statement_timeout")
                st = cur.fetchone()[0]
                cur.execute("SHOW work_mem")
                wm = cur.fetchone()[0]
            mgr.clear_cache()
            return f"Pool GUC: statement_timeout={st}, work_mem={wm}"
        self.run_sync(cat, "Pool conn sync_settings (configure callback)", t_pool_guc)

        async def t_async_guc():
            from pgmonkey import PGConnectionManager
            mgr = PGConnectionManager()
            cfg_path = write_config("async_guc", _base_config(
                PG_PLAIN_PORT, "async", "disable",
                async_settings={
                    "statement_timeout": "9000",
                    "work_mem": "24MB",
                }
            ))
            async with await mgr.get_database_connection(cfg_path) as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SHOW statement_timeout")
                    row = await cur.fetchone()
                    st = row[0]
                    await cur.execute("SHOW work_mem")
                    row = await cur.fetchone()
                    wm = row[0]
            await mgr.clear_cache_async()
            return f"Async GUC: statement_timeout={st}, work_mem={wm}"
        self.run_async(cat, "Async conn async_settings", t_async_guc)

        async def t_async_pool_guc():
            from pgmonkey import PGConnectionManager
            mgr = PGConnectionManager()
            cfg_path = write_config("async_pool_guc", _base_config(
                PG_PLAIN_PORT, "async_pool", "disable",
                async_settings={"statement_timeout": "11000", "work_mem": "48MB"},
                async_pool_settings={"min_size": 1, "max_size": 3, "timeout": 10}
            ))
            async with await mgr.get_database_connection(cfg_path) as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SHOW statement_timeout")
                    row = await cur.fetchone()
                    st = row[0]
            await mgr.clear_cache_async()
            return f"Async pool GUC: statement_timeout={st}"
        self.run_async(cat, "Async pool async_settings (configure callback)", t_async_pool_guc)

    # ------------------------------------------------------------------
    # 6. Transactions
    # ------------------------------------------------------------------
    def test_transactions(self):
        cat = "Transactions"
        print(f"\n--- {cat} ---")

        def t_commit():
            from pgmonkey import PGConnectionManager
            mgr = PGConnectionManager()
            cfg_path = write_config("txn_commit", _base_config(PG_PLAIN_PORT, "normal", "disable"))
            # Insert a row - should commit on clean exit
            with mgr.get_database_connection(cfg_path) as conn:
                cur = conn.cursor()
                cur.execute("DELETE FROM transaction_test")  # clean slate
                cur.execute("INSERT INTO transaction_test (data) VALUES ('committed_row')")
            # Read back in a new connection
            with mgr.get_database_connection(cfg_path, force_reload=True) as conn:
                cur = conn.cursor()
                cur.execute("SELECT data FROM transaction_test WHERE data = 'committed_row'")
                row = cur.fetchone()
                assert row is not None, "Committed row not found"
                assert row[0] == "committed_row"
            mgr.clear_cache()
            return "Commit on clean exit verified"
        self.run_sync(cat, "Commit on clean context exit", t_commit)

        def t_rollback():
            from pgmonkey import PGConnectionManager
            mgr = PGConnectionManager()
            cfg_path = write_config("txn_rollback", _base_config(PG_PLAIN_PORT, "normal", "disable"))
            # Clean slate
            with mgr.get_database_connection(cfg_path) as conn:
                cur = conn.cursor()
                cur.execute("DELETE FROM transaction_test WHERE data = 'rollback_row'")
            mgr.clear_cache()
            # Insert a row then raise - should rollback
            try:
                with mgr.get_database_connection(cfg_path) as conn:
                    cur = conn.cursor()
                    cur.execute("INSERT INTO transaction_test (data) VALUES ('rollback_row')")
                    raise ValueError("Intentional error for rollback test")
            except ValueError:
                pass
            # Verify the row is NOT there
            mgr2 = PGConnectionManager()
            with mgr2.get_database_connection(cfg_path) as conn:
                cur = conn.cursor()
                cur.execute("SELECT data FROM transaction_test WHERE data = 'rollback_row'")
                row = cur.fetchone()
                assert row is None, f"Row should have been rolled back, got {row}"
            mgr2.clear_cache()
            return "Rollback on exception verified"
        self.run_sync(cat, "Rollback on exception", t_rollback)

        def t_autocommit():
            from pgmonkey import PGConnectionManager
            mgr = PGConnectionManager()
            cfg_path = write_config("txn_autocommit", _base_config(
                PG_PLAIN_PORT, "normal", "disable",
                extra_conn={"autocommit": True}
            ))
            with mgr.get_database_connection(cfg_path) as conn:
                cur = conn.cursor()
                # In autocommit mode, each statement is its own transaction
                cur.execute("SELECT 1")
                assert cur.fetchone()[0] == 1
            mgr.clear_cache()
            return "Autocommit mode OK"
        self.run_sync(cat, "Autocommit mode", t_autocommit)

    # ------------------------------------------------------------------
    # 7. Environment Variable Interpolation
    # ------------------------------------------------------------------
    def test_env_interpolation(self):
        cat = "Env Var Interpolation"
        print(f"\n--- {cat} ---")

        def t_env_substitution():
            """Test ${VAR} substitution."""
            from pgmonkey import load_config
            os.environ["PGMONKEY_TEST_HOST"] = "localhost"
            os.environ["PGMONKEY_TEST_PORT"] = str(PG_PLAIN_PORT)
            os.environ["PGMONKEY_TEST_USER"] = DB_USER
            os.environ["PGMONKEY_TEST_PASS"] = DB_PASS
            cfg = {
                "connection_type": "normal",
                "connection_settings": {
                    "user": "${PGMONKEY_TEST_USER}",
                    "password": "${PGMONKEY_TEST_PASS}",
                    "host": "${PGMONKEY_TEST_HOST}",
                    "port": "${PGMONKEY_TEST_PORT}",
                    "dbname": DB_NAME,
                    "sslmode": "disable",
                }
            }
            path = write_config("env_substitution", cfg)
            resolved = load_config(path, resolve_env=True)
            conn_s = resolved["connection_settings"]
            assert conn_s["user"] == DB_USER, f"Expected {DB_USER}, got {conn_s['user']}"
            assert conn_s["host"] == "localhost"
            assert conn_s["port"] == str(PG_PLAIN_PORT)
            return f"Resolved: user={conn_s['user']}, host={conn_s['host']}, port={conn_s['port']}"
        self.run_sync(cat, "${VAR} substitution", t_env_substitution)

        def t_env_default():
            """Test ${VAR:-default} fallback."""
            from pgmonkey import load_config
            # Make sure the var does NOT exist
            os.environ.pop("PGMONKEY_NONEXISTENT", None)
            cfg = {
                "connection_type": "normal",
                "connection_settings": {
                    "user": DB_USER,
                    "password": DB_PASS,
                    "host": "${PGMONKEY_NONEXISTENT:-localhost}",
                    "port": "${PGMONKEY_NONEXISTENT_PORT:-5432}",
                    "dbname": DB_NAME,
                    "sslmode": "disable",
                }
            }
            path = write_config("env_default", cfg)
            resolved = load_config(path, resolve_env=True)
            conn_s = resolved["connection_settings"]
            assert conn_s["host"] == "localhost"
            assert conn_s["port"] == "5432"
            return f"Defaults applied: host={conn_s['host']}, port={conn_s['port']}"
        self.run_sync(cat, "${VAR:-default} fallback", t_env_default)

        def t_env_from_env():
            """Test from_env structured reference."""
            from pgmonkey import load_config
            os.environ["PGMONKEY_SECRET_PASS"] = DB_PASS
            cfg = {
                "connection_type": "normal",
                "connection_settings": {
                    "user": DB_USER,
                    "password": {"from_env": "PGMONKEY_SECRET_PASS"},
                    "host": "localhost",
                    "port": str(PG_PLAIN_PORT),
                    "dbname": DB_NAME,
                    "sslmode": "disable",
                }
            }
            path = write_config("env_from_env", cfg)
            resolved = load_config(path, resolve_env=True)
            assert resolved["connection_settings"]["password"] == DB_PASS
            return "from_env resolved correctly"
        self.run_sync(cat, "from_env structured reference", t_env_from_env)

        def t_env_from_file():
            """Test from_file structured reference."""
            from pgmonkey import load_config
            # Write password to a temp file (simulating Kubernetes Secret)
            secret_file = CONFIGS_DIR / "test_secret.txt"
            secret_file.write_text(DB_PASS + "\n")  # trailing newline like K8s
            cfg = {
                "connection_type": "normal",
                "connection_settings": {
                    "user": DB_USER,
                    "password": {"from_file": str(secret_file)},
                    "host": "localhost",
                    "port": str(PG_PLAIN_PORT),
                    "dbname": DB_NAME,
                    "sslmode": "disable",
                }
            }
            path = write_config("env_from_file", cfg)
            resolved = load_config(path, resolve_env=True)
            # from_file should trim trailing newline
            assert resolved["connection_settings"]["password"] == DB_PASS
            return "from_file resolved (trailing newline trimmed)"
        self.run_sync(cat, "from_file structured reference", t_env_from_file)

        def t_env_sensitive_protection():
            """Test that sensitive keys reject defaults."""
            from pgmonkey import load_config, EnvInterpolationError
            os.environ.pop("PGMONKEY_MISSING_PASS", None)
            cfg = {
                "connection_type": "normal",
                "connection_settings": {
                    "user": DB_USER,
                    "password": "${PGMONKEY_MISSING_PASS:-fallback_pass}",
                    "host": "localhost",
                    "port": str(PG_PLAIN_PORT),
                    "dbname": DB_NAME,
                    "sslmode": "disable",
                }
            }
            path = write_config("env_sensitive_blocked", cfg)
            try:
                load_config(path, resolve_env=True)
                raise AssertionError("Should have raised EnvInterpolationError")
            except EnvInterpolationError:
                return "Sensitive key default correctly blocked"
        self.run_sync(cat, "Sensitive key default protection", t_env_sensitive_protection)

        def t_env_allow_sensitive():
            """Test allow_sensitive_defaults=True."""
            from pgmonkey import load_config
            os.environ.pop("PGMONKEY_MISSING_PASS2", None)
            cfg = {
                "connection_type": "normal",
                "connection_settings": {
                    "user": DB_USER,
                    "password": "${PGMONKEY_MISSING_PASS2:-devpass}",
                    "host": "localhost",
                    "port": str(PG_PLAIN_PORT),
                    "dbname": DB_NAME,
                    "sslmode": "disable",
                }
            }
            path = write_config("env_sensitive_allowed", cfg)
            resolved = load_config(path, resolve_env=True, allow_sensitive_defaults=True)
            assert resolved["connection_settings"]["password"] == "devpass"
            return "Sensitive default allowed when opted in"
        self.run_sync(cat, "allow_sensitive_defaults=True", t_env_allow_sensitive)

        def t_env_missing_error():
            """Test that missing required var raises EnvInterpolationError."""
            from pgmonkey import load_config, EnvInterpolationError
            os.environ.pop("PGMONKEY_TOTALLY_MISSING", None)
            cfg = {
                "connection_type": "normal",
                "connection_settings": {
                    "user": DB_USER,
                    "password": DB_PASS,
                    "host": "${PGMONKEY_TOTALLY_MISSING}",
                    "port": str(PG_PLAIN_PORT),
                    "dbname": DB_NAME,
                    "sslmode": "disable",
                }
            }
            path = write_config("env_missing_error", cfg)
            try:
                load_config(path, resolve_env=True)
                raise AssertionError("Should have raised EnvInterpolationError")
            except EnvInterpolationError as e:
                return f"Correct error: {e}"
        self.run_sync(cat, "Missing env var raises error", t_env_missing_error)

        def t_env_real_connection():
            """End-to-end: resolve env vars and actually connect."""
            from pgmonkey import PGConnectionManager
            os.environ["PGMONKEY_E2E_HOST"] = "localhost"
            os.environ["PGMONKEY_E2E_PORT"] = str(PG_PLAIN_PORT)
            os.environ["PGMONKEY_E2E_USER"] = DB_USER
            os.environ["PGMONKEY_E2E_PASS"] = DB_PASS
            cfg = {
                "connection_type": "normal",
                "connection_settings": {
                    "user": "${PGMONKEY_E2E_USER}",
                    "password": "${PGMONKEY_E2E_PASS}",
                    "host": "${PGMONKEY_E2E_HOST}",
                    "port": "${PGMONKEY_E2E_PORT}",
                    "dbname": DB_NAME,
                    "sslmode": "disable",
                }
            }
            path = write_config("env_e2e", cfg)
            mgr = PGConnectionManager()
            with mgr.get_database_connection(path, resolve_env=True) as conn:
                cur = conn.cursor()
                cur.execute("SELECT current_user")
                user = cur.fetchone()[0]
                assert user == DB_USER
            mgr.clear_cache()
            return f"End-to-end env interpolation + connection OK (user={user})"
        self.run_sync(cat, "End-to-end env vars to live connection", t_env_real_connection)

    # ------------------------------------------------------------------
    # 8. CLI Commands
    # ------------------------------------------------------------------
    def test_cli_commands(self):
        cat = "CLI Commands"
        print(f"\n--- {cat} ---")

        def t_pgconfig_create():
            out_path = str(CONFIGS_DIR / "cli_created.yaml")
            rc, stdout, stderr = _run_cli("pgconfig", "create", "--type", "pg",
                                          "--filepath", out_path)
            assert rc == 0, f"Exit code {rc}: {stderr}"
            assert Path(out_path).exists(), "Config file not created"
            with open(out_path) as f:
                cfg = yaml.safe_load(f)
            assert "connection_type" in cfg
            assert "connection_settings" in cfg
            return f"Config template created with keys: {list(cfg.keys())}"
        self.run_sync(cat, "pgconfig create --type pg", t_pgconfig_create)

        def t_pgconfig_test():
            cfg_path = write_config("cli_test_conn", _base_config(
                PG_PLAIN_PORT, "normal", "disable"))
            rc, stdout, stderr = _run_cli("pgconfig", "test", "--filepath", cfg_path)
            output = stdout + stderr
            # The test command should succeed and show connection info
            assert rc == 0, f"Exit code {rc}: {output}"
            return f"Connection test passed (exit=0)"
        self.run_sync(cat, "pgconfig test --filepath", t_pgconfig_test)

        def t_pgconfig_test_resolve_env():
            os.environ["PGMONKEY_CLI_HOST"] = "localhost"
            os.environ["PGMONKEY_CLI_PORT"] = str(PG_PLAIN_PORT)
            os.environ["PGMONKEY_CLI_USER"] = DB_USER
            os.environ["PGMONKEY_CLI_PASS"] = DB_PASS
            cfg = {
                "connection_type": "normal",
                "connection_settings": {
                    "user": "${PGMONKEY_CLI_USER}",
                    "password": "${PGMONKEY_CLI_PASS}",
                    "host": "${PGMONKEY_CLI_HOST}",
                    "port": "${PGMONKEY_CLI_PORT}",
                    "dbname": DB_NAME,
                    "sslmode": "disable",
                }
            }
            cfg_path = write_config("cli_test_env", cfg)
            rc, stdout, stderr = _run_cli("pgconfig", "test", "--filepath", cfg_path,
                                          "--resolve-env")
            output = stdout + stderr
            assert rc == 0, f"Exit code {rc}: {output}"
            return "Connection test with --resolve-env passed"
        self.run_sync(cat, "pgconfig test --resolve-env", t_pgconfig_test_resolve_env)

        def t_generate_code_pgmonkey():
            cfg_path = write_config("cli_codegen", _base_config(
                PG_PLAIN_PORT, "normal", "disable"))
            rc, stdout, stderr = _run_cli("pgconfig", "generate-code", "--filepath", cfg_path,
                                          "--library", "pgmonkey")
            output = stdout + stderr
            assert rc == 0, f"Exit code {rc}: {output}"
            assert "PGConnectionManager" in output, "Expected PGConnectionManager in output"
            return "Code generation (pgmonkey library) OK"
        self.run_sync(cat, "pgconfig generate-code --library pgmonkey", t_generate_code_pgmonkey)

        def t_generate_code_psycopg():
            cfg_path = write_config("cli_codegen_psycopg", _base_config(
                PG_PLAIN_PORT, "normal", "disable"))
            rc, stdout, stderr = _run_cli("pgconfig", "generate-code", "--filepath", cfg_path,
                                          "--library", "psycopg")
            output = stdout + stderr
            assert rc == 0, f"Exit code {rc}: {output}"
            assert "psycopg" in output.lower(), "Expected psycopg in output"
            return "Code generation (psycopg library) OK"
        self.run_sync(cat, "pgconfig generate-code --library psycopg", t_generate_code_psycopg)

        def t_generate_code_all_types():
            results = []
            for ctype in ("normal", "pool", "async", "async_pool"):
                cfg_path = write_config(f"cli_codegen_{ctype}", _base_config(
                    PG_PLAIN_PORT, ctype, "disable",
                    pool_settings={"min_size": 2, "max_size": 5, "timeout": 10}
                    if ctype == "pool" else None,
                    async_pool_settings={"min_size": 2, "max_size": 5, "timeout": 10}
                    if ctype == "async_pool" else None,
                ))
                rc, stdout, stderr = _run_cli("pgconfig", "generate-code",
                                              "--filepath", cfg_path,
                                              "--connection-type", ctype)
                assert rc == 0, f"Exit {rc} for {ctype}: {stderr}"
                results.append(ctype)
            return f"Code generated for all types: {results}"
        self.run_sync(cat, "generate-code for all 4 connection types", t_generate_code_all_types)

        def t_pgserverconfig():
            cfg_path = write_config("cli_serverconfig", _base_config(
                PG_PLAIN_PORT, "pool", "disable",
                pool_settings={"min_size": 5, "max_size": 20, "timeout": 30}
            ))
            rc, stdout, stderr = _run_cli("pgserverconfig", "--filepath", cfg_path)
            output = stdout + stderr
            assert rc == 0, f"Exit code {rc}: {output}"
            return "Server config recommendations generated"
        self.run_sync(cat, "pgserverconfig recommendations", t_pgserverconfig)

        def t_pgserverconfig_audit():
            cfg_path = write_config("cli_audit", _base_config(
                PG_PLAIN_PORT, "pool", "disable",
                pool_settings={"min_size": 5, "max_size": 20, "timeout": 30}
            ))
            rc, stdout, stderr = _run_cli("pgserverconfig", "--filepath", cfg_path, "--audit")
            output = stdout + stderr
            # Audit may show warnings about permissions on some settings, that's OK
            # It should not crash
            assert rc == 0, f"Exit code {rc}: {output}"
            return "Server audit completed"
        self.run_sync(cat, "pgserverconfig --audit (live server)", t_pgserverconfig_audit)

    # ------------------------------------------------------------------
    # 9. CSV Import/Export
    # ------------------------------------------------------------------
    def test_csv_import_export(self):
        cat = "CSV Import/Export"
        print(f"\n--- {cat} ---")

        def t_csv_export():
            cfg_path = write_config("csv_export_conn", _base_config(
                PG_PLAIN_PORT, "normal", "disable"))
            export_file = str(CONFIGS_DIR / "exported_test_data.csv")
            rc, stdout, stderr = _run_cli(
                "pgexport",
                "--table", "test_data",
                "--connconfig", cfg_path,
                "--export_file", export_file,
                timeout=60
            )
            output = stdout + stderr
            assert rc == 0, f"Exit code {rc}: {output}"
            assert Path(export_file).exists(), "Export file not created"
            lines = Path(export_file).read_text().strip().split("\n")
            # Should have header + 5 data rows
            assert len(lines) >= 5, f"Expected at least 5 lines, got {len(lines)}"
            return f"Exported {len(lines)} lines to CSV"
        self.run_sync(cat, "Export table to CSV", t_csv_export)

        def t_csv_import():
            # First create a CSV to import
            import_csv = CONFIGS_DIR / "import_test.csv"
            import_csv.write_text(
                "name,value,category\n"
                "zeta,600,group_d\n"
                "eta,700,group_d\n"
                "theta,800,group_e\n"
            )
            cfg_path = write_config("csv_import_conn", _base_config(
                PG_PLAIN_PORT, "normal", "disable"))
            rc, stdout, stderr = _run_cli(
                "pgimport",
                "--table", "imported_data",
                "--connconfig", cfg_path,
                "--import_file", str(import_csv),
                timeout=60
            )
            output = stdout + stderr
            assert rc == 0, f"Exit code {rc}: {output}"
            # Verify the data was imported
            from pgmonkey import PGConnectionManager
            mgr = PGConnectionManager()
            with mgr.get_database_connection(cfg_path) as conn:
                cur = conn.cursor()
                cur.execute("SELECT count(*) FROM imported_data")
                count = cur.fetchone()[0]
                assert count == 3, f"Expected 3 imported rows, got {count}"
            mgr.clear_cache()
            return f"Imported 3 rows into imported_data table"
        self.run_sync(cat, "Import CSV to new table", t_csv_import)

        def t_csv_roundtrip():
            """Export, import, verify data matches."""
            cfg_path = write_config("csv_roundtrip_conn", _base_config(
                PG_PLAIN_PORT, "normal", "disable"))
            export_file = str(CONFIGS_DIR / "roundtrip_export.csv")
            # Export
            rc, stdout, stderr = _run_cli(
                "pgexport", "--table", "test_data",
                "--connconfig", cfg_path,
                "--export_file", export_file, timeout=60)
            assert rc == 0, f"Export failed: {stderr}"
            # Import into new table
            rc, stdout, stderr = _run_cli(
                "pgimport", "--table", "roundtrip_imported",
                "--connconfig", cfg_path,
                "--import_file", export_file, timeout=60)
            assert rc == 0, f"Import failed: {stderr}"
            # Verify row counts match
            from pgmonkey import PGConnectionManager
            mgr = PGConnectionManager()
            with mgr.get_database_connection(cfg_path) as conn:
                cur = conn.cursor()
                cur.execute("SELECT count(*) FROM test_data")
                orig = cur.fetchone()[0]
                cur.execute("SELECT count(*) FROM roundtrip_imported")
                imported = cur.fetchone()[0]
                assert orig == imported, f"Row count mismatch: {orig} vs {imported}"
            mgr.clear_cache()
            return f"Roundtrip OK: {orig} rows exported and re-imported"
        self.run_sync(cat, "CSV export-import roundtrip", t_csv_roundtrip)

    # ------------------------------------------------------------------
    # 10. Connection Caching
    # ------------------------------------------------------------------
    def test_connection_caching(self):
        cat = "Connection Caching"
        print(f"\n--- {cat} ---")

        def t_cache_same():
            from pgmonkey import PGConnectionManager
            mgr = PGConnectionManager()
            cfg_path = write_config("cache_same", _base_config(
                PG_PLAIN_PORT, "normal", "disable"))
            conn1 = mgr.get_database_connection(cfg_path)
            conn2 = mgr.get_database_connection(cfg_path)
            assert conn1 is conn2, "Expected same cached connection object"
            info = mgr.cache_info
            assert info["size"] == 1
            mgr.clear_cache()
            return f"Same config returns cached object (cache size={info['size']})"
        self.run_sync(cat, "Same config returns cached connection", t_cache_same)

        def t_cache_diff_type():
            from pgmonkey import PGConnectionManager
            mgr = PGConnectionManager()
            cfg_path = write_config("cache_diff_type", _base_config(
                PG_PLAIN_PORT, "normal", "disable",
                pool_settings={"min_size": 1, "max_size": 3, "timeout": 10}
            ))
            conn_normal = mgr.get_database_connection(cfg_path, "normal")
            conn_pool = mgr.get_database_connection(cfg_path, "pool")
            assert conn_normal is not conn_pool, "Different types should be different objects"
            info = mgr.cache_info
            assert info["size"] == 2
            mgr.clear_cache()
            return f"Different types get separate cache entries (size={info['size']})"
        self.run_sync(cat, "Different connection_type = separate cache entry", t_cache_diff_type)

        def t_cache_force_reload():
            from pgmonkey import PGConnectionManager
            mgr = PGConnectionManager()
            cfg_path = write_config("cache_reload", _base_config(
                PG_PLAIN_PORT, "normal", "disable"))
            conn1 = mgr.get_database_connection(cfg_path)
            conn2 = mgr.get_database_connection(cfg_path, force_reload=True)
            assert conn1 is not conn2, "force_reload should create new connection"
            mgr.clear_cache()
            return "force_reload creates new connection"
        self.run_sync(cat, "force_reload creates new connection", t_cache_force_reload)

        def t_cache_clear():
            from pgmonkey import PGConnectionManager
            mgr = PGConnectionManager()
            cfg_path = write_config("cache_clear", _base_config(
                PG_PLAIN_PORT, "normal", "disable"))
            mgr.get_database_connection(cfg_path)
            assert mgr.cache_info["size"] > 0
            mgr.clear_cache()
            assert mgr.cache_info["size"] == 0
            return "Cache cleared successfully"
        self.run_sync(cat, "clear_cache() empties cache", t_cache_clear)

        def t_cache_info():
            from pgmonkey import PGConnectionManager
            mgr = PGConnectionManager()
            cfg1 = write_config("cache_info_1", _base_config(
                PG_PLAIN_PORT, "normal", "disable"))
            cfg2 = write_config("cache_info_2", _base_config(
                PG_PLAIN_PORT, "normal", "disable",
                extra_conn={"application_name": "cache_test_2"}))
            mgr.get_database_connection(cfg1)
            mgr.get_database_connection(cfg2)
            info = mgr.cache_info
            assert info["size"] == 2
            assert "connection_types" in info
            mgr.clear_cache()
            return f"cache_info: size={info['size']}, types={list(info.get('connection_types', {}).values())[:2]}"
        self.run_sync(cat, "cache_info reports correctly", t_cache_info)

    # ------------------------------------------------------------------
    # 11. Config and Utilities
    # ------------------------------------------------------------------
    def test_config_utilities(self):
        cat = "Config & Utilities"
        print(f"\n--- {cat} ---")

        def t_load_config():
            from pgmonkey import load_config
            cfg_path = write_config("util_load", _base_config(
                PG_PLAIN_PORT, "normal", "disable"))
            cfg = load_config(cfg_path)
            assert cfg["connection_type"] == "normal"
            assert cfg["connection_settings"]["host"] == "localhost"
            return f"Config loaded: type={cfg['connection_type']}"
        self.run_sync(cat, "load_config basic", t_load_config)

        def t_normalize_old_format():
            """Test that old postgresql: wrapper is auto-unwrapped."""
            from pgmonkey.common.utils.configutils import normalize_config
            import warnings
            old_cfg = {
                "postgresql": {
                    "connection_type": "normal",
                    "connection_settings": {
                        "host": "localhost",
                    }
                }
            }
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                result = normalize_config(old_cfg)
                # Should have produced a DeprecationWarning
                dep_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
                assert len(dep_warnings) > 0, "Expected DeprecationWarning for old format"
            assert result["connection_type"] == "normal"
            return "Old format auto-unwrapped with DeprecationWarning"
        self.run_sync(cat, "normalize_config (old postgresql: format)", t_normalize_old_format)

        def t_redact_config():
            from pgmonkey import redact_config
            cfg = {
                "connection_type": "normal",
                "connection_settings": {
                    "user": "myuser",
                    "password": "supersecret",
                    "host": "localhost",
                    "sslkey": "/path/to/key",
                    "sslcert": "/path/to/cert",
                    "sslrootcert": "/path/to/ca",
                }
            }
            redacted = redact_config(cfg)
            conn = redacted["connection_settings"]
            assert conn["password"] == "***REDACTED***"
            assert conn["sslkey"] == "***REDACTED***"
            assert conn["user"] == "myuser"  # not sensitive
            assert conn["host"] == "localhost"  # not sensitive
            return f"Redacted keys: password, sslkey, sslcert, sslrootcert"
        self.run_sync(cat, "redact_config masks sensitive values", t_redact_config)

    # ------------------------------------------------------------------
    # 12. Code Generation (programmatic)
    # ------------------------------------------------------------------
    def test_code_generation(self):
        cat = "Code Generation"
        print(f"\n--- {cat} ---")

        def t_codegen_templates():
            import io
            from contextlib import redirect_stdout
            from pgmonkey.tools.connection_code_generator import ConnectionCodeGenerator
            gen = ConnectionCodeGenerator()
            cfg_path = write_config("codegen_test", _base_config(
                PG_PLAIN_PORT, "normal", "disable",
                pool_settings={"min_size": 2, "max_size": 5, "timeout": 10},
                async_pool_settings={"min_size": 2, "max_size": 5, "timeout": 10}
            ))
            results = []
            for ctype in ("normal", "pool", "async", "async_pool"):
                for lib in ("pgmonkey", "psycopg"):
                    buf = io.StringIO()
                    with redirect_stdout(buf):
                        gen.generate_connection_code(cfg_path, ctype, lib)
                    code = buf.getvalue()
                    assert len(code) > 50, \
                        f"Empty/short code for {ctype}/{lib}"
                    results.append(f"{ctype}/{lib}={len(code)}chars")
            return f"All 8 templates generated: {', '.join(results)}"
        self.run_sync(cat, "All 8 code templates (4 types x 2 libraries)", t_codegen_templates)

        def t_codegen_safe_sql():
            """Verify generated code uses safe SQL composition."""
            import io
            from contextlib import redirect_stdout
            from pgmonkey.tools.connection_code_generator import ConnectionCodeGenerator
            gen = ConnectionCodeGenerator()
            cfg_path = write_config("codegen_sql_safe", _base_config(
                PG_PLAIN_PORT, "async", "disable",
                async_settings={"statement_timeout": "5000"}
            ))
            buf = io.StringIO()
            with redirect_stdout(buf):
                gen.generate_connection_code(cfg_path, "async", "psycopg")
            code = buf.getvalue()
            assert "sql.SQL" in code and "sql.Identifier" in code, \
                "Generated code should use safe SQL composition for GUC settings"
            return "Generated code uses psycopg.sql for safe GUC SET"
        self.run_sync(cat, "Generated code uses safe SQL composition", t_codegen_safe_sql)

    # ------------------------------------------------------------------
    # 13. Server Audit (programmatic)
    # ------------------------------------------------------------------
    def test_server_audit(self):
        cat = "Server Audit"
        print(f"\n--- {cat} ---")

        def t_recommendations():
            import io
            from contextlib import redirect_stdout
            from pgmonkey.serversettings.postgres_server_config_generator import PostgresServerConfigGenerator
            cfg_path = write_config("audit_recs", _base_config(
                PG_PLAIN_PORT, "pool", "require",
                pool_settings={"min_size": 5, "max_size": 20, "timeout": 30},
                extra_conn={"sslrootcert": str(CERTS_DIR / "ca.crt")}
            ))
            gen = PostgresServerConfigGenerator(cfg_path)
            buf = io.StringIO()
            with redirect_stdout(buf):
                gen.print_configurations()
            output = buf.getvalue()
            assert len(output) > 0, "No recommendations generated"
            return f"Recommendations generated ({len(output)} chars)"
        self.run_sync(cat, "Generate postgresql.conf/pg_hba recommendations", t_recommendations)

        def t_live_audit():
            from pgmonkey.managers.pgconnection_manager import PGConnectionManager
            from pgmonkey.serversettings.postgres_server_settings_inspector import PostgresServerSettingsInspector
            mgr = PGConnectionManager()
            cfg_path = write_config("audit_live", _base_config(
                PG_PLAIN_PORT, "normal", "disable"))
            with mgr.get_database_connection(cfg_path) as conn:
                inspector = PostgresServerSettingsInspector(conn.connection)
                settings = inspector.get_current_settings()
                assert settings is not None, "get_current_settings returned None"
                assert "max_connections" in settings
                mc = settings["max_connections"]["value"]
            mgr.clear_cache()
            return f"Live audit OK: max_connections={mc}, {len(settings)} settings inspected"
        self.run_sync(cat, "Live server pg_settings audit", t_live_audit)

    # ------------------------------------------------------------------
    # 14. Error Handling
    # ------------------------------------------------------------------
    def test_error_handling(self):
        cat = "Error Handling"
        print(f"\n--- {cat} ---")

        def t_bad_host():
            from pgmonkey import PGConnectionManager
            mgr = PGConnectionManager()
            cfg_path = write_config("err_bad_host", _base_config(
                19999, "normal", "disable",
                extra_conn={"host": "192.0.2.1", "connect_timeout": "2"}
            ))
            try:
                with mgr.get_database_connection(cfg_path) as conn:
                    pass
                raise AssertionError("Should have raised connection error")
            except Exception as e:
                if "Should have raised" in str(e):
                    raise
                mgr.clear_cache()
                return f"Graceful error: {type(e).__name__}"
        self.run_sync(cat, "Bad host fails gracefully", t_bad_host)

        def t_bad_password():
            from pgmonkey import PGConnectionManager
            mgr = PGConnectionManager()
            cfg_path = write_config("err_bad_pass", _base_config(
                PG_PLAIN_PORT, "normal", "disable",
                extra_conn={"password": "wrong_password", "connect_timeout": "5"}
            ))
            try:
                with mgr.get_database_connection(cfg_path) as conn:
                    pass
                raise AssertionError("Should have raised auth error")
            except Exception as e:
                if "Should have raised" in str(e):
                    raise
                mgr.clear_cache()
                return f"Graceful error: {type(e).__name__}: {str(e)[:60]}"
        self.run_sync(cat, "Wrong password fails gracefully", t_bad_password)

        def t_cursor_no_conn():
            from pgmonkey.connections.postgres.normal_connection import PGNormalConnection
            conn = PGNormalConnection({})
            try:
                conn.cursor()
                raise AssertionError("Should have raised error for no connection")
            except Exception as e:
                if "Should have raised" in str(e):
                    raise
                return f"Correct error: {str(e)[:80]}"
        self.run_sync(cat, "Cursor without connection raises error", t_cursor_no_conn)

    # ======================================================================
    # Report generation
    # ======================================================================
    def generate_report(self):
        """Write report.md with full test results."""
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed
        total_time = (time.monotonic() - self.start_time) * 1000

        # Get pgmonkey version
        try:
            from pgmonkey.settings.settings_manager import SettingsManager
            sm = SettingsManager()
            version = sm.get_version()
        except Exception:
            version = "unknown"

        # Get PG version
        try:
            from pgmonkey import PGConnectionManager
            mgr = PGConnectionManager()
            cfg_path = write_config("report_ver", _base_config(PG_PLAIN_PORT, "normal", "disable"))
            with mgr.get_database_connection(cfg_path) as conn:
                cur = conn.cursor()
                cur.execute("SELECT version()")
                pg_version = cur.fetchone()[0].split(",")[0]
            mgr.clear_cache()
        except Exception:
            pg_version = "unknown"

        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        # Build category summary
        categories = {}
        for r in self.results:
            if r.category not in categories:
                categories[r.category] = {"passed": 0, "failed": 0, "total": 0}
            categories[r.category]["total"] += 1
            if r.passed:
                categories[r.category]["passed"] += 1
            else:
                categories[r.category]["failed"] += 1

        lines = []
        lines.append("# pgmonkey Integration Test Report\n")
        lines.append(f"**Date:** {now}  ")
        lines.append(f"**pgmonkey version:** {version}  ")
        lines.append(f"**PostgreSQL:** {pg_version}  ")
        lines.append(f"**Total tests:** {total}  ")
        lines.append(f"**Passed:** {passed}  ")
        lines.append(f"**Failed:** {failed}  ")
        lines.append(f"**Duration:** {total_time:.0f}ms  ")
        lines.append("")

        # Summary table
        lines.append("## Summary\n")
        lines.append("| Category | Passed | Failed | Total |")
        lines.append("|----------|--------|--------|-------|")
        for cat, counts in categories.items():
            status = "PASS" if counts["failed"] == 0 else "**FAIL**"
            lines.append(f"| {cat} | {counts['passed']} | {counts['failed']} | {counts['total']} |")
        lines.append("")

        # Detailed results per category
        lines.append("## Detailed Results\n")
        current_cat = None
        for r in self.results:
            if r.category != current_cat:
                current_cat = r.category
                lines.append(f"### {current_cat}\n")
                lines.append("| Test | Status | Duration | Detail |")
                lines.append("|------|--------|----------|--------|")
            status = "PASS" if r.passed else "**FAIL**"
            detail = r.detail.replace("|", "/").replace("\n", " ")[:120]
            lines.append(f"| {r.name} | {status} | {r.duration_ms:.0f}ms | {detail} |")
            if r.category != (self.results[self.results.index(r) + 1].category
                              if self.results.index(r) + 1 < len(self.results) else None):
                lines.append("")

        # Failed test details
        failed_tests = [r for r in self.results if not r.passed]
        if failed_tests:
            lines.append("## Failed Test Details\n")
            for r in failed_tests:
                lines.append(f"### FAIL: {r.name}\n")
                lines.append(f"**Category:** {r.category}  ")
                lines.append(f"**Duration:** {r.duration_ms:.0f}ms  ")
                lines.append(f"**Error:** {r.detail}\n")
                if r.error:
                    lines.append("```")
                    lines.append(r.error.strip())
                    lines.append("```\n")

        # Environment
        lines.append("## Test Environment\n")
        lines.append("| Instance | Port | Purpose |")
        lines.append("|----------|------|---------|")
        lines.append(f"| pg-plain | {PG_PLAIN_PORT} | Password auth, no SSL |")
        lines.append(f"| pg-ssl | {PG_SSL_PORT} | SSL enabled, password auth |")
        lines.append(f"| pg-clientcert | {PG_CLIENTCERT_PORT} | SSL + client certificate required |")
        lines.append("")

        report = "\n".join(lines)
        REPORT_FILE.write_text(report)
        return report, passed, failed

    # ======================================================================
    # Main runner
    # ======================================================================
    def run_all(self):
        print("=" * 60)
        print("  pgmonkey Integration Test Harness")
        print("=" * 60)

        self.test_connection_types()
        self.test_ssl_modes()
        self.test_client_certificates()
        self.test_pool_features()
        self.test_guc_settings()
        self.test_transactions()
        self.test_env_interpolation()
        self.test_cli_commands()
        self.test_csv_import_export()
        self.test_connection_caching()
        self.test_config_utilities()
        self.test_code_generation()
        self.test_server_audit()
        self.test_error_handling()

        report, passed, failed = self.generate_report()

        total = passed + failed
        print("\n" + "=" * 60)
        print(f"  RESULTS: {passed}/{total} passed, {failed} failed")
        print(f"  Report written to: {REPORT_FILE}")
        print("=" * 60)

        return 0 if failed == 0 else 1


if __name__ == "__main__":
    harness = TestHarness()
    sys.exit(harness.run_all())
