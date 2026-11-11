"""Monte Carlo analysis on seeds 1..n (Decisions Log #30, #33):

- the pre-registered Shock 3 candidate sweep (#33);
- per-day p5/p50/p95 bands of census (total, per department) and N1 requirement, with the primary
  dataset overlaid (CSV + PNG);
- the imbalance metric (#34) on the MC and the primary dataset;
- the MC mean of realised LOS per level.

    uv run python -m src.data_generation.mc_analysis --n 1000 --primary seed20261107

Outputs go to data/processed/montecarlo/ (hidden in run sessions: data/** is denied).
Demand does not depend on the pools, so one simulation per seed serves every candidate schedule.
"""

from __future__ import annotations

import argparse
import copy
import csv
import json
from pathlib import Path

import numpy as np

from src.environment.allocation import largest_remainder
from src.utils.constants import DEPARTMENTS

from .generator import generate, load_json, pools_for_day
from .stats import CENSUS_COLS, n1_requirement, typed
from .validation import load_dataset

CONFIG_DIR = Path(__file__).parent / "configs"
DEPT_LABEL = {"internal_medicine": "Internal Medicine", "cardiology": "Cardiology",
              "neurology": "Neurology", "orthopedics": "Orthopedics"}


# ----------------------------------------------------------------------------- candidate schedules

def candidate_configs(gen: dict) -> dict[str, dict]:
    """Pre-registered candidates (Decisions Log #33). Pool during Shock 3 is 96 - N in all of them."""
    base = int(gen["base_pools"]["total_beds"])
    nurse_shocks = [s for s in gen["shocks"] if s["resource"] == "nurses"]
    out = {}

    def make(name, family, n, shock2, shock3, onset, eligible):
        cfg = copy.deepcopy(gen)
        cfg["shocks"] = nurse_shocks + [shock2, shock3]
        out[name] = {"family": family, "N": n, "onset_day": onset, "eligible": eligible,
                     "window": (shock3["from_day"], shock3["to_day"]), "config": cfg,
                     "schedule": f"beds +4 days {shock2['from_day']}-{shock2['to_day']}; "
                                 f"beds -{n} days {shock3['from_day']}-{shock3['to_day']} (pool {base - n})"}

    s2 = {"resource": "beds", "delta": 4, "from_day": 16, "to_day": 20}
    s2_short = {"resource": "beds", "delta": 4, "from_day": 16, "to_day": 18}
    make("approved (A10)", "approved", 10, s2, {"resource": "beds", "delta": -10, "from_day": 23, "to_day": 25}, 23, False)
    for n in (18, 22, 26):
        make(f"A{n}", "A", n, s2, {"resource": "beds", "delta": -n, "from_day": 23, "to_day": 25}, 23, True)
    for n in (10, 14, 18):
        make(f"B{n}", "B", n, s2_short, {"resource": "beds", "delta": -n, "from_day": 19, "to_day": 21}, 19, True)
    for n in (10, 14, 18):
        make(f"C{n}", "C", n, s2, {"resource": "beds", "delta": -n, "from_day": 21, "to_day": 23}, 21, False)
    return out


def pool_series(cfg: dict) -> np.ndarray:
    H = int(cfg["horizon_days"])
    return np.array([pools_for_day(cfg, t)[0] for t in range(1, H + 1)])


# ----------------------------------------------------------------------------- per-seed arrays

def demand_arrays(demand, env: dict) -> dict[str, np.ndarray]:
    """Arrays indexed [day-1, dept] in the fixed department order."""
    d = demand.sort_values(["day"]).copy()
    d["dept_idx"] = d["department"].map({k: i for i, k in enumerate(DEPARTMENTS)})
    d = d.sort_values(["day", "dept_idx"])
    H = d["day"].max()
    census = d[CENSUS_COLS].sum(axis=1).to_numpy().reshape(H, 4)
    arrivals = d["arrivals"].to_numpy().reshape(H, 4)
    n1 = n1_requirement(d["census_L1"].to_numpy(), d["census_L2"].to_numpy(), d["census_L3"].to_numpy(), env).reshape(H, 4)
    return {"census": census, "arrivals": arrivals, "n1": n1}


def shock_metrics(arr: dict, pools: np.ndarray, onset: int, window: tuple[int, int], max_beds: int) -> dict:
    census = arr["census"]
    total = census.sum(axis=1)
    t0 = onset - 1                                          # 0-based index of the onset day
    carried = int(total[t0] - arr["arrivals"][t0].sum())
    occ_max_prev = min(int(pools[t0 - 1]), int(np.minimum(census[t0 - 1], max_beds).sum()))
    ovf_min = int(total[t0 - 1]) - occ_max_prev
    forced = max(0, carried - ovf_min - int(pools[t0]))
    possible = max(0, min(carried, int(pools[t0 - 1])) - int(pools[t0]))
    over = total > pools
    w = slice(window[0] - 1, window[1])
    return {
        "carried": carried, "forced_cut": forced, "possible_cut": possible,
        "days_census_gt_pool": int(over.sum()),
        "window_days_census_gt_pool": int(over[w].sum()),
        "window_mean_excess": float(np.maximum(0, total[w] - pools[w]).mean()),
    }


def imbalance(arr: dict, pools: np.ndarray, max_beds: int) -> dict:
    """Decisions Log #34. Days with total census < pool on which some department's census exceeds its
    share of the pool; shares are (i) the initial-allocation proportions, (ii) an equal split."""
    census = arr["census"]
    total = census.sum(axis=1)
    b1 = largest_remainder(int(pools[0]), census[0].tolist(), caps=[max_beds] * 4)
    out = {}
    for name, weights in (("initial_share", b1), ("equal_share", [1, 1, 1, 1])):
        days, excess = 0, 0
        for t in range(len(pools)):
            if total[t] >= pools[t]:
                continue
            share = np.array(largest_remainder(int(pools[t]), weights, caps=[max_beds] * 4))
            ex = np.maximum(0, census[t] - share)
            if ex.sum() > 0:
                days += 1
                excess += int(ex.sum())
        out[name] = {"days": days, "excess_patient_days": excess}
    return out


def los_means(registry) -> dict[str, float]:
    los = registry["discharge_day"] - registry["arrival_day"]
    return {f"L{k}": float(los[registry["complexity"] == k].mean()) for k in (1, 2, 3)}


# ----------------------------------------------------------------------------- summaries

def pct(a, qs=(5, 50, 95)) -> dict:
    a = np.asarray(a, dtype=float)
    return {f"p{q}": float(np.percentile(a, q)) for q in qs} | {"mean": float(a.mean())}


def run(n: int, gen: dict, env: dict, primary: dict | None) -> dict:
    max_beds = int(env["max_beds"])
    cands = candidate_configs(gen)
    cand_pools = {k: pool_series(c["config"]) for k, c in cands.items()}
    approved_pools = pool_series(gen)
    H = int(gen["horizon_days"])

    per_seed = {k: [] for k in cands}
    bands = {"total_census": [], "n1_total": [], **{f"census_{d}": [] for d in DEPARTMENTS}}
    imb = []
    los = []
    carried_by_day = {19: [], 21: [], 23: []}
    for seed in range(1, n + 1):
        ds = generate(gen, env, seed)
        arr = demand_arrays(ds.demand, env)
        for k, c in cands.items():
            per_seed[k].append(shock_metrics(arr, cand_pools[k], c["onset_day"], c["window"], max_beds))
        bands["total_census"].append(arr["census"].sum(axis=1))
        bands["n1_total"].append(arr["n1"].sum(axis=1))
        for i, d in enumerate(DEPARTMENTS):
            bands[f"census_{d}"].append(arr["census"][:, i])
        imb.append(imbalance(arr, approved_pools, max_beds))
        los.append(los_means(ds.registry))
        for t in carried_by_day:
            carried_by_day[t].append(int(arr["census"][t - 1].sum() - arr["arrivals"][t - 1].sum()))

    sweep = {}
    for k, c in cands.items():
        rows = per_seed[k]
        forced = np.array([r["forced_cut"] for r in rows])
        possible = np.array([r["possible_cut"] for r in rows])
        sweep[k] = {
            "family": c["family"], "N": c["N"], "eligible": c["eligible"], "schedule": c["schedule"],
            "onset_day": c["onset_day"],
            "P_forced_cut": float((forced > 0).mean()),
            "P_possible_cut": float((possible > 0).mean()),
            "forced_cut_size": pct(forced),
            "forced_cut_size_given_cut": pct(forced[forced > 0]) if (forced > 0).any() else None,
            "days_census_gt_pool": pct([r["days_census_gt_pool"] for r in rows]),
            "window_mean_daily_excess_census_over_pool": pct([r["window_mean_excess"] for r in rows]),
            "carried_into_onset": pct([r["carried"] for r in rows]),
        }
    if primary is not None:
        for k, c in cands.items():
            sweep[k]["primary"] = shock_metrics(primary["arr"], cand_pools[k], c["onset_day"], c["window"], max_beds)

    # pre-registered rule (#33)
    eligible = [(v["N"], v["days_census_gt_pool"]["mean"], k) for k, v in sweep.items()
                if v["eligible"] and v["P_forced_cut"] >= 0.85]
    selection = sorted(eligible)[0][2] if eligible else None

    band_rows = {}
    for name, series in bands.items():
        a = np.vstack(series)
        band_rows[name] = {q: np.percentile(a, q, axis=0) for q in (5, 50, 95)}
    imb_summary = {
        name: {m: pct([x[name][m] for x in imb]) for m in ("days", "excess_patient_days")}
        for name in ("initial_share", "equal_share")
    }
    if primary is not None:
        for name in imb_summary:
            imb_summary[name]["primary"] = primary["imbalance"][name]
            for m in ("days", "excess_patient_days"):
                a = np.array([x[name][m] for x in imb])
                v = primary["imbalance"][name][m]
                imb_summary[name][m]["primary_percentile"] = float(100 * ((a < v).mean() + 0.5 * (a == v).mean()))
    return {
        "n_seeds": n, "seeds": f"1..{n}",
        "sweep": sweep, "selection_by_preregistered_rule": selection,
        "carried_by_onset_day": {t: pct(v) for t, v in carried_by_day.items()},
        "imbalance": imb_summary,
        "los_mean_mc": {k: pct([x[k] for x in los]) for k in ("L1", "L2", "L3")},
        "_bands": band_rows, "_H": H,
    }


# ----------------------------------------------------------------------------- outputs

def write_bands_csv(path: Path, bands: dict, primary_series: dict, H: int) -> None:
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["series", "day", "p5", "p50", "p95", "primary"])
        for name, q in bands.items():
            for t in range(H):
                w.writerow([name, t + 1, f"{q[5][t]:.1f}", f"{q[50][t]:.1f}", f"{q[95][t]:.1f}",
                            int(primary_series[name][t]) if primary_series else ""])


def plot_bands(path: Path, bands: dict, primary_series: dict, pools: np.ndarray, nurses: np.ndarray,
               max_beds: int, H: int, primary_id: str) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch

    surface, ink, ink2, grid = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
    band, median, prim, ref = "#b7d3f6", "#2a78d6", "#eb6834", "#52514e"
    plt.rcParams.update({"font.size": 9, "axes.edgecolor": grid, "axes.labelcolor": ink2,
                         "xtick.color": ink2, "ytick.color": ink2, "text.color": ink})
    panels = [("total_census", "Total census", ("bed pool", pools)),
              *[(f"census_{d}", f"Census: {DEPT_LABEL[d]}", ("max_beds", np.full(H, max_beds))) for d in DEPARTMENTS],
              ("n1_total", "N1 nurse requirement (total)", ("nurse pool", nurses))]
    fig, axes = plt.subplots(2, 3, figsize=(13, 7), sharex=True, facecolor=surface)
    days = np.arange(1, H + 1)
    for ax, (key, title, (ref_label, ref_vals)) in zip(axes.flat, panels):
        ax.set_facecolor(surface)
        q = bands[key]
        ax.fill_between(days, q[5], q[95], color=band, linewidth=0, step=None)
        ax.plot(days, q[50], color=median, linewidth=1.5)
        ax.step(days, ref_vals, where="mid", color=ref, linewidth=1.2, linestyle=(0, (4, 3)))
        if primary_series:
            ax.plot(days, primary_series[key], color=prim, linewidth=2, marker="o", markersize=3.2,
                    markeredgecolor=surface, markeredgewidth=0.8)
        ax.set_title(title, loc="left", fontsize=10, color=ink)
        ax.grid(axis="y", color=grid, linewidth=0.6)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        ax.text(H + 0.3, ref_vals[-1], ref_label, color=ink2, fontsize=8, va="center")
        ax.set_xlim(1, H + 4.5)
    for ax in axes[1]:
        ax.set_xlabel("Day")
    handles = [Patch(color=band, label="MC p5–p95"), Line2D([], [], color=median, lw=1.5, label="MC median"),
               Line2D([], [], color=prim, lw=2, marker="o", ms=3.2, label=f"Primary dataset ({primary_id})"),
               Line2D([], [], color=ref, lw=1.2, ls=(0, (4, 3)), label="Pool / cap")]
    fig.legend(handles=handles, loc="upper left", ncol=4, frameon=False, bbox_to_anchor=(0.01, 0.995))
    fig.suptitle("Per-day Monte Carlo bands (seeds 1–1000), approved schedule", x=0.01, y=0.955, ha="left",
                 fontsize=11, color=ink)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.savefig(path, dpi=150, facecolor=surface)
    plt.close(fig)


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--n", type=int, default=1000)
    p.add_argument("--config", default=str(CONFIG_DIR / "generation_config.json"))
    p.add_argument("--env", default=str(CONFIG_DIR / "environment_config.json"))
    p.add_argument("--primary", default=None)
    p.add_argument("--root", default=".")
    args = p.parse_args(argv)
    gen, env = load_json(args.config), load_json(args.env)

    primary = None
    primary_series = {}
    if args.primary:
        data = typed(load_dataset(args.root, args.primary))
        arr = demand_arrays(data["demand"], env)
        pools = data["resources"].sort_values("day")["total_beds"].to_numpy()
        primary = {"arr": arr, "imbalance": imbalance(arr, pools, int(env["max_beds"])), "los": los_means(data["registry"])}
        primary_series = {"total_census": arr["census"].sum(axis=1), "n1_total": arr["n1"].sum(axis=1),
                          **{f"census_{d}": arr["census"][:, i] for i, d in enumerate(DEPARTMENTS)}}

    res = run(args.n, gen, env, primary)
    out = Path(args.root) / "data" / "processed" / "montecarlo"
    out.mkdir(parents=True, exist_ok=True)
    H = res.pop("_H")
    bands = res.pop("_bands")
    write_bands_csv(out / "mc_daily_bands.csv", bands, primary_series, H)
    nurses = np.array([pools_for_day(gen, t)[1] for t in range(1, H + 1)])
    plot_bands(out / "mc_daily_bands.png", bands, primary_series, pool_series(gen), nurses,
               int(env["max_beds"]), H, args.primary or "")
    if primary is not None:
        res["primary_los_mean"] = primary["los"]
    with open(out / "mc_analysis.json", "w", encoding="utf-8", newline="\n") as fh:
        json.dump(res, fh, indent=2, default=lambda o: o.item() if hasattr(o, "item") else str(o))
        fh.write("\n")
    print(json.dumps({k: v for k, v in res.items()}, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)))


if __name__ == "__main__":
    main()
