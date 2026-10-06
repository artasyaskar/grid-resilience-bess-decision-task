#!/usr/bin/env bash
set -e

echo "[SOLVE.SH] Executing Reference Solution..."

if [ -f "/solution/solve.py" ]; then
    python3 /solution/solve.py
elif [ -f "/workspace/solution/solve.py" ]; then
    python3 /workspace/solution/solve.py
elif [ -f "./solve.py" ]; then
    python3 ./solve.py
else
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    python3 "${SCRIPT_DIR}/solve.py"
fi

echo "[SOLVE.SH] Reference Solution Completed."
