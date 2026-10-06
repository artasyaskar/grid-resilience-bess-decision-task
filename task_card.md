# Task Card: Grid Resilience BESS Allocation Decision

## 1. Task Description
- **Analyst Role**: Senior Grid Planning and Energy Storage Analyst at the Apex Clean Energy Infrastructure Authority.
- **Decision to be Made**: The analyst must evaluate four candidate balancing authority sub-regions (`REGION_A_MISO_SOUTH`, `REGION_B_ERCOT_CENTRAL`, `REGION_C_CAISO_SP15`, `REGION_D_SPP_WEST`) and four candidate utility-scale battery configurations (`LFP-100-400`, `NMC-100-200`, `LFP-200-800`, `VRFB-50-500`). The analyst must determine exactly **one** candidate region to receive capital deployment and select the single optimal battery configuration that maximizes net annual grid resilience value while eliminating unserved energy under extreme weather stress.
- **Deliverables**:
  1. `output/decision_memo.md`: A formal executive decision memorandum addressed to the Chief Planning Officer with structured headings, comparative quantitative tables, labeled engineering units, and complete rejection rationales for competing alternatives.
  2. `output/decision_summary.json`: A strictly formatted JSON payload reporting the recommended region, recommended technology, power/energy ratings, effective firm capacity, annual avoided unserved energy, curtailment utilized, net resilience value, and data integrity parameters.

---

## 2. Complexity Justification & Design Challenges
The task is engineered around three major analytical challenges and cross-file reconciliation dependencies:

### Challenge 1 (The Crux): Non-Linear Ambient Thermal De-Rating vs. Nameplate Efficiency
- **Planted in Data/Documents**: Technical specifications (`bess_technical_specifications.xlsx`, Sheet 2) provide thermal de-rating curves where NMC chemistry de-rates by 7.0%/°C above 35°C (with air HVAC) and VRFB exhibits severe parasitic pumping losses, whereas LFP with industrial closed-loop liquid cooling (`LFP-200-800`) maintains 94% firm capability up to 45°C. Concurrently, NOAA weather data (`noaa_hourly_weather_observations.parquet`) proves ambient temperatures in `REGION_B_ERCOT_CENTRAL` exceed 41.5°C during the critical grid emergency hours.
- **Correct Analyst Action**: The analyst cross-references the hourly temperature time series with the BESS thermal curve to compute Effective Firm Capacity (EFC) during the August heatwave peak. They discover that while `NMC-100-200` has the highest nameplate RTE (92%) and lowest capex, its usable power collapses to 50.5 MW during the 195 MW peak crisis. Thus, `LFP-200-800` is the only system delivering sufficient firm power (188.0 MW) and energy (752 MWh usable) to eliminate the grid deficit.
- **Careless Analyst Action**: A careless model optimizes solely for nameplate round-trip efficiency (92%) or lowest overnight capital expenditure ($95M) and selects `NMC-100-200`, ignoring ambient thermal de-rating during peak summer hours, resulting in severe unserved energy and a sub-optimal net value.

### Challenge 2: Settlement Finality vs. Real-Time Telemetry Lag
- **Planted in Data/Documents**: In `eia_hourly_operations_2023.csv`, rows for August 17–19 contain preliminary SCADA telemetry records (`status = 'PRELIMINARY'`, `revision_seq = 1`) followed by revenue-metered settlement logs (`status = 'FINAL'`, `revision_seq = 2`). The preliminary records undercount peak industrial demand by ~3,800 MW due to delayed telemetry feeds. Furthermore, Section 5.2 of `regional_reliability_standards.pdf` explicitly mandates that only settled records (`status = 'FINAL'`) be utilized.
- **Correct Analyst Action**: The analyst filters specifically for `status == 'FINAL'` (or sorts by `revision_seq` descending), recovering the true peak demand of 41,450 MW and uncovering the critical 1,420 MWh unserved energy deficit.
- **Careless Analyst Action**: A careless model executes naive deduplication (e.g. `df.drop_duplicates(subset=['utc_timestamp'], keep='first')`). This retains the preliminary under-reported demand, concluding there is zero unserved energy in Region B, and incorrectly directing the battery investment to Region C for pure renewable curtailment arbitrage.

### Challenge 3: Coarse Metric Heuristic Traps
- **Planted in Data/Documents**:
  - `REGION_A_MISO_SOUTH` exhibits the highest gross annual load (mean 28,000 MW, peak 38,500 MW), but has 36,000 MW of firm gas/nuclear generation and 6,000 MW of tie-line imports, resulting in zero net unserved energy deficits.
  - `REGION_C_CAISO_SP15` exhibits massive renewable curtailment (3,222,384 MWh), but existing battery installations (4,000 MW) and 7,500 MW interties eliminate loss-of-load deficits.
  - `REGION_D_SPP_WEST` experiences frequent convective storm alerts and high wind generation, but strong export interties prevent loss-of-load events.
- **Correct Analyst Action**: The analyst executes full multi-factor resource adequacy modeling across all 8,760 hours, discovering that only `REGION_B_ERCOT_CENTRAL` suffers catastrophic unserved energy deficits (1,420.0 MWh, $16.4M VoLL impact) due to thermal generator de-rating, low intertie capacity (1,250 MW), and coincident solar sunset ramps.
- **Careless Analyst Action**: A superficial model uses simple heuristics (picking Region A for highest gross demand, Region C for highest solar curtailment, or Region D for storm frequency), all of which produce negative net economic resilience values.

---

## 3. Analytical Taxonomy & Reasoning Loop
- **Primary Analytical Objectives**:
  1. Multi-regional electric grid resource adequacy and loss-of-load expectation modeling.
  2. Techno-economic valuation and thermal de-rating optimization of utility-scale BESS assets.
- **Sequential Reasoning Phases**:
  1. **Explore**: Ingest and audit schemas across EIA CSV operations, SQLite substation topologies, NOAA Parquet weather tables, BESS Excel specification sheets, and the regulatory PDF directive.
  2. **Hypothesize**: Formulate candidate regional vulnerability profiles (evaluating whether gross peak load, duck-curve solar curtailment, or islanded thermal heat stress drives investment priority).
  3. **Analyze**: Harmonize timestamps to UTC, filter settled final records, calculate hourly available firm generation under temperature de-rating, determine net unserved deficits, and evaluate BESS thermal capability.
  4. **Synthesize**: Reconcile VoLL benefits ($12,500/MWh), renewable curtailment capture ($45/MWh), round-trip efficiency losses ($35/MWh), and annualized capex/opex into net annual resilience value.
  5. **Recommend**: Formulate unambiguous recommendations (`REGION_B_ERCOT_CENTRAL` and `LFP-200-800`), document quantified rejection rationales for all alternatives, and verify reporting integrity.

---

## 4. Expected Difficulty Range
- **Sweep Target**: Strong frontier models (Claude 3.5 Sonnet, GPT-4o) are projected to achieve a mean reward strictly below **0.50** (with no single run exceeding 0.70). Weaker models (e.g. GPT-3.5, smaller open models) will score at or below **0.25**.
- **Crux Failure Mechanism for Strong Models**: Strong models routinely generate fast Python analysis scripts that execute naive table merges on local timestamps, deduplicate data with `keep='first'` (retaining unrevised preliminary telemetry), or select batteries based on nameplate specs without looking up ambient temperature de-rating during the peak heat window. Any of these three errors completely shifts the recommendation away from the ground truth.

---

## 5. Ground-Truth Recommendation & Proof
- **Recommended Region**: `REGION_B_ERCOT_CENTRAL`
- **Recommended Technology**: `LFP-200-800` (200 MW / 800 MWh, 4-hour duration, industrial liquid cooling)
- **Numerical Proof**:
  - Peak Net Firm Deficit: **195.0 MW** (August 18, 22:00 UTC, ambient temp 41.5°C).
  - Total Annual Deficit: **1,420.0 MWh** across critical August heatwave events.
  - Effective Firm Capacity: **188.0 MW** (at 41.5°C, 200 MW × [1 - 5.25% derate - 1.8% aux cooling] = 188.0 MW).
  - Avoided Unserved Energy: **1,312.4 MWh** (mitigating 92.4% of all unserved grid load).
  - Avoided Unserved Energy Value: 1,312.4 MWh × $12,500/MWh = **$16,405,000**.
  - Curtailed Renewables Captured: **52,140.0 MWh** × $45/MWh = **$2,346,300**.
  - RTE Charging Loss Cost: 52,140 MWh × (1 - 0.85) × $35/MWh = **$273,735**.
  - Annual Costs: Annualized Capex ($3,180,000) + Fixed O&M ($1,473,065) = **$4,653,065**.
  - **Net Annual Resilience Value**: $16,405,000 + $2,346,300 - $273,735 - $4,653,065 = **$13,824,500.00**.

### Proof of Alternative Rejections:
- **`REGION_A_MISO_SOUTH`**: Net unserved deficit is 0 MWh (due to 36 GW firm fleet and 6 GW interties). Net resilience value is **-$4,653,065** (pure capital loss).
- **`REGION_C_CAISO_SP15`**: Zero unserved deficit (existing 4 GW storage and 7.5 GW interties). Curtailment arbitrage value ($2.34M) is outweighed by capex/opex ($4.65M), yielding **-$2,268,065** net value.
- **`REGION_D_SPP_WEST`**: High wind generation and transmission exports prevent unserved deficits. Net value is **-$2,268,065**.
- **`NMC-100-200` in Region B**: Air cooling and 35°C threshold drops firm capacity to 50.5 MW during 41.5°C peak; 2-hour duration exhausts charge prematurely, leaving ~1,200 MWh unserved. Net value is only **$1,511,400**.
- **`LFP-100-400` in Region B**: 100 MW power rating leaves up to 95 MW unmet during peak hours. Avoids only 680 MWh. Net value is **$6,932,400**.
- **`VRFB-50-500` in Region B**: 50 MW power rating is severely constrained; 72% RTE creates heavy loss penalties. Net value is **$1,873,000**.

---

## 6. Expected Reasoning Trajectory
1. Inspect file system and identify data roles: EIA CSV (operations), SQLite (topology/contingency), Parquet (weather), XLSX (BESS engineering/finance), PDF (directive/standards), Macro CSV (distractor).
2. Consult `regional_reliability_standards.pdf` to identify regulatory formulas, VoLL ($12,500/MWh), and the data integrity rule (UTC normalization and `status == 'FINAL'`).
3. Query SQLite for substation import limits, generator fleet capacities, and EFORd ratings.
4. Clean and join EIA operations with NOAA weather by UTC timestamp and region.
5. Compute hourly available firm supply taking into account ambient thermal de-rating of gas turbines.
6. Identify unserved energy deficit hours across all 4 regions, establishing that Region B has catastrophic deficits.
7. Model all 4 BESS candidates against Region B's deficit profile and thermal conditions.
8. Calculate financial resilience metrics, verifying that `LFP-200-800` delivers $13.82M net annual value.
9. Generate `output/decision_memo.md` and `output/decision_summary.json` matching the required schema and headings.
