import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Link,
  useNavigate,
  useParams,
  useSearchParams,
} from "react-router-dom";
import { simulationApi, workspaceApi } from "../lib/api";
import { Button } from "../components/ui/button";
import { Comparison } from "../features/reports/Comparison";
import { factLabel } from "../features/simulation/presentation";

export function ReplayLab() {
  const { sessionId = "" } = useParams();
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const cache = useQueryClient();
  const [verification, setVerification] = useState<string>();
  const query = useQuery({
    queryKey: ["session", sessionId],
    queryFn: () => simulationApi.session(sessionId),
    staleTime: 0,
  });
  const runs = useQuery({
    queryKey: ["replay-runs"],
    queryFn: () => workspaceApi.library("", 0, 50),
    staleTime: 0,
  });
  const fork = useMutation({
    mutationFn: (index: number) => simulationApi.fork(sessionId, index),
    onSuccess: (child) => {
      cache.setQueryData(["session", child.id], child);
      void cache.invalidateQueries({ queryKey: ["library"] });
      void cache.invalidateQueries({ queryKey: ["replay-runs"] });
      void cache.invalidateQueries({ queryKey: ["incident-branches"] });
      navigate(`/simulation/${child.id}`);
    },
  });
  const replay = useMutation({
    mutationFn: () => simulationApi.replay(sessionId),
    onSuccess: (result) =>
      setVerification(`${result.session_id}:${result.last_state_hash}`),
  });
  if (query.isPending)
    return (
      <p className="message" role="status">
        Loading the pinned timeline…
      </p>
    );
  if (!query.data)
    return (
      <section className="message" role="alert">
        <h1>Replay unavailable</h1>
        <p>{query.error?.message}</p>
        <Button onClick={() => void query.refetch()}>Retry</Button>
      </section>
    );
  const session = query.data;
  const requested = Number(params.get("event"));
  const defaultIndex =
    [...session.events]
      .reverse()
      .find((event) => event.event_type === "decision_evaluated")?.sequence ??
    0;
  const index =
    params.has("event") &&
    Number.isInteger(requested) &&
    requested >= 0 &&
    requested < session.events.length
      ? requested
      : Math.max(0, defaultIndex);
  const event = session.events[index];
  const node = session.result.input_snapshot.graph.nodes.find(
    (node) => node.id === event.node_id,
  );
  const right = params.get("compare") ?? session.id;
  const left = params.get("left") ?? session.parent_session_id ?? session.id;
  const compare = left !== right;
  const allOptions = [
    { id: session.id, scenario_title: session.result.scenario_title },
    ...(runs.data?.sessions ?? []).map((run) => ({
      id: run.id,
      scenario_title: run.scenario_title,
    })),
    { id: left, scenario_title: "Selected run A" },
    { id: right, scenario_title: "Selected run B" },
  ];
  const options = allOptions.filter(
    (run, index) =>
      allOptions.findIndex((other) => other.id === run.id) === index,
  );
  return (
    <section className="replay-page">
      <header className="library-heading">
        <div>
          <span className="eyebrow">Replay Lab / Pinned event history</span>
          <h1>Rewind. Branch. Compare.</h1>
          <p>
            {session.result.scenario_title} · {session.events.length} stored
            events
          </p>
        </div>
        <div className="session-actions">
          <Button
            variant="outline"
            disabled={replay.isPending}
            onClick={() => replay.mutate()}
          >
            Verify replay
          </Button>
          <Link to={`/simulation/${session.id}`}>Open rehearsal</Link>
        </div>
      </header>
      {verification ===
        `${session.id}:${session.events.at(-1)?.state_hash}` && (
        <p className="verification" role="status">
          Pinned inputs reproduce the stored history.
        </p>
      )}
      {(fork.error ?? replay.error) && (
        <p role="alert">{(fork.error ?? replay.error)?.message}</p>
      )}
      <section className="panel report-section">
        <label htmlFor="replay-scrubber">Event checkpoint</label>
        <input
          id="replay-scrubber"
          className="replay-scrubber"
          type="range"
          min={0}
          max={session.events.length - 1}
          value={index}
          aria-valuetext={`Event ${index + 1}: ${event.event_type.replaceAll("_", " ")} at ${node?.label ?? event.node_id}`}
          onChange={(event) =>
            setParams((previous) => {
              const next = new URLSearchParams(previous);
              next.set("event", event.target.value);
              return next;
            })
          }
        />
        <label htmlFor="replay-event">Jump to an event</label>
        <select
          id="replay-event"
          value={index}
          onChange={(event) =>
            setParams((previous) => {
              const next = new URLSearchParams(previous);
              next.set("event", event.target.value);
              return next;
            })
          }
        >
          {session.events.map((event) => (
            <option key={event.sequence} value={event.sequence}>
              {event.sequence + 1}. {event.event_type.replaceAll("_", " ")} —{" "}
              {
                session.result.input_snapshot.graph.nodes.find(
                  (node) => node.id === event.node_id,
                )?.label
              }
            </option>
          ))}
        </select>
        <div className="replay-checkpoint">
          <div>
            <span className="badge">
              Event {index + 1} / {session.events.length}
            </span>
            <h2>{node?.label}</h2>
            <p>{event.event_type.replaceAll("_", " ")}</p>
            <dl className="report-metadata">
              {Object.entries(event.facts_snapshot).map(([field, value]) => (
                <div key={field}>
                  <dt>{factLabel(field)}</dt>
                  <dd>{String(value)}</dd>
                </div>
              ))}
            </dl>
          </div>
          <div>
            <Button
              disabled={
                event.event_type !== "decision_evaluated" || fork.isPending
              }
              onClick={() => fork.mutate(index)}
            >
              {fork.isPending
                ? "Creating branch…"
                : "Fork before this decision"}
            </Button>
            <p className="muted">
              Fork only at a stored decision checkpoint. The parent and its
              policy stay intact. A gap remains a gap until a separate proposal
              changes the modeled policy.
            </p>
            <p className="hash-value">Stored hash: {event.state_hash}</p>
          </div>
        </div>
      </section>
      <section className="panel report-section no-print">
        <h2>Compare recorded runs</h2>
        {runs.isPending && <p role="status">Loading saved runs…</p>}
        {runs.error && (
          <p role="alert">
            Saved runs could not load: {runs.error.message}{" "}
            <button className="text-action" onClick={() => void runs.refetch()}>
              Retry saved runs
            </button>
          </p>
        )}
        <p className="muted">
          For a changed-policy comparison, select the originating run as A and
          its linked proposal rehearsal as B.
        </p>
        <div className="comparison-selectors">
          <label>
            Run A
            <select
              value={left}
              onChange={(event) =>
                setParams((previous) => {
                  const next = new URLSearchParams(previous);
                  next.set("left", event.target.value);
                  return next;
                })
              }
            >
              {options.map((run) => (
                <option value={run.id} key={run.id}>
                  {run.scenario_title} · {run.id.slice(0, 8)}
                </option>
              ))}
            </select>
          </label>
          <label>
            Run B
            <select
              value={right}
              onChange={(event) =>
                setParams((previous) => {
                  const next = new URLSearchParams(previous);
                  next.set("compare", event.target.value);
                  return next;
                })
              }
            >
              {options.map((run) => (
                <option value={run.id} key={run.id}>
                  {run.scenario_title} · {run.id.slice(0, 8)}
                </option>
              ))}
            </select>
          </label>
        </div>
        {!compare && <p>Choose a different run to compare.</p>}
      </section>
      {compare && (
        <Comparison
          parentId={left}
          alternateId={right}
          title="Recorded run comparison"
          columns={["Run A", "Run B"]}
        />
      )}
    </section>
  );
}
