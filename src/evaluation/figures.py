"""Static figures (figure plan, owner decision §11 #49; CLAUDE.md §10.K). Each figure answers one question.

    uv run python -m src.evaluation.figures <dataset_id> <run_id> [<run_id> ...] [--data-root PATH] [--out DIR]

All figures are drawn from the run records and the dataset only (the deterministic audit and the metrics
are recomputed, never taken from an agent), so they show actual decisions and invent no movements.

  F1 overflow_by_tier      Does the policy leave high-tier patients waiting more than the floor requires?
  F2 nurse_gap_by_tier     When nurses are rationed, is avoidable uncovered need concentrated at high tiers?
  F3 beds_over_time        How are beds moved between departments, and do they follow the patients?
  F4 nurses_vs_requirement Are nurses assigned where the N1 requirement is?
  F5 fairness_dispersion   Do patients of the same tier wait equally across departments?
  F6 checker_matching      How much of the deterministic audit did the CHECKER find, by stratum (counts)?

`daily_frame` is also the record-field check: it builds, per day and department, every field the figures
and the later animation need (beds, nurses, pools, in-bed and overflow by tier, N1 requirement, transfers),
and `check_frame` asserts the identities that tie them to the records.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from src.environment.nurses import requirement  # noqa: E402
from src.utils.constants import DEPARTMENTS, LEVELS  # noqa: E402

from .audit import load_records  # noqa: E402
from .dataset import ROOT, load_dataset  # noqa: E402
from .metrics import evaluate_run  # noqa: E402

# reference categorical palette (dataviz skill, references/palette.md, slots 1-4, light mode), fixed order
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
TIER = {1: "#86b6ef", 2: "#3987e5", 3: "#184f95"}            # one hue, light -> dark = low -> high tier
INK, INK2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
SHORT = {"internal_medicine": "Internal Medicine", "cardiology": "Cardiology", "neurology": "Neurology",
         "orthopedics": "Orthopedics"}


def _style(ax):
    ax.set_facecolor(SURFACE)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(INK2)
    ax.tick_params(colors=INK2, labelsize=8)
    ax.yaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


# --------------------------------------------------------------------------- record-field check
def daily_frame(ds, run_dir: Path) -> list[dict]:
    """One row per (day, department) with every field the figures and the animation need."""
    rec = load_records(run_dir)
    level = {}
    for t in range(1, ds.horizon + 1):
        for p in ds.present(t):
            level[p.patient_id] = p.complexity
    rows = []
    prev = rec.initial
    for t in range(1, ds.horizon + 1):
        a = rec.alloc[t]
        bl = rec.beds_final[t]["patients"]
        census = Counter((p.department, p.complexity) for p in ds.present(t))
        for d in DEPARTMENTS:
            in_bed = {k: 0 for k in LEVELS}
            over = {k: 0 for k in LEVELS}
            for pid, v in bl.items():
                if v["department"] == d:
                    (in_bed if v["status"] == "in_bed" else over)[level[pid]] += 1
            rows.append({"day": t, "department": d, "source": a["source"],
                         "beds": a["beds"][d], "nurses": a["nurses"][d],
                         "pool_beds": ds.pool_beds[t], "pool_nurses": ds.pool_nurses[t],
                         "in_bed": in_bed, "overflow": over,
                         "census": {k: census[(d, k)] for k in LEVELS},
                         "requirement": requirement(census[(d, 1)], census[(d, 2)], census[(d, 3)], ds.env),
                         "beds_change": a["beds"][d] - prev["beds"][d],
                         "nurses_change": a["nurses"][d] - prev["nurses"][d]})
        prev = a
    return rows


def check_frame(rows: list[dict], max_beds: int) -> list[str]:
    """Identities between the fields; an empty list means the records carry everything consistently."""
    probs = []
    for t in sorted({r["day"] for r in rows}):
        day = [r for r in rows if r["day"] == t]
        if sum(r["beds"] for r in day) != day[0]["pool_beds"]:
            probs.append(f"day {t}: beds do not sum to the pool")
        if sum(r["nurses"] for r in day) != day[0]["pool_nurses"]:
            probs.append(f"day {t}: nurses do not sum to the pool")
        for r in day:
            if any(r["in_bed"][k] + r["overflow"][k] != r["census"][k] for k in LEVELS):
                probs.append(f"day {t} {r['department']}: in-bed + overflow != census")
            if sum(r["in_bed"].values()) > r["beds"] or not 0 <= r["beds"] <= max_beds:
                probs.append(f"day {t} {r['department']}: occupancy above beds or beds out of bounds")
    return probs


# --------------------------------------------------------------------------- figures
def _grouped(ax, labels, series: dict[str, list[float]], fmt="{:g}"):
    n = len(series)
    w = 0.8 / n
    for i, (name, vals) in enumerate(series.items()):
        xs = [j + (i - (n - 1) / 2) * w for j in range(len(labels))]
        bars = ax.bar(xs, vals, width=w - 0.04, color=SERIES[i % len(SERIES)], label=name, zorder=2)
        for b, v in zip(bars, vals):
            ax.annotate(fmt.format(v), (b.get_x() + b.get_width() / 2, b.get_height()), ha="center",
                        va="bottom", fontsize=7, color=INK2, xytext=(0, 1), textcoords="offset points")
    ax.set_xticks(range(len(labels)), labels)
    ax.legend(frameon=False, fontsize=8, labelcolor=INK)


def fig_overflow_by_tier(metrics: dict[str, dict], out: Path):
    fig, ax = plt.subplots(figsize=(7, 3.6))
    _style(ax)
    labels = [f"Tier {j}" for j in (3, 2, 1)]
    _grouped(ax, labels, {n: [m["A3"][f"tier{j}"]["raw"] for j in (3, 2, 1)] for n, m in metrics.items()})
    any_m = next(iter(metrics.values()))
    for i, j in enumerate((3, 2, 1)):
        ax.hlines(any_m["A3"][f"tier{j}"]["floor"], i - 0.42, i + 0.42, colors=INK, linestyles="--", linewidth=1,
                  zorder=3, label="floor (policy-independent)" if i == 0 else None)
    ax.legend(frameon=False, fontsize=8, labelcolor=INK)
    ax.set_ylabel("overflow patient-days", color=INK2, fontsize=9)
    ax.set_title("F1. Does the policy leave high-tier patients waiting more than the floor requires?",
                 loc="left", fontsize=10, color=INK)
    fig.tight_layout()
    fig.savefig(out / "F1_overflow_by_tier.png", dpi=150, facecolor=SURFACE)
    plt.close(fig)


def fig_nurse_gap_by_tier(metrics: dict[str, dict], out: Path):
    fig, ax = plt.subplots(figsize=(7, 3.6))
    _style(ax)
    _grouped(ax, [f"Tier {j}" for j in (3, 2, 1)],
             {n: [m["A2"][f"tier{j}"]["SV_N"] for j in (3, 2, 1)] for n, m in metrics.items()}, fmt="{:.2f}")
    ax.set_ylabel("avoidable uncovered need\n(nurse-need units, summed over days)", color=INK2, fontsize=9)
    ax.set_title("F2. When nurses are rationed, how much uncovered need was avoidable, by tier?",
                 loc="left", fontsize=10, color=INK)
    fig.tight_layout()
    fig.savefig(out / "F2_nurse_gap_by_tier.png", dpi=150, facecolor=SURFACE)
    plt.close(fig)


def fig_beds_over_time(rows: list[dict], name: str, out: Path):
    fig, axes = plt.subplots(1, 4, figsize=(11, 3.2), sharey=True)
    days = sorted({r["day"] for r in rows})
    for ax, d in zip(axes, DEPARTMENTS):
        _style(ax)
        mine = [r for r in rows if r["department"] == d]
        bottom = [0] * len(days)
        for k in (3, 2, 1):
            vals = [r["in_bed"][k] for r in mine]
            ax.bar(days, vals, bottom=bottom, color=TIER[k], width=0.85, label=f"in bed, tier {k}", zorder=2,
                   edgecolor=SURFACE, linewidth=1)
            bottom = [b + v for b, v in zip(bottom, vals)]
        ov = [sum(r["overflow"].values()) for r in mine]
        ax.bar(days, ov, bottom=bottom, color="none", edgecolor=INK2, hatch="///", width=0.85, linewidth=0.6,
               label="overflow (no bed)", zorder=2)
        ax.step(days, [r["beds"] for r in mine], where="mid", color=SERIES[1], linewidth=2, label="beds allocated",
                zorder=3)
        ax.set_title(SHORT[d], fontsize=9, color=INK, loc="left")
        ax.set_xlabel("day", fontsize=8, color=INK2)
    axes[0].set_ylabel("patients / beds", fontsize=9, color=INK2)
    axes[-1].legend(frameon=False, fontsize=7, labelcolor=INK, loc="upper right")
    fig.suptitle(f"F3. {name}: are beds moved to where the patients are? (pool: "
                 + ", ".join(sorted({str(r['pool_beds']) for r in rows}, key=int)) + " beds)",
                 x=0.01, ha="left", fontsize=10, color=INK)
    fig.tight_layout()
    fig.savefig(out / f"F3_beds_over_time_{name}.png", dpi=150, facecolor=SURFACE)
    plt.close(fig)


def fig_nurses_vs_requirement(rows: list[dict], name: str, out: Path):
    fig, axes = plt.subplots(1, 4, figsize=(11, 3.0), sharey=True)
    days = sorted({r["day"] for r in rows})
    for ax, d in zip(axes, DEPARTMENTS):
        _style(ax)
        mine = [r for r in rows if r["department"] == d]
        ax.plot(days, [r["requirement"] for r in mine], color=INK2, linewidth=2, linestyle="--",
                label="N1 requirement", zorder=2)
        ax.plot(days, [r["nurses"] for r in mine], color=SERIES[0], linewidth=2, marker="o", markersize=4,
                label="nurses assigned", zorder=3)
        ax.set_title(SHORT[d], fontsize=9, color=INK, loc="left")
        ax.set_xlabel("day", fontsize=8, color=INK2)
    axes[0].set_ylabel("nurses", fontsize=9, color=INK2)
    axes[-1].legend(frameon=False, fontsize=7, labelcolor=INK)
    fig.suptitle(f"F4. {name}: are nurses assigned where the requirement is?", x=0.01, ha="left", fontsize=10,
                 color=INK)
    fig.tight_layout()
    fig.savefig(out / f"F4_nurses_vs_requirement_{name}.png", dpi=150, facecolor=SURFACE)
    plt.close(fig)


def fig_fairness_dispersion(metrics: dict[str, dict], out: Path):
    fig, ax = plt.subplots(figsize=(7, 3.6))
    _style(ax)
    _grouped(ax, [f"Tier {k}" for k in (3, 2, 1)],
             {n: [m["B1"][f"L{k}"]["dispersion_pp"] for k in (3, 2, 1)] for n, m in metrics.items()}, fmt="{:.1f}")
    ax.set_ylabel("overflow-rate dispersion\nacross departments (pp, max − min)", color=INK2, fontsize=9)
    ax.set_title("F5. Do patients of the same tier wait equally across departments?", loc="left", fontsize=10,
                 color=INK)
    fig.tight_layout()
    fig.savefig(out / "F5_fairness_dispersion.png", dpi=150, facecolor=SURFACE)
    plt.close(fig)


def fig_checker_matching(report: dict, name: str, out: Path):
    o = report["checker_overall"]
    strata = [("Headline", o["by_group"]["headline"]),
              ("Rejected submissions", o["by_group"]["headline_rejected_submission"]),
              ("Secondary", o["by_group"]["secondary"])]
    strata += [(t, v) for t, v in o["by_type"].items()]
    fig, ax = plt.subplots(figsize=(7, 0.45 * len(strata) + 1.2))
    _style(ax)
    ax.xaxis.grid(True, color=GRID)
    ax.yaxis.grid(False)
    ys = list(range(len(strata)))[::-1]
    for y, (lab, v) in zip(ys, strata):
        ax.barh(y, v["audit"], color=GRID, height=0.6, zorder=2)
        ax.barh(y, v["matched"], color=SERIES[0], height=0.6, zorder=3)
        ax.annotate(f"{v['matched']}/{v['audit']} found · {v['checker']} reported", (max(v["audit"], 0.1), y),
                    xytext=(4, 0), textcoords="offset points", va="center", fontsize=8, color=INK2)
    ax.set_yticks(ys, [s[0] for s in strata], fontsize=8)
    ax.set_xlabel("audit issues (grey) and those the CHECKER matched (blue)", fontsize=8, color=INK2)
    ax.set_title(f"F6. {name}: how much of the audit did the CHECKER find?", loc="left", fontsize=10, color=INK)
    fig.tight_layout()
    fig.savefig(out / f"F6_checker_matching_{name}.png", dpi=150, facecolor=SURFACE)
    plt.close(fig)


def build(dataset_id: str, runs: list[str], data_root: Path = ROOT, out: Path | None = None,
          results_root: Path = ROOT / "results") -> dict:
    import tempfile
    ds = load_dataset(dataset_id, data_root)
    out = out or results_root / "visualizations" / dataset_id
    out.mkdir(parents=True, exist_ok=True)
    metrics, problems = {}, {}
    with tempfile.TemporaryDirectory() as tmp:
        for r in runs:
            rd = results_root / "allocations" / r
            metrics[r] = evaluate_run(ds, rd, out_root=Path(tmp))        # recomputed, written to a temp dir only
            rows = daily_frame(ds, rd)
            problems[r] = check_frame(rows, ds.max_beds)
            fig_beds_over_time(rows, r, out)
            fig_nurses_vs_requirement(rows, r, out)
            rep = results_root / "evaluations" / r / "run_report.json"
            if rep.exists():
                fig_checker_matching(json.loads(rep.read_text(encoding="utf-8")), r, out)
    fig_overflow_by_tier(metrics, out)
    fig_nurse_gap_by_tier(metrics, out)
    fig_fairness_dispersion(metrics, out)
    return {"out": str(out), "record_field_problems": problems}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("dataset")
    ap.add_argument("runs", nargs="+")
    ap.add_argument("--data-root", default=str(ROOT))
    ap.add_argument("--out")
    a = ap.parse_args()
    print(json.dumps(build(a.dataset, a.runs, Path(a.data_root), Path(a.out) if a.out else None), indent=2))
