import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { workspaceApi } from "../lib/api";
import { Button } from "../components/ui/button";
export function VersionHistory() {
  const { playbookId = "" } = useParams();
  const query = useQuery({
    queryKey: ["history", playbookId],
    queryFn: () => workspaceApi.history(playbookId),
    staleTime: 0,
  });
  return (
    <section className="review-page">
      <span className="eyebrow">Source Studio / Version history</span>
      <h1>Trace how the procedure changed.</h1>
      <p>
        Each revision is a separate version. Source changes retain their
        original document. Existing rehearsals keep their own pinned policy and
        authority.
      </p>
      {query.isPending && <p role="status">Loading the version family…</p>}
      {query.error && (
        <p role="alert">
          {query.error.message}{" "}
          <Button onClick={() => void query.refetch()}>Retry</Button>
        </p>
      )}
      <ol className="version-history">
        {query.data?.versions.map((version) => (
          <li
            className="panel library-card"
            key={version.id}
            aria-current={version.id === playbookId ? "step" : undefined}
          >
            <span
              className={`badge ${version.status === "approved" ? "mint" : "amber"}`}
            >
              v{version.version} · {version.status}
            </span>
            <h2>{version.title}</h2>
            <p className="muted">
              {new Date(version.created_at).toLocaleString()} ·{" "}
              {version.node_count} nodes
            </p>
            <p>
              {version.parent_version_id ? (
                <>
                  Revision of{" "}
                  <Link to={`/history/${version.parent_version_id}`}>
                    {version.parent_version_id.slice(0, 8)}
                  </Link>
                </>
              ) : (
                "Original model"
              )}
            </p>
            <p className="session-id">Source {version.document_id}</p>
            <div className="session-actions">
              <Link to={`/studio?playbook=${version.id}`}>Inspect version</Link>
              <Link to={`/review/${version.id}`}>Review & revise</Link>
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}
