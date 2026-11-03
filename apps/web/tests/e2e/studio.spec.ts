import { test, expect } from "@playwright/test";

test("demo loads and graph selection follows real source evidence", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("link", { name: /Explore demo/ }).click();
  await expect(
    page.getByRole("heading", { name: "Every rule starts with evidence." }),
  ).toBeVisible();
  await page
    .locator(".react-flow__node")
    .filter({ hasText: "Can we move indoors?" })
    .click();
  await expect(page.getByTestId("segment-4")).toHaveAttribute(
    "data-highlighted",
    "true",
  );
  await expect(page.getByTestId("segment-3")).toHaveAttribute(
    "data-highlighted",
    "false",
  );
  await expect(
    page.getByText("AND indoor_spaces gt 0", { exact: true }),
  ).toBeVisible();
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: test.info().outputPath("source-studio.png"),
    fullPage: true,
  });
  await page.getByLabel("SWITCH DEMO").selectOption("customer-support");
  await expect(
    page.getByRole("heading", {
      name: "Which refund rule applies?",
      exact: true,
    }),
  ).toBeVisible();
  await expect(page.getByTestId("segment-3")).toHaveAttribute(
    "data-highlighted",
    "true",
  );
  await expect(page.getByTestId("segment-4")).toHaveAttribute(
    "data-highlighted",
    "true",
  );
});

test("rule selection works from the keyboard", async ({ page }) => {
  await page.goto("/studio");
  const rule = page.getByRole("button", {
    name: "Review venue authority",
    exact: true,
  });
  await rule.focus();
  await page.keyboard.press("Enter");
  await expect(rule).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByTestId("segment-5")).toHaveAttribute(
    "data-highlighted",
    "true",
  );
});

test("import persists source text through the API", async ({ page }) => {
  await page.goto("/import");
  await page
    .getByLabel("Document title")
    .fill("Fictional front desk procedure");
  await page
    .getByLabel("Procedure text")
    .fill("Welcome customers.\n\nEscalate unresolved requests.");
  await page.getByRole("button", { name: "Import document" }).click();
  await expect(
    page.getByRole("heading", { name: "Imported 2 source sections" }),
  ).toBeVisible();
  await expect(
    page.getByText("Escalate unresolved requests.", { exact: true }),
  ).toBeVisible();
});

test("Source Studio fits a mobile viewport", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/studio");
  await expect(
    page.getByRole("heading", { name: "Policy graph", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Source document", exact: true }),
  ).toBeVisible();
  const width = await page.evaluate(() => document.documentElement.scrollWidth);
  expect(width).toBeLessThanOrEqual(390);
  await page.screenshot({
    path: test.info().outputPath("source-studio-mobile.png"),
    fullPage: true,
  });
});
