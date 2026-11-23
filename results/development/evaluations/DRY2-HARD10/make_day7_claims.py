"""Full manual claim extraction of DRY2's day-7 explanation (calibration for EVALUATION_PLAN.md §4, Point A).

Every verifiable figure in all six fields is one claim. Order "a/b/c/d" in the explanation is cardiology /
internal_medicine / neurology / orthopedics (the order the ALLOCATOR used throughout DRY2). Writes
explanation_claims_day7_spec.json next to this file; score with
    uv run python -c "from src.evaluation.claim_check import score; ..."  (see tests/test_claim_check.py)
"""

import json
from pathlib import Path

CA, IM, NE, OR = "cardiology", "internal_medicine", "neurology", "orthopedics"
A = {"decided": 7}
B = {"base": {"decided": 7}, "nurses": {CA: 5, IM: 1, NE: 0, OR: 0}}
C = {"in_effect": 6}
claims = []


CATEGORY = {"pool_beds": "pool", "pool_nurses": "pool", "free_beds": "pool", "beds": "beds", "nurses": "nurses",
            "empty_beds": "empty_beds", "overflow": "overflow", "patient_in_bed": "overflow",
            "shortage": "nurse_coverage", "covered_need": "nurse_coverage"}


def c(field, text, quantity=None, value=None, relation="eq", allocation=None, compare=None, day=7):
    d = {"id": f"D7-{len(claims) + 1:02d}", "finding": "day 7 (full extraction)", "author": "ALLOCATOR",
         "field": field, "text": text, "day": day,
         "category": CATEGORY.get((quantity or {}).get("name"), "other" if quantity else "not_a_figure")}
    if quantity is not None:
        d["quantity"] = quantity
        d["relation"] = relation
        if value is not None:
            d["value"] = str(value)
        if allocation is not None:
            d["allocation"] = allocation
        if compare is not None:
            d["compare_allocation"] = compare
    claims.append(d)


q = lambda name, **k: {"name": name, **k}

# situation
c("situation", "Pools 20 beds", q("pool_beds"), 20)
c("situation", "... and 6 nurses", q("pool_nurses"), 6)
c("situation", "occupied 18 of 20", q("holders"), 18)
c("situation", "Census 28", q("census"), 28)
c("situation", "cardiology 16", q("census", departments=[CA]), 16)
c("situation", "IM 7", q("census", departments=[IM]), 7)
c("situation", "neurology 2", q("census", departments=[NE]), 2)
c("situation", "orthopedics 3", q("census", departments=[OR]), 3)
c("situation", "so 10 patients are without a bed (before the decision: not holding a bed)", q("queue"), 10)
c("situation", "Cardiology is at max_beds 10", q("max_beds"), 10)
c("situation", "... and fully occupied", q("holders", departments=[CA]), 10)
c("situation", "Only 2 beds are not tied to occupied patients", q("free_beds"), 2)
c("situation", "N1 requirement is 13", q("requirement"), 13)
# alternatives: A
for dep, lv, v in ((CA, 3, 1), (CA, 2, 4), (CA, 1, 1), (IM, 1, 1), (OR, 1, 1)):
    c("alternatives", f"A: overflow {dep} L{lv} {v}", q("overflow", departments=[dep], levels=[lv]), v, allocation=A)
c("alternatives", "A: neurology overflow 0", q("overflow", departments=[NE]), 0, allocation=A)
c("alternatives", "A: L3 shortage cardiology 0.4", q("shortage", departments=[CA], levels=[3]), 0.4, allocation=A)
c("alternatives", "A: L3 shortage IM 0.6", q("shortage", departments=[IM], levels=[3]), 0.6, allocation=A)
# B
c("alternatives", "B: same overflow", q("overflow"), relation="eq_alloc", allocation=B, compare=A)
c("alternatives", "B: L3 shortage cardiology 0.4", q("shortage", departments=[CA], levels=[3]), 0.4, allocation=B)
c("alternatives", "B: L3 shortage neurology 0.6", q("shortage", departments=[NE], levels=[3]), 0.6, allocation=B)
c("alternatives", "B: IM L3 covered", q("shortage", departments=[IM], levels=[3]), 0, allocation=B)
c("alternatives", "B: total coverage slightly higher (1.0 vs 0.95 in the department) [referent unclear]")
c("alternatives", "A: total L3 shortage 1.0", q("shortage", levels=[3]), 1.0, allocation=A)
c("alternatives", "B: the same total L3 shortage of 1.0", q("shortage", levels=[3]), 1.0, allocation=B)
# C
c("alternatives", "C (current allocation): neurology L2 P000082 stays in overflow",
  q("patient_in_bed", patient_id="P000082"), 0, allocation=C)
c("alternatives", "C: orthopedics L1 P000083 gets a bed", q("patient_in_bed", patient_id="P000083"), 1, allocation=C)
c("alternatives", "I did not simulate other nurse splits ... leaves more L3 uncovered by my arithmetic [not a figure]")
# information_used
for dep, v in ((CA, 10), (IM, 5), (NE, 1), (OR, 2)):
    c("information_used", f"occupied beds {dep} {v}", q("holders", departments=[dep]), v)
c("information_used", "max_beds 10", q("max_beds"), 10)
for dep, v in ((CA, 10), (IM, 6), (NE, 1), (OR, 3)):
    c("information_used", f"in-effect beds {dep} {v}", q("beds", departments=[dep]), v, allocation=C)
for dep, v in ((CA, 5), (IM, 0), (NE, 1), (OR, 0)):
    c("information_used", f"in-effect nurses {dep} {v}", q("nurses", departments=[dep]), v, allocation=C)
for pid, dep, lv, day in (("P000074", CA, 3, 6), ("P000079", IM, 3, 7), ("P000072", CA, 2, 6), ("P000073", CA, 2, 6),
                          ("P000075", CA, 2, 6), ("P000082", NE, 2, 7)):
    c("information_used", f"queue: {pid} {dep} L{lv} day {day}",
      q("patient", patient_id=pid, department=dep, level=lv, arrival_day=day), 1)
for pid, dep, lv in (("P000081", CA, 2), ("P000078", IM, 1), ("P000080", CA, 1), ("P000083", OR, 1)):
    c("information_used", f"queue: {pid} {dep} L{lv}", q("patient", patient_id=pid, department=dep, level=lv), 1)
# reasons
c("reasons", "the 2 usable beds go to IM L3 (P000079) ...", q("patient_in_bed", patient_id="P000079"), 1, allocation=A)
c("reasons", "... and the neurology L2 (P000082)", q("patient_in_bed", patient_id="P000082"), 1, allocation=A)
c("reasons", "Orthopedics drops from 3 to 2 beds", q("beds", departments=[OR]), 2, allocation=A)
c("reasons", "(its spare bed was empty) ['empty' = no patient after assignment; the bed was free (not held), "
  "and under C it would go to P000083, so strict reading: wrong]", q("empty_beds", departments=[OR]), 1, allocation=C)
c("reasons", "1 nurse covers neurology L3 ...", q("shortage", departments=[NE], levels=[3]), 0, allocation=A)
c("reasons", "... plus L2", q("covered_need", departments=[NE], levels=[2]), 0.35, allocation=A)
c("reasons", "5 cover cardiology L3 nearly fully [qualitative]")
c("reasons", "all 20 beds assigned", q("beds"), 20, allocation=A)
c("reasons", "... and 6 nurses", q("nurses"), 6, allocation=A)
c("reasons", "no idle bed", q("empty_beds"), 0, allocation=A)
# tradeoffs
for dep, v in ((NE, 2), (OR, 2), (IM, 6), (CA, 10)):
    c("tradeoffs", f"beds moved: {dep} now {v}", q("beds", departments=[dep]), v, allocation=A)
c("tradeoffs", "IM L3 is uncovered (0.6)", q("shortage", departments=[IM], levels=[3]), 0.6, allocation=A)
c("tradeoffs", "the neurology nurse also covers 0.35 of L2", q("covered_need", departments=[NE], levels=[2]), 0.35,
  allocation=A)
c("tradeoffs", "orthopedics L1 waits in overflow", q("overflow", departments=[OR], levels=[1]), 1, allocation=A)
c("tradeoffs", "IM L1 waits in overflow", q("overflow", departments=[IM], levels=[1]), 1, allocation=A)
c("tradeoffs", "orthopedics L2 gets no nursing", q("covered_need", departments=[OR], levels=[2]), 0, allocation=A)
c("tradeoffs", "IM L2 gets no nursing", q("covered_need", departments=[IM], levels=[2]), 0, allocation=A)
# uncertainty
c("uncertainty", "Cardiology has had about 2.7 arrivals per day [days 1-7; 'about': within ±0.05]",
  q("mean_arrivals", departments=[CA], days=[1, 7]), 2.7, relation="round")
c("uncertainty", "with almost no discharges [vague]")
c("uncertainty", "Only 7 days of history [trivially true]")

out = Path(__file__).with_name("explanation_claims_day7_spec.json")
out.write_text(json.dumps({"run_id": "DRY2-HARD10", "note": "full extraction of the day-7 explanation",
                           "claims": claims}, indent=2) + "\n", encoding="utf-8", newline="\n")
print(len(claims), "claims")
