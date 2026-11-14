"""Run-record consistency check (owner decision §11 #33): after any interruption and resume, every day has
exactly the records it should, and no day is duplicated. Used by the resume tests and after every launch.

    uv run python -m src.mcp_server.consistency [<run allocation dir>]
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

from .store import Store

CLOSED_PHASES = ("READY_TO_CLOSE", "AUDIT", "CLOSED", "FINISHED")


def check(store: Store) -> list[str]:
    st = store.read_state()
    d, phase = st["day"], st["phase"]
    if phase == "HALTED":
        phase = st.get("phase_before_halt", "ALLOCATION")
    retry = store.manifest()["retry_limit"]
    probs: list[str] = []
    done = d if phase in CLOSED_PHASES else d - 1          # days whose allocation phase has ended

    obs = Counter(x["day"] for x in store.read("observed_state"))
    for t in range(1, d + 1):
        if obs[t] != 1:
            probs.append(f"observed_state: {obs[t]} lines for day {t}")
    alloc = store.read("allocation_state")
    if d >= 1 and sum(1 for x in alloc if x["source"] == "initial_rule") != 1:
        probs.append("allocation_state: not exactly one initial_rule line")
    for t in range(1, d + 1):
        a = sum(1 for x in alloc if x["day"] == t and x["source"] == "ALLOCATOR")
        r = sum(1 for x in alloc if x["day"] == t and x["source"] == "repair_rule")
        r += sum(1 for x in alloc if x["day"] == t and str(x["source"]).startswith("replay_"))   # Log #89
        if a > 1 or r > 1 or (a and r):
            probs.append(f"allocation_state: day {t} has {a} ALLOCATOR and {r} repair lines")
        if t <= done and a + r != 1:
            probs.append(f"allocation_state: day {t} closed without exactly one decision or repair")
        dec = [x for x in store.read("decision_history") if x["day"] == t]
        if [x["attempt"] for x in dec] != list(range(1, len(dec) + 1)) or len(dec) > retry:
            probs.append(f"decision_history: day {t} attempts {[x['attempt'] for x in dec]}")
        acc = [x for x in dec if x["outcome"] == "accepted"]
        if len(acc) > 1 or (acc and dec[-1]["outcome"] != "accepted"):
            probs.append(f"decision_history: day {t} has {len(acc)} accepted attempts, or one not last")
        if bool(acc) != bool(a):
            probs.append(f"day {t}: accepted decision and ALLOCATOR allocation line disagree")
    beds = store.read("bed_assignment_state")
    if d >= 1 and sum(1 for x in beds if x["day"] == 1 and x["stage"] == "initial") != 1:
        probs.append("bed_assignment_state: not exactly one day-1 initial line")
    for t in range(1, d + 1):
        n = sum(1 for x in beds if x["day"] == t and x["stage"] == "final")
        if n != (1 if t <= done else 0):
            probs.append(f"bed_assignment_state: {n} final lines for day {t}")
    audits = Counter(x["day"] for x in store.read("deterministic_audit"))
    vh = store.read("validation_history")
    for t in range(5, d + 1, 5):
        if t <= done and audits[t] != 1:
            probs.append(f"deterministic_audit: {audits[t]} records for audit day {t}")
        rep = sum(1 for x in vh if x["day"] == t and x.get("kind") == "report")
        fail = sum(1 for x in vh if x["day"] == t and x.get("kind") == "llm_checker_failure")
        closed = t < d or (t == d and phase in ("CLOSED", "FINISHED"))
        if rep > 1 or fail > 1 or (rep and fail) or (closed and rep + fail != 1):
            probs.append(f"validation_history: audit day {t} has {rep} reports and {fail} failures")
    for name in ("observed_state", "allocation_state", "decision_history", "bed_assignment_state",
                 "deterministic_audit", "validation_history"):
        future = [x["day"] for x in store.read(name) if x["day"] > d]
        if future:
            probs.append(f"{name}: records for future days {sorted(set(future))}")
    return probs


def main() -> int:
    store = Store.active() if len(sys.argv) < 2 else None
    if store is None:
        import json
        alloc = Path(sys.argv[1])
        store = Store(alloc, Path(json.loads((alloc / "run_manifest.json").read_text())["eval_dir"]))
    probs = check(store)
    print("consistent" if not probs else "\n".join(probs))
    return 1 if probs else 0


if __name__ == "__main__":
    sys.exit(main())
