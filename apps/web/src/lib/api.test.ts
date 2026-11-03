import { describe, expect, it } from "vitest";
import { catalogSchema, playbookSchema, replaySchema } from "./api";

describe("API boundary validation", () => {
  it("rejects success-shaped payloads missing actual graph data", () => {
    expect(playbookSchema.safeParse({ status: "ok" }).success).toBe(false);
  });
  it("accepts an empty catalog for the empty UI state", () => {
    expect(catalogSchema.parse({ demos: [] }).demos).toEqual([]);
  });
  it("does not accept an unverified replay as a successful verification", () => {
    expect(
      replaySchema.safeParse({
        session_id: "run",
        verified: false,
        event_count: 3,
        last_state_hash: "hash",
        engine_version: "ghostshift-engine-1",
      }).success,
    ).toBe(false);
  });
  it("rejects an unknown catalog availability status", () => {
    expect(
      catalogSchema.safeParse({
        demos: [
          {
            id: "x",
            title: "x",
            description: "x",
            document_id: "x",
            playbook_id: "x",
            scenario_id: "x",
            fictional: true,
            scenario_status: "running",
          },
        ],
      }).success,
    ).toBe(false);
  });
});
