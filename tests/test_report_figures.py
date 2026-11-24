"""Phase 3 figures and animations against the tables and the records (Decisions Log #136-#137).

Every builder returns the values it drew, read back from the matplotlib artists. They are compared here with
the analysis-table cells (F1, F2, F5, F6) and with allocation_state.jsonl read directly (F3, F4, animations), so
the figures cannot drift from ANALYSIS.md or from the records.
"""

from __future__ import annotations

import json

import pytest
from PIL import Image

from src.evaluation.analysis import AGENT_RUNS, PRIMARY, load_numbers, slug
from src.evaluation.dataset import ROOT
from src.evaluation.figure_style import POLICY, palette_report
from src.evaluation.report_figures import (POLICIES, _frames, common_limits, fig1, fig2, fig3, fig4, fig5, fig6,
                                           net_balances)
from src.utils.constants import DEPARTMENTS

ALL, ZOOM = "all policies", "zoom: without B0 (its own scale)"


def _cell(n, table, row, col):
    return n[f"{table}.{slug(row)}.{slug(col)}"]["value"]


def _final_alloc(name: str) -> dict[int, dict]:
    out, init = {}, None
    for line in (ROOT / "results" / "allocations" / name / "allocation_state.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            x = json.loads(line)
            if x["source"] == "initial_rule":
                init = x
            else:
                out[x["day"]] = x
    return out, init


def test_policy_palette_passes_the_dataviz_floors():
    r = palette_report()
    assert r["worst_normal"]["normal"] >= 15 and r["worst_cvd"]["cvd"] >= 8, r
    assert len(set(POLICY.values())) == len(POLICY)


def test_bar_figures_plot_the_table_cells(tmp_path):
    n = load_numbers()
    d1 = fig1(n, tmp_path)
    for j in (3, 2):
        for p in POLICIES:
            assert d1[(ALL, f"Tier {j}", p)] == float(_cell(n, "main_headline", f"A3 tier {j} raw", p))
        assert d1[(ALL, f"Tier {j}", "floor")] == float(_cell(n, "main_headline", f"A3 tier {j} raw", "floor"))
        assert (ZOOM, f"Tier {j}", "B0") not in d1
    d2 = fig2(n, tmp_path)
    for j in (3, 2, 1):
        for p in POLICIES:
            v = float(_cell(n, "main_headline", f"A2 SV_N tier {j}", p))
            assert d2[(ALL, f"Tier {j}", p)] == pytest.approx(v)
            if p != "B0":
                assert d2[(ZOOM, f"Tier {j}", p)] == pytest.approx(v)       # the zoom keeps the small values
    d5 = fig5(n, tmp_path)
    for k in (3, 2, 1):
        for p in POLICIES:
            assert d5[(ALL, f"Level {k}", p)] == pytest.approx(float(_cell(n, "main_secondary",
                                                                           f"B1 dispersion L{k} (pp)", p)))
    d6 = fig6(n, tmp_path)
    for run in AGENT_RUNS + ["STRESS1"]:
        for row in ("headline group", "secondary group", "type beds_reversal"):
            m, a = map(int, _cell(n, f"checker_{run}", row, "recall").split("/"))
            assert d6[(run, row)] == (m, a)
    assert sorted(p.name for p in tmp_path.glob("*.png")) == [
        "F1_overflow_by_tier.png", "F2_nurse_gap_by_tier.png", "F5_fairness_dispersion.png",
        "F6_checker_vs_audit.png"]


def test_over_time_figures_plot_the_recorded_allocations(tmp_path):
    ds, frames = _frames()
    d3, d4 = fig3(frames, ds.max_beds, tmp_path), fig4(frames, tmp_path)
    for p in POLICIES:
        final, _ = _final_alloc(p if p in AGENT_RUNS else f"{p}-{PRIMARY}")
        for t in (1, 12, 23, 30):
            for d in DEPARTMENTS:
                assert d3[(p, d, t)] == final[t]["beds"][d], (p, d, t)
                assert d4[(p, d, t)] == final[t]["nurses"][d], (p, d, t)


def test_animation_balances_and_files():
    limits = common_limits()
    for run in AGENT_RUNS:
        final, init = _final_alloc(run)
        nb = net_balances(run)
        assert sorted(nb) == list(range(1, 31))
        for t in (1, 15, 30):
            for res in ("beds", "nurses"):
                for d in DEPARTMENTS:
                    v = nb[t][res][d]
                    assert v == final[t][res][d] - init[res][d]
                    assert abs(v) < limits[res]
        gif = ROOT / "results" / "figures" / "animations" / f"{run}_net_balances.gif"
        assert gif.stat().st_size < 5 * 1024 * 1024
        with Image.open(gif) as im:
            assert im.n_frames == 30
