import type { Playbook } from "./api";
type Graph = Playbook["graph"];
export function insertStep(graph: Graph, type: "decision" | "action"): Graph {
  const end = graph.nodes.find((node) => node.type === "end");
  if (!end) throw new Error("A completion step is required.");
  const id = `${type}-${crypto.randomUUID()}`;
  const nodes = graph.nodes.map((node) => ({
    ...node,
    next_node: node.next_node === end.id ? id : node.next_node,
    choices: node.choices.map((choice) => ({
      ...choice,
      destination: choice.destination === end.id ? id : choice.destination,
    })),
  }));
  nodes.splice(
    nodes.findIndex((node) => node.id === end.id),
    0,
    {
      id,
      type,
      label: type === "decision" ? "New decision" : "New action",
      source_refs: [],
      next_node: type === "action" ? end.id : null,
      choices:
        type === "decision"
          ? [
              {
                id: `choice-${crypto.randomUUID()}`,
                label: "",
                destination: end.id,
                conditions: [{ field: "", operator: "eq", value: 0 }],
                source_refs: [],
                evidence_status: "uncited",
              },
            ]
          : [],
    },
  );
  return { nodes };
}
export function removeStep(
  graph: Graph,
  id: string,
  replacement: string,
): Graph {
  const selected = graph.nodes.find((node) => node.id === id);
  if (!selected || !["action", "decision"].includes(selected.type))
    throw new Error("Only action and decision steps can be removed.");
  if (
    id === replacement ||
    !graph.nodes.some((node) => node.id === replacement)
  )
    throw new Error("Choose an existing replacement step.");
  return {
    nodes: graph.nodes
      .filter((node) => node.id !== id)
      .map((node) => ({
        ...node,
        next_node: node.next_node === id ? replacement : node.next_node,
        choices: node.choices.map((choice) => ({
          ...choice,
          destination:
            choice.destination === id ? replacement : choice.destination,
        })),
      })),
  };
}
