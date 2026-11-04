import { test, expect } from "@playwright/test";
import {
  documentSchema,
  playbookSchema,
  scenarioSchema,
} from "../../src/lib/api";

test("membership facts retain their types and scenario saves preserve and lock submitted entries", async ({
  page,
  request,
}) => {
  const source = documentSchema.parse(
    await (
      await request.post("/api/documents", {
        data: {
          title: "Fictional membership procedure",
          content: "Proceed for an available team of two or three people.",
        },
      })
    ).json(),
  );
  const version = playbookSchema.parse(
    await (
      await request.post("/api/playbooks", {
        data: {
          document_id: source.id,
          title: source.title,
          graph: {
            nodes: [
              { id: "start", label: "Begin", type: "start", next_node: "team" },
              {
                id: "team",
                label: "Is the team ready?",
                type: "decision",
                choices: [
                  {
                    id: "proceed",
                    label: "Proceed",
                    destination: "end",
                    conditions: [
                      { field: "available", operator: "in", value: [true] },
                      { field: "people", operator: "in", value: [2, 3] },
                    ],
                    source_refs: [source.segments[0].id],
                    evidence_status: "cited",
                  },
                ],
              },
              { id: "end", label: "Complete", type: "end" },
            ],
          },
        },
      })
    ).json(),
  );
  await page.goto(`/scenarios/new?playbook=${version.id}`);
  await page
    .getByLabel("Scenario title", { exact: true })
    .fill("Fictional ready team");
  const available = page
    .locator(".fact-row")
    .filter({ has: page.locator('input[value="available"]') });
  const people = page
    .locator(".fact-row")
    .filter({ has: page.locator('input[value="people"]') });
  await expect(available.getByLabel("Value type", { exact: true })).toHaveValue(
    "boolean",
  );
  await expect(people.getByLabel("Value type", { exact: true })).toHaveValue(
    "number",
  );
  await available
    .getByLabel("Fact value", { exact: true })
    .selectOption("true");
  await people.getByLabel("Fact value", { exact: true }).fill("2");
  await page.getByRole("checkbox").check();
  await page.route("**/api/scenarios", (route) =>
    route.fulfill({ status: 503, body: "unavailable" }),
  );
  await page
    .getByRole("button", { name: "Save scenario", exact: true })
    .click();
  await expect(page.getByRole("alert")).toContainText(
    "Your entries are preserved",
  );
  await expect(people.getByLabel("Fact value", { exact: true })).toHaveValue(
    "2",
  );
  await page.unroute("**/api/scenarios");
  let release = () => {};
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route("**/api/scenarios", async (route) => {
    await gate;
    await route.continue();
  });
  try {
    await page
      .getByRole("button", { name: "Save scenario", exact: true })
      .click();
    await expect(
      page.getByLabel("Scenario title", { exact: true }),
    ).toBeDisabled();
    await expect(
      people.getByLabel("Fact value", { exact: true }),
    ).toBeDisabled();
    await expect(
      page.getByRole("button", { name: "Add scheduled change", exact: true }),
    ).toBeDisabled();
  } finally {
    release();
  }
  await expect(page).toHaveURL(/\/simulation\?scenario=/);
  const id = new URL(page.url()).searchParams.get("scenario");
  const saved = scenarioSchema.parse(
    await (await request.get(`/api/scenarios/${id}`)).json(),
  );
  expect(saved.initial_facts).toEqual({ available: true, people: 2 });
  await page.getByRole("checkbox").check();
  await page
    .getByRole("button", { name: "Start rehearsal", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Choose: Proceed", exact: true }),
  ).toBeVisible();
});

test("a draft cannot silently save against an older source while source edits are unsaved", async ({
  page,
  request,
}) => {
  const source = documentSchema.parse(
    await (
      await request.post("/api/documents", {
        data: {
          title: "Fictional source save boundary",
          content: "Notify the team.",
        },
      })
    ).json(),
  );
  const draft = playbookSchema.parse(
    await (
      await request.post(`/api/documents/${source.id}/draft`, {
        data: { title: source.title },
      })
    ).json(),
  );
  await page.goto(`/review/${draft.id}?edit=1`);
  await page.getByText("Revise the source document", { exact: true }).click();
  const text = page.getByRole("textbox", {
    name: "Revised procedure",
    exact: true,
  });
  const saveDraft = page.getByRole("button", {
    name: "Save draft revision",
    exact: true,
  });
  await text.fill("Notify the operations lead.");
  await expect(saveDraft).toBeDisabled();
  await expect(page.getByRole("status")).toContainText(
    "Source edits are not saved",
  );
  await page
    .getByRole("button", { name: "Discard unsaved source edits", exact: true })
    .click();
  await expect(text).toHaveValue(source.content);
  await expect(saveDraft).toBeEnabled();
  await text.fill("Notify the operations lead.");
  await page.route("**/api/documents", (route) =>
    route.fulfill({ status: 503, body: "unavailable" }),
  );
  await page
    .getByRole("button", { name: "Save revised source snapshot", exact: true })
    .click();
  await expect(page.getByRole("alert")).toContainText("503");
  await expect(text).toHaveValue("Notify the operations lead.");
  await expect(saveDraft).toBeDisabled();
  await page.unroute("**/api/documents");
  let release = () => {};
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route("**/api/documents", async (route) => {
    await gate;
    await route.continue();
  });
  try {
    await page
      .getByRole("button", {
        name: "Save revised source snapshot",
        exact: true,
      })
      .click();
    await expect(text).toBeDisabled();
    await expect(saveDraft).toBeDisabled();
    await expect(
      page.getByRole("button", {
        name: "Add action before completion",
        exact: true,
      }),
    ).toBeDisabled();
  } finally {
    release();
  }
  await expect(
    page.getByText(
      "New source saved. Select its supporting sections for each rule.",
    ),
  ).toBeVisible();
  await expect(saveDraft).toBeEnabled();
  await page
    .getByRole("button", { name: "Add action before completion", exact: true })
    .click();
  await page
    .getByLabel("Action step label", { exact: true })
    .fill("Notify operations lead");
  await page
    .getByRole("group", {
      name: "Action evidence: Notify operations lead",
      exact: true,
    })
    .getByRole("checkbox")
    .check();
  await saveDraft.click();
  await expect(page).not.toHaveURL(new RegExp(`/review/${draft.id}`));
  const version = playbookSchema.parse(
    await (
      await request.get(
        `/api/playbooks/${new URL(page.url()).pathname.split("/").at(-1)}`,
      )
    ).json(),
  );
  expect(version.document_id).not.toBe(source.id);
  expect(
    documentSchema.parse(
      await (await request.get(`/api/documents/${source.id}`)).json(),
    ),
  ).toEqual(source);
});

test("Source Studio retries a failed scenario list without requiring a page reload", async ({
  page,
}) => {
  await page.route("**/api/playbooks/night-market-v1/scenarios", (route) =>
    route.fulfill({ status: 503, body: "unavailable" }),
  );
  await page.goto("/studio");
  await expect(
    page.getByRole("heading", {
      name: "Source Studio couldn’t load",
      exact: true,
    }),
  ).toBeVisible();
  await page.unroute("**/api/playbooks/night-market-v1/scenarios");
  await page.getByRole("button", { name: "Retry", exact: true }).click();
  await expect(page.getByRole("heading", { level: 1 })).toContainText(
    "Every rule starts with evidence",
  );
  await expect(page.locator(".react-flow__node")).not.toHaveCount(0);
});

test("missing records and invalid routes offer visible recovery", async ({
  page,
}) => {
  for (const path of [
    "/sources/missing-quality-record",
    "/review/missing-quality-record",
    "/replay/missing-quality-record",
    "/simulation/missing-quality-record",
    "/simulation/missing-quality-record/report",
  ]) {
    await page.goto(path);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Retry", exact: true }),
    ).toBeVisible();
    await expect(
      page.getByRole("link", { name: "Library", exact: true }),
    ).toBeVisible();
  }
  await page.goto("/no-such-quality-page");
  await expect(
    page.getByRole("heading", { name: "We couldn’t find this page." }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Return home", exact: true }).click();
  await expect(page.getByRole("heading", { level: 1 })).toContainText(
    "Every playbook",
  );
});
