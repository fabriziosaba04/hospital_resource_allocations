# Evaluation Plan

**Status: metric formulas and the CHECKER severity scale fixed by the owner on 2026-11-12, before any agent output was seen** (`PROJECT_SPEC.md` §11 #16–#23). Baseline outputs may be seen before the headline set is confirmed; agent outputs may not (§8). Principles are in `CLAUDE.md` §7 and §10.L, and implementation details in [`PROJECT_SPEC.md`](PROJECT_SPEC.md).

Tags: **[S]** follows directly from the spec; **[J]** was a judgment call, approved by the owner on 2026-11-12.

## 1. Question

Does the LLM ALLOCATOR make better allocation decisions than simple deterministic strategies, facing the same environment, while respecting clinical priority first, then fairness, then efficiency? And how reliable and consistent is it?

**Framing on the per-day bed metric (owner, 2026-11-12).** B1 (clinical-priority-first) scores **0 on A1 by construction**: it is an optimal myopic rule for that metric. On A1 the question is therefore "does the agent match an optimal myopic rule, and where does it fail?", not "does it beat it". The agent's possible advantage lies in the **path component of A3** (placements that avoid blocking beds later) and in **nurse rationing (A2)**. The headroom available there is quantified from the baselines in §8.

## 2. Notation

All quantities are computed **within the horizon, days 1 … H**, from the run records (Bed Assignment State, Allocation State), the registry (department, level, `arrival_day`, presence) and the pools.

| Symbol | Meaning |
| --- | --- |
| d, k, t | Department, complexity level, day |
| j | Tier: "level j or higher", j ∈ {1, 2, 3}. A superscript ≥j restricts a set or count to that tier |
| n_{k,d}(t) | Present level-k patients in d, including overflow |
| H_d(t) | **Holders**: patients in a bed in d at the end of t−1 who are still present on t. On day 1 they are the patients placed by the initial assignment (Log #21). O_d(t) = \|H_d(t)\| |
| Q_d(t) | Present patients in d who are not holders |
| M(t) | Movable beds, `P_B(t) − Σ_d O_d(t)` |
| r_d(t) | Cap room for holders, `max_beds − O_d(t)` |
| **Movable bed** | One of the `B_d(t) − O_d(t)` beds of d not protected by no-eviction. It either serves a non-holder admitted that day or is empty. **An empty bed counts as level 0** [J] |
| **Shock day** | `Σ_d O_d(t) > P_B(t)`; then c(t) = `Σ_d O_d − P_B` holders must be cut and no movable beds exist |
| OF_{k,d}(t) | Level-k patients in overflow in d on day t |
| need_{k,d} | `w_k · n_{k,d}`, exact; a_{j,d} = `Σ_{k≥j} need_{k,d}` |
| covered, shortage | From coverage rule C1 (`PROJECT_SPEC.md` §5.4). Tier coverage in d is `min(N_d, a_{j,d})` |
| req_d | N1 requirement, `⌈a_{1,d}⌉` |
| B_d, N_d, P_B, P_N | As in `CLAUDE.md` §10 |

## 3. Metric Definitions (fixed 2026-11-12)

### 3.1 A1. Bed clinical gap: SV_B (headline)

**Normal day** (Σ O_d ≤ P_B), for each tier j:

```
Max_j(t) = Σ_d |H_d^{≥j}| + min( M, Σ_d min(|Q_d^{≥j}|, r_d) )
Ach_j(t) = level-≥j patients in a bed on day t
gap_j(t) = Max_j(t) − Ach_j(t)   ≥ 0
```

**Shock day:** `Max_j(t) = |H^{≥j}| − max(0, c − |H^{<j}|)` (the c cuts fall on the lowest-level holders hospital-wide); `Ach_j` as above.

`SV_B = Σ_t Σ_j gap_j(t)`. **Unit:** severity-weighted patient-days. **Lower is better; floor 0.**

**Pairing (the same quantity, by type).** [S] `CLAUDE.md` §10.G, `EVALUATION_PLAN` §3.1 (2026-11-07), §11 #3.

- *Normal day:* unserved patients (non-holders in overflow in d with `max_beds − B_d > 0`) are taken from the highest level down. Each is paired with the lowest-level movable bed in another department d′ ≠ d serving level k′ < k (empty = 0). A pair uses one unit of d's room. Severity `k − k′`. Type **displaced** if k′ ≥ 1, **empty** if k′ = 0.
- *Shock day:* cut holders, highest level first, are each paired with the lowest-level kept holder of level k′ < k in another department. Severity `k − k′`. Type **shock-cut**.

Σ over pairs of `k − k′` equals SV_B: a pair (k, k′) crosses exactly the tiers k′ < j ≤ k. The audit computes both and records any mismatch as a Critical issue. The equality was checked on 20,000 random normal days before the formulas were fixed, and is a test for both day types (§7).

- **Net of unavoidable:** Max_j respects the cap and the pool, so cap-blocked overflow and hospital shortfall never count [S].
- **Independence:** the closed form is the audit's own code; the pairing is the environment's clinical-violation detector (§5.6). They are cross-checked.
- ⚠ **B1 scores 0 by construction** (§1). This metric can show the agent matching B1, never beating it.
- ⚠ The gap is per day, given that day's holders. Path damage (a bed blocked today by a low-level placement yesterday) appears in A3.

### 3.2 A2. Nurse clinical gap: SV_N per tier (headline, read lexicographically)

For each tier j:

```
cov_j(N)  = Σ_d min(N_d, a_{j,d})
MaxN_j(t) = max over integer N ≥ 0 with Σ_d N_d = P_N of cov_j(N)
          = Σ_d a_{j,d}                                       if P_N ≥ Σ_d ⌈a_{j,d}⌉
          = P_N                                               if P_N ≤ Σ_d ⌊a_{j,d}⌋
          = Σ_d ⌊a_{j,d}⌋ + (sum of the P_N − Σ_d ⌊a_{j,d}⌋ largest fractional parts of a_{j,d})   otherwise
gapN_j(t) = MaxN_j(t) − cov_j(N(t))
L(t)      = lexicographic minimum of (gapN_3, gapN_2, gapN_1) over all integer allocations   (rounding floor)
SV_N,j    = Σ_t ( gapN_j(t) − L_j(t) )
```

**Unit:** nurse-days of N1 need. **Lower is better; floor 0 per tier as long as the higher tiers are at their floor.** Read SV_N,3 first, then SV_N,2, then SV_N,1. A negative value at a lower tier can only come with a positive value at a higher tier.

- **Weighting:** covering one unit of L1 instead of L3 adds 1 to tiers 3 and 2, i.e. the level difference [S].
- **Idle-nurse type included:** an idle nurse while higher-level need is uncovered elsewhere counts, as the nurse analogue of §11 #3 (approved).
- **Three-case closed form** (corrected 2026-11-12, REFLECTION_LOG R17): the middle case, `P_N ≤ Σ⌊a⌋`, occurs at tier 1 on rationing days.
- **Independence:** the environment uses the closed form; the audit enumerates every integer allocation (about 10⁴ per day) for MaxN_j and L(t). They are cross-checked.
- **Rounding floor:** per-tier maxima are not always reachable together, because one nurse can straddle two levels. L(t) is the best any allocation can do, read lexicographically.

### 3.3 A3. Overflow by tier: raw, floor and excess (headline for tiers 3 and 2)

```
raw_j    = Σ_t OF^{≥j}(t)                                                       patient-days
floor_j  = Σ_t [ n^{≥j}(t) − min(P_B(t), Σ_d min(n_d^{≥j}(t), max_beds)) ]     policy-independent
excess_j = raw_j − floor_j = avoid_j + path_j
avoid_j  = Σ_t gap_j(t)                       (avoidable today, = A1 at tier j)
path_j   = excess_j − avoid_j  ≥ 0            (caused by earlier placements protected by no-eviction)
```

- floor_1 covers both rows of the structural table (cap excess and hospital shortfall, §3.6 of the 2026-11-11 plan). floor_j is `ovf_min` of Decisions Log #33 per tier [J].
- Subtracting a policy-independent floor does not change rankings, so this keeps the rule that hospital shortfalls are reported as the floor, not attributed.
- path_j ≥ 0 always (proof in `PROJECT_SPEC.md` §9, Log #50; tested).
- ⚠ raw_1 is almost the same for every work-conserving policy; the information is in tiers 3 and 2.

### 3.4 A4. Nurse shortage by level (secondary)

`S_k = Σ_t Σ_d shortage_{k,d}(t)` (nurse-days of need). Tier floor `Σ_t (Σ_d a_{j,d} − MaxN_j)`. Nurses are freely reassignable, so the tier excess equals Σ_t gapN_j: context for A2, not a separate score.

### 3.5 B. Fairness (secondary)

| Metric | Formula | Unit |
| --- | --- | --- |
| **B1 Overflow-rate dispersion**, per level | `D_k = max_d OR_{k,d} − min_d OR_{k,d}`, with `OR_{k,d} = Σ_t OF^net_{k,d} / Σ_t n_{k,d}`, over departments with `Σ_t n_{k,d} > 0`. **Net:** each day, the cap excess `max(0, n_d − max_beds)` is removed from d's overflow patients from the lowest level upward [J]. Denominators are reported | percentage points |
| **B2 F1 inversions**, per level | Normal days only. A level-k patient p in overflow in d (with `max_beds − B_d > 0`) while a level-k patient q with a **later** `arrival_day` was admitted that day to a movable bed in d′ ≠ d. Per level, overflowed patients (oldest first) are paired with admitted patients (newest first); each pair uses a unit of d's room. Count, and the total `arrival_q − arrival_p` [J] | patient-days; days |
| **B3 Wait distribution**, per level | Among patients ever in overflow within the horizon: mean and maximum of their overflow days. Replaces "mean days in overflow" (REFLECTION_LOG R14). Right-censored at day H | days |

- ⚠ B1: equal overflow everywhere scores 0, so it is read only alongside A1 and A3. Small denominators (for example Orthopedics L3) make it noisy.
- B2: B1 scores 0 by construction (tested). Within a department the assignment rule already enforces arrival order, so only cross-department inversions count.

### 3.6 C. Efficiency and B4 (descriptive only)

| Metric | Formula | Unit |
| --- | --- | --- |
| C1 Bed utilisation | `Σ_t occupied / Σ_t P_B` | share |
| C2 Avoidable idle beds | `Σ_t gap_1(t)` restricted to empty-type pairs; the empty-bed part of A1, **not scored twice** | bed-days |
| C3 Nurse utilisation | `Σ_t Σ_d min(N_d, req_d) / Σ_t P_N` | share |
| C4 Avoidable idle nurses | `Σ_t min(Σ_d max(0, N_d − req_d), Σ_d max(0, req_d − N_d))`; unavoidable part `Σ_t max(0, P_N − Σ_d req_d)` | nurse-days |
| B4 Relative nurse coverage dispersion | `RC_{k,d} = Σ_t covered_{k,d} / Σ_t need_{k,d}`; `max_d − min_d` | ratio |

C2 and C4 are contained in A1 and A2: in this model, bed and nurse inefficiency are already clinical violations.

### 3.7 D. Feasibility: a gate, not a metric

- **Gate:** zero hard-constraint violations **in effect**, checked by the audit's own implementation. Otherwise the run is **not interpreted** (a Critical issue, §4).
- **Reported:** rejected **submissions** by code, ALLOCATOR failure days (repair applied), halts. Calls to `validate_allocation` are free and never counted.

### 3.8 E. Stability

**Reference:** `R(t)` = the repair rule (`PROJECT_SPEC.md` §5.7) applied to the allocation in effect at t−1 (on day 1, the initial allocation), i.e. what B0 would do from the same starting point [J].

```
τ_d(t) = B_d(t) − R_d(t)                (Σ_d τ_d = 0); the same for nurses
RS(t)  = ½ Σ_d |τ_d(t)|                 reallocation size
```

- **Reversals (headline for beds; secondary for nurses):** for each department and resource, units of τ_d of one sign on day t1 matched with units of the opposite sign on t2, `0 < t2 − t1 ≤ W`, oldest unmatched units first; units older than W expire. Count matched units. **W = 3** (the L1 mean stay); **W = 2 and W = 5 are pre-registered sensitivity checks**. Unit: beds (nurses).
- **Descriptive only:** RS and reallocation frequency (days with RS > 0). Reallocation is the task, not a cost.
- On days with no pool change, RS equals the 2026-11-07 formula `½(Σ|ΔB_d| − |ΔP_B|)`.
- B0 has τ = 0 by definition.

### 3.9 F. Explanation quality (qualitative, LLM-dependent)

Assessed by the LLM CHECKER only, reported qualitatively and **labelled LLM-dependent**. It is not part of verification (REFLECTION_LOG R13).

### 3.10 Headline set (to be confirmed after the headroom review, §8)

| Role | Metrics |
| --- | --- |
| **Headline** | SV_B (A1) with its displaced / empty / shock-cut split; SV_N per tier, lexicographic (A2); A3 excess for tiers 3 and 2, split into avoid and path; bed reversals within W = 3 |
| **Gate** | D |
| **Secondary** | B1, B2, B3, A4, nurse reversals |
| **Descriptive** | RS and frequency, C1–C4, B4 |

**No combined score.**

## 4. CHECKER Severity Scale (fixed 2026-11-12)

**Categories** [S: the three categories; J: the test]:

- **Violation:** a rule check from `CLAUDE.md` §10.E, §10.G or `AGENTS.md` §3.2 returns true.
- **Concern:** no rule is broken, but there is a measurable cost (patient-days, nurse-days, beds moved) against an alternative feasible that day, or a statement contradicted by the records.
- **Improvement:** no measurable cost; process or explanation quality only.

**Levels** [J]. Named, so they do not clash with the numeric clinical severity 1–3, which remains the clinical measure [S]:

| Level | Criteria | Issues |
| --- | --- | --- |
| **Critical** | The experiment itself is compromised | A hard constraint broken in an allocation **in effect** (validator bug); a temporal or information leak; a record by the wrong writer; a replay mismatch; a pairing/closed-form mismatch in the audit |
| **Major** | Clinical severity ≥ 2, or a failed day | Bed or shock-cut pair with `k − k′ ≥ 2`; a day with a positive net nurse gap at tier 3; an ALLOCATOR failure day (all N submissions rejected, repair applied); an explanation that misstates a clinical outcome |
| **Moderate** | Clinical severity 1, or a caught rule breach | Bed or shock-cut pair with `k − k′ = 1`; a day whose positive net nurse gap is only at tiers 2 or 1; a rejected **submission** later corrected the same day; an F1 inversion; an explanation that misstates a non-clinical number |
| **Minor** | Low cost, or process only | A bed or nurse reversal within W; a reallocation that changed no patient outcome; a §3.6 explanation field missing or empty; a modification submitted without a `simulate_allocation` call |

Nurse issues are graded by the **highest tier with a positive net gap**, not by level difference, because need units do not pair cleanly [J].

**Use in evaluation:**

1. The deterministic audit assigns category and level to every deterministic issue type by these rules. The same rules apply to the baselines; explanation and process items do not apply to them.
2. Runs are compared on **issue counts by level, lexicographically** (Critical, then Major, then Moderate, then Minor). No weighted sum (`CLAUDE.md` §10.I).
3. **Any Critical issue blocks interpretation** of the run until it is explained (and logged in `REFLECTION_LOG.md`).
4. **CHECKER-versus-audit matching is a primary Verification output:** the LLM CHECKER's issues are matched to deterministic issues on (day, type); report recall, precision and level agreement. Issues only the LLM can raise (explanation accuracy) are reported separately as LLM-dependent.

**Examples:**

1. Cardiology has 35 beds (cap 40) and an L3 patient in overflow; a freed Orthopedics bed goes to a newly arrived L1 patient → displaced pair, severity 2, **Major**.
2. As 1, but the bed is left empty in Neurology → empty pair, severity 3, **Major**.
3. An Internal Medicine L2 patient overflows while an Orthopedics movable bed goes to an L1 patient → severity 1, **Moderate**.
4. As 1, but Cardiology is at 40 beds → **no issue**: structural, reported as context.
5. Stress variant, day 23, forced cut of 6: an L2 holder in Neurology is cut while an L1 holder in Orthopedics is kept → shock-cut pair, severity 1, **Moderate**. Cutting 7 is `SHOCK_OVERCUT`: a rejected submission is **Moderate**; in effect it is **Critical**.
6. Three rejected **submissions**, then the repair rule → ALLOCATOR failure day, **Major**. Any number of `validate_allocation` calls before a valid submission → no issue.
7. Two L2 patients overflow, in Internal Medicine since day 12 and in Cardiology since day 14; the free bed goes to Cardiology while Internal Medicine has room → F1 inversion of 2 days, **Moderate** concern.
8. Cardiology gains 3 beds on day 14 and loses 3 on day 16 with no pool change → reversal of 3 within W, **Minor** concern.
9. An explanation says "no L3 in overflow" while the records show one → **Major** concern. An empty `alternatives` field → **Minor** improvement.

## 5. Baselines

| ID | Strategy | Algorithm |
| --- | --- | --- |
| B0 | No reallocation | `PROJECT_SPEC.md` §6 |
| B1 | Clinical-priority-first | `PROJECT_SPEC.md` §6 |
| B2 | Proportional | `PROJECT_SPEC.md` §6 |

- All baselines start from the common initial allocation.
- They use the same datasets, hard constraints, intra-department rule and deterministic audit as the agent.
- No baseline is claimed to be optimal in general. B1 is optimal **for A1 and B2 only** (tested), and on the day, not over the horizon.

## 6. Run Plan

1. **Datasets:** frozen at `data-v1.0`; the manifest check must pass.
2. **Baselines** B0, B1 and B2 on the primary dataset, the two robustness seeds and the stress variant. They are deterministic, so one run each.
3. **Agent runs** R1, R2 and R3 on the **same** primary dataset, each a fresh run in a run session. Differences between runs isolate LLM variability.
4. **Stress run (planned, owner 2026-11-12):** one agent run on `seed20261107_stress`, with B0–B2 as reference. It stays **excluded from the main comparisons** and is reported separately as a probe of forced-cut handling. Before any use, the shock-day A1 pairing is tested against the closed form (§7).
5. **Robustness:** the baselines on the two extra seeds, reported as an appendix. Agent results rest on the primary dataset only (declared limitation).
6. **Metrics** for every run with the same code, plus the verification checks (§7).

## 7. Verification Checks

These checks are independent of any LLM output.

| Check | What it verifies |
| --- | --- |
| Dataset reconciliation (`DATA_DICTIONARY.md` §4.1) | Operations and registry tables agree, since they are produced independently |
| Integrity and generation constraints (`DATA_DICTIONARY.md` §4.2–4.3) | Dataset validity, including `total_beds ≤ 4 × max_beds` |
| Deterministic audit | Hard constraints (own implementation), clinical gaps, metrics, for every five-day period |
| Validator vs. audit cross-check | Two independent implementations of the hard constraints agree |
| A1 pairing vs. closed form | Normal and shock days; any mismatch is Critical |
| A2 closed form vs. enumeration | All three cases of the closed form |
| Replay check | The audit's own assignment rule reproduces the stored Bed Assignment State exactly |
| Repair and baseline properties | Repair is always feasible; every baseline allocation passes the validator; B1 scores 0 on A1 and B2; B0 has τ = 0 |
| Temporal-leak tests | No tool response contains post-day-t data or the `discharge_day` of present patients |
| Smoke test (`AGENTS.md` §2.4) | Tool whitelists, server isolation and dispatcher restrictions |
| **CHECKER vs. audit matching** | Recall, precision and level agreement of the LLM CHECKER (§4) — a primary Verification output |

## 8. Headroom (baselines only)

*Computed 2026-11-12 from the baseline runs (`uv run python -m src.evaluation`; `results/evaluations/headroom.json`). No agent output exists at this point.* For each metric: B0 / **B1** / B2, the per-metric floor (– where no floor is computed), and B1 − floor per seed. A floor of 0 for an excess, a gap or a count is a **lower bound**, not a value known to be reachable over the horizon, so B1 − floor is an **upper bound on the headroom** below B1.

### 8.1 Main datasets (primary and robustness seeds)

| Metric | `seed20261107` B0 / B1 / B2 | `seed20261108` B0 / B1 / B2 | `seed20261109` B0 / B1 / B2 | Floor | B1 − floor |
| --- | --- | --- | --- | --- | --- |
| A1 SV_B | 280 / **0** / 3 | 265 / **0** / 19 | 257 / **0** / 0 | 0 | 0 / 0 / 0 |
| A1 displaced severity | 8 / **0** / 3 | 24 / **0** / 19 | 0 / **0** / 0 | 0 | 0 / 0 / 0 |
| A1 empty severity | 272 / **0** / 0 | 241 / **0** / 0 | 257 / **0** / 0 | 0 | 0 / 0 / 0 |
| A1 shock-cut severity | 0 / **0** / 0 | 0 / **0** / 0 | 0 / **0** / 0 | 0 | 0 / 0 / 0 |
| A2 SV_N tier 3 | 8.8 / **0** / 0 | 44 / **0** / 2.4 | 6.4 / **0** / 0 | 0 | 0 / 0 / 0 |
| A2 SV_N tier 2 | 67.9 / **1.05** / 6.85 | 83.9 / **2.3** / 13.9 | 53.2 / **0** / 0.45 | 0 | 1.05 / 2.3 / 0 |
| A2 SV_N tier 1 | 65.8 / **1.2** / 0.85 | 55.75 / **1.85** / 1.75 | 90.8 / **0.45** / 0.2 | 0 | 1.2 / 1.85 / 0.45 |
| A3 tier 3 raw | 12 / **0** / 0 | 22 / **0** / 2 | 14 / **0** / 0 | 0 | 0 / 0 / 0 |
| A3 tier 3 excess | 12 / **0** / 0 | 22 / **0** / 2 | 14 / **0** / 0 | 0 | 0 / 0 / 0 |
| A3 tier 3 avoid | 12 / **0** / 0 | 22 / **0** / 2 | 14 / **0** / 0 | 0 | 0 / 0 / 0 |
| A3 tier 3 path | 0 / **0** / 0 | 0 / **0** / 0 | 0 / **0** / 0 | 0 | 0 / 0 / 0 |
| A3 tier 2 raw | 106 / **1** / 4 | 119 / **4** / 23 | 73 / **0** / 0 | 0 | 1 / 4 / 0 |
| A3 tier 2 excess | 106 / **1** / 4 | 119 / **4** / 23 | 73 / **0** / 0 | 0 | 1 / 4 / 0 |
| A3 tier 2 avoid | 106 / **0** / 3 | 104 / **0** / 17 | 73 / **0** / 0 | 0 | 0 / 0 / 0 |
| A3 tier 2 path | 0 / **1** / 1 | 15 / **4** / 6 | 0 / **0** / 0 | 0 | 1 / 4 / 0 |
| E bed reversals W3 | 0 / **116** / 114 | 0 / **109** / 110 | 0 / **103** / 103 | 0 | 116 / 109 / 103 |
| B1 dispersion L1 (pp) | 49.19 / **6.09** / 2 | 49.48 / **5.52** / 10.61 | 67.02 / **0** / 0 | – | – / – / – |
| B2 F1 inversions L1 | 40 / **0** / 1 | 37 / **0** / 5 | 48 / **0** / 0 | 0 | 0 / 0 / 0 |
| B3 mean overflow days L1 | 2.324 / **1** / 1.056 | 1.69 / **1.345** / 1.31 | 1.98 / **0** / 0 | – | – / – / – |
| B1 dispersion L2 (pp) | 34.37 / **0.41** / 2.1 | 26.88 / **0.93** / 4.63 | 24.79 / **0** / 0 | – | – / – / – |
| B2 F1 inversions L2 | 46 / **0** / 0 | 41 / **0** / 4 | 36 / **0** / 0 | 0 | 0 / 0 / 0 |
| B3 mean overflow days L2 | 2.35 / **1** / 1 | 2.622 / **1** / 1.615 | 3.278 / **0** / 0 | – | – / – / – |
| B1 dispersion L3 (pp) | 3.68 / **0** / 0 | 6.07 / **0** / 0.32 | 5.04 / **0** / 0 | – | – / – / – |
| B2 F1 inversions L3 | 1 / **0** / 0 | 5 / **0** / 0 | 3 / **0** / 0 | 0 | 0 / 0 / 0 |
| B3 mean overflow days L3 | 1.091 / **0** / 0 | 1.294 / **0** / 1 | 1.4 / **0** / 0 | – | – / – / – |
| A4 shortage L3 | 8.8 / **0** / 0 | 44 / **0** / 2.4 | 6.4 / **0** / 0 | – | – / – / – |
| A4 shortage L2 | 63.2 / **5.15** / 10.95 | 70.1 / **32.5** / 41.7 | 46.8 / **0** / 0.45 | – | – / – / – |
| A4 shortage L1 | 33.95 / **36.2** / 30.05 | 29.3 / **57** / 45.3 | 40.2 / **3.05** / 2.35 | – | – / – / – |
| E nurse reversals W3 | 0 / **47** / 48 | 0 / **26** / 34 | 0 / **39** / 40 | 0 | 47 / 26 / 39 |

### 8.2 Stress variant (separate probe, excluded from the main comparisons)

| Metric | `seed20261107_stress` B0 / B1 / B2 | Floor | B1 − floor |
| --- | --- | --- | --- |
| A1 SV_B | 231 / **0** / 11 | 0 | 0 |
| A1 displaced severity | 8 / **0** / 11 | 0 | 0 |
| A1 empty severity | 223 / **0** / 0 | 0 | 0 |
| A1 shock-cut severity | 0 / **0** / 0 | 0 | 0 |
| A2 SV_N tier 3 | 8.8 / **0** / 0 | 0 | 0 |
| A2 SV_N tier 2 | 67.9 / **1.05** / 6.85 | 0 | 1.05 |
| A2 SV_N tier 1 | 65.8 / **1.2** / 0.85 | 0 | 1.2 |
| A3 tier 3 raw | 20 / **3** / 12 | 0 | 3 |
| A3 tier 3 excess | 20 / **3** / 12 | 0 | 3 |
| A3 tier 3 avoid | 17 / **0** / 9 | 0 | 0 |
| A3 tier 3 path | 3 / **3** / 3 | 0 | 3 |
| A3 tier 2 raw | 108 / **38** / 42 | 38 | 0 |
| A3 tier 2 excess | 70 / **0** / 4 | 0 | 0 |
| A3 tier 2 avoid | 69 / **0** / 2 | 0 | 0 |
| A3 tier 2 path | 1 / **0** / 2 | 0 | 0 |
| E bed reversals W3 | 0 / **115** / 104 | 0 | 115 |
| B1 dispersion L1 (pp) | 42 / **6.45** / 7.37 | – | – |
| B2 F1 inversions L1 | 39 / **0** / 4 | 0 | 0 |
| B3 mean overflow days L1 | 2.156 / **1.537** / 1.513 | – | – |
| B1 dispersion L2 (pp) | 22.85 / **2.21** / 4.36 | – | – |
| B2 F1 inversions L2 | 33 / **0** / 3 | 0 | 0 |
| B3 mean overflow days L2 | 1.833 / **1.25** / 1.25 | – | – |
| B1 dispersion L3 (pp) | 4.29 / **0.74** / 1.59 | – | – |
| B2 F1 inversions L3 | 2 / **0** / 2 | 0 | 0 |
| B3 mean overflow days L3 | 1.111 / **1** / 1.2 | – | – |
| A4 shortage L3 | 8.8 / **0** / 0 | – | – |
| A4 shortage L2 | 63.2 / **5.15** / 10.95 | – | – |
| A4 shortage L1 | 33.95 / **36.2** / 30.05 | – | – |
| E nurse reversals W3 | 0 / **47** / 48 | 0 | 47 |

### 8.3 Context (policy-independent)

| Dataset | Hospital bed shortfall | Cap excess | A3 tier-1 floor | Nurse shortfall (N1 above pool) |
| --- | --- | --- | --- | --- |
| `seed20261107` | 22 patient-days over 5 days | 2 (Cardiology day 17, Internal Medicine day 21) | 23 (day 17 has both) | 67 nurse-days over 17 days |
| `seed20261108` | 78 over 10 days | 0 | 78 | 128 over 23 days |
| `seed20261109` | 0 (census peaks at 95 < 96) | 0 | 0 | 8 over 4 days |
| `seed20261107_stress` | 100 over 7 days | 2 | 101 | 67 over 17 days |

### 8.4 Findings for the headline review

1. **A1:** B1 = 0 on every dataset, as expected (tested). B2 is close (0–19); B0 is far (257–280 on the main datasets, 231 on the stress variant), almost all of it **empty** pairs (a static allocation leaves beds idle in one department while patients wait in another).
2. **A2 headroom below B1 is small:** at most 2.3 nurse-days at tier 2 and 1.85 at tier 1 (seed 08), and 0 at tier 3 everywhere. B1's largest-remainder rationing is near-optimal. On seed 09 there is almost no nurse rationing (8 nurse-days of shortfall).
3. **A3 path headroom below B1 is small:** at most 4 patient-days at tier 2 (seed 08) and 0 at tier 3 on the main datasets. Since 0 is only a lower bound, the true headroom may be smaller still. **The two places named in §1 as the agent's possible advantage hold, on these data, at most a few patient-days or nurse-days.**
4. **Bed reversals (headline) are dominated by empty-bed churn.** B1 and B2 reverse 103–116 bed units within W = 3 (B0: 0). Between 45% and 78% of the bed units they move land on beds that are idle that day, because both re-split spare beds by census every day. An agent that simply leaves empty beds where they are would score far better than B1 and B2 on this headline without allocating any better (REFLECTION_LOG R19). **Owner decision needed** before the headline set is confirmed.
5. **Stress variant:** the forced cut falls on day 23 only. B1 and B2 cut 6 beds, as Log #41 predicts for policies that fill every bed they can; B0 cuts only 4, because it had left beds empty and so carried fewer holders into the shock. Shock-cut severity is 0 for **all three** baselines, because all of them cut with the same hospital-wide lowest-level-first rule. The probe can show whether the agent matches that rule, but no baseline varies on it.
6. **Fairness is where B1 is beatable:** B1's L1 overflow-rate dispersion (5.5–6.1 pp on seeds 07–08) is higher than B2's on seed 07 (2.0 pp). Seed 09 has no overflow under B1 or B2 at all, so it does not discriminate between them.
7. **Rounding floor:** the lexicographic floor differs from the joint floor on 0–2 days per dataset (Log #47).

## 9. Reporting LLM Variability

With n ≤ 3 runs, no inferential statistics are claimed. For each metric, the report gives:

- The value for each run (R1–R3), with the range (min–max) and the mean.
- The baseline values, as reference lines.

Decision-level agreement between runs is also reported:

- The share of days on which the runs chose identical allocations.
- The mean L1 distance between their daily allocations.

Notable divergences are discussed qualitatively in the Reflection, using the decision explanations and the CHECKER reports.
