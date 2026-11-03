import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "react-router-dom";
import { policyApi } from "../lib/api";
import { Button } from "../components/ui/button";
import { operatorLabels } from "../features/simulation/presentation";

export function ProposalDetail() {
  const { proposalId = "" } = useParams();
  const navigate = useNavigate();
  const [consent, setConsent] = useState(false);
  const query = useQuery({
    queryKey: ["proposal", proposalId],
    queryFn: () => policyApi.proposal(proposalId),
  });
  const rehearse = useMutation({
    mutationFn: () => policyApi.rehearse(proposalId),
    onSuccess: (result) => navigate(`/simulation/${result.id}`),
  });
  if (query.isPending)
    return (
      <p className="message" role="status">
        Restoring saved proposal…
      </p>
    );
  if (query.error)
    return (
      <section className="message" role="alert">
        <h1>Proposal unavailable</h1>
        <p>{query.error.message}</p>
        <Button onClick={() => void query.refetch()}>Retry</Button>
      </section>
    );
  const proposal = query.data;
  return (
    <article className="review-page">
      <span className="eyebrow">Saved proposed resolution</span>
      <h1>Test the change before you trust it.</h1>
      <span className="badge amber">Unapproved · review pending</span>
      <h2>{proposal.rationale}</h2>
      {proposal.choices.map((choice) => (
        <section className="review-rule" key={choice.id}>
          <h3>{choice.label}</h3>
          <ul>
            {choice.conditions.map((condition, index) => (
              <li key={index}>
                {condition.field} {operatorLabels[condition.operator]}{" "}
                {JSON.stringify(condition.value)}
              </li>
            ))}
          </ul>
          <p>
            {choice.evidence_status === "uncited"
              ? "Uncited proposed rule"
              : "Existing source citation; no approval implied"}
          </p>
        </section>
      ))}
      <p>
        Rehearsal reuses the original scenario, seed and prior user decisions.
        All events are recomputed under a separate draft policy context.
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
        <Link to={`/simulation/${proposal.session_id}`}>Original run</Link>
        <Link to={`/review/${proposal.proposed_playbook_version_id}`}>
          Review & create a source-supported revision
        </Link>
      </div>
      {rehearse.error && <p role="alert">{rehearse.error.message}</p>}
    </article>
  );
}
