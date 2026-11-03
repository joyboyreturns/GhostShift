import { test, expect } from "@playwright/test";
import { readFile } from "node:fs/promises";
import { comparisonSchema, sessionSchema } from "../../src/lib/api";

test("the flagship shift uses real events through proposal, comparison and portable evidence", async ({
  page,
  request,
}) => {
  await page.goto("/");
  await page.screenshot({
    path: test.info().outputPath("incident-home.png"),
    fullPage: true,
  });
  await page.getByRole("link", { name: "Start your shift" }).click();
  await expect(
    page.getByRole("heading", { name: "The last dry hour" }),
  ).toBeVisible();
  await expect(
    page.getByRole("region", { name: "Shift briefing" }),
  ).toContainText("Night Market operations coordinator");
  await page.screenshot({
    path: test.info().outputPath("incident-briefing.png"),
    fullPage: true,
  });
  await page.getByRole("checkbox").check();
  await page
    .getByRole("button", { name: "Start rehearsal", exact: true })
    .click();
  await expect(page).toHaveURL(/\/simulation\/[a-f0-9-]+$/);
  const parentId = new URL(page.url()).pathname.split("/").at(-1)!;
  const feed = page.getByRole("region", { name: "Dispatch log" });
  await expect(feed).toContainText("A delayed arrival needs your attention");
  await expect(feed).not.toContainText("85");
  await expect(feed.getByRole("button", { name: "Sound off" })).toHaveAttribute(
    "aria-pressed",
    "false",
  );
  await page
    .getByRole("button", {
      name: "Choose: Escalate to operations lead",
      exact: true,
    })
    .click();
  await expect(
    page.getByRole("heading", { name: "The procedure has no matching path." }),
  ).toBeVisible();
  await feed.getByRole("button", { name: "Next update" }).click();
  await feed.getByRole("button", { name: "Show all updates" }).click();
  await expect(feed).toContainText("Rain risk: 40 → 85");
  await page.evaluate(() => {
    (document.activeElement as HTMLElement)?.blur();
    window.scrollTo(0, 0);
  });
  await page.screenshot({
    path: test.info().outputPath("incident-command-room.png"),
    fullPage: true,
  });
  await expect(
    page.getByText(/The indoor-capacity guard is a modeled assumption/),
  ).toBeVisible();
  await feed.getByRole("list", { name: "Recorded incident updates" }).focus();
  await page.keyboard.press("End");
  await expect(
    feed.getByText("Rehearsal stopped", { exact: true }),
  ).toBeInViewport();
  const before = sessionSchema.parse(
    await (await request.get(`/api/sessions/${parentId}`)).json(),
  );
  await page
    .getByRole("button", { name: "Inspect conditions & history" })
    .click();
  await expect(page).toHaveURL(/view=inspect/);
  await expect(feed).toHaveCount(0);
  await page.reload();
  await expect(
    page.getByRole("button", { name: "Inspect conditions & history" }),
  ).toHaveAttribute("aria-pressed", "true");
  await page
    .getByRole("button", { name: "Incident view", exact: true })
    .click();
  await page.getByRole("link", { name: "Test a proposed rule ↓" }).click();
  const proposal = page.locator(".proposal-section");
  await proposal
    .getByLabel("Reason for the change")
    .fill("Fictional experiment for exhausted indoor capacity");
  await proposal
    .getByRole("button", { name: "Add choice for current facts", exact: true })
    .click();
  await proposal
    .locator(".policy-choice")
    .last()
    .getByLabel("Action label", { exact: true })
    .fill("Pause admission and contact venue manager");
  await proposal
    .getByRole("button", { name: "Save unapproved proposal" })
    .click();
  await proposal.getByRole("checkbox").check();
  await proposal
    .getByRole("button", { name: "Rehearse proposal", exact: true })
    .click();
  await page
    .getByRole("button", {
      name: "Choose: Pause admission and contact venue manager",
      exact: true,
    })
    .click();
  await expect(page).not.toHaveURL(new RegExp(`${parentId}$`));
  const alternateId = new URL(page.url()).pathname.split("/").at(-1)!;
  await expect(
    page.getByRole("region", { name: "Shift debrief" }),
  ).toContainText("Rehearsal complete");
  await expect(
    page.getByRole("list", { name: "Run relationships" }),
  ).toContainText("Unapproved proposed policy");
  await page
    .getByRole("button", { name: "Verify replay", exact: true })
    .click();
  await expect(
    page.getByText(/Replay verified against pinned inputs/),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Compare with parent", exact: true })
    .click();
  await expect(
    page.getByRole("region", { name: "Run comparison" }),
  ).toContainText("No choice recorded at this point");
  await expect(
    page.getByRole("region", { name: "Run comparison" }),
  ).toContainText("Pause admission and contact venue manager");
  await page
    .getByRole("link", { name: "Export parent / alternate comparison ↗" })
    .click();
  await expect(
    page.getByRole("heading", { name: "Two paths, inspected." }),
  ).toBeVisible();
  await page.locator(".report-page").screenshot({
    path: test.info().outputPath("incident-comparison.png"),
    style: ".app-header, .skip-link { visibility: hidden !important; }",
  });
  const [download] = await Promise.all([
    page.waitForEvent("download"),
    page.getByRole("link", { name: "Download comparison JSON" }).click(),
  ]);
  const path = test.info().outputPath("incident-comparison.json");
  await download.saveAs(path);
  const comparison = comparisonSchema.parse(
    JSON.parse(await readFile(path, "utf8")),
  );
  expect(comparison.left.session_id).toBe(parentId);
  expect(comparison.right.session_id).toBe(alternateId);
  expect(comparison.left.status).toBe("uncovered");
  expect(comparison.right.status).toBe("completed");
  expect(comparison.right.reviewed_supported_count).toBe(0);
  expect(comparison.right.proposals[0].review_status).toBe("pending");
  expect(
    sessionSchema.parse(
      await (await request.get(`/api/sessions/${parentId}`)).json(),
    ),
  ).toEqual(before);
});

test("incident controls remain keyboard accessible, silent and usable with reduced motion on mobile", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/simulation?scenario=customer-support");
  await expect(
    page.getByRole("heading", { name: "One request. Two answers." }),
  ).toBeVisible();
  await page.getByRole("checkbox").check();
  await page
    .getByRole("button", { name: "Start rehearsal", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "More than one rule matches." }),
  ).toBeVisible();
  const all = page.getByRole("button", { name: "Show all updates" });
  await all.focus();
  await page.keyboard.press("Enter");
  await expect(
    page.getByRole("region", { name: "Dispatch log" }),
  ).toContainText("Conflicting paths need human review");
  await expect(page.getByRole("button", { name: "Sound off" })).toHaveAttribute(
    "aria-pressed",
    "false",
  );
  await expect(page.getByTestId("segment-3")).toHaveAttribute(
    "data-highlighted",
    "true",
  );
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  const heading = page.getByRole("heading", {
    name: "Every alternate has an origin.",
  });
  const box = await heading.boundingBox();
  const intro = page.getByText("Recorded parent links connect these runs.", {
    exact: false,
  });
  const introBox = await intro.boundingBox();
  expect(box && introBox && box.y + box.height <= introBox.y).toBeTruthy();
  await page.evaluate(() => {
    (document.activeElement as HTMLElement)?.blur();
    window.scrollTo(0, 0);
  });
  await page.screenshot({
    path: test.info().outputPath("incident-mobile.png"),
    fullPage: true,
  });
});

test("a failed choice preserves the active decision and can be retried", async ({
  page,
}) => {
  await page.goto("/simulation?scenario=night-market");
  await page.getByRole("checkbox").check();
  await page
    .getByRole("button", { name: "Start rehearsal", exact: true })
    .click();
  await page.route("**/api/sessions/*/choose", async (route) =>
    route.fulfill({
      status: 409,
      contentType: "application/json",
      body: JSON.stringify({
        error: { message: "Revision conflict; reload the current run." },
      }),
    }),
  );
  await page
    .getByRole("button", {
      name: "Choose: Escalate to operations lead",
      exact: true,
    })
    .click();
  await expect(page.getByRole("alert")).toContainText("Revision conflict");
  await expect(
    page.getByRole("heading", { name: "Is the vendor late?", exact: true }),
  ).toBeVisible();
  await page.unroute("**/api/sessions/*/choose");
  await page
    .getByRole("button", {
      name: "Choose: Escalate to operations lead",
      exact: true,
    })
    .click();
  await expect(
    page.getByRole("heading", { name: "The procedure has no matching path." }),
  ).toBeVisible();
});

test("unavailable audio has a visible fallback and never blocks incident playback", async ({
  page,
}) => {
  await page.addInitScript(() => {
    Object.defineProperty(window, "AudioContext", {
      value: class {
        constructor() {
          throw new Error("Audio unavailable for this test");
        }
      },
    });
  });
  await page.goto("/simulation?scenario=customer-support");
  await page.getByRole("checkbox").check();
  await page
    .getByRole("button", { name: "Start rehearsal", exact: true })
    .click();
  await page.getByRole("button", { name: "Sound off" }).click();
  await page.getByRole("button", { name: "Next update", exact: true }).click();
  await expect(
    page.getByText(
      "Sound is unavailable in this browser. All updates remain available as text.",
    ),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "Sound off" })).toHaveAttribute(
    "aria-pressed",
    "false",
  );
  await expect(
    page.getByRole("region", { name: "Dispatch log" }),
  ).toContainText("Conflicting paths need human review");
  await expect(
    page.getByRole("link", { name: "Test a proposed rule ↓" }),
  ).toBeVisible();
});
