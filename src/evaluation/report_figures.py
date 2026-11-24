"""Phase 3 figures F1-F6 and the per-run animations (Decisions Log #136-#137).

F1, F2, F5 and F6 read the analysis tables in results/analysis/ (`analysis.load_numbers`), so they cannot drift
from ANALYSIS.md. F3, F4 and the animations read the same committed run records the tables come from
(`figures.daily_frame`, `audit.load_records`). Every builder returns the values it drew, read back from the
matplotlib artists, so tests/test_report_figures.py can compare them with the table cells and the records.
Colours: `figure_style` (one fixed colour per policy).
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.animation import FuncAnimation, PillowWriter  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.ticker import MaxNLocator  # noqa: E402
import matplotlib.patheffects as pe  # noqa: E402

from src.utils.constants import DEPARTMENTS  # noqa: E402
from src.utils.paths import guard_write, long_path  # noqa: E402

from .analysis import AGENT_RUNS, BASELINES, PRIMARY, load_numbers, slug  # noqa: E402
from .audit import load_records  # noqa: E402
from .dataset import ROOT, load_dataset  # noqa: E402
from .figure_style import DEPT, DPI, GRID, HATCH, INK, INK2, POLICY, SURFACE  # noqa: E402
from .figures import SHORT, daily_frame  # noqa: E402

POLICIES = AGENT_RUNS + BASELINES
LIGHTNESS = {"R1": 0, "R2": 1, "R3": 2, "B0": 0, "B1": 1, "B2": 2}   # within each row of F3/F4
WIDTHS = (4.2, 2.6, 1.3)                                              # lightest drawn first and widest
OUTLINED = {"R3", "B2"}                                               # contrast < 3:1 on the surface
FIG_DIR = ROOT / "results" / "figures"


def _num(v: str) -> float:
    return float(v)


def _cell(numbers: dict, table: str, row: str, col: str) -> str:
    return numbers[f"{table}.{slug(row)}.{slug(col)}"]["value"]


def _style(ax):
    ax.set_facecolor(SURFACE)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(INK2)
    ax.tick_params(colors=INK2, labelsize=7.5)
    ax.yaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def _save(fig, path: Path) -> Path:
    path = guard_write(Path(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(long_path(path), dpi=DPI, facecolor=SURFACE)
    plt.close(fig)
    return path


def _policy_legend(fig, extra=(), ncol=7, y=0.0):
    handles = [Patch(facecolor=POLICY[p], hatch=HATCH[p], edgecolor=INK2, linewidth=0.5, label=p) for p in POLICIES]
    fig.legend(handles=handles + list(extra), loc="lower center", ncol=ncol, frameon=False, fontsize=7.5,
               bbox_to_anchor=(0.5, y), labelcolor=INK)


# --------------------------------------------------------------------------- grouped bars with a zoom panel
def _grouped_two_panels(groups: list[tuple[str, dict, float | None]], title: str, ylabel: str, path: Path,
                        fmt: str = "{:g}") -> dict:
    """groups: (label, {policy: value}, floor or None). Left panel: every policy; right panel: without B0 on its
    own scale, so differences between the runs and B1/B2 stay visible."""
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.9), gridspec_kw={"width_ratios": [1, 1]})
    drawn = {}
    for ax, pols, sub in ((axes[0], POLICIES, "all policies"),
                          (axes[1], [p for p in POLICIES if p != "B0"], "zoom: without B0 (its own scale)")):
        _style(ax)
        n, w = len(pols), 0.8 / len(pols)
        top = max([v for _, vals, _ in groups for p, v in vals.items() if p in pols] + [0])
        for gi, (lab, vals, floor) in enumerate(groups):
            for i, p in enumerate(pols):
                x = gi + (i - (n - 1) / 2) * w
                bar = ax.bar(x, vals[p], width=w * 0.9, color=POLICY[p], hatch=HATCH[p], edgecolor=INK2,
                             linewidth=0.5, zorder=2)[0]
                drawn[(sub, lab, p)] = bar.get_height()
                ax.annotate(fmt.format(vals[p]), (x, vals[p]), ha="center", va="bottom", fontsize=6,
                            color=INK2, xytext=(0, 1.5), textcoords="offset points", rotation=90 if n > 5 else 0)
            if floor is not None:
                ax.hlines(floor, gi - 0.44, gi + 0.44, colors=INK, linestyles="--", linewidth=1.2, zorder=3)
                drawn[(sub, lab, "floor")] = floor
        ax.set_xticks(range(len(groups)), [g[0] if g[2] is None else f"{g[0]}\nfloor = {g[2]:g}" for g in groups],
                      fontsize=8)                             # a floor of 0 sits on the axis: say it in text
        ax.set_ylim(0, top * 1.28 if top > 0 else 1)
        ax.set_title(sub, fontsize=8.5, color=INK2, loc="left")
    axes[0].set_ylabel(ylabel, fontsize=8.5, color=INK2)
    extra = [Line2D([], [], color=INK, linestyle="--", linewidth=1.2, label="floor")] \
        if any(g[2] is not None for g in groups) else []
    _policy_legend(fig, extra, ncol=7)
    fig.suptitle(title, x=0.01, ha="left", fontsize=10, color=INK)
    fig.tight_layout(rect=(0, 0.07, 1, 0.95))
    _save(fig, path)
    return drawn


def fig1(numbers: dict, out: Path = FIG_DIR) -> dict:
    groups = []
    for j in (3, 2):
        row = f"A3 tier {j} raw"
        groups.append((f"Tier {j}", {p: _num(_cell(numbers, "main_headline", row, p)) for p in POLICIES},
                       _num(_cell(numbers, "main_headline", row, "floor"))))
    same = all(groups[i][1][r] == groups[i][1]["B1"] for i in range(len(groups)) for r in AGENT_RUNS)
    title = ("F1. Overflow of tiers 3 and 2 (A3 raw): " + ("R1–R3 equal B1 at every tier" if same
             else "R1–R3 differ from B1") + "; B0 is far above")
    return _grouped_two_panels(groups, title, "overflow patient-days", out / "F1_overflow_by_tier.png")


def fig2(numbers: dict, out: Path = FIG_DIR) -> dict:
    groups = [(f"Tier {j}", {p: _num(_cell(numbers, "main_headline", f"A2 SV_N tier {j}", p)) for p in POLICIES},
               _num(_cell(numbers, "main_headline", f"A2 SV_N tier {j}", "floor"))) for j in (3, 2, 1)]
    better = all(_cell(numbers, "main_lex", "A2 (tier 3, 2, 1) vs B1", r) == "better" for r in AGENT_RUNS)
    title = ("F2. Avoidable nurse gap SV_N (A2): " + ("each run is lower than B1, read lexicographically "
             "(tier 3, then tier 2)" if better else "runs against B1, read lexicographically"))
    return _grouped_two_panels(groups, title, "need units over the horizon", out / "F2_nurse_gap_by_tier.png",
                               fmt="{:.2f}")


def fig5(numbers: dict, out: Path = FIG_DIR) -> dict:
    groups = [(f"Level {k}", {p: _num(_cell(numbers, "main_secondary", f"B1 dispersion L{k} (pp)", p))
                              for p in POLICIES}, None) for k in (3, 2, 1)]
    rest = max(v for _, vals, _ in groups for p, v in vals.items() if p != "B0")
    title = f"F5. Overflow-rate dispersion across departments (secondary): B0 far above; the others within {rest:g} pp"
    return _grouped_two_panels(groups, title, "max − min overflow rate (pp)", out / "F5_fairness_dispersion.png",
                               fmt="{:.2f}")


# --------------------------------------------------------------------------- F3, F4: over time, from records
def _frames(dataset_id: str = PRIMARY) -> tuple[object, dict[str, list[dict]]]:
    ds = load_dataset(dataset_id)
    rows = {}
    for p in POLICIES:
        name = p if p in AGENT_RUNS else f"{p}-{dataset_id}"
        rows[p] = daily_frame(ds, long_path(ROOT / "results" / "allocations" / name))
    return ds, rows


def _over_time(frames: dict, value: str, ref: str, ref_label: str, ylabel: str, title: str, path: Path,
               cap: int | None = None) -> dict:
    fig, axes = plt.subplots(2, 4, figsize=(12, 5.6), sharex=True, sharey=True)
    drawn = {}
    for ri, (group, pols) in enumerate((("agent runs", AGENT_RUNS), ("baselines", BASELINES))):
        for ci, d in enumerate(DEPARTMENTS):
            ax = axes[ri][ci]
            _style(ax)
            ref_rows = [r for r in frames[pols[0]] if r["department"] == d]
            days = [r["day"] for r in ref_rows]
            ax.plot(days, [r[ref] if ref != "census" else sum(r["census"].values()) for r in ref_rows],
                    color=INK, linestyle="--", linewidth=1.6, zorder=4)
            if cap is not None:
                ax.axhline(cap, color=INK2, linestyle=":", linewidth=1, zorder=1)
            for k, p in enumerate(sorted(pols, key=lambda q: -LIGHTNESS[q])):   # lightest (widest) first
                mine = [r for r in frames[p] if r["department"] == d]
                line = ax.step([r["day"] for r in mine], [r[value] for r in mine], where="mid", color=POLICY[p],
                               linewidth=WIDTHS[k], zorder=3 + k)[0]
                if p in OUTLINED:
                    line.set_path_effects([pe.Stroke(linewidth=WIDTHS[k] + 1.2, foreground=INK2), pe.Normal()])
                for x, y in zip(*line.get_data()):
                    drawn[(p, d, int(x))] = float(y)
            ax.yaxis.set_major_locator(MaxNLocator(integer=True))
            if ri == 0:
                ax.set_title(SHORT[d], fontsize=9, color=INK, loc="left")
            if ci == 0:
                ax.set_ylabel(f"{group}\n{ylabel}", fontsize=8.5, color=INK2)
            if ri == 1:
                ax.set_xlabel("day", fontsize=8, color=INK2)
    extra = [Line2D([], [], color=INK, linestyle="--", linewidth=1.6, label=ref_label)]
    if cap is not None:
        extra.append(Line2D([], [], color=INK2, linestyle=":", linewidth=1, label="cap per department"))
    handles = [Line2D([], [], color=POLICY[p], linewidth=2, label=p,
                      path_effects=[pe.Stroke(linewidth=3.2, foreground=INK2), pe.Normal()] if p in OUTLINED else None)
               for p in POLICIES] + extra
    fig.legend(handles=handles, loc="lower center", ncol=len(handles), frameon=False, fontsize=7.5, labelcolor=INK)
    fig.suptitle(title, x=0.01, ha="left", fontsize=10, color=INK)
    fig.tight_layout(rect=(0, 0.05, 1, 0.96))
    _save(fig, path)
    return drawn


def fig3(frames: dict, max_beds: int, out: Path = FIG_DIR) -> dict:
    return _over_time(frames, "beds", "census", "patients present (census)", "beds allocated",
                      "F3. Beds allocated per department over time, against the patients present",
                      out / "F3_beds_over_time.png", cap=max_beds)


def fig4(frames: dict, out: Path = FIG_DIR) -> dict:
    return _over_time(frames, "nurses", "requirement", "N1 requirement", "nurses assigned",
                      "F4. Nurses assigned per department over time, against the N1 requirement",
                      out / "F4_nurses_vs_requirement.png")


# --------------------------------------------------------------------------- F6: CHECKER against the audit
F6_ROWS = [("headline group", "headline group"), ("rejected_submission (own row)", "rejected submissions"),
           ("secondary group", "secondary group"), ("type nurse_gap", "nurse_gap"),
           ("type beds_reversal", "beds_reversal"), ("type nurses_reversal", "nurses_reversal"),
           ("type reallocation_without_effect", "reallocation without effect")]


def fig6(numbers: dict, out: Path = FIG_DIR) -> dict:
    panels = [(r, f"checker_{r}", POLICY[r], r) for r in AGENT_RUNS] + \
             [("STRESS1", "checker_STRESS1", "#5d5c58", "STRESS1 (descriptive, separate probe)")]
    fig, axes = plt.subplots(1, 4, figsize=(12.5, 3.6), sharey=True, sharex=True)
    drawn = {}
    xmax = max(int(_cell(numbers, table, row, "recall").split("/")[1]) for _, table, _, _ in panels
               for row, _ in F6_ROWS)
    for ax, (run, table, colour, name) in zip(axes, panels):
        _style(ax)
        ax.yaxis.grid(False)
        ax.xaxis.grid(True, color=GRID, linewidth=0.8)
        ys = list(range(len(F6_ROWS)))[::-1]
        top = 0
        for y, (row, label) in zip(ys, F6_ROWS):
            rec = _cell(numbers, table, row, "recall")
            m, a = map(int, rec.split("/"))
            c = int(_cell(numbers, table, row, "precision").split("/")[1])
            top = max(top, a)
            ax.barh(y, a, color=GRID, height=0.62, zorder=2)
            bar = ax.barh(y, m, color=colour, height=0.62, zorder=3)[0]
            drawn[(run, row)] = (int(bar.get_width()), a)
            ax.annotate(f"{m}/{a} · {c} reported", (a, y), xytext=(3, 0), textcoords="offset points", va="center",
                        fontsize=6.5, color=INK2)
        ax.set_xlim(0, xmax * 1.6)
        ax.set_yticks(ys, [lab for _, lab in F6_ROWS], fontsize=7.5)
        ax.set_title(name, fontsize=8.5, color=INK, loc="left")
        ax.set_xlabel("audit issues (grey); matched by the CHECKER (colour)", fontsize=7, color=INK2)
    fig.suptitle("F6. The CHECKER against the deterministic audit: matched/total per stratum (reversal recall "
                 "measures reading, not discovery)", x=0.01, ha="left", fontsize=10, color=INK)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    _save(fig, out / "F6_checker_vs_audit.png")
    return drawn


# --------------------------------------------------------------------------- animations (owner decision §11 #51)
def net_balances(run: str) -> dict[int, dict[str, dict[str, int]]]:
    """Per day and resource, each department's allocation in effect minus the common initial allocation of day 1
    (Log #137). The records hold allocations, not transfers, so no movement between departments is implied."""
    rec = load_records(long_path(ROOT / "results" / "allocations" / run))
    init = rec.initial
    return {t: {res: {d: rec.alloc[t][res][d] - init[res][d] for d in DEPARTMENTS} for res in ("beds", "nurses")}
            for t in sorted(rec.alloc)}


def animate(run: str, limits: dict[str, int], out: Path = FIG_DIR / "animations", pools: dict | None = None) -> Path:
    data = net_balances(run)
    days = sorted(data)
    fig, axes = plt.subplots(1, 2, figsize=(8.4, 3.7))
    labels = [SHORT[d].replace(" ", "\n") for d in DEPARTMENTS]

    def draw(i):
        t = days[i]
        for ax, res, unit in ((axes[0], "beds", "beds"), (axes[1], "nurses", "nurses")):
            ax.clear()
            _style(ax)
            vals = [data[t][res][d] for d in DEPARTMENTS]
            ax.bar(range(4), vals, color=[DEPT[d] for d in DEPARTMENTS], edgecolor=SURFACE, linewidth=2, zorder=2)
            ax.axhline(0, color=INK2, linewidth=1, zorder=3)
            for x, v in enumerate(vals):
                ax.annotate(f"{v:+d}", (x, v), ha="center", va="bottom" if v >= 0 else "top", fontsize=8,
                            color=INK, xytext=(0, 2 if v >= 0 else -2), textcoords="offset points")
            ax.set_ylim(-limits[res], limits[res])
            ax.set_xticks(range(4), labels, fontsize=7.5)
            ax.set_ylabel(f"net {unit} vs day-1 initial allocation", fontsize=8, color=INK2)
            title = f"{unit.capitalize()}"
            if pools:
                title += f" (pool {pools[res][t]})"
            ax.set_title(title, fontsize=9, color=INK, loc="left")
        fig.suptitle(f"{run} · day {t} of {days[-1]}", x=0.01, ha="left", fontsize=11, color=INK)
        fig.text(0.01, 0.01, "Net change per department only: the records hold allocations, not transfers, so no "
                 "movement between departments is drawn.", fontsize=6.5, color=INK2) if i == 0 else None
        fig.tight_layout(rect=(0, 0.04, 1, 0.94))

    anim = FuncAnimation(fig, draw, frames=len(days), interval=600)
    path = guard_write(Path(out) / f"{run}_net_balances.gif")
    path.parent.mkdir(parents=True, exist_ok=True)
    anim.save(long_path(path), writer=PillowWriter(fps=2), dpi=90, savefig_kwargs={"facecolor": SURFACE})
    plt.close(fig)
    return path


def common_limits(runs: list[str] = AGENT_RUNS) -> dict[str, int]:
    """The same y-limits in every animation, so the runs can be compared frame by frame."""
    out = {}
    for res in ("beds", "nurses"):
        m = max(abs(v) for r in runs for day in net_balances(r).values() for v in day[res].values())
        out[res] = int(m * 1.25) + 1
    return out
