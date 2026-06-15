# paper/ — AAAI-27 manuscript (single-tool-use evaluation)

Self-contained home of the new paper. See **`GOALS.md`** for scope, deadlines, and the
prior-work policy. The directory holds the official AAAI-27 templates, the planning docs,
and a compilable **scaffold** (`main.tex` + `refs.bib`) — sections are empty (TODO pointers
only); **no paper prose is written yet.**

## Layout

```
paper/
  GOALS.md            # scope, deadlines, prior-work policy, source pointers
  README.md           # this file
  main.tex            # working manuscript — anonymized scaffold, empty sections (start here)
  refs.bib            # bibliography (seeded with the anonymized self-citation)
  authorkit27/        # official AAAI-27 author kit (LaTeX), imported verbatim
    aaai2027.sty                  # style file — submission template loads [submission]{aaai2027}
    aaai2027.bst                  # bibliography style
    aaai2027.bib                  # example bib (reference only; we'll keep our own refs.bib)
    AnonymousSubmission2027.tex   # << start the submission from this (double-blind)
    AnonymousSubmission2027.pdf   # rendered template == the AAAI formatting instructions
    CameraReady2027.tex           # for the final (de-anonymized) version, later
    ReproducibilityChecklist.tex  # AAAI reproducibility checklist (+ .pdf)
    Figures/                      # example figures the templates compile against
```

The author kit was downloaded from <https://aaai.org/authorkit27/>
(→ `https://aaai.org/wp-content/uploads/2026/05/AuthorKit27.zip`) on 2026-06-14.
The kit's Word/`.docx` variants and the rendered CameraReady PDF were dropped (we submit in
LaTeX); pull them from the zip again if needed.

## Build

```bash
cd paper
TEXINPUTS="./authorkit27:" BSTINPUTS="./authorkit27:" \
  pdflatex main && bibtex main && pdflatex main && pdflatex main
```

The `TEXINPUTS`/`BSTINPUTS` prefixes make `aaai2027.{sty,bst}` discoverable (alternatively
copy/symlink them next to `main.tex`).

> **Local build note:** `aaai2027.sty` needs the `newtx` font package. A TeX Live *basic*
> install lacks it (`newtxtext.sty not found`) — install with `tlmgr install newtx`, or just
> build on **Overleaf**, where it's present. The scaffold itself compiles cleanly; this is
> only a missing-font-package issue on minimal local installs.

## Workflow

Write locally on `paper/aaai27-single-tool-draft`; push to GitHub and mirror to Overleaf
later. Per AAAI rules, the submitted PDF must use the **anonymous** template — keep
author/affiliation/acknowledgement and any self-identifying repo links out until camera-ready.
