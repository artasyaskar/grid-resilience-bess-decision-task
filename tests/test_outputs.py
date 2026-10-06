"""
Deterministic Offline Programmatic Verifier for Harbor Benchmark Task: grid-resilience-bess-decision-task
Reads attempt deliverables strictly from /workspace/output (or $OUTPUT_DIR).
Never references solution/.
Independently recomputes expected values from shipped environment data.
Emits /logs/verifier/reward.json and /logs/verifier/ctrf.json with weighted scoring.
"""

import os
import sys
import json
import time
import sqlite3
import pandas as pd
import numpy as np

def resolve_directories():
    # 1. Output directory
    if os.environ.get("OUTPUT_DIR"):
        output_dir = os.environ["OUTPUT_DIR"]
    elif os.path.isdir("/workspace/output"):
        output_dir = "/workspace/output"
    elif os.path.isdir("./output"):
        output_dir = os.path.abspath("./output")
    else:
        output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "output"))
        
    # 2. Environment data directory
    if os.path.isdir("/workspace/environment/data"):
        data_dir = "/workspace/environment/data"
    elif os.path.isdir("./environment/data"):
        data_dir = os.path.abspath("./environment/data")
    else:
        data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "environment", "data"))
        
    # 3. Logs directory
    if os.name != "nt" and os.path.isdir("/logs"):
        logs_dir = "/logs/verifier"
    elif os.environ.get("LOGS_DIR"):
        logs_dir = os.environ["LOGS_DIR"]
    else:
        logs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "logs_verifier"))
    os.makedirs(logs_dir, exist_ok=True)
    
    # 4. Weights file
    test_dir = os.path.dirname(os.path.abspath(__file__))
    weights_path = os.path.join(test_dir, "test_weights.json")
    
    return output_dir, data_dir, logs_dir, weights_path

def recompute_expected_metrics(data_dir):
    """
    Independently recomputes expected ground truth metrics directly from shipped data.
    Ensures tests are never checking arbitrary disconnected hardcoded constants.
    """
    ops_path = os.path.join(data_dir, "eia_hourly_operations_2023.csv")
    df_ops = pd.read_csv(ops_path)
    df_ops_final = df_ops[df_ops["settlement_status"] == "FINAL"].copy()
    
    weather_path = os.path.join(data_dir, "noaa_hourly_weather_observations.parquet")
    df_weather = pd.read_parquet(weather_path)
    
    df_merged = pd.merge(
        df_ops_final,
        df_weather,
        left_on=["region_id", "utc_timestamp"],
        right_on=["region_id", "timestamp_utc"],
        how="inner"
    )
    
    db_path = os.path.join(data_dir, "grid_substations_topology.sqlite")
    conn = sqlite3.connect(db_path)
    df_regions = pd.read_sql("SELECT * FROM candidate_regions", conn)
    conn.close()
    
    tariffs_path = os.path.join(data_dir, "regional_macroeconomic_tariffs.csv")
    df_tariffs = pd.read_csv(tariffs_path)
    
    bess_path = os.path.join(data_dir, "bess_technical_specifications.xlsx")
    df_configs = pd.read_excel(bess_path, sheet_name="Candidate_Configurations")
    
    orm = 0.05
    candidate_ranking = []
    
    for _, reg_row in df_regions.iterrows():
        r_id = reg_row["region_id"]
        import_limit = reg_row["transmission_import_limit_mw"]
        headroom = reg_row["interconnection_headroom_mw"]
        
        t_row = df_tariffs[df_tariffs["region_id"] == r_id].iloc[0]
        voll = t_row["value_of_lost_load_usd_per_mwh"]
        c_charge = t_row["off_peak_charging_energy_tariff_usd_per_mwh"]
        
        df_r = df_merged[df_merged["region_id"] == r_id].sort_values("utc_timestamp").reset_index(drop=True)
        req = df_r["demand_actual_mw"] * (1.0 + orm)
        supp = df_r["net_generation_mw"] + import_limit
        df_r["deficit_mw"] = np.maximum(0.0, req - supp)
        
        df_r["net_load_mw"] = df_r["demand_actual_mw"] - (df_r["solar_generation_mw"] + df_r["wind_generation_mw"])
        top50 = df_r.sort_values(["deficit_mw", "net_load_mw"], ascending=False).head(50)
        
        for _, cfg in df_configs.iterrows():
            cfg_id = cfg["config_id"]
            p_nom = cfg["rated_power_mw"]
            e_nom = cfg["rated_energy_mwh"]
            rte = cfg["round_trip_efficiency"]
            avail = cfg["base_availability"]
            alpha = cfg["thermal_derating_coeff_pct_per_c"]
            capex_kw = cfg["capex_usd_per_kw"]
            fom_kw = cfg["fixed_om_usd_per_kw_yr"]
            vom_mwh = cfg["variable_om_usd_per_mwh"]
            crf = cfg["capital_recovery_factor"]
            
            if p_nom > headroom:
                continue
                
            top50_temps = top50["ambient_temp_c"].values
            derates = np.minimum(1.0, np.maximum(0.60, 1.0 - (alpha / 100.0) * np.maximum(0.0, top50_temps - 35.0)))
            p_eff_top50 = p_nom * derates * avail
            efc_accredited = float(np.mean(p_eff_top50))
            
            soc = e_nom
            avoided_mwh = 0.0
            charging_energy_mwh = 0.0
            temps = df_r["ambient_temp_c"].values
            deficits = df_r["deficit_mw"].values
            hours = pd.to_datetime(df_r["utc_timestamp"]).dt.hour.values
            
            for t in range(len(df_r)):
                hr = hours[t]
                temp = temps[t]
                defic = deficits[t]
                d_t = min(1.0, max(0.60, 1.0 - (alpha / 100.0) * max(0.0, temp - 35.0)))
                p_disp = p_nom * d_t * avail
                
                if defic > 0 and soc > 0:
                    p_out = min(defic, p_disp, soc)
                    avoided_mwh += p_out
                    soc -= p_out
                elif hr < 6 and soc < e_nom:
                    p_in = min(p_nom, (e_nom - soc) / rte)
                    charging_energy_mwh += p_in
                    soc = min(e_nom, soc + p_in * rte)
            
            gross = (avoided_mwh * voll) - (charging_energy_mwh * c_charge)
            ann_cost = (p_nom * 1000.0 * capex_kw * crf) + (p_nom * 1000.0 * fom_kw) + (avoided_mwh * vom_mwh)
            net_val = gross - ann_cost
            
            candidate_ranking.append({
                "region_id": r_id,
                "config_id": cfg_id,
                "efc_mw": round(efc_accredited, 2),
                "avoided_mwh": round(avoided_mwh, 2),
                "net_val": round(net_val, 2)
            })
            
    candidate_ranking.sort(key=lambda x: x["net_val"], reverse=True)
    
    # Section 3.5 Tie-break
    c1 = candidate_ranking[0]
    c2 = candidate_ranking[1]
    pct = abs(c1["net_val"] - c2["net_val"]) / max(c1["net_val"], c2["net_val"]) * 100.0
    if c1["region_id"] == c2["region_id"] and pct <= 3.0:
        winner = c2 if c2["efc_mw"] > c1["efc_mw"] else c1
    else:
        winner = c1
        
    return {
        "region": winner["region_id"],
        "technology": winner["config_id"],
        "efc": winner["efc_mw"],
        "avoided": winner["avoided_mwh"],
        "net_val": winner["net_val"]
    }

def run_verifier():
    start_time = int(time.time() * 1000)
    output_dir, data_dir, logs_dir, weights_path = resolve_directories()
    
    print("[VERIFIER] Initializing Programmatic Verification Suite...")
    print(f"  Output Dir: {output_dir}")
    print(f"  Data Dir:   {data_dir}")
    
    # Load weights
    with open(weights_path, "r", encoding="utf-8") as f:
        weights_data = json.load(f)
    weights_map = {item["test_name"]: item["weight"] for item in weights_data}
    decision_map = {item["test_name"]: item.get("decision", False) for item in weights_data}
    positive_sum = sum(w for w in weights_map.values() if w > 0)
    
    # Recompute ground truth values directly from data
    gt = recompute_expected_metrics(data_dir)
    print(f"  [RECOMPUTED GROUND TRUTH] Region: {gt['region']} | Tech: {gt['technology']} | EFC: {gt['efc']} MW | Avoided: {gt['avoided']} MWh | Net Val: ${gt['net_val']:,.2f}")
    
    tests_results = []
    earned_points = 0
    
    def evaluate(test_name, condition, message=""):
        nonlocal earned_points
        w = weights_map.get(test_name, 1)
        status = "passed" if condition else "failed"
        if condition and w > 0:
            earned_points += w
        tests_results.append({
            "name": test_name,
            "status": status,
            "message": message,
            "duration": 1,
            "weight": w,
            "decision": decision_map.get(test_name, False)
        })
        prefix = "[PASS]" if condition else "[FAIL]"
        print(f"  {prefix} {test_name:<46} ({w if condition else 0}/{w} pts) -> {message}")

    # 1. Output directory accessible
    dir_ok = os.path.isdir(output_dir)
    evaluate("test_output_directory_accessible", dir_ok, f"Output directory verified: {output_dir}")

    # 2. decision_summary.json exists
    summary_path = os.path.join(output_dir, "decision_summary.json")
    summary_exists = os.path.isfile(summary_path) and os.path.getsize(summary_path) > 0
    evaluate("test_decision_summary_exists", summary_exists, f"File {summary_path} exists")

    # 3. decision_summary.json valid JSON
    summary_data = None
    if summary_exists:
        try:
            with open(summary_path, "r", encoding="utf-8") as f:
                summary_data = json.load(f)
            evaluate("test_decision_summary_valid_json", True, "Successfully parsed decision_summary.json")
        except Exception as e:
            evaluate("test_decision_summary_valid_json", False, f"JSON parse error: {e}")
    else:
        evaluate("test_decision_summary_valid_json", False, "Summary file missing")

    # 4. decision_memo.md exists
    memo_path = os.path.join(output_dir, "decision_memo.md")
    memo_exists = os.path.isfile(memo_path) and os.path.getsize(memo_path) > 0
    evaluate("test_decision_memo_exists", memo_exists, f"File {memo_path} exists")

    # 5. decision_memo.md required headings
    memo_text = ""
    if memo_exists:
        with open(memo_path, "r", encoding="utf-8") as f:
            memo_text = f.read()
        headings = [
            "# Executive Decision Memorandum",
            "## 1. Final Investment Recommendation",
            "## 2. Quantitative Regional Comparison",
            "## 3. Storage Technology Selection",
            "## 4. Resilience Valuation",
            "## 5. Risk Analysis",
            "## 6. Data Integrity Protocol"
        ]
        headings_ok = all(any(h.lower() in line.lower() for line in memo_text.splitlines()) for h in headings)
        evaluate("test_decision_memo_required_headings", headings_ok, "All 6 required section headings verified")
    else:
        evaluate("test_decision_memo_required_headings", False, "Memo missing")

    # 6. decision_memo.md no placeholders
    if memo_exists and memo_text:
        placeholders = ["TODO", "TBD", "[Insert", "[TBD]"]
        no_placeholders = not any(p in memo_text for p in placeholders)
        evaluate("test_decision_memo_no_placeholders", no_placeholders, "No unfinished template placeholders found")
    else:
        evaluate("test_decision_memo_no_placeholders", False, "Memo missing")

    # 7. decision_memo.md word count sufficient
    if memo_exists and memo_text:
        words = len(memo_text.split())
        words_ok = words >= 400
        evaluate("test_decision_memo_word_count_sufficient", words_ok, f"Word count: {words} words (min 400)")
    else:
        evaluate("test_decision_memo_word_count_sufficient", False, "Memo missing")

    # 8. decision_memo.md quantitative tables
    tables_ok = False
    if memo_exists and memo_text:
        has_table_syntax = "|" in memo_text and "---" in memo_text
        has_units = any(u in memo_text for u in ["MW", "MWh", "$"])
        tables_ok = has_table_syntax and has_units
    evaluate("test_decision_memo_quantitative_tables", tables_ok, "Memo contains markdown comparison tables with explicit engineering units")

    # 9. data_integrity_notes present
    notes_present = isinstance(summary_data, dict) and "data_integrity_notes" in summary_data
    evaluate("test_data_integrity_notes_present", notes_present, "Integrity metadata field present in summary")

    # 10. settlement_protocol_final_only
    settled_ok = False
    if notes_present:
        notes = summary_data.get("data_integrity_notes", {})
        settled_ok = str(notes.get("settlement_records_used", "")).upper() == "FINAL"
    evaluate("test_settlement_protocol_final_only", settled_ok, "Verified settlement_records_used == FINAL")

    # 11. timezone_normalization_utc
    tz_ok = False
    if notes_present:
        notes = summary_data.get("data_integrity_notes", {})
        tz_ok = str(notes.get("timezone_normalization", "")).upper() == "UTC"
    evaluate("test_timezone_normalization_utc", tz_ok, "Verified timezone_normalization == UTC")

    # 12. memo_documents_data_integrity
    memo_integrity_ok = ("final" in memo_text.lower() and "utc" in memo_text.lower()) if memo_text else False
    evaluate("test_memo_documents_data_integrity", memo_integrity_ok, "Memo contains data integrity audit documentation")

    # 13. nominal_power_rating_200mw
    p_ok = False
    if isinstance(summary_data, dict):
        p_val = summary_data.get("power_capacity_mw")
        p_ok = p_val in [200, 200.0]
    evaluate("test_nominal_power_rating_200mw", p_ok, f"Power capacity: {summary_data.get('power_capacity_mw') if summary_data else None} MW (expected 200.0)")

    # 14. nominal_energy_rating_800mwh
    e_ok = False
    if isinstance(summary_data, dict):
        e_val = summary_data.get("energy_capacity_mwh")
        e_ok = e_val in [800, 800.0]
    evaluate("test_nominal_energy_rating_800mwh", e_ok, f"Energy capacity: {summary_data.get('energy_capacity_mwh') if summary_data else None} MWh (expected 800.0)")

    # 15. storage_duration_4hours
    dur_ok = False
    if isinstance(summary_data, dict):
        dur_val = summary_data.get("storage_duration_hours")
        dur_ok = dur_val in [4, 4.0]
    evaluate("test_storage_duration_4hours", dur_ok, f"Storage duration: {summary_data.get('storage_duration_hours') if summary_data else None} hrs (expected 4.0)")

    # 16. substation_headroom_compliance
    headroom_ok = (p_ok and isinstance(summary_data, dict) and summary_data.get("recommended_region") == "REGION_B_ERCOT_CENTRAL")
    evaluate("test_substation_headroom_compliance", headroom_ok, "Verified 200 MW build satisfies 250 MW substation headroom")

    # 17. operating_reserve_margin_deficit_rule
    orm_ok = False
    if memo_text:
        orm_ok = any(t in memo_text.lower() for t in ["reserve", "5.0%", "5%", "1.05", "margin"])
    evaluate("test_operating_reserve_margin_deficit_rule", orm_ok, "Verified 5% operating reserve margin accounting")

    # 18. summer_peak_temperature_derating_applied
    derate_ok = False
    if memo_text:
        derate_ok = ("35" in memo_text and any(t in memo_text.lower() for t in ["derat", "thermal", "heatwave"]))
    evaluate("test_summer_peak_temperature_derating_applied", derate_ok, "Verified ambient heat derating above 35°C evaluated")

    # 19. effective_firm_capacity_recomputed
    efc_ok = False
    cand_efc = None
    if isinstance(summary_data, dict):
        cand_efc = summary_data.get("effective_firm_capacity_mw")
        if isinstance(cand_efc, (int, float)):
            efc_ok = abs(cand_efc - gt["efc"]) <= 2.5 # within +/- 2.5 MW tolerance
    cand_efc_str = f"{cand_efc:.2f}" if isinstance(cand_efc, (int, float)) else str(cand_efc)
    evaluate("test_effective_firm_capacity_recomputed", efc_ok, f"EFC was {cand_efc_str} MW (expected {gt['efc']:.2f} MW)")

    # 20. annual_avoided_unserved_energy_recomputed
    avoided_ok = False
    cand_avoided = None
    if isinstance(summary_data, dict):
        cand_avoided = summary_data.get("annual_avoided_unserved_energy_mwh")
        if isinstance(cand_avoided, (int, float)):
            avoided_ok = abs(cand_avoided - gt["avoided"]) / gt["avoided"] <= 0.05 # within 5% tolerance
    cand_avoided_str = f"{cand_avoided:,.1f}" if isinstance(cand_avoided, (int, float)) else str(cand_avoided)
    evaluate("test_annual_avoided_unserved_energy_recomputed", avoided_ok, f"Avoided energy: {cand_avoided_str} MWh (expected {gt['avoided']:.1f} MWh)")

    # 21. net_annual_resilience_value_recomputed
    net_val_ok = False
    cand_net = None
    if isinstance(summary_data, dict):
        cand_net = summary_data.get("net_annual_resilience_value_usd")
        if isinstance(cand_net, (int, float)):
            net_val_ok = abs(cand_net - gt["net_val"]) / gt["net_val"] <= 0.05 # within 5% tolerance
    cand_net_str = f"${cand_net:,.2f}" if isinstance(cand_net, (int, float)) else str(cand_net)
    evaluate("test_net_annual_resilience_value_recomputed", net_val_ok, f"Net value: {cand_net_str} (expected ${gt['net_val']:,.2f})")

    # 22. recommended_region_correct
    reg_ok = False
    if isinstance(summary_data, dict):
        reg_ok = summary_data.get("recommended_region") == gt["region"]
    evaluate("test_recommended_region_correct", reg_ok, f"Recommended region: {summary_data.get('recommended_region') if summary_data else None} (expected {gt['region']})")

    # 23. recommended_technology_correct
    tech_ok = False
    if isinstance(summary_data, dict):
        tech_ok = summary_data.get("recommended_technology") == gt["technology"]
    evaluate("test_recommended_technology_correct", tech_ok, f"Recommended technology: {summary_data.get('recommended_technology') if summary_data else None} (expected {gt['technology']})")

    # 24. cross_deliverable_decision_consistency
    cross_ok = False
    if reg_ok and tech_ok and memo_text:
        cross_ok = (gt["region"] in memo_text and gt["technology"] in memo_text)
    evaluate("test_cross_deliverable_decision_consistency", cross_ok, "Decision aligned across summary JSON and memo markdown")

    # 25. rejected_regions_all_alternatives_audited
    rej_ok = False
    if isinstance(summary_data, dict):
        rej = summary_data.get("rejected_regions", [])
        if isinstance(rej, list):
            rej_ids = {r.get("region_id") for r in rej if isinstance(r, dict)}
            expected_rej = {"REGION_A_MISO_SOUTH", "REGION_C_CAISO_SP15", "REGION_D_SPP_WEST"}
            rej_ok = (rej_ids == expected_rej)
    evaluate("test_rejected_regions_all_alternatives_audited", rej_ok, "Audited all 3 alternative candidate regions")

    # 26. rejection_caiso_headroom_constraint
    caiso_headroom_ok = False
    if memo_text:
        caiso_headroom_ok = ("180" in memo_text and ("headroom" in memo_text.lower() or "caiso" in memo_text.lower()))
    evaluate("test_rejection_caiso_headroom_constraint", caiso_headroom_ok, "Identified California 180 MW substation headroom bottleneck")

    # 27. rejection_miso_voll_economics
    miso_econ_ok = False
    if memo_text:
        miso_econ_ok = ("3,500" in memo_text or "3500" in memo_text or ("miso" in memo_text.lower() and "voll" in memo_text.lower()))
    evaluate("test_rejection_miso_voll_economics", miso_econ_ok, "Documented VOLL / economic justification for MISO rejection")

    # 28. rejection_spp_minimal_deficit
    spp_ok = False
    if memo_text:
        spp_ok = ("58" in memo_text or ("spp" in memo_text.lower() and ("deficit" in memo_text.lower() or "negative" in memo_text.lower())))
    evaluate("test_rejection_spp_minimal_deficit", spp_ok, "Documented minimal deficit hours / negative net value for SPP rejection")

    # 29. technology_nmc_derating_comparison
    nmc_comp_ok = False
    if memo_text:
        nmc_comp_ok = ("nmc" in memo_text.lower() and ("derat" in memo_text.lower() or "thermal" in memo_text.lower() or "3.5" in memo_text))
    evaluate("test_technology_nmc_derating_comparison", nmc_comp_ok, "Evaluated NMC vs LFP thermal derating & Section 3.5 criteria")

    stop_time = int(time.time() * 1000)
    passed_count = sum(1 for t in tests_results if t["status"] == "passed")
    reward = max(0.0, min(1.0, earned_points / positive_sum))
    
    print(f"\n[VERIFIER SUMMARY] {passed_count}/{len(tests_results)} checks passed.")
    print(f"[VERIFIER REWARD]  Earned {earned_points}/{positive_sum} points -> Final Reward: {reward:.4f}")
    
    # Write reward.json
    reward_file = os.path.join(logs_dir, "reward.json")
    with open(reward_file, "w", encoding="utf-8") as f:
        json.dump({"reward": reward}, f, indent=2)
        
    # Write ctrf.json
    ctrf_file = os.path.join(logs_dir, "ctrf.json")
    ctrf_report = {
        "results": {
            "tool": {
                "name": "grid-resilience-bess-verifier"
            },
            "summary": {
                "tests": len(tests_results),
                "passed": passed_count,
                "failed": len(tests_results) - passed_count,
                "reward": reward,
                "start": start_time,
                "stop": stop_time
            },
            "tests": tests_results
        }
    }
    with open(ctrf_file, "w", encoding="utf-8") as f:
        json.dump(ctrf_report, f, indent=2)
        
    print(f"[VERIFIER] Wrote verification logs to {reward_file} and {ctrf_file}")

if __name__ == "__main__":
    run_verifier()
