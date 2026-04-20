---
name: development-log
description: Maintain the project's development documentation — `development/CHANGELOG.md` (dated record of framework + sibling-MCP changes) and `development/OPEN_ISSUES.md` (tracked methodology/measurement gaps as `ISS-###`). Trigger whenever the user finishes a non-trivial framework or plugin change, asks to "log/document/record/add to changelog/track as an issue", closes a known issue, or produces a results review that surfaces new methodology gaps. Also trigger before starting new work so the history informs the plan.
disable-model-invocation: true
argument-hint: [what was changed OR what issue was found OR "review"]
---

## Why this skill exists

The harness is a ~4-file research codebase whose correctness depends on methodology consistency across runs. Edits to `run_experiment.py` and to the sibling `../pddl-copilot` plugins can silently shift tool output shapes, scorer behaviour, or reproducibility guarantees. `development/CHANGELOG.md` and `development/OPEN_ISSUES.md` exist so that trail is explicit and future runs can be compared to past ones on solid ground. Keep them accurate and the paper comparisons stay defensible; let them rot and every reviewer conversation restarts from zero.

## When the user's ask is recording a change

1. Read `development/CHANGELOG.md`. Newest entries at top. Check the latest date matches or precedes today's; if a block for today already exists, append a sub-entry rather than duplicating the date header.
2. Draft an entry with this structure (imperative, one source of truth):

```markdown
## YYYY-MM-DD — Short imperative title

**Motivation.** One or two sentences: what problem this solves and what prompted it (a results review, a failing run, user direction). Link evidence (`results/<dir>/summary_*.json`, open-issue ID, etc.).

**Code change — `<path>`** (repeat per repo/file set touched)
- Bullet what changed and what the new contract/behaviour is. Include dual-mode specifications if the change adds a mode (e.g., default vs. `verbose=False`).

**Tests / validation**
- Which test suites ran (`verify.sh`, notebook sanity checks, smoke run) and the pass counts.

**Compatibility**
- What's byte-identical, what's not, which scorer paths were verified unaffected. This is the section reviewers will read.
```

3. Cross-check `development/OPEN_ISSUES.md`. If the change closes or narrows any `ISS-###`, update or move that entry (see "Closing an issue" below). If the change *creates* a new concern worth tracking (but not resolving now), add a fresh `ISS-###` before you commit.
4. Do NOT commit for the user unless they asked you to. Describe what was recorded and wait.

## When the user's ask is logging a new issue

1. Read `development/OPEN_ISSUES.md`. Pick the next `ISS-###` number. Severity legend in the file: **P1** blocks paper-comparable numbers · **P2** distorts interpretation or wastes runtime · **P3** cosmetic / taxonomy. Assign with a short rationale — err on the side of lower severity unless the issue genuinely blocks a result.
2. Add the entry under the matching severity heading using this template:

```markdown
### ISS-### · One-line title
**Source.** Where it came from (results-review date/path, user message, CI log).
**Evidence.** Concrete numbers, file paths, or transcripts that show the problem. Reviewers should be able to reproduce the finding from this line alone.
**Impact.** What's broken or misleading if unfixed, phrased in paper-comparability terms.
**Fix.** Minimal sketch of the fix, including which file(s) would move.
**Files.** Specific code paths the fix would touch.
```

3. Keep the "Priority order for next work" section at the bottom of the file current — reorder only when the ranking actually changes, not every edit.

## Closing an issue

Two valid patterns depending on user preference:
- **Move**: delete the `ISS-###` entry from `OPEN_ISSUES.md` and summarize the resolution inside the CHANGELOG entry that closed it (with a backlink: `Closes ISS-###`).
- **Strike-through**: leave the entry in place with a `**Resolved YYYY-MM-DD (see CHANGELOG):** …` line at the top and remove it from the priority list.

Prefer "move" for tactical issues, "strike-through" for issues whose existence is itself informative for reviewers (e.g., a known non-discriminative metric that was replaced).

## When the user says "review" / no target given

1. Diff git since the most recent CHANGELOG date header. List commits/files that aren't yet reflected.
2. Scan the latest `results/<timestamp>_*` directories for new summary JSONs — any new failure modes, truncation clusters, or schema changes worth an `ISS-###`?
3. Propose a short list of draft entries (changelog additions + new issues) and ask the user which to land. Do not edit the files until the user confirms.

## Writing-style reminders

- Imperative voice, short paragraphs. Reviewers skim; don't bury the contract.
- Always record WHY, not just WHAT — code diffs capture "what" already.
- When describing a schema change, show both shapes (before → after). Ambiguity here costs hours later.
- Use absolute paths or paths-from-repo-root (`plugins/pddl-validator/server/validator_server.py`), never bare filenames, so cross-repo edits are unambiguous.
- Convert relative dates to absolute dates before writing (use the current `currentDate` context).

## Anti-patterns (push back if the user requests them)

- A new `docs/` directory duplicating `development/`. One source of truth.
- Per-change standalone `.md` files in `development/`. The CHANGELOG is the index; do not fragment it.
- Logging routine refactors or typo fixes. Only entries that change behaviour, schema, methodology, or reproducibility belong here.
