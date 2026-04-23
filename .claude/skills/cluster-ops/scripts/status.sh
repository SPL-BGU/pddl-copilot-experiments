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

# Banner matches both layouts:
#   cis:  "CONDITION: <cond>   started ..."         (run_condition.sbatch)
#   rtx:  "THINK: on   CONDITION: <cond>   started ..." (run_condition_rtx.sbatch)
# Dropping the ^ anchor lets the regex match mid-line for the rtx layout.
BANNER = re.compile(r'CONDITION:\s+(\S+)\s+.*started', re.M)
# Both sbatches emit "Conditions:  cond1 cond2 ..." during setup; presence of
# this line is the signal that the job loops multiple conditions in one file
# (cis: single think × N conds, rtx: M thinks × N conds).
CONDITIONS_LINE = re.compile(r'^Conditions:\s+(.+)$', re.M)
# rtx sbatch prints "Think modes: on off"; cis sbatch prints the singular
# "Think mode:  on|off|default" — match either so we count banners correctly.
THINK_MODES_LINE = re.compile(r'^Think mode(?:s)?:\s+(.+)$', re.M)
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

    # Detect multi-cond layout by the presence of a "Conditions:" line.
    # Covers both run_condition.sbatch (cis) and run_condition_rtx.sbatch,
    # regardless of whether the job name ends with _on|_off|_default.
    conds_m = CONDITIONS_LINE.search(text)
    if conds_m:
        total_conds = len(conds_m.group(1).split())
        thinks_m = THINK_MODES_LINE.search(text)
        n_thinks = len(thinks_m.group(1).split()) if thinks_m else 1
        # Denominator = think_modes × conditions (rtx loops outer THINK_MODES;
        # cis has a single think per job so n_thinks=1 and denom==total_conds).
        total_banners = total_conds * n_thinks
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
        phase = f"cond {cur_idx}/{total_banners}: {cur_cond}"
    else:
        # Legacy layout: one condition per file, no "Conditions:" setup line.
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
