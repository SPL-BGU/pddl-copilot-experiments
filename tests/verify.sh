#!/usr/bin/env bash
# verify.sh — Run the scoring-audit test suite.
# Mirrors ../pddl-copilot/plugins/*/tests/verify.sh: shell entry point, Python
# assertions. No pytest dependency.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_DIR="$REPO_ROOT/.venv"

GREEN='\033[0;32m'; RED='\033[0;31m'; NC='\033[0m'
FAILURES=0

if [ -f "$VENV_DIR/bin/activate" ]; then
    # shellcheck disable=SC1091
    source "$VENV_DIR/bin/activate"
fi

PYTHON="${PYTHON:-python3}"

echo "Scoring-audit test suite"
echo "Repo: $REPO_ROOT"
echo ""

run_test() {
    local file="$1"
    echo "-- $file --"
    if "$PYTHON" "$SCRIPT_DIR/$file"; then
        echo -e "${GREEN}PASS${NC} $file"
    else
        echo -e "${RED}FAIL${NC} $file"
        FAILURES=$((FAILURES + 1))
    fi
    echo ""
}

run_test test_scoring.py
run_test test_check_success.py
run_test test_fixtures.py

if [ "$FAILURES" -gt 0 ]; then
    echo -e "${RED}$FAILURES test file(s) failed${NC}"
    exit 1
fi
echo -e "${GREEN}All test files passed${NC}"
