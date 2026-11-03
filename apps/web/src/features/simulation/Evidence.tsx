import { useQuery } from "@tanstack/react-query";
import { api } from "../../lib/api";
import { SourcePanel } from "../documents/SourcePanel";

export function Evidence({
  documentId,
  refs,
  expanded = false,
}: {
  documentId: string;
  refs: string[];
  expanded?: boolean;
}) {
  const document = useQuery({
    queryKey: ["document", documentId],
    queryFn: () => api.document(documentId),
  });
  return (
    <details className="evidence-drawer panel" open={expanded}>
      <summary>
        Source evidence{" "}
        <span className="muted">
          {refs.length} cited sections · inspect the original text
        </span>
      </summary>
      {document.isPending && (
        <p className="muted" role="status">
          Loading original source…
        </p>
      )}
      {document.error && (
        <p role="alert">Source unavailable: {document.error.message}</p>
      )}
      {document.data && (
        <>
          <div className="evidence-title">
            <h3>{document.data.title}</h3>
            <p className="muted">
              Citations locate the source. They do not establish that a draft
              rule was reviewed.
            </p>
          </div>
          <SourcePanel document={document.data} refs={refs} />
        </>
      )}
    </details>
  );
}
