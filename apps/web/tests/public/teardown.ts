import { rmSync, existsSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
export default function teardown() {
  const directory = process.env.GHOSTSHIFT_PUBLIC_TEST_DIR;
  if (directory?.startsWith(join(tmpdir(), "ghostshift-public-")) && existsSync(join(directory, ".ghostshift-public-test")) && readFileSync(join(directory, ".ghostshift-public-test"), "utf8") === "ephemeral public test data v1") rmSync(directory, {recursive: true, force: true});
}
