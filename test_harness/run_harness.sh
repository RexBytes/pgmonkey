#!/usr/bin/env bash
# pgmonkey Integration Test Harness - Master Script
#
# Usage:
#   ./run_harness.sh           Run tests (starts Docker, runs tests, tears down)
#   ./run_harness.sh --keep    Run tests but keep Docker containers running after
#   ./run_harness.sh --down    Just tear down Docker containers
#   ./run_harness.sh --help    Show this help
#
# Prerequisites:
#   - Docker and Docker Compose
#   - OpenSSL (for certificate generation)
#   - Python 3.10+ with pip

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.yml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

info()  { echo -e "${BLUE}[INFO]${NC} $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}   $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
fail()  { echo -e "${RED}[FAIL]${NC} $*"; }

KEEP_CONTAINERS=false
DOWN_ONLY=false

for arg in "$@"; do
    case "$arg" in
        --keep) KEEP_CONTAINERS=true ;;
        --down) DOWN_ONLY=true ;;
        --help|-h)
            head -12 "$0" | tail -8
            exit 0
            ;;
        *)
            fail "Unknown argument: $arg"
            exit 1
            ;;
    esac
done

# --- Teardown only ---
if [ "$DOWN_ONLY" = true ]; then
    info "Tearing down Docker containers ..."
    docker compose -f "$COMPOSE_FILE" down -v 2>/dev/null || true
    ok "Containers stopped."
    exit 0
fi

# --- Check prerequisites ---
info "Checking prerequisites ..."

check_cmd() {
    if ! command -v "$1" &>/dev/null; then
        fail "Required command not found: $1"
        exit 1
    fi
}

check_cmd docker
check_cmd openssl
check_cmd python3

# Check docker compose (plugin or standalone)
if docker compose version &>/dev/null; then
    COMPOSE="docker compose"
elif command -v docker-compose &>/dev/null; then
    COMPOSE="docker-compose"
else
    fail "Docker Compose not found (tried 'docker compose' and 'docker-compose')"
    exit 1
fi

ok "Prerequisites OK (docker, openssl, python3, compose)"

# --- Generate SSL certificates ---
if [ ! -f "$SCRIPT_DIR/certs/ca.crt" ]; then
    info "Generating SSL certificates ..."
    bash "$SCRIPT_DIR/scripts/generate_certs.sh"
    ok "Certificates generated."
else
    info "SSL certificates already exist, skipping generation."
    info "  (Delete test_harness/certs/ to regenerate)"
fi

# --- Tear down any existing containers ---
info "Cleaning up any existing containers ..."
$COMPOSE -f "$COMPOSE_FILE" down -v 2>/dev/null || true

# --- Start Docker Compose ---
info "Starting PostgreSQL containers ..."
$COMPOSE -f "$COMPOSE_FILE" up -d

# --- Wait for all instances to be healthy ---
info "Waiting for PostgreSQL instances to be ready ..."

wait_for_pg() {
    local container="$1"
    local port="$2"
    local max_wait=60
    local elapsed=0

    while [ $elapsed -lt $max_wait ]; do
        if docker exec "$container" pg_isready -U postgres -q 2>/dev/null; then
            ok "$container (port $port) is ready."
            return 0
        fi
        sleep 1
        elapsed=$((elapsed + 1))
    done
    fail "$container did not become ready within ${max_wait}s"
    return 1
}

wait_for_pg "pgmonkey-plain" 5441
wait_for_pg "pgmonkey-ssl" 5442
wait_for_pg "pgmonkey-clientcert" 5443

# --- Install pgmonkey in dev mode ---
info "Installing pgmonkey in development mode ..."
cd "$PROJECT_ROOT"
pip install -e ".[test]" --quiet 2>&1 | tail -1 || {
    warn "pip install had warnings, continuing anyway ..."
}
ok "pgmonkey installed."

# --- Run tests ---
info "Running integration tests ..."
echo ""

EXIT_CODE=0
python3 "$SCRIPT_DIR/run_tests.py" || EXIT_CODE=$?

echo ""

# --- Teardown ---
if [ "$KEEP_CONTAINERS" = true ]; then
    warn "Containers kept running (--keep). Tear down with: ./run_harness.sh --down"
else
    info "Tearing down Docker containers ..."
    $COMPOSE -f "$COMPOSE_FILE" down -v 2>/dev/null || true
    ok "Containers stopped."
fi

# --- Final status ---
if [ $EXIT_CODE -eq 0 ]; then
    ok "All tests passed! Report: $SCRIPT_DIR/report.md"
else
    fail "Some tests failed. Report: $SCRIPT_DIR/report.md"
fi

exit $EXIT_CODE
