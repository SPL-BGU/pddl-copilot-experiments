# Investigation handoff — vLLM sweep 17480288 failed, two distinct modes (2026-05-11)

**Status:** broken. Array 17480288 was cancelled and its artifacts moved to a quarantine directory (see paths below). Two distinct failure modes need to be characterised + fixed before the next vLLM sweep can be submitted.

**Branch:** `main` @ `9ce4ad2` (PR #58 already merged — production sbatch + smoke parser fix + context-overflow retry + safety bump to 32 + prefix-caching pin all live on main).

**Models in scope:** `qwen3.6:27b` (5 cells) + `Qwen3.5:0.8B` (5 cells). Matrix per model: `on×{tools_per-task, tools_all}` + `off×{no-tools, tools_per-task, tools_all}` = 5 cells × 2 models = 10 cells.

---

## Failure mode 1 — qwen3.6:27b OOM on L40S nodes

**Symptom.** 3 of 5 qwen27 cells (`17480288_{2,3,4}`) failed with `ExitCode 3:0` during vLLM startup. The preserved serve logs show:

```
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 20.00 MiB.
GPU 0 has a total capacity of 44.39 GiB of which 11.31 MiB is free.
```

Crash site: `_initialize_kv_caches` in `vllm/v1/engine/core.py:128`. Model weights loaded fine (19.05 GiB); the OOM is at KV cache pre-allocation. vLLM never reached `Application startup complete`.

**Root cause.** SLURM's `rtx_6000` GRES label is **shared between two physical GPU classes** at BGU CIS:
- Real `rtx_6000` Ada: 48 GiB visible (worked in smoke 17461801 on `ise-cpu256-08`)
- `ee-l40s-02` (L40S): **44.39 GiB visible** (where 17480288_{2,3,4} landed)

The 3.6 GiB visible-memory delta is the difference between fitting and OOM. Combined with two recent config changes that tightened the budget:

1. **`8a7c1e8` pinned `--enable-prefix-caching`** (vs the smoke baseline 17461801 which ran without prefix caching). APC pre-reserves KV blocks for prefix-hit reuse, on top of the standard KV cache.
2. **`gpu_memory_utilization=0.85`** — at 0.85 of 44.39 GiB, KV-cache headroom after weights is ~15 GiB instead of the smoke's ~25 GiB.

**Confirm via:** `scontrol show node ee-l40s-02 | grep -E 'Features|Gres'` → `AvailableFeatures=l40s` while `Gres=gpu:rtx_6000:8` (the mislabel).

**Fix candidates (evidence-driven):**

- **A. `--exclude=ee-l40s-02`** in the production sbatch — cheapest, surgical. Need to verify there are no OTHER L40S-as-rtx_6000 nodes (search via `sinfo -h -N -o '%N %f' | grep l40s`).
- **B. `--constraint=<feature>`** — only if a feature flag exists for "real rtx_6000". Check `sinfo -h -N -o '%N %f'`. If real rtx_6000 nodes carry a feature like `rtx_6000_ada` while L40S carries `l40s`, constraint is the cleanest filter.
- **C. Lower `gpu_memory_utilization` 0.85 → 0.78** — defense in depth; works on both 44 and 48 GiB GPUs. Costs throughput on real rtx_6000 (smaller KV cache → fewer concurrent sequences).
- **D. Drop `--enable-prefix-caching`** — reverts the `8a7c1e8` pin. Restores the smoke-baseline behaviour. Loses the prefix-caching win on shared `{domain}` prefixes across the 5 tasks.

**Chosen fix (2026-05-11): B (`--constraint=rtx_6000`).**

Live `sinfo -h -N -o '%N %f %G'` confirms both L40S nodes carry the `l40s` feature while every real rtx_6000 node carries `rtx_6000`:
```
cs-6000-{01..04}      gpu,rtx_6000   gpu:rtx_6000:8
cs-cpu256-01          gpu,rtx_6000   gpu:rtx_6000:1
ee-l40s-{01,02}       gpu,l40s       gpu:rtx_6000:8     ← mislabel
ise-6000-{01..07}     gpu,rtx_6000   gpu:rtx_6000:8
…
```

`--constraint=rtx_6000` is strictly stronger than `--exclude=ee-l40s-02`:
1. Covers BOTH `ee-l40s-{01,02}`, not just the one we observed land today.
2. Future-proof: any new GPU class that gets a `gpu:rtx_6000:N` GRES mislabel without the `rtx_6000` feature is filtered out automatically.
3. Self-contained — lives in the sbatch header (one line) with no operator memory required.

Implementation: add `#SBATCH --constraint=rtx_6000` to `run_condition_vllm_rtx.sbatch` (vLLM path only; Ollama path defaults to `rtx_pro_6000` which is unaffected). Defense-in-depth knobs C/D remain available if a future real-rtx_6000 OOM appears.

---

## Failure mode 2 — `/scratch` exhaustion on `ise-cpu256-27` (think-on hypothesis FALSIFIED)

**Updated 2026-05-11 after reading the per-cell .out evidence — original hypothesis (Qwen3.5 chat-template kwarg) is wrong.**

**Symptom.** Cells `17480288_{6,9}` failed with `ExitCode 1:0` after ~2 seconds on `ise-cpu256-27` (real rtx_6000 node, NOT L40S). Verbatim error from both:

```
mkdir: cannot create directory '/scratch/omereliy/<JOBID>/vllm-work': No space left on device
```

Source: `cluster-experimenting/logs/_dirty_2026-05-11_vllm/pddl_rtx_pack2_qwen3_6_27b_vllm-17480300.out` (IDX=6, on/tools_all_minimal) and `pddl_rtx_pack2_qwen3_6_27b_vllm-17480288.out` (IDX=9, off/tools_all_minimal).

**Falsifying observations vs the original "think-on" hypothesis.**

1. **The two failing cells span think∈{on, off}**, not a single think value. Per `17480288.cells.tsv`: IDX=6 is `Qwen3.5:0.8B|on|tools_all_minimal`, IDX=9 is `Qwen3.5:0.8B|off|tools_all_minimal`.
2. **The other think-on 0.8B cell (IDX=5 = on/tools_per-task) did NOT fast-fail** — it ran for 25:56 before being cancelled by the operator (on `ee-l40s-02`). If the chat-template kwarg were rejected, IDX=5 would have failed identically.
3. **The 2s exit is sub-startup** — vLLM cold-load for 0.8B is ~30-60s. Failing at 2s means we never reached `apptainer exec`, let alone the chat-template path.
4. **The error line is `mkdir`, not Python.** Comes from bash, not from vLLM or the harness.

**Root cause.** `cluster-experimenting/run_condition_vllm_rtx.sbatch:82-95` resolves `WORK="$SCRATCH_BASE/vllm-work"` only when the bare `mkdir -p "$SCRATCH_BASE"` succeeds. But `mkdir -p` on an EXISTING (or otherwise empty) directory entry returns 0 even when the underlying filesystem is full; the very next `mkdir -p "$WORK/hf-cache"` then fails with `ENOSPC`, and `set -eo pipefail` aborts the script with exit 1 before the trap can fire.

`ise-cpu256-27` had `/scratch` exhausted at the time array tasks 6 and 9 landed there. The fallback-to-`/tmp` branch never engaged because the first mkdir succeeded misleadingly.

**Fix.** Atomicize the writability test — try `mkdir -p` on the FULL target path (`$SCRATCH_BASE/vllm-work/hf-cache`) inside the test, and fall back to `/tmp` if any step fails. This catches both "base unwritable" and "base creatable, deeper levels fail (ENOSPC)" in one branch.

```bash
# Proposed replacement for run_condition_vllm_rtx.sbatch:82-95
WORK=""
SCRATCH_BASE="/scratch/${SLURM_JOB_USER:-$USER}/${SLURM_JOB_ID:-$$}"
if mkdir -p "$SCRATCH_BASE/vllm-work/hf-cache" 2>/dev/null; then
    export SLURM_SCRATCH_DIR="$SCRATCH_BASE"
    WORK="$SCRATCH_BASE/vllm-work"
else
    echo "Note: $SCRATCH_BASE unwritable or out of space, falling back to /tmp"
    WORK="/tmp/vllm-${SLURM_JOB_ID:-$$}"
    mkdir -p "$WORK/hf-cache" || { echo "ERROR: cannot create $WORK/hf-cache on /tmp either"; exit 1; }
fi
cd "$WORK"
```

**Why this is the right fix (vs node-exclude).** `ise-cpu256-27`'s `/scratch` exhaustion is a node-side condition (likely a leak from a prior job's epilog). Excluding the node permanently is overkill — we want graceful degradation on transient operator-side conditions. The `/tmp` fallback already existed for unwritable-base; we're just closing a hole where ENOSPC slips past the gate.

**Does NOT change response shape.** This fix only affects where the model weights are cached on local disk; the wire format, model, sampling, and chat-template paths are untouched. No fresh `slurm_vllm_*` namespace required if all that changes is scratch routing.

---

## Quarantine paths (on the cluster)

The cancel-and-clean step preserved EVERY artifact from today's failed vLLM sweeps under quarantine dirs (NOT `rm -rf`d):

**Results corpora** — `results/_dirty_2026-05-11_vllm/`
- Contains all `slurm_vllm_*` dirs from today's arrays (`17478276`, `17478449`, `17478468`, `17478499`, `17478753`, `17480288`)
- Each subdir has its `trials.jsonl` with the raw responses, including the BadRequestError exceptions from pre-safety-bump trials

**Logs** — `cluster-experimenting/logs/_dirty_2026-05-11_vllm/`
- All `*-vllm-*.log` files (vLLM serve logs, preserved by the sbatch's `preserve_serve_logs` trap)
- All `pddl_*vllm*-*.out` files (SLURM stdout, one per array task)
- All `*.cells.tsv` manifests for today's array job IDs
- `sacct_snapshot.tsv` — full sacct dump of all today's job IDs with State/ExitCode/NodeList/ReqTRES

Pre-2026-05-11 Ollama corpora and verified smoke probes (`results/smoke/probe_vllm_*`) were NOT touched.

---

## Useful commands

### Find the 27B OOM lines
```bash
grep -nH "OutOfMemoryError\|CUDA out of memory" \
  cluster-experimenting/logs/_dirty_2026-05-11_vllm/*vllm*qwen3_6_27b*.log
```

### Find the 0.8B think-on 2s-exit error
```bash
# the JOBID for 17480288_6 and _9 — find via sacct snapshot
awk -F$'\t' '$1 ~ /17480288_(6|9)$/' \
  cluster-experimenting/logs/_dirty_2026-05-11_vllm/sacct_snapshot.tsv
# then tail the matching .out file (mtime sort + grep job ID)
ls -t cluster-experimenting/logs/_dirty_2026-05-11_vllm/pddl_*vllm*-*.out \
  | head -20
```

### Check which nodes are L40S vs real rtx_6000
```bash
sinfo -h -N -o '%N %f %G' | grep -E 'rtx_6000|l40s'
scontrol show node ee-l40s-02 | grep -E 'Features|Gres|RealMemory'
```

### Inspect the chat template on Qwen3.5
```bash
python3 - <<'PY'
from transformers import AutoTokenizer
t = AutoTokenizer.from_pretrained("Qwen/Qwen3.5-0.8B")
print("--- chat_template (first 2KB) ---")
print(t.chat_template[:2000] if t.chat_template else "<none>")
print("\n--- supports enable_thinking? ---")
print("enable_thinking" in (t.chat_template or ""))
PY
```

### Reproduce the 27B OOM locally (sanity)
```bash
# On a node with rtx_6000:1 — confirm whether it's real or L40S
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
# real rtx_6000 prints "NVIDIA RTX 6000 Ada Generation, 49140 MiB"
# L40S prints "NVIDIA L40S, 46068 MiB" (or similar with ~44 GiB visible)
```

### sacct one-liner for full failure record
```bash
sacct -j 17478276,17478449,17478468,17478499,17478753,17478812,17480288 \
  --format=JobID,JobName%40,State,ExitCode,NodeList%25,Elapsed,ReqTRES%60 -P
```

### Verify the patched client is on the cluster
```bash
grep -nH "_CTX_RETRY_SAFETY" pddl_eval/vllm_client.py
# Expected: line ~77 → _CTX_RETRY_SAFETY = 32
```

### Submit one cell for a minimal repro (single 27B think-off no-tools)
```bash
# After diagnosing the fix, smoke ONE 27B cell with the candidate constraint
sbatch --exclude=ee-l40s-02 \
  --export=ALL,CELLS_LIST='qwen3.6:27b|off|no-tools',CONCURRENCY=4 \
  cluster-experimenting/run_condition_vllm_rtx.sbatch
```

### Submit one cell for 0.8B think-on repro
```bash
# Same idea — single (0.8B, on, no-tools) to isolate the think-on bug
sbatch --export=ALL,CELLS_LIST='Qwen3.5:0.8B|on|no-tools',CONCURRENCY=4 \
  cluster-experimenting/run_condition_vllm_rtx.sbatch
```

---

## Context the new agent must respect

- **Branch is `main` @ `9ce4ad2`.** All vLLM consolidation work (PR #58) is merged. Don't re-stack patches on the consolidated branch — make a fresh branch off main.
- **`_CTX_RETRY_SAFETY = 32`** is the post-bump value. Drift was empirically +9 tokens. Don't lower it without re-measuring.
- **Cluster username is `omereliy`** (short form), `$HOME=/home/omereliy`. Laptop uses `omereliyahu`.
- **Methodology**: corpus identity is load-bearing. Don't commingle pre- and post-fix trials in one `trials.jsonl`. If the fix changes response shape, a fresh `slurm_vllm_<model>_<think>_<cond>/` namespace or a hard `rm` before resubmit is required.
- **Open issues**: `ISS-003` (0.6B "name-as-content" bug) was empirically reproduced on **0.8B + vLLM + qwen3_xml** during today's runs — 8 hits in the 290-trial 0.8B pre-fix corpus. Worth carrying into the eventual paper writeup; do NOT open a new ISS — `feedback_tool_adherence_is_data.md` says these are findings not harness bugs.
- **Don't touch** `results/smoke/probe_vllm_*` (verified pre-2026-05-11 smokes — those are reference data). Also do NOT touch Ollama production corpora (`results/slurm_qwen3_6_*`, `results/slurm_gemma4_31b_*` etc.).
- **Reasoning parser**: Qwen3.5/3.6 use `qwen3_xml` for tool-call + `qwen3` for reasoning. Confirmed by smoke 17461801 (27B) and 17468315 (35B). Gemma-4 needs `REASONING_PARSER=none` per the smoke-parser fix landed today.

---

## Open questions for the new agent to resolve

1. ~~Is there a feature flag in `sinfo -h -N -o '%N %f'` that distinguishes real rtx_6000 from L40S?~~ **Resolved 2026-05-11**: yes, `rtx_6000` vs `l40s`. `--constraint=rtx_6000` adopted.
2. ~~Does the Qwen3.5 chat template raise on `enable_thinking=True`~~ **Resolved 2026-05-11**: irrelevant — the 2s exit was `mkdir: No space left on device` on `/scratch` of `ise-cpu256-27`, not a chat-template error. See "Failure mode 2" above for the falsifying evidence.
3. ~~Are there OTHER L40S nodes mislabelled as `rtx_6000`?~~ **Resolved 2026-05-11**: yes — `ee-l40s-01` AND `ee-l40s-02`. Both filtered by `--constraint=rtx_6000`.
4. Should the `gpu_memory_utilization=0.85` default be lowered to give headroom for future GPU-class additions, or is the per-class constraint policy enough? **Decision deferred**: constraint policy is currently sufficient. Revisit if a future real-rtx_6000 OOM appears or if BGU adds another mislabelled class.
5. Should `submit_with_rtx.sh --backend vllm` route different models to different GPU classes? Still open — not blocking the current sweep.
6. **NEW**: Is `ise-cpu256-27`'s `/scratch` exhaustion recurring (operator should clean) or a one-off? Worth a ping to cluster IT if it reappears. The fallback-to-`/tmp` patch makes us robust either way.
