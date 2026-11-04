# Session 1: Ghost Scan (spec-driven feature)

You are working in the GhostShift repository. Read AGENTS.md, docs/PRD.md, docs/architecture.md,
.kiro/steering/*, .kiro/specs/simulation-engine/*, and services/api/app/engine/ before changing anything.
Follow Kiro's spec workflow: write requirements.md (EARS-style acceptance criteria), then design.md,
then tasks.md under `.kiro/specs/ghost-scan/`, then implement the tasks one at a time and tick them off.
Stop after each phase only if something is ambiguous; otherwise continue.

## Problem
Today a person finds a ghost path (a state where zero or several rules match) only by rehearsing by hand.
Add **Ghost Scan**: an automatic, deterministic exploration of a playbook against a scenario that lists
every reachable ghost path, so a procedure author can run it like a unit test.

## Requirements to cover (refine them in requirements.md)
- Explore the decision graph from the scenario's initial facts, applying the scenario's injects in
  their defined order, using the **existing engine's** evaluation. Do not duplicate predicate logic.
- For every reachable decision state, enumerate each available choice and follow it. Report:
  uncovered states (zero matches), overlap states (several matches), unreachable nodes, and dead ends.
- Each finding carries the node, the facts at that point, the choice path that reaches it, and the source
  references the relevant rules cite (use existing evidence fields; never claim approval).
- Deterministic and bounded: stable ordering, configurable max states/depth with a clear "truncated"
  result, cycle handling, and identical output for identical inputs (include a result hash).
- API: a read-only endpoint under `/api` returning a Pydantic v2 model (e.g. `POST /api/playbooks/{id}/ghost-scan`
  with scenario id in the body, since it computes, does not mutate). Validate IDs against the document.
  No new tables are required; if you think you need one, justify it and add a migration.
- Frontend: a "Scan for ghost paths" panel on an existing page (Studio or Library), data validated with
  Zod, accessible (semantic list, keyboard focus, reduced motion), linking each finding to the source.
  Do not interpret policy in presentation components.
- Tests: example tests plus **Hypothesis property tests** for invariants (determinism, scan findings
  are a subset of states a manual rehearsal can reach, bounds respected, no mutation of the playbook).
  Add one Playwright test of the UI flow against the Night Market fixture (the scan must report the
  known indoor-capacity ghost). Document any bug the property tests reveal.

## Done means
`make lint`, `make typecheck`, `make test` pass; the Night Market scan reports the known uncovered state;
tasks.md is fully updated; list in your final message what you could not finish. Do not fabricate results.
