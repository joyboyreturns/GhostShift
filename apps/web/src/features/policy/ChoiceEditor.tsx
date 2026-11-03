import { useState } from "react";
import {
  condition,
  type PolicyChoice,
  type PolicyNode,
  type SourceDocument,
} from "../../lib/api";
import { Button } from "../../components/ui/button";
import { operatorLabels } from "../simulation/presentation";

function Operand({
  value,
  onChange,
}: {
  value: PolicyChoice["conditions"][number]["value"];
  onChange: (value: PolicyChoice["conditions"][number]["value"]) => void;
}) {
  const serialized = JSON.stringify(value);
  const [draft, setDraft] = useState({
    committed: serialized,
    text: serialized,
  });
  if (draft.committed !== serialized)
    setDraft({ committed: serialized, text: serialized });
  const text = draft.committed === serialized ? draft.text : serialized;
  return (
    <label>
      Comparison value
      <input
        required
        value={text}
        aria-label="Comparison value"
        onChange={(event) => {
          try {
            const parsed: unknown = JSON.parse(event.target.value);
            const result = condition.shape.value.safeParse(parsed);
            if (!result.success)
              throw new Error(
                "Use a number, true/false, quoted text, or a list.",
              );
            event.target.setCustomValidity("");
            setDraft({
              committed: JSON.stringify(result.data),
              text: event.target.value,
            });
            onChange(result.data);
          } catch {
            setDraft({ committed: serialized, text: event.target.value });
            event.target.setCustomValidity(
              "Use a number, true/false, quoted text, or a list.",
            );
          }
        }}
      />
      <small>Examples: 70, true, "rain", ["rain", "wind"]</small>
    </label>
  );
}

export function ChoiceEditor({
  choices,
  onChange,
  nodes,
  source,
}: {
  choices: PolicyChoice[];
  onChange: (choices: PolicyChoice[]) => void;
  nodes: PolicyNode[];
  source?: SourceDocument;
}) {
  function change(index: number, patch: Partial<PolicyChoice>) {
    onChange(
      choices.map((choice, i) =>
        i === index ? { ...choice, ...patch } : choice,
      ),
    );
  }
  return (
    <div className="choice-editor">
      {choices.map((choice, index) => (
        <fieldset key={choice.id} className="policy-choice">
          <legend>Choice {index + 1}</legend>
          <label>
            Action label
            <input
              required
              maxLength={300}
              value={choice.label}
              onChange={(event) => change(index, { label: event.target.value })}
            />
          </label>
          <label>
            Continue to
            <select
              value={choice.destination}
              onChange={(event) =>
                change(index, { destination: event.target.value })
              }
            >
              {nodes.map((node) => (
                <option key={node.id} value={node.id}>
                  {node.label}
                </option>
              ))}
            </select>
          </label>
          <p className="muted">All conditions must match.</p>
          {choice.conditions.map((item, conditionIndex) => (
            <div className="condition-editor" key={conditionIndex}>
              <label>
                Fact name
                <input
                  required
                  maxLength={100}
                  value={item.field}
                  onChange={(event) =>
                    change(index, {
                      conditions: choice.conditions.map((existing, i) =>
                        i === conditionIndex
                          ? { ...existing, field: event.target.value }
                          : existing,
                      ),
                    })
                  }
                />
              </label>
              <label>
                Comparison
                <select
                  aria-label="Comparison"
                  value={item.operator}
                  onChange={(event) =>
                    change(index, {
                      conditions: choice.conditions.map((existing, i) =>
                        i === conditionIndex
                          ? {
                              ...existing,
                              operator: condition.shape.operator.parse(
                                event.target.value,
                              ),
                            }
                          : existing,
                      ),
                    })
                  }
                >
                  {condition.shape.operator.options.map((operator) => (
                    <option key={operator} value={operator}>
                      {operatorLabels[operator]}
                    </option>
                  ))}
                </select>
              </label>
              <Operand
                value={item.value}
                onChange={(value) =>
                  change(index, {
                    conditions: choice.conditions.map((existing, i) =>
                      i === conditionIndex ? { ...existing, value } : existing,
                    ),
                  })
                }
              />
              <Button
                type="button"
                variant="outline"
                disabled={choice.conditions.length === 1}
                onClick={() =>
                  change(index, {
                    conditions: choice.conditions.filter(
                      (_, i) => i !== conditionIndex,
                    ),
                  })
                }
              >
                Remove condition
              </Button>
            </div>
          ))}
          <Button
            type="button"
            variant="outline"
            disabled={choice.conditions.length >= 20}
            onClick={() =>
              change(index, {
                conditions: [
                  ...choice.conditions,
                  { field: "", operator: "eq", value: 0 },
                ],
              })
            }
          >
            Add condition
          </Button>
          {source && (
            <fieldset className="citation-picker">
              <legend>Evidence for this choice</legend>
              {source.segments.map((segment) => (
                <label className="consent" key={segment.id}>
                  <input
                    type="checkbox"
                    checked={choice.source_refs.includes(segment.id)}
                    onChange={(event) => {
                      const refs = event.target.checked
                        ? [...choice.source_refs, segment.id]
                        : choice.source_refs.filter(
                            (ref) => ref !== segment.id,
                          );
                      change(index, {
                        source_refs: refs,
                        evidence_status: refs.length ? "cited" : "uncited",
                      });
                    }}
                  />
                  §{segment.ordinal} {segment.text}
                </label>
              ))}
            </fieldset>
          )}
          <Button
            type="button"
            variant="outline"
            disabled={choices.length === 1}
            onClick={() => onChange(choices.filter((_, i) => i !== index))}
          >
            Remove choice
          </Button>
        </fieldset>
      ))}
      <Button
        type="button"
        variant="outline"
        disabled={choices.length >= 50}
        onClick={() =>
          onChange([
            ...choices,
            {
              id: `choice-${crypto.randomUUID()}`,
              label: "",
              destination:
                nodes.find((node) => node.type === "end")?.id ?? nodes[0].id,
              conditions: [{ field: "", operator: "eq", value: 0 }],
              source_refs: [],
              evidence_status: "uncited",
            },
          ])
        }
      >
        Add choice
      </Button>
    </div>
  );
}
