# Cleanup recipes — cluster-ops

Quarantine-then-prune is the recovery pattern when the corpus drifts from the
intended configuration. Nothing gets `rm`'d from `results/` directly:
whole-dir moves go to `checkpoints/cluster-<UTC-date>-<reason>/`, and
per-row cleanups write a `.bak-precleanup<N>-<UTC-timestamp>` sibling before
overwriting `trials.jsonl`.

> Pre-2026-05-23 dual-backend contamination scenarios (Ollama vs vLLM) are
> no longer reachable; see git history for the worked 2026-05-18 example.

## Cancel-induced error rows

`scancel` (or manual SIGTERM) interrupts a running cell mid-trial. The
in-flight trial gets persisted with a `failure_reason` reflecting the
cancellation, not model capability. These rows must come out before
re-running so the resume-key set doesn't skip the to-be-rerun trials.

### Detect

```bash
ssh omereliy@slurm.bgu.ac.il '
  for d in ~/pddl-copilot-experiments/results/slurm_*_<model>_*; do
    [ -f "$d/trials.jsonl" ] || continue
    echo "== $(basename $d)"
    jq -r ".failure_reason // \"-\"" "$d/trials.jsonl" | sort | uniq -c
  done'
```

Cancel-induced rows usually appear as a burst of identical `failure_reason`
at the **tail** of the file. Typical codes by cancel timing:

| Where the cancel hit | Typical `failure_reason` |
|---|---|
| Mid tool call | `FR_TOOL_ERROR` / `FR_TOOL_LOOP_EXCEEDED` |
| Mid generation | `FR_TIMEOUT` / `FR_TRUNCATION` (false positive) |
| Before first token | empty / `FR_OTHER` |

`FR_TOOL_ERROR` is overloaded (`OPEN_ISSUES.md` ISS-005) — confirm the row
came from a cancel, not a real model error, by reading the matching
`single_task_*.json` or the `.out` tail.

### Prune

Always back up first. Naming convention:
`trials.jsonl.bak-precleanup<N>-<UTC-timestamp>`, with `<N>` the next free
integer per file:

```bash
ssh omereliy@slurm.bgu.ac.il '
  TS=$(date -u +%Y%m%dT%H%M%S)
  for f in ~/pddl-copilot-experiments/results/slurm_*_<model>_*/trials.jsonl; do
    N=1; while ls "${f}.bak-precleanup${N}-"* >/dev/null 2>&1; do N=$((N+1)); done
    cp -a "$f" "${f}.bak-precleanup${N}-${TS}"
    # Strip by jid AND failure_reason — never by failure_reason alone
    jq -c "select(.meta.jid != \"<cancelled-jid>\" or (.failure_reason // \"\") | startswith(\"FR_TOOL\") | not)" \
      "$f" > "${f}.tmp" && mv "${f}.tmp" "$f"
  done'
```

Two safe `jq` predicates:

- **By jid**: every cancel-affected row carries the SLURM jid that wrote
  it (in `meta.jid` or the equivalent field — check schema). Drop only
  rows whose jid matches the cancelled array AND whose `failure_reason`
  is in the cancel-set.
- **By trailing run**: a single uninterrupted suffix of identical-reason
  rows at end-of-file is almost always cancel artefact. Confirm with
  `tail -1 trials.jsonl | jq '.meta.host, .meta.timestamp'` before stripping.

**Never strip by `failure_reason` alone** — a real model error and a cancel
row share the same code. The jid or a timestamp window must be in the filter.

### Re-aggregate

After pruning, regenerate downstream artefacts so summaries don't keep stale
row counts:

```bash
# from the analyzer skill — see .claude/skills/analyzer/SKILL.md
bash .claude/skills/analyzer/scripts/aggregate.py --rebuild
```

## Quarantine directory convention

`checkpoints/cluster-<UTC-date>-<short-reason>/`. Each directory carries one
`README.md`: cancelled jid, wrong sbatch (if applicable), expected canonical
backend, root-cause one-liner, UTC date.

## Not in scope

- **No auto-detect of cancel boundary.** The `jq` predicate is hand-crafted
  from the cancel window; the script can't infer which rows were live-at-cancel
  without a jid or timestamp cutoff.
- **No history rewrite / no rm.** Quarantined dirs stay under `checkpoints/`
  (cheap NFS); reclaim space only when the user surfaces it explicitly.
