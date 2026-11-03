import { useId } from "react";
import { Button } from "../../components/ui/button";
import { newFact, type FactDraft } from "../../lib/scenarioDraft";
export function FactsEditor({
  rows,
  onChange,
  fields = [],
}: {
  rows: FactDraft[];
  onChange: (rows: FactDraft[]) => void;
  fields?: string[];
}) {
  const id = useId();
  function change(index: number, patch: Partial<FactDraft>) {
    onChange(rows.map((row, i) => (i === index ? { ...row, ...patch } : row)));
  }
  return (
    <div className="facts-editor">
      <datalist id={id}>
        {fields.map((field) => (
          <option value={field} key={field} />
        ))}
      </datalist>
      {rows.map((row, index) => (
        <fieldset className="fact-row" key={row.id}>
          <legend>Fact {index + 1}</legend>
          <label>
            Fact name
            <input
              required
              list={id}
              maxLength={100}
              value={row.field}
              onChange={(event) => change(index, { field: event.target.value })}
            />
          </label>
          <label>
            Value type
            <select
              aria-label="Value type"
              value={row.kind}
              onChange={(event) =>
                change(index, {
                  kind: event.target.value as FactDraft["kind"],
                  value: "",
                })
              }
            >
              <option value="number">Number</option>
              <option value="boolean">True / false</option>
              <option value="text">Text</option>
            </select>
          </label>
          <label>
            Fact value
            {row.kind === "boolean" ? (
              <select
                aria-label="Fact value"
                required
                value={row.value}
                onChange={(event) =>
                  change(index, { value: event.target.value })
                }
              >
                <option value="">Choose…</option>
                <option value="true">True</option>
                <option value="false">False</option>
              </select>
            ) : (
              <input
                required={row.kind === "number"}
                type={row.kind === "number" ? "number" : "text"}
                step="any"
                maxLength={500}
                value={row.value}
                onChange={(event) =>
                  change(index, { value: event.target.value })
                }
              />
            )}
          </label>
          <Button
            type="button"
            variant="outline"
            onClick={() => onChange(rows.filter((_, i) => i !== index))}
          >
            Remove fact
          </Button>
        </fieldset>
      ))}
      <Button
        type="button"
        variant="outline"
        disabled={rows.length >= 64}
        onClick={() => onChange([...rows, newFact()])}
      >
        Add fact
      </Button>
    </div>
  );
}
