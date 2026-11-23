"""Step 5: verify that the four agent runs in the repository are byte-identical to what was copied back.

    uv run python src/05_verify_copy_back.py            # repository only (--sums-only): any clone can run this
    uv run python src/05_verify_copy_back.py --full     # also against the run clone and the Claude Code session
                                                        # folders (owner's machine only)
    uv run python src/05_verify_copy_back.py --save     # also write the output to results/verification/copy_back/

Thin wrapper around tests/manual/verify_copy_back_independent.py, which imports nothing from src/ on purpose.
Saved outputs replace the repository root by <repo> and the home folder by ~ (no machine paths published).
"""
import argparse
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.utils.paths import guard_write  # noqa: E402

SCRIPT = ROOT / "tests" / "manual" / "verify_copy_back_independent.py"
RUNS = ["R1", "R2", "R3", "STRESS1"]

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", action="store_true")
    ap.add_argument("--save", action="store_true")
    a = ap.parse_args()
    mode = "full" if a.full else "sums_only"
    status = 0
    for run in RUNS:
        cmd = [sys.executable, str(SCRIPT), run] + ([] if a.full else ["--sums-only"])
        p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", cwd=ROOT)
        out = p.stdout + p.stderr
        print(out, end="")
        status |= p.returncode
        if a.save:
            text = out
            for path, label in ((str(ROOT), "<repo>"), (str(Path.home()), "~")):
                text = text.replace(path.replace("\\", "\\\\"), label).replace(path, label)   # repr and plain
            dst = guard_write(ROOT / "results" / "verification" / "copy_back" / f"{run}_{mode}.txt")
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(f"# {SCRIPT.relative_to(ROOT).as_posix()} {run}{'' if a.full else ' --sums-only'}"
                           f" | {date.today().isoformat()} | exit {p.returncode}\n" + text,
                           encoding="utf-8", newline="\n")
    print("ALL RUNS:", "OK" if status == 0 else "FAIL")
    sys.exit(status)
