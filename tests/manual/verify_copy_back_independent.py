"""Independent check of an agent run's copy-back (manual; never collected by pytest).

    uv run python tests/manual/verify_copy_back_independent.py RUN_ID [--repo PATH] [--clone PATH]

Compares, by SHA-256:
  1. the repository's run folders (results/allocations/RUN, results/evaluations/RUN)
     with the clone's, file by file (the capture under transcripts/subagents/ is
     repository-only and is checked in step 2);
  2. the subagent capture (results/allocations/RUN/transcripts/subagents/) with the
     Claude Code session folder it was copied from (~/.claude/projects/*/<session_id>),
     and with its own SHA256SUMS.json.

Independence is the point: this script imports nothing from src/ and does its own
Windows extended-length (\\\\?\\) prefixing instead of src.utils.paths.long_path.
It only reads. Exit status 0 if every comparison matches, 1 otherwise.

Kept from the scratch script used for the R3 and STRESS1 copy-back checks
(2026-11-22), generalised to take the run id as an argument.
"""
import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

DEFAULT_REPO = Path(__file__).resolve().parents[2]
DEFAULT_CLONE = Path("C:/hra-runs/hospital_resource_allocations")


def lp(p):
    """Own extended-length form (Windows); identity elsewhere."""
    if os.name != "nt":
        return os.path.abspath(str(p))
    return "\\\\?\\" + os.path.abspath(str(p)).replace("/", "\\")


def plain(full):
    return full[4:] if full.startswith("\\\\?\\") else full


def hashfull(full):
    with open(full, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def tree(root, skip=None):
    out = {}
    base = lp(root)
    for dp, _dn, fn in os.walk(base):
        for f in fn:
            full = os.path.join(dp, f)
            rel = os.path.relpath(full, base).replace("\\", "/")
            if skip and rel.startswith(skip):
                continue
            out[rel] = full
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("run_id")
    ap.add_argument("--repo", type=Path, default=DEFAULT_REPO)
    ap.add_argument("--clone", type=Path, default=DEFAULT_CLONE)
    a = ap.parse_args()
    REPO, CLONE, RUN = a.repo, a.clone, a.run_id
    ok = True
    print(f"run {RUN}\n  repo  {REPO}\n  clone {CLONE}")

    # 1. run folders
    for kind in ("allocations", "evaluations"):
        c = tree(CLONE / "results" / kind / RUN)
        r = tree(REPO / "results" / kind / RUN, skip="transcripts/subagents/")
        matched = sum(1 for k in c if k in r and hashfull(c[k]) == hashfull(r[k]))
        repo_only = sorted({k.split("/")[0] for k in set(r) - set(c)})
        print(f"{kind}: matched {matched}/{len(c)} clone files; repo-only entries: {repo_only}")
        ok &= bool(c) and matched == len(c)

    # 2. capture vs session folder
    launch = "".join(
        p.read_text(encoding="utf-8")
        for p in sorted((CLONE / "results/allocations" / RUN / "transcripts").glob("launch-*.jsonl"))
    )
    sids = list(dict.fromkeys(re.findall(r'"session_id":"([0-9a-f-]{36})"', launch)))
    proj = Path.home() / ".claude" / "projects"
    sess = [p for s in sids for p in proj.glob(f"*/{s}") if (p / "subagents").is_dir()]
    print("sessions:", sids, "folders:", [str(p) for p in sess])
    if len(sess) != 1:
        print("FAIL: expected exactly one session folder with subagents/")
        return 1
    S = sess[0]
    src = {}  # capture-relative path -> (type, path)
    for f in (S / "subagents").glob("*.meta.json"):
        kind = json.loads(f.read_text(encoding="utf-8"))["agentType"]
        t = f.with_name(f.name[: -len(".meta.json")] + ".jsonl")
        src[f"{kind}/{f.name}"] = ("meta", f)
        src[f"{kind}/{t.name}"] = ("transcript", t)
    alloc_text = "".join(
        v[1].read_text(encoding="utf-8")
        for k, v in src.items()
        if k.startswith("allocator/") and v[0] == "transcript"
    )
    other_sub = [
        f.name for f in (S / "subagents").iterdir()
        if not (f.name.endswith(".meta.json") or f.name.endswith(".jsonl"))
    ]
    print("other entries in session subagents/:", other_sub)
    tr = S / "tool-results"
    unclassified = []
    if tr.is_dir():
        for f in os.listdir(lp(tr)):
            if f.startswith("mcp-allocator-") or Path(f).stem in alloc_text:
                src[f"allocator/tool-results/{f}"] = ("tool-result", tr / f)
            elif f.startswith("mcp-checker-"):
                src[f"checker/tool-results/{f}"] = ("tool-result", tr / f)
            else:
                unclassified.append(f)
    print("unclassified tool-results in session:", unclassified)
    dst_root = REPO / "results/allocations" / RUN / "transcripts/subagents"
    dst = {k: v for k, v in tree(dst_root).items() if k != "SHA256SUMS.json"}
    counts = {}
    for k, (typ, _) in src.items():
        counts.setdefault((k.split("/")[0], typ), [0, 0])[0] += 1
    for k in dst:
        typ = "tool-result" if "/tool-results/" in k else ("meta" if k.endswith(".meta.json") else "transcript")
        counts.setdefault((k.split("/")[0], typ), [0, 0])[1] += 1
    for key in sorted(counts):
        print(f"  {key[0]:9s} {key[1]:11s} session {counts[key][0]:3d}  repo {counts[key][1]:3d}")
    missing = sorted(set(src) - set(dst))
    extra = sorted(set(dst) - set(src))
    common = set(src) & set(dst)
    mism = [k for k in common if hashfull(lp(src[k][1])) != hashfull(dst[k])]
    print(f"capture vs session: matched {len(common) - len(mism)}/{len(src)}; "
          f"missing {len(missing)}, extra {len(extra)}, mismatched {len(mism)}",
          missing[:3], extra[:3], mism[:3])
    ok &= not missing and not extra and not mism and bool(src)
    with open(lp(dst_root / "SHA256SUMS.json"), encoding="utf-8") as fh:
        sums = json.load(fh)
    files = sums["files"]
    fs = ({k: (v if isinstance(v, str) else v.get("sha256")) for k, v in files.items()}
          if isinstance(files, dict) else files)
    sm = sum(1 for k, v in fs.items() if k in dst and hashfull(dst[k]) == v)
    not_on_disk = len(set(fs) - set(dst))
    not_listed = len(set(dst) - set(fs))
    print(f"SHA256SUMS.json: matched {sm}/{len(dst)} on disk ({len(fs)} entries); "
          f"keys not on disk {not_on_disk}; on disk not listed {not_listed}; "
          f"recorded mismatches {sums.get('hash_mismatches')}")
    ok &= sm == len(dst) == len(fs) and not not_on_disk and not not_listed
    longest = max(dst.values(), key=lambda p: len(plain(p)))
    print("longest destination:", len(plain(longest)), plain(longest))
    print("RESULT:", "OK" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
