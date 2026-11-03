# GhostShift — Product and Engineering Specification v0.1

Authoritative source: the user's Kiroween 2026 build handoff, November 3, 2026.
This checked-in specification preserves its product requirements and milestone boundary.
Competition claims and dates are user-provided planning context, not independently verified here.

**Tagline:** Unit tests for the real-world playbooks nobody reads.
**Category:** Frankenstein. **Target:** Kiroween 2026.
**Planned deadline:** December 4, 2026, 2 PM Pacific.

## Product

Turn static operating procedures into source-linked decision graphs so operations managers,
event coordinators, team leads, and small organizations can rehearse disruptions and expose
missing or conflicting instructions before real incidents. This is a rehearsal and documentation
testing tool. Initial data is fictional event operations and customer support. It is not a live
emergency response system or document chatbot. Do not claim to have invented simulation training.

## Required eventual journey

Explore demo → read numbered source sections → inspect reviewed graph → start late-vendor/rain
scenario → choose actions → inspect source-linked events → stop on uncovered conditions → fork
an earlier decision → propose a clearly unapproved resolution → replay → compare actual outcomes
→ download an after-action report. Every step must work through real API state and the same
engine. No fabricated success or outcome screens.

## Milestones in this implementation

**M0:** repository foundation, React/TypeScript/Vite and FastAPI package management, lint/type/test
configuration, Make targets, Compose, safe environment defaults, conventions, MIT license,
Codex-authored steering, PRD, architecture, reproducible commands.

**M1:** health/catalog, persisted immutable documents and stable source segments, safe declarative
Pydantic graph schemas and graph/evidence validation, text/Markdown import, two fictional fixture
graphs and future scenario inputs, API-driven Source Studio, React Flow interaction, source
highlighting, evidence inspector, responsive navigation, loading/empty/error states, backend tests
and Playwright smoke test. Seeded graphs are drafts. Approval/review interactions belong to the
next source workflow milestone. No simulation implementation in this run.

## Full product priorities

**P0:** landing/demo entry; two complete scenarios; Markdown/text ingestion; stable segmentation;
visual graph; human draft review; validation; deterministic simulation and decision evaluation;
uncovered/overlapping paths; source evidence; append-only history; replay; checkpoint forks;
comparison; actual after-action report; responsive keyboard UI; backend/frontend tests;
one-command setup. Later completion requires Kiro implementation.

**P1:** digital PDF extraction, optional OpenAI-compatible draft extraction/scenario suggestions,
source/rule editing, version history, better export/screenshots, guided onboarding, hosted demo,
truthful Kiro evidence. Default demo requires no AI key.

**P2:** shared rehearsals, collaboration, advanced scenario authoring, document comparison,
operational integrations.

**Excluded:** enterprise multi-tenant authentication, live multiplayer, OCR, generic RAG chatbot,
autonomous policy decisions, workflow marketplace, mobile apps, generic agent frameworks.

## Rules and authority

Node types: start, decision, action, end; stable IDs, labels, source references, valid transitions.
Choices include ID, label, destination, conditions, source references, and cited/uncited evidence.
Conditions: field/operator/value; eq, neq, gt, gte, lt, lte, in; lists of conditions compose with AND.
Never execute arbitrary expressions. Every reference must exist in the associated document.
A valid citation does not prove faithful interpretation. Only explicit human review can approve a
rule. Approved versions never change; edits create versions. Proposals cannot become policy silently.

## Future decision evaluation and replay invariants

Exactly one match is an unambiguous modeled path; zero matches is uncovered; multiple matches is
potential overlap; selecting a nonmatch records a deviation. Do not invent an authoritative answer.
Same version/scenario/seed/decisions → identical logical events. Preserve event order, immutable
approved inputs and parent sessions. Fork only valid checkpoints. Reports separate supported
findings, modeled assumptions, deviations, and unapproved proposals.

## Fixtures

Night Market: escalate delays >=30 minutes; redirect indoors when rain risk >70%; cancellation
requires designated venue manager. Scenario: delay 45, rain risk rises to 85, indoor capacity 0.
No reviewed combined rain/capacity instruction exists. The capacity guard in the draft graph is a
modeled assumption requiring review, not authority established by the weather citation.

Customer Support: refunds within 30 days conflict with promotional purchase exclusion; no
precedence is documented. Same schema and eventual engine must handle both domains.

## Eventual persistence

Document(id,title,content,content_hash,source_type,created_at).
SourceSegment(id,document_id,ordinal,text,start_offset,end_offset).
PlaybookVersion(id,document_id,version,title,status,graph_json,created_at).
Scenario(id,playbook_version_id,title,description,initial_facts_json,injects_json,seed).
SimulationSession(id,scenario_id,playbook_version_id,parent_session_id,fork_event_index,status,
revision,current_node_id,state_json,created_at).
SessionEvent(id,session_id,sequence_number,event_type,payload_json,state_hash,created_at), append-only.
RuleProposal(id,playbook_version_id,target_node_id,proposed_change_json,evidence_status,
review_status,created_at).
Only the first three persistence models are implemented in M1.

## API contract

Prefix /api. Implemented: GET health, GET demo, POST documents, GET documents/{id},
POST playbooks (draft creation + validation), GET playbooks/{id}.
Future: POST playbooks/{id}/approve; POST playbooks/{id}/revisions; GET scenarios/{id};
POST sessions; GET sessions/{id}; POST sessions/{id}/choose with expected revision;
POST sessions/{id}/fork; GET sessions/{id}/report; GET sessions/compare.
Use typed schemas, consistent errors, input limits, optimistic decision concurrency.
No fake endpoints or discarded writes.

## UX and visual identity

Home: document-to-graph hero, Explore demo, Import procedure.
Source Studio: source / interactive graph / condition and evidence inspector. Selection highlights
actual citations. Simulation Room later: facts / current decisions / timeline / evidence drawer.
Replay Lab later: checkpoint selection, fork, alternate choice, deterministic replay, comparison.
Report later: version/scenario, decisions, source-backed decisions, deviations, uncovered paths,
overlaps, proposals, comparisons, JSON and print export.

Deep navy #0B1020; surface #151D30; amber #F4B860 warnings; mint #79E2C0 validated evidence;
coral #FF777D deviations; text #F2F5FA. Sophisticated command center, restrained motion.
Keyboard, focus, reduced motion, contrast, descriptive statuses.

## Reliability and security

Offline-default demo; treat uploaded text as untrusted; enforce size limits; no arbitrary execution;
provider keys server-side only if later added; restricted CORS; public write rate limits and isolation;
cleanup anonymous content; actionable failures preserving input; no source documents in logs;
no private content in public demos. Local foundation must not be mistaken for hardened deployment.

## Tests and final acceptance

M1 tests: import persistence, stable offsets and IDs, fixtures, graph topology, evidence integrity,
immutability, source selection and keyboard smoke tests. Eventual tests: uncovered and overlap
detection, replay determinism, branch isolation, revision conflicts, proposal authority, report
version pinning, Hypothesis-generated small graph/decision sequences, full browser journey.

Full MVP acceptance also requires both scenarios executable without AI, real uncovered path,
replay/parent isolation, actual-event reports, all critical tests passing, fresh documented install,
hosted app, public MIT repository, .kiro artifacts, and real substantial Kiro contributions.

## Kiro requirement

Codex only scaffolds M0/M1. Kiro must substantially implement and review engine, branching,
properties, source evidence workflow, and major UX. Use actual Kiro sessions for requirements,
design, tasks, hooks, tests, and evidence. Never manufacture Kiro usage. The initial .kiro files
are explicitly Codex-authored handoff notes. Keep this directory in Git.

## Implementation progress — November 3, 2026

The original M0/M1 run is complete and verified. A subsequent real Kiro CLI session authored the
M2 engine specs, initial implementation and 60 tests. Codex reviewed/corrected that output locally
and added 22 regressions/property tests. Final checks pass (100 backend, 3 frontend unit, 4 browser).
The core now supports deterministic checkpoints, gap/overlap detection, deviations, injects and
hashed logical history. Persisted sessions/events, approval, replay/fork/report APIs and simulation
UI remain subsequent milestones. See ENGINE_REVIEW.md and kiro-evidence.md. No additional Kiro
model sessions may be started without an explicit user request, to conserve limited credits.

### Milestone 3 integration progress — November 3, 2026

Codex integrated the existing engine into persisted scenarios/sessions and append-only event history,
atomic revision-guarded choices, snapshot replay verification, checkpoint forks, comparison and real
reports. Simulation Room, evidence inspection, JSON export and print layout are working in the web UI.
No new Kiro model calls were used. Policy review/approval/revisions and proposed-rule replay remain
next; public hosting and hardening are not complete. See PERSISTED_REHEARSALS.md.


### Milestone 4 integration progress — November 3, 2026

Codex implemented explicit human review, immutable source/playbook revisions, manual rule modeling,
append-only proposals, and unapproved proposed-policy rehearsal/comparison. The engine is unchanged,
and no additional Kiro calls were made. See POLICY_REVIEW.md and VALIDATION.md. Public-demo write
limits, anonymous isolation/retention, hosting and submission artifacts remain outstanding.


### Milestone 5 integration progress — November 3, 2026

Codex added locally verified public-demo request/write/storage limits, signed isolated temporary
workspaces, retention, clean templates, backup/restore evidence and Caddy deployment configuration.
The production-built browser journey passes locally with separate visitor contexts. No extra Kiro
calls, engine changes or runtime AI services were used. Docker runtime, actual HTTPS hosting, public
repository publication and submission assets remain outstanding; see PUBLIC_DEMO.md/DEPLOYMENT.md.


### Milestone 6 local product completion — November 3, 2026

Codex completed library discovery/search, own-procedure scenarios, source/version history, Replay
Lab, action-step editing/removal, digitally generated PDF import with page/file provenance, linked
onboarding and evidence-complete portable session/comparison exports. See PRODUCT_COMPLETION.md
and VALIDATION.md. Prior milestone progress notes describe their historical boundaries, not current
missing features. The existing Kiro/Codex engine is unchanged, no further Kiro model calls were used,
and deployment was explicitly excluded. Optional AI assistance remains unbuilt under the active
no-LLM dependency constraint; collaboration/integrations remain P2. Full hackathon acceptance still
requires public hosting/repository/video and final submission checks.
