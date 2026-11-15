"""R1 claim extraction, days 6-10 (EVALUATION_PLAN.md §4; conventions in README.md of this folder)."""
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


# ---------------------------------------------------------------- day 6 (cur = decided 5; dec = 20/34/12/30, 8/13/6/10)
D = 6
pools(S, "no external change (beds 96", 96, "nurses 37)", 37)
c(S, "occupied beds 68", "holders", "eq", 68, "beds", "copied")
c(S, "19 patients in the overflow queue", "queue", "eq", 19, "overflow", "derived")
queue_lv(S, "6 level 3", 6, "10 level 2", 10, "3 level 1", 3)
c(S, "Current allocation leaves IM at 0 spare beds", "spare_beds", "eq", 0, "empty_beds", "derived", alloc="cur",
  deps=["IM"], rival=True)
per_dep(I, "Occupied 16/23/9/20", "holders", [16, 23, 9, 20], "beds", "copied")
per_dep(I, "Allocation in effect beds 22/31/14/29", "beds", [22, 31, 14, 29], "beds", "copied", alloc="cur")
per_dep(I, "nurses 9/12/7/9", "nurses", [9, 12, 7, 9], "beds", "copied", alloc="cur")
zero_outcomes(A, "A) Keep current allocation ...: 0 overflow", None, "cur")
c(A, "level 1 nurse shortage of 0.8 in IM", "shortage", "round", 0.8, "nurse_coverage", "copied", alloc="cur",
  deps=["IM"], levels=[1])
c(A, "and 0.2 in orthopedics", "shortage", "round", 0.2, "nurse_coverage", "copied", alloc="cur", deps=["O"],
  levels=[1])
zero_outcomes(A, "B) Chosen: ... 0 overflow at all levels", "B) ... 0 nurse shortage at all levels", "dec")
c(R, "the 9 spare beds are weighted toward ...", "spare_beds", "eq", 9, "empty_beds", "derived", alloc="dec",
  rival=True)
for d, v in (("IM", 3), ("O", 3), ("C", 2), ("N", 1)):
    c(R, "(IM +3, orthopedics +3, cardiology +2, neurology +1)", "spare_beds", "eq", v, "empty_beds", "derived",
      alloc="dec", deps=[d], rival=True,
      note="breakdown of the 9 spare beds; tradeoffs repeats N 1 and C 2 'above census' (extracted once, here)")

# ---------------------------------------------------------------- day 7 (cur = decided 6; dec = 19/36/18/23, 7/14/9/7)
D = 7
pools(S, "no external change (beds 96", 96, "nurses 37)", 37)
c(S, "Occupied beds 70", "holders", "eq", 70, "beds", "copied")
c(S, "19 patients are in the overflow queue", "queue", "eq", 19, "overflow", "derived")
queue_lv(S, "6 level 3", 6, "6 level 2", 6, "7 level 1", 7)
c(S, "the current allocation (neurology 12 beds", "beds", "eq", 12, "beds", "copied", alloc="cur", deps=["N"])
c(S, "6 nurses)", "nurses", "eq", 6, "beds", "copied", alloc="cur", deps=["N"])
c(S, "is 4 beds ... short", "overflow", "eq", 4, "overflow", "derived", alloc="cur", deps=["N"])
c(S, "while orthopedics holds 9 spare beds", "spare_beds", "eq", 9, "empty_beds", "derived", alloc="cur",
  deps=["O"], rival=True)
per_dep(I, "Occupied 16/27/11/16", "holders", [16, 27, 11, 16], "beds", "copied")
per_dep(I, "Allocation in effect beds 20/34/12/30", "beds", [20, 34, None, 30], "beds", "copied", alloc="cur")
per_dep(I, "nurses 8/13/6/10", "nurses", [8, 13, None, 10], "beds", "copied", alloc="cur")
c(A, "A) ... neurology has 2 level 3", "overflow", "eq", 2, "overflow", "copied", alloc="cur", deps=["N"], levels=[3])
c(A, "and 2 level 2 patients in overflow", "overflow", "eq", 2, "overflow", "copied", alloc="cur", deps=["N"],
  levels=[2])
for p in ("P000667", "P000669", "P000666", "P000668"):
    c(A, "(P000667, P000669, P000666, P000668)", "patient_in_bed", "eq", 0, "overflow", "copied", alloc="cur",
      patient_id=p)
c(A, "while orthopedics has spare empty beds", "empty_beds", "ge", 1, "empty_beds", "derived", alloc="cur",
  deps=["O"], term="empty", alt={"quantity": {"name": "spare_beds", "departments": ["orthopedics"]}})
c(A, "Neurology nurse shortage is 0.6 at level 3", "shortage", "round", 0.6, "nurse_coverage", "copied", alloc="cur",
  deps=["N"], levels=[3])
c(A, "and 1.75 at level 2", "shortage", "round", 1.75, "nurse_coverage", "copied", alloc="cur", deps=["N"],
  levels=[2])
c(A, "while orthopedics and cardiology cover level 1", "shortage", "eq", 0, "nurse_coverage", "derived",
  alloc="cur", deps=["O", "C"], levels=[1], term="covered")
c(A, "B) Chosen: ... 0 overflow at every level", "overflow", "eq", 0, "overflow", "derived", alloc="dec")
c(A, "0 shortage at level 2 and 3 everywhere", "shortage", "eq", 0, "nurse_coverage", "derived", alloc="dec",
  levels=[2, 3])
for d, v in (("IM", 0.25), ("C", 0.4), ("O", 0.55)):
    c(A, "only level 1 shortage remains (IM 0.25, cardiology 0.4, orthopedics 0.55", "shortage", "round", v,
      "nurse_coverage", "copied", alloc="dec", deps=[d], levels=[1])
c(A, "total 1.2)", "shortage", "round", 1.2, "nurse_coverage", "derived", alloc="dec", levels=[1])
for d, v in (("C", 6.2), ("IM", 13.05), ("N", 8.35), ("O", 6.15)):
    c(R, "ceil of the level 3 plus level 2 need per department (6.2, 13.05, 8.35, 6.15)", "need", "round", v,
      "nurse_coverage", "derived", deps=[d], levels=[2, 3])
c(R, "with 7 spare beds spread by arrival rate", "spare_beds", "eq", 7, "empty_beds", "derived", alloc="dec",
  rival=True)
c(T, "orthopedics has 2 spare beds above census", "empty_beds", "eq", 2, "empty_beds", "derived", alloc="dec",
  deps=["O"], note="qualified 'above census': reading set by the qualifier (§11 #59 follow-up)")

# ---------------------------------------------------------------- day 8 (cur = decided 7, invalid today: 37 nurses vs pool 33;
#                                                                   dec = 17/36/15/28, 7/12/7/7)
D = 8
INVALID = "alternative fails validation (CONSERVATION_NURSES): unverifiable (item 2)"
c(S, "nurse pool reduced by 4 (37", "pool_nurses", "eq", 37, "pool", "derived", qday=7,
  note="past value: end of the previous day (item 2); 'by 4' is the difference of the two stated pools")
c(S, "to 33)", "pool_nurses", "eq", 33, "pool", "copied")
c(S, "bed pool unchanged at 96", "pool_beds", "eq", 96, "pool", "copied")
c(S, "Occupied beds 70", "holders", "eq", 70, "beds", "copied")
c(S, "Current nurse allocation (37 total) is infeasible", "nurses", "eq", 37, "beds", "derived", alloc="cur")
c(S, "9 patients in the queue", "queue", "eq", 9, "overflow", "derived")
queue_lv(S, "1 level 3", 1, "4 level 2", 4, "4 level 1", 4)
per_dep(I, "occupied 12/27/12/19", "holders", [12, 27, 12, 19], "beds", "copied")
per_dep(I, "Allocation in effect beds 19/36/18/23", "beds", [19, 36, 18, 23], "beds", "copied", alloc="cur")
per_dep(I, "nurses 7/14/9/7", "nurses", [7, 14, 9, 7], "beds", "copied", alloc="cur")
c(A, "A) Keep the day-7 allocation ... Its beds would give 0 overflow", None, None, None, "overflow", "derived",
  note="intended: overflow under cur eq 0; " + INVALID)
c(A, "it leaves neurology 6 spare beds above census", None, None, None, "empty_beds", "derived",
  note="intended: empty_beds neurology under cur eq 6 (qualified above census); " + INVALID)
c(A, "and orthopedics only 1", None, None, None, "empty_beds", "derived",
  note="intended: empty_beds orthopedics under cur eq 1 (qualified above census); " + INVALID)
c(A, "B) Chosen: ... 0 overflow at all levels", "overflow", "eq", 0, "overflow", "derived", alloc="dec")
c(A, "0 shortage at level 2 and 3 in every department", "shortage", "eq", 0, "nurse_coverage", "derived",
  alloc="dec", levels=[2, 3])
c(A, "level 1 shortage IM 1.05", "shortage", "round", 1.05, "nurse_coverage", "copied", alloc="dec", deps=["IM"],
  levels=[1])
c(A, "and orthopedics 0.9", "shortage", "round", 0.9, "nurse_coverage", "copied", alloc="dec", deps=["O"],
  levels=[1])
for d, v in (("C", 5.6), ("IM", 11.65), ("N", 6.45), ("O", 6.5)):
    c(R, "ceil of level 3 plus level 2 need (5.6, 11.65, 6.45, 6.5", "need", "round", v, "nurse_coverage", "derived",
      deps=[d], levels=[2, 3])
c(R, "the 33rd nurse goes to cardiology, covering its level 1 need fully", "shortage", "eq", 0, "nurse_coverage",
  "derived", alloc="dec", deps=["C"], levels=[1], term="covered")
c(T, "level 1 nursing shortfall of about 1.95 nurse-equivalents in IM and orthopedics", "shortage", "round", 1.95,
  "nurse_coverage", "derived", alloc="dec", deps=["IM", "O"], levels=[1])
c(T, "neurology has about 0.55 nurse unused above need", "need", "round", 6.45, "nurse_coverage", "derived",
  deps=["N"], note="restated: 0.55 = 7 nurses (the proposal, a definition) minus neurology's total need; "
                   "the total-need figure 6.45 differs from the level 2-3 claim only by level 1 (census 0)")
c(T, "Moving that nurse to IM would leave neurology level 2 uncovered", "shortage", "ne", 0, "nurse_coverage",
  "derived", alloc={"B": [17, 36, 15, 28], "N": [7, 13, 6, 7]}, deps=["N"], levels=[2], term="covered",
  note="alternative not simulated by the ALLOCATOR: B with one nurse moved from neurology to IM")
c(U, "it has 3 spare beds above census", "empty_beds", "eq", 3, "empty_beds", "derived", alloc="dec", deps=["N"],
  note="qualified 'above census': reading set by the qualifier (§11 #59 follow-up)")

# ---------------------------------------------------------------- day 9 (cur = decided 8; dec = 15/35/14/32, 5/12/7/9)
D = 9
pools(S, "no external change (beds 96", 96, "nurses 33)", 33)
c(S, "Occupied beds 64", "holders", "eq", 64, "beds", "copied")
c(S, "13 patients in the queue", "queue", "eq", 13, "overflow", "derived")
queue_lv(S, "1 level 3", 1, "7 level 2", 7, "5 level 1", 5)
per_dep(S, "The current allocation (beds 17/36/15/28", "beds", [17, 36, 15, 28], "beds", "copied", alloc="cur")
per_dep(S, "nurses 7/12/7/7)", "nurses", [7, 12, 7, 7], "beds", "copied", alloc="cur")
per_dep(I, "Occupied 10/22/11/21", "holders", [10, 22, 11, 21], "beds", "copied")
c(A, "A) Keep current allocation: valid, 0 overflow", "overflow", "eq", 0, "overflow", "derived", alloc="cur")
c(A, "orthopedics has a level 1 nurse shortage of 1.25", "shortage", "round", 1.25, "nurse_coverage", "copied",
  alloc="cur", deps=["O"], levels=[1])
c(A, "while cardiology holds 2 nurses above need", "need", "round", 5, "nurse_coverage", "derived", deps=["C"],
  note="restated: 2 = 7 nurses in effect minus cardiology's total need, so need = 5 at the stated precision")
zero_outcomes(A, "B) Chosen: ... 0 overflow at all levels", "B) ... 0 nurse shortage at all levels", "dec")
c(R, "with the 19 spare beds weighted toward ...", "spare_beds", "eq", 19, "empty_beds", "derived", alloc="dec",
  rival=True)
for d, v in (("IM", 7), ("O", 7), ("C", 3), ("N", 2)):
    c(R, "(IM +7, orthopedics +7, cardiology +3, neurology +2)", "spare_beds", "eq", v, "empty_beds", "derived",
      alloc="dec", deps=[d], rival=True,
      note="breakdown of the 19 spare beds; tradeoffs repeats C 3 and N 2 'above census' (extracted once, here)")

# ---------------------------------------------------------------- day 10 (cur = decided 9; dec = 15/35/17/29, 5/13/8/7)
D = 10
pools(S, "no external change (beds 96", 96, "nurses 33)", 33)
c(S, "Occupied beds 63", "holders", "eq", 63, "beds", "copied")
c(S, "13 patients in the queue", "queue", "eq", 13, "overflow", "derived")
queue_lv(S, "3 level 3", 3, "6 level 2", 6, "4 level 1", 4)
per_dep(S, "Current nurses 5/12/7/9", "nurses", [5, 12, 7, 9], "beds", "copied", alloc="cur")
c(S, "Neurology beds 14", "beds", "eq", 14, "beds", "copied", alloc="cur", deps=["N"])
c(S, "equal census, zero slack", "empty_beds", "eq", 0, "empty_beds", "derived", alloc="cur", deps=["N"],
  note="'equal census' sets the reading (beds - census); reasons repeats it ('neurology, which had none'), "
       "extracted once, here")
per_dep(I, "Occupied 10/24/11/18", "holders", [10, 24, 11, 18], "beds", "copied")
per_dep(I, "Allocation in effect beds 15/35/14/32", "beds", [15, 35, None, 32], "beds", "copied", alloc="cur")
for d, v in (("C", 4.75), ("IM", 11.05), ("N", 7.4), ("O", 5.55)):
    c(I, "Level 3 plus level 2 nurse need 4.75/11.05/7.4/5.55", "need", "round", v, "nurse_coverage", "derived",
      deps=[d], levels=[2, 3])
c(A, "A) Keep current allocation ...: valid, 0 overflow", "overflow", "eq", 0, "overflow", "derived", alloc="cur")
c(A, "but level 2 shortage of 0.4 in neurology", "shortage", "round", 0.4, "nurse_coverage", "copied", alloc="cur",
  deps=["N"], levels=[2])
c(A, "and level 1 shortage of 0.45 in IM", "shortage", "round", 0.45, "nurse_coverage", "copied", alloc="cur",
  deps=["IM"], levels=[1])
c(A, "(level 1 covered 1.6", "covered_need", "round", 1.6, "nurse_coverage", "copied", alloc="cur", deps=["O"],
  levels=[1], term="covered")
c(A, "of 1.6 needed)", "need", "round", 1.6, "nurse_coverage", "derived", deps=["O"], levels=[1])
c(A, "B) Chosen: ... 0 overflow at all levels", "overflow", "eq", 0, "overflow", "derived", alloc="dec")
c(A, "0 shortage at levels 2 and 3", "shortage", "eq", 0, "nurse_coverage", "derived", alloc="dec", levels=[2, 3])
c(A, "only 0.15 level 1 shortage in orthopedics", "shortage", "round", 0.15, "nurse_coverage", "copied",
  alloc="dec", deps=["O"], levels=[1])
c(R, "fixes the level 2 gap in neurology that A leaves while lower-level need is covered elsewhere", None, None,
  None, "nurse_coverage", "derived", term="covered",
  note="ambiguous referent: 'elsewhere' names no departments and no allocation-level set; unverifiable (item 2)")
c(R, "3 beds move from orthopedics, which has 11 spare", "spare_beds", "eq", 11, "empty_beds", "derived",
  alloc="cur", deps=["O"], rival=True)
c(T, "orthopedics has less bed slack (8 above census instead of 11)", "empty_beds", "eq", 8, "empty_beds",
  "derived", alloc="dec", deps=["O"], note="qualified 'above census'; 'instead of 11' repeats the reasons figure")
