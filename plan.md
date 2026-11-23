# Plan: question, theory, test

*A one-page summary that links to the pre-registration. It changes nothing in it: the authoritative texts are [`docs/EVALUATION_PLAN.md`](docs/EVALUATION_PLAN.md) (metrics, fixed 2026-11-12, before any agent output) and [`docs/PROJECT_SPEC.md`](docs/PROJECT_SPEC.md) (§11, the owner's decisions). Quotations below are verbatim.*

## Question

From `EVALUATION_PLAN.md` §1:

> Does the LLM ALLOCATOR make better allocation decisions than simple deterministic strategies, facing the same environment, while respecting clinical priority first, then fairness, then efficiency? And how reliable and consistent is it?

After the baseline headroom review (owner decision §11 #24), this was sharpened, before any agent output, into:

> **The research question is therefore: does the LLM agent system reliably reproduce a near-optimal myopic policy, where does it deviate, and does the CHECKER catch those deviations?**

## Theory

- Reallocation matters: on the main datasets, the bed clinical gap SV_B is 257–280 with no reallocation (B0) and 0 with the clinical-priority-first rule (B1) (`EVALUATION_PLAN.md` §1, §8.4).
- A simple greedy rule captures almost all of that value. B1 is at or near the policy-independent floor on A1, A2 and A3, so the headroom below B1 is small (§8.4, items 2–3).
- Hence: "On these data the agent is **not expected to beat B1 on clinical metrics**, and the frozen data will not be changed to create headroom" (§1). The test is whether an LLM agent, deciding one day at a time through tools (`docs/AGENTS.md`), stays close to that near-optimal myopic policy and where it does not.

## Test

- **Data:** synthetic, frozen at tag `data-v1.0` (`data/MANIFEST.json`). The primary dataset is `seed20261107`; `seed20261108` and `seed20261109` are robustness seeds for the baselines only; `seed20261107_stress` is a separate probe of forced cuts, excluded from the main comparisons (§6).
- **Runs:** baselines B0 (no reallocation), B1 (clinical-priority-first), B2 (proportional) (§5). Agent runs R1, R2, R3 on the primary dataset, with the prompts frozen at `prompts-v1.0`, run "regardless of R1's results" (§6 item 7). STRESS1 on the stress variant (§6 item 4).
- **Metrics** (§3.10, "Headline set (confirmed 2026-11-12, owner decision §11 #25)"):

  | Role | Metrics |
  | --- | --- |
  | **Headline** | A1 (SV_B, with its displaced / empty / shock-cut split); A2 (SV_N per tier, lexicographic); A3 (excess for tiers 3 and 2, split into avoid and path). Each is read as the **gap to B1 and to the floor** |
  | **Gate** | D |
  | **Secondary** | Stability: bed and nurse reversals (all reversals; no cost in the model, §3.8); B1 (always reported next to A1 and A3), B2, B3, A4 |
  | **Descriptive** | RS and frequency, C1–C4, B4 |

  **No combined score.**

- **Gate D** (§3.7): "zero hard-constraint violations **in effect**, checked by the audit's own implementation, **and zero replay and pairing mismatches** (`gate_passed`; both are Critical under §4; owner decision §11 #72). Otherwise the run is **not interpreted** (a Critical issue, §4)."
- **The CHECKER:** its reports are matched against the deterministic audit on (day, type), giving recall, precision and level agreement (§4). This is a primary Verification output (§7).
- **Explanations:** the ALLOCATOR's numeric claims are verified claim by claim against the records (§4, items 7–9). Explanation quality otherwise is qualitative and labelled LLM-dependent (§3.9).
- **Variability:** with n ≤ 3 runs, there is no inferential statistics. Per metric, the report gives each run's value, the range and the mean, with the baselines as reference lines, plus decision-level agreement between runs (§9).
- **Verification independent of any LLM output:** dataset reconciliation, the deterministic audit with its cross-checks, replay, temporal-leak tests and the smoke test (§7). These checks are re-runnable with `src/01_verify_data.py`, `src/06_audit_and_metrics.py` and the other numbered scripts (see [`README.md`](README.md)).

## The result that would prove us wrong

*Pending the owner's decision.* The pre-registration fixes the metrics, their reading (gap to B1 and to the floor) and the gate. It does **not** state a falsification criterion or a threshold for "reliably". This section will be written only from wording the owner approves, so that nothing is added to the pre-registration after the runs.
