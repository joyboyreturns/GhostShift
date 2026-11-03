import { useInfiniteQuery, useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { GitFork } from "lucide-react";
import {
  simulationApi,
  workspaceApi,
  type SimulationSession,
} from "../../lib/api";
import { relatedBranches } from "./narrative";
import { statusLabels } from "../simulation/presentation";
import { Button } from "../../components/ui/button";

export function BranchMap({ session }: { session: SimulationSession }) {
  const runs = useInfiniteQuery({
    queryKey: ["incident-branches", session.id, session.revision],
    initialPageParam: 0,
    queryFn: ({ pageParam }) => workspaceApi.library("", pageParam, 50),
    getNextPageParam: (page) =>
      page.offset + page.limit < page.totals.sessions
        ? page.offset + page.limit
        : undefined,
    staleTime: 0,
  });
  const parent = useQuery({
    queryKey: ["session", session.parent_session_id],
    queryFn: () => simulationApi.session(session.parent_session_id!),
    enabled: !!session.parent_session_id,
  });
  const loaded = runs.data?.pages.flatMap((page) => page.sessions) ?? [];
  const related = relatedBranches(session, [
    ...loaded,
    ...(parent.data ? [parent.data] : []),
  ]);
  return (
    <section className="panel branch-map" aria-labelledby="branch-map-heading">
      <header className="panel-heading">
        <div>
          <span className="eyebrow">
            <GitFork size={14} aria-hidden="true" /> Preserved timelines
          </span>
          <h2 id="branch-map-heading">Every alternate has an origin.</h2>
        </div>
        <Link to={`/replay/${session.id}`}>Open Replay Lab ↗</Link>
      </header>
      <p className="muted">
        Recorded parent links connect these runs. A checkpoint fork keeps its
        policy; a proposed-policy rehearsal recomputes the scenario under an
        unapproved version.
      </p>
      <ol className="branch-list" aria-label="Run relationships">
        {related.map((run) => (
          <li
            key={run.id}
            className={run.id === session.id ? "branch-current" : ""}
          >
            <span className="branch-dot" aria-hidden="true" />
            <div>
              <span className="eyebrow">
                {run.id === session.id
                  ? "Current run"
                  : run.id === session.parent_session_id
                    ? "Parent run"
                    : "Related alternate"}
              </span>
              <Link
                to={`/simulation/${run.id}`}
                aria-current={run.id === session.id ? "page" : undefined}
              >
                {run.id.slice(0, 8)} · {statusLabels[run.status]}
              </Link>
              <p>
                {run.parent_session_id ? (
                  <>
                    From{" "}
                    <Link to={`/simulation/${run.parent_session_id}`}>
                      {run.parent_session_id.slice(0, 8)}
                    </Link>
                    {" · "}
                    {run.id === session.id
                      ? session.proposal_id
                        ? "Unapproved proposed policy"
                        : "Checkpoint fork · same policy"
                      : related.find(
                            (other) => other.id === run.parent_session_id,
                          )?.playbook_version_id === run.playbook_version_id
                        ? "Checkpoint fork · same policy"
                        : related.some(
                              (other) => other.id === run.parent_session_id,
                            )
                          ? "Different policy · inspect run for proposal"
                          : "Parent details not loaded · inspect run"}
                  </>
                ) : (
                  "Original run · no parent"
                )}
              </p>
              {run.parent_session_id && (
                <Link
                  to={`/reports/compare?${new URLSearchParams({ left: run.parent_session_id, right: run.id })}`}
                >
                  Compare this alternate ↗
                </Link>
              )}
            </div>
          </li>
        ))}
      </ol>
      {runs.isPending && <p role="status">Loading recorded branches…</p>}
      {(runs.error ?? parent.error) && (
        <p role="alert">
          Some relationships could not load:{" "}
          {(runs.error ?? parent.error)?.message}{" "}
          <button
            className="text-action"
            onClick={() => {
              void runs.refetch();
              if (session.parent_session_id) void parent.refetch();
            }}
          >
            Retry relationships
          </button>
        </p>
      )}
      {runs.hasNextPage && (
        <Button
          variant="outline"
          disabled={runs.isFetchingNextPage}
          onClick={() => void runs.fetchNextPage()}
        >
          Load older runs
        </Button>
      )}
      <p className="muted">
        Showing relationships among {loaded.length} loaded library runs
        {runs.hasNextPage ? "; older alternates may not be shown yet" : ""}.
        Your current run and available parent are included.
      </p>
    </section>
  );
}
