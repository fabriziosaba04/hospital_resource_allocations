# Reflection Log

A running record of things that went wrong, or nearly went wrong, during the project. It is source material for the final Reflection (`LIMITATIONS_AND_REFLECTION.md`) and for the Verification section of the report.

**Rule (owner, 2026-11-11):** add an entry **at the moment** something like this happens, not at the end of a session, and mention new entries in the session report. Errors by the AI assistant count as much as errors in the code or the design.

Each entry records:

- **What happened:** the error or near miss, stated plainly.
- **How it was caught:** which independent check revealed it.
- **Implication for AI-agent reliability:** what it teaches about trusting AI-generated reasoning, code or claims.
- **Decisions Log:** the related entries in `PROJECT_SPEC.md` §9.

---

## 2026-11-11

### R1. The rationale for Shock 3 was wrong (advisor error)

- **What happened:** the approved rationale for Shock 3 (beds −10 on days 23–25) was that it "hits while census is high, so relaxed no-eviction is exercised". The reasoning compared the census with the shocked pool. But a forced cut depends on the patients **carried over** from the previous day against the new pool, because new arrivals can always overflow instead. On the primary seed, only 62 patients carry over into day 23, against a pool of 86, so no cut is ever forced.
- **How it was caught:** an explicit check of the shock's stated purpose against the generated data (carried-over patients on each pool-decrease day), confirmed by the 1,000-seed Monte Carlo: P(forced cut) = 0.002 for the approved schedule. A pre-registered sweep of candidate schedules then selected nothing (best eligible: 0.52), and the threshold was **not** lowered after the fact.
- **Implication:** a plausible, approved rationale can be wrong in its mechanism. A design goal stated in prose ("this shock exercises X") must be verified quantitatively against the data. Pre-registering the selection rule kept the follow-up decision honest when the result was negative.
- **Decisions Log:** #33, #40, #41; owner decisions §11 #10–12; `LIMITATIONS_AND_REFLECTION.md` §2.

### R2. The floating-point example in Log #29 was wrong

- **What happened:** Log #29 justified exact integer arithmetic for the N1 requirement with the claim that `0.35 × 20` gives `7.000000000000001` in floating point. It does not: the result is exactly `7.0`. The underlying risk is real, but rarer than implied: 10 of the 68,921 census combinations up to 40 per level round wrong, for example (12, 0, 1): `0.2·12 + 0.6·1 = 3.0000000000000004`, so `ceil` gives 4 instead of 3.
- **How it was caught:** while writing the hand-computed N1 test, the assistant evaluated the claimed example directly. An exhaustive search then found the real failing cases.
- **Implication:** an AI assistant can state a specific technical "fact" with confidence that it has never checked. A correct decision (exact arithmetic) can rest on a false justification. Every concrete numerical claim in documentation should be executable or tested.
- **Decisions Log:** #29 (corrected), #42.

### R3. A property-test failure was a bug in the test, not in the validator

- **What happened:** the property test for `SHOCK_OVERCUT` failed. The test's mutation moved a bed into a department that had itself been cut. That only shifts the cut between departments, so the total cut does not grow and the validator was right to accept it.
- **How it was caught:** Hypothesis produced a minimal counterexample, and the assistant analysed it before changing any code. Only the test was changed.
- **Implication:** a failing test is evidence, not a verdict. An AI assistant asked to "make the tests pass" could just as easily weaken the validator. Every fix must say which side was wrong, and why.
- **Decisions Log:** #37 (environment cut path).

### R4. The validator did not compute the nurse requirement at all

- **What happened:** the owner asked for confirmation that the data validator computes the N1 requirement with its own integer implementation, separate from the generator's. In fact neither does: N1 is not stored in the datasets, so no data check uses it. It is computed in `stats.py` (descriptive statistics) and `src/environment/nurses.py`. The assistant reported this instead of confirming the assumption.
- **How it was caught:** the assistant read the code before answering.
- **Implication:** a request to "confirm" invites agreement. Both people and AI assistants should answer from the artefact, not from the premise of the question. A third, independent N1 implementation is still needed in the deterministic audit.
- **Decisions Log:** #37, #42.

### R5. Gaps in the run-session deny list

- **What happened:** hidden generation information stayed reachable until it was closed:
  - Monte Carlo outputs in `data/processed/montecarlo/` (before deny-by-default on `data/**`).
  - `tests/`, which contains the shock schedule and parameter values.
  - The `.hypothesis/` cache, which collects literals from source files.
- **How it was caught:** a real headless Claude Code session started with `.claude/run-settings.json`, whose tool results were classified from the transcript (`tests/manual/verify_run_settings.py`). A repository-wide `Grep` revealed the `tests/` and `.hypothesis/` paths. After the fixes, 16 protected reads were denied and the controls allowed.
- **Implication:** information hiding by deny-list is fragile, because new files keep appearing in unexpected places (caches, tests, analysis outputs). Deny-by-default plus an empirical check in a real session is much stronger than reasoning about paths. The dispatcher having no file tools remains the first layer.
- **Decisions Log:** #39; owner decisions §11 #8, #9, #13; `PROJECT_SPEC.md` §8.

### R6. Shock 1 is weak on the primary seed

- **What happened:** with nurse pool 33 on days 8–10, the N1 requirement on the primary seed is 36 / 33 / 34, so the shortage is only 3 / 0 / 1, while the census is low (79 / 77 / 76). There is no shortage on day 9, and no slack either.
- **How it was caught:** a per-day check of requirement against pool, requested by the owner before the freeze.
- **Implication:** Shock 1 must not be presented as a crisis in the report or in the ALLOCATOR's evaluation. Claims about what a scenario "tests" have to be checked on the actual dataset, not inferred from the parameters.
- **Decisions Log:** `PROJECT_SPEC.md` §0 (nurse checks); §10.2 (nurse-rationing regime).
