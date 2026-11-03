import { afterEach, describe, expect, it, vi } from "vitest";
import { catalogSchema, playbookSchema, replaySchema, request } from "./api";

afterEach(() => vi.unstubAllGlobals());

describe("request recovery", () => {
  it("explains an offline save without retrying or losing its payload", async () => {
    const fetch = vi.fn().mockRejectedValue(new TypeError("Failed to fetch"));
    vi.stubGlobal("fetch", fetch);
    await expect(
      request("/documents", catalogSchema, {
        method: "POST",
        body: "saved input",
      }),
    ).rejects.toThrow("check the Library");
    expect(fetch).toHaveBeenCalledExactlyOnceWith("/api/documents", {
      method: "POST",
      body: "saved input",
    });
  });

  it("keeps intentional cancellation distinct from a connection failure", async () => {
    const error = new DOMException("Cancelled", "AbortError");
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(error));
    await expect(request("/demo", catalogSchema)).rejects.toBe(error);
  });

  it("handles an HTML gateway error without exposing its contents", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          new Response("<h1>private proxy diagnostics</h1>", { status: 502 }),
        ),
    );
    await expect(request("/demo", catalogSchema)).rejects.toThrow("(502)");
    await expect(request("/demo", catalogSchema)).rejects.not.toThrow(
      "private proxy",
    );
  });

  it.each(["", "not json"])(
    "handles unreadable successful responses: %j",
    async (body) => {
      vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(body)));
      await expect(request("/demo", catalogSchema)).rejects.toThrow(
        "unreadable response",
      );
    },
  );

  it("rejects incompatible success data without exposing the payload", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(Response.json({ demos: "private content" })),
    );
    await expect(request("/demo", catalogSchema)).rejects.toThrow(
      "unexpected data",
    );
  });

  it("preserves actionable server validation details", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        Response.json(
          {
            error: {
              message: "Invalid input",
              details: [
                { location: ["body", "title"], message: "Title is required" },
              ],
            },
          },
          { status: 422 },
        ),
      ),
    );
    await expect(request("/documents", catalogSchema)).rejects.toThrow(
      "Invalid input · title: Title is required",
    );
  });

  it("returns validated successful data", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(Response.json({ demos: [] })),
    );
    await expect(request("/demo", catalogSchema)).resolves.toEqual({
      demos: [],
    });
  });
});

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
