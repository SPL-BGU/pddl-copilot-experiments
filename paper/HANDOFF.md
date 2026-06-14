# Handoff — AAAI-27 single-tool-use paper

**Branch:** `paper/aaai27-single-tool-draft` (pushed clean at `6f25668`; **uncommitted
working-tree changes from 2026-06-14: Methodology + Results + `paper/figures/` in `paper/`,
decode-cap fix in `EXPERIMENTS_FLOW.md` — not yet committed**).
**Repo:** `pddl-copilot-experiments`. All paper work lives in `paper/`.
**Last session:** 2026-06-14.

## TL;DR for a fresh session
Read, in order: `paper/GOALS.md` (scope + deadlines + prior-work policy) →
`paper/RESULTS_PLAN.md` (the decided Results structure) → this file. The manuscript skeleton
is `paper/main.tex`; the bibliography is `paper/refs.bib` (fully verified). Then draft the
next section. **Suggested next task: Methodology (goal 3a).**

## What's DONE
- AAAI-27 author kit imported (`paper/authorkit27/`, anonymous template).
- `paper/main.tex` — anonymized scaffold; **Background and Related Work + Methodology +
  Results are written** (all drafted + adversarially fact-checked vs sources 2026-06-14);
  Introduction / Limitations / Future Work / Conclusion / Abstract are still stubs.
- `paper/figures/` — 5 PNGs copied from the deck; Results uses 3: `solve.png`+`simulate.png`
  (Fig 1), `mechanism_validate_plan.png` (Fig 2), `token_quadrant.png` (Fig 3).
  `visible_mode_succ.png` copied but the robustness story is folded to text.
- `paper/refs.bib` — 20 references, **all verified** against DBLP/ACL/PMLR/NeurIPS/arXiv;
  keys tidy (years match).
- `paper/GOALS.md`, `paper/RESULTS_PLAN.md` — scope + Results plan (decisions locked).
- Local build works (see Build below). `main.pdf` compiles to **7 pages** (Intro/Limitations/
  Future Work/Conclusion still EMPTY) — references span ~1.2 of those pages.

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
4. **Introduction (goal 1 partial) — NEXT.** motivation, the gap, contributions list.
5. **Limitations** + **Future Work** — PlanBench/phase-3 + Huang & Zhang baseline are a
   one-paragraph Future Work mention only (out of scope here).
6. **Abstract** — write LAST.
7. **Reproducibility checklist** — AAAI requires it; `authorkit27/ReproducibilityChecklist.tex`.
8. **Page-limit pass** — fit **7 pages** (refs unlimited, appendix maybe-unread). Verify the
   7-page rule against the CFP. **STATUS 2026-06-14:** the doc is already **7 pages with
   Intro/Limitations/Future Work/Conclusion EMPTY** (refs ~1.2pp don't count; technical
   content ~5.5–6pp). Filling those (~1.5pp) WILL exceed 7 → trim here. Best candidates: make
   Fig 1 or Fig 3 single-column (both are `figure*` double-column now), move one to an
   appendix, or tighten Results prose. The robustness figure (`visible_mode_succ`) is already
   folded to text.
9. **Anonymization pass before submission** — third-person self-citation only; clear PDF
   metadata; no de-anonymizing links.

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
```
6f25668 paper: rename bib keys to match years (bfcl2024->2025, pallagani2023->2022)
126ea63 paper: verify all 20 bib entries against authoritative sources
959094b paper: AAAI-27 draft scaffold + Background/Related Work
```

## Suggested opening prompt for the fresh session
> Continue the AAAI-27 paper on branch `paper/aaai27-single-tool-draft`. Read
> `paper/HANDOFF.md`, `paper/GOALS.md`, and `paper/RESULTS_PLAN.md`, then draft the
> **Methodology** section in `paper/main.tex` from `EXPERIMENTS_FLOW.md` + the deck. Keep it
> double-blind (third-person self-citation) and within the 7-page budget.
