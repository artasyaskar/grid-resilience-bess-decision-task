# Input Data Catalog: Regional Grid Resiliency & BESS Allocation

This directory (`/workspace/environment/data/`) contains the empirical datasets, electrical grid topology databases, technical equipment specifications, and regulatory standards required for the regional BESS investment evaluation.

## File Manifest

| Filename | Format | Description |
|---|---|---|
| `eia_hourly_operations_2023.csv` | CSV | 8,760-hour operational records covering demand, renewable production (solar, wind), conventional generation, net tie interchange, and settlement revision status across four candidate balancing authorities. |
| `grid_substations_topology.sqlite` | SQLite3 Database | Relational database containing substation interconnect ratings, transmission tie import limits, generator fleet capacities, and regional N-1 contingency reserve requirements. |
| `noaa_hourly_weather_observations.parquet` | Apache Parquet | High-resolution hourly meteorological observations (ambient dry-bulb temperature, dew point, wind speed, heat index, extreme flags) for representative monitoring stations in each candidate region. |
| `bess_technical_specifications.xlsx` | Excel (.xlsx) | Multi-tab engineering and financial workbook detailing candidate BESS configurations, thermal capacity de-rating curves, auxiliary cooling loads, and financial valuation benchmarks. |
| `regional_reliability_standards.pdf` | PDF Document | Official regulatory directive defining resource adequacy deficit formulas, effective firm capacity standards, lost load valuation parameters, and reporting contracts. |
| `regional_macroeconomic_tariffs.csv` | CSV | Regional economic dataset containing county-level commercial electricity retail tariffs, municipal tax credits, property tax rates, and inflation indices. |

---

## Data Schema Summaries

### 1. `eia_hourly_operations_2023.csv`
- `utc_timestamp`: ISO 8601 UTC timestamp (`YYYY-MM-DDTHH:MM:SSZ`).
- `local_timestamp`: Regional clock time (`YYYY-MM-DD HH:MM:SS`).
- `region_id`: Balancing authority identifier (`REGION_A_MISO_SOUTH`, `REGION_B_ERCOT_CENTRAL`, `REGION_C_CAISO_SP15`, `REGION_D_SPP_WEST`).
- `demand_mw`: Total regional electrical load demand in MW.
- `solar_mw`: Real-time utility-scale solar generation in MW.
- `wind_mw`: Real-time wind generation in MW.
- `hydro_mw`: Hydroelectric generation in MW.
- `net_generation_mw`: Total net electricity generation inside the balancing area in MW.
- `interchange_mw`: Net scheduled interchange across external interconnection ties in MW.
- `curtailed_renewable_mw`: Curtailed renewable generation in MW.
- `status`: Settlement record status (`FINAL` vs `PRELIMINARY`).
- `revision_seq`: Revision sequence number.

### 2. `grid_substations_topology.sqlite`
- **`substation_nodes`**: Substation ID, region, nominal voltage (kV), firm tie-line import capacity (MW), BESS interconnection headroom (MW), and N-1 contingency reserve (MW).
- **`generator_fleet`**: Generating unit ID, region, plant name, fuel type, nameplate capacity (MW), equivalent forced outage rate (EFORd), and high-temperature capacity de-rate coefficient (% per °C above 35°C).
- **`regional_reliability_metrics`**: Regional reliability policies, largest single hazard rating (MW), and unserved energy tolerance thresholds.

### 3. `noaa_hourly_weather_observations.parquet`
- `station_id`: NOAA GHCN station identifier.
- `region_id`: Associated balancing authority region identifier.
- `observation_time_utc`: UTC observation timestamp.
- `temp_celsius`: Ambient dry-bulb temperature in degrees Celsius.
- `dew_point_celsius`: Dew point temperature in degrees Celsius.
- `wind_speed_ms`: Wind speed in meters per second.
- `heat_index_celsius`: Calculated heat index in degrees Celsius.
- `extreme_flag`: Indicator flag for extreme thermal/meteorological events (1 = active, 0 = normal).

### 4. `bess_technical_specifications.xlsx`
- **Sheet `Candidate_Configurations`**: BESS configuration ID, rated power (MW), rated energy (MWh), discharge duration (hours), battery chemistry, cooling system architecture, overnight capex ($), annualized capex ($/year), fixed O&M ($/year), and round-trip efficiency (RTE).
- **Sheet `Thermal_Derating_Curves`**: Chemistry thermal operating limits, ambient temperature threshold (°C), capacity de-rate factor per degree above threshold, and auxiliary cooling parasitic load (%).
- **Sheet `Financial_Valuation_Model`**: Valuation parameters including Value of Lost Load (VoLL, $/MWh), curtailment arbitrage value ($/MWh), and parasitic charging loss cost ($/MWh).

### 5. `regional_reliability_standards.pdf`
- Formal regulatory standard defining equations for net unserved load deficit, effective firm capacity during peak stress hours, net annual resilience value, and required deliverable formats.

### 6. `regional_macroeconomic_tariffs.csv`
- County-level economic indicators, retail commercial rates, municipal incentives, and local tax rates.
