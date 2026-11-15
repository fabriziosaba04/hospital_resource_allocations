"""R1 claim extraction, days 21-25 (EVALUATION_PLAN.md §4; conventions in README.md of this folder)."""
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


# ---------------------------------------------------------------- day 21 (cur = decided 20, invalid today: 100 beds vs pool 96;
#                                    A = chosen = dec = 25/40/16/15, 11/14/9/3; B = same beds, 11/15/9/2)
D = 21
B21 = {"B": [25, 40, 16, 15], "N": [11, 15, 9, 2]}
INVALID = "the previous allocation fails validation today (CONSERVATION_BEDS, 100 vs 96): unverifiable (item 2)"
c(S, "The bed pool fell by 4", "pool_beds", "eq", 100, "pool", "derived", qday=20,
  note="restated: 'fell by 4 to 96' gives yesterday's pool 100 (item 2, end of the previous day)")
c(S, "to 96", "pool_beds", "eq", 96, "pool", "copied")
c(S, "The nurse pool is unchanged at 37", "pool_nurses", "eq", 37, "pool", "copied")
c(S, "Occupied beds total 84", "holders", "eq", 84, "beds", "copied")
per_dep(S, "The previous allocation was 30/37/19/14 beds", "beds", [30, 37, 19, 14], "beds", "copied", alloc="cur")
c(S, "(census 41, 36 occupied)", "holders", "eq", 36, "beds", "copied", deps=["IM"])
c(S, "It left internal_medicine ... short of beds", None, None, None, "overflow", "derived",
  note="intended: overflow IM under the previous allocation; " + INVALID)
c(S, "while cardiology had 6 spare", None, None, None, "empty_beds", "derived", term="spare",
  note="intended: spare_beds C under the previous allocation, rival empty; " + INVALID)
c(S, "and neurology 4 spare", None, None, None, "empty_beds", "derived", term="spare",
  note="intended: spare_beds N under the previous allocation, rival empty; " + INVALID)
c(S, "Nine patients are in the overflow queue", "queue", "eq", 9, "overflow", "derived")
per_dep(S, "IM 5, neurology 1, orthopedics 3", "queue", [None, 5, 1, 3], "overflow", "derived")
per_dep(I, "Occupied beds: cardiology 24, IM 36, neurology 14, orthopedics 10", "holders", [24, None, 14, 10],
        "beds", "copied")
for d in ("IM", "N"):
    c(I, "Overflow queue levels: L3 in IM and neurology", "queue", "ge", 1, "overflow", "derived", deps=[d],
      levels=[3], note="presence without a count; one claim per named department")
c(I, "L2 in IM (3)", "queue", "eq", 3, "overflow", "derived", deps=["IM"], levels=[2])
c(I, "and orthopedics (1)", "queue", "eq", 1, "overflow", "derived", deps=["O"], levels=[2])
c(I, "L1 in IM (1)", "queue", "eq", 1, "overflow", "derived", deps=["IM"], levels=[1])
c(I, "and orthopedics (2)", "queue", "eq", 2, "overflow", "derived", deps=["O"], levels=[1])
c(A, "A) ... Overflow is only 1 IM L1 patient", "overflow", "eq", 1, "overflow", "derived", alloc="dec")
c(A, "(P000919)", "patient_in_bed", "eq", 0, "overflow", "copied", alloc="dec", patient_id="P000919")
c(A, "All L3 and L2 nursing is covered", "shortage", "eq", 0, "nurse_coverage", "derived", alloc="dec",
  levels=[2, 3], term="covered")
c(A, "The only shortage is L1: IM 0.8", "shortage", "round", 0.8, "nurse_coverage", "copied", alloc="dec",
  deps=["IM"], levels=[1])
c(A, "orthopedics 1.15", "shortage", "round", 1.15, "nurse_coverage", "copied", alloc="dec", deps=["O"],
  levels=[1])
c(A, "B) Same beds with nurses 11/15/9/2. Valid, but orthopedics L2 is short by 0.95", "shortage", "round", 0.95,
  "nurse_coverage", "copied", alloc=B21, deps=["O"], levels=[2])
c(A, "which is worse by clinical priority", "covered_need", "lex_le_alloc", None, "nurse_coverage", "derived",
  alloc=B21, cmp="dec", term="no better",
  alt={"relation": "le_alloc", "quantity": {"name": "covered_need", "levels": [2, 3]}},
  note="'worse by clinical priority' read as B not better than A by tier (§11 #57); strictness not tested")
c(A, "IM L1 is covered instead", "shortage", "eq", 0, "nurse_coverage", "derived", alloc=B21, deps=["IM"],
  levels=[1], term="covered")
c(A, "it totals 100 beds against a pool of 96", "beds", "eq", 100, "beds", "derived", alloc="cur")
c(R, "the 3 spare beds go to", "spare_beds", "eq", 3, "empty_beds", "derived", alloc="dec", rival=True)
per_dep(R, "cardiology (+1), neurology (+1) and orthopedics (+2)", "spare_beds", [1, None, 1, 2], "empty_beds",
        "derived", alloc="dec", rival=True)
c(T, "about 2 nurse-equivalents of L1 coverage unmet", "shortage", "round", 2, "nurse_coverage", "derived",
  alloc="dec", levels=[1])

# ---------------------------------------------------------------- day 22 (cur = decided 21; dec = 24/37/18/17, 11/12/9/5)
D = 22
pools(S, "no external pool change (beds 96", 96, "nurses 37)", 37)
c(S, "orthopedics short 2 nurses (shortage 0.6 L1", "shortage", "round", 0.6, "nurse_coverage", "copied",
  alloc="cur", deps=["O"], levels=[1])
c(S, "and 0.8 L2 in simulation)", "shortage", "round", 0.8, "nurse_coverage", "copied", alloc="cur", deps=["O"],
  levels=[2])
c(S, "8 patients are waiting for a bed", "queue", "eq", 8, "overflow", "derived")
queue_lv(S, "4 L3", 4, "2 L2", 2, "2 L1", 2)
c(S, "and one L1 in IM has waited 1 day", "queue", "eq", 1, "overflow", "derived", deps=["IM"], levels=[1],
  note="count of IM level 1 patients waiting; the 1 day waited is a patient attribute (outside the universe)")
per_dep(I, "Occupied beds CA 20, IM 29, NE 14, OR 7", "holders", [20, 29, 14, 7], "beds", "copied")
c(I, "(total 70, no shock)", "holders", "eq", 70, "beds", "copied")
per_dep(A, "A) Keep the current allocation (CA 25, IM 40, NE 16, OR 15", "beds", [25, 40, 16, 15], "beds", "copied",
        alloc="cur")
per_dep(A, "nurses 11/14/9/3)", "nurses", [11, 14, 9, 3], "beds", "copied", alloc="cur")
c(A, "Zero bed overflow", "overflow", "eq", 0, "overflow", "derived", alloc="cur")
zero_outcomes(A, "B) Chosen: ... Zero overflow at every level", "and zero nurse shortage at every level", "dec")
c(R, "Beds above census (18 spare)", "empty_beds", "eq", 18, "empty_beds", "derived", alloc="dec",
  note="qualified 'above census'")
c(T, "IM keeps 6 spare beds", "spare_beds", "eq", 6, "empty_beds", "derived", alloc="dec", deps=["IM"], rival=True)
per_dep(T, "Spare beds elsewhere are small (CA 3, NE 3, OR 6)", "spare_beds", [3, None, 3, 6], "empty_beds",
        "derived", alloc="dec", rival=True)

# ---------------------------------------------------------------- day 23 (cur = decided 22, invalid today: 96 beds vs pool 86;
#                                    A = chosen = dec = 20/35/15/16, 9/14/8/6; B = 24/37/18/7, 11/12/9/5, invalid)
D = 23
c(S, "The bed pool fell externally by 10 (96", "pool_beds", "eq", 96, "pool", "derived", qday=22,
  note="past value: end of the previous day (item 2)")
c(S, "to 86)", "pool_beds", "eq", 86, "pool", "copied")
c(S, "the nurse pool is unchanged at 37", "pool_nurses", "eq", 37, "pool", "copied")
c(S, "Occupied beds total 62", "holders", "eq", 62, "beds", "copied")
per_dep(S, "The previous allocation (24/37/18/17)", "beds", [24, 37, 18, 17], "beds", "copied", alloc="cur")
c(S, "is not feasible because it sums to 96", "beds", "eq", 96, "beds", "derived", alloc="cur")
per_dep(I, "Occupied beds: cardiology 17, internal medicine 24, neurology 12, orthopedics 9", "holders",
        [17, 24, 12, 9], "beds", "copied")
c(I, "The overflow queue has 17 patients", "queue", "eq", 17, "overflow", "derived")
zero_outcomes(A, "A) ... Simulated: valid, zero overflow at every level", "zero nurse shortage", "dec")
INV_B = "alternative B fails validation (EVICTION): unverifiable (item 2)"
c(A, "It also leaves 7 orthopedics patients in overflow", None, None, None, "overflow", "copied",
  note="intended: overflow O under B eq 7; " + INV_B)
c(A, "including 3 level-2 patients", None, None, None, "overflow", "copied",
  note="intended: overflow O L2 under B eq 3; " + INV_B)
c(A, "and some level-1 nurse shortage", None, None, None, "nurse_coverage", "derived",
  note="intended: shortage L1 under B > 0; " + INV_B + "; also a vague qualifier ('some')")
c(R, "beds equal census in each department (19/32/14/14) plus 7 spare beds", "empty_beds", "eq", 7, "empty_beds",
  "derived", alloc="dec", note="qualified: 'census ... plus 7 spare' states the reading (beds above census)")
per_dep(R, "spread by recent arrival rates: internal medicine +3, orthopedics +2, cardiology +1, neurology +1",
        "empty_beds", [1, 3, 1, 2], "empty_beds", "derived", alloc="dec",
        note="qualified as the 7 spare beds above census of the same sentence")

# ---------------------------------------------------------------- day 24 (cur = decided 23; dec = 26/28/17/15, 12/11/9/5)
D = 24
pools(S, "no external pool change (beds 86", 86, "nurses 37)", 37)
per_dep(S, "The current allocation (cards 20, IM 35, neuro 15, ortho 16 beds)", "beds", [20, 35, 15, 16], "beds",
        "copied", alloc="cur")
c(S, "while IM has 8 surplus beds", "empty_beds", "eq", 8, "empty_beds", "derived", alloc="cur", deps=["IM"],
  term="surplus", note="'surplus' is not a rubric term; read against census, as the sentence compares census and "
                       "beds (beds minus patients placed), no rival reading")
c(S, "and ortho 2", "empty_beds", "eq", 2, "empty_beds", "derived", alloc="cur", deps=["O"], term="surplus",
  note="as the IM figure")
per_dep(I, "Occupied beds are 17, 21, 13 and 10", "holders", [17, 21, 13, 10], "beds", "copied")
c(I, "total 61", "holders", "eq", 61, "beds", "copied")
c(I, "The overflow queue has 20 patients", "queue", "eq", 20, "overflow", "derived")
c(I, "Current allocation simulation: overflow of 1 L3", "overflow", "eq", 1, "overflow", "copied", alloc="cur",
  deps=["C"], levels=[3])
c(I, "and 3 L2 in cardiology", "overflow", "eq", 3, "overflow", "copied", alloc="cur", deps=["C"], levels=[2])
c(I, "and 1 L1 in neurology", "overflow", "eq", 1, "overflow", "copied", alloc="cur", deps=["N"], levels=[1],
  note="alternatives A repeats these three figures; 'plus nurse shortages in cardiology and neurology' is "
       "extracted with A's figures")
for d, lv, v in (("C", 2, 1.95), ("C", 1, 0.4), ("N", 2, 0.5), ("N", 1, 0.2)):
    c(A, "nurse shortage of 1.95 L2 and 0.4 L1 in cardiology and 0.5 L2 and 0.2 L1 in neurology", "shortage",
      "round", v, "nurse_coverage", "copied", alloc="cur", deps=[d], levels=[lv])
zero_outcomes(A, "B) Chosen: ... Simulated overflow is zero", "and nurse shortage is zero in every department and level",
              "dec")
c(R, "beds match census with 5 spare beds", "empty_beds", "eq", 5, "empty_beds", "derived", alloc="dec",
  note="qualified: 'match census with 5 spare' states the reading (beds above census)")
per_dep(R, "2 in cardiology ..., and 1 each in IM, neurology and ortho", "empty_beds", [2, 1, 1, 1], "empty_beds",
        "derived", alloc="dec", note="qualified as the 5 spare beds above census of the same sentence")

# ---------------------------------------------------------------- day 25 (cur = decided 24 = "A"; B = 24/29/20/13, 12/12/9/4;
#                                    C = chosen = dec = 24/29/20/13, 12/11/10/4)
D = 25
B25 = {"B": [24, 29, 20, 13], "N": [12, 12, 9, 4]}
pools(S, "No external pool change (beds 86", 86, "nurses 37)", 37)
c(S, "69 beds are occupied", "holders", "eq", 69, "beds", "copied")
c(S, "That leaves 17 free beds", "free_beds", "eq", 17, "pool", "derived", rival=True, rival_alloc="dec")
c(S, "for 27 waiting patients", "queue", "eq", 27, "overflow", "derived")
c(S, "The current allocation leaves 3 level-2 patients waiting in neurology", "overflow", "eq", 3, "overflow",
  "copied", alloc="cur", deps=["N"], levels=[2])
c(S, "and 1 in internal medicine", "overflow", "eq", 1, "overflow", "copied", alloc="cur", deps=["IM"], levels=[2])
c(S, "while cardiology holds spare beds for level-1 patients", "spare_beds", "ge", 1, "empty_beds", "derived",
  alloc="cur", deps=["C"], rival=True)
per_dep(I, "Occupied beds: cardiology 19, internal medicine 24, neurology 15, orthopedics 11", "holders",
        [19, 24, 15, 11], "beds", "copied")
c(I, "Overflow queue: level 3 is 3 in cardiology", "queue", "eq", 3, "overflow", "derived", deps=["C"], levels=[3])
per_dep(I, "Level 2 is 2 in cardiology, 5 in internal medicine, 5 in neurology and 3 in orthopedics", "queue",
        [2, 5, 5, 3], "overflow", "derived", levels=[2])
c(I, "15 in total", "queue", "eq", 15, "overflow", "derived", levels=[2])
per_dep(I, "Level 1 is 2 in cardiology, 3 in internal medicine and 4 in orthopedics", "queue", [2, 3, None, 4],
        "overflow", "derived", levels=[1])
c(A, "A) ... Result: 4 level-2 patients wait (internal medicine 1, neurology 3)", "overflow", "eq", 4, "overflow",
  "derived", alloc="cur", levels=[2], note="the two department figures repeat the situation")
c(A, "while 2 level-1 patients are served in cardiology", "overflow", "eq", 0, "overflow", "derived", alloc="cur",
  deps=["C"], levels=[1], note="restated: the 2 queued cardiology level 1 patients (information_used) all get a bed")
c(A, "Neurology level-2 nursing is short by 0.65", "shortage", "round", 0.65, "nurse_coverage", "copied",
  alloc="cur", deps=["N"], levels=[2])
c(A, "B) ... Result: 1 level-2 patient waits", "overflow", "eq", 1, "overflow", "derived", alloc=B25, levels=[2])
c(A, "and neurology level-2 nursing is short by 0.65", "shortage", "round", 0.65, "nurse_coverage", "copied",
  alloc=B25, deps=["N"], levels=[2])
c(A, "C) Chosen ... all level-3 patients are bedded", "overflow", "eq", 0, "overflow", "derived", alloc="dec",
  levels=[3])
c(A, "14 of 15 level-2 patients are bedded", "overflow", "eq", 1, "overflow", "derived", alloc="dec", levels=[2],
  note="restated: 15 - 14 in overflow")
c(A, "and no level-3 or level-2 nursing shortage remains", "shortage", "eq", 0, "nurse_coverage", "derived",
  alloc="dec", levels=[2, 3])
c(R, "The only uncovered nursing is level-1 (internal medicine 1.15", "shortage", "round", 1.15, "nurse_coverage",
  "copied", alloc="dec", deps=["IM"], levels=[1])
c(R, "orthopedics 1.45)", "shortage", "round", 1.45, "nurse_coverage", "copied", alloc="dec", deps=["O"],
  levels=[1])
c(R, "I left it in orthopedics", "overflow", "eq", 1, "overflow", "copied", alloc="dec", deps=["O"], levels=[2])
c(R, "Efficiency: no bed is left empty", "empty_beds", "eq", 0, "empty_beds", "derived", alloc="dec", term="empty",
  alt={"quantity": {"name": "spare_beds"}})
c(T, "One level-2 patient (P000996, orthopedics) waits", "patient_in_bed", "eq", 0, "overflow", "copied",
  alloc="dec", patient_id="P000996")
c(T, "Nine level-1 patients wait", "overflow", "eq", 9, "overflow", "derived", alloc="dec", levels=[1])
