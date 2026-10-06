# Grid Resilience & Utility-Scale BESS Allocation Decision

## Context and Role
You are acting as the **Lead Grid Planning and Energy Storage Analyst** at the Apex Clean Energy Infrastructure Authority.

The capital allocation committee has authorized funding for exactly **one** utility-scale Battery Energy Storage System (BESS) installation designed to reinforce regional electric grid reliability, eliminate catastrophic unserved energy under extreme weather conditions, and support critical transmission infrastructure.

Four candidate balancing authority sub-regions are competing for this deployment:
1. `REGION_A_MISO_SOUTH`
2. `REGION_B_ERCOT_CENTRAL`
3. `REGION_C_CAISO_SP15`
4. `REGION_D_SPP_WEST`

Your objective is to conduct a rigorous, data-driven engineering and economic analysis across the multi-source authoritative dataset provided in `/workspace/environment/data/`, establish which candidate region must receive the investment, and determine which candidate battery technology configuration is optimal.

---

## Required Deliverables
All deliverables must be written to the `output/` directory (`/workspace/output/`). Any reasoning or analysis presented solely in conversational text will not be graded.

You must produce exactly two deliverables:

### 1. Executive Decision Memorandum (`output/decision_memo.md`)
A formal Markdown decision memorandum addressed to the Chief Planning Officer and the Capital Investment Committee.

The memorandum must include the following exact top-level and second-level section headings:
- `# Executive Decision Memorandum: Utility-Scale BESS Regional Allocation`
- `## 1. Final Investment Recommendation`
- `## 2. Quantitative Regional Comparison & Multi-Factor Trade-Offs`
- `## 3. Storage Technology Selection & Thermal Performance Analysis`
- `## 4. Resilience Valuation & Unserved Energy Mitigation`
- `## 5. Risk Analysis, Sensitivities, and Rejected Alternatives`
- `## 6. Data Integrity Protocol & Accounting Audit`

The memorandum must present professional, publication-grade comparative markdown tables, explicitly labeled engineering units (MW, MWh, °C, $ USD, %, $/MWh), and defensible quantitative reasoning for why the recommended region and technology combination decisively outperforms all competing alternatives. Do not leave placeholder text (such as `TODO`, `TBD`, or `[Insert Here]`) or raw programmatic debug dumps in the deliverable.

### 2. Structured Decision Summary (`output/decision_summary.json`)
A machine-readable JSON file containing the verified decision tokens and supporting numerical results.

The file must conform to the following schema:
```json
{
  "recommended_region": "<REGION_TOKEN>",
  "recommended_technology": "<CONFIG_TOKEN>",
  "power_capacity_mw": <FLOAT_OR_INT>,
  "energy_capacity_mwh": <FLOAT_OR_INT>,
  "storage_duration_hours": <FLOAT_OR_INT>,
  "effective_firm_capacity_mw": <FLOAT>,
  "annual_avoided_unserved_energy_mwh": <FLOAT>,
  "net_annual_resilience_value_usd": <FLOAT_OR_INT>,
  "rejected_regions": [
    {
      "region_id": "<REGION_TOKEN>",
      "rejection_reason": "<STRING>"
    }
  ],
  "data_integrity_notes": {
    "settlement_records_used": "<STRING>",
    "timezone_normalization": "<STRING>"
  }
}
```

#### Field Specifications:
- `recommended_region`: Exactly one of `REGION_A_MISO_SOUTH`, `REGION_B_ERCOT_CENTRAL`, `REGION_C_CAISO_SP15`, `REGION_D_SPP_WEST`.
- `recommended_technology`: Candidate configuration ID from the technical specifications (e.g., `LFP-100-200`, `LFP-150-600`, `LFP-200-800`, `NMC-200-800`, `FLOW-100-800`).
- `power_capacity_mw`: Nominal nameplate power rating in MW.
- `energy_capacity_mwh`: Nominal nameplate energy capacity in MWh.
- `storage_duration_hours`: Rated discharge duration in hours.
- `effective_firm_capacity_mw`: Effective firm capacity delivered during peak deficit stress hours (in MW, reported to 2 decimal places).
- `annual_avoided_unserved_energy_mwh`: Total unserved load avoided across the 2023 annual evaluation window (in MWh, reported to 1 decimal place).
- `net_annual_resilience_value_usd`: Net annual economic resilience value in USD (in whole dollars or rounded to 2 decimal places).
- `rejected_regions`: An array of exactly 3 objects covering the non-selected candidate regions, each specifying the `region_id` and a substantive engineering/economic `rejection_reason`.
- `data_integrity_notes`: An object containing `settlement_records_used` (documenting the settlement status filtered) and `timezone_normalization` (documenting the temporal standard applied).

---

## Operating Instructions & Prohibitions
1. The analysis must be derived entirely from the input files provided in `/workspace/environment/data/`. External internet access is disabled in this evaluation environment.
2. The deliverable files must be written under `/workspace/output/` (or relative path `output/`).
3. You must independently inspect the shipped documentation, standards, topology databases, meteorological series, and operational logs to determine the authoritative regulatory standards, thermal de-rating rules, and settlement criteria.
