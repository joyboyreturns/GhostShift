import { describe, expect, it } from "vitest";
import { insertStep, removeStep } from "./graphDraft";
import type { Playbook } from "./api";
const graph: Playbook["graph"] = {
  nodes: [
    {
      id: "start",
      type: "start",
      label: "Begin",
      next_node: "end",
      choices: [],
      source_refs: [],
    },
    {
      id: "end",
      type: "end",
      label: "Done",
      next_node: null,
      choices: [],
      source_refs: [],
    },
  ],
};
describe("human-authored graph edits", () => {
  it("inserts an uncited action without changing the saved input", () => {
    const next = insertStep(graph, "action");
    expect(graph.nodes[0].next_node).toBe("end");
    expect(next.nodes[0].next_node).toBe(next.nodes[1].id);
    expect(next.nodes[1].next_node).toBe("end");
    expect(next.nodes[1].source_refs).toEqual([]);
  });
  it("removes only the requested step and rewires incoming paths explicitly", () => {
    const next = insertStep(graph, "decision");
    const restored = removeStep(next, next.nodes[1].id, "end");
    expect(restored).toEqual(graph);
    expect(next.nodes).toHaveLength(3);
    expect(() => removeStep(next, "start", "end")).toThrow();
    expect(() => removeStep(next, next.nodes[1].id, "missing")).toThrow();
  });
});
