"""CHECKER-versus-audit matching (EVALUATION_PLAN.md §4 point 4; Decisions Log #82). Deterministic.

Issues are matched on (day, type). For each key, min(n_audit, n_checker) issues match; within a key, both
sides' severity levels are sorted (most severe first) and paired in order, for level agreement.
  recall          = matched / audit issues of agent-attributable types
  precision       = matched / CHECKER issues of those types
  level agreement = matched pairs with equal severity / matched pairs
CHECKER issues of the LLM-only types (explanation_inaccuracy, information_leak, inconsistency, other) are
counted separately; the integrity types (replay_mismatch, pairing_closed_form_mismatch) are not matched.

Stratified reporting (owner decision §11 #37; Log #86). The pooled figures are dominated by the many Minor
reversals, so the same pairing is also reported
  - by type;
  - by severity level: recall over audit issues of that level, precision over CHECKER issues of that level,
    level agreement over matched audit issues of that level;
  - by group: HEADLINE (clinical and hard-constraint types), SECONDARY (reversals and reallocations without
    effect), OTHER (the remaining deterministic types, rejected_submission and f1_inversion).
Within a (day, type) key the pairing is the approved one (Log #82): both sides sorted most severe first, the
first min(n_audit, n_checker) of each paired in order. So when the CHECKER reports fewer issues than the
audit under a key, the matched audit issues are taken to be its most severe ones (stated with the results).
"""

from __future__ import annotations

from collections import defaultdict

AGENT_TYPES = ("hard_constraint_in_effect", "rejected_submission", "allocator_failure_day", "bed_displaced",
               "bed_empty", "bed_shock_cut", "nurse_gap", "f1_inversion", "beds_reversal", "nurses_reversal",
               "reallocation_without_effect")
LLM_ONLY = ("explanation_inaccuracy", "information_leak", "inconsistency", "other")
RANK = {"Critical": 0, "Major": 1, "Moderate": 2, "Minor": 3}


HEADLINE = ("hard_constraint_in_effect", "bed_displaced", "bed_empty", "bed_shock_cut", "nurse_gap",
            "allocator_failure_day")
SECONDARY = ("beds_reversal", "nurses_reversal", "reallocation_without_effect")
OTHER = tuple(t for t in AGENT_TYPES if t not in HEADLINE + SECONDARY)
LEVELS = ("Critical", "Major", "Moderate", "Minor")


def _ratio(num: int, den: int):
    return None if den == 0 else round(num / den, 3)


def _stats(audit_side: list[tuple], checker_side: list[tuple]) -> dict:
    """audit_side: (level, matched, checker_level or None); checker_side: (level, matched)."""
    m_a = [x for x in audit_side if x[1]]
    return {"audit": len(audit_side), "checker": len(checker_side), "matched": len(m_a),
            "recall": _ratio(len(m_a), len(audit_side)),
            "precision": _ratio(sum(1 for x in checker_side if x[1]), len(checker_side)),
            "level_agreement": _ratio(sum(1 for x in m_a if x[0] == x[2]), len(m_a))}


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
    a_rows, c_rows = [], []                       # (type, level, matched, partner level) / (type, level, matched)
    for key in sorted(set(a) | set(c)):
        la = sorted(a.get(key, []), key=lambda x: RANK.get(x, 9))
        lc = sorted(c.get(key, []), key=lambda x: RANK.get(x, 9))
        m = min(len(la), len(lc))
        matched += m
        same += sum(1 for x, y in zip(la[:m], lc[:m]) if x == y)
        per_type[key[1]]["audit"] += len(la)
        per_type[key[1]]["checker"] += len(lc)
        per_type[key[1]]["matched"] += m
        a_rows += [(key[1], lv, j < m, lc[j] if j < m else None) for j, lv in enumerate(la)]
        c_rows += [(key[1], lv, j < m) for j, lv in enumerate(lc)]

    def strat(types, level=None):
        return _stats([(lv, ok, p) for t, lv, ok, p in a_rows if t in types and (level is None or lv == level)],
                      [(lv, ok) for t, lv, ok in c_rows if t in types and (level is None or lv == level)])

    n_a, n_c = sum(len(v) for v in a.values()), sum(len(v) for v in c.values())
    return {"audit_issues": n_a, "checker_issues": n_c, "matched": matched,
            "recall": None if n_a == 0 else round(matched / n_a, 3),
            "precision": None if n_c == 0 else round(matched / n_c, 3),
            "level_agreement": None if matched == 0 else round(same / matched, 3),
            "per_type": {t: v for t, v in per_type.items() if v["audit"] or v["checker"]},
            "by_type": {t: strat((t,)) for t in AGENT_TYPES if per_type[t]["audit"] or per_type[t]["checker"]},
            "by_level": {lv: strat(AGENT_TYPES, lv) for lv in LEVELS},
            "by_group": {"headline": strat(HEADLINE), "secondary": strat(SECONDARY), "other": strat(OTHER)},
            "groups": {"headline": list(HEADLINE), "secondary": list(SECONDARY), "other": list(OTHER)},
            "checker_llm_only": dict(llm_only), "checker_unmatchable": len(unknown)}
