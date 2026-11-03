import type { PolicyNode, SourceDocument } from "../../lib/api";
export function RuleInspector({
  node,
  document,
  authority = "draft",
}: {
  node?: PolicyNode;
  document: SourceDocument;
  authority?: "draft" | "approved";
}) {
  if (!node)
    return (
      <div className="inspector-content">
        <p>
          Select a graph node to inspect its conditions and source evidence.
        </p>
      </div>
    );
  const refs = [
    ...new Set([
      ...node.source_refs,
      ...node.choices.flatMap((c) => c.source_refs),
    ]),
  ];
  return (
    <div className="inspector-content">
      <span className="eyebrow">
        {node.type} / {node.id}
      </span>
      <h3>{node.label}</h3>
      <span className={`badge ${authority === "approved" ? "mint" : "amber"}`}>
        {authority === "approved"
          ? "Human review recorded"
          : "Pending human review"}
      </span>
      <p className="muted">
        A citation locates evidence. A person must verify that the rule
        represents it accurately.
      </p>
      <h4>Conditions & transitions</h4>
      {node.choices.length ? (
        node.choices.map((choice) => (
          <div className="condition" key={choice.id}>
            <strong>{choice.label}</strong>
            {choice.conditions.map((c, i) => (
              <code key={i}>
                {i > 0 ? "AND " : ""}
                {c.field} {c.operator} {JSON.stringify(c.value)}
              </code>
            ))}
            <span className="muted">
              → {choice.destination} · {choice.evidence_status}
            </span>
          </div>
        ))
      ) : (
        <p className="muted">
          {node.next_node
            ? `Continues to ${node.next_node}`
            : "End of modeled workflow"}
        </p>
      )}
      <h4>
        Source evidence <span className="count">{refs.length}</span>
      </h4>
      {refs.length ? (
        refs.map((ref) => {
          const segment = document.segments.find((s) => s.id === ref);
          return (
            <blockquote key={ref}>
              <span>
                §{segment?.ordinal}
                {segment?.page_number != null
                  ? ` · PDF page ${segment.page_number}`
                  : ""}
              </span>
              {segment?.text}
            </blockquote>
          );
        })
      ) : (
        <p className="muted">
          No source cited. This node has no evidence authority.
        </p>
      )}
    </div>
  );
}
