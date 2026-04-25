#!/usr/bin/env bash
# Postmortem of completed pddl_* SLURM jobs via `sacct`.
#
# Surfaces what `summary.json` doesn't: how the SLURM job itself behaved.
# Wall time, MaxRSS, exit code, OOM-Kill flag, derived exit code from
# children. Closes the loop on PDF p9's "use minimum possible RAM" rule by
# computing memory headroom across recent jobs and recommending a --mem
# value to drop to.
#
# Output: markdown table + one-line headroom recommendation.
#
# Usage:
#   bash postmortem.sh                       # last 7 days, all pddl_* jobs
#   bash postmortem.sh --since 2026-04-22    # since a specific date
#   bash postmortem.sh --jobs 17130166,17130167  # specific job ids
#
# Env overrides:
#   REMOTE_USER (default omereliyahu), REMOTE_HOST (default slurm.bgu.ac.il)

set -eo pipefail

REMOTE_USER="${REMOTE_USER:-omereliy}"
REMOTE_HOST="${REMOTE_HOST:-slurm.bgu.ac.il}"
SINCE=""
JOBS=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --since) shift; SINCE="$1"; shift ;;
        --jobs)  shift; JOBS="$1"; shift ;;
        -h|--help)
            sed -n '1,20p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) echo "Unknown option: $1" >&2; exit 1 ;;
    esac
done

if [ -z "$SINCE" ]; then
    # sacct accepts relative time strings, no eval round-trip needed.
    SINCE_ARG="--starttime=now-7days"
else
    SINCE_ARG="--starttime=$SINCE"
fi

if [ -n "$JOBS" ]; then
    # `--jobs=` overrides the default `--user=` scope: sacct will return
    # those exact job ids regardless of who owns them. Fine for the
    # documented use case (the user passes ids they already saw under
    # their own queue), but worth knowing.
    SCOPE="--jobs=$JOBS"
    NAME_FILTER=""
else
    # Use the long-form `--user=` (single token, no internal whitespace) so
    # ssh doesn't word-split it into "-u" + "omereliy" and trip the next
    # positional arg into being consumed by `-u`.
    SCOPE="--user=$REMOTE_USER"
    # Job names are unique per (model, think), so we can't pre-filter via
    # sacct --name=. Grep client-side for the pddl_ prefix instead.
    NAME_FILTER="pddl_"
fi

# Note `bash -s --`: SINCE_ARG and SCOPE start with `--` (`--starttime=...`,
# `--jobs=...`), which remote bash would otherwise try to parse as its own
# options. The `--` ends bash option parsing so they land in $1/$2/$3.
ssh "${REMOTE_USER}@${REMOTE_HOST}" "bash -s --" "$SINCE_ARG" "$SCOPE" "$NAME_FILTER" <<'REMOTE'
set -eo pipefail
SINCE_ARG="$1"
SCOPE="$2"
NAME_FILTER="$3"

# ReqMem on this cluster is per-node; AllocTRES carries the canonical
# allocation. We pull both so the report shows what was asked vs allocated.
# %N suffix in --format widens the column without truncation.
# Capture the python source via a quoted heredoc into a variable, then pass
# it to `python3 -c "$PY"`. We CANNOT use `python3 - <<'PY' ... PY` here:
# that form makes the heredoc become python's stdin, hijacking the pipe and
# starving sys.stdin of the sacct rows we want to process.
PY=$(cat <<'PY'
import sys, re

def parse_rss(s):
    """sacct MaxRSS like '11329076K', '12.3G', '0' → bytes (int) or None."""
    if not s or s == '0':
        return None
    m = re.match(r'^([\d.]+)([KMGT]?)$', s)
    if not m:
        return None
    val = float(m.group(1))
    mul = {'K': 1024, 'M': 1024**2, 'G': 1024**3, 'T': 1024**4, '': 1}[m.group(2)]
    return int(val * mul)

def fmt_rss(b):
    if b is None: return '-'
    for unit, div in (('TB', 1024**4), ('GB', 1024**3), ('MB', 1024**2), ('KB', 1024)):
        if b >= div:
            return f'{b/div:.1f}{unit}'
    return f'{b}B'

def parse_mem_alloc(tres):
    """AllocTRES like 'cpu=12,mem=48G,node=1,billing=12,gres/gpu=1' → bytes."""
    if not tres: return None
    for part in tres.split(','):
        if part.startswith('mem='):
            return parse_rss(part[4:])
    return None

# sacct emits one line per JobID *and* per JobID.batch / .extern. We want the
# batch step's MaxRSS but the parent step's State / ExitCode / Elapsed. Group
# by parent job id and merge.
jobs = {}
for line in sys.stdin:
    line = line.rstrip('\n')
    if not line: continue
    parts = line.split('|')
    if len(parts) < 10: continue
    jid_raw, jname, state, elapsed, maxrss, reqmem, alloctres, exitcode, dexit, comment = parts[:10]
    is_step = '.' in jid_raw
    parent = jid_raw.split('.')[0]
    rec = jobs.setdefault(parent, {})
    if is_step:
        rss = parse_rss(maxrss)
        if rss is not None and rss > rec.get('maxrss', 0):
            rec['maxrss'] = rss
    else:
        rec.update({
            'jid': parent, 'jname': jname, 'state': state, 'elapsed': elapsed,
            'reqmem': reqmem, 'alloctres': alloctres,
            'exit': exitcode, 'dexit': dexit, 'comment': comment,
        })

# Render
print('| job | name | state | elapsed | MaxRSS | --mem | exit | derived | comment |')
print('|---|---|---|---|---|---|---|---|---|')
mem_used_per_job = []
for parent in sorted(jobs):
    r = jobs[parent]
    # awk lets every step row through unconditionally (no name match), so
    # non-pddl jobs whose .batch step survives the filter end up here without
    # a parent row. Skip those orphans.
    if 'jid' not in r: continue
    rss = r.get('maxrss')
    alloc_mem = parse_mem_alloc(r.get('alloctres', ''))
    mem_str = fmt_rss(alloc_mem) if alloc_mem else r.get('reqmem', '-')
    if rss is not None and alloc_mem is not None:
        mem_used_per_job.append((rss, alloc_mem, r['jname']))
    print(f"| {r['jid']} | {r['jname']} | {r['state']} | {r['elapsed']} | "
          f"{fmt_rss(rss)} | {mem_str} | {r['exit']} | {r['dexit']} | "
          f"{r['comment'] or '-'} |")

# Per-job-name peak — the sweep is heterogeneous (small models like
# Qwen3.5:0.8B use ~2GB, gpt-oss:120b uses 70GB), so a single global
# `--mem` recommendation would either OOM the big model or over-allocate
# every small one. Group by jname and report each group's peak.
if mem_used_per_job:
    by_name = {}
    for rss, alloc, jname in mem_used_per_job:
        cur = by_name.get(jname)
        if cur is None or rss > cur[0]:
            by_name[jname] = (rss, alloc)
    print()
    print('**Per-job-name peak (right-size --mem):**')
    for jname in sorted(by_name):
        peak_rss, alloc = by_name[jname]
        recommended = int(peak_rss * 1.25 / (1024**3))
        slack = (alloc - peak_rss) * 100 / alloc
        print(f'- `{jname}`: peak {fmt_rss(peak_rss)} of {fmt_rss(alloc)} '
              f'({slack:.0f}% slack) → safe `--mem={recommended}G`')
PY
)

sacct $SCOPE \
      $SINCE_ARG \
      --format=JobID,JobName%30,State%15,Elapsed,MaxRSS,ReqMem,AllocTRES%60,ExitCode,DerivedExitcode,Comment%40 \
      --parsable2 \
      --noheader 2>/dev/null \
    | { if [ -n "$NAME_FILTER" ]; then
          # Match the prefix in field 2 (JobName) for parent rows; allow step
          # rows (e.g. "<jid>.batch") through unconditionally so they merge
          # into the parent's MaxRSS in the python pass.
          awk -F'|' -v p="$NAME_FILTER" '$1 ~ /\./ || index($2, p) == 1'
        else
          cat
        fi
      } \
    | python3 -c "$PY"
REMOTE
