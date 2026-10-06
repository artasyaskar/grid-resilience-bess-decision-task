"""
Deterministic Offline Programmatic Verifier for Harbor Benchmark Task: grid-resilience-bess-decision-task
Reads final attempt deliverables strictly from /workspace/output (or $OUTPUT_DIR).
Never references ../output or solution/.
Emits /logs/verifier/reward.json and /logs/verifier/ctrf.json.
"""

import os
import sys
import json
import time

def run_verifier():
    start_time = int(time.time() * 1000)
    
    # 1. Resolve output directory strictly per Harbor guidelines
    # Never resolve relative to tests directory (intake rule)
    if os.environ.get("OUTPUT_DIR"):
        output_dir = os.environ["OUTPUT_DIR"]
    elif os.path.isdir("/workspace/output"):
        output_dir = "/workspace/output"
    elif os.path.isdir("./output"):
        output_dir = os.path.abspath("./output")
    else:
        output_dir = "/workspace/output"

    # 2. Resolve logs directory
    if os.name != "nt" and os.path.isdir("/logs"):
        logs_dir = "/logs/verifier"
        os.makedirs(logs_dir, exist_ok=True)
    elif os.environ.get("LOGS_DIR"):
        logs_dir = os.environ["LOGS_DIR"]
    else:
        logs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "logs_verifier"))
        os.makedirs(logs_dir, exist_ok=True)

    reward_file = os.path.join(logs_dir, "reward.json")
    ctrf_file = os.path.join(logs_dir, "ctrf.json")

    tests_results = []
    
    def record_test(name, passed, message=""):
        tests_results.append({
            "name": name,
            "status": "passed" if passed else "failed",
            "message": message,
            "duration": 1
        })

    # Check 1: Directory accessible
    dir_exists = os.path.isdir(output_dir)
    record_test("test_output_directory_accessible", dir_exists, f"Checked output_dir: {output_dir}")

    # Check 2: decision_summary.json exists
    summary_path = os.path.join(output_dir, "decision_summary.json")
    summary_exists = os.path.isfile(summary_path) and os.path.getsize(summary_path) > 0
    record_test("test_decision_summary_exists", summary_exists, f"File {summary_path} present")

    # Check 3: decision_summary.json parses
    summary_data = None
    if summary_exists:
        try:
            with open(summary_path, "r", encoding="utf-8") as f:
                summary_data = json.load(f)
            record_test("test_decision_summary_valid_json", True, "Successfully parsed JSON")
        except Exception as e:
            record_test("test_decision_summary_valid_json", False, f"JSON parse error: {e}")
    else:
        record_test("test_decision_summary_valid_json", False, "File missing")

    # Check 4: decision_memo.md exists
    memo_path = os.path.join(output_dir, "decision_memo.md")
    memo_exists = os.path.isfile(memo_path) and os.path.getsize(memo_path) > 0
    record_test("test_decision_memo_exists", memo_exists, f"File {memo_path} present")

    # Check 5: decision_memo.md required headings
    memo_text = ""
    if memo_exists:
        try:
            with open(memo_path, "r", encoding="utf-8") as f:
                memo_text = f.read()
            required_headings = [
                "# Executive Decision Memorandum: Utility-Scale BESS Regional Allocation",
                "## 1. Final Investment Recommendation",
                "## 2. Quantitative Regional Comparison & Multi-Factor Trade-Offs",
                "## 3. Storage Technology Selection & Thermal Performance Analysis",
                "## 4. Resilience Valuation & Unserved Energy Mitigation",
                "## 5. Risk Analysis, Sensitivities, and Rejected Alternatives"
            ]
            all_headings_present = all(h in memo_text for h in required_headings)
            record_test("test_decision_memo_required_headings", all_headings_present, "All 6 required section headings verified")
        except Exception as e:
            record_test("test_decision_memo_required_headings", False, f"Read error: {e}")
    else:
        record_test("test_decision_memo_required_headings", False, "Memo missing")

    # Check 6: decision_memo.md no placeholders
    if memo_exists and memo_text:
        placeholders = ["TODO", "TBD", "[Insert", "[TBD]"]
        no_placeholders = not any(p in memo_text for p in placeholders)
        record_test("test_decision_memo_no_placeholders", no_placeholders, "No placeholder markers found")
    else:
        record_test("test_decision_memo_no_placeholders", False, "Memo missing")

    # Check 7: Recommended region token
    if summary_data and isinstance(summary_data, dict):
        reg = summary_data.get("recommended_region")
        is_rec_reg = (reg == "REGION_B_ERCOT_CENTRAL")
        record_test("test_recommended_region_correct", is_rec_reg, f"Region was: {reg}")
    else:
        record_test("test_recommended_region_correct", False, "Data missing")

    # Check 8: Recommended technology token
    if summary_data and isinstance(summary_data, dict):
        tech = summary_data.get("recommended_technology")
        is_rec_tech = (tech == "LFP-200-800")
        record_test("test_recommended_technology_correct", is_rec_tech, f"Technology was: {tech}")
    else:
        record_test("test_recommended_technology_correct", False, "Data missing")

    # Check 9: Capacity specs
    if summary_data and isinstance(summary_data, dict):
        p_cap = summary_data.get("power_capacity_mw")
        e_cap = summary_data.get("energy_capacity_mwh")
        dur = summary_data.get("storage_duration_hours")
        caps_ok = (p_cap in [200, 200.0]) and (e_cap in [800, 800.0]) and (dur in [4, 4.0])
        record_test("test_nominal_capacity_ratings", caps_ok, f"Ratings: P={p_cap}, E={e_cap}, Dur={dur}")
    else:
        record_test("test_nominal_capacity_ratings", False, "Data missing")

    # Check 10: Effective Firm Capacity Range
    if summary_data and isinstance(summary_data, dict):
        efc = summary_data.get("effective_firm_capacity_mw")
        efc_ok = isinstance(efc, (int, float)) and (185.0 <= efc <= 192.0)
        record_test("test_effective_firm_capacity_range", efc_ok, f"EFC was: {efc} MW")
    else:
        record_test("test_effective_firm_capacity_range", False, "Data missing")

    # Check 11: Avoided Unserved Energy Range
    if summary_data and isinstance(summary_data, dict):
        avoided = summary_data.get("annual_avoided_unserved_energy_mwh")
        avoided_ok = isinstance(avoided, (int, float)) and (1300.0 <= avoided <= 1325.0)
        record_test("test_avoided_unserved_energy_range", avoided_ok, f"Avoided: {avoided} MWh")
    else:
        record_test("test_avoided_unserved_energy_range", False, "Data missing")

    # Check 12: Net Annual Resilience Value Range
    if summary_data and isinstance(summary_data, dict):
        net_val = summary_data.get("net_annual_resilience_value_usd")
        val_ok = isinstance(net_val, (int, float)) and (13500000 <= net_val <= 14200000)
        record_test("test_net_annual_resilience_value_range", val_ok, f"Net value: {net_val} USD")
    else:
        record_test("test_net_annual_resilience_value_range", False, "Data missing")

    # Check 13: Rejected Regions Audit
    if summary_data and isinstance(summary_data, dict):
        rej = summary_data.get("rejected_regions", [])
        rej_ok = isinstance(rej, list) and len(rej) == 3
        if rej_ok:
            rej_ids = {r.get("region_id") for r in rej if isinstance(r, dict)}
            expected_rej = {"REGION_A_MISO_SOUTH", "REGION_C_CAISO_SP15", "REGION_D_SPP_WEST"}
            rej_ok = (rej_ids == expected_rej)
        record_test("test_rejected_regions_audit", rej_ok, f"Rejected regions checked: {len(rej)} entries")
    else:
        record_test("test_rejected_regions_audit", False, "Data missing")

    # Check 14: Data Integrity Protocol
    if summary_data and isinstance(summary_data, dict):
        notes = summary_data.get("data_integrity_notes", {})
        settled = notes.get("settlement_records_used") == "FINAL"
        tz = notes.get("timezone_normalization") == "UTC"
        record_test("test_data_integrity_protocol", settled and tz, f"Integrity notes: {notes}")
    else:
        record_test("test_data_integrity_protocol", False, "Data missing")

    stop_time = int(time.time() * 1000)
    passed_count = sum(1 for t in tests_results if t["status"] == "passed")
    failed_count = sum(1 for t in tests_results if t["status"] == "failed")

    # CTRF Output
    ctrf_data = {
        "results": {
            "tool": {
                "name": "grid-resilience-bess-verifier"
            },
            "summary": {
                "tests": len(tests_results),
                "passed": passed_count,
                "failed": failed_count,
                "pending": 0,
                "skipped": 0,
                "other": 0,
                "start": start_time,
                "stop": stop_time
            },
            "tests": tests_results
        }
    }

    with open(ctrf_file, "w", encoding="utf-8") as f:
        json.dump(ctrf_data, f, indent=2)

    # Per Harbor handbook: test_weights.json is [], programmatic tests carry no weight by default
    # reward.json writes float reward (0.0 by construction)
    reward_data = {"reward": 0.0}
    with open(reward_file, "w", encoding="utf-8") as f:
        json.dump(reward_data, f, indent=2)

    print(f"[TESTS] Completed verifier: {passed_count}/{len(tests_results)} checks passed.")
    print(f"[TESTS] Wrote {ctrf_file} and {reward_file}.")

if __name__ == "__main__":
    run_verifier()
