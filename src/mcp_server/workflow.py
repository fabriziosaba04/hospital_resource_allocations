"""State machine and tool logic for every role (PROJECT_SPEC.md §2–§3, AGENTS.md §2–§10).

Plain Python, so it is testable without MCP; `server.py` only wraps these methods as tools. Every method
re-reads the run state from disk, checks the phase, and writes under the lock.
"""

from __future__ import annotations

import subprocess
from fractions import Fraction
from pathlib import Path

from src.environment.bed_assignment import assign_beds
from src.environment.initial import initial_allocation
from src.environment.nurses import requirement as n1_requirement
from src.environment.repair import repair
from src.environment.validator import validate
from src.environment.whatif import DayContext, simulate
from src.evaluation.audit import audit_day, load_records, weights_hundredths
from src.evaluation.dataset import ROOT, load_dataset
from src.evaluation.metrics import add_reversal_issues
from src.utils.constants import DEPARTMENTS, LEVELS

from .analyzer import run_analyzer
from .store import Store, now

PHASES = ("READY", "ALLOCATION", "READY_TO_CLOSE", "AUDIT", "CLOSED", "FINISHED", "HALTED")
EXPLANATION_FIELDS = ("situation", "information_used", "alternatives", "reasons", "tradeoffs", "uncertainty")
TEMPLATE_ALLOCATE = "ALLOCATE"
TEMPLATE_AUDIT = "AUDIT"


class WorkflowError(RuntimeError):
    """A call in the wrong phase or with invalid arguments; the message names the expected action."""


def _f(x) -> float:
    return round(float(x), 4) if isinstance(x, Fraction) else x


def _num(d: dict) -> dict:
    return {str(k): (_num(v) if isinstance(v, dict) else _f(v)) for k, v in d.items()}


def code_version() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True,
                              timeout=10).stdout.strip() or "unknown"
    except Exception:
        return "unknown"


class Workflow:
    def __init__(self, store: Store | None = None):
        self.store = store or Store.active()
        self.m = self.store.manifest()
        self.run_id = self.m["run_id"]
        self.ds = load_dataset(self.m["dataset_id"], root=Path(self.m["data_root"]))

    # ------------------------------------------------------------------ helpers
    def _line(self, writer: str, day: int, **content) -> dict:
        return {"run_id": self.run_id, "day": day, "writer": writer, "created_at": now(),
                "inputs": {"dataset_id": self.m["dataset_id"]}, **content}

    def _log(self, day, event, **detail):
        self.store.append("workflow", self._line("orchestrator", day, event=event, **detail))

    def _require(self, state: dict, phases: tuple[str, ...], tool: str):
        if state["phase"] not in phases:
            msg = (f"{tool} is not allowed in phase {state['phase']} (day {state['day']}). "
                   f"Expected next action: {self._next_action(state)}")
            with self.store.lock():
                self._log(state["day"], "rejected_call", tool=tool, phase=state["phase"])
            raise WorkflowError(msg)

    def _next_action(self, s: dict) -> str:
        p = s["phase"]
        if p in ("READY", "CLOSED"):
            return "call advance_day"
        if p == "ALLOCATION":
            return ("call end_allocation_phase" if s["accepted"] else
                    f"invoke the allocator subagent with template {TEMPLATE_ALLOCATE}, then call end_allocation_phase")
        if p == "READY_TO_CLOSE":
            return "call close_day"
        if p == "AUDIT":
            return ("call close_day" if s["report_received"] else
                    f"invoke the checker subagent with template {TEMPLATE_AUDIT}, then call close_day")
        if p == "FINISHED":
            return "the run is finished: stop"
        return f"the run is halted ({s.get('halt_reason')}): stop"

    def _allocation_in_effect(self, day: int) -> dict:
        lines = [x for x in self.store.read("allocation_state") if x["day"] <= day]
        return lines[-1]

    def _bed_line(self, day: int, stage: str) -> dict | None:
        for x in self.store.read("bed_assignment_state"):
            if x["day"] == day and x["stage"] == stage:
                return x
        return None

    def _holders(self, day: int) -> set[str]:
        prev = self._bed_line(1, "initial") if day == 1 else self._bed_line(day - 1, "final")
        present = {p.patient_id for p in self.ds.present(day)}
        return {pid for pid, v in prev["patients"].items() if v["status"] == "in_bed" and pid in present}

    def _ctx(self, day: int) -> DayContext:
        return DayContext(day, tuple(self.ds.present(day)), frozenset(self._holders(day)), self.ds.pool_beds[day],
                          self.ds.pool_nurses[day], self.ds.max_beds, self.ds.env)

    def _write_beds(self, day: int, stage: str, beds: dict, holders: set[str]) -> None:
        present = self.ds.present(day)
        asg = assign_beds(beds, present, holders)
        self.store.append("bed_assignment_state", self._line(
            "environment", day, stage=stage,
            patients={p.patient_id: {"department": p.department,
                                     "status": "in_bed" if p.patient_id in asg.in_bed else "overflow"}
                      for p in present}))

    @staticmethod
    def _check_explanation(explanation) -> None:
        if not isinstance(explanation, dict):
            raise WorkflowError(f"explanation must be an object with the fields {list(EXPLANATION_FIELDS)}")
        missing = [k for k in EXPLANATION_FIELDS if not str(explanation.get(k, "")).strip()]
        if missing:
            raise WorkflowError(f"explanation is missing or empty: {missing} (CLAUDE.md §3.6)")

    # ------------------------------------------------------------------ orchestration
    def get_workflow_status(self) -> dict:
        s = self.store.read_state()
        return {"run_id": self.run_id, "day": s["day"], "horizon": s["horizon"], "phase": s["phase"],
                "expected_next_action": self._next_action(s)}

    def advance_day(self) -> dict:
        s = self.store.read_state()
        self._require(s, ("READY", "CLOSED"), "advance_day")
        t = s["day"] + 1
        with self.store.lock():
            if t == 1:
                ctx0 = DayContext(1, tuple(self.ds.present(1)), frozenset(), self.ds.pool_beds[1],
                                  self.ds.pool_nurses[1], self.ds.max_beds, self.ds.env)
                c = ctx0.counts()
                census = {d: sum(c[d].values()) for d in DEPARTMENTS}
                req = {d: n1_requirement(c[d][1], c[d][2], c[d][3], self.ds.env) for d in DEPARTMENTS}
                beds, nurses = initial_allocation(self.ds.pool_beds[1], self.ds.pool_nurses[1], census, req,
                                                  self.ds.max_beds)
                self.store.append("allocation_state", self._line("initial_rule", 1, source="initial_rule",
                                                                 beds=beds, nurses=nurses))
                self._write_beds(1, "initial", beds, set())
            ctx = self._ctx(t)
            prev_overflow = None
            if t > 1:
                lvl = {p.patient_id: (p.department, p.complexity) for p in self.ds.present(t - 1)}
                prev_overflow = {d: {k: 0 for k in LEVELS} for d in DEPARTMENTS}
                for pid, v in self._bed_line(t - 1, "final")["patients"].items():
                    if v["status"] == "overflow":
                        d, k = lvl[pid]
                        prev_overflow[d][k] += 1
            observed = run_analyzer(Path(self.m["data_root"]), self.m["dataset_id"], t, self.ds.env, ctx.occupied,
                                    self._allocation_in_effect(t), prev_overflow)
            self.store.append("observed_state", self._line("analyzer", t, observed=observed))
            s.update(day=t, phase="ALLOCATION", attempts=0, accepted=False, report_received=False)
            self.store.write_state(s)
            self._log(t, "advance_day")
        return self.get_workflow_status()

    def end_allocation_phase(self) -> dict:
        s = self.store.read_state()
        self._require(s, ("ALLOCATION",), "end_allocation_phase")
        t = s["day"]
        with self.store.lock():
            ctx = self._ctx(t)
            if not s["accepted"]:
                prev = self._allocation_in_effect(t)
                req = {d: n1_requirement(*(ctx.counts()[d][k] for k in LEVELS), self.ds.env) for d in DEPARTMENTS}
                r = repair(prev["beds"], prev["nurses"], ctx.pool_beds, ctx.pool_nurses, ctx.max_beds, ctx.holders, req)
                self.store.append("allocation_state", self._line("repair_rule", t, source="repair_rule",
                                                                 beds=r.beds, nurses=r.nurses))
                self._log(t, "allocator_failure", attempts=s["attempts"], detail="no accepted decision; repair rule applied")
            alloc = self._allocation_in_effect(t)
            self._write_beds(t, "final", alloc["beds"], set(ctx.holder_ids))
            if t % 5 == 0:
                self._run_audit(t)
                s["phase"] = "AUDIT"
            else:
                s["phase"] = "READY_TO_CLOSE"
            self.store.write_state(s)
            self._log(t, "end_allocation_phase", source=alloc["source"])
        return self.get_workflow_status()

    def _run_audit(self, t: int) -> None:
        rec = load_records(self.store.alloc_dir)
        w = weights_hundredths(self.ds.env)
        days = [audit_day(self.ds, rec, d, w) for d in range(1, t + 1)]
        for x in rec.decisions:
            if x.get("outcome") == "rejected":
                days[x["day"] - 1]["issues"].append({"day": x["day"], "category": "violation", "level": "Moderate",
                                                     "type": "rejected_submission", "detail": x.get("codes")})
        for d in days:
            if d["source"] == "repair_rule":
                d["issues"].append({"day": d["day"], "category": "violation", "level": "Major",
                                    "type": "allocator_failure_day", "detail": "repair rule applied"})
        add_reversal_issues(days)
        period = [{k: v for k, v in d.items() if k != "in_bed"} for d in days[t - 5: t]]
        self.store.append("deterministic_audit", self._line("deterministic_audit", t,
                                                            period={"from_day": t - 4, "to_day": t}, days=period))

    def close_day(self) -> dict:
        s = self.store.read_state()
        self._require(s, ("READY_TO_CLOSE", "AUDIT"), "close_day")
        t = s["day"]
        with self.store.lock():
            if s["phase"] == "AUDIT" and not s["report_received"]:
                self.store.append("validation_history", self._line(
                    "orchestrator", t, kind="llm_checker_failure", period={"from_day": t - 4, "to_day": t}))
                self._log(t, "llm_checker_failure")
            s["phase"] = "FINISHED" if t == s["horizon"] else "CLOSED"
            self.store.write_state(s)
            self._log(t, "close_day", next_phase=s["phase"])
        return self.get_workflow_status()

    # ------------------------------------------------------------------ allocator
    def _alloc_phase(self, tool: str) -> dict:
        s = self.store.read_state()
        self._require(s, ("ALLOCATION",), tool)
        return s

    def get_observed_state(self) -> dict:
        s = self._alloc_phase("get_observed_state")
        line = [x for x in self.store.read("observed_state") if x["day"] == s["day"]][-1]
        return {"day": s["day"], **line["observed"]}

    def get_allocation_state(self) -> dict:
        s = self._alloc_phase("get_allocation_state")
        lines = [x for x in self.store.read("allocation_state") if x["day"] <= s["day"]]
        cur = lines[-1]
        return {"day": s["day"], "in_effect": {"beds": cur["beds"], "nurses": cur["nurses"], "source": cur["source"],
                                              "decided_on_day": cur["day"]},
                "decision_accepted_today": s["accepted"],
                "history": [{"day": x["day"], "source": x["source"], "beds": x["beds"], "nurses": x["nurses"]}
                            for x in lines]}

    def get_decision_history(self) -> dict:
        s = self._alloc_phase("get_decision_history")
        return {"day": s["day"], "decisions": [{k: v for k, v in x.items() if k not in ("inputs", "run_id")}
                                               for x in self.store.read("decision_history") if x["day"] <= s["day"]]}

    def get_overflow_queue(self) -> dict:
        """Patients present today without a bed held from yesterday (never discharge_day)."""
        s = self._alloc_phase("get_overflow_queue")
        t = s["day"]
        holders = self._holders(t)
        queue = [{"patient_id": p.patient_id, "department": p.department, "complexity": p.complexity,
                  "arrival_day": p.arrival_day, "days_waiting": t - p.arrival_day}
                 for p in self.ds.present(t) if p.patient_id not in holders]
        queue.sort(key=lambda x: (-x["complexity"], x["arrival_day"], x["patient_id"]))
        return {"day": t, "note": "patients present today who do not hold a bed from yesterday; "
                                  "they receive free beds by the intra-department rule once the allocation takes effect",
                "queue": queue}

    @property
    def assisted(self) -> bool:
        """Run flag for the optional "assisted" ablation (owner decision §11 #29): violation labels in the
        what-if. Off unless set in run_manifest.json at initialisation."""
        return bool(self.m.get("expose_violation_labels", False))

    def _whatif(self, beds, nurses, ctx) -> dict:
        """Outcomes only: hard-constraint result, overflow by department and level with waiting days, and
        nurse coverage and shortage by department and level. No clinical-priority labels unless assisted."""
        res = simulate(beds, nurses, ctx)
        out = {"valid": not res.violations,
               "violations": [{"code": v.code, "message": v.message} for v in res.violations]}
        if res.assignment is not None:
            overflow_patients = sorted(
                ({"patient_id": p.patient_id, "department": p.department, "complexity": p.complexity,
                  "arrival_day": p.arrival_day, "days_waiting": ctx.day - p.arrival_day}
                 for p in ctx.present if p.patient_id in res.assignment.overflow),
                key=lambda x: (x["department"], -x["complexity"], x["arrival_day"], x["patient_id"]))
            out.update(overflow_by_department_and_level=_num(res.overflow),
                       overflow_patients=overflow_patients,
                       nurse_covered_by_department_and_level=_num(res.covered),
                       nurse_shortage_by_department_and_level=_num(res.shortage))
        if res.assignment is not None and self.assisted:
            out.update(bed_priority_violations=[{"kind": p.kind, "unserved_patient": p.unserved_id,
                                                 "unserved_department": p.unserved_department,
                                                 "unserved_level": p.unserved_level,
                                                 "served_patient": p.served_id,
                                                 "served_department": p.served_department,
                                                 "served_level": p.served_level, "severity": p.severity}
                                                for p in res.bed_pairs],
                       nurse_priority_gap_by_tier={f"level_{j}_and_above": _f(g)
                                                   for j, g in res.nurse_tier_gaps.items()})
        return out

    def simulate_allocation(self, beds: dict, nurses: dict) -> dict:
        s = self._alloc_phase("simulate_allocation")
        return {"day": s["day"], "writes": "none", **self._whatif(beds, nurses, self._ctx(s["day"]))}

    def validate_allocation(self, beds: dict, nurses: dict) -> dict:
        s = self._alloc_phase("validate_allocation")
        ctx = self._ctx(s["day"])
        v = validate(beds, nurses, ctx.pool_beds, ctx.pool_nurses, ctx.max_beds, ctx.occupied)
        return {"day": s["day"], "valid": not v, "violations": [{"code": x.code, "message": x.message} for x in v],
                "counts_as_attempt": False}

    def submit_decision(self, beds: dict, nurses: dict, explanation: dict) -> dict:
        s = self._alloc_phase("submit_decision")
        t = s["day"]
        if s["accepted"]:
            raise WorkflowError("a decision was already accepted today. Expected next action: " + self._next_action(s))
        if s["attempts"] >= self.m["retry_limit"]:
            raise WorkflowError(f"the retry limit ({self.m['retry_limit']}) is reached. Expected next action: "
                                + self._next_action(s))
        self._check_explanation(explanation)
        ctx = self._ctx(t)
        with self.store.lock():
            v = validate(beds, nurses, ctx.pool_beds, ctx.pool_nurses, ctx.max_beds, ctx.occupied)
            s["attempts"] += 1
            outcome = "rejected" if v else "accepted"
            self.store.append("decision_history", self._line(
                "allocator", t, attempt=s["attempts"], outcome=outcome, codes=[x.code for x in v],
                messages=[x.message for x in v], beds=beds, nurses=nurses,
                explanation={k: explanation[k] for k in EXPLANATION_FIELDS}))
            if not v:
                self.store.append("allocation_state", self._line("allocator", t, source="ALLOCATOR",
                                                                 beds=beds, nurses=nurses))
                s["accepted"] = True
            self.store.write_state(s)
            self._log(t, "submit_decision", attempt=s["attempts"], outcome=outcome)
        return {"day": t, "outcome": outcome, "attempt": s["attempts"], "retry_limit": self.m["retry_limit"],
                "violations": [{"code": x.code, "message": x.message} for x in v]}

    # ------------------------------------------------------------------ checker
    def _audit_phase(self, tool: str, from_day: int | None = None, to_day: int | None = None) -> tuple[dict, int, int]:
        s = self.store.read_state()
        self._require(s, ("AUDIT",), tool)
        lo = s["day"] - 4 if from_day is None else int(from_day)
        hi = s["day"] if to_day is None else int(to_day)
        if hi > s["day"] or lo < 1 or lo > hi:
            raise WorkflowError(f"period must satisfy 1 <= from_day <= to_day <= {s['day']} (the current day)")
        return s, lo, hi

    # The Deterministic Audit Record is written for evaluation only and is readable by no agent tool
    # (owner decision §11 #29, superseding Log #6).

    def checker_allocation_state(self, from_day: int | None = None, to_day: int | None = None) -> dict:
        s, lo, hi = self._audit_phase("get_allocation_state", from_day, to_day)
        lines = self.store.read("allocation_state")
        return {"period": {"from_day": lo, "to_day": hi},
                "allocations": [{"day": x["day"], "source": x["source"], "beds": x["beds"], "nurses": x["nurses"]}
                                for x in lines if lo <= x["day"] <= hi]}

    def _past_day(self, tool: str, day) -> int:
        s = self.store.read_state()
        self._require(s, ("AUDIT",), tool)
        d = int(day)
        if not 1 <= d <= s["day"]:
            raise WorkflowError(f"day must satisfy 1 <= day <= {s['day']} (the current audit day)")
        return d

    def checker_overflow_queue(self, day) -> dict:
        """The queue as it stood on `day` before that day's decision: present patients without a bed held
        from the previous day."""
        d = self._past_day("get_overflow_queue", day)
        holders = self._holders(d)
        queue = [{"patient_id": p.patient_id, "department": p.department, "complexity": p.complexity,
                  "arrival_day": p.arrival_day, "days_waiting": d - p.arrival_day}
                 for p in self.ds.present(d) if p.patient_id not in holders]
        queue.sort(key=lambda x: (-x["complexity"], x["arrival_day"], x["patient_id"]))
        return {"day": d, "queue": queue}

    def checker_simulate(self, day, beds: dict, nurses: dict) -> dict:
        """What-if on a past day, as it stood that day before its decision. Outcomes only; no writes."""
        d = self._past_day("simulate_allocation", day)
        return {"day": d, "writes": "none", **self._whatif(beds, nurses, self._ctx(d))}

    def checker_decision_history(self, from_day: int | None = None, to_day: int | None = None) -> dict:
        s, lo, hi = self._audit_phase("get_decision_history", from_day, to_day)
        return {"period": {"from_day": lo, "to_day": hi},
                "decisions": [{k: v for k, v in x.items() if k not in ("inputs", "run_id")}
                              for x in self.store.read("decision_history") if lo <= x["day"] <= hi],
                "allocations": [{"day": x["day"], "source": x["source"], "beds": x["beds"], "nurses": x["nurses"]}
                                for x in self.store.read("allocation_state") if lo <= x["day"] <= hi]}

    def checker_observed_state(self, from_day: int | None = None, to_day: int | None = None) -> dict:
        s, lo, hi = self._audit_phase("get_observed_state", from_day, to_day)
        return {"period": {"from_day": lo, "to_day": hi},
                "observed": [{"day": x["day"], **x["observed"]} for x in self.store.read("observed_state")
                             if lo <= x["day"] <= hi]}

    def submit_validation_report(self, report: dict) -> dict:
        s, _, _ = self._audit_phase("submit_validation_report")
        if s["report_received"]:
            raise WorkflowError("a report for this audit was already accepted. Expected next action: "
                                + self._next_action(s))
        for k in ("period", "checked", "issues", "summary"):
            if k not in report:
                raise WorkflowError(f"report is missing '{k}' (fields: period, checked, issues, summary)")
        if not isinstance(report["issues"], list):
            raise WorkflowError("report.issues must be a list (it may be empty)")
        for i, issue in enumerate(report["issues"]):
            if issue.get("category") not in ("violation", "concern", "improvement"):
                raise WorkflowError(f"issues[{i}].category must be violation, concern or improvement")
            if issue.get("severity") not in ("Critical", "Major", "Moderate", "Minor"):
                raise WorkflowError(f"issues[{i}].severity must be Critical, Major, Moderate or Minor")
        with self.store.lock():
            self.store.append("validation_history", self._line("llm_checker", s["day"], kind="report", report=report))
            s["report_received"] = True
            self.store.write_state(s)
            self._log(s["day"], "submit_validation_report", issues=len(report["issues"]))
        return {"accepted": True, "issues_recorded": len(report["issues"])}
