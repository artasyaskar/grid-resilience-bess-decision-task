"""
Ground Truth Computation Script for Harbor Task: grid-resilience-bess-decision-task
Computes exact, deterministic analytical solution directly from shipped data files:
1. environment/data/eia_hourly_operations_2023.csv
2. environment/data/noaa_hourly_weather_observations.parquet
3. environment/data/bess_technical_specifications.xlsx
4. environment/data/grid_substations_topology.sqlite
5. environment/data/regional_macroeconomic_tariffs.csv

Follows all mandated protocols from regional_reliability_standards.pdf:
- settlement_status == 'FINAL'
- UTC timestamp synchronization
- Operating reserve margin = 5.0%
- Ambient temperature derating above 35.0 C
- Capital Recovery Factor based on asset life
"""

import os
import json
import sqlite3
import pandas as pd
import numpy as np

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(BASE_DIR, "environment", "data")

def compute_ground_truth():
    print("=== COMPUTING GROUND TRUTH FROM SHIPPED DATA ===")
    
    # 1. Load EIA Operations and enforce data integrity protocol
    ops_path = os.path.join(DATA_DIR, "eia_hourly_operations_2023.csv")
    df_ops = pd.read_csv(ops_path)
    df_ops_final = df_ops[df_ops["settlement_status"] == "FINAL"].copy()
    print(f"Loaded EIA Operations: {len(df_ops)} total rows, {len(df_ops_final)} FINAL settled rows.")
    
    # 2. Load NOAA Weather Parquet
    weather_path = os.path.join(DATA_DIR, "noaa_hourly_weather_observations.parquet")
    df_weather = pd.read_parquet(weather_path)
    print(f"Loaded NOAA Weather: {len(df_weather)} hourly station observations.")
    
    # Merge on (region_id, utc_timestamp / timestamp_utc)
    df_merged = pd.merge(
        df_ops_final,
        df_weather,
        left_on=["region_id", "utc_timestamp"],
        right_on=["region_id", "timestamp_utc"],
        how="inner"
    )
    print(f"Merged Synchronized Dataset: {len(df_merged)} rows across {df_merged['region_id'].nunique()} regions.")
    
    # 3. Load SQLite Topology
    db_path = os.path.join(DATA_DIR, "grid_substations_topology.sqlite")
    conn = sqlite3.connect(db_path)
    df_regions = pd.read_sql("SELECT * FROM candidate_regions", conn)
    conn.close()
    
    # 4. Load Tariffs
    tariffs_path = os.path.join(DATA_DIR, "regional_macroeconomic_tariffs.csv")
    df_tariffs = pd.read_csv(tariffs_path)
    
    # 5. Load BESS Specs
    bess_path = os.path.join(DATA_DIR, "bess_technical_specifications.xlsx")
    df_configs = pd.read_excel(bess_path, sheet_name="Candidate_Configurations")
    
    orm = 0.05 # 5% operating reserve margin per standard
    
    regional_evaluations = {}
    candidate_ranking = []
    
    for _, reg_row in df_regions.iterrows():
        r_id = reg_row["region_id"]
        ba = reg_row["balancing_authority"]
        import_limit = reg_row["transmission_import_limit_mw"]
        headroom = reg_row["interconnection_headroom_mw"]
        
        t_row = df_tariffs[df_tariffs["region_id"] == r_id].iloc[0]
        voll = t_row["value_of_lost_load_usd_per_mwh"]
        c_charge = t_row["off_peak_charging_energy_tariff_usd_per_mwh"]
        
        df_r = df_merged[df_merged["region_id"] == r_id].sort_values("utc_timestamp").reset_index(drop=True)
        
        # Calculate hourly demand with operating reserve requirement and available supply
        req = df_r["demand_actual_mw"] * (1.0 + orm)
        supp = df_r["net_generation_mw"] + import_limit
        df_r["deficit_mw"] = np.maximum(0.0, req - supp)
        
        total_deficit_mwh = float(df_r["deficit_mw"].sum())
        peak_deficit_mw = float(df_r["deficit_mw"].max())
        deficit_hours = int((df_r["deficit_mw"] > 0).sum())
        
        # Top 50 stress hours for capacity accreditation
        df_r["net_load_mw"] = df_r["demand_actual_mw"] - (df_r["solar_generation_mw"] + df_r["wind_generation_mw"])
        top50 = df_r.sort_values(["deficit_mw", "net_load_mw"], ascending=False).head(50)
        
        config_evals = {}
        
        for _, cfg in df_configs.iterrows():
            cfg_id = cfg["config_id"]
            p_nom = cfg["rated_power_mw"]
            e_nom = cfg["rated_energy_mwh"]
            dur = cfg["duration_hours"]
            rte = cfg["round_trip_efficiency"]
            avail = cfg["base_availability"]
            alpha = cfg["thermal_derating_coeff_pct_per_c"]
            capex_kw = cfg["capex_usd_per_kw"]
            fom_kw = cfg["fixed_om_usd_per_kw_yr"]
            vom_mwh = cfg["variable_om_usd_per_mwh"]
            crf = cfg["capital_recovery_factor"]
            
            # Screening check: Headroom
            if p_nom > headroom:
                config_evals[cfg_id] = {
                    "status": "DISQUALIFIED",
                    "rejection_reason": f"Rated power {p_nom} MW exceeds substation headroom {headroom} MW."
                }
                continue
                
            # EFC accreditation during top 50 stress hours
            top50_temps = top50["ambient_temp_c"].values
            derates = np.minimum(1.0, np.maximum(0.60, 1.0 - (alpha / 100.0) * np.maximum(0.0, top50_temps - 35.0)))
            p_eff_top50 = p_nom * derates * avail
            efc_accredited = float(np.mean(p_eff_top50))
            
            # 8,760-hour dispatch simulation
            soc = e_nom
            avoided_mwh = 0.0
            charging_energy_mwh = 0.0
            
            temps = df_r["ambient_temp_c"].values
            deficits = df_r["deficit_mw"].values
            dt_series = pd.to_datetime(df_r["utc_timestamp"])
            hours = dt_series.dt.hour.values
            
            for t in range(len(df_r)):
                hr = hours[t]
                temp = temps[t]
                defic = deficits[t]
                
                # Hourly derating
                d_t = min(1.0, max(0.60, 1.0 - (alpha / 100.0) * max(0.0, temp - 35.0)))
                p_disp = p_nom * d_t * avail
                
                # Discharge during deficit
                if defic > 0 and soc > 0:
                    p_out = min(defic, p_disp, soc)
                    avoided_mwh += p_out
                    soc -= p_out
                # Recharge during off-peak hours (00:00 - 05:00 UTC)
                elif hr < 6 and soc < e_nom:
                    p_in = min(p_nom, (e_nom - soc) / rte)
                    charging_energy_mwh += p_in
                    soc = min(e_nom, soc + p_in * rte)
            
            # Financial Valuation
            avoided_outage_val = avoided_mwh * voll
            charging_cost = charging_energy_mwh * c_charge
            gross_resilience_val = avoided_outage_val - charging_cost
            
            annual_capex = p_nom * 1000.0 * capex_kw * crf
            annual_fom = p_nom * 1000.0 * fom_kw
            annual_vom = avoided_mwh * vom_mwh
            total_annual_cost = annual_capex + annual_fom + annual_vom
            
            net_annual_val = gross_resilience_val - total_annual_cost
            
            config_evals[cfg_id] = {
                "status": "QUALIFIED",
                "effective_firm_capacity_mw": round(efc_accredited, 2),
                "annual_avoided_unserved_energy_mwh": round(avoided_mwh, 2),
                "gross_annual_resilience_value_usd": round(gross_resilience_val, 2),
                "total_annual_cost_usd": round(total_annual_cost, 2),
                "net_annual_resilience_value_usd": round(net_annual_val, 2)
            }
            
            candidate_ranking.append({
                "region_id": r_id,
                "config_id": cfg_id,
                "status": "QUALIFIED",
                "effective_firm_capacity_mw": round(efc_accredited, 2),
                "annual_avoided_unserved_energy_mwh": round(avoided_mwh, 2),
                "net_annual_resilience_value_usd": round(net_annual_val, 2)
            })
            
        regional_evaluations[r_id] = {
            "balancing_authority": ba,
            "annual_unserved_energy_deficit_mwh": round(total_deficit_mwh, 2),
            "peak_deficit_mw": round(peak_deficit_mw, 2),
            "deficit_hours": deficit_hours,
            "configs": config_evals
        }
    
    # Sort ranking primarily by net_annual_resilience_value_usd
    candidate_ranking.sort(key=lambda x: x["net_annual_resilience_value_usd"], reverse=True)
    
    # Apply Section 3.5 Thermal Reliability & Capacity Accreditation Criterion:
    # If the top two qualified configurations yield Net Annual Resilience Values within 3.0% of each other,
    # select the candidate achieving the higher accredited Effective Firm Capacity (EFC, MW).
    cand_top1 = candidate_ranking[0]
    cand_top2 = candidate_ranking[1]
    
    val1 = cand_top1["net_annual_resilience_value_usd"]
    val2 = cand_top2["net_annual_resilience_value_usd"]
    pct_diff = abs(val1 - val2) / max(val1, val2) * 100.0
    
    if cand_top1["region_id"] == cand_top2["region_id"] and pct_diff <= 3.0:
        if cand_top2["effective_firm_capacity_mw"] > cand_top1["effective_firm_capacity_mw"]:
            print(f"\n[SECTION 3.5 RULE FIRED] Top 2 candidates within {pct_diff:.2f}% (<= 3.0%).")
            print(f"  Selecting {cand_top2['config_id']} due to higher accredited EFC ({cand_top2['effective_firm_capacity_mw']} MW vs {cand_top1['effective_firm_capacity_mw']} MW).")
            best_candidate = cand_top2
        else:
            best_candidate = cand_top1
    else:
        best_candidate = cand_top1
    
    print("\n================== CANDIDATE RANKING TABLE ==================")
    for rank, cand in enumerate(candidate_ranking, 1):
        print(f"Rank {rank:2d}: {cand['region_id']:<24} | {cand['config_id']:<12} | EFC: {cand['effective_firm_capacity_mw']:6.2f} MW | Avoided: {cand['annual_avoided_unserved_energy_mwh']:9.2f} MWh | Net Val: ${cand['net_annual_resilience_value_usd']:,.2f}")
    
    print("\n================== GROUND TRUTH RECOMMENDATION ==================")
    print(f"Recommended Region:     {best_candidate['region_id']}")
    print(f"Recommended Technology: {best_candidate['config_id']}")
    print(f"Effective Firm Cap:     {best_candidate['effective_firm_capacity_mw']} MW")
    print(f"Avoided Unserved Energy:{best_candidate['annual_avoided_unserved_energy_mwh']} MWh")
    print(f"Net Annual Value:       ${best_candidate['net_annual_resilience_value_usd']:,.2f}")
    
    ground_truth = {
        "recommended_region": best_candidate["region_id"],
        "recommended_technology": best_candidate["config_id"],
        "power_capacity_mw": 200.0,
        "energy_capacity_mwh": 800.0,
        "storage_duration_hours": 4.0,
        "effective_firm_capacity_mw": best_candidate["effective_firm_capacity_mw"],
        "annual_avoided_unserved_energy_mwh": best_candidate["annual_avoided_unserved_energy_mwh"],
        "net_annual_resilience_value_usd": best_candidate["net_annual_resilience_value_usd"],
        "regional_evaluations": regional_evaluations,
        "ranking": candidate_ranking
    }
    
    gt_file = os.path.join(BASE_DIR, "scratch", "ground_truth.json")
    with open(gt_file, "w", encoding="utf-8") as f:
        json.dump(ground_truth, f, indent=2)
    print(f"\nWrote ground truth output to {gt_file}")
    
    return ground_truth

if __name__ == "__main__":
    compute_ground_truth()
