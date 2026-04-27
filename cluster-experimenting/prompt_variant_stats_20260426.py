"""Per-(task, prompt_variant) success-rate breakdown for the 26042026 sweep.

Walks every `single_task_*.json` under
`checkpoints/cluster-26042026/results_extracted/`, pools trials by task and
prompt_variant (0-4), and emits Wilson 95% CIs. Also reports a per-prompt-style
(minimal/guided) and per-model split so the answer to "which variant is best"
can be checked for stability across conditions.

One-off analysis script, not part of the harness. Outputs:
- `checkpoints/cluster-26042026/prompt_variant_stats.csv` (machine-readable)
- `checkpoints/cluster-26042026/prompt_variant_stats.md`  (human-readable)
"""

from __future__ import annotations

import csv
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHECKPOINT = ROOT / "checkpoints" / "cluster-26042026"
RESULTS_DIR = CHECKPOINT / "results_extracted"
TASKS = ("solve", "validate_domain", "validate_problem", "validate_plan", "simulate")
VARIANTS = (0, 1, 2, 3, 4)


def wilson_ci(successes: int, total: int, z: float = 1.96) -> tuple[float, float]:
    if total == 0:
        return (0.0, 0.0)
    phat = successes / total
    denom = 1 + z * z / total
    center = (phat + z * z / (2 * total)) / denom
    half = (z * math.sqrt((phat * (1 - phat) + z * z / (4 * total)) / total)) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def load_trials() -> list[dict]:
    if not RESULTS_DIR.is_dir():
        sys.exit(f"missing {RESULTS_DIR}")
    trials: list[dict] = []
    for run_dir in sorted(RESULTS_DIR.iterdir()):
        if not run_dir.is_dir():
            continue
        for path in run_dir.glob("single_task_*.json"):
            with path.open() as fp:
                records = json.load(fp)
            for rec in records:
                trials.append(rec)
    return trials


def aggregate(
    trials: list[dict],
    key_fn,
    *,
    only_tools: bool | None = None,
) -> dict:
    agg: dict = defaultdict(lambda: {"n": 0, "succ": 0, "tool_sel": 0})
    for r in trials:
        if only_tools is True and not r.get("with_tools"):
            continue
        if only_tools is False and r.get("with_tools"):
            continue
        key = key_fn(r)
        if key is None:
            continue
        agg[key]["n"] += 1
        if r.get("success"):
            agg[key]["succ"] += 1
        if r.get("tool_selected"):
            agg[key]["tool_sel"] += 1
    return agg


def fmt_rate(succ: int, n: int) -> str:
    if n == 0:
        return "—"
    rate = succ / n
    lo, hi = wilson_ci(succ, n)
    return f"{rate:.3f} [{lo:.3f},{hi:.3f}] (n={n})"


def render_overall(trials: list[dict]) -> tuple[str, list[dict]]:
    """Pooled across all conditions: rows per (task, variant)."""
    agg = aggregate(trials, lambda r: (r["task"], r["prompt_variant"]))
    lines = ["## 1. Pooled across all conditions and models",
             "",
             "Success rate (Wilson 95% CI) per (task × prompt_variant). Pooled over "
             "5 models × {no-tools, tools×4} × 10 problems.",
             "",
             "| task | v0 | v1 | v2 | v3 | v4 | best |",
             "|------|----|----|----|----|----|------|"]
    csv_rows: list[dict] = []
    for task in TASKS:
        cells = []
        rates: dict[int, float] = {}
        for v in VARIANTS:
            d = agg.get((task, v), {"n": 0, "succ": 0})
            cells.append(fmt_rate(d["succ"], d["n"]))
            rates[v] = (d["succ"] / d["n"]) if d["n"] > 0 else float("nan")
            csv_rows.append({
                "scope": "pooled",
                "task": task,
                "prompt_variant": v,
                "n": d["n"],
                "successes": d["succ"],
                "success_rate": round(rates[v], 4) if d["n"] else "",
                "ci_lo": round(wilson_ci(d["succ"], d["n"])[0], 4) if d["n"] else "",
                "ci_hi": round(wilson_ci(d["succ"], d["n"])[1], 4) if d["n"] else "",
            })
        finite = {v: r for v, r in rates.items() if not math.isnan(r)}
        best_v = max(finite, key=finite.get) if finite else "-"
        lines.append("| " + " | ".join([task] + cells + [f"v{best_v}"]) + " |")
    return "\n".join(lines), csv_rows


def render_by_style(trials: list[dict]) -> tuple[str, list[dict]]:
    """Tools-only: per (prompt_style, task, variant) — does the winner flip?"""
    agg = aggregate(
        trials,
        lambda r: (
            r.get("prompt_style"),
            r["task"],
            r["prompt_variant"],
        ),
        only_tools=True,
    )
    lines = ["", "## 2. Tools-on, split by `prompt_style` (minimal vs guided)",
             "",
             "Same statistic, restricted to with-tools trials, split by the "
             "system-prompt style. Lets us check whether the best variant is "
             "stable across system prompts."]
    csv_rows: list[dict] = []
    for style in ("minimal", "guided"):
        lines.append("")
        lines.append(f"### prompt_style = `{style}`")
        lines.append("")
        lines.append("| task | v0 | v1 | v2 | v3 | v4 | best |")
        lines.append("|------|----|----|----|----|----|------|")
        for task in TASKS:
            cells = []
            rates: dict[int, float] = {}
            for v in VARIANTS:
                d = agg.get((style, task, v), {"n": 0, "succ": 0})
                cells.append(fmt_rate(d["succ"], d["n"]))
                rates[v] = (d["succ"] / d["n"]) if d["n"] > 0 else float("nan")
                csv_rows.append({
                    "scope": f"prompt_style={style}",
                    "task": task,
                    "prompt_variant": v,
                    "n": d["n"],
                    "successes": d["succ"],
                    "success_rate": round(rates[v], 4) if d["n"] else "",
                    "ci_lo": round(wilson_ci(d["succ"], d["n"])[0], 4) if d["n"] else "",
                    "ci_hi": round(wilson_ci(d["succ"], d["n"])[1], 4) if d["n"] else "",
                })
            finite = {v: r for v, r in rates.items() if not math.isnan(r)}
            best_v = max(finite, key=finite.get) if finite else "-"
            lines.append("| " + " | ".join([task] + cells + [f"v{best_v}"]) + " |")
    return "\n".join(lines), csv_rows


def render_by_model(trials: list[dict]) -> tuple[str, list[dict]]:
    """Pooled across conditions, split by model — sanity check."""
    models = sorted({r["model"] for r in trials})
    agg = aggregate(trials, lambda r: (r["model"], r["task"], r["prompt_variant"]))
    lines = ["", "## 3. Per-model best-variant summary (pooled across conditions)",
             "",
             "Best variant per (model, task) by raw success rate. Wide spreads "
             "indicate fragile results; tied/near-tied cells are essentially noise.",
             "",
             "| model | " + " | ".join(TASKS) + " |",
             "|" + "|".join(["---"] * (len(TASKS) + 1)) + "|"]
    csv_rows: list[dict] = []
    for model in models:
        cells = []
        for task in TASKS:
            rates: dict[int, tuple[float, int]] = {}
            for v in VARIANTS:
                d = agg.get((model, task, v), {"n": 0, "succ": 0})
                if d["n"] > 0:
                    rates[v] = (d["succ"] / d["n"], d["n"])
                csv_rows.append({
                    "scope": f"model={model}",
                    "task": task,
                    "prompt_variant": v,
                    "n": d["n"],
                    "successes": d["succ"],
                    "success_rate": round(d["succ"] / d["n"], 4) if d["n"] else "",
                    "ci_lo": round(wilson_ci(d["succ"], d["n"])[0], 4) if d["n"] else "",
                    "ci_hi": round(wilson_ci(d["succ"], d["n"])[1], 4) if d["n"] else "",
                })
            if not rates:
                cells.append("—")
                continue
            best_v = max(rates, key=lambda v: rates[v][0])
            best_rate, n = rates[best_v]
            spread = max(r[0] for r in rates.values()) - min(r[0] for r in rates.values())
            cells.append(f"v{best_v} ({best_rate:.2f}, Δ={spread:.2f})")
        lines.append("| " + " | ".join([model] + cells) + " |")
    return "\n".join(lines), csv_rows


def render_full_by_model(trials: list[dict]) -> str:
    """Per-(model, task) full row of all 5 variants for inspection."""
    models = sorted({r["model"] for r in trials})
    agg = aggregate(trials, lambda r: (r["model"], r["task"], r["prompt_variant"]))
    lines = ["", "## 4. Full per-model × per-task × per-variant breakdown",
             "",
             "All five variants laid out per cell so you can see the actual spread "
             "feeding the section-3 winners. Format: `rate (n)`. **Δ** = max - min "
             "across variants; bold cells flag Δ > 0.10 (variant choice meaningfully "
             "moves the number).",
             ""]
    for model in models:
        lines.append(f"### {model}")
        lines.append("")
        lines.append("| task | v0 | v1 | v2 | v3 | v4 | Δ |")
        lines.append("|------|----|----|----|----|----|---|")
        for task in TASKS:
            rates: list[tuple[int, float, int]] = []
            for v in VARIANTS:
                d = agg.get((model, task, v), {"n": 0, "succ": 0})
                rate = (d["succ"] / d["n"]) if d["n"] > 0 else float("nan")
                rates.append((v, rate, d["n"]))
            finite = [r for r in rates if not math.isnan(r[1])]
            if not finite:
                continue
            spread = max(r[1] for r in finite) - min(r[1] for r in finite)
            best_v = max(finite, key=lambda r: r[1])[0]
            worst_v = min(finite, key=lambda r: r[1])[0]
            cells = []
            for v, rate, n in rates:
                if math.isnan(rate):
                    cells.append("—")
                    continue
                tag = ""
                if v == best_v and spread > 0.05:
                    tag = "**"  # bold highest if spread is non-trivial
                cells.append(f"{tag}{rate:.2f}{tag} (n={n})")
            spread_cell = f"**{spread:.2f}**" if spread > 0.10 else f"{spread:.2f}"
            lines.append("| " + " | ".join([task] + cells + [spread_cell]) + " |")
        lines.append("")
    return "\n".join(lines)


def render_style_comparison(trials: list[dict]) -> str:
    """Per (model, prompt_style) avg success rate across all single-task trials —
    answers 'is minimal or guided meaningfully better per model?'"""
    agg = aggregate(
        trials,
        lambda r: (r["model"], r.get("prompt_style")),
        only_tools=True,
    )
    models = sorted({r["model"] for r in trials})
    lines = ["", "## 5. `prompt_style` × model — minimal vs guided",
             "",
             "Tools-on only. Averaged over all single-task trials per (model, style). "
             "If `|Δ|` is small relative to the CI half-width, the two styles are "
             "indistinguishable for that model.",
             "",
             "| model | minimal | guided | Δ (guided − minimal) |",
             "|---|---|---|---|"]
    for model in models:
        m = agg.get((model, "minimal"), {"n": 0, "succ": 0})
        g = agg.get((model, "guided"), {"n": 0, "succ": 0})
        if m["n"] == 0 and g["n"] == 0:
            continue
        m_rate = m["succ"] / m["n"] if m["n"] else 0.0
        g_rate = g["succ"] / g["n"] if g["n"] else 0.0
        m_lo, m_hi = wilson_ci(m["succ"], m["n"])
        g_lo, g_hi = wilson_ci(g["succ"], g["n"])
        delta = g_rate - m_rate
        lines.append(
            f"| {model} | {m_rate:.3f} [{m_lo:.3f},{m_hi:.3f}] (n={m['n']}) "
            f"| {g_rate:.3f} [{g_lo:.3f},{g_hi:.3f}] (n={g['n']}) "
            f"| {delta:+.3f} |"
        )
    return "\n".join(lines)


def render_variant_dropping_advice(trials: list[dict]) -> str:
    """How representative is each variant of the 5-variant mean? This guides
    'if I keep only K variants, which K should I keep'."""
    # Per task, compute the mean across all 5 variants pooled over models, then
    # for each variant rank |variant_rate - all5_mean|.
    by_task_var = aggregate(trials, lambda r: (r["task"], r["prompt_variant"]))
    by_task = aggregate(trials, lambda r: r["task"])
    lines = ["", "## 6. Which variants best approximate the 5-variant mean?",
             "",
             "If you drop to K variants, you want the K whose pooled success rate "
             "is closest to the full-5 mean (so the truncated estimator is "
             "unbiased). Reported per task: |variant rate − 5-variant mean|, "
             "smallest = most representative.",
             "",
             "| task | full-5 mean | rank: closest → farthest |",
             "|------|-------------|--------------------------|"]
    representativeness: dict[int, list[float]] = {v: [] for v in VARIANTS}
    for task in TASKS:
        full = by_task.get(task)
        if not full or full["n"] == 0:
            continue
        full_rate = full["succ"] / full["n"]
        per_var: list[tuple[int, float]] = []
        for v in VARIANTS:
            d = by_task_var.get((task, v))
            if d and d["n"] > 0:
                rate = d["succ"] / d["n"]
                gap = abs(rate - full_rate)
                per_var.append((v, gap))
                representativeness[v].append(gap)
        per_var.sort(key=lambda x: x[1])
        ranking = " → ".join(f"v{v} (Δ={g:.3f})" for v, g in per_var)
        lines.append(f"| {task} | {full_rate:.3f} | {ranking} |")

    lines.append("")
    lines.append("**Average representativeness across all tasks** (lower = more "
                 "robust to use as a substitute for the full sweep):")
    lines.append("")
    avg_gap = {v: (sum(gs) / len(gs) if gs else float("inf"))
               for v, gs in representativeness.items()}
    for v, g in sorted(avg_gap.items(), key=lambda kv: kv[1]):
        lines.append(f"- v{v}: mean |gap| = {g:.4f}")
    return "\n".join(lines)


def main() -> None:
    trials = load_trials()
    if not trials:
        sys.exit("no trials loaded")

    overall_md, overall_csv = render_overall(trials)
    style_md, style_csv = render_by_style(trials)
    model_md, model_csv = render_by_model(trials)
    full_model_md = render_full_by_model(trials)
    style_cmp_md = render_style_comparison(trials)
    drop_advice_md = render_variant_dropping_advice(trials)

    header = [
        "# Prompt-variant (v0-v4) success-rate breakdown — sweep 26042026",
        "",
        f"Loaded {len(trials):,} single-task trials from {RESULTS_DIR.relative_to(ROOT)}.",
        "",
        "Each task uses 5 paraphrased user prompts (run_experiment.py:190 "
        "`PROMPT_TEMPLATES`). `prompt_variant` selects which paraphrase a given "
        "trial used. CIs are Wilson 95%.",
        "",
    ]
    md_path = CHECKPOINT / "prompt_variant_stats.md"
    csv_path = CHECKPOINT / "prompt_variant_stats.csv"
    md_path.write_text(
        "\n".join(header) + overall_md + "\n" + style_md + "\n" + model_md + "\n"
        + full_model_md + "\n" + style_cmp_md + "\n" + drop_advice_md + "\n"
    )

    fields = ["scope", "task", "prompt_variant", "n", "successes",
              "success_rate", "ci_lo", "ci_hi"]
    with csv_path.open("w", newline="") as fp:
        w = csv.DictWriter(fp, fieldnames=fields)
        w.writeheader()
        for row in overall_csv + style_csv + model_csv:
            w.writerow(row)

    sys.stdout.write(f"wrote {md_path.relative_to(ROOT)}\n")
    sys.stdout.write(f"wrote {csv_path.relative_to(ROOT)}\n\n")
    sys.stdout.write(overall_md + "\n")


if __name__ == "__main__":
    main()
