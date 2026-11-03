import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { Download, Printer, ArrowLeft } from "lucide-react";
import { simulationApi } from "../lib/api";
import { Button } from "../components/ui/button";
import { statusLabels } from "../features/simulation/presentation";
import { Evidence } from "../features/simulation/Evidence";

export function SessionReport() {
  const { sessionId = "" } = useParams();
  const query = useQuery({
    queryKey: ["report", sessionId],
    queryFn: () => simulationApi.report(sessionId),
    staleTime: 0,
  });
  if (query.isPending)
    return (
      <section className="message" role="status">
        Building a report from stored events…
      </section>
    );
  if (query.error)
    return (
      <section className="message" role="alert">
        <h1>Report unavailable</h1>
        <p>{query.error.message}</p>
        <Button onClick={() => void query.refetch()}>Retry</Button>
      </section>
    );
  const report = query.data;
  const refs = [
    ...new Set([
      ...report.decisions.flatMap((decision) => decision.source_refs),
      ...report.findings.flatMap((finding) => finding.source_refs),
    ]),
  ];
  return (
    <article className="report-page">
      <div className="report-navigation no-print">
        <Link to={`/simulation/${sessionId}`}>
          <ArrowLeft size={15} />
          Back to rehearsal
        </Link>
        <div className="session-actions">
          <Button asChild variant="outline">
            <a
              href={`/api/sessions/${encodeURIComponent(sessionId)}/report`}
              download={`ghostshift-${sessionId}.json`}
            >
              <Download size={16} />
              Download report JSON
            </a>
          </Button>
          <Button variant="outline" onClick={() => window.print()}>
            <Printer size={16} />
            Print report
          </Button>
        </div>
      </div>
      <span className="eyebrow">
        GhostShift /{" "}
        {report.in_progress
          ? "In-progress session report"
          : "After-action report"}
      </span>
      <h1>{report.scenario_title}</h1>
      <p className="report-outcome">{statusLabels[report.status]}</p>
      <span className="badge amber">
        {report.playbook_authority === "draft"
          ? "Unapproved model rehearsal"
          : "Reviewed playbook rehearsal"}
      </span>
      <p className="muted">
        This report reflects the actual recorded run. Source citations locate
        text; draft citations do not establish reviewed policy support.
      </p>
      <dl className="report-metadata">
        <div>
          <dt>Run</dt>
          <dd>{report.session_id}</dd>
        </div>
        <div>
          <dt>Pinned playbook</dt>
          <dd>{report.playbook_version_id}</dd>
        </div>
        <div>
          <dt>Scenario seed</dt>
          <dd>{report.scenario_seed}</dd>
        </div>
        <div>
          <dt>Revision</dt>
          <dd>{report.revision}</dd>
        </div>
        {report.parent_session_id && (
          <div>
            <dt>Parent run</dt>
            <dd>{report.parent_session_id}</dd>
          </div>
        )}
      </dl>
      {report.approval && (
        <p className="verification">
          Review recorded by {report.approval.reviewer}: {report.approval.notes}
        </p>
      )}
      <div className="report-stats">
        <div>
          <strong>{report.decision_count}</strong>
          <span>Decisions</span>
        </div>
        <div>
          <strong>{report.deviation_count}</strong>
          <span>Deviations</span>
        </div>
        <div>
          <strong>{report.uncovered_count}</strong>
          <span>Uncovered paths</span>
        </div>
        <div>
          <strong>{report.overlap_count}</strong>
          <span>Potential overlaps</span>
        </div>
      </div>
      <section className="panel report-section">
        <h2>Decisions & evidence</h2>
        <p className="muted">
          {report.cited_decision_count} cited decisions ·{" "}
          {report.reviewed_supported_count} reviewed, supported decisions
        </p>
        {report.decisions.length ? (
          <ol className="report-decisions">
            {report.decisions.map((decision, index) => (
              <li key={`${decision.node_id}-${index}`}>
                <div>
                  <strong>{decision.choice_label}</strong>
                  <span>{decision.node_label}</span>
                </div>
                <span
                  className={`badge ${decision.outcome === "deviation" ? "coral" : ""}`}
                >
                  {decision.outcome === "deviation"
                    ? "Deviation"
                    : "Matches model"}
                </span>
                <p className="muted">
                  {decision.source_refs.length} source citations ·{" "}
                  {decision.reviewed_support
                    ? "Reviewed support recorded"
                    : "Not established as reviewed policy support"}
                </p>
              </li>
            ))}
          </ol>
        ) : (
          <p>No decisions have been selected in this run.</p>
        )}
      </section>
      <section className="panel report-section">
        <h2>Findings requiring review</h2>
        {report.findings.length ? (
          report.findings.map((finding) => (
            <div
              key={`${finding.kind}-${finding.node_id}`}
              className="report-finding"
            >
              <span className="badge amber">
                {finding.kind === "uncovered"
                  ? "Uncovered decision path"
                  : "Potential rule overlap"}
              </span>
              <h3>{finding.node_label}</h3>
              <p>
                {finding.kind === "uncovered"
                  ? "No modeled choice covers the facts at this checkpoint. No authoritative action was selected."
                  : `${finding.matching_choice_ids.length} choices matched; no policy precedence was invented.`}
              </p>
              {(finding.missing_conditions > 0 ||
                finding.incompatible_conditions > 0) && (
                <p className="action-error">
                  {finding.missing_conditions} missing fact conditions and{" "}
                  {finding.incompatible_conditions} incompatible fact conditions
                  also need review.
                </p>
              )}
            </div>
          ))
        ) : (
          <p>
            No uncovered or overlapping decision has been reached
            {report.in_progress
              ? " yet. This run is still awaiting a decision."
              : "."}
          </p>
        )}
      </section>
      {report.proposals.length > 0 && (
        <section className="panel report-section">
          <h2>Proposed rule changes · unapproved</h2>
          {report.proposals.map((proposal) => (
            <div className="report-finding" key={proposal.id}>
              <h3>{proposal.rationale}</h3>
              <p>Review pending · changed rules are uncited assumptions.</p>
              <ul>
                {proposal.choices.map((choice) => (
                  <li key={choice.id}>
                    {choice.label} · {choice.evidence_status}
                  </li>
                ))}
              </ul>
              <Link className="no-print" to={`/proposals/${proposal.id}`}>
                Resume saved proposal
              </Link>
              {" · "}
              <Link
                className="no-print"
                to={`/review/${proposal.proposed_playbook_version_id}?scenario=${report.scenario_id}`}
              >
                Inspect proposed version
              </Link>
            </div>
          ))}
        </section>
      )}
      <Evidence documentId={report.document_id} refs={refs} expanded />
      <section className="report-integrity">
        <h2>Reproducibility</h2>
        <p className="hash-value">
          Source text hash: {report.source_content_hash}
        </p>
        {report.original_file_hash && (
          <p className="hash-value">
            Original PDF SHA-256: {report.original_file_hash}
          </p>
        )}
        <p className="muted">
          The JSON export includes cited text, pinned replay inputs and durable
          logical events.
        </p>
        <p>
          {report.event_count} stored logical events, verified by re-executing
          the pinned inputs.
        </p>
        <p className="hash-value">
          Last stored event hash: {report.last_state_hash}
        </p>
        <p className="muted">{report.rehearsal_notice}</p>
      </section>
    </article>
  );
}
