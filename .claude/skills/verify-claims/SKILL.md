---
name: verify-claims
description: Ground every quantitative or mechanistic claim in scoring code and canonical data. Use to check numbers before they go into the paper or an outline, and to audit claims already in the text.
---

# Verify claims against code and data

Tex is not ground truth, and neither are prior conversation summaries. For each claim in scope:

1. **Check `development/NUMBERS.md` first.** It holds the frozen value of every headline figure and the stale readings each one replaces. Several figures exist at more than one value; quote the frozen one, and if your recomputation disagrees with it, stop and report rather than editing.
2. **Locate the source.** Identify the exact scoring/aggregation code path and the raw corpus that produce the number. The paper leads with the October rerun (`results/delivered-rerun`, frozen readout `development/reference/delivered_rerun_readout.md`) and, for tools against no tools on solve and simulate, the matched run (its own folder and registration, `development/reference/matched_run_prereg.md`). The corrected-prompt control (`results/control-promptfix`), the pilots, the Claude runs and the May main sweep are supplement material; each has its own source in `NUMBERS.md`. For main-sweep figures the corpora are `results/sweep5v2-live` (full N) and `*_sweep6`; any other sweep folder (old sync mirrors, moved out of the repo on 2026-10-10, see `development/MOVES.md`) gives wrong numbers — never verify against one. Corpora are never pooled, and a figure from one never stands in for a cell of another.
3. **Check the aggregation field.** Confirm the field being aggregated is the right one for the task (e.g. delivered vs tool-verified; not `llm_correct_binary` blanket-applied across tasks) and that censoring/at-cap handling matches the claim's framing.
4. **Check pending specs.** Grep `development/` for PENDING rewrite specs and read the relevant bottom lines in `development/paper_notes_discussions.md` — a decided-but-not-yet-applied spec overrides current tex.
5. **Recompute or trace.** Reproduce the number from data (script or one-off), or trace it to an existing verified artifact (memo, deck, locked table). A claim with no reproducible source gets flagged, not reworded.
6. **Report claim → evidence** as a compact table (claim, value in tex or outline, verified value, source file:line / corpus). Report mismatches; do not reword the text to fit.
7. **Compile.** If a tex file was changed (a pasted table row, a corrected number), verify a clean standalone LaTeX compile of `paper/`.

Omer writes the paper's prose. The session outlines (`development/paper_outline.md`), analyses and checks numbers; it changes tex only when asked, and then only what was asked (table rows are pasted from the generators in `tools/reanalysis/`, never edited by hand). Any tex change goes on a short branch off `main` and reaches `main` by PR, which Omer merges; `paper/main.tex` on `main` is the paper. Run `development/sync_overleaf.sh pull` before editing tex.
