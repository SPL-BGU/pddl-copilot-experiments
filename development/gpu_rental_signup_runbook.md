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
**HF → Settings → Access Tokens → New token (Read)**, save the `hf_...` value — you'll set it on the
**box**, not your laptop.

## 4. Deploy the pod
1. **https://www.runpod.io/** → **Deploy** → **Secure Cloud** *(not Community Cloud)*.
2. GPU = **H200 SXM (141 GB)**, **1× GPU**.
3. Template = **vLLM** or **PyTorch/CUDA**; enable **SSH**.
4. **Confirm ~$3.59/hr** before you deploy.

## 5. Attach a persistent volume — run-critical
A **~150–200 GB volume mounted at `/workspace`**. It caches the ~70 GB weights + repos + results
across stop/restart. **Without it, every restart re-pulls 70 GB.**

## 6. Verify, then hand off
```bash
ssh -i ~/.ssh/runpod_ed25519 root@<pod-host> -p <pod-port>    # host+port shown on the pod page
```
Then **send me `<pod-host>` + `<pod-port>`** and I'll run smoke → pilot → full run.

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
