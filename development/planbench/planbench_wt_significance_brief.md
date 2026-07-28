# PlanBench with-tools arm — plain-language brief and go/no-go

**Why this page exists.** At the scope slot (carried to `planbench_wt_prereg.md` §10 RATIFY)
you wrote: *"lets simplify and dig deeper here i either dont realy get the full picture or
it just seems insignificant."* The previous session read the "simplify" half as a vote for
shape B and applied it. It never answered the other half. This page does, in one read, and
ends in three answer slots. **Nothing is built and nothing is spent.**

**State verified 2026-07-28 (not taken from the handoff):**
- The prereg branch is **merged to main** (`53553a7`), tree clean. The handoff still says
  "5 commits ahead, unmerged" — stale, corrected below.
- **Nothing built.** No `anthropic-tools` / `anthropic-scaffold` token exists anywhere in
  the code. No adapter, no engine registration, no venv.
- **NT anchors reproduce exactly** off `results/haiku-frontier/planbench/`: ordinary t1
  205/500, Mystery t1 4/500, n=500 both. The layer this arm sits next to is real and graded.

---

## 1. The whole arm in six sentences

PlanBench hands the model a blocksworld problem in English. It ships the same 500 problems
a second time with every word renamed to nonsense: "object a craves object b" instead of
"a is on b". We verified on disk that the nonsense edition is the identical puzzle under a
pure symbol rename with an identity object mapping (501/501 instances, 500/500 gold plans),
so the two editions are exactly paired. We already measured Haiku with no tools: **41.0% on
the ordinary edition, 0.8% on the nonsense one** — renaming the words destroys it, and that
collapse is PlanBench's most cited result. Our paper's whole thesis is that the model should
not be doing the search at all: it should write PDDL and hand it to Fast Downward, which
cannot see what the predicates are called. So either the nonsense edition stops mattering
once a real planner is doing the search, or the model still fails and the failure was never
search in the first place — it lives in the English→PDDL translation, and we can point at
exactly that stage.

## 2. Why it takes four cells, not two

|  | tools on | tools off (matched) | what the row is for |
|---|---|---|---|
| **ordinary** | ~$17 | ~$4 | the ceiling: proves the tool path works at all on this benchmark |
| **Mystery** | ~$21 | ~$4 | the actual question: does renaming still hurt when a planner does the search |

The two "tools off" cells look redundant against the graded NT layer, and they are not. The
graded layer answered the bare PlanBench prompt. The tools arm has to answer a scaffolded
prompt (write PDDL, use the tools, format the answer this way). Comparing tools-on against
the bare NT rows would confound tool access with prompt shape. Every published
tools-help-planning comparison I could find changes both at once. **The matched cells buy
the single ablation: the only thing that differs is whether the tools are plugged in.** That
is the design's one genuinely unrun contribution, and it costs $8 of the $46.

## 3. What each possible result buys

| outcome | rule | what we print | worth $46? |
|---|---|---|---|
| **RESCUE** | Mystery ≥ 272/500 | the funnel claim survives on an instrument we did not build | yes, but unsurprising — the direction is published ≥4× |
| **PARTIAL** | CI inside [5%, 50%) | tools narrow the gap without closing it; "gap narrowed, not closed" language is pre-committed | yes — a bounded honest number nobody has |
| **NO-RESCUE** | Wilson upper < 5% | the failure moved upstream to translation, shown directly by comparing the model's PDDL against the true PDDL | **most interesting and most novel outcome** |
| **INCONCLUSIVE / joint falsifier** | 62 of 500 integer outcomes | we report the mechanism claim unsupported | this is the risk you are buying |

Note the third row. If tools do not rescue Mystery, that is not a wasted $46. It reframes
the field's headline "LLMs cannot plan" as "LLMs cannot translate obfuscated English", and
our tools are the instrument that makes the difference visible. The prereg pre-commits to
publishing all four outcomes, including the one where our own story fails.

## 4. "It seems insignificant" — straight answer

**You are right about the direction.** "Give it a planner and Mystery gets better" is
already published at least four times. If that sentence were the deliverable, do not pay
for it.

**One paper is uncomfortably close and it is the reason RESCUE is not a foregone
conclusion.** Göbel et al. (arXiv:2603.06064, spot-verified 07-25) ran **this exact model**
with PDDL tools over MCP and got 63.7% → 66.7%, a +3.0pp move at 5.7× the token cost. But
they exposed a step-wise simulator and left the search inside the model, on 102 clean IPC
instances with no obfuscation. We hand the search away entirely and test the rename. It is
a different experiment, and their thin result is exactly why ours is not predictable.

**The one argument that justifies the $46 is defensive, not novel.** Every tools number in
the paper today is measured on a benchmark we built. The cheapest attack a reviewer has is
"you designed the benchmark your method wins on". This arm is the only place in the paper
where that attack dies, and it dies for the price of a dinner. If that argument does not
move you, then the correct action is **not to run it** and to publish the design as
pre-registered future work inside an NT-only Act 4. That path already exists in the prereg
(§8 fallback) and it is a legitimate outcome, not a failure.

## 5. "Dig deeper" — where the depth actually is

The depth is not more cells. It is two measurements this setup makes possible and the bare
benchmark cannot:

1. **Delegation rate.** Did the model actually call `classic_planner`, or did it keep
   guessing in its head while holding a planner? Pre-registered threshold: 80%.
2. **Formalization match.** Is the PDDL the model wrote a correct renaming of the true
   PDDL? We can check this exactly, because the true PDDL is reconstructible from the
   prompt and we verified that for 500/500 instances in both editions. Domain level uses a
   24-bijection check, problem level uses set equality.

Together those split three failure modes that the literature reports as one number: cannot
plan, cannot translate, did not use the tool. Nobody has run that split on PlanBench. That
is the part of this arm that is not a replication, and it is already inside shape B at no
extra cost.

## 6. Money, and every off-ramp

| step | cost | off-ramp |
|---|---|---|
| build (adapter, instance-id tool logging, engine names, venv) | $0, ~1 agent-day of my time | you can stop here |
| calibration: 40 throwaway instances, disjoint from the graded set | ≈$1.50 | you see the real $/trial before authorizing anything. Its decision function reads cost and throughput only, never accuracy, so it cannot peek at the answer |
| full run, 4 cells × 500 | ≈$46 central (1000 tool trials ≈$38 + 1000 matched ≈$8); low band ≈$25 | auto-kill if calibration projects over the balance even at n=200/cell |
| optional pure-availability sensitivity arm | ≈$4 | drop it freely |
| hard deadline | — | 2026-08-15: converts to pre-registered future work |

The account is prepaid with no real-time billing, so **the balance you load is the hard
ceiling** and no software cap is needed. One caveat carried forward: the ~$70.6 remainder
figure is bookkeeping from `frontier_rerun_handoff.md:74`, not a console reading. Confirm
it before loading.

---

## 7. Decisions

**Slot 1 — go or no-go.**

- **A. Ratify shape B as written (my recommendation).** 4 cells, whole 500-instance pool,
  ≈$46 central / ≈$52 with sensitivity + calibration. Rationale: the reviewer objection it
  buys off is the most likely attack on the paper's central claim, $46 is inside the noise
  of the project's budget, and the delegation + formalization split makes it more than a
  replication.
- **B. Ratify, but Mystery pair only (≈$25).** Not recommended. Without the
  ordinary-with-tools cell there is no ceiling, so a low Mystery number cannot be told
  apart from "our scaffold just does not work on this benchmark", and the arm loses its
  ability to conclude anything.
- **C. Do not run it.** Publish the design as pre-registered future work inside an NT-only
  Act 4 (§8 fallback). $0. Act 4 still carries its headline, which this arm was never
  allowed to touch.
- **D. Something else — tell me what would make it worth doing.**

> ANSWER:
>

**Slot 2 — only if A or B.** How much balance do you want loaded, and do you want me to
treat the ~$70.6 as confirmed or wait for you to read the console?

> ANSWER:
>

**Slot 3 — free work available right now, not blocked by this gate.** Both are local, $0,
and both currently block paper prose:
(a) the NT t3 GPT-4 **mix-confound audit** (`planbench_frontier_haiku_nt.md` finding 2 is
marked PENDING AUDIT; the committed GPT-4 t3 corpus is a different corpus, and a
common-mix reweighting collapses the Mystery t3 gap from 28.2pp to 9.5pp);
(b) `/verify-claims` on the two free NT strengtheners — the apparent independent LLMFP
replication (41.5 / 0.8 at n=602 against our 41.0 / 0.8) and the published GPT-4 Mystery-t1
comparator (26/600 = 4.3% [3.0,6.3], Valmeekam arXiv:2305.15771 Table 1), which is
CI-disjoint **above** Haiku's 0.8% and is currently recorded as "not in canonical".
Should I start these now while the gate is open?

> ANSWER:
>

---

**If you pick A or B, the build order is unchanged** and lives in
`PLANBENCH_WT_HANDOFF.md` §6. **If you pick C**, the only owed work is a paragraph in the
Act 4 write-up that publishes this design as future work, and the ~$70.6 goes back on the
table for something else.
