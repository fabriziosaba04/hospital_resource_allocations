"""allocator_digest: CHECKER files are separated by metadata and never reach the digest (§11 #58, Log #98)."""

import json

import pytest

from src.evaluation.allocator_digest import digest, preserve

EXPL = {"situation": "s", "information_used": "i", "alternatives": "a", "reasons": "r", "tradeoffs": "t",
        "uncertainty": "u"}


def _transcript(ts, text, explanation):
    call = {"type": "tool_use", "id": f"toolu_{ts}", "name": "mcp__allocator__submit_decision",
            "input": {"beds": {}, "nurses": {}, "explanation": explanation}}
    return "\n".join(json.dumps(o) for o in [
        {"type": "user", "timestamp": ts, "message": {"content": "dispatch"}},
        {"type": "assistant", "timestamp": ts, "message": {"content": [{"type": "text", "text": text}, call]}},
        {"type": "user", "timestamp": ts, "message": {"content": [
            {"type": "tool_result", "tool_use_id": f"toolu_{ts}", "content": [{"type": "text", "text": "ok"}]}]}},
    ]) + "\n"


def _session(tmp_path, alloc_expl):
    s = tmp_path / "session"
    (s / "subagents").mkdir(parents=True)
    (s / "tool-results").mkdir()
    for name, kind, ts, text, ex in [("a1", "allocator", "2026-01-01T00:00:01", "ALLOC-ONE", alloc_expl[0]),
                                     ("c1", "checker", "2026-01-01T00:00:02", "CHECKER-SECRET", EXPL),
                                     ("a2", "allocator", "2026-01-01T00:00:03", "ALLOC-TWO", alloc_expl[1])]:
        (s / "subagents" / f"agent-{name}.meta.json").write_text(json.dumps({"agentType": kind}))
        (s / "subagents" / f"agent-{name}.jsonl").write_text(_transcript(ts, text, ex))
    (s / "tool-results" / "mcp-checker-x-1.txt").write_text("CHECKER-SECRET")
    (s / "tool-results" / "mcp-allocator-y-1.txt").write_text("big")
    return s


def _run(tmp_path, explanations):
    run = tmp_path / "results" / "allocations" / "R"
    run.mkdir(parents=True)
    (run / "decision_history.jsonl").write_text("".join(
        json.dumps({"day": d, "writer": "allocator", "outcome": "accepted", "beds": {}, "nurses": {},
                    "explanation": e}) + "\n" for d, e in enumerate(explanations, 1)))
    return tmp_path / "results"


def test_split_and_digest_exclude_checker(tmp_path):
    e1, e2 = dict(EXPL, situation="day1"), dict(EXPL, situation="day2")
    s = _session(tmp_path, [e1, e2])
    res = _run(tmp_path, [e1, e2])
    m = preserve(s, "R", res)
    assert m["hash_mismatches"] == []
    assert {r.split("/")[0] for r in m["files"]} == {"allocator", "checker"}
    assert "checker/tool-results/mcp-checker-x-1.txt" in m["files"]
    days = digest("R", res)
    texts = [p.read_text(encoding="utf-8") for p in days]
    assert len(days) == 2 and "ALLOC-ONE" in texts[0] and "ALLOC-TWO" in texts[1]
    assert all("CHECKER-SECRET" not in t for t in texts)


def test_digest_refuses_day_mismatch(tmp_path):
    e1, e2 = dict(EXPL, situation="day1"), dict(EXPL, situation="day2")
    s = _session(tmp_path, [e2, e1])          # transcripts in the wrong order for the records
    res = _run(tmp_path, [e1, e2])
    preserve(s, "R", res)
    with pytest.raises(SystemExit):
        digest("R", res)
