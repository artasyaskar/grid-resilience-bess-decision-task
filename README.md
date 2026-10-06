# Grid Resilience BESS Allocation Decision Task (`grid-resilience-bess-decision-task`)

A rigorous, benchmark-grade Electrical Engineering & Energy Systems analytical decision task packaged for the **Harbor** evaluation platform (Harbor 0.18.0).

---

## Overview

- **Analyst Role**: Lead Grid Planning & Energy Storage Analyst at Apex Clean Energy Infrastructure Authority
- **The Core Decision**: Determine which of 4 candidate balancing authorities (`REGION_A_MISO_SOUTH`, `REGION_B_ERCOT_CENTRAL`, `REGION_C_CAISO_SP15`, `REGION_D_SPP_WEST`) must receive a utility-scale Battery Energy Storage System (BESS) investment, and select the single optimal battery configuration (`LFP-100-400`, `NMC-100-200`, `LFP-200-800`, `VRFB-50-500`) to maximize net annual resilience value while eliminating grid loss-of-load deficits under extreme heat stress.
- **Ground-Truth Recommendation**: `REGION_B_ERCOT_CENTRAL` paired with `LFP-200-800`.
- **Target Evaluation Sweeps**: Strong models (Claude 3.5 Sonnet, GPT-4o) mean reward $\le 0.50$ (no single trial $> 0.70$); weak models $\le 0.25$.

---

## Harbor Package Layout

```
grid-resilience-bess-decision-task/
├── task.toml                       # Task resource bounds and operational metadata
├── instruction.md                  # Method-free, contract-complete prompt for the agent
├── rubrics.json                    # 35 binary criteria (100 positive pts, 40 on decision)
├── task_card.md                    # Detailed task review documentation & crux justifications
├── LICENSE                         # Open MIT license
├── README.md                       # Repository guide
├── environment/                    # Container specification & input data
│   ├── Dockerfile                  # Base image pinned by immutable @sha256 digest
│   ├── LICENSES.md                 # Public data provenance (EIA-930, NOAA, NREL ATB)
│   ├── README_DATA.md              # Input data schema catalog
│   └── data/
│       ├── eia_hourly_operations_2023.csv         # 8,760-hr grid operations (CSV)
│       ├── grid_substations_topology.sqlite       # Relational substation & generator DB (SQLite)
│       ├── noaa_hourly_weather_observations.parquet # Hourly meteorology time series (Parquet)
│       ├── bess_technical_specifications.xlsx     # Battery configurations & thermal curves (XLSX)
│       ├── regional_reliability_standards.pdf     # Official regulatory directive (PDF)
│       └── regional_macroeconomic_tariffs.csv     # Plausible regional economic indicators (Distractor)
├── solution/                       # Reference golden solution (never shown to agent)
│   ├── solve.sh                    # Executable entry point
│   └── solve.py                    # Deterministic energy systems solver
├── tests/                          # Programmatic verifier (offline & deterministic)
│   ├── test.sh                     # Verifier bash entry point
│   ├── test_outputs.py             # Offline verification checks
│   └── test_weights.json           # Programmatic test weights ([])
└── scripts/                        # Development & auditing scripts
    ├── prepare_dataset.py          # Regenerates input datasets
    ├── compute_ground_truth.py     # Independent ground truth verifier
    └── evaluate_rubric.py          # Local judge simulating rubrics.json scoring
```

---

## Input Data Complexity & Analytical Cruxes

1. **Multi-Format Cross-Referencing**:
   - Spans 5 distinct data categories: CSV, SQLite, Parquet, XLSX, and PDF.
   - At least 2 genuinely complex files (`eia_hourly_operations_2023.csv` with 35,000+ rows and `grid_substations_topology.sqlite` with relational schemas).
   - Contains 1 realistic distractor dataset (`regional_macroeconomic_tariffs.csv`).
2. **Crux 1: Non-Linear Ambient Thermal De-Rating**:
   - `NMC-100-200` has the highest nameplate round-trip efficiency (92%) and lowest capex, but suffers 7%/°C de-rating above 35°C, collapsing to 50.5 MW during ERCOT Central's 41.5°C peak heatwave crisis.
   - `LFP-200-800` utilizes industrial closed-loop liquid cooling, retaining 188.0 MW firm capacity to eliminate the 195 MW peak grid deficit.
3. **Crux 2: Settlement Finality vs SCADA Telemetry**:
   - Telemetry SCADA records (`status = 'PRELIMINARY'`) omitted delayed industrial metering feeds, under-reporting peak load by ~3,800 MW. Naive deduplication (`keep='first'`) misses the entire 1,420 MWh deficit! Filtering for settled revenue metering (`status = 'FINAL'`) is required.
4. **Crux 3: Coarse Heuristic Defeat**:
   - Region A has highest gross load $\to$ $0$ deficit, -$4.65M net return.
   - Region C has highest solar curtailment $\to$ $0$ deficit, -$2.27M net return.
   - Region D has highest storm count $\to$ $0$ deficit, -$2.27M net return.

---

## Local Verification & Testing

### 1. Run Reference Solution
```bash
python solution/solve.py
```
Generates golden deliverables in `output/decision_memo.md` and `output/decision_summary.json`.

### 2. Verify Programmatic Tests (Oracle Check)
```bash
python tests/test_outputs.py
```
Expected output: `14/14 checks passed`, writes `/logs/verifier/ctrf.json` and `reward.json`.

### 3. Verify Rubrics (NOP vs. Oracle)
```bash
python scripts/evaluate_rubric.py
```
Expected output:
- **ORACLE SCORE**: `100/100 points -> Reward: 1.0000`
- **NOP SCORE**: `0/100 points -> Reward: 0.0000`

### 4. Harbor CLI Checks (with Docker running)
```bash
# NOP agent check (must score 0)
harbor run -p . -a nop

# Oracle agent check (must score 1.0)
harbor run -p . -a oracle

# Inspect run logs
harbor view ./jobs
```

---

## Packaging for Submission

To create the clean task archive for platform upload:
```bash
# Ensure zip excludes temporary local artifacts
zip -r grid-resilience-bess-decision-task.zip task.toml instruction.md rubrics.json task_card.md LICENSE README.md environment/ solution/ tests/
```
Ensure that no files outside the allowlist are included.
