#!/usr/bin/env bash
set -e

echo "[TEST.SH] Starting Programmatic Task Verifier..."

mkdir -p /logs/verifier

if [ -f "/workspace/tests/test_outputs.py" ]; then
    python3 /workspace/tests/test_outputs.py
elif [ -f "./tests/test_outputs.py" ]; then
    python3 ./tests/test_outputs.py
else
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    python3 "${SCRIPT_DIR}/test_outputs.py"
fi

echo "[TEST.SH] Verifier Execution Complete."
