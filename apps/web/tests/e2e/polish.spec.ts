import { test, expect } from "@playwright/test";

test("Library history keeps the search field, results and pagination consistent", async ({
  page,
}) => {
  await page.goto("/library?q=Night");
  const search = page.getByRole("textbox", {
    name: "Search by title or run ID",
  });
  await expect(search).toHaveValue("Night");
  await search.fill("Customer");
  await page.getByRole("button", { name: "Search", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Search", exact: true }),
  ).toBeFocused();
  await expect(page.locator(".library-grid")).toContainText("Customer Support");
  await page.goBack();
  await expect(search).toHaveValue("Night");
  await expect(page.locator(".library-grid")).toContainText("Night Market");
  await page.goForward();
  await expect(search).toHaveValue("Customer");
  await page.goto("/library?offset=100000");
  await expect(
    page.getByRole("heading", { name: "No results on this page" }),
  ).toBeVisible();
  await expect(page.getByLabel("Library pagination")).toContainText(
    "0 on this page",
  );
  await page.getByRole("button", { name: "Return to first page" }).click();
  await expect(page.locator(".library-card").first()).toBeVisible();
  for (const offset of ["Infinity", "1.5", "-1", "invalid", "100001"]) {
    await page.goto(`/library?offset=${offset}`);
    await expect(page.locator(".library-card").first()).toBeVisible();
    await expect(page.getByRole("alert")).toHaveCount(0);
  }
  await page.goto("/library?q=no-such-procedure-polish");
  await page.getByRole("button", { name: "Clear search" }).click();
  await expect(search).toHaveValue("");
  await expect(page.locator(".library-card").first()).toBeVisible();
});

test("import recovers from a gateway failure and locks the submitted source while saving", async ({
  page,
}) => {
  await page.goto("/import");
  const title = page.getByLabel("Document title");
  const content = page.getByLabel("Procedure text");
  const text = "Fictional polish rehearsal.\n\nEscalate unresolved requests.";
  const name = `Polished source ${Date.now()}`;
  await title.fill(name);
  await content.fill(text);
  await page.route("**/api/documents", (route) =>
    route.fulfill({
      status: 502,
      contentType: "text/html",
      body: "<h1>Gateway unavailable</h1>",
    }),
  );
  await page
    .getByRole("button", { name: "Import document", exact: true })
    .click();
  await expect(page.getByRole("alert")).toContainText("(502)");
  await expect(title).toHaveValue(name);
  await expect(content).toHaveValue(text);
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
      .getByRole("button", { name: "Import document", exact: true })
      .click();
    await expect(
      page.getByRole("button", { name: "Importing…" }),
    ).toBeDisabled();
    await expect(title).toBeDisabled();
    await expect(content).toBeDisabled();
    await expect(
      page.getByRole("button", { name: "Upload PDF" }),
    ).toBeDisabled();
  } finally {
    release();
  }
  await expect(
    page.getByRole("heading", { name: "Imported 2 source sections" }),
  ).toBeVisible();
  await title.fill("Another unsaved title");
  await expect(
    page.getByRole("region", { name: "Imported source" }),
  ).toContainText(name);
  await page.getByRole("link", { name: "Library", exact: true }).click();
  await page
    .getByRole("textbox", { name: "Search by title or run ID" })
    .fill(name);
  await page.getByRole("button", { name: "Search", exact: true }).click();
  await expect(page.locator(".library-grid")).toContainText(name);
});

test("oversized PDF selection explains why importing is disabled", async ({
  page,
}) => {
  await page.goto("/import");
  await page.getByRole("button", { name: "Upload PDF" }).click();
  await page.getByLabel("Document title").fill("Oversized fictional PDF");
  await page.getByLabel("Text-based PDF", { exact: true }).setInputFiles({
    name: "large.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.alloc(256 * 1024 + 1),
  });
  await expect(page.getByRole("alert")).toContainText("exceeds 256 KiB");
  await expect(
    page.getByRole("button", { name: "Import document", exact: true }),
  ).toBeDisabled();
  await page.getByRole("button", { name: "Paste text or Markdown" }).click();
  await page.getByRole("button", { name: "Upload PDF" }).click();
  await expect(page.getByRole("alert")).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Import document", exact: true }),
  ).toBeDisabled();
});

test("a failed page module offers recovery instead of an empty screen", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await page.route("**/src/routes/Library.tsx*", (route) =>
    route.fulfill({ status: 503, body: "unavailable" }),
  );
  await page.getByRole("link", { name: "Library", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "This page could not open." }),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "Reload page" })).toBeVisible();
  await page.getByRole("link", { name: "Return home", exact: true }).click();
  await expect(page.getByRole("heading", { level: 1 })).toContainText(
    "Every playbook",
  );
});

for (const width of [360, 390, 768, 1440]) {
  test(`existing journeys fit ${width}px with keyboard and reduced motion`, async ({
    page,
    request,
  }) => {
    test.setTimeout(120_000);
    await page.setViewportSize({ width, height: 960 });
    await page.emulateMedia({ reducedMotion: "reduce" });
    const started = await request.post("/api/sessions", {
      data: { scenario_id: "night-market", allow_draft_rehearsal: true },
    });
    expect(started.status()).toBe(201);
    const initial = await started.json();
    const chosen = await request.post(`/api/sessions/${initial.id}/choose`, {
      data: { choice_id: "escalate", expected_revision: 0 },
    });
    expect(chosen.ok()).toBe(true);
    const forked = await request.post(`/api/sessions/${initial.id}/fork`, {
      data: { event_index: 2 },
    });
    expect(forked.status()).toBe(201);
    const alternate = await forked.json();
    expect(
      (
        await request.post(`/api/sessions/${alternate.id}/choose`, {
          data: { choice_id: "routine", expected_revision: 0 },
        })
      ).ok(),
    ).toBe(true);
    const routes = [
      "/",
      "/studio",
      "/library",
      "/import",
      "/review/night-market-v1?edit=1",
      "/scenarios/new?playbook=night-market-v1",
      `/simulation/${initial.id}`,
      `/replay/${initial.id}`,
      `/simulation/${initial.id}/report`,
      `/reports/compare?left=${initial.id}&right=${alternate.id}`,
    ];
    for (const [index, path] of routes.entries()) {
      await page.goto(path);
      const heading = page.getByRole("heading", { level: 1 }).first();
      await expect(heading).toBeVisible();
      await expect(heading).toBeFocused();
      await expect(page).toHaveTitle(/GhostShift/);
      await page.getByRole("link", { name: "Skip to content" }).focus();
      await page.keyboard.press("Enter");
      await expect(page).toHaveURL(/#main$/);
      await expect(page.locator("#main")).toBeFocused();
      expect(
        await page.evaluate(() => document.documentElement.scrollWidth),
      ).toBeLessThanOrEqual(width);
      await page.evaluate(() => {
        if (document.activeElement instanceof HTMLElement)
          document.activeElement.blur();
        window.scrollTo(0, 0);
      });
      await page.screenshot({
        path: test.info().outputPath(`polish-${width}-${index}.png`),
        fullPage: true,
      });
    }
    await page.emulateMedia({ media: "print" });
    await expect(
      page.getByRole("heading", { name: "Two paths, inspected." }),
    ).toBeVisible();
    await expect(
      page.getByRole("navigation", { name: "Main navigation" }),
    ).not.toBeVisible();
    await page.screenshot({
      path: test.info().outputPath(`comparison-print-${width}.png`),
      fullPage: true,
    });
    await page.goto(`/simulation/${initial.id}/report`);
    await expect(page.getByRole("heading", { level: 1 }).first()).toBeVisible();
    await page.screenshot({
      path: test.info().outputPath(`report-print-${width}.png`),
      fullPage: true,
    });
  });
}
