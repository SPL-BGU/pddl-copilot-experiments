#!/usr/bin/env bash
# One-time cluster env setup for pddl-copilot-experiments.
# Run on the BGU ISE-CS-DT login node (slurm.bgu.ac.il) after cloning both repos.
#
# Prereqs:
#   ssh <user>@slurm.bgu.ac.il
#   cd ~
#   git clone https://github.com/SPL-BGU/pddl-copilot-experiments.git
#   git clone https://github.com/SPL-BGU/pddl-copilot.git
#
# Usage:
#   bash ~/pddl-copilot-experiments/cluster-experimenting/setup_env.sh

set -euo pipefail

ENV_NAME="${ENV_NAME:-pddl_copilot}"
PYTHON_VERSION="${PYTHON_VERSION:-3.12}"
JAVA_VERSION="${JAVA_VERSION:-17}"

EXPT_ROOT="${EXPT_ROOT:-$HOME/pddl-copilot-experiments}"
MARKETPLACE_PATH="${PDDL_MARKETPLACE_PATH:-$HOME/pddl-copilot}"

echo "== Sanity checks =="
[ -d "$EXPT_ROOT" ]        || { echo "Error: $EXPT_ROOT not found. Clone pddl-copilot-experiments under \$HOME first."; exit 1; }
[ -d "$MARKETPLACE_PATH" ] || { echo "Error: $MARKETPLACE_PATH not found. Clone pddl-copilot under \$HOME first."; exit 1; }
[ -f "$EXPT_ROOT/requirements.txt" ] || { echo "Error: $EXPT_ROOT/requirements.txt missing."; exit 1; }

echo "== Loading anaconda module =="
module load anaconda

if conda env list | awk '{print $1}' | grep -qx "$ENV_NAME"; then
    echo "Conda env '$ENV_NAME' already exists — reusing (delete with 'conda remove -n $ENV_NAME --all' to rebuild)."
else
    echo "== Creating conda env '$ENV_NAME' (python=$PYTHON_VERSION, openjdk=$JAVA_VERSION) =="
    # openjdk via conda-forge avoids needing a cluster-wide Java module.
    conda create -n "$ENV_NAME" -c conda-forge \
        python="$PYTHON_VERSION" \
        "openjdk=$JAVA_VERSION" \
        -y
fi

source activate "$ENV_NAME"

echo "== Installing Python deps =="
pip install --upgrade pip
pip install -r "$EXPT_ROOT/requirements.txt"

echo "== Pre-creating MCP plugin venvs =="
# Each plugin's launch-server.sh lazily creates a .venv on first MCP spawn.
# Doing it here means the first sbatch doesn't waste compute time on pip install,
# and avoids N parallel jobs racing to populate the same .venv.
for plugin in pddl-solver pddl-validator; do
    plug_dir="$MARKETPLACE_PATH/plugins/$plugin"
    if [ ! -d "$plug_dir" ]; then
        echo "  warn: $plug_dir not found, skipping"
        continue
    fi
    if [ -d "$plug_dir/.venv" ]; then
        echo "  $plugin: .venv already exists, skipping"
        continue
    fi
    echo "  $plugin: creating .venv and installing requirements..."
    python3 -m venv "$plug_dir/.venv"
    "$plug_dir/.venv/bin/pip" install --quiet --upgrade pip
    "$plug_dir/.venv/bin/pip" install --quiet -r "$plug_dir/requirements.txt"
done

echo "== Verification =="
java -version 2>&1 | head -1
python3 -c "import mcp, ollama; print('python deps: mcp + ollama OK')"

echo ""
echo "Done. Activate later with:"
echo "  module load anaconda"
echo "  source activate $ENV_NAME"
echo ""
echo "Next: submit jobs via"
echo "  bash $EXPT_ROOT/cluster-experimenting/submit_all.sh --dry-run   # preview"
echo "  bash $EXPT_ROOT/cluster-experimenting/submit_all.sh             # submit (both models × 5 conditions = 10 jobs)"
