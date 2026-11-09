# D5b ground truth: IPC 2023 size ladder, Fast Downward, VAL

Plan row D5b (`development/weakness_action_plan.md`), handoff 2026-11-09 item 9.
No model runs. This folder builds the planner ground truth that must exist
before any model sees these problems: fresh problems from the IPC 2023
learning-track generators, a syntax check of every domain and problem, Fast
Downward at 120 s and 1800 s with the pddl-solver plugin's three strategies,
and a VAL check of every plan found.

## What is committed and what is not

The source repo (`github.com/ipc2023-learning/benchmarks`) has no licence file,
so its files are not committed here (provisional on Omer's answer to handoff §6
decision 4). Committed:

- `ladder.py`: the pinned commit (`19d6a8ad4b354328154a2cc1f1a95f7c09fa9db6`),
  the tier parameters, the seeds and the generator command builder.
- `manifest.json`: the spec, the sha256 of the four domain files and of the
  120 generated problems, with each problem's parameters, seed and command.
- the scripts and `requirements.txt` (the scratch venv).

Not committed (gitignored `external/`): the clone, the generated PDDL, the
plans, and the run records `external/d5b-work/runs/fd_{120,1800}s.jsonl`.

## The ladder

Four domains shared with the IPC 2023 track: blocksworld, miconic, rovers,
satellite, using IPC's own domain files (their blocksworld uses `pickup`,
`putdown`, `arm-empty`, `on-table`, unlike ours). Three tiers per domain copy
IPC's testing tiers easy, medium and hard: the same start and end parameters
and the same interpolation formula as each `generate_all.py`, with 10
instances per tier (IPC has 30) and fresh seeds 5001-5010, 5101-5110,
5201-5210 (IPC used 1007-1036 for testing, 42 upwards for training). That is
120 problems. `pipeline repro-ipc` rebuilds IPC's own 360 testing problems with
the same command builder and checks them byte for byte against the clone,
which shows the builder calls the generators the way IPC did.

## Planner settings

Copied from `../pddl-copilot/plugins/pddl-solver/server/solver_server.py`
(read only): unified-planning `PDDLReader`, `OneshotPlanner(name="fast-downward",
params={"fast_downward_search_config": ...})`, `solve(timeout=T)`, the three
`FD_STRATEGIES` (`lazy_greedy_cea`, the plugin default; `lazy_greedy_ff`;
`astar_lmcut`). Versions as in the laptop plugin venv: unified_planning 1.3.0,
up_fast_downward 0.5.2. VAL is pddl-pyvalidator 0.1.6.

Differences from the plugin, all needed to run this as a batch:

- A memory cap of 8 GiB per run (the limit Corrêa et al. used; the plugin has
  none). Over it the run is recorded `memout_cap`.
- Runs in parallel (default: cores minus 2). The time limit is wall clock, as
  in the plugin, so a run close to the limit can land on either side of it on
  a loaded machine; `shares` prints how many solved runs took over half the
  limit.
- The 1800 s pass runs only the pairs unsolved at 120 s. Fast Downward's
  searches here are deterministic, so a pair solved within 120 s is solved
  within 1800 s with the same plan.

## Regenerate

From the repo root:

```bash
git clone https://github.com/ipc2023-learning/benchmarks external/ipc2023-learning
git -C external/ipc2023-learning checkout 19d6a8ad4b354328154a2cc1f1a95f7c09fa9db6
/opt/homebrew/bin/python3.14 -m venv external/d5b-venv
external/d5b-venv/bin/pip install -r tools/d5b/requirements.txt
PY=external/d5b-venv/bin/python
$PY -m tools.d5b.pipeline repro-ipc      # 360 of 360 IPC testing problems rebuilt byte for byte
$PY -m tools.d5b.pipeline generate       # 120 problems -> external/d5b-work/problems
$PY -m tools.d5b.manifest --check        # hashes match manifest.json
$PY -m tools.d5b.pipeline validate       # every domain and problem, pddl-pyvalidator
$PY -m tools.d5b.pipeline solve --time-limit 120
$PY -m tools.d5b.pipeline val --time-limit 120     # only if some VAL check was cut off
$PY -m tools.d5b.pipeline solve --time-limit 1800  # resumable; --max-hours N stops starting jobs
$PY -m tools.d5b.pipeline val --time-limit 1800
python -m tools.d5b.shares               # the solved shares (repo venv is fine)
```

Tests: `python3 tests/test_d5b.py` (standard library only).
