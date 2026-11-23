# Results index

Every table and figure here was made by code in [`src/`](../src/). Run folders follow one convention: `allocations/<run_id>/` holds the records a run wrote (allocations, bed assignment, decisions, transcripts), and `evaluations/<run_id>/` holds what was computed from them (deterministic audit, metrics, run report). The agent runs are **frozen**: they were copied back from the run clone with hash manifests, and any write into them raises an error (`src/utils/paths.py`, `guard_write`).

## Runs (the four agent runs)

| Run | Dataset | Records | Audit, run report, copy-back manifest |
| --- | --- | --- | --- |
| R1 | `seed20261107` | [`allocations/R1/`](allocations/R1/) | [`evaluations/R1/`](evaluations/R1/) |
| R2 | `seed20261107` | [`allocations/R2/`](allocations/R2/) | [`evaluations/R2/`](evaluations/R2/) |
| R3 | `seed20261107` | [`allocations/R3/`](allocations/R3/) | [`evaluations/R3/`](evaluations/R3/) |
| STRESS1 | `seed20261107_stress` (forced-cut probe, reported separately) | [`allocations/STRESS1/`](allocations/STRESS1/) | [`evaluations/STRESS1/`](evaluations/STRESS1/) |

- Each `allocations/<run>/transcripts/` folder holds the dispatcher's launch transcript and, under `subagents/`, every ALLOCATOR and CHECKER transcript, with `SHA256SUMS.json`.
- `evaluations/<run>/copy_back.json` records the SHA-256 of every file copied back.
- R1's claim-verification and owner-review material is in [`evaluations/R1/`](evaluations/R1/): `explanation_claims_spec.json`, `explanation_claims.json`, `claims_extraction/`, `owner_extraction/`, `owner_review/`, `allocator_digest/`.

## Baselines

B0 (no reallocation), B1 (clinical-priority-first) and B2 (proportional), each on the four datasets. They are deterministic, so there is one run each: `allocations/B?-<dataset>/` and `evaluations/B?-<dataset>/`, for example [`evaluations/B1-seed20261107/`](evaluations/B1-seed20261107/). The headroom table is [`evaluations/headroom.json`](evaluations/headroom.json). `seed20261108` and `seed20261109` are robustness seeds (baselines only). Rebuilt and compared by `src/03_run_baselines.py`.

## Analysis

[`analysis/`](analysis/): cross-run results (R1–R3 against the baselines, STRESS1, CHECKER matching). *To be completed.* Recomputations by the numbered scripts land in `analysis/recomputed/`, which is not committed.

## Figures

[`figures/`](figures/): static figures per dataset, built by `src/09_build_figures.py`. *To be completed.*

## Verification

[`verification/`](verification/):

- [`copy_back/`](verification/copy_back/): the independent re-hash of the four runs (`tests/manual/verify_copy_back_independent.py`), in two modes. `<run>_full.txt` compares against the run clone and the Claude Code session folders (owner's machine). `<run>_sums_only.txt` compares against the manifests in this repository.
- [`pre_run/`](verification/pre_run/): the smoke test of the run-session restrictions (`smoke_test.json` and its transcripts), and the run-settings probe (`run_settings_verification.json`).

## Development

[`development/`](development/): the dry runs and synthetic fixtures used to build and test the system. They are not results. See [`development/README.md`](development/README.md).
