#!/usr/bin/env bash
# Cluster status snapshot. One SSH call. Server-side parsing in Python to
# dodge shell escaping issues around `->` and `[`.
#
# Output: Two markdown tables — Pending (with REASON column) and Running
# (with progress columns). Pending is rendered first so wave-blocking
# REASON values like DependencyNeverSatisfied / Resources / Priority surface
# without a separate `squeue --me -t PD` round-trip.
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
# %R is the REASON column (populated for PENDING jobs).
queue=$(squeue -u "$REMOTE_USER" -h -o '%i|%j|%T|%M|%R' 2>/dev/null | sort || true)
if [ -z "$queue" ]; then
    echo '_no jobs_'
    exit 0
fi

python3 - "$queue" <<'PY'
import os, re, sys

queue_raw = sys.argv[1]
running = []
pending = []

# Banner matches both layouts:
#   current: "THINK: on   CONDITION: <cond>   started ..." (run_condition_rtx.sbatch)
#   legacy:  "CONDITION: <cond>   started ..."             (retired cis sbatch; still
#                                                           seen in archived logs)
# Dropping the ^ anchor lets the regex match mid-line for the current layout.
BANNER = re.compile(r'CONDITION:\s+(\S+)\s+.*started', re.M)
# Both sbatches emit "Conditions:  cond1 cond2 ..." during setup; presence of
# this line is the signal that the job loops multiple conditions in one file
# (current: M thinks × N conds; legacy: single think × N conds).
CONDITIONS_LINE = re.compile(r'^Conditions:\s+(.+)$', re.M)
# Current rtx sbatch prints "Think modes: on off"; legacy cis sbatch printed
# the singular "Think mode:  on|off|default" — match either so we count
# banners correctly across archived and current logs.
THINK_MODES_LINE = re.compile(r'^Think mode(?:s)?:\s+(.+)$', re.M)
# Capture both numerator AND denominator. Smoke totals are ~5–15 per pass,
# not 250; production sweeps with custom --chain-samples or task-subset
# also break a hardcoded denominator.
PROGRESS = re.compile(r'\[ *(\d+)/(\d+) ')
CHAIN = re.compile(r'chain=(\d+) \[(\d+)/\d+\]')
# Smoke fast-path emits "Smoke pass: think=X, conditions=Y" headers from
# run_experiment.async_main. There are exactly 2 passes (think=on/off) per
# `python run_experiment.py --smoke` invocation.
SMOKE_PASS = re.compile(r'^\s*Smoke pass:\s+think=(\S+),\s+conditions=(\S+)', re.M)

for line in queue_raw.splitlines():
    line = line.strip()
    if not line:
        continue
    jid, jname, state, elapsed, reason = line.split('|', 4)

    if state == 'PENDING':
        pending.append((jid, jname, reason or '-', elapsed))
        continue

    # locate .out file (only RUNNING jobs have one)
    f = None
    for n in os.listdir('.'):
        if n.endswith(f'-{jid}.out'):
            f = n
            break
    if not f:
        running.append((f"{jid}:{jname}", "_no log_", "-", "-", elapsed))
        continue

    text = open(f, errors='replace').read()

    # Smoke jobs (jname ends with _smoke or _smoke-shuffle): the fast-path in
    # run_condition_rtx.sbatch skips the inner THINK × CONDITIONS loop, so
    # the BANNER regex matches 0 times and total_banners (computed from the
    # setup-line "Conditions:" + "Think modes:") describes the planned matrix
    # the smoke job is NOT running. Branch early and report what smoke
    # actually emits: per-pass headers + dynamic-denominator progress.
    if jname.endswith('_smoke') or jname.endswith('_smoke-shuffle'):
        passes = list(SMOKE_PASS.finditer(text))
        if passes:
            last = passes[-1]
            phase = f"smoke pass {len(passes)}/2 (think={last.group(1)})"
            slice_text = text[last.end():]
        else:
            phase = "smoke setup"
            slice_text = text
        st_matches = PROGRESS.findall(slice_text)
        if st_matches:
            n, m = st_matches[-1]
            st_label = f"{n}/{m}"
        else:
            st_label = "0/?"
        running.append((f"{jid}:{jname}", phase, st_label, "n/a", elapsed))
        continue

    # Detect multi-cond layout by the presence of a "Conditions:" line.
    # Covers both run_condition_rtx.sbatch (current) and the retired cis
    # sbatch (still seen in archived logs), regardless of whether the job
    # name ends with _on|_off|_default.
    conds_m = CONDITIONS_LINE.search(text)
    if conds_m:
        total_conds = len(conds_m.group(1).split())
        thinks_m = THINK_MODES_LINE.search(text)
        n_thinks = len(thinks_m.group(1).split()) if thinks_m else 1
        # Denominator = think_modes × conditions (current rtx loops outer
        # THINK_MODES; legacy cis had a single think per job so n_thinks=1
        # and denom==total_conds).
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
        if st_matches:
            n, m = st_matches[-1]
            st_label = f"{n}/{m}"
        else:
            st_label = "0/?"
        chain_matches = CHAIN.findall(slice_text)
        chain_done = len(chain_matches)
        phase = f"cond {cur_idx}/{total_banners}: {cur_cond}"
    else:
        # Legacy layout: one condition per file, no "Conditions:" setup line.
        st_matches = PROGRESS.findall(text)
        if st_matches:
            n, m = st_matches[-1]
            st_label = f"{n}/{m}"
        else:
            st_label = "0/?"
        chain_matches = CHAIN.findall(text)
        chain_done = len(chain_matches)
        phase = "legacy single-cond"

    running.append((f"{jid}:{jname}", phase, st_label,
                    f"{chain_done}", elapsed))

if pending:
    print('### Pending')
    print('| job | name | reason | elapsed |')
    print('|---|---|---|---|')
    for jid, jname, reason, elapsed in pending:
        print(f'| {jid} | {jname} | {reason} | {elapsed} |')
    print()

if running:
    print('### Running')
    print('| job | phase | ST | chain | elapsed |')
    print('|---|---|---|---|---|')
    for r in running:
        print('| ' + ' | '.join(r) + ' |')
PY
REMOTE
