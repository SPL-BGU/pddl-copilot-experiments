# Decoupled think=on sweep — HANDOFF (2026-06-27)

**For the next agent.** Pick up the in-flight Line-1 decoupled-budget no-tools sweep and take it
through completion → final A/B → (optional) the with-tools parity decision. Read this top-to-bottom
before any cluster action. Companion docs: `decoupled_run_staging.md` (build + decisions),
`decoupled_budget_plan.md`, `q1_grader_plan.md`; memory `project_simulate_grader_artifact`;
ISS-024 in `OPEN_ISSUES.md`.

## TL;DR state

- **Branch:** `paper/iter2-decoupled-run` @ `6007032` (pushed to origin; this is the exact code the
  cluster is running). Local doc commits on top (`611ff87` + this). `sweep5v2-final` tag pins the
  pre-change corpus. **Do NOT push code mid-run** that touches `run_experiment.py`/`pddl_eval/` (a
  9B resubmit re-reads the checkout); doc-only pushes are fine.
- **Smoke = GREEN, Line-1 hypothesis CONFIRMED** (see "Result so far").
- **Full sweep LAUNCHED + RUNNING:** SLURM job **`18426027`** (4-cell array, all 4 Qwens, no-tools,
  think=on, `--decoupled-budget --num-predict-think 8192` answer=per-task, `--reasoning-parser none`,
  `RUN_TAG=decoupled-thinkon`, `--time 48:00:00`). Parser-off verified live.
- **Open decision (user's):** with-tools parity — cheap parser-off+tools smoke vs full re-run (below).
- **`paper/` is OFF-LIMITS** (gather-data-first). Never pool the decoupled corpus into `sweep5v2-live`.

## Result so far (from the `--partial 2` smoke; matched A/B, join on trial `key`)

Decoupled (split budget) vs sweep5v2 think=on baseline (shared budget), no-tools `simulate`:
- **qwen3.6:35b: 0% → 42%** (n=120 complete); empties 54→4; answer-trunc ~17%; Wilson [33,51] vs [0,3] — disjoint.
- **Qwen3.5:9B: 0% → ~25-30%** (n≈100); empties 63→6.
- Validation also lifts (9B validate_domain 3%→43%; empties→0 on all validate_* tasks).
- **`solve` is the honest EXCEPTION** — decoupling does NOT help it (long prompt + 8192 reasoning +
  long plan answer > 16K ctx → Call-2 starved by the CONTEXT CEILING, answer-budget-independent).
- Mechanism = the open-roster simulate 0% floor was substantially **shared-budget reasoning
  starvation**, stacked on the frontier **notation** artifact (`_canon_atom`). Two artifacts.

## Live sweep status @ 2026-06-27 ~09:08 (job 18426027)

Full no-tools cell ≈ **4560 trials** (5 tasks × full fixtures × 3 no-tools variants v11-13).

| cell | model | trials | ~%done | rate | note |
|---|---|--:|--:|--:|---|
| _0 | Qwen3.5:0.8B | 3844 | 84% | ~410/h | finishes ~2h |
| _3 | qwen3.6:35b | 3678 | 81% | ~357/h | finishes ~2-3h |
| _1 | Qwen3.5:4B | 1461 | 32% | ~144/h | ~21h left |
| _2 | Qwen3.5:9B | 885 | 19% | ~87/h | **long pole — projects past 48h wall** |

Turbulence so far (all auto-recovered, no data lost): **2 preemptions + 1 wedge-abort** (0.8B's
vLLM briefly wedged → harness "Aborting cell: 7 consecutive APIConnectionErrors … Resume on rerun" →
requeued, recovered). These are NORMAL on the contended BGU cluster.

## NEXT STEPS (in order)

1. **Monitor `18426027` to completion.** Use `cluster-ops`. Fastest board:
   `bash .claude/skills/cluster-ops/scripts/status.sh --decoupled` (4 Qwens × `on/nt-neut`, dedup'd
   per-cell %/Δ/ETA/watch-list; remote-side only — no result sync). Poll the job STATE with
   `sacct -j 18426027 -X -o State` — **NOT** `squeue`-empty (that false-positives during the frequent
   VPN drops; a dropped SSH returns empty and looks like "done"). Raw per-cell progress = `wc -l` on
   `results/slurm_vllm_<m>_on_no-tools_decoupled-thinkon/trials.jsonl`.
2. **9B will likely TIMEOUT at 48h (~85% done).** When it does, **resubmit to resume** — same wrapper
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
