# Hand-read rubric: E4 "needs reading" rows (delivered rerun, prereg §8b item 13)

Each packet is one trial in which the model **called the tool and the tool's result was
correct**, but the model's **final answer** (`final_answer`) was graded wrong by the strict
delivered grader, and the grader's fixed mechanical rules could not say why. Your job is
to read the final answer and say why, using a fixed list of categories.

Packet fields: `task`; `reference` (the correct answer: `correct_verdict` for validate
tasks, `tool_plan` for solve, `oracle_trajectory` for simulate); `tool_calls` (what the
model called and what came back, long results cut); `final_answer` (the full text the
model delivered); `done_reason`; for simulate also `reading_aid`.

`reading_aid` (simulate only) is mechanical: it reads the answer as one JSON step object
per line and compares it with the oracle. `json_step_lines` = how many such lines were
found (0 = the answer is not in that form); `every_step_matches_oracle` = true when every
step's action, true facts and numbers equal the oracle. Use it, but confirm by looking
at the answer: check the form yourself and spot-check at least two steps.

## Category: one per row, first match wins (the order is fixed)

1. **NO_FINAL_ANSWER**: the final answer is empty.
2. **TOOL_INPUT_ERROR**: the tool's own result is wrong because the model changed the
   input when calling it. (Should not occur here: every tool result here was correct.)
3. **SUMMARY_ONLY**: the answer does not restate the result. Prose about the result, or
   a list of changes.
   - simulate: full states are written out for fewer than half of the steps.
   - solve: fewer than half of the plan's actions appear.
   - validate: no final verdict is stated at all.
4. **ABRIDGED**: the result is restated but openly shortened. Steps are skipped, a state
   is replaced by a placeholder ("...", "unchanged", "same as above", "all other facts"),
   or each step lists only what changed.
5. **WRONG_WRAPPER**: the full result is there, but not in the form the grader reads.
   - simulate: every step with its full state, but not as a single JSON array. Examples:
     one JSON object per line, markdown tables, plain code blocks, several JSON objects.
   - solve: every action is present but cannot be extracted.
   - validate: a clear final verdict is stated in a form the parser misses.

   The category is about the form only. Whether the content is right goes in
   `human_correct`.
6. **NUMERIC_OMITTED** (simulate only): every step, actions and facts right, every number
   given is right, but some numeric fluents are missing.
7. **WRONG_FACTS**: the restated content differs from the tool's result: a different
   verdict, a different plan, wrong facts in the states.
8. **OTHER**: none of the above fits. Say why in the note.

## human_correct

Would a careful human grader holding `reference` accept the answer's content as correct?

- **yes**:
  - validate: the stated final verdict equals `correct_verdict`;
  - solve: the plan equals `tool_plan`;
  - simulate: every step's action, true facts and numbers match the oracle (form ignored).
- **no**: it states something that differs, or states nothing.
- **unclear**: you cannot tell. Explain in the note.

For simulate rows that are not JSON per line (markdown tables, prose), compare at least the
first step, one middle step and the last step with the oracle. If those all match and nothing
is visibly missing, answer yes, and say in the note that it was a spot check.

## Output

Write a JSON array to the output path you were given, one object per packet, in packet order:

```json
{"id": "<packet id>", "category": "<one of the 8 names>", "human_correct": "yes|no|unclear",
 "note": "<one short sentence: what the answer does>"}
```

Read every packet yourself. Do not skip any, and do not label packets from their file name
or the aid alone. Use only the packet contents; never open other files in the repo.
