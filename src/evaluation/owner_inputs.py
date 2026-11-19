"""Owner input tables (owner, 2026-11-19; R50, §11 #62): every judgement the owner writes by hand lives in a
committed table that the pipeline reads and never rewrites. The generated CSVs take their owner columns from
these tables at each run.

    <eval>/owner_extraction/owner_adjudication_causes.csv  -> adjudication_7a.csv     (owner_claims.main)
    <eval>/owner_review/owner_review_wrong.csv             -> review_7b_wrong.csv     (claim_review.main)
    <eval>/owner_review/owner_review_unverifiable.csv      -> review_7c_unverifiable.csv
    (<eval>/owner_extraction/owner_verdicts_nonmech.csv    -> non_mechanical_mappings.csv, owner_verdicts.py)

At each merge the table's keys must be exactly the generated rows' keys, its context columns must equal the
generated values (numbers compared as numbers, whitespace normalised), and each value-listed column (ALLOWED:
`cause`, and `owner_verdict` of the two review tables, §11 #63) must be empty or one of its fixed values.
Anything else raises OwnerInputError, naming the key, line and column, and the generated CSV that
takes its owner columns from that table is not written.

    uv run python -m src.evaluation.owner_inputs init R1    # creates the tables that do not exist yet; never overwrites
"""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

CAUSES = ("owner_miss", "assistant_miss", "owner_encoding", "assistant_encoding", "rubric_ambiguity")

WRONG_VERDICTS = ("confirmed_wrong", "actually_correct", "should_be_unverifiable", "extraction_error")
UNVER_VERDICTS = ("confirmed_unverifiable", "verifiable_correct", "verifiable_wrong", "extraction_error")

ADJ_FILE = "owner_adjudication_causes.csv"
WRONG_FILE = "owner_review_wrong.csv"
UNVER_FILE = "owner_review_unverifiable.csv"
# columns with a fixed list of values, per table (owner, §11 #62-#63); comments are free text
ALLOWED = {ADJ_FILE: {"cause": CAUSES}, WRONG_FILE: {"owner_verdict": WRONG_VERDICTS},
           UNVER_FILE: {"owner_verdict": UNVER_VERDICTS}}

ADJ_COLS = ["side", "claim_id", "day", "text", "cause", "comment", "cause_set_by"]
ADJ_KEY, ADJ_OWNER = ("side", "claim_id"), ("cause", "comment", "cause_set_by")
REVIEW_COLS = {
    "wrong": ["id", "day", "text", "encoding", "stated", "computed", "tier", "owner_verdict", "owner_comment"],
    "unverifiable": ["id", "day", "text", "encoding", "stated", "computed", "note", "owner_verdict",
                     "owner_comment"]}
REVIEW_KEY, REVIEW_OWNER = ("id",), ("owner_verdict", "owner_comment")


class OwnerInputError(ValueError):
    pass


def adjudication_claim_id(row: dict) -> str:
    """The claim a row of adjudication_7a.csv is about: the owner's claim on an owner-only row, the assistant's
    on an assistant-only row (the other side's columns are a display-only nearest counterpart)."""
    if row["side"] == "owner_only":
        return f"OWN-D{int(row['day']):02d}-r{int(row['owner_row']):03d}"
    return row["assistant_id"]


def _same(a: str, b: str) -> bool:
    a, b = re.sub(r"\s+", " ", str(a).strip()), re.sub(r"\s+", " ", str(b).strip())
    if a == b:
        return True
    try:
        return float(a) == float(b)
    except ValueError:
        return False


def read_table(path: Path, cols: list[str], key: tuple[str, ...]) -> dict[tuple, dict]:
    if not path.exists():
        raise OwnerInputError(f"{path.name}: missing (create it with `python -m src.evaluation.owner_inputs init`)")
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != cols:
            raise OwnerInputError(f"{path.name}: header {reader.fieldnames} is not {cols}")
        out = {}
        for n, r in enumerate(reader, 2):
            k = tuple(r[c].strip() for c in key)
            if k in out:
                raise OwnerInputError(f"{path.name}: duplicate key {k} (line {n})")
            out[k] = r
            r["__line__"] = n
    return out


def merge(generated: list[dict], path: Path, cols: list[str], key: tuple[str, ...], owner_cols: tuple[str, ...],
          context: dict[tuple, dict]) -> dict[tuple, dict]:
    """Owner cells by key, after checking the table against the generated rows. `context` gives, per generated
    key, the values the table's context columns must hold."""
    table = read_table(path, cols, key)
    gen = set(context)
    missing, extra = sorted(gen - set(table)), sorted(set(table) - gen)
    if missing or extra:
        raise OwnerInputError(f"{path.name}: keys missing from the table {missing}; unknown keys {extra}")
    for k, r in table.items():
        for c, v in context[k].items():
            if not _same(r[c], v):
                raise OwnerInputError(f"{path.name}: {k} column {c!r} is {r[c]!r}, generated {v!r}")
        for c, values in ALLOWED.get(path.name, {}).items():
            if r[c].strip() not in ("",) + values:
                raise OwnerInputError(f"{path.name}: {k} (line {r['__line__']}) column {c!r} is {r[c]!r}, "
                                      f"not empty and not in {list(values)}")
    return {k: {c: table[k][c] for c in owner_cols} for k in table}


def _write_new(path: Path, cols: list[str], rows: list[dict]) -> bool:
    if path.exists():
        return False
    with open(path, "x", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    return True


# --- context of each generated row -------------------------------------------------------------------------

def adjudication_context(rows: list[dict]) -> dict[tuple, dict]:
    out = {}
    for r in rows:
        own = r["side"] == "owner_only"
        out[(r["side"], adjudication_claim_id(r))] = {"day": r["day"],
                                                     "text": r["owner_text"] if own else r["assistant_text"]}
    return out


def review_row(c: dict, kind: str) -> dict:
    from .claim_review import tier
    from .owner_claims import encoding
    v = c.get("value")
    row = {"id": c["id"], "day": str(c["day"]), "text": c["text"], "encoding": encoding(c),
           "stated": "" if v is None else (json.dumps(v) if isinstance(v, list) else str(v)),
           "computed": json.dumps(c.get("computed"))}
    row["tier" if kind == "wrong" else "note"] = tier(c) if kind == "wrong" else c.get("note", "")
    return row


def review_context(claims: list[dict], kind: str) -> dict[tuple, dict]:
    return {(c["id"],): review_row(c, kind) for c in claims}


def init(eval_dir: Path) -> list[str]:
    """Create the tables that do not exist yet from the generated rows; owner cells empty except the causes
    already set by the owner in owner_verdicts_nonmech.csv. Never overwrites."""
    made = []
    ex = eval_dir / "owner_extraction"
    adj = list(csv.DictReader(open(ex / "adjudication_7a.csv", encoding="utf-8-sig")))
    nonmech = {int(r["row"]): r for r in csv.DictReader(open(ex / "owner_verdicts_nonmech.csv", encoding="utf-8"))}
    rows = []
    for r in adj:
        own = r["side"] == "owner_only"
        v = nonmech.get(int(r["owner_row"])) if own and r["owner_row"] else None
        rows.append({"side": r["side"], "claim_id": adjudication_claim_id(r), "day": r["day"],
                     "text": r["owner_text"] if own else r["assistant_text"],
                     "cause": v["cause"] if v and v["cause"] else "",
                     "comment": v["owner_comment"] if v and v["cause"] else "",
                     "cause_set_by": v["set_by"] if v and v["cause"] else ""})
    if _write_new(ex / ADJ_FILE, ADJ_COLS, rows):
        made.append(ADJ_FILE)
    claims = [c for c in json.loads((eval_dir / "explanation_claims.json").read_text(encoding="utf-8"))["claims"]
              if c["author"] == "ALLOCATOR"]
    for kind, name in (("wrong", WRONG_FILE), ("unverifiable", UNVER_FILE)):
        rs = [{**review_row(c, kind), "owner_verdict": "", "owner_comment": ""} for c in claims
              if c["verdict"] == kind]
        if _write_new(eval_dir / "owner_review" / name, REVIEW_COLS[kind], rs):
            made.append(name)
    return made


if __name__ == "__main__":
    from .dataset import ROOT
    if sys.argv[1] != "init":
        raise SystemExit("usage: python -m src.evaluation.owner_inputs init <run_id>")
    print("created:", init(ROOT / "results" / "evaluations" / sys.argv[2]) or "nothing (all tables exist)")
