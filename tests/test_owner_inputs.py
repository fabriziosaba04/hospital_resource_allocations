"""Owner input tables (R50, §11 #62): the pipeline reads them, never rewrites them, and fails loudly on
unknown keys, missing keys, changed context or unknown causes."""

from __future__ import annotations

import csv
import shutil
from pathlib import Path

import pytest

from src.evaluation import claim_review, owner_claims
from src.evaluation.dataset import ROOT
from src.evaluation.owner_inputs import ADJ_FILE, CAUSES, UNVER_FILE, WRONG_FILE, OwnerInputError

EVAL = ROOT / "results" / "evaluations" / "R1"
ALLOC = ROOT / "results" / "allocations" / "R1"


@pytest.fixture
def ev(tmp_path):
    dst = tmp_path / "R1"
    shutil.copytree(EVAL, dst, ignore=shutil.ignore_patterns("allocator_digest", "claims_extraction"))
    return dst


def _tables(ev: Path) -> dict[str, Path]:
    return {"adj": ev / "owner_extraction" / ADJ_FILE, "wrong": ev / "owner_review" / WRONG_FILE,
            "unver": ev / "owner_review" / UNVER_FILE,
            "nonmech": ev / "owner_extraction" / "owner_verdicts_nonmech.csv"}


def _edit(path: Path, fn, enc="utf-8-sig") -> None:
    with open(path, encoding=enc, newline="") as f:
        r = csv.DictReader(f)
        cols, rows = r.fieldnames, list(r)
    fn(rows)
    with open(path, "w", encoding=enc, newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def _rows(path: Path) -> list[dict]:
    return list(csv.DictReader(open(path, encoding="utf-8-sig")))


def _run(ev: Path) -> None:
    owner_claims.main("R1", ev, ALLOC)
    claim_review.main("R1", ev)


def test_committed_tables_cover_the_generated_rows_and_prefill_only_the_three_owner_causes():
    adj = _rows(_tables(EVAL)["adj"])
    assert len(adj) == len(_rows(EVAL / "owner_extraction" / "adjudication_7a.csv")) == 43
    assert {(r["claim_id"], r["cause"]) for r in adj if r["cause"]} == \
        {("OWN-D08-r064", "rubric_ambiguity"), ("OWN-D08-r071", "owner_encoding"),
         ("OWN-D18-r166", "rubric_ambiguity")}
    assert len(_rows(_tables(EVAL)["wrong"])) == 75 and len(_rows(_tables(EVAL)["unver"])) == 26
    assert not any(r["owner_verdict"] or r["owner_comment"]
                   for t in ("wrong", "unver") for r in _rows(_tables(EVAL)[t]))


def test_owner_cells_survive_reruns_unchanged(ev):
    t = _tables(ev)
    note = 'checked, "quoted", comma; π → ok'

    def adj(rows):
        rows[0].update(cause="assistant_miss", comment=note, cause_set_by="owner")
        rows[-1].update(cause="owner_miss", comment="second", cause_set_by="owner")

    def rev(rows):
        rows[0].update(owner_verdict="agree", owner_comment=note)
        rows[-1].update(owner_verdict="disagree", owner_comment="x")

    def nm(rows):
        rows[0]["owner_comment"] = note
    _edit(t["adj"], adj)
    _edit(t["wrong"], rev)
    _edit(t["unver"], rev)
    _edit(t["nonmech"], nm, enc="utf-8")
    before = {k: p.read_bytes() for k, p in t.items()}
    for _ in range(2):
        _run(ev)
        assert {k: p.read_bytes() for k, p in t.items()} == before      # never rewritten
    a = _rows(ev / "owner_extraction" / "adjudication_7a.csv")
    assert (a[0]["cause"], a[0]["comment"], a[-1]["cause"]) == ("assistant_miss", note, "owner_miss")
    assert {r["cause"] for r in a if r["claim_id"] == "OWN-D08-r071"} == {"owner_encoding"}
    for name in ("review_7b_wrong.csv", "review_7c_unverifiable.csv"):
        r = _rows(ev / "owner_review" / name)
        assert (r[0]["owner_verdict"], r[0]["owner_comment"], r[-1]["owner_verdict"]) == ("agree", note, "disagree")
    nm_out = list(csv.DictReader(open(ev / "owner_extraction" / "non_mechanical_mappings.csv", encoding="utf-8")))
    assert nm_out[0]["owner_comment"] == note


@pytest.mark.parametrize("table,change,match", [
    ("adj", lambda rows: rows[1].update(cause="typo_cause"), "not in"),
    ("adj", lambda rows: rows[1].update(claim_id="OWN-D99-r999"), "unknown keys"),
    ("adj", lambda rows: rows.pop(), "missing"),
    ("adj", lambda rows: rows[1].update(text="edited text"), "column 'text'"),
    ("wrong", lambda rows: rows[0].update(computed="999"), "column 'computed'"),
    ("wrong", lambda rows: rows.append(dict(rows[0])), "duplicate key"),
    ("unver", lambda rows: rows[0].update(id="R1-D99-99"), "unknown keys"),
])
def test_bad_tables_fail_loudly_and_write_nothing(ev, table, change, match):
    t = _tables(ev)
    _edit(t[table], change)
    gen = [ev / "owner_extraction" / "adjudication_7a.csv", ev / "owner_review" / "review_7b_wrong.csv",
           ev / "owner_review" / "review_7c_unverifiable.csv"]
    target = gen[0] if table == "adj" else gen[1]
    before = target.read_bytes()
    with pytest.raises(OwnerInputError, match=match):
        _run(ev)
    assert target.read_bytes() == before


def test_number_formatting_is_not_a_context_change(ev):
    """A spreadsheet may rewrite 13 as 13.0; numbers are compared as numbers."""
    _edit(_tables(ev)["wrong"], lambda rows: rows[0].update(computed=rows[0]["computed"] + ".0"))
    claim_review.main("R1", ev)


def test_cause_list_is_the_fixed_one():
    assert CAUSES == ("owner_miss", "assistant_miss", "owner_encoding", "assistant_encoding", "rubric_ambiguity")
