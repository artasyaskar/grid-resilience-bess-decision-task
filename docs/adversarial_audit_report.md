# Hostile Quality Audit Report: `grid-resilience-bess-decision-task`

This document details the exhaustive, adversarial review conducted across three independent personas in accordance with the benchmark creation handbook.

---

## Part 1: Reviewer 1 — Senior Energy-Systems Engineer

### 1. Independent Task Solution & Defense
- **The Core Question**: Where should the capital allocation committee deploy a single utility-scale BESS, and what battery chemistry/sizing should be selected?
- **Data Cross-Reconciliation**:
  - The analyst parses `grid_substations_topology.sqlite` to obtain available firm generation fleets and tie-line import limits.
  - The analyst cross-references `eia_hourly_operations_2023.csv` with `noaa_hourly_weather_observations.parquet` on UTC timestamps.
  - In `REGION_B_ERCOT_CENTRAL`, during August 17–19, 2023, extreme heat (>41.5°C) triggers 1.2%/°C thermal de-rating across gas combined-cycle and peaking combustion turbines. Concurrently, solar generation collapses during the 20:00–23:00 UTC evening ramp while cooling demand stays near 41,450 MW.
  - This results in **1,420.0 MWh** of net firm generation deficit across 10 stress hours, with a peak hourly deficit of **195.0 MW**.
  - In `REGION_A_MISO_SOUTH`, 36,000 MW firm fleet + 6,000 MW tie imports provide adequate headroom (0 unserved deficit).
  - In `REGION_C_CAISO_SP15`, existing 4,000 MW storage + 7,500 MW Pacific interties absorb ramps (0 unserved deficit).
  - In `REGION_D_SPP_WEST`, wind generation and export interties maintain balance (0 unserved deficit).
- **Battery Sizing & Technology**:
  - `LFP-100-400` is rejected: 100 MW power rating leaves 95 MW unmet during the 195 MW peak crisis; net resilience value is $6,932,400.
  - `NMC-100-200` is rejected: Ambient temperature 41.5°C triggers 45.5% thermal capacity de-rating and 4% auxiliary load, reducing firm delivery to 50.5 MW / 109 MWh; net value is $1,511,400.
  - `VRFB-50-500` is rejected: 50 MW power ceiling and 72% round-trip efficiency penalty yield $1,873,000 net value.
  - `LFP-200-800` is uniquely optimal: Closed-loop liquid cooling maintains 188.0 MW effective firm capacity at 41.5°C, eliminating 1,312.4 MWh of unserved energy ($16,405,000 VoLL benefit) and absorbing 52,140 MWh of curtailed renewables ($2,346,300), delivering **$13,824,500.00 USD/year** net value.
- **Defensibility Assessment**:
  - The ground truth is 100% deterministic and mathematically unique. No alternative region or battery configuration can be defended from the shipped evidence.

---

## Part 2: Reviewer 2 — Adversarial Benchmark Model (Shortcut Attack)

We simulated nine shortcut vectors that frontier LLMs commonly attempt:

| Shortcut Vector | Adversarial Heuristic | Resulting Region / Battery Choice | Outcome / Score | Accidental Correct Winner? |
|---|---|---|---|---|
| **Shortcut 1** | Choose highest gross annual load | `REGION_A_MISO_SOUTH` | Net Value: -$4.65M (Reward: ~0.24) | **NO** (Failed) |
| **Shortcut 2** | Choose highest renewable curtailment | `REGION_C_CAISO_SP15` | Net Value: -$2.27M (Reward: ~0.22) | **NO** (Failed) |
| **Shortcut 3** | Choose highest storm/weather alerts | `REGION_D_SPP_WEST` | Net Value: -$2.27M (Reward: ~0.22) | **NO** (Failed) |
| **Shortcut 4** | Choose highest nameplate RTE & lowest capex | `NMC-100-200` (92% RTE, $95M Capex) | De-rates to 50.5 MW; Reward: ~0.55 | **NO** (Failed) |
| **Shortcut 5** | Naive deduplication (`keep='first'`) | Keeps `PRELIMINARY` records | Deficit appears as 0 MWh $\to$ chooses Region C | **NO** (Failed) |
| **Shortcut 6** | Naive timestamp join (Local time == UTC) | Joins CDT against UTC weather | 5-hr shift masks net deficit $\to$ wrong answer | **NO** (Failed) |
| **Shortcut 7** | Single-dataset analysis (CSV only) | Ignores SQLite substation tie limits | Assumes unlimited transmission $\to$ wrong answer | **NO** (Failed) |
| **Shortcut 8** | Select longest duration battery | `VRFB-50-500` (10-hr flow) | Fails power deficit (50 MW vs 195 MW) | **NO** (Failed) |
| **Shortcut 9** | Distractor reliance | Follows `regional_macroeconomic_tariffs.csv` | Picks CA or TX county taxes $\to$ fails technical criteria | **NO** (Failed) |

**Adversarial Verdict**: Zero shortcuts reach the correct recommendation. The correct candidate is NOT the maximum on any single individual metric. It wins solely through the non-linear interaction of variables.

---

## Part 3: Reviewer 3 — Harbor Quality & Standards Auditor

1. **Prompt & Metadata Leakage**:
   - `instruction.md`: Contains zero mention of Region B, ERCOT, LFP-200-800, heatwave dates, or expected numbers. Completely method-free.
   - Filenames: All neutral (`eia_hourly_operations_2023.csv`, `grid_substations_topology.sqlite`, `bess_technical_specifications.xlsx`).
   - Column Names: Neutral domain names; no target labels.
   - Ground Truth Separation: Ground truth exists solely in `solution/` (which is never visible to the agent) and `task_card.md` (which is review-facing).
2. **Rubric Structure**:
   - **Criterion Count**: 35 criteria (compliant with 25–50 bounds).
   - **Total Positive Points**: Exactly 100 points.
   - **Decision Points**: Exactly 40 positive points across 3 `recommend`-category criteria (items 1, 2, 3), satisfying the 30–50% / 30–40% share rule.
   - **Single Criterion Cap**: Maximum single weight is 15 points (15% $\le$ 20% ceiling).
   - **Minimum Criterion Weight**: Minimum is 1 point ($\ge$ 1% floor).
   - **Length Limit**: Every criterion is strictly under 180 characters ($\le$ 250 character limit).
   - **Wording**: Zero subjective terms ("appropriately", "effectively", "reasonably" are absent).
   - **Graded Files**: Every criterion specifies `grades_output_files` pointing to `output/decision_memo.md` and/or `output/decision_summary.json`.
   - **Penalties**: 2 negative criteria (-5 each) checking independent errors (raw code dumps, fabricated region tokens) without double-penalizing missing positive criteria.
3. **Execution Environment & Verifier**:
   - Base Docker image: Pinned by immutable `@sha256:ad5dadd957a398226996bc4846e522c39f2a77340b531b28aaab85b2d361210b` digest.
   - Programmatic tests: Offline, deterministic, reads `/workspace/output`, never references `../output`.
   - `tests/test_weights.json`: Configured as empty array `[]`.
   - Output files: Emits `/logs/verifier/ctrf.json` and `/logs/verifier/reward.json`.
4. **Local Agent Validations**:
   - **NOP Agent**: Receives score **0.0000** (0 / 100 points).
   - **ORACLE Agent**: Receives score **1.0000** (100 / 100 points).
5. **Data Provenance & File Types**:
   - Grounded in EIA-930, NOAA GHCNh, and NREL ATB. Documented in `environment/LICENSES.md`.
   - All files strictly match the Harbor file extension allowlist.

---

## Synthesis of Questions

- **"Could a strong model reach the correct recommendation without performing the intended cross-file analysis?"**
  - **NO.** Every tested shortcut fails. The model must cross-reference operations, substation limits, weather, and thermal de-rating curves.
- **"Can a careful analyst defend exactly one recommendation using only the shipped data?"**
  - **YES.** `REGION_B_ERCOT_CENTRAL` and `LFP-200-800` uniquely deliver positive resilience value ($13.82M), while all competing configurations are negative or severely sub-optimal.
