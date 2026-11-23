"""Figure plan and record-field check (owner decision §11 #49): figure code runs on the baselines and DRY2,
and the records carry every field the figures and the animation need."""

from __future__ import annotations

from src.evaluation.dataset import ROOT, load_dataset
from src.evaluation.figures import build, check_frame, daily_frame

DEV = ROOT / "results" / "development"                   # moved here in the clean-up (2026-11-23)
FIX = DEV / "dry_runs" / "HARD10_fixture"
RUNS = ["B0-HARD10", "B1-HARD10", "B2-HARD10", "DRY2-HARD10"]
FIELDS = {"day", "department", "source", "beds", "nurses", "pool_beds", "pool_nurses", "in_bed", "overflow",
          "census", "requirement", "beds_change", "nurses_change"}


def test_records_carry_every_field_for_figures_and_animation():
    ds = load_dataset("HARD10", FIX)
    for r in RUNS:
        rows = daily_frame(ds, DEV / "allocations" / r)
        assert len(rows) == ds.horizon * 4
        assert all(set(x) == FIELDS for x in rows)
        assert check_frame(rows, ds.max_beds) == []
        # transfers are derived from consecutive allocations, so the animation shows only recorded moves
        for d in {x["department"] for x in rows}:
            mine = [x for x in rows if x["department"] == d]
            assert all(b["beds"] - a["beds"] == b["beds_change"] for a, b in zip(mine, mine[1:]))


def test_figures_build_on_baselines_and_dry2(tmp_path):
    out = build("HARD10", RUNS, data_root=FIX, out=tmp_path, results_root=DEV)
    assert all(not p for p in out["record_field_problems"].values())
    names = {p.name for p in tmp_path.glob("*.png")}
    assert {"F1_overflow_by_tier.png", "F2_nurse_gap_by_tier.png", "F5_fairness_dispersion.png",
            "F6_checker_matching_DRY2-HARD10.png"} <= names
    assert {f"F3_beds_over_time_{r}.png" for r in RUNS} <= names
    assert {f"F4_nurses_vs_requirement_{r}.png" for r in RUNS} <= names
