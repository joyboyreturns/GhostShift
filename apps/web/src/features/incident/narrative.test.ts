import { describe, expect, it } from "vitest";
import { sessionSchema, type SimulationSession } from "../../lib/api";
import {
  changedFacts,
  incidentUpdates,
  relatedBranches,
  storyFor,
} from "./narrative";

const demos = [
  {
    id: "night-market",
    scenario_id: "night-market",
    playbook_id: "night-market-v1",
    document_id: "night-market",
  },
];
function session(events: SimulationSession["events"] = []): SimulationSession {
  return sessionSchema.parse({
    id: "current",
    scenario_id: "night-market",
    playbook_version_id: "night-market-v1",
    document_id: "night-market",
    parent_session_id: null,
    fork_event_index: null,
    engine_version: "test",
    revision: 0,
    status: "uncovered",
    current_node_id: "weather",
    created_at: "2026-11-03T00:00:00Z",
    proposal_id: null,
    events,
    result: {
      playbook_version_id: "night-market-v1",
      playbook_authority: "draft",
      status: "uncovered",
      scenario_title: "Test",
      scenario_seed: 1,
      final_facts: { rain_risk: 85 },
      deviations: [],
      checkpoint: null,
      rehearsal_notice: "Test",
      decisions_made: [],
      input_snapshot: {
        graph: {
          nodes: [
            {
              id: "weather",
              label: "Weather checkpoint",
              type: "decision",
              source_refs: [],
              choices: [],
              next_node: null,
            },
          ],
        },
        scenario: {
          title: "Test",
          seed: 1,
          initial_facts: { rain_risk: 40 },
          injects: [],
        },
        execution_mode: "interactive",
      },
    },
  });
}
function event(
  sequence: number,
  event_type: SimulationSession["events"][number]["event_type"],
  facts_snapshot = { rain_risk: 40 },
  payload: Record<string, unknown> = {},
): SimulationSession["events"][number] {
  return {
    id: `event-${sequence}`,
    created_at: "2026-11-03T00:00:00Z",
    sequence,
    node_id: "weather",
    event_type,
    playbook_version_id: "night-market-v1",
    playbook_authority: "draft",
    execution_mode: "interactive",
    context_hash: "test-context",
    state_hash: "test-hash",
    payload,
    facts_snapshot,
  };
}

describe("incident presentation boundaries", () => {
  it("only applies authored atmosphere to the catalog's exact scenario, version and document", () => {
    expect(
      storyFor("night-market", "night-market-v1", demos, "night-market")?.title,
    ).toBe("The last dry hour");
    expect(storyFor("night-market", "proposal-v2", demos)).toBeUndefined();
    expect(storyFor("custom", "night-market-v1", demos)).toBeUndefined();
    expect(
      storyFor("night-market", "night-market-v1", demos, "other-source"),
    ).toBeUndefined();
    expect(storyFor("night-market", "night-market-v1", [])).toBeUndefined();
  });
  it("does not reveal future injects and falls back to the actual node label", () => {
    const updates = incidentUpdates(session([event(0, "node_entered")]));
    expect(updates).toHaveLength(1);
    expect(updates[0].detail).toBe("Weather checkpoint");
    expect(JSON.stringify(updates)).not.toContain("85");
  });
  it("reports updates from consecutive snapshots, including zero, false and missing facts", () => {
    expect(
      changedFacts(
        { capacity: 1, open: true },
        { capacity: 0, open: false, rain: 85 },
      ),
    ).toEqual([
      { field: "capacity", previous: 1, value: 0 },
      { field: "open", previous: true, value: false },
      { field: "rain", previous: undefined, value: 85 },
    ]);
    const run = session([
      event(0, "node_entered"),
      event(1, "inject_applied", { rain_risk: 85 }),
      event(
        2,
        "decision_evaluated",
        { rain_risk: 85 },
        { result: "uncovered" },
      ),
    ]);
    const updates = incidentUpdates(
      run,
      storyFor("night-market", "night-market-v1", demos),
    );
    expect(updates[1].title).toBe("The weather picture has changed");
    expect(updates[1].detail).toBe("Rain risk: 40 → 85");
    expect(updates[2].title).toBe("No modeled choice covers these facts");
    expect(run.events[0].facts_snapshot.rain_risk).toBe(40);
  });
  it("keeps an unchanged inject and overlap distinct from an uncovered finding", () => {
    const updates = incidentUpdates(
      session([
        event(0, "inject_applied"),
        event(
          1,
          "decision_evaluated",
          { rain_risk: 40 },
          { result: "overlap" },
        ),
      ]),
    );
    expect(updates[0].detail).toContain("unchanged");
    expect(updates[1].title).toBe("Conflicting paths need human review");
  });
  it("includes only API-linked parents, children and siblings, with current state taking precedence", () => {
    const current = { ...session(), parent_session_id: "parent" };
    const branch = (id: string, parent_session_id: string | null) => ({
      id,
      parent_session_id,
      playbook_version_id: "v1",
      status: "uncovered" as const,
    });
    const related = relatedBranches(current, [
      branch("parent", null),
      branch("sibling", "parent"),
      branch("child", "current"),
      branch("other", null),
      branch("current", "parent"),
    ]);
    expect(related.map((run) => run.id)).toEqual([
      "parent",
      "sibling",
      "child",
      "current",
    ]);
    expect(related.at(-1)?.playbook_version_id).toBe("night-market-v1");
    expect(
      relatedBranches(session(), [branch("unrelated-root", null)]),
    ).toHaveLength(1);
  });
});
