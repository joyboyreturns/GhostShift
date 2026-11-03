import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { ArrowRight, GitBranch } from "lucide-react";
import { api, simulationApi, workspaceApi } from "../lib/api";
import { Button } from "../components/ui/button";
import { factLabel } from "../features/simulation/presentation";

export function SimulationStart() {
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const [consent, setConsent] = useState(false);
  const catalog = useQuery({ queryKey: ["catalog"], queryFn: api.catalog });
  const options = useQuery({
    queryKey: ["scenario-options"],
    queryFn: () => workspaceApi.library("", 0, 50),
    staleTime: 0,
  });
  const scenarioId =
    params.get("scenario") ?? catalog.data?.demos[0]?.scenario_id;
  const scenario = useQuery({
    queryKey: ["scenario", scenarioId],
    queryFn: () => simulationApi.scenario(scenarioId!),
    enabled: !!scenarioId,
  });
  const versionId =
    params.get("playbook") ?? scenario.data?.playbook_version_id;
  const playbook = useQuery({
    queryKey: ["playbook", versionId],
    queryFn: () => api.playbook(versionId!),
    enabled: !!versionId,
  });
  const start = useMutation({
    mutationFn: () =>
      simulationApi.start(
        scenarioId!,
        consent,
        params.get("playbook") ?? undefined,
      ),
    onSuccess: (session) => navigate(`/simulation/${session.id}`),
  });
  const error = catalog.error ?? scenario.error ?? playbook.error;
  if (error)
    return (
      <section className="message" role="alert">
        <h1>Scenarios couldn’t load</h1>
        <p>{error.message}</p>
        <Button
          onClick={() => {
            void catalog.refetch();
            void scenario.refetch();
            void playbook.refetch();
          }}
        >
          Retry
        </Button>
      </section>
    );
  if (
    catalog.isPending ||
    (scenarioId && (scenario.isPending || playbook.isPending))
  )
    return (
      <div className="message" role="status">
        Loading scenarios…
      </div>
    );
  if (!scenarioId || !scenario.data)
    return (
      <section className="message">
        <h1>No scenarios available</h1>
        <Link to="/studio">Return to Source Studio</Link>
      </section>
    );
  const data = scenario.data;
  return (
    <section className="scenario-start">
      <span className="eyebrow">Simulation Room / Fictional rehearsals</span>
      <h1>
        Rehearse the unexpected<span>.</span>
      </h1>
      <p className="muted">
        Make decisions against a pinned copy of the procedure. Every action and
        finding stays linked to the source.
      </p>
      <label htmlFor="scenario-select">Choose a fictional scenario</label>
      <select
        id="scenario-select"
        value={data.id}
        onChange={(event) => {
          setParams({ scenario: event.target.value });
          setConsent(false);
        }}
      >
        {options.data?.scenarios.map((scenario) => (
          <option key={scenario.id} value={scenario.id}>
            {scenario.title}
          </option>
        ))}
        {!options.data?.scenarios.some(
          (scenario) => scenario.id === data.id,
        ) && <option value={data.id}>{data.title}</option>}
      </select>
      <div className="scenario-card panel">
        <span className="badge amber">
          Fictional ·{" "}
          {playbook.data?.status === "approved"
            ? "reviewed playbook"
            : "draft model"}
        </span>
        <h2>{data.title}</h2>
        <p>{data.description}</p>
        <div className="initial-facts">
          <h3>Starting facts</h3>
          <dl>
            {Object.entries(data.initial_facts).map(([field, value]) => (
              <div key={field}>
                <dt>{factLabel(field)}</dt>
                <dd>{String(value)}</dd>
              </div>
            ))}
          </dl>
        </div>
        <p className="muted">
          {data.injects.length} scheduled scenario changes. New facts appear at
          their modeled checkpoint.
        </p>
        <label className="consent">
          <input
            type="checkbox"
            checked={consent}
            onChange={(event) => setConsent(event.target.checked)}
          />
          {playbook.data?.status === "approved"
            ? "I understand this is a fictional rehearsal of a reviewed playbook."
            : "I understand this is a fictional, unapproved model rehearsal."}
        </label>
        <div className="hero-actions">
          <Button
            disabled={!consent || start.isPending}
            onClick={() => start.mutate()}
          >
            {start.isPending ? "Starting…" : "Start rehearsal"}
            <ArrowRight size={17} />
          </Button>
          <Button asChild variant="outline">
            <Link to={`/studio?playbook=${versionId}`}>
              <GitBranch size={16} />
              Inspect source & graph
            </Link>
          </Button>
        </div>
        {start.error && (
          <p role="alert">
            Couldn’t start the rehearsal: {start.error.message}
          </p>
        )}
      </div>
    </section>
  );
}
