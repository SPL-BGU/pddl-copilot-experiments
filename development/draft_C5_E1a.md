# Draft: C5 hit list and E1a vocabulary (2026-11-09, handoff item 7)

> **E1 is OPEN (Omer, 2026-11-09).** Nothing in this draft removes RQ1 to RQ6 or the
> scorecard (`tab:scorecard`), from the tex or from any draft. Part 2 carries both
> framings side by side: the existing RQ1 to RQ6 and the suggestion in
> `draft_E1_research_questions.md`. Where a scorecard cell carries a retired figure, this
> draft says which E step re-fills the cell. It does not say the row goes.

*Doc-only. The tex is not edited. Tex line numbers are for `paper/main.tex` at `main`
`130193e`; re-run the searches in §1.4 after any tex change. Numbers inside quoted tex
are the tex's own words, shown so the hit can be found; they are not quoted here as
figures. Where a value is pinned, the `NUMBERS.md` block is named.*

Plan step C5 (`weakness_action_plan.md` §4 C) asks: does anything from the retired
open-model delivered ranges survive in the tex? Plan step E1 asks for the vocabulary:
what each kept term means and which terms go. This draft answers the first in Part 1
and drafts the second (E1a) in Part 2.

## Sources and short names

| short name | what it points to |
|---|---|
| **S1-Rules** | `NUMBERS.md`, block "Study 1 — main sweep figures", "Rules for this block", first bullet: Study 1's delivered surface (the overlay's `e2e_strict` bounds) "is retired for the open models and is not carried here" |
| **Plan-Leaves** | `weakness_action_plan.md` §4 E, "Leaves the paper": "-67" as a headline; "law" and "identical"; the open-model delivered ranges; the robust floor and the realizable benefit; the private vocabulary that existed to handle the ranges |
| **Plan-Outline** | `weakness_action_plan.md` §4 E, "Outline" (sections 1 to 8 and the appendix) |
| **Plan-E7** | `weakness_action_plan.md` §4 E, "E7, the consistency-read leftovers" (held sentences E3a, E3b, E8b) |
| **Job2** | `NUMBERS.md`, block "Job 2 — the delivered surface". Holds the retired open-model values (for example the validate_plan and validate_domain bounds, the delivered cost-of-pass ranges). Read with S1-Rules: these rows are the retired surface for the open models |
| **Per-cell** | `NUMBERS.md`, block "Single-tool suite — per-cell figures": the overlay CSV `results/derived/e2e_overlay/pooled_e2e_table.csv` is the one source of every per-cell bound |
| **Iss024d** | `NUMBERS.md`, block "Added 2026-10-03 — figures changed by the consistency read" (the full-storage rerun rows) |
| **Readout** | `NUMBERS.md`, block "Delivered rerun — readout (FROZEN 2026-10-09)" (Study 2, R1 to R5, E1, E2) |
| **Secondary** | `NUMBERS.md`, block "Delivered rerun — descriptive secondary analyses" (Gemma no-call answers, E4 hand read, cost by price ratio) |
| **S1-row "x"** | a named row of the `NUMBERS.md` Study 1 block, with its "do NOT quote" column |
| **WC-Cn / WC-Dn** | `reference/weakness_consolidated.md`, item Cn or Dn |

**Why the ranges are retired, in one line.** The rerun showed our harness pulled the
open-model delivered ranges down (plan §1; `paper_notes_discussions.md` 2026-10-10:
"Only the open-model delivered ranges were badly off"), and S1-Rules retires that
surface. Study 2 (the delivered rerun and its extension) measures the delivered answer
exactly on a fixed setup.

**Owners.** An owner is the E step that replaces the passage, with the outline section
it lands in:

| owner | E step | outline section |
|---|---|---|
| **E2** | Methods and Study 1 results | §3 Methods, §4 Study 1 |
| **E3** | Study 2 results | §5 Study 2 |
| **E4** | Frontier tier and PlanBench | §6 Frontier, §7 PlanBench |
| **E5** | Discussion, Limitations, Conclusion | §8 |
| **E6** | Title and abstract | title, abstract |
| **E7** | Consistency-read leftovers (with E3) | wherever E3 places them |
| **E1** | the outline and the vocabulary (open) | the RQ list and the scorecard's form |

**PROPOSED** marks an owner this draft suggests where the plan names none today. The
handoff (item 7) names four such places: the Introduction, `tab:vdom`, `tab:decomp` and
the figures. This search found three more: `tab:howtoread`, the steering-control
appendix, and the `\cbnd` macro in the preamble. Each is in the Decisions list at the end.

---

# Part 1. C5 hit list

## 1.1 What counts as a hit

1. **Retired figures:** every open-model delivered bound `\cbnd{a}{b}` from the main
   sweep (S1-Rules), and every sentence or caption built on them (verdicts like
   "undecided", "straddles", "clears at the claim-adverse end"; delivered cost-of-pass
   ranges).
2. **Retired words:** "straddling", "law", "identical" (as a claim), "robust floor",
   "realizable benefit" (Plan-Leaves), and the private vocabulary that existed to handle
   the ranges (WC-C19, weakness Q9): delivered surface, primary surface, two layers,
   mechanism layer, censoring bound, claim-adverse end, determinate / indeterminate rows,
   sole-source, budget-dependent, headroom (as a regime label), delegation-terminal,
   apparatus, tool path.
3. **Superseded, not on the retired list:** the full-storage rerun (`iss024d`) bounds.
   They are a separate setup, not Study 1. But that rerun carries the same harness faults
   as the main sweep (`paper_notes_discussions.md` 2026-10-10, "Per-run fault check"), and
   the Readout block's E1 row says not to quote its "at most 21%" as a figure of the
   rerun. Study 2 measures the same things exactly. They are listed so E3 can decide them
   (Decision 6).
4. **Not a hit:** frontier bounds (frontier simulate, Sonnet unaided simulate). They are
   pinned as "quote this" in `NUMBERS.md` (Job2 frontier rows; "Frontier e2e" block; the
   Abstract block row 3). They stay until E4 decides (Decision 7). PlanBench and the
   steering-control figures are frozen and stay.

A few hits are **NUMBERS.md "do NOT quote" items** that are not ranges. They were found by
the same reading, and they sit in the same passages, so they are listed and marked
**(N-flag)**.

## 1.2 The hit list

### Abstract — owner E6

| id | tex line | quoted text (short) | why it goes | owner |
|---|---|---|---|---|
| A1 | 90–91 | "calls the validator on $21\%$ of trials when merely available" | The figures stay (Abstract block row 2). "Merely available" is the retired name of the plain arm: the arm is "tool available plus a policy sentence" (Plan-Outline §3), and the policy sentence lowers calling (Readout, R5 row) | E6 |
| A2 | 93–95 | "by a gap growing with answer length, ... at both tiers" | The figures stay (Abstract block row 3, frontier). The reading "the gap tracks answer length" is the one Plan-E7 (E3b, E8b) rewrites, and "at both tiers" is unclear (WC-C20) | E6, after E3/E4 settle the reading |

### Introduction — no owner today; PROPOSED E6

| id | tex line | quoted text (short) | why it goes | owner |
|---|---|---|---|---|
| I1 | 155–158 | "collapses one $\geq$9B model's validator invocation to $21\%$ ... (its tool path drops $67$\,pp)" | "-67" leaves the headline; it stays only as a labelled tool-verified figure (Plan-Leaves; S1-row "Gemma validate_plan availability, tool-verified"). "Tool path", "invocation" are retired words (Part 2) | PROPOSED E6 |
| I2 | 158–161 | "a \emph{delivery gap} that grows with answer length and persists at the frontier tier" | The "grows with answer length" reading is rewritten from Study 2 (Plan-E7; WC-C5) | PROPOSED E6 |
| I3 | 161–164 | "Where the unaided baseline has headroom ... the pattern survives reasoning mode" | "Headroom" is a regime label (Part 2). "Survives reasoning mode" was checked on tool-verified only (WC-C18); wave 2 (plan D3) measures it again | PROPOSED E6 |
| I4 | 167–172 | "graded at two labeled layers (the delivered answer as the primary surface; ... the mechanism layer), with ... explicit censoring bounds" | Private vocabulary and the bounds (S1-Rules; Plan-Leaves) | PROPOSED E6 |
| I5 | 173–181 | "the \emph{invocation rate} ... mere \emph{availability} collapses the tool path" | "Invocation rate" becomes "calling rate"; "mere availability" goes (A1). The outline allows at most three contributions; the tex has five (Plan-Outline §1) | PROPOSED E6 |
| I6 | 182–185 | "identical at two frontier tiers, so the gap tracks answer length rather than model strength" | "Identical" leaves (Plan-Leaves; WC-C5). The open models lose far more on plans than the frontier, so "rather than model strength" does not hold as written (WC-C5) | PROPOSED E6 |
| I7 | 188–190 | "the verdict pattern reproduces under reasoning mode through budget-insensitive statistics" | This is the robust-floor argument (Plan-Leaves); wave 2 measures reasoning mode directly (plan D3) | PROPOSED E6 |

### §3 Methodology — owner E2

| id | tex line | quoted text (short) | why it goes | owner |
|---|---|---|---|---|
| M1 | 340–344 | "The Metrics subsection defines the two layers and fixes the delivered answer as the primary surface" | Vocabulary ("two layers", "primary surface"). Plan-Outline §3: the delivered answer is the main outcome, calling the second, tool-verified appears once | E2 |
| M2 | 510–513 | "The \emph{realizable benefit} of the tool, used as the cross-mode spine below" | Plan-Leaves | E2 |
| M3 | 516–528 | "\paragraph{One primary surface, two layers.} ... labeled as the mechanism layer" | Vocabulary (WC-C19); the outline's outcome list replaces the paragraph | E2 |
| M4 | 528–532 | "\emph{delegation-terminal}" | Private term (WC-C19). Plain words: "an empty final answer after a correct tool result" | E2 |
| M5 | 534–549 | "\paragraph{One surface, three value shapes.} ... censoring bounds, written \cbnd{a}{b} ... claim-adverse end ... \emph{undecided}" | The whole paragraph exists to handle the ranges (weakness Q9; S1-Rules). Only the frontier simulate bounds would still need a notation (Decision 7) | E2 |
| M6 | 570 | "log-odds $+7.5$, posterior SD $0.10$" | **(N-flag)** S1-row "mixed model": do NOT quote "+7.5, SD 0.10" (the SD is about three times too small) | E2 |
| M7 | 588–591 | "collapses one $\geq$9B model's validator invocation to $21\%$ ... a mechanism-layer drop of $-67$\,pp" | "-67" as an example in Methods: keep only as a labelled tool-verified figure (Plan-Leaves); "mechanism-layer" goes | E2 |
| M8 | 596–602 | "already stricter than a Bonferroni bound for a confirmatory family as large as ${\sim}30$" | **(N-flag)** S1-row "paired verdicts": do NOT quote the "stricter than Bonferroni" argument (WC-C9). The verdict rule moves to the paired, clustered, Holm tests (T5) | E2 |
| M9 | 605–625 | "\subsection{Cross-Mode Aggregation and the Robust Floor}" ... "\emph{robust} ... \emph{sole-source} ... \emph{budget-dependent}" | Robust floor and realizable benefit leave (Plan-Leaves); the regime labels go with them. E2 removes the subsection from Methods; the reasoning-mode result itself moves to Study 2 (plan D3) | E2 (removal); E3 (the reasoning-mode result) |

### Start of Results, the RQ list and the scorecard

| id | tex line | quoted text (short) | why it goes | owner |
|---|---|---|---|---|
| R1 | 648–660 | "All headline rates are \emph{delivered} ... where a cell is a censoring bound \cbnd{a}{b}, the gap is asserted only if it survives the claim-adverse end" | Bounds and their rule (S1-Rules). Study 1 headlines are unaided, calling and tool-verified (NUMBERS.md Study 1 block); delivered headlines are Study 2 | E2 (§4 opening); E3 (§5 opening) |
| R2 | 668–707 (`tab:howtoread`) | row "Open-weight sweeps (tool arms) & $500$-char snapshot & bounds \cbnd{a}{b} & ... straddling cells stay \emph{undecided}"; row "Independent full-storage rerun"; caption "one primary surface (delivered), three value shapes" | Every open-model row and the caption rest on the retired surface (S1-Rules) and on the private vocabulary. Plan-Outline's appendix asks for "one table of setups" in "How we measured", which this table could become | **PROPOSED E2** (appendix "How we measured"; no E step names that appendix today) |
| R3 | 712–725 (`fig:funnel` caption) | "obtains a correct tool result (the mechanism layer), and delivers a correct answer (the primary surface)"; "this corpus's \emph{solve} and \emph{simulate} tool cells are censoring bounds too wide to draw"; "hatched segments are censoring bounds" | The open-model panel's delivered bars come from the retired overlay (`paper/figures/make_paper_figures.py` reads `e2e_strict`; Per-cell block). Vocabulary | **PROPOSED E3** (open-model panel, redrawn from Study 2); **E4** (frontier and PlanBench panels) |
| — | 728–744 (RQ list) | RQ1 to RQ6 | **Not a hit. Stays.** E1 is open (`draft_E1_research_questions.md`). See Part 2 for what RQ3's wording "mere availability" would need if kept | E1 |
| R4 | 746–762 | "Two regime vocabularies appear below ... \emph{sole-source} ... \emph{headroom} ... \emph{mixed} ... \emph{robust}, \emph{budget-dependent}"; "at the delivered surface the canonical corpus is censored into bounds that cannot decide the harm" | Regime vocabulary goes (Plan-Leaves, private vocabulary); the bound sentence is retired (S1-Rules) | E2 (task framing in §4); E3 (the delivered half) |
| S1 | 773–778 (scorecard row RQ1) | "delivered lower bounds $92$--$100\%$"; "\cbnd{92.2}{95.3} vs $65.7$"; "the 35B cell straddles and stays undecided" | Retired ranges and "straddles" (S1-Rules; Plan-Leaves; Job2 holds the 9B validate_domain bound). **The row stays (E1 open).** Its evidence cell is re-filled | E1 (form); E2 (unaided, tool-verified); E3 (delivered) |
| S2 | 779–784 (row RQ2) | "Open-roster tool cells are bounds: the 9B survives the worst case (\cbnd{26.0}{58.7} vs $10.7$) ... Gemma and the 35B are undecided" | Retired ranges (S1-Rules; Per-cell). **Row stays** | E1; E2; E3; E4 (the frontier half of the cell stays as is) |
| S3 | 785–790 (row RQ3) | "\textsc{undecided} (delivered)"; "all three canonical cells are censored into straddling bounds"; "\cbnd{30.0}{63.1}" | Retired ranges; "straddling" is also wrong for two of three cells (WC-D3); the full-storage rerun value is superseded (§1.1 item 3). Study 2 gives the registered label (Readout, R1 row). **Row stays** | E1; E2 (calling, tool-verified); E3 (delivered) |
| S4 | 791–796 (row RQ4) | "With tools, delivered is undecided on the canonical corpus" | Retired (S1-Rules). The frontier bounds in the same cell are not hits (§1.1 item 4). **Row stays** | E1; E2 (unaided, with the qualifier of the Job2 row "open-roster unaided simulate"); E3; E4 |
| S5 | 797–800 (rows RQ5, RQ6) | "\textsc{yes} (mechanism layer)", "\textsc{no} (mechanism layer)" | No range. Vocabulary only ("mechanism layer"). The rows set a tool-verified side against a strict unaided side (WC-C7); E2 says so. **Rows stay** | E1; E2 |
| S6 | 803–810 (scorecard caption) | "Scorecard: six research questions on the delivered surface"; "Cells written \cbnd{a}{b} are censoring bounds and support a verdict only at their claim-adverse end" | Caption error: two of six rows are tool-verified (WC-C20); bound vocabulary (S1-Rules). **The table stays** | E1 (form); E2 |
| F1 | 818–835 (`fig:solesource` caption) | "hatched segments are censoring bounds"; "the open-weight tool arms clear their baselines only at the claim-adverse end of the 9B's bound"; "at most \cbnd{6}{21} is delivered" | The open-model solve panel is the retired surface; the simulate panel is the full-storage rerun (superseded, §1.1 item 3). Frontier panels are not hits | **PROPOSED E3** (open-model panels from Study 2); **E4** (frontier panels) |

### §4 / §5 material inside today's Results

| id | tex line | quoted text (short) | why it goes | owner |
|---|---|---|---|---|
| T1 | 839 | "\subsection{Two Tasks the Model Cannot Do Unaided}" | WC-C6: E3 retitles the "cannot do unaided" section (plan §5, row C6) | E3 |
| T2 | 840 | "\emph{Solve} and \emph{simulate} are sole-source on the baseline side" | Regime vocabulary | E2 |
| T3 | 847–853 | "the 9B's \cbnd{26.0}{58.7} clears its $10.7\%$ baseline ...; Gemma (\cbnd{14.3}{35.3}) and the 35B (\cbnd{12.7}{53.7}) straddle and stay undecided (RQ2 \textsc{yes}, carried by the frontier tier and the baseline floor)" | Retired ranges (S1-Rules; Per-cell), "straddle", and WC-C20 (open-model evidence carried by the frontier) | E3 |
| T4 | 853–854 | "The mechanism layer points to invocation as the reason the open-roster bounds sit so far under their tool-verified rates" | WC-C20: a gap below tool-verified cannot be a calling problem. The rerun traced the solve gap to storage and the refused final request (Readout, R4 row) | E3 |
| T5 | 854–858 | "(Qwen3.6-35B invokes the planner on only $68\%$ of trials)"; "every $\geq$9B model is $\geq$93\% accurate when it does call the planner" | **(N-flag)** S1-row "calling, rerun vs main sweep": do NOT quote "the 35B calls the planner on only 68%" without the caveat that the rerun moved this cell. S1-row "correct given a call": 35B solve plain is below 93 | E2 |
| T6 | 863–869 | "not one open-roster tool-arm trial yields a determinate delivered success, and the bounds top out at \cbnd{0}{20}--\cbnd{0}{39} for the $\geq$9B models" | Retired (S1-Rules). Also: the low end of this range matches only thinking-on overlay rows (Qwen3.5-4B, Qwen3.6-35B), not a ≥9B thinking-off row (§1.5) | E3 |
| T7 | 870–871 | "The unaided zero, meanwhile, is a property of the deployed budget and format requirements, not an absent capability." | Held sentence E3a (Plan-E7). E3 rewrites it from the new numbers; plan §5 row D8: "budget and format contract" | E7 (with E3) |
| T8 | 889–893 | "a delivered-surface version of that contrast cannot be computed from this corpus (the tool arm delivers no determinate trajectory)" | Study 2 computes delivered simulate exactly (Readout, E1 simulate row) | E3 |
| F2 | 899–913 (`fig:failtax` caption) | "How answers fail on the delivered surface"; "\emph{censored} (... a bound rather than a failure)"; "on the tool arms the dominant non-success mass is censoring, which is why those cells are bounds" | The tool-arm bars are the retired surface. Study 2 has the delivery-gap categories with hand reads (Secondary, "E4 hand read" row; S2-E table) | **PROPOSED E3** (tool arms from Study 2 categories); E2 (the unaided anatomy) |
| D1 | 918 | "The two grading layers let us measure" | Vocabulary | E4 |
| D2 | 922–923 | "The pattern is sharp and identical at both capability tiers." | Held sentence E8b (Plan-E7); "identical" leaves (Plan-Leaves) | E7 (with E3; lands in E4's §6) |
| D3 | 936–942 | "The gap therefore tracks the length of what must be restated ... On this evidence the gap is a property of answer length interacting with the output budget, not of model strength." | Held sentence E3b (Plan-E7); WC-C5 | E7 (with E3; lands in E4's §6) |
| D4 | 961–972 | "the tool arms' delivered rates are bounds, so the gap is bounded rather than pointed; the full-storage rerun ... makes it exact"; "\cbnd{8.3}{10.7} ... \cbnd{12.7}{13.7}"; "the gap can run \emph{backwards} ... \cbnd{30.0}{63.1}" | Open-model bounds retired (S1-Rules); the full-storage rerun values superseded (Iss024d; Readout, E1 row "do NOT quote"). Study 2 gives the open-model delivery gap and the Gemma no-call answers (Readout E1; Secondary, no-call row) | E3 |
| D5 | 989–994 (`tab:deliverygap` caption) | "mechanism layer (tool-verified)"; "\emph{think}=off equivalent" | Vocabulary; "think=off equivalent" is never defined (WC-C19). Values are frontier and not hits | E4 |
| V1 | 998 | "\subsection{Two Validation Tasks: Headroom and Rescue}" | Regime label in a heading | E2 (title of the Study 1 part); E3 |
| V2 | 1001–1008 | "the 9B rises to \cbnd{92.2}{95.3} ...; Gemma's \cbnd{84.3}{99.8} ...; the 35B's \cbnd{74.7}{97.8} straddles its $75.7\%$ baseline and stays undecided" | Retired ranges and "straddles" (S1-Rules; Per-cell) | E3 |
| V3 | 1015–1024 | "The delivered lower bounds alone establish it: \cbnd{99.7}{100.0} ..."; "Balanced accuracy on the delivered surface ... \cbnd{100.0}{100.0} ... \cbnd{82.7}{99.2}"; "favorable for all three at the claim-adverse end" | Retired (S1-Rules; the values are in Job2, rows "9B validate_domain delivered" and "validate_domain balanced accuracy, delivered"). The tool-verified balanced accuracy stays (S1-row "validate_domain balanced accuracy"; T4) | E3 (delivered); E2 (unaided and tool-verified) |
| V4 | 1025–1032 | "verdict holds from 4B up (\cbnd{84.2}{100.0} ...)"; "The 0.8B model moves sharply and decidedly \emph{against} ... at the censoring bounds' favorable end (... \cbnd{43.9}{45.8}; ... \cbnd{4.0}{5.8})" | Retired (S1-Rules). The 0.8B and 4B are rerun on the fixed setup (plan D2, the size ladder) | E3 |
| V5 | 1033–1034 | "Steering does not help either validation task at the mechanism layer" | Vocabulary | E2 |
| F3 | 1044–1049 (`fig:mechanism` caption) | "mechanism-layer (tool-verified) success"; "Both panels are exact in every corpus" | Vocabulary only. The values are Study 1 calling and tool-verified (S1-row "Gemma validate_plan calling"; T2) | **PROPOSED E2** |
| B1 | 1053 | "\subsection{When Availability Backfires at the Tool Path, and Steering Repairs It}" | "Tool path"; Study 2 finds no delivered harm (Readout, R1 row) | E3 (heading); E2 (the Study 1 calling result) |
| B2 | 1068–1073 | "Across every $\geq$9B tool cell except 9B \emph{simulate} ($\approx$81\%), $P(\text{correct}\mid\text{call})$ stays $\geq$92\%" | **(N-flag)** S1-row "correct given a call": the exception list misses 9B validate_problem steered and Gemma simulate | E2 |
| B3 | 1075–1081 | "All three $\geq$9B tool cells are censored into straddling bounds (Gemma \cbnd{6.6}{99.6} ...; the 35B \cbnd{55.0}{90.3} ...; the 9B \cbnd{80.8}{87.2} ...), so the availability gap on this task is \emph{undecided} at the primary surface, in both directions" | Retired ranges (S1-Rules; Job2 row "gemma validate_plan, canonical delivered"); "straddling" and "in both directions" are wrong for two of three cells (WC-D3). Study 2 R1 decides the Gemma cell (Readout) | E3 |
| B4 | 1081–1086 | "in that corpus Gemma's delivered rate is \cbnd{30.0}{63.1} while its mechanism layer is $0.9\%$" | Superseded (Job2 row "gemma validate_plan, full-storage rerun": separate setup, within-corpus only). Study 2 reads the no-call answers in full (Secondary, no-call row) | E3 |
| B5 | 1104–1109 | "the 9B ``beats'' the 35B (\emph{solve} $99\%$ vs.\ $63\%$ ...)"; "accuracy-given-a-call is $\geq$93\% for both" | **(N-flag)** S1-row "calling, rerun vs main sweep": do NOT quote the 9B-vs-35B "size inversion" on solve without the caveat; S1-row "correct given a call": 35B solve plain is below 93 | E2 |
| X1 | 1118–1120 | "These two difficulty analyses run at the mechanism layer (... since binned delivered rates on the canonical corpus are bounds too wide to compare)" | The stated reason is the retired surface; the analysis sets tool-verified against strict unaided (WC-C7). RQ5 and RQ6 stay (E1) | E2 (Study 1); E3 if Study 2 adds size (plan D1b, D5b) |
| C1 | 1140–1147 (`fig:tokens` caption) | "a translucent bar marks a censoring bound"; "Delivered cost-of-pass (... as a range across the bound) is $0.6$--$1.6\times$ ... $2.8$--$5.2\times$ ... not identified on \emph{simulate}" | Retired (S1-Rules; Job2 row "delivered cost-of-pass multiplier, pooled ≥9B"). Study 2 has cost by price ratio (Secondary, cost row; S2-C table) | **PROPOSED E3** |
| C2 | 1171–1179 | "these ratios count successes at the mechanism layer and are labeled tool-path economics; the delivered-surface cost-of-pass is a range across the bound"; "$\approx$0.3--0.4$\times$"; "$0.6$--$1.6\times$" | Retired range, and a tool-verified ratio presented as cost (Job2 row: the 0.3–0.4× is not a delivered figure). Secondary cost row: never quote "tools are cheaper" without the price ratio | E3 |
| C3 | 1185–1191 | "at the delivered level neither arm's per-success cost is identified on this corpus"; "the tool is a luxury: $\approx$3--5$\times$ costlier per success on most \emph{validate\_*} cells" | The reason given is the retired surface; the 3–5× counts tool-verified successes (C2). Study 2 has delivered cost for every task, by price ratio (Secondary, cost row; S2-C) | E3 |
| C4 | 1203–1206 | "cap-hit-and-failed stays $\leq$10\% in the tool arms at the mechanism layer, though the same cap-hit can censor or fail the delivered answer" | Vocabulary ("mechanism layer", "censor") | E3 |
| Q1 | 1210–1215 | "At the mechanism layer, the same signed rule ... reproduces the \emph{think}=off mechanism-layer pattern ...; the delivered surface under \emph{think}=on carries the same censoring bounds ... and adds no decided cell" | Retired bounds (S1-Rules); "survives reasoning mode" checked on tool-verified only (WC-C18). Wave 2 measures it (plan D3) | E3 |
| Q2 | 1225–1230 | "The robust floor (... computed at the mechanism layer) keeps \emph{solve} robust ... \emph{simulate} sole-source ... budget-dependent" | Plan-Leaves (robust floor), regime labels | E3 |
| Q3 | 1308 | "the tool's work shows up at the mechanism layer ($97$--$99\%$) and is lost in delivery" | Vocabulary only; frontier values are not hits | E4 |

### §8 Discussion, Limitations, Conclusion — owner E5

| id | tex line | quoted text (short) | why it goes | owner |
|---|---|---|---|---|
| E5a | 1624–1625 | "all delivered-surface unless labeled" | Vocabulary | E5 |
| E5b | 1632–1634 | "open-weight models deliver at most $21\%$ in the full-storage rerun" | Superseded (Iss024d row; Readout E1 row: do NOT quote it as a figure of the rerun) | E5 |
| E5c | 1634–1636 | "a ${\approx}3$--$5\times$ token-cost luxury (tool-path economics)" | A tool-verified cost ratio; Study 2 has delivered cost by price ratio (Secondary) | E5 |
| E5d | 1636–1642 | "once called, the tool is over $92\%$ accurate. Whether that collapse costs the user's answer is bounded, not decided, on our canonical corpus" | Study 2 decides it (Readout, R1 row). **(N-flag)** "over 92%" (S1-row "correct given a call") | E5 |
| E5e | 1653–1657 | "accuracy-given-a-call exceeds $92\%$ (9B \emph{simulate}, $\approx$81\%, is the exception)" | **(N-flag)** S1-row "correct given a call" | E5 (figures from E2) |
| E5f | 1665–1667 | "how much it costs the delivered answer is corpus-dependent and, on our canonical corpus, bounded rather than decided" | Study 2 decides it (Readout, R1 row) | E5 |
| E5g | 1688–1690 | "($97$--$99\%$ at the mechanism layer)" | Vocabulary | E5 |
| L1 | 1698–1706 | "defend the cross-mode claims with budget-insensitive statistics (the robust floor)"; "through the budget-insensitive robust floor" | Plan-Leaves | E5 |
| L2 | 1717 | "that task's apparent floor is an apparatus effect" | Vocabulary ("apparatus" becomes "setup") | E5 |
| L3 | 1740–1743 | "the with-tools effect at the mechanism layer and the control on the model's own answer ... a juxtaposition across surfaces" | Vocabulary; the steering-control figures stay (NUMBERS.md nt-ster block) | E5 |
| L4 | 1763–1773 | "the tool arms' delivered rates there are censoring bounds and several availability cells are undecided rather than measured ... we pre-register that rerun ... as our declared answer should a reviewer require those cells decided" | The rerun was run (Study 2; Readout). The paragraph becomes one sentence in "How we measured" | E5; E2 ("How we measured") |
| K1 | 1826–1829 | "($-67$\,pp at the mechanism layer) ...; whether that collapse reaches the delivered answer is bounded, not decided, on our canonical corpus" | Study 2 decides it (Readout, R1 row); "-67" only as a labelled tool-verified figure (Plan-Leaves) | E5 |
| K2 | 1830–1834 | "the \emph{invocation rate} ... and the \emph{delivery gap} ... grows with answer length. Both survive reasoning mode" | The "grows with answer length" reading (Plan-E7) and "survive reasoning mode" (WC-C18) | E5 |

Out of C5's scope but in the same passages, owned elsewhere: 1675–1679 "direct empirical
support for the LLM-Modulo thesis" (plan B5); 1839–1841 "a single imperative sentence
sufficed across the $4$B--$35$B range" (WC-C18, E5).

### Appendix

| id | tex line | quoted text (short) | why it goes | owner |
|---|---|---|---|---|
| P1 | 1848–1855 and caption 1874–1883 (`tab:decomp`) | "at the mechanism layer"; "accuracy-given-a-call stays $\geq$92\% throughout, except on 9B \emph{simulate}"; caption "on the delivered surface a non-calling model can still answer correctly in prose (Results), which is why these columns are labeled mechanism" | The seven rows are Study 1 calling figures and stay: `NUMBERS.md` Study 1 provenance says `s1_calling.py` reproduces all seven rows. Hits are the vocabulary, the **(N-flag)** "≥92% throughout" (S1-row "correct given a call"), and the caption's prose claim, now measured in Study 2 (Secondary, no-call row) | **PROPOSED E2** |
| P2 | 1887–1898, 1911–1915, caption 1918–1921 (`tab:vdom`) | column "bal.$^{d}$" with "\cbnd{100.0}{100.0}", "\cbnd{92.2}{95.0}", "\cbnd{82.7}{99.2}"; "on the delivered surface the same cells are censoring bounds (last column), and the bound's claim-adverse end still clears"; caption "$^{d}$ = delivered surface (censoring bounds)" | The last column is retired (S1-Rules; the values are the Job2 row "validate_domain balanced accuracy, delivered"). The no-tools and tool-verified columns are Study 1 (T4) and stay. No Study 2 balanced accuracy is in `NUMBERS.md` yet | **PROPOSED E2** (columns 1–4); E3 for any delivered column (Decision 2) |
| P3 | 1999, 2050–2051, 2106–2107, 2116–2118, 2157 (steering control) | "Rows censored ... reported as bounds"; captions "delivered surface on determinate rows"; "censoring bounds under extreme imputation"; "two runs under one apparatus pin" | Vocabulary only. The control's figures are frozen and stay (NUMBERS.md nt-ster block). "Apparatus pin" is never defined (WC-C19) | **PROPOSED E3** (plan §5 row D7 has E3 scope the steering claim; no E step names this appendix) |
| P4 | 1963 | "re-ran the $100$ canonical \emph{simulate} trial keys" | "Trial keys" is never defined (WC-C19). Frontier probe; figures stay | E4 |
| P5 | 75–77 (preamble) | "\newcommand{\cbnd}[2]{...}" and its comment | The macro stays while any bound is printed (the frontier simulate cells). It goes when the last one goes | **PROPOSED E7** |

Not owned here: the comment at tex 651–654 ("Open-roster delivered numbers come from
results/derived/e2e_overlay/pooled_e2e_table.csv ...") is handoff item 3 (a separate small
paper PR).

## 1.3 Words with no hit or a false hit

- **"law": 0 hits.** It left the tex in PR #111 (`de7359c`, "delivery-gap law at the
  frontier"). Nothing to do.
- **"identical": 9 lines, 2 retired** (184 = I6, 923 = D2). The other 7 are plain uses and
  stay: 380, 410, 446 ("byte-identical"), 629, 1233 ("structurally identical domains"),
  1168 ("on identical data"), 1447 (PlanBench, "identical on both sides").
- **"both directions": 2 lines, 1 retired** (1080 = B3). 1360 (frontier solve domains
  "move in both directions under renaming") is a plain use.
- **"headroom" in 1301** (frontier, "the tool's headroom on tasks the model partly does")
  is plain English, not the regime label. It can stay.
- **`\cbnd` lines that are not hits** (frontier and frontier probe): 683 (notation in
  `tab:howtoread`), 793–795 (RQ4 frontier half), 832–834 (frontier panel), 932, 959, 986,
  1272–1273, 1305–1306, 1347, 1363, 1631, 1686, 1714. E4 decides these (Decision 7).

## 1.4 Search terms (re-run after any tex change)

Run from the repo root. Each term is case-insensitive. The second command lists every
`\cbnd` and which overlay row it matches; it is read-only.

```bash
for t in '\\cbnd\{' 'straddl' '\blaws?\b' 'identical' 'robust floor' \
  'realizable benefit' 'claim-adverse' 'censor' '\bindeterminate\b|\bdeterminate\b' \
  'undecided' 'both directions' 'mechanism[- ]layer' \
  'delivered surface|primary surface|two layers' 'sole[- ]source' \
  'budget-dependent|headroom' 'apparatus' 'delegation-terminal' '=off equivalent' \
  'first-draw|trial keys|apparatus pin|summary-only' \
  'bounded,? (rather than|not) decided|bounded rather than pointed' \
  'at most \$21' 'invocation rate' 'merely available|mere availability' \
  'tool path' 'tool-path'; do
  echo "== $t"; grep -n -i -P "$t" paper/main.tex | cut -c1-120
done
```

Counts at `130193e` (lines, not occurrences): `\cbnd{` 51; straddl 6; law 0; identical 9;
robust floor 5; realizable benefit 4; claim-adverse 9; censor 47; (in)determinate 14;
undecided 13; both directions 2; mechanism layer 41; delivered/primary surface or two
layers 24; sole-source 7; budget-dependent or headroom 9; apparatus 21;
delegation-terminal 1; "=off equivalent" 1; first-draw / trial keys / apparatus pin /
summary-only 5; "bounded, not decided" and kin 4; "at most $21" 1; invocation rate 13;
merely available / mere availability 5; tool path 14; tool-path 5. (Counted with the
loop above, `grep -c` in place of `grep -n`.)

**Where the high-count words sit** (all in passages that the hit list already gives an
owner, so no extra row is needed):

- "mechanism layer" (41 lines): Introduction 170; Methods 528, 590; Results 650, 656,
  713, 758, 786, 795, 797, 799, 808, 821, 846, 853, 863, 890, 926, 967, 969, 990, 1033,
  1045, 1058, 1067, 1100, 1118, 1172, 1189, 1205, 1210, 1212, 1222, 1226, 1308;
  Discussion 1689; Limitations 1741; Conclusion 1827; appendix 1874, 1893, 1919. Every one
  becomes "tool-verified" or is cut (Part 2).
- "apparatus" (21 lines): 689, 702, 829, 950, 1257, 1717, 1743, 1748, 1750, 1769, 1973,
  1992, 1993, 1996, 2124, 2157, 2198, 2206, 2210, 2211, 2217. Becomes "setup".
- "mere availability" / "merely available" (5 lines): 91 (A1), 739 (RQ3 wording: stays
  while E1 is open, Decision 9), 758 (R4), 1636 (E5d), 1826 (K1).
- "tool path" / "tool-path" (19 lines): 157, 176, 180, 809, 857, 1047, 1053, 1059, 1063,
  1085, 1108, 1124, 1172, 1629, 1630, 1635, 1636, 1850, 1874. All sit in passages above
  (Introduction, scorecard caption, T5, F3, B1–B5, X1, C2, E5a–E5d, P1). Becomes
  "tool-verified" or "calling".
- "censor" (47 lines): every open-model use is inside a hit above. The frontier uses
  (933, 947, 958, 992–993, 1271, 1290, 1363, 1978) wait for Decision 7. The steering
  control's (1999, 2032, 2116, 2165, 2219) are P3.

## 1.5 Checks run (the `/verify-claims` procedure, applied to a doc-only draft)

`.claude/skills/verify-claims/SKILL.md` was read and applied as follows. This draft adds
no new figure; it locates retired ones. So the check is "is each value I call retired
really the retired surface, and does each 'do NOT quote' flag match `NUMBERS.md`?"

| step | what was checked | result |
|---|---|---|
| 1. `NUMBERS.md` first | Study 1 block (Rules, rows "correct given a call", "calling, rerun vs main sweep", "mixed model", "paired verdicts", "validate_domain balanced accuracy"); Job2; Iss024d; Readout; Secondary; Abstract; Per-cell | each hit's "why" cites one of these; no hit quotes a figure as a new value |
| 2. source | every `\cbnd` in the tex traced to the overlay CSV `results/derived/e2e_overlay/pooled_e2e_table.csv` (`corpus = sweep5v2-live`, tool arms), by a read-only script in a scratch folder (rounded low and high compared) | every open-model bound in the hit list matches one thinking-off tool row, except: the two delivered balanced-accuracy bounds (derived, not CSV rows; they match the Job2 row), and the low end of tex 867 "\cbnd{0}{20}", which matches only thinking-on rows (Qwen3.5-4B, Qwen3.6-35B). The full-storage-rerun and frontier bounds have no `sweep5v2-live` row, as expected |
| 3. aggregation field | the overlay's `low` / `high` are the `e2e_strict` censoring bounds, which S1-Rules retires | confirmed from the CSV header and S1-Rules |
| 4. pending specs | `grep -rl PENDING development/`: no open spec touches these passages. `paper_notes_discussions.md` bottom lines: 2026-10-10 (ranges retired), 2026-11-09 later and close (RQs stay open) | consistent with this draft |
| 5. recompute | not needed: no new figure. The one mismatch (tex 867) is recorded, not corrected; the passage is retired anyway | — |
| 7. compile | no tex edit, so no compile | — |

---

# Part 2. E1a vocabulary

> **E1 is open.** This is a draft of the vocabulary only. It keeps RQ1 to RQ6 and the
> scorecard. §2.3 shows which terms each research-question framing needs, side by side.

## 2.1 Terms kept, with a one-line meaning

| term | meaning (one line) | notes / source |
|---|---|---|
| **Study 1** | The main sweep (`sweep5v2-live`; `sweep6-live` for contamination): what models do alone, how often they call, and whether the call is right | NUMBERS.md Study 1 block; plan §1 |
| **Study 2** | The pre-registered delivered rerun plus its extension on the same fixed setup: what reaches the final answer | plan §1, §4 D; Readout |
| **never pooled** | No number mixes Study 1 and Study 2 rows, and no Study 2 figure stands in for a Study 1 cell | plan §1; S1-Rules |
| **frontier tier** | The Claude models, run on their own runner, as a reference | plan §1, Outline §6 |
| **PlanBench** | The outside benchmark, now with open models too | Outline §7 |
| **unaided** | The arm with the tools removed; the model answers alone | plan Outline §3; NUMBERS.md Study 1 "Arms" |
| **plain** | Tool available plus a policy sentence (the system prompt tells the model to use the available tool); wordings v11–13 | plan Outline §3; Readout R5 (the sentence lowers calling for Gemma) |
| **neutral** | Tool available, and the system prompt is the role sentence only (no policy sentence) | `reference/delivered_rerun_prereg.md` §2, Part B; plan D2 |
| **steered** | The user prompt plus one sentence that tells the model to use the tool; wordings v14–16 | plan Outline §3; NUMBERS.md Study 1 "Arms" |
| **steering control** | The steering sentence with the tools removed, to test whether the sentence alone moves the unaided score | NUMBERS.md nt-ster block |
| **availability contrast** | plain minus unaided | replaces "availability gap" (proposal) |
| **steering contrast** | steered minus plain | replaces "steering gap" (proposal) |
| **policy-sentence contrast** | plain minus neutral (the effect of the "use the tool" sentence) | new name for the Part B 2 × 2 (proposal) |
| **delivered** | The model's own final answer, graded against the oracle. The main outcome | plan Outline §3 |
| **calling rate** | Share of tool-arm trials where the model called the task's own tool (harness field `tool_selected`). The second measure | NUMBERS.md Study 1 provenance; replaces "invocation rate" |
| **correct given a call** | Tool-verified rate among the trials that called | NUMBERS.md Study 1 (T2) |
| **tool-verified** | A correct result appeared in a tool response during the trial, whatever the final answer said. Appears once, as the mechanism check | plan Outline §3; replaces "mechanism layer" |
| **gate 1 (calling)** | The model has to call the tool | plan §1; Readout R3 |
| **gate 2 (delivery)** | The tool's result has to reach the final answer | plan §1; Readout R3 |
| **delivery gap** | Trials where the tool returned a correct result but the final answer is not right, with the reason (for example clipped, refused, wrong wrapper). A description, not a law | weakness Q5; Secondary E4 hand read |
| **context room** | How much of the window is left for the answer after the tool result | plan D1c, D2 |
| **thinking on / thinking off** | The serving runtime's reasoning switch. Tables may write on / off | replaces "think=on", "think=off equivalent" in prose |
| **wording** | One of the three user-prompt wordings per task and arm; "prompt v11" is defined once in Methods | plan B3; replaces "paraphrase" in prose |
| **canonical / anonymized corpus** | The public domains, and the same domains with every surface name renamed (lexical only) | tex Contamination Control (PR #123) |
| **contamination test** | Paired, clustered, ±5 equivalence test, anonymized minus canonical | NUMBERS.md Study 1 (T7) |
| **headline models** | Qwen3.5-9B, Gemma-26B, Qwen3.6-35B | NUMBERS.md Study 1 block |
| **setup** | One run configuration: harness version, serving version, storage, grader | plan §1 ("the fixed setup"); replaces "apparatus" |
| **cost-of-pass** | Tokens per correct delivered answer, always with the output-to-input price ratio | Secondary, cost row |
| **format-exact** | The strict unaided simulate grade; always quoted with its qualifier | Job2 row "open-roster unaided simulate" |
| **answer contract** | The format and length rules the final answer must meet | plan §5 row D8 ("budget and format contract") |
| **first answer** (PlanBench) | The first answer drawn, as opposed to the last attempt; defined once in §7 | replaces "first-draw" (PlanBench block) |

## 2.2 Terms that go, and what replaces them

| term that goes | why | replaced by |
|---|---|---|
| delivered surface, primary surface, "two layers", "one surface, three value shapes" | private vocabulary (WC-C19) | "delivered" (one main score) |
| mechanism layer, "mechanism", tool path | private vocabulary (WC-C19; 41 lines) | "tool-verified", or "called and got a correct tool result" |
| censoring bound `⟨a, b⟩`, `\cbnd`, indeterminate / determinate rows | existed to handle the ranges (weakness Q9); retired with them (S1-Rules) | exact Study 2 rates. Frontier simulate: Decision 7 |
| claim-adverse end | same | — (no bounds) |
| straddling, straddles, "undecided in both directions" | retired; wrong for two of three cells (WC-D3) | Study 2's registered labels (Readout, for example "No delivered harm", "Unresolved") |
| undecided, as a verdict made from bounds | same | Study 2 labels; Study 1 paired tests (T5) |
| robust floor; budget-insensitive statistics | Plan-Leaves | reasoning mode measured directly (plan D3) |
| realizable benefit | Plan-Leaves | "steered minus unaided", said in plain words where needed |
| sole-source, headroom, mixed, robust, budget-dependent (regime labels) | private vocabulary | plain descriptions: "the model cannot do it alone under this answer contract", "weak unaided score" |
| invocation, invocation rate | two words for one thing | calling, calling rate |
| "merely available", "mere availability" (for the plain arm) | the plain arm carries a policy sentence (Readout R5) | "plain: tool available plus a policy sentence"; "neutral" for the arm without it |
| "law", "identical" (as claims) | Plan-Leaves; WC-C5 | a description of how often a correct tool result fails to reach the answer, and why |
| "-67" as a headline | Plan-Leaves | a labelled tool-verified figure only (S1-row "Gemma validate_plan availability") |
| apparatus, apparatus pin | private vocabulary | setup |
| delegation-terminal | private term | "empty final answer after a correct tool result" |
| "think=off equivalent" | never defined (WC-C19) | "thinking off" |
| trial keys; summary-only failures | never defined (WC-C19) | "the same trials (task, wording, problem)"; define or drop |
| tool-path economics | a tool-verified ratio read as cost | Study 2 cost-of-pass by price ratio |
| availability gap, steering gap | "gap" also names the delivery gap | availability contrast, steering contrast (proposal) |

## 2.3 The two research-question framings, side by side

Both stay on the table (E1 open). The rows say which vocabulary each one needs. "Needs"
means the framing cannot be written without the term.

| term | Existing RQ1–RQ6 + scorecard | Suggested Q0 / Q1 / Q2 (gates) |
|---|---|---|
| unaided | needed (every RQ has an unaided side) | needed (Q0 is the unaided baseline) |
| plain | needed (RQ1–RQ4; RQ3 calls it "mere availability", which would need rewording, not removal) | needed (Q1) |
| neutral | optional (RQ3 could cite it as the check on "availability") | needed (Q1: prompt wording across families) |
| steered | needed (RQ3) | needed (Q1) |
| delivered | needed (RQ1–RQ4 and the scorecard's delivered cells) | needed (Q2) |
| tool-verified | needed (RQ5, RQ6 rows are tool-verified; RQ3 mechanism) | needed once (the mechanism check under Q1) |
| calling rate | needed (RQ3) | needed (Q1 is the calling question) |
| gate 1 / gate 2 | not needed (the gates cut across RQs; `paper_notes` 2026-11-09 maps them) | needed (Q1, Q2) |
| delivery gap | needed (RQ4's evidence) | needed (Q2) |
| context room | not needed | needed (Q2) |
| thinking on / off | needed (the robustness passage) | needed (Q1 factor) |
| problem size (plan length, object count, D5b ladder) | needed as its own questions (RQ5, RQ6) | a factor under each question, not a question |
| item kinds (harder items, D1b) | not needed | needed (Q1 factor) |
| verdict labels (YES / MIXED / NO) and the rule behind them | needed (the scorecard). The rule changes in E2 either way: paired, clustered, Holm tests (S1-row "paired verdicts"; WC-C9) | not needed |
| per-task framing (validate_domain, ..., simulate) | needed (RQ1–RQ4 are per task) | tasks become a factor under Q0–Q2 |
| format-exact (with qualifier) | needed (RQ4) | needed (Q0) |
| cost-of-pass | needed (Results cost passage) | needed (under Q2 or Discussion) |

What changes under either framing: the scorecard cells S1–S4 that carry retired ranges get
new evidence (Part 1); RQ3's "mere availability" needs new words; RQ5 and RQ6 say they are
tool-verified. What the suggestion adds: the gate words, context room and item kinds.
What it drops: the scorecard and its verdict labels (`draft_E1_research_questions.md`,
"Suggested"). Omer decides; this draft only lists what each needs.

---

## Decisions for Omer

1. **Introduction owner.** Recommend **E6**: write it last with the title and abstract,
   because it previews the findings and the contributions (at most three). Add a line to
   the plan's E table.
2. **`tab:vdom`.** Recommend **E2** owns the no-tools and tool-verified columns (Study 1,
   T4), and the delivered column is dropped. If E3 wants a delivered validate_domain
   figure, a script must compute a Study 2 balanced accuracy first; `NUMBERS.md` has none
   yet.
3. **`tab:decomp`.** Recommend **E2**. Keep the seven rows (Study 1, reproduced by
   `s1_calling.py`); rewrite the caption without "mechanism layer" and "delivered
   surface"; fix "≥92% throughout" to the S1-row "correct given a call".
4. **The figures.** Funnel, solve and simulate, failure taxonomy and token quadrant draw
   their open-model bars from the retired overlay (`make_paper_figures.py`). Recommend
   **E3** owns the open-model panels (redrawn from Study 2 after D4), **E4** the frontier
   and PlanBench panels, **E2** `fig:mechanism` (wording only). The redraw is a code PR on
   the figure generator.
5. **`tab:howtoread`.** Recommend it becomes the appendix "How we measured" table of
   setups (Plan-Outline), owned by **E2**. No E step names that appendix today; add it to
   E2.
6. **The full-storage rerun (`iss024d`) figures in the body** (the Gemma validate_plan
   bound, "at most 21%", the simulate panel). Recommend **dropping them from the body**:
   that rerun carries the same harness faults as the main sweep (`paper_notes`
   2026-10-10), and Study 2 measures the same things on the fixed setup. At most one line
   in "How we measured". Owner E3.
7. **Frontier simulate bounds,** the only bounds left once the open-model ranges go.
   Recommend **keeping them in §6 as labelled bounds**, with one notation defined once in
   E4, because the probe is a different setup and `NUMBERS.md` (Job2, budget-probe row)
   forbids pooling probe rows with the canonical cells. The `\cbnd` macro then stays
   (P5).
8. **The steering-control appendix (P3).** Recommend **E3** (plan §5 row D7 already has
   E3 scope that claim). Wording only; the figures are frozen.
9. **Arm names.** Recommend "plain (tool available plus a policy sentence)" and
   "neutral" as the two names, and never "merely available". If RQ3 is kept, reword its
   "mere availability" to match. This is part of E1.
10. **"Calling" over "invocation".** Recommend "calling" and "calling rate" everywhere
    (plan and `NUMBERS.md` already use them).
11. **"Gap" for the two contrasts.** Recommend "availability contrast" and "steering
    contrast", so "gap" means only the delivery gap. Low stakes; say no and the tex keeps
    "gap".
