# Decoupled think=on sweep — HANDOFF (2026-06-27)

**For the next agent.** Pick up the in-flight Line-1 decoupled-budget no-tools sweep and take it
through completion → final A/B → (optional) the with-tools parity decision. Read this top-to-bottom
before any cluster action. Companion docs: `decoupled_run_staging.md` (build + decisions),
`../archive/decoupled_budget_plan.md`, `../archive/q1_grader_plan.md`; memory `project_simulate_grader_artifact`;
ISS-024 in `OPEN_ISSUES.md`.

## TL;DR state

- **Branch:** `paper/iter2-decoupled-run` @ `6007032` (pushed to origin; this is the exact code the
  cluster is running). Local doc commits on top (`611ff87` + this). `sweep5v2-final` tag pins the
  pre-change corpus. **Do NOT push code mid-run** that touches `run_experiment.py`/`pddl_eval/` (a
  9B resubmit re-reads the checkout); doc-only pushes are fine.
- **Smoke = GREEN, Line-1 hypothesis CONFIRMED** (see "Result so far").
- **Full sweep LAUNCHED + RUNNING:** SLURM job **`18426027`** (4-cell array, all 4 Qwens, no-tools,
  think=on, `--decoupled-budget --num-predict-think 8192` answer=per-task, `--reasoning-parser none`,
  `RUN_TAG=decoupled-thinkon`, `--time 48:00:00`). Parser-off verified live. **9B long-pole hit the 48h wall → resubmitted to resume as job `18466812`** (the live job to monitor now).
- **Open decision (user's):** with-tools parity — cheap parser-off+tools smoke vs full re-run (below).
- **`paper/` is OFF-LIMITS** (gather-data-first). Never pool the decoupled corpus into `sweep5v2-live`.

## ✅ LINE COMPLETE — final matched-A/B rollup (2026-07-11)

9B (the last cell) completed clean on **2026-06-29** (job `18466812`, exit `0:0`, 4560/4560).
All 4 Qwen cells synced to `results/decoupled-rollup/` (gitignored) and joined **4560/4560 keys
on both sides, 0 unmatched**. The 3 earlier cells reproduce their per-cell A/Bs exactly (join
validated); 9B is new. Rollup script: **`development/decoupled/decoupled_rollup.py`** (matched
join + Wilson CIs + baseline-simulate Q1-coercibility bound; runs on the synced dirs, no
cluster/MCP needed — re-sync the 8 dirs first if absent).

State-tracking success (`success`, base→dec), decoupled vs sweep5v2 think=on baseline, n=4560/cell:

| model | validate_domain | validate_problem | validate_plan | solve | simulate |
|---|--:|--:|--:|--:|--:|
| Qwen3.5:0.8B | 0.3→48.6 (+48.3✓) | 0.2→27.7 (+27.5✓) | 0.0→4.4 (+4.4✓) | 0.0→0.0 | 0.0→0.0 |
| Qwen3.5:4B   | 0.8→42.5 (+41.7✓) | 11.5→63.2 (+51.7✓) | 25.0→77.1 (+52.1✓) | 15.7→9.7 (🔻−6.0) | 0.0→23.0 (+23.0✓) |
| Qwen3.5:9B   | 3.3→37.8 (+34.4✓) | 17.5→66.0 (+48.5✓) | **21.4→81.4 (+60.0✓)** | 27.0→27.0 (0.0) | 0.0→22.3 (+22.3✓) |
| qwen3.6:35b  | 73.3→80.3 (+6.9) | 77.5→77.2 (−0.3) | 84.8→91.6 (+6.8✓) | 38.3→39.3 (+1.0) | **0.0→40.0 (+40.0✓)** |

(✓ = Wilson 95% CIs disjoint.)

### Findings (consolidated; supersedes the provisional per-cell reads below)

1. **validate lifts are large + Wilson-disjoint for every model with the latent skill.** 9B posts
   the **biggest validate_plan lift of the roster, +60.0pp (21→81)**; 4B +52.1; 35b already high so
   +6.8. Empties are crushed everywhere (validate_* baseline 71–99% empty → ~0).
2. **The solve regression is 4B-ONLY, not a gradient.** solve across sizes: 0.8B 0→0, **4B 15.7→9.7
   (−6.0)**, 9B 27→27 (flat), 35b 38→39 (flat). Decoupling costs solve wins only at *mid*-capability
   (4B has few wins and the fixed 8192-think + long plan answer overruns 16K ctx harder than the
   baseline's adaptive shared budget). Report solve as a **risk at 4B**, not a monotonic decline.
3. **simulate has a mid-PLATEAU, not strict monotonicity.** state-tracking: 0.8B 0 → 4B 23.0 ≈ 9B
   22.3 → 35b 40.0 (4B/9B CIs overlap → tied). Honest shape = **floor → mid plateau (~22–23%) → top
   (40%)**. Drop the earlier "strictly monotonic 0→23→40" phrasing — 9B lands on the 4B plateau.
4. **simulate format-compliance = 0% for ALL four models.** No model ever emits the schema-exact
   `{"trajectory":[…]}` wrapper; every point of state-tracking success is credited by the Q1
   wrapper-tolerant coercion, so **strict (content ∧ format) = 0% across the board.** Clean
   two-metric result: these models can *track state* up to 40% of the time but never in the exact
   requested *format*.
5. **NOT a grader artifact.** baseline simulate state-tracking is ≤0.7% even re-graded under Q1
   (Q1-coercibility upper bound: 0.8B ≤0.7%, 4B/9B ≤0.0%, 35b ≤0.3%; baseline is ~99% truncated/
   empty, so nothing to coerce). Decoupled 22–40% is a real lift, not a pre-Q1-vs-Q1 comparison
   artifact.

### Remaining on this line

- **Only the with-tools parity decision (ISS-024(d), "Open decision" §below) is open** — GATED on
  the user's pick + a green parser-off+tools smoke. Everything else on Line 1 is done.
- `paper/` stays frozen (gather-data-first); this rollup is the **ready-to-fold** answer to the
  simulate sole-source-floor claim once the freeze lifts.

## 📌 PAPER REWRITE — PENDING, for a FRESH session (this session did NOT touch `paper/`)

Decision (2026-07-11, user): fold the decoupled results into the paper, but a **fresh-session
agent does the actual `paper/` rewrite** — this session deliberately left `paper/` untouched.
What the fresh agent must change (numbers: the LINE-COMPLETE table above +
`development/decoupled/decoupled_rollup.py`):

1. **Retract the simulate "sole-source floor" claim.** No-tools simulate 0% was an ARTIFACT
   (grader + shared-budget reasoning starvation), not a capability floor. Report the true
   no-tools baseline = decoupled: 0.8B 0% · 4B 23% · 9B 22% · 35b 40% (state-tracking).
2. **Re-frame the simulate tool-lift apples-to-apples** as decoupled-no-tools (22–40%) →
   with-tools (~87–96%), NOT old-0% → 90%. Lift is still large; the "can't simulate at all"
   framing is wrong.
3. **Two-metric finding:** simulate format-compliance = 0% for every model (strict
   content∧format = 0%); all no-tools state-tracking success is Q1 wrapper-tolerant coercion.
4. **solve caveat:** decoupling is a RISK at mid-capability (4B −6pp); neutral for 9B/35b
   (ctx-ceiling).

## With-tools parity — CONCLUSION (no full re-run; reuse sweep5v2 with-tools)

Q: re-run with-tools under the decoupled apparatus, or would we see no change vs sweep5v2?
A: **No re-run — reuse sweep5v2 with-tools.** Expected change = none, three structural reasons:
(1) `--decoupled-budget` is rejected with tools by construction (no-tools-only); (2) with-tools
has no reasoning starvation to fix — sweep5v2 with-tools think=on already shows `think_overflow=0`
everywhere and simulate 87–96% (9B/35B); (3) the sole apparatus delta (reasoning-parser off in
decoupled vs on in sweep5v2) governs `<think>`/answer separation in the no-tools TEXT path only —
with-tools answers are TOOL CALLS, extracted + graded independent of the reasoning parser.
**Apples-to-apples insurance (cheap):** parser-off + tools smoke (1–2 Qwens, `--partial`,
think=on), diff vs the matching sweep5v2 with-tools cells. Matches (expected) → sweep5v2 with-tools
is the apparatus-validated comparison arm, cite it. Diverges → full re-run. Same as ISS-024(d);
GATED on user + a green smoke.

## With-tools GRADING-SURFACE caveat — PROVEN (2026-07-11); the paper must state it

**With-tools success is graded on the TOOL CALL RESULT, not the model's final answer.** Proof
(`pddl_eval/scoring.py` `check_success`): the with-tools branches read the tool's own output via
`_get_tool_results` / `tc.get("result")` — validate_\* `:528-536`, solve `:473-492`, simulate
`:575-583`; helper `_get_tool_results` `:74` returns `tc["result"]` verbatim. The model `response`
is read ONLY in the no-tools fallback paths (`:497-498`, `:544-548`, `:596`). So with-tools success
= *"right tool selected AND the tool (on the model's args) returned the ground-truth answer"*, NOT
*"the model correctly conveyed that answer"*.

Empirical size of the gap (validate_\*, sweep5v2 with-tools successes; repro:
`development/decoupled/with_tools_grading_surface_probe.py`):

| | 35b (n=7812) | 4B (n=6075) |
|---|--:|--:|
| model restates the tool verdict (faithful) | 63.6% | 60.3% |
| model states a **contradictory** verdict | **0.0%** | **0.0%** |
| model states **no checkable verdict** (credited on the tool alone) | 36.4% | 39.7% |
| — of which completed yet silent (`done_reason=stop`) | 28.9% | 17.3% |
| — of which truncated (`done_reason=length`) | 7.4% | 22.5% |

**Implications for the paper rewrite:**
- **No-tools grades the model's OWN answer; with-tools grades the TOOL's answer** — a different,
  more generous surface. With-tools numbers are a **tool-selection + faithful-invocation** metric,
  NOT a strict end-to-end answer metric. The tool-lift claim must say so; do not read with-tools
  success as "the model produced the right final answer".
- **Models never *misreport* the tool (0% contradiction)** — the deviation is *under-specification*
  (≈29% of 35b successes complete without ever stating a checkable conclusion), not error.

**PROPOSED, deferred to a fresh session (per user, to discuss — do NOT build yet):** add a
secondary **end-to-end with-tools** metric that ALSO requires the model's final `response` to match
ground truth (grade `response` via the no-tools path), quantifying the interpretation gap. Fully
offline-computable — `response` + `tool_calls[].result` are both stored — so no re-run needed.

## Result so far (from the `--partial 2` smoke; matched A/B, join on trial `key`)

Decoupled (split budget) vs sweep5v2 think=on baseline (shared budget), no-tools `simulate`:
- **qwen3.6:35b: 0% → 42%** (n=120 complete); empties 54→4; answer-trunc ~17%; Wilson [33,51] vs [0,3] — disjoint.
- **Qwen3.5:9B: 0% → ~25-30%** (n≈100); empties 63→6.
- Validation also lifts (9B validate_domain 3%→43%; empties→0 on all validate_* tasks).
- **`solve` is the honest EXCEPTION** — decoupling does NOT help it (long prompt + 8192 reasoning +
  long plan answer > 16K ctx → Call-2 starved by the CONTEXT CEILING, answer-budget-independent).
- Mechanism = the open-roster simulate 0% floor was substantially **shared-budget reasoning
  starvation**, stacked on the frontier **notation** artifact (`_canon_atom`). Two artifacts.

## Completed cell — Qwen3.5:0.8B FINAL A/B (2026-06-27; first cell done, 4560/4560)

Matched A/B (join on trial `key`), decoupled vs sweep5v2 think=on baseline, all 5 tasks, n=4560.
Grader confound is **immaterial here**: the 0.8B baseline simulate was genuinely empty (293/300
`truncated_no_answer`, only 0.7% Q1-coercible), not a grader artifact — so `success` is honest.

| task | baseline | decoupled | impact |
|---|--:|--:|:--|
| validate_domain  | 0.3% | **48.6%** | ⬆️ +48.3pp (Wilson disjoint) |
| validate_problem | 0.2% | **27.7%** | ⬆️ +27.5pp (Wilson disjoint) |
| validate_plan    | 0.0% | 4.4%      | ⬆️ +4.4pp (small; 92.6% answer-trunc throttles it) |
| solve            | 0.0% | 0.0%      | ➖ no change (ctx-ceiling exception) |
| simulate         | 0.0% | 0.0%      | ➖ no change (empties 97.7%→10% but 70% `result_mismatch`) |

- **No regression on any task; improvement on three.** Empties/parse-errors crushed everywhere
  except solve (e.g. simulate 97.7%→10% empty, validate_* 99%→~0%) — the expected
  output-erroring/parsing fix landed.
- Accuracy lift is **capability-gated**: it converts to `success` only where 0.8B has the latent
  skill (the two validate tasks). simulate/solve stay 0% — decoupling buys a non-empty *wrong*
  answer, not a right one, on the tasks past this model's capability floor.

> **Cross-model status.** The 0.8B verdict above does NOT generalize — see the 35b cell below,
> which behaves oppositely on simulate. 9B/4B are still in flight (NEXT STEPS §3); story stays OPEN
> for them.

## Completed cell — qwen3.6:35b FINAL A/B (2026-06-27; second cell done, 4560/4560)

Matched A/B (join on trial `key`), decoupled vs sweep5v2 think=on baseline, all 5 tasks, n=4560.

| task | baseline | decoupled | impact |
|---|--:|--:|:--|
| **simulate**     | 0.0%  | **40.0%** | ⬆️ **+40.0pp** (Wilson disjoint [0,1.3] vs [34.6,45.6]) |
| validate_plan    | 84.8% | 91.6%     | ⬆️ +6.8pp (Wilson disjoint) |
| validate_domain  | 73.3% | 80.3%     | ⬆️ +6.9pp (CIs marginally touch) |
| validate_problem | 77.5% | 77.2%     | ➖ flat (−0.3pp = 2 trials, noise) |
| solve            | 38.3% | 39.3%     | ➖ flat (+1.0pp; ctx-bound) |

- **CONFIRMS the smoke prediction**: simulate 0→40% at full N (smoke said 0→42%). **No regression** on
  any task; three improve. The simulate lift is honest — the baseline is ~0% under *either* grader
  (only 0.3% of baseline simulate responses are Q1-coercible — truncated/non-JSON), so it is not a
  grader artifact. Decoupling crushed simulate empties **48.7%→8.3%**; Q1 wrapper-tolerance then
  credits the 120 coercible-but-correct trajectories (the model never emits the exact wrapper —
  0% format-compliant — yet gets the *content* right 40% of the time).
- **solve stays ctx-bound**: decoupled answer-truncation actually *rose* 22%→39% (8192 think + long
  plan answer overruns the 16K window), yet success held flat — the ctx-ceiling exception, now at a
  capable model.

**Cross-model (the clean mechanism).** Same intervention, opposite simulate outcomes →
decoupling does not *create* capability, it *unmasks* it:

| model | simulate | validate_plan | read |
|---|--:|--:|---|
| Qwen3.5:0.8B | 0% → **0%**  | 0% → 4%   | too weak — budget buys a *wrong* answer |
| Qwen3.5:4B   | 0% → **23%** | 25% → 77% | mid — lifts everywhere but solve *regresses* |
| qwen3.6:35b  | 0% → **40%** | 85% → 92% | capable — budget *unmasks* real skill |

simulate rises **monotonically with capability** (0 → 23 → 40), confirming decoupling *unmasks*
latent skill rather than creating it. 0.8B is the control (no skill to recover); 35b is the positive
case; 4B is the middle of the curve (see its cell below — and the **first solve regression**). Only
9B is left (in flight; ~58% as of 2026-06-28, resumed under `18466812`).

## Completed cell — Qwen3.5:4B FINAL A/B (2026-06-28; third cell done, 4560/4560)

Matched A/B (join on trial `key`), decoupled vs sweep5v2 think=on baseline, all 5 tasks, n=4560.

| task | baseline | decoupled | impact |
|---|--:|--:|:--|
| validate_plan    | 25.0% | **77.1%** | ⬆️ **+52.1pp** (Wilson disjoint) |
| validate_problem | 11.5% | **63.2%** | ⬆️ **+51.7pp** (Wilson disjoint) |
| validate_domain  | 0.8%  | **42.5%** | ⬆️ **+41.7pp** (Wilson disjoint) |
| simulate         | 0.0%  | **23.0%** | ⬆️ +23.0pp (Wilson disjoint [0,1.3] vs [18.6,28.1]) |
| **solve**        | 15.7% | 9.7%      | 🔻 **−6.0pp REGRESSION** |

- **Four big lifts, one regression.** The validate tasks get the *largest* lifts of any model
  (+42 to +52pp) — 4B is the budget-starved-but-capable sweet spot (baseline 69–97% empty on those).
  simulate +23pp sits between 0.8B (0%) and 35b (40%), confirming the capability gradient.
- **⚠️ FIRST REGRESSION: solve 15.7%→9.7%** (47→29 of 300). Mechanistic, not noise — decoupled
  empties/truncation *rose* 83.3%→89.7% (~19 more trials truncate, matching the ~18 lost wins). The
  fixed 8192 think + long plan answer overruns the 16K ctx harder than the baseline's adaptive shared
  budget, so on solve decoupling *costs* the few wins 4B had. CIs marginally touch ([12.0,20.2] vs
  [6.8,13.5]) but the truncation mechanism corroborates a real effect. **This breaks the
  "no regression anywhere" property** that held for 0.8B and 35b: solve is not just the ctx-ceiling
  "no-help" case — for a mid-size model it is a net loss. Report solve as a decoupling *risk*, not a
  neutral exception.
- 4B decoupled simulate also shows high `format_parse_fail` (102/300 = 34% — non-JSON output), which
  caps the simulate lift; empties were crushed 91%→10% but a third of the output isn't coercible.

## Live sweep status @ 2026-06-28 (orig array `18426027`; 9B resumed as `18466812`)

Full no-tools cell ≈ **4560 trials** (5 tasks × full fixtures × 3 no-tools variants v11-13).

| cell | model | trials | ~%done | note |
|---|---|--:|--:|---|
| _0 | Qwen3.5:0.8B | 4560 | **100% ✓ DONE** | final A/B above (simulate flat) |
| _3 | qwen3.6:35b | 4560 | **100% ✓ DONE** | final A/B above (simulate 0→40%) |
| _1 | Qwen3.5:4B | 4560 | **100% ✓ DONE** | final A/B above (simulate 0→23%; **solve −6pp regression**) |
| _2 → `18466812` | Qwen3.5:9B | 4560 | **100% ✓ DONE** | completed 2026-06-29 (exit `0:0`); final A/B in the LINE-COMPLETE §above |

Use `bash .claude/skills/cluster-ops/scripts/status.sh --decoupled` for the live board.

Turbulence so far (all auto-recovered, no data lost): **2 preemptions + 1 wedge-abort** (0.8B's
vLLM briefly wedged → harness "Aborting cell: 7 consecutive APIConnectionErrors … Resume on rerun" →
requeued, recovered). These are NORMAL on the contended BGU cluster.

## NEXT STEPS (in order)

1. **Monitor `18466812` (the resumed 9B long pole; the other cells ran under the original array `18426027`) to completion.** Use `cluster-ops`. Fastest board:
   `bash .claude/skills/cluster-ops/scripts/status.sh --decoupled` (4 Qwens × `on/nt-neut`, dedup'd
   per-cell %/Δ/ETA/watch-list; remote-side only — no result sync). Poll the job STATE with
   `sacct -j 18466812 -X -o State` — **NOT** `squeue`-empty (that false-positives during the frequent
   VPN drops; a dropped SSH returns empty and looks like "done"). Raw per-cell progress = `wc -l` on
   `results/slurm_vllm_<m>_on_no-tools_decoupled-thinkon/trials.jsonl`.
2. **9B hit the 48h wall (~85% done) and was resubmitted to resume as job `18466812`.** If `18466812` also walls, **resubmit again** — same wrapper
   command, it resumes from `trials.jsonl`:
   ```
   ssh slurm "cd ~/pddl-copilot-experiments && bash cluster-experimenting/submit_with_rtx.sh Qwen3.5:9B \
       --no-tools --think-modes on --decoupled-budget --num-predict-think 8192 \
       --reasoning-parser none --run-tag decoupled-thinkon --time 48:00:00"
   ```
   (Consider `scontrol Nice` to de-prioritize nothing / or just let it run; preemption is the main risk.)
3. **On full completion → the final matched A/B** (this is the deliverable). For all 4 Qwens × all 5
   tasks, compare decoupled vs the sweep5v2 think=on baseline:
   - decoupled dirs: `results/slurm_vllm_<m>_on_no-tools_decoupled-thinkon/trials.jsonl`
   - baseline dirs:  `results/slurm_vllm_<m>_on_no-tools_sweep5v2/trials.jsonl`
   - **Join on the top-level trial `key`**; fields live under `result.{task, success, done_reason,
     think_truncated, response, failure_reason, format_compliant, ...}`.
   - Report the **3 Q1 numbers** (state-tracking = `success`; format-compliance = `format_compliant`;
     strict = both) + `think_truncated` rate, per cell. The decoupled trials are ALREADY Q1-graded
     (Q1 is the live grader on this branch). For apples-to-apples secondary metrics, **re-grade the
     sweep5v2 `simulate` baseline cells with Q1 offline** (`tools/claude_api_batch.py`-style or the
     live `check_success`) since they were graded pre-Q1.
   - Headline: simulate 0%→~30-42% across models; empties crushed; `solve` = ctx-ceiling exception;
     **Gemma reported SEPARATELY** (excluded — no `<think>`; its think=on truncation is plain
     long-output, not a decoupling case). Use the `analyzer` skill for the master table + Wilson CIs.
   - The exact join logic (reusable) is embedded at the bottom of this doc.
4. **Then the open with-tools decision** (below).

## Open decision — with-tools parity (user wants the tools arm "as similar as possible")

Evidence gathered (do NOT re-derive): decoupling is **no-tools-only by construction** (`run_experiment.py`
rejects `--decoupled-budget` with tools; `runner.py:381 if with_tools:` precedes the decoupled branch →
unreachable for tools; with-tools simulate is graded on the `get_state_transition` TOOL result, not
model-generated text). sweep5v2 with-tools think=on already shows **think_overflow=0 everywhere** and
simulate 87-96% (9B/35B) — no starvation to fix. The ONLY apparatus delta vs the decoupled no-tools
arm is the **reasoning parser (sweep5v2=on, decoupled=off)**, which is independent of tool-call
extraction → should be immaterial. Logged as **ISS-024(d)** future-work.
**Recommendation:** run a cheap **parser-off + tools** smoke (1-2 Qwens, `--partial`, think=on) and
compare to the matching sweep5v2 cells; if it matches, reuse sweep5v2 with-tools as the
apparatus-validated comparison arm (no multi-day re-run). Only if it diverges → full 4-cell re-run.
**GATED** — needs the user's pick + a green smoke before any full submit.

## Cluster access notes

- `ssh slurm` → user `omereliy`, login `slurm-login-0X.auth.ad.bgu.ac.il` (round-robin). Key is in
  the cluster's authorized_keys (registered via `ssh-copy-id` 2026-06-26); `ssh-add` the laptop key
  if the agent is empty.
- **The VPN/link is FLAKY** — it dropped for hours overnight (TCP timeout on :22, not auth). Don't
  hammer; back off. The sweep runs autonomously and resumes regardless of the laptop link.
- Repo on cluster: `~/pddl-copilot-experiments` on branch `paper/iter2-decoupled-run` @ `6007032`.
  Run all submits/git from there (sbatch output paths are cwd-relative).
- One wrapper invocation per cluster step; `cluster-ops` for queue/submit/sync, `analyzer` for tables.

## Embedded final-A/B join (reusable — run via `ssh slurm "cd ~/pddl-copilot-experiments && python3 -" < this`)

```python
import json, collections
def load(path):
    out = {}
    for ln in open(path):
        ln = ln.strip()
        if not ln: continue
        rec = json.loads(ln); k = rec.get('key'); k = tuple(k) if isinstance(k, list) else k
        out[k] = rec.get('result', rec)
    return out
def empty(r): return not (r.get('response') or '').strip()
for disp, m in [('Qwen3.5:0.8B','Qwen3_5_0_8B'),('Qwen3.5:4B','Qwen3_5_4B'),('Qwen3.5:9B','Qwen3_5_9B'),('qwen3.6:35b','qwen3_6_35b')]:
    try:
        D = load('results/slurm_vllm_%s_on_no-tools_decoupled-thinkon/trials.jsonl' % m)
        B = load('results/slurm_vllm_%s_on_no-tools_sweep5v2/trials.jsonl' % m)
    except FileNotFoundError as e:
        print(disp, 'missing', e); continue
    common = [k for k in D if k in B]
    bytask = collections.defaultdict(list)
    for k in common: bytask[D[k].get('task')].append(k)
    print('\n====', disp, '(matched', len(common), ') ====')
    for t in sorted(bytask, key=lambda x:(x or '')):
        ks = bytask[t]; d=[D[k] for k in ks]; b=[B[k] for k in ks]; n=len(ks)
        c = lambda rs,p: sum(1 for r in rs if p(r))
        print('  %-16s n=%-4d  base succ=%-4d empty=%-4d | dec succ=%-4d empty=%-4d trunc=%-4d overthink=%-4d'
              % (t, n, c(b,lambda r:r.get('success') is True), c(b,empty),
                 c(d,lambda r:r.get('success') is True), c(d,empty),
                 c(d,lambda r:r.get('done_reason')=='length'), c(d,lambda r:r.get('think_truncated') is True)))
```
