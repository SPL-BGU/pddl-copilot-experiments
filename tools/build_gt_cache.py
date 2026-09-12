#!/usr/bin/env python3
"""Materialize the MCP-generated ground truth to a JSON cache (overlay Phase 2).

The harness regenerates ground truth (oracle plan validity, canonical plan,
state trajectory) via live MCP calls at every run start; nothing is persisted,
which is what blocks offline regrading of solve/simulate (see
development/tool_call_vs_final_output_grading.md §9-10). This script runs the
exact same `generate_ground_truth` once, locally, and dumps the result.

Deterministic given the fixture tree (planner + validator are oracles), so the
cache is safe to reuse across regrade runs. Rebuild after any change under
domains/.

Usage:
    python tools/build_gt_cache.py \
        [--marketplace-path ../pddl-copilot] [--domains-dir domains] \
        [--out results/derived/gt_cache.json]
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from run_experiment import resolve_plugin_dirs  # noqa: E402
from pddl_eval.chat import MCPPlanner  # noqa: E402
from pddl_eval.domains import generate_ground_truth, load_domains  # noqa: E402


async def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--marketplace-path", default="../pddl-copilot")
    ap.add_argument("--domains-dir", default="domains")
    ap.add_argument("--out", default="results/derived/gt_cache.json")
    args = ap.parse_args()

    plugin_dirs = resolve_plugin_dirs(args.marketplace_path)
    domains = load_domains(Path(args.domains_dir))
    print(f"domains loaded: {len(domains)}", flush=True)

    mcp = MCPPlanner()
    try:
        await mcp.connect(plugin_dirs)
        gt = await generate_ground_truth(mcp, domains)
    finally:
        await mcp.close()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(gt))
    n_probs = sum(1 for d in gt.values() for p in d if p != "_negatives")
    print(f"gt cache written: {out} ({n_probs} problems, "
          f"{out.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    asyncio.run(main())
