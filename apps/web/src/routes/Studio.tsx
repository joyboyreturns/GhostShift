import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";
import { FileText, GitBranch, ScanLine, ArrowUpRight } from "lucide-react";
import { api, policyApi } from "../lib/api";
import { SourcePanel } from "../features/documents/SourcePanel";
import { PolicyGraph } from "../features/playbooks/PolicyGraph";
import { RuleInspector } from "../features/playbooks/RuleInspector";
import { Button } from "../components/ui/button";

export function Studio() {
  const [params, setParams] = useSearchParams();
  const [selected, setSelected] = useState<{
    playbookId: string;
    nodeId: string;
  }>();
  const catalog = useQuery({ queryKey: ["catalog"], queryFn: api.catalog });
  const demo =
    catalog.data?.demos.find((d) => d.id === params.get("demo")) ??
    catalog.data?.demos[0];
  const playbookId = params.get("playbook") ?? demo?.playbook_id;
  const playbook = useQuery({
    queryKey: ["playbook", playbookId],
    queryFn: () => api.playbook(playbookId!),
    enabled: !!playbookId,
  });
  const document = useQuery({
    queryKey: ["document", playbook.data?.document_id],
    queryFn: () => api.document(playbook.data!.document_id),
    enabled: !!playbook.data,
  });
  const scenarios = useQuery({
    queryKey: ["compatible-scenarios", playbookId],
    queryFn: () => policyApi.scenarios(playbookId!),
    enabled: !!playbookId,
  });
  const scenarioId = scenarios.data?.[0]?.id;
  const error =
    catalog.error ?? document.error ?? playbook.error ?? scenarios.error;
  if (error)
    return (
      <section className="message" role="alert">
        <h1>Source Studio couldn’t load</h1>
        <p>{error.message}</p>
        <Button
          onClick={() => {
            void catalog.refetch();
            if (playbook.data) void document.refetch();
            if (playbookId) {
              void playbook.refetch();
              void scenarios.refetch();
            }
          }}
        >
          Retry
        </Button>
      </section>
    );
  if (catalog.isPending || (demo && (document.isPending || playbook.isPending)))
    return (
      <div className="message" role="status">
        Loading source documents and validated graph…
      </div>
    );
  if (!document.data || !playbook.data)
    return (
      <div className="message">
        <h1>No playbooks yet</h1>
        <Link to="/import">Import your first procedure</Link>
      </div>
    );
  const graph = playbook.data;
  const active =
    selected?.playbookId === graph.id
      ? graph.graph.nodes.find((n) => n.id === selected.nodeId)
      : graph.graph.nodes.find((n) => n.type === "decision");
  const refs = active
    ? [
        ...new Set([
          ...active.source_refs,
          ...active.choices.flatMap((c) => c.source_refs),
        ]),
      ]
    : [];
  return (
    <>
      <section className="studio-heading">
        <div>
          <div className="eyebrow">Workspace / Source Studio</div>
          <h1>
            Every rule starts with evidence<span>.</span>
          </h1>
          <p>
            Inspect the procedure. Trace the logic. Find what needs a second
            look.
          </p>
        </div>
        <div className="session-actions">
          {scenarioId && (
            <Button asChild>
              <Link
                to={`/simulation?scenario=${scenarioId}&playbook=${playbook.data.id}`}
              >
                Rehearse scenario
              </Link>
            </Button>
          )}
          <Button asChild variant="outline">
            <Link
              to={`/review/${playbook.data.id}${scenarioId ? `?scenario=${scenarioId}` : ""}`}
            >
              Review & revise policy
            </Link>
          </Button>
          <Link to={`/history/${playbook.data.id}`}>Version history</Link>
          <Link to={`/scenarios/new?playbook=${playbook.data.id}`}>
            Create scenario
          </Link>
          <Button asChild variant="outline">
            <Link to="/import">
              Import procedure <ArrowUpRight size={15} />
            </Link>
          </Button>
        </div>
      </section>
      <div className="workbench-toolbar">
        <div className="select-group">
          <label htmlFor="demo-select">SWITCH DEMO</label>
          <select
            id="demo-select"
            value={params.has("playbook") ? "" : (demo?.id ?? "")}
            onChange={(e) => setParams({ demo: e.target.value })}
          >
            {params.has("playbook") && (
              <option value="" disabled>
                Current procedure · v{graph.version}
              </option>
            )}
            {catalog.data?.demos.map((d) => (
              <option key={d.id} value={d.id}>
                {d.title}
              </option>
            ))}
          </select>
        </div>
        <div className="toolbar-meta">
          <span className="badge">
            v{graph.version} · {graph.status}
          </span>
          <span>{graph.graph.nodes.length} nodes</span>
          <span>{document.data.segments.length} source sections</span>
        </div>
      </div>
      <div className="workbench">
        <section className="panel source-panel">
          <header className="panel-heading">
            <FileText size={17} />
            <h2>Source document</h2>
            <span className="file-type">
              {document.data.source_type === "pdf"
                ? "PDF text"
                : document.data.source_type === "text"
                  ? ".txt"
                  : ".md"}
            </span>
          </header>
          <div className="document-title">
            <span className="eyebrow">Original procedure</span>
            <h3>{document.data.title}</h3>
            <p>
              {catalog.data?.demos.some(
                (demo) => demo.document_id === document.data.id,
              )
                ? "Fictional"
                : "Imported"}{" "}
              · immutable source
            </p>
          </div>
          <SourcePanel document={document.data} refs={refs} />
        </section>
        <section className="panel graph-panel">
          <header className="panel-heading">
            <GitBranch size={17} />
            <h2>Policy graph</h2>
            <span className="badge mint">References validated</span>
          </header>
          <div className="graph-note">
            Select a node to trace its source · Tab to navigate
          </div>
          <PolicyGraph
            playbook={graph}
            selectedId={active?.id}
            onSelect={(nodeId) => setSelected({ playbookId: graph.id, nodeId })}
          />
          <div className="graph-legend">
            <span>
              <i className="dot mint-dot" /> Source linked
            </span>
            <span>
              <i className="dot amber-dot" /> Review pending
            </span>
          </div>
        </section>
        <aside className="panel inspector-panel">
          <header className="panel-heading">
            <ScanLine size={17} />
            <h2>Rule inspector</h2>
          </header>
          <RuleInspector
            node={active}
            document={document.data}
            authority={graph.status}
          />
        </aside>
      </div>
      <div className="milestone-note">
        <span className="badge amber">Foundation preview</span>
        <p>
          Source inspection, rehearsals, checkpoint forks, replay verification
          and reports are live. Review rules against their sources, create
          immutable revisions, and test proposed changes without granting them
          authority.
        </p>
      </div>
    </>
  );
}
