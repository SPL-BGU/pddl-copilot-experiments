# nt-ster submit window — open decisions (2026-08-16)

Written while setting up the run worktree, before the VPN window. Governing docs, in
priority order where they disagree: `ntster_h4_prereg.md` (RATIFIED 08-11, its §10 text
is the most recent) > `remaining_work_20260811.md` > `journal_decisions_memo.md` §6.

## Where the readiness gate actually stands

`ntster_h4_prereg.md` §10 gates the submit on §8 items 7, 9, 10, 14.

| item | what it is | state |
|---|---|---|
| 7 | reconstruct the decoupled `think=on` wall | **DONE today** — ~132 GPU-h on-mode, ~178 total, inside the ratified 156-196 band |
| 14 | confirm `guided_json` stays parked, in writing | **DONE today** — the 08-16 audit measured it never binds (526/88,781 = 0.59%), so §3.7 M1 keeps its interpretability |
| 9 | write + **freeze** `tools/ntster_f_gate.py` and `tools/ntster_h4.py`, hashes recorded in the prereg | **OPEN** — not started; this is the big one (§7 step 3 lists ~10 required behaviours) |
| 10 | rebuild + stamp `gt_cache.json` from the pinned marketplace commit, add the GT-hash dump/assert | **OPEN** — cache on disk is an unstamped Jul-11 artifact |

Item 8 (smoke) is cluster-gated and is its own problem — see D3.

---

## D1 — What does this VPN window get used for?

Items 9 and 10 are not done, and §10 gates the submit on them. Item 9 is hours of local
work. So either the window is spent on something other than the production submit, or we
knowingly deviate.

There is also a genuine internal contradiction in the prereg worth naming: **§7 step 1
and §10 both say the analysis scripts are frozen *before the submit*; §7 step 3 says
they are written "local while running" with hashes recorded *before the sync ping*.**
Two of the three statements, including the most recent (§10, written at ratification),
say before-submit — so that is the reading I have been treating as binding.

Options:

- **(a) Cluster-state + preflight only this window** (recommended). Confirm what is
  checked out in `~/pddl-copilot-experiments` on the cluster, that it is
  generation-identical to the pin, rebuild the venvs per the standing preflight rule,
  confirm the `vllm.sif` tag, check queue capacity. No submit. I build items 9 and 10
  locally afterwards; you open a second window for the real submit. Costs a window,
  keeps the prereg's own gate intact.
- **(b) Preflight + submit the off-mode arm now**, on the §7-step-3 reading (scripts
  frozen while the job runs, hashes recorded before the sync ping). The off-mode arm is
  the cheap half (~46 GPU-h) and the one that cannot be invalidated by an
  analysis-script choice, since the data is written blind either way. Fastest path to
  data; the cost is that we are taking the looser of two readings of our own prereg,
  which is exactly the kind of thing a preregistration exists to prevent.
- **(c) Preflight + submit both arms now.** Same deviation as (b), doubled, and it
  commits the ~132 GPU-h on-mode half before its `--time` question (D2) has been
  answered with any measurement of the steered arm's per-trial cost.

> ANSWER (a / b / c):
>

## D2 — `--time` on the on-mode submit: 5 days or 7?

The prereg §7 command says `--time 5-00:00:00` (=120 h) for both submits. Today's
reconstruction says the **9B on-mode cell projects to ~105 h**, which becomes **~137 h**
once the prereg's own +30% node-speed spread is applied — i.e. it overruns a 5-day ask.
The partition cap is 7 days and **SLURM bills usage, not the ask**, so a 7-day ask costs
nothing extra; `TimeLimit` increases are admin-denied after the fact, so a wrong ask is
only fixable by resubmitting. A TIMEOUT is resumable from `trials.jsonl` but costs a
queue cycle and another ping from you.

Recommendation: **`--time 7-00:00:00` for the on-mode submit**, keep 5 days for off-mode
(its longest cell is ~25 h). This is a deviation from the literal §7 command, so it wants
your initials rather than my judgement.

> ANSWER (7 days on-mode / keep 5 days as written / other):
>

## D3 — The prereg's "smoke first" step is not executable as written

§7 step 2 says to smoke the `--include-no-tools-steered` path before production. It
cannot be done with `--smoke`: the wrapper rejects `--smoke` combined with `--no-tools`
or `--think-modes` (`submit_with_rtx.sh:311-315`), and `--smoke` forces
`--num-variants 1`, so it would never emit v14-16 at all. `--num-variants N` takes a
**prefix** of the variant list, so it cannot select the steered variants either; the
`--variants` pass-through that could is explicitly **not authorised** (§8 item 12), and
`--shard` is forbidden (it breaks the pairing the primary endpoint depends on). No
`--domains`/`--problems` pass-through exists in the wrapper or sbatch.

What I verified locally instead, at $0:

- The steered override is prompt-level and **branch-independent**: `runner.py:350` builds
  `messages` once, then dispatches to the decoupled path (`:399`) or the plain path
  (`:413`). So `--include-no-tools-steered` composes with `--decoupled-budget` **by
  construction** — the directive is in the prompt before the two paths diverge. That was
  the listed unknown.
- Variants are the **innermost** emission loop (`runner.py:735-744`), so v14-16 rows
  appear from the first problem onward, not after the neutral arm finishes.
- Caveat on the prereg's own acceptance criterion: it asks to confirm "the steered
  directive present in the stored prompt", but **trial rows store no prompt** — the
  schema is `key` + `result{...}` with `response` but no prompt text. The on-disk check
  can only be `prompt_variant ∈ {14,15,16}` with `with_tools=false`.

Options:

- **(a) Live-smoke (recommended):** submit production, and as soon as the first rows land
  in `OUT_DIR/trials.jsonl`, check that v14-16 rows exist with `with_tools=false` and
  that variant counts are tracking 6-way. If wrong, `scancel` and fix — cost is one queue
  cycle, the same cost the prereg already accepts for a TIMEOUT.
- **(b) Add a `--domains/--problems` pass-through** to the wrapper (branch + PR) and run
  a genuine reduced-fixture smoke. Correct by the book, but it is a harness change
  landing immediately before a run whose whole point is apparatus stability, and it
  delays the window.

> ANSWER (a / b):
>

## D4 — Item 10's GT-hash dump contradicts its own "no code change" row

§7 step 3 asks to "dump each run's ground truth into the cell dir and gate the analysis
on those hashes" — that is an edit to `run_experiment.py`. But §8 row 10 marks item 10
**"Code change + PR? No"**. It cannot be both, and a harness edit is not free here: the
sbatch sources from `$HOME` on the cluster at run time, so the edit would have to be
checked out there, against a pin whose whole claim is generation-identity with `6007032`.

Options:

- **(a) Cache-only + SHA argument (recommended):** rebuild and stamp `gt_cache.json` from
  the pinned marketplace commit, and rely on the §7-step-2 requirement to record both
  repo SHAs. Ground truth is deterministic given the fixture tree, and `pddl-solver` /
  `pddl-validator` / `pddl-parser` are **unchanged since the pinned `5e4f9c0`** (verified
  today — the two commits since it are the additive visualizer plugin). So matching SHAs
  plus a matching stamp is a sound equivalence argument without touching the harness.
- **(b) Make the harness edit**, PR it, and check the run branch out in `$HOME` before
  submitting — strongest audit trail, but it perturbs the pinned apparatus.

> ANSWER (a / b):
>

---

## Not blocking, for awareness

- The worktree is `../pddl-copilot-worktrees/ntster-h4` on `run/ntster-h4`, based on
  `origin/main` (`d26949c`). It does **not** carry `d10fd15` (the guided_json audit) —
  that is doc-only and on `audit/guided-json-iss024b`, so it has no effect on the run.
- `results/` is gitignored, so the worktree has no data tree. Analysis and syncs should
  keep pointing at the main checkout's `results/`; I have not created a second one.
- Llama (§8 item 11) stays sequenced strictly after nt-ster, per R3. Its branch must not
  be checked out in `$HOME` until every nt-ster cell is terminal, and must not touch
  `PDDL_VLLM_VERIFIED_MODELS` while nt-ster is live.
- Expect gemma's VRAM guard at zero margin (85.9% peak against a `> 85` guard); on
  `rc=3`, resubmit gemma alone with `GPU_MEM_UTIL=0.82`.
