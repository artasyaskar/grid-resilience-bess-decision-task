#!/usr/bin/env python3
"""
Automated Packager for Harbor Benchmark Task: grid-resilience-bess-decision-task
Creates grid-resilience-bess-decision-task.zip strictly packaging required files
while preventing accidental exclusions of test scripts or inclusion of attempt outputs.
"""

import os
import sys
import zipfile

def package_task():
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    zip_name = "grid-resilience-bess-decision-task.zip"
    zip_path = os.path.join(root_dir, zip_name)
    
    print(f"[*] Packaging task from root: {root_dir}")
    
    # Exact prefixes/patterns to exclude
    EXCLUDE_DIRS = {
        ".git",
        ".github",
        ".gemini",
        ".agents",
        "output",
        "jobs",
        "logs",
        "logs_verifier",
        "scratch",
        "coldchain-harbor-task",
        "__pycache__",
    }
    
    EXCLUDE_EXTS = {
        ".pyc",
        ".pyo",
        ".zip",
        ".DS_Store"
    }
    
    EXCLUDE_EXACT_FILES = {
        "grid-resilience-bess-decision-task.zip"
    }

    files_to_add = []
    
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Compute relative path from root
        rel_dir = os.path.relpath(dirpath, root_dir).replace("\\", "/")
        
        # Filter out directories in-place to prevent descending into them
        dirnames[:] = [
            d for d in dirnames
            if d not in EXCLUDE_DIRS and not d.startswith(".git")
        ]
        
        # Check if current directory path starts with any excluded directory
        parts = rel_dir.split("/")
        if any(p in EXCLUDE_DIRS for p in parts if p != "."):
            continue
            
        for f in sorted(filenames):
            if f in EXCLUDE_EXACT_FILES:
                continue
            if any(f.endswith(ext) for ext in EXCLUDE_EXTS):
                continue
                
            rel_file = os.path.normpath(os.path.join(rel_dir, f)).replace("\\", "/")
            if rel_file.startswith("./"):
                rel_file = rel_file[2:]
                
            abs_file = os.path.join(dirpath, f)
            files_to_add.append((abs_file, rel_file))

    print(f"[*] Found {len(files_to_add)} files to package.")
    
    # Create zip file
    if os.path.exists(zip_path):
        os.remove(zip_path)
        
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for abs_file, rel_file in files_to_add:
            zf.write(abs_file, arcname=rel_file)
            print(f"  + {rel_file}")
            
    # Verify contents of zip file
    print(f"\n[*] Verifying contents of {zip_name}...")
    with zipfile.ZipFile(zip_path, "r") as zf:
        namelist = set(zf.namelist())
        
    critical_files = [
        "task.toml",
        "instruction.md",
        "rubrics.json",
        "environment/Dockerfile",
        "environment/data/eia_hourly_operations_2023.csv",
        "environment/data/noaa_hourly_weather_observations.parquet",
        "environment/data/bess_technical_specifications.xlsx",
        "environment/data/grid_substations_topology.sqlite",
        "environment/data/regional_macroeconomic_tariffs.csv",
        "environment/data/regional_reliability_standards.pdf",
        "solution/solve.sh",
        "solution/solve.py",
        "tests/test.sh",
        "tests/test_outputs.py",
        "tests/test_weights.json",
    ]
    
    missing = [cf for cf in critical_files if cf not in namelist]
    if missing:
        print(f"[!] ERROR: Missing critical files in zip: {missing}")
        sys.exit(1)
        
    # Check that forbidden files are absent
    forbidden = [f for f in namelist if f.startswith("output/") or f.startswith(".git/")]
    if forbidden:
        print(f"[!] ERROR: Forbidden files included in zip: {forbidden}")
        sys.exit(1)
        
    zip_size_mb = os.path.getsize(zip_path) / (1024 * 1024)
    print(f"\n[SUCCESS] '{zip_name}' created successfully ({zip_size_mb:.2f} MB)!")
    print(f"  Total files: {len(namelist)}")
    print(f"  Verified critical files: {len(critical_files)}/{len(critical_files)} present.")
    print(f"  'tests/test_outputs.py' confirmed present at arcname: 'tests/test_outputs.py'")

if __name__ == "__main__":
    package_task()
