#!/usr/bin/env bash
# planbench/setup.sh — provision the PlanBench arm dependencies.
#
# Idempotent: re-running skips already-completed steps.
#
# Outputs the env-var exports needed to run a PlanBench task. Source the
# printed block, or run with `--print-env-only` after a successful setup
# to get just the exports.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
EXTERNAL_DIR="${REPO_ROOT}/external"
LLMS_PLANNING_REMOTE="${LLMS_PLANNING_REMOTE:-https://github.com/karthikv792/LLMs-Planning.git}"
LLMS_PLANNING_REF="${LLMS_PLANNING_REF:-main}"
DOWNWARD_REMOTE="${DOWNWARD_REMOTE:-https://github.com/aibasel/downward.git}"
DOWNWARD_REF="${DOWNWARD_REF:-release-23.06.0}"

PRINT_ENV_ONLY=0
TOOLS=0
for arg in "$@"; do
    case "$arg" in
        --print-env-only) PRINT_ENV_ONLY=1 ;;
        --tools) TOOLS=1 ;;
        -h|--help)
            sed -n '2,9p' "$0"
            exit 0
            ;;
    esac
done

print_env() {
    local val_dir="$1" pr2_dir="$2" fd_dir="$3" venv_dir="$4" pb_dir="$5"
    cat <<EOF

# --- planbench arm env exports ---
export VAL="$val_dir"
export PR2="$pr2_dir"
export FAST_DOWNWARD="$fd_dir"
export PLANBENCH_PATH="$pb_dir"
export PLANBENCH_VENV="$venv_dir"
export PLANBENCH_TOOLS_VENV="$pb_dir/.venv-tools"
export PDDL_COPILOT_EXPERIMENTS_ROOT="$REPO_ROOT"
export PYTHONPATH="$REPO_ROOT\${PYTHONPATH:+:\$PYTHONPATH}"
# Stub key so PlanBench's utils/__init__.py imports cleanly without an
# OpenAI account. Replace with a real key if you also want to run the
# bloom / openai engines.
: "\${OPENAI_API_KEY:=__planbench_stub__}"
export OPENAI_API_KEY
# Activate the slim PlanBench venv (skip if you manage your own venv):
# source "$venv_dir/bin/activate"
# --- end ---
EOF
}

if [[ "$PRINT_ENV_ONLY" -eq 1 ]]; then
    pb_dir="$EXTERNAL_DIR/LLMs-Planning"
    print_env "$pb_dir/planner_tools/VAL" "$pb_dir/planner_tools/PR2" \
              "$EXTERNAL_DIR/downward" "$pb_dir/.venv" "$pb_dir"
    exit 0
fi

cd "$REPO_ROOT"
mkdir -p "$EXTERNAL_DIR"

# 1. LLMs-Planning checkout ---------------------------------------------------
PB_DIR="$EXTERNAL_DIR/LLMs-Planning"
if [[ ! -d "$PB_DIR/.git" ]]; then
    echo "[planbench setup] cloning LLMs-Planning..."
    git clone "$LLMS_PLANNING_REMOTE" "$PB_DIR"
fi
(cd "$PB_DIR" && git fetch --tags --quiet --depth 1 origin "$LLMS_PLANNING_REF" \
    && git checkout --quiet FETCH_HEAD)

# 2. Apply patches (idempotent in-place edits, anchored on stable strings) ---
python3 "$REPO_ROOT/planbench/apply_patches.py" "$PB_DIR"

# 3. VAL — try pre-built binary, rebuild on failure --------------------------
# The vendored binary is a Linux x86_64 ELF; on Linux it usually runs fine,
# on macOS it doesn't. The rebuild path requires `make clean` first because
# the repo ships stale Linux .o files that confuse `make validate`.
VAL_DIR="$PB_DIR/planner_tools/VAL"
SKIP_LINUX_BINARIES=0
if [[ "$(uname)" == "Darwin" ]]; then
    SKIP_LINUX_BINARIES=1
    cat >&2 <<'EOF'
[planbench setup] macOS detected — skipping VAL / PR2 / FD evaluation binaries.
  VAL is a Linux ELF binary (rebuild on Darwin is brittle; not attempted).
  PR2 is a 32-bit Linux binary with no source distribution.
  Fast Downward builds on Darwin but PlanBench evaluation needs VAL anyway,
  so the local arm is engine-smoke-only. Run full evaluation on the cluster.
EOF
elif "$VAL_DIR/validate" -h >/dev/null 2>&1; then
    echo "[planbench setup] VAL binary OK (pre-built)"
else
    echo "[planbench setup] rebuilding VAL from source (make clean + validate)..."
    (cd "$VAL_DIR" && make clean validate >/tmp/val-build.log 2>&1) \
        || { echo "[planbench setup] VAL build failed; see /tmp/val-build.log" >&2; exit 1; }
fi

# 4. PR2 — pre-built only (no source distribution; closed-source) ------------
PR2_DIR="$PB_DIR/planner_tools/PR2"
if [[ "$SKIP_LINUX_BINARIES" -eq 0 ]]; then
    if "$PR2_DIR/pr2plan" -h >/dev/null 2>&1; then
        echo "[planbench setup] PR2 binary OK"
    else
        cat >&2 <<'EOF'
[planbench setup] WARN: pr2plan does not run on this host.
  PR2 is a 32-bit Linux ELF binary with no upstream source distribution.
  - Ubuntu/Debian Linux: install i386 compat libs:
      sudo dpkg --add-architecture i386 && sudo apt install libc6:i386 libstdc++6:i386
  - Tasks t4-t8 will fail here. t1, t2, t3, t7 still run.
EOF
    fi
fi

# 5. Fast Downward -----------------------------------------------------------
FD_DIR="$EXTERNAL_DIR/downward"
if [[ "$SKIP_LINUX_BINARIES" -eq 0 ]]; then
    if [[ ! -d "$FD_DIR/.git" ]]; then
        echo "[planbench setup] cloning Fast Downward ($DOWNWARD_REF)..."
        git clone --depth 1 --branch "$DOWNWARD_REF" "$DOWNWARD_REMOTE" "$FD_DIR"
    fi
    if [[ ! -d "$FD_DIR/builds/release" ]]; then
        echo "[planbench setup] building Fast Downward (5-10 min)..."
        (cd "$FD_DIR" && ./build.py >/tmp/fd-build.log 2>&1) \
            || { echo "[planbench setup] FD build failed; see /tmp/fd-build.log" >&2; exit 1; }
    fi
fi

# 6. Slim Python venv --------------------------------------------------------
# PlanBench's pinned requirements.txt is from 2022 (tarski==0.7.0,
# pddl==0.2.0). Those pins are real — PlanBench's code uses tarski 0.7.0
# specific APIs. We only need the import-time deps plus httpx (the HTTP
# client engine.py uses to reach the self-deployed vLLM server; the Ollama
# backend was retired 2026-05-18). Prefer python3.12 (widely compatible
# with the old pins); fall back to whatever python3 we find.
PYTHON_BIN="${PLANBENCH_PYTHON:-}"
if [[ -z "$PYTHON_BIN" ]]; then
    for candidate in python3.12 python3.11 python3.10 python3; do
        if command -v "$candidate" >/dev/null 2>&1; then
            PYTHON_BIN="$(command -v "$candidate")"
            break
        fi
    done
fi
if [[ -z "$PYTHON_BIN" ]]; then
    echo "[planbench setup] no python3 in PATH" >&2; exit 1
fi
VENV_DIR="$PB_DIR/.venv"
if [[ ! -d "$VENV_DIR" ]]; then
    echo "[planbench setup] creating PlanBench venv ($PYTHON_BIN)..."
    "$PYTHON_BIN" -m venv "$VENV_DIR"
fi
"$VENV_DIR/bin/pip" install --quiet --upgrade pip
"$VENV_DIR/bin/pip" install --quiet \
    pyyaml 'tarski==0.7.0' 'pddl==0.2.0' numpy \
    'openai<1.0' transformers httpx

# 6b. Tools venv (--tools) — v2 MCP-tools-on arm (ISS-022) -------------------
# Kept SEPARATE from the v1 .venv so its frozen openai<1.0 corpus stays
# byte-reproducible. Same PlanBench deps, but openai>=1.0 (the
# pddl_eval.vllm_client.VLLMClient / AsyncOpenAI the tool-loop reuses) plus
# mcp (the MCP stdio client). Validated under python3.12 that openai 2.x,
# tarski 0.7.0 and pddl 0.2.0 coexist and that PlanBench's patched load path
# tolerates openai>=1.0 (it only ASSIGNS openai.api_key; the removed-in-v1
# openai.Completion.create is in the dispatch `else` we never reach with a
# pddl_copilot__ engine).
if [[ "$TOOLS" -eq 1 ]]; then
    # mcp requires python>=3.10; the BGU cluster's system python3 is 3.9 (no uv
    # / python3.1x on PATH). Fail loudly with the fix rather than a cryptic
    # "No matching distribution found for mcp" from a 3.9 venv.
    if ! "$PYTHON_BIN" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)'; then
        PYVER="$("$PYTHON_BIN" -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
        echo "[planbench setup] ERROR: --tools needs python>=3.10 for mcp; got $PYTHON_BIN ($PYVER)." >&2
        echo "  BGU cluster: 'module load anaconda && source activate pddl_copilot' first," >&2
        echo "  or pass PLANBENCH_PYTHON=<a python3.10+ binary>." >&2
        exit 1
    fi
    TOOLS_VENV_DIR="$PB_DIR/.venv-tools"
    if [[ ! -d "$TOOLS_VENV_DIR" ]]; then
        echo "[planbench setup] creating PlanBench TOOLS venv ($PYTHON_BIN)..."
        "$PYTHON_BIN" -m venv "$TOOLS_VENV_DIR"
    fi
    "$TOOLS_VENV_DIR/bin/pip" install --quiet --upgrade pip
    "$TOOLS_VENV_DIR/bin/pip" install --quiet \
        pyyaml 'tarski==0.7.0' 'pddl==0.2.0' numpy \
        'openai>=1.0' transformers httpx mcp
    echo "[planbench setup] tools venv ready: $TOOLS_VENV_DIR"
fi

# 7. Print env ---------------------------------------------------------------
print_env "$VAL_DIR" "$PR2_DIR" "$FD_DIR" "$VENV_DIR" "$PB_DIR"

cat <<EOF

[planbench setup] DONE. Smoke test (needs a vLLM server reachable at
\$VLLM_BASE — e.g. cluster: submit via submit_planbench.sh --smoke):

  source <(bash $REPO_ROOT/planbench/setup.sh --print-env-only)
  source "$VENV_DIR/bin/activate"
  export VLLM_BASE="http://localhost:8000/v1"   # point at a running vLLM
  cd "$PB_DIR/plan-bench"
  python3 llm_plan_pipeline.py --task t1 --config blocksworld \\
      --engine pddl_copilot__vllm__Qwen3.5:0.8B \\
      --specific_instances 2 3 4 --verbose True
EOF
