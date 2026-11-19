"""Display-only side-by-side view of the item-7a unmatched claims (owner, 2026-11-19)."""

from __future__ import annotations

import csv
import shutil

from src.evaluation import adjudication_view
from src.evaluation.adjudication_view import BANNER, rule
from src.evaluation.dataset import ROOT

EVAL = ROOT / "results" / "evaluations" / "R1"
ALLOC = ROOT / "results" / "allocations" / "R1"


def test_pairing_rule():
    assert rule("7 level 2 in IM", "(e.g. 7 level-2 in IM")[0] == "P1 contains"
    assert rule("nurses reduced by 4", "nurse pool reduced by 4 (37") == ("P2 number", "by 4")
    assert rule("3-nurse hospital-wide shortage", "it has 3 spare beds above census") is None
    assert rule("orthopedics only 1", "covering its level 1 need fully") is None


def test_view_covers_every_unmatched_claim_once_and_is_marked_display_only(tmp_path):
    ev = tmp_path / "R1"
    shutil.copytree(EVAL, ev, ignore=shutil.ignore_patterns("allocator_digest", "claims_extraction", "owner_review"))
    before = {p.name: p.read_bytes() for p in (ev / "owner_extraction").iterdir()
              if p.name not in ("adjudication_pairs_view.csv", "adjudication_pairs_summary.json")}
    s = adjudication_view.main("R1", ev, ALLOC)
    assert s["counts"] == {"pairs": 15, "owner_singles": 7, "assistant_singles": 6, "owner_only_total": 22,
                           "assistant_only_total": 21}
    lines = (ev / "owner_extraction" / "adjudication_pairs_view.csv").read_text(encoding="utf-8-sig").splitlines()
    assert lines[0] == BANNER
    rows = list(csv.DictReader(lines[1:]))
    # the same unmatched claims as the committed adjudication_7a.csv, each exactly once
    adj = list(csv.DictReader(open(EVAL / "owner_extraction" / "adjudication_7a.csv", encoding="utf-8-sig")))
    ids_o = [r["owner_id"] for r in rows if r["owner_id"]]
    ids_a = [r["assistant_id"] for r in rows if r["assistant_id"]]
    assert sorted(ids_o) == sorted(r["claim_id"] for r in adj if r["side"] == "owner_only")
    assert sorted(ids_a) == sorted(r["claim_id"] for r in adj if r["side"] == "assistant_only")
    assert len(set(ids_o)) == len(ids_o) and len(set(ids_a)) == len(ids_a)
    pairs = {(r["owner_id"], r["assistant_id"]) for r in rows if r["kind"] == "pair"}
    assert {("OWN-D03-r058", "R1-D03-34"), ("OWN-D18-r151", "R1-D18-14"), ("OWN-D08-r064", "R1-D08-01")} <= pairs
    # writes only its two display files
    assert {p.name: p.read_bytes() for p in (ev / "owner_extraction").iterdir() if p.name in before} == before
