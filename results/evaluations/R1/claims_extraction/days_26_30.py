"""R1 claim extraction, days 26-30 (EVALUATION_PLAN.md §4; conventions in README.md of this folder)."""
CLAIMS = []
D = None


def c(field, text, q, rel, v, cat, basis, **kw):
    CLAIMS.append({"day": D, "field": field, "text": text, "q": q, "rel": rel, "v": v, "cat": cat,
                   "basis": basis, **kw})


def pools(field, text_b, b, text_n, n):
    c(field, text_b, "pool_beds", "eq", b, "pool", "copied")
    c(field, text_n, "pool_nurses", "eq", n, "pool", "copied")


def per_dep(field, text, q, values, cat, basis, deps=("C", "IM", "N", "O"), **kw):
    for d, v in zip(deps, values):
        if v is not None:
            c(field, text, q, "eq", v, cat, basis, deps=[d], **kw)


S, I, A, R, T, U = "situation", "information_used", "alternatives", "reasons", "tradeoffs", "uncertainty"


def queue_lv(field, t3, v3, t2, v2, t1, v1):
    c(field, t3, "queue", "eq", v3, "overflow", "derived", levels=[3])
    c(field, t2, "queue", "eq", v2, "overflow", "derived", levels=[2])
    c(field, t1, "queue", "eq", v1, "overflow", "derived", levels=[1])


def zero_outcomes(field, t_ovf, t_short, alloc):
    if t_ovf:
        c(field, t_ovf, "overflow", "eq", 0, "overflow", "derived", alloc=alloc)
    if t_short:
        c(field, t_short, "shortage", "eq", 0, "nurse_coverage", "derived", alloc=alloc)


# ---------------------------------------------------------------- day 26 (cur = decided 25, invalid today: 86 beds vs pool 96;
#                                    A = chosen = dec = 27/29/20/20, 12/10/9/6; B = same beds, 12/10/10/5)
D = 26
B26 = {"B": [27, 29, 20, 20], "N": [12, 10, 10, 5]}
c(S, "Bed pool rose 10 (external event, 86", "pool_beds", "eq", 86, "pool", "derived", qday=25,
  note="past value: end of the previous day (item 2)")
c(S, "to 96)", "pool_beds", "eq", 96, "pool", "copied")
c(S, "nurse pool unchanged at 37", "pool_nurses", "eq", 37, "pool", "copied")
c(S, "Occupied beds total 75", "holders", "eq", 75, "beds", "copied")
per_dep(S, "(cardiology 20, internal medicine 24, neurology 19, orthopedics 12)", "holders", [20, 24, 19, 12],
        "beds", "copied")
c(S, "Total census is 100 against 96 beds, so 4 patients must stay in overflow", "overflow", "ge", 4, "overflow",
  "derived", alloc="dec", note="'must stay': at least 4 under any allocation, tested on the chosen one")
c(I, "Overflow queue of 25 patients", "queue", "eq", 25, "overflow", "derived")
c(I, "6 level 3", "queue", "eq", 6, "overflow", "derived", levels=[3])
per_dep(I, "(cardiology 2, orthopedics 4, all arrived day 26)", "queue", [2, None, None, 4], "overflow", "derived",
        levels=[3])
c(I, "8 level 2", "queue", "eq", 8, "overflow", "derived", levels=[2])
c(I, "11 level 1", "queue", "eq", 11, "overflow", "derived", levels=[1])
per_dep(I, "Of the level 1 patients, 6 in internal medicine, 2 in cardiology and 3 in orthopedics", "queue",
        [2, 6, None, 3], "overflow", "derived", levels=[1],
        note="'7 of them arrived day 25 and 4 arrived day 26' is a patient attribute (outside the universe)")
per_dep(I, "Previous allocation on day 25 was cardiology 24, internal medicine 29, neurology 20, orthopedics 13 beds",
        "beds", [24, 29, 20, 13], "beds", "copied", alloc="cur")
c(A, "Alternative A, chosen: ... overflow only 4 level 1 patients", "overflow", "eq", 4, "overflow", "derived",
  alloc="dec", note="'only': total overflow; all at level 1")
c(A, "(internal medicine 3", "overflow", "eq", 3, "overflow", "copied", alloc="dec", deps=["IM"], levels=[1])
c(A, "orthopedics 1)", "overflow", "eq", 1, "overflow", "copied", alloc="dec", deps=["O"], levels=[1])
c(A, "All level 3 nursing is covered", "shortage", "eq", 0, "nurse_coverage", "derived", alloc="dec", levels=[3],
  term="covered")
for d, v in (("C", 0.5), ("IM", 0.05), ("N", 0.65), ("O", 0.05)):
    c(A, "level 2 shortage is small (cardiology 0.5, internal medicine 0.05, neurology 0.65, orthopedics 0.05)",
      "shortage", "round", v, "nurse_coverage", "copied", alloc="dec", deps=[d], levels=[2])
c(A, "Alternative B: same beds, nurses 12/10/10/5. Simulation: valid, same overflow", "overflow", "eq_alloc", None,
  "overflow", "derived", alloc=B26, cmp="dec")
c(A, "It covered 0.2 of neurology level 1 need", "covered_need", "round", 0.2, "nurse_coverage", "copied",
  alloc=B26, deps=["N"], levels=[1], term="covered")
c(A, "while orthopedics level 2 need was short 1.05", "shortage", "round", 1.05, "nurse_coverage", "copied",
  alloc=B26, deps=["O"], levels=[2])
c(A, "It is infeasible today because it sums to 86 beds", "beds", "eq", 86, "beds", "derived", alloc="cur")
c(R, "No level 1 nursing is funded while level 2 need is uncovered anywhere, except small rounding gaps",
  "covered_need", "eq", 0, "nurse_coverage", "derived", alloc="dec", levels=[1], term="covered",
  note="the figure is level 1 coverage 0 under the chosen allocation; the 'rounding gaps' hedge refers to level 2")
c(R, "All level 1 patients who arrived day 25 (1 day waiting) get beds", None, None, None, "overflow", "derived",
  note="unnamed group selected by arrival day: not expressible in claim_check (no arrival-day filter on "
       "patient_in_bed or overflow); unverifiable by script")
c(R, "Efficiency: all 96 beds ... are used with no idle capacity", "empty_beds", "eq", 0, "empty_beds", "derived",
  alloc="dec", term="idle", note="'idle' beds read as empty, no rival reading (as day 18)")
c(T, "Nursing is short by about 6 nurse units overall", "shortage", "round", 6, "nurse_coverage", "derived",
  alloc="dec")

# ---------------------------------------------------------------- day 27 (cur = decided 26; A = chosen = dec = 31/30/17/18,
#                                    14/10/8/5; B = 31/31/17/17, 13/10/9/5)
D = 27
B27 = {"B": [31, 31, 17, 17], "N": [13, 10, 9, 5]}
pools(S, "Pools unchanged (96 beds", 96, "37 nurses)", 37)
c(S, "no shock (occupied 76 <= 96)", "holders", "eq", 76, "beds", "copied")
per_dep(S, "The current allocation (27/29/20/20)", "beds", [27, 29, 20, 20], "beds", "copied", alloc="cur")
c(S, "leaves cardiology 4 short", "overflow", "eq", 4, "overflow", "derived", alloc="cur", deps=["C"])
c(S, "and internal medicine 2 short", "overflow", "eq", 2, "overflow", "derived", alloc="cur", deps=["IM"])
for d in ("N", "O"):
    c(S, "while neurology and orthopedics hold spare beds", "spare_beds", "ge", 1, "empty_beds", "derived",
      alloc="cur", deps=[d], rival=True, note="one claim per named department")
per_dep(I, "Occupied beds: cardiology 24, IM 22, neurology 16, ortho 14", "holders", [24, 22, 16, 14], "beds",
        "copied")
c(I, "Overflow queue of 22 patients", "queue", "eq", 22, "overflow", "derived")
c(I, "6 level-3", "queue", "eq", 6, "overflow", "derived", levels=[3])
per_dep(I, "(IM 1, cardiology 3, neurology 1, ortho 1)", "queue", [3, 1, 1, 1], "overflow", "derived", levels=[3])
c(I, "6 level-2", "queue", "eq", 6, "overflow", "derived", levels=[2])
per_dep(I, "(IM 3, cardiology 3)", "queue", [3, 3, None, None], "overflow", "derived", levels=[2])
c(I, "10 level-1", "queue", "eq", 10, "overflow", "derived", levels=[1])
per_dep(I, "(IM 5, cardiology 1, ortho 4)", "queue", [1, 5, None, 4], "overflow", "derived", levels=[1],
        note="the named waiting patients' arrival day and days waited are patient attributes (outside the universe)")
c(A, "A (chosen): ... Simulated overflow is 2 level-1 patients", "overflow", "eq", 2, "overflow", "derived",
  alloc="dec", levels=[1])
c(A, "(P001019 IM", "patient_in_bed", "eq", 0, "overflow", "copied", alloc="dec", patient_id="P001019")
c(A, "P001031 ortho)", "patient_in_bed", "eq", 0, "overflow", "copied", alloc="dec", patient_id="P001031")
c(A, "All level-3 and level-2 patients are covered", "overflow", "eq", 0, "overflow", "derived", alloc="dec",
  levels=[2, 3], note="'covered' said of patients, i.e. bedded; not the nursing term")
c(A, "Level-3 nursing is fully covered", "shortage", "eq", 0, "nurse_coverage", "derived", alloc="dec", levels=[3],
  term="covered")
for d, v in (("O", 0.95), ("IM", 0.05), ("N", 0.1)):
    c(A, "The only level-2 shortage is 0.95 in ortho and 0.05 in IM, plus 0.1 in neurology", "shortage", "round", v,
      "nurse_coverage", "copied", alloc="dec", deps=[d], levels=[2])
c(A, "B: ... Overflow is 2 level-1 patients, both in ortho", "overflow", "eq", 2, "overflow", "copied", alloc=B27,
  deps=["O"], levels=[1])
c(A, "and nurse coverage is worse", "covered_need", "lex_le_alloc", None, "nurse_coverage", "derived", alloc=B27,
  cmp="dec", term="no better",
  alt={"relation": "le_alloc", "quantity": {"name": "covered_need", "levels": [2, 3]}},
  note="'worse' read as B not better than A by tier (§11 #57); strictness not tested")
c(A, "Cardiology level-2 is short 0.8", "shortage", "round", 0.8, "nurse_coverage", "copied", alloc=B27,
  deps=["C"], levels=[2])
c(A, "and neurology has spare level-1 coverage", "shortage", "eq", 0, "nurse_coverage", "derived", alloc=B27,
  deps=["N"], levels=[1], term="covered", note="read as neurology level 1 covered (shortage 0)")
for lv in (3, 2):
    c(A, "its bed counts leave level-3 and level-2 cardiology patients waiting", "overflow", "ge", 1, "overflow",
      "derived", alloc="cur", deps=["C"], levels=[lv], note="one claim per named level")
for p in ("P001000", "P001001", "P001010"):
    c(R, "the three level-1 patients that have waited 1 day (P001000, P001001, P001010) get beds", "patient_in_bed",
      "eq", 1, "overflow", "derived", alloc="dec", patient_id=p,
      note="in bed = absent from overflow_patients: derived")
c(R, "no bed ... is idle", "empty_beds", "eq", 0, "empty_beds", "derived", alloc="dec", term="idle",
  note="'idle' beds read as empty, no rival reading (as day 18)")
for d, v in (("C", 13.8), ("IM", 10.05), ("N", 8.1), ("O", 5.95)):
    c(R, "level-weighted need (cardiology 13.8 for levels 3 and 2, IM 10.05, neurology 8.1, ortho 5.95)", "need",
      "round", v, "nurse_coverage", "derived", deps=[d], levels=[2, 3])
c(T, "level-3 plus level-2 nursing need (about 37.9)", "need", "round", 37.9, "nurse_coverage", "derived",
  levels=[2, 3])
c(T, "a level-2 shortage of about 1 nurse in total", "shortage", "round", 1, "nurse_coverage", "derived",
  alloc="dec", levels=[2])
c(T, "level-1 nursing is mostly uncovered", None, None, None, "nurse_coverage", "derived", term="covered",
  note="vague qualifier 'mostly': unverifiable (item 2)")

# ---------------------------------------------------------------- day 28 (cur = decided 27; same beds 30/33/15/18 for all:
#                                    A = 14/11/6/6, B = 13/11/6/7, C = chosen = dec = 13/12/7/5)
D = 28
A28 = {"B": [30, 33, 15, 18], "N": [14, 11, 6, 6]}
B28 = {"B": [30, 33, 15, 18], "N": [13, 11, 6, 7]}
pools(S, "No external pool change (beds 96", 96, "nurses 37)", 37)
c(S, "Occupied beds total 79", "holders", "eq", 79, "beds", "copied")
c(S, "Total census is 89, so 7 beds are spare", "spare_beds", "eq", 7, "empty_beds", "derived", alloc="dec",
  rival=True, note="hospital-wide spare under the chosen allocation (pool minus occupied under the strict reading)")
for d in ("IM", "O"):
    c(S, "Current allocation leaves internal_medicine and orthopedics patients in overflow (L1 each, from yesterday)",
      "overflow", "eq", 1, "overflow", "derived", alloc="cur", deps=[d], levels=[1],
      note="present tense read literally: the current allocation applied today. The other reading, yesterday's "
           "overflow (overflow_yesterday_by_level IM L1 = 1, O L1 = 1), is noted for the owner's review")
per_dep(I, "Occupied: 28/26/12/13", "holders", [28, 26, 12, 13], "beds", "copied")
c(I, "Overflow queue of 10 patients", "queue", "eq", 10, "overflow", "derived")
queue_lv(I, "(L3 x2", 2, "L2 x4", 4, "L1 x4", 4)
c(A, "A: nurses 14/11/6/6 left neurology L2 short by 0.55", "shortage", "round", 0.55, "nurse_coverage", "copied",
  alloc=A28, deps=["N"], levels=[2])
c(A, "and IM L1 short by 0.85", "shortage", "round", 0.85, "nurse_coverage", "copied", alloc=A28, deps=["IM"],
  levels=[1])
c(A, "while orthopedics L1 was almost fully covered", None, None, None, "nurse_coverage", "derived",
  term="covered", note="vague qualifier 'almost': unverifiable (item 2)")
c(A, "B: nurses 13/11/6/7 also left neurology L2 short by 0.55", "shortage", "round", 0.55, "nurse_coverage",
  "copied", alloc=B28, deps=["N"], levels=[2])
c(A, "while orthopedics L1 was covered", "shortage", "eq", 0, "nurse_coverage", "derived", alloc=B28, deps=["O"],
  levels=[1], term="covered")
c(A, "C (chosen): nurses 13/12/7/5 left no L2 or L3 shortage", "shortage", "eq", 0, "nurse_coverage", "derived",
  alloc="dec", levels=[2, 3])
c(A, "Only L1 is short (cardiology 0.45", "shortage", "round", 0.45, "nurse_coverage", "copied", alloc="dec",
  deps=["C"], levels=[1])
c(A, "orthopedics 1.05)", "shortage", "round", 1.05, "nurse_coverage", "copied", alloc="dec", deps=["O"],
  levels=[1])
for al in (A28, B28, "dec"):
    c(A, "No option removed any overflow differently, since all had zero overflow", "overflow", "eq", 0, "overflow",
      "derived", alloc=al, note="one claim per option")
for al in (A28, B28):
    c(R, "Option C covers neurology L2 and IM L2, which A and B left short", "shortage", "ne", 0, "nurse_coverage",
      "derived", alloc=al, deps=["IM"], levels=[2], term="covered",
      note="IM L2 'left short' under each of A and B; neurology's repeats the alternatives' 0.55")
per_dep(R, "(IM +3, orthopedics +2, cardiology +1, neurology +1)", "spare_beds", [1, 3, 1, 2], "empty_beds",
        "derived", alloc="dec", rival=True, note="breakdown of the 7 spare beds")
c(T, "(1.5 nurse-equivalents total in cardiology and orthopedics)", "shortage", "round", 1.5, "nurse_coverage",
  "derived", alloc="dec", deps=["C", "O"], levels=[1])

# ---------------------------------------------------------------- day 29 (cur = decided 28; A = chosen = dec = 32/33/16/15,
#                                    13/11/8/5; B = same beds, 14/11/8/4)
D = 29
B29 = {"B": [32, 33, 16, 15], "N": [14, 11, 8, 4]}
pools(S, "No external pool change (beds 96", 96, "nurses 37)", 37)
c(S, "Total occupied beds 71", "holders", "eq", 71, "beds", "copied")
c(S, "above the current beds in cardiology (30)", "beds", "eq", 30, "beds", "copied", alloc="cur", deps=["C"])
c(S, "neurology (15)", "beds", "eq", 15, "beds", "copied", alloc="cur", deps=["N"])
c(S, "the current allocation leaves 23 queued patients", "queue", "eq", 23, "overflow", "derived",
  note="'in overflow in some departments' is restated with departments in the alternatives, extracted there")
per_dep(I, "Allocation in effect from day 28: beds C30/IM33/N15/O18", "beds", [None, 33, None, 18], "beds",
        "copied", alloc="cur")
per_dep(I, "nurses C13/IM12/N7/O5", "nurses", [13, 12, 7, 5], "beds", "copied", alloc="cur")
c(A, "A) ...: no overflow", "overflow", "eq", 0, "overflow", "derived", alloc="dec")
c(A, "all level 3 and level 2 nursing need covered", "shortage", "eq", 0, "nurse_coverage", "derived", alloc="dec",
  levels=[2, 3], term="covered")
for d, v in (("IM", 0.9), ("C", 0.75), ("O", 1.0)):
    c(A, "level 1 shortage only (IM 0.9, C 0.75, O 1.0)", "shortage", "round", v, "nurse_coverage", "copied",
      alloc="dec", deps=[d], levels=[1])
c(A, "B) same beds, nurses C14/IM11/N8/O4: no overflow", "overflow", "eq", 0, "overflow", "derived", alloc=B29)
c(A, "but orthopedics level 2 is short by 1.0", "shortage", "round", 1.0, "nurse_coverage", "copied", alloc=B29,
  deps=["O"], levels=[2])
c(A, "while cardiology level 1 is fully covered", "shortage", "eq", 0, "nurse_coverage", "derived", alloc=B29,
  deps=["C"], levels=[1], term="covered")
for d in ("C", "N"):
    c(A, "it would leave overflow in cardiology and neurology", "overflow", "ge", 1, "overflow", "derived",
      alloc="cur", deps=[d], note="one claim per named department")
c(R, "beds match census exactly, and the 2 spare beds", "empty_beds", "eq", 2, "empty_beds", "derived",
  alloc="dec", note="qualified: beds above census")
per_dep(R, "go to cardiology (+1) and internal medicine (+1)", "empty_beds", [1, 1, None, None], "empty_beds",
        "derived", alloc="dec", note="qualified as the 2 spare beds above census of the same sentence")
c(R, "Orthopedics gives up 3 idle beds", "empty_beds", "eq", 3, "empty_beds", "derived", alloc="cur", deps=["O"],
  term="idle", note="'idle' beds read as empty, no rival reading (as day 18)")
c(T, "Orthopedics level 1 patients get no nursing coverage today", "covered_need", "eq", 0, "nurse_coverage",
  "copied", alloc="dec", deps=["O"], levels=[1], term="covered")

# ---------------------------------------------------------------- day 30 (cur = decided 29 = "A"; B = 30/29/17/20, 13/10/8/6;
#                                    C = chosen = dec = 30/29/17/20, 12/10/8/7)
D = 30
B30 = {"B": [30, 29, 17, 20], "N": [13, 10, 8, 6]}
NOT_Q = "holders plus queued level 2-3 patients is not a claim_check quantity; unverifiable by script"
pools(S, "Pools unchanged (96 beds", 96, "37 nurses; no external change)", 37)
c(S, "Occupied beds total 76", "holders", "eq", 76, "beds", "copied")
c(S, "Census is 100 against 96 beds, so at least 4 patients must overflow", "overflow", "ge", 4, "overflow",
  "derived", alloc="dec", note="'must': at least 4 under any allocation, tested on the chosen one")
c(S, "(census 24, 13 occupied)", "holders", "eq", 13, "beds", "copied", deps=["O"])
c(S, "while the current allocation gives it only 15 beds", "beds", "eq", 15, "beds", "copied", alloc="cur",
  deps=["O"])
per_dep(I, "Occupied beds: cardiology 24, internal medicine 26, neurology 13, orthopedics 13", "holders",
        [24, 26, 13, None], "beds", "copied")
c(I, "Overflow queue of 24 patients", "queue", "eq", 24, "overflow", "derived")
c(I, "L3 = 6", "queue", "eq", 6, "overflow", "derived", levels=[3])
per_dep(I, "(cardiology 2, neurology 3, orthopedics 1)", "queue", [2, None, 3, 1], "overflow", "derived", levels=[3])
c(I, "L2 = 8", "queue", "eq", 8, "overflow", "derived", levels=[2])
per_dep(I, "(internal medicine 2, cardiology 3, orthopedics 3)", "queue", [3, 2, None, 3], "overflow", "derived",
        levels=[2])
c(I, "L1 = 10", "queue", "eq", 10, "overflow", "derived", levels=[1])
per_dep(I, "(internal medicine 1, cardiology 1, neurology 1, orthopedics 7)", "queue", [1, 1, 1, 7], "overflow",
        "derived", levels=[1])
c(I, "There are 20 free beds", "free_beds", "eq", 20, "pool", "derived", rival=True, rival_alloc="dec")
per_dep(A, "(A) Keep the current allocation (beds 32/33/16/15", "beds", [32, 33, 16, 15], "beds", "copied",
        alloc="cur")
per_dep(A, "nurses 13/11/8/5 ...)", "nurses", [13, 11, 8, 5], "beds", "copied", alloc="cur")
c(A, "Simulated overflow: 10 patients", "overflow", "eq", 10, "overflow", "derived", alloc="cur")
c(A, "including 2 L2 in orthopedics", "overflow", "eq", 2, "overflow", "copied", alloc="cur", deps=["O"], levels=[2])
for d in ("C", "IM"):
    c(A, "while cardiology and internal medicine hold empty beds", "empty_beds", "ge", 1, "empty_beds", "derived",
      alloc="cur", deps=[d], term="empty", alt={"quantity": {"name": "spare_beds", "departments": [
          {"C": "cardiology", "IM": "internal_medicine"}[d]]}}, note="one claim per named department")
c(A, "(B) ... Overflow is 4 L1 in orthopedics", "overflow", "eq", 4, "overflow", "copied", alloc=B30, deps=["O"],
  levels=[1])
c(A, "L2 nurse shortage is 0.75", "shortage", "round", 0.75, "nurse_coverage", "derived", alloc=B30, levels=[2])
c(A, "while 0.7 of L1 need is covered", "covered_need", "round", 0.7, "nurse_coverage", "derived", alloc=B30,
  levels=[1], term="covered")
c(A, "(C) Chosen: ... Same overflow", "overflow", "eq_alloc", None, "overflow", "derived", alloc="dec", cmp=B30)
c(A, "L2 nurse shortage is 0.6", "shortage", "round", 0.6, "nurse_coverage", "derived", alloc="dec", levels=[2])
c(A, "(cardiology 0.5", "shortage", "round", 0.5, "nurse_coverage", "copied", alloc="dec", deps=["C"], levels=[2])
c(A, "neurology 0.1)", "shortage", "round", 0.1, "nurse_coverage", "copied", alloc="dec", deps=["N"], levels=[2])
c(A, "while 0.55 of L1 need is covered", "covered_need", "round", 0.55, "nurse_coverage", "derived", alloc="dec",
  levels=[1], term="covered")
c(A, "(internal medicine 0.2", "covered_need", "round", 0.2, "nurse_coverage", "copied", alloc="dec", deps=["IM"],
  levels=[1], term="covered")
c(A, "orthopedics 0.35)", "covered_need", "round", 0.35, "nurse_coverage", "copied", alloc="dec", deps=["O"],
  levels=[1], term="covered")
for d, v in (("cardiology", 29), ("internal medicine", 28), ("neurology", 16), ("orthopedics", 17)):
    c(R, "That gives cardiology 29, internal medicine 28, neurology 16 and orthopedics 17", None, None, None, "beds",
      "derived", note=f"intended: {d} occupied + queued L2-3 = {v}; " + NOT_Q)
c(R, "which sum to 90", None, None, None, "beds", "derived", note="intended: the four bed minimums sum to 90; " + NOT_Q)
c(R, "The remaining 6 free beds go to L1 patients ... The 6 spare beds", None, None, None, "empty_beds", "derived",
  note="beds above the stated minimums (96 - 90); the context sets the referent, " + NOT_Q)
c(R, "which fills L1 in cardiology, internal medicine and neurology (1 each)", "overflow", "eq", 0, "overflow",
  "derived", alloc="dec", deps=["C", "IM", "N"], levels=[1],
  note="'3 in orthopedics' restates the 4 orthopedics level 1 in overflow (7 queued)")
c(R, "Efficiency: no bed is left empty while a patient waits", "empty_beds", "eq", 0, "empty_beds", "derived",
  alloc="dec", term="empty", alt={"quantity": {"name": "spare_beds"}})
c(R, "Nurses: L3 need is fully covered in every department", "shortage", "eq", 0, "nurse_coverage", "derived",
  alloc="dec", levels=[3], term="covered")
c(R, "The pool is 0.05 short of the combined L3+L2 need", "need", "round", 37.05, "nurse_coverage", "derived",
  levels=[2, 3], note="restated: need = pool 37 + 0.05")
c(R, "and C leaves less than B", "shortage", "le_alloc", None, "nurse_coverage", "derived", alloc="dec", cmp=B30,
  levels=[2], note="named quantity: level 2 shortage; 'less' is strict, le_alloc is not")
