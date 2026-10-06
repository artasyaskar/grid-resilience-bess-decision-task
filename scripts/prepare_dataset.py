"""
Complete Data Preparation Script for Harbor Benchmark Task: grid-resilience-bess-decision-task

Generates 6 authoritative, realistic, cross-referenced energy systems datasets:
1. environment/data/eia_hourly_operations_2023.csv (Spreadsheet/CSV, 35,040+ rows)
2. environment/data/grid_substations_topology.sqlite (Database/SQLite, 3 relational tables)
3. environment/data/noaa_hourly_weather_observations.parquet (Spreadsheet/Parquet, 35,040 rows)
4. environment/data/bess_technical_specifications.xlsx (Spreadsheet/XLSX, 3 technical sheets)
5. environment/data/regional_reliability_standards.pdf (Text/PDF, 6-page formal regulatory document)
6. environment/data/regional_macroeconomic_tariffs.csv (Spreadsheet/CSV, Distractor dataset)
"""

import os
import sqlite3
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(BASE_DIR, "environment", "data")
os.makedirs(DATA_DIR, exist_ok=True)

np.random.seed(42)

print("================================================================================")
print("1. GENERATING eia_hourly_operations_2023.csv...")
print("================================================================================")

# Generate 8,760 hours for 2023 (non-leap year)
start_utc = datetime(2023, 1, 1, 0, 0, 0)
hours_in_year = 8760
utc_datetimes = [start_utc + timedelta(hours=i) for i in range(hours_in_year)]

regions = [
    "REGION_A_MISO_SOUTH",
    "REGION_B_ERCOT_CENTRAL",
    "REGION_C_CAISO_SP15",
    "REGION_D_SPP_WEST"
]

# Timezones & offsets
# Region A, B, D: Central Time (UTC-6 in standard, UTC-5 in daylight saving: March 12 02:00 to Nov 5 02:00)
# Region C: Pacific Time (UTC-8 in standard, UTC-7 in daylight saving)

def get_local_time_and_string(dt_utc, tz_type="central"):
    month, day, hour = dt_utc.month, dt_utc.day, dt_utc.hour
    # Simplified US DST 2023: Starts Mar 12 07:00 UTC (02:00 local standard), Ends Nov 5 06:00 UTC (02:00 local daylight)
    is_dst = False
    if (month > 3 or (month == 3 and day > 12) or (month == 3 and day == 12 and hour >= 7)) and \
       (month < 11 or (month == 11 and day < 5) or (month == 11 and day == 5 and hour < 6)):
        is_dst = True

    if tz_type == "central":
        offset_hours = -5 if is_dst else -6
    else: # pacific
        offset_hours = -7 if is_dst else -8

    local_dt = dt_utc + timedelta(hours=offset_hours)
    return local_dt.strftime("%Y-%m-%d %H:%M:%S")

records_ops = []

for r_idx, region in enumerate(regions):
    tz_type = "pacific" if "CAISO" in region else "central"
    
    for h_idx, dt_utc in enumerate(utc_datetimes):
        d_of_y = dt_utc.timetuple().tm_yday
        hr = dt_utc.hour
        local_str = get_local_time_and_string(dt_utc, tz_type)
        
        # Diurnal and seasonal profiles
        # Summer peak: day 180 to 245 (late June to early Sept)
        summer_factor = np.exp(-((d_of_y - 215) ** 2) / (2 * 35 ** 2))
        winter_factor = np.exp(-((d_of_y - 20) ** 2) / (2 * 25 ** 2))
        
        # Local hour roughly (hr - 5 or hr - 7)
        local_hr = (hr - (5 if tz_type == "central" else 7)) % 24
        diurnal_load = np.sin((local_hr - 6) / 24 * np.pi) ** 2 if 6 <= local_hr <= 23 else 0.1
        
        # Solar profile (daytime 6 to 19 local)
        solar_potential = np.sin((local_hr - 6) / 13 * np.pi) if 6 <= local_hr <= 19 else 0.0
        solar_potential = max(0.0, solar_potential)
        
        # Base numbers per region
        if region == "REGION_A_MISO_SOUTH":
            base_load = 26000 + 10000 * summer_factor + 4000 * winter_factor + 2500 * diurnal_load + np.random.normal(0, 150)
            solar = solar_potential * 1800 * (1 - 0.2 * np.random.rand())
            wind = 1200 + 400 * np.sin(h_idx / 24) + np.random.normal(0, 80)
            hydro = 650 + np.random.normal(0, 20)
            net_gen = base_load - 1200 + np.random.normal(0, 50)
            interchange = base_load - net_gen
            curtailed = 0.0
            demand = base_load
            
        elif region == "REGION_B_ERCOT_CENTRAL":
            base_load = 28000 + 13000 * summer_factor + 3000 * winter_factor + 3800 * diurnal_load + np.random.normal(0, 200)
            solar = solar_potential * 12500 * (1 - 0.15 * np.random.rand())
            wind = 5000 + 3500 * np.cos((h_idx + 12) / 24 * 2 * np.pi) + np.random.normal(0, 250)
            wind = max(800.0, wind)
            hydro = 250 + np.random.normal(0, 10)
            
            # Midday solar curtailment when solar > 10,000 MW and local_hr between 11 and 15
            curtailed = 0.0
            if solar > 9500 and 11 <= local_hr <= 15:
                curtailed = (solar - 9500) * 0.35 + np.random.uniform(20, 80)
                
            net_gen = base_load - 400 + np.random.normal(0, 50)
            interchange = -400.0 # limited export/import
            demand = base_load
            
            # Critical August Heatwave: Days 229, 230, 231 (Aug 17, 18, 19, 2023)
            # Extreme peak demand reached in late afternoon (21:00, 22:00, 23:00 UTC)
            if d_of_y in [229, 230, 231] and hr in [20, 21, 22, 23]:
                if d_of_y == 229: # Aug 17
                    demand = 41200.0 if hr == 22 else (40850.0 if hr == 21 else 39900.0)
                elif d_of_y == 230: # Aug 18 (Peak Day)
                    demand = 41450.0 if hr == 22 else (41100.0 if hr == 21 else 40300.0)
                elif d_of_y == 231: # Aug 19
                    demand = 41100.0 if hr == 22 else (40700.0 if hr == 21 else 39600.0)
                # Coincident collapse of solar as sunset approaches
                solar = 1800.0 if hr == 21 else (380.0 if hr == 22 else 0.0)
                wind = 1750.0 if hr == 22 else 1900.0
                curtailed = 0.0

        elif region == "REGION_C_CAISO_SP15":
            base_load = 16000 + 7500 * summer_factor + 1500 * winter_factor + 2500 * diurnal_load + np.random.normal(0, 150)
            solar = solar_potential * 15500 * (1 - 0.1 * np.random.rand())
            wind = 2500 + 1200 * np.sin(h_idx / 24) + np.random.normal(0, 100)
            hydro = 2800 + np.random.normal(0, 50)
            # Massive duck-curve curtailment in spring/summer midday
            curtailed = 0.0
            if solar > 11000 and 10 <= local_hr <= 15:
                curtailed = (solar - 11000) * 0.55 + np.random.uniform(50, 150)
            net_gen = base_load - 3500 + np.random.normal(0, 80)
            interchange = 3500.0 # massive imports via Pacific Intertie
            demand = base_load

        else: # REGION_D_SPP_WEST
            base_load = 11000 + 5000 * summer_factor + 2500 * winter_factor + 1800 * diurnal_load + np.random.normal(0, 100)
            solar = solar_potential * 2800 * (1 - 0.2 * np.random.rand())
            wind = 8500 + 3500 * np.sin((h_idx + 6) / 24 * 2 * np.pi) + np.random.normal(0, 200)
            hydro = 450 + np.random.normal(0, 15)
            curtailed = 0.0
            if wind > 10500:
                curtailed = (wind - 10500) * 0.4 + np.random.uniform(30, 90)
            net_gen = base_load + 1800 + np.random.normal(0, 60)
            interchange = -1800.0 # net export
            demand = base_load

        rec = {
            "utc_timestamp": dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "local_timestamp": local_str,
            "region_id": region,
            "demand_mw": round(float(demand), 1),
            "solar_mw": round(float(solar), 1),
            "wind_mw": round(float(wind), 1),
            "hydro_mw": round(float(hydro), 1),
            "net_generation_mw": round(float(net_gen), 1),
            "interchange_mw": round(float(interchange), 1),
            "curtailed_renewable_mw": round(float(curtailed), 1),
            "status": "FINAL",
            "revision_seq": 1
        }
        records_ops.append(rec)
        
        # PLANTING TRAP: Preliminary unrevised records for Region B during Aug 17-19
        if region == "REGION_B_ERCOT_CENTRAL" and d_of_y in [229, 230, 231] and hr in [20, 21, 22, 23]:
            # The true record is revision_seq=2, FINAL
            rec["revision_seq"] = 2
            # Now create the preliminary record (revision_seq=1, PRELIMINARY) where SCADA telemetry was undercounting demand
            prelim_rec = rec.copy()
            prelim_rec["status"] = "PRELIMINARY"
            prelim_rec["revision_seq"] = 1
            # Under-reported demand by ~3,500 to 4,000 MW!
            prelim_rec["demand_mw"] = round(float(demand - 3800.0), 1)
            # Append preliminary record BEFORE final record to trap naive `keep='first'` deduplication!
            records_ops.insert(-1, prelim_rec)

df_ops = pd.DataFrame(records_ops)
csv_ops_path = os.path.join(DATA_DIR, "eia_hourly_operations_2023.csv")
df_ops.to_csv(csv_ops_path, index=False)
print(f"-> Generated {csv_ops_path} with {len(df_ops):,} rows.")

print("================================================================================")
print("2. GENERATING grid_substations_topology.sqlite...")
print("================================================================================")

sqlite_path = os.path.join(DATA_DIR, "grid_substations_topology.sqlite")
if os.path.exists(sqlite_path):
    os.remove(sqlite_path)

conn = sqlite3.connect(sqlite_path)
cur = conn.cursor()

# Table 1: substation_nodes
cur.execute("""
CREATE TABLE substation_nodes (
    substation_id TEXT PRIMARY KEY,
    region_id TEXT NOT NULL,
    substation_name TEXT NOT NULL,
    voltage_kv REAL NOT NULL,
    firm_tie_import_capacity_mw REAL NOT NULL,
    bess_interconnection_headroom_mw REAL NOT NULL,
    n1_contingency_reserve_mw REAL NOT NULL
);
""")

substations = [
    ("SUB-A1-GULF", "REGION_A_MISO_SOUTH", "Gulfport 500kV Bulk Switching Station", 500.0, 6000.0, 350.0, 1200.0),
    ("SUB-A2-DELTA", "REGION_A_MISO_SOUTH", "Baton Rouge 345kV Industrial Hub", 345.0, 4500.0, 200.0, 850.0),
    ("SUB-B1-HILL", "REGION_B_ERCOT_CENTRAL", "Austin-San Antonio 345kV Resiliency Node", 345.0, 1250.0, 250.0, 750.0),
    ("SUB-B2-METRO", "REGION_B_ERCOT_CENTRAL", "DFW Metro 345kV Bulk Terminal", 345.0, 1000.0, 150.0, 750.0),
    ("SUB-C1-BASIN", "REGION_C_CAISO_SP15", "Vincent 500kV Major Intertie Substation", 500.0, 7500.0, 500.0, 1500.0),
    ("SUB-C2-COAST", "REGION_C_CAISO_SP15", "San Onofre 230kV Coastal Node", 230.0, 4200.0, 150.0, 900.0),
    ("SUB-D1-PLAINS", "REGION_D_SPP_WEST", "Potter County 345kV Wind Intertie", 345.0, 3500.0, 300.0, 600.0),
    ("SUB-D2-PAN", "REGION_D_SPP_WEST", "Woodward 345kV Transmission Hub", 345.0, 2800.0, 150.0, 500.0)
]
cur.executemany("INSERT INTO substation_nodes VALUES (?, ?, ?, ?, ?, ?, ?)", substations)

# Table 2: generator_fleet
cur.execute("""
CREATE TABLE generator_fleet (
    unit_id TEXT PRIMARY KEY,
    region_id TEXT NOT NULL,
    plant_name TEXT NOT NULL,
    fuel_type TEXT NOT NULL,
    nameplate_capacity_mw REAL NOT NULL,
    firm_derate_eford REAL NOT NULL,
    summer_temp_derate_pct_per_deg_above_35c REAL NOT NULL,
    heat_rate_btu_kwh REAL NOT NULL
);
""")

generators = [
    # Region A (MISO South): Total nominal ~36,000 MW firm
    ("GEN-A-CC1", "REGION_A_MISO_SOUTH", "Grand Gulf Combined Cycle", "CCGT", 18500.0, 0.05, 0.4, 6900.0),
    ("GEN-A-NUC", "REGION_A_MISO_SOUTH", "River Bend Nuclear Station", "Nuclear", 9500.0, 0.02, 0.0, 10200.0),
    ("GEN-A-CT1", "REGION_A_MISO_SOUTH", "Pelican Peaking Station", "OCGT", 8000.0, 0.08, 0.8, 9800.0),
    
    # Region B (ERCOT Central): Total nominal 41,500 MW firm
    # Gas units suffer 1.2% capacity de-rate per deg C above 35 C!
    ("GEN-B-CC1", "REGION_B_ERCOT_CENTRAL", "Colorado River Energy Center", "CCGT", 22000.0, 0.06, 1.2, 6850.0),
    ("GEN-B-NUC", "REGION_B_ERCOT_CENTRAL", "South Texas Nuclear Project", "Nuclear", 8500.0, 0.02, 0.0, 10100.0),
    ("GEN-B-CT1", "REGION_B_ERCOT_CENTRAL", "Brazos Valley Peaking Units", "OCGT", 11000.0, 0.09, 1.2, 10200.0),
    
    # Region C (CAISO SP15): Total nominal 22,000 MW firm + storage fleet
    ("GEN-C-CC1", "REGION_C_CAISO_SP15", "Mountainview Power Station", "CCGT", 14000.0, 0.04, 0.5, 6750.0),
    ("GEN-C-NUC", "REGION_C_CAISO_SP15", "Diablo Canyon Unit 1 & 2", "Nuclear", 4500.0, 0.02, 0.0, 10050.0),
    ("GEN-C-BESS_EXIST", "REGION_C_CAISO_SP15", "Moss Landing & Valley Storage Fleet", "Storage", 4000.0, 0.01, 0.2, 0.0),
    ("GEN-C-CT1", "REGION_C_CAISO_SP15", "Alamitos Peaker Station", "OCGT", 3500.0, 0.07, 0.6, 9600.0),
    
    # Region D (SPP West): Total nominal 16,000 MW firm
    ("GEN-D-CC1", "REGION_D_SPP_WEST", "Holcomb Energy Center", "CCGT", 9500.0, 0.05, 0.5, 7100.0),
    ("GEN-D-COAL", "REGION_D_SPP_WEST", "Tolk Generating Station", "Coal", 4000.0, 0.07, 0.3, 9800.0),
    ("GEN-D-CT1", "REGION_D_SPP_WEST", "Harrington Peaker Fleet", "OCGT", 2500.0, 0.08, 0.7, 10400.0)
]
cur.executemany("INSERT INTO generator_fleet VALUES (?, ?, ?, ?, ?, ?, ?, ?)", generators)

# Table 3: regional_reliability_metrics
cur.execute("""
CREATE TABLE regional_reliability_metrics (
    region_id TEXT PRIMARY KEY,
    contingency_reserve_policy TEXT NOT NULL,
    largest_single_hazard_mw REAL NOT NULL,
    target_unserved_energy_tolerance_mwh REAL NOT NULL,
    voll_standard_usd_per_mwh REAL NOT NULL
);
""")

rel_metrics = [
    ("REGION_A_MISO_SOUTH", "N-1 Transmission & Largest Generation Unit", 1200.0, 50.0, 12500.0),
    ("REGION_B_ERCOT_CENTRAL", "N-1 Single Plant Hazard (STNP Unit trip)", 750.0, 0.0, 12500.0),
    ("REGION_C_CAISO_SP15", "N-1 Intertie Import Loss", 1500.0, 100.0, 12500.0),
    ("REGION_D_SPP_WEST", "N-1 Wind Ramp & Unit Loss", 600.0, 50.0, 12500.0)
]
cur.executemany("INSERT INTO regional_reliability_metrics VALUES (?, ?, ?, ?, ?)", rel_metrics)

conn.commit()
conn.close()
print(f"-> Generated {sqlite_path} with 3 relational tables.")

print("================================================================================")
print("3. GENERATING noaa_hourly_weather_observations.parquet...")
print("================================================================================")

station_map = {
    "REGION_A_MISO_SOUTH": "USW00013963",  # Little Rock / Gulf Inland
    "REGION_B_ERCOT_CENTRAL": "USW00012918", # Houston / Austin / Central TX
    "REGION_C_CAISO_SP15": "USW00023174",  # Los Angeles Basin
    "REGION_D_SPP_WEST": "USW00023061"    # Amarillo Plains
}

weather_records = []

for r_idx, region in enumerate(regions):
    station_id = station_map[region]
    tz_type = "pacific" if "CAISO" in region else "central"
    
    for h_idx, dt_utc in enumerate(utc_datetimes):
        d_of_y = dt_utc.timetuple().tm_yday
        hr = dt_utc.hour
        
        # Local hour approximation
        local_hr = (hr - (5 if tz_type == "central" else 7)) % 24
        
        # Base annual temperature curve
        summer_factor = np.exp(-((d_of_y - 215) ** 2) / (2 * 40 ** 2))
        winter_factor = np.exp(-((d_of_y - 20) ** 2) / (2 * 30 ** 2))
        diurnal_temp = np.sin((local_hr - 9) / 24 * 2 * np.pi)
        
        if region == "REGION_B_ERCOT_CENTRAL":
            base_temp = 16.0 + 19.0 * summer_factor - 8.0 * winter_factor + 5.5 * diurnal_temp + np.random.normal(0, 0.4)
            # CRITICAL AUGUST HEATWAVE (Days 229, 230, 231 - Aug 17, 18, 19)
            if d_of_y in [229, 230, 231]:
                # Afternoon heat peak in local hours 15:00 - 18:00 (20:00 - 23:00 UTC)
                if hr in [20, 21, 22, 23]:
                    if d_of_y == 230 and hr == 22:
                        base_temp = 41.5 # Peak ambient temperature!
                    elif d_of_y == 230 and hr == 21:
                        base_temp = 40.8
                    elif d_of_y == 229 and hr == 22:
                        base_temp = 40.2
                    elif d_of_y == 231 and hr == 22:
                        base_temp = 39.8
                    else:
                        base_temp = 39.1
            dew_point = 20.0 + 4.0 * summer_factor + np.random.normal(0, 0.3)
            wind_speed = 3.5 + 2.0 * np.random.rand()
            extreme_flag = 1 if base_temp >= 38.0 else 0
            
        elif region == "REGION_A_MISO_SOUTH":
            base_temp = 15.0 + 16.0 * summer_factor - 7.0 * winter_factor + 4.5 * diurnal_temp + np.random.normal(0, 0.4)
            dew_point = 19.0 + 3.0 * summer_factor + np.random.normal(0, 0.3)
            wind_speed = 2.8 + 1.8 * np.random.rand()
            extreme_flag = 1 if base_temp >= 38.0 else 0
            
        elif region == "REGION_C_CAISO_SP15":
            # Coastal / Basin: Moderate summer highs, rarely exceeding 33 C
            base_temp = 14.0 + 12.0 * summer_factor - 3.0 * winter_factor + 4.0 * diurnal_temp + np.random.normal(0, 0.3)
            dew_point = 12.0 + 2.0 * summer_factor + np.random.normal(0, 0.3)
            wind_speed = 3.2 + 2.5 * np.random.rand()
            extreme_flag = 0
            
        else: # REGION_D_SPP_WEST
            # High plains: cold winter freezes, moderate summer
            base_temp = 12.0 + 17.0 * summer_factor - 14.0 * winter_factor + 6.0 * diurnal_temp + np.random.normal(0, 0.5)
            dew_point = 8.0 + 4.0 * summer_factor + np.random.normal(0, 0.4)
            wind_speed = 6.5 + 3.0 * np.random.rand()
            extreme_flag = 1 if (base_temp >= 38.0 or base_temp <= -5.0) else 0

        # Heat index approximation
        hi = base_temp + 0.33 * dew_point - 0.7 * wind_speed - 4.0
        
        weather_records.append({
            "station_id": station_id,
            "region_id": region,
            "observation_time_utc": dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "temp_celsius": round(float(base_temp), 2),
            "dew_point_celsius": round(float(dew_point), 2),
            "wind_speed_ms": round(float(wind_speed), 2),
            "heat_index_celsius": round(float(hi), 2),
            "extreme_flag": int(extreme_flag)
        })

df_weather = pd.DataFrame(weather_records)
parquet_weather_path = os.path.join(DATA_DIR, "noaa_hourly_weather_observations.parquet")
df_weather.to_parquet(parquet_weather_path, index=False)
print(f"-> Generated {parquet_weather_path} with {len(df_weather):,} rows.")

print("================================================================================")
print("4. GENERATING bess_technical_specifications.xlsx...")
print("================================================================================")

excel_path = os.path.join(DATA_DIR, "bess_technical_specifications.xlsx")
wb = openpyxl.Workbook()

# Style definitions
header_fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
data_font = Font(name="Calibri", size=11)
bold_font = Font(name="Calibri", size=11, bold=True)
thin_border = Border(
    left=Side(style='thin', color='D9D9D9'),
    right=Side(style='thin', color='D9D9D9'),
    top=Side(style='thin', color='D9D9D9'),
    bottom=Side(style='thin', color='D9D9D9')
)

# Sheet 1: Candidate_Configurations
ws1 = wb.active
ws1.title = "Candidate_Configurations"

headers1 = [
    "config_id", "power_mw", "energy_mwh", "duration_hrs", "chemistry",
    "cooling_system", "overnight_capex_usd", "annualized_capex_usd", "annual_fixed_om_usd",
    "round_trip_efficiency", "warranty_cycles"
]
ws1.append(headers1)

bess_configs = [
    ["LFP-100-400", 100.0, 400.0, 4.0, "LFP", "Forced Air HVAC", 140000000, 1680000, 850000, 0.86, 3500],
    ["NMC-100-200", 100.0, 200.0, 2.0, "NMC", "Standard Air HVAC", 95000000, 1140000, 580000, 0.92, 2000],
    ["LFP-200-800", 200.0, 800.0, 4.0, "LFP", "Industrial Closed-Loop Liquid", 265000000, 3180000, 1473065, 0.85, 4000],
    ["VRFB-50-500", 50.0, 500.0, 10.0, "Flow-VRFB", "Electrolyte Chiller Loops", 210000000, 2520000, 1260000, 0.72, 10000]
]

for row in bess_configs:
    ws1.append(row)

# Sheet 2: Thermal_Derating_Curves
ws2 = wb.create_sheet(title="Thermal_Derating_Curves")
headers2 = [
    "config_id", "chemistry", "threshold_temp_c", "derate_pct_per_deg_above_threshold",
    "max_operating_temp_c", "auxiliary_cooling_load_pct", "derate_notes"
]
ws2.append(headers2)

derate_rows = [
    ["LFP-100-400", "LFP", 35.0, 0.035, 45.0, 0.025, "Standard forced-air cooling derates above 35C ambient"],
    ["NMC-100-200", "NMC", 35.0, 0.070, 42.0, 0.040, "High thermal sensitivity; 35% capacity curtailment at 40C, accelerates degradation"],
    ["LFP-200-800", "LFP", 38.0, 0.015, 48.0, 0.018, "Industrial closed-loop liquid cooling maintains 94% firm capacity at 42C"],
    ["VRFB-50-500", "Flow-VRFB", 40.0, 0.020, 45.0, 0.055, "Auxiliary pumping load escalates rapidly above 35C; low power delivery"]
]

for row in derate_rows:
    ws2.append(row)

# Sheet 3: Financial_Valuation_Model
ws3 = wb.create_sheet(title="Financial_Valuation_Model")
headers3 = ["parameter_key", "parameter_description", "unit", "value", "methodological_notes"]
ws3.append(headers3)

fin_params = [
    ["voll_usd_per_mwh", "Value of Lost Load for avoided unserved energy", "USD/MWh", 12500.0, "Regulatory VOLL standard for critical unserved load"],
    ["curtailment_arbitrage_usd_per_mwh", "Value of absorbed renewable curtailment injected during stress/ramp", "USD/MWh", 45.0, "Wholesale green attribute + peak arbitrage margin"],
    ["rte_loss_cost_usd_per_mwh", "Levelized parasitic charging loss cost", "USD/MWh", 35.0, "Average off-peak wholesale charging cost applied to round-trip losses"],
    ["federal_clean_energy_grant_offset_pct", "IRA Section 48 ITC and federal infrastructure co-funding", "Fraction", 0.70, "Reflected directly in net annualized capex figures"],
    ["carrying_charge_rate", "Fixed capital recovery factor & municipal utility discount rate", "Fraction", 0.04, "Net annualized capital asset amortization rate"],
    ["max_grid_headroom_absorption_factor", "Transmission substation maximum annual curtailment capture ratio", "Fraction", 0.762, "Maximum portion of regional curtailed renewable MWh deliverable through substation tie"]
]

for row in fin_params:
    ws3.append(row)

# Format all sheets
for ws in [ws1, ws2, ws3]:
    for col in ws.columns:
        col_letter = col[0].column_letter
        ws.column_dimensions[col_letter].width = 24
        col[0].fill = header_fill
        col[0].font = header_font
        col[0].alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        for cell in col[1:]:
            cell.font = data_font
            cell.border = thin_border
            if isinstance(cell.value, float):
                cell.number_format = "#,##0.00" if cell.value < 1000 else "#,##0"
            elif isinstance(cell.value, int):
                cell.number_format = "#,##0"

wb.save(excel_path)
print(f"-> Generated {excel_path} with 3 technical sheets.")

print("================================================================================")
print("5. GENERATING regional_reliability_standards.pdf...")
print("================================================================================")

pdf_path = os.path.join(DATA_DIR, "regional_reliability_standards.pdf")

doc = SimpleDocTemplate(
    pdf_path,
    pagesize=letter,
    leftMargin=54,
    rightMargin=54,
    topMargin=54,
    bottomMargin=54
)

styles = getSampleStyleSheet()

title_style = ParagraphStyle(
    'DocTitle',
    parent=styles['Normal'],
    fontName='Helvetica-Bold',
    fontSize=18,
    leading=22,
    textColor=colors.HexColor('#1F497D'),
    alignment=1, # Center
    spaceAfter=12
)

subtitle_style = ParagraphStyle(
    'DocSubtitle',
    parent=styles['Normal'],
    fontName='Helvetica-Bold',
    fontSize=12,
    leading=16,
    textColor=colors.HexColor('#595959'),
    alignment=1,
    spaceAfter=20
)

h1_style = ParagraphStyle(
    'Heading1_Custom',
    parent=styles['Normal'],
    fontName='Helvetica-Bold',
    fontSize=13,
    leading=17,
    textColor=colors.HexColor('#1F497D'),
    spaceBefore=14,
    spaceAfter=6
)

h2_style = ParagraphStyle(
    'Heading2_Custom',
    parent=styles['Normal'],
    fontName='Helvetica-Bold',
    fontSize=11,
    leading=15,
    textColor=colors.HexColor('#2E75B6'),
    spaceBefore=10,
    spaceAfter=4
)

body_style = ParagraphStyle(
    'Body_Custom',
    parent=styles['Normal'],
    fontName='Helvetica',
    fontSize=9.5,
    leading=13.5,
    textColor=colors.HexColor('#262626'),
    spaceAfter=6
)

callout_style = ParagraphStyle(
    'Callout_Custom',
    parent=styles['Normal'],
    fontName='Helvetica-Bold',
    fontSize=9.5,
    leading=13.5,
    textColor=colors.HexColor('#C00000'),
    spaceBefore=4,
    spaceAfter=6
)

story = []

# Title Banner
story.append(Paragraph("APEX REGIONAL CLEAN ENERGY INFRASTRUCTURE DIRECTIVE", title_style))
story.append(Paragraph("Standard R-2023-BESS: Grid Resiliency Sizing, Valuation, and Allocation Mandate", subtitle_style))
story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#1F497D'), spaceBefore=0, spaceAfter=14))

# Section 1
story.append(Paragraph("1. Purpose, Regulatory Authority, and Investment Scope", h1_style))
story.append(Paragraph(
    "Pursuant to the Regional Clean Energy Resiliency Act, this directive establishes the formal analytical framework "
    "for allocating capital expenditure towards utility-scale Battery Energy Storage System (BESS) deployments across "
    "candidate balancing authorities. The objective is to identify exactly one regional interconnection node suffering from the most severe "
    "unserved energy vulnerability under extreme thermal stress, and deploying the optimal battery chemistry and duration configuration "
    "to maximize net annual resiliency value.",
    body_style
))
story.append(Paragraph(
    "Candidate regions under evaluation are: <b>REGION_A_MISO_SOUTH</b>, <b>REGION_B_ERCOT_CENTRAL</b>, "
    "<b>REGION_C_CAISO_SP15</b>, and <b>REGION_D_SPP_WEST</b>. Each region exhibits distinct load profiles, generation mixes, "
    "and meteorological vulnerability characteristics.",
    body_style
))

# Section 2
story.append(Paragraph("2. Methodological Standards for Resource Adequacy & Deficit Accounting", h1_style))
story.append(Paragraph(
    "2.1 Net Load Deficit Definition: For any operational hour <i>t</i>, the unserved energy deficit (<i>Deficit<sub>t</sub></i>, in MW) is defined by:",
    body_style
))
story.append(Paragraph(
    "<b>Deficit<sub>t</sub> = max(0, Demand<sub>t</sub> - [Available_Firm_Gen<sub>t</sub> + Firm_Tie_Imports - N1_Reserve])</b>",
    callout_style
))
story.append(Paragraph(
    "Where Available_Firm_Gen<sub>t</sub> represents the nameplate firm generation fleet de-rated by the unit Equivalent Forced Outage Rate (EFORd) "
    "and adjusted for summer ambient temperature de-rating. For gas-fired combined-cycle and peaking combustion turbines, capacity suffers a "
    "contractual de-rate per degree Celsius above 35°C ambient as specified in the generator fleet database. "
    "Variable renewable generation (Solar and Wind) must be subtracted from gross demand prior to evaluating net firm resource adequacy.",
    body_style
))

# Section 3
story.append(Paragraph("3. Storage Performance, Effective Firm Capacity, and Thermal De-Rating", h1_style))
story.append(Paragraph(
    "Candidate BESS assets operate under real-world thermodynamic constraints. When deploying storage to mitigate grid loss-of-load events, "
    "analysts must not assume nameplate output under extreme ambient conditions. Effective Firm Capacity (EFC, in MW) during any stress hour "
    "is governed by the battery thermal de-rating curve (Table 2 of the Technical Specifications):",
    body_style
))
story.append(Paragraph(
    "<b>EFC<sub>t</sub> = Power_Capacity_MW × [1.0 - (max(0, Ambient_Temp<sub>t</sub> - Threshold_Temp) × Derate_Rate) - Aux_Cooling_Load_Pct]</b>",
    callout_style
))
story.append(Paragraph(
    "Crucially, configurations utilizing standard forced-air HVAC or chemically sensitive chemistries (such as NMC) suffer severe capacity de-rating "
    "and degradation acceleration when ambient temperatures exceed 35°C. In contrast, heavy industrial closed-loop liquid cooling architectures "
    "(such as configuration LFP-200-800) maintain 94% effective capability up to 45°C ambient temperatures.",
    body_style
))

# Section 4
story.append(Paragraph("4. Comprehensive Net Resiliency Valuation Function", h1_style))
story.append(Paragraph(
    "The deterministic economic decision shall be evaluated using the Net Annual Resilience Value ($ USD/year), computed strictly as:",
    body_style
))
story.append(Paragraph(
    "<b>Net_Annual_Resilience_Value = Gross_Resilience_Benefit - Annualized_Capex - Annual_Fixed_OM - Annual_RTE_Loss_Cost</b>",
    h2_style
))
story.append(Paragraph("Where:", body_style))
story.append(Paragraph("• <b>Gross_Resilience_Benefit</b> = (Avoided_Unserved_Energy_MWh × VoLL) + (Curtailed_Renewables_Absorbed_MWh × Curtailment_Value)", body_style))
story.append(Paragraph("• <b>VoLL (Value of Lost Load)</b> = $12,500.00 / MWh", body_style))
story.append(Paragraph("• <b>Curtailment Arbitrage Value</b> = $45.00 / MWh of absorbed renewable curtailment injected during stress hours", body_style))
story.append(Paragraph("• <b>Annual_RTE_Loss_Cost</b> = Curtailed_Renewables_Absorbed_MWh × (1.0 - Round_Trip_Efficiency) × $35.00 / MWh", body_style))
story.append(Paragraph("• <b>Annualized_Capex & Annual_Fixed_OM</b> = Values explicitly enumerated in Candidate_Configurations specification sheet.", body_style))

# Section 5 - Crucial data integrity rule
story.append(Paragraph("5. Data Integrity, Reconciliation, and Provenance Protocols", h1_style))
story.append(Paragraph(
    "<b>Section 5.1 Temporal Harmonization Protocol:</b> All balancing authority time series must be normalized to Coordinated Universal Time (UTC). "
    "Local timestamps are subject to regional Daylight Saving Time (DST) shifts and station clock offsets. A direct join on local clock timestamps without UTC alignment "
    "will mismatch solar production profiles against ambient thermal peaks by 5 to 6 hours, invalidating resource adequacy findings.",
    body_style
))
story.append(Paragraph(
    "<b>Section 5.2 Settlement Finality Rule:</b> Preliminary telemetry records (status = 'PRELIMINARY') generated by real-time supervisory control "
    "and data acquisition (SCADA) systems frequently omit delayed metering feeds during major contingency events. Analysts are strictly instructed to "
    "filter for settled records (status = 'FINAL', revision_seq = 2) for all deficit sizing and investment determinations.",
    callout_style
))

# Section 6 - Required Deliverables
story.append(Paragraph("6. Required Reporting Contract & Deliverables", h1_style))
story.append(Paragraph(
    "The analysis must produce exactly two deliverables written to the designated output directory: "
    "<b>output/decision_memo.md</b> (a formal Executive Decision Memorandum formatted in Markdown for the Chief Planning Officer) and "
    "<b>output/decision_summary.json</b> (a structured machine-readable payload containing exact numerical determinations). "
    "Deliverables must detail the recommended region, recommended technology configuration, avoided unserved energy (MWh), "
    "effective firm capacity (MW), utilized curtailed renewables (MWh), and net annual resilience value ($ USD).",
    body_style
))

doc.build(story)
print(f"-> Generated {pdf_path} (Formal Regulatory Standards PDF).")

print("================================================================================")
print("6. GENERATING regional_macroeconomic_tariffs.csv (DISTRACTOR)...")
print("================================================================================")

distractor_records = []
counties = [
    ("REGION_A_MISO_SOUTH", "East Baton Rouge", "LA", 0.098, 1250, 0.045, 1.02),
    ("REGION_A_MISO_SOUTH", "Harrison County", "MS", 0.104, 980, 0.042, 1.01),
    ("REGION_B_ERCOT_CENTRAL", "Travis County", "TX", 0.112, 2100, 0.052, 1.05),
    ("REGION_B_ERCOT_CENTRAL", "Bexar County", "TX", 0.108, 1850, 0.048, 1.04),
    ("REGION_B_ERCOT_CENTRAL", "Harris County", "TX", 0.115, 2400, 0.055, 1.06),
    ("REGION_C_CAISO_SP15", "Los Angeles County", "CA", 0.198, 3200, 0.075, 1.08),
    ("REGION_C_CAISO_SP15", "San Diego County", "CA", 0.215, 3450, 0.082, 1.09),
    ("REGION_D_SPP_WEST", "Potter County", "TX", 0.089, 850, 0.038, 1.01),
    ("REGION_D_SPP_WEST", "Ford County", "KS", 0.092, 790, 0.039, 1.00)
]

for reg, cty, st, tariff, sub_incentive, tax_rate, infl in counties:
    distractor_records.append({
        "region_id": reg,
        "county_name": cty,
        "state_code": st,
        "commercial_retail_tariff_usd_kwh": tariff,
        "municipal_job_tax_credit_usd_per_job": sub_incentive,
        "local_property_tax_rate": tax_rate,
        "regional_inflation_index_2023": infl
    })

df_distractor = pd.DataFrame(distractor_records)
distractor_path = os.path.join(DATA_DIR, "regional_macroeconomic_tariffs.csv")
df_distractor.to_csv(distractor_path, index=False)
print(f"-> Generated {distractor_path} (Distractor Dataset).")

print("================================================================================")
print("DATASET PREPARATION COMPLETED SUCCESSFULLY!")
print("================================================================================")
