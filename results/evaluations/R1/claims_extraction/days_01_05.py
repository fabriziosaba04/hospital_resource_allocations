"""R1 claim extraction, days 1-5 (EVALUATION_PLAN.md §4; conventions in README.md of this folder)."""
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

# ---------------------------------------------------------------- day 1 (cur = initial allocation)
D = 1
pools(S, "no external pool change (beds 96", 96, "nurses 37)", 37)
c(S, "Occupied beds 82", "holders", "eq", 82, "beds", "copied")
c(S, "no overflow queue", "queue", "eq", 0, "overflow", "derived")
c(S, "Current allocation is feasible and has zero overflow", "overflow", "eq", 0, "overflow", "derived", alloc="cur")
c(S, "1 spare nurse in internal_medicine (12 vs requirement 11)", "nurses", "eq", 12, "beds", "copied",
  alloc="cur", deps=["IM"])
for d in ("C", "IM", "N", "O"):
    c(S, "3-5 spare beds per department", "spare_beds", "in_range", [3, 5], "empty_beds", "derived", alloc="cur",
      deps=[d], rival=True, note="range stated per department: one claim per department")
per_dep(I, "occupied/census cardiology 16, IM 28, neurology 17, orthopedics 21", "holders", [16, 28, 17, 21],
        "beds", "copied")
per_dep(I, "Initial allocation beds 19/33/20/24", "beds", [19, 33, 20, 24], "beds", "copied", alloc="cur")
per_dep(I, "nurses 8/12/9/8", "nurses", [8, None, 9, 8], "beds", "copied", alloc="cur",
        note="IM 12 already extracted from situation")
c(A, "A) keep current allocation: 0 overflow, 0 nurse shortage", "shortage", "eq", 0, "nurse_coverage", "derived",
  alloc="cur")
c(A, "B) beds 18/32/19/27, nurses 8/11/9/9: 0 overflow", "overflow", "eq", 0, "overflow", "derived", alloc="dec")
c(A, "B) ... 0 shortage", "shortage", "eq", 0, "nurse_coverage", "derived", alloc="dec")
c(A, "B) ... same coverage", "covered_need", "eq_alloc", None, "nurse_coverage", "derived", alloc="dec", cmp="cur")

# ---------------------------------------------------------------- day 2 (cur = decided 1; dec = same)
D = 2
pools(S, "no external change (beds 96", 96, "nurses 37)", 37)
c(S, "Occupied beds 65", "holders", "eq", 65, "beds", "copied")
c(S, "18 patients arrived today without a bed", "queue", "eq", 18, "overflow", "derived")
per_dep(I, "against current beds 18/32/19/27", "beds", [18, 32, 19, 27], "beds", "copied", alloc="cur")
per_dep(I, "Occupied 14/19/14/18", "holders", [14, 19, 14, 18], "beds", "copied")
c(I, "The overflow queue holds 18 same-day arrivals: 3 level 3", "queue", "eq", 3, "overflow", "derived", levels=[3])
c(I, "11 level 2", "queue", "eq", 11, "overflow", "derived", levels=[2])
c(I, "4 level 1", "queue", "eq", 4, "overflow", "derived", levels=[1])
per_dep(A, "A) Keep the current allocation, ... nurses 8/11/9/9", "nurses", [8, 11, 9, 9], "beds", "copied",
        alloc="cur")
c(A, "A) Simulated result: 0 overflow at every level", "overflow", "eq", 0, "overflow", "derived", alloc="cur")
c(A, "A) 0 nurse shortage", "shortage", "eq", 0, "nurse_coverage", "derived", alloc="cur")
B2 = {"B": [19, 30, 20, 27], "N": [8, 11, 9, 9]}
c(A, "B) Beds 19/30/20/27 with the same nurses. Simulated result: identical, 0 overflow", "overflow", "eq", 0,
  "overflow", "derived", alloc=B2)
c(A, "B) ... and 0 shortage", "shortage", "eq", 0, "nurse_coverage", "derived", alloc=B2)
c(T, "The cost is about 13 free beds spread unevenly", "free_beds", "round", 13, "pool", "derived", rival=True,
  rival_alloc="dec")
c(T, "IM holding 6 spare beds", "spare_beds", "eq", 6, "empty_beds", "derived", alloc="dec", deps=["IM"], rival=True)
c(T, "and orthopedics 5", "spare_beds", "eq", 5, "empty_beds", "derived", alloc="dec", deps=["O"], rival=True)
c(U, "departments with 1 spare bed, cardiology and neurology", "spare_beds", "eq", 1, "empty_beds", "derived",
  alloc="dec", deps=["C"], rival=True)
c(U, "departments with 1 spare bed, cardiology and neurology", "spare_beds", "eq", 1, "empty_beds", "derived",
  alloc="dec", deps=["N"], rival=True)

# ---------------------------------------------------------------- day 3 (cur = decided 2; dec = 21/32/19/24, 9/12/9/7)
D = 3
pools(S, "no external change (beds 96", 96, "nurses 37)", 37)
c(S, "Occupied beds 73", "holders", "eq", 73, "beds", "copied")
c(S, "18 patients are in the overflow queue", "queue", "eq", 18, "overflow", "derived")
per_dep(S, "Current beds 18/32/19/27", "beds", [18, 32, 19, 27], "beds", "copied", alloc="cur")
c(S, "would leave cardiology short by 2", "overflow", "eq", 2, "overflow", "derived", alloc="cur", deps=["C"])
c(S, "while orthopedics holds 5 spare", "spare_beds", "eq", 5, "empty_beds", "derived", alloc="cur", deps=["O"],
  rival=True)
per_dep(I, "Occupied 15/23/17/18", "holders", [15, 23, 17, 18], "beds", "copied")
c(I, "Queue: 4 level 3", "queue", "eq", 4, "overflow", "derived", levels=[3])
c(I, "6 level 2", "queue", "eq", 6, "overflow", "derived", levels=[2])
c(I, "8 level 1", "queue", "eq", 8, "overflow", "derived", levels=[1])
per_dep(I, "Current allocation ... nurses 8/11/9/9", "nurses", [8, 11, 9, 9], "beds", "copied", alloc="cur")
c(A, "A) ... overflow in cardiology of 1 level-2 patient", "overflow", "eq", 1, "overflow", "copied", alloc="cur",
  deps=["C"], levels=[2])
c(A, "(P000593)", "patient_in_bed", "eq", 0, "overflow", "copied", alloc="cur", patient_id="P000593")
c(A, "and 1 level-1 patient", "overflow", "eq", 1, "overflow", "copied", alloc="cur", deps=["C"], levels=[1])
c(A, "(P000589)", "patient_in_bed", "eq", 0, "overflow", "copied", alloc="cur", patient_id="P000589")
c(A, "while orthopedics has 3+ empty beds", "empty_beds", "ge", 3, "empty_beds", "derived", alloc="cur", deps=["O"],
  term="empty", alt={"quantity": {"name": "spare_beds", "departments": ["orthopedics"]}})
c(A, "Nurse shortage is level 1 only", "shortage", "eq", 0, "nurse_coverage", "derived", alloc="cur", levels=[2, 3])
c(A, "(IM 1.15", "shortage", "round", 1.15, "nurse_coverage", "copied", alloc="cur", deps=["IM"], levels=[1])
c(A, "cardiology 0.1)", "shortage", "round", 0.1, "nurse_coverage", "copied", alloc="cur", deps=["C"], levels=[1])
c(A, "B) Chosen: ... 0 overflow at every level", "overflow", "eq", 0, "overflow", "derived", alloc="dec")
c(A, "nurse shortage only level 1 ... with no level 2 or 3 need uncovered", "shortage", "eq", 0, "nurse_coverage",
  "derived", alloc="dec", levels=[2, 3], term="covered")
c(A, "(IM 0.15", "shortage", "round", 0.15, "nurse_coverage", "copied", alloc="dec", deps=["IM"], levels=[1])
c(A, "orthopedics 0.15)", "shortage", "round", 0.15, "nurse_coverage", "copied", alloc="dec", deps=["O"], levels=[1])
c(R, "The only uncovered need is about 0.3 nurse-equivalents of level 1", "shortage", "round", 0.3,
  "nurse_coverage", "derived", alloc="dec", levels=[1])
c(R, "with 5 spare beds spread out", "spare_beds", "eq", 5, "empty_beds", "derived", alloc="dec", rival=True)
c(R, "Orthopedics' 7 nurses cover its level 3 and 2 need (5.75)", "covered_need", "round", 5.75, "nurse_coverage",
  "derived", alloc="dec", deps=["O"], levels=[2, 3], term="covered")
c(T, "less spare capacity in orthopedics (2 spare beds", "spare_beds", "eq", 2, "empty_beds", "derived", alloc="dec",
  deps=["O"], rival=True)
c(T, "6 spare above occupied)", "spare_beds", "eq", 6, "empty_beds", "derived", alloc="dec", deps=["O"],
  note="qualified 'above occupied': reading set by the qualifier (§11 #59 follow-up)")

# ---------------------------------------------------------------- day 4 (cur = decided 3; dec = 18/33/20/25, 7/13/9/8)
D = 4
pools(S, "no external change (beds 96", 96, "nurses 37)", 37)
c(S, "Occupied beds 71", "holders", "eq", 71, "beds", "copied")
c(S, "18 patients are in the overflow queue", "queue", "eq", 18, "overflow", "derived")
c(S, "6 level 3", "queue", "eq", 6, "overflow", "derived", levels=[3])
c(S, "5 level 2", "queue", "eq", 5, "overflow", "derived", levels=[2])
c(S, "7 level 1", "queue", "eq", 7, "overflow", "derived", levels=[1])
per_dep(S, "The current allocation (beds 21/32/19/24", "beds", [21, 32, 19, 24], "beds", "copied", alloc="cur")
per_dep(S, "nurses 9/12/9/7)", "nurses", [9, 12, 9, 7], "beds", "copied", alloc="cur")
c(S, "over-supplies cardiology (5 spare beds", "spare_beds", "eq", 5, "empty_beds", "derived", alloc="cur",
  deps=["C"], rival=True)
per_dep(I, "Occupied 14/24/15/18", "holders", [14, 24, 15, 18], "beds", "copied")
c(A, "A) Keep current allocation: 0 overflow", "overflow", "eq", 0, "overflow", "derived", alloc="cur")
c(A, "level 1 nurse shortage of 0.4 in IM", "shortage", "round", 0.4, "nurse_coverage", "copied", alloc="cur",
  deps=["IM"], levels=[1])
c(A, "and 0.65 in orthopedics", "shortage", "round", 0.65, "nurse_coverage", "copied", alloc="cur", deps=["O"],
  levels=[1])
c(A, "B) Chosen: ... 0 overflow at all levels", "overflow", "eq", 0, "overflow", "derived", alloc="dec")
c(A, "B) ... 0 nurse shortage at all levels", "shortage", "eq", 0, "nurse_coverage", "derived", alloc="dec")
c(R, "the 7 spare beds are spread across departments", "spare_beds", "eq", 7, "empty_beds", "derived", alloc="dec",
  rival=True)
c(T, "less slack in cardiology (2 spare beds above census", "empty_beds", "eq", 2, "empty_beds", "derived",
  alloc="dec", deps=["C"], note="qualified 'above census': reading set by the qualifier (§11 #59 follow-up)")
c(T, "only 1 spare bed in orthopedics", "spare_beds", "eq", 1, "empty_beds", "derived", alloc="dec", deps=["O"],
  rival=True)
c(U, "Orthopedics has 1 spare bed and IM 2", "spare_beds", "eq", 2, "empty_beds", "derived", alloc="dec", deps=["IM"],
  rival=True)

# ---------------------------------------------------------------- day 5 (cur = decided 4; dec = 22/31/14/29, 9/12/7/9)
D = 5
pools(S, "no external change (beds 96", 96, "nurses 37)", 37)
c(S, "Occupied beds 66", "holders", "eq", 66, "beds", "copied")
c(S, "20 patients are in the overflow queue", "queue", "eq", 20, "overflow", "derived")
c(S, "4 level 3", "queue", "eq", 4, "overflow", "derived", levels=[3])
c(S, "4 level 2", "queue", "eq", 4, "overflow", "derived", levels=[2])
c(S, "12 level 1", "queue", "eq", 12, "overflow", "derived", levels=[1])
per_dep(S, "The current allocation (beds 18/33/20/25", "beds", [18, 33, 20, 25], "beds", "copied", alloc="cur")
per_dep(S, "nurses 7/13/9/8)", "nurses", [7, 13, 9, 8], "beds", "copied", alloc="cur")
c(S, "leaves cardiology 2 beds short", "overflow", "eq", 2, "overflow", "derived", alloc="cur", deps=["C"])
c(S, "while neurology holds 7 spare beds", "spare_beds", "eq", 7, "empty_beds", "derived", alloc="cur", deps=["N"],
  rival=True)
c(S, "and IM 5", "spare_beds", "eq", 5, "empty_beds", "derived", alloc="cur", deps=["IM"], rival=True)
per_dep(I, "Occupied 12/21/12/21", "holders", [12, 21, 12, 21], "beds", "copied")
c(A, "A) ... 2 level 1 patients", "overflow", "eq", 2, "overflow", "copied", alloc="cur", deps=["C"], levels=[1])
c(A, "(P000628", "patient_in_bed", "eq", 0, "overflow", "copied", alloc="cur", patient_id="P000628")
c(A, "P000629) in cardiology overflow", "patient_in_bed", "eq", 0, "overflow", "copied", alloc="cur",
  patient_id="P000629")
c(A, "Cardiology nurse shortage is 0.5 at level 2", "shortage", "round", 0.5, "nurse_coverage", "copied",
  alloc="cur", deps=["C"], levels=[2])
c(A, "and 1.0 at level 1", "shortage", "round", 1.0, "nurse_coverage", "copied", alloc="cur", deps=["C"], levels=[1])
c(A, "orthopedics is short 0.1 at level 1", "shortage", "round", 0.1, "nurse_coverage", "copied", alloc="cur",
  deps=["O"], levels=[1])
c(A, "B) Chosen: ... 0 overflow at all levels", "overflow", "eq", 0, "overflow", "derived", alloc="dec")
c(A, "B) ... 0 nurse shortage at all levels", "shortage", "eq", 0, "nurse_coverage", "derived", alloc="dec")
c(T, "neurology has only 1 spare bed above census", "empty_beds", "eq", 1, "empty_beds", "derived", alloc="dec",
  deps=["N"], note="qualified 'above census': reading set by the qualifier (§11 #59 follow-up)")
c(T, "and 2 above occupied", "spare_beds", "eq", 2, "empty_beds", "derived", alloc="dec", deps=["N"],
  note="qualified 'above occupied': reading set by the qualifier (§11 #59 follow-up)")
for d, v in (("C", 2), ("IM", 3), ("O", 4)):
    c(U, "The spare-bed distribution (2/3/1/4 above census)", "empty_beds", "eq", v, "empty_beds", "derived",
      alloc="dec", deps=[d], note="qualified 'above census'; neurology's 1 already extracted from tradeoffs")
