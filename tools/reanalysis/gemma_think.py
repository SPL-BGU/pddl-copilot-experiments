#!/usr/bin/env python3
"""Gemma-26B thinking on against thinking off, paired on the trial key (read-only).

    .venv/bin/python tools/reanalysis/gemma_think.py --results /abs/results

Backs the 2026-11-09 CHANGELOG correction "Gemma 4 does think when
`enable_thinking=True`": Gemma is served with `REASONING_PARSER=none`, so its
reasoning stays inside `response`, opened by `<|channel>thought` (or a bare
`thought` line) and closed by `<channel|>`. For each corpus, cell kind (no-tools,
tools) and arm, rows are paired on the trial key with the think field masked, and
the table gives per task: success (the stored grade, `success`; the tools cell's
value is tool-verified), answers cut by the output budget (`done_reason ==
"length"`), answers that open a thought channel, calling (`tool_selected`), and the
no-call rows cut inside an unclosed thought channel.

Self-check (exit 2 on failure): the three figures the CHANGELOG entry quotes, on
sweep5v2-live: every one of the 4,560 no-tools think-on responses opens a thought
channel; no-tools validate_plan answers cut by the budget, 9 (off) and 2,690 (on) of
3,000; plain validate_plan rows of the think-on tools cell without a call, 2,981, of
which 2,025 ran out inside the thought channel.

Writes tools/reanalysis/out/gemma_think.md.
"""
from __future__ import annotations

import argparse
import statistics
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import iss027_common as C  # noqa: E402  (load_rows, arm_of)

MODEL = "gemma4_26b-a4b"
CORPORA = ("sweep5v2-live", "sweep6-live")
TASKS = ("solve", "validate_domain", "validate_problem", "validate_plan", "simulate")
CHANGELOG = {"thought_start_no_tools_on": (4560, 4560), "vp_cut_no_tools": (9, 2690),
             "vp_plain_no_call_on": 2981, "vp_plain_no_call_cut_in_thought_on": 2025}


EMPTY_CHANNEL = "<|channel>thought\n<channel|>"  # the leaked empty marker (pddl_eval/scoring.py)


def opens_thought(text: str) -> bool:
    """The answer opens a thought channel that is not the leaked empty marker."""
    t = (text or "").lstrip()
    if t.startswith(EMPTY_CHANNEL):
        return False
    return t.startswith("<|channel>thought") or t.startswith("thought")


def cut_in_thought(r: dict) -> bool:
    resp = r.get("response") or ""
    return r.get("done_reason") == "length" and opens_thought(resp) and "<channel|>" not in resp


def masked(key: tuple) -> tuple:
    k = list(key)
    k[7] = "*"  # think
    return tuple(k)


def compare(results: Path, corpus: str, kind: str) -> dict:
    cell = "no-tools" if kind == "no-tools" else "tools_all_minimal"
    off, _ = C.load_rows(results / corpus / f"slurm_vllm_{MODEL}_off_{cell}" / "trials.jsonl")
    on, _ = C.load_rows(results / corpus / f"slurm_vllm_{MODEL}_on_{cell}" / "trials.jsonl")
    offm, onm = {masked(k): v for k, v in off.items()}, {masked(k): v for k, v in on.items()}
    agg = defaultdict(lambda: defaultdict(list))
    for k in sorted(set(offm) & set(onm)):
        for lab, r in (("off", offm[k]), ("on", onm[k])):
            a = agg[(r["task"], C.arm_of(r))]
            a[f"{lab}_ok"].append(bool(r["success"]))
            a[f"{lab}_cut"].append(r.get("done_reason") == "length")
            a[f"{lab}_thought"].append(opens_thought(r.get("response")))
            a[f"{lab}_comp"].append((r.get("tokens") or {}).get("completion") or 0)
            if r.get("with_tools"):
                a[f"{lab}_called"].append(bool(r.get("tool_selected")))
                if not r.get("tool_selected"):
                    a[f"{lab}_nocall_cut_in_thought"].append(cut_in_thought(r))
    return {"n_off": len(off), "n_on": len(on), "paired": len(set(offm) & set(onm)),
            "thought_on": sum(opens_thought(r.get("response")) for r in on.values()), "agg": agg}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--results", type=Path, required=True, help="results root (read-only)")
    ap.add_argument("--out-dir", type=Path, default=C.OUT)
    args = ap.parse_args(argv)
    res = {(c, kind): compare(args.results, c, kind) for c in CORPORA for kind in ("no-tools", "tools")}

    # self-check against the CHANGELOG entry
    nt, tl = res[("sweep5v2-live", "no-tools")], res[("sweep5v2-live", "tools")]
    vp = nt["agg"][("validate_plan", "unaided")]
    vpp = tl["agg"][("validate_plan", "plain")]
    got = {"thought_start_no_tools_on": (nt["thought_on"], nt["n_on"]),
           "vp_cut_no_tools": (sum(vp["off_cut"]), sum(vp["on_cut"])),
           "vp_plain_no_call_on": len(vpp["on_nocall_cut_in_thought"]),
           "vp_plain_no_call_cut_in_thought_on": sum(vpp["on_nocall_cut_in_thought"])}
    bad = [f"{k}: {got[k]} vs CHANGELOG {v}" for k, v in CHANGELOG.items() if got[k] != v]
    if bad:
        print("HALT: " + "; ".join(bad), file=sys.stderr)
        return 2

    L = ["# Gemma-26B, thinking on against thinking off (paired trial keys)", "",
         "*Generated by `tools/reanalysis/gemma_think.py`; do not edit, rerun the script.* "
         f"Self-check: the {len(CHANGELOG)} figures of the 2026-11-09 CHANGELOG entry reproduce "
         f"(sweep5v2-live: {got['thought_start_no_tools_on'][0]:,} of {got['thought_start_no_tools_on'][1]:,} "
         "no-tools think-on responses open a thought channel; no-tools validate_plan cut by the budget "
         f"{got['vp_cut_no_tools'][0]} → {got['vp_cut_no_tools'][1]:,} of 3,000; plain validate_plan without a "
         f"call {got['vp_plain_no_call_on']:,}, of which {got['vp_plain_no_call_cut_in_thought_on']:,} cut inside "
         "the thought channel).", "",
         "Success = the stored grade (`success`): the online grade unaided, tool-verified on the tools "
         "cell. Cut = `done_reason == \"length\"`. Thought = the response opens `<|channel>thought` or a "
         "bare `thought` line (the leaked empty marker `<|channel>thought\\n<channel|>` does not count). No call, cut in thought = rows without a call whose answer ran out "
         "before `<channel|>`.", ""]
    for (c, kind), r in res.items():
        L += [f"## {c}, {kind} (off {r['n_off']:,} rows, on {r['n_on']:,}, paired {r['paired']:,})", "",
              "| task | arm | n | success off / on | cut off / on | thought off / on | median completion "
              "tokens off / on | calling off / on | no call, cut in thought (on) |",
              "|---|---|---|---|---|---|---|---|---|"]
        for (t, arm), a in sorted(r["agg"].items(), key=lambda x: (TASKS.index(x[0][0]), x[0][1])):
            n = len(a["off_ok"])
            call = (f"{sum(a['off_called']):,} / {sum(a['on_called']):,}" if a.get("on_called") else "–")
            nc = (f"{sum(a['on_nocall_cut_in_thought']):,} of {len(a['on_nocall_cut_in_thought']):,}"
                  if a.get("on_nocall_cut_in_thought") else "–")
            L.append(f"| {t} | {arm} | {n:,} | {sum(a['off_ok']):,} / {sum(a['on_ok']):,} | "
                     f"{sum(a['off_cut']):,} / {sum(a['on_cut']):,} | {sum(a['off_thought']):,} / "
                     f"{sum(a['on_thought']):,} | {statistics.median(a['off_comp']):.0f} / "
                     f"{statistics.median(a['on_comp']):.0f} | {call} | {nc} |")
        L.append("")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "gemma_think.md").write_text("\n".join(L))
    print(f"self-check: {len(CHANGELOG)} of {len(CHANGELOG)} pass; wrote {args.out_dir}/gemma_think.md",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
