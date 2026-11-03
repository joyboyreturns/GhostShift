# Architecture

Browser → Vite React shell → TanStack Query → Zod API boundary → /api FastAPI routes →
document/playbook/simulation services → SQLAlchemy 2 → SQLite (WAL, FK enforcement).

Python 3.12 is the target runtime. package-lock.json and uv.lock record the resolved dependencies.
Install with npm ci and uv sync --locked. The tested interpreter is Python 3.12.13.
Alembic 0001 owns document/playbook tables and immutability triggers; 0002 adds scenarios, pinned
sessions and append-only event rows with database guards. Startup seeds fixtures
idempotently after migrations; make seed explicitly migrates and seeds. Documents and segments
are immutable in ORM and SQLite. Migration 0003 adds version ancestry, proposal snapshots and
explicit human review records; see POLICY_REVIEW.md.

Segmentation uses blank-line paragraphs without normalizing the original source. Offsets are
Python Unicode code-point offsets, with exclusive end. Stable IDs namespace the immutable
document ID, ordinal, and SHA256 paragraph prefix. Separate imports intentionally receive separate
reference namespaces; content_hash identifies identical bytes. HTML/Markdown is rendered as text,
never injected as HTML. Maximum content is 100,000 characters.

Graph validation checks unique node/choice IDs, start/end cardinality, node transition shape,
destinations, reachability, operand shape, cited status consistency, and document-scoped evidence.
Conditions are data, not executable code. Lists compose with AND. Matching/overlap interpretation
uses the existing Kiro/Codex engine. Cycles are bounded by its configurable step budget.

React Flow receives nodes/edges mapped solely from API graphs. UI layout coordinates are
presentation concerns. Selecting nodes or keyboard shortcut buttons highlights the union of node
and choice citations. The inspector shows both conditions and exact source text. All seeded rules
are drafts. Citation validation does not mean approval or policy correctness.

The flagship weather graph includes a capacity guard as an explicit modeled assumption; its
citation does not establish that assumption. The source states that capacity is unaddressed.
The review workflow requires a human to verify semantic support before approval; the seeded
capacity guard should be corrected in a source/model revision rather than blindly approved.

app/engine/interfaces.py now defines typed run inputs, scenarios, decisions, checkpoints, events,
results and the SimulationEngine Protocol. predicates.py evaluates the safe declarative operators;
interpreter.py implements graph traversal. Kiro authored the initial design/code/tests; Codex made
explicitly attributed review corrections (docs/ENGINE_REVIEW.md).

Default interactive execution returns awaiting_decision until a caller supplies a choice. The
explicit auto_rehearsal mode may traverse one matching choice automatically and records its origin.
Uncovered and overlapping decisions always stop. Both seeded fixtures are drafts; no engine call
approves them. The API derives authority from stored versions; drafts require explicit model-rehearsal consent. Source reference
membership is validated by document/playbook services and fixture loading, then preserved in events.

Facts are strict finite scalars. Injects apply once per target in declared order. Graph/scenario
input is revalidated and copied. Every logical event carries authority, version, mode and diagnostic
context. SHA256 hashing uses canonical JSON and a previous-event hash; the context hash pins graph,
scenario/seed/injects and authority without including future choices. Results retain a full input
snapshot and actual decision-only choice stream, including selection origin, for reproducible reuse.
Generated branch-graph tests verify history, evidence and parent isolation. The seed is pinned but
no randomness is implemented. Cycles have a configurable budget and expose partial history on error.

`make engine-demo` loads both fictional graphs/scenarios and runs the real core, explicitly as draft
automatic rehearsals. The browser instead uses interactive persisted sessions through the simulation
service. Session creation pins graph/scenario/seed/authority; revision-guarded choices append a stable
logical-event prefix atomically. The awaiting pause marker is response-only, while actual terminal
markers stay durable. Reads re-execute and verify state plus ledger within one SQLite snapshot.
Checkpoint forks recreate earlier choices and own their event rows, preserving parents. Comparison
and reports derive actual findings and evidence; cited drafts never count as reviewed support.
See PERSISTED_REHEARSALS.md for M3 transaction design and POLICY_REVIEW.md for the subsequent
hash-bound approval, immutable source revisions, manual rule authoring, proposal rehearsal and
explicit different-policy comparisons. HTTP writes now retry pre-commit SQLite contention with
bounded backoff; an after_commit listener prevents repeating successful writes. Spec folders that contain only placeholders
must not be presented as Kiro-authored implementation evidence.

Local dev uses Vite /api proxy; Compose points it at api:8000. Production plan is static frontend,
Caddy HTTPS, API container and persistent SQLite volume on Ubuntu. Production deployment remains follow-up work. Retention, abuse controls and isolation are now
implemented and locally verified in M5 below.

Primary references consulted: [React Flow](https://reactflow.dev/learn),
[FastAPI request models](https://fastapi.tiangolo.com/tutorial/body/).


M5 public-mode integration: a pure ASGI guard bounds JSON bodies before parsing, admits per-IP
requests/workspaces, and issues signed expiry cookies. A clean, explicit fixture-only template is
copied into a separate database per anonymous visitor. Scoped NullPool connections retain the
original event/replay and evidence services unchanged. POSIX file leases coordinate in-flight
requests and whole-workspace retention; one API process is enforced. Local development continues
to use the original database. No business schema migration or engine changes were needed for this
isolation strategy. The production build is served through Caddy with same-origin API routing.
See PUBLIC_DEMO.md for controls, backups and test evidence; DEPLOYMENT.md for remaining host checks.


M6 local product integration: workspace services expose bounded library summaries, version-family
history and immutable custom scenarios. PDF parsing runs in a bounded subprocess; migration 0004
stores nullable file/page provenance without changing existing source/approval guards. Source text
is segmented before graph modeling, with page numbers preserved in evidence. Report responses now
include cited text, replay input, durable events and pinned review provenance. React routes for
Library, SourceDocument, VersionHistory, ScenarioCreate, ReplayLab and ComparisonReport consume
Zod-validated API data. UI authoring manipulates declarative drafts; all saved graphs are validated
by existing services. No engine changes or deployment changes were needed. See PRODUCT_COMPLETION.md
for limits and data semantics.
