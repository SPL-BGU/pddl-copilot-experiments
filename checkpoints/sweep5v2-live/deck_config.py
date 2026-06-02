"""Live deck config for in-flight sweep-5v2 (CANONICAL corpus, v11-v16 active prompts).

Consumed by .claude/skills/analyzer/scripts/build_deck.py. Source root is
the synthetic `results/sweep5v2-live/` produced by:

    python3 .claude/skills/analyzer/scripts/filter_variants.py \\
        --src sweep56-cluster-<YYYYMMDD> --dst sweep5v2-live \\
        --model-glob 'slurm_vllm_*_sweep5v2' --arm both --min-out 100

sweep-5v2 = the CANONICAL (regular, non-anonymised) half of the contamination
probe. no-tools cells are REUSED from sweep-5 (each complete at 4560 trials,
neutral v11-v13); with-tools cells were rerun fresh under the updated
pddl-copilot MCP server (validator arg-error fixes, main 5e4f9c0). Pair this
deck against the sweep-6 (anon corpus, domains-anon/) deck — the canonical-vs-anon
delta on the matched cells is the contamination signal.

The min-out is intentionally permissive (100, not the canonical 4560/9120) so
partial cells appear in the deck while the sweep is still running. Cells below
100 v11-v16 trials are omitted; bars will be missing for those.

Rebuild after a fresh sync by re-running the filter + this build.
"""

RESULTS = "results/sweep5v2-live"
OUT_PPTX = "checkpoints/sweep5v2-live/pddl_copilot_sweep5v2_live.pptx"

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

TITLE = "PDDL Copilot — sweep-5v2 / CANONICAL LIVE (in-flight, v11-v16 active prompts)"
SUBTITLE = (
    "Qwen3.5:0.8B / 4B / 9B · gemma4:26b-a4b · qwen3.6:35b · "
    "sweep-5v2 = CANONICAL corpus (regular domains/, NOT anonymised) · "
    "active arms: neutral v11-v13 + steered v14-v16 · all-tools vs no-tools · think on/off · "
    "no-tools REUSED from sweep-5 (complete, 4560/cell); with-tools rerun fresh under updated MCP server · "
    "rebuild 2026-06-01 — CANONICAL corpus COMPLETE: all 20 cells (no-tools 4560/cell, "
    "with-tools 9120/cell) across all 5 models; Qwen3.5-0.8B with-tools rerun completed, verified clean + "
    "deduped (9120) 2026-06-01. min-out 100 retained for parity with the anon (sweep-6) deck."
)

SLIDE_CAPTIONS = {
    "success_off":
        "Per-task success on sweep-5v2 CANONICAL cells (v11-v16). 2026-05-31: COMPLETE — no-tools 4560/cell "
        "(reused sweep-5), with-tools 9120/cell, all 5 models. "
        "Pair against the sweep-6 (anon) deck for the contamination delta.",
    "success_on":
        "Same chart, think=on. Note Qwen3.5-0.8B on/no-tools is dominated by truncated_no_answer "
        "(reasoning consumes the entire output budget). This is the CANONICAL baseline; the anon (sweep-6) "
        "deck shows the same cells on the lexically-renamed corpus.",
    "tool_selection":
        "% of with-tools trials where the model invoked the expected planner/validator tool, "
        "over v11-v16 cells (all 5 models, complete).",
    "failure_breakdown_off":
        "100%-stacked share of failure reasons per (model × arm × task) at think=off, CANONICAL corpus. "
        "verdict_mismatch and format_parse_fail dominate; truncated_no_answer present on rows that hit the "
        "output cap. think_overflow is empty by gate — only think=on rows can carry it.",
    "failure_breakdown_on":
        "Same chart at think=on. The light-pink think_overflow slab is the read-time relabel: rows where the "
        "model exhausted the output budget without emitting a visible response (vLLM qwen3 reasoning-parser "
        "eats partial `<think>` content on length-truncation). Qwen3.5 sizes are dominated by think_overflow "
        "on no-tools tasks; gemma4 (no reasoning parser) stays on truncated_no_answer.",
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
