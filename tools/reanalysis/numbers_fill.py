#!/usr/bin/env python3
"""Fill the generated blocks of development/NUMBERS.md from tools/reanalysis/out/.

A generated block sits between `<!-- gen:NAME -->` and `<!-- /gen:NAME -->`;
everything between the two markers is replaced by the listed output files,
joined by a blank line. Text outside the markers is never touched, so the
headings and provenance lines stay hand-written and every figure comes from
a script. Run after the scripts that write the outputs:

  .venv/bin/python tools/reanalysis/numbers_fill.py [--check]

--check exits 1 when NUMBERS.md is not up to date with the outputs.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
NUMBERS = HERE.parents[1] / "development" / "NUMBERS.md"
BLOCKS = {
    "s1_call_flips": ["numbers_s1_call_flips.md", "s1_call_flips_table.md"],
    "06_frontier_tools_contamination": ["numbers_06_frontier_tools_contamination.md"],
    "val_frontier_solve": ["numbers_val_frontier_solve.md"],
    # ISS-028 post hoc split of the delivered rerun's solve WRONG_FACTS rows
    # (iss028_goal_trailers.py)
    "iss028": ["numbers_iss028.md"],
    # ISS-029 simulate prompt plan vs cached plan (iss029_simulate_plan.py; needs
    # the pinned results/derived/gt_cache.json)
    "iss029": ["numbers_iss029.md"],
}


def fill(text: str, out_dir: Path) -> str:
    for name, files in BLOCKS.items():
        body = "\n".join((out_dir / f).read_text().strip() + "\n" for f in files)
        pat = re.compile(rf"(<!-- gen:{re.escape(name)} -->\n).*?(<!-- /gen:{re.escape(name)} -->)", re.S)
        if not pat.search(text):
            raise SystemExit(f"NUMBERS.md has no gen:{name} markers")
        text = pat.sub(lambda m: m.group(1) + body + m.group(2), text)
    return text


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)
    old = NUMBERS.read_text()
    new = fill(old, HERE / "out")
    if args.check:
        print("up to date" if new == old else "NUMBERS.md differs from the generated outputs")
        return int(new != old)
    NUMBERS.write_text(new)
    return 0


if __name__ == "__main__":
    sys.exit(main())
