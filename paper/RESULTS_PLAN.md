# Results — narration plan (DECIDED 2026-06-14)

**Status:** structure decided; **no Results prose drafted yet.** Canonical source =
`checkpoints/rq-sweep5v2/pddl_copilot_rq_sweep5v2_unified.{pptx,pdf}` (59 slides) +
`checkpoints/rq-sweep5v2/plots-unified/`. Findings provenance:
`development/paper_notes_discussions.md` (2026-06-08 → 06-11). Headline = **think=off**.

## Decisions (this session)

1. **Organization:** regime-led hybrid — sole-source → headroom → mixed → scaling → cost →
   robustness; RQ tags kept as anchors.
2. **Reasoning mode (think=on):** compact Results subsection + appendix; quote the robust
   floor + the budget confound, not the raw think=on gaps.
3. **Token efficiency:** co-headline subsection with **one** main figure (cost-of-pass
   quadrant) + the decomposition in text; completion-only lens → appendix.
4. **Figures to main:** 4 figures + the scorecard table; all numeric tables → appendix.
5. **Headline/caveat:** think=off locked verdicts; RQ0.3 = MIXED, stated honestly with full
   mechanism armor; 0.8B = one caveat paragraph (≥9B headline, ≥4B in appendix tables).

## Methods vs. Results split (deck → paper)

- **Methodology** (move out of Results): tasks × 3 arms (deck s4); success metric +
  Wilson CIs + arms-never-pooled (s5); signed-significance rule (s6); cross-mode
  aggregation + realizable-benefit spine = steered arm (s36, s40).
- **Results:** all RQ evidence, token, cross-mode, contamination.
- **Limitations:** s43 (s44 "what the paper can claim" is our own guidance, not content).
- **Appendix:** s45–59 (full per-task and token tables, completion-only lens, cross-mode detail).

## Results structure (regime-led)

| § | Claim | Main asset | Deck slides | Plot source (`plots-unified/`) |
|---|---|---|---|---|
| Lead + **Table 1** | Scorecard: 6 RQs + verdicts + headline numbers; 2/5 tasks don't happen without the tool | scorecard table | 2, 3 | — |
| **R.1 Sole-source** (RQ0.2 solve, RQ0.4 simulate) | simulate 0% / solve floored ~8–11% → tool 63–97% | **Fig 1** | 11, 20 | `solve.png` + `simulate.png` |
| **R.2 Headroom** (RQ0.1 validate_domain/problem) | tool helps even with a partial baseline (+21–30pp) | text + Table 1 (charts saturate) | 7–9 | `validate_domain.png`, `validate_problem.png` (opt.) |
| **R.3 Mixed** (RQ0.3 validate_plan) | availability can hurt (silence/under-call); steering repairs; 9B>35B = propensity, not capability | **Fig 2** | 14–18, 21 | `mechanism_validate_plan.png` |
| **R.4 Scaling** (RQ0.5 grows, RQ0.6 flat) | advantage grows with plan length; flat in object count | text (+ opt. small fig) | 29–31 | `phase2_rq05.png`, `phase2_rq06.png` |
| **R.5 Cost** (co-headline) | ~4–15× tokens/trial; cost-of-pass 0.3× where floored, 3–11× where strong | **Fig 3** + decomposition in text | 23–28 | `token_quadrant.png` |
| **R.6 Robustness** (compact) | pattern survives reasoning mode (robust floor; budget-confounded); contamination null | **Fig 4** (or fold to text) | 32–42 | `visible_mode_succ.png` / `mode_scatter.png` |

## Main figures — source assets

- **Fig 1** `solve.png` + `simulate.png` — success by arm (grey/blue/orange), ≥9B band.
- **Fig 2** `mechanism_validate_plan.png` — tool_selected → success, plain vs. steered.
- **Fig 3** `token_quadrant.png` — tokens/trial (log) vs. success, no-tools→steered arrows.
- **Fig 4** `visible_mode_succ.png` — modes side-by-side per model (think=off vs. on).
- **Table 1** — scorecard (6 RQs × verdicts × headline numbers).

> Assets are **PNG** from `rq_deck.py`. For camera-ready, regenerate as **vector PDF @300dpi**
> (source: `.claude/skills/analyzer/scripts/rq_deck.py` plot functions).

## Appendix (from deck backup)

`cop_dumbbell.png`, `token_profile.png`, `realizable_dumbbell.png`,
`visible_mode_capfail.png`, `think_on_cliff.png`; full success tables (s53–55), token
tables (s46–49), completion-only lens (s50–51), difficulty bins (s52, s56), cross-mode
detail (s57–59).

## Open items

- Verify AAAI-27 **page limit** (CFP) — may trim Fig 4 or the RQ0.5 figure.
- Regenerate all main figures as **PDF** before submission.
- **Anonymize** the self-citation (see `refs.bib` note).
