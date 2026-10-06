# Input Data Catalog: Regional Grid Resiliency & BESS Allocation

This directory (`/workspace/environment/data/`) contains the empirical datasets, electrical grid topology database, technical equipment specifications, and regulatory standards required for the regional BESS investment evaluation.

## File Manifest

| Filename | Format | Size | Description |
|---|---|---|---|
| `eia_hourly_operations_2023.csv` | CSV | ~4.1 MB | 35,712 operational records covering hourly demand, generation by fuel type, interchange, and settlement revision status across four candidate balancing authorities. |
| `grid_substations_topology.sqlite` | SQLite3 Database | ~28 KB | Relational database containing substation interconnect ratings, transmission tie import limits, and candidate region topology. |
| `noaa_hourly_weather_observations.parquet` | Apache Parquet | ~218 KB | High-resolution hourly meteorological observations (ambient dry-bulb temperature, dew point, wind speed, heat index) for representative monitoring stations in each candidate region. |
| `bess_technical_specifications.xlsx` | Excel (.xlsx) | ~18 KB | Multi-tab engineering and financial workbook detailing candidate BESS configurations, thermal capacity de-rating curves, and NREL ATB 2023 cost baselines. |
| `regional_reliability_standards.pdf` | PDF Document | ~6 KB | Official regulatory directive defining resource adequacy deficit formulas, effective firm capacity standards, lost load valuation parameters, and Section 3.5 tie-breaker rules. |
| `regional_macroeconomic_tariffs.csv` | CSV | ~1 KB | Regional economic dataset containing balancing authority statutory Value of Lost Load (VOLL), off-peak charging energy tariffs, and capital recovery factors. |

---

## Data Schema Summaries

### 1. `eia_hourly_operations_2023.csv`
- `region_id`: Balancing authority identifier (`REGION_A_MISO_SOUTH`, `REGION_B_ERCOT_CENTRAL`, `REGION_C_CAISO_SP15`, `REGION_D_SPP_WEST`).
- `utc_timestamp`: Continuous ISO 8601 UTC timestamp (`YYYY-MM-DDTHH:MM:SSZ`).
- `local_timestamp`: Regional wall-clock time (`YYYY-MM-DD HH:MM:SS`).
- `demand_forecast_mw`: Day-ahead load forecast in MW.
- `demand_actual_mw`: Real-time metered demand in MW.
- `net_generation_mw`: Total net electricity generation inside the balancing authority in MW.
- `total_interchange_mw`: Net scheduled interchange across external interconnection ties in MW.
- `solar_generation_mw`: Utility-scale solar generation in MW.
- `wind_generation_mw`: Utility-scale wind generation in MW.
- `thermal_generation_mw`: Combined thermal (gas, coal, nuclear) generation in MW.
- `settlement_status`: Settlement verification status (`FINAL` for audited meter settlements, `INITIAL` for preliminary telemetry).

### 2. `grid_substations_topology.sqlite`
- **`candidate_regions`**: Regional identifiers, balancing authority name, transmission import limit (MW), and interconnection headroom (MW).
- **`candidate_substations`**: Substation ID, region, nominal bus voltage (kV), maximum injection capacity (MW), and candidate bus name.
- **`transmission_corridor_limits`**: Regional transmission corridors, emergency thermal ratings (MVA), and N-1 contingency reserve requirements (MW).

### 3. `noaa_hourly_weather_observations.parquet`
- `station_id`: NOAA ISD station identifier (e.g., `722530-12921` for KSAT).
- `region_id`: Associated balancing authority region identifier.
- `station_name`: Weather station airport name.
- `timestamp_utc`: UTC observation timestamp.
- `ambient_temp_c`: Dry-bulb ambient air temperature in degrees Celsius.
- `dew_point_c`: Dew point temperature in degrees Celsius.
- `wind_speed_mps`: Wind speed in meters per second.
- `heat_index_c`: Derived heat index in degrees Celsius.
- `quality_flag`: Meteorological data quality indicator (`V` = verified).

### 4. `bess_technical_specifications.xlsx`
- **Sheet `Candidate_Configurations`**: Configuration ID (`LFP-100-200`, `LFP-150-600`, `LFP-200-800`, `NMC-200-800`, `FLOW-100-800`), chemistry, rated power (MW), rated energy (MWh), duration (hours), round-trip efficiency, base availability, thermal derating coefficient (%/°C above 35°C), calendar degradation (%/yr), capex ($/kW), fixed O&M ($/kW-yr), variable O&M ($/MWh), and capital recovery factor (CRF).
- **Sheet `NREL_ATB_2023_Baseline`**: NREL ATB 2023 benchmark cost projections for utility-scale battery systems.

### 5. `regional_reliability_standards.pdf`
- Formal regulatory directive (FERC-NERC-BAL-2023-09A) defining equations for hourly supply deficit with 5.0% operating reserve margin, temperature derating and effective firm capacity (EFC) during top 50 deficit hours, net annual resilience value, and Section 3.5 capacity accreditation tie-breaker.

### 6. `regional_macroeconomic_tariffs.csv`
- Balancing authority statutory Value of Lost Load ($/MWh), off-peak charging energy tariffs ($/MWh), and regional capital recovery factors.
