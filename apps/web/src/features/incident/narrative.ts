import type { Facts, SimulationSession } from "../../lib/api";
import { factLabel, statusLabels } from "../simulation/presentation";

export type DemoIdentity = {
  id: string;
  scenario_id: string;
  playbook_id: string;
  document_id: string;
};
export type Story = {
  title: string;
  role: string;
  briefing: string;
  objective: string;
  beats: Record<
    string,
    Partial<Record<SimulationSession["events"][number]["event_type"], string>>
  >;
};

// Authored atmosphere only. Choices, facts and findings always come from the API.
const stories: Record<string, Story> = {
  "night-market": {
    title: "The last dry hour",
    role: "Your role · Night Market operations coordinator",
    briefing:
      "Lanterns are going up. Vendors are arriving. You're coordinating tonight's fictional market, and the procedure is open on your desk.",
    objective:
      "Follow the procedure through a delayed delivery and a weather update. Find where its instructions stop covering the situation.",
    beats: {
      delivery: { node_entered: "A delayed arrival needs your attention" },
      weather: { inject_applied: "The weather picture has changed" },
    },
  },
  "customer-support": {
    title: "One request. Two answers.",
    role: "Your role · Customer support lead",
    briefing:
      "A fictional refund request has reached your desk. Two clauses may apply. Your task is to inspect what the procedure actually establishes.",
    objective:
      "Find the conflicting rules and inspect their sources before testing a proposed change.",
    beats: {},
  },
};

export function storyFor(
  scenarioId: string,
  versionId: string,
  demos: readonly DemoIdentity[],
  documentId?: string,
): Story | undefined {
  const demo = demos.find(
    (entry) =>
      entry.scenario_id === scenarioId &&
      entry.playbook_id === versionId &&
      (documentId === undefined || entry.document_id === documentId),
  );
  return demo ? stories[demo.id] : undefined;
}

export function changedFacts(previous: Facts, next: Facts) {
  return Object.entries(next)
    .filter(
      ([field, value]) =>
        !Object.hasOwn(previous, field) || previous[field] !== value,
    )
    .map(([field, value]) => ({ field, previous: previous[field], value }));
}

export function incidentUpdates(session: SimulationSession, story?: Story) {
  const nodes = session.result.input_snapshot.graph.nodes;
  return session.events.flatMap((event, index) => {
    const node = nodes.find((entry) => entry.id === event.node_id);
    const choice = node?.choices.find(
      (entry) => entry.id === event.payload.selected_choice_id,
    );
    const changes = changedFacts(
      index === 0
        ? session.result.input_snapshot.scenario.initial_facts
        : session.events[index - 1].facts_snapshot,
      event.facts_snapshot,
    );
    let title: string;
    let detail = node?.label ?? event.node_id;
    switch (event.event_type) {
      case "node_entered":
        if (node?.type !== "decision" && node?.type !== "action") return [];
        title = "Procedure checkpoint reached";
        break;
      case "inject_applied":
        title = "Scenario facts updated";
        detail = changes.length
          ? changes
              .map(
                ({ field, previous, value }) =>
                  `${factLabel(field)}: ${previous === undefined ? "not set" : String(previous)} → ${String(value)}`,
              )
              .join(" · ")
          : "Scheduled update recorded; fact values are unchanged.";
        break;
      case "decision_selected":
        title = "Choice recorded";
        detail =
          choice?.label ?? "A choice was recorded in the stored history.";
        break;
      case "decision_evaluated":
        if (event.payload.result === "exact_match") return [];
        title =
          event.payload.result === "uncovered"
            ? "No modeled choice covers these facts"
            : event.payload.result === "overlap"
              ? "Conflicting paths need human review"
              : "Decision evaluated";
        break;
      case "deviation_recorded":
        title = "Deviation recorded";
        detail = "The selected choice did not match the modeled conditions.";
        break;
      case "run_terminated":
        title = "Rehearsal stopped";
        detail = statusLabels[session.status];
        break;
    }
    return [
      {
        id: event.id,
        sequence: event.sequence,
        type: event.event_type,
        title: story?.beats[event.node_id]?.[event.event_type] ?? title,
        detail,
        changes,
      },
    ];
  });
}

type BranchRun = Pick<
  SimulationSession,
  "id" | "parent_session_id" | "playbook_version_id" | "status"
>;
export function relatedBranches(
  current: BranchRun,
  runs: readonly BranchRun[],
) {
  const unique = new Map(runs.map((run) => [run.id, run]));
  unique.set(current.id, current);
  return [...unique.values()].filter(
    (run) =>
      run.id === current.id ||
      run.id === current.parent_session_id ||
      run.parent_session_id === current.id ||
      (current.parent_session_id !== null &&
        run.parent_session_id === current.parent_session_id),
  );
}
