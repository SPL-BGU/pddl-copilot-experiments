"""Aggregation, tabular reports, and JSON serialization.

`summarize_single_task` produces the long-format rows with N, success rate,
Wilson 95% CIs, per-variant breakdowns, and failure-reason counts. The
`print_*` helpers render those rows for end-of-run inspection. `save_results`
writes the trio (single_task_*.json + chain_*.json + summary_*.json) under
the output dir.

DAG: summary → runner. (For `TaskResult`, `TASKS`, `ACTIVE_PROMPT_VARIANTS`.)
"""

import json
import math
import time
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path

from .prompts import ACTIVE_PROMPT_VARIANTS
from .runner import TASKS, TaskResult
from .scoring import FR_OK


def wilson_ci(successes: int, total: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score confidence interval for a binomial proportion."""
    if total == 0:
        return (0.0, 0.0)
    phat = successes / total
    denom = 1 + z * z / total
    center = (phat + z * z / (2 * total)) / denom
    half = (z * math.sqrt((phat * (1 - phat) + z * z / (4 * total)) / total)) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def _new_token_agg() -> dict:
    """Per-cell accumulator for the `tokens` summary row (see `_token_row`)."""
    return {
        "n": 0,
        "prompt_sum": 0,
        "completion_sum": 0,
        "turns_sum": 0,
        "turns_max": 0,
        "eval_duration_ns_sum": 0,
    }


def _add_tokens(agg: dict, tokens: dict) -> None:
    """Fold one trial's `tokens` dict into a `_new_token_agg` accumulator.

    Trials missing token data (e.g. errored before the chat call) are
    skipped so means stay over the trials that actually consumed tokens;
    `n` mirrors the count used in those means.
    """
    if not tokens:
        return
    agg["n"] += 1
    agg["prompt_sum"] += tokens.get("prompt", 0) or 0
    agg["completion_sum"] += tokens.get("completion", 0) or 0
    turns = tokens.get("turns", 0) or 0
    agg["turns_sum"] += turns
    if turns > agg["turns_max"]:
        agg["turns_max"] = turns
    agg["eval_duration_ns_sum"] += tokens.get("eval_duration_ns", 0) or 0


def _token_row(agg: dict) -> dict:
    """Render a token-stats row from a `_new_token_agg` accumulator.

    `completion_tokens_per_s` divides the summed completion tokens by the
    summed eval-duration so it's robust to per-trial duration skew (a few
    very-slow trials don't dominate the mean). Returns 0.0 when the cell
    has no token-bearing trials so consumers can plot the field
    unconditionally.
    """
    n = agg["n"]
    if n == 0:
        return {
            "n": 0,
            "prompt_sum": 0, "prompt_mean": 0.0,
            "completion_sum": 0, "completion_mean": 0.0,
            "total_sum": 0, "total_mean": 0.0,
            "turns_mean": 0.0, "turns_max": 0,
            "eval_duration_s_sum": 0.0, "eval_duration_s_mean": 0.0,
            "completion_tokens_per_s": 0.0,
        }
    prompt_sum = agg["prompt_sum"]
    completion_sum = agg["completion_sum"]
    total_sum = prompt_sum + completion_sum
    eval_dur_s = agg["eval_duration_ns_sum"] / 1e9
    return {
        "n": n,
        "prompt_sum": prompt_sum,
        "prompt_mean": round(prompt_sum / n, 2),
        "completion_sum": completion_sum,
        "completion_mean": round(completion_sum / n, 2),
        "total_sum": total_sum,
        "total_mean": round(total_sum / n, 2),
        "turns_mean": round(agg["turns_sum"] / n, 3),
        "turns_max": agg["turns_max"],
        "eval_duration_s_sum": round(eval_dur_s, 2),
        "eval_duration_s_mean": round(eval_dur_s / n, 3),
        "completion_tokens_per_s": round(completion_sum / eval_dur_s, 2) if eval_dur_s > 0 else 0.0,
    }


def summarize_single_task(results: list[TaskResult]) -> list[dict]:
    """Aggregate single-task results into long-format rows with N and 95% CIs.

    For the "tools" condition, also reports tool_selected count/rate — how often
    the model called the correct MCP tool, independently of result correctness.
    Each row also carries `truncated` (count where done_reason=="length") and
    a `failure_reasons: {reason: count}` dict so the notebook can plot
    failure-mode breakdowns without reparsing the raw JSON.

    Each row also carries `per_variant`: a dict keyed by `prompt_variant`
    (string) → {n, successes, success_rate, ci_lo, ci_hi[, tool_selected_*]}.
    Lets the paper pick a single representative variant later without
    re-aggregating the raw JSON.

    A `tokens` dict per row aggregates the per-trial `TaskResult.tokens`
    into prompt/completion/turn/duration totals + means and a stable
    completion-tokens-per-second rate (sum/sum, not mean of ratios).
    Per-variant cells carry the same shape so analysis can compare
    variants on token usage as well as success.
    """
    def _new_agg() -> dict:
        return {
            "total": 0,
            "success": 0,
            "tool_selected": 0,
            "truncated": 0,
            "failure_reasons": defaultdict(int),
            "per_variant": defaultdict(lambda: {"n": 0, "succ": 0, "tool_sel": 0,
                                                "tokens": _new_token_agg()}),
            "tokens": _new_token_agg(),
        }

    agg: dict = defaultdict(_new_agg)
    for r in results:
        cond = "tools" if r.with_tools else "no-tools"
        key = (r.model, cond, r.task)
        agg[key]["total"] += 1
        if r.success:
            agg[key]["success"] += 1
        if r.tool_selected:
            agg[key]["tool_selected"] += 1
        if r.truncated:
            agg[key]["truncated"] += 1
        agg[key]["failure_reasons"][r.failure_reason] += 1
        _add_tokens(agg[key]["tokens"], r.tokens)
        pv = agg[key]["per_variant"][r.prompt_variant]
        pv["n"] += 1
        if r.success:
            pv["succ"] += 1
        if r.tool_selected:
            pv["tool_sel"] += 1
        _add_tokens(pv["tokens"], r.tokens)

    models = sorted(set(r.model for r in results))
    tasks_present = [t for t in TASKS if any(r.task == t for r in results)]

    rows: list[dict] = []
    for model in models:
        for cond in ("tools", "no-tools"):
            for task in tasks_present:
                d = agg[(model, cond, task)]
                n = d["total"]
                s = d["success"]
                rate = s / n if n > 0 else 0.0
                lo, hi = wilson_ci(s, n)
                row: dict = {
                    "model": model,
                    "condition": cond,
                    "task": task,
                    "successes": s,
                    "n": n,
                    "success_rate": round(rate, 4),
                    "ci_lo": round(lo, 4),
                    "ci_hi": round(hi, 4),
                    "truncated": d["truncated"],
                    "failure_reasons": dict(d["failure_reasons"]),
                }
                if cond == "tools":
                    ts = d["tool_selected"]
                    ts_rate = ts / n if n > 0 else 0.0
                    ts_lo, ts_hi = wilson_ci(ts, n)
                    row["tool_selected"] = ts
                    row["tool_selected_rate"] = round(ts_rate, 4)
                    row["tool_selected_ci_lo"] = round(ts_lo, 4)
                    row["tool_selected_ci_hi"] = round(ts_hi, 4)
                row["tokens"] = _token_row(d["tokens"])
                # Per-variant breakdown. Sorted-by-variant for stable JSON output.
                per_variant: dict[str, dict] = {}
                for pv_key in sorted(d["per_variant"].keys()):
                    pv_d = d["per_variant"][pv_key]
                    pv_n, pv_s = pv_d["n"], pv_d["succ"]
                    pv_lo, pv_hi = wilson_ci(pv_s, pv_n)
                    cell: dict = {
                        "n": pv_n,
                        "successes": pv_s,
                        "success_rate": round(pv_s / pv_n, 4) if pv_n else 0.0,
                        "ci_lo": round(pv_lo, 4),
                        "ci_hi": round(pv_hi, 4),
                    }
                    if cond == "tools":
                        pv_ts = pv_d["tool_sel"]
                        pv_ts_lo, pv_ts_hi = wilson_ci(pv_ts, pv_n)
                        cell["tool_selected"] = pv_ts
                        cell["tool_selected_rate"] = round(pv_ts / pv_n, 4) if pv_n else 0.0
                        cell["tool_selected_ci_lo"] = round(pv_ts_lo, 4)
                        cell["tool_selected_ci_hi"] = round(pv_ts_hi, 4)
                    cell["tokens"] = _token_row(pv_d["tokens"])
                    per_variant[str(pv_key)] = cell
                row["per_variant"] = per_variant
                rows.append(row)
    return rows


def _display_condition(cond: str) -> str:
    """Map the internal condition tag ("tools"/"no-tools") to its
    user-facing display string. PR-4 (2026-04-29) renames "no-tools" to
    "no-pddl-tools" in printed tables and the CLI banner; the JSON
    `condition` field stays "no-tools" so old result corpora parse
    identically and downstream notebooks need no migration.
    """
    return "no-pddl-tools" if cond == "no-tools" else cond


def print_fail_reasons_table(results: list[TaskResult]):
    """Per (model, condition, task) breakdown of the top failure reasons.

    Complements the success-rate table by answering "why did the failures
    fail?" at a glance — counts the top 3 FR_* tags per cell plus a
    truncation count.
    """
    rows = summarize_single_task(results)
    if not rows:
        return

    header = (
        f"{'Model':<20} {'Condition':<13} {'Task':<18} "
        f"{'N':>4}  {'Fails':>5}  {'Trunc':>5}  Top failure reasons"
    )
    bar = "=" * max(len(header), 92)
    print("\n" + bar)
    print("FAIL REASONS BY (model, condition, task)")
    print(bar)
    print(header)
    print("-" * len(bar))
    for r in rows:
        n = r["n"]
        fails = n - r["successes"]
        reasons = {k: v for k, v in r["failure_reasons"].items() if k != FR_OK}
        top = sorted(reasons.items(), key=lambda kv: -kv[1])[:3]
        top_str = ", ".join(f"{k}:{v}" for k, v in top) if top else "-"
        print(
            f"{r['model']:<20} {_display_condition(r['condition']):<13} {r['task']:<18} "
            f"{n:>4}  {fails:>5}  {r['truncated']:>5}  {top_str}"
        )
    print(bar)


def print_single_task_table(results: list[TaskResult]):
    """Long-format table with success rate, N, and Wilson 95% CI."""
    rows = summarize_single_task(results)
    if not rows:
        return

    header = (
        f"{'Model':<20} {'Condition':<13} {'Task':<18} "
        f"{'Rate':>6}  {'N':>4}  {'95% CI':<16}  {'ToolSel':>7}"
    )
    bar = "=" * len(header)
    print("\n" + bar)
    print("SINGLE-TASK SUCCESS RATES (with Wilson 95% CI)")
    print(bar)
    print(header)
    print("-" * len(header))
    for r in rows:
        ci_str = f"[{r['ci_lo']:.2f}, {r['ci_hi']:.2f}]"
        ts_str = f"{r['tool_selected_rate']:.2f}" if "tool_selected_rate" in r else "   -"
        print(
            f"{r['model']:<20} {_display_condition(r['condition']):<13} {r['task']:<18} "
            f"{r['success_rate']:>6.2f}  {r['n']:>4}  {ci_str:<16}  {ts_str:>7}"
        )
    print(bar)


def print_per_variant_table(results: list[TaskResult]):
    """Per-(model, condition, task) success rate split across active variants.

    The summary JSON's `per_variant` field carries the same numbers; this is
    just a quick eyeball at the end of a run to spot variants that drift far
    from their cell mean (a signal the variant pool may need adjusting).
    """
    rows = summarize_single_task(results)
    if not rows:
        return
    variants = sorted({int(k) for r in rows for k in r.get("per_variant", {}).keys()})
    if not variants:
        return
    var_cols = "  ".join(f"v{v:>1}".ljust(8) for v in variants)
    header = (
        f"{'Model':<20} {'Condition':<13} {'Task':<18} "
        f"{var_cols}  {'Δ':>5}"
    )
    bar = "=" * len(header)
    print("\n" + bar)
    print(f"PER-VARIANT SUCCESS RATES (active variants: {list(ACTIVE_PROMPT_VARIANTS)})")
    print(bar)
    print(header)
    print("-" * len(header))
    for r in rows:
        cells = []
        rates: list[float] = []
        for v in variants:
            cell = r["per_variant"].get(str(v))
            if not cell or cell["n"] == 0:
                cells.append("  -    ")
                continue
            rates.append(cell["success_rate"])
            cells.append(f"{cell['success_rate']:.2f}({cell['n']:>2})")
        spread = (max(rates) - min(rates)) if rates else 0.0
        cells_str = "  ".join(c.ljust(8) for c in cells)
        print(
            f"{r['model']:<20} {_display_condition(r['condition']):<13} {r['task']:<18} "
            f"{cells_str}  {spread:>5.2f}"
        )
    print(bar)


def summarize_chains(chain_results: list[dict]) -> list[dict]:
    """Attach Wilson CI to each chain result row."""
    rows: list[dict] = []
    for r in chain_results:
        lo, hi = wilson_ci(r["successes"], r["samples"])
        rows.append({**r, "ci_lo": round(lo, 4), "ci_hi": round(hi, 4)})
    return rows


def print_chain_table(chain_results: list[dict]):
    if not chain_results:
        return
    rows = summarize_chains(chain_results)
    header = f"{'Model':<20} {'Condition':<13} {'Chain n':>7}  {'Rate':>6}  {'N':>4}  {'95% CI':<16}"
    bar = "=" * len(header)
    print("\n" + bar)
    print("MULTI-TASK CHAIN SUCCESS RATES (with Wilson 95% CI)")
    print(bar)
    print(header)
    print("-" * len(header))
    # Sort by (model, with_tools desc so tools comes first, chain_length)
    rows_sorted = sorted(
        rows,
        key=lambda r: (r["model"], not r.get("with_tools", True), r["chain_length"]),
    )
    for r in rows_sorted:
        cond = "tools" if r.get("with_tools", True) else "no-tools"
        ci_str = f"[{r['ci_lo']:.2f}, {r['ci_hi']:.2f}]"
        print(
            f"{r['model']:<20} {_display_condition(cond):<13} {r['chain_length']:>7}  "
            f"{r['success_rate']:>6.2f}  {r['samples']:>4}  {ci_str:<16}"
        )
    print(bar)


def save_results(
    single: list[TaskResult],
    chains: list[dict],
    output_dir: Path,
    meta: dict | None = None,
):
    output_dir.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")

    p1 = output_dir / f"single_task_{ts}.json"
    p1.write_text(json.dumps([asdict(r) for r in single], indent=2))
    print(f"\nSaved single-task results -> {p1}")

    if chains:
        p2 = output_dir / f"chain_{ts}.json"
        p2.write_text(json.dumps(chains, indent=2))
        print(f"Saved chain results       -> {p2}")

    # Aggregated summary with N and Wilson 95% CIs for downstream analysis.
    # `meta` records the CLI knobs that distinguish this run from others in
    # the same results/ tree (host, condition split, filter, prompt, think).
    # Without it, remote/local and tools/no-tools runs look identical at the
    # summary level and can only be told apart by result-dir naming.
    summary = {
        "single_task": summarize_single_task(single) if single else [],
        "chains": summarize_chains(chains) if chains else [],
    }
    if meta:
        summary["meta"] = meta
    p3 = output_dir / f"summary_{ts}.json"
    p3.write_text(json.dumps(summary, indent=2))
    print(f"Saved summary              -> {p3}")
