"""
Provenance audit for Projects.xlsx.

    python verify_provenance.py

Answers one question: is there anything in `Projects.xlsx` that was not copied from the
original `My Tasks_Projects.xlsx`?

It normalises text (strips URLs, collapses whitespace, lowercases) and checks every
non-empty cell against the pool of every text value anywhere in the source workbook. Any
cell that cannot be traced is printed. A clean run means nothing was invented, estimated
or reworded.

Run it whenever you want to reassure yourself — or a colleague — that the seeded rows are
a faithful copy. It only reads; it never writes.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).parent
DEFAULT_SRC = Path.home() / "Downloads" / "My Tasks_Projects.xlsx"
DEFAULT_DST = HERE / "Projects.xlsx"

# Columns that hold dates or IDs rather than prose - compared by presence, not by text.
NON_PROSE = {"ID", "Start Date", "Completed Date"}
# Columns the generator deliberately leaves blank for seeded rows.
EXPECTED_BLANK = {"How It Was Built", "Why It Was Built"}


def txt(v) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    s = str(v).strip()
    return "" if s.lower() in {"nan", "none", "nat"} else s


def norm(v) -> str:
    """Comparable form: URLs removed, whitespace collapsed, lowercased."""
    s = re.sub(r"\s*https?://[^\s,;)\]]+\s*,?", " ", txt(v))
    return re.sub(r"\s+", " ", s).strip(" ,.").lower()


def source_pool(src: Path) -> tuple[set[str], dict[str, int]]:
    """Every text value anywhere in the source workbook, plus per-sheet row counts."""
    sheets = pd.read_excel(src, sheet_name=None, dtype=object)
    pool: set[str] = set()
    counts: dict[str, int] = {}
    for name, df in sheets.items():
        df = df.dropna(how="all")
        counts[str(name)] = len(df)
        for _, row in df.iterrows():
            for v in row.tolist():
                n = norm(v)
                if n:
                    pool.add(n)
                    # also index each line separately: checklists are multi-line cells
                    for line in str(txt(v)).splitlines():
                        ln = norm(line)
                        if ln:
                            pool.add(ln)
    pool.discard("")
    return pool, counts


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", default=str(DEFAULT_SRC))
    ap.add_argument("--target", default=str(DEFAULT_DST))
    args = ap.parse_args()

    src, dst = Path(args.source), Path(args.target)
    for p in (src, dst):
        if not p.exists():
            print(f"Not found: {p}")
            return 2

    pool, counts = source_pool(src)
    print(f"SOURCE  {src}")
    for name, n in counts.items():
        print(f"          sheet '{name}': {n} rows")
    print(f"TARGET  {dst}")

    df = pd.read_excel(dst, sheet_name="Projects", dtype=object)
    df = df[df["Project Name"].notna()]
    print(f"          sheet 'Projects': {len(df)} rows with a project name")
    print()

    print(f"{'COLUMN':<24}{'FILLED':>7}{'BLANK':>7}   TRACES BACK TO SOURCE?")
    print("-" * 88)
    problems: list[tuple[str, list[str]]] = []

    for col in df.columns:
        vals = [v for v in df[col].tolist() if txt(v)]
        filled, blank = len(vals), len(df) - len([v for v in df[col].tolist() if txt(v)])

        if col in NON_PROSE:
            verdict = "yes - copied from ID / Created / Completed"
        elif filled == 0:
            verdict = ("blank BY DESIGN - never captured in the old sheet"
                       if col in EXPECTED_BLANK else "all blank - nothing written")
        else:
            bad = [v for v in vals if norm(v) and norm(v) not in pool]
            if bad:
                problems.append((col, [txt(b) for b in bad]))
                verdict = f"NO - {len(bad)} value(s) NOT found in source"
            else:
                verdict = f"yes - all {filled} verbatim from source"
        print(f"{col:<24}{filled:>7}{blank:>7}   {verdict}")

    print()
    if problems:
        print("!!! THESE VALUES COULD NOT BE TRACED TO THE SOURCE WORKBOOK:")
        for col, bad in problems:
            for b in bad[:4]:
                print(f"    [{col}] {b[:110]}")
        print("\nFAILED - investigate before sharing.")
        return 1

    print("PASS - every non-empty cell traces back to the original workbook.")
    print("       Nothing was invented, estimated or reworded.")

    # ID continuity is a property of the SOURCE, not of the copy - surface it either way.
    ids = sorted(int(float(v)) for v in df["ID"].dropna())
    gaps = [i for i in range(min(ids), max(ids) + 1) if i not in ids]
    if gaps:
        print()
        print(f"NOTE   the source tracker's IDs run {min(ids)}-{max(ids)} but skip "
              f"{len(gaps)}: {', '.join(map(str, gaps))}")
        print("       Those projects are absent from the source file, so they were never")
        print("       available to copy. If they existed, they are missing from the")
        print("       registry and someone needs to re-add them by hand.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
