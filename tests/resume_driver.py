"""Deterministic stand-in for a run session, used by tests/test_resume.py (no LLM).

    python tests/resume_driver.py <alloc_dir> <eval_dir>

Follows `expected_next_action` like the dispatcher. Its ALLOCATOR is fixed: day 2 makes one rejected
submission and then submits B1; day 4 submits nothing (repair rule); other days submit B1. The CHECKER
submits a fixed empty report. With HRA_CRASH_AFTER set, the process dies part-way (src/mcp_server/store.py).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.evaluation.baselines import b1  # noqa: E402
from src.mcp_server.store import Store  # noqa: E402
from src.mcp_server.workflow import Workflow  # noqa: E402
from src.utils.constants import DEPARTMENTS  # noqa: E402

EXPL = {k: f"driver {k}" for k in ("situation", "information_used", "alternatives", "reasons", "tradeoffs",
                                   "uncertainty")}


def main() -> int:
    store = Store(Path(sys.argv[1]), Path(sys.argv[2]))
    for _ in range(200):
        w = Workflow(store)
        st = w.get_workflow_status()
        act, t = st["expected_next_action"], st["day"]
        if act.startswith("call advance_day"):
            w.advance_day()
        elif act.startswith("invoke the allocator"):
            # the same decisions whatever the point of resumption: attempts are read from the records
            if t == 2 and w._state()["attempts"] == 0:
                zero = {d: 0 for d in DEPARTMENTS}
                w.submit_decision(zero, zero, EXPL)                  # attempt 1: rejected
            if t != 4 and not w._state()["accepted"]:
                prev = w._allocation_in_effect(t)
                beds, nurses = b1(prev["beds"], prev["nurses"], w._ctx(t))
                w.submit_decision(beds, nurses, EXPL)
            w.end_allocation_phase()
        elif act.startswith("call end_allocation_phase"):
            w.end_allocation_phase()
        elif act.startswith("invoke the checker"):
            w.submit_validation_report({"period": {"from_day": t - 4, "to_day": t}, "checked": ["driver"],
                                        "issues": [], "summary": "driver"})
            w.close_day()
        elif act.startswith("call close_day"):
            w.close_day()
        elif "finished" in act:
            return 0
        else:
            print(act)
            return 2
    return 3


if __name__ == "__main__":
    sys.exit(main())
