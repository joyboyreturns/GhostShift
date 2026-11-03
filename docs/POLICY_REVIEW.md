# Policy review, source revisions and proposed-policy rehearsal — Milestone 4

Implemented by Codex around the existing, unchanged Kiro/Codex engine. No new Kiro model calls,
LLM dependencies, or fabricated Kiro artifacts were used. This remains a local preview.

## User journeys

**Find a gap and test a proposal:** Explore demo → Rehearse scenario → acknowledge draft rehearsal
→ choose escalation → expand **Propose a rule change**. Enter a reason and use **Add choice for
current facts**, or edit the declarative conditions manually. Enter the proposed action, inspect its
conditions/destination, and save. Acknowledge the proposal is unapproved and rehearse it. Prior user
decisions are reused, every event is recomputed, and the new matching choice still requires a real
user selection. Compare with parent, verify replay, then open the actual-event report. Saved proposals
can be resumed from their report link after reload. The support overlap uses the identical service:
edit the competing conditions to test an explicit precedence proposal.

**Import and model:** Import text/Markdown → Model decision rules → Add decision before completion.
Set the question, actions, fact predicates and destinations; select the actual supporting source
sections. Save a new draft revision. Source Studio loads the saved graph from the API. This is manual
authoring, not automatic extraction. Arbitrary graph topology deletion and scenario authoring are not
implemented. A blank structural start/end draft cannot be approved. Imported procedures do not get
an unrelated demo scenario assigned to them.

**Review:** Source Studio → Review & revise policy. Inspect every condition and exact cited text,
confirm each choice individually, supply reviewer name/notes, and explicitly attest source support
for the entire model. The API requires every choice exactly once and checks the expected graph hash.
Uncited rules, blank models, stale drafts and proposal snapshots cannot be approved. Approval and
its immutable review record commit together. Local reviewer names are attestations, not authenticated
identities. Citation validity and deterministic results cannot prove semantic fidelity to the source.

**Revise:** Create a new revision on the review page. Rules can be edited and decisions inserted
before completion. Revised source text is imported as a new immutable document. Its old citations
are cleared, and the user explicitly selects new evidence before saving. Versions retain a parent
link; their numbers advance even when the source document changes. Approval is never inherited.
Old documents, approved versions, pinned session inputs and event histories remain unchanged.

The fictional weather fixture intentionally models a capacity guard that its source does not
establish. It remains a draft. A reviewer should correct the source/model rather than blindly approve
all citations. Tests that exercise approval use explicit test attestations; they do not certify the
seed fixture's semantic accuracy.

## Persistence and authority

Alembic 0003 adds parent_version_id, append-only RuleProposal snapshots and immutable PlaybookReview
records. ORM guards and SQLite triggers prevent review/proposal edits/deletes; existing approved
playbook guards remain in force. Migration upgrade/downgrade/re-upgrade preserves existing fixture
records and immutability. Tables are never auto-created by app startup.

A proposal pins its originating session, original version, target decision, reason and complete
proposed graph. Only the blocked decision's choice set changes. Changed choices lose old evidence
claims and become uncited; unchanged choices retain their citations without gaining approval. All
submitted evidence references and the resulting topology are validated. Proposal snapshots stay
pending and cannot be approved directly. Create a separate, cited revision and explicitly review it.
The original proposal remains a historical pending artifact even if a descendant version is reviewed.

Proposed-policy rehearsal uses the parent's pinned scenario/seed and actual prior choice stream,
plus the saved proposed graph under **draft** authority. It creates a separate session and ledger.
If a change invalidates the prior decision stream, or the stored proposed draft has changed, the
request fails; no fabricated continuation is returned. Same-policy checkpoint forks retain the M3
prefix invariant. Proposed-policy comparisons require explicit opt-in and a linked proposal plus
identical scenario inputs; they report a different scope and **null shared_event_prefix** because the
event contexts differ. Completion under an assumption never establishes approved policy correctness.

Reports include actual chosen rules, their evidence/authority and saved proposal records. Existing
runs retain the authority captured at their creation even if that version is approved later.

## Write concurrency

HTTP POST adapters use a shared transaction wrapper. A SQLite busy/snapshot failure **before commit**
rolls back and retries the entire operation up to three times with 20/40/80 ms backoff. Revision/hash
checks run again against a fresh snapshot. A SQLAlchemy after_commit listener prevents retrying a
successful write if response verification subsequently fails. Conflicting choices for one revision
still produce one commit and one conflict. Exhausted retries return an actionable error.

This fixes real contention found while independent browser tests wrote different sessions. Regression
tests force an unrelated commit during choice evaluation and a failure after the choice committed.
The latter reports that the write was saved, and proves it was not repeated.

## API additions

- POST /api/documents/{id}/draft — persist an empty structural draft for manual modeling.
- POST /api/playbooks/{id}/revisions — new draft, explicit document/graph, retained parent.
- GET /api/playbooks/{id}/review — actual review record or null.
- POST /api/playbooks/{id}/approve — hash-bound, explicit human source review.
- GET /api/playbooks/{id}/scenarios — compatible scenarios derived from version ancestry.
- POST /api/sessions/{id}/proposals — save a real change at a gap/overlap, expected revision required.
- GET /api/proposals/{id} — restore saved proposal.
- POST /api/proposals/{id}/rehearse — explicit unapproved-model consent required.
- POST /api/sessions additionally accepts a compatible descendant playbook_version_id.
- GET /api/sessions/compare additionally accepts allow_policy_change=true for linked proposals.

## Remaining boundary

Public body/write limits, anonymous data isolation and retention are still required before publishing.
Docker runtime, HTTPS hosting, public repository and submission links remain unverified/unpublished.
No public endpoint is claimed. The implemented review is intentionally local and has no authentication.
