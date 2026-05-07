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
# Cache: ~/.cache/cluster-ops-status.json is local-only state. Safe to
# `rm` to reset (next run will be a "first run" with no Δ table).
#
# Env: REMOTE_USER, REMOTE_HOST, REPO_REMOTE, STATE_FILE.

set -eo pipefail

REMOTE_USER="${REMOTE_USER:-omereliy}"
REMOTE_HOST="${REMOTE_HOST:-slurm.bgu.ac.il}"
REPO_REMOTE="${REPO_REMOTE:-pddl-copilot-experiments}"
STATE_FILE="${STATE_FILE:-$HOME/.cache/cluster-ops-status.json}"

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
squeue -u "$USER" -r -h -o '%i|%j|%T|%M|%R' 2>/dev/null | sort || true
echo "=== counts ==="
shopt -s nullglob
for d in "$HOME/$REPO/results/"slurm_*/; do
    n=$(wc -l < "$d/trials.jsonl" 2>/dev/null || echo 0)
    printf '%s\t%s\n' "$n" "$(basename "$d")"
done
echo "=== end ==="
REMOTE
)

python3 - "$remote_payload" "$STATE_FILE" <<'PY'
import json, os, re, sys, time

payload, state_file = sys.argv[1], sys.argv[2]

# ---- Roster + dimensions (matches submit_with_rtx.sh --all roster) ----
ROSTER = ["Qwen3_5_0_8B", "gemma4_31b", "qwen3_6_27b", "qwen3_6_35b"]
DISPLAY = {"Qwen3_5_0_8B":"Qwen3.5:0.8B", "gemma4_31b":"gemma4:31b",
           "qwen3_6_27b":"qwen3.6:27b", "qwen3_6_35b":"qwen3.6:35b"}
# Matrix-gate (no-tools/think=on excluded): 5 cells per model.
CELLS = [("on","tools_per-task_minimal"),("on","tools_all_minimal"),
         ("off","no-tools"),("off","tools_per-task_minimal"),("off","tools_all_minimal")]
COL_HEADERS = ["on / tools_pt","on / tools_all","off / no-tools","off / tools_pt","off / tools_all"]
DENOM = {"no-tools":4260, "tools_per-task_minimal":4560, "tools_all_minimal":4560}
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

# ---- Counts: dirname → (model, think, cond) ----
counts, unknown = {}, []
for line in count_raw:
    n_str, _, dirname = line.partition("\t")
    if not dirname.startswith("slurm_"): continue
    try: n = int(n_str)
    except ValueError: continue
    rem = dirname[len("slurm_"):]
    matched = None
    for m in ROSTER:
        if rem.startswith(m + "_"):
            tail = rem[len(m)+1:]
            for th in ("on","off","default"):
                if tail.startswith(th + "_"):
                    cond = tail[len(th)+1:]
                    if cond in DENOM:
                        matched = (m, th, cond)
                    break
            break
    if matched: counts[matched] = n
    else:       unknown.append(dirname)

# ---- Queue ----
queue = []
for line in queue_raw:
    parts = line.split("|", 4)
    if len(parts) != 5: continue
    queue.append(dict(zip(("jid","jname","state","elapsed","reason"), parts)))

def jname_to_cell(jname):
    """Per-cell array task name → (model,think,cond), e.g. pddl_gemma4_31b_on_tools-pt."""
    if not jname.startswith("pddl_"): return None
    rem = jname[len("pddl_"):]
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
    (e.g. 'pddl_rtx_pack2_qwen3_6_27b' covers all 5 cells of qwen3.6:27b)."""
    for m in ROSTER:
        if m in jname: return m
    return None

cell_running, cell_pending, model_pending = {}, {}, set()
for q in queue:
    cell = jname_to_cell(q["jname"])
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

# ---- Render ----
def cell_text(cell):
    if cell not in counts:
        # cell with no dir: pending if its model has a pending parent-name task
        return "0/—" + (" PD" if cell[0] in {p for p,_ in CELLS} and cell in cell_pending else
                       (" PD" if cell[0]+"_meta" in [] else " _-_"))
    n = counts[cell]; denom = DENOM[cell[2]]
    pct = 100*n/denom if denom else 0
    # Only treat positive delta as "growing" when we have prior state to diff
    # against — otherwise on first run every non-empty cell looks like ▶.
    grew = prev_ts is not None and deltas.get(cell, {}).get("delta", 0) > 0
    txt = f"{n}/{denom} (**{pct:.1f}%**)"
    if   n >= denom:                                icon = "✓"
    elif grew or cell in cell_running:              icon = "▶"
    elif cell in cell_pending:                      icon = "PD↻" if n > 0 else "PD"
    elif cell[0] in model_pending:                  icon = "PD↻" if n > 0 else "PD"
    elif n > 0:                                     icon = "⏸"
    else:                                           icon = "_-_"
    return f"{txt} {icon}"

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

out = []

# Header
if window_str is not None:
    out.append(f"## Status — ~{window_str} since last check\n")
else:
    out.append("## Status — first run (no prior state)\n")

# What changed
if done_now or started_now:
    out.append("### What changed")
    for cell, prev in done_now:
        out.append(f"- ✓ **{cell_label(cell)}** flipped to 100% (was {prev}/{DENOM[cell[2]]})")
    for cell, n in started_now:
        out.append(f"- ▶🆕 **{cell_label(cell)}** started ({n}/{DENOM[cell[2]]} trials)")
    out.append("")

# Matrix
out.append("### Per-cell progress (denominators 4260 / 4560)")
out.append("| Model | " + " | ".join(COL_HEADERS) + " |")
out.append("|" + "|".join(["---"] * (1 + len(COL_HEADERS))) + "|")
for m in ROSTER:
    row = [f"**{DISPLAY[m]}**"]
    for th, c in CELLS:
        row.append(cell_text((m, th, c)))
    out.append("| " + " | ".join(row) + " |")
out.append("")

# Δ — first run has no real delta (every cell would look new), so skip the table.
hdr = f" (window: ~{window_str})" if window_str else " (first run — no delta)"
out.append(f"### Δ since last status{hdr}")
growing = sorted(((c,d) for c,d in deltas.items() if d["delta"] > 0),
                 key=lambda x: x[1]["pct"], reverse=True) if prev_ts else []
if growing:
    out.append("| Cell | Prev → Now | Δ | pace | ETA |")
    out.append("|---|---|---|---|---|")
    for cell, d in growing:
        prev_now = f"{d['prev']} → **{d['now']}**" + (" ✓" if d['now'] >= d['denom'] else "")
        pace = f"~{d['pace_s']:.0f} s/trial" if d["pace_s"] else "—"
        eta  = "**DONE**" if d['now'] >= d['denom'] else (f"~{d['eta_h']:.1f}h" if d['eta_h'] is not None else "—")
        out.append(f"| {cell_label(cell)} | {prev_now} | +{d['delta']} | {pace} | {eta} |")
else:
    out.append("_no cells advanced this window_")
out.append("")

# Roll-up
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
out.append("### Roll-up")
out.append(f"- **Done**: {done_cnt} / {total_expected} cells ({100*done_cnt//total_expected if total_expected else 0}%)")
out.append(f"- **Trial coverage**: {total_now/1000:.1f}K / {total_denom/1000:.0f}K ≈ **{coverage:.0f}%**")
out.append(f"- **Running**: {len(cell_running)} cells" + (f" (jobs {', '.join(run_jids)})" if run_jids else ""))
out.append(f"- **Watch list**: {'; '.join(watch) if watch else 'none'}")

# Queue (compact)
running_jobs = [q for q in queue if q["state"] == "RUNNING"]
pending_jobs = [q for q in queue if q["state"] == "PENDING"]
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

print("\n".join(out))

# Save state for next invocation
new_state = {"timestamp": now_ts,
             "counts": {f"{m}|{t}|{c}": n for (m,t,c), n in counts.items()}}
with open(state_file, "w") as f:
    json.dump(new_state, f)
PY
