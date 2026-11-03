import { useState } from "react";
import { Button } from "../../components/ui/button";
import type { PolicyNode } from "../../lib/api";
export function StepRemoval({
  node,
  nodes,
  onRemove,
}: {
  node: PolicyNode;
  nodes: PolicyNode[];
  onRemove: (replacement: string) => void;
}) {
  const [replacement, setReplacement] = useState(
    nodes.find((node) => node.type === "end")!.id,
  );
  return (
    <details className="step-removal">
      <summary>Remove this step from the draft revision</summary>
      <p>
        Its incoming paths will continue to the step you choose. Other steps
        stay in the model; validation will flag any that become unreachable.
      </p>
      <label>
        Replace incoming paths with
        <select
          aria-label="Replace incoming paths with"
          value={replacement}
          onChange={(event) => setReplacement(event.target.value)}
        >
          {nodes
            .filter((item) => item.id !== node.id)
            .map((item) => (
              <option key={item.id} value={item.id}>
                {item.label}
              </option>
            ))}
        </select>
      </label>
      <Button
        type="button"
        variant="outline"
        onClick={() => onRemove(replacement)}
      >
        Remove step: {node.label}
      </Button>
    </details>
  );
}
