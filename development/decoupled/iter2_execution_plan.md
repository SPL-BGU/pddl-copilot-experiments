# Iter-2 Execution Plan, Handoff & Branching Policy

**Audience:** future-me + any coding agent picking up the iter-2 review work. Read this first.

---

## 1. Goal

Address the iter-2 external-review asks to maximize **AAAI-27** acceptance probability. Both
Stanford agentic reviews (AAAI + NeurIPS rubrics) already recommend **ACCEPT**, so this is
acceptance-probability *maximization*, not a rescue. All triage decisions (A–F) are made; the
authoritative triage is `paper/automated-platforms-review/iter2/iter2_action_plan.md`.

## 2. Current state (2026-06-20)

- Both iter-2 reviews **ACCEPT**. 16 consolidated asks triaged.
- **Decisions:** venue = **AAAI-27** (Jul 27; JAIR/AIJ journal extension kept as an *optional,
  uncommitted* future path). BF16 → keep the within-model `P(call)×P(correct|call)` reframe, do
  **not** fold a BF16 number. Compute: **[6] schema-salience first, then [5b] simulate
  compressed-diff**. Frontier [1]: verify the Sonnet `solve`/`simulate`=0 (likely the sweep7
  JRE/host artifact) before surfacing the with-tools pilot. **E = yes** (build Exp 1, decoupled
  budget). **F = yes** (run Exp 2, clean cluster BF16).
- **Landed (branch `paper/iter2-writing-batch`):** [9] FWER, [12] cost production-note, [8]
  shared-vs-decoupled honesty clause. Paper build clean (16 pp, 0 undefined refs, 0 overfull).
- **Pending:** the remaining writing asks + five experiment/probe tasks (T3–T7 below).

## 3. Branching-per-task policy

- **Integration branch:** `paper/aaai27` (the stable paper branch; CI auto-syncs it to Overleaf
  with the clobber guard). Task branches fork from it and PR **back into it**.
- **One task = one branch = one PR.** Branch name: `paper/iter2-<task-slug>`.
- **Serialize.** At most **one** task branch in flight at a time; do not open the next until the
  current is merged. (Experiment branches may stay open only while their cluster sweep runs — see
  below.) This is the explicit "don't drag too many tasks at once."
- **Every PR contains, together — no stale content:**
  1. The code/experiment change (harness, scripts), if any.
  2. The matching `paper/main.tex` edit — **the paper is written side-by-side** so the manuscript
     never lags the code or the results.
  3. Docs: a dated bullet in `development/paper_notes_discussions.md`, and update this plan's task
     status.
  4. A **green paper build** (`cd paper && latexmk -pdf -interaction=nonstopmode main.tex`;
     0 undefined refs, 0 overfull) before merge.
- **Experiments:** the branch lands code first; when the cluster sweep completes, the results +
  paper writeup + doc update complete the **same** PR. Never merge a half-written experiment.
- **`main` sync:** `main` trails `paper/aaai27` by default. Only fast-forward `main` when it shares
  a head with `paper/aaai27` (a safe FF). As of 2026-06-20 `main` is 6 commits behind (`eb4818e`) —
  do **not** force-sync it.
- **Commits & PRs:** no Claude credits (global instruction).

## 4. Task queue (sequenced — work top-down, one at a time)

| T | Task | Branch | PR contents | Status |
|---|------|--------|-------------|--------|
| **T1** | iter2 triage + first writing fixes | `paper/iter2-writing-batch` | review docs, action plan, this plan, paper_notes entry; **[9] FWER + [12] cost + [8] honesty** in `main.tex` | **IN PROGRESS** |
| T2 | remaining writing asks | `paper/iter2-writing-2` | [13] reproducibility detail + HW/SW stack, [14] related-work (ReAct/PoT + RLHF-on-propensity), [16] practitioner exec summary, [7] tool-call iteration stats, [10] forced-decoding honesty note | ✅ PR open |
| T3 | **[6] schema-salience probe** | `paper/iter2-schema-salience` | `chat.py` schema transform (mirror `_strip_verbose_from_schema`) + `--schema-variant {baseline,terse,salient}` flag; 3-cell sweep (Qwen3.5-9B, `validate_plan`, tool-available, think=off); paper subsection + token-cost number | TODO |
| T4 | **[5b] simulate compressed-diff** (+ [5a] writeup) | `paper/iter2-simulate-schema` | `SimulateDeltaResponse` schema + grader branch (reuse `_normalize_trajectory`); ~900-trial no-tools `simulate` sweep (35B); paper: [5a] partial-credit decomposition + [5b] verbosity-vs-tracking result | TODO |
| T5 | **[1] frontier verify + surface** | `paper/iter2-frontier-wt` | sanity-check Sonnet `solve`/`simulate`=0 (JRE/host artifact?); aggregate the on-disk pilot (`results/frontier-with-tools-probe/`); paper datapoint, clearly pilot-N (n=6/task) | TODO |
| T6 | **Exp 1 — decoupled budget [8]** | `paper/iter2-decoupled-budget` | budget-forcing in `vllm_client.py`/`chat.py`/`runner.py` (`stop=["</think>"]` + 2-call continuation) + flags; no-tools think=on sweep (binding case Gemma-MoE-26B + Qwen-9B); paper: convert the Limitations hedge → a result | TODO |
| T7 | **Exp 2 — clean BF16 35B [2]** | `paper/iter2-bf16-control` | BF16 HF-id branch (`lib/defaults.sh`) + `rtx_pro_6000:1` routing; cluster sweep (35B tools cells; verify Java/ENHSP + `qwen3_xml` parser on a smoke first); paper: replace the quant caveat with a measured null | TODO |

## 5. Methodology guardrails (do not violate)

- **One knob per corpus** vs the shared `sweep5v2-live` baseline. Consolidate the *submission*
  (parallel array job), never the *factors* — mixing precision/prompt/schema/temperature/budget in
  one corpus destroys attribution.
- **Corpus identity is load-bearing:** each probe is a clean A/B against the locked baseline; keep
  distinct `RUN_TAG`s; never pool a probe into `sweep5v2-live`.
- **Verify before claiming.** The frontier pilot stays clearly pilot-N; the Sonnet zeros get a
  JRE/host sanity-check before any number is quoted (the sweep7 lesson).
- **Build-verify the paper every PR.** Latex must compile clean before merge.
