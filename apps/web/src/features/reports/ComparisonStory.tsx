import { Link } from "react-router-dom";
import type { SessionReport } from "../../lib/api";
import { statusLabels } from "../simulation/presentation";

import { firstDecisionDifference } from "./comparisonPresentation";

export function ComparisonStory({
  left,
  right,
}: {
  left: SessionReport;
  right: SessionReport;
}) {
  const difference = firstDecisionDifference(left, right);
  return (
    <div className="comparison-story">
      <h3>What changed in the recorded runs?</h3>
      {!difference && (
        <p>
          The recorded choice sequence is the same. Inspect findings and pinned
          policy versions for other differences.
        </p>
      )}
      <div className="outcome-pair">
        {[left, right].map((report, index) => {
          const decision = index === 0 ? difference?.left : difference?.right;
          return (
            <article key={report.session_id}>
              <span className="eyebrow">
                {index === 0 ? "Original / Run A" : "Alternate / Run B"}
              </span>
              <h4>{statusLabels[report.status]}</h4>
              <p className="badge amber">
                {report.playbook_authority === "approved"
                  ? "Human review recorded"
                  : "Unapproved model"}
              </p>
              {difference && (
                <p>
                  <strong>
                    {decision?.choice_label ??
                      "No choice recorded at this point"}
                  </strong>
                  {decision && <> · {decision.node_label}</>}
                </p>
              )}
              <ul>
                {report.findings.map((finding) => (
                  <li key={`${finding.node_id}:${finding.kind}`}>
                    {finding.node_label}:{" "}
                    {finding.kind === "uncovered"
                      ? "no matching path"
                      : "multiple matching paths"}
                  </li>
                ))}
              </ul>
              <p>
                {report.deviation_count} deviations ·{" "}
                {report.reviewed_supported_count} reviewed, supported decisions
              </p>
              <Link
                className="no-print"
                to={`/simulation/${report.session_id}`}
              >
                Inspect run {index === 0 ? "A" : "B"} ↗
              </Link>
            </article>
          );
        })}
      </div>
      <p className="muted">
        Reaching the modeled end does not prove that a proposed response works
        in the real world. Compare the recorded evidence and review any
        assumptions.
      </p>
    </div>
  );
}
