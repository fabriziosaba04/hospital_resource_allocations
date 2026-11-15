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

Further conventions fixed while extracting (all applied from the day they first occurred onward; earlier days had no
instance):

- **Scope of text.** Only the six explanation fields of each day's accepted submission. In R1 every day was accepted at
  attempt 1, so there are no rejected submissions; the ALLOCATOR's free text outside `submit_decision` is not an
  explanation and is not extracted.
- **Past tense** (item 2): a pool "fell from X" is `pool_*` on day d-1 (`day` = d-1 in the entry; the id keeps day d).
- **Invalid allocations.** Outcomes of an allocation that fails validation that day are unverifiable (item 2) and are
  written with `quantity` null and the intended quantity in `note` (days 8, 21, 23). Statements of the in-effect
  allocation itself on shock days (beds or nurses figures, days 8, 11, 16, 21, 23, 26) are encoded with `cur`. **Check
  before recomputation:** `claim_check.quantity` simulates before returning `beds` / `nurses`; if the engine returns no
  assignment for an invalid allocation, these figures would come out unverifiable instead of being compared.
- **"Idle beds", "surplus beds"** are not rubric terms: read as empty (`empty_beds`), `rubric_term` "idle" /
  "surplus", no rival reading. Bare "idle nurses" is a requirement figure (outside); nurse slack stated in need units
  ("0.2 of rounding", "0.55 unused above need", "2 above need") is restated as `need` or `covered_need` (note).
- **Comparisons.** "worse", "more", "less" on a named quantity use `ge_alloc` / `le_alloc` (not strict; noted);
  "worse by clinical priority" and "nurse coverage is worse" use `lex_le_alloc` with the §11 #57 rival reading.
- **Ambiguous or vague**, `quantity` null: "covered elsewhere" / "other departments cover" (some or all?), "many",
  "partly", "almost", "mostly", "some". Also null when the figure is verifiable but not a `claim_check` quantity
  (optimality claims, groups selected by arrival day, occupied plus queued minimums on day 30); each says so in `note`.
- **Patient attributes** (arrival day, days waited) are outside the universe; a named patient in or out of a bed is in.
- **Presence without a count** ("L3 in IM and neurology", "hold spare beds", "leaves IM short") is `ge 1`, one claim
  per named department or level.
