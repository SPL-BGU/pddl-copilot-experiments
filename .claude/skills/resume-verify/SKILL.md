---
name: resume-verify
description: Resume work from a handoff doc by reconstructing and verifying current state before acting. Use when the user points at a handoff/postmortem/plan doc and says "continue", "resume", or "pick this up".
---

# Resume and verify

Handoff docs describe the state at write time, not now. Before acting on one:

1. Read the handoff doc the user named (or the newest matching `*HANDOFF*.md` / `development/*handoff*` if none named) and list its load-bearing claims: what ran, what's in flight, what's blocked, what's next.
2. Verify each claim against the actual state before trusting it:
   - Git: `git log --oneline -15`, current branch, open PRs (`gh pr list`) — did work land after the doc was written?
   - Results: do the corpora/dirs the doc references exist, and with the expected trial counts? Use canonical sources only (see CLAUDE.md / Data rigor).
   - Jobs: cluster or pod state is verified only via the user — **do not SSH/SLURM without an explicit go-ahead** (their connection isn't always up). Ask, or rely on local synced evidence.
3. Report a short delta: which handoff claims still hold, which are stale, and what that changes about the next step.
4. Before recommending any run/rerun, check whether an equivalent run already exists in results. Never propose rerunning a config a prior pilot already showed fails or is confounded — cite the failed pilot instead.
5. Only then act on the "next steps".

If the handoff conflicts with the repo state, the repo state wins; flag the discrepancy rather than silently following the doc.
