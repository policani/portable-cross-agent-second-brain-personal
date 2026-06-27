---
name: ingest
description: Turn new material into knowledge-base notes for a single-user vault. Use when the owner drops files in _inbox/, pastes new material, or says "ingest", "capture this", "add to the knowledge base", or connects a new source (email, calendar, Drive, Notion). Reads sources and existing notes and writes notes directly into knowledge-base/ — no approval queue, because the owner is the only user.
---

# Skill: Ingest new material (single-user, no gate)

Turn new material — from any connected source, not just `_inbox/` — into notes,
written straight into the vault. The owner is the only user, so there is no
approval step; they edit or prune in place.

## Steps

1. **Gather.** Read everything new the owner has connected: `_inbox/` files,
   pasted text, and (if connected) recent email threads, calendar meetings,
   shared Drive/Docs/Notion. Also read the existing `knowledge-base/` notes so
   you know what's already captured.
2. **Extract durable facts only.** Decisions, preferences, commitments, people,
   changed facts. Skip small talk and anything already in the vault.
3. **Map each fact to a note type:** snapshot, key-people, preferences-and-rules,
   project-history, decisions-and-rationale, open-loops, source-links.
4. **Write directly into `knowledge-base/`** — update the right note (or create
   one) with frontmatter: `title`, `source` (always record where it came from),
   `date`, `status: extracted` (or `inferred` if you reasoned it out),
   `sensitivity` (public/internal/confidential/restricted).
5. **Flag conflicts in place.** If a new fact contradicts an existing note, say
   so in the note rather than silently overwriting it.
6. **Clean up.** Once an `_inbox/` item is ingested, remove it or move it to a
   sources archive.

## Rules

- Never write `restricted` material into the vault without explicit approval.
- A fact with no traceable source is `status: inferred`, not `verified`.
- The protection is traceability (source + status), not an approval queue.
