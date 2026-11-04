import { test, expect, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

async function startRehearsal(page: Page) {
  await page.goto("/simulation?scenario=night-market");
  await page
    .getByRole("checkbox", {
      name: "I understand this is a fictional, unapproved model rehearsal.",
    })
    .check();
  await page
    .getByRole("button", { name: "Start rehearsal", exact: true })
    .click();
  await expect(page).toHaveURL(/\/simulation\/[a-f0-9-]+$/);
}

async function scan(page: Page, label: string) {
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();
  const summary = results.violations.map(
    (v) =>
      `${v.id} (${v.impact}): ${v.nodes
        .slice(0, 3)
        .map((n) => n.target.join(" "))
        .join(" | ")}`,
  );
  expect(summary, `axe violations on ${label}`).toEqual([]);
}

for (const [label, path] of [
  ["home", "/"],
  ["guide", "/guide"],
  ["source studio", "/studio"],
  ["library", "/library"],
  ["import", "/import"],
  ["simulation start", "/simulation?scenario=night-market"],
] as const) {
  test(`axe finds no WCAG 2.1 A/AA violations on ${label}`, async ({
    page,
  }) => {
    await page.goto(path);
    await expect(page.locator("#root")).toBeVisible();
    await page.waitForLoadState("networkidle");
    await scan(page, label);
  });
}

test("axe finds no WCAG 2.1 A/AA violations in the live Simulation Room", async ({
  page,
}) => {
  await startRehearsal(page);
  await expect(
    page.getByRole("heading", { name: "Is the vendor late?", exact: true }),
  ).toBeVisible();
  await scan(page, "simulation room (active decision)");
  await page
    .getByRole("button", {
      name: "Choose: Escalate to operations lead",
      exact: true,
    })
    .click();
  await expect(
    page.getByRole("heading", { name: "The procedure has no matching path." }),
  ).toBeVisible();
  await scan(page, "simulation room (uncovered path)");
});

test("axe finds no WCAG 2.1 A/AA violations on replay, report and scenario pages", async ({
  page,
}) => {
  await startRehearsal(page);
  const session = page.url().split("/simulation/")[1];
  for (const path of [
    `/replay/${session}`,
    `/simulation/${session}/report`,
    "/scenarios/new",
  ]) {
    await page.goto(path);
    await page.waitForLoadState("networkidle");
    await scan(page, path);
  }
});

test("axe finds no violations at a 390px mobile width", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  for (const path of ["/", "/library", "/simulation?scenario=night-market"]) {
    await page.goto(path);
    await page.waitForLoadState("networkidle");
    await scan(page, `${path} (mobile)`);
  }
});
