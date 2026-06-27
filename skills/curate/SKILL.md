---
name: curate
description: Weekly health check for a single-user knowledge base. Use when the owner says "curate", "health check", "review the vault", "what's stale", or on a weekly schedule. Reads the notes and sources, then writes a short health report and makes light fixes directly in knowledge-base/ — no approval queue, because the owner is the only user.
---

# Skill: Curate (run weekly, single-user)

Keep the vault healthy. Read `knowledge-base/` and the sources, produce a short
health report, and make light fixes directly (the owner is the only user, so
there is no approval queue). Leave anything judgment-heavy for the owner.

## Report and fix

- Recent source activity (new emails, meetings, docs, `_inbox/` drops) that was
  never ingested.
- Stale notes (past their review date, or outdated by newer notes).
- Contradictions (two notes that disagree) — flag them in the notes.
- Open loops with no recent activity.
- Facts with no source, or still marked `inferred`.
- Gaps the owner clearly cares about but the vault doesn't cover.

## Output

A short health report (what's healthy, what needs attention). Make small,
safe fixes in place — fixing a stale date, adding a missing source, marking a
confirmed fact `verified`. Leave merges, deletions, and contested calls for the
owner to make.

## Schedule it

- **Claude Cowork / Code:** run on a weekly scheduled task, or just ask "curate"
  weekly.
- **Codex / Cursor:** invoke the skill weekly, or wire it into your own cron/task
  runner pointed at this folder.
