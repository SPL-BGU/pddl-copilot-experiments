# Runbook — rent a RunPod H200 (account, billing, access, cost control)

**Purpose:** the **provider signup + billing + access + cost-control** reference for getting a
steady **H200-141GB** box online. This is the "how you get and pay for the box" half.

- **The actual run** (bootstrap, smoke → pilot → full sweep7, sync back) lives in
  **`development/steady_gpu_runbook.md`** — don't duplicate it here.
- **The goal + constraints** live in `development/steady_gpu_deployment_handoff.md`.
- **Cost framing** is slide 5 of `development/cost-breakdowns/cheap_model_cost_slides.pptx`.

> **Division of labour**
> - **PART A = you (human-only):** account, payment, SSH key, launch the box. Nobody else can do
>   these — they need your identity + card.
> - **PART B = dev (me / next agent):** install + launch vanilla vLLM, run the probe + sweep.
>   See `steady_gpu_runbook.md`; **no action from you**.

---

## Decision — RunPod Secure Cloud

For one steady box running vanilla vLLM, **RunPod Secure Cloud** wins: cheapest *predictable* H200
price (**~$3.59/hr**), vetted Tier-3/4 datacenter hardware, a one-click **vLLM/PyTorch template**,
and it's what the handoff recommended.

**Evaluated and rejected:**
- **NVIDIA Brev** (`brev.nvidia.com`): the same H200 lists at **$5.29–5.40/hr** (~50% more) and Brev
  is a *pass-through* over other clouds — extra layer, no upside for us.
- **vast.ai**: our 2026-05-06 attempt (a *pool* of community boxes behind Caddy + bearer + Ollama)
  was reverted one day later for **unreliable performance** (CHANGELOG 2026-05-07). Community
  hardware = variable quality. The new single-box / vanilla-vLLM design avoids most of that, and
  Secure Cloud avoids the rest. Don't use **Community Cloud** (the vast-like tier).
- **Lambda**: fine alternative (pay-per-minute, no prepaid balance to strand), ~$5/hr H200.

> 💸 **Prepaid credit is effectively non-refundable** on RunPod (refunds are case-by-case via
> support, not self-serve). **Load small, top up often** — don't front-load the whole sweep.

---

## PART A — what only you can do

### 0. Prerequisites
- [x] **RunPod account** with a small credit loaded (you've done this).
- [x] A **credit card** on file.
- [ ] An **SSH key** (step 2) — needed to reach the box. macOS has `ssh`/`rsync` built in; no extra CLI.
- [ ] A **Hugging Face token (Read)** (step 3) — to download model weights.

  (No NVIDIA account, no Homebrew, no `brev` CLI needed on the RunPod path.)

### 1. Credits — how much
You've loaded some already. Sizing: **~$25** is enough to validate the box + run the **pilot**;
the operator runbook suggests **~$50** to cover the full **35B `sweep7`** with buffer. The pilot
(in `steady_gpu_runbook.md`, Step B) measures real GPU-hours so you confirm the total **before**
committing. Top up after the pilot rather than up-front (credits don't refund).

### 2. Add your SSH public key
```bash
ssh-keygen -t ed25519 -C runpod -f ~/.ssh/runpod_ed25519     # press enter for no passphrase
cat ~/.ssh/runpod_ed25519.pub                                 # copy this line
```
Paste the `.pub` line into **RunPod → Settings → SSH Public Keys**.

### 3. Hugging Face token (Read)
HF → **Settings → Access Tokens → New token (Read)**. Save the `hf_...` value for step 2 of the
operator runbook. Note: `Qwen/Qwen3.6-35B-A3B` is **ungated**; **gemma** (later) needs its license
accepted on HF first.

### 4. Deploy the pod
1. **https://www.runpod.io/** → **Deploy** → **Secure Cloud** (not Community Cloud).
2. GPU = **H200 SXM (141 GB)**, **1× GPU** (a single H200 fits every model in BF16).
3. Template = **vLLM** or **PyTorch/CUDA**; enable **SSH**.
4. Confirm **~$3.59/hr** before deploying.

### 5. Attach a persistent volume — **run-critical**
Attach a **~150–200 GB Network/Persistent Volume mounted at `/workspace`**. It caches the ~70 GB
BF16 weights + both repos + results across stop/restart. **Without it, every restart re-pulls
70 GB of weights.**

### 6. Verify SSH, then hand off
```bash
ssh -i ~/.ssh/runpod_ed25519 root@<pod-host> -p <pod-port>    # RunPod shows host+port on the pod
```
Then **give me `<pod-host>` + `<pod-port>`** (or run `steady_gpu_runbook.md` yourself). Creating +
paying for the box was the human-only part; from there dev can drive it.

---

## ⚠️ COST CONTROL — every time you finish

RunPod bills **per hour while the pod is RUNNING**, even idle.

- **Stop** the pod between sessions → no compute charge; the `/workspace` volume (and your cached
  weights) **persists** for a small storage fee.
- **Terminate** only when the whole sweep is done → frees everything (volume + data gone).
- Rule of thumb: **stop** between sessions, **terminate** when finished. And remember credits don't
  refund, so unused balance is spend-it-or-lose-it.

---

## How the harness reaches vLLM

**Chosen design (simplest):** the harness runs **on the box** against `localhost:8000`. Vanilla
vLLM needs no key, so `VLLMClient`'s hardcoded `api_key="EMPTY"` works unchanged — no code change
(tracked as deferred **ISS-023**; only a *public, auth-gated* endpoint would need it).

**Alternative — run the harness on your laptop** via an SSH tunnel:
```bash
ssh -i ~/.ssh/runpod_ed25519 -p <pod-port> -L 8000:localhost:8000 root@<pod-host>
# then locally:  run_experiment.py --llm-base-url http://localhost:8000
#                export VLLM_BASE=http://localhost:8000/v1   # PlanBench
```

---

## PART B — what dev does next (no action from you)

See **`development/steady_gpu_runbook.md`** for the full operator sequence: clone repos onto
`/workspace`, `pip install vllm`, pre-download weights, **smoke** (confirm tool extraction) →
**pilot** (measure cost) → **full `sweep7`** (35B BF16) → **sync back + analyze**. Corpus isolation:
each model's `trials.jsonl` from this ONE backend; sampling params identical to the cluster cells.

---

## Sources (verified Jun 2026)
- RunPod: https://www.runpod.io/  ·  H200: https://www.runpod.io/gpu-models/h200
- H200 price comparison: https://getdeploying.com/gpus/nvidia-h200
- Lambda (pay-per-minute alt): https://lambda.ai/service/gpu-cloud
- vast.ai postmortem: `development/CHANGELOG.md` 2026-05-07 (reverted pool transport)
</content>
