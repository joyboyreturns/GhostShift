import { defineConfig } from "@playwright/test";

const origin = process.env.GHOSTSHIFT_CONTAINER_ORIGIN;
if (!origin || !/^http:\/\/127\.0\.0\.1:\d+$/.test(origin)) {
  throw new Error("Container checks require an explicit loopback HTTP origin.");
}
export default defineConfig({
  testDir: "./tests/public",
  outputDir: "./test-results/containers",
  workers: 1,
  use: { baseURL: origin, trace: "retain-on-failure" },
});
