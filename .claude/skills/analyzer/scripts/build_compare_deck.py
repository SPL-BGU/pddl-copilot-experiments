"""Build a contamination-probe comparison deck: canonical vs anon corpus.

Pairs two *filtered* results roots cell-by-cell over (model, think, arm, task),
computes per-cell success — runner-scored `r["success"]`, NOT a re-derived
ground truth (the anon corpus renames problem_name/plan_label, so `truth_for`
would be wrong on that side; the runner already scored each trial against its
own corpus) — with Wilson 95% CIs on each side, and renders the
canonical−anon delta as a Δ heatmap, per-task paired bars, and a summary table.

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

CANON_COLOR = "#2E86AB"   # blue
ANON_COLOR = "#E07B39"    # orange


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
# Figures
# ---------------------------------------------------------------------------

def fig_delta_heatmap(CANON, ANON, think, min_n, canon_label, anon_label, out_png):
    """Rows = matched (model, arm) for this think; cols = tasks; cell = Δpp."""
    rows_keys = []
    for arm in ARM_ORDER:
        for m in MODEL_ORDER:
            k = (m, think, arm)
            if k in CANON and k in ANON:
                rows_keys.append((m, arm))
    n_rows = len(rows_keys)
    grid = np.full((max(n_rows, 1), len(TASKS)), np.nan)
    sig = np.zeros((max(n_rows, 1), len(TASKS)), dtype=bool)
    for i, (m, arm) in enumerate(rows_keys):
        kc, ka = (m, think, arm), (m, think, arm)
        for j, task in enumerate(TASKS):
            _, sc, nc = _cell_stats(CANON[kc], task)
            _, sa, na = _cell_stats(ANON[ka], task)
            if nc >= min_n and na >= min_n:
                grid[i, j] = (sc / nc - sa / na) * 100.0
                sig[i, j] = _disjoint(sc, nc, sa, na)

    fig, ax = plt.subplots(figsize=(9.5, max(2.2, 0.52 * n_rows + 1.6)))
    if n_rows == 0:
        ax.text(0.5, 0.5, "(no matched cells for this think mode)",
                ha="center", va="center", transform=ax.transAxes, color="#888")
        ax.axis("off")
        fig.savefig(out_png, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return
    vmax = max(10.0, float(np.nanmax(np.abs(grid))) if np.isfinite(grid).any() else 10.0)
    im = ax.imshow(grid, cmap="RdBu_r", vmin=-vmax, vmax=vmax, aspect="auto")
    ax.set_xticks(range(len(TASKS)))
    ax.set_xticklabels([TASK_LABELS[t] for t in TASKS], fontsize=9)
    ax.set_yticks(range(n_rows))
    ax.set_yticklabels([f"{MODEL_DISP[m]} · {ARM_DISP[a]}" for m, a in rows_keys], fontsize=8)
    for i in range(n_rows):
        for j in range(len(TASKS)):
            v = grid[i, j]
            if np.isnan(v):
                ax.text(j, i, "—", ha="center", va="center", color="#bbb", fontsize=9)
            else:
                star = "*" if sig[i, j] else ""
                ax.text(j, i, f"{v:+.0f}{star}", ha="center", va="center",
                        fontsize=8, fontweight="bold" if sig[i, j] else "normal",
                        color="white" if abs(v) > vmax * 0.55 else "black")
    cb = fig.colorbar(im, ax=ax, fraction=0.035, pad=0.02)
    cb.set_label(f"Δ success (pp):  {canon_label} − {anon_label}\n"
                 f"red = canonical advantage (contamination)   ·   * = CI-disjoint",
                 fontsize=8)
    ax.set_title(f"Contamination Δ heatmap · think={think}  (— = a side below {min_n} trials)",
                 fontsize=11)
    fig.tight_layout()
    fig.savefig(out_png, dpi=150, bbox_inches="tight")
    plt.close(fig)


def fig_task_paired(CANON, ANON, task, min_n, canon_label, anon_label, out_png):
    """1×2 (think off/on); paired canonical vs anon bars per matched (arm, model)."""
    fig, axes = plt.subplots(1, 2, figsize=(15, 6.2), sharey=True)
    for col, think in enumerate(["off", "on"]):
        ax = axes[col]
        cells = []  # (arm, model, sc, nc, sa, na)
        for arm in ARM_ORDER:
            for m in MODEL_ORDER:
                k = (m, think, arm)
                if k in CANON and k in ANON:
                    _, sc, nc = _cell_stats(CANON[k], task)
                    _, sa, na = _cell_stats(ANON[k], task)
                    if nc >= min_n and na >= min_n:
                        cells.append((arm, m, sc, nc, sa, na))
        if not cells:
            ax.text(0.5, 0.5, f"(no matched cells ≥ {min_n}/side)", ha="center",
                    va="center", transform=ax.transAxes, color="#888")
            ax.set_title(f"think={think}", fontsize=11)
            ax.set_ylim(0, 105)
            continue
        x = np.arange(len(cells))
        w = 0.38
        for xi, (arm, m, sc, nc, sa, na) in zip(x, cells):
            pc, pa = sc / nc * 100, sa / na * 100
            lo_c, hi_c = wilson_ci(sc, nc)
            lo_a, hi_a = wilson_ci(sa, na)
            ax.bar(xi - w / 2, pc, w, color=CANON_COLOR,
                   yerr=[[max(0.0, (pc / 100 - lo_c) * 100)], [max(0.0, (hi_c - pc / 100) * 100)]],
                   capsize=2.5, error_kw=dict(elinewidth=0.8))
            ax.bar(xi + w / 2, pa, w, color=ANON_COLOR,
                   yerr=[[max(0.0, (pa / 100 - lo_a) * 100)], [max(0.0, (hi_a - pa / 100) * 100)]],
                   capsize=2.5, error_kw=dict(elinewidth=0.8))
            d = pc - pa
            star = "*" if _disjoint(sc, nc, sa, na) else ""
            ax.text(xi, max(pc, pa) + 3, f"Δ{d:+.0f}{star}", ha="center",
                    fontsize=7.5, fontweight="bold" if star else "normal")
        # arm-group separators
        prev_arm = None
        for xi, (arm, *_rest) in zip(x, cells):
            if prev_arm is not None and arm != prev_arm:
                ax.axvline(xi - 0.5, color="#ccc", linewidth=0.8, linestyle="--")
            prev_arm = arm
        # x-axis: only the (rotated) model name + n sits on the ticks; the arm is
        # lifted into a centered second-tier group label below each contiguous arm
        # run (the dashed separators above already mark the boundaries). This stops
        # the long "no-tools(neut)" strings from colliding with their neighbours.
        ax.set_xticks(x)
        ax.set_xticklabels(
            [f"{MODEL_DISP[m].replace('Qwen3.5-', 'Q3.5-').replace('Qwen3.6-', 'Q3.6-').replace('Gemma4-', 'G4-')}\n"
             f"n={nc}/{na}"
             for (arm, m, sc, nc, sa, na) in cells],
            rotation=30, ha="right", rotation_mode="anchor", fontsize=7)
        trans = ax.get_xaxis_transform()  # x = data coords, y = axes fraction
        run_start = 0
        for i in range(len(cells) + 1):
            if i == len(cells) or cells[i][0] != cells[run_start][0]:
                arm = cells[run_start][0]
                center = (x[run_start] + x[i - 1]) / 2.0
                ax.text(center, -0.205, ARM_DISP[arm], transform=trans,
                        ha="center", va="top", fontsize=9, fontweight="bold",
                        color="#444")
                run_start = i
        ax.set_title(f"think={think}", fontsize=11)
        ax.set_ylim(0, 105)
        ax.grid(axis="y", linestyle=":", alpha=0.4)
        if col == 0:
            ax.set_ylabel("success %  (Wilson 95% CI)", fontsize=10)
    fig.legend(handles=[plt.Rectangle((0, 0), 1, 1, color=CANON_COLOR),
                        plt.Rectangle((0, 0), 1, 1, color=ANON_COLOR)],
               labels=[canon_label, anon_label], loc="upper center", ncol=2,
               fontsize=10, frameon=False, bbox_to_anchor=(0.5, 1.02))
    fig.suptitle(f"{TASK_LABELS[task]} — success: {canon_label} vs {anon_label}  "
                 f"(Δ = canonical − anon; * = CI-disjoint)", fontsize=12, y=1.06)
    fig.tight_layout(rect=[0, 0.10, 1, 1])  # reserve bottom band for the arm-tier labels
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
        f"clean probe = no-tools neutral arm  ·  PRELIMINARY 2026-05-29 (partial in-flight cells, "
        f"per-side min-n {args.min_n}/task)",
    )

    bd.add_text_slide(prs, "How to read this deck", [
        f"• Two corpora, same matrix: {args.canon_label} uses the regular domains/; {args.anon_label} "
        f"uses domains-anon/ — the SAME domains lexically renamed (predicates/types/objects scrambled).",
        "• Δ = canonical success − anon success (percentage points). Δ>0 (red in the heatmap) = the model "
        "does better when domains carry their real names = consistent with MEMORISATION of the canonical "
        "domains during pre-training (contamination).",
        "• The CLEAN probe is the no-tools neutral arm (nt-neut): with no tools, success depends purely on "
        "the model's own knowledge of the domain, so memorisation shows up most starkly there.",
        "• A PRIORI one might expect with-tools arms (tl-neut / tl-ster) to show Δ≈0 — the planner/validator "
        "solves the task regardless of domain names. The data does NOT bear that out (see the observed-pattern "
        "note on the final slide), so read the with-tools rows as a finding, not a sanity check.",
        "• Metric = runner-scored success (each trial judged against its OWN corpus's ground truth). "
        "Wilson 95% CIs throughout; '*' marks a Δ whose canonical/anon CIs do not overlap.",
        f"• PRELIMINARY: jobs are ~1 day into 48h. Only cells with ≥{args.min_n} trials/side/task are plotted. "
        "Stable Δ (complete both sides): Qwen3.5-0.8B / Gemma4 / Qwen3.6-35B nt-neut. Provisional: Qwen3.5-4B "
        "anon nt-neut (~150 trials). UNCOMPARABLE: Qwen3.5-9B — its anon no-tools cell has not started "
        "(off missing, on=9 trials), so 9B is absent here; its blank is missing data, NOT a null result.",
    ])

    for think in ("off", "on"):
        png = fig_dir / f"delta_heatmap_{think}.png"
        fig_delta_heatmap(CANON, ANON, think, args.min_n, args.canon_label, args.anon_label, png)
        bd.add_image_slide(
            prs, f"Contamination Δ heatmap · think={think}", png,
            caption=f"Cell = {args.canon_label} − {args.anon_label} success (pp). Red = canonical "
                    f"advantage (contamination); blue = anon higher. '*' = CI-disjoint; '—' = a side "
                    f"below {args.min_n} trials. nt-neut rows are the clean probe; with-tools rows ~0 by design.")

    for task in TASKS:
        png = fig_dir / f"paired_{task}.png"
        fig_task_paired(CANON, ANON, task, args.min_n, args.canon_label, args.anon_label, png)
        bd.add_image_slide(
            prs, f"{TASK_LABELS[task]} — canonical vs anon", png,
            caption=f"Paired success per matched cell, grouped by arm (dashed = arm boundary). Blue = "
                    f"{args.canon_label}, orange = {args.anon_label}. n shown as n_canon/n_anon per cell. "
                    f"Δ above each pair; '*' = CI-disjoint.")

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
        "OBSERVED PATTERN (preliminary, complete cells only): the CLEAN no-tools probe (nt-neut) shows ~NULL "
        "contamination — |ΔST| ≤ 1.5pp with ZERO CI-disjoint tasks for the three complete models "
        "(Qwen3.5-0.8B, Gemma4, Qwen3.6-35B). The WITH-TOOLS arms instead carry a small but CONSISTENT "
        "canonical advantage (+2 to +5pp ST-mean; up to +11pp on a single task; several tasks CI-disjoint), "
        "strongest on solve / simulate / validate_plan.",
        "WHERE THE no-tools NULL IS INFORMATIVE: the null is meaningful only where no-tools isn't floored — "
        "Gemma4-off and Qwen3.6-off sit at ~49% (ample headroom for a gap, and none appears). At the floor "
        "(e.g. Qwen3.5-0.8B-on ≈0%) a null is uninformative — no room for a gap either way.",
        "MECHANISM OF THE with-tools EDGE (measured, not assumed): on the complete off with-tools cells "
        "(n=18,240/side), anon loses −3.0pp success vs canonical. That deficit is dominated by "
        "verdict_mismatch (+1.7pp: right tool called, valid output, WRONG conclusion) and tool_not_selected "
        "(+0.8pp); tool_error / parse failures barely move (+0.3pp). So the edge is a REASONING degradation "
        "over tool output when domain names are scrambled — NOT parsing friction. Modest (+1.7pp) and "
        "preliminary, but it points at semantic interpretation, not surface parsing.",
        "COVERAGE (this rebuild): no-tools nt-neut matched for Qwen3.5-0.8B, Gemma4, Qwen3.6-35B (complete "
        "both sides) and Qwen3.5-4B (anon partial ~150 trials, wide CIs). With-tools (tl-neut/tl-ster) matched "
        "for Gemma4 + Qwen3.6-35B only — the Qwen3.5 with-tools cells are still PENDING on the cluster.",
        "Qwen3.5-9B is UNCOMPARABLE: its anon no-tools cell had not started at sync (off missing, on=9 trials, "
        "below threshold). Re-sync once it fills in.",
        "NEXT (stronger view, once cells fill): per-DOMAIN Δ (canonical-blocksworld vs anon-blocksworld) — "
        "contamination is domain-specific, so a per-domain heatmap localises which domains the model memorised. "
        "Requires the anon↔canonical domain-name mapping; defer until both corpora complete.",
        "Rebuild after the next sync: re-run filter_variants for both roots, then re-run this script.",
    ])

    prs.save(str(out_pptx))
    print(f"wrote {out_pptx}")


if __name__ == "__main__":
    main()
