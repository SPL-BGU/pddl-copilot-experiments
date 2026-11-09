# Draft: research questions, existing against suggested (OPEN, Omer 2026-11-09)

*Kept open on purpose. Nothing in the tex changes until Omer decides. Existing text copied
from `paper/main.tex` (RQ list after "We organize the evaluation around six research
questions"; scorecard `tab:scorecard`).*

## Existing (tex)

- **RQ1.** On the two file-validation tasks (validate_domain, validate_problem), where the
  unaided model has some competence, does tool availability add value?
- **RQ2.** On solve, can the unaided model find valid plans, and how much does the tool add?
- **RQ3.** On validate_plan, a task the unaided model already does well, does mere
  availability help or hurt, and does steering change the answer?
- **RQ4.** On simulate, can the unaided model produce an exact state trajectory at all?
- **RQ5.** Does the tool's advantage grow with plan length?
- **RQ6.** Does it grow with object count?

Plus the scorecard table (one verdict per RQ).

## Suggested

- **Q0, baseline.** What does the model do alone?
- **Q1, gate 1 (calling).** When does the model call the tool? Across tasks, prompt
  wording, model families, reasoning mode and item kinds.
- **Q2, gate 2 (delivery).** When does the tool's result reach the final answer? Against
  context room and answer form.
- Problem size (plan length, object count, the D5b ladder) is a factor under each, not a
  question of its own. The scorecard is dropped (its verdicts rest on the retired ranges).

> ANSWER (keep existing / take suggested / change):
