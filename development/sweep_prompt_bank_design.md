# Sweep-5 prompt-bank design

Dated 2026-05-23. Branch: `sweep5-new-prompts`. **Marketplace pin:** post-PR-52 (pddl-copilot @ `2850bc4`, marketplace `1.4.0`, validator `3.0.0`). **Backend pin:** vLLM only (Ollama retired 2026-05-23 — see `project_ollama_retired` memory).

This is the design doc for the prompt bank that ships with sweep-5. It supersedes:
- the sweep-3 active set v0/v1/v2 (kept byte-stable in `pddl_eval/prompts.py` for replay only),
- the sweep-4 / sweep-4.1 sets v5/v6/v7 and v8/v9/v10 (likewise kept byte-stable),
- the earlier sweep-4 draft of this document (committed at `da5f6ee`, then revisited 2026-05-21).

The earlier draft proposed *curated SKILL-inlining* in the system prompt. That approach was internally inconsistent — §2.3 invoked surface-area parity as the no-tools-mirror rationale while §3.1 violated it with per-task SKILL bodies. A fresh-session review (transcript in conversation history) flagged the contradiction; this rewrite resolves it by switching to **thin per-task policy stubs** that genuinely mirror across arms (Option C).

The 2026-05-23 marketplace split (`validate_pddl_syntax` → `validate_domain` / `validate_problem` / `validate_plan`, all task-aligned with required-argument schemas) also collapses the `validate_plan` two-sentence steered directive that the prior draft needed. Under the new tool surface every steered prompt is *one* appended directive sentence.

---

## 0. Pre-registration

Locked at commit-on-merge of this doc onto `sweep5-new-prompts`. Marketplace pin must remain `pddl-copilot @ 2850bc4` for the entire sweep-5 + control submission window.

**Matrix.**

| Axis | Values | Source |
|---|---|---|
| Models | `Qwen3.5:0.8B`, `Qwen3.5:4B`, `Qwen3.5:9B`, `qwen3.6:35b`, `gemma4:26b-a4b` | vLLM roster post-2026-05-18 backend unification |
| Conditions | `no-tools`, `tools_all_minimal` | sweep-3/4 conventions; `tool_filter=per-task` retired |
| Think modes | `on`, `off` | per-cell |
| Tasks | `solve`, `validate_domain`, `validate_problem`, `validate_plan`, `simulate` | unchanged |
| Problems | per-task corpus (same as sweep-4) | `domains/` |
| Prompt variants | `v11`, `v12`, `v13` (neutral); `v14`, `v15`, `v16` (steered) | this doc §3 |
| Steering arm | neutral (no-directive) or steered (one directive sentence appended) | new for sweep-5 |

**Active sub-matrices.**
- **Sweep-5 main** (3-arm): `(no-tools × v11/v12/v13)` + `(with-tools × v11/v12/v13)` + `(with-tools × v14/v15/v16)`. Emit-skip frozenset gates `(no-tools × v14/v15/v16)` cells.
- **Sweep-5 control** (4th arm, full): `(no-tools × v14/v15/v16)`. Submitted as a separate cluster job tagged distinctly from the main sweep so analyzer joins remain unambiguous. Same model × task × problem × think footprint as one main arm.

**Primary outcomes (reported with Wilson 95% CIs).**
1. `result_correct` rate per cell.
2. `tool_selected` rate per `with-tools` cell.
3. Output-token count per cell (median and mean).
4. `FR_*` distribution per cell — `FR_TOOL_NOT_SELECTED`, `FR_WRONG_TOOL` (new in marketplace 1.4.0), `FR_TOOL_ERROR`, `FR_VERDICT_MISMATCH`, `FR_RESULT_MISMATCH`, `FR_FORMAT_PARSE_FAIL`, `FR_TRUNCATED_NO_ANSWER`, `FR_THINK_OVERFLOW`, `FR_LOOP_EXHAUSTED`, `FR_EXCEPTION`.

**Hypotheses (pre-registered).**
- **H1 (tool utility, headline)**: tools improve `result_correct` over no-tools at *constant prompt content* — i.e., `(with-tools, v11/v12/v13)` > `(no-tools, v11/v12/v13)`. This isolates tool availability from prompt content because the neutral text is byte-identical across the two arms.
- **H2 (steering effect)**: explicit steering improves `tool_selected` over neutral within with-tools — i.e., `(with-tools, v14/v15/v16)` > `(with-tools, v11/v12/v13)` on `tool_selected` AND `FR_WRONG_TOOL` decreases.
- **H3 (token efficiency)**: with-tools cells produce fewer output tokens than no-tools cells per successful trial (tool-result-conditioned vs inline reasoning).
- **H4 (control / falsification)**: the steered directive alone does not move the no-tools floor — i.e., `(no-tools, v14/v15/v16)` ≈ `(no-tools, v11/v12/v13)` within run-to-run noise. If H4 fails, the H2 attribution to steering effect is compromised.

**Sample size**: per-task corpus from `domains/` × paraphrases (3) × think modes (2) × models (5) × condition (2 for main; 1 additional for control). Wilson CIs are tightest where N×paraphrases is highest.

**Exclusion rules.**
- `infra_failure=True` rows excluded from all denominators (transport/cluster failures unrelated to model performance).
- Truncation override: `FR_TRUNCATED_NO_ANSWER` reassignments per `_apply_truncation_override` in `pddl_eval/scoring.py` apply at write time and are honored as-stored at analysis time.
- All other `FR_*` tags count as failures in `result_correct`.

**Multiple-comparison correction**: Wilson 95% CIs per cell. For paper-level claims comparing cell pairs (e.g., H1 on each of 5 tasks × 5 models = 25 comparisons), Bonferroni applied: per-comparison α = 0.05/25 = 0.002.

---

## 1. Literature & industry anchors (verified from primary sources)

Only sources I could verify from primary text are cited. Abstracts-only material is excluded by the user direction ("focus on highly-regarded papers or companies; their methodology is probably the narrative").

### 1.1 Anthropic — Define Tools docs (primary source)

URL: `https://platform.claude.com/docs/en/docs/agents-and-tools/tool-use/define-tools` (fetched 2026-05-21).

- "Provide extremely detailed descriptions. This is by far the most important factor in tool performance." Recommended length: "Aim for at least 3-4 sentences per tool description, more if the tool is complex."
- The API "constructs a special system prompt from the tool definitions, tool configuration, and any user-specified system prompt." **Tool definitions belong in `tools=[]`; the user system prompt is appended, not a duplicate of the schema.**
- Soft-steering pattern: "you can use `{"type": "auto"}` for `tool_choice` (the default) and add explicit instructions in a `user` message. For example: `What's the weather like in London? Use the get_weather tool in your response.`" — **this is the canonical neutral-vs-steered design**: same body + one appended directive in the user prompt.
- `tool_choice=auto` is the default when tools are present. Forced tool-use is not supported with extended thinking (relevant — our matrix includes `think=on`).

### 1.2 Anthropic — "Writing tools for agents" engineering blog (primary source)

URL: `https://www.anthropic.com/engineering/writing-tools-for-agents`.

- "Prompt-engineering your tool descriptions and specs" ranks among "the most effective methods for improving tools. Even small refinements can yield dramatic improvements."
- "More tools don't always lead to better outcomes" — consolidate, don't proliferate.
- "Write descriptions as if teaching a new team member, making implicit context explicit."

These two Anthropic sources jointly say: the **tool-description quality bar** lives in the marketplace's `tools=[]` definitions, not in our system prompt. PR-52 in `pddl-copilot` raised the bar at that source (3-4 sentence per-tool descriptions, error-mode enumeration, schema enumeration of `status` values). Our experiments-repo system prompt then does NOT need to restate any of that.

### 1.3 BFCL — Berkeley Function-Calling Leaderboard methodology (primary source)

URL: `https://gorilla.cs.berkeley.edu/blogs/8_berkeley_function_calling_leaderboard.html`.

- **Function-calling models receive no explicit system prompt** — only `tools=[]`. Verbatim: "For all the function calling models, we did not supply any system prompt but instead, toggle the function calling mode on and put the function definitions where they should be."
- Three orthogonal eval dimensions: **relevance detection** (should-call), **function selection** (which-tool), **parameter filling** (correct-args). No no-tools baseline; relevance detection tests "none of the provided functions are relevant" as the rejection condition.

Our matrix maps directly onto two of these (selection = `FR_TOOL_NOT_SELECTED` vs `FR_WRONG_TOOL`; parameter filling = no longer applicable because marketplace 1.4.0's schema enforcement eliminates the parameter-filling error class for the validator tools). The third (relevance detection) does not apply — every cell's prompt is a task where some tool *is* relevant.

### 1.4 ReAct (Yao et al. 2022, arXiv:2210.03629) — primary structural pattern

- Reasoning + Action interleaved; "1–2 in-context examples sufficient" — exemplars teach *shape*, not *content*.

We use the "shape exemplar" pattern in the `simulate` task's wire-format teaching (one JSON-shaped step in each paraphrase). Not used for solve / validate_* (where the JSON schema constraint already enforces shape).

### 1.5 PDDL Copilot paper (Spector & Cohen, arXiv:2509.12987) — the project's research thesis

- The headline claim: LLMs fail at PDDL planning / validation / simulation; offloading to symbolic tools is the fix. This is the **only** reason the no-tools arm exists in our matrix — BFCL doesn't run one because it answers a different research question.

### 1.6 Synthesis — matrix shape is well-grounded

| Arm | What it measures | Anchored to |
|---|---|---|
| `(no-tools, v11/v12/v13)` | floor: model's unaided capability under a well-engineered, format-constrained prompt | PDDL Copilot paper (headline) |
| `(with-tools, v11/v12/v13)` | BFCL **relevance detection** — does the model spontaneously call the right tool when its existence is known but not steered? | BFCL relevance dimension |
| `(with-tools, v14/v15/v16)` | BFCL **function selection** — with explicit steering, does the model select the right tool? (parameter filling is now schema-enforced, so this isolates selection) | BFCL selection dimension + Anthropic user-message-steering exemplar |
| `(no-tools, v14/v15/v16)` *(control, sweep-5 control arm)* | **falsification check on H4**: does the steered directive alone move the no-tools floor? | Internal — closes the "is it tools or is it the prompt" door |

The fourth arm `(no-tools, steered)` is methodologically valuable as a control (closes a confound) but is *not* the headline 3-arm comparison; it's a separate cluster submit and reported as a control in §Results, not as a primary outcome.

---

## 2. Methodology

### 2.1 Three-arm matrix (justified)

Pre-approved by user on 2026-05-21. Re-validated against literature in §1.6. Resolves the H1 vs H2 attribution question by holding prompt content constant between `(no-tools, neutral)` and `(with-tools, neutral)`, and holding tool availability constant between `(with-tools, neutral)` and `(with-tools, steered)`.

### 2.2 Variant indexing v11–v16

| Pair (neutral, steered) | Paraphrase character |
|---|---|
| (v11, v14) | imperative — "Solve…", "Check if…", "Validate…", "Simulate…" |
| (v12, v15) | declarative — "Find a valid plan…", "Validate the syntax…", "Step through this plan…" |
| (v13, v16) | interrogative — "Is this PDDL domain syntactically correct?", "Is this plan valid…?" |

The neutral text is byte-identical between the no-tools and with-tools-neutral arms. The steered text inserts exactly one directive sentence at the position just before the body anchor (`\n\nDomain:`), preserving the neutral text byte-for-byte everywhere else. The pure-append property is enforced as a unit test (§3.5).

`STEERED_VARIANTS = frozenset({14, 15, 16})` gates emit-time skip behavior:
- Main sweep submit: emit-skip ON → `(no-tools, v14/v15/v16)` cells are not emitted.
- Control sweep submit: emit-skip OFF → `(no-tools, v14/v15/v16)` cells emit as the 4th arm.

This is one CLI flag on `run_experiment.py` (`--include-no-tools-steered`, default off) that flips the gate.

### 2.3 System-prompt design (Option C — thin per-task policy stubs)

The prior draft's `WITH_TOOLS_SYSTEM_BY_TASK` inlined tool signatures, polymorphism warnings, and workflow steps for each task. That violated two principles:
- **Anthropic §1.1**: schema lives in `tools=[]`, not in the system prompt. Duplicating it wastes tokens and creates a maintenance liability (tool-description drift between marketplace and system prompt).
- **Anthropic §1.2** (writing tools for agents): tool-description quality investment belongs in the marketplace. PR-52 already raised the bar at that source (3-4 sentence per-tool descriptions, error-mode enumeration). The system prompt should not re-implement that quality work.

**Option C** keeps per-task system prompts (preserving user-approved D3 of the 2026-05-21 question round) but each entry is a **3-sentence behavior policy** that names the assistant's task role, the policy claim ("you cannot do X from training alone — use the tool"), and the tool category — without restating the tool's signature, arguments, or status enumeration. The tool's full description lives in `tools=[]` (marketplace 1.4.0 quality bar).

### 2.4 No-tools mirror parity

The (no-tools, neutral) vs (with-tools, neutral) comparison is the central PDDL Copilot claim (H1). To isolate tool availability from instruction-surface differential, **both arms' system prompts have the same structure**:
- 3 sentences each.
- Same role-framing sentence.
- Same task-orientation sentence.
- Differ only on the third sentence: "use the tool" (with-tools) vs "use your own reasoning" (no-tools).

Per-task on both sides. `WITHOUT_TOOLS_SYSTEM_BY_TASK[task]` is the structural mirror of `WITH_TOOLS_SYSTEM_BY_TASK[task]`.

### 2.5 Marketplace 1.4.0 effects on the prompt bank

The validator tool split (`validate_pddl_syntax` → three task-aligned tools, each with a JSON schema enforcing its required arguments) **eliminates the parameter-filling error class** for validators. Consequences:

- **`validate_plan` steered directive simplifies to one sentence.** The prior draft's two-sentence directive ("if you omit `plan`, the tool checks domain/problem syntax but never tests whether the plan actually solves the problem") was teaching the model to defend against a polymorphism that no longer exists. Under marketplace 1.4.0 a model that tries to call `validate_plan` without `plan` gets a schema validation error before the tool even runs. The steered directive collapses to: "Use the `validate_plan` tool with the domain, problem, and plan as arguments."
- **`FR_WRONG_TOOL` is now a distinct, measurable failure mode.** Before the split, every validator call landed in the same `validate_pddl_syntax` bucket. After, calling `validate_problem` while task = `validate_plan` is graded as `FR_WRONG_TOOL` (not the previous `FR_VERDICT_MISMATCH` masquerade). This sharpens H2: steering should specifically reduce `FR_WRONG_TOOL`.
- **No `verbose=` references in any prompt.** The harness pins `verbose=False` and strips the param from the schema (`pddl_eval/chat.py:_PINNED_VERBOSE_FALSE`); mentioning it in the prompt would teach the model about a knob it cannot see.

### 2.6 Sweep-5 scope: complete backed-up experiment

Sweep-5 is a **complete experiment**, not a follow-up. The earlier framing ("sweep-4.1 follow-up") was retired because the marketplace 1.4.0 split is a substantial enough tool-surface change that bundling it into a "follow-up" understates the methodological reset.

Sweep-5 includes:
- **Main 3-arm sweep**: 5 models × 2 conditions × 2 think × 5 tasks × N problems × 3 paraphrases × {neutral OR steered per condition rules} = full matrix.
- **Control 4th arm**: `(no-tools, steered)` across the same matrix shape as one main arm. Tagged separately in the cluster output for analyzer-side join cleanliness.

Together these form the 4-arm dataset that the paper draws from. Sweep-3/4/4.1 results are *historical* — preserved in `results/` and `checkpoints/` at their respective marketplace pins, not joined into sweep-5 aggregations.

---

## 3. The prompt bank

### 3.1 `WITH_TOOLS_SYSTEM_BY_TASK` — thin per-task policy stubs (3 sentences each)

```python
WITH_TOOLS_SYSTEM_BY_TASK: dict[str, str] = {
    "solve": (
        "You are a PDDL planning assistant. LLMs cannot reliably generate "
        "correct plans from training alone (arXiv:2509.12987). Use the "
        "available planner tool to produce the plan."
    ),
    "validate_domain": (
        "You are a PDDL validation assistant. LLMs cannot reliably check "
        "PDDL syntax from training alone. Use the available validation "
        "tool to check the domain."
    ),
    "validate_problem": (
        "You are a PDDL validation assistant. LLMs cannot reliably check "
        "PDDL syntax from training alone. Use the available validation "
        "tool to check the problem against its domain."
    ),
    "validate_plan": (
        "You are a PDDL validation assistant. LLMs cannot reliably check "
        "plan correctness from training alone. Use the available validation "
        "tool to check whether the plan solves the problem."
    ),
    "simulate": (
        "You are a PDDL simulation assistant. LLMs cannot reliably trace "
        "state transitions through a plan from training alone. Use the "
        "available simulation tool to compute the trajectory."
    ),
}
```

No tool names. No argument names. No status enumerations. No polymorphism warnings. The model receives the full tool surface — names, descriptions, JSON schemas, error modes — through `tools=[]` as Anthropic's documentation prescribes.

### 3.2 `WITHOUT_TOOLS_SYSTEM_BY_TASK` — per-task mirror (3 sentences each)

```python
WITHOUT_TOOLS_SYSTEM_BY_TASK: dict[str, str] = {
    "solve": (
        "You are a PDDL planning assistant. PDDL planning tools are not "
        "available in this evaluation. Analyze the domain and problem and "
        "produce a plan using your own reasoning; conform to the JSON "
        "schema provided by the format constraint."
    ),
    "validate_domain": (
        "You are a PDDL validation assistant. PDDL validation tools are "
        "not available in this evaluation. Analyze the domain syntax using "
        "your own reasoning; end your response with exactly one line: "
        "VERDICT: VALID or VERDICT: INVALID."
    ),
    "validate_problem": (
        "You are a PDDL validation assistant. PDDL validation tools are "
        "not available in this evaluation. Analyze the problem against its "
        "domain using your own reasoning; end your response with exactly "
        "one line: VERDICT: VALID or VERDICT: INVALID."
    ),
    "validate_plan": (
        "You are a PDDL validation assistant. PDDL validation tools are "
        "not available in this evaluation. Analyze whether the plan solves "
        "the problem using your own reasoning; end your response with "
        "exactly one line: VERDICT: VALID or VERDICT: INVALID."
    ),
    "simulate": (
        "You are a PDDL simulation assistant. PDDL simulation tools are "
        "not available in this evaluation. Trace the state transitions "
        "using your own reasoning; conform to the JSON schema provided by "
        "the format constraint (per-step state with boolean predicates "
        "and numeric fluents)."
    ),
}
```

Structurally parallel to `WITH_TOOLS_SYSTEM_BY_TASK`. Three sentences each. Same role-framing sentence; second sentence flips "use the tool" to "tools not available"; third sentence flips "use the tool" to "use your own reasoning" and adds the task-appropriate output-shape reminder (VERDICT line for `validate_*`, JSON schema for `solve`/`simulate`).

### 3.3 Legacy constants preserved byte-stable for v0–v10 replay

```python
# UNCHANGED — preserved for replay of sweep-3/4/4.1 cells.
# Do not edit. (Bodies at pddl_eval/prompts.py:46-56 today.)
WITH_TOOLS_SYSTEM: str = "You are a PDDL planning assistant with access to planning tools. ..."
WITHOUT_TOOLS_SYSTEM: str = "You are a PDDL planning assistant. ..."
```

Variant-gated dispatch in `runner.py`:

```python
if prompt_variant >= 11:
    system = (
        WITH_TOOLS_SYSTEM_BY_TASK[task]
        if with_tools
        else WITHOUT_TOOLS_SYSTEM_BY_TASK[task]
    )
else:
    system = WITH_TOOLS_SYSTEM if with_tools else WITHOUT_TOOLS_SYSTEM
```

v0–v10 cells continue to see the original flat constants byte-for-byte; only v11+ routes to the new per-task dicts.

### 3.4 User prompts

**Notation.** In the tables below, `vN + DIRECTIVE` means: the steered string is the neutral `vN` template with the single sentence `DIRECTIVE` inserted **at the position immediately before the `\n\nDomain:` (or `\n\n{domain}`) body anchor** — not appended at the very end of the string. The neutral text from that point onward (body block + VERDICT trailer if present) is preserved byte-for-byte. See §3.5 property test for the exact assertion.

#### `solve` (3 paraphrases × {neutral, steered})

| | Neutral (v11/v12/v13 — used by both no-tools and with-tools-neutral arms) | Steered (v14/v15/v16 — used by with-tools-steered arm) |
|---|---|---|
| **v11/v14** | `Solve this PDDL planning problem and return a plan. Each step must be a single parenthesised PDDL action, e.g. \`(pick-up a)\`.\n\nDomain:\n{domain}\n\nProblem:\n{problem}` | v11 + ` Use the planner tool with the domain and problem as arguments.` |
| **v12/v15** | `Find a valid plan for this PDDL problem. Output each action on its own line in parenthesised PDDL form, e.g. \`(unstack a b)\`.\n\nDomain definition:\n{domain}\n\nProblem definition:\n{problem}` | v12 + ` Use the planner tool with the domain and problem as arguments.` |
| **v13/v16** | `Generate a plan that solves the following planning problem. Each action in your plan must be a single parenthesised PDDL form, e.g. \`(stack a b)\`.\n\nDomain:\n{domain}\n\nProblem:\n{problem}` | v13 + ` Use the planner tool with the domain and problem as arguments.` |

Rationale: action wire-format teaching (one example per paraphrase) addresses sweep-3 review finding 6 (`.local/prompts_review.md`: solve no-tools doesn't teach action format). Steered directive names the *tool category* ("planner tool") not a specific tool ("classic_planner" vs "numeric_planner"); the model picks the appropriate one based on the marketplace's tool descriptions and the domain's `:functions` presence (per Anthropic 1.2: consolidated, well-described tools beat per-call selection guidance in the system prompt).

#### `validate_domain` (3 paraphrases × {neutral, steered})

| | Neutral | Steered |
|---|---|---|
| **v11/v14** | `Check if this PDDL domain definition has valid syntax.\n\n{domain}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID` | v11 + ` Use the validate_domain tool with the domain as its argument.` |
| **v12/v15** | `Validate the following PDDL domain for syntactic correctness.\n\n{domain}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID` | v12 + ` Use the validate_domain tool with the domain as its argument.` |
| **v13/v16** | `Is this PDDL domain syntactically correct?\n\n{domain}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID` | v13 + ` Use the validate_domain tool with the domain as its argument.` |

Rationale: VERDICT trailer present in every neutral (sweep-4 empirical regression fix — without it, `FR_FORMAT_PARSE_FAIL` spikes even under vLLM `guided_json` on hybrid-architecture models; see `project_ctx_bump_32k_smoke_failed` memory). Steered directive names the specific tool because marketplace 1.4.0 made tool selection task-aligned 1:1 with task names.

#### `validate_problem` (3 paraphrases × {neutral, steered})

| | Neutral | Steered |
|---|---|---|
| **v11/v14** | `Check if this PDDL problem has valid syntax given the domain.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID` | v11 + ` Use the validate_problem tool with the domain and problem as arguments.` |
| **v12/v15** | `Validate the syntax of this PDDL problem against its domain.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID` | v12 + ` Use the validate_problem tool with the domain and problem as arguments.` |
| **v13/v16** | `Is this PDDL problem file syntactically correct for the given domain?\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID` | v13 + ` Use the validate_problem tool with the domain and problem as arguments.` |

#### `validate_plan` (3 paraphrases × {neutral, steered}) — one-sentence directive

| | Neutral | Steered |
|---|---|---|
| **v11/v14** | `Validate whether this plan is correct for the given domain and problem.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID` | v11 + ` Use the validate_plan tool with the domain, problem, and plan as arguments.` |
| **v12/v15** | `Check if the following plan solves the PDDL problem.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID` | v12 + ` Use the validate_plan tool with the domain, problem, and plan as arguments.` |
| **v13/v16** | `Is this plan valid for the given planning problem?\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID` | v13 + ` Use the validate_plan tool with the domain, problem, and plan as arguments.` |

The earlier draft's two-sentence directive about polymorphism is gone — `validate_plan(domain, problem, plan)` has `plan` as a required argument in its JSON schema, so the model physically cannot call it with the wrong shape. The previous safety net becomes redundant.

#### `simulate` (3 paraphrases × {neutral, steered}) — wire-format example preserved

The wire-format JSON example in each neutral addresses sweep-3 review finding 5 (no-tools simulate doesn't teach `_normalize_trajectory`'s expected wire format). Following ReAct §1.4 — exemplars teach shape, not content.

| | Neutral | Steered |
|---|---|---|
| **v11/v14** | `Simulate this plan and return the trajectory. Step 0 is the initial state from the problem with \`action\` empty. Each later step records the action executed. \`state.boolean\` lists EVERY predicate that holds in that state, each as a parenthesised lowercase form, e.g. \`(on a b)\`; \`state.numeric\` is the fluents map.\nExample step: {{"step": 0, "action": "", "state": {{"boolean": ["(on a b)", "(clear c)"], "numeric": {{}}}}}}\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}` | v11 + `\nUse the get_state_transition tool with the domain, problem, and plan as arguments.` |
| **v12/v15** | `Step through this plan action by action. For each step emit \`action\` (the action just executed, or empty for step 0) and \`state.boolean\` listing every currently-true predicate in parenthesised PDDL form, e.g. \`(on a b)\`.\nExample step: {{"step": 1, "action": "(unstack a b)", "state": {{"boolean": ["(holding a)", "(clear b)"], "numeric": {{}}}}}}\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}` | v12 + `\nUse the get_state_transition tool with the domain, problem, and plan as arguments.` |
| **v13/v16** | `Show the state at each step of this plan. Step 0 = initial state with empty \`action\`. Each \`state.boolean\` entry lists every predicate that holds in that state, parenthesised and lowercase; \`state.numeric\` is the fluents map (empty for purely-symbolic domains).\nExample step: {{"step": 0, "action": "", "state": {{"boolean": ["(ontable a)", "(clear a)"], "numeric": {{}}}}}}\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}` | v13 + `\nUse the get_state_transition tool with the domain, problem, and plan as arguments.` |

Wire-format example is preserved in the steered prompts even though under with-tools the model can call `get_state_transition` and echo the tool's result. This preserves the pure-append property; the model under with-tools is free to ignore the wire-format teaching (its output will be the tool's result, which already conforms).

### 3.5 Property tests (enforced — new file `pddl_eval/tests/test_prompts.py`)

Run via `bash tests/verify.sh`. Fail the build if any property is violated.

- **Pure-append property.** For each task t and paraphrase k ∈ {0, 1, 2}: the steered template `PROMPT_TEMPLATES_TOOLS_OVERRIDE[t][14+k]` is the matching neutral template `PROMPT_TEMPLATES[t][11+k]` with **exactly one directive sentence inserted** before the body anchor (`\n\nDomain:` or `\n\n{domain}`). The directive ends with a single `.`. The remainder after the inserted sentence equals the matching neutral substring byte-for-byte. **All 15 pairs satisfy this** under the simplified directives — no `validate_plan` exception.
- **VERDICT-trailer presence.** All `validate_*` templates (neutral and steered, both indices 11..16) contain the literal substring `VERDICT: VALID or VERDICT: INVALID` exactly once.
- **`simulate` wire-format example.** All `simulate` templates (neutral and steered) contain the literal substrings `"step":`, `"action":`, `"state":`, `"boolean":`, and `"numeric":` (the JSON example shape).
- **`solve` action example.** All `solve` templates contain at least one parenthesised PDDL action example matching `(pick-up …)` OR `(unstack …)` OR `(stack …)`.
- **No harness-mismatched content.** No template, `WITH_TOOLS_SYSTEM_BY_TASK` entry, or `WITHOUT_TOOLS_SYSTEM_BY_TASK` entry contains any of: `verbose=`, `save_plan`, `get_trajectory`, `check_applicable`, `inspect_domain`, `inspect_problem`, `normalize_pddl`, `validate_pddl_syntax` (legacy polymorphic tool name).
- **System-prompt parity property.** For each task t, `WITH_TOOLS_SYSTEM_BY_TASK[t]` and `WITHOUT_TOOLS_SYSTEM_BY_TASK[t]` both have exactly 3 sentences (counted by `.` followed by whitespace or end-of-string) and start with the identical role-framing sentence ("You are a PDDL [...] assistant.").
- **Emit-skip behavior.** Unit test for the emit-point gate: for each `(with_tools, prompt_variant) ∈ {True, False} × {11, 12, 13, 14, 15, 16}`, assert that exactly the three combinations `(False, 14)`, `(False, 15)`, `(False, 16)` are skipped when `--include-no-tools-steered` is OFF (sweep-5 main); the other 9 combinations are emitted. With the flag ON (sweep-5 control), all 12 combinations emit.

---

## 4. Implementation plan

### 4.1 Files to modify

| File | Action | Description |
|---|---|---|
| `pddl_eval/prompts.py` | additions only | Append v11/v12/v13 (neutral) and v14/v15/v16 (steered) to each task's `PROMPT_TEMPLATES` list; populate `PROMPT_TEMPLATES_TOOLS_OVERRIDE[task][14..16]` only; add new constants `WITH_TOOLS_SYSTEM_BY_TASK` (dict, §3.1) and `WITHOUT_TOOLS_SYSTEM_BY_TASK` (dict, §3.2); leave `WITH_TOOLS_SYSTEM` and `WITHOUT_TOOLS_SYSTEM` byte-identical; flip `ACTIVE_PROMPT_VARIANTS = (11, 12, 13, 14, 15, 16)`; add `STEERED_VARIANTS = frozenset({14, 15, 16})`. v0–v10 strings untouched. |
| `pddl_eval/runner.py` | modify | Replace system-prompt selection at `:288` with the variant-gated dispatch (§3.3 code block). Add the emit-point skip at `_emit_job` (around `:546`): `if not with_tools and prompt_variant in STEERED_VARIANTS and not include_no_tools_steered: continue`. Imports updated. |
| `run_experiment.py` | modify | Add `--include-no-tools-steered` flag (default `False`); thread through to `_emit_job`. Argparse help text mentions the new v11..v16 active set + the control-arm flag. |
| `pddl_eval/tests/test_prompts.py` | create | The §3.5 property tests as Python assertions, runnable via `bash tests/verify.sh`. |
| `tests/verify.sh` | modify | Add `run_test test_prompts.py` line. |
| `EXPERIMENTS_FLOW.md` | modify | §3 paraphrase-count + §4.1 metrics + §11 paper-diff updated to three-arm matrix + sweep-5 framing. Reference this design doc as the source-of-truth for prompts. |
| `development/CHANGELOG.md` | append | Dated 2026-05-23 entry: sweep-5 prompt-bank rationale, link to this doc, list of v11..v16 indices and arm mapping, control-arm flag, no methodology change for v0..v10 cells. |

### 4.2 Validation

1. **Static (test_prompts.py)**: all §3.5 property tests pass. Failure = stop, fix wording.
2. **Smoke (laptop vLLM endpoint or CIS qwen08b)**: 1 model × 5 tasks × 1 problem × all 6 variants × both conditions = 60 trials (with emit-skip filtering down to ~45 actually emitted, plus 9 control cells if flag is on). Eyeball one trial per (task × variant × condition) in `trials.jsonl` to confirm: neutral text matches §3.4 byte-for-byte; steered text adds exactly the directive sentence; system prompts match §3.1/§3.2.
3. **Cluster vLLM smoke**: same single-cell shape on the cluster, before full submit.
4. **Full sweep submit** only after 1–3 all pass.

### 4.3 Compatibility

- v0–v10 trial replay: unchanged (variant-gated dispatch preserves legacy system prompts; legacy prompts.py entries byte-stable).
- v11–v16 are disjoint resume keys; zero collision risk.
- Sweep-3/4/4.1 results in `results/` and `checkpoints/` remain valid as historical snapshots tied to their respective marketplace pins (1.2.0, 1.3.0). Marketplace 1.4.0's validator split makes those trials unreplayable against the new pin; this is intentional per user direction.
- Trial-key shape unchanged (10-tuple); no `runner.py` resume-key edits.

### 4.4 Rollout sequence

1. Write the prompt bank per §3 into `pddl_eval/prompts.py` (additions only).
2. Add `WITH_TOOLS_SYSTEM_BY_TASK` / `WITHOUT_TOOLS_SYSTEM_BY_TASK` to `prompts.py`.
3. Wire the variant-gated dispatch and emit-skip gate in `runner.py` + `run_experiment.py`.
4. Write `tests/test_prompts.py` with §3.5 properties.
5. `bash tests/verify.sh` — all green.
6. Local smoke (laptop vLLM) — §4.2 step 2.
7. Commit on `sweep5-new-prompts` branch. No Claude credits (per `feedback_no_claude_credits_in_commits`).
8. Cluster vLLM smoke — §4.2 step 3.
9. Sweep-5 main submit.
10. After main sweep completes: sweep-5 control submit (same code, `--include-no-tools-steered` flipped on).

---

## 5. Risks

- **Per-task system prompts ship with the codebase**, not with the marketplace. Marketplace updates to tool descriptions don't auto-propagate here, but that's fine because the system prompt no longer restates tool documentation — only the policy framing, which is stable across marketplace versions.
- **VERDICT trailer is a backend-empirical safety belt, not an architectural necessity.** vLLM enforces `guided_json` as a hard grammar (so well-formed JSON is in principle guaranteed), but sweep-4 observed `FR_FORMAT_PARSE_FAIL` spikes on hybrid-architecture models (Qwen3.5/3.6 Mamba hybrid) even under guided decoding. The trailer + `extract_verdict` regex catches those failures. If a future vLLM release tightens guided decoding for hybrid architectures, the trailer becomes redundant — but the safety belt costs ~6 tokens per validate trial and stays.
- **Same-directive-across-paraphrases**: the paraphrase axis varies only the neutral opening clause; the steered directive is byte-identical across the three paraphrases per task. This is deliberate — varying both would mix two sources of variance and dilute the steering measurement. Disclosure goes in §6.
- **Emit-skip gate must be tested**. The §3.5 emit-skip unit test covers all 12 `(with_tools, prompt_variant)` combinations under both flag states. A regression here would silently break the matrix.
- **No SKILL.md inlining in this sweep**. The earlier draft inlined curated SKILL bodies; we dropped that for Option C. If a future sweep wants to test whether richer system-prompt tool documentation lifts performance further, the comparison would be sweep-5 vs that hypothetical sweep-6 — clean diff, no confound.

---

## 6. Methodology disclosures (for `EXPERIMENTS_FLOW.md` / paper)

These are the disclosures the paper needs to defend the design against reviewer objections. Each goes into `EXPERIMENTS_FLOW.md` under a new "§ Methodology disclosures" section that cross-references this design doc.

### 6.1 BFCL divergence

> *"BFCL (Berkeley Function-Calling Leaderboard) benchmarks function-calling correctness in isolation and does not include a no-tools baseline. We include one because our research question is tool *utility* for symbolic reasoning (the PDDL Copilot paper's headline claim), not function-calling correctness alone. The no-tools arm is therefore additive to BFCL's design, not a divergence from it."*

### 6.2 Fusion novelty

> *"Our three-arm matrix combines two prior methodologies: PDDL Copilot's (tools | no-tools) split and BFCL's within-tools decomposition (relevance / selection / parameter-filling). Neither source endorses the exact 3-arm shape we use. We acknowledge this is a novel combination, motivated by the need to attribute the headline tool-utility claim cleanly while still measuring tool-selection behavior."*

### 6.3 Paraphrase-axis asymmetry

> *"The paraphrase axis (3 per task) varies only the neutral task-framing clause. The steered directive is held byte-identical across the three paraphrases per task. This isolates steering variance from paraphrase variance; varying both would dilute the H2 measurement. The neutral arm's paraphrase axis remains a linguistic-robustness probe for H1."*

### 6.4 VERDICT trailer (post-vLLM-only justification)

> *"The VERDICT trailer in `validate_*` no-tools prompts is an empirical safety belt against `FR_FORMAT_PARSE_FAIL` events on hybrid-architecture models (Qwen3.5/3.6 Mamba hybrid). Sweep-4 dropped the trailer from `validate_*` v5/v6/v7 and observed a regression in `FR_FORMAT_PARSE_FAIL` rates even under vLLM `guided_json` enforcement; sweep-5 restores it. The trailer adds ~6 tokens per trial and serves as a cross-architecture fallback."*

### 6.5 `(no-tools, steered)` control arm

> *"The fourth arm (no-tools, steered) is methodologically valuable as a falsification check on H2 — confirming that the steered directive alone does not move the no-tools floor — but is conceptually a control, not a primary outcome. We report it in a separate Results subsection rather than as a fourth column in the headline 3-arm table."*

### 6.6 Marketplace 1.4.0 effects on `FR_*` taxonomy

> *"Marketplace 1.4.0 (pddl-copilot @ 2850bc4) split the polymorphic `validate_pddl_syntax` into three task-aligned tools whose JSON schemas enforce required arguments. As a result: (a) the previous `FR_VERDICT_MISMATCH` masquerade (model calls validator without `plan`, tool returns the consistency verdict instead of plan verdict) is structurally unreachable; (b) `FR_WRONG_TOOL` is introduced as a distinct failure mode (model called a non-matching validator tool); (c) the `validate_plan` steered directive simplifies to one sentence. Sweep-3/4/4.1 used the polymorphic predecessor and remain comparable only as historical pin-locked snapshots."*

---

## 7. What this doc does NOT decide

- **Statistical analysis details** (Wilson CI implementation, Bonferroni denominator) are pre-registered in §0 but the analyzer skill is the implementation site, not this doc.
- **Cluster-side knobs** (`--max-model-len`, `--time`, GPU class) are set by `cluster-experimenting/`, not here.
- **Marketplace tool descriptions** live in `../pddl-copilot/`; PR-52 raised the quality bar there and this sweep pins to that result.
- **Sweep-6 (if any)** is not designed here. If `H2` shows steering effect, sweep-6 might ablate the SKILL-inlining variant we deferred from sweep-5. That's a separate design discussion.
