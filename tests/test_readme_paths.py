"""Every path cited in the grader-facing documents exists (owner, 2026-11-23: the README will keep changing).

Checked: markdown links `[..](path)` and back-quoted repository paths (`src/...`, `results/...`, ...), in README.md,
results/README.md and the other READMEs under results/, plan.md, mistakes.md, ERROR_ANALYSIS.md and REFLECTION.md.
A path is resolved against the document's folder, then against the repository root. Placeholders (`<run_id>`,
`B?`, `…`) and the uncommitted results/analysis/recomputed/ are skipped.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from src.evaluation.dataset import ROOT

DOCS = ["README.md", "plan.md", "mistakes.md", "ERROR_ANALYSIS.md", "REFLECTION.md",
        *sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / "results").glob("*README.md")),
        *sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / "results").glob("*/README.md"))]
LINK = re.compile(r"\]\(([^)\s]+)\)")
TICK = re.compile(r"`([^`\s]+)`(?!\])")          # link text is checked through its target
TOPS = ("src/", "tests/", "docs/", "data/", "results/", ".claude/", "allocations/", "evaluations/", "analysis/",
        "figures/", "verification/", "development/", "dry_runs/", "copy_back/", "pre_run/")
ROOT_FILES = {"README.md", "CLAUDE.md", "plan.md", "mistakes.md", "ERROR_ANALYSIS.md", "REFLECTION.md",
              ".gitattributes", ".gitignore", ".mcp.json", "pyproject.toml", "uv.lock"}
PLACEHOLDER = re.compile(r"[<>?*…{}]|\.\.\.")


def cited(doc: Path) -> set[str]:
    text = doc.read_text(encoding="utf-8")
    out = {m.split("#")[0] for m in LINK.findall(text) if not m.startswith(("http://", "https://", "#", "mailto:"))}
    out |= {t for t in TICK.findall(text) if t.startswith(TOPS) or t in ROOT_FILES}
    return {p for p in out if p and not PLACEHOLDER.search(p) and "recomputed" not in p}


@pytest.mark.parametrize("name", DOCS)
def test_every_cited_path_exists(name):
    doc = ROOT / name
    assert doc.is_file(), name
    missing = [p for p in sorted(cited(doc)) if not ((doc.parent / p).exists() or (ROOT / p).exists())]
    assert missing == [], f"{name} cites paths that do not exist: {missing}"


def test_the_check_sees_the_readme_paths():
    """Guard against a regex that silently matches nothing."""
    paths = cited(ROOT / "README.md")
    assert {"plan.md", "ERROR_ANALYSIS.md", "src/06_audit_and_metrics.py", "results/README.md"} <= paths
    assert len(paths) > 40
