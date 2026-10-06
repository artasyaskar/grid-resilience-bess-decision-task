"""
Local Rubric Evaluator
Simulates the Harbor rubric judge against an output directory according to rubrics.json.
Validates:
1. NOP attempt scores 0.0
2. Oracle attempt scores 1.0 (100/100)
"""

import os
import sys
import json
import re

def grade_attempt(output_dir, rubrics_file):
    with open(rubrics_file, "r", encoding="utf-8") as f:
        rubrics = json.load(f)

    earned_weights = 0
    positive_weights = 0
    results = []

    memo_file = os.path.join(output_dir, "decision_memo.md")
    summary_file = os.path.join(output_dir, "decision_summary.json")

    memo_text = ""
    if os.path.isfile(memo_file):
        try:
            with open(memo_file, "r", encoding="utf-8") as f:
                memo_text = f.read()
        except:
            pass

    summary_json = None
    if os.path.isfile(summary_file):
        try:
            with open(summary_file, "r", encoding="utf-8") as f:
                summary_json = json.load(f)
        except:
            pass

    for crit in rubrics:
        item = crit["item"]
        weight = crit["weight"]
        text = crit["criterion"]
        cat = crit["category"]
        
        if weight > 0:
            positive_weights += weight

        passed = False

        if item == 1:
            passed = isinstance(summary_json, dict) and summary_json.get("recommended_region") == "REGION_B_ERCOT_CENTRAL"
        elif item == 2:
            passed = isinstance(summary_json, dict) and summary_json.get("recommended_technology") == "LFP-200-800"
        elif item == 3:
            val = summary_json.get("net_annual_resilience_value_usd") if isinstance(summary_json, dict) else None
            passed = isinstance(val, (int, float)) and (13500000 <= val <= 14200000)
        elif item == 4:
            passed = os.path.isfile(memo_file) and os.path.getsize(memo_file) > 0
        elif item == 5:
            passed = isinstance(summary_json, dict) and len(summary_json) > 0
        elif item == 6:
            passed = "# Executive Decision Memorandum: Utility-Scale BESS Regional Allocation" in memo_text
        elif item == 7:
            passed = "## 1. Final Investment Recommendation" in memo_text
        elif item == 8:
            passed = "## 2. Quantitative Regional Comparison & Multi-Factor Trade-Offs" in memo_text
        elif item == 9:
            passed = "## 3. Storage Technology Selection & Thermal Performance Analysis" in memo_text
        elif item == 10:
            passed = "## 4. Resilience Valuation & Unserved Energy Mitigation" in memo_text
        elif item == 11:
            passed = "## 5. Risk Analysis, Sensitivities, and Rejected Alternatives" in memo_text
        elif item == 12:
            val = summary_json.get("power_capacity_mw") if isinstance(summary_json, dict) else None
            passed = val in [200, 200.0]
        elif item == 13:
            val = summary_json.get("energy_capacity_mwh") if isinstance(summary_json, dict) else None
            passed = val in [800, 800.0]
        elif item == 14:
            val = summary_json.get("storage_duration_hours") if isinstance(summary_json, dict) else None
            passed = val in [4, 4.0]
        elif item == 15:
            val = summary_json.get("effective_firm_capacity_mw") if isinstance(summary_json, dict) else None
            passed = isinstance(val, (int, float)) and (185.0 <= val <= 192.0)
        elif item == 16:
            val = summary_json.get("annual_avoided_unserved_energy_mwh") if isinstance(summary_json, dict) else None
            passed = isinstance(val, (int, float)) and (1300.0 <= val <= 1325.0)
        elif item == 17:
            val = summary_json.get("annual_curtailment_utilized_mwh") if isinstance(summary_json, dict) else None
            passed = isinstance(val, (int, float)) and (50000.0 <= val <= 54000.0)
        elif item == 18:
            rej = summary_json.get("rejected_regions") if isinstance(summary_json, dict) else None
            passed = isinstance(rej, list) and len(rej) == 3
        elif item == 19:
            rej = summary_json.get("rejected_regions") if isinstance(summary_json, dict) else []
            r_ids = {r.get("region_id") for r in rej if isinstance(r, dict)}
            passed = r_ids == {"REGION_A_MISO_SOUTH", "REGION_C_CAISO_SP15", "REGION_D_SPP_WEST"}
        elif item == 20:
            notes = summary_json.get("data_integrity_notes") if isinstance(summary_json, dict) else {}
            passed = isinstance(notes, dict) and notes.get("settlement_records_used") == "FINAL"
        elif item == 21:
            notes = summary_json.get("data_integrity_notes") if isinstance(summary_json, dict) else {}
            passed = isinstance(notes, dict) and notes.get("timezone_normalization") == "UTC"
        elif item == 22:
            passed = "REGION_B_ERCOT_CENTRAL" in memo_text and ("unserved" in memo_text.lower() or "deficit" in memo_text.lower()) and "August" in memo_text
        elif item == 23:
            passed = ("40" in memo_text or "41" in memo_text) and "°C" in memo_text and "REGION_B" in memo_text
        elif item == 24:
            passed = "de-rat" in memo_text.lower() or "derat" in memo_text.lower()
        elif item == 25:
            passed = "NMC" in memo_text and ("thermal" in memo_text.lower() or "de-rat" in memo_text.lower() or "35" in memo_text)
        elif item == 26:
            passed = ("100" in memo_text) and ("195" in memo_text or "deficit" in memo_text.lower() or "insufficient" in memo_text.lower())
        elif item == 27:
            passed = "VRFB" in memo_text and ("50" in memo_text or "pumping" in memo_text.lower() or "losses" in memo_text.lower() or "efficiency" in memo_text.lower())
        elif item == 28:
            passed = "REGION_A_MISO_SOUTH" in memo_text and ("firm" in memo_text.lower() or "6,000" in memo_text or "6000" in memo_text or "import" in memo_text.lower())
        elif item == 29:
            passed = "REGION_C_CAISO_SP15" in memo_text and ("battery" in memo_text.lower() or "intertie" in memo_text.lower() or "7,500" in memo_text or "7500" in memo_text)
        elif item == 30:
            passed = "REGION_D_SPP_WEST" in memo_text and ("wind" in memo_text.lower() or "export" in memo_text.lower() or "3,500" in memo_text or "3500" in memo_text)
        elif item == 31:
            # Markdown table with all 4 regions
            passed = all(r in memo_text for r in ["REGION_A", "REGION_B", "REGION_C", "REGION_D"]) and "|" in memo_text
        elif item == 32:
            # Markdown table with all 4 battery configs
            passed = all(c in memo_text for c in ["LFP-100-400", "NMC-100-200", "LFP-200-800", "VRFB-50-500"]) and "|" in memo_text
        elif item == 33:
            passed = "12,500" in memo_text or "12500" in memo_text or "Value of Lost Load" in memo_text or "VoLL" in memo_text
        elif item == 34:
            passed = "MW" in memo_text and "MWh" in memo_text and ("USD" in memo_text or "$" in memo_text)
        elif item == 35:
            passed = len(memo_text) > 0 and not any(p in memo_text for p in ["TODO", "TBD", "[Insert", "[TBD]"])
        elif item == 36: # penalty: raw traces or code dumps
            if memo_text:
                has_corruption = ("Traceback (most recent call last)" in memo_text) or ("<string>" in memo_text and "line " in memo_text)
                if has_corruption:
                    earned_weights += weight # subtracts 5
                    passed = False
                else:
                    passed = True
            else:
                passed = True # Missing file is scored 0 in positive criteria, no double penalty
        elif item == 37: # penalty: fabricated region tokens
            if summary_json and isinstance(summary_json, dict):
                reg = summary_json.get("recommended_region")
                valid_regs = {"REGION_A_MISO_SOUTH", "REGION_B_ERCOT_CENTRAL", "REGION_C_CAISO_SP15", "REGION_D_SPP_WEST"}
                if reg and reg not in valid_regs:
                    earned_weights += weight # subtracts 5
                    passed = False
                else:
                    passed = True
            else:
                passed = True # Missing file is not double penalized

        if weight > 0 and passed:
            earned_weights += weight

        results.append({
            "item": item,
            "weight": weight,
            "category": cat,
            "passed": passed,
            "text": text[:60] + "..."
        })

    reward = earned_weights / positive_weights if positive_weights > 0 else 0.0
    return reward, earned_weights, positive_weights, results

if __name__ == "__main__":
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    rubrics_path = os.path.join(base_dir, "rubrics.json")
    
    # 1. Evaluate Oracle
    oracle_dir = os.path.join(base_dir, "output")
    reward_oracle, earned_o, total_o, _ = grade_attempt(oracle_dir, rubrics_path)
    print(f"ORACLE SCORE: {earned_o}/{total_o} points -> Reward: {reward_oracle:.4f}")
    
    # 2. Evaluate NOP
    empty_dir = os.path.join(base_dir, "temp_nop_dir")
    os.makedirs(empty_dir, exist_ok=True)
    reward_nop, earned_n, total_n, _ = grade_attempt(empty_dir, rubrics_path)
    if os.path.exists(empty_dir):
        os.rmdir(empty_dir)
    print(f"NOP SCORE: {earned_n}/{total_n} points -> Reward: {reward_nop:.4f}")
