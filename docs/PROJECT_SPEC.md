# Project Specification

This is the consolidated technical design of the Hospital Resource Allocation Agent, based on the conceptual design frozen on 2026-11-07.

| Topic | Authoritative document |
| --- | --- |
| Principles, hard constraints and data model | [`CLAUDE.md`](../CLAUDE.md) |
| Agent roles, permissions and workflow | [`AGENTS.md`](AGENTS.md) |
| Dataset fields | [`DATA_DICTIONARY.md`](DATA_DICTIONARY.md) |
| Metrics and run plan | [`EVALUATION_PLAN.md`](EVALUATION_PLAN.md) |

This document specifies **how** those are implemented, and does not restate them. Implementation-level choices are listed in the [Implementation Decisions Log](#9-implementation-decisions-log).

## 0. Current Status and Next Step

*Last updated 2026-11-12. A new session should read this section first, then `CLAUDE.md`, `AGENTS.md` and `docs/REFLECTION_LOG.md`. This section is meant to be enough to resume from the repository alone.*

### Timeline

- **External deadline:** "early December" (not yet confirmed by the course, as of 2026-11-12).
- **Internal deadline: 30 November 2026.** Plan against this date (Log #45).
- The extra time goes to **evaluation depth**: agent runs R2 and R3, the stress-variant run, and the robustness appendix. It is **not** for new features. The order of the next steps below is unchanged.

### Resume checklist

```bash
uv sync                                                        # environment (Python >= 3.12)
uv run pytest -q                                               # fast suite (slow tests excluded); full: -m "slow or not slow" (CLAUDE.md §9.4)
uv run python -m src.data_generation.manifest --verify         # expect "manifest OK" (add --regenerate for a byte-exact rebuild)
git log --oneline --decorate                                   # expect tag data-v1.0 on 42b39ed, with later commits on top
```

### Working rules in force

- **Escalation** (`CLAUDE.md` §9.2): decide implementation-level choices and log them in §9; escalate anything touching principles, agent visibility, metrics or evaluation design, or data generation, with a recommendation.
- **Data are frozen** at git tag `data-v1.0` (`CLAUDE.md` §9.3, Log #44). Any change to data needs a new tag and the owner's approval. The manifest check must pass before any run.
- **Reflection log:** when something goes wrong or nearly goes wrong, add an entry to `docs/REFLECTION_LOG.md` **at that moment**, and mention it in the session report.
- **Nothing in `src/environment/`, `src/evaluation/` or `src/mcp_server/` may embed generation parameters.** They are hidden from agents (§8, Log #40).
- **N1 must use exact arithmetic** everywhere (Log #29, #42). Floating-point `ceil` is wrong on real census combinations.
- **Never run an agent run from a development session** (`CLAUDE.md` §9.1). Run sessions start from the project root (§8).

### Where things stand

| Area | State | Where |
| --- | --- | --- |
| Conceptual design | Frozen 2026-11-07 | `CLAUDE.md` §9.3, §10 |
| Data generator and 19 validation checks | Done, tested | `src/data_generation/`, `tests/test_data_generation.py` |
| Datasets | Frozen (`data-v1.0`): `seed20261107` (primary: agent runs and baselines); `seed20261108`, `seed20261109` (robustness: baselines only); `seed20261107_stress` (constructed test case: forced 6-bed cut on day 23; **excluded from all main comparisons**) | `data/`, `data/MANIFEST.json`, `DATA_DICTIONARY.md` §5 |
| Monte Carlo (seeds 1–1000) | Done: reference ranges, per-day bands (PNG and CSV), Shock 3 sweep, imbalance metric | `data/processed/montecarlo/`; `src/data_generation/montecarlo.py`, `mc_analysis.py` |
| Shock 3 | Approved schedule kept (beds −10, days 23–25). It almost never forces a cut (P = 0.002); a reliable cut would need about a 30% bed loss. Negative result recorded | Log #33, #40; `LIMITATIONS_AND_REFLECTION.md` §2 |
| Environment, cut path | Done, tested: largest remainder (§5.1), bed assignment (§5.3), N1 requirement, validator (§5.5), repair rule (§5.7) | `src/environment/`; `tests/test_environment_cut_path.py`, `tests/test_nurse_requirement.py` |
| Environment, rest | Done, tested (2026-11-12): initial allocation (§5.2), nurse coverage C1 and tier maxima (§5.4), bed pairing detector, what-if (§5.6) | `src/environment/`; `tests/test_environment_rest.py` |
| Run-session restrictions | `.claude/run-settings.json`: deny-by-default on `data/**`, plus `docs/`, generator code, `tests/`, `.hypothesis/` and (2026-11-12) `results/**`; `enabledMcpjsonServers` and allow rules for the run's own servers only (Log #64). Re-verified 2026-11-12: 19 protected reads denied, controls allowed | §8; `tests/manual/verify_run_settings.py` |
| Deterministic audit, metrics, baselines | Done, tested (2026-11-12). B0–B2 run on all four datasets; every run passes the gate. Headroom reviewed by the owner; headline set confirmed (§11 #24–#28) | `src/evaluation/`; `tests/test_evaluation.py`; `uv run python -m src.evaluation`; `results/` |
| MCP server, state machine, agent files, prompts | **Built 2026-11-12** (milestone 2): record store, state machine, ANALYZER, three role servers, `init_run`, `.mcp.json`, dispatcher/allocator/checker files. Unit tests on a synthetic fixture; smoke test 13/14 checks pass (Log #70; check 5c not shown live, R22). **ALLOCATOR and CHECKER prompts are drafts awaiting owner review**; no run on frozen data | `src/mcp_server/`, `.claude/agents/`, `src/agent/`; `tests/test_mcp_server.py`; `tests/manual/smoke_test.py` |
| Documentation | Decisions Log #1–70, owner decisions §11 #1–28, reflection log R1–R22 | `docs/` |

**Key data facts (primary seed, approved schedule):**

- Mean census 87.8 (range 73–102); census exceeds the bed pool on 5 days.
- The nurse requirement exceeds the pool on 17 of 30 days. This rationing regime is deliberate (§10.2).
- The Shock 1 shortage is only 3 / 0 / 1 on days 8–10 (REFLECTION_LOG R6), so it must not be presented as a crisis.
- Demand exceeds `max_beds` twice (Cardiology on day 17, Internal Medicine on day 21). That overflow is structural and is inside the policy-independent floor of A3 (`EVALUATION_PLAN.md` §3.3).

### Still open (owner decisions pending)

- **The headline set** is fixed provisionally (`EVALUATION_PLAN.md` §3.10) and is confirmed only after the owner reviews the baseline headroom (`EVALUATION_PLAN.md` §8). Open point from that review: bed reversals are dominated by empty-bed churn (§8.4 finding 4, REFLECTION_LOG R19).
- **Visualization tools and design** (deferred; not needed before the first run).

Metric formulas and the CHECKER severity scale were **fixed on 2026-11-12, before any agent output** (§11 #16–#23, `EVALUATION_PLAN.md` §3–§4).

### Next steps (order set by the owner, 2026-11-11; updated 2026-11-12)

1. **Done 2026-11-12:** the metric formulas and the severity scale were proposed and fixed (§11 #16–#23). The original wording of this step follows. **Write proposals for the owner, to be fixed before any agent output is seen.** These are escalation areas 1 and 3: propose, do not decide.
   - **(a) Final metric formulas.** Start from `EVALUATION_PLAN.md` §3 and §3.6. For each metric give the exact formula, the unit, how it is computed from the records (Bed Assignment State, Allocation State) and its direction (lower or higher is better). Propose which metrics are headline and which secondary. Include:
     - the pairing rule for clinical violations (§3.1);
     - the empty-bed violation type (severity = k, §11 #3);
     - the fairness metrics F2, per level;
     - the stability metrics, with a concrete reversal window;
     - how structural outcomes are netted out.
   - **(b) CHECKER severity scale.** Clinical violations keep severity = level difference (`CLAUDE.md` §10.G). Propose a scale for everything else (hard-constraint violations, concerns, improvement opportunities, explanation inaccuracies), with objective criteria for each category.
   - Record the owner's decisions in §11, and update `EVALUATION_PLAN.md`, `AGENTS.md` §6 and `CLAUDE.md` §10.M before moving on.
2. **Complete `src/environment/`.** Pure functions only, each with tests in the style of `tests/test_environment_cut_path.py`:
   - initial allocation (§5.2): beds `LR(P_B(1), census_d(1), caps = max_beds)`; nurses `LR(P_N(1), requirement_d(1))`;
   - nurse coverage C1 (§5.4);
   - the clinical-violation detector (bed, shock-cut and nurse types, `CLAUDE.md` §10.G);
   - what-if (§5.6).
3. **`src/evaluation/`:**
   - the deterministic audit, with its **own** hard-constraint and N1 implementations, cross-tested against `src/environment/` (§1, Log #17);
   - the metrics, using the formulas the owner fixes in step 1;
   - the baselines B0, B1 and B2 (§6), run on the three seeds **and the stress variant** through the same environment functions, writing records in the §4 layout;
   - **report the headroom table (`EVALUATION_PLAN.md` §8) to the owner before starting step 4** (§11 #23).
4. **Done 2026-11-12 except the owner's prompt review and R1** (Log #61–#70). **Minimal MCP path to a first end-to-end run:**
   - the state machine and record store (§3–4);
   - the orchestration, allocator and checker role servers (§2);
   - `.mcp.json` and the dispatcher, allocator and checker agent files (§8), with `tools` and frontmatter syntax checked against current Claude Code documentation;
   - the smoke test (`AGENTS.md` §2.4);
   - the ALLOCATOR and CHECKER prompts, **reviewed by the owner before the first run**;
   - then run R1 on `seed20261107` in a run session.
5. **Polish** (visualizations, runs R2 and R3, the stress run — planned since 2026-11-12, §11 #22 — the report) **only after the first run works**. The time to the internal deadline (30 November) is reserved for evaluation depth within this step, not for new features (Log #45).

### Approved by the owner

- 2026-11-07: the numerical parameters (§10), escalation decisions §11 #1–5, the repair rule and baselines (§5.7, §6) and the session setup (§8).
- 2026-11-11: decisions §11 #6–15 (LOS interpretation, `external_event` semantics, deny rules, Shock 3 kept, stress variant, data freeze, work order).
- 2026-11-12: decisions §11 #16–23 (metric formulas, framing, headline set, judgment items, severity scale, CHECKER matching, stress run, work order); internal deadline 30 November (Log #45).

## 1. Code Layout

```text
src/
├── data_generation/     generator, validation and reconciliation checks
├── environment/         deterministic rules: allocation helpers, initial allocation, bed assignment,
│                        nurse coverage, validator, what-if, repair rule (pure functions, no I/O)
├── mcp_server/          role instances, state machine, record store (all disk I/O)
├── agent/               subagent system prompts and fixed dispatch templates
├── evaluation/          deterministic audit, metrics, baseline runner
└── utils/               shared helpers
```

- **Pure core:** `src/environment/` contains pure functions. The MCP server and the baseline runner both call the same code, which guarantees the "same environment" requirement (`CLAUDE.md` §10.L).
- **Audit independence:** the deterministic audit (`src/evaluation/`) re-checks hard constraints with its **own** implementation, not the validator's. The two are cross-checked in tests.

## 2. MCP Server Instances and Tools

One entry point, `python -m src.mcp_server --role <orchestration|allocator|checker>`, is run with `uv` over stdio. Each role registers only its own tools.

- The **orchestration** instance is configured in `.mcp.json`.
- The **allocator** and **checker** instances are defined inline in their subagent files (`AGENTS.md` §2).

### 2.1 Orchestration instance (dispatcher only)

| Tool | Allowed in phase | Effect |
| --- | --- | --- |
| `get_workflow_status()` | Any | Returns the run ID, current day, phase and expected next action. It returns **no hospital data**. |
| `advance_day()` | `READY` (before day 1) or `CLOSED` | Moves to day t+1 and runs `run_analyzer`. On day 1 it first applies the initial allocation and its bed assignment. Moves to `ALLOCATION`. |
| `end_allocation_phase()` | `ALLOCATION` | If no decision was accepted, applies the repair rule and records an ALLOCATOR failure. Writes the Bed Assignment State. On days with t mod 5 = 0 it runs the deterministic audit and moves to `AUDIT`; otherwise it moves to `READY_TO_CLOSE`. |
| `close_day()` | `READY_TO_CLOSE` or `AUDIT` | In `AUDIT` with no LLM report, it records the LLM-layer failure. Writes the workflow record. Moves to `CLOSED`, or to `FINISHED` if t = H. |

### 2.2 Allocator instance (ALLOCATOR subagent only)

All tools are allowed only in phase `ALLOCATION`.

| Tool | Returns or does |
| --- | --- |
| `get_observed_state()` | The day-t Observed State: pools, External Changes, and per department: arrivals, discharges, census by level, occupied beds O_d(t), N1 requirement, and changes detected by the ANALYZER |
| `get_allocation_state()` | The allocation currently in effect (B_d, N_d) and its source (ALLOCATOR, initial rule or repair rule) |
| `get_decision_history()` | All previous decision records, including attempts and validation outcomes |
| `get_overflow_queue()` | Patients currently in overflow: `patient_id`, `department`, `complexity`, `arrival_day`, `days_waiting = t − arrival_day`. It **never returns `discharge_day`**. |
| `simulate_allocation(beds, nurses)` | Day-t outcomes of a proposal: overflow by department and level, nurse coverage and shortage by level, clinical priority violations and the validator result. **No writes.** |
| `validate_allocation(beds, nurses)` | The validator result only. Does not count as an attempt. |
| `submit_decision(beds, nurses, explanation)` | Validates the proposal. If valid, it records the decision, updates the Allocation State and closes submissions for the day; otherwise it records a rejected attempt and returns the reasons. Accepted at most once per day, and at most N attempts. |

`explanation` is structured with the six fields of `CLAUDE.md` §3.6: `situation`, `information_used`, `alternatives`, `reasons`, `tradeoffs`, `uncertainty`.

### 2.3 Checker instance (CHECKER subagent only)

All tools are allowed only in phase `AUDIT`. `period` is `{from_day, to_day}` with `to_day ≤ t`.

| Tool | Returns or does |
| --- | --- |
| `get_deterministic_audit(period)` | The stored Deterministic Audit Record |
| `get_decision_history(period)` | Decisions, explanations and attempts |
| `get_observed_state(period)` | Observed States for the period |
| `submit_validation_report(report)` | Appends the report to the Validation History. Accepted once per audit. |

`report` contains `period`, `checked` (what was examined), `issues` and `summary`. Each issue has the fields listed in `AGENTS.md` §6, plus a `category` of `violation`, `concern` or `improvement`.

## 3. State Machine

```text
READY ─advance_day─▶ ALLOCATION ─end_allocation_phase─▶ READY_TO_CLOSE ─close_day─▶ CLOSED ─advance_day─▶ …
                                        │ (t mod 5 = 0)                       ▲
                                        └────────────▶ AUDIT ─close_day───────┘
CLOSED on day H ─▶ FINISHED          any unrecoverable error ─▶ HALTED (reason recorded)
```

- The state lives in `state.json` in the run directory. Every tool call **re-reads it from disk** (no caching), checks the phase and updates it with an atomic replace.
- A call in the wrong phase is rejected with an error naming the expected action, and the rejection is logged.
- A run is resumed by starting a new run session. `get_workflow_status` shows where to continue.
- **Run initialisation** happens in a development session, with `python -m src.mcp_server.init_run --dataset <dataset_id>`. It does four things:
  1. Creates the run directory.
  2. Writes `run_manifest.json` (run ID, dataset ID, N, code version, start time).
  3. Sets the state to `READY`.
  4. Points `results/allocations/ACTIVE_RUN` to the run.

## 4. Records and Storage

Writers and readers are defined in `AGENTS.md` §3.

**Common rules:**

- Every line carries `run_id`, `day`, `writer`, `created_at` and a reference to its inputs.
- Files are append-only JSON Lines, written by appending complete lines.
- One `state.json` per run, replaced atomically through a temporary file.
- Phases make access sequential. A lock file guards each write against accidental concurrency.

| Record | File |
| --- | --- |
| Observed State | `results/allocations/<run_id>/observed_state.jsonl` |
| Allocation State | `results/allocations/<run_id>/allocation_state.jsonl` |
| Decision History, including every attempt | `results/allocations/<run_id>/decision_history.jsonl` |
| Bed Assignment State | `results/allocations/<run_id>/bed_assignment_state.jsonl`. On day 1 there is one line per stage: `initial` and `final`. |
| Workflow records | `results/allocations/<run_id>/workflow.jsonl` |
| Deterministic Audit Record | `results/evaluations/<run_id>/deterministic_audit.jsonl` |
| Validation History | `results/evaluations/<run_id>/validation_history.jsonl` |
| Run metrics (computed after the run) | `results/evaluations/<run_id>/metrics.json` |

Baseline runs use the same layout, with run IDs such as `B1-<dataset_id>`.

## 5. Environment Component

These are pure functions in `src/environment/`. Departments are always iterated in the fixed order `internal_medicine`, `cardiology`, `neurology`, `orthopedics`.

### 5.1 Largest remainder: `LR(total, weights, caps=None)`

1. Compute the quotas `q_d = total · w_d / Σw`. If Σw = 0, use equal weights.
2. Take `⌊q_d⌋`, capped at `cap_d`.
3. Give the remaining units one at a time to the largest fractional parts among departments below their cap. Ties go in department order.
4. If capped departments leave units unplaced, redistribute them over the uncapped departments with the same procedure.
5. Fail only if Σcap < total.

### 5.2 Initial allocation (day 1)

- **Beds:** `B_d(1) = LR(P_B(1), census_d(1), caps = max_beds)`.
- **Nurses:** `N_d(1) = LR(P_N(1), requirement_d(1))`, in proportion to the N1 requirement (approved, Section 11).

The bed assignment (Section 5.3) then runs, with no prior holders.

### 5.3 Intra-department bed assignment

For each department, after the allocation for day t takes effect:

1. **Holders:** patients who held a bed in d at the end of t−1 and are still present on t. On day 1 there are no holders before the initial pass.
2. **Shock cut:** if `B_d < |holders|`, remove holders ordered by (complexity ascending, `arrival_day` descending, `patient_id` descending) until `|holders| = B_d`. The removed patients move to overflow.
3. **Free beds:** `free = B_d − |holders|`. Assign them to non-holders in d, ordered by (complexity descending, `arrival_day` ascending, `patient_id` ascending).
4. **Output:** one Bed Assignment State entry per present patient, either `in_bed` or `overflow`.

### 5.4 Nurse coverage (C1)

For department d:

- `need_{k,d} = w_k · n_{k,d}`, where `n_{k,d}` counts all present level-k patients, including overflow.
- `requirement_d = ⌈Σ_k need_{k,d}⌉`.
- Coverage takes `N_d` and covers L3, then L2, then L1: `covered_{k,d} = min(need_{k,d}, remaining)`.
- `shortage_{k,d} = need_{k,d} − covered_{k,d}`. The shortage therefore falls on the lowest levels first.

### 5.5 Validator

The validator checks the hard constraints of `CLAUDE.md` §10.E against P_B(t), P_N(t), `max_beds` and O_d(t). It returns a list of violations, each with a code (`CONSERVATION_BEDS`, `CONSERVATION_NURSES`, `BOUNDS`, `INTEGRALITY`, `EVICTION`, `SHOCK_OVERCUT`) and a message. An empty list means the proposal is valid.

### 5.6 What-if

The what-if applies Sections 5.3 and 5.4 to a proposal on day t, in memory. It reuses the audit's clinical-violation detector and returns the validator result. It never writes.

### 5.7 Repair rule

The reference is the allocation in effect at the end of t−1. On day 1, that is the initial allocation.

**Nurses.** Let `Δ = P_N(t) − Σ N_d`.

- If Δ ≥ 0: `N_d += LR(Δ, N_d)`. If every N_d is 0, the weights are the N1 requirement.
- If Δ < 0: `N_d −= LR(|Δ|, N_d, caps = N_d)`.

**Beds.** Let `Δ = P_B(t) − Σ B_d`.

- If Δ > 0: `B_d += LR(Δ, B_d, caps = max_beds − B_d)`.
- If Δ < 0, with `free_d = B_d − O_d(t)`:
  1. Let `r = min(|Δ|, Σ free_d)`. Set `B_d −= LR(r, free_d, caps = free_d)`.
  2. Let `c = |Δ| − r`. If c > 0, select c occupied beds hospital-wide, ordered by (complexity ascending, `arrival_day` descending, `patient_id` descending), and decrement B_d for each selected patient's department.
- If Δ = 0: no change.

**Properties.** The result always satisfies conservation. It also satisfies relaxed no-eviction, because `c = Σ O_d − P_B(t)` exactly when cuts are needed. The rule halts only if `Σ cap < Δ`, which the generation constraint `total_beds ≤ 4 × max_beds` excludes.

## 6. Baseline Implementations

All baselines are deterministic. They run through the same environment functions and the same day sequence, without MCP and without an LLM. They write the same records with `writer = <baseline>`, so the same audit and metrics apply. The rules are agreed in `CLAUDE.md` §10.L; the algorithms are below.

### B0: No reallocation

Apply the repair rule (Section 5.7) every day, starting from the initial allocation.

### B1: Clinical-priority-first

**Beds:**

1. Set `B_d = O_d(t)`.
2. If `Σ O_d > P_B(t)`, apply the cut step of Section 5.7 and stop.
3. Otherwise, let `M = P_B(t) − Σ O_d`. Order all present non-holders hospital-wide by (complexity descending, `arrival_day` ascending, `patient_id` ascending).
4. Give one bed to each patient's department in that order while M > 0, skipping departments at the cap.
5. Split any leftover M with `LR(M, census_d, caps = max_beds − B_d)`.

**Nurses:**

1. For k = 3, 2, 1, compute the incremental integer need `inc_{k,d} = ⌈Σ_{j≥k} need_{j,d}⌉ − ⌈Σ_{j>k} need_{j,d}⌉`.
2. If `Σ_d inc_{k,d}` is no more than the nurses remaining, allocate all of it. Otherwise allocate `LR(remaining, inc_{k,d}, caps = inc_{k,d})` and stop.
3. Split any leftover with `LR(left, requirement_d)`.

### B2: Proportional

**Beds:**

1. Compute the target `T_d = LR(P_B(t), census_d, caps = max_beds)`.
2. Set floors `F_d = O_d(t)`, after the Section 5.7 cut if `Σ O_d > P_B(t)`.
3. Let `R = P_B(t) − Σ F_d` and `u_d = max(0, T_d − F_d)`.
4. Set `B_d = F_d + LR(R, u_d, caps = max_beds − F_d)`. If Σu = 0, use census as the weights.

**Nurses:** `N_d = LR(P_N(t), requirement_d)`.

## 7. Data Generation Pipeline

`python -m src.data_generation --config <generation_config> --env <environment_config> --seed <s>` runs four steps:

1. **Simulate** days `−burn_in+1 … H` in within-day order: discharges, then arrivals. Arrivals are Poisson(λ_d(t)). Complexity is drawn from the department mix, and length of stay from the level's distribution. Pools come from the base values plus the shock schedule.
2. **Count independently.** While simulating, maintain counters for arrivals, discharges and census by department and level. Write `department_demand_daily` from these counters, **not** by querying the registry. This makes reconciliation a genuine check.
3. **Write** the three CSV tables and both configs to the locations in `DATA_DICTIONARY.md` §5.
4. **Validate** with every check in `DATA_DICTIONARY.md` §4, and write `validation_report.json`. A dataset that fails any check is rejected.

## 8. Development and Run Sessions

The rules are in `CLAUDE.md` §9.1. This is the setup:

| File | Content |
| --- | --- |
| `.mcp.json` | The `orchestration` server only: `uv run python -m src.mcp_server --role orchestration` |
| `.claude/agents/dispatcher.md` | `tools: mcp__orchestration__*, Agent(allocator, checker)`. Its body instructs it to follow `get_workflow_status`, use only the fixed templates in `src/agent/`, and exercise no judgement. |
| `.claude/agents/allocator.md` | `tools: mcp__allocator__*`, with inline `mcpServers: allocator` (stdio, `--role allocator`). Its body is the ALLOCATOR prompt. |
| `.claude/agents/checker.md` | `tools: mcp__checker__*`, with inline `mcpServers: checker` (stdio, `--role checker`). Its body is the CHECKER prompt. |
| `.claude/run-settings.json` | `permissions.deny`: `Read(./data/**)`, `Edit(./data/**)`, `Read(./docs/**)`, `Read(./src/data_generation/**)`, `Read(./tests/**)`, `Read(./.hypothesis/**)`, `Edit(./results/**)`. **Deny-by-default on `data/**`** (Section 11, #9): agents reach data only through the MCP server, which is a Python process and unaffected by the deny rules. The `docs/` and generator rules contain the hidden generation parameters (Section 11, #8). |

- **Starting a run session:** `claude --agent dispatcher --settings .claude/run-settings.json`, **from the project root**. In a `--settings` file, a `./path` rule resolves against the current directory, and a `/path` rule against the settings file's own directory (`.claude/`). The rules therefore use `./` and hold only when the session starts at the root (Claude Code permissions documentation, checked 2026-11-11).
- **Verification of the deny rules (2026-11-11):** `tests/manual/verify_run_settings.py` runs a headless session with the run settings and classifies every tool result from the transcript. Reads of `patient_registry` (all three seeds), `generation_config` (two seeds), `environment_config`, the demand table, both Monte Carlo files, `docs/PROJECT_SPEC.md` and the generator config were all **denied**. Reads of `README.md` and `src/environment/validator.py` were allowed, as controls. `Glob` over `data/**` and `**/generation_config.json` returned no files, `Grep` on `data` was denied, and no leak marker appeared in any result. The record is `results/evaluations/run_settings_verification.json`. **Re-verified after adding `tests/**` and `.hypothesis/**` (Section 11, #13):** 16 protected reads denied (the earlier ones plus the stress config and data, two test files and a `.hypothesis` constants file); both controls allowed. Repository-wide Grep for `arrival_rates`, `cv_continuous` and `discharge_day`, and Glob for `**/*stress*`, return only `CLAUDE.md` (which names `discharge_day` as a concept) and the verification record itself (search patterns, no values). **Remaining exposure:** `src/data_generation/mc_analysis.py` is denied, but `src/environment/` and `src/evaluation/` must never embed generation parameters.
- **Defence in depth:** the dispatcher has no Read or Edit tools, so the deny rules are a second layer.
- **Dispatch templates** are constant strings, for example "Make today's allocation decision using your tools." They contain no data.
- **`omitClaudeMd: true` in `allocator.md` and `checker.md`** (approved, Section 11). Subagents load `CLAUDE.md` by default, and it describes the generator design. The principles each subagent needs are restated in its prompt, which must stay consistent with `CLAUDE.md`. The owner reviews both prompts before the first run.
- The dispatcher still loads `CLAUDE.md`, because `omitClaudeMd` is ignored for a main-session agent. This is harmless, since it sends only fixed templates with no data.

## 9. Implementation Decisions Log

| # | Date | Choice | Alternatives | Rationale |
| --- | --- | --- | --- | --- |
| 1 | 2026-11-07 | Shared deterministic rules in a new `src/environment/` (pure functions), used by the server and the baselines | Rules inside `src/mcp_server/`; duplicated logic in baselines | One implementation guarantees the agent and baselines face the same environment |
| 2 | 2026-11-07 | Server in `src/mcp_server/`, one entry point with `--role` | Three separate server packages | One codebase, so the roles differ only in their registered tools |
| 3 | 2026-11-07 | Server names `orchestration`, `allocator`, `checker` | Prefixed names such as `hra-…` | Short, with no `.`, `__` or trailing `_`, so tool-name matching is unambiguous |
| 4 | 2026-11-07 | Orchestration tools `advance_day`, `end_allocation_phase`, `close_day`, `get_workflow_status` | Automatic audit triggered inside `submit_decision`; a separate `start_audit` tool | An explicit phase end guarantees that repair, bed assignment and the deterministic audit always run, independently of the LLM |
| 5 | 2026-11-07 | LLM CHECKER failure recorded automatically by `close_day`; no retry | Retry the CHECKER; a dispatcher-reported failure | Never blocking, no dispatcher judgement, and the deterministic layer already ran |
| 6 | 2026-11-07 | Tool renamed to `get_deterministic_audit` | `run_deterministic_audit` | The audit already ran, so the tool only reads (approved by the owner) |
| 7 | 2026-11-07 | Agent and checker tools usable only in their own phase | Read tools usable in any phase | Enforces order and the temporal rule at the tool level |
| 8 | 2026-11-07 | Records as append-only JSONL, plus atomic-replace `state.json` and a lock file | SQLite; one file per day | Human-readable, diff-friendly, simple to audit, and safe across processes |
| 9 | 2026-11-07 | No caching: every call re-reads state from disk | In-memory state per instance | Several processes share state, so disk is the single source of truth |
| 10 | 2026-11-07 | Run records in `results/allocations/<run_id>/`, audits and reports in `results/evaluations/<run_id>/`, active-run pointer file | A new `results/runs/` tree | Uses the approved structure without new top-level folders |
| 11 | 2026-11-07 | Input tables as CSV, configs as JSON, under `data/raw/` and `data/metadata/` per `dataset_id` | Parquet; a single JSON file | Readable and tool-agnostic, and small enough that CSV is sufficient |
| 12 | 2026-11-07 | Department codes in snake_case, with a fixed order `internal_medicine`, `cardiology`, `neurology`, `orthopedics` for all ties | Alphabetical; random | Deterministic and readable |
| 13 | 2026-11-07 | `patient_id` = `P` + six digits, assigned in (arrival day, generation order) | UUIDs | ID order then matches arrival order, so ID tie-breaks are meaningful and reproducible |
| 14 | 2026-11-07 | Residual tie-breaks: assignment by `patient_id` ascending, cuts by `patient_id` descending | Random with a seed | Mirrors "longest-waiting keeps priority"; deterministic |
| 15 | 2026-11-07 | Largest-remainder ties broken by department order, with iterative capping | Random; proportional rounding | Deterministic, and always sums exactly to the total |
| 16 | 2026-11-07 | `days_waiting = t − arrival_day` | Days since entering overflow | Matches the owner's decision that waiting counts from `arrival_day` |
| 17 | 2026-11-07 | Deterministic audit has its own hard-constraint implementation, cross-tested against the validator | Reuse the validator | Independent verification, not self-checking code |
| 18 | 2026-11-07 | Demand table written from independent counters in the generator | Derived from the registry after the fact | Makes reconciliation a genuine check, as the design requires |
| 19 | 2026-11-07 | Run initialisation by a CLI command in a development session | An orchestration tool | Keeps dataset choice out of the dispatcher's hands |
| 20 | 2026-11-07 | Run-only restrictions in `.claude/run-settings.json` via `--settings` | Project `.claude/settings.json` | Settings in the project file would also restrict development sessions |
| 21 | 2026-11-07 | Day-1 Bed Assignment State recorded in two stages (`initial`, `final`) | Final stage only | The initial stage defines which beds no-eviction protects on day 1 |
| 22 | 2026-11-07 | Python MCP SDK (FastMCP), `uv`-managed project with `pyproject.toml` at the root | Raw MCP protocol | Standard, minimal and local |
| 23 | 2026-11-11 | RNG `numpy.random.default_rng(seed)`; draws per day, then department in fixed order: Poisson count, complexities, standard normals for LOS | Separate RNG streams per department | One documented draw order makes datasets exactly reproducible |
| 24 | 2026-11-11 | Burn-in starts from an empty hospital on day −29 with base arrival rates; surges and shocks apply only to horizon days | Start from an approximate steady state | Simplest warm start; 30 days is about 4 × the L3 mean stay |
| 25 | 2026-11-11 | `dataset_id = seed<seed>`, e.g. `seed20261107` | Hash or date-based IDs | The ID encodes the seed, as `DATA_DICTIONARY.md` §5 requires |
| 26 | 2026-11-11 | Template configs in `src/data_generation/configs/`; `--seed` overrides the template seed; the written `generation_config.json` records the seed used and the LOS calibration (σ, μ by level) | Hard-coded defaults in Python | Parameters stay in one data file; each dataset carries its own exact config |
| 27 | 2026-11-11 | Validation in `validation.py` reads the written CSVs as strings, recomputes every expected quantity from the registry with its own code and never imports generator logic. A check that hits malformed data fails instead of crashing. 19 checks: the 13 required by `DATA_DICTIONARY.md` §4 plus schema, integer fields, ID format and order, `external_event` consistency, pools vs. schedule and `environment_config` | Validate in-memory generator output | Independence is the purpose of the check |
| 28 | 2026-11-11 | A rejected dataset keeps its files, with `accepted: false` in `validation_report.json`, and the CLI exits with code 1. Existing `data/raw/<dataset_id>/` is never overwritten without `--overwrite` | Delete rejected datasets | Rejections stay inspectable; original data stays immutable |
| 29 | 2026-11-11 | N1 requirement computed in exact integer arithmetic (weights in hundredths): `ceil(s/100)` with `s = 20·n1 + 35·n2 + 60·n3` | Floating-point `ceil` | Floating point gets the rounding wrong on 10 of the 68,921 census combinations up to 40 per level, e.g. (12, 0, 1): 2.4 + 0.6 = 3.0 is computed as `3.0000000000000004`, giving 4 instead of 3. *Corrected 2026-11-11:* the earlier example, `0.35 × 20`, is in fact exact in floating point. Every N1 implementation must use exact arithmetic (see #37 and `tests/test_nurse_requirement.py`) |
| 30 | 2026-11-11 | Monte Carlo on seeds 1–1000 (disjoint from the dataset seeds), reporting mean, sd, 2.5/50/97.5 percentiles and the dataset's mid-rank percentile; written to `data/processed/montecarlo/` | Reuse the 20-seed pre-check | The pre-check script was not in the repository; 1,000 seeds give reference ranges, not just point values |
| 31 | 2026-11-11 | Pre-check statistics interpreted as: mean over days 1–30 of total census; mean of Σ_d ceil(N1_d); maximum total census in the horizon ("surge peak") | Other definitions | The 1,000-seed means (89.4, 38.4, 107.4) reproduce the recorded ≈ 89, ≈ 38, ≈ 105 |
| 32 | 2026-11-11 | AGENTS.md §8 note on the horizon updated to H = 30 (approved); `pyproject.toml` and `uv.lock` added to the `CLAUDE.md` §0 tree | Leave stale text | Removes inconsistencies found on 2026-11-11 |
| 33 | 2026-11-11 | **Pre-registered Shock 3 selection rule (owner, recorded before the sweep was run).** Candidates: **A** = Shock 3 at −N on days 23–25, N ∈ {18, 22, 26}, Shock 2 unchanged; **B** = Shock 2 (+4) on days 16–18, Shock 3 on days 19–21 with pool 96 − N, N ∈ {10, 14, 18}; **C** (added by Claude, *reported only, not eligible*) = Shock 2 unchanged, Shock 3 on days 21–23 with pool 96 − N, N ∈ {10, 14, 18}. MC seeds 1–1000, as in #30; demand is identical across candidates because pools never affect the RNG. Definitions, with t0 the onset day: `carried = census(t0) − arrivals(t0)`; `ovf_min = census(t0−1) − min(P_B(t0−1), Σ_d min(census_d(t0−1), max_beds))`; **forced cut size** `= max(0, carried − ovf_min − P_B(t0))`, the cut that every work-conserving allocation on t0−1 must make; possible cut (upper bound) `= max(0, min(carried, P_B(t0−1)) − P_B(t0))`. **Rule:** among A and B only, choose the smallest N with P(forced cut size > 0) ≥ 0.85; ties go to the lower mean number of horizon days with census > P_B. If no candidate qualifies, none is chosen and the result goes back to the owner. The primary seed is then accepted whatever it shows. | Choose after seeing results | Pre-registration prevents fitting the choice to the outcome |
| 34 | 2026-11-11 | **Imbalance metric** (owner request, generation diagnostics): a day counts when total census < P_B(t) and some department's census exceeds its share of the pool; excess = Σ_d max(0, census_d − share_d) on those days. "Proportional share" is reported in two readings: (i) **initial share**, `LR(P_B(t), B(1), caps = max_beds)` with B(1) the common initial allocation; (ii) **equal share**, `LR(P_B(t), [1,1,1,1], caps = max_beds)` | A share proportional to the current census, which can never be exceeded while census < pool | The owner's wording leaves the reference share open; (i) is what a static allocation (B0) actually faces. It describes the data, not a policy, and is not an evaluation metric |
| 35 | 2026-11-11 | Shock-sweep "refused admissions" reported as the mean over the shock window of `max(0, census(t) − P_B(t))` | Counting arrivals turned away | The model has no admission refusal: patients beyond the pool overflow. Hospital-level excess census is the closest observable |
| 36 | 2026-11-11 | Dependencies `matplotlib` (plots) and dev `hypothesis` (property tests) | Hand-rolled random tests; plotting deferred | Standard, local, and needed for the requested bands plot and cut-path properties |
| 37 | 2026-11-11 | Cut-path pieces of `src/environment/` built ahead of the rest (§5.1, §5.3, §5.5, §5.7, plus N1), with exact `Fraction` arithmetic in LR and N1 | Wait for the full environment | The owner asked for the cut-path tests now. N1 in `src/environment/nurses.py` (Fraction of the decimal weights) is independent of `src/data_generation/stats.py` (integer hundredths), and the two are cross-checked over 22,000 census combinations |
| 38 | 2026-11-11 | `.hypothesis/` added to `.gitignore` | Commit the example database | It is a local cache, and it stores literals harvested from source files |
| 39 | 2026-11-11 | Run-settings verification as a manual script (`tests/manual/`), not a pytest test; evidence saved in `results/evaluations/run_settings_verification.json` | An automated test | It needs the `claude` CLI and spends model usage |
| 40 | 2026-11-11 | **Negative result, Shock 3 (recorded at the owner's request).** Under the pre-registered rule (#33), no candidate reached P(forced cut) ≥ 0.85 on seeds 1–1000. Eligible results: A18 0.086, A22 0.291, A26 0.523, B10 0.011, B14 0.100, B18 0.304; the approved A10 gives 0.002. Patients carried over into the onset day (p5 / p50 / p95): 63 / 78 / 92 on day 19, 62 / 75 / 90 on day 21, 59 / 72 / 87 on day 23. The smallest N reaching 0.85 is 29 for onset day 19, 31 for day 21 and 33 for day 23, i.e. a pool of 63–67 beds: **about a 30% bed loss**. The approved schedule is kept; the agent run is not expected to exercise relaxed no-eviction. Source: `data/processed/montecarlo/mc_analysis.json` | Lower the threshold after the fact; adopt a ~30% shock | Pre-registration binds; a ~30% shock is unrealistic for this demand |
| 41 | 2026-11-11 | Stress variant: config `src/data_generation/configs/generation_config_stress.json` (fields `dataset_id`, `variant`, `variant_note`), written with the new `--dataset-id` override and the same seed. **N = 40** (pool 56 on days 23–25): forced cut 6 on day 23 by the #33 definition (62 carried over, minimum overflow 0 on day 22). N = 35 is the smallest N that forces a cut (1 bed); 40 makes the cut large enough to exercise the ordering across levels and departments. Its registry and demand table are byte-identical to the primary's; only the pool rows for days 23–26 differ | N = 35 (1-bed cut); a new seed | A constructed test case, chosen on this seed by design (owner decision #12) |
| 42 | 2026-11-11 | Corrected the example in #29 (see there). Hand-computed N1 tests check per-department rounding (the hospital total is the sum of department ceilings, 12, not the pooled ceiling, 11) and two real floating-point traps | – | Guards against both implementations sharing a misreading of the spec |
| 43 | 2026-11-11 | Git repository initialised on `main` (the project had none); `.gitattributes` keeps `data/**` and the template configs byte-exact despite the system-wide `core.autocrlf=true`, and normalises other text files to LF. The manifest hashes code files with CRLF normalised to LF | Commit data with line-ending conversion | Hashes must survive any checkout on any OS |
| 44 | 2026-11-11 | **Data freeze `data-v1.0`.** `data/MANIFEST.json`: SHA-256 of the 20 data files of the four datasets (CSVs and per-dataset configs), the 3 template configs, and the generator code (`generator.py`, `los.py`, `__main__.py`, `validation.py`, `constants.py`); generator commit `a1d60799e071fedd69ecece69721bf75de9dec66`. Check: `uv run python -m src.data_generation.manifest --verify [--regenerate]`, also run by `tests/test_manifest.py`. It fails on a hash mismatch, a missing or unlisted data file, or a changed generator file, and `--regenerate` rebuilds every dataset from its frozen configs and compares the bytes. Validation reports and Monte Carlo outputs in `data/processed/` are committed but not hashed (they carry timestamps and are derived). Tagged `data-v1.0`. **Any later change to data requires a new tag and the owner's approval** | Hash only the CSVs; no regeneration check | Freezes both the data and the means to reproduce them |
| 45 | 2026-11-12 | **Schedule (owner).** The external deadline moved to "early December" (not yet confirmed). Plan against an **internal deadline of 30 November 2026**. The extra time is for evaluation depth (runs R2 and R3, the stress-variant run, robustness), not new features; the order of the §0 next steps is unchanged. No earlier deadline was recorded in the repository: the owner's instruction referred to 16 November, which appears in no committed file (REFLECTION_LOG R7) | Plan against the unconfirmed external date | A fixed internal date keeps a buffer if "early December" turns out earlier |
| 46 | 2026-11-12 | **A2 closed form has three cases** (owner correction, REFLECTION_LOG R17): `MaxN_j = Σa` if `P_N ≥ Σ⌈a⌉`; `= P_N` if `P_N ≤ Σ⌊a⌋`; otherwise `Σ⌊a⌋` plus the `P_N − Σ⌊a⌋` largest fractional parts. Each nurse adds at most 1 unit of coverage and the per-department gain is concave (1 per nurse up to ⌊a_d⌋, then the fractional part, then 0), so greedy is optimal. Explicit test for the middle case plus an enumeration cross-check | The two-case form of the proposal | It overstated the maximum on rationing days |
| 47 | 2026-11-12 | **Rounding floor for SV_N is the lexicographic minimum** `L(t)` of `(gapN_3, gapN_2, gapN_1)` over all integer allocations, per tier. The proposal's joint floor `F_N = min Σ_j gapN_j` is not used | Joint minimum F_N | The owner fixed the reading as per tier and lexicographic; a joint minimum could credit a trade of L3 coverage for L2. The number of days on which `Σ_j L_j ≠ F_N` is reported with the headroom |
| 48 | 2026-11-12 | **Record-level definitions (R11):** holders `H_d(t)` = in-bed patients of the previous Bed Assignment State (day 1: the `initial` stage) still present; movable beds = `B_d − O_d`; an empty movable bed is level 0; a shock day is `Σ O_d > P_B`, on which no movable beds exist (relaxed no-eviction forces `Σ_d max(0, B_d − O_d) = 0`) | "free, or freed by that day's discharges" | Computable from the records |
| 49 | 2026-11-12 | **Stability reference (R12):** `τ = B − R`, with R the repair rule applied to the previous allocation, i.e. what B0 would do from the same state | `½(Σ|ΔB| − |ΔP|)` without a reference | Names the counterfactual; equal to the old formula on days with no pool change |
| 50 | 2026-11-12 | **A3 path component is never negative.** `raw − floor − avoid = Σ_t [min(P_B, Σ_d min(n_d^{≥j}, max_beds)) − Max_j]`, and `Max_j` is at most both terms: per department `|H^{≥j}_d| + min(|Q^{≥j}_d|, max_beds − O_d) ≤ min(n^{≥j}_d, max_beds)`, and `Σ|H^{≥j}| + M ≤ P_B`; on shock days `Max_j = min(|H^{≥j}|, P_B)`. Tested on all baseline runs | – | Makes the decomposition well defined |
| 51 | 2026-11-12 | **Fairness definitions (R14):** B3 (wait distribution among patients ever in overflow) replaces "mean days in overflow"; B1 cap netting removes the daily cap excess from d's **overflow** patients from the lowest level upward, so net overflow is never negative | Netting against census by level | Holders may be low-level while higher-level non-holders overflow, so netting against census could go negative |
| 52 | 2026-11-12 | **R10 and R13 resolved:** the nurse clinical violation is measured as the A2 tier gap in need units (with the idle-nurse type, owner-approved); explanation quality is qualitative, LLM CHECKER only, labelled LLM-dependent | Need-unit pairing; a structured `expected_outcomes` field | Pairing in need units is not well defined with whole nurses; matching structured predictions would be trivial given `simulate_allocation` |
| 53 | 2026-11-12 | **Environment completed:** `initial.py` (§5.2), C1 coverage and the three-case tier maximum in `nurses.py` (Fraction), the bed pairing detector in `clinical.py`, the what-if in `whatif.py` with a `DayContext` (day, present patients, holders, pools, `max_beds`, weights). The what-if returns no outcomes for proposals with `BOUNDS` or `INTEGRALITY` errors, and no pairs for any invalid proposal | Outcomes for invalid proposals too | Pairing assumes a feasible allocation |
| 54 | 2026-11-12 | **Audit independence:** `src/evaluation/audit.py` has its own hard-constraint check, its own N1 and C1 in integer hundredths (via `Decimal`; the third N1 implementation, R4), its own bed-assignment replay, the bed closed form `Max_j`, and an enumeration of every integer nurse allocation (about 10⁴ per day) for `MaxN_j` and the lexicographic floor. It uses the environment only for the pairing detector (the other side of the A1 cross-check) and the repair rule (the stability reference, which is defined as that rule) | Reuse the environment code | Independent verification (`CLAUDE.md` §7) |
| 55 | 2026-11-12 | **Baseline records:** `allocation_state.jsonl` (day 1: the `initial_rule` line, then the decision) and `bed_assignment_state.jsonl` (one line per day and stage, with a map patient → department and status). No Observed State or workflow records for baselines (they belong to the server). The audit writes one `deterministic_audit.jsonl` line per five-day period, plus `metrics.json`. Baseline results are committed: they are deterministic and contain no agent output | One line per patient and day | Compact, and replayable by the audit |
| 56 | 2026-11-12 | **Issue mapping details:** one nurse-gap issue per day, graded by its highest tier with a positive net gap; reversal issues per day and department (W = 3); "reallocation without effect" = τ ≠ 0 while the in-bed set and the covered need by level and department equal those under the repair reference; rejected submissions and failure days are read from the Decision History and the Allocation State `source` | One issue per unit | Keeps the issue counts readable |
| 57 | 2026-11-12 | **Pairing tie-breaks:** bed pairs pair unserved patients in assignment order (level descending, `arrival_day`, `patient_id`) with served beds in (level ascending, department order, `patient_id`); F1 inversions use a strict `arrival_day` comparison (equal arrival days never count) and pair oldest-waiting with newest-placed; reversals match oldest unmatched units first, and units older than W expire | Other greedy orders | Deterministic; the A1 total does not depend on the order (cross-checked against the closed form) |
| 58 | 2026-11-12 | **Testing and docs policy (owner, `CLAUDE.md` §9.4).** Slow tests marked `@pytest.mark.slow` (the Hypothesis suites in `test_environment_cut_path.py` and `test_environment_rest.py`, and `manifest --regenerate`) and excluded by default via `addopts = -m "not slow"`; the full suite is `uv run pytest -m "slow or not slow"` (an empty `-m ""` is dropped by Windows PowerShell 5.1). No Monte Carlo test exists in the suite, and the headless run-settings check is a manual script, so neither needed a mark. `tests/test_evaluation.py` (12 baseline runs and audits in one module fixture) is not in the owner's list and stays in the fast suite | Mark by module; a separate slow directory | Per-test marks keep the fast hand tests of the same modules in the fast suite |
| 59 | 2026-11-12 | **Occupied-reversal count** (owner decision §11 #26 asked for "reversals of beds that were occupied in between" and left the definition to the assistant): only gain-then-loss matches count, in the receiving department; for m units the count is `max(0, min(m, m − min idle_d(s)))` over the days in between (a lower bound on the gained beds in use on the least idle day). "All reversals" keeps the approved definition (both directions, so a round trip counts twice) | Count in both departments; require occupation on every day in between; track individual beds | Beds are counts, not identities, so only a bound is computable from the records; the receiving side is where the beds were. **Reported to the owner for confirmation** |
| 60 | 2026-11-12 | **R20 fix:** `Read(./results/**)` added to `.claude/run-settings.json`; `verify_run_settings.py` probes a baseline bed-assignment file, `headroom.json` and a `Glob` over `results/**` | – | Owner decision §11 #27 |
| 61 | 2026-11-12 | **ANALYZER output = facts only.** Observed State: pools; external changes (pool change vs. the previous day, `external_event`); per department arrivals, discharges, census by level and its change, occupied beds O_d, N1 requirement, arrival means over the last 3 and 7 days and all days so far, yesterday's overflow by level; feasibility of the allocation in effect against today's pools and occupied beds; allocation minus census and nurses minus requirement. No thresholds, flags or recommendations | Trend flags with thresholds (e.g. "surge detected") | A threshold would be a new parameter shaping what the agent sees; summaries of days ≤ t are within the temporal rule |
| 62 | 2026-11-12 | **Errors reach the agent as `ToolError`.** `server.py` wraps every call and converts `WorkflowError` and `StoreError` into the SDK's `ToolError`, whose message is passed to the model (REFLECTION_LOG R21) | Return error dicts | The SDK hides the text of any other exception |
| 63 | 2026-11-12 | **MCP Python SDK v2** (`mcp>=2.3,<3`, `MCPServer`; v2 renamed FastMCP, Log #22) | Pin `mcp<2` and FastMCP | Current major version; same stdio model |
| 64 | 2026-11-12 | **Run settings additions:** `enabledMcpjsonServers: ["orchestration"]` (a headless session cannot answer the `.mcp.json` approval prompt) and `permissions.allow` for `mcp__orchestration`, `mcp__allocator`, `mcp__checker`, `Agent(allocator)`, `Agent(checker)` (otherwise every tool call would wait on a prompt). Only our own servers and the two subagents are allowed; the deny list is unchanged | Approve interactively at every run | Runs must be reproducible without manual approvals; nothing beyond the run's own tools is permitted |
| 65 | 2026-11-12 | **Overflow queue** = present patients who do not hold a bed from yesterday (new arrivals included), before today's assignment, sorted by the assignment order; never `discharge_day` | Only patients already in overflow yesterday | These are exactly the patients the day's free beds go to |
| 66 | 2026-11-12 | **`submit_decision` input handling:** beds and nurses are passed to the validator as received (no type coercion, so `INTEGRALITY` is detectable); an explanation with a missing or empty field is a schema error, returned without counting as an attempt; only validator outcomes count as attempts | Coerce numbers; count schema errors as attempts | Keeps the hard-constraint check honest, and the attempt count means "rejected by the validator" |
| 67 | 2026-11-12 | **In-run audit:** on each audit day the server audits days 1…t from the records (reversal issues use only days ≤ t) and stores the current five-day period | Audit only the five days | Reversals and holders need the history; the stored record still covers one period |
| 68 | 2026-11-12 | **Agent files:** `dispatcher` (`tools: mcp__orchestration__*, Agent(allocator, checker)`, no other tools), `allocator` and `checker` (`tools: mcp__<role>__*`, inline stdio `mcpServers` list entry, `omitClaudeMd: true`); syntax checked against the subagents documentation on 2026-11-12. No `model` field, so subagents inherit the session model: **the model for the real runs is an open question for the owner**. The fixed templates live in `src/agent/templates.py` and verbatim in `dispatcher.md` (tested) | Set a model now | Model choice affects the evaluation |
| 69 | 2026-11-12 | **Smoke test design** (`tests/manual/smoke_test.py`): a synthetic 5-day fixture (`src/mcp_server/fixture.py`, hand-made, no generator), one headless run session started exactly as a real run (`--agent dispatcher --settings .claude/run-settings.json`), haiku for main and subagents, smoke prompts that make the subagents call their own tools mechanically and attempt foreign ones (day 1 re-submits the allocation in effect; days 2–4 fall back to repair). Checks are classified from the stream-json transcript and the run records. The ACTIVE_RUN pointer is saved and restored. **Limitation:** the transcript shows the main session's tool list but not a subagent's, so "a subagent cannot call foreign tools" rests on its frontmatter (tested), on each role server registering only its tools (tested) and on no foreign call succeeding in the session | Use a frozen dataset; dedicated smoke agent files | No agent output on frozen data; the real agent files and settings are what is tested |
| 70 | 2026-11-12 | **Smoke test result** (`results/evaluations/smoke_test.json`, transcript `smoke_test_transcript.jsonl`): 13 of 14 checks pass. The main session's tools are exactly the 4 orchestration tools plus the Agent tool (named `Task` in stream-json); it has no Read, Write, Edit, Bash, Glob or Grep and no submit tool; the orchestration server connects; both inline role servers connect, and each subagent called all its own tools successfully, with no foreign tool succeeding. The run went READY → FINISHED with 5 accepted ALLOCATOR decisions, 1 audit and 1 CHECKER report, and the dispatcher passed only the fixed templates. **Not shown live:** check 5c (no other subagent can be spawned), because the dispatcher refused the off-protocol instruction (R22). Evidence for 5c is the `Agent(allocator, checker)` frontmatter (tested) and the documented allowlist behaviour. Also observed: the user's claude.ai connectors (Claude Docs, Gmail, Calendar, Drive) connect in run sessions; their tools are not in any agent's `tools` list, so they are unreachable | Re-run with a different design | Reported to the owner rather than spending more runs (R22) |

## 10. Approved Parameter Set

**Approved by the owner on 2026-11-07.** These are illustrative synthetic values, not real hospital statistics. They were calibrated with a 20-seed pre-check: mean census about 89, mean N1 requirement about 38, mean total surge peak about 105.

### 10.1 `environment_config` (visible to agents)

| Parameter | Value | Rationale |
| --- | --- | --- |
| `max_beds` | 40 | Lets the surge department expand but prevents extreme concentration. 4 × 40 = 160 ≥ the peak pool of 100. |
| w(L1), w(L2), w(L3) | 0.20, 0.35, 0.60 | Roughly 1 nurse per 5, 3 and 1.7 patients |

### 10.2 `generation_config` (hidden from all agents)

| Parameter | Value | Rationale |
| --- | --- | --- |
| Base `total_beds` | **96** | About 92% mean occupancy, so days with imbalance and spare capacity occur often |
| Base `total_nurses` | 37 | About 96% of the mean requirement: shortage on busy days, slack on quiet ones. **This deliberately creates a nurse-rationing regime** (recorded 2026-11-11): in the 1,000-seed Monte Carlo the total N1 requirement exceeds the pool on a mean of 18 of 30 days (2.5–97.5%: 7–28), and on 17 days in the primary dataset. Nurse allocation is therefore a real trade-off on most days, not an edge case, and nurse shortage is an expected outcome of every policy. |
| λ_d (arrivals per day) | IM 6.0, Cardiology 4.0, Neurology 3.0, Orthopedics 4.5 | Realistic size differences, with IM the highest volume |
| Complexity mix L1/L2/L3 | IM .45/.40/.15, Cardiology .25/.40/.35, Neurology .20/.40/.40, Orthopedics .55/.35/.10 | Cardiology and Neurology acute, Orthopedics mostly simple, IM broad |
| Length of stay | Discretised lognormal (ceiling), coefficient of variation 0.6, discrete means L1 3, L2 5, L3 8 days. The same in every department. **Interpretation (approved 2026-11-11):** CV 0.6 is that of the continuous lognormal, so σ = √ln(1.36) ≈ 0.5545; μ is solved numerically so that the mean of ceil(X) is exactly 3, 5 and 8 (μ ≈ 0.7626, 1.3503, 1.8612). The resulting discrete CVs are about 0.51, 0.54 and 0.56. | Right-skewed, rising with complexity |
| Surge | Cardiology λ × 1.6 on days 12–19 | Mid-horizon, so adaptation is visible |
| Shock 1 | Nurses −4 on days 8–10 | Staff absence wave |
| Shock 2 | Beds +4 on days 16–20 (pool 100) | Surge capacity; still within 4 × `max_beds` |
| Shock 3 | Beds **−10** on days 23–25 (pool 86) | *Original rationale, shown to be wrong:* "hits while census is high, so relaxed no-eviction is exercised". A forced cut depends on patients carried over, not on census; P(forced cut) = 0.002 (REFLECTION_LOG R1, Log #40). Kept as approved; the cut path is exercised by the stress variant instead (Log #41) |
| Shock type | Scheduled, not random | Each shock is interpretable |
| Burn-in | 30 days | About 4 × the L3 mean stay, so day 1 is in steady state |
| Horizon H | 30 days (6 audits) | Covers the surge, the shocks and recovery |
| Seeds | Primary **20261107**. Robustness seeds 20261108 and 20261109, for the baselines only. | One fixed dataset isolates LLM variability |

### 10.3 Run parameter

| Parameter | Value | Rationale |
| --- | --- | --- |
| Retry limit N | 3 | Enough to fix validator rejections without looping |

## 11. Approved Escalation Decisions

**Approved by the owner on 2026-11-07.**

| # | Decision | Applied in |
| --- | --- | --- |
| 1 | `omitClaudeMd: true` for the ALLOCATOR and CHECKER subagents. Their prompts restate the needed principles, consistent with `CLAUDE.md`, and the owner reviews them before the first run. | Section 8 |
| 2 | `external_event` describes only the current day's change, with no duration or forecast | `DATA_DICTIONARY.md` §5 |
| 3 | An empty movable bed left unused while a higher-level patient overflows is a separate violation type, with severity = k (the unserved patient's level) | `EVALUATION_PLAN.md` §3.1 |
| 4 | Day-1 nurses are split in proportion to the N1 requirement | Section 5.2 |
| 5 | Robustness: the deterministic baselines also run on two extra seeds, as an appendix. Agent results rest on the primary dataset only, which is declared as a limitation. | `EVALUATION_PLAN.md` §5, `LIMITATIONS_AND_REFLECTION.md` §2 |

The robustness seeds (20261108 and 20261109) are an implementation choice, also recorded here. The primary seed was approved as proposed.

**Approved by the owner on 2026-11-11.**

| # | Decision | Applied in |
| --- | --- | --- |
| 6 | LOS discretisation: σ from a continuous CV of 0.6; μ calibrated so the discrete (ceiling) mean is exactly 3 / 5 / 8 | Section 10.2, `DATA_DICTIONARY.md` §3.5 |
| 7 | `external_event` is non-empty only on days when a pool changes from the previous day, restorations included (days 8, 11, 16, 21, 23, 26 under the approved schedule); empty on day 1 | `DATA_DICTIONARY.md` §3.1 |
| 8 | Run-session deny list extended with `Read(./docs/**)` and `Read(./src/data_generation/**)`, as a second layer behind the tool restrictions | Section 8, `CLAUDE.md` §9.1 |
| 9 | Deny-by-default for `data/**` in run sessions (`Read` and `Edit`); agents access data only through the MCP server. Verified the same day (Section 8). | Section 8, `DATA_DICTIONARY.md` §5 |
| 10 | Shock 3: sweep the candidate schedules under the pre-registered rule (Decisions Log #33) before changing anything; add cut-path tests regardless. Result: no candidate qualified. | Section 0 |
| 11 | **Keep the approved Shock 3** (beds −10, days 23–25). The rule selected nothing, and the threshold is not lowered after the fact. The negative result is recorded. | Log #40, `LIMITATIONS_AND_REFLECTION.md` §2 |
| 12 | Create the stress variant `seed20261107_stress`: a constructed test case with a Shock 3 large enough to force a cut on day 23 for this seed; choosing the magnitude from this seed is acceptable because it is not a representative draw. Excluded from all baseline and agent comparisons in the main evaluation; an optional run may come later. | Log #41, `EVALUATION_PLAN.md` §5 |
| 13 | Deny list extended with `Read(./tests/**)` and `Read(./.hypothesis/**)` | Section 8 |
| 14 | **Data freeze:** `data/MANIFEST.json` with SHA-256 hashes, a manifest check, git tag `data-v1.0`. After the freeze, any change to data needs a new tag and the owner's approval. | Log #44, `CLAUDE.md` §9.3 |
| 15 | Work order: metric formulas and CHECKER severity scale proposed and fixed **before any agent output is seen**; then the environment, the audit and baselines, and a minimal MCP path to a first run; polish afterwards | Section 0 |

**Approved by the owner on 2026-11-12** (metric formulas and severity scale fixed **before any agent output**).

| # | Decision | Applied in |
| --- | --- | --- |
| 16 | Metric formulas fixed as in `EVALUATION_PLAN.md` §3, with the A2 closed form corrected to three cases (Log #46) | `EVALUATION_PLAN.md` §3 |
| 17 | Framing: B1 is an optimal myopic rule on A1, so the agent can only match or lose there; the agent's possible advantage lies in the A3 path component and in nurse rationing (A2). Headroom is quantified from baselines (B0–B2, three seeds) before the headline set is confirmed; seeing baseline outputs first is fine, seeing agent outputs is not | `EVALUATION_PLAN.md` §1, §8 |
| 18 | Headline: SV_B with its type split; SV_N per tier, lexicographic; A3 excess for tiers 3 and 2, split into avoid and path; bed reversals within W. Gate: D (zero hard-constraint violations in effect, else the run is not interpreted). Secondary: B1, B2, B3, A4, nurse reversals. Descriptive: RS and frequency, C1–C4, B4. No combined score | `EVALUATION_PLAN.md` §3.10 |
| 19 | Approved judgment items: empty bed = level 0; the idle-nurse violation type; F1 inversions (B2) as a secondary metric, with a test that B1 scores 0 on it; W = 3, with W = 2 and 5 as pre-registered sensitivity checks; cap excess netted against the lowest levels; explanation quality qualitative and labelled LLM-dependent. The shock-day A1 pairing must be tested against the closed form before any use on the stress variant | `EVALUATION_PLAN.md` §3 |
| 20 | Severity scale approved (Critical / Major / Moderate / Minor, with the category test). `validate_allocation` calls are free and never counted; only rejected submissions count. Comparison by lexicographic counts by level; any Critical issue blocks interpretation | `EVALUATION_PLAN.md` §4, `AGENTS.md` §6 |
| 21 | CHECKER-versus-audit matching (recall, precision, level agreement) is a primary Verification output | `EVALUATION_PLAN.md` §4, §7 |
| 22 | The stress run is **planned**. It stays excluded from the main comparisons and is reported separately as a probe of forced-cut handling, with B0–B2 run on it as reference | `EVALUATION_PLAN.md` §6 |
| 23 | Work order: finish `src/environment/`; build the audit and metrics and run B0–B2 on the three seeds and the stress variant; report the headroom table to the owner **before** starting the MCP work | Section 0 |
| 24 | **Framing after the headroom review:** reallocation matters a lot (B0 vs B1), and B1 captures almost all of its value. The research question is whether the LLM agent system reliably reproduces a near-optimal myopic policy, where it deviates, and whether the CHECKER catches the deviations. On these data the agent is not expected to beat B1 on clinical metrics; the frozen data are not changed to create headroom | `EVALUATION_PLAN.md` §1, `LIMITATIONS_AND_REFLECTION.md` §4 |
| 25 | **Headline set confirmed:** A1, A2 (per tier), A3 (tiers 3 and 2), each read as the gap to B1 and to the floor; gate D. Fairness dispersion is **not** promoted (that would be result-driven metric selection; it is noisy across seeds and can be gamed) and stays secondary, always next to A1/A3 | `EVALUATION_PLAN.md` §3.10 |
| 26 | **Stability demoted to secondary** (validity fix, R19): report all reversals and reversals of beds occupied in between, each with a worked example | `EVALUATION_PLAN.md` §3.8; Log #59 |
| 27 | **R20:** `Read(./results/**)` added to the run settings and re-verified; the CHECKER reads the record store only through MCP, never `results/` | `AGENTS.md` §6; Log #60 |
| 28 | **Log #47 confirmed** (lexicographic floor per tier). Ask before deviating from an approved formula, even if the deviation is logged. Notes recorded: seed 09 cannot discriminate B1 and B2 on bed metrics; the stress variant tests whether the agent follows the cut rule under pressure (its intended purpose), and B0's 4-bed cut is consistent with Log #41 | `EVALUATION_PLAN.md` §6, §8.4 |
