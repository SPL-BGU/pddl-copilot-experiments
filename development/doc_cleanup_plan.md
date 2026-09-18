# Documentation cleanup plan (Step 2 of `review_round_handoff.md`), 2026-09-18

**Nothing has been moved or rewritten.** This file is the plan only. Work starts after you
answer here.

**Goal.** A fresh session trusts what it reads first. After this pass, the path and the
first screen of every live doc tell the truth: where the paper is edited, what the venue
is, what work is left, which corpus numbers are checked against, which backend exists.

**How to answer.**
- Part 1 holds the **seven real decisions** (Q1–Q7). Each has a recommendation.
- Part 2 holds one table per area, a row per file, with **one approval slot per table**.
  Write `ok`, or `ok except A4, A9: <what you want instead>`.
- Fast path: if you agree with every recommendation in this file, write `ok all` here
  and skip the rest.

> ANSWER (ok all / see slots below):
>

**How it was surveyed.** Four read-only audits on 2026-09-18 (the `development/` root,
the files beside `main.tex`, the issues and flow docs, the skills and agent memory). I
re-checked the claims that carry weight myself: the freeze-record hashes, the deleted
chain code, the `cp … main.tex` command, the two risky memory entries. Anything still
marked UNVERIFIED gets checked again at execution, before the edit.

---

## Part 1 — Decisions

### Q1. Frozen code cites two docs we want to move

The budget-probe freeze record (`frontier_budget_probe_prereg.md`, "Freeze record
(2026-09-10)") pins nine files by sha256. Several name a doc by full path in a
docstring: `tools/budget_probe_analysis.py:4`, `tools/_run_manifest.py:4`,
`tools/e2e_regrade.py:5,119`, `.claude/skills/analyzer/scripts/e2e_overlay.py:7`,
`tools/frontier_runner.py`, `tools/claude_api_batch.py`. Repairing the path changes the
hash, so the handoff's rule 4 ("repair inbound links in `tools/`") cannot apply to them.
`MOVES.md` already has this case for the nt-ster scripts: "Do not repair them."

- (a) Move the docs, leave the old path inside the frozen files, add a second
  "deliberately keep pre-reorg paths" block to `MOVES.md`. Links in files that are not
  pinned get repaired as usual.
- (b) Keep `frontier_budget_probe_prereg.md` and `tool_call_vs_final_output_grading.md`
  in the root so no path goes stale.

**Recommendation: (a).** It follows the existing precedent and keeps "root = live" true.

> ANSWER (a / b):
>

### Q2. Three stale pointers sit inside Overleaf-synced files

`paper/main.tex:1-2` is a header comment that still says "AAAI-27 anonymous submission
… SCAFFOLD ONLY: sections are empty … See GOALS.md". `paper/main.tex:638` (a comment)
and `paper/figures/make_paper_figures.py:3` cite the Job 2 worknote by path. All three
are comments, so the PDF does not change, but editing them in a docs PR fires the
Overleaf sync.

- (a) Leave them out of this cleanup. Add `MOVES.md` rows now. Fix the three comments
  in the first real paper PR of Step 4 (the overfull-table fix), so one sync covers it.
- (b) Fix them in the rewrites PR and accept one extra, content-free Overleaf sync.

**Recommendation: (a).**

> ANSWER (a / b):
>

### Q3. `CLAUDE.md` line 5 states something false

It says the chain phase's "function bodies [are] preserved in
`pddl_eval/{runner,summary}.py`". They were deleted on 2026-05-25 (`CHANGELOG.md`,
HARNESS-01: `run_chain_experiment`, `summarize_chains`, `print_chain_table`,
`DEFAULT_NUM_CTX_CHAIN`). A grep of `pddl_eval/` and `run_experiment.py` finds no chain
code. The handoff assumed this sentence could stay as written. Every session reads
`CLAUDE.md` first, so this one matters.

**Recommendation:** keep the warning, correct the fact: "the chain phase was archived
2026-05-05 and its code deleted 2026-05-25; bringing it back means restoring it from
git history and re-wiring the dispatch". Same PR also fixes line 15 (venue, see table D).

> ANSWER (ok / other wording):
>

### Q4. Open items that live only in the June review files

Rule 3 of the handoff: before a file is archived, anything still open in it must be
carried into `STATUS.md`. The audit checked every action item in the iter-1 and iter-2
plans against the tex and the logs. Nearly all are closed or superseded, each with a tex
line or a log entry as evidence. These are not, and nothing live tracks them today:

| # | item | evidence | recommendation |
|---|---|---|---|
| 1 | GLMM refit with a standard (non-variational) estimator | `main.tex:564` still quotes the variational output (log-odds +7.5, posterior SD 0.10); only an archived roadmap mentions the refit | **track** under `STATUS.md` N3: local, $0 |
| 2 | Curated code and data release at publication | the tex checklist (`main.tex:2326`) promises it; no live doc tracks it | **track** under N3: the paper commits us to it |
| 3 | Clean cluster BF16-35B precision control (iter-2 DECISION F) | recorded "yes" on 06-20, never run, never dropped | **record as not planned**, list under N4 optional. The within-model reframe that was its fallback is what the tex says |
| 4 | Schema-salience probe (iter-2 ask 6) | approved 06-20, never built (`--schema-variant` does not exist), never dropped | **record as not planned**, list under N4 optional |
| 5 | Writing leftovers: structural-contamination clause, steering-phrasing Future Work sentence, temperature Future Work sentence, classical-vs-numeric cost split, symbol-map appendix | none is in the tex; none was explicitly dropped | **list once** under N3's consistency read as candidates. No prose written unprompted |

Whatever you answer becomes one dated entry in `paper_notes_discussions.md` (appending
is how that log works; no old entry is touched). The same entry records the iter-1
decisions Q1–Q3 of 06-18, which today exist only in `iter1_action_plan.md`.

> ANSWER (ok / per item: track · not planned · drop):
>

### Q5. `NUMBERS.md` needs three wording-only touches

No figure changes. (i) It names the deleted branch five times, always as provenance
("tex: `paper/aaai27` `125cc7a`"). (ii) Line 20 cites the PlanBench handoff as "Binding
constraints on use"; if that handoff is archived (row A13) the pointer must move to
where the constraints really are: Amendment M in `reference/planbench_wt_prereg.md` and
the first-draw rule in the results doc. (iii) The budget-probe row (line 74) names no
source file; the readout should be named.

**Recommendation:** leave every row as it is; add one line at the top saying that
hashes written as "`paper/aaai27` `<hash>`" are on `main` since PR #101; repoint line
20; add the readout path to line 74. I verify (ii) against both targets before editing.

> ANSWER (ok / leave NUMBERS.md completely alone):
>

### Q6. `OPEN_ISSUES.md` says 13 open; 5 are

| real state | issues | proposed |
|---|---|---|
| open | ISS-005, 013, 019, 020 (frozen by corpus identity), 025 | keep; fix stale file anchors (several still point into `run_experiment.py`, the code is in `pddl_eval/`) |
| closed, not struck | ISS-022 (PR #93) | strike |
| closed in substance | ISS-017 (its residual cites lines that do not exist) | strike, one-line reason |
| moot | ISS-003 (`guided` prompt style retired), ISS-008 (0.6B model and `per-task` retired), ISS-010 (`per-task` filter retired) | strike as moot, one-line reason each |
| no work owed | ISS-021 (accepted limitation), ISS-012 (decided: leave as is), ISS-024 (done; `guided_json` fix parked per D4) | stay listed, index label changes to "no work owed" |

Issue bodies stay untouched as history. The April "Planned batches" and "Raw impact
ranking" tail (lines 210–251) gets one line at its head saying it is historical. Line 3
("close an issue by moving it into `CHANGELOG.md`") contradicts the strike-in-place
practice and is corrected. The index tally is updated. Two UNVERIFIED points (ISS-024
`gt` persistence, ISS-012 re-evaluation) are checked before striking anything.

> ANSWER (ok / keep the moot ones open / other):
>

### Q7. Agent memory (outside the repo, no PR)

79 files including the index. Proposed: **keep 43, update 22, merge 9 into 1, delete
4**, and shorten the index (31 of 77 index lines are over 200 characters; the longest is
549). Every `feedback` entry stays. Full table in Part 2, section J.

Two entries can cause a wrong number or a wrong action, so they go first:
`project_sonnet_frontier_notools.md` still presents "simulate 0.0% hard floor" as a
finding (retracted: a grader artifact, see `NUMBERS.md`), and
`reference_vllm_parser_per_model.md` says to `rm ~/vllm.sif`, which
`reference_bgu_vllm_sif_cache.md` forbids.

> ANSWER (ok / fix only the two risky ones / leave memory alone):
>

---

## Part 2 — Tables, one approval slot each

The letters follow the handoff's inventory rows A–J. Row G (`OPEN_ISSUES.md`) is Q6
above, so there is no table G.

### A. `development/` root (20 docs now; 11 after the moves)

| id | file | verdict | reason |
|---|---|---|---|
| A1 | `STATUS.md`, `NUMBERS.md`, `MOVES.md`, `README.md`, `CHANGELOG.md`, `OPEN_ISSUES.md`, `paper_notes_discussions.md` | keep | the entry points and the logs |
| A2 | `review_round_handoff.md`, `advisor_brief.md` | keep | the open review round (PR #103) |
| A3 | `paper-git-overleaf-instructions.md` + the two sync scripts | keep | live guide; `CLAUDE.md` and the workflow file point at it. Title fixed in table D |
| A4 | `journal_decisions_memo.md` | keep for now | §5 and §10 feed the advisor round. Moves to `reference/` once the venue is ratified |
| A5 | `title_abstract_candidates.md` | → `reference/` | N1 is closed; `NUMBERS.md` cites §4 and §5. If the advisors reopen the title or abstract, that work gets a new short root doc. Its one blank slot (line 264) belongs to a draft that §5 replaced |
| A6 | `frontier_budget_probe_prereg.md` | → `reference/` | ratified prereg; holds the freeze record. Body never edited (Q1) |
| A7 | `frontier_budget_probe_readout.md` | → `reference/` | ratified readout, in the tex |
| A8 | `frontier_budget_probe_handoff.md` | → `archive/frontier/` | its own title says CLOSED |
| A9 | `iss024d_parity_prereg.md` | → `reference/` | executed prereg (parity failed 07-17). Its blank slot at line 35 stays blank: a prereg is not edited |
| A10 | `job2_delivered_reframe_worknote.md` | → `reference/` | named a worknote, but `NUMBERS.md` cites §2 (the 13/25 verdict table) and §6 (the recompute script). Archive is "never a number", so it cannot go there |
| A11 | `ntster_h4_final_readout_20260829.md` | → `reference/` | ratified readout. The README says it is live "because its paper integration is still open"; that closed 09-13 |
| A12 | `sonnet_wt_vs_haiku_e2e_memo.md`, `tool_call_vs_final_output_grading.md` | → `reference/` | `NUMBERS.md` provenance; stable grading spec the code cites (Q1) |
| A13 | `planbench/PLANBENCH_WT_FINAL_PHASE_HANDOFF.md` | → `archive/planbench/` | arm closed. The body says "PR #93, open" and "paper edits go on `paper/aaai27` ONLY". Needs Q5 (ii) first |
| A14 | `planbench/planbench_wt_paper_integration_plan.md` | → `archive/planbench/` | executed plan (Job 1 done) |
| A15 | `planbench/planbench_wt_results_20260803.md` | → `reference/` | `NUMBERS.md` provenance for every PlanBench row. After this `development/planbench/` is empty and goes away |
| A16 | `dev_docs_refactor_plan.md` | → `archive/plans-executed/` | ran in full as PR #95 (all 47 `MOVES.md` rows checked). Its six blank slots D1–D6 are dead |
| A17 | `doc_cleanup_plan.md` (this file) | → `archive/plans-executed/` in the last PR | executed plan |

Bonus: moving A9, A11 and A12 into `reference/` makes several bare-name citations
inside `reference/` resolve again without touching those files.

Each move = `git mv` + one `MOVES.md` row + README map + link repair in every file that
is not pinned. The README map also gets `reference/serving_env_20260913.md`, which
`NUMBERS.md` cites and the map never listed.

> ANSWER (table A):
>

### B. `STATUS.md`, edited in place: 385 lines → about 120

Before a block is cut I confirm the fact is in the record named here. If it is not, I
add it there first.

| id | block (lines today) | action | where the fact stays |
|---|---|---|---|
| B1 | header refresh history (3–12) | keep the latest refresh only | git history |
| B2 | one-paragraph answer (23–40) | rewrite: five lines, present tense, no branch names | — |
| B3 | state-by-line table (42–54) | keep, drop the branch names | — |
| B4 | Job 1 (56–77) | one row in a new closed-work table: what · tex location · commit · record | `paper_notes` 08-11, 09-07; `NUMBERS.md` PlanBench rows |
| B5 | Job 2 + budget probe (79–117) | one row | `paper_notes` 09-07 to 09-12; `NUMBERS.md` Job 2 block |
| B6 | Job 3 (119–173) | one row. The "Llama probe is unblocked" fact moves to N4 | `paper_notes` 08-29, 08-30, 09-12, 09-13; `NUMBERS.md` nt-ster block |
| B7 | Job 4 (175–187) | one row | `paper_notes` 08-17, 08-20; `NUMBERS.md` corpus scale |
| B8 | housekeeping table (189–196), with the 20-line serving-environment history cell | one row | `paper_notes` 09-13, 09-14; `reference/serving_env_20260913.md` |
| B9 | operational note, single line of work (198–206) | keep, shortened | — |
| B10 | external gates (208–220) | keep, four lines | `paper_notes` 08-30 |
| B11 | R1–R4, answered (224–264) | a short "decided" list, one line each | `paper_notes` 09-07 (R1), 08-29 (R2); R3 and R4 to be confirmed |
| B12 | N1, with its "Original text of this item" (277–307) | one row in the closed-work table; the original text goes (it says "edit on `paper/aaai27` in the worktree") | `paper_notes` 09-15/18; `NUMBERS.md` abstract block |
| B13 | N2–N5 (309–352) | keep. N2 points at `advisor_brief.md`. N3's line reference corrected to 755–796. N3 gains the Q4 items and a de-anonymising step for the JAIR reformat (today nothing mentions the author block, the links block or `[submission]` mode). N5 updated |
| B14 | R5, R6, answered (356–374) | decided list | `paper_notes` 09-15/18 |
| B15 | R7, R8 (376–385) | keep, slots stay open | — |

> ANSWER (table B):
>

### C. Files beside `main.tex`

None is referenced by `sync_overleaf.sh`, `make_overleaf_zip.sh`, the workflow or
`paper/.gitignore`, so moving them is safe and fires no sync.

| id | file | verdict | reason |
|---|---|---|---|
| C1 | `paper/HANDOFF.md` | → `development/archive/paper-june/` | names the dead branch three times, carries a paste-ready "Continue the AAAI-27 paper on branch…" prompt, lists a done Sonnet run as pending. Lines 117–121 hold the only full font recipe: copied into `paper/README.md` first |
| C2 | `paper/GOALS.md` | → same | **lines 95–102 tell the reader to run `cp authorkit27/AnonymousSubmission2027.tex main.tex`, which would overwrite the manuscript.** Also: AAAI deadlines, "no paper prose written yet", PlanBench out of scope, RQ decks as the data source |
| C3 | `paper/REVIEW_AND_REWRITES.md` | → same | every number was computed from the stale mirror `sweep5-cluster-20260530`; four of its figures conflict with `NUMBERS.md` (−67 pp as delivered, simulate 0%, cost-of-pass 0.3×, balanced accuracy 95–100) |
| C4 | `paper/automated-platforms-review/` (iter1 + iter2), moved as one directory | → `development/archive/paper-june/automated-platforms-review/` | records. Moved as a unit so their relative links survive. Note for `MOVES.md`: the three iter-1 PDFs have been 0-byte files since they were committed, so `iter1_review_synthesis.md` is the only record of those reviews. Gated on Q4 |
| C5 | `paper/README.md` | **stays, rewritten** | about 70% wrong: "scaffold, no prose yet", "start the submission from `AnonymousSubmission2027.tex`" (the C2 hazard again), "Per AAAI rules…", a `TEXINPUTS` recipe the repo no longer needs, no mention of the root `aaai2027.sty/.bst` or `figures/`. New text: journal paper (JAIR target, TMLR fallback), still typeset with `aaai2027.sty` and still anonymous until the N3 reformat, compiles standalone, the full font recipe, do not hand-edit the style files |

Inbound links: `tools/claude_api_batch.py:4` cites C3 and is pinned (Q1), so it stays
stale with a `MOVES.md` row. `main.tex:2` points at C2 (Q2).

> ANSWER (table C):
>

### D. Venue wording

| id | where | now | becomes |
|---|---|---|---|
| D1 | `CLAUDE.md:15` | "The AAAI-27 paper lives in `paper/`…" | "The journal paper (JAIR target, TMLR fallback; still typeset with `aaai2027.sty` until the N3 reformat) lives in `paper/`…" |
| D2 | `paper-git-overleaf-instructions.md:3` | "code and the AAAI-27 paper" | "code and the journal paper" |
| D3 | `paper/README.md` | see C5 | see C5 |

The file names `aaai2027.sty` and `aaai2027.bst` stay.

> ANSWER (table D):
>

### E + F. Ollama and the chain phase

Smaller than the handoff expected. Every one of the 30 "ollama" hits in the live docs
is a history sentence, the real `cis-ollama` hostname, or the live tag name
`ollama_parse_error`. There is no how-to text to delete.

| id | where | action |
|---|---|---|
| E1 | `CLAUDE.md:3`, cluster-ops `SKILL.md:23`, `EXPERIMENTS_FLOW.md:19,569`, `cluster-experimenting/README.md:39` | one wording everywhere: "retired 2026-05-18, code removed 2026-05-23" (today some say 05-18, others 05-23) |
| E2 | `cluster-experimenting/README.md:36` | add one clause: the hostname still exists and now serves vLLM |
| E3 | `EXPERIMENTS_FLOW.md:377`, `:414–417` | Ollama-era leftovers without the word in them: a `:11434` host example, `MAX_LOADED_MODELS=1`, a packed-job recipe. Handled in table H |
| F1 | `CLAUDE.md:5` | see Q3 |
| F2 | `README.md:131` | legacy `chain_*.json` is "still parseable by the analyzer" → "ignored by the analyzer" |
| F3 | `EXPERIMENTS_FLOW.md:590` | "remains archived (§4.3)": there is no §4.3; fix the reference |
| F4 | `OPEN_ISSUES.md:101`, `:116` | present-tense chain text inside two struck, closed issues. Left as history |
| F5 | `OPEN_ISSUES.md:216` | sits in the April tail, covered by Q6 |

> ANSWER (table E + F):
>

### H. Top-level `README.md` and `EXPERIMENTS_FLOW.md`

Every command and default was checked against `run_experiment.py --help` and the code.

| id | file | verdict | what changes |
|---|---|---|---|
| H1 | `README.md` | light fix | two wrong CLI defaults (`--models` is optional, not required; `--num-variants` is 6 over variants 11–16, not 3 over 0–2); ten flags missing from the table; "Domain Structure" says 10 domains and a `p01.plan` file (real: 20 domains, `pNN_v1..v5.plan`, `pNN_b1..b5.plan`, negatives); results path wrong; success described as one metric when there are two; about six pointer lines added (`STATUS.md`, `NUMBERS.md`, canonical corpora, e2e overlay, frontier runner, PlanBench, journal target) |
| H2 | `EXPERIMENTS_FLOW.md` §1, §2.3, §5, §8 | light fix | "4 tools-conditions" (there is one); three plugins listed (two are required); the legacy system prompt quoted as the active one; "5 variants" (6); `MCPPlanner` in the wrong file |
| H3 | `EXPERIMENTS_FLOW.md` §9 | rewrite the field tables | `RESPONSE_SNAPSHOT_LEN=500` (real value 16384; 500 applies only to corpora from before 2026-06-25, which is what causes the censoring); `trials.jsonl` never mentioned; six meta fields and four trial fields missing |
| H4 | `EXPERIMENTS_FLOW.md` §10 | rewrite the cluster block, cut laptop monitoring | describes a four-model packed job with `qwen3.6:27b` and `gemma4:31b`, which `vllm_lookup` rejects, so the command shown fails today. `run_background.sh` no longer exists |
| H5 | `EXPERIMENTS_FLOW.md` §11 | fix two rows | "10 IPC benchmarks" (20); no-tools "gated to think=off" (lifted) |
| H6 | `EXPERIMENTS_FLOW.md` §13 | rewrite, short | still calls the PlanBench tools arm future work ("tracked as ISS-022", "Mystery deferred", "validation pending"). It ran and closed in PR #93. Replace with a pointer to `planbench/README.md` and the moved results doc |
| H7 | `EXPERIMENTS_FLOW.md` | one short new section | the delivered-answer overlay and its censoring rule, the frontier runner, the decoupled budget, the anonymized corpus, the canonical corpus names |

UNVERIFIED and checked at execution: the two marketplace version schemes at lines 315
and 320.

> ANSWER (table H):
>

### I. `.claude/skills/` and `.claude/agents/`

Only one dead-branch reference exists. The larger problem is `cluster-ops`, which
describes a `status.sh` that has not existed in that form since 05-27.

| id | file | verdict | what changes |
|---|---|---|---|
| I1 | `verify-claims/SKILL.md` | light fix | line 17 "Paper edits go on the `paper/aaai27` branch" → short branch off `main` + PR. Add the step `CLAUDE.md` already requires: check `NUMBERS.md` |
| I2 | `cluster-ops/SKILL.md` | rewrite the `status.sh` section (lines 39–84), light fixes elsewhere | 8 columns and "Done X/40" (real: 6 columns, X/30, run tag `sweep6`); wrong cache path; missing `--iss024d` and `--ntster` profiles; a `nt-ctrl` column that does not exist; no-tools time limit 5 h (real 12 h); the GPU default stated backwards in two places; `PDDL_SLOW_MODELS` names retired `gemma4:31b`; `max-num-seqs=4` that the serve command does not pass; several dead line references |
| I3 | `cluster-ops/cleanup.md` | light fix | line 81 runs a Python file with `bash` and passes a flag that does not exist |
| I4 | `analyzer/SKILL.md` | light fix | every example path is gone (`results/full-cluster-run1`, `results/cluster-2026…`, `results/sweep5-live`, two `checkpoints/` paths) → `results/sweep5v2-live`; "7 figures" (5); a sentence about an `IN_FLIGHT` dict that is now empty |
| I5 | `debug-and-simplify/SKILL.md` | light fix | names `validate_pddl_syntax` (tool gone), `--dry-run` (flag gone), `run_*.log`, notebooks (removed), two closed issues |
| I6 | `development-log/SKILL.md` | light fix | two lines: notebooks, a results path pattern that does not exist |
| I7 | `resume-verify/SKILL.md` | light fix | its fallback "newest `*HANDOFF*.md`" would pick a stale archived handoff. Default to `STATUS.md` and handoffs in the `development/` root only |
| I8 | `simplify/SKILL.md` | light fix | a sentence about the built-in skill that is no longer true; "§4.1–§4.3" (no §4.3). The skill keeps its name |
| I9 | `agents/cluster-ops.md` | light fix | its description promises plots and tables, which belong to the analyzer. Add the standing rule: ask Omer before any SSH |
| I10 | `freeze-protocol`, `plan-review-simplify`, `agents/experiment-runner.md` | clean | no change |

> ANSWER (table I):
>

### J. Agent memory (detail for Q7)

| verdict | count | entries |
|---|---|---|
| keep | 43 | 23 feedback, 11 project, 9 reference |
| update (one false statement each) | 22 | `user_profile` (AAAI-27 wording, archived path); 7 feedback (`bgu_timelimit_admin_only`, `check_pending_specs…`, `no_tools_skip_chain`, `sbatch_cwd_dependence`, `submit_with_rtx_time_pin`, `vllm_gpu_share_qwen35`, `worktree_for_main_push`); 9 project (`cost_recalibration`, `e2e_grading_overlay`, `notools_summary_cleanup`, `ntster_h4_run`, `paper_strategy`, `planbench_vllm_migration`, `simulate_grader_artifact`, `sweep4_design`, `sweep6_design`); 5 reference (`bgu_cis_vllm_endpoints`, `bgu_cluster_guide_mar26`, `bgu_it_resource_caps`, `paper_and_repos`, `vllm_parser_per_model`) |
| merge → one entry "closed lines: quote `NUMBERS.md`" | 8 | `abstract_rebuild_20260918`, `frontier_phase_design`, `job2_delivered_reframe`, `journal_decision_batch`, `paper_housekeeping_20260913`, `paper_iter1_review`, `planbench_v2_v3`, `sonnet_frontier_notools`. One bullet per job, carrying only what the repo does not record. Examples: the budget is 64,000 because that is Haiku 4.5's output ceiling; when local is ahead, `sync_overleaf.sh pull` leaves `main.tex` modified with the edit reversed, so `git checkout -- paper/main.tex` and never commit that diff; PlanBench `build_table` uses 500-pool slices while the results doc uses the 600 union |
| merge into `project_ollama_retired` | 1 | `reference_bgu_self_deploy_ollama` (one line: where the admin wrapper lives) |
| delete | 4 | `project_framework_evolution` (the lesson is in `EXPERIMENTS_FLOW.md`; two of its items are now false), `project_ollama_compute_node_probe` (cannot fire any more), `project_overleaf_sync` (no index line; says "branch for paper work = `paper/aaai27`"; all of it is in `CLAUDE.md` and the instructions doc), `reference_bgu_ollama` (calls itself archival) |

Found while auditing, and the reason one entry is rewritten rather than removed: the
summary stub-row bug behind `project_notools_summary_cleanup` is still present in the
canonical corpus (a no-tools `summary_*.json` under `sweep5v2-live` has five
`condition='tools'` rows with n=0 next to the five real ones). It becomes a standing
warning: filter `single_task` on `condition`.

`project_paper_strategy` says Omer "was a co-author on the earlier one", which
contradicts `user_profile` ("NOT on the original arXiv", verified 06-14). I keep the
`user_profile` reading unless you say otherwise.

Index: one short hook per line, the unindexed file resolved, five stale hooks fixed.

> ANSWER (table J, if different from Q7):
>

---

## Part 3 — Found along the way, not part of this pass

Listed so they are not lost. None is touched by the cleanup.

**For a separate `feat/` PR (code):**
- `planbench/engine.py`: a dead `_ollama_chat` path (`import ollama`, `OLLAMA_HOST`).
- Stale names on live things: `FR_OLLAMA_PARSE_ERROR`, `OLLAMA_TOOL_PARSE_SIGNATURES`,
  `_to_ollama_response`. **The string `"ollama_parse_error"` must not change**; the
  corpora carry it.
- Stale docstrings: `pddl_eval/__init__.py:8`, `schemas.py:4,14,73`, `scoring.py:449,493`.
- `run_experiment.py`: the `--models` default is `['qwen3:0.6b','qwen3:4b']`, and
  neither tag is in `vllm_lookup`.
- `submit_with_rtx.sh:15-21` says the default GPU is `rtx_pro_6000`; line 348 defaults
  to `rtx_6000`.
- Analyzer `find_default_root()` looks for result directories that do not exist, so
  every no-argument call fails.
- The summary stub-row bug above (the writer in `run_experiment.py`).

**For `/verify-claims` or the first Step 4 paper PR:**
- `main.tex:568` says "the *simulate* no-tools baseline is 0/3,000" inside the GLMM
  justification. `main.tex:845` qualifies the same zero as *format-exact* success. Line
  568 has no qualifier and `NUMBERS.md` has no row for it. It may be fine; it needs a
  check, not a silent fix.
- `main.tex:1-2` header comment (Q2). `main.tex:564` variational GLMM output (Q4 item 1).

**Log entries that are wrong and stay wrong (append-only):** `CHANGELOG.md:452` and
`paper_notes_discussions.md:797` write "ISS-021" where they mean ISS-024. The 08-29
reorganisation's six decisions were never logged; the commit message of PR #95 is their
only record.

**Left alone:** the two stashes, the untracked `paper/pddl-copilot-paper-overleaf.zip`
(June, gitignored), the empty `.claude/worktrees/` directory.

---

## Delivery

1. **This file** (branch `docs/doc-cleanup-plan`). You answer here; I commit the answers.
2. **PR "moves only":** tables A and C moves, `MOVES.md` rows (including the second
   "deliberately stale" block from Q1), README map, link repair in files that are not
   pinned. No body text changes, so the diff is renames plus path strings.
3. **PR "rewrites":** `STATUS.md` (B), `paper/README.md` (C5), `CLAUDE.md` and venue
   wording (Q3, D), E + F, `OPEN_ISSUES.md` (Q6), `NUMBERS.md` touches (Q5), H, I, the
   `paper_notes` entry (Q4). Memory (J) is done alongside, outside the repo.

Editing `CLAUDE.md` and `.claude/` files happens only with your `ok` on Q3 and table I.

**Done means (both results pasted into the last PR):**

- **Grep residue.** Baseline today, across the 40 live docs:

  | `paper/aaai27` | `worktree` | `single-tool-draft` | `paper/iter2` | `AAAI-27` | `ollama` | chain phase |
  |---|---|---|---|---|---|---|
  | 57 | 21 | 8 | 4 | 26 | 30 | 12 |

  Largest today: `STATUS.md` (22 mentions of the dead branch), `paper/HANDOFF.md` (9 ×
  AAAI-27), `cluster-experimenting/README.md` (11 × ollama, all history), and
  `review_round_handoff.md` itself (its hits are sentences saying the thing is gone).
  Target: every remaining hit is such a sentence, the `cis-ollama` hostname, the
  `ollama_parse_error` tag, or a provenance hash covered by the Q5 header note.
- **Cold-read test.** A fresh subagent with only the repo answers six questions: where
  the paper is edited and how it reaches Overleaf, the target venue, what work is left,
  which corpus numbers are verified against, which inference backend exists, whether
  the chain phase is active. Every answer must match `STATUS.md` and `CLAUDE.md`. A
  wrong answer names the doc that misled it; that doc gets fixed and the test reruns.
