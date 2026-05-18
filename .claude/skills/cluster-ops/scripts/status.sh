#!/usr/bin/env bash
# Cluster status snapshot — rich format with delta-vs-last-invocation.
#
# One SSH call gathers `squeue` + per-cell `wc -l trials.jsonl`. Local
# Python diffs against $STATE_FILE (default ~/.cache/cluster-ops-status.json)
# and renders five sections:
#   1. Header (~hours since last check, or "first run")
#   2. What changed (cells flipped to ✓ this window, new running cells)
#   3. Per-cell progress matrix (4 active models × 5 think×cond cells)
#   4. Δ since last status (only cells whose count grew, with pace + ETA)
#   5. Roll-up (done X/20, coverage %, running cells, --time watch list)
#   6. Queue (compact pending+running summary; useful when REASON ≠ normal)
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

# Output-mode flags (parsed before SSH so --help works offline).
mode="auto"
color="auto"
for arg in "$@"; do
    case "$arg" in
        --md|--markdown)        mode="md" ;;
        --terminal|--pretty)    mode="terminal" ;;
        --no-color)             color="off" ;;
        -h|--help)
            sed -n '2,18p' "$0"; exit 0 ;;
        *)
            printf 'unknown flag: %s\n' "$arg" >&2; exit 2 ;;
    esac
done

mkdir -p "$(dirname "$STATE_FILE")"

# Single SSH: dump queue + per-cell trial counts as two delimited blocks.
remote_payload=$(ssh "${REMOTE_USER}@${REMOTE_HOST}" "bash -s" "$REMOTE_USER" "$REPO_REMOTE" <<'REMOTE'
set -eo pipefail
USER="$1"
REPO="$2"
echo "=== queue ==="
# -r expands array ranges so each pending task is a separate row (otherwise
# squeue collapses pending arrays like 17389411_[6-9] into one row, breaking
# the per-cell count and the "Pending (N)" total).
queue_lines=$(squeue -u "$USER" -r -h -o '%i|%j|%T|%M|%R' 2>/dev/null | sort || true)
printf '%s\n' "$queue_lines"
echo "=== counts ==="
shopt -s nullglob
for d in "$HOME/$REPO/results/"slurm_*/; do
    if [ -f "$d/trials.jsonl" ]; then
        n=$(wc -l < "$d/trials.jsonl")
    else
        n=0
    fi
    printf '%s\t%s\n' "$n" "$(basename "$d")"
done
echo "=== manifests ==="
# Emit `<arrayjid>\t<idx>\t<model>\t<think>\t<cond>` rows for every cells.tsv
# whose ArrayJobId currently appears in the queue. This lets the local
# parser resolve packed-array job names (e.g. pddl_rtx_pack2_gemma4_31b_*
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

python3 - "$remote_payload" "$STATE_FILE" "$mode" "$color" <<'PY'
import json, os, re, sys, time

payload, state_file, mode_arg, color_arg = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]

# ---- Roster + dimensions (matches submit_with_rtx.sh --all roster) ----
# 2026-05-17 swap: dropped qwen3_6_27b (slowest cell, ~19h tools×on);
# added Qwen3_5_4B and Qwen3_5_9B to fill the 0.8B → 35B param gap.
ROSTER = ["Qwen3_5_0_8B", "Qwen3_5_4B", "Qwen3_5_9B", "gemma4_31b", "qwen3_6_35b"]
DISPLAY = {"Qwen3_5_0_8B":"Qwen3.5:0.8B", "Qwen3_5_4B":"Qwen3.5:4B",
           "Qwen3_5_9B":"Qwen3.5:9B", "gemma4_31b":"gemma4:31b",
           "qwen3_6_35b":"qwen3.6:35b"}
# Canonical backend per model (2026-05-17). Dirs from the OTHER backend
# are skipped during counting — a model is fully owned by one backend so
# the matrix reflects the paper-corpus choice and partial runs on the
# wrong backend don't pollute progress. vLLM cells live under
# `slurm_vllm_<model>_<think>_<cond>/`; Ollama cells under
# `slurm_<model>_<think>_<cond>/`. qwen3_6_35b flipped ollama → vllm on
# 2026-05-17 alongside the roster swap; the prior Ollama 35B corpus is
# checkpointed under `checkpoints/cluster-2026{0514,0517}/`.
BACKEND = {"Qwen3_5_0_8B":"vllm", "Qwen3_5_4B":"vllm", "Qwen3_5_9B":"vllm",
           "qwen3_6_35b":"vllm", "gemma4_31b":"ollama"}
# Full 6-cell matrix per model (think ∈ {on,off} × cond ∈ {no-tools, tools_pt,
# tools_all}). The legacy no-tools/think=on gate was lifted 2026-05-12
# (commit fe1c061) to complete the ablation dimension. Order matches
# `short_hdrs` in render_terminal so the markdown and terminal renderers
# render the same column sequence.
CELLS = [("on","no-tools"),("on","tools_per-task_minimal"),("on","tools_all_minimal"),
         ("off","no-tools"),("off","tools_per-task_minimal"),("off","tools_all_minimal")]
COL_HEADERS = ["on / no-tools","on / tools_pt","on / tools_all",
               "off / no-tools","off / tools_pt","off / tools_all"]
DENOM = {"no-tools":4560, "tools_per-task_minimal":4560, "tools_all_minimal":4560}
TIME_LIMIT_H = 72  # current --time per cell

# Job-name short-cond → full cond (used when array tasks have per-cell names).
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
# (e.g. pddl_rtx_pack2_gemma4_31b_notools covers both gemma4:31b and
# qwen3.6:35b — the parent jname only mentions gemma4).
MODEL_TAG_TO_ROSTER = {"Qwen3.5:0.8B":"Qwen3_5_0_8B", "Qwen3.5:4B":"Qwen3_5_4B",
                       "Qwen3.5:9B":"Qwen3_5_9B", "gemma4:31b":"gemma4_31b",
                       "qwen3.6:35b":"qwen3_6_35b"}
manifest_index = {}
for line in manifest_raw:
    parts = line.split("\t")
    if len(parts) != 5: continue
    jid, idx, model_tag, think, cond = parts
    m = MODEL_TAG_TO_ROSTER.get(model_tag)
    if m and cond in DENOM:
        manifest_index[(jid, idx)] = (m, think, cond)

# ---- Counts: dirname → (model, think, cond) ----
# Two dir families exist on disk:
#   * `slurm_<model>_<think>_<cond>/`        Ollama backend
#   * `slurm_vllm_<model>_<think>_<cond>/`   vLLM backend
# We strip the optional "vllm_" prefix, classify the dir's backend, then
# count it only if it matches BACKEND[model] — the canonical backend for
# the paper corpus. Dirs on the non-canonical backend (e.g. an Ollama
# slurm_qwen3_6_35b_* from the prior corpus, now that 35B is owned by
# vLLM) are reported under "skipped (wrong backend)" instead of polluting
# the matrix or the unknown list.
counts, unknown, wrong_backend = {}, [], []
for line in count_raw:
    n_str, _, dirname = line.partition("\t")
    if not dirname.startswith("slurm_"): continue
    try: n = int(n_str)
    except ValueError: continue
    rem = dirname[len("slurm_"):]
    if rem.startswith("vllm_"):
        rem = rem[len("vllm_"):]
        dir_backend = "vllm"
    else:
        dir_backend = "ollama"
    matched = None
    backend_mismatch = False
    for m in ROSTER:
        if rem.startswith(m + "_"):
            if BACKEND.get(m) != dir_backend:
                backend_mismatch = True
                break
            tail = rem[len(m)+1:]
            for th in ("on","off","default"):
                if tail.startswith(th + "_"):
                    cond = tail[len(th)+1:]
                    if cond in DENOM:
                        matched = (m, th, cond)
                    break
            break
    if matched:                  counts[matched] = n
    elif backend_mismatch:       wrong_backend.append(dirname)
    else:                        unknown.append(dirname)

# ---- Queue ----
queue = []
for line in queue_raw:
    parts = line.split("|", 4)
    if len(parts) != 5: continue
    queue.append(dict(zip(("jid","jname","state","elapsed","reason"), parts)))

def jname_to_cell(jname):
    """Per-cell array task name → (model,think,cond).
    Ollama: pddl_gemma4_31b_on_tools-pt
    vLLM:   pddl_vllm_Qwen3_5_9B_on_notools
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
    if not (cell and cell[2] in DENOM):
        # Fall back to the manifest: ArrayJobId + ArrayTaskId → cell.
        jid_parts = q["jid"].split("_", 1)
        if len(jid_parts) == 2:
            cell = manifest_index.get((jid_parts[0], jid_parts[1]))
    if cell and cell[2] in DENOM:
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
    pace_s = (window_s / d) if (d > 0 and window_s) else None
    eta_h = ((denom - n) * pace_s / 3600) if (pace_s and n < denom) else None
    deltas[cell] = {"now":n, "prev":prev, "delta":d, "denom":denom,
                    "pct":100*n/denom if denom else 0, "pace_s":pace_s, "eta_h":eta_h}

# ---- "What changed" since last invocation ----
# Only meaningful when we have a prior cache to diff against; on first run
# every cell trivially looks "newly started", which is noise.
done_now, started_now = [], []
if prev_ts:
    for cell, d in deltas.items():
        if d["now"] >= d["denom"] and 0 < d["prev"] < d["denom"]:
            done_now.append((cell, d["prev"]))
        elif d["prev"] == 0 and d["now"] > 0:
            started_now.append((cell, d["now"]))

# ---- Cell-status classification (shared by both renderers) ----
# Returns one of: done, growing, stalled, pending_rerun, pending_fresh, empty.
def cell_status(cell):
    if cell not in counts:
        if cell in cell_running:
            return "growing"   # RUNNING but trials.jsonl not yet created (e.g. vLLM warmup)
        if cell in cell_pending or cell[0] in model_pending:
            return "pending_fresh"
        return "empty"
    n = counts[cell]; denom = DENOM[cell[2]]
    if n >= denom:                                 return "done"
    grew = prev_ts is not None and deltas.get(cell, {}).get("delta", 0) > 0
    if grew or cell in cell_running:               return "growing"
    if cell in cell_pending or cell[0] in model_pending:
        return "pending_rerun" if n > 0 else "pending_fresh"
    if n > 0:                                      return "stalled"
    return "empty"

def cell_label(cell):
    m, th, c = cell
    short = {"tools_per-task_minimal":"tools_pt","tools_all_minimal":"tools_all","no-tools":"no-tools"}[c]
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
for cell, d in deltas.items():
    if cell not in cell_running: continue
    elapsed_h = parse_elapsed_h(cell_running[cell]["elapsed"])
    if d["eta_h"] is not None and elapsed_h + d["eta_h"] > 0.9 * TIME_LIMIT_H:
        watch.append(f"{cell_label(cell)} ({elapsed_h:.0f}h+{d['eta_h']:.0f}h ETA → over 0.9×{TIME_LIMIT_H}h)")

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

    out.append("### Per-cell progress (denominator 4560)")
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
    if wrong_backend:
        out.append(f"_(skipped {len(wrong_backend)} dirs on non-canonical backend per BACKEND map: {', '.join(wrong_backend[:3])}{'…' if len(wrong_backend)>3 else ''})_")

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
    out.append(H2("Per-cell progress") + DIM + "  (denom 4560)" + RESET)
    short_hdrs = ["on/no-tools", "on/tools_pt", "on/tools_all",
                  "off/no-tools", "off/tools_pt", "off/tools_all"]
    MODEL_W = 14   # "Qwen3.5:0.8B" = 12 + slack
    CELL_W  = 14   # " ✓  100.0%  " ≈ 11–12 chars; pad to 14 for separation
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
    if wrong_backend:
        out.append(f"  {DIM}(skipped {len(wrong_backend)} dirs on non-canonical backend: "
                   f"{', '.join(wrong_backend[:3])}{'…' if len(wrong_backend)>3 else ''}){RESET}")

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
