# Grid Resilience BESS Allocation Decision Task (`grid-resilience-bess-decision-task`)

A rigorous, benchmark-grade Electrical Engineering & Energy Systems analytical decision task packaged for the **Harbor** evaluation platform (Harbor 0.18.0). Built entirely from authoritative public data sources (EIA-930, NOAA ISD, NREL ATB 2023).

---

## Overview

- **Analyst Role**: Lead Grid Planning & Energy Storage Analyst at Apex Clean Energy Infrastructure Authority
- **The Core Decision**: Determine which of 4 candidate balancing authorities (`REGION_A_MISO_SOUTH`, `REGION_B_ERCOT_CENTRAL`, `REGION_C_CAISO_SP15`, `REGION_D_SPP_WEST`) must receive a utility-scale Battery Energy Storage System (BESS) investment, and select the optimal battery configuration (`LFP-100-200`, `LFP-150-600`, `LFP-200-800`, `NMC-200-800`, `FLOW-100-800`) to maximize net annual resilience value while eliminating grid loss-of-load deficits under extreme heat stress.
- **Ground-Truth Recommendation**: `REGION_B_ERCOT_CENTRAL` paired with `LFP-200-800`.
- **Accredited Effective Firm Capacity**: 189.81 MW during peak scarcity intervals.
- **Annual Avoided Unserved Energy**: 188,968.0 MWh.
- **Net Annual Resilience Value**: $1,653,136,610.60.

---

## Harbor Package Layout

```
grid-resilience-bess-decision-task/
├── task.toml                       # Task resource bounds and operational metadata
├── instruction.md                  # Method-free, contract-complete prompt for the agent
├── rubrics.json                    # 29 binary criteria (100 positive pts, 30 on decision)
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
│       └── regional_macroeconomic_tariffs.csv     # Regional VOLL & off-peak tariffs (CSV)
├── solution/                       # Reference golden solution (never shown to agent)
│   ├── solve.sh                    # Executable entry point
│   └── solve.py                    # Deterministic energy systems solver
├── tests/                          # Programmatic verifier (offline & deterministic)
│   ├── test.sh                     # Verifier bash entry point
│   ├── test_outputs.py             # Offline verification checks
│   └── test_weights.json           # 29 weighted programmatic checks summing to 100 pts
├── docs/                           # Comprehensive documentation & verification logs
│   ├── final_audit_report.md       # Full rebuild provenance and audit report
│   └── adversarial_validation_results.json # Adversarial validation score matrix
└── scripts/                        # Development & auditing scripts
    ├── prepare_dataset.py          # Regenerates input datasets from raw sources
    ├── compute_ground_truth.py     # Independent ground truth verifier
    ├── run_adversarial_suite.py    # Adversarial test runner (variants A-I)
    └── verify_determinism.py       # Multi-run bitwise determinism verifier
```

---

## Input Data Complexity & Analytical Cruxes

1. **Multi-Format Cross-Referencing**:
   - Spans 5 distinct data categories: CSV, SQLite, Parquet, XLSX, and PDF.
   - At least 2 genuinely complex files (`eia_hourly_operations_2023.csv` with 35,000+ rows and `grid_substations_topology.sqlite` with relational schemas).
   - Relies on regulatory directives (`regional_reliability_standards.pdf`) for mathematical formulations.
2. **Crux 1: Non-Linear Ambient Thermal De-Rating & Section 3.5 Tie-Breaker**:
   - `NMC-200-800` exhibits higher headline financial return under unconstrained conditions ($1.687B vs $1.653B, within 2.04%), but de-rates at 1.5%/°C above 35°C (yielding 184.39 MW EFC).
   - `LFP-200-800` de-rates at only 0.8%/°C, maintaining 189.81 MW EFC. Pursuant to Section 3.5 of the reliability directive, candidates within 3.0% must be awarded to the asset with higher accredited EFC during extreme heat stress.
3. **Crux 2: Settlement Finality vs Preliminary Telemetry**:
   - Preliminary SCADA telemetry (`settlement_status == 'INITIAL'`) contains incomplete generation feeds. Solvers must filter for revenue-metered settlement logs (`settlement_status == 'FINAL'`).
4. **Crux 3: UTC Temporal Harmonization**:
   - NOAA meteorological series are recorded in UTC, while operations tables contain both local wall-clock and UTC timestamps. Failure to normalize to UTC causes a 5-6 hour shift, misaligning peak temperature intervals with grid deficit hours.
5. **Crux 4: Substation Headroom Constraints**:
   - Region C (CAISO SP15) has a 180 MW substation headroom limit at Redondo Beach 230kV, legally disqualifying all 200 MW configurations.

---

## Verification & Testing

### 1. Run Reference Solution
```bash
python solution/solve.py
```
Generates golden deliverables in `output/decision_memo.md` and `output/decision_summary.json`.

### 2. Verify Programmatic Tests (Oracle Check)
```bash
python tests/test_outputs.py
```
Expected output: `29/29 checks passed -> Reward: 1.0000`, writes `/logs/verifier/ctrf.json` and `/logs/verifier/reward.json`.

### 3. Run Adversarial Suite
```bash
python scripts/run_adversarial_suite.py
```
Validates that shallow heuristics naturally fail appropriate criteria while the Oracle achieves full reward.

### 4. Verify Bitwise Determinism
```bash
python scripts/verify_determinism.py
```
Verifies identical SHA256 hashes across repeated independent solver runs.

### 5. Harbor CLI Commands (Offline Container)
```bash
# NOP agent check (must score 0.0000)
harbor run -p . -a nop

# Oracle agent check (must score 1.0000)
harbor run -p . -a oracle
```
