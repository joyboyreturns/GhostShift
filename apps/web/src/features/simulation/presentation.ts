import type { RunStatus } from "../../lib/api";
export const statusLabels: Record<RunStatus, string> = {
  awaiting_decision: "Your decision",
  completed: "Rehearsal complete",
  deviation: "Completed with deviations",
  uncovered: "Uncovered decision path",
  overlap: "Potential rule overlap",
  budget_exceeded: "Traversal limit reached",
};
export function factLabel(field: string): string {
  return field
    .replaceAll("_", " ")
    .replace(/^./, (letter) => letter.toUpperCase());
}

export const operatorLabels = {
  eq: "is",
  neq: "is not",
  gt: "above",
  gte: "at least",
  lt: "below",
  lte: "at most",
  in: "is one of",
};
