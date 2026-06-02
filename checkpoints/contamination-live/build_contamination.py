"""FULL 5-MODEL contamination deck — canonical vs anon, COMPLETE corpora.

`.local` reproduction built after the 2026-06-02 sync. All 5 models are now
complete in BOTH corpora (Qwen3.5-9B's anon think-on with-tools cell landed,
7240 → 9120; canonical 0.8B was reran + deduped on 06-01). No model is held out
and nothing is in flight.

Reuses the shared build_compare_deck.py figure/table functions unchanged (Δ
metric byte-identical to the per-experiment decks); inlines main()'s slide
assembly only so the subtitle + prose slides reflect the now-COMPLETE coverage
(the shared script's baked prose still describes the earlier in-flight state).

Shared build_compare_deck.py / build_deck.py are NOT modified.

Run from the repo root:
    .venv/bin/python3 .local/decks_full_5model/build_contamination.py
"""
from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS = Path("/Users/omereliyahu/personal/pddl-copilot-experiments"
                "/.claude/skills/analyzer/scripts")
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import build_deck as bd          # noqa: E402
import build_compare_deck as bcd  # noqa: E402

# Full roster (this is bcd's default; set explicitly for clarity).
bcd.MODEL_ORDER = ["Qwen3_5_0_8B", "Qwen3_5_4B", "Qwen3_5_9B", "gemma4_26b-a4b", "qwen3_6_35b"]

CANON_REL = "results/sweep5v2-live"
ANON_REL = "results/sweep6-live"
CANON_LABEL = "canonical (sweep-5v2)"
ANON_LABEL = "anon (sweep-6)"
MIN_N = 50
OUT_PPTX = Path("/Users/omereliyahu/personal/pddl-copilot-experiments"
                "/checkpoints/contamination-live/pddl_copilot_contamination_live.pptx")


def main() -> None:
    repo = Path(bcd.__file__).resolve().parents[4]
    CANON = bd.load_all(repo / CANON_REL)
    ANON = bd.load_all(repo / ANON_REL)

    matched = [k for k in sorted(set(CANON) & set(ANON)) if k[0] in bcd.MODEL_ORDER]
    print("=== (model, think, arm) MATCHED keys ===")
    for k in matched:
        print(f"  {k}   n_canon={len(CANON[k])}  n_anon={len(ANON[k])}")
    print(f"models: {bcd.MODEL_ORDER}\n")

    OUT_PPTX.parent.mkdir(parents=True, exist_ok=True)
    fig_dir = OUT_PPTX.with_suffix("")
    fig_dir = fig_dir.parent / (fig_dir.name + "_figs")
    fig_dir.mkdir(parents=True, exist_ok=True)

    prs = bd._make_pptx()
    bd.add_title_slide(
        prs,
        "PDDL Copilot — Contamination Probe: canonical vs anonymised corpus — FULL 5-model, COMPLETE",
        f"{CANON_LABEL}  vs  {ANON_LABEL}  ·  Δ = canonical − anon success (pp)  ·  "
        f"clean probe = no-tools neutral arm  ·  COMPLETE corpora: no-tools 4560/side, with-tools "
        f"9120/side, both corpora, all 5 models  ·  rebuild 2026-06-02 (Qwen3.5-9B anon cell completed; "
        f"nothing in flight)",
    )

    bd.add_text_slide(prs, "How to read this deck", [
        f"• Two corpora, same matrix: {CANON_LABEL} uses the regular domains/; {ANON_LABEL} "
        f"uses domains-anon/ — the SAME domains, lexically renamed (predicates/types/objects scrambled).",
        "• Δ = canonical success − anon success (percentage points). Δ>0 (RED) = the model does better when "
        "domains carry their real names = consistent with MEMORISATION of the canonical domains during "
        "pre-training (contamination). Δ<0 (BLUE) = anon scored higher.",
        "• ONE table per arm. Rows = model × think; the 5 left columns are the per-task Δ; the right ST "
        "column is the mean of that row's task Δ. A BOXED, bold cell = the canonical and anon Wilson 95% "
        "CIs are DISJOINT — a real drift, not noise. '—' = a side below the min-n threshold.",
        "• The CLEAN probe is the no-tools neutral arm (nt-neut): with no tools, success rides purely on the "
        "model's own knowledge of the domain, so memorisation would surface most starkly there. Lead with it.",
        "• With-tools arms (tl-neut / tl-ster) measure tool-assisted success — the planner/validator can solve "
        "regardless of domain names, so Δ there reflects reasoning / tool-use variance, not pure recall. Read "
        "those tables as a secondary finding, not a contamination probe.",
        "• Metric = runner-scored success (each trial judged against its OWN corpus's ground truth). "
        "Wilson 95% CIs throughout.",
        "• COMPLETE: all 5 models, both corpora, every cell at full denominator. Nothing in flight.",
    ])

    for arm in bcd.ARM_ORDER:
        png = fig_dir / f"delta_table_{arm}.png"
        bcd.fig_delta_table(CANON, ANON, arm, MIN_N, CANON_LABEL, ANON_LABEL, png)
        clean = "  (clean contamination probe)" if arm == "nt-neut" else "  (secondary — tool-assisted)"
        extra = (" The only boxed cells (validate_plan × think=on) are a TOKENISATION artifact — anon prompts "
                 "tokenise ~5% longer → more think=on truncation; see the final slide.") if arm == "nt-neut" else ""
        bd.add_image_slide(
            prs, f"Δ success table · {bcd.ARM_DISP[arm]}{clean}", png,
            caption=f"Per-task Δ = {CANON_LABEL} − {ANON_LABEL} success (pp) for the "
                    f"{bcd.ARM_DISP[arm]} arm. Rows = model × think; right ST column = mean of the task Δ. "
                    f"Red = canonical advantage; blue = anon higher. Boxed+bold = CI-disjoint. "
                    f"'—' = a side below {MIN_N} trials.{extra}")

    rows = bcd.summary_rows(CANON, ANON, MIN_N)
    bd.add_table_slide(
        prs, "Contamination Δ summary — ST-mean per matched cell",
        ["arm", "model", "think", f"{CANON_LABEL} ST%", f"{ANON_LABEL} ST%",
         "ΔST (pp)", "tasks CI-disjoint", "n canon/anon"],
        rows,
        notes="ST% = unweighted mean over tasks with ≥min-n trials both sides. "
              "ΔST>0 = canonical advantage. 'tasks CI-disjoint' counts how many of the cell's tasks "
              "have non-overlapping canonical/anon Wilson CIs.")

    bd.add_text_slide(prs, "Observed pattern, coverage & next steps", [
        "HEADLINE — the CLEAN no-tools neutral probe is essentially NULL: ST-mean |Δ| ≤ 1.3pp (think=off) and "
        "≤ 2.6pp (on) across all 5 models, and think=off has ZERO CI-disjoint task cells. No model carries a "
        "clean-probe contamination signal.",
        "THE ONLY CLEAN-PROBE DRIFT IS A TOKENISATION ARTIFACT, not contamination. The sole CI-disjoint nt-neut "
        "cells are validate_plan × think=on (Qwen3.5-4B +6.3, Qwen3.5-9B +4.0, Qwen3.6-35B +4.3pp canonical). "
        "But anon domain names tokenise ~5% LONGER, so anon trials hit the think=on decode-budget cliff MORE: "
        "the truncation Δ tracks the success Δ almost 1:1, and success GIVEN completion is ~equal across "
        "corpora. The 'edge' is the extra truncation, not better domain knowledge. Net: no genuine "
        "contamination survives on the clean probe.",
        "WHERE THE NULL IS INFORMATIVE: it is meaningful only where no-tools isn't floored — Gemma4-off "
        "(~50%) and Qwen3.6-off (~49%) have ample headroom for a memorisation gap, and none appears. At the "
        "floor (Qwen3.5-0.8B, and small models with think=on, ~0%) a null is uninformative — no room for a "
        "gap either way.",
        "WITH-TOOLS (tl-neut / tl-ster) — small, MIXED-SIGN drifts concentrated in the validation tasks, in "
        "BOTH directions. Read as SECONDARY, not a contamination probe: with tools the planner/validator "
        "solves regardless of domain names, so any edge is tool-interaction, not model recall. Two confounds "
        "inflate these arms: (1) the validate_plan / validate_domain components overlap the known FastMCP "
        "arg-error binning artifact (see project_validate_plan_fp_scoring_bug); (2) the canonical with-tools "
        "cells were rerun under the UPDATED pddl-copilot MCP server (validator arg-error fixes, main 5e4f9c0) "
        "while the anon with-tools cells were not — so a canon−anon with-tools Δ conflates MCP/vLLM TOOLING "
        "VERSION with corpus. Do not read these as recall.",
        "CORRECTION vs the preliminary build: the earlier verdict_mismatch (+1.7pp) 'reasoning-degradation' "
        "mechanism is RETRACTED — it was an artifact of only Gemma4 + Qwen3.6 being complete in that build, "
        "and the with-tools deficit is not in verdict_mismatch.",
        "COVERAGE (sync 2026-06-02): FULLY COMPLETE — all 5 models, both corpora, every cell at full "
        "denominator (no-tools 4560 trials/side, with-tools 9120 trials/side). Qwen3.5-9B's anon think-on "
        "with-tools cell completed (7240→9120) and nothing is in flight. The conclusion rests on the clean "
        "no-tools probe and is now final, not provisional.",
        "BOTTOM LINE: NO evidence of train-set contamination. The clean no-tools probe is null on every "
        "task/model under think=off, and the only think=on CI-disjoint cells (validate_plan) are fully "
        "explained by a differential-truncation artifact (anon prompts ~5% longer → more decode-cliff "
        "truncation), NOT recall. The with-tools deltas are small, mixed-sign, secondary and version-confounded "
        "— they do not support a contamination claim either.",
        "NEXT: a per-DOMAIN Δ (canonical-blocksworld vs anon-blocksworld) localises which specific domains, "
        "if any, a model memorised; it needs the anon↔canonical name mapping. Rebuild after any further sync: "
        "re-run filter_variants on both roots, then re-run this script.",
    ])

    prs.save(str(OUT_PPTX))
    print(f"wrote {OUT_PPTX}")


if __name__ == "__main__":
    main()
