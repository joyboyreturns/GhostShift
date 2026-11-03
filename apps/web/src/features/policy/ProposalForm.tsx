import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import { policyApi, type SimulationSession } from "../../lib/api";
import { Button } from "../../components/ui/button";
import { ChoiceEditor } from "./ChoiceEditor";

export function ProposalForm({ session }: { session: SimulationSession }) {
  const navigate = useNavigate();
  const cache = useQueryClient();
  const nodes = session.result.input_snapshot.graph.nodes;
  const node = nodes.find((node) => node.id === session.current_node_id)!;
  const [choices, setChoices] = useState(node.choices);
  const [rationale, setRationale] = useState("");
  const [consent, setConsent] = useState(false);
  const save = useMutation({
    mutationFn: () =>
      policyApi.propose(session.id, session.revision, rationale, choices),
    onSuccess: () => {
      void cache.invalidateQueries({ queryKey: ["library"] });
    },
  });
  const rehearse = useMutation({
    mutationFn: () => policyApi.rehearse(save.data!.id),
    onSuccess: (result) => {
      cache.setQueryData(["session", result.id], result);
      void cache.invalidateQueries({ queryKey: ["library"] });
      void cache.invalidateQueries({ queryKey: ["replay-runs"] });
      void cache.invalidateQueries({ queryKey: ["incident-branches"] });
      navigate(`/simulation/${result.id}`);
    },
  });
  return (
    <section className="panel report-section proposal-section">
      <span className="eyebrow">Human proposal / No policy authority</span>
      <h2>Test a proposed resolution</h2>
      <p>
        Revise the choices at “{node.label}”. Changed choices become uncited
        assumptions. The original source and run stay intact.
      </p>
      {save.data ? (
        <div aria-live="polite">
          <h3>Proposal saved · awaiting review</h3>
          <p>{save.data.rationale}</p>
          <p className="muted">
            Rehearsal reuses prior decisions and recomputes the scenario under
            the proposed policy. It does not approve the rule.
          </p>
          <label className="consent">
            <input
              type="checkbox"
              checked={consent}
              onChange={(event) => setConsent(event.target.checked)}
            />
            I understand this proposal is unapproved.
          </label>
          <div className="session-actions">
            <Button
              disabled={!consent || rehearse.isPending}
              onClick={() => rehearse.mutate()}
            >
              {rehearse.isPending ? "Recomputing…" : "Rehearse proposal"}
            </Button>
            <Link
              to={`/review/${save.data.proposed_playbook_version_id}?scenario=${session.scenario_id}`}
            >
              Inspect proposed version
            </Link>
          </div>
        </div>
      ) : (
        <form
          onSubmit={(event) => {
            event.preventDefault();
            save.mutate();
          }}
        >
          <label>
            Reason for the change
            <textarea
              required
              maxLength={2000}
              value={rationale}
              onChange={(event) => setRationale(event.target.value)}
              rows={3}
            />
          </label>
          <p className="muted">
            For a focused experiment, add a choice matching these exact facts.
            Enter the action yourself; this does not create a general policy.
          </p>
          <Button
            type="button"
            variant="outline"
            disabled={
              choices.length >= 50 ||
              Object.keys(session.result.final_facts).length === 0 ||
              Object.keys(session.result.final_facts).length > 20
            }
            onClick={() =>
              setChoices((previous) => [
                ...previous,
                {
                  id: `proposal-${crypto.randomUUID()}`,
                  label: "",
                  destination: nodes.find((node) => node.type === "end")!.id,
                  conditions: Object.entries(session.result.final_facts).map(
                    ([field, value]) => ({ field, operator: "eq", value }),
                  ),
                  source_refs: [],
                  evidence_status: "uncited",
                },
              ])
            }
          >
            Add choice for current facts
          </Button>
          <details className="existing-proposal-choices">
            <summary>
              Inspect or edit the existing {node.choices.length} choices
            </summary>
            <ChoiceEditor
              choices={choices.filter((choice) =>
                node.choices.some((original) => original.id === choice.id),
              )}
              onChange={(existing) =>
                setChoices([
                  ...existing,
                  ...choices.filter(
                    (choice) =>
                      !node.choices.some(
                        (original) => original.id === choice.id,
                      ),
                  ),
                ])
              }
              nodes={nodes}
            />
          </details>
          {choices.some(
            (choice) =>
              !node.choices.some((original) => original.id === choice.id),
          ) && (
            <>
              <h3>Your proposed choices · uncited assumptions</h3>
              <ChoiceEditor
                choices={choices.filter(
                  (choice) =>
                    !node.choices.some((original) => original.id === choice.id),
                )}
                onChange={(added) =>
                  setChoices([
                    ...choices.filter((choice) =>
                      node.choices.some(
                        (original) => original.id === choice.id,
                      ),
                    ),
                    ...added,
                  ])
                }
                nodes={nodes}
              />
            </>
          )}
          <p className="muted">
            Review the action, exact-fact conditions and destination before
            saving. This experiment covers these inputs only; it does not
            establish a general policy.
          </p>
          <Button disabled={save.isPending || !rationale.trim()}>
            {save.isPending ? "Saving…" : "Save unapproved proposal"}
          </Button>
        </form>
      )}
      {(save.error ?? rehearse.error) && (
        <p role="alert">{(save.error ?? rehearse.error)?.message}</p>
      )}
    </section>
  );
}
