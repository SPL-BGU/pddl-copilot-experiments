# Frontier Phase (Haiku-first) — Implementation & Experiment Plan

Status: **DRAFT for approval** (2026-06-22). No code written yet.
Annotate your answers inline under each `> ANSWER:` slot. Builds on
`project_frontier_phase_design` (memory), `project_sonnet_frontier_notools`,
`project_cost_recalibration`, and `OPEN_ISSUES.md` ISS-023.

---

## 0. What I verified on disk (grounding)

- **Single-tool NT batch tool** (`tools/sonnet_batch.py`) is complete + correct;
  hard-codes `MODEL="claude-sonnet-4-6"` and calls
  `build_jobs(num_variants=len(ACTIVE_PROMPT_VARIANTS))`.
  `ACTIVE_PROMPT_VARIANTS[:num_variants]` ⇒ `num_variants=1` selects **v11 only**
  (a plain variant; steered = 14/15/16, auto-skipped under `no-tools` anyway).
  Sonnet NT ran v11/12/13, so **Haiku-NT-v11 ⊂ Sonnet's plain set** — strictly
  comparable, and a v11-only slice of the existing Sonnet corpus is a
  **zero-cost filter** (no Sonnet rerun).
- **Single-tool WT probe** (`tools/sonnet_tools_probe.py`) already has the full
  Anthropic agentic loop, `--model`, `--no-tools`, per-trial error handling, and
  cost projection. It is **keys-file-sample only** and sets **no `cache_control`
  anywhere** (confirmed: 0 matches in `tools/`+`planbench/`).
- **PlanBench** prompts are **pre-generated on disk**
  (`external/LLMs-Planning/plan-bench/prompts/<domain>/task_N_*.json`, present
  locally). `get_responses()` reads them, calls `send_query` per instance, writes
  `responses/<domain>/<engine>/task_N_*.json`; `response_evaluation.py` grades via
  VAL. `engine.py` is vLLM-only; backends dispatch on
  `pddl_copilot__<backend>__<model>`.
- Instance counts (t1/t2/t3/t7): blocksworld 500, logistics 285,
  mystery_blocksworld 500 ⇒ **5140/condition**. Query sizes 2.1k–8.8k chars
  (logistics t3 heaviest).

---

## 1. Simplest correct implementation, file-by-file

### Shared code (the anti-drift core)

`tools/_sonnet_common.py` already holds `format_for` (no-tools request shaping).
Add **one** shared helper there; all three runners call it:

| Helper | What it does | Consumers |
|---|---|---|
| `anthropic_tool_loop(client, model, system, user, tools, max_tokens, call_tool, *, cache=True)` | The Anthropic Messages agentic loop (currently inlined as `_run_one` in `sonnet_tools_probe.py`): loop to `MAX_TOOL_LOOPS`, convert tool_use blocks, execute via the `call_tool` callback, replay, return `{text, tool_calls, stop_reason, in_tok, out_tok, turns, loop_exhausted}`. **Caching lives here**: wrap `system` as a content block with `cache_control:{type:ephemeral}` and tag the last tool — so every WT runner caches the identical ~3.6k-tok prefix. | `sonnet_tools_probe.py` (single-tool WT) **and** `planbench/engine.py` (PlanBench WT) |

Key reuse: **one Anthropic tool loop + one caching implementation**, not three.
`format_for` stays the no-tools shaper. The Anthropic SDK submit/poll plumbing is
~30 lines and only the single-tool batch tool needs it → **not worth factoring**
(see Challenge #1).

_note_: rename to claude_api_tools_probe.py make sure other files and functions are also renamed so the code stays clean.

### The 4 runs

| # | Run | File(s) | Action | Change |
|---|---|---|---|---|
| 1 | Single-tool **Haiku NT** | `tools/sonnet_batch.py` | modify | Add `--model` (default sonnet) → set `MODEL` + price table; add `--num-variants` (default `len(ACTIVE)`) → thread into `build_jobs`. ~10 LOC. |
| 2 | Single-tool **Haiku WT** | `tools/sonnet_tools_probe.py` | modify | Add `--num-variants`; make `--keys-file` optional (absent ⇒ full grid); replace inlined `_run_one` body with the shared `anthropic_tool_loop(..., cache=True)`. ~25 LOC net. |
| — | (shared) | `tools/_sonnet_common.py` | create helper | `anthropic_tool_loop` (above). ~45 LOC. |
| 3 | PlanBench **Haiku NT** | `planbench/engine.py` | modify | Add `anthropic` backend in `_parse_engine_name` + `_anthropic_chat()` mirroring `_vllm_chat` (single live Messages call, think-off, temp 0). ~20 LOC. **Live, not batch** (Challenge #1). |
| 4 | PlanBench **Haiku WT** | `planbench/engine.py` | modify | Add `anthropic-tools` backend: persistent `(loop, mcp, AsyncAnthropic)` runtime (clone of `_get_tools_runtime`, swap VLLMClient→AsyncAnthropic) + per-instance call to shared `anthropic_tool_loop`. Reuse existing `_tools_system_prompt`/`_render_answer_from_tools` (backend-agnostic). ~40 LOC. |

**No new files, no new sbatch.** All four run **locally** with `ANTHROPIC_API_KEY`
(no GPU/cluster): runs 1–2 via the `tools/` scripts, runs 3–4 via PlanBench's own
`response_generation.py --engine pddl_copilot__anthropic[-tools]__claude-haiku-4-5`
then `response_evaluation.py`. Corpus identity holds: NT reuses
`build_jobs`/`check_success`/VAL; WT reuses the same prompts/graders.

---

## 2. Experiment matrix & run order

| Order | Cell | N | Backend | Blocked by | Est. cost (Haiku) |
|---|---|---|---|---|---|
| **1** | Single-tool **Haiku NT** (canonical, v11) | 1,520 | Batch (−50%) | — | **~$17** (measured anchor) |
| **2** | PlanBench **Haiku NT** (t1/t2/t3/t7 × bw/log/mbw) | 5,140 | Live | — | **~$12–18** (char-derived) |
| 3 | Single-tool **Haiku WT** (canonical, v11, bare loop+cache) | 1,520 | Live+cache | Fork A/C | ~$49 plain → **~$25–35 cached** |
| 4 | PlanBench **Haiku WT** (bare loop+cache) | 5,140 full / **1,200 subsample** | Live+cache | Fork A/C + cost | full ~$50–120 → **subsample ~$12–30** |

**Run order:** the two **NT runs ship first** — unblocked by every fork, cheap,
and they complete the no-tools capability ladder (Haiku-NT vs existing Sonnet-NT
vs the open roster). **Measure-first**: WT runs emit `turns/trial`; read the
histogram before deciding whether to cap `MAX_TOOL_LOOPS` below 10 (no knob added
preemptively). For Sonnet↔Haiku NT comparability, **slice Sonnet-NT to v11-only**
from the corpus on disk (free) so the ladder is v11-on-v11.

**Anon (sweep6) for Haiku:** NT validate_* near-ceiling and Sonnet contamination
Δ was null → recommend **canonical-only for all four Haiku cells**; the
contamination story is already carried by Sonnet-NT + the open roster.

> **CROSSROAD — after run 3 (single-tool Haiku WT) completes (user, 2026-06-22):**
> Once the single-tool WT run finishes and the realized (cached) cost is known,
> **if it lands materially under the ~$25–35 estimate, reconsider re-running the
> single-task WT cell on 3 prompt variants (v_i … v_{i+2}) instead of the single
> v11.** The single-prompt decision was a cost cut, not a methodological
> preference; cheaper-than-expected WT buys back the variant breadth (tighter
> per-cell N, prompt-robustness of the propensity/lift result, and v-on-v
> comparability with the open roster's plain set). Decide at that gate, not now.
> NB: this is WT-only — NT stays single-variant (run 1 is done at v11).

---

## 3. Open forks — recommendation (these gate ONLY the WT cells)

**A — Headline WT harness.** Recommend **(A) bare Messages-API loop as the
shipping harness now, with (C) Claude-native as a separately-approved second row,
never (B) for Haiku.** (A) is already built (`sonnet_tools_probe` + the new
`anthropic-tools` backend), is **byte-comparable to the open-model WT arm** (same
forcing prompt, same `check_success`/VAL graders), and lands the capability-ladder
numbers immediately. (C) Claude Code/Agent-SDK + marketplace-skills is the
max-fidelity "deployed product" you lean toward — but it's a **large new
integration, Anthropic-locked, and confounds tools-vs-scaffold**, so it should be
a deliberate add-on, not the critical path. (B) agnostic framework is the
cross-provider/Gemini direction — deferred with Gemini.

**B — Bare-loop ablation alongside C.** **Yes** — nearly free (the bare loop *is*
the (A) runner). `(C) − (A)` attributes lift to scaffold/skills; `(A) − no-tools`
attributes it to raw tools. Per SWE-agent, an unablated (C) lift is
uninterpretable; so even if (C) is approved, (A) runs on the same cells.

**C — Steering as calibrated system prompt.** **Agree** — drop the v14–16
sentence-append; make steering a system-prompt axis with **two pre-registered
texts**: *neutral* (no tool-forcing) vs a *tool-oriented* "pddl-copilot" prompt,
calibrated to avoid the over-trigger from "MUST use tool." **Neutral is the
headline** (measures propensity — the frontier question); oriented measures the
capability ceiling (probe already pegged ~100%). Pre-register both in
`EXPERIMENTS_FLOW.md` + `paper_notes_discussions.md`. Running both **doubles WT
trials** → recommend **neutral-primary**, oriented only if an N-matched ceiling is
needed.

---

## 4. Simplification challenges (the point of this pass)

1. **PlanBench NT: run LIVE, not batch — overriding settled-decision #2 for this
   cell only.** Batch's premise was the −50% discount, but Haiku PlanBench NT is
   only **~$12–18 total**, so batch saves **~$8** while costing an ~80-LOC
   standalone harness (re-read prompts, write PlanBench's response-JSON schema,
   re-invoke evaluator) that duplicates PlanBench's own iterate-and-write. Live is
   **one `_anthropic_chat` branch (~20 LOC)** reusing `send_query`/VAL untouched,
   symmetric with `vllm`/`vllm-tools`. Single-tool NT *does* use batch — there the
   tool already exists, so honoring batch is free. Asymmetry justified by code
   cost, not principle.
2. **PlanBench WT: subsample (≈100/cell = 1,200) + caching, after a turns/tokens
   probe.** Only expensive run; full 5,140 buys tight CIs + baseline-instance
   matching, but "does Haiku clear the NL→PDDL wall *with* tools?" is answerable on
   a subsample with CIs at **~⅕ cost**. Measure turns first, then size N.
3. **No anon for Haiku** — saves a full duplicate of every cell for a
   contamination Δ already shown null at the frontier.
4. **One shared `anthropic_tool_loop`** instead of a copy per WT runner — single
   caching implementation, single drift surface.
5. **Slice Sonnet-NT to v11**, don't rerun — comparability for free.

---

## 5. Documentation owed (on execution, not now)

- `development/CHANGELOG.md` dated entry (4 frontier backends, live/batch split,
  caching).
- `EXPERIMENTS_FLOW.md` §8/§11 (frontier backends + pre-registered steering texts).
- `development/paper_notes_discussions.md` (live-PlanBench-NT, no-anon, subsample
  decisions).
- **Narrows `ISS-023`** — caching is the cheaper-WT answer it asked for; move
  toward closure once run 3 measures the realized saving.

---

## 6. Decisions needed before I start the WT runs

(The two NT runs are unblocked; I can start them on approval. WT needs the below.)

### Q1 — WT harness (gates runs 3–4)
- **(rec) Bare loop now, C as add-on** — ship the comparable bare loop now; treat
  Claude-native (C) as a separately-approved second row + bare-loop ablation.
- Claude-native (C) only — large new build, delays WT, still needs the (A)
  ablation for attribution.
- Bare loop only — cheapest; loses the "deployed product" framing.

> ANSWER: yes, but C is a must. well run plan-bench using c so we can use the subagents feature of claude incase we
> add the hybrid approach so a must establish some success criteria for the setup. haiku is enough for it.
> no need to add other models for C at the moment. 

### Q2 — PlanBench NT backend (run 2; my main simplification challenge)
- **(rec)** Live (~$15, +20 LOC) — tiny `anthropic` backend; reuse send_query/VAL;
  overrides batch for this cell only (saves ~80 LOC for ~$8 extra).
- Batch (~$8, +80 LOC) — honor settled-decision #2; standalone offline harness.

> ANSWER: explain further the question. clarify and simplify explanations

### Q3 — WT scope/cost controls (runs 3–4; can pick several)
- **(rec) Neutral steering primary** — neutral system prompt as headline; oriented
  only if an N-matched ceiling is needed (avoids doubling WT).
- **(rec) Subsample PlanBench WT** — ~100/cell (1,200) with CIs after a probe;
  full only if reviewers need tight CIs / baseline-instance matching.
- **(rec) Canonical-only (no anon)** — skip the sweep6 duplicate for all Haiku
  cells; contamination Δ already null at the frontier.

> ANSWER: 1. run both steered and neutral for haiku, I accept it; 2. ok; 3. ok

### Q4 — Anything else / overrides

> ANSWER: explain further why ther bare api is valuble comparison.
> what the reviewers would appreciate more as the main results? the vllm has any priority over claude-api?
> if claude-api is preffered perrhaps the harness is enough, otherwise the rec of running bare api as a must is correct.
