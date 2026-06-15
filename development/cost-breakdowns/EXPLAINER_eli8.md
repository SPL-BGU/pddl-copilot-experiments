# The AI Puzzle Test — explained like you're 8

This explains the 3 slides in `cheap_model_cost_slides.pptx`: what the test is, what it
costs, which puzzle-worlds we use, what we're allowed to cut, and the smallest version
that's still a *real* experiment.

---

## 1. The big idea (one breath)

We rent **AI brains** over the internet and **pay them by the word** they read and write.
We give them planning puzzles, then grade the answers. The slides are about **how much
that costs** and **how to make the test smaller without making it unfair**.

---

## 2. The cast of characters

| Word we use | What it really means (kid version) |
|---|---|
| **Model** | A student (an AI brain). We test **2 cheap students**. |
| **Task** | A *kind* of question (e.g. "solve this", "is this answer right?"). |
| **Domain** | A *puzzle world / theme* (blocks, robots, trucks…). |
| **Problem** | One specific puzzle inside a world. |
| **Variant** | The **same** question asked in **different words** (to check the student isn't fooled by wording). |
| **Think on/off** | Whether the student may **scribble rough work** before answering. |
| **Tools on/off** | Whether the student gets a **planning calculator** (our PDDL helper tools) or has to do it in their head. |

The whole point of the experiment: **does giving the student the calculator (tools) make it
get more answers right?** Everything else exists to make that comparison fair.

---

## 3. The two tests (benchmarks)

### Test A — "Single-Tool" (we call it **sweep5**) — *our own exam*
- **5 question-types (tasks):**
  1. `solve` — "make a plan to reach the goal."
  2. `validate_domain` — "is this rule-book well-formed?"
  3. `validate_problem` — "is this puzzle set up correctly?"
  4. `validate_plan` — "is this answer plan correct?" ← the giant (see slide 2)
  5. `simulate` — "if we do this action, what happens next?"
- **20 puzzle-worlds (domains)** — every task is asked in **all 20**.
- **Full size = 27,360 graded answers per student** (both think on/off, all wordings, with and without the calculator).

### Test B — **PlanBench** — *a famous public exam*
- **~9 question-types** (named t1, t2, t3, … — plan generation, plan checking, replanning, etc.).
- **Main worlds: blocksworld + logistics.** Plus a **scrambled-names version of blocksworld**
  (called *mystery*) to make sure the student is really *thinking*, not just *remembering* the
  famous puzzles. A few questions also use **depots**.
- **~7,000 puzzles per setting.**

---

## 4. The 20 puzzle-worlds, BY NAME (the thing you asked for)

Every one of the 5 sweep5 tasks runs in **all 20** of these. They come in two families:

**Classical (10)** — plain "do this then that" puzzles:
`blocksworld`, `gripper`, `miconic`, `depots`, `satellite`, `rovers`, `barman`, `parking`, `tpp`, `zenotravel`

**Numeric (10)** — puzzles with **numbers/amounts** (fuel, water, money, counts):
`counters`, `delivery`, `drone`, `sailing`, `farmland`, `gardening`, `block-grouping`, `pogo_stick`, `depot`, `zenotravel-numeric`

A few in kid words:
- `blocksworld` — stack and unstack blocks.
- `gripper` — a robot with two hands carrying balls between rooms.
- `miconic` — an elevator picking up and dropping off people.
- `delivery` / `tpp` — drive around buying/delivering things.
- `drone` / `sailing` — move around using up fuel/wind (numbers matter).
- `farmland` / `gardening` — grow/move stuff with amounts.

**Which worlds run in each experiment:**

| Experiment | How many worlds | Names |
|---|---|---|
| **sweep5** (every task) | **20** | all of the list above (10 classical + 10 numeric) |
| **PlanBench** (most tasks) | **2 (+2 extra)** | `blocksworld` + `logistics`; plus `mystery` (scrambled blocks) as a memory-cheat check, and `depots` for one task |

---

## 5. The three slides, in kid words

- **Slide 1 — the price tags.** How much each AI student costs to run **both whole tests**.
  The cheap pair (**Haiku + Gemini Flash-Lite**) ≈ **$1,047** total. Sonnet is stronger but
  ≈ **$3,253** (3× more). Qwen is cheapest but we already run Qwen for free on our own
  computers, so paying for it again is a bit silly.
- **Slide 2 — which question costs the most.** It's **`validate_plan`**. Why? Because each
  puzzle there secretly contains **10 little checks** (5 plans that are *broken* + 5 that are
  *good*). So it's **66% of the whole bill** — two out of every three dollars.
- **Slide 3 — how to spend less by doing less.** A menu of cuts and how much each one saves.

---

## 6. What gets thrown away (and what we NEVER throw away)

First: the **old "just do 1/3 of it" idea is gone.** We now plan the **full** test. The cuts
below are an *optional menu* if money gets tight — and each one only throws away **spares**.

**Safe to cut (we keep plenty):**
| Cut | What we throw away | What we keep | Saves |
|---|---|---|---|
| Wordings 6 → 2 | 4 of 6 re-phrasings of each question | still 2 wordings (enough to show wording doesn't matter) | ~−52% |
| Plan-checks 10 → 4 | 6 of the 10 mini-checks in `validate_plan` | 2 broken + 2 good (still tests both skills) | ~−40% |
| Worlds 20 → 10 | half the puzzle-worlds | **5 classical + 5 numeric** (still both families) | ~−50% |
| Drop "think-on" | the scribble-rough-work setting | the no-scribble setting | ~−64% (biggest) |

**We NEVER throw away:**
- **Tools vs no-tools** — that's the *whole question*. Drop it and there's no experiment.
- **A whole world-family** — keep *some* classical **and** *some* numeric, or we can't say it
  works "in general."
- Ideally **both think on/off**, because that's a question we actually care about. (If money is
  very tight, this is the one we'd drop *last-but-cheapest-to-drop* — it halves the cost.)

---

## 7. The smallest test that's still a REAL experiment

Think of it like a school exam: you don't need to ask **every** kid **every** question in
**every** subject to fairly rank them. You need **enough** questions, spread across **enough**
subjects, asked **fairly**.

**Recommended lean-but-solid setup:**
- ✅ Keep **both** students (the comparison).
- ✅ Keep **tools vs no-tools** (the whole point).
- ✅ Keep **both think on/off** (a real question — and it's only a 2× cost).
- ✅ Keep **10 balanced worlds** (5 classical + 5 numeric) — enough to claim "it generalizes."
- ✂️ Use **2 wordings** instead of 6, and **4 plan-checks** instead of 10.

**Why it's still solid:** every comparison cell still has **hundreds of graded answers**, so the
"with-tools vs without" gap still comes with proper **confidence bars** (we can still say "this
difference is real, not luck"). We kept *breadth* (many worlds, both families) and the *core
comparison* — we only trimmed *repetition* (extra wordings, extra near-identical plan-checks).

**Price of this lean-but-solid version:** roughly **one-tenth** of the full sweep5 bill — about
**$54** for the Haiku + Gemini pair (sweep5), still with both think settings. PlanBench shrinks
the same way. So the full *and* lean versions are both cheap on the cheap models; the cuts
matter most if we ever price the expensive students (Sonnet/Opus).

**The one rule of thumb:** *cut the repeats, keep the spread.* Drop extra wordings and extra
plan-checks (those are repeats); keep many worlds and both tool-settings (that's the spread and
the question).

---

### Numbers behind this doc
Tasks/domains/counts are from the real corpus (`results/sweep5-cluster-20260601`, Qwen3.5-9B);
costs from `cheap_model_cost_slides.py`. AI-brain word-counts are measured on our own Qwen runs
and are an **estimate** for the rented brains — a tiny **$20–35 trial run** would confirm the
real numbers before we spend the rest.
