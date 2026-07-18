# Product Improvement Plan

Last updated: 2026-07-18

## Customer-language correction

Do not position this as a team knowledge workflow with the approval gate removed.
Customer language points to a private, low-friction cross-tool AI memory for one
person: notes, decisions, preferences, workflows, project continuity, and local
control.

Use language such as:

- private cross-tool AI memory;
- local-first personal second brain;
- fewer context resets;
- direct ingest with traceability;
- connect notes instead of hoarding them;
- personal preferences and project continuity.

## Product gap

The Personal edition needs a lower-setup public story than the Team edition. It
should demonstrate direct ingest, traceability, cleanup, and single-user
ownership without implying team governance.

## Capability backlog

1. Add a short personal setup walkthrough for one user starting from an empty
   vault.
2. Add examples for direct ingest into `knowledge-base/` with source and status
   fields.
3. Add cleanup guidance for inferred, stale, contradictory, or low-value notes.
4. Add local backup examples for Git, zip snapshots, or sync folders.
5. Cross-link the Team edition only where the approval-gate distinction matters.

## Acceptance criteria

- The product reads as personal, private, and low-friction.
- Direct ingest is balanced by traceability and cleanup guidance.
- Examples do not include private personal data.
- The Personal edition stays clearly distinct from the Team edition.

## Completed foundation — 2026-07-18

- Added a durable relationship ledger to the bundled index: direct references are
  marked extracted; similar-content candidates are marked inferred with a score
  and shared-term explanation. Agents can inspect the result with
  `python brain.py --related "<question>"`.
- Added `PRODUCT_IDENTITY.md` as the shared positioning and claim-discipline
  source of truth for both editions. It defines customer problems, personal and
  business value, product boundaries, and a reproducible token-efficiency
  measurement protocol.
- Replaced unsupported universal savings/payback language in the README with
  evidence-backed mechanism claims.
