#!/usr/bin/env bash
# Bootstrap a fresh Ubuntu 22.04/24.04 host for the public GhostShift demo.
# Run on the server as a sudo-capable user, from the cloned repository root:
#   DEMO_DOMAIN=demo.example.org ./deploy/provision-ubuntu.sh
# Idempotent where possible. It never touches an existing deploy/.env.public secret.
set -euo pipefail

: "${DEMO_DOMAIN:?Set DEMO_DOMAIN to the hostname whose A record points at this server}"
cd "$(dirname "$0")/.."
ENV_FILE=deploy/.env.public
COMPOSE=(docker compose --env-file "$ENV_FILE" -f deploy/compose.public.yml)

if ! command -v docker >/dev/null 2>&1; then
  echo "Installing Docker Engine from Docker's apt repository"
  sudo apt-get update -y
  sudo apt-get install -y ca-certificates curl gnupg
  sudo install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
    | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
  sudo apt-get update -y
  sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  sudo usermod -aG docker "$USER" || true
fi

if [ ! -f "$ENV_FILE" ]; then
  cp deploy/.env.public.example "$ENV_FILE"
  chmod 600 "$ENV_FILE"
  SECRET=$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')
  sed -i "s|^DEMO_DOMAIN=.*|DEMO_DOMAIN=${DEMO_DOMAIN}|; s|^PUBLIC_DEMO_SECRET=.*|PUBLIC_DEMO_SECRET=${SECRET}|" "$ENV_FILE"
  echo "Created $ENV_FILE with a new secret. Keep it stable; rotating it invalidates demo cookies."
else
  echo "$ENV_FILE already exists; leaving it unchanged."
fi

if command -v ufw >/dev/null 2>&1; then
  sudo ufw allow 22/tcp >/dev/null && sudo ufw allow 80/tcp >/dev/null && sudo ufw allow 443/tcp >/dev/null
  echo "Firewall: 22, 80, 443 allowed (enable ufw yourself if it is inactive)."
fi

"${COMPOSE[@]}" config --quiet
"${COMPOSE[@]}" build api web
if "${COMPOSE[@]}" run --rm prepare; then
  echo "Template prepared."
else
  echo "prepare refused or failed (expected on repeat runs: it will not overwrite an existing template)."
fi
"${COMPOSE[@]}" up -d
"${COMPOSE[@]}" ps
cat <<MSG

Next, from any machine:
  python3 scripts/smoke_live.py https://${DEMO_DOMAIN}
Then complete the manual acceptance checks in docs/DEPLOYMENT.md (TLS, cookies, 24h expiry, restart).
MSG
