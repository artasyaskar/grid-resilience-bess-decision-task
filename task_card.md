# Task Card: Grid Resilience BESS Allocation Decision

## 1. Task Description
- **Analyst Role**: Senior Grid Planning and Energy Storage Analyst at the Apex Clean Energy Infrastructure Authority.
- **Decision to be Made**: The analyst must evaluate four candidate balancing authority sub-regions (`REGION_A_MISO_SOUTH`, `REGION_B_ERCOT_CENTRAL`, `REGION_C_CAISO_SP15`, `REGION_D_SPP_WEST`) and five candidate utility-scale battery configurations (`LFP-100-200`, `LFP-150-600`, `LFP-200-800`, `NMC-200-800`, `FLOW-100-800`). The analyst must determine exactly **one** candidate region to receive capital deployment and select the single optimal battery configuration that maximizes net annual grid resilience value while eliminating unserved energy under extreme weather stress.
- **Deliverables**:
  1. `output/decision_memo.md`: A formal executive decision memorandum addressed to the Chief Planning Officer with structured headings, comparative quantitative tables, labeled engineering units, and complete rejection rationales for competing alternatives.
  2. `output/decision_summary.json`: A strictly formatted JSON payload reporting the recommended region, recommended technology, power/energy ratings, effective firm capacity, annual avoided unserved energy, net resilience value, rejected regions audit, and data integrity parameters.

---

## 2. Complexity Justification & Design Challenges
The task is engineered around three major analytical challenges and cross-file reconciliation dependencies:

### Challenge 1 (The Crux): Non-Linear Ambient Thermal De-Rating & Regulatory Capacity Accreditation (Section 3.5)
- **Planted in Data/Documents**: Technical specifications (`bess_technical_specifications.xlsx`) provide thermal de-rating coefficients where NMC chemistry de-rates by 1.5%/°C above 35.0°C, whereas LFP with liquid cooling (`LFP-200-800`) de-rates by only 0.8%/°C. Concurrently, NOAA weather observations (`noaa_hourly_weather_observations.parquet`) reveal ambient temperatures in `REGION_B_ERCOT_CENTRAL` at San Antonio KSAT reaching 41.1°C with 598 hours above 35°C during summer scarcity intervals.
- **Correct Analyst Action**: The analyst cross-references hourly temperatures with BESS thermal curves across the top 50 deficit hours to compute Effective Firm Capacity (EFC). In financial modeling, unconstrained NMC yields $1.687B vs LFP's $1.653B (a 2.04% difference, which is $\le 3.0\%$). Under Section 3.5 of `regional_reliability_standards.pdf`, when candidate options are within 3.0%, the planner must select the asset with higher accredited EFC during peak heat stress. LFP delivers 189.81 MW vs NMC's 184.39 MW, making `LFP-200-800` the regulatory and engineering winner.
- **Careless Analyst Action**: A careless model evaluates only unconstrained headline financial return or misses Section 3.5 capacity accreditation rules, incorrectly selecting `NMC-200-800`, or selects a sub-scale 100 MW system that leaves massive deficit unserved.

### Challenge 2: Settlement Finality vs. Real-Time Telemetry Lag & UTC Timezone Normalization
- **Planted in Data/Documents**: In `eia_hourly_operations_2023.csv`, preliminary SCADA telemetry records (`settlement_status == 'INITIAL'`) exist alongside revenue-metered settlement logs (`settlement_status == 'FINAL'`). Preliminary records contain missing or under-reported generation values. Section 2.1 of `regional_reliability_standards.pdf` explicitly mandates that only audited meter reconciliations (`settlement_status == 'FINAL'`) be utilized. Concurrently, operational timestamps must be harmonized with NOAA weather data in continuous Coordinated Universal Time (UTC).
- **Correct Analyst Action**: The analyst filters specifically for `settlement_status == 'FINAL'` (8,760 verified hourly observations) and performs inner join on `utc_timestamp` / `timestamp_utc`.
- **Careless Analyst Action**: A careless model fails to filter for `FINAL` records, processing 8,928 rows containing duplicate telemetry, or performs naive string matching against non-standardized local timestamps without adjusting for daylight saving time, corrupting peak scarcity hours.

### Challenge 3: Physical Interconnection Headroom Bottlenecks & Economic Heuristic Traps
- **Planted in Data/Documents**:
  - `REGION_C_CAISO_SP15` exhibits strong solar duck-curve ramping, but `grid_substations_topology.sqlite` documents that interconnection headroom at Redondo Beach 230kV is strictly capped at 180.0 MW. This legally disqualifies 200 MW systems under Section 4. Sizing down to a compliant 150 MW system yields only $706.59M net resilience value due to lower statutory VOLL ($5,000/MWh).
  - `REGION_A_MISO_SOUTH` has ample 300 MW substation headroom, but statutory VOLL is only $3,500/MWh, yielding $630.88M.
  - `REGION_D_SPP_WEST` experiences only 58 deficit hours in 2023, causing capital amortization to exceed outage savings and resulting in a negative net resilience value (-$9.77M).
- **Correct Analyst Action**: The analyst executes full multi-factor resource adequacy modeling across all regions, discovering that `REGION_B_ERCOT_CENTRAL` combines acute summer scarcity (794 deficit hours), islanded import limits (1,250 MW), full 250 MW substation headroom, and the highest statutory VOLL ($9,000/MWh), yielding an unprecedented $1,653,136,610.60 net resilience value.
- **Careless Analyst Action**: A model commits a fatal error by attempting a 200 MW deployment in CAISO (violating the 180 MW headroom bottleneck) or relies on simplistic regional heuristics.

---

## 3. Analytical Taxonomy & Reasoning Loop
- **Primary Analytical Objectives**:
  1. Multi-regional electric grid resource adequacy and loss-of-load expectation modeling.
  2. Techno-economic valuation, thermal de-rating optimization, and regulatory compliance screening for utility-scale BESS assets.
- **Sequential Reasoning Phases**:
  1. **Explore**: Ingest schemas across EIA-930 operations CSV, SQLite substation topology, NOAA Parquet weather tables, BESS Excel specifications, tariffs CSV, and regulatory PDF standards.
  2. **Hypothesize**: Formulate candidate regional vulnerability profiles (accounting for transmission tie limits, local generation, and extreme heatwaves).
  3. **Analyze**: Filter operations data for `settlement_status == 'FINAL'`, harmonize timestamps to UTC, apply the 5.0% operating reserve margin, calculate hourly deficits, evaluate ambient thermal derating above 35.0°C, and compute accredited EFC.
  4. **Synthesize**: Model 8,760-hour storage dispatch, compute avoided unserved energy, monetize outage reduction via regional VOLL, deduct charging energy costs and annualized capital/O&M expenses, and apply Section 3.5 tie-breaking criteria.
  5. **Recommend**: Deliver unambiguous investment allocation (`REGION_B_ERCOT_CENTRAL` and `LFP-200-800`), document rigorous quantified rejection rationales for all alternatives, and verify data integrity reporting.

---

## 4. Expected Difficulty Range
- **Sweep Target**: Strong frontier models evaluated in zero-shot settings are projected to achieve a mean reward strictly below **0.50** (with no single run exceeding 0.70). Weaker baseline models will score at or below **0.25**.
- **Crux Failure Mechanism**: Models routinely generate analysis scripts that execute naive table merges on local timestamps, fail to filter out unrevised preliminary telemetry (`INITIAL`), violate physical substation headroom limits (e.g. attempting 200 MW build in CAISO), or select NMC battery chemistry based on unconstrained headline returns while ignoring ambient temperature de-rating and the Section 3.5 capacity accreditation tie-breaker. Any of these errors causes immediate failure on key rubric criteria.

---

## 5. Ground-Truth Recommendation & Proof
- **Recommended Region**: `REGION_B_ERCOT_CENTRAL`
- **Recommended Technology**: `LFP-200-800` (200.0 MW / 800.0 MWh, 4-hour duration, liquid cooling)
- **Dynamically Computed Numerical Values (from 2023 Authoritative Data)**:
  - Peak Reserve Margin Deficit: **1,289.4 MW** (August 18, 2023 23:00 UTC, ambient temp 40.0°C).
  - Total Annual Baseline Deficit: **418,291.5 MWh** across 794 deficit hours.
  - Accredited Effective Firm Capacity (Top 50 Hours): **189.81 MW** (at mean top-50 ambient temp 38.6°C, derating factor 0.971 × 0.977 availability).
  - Annual Avoided Unserved Energy: **188,968.0 MWh**.
  - Monetized Avoided Outage Value: 188,968.0 MWh × $9,000/MWh = **$1,700,712,000.00**.
  - Off-Peak Recharging Energy Cost: **$43,284,847.88**.
  - Gross Resilience Value: **$1,657,427,152.12**.
  - Annualized Lifecycle Cost (CRF @ 0.09809 + FOM + VOM): **$4,290,541.52**.
  - **Net Annual Resilience Value**: **$1,653,136,610.60**.

### Proof of Alternative Rejections:
- **`REGION_C_CAISO_SP15`**: Legally disqualified for 200 MW configurations due to 180.0 MW substation headroom limit at Redondo Beach 230kV. Best compliant system (LFP-150-600) yields only **$706.59M** net resilience value due to $5,000/MWh VOLL.
- **`REGION_A_MISO_SOUTH`**: Regional statutory VOLL is $3,500/MWh, generating **$630.88M** net value for LFP-200-800 (over $1.02B lower than ERCOT).
- **`REGION_D_SPP_WEST`**: Only 58 deficit hours occur in 2023. At $4,000/MWh VOLL, avoided outage benefits fail to cover annualized capital costs, resulting in **-$9.77M** net resilience value.
- **`NMC-200-800` in Region B**: While generating $1.687B unconstrained value, it falls within 2.04% of LFP. Under Section 3.5, LFP's superior thermal resilience (189.81 MW EFC vs NMC's 184.39 MW EFC) mandates the selection of `LFP-200-800`.
