# Decoupled-budget think=on — implementation plan (Line 1 / iter-2 T6 / Exp 1)

**Status:** PLAN ONLY. Nothing built, nothing run. Cluster work is GATED — ping first.
**Date:** 2026-06-24
**Background:** `../decoupled/simulate_decisions_and_next_steps.md` (Line 1), `../decoupled/iter2_execution_plan.md` (T6),
`paper/automated-platforms-review/iter2/iter2_action_plan.md` (Exp 1), memory
`project_think_overflow_unreachable`, CHANGELOG 2026-05-04 (think-overflow predicate).

Answer the `> DECISION:` slots inline; I'll fold them in before any code.

---

## Objective

Give the **reasoning phase** and the **answer phase** of a think=on no-tools trial **separate
token budgets**, so a long reasoning trace can no longer consume the budget the model needs to
emit its final answer. This converts the Limitations hedge ("think=on is confounded by a shared
decode budget; baseline truncates 55–83%") into a measured result.

## The mechanism (verified against the current code)

Today, `chat_without_tools` makes **one** `client.chat()` call with `max_tokens = num_predict`.
For a Qwen3 thinking model that single budget covers `<think>…</think>` **and** the answer. If the
model spends it all thinking, the answer comes back empty → `truncated_no_answer` / `think_overflow`.

The fix is a **2-call continuation**:

- **Call 1 — reasoning.** `messages=[system,user]`, `enable_thinking=True` (Qwen3 template prepends
  `<think>\n`), `max_tokens = THINK_BUDGET`, `stop=["</think>"]`. The model produces only the
  reasoning body (the `<think>` open is in the prompt, not generated).
  - `finish_reason="stop"` → reasoning closed within budget.
  - `finish_reason="length"` → reasoning hit THINK_BUDGET. **We force-close it and still proceed**
    — this is the whole point: the answer is no longer starved. Record `think_truncated=True`.
- **Call 2 — answer (continuation).** `messages=[system,user, {role:assistant,
  content:"<think>\n{reasoning}\n</think>\n\n"}]` with vLLM
  `extra_body={continue_final_message:True, add_generation_prompt:False}`, `max_tokens =
  ANSWER_BUDGET`, no `stop`. The model continues from the closed think block and emits the answer.
  `finish_reason="length"` here is the **genuine answer-truncation** signal that grading cares about.

`THINK_BUDGET` and `ANSWER_BUDGET` are independent `max_tokens` on the two calls — that is the
decoupling. The existing context-overflow retry in `vllm_client.chat()` is the safety net if a
budget choice overflows `max_model_len`.

### Why this is correct *and* minimal
- It is genuinely a different experiment from the failed `b527f71` cap-raise (that enlarged the
  single shared window; it did not split reasoning from answer). Directly answers reviewer [8].
- It reuses the existing single-call primitive twice; no new transport, no new server endpoint.
- `stop` is a standard OpenAI param (not currently plumbed — confirmed); `continue_final_message`
  is a vLLM chat param present since well before the pinned **v0.20.2** image. No new dependency.

---

## ⚠️ Difficulties found (the "report back" items)

### D1 — The "binding case = Gemma-MoE-26B" is **wrong for this mechanism** (correctness)
`gemma4:26b-a4b` is configured with `REASONING_PARSER=none` because **Gemma's tokenizer has no
`<think>` tokens** (`cluster-experimenting/lib/defaults.sh:84-101`). So:
- `stop=["</think>"]` is meaningless for Gemma — it never emits that token.
- For Gemma, think=on ≈ think=off (the template ignores `enable_thinking`); its 89–100% truncation
  is **plain long-output truncation**, not the shared-reasoning-budget confound. There is nothing
  to decouple.

The shared-budget confound that reviewer [8] raised **only exists for models with a separate
reasoning phase = the Qwen3 thinking roster** (`Qwen3.5:0.8B/4B/9B`, `qwen3.6:35b`). Scoping the
experiment to those models is therefore *more* correct, not a compromise. Gemma's long-output
truncation should be reported separately as its own phenomenon (it is not evidence for/against
decoupling).

> **DECISION A — scope + binding case.** Recommend: run decoupled over the **Qwen3 thinking roster
> only**; pick the worst-truncating *Qwen* think=on cell from sweep5v2 as the headline binding case
> (likely `qwen3.6:35b` or `Qwen3.5:9B` on `validate_plan`/`simulate`). Report Gemma's truncation
> as a separate, non-decoupling observation.
> ANSWER: recommendation accepted. run qwen roster only. report gemma separately

### D2 — Reasoning-parser ↔ stop-string interaction (this is "the risk" the iter-2 plan flagged)
With `--reasoning-parser qwen3` on, the parser **only flushes `reasoning_content` after it sees a
complete `</think>`** (this is the documented `think_overflow_unreachable` gotcha). But we are
*stopping at* `</think>`. Two failure modes:
- `include_stop_str_in_output=False` (default) → the `</think>` is excluded → the parser may never
  see a closed block → `reasoning_content` can come back **empty even on the clean stop case**, and
  we lose the reasoning text needed to build Call 2.
- `finish_reason="length"` (reasoning truncated) → no `</think>` at all → same problem.

Two robust ways out (pick one in the smoke):
1. **Keep parser on, but `include_stop_str_in_output=True`** and reconstruct the reasoning as
   `(reasoning_content or "") + (content or "")` then strip a trailing `</think>`. Concatenating
   both fields is parser-version-proof.
2. **Run the decoupled sweep's vLLM server with the reasoning parser OFF.** Then Call 1's raw
   `content` is the reasoning verbatim (no parser ambiguity), and scoring already strips inline
   `<think>…</think>` (`scoring._THINK_BLOCK_RE`). Cleanest control; removes the risk entirely.
   This is legitimate because the decoupled run is a **new corpus with its own RUN_TAG** (it does
   not need to match the baseline's server flags — the budget mechanism already differs).

> **DECISION B — reasoning-parser handling.** Recommend option 2 (parser OFF for the decoupled
> server) as the primary, with option 1 as the fallback if continuation misbehaves with the parser
> off. Final pick confirmed by the smoke (D3).
> ANSWER: option 2 sounds best.

### D3 — `continue_final_message` + Qwen3 template (must smoke before committing GPUs)
Need to confirm on a real Qwen3 model + vLLM v0.20.2 that, when the final message is an assistant
turn with `continue_final_message=True` / `add_generation_prompt=False`, the template continues the
turn verbatim and does **not** re-inject a `<think>` block or a generation prefix. This is exactly
the "commit GPUs only after a green smoke" gate the iter-2 plan already requires. No decision —
it's a build-time validation step.

### D4 — num_ctx budgeting
Constraint per call: `prompt + THINK_BUDGET ≤ max_model_len` (Call 1) and `prompt + reasoning +
ANSWER_BUDGET ≤ max_model_len` (Call 2, because Call 2 re-feeds the reasoning as prompt). With
`num_ctx=16384`, prompt ~1–2K, `THINK_BUDGET=8192`, `ANSWER_BUDGET=4096`: Call 2 ≈ 2K+8192+4096 ≈
14.3K ✓. `solve` answers may want more headroom.

> **DECISION C — budgets.** Recommend `THINK_BUDGET=8192`, `ANSWER_BUDGET=4096` (non-solve) /
> `6144` (solve), keep `num_ctx=16384` (avoids re-opening the 32K-ctx VRAM/format regression in
> `project_ctx_bump_32k_smoke_failed`). Adjust only if the smoke shows Call-2 overflow.
> ANSWER: accepted.

### D5 — Token accounting / cost honesty
Call 2 re-encodes the reasoning as prompt tokens, so naive summing double-counts. Plan: store the
**decode split** (`think_completion` + `answer_completion`) and Call 1's prompt as the true input;
note that the 2-call design re-encodes reasoning as Call-2 prompt (prefix-cacheable for the
system+user portion). Stored in the existing free-form `tokens` dict — no schema change. Not a
blocker, just a measurement note for the cost paragraph.

### D6 — Grader + storage are prerequisites, not part of this change
- The **Q1 two-metric simulate grader** must land as its **own small PR first** (the decisions doc
  is explicit: "land it as its own small PR before the sweeps, not bundled"). The decoupled change
  is grader-agnostic.
- **Full-response storage**: raise/remove `RESPONSE_SNAPSHOT_LEN` (currently 500) so the decoupled
  corpus is re-gradeable offline. One-line constant change; can ride with the decoupled PR or the
  grader PR.
- For an apples-to-apples *simulate-accuracy* comparison, the baseline sweep5v2 Qwen think=on
  `simulate` cells should be re-graded with Q1 (cheap/offline). Truncation-rate comparison needs no
  re-grade.

> **DECISION D — sequencing.** Recommend: (1) Q1 grader PR → (2) decoupled-budget PR (incl. raise
> `RESPONSE_SNAPSHOT_LEN`) → smoke → (3) gated cluster run. Confirm this order.
> ANSWER: accepted.
> 

> **DECISION E — version tag.** tag current main head as the last version of sweep5v2 so it can be reconstructed later
> after all pr's merged. so we wont loose the sweep5v2 commit.

---

## Scope / files

| File | Action | Description |
|------|--------|-------------|
| `pddl_eval/vllm_client.py` | modify | `chat()` accepts `stop: list[str] \| None` (→ top-level `stop`) and a single `vllm_extra: dict \| None` merged into `extra_body` (carries `continue_final_message` / `add_generation_prompt` / `include_stop_str_in_output`). Small, generic passthrough. |
| `pddl_eval/chat.py` | modify | New `chat_without_tools_decoupled(...)` helper: Call 1 (think, `stop=["</think>"]`) → reconstruct reasoning → Call 2 (continuation, answer). Returns `(answer_text, done_reason_call2, tokens_with_split, thinking_text, think_truncated)`. Reuses `_build_chat_kwargs` + `_response_*` extractors. |
| `pddl_eval/runner.py` | modify | In the no-tools branch, when `decoupled_budget` is set and `think is True`, call the new helper instead of `chat_without_tools`. Thread `num_predict_think` / `num_predict_answer`. Add `think_truncated: bool = False` field to `TaskResult`. Pass Call-2 `done_reason` to the existing `_classify_step_failure`. |
| `run_experiment.py` | modify | CLI: `--decoupled-budget` (flag), `--num-predict-think`, `--num-predict-answer`; thread to `run_single_task_experiment`; print them in the run banner; persist in the run-meta dict. |
| `pddl_eval/runner.py` (const) | modify | Raise `RESPONSE_SNAPSHOT_LEN` (D6) for re-gradeability. |
| `tests/test_*` | create/modify | Unit test the 2-call helper with a fake client (assert budgets, stop, continuation flags, token split, `think_truncated`). |
| `development/CHANGELOG.md` | modify | Dated entry on landing. |
| `development/OPEN_ISSUES.md` | modify | Narrow ISS-024's "(think=on) decoupled budget" clause. |

Methodology guardrail honored: **one knob per corpus**. The decoupled run is a clean A/B against
the sweep5v2 think=on Qwen cells; new `RUN_TAG`; never pooled into `sweep5v2-live`.

## Reproducibility
- Existing results untouched (new corpus, new RUN_TAG, different server config). No re-baseline.
- New CLI flags default OFF → existing reproductions byte-identical.
- Baseline for the comparison = sweep5v2 think=on Qwen cells (already on disk).

## Execution steps (when approved)
1. Branch `paper/iter2-decoupled-budget` off `paper/aaai27` (one-task-one-branch policy).
2. `vllm_client.py`: add `stop` + `vllm_extra` passthrough (+ regression test).
3. `chat.py`: add `chat_without_tools_decoupled` (+ unit test with fake client).
4. `runner.py`: wire the branch, `think_truncated` field, token split, classification.
5. `run_experiment.py`: CLI flags + banner + run-meta.
6. Raise `RESPONSE_SNAPSHOT_LEN`.
7. Local fake-client tests green.
8. **GATED:** single-Qwen smoke on the cluster (resolves D2/D3/D4) — ping before submitting.
9. After green smoke: full decoupled think=on no-tools sweep over the Qwen roster (gated).
10. Aggregate; convert the Limitations hedge → a result; paper writeup in the same PR.

## Validation strategy
- **Unit (local, no GPU):** fake `VLLMClient` returning scripted Call-1/Call-2 responses; assert
  Call 1 carries `stop=["</think>"]` + THINK_BUDGET, Call 2 carries `continue_final_message` +
  ANSWER_BUDGET + the injected think block; assert token split + `think_truncated` on Call-1 length.
- **Smoke (gated, 1 Qwen model, few fixtures/task):** confirm continuation works against the real
  template; confirm answers are non-empty where the shared-budget baseline truncated; lock D2.
- **Result check:** decoupled think=on truncation/`think_overflow` should drop vs the sweep5v2
  baseline while answer completion rises — the headline.

## Documentation
- CHANGELOG entry on landing (files, motivation, compat note: new flags default-off).
- Narrow ISS-024 (the "(think=on) decoupled budget" clause) in OPEN_ISSUES.md.
- Dated bullet in `development/paper_notes_discussions.md` once the result lands.
