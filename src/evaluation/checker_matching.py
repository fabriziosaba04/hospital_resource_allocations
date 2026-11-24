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
  - by group (owner decision §11 #43): HEADLINE (clinical and hard-constraint types), with rejected_submission
    always a separate row (`headline_rejected_submission`), never folded into the headline group's figures,
    because it is visible in the records and close to trivial to detect; SECONDARY (reversals, reallocations
    without effect, F1 inversions).
Descriptive date-shift count (owner decision §11 #45): among issues left unmatched by the primary rule, pairs
with the same type, a day differing by 1 or 2, and the same departments (the audit issue's departments all
named in the CHECKER issue's text; types without departments compare on type only). Reported next to the
primary figures, never instead of them.
Within a (day, type) key the pairing is the approved one (Log #82): both sides sorted most severe first, the
first min(n_audit, n_checker) of each paired in order. So when the CHECKER reports fewer issues than the
audit under a key, the matched audit issues are taken to be its most severe ones (stated with the results).
"""

from __future__ import annotations

import re
from collections import defaultdict

AGENT_TYPES = ("hard_constraint_in_effect", "rejected_submission", "allocator_failure_day", "bed_displaced",
               "bed_empty", "bed_shock_cut", "nurse_gap", "f1_inversion", "beds_reversal", "nurses_reversal",
               "reallocation_without_effect")
LLM_ONLY = ("explanation_inaccuracy", "information_leak", "inconsistency", "other")
RANK = {"Critical": 0, "Major": 1, "Moderate": 2, "Minor": 3}


HEADLINE = ("hard_constraint_in_effect", "bed_displaced", "bed_empty", "bed_shock_cut", "nurse_gap",
            "allocator_failure_day")
HEADLINE_SEPARATE = ("rejected_submission",)          # headline type, own row, never folded into HEADLINE
SECONDARY = ("beds_reversal", "nurses_reversal", "reallocation_without_effect", "f1_inversion")
OTHER = tuple(t for t in AGENT_TYPES if t not in HEADLINE + HEADLINE_SEPARATE + SECONDARY)
# department names as the CHECKER may write them: (case-insensitive patterns, case-sensitive abbreviations)
DEPT_ALIASES = {"internal_medicine": ([r"internal[ _]medicine"], [r"\bIM\b"]),
                "cardiology": ([r"cardiology"], []),
                "neurology": ([r"neurology"], []),
                "orthopedics": ([r"orthop(a)?edics"], [])}
TEXT_FIELDS = ("what_happened", "what_should_have_happened", "why_incorrect", "impact")


def _audit_departments(issue: dict) -> set[str]:
    d = issue.get("detail")
    if not isinstance(d, dict):
        return set()
    return {d[k] for k in ("department", "unserved_department", "served_department") if d.get(k)}


def _checker_departments(issue: dict) -> set[str]:
    text = " ".join(str(issue.get(k, "")) for k in TEXT_FIELDS)
    out = set()
    for dep, (ci, cs) in DEPT_ALIASES.items():
        if any(re.search(pt, text, re.IGNORECASE) for pt in ci) or any(re.search(pt, text) for pt in cs):
            out.add(dep)
    return out


def date_shift_matches(audit_issues: list[dict], checker_issues: list[dict], max_shift: int = 2) -> list[dict]:
    """Descriptive only: pairs among the issues the primary (day, type) rule leaves unmatched."""
    a, c = defaultdict(list), defaultdict(list)
    for i in audit_issues:
        if i["type"] in AGENT_TYPES:
            a[(int(i["day"]), i["type"])].append(i)
    for i in checker_issues:
        try:
            if i.get("type") in AGENT_TYPES:
                c[(int(i["day"]), i["type"])].append(i)
        except (KeyError, TypeError, ValueError):
            pass
    left_a, left_c = [], []
    for key in set(a) | set(c):
        m = min(len(a.get(key, [])), len(c.get(key, [])))
        left_a += a.get(key, [])[m:]
        left_c += c.get(key, [])[m:]
    used, out = set(), []
    for ai in sorted(left_a, key=lambda x: (x["day"], x["type"])):
        need = _audit_departments(ai)
        for j, ci in sorted(enumerate(left_c), key=lambda x: (abs(int(x[1]["day"]) - ai["day"]), x[0])):
            if j in used or ci["type"] != ai["type"]:
                continue
            if not 1 <= abs(int(ci["day"]) - int(ai["day"])) <= max_shift:
                continue
            if need and not need <= _checker_departments(ci):
                continue
            used.add(j)
            out.append({"type": ai["type"], "audit_day": int(ai["day"]), "checker_day": int(ci["day"]),
                        "departments": sorted(need)})
            break
    return out
LEVELS = ("Critical", "Major", "Moderate", "Minor")


def _ratio(num: int, den: int):
    return None if den == 0 else round(num / den, 3)


def _stats(audit_side: list[tuple], checker_side: list[tuple], counts: bool = False) -> dict:
    """audit_side: (level, matched, checker_level or None); checker_side: (level, matched). With `counts`, the
    numerators behind the ratios are added (`checker_matched`, `level_same`), so every figure can be written as
    matched/total (EVALUATION_PLAN.md §4 item 6; Log #129); the default output is unchanged."""
    m_a = [x for x in audit_side if x[1]]
    m_c = sum(1 for x in checker_side if x[1])
    same = sum(1 for x in m_a if x[0] == x[2])
    out = {"audit": len(audit_side), "checker": len(checker_side), "matched": len(m_a),
           "recall": _ratio(len(m_a), len(audit_side)),
           "precision": _ratio(m_c, len(checker_side)),
           "level_agreement": _ratio(same, len(m_a))}
    if counts:
        out.update(checker_matched=m_c, level_same=same)
    return out


def match(audit_issues: list[dict], checker_issues: list[dict], counts: bool = False) -> dict:
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
                      [(lv, ok) for t, lv, ok in c_rows if t in types and (level is None or lv == level)], counts)

    n_a, n_c = sum(len(v) for v in a.values()), sum(len(v) for v in c.values())
    res = {"audit_issues": n_a, "checker_issues": n_c, "matched": matched,
            "recall": None if n_a == 0 else round(matched / n_a, 3),
            "precision": None if n_c == 0 else round(matched / n_c, 3),
            "level_agreement": None if matched == 0 else round(same / matched, 3),
            "per_type": {t: v for t, v in per_type.items() if v["audit"] or v["checker"]},
            "by_type": {t: strat((t,)) for t in AGENT_TYPES
                        if counts or per_type[t]["audit"] or per_type[t]["checker"]},
            "by_level": {lv: strat(AGENT_TYPES, lv) for lv in LEVELS},
            "by_group": {"headline": strat(HEADLINE), "headline_rejected_submission": strat(HEADLINE_SEPARATE),
                         "secondary": strat(SECONDARY)},
            "groups": {"headline": list(HEADLINE), "headline_rejected_submission": list(HEADLINE_SEPARATE),
                       "secondary": list(SECONDARY)},
            "date_shift_matches": date_shift_matches(audit_issues, checker_issues),
            "checker_llm_only": dict(llm_only), "checker_unmatchable": len(unknown)}
    if counts:                                    # every type listed, and the numerator of level agreement
        res["level_same"] = same
    return res
