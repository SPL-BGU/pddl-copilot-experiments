"""C11 / C12 side finding — byte-identical prompts inside one cell.

Two places in the grid send the same prompt five times:

  validate_domain, valid domains   one job per (domain, problem) (runner.py:735-743)
                                   but the prompt template contains only {domain}
                                   (prompts.py:374-379), so p01..p05 of a domain
                                   give five identical prompts per wording.
  validate_plan, valid plans       one job per committed valid plan v1..v5
                                   (runner.py:718-734); where the five plan files
                                   of a problem are byte-identical the five
                                   prompts are identical too.

Every trial is one sample at temperature 0 (chat.py:28), so identical prompts
"should" give identical outcomes. This script counts how often they do not,
which is the only measurement of run-to-run variation the corpus contains.

For each headline model x arm it reports the number of identical-prompt groups
(size 5), how many are not unanimous on the harness score, and the share of
trials that disagree with their group's majority.

    python3 tools/reanalysis/bc_duplicate_prompts.py [--corpus sweep5v2-live]

Writes out/breakdowns_cost/duplicate_prompts_<corpus>.md.
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bc_common as C  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default="sweep5v2-live")
    args = ap.parse_args()
    track = C.domain_track()
    root = C.REPO / ("domains-anon" if args.corpus.startswith("sweep6") else "domains")

    # problems whose five valid-plan files are byte-identical
    identical, n_prob, distinct_valid, distinct_invalid = set(), 0, 0, 0
    for d, t in track.items():
        ddir = root / t / d
        if not ddir.is_dir():
            # anon tree may use different directory names; fall back to canonical
            ddir = C.DOMAINS_DIR / t / d
        for pf in sorted(ddir.glob("p[0-9][0-9].pddl")):
            n_prob += 1
            v = {(ddir / f"{pf.stem}_v{i}.plan").read_text() for i in range(1, 6)}
            b = {(ddir / f"{pf.stem}_b{i}.plan").read_text() for i in range(1, 6)}
            distinct_valid += len(v)
            distinct_invalid += len(b)
            if len(v) == 1:
                identical.add((d, pf.stem))

    md = [f"# Identical prompts and run-to-run agreement, {args.corpus}, think off", "",
          f"Problems whose five valid-plan files are byte-identical: {len(identical)} of {n_prob} "
          f"({distinct_valid} distinct valid-plan files of {5 * n_prob}; "
          f"{distinct_invalid} distinct invalid-plan files of {5 * n_prob}).", "",
          "Distinct prompts per arm (three wordings): validate_domain "
          f"{3 * len(track)} valid + {3 * len(track)} invalid = {6 * len(track)} of 360 trials; "
          f"validate_plan {3 * distinct_valid} valid + {3 * distinct_invalid} invalid = "
          f"{3 * (distinct_valid + distinct_invalid)} of 3000 trials.", ""]

    cells = C.open_cells(args.corpus)
    rows_out = []
    for mkey, mdisp in C.HEADLINE:
        for arm in C.ARMS:
            for task, label in (("validate_domain", "validate_domain, valid domain x5"),
                                ("validate_plan", "validate_plan, valid plan x5")):
                groups = defaultdict(list)
                for r in cells[mkey]:
                    if r["task"] != task or r["arm"] != arm:
                        continue
                    if task == "validate_domain":
                        if r["problem"] == "domain_neg":
                            continue
                        groups[(r["domain"], r["pv"])].append(r["success"])
                    else:
                        if not r["plan_label"].startswith("v"):
                            continue
                        if (r["domain"], r["problem"]) not in identical:
                            continue
                        groups[(r["domain"], r["problem"], r["pv"])].append(r["success"])
                assert all(len(g) == 5 for g in groups.values()), "group size != 5"
                mixed = sum(1 for g in groups.values() if len(set(g)) > 1)
                minority = sum(min(sum(g), len(g) - sum(g)) for g in groups.values())
                n = 5 * len(groups)
                rows_out.append([mdisp, C.ARM_DISP[arm], label, len(groups), mixed,
                                 f"{100 * mixed / len(groups):.1f}%",
                                 f"{minority}/{n} ({100 * minority / n:.1f}%)"])
    md += [C.md_table(["model", "arm", "identical-prompt set", "groups of 5",
                       "groups not unanimous", "share not unanimous",
                       "trials disagreeing with their group's majority"], rows_out), ""]
    C.OUT_DIR.mkdir(parents=True, exist_ok=True)
    (C.OUT_DIR / f"duplicate_prompts_{args.corpus}.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
