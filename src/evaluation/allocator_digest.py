"""ALLOCATOR-only view of a run, for claim extraction (owner access rule §11 #58, Log #98).

    uv run python -m src.evaluation.allocator_digest preserve <claude session dir> [<more session dirs>] <run_id>
    uv run python -m src.evaluation.allocator_digest digest <run_id>

`preserve` copies the per-subagent transcripts Claude Code wrote for the run session (outside the
repository, `~/.claude/projects/<clone>/<session>/`) into `results/allocations/<run>/transcripts/subagents/`,
split by the `agentType` of each `.meta.json` into `allocator/` and `checker/`. Spilled tool results
(`tool-results/`) go to `allocator/` if their name starts with `mcp-allocator-` or their tool-use id appears
in an ALLOCATOR transcript, to `checker/` if it starts with `mcp-checker-`, and otherwise to `unclassified/`.
**Nothing is opened except the `.meta.json` files and the ALLOCATOR transcripts** (the id search). A SHA-256
manifest is written next to them.

`digest` reads **only** `subagents/allocator/*.jsonl` and `decision_history.jsonl` (writer ALLOCATOR), and
writes `results/evaluations/<run>/allocator_digest/day_NN.md`: every tool call and the tool result the
ALLOCATOR received, in order, then the six explanation fields of the accepted decision. Day attribution:
transcripts sorted by first timestamp; each must contain a `submit_decision` whose explanation equals
`decision_history`'s for that day, or the digest refuses. Thinking blocks and harness attachments are left out.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

from .dataset import ROOT

FIELDS = ("situation", "information_used", "alternatives", "reasons", "tradeoffs", "uncertainty")


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def preserve(session_dirs, run_id: str, results: Path = ROOT / "results") -> dict:
    """`session_dirs`: one Claude Code session folder, or a list of them (one per launch of a resumed run)."""
    dirs = [Path(session_dirs)] if isinstance(session_dirs, (str, Path)) else [Path(d) for d in session_dirs]
    out = results / "allocations" / run_id / "transcripts" / "subagents"
    if out.exists():
        raise SystemExit(f"{out} already exists: never overwritten")
    kinds: dict[str, list[Path]] = {}
    for sub in (d / "subagents" for d in dirs):
        for meta in sorted(sub.glob("*.meta.json")):
            kind = json.loads(meta.read_text(encoding="utf-8"))["agentType"]
            if kind not in ("allocator", "checker"):
                raise SystemExit(f"unexpected agentType {kind!r} in {meta.name}")
            kinds.setdefault(kind, []).append(meta)
    alloc_text = "".join((m.with_name(m.name[:-len(".meta.json")] + ".jsonl")).read_text(encoding="utf-8")
                         for m in kinds.get("allocator", []))
    origin: dict[str, Path] = {}                         # copied path (relative to out) -> source file

    def put(src: Path, rel: str) -> None:
        if rel in origin:
            raise SystemExit(f"{rel} appears in two sessions")
        (out / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, out / rel)
        origin[rel] = src

    for kind, metas in kinds.items():
        (out / kind).mkdir(parents=True, exist_ok=True)
        for m in metas:
            put(m, f"{kind}/{m.name}")
            t = m.with_name(m.name[:-len(".meta.json")] + ".jsonl")
            put(t, f"{kind}/{t.name}")
    for tr in (d / "tool-results" for d in dirs):
        for f in sorted(tr.glob("*")) if tr.is_dir() else []:
            if f.name.startswith("mcp-allocator-") or f.stem in alloc_text:
                kind = "allocator"
            elif f.name.startswith("mcp-checker-"):
                kind = "checker"
            else:
                kind = "unclassified"
            put(f, f"{kind}/tool-results/{f.name}")
    out.mkdir(parents=True, exist_ok=True)
    manifest = {"source": [str(d.resolve()) for d in dirs] if len(dirs) > 1 else str(dirs[0].resolve()),
                "files": {rel: _sha(out / rel) for rel in sorted(origin)}}
    manifest["hash_mismatches"] = [r for r, h in manifest["files"].items() if _sha(origin[r]) != h]
    (out / "SHA256SUMS.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    return manifest


def _text(content) -> str:
    if isinstance(content, str):
        return content
    return "\n".join(c.get("text", json.dumps(c)) if isinstance(c, dict) else str(c) for c in content)


def _events(path: Path) -> tuple[str, list[tuple[str, str, str]]]:
    """(first timestamp, [(kind, name, text)]) for tool calls, tool results and final texts."""
    ev, first = [], None
    names = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        o = json.loads(line)
        if o.get("type") not in ("assistant", "user"):
            continue
        first = first or o.get("timestamp")
        content = o.get("message", {}).get("content")
        if not isinstance(content, list):
            continue
        for c in content:
            if c.get("type") == "tool_use":
                names[c["id"]] = c["name"]
                ev.append(("call", c["name"], json.dumps(c.get("input", {}), indent=1, ensure_ascii=False)))
            elif c.get("type") == "tool_result":
                ev.append(("result", names.get(c.get("tool_use_id"), "?"), _text(c.get("content", ""))))
            elif c.get("type") == "text" and o["type"] == "assistant":
                ev.append(("text", "", c["text"]))
    return first or "", ev


def digest(run_id: str, results: Path = ROOT / "results") -> list[Path]:
    run = results / "allocations" / run_id
    decisions = {}
    for line in (run / "decision_history.jsonl").read_text(encoding="utf-8").splitlines():
        d = json.loads(line)
        if d.get("writer") != "allocator":
            raise SystemExit(f"decision_history line not written by the ALLOCATOR: writer={d.get('writer')!r}")
        if d.get("outcome") == "accepted":
            decisions[d["day"]] = d
    trs = sorted(((*_events(p), p) for p in (run / "transcripts" / "subagents" / "allocator").glob("*.jsonl")))
    if len(trs) != len(decisions):
        raise SystemExit(f"{len(trs)} ALLOCATOR transcripts for {len(decisions)} accepted decisions")
    out_dir = results / "evaluations" / run_id / "allocator_digest"
    out_dir.mkdir(parents=True, exist_ok=False)
    written = []
    for day, (first, ev, path) in zip(sorted(decisions), trs):
        dec = decisions[day]
        subs = [json.loads(t) for k, n, t in ev if k == "call" and n.endswith("submit_decision")]
        if not any(s.get("explanation") == dec["explanation"] for s in subs):
            raise SystemExit(f"day {day}: transcript {path.name} has no submit_decision matching decision_history")
        lines = [f"# {run_id} day {day}", "", f"Transcript: `{path.name}` (first message {first})", ""]
        for i, (k, n, t) in enumerate(ev, 1):
            head = {"call": f"## {i}. CALL {n}", "result": f"## {i}. RESULT received ({n})", "text": f"## {i}. TEXT"}[k]
            lines += [head, "", "```", t, "```", ""]
        lines += ["## Accepted decision (decision_history)", "",
                  "```", json.dumps({"beds": dec["beds"], "nurses": dec["nurses"]}, ensure_ascii=False), "```", ""]
        for f in FIELDS:
            lines += [f"### {f}", "", str(dec["explanation"].get(f, "")), ""]
        p = out_dir / f"day_{day:02d}.md"
        p.write_text("\n".join(lines), encoding="utf-8", newline="\n")
        written.append(p)
    return written


if __name__ == "__main__":
    if sys.argv[1] == "preserve":
        m = preserve([Path(a) for a in sys.argv[2:-1]], sys.argv[-1])
        print(json.dumps({"files": len(m["files"]), "hash_mismatches": m["hash_mismatches"],
                          "by_folder": {k: sum(1 for r in m["files"] if r.startswith(k + "/"))
                                        for k in ("allocator", "checker", "unclassified")}}, indent=2))
    elif sys.argv[1] == "digest":
        print(len(digest(sys.argv[2])), "day files written")
