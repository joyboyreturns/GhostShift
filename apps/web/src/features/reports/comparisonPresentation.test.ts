import { expect, it } from "vitest";
import { firstDecisionDifference } from "./comparisonPresentation";
import type { SessionReport } from "../../lib/api";
const choice: SessionReport["decisions"][number] = {
  node_id: "delivery",
  node_label: "Delivery",
  choice_id: "escalate",
  choice_label: "Escalate",
  outcome: "modeled_match",
  source_refs: [],
  evidence_status: "uncited",
  reviewed_support: false,
};
it("distinguishes a changed choice from a proposal reaching a previously blocked decision", () => {
  expect(
    firstDecisionDifference(
      { decisions: [choice] },
      { decisions: [{ ...choice }] },
    ),
  ).toBeUndefined();
  expect(
    firstDecisionDifference(
      { decisions: [choice] },
      { decisions: [{ ...choice, outcome: "deviation" }] },
    )?.right?.outcome,
  ).toBe("deviation");
  const added = {
    ...choice,
    node_id: "weather",
    choice_id: "pause",
    choice_label: "Pause",
  };
  expect(
    firstDecisionDifference(
      { decisions: [choice] },
      { decisions: [choice, added] },
    ),
  ).toEqual({ left: undefined, right: added });
});
