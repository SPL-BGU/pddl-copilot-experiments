# AAAI-27 Paper — Goals & Scope

**Branch:** `paper/aaai27-single-tool-draft`
**Opened:** 2026-06-14
**Status:** *Scaffold only.* Templates imported and scope fixed; **no paper prose written yet** (per author instruction, 2026-06-14).

This is "Paper 1 (tools/eval)" of the two-paper plan (see memory `project_paper_strategy`):
an evaluation of whether LLMs benefit from MCP-served symbolic PDDL planning/validation
tools on **single-tool-use** PDDL tasks, served via vLLM, **with vs. without** tools.

---

## Venue & deadlines

- **Venue:** AAAI-27, Main Technical Track.
- **Format:** double-blind. Use the AAAI-27 **anonymous** template
  (`authorkit27/AnonymousSubmission2027.tex`, which loads `\usepackage[submission]{aaai2027}`).
- **Deadlines** (from <https://aaai.org/conference/aaai/aaai-27/>, fetched 2026-06-14 —
  *re-verify against the official CFP before relying on these*):
  - OpenReview author registration opens: **Jun 17, 2026**
  - Submission site opens: **Jun 24, 2026**
  - Abstracts due: **Jul 21, 2026**
  - Full papers due: **Jul 28, 2026**

---

## Relationship to the earlier version (our own work, not external prior art)

- arXiv:2509.12987 — *"Toward PDDL Planning Copilot"* — is **our own group's earlier
  version of this work** (SPL-BGU). It was **not accepted** (arXiv-only). This experiment
  program, and this AAAI-27 paper (**led by Omer**), were initiated to build a
  substantially **more robust** version. So this is the **successor / strengthened redo of
  our own work**, not an extension of unrelated prior art.
- Because the earlier version is **our own unpublished work**, this is **self-citation, not
  third-party prior art** — no external-plagiarism risk. We still **re-derive** the
  background/lit-review and methodology to fit the more robust framework (strict end-to-end
  validation, `tool_selected` metric, Wilson 95% CIs, the three-arm no-tools / +tool(plain)
  / +tool(steered) design, a contamination control). We do **not** carry over the old
  prose; the new framework is different enough that the old framing no longer fits.
- The earlier paper's writing project is **not continued here.** This `paper/` directory is
  the single, self-contained home of the new paper. Cite the arXiv version where relevant
  as the earlier version of our own work; it is never "the paper."

---

## Goals of this draft (IN SCOPE)

1. **Abstract.**
2. **Complete background + literature review.** Covers: LLMs for planning / PDDL,
   LLM-as-formalizer, tool-use & MCP-native agent benchmarks, symbolic planners &
   validators as oracles. Anchors and external calibration already collected (see
   pointers below).
3. **Methodology + results — single-tool-use evaluation.** The harness, the task suite
   (`solve`, `validate_domain`, `validate_problem`, `validate_plan`, `simulate`), the
   model roster, the three-arm design, the metrics & CIs, the contamination control, the
   token-efficiency analysis, and the locked RQ0.1–0.6 findings.
4. **Future work — PlanBench.** Reserve **only a Future Work mention.** The PlanBench
   results & discussion are **out of scope** for the body of this draft.

---

## Explicitly OUT OF SCOPE for this draft

- PlanBench results & discussion (phase-3) — deferred to a later draft / future work.
- SOTA LLM-as-formalizer baselines, incl. Huang & Zhang (ACL 2025) — phase-3.
- The multi-task / chain phase (archived in the harness; not wired into `run_experiment.py`).
- Paper 2 (autonomous monitoring agent) — separate paper.

---

## Where the material already lives (pointers — content not yet written)

> These are sources to draw from when writing; nothing below is drafted prose.

- **Locked single-tool RQ findings & verdicts:** `development/paper_notes_discussions.md`
  (entries 2026-06-08 → 2026-06-11); RQ deck under `checkpoints/rq-sweep5v2/`.
- **Methodology / harness:** `EXPERIMENTS_FLOW.md`, `run_experiment.py`, `pddl_eval/`.
- **External benchmark calibration:** `development/baseline_comparison_tool_use_benchmarks.md`.
- **Contamination control:** `development/contamination_probe_plan.md` + the 2026-06-01
  verdict in `paper_notes_discussions.md`.
- **Token / cost efficiency:** the 2026-06-09 / 06-10 notes + memory `project_tool_efficiency_metrics`.
- **Domains & provenance:** `domains/README.md`.

---

## Results narration — DECIDED 2026-06-14

How to discuss the Results (goal 3b) was settled and is now **realized in the written Results
section** of `paper/main.tex` (regime-led structure, scorecard table + 3 figures,
methods-vs-results split). The standalone `RESULTS_PLAN.md` was retired 2026-06-18 once the
prose landed. Canonical data source =
`checkpoints/rq-sweep5v2/pddl_copilot_rq_sweep5v2_unified.{pptx,pdf}` + `plots-unified/`;
current review + grounded rewrite plan is in `paper/REVIEW_AND_REWRITES.md`.

## How to start writing (when ready — not done yet)

```bash
cd paper
cp authorkit27/AnonymousSubmission2027.tex main.tex   # working file
# create refs.bib for our bibliography; in main.tex use \bibliography{refs}
# keep aaai2027.{sty,bst} discoverable (symlink/copy next to main.tex, or set TEXINPUTS)
```

Build: `pdflatex main && bibtex main && pdflatex main && pdflatex main`.
Later we push to GitHub and mirror to Overleaf.
