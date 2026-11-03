import { test, expect, type Page } from "@playwright/test";
import { readFile } from "node:fs/promises";
import { reportSchema } from "../../src/lib/api";

async function startRehearsal(page: Page, scenario = "night-market") {
  await page.goto(`/simulation?scenario=${scenario}`);
  const start = page.getByRole("button", {
    name: "Start rehearsal",
    exact: true,
  });
  await expect(start).toBeDisabled();
  await page
    .getByRole("checkbox", {
      name: "I understand this is a fictional, unapproved model rehearsal.",
    })
    .check();
  await start.click();
  await expect(page).toHaveURL(/\/simulation\/[a-f0-9-]+$/);
}

async function reachGap(page: Page) {
  await startRehearsal(page);
  await page
    .getByRole("button", {
      name: "Choose: Escalate to operations lead",
      exact: true,
    })
    .focus();
  await page.keyboard.press("Enter");
  await expect(
    page.getByRole("heading", { name: "The procedure has no matching path." }),
  ).toBeVisible();
}

test("real choices persist, stop at the policy gap, replay, and export actual findings", async ({
  page,
}) => {
  await page.goto("/studio");
  await page.getByRole("link", { name: "Rehearse scenario" }).click();
  await page.getByRole("checkbox").check();
  await page
    .getByRole("button", { name: "Start rehearsal", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Is the vendor late?", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", {
      name: "Choose: Escalate to operations lead",
      exact: true,
    })
    .click();
  await expect(
    page.getByRole("heading", { name: "The procedure has no matching path." }),
  ).toBeVisible();
  await expect(
    page.locator(".facts-panel").getByText("85", { exact: true }),
  ).toBeVisible();
  const runUrl = page.url();
  const sessionId = new URL(runUrl).pathname.split("/").at(-1)!;
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "The procedure has no matching path." }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Verify replay", exact: true })
    .click();
  await expect(
    page.getByText(/Replay verified against pinned inputs/),
  ).toBeVisible();
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: test.info().outputPath("simulation-gap.png"),
    fullPage: true,
  });
  await page.getByRole("link", { name: "Session report", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Findings requiring review" }),
  ).toBeVisible();
  await expect(
    page
      .locator(".report-finding")
      .getByText("Uncovered decision path", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("1 cited decisions · 0 reviewed, supported decisions"),
  ).toBeVisible();
  const [download] = await Promise.all([
    page.waitForEvent("download"),
    page.getByRole("link", { name: "Download report JSON" }).click(),
  ]);
  const saved = test.info().outputPath("actual-report.json");
  await download.saveAs(saved);
  const report = reportSchema.parse(JSON.parse(await readFile(saved, "utf8")));
  expect(report.session_id).toBe(sessionId);
  expect(report.uncovered_count).toBe(1);
  expect(report.playbook_authority).toBe("draft");
  expect(report.reviewed_supported_count).toBe(0);
  await page.screenshot({
    path: test.info().outputPath("after-action-report.png"),
    fullPage: true,
  });
});

test("a checkpoint fork records an alternate choice without modifying its parent", async ({
  page,
}) => {
  await reachGap(page);
  const parentUrl = page.url();
  await page
    .getByRole("button", {
      name: "Fork before Is the vendor late?",
      exact: true,
    })
    .click();
  await expect(
    page.getByText("Alternate run from a saved checkpoint.", { exact: true }),
  ).toBeVisible();
  expect(page.url()).not.toBe(parentUrl);
  await page
    .getByRole("button", {
      name: "Choose as deviation: Continue routine intake",
      exact: true,
    })
    .click();
  await expect(
    page.getByText("1 deviation recorded in this run.", { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Compare with parent", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Parent vs. alternate" }),
  ).toBeVisible();
  await expect(
    page.getByRole("row", { name: /Deviations\s+0\s+1/ }),
  ).toBeVisible();
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: test.info().outputPath("fork-comparison.png"),
    fullPage: true,
  });
  await page.getByRole("link", { name: "Open parent", exact: true }).click();
  await expect(page).toHaveURL(parentUrl);
  await expect(
    page.getByRole("heading", { name: "The procedure has no matching path." }),
  ).toBeVisible();
  await expect(page.locator(".deviation-notice")).toHaveCount(0);
});

test("the support fixture stops on real overlap and exposes both original source sections", async ({
  page,
}) => {
  await startRehearsal(page, "customer-support");
  await expect(
    page.getByRole("heading", { name: "More than one rule matches." }),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: /^Choose:/ })).toHaveCount(0);
  await expect(page.getByTestId("segment-3")).toHaveAttribute(
    "data-highlighted",
    "true",
  );
  await expect(page.getByTestId("segment-4")).toHaveAttribute(
    "data-highlighted",
    "true",
  );
});

test("the rehearsal and report fit a mobile viewport", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await reachGap(page);
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth),
  ).toBeLessThanOrEqual(390);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: test.info().outputPath("simulation-mobile.png"),
    fullPage: true,
  });
  await page.getByRole("link", { name: "Session report", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Reproducibility", exact: true }),
  ).toBeVisible();
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth),
  ).toBeLessThanOrEqual(390);
});
