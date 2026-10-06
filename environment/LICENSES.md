# Dataset Provenance & Licensing Information

This benchmark task incorporates real-world empirical grid operations, meteorological observations, and authoritative techno-economic cost projections derived from official federal public sources:

## 1. U.S. Energy Information Administration (EIA)
- **Source Product**: EIA-930 Hourly Electric Grid Monitor Operational Datasets (Calendar Year 2023).
- **Official Access Location**: https://www.eia.gov/electricity/gridmonitor/knownissues/xls/
- **Retrieved Datasets**: Official regional workbooks `Region_TEX.xlsx` (ERCOT), `Region_CAL.xlsx` (CAISO), `Region_MIDW.xlsx` (MISO), and `Region_CENT.xlsx` (SPP).
- **Retrieval Date**: October 2026.
- **Attributes Utilized**: Hourly demand actual (MW), demand forecast (MW), net generation (MW), solar generation (MW), wind generation (MW), thermal generation (MW), total interchange (MW), and settlement status (`FINAL` vs `INITIAL`).
- **Data Filtering & Transformation**: Filtered to 8,760 continuous hourly observations for calendar year 2023. Reconciled UTC and local time stamps. Included preliminary telemetry (`INITIAL`) alongside verified meter settlements (`FINAL`) to evaluate analytical data integrity.
- **Licensing**: Public Domain (United States Government Work under 17 U.S.C. § 105). Free for unrestricted research, benchmark development, redistribution, and commercial evaluation.

## 2. National Oceanic and Atmospheric Administration (NOAA / NCEI)
- **Source Product**: Integrated Surface Database (ISD) Hourly Meteorological Observations (Calendar Year 2023).
- **Official Access Location**: https://www.ncei.noaa.gov/pub/data/noaa/2023/
- **Representative Stations**:
  - `722530-12921` (San Antonio International Airport / KSAT - ERCOT Central)
  - `722310-12916` (New Orleans Louis Armstrong Airport / KMSY - MISO South)
  - `722950-23174` (Los Angeles International Airport / KLAX - CAISO SP15)
  - `723530-13967` (Oklahoma City Will Rogers World Airport / KOKC - SPP West)
- **Retrieval Date**: October 2026.
- **Attributes Utilized**: Dry-bulb ambient air temperature (°C), dew point temperature (°C), wind speed (m/s), and derived heat index (°C).
- **Data Transformation**: Extracted hourly observations synchronized to continuous UTC timestamps and formatted as Apache Parquet.
- **Licensing**: Public Domain (United States Government Work under 17 U.S.C. § 105). Free and unrestricted public use.

## 3. National Renewable Energy Laboratory (NREL)
- **Source Product**: NREL Annual Technology Baseline (ATB) 2023 - Utility-Scale Battery Storage.
- **Official Access Location**: https://atb.nrel.gov/electricity/2023/data / OpenEI OEDI Data Repository
- **Retrieval Date**: October 2026.
- **Attributes Utilized**: Overnight Capital Cost ($/kW, $/kWh), Fixed O&M ($/kW-yr), Variable O&M ($/MWh), Capital Recovery Factor (CRF), calendar degradation rates, and round-trip efficiency across 2-hour, 4-hour, and 8-hour utility-scale configurations.
- **Licensing**: Creative Commons CC0 1.0 Universal / Open Government License.

## 4. Benchmark Grid Infrastructure & Regulatory Standards
- **Components**: `grid_substations_topology.sqlite`, `regional_macroeconomic_tariffs.csv`, and `regional_reliability_standards.pdf`.
- **Purpose**: Relational schema defining regional interconnection headroom, transmission tie limits, statutory Value of Lost Load (VOLL) benchmarks, and regulatory reliability directives (FERC-NERC-BAL-2023-09A).
- **Licensing**: MIT License (Copyright 2026 Benchmark Authors).
