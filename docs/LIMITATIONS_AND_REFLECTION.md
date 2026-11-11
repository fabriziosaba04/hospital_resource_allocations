# Limitations and Reflection

## 1. Scope and Simplifying Assumptions

## 2. Synthetic Data Limitations

- **Declared limitation (2026-11-07):** agent results rest on a single dataset (seed 20261107). Robustness checks on two extra seeds cover only the deterministic baselines.
- **Declared limitation (2026-11-11): relaxed no-eviction is not exercised in the main evaluation.** Shock 3 (beds −10 on days 23–25) forces a cut with probability 0.002 over seeds 1–1000, and not at all on the three datasets. In a pre-registered sweep (`PROJECT_SPEC.md` Decisions Log #33 and #40), no candidate schedule reached P(forced cut) ≥ 0.85; the best eligible one, −26 on days 23–25, reached 0.52. Under this demand, a reliable forced cut requires a bed loss of **about 30%** (pool 63–67 instead of 96). The threshold was not lowered after the fact, and the approved schedule was kept. The cut path (the repair rule's cut step, the intra-department cut, the validator's `SHOCK_OVERCUT`) is verified by unit, property and end-to-end tests instead, and by the constructed stress variant `seed20261107_stress` (forced 6-bed cut on day 23). That variant is a test case, not a representative draw, and is excluded from the main comparisons.

## 3. Agent Errors Identified by the CHECKER

## 4. Comparison with Baselines

## 5. Between-Run Variability of the LLM Agent

## 6. Enforcement Gaps and Residual Risks

- Run-session deny rules are a second layer and apply only to Claude Code tools; they hold only when the session starts from the project root (`./` rules). Verified 2026-11-11 (`PROJECT_SPEC.md` §8).

## 7. What Worked and What Did Not

## 8. Lessons and Future Work
