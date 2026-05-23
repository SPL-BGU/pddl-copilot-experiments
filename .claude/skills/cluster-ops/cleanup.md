# Cleanup recipes — cluster-ops

Two cleanup scenarios surface when the corpus drifts from the intended
configuration. Both follow a **quarantine-then-prune** pattern — nothing
gets `rm`'d from `results/` directly; whole-dir moves go to
`checkpoints/cluster-<UTC-date>-<reason>/`, and per-row cleanups write a
`.bak-precleanup<N>-<UTC-timestamp>` sibling before overwriting
`trials.jsonl`.

## Scenario A — Misconfigured deployment

**Historical (pre 2026-05-23).** When two backends coexisted (Ollama and
vLLM), a job could run on the wrong sbatch and emit rows to a
non-canonical path. The recipe and worked example below are retained
because the **quarantine-then-prune** pattern still applies to any
analogous contamination — most importantly, a model running with the
wrong `TOOL_CALL_PARSER` (e.g. `hermes` instead of `qwen3_xml`), which
silently produces 0% tool-selection on the affected cells.

Original wording (pre-vLLM-unification): A job ran on the wrong backend
(e.g. Ollama sbatch dispatched a vLLM-only model). Every row in the
affected `trials.jsonl` files is corpus-identity contamination; whole
directories come out.

### Detect

1. `status.sh`'s footer prints `(skipped N dirs on non-canonical backend
   per BACKEND map: …)`. Read this line **before** chasing "percentages
   not changing" — the skipped paths are dirs whose prefix doesn't match
   `BACKEND[model]`.
2. Mtime divergence between sibling prefixes: `slurm_<model>_*` freshly
   modified while `slurm_vllm_<model>_*` is stale (or vice-versa) means
   the active job is writing to the non-canonical path.

### Diagnose

```bash
ssh omereliy@slurm.bgu.ac.il 'scontrol show job <jid> | grep -E "Command|JobName"'
grep -A2 "^BACKEND = {" .claude/skills/cluster-ops/scripts/status.sh
```

- `Command=run_condition_rtx.sbatch` → Ollama, writes `slurm_<model>_*`
- `Command=run_condition_vllm_rtx.sbatch` → vLLM, writes `slurm_vllm_<model>_*`

If `BACKEND[model]` and the sbatch path disagree, the submission is wrong.

### Quarantine + resubmit

```bash
# 1. Cancel — let it drain COMPLETING → gone before touching files
ssh omereliy@slurm.bgu.ac.il 'scancel <jid>'

# 2. Quarantine affected dirs (move, never rm)
ssh omereliy@slurm.bgu.ac.il '
  CK=~/pddl-copilot-experiments/checkpoints/cluster-$(date -u +%Y%m%d)-<reason>
  mkdir -p "$CK"
  for d in ~/pddl-copilot-experiments/results/slurm_<model>_*; do
    [ -d "$d" ] || continue
    echo "$(wc -l < "$d/trials.jsonl") $(basename "$d")"
    mv "$d" "$CK/"
  done
  cat > "$CK/README.md" <<EOF
# <reason>
Cancelled jid <jid> on $(date -u +%F). Wrong sbatch <command> used for
<model>, whose canonical backend per BACKEND map is <expected>.
Root cause: <one line>.
EOF'

# 3. Verify removal
ssh omereliy@slurm.bgu.ac.il 'ls -d ~/pddl-copilot-experiments/results/slurm_<model>_* 2>&1'

# 4. Resubmit (single vLLM backend post 2026-05-23)
ssh omereliy@slurm.bgu.ac.il '
  cd ~/pddl-copilot-experiments \
  && bash cluster-experimenting/submit_with_rtx.sh \
        --gpu-type <gpu> <models>'
```

### Worked example — 2026-05-18 Qwen3.5:4B/9B Ollama contamination

Job `17630135` (`pddl_rtx_pack2_Qwen3_5_4B`) submitted via
`run_condition_rtx.sbatch` (Ollama) for vLLM-only models Qwen3.5:4B and
Qwen3.5:9B. Wrote to 8 `slurm_Qwen3_5_{4B,9B}_*` dirs (777 trials total)
over ~2h before `status.sh`'s "skipped N dirs on non-canonical backend"
footer caught it. Root cause: `submit_with_rtx.sh:122` `BACKEND="ollama"`
default fires when `--backend vllm` is omitted, regardless of
`PDDL_VLLM_VERIFIED_MODELS` membership. Quarantined to
`checkpoints/cluster-20260518-ollama-tainted-4b9b/`; resubmitted as job
`17632331` with `--backend vllm --gpu-type rtx_6000`.

## Scenario B — Cancel-induced error rows

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

Cancel-induced rows usually appear as a burst of identical
`failure_reason` at the **tail** of the file. The exact code depends on
where the cancel hit:

| Where the cancel hit | Typical `failure_reason` |
|---|---|
| Mid tool call | `FR_TOOL_ERROR` / `FR_TOOL_LOOP_EXCEEDED` |
| Mid generation | `FR_TIMEOUT` / `FR_TRUNCATION` (false positive) |
| Before first token | empty / `FR_OTHER` |

`FR_TOOL_ERROR` is overloaded (`OPEN_ISSUES.md` ISS-005) — confirm the
row came from a cancel, not a real model error, by reading the matching
`single_task_*.json` or the `.out` tail.

### Prune

Always back up first. The naming convention is
`trials.jsonl.bak-precleanup<N>-<UTC-timestamp>`, where `<N>` is the next
free integer per file:

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

The `jq` predicate is the cleanup's core. Two safe patterns:

- **By jid**: every cancel-affected row carries the SLURM jid that wrote
  it (in `meta.jid` or the equivalent field — check schema). Drop only
  rows whose jid matches the cancelled array AND whose `failure_reason`
  is in the cancel-set.
- **By trailing run**: a single uninterrupted suffix of identical-reason
  rows at end-of-file is almost always cancel artefact. Confirm with
  `tail -1 trials.jsonl | jq '.meta.host, .meta.timestamp'` before
  stripping.

**Never strip by `failure_reason` alone** — a real model error and a
cancel row share the same code. The jid or a timestamp window must be in
the filter.

### Re-aggregate

After pruning, regenerate downstream artefacts so summaries don't keep
stale row counts:

```bash
# from the analyzer skill — see .claude/skills/analyzer/SKILL.md
bash .claude/skills/analyzer/scripts/aggregate.py --rebuild
```

## Quarantine directory convention

`checkpoints/cluster-<UTC-date>-<short-reason>/`:

- `cluster-20260514-pre-roster-swap/` — pre-27b→4B/9B-swap snapshot.
- `cluster-20260517-ablation/` — ablation-axes plot restyle outputs.
- `cluster-20260518-ollama-tainted-4b9b/` — worked example above.

Each directory carries one `README.md`: cancelled jid, wrong sbatch (if
applicable), expected canonical backend, root-cause one-liner, UTC date.

## What this recipe does NOT do

- **No row-level inspection for Scenario A.** Whole dirs are treated as
  contaminated based on path prefix; cancel-induced rows inside a
  canonical-prefix dir are Scenario B's problem.
- **No auto-detect of cancel boundary.** The `jq` predicate is
  hand-crafted from the cancel window — the script can't infer which
  rows were live-at-cancel without a jid or timestamp cutoff.
- **No history rewrite / no rm.** Quarantined dirs stay under
  `checkpoints/` (cheap NFS); reclaim space only when the user surfaces
  it explicitly.
