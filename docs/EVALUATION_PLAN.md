# Evaluation Plan

**Status:** draft. **All formulas are provisional** until the first data generation, and the final selection of metrics is open (`CLAUDE.md` §10.M). Principles are in `CLAUDE.md` §7 and §10.L, and implementation details in [`PROJECT_SPEC.md`](PROJECT_SPEC.md).

## 1. Question

Does the LLM ALLOCATOR make better allocation decisions than simple deterministic strategies, facing the same environment, while respecting clinical priority first, then fairness, then efficiency? And how reliable and consistent is it?

## 2. Notation

All quantities are computed **within the horizon, days 1 … H**, from the run records, mainly the Bed Assignment State and the Allocation State.

| Symbol | Meaning |
| --- | --- |
| d, k, t | Department, complexity level, day |
| n_{k,d}(t) | Present level-k patients in d, including overflow |
| OF_{k,d}(t) | Level-k patients in overflow in d on day t |
| need, covered, shortage | Nurse quantities from coverage rule C1 (`PROJECT_SPEC.md` §5.4) |
| B_d, N_d, P_B, P_N, O_d | As in `CLAUDE.md` §10 |

## 3. Metrics by Dimension (provisional)

### 3.1 Clinical priority

| Metric | Formula | Note |
| --- | --- | --- |
| Clinical violations, by type | Count of bed, shock-cut and nurse violations (`CLAUDE.md` §10.G), summed over t | Detected by the deterministic audit |
| Severity | For each violation, the level gap k − k′ between the unserved patient and the one served in their place. Report the total, the mean and the distribution. | An empty movable bed left unused while a higher-level patient overflows is a **separate violation type, with severity = k** (approved 2026-11-07). |
| Overflow by level | `Σ_t Σ_d OF_{k,d}(t)` (patient-days), for each k | L3 patient-days are the most important |
| Nurse shortage by level | `Σ_t Σ_d shortage_{k,d}(t)`, for each k | Attributed from the lowest level upward |

To avoid double counting, bed violations are counted by **pairing**: unserved patients are taken from the highest level down, each paired with the lowest-level movable bed served in their place.

### 3.2 Fairness (F2, per level k)

| Metric | Formula |
| --- | --- |
| Overflow-rate dispersion | `max_d OR_{k,d} − min_d OR_{k,d}`, where `OR_{k,d} = Σ_t OF_{k,d}(t) / Σ_t n_{k,d}(t)` (pooled over the horizon). Also reported as a daily series. |
| Mean days in overflow | `Σ_t Σ_d OF_{k,d}(t) / (number of distinct level-k patients present at some t in the horizon)` |
| Relative nurse coverage | `RC_{k,d} = Σ_t covered_{k,d}(t) / Σ_t need_{k,d}(t)`. Report its dispersion, `max_d − min_d`. |

### 3.3 Efficiency

| Metric | Formula |
| --- | --- |
| Bed utilisation | `Σ_t (beds occupied) / Σ_t P_B(t)` |
| Idle beds | `Σ_t Σ_d max(0, B_d − n_d)`, reported separately for days when overflow exists elsewhere |
| Nurse utilisation | `Σ_t Σ_d min(N_d, requirement_d) / Σ_t P_N(t)` |
| Idle nurses | `Σ_t Σ_d max(0, N_d − requirement_d)` |

### 3.4 Operational feasibility and resource conservation

| Metric | Source |
| --- | --- |
| Rejected submissions (count, codes) | Decision History attempts |
| ALLOCATOR failures (days repaired) | Allocation State source = repair rule |
| Hard-constraint violations in effect | Deterministic audit. Must be 0 for accepted decisions; a non-zero value indicates a validator bug. |
| Halts | Workflow records |

### 3.5 Sequential consistency and stability

| Metric | Formula |
| --- | --- |
| Reallocation frequency | Days on which the allocation differs from the previous day beyond what the pool change forces |
| Reallocation size (beds) | `½ (Σ_d |B_d(t) − B_d(t−1)| − |P_B(t) − P_B(t−1)|)`, and the same for nurses |
| Reversals | A department gains and then loses resources (or the reverse) within a short window. The window length is provisional. |

### 3.6 Structural outcomes: excluded from agent-attributable metrics (recorded 2026-11-11)

Some outcomes are forced by the data and the environment rules, so no policy can avoid them. They are reported separately, as context, and are **excluded from every metric attributed to the ALLOCATOR** (and to the baselines, in the same way):

| Structural outcome | Definition | Example (primary dataset, approved schedule) |
| --- | --- | --- |
| **Demand above the bed cap** | On day t, `max(0, n_d(t) − max_beds)` patients in d are in overflow under every feasible allocation | Cardiology 41 on day 17; Internal Medicine 41 on day 21 (1 patient-day each) |
| Hospital-level bed shortfall | `max(0, Σ_d n_d(t) − P_B(t))` patients are in overflow whatever the split | 22 patient-days over 5 days |
| Hospital-level nurse shortfall | `max(0, Σ_d requirement_d(t) − P_N(t))` | 67 nurse-days over 17 days (the deliberate rationing regime, `PROJECT_SPEC.md` §10.2) |

- **Overflow metrics** (§3.1, §3.2) are reported both raw and net of the cap excess. Only the net figure is attributed to a policy.
- **Clinical violations** already exclude cap-blocked cases by definition (`CLAUDE.md` §10.G: "the cap of d would have allowed assigning the bed to d").
- Shortfalls at the hospital level are not subtracted from the policy metrics; *how* a shortfall is distributed across levels and departments is exactly what the metrics judge. They are reported as the unavoidable floor against which policies are compared.
- The listed examples refer to the current primary dataset and change if the dataset is regenerated.

### 3.7 Explanation quality (LLM CHECKER, qualitative)

- The share of decisions whose stated expected consequences match the deterministic outcomes.
- The issues the LLM CHECKER flags, by category (violation, concern, improvement).
- These complement the deterministic metrics and never replace them.

## 4. Baselines

| ID | Strategy | Algorithm |
| --- | --- | --- |
| B0 | No reallocation | `PROJECT_SPEC.md` §6 |
| B1 | Clinical-priority-first | `PROJECT_SPEC.md` §6 |
| B2 | Proportional | `PROJECT_SPEC.md` §6 |

- All baselines start from the common initial allocation.
- They use the same datasets, hard constraints, intra-department rule and deterministic audit as the agent.
- No baseline is claimed to be optimal.

## 5. Run Plan

1. **Generate** the primary dataset from the approved parameters and seed. All checks in `DATA_DICTIONARY.md` §4 must pass.
2. **Run the baselines** B0, B1 and B2 on the primary dataset. They are deterministic, so one run each is enough.
3. **Run the agent:** R1, then optionally R2 and R3, on the **same** primary dataset. Each is a fresh run in a run session. Because the dataset is held fixed, differences between runs isolate LLM variability.
4. **Compute metrics** for every run with the same code, and run the verification checks (Section 6).
5. **Stress variant (approved 2026-11-11):** `seed20261107_stress` is a constructed test case for the shock-cut path. An optional run on it may come later. It is **excluded from all baseline and agent comparisons** in the main evaluation and reported, if at all, separately.
6. **Robustness (approved 2026-11-07):** the deterministic baselines also run on two extra seeds (`PROJECT_SPEC.md` §10), reported as an appendix. Agent results rest on the primary dataset only, which is declared as a limitation.

## 6. Verification Checks

These checks are independent of any LLM output.

| Check | What it verifies |
| --- | --- |
| Dataset reconciliation (`DATA_DICTIONARY.md` §4.1) | Operations and registry tables agree, since they are produced independently |
| Integrity and generation constraints (`DATA_DICTIONARY.md` §4.2–4.3) | Dataset validity, including `total_beds ≤ 4 × max_beds` |
| Deterministic audit | Hard constraints, clinical violations and metrics, for every five-day period |
| Validator vs. audit cross-check | Two independent implementations of the hard constraints agree on every accepted allocation |
| Replay check | Recomputing the Bed Assignment State from the Allocation State and the registry reproduces the stored records exactly |
| Repair and baseline properties | Unit and property tests: repair is always feasible, and every baseline allocation passes the validator |
| Temporal-leak tests | No tool response contains post-day-t data or the `discharge_day` of present patients |
| Smoke test (`AGENTS.md` §2.4) | Tool whitelists, server isolation and dispatcher restrictions |

## 7. Reporting LLM Variability

With n ≤ 3 runs, no inferential statistics are claimed. For each metric, the report gives:

- The value for each run (R1–R3), with the range (min–max) and the mean.
- The baseline values, as reference lines.

Decision-level agreement between runs is also reported:

- The share of days on which the runs chose identical allocations.
- The mean L1 distance between their daily allocations.

Notable divergences are discussed qualitatively in the Reflection, using the decision explanations and the CHECKER reports.
