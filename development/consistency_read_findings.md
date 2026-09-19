# Whole-paper consistency read — findings (2026-09-19)

*N3 item from `STATUS.md`. Read of `paper/main.tex` at `3196112` (after PR #107).
Nothing in the tex was changed. Line numbers are for that commit. Every quote below was
re-checked against the file. Answer in the `> ANSWER:` slots; I edit only what you
approve, on one `paper/` branch, after `/verify-claims` for anything that touches a
number.*

**Short version.** Terminology is mostly clean ("propensity" 0, prose em-dashes 0). The
read found **nine places where the paper contradicts itself**, most of them inside the
Job 2 (delivered reframe) and Job 3 (steering control) text, **four leftover synonyms**
for "invocation rate", **one caption promise that is not kept** (Wilson intervals "in the
text"), and a cluster of "X, not Y" closers in the Job 2 prose.

---

## A. The paper contradicts itself (most important first)

| # | Lines | What the tex says | Why it is a problem | Smallest fix |
|---|---|---|---|---|
| A1 | 1163–64 vs 955–60 | "delivered successes are a subset of tool-verified ones" | The delivery-gap section shows the opposite case: Gemma delivers ⟨30.0, 63.1⟩ with 0.9% tool-verified, because it answers in prose without calling | drop the "since … subset" clause, or limit it to trials that call the tool |
| A2 | 809 vs 694 | Figure caption: "Sole-source tasks on the delivered surface" | How-to-read footnote (iii) says no sole-source claim is made for simulate at the delivered level, and the same figure shows unaided frontier simulate at ⟨34, 53⟩ | retitle the caption without "sole-source" |
| A3 | 1202–03 vs scorecard | think=on "reproduces the verdict pattern (YES/YES/MIXED/YES, RQ5 YES, RQ6 NO)" | The scorecard now reads RQ3 "UNDECIDED (delivered); MIXED (mechanism)" and RQ4 "NO as deployed". There is no think=off pattern with RQ4 = YES left to reproduce | say it reproduces the *mechanism-layer* pattern, or restate per RQ |
| A4 | 2146–47 vs 860–66 | Appendix: the open roster's 0% unaided simulate "is not a formatting artifact" | The body says that same zero is mostly unparseable output and 0% wrapper compliance | "not an artifact of predicate notation in the grader" (which is what the normal form rules out) |
| A5 | 571, 852, 1120–21, 1218 | unqualified simulate zero ("0/3,000", "rule-of-three ≤0.1%", "stays floored at 0", "simulate sole-source") | The zero is format-exact on the shared-budget corpus, and the paper reports 22–40% content-correct elsewhere. **Line 571 was fixed 09-19** ("0/3,000 format-exact on the shared-budget corpus", your go); 852 was already qualified; 1120–21 and 1218 are still bare | same qualifier at the two remaining sites |
| A6 | 850 vs `tab:ster-tasks` (1991–2015) | body: unaided simulate 0%. Appendix table, same arm and task: 10.9–28.0% (off), 32.5–45.8% (on) | Different grader and storage, but no sentence says so | one caption clause: anchor simulate uses the delivered grader at 16K storage, not comparable to the format-exact 0% |
| A7 | 536 vs `tab:ster-tasks` | "indeterminate" | Two meanings: a censored trial (Metrics) and an equivalence outcome whose interval crosses the margin (appendix). The body already says "unresolved" for the second | relabel the appendix column "unresolved" (also matches your equivalence-wording rule) |
| A8 | 738 vs 770, 831; 618 | solve called "sole-source (no unaided success)" | Its unaided rate is 8–11% (22–29% frontier). Line 618 defines sole-source as "baseline at 0" | define it as "essentially no unaided success as deployed", or stop calling solve sole-source |
| A9 | 1940–41 | appendix: "eight eligible task cells are equivalent" | The body says "met the ±5 pp equivalence criterion" | match the body wording |

> ANSWER (fix all with the smallest fix / list the ones to skip or word differently):
>

## B. Leftover synonyms and naming (mechanical)

| # | Lines | Now | Proposed |
|---|---|---|---|
| B1 | 848 | "is invocation frequency" | "the invocation rate" |
| B2 | 1035 + figure axis/title (`make_paper_figures.py` 419, 446) | "tool-use rate" | "invocation rate"; needs the figure regenerated, so caption and figure change together |
| B3 | 1098 | "tracks tool-use almost 1:1" | "tracks invocation" |
| B4 | 1103 | "spontaneous tool adoption" | "spontaneous invocation" |
| B5 | 1285 | "the delivery-gap law" (used once, never defined) | "the delivery-gap pattern" |
| B6 | 1642 vs 415–17 | "sampling" means fixture sampling in one place and decoding randomness in the other | 1642: "not decoding variance" |
| B7 | 873, 870, 692, 1241, 783 | one corpus, four names: main corpus / main sweep / shared-budget corpus / canonical corpus | "canonical" everywhere, gloss "shared-budget" once |
| B8 | 1410, 1502, 1508, 1533, 1435, 1516 | standard Blocksworld called plain / clean / familiar / standard | "standard" |
| B9 | 772, 837, 1252, 1566 | open-roster / open-weight roster / open roster / open models | "open-weight roster", adjective "open-roster" (low priority) |
| B10 | 1932–34 | "in every unit" written twice in one sentence | merge |

> ANSWER (apply all / list exceptions):
>

## C. Notation gate (bounds ⟨a, b⟩ vs intervals [a, b])

Good news first: every censoring bound uses `\cbnd`, every interval uses square
brackets, and the captions of the newest tables and figures say which is which.

| # | Lines | Problem | Smallest fix |
|---|---|---|---|
| C1 | 981–82 | caption of the frontier delivery-gap table: "every other cell is exact (Wilson 95% intervals in the text)". **The text gives no interval for any of those cells** | add the intervals to the text, or drop the clause |
| C2 | 136, 554 | "confidence interval on every proportion" / "Every reported proportion carries a Wilson 95%" while most Results proportions print bare | soften to "computed for every proportion", or add intervals at headline sites |
| C3 | 1565 | ⟨49, 64⟩ "at the frontier" merges Sonnet's low end with Haiku's high end; Metrics defines a bound per cell | print both cells |
| C4 | 768 | "(≥92.2 vs 65.7)" is a third way to write a bound | `\cbnd{92.2}{95.3}`, as at line 992 |
| C5 | 785 vs 1281 | ⟨49,62⟩/⟨52,64⟩ in one place, reversed order in the other, neither labeled | label Sonnet/Haiku, keep one order |
| C6 | 1174 vs 1135, 1168 | `\cbnd` used for a token cost once, dash ranges for the same kind of quantity elsewhere | pick one; if `\cbnd` stays for costs, say so once |
| C7 | 1866–68, 1296–1300 vs 667, 1321 | contamination table prints simulate Δ "+0.0" as exact, while how-to-read row 1 calls that cell a bound and `tab:frontier` prints "---" | footnote: this column is the format-exact grade, or print "---" |
| C8 | 1011 vs 1837 | ⟨100, 100⟩ vs ⟨100.0, 100.0⟩ | align precision |

> ANSWER (apply all / list exceptions; for C1 and C2 say "add intervals" or "soften"):
>

## D. One number at two values (flag only, needs `/verify-claims` before any edit)

| # | Lines | What differs | What I already know |
|---|---|---|---|
| D1 | 824 vs 784, 1255, 1282, 1619, 1647 | Sonnet unaided simulate ⟨34, 53⟩ in the figure caption, ⟨41.7, 61.3⟩ everywhere else | both are frozen in `NUMBERS.md`: the first is the prompt-v11 slice (n=100), the second is full N (n=300). The tex never says which is which, and line 1281 compares v11 with-tools bounds against the full-N cell. Needs a label, not a new number |
| D2 | 822 vs 1566 (and 953) | rerun simulate "at most ⟨6, 21⟩ delivered" vs "open models deliver at most 17%" | **confirmed inconsistent.** The worknote (§ line 320) has Gemma at ⟨6.0, 20.7⟩. Line 953 lists 4B/9B/35B and leaves Gemma out; line 1566's "17%" is the 9B high end and ignores Gemma's 20.7 |
| D3 | 1749–50 vs 974 | "verified at 97–99% … delivered at half that or less" | Haiku is ⟨52, 64⟩ against 97, and half of 97 is 48.5, so "half or less" fails even at the low end |
| D4 | 821 vs 954 | rerun mechanism layer "44–94% per cell" vs "63, 83, and 92%" | probably different arm/model coverage (Gemma and steered arms), but the text does not say |
| D5 | 1163 vs 1135, 1180 | "delivered cost-of-pass can only be equal or costlier" vs validation delivered 2.8–5.2× against mechanism ≈3–5× | the low end contradicts the claim, possibly rounding. Tied to A1 (same sentence) |
| — | 1540 vs 1394 | our stripped regrade "26 of 600, 4.3% [3.0, 6.3]" equals the published GPT-4 Mystery cell exactly | **false alarm.** Both are frozen in `NUMBERS.md` (rows "GPT-4 reference line" and "matched-NT stripped-block regrade"). A real coincidence. Optional: add "coincidentally equal" so a reviewer does not suspect a copy error |

> ANSWER (verify and fix D1–D5 / list exceptions; "coincidentally equal" yes or no):
>

## E. AI-writing tells

About 75 hits were judged fine in context (plain "rather than" contrasts, technical
scoping, data-driven triads). These are the ones that do read as tells:

| # | Lines | Tell | Smallest fix |
|---|---|---|---|
| E1 | 959 and 1074–75 | the sentence "Not calling is not the same as not answering" appears **twice, word for word** | keep one |
| E2 | 1575, 1624–25, 1759 | three "the rule follows" reveals; the same rule is stated twice in Discussion and once in the Conclusion | keep one in Discussion |
| E3 | 861, 874, 929–30, 1261–62, 1691 | five "X, not Y" closers, all in Job 2 text; the density is the tell | recast two or three as positive statements |
| E4 | 1005, 1583–85, 1623–24 | "not X but Y" reversals | recast one or two |
| E5 | 843–44 | colon reveal of one word ("…: invocation.") | fold into the sentence |
| E6 | 1592–94 | rhetorical question pair ("can the model plan?" → "will the model delegate?") | state it plainly |
| E7 | 877, 1246 | "honest" as an intensifier, twice | drop both |
| E8 | 1048, 910–11, 584, 1601, 1078, 1279 | "dramatic", "sharp", "real weight", "a real caution", "huge", "enormous" next to exact numbers | delete the adjective |
| E9 | 1283 | "and dies in delivery" | "is lost in delivery" |
| E10 | 123, 1409, 906–07, 134, 263 | filler openers and promises ("Two things stand out.", "That is the gap we close.") | trim |
| E11 | 532–33, 693, 1124–25, 1762–63 | milder cases of the same patterns | optional |

These are prose changes, so I will not touch any of them without a yes. If you approve
some, I will show you each reworded sentence next to the original before committing.

> ANSWER (which rows; "show me drafts first" is the default):
>

## F. June-review candidates — where each would attach (candidates only, nothing drafted)

- **Structural-contamination clause:** Methodology, Contamination Control, after line 626 (renaming is surface-only), or the Limitations sentence on the 20-domain suite (1654–57).
- **Steering-phrasing Future Work sentence:** Future Work, before line 1723; pairs with 380–81 (the directive is held byte-identical).
- **Temperature Future Work sentence:** Future Work, after line 1727; Limitations 1642 already says higher temperatures are untested and Future Work has no counterpart.
- **Classical-vs-numeric cost split:** "What the Tool Costs", after the solve cost-of-pass sentence (1165–69), or an appendix table beside `tab:decomp`. Needs a new computation.
- **Symbol-map appendix:** new Technical Appendix paragraph after "Per-task contamination" (1851–76), referenced from line 626.

> ANSWER (which, if any, to draft):
>
