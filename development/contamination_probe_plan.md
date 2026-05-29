# Contamination Probe — Anonymised-Corpus Pilot (`domains-anon/`)

**Status:** plan, not implemented.
**Author / date:** drafted 2026-05-26.
**Scope:** 1 model (Qwen 35B), 6 sweep-5 arms, full domain set with lexical renames.
**Owner-decision required before kickoff:** §11 open questions.

---

## 1. Goal & Hypothesis

**Question.** Does Qwen 35B's sweep-5 performance change when domain / problem / plan
*surface symbols* (type names, predicate names, action names, object names) are
swapped for thematically-different but structurally-isomorphic names, while
keeping arity, signatures, preconditions, and effects byte-equivalent?

**Hypotheses.**
- **H-contam-lex (lexical-contamination probe).** If a substantial fraction of
  the model's solve / validate accuracy on canonical IPC domains is driven by
  *lexical memorisation* of the published corpus, then renaming surface symbols
  will degrade performance even though the underlying planning problem is
  unchanged.
- **H-null (structural-only).** If accuracy is driven by reasoning over the
  *structure* (typed parameters, precondition / effect logic), then surface
  renames will leave accuracy within CI of the canonical baseline.

**What this DOES test.** Lexical / surface-form memorisation. Detectable by a
swap of `truck` → `train`, `depot` → `dock`, `lift` → `winch`.

**What this DOES NOT test.** Structural / topological memorisation. The
action skeleton (parameters, types, precondition shape) is preserved — Qwen
could still recognise "this is depots" from its 5-argument lift+drop+load+unload
signature. To probe that, a follow-up would adopt the **Mystery-BW** style of
[Huang & Zhang ACL 2025] full structural obfuscation. This pilot is the
*cheaper, narrower* lexical probe; we report it as such.

**Comparator (paired design).** Same 6 arms × same model × same task set,
canonical corpus vs renamed corpus. Per-cell paired delta with 95% Wilson CI on
the renamed minus canonical difference.

---

## 2. Experiment Matrix

**Model.** `qwen3.6:35b` (the user-spec'd "qwen 35B" — the only 35B-class entry
in the active roster per `EXPERIMENTS_FLOW.md` §2; vLLM parser `qwen3_xml` per
`reference_vllm_parser_per_model.md`).

**Arms (6 logical arms, 4 invocations).**

| # | Condition | Variants | Think | Notes |
|---|-----------|----------|-------|-------|
| 1 | no-tools  | v11/v12/v13 (neutral) | on  | nt-neut, think on |
| 2 | no-tools  | v11/v12/v13 (neutral) | off | nt-neut, think off |
| 3 | with-tools | v11–v16 (neutral + steered) | on  | tools neut + steered, think on |
| 4 | with-tools | v11–v16 (neutral + steered) | off | tools neut + steered, think off |

Steered / neutral within with-tools are post-hoc separable by
`prompt_variant` field (v11–v13 = neutral, v14–v16 = steered) — same
sweep-5 convention. We do **not** include the optional `--include-no-tools-steered`
control arm; this pilot has no resources to spend on it.

**Tasks.** All 5 (`solve`, `validate_domain`, `validate_problem`, `validate_plan`,
`simulate`).

**Trials per cell.** Same as sweep-5: 3 paraphrases × per-task fixture count.

**Total invocations.** 4 (canonical baseline reuses existing sweep-5 results;
new compute is 4 invocations on the renamed corpus).

---

## 3. Renaming Methodology — Deterministic Theme Remap

**Why deterministic, not LLM-rewrite.** A regex / AST-driven theme map is
- reproducible from the mapping file alone,
- guaranteed to preserve PDDL syntactic structure (we never invent new tokens),
- testable by symmetric round-trip (re-map back → byte-equal canonical),

which an LLM-rewrite cannot guarantee. `pddl-author` / `pddl-fixer` are
*not* used for the rename itself; they appear later as a fallback for solver
re-derivation if a generated plan fails.

### 3.1 Per-domain symbol table

For each of the 20 domains, build a `anon_map.yaml` (stored as
`domains-anon/_maps/<domain>.yaml`):

```yaml
domain: depots
theme: maritime
rename:
  types:
    place: harbour
    locatable: vessel_or_cargo
    depot: dock
    distributor: warehouse
    truck: barge
    hoist: winch
    surface: deck
    pallet: skid
    crate: container
  predicates:
    at: docked_at
    on: stacked_on
    in: stowed_in
    lifting: hoisting
    available: ready
    clear: empty
  actions:
    drive: sail
    lift: winch_up
    drop: winch_down
    load: stow
    unload: unstow
  object_prefixes:        # for p01..p05 / n01..n05 objects
    depot: dock
    distributor: warehouse
    truck: barge
    pallet: skid
    crate: container
    hoist: winch
```

**Constraints on the mapping:**
1. **Bijective** — no two source symbols map to the same target.
2. **Theme-cohesive** — within a domain, replacements share a semantic field
   (maritime, agricultural, etc.). Mixing themes leaks no information; cohesion
   just makes the resulting PDDL legible to a human reviewer.
3. **Lexically distant from the canonical** — no rename that is a synonym or
   morphological variant (`truck` → `lorry` is too close); aim for cross-domain
   distance.
4. **Same syntactic class** — types stay nouns, actions stay verbs, predicates
   stay verb-phrases. Avoids any signal from POS shift.
5. **No collisions with PDDL keywords** — never rename to `define`, `domain`,
   `requirements`, `types`, `predicates`, `action`, `parameters`, `precondition`,
   `effect`, `and`, `or`, `not`, `forall`, `exists`, `when`, `object`, `either`,
   `init`, `goal`, `assign`, `increase`, `decrease`, `total-cost`, `metric`,
   numeric op names, etc.
6. **Reserved-name guard** — never rename to a token that already appears as a
   different symbol in the same domain (e.g. cannot rename `lift` → `drop`
   even if `drop` were also being renamed — would create transient parser
   ambiguity).

### 3.2 Mechanical rewrite

For each PDDL file (domain, problem, plan):
- Tokenise on PDDL lexical rules (whitespace + paren boundaries; case-insensitive).
- For every token, look up in the merged rename table; substitute if matched.
- Preserve original whitespace, comments, casing convention.
- For object names (`depot0`, `truck1`, …): pattern `(<canonical-type-name>)(\d+)`
  → `(<renamed-type-name>)\g<2>` (numeric suffix preserved).
- Plan files: the `(<action> <args…>)` lines are rewritten with both the
  action rename and the object-name remap.
- **Problem-name post-pass (added 2026-05-26):** every `(define (problem X))`
  header in `p0N.pddl` / `n0N.pddl` is wholesale-replaced with the deterministic
  synthetic identifier `<renamed_domain_token>-<file_stem>` (e.g.
  `apiary-p01`, `tearoom-n02`). Runs *after* the identifier char-walk and
  object-prefix regex so the synthetic name is opaque to both. Closes the
  leak class where canonical (or canonical-substring) tokens survived in the
  problem identifier — `parking` (literal match), `delivery-x-1`, `depotprob81`,
  `roverprob511`, `bw_rand_3`, `ZTRAVEL-2-1`, `gripper-1-3-1` (substring
  matches inside atomic PDDL identifiers; partial substitution would have
  been unsafe). The original problem name is recorded in `_rename.log` and
  restored by the round-trip-check via the canonical source.
  **Embedded renamed-domain token is deliberate**, not a separate leak:
  `(:domain X)` on the very next line already exposes the renamed-domain
  identifier, so the synthetic header's `<renamed_domain_token>-…` prefix
  carries no additional signal. The rename target is the unit of
  identification within the renamed corpus, by design.
- **Header-shape audit (added 2026-05-26):** `rewrite_corpus` runs an
  invariant check on the staged tmp directory before atomic-promote — every
  `p0N.pddl` / `n0N.pddl` header must match
  `\(define\s+\(problem\s+[a-z][a-z0-9_-]*-[pn]\d{2}\)`. A regression in the
  problem-name pass aborts the rewrite atomically; the previous
  `domains-anon/` stays untouched.

**Implementation note.** Write this as a single Python script
`tools/anon_rename.py` that consumes a per-domain `anon_map.yaml` and a
source directory (always `domains/`), emits a target directory (always
`domains-anon/`). Idempotent on re-run, fails closed on collision / keyword
violation, refuses to start if the output path resolves to `domains/` or
inside it (defence-in-depth per §6). No external libs beyond `re` and `yaml`.

### 3.3 Negative-fixture preservation

`domain_neg.pddl`, `n01..n05.pddl`, and `p<NN>_b<K>.plan` carry intentional
bugs from the taxonomies in `domains/README.md`. The bugs are *structural*
(missing precondition, wrong arity, undeclared object, etc.) — none of them
depend on a specific symbol name. Therefore the same mechanical rewrite
applied to a negative fixture preserves the bug.

**Verification gate (§4):** after rewrite, every negative must still validate
`valid=false` against the matching validator tool. If any negative flips to
`valid=true`, the rename script's behaviour is buggy on that fixture and the
domain is excluded until fixed. We do **not** patch the renamed negative by
hand; the rewrite must be the identity on bug-structure.

---

## 4. Validation Pipeline (fail-fast at each gate)

Run per domain, in order. Each step gates the next.

| # | Gate | Tool (MCP) | Pass criterion |
|---|------|------------|----------------|
| 1 | Domain syntax | `pddl-parser → inspect_domain` on `domain.pddl` (renamed) | Parses; exposes the renamed types / predicates / actions. |
| 2 | Domain validity | `pddl-validator → validate_domain` | `valid=true`. |
| 3 | Negative-domain validity | `pddl-validator → validate_domain` on `domain_neg.pddl` (renamed) | `valid=false`. |
| 4 | Positive-problem validity (×5) | `pddl-validator → validate_problem` on each `p0N.pddl` | `valid=true`. |
| 5 | Negative-problem validity (×5) | `pddl-validator → validate_problem` on each `n0N.pddl` | `valid=false`. |
| 6 | Re-solve positives (×5) | `pddl-solver → classic_planner` / `numeric_planner` | Plan returned. |
| 7 | Plan equivalence | `pddl-parser → get_trajectory` on (`pNN_v1.plan` renamed) vs solver output — both reach the goal | Both `valid=true` against the renamed domain / problem. |
| 8 | Valid plan validity (×5×5) | `pddl-validator → validate_plan` on each `pNN_vK.plan` (renamed) | `valid=true`. If any `vK` fails, replace it with a freshly-solved plan from step 6. |
| 9 | Invalid plan validity (×5×5) | `pddl-validator → validate_plan` on each `pNN_bK.plan` (renamed) | `valid=false`. (Same identity-on-bug-structure invariant as §3.3.) |
| 10 | Trajectory smoke (×5) | `pddl-validator → get_state_transition` on each (`pNN.pddl`, `pNN_v1.plan`) | Non-empty `trajectory`; `valid=true`. |

**Round-trip determinism check (independent of MCP):** apply the inverse
rename to the rewritten corpus, byte-compare to the canonical corpus. Must be
identical except for harmless whitespace differences from the rewrite. Any
non-trivial diff = bug in the rewriter.

**`generate_ground_truth` re-run.** Once §4 passes per domain, run
`run_experiment.py` in a ground-truth-only mode against the renamed corpus.
The existing startup fail-fast (`generate_ground_truth` aborts on any
`p<NN>_vK` that the validator rejects, per `EXPERIMENTS_FLOW.md` §6) is the
final integration gate.

---

## 5. MCP Tool Usage Map

| Capability | Where in the pipeline | Why |
|---|---|---|
| `pddl-parser → inspect_domain` / `inspect_problem` | §3.1 to extract the canonical symbol table per domain; §4 step 1 to confirm post-rewrite parse | Source of truth for what symbols exist; avoids us inventing symbols. |
| `pddl-parser → get_trajectory` | §4 step 7, step 10 | Sanity-checks that the renamed problem + plan still produce a coherent trace. |
| `pddl-validator → validate_domain` / `validate_problem` / `validate_plan` | §4 steps 2 – 5, 8 – 9 | The only ground-truth oracle for the renamed corpus. |
| `pddl-validator → get_state_transition` | §4 step 10 | Trajectory smoke; matches the harness's `simulate` ground-truth path. |
| `pddl-solver → classic_planner` / `numeric_planner` | §4 step 6 (and as fallback if a renamed `vK` plan no longer validates) | Re-derive plans whose action names have changed; provides a known-good plan in the renamed alphabet. |
| `pddl-author → /pddl-authoring`, `pddl-fixer → /pddl-fixing` | **Not used** for the rename itself (deterministic rewriter, §3.2). Reserved as an escape hatch if a domain's negative fixture cannot survive mechanical rewrite — in that case author a fresh renamed-corpus negative from scratch with the same bug class. | Author / fixer are LLM-loop tools; we keep them out of the deterministic path but acknowledge them as a fallback for unusual fixtures. |

---

## 6. File Layout

**Hard invariant: `domains/` is never written to by any step of this plan.**
The renamed corpus lives in a top-level sibling directory `domains-anon/`.
This guarantees the canonical fixtures (which the paper cites by file path)
stay byte-identical even if the rewriter has bugs.

```
domains/                       # CANONICAL — read-only for this plan.
  classical/...                #   Never touched.
  numeric/...                  #   Never touched.
domains-anon/                  # NEW top-level dir (sibling of domains/).
  classical/<domain>/...       #   Mirrors layout exactly (domain.pddl,
  numeric/<domain>/...         #   domain_neg.pddl, p01..p05.pddl,
                               #   n01..n05.pddl, pNN_vK.plan, pNN_bK.plan).
  _maps/<domain>.yaml          #   Per-domain rename table (committed).
  _rename.log                  #   Rewriter audit log (committed).
tools/
  anon_rename.py               # Deterministic rewriter (new). Reads from
                               #   domains/<...>, writes to domains-anon/<...>.
                               #   Refuses to start if the output path is
                               #   inside domains/ or equal to domains/.
  anon_validate.py             # Runs §4 gates against MCP servers (new),
                               #   over domains-anon/ only.
```

`domains-anon/` mirrors the same `{classical,numeric}/<domain>/` layout the
existing `pddl_eval.domains.load_domains` expects, so no Python changes are
needed — the harness is just pointed at the new root via `--domains-dir`
(see §7).

The rewriter (`tools/anon_rename.py`) MUST:
- Refuse to run if `--output-dir` resolves to `domains/` or any path inside it.
- Write atomically (write to `domains-anon.tmp/`, rename to `domains-anon/`
  on success) so a crashed run can't leave `domains-anon/` in a partial state
  that gets accidentally used.
- Never open any file under `domains/` in write mode — read-only opens only.

---

## 7. Harness Wiring

The runner already accepts `--domains-dir` (`run_experiment.py` line 561) — so
no Python changes are needed; the renamed corpus is selected at the CLI by
pointing this flag at `domains-anon/`.

**Required cluster-side change:** `cluster-experimenting/submit_with_rtx.sh`
does not currently forward `--domains-dir` through to the sbatch invocation.
Add a `--domains-dir <path>` pass-through flag mirroring the existing
`--include-no-tools-steered` plumbing pattern, propagated into
`run_condition_vllm_rtx.sbatch` and onto the `python3 run_experiment.py …`
line. Single-file edit; one new env variable.

The wrapper MUST also reject any `--domains-dir` whose resolved real-path is
`domains/` or inside it, even though §6 promises the rewriter never writes
there — defence-in-depth so a typo at submit time can never accidentally
re-run the canonical fixtures under the contamination-probe banner.

**Submit incantations** (after the pass-through is added):

```bash
# Canonical baseline (re-use sweep-5 results if qwen3.6:35b was in scope at
# the same 6 arms — confirm via §11 open question 3; otherwise re-run on
# the canonical tree). Default --domains-dir is the canonical domains/.
bash cluster-experimenting/submit_with_rtx.sh qwen3.6:35b

# Renamed corpus (the upcoming test). Same 4 invocations, different tree.
bash cluster-experimenting/submit_with_rtx.sh qwen3.6:35b \
     --domains-dir domains-anon
```

Result directories are tagged by run-name in
`cluster-experimenting/submit_with_rtx.sh`; pick a distinct `--run-tag anon-probe`
to avoid clobbering canonical results on disk and in `results/slurm_vllm_*`.

---

## 8. Phased Execution

**Phase A — pilot (3 domains end-to-end).**
Picks: `depots` (paper, boolean, multi-type), `gripper` (PR-3, boolean,
single-type), `counters` (paper, numeric, minimal). Authors / runs §3–4 on
exactly those three. Verifies the rewriter, the validation gates, and the
harness wiring on a small surface. Estimated cost: 1 day rewriter dev + 1 day
fixture validation + 1 cluster invocation pair (canonical vs `domains-anon/`)
on 4 arms × 3 domains.

**Phase B — full corpus (remaining 17 domains).**
Batches of 5 domains. Same pipeline. No new code; new YAMLs only.

**Phase C — analysis.**
Notebook lives in `cluster-experimenting/analyzer/` (per the `analyzer` skill).
Required tables / figures:

- Paired (canonical, `domains-anon/`) success-rate panel per (arm × task),
  with Wilson CI on the per-cell difference.
- Per-task break-down: where (if anywhere) is the largest anon-corpus
  drop?
- `failure_reasons` shift table: does `FR_FORMAT_PARSE_FAIL` rise (model
  confused by unfamiliar tokens) vs `FR_VERDICT_MISMATCH` (reasoning intact,
  surface form irrelevant)?
- `tool_selected_rate` panel (with-tools arms only): does the model still
  pick the right MCP tool when the domain wears unfamiliar clothes?

**Decision gate after Phase A.** If pilot already shows a large anon-corpus
drop (>5 pp on the headline cell, outside CI), Phase B is justified. If the
pilot delta is within CI on all three domains, decide whether to (a) stop —
lexical contamination not detected at this n — or (b) escalate to the
Mystery-BW-style structural obfuscation (a different design, not this plan).

---

## 9. Risks & Limitations

| Risk | Mitigation |
|---|---|
| **Surface rename leaks structure.** The action skeleton (5-arg lift / 4-arg load / etc.) is preserved; a strong model may recognise depots from arity alone. | Acknowledged. This is a *lexical* probe by design. Negative result here does NOT rule out memorisation — only the easiest form of it. Report the limitation prominently. |
| **Negative-fixture invariance not actually identity on bug-structure.** A bug class encoded as "predicate `foo` declared with wrong arity" survives rename; a bug class encoded as "uses keyword `at` in a forbidden context" might not. | §4 gates 3, 5, 9 catch this. Any fixture that flips polarity is excluded from the pilot and re-authored via `pddl-fixer` for Phase B. |
| **Solver outputs a `v1` plan that no longer matches the committed `v2..v5` diversity** (Fast Downward / ENHSP may pick a different optimal under renamed symbols). | Acceptable. Plan diversity is a per-call grader robustness affordance, not a correctness assertion. Validate each `vK` independently; replace any that no longer validates with a freshly-solved plan. |
| **`qwen3.6:35b` tokeniser splits the unfamiliar theme tokens awkwardly**, inflating prompt length and triggering `FR_THINK_OVERFLOW` / truncation. | Watch `tokens.prompt` and `done_reason` per cell. If truncation rises >5 pp vs canonical, raise `--num-predict` (per `EXPERIMENTS_FLOW.md` §5) and re-run only the affected cells. |
| **submit wrapper pass-through bug.** `--domains-dir` reaches the python CLI but the wrong tree is picked. | Phase A is the smoke. Always print the resolved `--domains-dir` in the first 5 lines of the runner log and confirm by eye before scaling. |

---

## 10. Effort Estimate

| Stage | Effort |
|---|---|
| Author per-domain rename YAMLs (20 domains) | ~30 – 45 min each; 10 – 15 h total. Cross-check vs §3.1 constraints by eye. |
| Build `tools/anon_rename.py` + `tools/anon_validate.py` | 4 – 6 h |
| Submit-wrapper `--domains-dir` pass-through | 30 min |
| Phase A pilot run + analysis | 1 day cluster time + half a day analyst time |
| Phase B full-corpus | 2 – 3 days cluster time (1 model × 4 invocations × n domains) |
| Phase C paper-ready figures + table | 1 day |

---

## 11. Open Questions for the User

1. **Model identity.** Confirm "qwen 35B" means `qwen3.6:35b`. (The roster has
   no other 35B-class model.)
2. **All 20 domains, or accept the Phase A → B gate?** Phase A pilots three; if
   the result is within CI, do we still want Phase B regardless, or stop?
3. **Canonical baseline reuse.** If sweep-5 already covers `qwen3.6:35b` at the
   exact 6 arms, we re-use those rows as the canonical baseline. If sweep-5
   used a different prompt-variant active set, we rerun the canonical too.
   (TODO: check `results/` for matching `meta.prompt_variants_active`.)
4. **Where do the renamed corpora live in git?** Default per this plan:
   same repo, top-level `domains-anon/` sibling of `domains/`. Alternative:
   a separate sibling repo that cleanly separates the contamination-probe
   artefact from the canonical fixtures the paper cites. Same-repo is the
   default unless you flag a paper-distribution concern.
5. **Naming.** Tag this `sweep-6-contam` or keep it as a one-off probe
   outside the sweep-N convention?

---

## 12. Out-of-Scope (explicit non-goals for this plan)

- Structural obfuscation (Mystery-BW style). A separate plan if the lexical
  probe is negative.
- More models. The plan is 1-model by user request. Adding models is a
  multiplicative cluster-time cost; defer until lexical effect is established.
- Re-running the chain-of-tasks phase. Sweep-5 retired chain; this probe is
  single-task only.
- Modifying the steered v14/v15/v16 prompt strings. They reference *task*
  names (`validate_plan`, `solve`) and tool names, not domain constants —
  unaffected by the rename. Verified in `pddl_eval/prompts.py`
  `WITH_TOOLS_STEERED_USER_TEMPLATES`.
