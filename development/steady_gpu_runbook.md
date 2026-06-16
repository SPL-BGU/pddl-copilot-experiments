# Runbook — steady GPU (RunPod H200) for the BF16 `sweep7` 35B run

Goal: re-run the **single-tool sweep5v2 experiment on Qwen3.6-35B in clean BF16**
(`Qwen/Qwen3.6-35B-A3B`) on one rented RunPod H200-141GB, as a fresh corpus
tagged **`sweep7`**. The experiment is config-identical to the cluster's AWQ run
— only the weights (BF16, not AWQ-INT4) and the host (RunPod box, not the SLURM
cluster) differ. Driver: `steady-gpu/run_steady_gpu.sh`.

Scope (locked): **35B only**, probe → full run. Extending to 9B/4B/0.8B/gemma is
a later phase (the driver already knows the 9B BF16 id).

---

## Part 1 — Get the box (human-only)

Account, payment, SSH key, HF token, deploying the Secure-Cloud **H200 SXM (141 GB)**, the
**`/workspace` volume**, and cost control are all in the **user manual** →
**`development/gpu_rental_signup_runbook.md`**. Do that first; once you can SSH in (and have
sent the host/port), the agent drives Part 2. The 35B `Qwen/Qwen3.6-35B-A3B` is **ungated**.

> **Auth note (dev):** the harness runs **on the box** against `localhost:8000`, so vLLM
> needs no key and `VLLMClient`'s hardcoded `api_key="EMPTY"` works unchanged.
> Only a *public* gated endpoint would need the deferred `ISS-023` key change.

---

## Part 2 — Operator sequence (the agent drives this once you're SSH'd in)

All paths under the persistent `/workspace` volume so they survive restarts.

### Box bootstrap (once per fresh volume)
```bash
cd /workspace
git clone https://github.com/SPL-BGU/pddl-copilot-experiments.git
git clone https://github.com/SPL-BGU/pddl-copilot.git        # MCP plugins (tools arm)

cd /workspace/pddl-copilot-experiments
python3 -m venv .venv && source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install vllm                                              # OpenAI server + `vllm serve`

# MCP plugin venvs (the tools arm spawns these). launch-server.sh lazily
# creates a .venv on first MCP spawn; pre-create to avoid first-run latency:
for p in pddl-solver pddl-validator; do
  bash /workspace/pddl-copilot/plugins/$p/scripts/launch-server.sh --help >/dev/null 2>&1 || true
done

# Pre-download the 35B BF16 weights onto the volume (it's PUBLIC — no token/login
# needed; only gated models like gemma need `huggingface-cli login` first)
export HF_HOME=/workspace/hf-cache
huggingface-cli download Qwen/Qwen3.6-35B-A3B                # ~70GB → warm cache
```

Point the driver at this checkout's repos (it defaults to `$HOME/...`; on the
box, set them to the `/workspace` clones):
```bash
export EXPT_ROOT=/workspace/pddl-copilot-experiments
export MARKETPLACE_PATH=/workspace/pddl-copilot
export HF_HOME=/workspace/hf-cache
cd "$EXPT_ROOT"
```

### Step A — Smoke (does it serve + extract tools?)
Confirms the BF16 served-name is right and the `qwen3_xml` parser yields
non-zero ToolSel. A wrong served-name silently gives 0% tool extraction.
```bash
SMOKE=1 bash steady-gpu/run_steady_gpu.sh
```
Check `results/smoke/...` — tools cells should show ToolSel > 0.

### Step B — Pilot (real throughput + cost)
Full matrix, capped to the first 2 fixtures/domain → measures tok/s on the BF16
35B so you can extrapolate GPU-hours/$ before committing the full grid.
```bash
PARTIAL_K=2 RESULTS_ROOT=/workspace/pddl-copilot-experiments/results/sweep7-pilot \
  bash steady-gpu/run_steady_gpu.sh
```
Time the run; multiply out to the full ~600-fixture grid; sanity-check against
the ~$3/hr H200 rate. Stop here and re-confirm budget if it's surprising.

### Step C — Full `sweep7` (35B BF16)
```bash
bash steady-gpu/run_steady_gpu.sh        # MODELS defaults to qwen3.6:35b
```
Resumable: a disconnect/teardown only loses the in-flight trial; re-run the same
command to continue. Results: `results/sweep7/slurm_vllm_qwen3_6_35b_<think>_<cond>_sweep7/`.

### Step D — Sync back + analyze (from your laptop)
```bash
rsync -avz -e "ssh -i ~/.ssh/runpod_ed25519 -p <pod-port>" \
  root@<pod-host>:/workspace/pddl-copilot-experiments/results/sweep7/ \
  ~/personal/pddl-copilot-experiments/results/sweep7/
```
Then run the **analyzer** skill pointed at the `sweep7` tree to compare BF16
vs the cluster's AWQ 35B (`sweep5v2`). The 35B BF16↔AWQ delta is a reportable
**finding**, not a bug — do not pool the two corpora.

### Step E — Stop the pod
**Stop** (not terminate) to keep the `/workspace` volume for the next phase
(9B, then PlanBench). Terminate only when fully done to stop all billing.

---

## What "mirrors the cluster" means here (and the two deliberate deviations)

Identical to the cluster sweep5v2 35B cells: matrix (5 tasks × {no-tools,
tools_all_minimal} × {think on, off} × prompt variants × domains), sampling
(temperature 0, greedy), `--max-model-len 16384`, parsers (`qwen3_xml` +
`qwen3`), prefix caching, and per-task `num_predict`.

Deliberate, generation-neutral deviations (documented so they're not mistaken
for drift):
1. **Weights:** BF16 `Qwen/Qwen3.6-35B-A3B` instead of AWQ-INT4
   `cyankiwi/Qwen3.6-35B-A3B-AWQ-4bit`. **This is the point of the run.**
2. **Serving infra:** pip `vllm serve` on a bare H200, `--gpu-memory-utilization
   0.90`, no `>85% VRAM abort`. The cluster used apptainer under SLURM with 0.85
   and an rtx_6000 OOM guard. GPU-mem-util only sizes the KV cache — at temp 0 it
   does not change token outputs.

Corpus isolation: `RUN_TAG=sweep7` → distinct `results/sweep7/` tree; the AWQ
`sweep5v2` corpus is untouched.
