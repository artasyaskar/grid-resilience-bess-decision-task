"""
Adversarial Validation Suite for grid-resilience-bess-decision-task.
Executes variants A through I and records verification results.
"""

import os
import sys
import json
import shutil
import tempfile
import pandas as pd
import numpy as np

# Ensure tests can be imported or executed
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TASK_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
ENV_DATA_DIR = os.path.join(TASK_ROOT, "environment", "data")
TESTS_DIR = os.path.join(TASK_ROOT, "tests")

# Add tests dir to sys.path to run verifier functions directly
sys.path.insert(0, TESTS_DIR)
sys.path.insert(0, os.path.join(TASK_ROOT, "solution"))
import test_outputs

def run_adversarial_variant(variant_name, generate_func):
    """Runs a specific adversarial generator and captures verifier output."""
    safe_name = "".join(c for c in variant_name if c.isalnum() or c == "_")[:12]
    temp_dir = tempfile.mkdtemp(prefix=f"adv_{safe_name}_")
    temp_logs = os.path.join(temp_dir, "logs")
    os.makedirs(temp_logs, exist_ok=True)
    
    # Set environment variables for verifier
    os.environ["OUTPUT_DIR"] = temp_dir
    os.environ["LOGS_DIR"] = temp_logs
    
    try:
        # Generate adversarial attempt
        generate_func(temp_dir)
        
        # Run verifier
        test_outputs.run_verifier()
        
        # Read reward and ctrf
        with open(os.path.join(temp_logs, "reward.json"), "r") as f:
            reward_data = json.load(f)
        with open(os.path.join(temp_logs, "ctrf.json"), "r") as f:
            ctrf_data = json.load(f)
            
        reward = reward_data["reward"]
        summary = ctrf_data["results"]["summary"]
        passed = summary["passed"]
        total = summary["tests"]
        failed_tests = [t["name"] for t in ctrf_data["results"]["tests"] if t["status"] == "failed"]
        
        return {
            "variant": variant_name,
            "reward": reward,
            "passed": passed,
            "total": total,
            "failed_tests": failed_tests
        }
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

# ---------------------------------------------------------------------------
# Generators for each adversarial variant
# ---------------------------------------------------------------------------

def gen_variant_a_naive_timestamp(out_dir):
    """Variant A: Naive local timestamp matching without timezone normalization."""
    summary_data = {
        "recommended_region": "REGION_B_ERCOT_CENTRAL",
        "recommended_technology": "LFP-200-800",
        "power_capacity_mw": 200.0,
        "energy_capacity_mwh": 800.0,
        "storage_duration_hours": 4.0,
        "effective_firm_capacity_mw": 172.50, # Distorted by local-time misalignment
        "annual_avoided_unserved_energy_mwh": 142100.0, # Distorted
        "net_annual_resilience_value_usd": 1245000000.0, # Distorted
        "rejected_regions": [
            {"region_id": "REGION_A_MISO_SOUTH", "rejection_reason": "Lower VOLL monetization ($3,500/MWh)."},
            {"region_id": "REGION_C_CAISO_SP15", "rejection_reason": "180 MW headroom constraint at Redondo Beach."},
            {"region_id": "REGION_D_SPP_WEST", "rejection_reason": "Minimal deficit hours (58 hrs) with negative net value."}
        ],
        "data_integrity_notes": {
            "settlement_records_used": "FINAL",
            "timezone_normalization": "LOCAL" # Failed timezone normalization
        }
    }
    with open(os.path.join(out_dir, "decision_summary.json"), "w") as f:
        json.dump(summary_data, f, indent=2)
    # Shorter memo
    with open(os.path.join(out_dir, "decision_memo.md"), "w") as f:
        f.write("# Executive Decision Memorandum: Utility-Scale BESS Regional Allocation\n\n## 1. Final Investment Recommendation\nRegion B.\n\n## 2. Quantitative Regional Comparison\nTable.\n\n## 3. Storage Technology Selection\nLFP.\n\n## 4. Resilience Valuation\nValue.\n\n## 5. Risk Analysis\nRisks.\n\n## 6. Data Integrity Protocol\nLocal time used.\n")

def gen_variant_b_no_revision_handling(out_dir):
    """Variant B: Retains preliminary INITIAL telemetry records."""
    summary_data = {
        "recommended_region": "REGION_B_ERCOT_CENTRAL",
        "recommended_technology": "LFP-200-800",
        "power_capacity_mw": 200.0,
        "energy_capacity_mwh": 800.0,
        "storage_duration_hours": 4.0,
        "effective_firm_capacity_mw": 189.81,
        "annual_avoided_unserved_energy_mwh": 188968.0,
        "net_annual_resilience_value_usd": 1653136610.6,
        "rejected_regions": [
            {"region_id": "REGION_A_MISO_SOUTH", "rejection_reason": "Lower VOLL monetization ($3,500/MWh)."},
            {"region_id": "REGION_C_CAISO_SP15", "rejection_reason": "180 MW headroom constraint at Redondo Beach."},
            {"region_id": "REGION_D_SPP_WEST", "rejection_reason": "Minimal deficit hours (58 hrs) with negative net value."}
        ],
        "data_integrity_notes": {
            "settlement_records_used": "ALL", # Failed settlement filter
            "timezone_normalization": "UTC"
        }
    }
    with open(os.path.join(out_dir, "decision_summary.json"), "w") as f:
        json.dump(summary_data, f, indent=2)
    with open(os.path.join(out_dir, "decision_memo.md"), "w") as f:
        f.write("# Executive Decision Memorandum: Utility-Scale BESS Regional Allocation\n" + "Word "*500 + "\n## 1. Final Investment Recommendation\n## 2. Quantitative Regional Comparison\n## 3. Storage Technology Selection\n## 4. Resilience Valuation\n## 5. Risk Analysis\n## 6. Data Integrity Protocol\n")

def gen_variant_c_wrong_timezone(out_dir):
    """Variant C: Uses local station time offset (CST/CDT)."""
    summary_data = {
        "recommended_region": "REGION_B_ERCOT_CENTRAL",
        "recommended_technology": "LFP-200-800",
        "power_capacity_mw": 200.0,
        "energy_capacity_mwh": 800.0,
        "storage_duration_hours": 4.0,
        "effective_firm_capacity_mw": 189.81,
        "annual_avoided_unserved_energy_mwh": 188968.0,
        "net_annual_resilience_value_usd": 1653136610.6,
        "rejected_regions": [
            {"region_id": "REGION_A_MISO_SOUTH", "rejection_reason": "Lower VOLL monetization ($3,500/MWh)."},
            {"region_id": "REGION_C_CAISO_SP15", "rejection_reason": "180 MW headroom constraint at Redondo Beach."},
            {"region_id": "REGION_D_SPP_WEST", "rejection_reason": "Minimal deficit hours (58 hrs) with negative net value."}
        ],
        "data_integrity_notes": {
            "settlement_records_used": "FINAL",
            "timezone_normalization": "CDT" # Failed UTC normalization
        }
    }
    with open(os.path.join(out_dir, "decision_summary.json"), "w") as f:
        json.dump(summary_data, f, indent=2)
    with open(os.path.join(out_dir, "decision_memo.md"), "w") as f:
        f.write("# Executive Decision Memorandum: Utility-Scale BESS Regional Allocation\n" + "Word "*500 + "\n## 1. Final Investment Recommendation\n## 2. Quantitative Regional Comparison\n## 3. Storage Technology Selection\n## 4. Resilience Valuation\n## 5. Risk Analysis\n## 6. Data Integrity Protocol\n")

def gen_variant_d_lowest_capex_heuristic(out_dir):
    """Variant D: Minimizes overnight capex, selecting 100 MW / 2-hr LFP."""
    summary_data = {
        "recommended_region": "REGION_B_ERCOT_CENTRAL",
        "recommended_technology": "LFP-100-200",
        "power_capacity_mw": 100.0,
        "energy_capacity_mwh": 200.0,
        "storage_duration_hours": 2.0,
        "effective_firm_capacity_mw": 94.90,
        "annual_avoided_unserved_energy_mwh": 88400.0,
        "net_annual_resilience_value_usd": 782100450.0,
        "rejected_regions": [
            {"region_id": "REGION_A_MISO_SOUTH", "rejection_reason": "Lower VOLL."},
            {"region_id": "REGION_C_CAISO_SP15", "rejection_reason": "180 MW headroom."},
            {"region_id": "REGION_D_SPP_WEST", "rejection_reason": "Negative value."}
        ],
        "data_integrity_notes": {
            "settlement_records_used": "FINAL",
            "timezone_normalization": "UTC"
        }
    }
    with open(os.path.join(out_dir, "decision_summary.json"), "w") as f:
        json.dump(summary_data, f, indent=2)
    with open(os.path.join(out_dir, "decision_memo.md"), "w") as f:
        f.write("# Executive Decision Memorandum: Utility-Scale BESS Regional Allocation\n" + "LFP-100-200 "*200 + "\n## 1. Final Investment Recommendation\n## 2. Quantitative Regional Comparison\n## 3. Storage Technology Selection\n## 4. Resilience Valuation\n## 5. Risk Analysis\n## 6. Data Integrity Protocol\n")

def gen_variant_e_headroom_violation_caiso(out_dir):
    """Variant E: Allocates 200 MW in CAISO, violating 180 MW substation limit."""
    summary_data = {
        "recommended_region": "REGION_C_CAISO_SP15",
        "recommended_technology": "LFP-200-800",
        "power_capacity_mw": 200.0,
        "energy_capacity_mwh": 800.0,
        "storage_duration_hours": 4.0,
        "effective_firm_capacity_mw": 189.81,
        "annual_avoided_unserved_energy_mwh": 188968.0,
        "net_annual_resilience_value_usd": 1653136610.6,
        "rejected_regions": [
            {"region_id": "REGION_A_MISO_SOUTH", "rejection_reason": "Lower VOLL."},
            {"region_id": "REGION_B_ERCOT_CENTRAL", "rejection_reason": "Alternative site."},
            {"region_id": "REGION_D_SPP_WEST", "rejection_reason": "Negative value."}
        ],
        "data_integrity_notes": {
            "settlement_records_used": "FINAL",
            "timezone_normalization": "UTC"
        }
    }
    with open(os.path.join(out_dir, "decision_summary.json"), "w") as f:
        json.dump(summary_data, f, indent=2)
    with open(os.path.join(out_dir, "decision_memo.md"), "w") as f:
        f.write("# Executive Decision Memorandum: Utility-Scale BESS Regional Allocation\n" + "REGION_C_CAISO_SP15 "*200 + "\n## 1. Final Investment Recommendation\n## 2. Quantitative Regional Comparison\n## 3. Storage Technology Selection\n## 4. Resilience Valuation\n## 5. Risk Analysis\n## 6. Data Integrity Protocol\n")

def gen_variant_f_ignore_section_3_5_tiebreaker(out_dir):
    """Variant F: Selects NMC-200-800 based purely on unconstrained financial NPV."""
    summary_data = {
        "recommended_region": "REGION_B_ERCOT_CENTRAL",
        "recommended_technology": "NMC-200-800", # Fails Section 3.5 thermal accreditation
        "power_capacity_mw": 200.0,
        "energy_capacity_mwh": 800.0,
        "storage_duration_hours": 4.0,
        "effective_firm_capacity_mw": 184.39,
        "annual_avoided_unserved_energy_mwh": 188968.0,
        "net_annual_resilience_value_usd": 1687240110.2,
        "rejected_regions": [
            {"region_id": "REGION_A_MISO_SOUTH", "rejection_reason": "Lower VOLL."},
            {"region_id": "REGION_C_CAISO_SP15", "rejection_reason": "180 MW headroom."},
            {"region_id": "REGION_D_SPP_WEST", "rejection_reason": "Negative value."}
        ],
        "data_integrity_notes": {
            "settlement_records_used": "FINAL",
            "timezone_normalization": "UTC"
        }
    }
    with open(os.path.join(out_dir, "decision_summary.json"), "w") as f:
        json.dump(summary_data, f, indent=2)
    with open(os.path.join(out_dir, "decision_memo.md"), "w") as f:
        f.write("# Executive Decision Memorandum: Utility-Scale BESS Regional Allocation\n" + "NMC-200-800 "*200 + "\n## 1. Final Investment Recommendation\n## 2. Quantitative Regional Comparison\n## 3. Storage Technology Selection\n## 4. Resilience Valuation\n## 5. Risk Analysis\n## 6. Data Integrity Protocol\n")

def gen_variant_g_hardcoded_old_answer(out_dir):
    """Variant G: Submits old synthetic numbers from discarded v1 benchmark."""
    summary_data = {
        "recommended_region": "REGION_B_ERCOT_CENTRAL",
        "recommended_technology": "LFP-200-800",
        "power_capacity_mw": 200.0,
        "energy_capacity_mwh": 800.0,
        "storage_duration_hours": 4.0,
        "effective_firm_capacity_mw": 188.0, # Old synthetic number
        "annual_avoided_unserved_energy_mwh": 1312.4, # Old synthetic number
        "net_annual_resilience_value_usd": 13824500.0, # Old synthetic number
        "rejected_regions": [
            {"region_id": "REGION_A_MISO_SOUTH", "rejection_reason": "Zero deficit."},
            {"region_id": "REGION_C_CAISO_SP15", "rejection_reason": "Zero deficit."},
            {"region_id": "REGION_D_SPP_WEST", "rejection_reason": "Zero deficit."}
        ],
        "data_integrity_notes": {
            "settlement_records_used": "FINAL",
            "timezone_normalization": "UTC"
        }
    }
    with open(os.path.join(out_dir, "decision_summary.json"), "w") as f:
        json.dump(summary_data, f, indent=2)
    with open(os.path.join(out_dir, "decision_memo.md"), "w") as f:
        f.write("# Executive Decision Memorandum: Utility-Scale BESS Regional Allocation\n" + "188.0 MW "*200 + "\n## 1. Final Investment Recommendation\n## 2. Quantitative Regional Comparison\n## 3. Storage Technology Selection\n## 4. Resilience Valuation\n## 5. Risk Analysis\n## 6. Data Integrity Protocol\n")

def gen_variant_h_incomplete_output(out_dir):
    """Variant H: Incomplete deliverable (missing memo, truncated JSON)."""
    summary_data = {
        "recommended_region": "REGION_B_ERCOT_CENTRAL"
    }
    with open(os.path.join(out_dir, "decision_summary.json"), "w") as f:
        json.dump(summary_data, f, indent=2)

def gen_variant_i_nop(out_dir):
    """Variant I: NOP (Empty directory, no deliverables written)."""
    pass

def main():
    print("=" * 80)
    print("STARTING ADVERSARIAL VALIDATION SUITE FOR GRID-RESILIENCE-BESS BENCHMARK")
    print("=" * 80)
    
    variants = [
        ("Variant A: Naive Timestamp Matching (Local Time)", gen_variant_a_naive_timestamp),
        ("Variant B: No Revision Filtering (Includes INITIAL)", gen_variant_b_no_revision_handling),
        ("Variant C: Wrong Timezone Normalization (CDT)", gen_variant_c_wrong_timezone),
        ("Variant D: Single-Metric Heuristic (Lowest Capex LFP-100-200)", gen_variant_d_lowest_capex_heuristic),
        ("Variant E: Headroom Violation (Allocating 200MW in CAISO)", gen_variant_e_headroom_violation_caiso),
        ("Variant F: Ignoring Sec 3.5 Tie-Breaker (Selecting NMC-200-800)", gen_variant_f_ignore_section_3_5_tiebreaker),
        ("Variant G: Hardcoded Legacy Synthetic Answer", gen_variant_g_hardcoded_old_answer),
        ("Variant H: Incomplete / Malformed Deliverables", gen_variant_h_incomplete_output),
        ("Variant I: NOP (Null Agent Execution)", gen_variant_i_nop)
    ]
    
    results = []
    for name, gen in variants:
        print(f"\n---> Testing {name}...")
        res = run_adversarial_variant(name, gen)
        results.append(res)
        print(f"     Result: {res['passed']}/{res['total']} tests passed | Reward: {res['reward']:.4f}")
        print(f"     Failed Tests ({len(res['failed_tests'])}): {', '.join(res['failed_tests'][:4])}...")

    # Also test the Oracle (Solution)
    print(f"\n---> Testing Oracle (solution/solve.py)...")
    temp_dir = tempfile.mkdtemp(prefix="oracle_test_")
    temp_logs = os.path.join(temp_dir, "logs")
    os.makedirs(temp_logs, exist_ok=True)
    os.environ["OUTPUT_DIR"] = temp_dir
    os.environ["DATA_DIR"] = ENV_DATA_DIR
    os.environ["LOGS_DIR"] = temp_logs
    
    import solve
    solve.run_solution()
    test_outputs.run_verifier()
    with open(os.path.join(temp_logs, "reward.json"), "r") as f:
        oracle_reward = json.load(f)["reward"]
    with open(os.path.join(temp_logs, "ctrf.json"), "r") as f:
        oracle_ctrf = json.load(f)
    shutil.rmtree(temp_dir, ignore_errors=True)
    
    print("\n" + "=" * 80)
    print("ADVERSARIAL TESTING SUMMARY TABLE")
    print("=" * 80)
    print(f"{'Solver Variant':<60} | {'Tests':<8} | {'Reward':<8}")
    print("-" * 80)
    print(f"{'Oracle (Ground Truth Analytical Solution)':<60} | {oracle_ctrf['results']['summary']['passed']:>2}/{oracle_ctrf['results']['summary']['tests']}    | {oracle_reward:.4f}")
    for r in results:
        print(f"{r['variant']:<60} | {r['passed']:>2}/{r['total']}    | {r['reward']:.4f}")
    print("=" * 80)
    
    # Save results to a json file for documentation
    audit_file = os.path.join(TASK_ROOT, "docs", "adversarial_validation_results.json")
    os.makedirs(os.path.dirname(audit_file), exist_ok=True)
    with open(audit_file, "w") as f:
        json.dump({"oracle": {"reward": oracle_reward, "passed": oracle_ctrf['results']['summary']['passed']}, "variants": results}, f, indent=2)
    print(f"Saved audit results to {audit_file}")

if __name__ == "__main__":
    main()
