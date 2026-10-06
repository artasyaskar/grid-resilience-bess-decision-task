"""
Determinism Verification Script for grid-resilience-bess-decision-task.
Executes the solver 5 consecutive times into clean temporary directories
and checks that output hashes and JSON contents are 100% bitwise identical.
"""

import os
import sys
import json
import hashlib
import tempfile
import shutil

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TASK_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
ENV_DATA_DIR = os.path.join(TASK_ROOT, "environment", "data")
sys.path.insert(0, os.path.join(TASK_ROOT, "solution"))
import solve

def hash_file(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def test_determinism(runs=5):
    print("=" * 70)
    print(f"VERIFYING SOLVER DETERMINISM ACROSS {runs} INDEPENDENT RUNS")
    print("=" * 70)
    
    hashes_json = []
    hashes_memo = []
    
    for i in range(1, runs + 1):
        temp_dir = tempfile.mkdtemp(prefix=f"det_run_{i}_")
        os.environ["OUTPUT_DIR"] = temp_dir
        os.environ["DATA_DIR"] = ENV_DATA_DIR
        
        try:
            solve.run_solution()
            
            p_json = os.path.join(temp_dir, "decision_summary.json")
            p_memo = os.path.join(temp_dir, "decision_memo.md")
            
            h_json = hash_file(p_json)
            h_memo = hash_file(p_memo)
            
            hashes_json.append(h_json)
            hashes_memo.append(h_memo)
            
            print(f"  Run {i}: JSON SHA256 = {h_json[:16]}... | Memo SHA256 = {h_memo[:16]}...")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
            
    all_json_identical = len(set(hashes_json)) == 1
    all_memo_identical = len(set(hashes_memo)) == 1
    
    print("-" * 70)
    print(f"JSON Determinism: {'PASSED (100% Identical)' if all_json_identical else 'FAILED'}")
    print(f"Memo Determinism: {'PASSED (100% Identical)' if all_memo_identical else 'FAILED'}")
    print("=" * 70)
    
    assert all_json_identical and all_memo_identical, "Determinism check failed!"
    print("All runs produced bitwise identical outputs without variance.")

if __name__ == "__main__":
    test_determinism()
