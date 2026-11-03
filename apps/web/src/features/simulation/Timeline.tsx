import type { SimulationSession } from "../../lib/api";

export function Timeline({
  session,
  onFork,
  pending,
}: {
  session: SimulationSession;
  onFork: (index: number) => void;
  pending: boolean;
}) {
  const nodes = session.result.input_snapshot.graph.nodes;
  return (
    <aside className="panel timeline-panel">
      <header className="panel-heading">
        <h2>Event history</h2>
        <span className="badge">{session.events.length} events</span>
      </header>
      <ol className="timeline-list">
        {session.events.map((event) => {
          const node = nodes.find((node) => node.id === event.node_id);
          const selected = node?.choices.find(
            (choice) => choice.id === event.payload.selected_choice_id,
          );
          const labels = {
            node_entered: "Step reached",
            inject_applied: "Scenario facts updated",
            decision_evaluated:
              event.payload.result === "uncovered"
                ? "No matching path"
                : event.payload.result === "overlap"
                  ? "Multiple matching paths"
                  : "Conditions evaluated",
            decision_selected: selected?.label ?? "Choice recorded",
            deviation_recorded: "Deviation recorded",
            run_terminated: "Run stopped",
          };
          return (
            <li
              key={event.id}
              className={
                event.event_type === "deviation_recorded"
                  ? "timeline-deviation"
                  : ""
              }
            >
              <span className="event-number">
                {String(event.sequence + 1).padStart(2, "0")}
              </span>
              <div>
                <strong>{labels[event.event_type]}</strong>
                <span>{node?.label ?? event.node_id}</span>
                {event.event_type === "decision_evaluated" && (
                  <button
                    className="text-action"
                    disabled={pending}
                    onClick={() => onFork(event.sequence)}
                    aria-label={`Fork before ${node?.label ?? event.node_id}`}
                  >
                    Fork here ↗
                  </button>
                )}
              </div>
            </li>
          );
        })}
      </ol>
      <p className="timeline-note">
        Forks preserve the parent and keep its pinned procedure. They do not
        change policy.
      </p>
    </aside>
  );
}
