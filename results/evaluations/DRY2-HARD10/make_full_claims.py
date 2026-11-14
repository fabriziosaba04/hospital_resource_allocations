"""Full claim extraction of DRY2's ten explanations, universe categories only (EVALUATION_PLAN.md §4, Point A).

Rubric applied (EVALUATION_PLAN.md §4, "Explanation claims"): one claim per stated figure in the universe
(pools and free beds; beds and nurses allocated, occupied beds; empty beds; overflow and waiting patients by
tier, including named patients in or out of a bed; nursing need, coverage and shortage by tier). Department
order in "a/b/c/d" is cardiology / internal medicine / neurology / orthopedics, as the ALLOCATOR used it. A
figure repeated in another field is extracted once. Day 7 comes from make_day7_claims.py (all categories).
Writes explanation_claims_full_spec.json.
"""

import json
from pathlib import Path

CA, IM, NE, OR = "cardiology", "internal_medicine", "neurology", "orthopedics"
CAT = {"pool_beds": "pool", "pool_nurses": "pool", "free_beds": "pool", "beds": "beds", "nurses": "beds",
       "holders": "beds", "empty_beds": "empty_beds", "overflow": "overflow", "queue": "overflow",
       "patient_in_bed": "overflow", "holders_cut": "overflow", "shortage": "nurse_coverage",
       "covered_need": "nurse_coverage", "need": "nurse_coverage"}
claims = []
DAY = [0]


def q(name, deps=None, levels=None, **k):
    d = {"name": name, **k}
    if deps:
        d["departments"] = deps
    if levels:
        d["levels"] = levels
    return d


def c(field, text, quantity, value=None, alloc=None, rel="eq", compare=None):
    d = {"id": f"D{DAY[0]}-{sum(1 for x in claims if x['day'] == DAY[0]) + 1:02d}", "finding": f"day {DAY[0]}",
         "author": "ALLOCATOR", "field": field, "text": text, "day": DAY[0], "category": CAT[quantity["name"]],
         "quantity": quantity, "relation": rel}
    if value is not None:
        d["value"] = str(value)
    if alloc is not None:
        d["allocation"] = alloc
    if compare is not None:
        d["compare_allocation"] = compare
    claims.append(d)


def nurses(a, b, cc, dd, base):
    return {"base": base, "nurses": {CA: a, IM: b, NE: cc, OR: dd}}


def alloc4(beds, nrs):
    return {"beds": dict(zip((CA, IM, NE, OR), beds)), "nurses": dict(zip((CA, IM, NE, OR), nrs))}


def beds_each(field, text, vals, alloc):
    for dep, v in zip((CA, IM, NE, OR), vals):
        c(field, f"{text} {dep} {v}", q("beds", [dep]), v, alloc)


def nurses_each(field, text, vals, alloc):
    for dep, v in zip((CA, IM, NE, OR), vals):
        c(field, f"{text} {dep} {v}", q("nurses", [dep]), v, alloc)


def holders_each(field, vals):
    for dep, v in zip((CA, IM, NE, OR), vals):
        c(field, f"occupied {dep} {v}", q("holders", [dep]), v)


def pools(b, n):
    c("situation", f"pool {b} beds", q("pool_beds"), b)
    c("situation", f"pool {n} nurses", q("pool_nurses"), n)


# ------------------------------------------------------------------ day 1
DAY[0] = 1
INIT, CH = {"in_effect": 0}, {"decided": 1}
c("alternatives", "A (current nurses): no overflow", q("overflow"), 0, INIT)
c("alternatives", "A: cardiology L3 uncovered by 0.2", q("shortage", [CA], [3]), 0.2, INIT)
c("alternatives", "A: IM L2 covered 1.4", q("covered_need", [IM], [2]), 1.4, INIT)
c("alternatives", "A: IM L1 covered 0.4", q("covered_need", [IM], [1]), 0.4, INIT)
c("alternatives", "B: all L3 covered", q("shortage", levels=[3]), 0, CH)
c("alternatives", "B: IM L2 shortage 0.6", q("shortage", [IM], [2]), 0.6, CH)
c("alternatives", "B: IM L1 shortage 0.6", q("shortage", [IM], [1]), 0.6, CH)
c("alternatives", "B: orthopedics L1 shortage 0.4", q("shortage", [OR], [1]), 0.4, CH)
beds_each("information_used", "initial beds", (4, 10, 1, 5), INIT)
nurses_each("information_used", "initial nurses", (1, 3, 1, 1), INIT)
c("information_used", "empty overflow queue", q("queue"), 0)
c("reasons", "nothing is overflowed", q("overflow"), 0, CH)
c("reasons", "the single spare bed stays in IM", q("empty_beds", [IM]), 1, CH)
c("reasons", "(single spare bed in total)", q("empty_beds"), 1, CH)
c("reasons", "all 6 nurses used", q("nurses"), 6, CH)
c("reasons", "20 beds assigned", q("beds"), 20, CH)
pools(20, 6)
c("situation", "Occupied beds 19", q("holders"), 19)
holders_each("situation", (4, 9, 1, 5))
c("tradeoffs", "Orthopedics level-1 gets 0.4 coverage", q("covered_need", [OR], [1]), 0.4, CH)

# ------------------------------------------------------------------ day 2
DAY[0] = 2
A, KEEP = {"decided": 2}, {"in_effect": 1}
B = alloc4((8, 7, 2, 3), (4, 1, 1, 0))
c("alternatives", "A: overflow 1 L2 in IM", q("overflow", [IM], [2]), 1, A)
c("alternatives", "A: overflow total 1", q("overflow"), 1, A)
c("alternatives", "A: every L3 has a bed", q("overflow", levels=[3]), 0, A)
for dep, v in ((CA, 0.6), (IM, 0.2), (NE, 0.2), (OR, 0)):
    c("alternatives", f"A: L3 shortage {dep} {v}", q("shortage", [dep], [3]), v, A)
c("alternatives", "B: overflow 1 L2 in cardiology", q("overflow", [CA], [2]), 1, B)
c("alternatives", "B: overflow total 1", q("overflow"), 1, B)
for dep, v in ((IM, 0.2), (NE, 0.2), (OR, 0.6)):
    c("alternatives", f"B: L3 shortage {dep} {v}", q("shortage", [dep], [3]), v, B)
c("alternatives", "B: cardiology level-2 gets 0.4 coverage", q("covered_need", [CA], [2]), 0.4, B)
c("alternatives", "keep: overflow 5 L3 in cardiology and neurology", q("overflow", [CA, NE], [3]), 5, KEEP)
c("alternatives", "keep: 4 beds empty in IM and orthopedics", q("empty_beds", [IM, OR]), 4, KEEP)
beds_each("information_used", "current beds", (4, 10, 1, 5), KEEP)
nurses_each("information_used", "current nurses", (2, 2, 1, 1), KEEP)
c("reasons", "level-3 need totals 6.6", q("need", levels=[3]), 6.6)
c("reasons", "no bed is empty", q("empty_beds"), 0, A)
pools(20, 6)
c("situation", "Occupied beds 14", q("holders"), 14)
holders_each("situation", (4, 6, 1, 3))
c("situation", "Seven new arrivals wait without a bed", q("queue"), 7)
c("situation", "5 level-3 waiting: cardiology 4", q("queue", [CA], [3]), 4)
c("situation", "... neurology 1", q("queue", [NE], [3]), 1)
c("situation", "2 level-2 waiting", q("queue", levels=[2]), 2)
beds_each("tradeoffs", "beds now", (9, 6, 2, 3), A)
c("tradeoffs", "IM level-2 shortage 1.75", q("shortage", [IM], [2]), 1.75, A)
c("tradeoffs", "orthopedics' nurse covers its level-3 need 0.6", q("covered_need", [OR], [3]), 0.6, A)
c("tradeoffs", "... plus 0.4 of level-1", q("covered_need", [OR], [1]), 0.4, A)
c("tradeoffs", "cardiology, IM, neurology level-3 short 1.0 total", q("shortage", [CA, IM, NE], [3]), 1.0, A)
c("tradeoffs", "moving orthopedics' only nurse ... is no better (levels 2-3 covered)", q("covered_need", levels=[2, 3]),
  alloc=nurses(4, 1, 1, 0, A), rel="le_alloc", compare=A)

# ------------------------------------------------------------------ day 3
DAY[0] = 3
A, B = {"decided": 3}, {"in_effect": 2}
c("alternatives", "A: zero overflow", q("overflow"), 0, A)
for dep, v in ((CA, 0.2), (NE, 0.2), (OR, 0.6)):
    c("alternatives", f"A: L3 shortage {dep} {v}", q("shortage", [dep], [3]), v, A)
c("alternatives", "A: L3 shortage total 1.0", q("shortage", levels=[3]), 1.0, A)
c("alternatives", "B: zero overflow", q("overflow"), 0, B)
c("alternatives", "B: L3 shortage cardiology 1.2", q("shortage", [CA], [3]), 1.2, B)
c("alternatives", "B: L3 shortage neurology 0.2", q("shortage", [NE], [3]), 0.2, B)
c("alternatives", "B: L3 shortage total 1.4", q("shortage", levels=[3]), 1.4, B)
c("alternatives", "B: orthopedics L3 covered", q("shortage", [OR], [3]), 0, B)
c("alternatives", "B: orthopedics L1 covered", q("shortage", [OR], [1]), 0, B)
holders_each("information_used", (7, 4, 2, 1))
beds_each("information_used", "in-effect beds", (9, 6, 2, 3), B)
nurses_each("information_used", "in-effect nurses", (3, 1, 1, 1), B)
c("reasons", "P000045 gets a bed", q("patient_in_bed", patient_id="P000045"), 1, A)
for dep in (CA, IM, OR):
    c("reasons", f"spare bed in {dep}", q("empty_beds", [dep]), 1, A)
c("reasons", "Three beds are spare", q("empty_beds"), 3, A)
pools(20, 6)
c("situation", "occupied 14 of 20", q("holders"), 14)
c("situation", "Three patients lack a bed", q("queue"), 3)
c("tradeoffs", "orthopedics L3 patient (0.6) gets no nursing", q("shortage", [OR], [3]), 0.6, A)
c("tradeoffs", "orthopedics L1 (0.2) gets no nursing", q("shortage", [OR], [1]), 0.2, A)
c("tradeoffs", "IM L2 is short 1.0", q("shortage", [IM], [2]), 1.0, A)
c("tradeoffs", "cardiology L2 short 0.35", q("shortage", [CA], [2]), 0.35, A)
c("tradeoffs", "L3 need 6.6", q("need", levels=[3]), 6.6)
c("tradeoffs", "IM's one nurse covers 0.6 L3", q("covered_need", [IM], [3]), 0.6, A)
c("tradeoffs", "... plus 0.4 L2", q("covered_need", [IM], [2]), 0.4, A)

# ------------------------------------------------------------------ day 4
DAY[0] = 4
A, KEEP = {"decided": 4}, {"in_effect": 3}
B = nurses(5, 2, 1, 0, A)
c("alternatives", "A: zero overflow", q("overflow"), 0, A)
c("alternatives", "A: all L3 covered", q("shortage", levels=[3]), 0, A)
for dep, lv, v in ((IM, 2, 0.3), (IM, 1, 0.2), (CA, 2, 0.15), (OR, 1, 0.55)):
    c("alternatives", f"A: shortage {dep} L{lv} {v}", q("shortage", [dep], [lv]), v, A)
c("alternatives", "B: zero overflow", q("overflow"), 0, B)
c("alternatives", "B: all L3 covered", q("shortage", levels=[3]), 0, B)
c("alternatives", "B: IM fully covered", q("shortage", [IM]), 0, B)
c("alternatives", "B: orthopedics L2 shortage 0.35", q("shortage", [OR], [2]), 0.35, B)
c("alternatives", "B: orthopedics L1 shortage 1.2", q("shortage", [OR], [1]), 1.2, B)
c("alternatives", "keep: sums to 20 beds", q("beds"), 20, KEEP)
c("alternatives", "keep: ... and 6 nurses", q("nurses"), 6, KEEP)
beds_each("information_used", "in-effect beds", (9, 6, 2, 3), KEEP)
nurses_each("information_used", "in-effect nurses", (4, 1, 1, 0), KEEP)
c("reasons", "Nobody is overflowed", q("overflow"), 0, A)
c("reasons", "The 2 spare beds", q("empty_beds"), 2, A)
c("reasons", "all 23 beds assigned", q("beds"), 23, A)
c("reasons", "... and 8 nurses", q("nurses"), 8, A)
pools(23, 8)
c("situation", "Occupied beds 12", q("holders"), 12)
holders_each("situation", (7, 3, 1, 1))
c("situation", "Nine patients are in the overflow queue", q("queue"), 9)
for dep, lv, v in ((CA, 3, 2), (OR, 2, 1), (OR, 1, 5), (IM, 1, 1)):
    c("situation", f"queue {dep} L{lv} {v}", q("queue", [dep], [lv]), v)
beds_each("tradeoffs", "beds now", (10, 4, 1, 8), A)
c("tradeoffs", "nurses cardiology 4 -> 5", q("nurses", [CA]), 5, A)
c("tradeoffs", "orthopedics 0 -> 1", q("nurses", [OR]), 1, A)
c("tradeoffs", "Neurology's nurse covers 0.6 of L3 need", q("covered_need", [NE], [3]), 0.6, A)

# ------------------------------------------------------------------ day 5
DAY[0] = 5
B, KEEP = {"decided": 5}, {"in_effect": 4}
A = nurses(5, 1, 1, 1, B)
c("alternatives", "A: zero overflow", q("overflow"), 0, A)
c("alternatives", "A: all L3 covered", q("shortage", levels=[3]), 0, A)
for dep, lv, v in ((IM, 2, 0.3), (IM, 1, 0.2), (CA, 2, 0.5)):
    c("alternatives", f"A: shortage {dep} L{lv} {v}", q("shortage", [dep], [lv]), v, A)
c("alternatives", "A: L2 total 0.8", q("shortage", levels=[2]), 0.8, A)
c("alternatives", "A: L1 total 0.2", q("shortage", levels=[1]), 0.2, A)
c("alternatives", "B: zero overflow", q("overflow"), 0, B)
c("alternatives", "B: all L3 covered", q("shortage", levels=[3]), 0, B)
for dep, lv, v in ((IM, 2, 0.3), (IM, 1, 0.2), (OR, 2, 0.35), (OR, 1, 0.6)):
    c("alternatives", f"B: shortage {dep} L{lv} {v}", q("shortage", [dep], [lv]), v, B)
c("alternatives", "B: L2 total 0.65", q("shortage", levels=[2]), 0.65, B)
c("alternatives", "B: L1 total 0.8", q("shortage", levels=[1]), 0.8, B)
holders_each("information_used", (7, 2, 1, 3))
beds_each("information_used", "in-effect beds", (10, 4, 1, 8), KEEP)
nurses_each("information_used", "in-effect nurses", (5, 1, 1, 1), KEEP)
c("reasons", "cardiology L2 is fully covered", q("shortage", [CA], [2]), 0, B)
c("reasons", "4 spare beds", q("empty_beds"), 4, B)
c("reasons", "all 23 beds assigned", q("beds"), 23, B)
c("reasons", "... and 8 nurses", q("nurses"), 8, B)
pools(23, 8)
c("situation", "occupied 13 of 23", q("holders"), 13)
c("situation", "Six patients arrived today without a bed", q("queue"), 6)
for dep, lv, v in ((CA, 3, 1), (CA, 2, 2), (IM, 2, 1), (IM, 1, 1), (OR, 1, 1)):
    c("situation", f"queue {dep} L{lv} {v}", q("queue", [dep], [lv]), v)
beds_each("tradeoffs", "beds now", (10, 5, 2, 6), B)
c("tradeoffs", "nurses orthopedics 1 to 0", q("nurses", [OR]), 0, B)
c("tradeoffs", "cardiology 5 to 6", q("nurses", [CA]), 6, B)
c("tradeoffs", "total shortage B 1.45", q("shortage"), 1.45, B)
c("tradeoffs", "vs A 1.0", q("shortage"), 1.0, A)

# ------------------------------------------------------------------ day 6
DAY[0] = 6
A, KEEP = {"decided": 6}, {"in_effect": 5}
B = nurses(6, 0, 0, 0, A)
c("alternatives", "A: overflow cardiology 1 L3", q("overflow", [CA], [3]), 1, A)
c("alternatives", "A: overflow cardiology 3 L2", q("overflow", [CA], [2]), 3, A)
c("alternatives", "A: overflow only in cardiology", q("overflow", [IM, NE, OR]), 0, A)
c("alternatives", "A: L3 shortage only cardiology 0.4", q("shortage", levels=[3]), 0.4, A)
for dep, v in ((CA, 1.75), (IM, 1.75), (OR, 0.7)):
    c("alternatives", f"A: L2 shortage {dep} {v}", q("shortage", [dep], [2]), v, A)
c("alternatives", "B (6/0/0/0): cardiology L3 fully covered", q("shortage", [CA], [3]), 0, B)
c("alternatives", "B: neurology L3 uncovered (0.6)", q("shortage", [NE], [3]), 0.6, B)
c("alternatives", "B: cardiology L2 gets 0.6 coverage", q("covered_need", [CA], [2]), 0.6, B)
c("alternatives", "keep: 23 beds", q("beds"), 23, KEEP)
c("alternatives", "keep: 8 nurses", q("nurses"), 8, KEEP)
beds_each("information_used", "in-effect beds", (10, 5, 2, 6), KEEP)
nurses_each("information_used", "in-effect nurses", (6, 1, 1, 0), KEEP)
c("reasons", "The 5 free beds", q("free_beds"), 5)
c("reasons", "waiting L2 in IM: 3", q("queue", [IM], [2]), 3)
c("reasons", "waiting L2 in orthopedics: 2", q("queue", [OR], [2]), 2)
c("reasons", "no bed is idle", q("empty_beds"), 0, A)
c("reasons", "neurology occupied is 1", q("holders", [NE]), 1)
c("reasons", "neurology covers its L3 fully", q("shortage", [NE], [3]), 0, A)
c("reasons", "cardiology 5 covers 5 of 5.4 L3: covered", q("covered_need", [CA], [3]), 5, A)
c("reasons", "... need 5.4", q("need", [CA], [3]), 5.4)
pools(20, 6)
c("situation", "Occupied beds 15", q("holders"), 15)
holders_each("situation", (10, 3, 1, 1))
c("situation", "9 patients wait without a bed", q("queue"), 9)
for dep, lv, v in ((CA, 3, 1), (CA, 2, 3), (IM, 2, 3), (OR, 2, 2)):
    c("situation", f"queue {dep} L{lv} {v}", q("queue", [dep], [lv]), v)
beds_each("tradeoffs", "beds now", (10, 6, 1, 3), A)
c("tradeoffs", "IM L2 housed but uncovered (shortage 1.75)", q("shortage", [IM], [2]), 1.75, A)
c("tradeoffs", "orthopedics L2 shortage 0.7", q("shortage", [OR], [2]), 0.7, A)
c("tradeoffs", "Cardiology L3 is short 0.4", q("shortage", [CA], [3]), 0.4, A)

# ------------------------------------------------------------------ day 8
DAY[0] = 8
A, KEEP = {"decided": 8}, {"in_effect": 7}
B = alloc4((6, 3, 2, 0), (4, 1, 0, 0))
for dep, lv, v in ((CA, 3, 1), (CA, 2, 4), (CA, 1, 1), (IM, 2, 4), (IM, 1, 1), (NE, 1, 1), (OR, 2, 1), (OR, 1, 2)):
    c("alternatives", f"A: overflow {dep} L{lv} {v}", q("overflow", [dep], [lv]), v, A)
c("alternatives", "A: L3 shortage cardiology 0.2", q("shortage", [CA], [3]), 0.2, A)
c("alternatives", "A: L3 shortage IM 0.6", q("shortage", [IM], [3]), 0.6, A)
c("alternatives", "A: L3 shortage total 0.8", q("shortage", levels=[3]), 0.8, A)
c("alternatives", "B: L3 shortage total 0.8", q("shortage", levels=[3]), 0.8, B)
c("alternatives", "B: cardiology 0.2", q("shortage", [CA], [3]), 0.2, B)
c("alternatives", "B: neurology 0.6", q("shortage", [NE], [3]), 0.6, B)
c("alternatives", "B: cuts P000066", q("patient_in_bed", patient_id="P000066"), 0, B)
c("alternatives", "B: cardiology overflow gets 5 L2", q("overflow", [CA], [2]), 5, B)
c("information_used", "shortfall 3 (occupied minus pool)", q("free_beds"), -3)
beds_each("information_used", "in-effect beds", (10, 6, 2, 2), KEEP)
nurses_each("information_used", "in-effect nurses", (5, 0, 1, 0), KEEP)
c("information_used", "occupied L3 = 8", q("holders", levels=[3]), 8)
for dep, v in ((CA, 6), (IM, 1), (NE, 1)):
    c("information_used", f"occupied L3 {dep} {v}", q("holders", [dep], [3]), v)
c("information_used", "occupied L2 = 6", q("holders", levels=[2]), 6)
for dep, v in ((CA, 1), (IM, 4), (NE, 1)):
    c("information_used", f"occupied L2 {dep} {v}", q("holders", [dep], [2]), v)
c("information_used", "occupied L1 = 0", q("holders", levels=[1]), 0)
c("reasons", "all 8 L3 occupants keep beds", q("holders_cut", levels=[3]), 0, A)
c("reasons", "no beds are free (all 11 occupied)", q("empty_beds"), 0, A)
c("reasons", "4 to cardiology covers 4.0 of L3", q("covered_need", [CA], [3]), 4.0, A)
c("reasons", "... of 4.2 L3 need", q("need", [CA], [3]), 4.2)
c("reasons", "neurology covers its L3 (0.6)", q("covered_need", [NE], [3]), 0.6, A)
c("reasons", "5.4 L3 need", q("need", levels=[3]), 5.4)
c("reasons", "IM has the most L2 occupants (4)", q("holders", [IM], [2]), 4)
pools(11, 5)
c("situation", "Occupied beds total 14", q("holders"), 14)
holders_each("situation", (7, 5, 2, 0))
c("situation", "12 patients in the overflow queue", q("queue"), 12)
beds_each("tradeoffs", "beds now", (7, 2, 2, 0), A)
c("tradeoffs", "3 IM L2 patients lose their beds", q("holders_cut", [IM], [2]), 3, A)
c("tradeoffs", "neurology's nurse also covers 0.35 of L2", q("covered_need", [NE], [2]), 0.35, A)

# ------------------------------------------------------------------ day 9
DAY[0] = 9
A, KEEP = {"decided": 9}, {"in_effect": 8}
B = nurses(4, 1, 0, 0, A)
c("alternatives", "A: no L3 in overflow", q("overflow", levels=[3]), 0, A)
for dep, lv, v in ((CA, 2, 4), (IM, 2, 3), (OR, 2, 1), (CA, 1, 1), (IM, 1, 2), (NE, 1, 1), (OR, 1, 4)):
    c("alternatives", f"A: overflow {dep} L{lv} {v}", q("overflow", [dep], [lv]), v, A)
c("alternatives", "A: L3 shortage cardiology 0.6", q("shortage", [CA], [3]), 0.6, A)
c("alternatives", "A: L3 shortage IM 0.2", q("shortage", [IM], [3]), 0.2, A)
c("alternatives", "A: L3 shortage total 0.8", q("shortage", levels=[3]), 0.8, A)
c("alternatives", "B: same overflow", q("overflow"), alloc=B, rel="eq_alloc", compare=A)
c("alternatives", "B: L3 shortage total 0.8", q("shortage", levels=[3]), 0.8, B)
c("alternatives", "B: IM 0.2", q("shortage", [IM], [3]), 0.2, B)
c("alternatives", "B: neurology 0.6", q("shortage", [NE], [3]), 0.6, B)
c("alternatives", "B: cardiology's spare 0.4 covers L2", q("covered_need", [CA], [2]), 0.4, B)
c("alternatives", "4 free beds", q("free_beds"), 4)
c("alternatives", "4 waiting L3", q("queue", levels=[3]), 4)
pools(11, 5)
c("information_used", "L3 waiting cardiology 3", q("queue", [CA], [3]), 3)
c("information_used", "L3 waiting IM 1", q("queue", [IM], [3]), 1)
for dep, v in ((CA, 4), (IM, 3), (OR, 1)):
    c("information_used", f"L2 waiting {dep} {v}", q("queue", [dep], [2]), v)
c("information_used", "L1 waiting 8", q("queue", levels=[1]), 8)
beds_each("information_used", "in-effect beds", (7, 2, 2, 0), KEEP)
nurses_each("information_used", "in-effect nurses", (4, 0, 1, 0), KEEP)
c("reasons", "occupied 7", q("holders"), 7)
c("reasons", "P000074 gets a bed", q("patient_in_bed", patient_id="P000074"), 1, A)
c("reasons", "neurology's nurse has 0.4 left after L3 (goes to L2 and L1)", q("covered_need", [NE], [1, 2]), 0.4, A)
c("reasons", "no empty bed", q("empty_beds"), 0, A)
holders_each("situation", (4, 1, 2, 0))
c("situation", "20 patients in the overflow queue", q("queue"), 20)
c("situation", "4 of them are L3", q("queue", levels=[3]), 4)
c("tradeoffs", "orthopedics L2 (P000088) waits", q("patient_in_bed", patient_id="P000088"), 0, A)
c("tradeoffs", "nurses cardiology 3", q("nurses", [CA]), 3, A)
c("tradeoffs", "IM 1", q("nurses", [IM]), 1, A)

# ------------------------------------------------------------------ day 10
DAY[0] = 10
A, KEEP = {"decided": 10}, {"in_effect": 9}
B = nurses(3, 1, 1, 1, A)
c("alternatives", "A: overflow only 2 L1", q("overflow"), 2, A)
c("alternatives", "A: overflow L1 = 2", q("overflow", levels=[1]), 2, A)
c("alternatives", "A: IM P000096 in overflow", q("patient_in_bed", patient_id="P000096"), 0, A)
c("alternatives", "A: orthopedics P000103 in overflow", q("patient_in_bed", patient_id="P000103"), 0, A)
c("alternatives", "A: all L3 and L2 housed", q("overflow", levels=[2, 3]), 0, A)
c("alternatives", "A: L3 shortage 0", q("shortage", levels=[3]), 0, A)
for dep, v in ((CA, 0.8), (IM, 0.15), (NE, 0.3), (OR, 0.35)):
    c("alternatives", f"A: L2 shortage {dep} {v}", q("shortage", [dep], [2]), v, A)
c("alternatives", "B: same overflow", q("overflow"), alloc=B, rel="eq_alloc", compare=A)
c("alternatives", "B: IM L3 short 0.8", q("shortage", [IM], [3]), 0.8, B)
c("alternatives", "B: orthopedics L2 covered", q("shortage", [OR], [2]), 0, B)
c("alternatives", "keep: 11 beds", q("beds"), 11, KEEP)
c("alternatives", "keep: 5 nurses", q("nurses"), 5, KEEP)
beds_each("information_used", "in-effect beds", (7, 2, 2, 0), KEEP)
nurses_each("information_used", "in-effect nurses", (3, 1, 1, 0), KEEP)
c("reasons", "L3 need (4.8)", q("need", levels=[3]), 4.8)
for pid in ("P000085", "P000087", "P000094"):
    c("reasons", f"oldest L1 {pid} gets a bed", q("patient_in_bed", patient_id=pid), 1, A)
c("reasons", "no empty bed", q("empty_beds"), 0, A)
c("reasons", "all 20 beds assigned", q("beds"), 20, A)
c("reasons", "... and 6 nurses", q("nurses"), 6, A)
pools(20, 6)
c("situation", "Occupied beds 6", q("holders"), 6)
holders_each("situation", (3, 2, 1, 0))
c("situation", "16 patients are in the queue", q("queue"), 16)
beds_each("tradeoffs", "beds now", (8, 4, 4, 4), A)
c("tradeoffs", "IM 1 -> 2 nurses", q("nurses", [IM]), 2, A)
c("tradeoffs", "orthopedics has no nurse", q("nurses", [OR]), 0, A)

# ------------------------------------------------------------------ day 7 (from the full day-7 extraction)
here = Path(__file__).parent
d7 = json.loads((here / "explanation_claims_day7_spec.json").read_text(encoding="utf-8"))["claims"]
d7_universe = [x for x in d7 if x.get("category") in ("pool", "beds", "nurses", "empty_beds", "overflow",
                                                      "nurse_coverage")]
for x in d7_universe:
    x = dict(x)
    x["category"] = "beds" if x["category"] == "nurses" else x["category"]
    x["finding"] = "day 7"
    claims.append(x)

claims.sort(key=lambda x: (x["day"], x["id"]))
(here / "explanation_claims_full_spec.json").write_text(
    json.dumps({"run_id": "DRY2-HARD10", "note": "full extraction, universe categories (EVALUATION_PLAN.md §4)",
                # the CHECKER's explanation findings (day-5 report), mapped to the claims they contest
                "disputed_by_checker": {"D2-14": "issue 3 (keep: 5 L3 overflow called wrong)",
                                        "D2-15": "issue 3 (keep: 4 empty beds called wrong)",
                                        "D2-45": "issue 2 (moving orthopedics' nurse is 'no better')"},
                "claims": claims}, indent=2) + "\n", encoding="utf-8", newline="\n")
print(len(claims), "claims")
