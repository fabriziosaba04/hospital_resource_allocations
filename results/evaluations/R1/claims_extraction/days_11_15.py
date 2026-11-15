"""R1 claim extraction, days 11-15 (EVALUATION_PLAN.md §4; conventions in README.md of this folder)."""
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


# ---------------------------------------------------------------- day 11 (cur = decided 10, invalid today: 33 nurses vs pool 37;
#                                    A = beds of cur with nurses 7/13/8/9; dec = 17/38/15/26, 8/14/8/7)
D = 11
A11 = {"B": [15, 35, 17, 29], "N": [7, 13, 8, 9]}
c(S, "nurse pool increased by 4 (33", "pool_nurses", "eq", 33, "pool", "derived", qday=10,
  note="past value: end of the previous day (item 2)")
c(S, "to 37)", "pool_nurses", "eq", 37, "pool", "copied")
c(S, "bed pool unchanged at 96", "pool_beds", "eq", 96, "pool", "copied")
c(S, "Occupied beds 63", "holders", "eq", 63, "beds", "copied")
c(S, "The in-effect nurse allocation (33) is infeasible", "nurses", "eq", 33, "beds", "derived", alloc="cur")
c(S, "17 patients are in the queue", "queue", "eq", 17, "overflow", "derived")
queue_lv(S, "3 level 3", 3, "6 level 2", 6, "8 level 1", 8)
per_dep(I, "Occupied 9/27/11/16", "holders", [9, 27, 11, 16], "beds", "copied")
per_dep(I, "In-effect beds 15/35/17/29", "beds", [15, 35, 17, 29], "beds", "copied", alloc="cur")
per_dep(I, "nurses 5/13/8/7", "nurses", [5, 13, 8, 7], "beds", "copied", alloc="cur")
zero_outcomes(A, "A) Keep the day-10 beds 15/35/17/29 with nurses 7/13/8/9 ...: valid, 0 overflow", "0 shortage", A11)
c(A, "bed slack is uneven, with orthopedics 9 above census", "empty_beds", "eq", 9, "empty_beds", "derived",
  alloc=A11, deps=["O"], note="qualified 'above census'")
c(A, "and cardiology only 1", "empty_beds", "eq", 1, "empty_beds", "derived", alloc=A11, deps=["C"],
  note="qualified 'above census'")
zero_outcomes(A, "B) Chosen: ... 0 overflow at every level", "0 nurse shortage at every level", "dec")
c(T, "orthopedics slack falls from 13", "empty_beds", "eq", 13, "empty_beds", "derived", alloc=A11, deps=["O"],
  note="qualified 'above census'; referent = the day-10 beds, evaluated under A (same beds, valid nurses) because "
       "the in-effect allocation fails validation today")
c(T, "to 6 above census", "empty_beds", "eq", 6, "empty_beds", "derived", alloc="dec", deps=["O"],
  note="qualified 'above census'")

# ---------------------------------------------------------------- day 12 (cur = decided 11; dec = 20/37/16/23, 9/14/8/6)
D = 12
pools(S, "no external change (beds 96", 96, "nurses 37)", 37)
c(S, "Occupied beds 66", "holders", "eq", 66, "beds", "copied")
c(S, "17 patients in the queue", "queue", "eq", 17, "overflow", "derived")
queue_lv(S, "4 level 3", 4, "7 level 2", 7, "6 level 1", 6)
per_dep(S, "The current beds 17/38/15/26", "beds", [17, 38, 15, 26], "beds", "copied", alloc="cur")
c(S, "leave cardiology 1 bed short", "overflow", "eq", 1, "overflow", "derived", alloc="cur", deps=["C"])
c(S, "while orthopedics has 8 spare beds", "spare_beds", "eq", 8, "empty_beds", "derived", alloc="cur", deps=["O"],
  rival=True)
c(S, "and IM 5", "spare_beds", "eq", 5, "empty_beds", "derived", alloc="cur", deps=["IM"], rival=True)
per_dep(I, "Occupied 12/27/12/15", "holders", [12, 27, 12, 15], "beds", "copied")
c(I, "Queue lists 16 patients", "queue", "eq", 16, "overflow", "derived",
  note="differs from the situation's 17, so not a repeat")
c(I, "(4 level 3, 7 level 2, 5 level 1)", "queue", "eq", 5, "overflow", "derived", levels=[1],
  note="levels 3 and 2 repeat the situation; level 1 differs (6 there)")
per_dep(I, "In-effect ... nurses 8/14/8/7", "nurses", [8, 14, 8, 7], "beds", "copied", alloc="cur")
c(A, "A) Keep the current allocation ...: valid, 0 nurse shortage", "shortage", "eq", 0, "nurse_coverage", "derived",
  alloc="cur")
c(A, "but 1 level 1 patient", "overflow", "eq", 1, "overflow", "copied", alloc="cur", deps=["C"], levels=[1])
c(A, "(P000738) in cardiology overflow", "patient_in_bed", "eq", 0, "overflow", "copied", alloc="cur",
  patient_id="P000738")
zero_outcomes(A, "B) Chosen: ... 0 overflow at every level", "0 nurse shortage at every level", "dec")
c(R, "13 spare beds are spread", "spare_beds", "eq", 13, "empty_beds", "derived", alloc="dec", rival=True)
c(R, "with cardiology ... given 2", "spare_beds", "eq", 2, "empty_beds", "derived", alloc="dec", deps=["C"],
  rival=True)
c(T, "orthopedics slack falls to 5 above census (from 8)", "empty_beds", "eq", 5, "empty_beds", "derived",
  alloc="dec", deps=["O"], note="qualified 'above census'; 'from 8' repeats the situation figure")

# ---------------------------------------------------------------- day 13 (cur = decided 12; dec = 23/35/20/18, 10/13/10/4)
D = 13
pools(S, "no external change (beds 96", 96, "nurses 37)", 37)
c(S, "Occupied beds 59", "holders", "eq", 59, "beds", "copied")
c(S, "15 patients in the queue", "queue", "eq", 15, "overflow", "derived")
queue_lv(S, "4 level 3", 4, "7 level 2", 7, "4 level 1", 4)
per_dep(S, "Current beds 20/37/16/23", "beds", [20, 37, 16, 23], "beds", "copied", alloc="cur")
c(S, "leave neurology 1 bed short", "overflow", "eq", 1, "overflow", "derived", alloc="cur", deps=["N"])
c(S, "while IM has 9 spare", "spare_beds", "eq", 9, "empty_beds", "derived", alloc="cur", deps=["IM"], rival=True)
c(S, "and orthopedics 14 spare", "spare_beds", "eq", 14, "empty_beds", "derived", alloc="cur", deps=["O"],
  rival=True)
per_dep(I, "Occupied 15/23/13/8", "holders", [15, 23, 13, 8], "beds", "copied")
per_dep(I, "In-effect ... nurses 9/14/8/6", "nurses", [9, 14, 8, 6], "beds", "copied", alloc="cur")
c(A, "A) ... but 1 level 2 patient", "overflow", "eq", 1, "overflow", "copied", alloc="cur", deps=["N"], levels=[2])
c(A, "(P000756) in neurology overflow", "patient_in_bed", "eq", 0, "overflow", "copied", alloc="cur",
  patient_id="P000756")
c(A, "while orthopedics and IM hold many empty beds", None, None, None, "empty_beds", "derived", term="empty",
  note="vague qualifier 'many': unverifiable (item 2)")
c(A, "and a 0.05 level 1 nurse shortage in neurology", "shortage", "round", 0.05, "nurse_coverage", "copied",
  alloc="cur", deps=["N"], levels=[1])
zero_outcomes(A, "B) Chosen: ... 0 overflow at every level", "0 nurse shortage at every level", "dec")
c(R, "the 22 spare beds are weighted toward ...", "spare_beds", "eq", 22, "empty_beds", "derived", alloc="dec",
  rival=True)
c(T, "orthopedics slack falls from 15", "empty_beds", "eq", 15, "empty_beds", "derived", alloc="cur", deps=["O"],
  note="qualified 'above census'; differs from the situation's 14, so not a repeat")
c(T, "to 9 above census", "empty_beds", "eq", 9, "empty_beds", "derived", alloc="dec", deps=["O"],
  note="qualified 'above census'")

# ---------------------------------------------------------------- day 14 (cur = decided 13; dec = 23/34/17/22, 10/12/9/6)
D = 14
pools(S, "no external change (beds 96", 96, "nurses 37)", 37)
c(S, "Occupied beds 53", "holders", "eq", 53, "beds", "copied")
c(S, "20 patients in the queue", "queue", "eq", 20, "overflow", "derived")
queue_lv(S, "6 level 3", 6, "5 level 2", 5, "9 level 1", 9)
c(S, "The current allocation is feasible with zero overflow", "overflow", "eq", 0, "overflow", "derived",
  alloc="cur")
c(S, "neurology 6 spare beds above census", "empty_beds", "eq", 6, "empty_beds", "derived", alloc="cur", deps=["N"],
  note="qualified 'above census'")
c(S, "orthopedics 7", "empty_beds", "eq", 7, "empty_beds", "derived", alloc="cur", deps=["O"],
  note="qualified 'above census'")
per_dep(I, "Occupied 17/20/11/5", "holders", [17, 20, 11, 5], "beds", "copied")
per_dep(I, "In-effect beds 23/35/20/18", "beds", [23, 35, 20, 18], "beds", "copied", alloc="cur")
per_dep(I, "nurses 10/13/10/4", "nurses", [10, 13, 10, 4], "beds", "copied", alloc="cur")
c(A, "A) Keep current allocation ...: valid, 0 overflow, 0 nurse shortage at every level", "shortage", "eq", 0,
  "nurse_coverage", "derived", alloc="cur")
zero_outcomes(A, "B) Chosen: ... valid, 0 overflow", "0 nurse shortage at every level", "dec")
per_dep(R, "Beds above census are 3/6/3/11 (cardiology/IM/neurology/orthopedics)", "empty_beds", [3, 6, 3, 11],
        "empty_beds", "derived", alloc="dec", note="qualified 'above census'")
per_dep(R, "versus 3/7/6/7 in A", "empty_beds", [3, 7, None, None], "empty_beds", "derived", alloc="cur",
        note="qualified 'above census'; neurology 6 and orthopedics 7 repeat the situation")

# ---------------------------------------------------------------- day 15 (cur = decided 14; dec = 34/30/16/16, 14/10/8/5)
D = 15
pools(S, "no external change (beds 96", 96, "nurses 37)", 37)
c(S, "Occupied beds 65", "holders", "eq", 65, "beds", "copied")
per_dep(S, "(20/22/13/10 cardiology/IM/neurology/orthopedics)", "holders", [20, 22, 13, 10], "beds", "copied")
c(S, "against 23 beds", "beds", "eq", 23, "beds", "copied", alloc="cur", deps=["C"])
c(S, "24 patients in the queue", "queue", "eq", 24, "overflow", "derived")
per_dep(I, "In-effect beds 23/34/17/22", "beds", [None, 34, 17, 22], "beds", "copied", alloc="cur")
per_dep(I, "nurses 10/12/9/6", "nurses", [10, 12, 9, 6], "beds", "copied", alloc="cur")
c(I, "Queue: 6 level 3", "queue", "eq", 6, "overflow", "derived", levels=[3])
c(I, "(5 cardiology", "queue", "eq", 5, "overflow", "derived", levels=[3], deps=["C"])
c(I, "1 neurology)", "queue", "eq", 1, "overflow", "derived", levels=[3], deps=["N"])
c(I, "11 level 2", "queue", "eq", 11, "overflow", "derived", levels=[2])
c(I, "7 level 1", "queue", "eq", 7, "overflow", "derived", levels=[1])
for d, v in (("C", 12.6), ("IM", 8.65), ("N", 8.0), ("O", 3.4)):
    c(I, "Level 3 plus level 2 nurse need 12.6/8.65/8.0/3.4", "need", "round", v, "nurse_coverage", "derived",
      deps=[d], levels=[2, 3])
c(A, "A) ... cardiology has overflow of 2 level 3", "overflow", "eq", 2, "overflow", "copied", alloc="cur",
  deps=["C"], levels=[3])
c(A, "5 level 2", "overflow", "eq", 5, "overflow", "copied", alloc="cur", deps=["C"], levels=[2])
c(A, "and 1 level 1", "overflow", "eq", 1, "overflow", "copied", alloc="cur", deps=["C"], levels=[1])
c(A, "while orthopedics and IM hold many empty beds", None, None, None, "empty_beds", "derived", term="empty",
  note="vague qualifier 'many': unverifiable (item 2)")
c(A, "cardiology nurse shortage is 2.6 at level 2", "shortage", "round", 2.6, "nurse_coverage", "copied",
  alloc="cur", deps=["C"], levels=[2])
c(A, "and 1.0 at level 1", "shortage", "round", 1.0, "nurse_coverage", "copied", alloc="cur", deps=["C"],
  levels=[1])
c(A, "B) Chosen: ... 0 overflow at every level", "overflow", "eq", 0, "overflow", "derived", alloc="dec")
c(A, "0 shortage at levels 2 and 3", "shortage", "eq", 0, "nurse_coverage", "derived", alloc="dec", levels=[2, 3])
c(A, "only 0.45 level 1 shortage in IM", "shortage", "round", 0.45, "nurse_coverage", "copied", alloc="dec",
  deps=["IM"], levels=[1])
c(R, "with 7 spare beds weighted to cardiology", "spare_beds", "eq", 7, "empty_beds", "derived", alloc="dec",
  rival=True)
for d in ("N", "O"):
    c(T, "slack is only 1 bed above census in neurology and orthopedics", "empty_beds", "eq", 1, "empty_beds",
      "derived", alloc="dec", deps=[d], note="qualified 'above census'; one claim per named department")
