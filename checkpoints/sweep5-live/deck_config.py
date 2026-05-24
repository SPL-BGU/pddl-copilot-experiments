"""Live deck config for in-flight sweep-5 (v11-v16 active prompts).

Consumed by .claude/skills/analyzer/scripts/build_deck.py. Source root is
the synthetic `results/sweep5-live/` produced by:

    python3 .claude/skills/analyzer/scripts/filter_variants.py \\
        --src sweep5-cluster-<YYYYMMDD> --dst sweep5-live \\
        --model-glob 'slurm_vllm_*' --arm both --min-out 100

The min-out is intentionally permissive (100, not the canonical 4560) so
partial cells appear in the deck while the sweep is still running. Cells
below 100 v11-v16 trials are omitted; bars will be missing for those.

Rebuild after a fresh sync by re-running the filter + this build.
"""

RESULTS = "results/sweep5-live"
OUT_PPTX = "checkpoints/sweep5-live/pddl_copilot_sweep5_live.pptx"

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

TITLE = "PDDL Copilot — sweep-5 LIVE (in-flight, v11-v16 active prompts)"
SUBTITLE = (
    "Qwen3.5:0.8B / 4B / 9B · gemma4:26b-a4b · qwen3.6:35b · "
    "sweep-5 active arms: neutral v11-v13 + steered v14-v16 · "
    "all-tools vs no-tools · think on/off · "
    "PRELIMINARY — partial cells (min-out 100 trials); missing bars = cell not yet at threshold"
)

SLIDE_CAPTIONS = {
    "success_off":
        "PRELIMINARY view: per-task success on partial sweep-5 cells (v11-v16, min-out 100). "
        "Missing bars = cell not yet at threshold. As of this rebuild, qwen3_6_35b and the smaller "
        "Qwen3.5 sizes have the most coverage; gemma4 no-tools cells lag.",
    "success_on":
        "Same chart, think=on. Note Qwen3.5-0.8B on/no-tools is dominated by truncated_no_answer "
        "(reasoning consumes the entire output budget). gemma4 on/no-tools is below the min-out "
        "threshold so has no bar.",
    "tool_selection":
        "% of with-tools trials where the model invoked the expected planner/validator tool, "
        "over v11-v16 partial cells.",
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
