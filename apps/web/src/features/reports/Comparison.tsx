import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { simulationApi } from "../../lib/api";
import { ComparisonStory } from "./ComparisonStory";
import { statusLabels } from "../simulation/presentation";

export function Comparison({
  parentId,
  alternateId,
  title = "Parent vs. alternate",
  columns = ["Parent", "Alternate"],
}: {
  parentId: string;
  alternateId: string;
  title?: string;
  columns?: readonly [string, string];
}) {
  const query = useQuery({
    queryKey: ["compare", parentId, alternateId],
    queryFn: () => simulationApi.compare(parentId, alternateId),
  });
  if (query.isPending) return <p role="status">Comparing actual runs…</p>;
  if (query.error)
    return (
      <p role="alert">
        Comparison unavailable: {query.error.message}{" "}
        <button className="text-action" onClick={() => void query.refetch()}>
          Retry comparison
        </button>
      </p>
    );
  const { left, right, shared_event_prefix, scope } = query.data;
  const rows = [
    ["Outcome", statusLabels[left.status], statusLabels[right.status]],
    ["Decisions", left.decision_count, right.decision_count],
    ["Deviations", left.deviation_count, right.deviation_count],
    ["Uncovered paths", left.uncovered_count, right.uncovered_count],
    ["Potential overlaps", left.overlap_count, right.overlap_count],
  ];
  return (
    <section className="comparison-panel panel" aria-label="Run comparison">
      <h2>{title}</h2>
      <p className="muted">
        {scope === "proposed_policy"
          ? "Same scenario, different policy. The alternate uses an unapproved proposal. Event hashes belong to separate contexts; a completed run does not establish policy correctness."
          : `${shared_event_prefix} shared logical events before the histories diverge. Same pinned procedure and scenario.`}
      </p>
      <p className="no-print">
        <Link
          to={`/reports/compare?${new URLSearchParams({ left: parentId, right: alternateId })}`}
        >
          Open printable comparison & export ↗
        </Link>
      </p>
      <ComparisonStory left={left} right={right} />
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th scope="col">Finding</th>
              <th scope="col">{columns[0]}</th>
              <th scope="col">{columns[1]}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(([label, leftValue, rightValue]) => (
              <tr key={label}>
                <th scope="row">{label}</th>
                <td>{leftValue}</td>
                <td>{rightValue}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
