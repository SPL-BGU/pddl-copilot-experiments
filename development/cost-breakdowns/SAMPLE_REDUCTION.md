# Cutting cost by running fewer samples — without hurting the methodology

Single-tool focus (PlanBench runs **free** on vLLM, so its API cost is not the lever to optimise).
Question: **how few trials can we run and still make the same claims honestly?**

All dollar figures are computed from the measured token tables in `cheap_model_cost_slides.py`;
all CI widths are 95% Wilson intervals at the per-task success rate measured on the Sonnet
no-tools full run (`results/sonnet-frontier/sweep5v2`). The cost engine and the corpus shape are
unchanged — only `n` per task moves.

---

## TL;DR

The corpus is **over-sampled in exactly the place that costs the most money.** `validate_plan` is
3,000 of 4,560 trials and ~⅔ of the bill, yet its 95% CI is already **±0.6pp** — far tighter than
any other cell needs to be. Trimming its redundant within-problem replicates buys most of the
saving at almost no methodological cost.

| Step | What changes | N | Haiku-WT | Sonnet-NT | Sonnet-WT | Worst CI hit |
|---|---|--:|--:|--:|--:|---|
| current | 20 domains · 3 variants · vp=10 checks | 4,560 | $146 | $39 | $449 | — |
| **L1** | `validate_plan` 10 → 4 checks (2 invalid + 2 valid) | 2,760 | **$102** | $24 | $322 | vp CI 1.2 → 1.9pp |
| **L2** | L1 **+** variants 3 → 2 | 1,840 | **$68** | $16 | $214 | solve CI 10 → 12pp |
| **L3** | L2 **+** domains 20 → 10 (5 classical + 5 numeric) | 920 | **$34** | $8 | $107 | solve CI 10 → 17pp |

**Recommendation: ship L1 unconditionally, take L2 if budget is tight, treat L3 as a last resort.**
L1 alone cuts the Haiku-with-tools run from $146 to $102 (−30%) and the Sonnet-with-tools arm from
$449 to $322, while every per-task CI except `validate_plan` is byte-for-byte unchanged — and even
that one stays under 2pp.

---

## 1. Where the samples (and the money) actually are

Per-task `n`, the measured no-tools success rate, and its 95% Wilson CI:

| Task | n / corpus | rate | 95% CI width | NT $ | share of NT bill |
|---|--:|--:|--:|--:|--:|
| solve | 300 | 28.7% | ±5.1pp (10.2 wide) | $1.24 | 3% |
| validate_domain | 360 | 93.6% | ±2.6pp | $1.38 | 4% |
| validate_problem | 600 | 89.7% | ±2.5pp | $2.19 | 6% |
| **validate_plan** | **3,000** | **97.3%** | **±0.6pp** | **$25.64** | **66%** |
| simulate | 300 | 0.0% | +1.3pp (upper) | $8.67 | 22% |

`validate_plan` is the only badly **over-powered** cell: a ±0.6pp interval on a binary rate is far
past the precision any reviewer asks for, and it is sitting on top of two-thirds of the bill. That
is the textbook signal to cut there first.

**It is even safer to cut than the count suggests.** Those 3,000 trials are **not** 3,000
independent draws — they are 100 problems × 10 plan-checks × 3 wording variants. The 10 checks
share a domain+problem, so they are correlated; the effective sample is already well below 3,000
and the naive ±0.6pp is *optimistic*. Dropping 10 → 4 checks removes correlated within-cluster
replicates — the redundant axis — so it costs far less real information than the −1,800 trials
imply.

---

## 2. The reduction ladder, with the CI consequence of each step

Cuts are ordered **redundancy first, generality last** — the rule of thumb is *cut the repeats,
keep the spread*.

**L1 — `validate_plan` 10 → 4 plan-checks (keep 2 invalid + 2 valid).**
Pure within-problem redundancy. Keeps both polarities, so the balanced design that guards against a
degenerate "always answer VALID" passer is intact. CI on `validate_plan` goes 1.2 → 1.9pp wide
(still tight); **every other cell is untouched.** −39% trials, Haiku-WT $146 → $102.

**L2 — also drop variants 3 → 2.**
The variant axis tests wording robustness, and sweep-6 already found the wording effect **null**.
Two variants still support a wording-robustness comparison (one would delete the claim entirely, so
do not go below two). CIs widen ~1–2pp per cell (solve 10 → 12pp). −60% trials, Haiku-WT → $68.

**L3 — also halve domains 20 → 10 (5 classical + 5 numeric).**
This is the first cut that touches the **generality breadth** that the paper actually advertises, so
it is the last resort. Keep both families (the never-cut rule) and pick a spread of difficulty, not
the easy half. CIs widen materially (solve 10 → 17pp, validate_domain 5 → 9pp). −80% trials,
Haiku-WT → $34.

---

## 3. The five honesty guardrails

A smaller `n` is **honest by construction** as long as these hold. None of them is a budget call;
they are correctness conditions.

1. **Cut symmetrically across both arms.** The headline is a *paired* tools-vs-no-tools contrast, so
   any reduction must be applied to the **identical** corpus on both arms. Subsampling `validate_plan`
   on the with-tools arm only (the "cheapest lever" in `with_tools_probe_findings.md`) breaks
   N-matching and is **not** allowed without a flagged note.
2. **Report the Wilson CI at the reduced n.** The CI is the honesty meter. Cutting `n` is fine;
   quoting the *old* tight CI next to the *new* `n`, or hiding the widening, is not.
3. **Cut redundancy, never bias.** Trim replicate axes (extra plan-checks, extra wordings). Do
   **not** drop the hard domains/problems — selecting the easy half would inflate the rate, which is
   the one cut that is dishonest at any `n`.
4. **Keep the spread.** Both tool conditions (the question itself), both domain families
   (generality), both polarities in `validate_plan` (balance), ≥2 variants (wording robustness).
5. **Do not under-sample `simulate`.** It is the floor result (0% unaided) **and** the single
   largest tools lift (0 → ~100%), so it is load-bearing for the headline. Its with-tools cost is
   intrinsic to that finding (the trajectory tool dumps a large state log), not redundancy — keep
   its `n` and, if its WT cost must come down, compact the trajectory *output* rather than cutting
   trials (a tool-output change, documented, not a sample cut).

> Non-sample lever for the with-tools arm: ~⅔ of the with-tools bill is the byte-identical system
> prompt + ~3.6k-token tool schema re-sent every turn. **Prompt caching** (0.1× on that fixed prefix)
> cuts the dollar cost with **zero** change to the corpus or grading — orthogonal to everything
> above, and the recommended first move before any sample cut on the WT arm (see
> `with_tools_probe_findings.md`).

---

## 4. Probing cost — what one probe per benchmark costs

Before committing to a $146–$673 full run, we run a small **stratified probe** to measure the real
token profile and confirm feasibility. The probe is the cheap insurance that priced this whole deck.

**Single-tool probe = the same 75-trial stratified set** (49 `validate_plan` + 8 `simulate` +
6 each `solve` / `validate_problem` / `validate_domain`; canonical sweep5v2, variant 11, mid
difficulty, both polarities). Costs below are **measured from the probe's own tokens**, not projected:

| Probe | n | $ measured | basis |
|---|--:|--:|---|
| Haiku — with-tools | 75 | **$2.72** | list (agentic loop, no batch) |
| Sonnet — with-tools | 52 | **$3.48** (~$5 at full 75) | list |
| Haiku — no-tools | 75 | **$0.30** | batch −50% |

**PlanBench single-probe** has no API tokens of its own, so the same 75-instance stratum is priced
with the PlanBench per-instance proxy × the sweep5 calibration (NT ×0.54, WT ×1.59):

| Probe (75 instances) | $ projected |
|---|--:|
| Haiku — with-tools | $2.40 |
| Sonnet — with-tools | $7.19 |
| Haiku — no-tools (batch) | $0.24 |
| Sonnet — no-tools (batch) | $0.71 |

**The point:** a probe costs **single-digit dollars** to de-risk a three-figure run. The Haiku
with-tools probe ($2.72) is **~1.9%** of the $146 run it priced; the PlanBench Haiku probe ($2.40)
is **~1.1%** of the $224 full pass. Always probe before a full API run, and when only a sanity
number is needed (not a paired contrast), a probe-sized sample with reported CIs can stand on its
own — never the full 7,000-instance PlanBench corpus on a paid API.

---

### Reproduce

```
.venv/bin/python development/cost-breakdowns/cheap_model_cost_slides.py   # token tables + price engine
```
Ladder costs = the engine's `nt_task` / `wt_task` re-evaluated at the reduced per-task `n`. CIs =
95% Wilson at the rates in `results/sonnet-frontier/sweep5v2/summary_*.json`. Probe costs = summed
`result.tokens` over `results/frontier-with-tools-probe/{haiku,sonnet}-*/trials*.jsonl` × list/batch
price. PlanBench probe = the per-instance proxy in `PB[...]` × calibration, × 75.
