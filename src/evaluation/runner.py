"""Baseline runner: the same day sequence as an agent run, without MCP or an LLM (PROJECT_SPEC.md §6).

Writes the PROJECT_SPEC.md §4 records for the run: allocation_state.jsonl and bed_assignment_state.jsonl
(day 1 in two stages, `initial` and `final`). Observed State and workflow records belong to the server
and are not produced for baselines.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from src.environment.bed_assignment import assign_beds
from src.environment.initial import initial_allocation
from src.environment.nurses import requirement as n1_requirement
from src.environment.validator import validate
from src.environment.whatif import DayContext
from src.utils.constants import DEPARTMENTS

from src.utils import paths

from .baselines import BASELINES
from .dataset import ROOT, Dataset


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _ctx(ds: Dataset, day: int, holder_ids: set[str]) -> DayContext:
    present = ds.present(day)
    ids = {p.patient_id for p in present}
    return DayContext(day, tuple(present), frozenset(holder_ids & ids), ds.pool_beds[day],
                      ds.pool_nurses[day], ds.max_beds, ds.env)


def _bed_line(run_id, ds, day, stage, present, asg):
    return {"run_id": run_id, "day": day, "stage": stage, "writer": "environment", "created_at": _now(),
            "inputs": {"dataset_id": ds.dataset_id, "allocation_state_day": day},
            "patients": {p.patient_id: {"department": p.department,
                                        "status": "in_bed" if p.patient_id in asg.in_bed else "overflow"}
                         for p in present}}


def run_baseline(name: str, ds: Dataset, out_root: Path | None = None) -> Path:
    """Records written to `out_root/<run_id>/`; default `results/analysis/recomputed/baselines/allocations/`."""
    run_id = f"{name}-{ds.dataset_id}"
    policy = BASELINES[name]
    alloc_lines, bed_lines = [], []
    holder_ids: set[str] = set()
    beds = nurses = None
    for day in range(1, ds.horizon + 1):
        if day == 1:
            ctx0 = _ctx(ds, 1, set())
            counts = ctx0.counts()
            census = {d: sum(counts[d].values()) for d in DEPARTMENTS}
            req = {d: n1_requirement(counts[d][1], counts[d][2], counts[d][3], ds.env) for d in DEPARTMENTS}
            beds, nurses = initial_allocation(ds.pool_beds[1], ds.pool_nurses[1], census, req, ds.max_beds)
            alloc_lines.append({"run_id": run_id, "day": 1, "writer": "initial_rule", "source": "initial_rule",
                                "created_at": _now(), "inputs": {"dataset_id": ds.dataset_id},
                                "beds": beds, "nurses": nurses})
            asg0 = assign_beds(beds, list(ctx0.present), set())
            bed_lines.append(_bed_line(run_id, ds, 1, "initial", ctx0.present, asg0))
            holder_ids = set(asg0.in_bed)
        ctx = _ctx(ds, day, holder_ids)
        beds, nurses = policy(beds, nurses, ctx)
        v = validate(beds, nurses, ctx.pool_beds, ctx.pool_nurses, ctx.max_beds, ctx.occupied)
        if v:
            raise RuntimeError(f"{run_id} day {day}: baseline produced an invalid allocation: {v}")
        alloc_lines.append({"run_id": run_id, "day": day, "writer": name, "source": name, "created_at": _now(),
                            "inputs": {"dataset_id": ds.dataset_id}, "beds": beds, "nurses": nurses})
        asg = assign_beds(beds, list(ctx.present), set(ctx.holder_ids))
        bed_lines.append(_bed_line(run_id, ds, day, "final", ctx.present, asg))
        holder_ids = set(asg.in_bed)
    if out_root is None:
        out_root = paths.RESULTS_ROOT / "analysis" / "recomputed" / "baselines" / "allocations"
    out = paths.guard_write(Path(out_root) / run_id)     # frozen run folders are read-only (R59)
    out.mkdir(parents=True, exist_ok=True)
    for fname, lines in (("allocation_state.jsonl", alloc_lines), ("bed_assignment_state.jsonl", bed_lines)):
        tmp = out / (fname + ".tmp")
        tmp.write_text("".join(json.dumps(x, sort_keys=True) + "\n" for x in lines), encoding="utf-8", newline="\n")
        tmp.replace(out / fname)
    return out
