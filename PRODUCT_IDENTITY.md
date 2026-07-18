# Memventory Product Identity

Last reviewed: 2026-07-18

## Product definition

**Memventory is portable, evidence-aware working memory for AI.** It gives an
individual or team a small, readable Markdown memory that Claude, Codex, and
Cursor can route, inspect, and maintain without a hosted database or vendor
lock-in.

It is not a promise that AI will remember everything. It is a system for making
the context worth retaining easier to find, verify, and carry between sessions
and tools.

## The problem it solves

| Customer problem | What Memventory changes | Resulting value |
| --- | --- | --- |
| Each new AI session starts with a context reset. | A shared snapshot, decisions, preferences, people, and open loops give agents an orienting source of truth. | Less re-explaining and faster useful work. |
| Important context is scattered across chats, files, and people. | A small note schema and source links turn it into an inspectable working memory. | Decisions and commitments are easier to recover and hand off. |
| Teams cannot tell fact from an AI's plausible guess. | Facts and relationships carry status; Team adds human approval before trusted memory changes. | More confidence using AI for ongoing work. |
| Loading whole folders wastes context and obscures the answer. | Deterministic routing finds the relevant section first; the relationship ledger exposes direct and candidate connections. | More focused prompts and less avoidable context loading. |
| A memory system becomes stranded when the team changes AI tools. | Plain Markdown plus paired agent instructions works across Claude, Codex, and Cursor. | The organization owns its knowledge and can change tools without a migration project. |

## Value propositions

### For an individual

- Keep preferences, decisions, and commitments available without rebuilding
  context every session.
- Know where a remembered claim came from, and whether it is verified or still
  tentative.
- Use whichever supported AI tool is best for the task without splitting your
  working memory.
- Start simple: readable files, local control, and no new system to administer.

### For a team or business

- Preserve operating context across people, projects, and agent sessions.
- Reduce reorientation work in recurring analysis, delivery, and handoffs.
- Make AI-supported memory more governable: sources, fact status, sensitivity,
  and—in the Team edition—an approval boundary.
- Limit unnecessary model context by routing to the smallest relevant evidence
  first, rather than treating every request as a whole-vault prompt.
- Retain control of the knowledge asset in portable files rather than a
  proprietary memory layer.

## Capability proof

Memventory earns its positioning through mechanisms a buyer can inspect:

- **Portable storage:** plain Markdown files remain readable without the product.
- **Cross-agent continuity:** CLAUDE.md and AGENTS.md give supported agents the
  same routing and maintenance rules.
- **Deterministic retrieval:** brain.py ranks heading-level sections locally
  before a model needs to read them.
- **Evidence-aware relationships:** the generated index records extracted
  references separately from inferred similar-content candidates, including
  confidence and shared terms. Use python brain.py --related "<question>" to
  inspect them.
- **Trust controls:** source, status, and sensitivity fields distinguish
  evidence from assumptions; the Team edition adds propose-then-approve.
- **Visible structure:** the local console and constellation map make note
  scope, file types, explicit references, and inferred neighbours inspectable.

## Claim discipline

### Claims we can make now

- “Routes agents to relevant sections before model context is loaded.”
- “The routing and index build use no model calls or model tokens.”
- “Keeps source status and inferred relationships visibly distinct from direct
  evidence.”
- “Runs locally on plain Markdown, with no database or vector store required.”
- “Works across Claude, Codex, and Cursor through portable instruction files.”
- “Can reduce unnecessary context loading when the alternative is repeatedly
  opening or pasting broad vault content.”

### Claims that require a customer measurement

- Any percentage or multiplier for token, cost, time, or productivity savings.
- A specific payback period or ROI.
- “Never forgets,” “always accurate,” “eliminates hallucinations,” or
  “automatically knows everything.”
- A claim that the product replaces knowledge management, governance, or human
  judgment.

Use “can reduce,” “helps preserve,” and “makes easier to verify” until a
measurement supports something stronger.

## Measuring token efficiency honestly

Do not publish a universal multiplier. Measure a real repeated task twice:

1. Record a baseline: the files or context an agent normally opens and the
   platform-reported input tokens, where available.
2. Run the same task using brain.py retrieval and only the returned sections;
   record the actual files opened and input tokens.
3. Repeat across at least five representative tasks, keeping answer quality and
   completion criteria constant.
4. Report the median and range, the corpus size, task type, model/tool, and
   whether initial indexing cost is included.

A defensible claim sounds like: “In this measured workflow, selective routing
reduced median model-input context from X to Y tokens across N repeated tasks.”
It does not compare a compact answer against blindly loading an entire corpus
unless that truly was the normal baseline.

## Messaging backbone

**Primary promise:** Give AI the context that matters—portable, traceable, and
ready when the next session starts.

**Personal edition:** Your working memory, carried across AI tools without a
system to maintain.

**Team edition:** Shared AI context that remains source-aware and approval-safe
as more people and agents contribute.

**Proof line:** Read the notes, inspect the source status, and ask the local
index why two things are connected.

## Product boundaries

Memventory is a working-memory foundation, not a replacement for a document
repository, CRM, data warehouse, legal record system, or human decision-maker.
It deliberately starts with curated context. Connectors, bulk migration, hosted
collaboration, and semantic extraction are optional extensions—not hidden
requirements for the core value.
