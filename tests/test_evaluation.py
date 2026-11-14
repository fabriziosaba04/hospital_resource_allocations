"""Baselines and the deterministic audit on the frozen datasets (EVALUATION_PLAN.md §5, §7).

Runs into a temporary directory, so the committed results are not touched.
"""

from __future__ import annotations

import copy
import json
import random

import pytest

from src.environment.validator import validate
from src.evaluation.audit import audit_run, own_hard_constraints
from src.evaluation.dataset import load_dataset
from src.evaluation.metrics import compute_metrics, reversals
from src.evaluation.runner import run_baseline
from src.utils.constants import DEPARTMENTS

DATASETS = ["seed20261107", "seed20261108", "seed20261109", "seed20261107_stress"]


@pytest.fixture(scope="module")
def audited(tmp_path_factory):
    root = tmp_path_factory.mktemp("runs")
    out = {}
    for ds_id in DATASETS:
        ds = load_dataset(ds_id)
        for name in ("B0", "B1", "B2"):
            run_dir = run_baseline(name, ds, out_root=root)
            rec, days = audit_run(ds, run_dir)
            out[(name, ds_id)] = (ds, run_dir, days, compute_metrics(ds, days))
    return out


def test_gate_passes_for_every_baseline(audited):
    for key, (_, _, days, m) in audited.items():
        assert m["D"]["gate_passed"], key
        assert all(d["replay_ok"] for d in days), key


def test_b1_is_zero_on_a1_and_f1_inversions(audited):
    for ds_id in DATASETS:
        m = audited[("B1", ds_id)][3]
        assert m["A1"]["SV_B"] == 0, ds_id
        assert all(m["B2"][f"L{k}"]["count"] == 0 for k in (1, 2, 3)), ds_id


def test_b0_never_reallocates(audited):
    for ds_id in DATASETS:
        m = audited[("B0", ds_id)][3]
        assert m["E"]["beds"]["RS_total"] == 0 and m["E"]["nurses"]["RS_total"] == 0, ds_id


def test_path_component_never_negative(audited):
    for key, (_, _, days, m) in audited.items():
        for j in (1, 2, 3):
            assert m["A3"][f"tier{j}"]["min_daily_path"] >= 0, key


def test_nurse_net_gap_never_negative_at_tier3(audited):
    """The lexicographic floor at tier 3 is the unconstrained tier-3 maximum, so net tier-3 gaps are >= 0."""
    for key, (_, _, days, _) in audited.items():
        assert all(d["nurse_lex_floor_h"][3] == 0 and d["nurse_net_h"][3] >= 0 for d in days), key


def test_stress_variant_has_a_forced_cut_day_and_others_do_not(audited):
    shock_days = {ds_id: [d["day"] for d in audited[("B0", ds_id)][2] if d["shock_day"]] for ds_id in DATASETS}
    assert 23 in shock_days["seed20261107_stress"]
    assert all(shock_days[s] == [] for s in DATASETS if s != "seed20261107_stress")


def test_audit_flags_an_injected_eviction_as_critical(audited, tmp_path):
    ds, run_dir, days, _ = audited[("B1", "seed20261107")]
    lines = [json.loads(x) for x in (run_dir / "allocation_state.jsonl").read_text().splitlines()]
    # move one occupied bed from the department with most beds to another on day 7, nurses unchanged
    tgt = next(x for x in lines if x["day"] == 7 and x["source"] != "initial_rule")
    occ = days[6]["occupied"]
    src = max(DEPARTMENTS, key=lambda d: occ[d])
    dst = next(d for d in DEPARTMENTS if d != src and tgt["beds"][d] < ds.max_beds)
    tgt["beds"][src] = occ[src] - 1
    tgt["beds"][dst] += sum(days[6]["beds"].values()) - sum(tgt["beds"].values())
    bad = tmp_path / "bad"
    bad.mkdir()
    (bad / "allocation_state.jsonl").write_text("".join(json.dumps(x) + "\n" for x in lines))
    (bad / "bed_assignment_state.jsonl").write_text((run_dir / "bed_assignment_state.jsonl").read_text())
    _, days2 = audit_run(ds, bad)
    lv = {(i["level"], i["type"]) for i in days2[6]["issues"]}
    assert ("Critical", "hard_constraint_in_effect") in lv


def test_audit_hard_constraints_agree_with_validator():
    rng = random.Random(7)
    for _ in range(5000):
        pool_b, pool_n, cap = rng.randint(0, 60), rng.randint(0, 20), rng.randint(5, 20)
        occ = {d: rng.randint(0, cap) for d in DEPARTMENTS}
        beds = {d: rng.randint(-1, cap + 1) for d in DEPARTMENTS}
        nurses = {d: rng.randint(-1, 8) for d in DEPARTMENTS}
        if rng.random() < 0.5:                              # often conserve, so the eviction checks are reached
            beds[DEPARTMENTS[0]] += pool_b - sum(beds.values())
            nurses[DEPARTMENTS[0]] += pool_n - sum(nurses.values())
        env_ok = validate(beds, nurses, pool_b, pool_n, cap, occ) == []
        own_ok = own_hard_constraints(beds, nurses, pool_b, pool_n, cap, occ) == []
        assert env_ok == own_ok, (beds, nurses, pool_b, pool_n, cap, occ)


def test_reversal_matching_by_hand():
    assert reversals([3, 0, -3], 3) == 3                    # owner example 8: +3 on day 14, -3 on day 16
    assert reversals([3, 0, 0, 0, -3], 3) == 0              # outside the window
    assert reversals([2, -1, -1, 1], 3) == 2                # +2 matched by the two -1s; the final +1 finds nothing left
    assert reversals([0, 0, 0], 3) == 0


def test_checker_matching_by_hand():
    from src.evaluation.checker_matching import match
    audit = [{"day": 3, "type": "bed_displaced", "level": "Major"},
             {"day": 3, "type": "bed_displaced", "level": "Moderate"},
             {"day": 4, "type": "nurse_gap", "level": "Moderate"},
             {"day": 4, "type": "replay_mismatch", "level": "Critical"}]           # integrity: not matched
    checker = [{"day": 3, "type": "bed_displaced", "severity": "Major"},          # matches the Major one
               {"day": 4, "type": "nurse_gap", "severity": "Major"},              # matched, level differs
               {"day": 5, "type": "f1_inversion", "severity": "Moderate"},        # false positive
               {"day": 2, "type": "explanation_inaccuracy", "severity": "Minor"}]  # LLM-only
    m = match(audit, checker)
    assert (m["audit_issues"], m["checker_issues"], m["matched"]) == (3, 3, 2)
    assert m["recall"] == round(2 / 3, 3) and m["precision"] == round(2 / 3, 3) and m["level_agreement"] == 0.5
    assert m["checker_llm_only"] == {"explanation_inaccuracy": 1}


def test_checker_matching_is_stratified_by_type_level_and_group():
    """Owner decision §11 #37: headline (clinical and hard-constraint) types apart from Minor reversals."""
    from src.evaluation.checker_matching import HEADLINE, OTHER, SECONDARY, AGENT_TYPES, match
    assert sorted(HEADLINE + SECONDARY + OTHER) == sorted(AGENT_TYPES)
    assert set(OTHER) == {"rejected_submission", "f1_inversion"}
    audit = [{"day": 3, "type": "bed_displaced", "level": "Major"},
             {"day": 3, "type": "bed_displaced", "level": "Moderate"},
             {"day": 4, "type": "nurse_gap", "level": "Moderate"}]
    audit += [{"day": 2, "type": "beds_reversal", "level": "Minor"}] * 6
    checker = [{"day": 3, "type": "bed_displaced", "severity": "Major"},
               {"day": 4, "type": "nurse_gap", "severity": "Major"},
               {"day": 5, "type": "f1_inversion", "severity": "Moderate"}]
    checker += [{"day": 2, "type": "beds_reversal", "severity": "Minor"}] * 6
    m = match(audit, checker)
    assert m["recall"] == round(8 / 9, 3)                                # pooled looks good...
    h = m["by_group"]["headline"]
    assert (h["audit"], h["checker"], h["matched"], h["recall"], h["precision"], h["level_agreement"]) ==         (3, 2, 2, round(2 / 3, 3), 1.0, 0.5)                             # ...the headline group does not
    assert m["by_group"]["secondary"]["recall"] == 1.0
    assert m["by_group"]["other"] == {"audit": 0, "checker": 1, "matched": 0, "recall": None, "precision": 0.0,
                                      "level_agreement": None}
    assert m["by_type"]["bed_displaced"]["recall"] == 0.5
    mod = m["by_level"]["Moderate"]                                      # audit side: 2 Moderate, 1 matched
    assert (mod["audit"], mod["matched"], mod["recall"], mod["level_agreement"]) == (2, 1, 0.5, 0.0)
    assert m["by_level"]["Major"]["precision"] == 1.0                    # CHECKER side: 2 Major, both matched
    assert m["by_level"]["Critical"]["recall"] is None
