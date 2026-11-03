# Engine review — Codex, November 3, 2026

Kiro CLI session `8b21a265-5723-4164-92b7-d17d990e23bc` authored the initial engine specification,
contracts, predicates, interpreter and 60 engine tests. It fixed a deviation-status overwrite found
by its own tests. The provider then throttled the session, which exited with code 1 before final
verification and evidence documentation. The actual CLI transcript and launcher metadata are in
.kiro/evidence/. This was one implementation session, not a claim of one inference request or a
known credit cost. No further Kiro model calls were made after the user's credit-conservation request.

Codex independently ran the initial output: all 78 backend tests passed, but formatting and strict
mypy still failed. Passing tests did not establish completion. Direct review experiments reproduced
the following problems before local corrections:

| Finding | Observed initial behavior | Local correction by Codex |
| --- | --- | --- |
| Recorded decisions could not reproduce a run | Start/action nodes were included in decisions_made. Feeding this list back into the interpreter changed a deviation into completed and changed the hash history. | Record only actual selected decision choices, retain their selection origin, and reject invalid/unordered/unused choices. |
| User choices were optional without an explicit mode | A supported decision completed automatically when no choice was supplied. | Default interactive mode returns awaiting_decision with a checkpoint. Automatic selection requires explicit auto_rehearsal mode and is recorded as such. |
| Invalid choice streams were silently ignored | A decision targeting a nonexistent node returned completed. | Validate decision targets/IDs before traversal, check visit order, and reject unused trailing choices. Unresolved stops expose remaining decisions. |
| Events lost authority context | None of the returned event objects had a playbook_authority field. | Every event carries version, authority, mode and a hash binding the graph/scenario context. |
| Result was insufficient to reconstruct its inputs | Only scenario title/seed were retained, without initial facts or injects. | Retain a validated, independently owned input_snapshot; JSON round-trip and reuse reproduce the same events. This is not a persisted replay API. |
| Missing/type-mismatched facts lost diagnostics | decision_evaluated retained only result and matching IDs. | Retain condition outcomes, evidence references and mismatch/missing flags in checkpoint and event data. |
| Nonfinite fact values were accepted | Scenario(initial_facts={x: NaN}) succeeded; JSON hashing allowed nonstandard NaN. | Strict finite engine models and canonical JSON with allow_nan=False. |
| Cycle test did not actually revisit its inject target | The initial one-shot inject test completed on first visit. | Added a bounded cycle that revisits a node and verifies exactly one injection plus accessible partial history. |
| Generated tests varied facts, not branch topology | Initial Hypothesis tests used fixed graphs. | Added generated valid branch graphs, predicates, injects and decision sequences with independent outcome, evidence and parent-isolation assertions. |

These corrections and the 22 regression/property tests in tests/test_engine_review.py are
**Codex-authored**, not Kiro-authored. The initial 60 tests remain attributed to Kiro; Codex updated
batch test inputs to explicitly opt into auto_rehearsal and updated hash checks for the new context.
The local fixture demo harness is also Codex-authored. No new Kiro credits were needed for them.

## Final contract

- The engine does not approve playbooks. Authority supplied by a trusted caller is recorded; the
  eventual API must derive it from immutable reviewed records, not from arbitrary browser input.
- Source membership is validated at the source/playbook service boundary and by fixture loading.
  Engine output preserves these citations; a citation alone still does not establish approval.
- Interactive execution pauses before selecting a supported path. Uncovered and overlap always
  stop, even if a caller supplied a choice. No correct policy answer is invented.
- Explicit auto_rehearsal runs may automatically select exactly one modeled match, visibly labeled.
- Conditions are declarative. Missing facts and incompatible types do not match and remain
  inspectable. Booleans are not numeric; finite int/float comparisons are compatible.
- Facts are strict finite scalar values. Context and event JSON are canonical and timestamp-free.
- The context hash pins graph, version, authority, scenario (including seed/injects), and mode.
  It excludes future choices and step budget so identical branch prefixes retain identical hashes.
- The seed is recorded/pinned, with no random behavior in this milestone.
- Run inputs are revalidated and copied. Frozen models own their nested data; their nested lists
  and maps are not intrinsically immutable Python containers. Independent runs do not alias them.
- Budget exhaustion raises TraversalBudgetExceeded with partial_result for diagnostics.

Persisted sessions/events, optimistic concurrency, approval/revisions, fork/replay/report APIs and
simulation UI remain later milestones. The engine core and test-driven reconstruction of a run are
implemented; no endpoint or user-facing workflow is claimed for those future features.
