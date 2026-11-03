import { useMutation, useQuery } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, policyApi, workspaceApi } from "../lib/api";
import { SourcePanel } from "../features/documents/SourcePanel";
import { Button } from "../components/ui/button";
export function SourceDocument() {
  const { documentId = "" } = useParams();
  const navigate = useNavigate();
  const document = useQuery({
    queryKey: ["document", documentId],
    queryFn: () => api.document(documentId),
  });
  const models = useQuery({
    queryKey: ["document-models", documentId],
    queryFn: () => workspaceApi.documentModels(documentId),
    staleTime: 0,
  });
  const draft = useMutation({
    mutationFn: () => policyApi.draft(documentId, document.data!.title),
    onSuccess: (result) => navigate(`/review/${result.id}?edit=1`),
  });
  if (document.isPending)
    return (
      <p className="message" role="status">
        Loading the immutable source…
      </p>
    );
  if (!document.data)
    return (
      <section className="message" role="alert">
        <h1>Source unavailable</h1>
        <p>{document.error?.message}</p>
        <Button onClick={() => void document.refetch()}>Retry</Button>
      </section>
    );
  return (
    <section className="review-page">
      <span className="eyebrow">Library / Immutable source</span>
      <h1>{document.data.title}</h1>
      <p>
        {document.data.source_type} · {document.data.segments.length} source
        sections
      </p>
      <p className="hash-value">Text hash: {document.data.content_hash}</p>
      <Button disabled={draft.isPending} onClick={() => draft.mutate()}>
        Create a new model from this source
      </Button>
      {draft.error && <p role="alert">{draft.error.message}</p>}
      <section className="panel report-section">
        <h2>Saved models</h2>
        <p className="muted">
          The latest 50 versions associated with this exact source record.
        </p>
        {models.isPending && <p role="status">Loading models…</p>}
        {models.error && <p role="alert">{models.error.message}</p>}
        {models.data?.length === 0 && (
          <p>No modeled rules yet. Create a model to begin.</p>
        )}
        <ul>
          {models.data?.map((model) => (
            <li key={model.id}>
              <Link to={`/studio?playbook=${model.id}`}>
                {model.title} · v{model.version} · {model.status}
              </Link>
            </li>
          ))}
        </ul>
      </section>
      <section className="panel source-panel">
        <SourcePanel document={document.data} refs={[]} />
      </section>
    </section>
  );
}
