import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { BookOpen, FileText, GitBranch, Plus, Play } from "lucide-react";
import { policyApi, workspaceApi } from "../lib/api";
import { Button } from "../components/ui/button";
import { statusLabels } from "../features/simulation/presentation";

const tabs = ["documents", "playbooks", "scenarios", "sessions"] as const;
type Tab = (typeof tabs)[number];
export function Library() {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const tab: Tab = tabs.find((tab) => tab === params.get("tab")) ?? "documents";
  const offset = Math.max(0, Number(params.get("offset")) || 0);
  const [search, setSearch] = useState(params.get("q") ?? "");
  const query = useQuery({
    queryKey: ["library", params.get("q") ?? "", offset],
    queryFn: () => workspaceApi.library(params.get("q") ?? "", offset),
    staleTime: 0,
  });
  const draft = useMutation({
    mutationFn: ({ id, title }: { id: string; title: string }) =>
      policyApi.draft(id, title),
    onSuccess: (result) => navigate(`/review/${result.id}?edit=1`),
  });
  const data = query.data;
  const empty = data && data[tab].length === 0;
  return (
    <section className="library-page">
      <header className="library-heading">
        <div>
          <span className="eyebrow">Workspace / Library</span>
          <h1>Your procedures, ready to test.</h1>
          <p className="muted">
            Return to saved sources, versions, scenarios and rehearsals in this
            workspace.
          </p>
        </div>
        <div className="session-actions">
          <Button asChild>
            <Link to="/import">
              <Plus size={16} />
              Import procedure
            </Link>
          </Button>
          <Link to="/guide">How it works ↗</Link>
        </div>
      </header>
      <form
        className="library-search"
        onSubmit={(event) => {
          event.preventDefault();
          setParams({ tab, q: search });
        }}
      >
        <label htmlFor="library-search">Search by title or run ID</label>
        <div>
          <input
            id="library-search"
            maxLength={200}
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
          <Button variant="outline">Search</Button>
        </div>
      </form>
      <nav className="library-tabs" aria-label="Library sections">
        {tabs.map((item) => (
          <button
            key={item}
            aria-current={item === tab ? "page" : undefined}
            onClick={() => setParams({ tab: item, q: params.get("q") ?? "" })}
          >
            {item[0].toUpperCase() + item.slice(1)}{" "}
            <span>{data?.totals[item] ?? "…"}</span>
          </button>
        ))}
      </nav>
      {query.isPending && <p role="status">Loading your workspace…</p>}
      {query.error && (
        <p role="alert">
          {query.error.message}{" "}
          <button className="text-action" onClick={() => void query.refetch()}>
            Retry
          </button>
        </p>
      )}
      {draft.error && <p role="alert">{draft.error.message}</p>}
      {empty && (
        <div className="panel library-empty">
          <h2>No {tab} found</h2>
          <p>
            {params.get("q")
              ? "Try another search."
              : tab === "sessions"
                ? "Start a scenario to record your first rehearsal."
                : "Import a procedure, model its rules, then create a scenario."}
          </p>
          <Link to={tab === "sessions" ? "/simulation" : "/import"}>
            {tab === "sessions" ? "Choose a scenario" : "Import a procedure"} ↗
          </Link>
        </div>
      )}
      <div className="library-grid">
        {tab === "documents" &&
          data?.documents.map((document) => (
            <article className="panel library-card" key={document.id}>
              <FileText size={20} />
              <span className="eyebrow">
                {document.source_type} · {document.segment_count} sections
              </span>
              <h2>
                <Link to={`/sources/${document.id}`}>{document.title}</Link>
              </h2>
              <p className="muted">
                {document.playbook_count} saved model versions ·{" "}
                {new Date(document.created_at).toLocaleDateString()}
              </p>
              <Button
                variant="outline"
                disabled={draft.isPending}
                onClick={() =>
                  draft.mutate({ id: document.id, title: document.title })
                }
              >
                Model this source
              </Button>
            </article>
          ))}
        {tab === "playbooks" &&
          data?.playbooks.map((version) => (
            <article className="panel library-card" key={version.id}>
              <GitBranch size={20} />
              <span
                className={`badge ${version.status === "approved" ? "mint" : "amber"}`}
              >
                v{version.version} · {version.status}
              </span>
              <h2>
                <Link to={`/studio?playbook=${version.id}`}>
                  {version.title}
                </Link>
              </h2>
              <p className="muted">
                {version.node_count} nodes ·{" "}
                {new Date(version.created_at).toLocaleDateString()}
              </p>
              <div className="session-actions">
                <Link to={`/review/${version.id}`}>Review & revise</Link>
                <Link to={`/history/${version.id}`}>Version history</Link>
                <Link to={`/scenarios/new?playbook=${version.id}`}>
                  Create scenario
                </Link>
              </div>
            </article>
          ))}
        {tab === "scenarios" &&
          data?.scenarios.map((scenario) => (
            <article className="panel library-card" key={scenario.id}>
              <Play size={20} />
              <span className="badge">Fictional rehearsal</span>
              <h2>{scenario.title}</h2>
              <p>{scenario.description}</p>
              <p className="muted">
                {Object.keys(scenario.initial_facts).length} initial facts ·{" "}
                {scenario.injects.length} scheduled changes
              </p>
              <Button asChild>
                <Link to={`/simulation?scenario=${scenario.id}`}>
                  Rehearse scenario
                </Link>
              </Button>
            </article>
          ))}
        {tab === "sessions" &&
          data?.sessions.map((session) => (
            <article className="panel library-card" key={session.id}>
              <BookOpen size={20} />
              <span className="badge amber">
                {statusLabels[session.status]}
              </span>
              <h2>
                <Link to={`/simulation/${session.id}`}>
                  {session.scenario_title}
                </Link>
              </h2>
              <p className="muted">
                {session.playbook_title} ·{" "}
                {new Date(session.created_at).toLocaleString()}
              </p>
              <small className="session-id">
                Run {session.id.slice(0, 8)} · revision {session.revision}
              </small>
              <div className="session-actions">
                <Link to={`/simulation/${session.id}`}>Resume run</Link>
                <Link to={`/replay/${session.id}`}>Replay Lab</Link>
                <Link to={`/simulation/${session.id}/report`}>Report</Link>
              </div>
            </article>
          ))}
      </div>
      {data && (
        <div className="pagination">
          <Button
            variant="outline"
            disabled={offset === 0}
            onClick={() =>
              setParams({
                tab,
                q: params.get("q") ?? "",
                offset: String(Math.max(0, offset - data.limit)),
              })
            }
          >
            Previous
          </Button>
          <span>
            {data.totals[tab]
              ? `${offset + 1}–${Math.min(offset + data.limit, data.totals[tab])} of ${data.totals[tab]}`
              : "0 results"}
          </span>
          <Button
            variant="outline"
            disabled={offset + data.limit >= data.totals[tab]}
            onClick={() =>
              setParams({
                tab,
                q: params.get("q") ?? "",
                offset: String(offset + data.limit),
              })
            }
          >
            Next
          </Button>
        </div>
      )}
    </section>
  );
}
