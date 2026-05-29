"""Live deck config for in-flight sweep-6 (v11-v16 active prompts).

Consumed by .claude/skills/analyzer/scripts/build_deck.py. Source root is
the synthetic `results/sweep6-live/` produced by:

    python3 .claude/skills/analyzer/scripts/filter_variants.py \\
        --src sweep6-cluster-<YYYYMMDD> --dst sweep6-live \\
        --model-glob 'slurm_vllm_*' --arm both --min-out 100

The min-out is intentionally permissive (100, not the canonical 4560) so
partial cells appear in the deck while the sweep is still running. Cells
below 100 v11-v16 trials are omitted; bars will be missing for those.

Rebuild after a fresh sync by re-running the filter + this build.
"""

RESULTS = "results/sweep6-live"
OUT_PPTX = "checkpoints/sweep6-live/pddl_copilot_sweep6_live.pptx"

MODEL_ORDER = ["Qwen3_5_0_8B", "Qwen3_5_4B", "Qwen3_5_9B", "gemma4_26b-a4b", "qwen3_6_35b"]
MODEL_DISP = {
    "Qwen3_5_0_8B":   "Qwen3.5-0.8B",
    "Qwen3_5_4B":     "Qwen3.5-4B",
    "Qwen3_5_9B":     "Qwen3.5-9B",
    "gemma4_26b-a4b": "Gemma4-26B-A4B",
    "qwen3_6_35b":    "Qwen3.6-35B-A3B",
}

COND_ORDER = ["tools_all_minimal", "no-tools"]
COND_DISP = {
    "tools_all_minimal": "all-tools",
    "no-tools": "no-tools",
}

TITLE = "PDDL Copilot — sweep-6 / anon-probe LIVE (in-flight, v11-v16 active prompts)"
SUBTITLE = (
    "Qwen3.5:0.8B / 4B / 9B · gemma4:26b-a4b · qwen3.6:35b · "
    "sweep-6 = anon-probe (domains-anon/, lexically renamed corpus) · "
    "sweep-6 active arms: neutral v11-v13 + steered v14-v16 · "
    "all-tools vs no-tools · think on/off · "
    "PRELIMINARY rebuild 2026-05-29 (~1 day into 48h jobs). with-tools coverage = gemma4 + "
    "qwen3.6:35b only (Qwen3.5 with-tools cells still PENDING); no-tools missing 9B-off (unstarted) "
    "and only-partial on 4B. min-out 100 trials; missing bars = cell not yet at threshold."
)

SLIDE_CAPTIONS = {
    "success_off":
        "PRELIMINARY view (2026-05-29): per-task success on partial sweep-6 ANON cells (v11-v16, min-out 100). "
        "Missing bars = cell not yet at threshold. with-tools arms exist only for gemma4 + qwen3.6:35b so far; "
        "the Qwen3.5 sizes show no-tools bars only (their with-tools cells are still queued). 4B no-tools is "
        "very early (~150 trials) so its CIs are wide.",
    "success_on":
        "Same chart, think=on. Note Qwen3.5-0.8B on/no-tools is dominated by truncated_no_answer "
        "(reasoning consumes the entire output budget). Pair against the sweep5v2 (canonical) deck — "
        "the anon-vs-canonical gap on these same cells is the contamination signal.",
    "tool_selection":
        "% of with-tools trials where the model invoked the expected planner/validator tool, "
        "over v11-v16 partial cells.",
    "failure_breakdown_off":
        "100%-stacked share of failure reasons per (model × arm × task) at think=off. "
        "verdict_mismatch and format_parse_fail dominate; truncated_no_answer present on the "
        "few rows that did hit the output cap. think_overflow is empty by gate — only think=on "
        "rows can carry it.",
    "failure_breakdown_on":
        "Same chart at think=on. The light-pink think_overflow slab is the 2026-05-25 read-time "
        "relabel: rows where the model exhausted the output budget without emitting a visible "
        "response (vLLM qwen3 reasoning-parser eats partial `<think>` content on length-truncation). "
        "Qwen3.5 sizes are dominated by think_overflow on no-tools tasks; gemma4 (no reasoning parser) "
        "stays on truncated_no_answer because its response field is non-empty.",
    "successful_tool_use":
        "Light bar = % of with-tools trials where the model called the matching tool. "
        "Dark bar = % where both (a) the right tool was called AND (b) the result was scored success. "
        "The (sel% − dark%) gap is the failure mode after tool selection: "
        "verdict_mismatch / tool_error / loop_exhausted.",
    "confusion_off":
        "One row per model; columns = validate_domain, validate_problem, validate_plan. "
        "TP = correctly predicted VALID, TN = correctly predicted INVALID. "
        "'no-ans' counts truncated / parse-fail trials excluded from prec/rec/acc.",
    "confusion_on":
        "think=on bloats output budget — note the no-ans count: at this corpus the entire response is "
        "reasoning text with no JSON verdict (truncated_no_answer + format_parse_fail dominate).",
}
