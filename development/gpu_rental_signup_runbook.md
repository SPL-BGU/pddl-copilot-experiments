# User manual — set up the RunPod H200 (everything YOU do)

Your end-to-end checklist to get the rented GPU box online and hand it to the agent. After this,
the agent runs the experiment **on the box** — you don't run any of that.

> **No cluster involved.** Every step here is the **RunPod web console** + **your laptop's
> terminal** (`ssh`/`rsync`, built into macOS). The SLURM cluster is **not** used for this run —
> that's the whole point of renting: the cluster can't seat the 35B in BF16. (Later, the smaller
> 0.8–9B models *might* run on the free cluster — still undecided — but nothing here does.)

We use **RunPod Secure Cloud** (cheapest predictable H200, ~$3.59/hr, vetted hardware).
💸 **Credits are effectively non-refundable — load small, top up after the pilot.**

---

## 0. Prerequisites
- [x] **RunPod account** + small credit (done)
- [x] **Credit card** on file (done)
- [ ] **SSH key** (step 2)
- [ ] *(optional)* **Hugging Face token (Read)** (step 3) — **not needed for the 35B** (it's a
  public model); only required later for gated models like gemma

## 1. Credits — how much
**~$25** validates the box + runs the pilot; **~$50** covers the full 35B run with buffer. The
pilot measures real cost first, so **top up after it**, not up front.

## 2. Add your SSH public key
```bash
ssh-keygen -t ed25519 -C runpod -f ~/.ssh/runpod_ed25519     # press enter for no passphrase
cat ~/.ssh/runpod_ed25519.pub                                 # copy this whole line
```
Paste the `.pub` line into **RunPod → Settings → SSH Public Keys**.

## 3. Hugging Face token (Read) — *optional, skip for the 35B*
`Qwen3.6-35B` is **public**, so the box downloads it **without any token**. Only bother with a
token if/when we add a **gated** model like **gemma** (which also needs its license accepted on HF),
or to dodge anonymous download rate-limits on the 70 GB pull. If you do want one:
**HF → Settings → Access Tokens → New token (Read)**, save the `hf_...` value.

**To use it (on the box, not your laptop):** easiest is a pod **environment variable
`HF_TOKEN=hf_…`** on the RunPod deploy screen (vLLM + the downloader read it automatically); or run
`huggingface-cli login` after you SSH in. **Keep it secret** — never paste it into chat or any file
in the repo; revoke at HF if it leaks.

## 4. Deploy the pod
In the **RunPod console** (https://console.runpod.io) → **Pods → Deploy**, set these in order:

1. **Cloud type:** **Secure Cloud** *(not Community Cloud — and persistent network volumes are
   Secure-Cloud only)*.
2. **GPU:** search **H200 SXM (141 GB)**; **count = 1**.
3. **Template:** a **PyTorch / CUDA** template — these ship **SSH pre-configured**. (We install vLLM
   ourselves, so the exact template doesn't matter much.)
4. **Storage — set it NOW** *(⚠️ a volume can't be added later without recreating the pod)*:
   - **Container disk ≈ 50 GB** (OS + venv + vLLM).
   - **Volume disk ≈ 150–200 GB**, **mount path `/workspace`** — **run-critical**: caches the ~70 GB
     weights + repos + results. Survives **Stop**; wiped on **Terminate**.
     *(Want the weights to survive Terminate/recreate too — e.g. for the later gemma phase? Create a
     **Network Volume** under Storage and attach it here instead.)*
5. **Networking / SSH:** ensure the pod has a **Public IP** and **TCP port 22 exposed** (the PyTorch
   template does this). This is required for `rsync`/`scp` later — RunPod's *basic proxied* SSH
   (`ssh.runpod.io`) **can't transfer files**. Your SSH public key is already added (step 2).
6. **(optional) Env vars:** add `HF_TOKEN` here if you're using one (not needed for the 35B).
7. **Type:** **On-Demand** (non-interruptible — keeps the box steady). Skip **Spot** (~50% cheaper
   but can be killed mid-run).
8. **Confirm the live on-demand rate** (~$3.6–4.4/hr), then **Deploy On-Demand**.

## 5. Connect & hand off
When the pod is **Running**, open it → **Connect** → copy the **"SSH over exposed TCP"** line (the
full-SSH one with a real IP + port, *not* the `ssh.runpod.io` proxy) and test it:
```bash
ssh root@<POD_IP> -p <SSH_PORT> -i ~/.ssh/runpod_ed25519
```
Then **send me `<POD_IP>` + `<SSH_PORT>`** and I'll run smoke → pilot → full run.

---

## ⚠️ Cost control — every time you finish
- **Stop** the pod between sessions → no compute charge; the `/workspace` volume persists (small
  storage fee).
- **Terminate** only when the whole sweep is done → frees everything (data gone).
- Rule: **stop** between sessions, **terminate** when finished. Unused credit doesn't refund.

---

*Reference only (not yours to run): the agent's on-box run sequence is in
`development/steady_gpu_runbook.md`; the goal + constraints are in
`development/steady_gpu_deployment_handoff.md`.  ·  RunPod: https://www.runpod.io/*
</content>
