

## 2026-11-22 (late) — Correction: the JSON constraint never bound in the rerun's unaided arm

- **What was wrong:** today's RQ1 block in `NUMBERS.md`, `roadmap.md` §3 and the session's
  summaries to Omer said the rerun's unaided answers were "sampled under a JSON format
  constraint" while the tool answers were not. That repeats the frozen readout's false E2
  caveat, which `STATUS.md` forbids copying.
- **What is true** (`reference/weakness_consolidated.md`, Q3 note; `paper/main.tex`
  Limitations): the constraint was intended for the unaided arm and never took effect, in
  the main sweep or in the rerun. The unaided arm asks for its format in the prompt only,
  so an unaided failure can be a failure of format as well as of content, and what a
  working constraint would have produced is unmeasured.
- **Fixed in:** `tools/reanalysis/rq1_metrics.py` (the generated note), `NUMBERS.md` "RQ1
  metrics", `roadmap.md` §3. No number changes. **Still wrong, not edited:** Omer's
  uncommitted `draft_advisor_correa_comparison.md` (§4.1 and §4.3 say the same thing).
