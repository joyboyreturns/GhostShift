import type React from "react";
import { useMemo } from "react";
import {
  Background,
  Controls,
  MarkerType,
  ReactFlow,
  type Node,
  type Edge,
} from "@xyflow/react";
import type { Playbook } from "../../lib/api";
import "@xyflow/react/dist/style.css";

export function PolicyGraph({
  playbook,
  selectedId,
  onSelect,
}: {
  playbook: Playbook;
  selectedId?: string;
  onSelect: (id: string) => void;
}) {
  const { nodes, edges } = useMemo(() => {
    const nodes: Node[] = playbook.graph.nodes.map((node, index) => ({
      id: node.id,
      position: { x: index % 2 === 0 ? 65 : 235, y: index * 150 + 30 },
      data: {
        label: (
          <>
            <small>
              {String(index + 1).padStart(2, "0")} / {node.type.toUpperCase()}
            </small>
            <strong>{node.label}</strong>
          </>
        ),
      },
      selected: selectedId === node.id,
      ariaLabel: node.label,
      className: `policy-node ${node.type}`,
    }));
    const edges: Edge[] = playbook.graph.nodes.flatMap((node) => {
      const destinations = [
        ...new Set(node.choices.map((choice) => choice.destination)),
      ];
      return [
        ...(node.next_node
          ? [
              {
                id: `${node.id}-next`,
                source: node.id,
                target: node.next_node,
                markerEnd: { type: MarkerType.ArrowClosed },
              },
            ]
          : []),
        ...destinations.map((destination) => {
          const choices = node.choices.filter(
            (choice) => choice.destination === destination,
          );
          return {
            id: JSON.stringify([node.id, "choices", destination]),
            source: node.id,
            target: destination,
            label:
              choices.length === 1
                ? choices[0].label
                : `${choices.length} choices · inspect rule`,
            ariaLabel: choices.map((choice) => choice.label).join("; "),
            markerEnd: { type: MarkerType.ArrowClosed },
            style: { stroke: "#8b7bc4" },
          };
        }),
      ];
    });
    return { nodes, edges };
  }, [playbook, selectedId]);
  return (
    <>
      <div className="node-shortcuts" aria-label="Select a rule">
        {playbook.graph.nodes.map((node) => (
          <button
            key={node.id}
            aria-pressed={selectedId === node.id}
            onClick={() => onSelect(node.id)}
          >
            {node.label}
          </button>
        ))}
      </div>
      <div className="graph-canvas" aria-label="Interactive playbook graph">
        <ReactFlow
          key={playbook.id}
          nodes={nodes}
          edges={edges}
          onNodeClick={(_: React.MouseEvent, node: Node) => onSelect(node.id)}
          nodesDraggable={false}
          nodesConnectable={false}
          fitView
          minZoom={0.3}
          maxZoom={1.5}
          colorMode="dark"
        >
          <Background color="#3a2f5e" gap={24} size={1.4} />
          <Controls showInteractive={false} />
        </ReactFlow>
      </div>
    </>
  );
}
