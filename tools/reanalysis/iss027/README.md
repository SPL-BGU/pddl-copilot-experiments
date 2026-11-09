# ISS-027 scope check and the Gemma thinking check (2026-11-09)

Read-only scripts from the 2026-11-09 audit, kept as written (they may hold absolute
paths from the session that ran them). They back the ISS-027 "Scope" paragraph in
`development/OPEN_ISSUES.md` and the 2026-11-09 CHANGELOG correction on Gemma thinking.
Before any figure from them goes into `NUMBERS.md`, clean them into proper
`tools/reanalysis/` scripts with a `--results` argument and a self-check.

- `scan_upper.py`: fixtures with upper-case names.
- `iss027_open.py`, `atcap.py`: re-grade of open-model unaided solve with plans
  lower-cased; answers cut at the 500-character snapshot.
- `replay_tools.py`, `replay_iss024d.py`: replay of stored simulate and validate_plan
  tool calls with the plan lower-cased (output: `replay_out_20261109.txt`).
- `gemma_think.py`: Gemma think-on against think-off on paired keys.
