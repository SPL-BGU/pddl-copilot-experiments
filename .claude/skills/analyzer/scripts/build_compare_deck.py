"""Build a contamination-probe comparison deck: canonical vs anon corpus.

Pairs two *filtered* results roots cell-by-cell over (model, think, arm, task),
computes per-cell success — runner-scored `r["success"]`, NOT a re-derived
ground truth (the anon corpus renames problem_name/plan_label, so `truth_for`
would be wrong on that side; the runner already scored each trial against its
own corpus) — with Wilson 95% CIs on each side, and renders the
canonical−anon delta as a per-arm Δ table (per-task cells, CI-disjoint cells
boxed as the "noticeable drift" highlight) plus an ST-mean summary table.

  Δ>0  (red)  = canonical better than anon = consistent with the model having
                MEMORISED the canonical (non-anonymised) domains.
  Δ≈0         = no contamination signal. EXPECTED for with-tools arms, where
                the planner/validator solves the task regardless of domain
                names; the clean probe is the no-tools neutral (nt-neut) arm,
                pure model knowledge.

Metric is identical to build_deck (imports its load_all / task_success_rate),
so this deck and the two per-experiment decks read off the same numbers.

Usage:
    python3 .claude/skills/analyzer/scripts/build_compare_deck.py \\
        --canon results/sweep5v2-live --anon results/sweep6-live \\
        --out   checkpoints/contamination-live/pddl_copilot_contamination_live.pptx \\
        --canon-label "canonical (sweep-5v2)" --anon-label "anon (sweep-6)" \\
        --min-n 50
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

# build_deck lives next to this file; put the scripts dir on sys.path so the
# `import build_deck` below resolves regardless of the caller's CWD.
_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from _constants import TASKS, TASK_LABELS, wilson_ci  # noqa: E402
import build_deck as bd  # noqa: E402  (load_all, task_success_rate, slide writers, _make_pptx)

MODEL_ORDER = ["Qwen3_5_0_8B", "Qwen3_5_4B", "Qwen3_5_9B", "gemma4_26b-a4b", "qwen3_6_35b"]
MODEL_DISP = {
    "Qwen3_5_0_8B":   "Qwen3.5-0.8B",
    "Qwen3_5_4B":     "Qwen3.5-4B",
    "Qwen3_5_9B":     "Qwen3.5-9B",
    "gemma4_26b-a4b": "Gemma4-26B-A4B",
    "qwen3_6_35b":    "Qwen3.6-35B-A3B",
}
ARM_ORDER = ["nt-neut", "tl-neut", "tl-ster"]
ARM_DISP = {"nt-neut": "no-tools(neut)", "tl-neut": "tools(neut)", "tl-ster": "tools(steer)"}

# A cell whose canonical/anon CIs are disjoint is boxed; this is the
# "noticeable drift" highlight the deck leads with.


def _model_idx(m: str) -> int:
    return MODEL_ORDER.index(m) if m in MODEL_ORDER else len(MODEL_ORDER)


def _cell_stats(rows, task):
    """(rate, succ, n) for one cell/task via build_deck's exact metric."""
    return bd.task_success_rate(rows, task)


def _disjoint(succ_c, n_c, succ_a, n_a):
    """True if the two Wilson 95% CIs do not overlap (Δ is CI-significant)."""
    lo_c, hi_c = wilson_ci(succ_c, n_c)
    lo_a, hi_a = wilson_ci(succ_a, n_a)
    return hi_c < lo_a or hi_a < lo_c


# ---------------------------------------------------------------------------
# Figure — one colored Δ table per arm
# ---------------------------------------------------------------------------

def fig_delta_table(CANON, ANON, arm, min_n, canon_label, anon_label, out_png):
    """Colored Δ matrix for ONE arm.

    Rows = (model, think); cols = the 5 tasks + an ST-mean summary column.
    Cell = canonical − anon success (pp). A boxed, bold cell = the canonical
    and anon Wilson 95% CIs are DISJOINT — a real drift, not noise (the
    "noticeable drift" highlight). '—' = a side below `min_n` trials.
    """
    rows_keys = [(m, th) for m in MODEL_ORDER for th in ("off", "on")
                 if (m, th, arm) in CANON and (m, th, arm) in ANON]
    n_rows = len(rows_keys)
    cols = TASKS + ["ST"]
    grid = np.full((max(n_rows, 1), len(cols)), np.nan)
    sig = np.zeros((max(n_rows, 1), len(cols)), dtype=bool)
    for i, (m, th) in enumerate(rows_keys):
        k = (m, th, arm)
        deltas = []
        for j, task in enumerate(TASKS):
            _, sc, nc = _cell_stats(CANON[k], task)
            _, sa, na = _cell_stats(ANON[k], task)
            if nc >= min_n and na >= min_n:
                grid[i, j] = (sc / nc - sa / na) * 100.0
                sig[i, j] = _disjoint(sc, nc, sa, na)
                deltas.append(grid[i, j])
        if deltas:
            grid[i, len(TASKS)] = float(np.mean(deltas))

    fig, ax = plt.subplots(figsize=(9.8, max(2.4, 0.55 * n_rows + 1.7)))
    if n_rows == 0:
        ax.text(0.5, 0.5, "(no matched cells for this arm)", ha="center",
                va="center", transform=ax.transAxes, color="#888")
        ax.axis("off")
        fig.savefig(out_png, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return

    # Color scale from the per-task cells only, so one averaged ST cell can't
    # compress the task palette.
    task_vals = grid[:, :len(TASKS)]
    vmax = max(10.0, float(np.nanmax(np.abs(task_vals))) if np.isfinite(task_vals).any() else 10.0)
    im = ax.imshow(grid, cmap="RdBu_r", vmin=-vmax, vmax=vmax, aspect="auto")
    ax.set_xticks(range(len(cols)))
    ax.set_xticklabels([TASK_LABELS.get(c, c) for c in cols], fontsize=9)
    ax.set_yticks(range(n_rows))
    ax.set_yticklabels([f"{MODEL_DISP[m]} · think={th}" for m, th in rows_keys], fontsize=8)
    # Thin separators: between models (rows) and before the ST summary column.
    for i in range(1, n_rows):
        if rows_keys[i][0] != rows_keys[i - 1][0]:
            ax.axhline(i - 0.5, color="#999", linewidth=1.0)
    ax.axvline(len(TASKS) - 0.5, color="#999", linewidth=1.0)
    for i in range(n_rows):
        for j in range(len(cols)):
            v = grid[i, j]
            if np.isnan(v):
                ax.text(j, i, "—", ha="center", va="center", color="#bbb", fontsize=9)
                continue
            boxed = bool(sig[i, j])
            ax.text(j, i, f"{v:+.0f}", ha="center", va="center", fontsize=8,
                    fontweight="bold" if boxed else "normal",
                    color="white" if abs(v) > vmax * 0.55 else "black")
            if boxed:
                ax.add_patch(plt.Rectangle((j - 0.5, i - 0.5), 1, 1, fill=False,
                                           edgecolor="black", linewidth=2.0))
    cb = fig.colorbar(im, ax=ax, fraction=0.035, pad=0.02)
    cb.set_label(f"Δ success (pp):  {canon_label} − {anon_label}\n"
                 f"red = canonical advantage (contamination)   ·   boxed = CI-disjoint",
                 fontsize=8)
    clean = "   —   CLEAN CONTAMINATION PROBE" if arm == "nt-neut" else ""
    ax.set_title(f"Per-task Δ success · {ARM_DISP[arm]}{clean}   "
                 f"(ST = mean of the task Δ; — = a side below {min_n} trials)", fontsize=11)
    fig.tight_layout()
    fig.savefig(out_png, dpi=150, bbox_inches="tight")
    plt.close(fig)


def summary_rows(CANON, ANON, min_n):
    """ST-mean (unweighted over tasks ≥ min_n both sides) per matched cell."""
    out = []
    for arm in ARM_ORDER:
        for think in ("off", "on"):
            for m in MODEL_ORDER:
                k = (m, think, arm)
                if k not in CANON or k not in ANON:
                    continue
                rc, ra, ndisjoint, ntask = [], [], 0, 0
                nc_tot = na_tot = 0
                for task in TASKS:
                    _, sc, nc = _cell_stats(CANON[k], task)
                    _, sa, na = _cell_stats(ANON[k], task)
                    if nc >= min_n and na >= min_n:
                        rc.append(sc / nc * 100)
                        ra.append(sa / na * 100)
                        nc_tot += nc
                        na_tot += na
                        ntask += 1
                        if _disjoint(sc, nc, sa, na):
                            ndisjoint += 1
                if ntask == 0:
                    continue
                mc, ma = float(np.mean(rc)), float(np.mean(ra))
                out.append([ARM_DISP[arm], MODEL_DISP[m], think,
                            f"{mc:.0f}", f"{ma:.0f}", f"{mc - ma:+.0f}",
                            f"{ndisjoint}/{ntask}", f"{nc_tot}/{na_tot}"])
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--canon", required=True, help="results subdir for the canonical corpus")
    p.add_argument("--anon", required=True, help="results subdir for the anon corpus")
    p.add_argument("--out", required=True, help="output .pptx path")
    p.add_argument("--canon-label", default="canonical")
    p.add_argument("--anon-label", default="anon")
    p.add_argument("--min-n", type=int, default=50,
                   help="per-side, per-task min trials to plot a comparison")
    args = p.parse_args()

    repo = Path(__file__).resolve().parents[4]
    canon_root = repo / args.canon if not Path(args.canon).is_absolute() else Path(args.canon)
    anon_root = repo / args.anon if not Path(args.anon).is_absolute() else Path(args.anon)

    print(f"Loading canonical: {canon_root}")
    CANON = bd.load_all(canon_root)
    print(f"Loading anon:      {anon_root}")
    ANON = bd.load_all(anon_root)

    # ---- pairing diagnostics (advisor guard #1: catch silent mispairing) ----
    ck, ak = set(CANON), set(ANON)
    matched = sorted(ck & ak)
    canon_only = sorted(ck - ak)
    anon_only = sorted(ak - ck)
    print("\n=== (model, think, arm) key sets ===")
    print(f"MATCHED ({len(matched)}):")
    for k in matched:
        print(f"  {k}   n_canon={len(CANON[k])}  n_anon={len(ANON[k])}")
    print(f"CANON-ONLY ({len(canon_only)}):  " + ", ".join(str(k) for k in canon_only))
    print(f"ANON-ONLY  ({len(anon_only)}):  " + ", ".join(str(k) for k in anon_only))
    print()

    out_pptx = Path(args.out)
    out_pptx.parent.mkdir(parents=True, exist_ok=True)
    fig_dir = out_pptx.with_suffix("")
    fig_dir = fig_dir.parent / (fig_dir.name + "_figs")
    fig_dir.mkdir(parents=True, exist_ok=True)

    prs = bd._make_pptx()
    bd.add_title_slide(
        prs,
        "PDDL Copilot — Contamination Probe: canonical vs anonymised corpus",
        f"{args.canon_label}  vs  {args.anon_label}  ·  Δ = canonical − anon success (pp)  ·  "
        f"clean probe = no-tools neutral arm  ·  complete corpora: no-tools 4560/side both corpora; "
        f"with-tools mostly complete (Qwen3.5-4B / 9B-on anon cells slightly under-filled)",
    )

    bd.add_text_slide(prs, "How to read this deck", [
        f"• Two corpora, same matrix: {args.canon_label} uses the regular domains/; {args.anon_label} "
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
    ])

    for arm in ARM_ORDER:
        png = fig_dir / f"delta_table_{arm}.png"
        fig_delta_table(CANON, ANON, arm, args.min_n, args.canon_label, args.anon_label, png)
        clean = "  (clean contamination probe)" if arm == "nt-neut" else "  (secondary — tool-assisted)"
        extra = (" The only boxed cells (validate_plan × think=on) are a TOKENISATION artifact — anon prompts "
                 "tokenise ~5% longer → more think=on truncation; see the final slide.") if arm == "nt-neut" else ""
        bd.add_image_slide(
            prs, f"Δ success table · {ARM_DISP[arm]}{clean}", png,
            caption=f"Per-task Δ = {args.canon_label} − {args.anon_label} success (pp) for the "
                    f"{ARM_DISP[arm]} arm. Rows = model × think; right ST column = mean of the task Δ. "
                    f"Red = canonical advantage; blue = anon higher. Boxed+bold = CI-disjoint. "
                    f"'—' = a side below {args.min_n} trials.{extra}")

    rows = summary_rows(CANON, ANON, args.min_n)
    bd.add_table_slide(
        prs, "Contamination Δ summary — ST-mean per matched cell",
        ["arm", "model", "think", f"{args.canon_label} ST%", f"{args.anon_label} ST%",
         "ΔST (pp)", "tasks CI-disjoint", "n canon/anon"],
        rows,
        notes="ST% = unweighted mean over tasks with ≥min-n trials both sides. "
              "ΔST>0 = canonical advantage. 'tasks CI-disjoint' counts how many of the cell's tasks "
              "have non-overlapping canonical/anon Wilson CIs.")

    bd.add_text_slide(prs, "Observed pattern, coverage & next steps", [
        "HEADLINE — the CLEAN no-tools neutral probe is essentially NULL: ST-mean |Δ| ≤ 1.3pp (think=off) and "
        "≤ 2.6pp (on) across all 5 models, and think=off has ZERO CI-disjoint task cells. This now INCLUDES "
        "Qwen3.5-9B and Qwen3.5-4B, which were missing / partial in the earlier preliminary build.",
        "THE ONLY CLEAN-PROBE DRIFT IS A TOKENISATION ARTIFACT, not contamination. The sole CI-disjoint nt-neut "
        "cells are validate_plan × think=on (Qwen3.5-4B +6.3, 9B +4.0, Qwen3.6-35B +4.3pp canonical). But anon "
        "domain names tokenise ~5% LONGER (input-token median 1309 vs 1249), so anon trials hit the think=on "
        "decode-budget cliff MORE: truncation Δ (+6.2 / +3.8 / +4.3pp) tracks the success Δ (+6.3 / +4.0 / "
        "+4.3pp) almost 1:1, and success GIVEN completion is ~equal (Qwen3.6 94.9% anon vs 95.2% canon; ~95-97% "
        "for 4B/9B). The 'edge' is the extra truncation, not better domain knowledge — and Qwen3.6 is confounded "
        "too, so it is NOT a clean carrier. Net: no genuine contamination survives on the clean probe.",
        "WHERE THE NULL IS INFORMATIVE: it is meaningful only where no-tools isn't floored — Gemma4-off "
        "(~50%) and Qwen3.6-off (~49%) have ample headroom for a memorisation gap, and none appears. At the "
        "floor (small models with think=on, ~0%) a null is uninformative — no room for a gap either way.",
        "WITH-TOOLS (tl-neut / tl-ster) — a small canonical-leaning edge, concentrated in simulate and "
        "validate_plan, but NOT YET STABLE, so read these tables as PROVISIONAL and secondary. Two cells are "
        "still in flight (Qwen3.5-9B think-on anon; Qwen3.5-0.8B think-off canonical was mid-rerun on the "
        "cluster, so this sync pulled partial-over-complete data for it), and the validate_plan component "
        "overlaps the known FastMCP arg-error binning artifact (see project_validate_plan_fp_scoring_bug). The "
        "per-cell numbers have shifted across syncs and will move again — do not pin a with-tools magnitude or "
        "mechanism from this build. With tools the planner/validator solves regardless of domain names, so any "
        "edge here is tool-interaction, not model recall.",
        "CORRECTION vs the preliminary build: the earlier verdict_mismatch (+1.7pp) 'reasoning-degradation' "
        "mechanism is RETRACTED — it was an artifact of only Gemma4 + Qwen3.6 being complete, and the "
        "with-tools deficit is not in verdict_mismatch. The exact with-tools magnitude/mechanism is deferred "
        "until the in-flight cells finish.",
        "COVERAGE (sync 2026-06-01): the clean no-tools probe is complete (4560 trials/side, all 5 models, "
        "both corpora) — the conclusion rests here. With-tools: Qwen3.5-4B is now complete; STILL in flight = "
        "Qwen3.5-9B think-on anon (~7.2k/9.1k) and Qwen3.5-0.8B think-off canonical (mid-rerun, ~8.0k). Those "
        "with-tools rows are provisional; re-sync to finalise them.",
        "BOTTOM LINE: NO evidence of train-set contamination. The clean no-tools probe is null on every "
        "task/model under think=off, and the only think=on CI-disjoint cells (validate_plan) are fully "
        "explained by a differential-truncation artifact (anon prompts ~5% longer → more decode-cliff "
        "truncation), NOT recall. The with-tools deltas are small, secondary (the planner/validator solves "
        "regardless of names) and not yet stable — they do not support a contamination claim either.",
        "NEXT: a per-DOMAIN Δ (canonical-blocksworld vs anon-blocksworld) localises which specific domains, "
        "if any, a model memorised; it needs the anon↔canonical name mapping. Rebuild after any further sync: "
        "re-run filter_variants on both roots, then re-run this script.",
    ])

    prs.save(str(out_pptx))
    print(f"wrote {out_pptx}")


if __name__ == "__main__":
    main()
