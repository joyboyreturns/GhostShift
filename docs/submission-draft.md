# GhostShift submission draft

Prepared November 3, 2026. Review and adapt in Devpost; nothing here has been submitted or published
as a submission. Public app and video URLs are intentionally absent until they exist and are verified.

## Pitch

**GhostShift — Find the ghost path before your next shift.**

Unit tests for the real-world playbooks nobody reads.

A procedure can look complete until two ordinary problems happen at once. GhostShift helps event
coordinators and operations leads rehearse that moment, expose the missing instruction, and test a
human-authored change while preserving exactly what the original said and did.

## Inspiration and audience

Teams document their normal process, but an incident rarely arrives one variable at a time. Our
fictional Night Market has a late vendor, rising rain risk and no indoor capacity. Its weather clause
says move indoors. It never explains what to do when indoors is full. That omission is the ghost path.

GhostShift is designed for people maintaining procedures and facilitating tabletop exercises. These
fictional demonstrations illustrate the intended value; we have not measured customer adoption,
real incident reduction or cost savings.

## What it does

Import text, Markdown or a text-based PDF. Model source-linked decision rules and explicitly review
their meaning. Rehearse fictional disruptions through an interactive command room. The deterministic
engine stops at uncovered or conflicting paths and records deviations when someone selects a
nonmatching choice. Inspect the source, fork a checkpoint, or save an unapproved proposal and test it
against the same scenario. Export both histories with quoted evidence and replay inputs.

## Frankenstein combination

GhostShift combines document provenance, declarative rule execution, append-only event history and
branching rehearsal. The unusual connection is treating a human procedure as something inspectable
and testable, then making its failures playable. The source remains a document, the model remains a
human interpretation, and a proposed response remains an experiment until reviewed.

React/TypeScript/Vite and React Flow supply the interface. FastAPI/Pydantic validates the models;
SQLAlchemy/SQLite preserves snapshots and history. PDF extraction retains page/text provenance.
Public-demo mode supplies separate temporary workspaces with quotas and expiry. The running app
requires no external AI service.

## How Kiro was used

One genuine Kiro CLI session authored the initial engine requirements, design and tasks, typed
contracts, deterministic predicate/traversal implementation, and 60 tests. It caught and fixed an
actual deviation-status bug. The session ended on throttling; we do not claim a successful completed
session. Codex independently reviewed and corrected the engine, added regressions, and built the
persistence, policy review, public-demo hardening and incident interface around it.

See [the contribution record](kiro-evidence.md), [review corrections](ENGINE_REVIEW.md), and
[the genuine engine specs](../.kiro/specs/simulation-engine/requirements.md). Initial steering and
placeholder hooks are Codex material; no Kiro hook use or additional sessions are claimed.

## Challenges and learning

A replayable run needs more than a seed: it needs pinned inputs, explicit choice origin, stable
logical event order and authority captured at execution time. A cited rule can still be an unsupported
interpretation. Separating citations, human review and unapproved experiments made the product both
more useful and more honest. See ENGINE_REVIEW.md for the concrete corrections and tests.

## Submission completion

The [official competition overview](https://kiroween.devpost.com/) and
[rules](https://kiroween.devpost.com/rules), checked November 3, list impact, Kiro implementation,
design, innovation and presentation as judging criteria. Plan for a working app URL, public GitHub
repository with license and root `.kiro`, and a public YouTube video under three minutes. The listed
deadline is December 4, 2026, 2 PM Pacific. Recheck all rules and entrant eligibility before submitting.

The [GitHub repository](https://github.com/joyboyreturns/GhostShift) was publicly readable on November 3.
These working-tree changes still require review, commit and publication. Hosting requires the
acceptance checks in DEPLOYMENT.md. Record the demo using demo-script.md, verify the real URLs, and
complete the entrant-only eligibility and final submission steps. Optional blog/social prizes need
separate qualifying published material; no such material is claimed here.
