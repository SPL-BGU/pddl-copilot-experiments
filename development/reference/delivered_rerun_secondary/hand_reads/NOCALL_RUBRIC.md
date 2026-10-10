# Hand-read rubric: Gemma no-call answers on validate_plan (delivered rerun, prereg §6)

Each packet is one trial in which Gemma was asked whether a plan is valid for a PDDL
problem. A plan-validation tool was available, but Gemma did **not** call it and answered
in prose instead. `final_answer` is the full answer. `correct_verdict` is the true answer
(VALID or INVALID). `mechanical` holds what the automatic grader extracted: the
`parsed_verdict`, and `ends_in_verdict`, which is true when the last verdict phrase starts
within the final 400 characters.

Read each answer in full and record:

- `ends_in_verdict`: yes / no. Does the answer end with a clear final verdict on the plan
  (VALID or INVALID, in any wording)?
- `verdict`: VALID / INVALID / none. Your own reading of the final verdict.
- `matches_mechanical`: yes / no. Does your verdict equal `mechanical.parsed_verdict`?
  (none against null counts as yes.)
- `right`: yes / no. Does your verdict equal `correct_verdict`? A verdict of none is no.
- `tool_attempt`: yes / no. Does the text try to call a tool, or write out a tool call?
- `mentions_tool`: yes / no. Does the text mention a tool or a validator it could use?
- `method`: one short phrase on how the answer reasons, e.g. "traces every step's
  preconditions", "checks the goal only", "stops partway".
- `note`: anything odd, or empty.

Write a JSON array to the output path you were given, one object per packet, in packet
order, with `id` plus the fields above. Read every packet yourself. Use only the packet
contents; never open other files in the repo.
