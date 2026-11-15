# R1 claim extraction (EVALUATION_PLAN.md §4 items 1–9)

`../explanation_claims_spec.json` is built from the batch files here (`days_NN_MM.py`, one per five days) with
`python add_claims.py <batch> ../explanation_claims_spec.json`. Sources read: the rubric, `../allocator_digest/day_NN.md`,
`results/allocations/R1/decision_history.jsonl`, and `src/evaluation/claim_check.py` (code only) — access rule §11 #58.
No CHECKER file, audit or run report was read. The spec has no `disputed_by_checker`.

Encoding conventions (implementation-level, applied uniformly):

- **Allocations.** `cur` = `{"in_effect": d-1}` (the allocation in effect when day d starts; the ALLOCATOR's "current"
  or "A"); `dec` = `{"decided": d}`; tested alternatives are written out from the `simulate_allocation` call. Proposed
  allocations are definitions, not claims; statements of the allocation in effect are claims.
- **Occupied** = `holders`; **queue / waiting** = `queue`; **overflow** of an allocation = `overflow`.
- **Spare / free** (§11 #59): bare → strict (`spare_beds`, `free_beds`) with rival `empty_beds`; "above census" →
  `empty_beds`, "above occupied" → `spare_beds`, no rubric term. Category `empty_beds` for department spare/empty,
  `pool` for hospital free beds.
- **Nurse slack against the N1 requirement** ("1 spare nurse", "2 nurses short hospital-wide", "0 idle nurses") is a
  requirement figure, outside the universe (item 1), and is not extracted. Census, arrivals and requirement likewise.
- **"Per department" ranges** are one claim per department, relation `in_range` with `[lo, hi]` (item 2: correct if
  the value lies inside). `claim_check.py` does not implement `in_range` yet; it must be added before recomputation.
- **Repeats.** A figure restated in another field, or a restatement of an already extracted outcome ("identical
  outcomes", "no level 3, 2 or 1 patient in overflow" after "0 overflow"), is extracted once, at its first occurrence.
- **Basis** (item 8): copied only when the stated value is one cell of a tool result received that day before the
  accepted submission, for the same quantity, departments, levels and allocation; totals, counts of a list, spare /
  empty / free beds and comparisons are derived. A named patient in overflow is copied from `overflow_patients`.
- **Decimals** use relation `round` (compared at the stated precision); "about N" likewise.
