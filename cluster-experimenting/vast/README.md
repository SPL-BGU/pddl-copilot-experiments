# Remote Ollama on Vast.ai

Lets cluster jobs offload the LLM serving to a rented GPU box on Vast.ai while
keeping the experiment code, MCP plugins, and result writing on the BGU
cluster. Saves cluster-GPU contention and frees you from waiting on the
`rtx_pro_6000` queue.

## Architecture

```
[Vast.ai box]                          [BGU SLURM job]
  ollama serve :11434  (internal)        run_experiment.py
  caddy reverse-proxy :8443  ◀── HTTPS+bearer ── pddl_eval/chat.py
                                                 MCP plugins (stdio, local)
  models preloaded in VRAM                       scoring + result write
  OLLAMA_KEEP_ALIVE=24h
```

The cluster job no longer needs a GPU. The MCP plugin servers still run as
stdio subprocesses inside the SLURM job — they were already decoupled from
the Ollama URL in `pddl_eval/chat.py`, so they don't move.

## One-time setup

1. Install the Vast CLI on the cluster login node (or wherever you'll run the
   deploy script):

   ```
   pip install --user vastai
   vastai set api-key <YOUR_API_KEY>
   ```

   In a GitHub Codespace the `VASTAI_API_KEY` repository secret is exposed as
   an env var; `deploy-ollama.sh` and `teardown-pool.sh` auto-pickup that env
   into `~/.vast_api_key` on first run, so step 1 reduces to
   `pip install --user vastai`.

2. The `.gitignore` in this directory excludes the generated `pool.txt` and
   `.token` from commits.

## Deploying the pool

```
# Pool size = max number of concurrent SLURM array tasks you intend to run.
# Each task picks a slot via SLURM_ARRAY_TASK_ID % N.
N=4 bash cluster-experimenting/vast/deploy-ollama.sh
```

Each box:

- Runs `ollama/ollama:latest`.
- Is filtered for `gpu_total_ram>=80 reliability>=0.95 disk_space>=100`
  (A100 80GB / H100 80GB class — needed to co-resident the 35B + 0.8b
  + one mid-class model without VRAM swap stalls).
- Auto-pulls + warms the active 4-model pack (override with `MODELS=...`).
- Exposes port 8443 publicly behind Caddy with a bearer-token auth gate.

The script appends `https://<host>:<port> # instance=<id>` to `pool.txt` and
generates a single shared bearer token in `.token` (reused on subsequent
runs).

## Smoke-testing before you submit

ALWAYS run this before the first sbatch — it catches the previous Vast
failure mode (port not actually exposed, auth mismatch, model not pulled):

```
bash cluster-experimenting/vast/smoke-test.sh
```

The test hits `/api/tags` and runs a 4-token `/api/chat` against the smallest
model on every URL in `pool.txt`. Fails loud if any box isn't fully ready.

## Submitting the sweep

Use the parallel submit wrapper that targets the remote sbatch:

```
bash cluster-experimenting/submit_with_remote.sh --all
```

Same flags as `submit_with_rtx.sh` (--all, --no-tools, --think-modes,
--smoke, --continue-partial, --partial, --shard, --exclude, --dry-run), minus
GPU-allocation flags (the cluster job no longer needs a GPU).

Each array task selects a pool slot by **model index** (the cell's model's
position in `--all` / the explicit model args), so each box stays on one
model when `N >= len(models)`. When `N < len(models)`, multiple models share
a box and Ollama swaps under `OLLAMA_MAX_LOADED_MODELS=3` — the pool warning
in `submit_with_remote.sh` flags this. The slot picker also accepts a manual
`SLURM_ARRAY_TASK_ID % N` fallback for legacy direct-sbatch invocations
(when `MODELS_LIST` isn't exported). Each task then sets `OLLAMA_HOST` and
`OLLAMA_AUTH_TOKEN` from `pool.txt` + `.token`, runs a preflight curl, and
calls `run_experiment.py` exactly as before.

## Tearing down

```
bash cluster-experimenting/vast/teardown-pool.sh
```

Destroys every instance recorded in `pool.txt` and renames the file to
`pool.txt.bak.<ts>`. Safe to re-run.

## Files

- `deploy-ollama.sh` — provisions N Vast instances, writes URLs to `pool.txt`.
- `Caddyfile.tmpl` — Caddy reverse-proxy config (bearer-token auth, TLS).
- `preload-model.sh` — runs ON the box, pulls + warms each model.
- `smoke-test.sh` — verifies reachability + auth + roster from the cluster side.
- `teardown-pool.sh` — `vastai destroy` for every instance in `pool.txt`.
- `pool.txt`, `.token` — generated, gitignored.

## Cost ballpark

A100 80GB on Vast typically runs ~$1.20-1.80 / hr / box. A 24h sweep with a
pool of 4 ≈ $115-170. Cheaper boxes (A6000 48GB, ~$0.40-0.80/hr) work only if
you partition by model class — a 48GB GPU cannot co-resident the 35B with a
mid-class model, so Ollama would swap on every cell change.

## Known limitations

- **TLS uses `tls internal` (self-signed via Caddy's local CA).** `run_experiment.py`
  passes `verify=False` to httpx whenever `OLLAMA_AUTH_TOKEN` is set, so the
  bearer token is the actual auth gate, not the cert. The token still rides
  TLS-encrypted on the wire, just without cert-chain verification. If you
  want full chain validation, swap `tls internal` in `Caddyfile.tmpl` for an
  automatic-HTTPS line backed by a domain you control.
- **Result methodology vs the rtx self-deploy variant.** The Vast pool runs
  `OLLAMA_KEEP_ALIVE=24h` and `OLLAMA_MAX_LOADED_MODELS=3` (vs `1h` / `1` on
  rtx). At `temperature=0.0` neither setting affects token outputs — they
  only change which models stay resident in VRAM and for how long. Result
  rows are interchangeable with the rtx path; latency-cost numbers are not.
- **Ollama version drift.** `IMAGE=ollama/ollama:latest` pulls whatever's
  current on Docker Hub at deploy time. The cluster's rtx Apptainer build
  pins via the cached `~/ollama.sif` from the first run, so the two paths
  can drift on Ollama micro-version. Pin `IMAGE` to a tag (e.g.
  `ollama/ollama:0.20.7`) for tight reproducibility.

## Troubleshooting

- **smoke-test reports 401**: bearer token mismatch. Verify the contents of
  `.token` match what the box has — re-run `deploy-ollama.sh`, the on-start
  command bakes the token in via env interpolation.
- **/api/tags returns "no models"**: preload still running. `vastai logs <id>`
  → look at `/var/log/preload.log` and `/var/log/ollama.log`.
- **chat() hangs / 504**: model still loading into VRAM on first hit.
  `keep_alive=24h` keeps it resident after the first chat.
- **Connection timeout**: port 8443 wasn't actually mapped externally. Check
  `vastai show instance <id>` and look for the `8443/tcp` entry under `ports`.
  Some Vast hosts don't allow arbitrary ports; the script picks the cheapest
  offer first — set `GPU_QUERY` to add a `direct_port_count>=1` filter, or
  pick a different host.
