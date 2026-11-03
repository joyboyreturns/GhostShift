import type { Facts } from "./api";
export type FactDraft = {
  id: string;
  field: string;
  kind: "number" | "boolean" | "text";
  value: string;
};
export function newFact(
  field = "",
  kind: FactDraft["kind"] = "number",
): FactDraft {
  return { id: crypto.randomUUID(), field, kind, value: "" };
}
export function readFacts(rows: FactDraft[]): Facts {
  const result = Object.create(null) as Facts;
  for (const row of rows) {
    const field = row.field.trim();
    if (!field || Object.hasOwn(result, field))
      throw new Error("Give every fact a unique, nonblank name.");
    if (row.kind === "number") {
      if (!row.value.trim() || !Number.isFinite(Number(row.value)))
        throw new Error(`Enter a finite number for ${field}.`);
      result[field] = Number(row.value);
    } else if (row.kind === "boolean") {
      if (!["true", "false"].includes(row.value))
        throw new Error(`Choose true or false for ${field}.`);
      result[field] = row.value === "true";
    } else result[field] = row.value;
  }
  return result;
}
