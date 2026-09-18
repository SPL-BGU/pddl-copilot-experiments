# paper/ — the journal manuscript

This directory holds the paper: a full manuscript (25 pages), not a scaffold.

- **Target venue:** JAIR, with TMLR as the fallback. AAAI-27 was dropped on 2026-08-30.
- **Typesetting today:** still the AAAI-27 style (`aaai2027.sty`, `[submission]` mode), and
  still **anonymous**. The reformat to the journal style, and adding the author block and
  repository links, is one pre-submission step tracked in `development/STATUS.md` (N3).
  Until then keep author names, affiliations, acknowledgements and self-identifying links
  out of the tex.
- **What is left to do** is in `development/STATUS.md`. **Which value of a figure to quote**
  is in `development/NUMBERS.md`. Check both before editing a claim.

## Layout

```
paper/
  README.md        # this file
  main.tex         # THE manuscript. Edit this file. Never replace it with a template.
  refs.bib         # bibliography
  aaai2027.sty     # style file, lives next to main.tex. Do not hand-edit.
  aaai2027.bst     # bibliography style. Do not hand-edit.
  figures/         # the figure PDFs the tex includes, plus make_paper_figures.py
  authorkit27/     # the original AAAI-27 author kit, kept for reference only
```

**Do not start from `authorkit27/AnonymousSubmission2027.tex` and do not copy any template
over `main.tex`.** Older June notes say to; they describe a time before the paper was
written, and following them would overwrite the manuscript. Those notes now live in
`development/archive/paper-june/`.

## What syncs to Overleaf

Only `main.tex`, `refs.bib`, `aaai2027.sty`, `aaai2027.bst` and `figures/*.pdf`. Nothing
else in this directory reaches Overleaf.

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
