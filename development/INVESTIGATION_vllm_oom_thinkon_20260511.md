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

**Recommended combo:** A (exclude) for the immediate fix, plus document the constraint in `lib/defaults.sh` so any future GPU-class addition has to be vetted before getting picked up. Don't reach for C/D yet — they trade off speed/quality for headroom we don't actually need on real rtx_6000.

---

## Failure mode 2 — Qwen3.5:0.8B think-on cells fast-fail at 2s

**Symptom.** Cells `17480288_{6,9}` (the two think-ON 0.8B cells: `on/tools_per-task_minimal` and `on/tools_all_minimal`) failed with `ExitCode 1:0` after ~2 seconds. Too fast for OOM or model-load. Different node (`ise-cpu256-27`, real rtx_6000) — NOT an L40S issue.

The other three 0.8B cells (think-OFF: `off/no-tools`, `off/tools_per-task`, `off/tools_all`) ran fine and accumulated trials. So the failure is specific to **Qwen3.5:0.8B + think=on**.

**Hypothesis to test.** The harness passes `enable_thinking=true` to vLLM via `extra_body.chat_template_kwargs` (see `pddl_eval/vllm_client.py:113-114`):
```python
if think is not None:
    extra_body["chat_template_kwargs"] = {"enable_thinking": bool(think)}
```

Qwen3.5 (vs Qwen3.6) may not support the `enable_thinking` chat-template kwarg, or its chat template may raise on `enable_thinking=True`. The 2-second exit suggests a startup-time chat-template validation failure before the first generation.

**Confirm via:** read the per-cell `.out` files (`17480288_6` and `17480288_9` — file names follow `pddl_rtx_pack2_*-<JOBID>_<TASKID>.out` or similar; sort by mtime in the quarantine dir). The actual error line should pinpoint chat-template rejection vs vLLM-server error vs harness-side exception.

**Also check:** the Qwen3.5 tokenizer's chat template content — `Qwen/Qwen3.5-0.8B`'s `tokenizer_config.json` on HF. If `enable_thinking` isn't a recognised kwarg in the template, vLLM raises on first message format.

**Fix candidates:**

- **A. Gate `enable_thinking` per model family** — only pass it for Qwen3.6+ (or whichever family advertises the thinking template). Add a model-aware check in `pddl_eval/vllm_client.py::chat()` or in the harness's think-axis dispatch.
- **B. Drop think-on for Qwen3.5 in the matrix-gate** — exclude (`Qwen3.5:0.8B`, `on`) cells from the sweep. Methodology-wise this is a finding ("0.8B in this generation doesn't support reasoning trace") more than a workaround.
- **C. Probe an alternative knob** — Qwen3.5 might use a different mechanism (e.g., a system-prompt prefix rather than a template kwarg). HF model card or transformers docs would say.

**Recommended:** read the actual error first. The 2-second exit means the error line is in the .out file — characterise before patching.

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

1. Is there a feature flag in `sinfo -h -N -o '%N %f'` that distinguishes real rtx_6000 from L40S? If yes, prefer `--constraint=<feature>` over `--exclude=ee-l40s-02` (more future-proof).
2. Does the Qwen3.5 chat template raise on `enable_thinking=True`, or does it silently ignore it (in which case the 2s exit is from something else)?
3. Are there OTHER L40S nodes mislabelled as `rtx_6000` in the BGU pool, or just `ee-l40s-02`?
4. Should the `gpu_memory_utilization=0.85` default be lowered to give headroom for future GPU-class additions, or is the per-class exclude policy enough?
5. Should `submit_with_rtx.sh --backend vllm` route different models to different GPU classes (e.g., 0.8B → `rtx_3090:1`, 27B → real `rtx_6000:1`) via the `vllm_lookup` table?
