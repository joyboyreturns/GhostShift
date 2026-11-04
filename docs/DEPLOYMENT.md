# Deployment handoff

The production configuration is ready for server verification. **No public deployment has happened.**
The native production frontend/Caddy/API journey passes locally and in GitHub CI. Production images now build and pass the actual container browser journey on local Linux/arm64
Docker, including restart persistence and expiry cleanup. Real target-server deployment and HTTPS
still need verification. Linux/amd64 Docker verification also passes in GitHub CI. See RELEASE_READINESS.md and the
container evidence under docs/evidence/.

Public hosting is deferred until after November 5, 2026 at the user’s request.

## Information needed when hosting resumes

Provide an Ubuntu SSH host alias/account and the intended demo hostname. Configure SSH access using
your usual key setup; private keys should not be pasted into chat or committed. The hostname needs
an A record pointing at the server. The supplied configuration expects ports 80/443 available and
one API instance behind Caddy. The public repository is https://github.com/joyboyreturns/GhostShift
(verified publicly readable November 3, 2026). Publish reviewed changes separately; repository
visibility does not establish application hosting.

Nothing is needed to keep using the local preview at http://localhost:5173.

## Server commands once the target is available

From the checked-out project root on an Ubuntu host with Docker Engine and Compose:

```sh
cp deploy/.env.public.example deploy/.env.public
chmod 600 deploy/.env.public
python3 -c 'import secrets; print(secrets.token_urlsafe(48))'
```

Put the intended hostname and generated secret into deploy/.env.public. It is ignored by Git and the
Docker build context. Keep the secret stable across restarts; rotating it invalidates existing demo
cookies. Never set PUBLIC_TEMPLATE_PATH to a local/private development database.

```sh
docker compose --env-file deploy/.env.public -f deploy/compose.public.yml config --quiet
docker compose --env-file deploy/.env.public -f deploy/compose.public.yml build api web
# First deployment only: explicit migrations/seeding into a new clean fixture template.
docker compose --env-file deploy/.env.public -f deploy/compose.public.yml run --rm prepare
docker compose --env-file deploy/.env.public -f deploy/compose.public.yml up -d
docker compose --env-file deploy/.env.public -f deploy/compose.public.yml ps
```

The API image installs locked runtime dependencies, runs as uid 10001 with a read-only root filesystem,
and stores only dedicated public data in /data. The one-off prepare service explicitly migrates and
seeds a new fixture template before the API starts. API startup never creates tables or runs migrations;
missing/outdated templates fail closed. Do not repeat prepare on routine restarts: existing templates
are validated and the preparation command refuses to overwrite them.
Caddy serves only the built frontend. Only web publishes ports; the API has no host port. The API's
forwarded-header trust is appropriate only while it remains reachable through this private proxy
network. The configuration has no automated publishing/deployment action.

Caddy handles HTTPS for the configured domain. DNS, certificate issuance, firewall and the resulting
browser security/cookie behavior must be checked on the real host. Do not claim those passed from
local HTTP tests. If this Ubuntu server already has a proxy or services on these ports, integrate
with that topology and reverify client-IP handling rather than launching competing listeners.

## Acceptance checks on the deployed host

Verify /api/health returns ok; normal navigation and a deep simulation/report URL load the SPA;
HTTPS cookies are Secure/HttpOnly/SameSite=Strict; two independent browser profiles cannot share
source/session/report data; the complete gap → proposal → unapproved replay/comparison → JSON report
journey passes; and configured error/rate/retention controls remain effective. Observe a 24-hour
expiry/cleanup cycle or test a shorter allowed TTL in a staging deployment. Confirm volume ownership,
container health, restart persistence, memory/disk bounds and real TLS before supplying a judge URL.
Use fictional documents in the public demo and retain its expiry/export notice.

## Maintenance and upgrades

The API prunes expired scopes at startup and every five minutes. Health becomes unavailable if
maintenance fails. Inspect infrastructure logs without enabling raw document/request-body logging.
A manual sweep is available using the same service environment:

```sh
docker compose --env-file deploy/.env.public -f deploy/compose.public.yml exec api .venv/bin/python -m app.services.demo_admin cleanup
```

Keep public data on local persistent storage supporting SQLite WAL and POSIX file locks. Do not use
an unsupported shared/network filesystem or add API replicas: the process lease deliberately rejects
a second instance. Storage limits bound main database pages; leave room for WAL/SHM, images and logs.

For a schema change, prepare a new template filename (for example template-0004.db after such a
migration exists) and deploy it explicitly. Existing incompatible demo scopes fail closed and remain
preserved until expiry; users start fresh. No request migrates old data. Backups of the **local**
development database can use the snapshot command in PUBLIC_DEMO.md; public temporary workspaces
are intentionally ephemeral. Copying the entire public volume into long-lived backups would defeat
the stated retention unless backup expiry is configured as well.

## Reproduce local production-path verification

Prerequisites: the normal Python/Node setup plus Caddy 2.11.7 (`brew install caddy` on macOS).

```sh
make e2e-public
```

This builds the actual frontend, prepares a fresh fixture-only database, launches an isolated API
and the same Caddyfile on loopback ports 8091/4174, tests two browser contexts and the proposal/report
workflow, then removes the marked temporary test data. It uses an explicit loopback-only insecure
cookie setting and does not verify public TLS. `make e2e` separately exercises the development-path browser journeys. GitHub CI is configured
to run both paths; see the actual workflow runs for remote results.


## Incident-experience launch acceptance

- [x] Publish incident-experience changes and release tooling (`9db8ab6`).
- [ ] Build and run the locked images on the target host; verify Docker health and restart persistence.
- [ ] Verify actual DNS/TLS, secure cookies, SPA deep links, isolation, quotas, retention and exports.
- [ ] In a fresh visitor profile: Start your shift → gap → source → authored proposal → alternate
  rehearsal → comparison → verified replay → exported JSON. Repeat at a mobile viewport.
- [ ] Confirm custom scenarios use neutral incident copy and proposed-policy runs stay unapproved.
- [ ] Check keyboard navigation, reduced motion and muted-by-default audio on the hosted build.
- [ ] Record deployment acceptance evidence, commit/image identifiers and the tested hostname.
- [ ] Only then add the judge-facing app URL to submission materials and record the public demo.

The native Caddy loopback suite is local evidence. It does not satisfy these target-host checks.


## Repeat actual container verification

Run `make e2e-containers` against an already running Docker daemon. When using a named context, set
`DOCKER_CONTEXT` (for example `DOCKER_CONTEXT=colima-ghostshift-validation make e2e-containers`).
The script creates a random Compose project with a clean fixture template, builds the real images,
binds Caddy only on loopback port 4180, runs the public browser test, restarts API/Caddy and checks
persisted data, then tests a 60-second workspace expiry and maintenance cleanup. The test overrides
HTTP/cookie/TTL/write-rate settings only in its private temporary configuration; production defaults
are unchanged. It removes only its own disposable containers/volumes, retaining built image caches.
Evidence is written to `artifacts/container-validation.json` and uploaded by CI. This is not a public
URL or TLS check. Use `python3 scripts/verify-containers.py --help` for context/port/report options.

## Fast path: provisioning script, smoke test and hosting options (added 2026-11-05)

`deploy/provision-ubuntu.sh` installs Docker if missing, creates `deploy/.env.public` with a fresh
secret (never overwriting an existing one), builds, prepares the template and starts the stack:

```sh
DEMO_DOMAIN=demo.example.org ./deploy/provision-ubuntu.sh
python3 scripts/smoke_live.py https://demo.example.org
```

`scripts/smoke_live.py` checks health, SPA deep links, security headers, workspace allocation and cookie
flags, a rehearsal with verified replay, and cross-workspace isolation. It passed against the local Caddy +
API production path with `--insecure-http` on 2026-11-05. It does not replace the manual TLS, DNS,
firewall, restart and 24-hour expiry checks above.

**Hosting options** (the deployment must stay up and free for judges until January 29, 2027):

- Any small Ubuntu VM with ports 80/443 (the stack is one API instance plus Caddy; the images have been
  verified on linux/arm64 and linux/amd64). Oracle Cloud's Always Free tier or a low-cost VPS both fit.
- No domain? Caddy can obtain certificates for a wildcard-DNS name such as `203-0-113-10.sslip.io`
  (replace with the server IP, dashes for dots). This depends on a third-party DNS service; treat it
  as a fallback and note it in the submission if used.
- Platforms without a persistent local disk are unsuitable: the API needs POSIX locks and SQLite WAL.

Do not publish the URL, or record it in `docs/submission-links.json`, until `smoke_live.py` and the
manual checks pass.

