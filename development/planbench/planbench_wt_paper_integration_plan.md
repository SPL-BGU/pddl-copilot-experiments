# PlanBench → paper integration plan (Act 4, SECONDARY claim) — draft 2026-08-06

**Status: PLAN ONLY — no tex has been touched.** Prose starts only after (1) Omer
signs the slots below, (2) PR #93 merges to main. Paper edits then go on
`paper/aaai27` exclusively, with `sync_overleaf.sh pull` (+ commit) before any push,
and `/verify-claims` before any literature number enters the tex.

Sources of truth: `planbench_wt_results_20260803.md` (all internal numbers, verified
against graded corpora 2026-08-06), `planbench_wt_prereg.md` §1/§4/amendments I+M+N,
`journal_decisions_memo.md` §2 (Figure-1 spec) + §4 (D-J3 ANSWER).

## 1. The claim being integrated (fixed by prereg, not open)

- Act 4's **headline is the NT layer** (already graded 06-22 + n=600 completion):
  honest re-measurement on the field's instrument; Haiku bare-NT clean 43.8 sits
  CI-disjoint above the GPT-4 reference 34.3 at the shared n=600 denominator;
  Mystery collapse replicates (0.7%).
- The WT arm carries the **explicitly labelled SECONDARY claim**: the funnel
  replicates when the model operates the prescribed remedy on the field's
  instrument. Never Act 4's headline, never compared to GPT-4.
- Wording per amendment I: the bare "tools rescue Mystery" result is already
  published (Huang & Zhang ACL 2025); ours is a **replication with an ablation the
  field has not run** — matched-scaffold control + directive-only rung, VAL grading
  on canonical instances, Wilson CIs + paired exact tests, the
  formalization-boundary metric, delegation mediator, measured $/trial. The prose
  must say so.

## 2. Where it goes

The current `paper/main.tex` has **no PlanBench results section** — PlanBench
appears only in citations and as a Future Work promise (L1076-77). The journal
Act restructure is accepted (07-24 slots) but not yet executed in tex.

**Recommendation: Option A.** Write the section now as a new self-contained
top-level section, "External validity on PlanBench" (working title), inserted
**between Results and Discussion** in the current tex. The journal memo fixes Act
4's internal structure regardless of where it sits (shrink-not-scatter), so this
section lifts unchanged into the Act restructure later; waiting (Option B) leaves
the arm's freshest material out of the living draft with nothing gained.

> ANSWER (placement: A = new section now / B = wait for Act restructure):
>A

## 3. Section skeleton, tables, figures

Presentation rules that bind throughout: WT cells never share a table or figure
with GPT-4 rows (prereg rule 5); every external number prints pool size + grader on
the same line (amendment M); GPT-4 is a labelled published reference line,
descriptive CI-separation language only, no tests against it.

1. **Opening paragraph** — what PlanBench is, the Mystery construction (pure symbol
   rename, verified 501/501 on disk), why it is the right external instrument, and
   the headline/secondary split stated up front.
2. **Table PB-A (NT re-measurement, carries the headline).** Rows: Haiku bare-NT
   clean 263/600 = 43.8 [39.9, 47.8]; Haiku bare-NT Mystery 4/600 = 0.7 [0.3, 1.7];
   GPT-4 clean 206/600 = 34.3 [30.6, 38.2] (published responses, published grader
   epoch, n=600); GPT-4 Mystery (Deceptive) 26/600 = 4.3, one-shot NL, verified
   against the paper (§5). No WT cells.
3. **Table/Figure PB-B (the WT 2×2, the SECONDARY claim).** Within-Haiku paired
   deltas only, n=600/cell, one Rosetta-VAL epoch. Clean WT is quoted FIRST-DRAW
   (decision 2026-08-06, Omer: the ~1pp is not worth the best-of-2 ambiguity from
   the 18 resume re-draws — results doc deviation 1; all 18 first draws are
   loop-exhausted empty answers, so first-draw = re-draws counted as failures):
   clean WT **410/600 = 68.3 [64.5, 71.9]** vs matched-NT 47.8 [43.9, 51.8],
   paired Δ **+20.5pp**, exact McNemar b=202 / c=79, **p = 1.4e-13** (recomputed
   2026-08-06 from the raw side-log by an independent script; both anchors
   410/418 reproduced, b/c shifts decompose exactly). The last-attempt reading
   69.7 [65.9, 73.2] / +21.8pp / p = 2.7e-15 lives only in the deviation
   footnote, never as the quoted number. Mystery WT 71.8 [68.1, 75.3] vs
   matched-NT 0.0 [0.0, 0.6], p = 3.6e-130 — one record per instance, no
   re-draws, unchanged. Clean-vs-Mystery WT paired Δ under first-draw = 3.5pp
   (Mystery above clean; b=119 / c=140, p = 0.214; last-attempt ≈2.2pp same
   direction) — inside the pre-registered ±7.5pp margin either way. No GPT-4
   column.
4. **Table PB-C (amendment N ladder, Mystery t1, n=600/rung):** native 0.7 /
   scaffold-only 0.0 / directive-only 0.5 / scaffold+tools 71.8 — the directive
   alone moves nothing; the contrast is tool availability. Proposed home: main
   body (it is the ablation the field has not run — burying it undercuts the
   novelty sentence). Appendix is the fallback if the section runs long.

> ANSWER (ladder placement: body / appendix):
>body

5. **Mechanism paragraph (formalization_match, prereg §4).** clean 96.3
   [94.5, 97.6] / Mystery 97.8 [96.3, 98.7] — the RESCUE branch requirement met;
   P(solvable | domain-equivalent PDDL) = 99.5% vs 1.6% otherwise; 0/35 no-match
   trials correct; delegation 100% in both WT cells. Reading: the collapse never
   was search, and formalization is semantics-blind transcription, so it survives
   obfuscation.
6. **Funnel figure amendment (prereg §4 ANSWER).** The PlanBench cascade gains
   **FORMALIZE as a new leading bar**: trials → FORMALIZE → CALL → tool result
   correct → delivered correct; four bars for PlanBench, three for our suite; NEED
   stays a reference line drawn from the no-tools arm, never a bar. FORMALIZE is
   declared an instrument property — absent by construction where prompts embed
   the PDDL (our own suite). One-line question: *can the model state the problem
   in the tool's language?*
7. **Audit/robustness paragraph.** Report the graded Mystery matched-NT 0.0
   [0.0, 0.6] with the narration-injection caveat (479/600 injected), then the
   stripped-block regrade as the instrument-robust reading: 26/600 = 4.3
   [3.0, 6.3], with the paired contrast surviving at p = 6.4e-112 (b=412, c=7).
   Per the signed slot both layers are reported; the injection depressed the NT
   cell, so the bias ran against the published 0.0, not in its favor. Also owned
   here: Mystery WT dialect losses 125/569 (bias against tools; no correction
   applied), loop exhaustion 10.5%/5.2% counted as delivered failures
   (treatment-policy).

> ANSWER (confirm the two-layer NT presentation: graded 0.0 + stripped 4.3 as
> robustness, per the signed audit-2 slot): confirmed-approved
>

8. **Cost sentence.** Measured, not estimated: confirmatory 2×2 $39.87; directive
   rung $2.61; bare-NT completion ≈$1.5; arm cumulative ≈$46.2. Per-trial cost
   printed alongside the claim (harness-eval convention).
9. **Limitation sentence.** Single-tier (Haiku only) owned explicitly; Sonnet
   extension pre-registered as future work, out of budget.

## 4. Edits to existing tex (small, all on paper/aaai27 after merge)

- **Future Work** (main.tex L1076-77): the PlanBench extension promise is now
  delivered — rewrite to point at the new section; keep the open-roster v2 cluster
  arm as the remaining future item (per D-J3 demotion).
- **Positioning / Related Work**: one sentence anchoring Huang & Zhang as the
  published rescue result we replicate-with-ablation; La Malfa arXiv:2512.09629 as
  closest agentic competitor. Both enter only after `/verify-claims`.
- **Limitations**: fold in the single-tier ownership if not already implied.
- No edits to Results/Methodology sections of the existing suite; the PlanBench
  section is additive.

## 5. Literature numbers — /verify-claims PASS 2026-08-06 (six sources, per-paper agents)

All six sources verified against the papers themselves; internal numbers were
already verified against the graded corpora (analyze_confirmatory +
stripped_block_regrade). Verdicts and the wording corrections that BIND prose:

| claim (as previously noted) | verdict | verified value + citation anchor |
|---|---|---|
| H&Z rescue, pool 100 | **CONFIRMED** | gpt-4o Mystery: formalizer 70/100 correct vs planner 0/100 (Table 3); n=100/cell; solvability = dual-bfws-ffparser, correctness = VAL; "robust to lexical perturbation" verbatim in abstract. Cite v4 / ACL 2025.acl-long.242 ONLY (older arXiv versions = different 111-instance pool). |
| GPT-4 Mystery 4.3 (Valmeekam 600) | **CONFIRMED** | 26/600 = 4.3%, Table 2 App A.3, row "Mystery Blocksworld (Deceptive)"; regime ONE-SHOT NL; grader FD+VAL. Clean 206/600 = 34.3 (Table 1) doubly verified — reproduced from the vendored corpus on disk (157/500 + 49/100). |
| La Malfa +12/+15, pool 93 | **PARTLY** | +12 (Google Natural Plan avg) and +15 (PlanBench avg; v2 Table 1: GPT-5-mini 91.6 vs 76.6) CONFIRMED. **Pool 93 is WRONG** — no such count exists; pools are 30/benchmark (v1) or 3 runs × 50/task (v2); "93" was a success rate. Cite v2 (retitled "End-to-end PDDL Planning with Hardcoded and Dynamic Agents"). |
| LLMFP replication, pool 602 | **CONFIRMED** | n=602 per task (Blocksworld AND Mystery separately). LLMFP Claude 3.5 Sonnet 93.0 clean / 98.0 Mystery; GPT-4o 96.2 / 77.7; direct baselines 0.5–0.8 Mystery. Metric = "optimal rate" (stricter than success); **grader undisclosed** — the amendment-M line must say so; formalizes to SMT (Z3), not PDDL. |
| Göbel +3.0pp | **PARTLY** | +3.0pp (63.7→66.7), Claude Haiku 4.5, MCP, 102 IPC Blocksworld instances CONFIRMED (arXiv:2603.06064 Table II). **Mechanism correction:** their roster exposes ONLY a step-wise simulator — no planner tool exists, so non-delegation is the authors' design, not model behavior; paper attributes the modest gain to self-assessed feedback. Prose must not say the model "kept the search" by choice. |
| Planetarium 96.1/94.4/24.8 | **CONFIRMED** | Verbatim abstract triplet: GPT-4o zero-shot, parseable / solvable / semantically correct, test n=15,943. Cite the NAACL 2025 (v2) revision; middle metric is "solvable". |

Amendment-M pool/grader lines as they will print: ours 600 (Rosetta VAL);
Valmeekam 600 (FD+VAL, one-shot); H&Z 100 (VAL); LLMFP 602 (grader undisclosed);
La Malfa 3×50/task (v2); Göbel 102 IPC (their harness). The frozen prereg's
amendment-I sentence "La Malfa 93" is superseded by this table (prereg stays
untouched; deviation-table-style correction, recorded here).

## 6. Execution order after sign-off

1. PR #93 merged by Omer (this plan rides in it).
2. `git checkout paper/aaai27`; read `development/paper-git-overleaf-instructions.md`;
   `sync_overleaf.sh pull` + commit any web edits.
3. `/verify-claims` pass on the §5 list; anything failing stays out (claim wording
   degrades gracefully: "published rescue results" without the number).
4. Write the section per §3, style rules binding (no AI-tell prose habits, no
   page-budget talk).
5. Compile standalone, `sync_overleaf.sh pull` again, then push.
6. Append the dated decision entry to `development/paper_notes_discussions.md`.

> ANSWER (approve plan overall / amendments):
> **Approved overall** (Omer, 2026-08-06, via chat + inline fills above): placement
> A, ladder in body, two-layer NT presentation confirmed. No amendments.
