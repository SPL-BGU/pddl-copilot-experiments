# Datasets we own: what each can support cleanly

**Written 2026-11-25 for Omer's decision on the clean runs. DECIDED the same day: option 1 (section 7).** The question: which
figures and analyses can be built cleanly from data we already have, and what is the
smallest new run that closes the rest. Row counts were read from `results/` today.
Where I did not re-check a detail I say so.

"Clean" below means: answers stored in full, the system message correct, one serving
version, and both sides of a comparison collected in the same run.

---

## 1. The corpora

### Open-weight, large

| Corpus | Folder | Rows | Models | Thinking | Arms | Tasks | Answer storage | When |
|---|---|---|---|---|---|---|---|---|
| Main sweep, public domains | `sweep5v2-live` | 136,800 | 5 (0.8B, 4B, 9B, Gemma-26B, 35B) | on and off | no tools; tools plain + steered | 5 | first 500 characters | 24 May to 2 June |
| Main sweep, renamed domains | `sweep6-live` | 136,800 | same 5 | on and off | same | 5 | first 500 characters | same |
| Rerun, tool arms ("Part A") | `delivered-rerun` | 27,360 | 3 (9B, Gemma-26B, 35B) | off | tools plain + steered | 5 | full (65,536 characters) | 3 to 9 October |
| Rerun, no tools ("Part C") | `delivered-rerun` | 13,680 | same 3 | off | no tools | 5 | full | same run |
| Rerun, Gemma neutral prompt | `delivered-rerun` | 6,000 | Gemma-26B | off | tools, neutral prompt | 5 | full | same run |
| Corrected-prompt control | `control-promptfix` | 5,400 | same 3 | off | no tools, three system messages | solve, simulate | full | 23 to 24 November |

### Open-weight, small and special-purpose

| Corpus | Folder | Rows | What it is |
|---|---|---|---|
| Budget-decoupled control | `decoupled-rollup` | 36,480 | no tools, thinking on, four Qwen models; half is the matching main-sweep cells |
| With-tools, thinking on | `iss024d-e2e-live` | 45,600 | five models, tools, thinking on. I did not re-check what it stores |
| Context pilots (32K, 64K) | `d1-smokes` (`d1c-*`) | part of 5,108 | three models, tool arm, simulate at larger context windows |
| JSON constraint pilot | `d1-smokes` (`d1d-*`) | part of 5,108 | Qwen3.5-9B, no tools, with and without a binding JSON schema |
| vLLM 0.22.0 re-check | `vllm0220-backup` | 18,240 | one model's cells kept from the serving-version check |

### Frontier

| Corpus | Folder | Rows | Arms | Wordings | Storage |
|---|---|---|---|---|---|
| Haiku 4.5, no tools | `haiku-frontier/sweep5v2` | 1,520 | no tools | v11 | 16,384 characters |
| Haiku 4.5, tools | `haiku-frontier/sweep5v2-with-tools` | 1,520 | tools plain | v11 | 16,384 characters |
| Sonnet 4.6, no tools | `sonnet-frontier/sweep5v2` | 4,560 | no tools | v11 to v13 | 16,384 characters |
| Sonnet 4.6, tools | `sonnet-frontier/sweep5v2-with-tools` | 1,520 | tools plain | v11 | 16,384 characters |
| Renamed domains | `*/sweep6*` | 1,520 to 4,560 each | as above | as above | as above |
| 64K output probe | `*/sweep5v2*-budget64k` | 100 each | both arms | v11 | 256K characters; simulate only |
| PlanBench | `planbench/` | 600 instances per domain | no tools, tools, controls | its own | its own registered study, Haiku 4.5 |

---

## 2. What is wrong with each, in one line

| Corpus | Fault | What the fault touches |
|---|---|---|
| Main sweep (both) | answers cut at 500 characters | no delivered rate for the tool arms; unaided graded at run time by a different grader |
| Main sweep | no-tools message on solve and simulate points at a schema that never arrived | unaided solve and simulate |
| Main sweep | part of the tool cells served by vLLM 0.22.0 | re-checked on one cell; no shift found |
| Rerun, tool arms | none in the data | it missed job-level parity with the main sweep, which matters only if the two are set side by side |
| Rerun, no tools | same schema reference on solve and simulate | unaided solve and simulate only; the three validation tasks are clean |
| Control | run seven weeks after the rerun's tool arms | any tools-versus-baseline difference on solve and simulate crosses two runs |
| Claude runs | one wording (except Sonnet no tools), 16,384-character storage, solve via structured output, arms 17 days apart | every Claude comparison; simulate is censored |

Two faults that are not about a corpus: the validator's upper-case rule (a few unaided
solve grades), and the simulate tool returning a different notation than the answer
needs (a property of the tool suite).

---

## 3. What each research question needs, and what already supplies it cleanly

### RQ1: do the tools help? (delivered answer, tools against no tools)

| Measure | Clean source today | Status |
|---|---|---|
| validate_plan verdict errors | rerun, tool arms against its own no-tools arm | **clean, one run** |
| validate_domain, validate_problem delivered | rerun, same pairing | **clean, one run**; not yet analysed as delivered rates in the paper |
| solve, tools against no tools | rerun tool arms against the control's format-stated cell | **crosses two runs** |
| simulate, tools against no tools | same | **crosses two runs** |
| plan length | rerun tool arms; control cell for the unaided plans | within-arm measure, so the two runs do not interact |

### RQ2: does the model choose the right tool?

| Measure | Clean source today | Status |
|---|---|---|
| exact tool, right tool, extra tools | rerun, tool arms (27,360 rows, calls stored in full) | **clean, one run** |
| steering effect on calling | rerun, plain against steered | **clean, one run** |
| calling under thinking on | main sweep only | not affected by the 500-character cut (calls are stored in full) |

### RQ3: does the model use the tool's output?

| Measure | Clean source today | Status |
|---|---|---|
| tool right, final answer wrong | rerun, tool arms | **clean, one run**; it never involves the no-tools arm |
| context exhaustion on simulate | rerun tool arms; 32K and 64K pilots | clean as a pilot |

### Supporting

| Topic | Source | Status |
|---|---|---|
| renamed domains (contamination) | main sweep, both corpora | usable for tool-verified and unaided rates, with the storage limit stated |
| thinking on | main sweep; decoupled control | main sweep only |
| the two small models | main sweep | main sweep only |
| PlanBench | its own study | clean and closed |

---

## 4. The bottom line

**Almost everything the three questions need is already clean inside the October rerun.**
RQ2 and RQ3 come entirely from its tool arms. RQ1 on the three validation tasks comes
from its tool arms and its own no-tools arm, collected in the same run.

**Exactly one comparison is not clean: RQ1 on solve and simulate.** The rerun's no-tools
arm had the faulty message on those two tasks, and the corrected baseline was collected
seven weeks later.

So the choice is not "everything again or nothing".

---

## 5. Options, smallest first

### Option 0: no new run

Keep RQ1 on solve and simulate as it is in the merged draft: corrected baseline against
the October tool arms, stated as a cross-run comparison, with the check that the
control's registered-message cell is within 4.0 points of the rerun's unaided arm.

- Cost: none.
- Weakness: the reviewer's objection stands for the one comparison the abstract leads
  with.

### Option 1: a small matched run on solve and simulate (recommended)

Run the format-stated no-tools cell, the plain tool arm and the steered tool arm
together, on solve and simulate only, for the three models.

- Size: 3 models x 2 tasks x 3 arms x 300 trials = **5,400 trials**, the size of the
  control. The control took about ten hours of wall time with preemption.
- What it buys: RQ1 on solve and simulate becomes a same-run comparison. Every
  comparison in the paper is then inside one run.
- What stays: the paper still names two open-weight corpora (the rerun and this run),
  but no figure mixes them.
- Design work: small. The registration and the frozen analysis of the control can be
  reused almost as they are, with two arms added.

### Option 2: option 1 plus the validation tasks' no-tools arm

Not needed. The rerun's no-tools arm is already clean on the three validation tasks.

### Option 3: the full unified run

41,040 trials, about six days. One corpus for everything.

- What it buys over option 1: a single dataset name in the paper, and delivered rates
  for all five tasks from one run.
- What it costs: six days of a nineteen-day window, with preemption active, and a new
  registration and frozen analysis for all five tasks.

### The frontier models, under any option

The Claude question is separate from the cluster. Their weaknesses (one wording, cut
storage, structured output on solve, arms 17 days apart) are not fixed by any
open-weight run. Section B of `unified_run_design.md` covers the choices; a Claude run
of two models is 18,240 calls and needs no cluster time.

---

## 6. If option 1 is chosen: where each figure comes from

| Figure or table in the 8-page paper | Data |
|---|---|
| RQ1, solve and simulate (rates, by plan length, by trace length) | the small matched run |
| RQ1, validation tasks (verdict errors, delivered rates) | rerun, tool arms against its no-tools arm |
| RQ2, tool choice and steering | rerun, tool arms |
| RQ3, delivery loss | rerun, tool arms |
| Frontier rows | the Claude run decided in section B of the design form |
| PlanBench | as it is |
| Thinking on, renamed domains, small models | main sweep, in the supplement |
| The control, the pilots, the old Claude runs | supplement |

---

## 7. Decision

> ANSWER (option 0, 1 or 3): **Option 1 (Omer, 2026-11-25).** The small matched run of 5,400 trials replaces the full unified run he approved earlier the same day. He also accepted that the four items that stay in the body (small solvable problems, the simulate tool's notation and the context limit, quantization, the Claude models' different conditions) are constraints and observed behaviour, not defects.

If the answer is option 1, the open-weight part of `unified_run_design.md` shrinks to
questions A5 to A10, and A1 to A4 are fixed by this document.
