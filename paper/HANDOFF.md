# Handoff — AAAI-27 single-tool-use paper

**Branch:** `paper/aaai27-single-tool-draft` (latest on `origin`; **working tree CLEAN** —
everything below is committed & pushed through `bf6f7cb`).
**Repo:** `pddl-copilot-experiments`. All paper work lives in `paper/`.
**Checkout (IMPORTANT — read first):** as of 2026-06-15 the main checkout
`/Users/omereliyahu/personal/pddl-copilot-experiments` is itself on
`paper/aaai27-single-tool-draft` (verify with `git worktree list` — there is now a single
worktree, no separate `-experiments-paper` dir). Do paper work right here. The earlier
HANDOFF described a dedicated `-experiments-paper` worktree; that no longer exists.
**Last session:** 2026-06-18 — review + rewrite pass (`paper/REVIEW_AND_REWRITES.md`): a
grounded critique with paste-ready rewrites; the Sonnet frontier no-tools experiment LOCKED;
GPT-OSS-120B set aside; the BF16-35B precision control re-homed to the cluster (pod with-tools
run abandoned). **This surfaced a MUST-FIX — `validate_domain` is mis-framed (review §1) — so the
prose is no longer "final"; substantive revisions are pending.** Earlier sessions (2026-06-14/15)
drafted + adversarially verified the full body and inlined the reproducibility checklist.

## TL;DR for a fresh session
Read, in order: `paper/GOALS.md` (scope + deadlines + prior-work policy) →
`paper/REVIEW_AND_REWRITES.md` (current review + grounded rewrite plan + the locked Sonnet
frontier experiment) → this file. The manuscript is `paper/main.tex`; the bibliography is
`paper/refs.bib` (fully verified). (The Results-narration plan, formerly `RESULTS_PLAN.md`, is
retired — its structure is now realized in the written Results section.)
**STATUS (2026-06-18):** Full body (Abstract → Conclusion) is drafted with 3 figures + the
inlined reproducibility checklist, and builds clean (0 undefined, 0 overfull). Latest build
(`main.pdf`, 2026-06-17) is **12 pp total**; only the **technical content** counts toward the
7-page limit (references + the inlined reproducibility checklist are the non-counting tail). It
ended on p7 as of the 2026-06-15 build, but `main.tex` was edited 2026-06-18 — **re-verify
pagination on the next rebuild.** The body is drafted but **NOT final**:
`REVIEW_AND_REWRITES.md` proposes substantive revisions (the `validate_domain` MUST-FIX, the
invocation-propensity reframe, a new Discussion). Code-availability decided (release at
publication, not submission). See "GAPS TO GOAL" for what's done vs. left.

## GAPS TO GOAL — status after the 2026-06-15 session-2 pass
Goal = a submission-ready, double-blind AAAI-27 PDF. Body, checklist, figures, and the
contamination control are done. What remains is publication-time work + one upload-time check.

DONE this pass (committed/pushed):
- **Vector figures** — the 3 Results figures are now true vector PDF (`paper/figures/*.pdf`).
- **Contamination control strengthened** — DECISION: keep the result in the MAIN text (per the
  PlanBench / Mystery-BW A* precedent; this is the OPPOSITE of the initial appendix/repo-link
  lean, confirmed by a research agent + an independent ranking agent). Added **Table 3** (per
  model: canonical vs anonymized no-tools success, $\Delta$, $N$=4{,}560), tightened the claim to
  the verified figure (mean $|\Delta|$=1.1pp, max 3.7, 0 CI-disjoint cells), and put the think=on
  validate\_plan tokenization-artifact numbers in-prose. Numbers verified 3 ways (sweep5v2 vs
  sweep6).
- **Deck RQ0.5 prose fixed** — `rq_deck.py` + regenerated unified deck now match the paper
  (simulate gap declines +100→+93→+77; only solve constant). The plot itself was already correct;
  only the slide prose was stale.
- **Code-availability decision: release at PUBLICATION, not at submission.** No artifact at review
  → checklist code-appendix items set to **no**, public-on-publication **yes** (the honest AAAI
  pairing). Eventual release = a curated, SCRUBBED package (eval harness + BOTH corpora, no
  cluster scripts, no `.git`) — see publication-time below.

REMAINING:
- **Review + rewrite plan — see `paper/REVIEW_AND_REWRITES.md` (2026-06-18).** Peer-review-style
  pass with paste-ready rewrites, all grounded in recomputed sweep5v2/sweep6 numbers. Headline
  items: (a) the reframe to lead with invocation-propensity / silence-not-error as the *general*
  tool-use lesson; (b) a MUST-FIX — `validate_domain` is mis-framed (all ≥9B models are at/below
  the 83% majority baseline unaided; balanced accuracy 53–74% — report balanced accuracy, recast
  as "tool rescues," not "refines a partial baseline"); (c) the `success = P(call)×P(correct|call)`
  decomposition; (d) add a Discussion section (currently none). Prioritized action list in §9.
- **[LOCKED] Frontier experiment — Sonnet 4.6 no-tools contamination + sole-source (`REVIEW…md` §7A).**
  Sonnet no-tools, think=off, full N, BOTH corpora (canonical sweep5v2 + anon sweep6), Batch API
  (−50%): `simulate` + `validate_plan` (+ optional `validate_problem`) ≈ $108–118, funded by ~$145
  Anthropic credit. Pilot ~$5–10 first; reuse exact fixtures/graders. Extends sole-source AND the
  contamination control to a strong *proprietary* model. GPT-OSS-120B was considered and **set
  aside** (§7B: not a capability step-up over the 35B, flaky with-tools tool-call path, redundant
  no-tools contamination). Promotes the frontier check from a generic Future-Work line to a
  concrete, costed, in-flight item.
- **PlanBench results + discussion — BIG forthcoming addition (planned, sweep in progress).**
  The PlanBench cross-domain track is still running (`development/PLANBENCH_HANDOFF_v3.md`; memory
  `project_planbench_v2_v3`). When it completes, ADD its results + discussion to the paper,
  promoting PlanBench from the one-paragraph Future Work mention to its own Results/Discussion
  content, carrying the same end-to-end grading, signed-significance, and contamination controls.
  **This supersedes GOALS.md's current "PlanBench out of scope" stance** — update GOALS.md when it
  lands. There is a TODO marker in `main.tex` just above `\section{Future Work}`. Absorbing
  PlanBench will exceed 7 pages; the plan is to TRIM Background/Discussion prose at that point —
  **cut location is deferred (user + advisors decide).**
- **Double-blind PDF-metadata — VERIFIED CLEAN 2026-06-15** (`exiftool main.pdf`: only generic
  `Creator: TeX` / `Producer: pdfTeX` / PTEX banner; no author/title/path/username). Just re-run
  `exiftool` on the FINAL pre-upload build (a rebuild regenerates the same generic fields), and
  keep the `\begin{links}` block commented.
- **Page focus (user + advisors).** 10 pages total, technical content ends p7 (within limit). Not
  trimming per user instruction; user/advisors will choose focus (esp. once PlanBench lands).
- **Publication-time:** build the curated scrubbed code+data release (both corpora); optionally
  typeset a per-task contamination appendix table + the canonical↔renamed symbol map (data
  verified, not yet typeset).
- **CFP re-verify (low effort):** confirm page rule + that the checklist doesn't count, and the
  deadlines, against the official AAAI-27 CFP before submission.

## What's DONE
- AAAI-27 author kit imported (`paper/authorkit27/`, anonymous template).
- `paper/main.tex` — **the full body is drafted and verified**: Abstract + Introduction +
  Background and Related Work + Methodology + Results + Limitations + Future Work + Conclusion
  (all adversarially fact-checked vs sources 2026-06-14) **+ the inlined, fully-answered
  reproducibility checklist (2026-06-15) + HF model-id footnote.** Only the camera-ready
  anonymization/vector-figure passes remain.
- **Wilson CI wording cleaned up paper-wide (2026-06-15):** "Wilson" is named only at the
  §Metrics definition and the sole-source figure's error-bar legend; the abstract/intro/
  positioning/results-narrative/scorecard-caption use plain "confidence interval" / "95%
  intervals" (the abstract folds it into "signed, interval-based significance rule"). Newcombe
  MOVER is likewise named once, in §Metrics.
- `paper/figures/` — 5 PNGs copied from the deck; Results uses 3: `solve.png`+`simulate.png`
  (Fig 1), `mechanism_validate_plan.png` (Fig 2), `token_quadrant.png` (Fig 3).
  `visible_mode_succ.png` copied but the robustness story is folded to text.
- `paper/refs.bib` — 20 references, **all verified** against DBLP/ACL/PMLR/NeurIPS/arXiv;
  keys tidy (years match).
- `paper/GOALS.md` — scope + decisions locked. (`RESULTS_PLAN.md` retired 2026-06-18; its
  Results-narration plan is now realized in the written Results section.)
- Local build works (see Build below). With the checklist inlined, `main.pdf` compiles to
  **9 pages total**; technical content **still ends on page 7** (references fill p7 right
  column → p8, then the reproducibility checklist fills p8→p9 — neither refs nor checklist count
  toward the limit) → **within the 7-page content limit, all 3 figures kept**. 0 undefined refs,
  0 overfull boxes.

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
2. ~~**Results (goal 3b)**~~ — **DONE 2026-06-14.** Regime-led: lead +
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
7. ~~**Reproducibility checklist**~~ — **DONE 2026-06-15.** Inlined verbatim into `main.tex`
   (after `\bibliography{refs}`, before `\end{document}`); only the "Type your response here"
   lines were replaced. Final answers as filled (deviations from the pre-load below are the
   honest/no-overclaim reads — flag if the user wants different): General 1.1/1.2/1.3 = yes;
   Theoretical 2.1 = no, 2.2–2.8 = NA; Dataset 3.1 = yes, 3.2 = yes, 3.3/3.4 = NA (no novel
   dataset — corpus is from the earlier release + public suites), 3.5/3.6 = yes, 3.7 = NA;
   Computational 4.1 = yes, 4.2 = **partial** (settings fixed by design, not swept), 4.3/4.4 =
   **partial** (full repo exists + release-ready but NOT attached as an appendix at submission;
   4.5 public-on-publication = yes), 4.6 = partial, 4.7 = NA (temp 0, no randomness), 4.8 =
   **partial** (infra kept generic for anonymity), 4.9 = yes, 4.10 = yes, 4.11 = yes, 4.12 =
   **partial** (signed disjoint-CI rule, not a named test), 4.13 = yes. HF ids go in the body
   footnote (checklist answers are single tokens, can't hold ids). **Open call for the user:**
   4.3/4.4 are `partial` assuming we do NOT submit anonymized supplementary code; flip to a code
   appendix at submission if you want those = yes. Original pre-loaded answers, for reference:
   The checklist was a list of `\question{...}{(yes/partial/no/NA)}` items
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
   every section). ~~reconcile non-canonical model labels with HF ids~~ **DONE 2026-06-15** (HF
   ids added as a §Models-and-Serving footnote; third-party ids, not author-identifying). Still
   owed at upload: **clear PDF metadata** (author/title/producer) and confirm **no de-anonymizing
   links** (the `\begin{links}` block stays commented).

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
Working tree **clean** as of 2026-06-15; branch pushed to `origin`.
```
bf6f7cb paper: de-name Wilson CI outside Methodology; fold interval into signed-significance rule
7a6d69f paper: fill + inline reproducibility checklist; add HF model ids to Methodology (AAAI-27)
6a60ce9 paper: document dedicated worktree in HANDOFF (avoid branch-switch confusion)
ee01e07 paper: draft Introduction, Limitations, Future Work, Conclusion, Abstract (AAAI-27)
0a31a3d paper: draft Methodology + Results sections (AAAI-27)
```
Decision log is in `development/paper_notes_discussions.md` (three 2026-06-14 entries + a
2026-06-15 entry covering the checklist answers, HF-id footnote, and Wilson de-naming).

## Suggested opening prompt for the fresh session
> Continue the AAAI-27 paper on branch `paper/aaai27-single-tool-draft`. Read
> `paper/HANDOFF.md` ("GAPS TO GOAL"), `paper/GOALS.md`, and `paper/REVIEW_AND_REWRITES.md`. The full
> body, the inlined reproducibility checklist, and the HF-id footnote are already drafted,
> verified, and pushed (`bf6f7cb`); the tree is clean. Only camera-ready mechanics remain. Pick
> from GAPS TO GOAL: (A) regenerate the 3 figures as vector PDF @300dpi from
> `checkpoints/rq-sweep5v2/plots-unified/`; (B) the anonymization/PDF-metadata pass; (D)
> re-verify the page rule + deadlines against the official CFP. Decision C (attach anonymized
> supplementary code → flip checklist 4.3/4.4 to `yes`?) is the user's call. Keep it double-blind
> (generic infra only).
