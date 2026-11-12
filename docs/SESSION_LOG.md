# Session Log

One entry per working session, newest last. Each entry records what was achieved, the state of the repository, the ordered next steps and the questions waiting for the owner. `PROJECT_SPEC.md` §0 points to the latest entry. Decisions themselves live in `PROJECT_SPEC.md` §9 (Implementation Decisions Log) and §11 (owner decisions); errors and near misses in `REFLECTION_LOG.md`.

---

## 2026-11-12

Commits of the day: `4b54ad7` … the session-close commit (see `git log`). Tag `data-v1.0` unchanged.

### Achieved

**Milestones**

1. **Metric formulas and CHECKER severity scale fixed before any agent output** (§11 #16–#23; `EVALUATION_PLAN.md` §3–§4).
2. **Environment complete; audit, metrics and baselines complete** (Log #53–#58). B0–B2 run on all four datasets; every run passes the gate.
3. **Headline set confirmed after the headroom review** (§11 #24–#28).
4. **Milestone 2: MCP server, agent files, smoke test 22/22** (Log #61–#76), with check 5c shown live through a versioned probe agent.
5. **Pre-R1 robustness** (§11 #33; Log #79–#81): HALTED with a recorded reason, stale-lock handling, resumable idempotent writes. Tested by killing a run at 12 points and resuming; the records equal an uninterrupted run's.
6. **Dry run DRY1-SMOKE5** on the synthetic fixture with `claude-sonnet-5-5` and the R1 launch command (results below).

**Key decisions**

- Internal deadline 30 November (Log #45).
- Testing and documentation policy (`CLAUDE.md` §9.4, Log #58).
- **Framing** (§11 #24): B1, a greedy rule, is at or near the floor on A1–A3. The question is whether the LLM system reliably reproduces a near-optimal myopic policy, where it deviates, and whether the CHECKER catches the deviations. The agent is not expected to beat B1 on clinical metrics, and the data stay frozen.
- **Headline:** A1, A2 per tier, A3 tiers 3 and 2, each read as the gap to B1 and to the floor; gate D. Fairness dispersion is not promoted (§11 #25).
- **Stability secondary:** all reversals only, with the statement that reversals have no cost in the model; the occupied-reversal count was dropped (§11 #26, #32).
- **Agent visibility redesign** (§11 #29, superseding Log #6): the CHECKER is blind to the deterministic audit and gets read-only record tools plus a past-day what-if. Both what-ifs return outcomes only. The labels sit behind an off-by-default "assisted" flag.
- **Model:** `claude-sonnet-5-5` for all roles, in the run settings (§11 #31).
- **Prompt development** only on the synthetic fixture; freeze at `prompts-v1.0` before R1 (§11 #34).
- **The CHECKER's deterministic definitions match the audit's** (§11 #35, Log #84).

**Main findings**

- **Headroom** (`EVALUATION_PLAN.md` §8): SV_B is 257–280 for B0 and 0 for B1. B1's headroom above the floor is at most 2.3 nurse-days (A2) and 4 patient-days (A3 path). Bed reversals are mostly empty-bed churn (R19). Seed 09 cannot discriminate B1 from B2 on bed metrics.
- **Design error caught at prompt review** (R25): the design approved on 2026-11-07 gave both agents the evaluation's answers. The CHECKER could read the audit, and the what-if labelled violations (and showed the A2 tier gaps).
- **Dry run** (below): the plumbing, the dispatcher, the ALLOCATOR's process and the resume-safe records work. The CHECKER's matching against the audit shows recall 0.43, all of it a reversal counting and reference issue (R28). The fixture contained no clinical-priority case to detect (R29).

### Dry run DRY1-SMOKE5: results for the owner's review

Setup: synthetic SMOKE5 fixture (5 days, 4 departments, pool 14 beds, 12 on day 3; 5 nurses; mean census 20.6). Labels flag off. Launched with `python -m src.mcp_server.launch`, one launch, no interruption. The models observed in the transcript equal the configured ones (`claude-sonnet-5-5`, main session and subagents). Final state FINISHED; consistency check clean. Records: `results/allocations/DRY1-SMOKE5/`; report: `results/evaluations/DRY1-SMOKE5/run_report.json`.

| Day | Accepted on attempt | What-if calls (validate) | Beds IM / CA / NE / OR | Nurses IM / CA / NE / OR | Audit issues | Wall clock | ALLOCATOR tokens |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 1 | 3 (0) | 4 / 5 / 2 / 3 | 1 / 3 / 0 / 1 | none | 37 s | 16,316 |
| 2 | 1 | 3 (0) | 4 / 5 / 3 / 2 | 1 / 2 / 1 / 1 | 2 × nurses_reversal (Minor) | 36 s | 17,873 |
| 3 | 1 | 3 (0) | 2 / 5 / 3 / 2 | 1 / 2 / 1 / 1 | none | 34 s | 19,399 |
| 4 | 1 | 2 (0) | 5 / 2 / 3 / 4 | 2 / 1 / 0 / 2 | 2 × beds_reversal (Minor) | 34 s | 19,525 |
| 5 | 1 | 3 (1) | 5 / 1 / 5 / 3 | 2 / 0 / 2 / 1 | 1 × beds_reversal, 2 × nurses_reversal (Minor) | 134 s (with CHECKER) | 22,098 |

- **Hard constraints:** no rejected submission, no repair day, no hard-constraint error.
- **Clinical:** no bed pair, no nurse gap and no F1 inversion on any day. The fixture never created one (R29).
- **CHECKER report** (day 5, 4 issues, CHECKER 44,195 tokens, 99 s):
  - nurses_reversal on days 2 and 5, and beds_reversal on day 4, each reported **once for both departments** of a round trip;
  - one explanation_inaccuracy (Moderate): day-1 alternative C lists L3 shortages 0.6 + 0.6 + 0.6 but states the total as 1.2. **Verified in the decision record.** It did not affect the choice: corrected, C totals 1.8, worse than the chosen B at 1.4.

  The CHECKER also wrote that it could not compute the reference allocation for the day-4 reversal exactly.
- **CHECKER versus audit** (deterministic, `checker_matching.py`): 7 audit issues, 3 CHECKER issues of matchable types, 3 matched.
  - **recall 0.43, precision 1.0, level agreement 1.0**;
  - per type: nurses_reversal 2 of 4, beds_reversal 1 of 3;
  - every miss is the second department of a round trip, or the day-5 bed reversal that depends on the reference allocation (R28).
- **Cost and time:** $0.78 (list price, `costBasis: list`), 295 s in total. ALLOCATOR about 30 s and 16–22k tokens per day, rising by about 1.4k tokens a day as the decision history grows. CHECKER 99 s and 44k tokens.
- **Extrapolation to 30 days (rough):**
  - At fixture scale, ALLOCATOR tokens grow to about 57k on day 30, about 1.1M in total, plus about 6 × 45–60k for the CHECKER. That is about 10 times the dry run: about $8 and 30–40 min.
  - The primary dataset has about 4.3 times the census (87.8 against 20.6), and the overflow queue and what-if outputs grow with it, so expect roughly 2–3 times that: **about $15–25 at list price and 45–90 min**.
  - On a subscription this is usage-limit consumption, not dollars. A 30-day run may well be interrupted, which is why the resume path was built and tested.
- **Unexpected in the transcripts:**
  1. The dispatcher launches subagents in the background and waits for their completion notices; it worked every time.
  2. The ALLOCATOR called `validate_allocation` only once in 5 days. It relied on the what-if's hard-constraint result, which is the same validator.
  3. The CHECKER merged the two departments of each reversal into one issue, against the stated counting unit.
  4. No tool errors, no rejected submissions, no off-protocol dispatcher action.

### State

- **Built:** data generation and validation; environment; deterministic audit, metrics, baselines and headroom; MCP server (state machine, record store, ANALYZER, three role servers), agent files, launcher, consistency check, run report, CHECKER matching; smoke test and run-settings verification scripts.
- **Frozen or tagged:** data at `data-v1.0` (manifest OK). Metric formulas, severity scale and headline set fixed (§11 #16–#28). **Prompts not frozen; no `prompts-v1.0` tag yet.**
- **Tests:** fast suite and full suite pass at the session-close commit (see the commit message). Manual: smoke test 22/22; run-settings verification passed (19 protected reads denied).
- **No run on frozen data.** No ACTIVE_RUN pointer is set (the dry run's pointer was removed at session close).
- **Still open:** the owner's dry-run review and the questions below; visualization (deferred).

### Next session

1. **Owner reviews this dry run** and answers the open questions below.
2. Apply the decisions, on the synthetic fixture only (§11 #34). If prompts or definitions change, run another dry run (with the harder fixture, if approved) and review it.
3. **Tag `prompts-v1.0`** (prompts and run settings frozen).
4. Pre-R1 checks: `verify_run_settings.py`, the smoke test, the full suite, the manifest check.
5. **R1** on `seed20261107` (`init_run --dataset seed20261107 --run-id R1`, then `launch`; resume with the same command if interrupted), then the run report and the metrics.
6. R2, R3, the stress run (reported separately), the robustness appendix, visualizations and the report, by 30 November.

### Open questions for the owner

1. **Reversal matching (R28).** The CHECKER cannot compute the reference allocation, and it merged round-trip departments. Options:
   - (a) expose the reference allocation (and τ) in the CHECKER's `get_allocation_state`. It is derived from the records, but it is an audit intermediate;
   - (b) define reversals for both the audit and the CHECKER on the plain day-to-day change, excluding pool-change days. That changes an approved metric;
   - (c) leave it, and report reversal matching separately as a known definitional limit.

   *Recommendation: (a), with the counting unit restated in the prompt as "two issues for a round trip between two departments".*
2. **Harder synthetic fixture (R29)** for the next dry run: more patients and pressure, a pool cut that forces a shock cut, and nurse rationing, so that the CHECKER faces clinical-priority cases. *Recommendation: yes.* It is synthetic, so it stays within §11 #34.
3. **Severity-scale wording vs. the audit.** The approved scale says "a rejected submission later corrected the same day" is Moderate; the audit (and now the prompt) counts **every** rejected submission as Moderate, and a failure day additionally as Major. *Recommendation: align `EVALUATION_PLAN.md` §4 to the audit.*
4. **Unobservable Minor item.** "A modification submitted without a `simulate_allocation` call" cannot be detected by the audit or the CHECKER, because what-if calls are not recorded. *Recommendation: drop it from the scale, or record what-if calls in the workflow log (visible to the CHECKER through its tools) if the owner wants it measured.*
5. **Cost.** At the extrapolated $15–25 (list) and 45–90 min per 30-day run, are R1–R3 plus the stress run (four runs) acceptable, or should R2/R3 be conditional on R1?
