#!/usr/bin/env bash
# PlanBench cluster status — model × task × config matrix.
#
# Dispatched by status.sh --bench planbench. Reads
# results/planbench/slurm_<model>_<jobid>/ on the cluster and reports
# completion per (task, config) cell. No Δ-table / pace / ETA — minimal
# v1 surface; richer machinery (matching status.sh's 5task renderer) can
# come later when there's enough corpus to justify it.
#
# Output mode: terminal (default) or --md.
# Env: REMOTE_USER, REMOTE_HOST, REPO_REMOTE.

set -eo pipefail

REMOTE_USER="${REMOTE_USER:-omereliy}"
REMOTE_HOST="${REMOTE_HOST:-slurm.bgu.ac.il}"
REPO_REMOTE="${REPO_REMOTE:-pddl-copilot-experiments}"

mode="terminal"
for arg in "$@"; do
    case "$arg" in
        --md|--markdown) mode="md" ;;
        --terminal|--pretty) mode="terminal" ;;
        --no-color) ;;  # no-op; status_planbench is monochrome
        *) echo "unknown flag: $arg" >&2; exit 2 ;;
    esac
done

# Single SSH: list PlanBench corpora + per-(task, config) JSON existence
# + per-instance row counts so the renderer can flag partial cells.
remote_payload=$(ssh "${REMOTE_USER}@${REMOTE_HOST}" "bash -s" "$REMOTE_USER" "$REPO_REMOTE" <<'REMOTE'
set -eo pipefail
USER="$1"
REPO="$2"
echo "=== queue ==="
squeue -u "$USER" -r -h -o '%i|%j|%T|%M|%R' 2>/dev/null \
    | grep planbench || true
echo "=== corpora ==="
shopt -s nullglob
for d in "$HOME/$REPO/results/planbench/"slurm_*/; do
    tag=$(basename "$d")
    manifest="$d/manifest.json"
    [ -f "$manifest" ] || continue
    # Count per-task-config files. Engine subdir name is the engine string
    # itself which contains :: — escape it for the find glob.
    for results_dir in "$d/results"/*/*/; do
        config=$(basename "$(dirname "$results_dir")")
        engine=$(basename "$results_dir")
        n=$(find "$results_dir" -maxdepth 1 -name 'task_*.json' 2>/dev/null | wc -l | tr -d ' ')
        printf '%s\t%s\t%s\t%s\n' "$tag" "$config" "$engine" "$n"
    done
done
echo "=== end ==="
REMOTE
)

python3 - "$remote_payload" "$mode" <<'PY'
import sys
from collections import defaultdict

payload, mode = sys.argv[1], sys.argv[2]

CANONICAL_TASKS = ["t1", "t2", "t3", "t4", "t5", "t6", "t7", "t8_1", "t8_2", "t8_3"]
CANONICAL_CONFIGS = ["blocksworld", "logistics", "depots"]

section = None
queue_rows = []
corpora = []  # (tag, config, engine, n_task_files)
for line in payload.splitlines():
    if line.startswith("=== "):
        section = line.strip("= ").strip()
        continue
    if not line.strip():
        continue
    if section == "queue":
        queue_rows.append(line)
    elif section == "corpora":
        parts = line.split("\t")
        if len(parts) == 4:
            tag, config, engine, n = parts
            try:
                n = int(n)
            except ValueError:
                n = 0
            corpora.append((tag, config, engine, n))

# Aggregate per (engine, config) → task count.
agg = defaultdict(lambda: defaultdict(int))
engines = set()
configs_seen = set()
for tag, config, engine, n in corpora:
    agg[engine][config] = max(agg[engine][config], n)
    engines.add(engine)
    configs_seen.add(config)

def fmt_engine_short(engine):
    if engine.startswith("pddl_copilot__"):
        rest = engine[len("pddl_copilot__"):]
        backend, _, model = rest.partition("__")
        return f"{backend}:{model}"
    return engine

print()
if not corpora:
    print("No PlanBench corpora found at results/planbench/slurm_*/ on cluster.")
else:
    header = f"{'engine':<32} " + "  ".join(f"{c:<13}" for c in CANONICAL_CONFIGS)
    if mode == "md":
        print("| engine | " + " | ".join(CANONICAL_CONFIGS) + " |")
        print("|--------|" + "|".join("--------" for _ in CANONICAL_CONFIGS) + "|")
    else:
        print(header)
        print("-" * len(header))
    for engine in sorted(engines):
        cells = []
        for cfg in CANONICAL_CONFIGS:
            done = agg[engine].get(cfg, 0)
            total = len(CANONICAL_TASKS)
            cells.append(f"{done}/{total}")
        short = fmt_engine_short(engine)
        if mode == "md":
            print(f"| {short} | " + " | ".join(cells) + " |")
        else:
            print(f"{short:<32} " + "  ".join(f"{c:<13}" for c in cells))

if queue_rows:
    print()
    print("Queue (PlanBench jobs):")
    for row in queue_rows:
        print(f"  {row}")
elif corpora:
    print()
    print("(no PlanBench jobs currently in queue)")
PY
