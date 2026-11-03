/** Record the actual local production app, then add disclosed system TTS narration. */
import { renderCaptions } from "./demo-captions.mjs";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import { dirname, join, resolve } from "node:path";
import { mkdtemp, mkdir, writeFile, readFile, rm } from "node:fs/promises";
import { spawn, spawnSync } from "node:child_process";
import { tmpdir } from "node:os";
import { randomBytes } from "node:crypto";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const require = createRequire(join(root, "apps/web/package.json"));
const { chromium, expect } = require("@playwright/test");
const output = resolve(process.env.GHOSTSHIFT_VIDEO_OUTPUT ?? join(root, "artifacts/demo"));
const ffmpeg = process.env.FFMPEG_PATH ?? "ffmpeg";
const chapters = [
  { seconds: 15, title: "The ghost path", text: "The vendor is late. Rain is coming. The indoor space is full. Your procedure says move indoors. Now what? GhostShift helps operations coordinators find the missing instruction before a real event does." },
  { seconds: 20, title: "Start your shift", text: "This is a local preview with fictional data. Start your shift against a pinned, unapproved model of the procedure. You make real choices. Each choice and its source references become part of the preserved history." },
  { seconds: 20, title: "The procedure stops", text: "We escalate the late delivery. Then the recorded scenario update raises rain risk from forty to eighty-five. Indoor capacity is zero. Neither modeled choice covers these facts. GhostShift stops instead of inventing an answer." },
  { seconds: 20, title: "Inspect the source", text: "The highlighted weather clause says redirect vendors indoors. It never addresses exhausted capacity. The capacity guard is a modeling assumption requiring review. A citation locates text. It does not prove that our interpretation has been approved." },
  { seconds: 40, title: "Test a human proposal", text: "Let's test a human-authored experiment. I enter a reason and add a choice for the current facts: pause admission and contact the venue manager. These equality conditions cover this case only. I review the destination, save an unapproved proposal, acknowledge its status, and rehearse it. The original procedure and run remain intact." },
  { seconds: 25, title: "Compare actual outcomes", text: "Replay verifies the stored history against pinned inputs. Compare the original gap with the alternate run. Under the proposed rule, these modeled inputs now reach the modeled end. That is evidence about this experiment, not proof of real-world correctness. Both runs still show their authority and recorded decisions." },
  { seconds: 15, title: "Keep the evidence", text: "Download the actual comparison: both histories, quoted sources, exact replay inputs, and logical events. A portable evidence package makes the experiment inspectable after this temporary workspace expires." },
  { seconds: 15, title: "Built with Kiro", text: "Kiro authored the initial engine, specs, and sixty tests. Codex reviewed it and built the product around it. Source provenance, executable rules, branching history. Find the ghost path before your next shift." },
];
const pause = (ms) => new Promise((done) => setTimeout(done, ms));
const processes = [];
let browser;
let context;
let directory;
function run(command, args, options = {}) {
  const result = spawnSync(command, args, { cwd: root, encoding: "utf8", ...options });
  if (result.error) throw result.error;
  if (result.status !== 0) throw new Error(`${command} failed: ${result.stderr ?? ""}`);
  return result;
}
function launch(command, args, options) {
  const child = spawn(command, args, { cwd: root, stdio: "ignore", ...options });
  processes.push(child);
  child.on("error", (error) => console.error("Local server failed:", error.message));
  return child;
}
async function ready(url) {
  let lastError = "No successful response yet";
  for (let attempt = 0; attempt < 90; attempt++) {
    try { const response = await fetch(url); if (response.ok) return; lastError = `HTTP ${response.status}`; } catch (error) { lastError = error.message; }
    await pause(500);
  }
  throw new Error(`Local recording server did not become ready: ${url}: ${lastError}`);
}

try {
  await mkdir(output, { recursive: true });
  directory = await mkdtemp(join(tmpdir(), "ghostshift-film-"));
  let offset = 0;
  const audio = [];
  for (const [index, chapter] of chapters.entries()) {
    const text = join(directory, `chapter-${index}.txt`);
    const spoken = join(directory, `chapter-${index}.aiff`);
    const padded = join(directory, `chapter-${index}.wav`);
    await writeFile(text, chapter.text);
    run("say", ["-v", "Samantha", "-r", "175", "-f", text, "-o", spoken]);
    const probe = run("afinfo", [spoken]).stdout;
    const duration = Number(/estimated duration:\s*([\d.]+)/.exec(probe)?.[1]);
    if (!duration || duration > chapter.seconds - 0.15) throw new Error(`Narration does not fit chapter ${index}: ${duration}s / ${chapter.seconds}s`);
    run(ffmpeg, ["-y", "-i", spoken, "-af", `apad,atrim=duration=${chapter.seconds}`, "-ar", "48000", "-ac", "2", padded]);
    audio.push(padded);
    chapter.start = offset;
    chapter.narration_seconds = duration;
    offset += chapter.seconds;
  }
  const concat = join(directory, "audio.txt");
  await writeFile(concat, audio.map((path) => `file '${path.replaceAll("'", "'\\''")}'`).join("\n"));
  const narration = join(directory, "narration.wav");
  run(ffmpeg, ["-y", "-f", "concat", "-safe", "0", "-i", concat, "-c", "copy", narration]);
  const subtitles = join(output, "ghostshift-demo.srt");
  await writeFile(subtitles, renderCaptions(chapters));
  const environment = { ...process.env, PUBLIC_DEMO: "true", PUBLIC_DEMO_SECRET: randomBytes(48).toString("hex"), PUBLIC_ORIGIN: "http://127.0.0.1:4177", PUBLIC_COOKIE_SECURE: "false", PUBLIC_TEMPLATE_PATH: join(directory, "template.db"), PUBLIC_WORKSPACE_ROOT: join(directory, "workspaces"), PUBLIC_NEW_WORKSPACES_PER_HOUR: "200", PUBLIC_WRITES_PER_MINUTE: "100", WEB_CONCURRENCY: "1" };
  const apiDirectory = join(root, "services/api");
  run("uv", ["run", "python", "-m", "app.services.demo_admin", "prepare"], { cwd: apiDirectory, env: environment });
  run("npm", ["--prefix", "apps/web", "run", "build"]);
  launch("uv", ["run", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8093"], { cwd: apiDirectory, env: environment });
  launch("caddy", ["run", "--config", join(root, "deploy/Caddyfile"), "--adapter", "caddyfile"], { env: { ...environment, GHOSTSHIFT_SITE: "http://127.0.0.1:4177", GHOSTSHIFT_API_UPSTREAM: "127.0.0.1:8093", GHOSTSHIFT_WEB_ROOT: join(root, "apps/web/dist") } });
  await ready("http://127.0.0.1:4177/api/health");
  browser = await chromium.launch();
  context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, recordVideo: { dir: join(directory, "video"), size: { width: 1440, height: 1000 } }, reducedMotion: "reduce" });
  const page = await context.newPage();
  const video = page.video();
  const started = performance.now();
  async function at(seconds) {
    const remaining = seconds * 1000 - (performance.now() - started);
    if (remaining < -2500) throw new Error(`Recording fell behind at ${seconds}s`);
    if (remaining > 0) await pause(remaining);
  }
  async function chapter(index) { await at(chapters[index].start); console.log(`Recording ${chapters[index].start}s: ${chapters[index].title}`); }
  await chapter(0);
  await page.goto("http://127.0.0.1:4177/");
  await expect(page.getByRole("link", { name: "Start your shift" })).toBeVisible();
  await at(7);
  await page.getByRole("link", { name: "Start your shift" }).click();
  await chapter(1);
  await page.getByRole("checkbox").check();
  await page.getByRole("button", { name: "Start rehearsal", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Is the vendor late?", exact: true })).toBeVisible();
  await page.locator(".command-workbench").scrollIntoViewIfNeeded();
  await at(30);
  await page.getByRole("button", { name: "Choose: Escalate to operations lead", exact: true }).click();
  await expect(page.getByRole("heading", { name: "The procedure has no matching path." })).toBeVisible();
  const parentId = new URL(page.url()).pathname.split("/").at(-1);
  const parentBefore = await (await context.request.get(`http://127.0.0.1:4177/api/sessions/${parentId}`)).json();
  await chapter(2);
  await page.getByRole("button", { name: "Show all updates" }).click();
  await page.locator(".command-workbench").scrollIntoViewIfNeeded();
  await chapter(3);
  await page.getByRole("link", { name: "Inspect the source ↓" }).click();
  await page.getByTestId("segment-4").scrollIntoViewIfNeeded();
  await chapter(4);
  await page.getByRole("link", { name: "Test a proposed rule ↓" }).click();
  const form = page.locator(".proposal-section");
  await form.getByLabel("Reason for the change").pressSequentially("Test a holding response when indoor capacity is exhausted", { delay: 35 });
  await form.getByRole("button", { name: "Add choice for current facts", exact: true }).click();
  await form.locator(".policy-choice").last().getByLabel("Action label", { exact: true }).pressSequentially("Pause admission and contact venue manager", { delay: 45 });
  await form.locator(".policy-choice").last().scrollIntoViewIfNeeded();
  await at(101);
  await form.getByRole("button", { name: "Save unapproved proposal" }).click();
  await form.getByRole("checkbox").check();
  await at(108);
  await form.getByRole("button", { name: "Rehearse proposal", exact: true }).click();
  await page.getByRole("button", { name: "Choose: Pause admission and contact venue manager", exact: true }).click();
  await expect(page.getByRole("region", {name: "Shift debrief"})).toContainText("Rehearsal complete");
  await chapter(5);
  await page.getByRole("button", { name: "Verify replay", exact: true }).click();
  await expect(page.getByText(/Replay verified against pinned inputs/)).toBeVisible();
  await at(120);
  await page.getByRole("button", { name: "Compare with parent", exact: true }).click();
  await page.getByRole("heading", {name: "What changed in the recorded runs?"}).scrollIntoViewIfNeeded();
  await expect(page.getByRole("region", {name: "Run comparison"})).toContainText("unapproved proposal");
  await chapter(6);
  await page.getByRole("link", {name: "Export parent / alternate comparison ↗"}).click();
  const [download] = await Promise.all([page.waitForEvent("download"), page.getByRole("link", {name: "Download comparison JSON"}).click()]);
  await download.saveAs(join(output, "recorded-comparison.json"));
  const comparison = JSON.parse(await readFile(join(output, "recorded-comparison.json"), "utf8"));
  if (comparison.left.status !== "uncovered" || comparison.right.status !== "completed" || comparison.right.reviewed_supported_count !== 0) throw new Error("Recorded outcomes did not match the demonstrated experiment");
  expect(await (await context.request.get(`http://127.0.0.1:4177/api/sessions/${parentId}`)).json()).toEqual(parentBefore);
  await chapter(7);
  await page.goto("http://127.0.0.1:4177/guide");
  await page.locator("#built-with-kiro").scrollIntoViewIfNeeded();
  await at(166);
  await page.goto("http://127.0.0.1:4177/");
  await at(170);
  await context.close(); context = undefined;
  const raw = await video.path();
  const final = join(output, "ghostshift-demo.mp4");
  run(ffmpeg, ["-y", "-i", raw, "-i", narration, "-i", subtitles, "-map", "0:v:0", "-map", "1:a:0", "-map", "2:0", "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-c:s", "mov_text", "-metadata:s:s:0", "language=eng", "-disposition:s:0", "0", "-movflags", "+faststart", "-t", "170", final]);
  await writeFile(join(output, "recording.json"), JSON.stringify({ duration_seconds: 170, resolution: "1440x1000", capture: "Real production-build browser actions against a clean local Caddy/API workspace; no mocked results", narration: "Synthetic local macOS Samantha voice, 175 words/minute", hosting: "Local preview only", chapters, comparison: "recorded-comparison.json" }, null, 2));
  console.log(`Recorded: ${final}`);
} finally {
  if (context) await context.close();
  if (browser) await browser.close();
  for (const process of processes) process.kill("SIGTERM");
  if (directory) await rm(directory, { recursive: true, force: true });
}
