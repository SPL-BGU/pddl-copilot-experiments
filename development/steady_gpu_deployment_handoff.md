# Steady-GPU sweep7 — STATUS & RESUME handoff (2026-06-17)

Single source of truth for the RunPod H200 BF16 `sweep7` run. Supersedes the old
`steady_gpu_runbook.md` + `gpu_rental_signup_runbook.md` (deleted 2026-06-17;
recoverable via git history). Turnkey env rebuild = `steady-gpu/VENV_RECIPE.md`.

## What this run is
Re-run the single-tool sweep5v2 experiment on **Qwen3.6-35B in clean BF16**
(`Qwen/Qwen3.6-35B-A3B`) on a rented RunPod H200-141GB, as a fresh corpus tagged
**`sweep7`**. Config-identical to the cluster's AWQ run — only the weights (BF16,
not AWQ-INT4) and the host differ. Driver: `steady-gpu/run_steady_gpu.sh`.

## The box
- Pod `f3nb15rlb2e0mi` (name `resulting_amber_monkey`), 1×H200-141GB, ~$4.39/hr.
- Image `runpod/pytorch:1.0.2-cu1281-torch280-ubuntu2404` → driver 570.195.03 = **CUDA 12.8 max**.
- `/workspace` = 180GB volume (persists across stop/start): holds both repo clones
  (`feat/steady-gpu-deployment`), the `.venv`, and the 68GB weights at `/workspace/hf-cache`.

## SSH (off-BGU only — BGU firewalls RunPod)
- Alias `runpod-sweep7` in `~/.ssh/config` → `root@157.66.255.19 -p 13250 -i ~/.ssh/runpod_ed25519`.
- ⚠️ **The exposed-TCP port changes on every stop/start.** Re-fetch after any restart:
  `runpodctl pod get f3nb15rlb2e0mi -o json`  → read `ssh.ip` / `ssh.port`, update the alias `Port`.
- Key = `~/.ssh/runpod_ed25519` (the "runpod" account key; `id_ed25519` is NOT in this pod).

## CURRENT STATE as of this handoff
Autonomous orchestrator `/workspace/run_all.sh` is running in tmux session `sweep7`:
**smoke → health-gate → full sweep7**. As of writing, the smoke's vLLM had loaded
(68GB on GPU) and was warming up; the gate had **not** yet reported.

### First thing next session — check where it got to:
```bash
ssh runpod-sweep7 'bash /workspace/status.sh'   # quick dashboard: STATUS, phase, GPU, per-cell trial counts
# or raw: ssh runpod-sweep7 'cat /workspace/logs/run_all.STATUS 2>/dev/null || echo RUNNING; tmux ls; tail -30 /workspace/logs/run_all.log'
```
Smoke gate PASSED 2026-06-17 11:53 (gen200=117); full sweep7 running as of handoff.
- `run_all.STATUS` absent → still running (`tail` the log / `tmux attach -t sweep7`).
- `DONE smoke_rc=.. full_rc=..` → full sweep finished → go to **Post-run** below.
- `FAILED ...` → smoke gate failed (vLLM didn't serve a generation). Inspect
  `steady-gpu/vllm-qwen3_6_35b-sweep7.log` for the cause, fix, re-launch `run_all.sh`.

## Fixes that were required (all in VENV_RECIPE.md; do NOT regress)
1. **vLLM cu129 wheel**, not plain `pip install vllm`. Plain pulls vllm 0.23.0 + torch
   cu130 (CUDA 13) → "driver too old" on the 12.8 box. cu129 (CUDA 12.9) runs via
   minor-version compat. Wheel URL in VENV_RECIPE.md.
2. **`fastapi==0.136.*`** (keep `starlette>=1.0`). fastapi 0.137.0 broke vLLM's API
   server (`_IncludedRouter ... no attribute 'path'` → 500 on /v1/models).
3. **`HF_HUB_OFFLINE=1` + `TRANSFORMERS_OFFLINE=1`** or vLLM stalls on HF metadata
   despite cached weights. (Set in run_all.sh.)
4. **`--served-model-name "$HF_MODEL"`** in the driver (committed `c0e7c5c`) — HF-offline
   renames the model id to the cache path, which would otherwise 404 the harness.

Why the cluster never hit these: it reuses a frozen, version-pinned apptainer
image (`~/vllm.sif`, ≈v0.20.2); RunPod got a fresh "latest-of-everything" install.

## Methodology (mirrors cluster sweep5v2; deliberate, generation-neutral deviations)
Identical matrix (5 tasks × {no-tools, tools_all_minimal} × {think on,off} × prompt
variants × domains), sampling (temp 0 greedy), `--max-model-len 16384`, parsers
(`qwen3_xml` + reasoning `qwen3`), prefix caching, per-task num_predict. Deviations:
1. **Weights:** BF16 `Qwen/Qwen3.6-35B-A3B` vs AWQ-INT4 `cyankiwi/...AWQ-4bit` — *this is the point*.
2. **Serving:** pip `vllm serve` on a bare H200, `--gpu-memory-utilization 0.90`, no
   >85% VRAM abort (that was an rtx_6000 OOM guard). GPU-mem-util only sizes KV cache;
   generation-neutral at temp 0.
Corpus isolation: `RUN_TAG=sweep7` → dedicated `results/sweep7/` root; canonical cell
dirnames `slurm_vllm_<model>_<think>_<cond>`. The AWQ sweep5v2 corpus is untouched.
**The BF16↔AWQ delta is a finding, not a bug — compare as adjacent columns, don't pool.**

## Post-run (when run_all.STATUS = DONE)
```bash
# 1. sync results to laptop
rsync -avz -e "ssh -i ~/.ssh/runpod_ed25519 -p <CURRENT_PORT>" \
  root@157.66.255.19:/workspace/pddl-copilot-experiments/results/sweep7/ \
  ~/personal/pddl-copilot-experiments/results/sweep7/
# 2. analyze (analyzer skill)
python3 .claude/skills/analyzer/scripts/aggregate.py results/sweep7
python3 .claude/skills/analyzer/scripts/plot.py      results/sweep7 --figs 4
python3 .claude/skills/analyzer/scripts/table.py     results/sweep7
# 3. STOP the pod to halt billing (results persist on the volume)
runpodctl pod stop f3nb15rlb2e0mi
```

## Open follow-ups
- Tar the verified `.venv` → `/workspace/venv-snapshot/venv-cu129.tar` for instant
  restore (recipe-rebuild otherwise ~10 min). Do during steady state, not weight-load.
- torch.compile cache lives on `/root/.cache/vllm` (container disk) → lost on pod
  restart → ~10 min recompile each launch. Redirect to `/workspace` to persist.
- launch-server.sh `--help` does NOT exit (execs the stdio server, hangs) — pre-create
  plugin venvs manually (`python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`).
- Smaller models (9B/4B/0.8B) + gemma are later phases. Cost framing: cost-breakdowns/.
