---
name: verify-claims
description: Ground every quantitative or mechanistic claim in scoring code and canonical data before writing or editing paper prose. Use before any paper edit that touches numbers, and to audit existing claims.
---

# Verify claims against code and data

Tex is not ground truth, and neither are prior conversation summaries. For each claim in scope:

1. **Check `development/NUMBERS.md` first.** It holds the frozen value of every headline figure and the stale readings each one replaces. Several figures exist at more than one value; quote the frozen one, and if your recomputation disagrees with it, stop and report rather than editing.
2. **Locate the source.** Identify the exact scoring/aggregation code path and the raw corpus that produce the number. Canonical corpora are `results/sweep5v2-live` (full N) and `*_sweep6`; `results/sweep5-cluster-20260530` is a stale partial mirror — never verify against it.
3. **Check the aggregation field.** Confirm the field being aggregated is the right one for the task (e.g. delivered vs tool-verified; not `llm_correct_binary` blanket-applied across tasks) and that censoring/at-cap handling matches the claim's framing.
4. **Check pending specs.** Grep `development/` for PENDING rewrite specs and read the relevant bottom lines in `development/paper_notes_discussions.md` — a decided-but-not-yet-applied spec overrides current tex.
5. **Recompute or trace.** Reproduce the number from data (script or one-off), or trace it to an existing verified artifact (memo, deck, locked table). A claim with no reproducible source gets flagged, not reworded.
6. **Report claim → evidence** as a compact table (claim, value in tex, verified value, source file:line / corpus), then apply edits.
7. **Compile.** After tex edits, verify a clean standalone LaTeX compile of `paper/`.

Paper edits go on a short branch off `main` and reach `main` by PR (since 2026-09-18 there is no `paper/aaai27` branch and no worktree; `paper/main.tex` on `main` is the paper). Run `development/sync_overleaf.sh pull` before editing tex. Prose style follows the no-AI-tells rule.
