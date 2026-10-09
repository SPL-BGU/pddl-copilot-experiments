"""Shared loader for the 2026-10 breakdown + cost re-analysis (weaknesses
C11 / C12 / C16 / C21; findings in development/reanalysis_breakdowns_cost.md).

Named `bc_*` to stay separate from the statistics re-analysis that shares this
directory (`common.py`, weakness C9). Nothing here imports from, or writes to,
that work or the hash-pinned prereg scripts.

Read-only over results/. One row per trial, built by joining

  * results/<corpus>/<cell>/trials.jsonl          (tokens, tool_selected, failure_reason)
  * results/derived/e2e_overlay/<corpus>/<cell>.e2e.jsonl   (delivered verdict)

on the trial key. Nothing is graded here: the delivered verdict is the overlay's
`e2e_strict` (True / False / "indeterminate"), the tool-verified verdict is the
overlay's `tool_verified` (== the stored harness `success` on with-tools rows,
None on no-tools rows). These are the same two fields
`.claude/skills/analyzer/scripts/e2e_overlay.py:load_e2e_cells` aggregates into
`results/derived/e2e_overlay/pooled_e2e_table.csv`, so a cell total computed
here must equal that CSV (checked by `bc_reproduce_numbers.py`).

Score vocabulary used by every bc_* script:

  delivered   e2e_strict. ok = True rows; cens = "indeterminate" rows (stored
              answer cut at the snapshot cap, so it can be neither confirmed nor
              refuted). A cell is the bound <ok/n, (ok+cens)/n>; it is a point
              only when cens == 0. On no-tools rows of every task except
              simulate this equals the stored online grade.
  tool-ver    with-tools rows only: the tool call returned the right result
              (stored `success`). Not defined for the no-tools arm.
  harness     stored `success`: tool-ver on with-tools rows, the strict online
              grade of the final answer on no-tools rows.

The stale mirror results/sweep5-cluster-20260530 is never read.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RESULTS = REPO / "results"
OVERLAY = RESULTS / "derived" / "e2e_overlay"
OUT_DIR = Path(__file__).resolve().parent / "out" / "breakdowns_cost"
DOMAINS_DIR = REPO / "domains"

TASKS = ["solve", "validate_domain", "validate_problem", "validate_plan", "simulate"]
ARMS = ["nt-neut", "tl-neut", "tl-ster"]
ARM_DISP = {"nt-neut": "no-tools", "tl-neut": "tools-plain", "tl-ster": "tools-steered"}

# Headline open models (the paper's ">=9B" set, rq_deck.py:85 MODELS_9B), think off.
HEADLINE = [
    ("gemma4_26b-a4b", "Gemma 26B a4b"),
    ("Qwen3_5_9B", "Qwen3.5 9B"),
    ("qwen3_6_35b", "Qwen3.6 35B"),
]
MODEL_DISP = dict(HEADLINE)
NEUTRAL = (11, 12, 13)
STEERED = (14, 15, 16)
# wording index within its bank: v11/v14 -> w1, v12/v15 -> w2, v13/v16 -> w3
WORDING = {11: "w1", 12: "w2", 13: "w3", 14: "w1", 15: "w2", 16: "w3"}


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson 95% score interval, as fractions (same formula as summary.py:45)."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n) / d
    return (max(0.0, c - h), min(1.0, c + h))


def domain_track() -> dict[str, str]:
    """domain name -> 'classical' | 'numeric', from the domains/ tree (the same
    source pddl_eval/domains.py:44 uses for the `type` field)."""
    out = {}
    for track in ("classical", "numeric"):
        for d in sorted((DOMAINS_DIR / track).iterdir()):
            if d.is_dir():
                out[d.name] = track
    return out


def arm_of(with_tools: bool, pv: int) -> str | None:
    side = "tl" if with_tools else "nt"
    if pv in NEUTRAL:
        return f"{side}-neut"
    if pv in STEERED:
        return f"{side}-ster"
    return None


def load_cell(corpus: str, cell: str) -> list[dict]:
    """Joined rows for one cell directory. Raises if the overlay and the trial
    file disagree on the key set (they must be 1:1)."""
    tpath = RESULTS / corpus / cell / "trials.jsonl"
    opath = OVERLAY / corpus / f"{cell}.e2e.jsonl"
    trials = {}
    with tpath.open() as f:
        for ln in f:
            if not ln.strip():
                continue
            r = json.loads(ln)
            k = json.dumps(r["key"])
            if k in trials:
                raise ValueError(f"duplicate trial key in {tpath}: {k}")
            trials[k] = r["result"]
    rows = []
    seen = set()
    with opath.open() as f:
        for ln in f:
            o = json.loads(ln)
            k = json.dumps(o["trial_key"])
            t = trials.get(k)
            if t is None:
                raise ValueError(f"overlay row without trial: {k}")
            seen.add(k)
            pv = int(o["prompt_variant"])
            tok = t.get("tokens") or {}
            rows.append({
                "corpus": corpus, "cell": cell,
                "task": o["task"], "domain": o["domain_name"],
                "problem": o["problem_name"], "plan_label": o.get("plan_label") or "",
                "pv": pv, "with_tools": bool(o["with_tools"]),
                "arm": arm_of(bool(o["with_tools"]), pv),
                "e2e": o["e2e_strict"],             # True / False / "indeterminate"
                "e2e_reason": o.get("e2e_reason"),
                "tv": o.get("tool_verified"),       # None on no-tools rows
                "success": bool(t.get("success")),
                "tool_selected": t.get("tool_selected"),
                "failure_reason": t.get("failure_reason"),
                "in_tok": int(tok.get("prompt", 0) or 0),
                "out_tok": int(tok.get("completion", 0) or 0),
                "cache_write": int(tok.get("cache_write", 0) or 0),
                "cache_read": int(tok.get("cache_read", 0) or 0),
                "turns": int(tok.get("turns", 0) or 0),
                "has_tokens": bool(tok),
            })
    if len(seen) != len(trials):
        raise ValueError(f"{cell}: {len(trials) - len(seen)} trials missing from overlay")
    return rows


def open_cells(corpus: str = "sweep5v2-live", think: str = "off") -> dict[str, list[dict]]:
    """{model_key: rows} for the three headline models, both conditions pooled
    (the arm field separates them)."""
    out = {}
    for mkey, _disp in HEADLINE:
        rows = []
        for cond in ("no-tools", "tools_all_minimal"):
            rows += load_cell(corpus, f"slurm_vllm_{mkey}_{think}_{cond}")
        out[mkey] = rows
    return out


def agg(rows: list[dict]) -> dict:
    """Counts for one group of rows (one arm)."""
    n = len(rows)
    ok = sum(1 for r in rows if r["e2e"] is True)
    cens = sum(1 for r in rows if r["e2e"] == "indeterminate")
    tv_n = sum(1 for r in rows if r["tv"] is not None)
    tv_ok = sum(1 for r in rows if r["tv"] is True)
    return {"n": n, "ok": ok, "cens": cens, "tv_n": tv_n, "tv_ok": tv_ok,
            "harness_ok": sum(1 for r in rows if r["success"]),
            "called": sum(1 for r in rows if r["tool_selected"] is True)}


def fmt_deliv(a: dict) -> str:
    """Delivered cell: point + Wilson when exact, <low, high> (cK) when censored."""
    n = a["n"]
    if n == 0:
        return "-"
    if a["cens"] == 0:
        lo, hi = wilson(a["ok"], n)
        return f"{100 * a['ok'] / n:.1f} [{100 * lo:.1f}, {100 * hi:.1f}]"
    return (f"⟨{100 * a['ok'] / n:.1f}, {100 * (a['ok'] + a['cens']) / n:.1f}⟩"
            f" (c{a['cens']})")


def fmt_rate(k: int, n: int) -> str:
    if n == 0:
        return "-"
    lo, hi = wilson(k, n)
    return f"{100 * k / n:.1f} [{100 * lo:.1f}, {100 * hi:.1f}]"


def md_table(headers: list[str], rows: list[list]) -> str:
    out = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    for r in rows:
        out.append("| " + " | ".join(str(x) for x in r) + " |")
    return "\n".join(out)
