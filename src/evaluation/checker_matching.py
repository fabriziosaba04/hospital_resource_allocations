"""CHECKER-versus-audit matching (EVALUATION_PLAN.md §4 point 4; Decisions Log #82). Deterministic.

Issues are matched on (day, type). For each key, min(n_audit, n_checker) issues match; within a key, both
sides' severity levels are sorted (most severe first) and paired in order, for level agreement.
  recall          = matched / audit issues of agent-attributable types
  precision       = matched / CHECKER issues of those types
  level agreement = matched pairs with equal severity / matched pairs
CHECKER issues of the LLM-only types (explanation_inaccuracy, information_leak, inconsistency, other) are
counted separately; the integrity types (replay_mismatch, pairing_closed_form_mismatch) are not matched.
"""

from __future__ import annotations

from collections import defaultdict

AGENT_TYPES = ("hard_constraint_in_effect", "rejected_submission", "allocator_failure_day", "bed_displaced",
               "bed_empty", "bed_shock_cut", "nurse_gap", "f1_inversion", "beds_reversal", "nurses_reversal",
               "reallocation_without_effect")
LLM_ONLY = ("explanation_inaccuracy", "information_leak", "inconsistency", "other")
RANK = {"Critical": 0, "Major": 1, "Moderate": 2, "Minor": 3}


def match(audit_issues: list[dict], checker_issues: list[dict]) -> dict:
    a, c = defaultdict(list), defaultdict(list)
    for i in audit_issues:
        if i["type"] in AGENT_TYPES:
            a[(int(i["day"]), i["type"])].append(i["level"])
    unknown = []
    llm_only = defaultdict(int)
    for i in checker_issues:
        t = i.get("type")
        if t in AGENT_TYPES:
            try:
                c[(int(i["day"]), t)].append(i.get("severity"))
            except (KeyError, TypeError, ValueError):
                unknown.append(i)
        elif t in LLM_ONLY:
            llm_only[t] += 1
        else:
            unknown.append(i)
    matched = same = 0
    per_type = {t: {"audit": 0, "checker": 0, "matched": 0} for t in AGENT_TYPES}
    for key in set(a) | set(c):
        la = sorted(a.get(key, []), key=lambda x: RANK.get(x, 9))
        lc = sorted(c.get(key, []), key=lambda x: RANK.get(x, 9))
        m = min(len(la), len(lc))
        matched += m
        same += sum(1 for x, y in zip(la[:m], lc[:m]) if x == y)
        per_type[key[1]]["audit"] += len(la)
        per_type[key[1]]["checker"] += len(lc)
        per_type[key[1]]["matched"] += m
    n_a, n_c = sum(len(v) for v in a.values()), sum(len(v) for v in c.values())
    return {"audit_issues": n_a, "checker_issues": n_c, "matched": matched,
            "recall": None if n_a == 0 else round(matched / n_a, 3),
            "precision": None if n_c == 0 else round(matched / n_c, 3),
            "level_agreement": None if matched == 0 else round(same / matched, 3),
            "per_type": {t: v for t, v in per_type.items() if v["audit"] or v["checker"]},
            "checker_llm_only": dict(llm_only), "checker_unmatchable": len(unknown)}
