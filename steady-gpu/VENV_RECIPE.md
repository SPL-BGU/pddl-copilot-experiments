# Turnkey venv recipe — steady-gpu sweep7 (RunPod H200, CUDA 12.8 driver)

Base image: runpod/pytorch:1.0.2-cu1281-torch280-ubuntu2404  (driver 570.195.03 = CUDA 12.8 max)

## Why the defaults break (do NOT `pip install vllm` plain)
- Plain `pip install vllm` pulls vllm 0.23.0 + torch 2.11 cu130 (CUDA 13) -> driver too old.
- It also pulls fastapi 0.137.x -> vLLM API server 500s on /v1/models (_IncludedRouter bug).

## Rebuild steps (in /workspace/pddl-copilot-experiments)
python3 -m venv .venv && source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
# vLLM built for CUDA 12.9 (minor-version-compatible with the 12.8 driver):
pip install "https://github.com/vllm-project/vllm/releases/download/v0.23.0/vllm-0.23.0+cu129-cp38-abi3-manylinux_2_28_x86_64.whl" \
  --extra-index-url https://download.pytorch.org/whl/cu129
# Pin fastapi < 0.137 (keep starlette >=1.0 for prometheus-fastapi-instrumentator / sse-starlette):
pip install "fastapi==0.136.*" "starlette>=1.0"

## Runtime env (required)
export HF_HOME=/workspace/hf-cache
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1   # else vLLM stalls on HF metadata
# driver passes --served-model-name "$HF_MODEL" (committed) so offline path-rename doesn't 404

## Exact lock
requirements-cu129.lock  (pip freeze of the verified-working venv)
