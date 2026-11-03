import { test, expect } from "@playwright/test";

test("a genuine policy gap can be proposed, rehearsed and compared without granting authority", async ({page, request}) => {
  await page.goto("/simulation?scenario=night-market");
  await page.getByRole("checkbox").check();
  await page.getByRole("button", {name: "Start rehearsal", exact: true}).click();
  await page.getByRole("button", {name: "Choose: Escalate to operations lead", exact: true}).click();
  await expect(page.getByRole("heading", {name: "The procedure has no matching path."})).toBeVisible();
  const parentId = new URL(page.url()).pathname.split("/").at(-1)!;
  const parentBefore = await (await request.get(`/api/sessions/${parentId}`)).json();
  await page.getByText("Propose a rule change", {exact: true}).click();
  await page.getByLabel("Reason for the change").fill("Test a safe holding action when indoor capacity is exhausted");
  const proposal = page.locator(".proposal-section");
  await proposal.getByRole("button", {name: "Add choice for current facts", exact: true}).click();
  const choice = proposal.locator(".policy-choice").last();
  await choice.getByLabel("Action label", {exact: true}).fill("Pause admission and contact venue manager");
  await expect(choice.locator(".condition-editor")).toHaveCount(3);
  await proposal.getByRole("button", {name: "Save unapproved proposal"}).click();
  await expect(proposal.getByRole("heading", {name: "Proposal saved · awaiting review"})).toBeVisible();
  await proposal.getByRole("checkbox", {name: "I understand this proposal is unapproved."}).check();
  await proposal.getByRole("button", {name: "Rehearse proposal", exact: true}).click();
  await expect(page).not.toHaveURL(new RegExp(`${parentId}$`));
  await page.getByRole("button", {name: "Choose: Pause admission and contact venue manager", exact: true}).click();
  await expect(page.getByText("The modeled workflow reached its end.", {exact: false})).toBeVisible();
  await page.getByRole("button", {name: "Compare with parent", exact: true}).click();
  await expect(page.getByRole("region", {name: "Run comparison"})).toContainText("Same scenario, different policy");
  await expect(page.getByRole("region", {name: "Run comparison"})).toContainText("unapproved proposal");
  await page.getByRole("button", {name: "Verify replay", exact: true}).click();
  await expect(page.getByText(/Replay verified against pinned inputs/)).toBeVisible();
  expect(await (await request.get(`/api/sessions/${parentId}`)).json()).toEqual(parentBefore);
  const alternateId = new URL(page.url()).pathname.split("/").at(-1)!;
  const report = await (await request.get(`/api/sessions/${alternateId}/report`)).json();
  expect(report.status).toBe("completed");
  expect(report.reviewed_supported_count).toBe(0);
  expect(report.proposals[0].review_status).toBe("pending");
  expect(report.decisions.at(-1).evidence_status).toBe("uncited");
  await page.screenshot({path: test.info().outputPath("proposed-policy-comparison.png"), fullPage: true});
  await page.getByRole("link", {name: "Session report", exact: true}).click();
  await expect(page.getByRole("heading", {name: "Proposed rule changes · unapproved"})).toBeVisible();
  await page.getByRole("link", {name: "Resume saved proposal"}).click();
  await page.reload();
  await expect(page.getByRole("heading", {name: "Test the change before you trust it."})).toBeVisible();
  await expect(page.getByRole("button", {name: "Rehearse proposal", exact: true})).toBeDisabled();
});

test("human review persists and source revisions require fresh citations", async ({page, request}) => {
  const source = await (await request.post("/api/documents", {data: {title: "Fictional reviewed delivery procedure", content: "Vendor delays of at least 30 minutes must be escalated to the operations lead."}})).json();
  const created = await request.post("/api/playbooks", {data: {document_id: source.id, title: "Fictional delivery policy", graph: {nodes: [
    {id: "start", label: "Begin", type: "start", next_node: "delay"},
    {id: "delay", label: "Is escalation required?", type: "decision", choices: [{id: "escalate", label: "Escalate to operations lead", destination: "end", conditions: [{field: "vendor_delay_minutes", operator: "gte", value: 30}], source_refs: [source.segments[0].id], evidence_status: "cited"}]},
    {id: "end", label: "Complete", type: "end"},
  ]}}});
  expect(created.status()).toBe(201);
  const version = await created.json();
  await page.goto(`/review/${version.id}`);
  const approve = page.getByRole("button", {name: "Approve reviewed version", exact: true});
  await expect(approve).toBeDisabled();
  await page.getByRole("checkbox", {name: "I verified this choice and all its conditions against the cited source."}).check();
  await page.getByLabel("Reviewer name").fill("Fictional QA reviewer");
  await page.getByLabel("Review notes").fill("The escalation threshold matches the cited fictional procedure.");
  await page.getByRole("checkbox", {name: /I confirm the entire modeled procedure/}).check();
  await approve.focus();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("heading", {name: "Approved version · immutable"})).toBeVisible();
  await page.reload();
  await expect(page.getByText("Reviewed by Fictional QA reviewer:", {exact: false})).toBeVisible();
  await page.getByText("Create a new revision", {exact: true}).click();
  await page.getByText("Revise the source document", {exact: true}).click();
  await page.getByLabel("Revised procedure").fill("Vendor delays of at least 45 minutes must be escalated to the operations lead.");
  await page.getByRole("button", {name: "Save revised source snapshot", exact: true}).click();
  await expect(page.getByText("New source saved. Select its supporting sections for each rule.")).toBeVisible();
  const editor = page.locator(".revision-node");
  await editor.getByRole("textbox", {name: "Comparison value", exact: true}).fill("45");
  await editor.getByRole("checkbox").check();
  await page.getByRole("button", {name: "Save draft revision", exact: true}).click();
  await expect(page).not.toHaveURL(new RegExp(`${version.id}$`));
  await expect(page.getByRole("button", {name: "Approve reviewed version", exact: true})).toBeDisabled();
  expect(await (await request.get(`/api/playbooks/${version.id}`)).json()).toEqual({...version, status: "approved"});
  await expect(page.getByText(/vendor_delay_minutes.*at least.*45/)).toBeVisible();
  await page.screenshot({path: test.info().outputPath("source-supported-revision.png"), fullPage: true});
});

test("an imported procedure can be modeled manually and inspected from real API graph data on mobile", async ({page, request}) => {
  await page.setViewportSize({width: 390, height: 844});
  await page.goto("/import");
  await page.getByLabel("Document title").fill("Fictional vendor intake — manual model");
  await page.getByLabel("Procedure text").fill("Escalate to the operations lead when the vendor is at least 30 minutes late.");
  await page.getByRole("button", {name: "Import document", exact: true}).click();
  await page.getByRole("button", {name: "Model decision rules", exact: true}).click();
  await page.getByRole("button", {name: "Add decision before completion", exact: true}).click();
  await page.getByLabel("Decision question", {exact: true}).fill("Does the vendor delay require escalation?");
  const rule = page.locator(".revision-node");
  await rule.getByLabel("Action label", {exact: true}).fill("Escalate to operations lead");
  await rule.getByLabel("Fact name", {exact: true}).fill("vendor_delay_minutes");
  await rule.getByLabel("Comparison", {exact: true}).selectOption("gte");
  await rule.getByRole("textbox", {name: "Comparison value", exact: true}).fill("30");
  // Removing an earlier condition must preserve the next condition's actual operand.
  await rule.getByRole("button", {name: "Add condition", exact: true}).click();
  const second = rule.locator(".condition-editor").last();
  await second.getByLabel("Fact name", {exact: true}).fill("vendor_delay_minutes");
  await second.getByRole("textbox", {name: "Comparison value", exact: true}).fill("45");
  await rule.locator(".condition-editor").first().getByRole("button", {name: "Remove condition", exact: true}).click();
  await expect(rule.getByRole("textbox", {name: "Comparison value", exact: true})).toHaveValue("45");
  await rule.getByRole("textbox", {name: "Comparison value", exact: true}).fill("30");
  await rule.getByLabel("Comparison", {exact: true}).selectOption("gte");
  await rule.getByRole("checkbox").check();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({path: test.info().outputPath("manual-model-mobile.png"), fullPage: true});
  await page.getByRole("button", {name: "Save draft revision", exact: true}).click();
  await expect(page.getByText(/vendor_delay_minutes.*at least.*30/)).toBeVisible();
  const versionId = new URL(page.url()).pathname.split("/").at(-1)!;
  const version = await (await request.get(`/api/playbooks/${versionId}`)).json();
  expect(version.version).toBe(2);
  expect(version.graph.nodes).toHaveLength(3);
  expect(version.graph.nodes[1].choices[0].source_refs).toHaveLength(1);
  await page.getByRole("link", {name: "Inspect graph & source", exact: true}).click();
  await expect(page.locator(".inspector-panel")).toContainText("Does the vendor delay require escalation?");
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});
