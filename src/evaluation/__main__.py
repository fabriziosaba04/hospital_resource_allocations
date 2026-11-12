"""Run baselines B0-B2 on the frozen datasets, audit them and write the headroom table.

    uv run python -m src.evaluation

The manifest check must pass first (CLAUDE.md §9.3). Outputs:
results/allocations/<B?-dataset>/, results/evaluations/<B?-dataset>/, results/evaluations/headroom.json
"""

from __future__ import annotations

import json
import subprocess
import sys

from .dataset import ROOT, load_dataset
from .metrics import evaluate_run
from .runner import run_baseline

MAIN = ["seed20261107", "seed20261108", "seed20261109"]
STRESS = ["seed20261107_stress"]
BASELINES = ["B0", "B1", "B2"]


def rows(m: dict) -> dict:
    """The per-metric values reported in the headroom table, with their floors (None = no floor computed)."""
    a1, a2, a3, e = m["A1"], m["A2"], m["A3"], m["E"]
    r = {
        "A1 SV_B": (a1["SV_B"], 0),
        "A1 displaced severity": (a1["by_type"]["displaced"]["severity"], 0),
        "A1 empty severity": (a1["by_type"]["empty"]["severity"], 0),
        "A1 shock-cut severity": (a1["by_type"]["shock_cut"]["severity"], 0),
    }
    for j in (3, 2, 1):
        r[f"A2 SV_N tier {j}"] = (a2[f"tier{j}"]["SV_N"], 0)
    for j in (3, 2):
        t = a3[f"tier{j}"]
        r[f"A3 tier {j} raw"] = (t["raw"], t["floor"])
        r[f"A3 tier {j} excess"] = (t["excess"], 0)
        r[f"A3 tier {j} avoid"] = (t["avoid"], 0)
        r[f"A3 tier {j} path"] = (t["path"], 0)
    r["E bed reversals W3 (all)"] = (e["beds"]["reversals"]["W3"], 0)
    r["E bed reversals W3 (occupied)"] = (e["beds"]["occupied_reversals"]["W3"], 0)
    for k in (1, 2, 3):
        r[f"B1 dispersion L{k} (pp)"] = (m["B1"][f"L{k}"]["dispersion_pp"], None)
        r[f"B2 F1 inversions L{k}"] = (m["B2"][f"L{k}"]["count"], 0)
        r[f"B3 mean overflow days L{k}"] = (m["B3"][f"L{k}"]["mean_days"], None)
    for k in (3, 2, 1):
        r[f"A4 shortage L{k}"] = (m["A4"]["shortage_by_level"][k], None)
    r["E nurse reversals W3"] = (e["nurses"]["reversals"]["W3"], 0)
    return r


def main() -> int:
    chk = subprocess.run([sys.executable, "-m", "src.data_generation.manifest", "--verify"], cwd=ROOT,
                         capture_output=True, text=True)
    if chk.returncode != 0:
        print(chk.stdout, chk.stderr)
        print("manifest check failed: no run")
        return 1
    out = {}
    for ds_id in MAIN + STRESS:
        ds = load_dataset(ds_id)
        for b in BASELINES:
            m = evaluate_run(ds, run_baseline(b, ds))
            out[f"{b}-{ds_id}"] = m
            print(f"{b}-{ds_id}: gate {m['D']['gate_passed']}")
    table = {}
    for ds_id in MAIN + STRESS:
        per = {b: rows(out[f"{b}-{ds_id}"]) for b in BASELINES}
        table[ds_id] = {name: {"B0": per["B0"][name][0], "B1": per["B1"][name][0], "B2": per["B2"][name][0],
                               "floor": per["B1"][name][1],
                               "B1_minus_floor": None if per["B1"][name][1] is None
                               else round(per["B1"][name][0] - per["B1"][name][1], 4)}
                        for name in per["B1"]}
    (ROOT / "results" / "evaluations" / "headroom.json").write_text(
        json.dumps({"note": "baselines only; no agent output", "table": table}, indent=2) + "\n",
        encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
