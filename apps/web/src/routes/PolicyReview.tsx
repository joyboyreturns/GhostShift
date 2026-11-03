import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Link,
  useNavigate,
  useParams,
  useSearchParams,
} from "react-router-dom";
import { api, policyApi, type Playbook, type SourceDocument } from "../lib/api";
import { Button } from "../components/ui/button";
import { StepRemoval } from "../features/policy/StepRemoval";
import { insertStep, removeStep } from "../lib/graphDraft";
import { ChoiceEditor } from "../features/policy/ChoiceEditor";
import { operatorLabels } from "../features/simulation/presentation";

function ReviewWorkspace({
  playbook,
  document,
  scenario,
}: {
  playbook: Playbook;
  document: SourceDocument;
  scenario: string | null;
}) {
  const navigate = useNavigate();
  const cache = useQueryClient();
  const [params] = useSearchParams();
  const [reviewed, setReviewed] = useState<string[]>([]);
  const [reviewer, setReviewer] = useState("");
  const [notes, setNotes] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [graph, setGraph] = useState(playbook.graph);
  const [source, setSource] = useState(document);
  const [sourceText, setSourceText] = useState(document.content);
  const suffix = scenario ? `?scenario=${encodeURIComponent(scenario)}` : "";
  const rules = playbook.graph.nodes.flatMap((node) =>
    node.choices.map((choice) => ({
      node,
      choice,
      key: JSON.stringify([node.id, choice.id]),
    })),
  );
  const audit = useQuery({
    queryKey: ["review", playbook.id],
    queryFn: () => policyApi.review(playbook.id),
  });
  const approval = useMutation({
    mutationFn: () => policyApi.approve(playbook, reviewer, notes),
    onSuccess: (result) => {
      cache.setQueryData(["playbook", result.id], result);
      void cache.invalidateQueries({ queryKey: ["review", result.id] });
    },
  });
  const revision = useMutation({
    mutationFn: () =>
      policyApi.revise(playbook.id, source.id, playbook.title, graph),
    onSuccess: (result) => navigate(`/review/${result.id}${suffix}`),
  });
  const importSource = useMutation({
    mutationFn: () =>
      api.import(
        `${document.title} — revision`.slice(0, 200),
        sourceText,
        "markdown",
      ),
    onSuccess: (result) => {
      setSource(result);
      setGraph((existing) => ({
        nodes: existing.nodes.map((node) => ({
          ...node,
          source_refs: [],
          choices: node.choices.map((choice) => ({
            ...choice,
            source_refs: [],
            evidence_status: "uncited",
          })),
        })),
      }));
    },
  });
  const empty = !playbook.graph.nodes.some(
    (node) => node.type === "decision" || node.type === "action",
  );
  const uncited =
    rules.some(({ choice }) => !choice.source_refs.length) ||
    playbook.graph.nodes.some(
      (node) => node.type === "action" && !node.source_refs.length,
    );
  return (
    <article className="review-page">
      <span className="eyebrow">Source Studio / Human review</span>
      <h1>{playbook.title}</h1>
      <div className="session-strip">
        <Link to={`/history/${playbook.id}`}>Version history</Link>
        <Link to={`/scenarios/new?playbook=${playbook.id}`}>
          Create scenario
        </Link>
        <span
          className={`badge ${playbook.status === "approved" ? "mint" : "amber"}`}
        >
          v{playbook.version} · {playbook.status}
        </span>
        <Link to={`/studio?playbook=${playbook.id}`}>
          Inspect graph & source
        </Link>
        {playbook.parent_version_id && (
          <Link to={`/review/${playbook.parent_version_id}${suffix}`}>
            Parent version
          </Link>
        )}
        {scenario && (
          <Link
            to={`/simulation?scenario=${encodeURIComponent(scenario)}&playbook=${playbook.id}`}
          >
            Rehearse this version
          </Link>
        )}
      </div>
      <p>
        A reference locates text. You must verify that every action, threshold
        and condition faithfully represents that text. Approval records your
        local review; this preview does not authenticate reviewer identities.
      </p>
      {document.source_type === "pdf" && (
        <p className="pdf-extraction-note">
          This model uses extracted PDF text. Verify reading order against the
          original file before approval.
          {document.empty_pages?.length
            ? ` No text was extracted from page(s) ${document.empty_pages.join(", ")}.`
            : ""}
        </p>
      )}
      {empty && (
        <p className="action-error">
          This source has no modeled rules yet. Add a decision in a new draft
          revision below.
        </p>
      )}
      {uncited && (
        <p className="action-error">
          Uncited rules block approval. Add supporting source text and citations
          in a new revision.
        </p>
      )}
      <section className="panel report-section">
        <h2>Review each modeled choice</h2>
        <form
          onSubmit={(event) => {
            event.preventDefault();
            approval.mutate();
          }}
        >
          {rules.map(({ node, choice, key }) => (
            <fieldset className="review-rule" key={key}>
              <legend>
                {node.label} / {choice.label}
              </legend>
              <ul>
                {choice.conditions.map((condition, index) => (
                  <li key={index}>
                    {condition.field} {operatorLabels[condition.operator]}{" "}
                    {JSON.stringify(condition.value)}
                  </li>
                ))}
              </ul>
              <p>
                Continues to:{" "}
                {
                  playbook.graph.nodes.find(
                    (node) => node.id === choice.destination,
                  )?.label
                }
              </p>
              {choice.source_refs.map((ref) => {
                const segment = document.segments.find(
                  (segment) => segment.id === ref,
                );
                return (
                  <blockquote key={ref}>
                    §{segment?.ordinal} {segment?.text}
                  </blockquote>
                );
              })}
              {!choice.source_refs.length && <p>No supporting source cited.</p>}
              {playbook.status === "draft" && (
                <label className="consent">
                  <input
                    type="checkbox"
                    checked={reviewed.includes(key)}
                    disabled={!choice.source_refs.length}
                    onChange={(event) =>
                      setReviewed((previous) =>
                        event.target.checked
                          ? [...previous, key]
                          : previous.filter((item) => item !== key),
                      )
                    }
                  />
                  I verified this choice and all its conditions against the
                  cited source.
                </label>
              )}
            </fieldset>
          ))}
          {playbook.graph.nodes
            .filter((node) => node.type === "action")
            .map((node) => (
              <section className="review-rule" key={node.id}>
                <h3>Action: {node.label}</h3>
                {node.source_refs.map((ref) => (
                  <blockquote key={ref}>
                    {
                      document.segments.find((segment) => segment.id === ref)
                        ?.text
                    }
                  </blockquote>
                ))}
              </section>
            ))}
          {playbook.status === "draft" && (
            <div className="approval-fields">
              <label>
                Reviewer name
                <input
                  required
                  maxLength={100}
                  value={reviewer}
                  onChange={(event) => setReviewer(event.target.value)}
                />
              </label>
              <label>
                Review notes
                <textarea
                  required
                  maxLength={2000}
                  value={notes}
                  onChange={(event) => setNotes(event.target.value)}
                  rows={3}
                />
              </label>
              <label className="consent">
                <input
                  type="checkbox"
                  checked={confirmed}
                  onChange={(event) => setConfirmed(event.target.checked)}
                />
                I confirm the entire modeled procedure, including action nodes,
                is supported by this source. I understand approval makes this
                version immutable.
              </label>
              <Button
                disabled={
                  empty ||
                  uncited ||
                  reviewed.length !== rules.length ||
                  !confirmed ||
                  !reviewer.trim() ||
                  !notes.trim() ||
                  approval.isPending
                }
              >
                {approval.isPending
                  ? "Recording review…"
                  : "Approve reviewed version"}
              </Button>
            </div>
          )}
        </form>
        {playbook.status === "approved" && (
          <div role="status">
            <h3>Approved version · immutable</h3>
            {audit.data && (
              <p>
                Reviewed by {audit.data.reviewer}: {audit.data.notes}
              </p>
            )}
            {audit.isPending && <p>Loading review record…</p>}
            {audit.error && <p role="alert">{audit.error.message}</p>}
          </div>
        )}
        {approval.error && <p role="alert">{approval.error.message}</p>}
      </section>
      <details
        className="panel report-section"
        open={params.get("edit") === "1" || empty ? true : undefined}
      >
        <summary>Create a new revision</summary>
        <p>
          Changes create a separate draft version. Existing approvals, sources
          and rehearsals remain pinned.
        </p>
        <details>
          <summary>Revise the source document</summary>
          <p>
            Saving revised source clears all old references. Explicitly cite the
            new sections below.
          </p>
          <label>
            Revised procedure
            <textarea
              rows={12}
              maxLength={100000}
              value={sourceText}
              onChange={(event) => setSourceText(event.target.value)}
            />
          </label>
          <Button
            type="button"
            variant="outline"
            disabled={
              importSource.isPending ||
              !sourceText.trim() ||
              sourceText === source.content
            }
            onClick={() => importSource.mutate()}
          >
            {importSource.isPending
              ? "Saving…"
              : "Save revised source snapshot"}
          </Button>
          {source.id !== document.id && (
            <p role="status">
              New source saved. Select its supporting sections for each rule.
            </p>
          )}
          {importSource.error && (
            <p role="alert">{importSource.error.message}</p>
          )}
        </details>
        <form
          onSubmit={(event) => {
            event.preventDefault();
            revision.mutate();
          }}
        >
          <Button
            type="button"
            variant="outline"
            disabled={graph.nodes.length >= 200}
            onClick={() =>
              setGraph((previous) => insertStep(previous, "decision"))
            }
          >
            Add decision before completion
          </Button>
          <Button
            type="button"
            variant="outline"
            disabled={graph.nodes.length >= 200}
            onClick={() =>
              setGraph((previous) => insertStep(previous, "action"))
            }
          >
            Add action before completion
          </Button>
          {graph.nodes
            .filter((node) => node.type === "decision")
            .map((node) => (
              <section
                className="revision-node"
                key={`${node.id}-${source.id}`}
              >
                <label>
                  Decision question
                  <input
                    required
                    maxLength={300}
                    value={node.label}
                    onChange={(event) =>
                      setGraph((previous) => ({
                        nodes: previous.nodes.map((existing) =>
                          existing.id === node.id
                            ? { ...existing, label: event.target.value }
                            : existing,
                        ),
                      }))
                    }
                  />
                </label>
                <StepRemoval
                  node={node}
                  nodes={graph.nodes}
                  onRemove={(replacement) =>
                    setGraph((previous) =>
                      removeStep(previous, node.id, replacement),
                    )
                  }
                />
                <ChoiceEditor
                  nodes={graph.nodes}
                  choices={node.choices}
                  source={source}
                  onChange={(choices) =>
                    setGraph((previous) => ({
                      nodes: previous.nodes.map((existing) =>
                        existing.id === node.id
                          ? { ...existing, choices }
                          : existing,
                      ),
                    }))
                  }
                />
              </section>
            ))}
          {graph.nodes
            .filter((node) => node.type === "action")
            .map((node) => (
              <fieldset key={node.id}>
                <legend>Action evidence: {node.label}</legend>
                <label>
                  Action step label
                  <input
                    required
                    maxLength={300}
                    value={node.label}
                    onChange={(event) =>
                      setGraph((previous) => ({
                        nodes: previous.nodes.map((existing) =>
                          existing.id === node.id
                            ? { ...existing, label: event.target.value }
                            : existing,
                        ),
                      }))
                    }
                  />
                </label>
                <StepRemoval
                  node={node}
                  nodes={graph.nodes}
                  onRemove={(replacement) =>
                    setGraph((previous) =>
                      removeStep(previous, node.id, replacement),
                    )
                  }
                />
                <label>
                  Continue after this action
                  <select
                    aria-label="Continue after this action"
                    value={node.next_node ?? ""}
                    onChange={(event) =>
                      setGraph((previous) => ({
                        nodes: previous.nodes.map((existing) =>
                          existing.id === node.id
                            ? { ...existing, next_node: event.target.value }
                            : existing,
                        ),
                      }))
                    }
                  >
                    {graph.nodes.map((next) => (
                      <option key={next.id} value={next.id}>
                        {next.label}
                      </option>
                    ))}
                  </select>
                </label>
                {source.segments.map((segment) => (
                  <label className="consent" key={segment.id}>
                    <input
                      type="checkbox"
                      checked={node.source_refs.includes(segment.id)}
                      onChange={(event) =>
                        setGraph((previous) => ({
                          nodes: previous.nodes.map((existing) =>
                            existing.id !== node.id
                              ? existing
                              : {
                                  ...existing,
                                  source_refs: event.target.checked
                                    ? [...existing.source_refs, segment.id]
                                    : existing.source_refs.filter(
                                        (ref) => ref !== segment.id,
                                      ),
                                },
                          ),
                        }))
                      }
                    />
                    §{segment.ordinal} {segment.text}
                  </label>
                ))}
              </fieldset>
            ))}
          <Button disabled={revision.isPending || importSource.isPending}>
            {revision.isPending ? "Saving…" : "Save draft revision"}
          </Button>
          {revision.error && (
            <p role="alert">
              {revision.error.message} Your edits are preserved.
            </p>
          )}
        </form>
      </details>
    </article>
  );
}

export function PolicyReview() {
  const { playbookId = "" } = useParams();
  const [params] = useSearchParams();
  const playbook = useQuery({
    queryKey: ["playbook", playbookId],
    queryFn: () => api.playbook(playbookId),
    staleTime: 0,
  });
  const source = useQuery({
    queryKey: ["document", playbook.data?.document_id],
    queryFn: () => api.document(playbook.data!.document_id),
    enabled: !!playbook.data,
  });
  const error = playbook.error ?? source.error;
  if (error && (!playbook.data || !source.data))
    return (
      <section className="message" role="alert">
        <h1>Review unavailable</h1>
        <p>{error.message}</p>
        <Button
          onClick={() => {
            void playbook.refetch();
            void source.refetch();
          }}
        >
          Retry
        </Button>
      </section>
    );
  if (!playbook.data || !source.data)
    return (
      <p className="message" role="status">
        Loading the pinned source and rules…
      </p>
    );
  return (
    <ReviewWorkspace
      key={playbook.data.id}
      playbook={playbook.data}
      document={source.data}
      scenario={params.get("scenario")}
    />
  );
}
