# Vast.ai self-deploy Ollama

Sibling of `cluster-experimenting/`. Spins up a single Vast.ai GPU instance,
clones this repo + the pddl-copilot marketplace onto it, runs `ollama serve`,
and executes `run_experiment.py` inside `tmux` on the instance. Results
rsync back to `results/vast-<instance-id>/` while the run is in flight.

## Why this exists

Cluster burn rate has been zero completed sweeps since the 2026-04-29 roster
refresh. Vast.ai gives us a queue-free path: ~$0.55/h for an L40S 48 GB
datacenter host. A full smoke (~90 min, ~$0.85) validates the pipeline; a
full sweep extrapolates to ~$25–$30 single-box sequential, or ~$28 across
4 parallel boxes for ~10× wall-time savings.

**Honest caveat:** the L40S is comparable to (or slower than) the cluster's
`rtx_pro_6000` Blackwell. Vast.ai does not improve per-call latency. The
demo win is queue elimination, always-on availability, and parallelism
across boxes — not faster individual calls.

## Setup (one-time, manual)

```bash
pip install vastai                                   # CLI
vastai set api-key <YOUR_KEY>                        # writes ~/.config/vastai/vast_api_key
vastai create ssh-key "$(cat ~/.ssh/id_ed25519.pub)" # one of your local pubkeys
vastai show user                                     # confirm balance + auth
```

The API key MUST NOT be committed. Reference it through the Vast CLI
config; never paste it inline in a shell command, never echo it into
logs, never put it in a script in this repo.

## Usage

```bash
# Default smoke: all 4 paper models on a single datacenter L40S 48GB.
bash cloud-experimenting/vast/run_smoke.sh

# Dry-run: pick offer + print would-be-launched command, no instance creation.
bash cloud-experimenting/vast/run_smoke.sh --dry-run

# Custom model set:
bash cloud-experimenting/vast/run_smoke.sh --models "Qwen3.5:0.8B qwen3.6:27b"

# Keep the instance alive after the smoke run (debug):
bash cloud-experimenting/vast/run_smoke.sh --keep
# ... then later: bash cloud-experimenting/vast/teardown.sh <instance-id>
```

While `run_smoke.sh` runs, results sync incrementally every 5 min into
`results/vast-<instance-id>/`. The orchestrator's EXIT trap always
attempts a final sync + `vastai destroy instance`, even on Ctrl-C.

## Cost guardrails (3 layers)

1. **Vast credit cap** — funded balance is the structural limit.
2. **Instance-side `shutdown -h +600`** in `bootstrap.sh` — 10 h hard kill.
3. **EXIT trap in `run_smoke.sh`** — destroys the instance unless `--keep`.

If a previous run was killed weirdly and an instance is still alive,
`vastai show instances` lists everything you own; `teardown.sh <id>`
forces cleanup.

## Reproducibility

`bootstrap.sh` writes `host_info.json` to the instance, captured into
`results/vast-<id>/`:

- Vast instance + host ID
- GPU model, CUDA version, RAM (from `nvidia-smi`)
- Ollama version (`ollama --version`)
- Per-model GGUF digests (`ollama show --modelfile <model>`)

For paper purposes: correctness numbers (success/failure, `tool_selected`,
tokens) are reproducible across hosts modulo FP non-determinism that exists
on the cluster too. Wall-time numbers are host-specific; document the GPU
in the methodology section the same way you'd document Ollama version.

## Files

| File | Runs on | Purpose |
|---|---|---|
| `run_smoke.sh` | laptop | Top-level orchestrator: launch → bootstrap → exec → sync → teardown. |
| `bootstrap.sh` | instance | One-time setup: apt + git clone + venv + ollama pull + serve. |
| `run_on_instance.sh` | instance | Starts the experiment inside `tmux`. Detaches; polled via SSH. |
| `sync_results.sh` | laptop | Idempotent `rsync results/` from instance. Safe to run mid-flight. |
| `teardown.sh` | laptop | Final sync + `vastai destroy instance`. Standalone or trap-driven. |
