import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { api, workspaceApi, type Playbook } from "../lib/api";
import { Button } from "../components/ui/button";
import { FactsEditor } from "../features/scenarios/FactsEditor";
import { newFact, readFacts, type FactDraft } from "../lib/scenarioDraft";

function ScenarioForm({ playbook }: { playbook: Playbook }) {
  const navigate = useNavigate();
  const cache = useQueryClient();
  const fields = [
    ...new Map(
      playbook.graph.nodes.flatMap((node) =>
        node.choices.flatMap((choice) =>
          choice.conditions.map(
            (condition) => [condition.field, condition] as const,
          ),
        ),
      ),
    ).values(),
  ];
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [seed, setSeed] = useState("0");
  const [consent, setConsent] = useState(false);
  const [facts, setFacts] = useState<FactDraft[]>(() =>
    fields
      .slice(0, 64)
      .map((condition) =>
        newFact(
          condition.field,
          typeof condition.value === "boolean"
            ? "boolean"
            : typeof condition.value === "number"
              ? "number"
              : "text",
        ),
      ),
  );
  const [injects, setInjects] = useState<
    { id: string; node: string; facts: FactDraft[] }[]
  >([]);
  const save = useMutation({
    mutationFn: () =>
      workspaceApi.createScenario({
        playbook_version_id: playbook.id,
        title,
        description,
        seed: Number(seed),
        fictional: true,
        initial_facts: readFacts(facts),
        injects: injects.map((inject) => ({
          before_node_id: inject.node,
          facts: readFacts(inject.facts),
        })),
      }),
    onSuccess: (result) => {
      void cache.invalidateQueries({ queryKey: ["library"] });
      void cache.invalidateQueries({ queryKey: ["compatible-scenarios"] });
      void cache.invalidateQueries({ queryKey: ["scenario-options"] });
      navigate(`/simulation?scenario=${result.id}`);
    },
  });
  return (
    <section className="review-page">
      <span className="eyebrow">
        Scenario Studio / Human-authored experiment
      </span>
      <h1>Rehearse your procedure.</h1>
      <p>
        Choose hypothetical facts and scheduled changes for{" "}
        <strong>{playbook.title}</strong> v{playbook.version}. The existing
        deterministic engine evaluates the saved rules. A scenario does not
        approve a policy.
      </p>
      <Link to={`/studio?playbook=${playbook.id}`}>Inspect this version ↗</Link>
      <form
        className="scenario-form"
        onSubmit={(event) => {
          event.preventDefault();
          save.mutate();
        }}
      >
        <label>
          Scenario title
          <input
            required
            maxLength={200}
            value={title}
            onChange={(event) => setTitle(event.target.value)}
          />
        </label>
        <label>
          Description
          <textarea
            rows={3}
            maxLength={2000}
            value={description}
            onChange={(event) => setDescription(event.target.value)}
          />
        </label>
        <label>
          Reproducibility seed
          <input
            type="number"
            min={0}
            max={2147483647}
            step={1}
            required
            value={seed}
            onChange={(event) => setSeed(event.target.value)}
          />
        </label>
        <section className="panel report-section">
          <h2>Starting facts</h2>
          <p className="muted">
            Names come from the modeled conditions. Supply your own values; an
            omitted fact can expose an uncovered path.
          </p>
          <FactsEditor
            rows={facts}
            onChange={setFacts}
            fields={fields.map((field) => field.field)}
          />
        </section>
        <section className="panel report-section">
          <h2>Scheduled fact changes</h2>
          <p className="muted">
            Changes apply once, immediately before the selected step, in the
            order shown.
          </p>
          {injects.map((inject, index) => (
            <fieldset className="inject-editor" key={inject.id}>
              <legend>Change {index + 1}</legend>
              <label>
                Before step
                <select
                  required
                  aria-label="Before step"
                  value={inject.node}
                  onChange={(event) =>
                    setInjects((previous) =>
                      previous.map((item) =>
                        item.id === inject.id
                          ? { ...item, node: event.target.value }
                          : item,
                      ),
                    )
                  }
                >
                  <option value="">Choose a step…</option>
                  {playbook.graph.nodes.map((node) => (
                    <option value={node.id} key={node.id}>
                      {node.label}
                    </option>
                  ))}
                </select>
              </label>
              <FactsEditor
                rows={inject.facts}
                onChange={(facts) =>
                  setInjects((previous) =>
                    previous.map((item) =>
                      item.id === inject.id ? { ...item, facts } : item,
                    ),
                  )
                }
                fields={fields.map((field) => field.field)}
              />
              <Button
                type="button"
                variant="outline"
                onClick={() =>
                  setInjects((previous) =>
                    previous.filter((item) => item.id !== inject.id),
                  )
                }
              >
                Remove change
              </Button>
            </fieldset>
          ))}
          <Button
            type="button"
            variant="outline"
            disabled={injects.length >= 20}
            onClick={() =>
              setInjects((previous) => [
                ...previous,
                { id: crypto.randomUUID(), node: "", facts: [newFact()] },
              ])
            }
          >
            Add scheduled change
          </Button>
        </section>
        <label className="consent">
          <input
            type="checkbox"
            checked={consent}
            onChange={(event) => setConsent(event.target.checked)}
          />
          This is a fictional training scenario, not a live incident.
        </label>
        <Button disabled={!consent || save.isPending}>
          {save.isPending ? "Saving…" : "Save scenario"}
        </Button>
        {save.error && (
          <p role="alert">{save.error.message} Your entries are preserved.</p>
        )}
      </form>
    </section>
  );
}
export function ScenarioCreate() {
  const [params] = useSearchParams();
  const id = params.get("playbook");
  const query = useQuery({
    queryKey: ["playbook", id],
    queryFn: () => api.playbook(id!),
    enabled: !!id,
  });
  if (!id)
    return (
      <section className="message">
        <h1>Choose a model first</h1>
        <Link to="/library?tab=playbooks">Open your playbooks</Link>
      </section>
    );
  if (query.error && !query.data)
    return (
      <section className="message" role="alert">
        <h1>Model unavailable</h1>
        <p>{query.error.message}</p>
        <Button onClick={() => void query.refetch()}>Retry</Button>
      </section>
    );
  if (!query.data)
    return (
      <p className="message" role="status">
        Loading the version and condition fields…
      </p>
    );
  return <ScenarioForm key={query.data.id} playbook={query.data} />;
}
