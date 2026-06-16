# Runbook — rent an NVIDIA GPU box and unblock probing

**Purpose:** get a steady **H200-141GB** box online so we can start probing sweep5v2 + PlanBench
on the open-model roster. Companion to `development/steady_gpu_deployment_handoff.md` (the goal)
and slide 5 of the cost deck (the framing).

> **Division of labour**
> - **PART A = you (human-only):** account, payment, launch the box, open access. Nobody else can
>   do these — they need your identity + card.
> - **PART B = dev (me / next agent):** install + launch vanilla vLLM, wire the harness, smoke-probe.
>   Listed here for context; **no action from you**.

---

## Which platform (you asked for "the NVIDIA platform")

The NVIDIA-branded, self-serve, *raw GPU box* you can run vanilla vLLM on is **NVIDIA Brev** →
**https://brev.nvidia.com**. It bills per hour and gives you a real Linux box with SSH.

- ❌ Not `build.nvidia.com` (that's NIM — managed inference endpoints, you can't run *our* vLLM on it).
- ❌ Not classic DGX Cloud (enterprise, committed contracts).
- ✅ NVIDIA Brev = the right NVIDIA product for us.

**Heads-up (from our handoff):** Brev is a *pass-through* to underlying clouds, so its per-hour H200
price is **variable** — check the live number in the console before you click Deploy. Real H200
on-demand in mid-2026 runs **~$3.0–4.4/hr** (RunPod ~$3.59, Lambda ~$4.99, market median ~$3.95).
At those prices budget **~$120–220** for the full sweep5v2 across all five models (PlanBench extra).
If Brev's price/availability looks bad, the **RunPod Secure Cloud** alternative is in the last section.

---

## PART A — what only you can do

### 0. Prerequisites (have these ready)
- [ ] An **NVIDIA account** (free) — you'll sign into Brev with it. Create/manage: https://www.nvidia.com/en-us/account/
- [ ] A **credit card** for hourly billing.
- [ ] Your Mac (you're on macOS) with **Homebrew**. Check: `brew --version`. If missing, install from https://brew.sh.

### 1. Create your Brev account
1. Go to **https://brev.nvidia.com**.
2. Sign in / sign up with your **email** (or NVIDIA-account OAuth). Verify the email.
3. You'll land on the Brev console.

### 2. Add a payment method
1. In the console, open **Settings → Billing** (account/org settings).
2. Add your credit card. Brev **bills per hour of compute**; a stopped instance has **no compute
   charge** (tiny storage cost only).
3. *(Optional but smart)* set a **spending alert / limit** if the billing page offers one.

### 3. Install the Brev CLI + log in (on your Mac)
You need the CLI so we can tunnel the GPU's port back to your laptop (step 6).
```bash
brew install brevdev/homebrew-brev/brev
brev --version
brev login                 # opens a browser to authenticate; creds saved to ~/.brev/
```

### 4. Launch an H200 instance (console)
1. In the console go to **GPU Instances → Create New Instance**.
   - Direct link for H200: **https://brev.nvidia.com/environment/new/public?gpu=H200**
2. On **Select your Compute**, pick an **H200 (141 GB)**, single GPU.
   - **Confirm the $/hr shown** before continuing (see price note above).
   - Region: pick whatever has H200 capacity and is closest.
3. **Storage:** bump the disk to **~300–400 GB** if asked — model weights for the 35B/31B are big
   (~70 GB each) and we'll cache several.
4. **Name** it e.g. `pddl-h200` and click **Deploy**. It takes a few minutes to boot.

### 5. Verify the box is real
```bash
brev refresh
brev list                  # see your instance + its status
brev shell pddl-h200       # opens a shell ON the box
# on the box:
nvidia-smi                 # should show 1× H200, ~141 GB. Then: exit
```

### 6. Open the door for dev (pick ONE)

**Option A — port-forward to your laptop (recommended, private):**
Once vLLM is running on the box (PART B), expose it locally so the harness can reach it at
`localhost:8000`:
```bash
brev port-forward pddl-h200 --port 8000:8000
# leave this running; the harness then uses  --llm-base-url http://localhost:8000
```

**Option B — just hand me access:** run `brev list` and tell me the instance name; I can drive it
via `brev shell` / `brev port-forward` from here. (You still had to create it + pay — that's the
human-only part.)

### ⚠️ COST CONTROL — do this every time you finish
You are billed **per hour while the instance is RUNNING**, even idle.
```bash
brev stop pddl-h200        # pause: no compute charge, keeps your data (/home/ubuntu/workspace)
brev start pddl-h200       # resume later (subject to H200 availability)
brev delete pddl-h200      # DONE for good: stops storage cost too (IRREVERSIBLE — wipes data)
```
Rule of thumb: **stop** between sessions, **delete** when the whole sweep is finished.

---

## PART B — what dev does next (no action from you)

For context only — once the box is up and reachable:
1. On the box: `pip install vllm`, then launch one model at a time, e.g.
   ```bash
   vllm serve <HF-model-id> --port 8000 \
        --served-model-name <name-the-harness-sends> \
        --max-model-len 16384 --gpu-memory-utilization 0.90 --enable-prefix-caching
   ```
   (exact HF ids + the per-model reasoning-parser flag come from the harness model map / the
   `reference_vllm_parser_per_model` note — the next agent fills these in.)
2. Point the harness at it:
   - sweep5: `run_experiment.py --llm-base-url http://localhost:8000`
   - PlanBench: `export VLLM_BASE=http://localhost:8000/v1`
3. Run a tiny **smoke probe** (a handful of trials) to confirm tokens come back and parse, then
   time-share the box across the five models per the handoff.
4. **Corpus isolation:** each model's `trials.jsonl` from this ONE backend; keep
   temp/top_p/max_tokens/seed identical to the cluster cells.

> Note: `VLLMClient` currently hardcodes `api_key="EMPTY"`. Brev's tunnel is private so that's fine;
> if we ever expose a public/Cloudflare URL with auth, the key has to become configurable.

---

## Alternative — RunPod Secure Cloud (if Brev is pricey/unavailable)

Equally simple, often cheaper, and the option our handoff actually recommended.
1. Sign up: **https://www.runpod.io/** → add payment (Billing).
2. **Deploy a Pod** → **Secure Cloud** → filter GPU = **H200 (141 GB)** → pick the **vLLM** or
   **PyTorch** template → set container disk + volume ~300–400 GB → **Deploy** (~$3.59/hr typical).
3. Expose the API: RunPod gives an **HTTP proxy URL** per exposed port, or use **TCP port mapping**
   + SSH; point the harness `--llm-base-url` / `VLLM_BASE` at that URL (`…/v1`).
4. **Stop/terminate** the pod when idle — same per-hour billing discipline as Brev.

---

## Sources (verified Jun 2026)
- NVIDIA Brev console: https://brev.nvidia.com  ·  H200 launch: https://brev.nvidia.com/environment/new/public?gpu=H200
- Brev quickstart: https://docs.nvidia.com/brev/getting-started/quickstart
- Brev GPU instances / billing: https://docs.nvidia.com/brev/concepts/gpu-instances
- Brev connectivity / port-forward: https://docs.nvidia.com/brev/cli/connectivity
- NVIDIA account: https://www.nvidia.com/en-us/account/
- H200 price comparison: https://getdeploying.com/gpus/nvidia-h200
- RunPod H200: https://www.runpod.io/gpu-models/h200
- Lambda pricing: https://lambda.ai/service/gpu-cloud (on-demand H200)
</content>
