# pgmonkey Test Infrastructure Report

**Date:** 2026-02-20
**pgmonkey version:** 4.0.0 (from `pyproject.toml`)
**Repository:** https://github.com/RexBytes/pgmonkey

---

## 1) What Is Implemented Today (Inventory)

### 1.1 Unit Tests

**Location:** `src/pgmonkey/tests/unit/`

17 unit test files covering all major subsystems:

| File | Lines | Scope |
|------|-------|-------|
| `test_env_interpolation.py` | 535 | Env var substitution, `from_env`, `from_file`, sensitive key protection |
| `test_connection_caching.py` | 392 | Cache keying, force_reload, atexit cleanup, connection type isolation |
| `test_csv_data_importer.py` | 311 | CSV import, BOM detection, auto_create_table, small file handling |
| `test_server_config_generator.py` | 295 | pg_hba entry generation, SSL mode recommendations |
| `test_async_pool_connection.py` | 292 | Async pool lifecycle, per-instance ContextVars |
| `test_normal_connection.py` | 279 | Sync connection connect/disconnect/cursor/GUC/transactions |
| `test_pool_connection.py` | 275 | Pool context manager, thread safety, `_pool_conn_ctx` |
| `test_server_settings_inspector.py` | 243 | `_evaluate_status`, NULL handling, pg_settings queries |
| `test_connection_factory.py` | 179 | Factory routing, config filtering (`is not None`) |
| `test_async_connection.py` | 172 | Async connection lifecycle, `__aexit__` try/finally |
| `test_code_generator.py` | 170 | Template rendering, safe SQL, repr(path) |
| `test_pgconnection_manager.py` | 144 | Manager API, cache key with connection_type |
| `test_csv_data_exporter.py` | 141 | CSV export, progress bar row counting |
| `test_config_manager.py` | 95 | Config loading, connection testing delegation |
| `test_path_utils.py` | 55 | Path utilities |
| `test_base_connection.py` | 28 | Abstract base class |
| `test_settings_manager.py` | 25 | SettingsManager init, version |

**Total: 327 tests** (verified by collection), all passing in ~1.3 seconds.

**Test style:** All unit tests use `unittest.mock` (patch, MagicMock, AsyncMock) - no real database connections required. Tests are organized as classes (`TestXxxYyy`) with methods.

### 1.2 Integration Tests (pytest-based)

**Location:** `src/pgmonkey/tests/integration/test_pgconnection_manager_integration.py`

A single file containing a parametrized test (`test_database_connection`) that exercises all four connection types (normal, pool, async, async_pool) against a live PostgreSQL instance.

**Activation:** Requires the `PGMONKEY_TEST_CONFIG` environment variable pointing to a YAML config file. If unset, the entire module is skipped via `pytest.skip(allow_module_level=True)`.

```python
# From test_pgconnection_manager_integration.py:12-18
CONFIG_FILE = os.environ.get("PGMONKEY_TEST_CONFIG")
if CONFIG_FILE is None:
    pytest.skip(
        "PGMONKEY_TEST_CONFIG environment variable not set - skipping integration tests",
        allow_module_level=True,
    )
```

### 1.3 End-to-End / Real-World Test Harness

**Location:** `test_harness/`

A fully self-contained integration test suite that:
- Spins up three PostgreSQL 16 Docker containers via `docker-compose.yml`
- Generates SSL certificates (CA, server, client)
- Runs 50+ tests across 14 categories against real databases
- Produces a Markdown report (`test_harness/report.md`)

**Structure:**

```
test_harness/
  docker-compose.yml          # 3 PostgreSQL 16 services
  run_harness.sh              # Master orchestration script
  run_tests.py                # Python test runner (custom TestHarness class)
  .gitignore                  # Excludes certs/, configs/, *.csv
  pg_configs/
    pg_hba_plain.conf         # Password auth, no SSL
    pg_hba_ssl.conf           # SSL available, password auth
    pg_hba_clientcert.conf    # SSL required + client cert
  scripts/
    generate_certs.sh         # OpenSSL CA/server/client cert generation
    setup_certs.sh            # Container entrypoint - copies certs before PG starts
    init_db.sql               # Creates test user, tables, seed data
```

### 1.4 Docker Services

Three PostgreSQL 16 instances defined in `test_harness/docker-compose.yml`:

| Service | Container Name | Host Port | Purpose |
|---------|---------------|-----------|---------|
| `pg-plain` | `pgmonkey-plain` | 5441 | Password auth (scram-sha-256), no SSL |
| `pg-ssl` | `pgmonkey-ssl` | 5442 | SSL enabled, password auth |
| `pg-clientcert` | `pgmonkey-clientcert` | 5443 | SSL + client certificate required |

**Credentials:** `pgmonkey_user` / `pgmonkey_pass` (defined in `scripts/init_db.sql`)
**Database:** `pgmonkey_test`

All services have healthchecks:
```yaml
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U postgres"]
  interval: 3s
  timeout: 3s
  retries: 10
```

### 1.5 Entry Points / Commands

| Command | What It Runs | Where |
|---------|-------------|-------|
| `python -m pytest src/pgmonkey/tests/unit/ -v` | 327 unit tests | Any environment |
| `python -m pytest src/pgmonkey/tests/unit/ -v -x` | Unit tests, stop on first failure | Any environment |
| `./test_harness/run_harness.sh` | Full end-to-end harness (Docker + tests + teardown) | Requires Docker, OpenSSL |
| `./test_harness/run_harness.sh --keep` | Same but keeps containers running | Requires Docker |
| `./test_harness/run_harness.sh --down` | Tear down containers only | Requires Docker |
| `python3 test_harness/run_tests.py` | Run harness tests only (assumes containers are up) | Requires running containers |

### 1.6 Test Output / Artifacts

| Output | Format | Location |
|--------|--------|----------|
| Unit test results | Console (pytest standard) | stdout |
| Harness results | Console (custom `[+] PASS` / `[!] FAIL` format) | stdout |
| Harness report | Markdown | `test_harness/report.md` |

**Not currently produced:** JUnit XML, coverage reports, HTML reports.

### 1.7 Config, Fixtures, and Helpers

**pytest configuration** (`pyproject.toml:53-55`):
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["src/pgmonkey/tests"]
```

**Test dependencies** (`pyproject.toml:34-39`):
```toml
[project.optional-dependencies]
test = [
    "pytest>=7.0.0,<10.0.0",
    "pytest-asyncio>=0.21.0,<2.0.0",
    "pytest-mock>=3.10.0,<4.0.0",
]
```

**Shared fixtures** (`src/pgmonkey/tests/conftest.py`):
- `sample_config` - full pgmonkey config dict
- `sample_config_file` - writes config to temp YAML, returns path
- `filtered_connection_settings` - expected filtered settings
- `ssl_config` / `ssl_config_file` - verify-full SSL configs
- `pytest_collection_modifyitems` hook - gracefully skips async tests when `pytest-asyncio` is not installed

**Harness helpers** (`test_harness/run_tests.py`):
- `_base_config()` - builds YAML config dicts for any port/conn_type/sslmode
- `write_config()` - writes config to `test_harness/configs/`
- `_run_cli()` - runs `python -m pgmonkey` CLI as subprocess

### 1.8 What Does NOT Exist

- No `.github/workflows/` directory (no GitHub Actions CI)
- No `Jenkinsfile`
- No `Makefile`
- No `tox.ini` or `noxfile.py`
- No `scripts/` directory at project root
- No linting/formatting configuration (no ruff, flake8, black, mypy, isort config)
- No coverage measurement or reporting
- No JUnit XML output configuration
- No `.pre-commit-config.yaml`

---

## 2) Sequential Flow in Professional Terms

### Current Pipeline (Manual)

```
Stage 1: Unit Tests (local dev)
    |
Stage 2: Integration Test Harness (local dev, Docker required)
    |
Stage 3: Manual inspection of report.md
```

### Stage 1: Unit Test Suite

| Aspect | Detail |
|--------|--------|
| **What runs** | `python -m pytest src/pgmonkey/tests/unit/ -v` |
| **Inputs/config** | `pyproject.toml` (`asyncio_mode = "auto"`, `testpaths`); `conftest.py` fixtures |
| **Outputs/artifacts** | Console output only (pass/fail per test) |
| **Pass/fail criteria** | Exit code 0 = all 327 tests pass; non-zero = failure |
| **Runtime** | ~1.3 seconds (verified). All tests use mocks, no I/O |

### Stage 2: End-to-End Test Harness

| Aspect | Detail |
|--------|--------|
| **What runs** | `./test_harness/run_harness.sh` - orchestration script |
| **Sub-steps** | (a) Prerequisite check (docker, openssl, python3), (b) Generate SSL certs if missing, (c) `docker compose down -v` cleanup, (d) `docker compose up -d`, (e) Wait for 3 PG instances (up to 60s each), (f) `pip install -e ".[test]"`, (g) `python3 run_tests.py`, (h) `docker compose down -v` (unless `--keep`), (i) Report exit code |
| **Inputs/config** | `docker-compose.yml`, `pg_configs/*.conf`, `scripts/init_db.sql`, `scripts/generate_certs.sh`, `scripts/setup_certs.sh` |
| **Outputs/artifacts** | `test_harness/report.md` (Markdown with summary table, per-test results, failure details, environment info) |
| **Pass/fail criteria** | `run_tests.py` returns 0 if all harness tests pass; harness exit code propagated |
| **Runtime** | Estimated 2-5 minutes: container startup (~30s), cert generation (~2s), 50+ tests with real DB connections and CLI subprocess calls |

### Stage 2 Test Categories (14 total)

1. **Connection Types** - Normal, Pool, Async, Async Pool connections (plain auth)
2. **SSL/TLS Modes** - disable, prefer, require, verify-ca, verify-full across connection types
3. **Client Certificate Auth** - verify-ca/verify-full with client certs, sync and async
4. **Connection Pooling** - min/max sizing, health check, 6-thread concurrent access, 6-task async concurrent access
5. **GUC/SET Settings** - statement_timeout, lock_timeout, work_mem via sync/async settings
6. **Transactions** - Commit on clean exit, rollback on exception, autocommit mode
7. **Env Var Interpolation** - `${VAR}`, `${VAR:-default}`, `from_env`, `from_file`, sensitive key protection, end-to-end with real connection
8. **CLI Commands** - `pgconfig create`, `pgconfig test`, `--resolve-env`, `generate-code` (both libraries, all 4 types), `pgserverconfig`, `pgserverconfig --audit`
9. **CSV Import/Export** - Export table to CSV, import CSV to new table, export-import roundtrip
10. **Connection Caching** - Same config returns cached object, different types = separate entries, force_reload, clear_cache, cache_info
11. **Config & Utilities** - `load_config`, `normalize_config` (old format), `redact_config`
12. **Code Generation** - All 8 templates (4 types x 2 libraries), safe SQL composition verification
13. **Server Audit** - Recommendation generation, live pg_settings inspection
14. **Error Handling** - Bad host fails gracefully, wrong password fails gracefully, cursor without connection

### Stage 3: Report Review (Manual)

| Aspect | Detail |
|--------|--------|
| **What runs** | Human reads `test_harness/report.md` |
| **Outputs** | Manual assessment of pass/fail |
| **Pass/fail criteria** | All rows show PASS in summary table |

---

## 3) Suitability for GitHub Actions

### 3.1 What Will Work Immediately

- **Unit tests**: No external dependencies. `pip install -e ".[test]" && pytest src/pgmonkey/tests/unit/` will work on any `ubuntu-latest` runner with Python 3.10+. Collection and execution take ~1.3 seconds.

- **Matrix testing**: pyproject.toml declares Python 3.10-3.13 support. A matrix strategy across these versions is trivial.

- **Docker Compose in harness**: GitHub Actions `ubuntu-latest` runners have Docker and Docker Compose pre-installed. The `docker-compose.yml` uses standard `postgres:16` images available on Docker Hub.

### 3.2 What Will Likely Break or Need Attention

1. **Port conflicts**: The harness uses fixed host ports 5441-5443. GitHub Actions runners are single-tenant, so this is safe - but if tests run in parallel jobs sharing a runner (self-hosted), there could be conflicts. Not an issue with GitHub-hosted runners.

2. **OpenSSL availability**: `generate_certs.sh` requires `openssl`. It is pre-installed on `ubuntu-latest` but should be listed as a prerequisite step.

3. **`pip install -e ".[test]"` with system PyYAML**: The runner may have a system-installed PyYAML that conflicts (as seen in our test: `Cannot uninstall PyYAML`). Fix: use `pip install -e ".[test]" --ignore-installed PyYAML` or use a virtual environment (which Actions `setup-python` creates by default).

4. **`run_harness.sh` does `pip install`**: The harness script runs `pip install -e ".[test]"` internally (line 135). In CI, the install should be done explicitly in a prior step, not buried in the harness script. The script should be refactored or the CI should skip that step.

5. **No JUnit XML output**: GitHub Actions can display test results natively if JUnit XML is uploaded. Currently neither the unit tests nor the harness produce XML. Fix: add `--junitxml=junit-unit.xml` to the pytest command. The harness produces Markdown only.

6. **No coverage reporting**: No `pytest-cov` or coverage configuration exists.

7. **`test_harness/report.md` is gitignored**: It is generated at runtime and listed in `.gitignore` via the `test_harness/.gitignore`. This is correct behavior - it should be uploaded as a CI artifact instead.

8. **Harness `wait_for_pg` uses `docker exec`**: This works on GitHub Actions since Docker is native (not Docker-in-Docker). No issues expected.

9. **Docker Compose `depends_on` / healthcheck**: The compose file defines healthchecks but does not use `depends_on` with `condition: service_healthy` (the services are independent). The harness script handles readiness via its own `wait_for_pg` function. This is fine.

### 3.3 Missing Readiness Checks

- The harness `wait_for_pg` function (lines 106-126 of `run_harness.sh`) is well-implemented with a 60-second timeout and diagnostic output on failure. It uses `docker exec ... pg_isready` which is the correct approach.
- The Docker healthchecks in `docker-compose.yml` are also properly configured.
- **No readiness check gap identified.**

### 3.4 Best Practices to Adopt

1. **Cache pip dependencies**: Use `actions/cache` or `actions/setup-python`'s built-in caching to avoid re-downloading `psycopg[binary]`, `psycopg_pool`, etc. on every run.

2. **Split unit and integration jobs**: Unit tests should run as a fast-feedback job (~2s). Integration tests should run as a separate job that only starts if unit tests pass. This gives developers instant feedback on logic regressions.

3. **Upload artifacts**: Upload `test_harness/report.md` and any JUnit XML as workflow artifacts.

4. **Add a linter job**: No linting is configured. Adding `ruff` (minimal config) as a fast first job would catch syntax errors and import issues before tests run.

5. **Use `docker compose up --wait`**: Instead of the custom `wait_for_pg` bash function, `docker compose up -d --wait` (Compose v2.1+) natively waits for healthchecks. This simplifies CI scripts.

### 3.5 Recommended Workflow Structure

```
Trigger: push to main, pull_request

Job 1: lint (optional, ~10s)
  - ruff check (if added)

Job 2: unit-tests (matrix: python 3.10, 3.11, 3.12, 3.13) (~30s each)
  - pip install -e ".[test]"
  - pytest src/pgmonkey/tests/unit/ --junitxml=...
  - Upload JUnit XML

Job 3: integration-tests (needs: unit-tests) (~3-5 min)
  - pip install -e ".[test]"
  - Generate certs
  - docker compose up -d --wait
  - python3 test_harness/run_tests.py
  - docker compose down -v
  - Upload report.md as artifact
```

---

## 4) Suitability for Jenkins

### 4.1 Prerequisites for Jenkins Agent

| Prerequisite | Detail |
|-------------|--------|
| **Python 3.10+** | Must be installed or available via `pyenv`/`asdf`. Multiple versions for matrix testing. |
| **pip** | With ability to install packages (virtualenv recommended) |
| **Docker Engine** | Docker CE/EE with the Docker socket accessible to the Jenkins agent user |
| **Docker Compose v2** | `docker compose` plugin (not the legacy `docker-compose` standalone) |
| **OpenSSL** | For SSL certificate generation |
| **Git** | Standard Jenkins requirement |

### 4.2 Jenkins-Specific Concerns

1. **Docker socket permissions**: The Jenkins agent user must be in the `docker` group or have sudo access to Docker. This is the most common source of Jenkins Docker failures.

2. **Workspace cleanup**: The harness generates `test_harness/certs/`, `test_harness/configs/`, and `test_harness/report.md`. The `run_harness.sh` script does `docker compose down -v` which handles container cleanup, but the generated files remain. Jenkins workspaces should use `cleanWs()` in a `post` block or the harness `--down` flag.

3. **Port conflicts on long-lived agents**: If multiple pipeline runs execute concurrently on the same agent, ports 5441-5443 will conflict. Solutions: (a) use `disableConcurrentBuilds()`, (b) use dynamic port allocation, or (c) use Docker networking with `--network` instead of host port mapping.

4. **Virtual environment isolation**: Jenkins agents running multiple projects may have package conflicts. The pipeline should create a virtualenv per build.

5. **Credential handling for PyPI**: Use Jenkins Credentials (type: Secret Text) for `TWINE_USERNAME`/`TWINE_PASSWORD` or the PyPI API token.

### 4.3 Jenkinsfile Assessment

A Jenkinsfile is straightforward given the existing tooling. The harness script `run_harness.sh` already encapsulates the entire integration test flow. A declarative pipeline would have three stages: unit tests, integration tests, and (optionally) release.

---

## 5) CI/CD End-to-End Implementation Proposal

### 5.A CI on Pull Requests

#### Proposed Jobs

**Job 1: Lint (fast feedback)**

No linter is currently configured. Recommended minimal addition:

```bash
pip install ruff
ruff check src/
```

Add to `pyproject.toml`:
```toml
[tool.ruff]
target-version = "py310"
line-length = 120

[tool.ruff.lint]
select = ["E", "F", "W", "I"]
```

**Job 2: Unit Tests (matrix)**

```bash
pip install -e ".[test]"
python -m pytest src/pgmonkey/tests/unit/ -v --tb=short --junitxml=junit-unit.xml
```

**Job 3: Integration / Harness Tests**

```bash
# Install
pip install -e ".[test]"

# Generate SSL certs
bash test_harness/scripts/generate_certs.sh

# Start PostgreSQL containers
docker compose -f test_harness/docker-compose.yml up -d --wait

# Run harness tests
python3 test_harness/run_tests.py

# Tear down
docker compose -f test_harness/docker-compose.yml down -v
```

**Artifacts to upload:**
- `junit-unit.xml` (unit test results)
- `test_harness/report.md` (integration test report)

#### Recommended File/Folder Changes (Minimal)

1. **Add `[tool.ruff]` section to `pyproject.toml`** (6 lines, see above)
2. **Add `ruff` to test dependencies** in `pyproject.toml`:
   ```toml
   [project.optional-dependencies]
   test = [
       "pytest>=7.0.0,<10.0.0",
       "pytest-asyncio>=0.21.0,<2.0.0",
       "pytest-mock>=3.10.0,<4.0.0",
   ]
   lint = [
       "ruff>=0.4.0",
   ]
   ```
3. **Create `.github/workflows/ci.yml`** (see below)
4. **Create `.github/workflows/release.yml`** (see below)

### 5.B Release on Tags

```
Trigger: push tag matching v*

Job 1: test (unit + integration - same as PR CI)
Job 2: release (needs: test)
  - Build wheel/sdist
  - Create GitHub Release with notes
  - Publish to PyPI via Trusted Publishing (OIDC)
```

### 5.C Optional: Nightly Scheduled Job

The integration harness involves Docker container orchestration, SSL cert generation, and 50+ tests against real databases. If this grows heavier over time, it can be moved to a nightly schedule. Currently at ~3-5 minutes estimated runtime, it is fast enough to run on every PR.

Recommendation: Run the full harness on every PR for now. Revisit if runtime exceeds 10 minutes.

---

### Sample `.github/workflows/ci.yml`

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

permissions:
  contents: read

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install ruff
      - run: ruff check src/

  unit-tests:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12", "3.13"]
      fail-fast: false
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
          cache: pip
      - run: pip install -e ".[test]"
      - run: python -m pytest src/pgmonkey/tests/unit/ -v --tb=short --junitxml=junit-unit.xml
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: unit-test-results-py${{ matrix.python-version }}
          path: junit-unit.xml

  integration-tests:
    runs-on: ubuntu-latest
    needs: unit-tests
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
      - run: pip install -e ".[test]"

      # Generate SSL certificates
      - run: bash test_harness/scripts/generate_certs.sh

      # Start PostgreSQL containers and wait for health
      - run: docker compose -f test_harness/docker-compose.yml up -d --wait
        env:
          COMPOSE_PROJECT_NAME: pgmonkey-ci

      # Run integration test harness
      - run: python3 test_harness/run_tests.py

      # Upload harness report
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: integration-test-report
          path: test_harness/report.md

      # Tear down containers
      - if: always()
        run: docker compose -f test_harness/docker-compose.yml down -v
        env:
          COMPOSE_PROJECT_NAME: pgmonkey-ci
```

### Sample `.github/workflows/release.yml`

```yaml
name: Release

on:
  push:
    tags:
      - "v*"

permissions:
  contents: write
  id-token: write  # Required for Trusted Publishing (OIDC)

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
      - run: pip install -e ".[test]"

      # Unit tests
      - run: python -m pytest src/pgmonkey/tests/unit/ -v --tb=short --junitxml=junit-unit.xml

      # Integration tests
      - run: bash test_harness/scripts/generate_certs.sh
      - run: docker compose -f test_harness/docker-compose.yml up -d --wait
      - run: python3 test_harness/run_tests.py
      - if: always()
        run: docker compose -f test_harness/docker-compose.yml down -v

  release:
    runs-on: ubuntu-latest
    needs: test
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      # Build distribution
      - run: pip install build
      - run: python -m build

      # Create GitHub Release
      - uses: softprops/action-gh-release@v2
        with:
          generate_release_notes: true
          files: dist/*

      # Publish to PyPI via Trusted Publishing (OIDC)
      # Prerequisites: Configure Trusted Publisher on pypi.org for this repo
      # See: https://docs.pypi.org/trusted-publishers/
      - uses: pypa/gh-action-pypi-publish@release/v1
        # No credentials needed - uses OIDC Trusted Publishing
```

### Sample `Jenkinsfile`

```groovy
pipeline {
    agent any

    options {
        disableConcurrentBuilds()
        timeout(time: 30, unit: 'MINUTES')
    }

    environment {
        // Use a virtualenv to isolate from system packages
        VENV = "${WORKSPACE}/.venv"
    }

    stages {
        stage('Setup') {
            steps {
                sh '''
                    python3 -m venv ${VENV}
                    . ${VENV}/bin/activate
                    pip install --upgrade pip
                    pip install -e ".[test]"
                '''
            }
        }

        stage('Lint') {
            steps {
                sh '''
                    . ${VENV}/bin/activate
                    pip install ruff
                    ruff check src/
                '''
            }
        }

        stage('Unit Tests') {
            steps {
                sh '''
                    . ${VENV}/bin/activate
                    python -m pytest src/pgmonkey/tests/unit/ -v --tb=short --junitxml=junit-unit.xml
                '''
            }
            post {
                always {
                    junit 'junit-unit.xml'
                }
            }
        }

        stage('Integration Tests') {
            steps {
                // Generate SSL certificates
                sh 'bash test_harness/scripts/generate_certs.sh'

                // Start PostgreSQL containers
                sh 'docker compose -f test_harness/docker-compose.yml up -d --wait'

                // Run harness tests
                sh '''
                    . ${VENV}/bin/activate
                    python3 test_harness/run_tests.py
                '''
            }
            post {
                always {
                    // Archive the test report
                    archiveArtifacts artifacts: 'test_harness/report.md', allowEmptyArchive: true

                    // Tear down containers
                    sh 'docker compose -f test_harness/docker-compose.yml down -v || true'
                }
            }
        }

        stage('Build') {
            when {
                buildingTag()
            }
            steps {
                sh '''
                    . ${VENV}/bin/activate
                    pip install build
                    python -m build
                '''
                archiveArtifacts artifacts: 'dist/*'
            }
        }

        stage('Publish to PyPI') {
            when {
                buildingTag()
            }
            steps {
                withCredentials([string(credentialsId: 'pypi-api-token', variable: 'PYPI_TOKEN')]) {
                    sh '''
                        . ${VENV}/bin/activate
                        pip install twine
                        twine upload dist/* -u __token__ -p ${PYPI_TOKEN}
                    '''
                }
            }
        }
    }

    post {
        always {
            cleanWs()
        }
    }
}
```

### Notes on Secrets/Credentials Handling

| Secret | GitHub Actions | Jenkins |
|--------|---------------|---------|
| **PyPI publishing** | Use [Trusted Publishing](https://docs.pypi.org/trusted-publishers/) (OIDC) - no secrets needed. Configure the publisher on pypi.org linking to the GitHub repo. | Store PyPI API token as a Jenkins Secret Text credential (`pypi-api-token`). Use `withCredentials` to inject. |
| **Docker Hub** | Not needed - `postgres:16` is a public image. If rate-limited, add `DOCKERHUB_USERNAME`/`DOCKERHUB_TOKEN` as repo secrets. | Same - add Docker Hub credentials if pull rate limits are hit. |
| **No other secrets required** | The test harness uses self-signed certs generated at runtime and hardcoded test credentials (`pgmonkey_user`/`pgmonkey_pass`) that only exist inside ephemeral containers. | Same. |

---

## Appendix: Files Inspected

### Project Root
- `pyproject.toml` - Build config, dependencies, pytest config, project metadata
- `requirements.txt` - Runtime dependencies (mirrors pyproject.toml)
- `.gitignore` - Standard Python gitignore
- `CLAUDE.md` - Project instructions and bug fix history

### Source Tree
- `src/pgmonkey/__init__.py`
- `src/pgmonkey/tests/conftest.py` - Shared fixtures, async skip hook
- `src/pgmonkey/tests/__init__.py`
- `src/pgmonkey/tests/unit/__init__.py`
- `src/pgmonkey/tests/unit/test_normal_connection.py` (sample, first 50 lines)
- `src/pgmonkey/tests/unit/test_connection_caching.py` (sample, first 50 lines)
- All 17 unit test files (line counts enumerated)
- `src/pgmonkey/tests/integration/__init__.py`
- `src/pgmonkey/tests/integration/test_pgconnection_manager_integration.py` (full)

### Test Harness
- `test_harness/docker-compose.yml` (full)
- `test_harness/run_harness.sh` (full, 166 lines)
- `test_harness/run_tests.py` (full, 1497 lines)
- `test_harness/.gitignore` (full)
- `test_harness/pg_configs/pg_hba_plain.conf` (full)
- `test_harness/pg_configs/pg_hba_ssl.conf` (full)
- `test_harness/pg_configs/pg_hba_clientcert.conf` (full)
- `test_harness/scripts/generate_certs.sh` (full)
- `test_harness/scripts/setup_certs.sh` (full)
- `test_harness/scripts/init_db.sql` (full)

### Directories Confirmed Absent
- `.github/` (no GitHub Actions workflows)
- `Jenkinsfile`
- `Makefile`
- `tox.ini`
- `noxfile.py`
- `scripts/` (at project root)
- `.pre-commit-config.yaml`
- `setup.cfg`
