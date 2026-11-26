# paper/ — the manuscript

This directory holds the paper.

- **Target venue:** ICAPS 2027, main track. Abstract 2026-12-07, paper 2026-12-14. The
  limit is 8 pages of main content plus references, with a supplementary PDF. A longer
  version continues as the thesis text. JAIR, TMLR and AAAI-27 are no longer targets.
- **Typesetting:** the AAAI-27 author kit (`aaai2027.sty`, `[submission]` mode), which is
  the format ICAPS 2027 asks for, and still **anonymous**. Keep author names,
  affiliations, acknowledgements and self-identifying links out of the tex.
- **Who writes:** Omer writes the prose. The session outlines the paper
  (`development/paper_outline.md`), analyses, and checks numbers. It does not rewrite
  his text.
- **Structure:** the paper asks three questions: do the tools help (RQ1), does the model
  pick the right tool (RQ2), does it use what the tool returns (RQ3). The Results answer
  them in that order.
- **`supplement_source.tex`:** raw material for the supplement. It holds the text that
  left `main.tex` on 2026-11-25, word for word: the Supporting Analyses section, the
  Methods and appendix parts that served it, the history of the unaided baseline and its
  second reading, the control's record, and thinking-on in RQ2. It is not compiled into
  `main.tex` and does not compile by itself. Sentences in `main.tex` that still point at
  this material carry a `% TODO(Omer)` comment.
- **Tables and figures are generated.** Table rows are pasted from generators and never
  edited by hand. In `tools/reanalysis/`: `rq1_tex.py`, `rq23_tex.py`,
  `rq1_control_metrics.py`, `control_prompt_fix_tex.py`, `rq3_context_pilot.py`,
  `rq3_simulate_regrade.py`, `rq1_layout_regrade.py`, `json_constraint_pilot.py`, and
  `rq1_figures.py` for figures. `paper/figures/make_paper_figures.py` draws the funnel
  figure and the figures of the supplement material.
- **What is left to do** is in `development/STATUS.md`. **Which value of a figure to quote**
  is in `development/NUMBERS.md`. Check both before a number goes into the text.

## Layout

```
paper/
  README.md               # this file
  main.tex                # THE manuscript. Edit this file. Never replace it with a template.
  supplement_source.tex   # raw material for the supplement; not compiled
  refs.bib                # bibliography
  aaai2027.sty            # style file, lives next to main.tex. Do not hand-edit.
  aaai2027.bst            # bibliography style. Do not hand-edit.
  figures/                # the figure PDFs, plus make_paper_figures.py
  authorkit27/            # the original AAAI-27 author kit, kept for reference only
```

**Do not start from `authorkit27/AnonymousSubmission2027.tex` and do not copy any template
over `main.tex`.** That would overwrite the manuscript.

## What syncs to Overleaf

Only `main.tex`, `refs.bib`, `aaai2027.sty`, `aaai2027.bst` and `figures/*.pdf`. Nothing
else in this directory reaches Overleaf; `supplement_source.tex` does not. The sync
copies files and never deletes one, so a figure removed from `figures/` stays on Overleaf
until someone removes it there by hand.

## Build

`paper/` compiles standalone. No `TEXINPUTS` or `BSTINPUTS` setting is needed, because the
style files sit next to `main.tex`.

```bash
cd paper
latexmk -pdf main
# or: pdflatex main && bibtex main && pdflatex main && pdflatex main
```

**Fonts on a minimal TeX install.** BasicTeX lacks several fonts the style needs. Install
them into the user tree (no sudo):

```bash
tlmgr --usermode install tex-gyre newtx courier psnfss
```

This covers the usual three failures: `newtxtext.sty not found`, `ts1-qtmr` (the newtx TS1
font, pulled in by the first `itemize` bullet) and `pcrr8t` (Courier T1, used by `\texttt`
and listings). If a fresh machine still fails, rerun that command or build on Overleaf.

The AAAI style does **not** load `amsmath`, so avoid `\text{}` in math; use `\mathrm{}`.

## Workflow

1. `git checkout main && git pull`, then a short branch `paper/<topic>`.
2. `development/sync_overleaf.sh pull` first, and commit if anything came down. A push
   without a pull can overwrite a coauthor's edits made on the Overleaf website.
3. Edit, compile, commit, push the branch, open a PR. Omer merges.
4. Merging a PR that touches the synced files pushes the paper to Overleaf by itself.
   Check that the Action run is green.

Read `development/paper-git-overleaf-instructions.md` before any sync work. Never
force-push to Overleaf.
