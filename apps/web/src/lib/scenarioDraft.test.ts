import { describe, expect, it } from "vitest";
import { newFact, readFacts, factKind } from "./scenarioDraft";
describe("authored fact values", () => {
  it("suggests scalar types for membership operands without coercing mixed lists", () => {
    expect(factKind([1, 2])).toBe("number");
    expect(factKind([true, false])).toBe("boolean");
    expect(factKind(["rain", "wind"])).toBe("text");
    expect(factKind([1, "1"])).toBe("text");
    expect(factKind([])).toBe("text");
    expect(factKind(false)).toBe("boolean");
    expect(factKind(0)).toBe("number");
  });
  it("preserves false, zero and quoted text as distinct scalar types", () => {
    const facts = readFacts([
      { ...newFact("count"), value: "0" },
      { ...newFact("flag", "boolean"), value: "false" },
      { ...newFact("text", "text"), value: "false" },
    ]);
    expect(facts).toEqual({ count: 0, flag: false, text: "false" });
  });
  it("rejects omitted numbers, nonfinite values and duplicate trimmed keys", () => {
    for (const value of ["", "Infinity", "NaN", "1e999"])
      expect(() => readFacts([{ ...newFact("count"), value }])).toThrow();
    expect(() =>
      readFacts([
        { ...newFact("count"), value: "1" },
        { ...newFact(" count "), value: "2" },
      ]),
    ).toThrow(/unique/);
  });
  it("treats prototype-like fact names as data", () => {
    const facts = readFacts([
      { ...newFact("__proto__", "text"), value: "example" },
    ]);
    expect(Object.hasOwn(facts, "__proto__")).toBe(true);
    expect(facts.__proto__).toBe("example");
    expect(Object.getPrototypeOf(facts)).toBe(null);
  });
});
