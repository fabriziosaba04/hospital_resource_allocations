# Data Dictionary

**Status:** based on the frozen design of 2026-11-07. **Numerical values were approved by the owner on 2026-11-07**; the full set, with rationales, is in [`PROJECT_SPEC.md`](PROJECT_SPEC.md) §10 and is summarised in Section 3. Encodings, file formats and storage locations are set in Section 5. They are implementation-level choices, also recorded in the Implementation Decisions Log in [`PROJECT_SPEC.md`](PROJECT_SPEC.md).

This document covers only the **input datasets and configuration** produced for the stochastic simulation. Agent and environment records are described in [`AGENTS.md`](AGENTS.md). Those records are the Observed State, Allocation State, Decision History, Bed Assignment State, Deterministic Audit Record, Validation History and workflow records. Their schemas are not yet defined.

## 1. Principle

The datasets contain only information that exists **independently of the agents' decisions**.

The distribution of beds and nurses across departments is an agent decision. It is therefore never part of the input data; it lives only in the Allocation State.

## 2. Conventions

| Convention | Definition |
| --- | --- |
| **Day** | Integer simulation day. Days in the horizon start at **1**, so audit days are the multiples of 5. Days ≤ 0 belong to the burn-in period. |
| **Horizon** | Days 1 … H, with H = 30 (approved; a multiple of 5). All metrics are computed within the horizon only. |
| **Burn-in** | A period simulated before day 1 so that the hospital is already occupied on day 1. Its length is 30 days (approved). |
| **Department** | Encoded as `internal_medicine`, `cardiology`, `neurology` or `orthopedics`. This fixed order is also used for deterministic tie-breaks. |
| **Complexity** | Integer 1, 2 or 3. Level 3 is the highest clinical priority. |
| **Presence** | A patient is present on day d if `arrival_day ≤ d < discharge_day`. On the discharge day the bed is already free. |
| **Census** | The number of patients present on a day, by department and complexity level. |

## 3. Tables

### 3.1 `hospital_resources_daily`

One row per day of the horizon. Primary key: `day`.

| Field | Type | Description | Value |
| --- | --- | --- | --- |
| `day` | integer | Simulation day, 1 … H | H = 30 |
| `total_beds` | integer ≥ 0 | Hospital-level bed pool P_B(t). Must satisfy `total_beds ≤ 4 × max_beds`. | Base 96; +4 on days 16–20; −10 on days 23–25 |
| `total_nurses` | integer ≥ 0 | Hospital-level nurse pool P_N(t), as an aggregate daily headcount with no shifts | Base 37; −4 on days 8–10 |
| `external_event` | text, may be empty | Description of any external shock affecting the pools on that day | Current-day change only, no duration or forecast. Non-empty only when a pool differs from the previous day, restorations included (days 8, 11, 16, 21, 23, 26); empty on day 1. Example: `bed pool reduced by 10` |

External shocks affect only these hospital-level pools, never a specific department.

### 3.2 `department_demand_daily`

One row per day of the horizon and department. Primary key: (`day`, `department`).

| Field | Type | Description |
| --- | --- | --- |
| `day` | integer | Simulation day, 1 … H |
| `department` | category | One of the four departments |
| `arrivals` | integer ≥ 0 | Patients whose `arrival_day` equals `day` |
| `discharges` | integer ≥ 0 | Patients whose `discharge_day` equals `day` |
| `census_L1` | integer ≥ 0 | Level-1 patients present on `day` |
| `census_L2` | integer ≥ 0 | Level-2 patients present on `day` |
| `census_L3` | integer ≥ 0 | Level-3 patients present on `day` |

- Census counts all present patients, whether they hold a bed or are in overflow. Bed holding is an outcome of allocation, not an input.
- On day 1, census includes the burn-in patients still present.
- This table is deliberately redundant with `patient_registry` (Section 4).

### 3.3 `patient_registry`

One row per patient, including burn-in patients. Primary key: `patient_id`.

| Field | Type | Description |
| --- | --- | --- |
| `patient_id` | string, unique | `P` followed by six digits (for example `P000123`). IDs are assigned in order of (`arrival_day`, generation order), so ID order matches arrival order. |
| `department` | category | Department the patient belongs to |
| `complexity` | integer 1–3 | Clinical complexity level |
| `arrival_day` | integer | Day of arrival. It is ≤ 0 for burn-in patients. |
| `discharge_day` | integer | True day of discharge, always populated. It may lie beyond the horizon, because discharges are simulated past day H. Must be greater than `arrival_day`. |

- Length of stay is `discharge_day − arrival_day`. It depends only on `complexity`.
- **Temporal rule:** agents never see the `discharge_day` of a patient still present. A discharge is observed only on the day it occurs.
- Agents access patient-level data only through server tools, for example `get_overflow_queue`, which returns days waiting measured from `arrival_day`.
- No demographic, personal or sensitive attributes are included. Any additional attribute requires explicit approval.

### 3.4 `environment_config` (static, visible to agents)

The rules of the environment, which agents need in order to act.

| Field | Type | Description | Value |
| --- | --- | --- | --- |
| `max_beds` | integer ≥ 0 | Maximum beds allocatable to any department. It is **the same for all departments**. | 40 (approved) |
| `w_L1`, `w_L2`, `w_L3` | numeric ≥ 0 | Nurse weights for the N1 requirement, treated as an environment staffing norm | 0.20, 0.35, 0.60 (approved) |

### 3.5 `generation_config` (static, hidden from all agents)

The true parameters of the data-generating process. It is used only by the generator. No server tool reads it, and inferring demand patterns from history is part of the ALLOCATOR's role.

| Parameter | Granularity | Value |
| --- | --- | --- |
| Arrival rate λ_d, including any temporal trend or surge | Per department (a surge in at least one) | IM 6.0, Cardiology 4.0, Neurology 3.0, Orthopedics 4.5; Cardiology × 1.6 on days 12–19 |
| Complexity mix (probability of each level among arrivals) | Per department | IM .45/.40/.15, Cardiology .25/.40/.35, Neurology .20/.40/.40, Orthopedics .55/.35/.10 |
| Length-of-stay distribution | Per complexity level, the same across departments | Discretised lognormal (ceiling), continuous CV 0.6, μ calibrated so the discrete means are exactly 3 / 5 / 8 days (approved 2026-11-11) |
| Base pools | Hospital-level | `total_beds` 96, `total_nurses` 37 |
| Shocks (scheduled) | Hospital-level | Nurses −4 on days 8–10; beds +4 on days 16–20; beds −10 on days 23–25 |
| Burn-in length | Global | 30 days |
| Horizon H | Global, a multiple of 5 | 30 days |
| Random seeds | Per generated dataset | Primary 20261107; robustness 20261108, 20261109 (baselines only) |

All values were approved by the owner on 2026-11-07. Rationales are in `PROJECT_SPEC.md` §10.

Departments differ **only** in arrival rate and complexity mix. They do not differ in nursing intensity or length of stay.

## 4. Validation Checks

These checks must not depend on any LLM output.

### 4.1 Reconciliation (operations vs. registry)

`department_demand_daily` and `patient_registry` are generated **independently from the same simulation run**. Reconciling them is therefore a genuine verification check.

For every day d in 1 … H and department k:

1. `arrivals(d, k)` equals the number of registry patients in k with `arrival_day = d`.
2. `discharges(d, k)` equals the number of registry patients in k with `discharge_day = d`.
3. `census_Lj(d, k)` equals the number of registry patients in k with complexity j and `arrival_day ≤ d < discharge_day`. On day 1 this includes burn-in patients.
4. For d ≥ 2: `census_total(d, k) = census_total(d−1, k) + arrivals(d, k) − discharges(d, k)`, where `census_total` is the sum of the three census fields.

### 4.2 Integrity

- `patient_id` is unique.
- `discharge_day > arrival_day` for every patient.
- All `department` and `complexity` values are valid.
- Every day 1 … H appears exactly once in `hospital_resources_daily`, and once per department in `department_demand_daily`.
- Burn-in patients have `arrival_day ≤ 0`, and every patient present on day 1 appears in the registry.

### 4.3 Generation constraints

- **Bed-cap feasibility:** `total_beds(t) ≤ 4 × max_beds` for every day t, **including after positive shocks**. Otherwise conservation and the cap cannot both hold. A dataset that violates this is rejected.
- Pools are non-negative integers on every day.

## 5. Files and Storage

Each generated dataset has a `dataset_id`, which encodes the seed.

| Content | Location | Format | Visible in run sessions |
| --- | --- | --- | --- |
| `hospital_resources_daily`, `department_demand_daily`, `patient_registry` | `data/raw/<dataset_id>/` | CSV | No: denied, and served to agents only through tools |
| `environment_config` | `data/metadata/<dataset_id>/environment_config.json` | JSON | Only through tools |
| `generation_config` | `data/metadata/<dataset_id>/generation_config.json` | JSON | **No**: denied, and never read by any server tool |
| Validation and reconciliation report | `data/processed/<dataset_id>/validation_report.json` | JSON | No: denied |
| Monte Carlo summaries, bands and sweep | `data/processed/montecarlo/` | JSON, CSV, PNG | No: denied (they describe the generation process) |

**Run sessions deny every file under `data/**`** (approved 2026-11-11). Agents reach data only through the MCP server.

**Datasets (frozen at tag `data-v1.0`, 2026-11-11; `data/MANIFEST.json` holds their SHA-256 hashes):**

| `dataset_id` | Role |
| --- | --- |
| `seed20261107` | Primary: agent runs and baselines |
| `seed20261108`, `seed20261109` | Robustness: baselines only (appendix) |
| `seed20261107_stress` | **Constructed test case**, not a representative draw: identical to the primary except Shock 3 (beds −40 on days 23–25, pool 56), which forces a 6-bed cut on day 23. Excluded from every comparison in the main evaluation |

Any change to frozen data needs a new tag and the owner's approval.

The `external_event` text describes **only the current day's change**, for example "bed pool reduced by 10". It never states a duration or a forecast (approved by the owner on 2026-11-07).

## 6. Open Items

None for this dictionary.
