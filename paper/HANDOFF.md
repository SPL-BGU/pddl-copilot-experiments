# Handoff — AAAI-27 single-tool-use paper

**Branch:** `paper/aaai27-single-tool-draft` (pushed clean at `ee01e07`; **working tree clean**).
Full paper body committed & pushed 2026-06-14.
**Repo:** `pddl-copilot-experiments`. All paper work lives in `paper/`.
**Last session:** 2026-06-14.

## TL;DR for a fresh session
Read, in order: `paper/GOALS.md` (scope + deadlines + prior-work policy) →
`paper/RESULTS_PLAN.md` (the decided Results structure) → this file. The manuscript is
`paper/main.tex`; the bibliography is `paper/refs.bib` (fully verified).
**STATUS 2026-06-14: the full paper body (Abstract → Conclusion) is drafted, adversarially
verified, and committed/pushed (`ee01e07`); it builds clean and the technical content is within
the 7-page limit with all 3 figures. No prose work remains.** The next concrete task is the
**reproducibility checklist (item 7)**; then the camera-ready passes (vector PDF figures,
anonymization/metadata, exact HF model ids).

## What's DONE
- AAAI-27 author kit imported (`paper/authorkit27/`, anonymous template).
- `paper/main.tex` — **the full body is drafted and verified**: Abstract + Introduction +
  Background and Related Work + Methodology + Results + Limitations + Future Work + Conclusion
  (all adversarially fact-checked vs sources 2026-06-14). Only the reproducibility checklist
  and the camera-ready anonymization/vector-figure passes remain.
- `paper/figures/` — 5 PNGs copied from the deck; Results uses 3: `solve.png`+`simulate.png`
  (Fig 1), `mechanism_validate_plan.png` (Fig 2), `token_quadrant.png` (Fig 3).
  `visible_mode_succ.png` copied but the robustness story is folded to text.
- `paper/refs.bib` — 20 references, **all verified** against DBLP/ACL/PMLR/NeurIPS/arXiv;
  keys tidy (years match).
- `paper/GOALS.md`, `paper/RESULTS_PLAN.md` — scope + Results plan (decisions locked).
- Local build works (see Build below). `main.pdf` compiles to **8 pages total**; technical
  content **ends on page 7** (references fill p7 right column + p8) → **within the 7-page
  content limit, all 3 figures kept**. 0 undefined refs, 0 overfull boxes.

## Build
```bash
cd paper
TEXINPUTS="./authorkit27:" BSTINPUTS="./authorkit27:" \
  pdflatex main && bibtex main && pdflatex main && pdflatex main
```
Local builds need several fonts the BasicTeX-2026 system tree lacks; they were installed into
the **user** tree (no sudo) on 2026-06-14 via
`tlmgr --usermode install tex-gyre newtx courier psnfss` — `ts1-qtmr` (newtx TS1; the first
`itemize` bullet pulls it in) and `pcrr8t` (Courier T1; `\texttt`/listings). If a fresh machine
fails on `newtxtext.sty` / `ts1-qtmr` / `pcrr8t`, rerun that usermode install or build on
Overleaf. NOTE: the AAAI kit does **not** load `amsmath`, so avoid `\text{}` — use `\mathrm{}`.

## REMAINING WORK (priority order)
1. ~~**Methodology (goal 3a)**~~ — **DONE 2026-06-14.** `\section{Methodology}` written
   (6 subsections: tasks/oracle/fixtures; models+serving; three-arm design; metrics+Wilson+
   signed-significance; cross-mode+robust-floor; contamination). Adversarially verified vs
   `EXPERIMENTS_FLOW.md`/deck/notes + code. **Three corrections found & applied — carry into
   Results:** (a) the validator is **pddl-pyvalidator (unified-planning)**, NOT VAL
   (`howey2004val` stays a Background-only cite); (b) non-solve decode cap is **6{,}144**, not
   4096 (`runner.py` `DEFAULT_NUM_PREDICT`; `EXPERIMENTS_FLOW.md` was stale — fixed this
   session); (c) `validate_domain` is **5:1 positive:negative** (ISS-020), not balanced.
2. ~~**Results (goal 3b)**~~ — **DONE 2026-06-14.** Regime-led per `RESULTS_PLAN.md`: lead +
   scorecard (`table*`) + 6 subsections (sole-source / headroom / mixed / scaling / cost /
   robustness), 3 figures. All numbers are locked deck values, adversarially fact-checked vs
   the deck. **Note:** the deck's ``8,192-token cap'' for simulate is a shorthand slip — the
   real simulate/validate cap is **6,144** (solve 8,192); both Methodology and Results use the
   correct caps. The cost ``4--15×/trial'' and ``3--11× costlier'' deck ranges span ≥4B; the
   ≥9B-scoped Results text uses the tighter ≥9B values (~4--6×/trial, ~3--5× costlier).
   Fact-check also corrected a deck overclaim: RQ0.5 **simulate's gap DECLINES**
   +100->+93->+77pp with plan length (its tool arm itself degrades), NOT
   "constant ~87-99pp" -- only **solve** is constant (+87-89pp). **Fix the deck
   slides 29-30 prose too.** Full record in `development/paper_notes_discussions.md`.
3. **Figures** — PNGs are in `paper/figures/` and compile in the draft; for camera-ready,
   regenerate the 3 used figures as **vector PDF @300dpi** (sources in
   `checkpoints/rq-sweep5v2/plots-unified/`; generator `.claude/skills/analyzer/scripts/rq_deck.py`).
4. ~~**Introduction (goal 1)**~~ — **DONE 2026-06-14.** Motivation, the gap (3 prior-work lines),
   the design in brief, a regime-dependent findings preview, and a 4-item contributions list.
   Verified clean (double-blind / claims-match-Results / no overclaim / citations).
5. ~~**Limitations + Future Work + Conclusion**~~ — **DONE 2026-06-14.** Limitations (think=on
   budget confound, temp-0 single-sample, 5-model/2-family roster, strict grading, no archived
   traces, latency unrecoverable, validate\_domain 5:1); Future Work = ONE-paragraph out-of-scope
   mention of PlanBench + Huang \& Zhang formalizer baselines + multi-tool orchestration + a
   cap-raised rerun; Conclusion. Verified clean.
6. ~~**Abstract**~~ — **DONE 2026-06-14.** 164 words, no citations (AAAI rule), claims match body.
7. **Reproducibility checklist — NEXT.** `authorkit27/ReproducibilityChecklist.tex` (template
   read 2026-06-14, not yet filled). It is a list of `\question{...}{(yes/partial/no/NA)}` items
   in 4 groups; answer each by replacing the "Type your response here" line with ONE option,
   editing nothing else. Pre-loaded answers:
   - **General Paper Structure:** conceptual outline of methods = **yes** (Methodology + Table 1);
     opinions-vs-facts delineated = **yes**; pedagogical refs = **yes**.
   - **Theoretical Contributions:** **no** (empirical paper, no theorems — the sub-questions
     become NA).
   - **Dataset Usage:** **yes** — 20 PDDL domains (10 from the earlier version's released set,
     cited; 10 substituted from public IPC/benchmark suites, public). No NOVEL dataset → the
     "novel dataset" sub-items are **NA/partial**; existing datasets cited + public = **yes**.
   - **Computational Experiments:** **yes** — fill: hyperparameters tried + selection (temp 0,
     ctx 16384, decode caps solve 8192 / others 6144, ≤10 tool loops); infra = vLLM on a
     workstation-class GPU — **keep GENERIC, no institution/host/SLURM**; metrics = strict
     end-to-end success + tool\_selected, Wilson 95\% CIs, signed significance (motivated in
     Methodology) = **yes**; #runs per result = temp 0 ⇒ 1 deterministic sample/trial, per-cell
     N=4{,}560 = **yes**; variation/confidence = Wilson CIs + Newcombe MOVER = **yes**;
     significance test = signed-disjoint-CI rule (Methodology) = **yes/partial**; code
     public-on-publication = **yes** (intend to release). Include exact **HF model ids** (roster
     labels Qwen3.5/3.6, Gemma-MoE-26B are non-canonical).
   Inline it before `\end{document}` (single-.tex submission rule); then rebuild and confirm the
   page budget still holds (the checklist usually doesn't count toward the 7 — verify vs CFP).
8. ~~**Page-limit pass**~~ — **SATISFIED 2026-06-14.** Full body builds to **8 pages total**, but
   technical content **ends on page 7** (Conclusion in p7 left column; references fill p7 right
   column + p8, and refs don't count) → within the 7-page content limit **with all 3 figures
   kept double-column** — no trim needed. Re-verify the exact rule against the CFP before
   submission; if it tightens, the lightest lever is tightening Results/Background prose (the
   user's chosen lever; keep figures).
9. **Anonymization pass before submission** — third-person self-citation only (verified clean in
   every section); clear PDF metadata; no de-anonymizing links; reconcile non-canonical model
   labels with HF ids in the reproducibility checklist (not a blind violation, a repro gap).

## Hard constraints / policies (don't relearn the hard way)
- **Double-blind.** Use the anonymous template. Cite the earlier version
  (Benyamin et al. 2025, arXiv:2509.12987) in the **third person**; never "our prior work."
  That paper is the authors' OWN rejected earlier version — cite, don't copy (our framework
  differs). Omer leads this redo; he is not an author of the arXiv version.
- **Page limit:** 7 pages technical content + unlimited references; no paid overlength.
- **Scope:** single-tool-use only. think=off is the headline; think=on is budget-confounded
  (robust-floor + caveat only). RQ0.3 (validate_plan) is **MIXED** — keep its full mechanism
  armor. PlanBench / SOTA formalizer baselines = Future Work.
- **Deadlines:** abstracts **Jul 21 2026**, full papers **Jul 28 2026** (verify vs CFP).
- **Commits:** no Claude credit lines. Branch is already feature-branched; commit + push when
  asked.

## Git state
Working tree **clean** as of 2026-06-14; branch pushed to `origin`.
```
ee01e07 paper: draft Introduction, Limitations, Future Work, Conclusion, Abstract (AAAI-27)
0a31a3d paper: draft Methodology + Results sections (AAAI-27)
6f25668 paper: rename bib keys to match years (bfcl2024->2025, pallagani2023->2022)
```
Decision log for the two 2026-06-14 sessions (corrections, page-budget resolution, deck
discrepancies to fix) is in `development/paper_notes_discussions.md` (three 2026-06-14 entries).

## Suggested opening prompt for the fresh session
> Continue the AAAI-27 paper on branch `paper/aaai27-single-tool-draft`. Read
> `paper/HANDOFF.md`, `paper/GOALS.md`, and `paper/RESULTS_PLAN.md`. The full body is already
> drafted, verified, and pushed (`ee01e07`). Next: complete the **reproducibility checklist** —
> inline `authorkit27/ReproducibilityChecklist.tex` into `paper/main.tex` (before
> `\end{document}`) and fill every `\question{...}` answer (replace each "Type your response
> here") using the pre-loaded answers in HANDOFF item 7, sourced from `EXPERIMENTS_FLOW.md` /
> `run_experiment.py` / `pddl_eval/`. Rebuild, confirm the 7-page content limit still holds, and
> keep it double-blind (generic infra only — no institution/host details).
