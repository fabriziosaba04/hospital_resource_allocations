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


# --- Log #116, R56: tool results at a destination of 260+ characters, and resuming a partial capture ---

REAL_NAME = "mcp-allocator-get_decision_history-1795337149486-we0rir.txt"   # R2's shape (random suffix)


def _deep_results(tmp_path):
    """A results root placed like R2's: the tool-results folder stays under Windows' 248-character directory
    limit (197 in R2), while the file inside it exceeds MAX_PATH (260 in R2)."""
    tail = len("/results/allocations/R/transcripts/subagents/allocator/tool-results")
    res = tmp_path / ("d" * (235 - len(str(tmp_path.absolute())) - tail - 1)) / "results"
    folder = res / "allocations" / "R" / "transcripts" / "subagents" / "allocator" / "tool-results"
    assert len(str(folder.absolute())) < 248 and len(str((folder / REAL_NAME).absolute())) > 260
    return res


def _session_with_real_names(tmp_path):
    s = _session(tmp_path, [EXPL, EXPL])
    (s / "tool-results" / REAL_NAME).write_text("history")
    (s / "tool-results" / "toolu_011LQ3awJsWrjtes7ZeApqRY.json").write_text("{}")
    return s


def test_preserve_copies_tool_results_beyond_max_path(tmp_path):
    from src.utils.paths import long_path
    s, res = _session_with_real_names(tmp_path), _deep_results(tmp_path)
    m = preserve(s, "R", res)
    assert m["hash_mismatches"] == []
    rel = f"allocator/tool-results/{REAL_NAME}"
    assert rel in m["files"]
    dst = res / "allocations" / "R" / "transcripts" / "subagents" / rel
    assert long_path(dst).read_text() == "history"


def test_preserve_resume_completes_a_partial_capture(tmp_path):
    from src.utils.paths import long_path
    s, res = _session_with_real_names(tmp_path), _deep_results(tmp_path)
    out = res / "allocations" / "R" / "transcripts" / "subagents"
    # the state R2's failed attempt left: transcripts and metadata copied, an empty tool-results folder, no manifest
    for kind, name in (("allocator", "agent-a1"), ("checker", "agent-c1"), ("allocator", "agent-a2")):
        long_path(out / kind / "tool-results").mkdir(parents=True, exist_ok=True)
        for ext in (".meta.json", ".jsonl"):
            (out / kind / f"{name}{ext}").write_bytes((s / "subagents" / f"{name}{ext}").read_bytes())
    with pytest.raises(SystemExit, match="never overwritten"):
        preserve(s, "R", res)                            # without resume: refuses as before
    m = preserve(s, "R", res, resume=True)
    assert m["hash_mismatches"] == [] and m["resumed"] == {"kept_verified": 6, "copied": 4}
    assert len(m["files"]) == 10
    with pytest.raises(SystemExit, match="complete"):
        preserve(s, "R", res, resume=True)               # a complete capture is never touched again


def test_preserve_resume_never_overwrites_different_content(tmp_path):
    s, res = _session_with_real_names(tmp_path), _deep_results(tmp_path)
    out = res / "allocations" / "R" / "transcripts" / "subagents" / "allocator"
    out.mkdir(parents=True)
    (out / "agent-a1.jsonl").write_text("tampered")
    with pytest.raises(SystemExit, match="differ from the source"):
        preserve(s, "R", res, resume=True)
    assert (out / "agent-a1.jsonl").read_text() == "tampered"
    assert not (out.parent / "SHA256SUMS.json").exists()


def test_preserve_resume_refuses_files_outside_the_plan(tmp_path):
    s, res = _session_with_real_names(tmp_path), _deep_results(tmp_path)
    out = res / "allocations" / "R" / "transcripts" / "subagents" / "allocator"
    out.mkdir(parents=True)
    (out / "stray.txt").write_text("x")
    with pytest.raises(SystemExit, match="not in the capture plan"):
        preserve(s, "R", res, resume=True)
