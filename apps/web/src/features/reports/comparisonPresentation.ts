import type { SessionReport } from "../../lib/api";

export function firstDecisionDifference(
  left: Pick<SessionReport, "decisions">,
  right: Pick<SessionReport, "decisions">,
) {
  const length = Math.max(left.decisions.length, right.decisions.length);
  for (let index = 0; index < length; index++) {
    const a = left.decisions[index];
    const b = right.decisions[index];
    if (
      !a ||
      !b ||
      a.node_id !== b.node_id ||
      a.choice_id !== b.choice_id ||
      a.choice_label !== b.choice_label ||
      a.outcome !== b.outcome
    ) {
      return { left: a, right: b };
    }
  }
  return undefined;
}
