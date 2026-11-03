#!/bin/sh
set -eu
(cd services/api && exec uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000) &
api_pid=$!
(cd apps/web && exec npm run dev) &
web_pid=$!
trap 'kill "$api_pid" "$web_pid" 2>/dev/null || true' EXIT INT TERM
wait
