"""Shared helpers of the Phase 2 analysis tables (src/10_* ... src/14_*; Decisions Log #128).

Every table is written in long format, one row per reported number:

    id, table, row, col, value, role, pre_registered, note

`id` is `<table>.<row>.<col>` and is what ANALYSIS.md and results/analysis/HEADLINE_NUMBERS.csv refer to.
`role` is the pre-registered role of the quantity (headline, gate, secondary, descriptive, context, check);
`pre_registered` is "yes" when the quantity and its reading were fixed before the agent output it is computed
on (EVALUATION_PLAN.md, fixed 2026-11-12; PROJECT_SPEC.md §11 #73-#75, fixed before the comparison was run),
"no" for anything added in the analysis. Counts that the plan asks to write as matched/total are strings
"m/n" (§4 item 6). No timestamps are written, so re-running a script reproduces its files byte for byte.
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

from src.utils.paths import guard_write, long_path

from .dataset import ROOT, load_dataset
from .metrics import evaluate_run

ANALYSIS_DIR = ROOT / "results" / "analysis"
COLUMNS = ["id", "table", "row", "col", "value", "role", "pre_registered", "note"]
AGENT_RUNS = ["R1", "R2", "R3"]
BASELINES = ["B0", "B1", "B2"]
PRIMARY = "seed20261107"
STRESS = "seed20261107_stress"


def fmt(v) -> str:
    """Integers as written; floats to at most 4 decimals without trailing zeros; None as an en dash."""
    if v is None:
        return "–"
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        s = f"{v:.4f}".rstrip("0").rstrip(".")
        return "0" if s in ("-0", "") else s
    return str(v)


def frac(m: int, n: int) -> str:
    return f"{m}/{n}"


def slug(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_")


class Table:
    """Rows of one or more display tables, written to one long-format CSV."""

    def __init__(self) -> None:
        self.rows: list[dict] = []
        self._ids: set[str] = set()

    def add(self, table: str, row: str, col: str, value, role: str, pre_registered: bool, note: str = "") -> None:
        rid = f"{table}.{slug(row)}.{slug(col)}"
        if rid in self._ids:
            raise ValueError(f"duplicate id {rid}")
        self._ids.add(rid)
        self.rows.append({"id": rid, "table": table, "row": row, "col": col, "value": fmt(value), "role": role,
                          "pre_registered": "yes" if pre_registered else "no", "note": note})

    def write(self, path: Path) -> Path:
        path = guard_write(Path(path))
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(long_path(path), "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=COLUMNS, lineterminator="\n")
            w.writeheader()
            w.writerows(self.rows)
        return path


def read_table(path: Path) -> list[dict]:
    with open(long_path(path), encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def policy_metrics(name: str, dataset_id: str | None = None) -> dict:
    """Audit and metrics of a run (agent run or baseline), recomputed from its committed records with the same
    code for every policy (`metrics.evaluate_run`; output to the guarded default results/analysis/recomputed/,
    never the run folder). For a baseline the result must equal its committed metrics.json."""
    alloc = ROOT / "results" / "allocations" / name
    if dataset_id is None:
        dataset_id = json.loads((alloc / "run_manifest.json").read_text(encoding="utf-8"))["dataset_id"]
    m = evaluate_run(load_dataset(dataset_id), alloc)
    committed = ROOT / "results" / "evaluations" / name / "metrics.json"
    if long_path(committed).exists() and json.loads(json.dumps(m)) != json.loads(committed.read_text(encoding="utf-8")):
        raise SystemExit(f"{name}: recomputed metrics differ from the committed {committed}")
    return m


def audit_days(run: str) -> list[dict]:
    """Day records of a run's committed deterministic audit (re-verified EQUAL by src/06 for agent runs and
    src/03 for baselines), in day order."""
    path = ROOT / "results" / "evaluations" / run / "deterministic_audit.jsonl"
    lines = [json.loads(x) for x in long_path(path).read_text(encoding="utf-8").splitlines() if x.strip()]
    return sorted((d for p in lines for d in p["days"]), key=lambda d: d["day"])


def metric_rows(m: dict) -> list[tuple[str, str, object, object]]:
    """(label, role, value, floor) for every metric of EVALUATION_PLAN.md §3, in the §3.10 order. The headline
    and secondary rows and their floors are exactly those of the headroom table (§8; `__main__.rows`); the
    rest are the remaining §3 quantities. floor None = no floor defined."""
    from .__main__ import rows                            # the §8 table's own definition of rows and floors
    base = rows(m)
    out = []
    role = {"A1": "headline", "A2": "headline", "A3": "headline"}
    for label, (v, fl) in base.items():
        if label.startswith(("A1", "A2", "A3")):
            out.append((label, role[label[:2]], v, fl))
    e, a4 = m["E"], m["A4"]
    for res, name in (("beds", "bed"), ("nurses", "nurse")):
        for w in ("W3", "W2", "W5"):                     # W = 3 primary; W = 2 and 5 pre-registered sensitivity
            out.append((f"E {name} reversals {w}", "secondary", e[res]["reversals"][w], 0))
    for k in (1, 2, 3):
        out.append((f"B1 dispersion L{k} (pp)", "secondary", m["B1"][f"L{k}"]["dispersion_pp"], None))
    for k in (1, 2, 3):
        out.append((f"B2 F1 inversions L{k}", "secondary", m["B2"][f"L{k}"]["count"], 0))
        out.append((f"B2 F1 inversion wait days L{k}", "secondary", m["B2"][f"L{k}"]["wait_days"], 0))
    for k in (1, 2, 3):
        out.append((f"B3 mean overflow days L{k}", "secondary", m["B3"][f"L{k}"]["mean_days"], None))
        out.append((f"B3 max overflow days L{k}", "secondary", m["B3"][f"L{k}"]["max_days"], None))
    for k in (3, 2, 1):
        out.append((f"A4 shortage L{k}", "secondary", a4["shortage_by_level"][k], None))
    for k in (3, 2, 1):
        out.append((f"A4 tier floor tier {k}", "context", a4["tier_floor"][k], None))
    # The shortage above is per level k; the floor is per tier j (levels >= j, §3.4). On the tier scale the
    # shortage is the sum over k >= j, and its excess over the floor must equal A2's raw gap at tier j (§3.4:
    # "the tier excess equals Σ_t gapN_j"). A difference is a bug, not a finding.
    for j in (3, 2, 1):
        tier = round(sum(a4["shortage_by_level"][k] for k in (1, 2, 3) if k >= j), 4)
        excess = round(tier - a4["tier_floor"][j], 4)
        if abs(excess - m["A2"][f"tier{j}"]["raw_gap"]) > 1e-6:
            raise SystemExit(f"STOP: A4 tier {j} excess {excess} != A2 raw gap {m['A2'][f'tier{j}']['raw_gap']}")
        out.append((f"A4 tier shortage tier {j} (levels >= {j})", "context", tier, a4["tier_floor"][j]))
        out.append((f"A4 tier excess tier {j} (= A2 raw gap)", "context", excess, 0))
    for res, name in (("beds", "bed"), ("nurses", "nurse")):
        out.append((f"E {name} RS total", "descriptive", e[res]["RS_total"], None))
        out.append((f"E {name} reallocation frequency (days)", "descriptive", e[res]["frequency_days"], None))
    c = m["C"]
    out += [("C1 bed utilisation", "descriptive", c["C1_bed_utilisation"], None),
            ("C2 avoidable idle bed-days", "descriptive", c["C2_avoidable_idle_bed_days"], 0),
            ("C3 nurse utilisation", "descriptive", c["C3_nurse_utilisation"], None),
            ("C4 avoidable idle nurse-days", "descriptive", c["C4_avoidable_idle_nurse_days"], 0),
            ("C4 unavoidable idle nurse-days", "descriptive", c["C4_unavoidable_idle_nurse_days"], None)]
    for k in (1, 2, 3):
        out.append((f"B4 coverage dispersion L{k}", "descriptive", m["B4"][f"L{k}"]["dispersion"], None))
    return out


def lexicographic(a: tuple, b: tuple) -> str:
    """'better' / 'equal' / 'worse' for a against b, lower is better, read element by element."""
    for x, y in zip(a, b):
        if round(x - y, 9) < 0:
            return "better"
        if round(x - y, 9) > 0:
            return "worse"
    return "equal"


# ---------------------------------------------------------------- ANALYSIS.md and HEADLINE_NUMBERS.csv (step 14)
SOURCES = {"main_comparison.csv": "src/10_main_comparison.py", "checker_vs_audit.csv": "src/11_checker_vs_audit.py",
           "checker_on_wrong_claims.csv": "src/12_checker_on_wrong_claims.py", "stress1.csv": "src/13_stress1.py"}
TEMPLATE = ROOT / "src" / "evaluation" / "analysis_template.md"
NUMBER_COLUMNS = ["id", "value", "source_file", "script", "pre_registered", "role", "label"]
_TOKEN = re.compile(r"\{\{(table|n):([^}|]+)(?:\|([^}]*))?\}\}")


def load_numbers(folder: Path = ANALYSIS_DIR) -> dict[str, dict]:
    out = {}
    for name, script in SOURCES.items():
        for r in read_table(Path(folder) / name):
            out[r["id"]] = {**r, "source_file": f"results/analysis/{name}", "script": script}
    return out


def _cell(v: str) -> str:
    return v.replace("|", r"\|")


def render(template: str, numbers: dict[str, dict]) -> tuple[str, list[dict]]:
    """Replace `{{table:<name>}}` (optionally `|<regex on the row label>`) with a Markdown table of that
    long-format table, and `{{n:<id>}}` with the value and its id. Returns the text and the HEADLINE_NUMBERS
    rows of every number used, in order of first use."""
    used: dict[str, dict] = {}

    def use(r):
        used.setdefault(r["id"], {"id": r["id"], "value": r["value"], "source_file": r["source_file"],
                                  "script": r["script"], "pre_registered": r["pre_registered"], "role": r["role"],
                                  "label": f"{r['row']} / {r['col']}"})

    def sub(m):
        kind, key, opt = m.group(1), m.group(2).strip(), m.group(3)
        if kind == "n":
            if key not in numbers:
                raise KeyError(f"unknown id {key}")
            use(numbers[key])
            return f"{numbers[key]['value']} [`{key}`]"
        collapse = opt == "collapse"                         # fold rows that are 0/0 in every column
        rows = [r for r in numbers.values() if r["table"] == key
                and (not opt or collapse or re.search(opt, r["row"]))]
        if not rows:
            raise KeyError(f"unknown or empty table {key}")
        order_r = list(dict.fromkeys(r["row"] for r in rows))
        order_c = list(dict.fromkeys(r["col"] for r in rows))
        cell = {(r["row"], r["col"]): r for r in rows}
        lines = ["| | " + " | ".join(_cell(c) for c in order_c) + " |", "| --- |" + " --- |" * len(order_c)]
        folded = [rr for rr in order_r if collapse
                  and all(cell[(rr, c)]["value"] == "0/0" for c in order_c if (rr, c) in cell)]
        for rr in folded:
            for c in order_c:
                if (rr, c) in cell:
                    use(cell[(rr, c)])
        for rr in (x for x in order_r if x not in folded):
            vals = []
            for c in order_c:
                r = cell.get((rr, c))
                if r is not None:
                    use(r)
                vals.append(_cell(r["value"]) if r is not None else "")
            lines.append(f"| {_cell(rr)} | " + " | ".join(vals) + " |")
        src = rows[0]
        if folded:
            lines += ["", "Rows with no issue on either side (0/0 in every column): "
                      + ", ".join(f"`{x}`" for x in folded) + "."]
        lines.append("")
        lines.append(f"*Source: [`{src['source_file']}`]({src['source_file']}), written by `{src['script']}`. "
                     f"Each cell's id is `{key}.<row>.<column>` (row and column names with every run of other characters as `_`) in `results/analysis/HEADLINE_NUMBERS.csv`.*")
        return "\n".join(lines)

    text = _TOKEN.sub(sub, template)
    return text, list(used.values())

