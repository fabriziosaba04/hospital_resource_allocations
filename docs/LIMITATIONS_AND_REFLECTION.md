# Limitations and Reflection

## 1. Scope and Simplifying Assumptions

## 2. Synthetic Data Limitations

- **Declared limitation (2026-11-07):** agent results rest on a single dataset (seed 20261107). Robustness checks on two extra seeds cover only the deterministic baselines.
- **Declared limitation (2026-11-11): relaxed no-eviction is not exercised in the main evaluation.** Shock 3 (beds −10 on days 23–25) forces a cut with probability 0.002 over seeds 1–1000, and not at all on the three datasets. In a pre-registered sweep (`PROJECT_SPEC.md` Decisions Log #33 and #40), no candidate schedule reached P(forced cut) ≥ 0.85; the best eligible one, −26 on days 23–25, reached 0.52. Under this demand, a reliable forced cut requires a bed loss of **about 30%** (pool 63–67 instead of 96). The threshold was not lowered after the fact, and the approved schedule was kept. The cut path (the repair rule's cut step, the intra-department cut, the validator's `SHOCK_OVERCUT`) is verified by unit, property and end-to-end tests instead, and by the constructed stress variant `seed20261107_stress` (forced 6-bed cut on day 23). That variant is a test case, not a representative draw, and is excluded from the main comparisons.

## 3. Agent Errors Identified by the CHECKER

## 4. Comparison with Baselines

- **Declared limitation (2026-11-12, owner decision): on these data the agent is not expected to beat B1 on clinical metrics.** The baseline headroom review (`EVALUATION_PLAN.md` §8) shows that B1, a simple greedy clinical-priority-first rule, is at or near the floor on A1, A2 and A3: SV_B = 0, nurse gaps of at most 2.3 nurse-days, path components of at most 4 patient-days. The evaluation therefore asks whether the LLM agent system reliably reproduces a near-optimal myopic policy, where it deviates, and whether the CHECKER catches the deviations. **The frozen data (`data-v1.0`) will not be changed to create headroom.**
- Seed 09 has no bed overflow under B1 or B2, so the robustness appendix cannot discriminate between them on bed metrics.
- B1 is optimal for A1 only day by day, given each day's holders. Optimality over the horizon is not claimed.
- **B1 on nurses (A2), measured 2026-11-14 (owner decision §11 #50).** B1 is **optimal on A1 by construction** and **greedy on nurses**: it gives each department whole nurses for its incremental need, tier 3 first (`PROJECT_SPEC.md` §6, B1 "Nurses" steps 1–3; the code matches the spec). Its gap to the best whole-number split (SV_N, summed over days):

  | Dataset | Tier 3 | Tier 2 (days > 0) | Tier 1 (days > 0) | Tier-2 gap / tier-2 need |
  | --- | --- | --- | --- | --- |
  | `seed20261107` | 0 | 1.05 (days 26, 30) | 1.2 (days 16, 26, 30) | 0.11% |
  | `seed20261108` | 0 | 2.3 (days 19, 23, 24, 27, 28) | 1.85 (days 4, 6, 12, 19, 27) | 0.22% |
  | `seed20261109` | 0 | 0 | 0.45 (day 21) | 0% |
  | HARD10 (synthetic) | 1.2 (2.1% of tier-3 need) | 1.2 | 0.75 | 1.41% |

  "Near-optimal" is therefore used **only for A2 on the frozen seeds**, where B1 is optimal at tier 3 and within 0.22% of tier-2 need. Elsewhere the wording is "optimal on A1 by construction, greedy on nurses with a measured gap of X". On HARD10, a small fixture where rounding up to whole nurses costs more, DRY2 beat B1 at every tier. On the primary seed an agent can beat B1 on A2 by at most 1.05 need units at tier 2 and 1.2 at tier 1 over the run.

## 5. Between-Run Variability of the LLM Agent

## 6. Enforcement Gaps and Residual Risks

- **Reversal detection by the CHECKER measures reading, not discovery (owner decision §11 #46, 2026-11-14).** The CHECKER is given the reference allocation and τ, computed exactly as the audit computes them (§11 #36). Its reversal recall shows whether it reads τ and applies the oldest-first matching rule correctly; it does not show that the CHECKER can find reversals on its own. This must be stated next to every reversal figure.
- **Small counts (owner decision §11 #47).** CHECKER matching figures rest on few issues (DRY2: 4 headline issues, all `nurse_gap`). They are written as counts ("4/4"), never as a rate alone.
- Run-session deny rules are a second layer and apply only to Claude Code tools; they hold only when the session starts from the project root (`./` rules). Verified 2026-11-11 (`PROJECT_SPEC.md` §8).

## 7. What Worked and What Did Not

## 8. Lessons and Future Work
