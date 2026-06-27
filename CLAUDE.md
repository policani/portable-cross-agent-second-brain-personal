# Portable Cross-Agent Second Brain (Personal) — operating guide for Claude

This is your living memory: the owner's solo second brain. Read from it to do
their work in their voice and context, and help keep it current. The owner is the
only user; they read and edit it too.

## Parity note (this is the whole point)

The same rules apply whether you are running in **Claude** (Cowork or Code),
**Codex**, or **Cursor**. Claude reads this `CLAUDE.md`; Codex and Cursor both
read `AGENTS.md`. The two files are kept in parity — same rules, phrased for each
client. If you change an operating rule in one, mirror it in the other. There is
no third file to maintain: Cursor reads `AGENTS.md` natively.

## The notes

The memory lives in `knowledge-base/`:

- `snapshot` — who they are, one-paragraph orientation
- `key-people` — stakeholders, roles, who decides what
- `preferences-and-rules` — how they like things done, and the red lines
- `project-history` — what's happened, in order
- `decisions-and-rationale` — what was decided and why
- `open-loops` — commitments and follow-ups still in the air
- `source-links` — where each fact came from

Each note has frontmatter (`title`, `source`, `date`, `status`, `sensitivity`).
If the notes are not here, they may be in a connected project or a linked
Notion/Drive — ask where the vault lives rather than guessing.

## Find the right note — selective routing (save tokens)

**Do not load the whole vault by default.** Read only the note(s) the task needs.
This is how a plain-markdown brain stays cheap and fast without a vector
database: route to the relevant note instead of dumping everything into context.
Use this map:

- Who someone is, their role, who decides → `key-people`
- Voice, preferences, red lines → `preferences-and-rules`
- What was decided and why → `decisions-and-rationale`
- Commitments / follow-ups in flight → `open-loops`
- What happened, in order → `project-history`
- Where a fact came from → `source-links`
- One-paragraph orientation → `snapshot`

Open several only if the task genuinely spans them; otherwise stop at the one
that fits. As the vault grows, keep this map current — it is the retrieval layer.

## How to use it

- Before answering or drafting, route to and read the relevant note(s). Prefer
  vault facts over assumptions, and reflect `preferences-and-rules` (voice, red
  lines).
- Cite the source note for important claims. A claim with no source is an
  opinion, not memory.

## Keeping it current — direct ingest (no approval gate)

This is a single-user vault, so there is **no propose-then-approve gate**. New
material flows `_inbox/` → ingest → **straight into `knowledge-base/`**. You draft
notes directly; the owner edits or prunes them in place.

- Mark every fact's `status`: `extracted` (from a source) · `inferred` (needs a
  later look) · `verified` (confirmed) · `deprecated` (history only).
- Label `sensitivity`: `public` · `internal` · `confidential` · `restricted`.
  Keep `restricted` material (credentials, personal/legal/medical) out unless
  the owner explicitly approves it.
- Two skills do the ongoing work: `skills/ingest` (capture new material into the
  vault) and `skills/curate` (periodic health check). See `INSTALL.md`.

## What replaces the gate

The protection in a solo vault is **traceability, not approval**. Every fact you
write records its `source` and a `status`. Anything uncertain is marked
`inferred` so it reads as a guess until the owner confirms it, and the weekly
curate pass surfaces unsourced or still-`inferred` facts for cleanup. Don't
silently overwrite an existing note — if a new fact contradicts one, say so in
the note.
