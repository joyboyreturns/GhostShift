# Public-demo hardening — Milestone 5

Codex-authored integration. The deterministic engine and dependency lockfiles are unchanged; no
additional Kiro model calls were made. These controls are tested locally. There is no hosted public
URL yet, and Docker images have not been built/run because this machine has no running Docker daemon.

## Isolation and lifetime

Local development continues to use services/api/ghostshift.db with no workspace expiry. Native Vite
now binds 127.0.0.1 by default. The development Compose file still publishes only loopback ports.

PUBLIC_DEMO=true selects a separate data path. An explicit offline `prepare` command migrates a new,
empty SQLite file and seeds only the two fictional fixtures. It never copies the user's development
database or overwrites an existing template. Startup verifies a template marker, schema revision,
fixture source text/hashes/segments, graph/scenario contents, and absence of personal sessions,
proposals, reviews or extra versions. A workspace backup is not accepted as a clean template.

Each anonymous visitor gets a random workspace identity and an HMAC-signed expiration token. The
cookie is host-only, HttpOnly, Secure and SameSite=Strict; production uses the __Host- prefix and
requires HTTPS. Insecure cookies are allowed only with explicit HTTP loopback test configuration.
A persistent random secret is required and never sent to the frontend. The API copies the clean
fixture template into a separate 0600 database under a dedicated 0700, marked directory. Database
connections use that visitor's file, so UUID guessing or sharing a run URL does not grant another
visitor access. All sessions, documents, proposals, approvals and reports remain in the same scope.

The browser bootstraps its catalog/cookie before route queries. It shows an expiry notice, export
reminder and confirmed **Start fresh workspace** control. A valid POST with an empty JSON object is
required to reset access; GETs and invalid reset bodies do not rotate the cookie. Reset leaves the
old data intact until expiry. Lost/cleared cookies lose access; this is not an authenticated account
or a recovery service. Review names remain user-supplied attestations.

Default TTL is 24 hours. Expired data becomes inaccessible immediately; startup, new allocations and
a background job every five minutes remove expired database files and WAL/SHM sidecars. Shared file
leases prevent deleting a workspace while a request uses it. Cleanup failure makes health/writes
unavailable and emits a content-free maintenance error. Retention does not weaken immutable-record
triggers or delete rows inside approved histories. A directory marker and strict filename grammar
limit deletion to this store's ephemeral files. Backup retention is not included: public temporary
workspaces should not be backed up by an infrastructure-wide job without a separate retention policy.

A process lease enforces one public API instance per workspace directory. This makes in-memory rate
limits explicit and prevents silently multiplying limits by adding workers. Schema-mismatched
workspaces fail with an actionable conflict and remain intact until expiry; no request migrates them.
A fresh workspace is required after an incompatible release. Server clocks must remain accurate.

## Limits and errors

| Control | Default |
| --- | --- |
| JSON request body | 524,288 bytes, including streamed bodies regardless of Content-Length |
| Body arrival deadline | 15 seconds total |
| JSON nesting | 64 levels; nonfinite numbers and invalid Unicode rejected |
| Writes | 30 per minute per client IP |
| Reads | 240 per minute per client IP; health/preflight excluded |
| New workspaces | 5 per hour per client IP, including cookie resets |
| Active/unpurged workspaces | 200 globally |
| Main database size | 16 MiB per workspace using SQLite page limits |

Rate bookkeeping is bounded to 10,000 keys and fails closed at capacity. Production Compose also
limits API concurrency/processes/memory. Database quotas do not include transient WAL/SHM overhead;
provision disk capacity above the 200 × 16 MiB main-file bound. The public API has no documented
multi-instance/distributed mode. IP limits assume the supplied direct Caddy→API topology; CDN/proxy
changes require verifying the trusted client address before deployment.

Public requests enforce the configured Host/Origin and reject cross-site browser requests. Writes
require application/json; body overflow, timeouts, admission limits, expired scopes and storage
quotas return consistent JSON errors with useful status codes. Rate responses include Retry-After.
API responses are no-store/nosniff. SQLite can automatically abort a transaction on SQLITE_FULL;
the connection wrapper restores rollback bookkeeping so the original quota error remains visible
and failed inserts do not leave partial source records. Successful writes are never replayed because
a response verification failed (the M4 commit-aware retry guard remains in use).

Caddy serves the production build and proxies /api on the same origin. It supplies a body/header
limit, CSP, framing restrictions, referrer policy and HTTPS configuration. Inline styles remain
allowed for React Flow; inline scripts/eval are not allowed by the policy. Public Swagger/OpenAPI
routes are disabled. Application/provider keys do not appear in the browser. No paid AI service or
LLM dependency was added. This is bounded demo hardening, not a claim of a completed security audit.

## Offline operations

From services/api, using the existing uv environment:

```sh
uv run python -m app.services.demo_admin prepare --output /absolute/path/template-0003.db
uv run python -m app.services.demo_admin cleanup
uv run python -m app.services.demo_admin backup --source /absolute/path/input.db --output /absolute/path/new-backup.db
```

Cleanup reads PUBLIC_TEMPLATE_PATH/PUBLIC_WORKSPACE_ROOT and the configured public environment.
It can run alongside the API; directory/file locks coordinate allocation and active requests.
Backup uses SQLite's snapshot backup operation, checks integrity and foreign keys, writes 0600,
and refuses existing output paths. Restoration is a deliberate offline operation: restore to a new
path, verify it, then point the service at the restored file. Tests restore a real completed choice
and reproduce its pinned session and hashes through the actual replay service. They also show that
this private backup is rejected as a public template. No production restore was performed.

## Verified locally

- 142 backend tests and 4 frontend unit tests, including 16 public-demo integration tests.
- 11 existing browser tests plus one separate full browser journey through Caddy's production build.
- Different browser contexts cannot fetch another scope's imported source or run/report; proposed
  policy execution, replay verification, reports and reset still work in the isolated deployment.
- Real quota exhaustion preserves successful records; cleanup skips an active lease then removes all
  expired sidecars. Invalid/expired/tampered tokens, reset validation, Host/Origin/content-type guards,
  streamed-body limits, body deadlines, capacity, schema mismatches and a second server are tested.
- Native Caddy 2.11.7 configuration validates. Production Compose interpolation validates. The public
  browser test uses explicit HTTP loopback configuration; live HTTPS/TLS and Docker runtime are unverified.
- npm audit --omit=dev reports zero findings. pip-audit 2.10.1 audited all 39 installed Python
  distributions with zero known findings and no skipped packages. Full npm audit reports 12 moderate
  development-toolchain entries via [the minimatch advisory](https://github.com/advisories/GHSA-g3hv-75wg-m249).
  Those tools do not ship in the static production image. No incompatible dependency upgrade was applied.
- CI configuration was added with pinned action commits and checksum-verified Caddy installation;
  it has not executed on GitHub because this repository is not published.

Implementation references: [Starlette ASGI middleware](https://www.starlette.io/middleware/),
[Caddy request body limits](https://caddyserver.com/docs/caddyfile/directives/request_body), and
[Caddy proxy behavior](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy).
