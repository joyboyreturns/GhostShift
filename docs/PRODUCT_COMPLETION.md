# Local product completion — Milestone 6

November 3, 2026. Codex-authored implementation around the existing, unchanged Kiro/Codex engine.
The user excluded deployment. No hosting changes or further Kiro model sessions were performed.

## What works

| Workflow | Real implementation |
| --- | --- |
| Bring a procedure | Text/Markdown import and digitally generated PDF text extraction; immutable source viewer with stable sections, Unicode offsets, page citations and content hashes. |
| Model and review | API-loaded graph, decision/choice/condition/evidence editing, action steps, explicit step removal with replacement, hash-bound human review, immutable revisions and version-family history. |
| Author a scenario | Typed facts and ordered changes before named steps; fictional-data acknowledgement; saved scenarios use the same engine as both seeded fixtures. |
| Rehearse | Real choices, injected facts, missing/overlapping paths, deviations, durable events, revision concurrency and source inspection. |
| Find saved work | Searchable, paginated workspace library for sources, models, scenarios and sessions; resume saved runs after reload. |
| Replay and fork | Dedicated Replay Lab with keyboard-operable event selection, saved facts/hashes, real checkpoint forks, verified replay and compatible-run comparison. |
| Test a policy proposal | Saved explicitly unapproved proposals, changed-policy rehearsals and comparison with the preserved parent. |
| Keep results | Session and comparison JSON exports with quoted evidence, replay inputs, logical events and captured approval provenance; printable reports. |
| Learn the workflow | Linked six-step Getting started guide; visible fictional/draft/authority status. |

Earlier milestones implemented the deterministic engine and public-demo isolation/limits/retention.
M6 completes the missing local authoring/discovery/replay/export paths. It does not make this a
published submission or certify source semantics. A human must review whether each condition and
citation accurately represents the procedure. Draft fixture rules remain drafts.

## Walk through your own procedure

1. Run `make dev` from the repository root and open http://localhost:5173.
2. Open **Import**, paste text/Markdown or choose **Upload PDF**, and save it.
3. Choose **Model decision rules**. Add decision/action steps, choices, conditions, destinations
   and actual source citations. Save a new draft version. Server validation checks the whole graph.
4. Choose **Create scenario** on the model. Enter typed facts and optional changes before steps.
   Confirm fictional rehearsal data and save. Acknowledge draft status before starting a draft run.
5. Make choices in Simulation Room. At a gap/overlap, inspect the source and save a proposal if useful.
6. Open **Replay Lab** to select a recorded event, inspect its facts/hash, fork a decision checkpoint,
   verify replay or compare compatible runs. Open the comparison report to print or export both runs.
7. Return through **Library**. **Version history** shows related source/model revisions and branches.

Approval is optional for a draft rehearsal, but always explicit. Proposal snapshots cannot silently
become approved. A completed experiment is not a policy approval. Reviewer names are local
attestations; there is no authentication system.

## API and persistence additions

- `GET /api/library?q=&offset=&limit=` returns bounded summaries and per-category totals.
  Search treats wildcard characters literally; default page size is 24, maximum 50.
- `GET /api/documents/{id}/models` lists up to 50 latest models for an immutable source.
- `GET /api/playbooks/{id}/history` traverses the actual version family, including source revisions
  and branches. Unrelated models are excluded. Families over 200 entries require narrower handling;
  corrupt/cyclic ancestry returns a visible error.
- `POST /api/scenarios` stores a real immutable scenario linked to a validated model. It accepts
  up to 64 distinct finite scalar facts across the scenario and up to 20 scheduled changes. Names
  are bounded to 100 characters, text values to 500, and inject targets must exist. Seeds are
  nonnegative 32-bit integers. Client-provided authority and scenario IDs are rejected.
- `POST /api/documents/pdf` accepts `{title, pdf_base64}` under the existing bounded JSON request
  path. Ordinary text import cannot supply PDF metadata.
- Existing session/report/comparison endpoints now include portable evidence and provenance.

Migration **0004_pdf_evidence** adds nullable original-file hash/page-count/blank-page metadata to
sources and page numbers to segments. Existing records and immutability guards are retained.
`make seed` applies migrations explicitly; startup does not create tables. Scenario persistence
already existed, so custom scenario creation needs no additional table.

SQLite timestamps are serialized with explicit UTC offsets. UI dates convert to local time; no
engine hash or stored logical event is altered by that presentation fix.

## PDF limits and evidence meaning

The locked parser is pypdf **6.21.4**. Supported uploads are unencrypted text-based PDFs, at most
256 KiB, 20 pages and 100,000 extracted characters. Scans/OCR and encrypted PDFs are rejected.
Empty-text pages are reported. Extraction/reading order needs human checking, especially for
columns, tables, missing fonts and mixed scanned/text documents.

Extraction runs in a separate application subprocess, with one parser at a time, a five-second
wall timeout, a three-second CPU limit and bounded parser streams/recovery. Linux additionally
uses a 256 MiB address-space limit; macOS does not reliably enforce this limit and no equivalent
memory guarantee is claimed for native development. This is process isolation, not an OS sandbox
or a comprehensive security audit. Parser diagnostics containing source data are not returned or
logged by the application. Failed imports do not create source records.

Only extracted text and provenance are stored. The original PDF binary is not retained. Its
SHA-256 identifies the uploaded file; the content hash identifies extracted text. Page citations
and Unicode offsets locate the stored text, not PDF screen coordinates. New imports intentionally
receive new source reference namespaces. Check source correctness before approving rules.

## Portable reports

Exports contain the pinned playbook/version, scenario/seed, source title/text hash and optional PDF
file hash; every source segment cited by the modeled graph, including unvisited choices; actual
choices/findings/final facts; full typed replay input; durable logical events; and the human review
record only when the run captured approved authority. A later approval does not relabel old draft
runs. For approved runs, missing or mismatched review provenance is rejected rather than invented.

The awaiting-decision marker remains response-only, following the existing ledger convention.
JSON contains the durable event ledger. It supplies reproducibility inputs for the engine; there
is no new standalone offline replay viewer. Public temporary workspaces still expire: export
before expiry if you need to retain results.

## Validation and remaining scope

See [VALIDATION.md](VALIDATION.md) for executed commands and results. The new browser tests cover
own-procedure authoring/scenarios/library recovery, actual PDF upload/provenance, action-step
revision/removal, Replay Lab checkpoint forks, and evidence-complete comparison downloads.

No AI extraction or AI scenario suggestions were added: the active development rules exclude an
LLM dependency, and the default workflow needs no paid API. P2 multiplayer, team collaboration,
advanced visual scenario authoring and external integrations remain optional and unimplemented.
Excluded enterprise authentication, OCR and live emergency decision-making are not product gaps
for this MVP. No Kiro hooks or extra sessions were manufactured.

Deployment and public publication are intentionally excluded from this pass. Target-server Docker,
HTTPS, volumes, public repository and video submission remain external acceptance work. The
existing three-minute demo script, MIT license and truthful Kiro evidence are available locally.
