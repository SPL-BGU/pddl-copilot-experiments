#!/bin/bash
### probe_serving_env.sh — record the serving environment for the paper's
### "computing infrastructure" sentence (paper/main.tex, Methodology,
### "Models and Serving") and its Reproducibility Checklist item.
###
### Run ON THE CLUSTER LOGIN NODE (slurm.bgu.ac.il), from the repo root:
###   bash cluster-experimenting/probe_serving_env.sh \
###     | tee development/reference/serving_env_$(date +%Y%m%d).txt
###
### Read-only: greps existing job logs, reads the cached vllm.sif, and runs
### one short `srun` per GPU class for driver + OS (each waits at most 2 min
### for a free GPU). Nothing is submitted with
### sbatch; nothing on disk is modified.
set -uo pipefail

ROOT="${EXPT_ROOT:-$HOME/pddl-copilot-experiments}"
LOGS="$ROOT/cluster-experimenting/logs"
SIF="${SIF:-$HOME/vllm.sif}"

echo "== probe_serving_env $(date '+%Y-%m-%dT%H:%M:%S%z') on $(hostname) =="

echo; echo "## 1. vLLM version actually served (startup banner in the preserved serve logs)"
grep -h -o 'vLLM API server version [0-9A-Za-z.+]*' "$LOGS"/*-vllm-*.log 2>/dev/null | sort | uniq -c \
  || echo "(no *-vllm-*.log under $LOGS)"

echo; echo "## 2. GPU models the sweep jobs saw (nvidia-smi line at the top of every job .out)"
grep -h -E '^[A-Za-z].*, [0-9]+ MiB$' "$LOGS"/*.out 2>/dev/null | sort | uniq -c \
  || echo "(no *.out under $LOGS)"

echo; echo "## 3. Container image contents: vLLM / PyTorch / CUDA runtime (sbatch pin: docker://vllm/vllm-openai:v0.20.2)"
if [ -f "$SIF" ]; then
  apptainer exec "$SIF" python3 - <<'PY'
import importlib.metadata as m
for pkg in ("vllm", "torch", "transformers", "flashinfer-python", "xformers", "triton"):
    try:
        print(f"{pkg}=={m.version(pkg)}")
    except m.PackageNotFoundError:
        print(f"{pkg}: not installed")
import torch
print("torch.version.cuda =", torch.version.cuda)
print("torch cudnn =", torch.backends.cudnn.version())
PY
  apptainer exec "$SIF" bash -c 'grep -E "^PRETTY_NAME=" /etc/os-release 2>/dev/null | sed "s/^/image OS: /"; nvcc --version 2>/dev/null | tail -1 | sed "s/^/nvcc: /"'
else
  echo "(no $SIF on this host)"
fi

echo; echo "## 4. SLURM's view of the GPU nodes (no allocation needed; kernel from the OS= field)"
sinfo -N -h -o '%N %f %G' 2>/dev/null | grep -E 'rtx_6000|rtx_pro_6000' | sort -u
for n in $(sinfo -N -h -o '%N %G' 2>/dev/null | grep -E 'rtx_6000|rtx_pro_6000' | awk '{print $1}' | sort -u | head -8); do
  printf '%s: ' "$n"; scontrol show node "$n" 2>/dev/null | grep -o 'OS=.*' | head -1
done

echo; echo "## 5. Host NVIDIA driver + OS, one node per GPU class (3-minute srun each; gives up if no GPU is free within 2 minutes)"
probe_node() {  # probe_node <--gpus spec> [extra sbatch flags...]
  echo "--- srun --gpus=$* ---"
  srun --partition=main --gpus="$1" "${@:2}" --mem=2G --time=00:03:00 --immediate=120 --job-name=env_probe \
    bash -c 'echo "node: $(hostname)"
             nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader | head -1
             nvidia-smi | grep -o "CUDA Version: [0-9.]*"
             grep -E "^(PRETTY_NAME|VERSION_ID)=" /etc/os-release
             echo "kernel: $(uname -r)"' 2>&1
}
probe_node rtx_6000:1 --constraint=rtx_6000
probe_node rtx_pro_6000:1

echo; echo "== done. Put the versions into the 'Models and Serving' sentence of paper/main.tex and flip the checklist item to yes. =="
