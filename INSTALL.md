# Install — set up the vault, skills, and your agent

Setup is once per environment. The knowledge base itself is just the markdown in
`knowledge-base/`; "installing" means pointing your agent at it and (optionally)
connecting sources.

## What's in the box

```
portable-cross-agent-second-brain-personal/
  CLAUDE.md            # Claude entry point (rules, routing map, where the vault is)
  AGENTS.md            # Codex + Cursor entry point (same rules, in parity)
  knowledge-base/      # the 7 notes — your actual memory
  _inbox/              # drop raw material here
  skills/ingest/       # capture new material -> knowledge-base/ (directly)
  skills/curate/       # weekly health check
  index.html           # open in a browser to read the vault
  INSTALL.md           # this file
  README.md
```

## 1. Fill the vault

Either edit the seven notes in `knowledge-base/` by hand, or let the AI do it:
drop source material in `_inbox/` and run the **ingest** skill — in this Personal
edition it writes notes **directly** into `knowledge-base/` (no approval queue,
because you're the only user), and you edit or prune in place.

## 2. Point your agent at it

**Claude (Cowork):** select this folder, and paste `CLAUDE.md` into the folder's
instructions. Connect sources (email, calendar, Drive) from the `+` → Connectors
if you want automatic ingest. Upload `skills/ingest` and `skills/curate` as
skills.

**Claude Code:** just open this folder. Claude Code reads `CLAUDE.md` and the
`skills/` folder from disk automatically.

**Codex:** open this folder. Codex reads `AGENTS.md` from the root.

**Cursor:** open this folder. Cursor reads root `AGENTS.md` natively — no
`.cursor/rules` file needed. (You can still add one later if you want
Cursor-specific behavior.)

Because Claude reads `CLAUDE.md` and Codex + Cursor read `AGENTS.md`, the same
vault behaves identically in all three. Keep the two files in parity if you edit
the rules.

## 3. Keep it current

- Run **ingest** whenever new material shows up — it writes straight into
  `knowledge-base/`.
- Run **curate** weekly (schedule it in Cowork, or invoke it on a cadence in
  Codex/Cursor).
- Edit or prune notes whenever you like. There's no approval queue — the
  protection is traceability (every fact carries its source and status).

## 4. Prove it works

Ask your agent for one real task — a follow-up email, a meeting prep, a brief —
using only the vault. Then ask the same thing in a blank AI with no vault. The
difference is the whole point.
