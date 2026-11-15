"""Run report across launches (Log #92): a launch cut off by a usage limit, resumed in a new launch, keeps the
per-day attribution of subagent work."""

from __future__ import annotations

import json

from src.evaluation.run_report import transcript_stats


def _status(tid, day, phase):
    text = json.dumps({"run_id": "X", "day": day, "horizon": 10, "phase": phase, "expected_next_action": "..."})
    return {"type": "user", "parent_tool_use_id": None,
            "message": {"content": [{"type": "tool_result", "tool_use_id": tid, "content": [{"type": "text",
                                                                                            "text": text}]}]}}


def _use(tid, name, parent=None, **inp):
    return {"type": "assistant", "parent_tool_use_id": parent,
            "message": {"content": [{"type": "tool_use", "id": tid, "name": name, "input": inp}]}}


def _write(path, events):
    path.write_text("".join(json.dumps(e) + "\n" for e in events), encoding="utf-8")


def test_day_survives_a_cut_off_launch(tmp_path):
    t = tmp_path / "transcripts"
    t.mkdir()
    # launch 1: status day 0, advance_day sent but the session is cut before its result arrives
    _write(t / "launch-1.jsonl", [_use("a", "mcp__orchestration__get_workflow_status"), _status("a", 0, "READY"),
                                  _use("b", "mcp__orchestration__advance_day")])
    # launch 2 (resume): the server is at day 1, ALLOCATION; the dispatcher invokes the ALLOCATOR
    _write(t / "launch-2.jsonl", [_use("c", "mcp__orchestration__get_workflow_status"),
                                  _status("c", 1, "ALLOCATION"),
                                  _use("d", "Agent", subagent_type="allocator"),
                                  {"type": "system", "subtype": "task_notification", "tool_use_id": "d",
                                   "usage": {"total_tokens": 1234, "duration_ms": 5000}}])
    # launches 3..10 exist and must sort numerically (launch-10 last), so day 2 work lands on day 2
    for k in range(3, 10):
        _write(t / f"launch-{k}.jsonl", [])
    _write(t / "launch-10.jsonl", [_use("e", "mcp__orchestration__advance_day"), _status("e", 2, "ALLOCATION"),
                                   _use("f", "Agent", subagent_type="allocator"),
                                   {"type": "system", "subtype": "task_notification", "tool_use_id": "f",
                                    "usage": {"total_tokens": 99, "duration_ms": 1000}}])
    per_day = transcript_stats(tmp_path)["per_day"]
    assert per_day[1]["allocator_tokens"] == 1234 and per_day[1]["allocator_invocations"] == 1
    assert per_day[2]["allocator_tokens"] == 99
    assert 0 not in per_day


def test_wall_clock_excludes_the_gap_between_launches():
    """Log #96: DRY3-RESUME day 1 was advanced in launch 1 (2026-11-14) and closed in launch 2 (next morning)."""
    from datetime import datetime, timezone
    from src.evaluation.run_report import active_seconds

    def t(h, m, s, d=15):
        return datetime(2026, 11, d, h, m, s, tzinfo=timezone.utc)
    spans = [(t(16, 50, 48, 14), t(16, 51, 6, 14)), (t(7, 28, 51), t(7, 30, 32)), (t(7, 30, 53), t(7, 33, 40))]
    assert active_seconds(t(16, 50, 55, 14), t(7, 29, 24), spans) == (11 + 33, 2)
    assert active_seconds(t(7, 30, 3), t(7, 31, 0), spans) == (29 + 7, 2)
    assert active_seconds(t(7, 31, 2), t(7, 31, 37), spans) == (35, 1)
    assert active_seconds(t(7, 0, 0), t(7, 0, 10), []) == (10, 1)
