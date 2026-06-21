# The AI Puzzle Test — explained like you're 8

This explains the 4 slides in `cheap_model_cost_slides.pptx`: what the test is, what it
**really** costs (we used to guess — now we **measured**), which puzzle-worlds we use,
and what we're allowed to cut.

> **What changed (June 2026):** the old version of these slides **guessed** the price by
> counting the words of a *different, free* AI student (our own Qwen). Now we have actually
> **rented two real students and run them** — so the prices below are **measured, not guessed**.
> And the guess was wrong in **two** ways (see §5). The old "$20–35 trial run will confirm
> the numbers" promise is **done** — this *is* the confirmation.

---

## 1. The big idea (one breath)

We rent **AI brains** over the internet and **pay them by the word** they read and write.
We give them planning puzzles, then grade the answers. The slides are about **how much
that really costs**, now that we've measured it for real.

---

## 2. The cast of characters

| Word we use | What it really means (kid version) |
|---|---|
| **Model** | A student (an AI brain). The two we actually rented: **Sonnet** (a strong, pricey one) and **Haiku** (a cheaper one). |
| **Task** | A *kind* of question (e.g. "solve this", "is this answer right?"). |
| **Domain** | A *puzzle world / theme* (blocks, robots, trucks…). |
| **Problem** | One specific puzzle inside a world. |
| **Variant** | The **same** question asked in **different words** (to check the student isn't fooled by wording). |
| **Think on/off** | Whether the student may **scribble rough work** before answering. *(We measured with think **off**.)* |
| **Tools on/off** | Whether the student gets a **planning calculator** (our PDDL helper tools) or has to do it in their head. |

The whole point: **does giving the student the calculator (tools) make it get more answers
right?** Everything else exists to make that comparison fair.

---

## 3. The price tags (slides 1 & 3)

We **measured both** rented students — **Sonnet** (strong, pricey) and **Haiku** (cheaper) —
on **both** the no-calculator and calculator tests. The big bills:

| What we ran | Student | Calculator? | **Real price** | Status |
|---|---|---|--:|---|
| The **whole** no-calculator test, both versions | **Sonnet** | no | **$81.51** | ✅ done |
| The calculator test (one version) | **Haiku** | yes | **$146** | ⏳ planned, waiting for a discount trick |
| (same, with the pricey student) | Sonnet | yes | $449 | for comparison |

**Now the new part:** once you've measured a student's **word-counts**, you can price **any**
student from **any company** — just multiply those counts by that company's per-word price. So we
can lay out the **whole class** (Anthropic, OpenAI, Google, Alibaba), even the students we never
rented. One test version, one corpus (the ✅ rows are the two we really measured; the rest are
projected from the measured word-counts):

| Tier | Student (company) | price/M words (in / out) | No-calculator | Calculator | How we know |
|---|---|---|--:|--:|---|
| **Top** | **Sonnet 4.6** (Anthropic) | $3 / $15 | **$39** | **$449** | ✅ measured |
| Top | GPT-5.5 (OpenAI) | $5 / $30 | $86 | $788 | projected |
| Top | Gemini 3.1 Pro (Google) | $2 / $12 | $34 | $315 | projected |
| Top | Qwen3.7-Max (Alibaba) | $2.5 / $7.5 | $26 | $321 | projected |
| **Middle** | **Haiku 4.5** (Anthropic) | $1 / $5 | **$17** | **$146** | ✅ measured |
| Middle | GPT-5.4 Mini (OpenAI) | $0.75 / $4.5 | $13 | $118 | projected |
| Middle | Gemini 2.5 Flash (Google) | $0.30 / $2.5 | $7 | $54 | projected |
| Middle | Qwen-Plus (Alibaba) | $0.40 / $1.2 | $4 | $51 | projected |
| **Budget** | GPT-5.4 Nano (OpenAI) | $0.20 / $1.25 | $4 | $32 | projected |
| Budget | Gemini 2.5 Flash-Lite (Google) | $0.10 / $0.40 | $1 | $14 | projected |
| Budget | Qwen-Flash (Alibaba) | $0.05 / $0.40 | $1 | $9 | projected (we run Qwen **free** anyway) |

*(Prices are June-2026 list prices — they change monthly, so re-check before quoting. Qwen-Max's
$2.5/$7.5 is currently half-off to $1.25/$3.75 on a promo.)*

**Two honest catches when reading the projected (non-✅) rows:**
1. Comparing a projected student to a measured one mixes **two things** — the company's price
   **and** the fact that we used each measured student's *own* word-count but everyone else's the
   *average*. So read the projected numbers as a **price map**, not a head-to-head race.
2. The **no-calculator** projection is trustworthy (every student writes a roughly-short answer),
   but the **calculator** projection is **shakier** — how much back-and-forth a student does is
   **its own personality** (see §4), so those calculator dollars could swing a fair bit.

---

## 4. Why the calculator is so much pricier

When the student has **no calculator**, it just reads the puzzle once and writes one answer.
Cheap. We can even mail all the puzzles in one big envelope ("batch") for **half price**.

When the student **uses the calculator**, it's a **back-and-forth conversation**: "use this
tool" → we run the tool → "here's the result" → "now use that tool" → … And here's the catch:
**every time it speaks, it re-reads the whole conversation so far** — the rulebook, the
calculator's instruction manual (long!), and everything already said. We **pay for all those
words again, every single turn.** And you **can't** mail a back-and-forth in one envelope, so
there's **no half-price**. That's why the calculator test costs multiples of the plain one.

**And how much back-and-forth depends on the student.** On "solve", **Haiku** chattered through
**50,000** words where **Sonnet** used only **19,000**. On "simulate", **Sonnet** pulled a giant
**141,000-word** play-by-play, while **Haiku** hit its **memory limit** and gave up part-way. So
the calculator's price is genuinely **hard to predict** for a student we haven't actually run —
that's why the cheaper students' calculator numbers in §3 are marked "shakier."

---

## 5. The two surprises (slide 1, the colored boxes)

The old **guess** was wrong in opposite directions:

- 🔻 **No-calculator was HALF as expensive as we guessed.** The free student (Qwen) writes
  a *long* answer even with scribbling off. The real students are **terse** — on "solve",
  Qwen wrote ~3,746 words, **Sonnet wrote 261**. Short answers = small bill. Guess said
  ~$73/version; **real was $39**.
- 🔺 **The calculator test was MORE expensive than we guessed (~1.6×).** All that back-and-forth
  re-reading (especially "simulate", which dumps a giant play-by-play) costs more than the
  guess assumed. Guess said ~$92; **real was $146**.

**The lesson:** these two errors **don't cancel out** for any single number — so every dollar
figure on the *old* slides is now retired. Each part of the test must be priced from its **own**
real measurement.

---

## 6. Which question costs the most (slide 2)

Still **`validate_plan`** — "is this answer plan correct?" Each puzzle there secretly contains
**10 little checks** (5 plans that are *broken* + 5 that are *good*), so it's **3,000 of the
4,560** answers and **about two-thirds (66%) of the no-calculator bill** ($25.6 of $39).

The other thing slide 2 shows: with the calculator, the pricey questions are **`simulate`** and
**`solve`** — the ones with the longest back-and-forth. (`simulate` jumped from a guessed $8 to a
real $30 on Haiku.)

---

## 7. The discount trick we're waiting on (slide 3)

Most of what the calculator test reads is **the same opening over and over** (the rulebook + the
long calculator manual) — about **9 of every 10 words it reads**. The rental company offers a
**"remember this" sticker** (*prompt caching*): stick it on that unchanging opening and they charge
**one-tenth** to re-read it. That's a **real** saving with **no change to the experiment at all** —
though not a 9/10 cut of the *bill*, because the student's own writing is charged at a higher rate,
so reading is only about **two-thirds of the money**.

Catch: we haven't switched it on yet, so we need a **quick re-test** to see how much it really
saves before paying for the full Haiku-with-calculator run. (Best guess: it drops $146 toward
~$90–110.) **That's the open decision** — run Haiku-with-tools once the sticker clears the budget.

---

## 8. A hybrid idea: a smart boss + a cheap helper (copy-paste cost)

The idea: use the **strong student (Sonnet)** as a **boss** who isn't allowed to touch the calculator
himself, but who can **hand each job to a cheaper helper (Haiku)** who *does* have the calculator.
The boss reads the question, says "Haiku, you take this one," reads Haiku's short answer back, and
writes the final reply.

**What you pay = the boss's thinking + the helper's calculator work** (one test version, one corpus,
think-off):

| Question type | Boss: Sonnet (no calc, **live**) | Helper: Haiku (with calc) | Together |
|---|--:|--:|--:|
| solve | $2.49 | $26.06 | $28.55 |
| validate_domain | $2.76 | $6.17 | $8.93 |
| validate_problem | $4.38 | $11.17 | $15.56 |
| validate_plan | $51.26 | $73.07 | $124.34 |
| simulate | $17.34 | $29.56 | $46.90 |
| **TOTAL** | **$78** | **$146** | **≈ $224** |

**Why the boss costs $78, not $39:** when Sonnet does the no-calculator test *alone*, we mail all the
questions in one big envelope (**batch, half price → $39**). But a **boss who waits for a helper
can't be mailed in an envelope** — it's a live back-and-forth, so the boss pays **full price ($78)**,
the very same reason the calculator test can't be batched. The helper's giant play-by-play (on
`simulate`) stays **inside Haiku**; the boss only reads Haiku's *short final answer*, so the boss's
bill stays small.

**How it stacks up** (one version, one corpus, think-off):

| Setup | Price | Accuracy |
|---|--:|---|
| Sonnet alone, no calculator (batchable) | $39 | low (solve ~29%, simulate 0%) |
| **Hybrid: Sonnet boss + Haiku helper** | **≈ $224** | ~100% (the helper does the work) |
| Haiku alone, with calculator | $146 | ~100% |
| Sonnet alone, with calculator | $449 | ~100% |

**The honest verdict:** in *our* test every question is a **single** job, so there's nothing for the
boss to break into steps — the boss is **pure overhead**. The hybrid pays **$224 to buy the same
~100% that Haiku-with-tools already gives for $146.** The boss-plus-helper pattern only earns its keep
when the top job is **big and needs splitting** (pick which helper, chain several sub-jobs, double-check
the result) — none of which our single-tool questions need. For this paper, **Haiku alone with tools
wins**; keep the hybrid in your pocket for genuinely multi-step work.

**And on PlanBench?** Same idea, bigger numbers — PlanBench is ~7,000 puzzles per setting, so one pass
of boss + helper comes to **≈ $356** (boss **$131** live + helper **$224**):

| Setup | Cost (one PlanBench pass, ~7,000 puzzles) |
|---|--:|
| Sonnet alone, no calculator (batchable) | $66 |
| **Hybrid: Sonnet boss + Haiku helper** | **≈ $356** |
| Haiku alone, with calculator | $224 |
| Sonnet alone, with calculator | $673 |

Same shape as our own test — the boss is overhead, so the hybrid ($356) just pays extra over Haiku
alone ($224) for the same answers. And remember §9: **PlanBench already runs FREE on our own
computers**, so renting a boss-plus-helper for it makes even *less* sense than on our own test. **Keep
PlanBench on vLLM.**

*(Numbers: boss = the model's measured/calibrated no-calculator word-counts at **full list price**;
helper = the with-calculator cost. Both totals are **floors** — one boss pass; a real hand-off adds
about one more boss turn (single-tool → ~$260–300; PlanBench → ~$420–490). Caching the boss's fixed
opening would pull them back down. PlanBench figures are calibration-transferred, not API-measured, so
treat them as ±wide. All from `cheap_model_cost_slides.py` → `hybrid_total()` / `hybrid_pb()`.)*

---

## 9. PlanBench — the famous public exam (slide 4)

`PlanBench` is a well-known public test (blocksworld, logistics, plus a *scrambled-names* version
called **mystery** to make sure the student is **thinking**, not **remembering**). It has **~7,000
puzzles per setting** — way more than our own test.

On the rented API, the **calculator** version of PlanBench is the real **budget-buster** — and the
bill depends entirely on which student you rent: roughly **$14** (Qwen-Flash) → **$224** (Haiku) →
**$673** (Sonnet) → **$1,204** (GPT-5.5) for **one pass**. But here's the happy part — **we already
run PlanBench for FREE on our own computers** (the open-weight students on SLURM). So the rule is
simple: **keep PlanBench on our own machines.** Only rent a *tiny* managed sample (a few hundred
puzzles) if we ever need one — never the full 7,000.

---

## 10. The 20 puzzle-worlds, BY NAME

Every one of the 5 single-tool tasks runs in **all 20** of these. Two families:

**Classical (10)** — plain "do this then that" puzzles:
`blocksworld`, `gripper`, `miconic`, `depots`, `satellite`, `rovers`, `barman`, `parking`, `tpp`, `zenotravel`

**Numeric (10)** — puzzles with **numbers/amounts** (fuel, water, money, counts):
`counters`, `delivery`, `drone`, `sailing`, `farmland`, `gardening`, `block-grouping`, `pogo_stick`, `depot`, `zenotravel-numeric`

A few in kid words: `blocksworld` (stack/unstack blocks), `gripper` (a two-handed robot carrying
balls between rooms), `miconic` (an elevator picking up and dropping off people), `drone`/`sailing`
(move around using up fuel/wind — numbers matter), `farmland`/`gardening` (grow/move stuff with amounts).

---

## 11. What gets thrown away (and what we NEVER throw away)

If money gets tight, each cut below only throws away **spares**. The percentages are the *same*
for every student (they depend on the test's shape, not the price), so they still hold after the
re-measurement.

**Safe to cut:**
| Cut | What we throw away | What we keep | Saves |
|---|---|---|---|
| Wordings 6 → 2 | 4 of 6 re-phrasings | 2 wordings (enough to show wording doesn't matter) | ~−52% |
| Plan-checks 10 → 4 | 6 of the 10 mini-checks in `validate_plan` | 2 broken + 2 good | ~−40% |
| Worlds 20 → 10 | half the puzzle-worlds | **5 classical + 5 numeric** | ~−50% |
| Drop "think-on" | the scribble-rough-work setting | the no-scribble setting | biggest — **but for the rented students, think-on cost is still UNmeasured** |

**We NEVER throw away:**
- **Tools vs no-tools** — that's the *whole question*.
- **A whole world-family** — keep *some* classical **and** *some* numeric, or we can't say it
  works "in general."

> ⚠️ **One honest caveat:** everything we measured used **think OFF**. We have **no real price**
> yet for a rented student that's allowed to scribble (think on) — its rough work could be much
> longer than the free student's, so any think-on dollar figure is still a **guess**.

---

## 12. The one rule of thumb

*Cut the repeats, keep the spread.* Drop extra wordings and extra plan-checks (repeats); keep many
worlds and both tool-settings (that's the spread and the question).

---

### Numbers behind this doc
Worlds/tasks/counts: the real corpus (`results/sweep5-cluster-20260601`, Qwen3.5-9B). **Prices: now
priced from MEASURED word-counts** on real API runs, not guessed:
- **no-tools** — Sonnet full run (`.local/sonnet/grade_{canonical,anon}.log`, both corpora = $81.51)
  **and** Haiku probe (`results/frontier-with-tools-probe/haiku-no-tools`).
- **with-tools** — the live Sonnet & Haiku probes (`results/frontier-with-tools-probe/{sonnet,haiku}-with-tools`),
  summarized in `development/with_tools_probe_findings.md`.

Sonnet and Haiku are priced from **their own** measured word-counts (both arms). Every other
student (OpenAI GPT, Google Gemini, Alibaba Qwen) is **projected** by re-pricing the **average** of
the two measured word-counts — accurate for no-tools, **± wide for with-tools** (the two measured
students differ up to ~2.7× in back-and-forth). Per-word **prices** are June-2026 list prices:
Anthropic from the `claude-api` skill, Google/OpenAI/Alibaba from vendor docs — re-verify in-console
(they move monthly; Qwen-Max is on a 50%-off promo). The slide deck **computes** every figure from
the word-count + price tables, so editing the data and re-running updates the slides. Anything with
think **on** is still **unmeasured** and flagged as such. PlanBench has no API word-counts of its
own, so its numbers (§9) are transferred from the single-tool measurement.
