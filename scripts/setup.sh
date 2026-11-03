#!/bin/sh
# Run from macOS Terminal when package downloads are available.
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$project_dir"

for dependency in uv node npm; do
    if ! command -v "$dependency" >/dev/null 2>&1; then
        printf 'Required command is missing: %s\n' "$dependency" >&2
        exit 1
    fi
done

node -e 'const [major, minor] = process.versions.node.split(".").map(Number); if (major < 22 || (major === 22 && minor < 12)) { console.error("Node 22.12 or newer is required"); process.exit(1); }'

printf '\nInstalling Python 3.12…\n'
uv python install 3.12

printf '\nInstalling locked frontend dependencies…\n'
(cd apps/web && npm ci)

printf '\nInstalling locked backend dependencies…\n'
(cd services/api && uv sync --locked --python 3.12)

printf '\nInstalling the Chromium browser used by Playwright…\n'
(cd apps/web && npx --no-install playwright install chromium)

printf '\nInstallation finished. Return to Codex to run the full validation suite.\n'
