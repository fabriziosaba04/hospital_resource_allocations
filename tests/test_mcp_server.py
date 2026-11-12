"""State machine, record store, role tool sets and information rules (PROJECT_SPEC.md §2–§4, AGENTS.md §2–§3, §8).

Runs the workflow core on the synthetic SMOKE5 fixture, without MCP and without any LLM.
"""

from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path

import pytest

from src.agent import templates
from src.mcp_server.fixture import DATASET_ID, write_fixture
from src.mcp_server.init_run import init_run
from src.mcp_server.server import ROLE_TOOLS, build
from src.mcp_server.workflow import Workflow, WorkflowError
from src.utils.constants import DEPARTMENTS

ROOT = Path(__file__).resolve().parents[1]
EXPL = {k: f"{k} text" for k in ("situation", "information_used", "alternatives", "reasons", "tradeoffs", "uncertainty")}


@pytest.fixture
def wf(tmp_path):
    write_fixture(tmp_path)
    store = init_run(DATASET_ID, "T1", data_root=tmp_path, results_root=tmp_path / "results",
                     check_manifest=False, set_pointer=False)
    return Workflow(store)


def maintain(w: Workflow):
    cur = w.get_allocation_state()["in_effect"]
    return w.submit_decision(cur["beds"], cur["nurses"], EXPL)


def test_full_cycle_with_repair_audit_and_report(wf):
    assert wf.get_workflow_status()["phase"] == "READY"
    for t in range(1, 6):
        wf.advance_day()
        if t in (1, 4):
            out = maintain(wf)
            # day 3 cut the pool, so "maintain" can be infeasible on later days; accept either outcome
            assert out["outcome"] in ("accepted", "rejected")
        wf.end_allocation_phase()
        if t == 5:
            assert wf.get_workflow_status()["phase"] == "AUDIT"
            audit = wf.store.read("deterministic_audit")
            assert [d["day"] for d in audit[0]["days"]] == [1, 2, 3, 4, 5]
            wf.submit_validation_report({"period": {"from_day": 1, "to_day": 5}, "checked": ["all"], "issues": [],
                                         "summary": "test"})
        wf.close_day()
    assert wf.get_workflow_status()["phase"] == "FINISHED"
    srcs = [x["source"] for x in wf.store.read("allocation_state")]
    assert srcs[0] == "initial_rule" and "repair_rule" in srcs
    assert len(wf.store.read("observed_state")) == 5
    stages = [(x["day"], x["stage"]) for x in wf.store.read("bed_assignment_state")]
    assert stages[:2] == [(1, "initial"), (1, "final")] and len(stages) == 6
    assert len(wf.store.read("deterministic_audit")) == 1
    assert [x["kind"] for x in wf.store.read("validation_history")] == ["report"]
    failures = [x for x in wf.store.read("workflow") if x["event"] == "allocator_failure"]
    assert {x["day"] for x in failures} >= {2, 3, 5}


def test_out_of_order_calls_are_rejected_and_logged(wf):
    with pytest.raises(WorkflowError, match="advance_day"):
        wf.close_day()
    wf.advance_day()
    with pytest.raises(WorkflowError, match="allocator"):
        wf.advance_day()
    with pytest.raises(WorkflowError):
        wf.checker_allocation_state()
    with pytest.raises(WorkflowError):
        wf.submit_validation_report({"period": {}, "checked": [], "issues": [], "summary": ""})
    wf.end_allocation_phase()
    with pytest.raises(WorkflowError):
        wf.submit_decision({}, {}, EXPL)
    with pytest.raises(WorkflowError):
        wf.get_observed_state()
    rejected = [x for x in wf.store.read("workflow") if x["event"] == "rejected_call"]
    assert len(rejected) == 6


def test_retry_limit_explanation_and_single_acceptance(wf):
    wf.advance_day()
    bad = {d: 0 for d in DEPARTMENTS}
    with pytest.raises(WorkflowError, match="explanation"):
        wf.submit_decision(bad, bad, {"situation": "x"})            # schema error: not an attempt
    for i in range(3):
        assert wf.submit_decision(bad, bad, EXPL)["outcome"] == "rejected"
    with pytest.raises(WorkflowError, match="retry limit"):
        maintain(wf)
    assert len(wf.store.read("decision_history")) == 3


def test_validate_is_free_and_accepted_once(wf):
    wf.advance_day()
    cur = wf.get_allocation_state()["in_effect"]
    for _ in range(5):
        assert wf.validate_allocation(cur["beds"], cur["nurses"])["valid"]
    assert wf._state()["attempts"] == 0          # derived from the records (Log #80)
    assert maintain(wf)["outcome"] == "accepted"
    with pytest.raises(WorkflowError, match="already accepted"):
        maintain(wf)


def test_integrality_is_not_coerced(wf):
    wf.advance_day()
    cur = wf.get_allocation_state()["in_effect"]
    beds = dict(cur["beds"])
    beds[DEPARTMENTS[0]] = float(beds[DEPARTMENTS[0]])
    out = wf.submit_decision(beds, cur["nurses"], EXPL)
    assert out["outcome"] == "rejected" and {v["code"] for v in out["violations"]} == {"INTEGRALITY"}


def test_simulate_writes_nothing(wf):
    wf.advance_day()
    before = {r: len(wf.store.read(r)) for r in ("allocation_state", "decision_history", "bed_assignment_state")}
    cur = wf.get_allocation_state()["in_effect"]
    out = wf.simulate_allocation(cur["beds"], cur["nurses"])
    assert out["valid"] and "overflow_by_department_and_level" in out
    assert {r: len(wf.store.read(r)) for r in before} == before


def test_no_future_information_in_agent_tools(wf):
    """AGENTS.md §3.2: no discharge_day, and no patient who has not arrived yet."""
    reg = {}
    for line in (Path(wf.m["data_root"]) / "data" / "raw" / DATASET_ID / "patient_registry.csv").read_text().splitlines()[1:]:
        pid, _, _, arr, _ = line.split(",")
        reg[pid] = int(arr)
    for t in range(1, 6):
        wf.advance_day()
        cur = wf.get_allocation_state()["in_effect"]
        outputs = [wf.get_observed_state(), wf.get_allocation_state(), wf.get_decision_history(),
                   wf.get_overflow_queue(), wf.simulate_allocation(cur["beds"], cur["nurses"]),
                   wf.get_workflow_status()]
        text = json.dumps(outputs)
        assert "discharge_day" not in text
        for pid in re.findall(r"P\d{6}", text):
            assert reg[pid] <= t, (t, pid)
        if t == 5:
            wf.end_allocation_phase()
            cur5 = wf.checker_allocation_state()["allocations"][-1]
            checker_out = [wf.checker_decision_history(), wf.checker_observed_state(), wf.checker_allocation_state(),
                           *[wf.checker_overflow_queue(d) for d in range(1, 6)],
                           wf.checker_simulate(3, *_alloc_on(wf, 3))]
            text = json.dumps(checker_out)
            assert "discharge_day" not in text
            for pid in re.findall(r"P\d{6}", text):
                assert reg[pid] <= 5, pid
            with pytest.raises(WorkflowError, match="current day"):
                wf.checker_allocation_state(1, 6)
            break
        wf.end_allocation_phase()
        wf.close_day()


def test_workflow_status_returns_no_hospital_data(wf):
    wf.advance_day()
    assert set(wf.get_workflow_status()) == {"run_id", "day", "horizon", "phase", "expected_next_action"}


def test_each_role_server_registers_exactly_its_tools():
    for role, names in ROLE_TOOLS.items():
        tools = asyncio.run(build(role).list_tools())
        assert sorted(t.name for t in tools) == sorted(names), role


def _frontmatter(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    return text.split("---")[1]


def test_agent_files_whitelist_only_their_role():
    disp = _frontmatter(ROOT / ".claude" / "agents" / "dispatcher.md")
    alloc = _frontmatter(ROOT / ".claude" / "agents" / "allocator.md")
    chk = _frontmatter(ROOT / ".claude" / "agents" / "checker.md")
    assert re.search(r"^tools:\s*mcp__orchestration__\*,\s*Agent\(allocator,\s*checker\)\s*$", disp, re.M)
    assert re.search(r"^tools:\s*mcp__allocator__\*\s*$", alloc, re.M)
    assert re.search(r"^tools:\s*mcp__checker__\*\s*$", chk, re.M)
    for fm, role in ((alloc, "allocator"), (chk, "checker")):
        assert re.search(r"^omitClaudeMd:\s*true\s*$", fm, re.M)
        assert f"--role" in fm and role in fm
    mcp = json.loads((ROOT / ".mcp.json").read_text())
    assert list(mcp["mcpServers"]) == ["orchestration"]


def test_dispatcher_body_contains_the_fixed_templates_verbatim():
    body = (ROOT / ".claude" / "agents" / "dispatcher.md").read_text(encoding="utf-8").split("---", 2)[2]
    for t in (templates.ALLOCATE, templates.AUDIT):
        assert t in body


FORBIDDEN_IN_PROMPTS = ["arrival rate", "λ", "lognormal", "surge", "shock schedule", "burn-in", "seed",
                        "generation_config", "12–19", "23–25", "16–20", "8–10", "discharge_day of"]


def test_prompts_do_not_leak_generation_information():
    for name in ("allocator.md", "checker.md", "dispatcher.md"):
        body = (ROOT / ".claude" / "agents" / name).read_text(encoding="utf-8").lower()
        for s in FORBIDDEN_IN_PROMPTS:
            assert s.lower() not in body, (name, s)


def _alloc_on(w: Workflow, day: int):
    x = [a for a in w.store.read("allocation_state") if a["day"] <= day][-1]
    return x["beds"], x["nurses"]


LABEL_KEYS = ("bed_priority_violations", "nurse_priority_gap_by_tier", "severity", "unserved")
AUDIT_KEYS = ("bed_gap", "nurse_lex_floor_h", "nurse_net_h", "f1_inversions", "pairs", "issues", "tau_beds",
              "bed_floor", "hard_constraint_errors")


def _run_to_audit(w: Workflow):
    for t in range(1, 6):
        w.advance_day()
        w.end_allocation_phase()
        if t < 5:
            w.close_day()


def test_whatif_returns_outcomes_only(wf):
    """Owner decision §11 #29: no clinical-priority labels, counts or severities, and no A2 tier gaps."""
    wf.advance_day()
    out = wf.simulate_allocation(*_alloc_on(wf, 1))
    assert {"valid", "violations", "overflow_by_department_and_level", "overflow_patients",
            "nurse_covered_by_department_and_level", "nurse_shortage_by_department_and_level"} <= set(out)
    text = json.dumps(out)
    assert not any(k in text for k in LABEL_KEYS)
    assert all("days_waiting" in p for p in out["overflow_patients"])


def test_validate_and_rejections_report_hard_constraints_only(wf):
    wf.advance_day()
    bad = {d: 0 for d in DEPARTMENTS}
    v = wf.validate_allocation(bad, bad)
    r = wf.submit_decision(bad, bad, EXPL)
    for out in (v, r):
        assert {x["code"] for x in out["violations"]} <= {"CONSERVATION_BEDS", "CONSERVATION_NURSES", "BOUNDS",
                                                          "INTEGRALITY", "EVICTION", "SHOCK_OVERCUT"}
        assert not any(k in json.dumps(out) for k in LABEL_KEYS)


def test_assisted_flag_exposes_labels_and_is_recorded(tmp_path):
    write_fixture(tmp_path)
    store = init_run(DATASET_ID, "A1", data_root=tmp_path, results_root=tmp_path / "results",
                     check_manifest=False, set_pointer=False, expose_violation_labels=True)
    w = Workflow(store)
    assert w.m["expose_violation_labels"] is True
    w.advance_day()
    out = w.simulate_allocation(*_alloc_on(w, 1))
    assert "bed_priority_violations" in out and "nurse_priority_gap_by_tier" in out


def test_default_run_records_labels_off(wf):
    assert wf.m["expose_violation_labels"] is False


def test_checker_past_day_tools_refuse_the_future_and_write_nothing(wf):
    _run_to_audit(wf)
    files = ("allocation_state", "decision_history", "bed_assignment_state", "observed_state", "deterministic_audit")
    before = {r: len(wf.store.read(r)) for r in files}
    q2 = wf.checker_overflow_queue(2)
    assert q2["day"] == 2 and all(p["arrival_day"] <= 2 for p in q2["queue"])
    out = wf.checker_simulate(2, *_alloc_on(wf, 2))
    assert out["valid"] and not any(k in json.dumps(out) for k in LABEL_KEYS)
    for bad in (6, 0):
        with pytest.raises(WorkflowError, match="current audit day"):
            wf.checker_overflow_queue(bad)
        with pytest.raises(WorkflowError, match="current audit day"):
            wf.checker_simulate(bad, *_alloc_on(wf, 2))
    assert {r: len(wf.store.read(r)) for r in files} == before


def test_past_day_whatif_matches_the_recorded_outcome(wf):
    """Replaying day d with the allocation in effect that day reproduces the stored overflow."""
    _run_to_audit(wf)
    for d in range(1, 6):
        out = wf.checker_simulate(d, *_alloc_on(wf, d))
        stored = [x for x in wf.store.read("bed_assignment_state") if x["day"] == d and x["stage"] == "final"][0]
        assert {p["patient_id"] for p in out["overflow_patients"]} == \
            {pid for pid, v in stored["patients"].items() if v["status"] == "overflow"}


def test_no_agent_tool_can_read_the_deterministic_audit(wf):
    """Owner decision §11 #29: the audit is stored for evaluation only."""
    assert not any("deterministic_audit" in t for names in ROLE_TOOLS.values() for t in names)
    src = (ROOT / "src" / "mcp_server" / "workflow.py").read_text(encoding="utf-8")
    assert 'read("deterministic_audit")' not in src
    _run_to_audit(wf)
    assert wf.store.read("deterministic_audit")                      # it was written...
    outs = [wf.checker_decision_history(), wf.checker_observed_state(), wf.checker_allocation_state(),
            wf.checker_overflow_queue(5), wf.checker_simulate(5, *_alloc_on(wf, 5)), wf.get_workflow_status()]
    text = json.dumps(outs)
    assert not any(f'"{k}"' in text for k in AUDIT_KEYS)              # ...and no tool returns its content



def test_checker_taxonomy_covers_every_agent_attributable_audit_type():
    """CHECKER-versus-audit matching works on `type` names (EVALUATION_PLAN.md §4). Every agent-attributable
    type the audit emits must appear in the source and in the prompt's taxonomy table."""
    import src.evaluation.audit as audit_mod
    import src.evaluation.metrics as metrics_mod
    src = (Path(audit_mod.__file__).read_text(encoding="utf-8") + Path(metrics_mod.__file__).read_text(encoding="utf-8")
           + (ROOT / "src" / "mcp_server" / "workflow.py").read_text(encoding="utf-8"))
    audit_types = {"hard_constraint_in_effect": '"hard_constraint_in_effect"', "rejected_submission": '"rejected_submission"',
                   "allocator_failure_day": '"allocator_failure_day"', "nurse_gap": '"nurse_gap"',
                   "f1_inversion": '"f1_inversion"', "reallocation_without_effect": '"reallocation_without_effect"',
                   "bed_displaced": '"displaced"', "bed_empty": '"empty"', "bed_shock_cut": '"shock_cut"',
                   "beds_reversal": '{res}_reversal', "nurses_reversal": '{res}_reversal'}
    for name, literal in audit_types.items():
        assert literal in src, f"audit no longer emits {name}"
    body = (ROOT / ".claude" / "agents" / "checker.md").read_text(encoding="utf-8")
    listed = {n for pair in re.findall(r"^\| `([a-z0-9_]+)`(?:, `([a-z0-9_]+)`)? \|", body, re.M) for n in pair if n}
    assert set(audit_types) <= listed, set(audit_types) - listed
    assert {"explanation_inaccuracy", "information_leak", "inconsistency", "other"} <= listed
