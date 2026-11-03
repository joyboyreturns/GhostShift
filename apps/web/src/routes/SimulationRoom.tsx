import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "react-router-dom";
import { FileText, GitBranch, RotateCcw, ShieldCheck } from "lucide-react";
import { simulationApi } from "../lib/api";
import { Button } from "../components/ui/button";
import { Evidence } from "../features/simulation/Evidence";
import { Timeline } from "../features/simulation/Timeline";
import {
  factLabel,
  statusLabels,
  operatorLabels,
} from "../features/simulation/presentation";
import { ProposalForm } from "../features/policy/ProposalForm";
import { Comparison } from "../features/reports/Comparison";

export function SimulationRoom() {
  const { sessionId = "" } = useParams();
  const navigate = useNavigate();
  const cache = useQueryClient();
  const [comparisonId, setComparisonId] = useState<string>();
  const query = useQuery({
    queryKey: ["session", sessionId],
    queryFn: () => simulationApi.session(sessionId),
    staleTime: 0,
  });
  const choose = useMutation({
    mutationFn: ({
      choiceId,
      revision,
    }: {
      choiceId: string;
      revision: number;
    }) => simulationApi.choose(sessionId, choiceId, revision),
    onSuccess: (session) => {
      cache.setQueryData(["session", sessionId], session);
      void cache.invalidateQueries({ queryKey: ["report", sessionId] });
      void cache.invalidateQueries({ queryKey: ["compare"] });
    },
    onError: () => {
      void query.refetch();
    },
  });
  const fork = useMutation({
    mutationFn: (index: number) => simulationApi.fork(sessionId, index),
    onSuccess: (session) => {
      cache.setQueryData(["session", session.id], session);
      choose.reset();
      replay.reset();
      navigate(`/simulation/${session.id}`);
    },
  });
  const replay = useMutation({
    mutationFn: () => simulationApi.replay(sessionId),
  });
  if (query.isPending)
    return (
      <section className="message" role="status">
        Restoring your rehearsal and event history…
      </section>
    );
  if (query.error)
    return (
      <section className="message" role="alert">
        <h1>Run unavailable</h1>
        <p>{query.error.message}</p>
        <Button onClick={() => void query.refetch()}>Retry</Button>
        <Link to="/simulation">Choose another scenario</Link>
      </section>
    );
  const session = query.data;
  const result = session.result;
  const node = result.input_snapshot.graph.nodes.find(
    (node) => node.id === session.current_node_id,
  );
  const checkpoint = result.checkpoint;
  const refs = [
    ...new Set([
      ...(node?.source_refs ?? []),
      ...(node?.choices.flatMap((choice) => choice.source_refs) ?? []),
    ]),
  ];
  const stopped = session.status !== "awaiting_decision";
  const problem =
    session.status === "uncovered" || session.status === "overlap";
  const mutationError = choose.error ?? fork.error ?? replay.error;
  const verified =
    replay.data?.session_id === session.id &&
    replay.data.last_state_hash === session.events.at(-1)?.state_hash;
  return (
    <div className="simulation-page">
      <section className="simulation-heading">
        <div>
          <div className="eyebrow">Simulation Room / Fictional rehearsal</div>
          <h1>{result.scenario_title}</h1>
          <p className="muted">
            A source-linked rehearsal. The original procedure remains unchanged.
          </p>
        </div>
        <div className="session-actions">
          <Button asChild variant="outline">
            <Link to={`/replay/${session.id}`}>Replay Lab</Link>
          </Button>
          <Button
            variant="outline"
            disabled={replay.isPending}
            onClick={() => replay.mutate()}
          >
            <RotateCcw size={16} />
            {replay.isPending ? "Verifying…" : "Verify replay"}
          </Button>
          <Button asChild>
            <Link to={`/simulation/${session.id}/report`}>
              <FileText size={16} />
              Session report
            </Link>
          </Button>
        </div>
      </section>
      <div className="session-strip">
        <span className="badge amber">
          {result.playbook_authority === "draft"
            ? "Unapproved model rehearsal"
            : "Reviewed playbook rehearsal"}
        </span>
        <span>
          Revision {session.revision} · {session.events.length} stored events
        </span>
        <span className="session-id">Run {session.id.slice(0, 8)}</span>
      </div>
      {verified && (
        <p className="verification" role="status">
          <ShieldCheck size={16} />
          Replay verified against pinned inputs · {
            replay.data?.event_count
          }{" "}
          stored events
        </p>
      )}
      {mutationError && (
        <p className="action-error" role="alert">
          {mutationError.message} Your stored history is preserved.
        </p>
      )}
      {session.parent_session_id && (
        <div className="fork-banner">
          <GitBranch size={17} />
          <span>
            {session.proposal_id
              ? "Unapproved proposed-policy rehearsal. History was recomputed."
              : "Alternate run from a saved checkpoint."}
          </span>
          <Link to={`/simulation/${session.parent_session_id}`}>
            Open parent
          </Link>
          <button
            className="text-action"
            onClick={() => setComparisonId(session.id)}
          >
            Compare with parent
          </button>
        </div>
      )}
      {session.proposal_id && (
        <p className="verification">
          <Link
            to={`/review/${session.playbook_version_id}?scenario=${session.scenario_id}`}
          >
            Inspect proposed rules · approval pending
          </Link>
        </p>
      )}
      <div className="simulation-grid">
        <aside className="panel facts-panel">
          <header className="panel-heading">
            <h2>Current facts</h2>
          </header>
          <dl>
            {Object.entries(result.final_facts).map(([field, value]) => (
              <div key={field}>
                <dt>{factLabel(field)}</dt>
                <dd>{String(value)}</dd>
              </div>
            ))}
          </dl>
          <div className="facts-note">
            <span className="eyebrow">Pinned procedure</span>
            <p>{session.playbook_version_id}</p>
            <Link to={`/studio?playbook=${session.playbook_version_id}`}>
              Inspect Source Studio ↗
            </Link>
            <p className="muted">
              Evidence below uses the exact source cited by this run’s snapshot.
            </p>
          </div>
        </aside>
        <section
          className={`panel decision-panel ${problem ? "decision-warning" : ""}`}
          aria-label="Active decision"
        >
          <span className={`badge ${problem ? "amber" : "mint"}`}>
            {statusLabels[session.status]}
          </span>
          <h2>{node?.label ?? "End of modeled workflow"}</h2>
          {session.status === "uncovered" && (
            <div className="stop-explanation">
              <h3>The procedure has no matching path.</h3>
              <p>
                No modeled choice covers these facts. The rehearsal has stopped
                for human review; it will not invent an authoritative action.
              </p>
              <p className="muted">
                Inspect the conditions and source context below, or fork an
                earlier decision. A fork keeps the same procedure.
              </p>
            </div>
          )}
          {session.status === "overlap" && (
            <div className="stop-explanation">
              <h3>More than one rule matches.</h3>
              <p>
                {checkpoint?.matching_choice_ids.length} modeled choices apply.
                No precedence is established, so the rehearsal has stopped for
                human review.
              </p>
            </div>
          )}
          {session.status === "budget_exceeded" && (
            <p role="alert">
              The traversal limit was reached. History is preserved for review.
            </p>
          )}
          {(session.status === "completed" ||
            session.status === "deviation") && (
            <p>
              The modeled workflow reached its end. Review the decisions,
              evidence and deviations in the session report.
            </p>
          )}
          {session.status === "awaiting_decision" && (
            <p className="muted">
              Choose an action. A nonmatching choice will be recorded as a
              deviation from the model.
            </p>
          )}
          <div className="decision-choices">
            {node?.choices.map((choice) => {
              const outcome = checkpoint?.choice_outcomes.find(
                (outcome) => outcome.choice_id === choice.id,
              );
              return (
                <article
                  className={`decision-choice ${outcome?.matched ? "choice-matches" : ""}`}
                  key={choice.id}
                >
                  <div className="choice-heading">
                    <h3>{choice.label}</h3>
                    <span className={`badge ${outcome?.matched ? "mint" : ""}`}>
                      {outcome?.matched ? "Matches model" : "Does not match"}
                    </span>
                  </div>
                  <ul className="condition-list">
                    {choice.conditions.map((condition, index) => {
                      const diagnostic = outcome?.condition_outcomes[index];
                      return (
                        <li key={index}>
                          <span>
                            {factLabel(condition.field)}{" "}
                            <span className="condition-operator">
                              {operatorLabels[condition.operator]}
                            </span>{" "}
                            {Array.isArray(condition.value)
                              ? condition.value.join(", ")
                              : String(condition.value)}
                          </span>
                          <span
                            className={
                              diagnostic?.result
                                ? "condition-pass"
                                : "condition-fail"
                            }
                          >
                            {diagnostic?.missing_fact
                              ? "Fact missing"
                              : diagnostic?.type_mismatch
                                ? "Incompatible fact"
                                : diagnostic?.result
                                  ? "Matches"
                                  : "Not met"}
                          </span>
                        </li>
                      );
                    })}
                  </ul>
                  <span className="muted">
                    {choice.source_refs.length} source citations · human review{" "}
                    {result.playbook_authority === "draft"
                      ? "pending"
                      : "recorded"}
                  </span>
                  {!stopped && (
                    <Button
                      variant={outcome?.matched ? "default" : "outline"}
                      disabled={choose.isPending}
                      onClick={() =>
                        choose.mutate({
                          choiceId: choice.id,
                          revision: session.revision,
                        })
                      }
                    >
                      {choose.isPending
                        ? "Saving choice…"
                        : outcome?.matched
                          ? `Choose: ${choice.label}`
                          : `Choose as deviation: ${choice.label}`}
                    </Button>
                  )}
                </article>
              );
            })}
          </div>
          {result.deviations.length > 0 && (
            <p className="deviation-notice">
              {result.deviations.length} deviation
              {result.deviations.length === 1 ? "" : "s"} recorded in this run.
            </p>
          )}
        </section>
        <Timeline
          session={session}
          pending={fork.isPending}
          onFork={(index) => fork.mutate(index)}
        />
      </div>
      {session.parent_session_id && comparisonId === session.id && (
        <Comparison
          parentId={session.parent_session_id}
          alternateId={session.id}
        />
      )}
      {problem && (
        <details className="panel report-section">
          <summary>Propose a rule change</summary>
          <ProposalForm key={session.id} session={session} />
        </details>
      )}
      <Evidence
        documentId={session.document_id}
        refs={refs}
        expanded={problem}
      />
      <p className="rehearsal-footnote">{result.rehearsal_notice}</p>
    </div>
  );
}
