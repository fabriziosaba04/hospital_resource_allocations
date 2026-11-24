# Repository clean-up plan (Phase 1a: inventory only)

*Written 2026-11-23, at commit `c34ca77` (Phase 0). Phase 1a moves nothing: it reads, measures and writes this file. Phase 1b (the moves) waits for the owner's review of this plan.*

**Status 2026-11-23: plan accepted by the owner; Phase 1b executed on branch `cleanup`** with the owner's decisions on U1–U6 (U1: `results/verification/`, not `development/`). Where the execution differs from this plan: the guard covers every writer found by searching `src/` (R60), not only the four in §3.3; `REFLECTION.md` is created as a placeholder; `docs/EVALUATION_PLAN.md` keeps its two old development paths (pre-registration text, Log #124). Details: Decisions Log #119–#124.

**Constraint that shapes the whole plan.** The hard rules forbid moving the run folders and captures of R1, R2, R3 and STRESS1, the owner input tables and the frozen R1 extraction. All of these live in `results/allocations/<run>/` and `results/evaluations/<run>/`. Those two folders therefore **stay**, and so does the code convention `results/{allocations,evaluations}/<run_id>` that about 25 modules rely on. The brief's grouping (`runs/`, `baselines/`) is delivered through an index (`results/README.md`), not through moves. Development material can move, because none of it is frozen.

## 1. Current state

### 1.1 Size

- **Tracked files:** 744. **Total:** 53.3 MB.
- **Largest file:** 3.03 MB (`results/allocations/R2/transcripts/launch-1.jsonl`). No file is over 50 MB, so GitHub's 100 MB limit is not an issue. The next largest are the other launch transcripts (2.5–2.6 MB) and `results/evaluations/R1/explanation_claims.json` (0.61 MB).
- **Untracked, local only (not in the repository and not in a `git archive` zip):** `.venv/`, `.hypothesis/`, `.pytest_cache/`, `__pycache__/`, `.claude/settings.local.json` and `notebooks/`, which is empty and so is not tracked.

### 1.2 Tree to depth 3 (tracked files)

| Path | Files | MB | Class |
| --- | ---: | ---: | --- |
| `.claude/agents/` (allocator, checker, dispatcher) | 3 | 0.02 | final (frozen at `prompts-v1.0`) |
| `.claude/run-settings.json` | 1 | – | final (frozen at `prompts-v1.0`) |
| `.mcp.json`, `.gitattributes`, `.gitignore`, `pyproject.toml`, `uv.lock` | 5 | 0.30 | final |
| `CLAUDE.md` | 1 | 0.04 | docs (standing instructions) |
| `README.md` | 1 | 0.00 | final, but **stale**: it says the agents are "not built yet" |
| `data/` | 29 | 0.42 | final (frozen at `data-v1.0`) |
| `data/raw/<4 datasets>/` | 12 | 0.14 | final |
| `data/metadata/<4 datasets>/` | 8 | 0.01 | final |
| `data/processed/<4 datasets>/` (validation reports) | 4 | 0.02 | final |
| `data/processed/montecarlo/` | 4 | 0.26 | final (Monte Carlo reference ranges) |
| `data/MANIFEST.json` | 1 | – | final |
| `docs/` | 8 | 0.37 | docs |
| `src/` | 60 | 0.34 | final |
| `src/data_generation/` (+ `configs/`) | 11 | 0.06 | final; 7 of these files are hashed in `MANIFEST.json` |
| `src/environment/` | 10 | 0.02 | final |
| `src/evaluation/` | 21 | 0.18 | final |
| `src/mcp_server/` | 12 | 0.08 | final (includes the dev fixtures `fixture.py` and `fixture_hard.py`) |
| `src/agent/`, `src/utils/` | 5 | 0.00 | final |
| `tests/` | 26 | 0.16 | final (verification) |
| `tests/manual/` (+ `fixtures/spawn-probe.md`) | 4 | 0.02 | final (manual checks) |
| `results/` | 610 | 51.62 | mixed, see below |
| `results/allocations/` | 447 | 45.47 | |
| `results/evaluations/` | 142 | 5.50 | |
| `results/dry_runs/` | 9 | 0.01 | development |
| `results/visualizations/HARD10/` | 12 | 0.65 | development |

`results/` in detail:

| Path | Files (alloc + eval) | MB | Class |
| --- | ---: | ---: | --- |
| `R1/`, `R2/`, `R3/` | 95+69, 95+5, 94+5 | 12.7, 10.8, 10.2 | final, **frozen** |
| `STRESS1/` | 95+5 | 10.7 | final, **frozen** |
| `B0/B1/B2-seed20261107` | 3 × (2+2) | 0.8 | final (main comparison) |
| `B0/B1/B2-seed20261108`, `-seed20261109` | 6 × (2+2) | 1.5 | final (robustness appendix) |
| `B0/B1/B2-seed20261107_stress` | 3 × (2+2) | 0.8 | final (STRESS1 comparison) |
| `evaluations/headroom.json` | 1 | – | final |
| `DRY1-SMOKE5`, `DRY2-HARD10`, `DRY3-RESUME` | 9+3, 9+11, 11+5 | 2.2 | development |
| `CHK-B2-HARD10` | 9+4 | 0.3 | development (CHECKER test on B2) |
| `B0/B1/B2-HARD10` | 3 × (2+2) | 0.2 | development (baselines on the HARD10 fixture) |
| `evaluations/smoke_test.json`, `smoke_test_transcript.jsonl`, `smoke_probe_transcript.jsonl` | 3 | 0.5 | **unclear** (U1) |
| `evaluations/run_settings_verification.json` | 1 | – | **unclear** (U1) |

### 1.3 Unclear items (owner to decide)

| # | Item | Why it is unclear | Options |
| --- | --- | --- | --- |
| U1 | `results/evaluations/smoke_test.json`, `smoke_test_transcript.jsonl`, `smoke_probe_transcript.jsonl`, `run_settings_verification.json` | They come from development checks, but they are also the **verification evidence** that the run-session permissions held before the agent runs (Verification is 20%) | (a) `results/development/verification/`; (b) a final `results/verification/`; (c) stay |
| U2 | `results/evaluations/DRY2-HARD10/make_day7_claims.py`, `make_full_claims.py` | Code inside `results/`. The brief's rule is that code lives in `src/` | Move with DRY2 to `results/development/` (no code change), or move them to `src/` or `tests/` |
| U3 | `notebooks/` (empty, untracked) | Listed in the `CLAUDE.md` tree, but contains nothing | Drop it from the tree, or keep it for a final notebook |
| U4 | `docs/PROJECT_OVERVIEW.md` | It overlaps with the README the grader reads first | Keep it and link it from the README, or fold it into the README |
| U5 | `docs/LIMITATIONS_AND_REFLECTION.md` (38 lines) | It is the obvious source for `REFLECTION.md` (one page) | Keep it as the long version and link it from `REFLECTION.md`, or replace it with `REFLECTION.md` |
| U6 | `tests/manual/smoke_test.py`, `verify_run_settings.py` output paths | If U1 moves those files, both scripts' default output paths change. Both scripts are frozen in the `prompts-v1.0` tag, but no further run uses them | Change the defaults in the working tree only (the tag stays as it is) |

## 2. Target tree and mapping

### 2.1 Target tree

```text
hospital_resource_allocations/
├── README.md               deliverable: structure, where everything is, how to reproduce
├── plan.md                 new: question, theory, test (one page; points to docs/EVALUATION_PLAN.md)
├── ERROR_ANALYSIS.md       new deliverable: errors found, where, how analysed
├── mistakes.md             new: pointer to ERROR_ANALYSIS.md (the brief's name)
├── REFLECTION.md           new deliverable: one page
├── CLAUDE.md               stays: standing instructions for the coding agent (the brief's "AGENTS.md")
├── .claude/  .mcp.json     stay (Claude Code needs them at the root; frozen at prompts-v1.0)
├── pyproject.toml  uv.lock  .gitattributes  .gitignore
├── data/                   stays as is (§3.1)
│   ├── raw/                the datasets exactly as generated and frozen (= brief's data/raw)
│   ├── metadata/           environment and generation configs per dataset
│   ├── processed/          validation reports and Monte Carlo (= brief's data/derived)
│   └── MANIFEST.json
├── src/
│   ├── 01_verify_data.py … 09_build_figures.py   new thin entry scripts (§5)
│   └── data_generation/ environment/ mcp_server/ agent/ evaluation/ utils/   unchanged
├── results/
│   ├── README.md           new index: runs, baselines, analysis, figures, development
│   ├── allocations/        stays: run records of R1–R3, STRESS1 and baselines B0–B2 × 4 datasets
│   ├── evaluations/        stays: audits, run reports, R1 claim and owner analysis, headroom.json
│   ├── analysis/           new: cross-run tables (R1–R3, STRESS1, CHECKER matching, recomputations)
│   ├── figures/            new: final figures
│   └── development/        DRY1–3, CHK-B2-HARD10, B?-HARD10, fixtures, HARD10 figures
│       ├── allocations/    keeps the allocations/evaluations convention, so the code works with results_root=results/development
│       ├── evaluations/
│       ├── dry_runs/
│       └── figures/HARD10/
├── tests/                  unchanged (tests/manual/ holds the manual checks)
└── docs/                   unchanged names; living docs updated, logs kept as written
```

The brief's groups map onto this layout as follows:

| Brief | Here |
| --- | --- |
| `results/runs/` | `results/allocations/{R1,R2,R3,STRESS1}/` + `results/evaluations/{same}/` (index in `results/README.md`) |
| `results/baselines/` | `results/allocations/B?-<dataset>/` + `results/evaluations/B?-<dataset>/` |
| `results/analysis/`, `results/figures/`, `results/development/` | as named |

### 2.2 Mapping, old path → new path

| Old path | New path |
| --- | --- |
| `results/allocations/{R1,R2,R3,STRESS1}/`, `results/evaluations/{R1,R2,R3,STRESS1}/` | stays (frozen) |
| `results/allocations/B?-seed*/`, `results/evaluations/B?-seed*/`, `results/evaluations/headroom.json` | stays (same code convention, and `figures.build` reads runs and baselines from one root) |
| `results/allocations/{DRY1-SMOKE5,DRY2-HARD10,DRY3-RESUME,CHK-B2-HARD10,B0-HARD10,B1-HARD10,B2-HARD10}/` | `results/development/allocations/<same>/` |
| `results/evaluations/{same seven}/` | `results/development/evaluations/<same>/` |
| `results/dry_runs/` | `results/development/dry_runs/` |
| `results/visualizations/HARD10/` | `results/development/figures/HARD10/` (`results/visualizations/` disappears) |
| `results/evaluations/smoke_*`, `run_settings_verification.json` | U1 (proposal: `results/development/verification/`) |
| `data/**` | stays |
| `src/**` | stays; new `src/0N_*.py` |
| `tests/**`, `docs/**`, `.claude/**`, `.mcp.json`, `CLAUDE.md` | stays |
| – | new: `plan.md`, `ERROR_ANALYSIS.md`, `mistakes.md`, `REFLECTION.md`, `results/README.md`, `results/analysis/`, `results/figures/` |

**`CLAUDE.md` and `docs/AGENTS.md`** (owner decision): both stay where they are, with their names and content. The README explains the two roles (§6).

**`mistakes.md` vs `ERROR_ANALYSIS.md`.** Recommendation: **one file, `ERROR_ANALYSIS.md`, plus `mistakes.md` as a three-line pointer to it.** The deliverable name the course asks for is "error analysis", so the real file carries that name. The brief's `mistakes.md` still finds it. `ERROR_ANALYSIS.md` would cover the agent's errors (audit, claim verification, CHECKER vs audit) and, in a separate section, the assistant's development errors from `docs/REFLECTION_LOG.md` ("where the agent went wrong, and how you found out").

## 3. Path-dependency audit

### 3.1 `data/` → `data/raw/` + `data/derived/`: not safe; recommendation: leave `data/` as is

- `data/MANIFEST.json` (frozen at `data-v1.0`) records **repo-relative paths** such as `data/raw/seed20261107/…` and `data/metadata/…`. `manifest --verify` resolves them from the root, and it flags any file under `data/raw` or `data/metadata` that the manifest does not list. Any rename would need a new manifest, which means a new data tag and the owner's approval (`CLAUDE.md` §9.3).
- `manifest.py` also reads `data/processed/<ds>/validation_report.json`. The manifest hashes the generator code (`src/data_generation/{__main__,generator,los,validation}.py`, `configs/*.json`, `src/utils/constants.py`), and `generator.py` and `validation.py` hard-code `data/raw`, `data/metadata` and `data/processed`. Renaming `processed/` → `derived/` therefore means editing hashed generator code, and the manifest check would fail.
- Further readers that hard-code `data/raw` and `data/metadata`: `src/evaluation/dataset.py`, `src/mcp_server/analyzer.py`, `fixture.py`, `fixture_hard.py`.
- Our `data/raw/` already matches the brief's meaning (the dataset exactly as produced, never edited). `data/processed/` plays the role of `data/derived/`. **The README states this mapping. No move.**

### 3.2 Run folders under `results/runs/`: not safe; recommendation: leave them in place

- The hard rules forbid moving the files themselves. The records themselves would survive a move, because the stored paths are relative: `SHA256SUMS.json` keys are relative to `transcripts/subagents/`, and `copy_back.json` keys are relative to the run folder. Its absolute paths name the clone and the session folder, which are sources, not destinations.
- The code would not survive a move. `results/{allocations,evaluations}/<run_id>` is hard-coded as a default in `audit`/`metrics`, `run_report`, `claim_check`, `figures`, `allocator_digest`, `copy_back`, `init_run`, `store` (`alloc_dir.parent.parent / "evaluations"`), `runner` and every owner-review module (adjudication_*, owner_*, rubric_check_view, unverifiable_view, decisions_ab), plus `tests/test_long_paths.py` and `.gitattributes` (`results/evaluations/R1/owner_extraction/owner_claims_*.csv -text`).
- `tests/manual/verify_copy_back_independent.py` also assumes this layout, on purpose: it has no shared path helper.
- Every session log, reflection entry, decision and commit message cites these paths.
- **Conclusion:** the R1–R3 and STRESS1 folders stay. The baselines stay too (§2.2).

### 3.3 Development moves: safe, with these references to update

| Move | Code and tests that reference the old path | Records inside the moved folders | Docs |
| --- | --- | --- | --- |
| DRY1–3, CHK-B2-HARD10, B?-HARD10 → `results/development/{allocations,evaluations}/` | `tests/test_copy_back.py` (copies `results/{kind}/DRY2-HARD10`, compares the committed `run_report.json`); `tests/test_figures.py` (`daily_frame(ds, ROOT/"results"/"allocations"/r)`, `build(...)` default `results_root`); `tests/test_claim_check.py` (`score("DRY2-HARD10")` with the default root, plus a literal spec path); `tests/test_run_report.py` (DRY3-RESUME through the default root). Each one needs `results_root=ROOT/"results"/"development"` or the new literal. No `src/` change, because every entry point already takes a root | `run_manifest.json` of DRY1/DRY2/CHK hold the absolute paths where they ran (historical, never used to resolve). `DRY3-RESUME/copy_back.json` keys are relative, so they stay valid. The `Store` sibling rule is kept by the parallel `allocations/`+`evaluations/` subfolders | `PROJECT_SPEC.md` §0/§1, `EVALUATION_PLAN.md`, `CLAUDE.md` §0 tree (living: update). `SESSION_LOG.md`, `REFLECTION_LOG.md`, Decisions Log rows (historical: keep as written, with one note at the top of each pointing to §2.2) |
| `results/dry_runs/` → `results/development/dry_runs/` | `tests/test_copy_back.py:18`, `tests/test_figures.py:9` (`FIX`) | none (fixture CSV and JSON) | `PROJECT_SPEC.md`, `CLAUDE.md` tree |
| `results/visualizations/HARD10/` → `results/development/figures/HARD10/` | `src/evaluation/figures.py:244` defaults `out` to `results/visualizations/<dataset>`. Change the default to `results/figures/<dataset>` (implementation-level). `tests/test_figures.py` writes to `tmp_path` and is unaffected | PNG only | `README.md`, `CLAUDE.md`, `EVALUATION_PLAN.md`, `PROJECT_SPEC.md` |
| U1 files → `results/development/verification/` (if chosen) | `tests/manual/smoke_test.py:96` (`out_dir`), `tests/manual/verify_run_settings.py:105` | `run_settings_verification.json` mentions `headroom.json` as a probe target (content only) | `PROJECT_SPEC.md`, `REFLECTION_LOG.md`, `SESSION_LOG.md` |

**Run-session permissions:** `.claude/run-settings.json` (frozen) denies `results/**`, which covers `results/development/`. No change is needed, and none is allowed.

**Hazard found during the audit (REFLECTION_LOG R59).** Several entry points write by default into the frozen run folders:

- `metrics.evaluate_run` → `results/evaluations/<run>/deterministic_audit.jsonl` and `metrics.json`;
- `run_report` → `results/evaluations/<run>/run_report.json`;
- `claim_check` (CLI) → `results/evaluations/<run>/explanation_claims.json`.

`python -m src.evaluation` rewrites the baseline records with a new `created_at`. Running any of these with the defaults on R1–R3 or STRESS1 would **overwrite a copy-back-hashed file**. Nothing has been overwritten. The numbered entry scripts (§5) must therefore always pass an output root under `results/analysis/recomputed/` and compare against the committed file. They must never write to the default.

## 4. Path length

| | Characters |
| --- | ---: |
| Longest relative path today | **132** (`results/allocations/STRESS1/transcripts/subagents/allocator/tool-results/mcp-allocator-get_decision_history-…-bzcuat.txt`) |
| Longest relative path after the moves | **132** (the frozen folders do not move) |
| Longest development path, today → after | 76 → 88 (`results/development/dry_runs/HARD10_fixture/data/metadata/HARD10/environment_config.json`) |
| Owner's repository root (OneDrive) | 132, so the longest absolute path is 265; this needs `core.longpaths` and the `\\?\` handling |
| Zip unpacked so the files sit directly in `C:\hra\` | 139 |
| GitHub zip in `C:\hra\` (adds a `hospital_resource_allocations-main\` folder) | 174 |
| `git clone` into `C:\hra\hospital_resource_allocations\` | 169 |

All grader cases stay below 260. No new path is longer than today's maximum.

## 5. Numbered entry points

These are thin scripts in `src/`. Each one adds the repository root to `sys.path` and calls existing modules (`runpy.run_module` or a function call). They move no logic and break no imports. pytest does not collect them, because they are not named `test_*`. They are new files, so the generator hashes in `MANIFEST.json` are unaffected.

| # | Script | Calls | Grader can re-run? |
| --- | --- | --- | --- |
| 01 | `01_verify_data.py` | `src.data_generation.manifest --verify` (`--regenerate` for a byte-exact rebuild of all four datasets from the seeds) | **Yes** (regeneration is slow) |
| 02 | `02_montecarlo.py` | `src.data_generation.montecarlo --n 1000`, `mc_analysis --n 1000 --primary seed20261107` | Yes, slow. It must write to a temp root, because the default is `data/processed/montecarlo/` (inside `data/`) |
| 03 | `03_run_baselines.py` | `src.evaluation` (B0–B2 × 4 datasets, audit, metrics, headroom) | Yes, **only with an output root**. `__main__` hard-codes `ROOT/results`, so Phase 1b adds an `--out` option (implementation-level) and compares the output with the committed files, ignoring `created_at` |
| 04 | `04_agent_run.py` | prints the commands `init_run` → `launch` → `copy_back` (no execution) | **No.** It needs the `claude` CLI, a subscription, a clone outside OneDrive, and it is non-deterministic |
| 05 | `05_verify_copy_back.py` | `tests/manual/verify_copy_back_independent.py` for R1, R2, R3, STRESS1 | Partly. The clone comparison and the session-folder comparison exist only on the owner's machine. Phase 1b adds a `--sums-only` mode (re-hash against `SHA256SUMS.json` and `copy_back.json`) that any clone can run |
| 06 | `06_audit_and_metrics.py` | `metrics.evaluate_run` on R1–R3, STRESS1 with `out_root=results/analysis/recomputed`, then a diff of `deterministic_audit.jsonl` against the committed file (ignoring `created_at`) | **Yes.** This recomputes the headline numbers without the agent |
| 07 | `07_run_reports.py` | `run_report.build` per run (CHECKER vs audit matching, cost), to an analysis root | Yes. Needs an output option, since today it writes inside the run folder |
| 08 | `08_claim_verification.py` | `claim_check.score("R1")` and the owner-review counts | Yes. Must not write `explanation_claims.json` inside the R1 folder |
| 09 | `09_build_figures.py` | `figures.build(seed20261107, [B0, B1, B2, R1, R2, R3])` and the STRESS1 set → `results/figures/` | **Yes** |

The pipeline order is data → (Monte Carlo) → baselines → agent runs → copy-back verification → audit and metrics → run reports and CHECKER matching → claim verification → figures.

## 6. README outline

1. **What this is** (3 lines): decision-support agent, four departments, beds and nurses; simulated environment, not a real hospital.
2. **Where the deliverables are:**

   | Brief | Path |
   | --- | --- |
   | Code | `src/` (numbered entry scripts `src/01…09`; agents: `.claude/agents/` and `src/mcp_server/`) |
   | README | `README.md` |
   | Error analysis | `ERROR_ANALYSIS.md` (`mistakes.md` points to it) |
   | Reflection | `REFLECTION.md` |
   | Plan | `plan.md` → `docs/EVALUATION_PLAN.md` |

3. **Two files called "agents"**: `CLAUDE.md` holds the standing instructions for the coding agent, which is what the brief calls `AGENTS.md`. `docs/AGENTS.md` specifies the system's own agents (ANALYZER, ALLOCATOR, CHECKER, ORCHESTRATOR). Both keep their names.
4. **Repository map**: the target tree of §2.1, plus the brief → here table (`data/raw` = `data/raw`, `data/derived` = `data/processed`, `results/runs` and `results/baselines` → `results/allocations` and `results/evaluations` via `results/README.md`).
5. **Grading axes → evidence:**
   - *Analysis (50%)*: `results/analysis/`, `results/figures/`, `docs/EVALUATION_PLAN.md`, run reports.
   - *Reflection (30%)*: `REFLECTION.md`, `docs/REFLECTION_LOG.md`, `docs/LIMITATIONS_AND_REFLECTION.md`.
   - *Verification (20%)*:
     - the deterministic audit (`src/evaluation/audit.py`, independent of any LLM output);
     - the `department_demand_daily` vs `patient_registry` reconciliation (19 data checks);
     - claim-by-claim verification (`claim_check.py`, R1 claims and the owner review);
     - CHECKER vs audit matching (`checker_matching.py`, `run_report.json`);
     - independent re-hashes (`data/MANIFEST.json` with `manifest --verify`; `SHA256SUMS.json`/`copy_back.json` with `tests/manual/verify_copy_back_independent.py`);
     - the recomputation of the headline numbers without the agent (`src/06_audit_and_metrics.py`);
     - run-session permission checks (`tests/manual/verify_run_settings.py`).
6. **The brief's session outputs → equivalents:**
   - "choices the agent made without asking you" → Implementation Decisions Log (`docs/PROJECT_SPEC.md` §9);
   - "same question re-run" → R1, R2, R3 on `seed20261107`;
   - "headline number recomputed without the agent" → deterministic audit and metrics (`src/06`);
   - owner decisions → `docs/PROJECT_SPEC.md` §11;
   - session record → `docs/SESSION_LOG.md`.
7. **Data, keys and privacy:**
   - The data is **synthetic**: generated by `src/data_generation/` from fixed seeds, with no personal data. The registry holds only an ID, department, complexity level and arrival and discharge days.
   - No API key is used: the runs go through Claude Code subagents on a subscription.
   - **Models:** `claude-sonnet-5-5` for dispatcher, ALLOCATOR and CHECKER in all four runs (R1, R2, R3, STRESS1; `run_manifest.json` → `models`). Code at `prompts-v1.0` = `f2162c0`. Claude Code versions per launch transcript: R1 2.1.325, R2 2.1.328, R3 2.1.330, STRESS1 2.1.330. The development assistant (this repository's coding agent) is named as Claude Code, with its model stated.
   - Transcripts contain the owner's Windows username in file paths (§7). They are left unedited by owner decision.
8. **Reproduce:** §8 of this plan, as commands.
9. **Tags:** `data-v1.0`, `prompts-v1.0`, and what each freezes.

## 7. Publication scan (report only; nothing changed)

Scope: all 744 tracked files, transcripts included (`git grep -I`).

| Category | Hits | Frozen / hashed | Editable |
| --- | --- | --- | --- |
| **Windows user path / username** (`C:\Users\<user>`, `/c/Users/…`; 476 occurrences of the username) | 88 files | 62: `transcripts/launch-1.jsonl` of R1, R2, R3, STRESS1 (4); ALLOCATOR subagent transcripts `agent-*.jsonl` in the capture, the ones that reference a spilled tool result (13 + 13 + 12 + 13 = 51); `SHA256SUMS.json` of the four captures (4, the recorded session-folder path); `copy_back.json` of R2, R3, STRESS1 (3) | 26: `run_manifest.json` + launch transcripts of CHK-B2-HARD10, DRY1, DRY2, DRY3 (9); `results/evaluations/R1/allocator_digest/day_18–30.md` (13, generated views of the capture, regenerable but inside a run folder); `smoke_probe_transcript.jsonl`, `smoke_test_transcript.jsonl`, `run_settings_verification.json` (3); `tests/test_copy_back.py` (1, a path literal in a test) |
| **Email addresses** in tracked files | 0 | – | – |
| **Email in git history** | the author line of all 62 commits carries the owner's personal email | – | not a file: visible on GitHub through the commit metadata. It is **not** in a `git archive` zip. Changing it would need a history rewrite, which is forbidden. **Owner decision (2026-11-23): the commit history stays as it is; it is process evidence. No action** |
| **API keys, tokens, secrets** | **0** | – | – |
| `.env` or credential files | 0 tracked (`.env*` is ignored; `.claude/settings.local.json` is untracked) | – | – |
| Other absolute machine paths (`C:\hra-runs\…`, `AppData`, `/home/`) | about 180 files | most: the run folders and captures of R1–R3 and STRESS1 (39 each), `copy_back.json` | DRY run folders, smoke transcripts, `tests/manual/verify_copy_back_independent.py` (default clone path `C:/hra-runs/…`), and one path each in `PROJECT_SPEC.md`, `REFLECTION_LOG.md`, `SESSION_LOG.md` |

Notes:

- The spilled tool-result files themselves do not contain the username; the transcripts that point to them do. R1's `copy_back.json` has no user path. `tests/test_copy_back.py` contains a `C:\Users` literal but not the username, which is why it counts for the path pattern (88) and not for the username (87).
- Under the owner decision, all 62 frozen files stay as they are. The 26 editable files could be scrubbed, but 13 of them (R1's digest) sit inside a run folder and 9 are development transcripts, so the plan proposes **no scrub** unless the owner asks for one.
- **Secrets, individually:** the secret patterns (`sk-ant-…`, `sk-…`, `gh?_…`, `AKIA…`, private-key headers, `authorization`/`x-api-key`/cookie fields, `access_token`/`refresh_token`, `password=`) match nothing. The only hits for `oauth` are the beta-header name `oauth-2025-04-20` (639 lines in request metadata) and a sentence of Claude Code's system prompt (288 lines). The long opaque strings in the transcripts are the fields `hash`, `shapeHash` and `requestDigest` (content hashes) and `signature` (thinking-block signatures). None of these is a credential. **No secret found.**

## 8. Reproducibility after the clean-up

| Goal | Needs | Commands |
| --- | --- | --- |
| Fast suite | Python ≥ 3.12 (developed on 3.14.4), `uv` | `uv sync`, then `uv run pytest -q` (202 pass today; the full suite is `-m "slow or not slow"`) |
| Data manifest | the `data/` and `src/data_generation/` bytes unchanged (`.gitattributes` keeps them `-text`) | `uv run python -m src.data_generation.manifest --verify` (add `--regenerate` for a byte-exact rebuild) |
| Audit and metrics on the committed runs | the run folders and datasets | `uv run python src/06_audit_and_metrics.py`, which writes to `results/analysis/recomputed/` and reports equal or different |
| Figures | matplotlib (in the lock file) | `uv run python src/09_build_figures.py` |
| Copy-back hashes | the repository only (`--sums-only`) | `uv run python src/05_verify_copy_back.py --sums-only` |
| Agent runs | the `claude` CLI with a subscription, a clone outside OneDrive | not reproducible by a grader. Commands documented in `src/04_agent_run.py` |

**Windows:**

- The longest repository path is 132 characters, so a clone or unzip under a short root such as `C:\hra\` works without long-path support.
- Under a deep root (the owner's OneDrive root of 132 characters reaches 265), set `git config core.longpaths true` before checkout. `core.longpaths` is a local git setting and does not travel with a clone.
- Alternatively enable `LongPathsEnabled` (administrator, `HKLM\SYSTEM\CurrentControlSet\Control\FileSystem`). It is 0 on the owner's machine.
- Readers in `src/` and the independent check use the `\\?\` form, so they work either way. git and Explorer do not.
- **Line endings:** `.gitattributes` forces LF and marks data, configs and the owner extraction `-text`. A zip made with `git archive` keeps the committed bytes, while a zip of the working tree on a machine with `core.autocrlf` may not. **The submission zip should be built with `git archive --format=zip HEAD`**, which also leaves out `.venv/` and the caches.

## 9. Phase 1b execution order (on branch `cleanup`)

After each step: `uv run pytest -q`, `uv run python -m src.data_generation.manifest --verify`, and `tests/manual/verify_copy_back_independent.py` on R1, R2, R3 and STRESS1, all four `RESULT: OK`. Commit only when pytest itself exits 0.

1. `git switch -c cleanup`. Baseline: the three checks above, recorded.
2. `git mv` the seven development run folders into `results/development/{allocations,evaluations}/`, and `results/dry_runs/` into `results/development/dry_runs/`. Update the four tests (§3.3) in the same commit. Verify.
3. `git mv results/visualizations/HARD10 results/development/figures/HARD10`; change the `figures.py` default to `results/figures/`; log the change. Verify.
4. U1 files, as decided by the owner. Update the two manual scripts' defaults. Verify.
5. Add the output-root options (`src.evaluation --out`, `run_report --out`, `claim_check` output) and `--sums-only` for the independent check, with tests that write to `tmp_path` and leave the committed files untouched (R59). Verify.
6. Add `src/01…09` entry scripts. Run 01, 06 and 09 once and check that the run folders are unchanged (`git status` clean outside `results/analysis/` and `results/figures/`). Verify.
7. Add `results/README.md`, `README.md` (rewrite), `plan.md`, `mistakes.md` pointer, and skeletons of `ERROR_ANALYSIS.md` and `REFLECTION.md` (content comes with the analysis). Update the `CLAUDE.md` §0 tree and `PROJECT_SPEC.md` §0/§1. Put a one-line note on old paths at the top of the historical logs. Verify.
8. Full suite (`-m "slow or not slow"`) and the manifest check, as a milestone. Re-measure path lengths (expect 132 maximum). Re-run the §7 scan (expect the same counts, with paths shifted for the moved development files).
9. Owner review, then merge `cleanup` into `main` (fast-forward, no history rewrite).

## 10. Post-clean-up path note for `docs/EVALUATION_PLAN.md` (2026-11-24, Log #126)

`docs/EVALUATION_PLAN.md` is pre-registration text and stays byte-identical (Log #124). Its two references to development paths that moved in Phase 1b resolve as follows:

| `EVALUATION_PLAN.md` | Path as written | Path now |
| --- | --- | --- |
| §4 item 7 (hours estimate) | `results/evaluations/DRY2-HARD10/make_full_claims.py` | `results/development/evaluations/DRY2-HARD10/make_full_claims.py` |
| §10 (figure plan) | `results/visualizations/HARD10/` | `results/development/figures/HARD10/` |

Every other path in `EVALUATION_PLAN.md` is unchanged by the clean-up.
