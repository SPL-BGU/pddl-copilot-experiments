"""Deck config for `sweep4-v5-v7-first` — consumed by
.claude/skills/analyzer/scripts/build_deck.py.

Reproduces the deck shipped on 2026-05-20 (commit bb5046a) on the 4-model
multi-model corpus. Update MODEL_ORDER / SLIDE_CAPTIONS as new cells land
and rerun:

    python3 .claude/skills/analyzer/scripts/build_deck.py \\
        --config checkpoints/sweep4-v5-v7-first/deck_config.py
"""

RESULTS = "results/sweep4-v5-v7-first"
OUT_PPTX = "checkpoints/sweep4-v5-v7-first/pddl_copilot_sweep4_v5_v7_first.pptx"

MODEL_ORDER = ["Qwen3_5_0_8B", "Qwen3_5_4B", "gemma4_26b-a4b", "qwen3_6_35b"]
MODEL_DISP = {
    "Qwen3_5_0_8B":   "Qwen3.5-0.8B",
    "Qwen3_5_4B":     "Qwen3.5-4B",
    "gemma4_26b-a4b": "Gemma4-26B-A4B",
    "qwen3_6_35b":    "Qwen3.6-35B-A3B",
}

# Sweep-4 part 1: only all-tools and no-tools were executed; per-task arm
# retired in sweep-5. `guided` was already disabled in the runner.
COND_ORDER = ["tools_all_minimal", "no-tools"]
COND_DISP = {
    "tools_all_minimal": "all-tools",
    "no-tools": "no-tools",
}

TITLE = "PDDL Copilot — sweep4-v5-v7-first (in-progress, 4 models)"
SUBTITLE = (
    "Qwen3.5:0.8B (all 4 cells) · Qwen3.5:4B (off/no-tools) · "
    "gemma4:26b-a4b (2 cells) · qwen3.6:35b (3 cells) · "
    "sweep-4 prompts v5/v6/v7 ('part 1 — explicit tool call') · "
    "all-tools vs no-tools · think on/off"
)

SLIDE_CAPTIONS = {
    "success_off":
        "Per-task success on 4560 trials per cell (3 variants × {100, 120, 200, 1000, 100} problems). "
        "Multi-model view of the v5/v6/v7 prompt rewrite. Larger models (qwen3.6:35b, gemma4:26b-a4b) "
        "reach near-ceiling with-tools across all 5 tasks; no-tools validate_* collapsed for every model "
        "(VERDICT-trailer drop in the v5/v6/v7 no-tools template — finding 1 in sweep4_plan_new_prompts.md). "
        "Missing bars = cell not yet complete.",
    "success_on":
        "Same chart, think=on. Only Qwen3.5:0.8B (both cells), gemma4 (on/tools_all only), and "
        "qwen3.6:35b (on/tools_all only) have completed on-cells in the current sync. "
        "Note: qwen3.6:35b on/tools_all and gemma4 on/tools_all rival or beat their off counterparts on most tasks.",
    "tool_selection":
        "% of with-tools trials where the model invoked the expected planner/validator tool. "
        "v5/v6/v7 prompts explicitly name the tool arguments — selection sits at the ceiling for every task "
        "across all models with completed all-tools cells.",
    "successful_tool_use":
        "Light bar = % of with-tools trials where the model called the matching tool. "
        "Dark bar = % where both (a) the right tool was called AND (b) the result was scored success. "
        "The (sel% − dark%) gap is the failure mode after tool selection: "
        "verdict_mismatch / tool_error / loop_exhausted.",
    "confusion_off":
        "One row per model; columns = validate_domain, validate_problem, validate_plan. "
        "True positive = correctly predicted VALID, true negative = correctly predicted INVALID. "
        "'no-ans' counts truncated / parse-fail trials excluded from prec/rec/acc.",
    "confusion_on":
        "think=on bloats output budget — note the no-ans count: at this corpus the entire response is "
        "reasoning text with no JSON verdict (truncated_no_answer + format_parse_fail dominate).",
}
