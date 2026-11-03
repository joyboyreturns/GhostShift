import { defineConfig } from "@playwright/test";
import { randomBytes } from "node:crypto";
import { mkdtempSync, existsSync, writeFileSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";

const directory = process.env.GHOSTSHIFT_PUBLIC_TEST_DIR ?? mkdtempSync(join(tmpdir(), "ghostshift-public-"));
const marker = join(directory, ".ghostshift-public-test");
if (!process.env.GHOSTSHIFT_PUBLIC_TEST_DIR) writeFileSync(marker, "ephemeral public test data v1");
if (!existsSync(marker) || readFileSync(marker, "utf8") !== "ephemeral public test data v1") throw new Error("Refusing an unmarked public-test directory");
process.env.GHOSTSHIFT_PUBLIC_TEST_DIR = directory;
const environment = {
  PUBLIC_DEMO: "true", PUBLIC_DEMO_SECRET: randomBytes(32).toString("hex"),
  PUBLIC_ORIGIN: "http://127.0.0.1:4174", PUBLIC_COOKIE_SECURE: "false",
  PUBLIC_TEMPLATE_PATH: join(directory, "template.db"), PUBLIC_WORKSPACE_ROOT: join(directory, "workspaces"),
  PUBLIC_WRITES_PER_MINUTE: "100", PUBLIC_NEW_WORKSPACES_PER_HOUR: "200", WEB_CONCURRENCY: "1",
};
export default defineConfig({
  testDir: "./tests/public",
  outputDir: "./test-results/public", workers: 1,
  globalTeardown: "./tests/public/teardown.ts",
  use: {baseURL: "http://127.0.0.1:4174", trace: "retain-on-failure"},
  webServer: [
    {command: "cd ../../services/api && uv run python -m app.services.demo_admin prepare && uv run uvicorn app.main:app --host 127.0.0.1 --port 8091", env: environment,
      url: "http://127.0.0.1:8091/api/health", reuseExistingServer: false},
    {command: "npm run build && caddy run --config ../../deploy/Caddyfile --adapter caddyfile",
      env: {GHOSTSHIFT_SITE: "http://127.0.0.1:4174", GHOSTSHIFT_API_UPSTREAM: "127.0.0.1:8091", GHOSTSHIFT_WEB_ROOT: resolve("dist")},
      url: "http://127.0.0.1:4174", reuseExistingServer: false},
  ],
});
