

## 2026-11-22 (night) — RQ2 and RQ3 tables, the RQ1 object-count view and figures

- **Go-ahead (Omer):** do the RQ2 and RQ3 analysis and finish the RQ1 leftovers before any
  paper text.
- **RQ2** (`tools/reanalysis/rq23_metrics.py`, `NUMBERS.md` "RQ2 metrics"): every tool
  trial sorted into four classes by the tools it called (none, right only, right and
  another, others only), for the main sweep, the rerun and the Claude runs. Self-check: the
  harness rule on the stored calls equals the stored `tool_selected` on every row.
- **RQ3** (same script, "RQ3 metrics"): of the trials where the tool was right, the share
  whose final answer is wrong. The rerun rows are the frozen E4 cells restated (30 of 30
  reproduce); Claude from the overlay, simulate as a range.
- **RQ1:** the object-count view is added to solve, and three figures are drawn from the
  tables' JSON (`rq1_figures.py`, `tools/reanalysis/out/figs/`). The paper's old
  grey and blue for the arms were too close to tell apart reliably, so these figures use a
  darker grey and a brighter blue, plus line style and marker.
- **Bottom lines, to be checked by Omer before any prose** (all figures in `NUMBERS.md`):
  - *Tool choice, validation tasks and simulate:* with thinking off the right tool is
    called in nearly every trial by the three larger open models and by Claude. The
    exceptions are all on the plain prompt: validate_plan (Gemma calls it in about a fifth
    of the trials, the 35B in about four fifths) and simulate (the 9B in about four fifths;
    the 35B in about three quarters in the main sweep but nearly always in the rerun). One
    steering sentence closes most of these gaps.
  - *Tool choice, solve:* "exactly the right tool" is far lower on solve than anywhere else,
    because models add calls. Much of that is a plan check after the planner or a call to
    the other planner. Solve is graded more strictly here than by the harness (the planner
    must fit the domain), so these solve figures are not the frozen calling rates.
  - *Thinking on (main sweep only):* on the plain prompt Gemma's calling collapses on
    every task, the 9B's drops on validate_plan and solve, and the 35B's does not drop.
  - *Use of the output:* validation verdicts are almost never lost. On solve 5 to 13% of
    correct tool results are lost, on simulate 70 to 91% for the open models and at least a
    third for Claude. The largest single cause in the rerun is a final turn that was
    refused or clipped because the tool result had filled the context window, not wrong
    content.
