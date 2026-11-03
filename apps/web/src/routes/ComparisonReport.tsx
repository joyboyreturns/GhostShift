import { useQuery } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";
import { simulationApi } from "../lib/api";
import { Button } from "../components/ui/button";
import { ComparisonStory } from "../features/reports/ComparisonStory";
import { statusLabels } from "../features/simulation/presentation";
export function ComparisonReport() {
  const [params] = useSearchParams();
  const left = params.get("left") ?? "";
  const right = params.get("right") ?? "";
  const query = useQuery({
    queryKey: ["compare", left, right],
    queryFn: () => simulationApi.compare(left, right),
    enabled: !!left && !!right,
    staleTime: 0,
  });
  if (!left || !right)
    return (
      <section className="message">
        <h1>Select two runs first</h1>
        <Link to="/library?tab=sessions">Open rehearsals</Link>
      </section>
    );
  if (query.isPending)
    return (
      <p className="message" role="status">
        Verifying both stored histories…
      </p>
    );
  if (!query.data)
    return (
      <section className="message" role="alert">
        <h1>Comparison unavailable</h1>
        <p>{query.error?.message}</p>
        <Button onClick={() => void query.refetch()}>Retry</Button>
      </section>
    );
  const comparison = query.data;
  return (
    <article className="report-page">
      <div className="report-navigation no-print">
        <Link to={`/replay/${left}?compare=${right}`}>Back to Replay Lab</Link>
        <div className="session-actions">
          <Button asChild variant="outline">
            <a
              href={`/api/sessions/compare?${new URLSearchParams({ left_id: left, right_id: right, allow_policy_change: "true" })}`}
              download="ghostshift-comparison.json"
            >
              Download comparison JSON
            </a>
          </Button>
          <Button variant="outline" onClick={() => window.print()}>
            Print comparison
          </Button>
        </div>
      </div>
      <span className="eyebrow">After-action / Comparative report</span>
      <h1>Two paths, inspected.</h1>
      <p>
        {comparison.scope === "proposed_policy"
          ? "Same scenario, different policy. The alternate remains an unapproved proposed model. Completion does not establish policy correctness."
          : "Same pinned policy and scenario, with independently stored decisions."}
      </p>
      <p className="muted">
        The JSON export contains both actual reports, cited source text, pinned
        replay inputs and durable logical events.
      </p>
      <ComparisonStory left={comparison.left} right={comparison.right} />
      <div className="comparison-report-grid">
        {[comparison.left, comparison.right].map((report, index) => (
          <section className="panel report-section" key={report.session_id}>
            <span className="eyebrow">Run {index === 0 ? "A" : "B"}</span>
            <h2>{report.scenario_title}</h2>
            <span className="badge amber">{statusLabels[report.status]}</span>
            <p>
              {report.playbook_authority === "draft"
                ? "Unapproved model"
                : "Human review recorded"}
            </p>
            <dl className="report-metadata">
              <div>
                <dt>Session</dt>
                <dd>{report.session_id}</dd>
              </div>
              <div>
                <dt>Pinned version</dt>
                <dd>{report.playbook_version_id}</dd>
              </div>
              <div>
                <dt>Source</dt>
                <dd>{report.source_title}</dd>
              </div>
              <div>
                <dt>Seed</dt>
                <dd>{report.scenario_seed}</dd>
              </div>
            </dl>
            <h3>Decisions</h3>
            <ol>
              {report.decisions.map((decision, index) => (
                <li className="comparison-decision" key={index}>
                  <strong>{decision.choice_label}</strong>
                  <p>
                    {decision.outcome === "deviation"
                      ? "Deviation"
                      : "Matches model"}{" "}
                    ·{" "}
                    {decision.reviewed_support
                      ? "Reviewed support"
                      : "Reviewed support not established"}
                  </p>
                </li>
              ))}
            </ol>
            <h3>Findings</h3>
            <p>
              {report.uncovered_count} uncovered paths · {report.overlap_count}{" "}
              potential overlaps · {report.deviation_count} deviations
            </p>
            {report.findings.map((finding) => (
              <p key={finding.node_id}>
                {finding.node_label}: {finding.kind}
              </p>
            ))}
            <h3>Evidence</h3>
            {report.evidence.map((evidence) => (
              <blockquote key={evidence.id}>
                §{evidence.ordinal} {evidence.text}
              </blockquote>
            ))}
            <p className="muted">
              {report.proposals.length} saved proposals · all historical
              proposal snapshots remain pending.
            </p>
            <p className="hash-value">
              Final durable hash: {report.last_state_hash}
            </p>
            <Link
              className="no-print"
              to={`/simulation/${report.session_id}/report`}
            >
              Full session report ↗
            </Link>
          </section>
        ))}
      </div>
    </article>
  );
}
