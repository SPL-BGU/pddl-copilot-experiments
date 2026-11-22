# Draft: steps B3, B4 and B5 (Methods text on test data, prompts, the checker; two claims)

*2026-10-27. Drafts for `weakness_action_plan.md` §4 B, rows B3 to B5. Nothing in `paper/`
was changed and nothing was committed. The edits below move later lines, so apply them
bottom-up or by the quoted anchor text. When Omer okays this, the PR follows;
`/verify-claims` runs on that PR.*

*Refreshed 2026-11-09 (handoff item 6). Tex line numbers are now at `main` `130193e`: every
anchor was re-found by its quoted text after PR #123 shifted the lines from about tex 630
on (the anchors before that did not move). B4's VAL slot is filled from `NUMBERS.md`. The
open questions of both B drafts are in one answer list just below. Code line numbers in
the grounding tables are still at `d57dd68` (this repo) and `2850bc4` (plugins). For
`tools/claude_api_batch.py`, which PR #131 edited, read them from that file at `bbcf111`
(`MOVES.md`, row of 2026-11-09).*

---

## Answer list for Omer (both B drafts)

This one list holds all the open questions of the two B drafts: items 1 to 12 come from
`draft_B1_B2_related_work.md` §5 and items 13 to 21 from the end of this file (21 in all,
as the handoff counted). Items 22 and 23 are new from the 2026-11-09 refresh. The question
text is kept as it was. The recommendation is the choice the draft makes now (or, where
the draft made none, mine, marked "Mine"), and a status line says what has changed since
2026-10-27. **None of the 21 had been answered by Omer when this list was made** (checked
against `paper_notes_discussions.md`, `STATUS.md` and `handoff_20261109.md` §2 on
2026-11-09). Write your answer after "ANSWER:".

**From B1 and B2 (`draft_B1_B2_related_work.md`)**

1. **Where B2 goes in the paper.** I made it its own short subsection at the end of §2
   ("Relation to the Preliminary Study", `\label{sec:prelim}`, which Positioning points
   to). The other options are the last paragraph of Positioning, or the Introduction.
   *Recommendation:* its own subsection, as drafted.
   > ANSWER:
2. **The "scored by tool selection" description is not quite what the arXiv paper did.**
   Its text says final answers were also checked (with VAL, the simulator, and by hand),
   and the correct tool call was an extra requirement. The draft says this: success
   needed both, so calling and delivery were folded into one number. The same correction
   applies to the memory note and to the cover letter. Is this the framing you want?
   *Recommendation:* yes, and the same words in the cover letter (F3).
   > ANSWER:
3. **The tool suite changed after the arXiv version.** That paper used Metric-FF for
   numeric planning and a VAL wrapper. Ours uses ENHSP and validators on
   `unified-planning`. The tex (line 314) says the suite "packages the Planning Copilot
   tools" of the arXiv paper. The draft says "an earlier version of this tool suite".
   Should B3/B4 state the change, and should B2 mention it?
   *Recommendation:* the draft keeps "an earlier version of this tool suite" in B2 and
   states the change nowhere else yet. Mine: one sentence in B3.1 naming the two changes,
   and B2 as drafted.
   > ANSWER:
4. **Calling figures in B2.** I used Study 1's 21% to 94% (the abstract's figures). Study 2
   has its own: 20.0% plain and 93.1% steered (R5 table). Using Study 2 would keep the
   whole Gemma passage inside one study. Which one?
   *Recommendation:* the draft uses Study 1, the abstract's figures. The two studies sit in
   separate sentences and are not combined.
   > ANSWER:
5. **Self-citation wording after de-anonymizing (F1).** The draft says "a preliminary study
   of an earlier version of this tool suite", in the third person. Under JAIR, once
   de-anonymized, it could say "the preliminary version of this work". Your call when F1
   happens.
   *Recommendation:* third person until F1.
   > ANSWER:
6. **Model name.** The draft uses "Gemma-MoE-26B" as the tex does now. E1 fixes the
   vocabulary, so this may change.
   *Recommendation:* keep the tex name until E1a decides.
   > ANSWER:
7. **The two Qwen validate_plan gains** (+14.2 for the 9B and +7.4 for the 35B, readout E2)
   would show that skipping the tool is model-specific. They are not in `NUMBERS.md` yet,
   so the draft leaves them out. Add a row and a clause?
   *Recommendation:* left out, as drafted. If you want the clause, a script adds the
   `NUMBERS.md` row first. *Status 2026-11-09:* still not in `NUMBERS.md`.
   > ANSWER:
8. **MCP benchmarks.** MCP-Universe and MCP-AgentBench are arXiv only. MCPAgentBench is a
   workshop paper (REALM at EMNLP 2026, per its arXiv record). MCP-Bench is ICLR 2026.
   Keep all four, or only MCP-Bench and MCP-Universe?
   *Recommendation:* the draft keeps all four, each cited for its own design point.
   > ANSWER:
9. **HAL** is cited once, for reporting accuracy against cost. Keep it or drop it?
   *Recommendation:* keep it, as drafted; our cost-of-pass analysis follows that practice.
   > ANSWER:
10. **The Introduction (lines 123 to 133) repeats the old three-lines framing**, including
    "has not been answered cleanly". It should match the new Positioning when E rewrites
    the Introduction. I did not touch it.
    *Recommendation:* leave it to the Introduction rewrite in E, and put it on the C5 hit
    list. *Status 2026-11-09:* the line numbers still hold at `130193e` (the quoted text is
    on line 130; the paragraph runs to line 137).
    > ANSWER:
11. **Optional references** (listed under §3, verified, not used): Chain of Thoughtlessness,
    LLM-Modulo for travel planning, The Illusion of Thinking. Add any?
    *Recommendation:* none (the draft adds none).
    > ANSWER:
12. **Thinking mode in B2.** The arXiv paper reported the better of each model's two
    modes. The new Study 1 block in `NUMBERS.md` (added today by the C2 work, not yet
    committed) has Gemma's validate_plan calling falling from 20.7% to 0.6% with thinking
    on. One sentence on this would show why reporting modes separately matters. Add it
    once that block is final? (Study 2's D3 measures it again on the fixed setup.)
    *Recommendation:* yes. *Status 2026-11-09:* the block is merged (PR #121). The figure is
    in `NUMBERS.md` "Study 1", row "calling under thinking on" (Gemma 20.7% → 0.6%,
    19/3,000). The handoff (§3) records that Gemma really thinks with thinking on, so the
    fall stands as a thinking-on effect.
    > ANSWER:

**From B3 to B5 (this file)**

13. The test-data counts in B3 are not in `NUMBERS.md`. Add the block at the end of this
    file to `NUMBERS.md` in the same PR? *Recommendation:* yes.
    > ANSWER:
14. `reanalysis_breakdowns_cost.md` §4.3 has the block-grouping error. Add a one-line dated
    correction there, or leave the record alone and let `NUMBERS.md` carry the right value?
    *Recommendation:* the draft gives no pick. Mine: leave the record alone and let the
    `NUMBERS.md` block carry the right value; its "do NOT quote" column already names the
    wrong split.
    > ANSWER:
15. B3.2 puts the full test-data description in the Methods body. Keep it there, or keep
    one short paragraph in the body and move the counts to the appendix?
    *Recommendation:* the draft keeps it in the body (C11 says the test data are barely
    described, and a journal has room).
    > ANSWER:
16. The draft says "wording" instead of "paraphrase" and "plain wordings" instead of
    "neutral paraphrases", so "neutral" stays free for the system-message arm. Adopt this
    throughout in E1? *Recommendation:* yes, in E1a.
    > ANSWER:
17. The default solve system message contains "arXiv:2509.12987". Keep it verbatim in the
    appendix (it is what the models saw) and accept that it names our earlier paper?
    *Recommendation:* the draft keeps it verbatim. Mine, in addition: under double-blind
    review it names our earlier paper, so mask it until F1.
    > ANSWER:
18. There is no citation for `unified-planning` in `refs.bib`, and `pyval` has no paper.
    Have B1 verify and add one for `unified-planning`, and cite `pddl-pyvalidator` by
    package and version in a footnote? The exact versions on the cluster are not recorded
    anywhere I could find (laptop: `pddl-pyvalidator` 0.1.5, `unified-planning` 1.3.0).
    Reading them off the cluster needs your go-ahead.
    *Recommendation:* yes to both. *Status 2026-11-09:* reading the cluster versions is part
    of the one cluster go-ahead in `handoff_20261109.md` §4 item 11. The extension grades
    with `pddl-pyvalidator` 0.1.6 (handoff decision 13, the case fix), so the footnote must
    name the version for each study.
    > ANSWER:
19. Add the Sonnet failure split (205 of its 214 unaided solve failures are wrong plans) to
    B5.2? It is not in `NUMBERS.md`, so it is left out for now.
    *Recommendation:* leave it out. *Status 2026-11-09:* the split was counted before the
    pyval case fault (ISS-027) was found. Under VAL, 12 of Sonnet's 300 canonical unaided
    solve trials move from fail to success (`NUMBERS.md` "VAL on the Claude solve plans"),
    so the split needs a recount by script first.
    > ANSWER:
20. The Background sentence (B5.3) sits in the section B1 rewrites. Apply it with B5, or
    hand it to B1?
    *Recommendation:* the draft gives no pick. Mine: hand it to B1. B1's §1 already
    replaces tex 193 to 273, and with it the sentence at 215 to 217.
    > ANSWER:
21. Should noticed items 2, 3 and 4 get their small fixes in this PR, or wait for E2, E4
    and E5? *Recommendation:* the draft gives no pick. Mine: wait, so the B PR stays small,
    and add the three to the C5 hit list.
    > ANSWER:

**New from the 2026-11-09 refresh**

22. **How to show the pyval case fault (ISS-027) beside frozen figures in the B text.** B4.1
    now says the stored grades are reported with the VAL grades beside them, labelled post
    hoc. Two drafted sentences quote frozen unaided solve figures that the fault lowers:
    B2's "22--29% unaided" and B5.2's Sonnet "28.7%". Under VAL they read Haiku 25.0 and
    Sonnet 32.7 (`NUMBERS.md` "VAL on the Claude solve plans"; Sonnet is still under a
    third, so B5.2's wording holds). *Recommendation (mine):* keep the frozen figure in the
    sentence and add the VAL reading in a short parenthesis or footnote marked post hoc.
    Never replace the frozen figure.
    > ANSWER:
23. **Which version of Corrêa et al. to cite.** The B1 draft cites arXiv:2511.09378 v2 (key
    `correa2025frontier`). A 2026 CACM version exists under a different title (Seipp's lab
    page, per `draft_D5_cost_and_correa.md`). *Recommendation (mine):* cite arXiv v2 now,
    since that is the text D5 checked; switch to CACM only after its details and the
    authors' given names are verified.
    > ANSWER:

**What is here**

| step | LaTeX block | where in `main.tex` | settles |
|---|---|---|---|
| B3 | B3.1 Tool Suite: seven tools, PDDL pasted, `pyval` named | 305 to 313 (anchor "Five tools cover the") and 318 to 320 | C11 |
| B3 | B3.2 Test data and Prompts paragraphs, "prompt v11", the frontier's single wording | 366 to 381 (whole paragraph) | C11, C12 |
| B3 | B3.3 small fixes ("appended", "complete prompt bank ships") | 453, 461 to 462, 493 | C11 |
| B3 | B3.4 appendix: Prompts (verbatim) and Test data per domain (table) | new, after line 2242 | C11, C12 |
| B4 | B4.1 the "by construction" sentence, the checker named, solve uses two programs | 328 to 334 (anchor "Before any model is run") | C2, C8, D1 |
| B4 | B4.2 table row and caption, optional "sound" and Metrics edits | 353, 360 to 362, 301, 523 | C2, C8 |
| B5 | B5.1 to B5.3 the two claims, every occurrence | 1360 to 1362 (already rewritten by PR #123), 1675 to 1689, 215 to 217 | C18 |

**Rules followed.** Every experiment number comes from `NUMBERS.md` (section named in the
grounding tables). The test-data counts in B3 are not experiment results and are not in
`NUMBERS.md` yet. They come from `reference/reanalysis_breakdowns_cost.md` §4 and from my own
recount of `domains/` today. A ready-to-paste `NUMBERS.md` block for them is at the end
(answer list item 13). The rerun readout's false sentence about sampling "under the per-task JSON
constraint" is not used anywhere. The suite is never called "checked by VAL".

**One correction to a reference doc.** `reanalysis_breakdowns_cost.md` §4.3 says 12 of the 20
invalid domains differ only by a parenthesis count and 1 has its `:predicates` block removed.
The "removed" one is block-grouping, and block-grouping's valid domain has no `:predicates`
block at all. Its invalid file differs by one extra closing parenthesis (`diff` shows only
line 55, `)` against `))`). The right split is 13 by parenthesis (10 extra, 3 missing), 5
undeclared predicate, 2 dropped hyphen. The drafts use 13. Every other §4 count I rechecked
matched (list in the grounding table).

---

## B3. Test data and prompts

### B3.1 Tool Suite (replaces tex 305 to 313, from "Five tools cover the" to "with well-typed arguments.")

The current text says "Five tools cover the five tasks" and then lists six. The harness
exposes seven.

```latex
Every tool trial, open-weight or frontier, exposes the same seven tools from two
plugins. The solver plugin provides a classical planner (Fast Downward
\citep{helmert2006fastdownward}), a numeric planner (ENHSP \citep{scala2016enhsp}) and
a tool that saves a plan to a file. The validator plugin provides
\texttt{validate\_domain}, \texttt{validate\_problem} and \texttt{validate\_plan}, which
return a VALID or INVALID verdict, and \texttt{get\_state\_transition}, which returns
the state trajectory a plan induces. The four validator tools run \texttt{pyval} (the
\texttt{pddl-pyvalidator} package), a Python plan validator built on the
\texttt{unified-planning} library, and both planners are also called through
\texttt{unified-planning}. Each task has one matching tool. On \emph{solve} there are
two, and the model picks the planner that fits the domain. The harness never narrows
the list, so every tool trial also tests whether the model picks the right tool, and
calls to the wrong tool do occur. The validator tools take an optional
\texttt{verbose} flag, which the harness removes from the schema the model sees and
fixes to false. The tools accept PDDL either as text or as a file path. The harness
gives no paths, so the model has to copy the PDDL text from its prompt into the call.
In the canonical corpus every call that carried a domain argument passed that text.
The tools are deterministic, and what the model contributes is choosing the matching
tool and passing the task's files into it intact.
```

Keep the next sentence ("The suite packages the Planning Copilot tools of ...") as it is.
Then replace its last sentence (tex 318 to 320, "The verbatim per-task prompts that expose
these tools, together with the one-sentence steering directive, appear in
Listing~\ref{lst:prompts}.") with:

```latex
Listing~\ref{lst:prompts} shows two of the system messages and the steering sentences,
and the Technical Appendix (Prompts) gives every prompt verbatim.
```

### B3.2 Test data and Prompts (replaces tex 366 to 381, the whole paragraph "The fixture corpus is 20 PDDL domains ... from paraphrase variance.")

The current paragraph calls the three wordings "imperative, declarative, interrogative
framings". None of them is declarative. On the verdict tasks two are instructions and one
is a question; on solve and simulate all three are instructions, and they also word the
answer format differently. The draft says so.

```latex
\paragraph{Test data.} The test set has 20 PDDL domains, 10 classical (e.g.,
blocksworld, gripper, rovers, satellite, depots) and 10 numeric (e.g., counters,
farmland, sailing, drone). Ten come from the dataset of \citet{benyamin2025copilot}
and ten from public benchmark suites. Four problems of one numeric domain are small
hand-written variants. Each domain has one valid and one invalid domain file, five
valid and five invalid problems, and five valid and five invalid plans for each valid
problem, 1{,}240 files in all. The valid plans come from the planners. For 99 of the
100 problems the five valid plan files are copies of one plan.

Every invalid file is an edit of a valid one, kept only if \texttt{pyval} rejected it,
and the harness checks every label again at startup. Of the 20 invalid domains, 13
differ from the valid file only by an unbalanced parenthesis, 5 use an undeclared
predicate and 2 drop the hyphen of a typed parameter list. The ten domains added for
this study all received the generator's first edit, one extra closing parenthesis. The
ten from the earlier dataset kept their hand-made invalid files. The 100 invalid
problems are edits of each domain's first problem. Of these, 45 use an object or
predicate that is not declared, 20 have an unbalanced parenthesis, 26 have no goal (13
of them also an extra parenthesis), and 9 have no objects block or no initial-state
block. The 500 invalid plans keep every action name and argument count legal, so each
error lies in what the plan does. In 400 of them steps were deleted (290 from the
middle and 110 from the end), 74 swap the first two arguments of one step, 17 repeat a
step, and 9 are hand-made files from the earlier dataset. In all, 380 of the 500 are
exactly one step shorter than the valid plan they came from. A valid problem declares
2 to 35 objects (median 9), and its reference plan has 2 to 110 steps (median 11.5).
Domain files run from 686 to 5{,}542 characters. Table~\ref{tab:domain-sizes} in the
Technical Appendix gives the sizes per domain.

One cell holds 4{,}560 trials: \emph{solve} 300, \emph{validate\_domain} 360,
\emph{validate\_problem} 600, \emph{validate\_plan} 3{,}000 and \emph{simulate} 300,
split evenly over three prompt wordings. Valid and invalid items are balanced on
\emph{validate\_problem} and \emph{validate\_plan}. On \emph{validate\_domain} each
wording has 100 valid trials (one per problem) and 20 invalid ones, so a model that
always answers VALID scores 83\%, and we report balanced accuracy there. Many trials
repeat a prompt exactly. The valid-domain prompt holds only the domain, so it repeats
once per problem, and the five valid plans of a problem are almost always one plan. Per
arm, \emph{validate\_plan} has 1{,}803 distinct prompts in 3{,}000 trials and
\emph{validate\_domain} has 120 in 360. The plan in a \emph{simulate} prompt is the
planner's plan, the one whose trajectory is the answer key. The difficulty bins in
Results split the trials into thirds. By reference plan length they are at most 8, 9
to 19, and more than 19 steps (on \emph{validate\_plan}, valid plans only). By object
count they are at most 6, 7 to 14, and more than 14 objects (at most 5, 6 to 13, and
more than 13 on \emph{validate\_problem}).

\paragraph{Prompts.} Each trial sends one system message and one user message. The
user message states the task in one of three wordings and then pastes in full the
PDDL the task needs. That is the domain file, the problem file except on
\emph{validate\_domain}, and the plan, one action per line, on \emph{validate\_plan}
and \emph{simulate}. The message gives no file paths. With the system message, a
prompt runs from about 1{,}000 to 10{,}100 characters. On the three verdict tasks the
wordings differ only in the opening sentence, two of them instructions and one a
question, and all three end with the same required verdict line. On \emph{solve} and
\emph{simulate} all three wordings are instructions, and they also describe the answer
format in different words. For example, only the second \emph{solve} wording asks for
each action on its own line. The steered arm adds one sentence that names the tool at
the end of the task statement, before the PDDL, and this sentence is the same for all
three wordings of a task. The system message depends only on the task and the arm. The
Technical Appendix (Prompts) gives every wording, system message and steering sentence
verbatim. We refer to the plain wordings by their indices in the released prompt bank,
v11, v12 and v13, and to their steered forms as v14 to v16, so ``prompt v11'' is the
first plain wording. The frontier tool runs used v11 only, and so did the Haiku
unaided run. The Sonnet unaided run used all three wordings. On the open-weight models
the wording moves both unaided success and how often a model calls the tool, so the
frontier results rest on a single wording and may not hold for the other two.
```

Notes on B3.2:

- The per-wording table that C3 builds should be cited after the last sentence once it
  exists (for example "(Technical Appendix, per-wording table)").
- Optional one-line version for Limitations when E5 splits that section: "The frontier tool
  runs used one prompt wording (v11), so the frontier comparisons do not show how wording
  affects that tier."

### B3.3 Small fixes that follow from B3.2 (optional, same PR)

| tex line | now | change to | why |
|---|---|---|---|
| 453 to 454 | "the neutral prompt plus exactly one appended sentence directing the model to use the tool." | "the plain prompt plus exactly one added sentence directing the model to use the tool." | the sentence goes before the PDDL, and the prompt does not end with it; "neutral" is kept free for the system-prompt arm (E1) |
| 461 to 462 | "The complete prompt bank ships with the released harness." | "The Technical Appendix (Prompts) gives every prompt verbatim." | the appendix now has them |
| 493 | "the steering contrast appends the single directive shown to the neutral user prompt" | "the steering contrast adds the single directive shown to the plain user prompt, after the task statement and before the PDDL" | same as line 453 |

### B3.4 Appendix blocks (new, insert after tex line 2242, the end of "Canonical trajectory normalization", before the Reproducibility Checklist comment)

The listings were generated from `pddl_eval/prompts.py` by a script, not typed. The script
also checked that each steered wording equals the plain wording plus one sentence at the
end of the first paragraph (on simulate: on its own line after the example step), and that
the sentence is the same for all three wordings of a task. Both checks passed.
`<domain>`, `<problem>` and `<plan>` are placeholders.

```latex
\paragraph{Prompts.}
Every trial sends one system message and one user message, built by the same function
for the open-weight and the frontier runs. In the listings below, \texttt{<domain>},
\texttt{<problem>} and \texttt{<plan>} stand for the full text the harness pastes in,
the plan as one action per line. The plain wordings v11 to v13 are shared by the
unaided arm and the plain tool arm. The steered form (v14, v15 or v16) of a wording
adds the task's steering sentence, after a space, at the end of the first paragraph. On
\emph{simulate} the sentence is added as its own line after the example step. The
steering control's unaided arm uses the steered forms. The system message depends only
on the task and the arm. The tool arms use the default form in Study~1 and in the
frontier runs, and Study~2 adds the neutral form, which keeps only the first sentence.
The unaided \emph{solve} and \emph{simulate} system messages refer to a format
constraint. That constraint was requested from the server but did not take effect
(Limitations). The frontier unaided runs differ from this in two details. For
\emph{solve} the plan was requested through the provider's structured-output parameter
with a schema holding a list of action strings. For \emph{simulate} one sentence was
appended to the user message:
\begin{lstlisting}[numbers=none]
Return ONLY a single JSON object (no prose, no markdown code fences) of the form {"trajectory": [ ...steps... ]}, where each step matches the example above (keys: step, action, state.boolean, state.numeric).
\end{lstlisting}

\noindent\emph{solve}, user message, three plain wordings
\begin{lstlisting}[numbers=none]
--- wording 1 (v11) ---
Solve this PDDL planning problem and return a plan. Each step must be a single parenthesised PDDL action, e.g. `(pick-up a)`.

Domain:
<domain>

Problem:
<problem>

--- wording 2 (v12) ---
Find a valid plan for this PDDL problem. Output each action on its own line in parenthesised PDDL form, e.g. `(unstack a b)`.

Domain definition:
<domain>

Problem definition:
<problem>

--- wording 3 (v13) ---
Generate a plan that solves the following planning problem. Each action in your plan must be a single parenthesised PDDL form, e.g. `(stack a b)`.

Domain:
<domain>

Problem:
<problem>

--- steering sentence (v14-v16) ---
Use the planner tool with the domain and problem as arguments.
\end{lstlisting}

\noindent\emph{validate\_domain}, user message, three plain wordings
\begin{lstlisting}[numbers=none]
--- wording 1 (v11) ---
Check if this PDDL domain definition has valid syntax.

<domain>

End your response with exactly one line: VERDICT: VALID or VERDICT: INVALID

--- wording 2 (v12) ---
Validate the following PDDL domain for syntactic correctness.

<domain>

End your response with exactly one line: VERDICT: VALID or VERDICT: INVALID

--- wording 3 (v13) ---
Is this PDDL domain syntactically correct?

<domain>

End your response with exactly one line: VERDICT: VALID or VERDICT: INVALID

--- steering sentence (v14-v16) ---
Use the validate_domain tool with the domain as its argument.
\end{lstlisting}

\noindent\emph{validate\_problem}, user message, three plain wordings
\begin{lstlisting}[numbers=none]
--- wording 1 (v11) ---
Check if this PDDL problem has valid syntax given the domain.

Domain:
<domain>

Problem:
<problem>

End your response with exactly one line: VERDICT: VALID or VERDICT: INVALID

--- wording 2 (v12) ---
Validate the syntax of this PDDL problem against its domain.

Domain:
<domain>

Problem:
<problem>

End your response with exactly one line: VERDICT: VALID or VERDICT: INVALID

--- wording 3 (v13) ---
Is this PDDL problem file syntactically correct for the given domain?

Domain:
<domain>

Problem:
<problem>

End your response with exactly one line: VERDICT: VALID or VERDICT: INVALID

--- steering sentence (v14-v16) ---
Use the validate_problem tool with the domain and problem as arguments.
\end{lstlisting}

\noindent\emph{validate\_plan}, user message, three plain wordings
\begin{lstlisting}[numbers=none]
--- wording 1 (v11) ---
Validate whether this plan is correct for the given domain and problem.

Domain:
<domain>

Problem:
<problem>

Plan:
<plan>

End your response with exactly one line: VERDICT: VALID or VERDICT: INVALID

--- wording 2 (v12) ---
Check if the following plan solves the PDDL problem.

Domain:
<domain>

Problem:
<problem>

Plan:
<plan>

End your response with exactly one line: VERDICT: VALID or VERDICT: INVALID

--- wording 3 (v13) ---
Is this plan valid for the given planning problem?

Domain:
<domain>

Problem:
<problem>

Plan:
<plan>

End your response with exactly one line: VERDICT: VALID or VERDICT: INVALID

--- steering sentence (v14-v16) ---
Use the validate_plan tool with the domain, problem, and plan as arguments.
\end{lstlisting}

\noindent\emph{simulate}, user message, three plain wordings
\begin{lstlisting}[numbers=none]
--- wording 1 (v11) ---
Simulate this plan and return the trajectory. Step 0 is the initial state from the problem with `action` empty. Each later step records the action executed. `state.boolean` lists EVERY predicate that holds in that state, each as a parenthesised lowercase form, e.g. `(on a b)`; `state.numeric` is the fluents map.
Example step: {"step": 0, "action": "", "state": {"boolean": ["(on a b)", "(clear c)"], "numeric": {}}}

Domain:
<domain>

Problem:
<problem>

Plan:
<plan>

--- wording 2 (v12) ---
Step through this plan action by action. For each step emit `action` (the action just executed, or empty for step 0) and `state.boolean` listing every currently-true predicate in parenthesised PDDL form, e.g. `(on a b)`.
Example step: {"step": 1, "action": "(unstack a b)", "state": {"boolean": ["(holding a)", "(clear b)"], "numeric": {}}}

Domain:
<domain>

Problem:
<problem>

Plan:
<plan>

--- wording 3 (v13) ---
Show the state at each step of this plan. Step 0 = initial state with empty `action`. Each `state.boolean` entry lists every predicate that holds in that state, parenthesised and lowercase; `state.numeric` is the fluents map (empty for purely-symbolic domains).
Example step: {"step": 0, "action": "", "state": {"boolean": ["(ontable a)", "(clear a)"], "numeric": {}}}

Domain:
<domain>

Problem:
<problem>

Plan:
<plan>

--- steering sentence (v14-v16) ---
Use the get_state_transition tool with the domain, problem, and plan as arguments.
\end{lstlisting}

\noindent System messages
\begin{lstlisting}[numbers=none]
--- solve, unaided arm ---
You are a PDDL planning assistant. PDDL planning tools are not available in this evaluation. Analyze the domain and problem and produce a plan using your own reasoning; conform to the JSON schema provided by the format constraint.
--- solve, tool arms (default) ---
You are a PDDL planning assistant. LLMs cannot reliably generate correct plans from training alone (arXiv:2509.12987). Use the available planner tool to produce the plan.
--- solve, tool arms (neutral style, Study 2) ---
You are a PDDL planning assistant.

--- validate_domain, unaided arm ---
You are a PDDL validation assistant. PDDL validation tools are not available in this evaluation. Analyze the domain syntax using your own reasoning; end your response with exactly one line: VERDICT: VALID or VERDICT: INVALID.
--- validate_domain, tool arms (default) ---
You are a PDDL validation assistant. LLMs cannot reliably check PDDL syntax from training alone. Use the available validation tool to check the domain.
--- validate_domain, tool arms (neutral style, Study 2) ---
You are a PDDL validation assistant.

--- validate_problem, unaided arm ---
You are a PDDL validation assistant. PDDL validation tools are not available in this evaluation. Analyze the problem against its domain using your own reasoning; end your response with exactly one line: VERDICT: VALID or VERDICT: INVALID.
--- validate_problem, tool arms (default) ---
You are a PDDL validation assistant. LLMs cannot reliably check PDDL syntax from training alone. Use the available validation tool to check the problem against its domain.
--- validate_problem, tool arms (neutral style, Study 2) ---
You are a PDDL validation assistant.

--- validate_plan, unaided arm ---
You are a PDDL validation assistant. PDDL validation tools are not available in this evaluation. Analyze whether the plan solves the problem using your own reasoning; end your response with exactly one line: VERDICT: VALID or VERDICT: INVALID.
--- validate_plan, tool arms (default) ---
You are a PDDL validation assistant. LLMs cannot reliably check plan correctness from training alone. Use the available validation tool to check whether the plan solves the problem.
--- validate_plan, tool arms (neutral style, Study 2) ---
You are a PDDL validation assistant.

--- simulate, unaided arm ---
You are a PDDL simulation assistant. PDDL simulation tools are not available in this evaluation. Trace the state transitions using your own reasoning; conform to the JSON schema provided by the format constraint (per-step state with boolean predicates and numeric fluents).
--- simulate, tool arms (default) ---
You are a PDDL simulation assistant. LLMs cannot reliably trace state transitions through a plan from training alone. Use the available simulation tool to compute the trajectory.
--- simulate, tool arms (neutral style, Study 2) ---
You are a PDDL simulation assistant.
\end{lstlisting}

\paragraph{Test data per domain.}
Table~\ref{tab:domain-sizes} gives the size of each domain. The classical domains are
barman, blocksworld, depots, rovers and satellite from the earlier dataset, and
gripper, miconic, parking, tpp and zenotravel from the \texttt{olam-compatible}
collection. The numeric domains are counters, depot, farmland, pogo\_stick and sailing
from the earlier dataset, and block-grouping, delivery, drone, gardening and
zenotravel-numeric from a public mirror of the numeric planning benchmarks.

\begin{table}[t]
\centering
\footnotesize
\begin{tabular}{@{}llrrrr@{}}
\toprule
\textbf{Domain} & \textbf{Track} & \textbf{Chars} & \textbf{Actions} & \textbf{Objects} & \textbf{Plan length} \\
\midrule
barman & classical & 5542 & 12 & 13--20 & 14--65 \\
blocksworld & classical & 1164 & 4 & 3--6 & 2--16 \\
depots & classical & 1521 & 5 & 9--24 & 5--22 \\
gripper & classical & 984 & 3 & 7--19 & 3--14 \\
miconic & classical & 1003 & 4 & 3--7 & 3--10 \\
parking & classical & 1852 & 4 & 6--10 & 3--7 \\
rovers & classical & 3967 & 9 & 11--19 & 12--34 \\
satellite & classical & 1717 & 5 & 9--21 & 6--15 \\
tpp & classical & 2279 & 4 & 8--18 & 13--36 \\
zenotravel & classical & 1579 & 5 & 12--18 & 4--10 \\
block-grouping & numeric & 1556 & 4 & 5--5 & 10--36 \\
counters & numeric & 1228 & 4 & 3--5 & 8--56 \\
delivery & numeric & 2185 & 5 & 13--22 & 14--46 \\
depot & numeric & 1819 & 5 & 9--21 & 5--62 \\
drone & numeric & 2701 & 8 & 2--18 & 5--110 \\
farmland & numeric & 686 & 2 & 4--15 & 3--19 \\
gardening & numeric & 3779 & 10 & 3--3 & 5--86 \\
pogo\_stick & numeric & 3330 & 7 & 35--35 & 10--23 \\
sailing & numeric & 1805 & 8 & 3--3 & 4--100 \\
zenotravel-numeric & numeric & 2215 & 5 & 4--7 & 3--14 \\
\bottomrule
\end{tabular}
\caption{Size of each test domain. Chars is the length of the valid domain file in
characters and Actions the number of action schemas. Objects and Plan length are the
range over the five valid problems, the plan length counted on the planner's plan.}
\label{tab:domain-sizes}
\end{table}
```

### B3 grounding

Code lines are at `main` `d57dd68` (this repo) and, for the plugins, at the sweep's pinned
marketplace commit `pddl-copilot` `2850bc4` unless marked "current". "Recount" means I
recomputed it today from `domains/` or the canonical corpus with a throwaway script.

| claim | backed by |
|---|---|
| seven tools, from two plugins, exposed in every tool trial | `run_experiment.py:123` (`REQUIRED_PLUGINS = ["pddl-solver", "pddl-validator"]`); `runner.py:406` (`allowed = None`); `chat.py:310-311` (`tools_payload = mcp.tools`); tool list at `2850bc4`: `solver_server.py` `classic_planner`, `numeric_planner`, `save_plan`; `validator_server.py` `validate_domain`, `validate_problem`, `validate_plan`, `get_state_transition` |
| same list on the frontier runs | `tools/frontier_runner.py:82-111` (wraps every `mcp.tools` entry) |
| validator tools run `pyval`, built on `unified-planning` | `validator_server.py:16` at `2850bc4` (`from pyval import PDDLValidator`; current `:20`); `plugins/pddl-validator/requirements.txt` (`pddl-pyvalidator>=0.1.5`); `pddl_pyvalidator-0.1.5` METADATA `Summary: Pure Python PDDL plan validator`, `Requires-Dist: unified-planning>=1.1.0`; `pyval/syntax_checker.py:5` (`PDDLReader`), `pyval/plan_simulator.py:7` (`UPSequentialSimulator`) |
| planners called through `unified-planning` | `solver_server.py:17-18` at `2850bc4` (`PDDLReader`, `OneshotPlanner`), `:239` `fast-downward`, `:275` `enhsp` (current `:24-25`, `:331`, `:443`, `:483`); `plugins/pddl-solver/requirements.txt` (`unified-planning`, `up-fast-downward`, `up-enhsp`) |
| wrong-tool calls occur | `scoring.py:572` (`FR_WRONG_TOOL`); recount: 36 `save_plan` calls in the three ≥9B think=off canonical tool cells; `reanalysis_breakdowns_cost.md` §4.4 item 11 (35B calls `validate_plan` on solve trials) |
| `verbose` hidden and fixed to false | `chat.py:82-110` (schema strip), `:156` (`"verbose": False`) |
| tools take text or a path | `validator_server.py:111` and `solver_server.py:280` (`_ensure_file`, current) |
| PDDL pasted, no paths | `runner.py:333-336` (`template.format(domain=..., problem=..., plan=...)`); `prompts.py:395-435` |
| every domain-argument call passed the text | recount over `sweep5v2-live` Qwen3.5-9B, Gemma, Qwen3.6-35B think=off tool cells: 27,185 calls carry `domain`, all PDDL text (3,722 start with the file's `;` comment header); 80 calls have no `domain`. Same totals as `reanalysis_breakdowns_cost.md` §4.4 item 14 |
| 20 domains, 10 + 10, 1,240 files; ten from the 2025 dataset | `domains/README.md:7-11`, `:38-47`; recount (20 / 20 / 100 / 100 / 500 / 500) |
| four hand-written numeric problems | `domains/README.md:11`, `:36` (zenotravel-numeric "hand-authored p02-p05") |
| valid plans from the planners; 99 of 100 problems have five copies | `tools/build_fixtures.py:375-399` (extra Fast Downward settings, then padding with copies); recount: 99 problems with five identical files, 101 distinct valid plans |
| invalid files kept only if `pyval` rejects; checked again at startup | `build_fixtures.py:475` (plans), `:539` (problems), `:591` (domains); `pddl_eval/domains.py:217`, `:267`, `:285`, `:312` (`SystemExit` on a label mismatch) |
| invalid domains 13 / 5 / 2; new domains got the first edit; old ones kept hand-made files | recount (parenthesis counts and `diff` per domain); generator order `build_fixtures.py:581-594`; hand-made files carried over by the migration at `build_fixtures.py:200-221`. **Differs from** `reanalysis_breakdowns_cost.md` §4.3 (see the correction at the top) |
| invalid problems 45 / 20 / 26 (13 with paren) / 9 | `reanalysis_breakdowns_cost.md` §4.3; my coarse recount gives the same split (45 content, 20 paren, 13 no goal, 13 no goal plus paren, 7 no objects, 2 no init) |
| invalid plans: names and arity legal; 290 / 110 / 74 / 17 / 9; 380 one step shorter | `build_fixtures.py:421-431`; `reanalysis_breakdowns_cost.md` §4.3; recount of length differences (380 at −1 of 500) |
| objects 2 to 35 (median 9); plan 2 to 110 (median 11.5); domain files 686 to 5,542 chars; per-domain table | recount; every per-domain row matches `reanalysis_breakdowns_cost.md` §4.3 |
| 4,560 per cell and the per-task split | tex 376-378; `runner.py:715-865` (job builder); `NUMBERS.md` "Corpus scale" (273,600 = 5 × 2 × 3 × 4,560 × 2) |
| validate_domain 100 valid to 20 invalid per wording; always-VALID scores 83% | `runner.py:738-784` (one positive job per problem), `:803-825` (one negative per domain); 100 / 120 = 83.3% |
| balanced accuracy reported for validate_domain | tex 1784 |
| 1,803 and 120 distinct prompts | `prompts.py:403-412` (validate_domain prompt holds only `{domain}`); (101 + 500) × 3 = 1,803; (20 + 20) × 3 = 120; `reanalysis_breakdowns_cost.md` §4 summary |
| simulate shows the planner's plan, whose trajectory is the key | `runner.py:750-758` (simulate keeps the oracle `gt`); `domains.py:182-196` |
| bin cut points | `.claude/skills/analyzer/scripts/rq_deck.py:482-515` (validate_plan bins use valid plans only, `:499-500`); `reanalysis_breakdowns_cost.md` §4.3 item 4 |
| prompt size about 1,000 to 10,100 characters | recount with `runner.build_messages`, v11, valid fixtures: 1,044 to 10,108 (medians 2,170 to 3,753 by task) |
| wordings: two instructions and one question on verdict tasks; three instructions on solve and simulate; only v12 solve asks one action per line | `prompts.py:395-435` |
| steering sentence placement, same for all three wordings | `prompts.py:306-363`; script check (passed); `reference/sweep_prompt_bank_design.md:332` |
| system message depends only on task and arm | `runner.py:337-348`; `prompts.py:82-174` |
| "prompt v11" = first plain wording | `prompts.py:180` (`ACTIVE_PROMPT_VARIANTS = (11, ..., 16)`), `:395-401` |
| prompt text unchanged since the sweep | `git diff b82f590 HEAD -- pddl_eval/prompts.py`: only the neutral system-message dict was added |
| frontier wordings | `frontier_runner.py:299-300`, `:561-562` (`--variant`); recount: Sonnet and Haiku tool runs 1,520 trials each, all v11; Haiku unaided 1,520, all v11; Sonnet unaided 4,560, 1,520 per wording |
| wording moves unaided success and the call rate | `NUMBERS.md` "Delivered rerun — descriptive secondary analyses", row "Gemma validate_plan invocation by wording" (31.0 / 25.1 / 3.9); `NUMBERS.md` "nt-ster H4", "Tex cross-check rows", row "F gate ranges" (solve 14.0–31.0, simulate 5.56–36.33) |
| frontier runs use the same message builder | `frontier_runner.py:135`; `tools/claude_api_batch.py:155` |
| frontier unaided format details | `tools/_claude_api_common.py:21-25` (simulate sentence), `:31-36` (solve schema), `:56-62`; `claude_api_batch.py:155-167` (`output_config`) |
| unaided format constraint did not take effect | tex 443-445 and 1754-1762 (PR #110) |

---

## B4. "By construction" and the checker

### B4.1 Oracle paragraph (replaces tex 328 to 334, from "Before any model is run, an oracle generates ground truth" to "returned plan is independently certified valid;")

The sentence the plan asks for is the fifth one below ("On the verdict tasks and
\emph{simulate} the checker is the tool, ..."). The no-call half, now only in the appendix
(tex 1878-1880), comes into the body in the sentence after it, as C2 asks.

The VAL sentences (filled in 2026-11-09, plan step C1, replacing the `TODO(C1)` comment)
follow the same-program sentence, because they test it. They state what VAL checked and
what it did not: plans only, never the domain and problem labels, never the simulate
trajectories. The open-model and the Claude plan checks are separate rows of `NUMBERS.md`
and are not pooled.

```latex
Before any model is run, an oracle makes the answer key by calling the same tools on
the original files. On the three verdict tasks the key is \texttt{pyval}'s verdict. On
\emph{simulate} it is the trajectory that \texttt{get\_state\_transition} returns for
the planner's plan. \emph{Solve} has no key plan, and a returned plan counts if
\texttt{pyval} accepts it for the original domain and problem. On the verdict tasks
and \emph{simulate} the checker is the tool, so the tool-verified outcome (defined
under Metrics) is correct by construction whenever the model calls the matching tool
on the unchanged task files. On every task a trial with no call fails at that layer by
construction. That layer therefore measures whether the model calls the right tool
with intact arguments, and it does not measure the tools' own accuracy. On
\emph{solve} the tool and the checker are different programs. Fast Downward or ENHSP
finds the plan and \texttt{pyval} checks it, although both read the PDDL through the
parser of \texttt{unified-planning}. On the other four tasks the tool and the answer
key are the same program, so a fault in \texttt{pyval} would go unseen on the tool
side and would count against an unaided answer that disagreed with it. We therefore
checked the plan side of the answer key with an outside validator, VAL
\citep{howey2004val}. VAL agrees with \texttt{pyval} on $1{,}731$ of $1{,}732$ plans
($99.94\%$, Wilson 95\% interval $[99.67, 99.99]$): all $1{,}000$ \emph{validate\_plan}
test plans and $731$ of the $732$ distinct \emph{solve} plans graded in the delivered
rerun. In the one disagreement \texttt{pyval} accepts \texttt{pick-up} for the action
\texttt{pick\_up}. A second check covers the $745$ \emph{solve} plans of the two Claude
models that both validators could read. VAL agrees on $734$ ($98.52\%$, $[97.38,
99.17]$), and on all $219$ plans of the tool arm. All $11$ disagreements are one fault
of \texttt{pyval}. When an unaided answer writes an upper-case name exactly as the test
file declares it, \texttt{pyval} rejects the plan, although PDDL names are
case-insensitive. This fault lowers a few unaided \emph{solve} grades. It also fails
some tool calls in which the model rewrote a plan with the file's capitals before
passing it to \texttt{validate\_plan} or \texttt{get\_state\_transition}. We report the
grades as stored and give the VAL grades beside them, labelled post hoc. VAL does not
confirm the rest of the key. On the domain and problem files it agrees with the labels
on only $184$ of $238$ ($77.3\%$). Every miss is an invalid file that VAL accepts,
because VAL ignores text after the \texttt{define} form and reads a missing goal as an
empty one. Those labels rest on a strict reading of the PDDL grammar. The
\emph{simulate} trajectories were not checked with VAL.
Grading is end-to-end and strict (Table~\ref{tab:tasks}): a \emph{solve} answer counts
only if \texttt{pyval} accepts the returned plan;
```

The paragraph then continues unchanged from "a \emph{simulate} answer counts only if its
entire trajectory equals the oracle's ...".

### B4.2 Table and three optional edits

| tex line | now | change to | required? |
|---|---|---|---|
| 353 | `solve & returned plan is certified valid (goal reached, all preconditions hold) \\` | `solve & \texttt{pyval} accepts the returned plan (every precondition holds and the goal is reached) \\` | yes (names the certifier) |
| 360 to 362 | "Each task has a single relevant, correct-by-construction tool per instance (\emph{solve} selects the classical or numeric planner)." | "Each task has one matching tool per instance (on \emph{solve}, the classical or the numeric planner)." | optional |
| 301 | "a suite of sound symbolic planners and validators" | "a suite of symbolic planners and validators" | optional (C8 objects to calling the validator "sound" with no independent check) |
| after 523 ("whatever the final message then said.") | (nothing) | "Because the answer key comes from the same tools, this layer mostly records whether the model called the matching tool with intact arguments (Tasks, Oracle, and Fixtures)." | optional |

### B4 grounding

| claim | backed by |
|---|---|
| the oracle calls the same tools on the original files | `pddl_eval/domains.py:174-200` (`_validate_capture` for domain and problem, planner call `:182`, `get_state_transition` `:193`, plan check `:199`); `_validate_capture` routes to the three validator tools at `:112-133` |
| verdict-task key is `pyval`'s verdict | `domains.py:112-133`; validator tools run `pyval` (B3 grounding) |
| simulate key is `get_state_transition` on the planner's plan | `domains.py:182-196`; `scoring.py:596-598` (`oracle_trace`, `oracle_canon`) |
| solve has no key plan; it counts if `pyval` accepts the plan for the original files | `scoring.py:500-545`: the planner's plan goes to `_validate_model_plan` (`:515`) with the harness's own `domain_pddl` and `problem_pddl`; `_validate_model_plan` calls `validate_plan` (`:409-433`); unaided and delivered answers use the same call (`:533`; `tools/e2e_regrade.py:69-72`) |
| tool-verified on the verdict tasks compares the tool's verdict on the model's arguments with the key | `scoring.py:547-575` (`:566` `if verdict == truth`) |
| tool-verified on simulate compares the tool's trajectory with the key | `scoring.py:591-617` (`:613`) |
| no call fails at that layer | `scoring.py:497-498` (`if with_tools and not tool_calls: return False, False, FR_TOOL_NOT_SELECTED`); tex appendix 1878-1880; `NUMBERS.md` "Study 1" block, note under the T2 table ("0 successes without a call in all 30 cells", merged in PR #121) |
| "on the unchanged task files" is needed | tex `tab:decomp` 1865-1871: P(correct given a call) is 92.6 to 99.4, so calls do fail; `development/CHANGELOG.md:1158` (an audit found the model had edited the plan before passing it to the tool) |
| solve: two programs, one shared parser | planner side `solver_server.py:17-18`, `:239`, `:275` at `2850bc4`; checker side `pyval/syntax_checker.py:5`, `pyval/plan_simulator.py:7` |
| not "checked by VAL" | `reference/weakness_consolidated.md` D1; `weakness_action_plan.md` §5 row D1; `paper_notes_discussions.md:49` |
| the same-program limit on four tasks | C8; negatives accepted only on `pyval` rejection (`build_fixtures.py:475`, `:539`, `:591`) |
| VAL agrees on 1,731 of 1,732 plans (99.94%, Wilson 95% [99.67, 99.99]); all 1,000 validate_plan test plans; 731 of 732 distinct solve plans of the delivered rerun | `NUMBERS.md` "VAL cross-check of the answer key (C1)", row "plans, VAL vs the answer key"; method in `reference/val_crosscheck.md`, script `tools/val_crosscheck.py`. Scope: 10 more plans crash VAL and are not counted (pyval rejects all 10). Do not write "100% agreement" or pool these plans with the files |
| the one disagreement is `pick-up` read as `pick_up` | `NUMBERS.md` C1 block, row "the one disagreement" |
| 745 Claude solve plans; VAL agrees on 734 (98.52%, [97.38, 99.17]); tool arm 219 of 219 | `NUMBERS.md` "Added 2026-11-09: VAL on the Claude solve plans" (PR #125, generated by `tools/reanalysis/val_frontier_solve.py`), first row. Scope: Sonnet 4.6 and Haiku 4.5, unaided and tool arm, canonical and renamed; 771 distinct graded plans, of which 21 answers hold no plan and 5 plans crash VAL, so 745 have a verdict from both. Never pooled with the C1 plans |
| all 11 disagreements are one case fault, unaided canonical answers only | same block, row "the disagreements"; `OPEN_ISSUES.md` ISS-027 |
| the fault also fails some tool calls on plans rewritten in the file's capitals | `OPEN_ISSUES.md` ISS-027, "Scope", item "Tool arms" (no figure quoted here; the post hoc figures are in draft PR #130 and are not on `main` yet) |
| stored grades kept, VAL grades beside them, post hoc | frozen-corpus rule (`CLAUDE.md`, `handoff_20261109.md` §1); `NUMBERS.md` same block, rows 3 and 4 ("do NOT quote": a corrected figure in place of the frozen one). Answer list item 22 |
| files: 184 of 238 (77.3%); every miss an invalid file VAL accepts (stray `)` after the define, missing `:goal`) | `NUMBERS.md` C1 block, row "domain and problem files, parse check" ("do NOT quote: validate_domain / validate_problem labels checked by VAL"); `reference/val_crosscheck.md` bottom line (2 more problem files crash VAL and are not counted) |
| simulate trajectories not checked with VAL | `reference/val_crosscheck.md`, "What this means for the paper" ("Simulate is not covered by this check") |
| VAL is cited as `howey2004val` | already in `paper/refs.bib` and the tex (line 202) |

B4 had no numbers until the VAL sentences were added on 2026-11-09. Every number in them is
in the rows above; the two Wilson intervals were recomputed from the counts and match.

---

## B5. The two claims that go

### Every occurrence

| # | tex lines | text now | action |
|---|---|---|---|
| 1 | 1339-1341 at `d57dd68`; **gone** at `130193e` | `$^\dagger$\emph{solve} stays near its unaided floor, so it proves the capability boundary at the frontier but carries limited contamination headroom.` (caption of `tab:frontier`) | done by PR #123: the quoted text no longer exists. The caption's dagger note is now tex 1360-1362 ("The \emph{solve} totals agree, but single domains move in both directions ...") and needs no B5 edit (B5.1) |
| 2 | 1675-1679 | "Third, our results are direct empirical support for the LLM-Modulo thesis \citep{kambhampati2024llmmodulo} that LLMs should be paired with sound external verifiers, and a refinement of it: the pairing pays off only when the orchestration actually routes work to the verifier, and naive availability does not guarantee that routing." | replace (B5.2) |
| 3 | 1679-1683 | "The \emph{solve} boundary is not an artifact of our open-weight roster's scale: ... so the necessity of an external solver reflects a capability boundary rather than the limited scale of the models we tested." | replace; this is the body form of claim 1 (C18 quotes it) (B5.2) |
| 4 | 1684-1689 | "... so the simulator's necessity is a matter of degree rather than an absolute boundary; the tool's verified work on that task (...) moreover largely fails to reach" | adjust, because it leans on the boundary sentence (B5.2) |
| 5 | 215-217 | "The present study is empirical evidence for exactly this division of labour: we measure what an LLM gains when a sound planner or validator is available as a callable tool, rather than asking the model to be the planner." | replace; same claim as 2 in the Background. B1 is rewriting this section, so this one may go with B1 (B5.3) |

A grep for "LLM-Modulo", "Modulo", "boundary", "thesis", "necessity" and "prove" finds no
other occurrence. Line 119 cites LLM-Modulo only for "known to be unreliable" and stays.

### B5.1 Table caption (was tex 1339-1341 at `d57dd68`; now tex 1360-1362, already rewritten)

> **Superseded 2026-11-08.** The contamination-wording PR rewrites this whole note: the
> boundary clause goes, and so does "limited contamination headroom" (solve at 28.7% is
> not a floor, and its paired interval is the widest of the four exact tasks). Row 1 of the
> table above needs no further edit; rows 2 to 5 stand.

Minimal deletion; the rest of the note is the author's contamination point and is left.

```latex
$^\dagger$\emph{solve} stays near its unaided floor, so it carries limited contamination
headroom.
```

### B5.2 Discussion (replaces tex 1675 from "Third, our results are direct empirical" through 1689 "moreover largely fails to reach")

```latex
Third, the results bear on the LLM-Modulo proposal \citep{kambhampati2024llmmodulo},
which pairs an LLM with sound external verifiers. We tested a narrower arrangement, in
which the model makes one decision, whether to hand the task to a sound tool, and no
generate-and-test loop runs. In that arrangement, making the tool available did not
ensure that the model used it, and how often a model called the tool varied widely
across models and prompts. Routing the work to the tool is therefore a condition of
its own. The low unaided \emph{solve} rate is not limited to the open-weight roster.
Claude Sonnet 4.6 also solves fewer than a third of problems unaided ($28.7\%$;
Table~\ref{tab:frontier}), measured with extended thinking off and the same
$8{,}192$-token output cap. That result describes this setting and leaves open what
extended thinking or a larger output budget would reach. \emph{Simulate} behaves
differently. Once format and budget pressures are removed, unaided state tracking
appears at $\geq$4B ($22$--$40\%$ in the budget-decoupled control) and reaches
\cbnd{41.7}{61.3} at the frontier, so models can do part of this task without the
simulator. The tool's verified work on that task ($97$--$99\%$ at the mechanism layer)
also largely fails to reach
```

The sentence then continues unchanged ("the delivered answer, so the simulator is accurate
and what it lacks is a delivery path. ..."). That clause and the rest of the paragraph are
E5's to rescope, not B5's.

### B5.3 Background (replaces tex 215 "The present study is empirical evidence for" through 217 "rather than asking the model to be the planner.")

```latex
In our setting the model decides whether to hand the whole task to a sound planner or
validator, and no generate-and-test loop runs. We measure what that hand-off gains.
```

### B5 grounding

| claim | backed by |
|---|---|
| Sonnet 4.6 unaided solve 28.7% | `NUMBERS.md` "Abstract — the four figures", row "frontier plan generation" (Sonnet 86/300 = 28.7); recount of `results/sonnet-frontier/sweep5v2/trials.jsonl`: 86 of 300. **Caveat (2026-11-09):** this is the stored grade, which the pyval case fault (ISS-027) lowers; under VAL it reads 32.7% (post hoc, `NUMBERS.md` "VAL on the Claude solve plans", row 3), still under a third, so the sentence holds. The frozen 28.7 stays in the sentence; answer list item 22 asks how to show the VAL reading |
| thinking off, 8,192-token cap on the frontier unaided solve | `tools/claude_api_batch.py:37-39` (no `thinking` parameter; `max_tokens` = the per-task cap), `:161`; `runner.py:100-101` (solve 8,192); recount: the two truncated Sonnet solve answers stop at exactly 8,192 output tokens |
| one decision, no generate-and-test loop | design of every arm (`chat.py:278-367`: the model may call tools, nothing re-prompts it with a critique); C18 ("no generate-and-verify loop is tested") |
| call rate varies widely across models and prompts | `NUMBERS.md` "Abstract", row "invocation on plan checking" (Gemma 21% plain, 94% steered); tex `tab:decomp` 1865-1869 (plain-arm call rate 20.7 Gemma, 82.9 Qwen3.6-35B, 97.9 Qwen3.5-9B); `NUMBERS.md` rerun secondary row "invocation by wording" (31.0 / 25.1 / 3.9). The C2 work is adding a "Study 1" block to `NUMBERS.md` (uncommitted today); once it lands, cite its T2 table here and for B4's no-call sentence ("0 successes without a call in all 30 cells"). *Landed (PR #121):* `NUMBERS.md` "Study 1" block, row "Gemma validate_plan calling" and the T2 table with its note; now cited in the B4 grounding |
| simulate 22–40% decoupled control | `NUMBERS.md` "Job 2" block, row "open-roster unaided simulate" |
| simulate ⟨41.7, 61.3⟩ Sonnet unaided | `NUMBERS.md` "Frontier e2e", row "simulate, no-tools" |
| 97–99% mechanism layer (unchanged text) | `NUMBERS.md` "Abstract", row "delivery gap" (Sonnet 99, Haiku 97) |

Not used in the LaTeX, offered in answer list item 19: of Sonnet's 214 failed unaided solve trials,
205 are plans `pyval` rejects, 7 are plans the validator could not process and 2 hit the
output cap (recount, `failure_reason` in the same file). Most of its failures are wrong plans.

---

## Things noticed in passing (not changed here)

1. `tools/build_fixtures.py:323-331` and `:379-386` pass an argument named `search` to
   `classic_planner`. The planner's parameter has been `strategy` since `pddl-copilot`
   `6afd6da` (2026-03-27), before the fixtures were built (2026-04-29, `b7960da`). That is
   very likely why 99 of 100 problems have five copies of one valid plan. D1b ("distinct
   valid plans") uses the same builder and should fix this first.
2. Tex 503-505 says argument errors are "largely structural, so the steered contrast isolates
   selection rather than parameter construction". With the PDDL pasted into the prompt, the
   model copies a few thousand characters into each call, and P(correct given a call) is
   92.6 to 99.4 (`tab:decomp`). E2 should revisit that sentence.
3. Tex 1804-1808 (Future Work) calls the with-tools arm on proprietary models an open
   question. The frontier tool arm exists, and both tiers call the tool on every trial
   (`NUMBERS.md` "Job 2", "frontier CALL rate"). For E5.
4. The frontier unaided arm is not prompt-identical to the open models (solve through the
   provider's structured-output parameter, simulate with one extra sentence). The tex does
   not say this. B3.4 now states it. It matters for C6 and E4.
5. The default solve system message cites "arXiv:2509.12987". The appendix shows it
   verbatim (answer list item 17).
6. C18's other claims ("law", "survives reasoning mode", "a single imperative sentence
   sufficed", "neither is capability or tool accuracy") are left
   for E5, as the plan says. Where they are at `130193e` (re-checked 2026-11-09): "neither
   is capability or tool accuracy" at tex 1830 to 1831; "survives reasoning mode" at 1833
   to 1834, now reworded by PR #123 ("Both survive reasoning mode, and the
   anonymized-domain control detects no memorization effect ..."); "a single imperative
   sentence sufficed" at 1839. The old anchor "1819-1821" did not hold even at `d57dd68`
   (those phrases were at 1808 to 1817 there). The word "law" is not in the tex at either
   commit, so that claim cannot be located.

---

## Proposed `NUMBERS.md` block (answer list item 13)

```markdown
## Test data (fixtures) — counts quoted in Methods (added 2026-10-XX)

Provenance: `reference/reanalysis_breakdowns_cost.md` §4, rechecked against `domains/` on
2026-10-27 (one correction, row 3). Fixture facts, not experiment results.

| figure | **quote this** | do NOT quote |
|---|---|---|
| inventory | **20** domains (10 classical, 10 numeric), **1,240** files: per domain 1 + 1 domain files, 5 + 5 problems, 25 + 25 plans | — |
| valid plans | **99 of 100** problems have five identical valid plan files; **101** distinct valid plans in 500 | "five distinct valid plans per problem" |
| invalid domains | **13** unbalanced parenthesis only (10 extra, 3 missing) · **5** undeclared predicate · **2** hyphen dropped | 12 by parenthesis and 1 ":predicates removed" (§4.3 misread block-grouping) |
| invalid problems | **45** undeclared object or predicate · **20** unbalanced parenthesis · **26** no goal (13 with an extra parenthesis) · **9** no objects or no init block | — |
| invalid plans | steps deleted **400** (290 middle, 110 end) · arguments swapped **74** · step repeated **17** · hand-made **9**; **380 of 500** exactly one step shorter | — |
| sizes | objects **2–35** (median 9); reference plan **2–110** steps (median 11.5); domain file **686–5,542** characters; prompt with system message **about 1,000–10,100** characters (v11) | — |
| validate_domain balance | **100 valid to 20 invalid** per wording; always-VALID scores **83%** | — |
| distinct prompts per arm | validate_plan **1,803 of 3,000**; validate_domain **120 of 360** | — |
| difficulty bins | length ≤ 8 / 9–19 / > 19 steps (validate_plan: valid plans only); objects ≤ 6 / 7–14 / > 14 (validate_problem ≤ 5 / 6–13 / > 13) | — |
| tool-call arguments | every call with a domain argument passed PDDL text (**27,185** calls, ≥9B think=off canonical tool cells) | — |
| frontier wordings | tool runs **v11 only** (both tiers); Haiku unaided **v11 only**; Sonnet unaided **v11–v13** | — |
```

---

## Open questions for Omer

The nine questions that were here moved on 2026-11-09 into the "Answer list for Omer" at
the top of this file. They are items 13 to 21 there, in the same order and with the same
wording, each with a recommendation and an answer slot. None had been answered when they
moved.
