#!/usr/bin/env bash
# Cluster status snapshot. One SSH call. Server-side parsing in Python to
# dodge shell escaping issues around `->` and `[`.
#
# Output: Markdown table with one row per running job.
#
# Env:
#   REMOTE_USER (default omereliy), REMOTE_HOST (default slurm.bgu.ac.il)
#   REMOTE_LOGS (default ~/pddl-copilot-experiments/cluster-experimenting/logs)

set -eo pipefail

REMOTE_USER="${REMOTE_USER:-omereliy}"
REMOTE_HOST="${REMOTE_HOST:-slurm.bgu.ac.il}"
REMOTE_LOGS="${REMOTE_LOGS:-pddl-copilot-experiments/cluster-experimenting/logs}"

# Quoted heredoc → no local expansion. Remote args passed positionally via `bash -s`.
ssh "${REMOTE_USER}@${REMOTE_HOST}" "bash -s" "$REMOTE_USER" "$REMOTE_LOGS" <<'REMOTE'
set -eo pipefail
REMOTE_USER="$1"
LOGS_DIR="$2"

if [ ! -d "$HOME/$LOGS_DIR" ] && [ ! -d "$LOGS_DIR" ]; then
    echo "logs dir missing: $LOGS_DIR"
    exit 1
fi
cd "$HOME/$LOGS_DIR" 2>/dev/null || cd "$LOGS_DIR"

# One squeue call, pipe its output into Python alongside file list.
queue=$(squeue -u "$REMOTE_USER" -h -o '%i|%j|%T|%M' 2>/dev/null | sort || true)
if [ -z "$queue" ]; then
    echo '_no running jobs_'
    exit 0
fi

python3 - "$queue" <<'PY'
import os, re, sys

queue_raw = sys.argv[1]
rows = []

# New layout: job name ends in _on|_off|_default
NEW_NAME = re.compile(r'_(on|off|default)$')
# run_condition.sbatch emits "CONDITION: <cond>  ... started ..." per cond start.
BANNER = re.compile(r'^CONDITION:\s+(\S+)\s+.*started', re.M)
# run_condition.sbatch:98 → "Conditions:  cond1 cond2 ..." (space-separated list).
CONDITIONS_LINE = re.compile(r'^Conditions:\s+(.+)$', re.M)
PROGRESS = re.compile(r'\[ *(\d+)/250 ')
CHAIN = re.compile(r'chain=(\d+) \[(\d+)/\d+\]')
T1200 = re.compile(r'(1199|1200|1201)\.\d+s.*FAIL \(exception\)')
RESULT = re.compile(r' -> ')

for line in queue_raw.splitlines():
    line = line.strip()
    if not line:
        continue
    jid, jname, state, elapsed = line.split('|')

    # locate .out file
    f = None
    for n in os.listdir('.'):
        if n.endswith(f'-{jid}.out'):
            f = n
            break
    if not f:
        rows.append((f"{jid}:{jname}", "_no log_", "-", "-", "-", elapsed))
        continue

    text = open(f, errors='replace').read()

    if NEW_NAME.search(jname):
        # Denominator from the job's own "Conditions:" line (respects CONDITIONS env override).
        conds_m = CONDITIONS_LINE.search(text)
        total_conds = len(conds_m.group(1).split()) if conds_m else 5
        # banners within one file; current cond is the last banner
        banners = list(BANNER.finditer(text))
        cur_idx = len(banners)
        if banners:
            cur_cond = banners[-1].group(1)
            slice_text = text[banners[-1].end():]
        else:
            cur_cond = "init"
            slice_text = text
        st_matches = PROGRESS.findall(slice_text)
        st = st_matches[-1] if st_matches else "0"
        chain_matches = CHAIN.findall(slice_text)
        chain_done = len(chain_matches)
        phase = f"cond {cur_idx}/{total_conds}: {cur_cond}"
    else:
        # legacy: one condition per file
        st_matches = PROGRESS.findall(text)
        st = st_matches[-1] if st_matches else "0"
        chain_matches = CHAIN.findall(text)
        chain_done = len(chain_matches)
        phase = "legacy single-cond"

    total_done = len(RESULT.findall(text))
    t1200_count = len(T1200.findall(text))
    pct = f"{(t1200_count / total_done * 100):.0f}%" if total_done > 0 else "-"

    rows.append((f"{jid}:{jname}", phase, f"{st}/250",
                 f"{chain_done}/400", f"{t1200_count} ({pct})", elapsed))

print('| job | phase | ST | chain | 1200s-timeouts | elapsed |')
print('|---|---|---|---|---|---|')
for r in rows:
    print('| ' + ' | '.join(r) + ' |')
PY
REMOTE
