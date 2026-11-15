"""R1 claim extraction, days 16-20 (EVALUATION_PLAN.md §4; conventions in README.md of this folder)."""
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


# ---------------------------------------------------------------- day 16 (cur = decided 15, invalid today: 96 beds vs pool 100;
#                                    A = 34/30/16/20, 14/10/8/5; dec = 37/28/20/15, 15/9/9/4)
D = 16
A16 = {"B": [34, 30, 16, 20], "N": [14, 10, 8, 5]}
c(S, "bed pool increased by 4 (96", "pool_beds", "eq", 96, "pool", "derived", qday=15,
  note="past value: end of the previous day (item 2)")
c(S, "to 100)", "pool_beds", "eq", 100, "pool", "copied")
c(S, "nurse pool unchanged at 37", "pool_nurses", "eq", 37, "pool", "copied")
c(S, "Occupied beds 72", "holders", "eq", 72, "beds", "copied")
per_dep(S, "(28/19/14/11 cardiology/IM/neurology/orthopedics)", "holders", [28, 19, 14, 11], "beds", "copied")
per_dep(S, "The in-effect beds (34/30/16/16", "beds", [34, 30, 16, 16], "beds", "copied", alloc="cur")
c(S, "= 96) are infeasible against the new pool", "beds", "eq", 96, "beds", "derived", alloc="cur")
c(S, "20 patients are in the queue", "queue", "eq", 20, "overflow", "derived")
for d, v in (("C", 13.3), ("IM", 8.15), ("N", 8.6), ("O", 3.05)):
    c(I, "Level 3 plus level 2 nurse need 13.3/8.15/8.6/3.05", "need", "round", v, "nurse_coverage", "derived",
      deps=[d], levels=[2, 3])
c(A, "A) ... valid, but 1 level 1 patient in cardiology overflow", "overflow", "eq", 1, "overflow", "copied",
  alloc=A16, deps=["C"], levels=[1])
c(A, "and 2 level 1 patients in neurology overflow", "overflow", "eq", 2, "overflow", "copied", alloc=A16,
  deps=["N"], levels=[1])
for d in ("IM", "O"):
    c(A, "while IM and orthopedics hold spare beds", "spare_beds", "ge", 1, "empty_beds", "derived", alloc=A16,
      deps=[d], rival=True, note="one claim per named department")
c(A, "plus a 0.6 level 2 nurse shortage in neurology", "shortage", "round", 0.6, "nurse_coverage", "copied",
  alloc=A16, deps=["N"], levels=[2])
c(A, "B) Chosen: ... 0 overflow at every level", "overflow", "eq", 0, "overflow", "derived", alloc="dec")
c(A, "0 shortage at levels 2 and 3", "shortage", "eq", 0, "nurse_coverage", "derived", alloc="dec", levels=[2, 3])
c(A, "only level 1 shortage of 0.35 in IM", "shortage", "round", 0.35, "nurse_coverage", "copied", alloc="dec",
  deps=["IM"], levels=[1])
c(A, "and 0.25 in orthopedics", "shortage", "round", 0.25, "nurse_coverage", "copied", alloc="dec", deps=["O"],
  levels=[1])
c(R, "falls only on 0.6 nurse-equivalents of level 1 need", "shortage", "round", 0.6, "nurse_coverage", "derived",
  alloc="dec", levels=[1])
c(R, "A leaves neurology level 2 need uncovered while level 1 is covered elsewhere", None, None, None,
  "nurse_coverage", "derived", term="covered",
  note="ambiguous referent: 'elsewhere' names no departments; unverifiable (item 2). The level 2 part repeats A's 0.6")
c(R, "the 8 spare beds are spread by recent arrivals", "spare_beds", "eq", 8, "empty_beds", "derived", alloc="dec",
  rival=True)
c(T, "orthopedics has only 1 spare bed above census", "empty_beds", "eq", 1, "empty_beds", "derived", alloc="dec",
  deps=["O"], note="qualified 'above census'")

# ---------------------------------------------------------------- day 17 (cur = decided 16; here "A" is the chosen
#                                    allocation = dec = 40/25/20/15, 15/8/10/4; "B" = 40/24/20/16, 16/8/9/4)
D = 17
B17 = {"B": [40, 24, 20, 16], "N": [16, 8, 9, 4]}
pools(S, "no external change (beds 100", 100, "nurses 37)", 37)
c(S, "Occupied beds 72", "holders", "eq", 72, "beds", "copied")
per_dep(S, "(31/16/16/9 cardiology/IM/neurology/orthopedics)", "holders", [31, 16, 16, 9], "beds", "copied")
c(S, "Census 41/25/20/16 = 102 exceeds 100 beds, so 2 patients cannot be seated", "overflow", "ge", 2, "overflow",
  "derived", alloc="dec", note="'cannot be seated': at least 2 in overflow under any allocation, tested on the chosen one")
c(S, "30 patients in the queue", "queue", "eq", 30, "overflow", "derived")
per_dep(I, "In-effect beds 37/28/20/15", "beds", [37, 28, 20, 15], "beds", "copied", alloc="cur")
per_dep(I, "nurses 15/9/9/4", "nurses", [15, 9, 9, 4], "beds", "copied", alloc="cur")
queue_lv(I, "Overflow queue: 10 level 3", 10, "12 level 2", 12, "8 level 1", 8)
for d, v in (("C", 9.6), ("IM", 4.2), ("N", 8.4), ("O", 0.6)):
    c(I, "Level 3 need 9.6/4.2/8.4/0.6", "need", "round", v, "nurse_coverage", "derived", deps=[d], levels=[3])
for d, v in (("C", 5.95), ("IM", 4.2), ("N", 1.4), ("O", 3.5)):
    c(I, "level 2 need 5.95/4.2/1.4/3.5 nurse-equivalents", "need", "round", v, "nurse_coverage", "derived",
      deps=[d], levels=[2])
c(A, "A) Chosen: ... overflow only 2 level 1 patients", "overflow", "eq", 2, "overflow", "derived", alloc="dec",
  levels=[1])
c(A, "(P000841 cardiology", "patient_in_bed", "eq", 0, "overflow", "copied", alloc="dec", patient_id="P000841")
c(A, "P000850 orthopedics)", "patient_in_bed", "eq", 0, "overflow", "copied", alloc="dec", patient_id="P000850")
c(A, "zero overflow at levels 2 and 3", "overflow", "eq", 0, "overflow", "derived", alloc="dec", levels=[2, 3])
c(A, "zero level 3 nurse shortage", "shortage", "eq", 0, "nurse_coverage", "derived", alloc="dec", levels=[3])
for d, v in (("C", 0.55), ("IM", 0.4), ("O", 0.1)):
    c(A, "level 2 shortage 0.55 cardiology, 0.4 IM, 0.1 orthopedics", "shortage", "round", v, "nurse_coverage",
      "copied", alloc="dec", deps=[d], levels=[2])
c(A, "(total 1.05)", "shortage", "round", 1.05, "nurse_coverage", "derived", alloc="dec", levels=[2])
c(A, "B) ...: valid, overflow 2 level 1", "overflow", "eq", 2, "overflow", "derived", alloc=B17, levels=[1])
c(A, "(P000841 cardiology", "patient_in_bed", "eq", 0, "overflow", "copied", alloc=B17, patient_id="P000841")
c(A, "P000830 IM)", "patient_in_bed", "eq", 0, "overflow", "copied", alloc=B17, patient_id="P000830")
for d, v in (("N", 0.8), ("IM", 0.4), ("O", 0.1)):
    c(A, "but level 2 shortage 0.8 in neurology, 0.4 IM, 0.1 orthopedics", "shortage", "round", v,
      "nurse_coverage", "copied", alloc=B17, deps=[d], levels=[2])
c(A, "(total 1.3)", "shortage", "round", 1.3, "nurse_coverage", "derived", alloc=B17, levels=[2])
c(A, "(total 1.3), worse", "shortage", "ge_alloc", None, "nurse_coverage", "derived", alloc=B17, cmp="dec",
  levels=[2], note="named quantity: level 2 shortage of B against the chosen A; 'worse' is strict, ge_alloc is not")
c(A, "The current allocation ... would leave more patients in overflow", "overflow", "ge_alloc", None, "overflow",
  "derived", alloc="cur", cmp="dec", note="'more' is strict, ge_alloc is not")
c(R, "no idle nurses except 0.2 of rounding in neurology", "covered_need", "round", 9.8, "nurse_coverage",
  "derived", alloc="dec", deps=["N"],
  note="restated: idle 0.2 = 10 nurses (the proposal, a definition) minus need covered in neurology")
c(R, "and no empty beds hospital-wide", "empty_beds", "eq", 0, "empty_beds", "derived", alloc="dec", term="empty",
  alt={"quantity": {"name": "spare_beds"}})
c(T, "IM has 9 spare beds above occupied", "spare_beds", "eq", 9, "empty_beds", "derived", alloc="dec",
  deps=["IM"], note="qualified 'above occupied'")
c(T, "but only 0 above census", "empty_beds", "eq", 0, "empty_beds", "derived", alloc="dec", deps=["IM"],
  note="qualified 'above census'")
c(T, "neurology 0", "empty_beds", "eq", 0, "empty_beds", "derived", alloc="dec", deps=["N"],
  note="qualified 'above census' (follows 'only 0 above census')")

# ---------------------------------------------------------------- day 18 (cur = decided 17; A = 37/29/20/14, 14/9/10/4;
#                                    B = same beds, 13/10/10/4; C = chosen = dec = same beds, 13/9/11/4)
D = 18
A18 = {"B": [37, 29, 20, 14], "N": [14, 9, 10, 4]}
B18 = {"B": [37, 29, 20, 14], "N": [13, 10, 10, 4]}
pools(S, "no external change (beds 100", 100, "nurses 37)", 37)
c(S, "Occupied beds 76", "holders", "eq", 76, "beds", "copied")
per_dep(S, "(C33, IM19, N16, O8)", "holders", [33, 19, 16, 8], "beds", "copied")
per_dep(S, "Current allocation beds 40/25/20/15", "beds", [40, 25, 20, 15], "beds", "copied", alloc="cur")
c(S, "leaves internal_medicine 3 beds short (overflow)", "overflow", "eq", 3, "overflow", "derived", alloc="cur",
  deps=["IM"])
c(S, "and cardiology with 4 idle beds", "empty_beds", "eq", 4, "empty_beds", "derived", alloc="cur", deps=["C"],
  term="idle", note="'idle beds' is not a rubric term; read as beds with no patient (empty), no rival reading")
c(I, "overflow queue of 23 patients", "queue", "eq", 23, "overflow", "derived")
c(I, "(e.g. 7 level-2 in IM", "queue", "eq", 7, "overflow", "derived", deps=["IM"], levels=[2])
c(I, "4 level-3 across C/N/O", "queue", "eq", 4, "overflow", "derived", deps=["C", "N", "O"], levels=[3])
c(A, "A) beds 37/29/20/14, nurses 14/9/10/4: no overflow", "overflow", "eq", 0, "overflow", "derived", alloc=A18)
c(A, "but neurology level-2 shortage 0.4", "shortage", "round", 0.4, "nurse_coverage", "copied", alloc=A18,
  deps=["N"], levels=[2])
c(A, "while level-1 nursing is partly covered in IM, C and O", None, None, None, "nurse_coverage", "derived",
  term="covered", note="vague qualifier 'partly': unverifiable (item 2)")
c(A, "B) same beds, nurses 13/10/10/4: no overflow", "overflow", "eq", 0, "overflow", "derived", alloc=B18)
c(A, "cardiology level-2 short 0.05", "shortage", "round", 0.05, "nurse_coverage", "copied", alloc=B18, deps=["C"],
  levels=[2])
c(A, "and neurology level-2 short 0.4", "shortage", "round", 0.4, "nurse_coverage", "copied", alloc=B18,
  deps=["N"], levels=[2])
c(A, "with IM level 1 covered more", "covered_need", "ge_alloc", None, "nurse_coverage", "derived", alloc=B18,
  cmp=A18, deps=["IM"], levels=[1], note="'more' than A, strict; ge_alloc is not")
c(A, "C) chosen, nurses 13/9/11/4: no overflow", "overflow", "eq", 0, "overflow", "derived", alloc="dec")
c(A, "only shortage at level 2 is 0.05 in cardiology", "shortage", "round", 0.05, "nurse_coverage", "derived",
  alloc="dec", levels=[2], note="'only': the level 2 shortage hospital-wide; the tradeoffs repeat it")
c(A, "level 3 fully covered everywhere", "shortage", "eq", 0, "nurse_coverage", "derived", alloc="dec", levels=[3],
  term="covered")
c(R, "with 2 spare placed in cardiology and IM", "spare_beds", "eq", 2, "empty_beds", "derived", alloc="dec",
  deps=["C", "IM"], rival=True)
c(T, "level-1 nursing shortfall of about 3.5 nurse-units in total", "shortage", "round", 3.5, "nurse_coverage",
  "derived", alloc="dec", levels=[1])
for d, v in (("IM", 1.25), ("C", 1.6), ("O", 0.65)):
    c(T, "(IM 1.25, C 1.6, O 0.65)", "shortage", "round", v, "nurse_coverage", "copied", alloc="dec", deps=[d],
      levels=[1])

# ---------------------------------------------------------------- day 19 (cur = decided 18 = "A"; B = 35/33/19/13, 14/10/9/4;
#                                    C = chosen = dec = 35/33/19/13, 13/10/10/4)
D = 19
B19 = {"B": [35, 33, 19, 13], "N": [14, 10, 9, 4]}
pools(S, "no external change (beds 100", 100, "nurses 37)", 37)
c(S, "Occupied beds 79", "holders", "eq", 79, "beds", "copied")
per_dep(S, "Current allocation (37/29/20/14 beds)", "beds", [37, 29, 20, 14], "beds", "copied", alloc="cur")
c(S, "leaves internal_medicine short: census 31 vs 29 beds", "overflow", "ge", 1, "overflow", "derived",
  alloc="cur", deps=["IM"], note="'short' with no stated overflow figure (census is outside the universe)")
per_dep(I, "occupied 29/22/17/11", "holders", [29, 22, 17, 11], "beds", "copied")
c(I, "Overflow queue of 17 new day-19 arrivals", "queue", "eq", 17, "overflow", "derived")
c(A, "A) Keep current allocation: 2 level-1 patients in IM overflow", "overflow", "eq", 2, "overflow", "copied",
  alloc="cur", deps=["IM"], levels=[1])
c(A, "IM L2 nurse shortage 0.8", "shortage", "round", 0.8, "nurse_coverage", "copied", alloc="cur", deps=["IM"],
  levels=[2])
c(A, "cardiology L2 shortage 0.2", "shortage", "round", 0.2, "nurse_coverage", "copied", alloc="cur", deps=["C"],
  levels=[2])
c(A, "B) Beds 35/33/19/13, nurses 14/10/9/4: zero overflow", "overflow", "eq", 0, "overflow", "derived", alloc=B19)
c(A, "but neurology L2 shortage 0.55", "shortage", "round", 0.55, "nurse_coverage", "copied", alloc=B19,
  deps=["N"], levels=[2])
c(A, "while L1 is covered elsewhere", None, None, None, "nurse_coverage", "derived", term="covered",
  note="ambiguous referent: 'elsewhere' names no departments; unverifiable (item 2)")
c(A, "C) Chosen: ... zero overflow", "overflow", "eq", 0, "overflow", "derived", alloc="dec")
c(A, "only L2 shortage is 0.2 in cardiology", "shortage", "round", 0.2, "nurse_coverage", "derived", alloc="dec",
  levels=[2], note="'only': the level 2 shortage hospital-wide")
c(A, "L3 fully covered everywhere", "shortage", "eq", 0, "nurse_coverage", "derived", alloc="dec", levels=[3],
  term="covered")
c(R, "Level-2 shortage is minimised at 0.2, the smallest reachable with integer nurses", None, None, None,
  "nurse_coverage", "derived",
  note="optimality over all integer nurse allocations is not a what-if quantity; unverifiable by claim_check")
c(R, "the 4 spare beds go mostly to IM", "spare_beds", "eq", 4, "empty_beds", "derived", alloc="dec", rival=True)
c(R, "(+2 over census)", "empty_beds", "eq", 2, "empty_beds", "derived", alloc="dec", deps=["IM"],
  note="qualified 'over census'")
for d in ("C", "O"):
    c(R, "and cardiology/orthopedics (+1 each)", "empty_beds", "eq", 1, "empty_beds", "derived", alloc="dec",
      deps=[d], note="qualified 'over census'; one claim per named department")
for d, v in (("IM", 1.4), ("C", 1.4), ("O", 0.1)):
    c(T, "level-1 nursing is mostly uncovered (shortage 1.4 IM, 1.4 cardiology, 0.1 orthopedics)", "shortage",
      "round", v, "nurse_coverage", "copied", alloc="dec", deps=[d], levels=[1])
for d, v in (("IM", 0.2), ("N", 0.2), ("O", 0.7)):
    c(T, "IM, neurology and orthopedics have small amounts of L1 coverage (0.2/0.2/0.7)", "covered_need", "round",
      v, "nurse_coverage", "copied", alloc="dec", deps=[d], levels=[1], term="covered")
for d in ("N", "O"):
    c(T, "Neurology and orthopedics have only 0 to 1 spare bed", "spare_beds", "in_range", [0, 1], "empty_beds",
      "derived", alloc="dec", deps=[d], rival=True, note="range stated per department: one claim per department")

# ---------------------------------------------------------------- day 20 (cur = decided 19; A = 30/37/19/14, 12/13/9/3;
#                                    B = same beds, 12/13/10/2; C = chosen = dec = same beds, 12/12/9/4)
# Appended in a separate commit: the first batch-4 commit (f8357a5) left day 20 out (R43).
D = 20
A20 = {"B": [30, 37, 19, 14], "N": [12, 13, 9, 3]}
B20 = {"B": [30, 37, 19, 14], "N": [12, 13, 10, 2]}
pools(S, "no external pool change (beds 100", 100, "nurses 37)", 37)
c(S, "occupied beds are 73", "holders", "eq", 73, "beds", "copied")
per_dep(S, "The current allocation (beds 35/33/19/13", "beds", [35, 33, 19, 13], "beds", "copied", alloc="cur")
per_dep(S, "nurses 13/10/10/4 ...)", "nurses", [13, 10, 10, 4], "beds", "copied", alloc="cur")
c(S, "leaves IM 4 beds short", "overflow", "eq", 4, "overflow", "derived", alloc="cur", deps=["IM"])
c(S, "and orthopedics 1 short", "overflow", "eq", 1, "overflow", "derived", alloc="cur", deps=["O"])
c(S, "with cardiology holding 5 spare beds", "spare_beds", "eq", 5, "empty_beds", "derived", alloc="cur",
  deps=["C"], rival=True)
c(S, "27 patients without a bed ... are in the overflow queue", "queue", "eq", 27, "overflow", "derived")
per_dep(I, "occupied 24/24/14/11", "holders", [24, 24, 14, 11], "beds", "copied")
for lv, vals in ((3, (6.6, 4.8, 7.8, 1.2)), (2, (4.55, 6.3, 1.05, 2.1)), (1, (1.2, 2.2, 0.6, 1.2))):
    for d, v in zip(("C", "IM", "N", "O"), vals):
        c(I, "fractional need: L3 6.6/4.8/7.8/1.2, L2 4.55/6.3/1.05/2.1, L1 1.2/2.2/0.6/1.2", "need", "round", v,
          "nurse_coverage", "derived", deps=[d], levels=[lv])
queue_lv(I, "The overflow queue holds 4 L3", 4, "12 L2", 12, "and 11 L1 patients", 11)
c(A, "A) beds 30/37/19/14 with nurses 12/13/9/3: no overflow", "overflow", "eq", 0, "overflow", "derived",
  alloc=A20)
c(A, "but orthopedics has an L2 shortage of 0.3", "shortage", "round", 0.3, "nurse_coverage", "copied", alloc=A20,
  deps=["O"], levels=[2])
c(A, "while IM L1 is covered 1.9", "covered_need", "round", 1.9, "nurse_coverage", "copied", alloc=A20,
  deps=["IM"], levels=[1], term="covered")
c(A, "B) The same beds with nurses 12/13/10/2: orthopedics L2 shortage 1.3", "shortage", "round", 1.3,
  "nurse_coverage", "copied", alloc=B20, deps=["O"], levels=[2])
c(A, "while other departments cover L1", None, None, None, "nurse_coverage", "derived", term="covered",
  note="ambiguous quantifier (some or all other departments), as for 'covered elsewhere'; unverifiable (item 2)")
c(A, "which is worse", "shortage", "ge_alloc", None, "nurse_coverage", "derived", alloc=B20, cmp=A20, deps=["O"],
  levels=[2], note="named quantity: orthopedics level 2 shortage of B against A; 'worse' is strict, ge_alloc is not")
c(A, "C) ... (chosen): no overflow", "overflow", "eq", 0, "overflow", "derived", alloc="dec")
c(A, "all L3 and L2 need covered in every department", "shortage", "eq", 0, "nurse_coverage", "derived",
  alloc="dec", levels=[2, 3], term="covered")
for d, v in (("IM", 1.3), ("C", 0.35), ("N", 0.45), ("O", 0.5)):
    c(A, "the 5-nurse shortage falls only on L1 (IM 1.3, cardiology 0.35, neurology 0.45, orthopedics 0.5)",
      "shortage", "round", v, "nurse_coverage", "copied", alloc="dec", deps=[d], levels=[1])
c(R, "Efficiency: no idle beds", "empty_beds", "eq", 0, "empty_beds", "derived", alloc="dec", term="idle",
  note="'idle beds' read as empty, no rival reading (as day 18); 'idle nurses' bare is a requirement figure")
c(T, "an L1 nurse shortage of about 2.6 nurse-equivalents in total", "shortage", "round", 2.6, "nurse_coverage",
  "derived", alloc="dec", levels=[1])
c(T, "Zero spare beds leaves no slack for tomorrow", "spare_beds", "eq", 0, "empty_beds", "derived", alloc="dec",
  rival=True)
