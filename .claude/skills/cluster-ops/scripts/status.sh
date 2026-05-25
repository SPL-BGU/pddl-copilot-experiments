#!/usr/bin/env bash
# Cluster status snapshot — rich format with delta-vs-last-invocation.
#
# One SSH call gathers `squeue` + per-cell `wc -l trials.jsonl`. Local
# Python diffs against $STATE_FILE (default ~/.cache/cluster-ops-status.json)
# and renders five sections:
#   1. Header (~hours since last check, or "first run")
#   2. What changed (cells flipped to ✓ this window, new running cells)
#   3. Per-cell progress matrix (5 active models × 8 logical columns —
#      think × {no-tools, tools_all} × {neutral v11-13, steered v14-16})
#   4. Δ since last status (only cells whose count grew, with pace + ETA)
#   5. Roll-up (done X/40, coverage %, running cells, --time watch list)
#   6. Queue (compact pending+running summary; useful when REASON ≠ normal)
#
# Sweep-5 matrix (active 2026-05-23): {no-tools, tools_all_minimal} ×
# {think on, off} = 4 sbatch cells per model. The prompt-variant axis
# (v11-13 neutral / v14-16 steered) lives WITHIN each cell, but status
# splits it out as an explicit 8-column view so the neutral-vs-steered
# breakdown is visible at a glance. Each logical column has a uniform
# 4560-trial denominator (3 variants × 1520 trials/variant).
#
# Arm semantics (which cells get filled by which submit):
#   no-tools-neutral    (v11-13) — main sweep-5 submit (always)
#   no-tools-steered    (v14-16) — 4th-arm control submit
#                                   (run_experiment.py --include-no-tools-steered)
#   tools_all-neutral   (v11-13) — main sweep-5 submit (always)
#   tools_all-steered   (v14-16) — main sweep-5 submit (always, same run as neutral)
#
# Both `tools_all-*` columns are filled by the same sbatch task that
# writes the underlying `slurm_vllm_<model>_<think>_tools_all_minimal/`
# trials.jsonl; the split is a row-level grep on STEERED_VARIANTS_RE.
# `no-tools-steered` is the ONLY column that doesn't inherit queue/
# running attribution from its sibling — main and control submits share
# `cond=no-tools` jnames, so status can't tell them apart at the queue
# layer. tools_per-task_minimal (retired 2026-05-19) and tools_*_guided
# (earlier) result dirs surface in the "skipped (unmatched)" footer;
# query via the analyzer skill if needed.
#
# Output mode (auto by stdout TTY-detect; override with flags):
#   --terminal / --pretty   ANSI-coloured aligned text (default when TTY)
#   --md                    GitHub-flavoured markdown (default when piped)
#   --no-color              suppress ANSI codes in terminal mode
#
# Cache: ~/.cache/cluster-ops-status.json is local-only state. Safe to
# `rm` to reset (next run will be a "first run" with no Δ table).
#
# Env: REMOTE_USER, REMOTE_HOST, REPO_REMOTE, STATE_FILE.

set -eo pipefail

REMOTE_USER="${REMOTE_USER:-omereliy}"
REMOTE_HOST="${REMOTE_HOST:-slurm.bgu.ac.il}"
REPO_REMOTE="${REPO_REMOTE:-pddl-copilot-experiments}"
STATE_FILE="${STATE_FILE:-$HOME/.cache/cluster-ops-status.json}"
# Active prompt variants for the in-flight sweep. Trials.jsonl files can
# carry rows from multiple sweeps (sweep-5 v11-16 append alongside
# sweep-4 v5-7 and sweep-3 v0-2 in the same per-cell file since the
# resume key includes prompt_variant — see pddl_eval/runner.py:441-451).
# These regexes filter cluster-side trial counts so the progress matrix
# reflects ONLY the active sweep.
#
#   ACTIVE_VARIANTS_RE  — full active set (default sweep-5: `1[1-6]`)
#   STEERED_VARIANTS_RE — subset that lands in the steered/control
#                         column (default sweep-5: `1[4-6]`). Set to ''
#                         to disable splitting (sweep-4 replay mode).
#
# Both regexes feed into a `"prompt_variant": <RE>[^0-9]` grep pattern,
# so multi-digit variant ids match correctly. For sweep-4 replay, run:
#   ACTIVE_VARIANTS_RE='[567]' STEERED_VARIANTS_RE='' bash status.sh
# For sweep-3 replay:
#   ACTIVE_VARIANTS_RE='[012]' STEERED_VARIANTS_RE='' bash status.sh
ACTIVE_VARIANTS_RE="${ACTIVE_VARIANTS_RE:-1[1-6]}"
STEERED_VARIANTS_RE="${STEERED_VARIANTS_RE-1[4-6]}"

# Output-mode flags (parsed before SSH so --help works offline).
mode="auto"
color="auto"
for arg in "$@"; do
    case "$arg" in
        --md|--markdown)        mode="md" ;;
        --terminal|--pretty)    mode="terminal" ;;
        --no-color)             color="off" ;;
        -h|--help)
            sed -n '2,40p' "$0"; exit 0 ;;
        *)
            printf 'unknown flag: %s\n' "$arg" >&2; exit 2 ;;
    esac
done

mkdir -p "$(dirname "$STATE_FILE")"

# Single SSH: dump queue + per-cell trial counts as two delimited blocks.
remote_payload=$(ssh "${REMOTE_USER}@${REMOTE_HOST}" "bash -s" "$REMOTE_USER" "$REPO_REMOTE" "$ACTIVE_VARIANTS_RE" "$STEERED_VARIANTS_RE" <<'REMOTE'
set -eo pipefail
USER="$1"
REPO="$2"
VARIANTS_RE="$3"
STEERED_RE="$4"
echo "=== queue ==="
# -r expands array ranges so each pending task is a separate row (otherwise
# squeue collapses pending arrays like 17389411_[6-9] into one row, breaking
# the per-cell count and the "Pending (N)" total).
queue_lines=$(squeue -u "$USER" -r -h -o '%i|%j|%T|%M|%R' 2>/dev/null | sort || true)
printf '%s\n' "$queue_lines"
echo "=== counts ==="
# Per dir, emit `<n_active>\t<n_steered>\t<basename>`. The local parser
# derives neutral = active - steered so sweep-5 can split no-tools cells
# into a main (v11-13) and control (v14-16) column. STEERED_RE empty →
# n_steered=0 unconditionally (sweep-4 replay mode collapses to a single
# count per cell).
#
# Parse trials.jsonl as JSON and dedup by the row-level `key` tuple — the
# harness's resume path can append the same trial twice (timing race between
# completion + checkpoint flush), so raw line counts overstate progress.
# Matches the analyzer's dedup convention so status and analyzer agree.
grep_count() {
    local re="$1" path="$2"
    if [ -z "$re" ]; then echo 0; return; fi
    [ -f "$path" ] || { echo 0; return; }
    python3 - "$re" "$path" <<'PY' 2>/dev/null || echo 0
import json, re, sys
pat = re.compile(sys.argv[1])
seen = set()
with open(sys.argv[2]) as f:
    for line in f:
        try:
            r = json.loads(line)
        except Exception:
            continue
        pv = r.get('result', {}).get('prompt_variant')
        if pv is None: continue
        if not pat.fullmatch(str(pv)): continue
        seen.add(tuple(r.get('key', [])))
print(len(seen))
PY
}
shopt -s nullglob
for d in "$HOME/$REPO/results/"slurm_*/; do
    if [ -f "$d/trials.jsonl" ]; then
        n_active=$(grep_count "$VARIANTS_RE" "$d/trials.jsonl")
        n_steered=$(grep_count "$STEERED_RE" "$d/trials.jsonl")
    else
        n_active=0
        n_steered=0
    fi
    printf '%s\t%s\t%s\n' "$n_active" "$n_steered" "$(basename "$d")"
done
echo "=== manifests ==="
# Emit `<arrayjid>\t<idx>\t<model>\t<think>\t<cond>` rows for every cells.tsv
# whose ArrayJobId currently appears in the queue. This lets the local
# parser resolve packed-array job names (e.g. pddl_rtx_pack2_gemma4_26b-a4b_*
# covers gemma4 AND qwen3.6:35b — the parent name only mentions one model)
# back to the precise (model, think, cond) cell per array task.
array_jids=$(printf '%s\n' "$queue_lines" | awk -F'|' '{split($1,a,"_"); print a[1]}' | sort -u)
for jid in $array_jids; do
    manifest="$HOME/$REPO/cluster-experimenting/logs/${jid}.cells.tsv"
    [ -f "$manifest" ] || continue
    while IFS=$'\t' read -r idx model think cond; do
        [ -n "$idx" ] || continue
        printf '%s\t%s\t%s\t%s\t%s\n' "$jid" "$idx" "$model" "$think" "$cond"
    done < "$manifest"
done
echo "=== end ==="
REMOTE
)

# `steered_enabled` mirrors the bash STEERED_VARIANTS_RE state. When the
# user disables steered tracking (sweep-4 replay: STEERED_VARIANTS_RE=''),
# the Python renderer drops the four `*-steered` logical columns entirely
# so the matrix collapses cleanly to 4 columns × 5 models = 20 cells.
if [ -n "$STEERED_VARIANTS_RE" ]; then
    steered_enabled=1
else
    steered_enabled=0
fi

python3 - "$remote_payload" "$STATE_FILE" "$mode" "$color" "$steered_enabled" <<'PY'
import json, os, re, sys, time

payload, state_file, mode_arg, color_arg = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
steered_enabled = (sys.argv[5] == "1") if len(sys.argv) > 5 else True

# ---- Roster + dimensions (matches submit_with_rtx.sh --all roster) ----
# 2026-05-18 swap: dropped gemma4_31b dense Ollama, added gemma4_26b-a4b
# MoE on vLLM; full roster now backend-unified on vLLM (smoke 17638752).
# 2026-05-17 swap (prior): dropped qwen3_6_27b (slowest cell, ~19h tools×on);
# added Qwen3_5_4B and Qwen3_5_9B to fill the 0.8B → 35B param gap.
ROSTER = ["Qwen3_5_0_8B", "Qwen3_5_4B", "Qwen3_5_9B", "gemma4_26b-a4b", "qwen3_6_35b"]
DISPLAY = {"Qwen3_5_0_8B":"Qwen3.5:0.8B", "Qwen3_5_4B":"Qwen3.5:4B",
           "Qwen3_5_9B":"Qwen3.5:9B", "gemma4_26b-a4b":"gemma4:26b-a4b",
           "qwen3_6_35b":"qwen3.6:35b"}
# Post 2026-05-23 the harness writes a single OUT_DIR shape:
# `slurm_vllm_<model>_<think>_<cond>/`. Legacy `slurm_<model>_<think>_<cond>/`
# dirs (pre-vLLM-unification Ollama corpora — kept as drift anchors) are
# counted in a separate "archived (pre-vLLM)" footer below; they never
# affect the active matrix. The per-model BACKEND map that gated this
# routing in the dual-backend era was retired with the Ollama backend.
# Sweep-5 8-column matrix per model (think ∈ {on,off} × cond ∈
# {no-tools-neutral, no-tools-steered, tools_all-neutral, tools_all-steered}).
# The sbatch-level cond axis is still {no-tools, tools_all_minimal}, but
# each underlying dir's trials are split into a neutral (v11-13) and a
# steered (v14-16) subset by re-grepping on STEERED_VARIANTS_RE. The
# split makes H1 (tools vs no-tools at byte-identical neutral prompt)
# and H2 (steered vs neutral within with-tools) directly readable from
# the status board. tools_per-task_minimal (retired 2026-05-19) and
# tools_*_guided (earlier) no longer appear. The legacy no-tools/think=on
# matrix-gate was lifted 2026-05-12 (commit fe1c061). Order matches
# `short_hdrs` in render_terminal so markdown and terminal renderers
# stay in lock-step.
CELLS = [("on","no-tools-neutral"),("on","no-tools-steered"),
         ("on","tools_all-neutral"),("on","tools_all-steered"),
         ("off","no-tools-neutral"),("off","no-tools-steered"),
         ("off","tools_all-neutral"),("off","tools_all-steered")]
COL_HEADERS = ["on / nt-neut","on / nt-ster","on / tl-neut","on / tl-ster",
               "off / nt-neut","off / nt-ster","off / tl-neut","off / tl-ster"]
# Sweep-4/3 replay mode collapses to neutral-only (4 columns × 5 models = 20
# cells). Steered grep was disabled (STEERED_VARIANTS_RE=''), so steered
# counts would all be 0 and would render as phantom growing rows when the
# underlying sbatch is RUNNING. Filter them out at the source.
if not steered_enabled:
    CELLS = [c for c in CELLS if not c[1].endswith("-steered")]
    COL_HEADERS = [h for h in COL_HEADERS if "-ster" not in h]
# Uniform per-column denominator: each logical column covers 3 variants ×
# 1520 trials/variant = 4560. 1520 trials/variant is the sweep-3-onward
# corpus (CHANGELOG.md:714).
DENOM = {"no-tools-neutral":4560, "no-tools-steered":4560,
         "tools_all-neutral":4560, "tools_all-steered":4560}
# Maps a logical (split) cond to the underlying dirname cond so queue/
# running attribution from the sbatch layer can fan back out to its
# logical children. `no-tools-steered` is the only column that doesn't
# inherit queue state — its sibling main submit shares the same
# `cond=no-tools` jname.
LOGICAL_TO_DIR_COND = {
    "no-tools-neutral":  "no-tools",
    "no-tools-steered":  "no-tools",   # special-cased in cell_status (no queue inheritance)
    "tools_all-neutral": "tools_all_minimal",
    "tools_all-steered": "tools_all_minimal",
}
# Dir-level conds (the actual sbatch/dirname/jname strings). Queue and
# manifest attribution uses this set; the rendered matrix uses the
# logical (split) conds via the COND_SPLIT mapping in the counts loop.
DIR_CONDS = set(LOGICAL_TO_DIR_COND.values())
# Per-model --time pin in submit_full_sweep.sh (2026-05-19):
#   pack3 (Qwen3.5:0.8B/4B/9B): 12h
#   slow models (qwen3.6:35b, gemma4:26b-a4b): 48h
# Used by the watch-list heuristic to flag cells whose elapsed + ETA
# exceed 0.9 × the model's wall-time budget. Fallback: 48h.
TIME_LIMIT_H_BY_MODEL = {
    "Qwen3_5_0_8B": 12, "Qwen3_5_4B": 12, "Qwen3_5_9B": 12,
    "qwen3_6_35b": 48, "gemma4_26b-a4b": 48,
}
TIME_LIMIT_H_DEFAULT = 48

# Job-name short-cond → full cond (used when array tasks have per-cell names).
# `tools-pt`/`tools_pt` keys retained for backwards-compatibility with
# pre-2026-05-19 sweep-3 cells that may still surface in the queue (e.g.
# a resume of a sweep-3 job); they map to the retired condition string
# so the parser doesn't silently classify them as unknown. The split
# `no-tools-steered` logical cond is NOT a sbatch-level cond and never
# appears in jnames — it's a status-side view derived from prompt_variant
# counts; queue rows for `no-tools` jobs always attribute to the main
# (`no-tools`) column.
SHORT_COND = {"tools-pt":"tools_per-task_minimal","tools_pt":"tools_per-task_minimal",
              "tools-all":"tools_all_minimal","tools_all":"tools_all_minimal",
              "notools":"no-tools","no-tools":"no-tools"}

# ---- Parse the SSH payload into queue lines + count lines ----
sections, cur = {}, None
for line in payload.splitlines():
    if line.startswith("=== "):
        cur = line.strip("= ").strip()
        sections[cur] = []
    elif cur is not None:
        sections[cur].append(line)
queue_raw  = [l for l in sections.get("queue",  []) if l.strip()]
count_raw  = [l for l in sections.get("counts", []) if l.strip()]
manifest_raw = [l for l in sections.get("manifests", []) if l.strip()]

# ---- Manifests: (array_jid, idx) → (model_token, think, cond) ----
# Lets us resolve packed-pending array tasks back to their precise cell
# even when the parent template name only mentions one of the packed models
# (e.g. pddl_rtx_pack2_gemma4_26b-a4b_notools covers both gemma4:26b-a4b
# and qwen3.6:35b — the parent jname only mentions gemma4).
MODEL_TAG_TO_ROSTER = {"Qwen3.5:0.8B":"Qwen3_5_0_8B", "Qwen3.5:4B":"Qwen3_5_4B",
                       "Qwen3.5:9B":"Qwen3_5_9B", "gemma4:26b-a4b":"gemma4_26b-a4b",
                       "qwen3.6:35b":"qwen3_6_35b"}
manifest_index = {}
for line in manifest_raw:
    parts = line.split("\t")
    if len(parts) != 5: continue
    jid, idx, model_tag, think, cond = parts
    m = MODEL_TAG_TO_ROSTER.get(model_tag)
    if m and cond in DIR_CONDS:
        manifest_index[(jid, idx)] = (m, think, cond)

# ---- Counts: dirname → (model, think, cond) ----
# Active dirs: `slurm_vllm_<model>_<think>_<cond>/`. Legacy
# `slurm_<model>_<think>_<cond>/` (no `vllm_` infix) are archived
# pre-vLLM-unification corpora — counted in a separate footer so the
# active matrix isn't polluted by drift-anchor history.
#
# Each count line is `<n_active>\t<n_steered>\t<dirname>`. Every dir
# (both no-tools and tools_all_minimal) is split into a neutral and a
# steered logical column: neutral = active - steered. With STEERED_RE=''
# on the wrapper, n_steered=0 unconditionally → all rows count as
# neutral (sweep-4 replay behaviour, where the steered columns stay
# empty).
COND_SPLIT = {
    "no-tools":          ("no-tools-neutral",  "no-tools-steered"),
    "tools_all_minimal": ("tools_all-neutral", "tools_all-steered"),
}
counts, unknown, archived_legacy = {}, [], []
malformed = 0   # finding #10: count silently-dropped count_raw lines and warn at end.
oversteered = []   # finding #8: dirs where n_steered > n_active (regex misconfig).
for line in count_raw:
    parts = line.split("\t", 2)
    if len(parts) != 3:
        malformed += 1
        continue
    n_active_str, n_steered_str, dirname = parts
    if not dirname.startswith("slurm_"): continue
    try:
        n_active = int(n_active_str)
        n_steered = int(n_steered_str)
    except ValueError:
        malformed += 1
        continue
    rem = dirname[len("slurm_"):]
    if rem.startswith("vllm_"):
        rem = rem[len("vllm_"):]
    else:
        archived_legacy.append(dirname)
        continue
    matched = None
    for m in ROSTER:
        if rem.startswith(m + "_"):
            tail = rem[len(m)+1:]
            for th in ("on","off","default"):
                if tail.startswith(th + "_"):
                    dir_cond = tail[len(th)+1:]
                    if dir_cond in COND_SPLIT:
                        matched = (m, th, dir_cond)
                    break
            break
    if not matched:
        unknown.append(dirname); continue
    m, th, dir_cond = matched
    neutral_col, steered_col = COND_SPLIT[dir_cond]
    if n_steered > n_active:
        oversteered.append((dirname, n_active, n_steered))
    n_neutral = max(0, n_active - n_steered)
    counts[(m, th, neutral_col)] = n_neutral
    if steered_enabled:
        counts[(m, th, steered_col)] = n_steered

# Surface bash → Python wire-format / regex-config issues to stderr without
# failing the run. Both are advisory: the matrix still renders, but the
# operator may be looking at degraded data.
if malformed and count_raw:
    print(f"warn: dropped {malformed} malformed count_raw line(s); check remote heredoc wire format",
          file=sys.stderr)
if oversteered:
    sample = ", ".join(f"{d}({a}/{s})" for d, a, s in oversteered[:3])
    print(f"warn: STEERED_VARIANTS_RE matched more rows than ACTIVE_VARIANTS_RE in "
          f"{len(oversteered)} dir(s) (e.g. {sample}); check regex overlap "
          f"(neutral counts clamped to 0)", file=sys.stderr)

# ---- Queue ----
queue = []
for line in queue_raw:
    parts = line.split("|", 4)
    if len(parts) != 5: continue
    queue.append(dict(zip(("jid","jname","state","elapsed","reason"), parts)))

def jname_to_cell(jname):
    """Per-cell array task name → (model,think,cond).
    vLLM:   pddl_vllm_Qwen3_5_9B_on_notools
    Ollama (legacy): pddl_<model>_<think>_<cond> — no `vllm_` infix.
    """
    if not jname.startswith("pddl_"): return None
    rem = jname[len("pddl_"):]
    if rem.startswith("vllm_"):
        rem = rem[len("vllm_"):]
    for m in ROSTER:
        if rem.startswith(m + "_"):
            tail = rem[len(m)+1:]
            for th in ("on","off","default"):
                if tail.startswith(th + "_"):
                    return (m, th, SHORT_COND.get(tail[len(th)+1:]))
            break
    return None

def jname_model(jname):
    """Parent-template array name → model token, or None.
    Used for pending tasks whose per-cell name hasn't materialised yet
    (e.g. 'pddl_rtx_pack3_Qwen3_5_0_8B' covers all 6 cells of each model
    in the small/mid pack — manifest resolves to the precise cell)."""
    for m in ROSTER:
        if m in jname: return m
    return None

cell_running, cell_pending, model_pending = {}, {}, set()
for q in queue:
    cell = jname_to_cell(q["jname"])
    if not (cell and cell[2] in DIR_CONDS):
        # Fall back to the manifest: ArrayJobId + ArrayTaskId → cell.
        jid_parts = q["jid"].split("_", 1)
        if len(jid_parts) == 2:
            cell = manifest_index.get((jid_parts[0], jid_parts[1]))
    if cell and cell[2] in DIR_CONDS:
        if q["state"] == "RUNNING":   cell_running[cell] = q
        elif q["state"] == "PENDING": cell_pending[cell] = q
    elif q["state"] == "PENDING":
        m = jname_model(q["jname"])
        if m: model_pending.add(m)

# ---- Diff vs cached state ----
prev_state = {}
if os.path.exists(state_file):
    try: prev_state = json.load(open(state_file))
    except Exception: prev_state = {}
prev_ts = prev_state.get("timestamp")
prev_counts = {tuple(k.split("|")): v for k, v in prev_state.get("counts", {}).items()
               if len(k.split("|")) == 3}
now_ts = int(time.time())
window_s = (now_ts - prev_ts) if prev_ts else None
window_h = (window_s / 3600) if window_s else None

def fmt_window(s):
    if s is None: return None
    if s < 60: return f"{s}s"
    if s < 3600: return f"{s//60}m"
    return f"{s/3600:.1f}h"
window_str = fmt_window(window_s)

deltas = {}
for cell, n in counts.items():
    prev = prev_counts.get(cell, 0)
    d = n - prev
    denom = DENOM[cell[2]]
    deltas[cell] = {"now":n, "prev":prev, "delta":d, "denom":denom,
                    "pct":100*n/denom if denom else 0, "pace_s":None, "eta_h":None}

# Finding #3: pace_s / eta_h must be computed at the underlying sbatch
# level, not per logical column. tl-neut and tl-ster share the same
# physical sbatch (the with-tools dir's trials.jsonl). Aggregating
# (delta, now, denom) by dir_cell and writing the result back to both
# logical children gives correct per-trial pace and a true ETA for the
# underlying job. Siblings will show identical pace/eta — visually
# signalling "these belong to the same sbatch".
dir_totals = {}
for cell, d in deltas.items():
    m, th, c = cell
    dir_cond = LOGICAL_TO_DIR_COND[c]
    dir_key = (m, th, dir_cond)
    t = dir_totals.setdefault(dir_key, {"delta": 0, "now": 0, "denom": 0})
    t["delta"] += d["delta"]
    t["now"] += d["now"]
    # Only fold a logical column's denom into the dir-level total when
    # that arm is actually active in the current submit. Without this,
    # main-only no-tools cells (steered arm dormant unless
    # `--include-no-tools-steered` ran) doubled their dir denom from
    # 4560 to 9120, halving `pace_s` and inflating `eta_h` ~2×.
    # tools_all sbatch always emits both arms together (one with-tools
    # cell produces v11..v16 in a single trials.jsonl), so for that
    # dir_cond we always sum. no-tools dirs sum a sibling's denom only
    # when that arm has on-disk evidence — the steered arm only fills
    # under `--include-no-tools-steered`.
    if dir_cond == "tools_all_minimal" or d["now"] > 0:
        t["denom"] += d["denom"]
for cell, d in deltas.items():
    m, th, c = cell
    t = dir_totals[(m, th, LOGICAL_TO_DIR_COND[c])]
    pace_s = (window_s / t["delta"]) if (t["delta"] > 0 and window_s) else None
    eta_h = ((t["denom"] - t["now"]) * pace_s / 3600) if (pace_s and t["now"] < t["denom"]) else None
    d["pace_s"] = pace_s
    d["eta_h"] = eta_h

# ---- "What changed" since last invocation ----
# Only meaningful when we have a prior cache to diff against; on first run
# every cell trivially looks "newly started", which is noise.
done_now, started_now = [], []
if prev_ts:
    for cell, d in deltas.items():
        if d["now"] >= d["denom"] and 0 < d["prev"] < d["denom"]:
            done_now.append((cell, d["prev"]))
        # Finding #5: the prev=0 → now>0 branch must ALSO require now<denom.
        # Without it, a cell that arrived already-complete (e.g. from a
        # pre-split cache where the prev key didn't match the new logical
        # key, so prev=0) gets mislabelled as "newly started" instead of
        # silently passed over. The post-upgrade noisefloor is otherwise
        # ~30 fake ▶🆕 bullets per first run.
        elif d["prev"] == 0 and 0 < d["now"] < d["denom"]:
            started_now.append((cell, d["now"]))

# ---- Cell-status classification (shared by both renderers) ----
# Returns one of: done, growing, stalled, pending_rerun, pending_fresh, empty.
# Logical cells are split (neutral/steered); queue + pending attribution
# is derived from the underlying dir-level cond via LOGICAL_TO_DIR_COND.
# no-tools-steered is the one exception: main and control submits share
# cond=no-tools jnames, so we can't tell which arm a queue row belongs
# to → classify on counts only.
def cell_status(cell):
    m, th, c = cell
    skip_queue = (c == "no-tools-steered")
    dir_cell = (m, th, LOGICAL_TO_DIR_COND[c])
    n = counts.get(cell, 0); denom = DENOM[c]
    grew = prev_ts is not None and deltas.get(cell, {}).get("delta", 0) > 0
    if cell not in counts:
        # RUNNING but trials.jsonl not yet created (vLLM warmup).
        if not skip_queue and dir_cell in cell_running:
            return "growing"
        if not skip_queue and (dir_cell in cell_pending or m in model_pending):
            return "pending_fresh"
        return "empty"
    if n >= denom:                                                 return "done"
    if grew:                                                       return "growing"
    if not skip_queue and dir_cell in cell_running:                return "growing"
    if not skip_queue and (dir_cell in cell_pending or m in model_pending):
        return "pending_rerun" if n > 0 else "pending_fresh"
    if n > 0:                                                      return "stalled"
    return "empty"

def cell_label(cell):
    m, th, c = cell
    # The `.get(c, c)` fallback prints any unmapped cond as-is — safe for
    # an unexpected cache key (renders as itself instead of crashing).
    short = {"no-tools-neutral":  "nt-neut",
             "no-tools-steered":  "nt-ster",
             "tools_all-neutral": "tl-neut",
             "tools_all-steered": "tl-ster"}.get(c, c)
    return f"{DISPLAY[m]} {th}/{short}"

def parse_elapsed_h(s):
    """squeue %M: 'D-HH:MM:SS' | 'HH:MM:SS' | 'MM:SS'."""
    if not s or s == "0:00": return 0.0
    days = 0
    if "-" in s:
        d, _, s = s.partition("-"); days = int(d)
    parts = s.split(":")
    if len(parts) == 3: h, mi, se = parts
    elif len(parts) == 2: h, mi, se = "0", parts[0], parts[1]
    else: return 0.0
    return days*24 + int(h) + int(mi)/60 + int(se)/3600

# ---- Roll-up totals (shared by both renderers) ----
done_cnt = sum(1 for d in deltas.values() if d["now"] >= d["denom"])
total_expected = len(ROSTER) * len(CELLS)
total_now = sum(d["now"] for d in deltas.values())
total_denom = len(ROSTER) * sum(DENOM[c] for _, c in CELLS)
coverage = (100*total_now/total_denom) if total_denom else 0

watch = []
# Finding #1: cell_running is keyed by dir-level cond, deltas by logical
# (split) cond. Without dedup, every RUNNING tools_all sbatch emits TWO
# watch entries (one per tl-neut / tl-ster sibling). De-dupe by dir_cell
# so each physical sbatch produces at most one watch line. The no-tools-
# steered skip stays — control-arm runs in a separate submit whose
# elapsed isn't what cell_running has for the main no-tools sbatch.
seen_dirs = set()
for cell, d in deltas.items():
    m, th, c = cell
    if c == "no-tools-steered": continue
    dir_cell = (m, th, LOGICAL_TO_DIR_COND.get(c, c))
    if dir_cell in seen_dirs: continue
    if dir_cell not in cell_running: continue
    seen_dirs.add(dir_cell)
    elapsed_h = parse_elapsed_h(cell_running[dir_cell]["elapsed"])
    budget_h = TIME_LIMIT_H_BY_MODEL.get(m, TIME_LIMIT_H_DEFAULT)
    # Watch lines now name the dir-level sbatch (e.g. "Qwen3.5:9B on/tools_all")
    # since the ETA covers BOTH neutral and steered halves of that run.
    dir_label = f"{DISPLAY[m]} {th}/{LOGICAL_TO_DIR_COND.get(c, c)}"
    if d["eta_h"] is not None and elapsed_h + d["eta_h"] > 0.9 * budget_h:
        watch.append(f"{dir_label} ({elapsed_h:.0f}h+{d['eta_h']:.0f}h ETA → over 0.9×{budget_h}h)")

run_jids = sorted({q["jid"] for q in cell_running.values()})
running_jobs = [q for q in queue if q["state"] == "RUNNING"]
pending_jobs = [q for q in queue if q["state"] == "PENDING"]
growing_cells = sorted(((c,d) for c,d in deltas.items() if d["delta"] > 0),
                       key=lambda x: x[1]["pct"], reverse=True) if prev_ts else []

# =========================================================================
#                          MARKDOWN RENDERER
# =========================================================================
def render_markdown():
    out = []
    if window_str is not None:
        out.append(f"## Status — ~{window_str} since last check\n")
    else:
        out.append("## Status — first run (no prior state)\n")

    if done_now or started_now:
        out.append("### What changed")
        for cell, prev in done_now:
            out.append(f"- ✓ **{cell_label(cell)}** flipped to 100% (was {prev}/{DENOM[cell[2]]})")
        for cell, n in started_now:
            out.append(f"- ▶🆕 **{cell_label(cell)}** started ({n}/{DENOM[cell[2]]} trials)")
        out.append("")

    out.append("### Per-cell progress (denom 4560 per column · nt=no-tools · tl=tools_all · neut=v11-13 · ster=v14-16)")
    out.append("| Model | " + " | ".join(COL_HEADERS) + " |")
    out.append("|" + "|".join(["---"] * (1 + len(COL_HEADERS))) + "|")
    icon_md = {"done":"✓", "growing":"▶", "stalled":"⏸",
               "pending_rerun":"PD↻", "pending_fresh":"PD", "empty":"_-_"}
    for m in ROSTER:
        row = [f"**{DISPLAY[m]}**"]
        for th, c in CELLS:
            cell = (m, th, c)
            st = cell_status(cell)
            if cell in counts:
                n = counts[cell]; denom = DENOM[c]
                pct = 100*n/denom if denom else 0
                row.append(f"{n}/{denom} (**{pct:.1f}%**) {icon_md[st]}")
            elif st == "pending_fresh":
                row.append("0/— PD")
            else:
                row.append("0/— _-_")
        out.append("| " + " | ".join(row) + " |")
    out.append("")

    hdr = f" (window: ~{window_str})" if window_str else " (first run — no delta)"
    out.append(f"### Δ since last status{hdr}")
    if growing_cells:
        out.append("| Cell | Prev → Now | Δ | pace | ETA |")
        out.append("|---|---|---|---|---|")
        for cell, d in growing_cells:
            prev_now = f"{d['prev']} → **{d['now']}**" + (" ✓" if d['now'] >= d['denom'] else "")
            pace = f"~{d['pace_s']:.0f} s/trial" if d["pace_s"] else "—"
            eta  = "**DONE**" if d['now'] >= d['denom'] else (f"~{d['eta_h']:.1f}h" if d['eta_h'] is not None else "—")
            out.append(f"| {cell_label(cell)} | {prev_now} | +{d['delta']} | {pace} | {eta} |")
    else:
        out.append("_no cells advanced this window_")
    out.append("")

    out.append("### Roll-up")
    out.append(f"- **Done**: {done_cnt} / {total_expected} cells ({100*done_cnt//total_expected if total_expected else 0}%)")
    out.append(f"- **Trial coverage**: {total_now/1000:.1f}K / {total_denom/1000:.0f}K ≈ **{coverage:.0f}%**")
    out.append(f"- **Running**: {len(cell_running)} cells" + (f" (jobs {', '.join(run_jids)})" if run_jids else ""))
    out.append(f"- **Watch list**: {'; '.join(watch) if watch else 'none'}")

    if running_jobs or pending_jobs:
        out.append("")
        out.append("### Queue")
        if running_jobs:
            out.append(f"- **Running** ({len(running_jobs)}): " + ", ".join(q["jid"] for q in running_jobs))
        if pending_jobs:
            by_reason = {}
            for q in pending_jobs:
                by_reason.setdefault(q["reason"], []).append(q["jid"])
            out.append(f"- **Pending** ({len(pending_jobs)}): " +
                       ", ".join(f"{r} ×{len(jids)}" for r, jids in by_reason.items()))

    if unknown:
        out.append("")
        out.append(f"_(skipped {len(unknown)} unmatched dirs: {', '.join(unknown[:3])}{'…' if len(unknown)>3 else ''})_")
    if archived_legacy:
        out.append(f"_(ignored {len(archived_legacy)} archived pre-vLLM dirs: {', '.join(archived_legacy[:3])}{'…' if len(archived_legacy)>3 else ''})_")

    return "\n".join(out)

# =========================================================================
#                          TERMINAL RENDERER
# =========================================================================
# ANSI helpers — visible-width-aware padding so colours don't break columns.
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
def _vlen(s):  return len(ANSI_RE.sub("", s))
def _pad(s, w, align="left"):
    pad = w - _vlen(s)
    if pad <= 0: return s
    return (" "*pad + s) if align == "right" else (s + " "*pad)

def render_terminal(use_color):
    if use_color:
        BOLD, DIM, RESET = "\x1b[1m", "\x1b[2m", "\x1b[0m"
        GREEN, CYAN, YELLOW, RED, GREY = "\x1b[32m","\x1b[36m","\x1b[33m","\x1b[31m","\x1b[90m"
    else:
        BOLD = DIM = RESET = GREEN = CYAN = YELLOW = RED = GREY = ""

    # Status → (icon, colour) — single-glyph icons keep alignment honest.
    ICONS = {
        "done":          ("✓",   GREEN),
        "growing":       ("▶",   CYAN),
        "stalled":       ("⏸",   RED),
        "pending_rerun": ("↻",   YELLOW),
        "pending_fresh": ("·",   GREY),
        "empty":         ("—",   GREY),
    }

    def H1(s): return f"{BOLD}{s}{RESET}"
    def H2(s): return f"{BOLD}{CYAN}{s}{RESET}"
    out = []

    # -- Header
    if window_str is not None:
        out.append(H1(f"Cluster Status") + DIM + f"  ~{window_str} since last check" + RESET)
    else:
        out.append(H1(f"Cluster Status") + DIM + "  first run (no prior state)" + RESET)
    out.append("")

    # -- What changed
    if done_now or started_now:
        out.append(H2("What changed"))
        for cell, prev in done_now:
            icon, col = ICONS["done"]
            out.append(f"  {col}{icon}{RESET} {cell_label(cell)} → 100% "
                       + DIM + f"(was {prev}/{DENOM[cell[2]]})" + RESET)
        for cell, n in started_now:
            icon, col = ICONS["growing"]
            out.append(f"  {col}{icon}{RESET} {cell_label(cell)} started "
                       + DIM + f"({n}/{DENOM[cell[2]]} trials)" + RESET)
        out.append("")

    # -- Per-cell progress matrix
    out.append(H2("Per-cell progress")
               + DIM + "  (denom 4560/col · nt=no-tools · tl=tools_all · neut=v11-13 · ster=v14-16)" + RESET)
    short_hdrs = ["on/nt-neut", "on/nt-ster", "on/tl-neut", "on/tl-ster",
                  "off/nt-neut","off/nt-ster","off/tl-neut","off/tl-ster"]
    MODEL_W = 14   # "Qwen3.5:0.8B" = 12 + slack
    CELL_W  = 12   # tighter to fit 8 cells without wrapping a wide terminal
    header = _pad("Model", MODEL_W) + "".join(_pad(h, CELL_W, "left") for h in short_hdrs)
    out.append("  " + DIM + header + RESET)
    out.append("  " + DIM + "─" * _vlen(header) + RESET)
    for m in ROSTER:
        row = _pad(DISPLAY[m], MODEL_W)
        for th, c in CELLS:
            cell = (m, th, c)
            st = cell_status(cell)
            icon, col = ICONS[st]
            if cell in counts:
                n = counts[cell]; denom = DENOM[c]
                pct = 100*n/denom if denom else 0
                txt = f"{col}{icon}{RESET} {pct:5.1f}%"
            elif st == "pending_fresh":
                txt = f"{col}{icon}{RESET} {DIM}pending{RESET}"
            else:
                txt = f"{col}{icon}{RESET} {DIM}—{RESET}"
            row += _pad(txt, CELL_W)
        out.append("  " + row)
    out.append("")
    out.append("  " + DIM + "Legend: " + RESET +
               f"{GREEN}✓{RESET} done · {CYAN}▶{RESET} running · {RED}⏸{RESET} stalled · "
               f"{YELLOW}↻{RESET} pending rerun · {GREY}·{RESET} pending fresh")
    out.append("")

    # -- Δ table
    if window_str:
        out.append(H2("Δ since last status") + DIM + f"  (~{window_str})" + RESET)
    else:
        out.append(H2("Δ since last status") + DIM + "  (first run — no delta)" + RESET)
    if growing_cells:
        # Columns: Cell | Prev → Now | Δ | pace | ETA
        cw = (32, 18, 7, 14, 8)
        hdr = (_pad("Cell", cw[0]) + _pad("Prev → Now", cw[1])
               + _pad("Δ", cw[2], "right") + " "
               + _pad("pace", cw[3]) + _pad("ETA", cw[4], "right"))
        out.append("  " + DIM + hdr + RESET)
        out.append("  " + DIM + "─" * _vlen(hdr) + RESET)
        for cell, d in growing_cells:
            done_mark = (" " + GREEN + "✓" + RESET) if d['now'] >= d['denom'] else ""
            prev_now = f"{d['prev']} → {BOLD}{d['now']}{RESET}{done_mark}"
            pace = f"~{d['pace_s']:.0f} s/trial" if d["pace_s"] else "—"
            eta  = (f"{BOLD}{GREEN}DONE{RESET}" if d['now'] >= d['denom']
                    else (f"~{d['eta_h']:.1f}h" if d['eta_h'] is not None else "—"))
            row = (_pad(cell_label(cell), cw[0]) + _pad(prev_now, cw[1])
                   + _pad(f"+{d['delta']}", cw[2], "right") + " "
                   + _pad(pace, cw[3]) + _pad(eta, cw[4], "right"))
            out.append("  " + row)
    else:
        out.append("  " + DIM + "no cells advanced this window" + RESET)
    out.append("")

    # -- Roll-up
    out.append(H2("Roll-up"))
    pct_done = (100*done_cnt//total_expected) if total_expected else 0
    out.append(f"  {DIM}Done           {RESET}{BOLD}{done_cnt}/{total_expected}{RESET} cells ({pct_done}%)")
    out.append(f"  {DIM}Trial coverage {RESET}{BOLD}{total_now/1000:.1f}K{RESET} / {total_denom/1000:.0f}K (~{coverage:.0f}%)")
    run_str = f"{len(cell_running)} cells" + (f"  {DIM}jobs {', '.join(run_jids)}{RESET}" if run_jids else "")
    out.append(f"  {DIM}Running        {RESET}{run_str}")
    if watch:
        out.append(f"  {DIM}Watch list     {RESET}{YELLOW}{'; '.join(watch)}{RESET}")
    else:
        out.append(f"  {DIM}Watch list     none{RESET}")
    out.append("")

    # -- Queue
    if running_jobs or pending_jobs:
        out.append(H2("Queue"))
        if running_jobs:
            out.append(f"  {DIM}Running ({len(running_jobs)}){RESET}  "
                       + ", ".join(q["jid"] for q in running_jobs))
        if pending_jobs:
            by_reason = {}
            for q in pending_jobs:
                by_reason.setdefault(q["reason"], []).append(q["jid"])
            out.append(f"  {DIM}Pending ({len(pending_jobs)}){RESET}  "
                       + ", ".join(f"{r} {DIM}×{RESET}{len(jids)}" for r, jids in by_reason.items()))

    if unknown:
        out.append("")
        out.append(f"  {DIM}(skipped {len(unknown)} unmatched dirs: "
                   f"{', '.join(unknown[:3])}{'…' if len(unknown)>3 else ''}){RESET}")
    if archived_legacy:
        out.append(f"  {DIM}(ignored {len(archived_legacy)} archived pre-vLLM dirs: "
                   f"{', '.join(archived_legacy[:3])}{'…' if len(archived_legacy)>3 else ''}){RESET}")

    return "\n".join(out)

# ---- Mode selection ----
if mode_arg == "auto":
    mode_arg = "terminal" if sys.stdout.isatty() else "md"
use_color = (color_arg != "off") and sys.stdout.isatty()

if mode_arg == "md":
    print(render_markdown())
else:
    print(render_terminal(use_color=use_color))

# Save state for next invocation (regardless of render mode).
new_state = {"timestamp": now_ts,
             "counts": {f"{m}|{t}|{c}": n for (m,t,c), n in counts.items()}}
with open(state_file, "w") as f:
    json.dump(new_state, f)
PY
