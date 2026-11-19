"""Item-7a recall after the owner's adjudication (§11 #64-#65)."""

from __future__ import annotations

import csv
import json
import shutil

import pytest

from src.evaluation import adjudication_recall
from src.evaluation.dataset import ROOT
from src.evaluation.owner_inputs import OwnerInputError

EVAL = ROOT / "results" / "evaluations" / "R1"
ALLOC = ROOT / "results" / "allocations" / "R1"


@pytest.fixture
def ev(tmp_path):
    dst = tmp_path / "R1"
    shutil.copytree(EVAL, dst, ignore=shutil.ignore_patterns("allocator_digest", "claims_extraction", "owner_review"))
    return dst


def test_committed_figures():
    r = json.loads((EVAL / "owner_extraction" / "comparison_7a_adjudicated.json").read_text(encoding="utf-8"))
    p = r["primary_recall"]
    assert p["as_frozen"]["a_found_by_b"]["derived"] == "28/47"
    assert p["after_earlier_verdicts_row_71"]["a_found_by_b"]["derived"] == "28/46"
    assert p["after_item_2_r145_r120_r123"]["a_found_by_b"]["derived"] == "28/41"
    assert p["after_row_57_final"] == {"a_found_by_b": {"copied": "58/60", "derived": "27/40", "unclassified": "0/1"},
                                       "b_found_by_a": {"copied": "56/57", "derived": "29/49"}}
    d = r["descriptive_recall_after_adjudication"]
    assert d["recall"] == {"a_found_by_b": {"copied": "60/60", "derived": "37/40", "unclassified": "1/1"},
                           "b_found_by_a": {"copied": "57/57", "derived": "41/49"}}
    # §11 #67: excluded only where both sides encode a value and the values differ
    ex = [x for x in d["pair_figure_check"] if x["excluded_different_figures"]]
    assert [(x["owner"], x["assistant"]) for x in ex] == [("OWN-D08-r064", "R1-D08-01"), ("OWN-D08-r125", "R1-D08-35")]
    assert "restatement" in ex[1]["note"] and "note" not in ex[0]
    assert d["not_counted_found"] == {
        "owner": ["OWN-D08-r064", "OWN-D08-r125", "OWN-D18-r166"],
        "assistant": ["R1-D03-36", "R1-D08-01", "R1-D08-05", "R1-D08-22", "R1-D08-33", "R1-D08-35", "R1-D08-36",
                      "R1-D08-37"]}
    assert "OWN-D08-r064" in d["not_counted_found"]["owner"] and "R1-D08-01" in d["not_counted_found"]["assistant"]
    assert "OWN-D03-r057" in r["universe_and_duplicates"]["duplicates_left_out"]
    chk = r["universe_and_duplicates"]["override_checks"]["OWN-D18-r145"]
    assert (chk["requirement"], chk["pool_nurses"], chk["b_shortage_in_effect"]) == (42, 37, 3.5)
    assert r["universe_and_duplicates"]["out_of_universe"] == ["OWN-D08-r071", "OWN-D18-r145"]


def test_rerun_reproduces_the_committed_file(ev):
    out = adjudication_recall.main("R1", ev, ALLOC)
    assert out == json.loads((EVAL / "owner_extraction" / "comparison_7a_adjudicated.json").read_text(encoding="utf-8"))


def test_different_figures():
    from src.evaluation.adjudication_recall import different_figures
    assert not different_figures({"value": 0.3}, {"value": 0.30})
    assert different_figures({"value": None, "owner_raw": {"Value": "4"}}, {"value": 37})
    assert not different_figures({"value": 6}, {"value": None})                       # one side has no value
    assert not different_figures({"value": None, "owner_raw": {"Value": ""}}, {"value": None})


def _edit(ev, fn):
    path = ev / "owner_extraction" / adjudication_recall.OVERRIDES_FILE
    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    fn(rows)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=adjudication_recall.OVERRIDE_COLS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


@pytest.mark.parametrize("change,match", [
    (lambda rows: rows[1].update(original="OWN-D08-r082"), "differ"),            # r120 (CA 12) vs r082 (IM 27)
    (lambda rows: rows[0].update(claim_id="OWN-D18-r167"), "item-2 rule"),       # 3.5 is not requirement - pool
    (lambda rows: rows[0].update(action="drop"), "action"),
    (lambda rows: rows[0].update(claim_id="OWN-D99-r999"), "unknown claim"),
])
def test_bad_overrides_fail_loudly(ev, change, match):
    _edit(ev, change)
    with pytest.raises(OwnerInputError, match=match):
        adjudication_recall.main("R1", ev, ALLOC)
