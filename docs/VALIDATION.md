# Validation — foundation, engine, rehearsals and policy workflow

November 3, 2026. M0–M6 are implemented locally. Kiro authored the initial engine specifications,
implementation and 60 tests; subsequent Codex review and integration are separately attributed in
kiro-evidence.md. No additional Kiro model sessions were used for M3, M4, M5 or M6.

## Kiroween visual overhaul re-validation (November 3, 2026)

This was a presentation-only change (see DESIGN.md). It added the self-hosted font packages
`@fontsource-variable/space-grotesk` 5.3.0 and `@fontsource-variable/jetbrains-mono` 5.3.0 to
package.json and package-lock.json. After the change, these commands were run from a clean state
with no dev servers running:

| Command | Result |
| --- | --- |
| `make lint` | Pass: Ruff clean, 55 files formatted; ESLint and Prettier clean |
| `make typecheck` | Pass: mypy, no issues in 35 source files; `tsc -b` clean |
| `make test` | Pass: 154 backend tests (1 known Starlette/httpx deprecation warning) and 9 frontend unit tests |
| `make e2e` | Pass: 15 Playwright browser tests |
| `npm run build` (apps/web) | Pass |

After the Halloween artwork pass (decor.css, components/decor/Spooky.tsx), all five commands
above were rerun and passed with the same counts.

Screenshots in docs/screenshots were recaptured at 1280 px and 390 px against a freshly seeded
database and visually inspected. `make e2e-public` (needs the Caddy CLI) was not rerun for this
change. The frontend markup it relies on is unchanged.

## GitHub Actions CI (November 3, 2026)

The workflow first ran after the repository was published. Two pre-existing CI defects were found
and fixed:
- `scripts/install-caddy-ci.sh` compared a SHA-256 digest against Caddy's checksum manifest, which
  publishes SHA-512 values. It now uses SHA-512, and this was checked against the real 2.11.7
  linux_amd64 archive.
- `apps/web/package-lock.json` recorded only the darwin-arm64 Tailwind oxide binding (npm
  optional-dependency bug), so `npm ci` on Linux could not load Tailwind. The other platform
  entries were added from the npm registry's real tarball and integrity metadata; no versions
  changed.

After both fixes, the "Verify GhostShift" workflow passed on `main` on ubuntu: install, Caddy
install, lint, typecheck, tests, `make e2e`, `make e2e-public`, `npm audit --omit=dev` and
pip-audit.

## Environment and dependencies

Python 3.12.13; Node 22.22.3; npm 10.9.8; uv 0.11.25. package-lock.json and services/api/uv.lock
record actual installed resolutions. Native/Docker installs use npm ci / uv sync --locked.
M6 adds locked pypdf 6.21.4 for local PDF parsing; no AI keys or external runtime service are required.
The earlier locked install completed with 239 npm packages and the existing backend environment.

Resolved versions include React/React DOM 19.3.1, React Flow 12.12.1, React Router 7.18.5, Vite 8.3.5,
TypeScript 6.0.3, FastAPI 0.162.0, Pydantic 2.14.2, SQLAlchemy 2.1.6, Alembic 1.20.1, pytest 9.2.0,
Hypothesis 6.170.14, Ruff 0.17.3, mypy 1.20.2 and Playwright 1.63.0.

## Commands actually run

| Command (root unless noted) | Result |
| --- | --- |
| make lint | Passed Ruff lint/formatting and frontend ESLint/Prettier. |
| make typecheck | Passed strict mypy on 35 application files and TypeScript. |
| make test | Passed 154 backend tests and 9 frontend unit tests. |
| make e2e | Passed 15 browser tests using the actual API, Vite and SQLite, with 4 workers. |
| make e2e-public | Passed one separate browser test through the actual production build/Caddy/API, using isolated temporary data and two visitors. |
| make seed | Passed; migration 0004 and existing fixtures are current. |
| npm run build (apps/web) | Passed production bundle generation, with lazy workspace, scenario, replay, source and comparison routes. |
| uv run alembic check (services/api) | Passed: no new upgrade operations detected. |
| make engine-demo (M2 validation) | Both real draft fixtures return uncovered/weather and overlap/refund. Engine code unchanged since M2. |
| docker-compose config --quiet (earlier foundation verification) | Passed standalone Compose 5.5.1 configuration validation; no runtime build claimed. |
| sh -n scripts/setup.sh scripts/dev.sh (earlier verification) | Passed shell syntax. |

## Backend evidence

The suite retains all foundation/segmentation tests, 60 original Kiro engine tests, 22 Codex engine
review regressions/properties and the M3 persisted rehearsal integration tests. M4 adds proposal,
review, revision, source modeling, ancestry/compatibility, migration and concurrency regressions.
API tests migrate a fresh **file-backed SQLite** database and exercise actual services and commits.

Coverage includes invalid topology/foreign source references; deterministic replay and branch
isolation; event-prefix preservation; corrupt-state rejection; atomic expected-revision choices;
concurrent same-run choices with exactly one commit; unchanged parents; consistent reader snapshots;
rollback between revision claim and event append; snapshot retries when unrelated writes commit;
no retry after a successful write whose response verification fails; gap/overlap proposals through
the same engine; forced uncited status for changed rules; no proposal-to-policy promotion; immutable
proposal/review records; source/approved-version immutability; explicit full human review, stale hash
rejection and pinned authority on older runs; draft version ancestry and compatible scenarios;
source namespaces across revisions; blank imports becoming real drafts; and migration
upgrade/downgrade/re-upgrade preserving records and original immutability guards.

## Browser and visual evidence

Fifteen tests pass: four Source Studio/import/keyboard/mobile tests, four persisted rehearsal tests,
three policy workflow tests and four workspace/PDF/Replay Lab/action-authoring tests. They cover actual choices and source evidence, genuine missing and
conflicting-rule stops, persistence after reload, replay verification, forks/deviations/comparison,
actual JSON downloads parsed with Zod, and mobile rehearsal/report widths. New tests cover saved
proposals → changed-policy rehearsal → completion → explicit comparison with an unchanged parent,
still-unapproved reports, restoring saved proposals, keyboard approval and immutable review records,
new source snapshots with cleared/reselected evidence, and manual modeling of an imported procedure
on mobile followed by loading its real saved graph in Source Studio. Condition removal preserves the
remaining operand; empty models cannot be approved.

Desktop comparison/review and mobile authoring screenshots were inspected. This exposed invisible
input borders in the first review UI; the controls were styled and inspected again. The real browser
suite also exposed SQLite contention, which was corrected with bounded rollback/retry of uncommitted
writes. Tests are not configured to hide failures through Playwright retries. Screenshots and report
artifacts are under ignored apps/web/test-results. M3 Chromium print emulation confirmed a white report
layout with content/source visible and navigation hidden; no physical printing or PDF pagination
verification is claimed.

## M5 production-path and hardening verification

Sixteen additional backend integration tests exercise genuine per-visitor SQLite scopes and copied
fixtures; cross-scope source/session/report/proposal access; signed/expired/malformed cookies;
validated reset without state changes on GET/invalid input; Host/Origin/content-type protection;
rate/admission limits across cookie resets; bounded streamed/slow/deep/nonfinite/invalid-Unicode JSON;
real SQLite page-quota exhaustion and rollback; active-lease retention protection and sidecar cleanup;
capacity and clean-template checks; schema conflicts without request migrations; observable maintenance
failure; enforced single API instance; verified backups/restored actual replay; and rejection of private
backups as public templates. Native development data is not copied into public mode.

`make e2e-public` builds the frontend and serves it through the same Caddyfile used by deployment.
It tests a complete gap/proposal/comparison/replay/report journey, separate browser scopes, persisted
reload, fresh-workspace reset, security headers and mobile width. Its mobile report screenshot was
inspected. It uses explicit HTTP loopback test settings and does not prove live HTTPS.

Caddy 2.11.7 was installed and its configuration validated. Production Compose interpolation passed
with synthetic validation-only values. Official Caddy checksum manifests were fetched and the Linux
archive entry verified for the CI installer. (Linux installation and GitHub CI were later run; see the GitHub Actions section below.)
all referenced action commits were resolved from their official repositories. M5 dependency
lockfiles were unchanged; M6 adds only pypdf. `npm audit --omit=dev` found zero vulnerabilities; pip-audit 2.10.1 audited all
40 Python distributions, including pypdf 6.21.4, with no known findings or skipped packages (M6 rerun). Full npm audit reports 12 moderate
development-tooling entries through the minimatch advisory; see PUBLIC_DEMO.md. No incompatible
transitive upgrade was forced. These audit results describe the checks performed, not a full security audit.

## Remaining limits

Starlette emits a non-blocking TestClient/httpx deprecation warning. A transient React Flow container
size warning appeared on some initial renders; source graphs render and selection assertions pass.
Docker image builds/runtime remain unverified because the daemon is unavailable; only configuration
was validated. Native services are the verified development path.

This is a **local preview**, not a published hackathon submission. Body/write/rate limits, anonymous
isolation/retention and backup restoration are locally tested. Before public release: verify Docker
runtime, DNS, HTTPS/cookies, persistent-volume behavior and the acceptance journey on the actual server. Reviewer names are local attestations without authentication. Semantic source correctness
requires human judgment; valid citations alone are insufficient. Manual authoring supports decision/action addition and explicit action/decision removal with
replacement; saved topology and citations are server validated. Custom scenario authoring, PDF text
extraction, version history and Replay Lab are implemented. AI extraction/suggestions remain optional
and unbuilt under the active no-LLM dependency constraint. At that verification point no public repository, hosted URL or video submission was claimed.
The repository is now publicly readable; see the incident-experience verification below.


## M6 local product verification

The final combined `make lint && make typecheck && make test && make e2e && make e2e-public`
completed successfully. Import ordering was subsequently cleaned up and lint was rerun. The production
bundle is rebuilt inside `make e2e-public`; its API/template use isolated temporary data on loopback.
A follow-up `uv run alembic check` reports no new upgrade operations. No remote service was deployed.

Twelve backend tests were added: seven workspace/scenario/history/report/UTC tests, four actual PDF
parsing/provenance/limit/report tests and one additional anonymous workspace discovery/authoring
isolation test. They exercise literal wildcard search, bounded pages/facts, invalid scenario targets,
version families across sources, corrupt ancestry, unchanged captured authority after later approval,
all graph-cited text in reports, PDF file hash/page/blank-page metadata, failed-import rollback,
subprocess timeout/capacity release, real PDF parsing and immutable provenance.

Five frontend unit tests exercise typed scenario values/invalid inputs and graph authoring isolation.
Four new browser tests exercise import → source modeling → own scenario/inject → actual rehearsal →
library recovery and exported evidence; Replay Lab keyboard checkpoint forks and parsed comparison
JSON; real PDF file upload and reloaded page citations; and action-step revisions/removal with the
original model preserved. Missing accessible select labels were fixed after the browser tests caught
them. The mobile library screenshot now waits for real loaded results, rather than capturing loading.

Desktop Replay Lab, comparison report and PDF source, plus the loaded mobile library screenshots were
visually inspected. Print-media comparison styles were exercised; no physical print/PDF pagination
claim is made. Parser memory protection on Linux is configured but this native macOS run does not
prove Linux resource enforcement or Docker runtime. See PRODUCT_COMPLETION.md for PDF limits.

Engine files and deployment/CI configuration have no diff from the M5 tree snapshot. No further Kiro
model sessions were used. These results describe local implementation checks, not hosted acceptance.


## Cinematic incident experience verification — November 3, 2026

Codex implemented and verified the incident presentation around the existing engine. No backend,
engine, migration, lockfile or original Kiro-artifact changes were needed. No Kiro session was launched.

| Check actually run | Result |
| --- | --- |
| `make lint` | Backend Ruff/format and frontend ESLint/Prettier passed, no lint warnings. |
| `make typecheck` | mypy on 35 application files and TypeScript passed. |
| `make test` | 154 backend tests and 15 frontend tests passed. |
| `DATABASE_URL=sqlite:////private/tmp/ghostshift-incident-e2e.db make e2e` | 19 real browser tests passed; final full run 46.3 seconds. |
| `make e2e-public` | Production frontend build and the Caddy/API public-workspace browser journey passed; final run 15.6 seconds. |
| `git diff --check` | Passed. |

Final frontend lint/typecheck were also rerun after adding keyboard scrolling to the dispatch log.
The existing FastAPI test-client dependency emits one Starlette/httpx deprecation warning during
backend tests; no new test warning or failure is treated as a success. Initial checks required access
to the existing uv cache outside the filesystem sandbox; approved reruns completed the checks.

Six additional frontend tests cover exact catalog/version/source matching, fallback for custom or
proposed versions, no premature inject narration, typed fact deltas, overlap and unchanged updates,
actual parent/sibling/child relationships, and differing recorded choices. Four additional browser
tests cover the full incident → proposal → comparison → parsed export workflow with unchanged parent,
inspect-view refresh, keyboard dispatch playback/scrolling, mobile/reduced-motion layout and source
evidence, failed-choice recovery, and unavailable-audio fallback. Existing custom-scenario, fork,
replay and public isolation tests remain in the passing suites.

Visual inspection covered the landing page, briefing, desktop command room, mobile Support run and
comparison report. A mobile branch-heading overlap found in inspection was corrected and a bounding-box
assertion now checks that heading against its explanatory text. A React sibling-key collision found
by the new full-journey test was corrected. Captures are listed in screenshots/README.md. The final report capture was refreshed with a passing full-journey test (14.7 seconds), temporarily
hiding sticky navigation during the element screenshot. Optional audio fallback was exercised; subjective sound quality and physical print pagination are not certified.

The public GitHub repository was verified at https://github.com/joyboyreturns/GhostShift on
November 3, 2026; prior statements about no public repository describe earlier verification points.
These incident changes are still local and uncommitted at this verification. Official submission
requirements were rechecked for preparation in submission-draft.md. Hosting, target-server Docker/TLS,
video publication and final submission remain pending. No judge-facing app URL is claimed.

## Release completion follow-up — November 3, 2026

`make lint`, `make typecheck` and `make test` passed again with the final incident experience
(154 backend and 15 frontend tests). The new `scripts/verify-containers.py` also passes Ruff and
format checks. The media recorder passes `node --check` and completed its real browser journey.

`python3 scripts/verify-containers.py --context colima-ghostshift-validation` built the real API/web
images in a dedicated Linux/arm64 Docker VM and passed the Caddy browser/isolation workflow, restart
persistence, expiry rejection and maintenance deletion. It used a random Compose project, clean
fixture-only template and loopback HTTP with test-only cookie/TTL/rate settings. Production defaults
were not changed. All of its disposable containers and volumes were removed. Actual report and
image identifiers are preserved in evidence/container-validation.json. CI now repeats container
verification on its own runner. This does not verify target-server DNS/TLS or publish an app URL.

The local MP4 has H.264 video, AAC stereo audio and optional English captions, exactly 170 seconds at
1440×1000. A contact sheet and a Kiro-attribution frame were inspected, and recorded comparison data
was checked against the real original/alternate results and unchanged parent. Narration is disclosed
system TTS. No uploaded video, final submission or personal eligibility attestation is fabricated.


The incident experience and release tooling were committed and pushed to `main` as `9db8ab6`.
The user explicitly deferred public hosting until after November 5, 2026 and requested a local
narrated recording for later upload. That local deliverable is prepared; no hosted URL or public
video is claimed. The dedicated Docker verification VM was stopped after container cleanup.
The MP4 was fully decoded without errors and its submission-artifact checksums matched.


### Published release verification

Commit `9db8ab63b3b888b28ef5cb4a5e73890dba9a38f7` passed the full GitHub Actions pipeline:
https://github.com/joyboyreturns/GhostShift/actions/runs/41629026438

The runner passed locked installs, lint/types/tests, 19 development browser tests, the native Caddy
public-workspace browser workflow, the production Docker workflow, npm runtime dependency audit
and pip-audit. The downloaded artifact confirms actual Linux/amd64 container builds, restart
persistence, expiry rejection and cleanup; its JSON is preserved in evidence/container-ci-validation.json.
A non-blocking annotation notes the pinned upload-artifact action’s Node 20 deprecation; the runner
executed it under Node 24 and artifact upload succeeded. No Kiro session or public app deployment
was performed. The follow-up commit contains only release documentation/evidence and hosting timing.

## Whole-product polish — November 3, 2026

Codex polished the existing two-fixture product locally. No AWS fixture or configuration,
deployment, Kiro session, engine change, schema migration, or new dependency was introduced.

The request boundary now explains network failures, unreadable responses and invalid response
shapes without displaying raw payloads or automatically retrying writes. Route rendering and
lazy-module failures have a reload/Home recovery screen. Path changes update the page title and
focus the main heading; query-only interactions retain focus. The skip link targets a focusable main.

Library search follows back/forward navigation, invalid offsets fall back to zero within the API's
existing bounds, and empty/out-of-range pages offer clear recovery. Imports freeze submitted inputs
while saving, retain failed text/file selections, explain oversized PDFs, and identify the saved
source independently of subsequent edits. Saves, approvals, revisions, choices and branches refresh
affected Library/run queries. Scenario-list, saved-run and comparison failures expose retry controls.

Shared layout refinements cover wrapping actions, readable panels, narrow forms, touch targets,
long identifiers, contained table scrolling and a corrected tablet header overflow. Print refinements
retain authority/evidence text, use clearer borders, hide interactive-only comparison links and reduce
splitting of metadata/rows. Existing reduced-motion and opt-in audio behavior is preserved.

Final commands all passed:

| Command | Result |
| --- | --- |
| `make lint` | Backend Ruff/format and frontend ESLint/Prettier passed. |
| `make typecheck` | Mypy (35 application files) and TypeScript passed. |
| `make test` | 154 backend tests and 23 frontend unit tests passed. |
| `make e2e` | 26 browser tests passed, including seven new polish tests. |
| `make e2e-public` | Production Vite build and local Caddy anonymous-workspace journey passed (one test). |

The new regressions cover request recovery/cancellation and validation details; Library history,
invalid offsets and empty-page recovery; failed/import-in-flight behavior and saved-source identity;
oversized PDF guidance; failed lazy-module recovery; and ten existing routes at 360, 768 and 1440px
with reduced motion, heading focus, skip-link keyboard access, overflow checks and screenshots.
Existing tests continue to cover both demo outcomes, custom authoring, replay, forks, proposals,
comparison exports, source provenance and public isolation.

Visual review included phone/tablet/desktop captures of the command room and authoring screens,
plus session/comparison print-media captures. Generated images are local Playwright artifacts under
`apps/web/test-results/polish-existing-journeys-*`. Print-media inspection is not certification of
physical printer pagination. The final production test used disposable fixture-only workspaces and
loopback HTTP; it does not establish public-host/TLS readiness.

The existing Starlette/httpx test-client deprecation remains. Browser runs can emit transient
React Flow container-size warnings during route/media transitions; graph display and interaction
checks passed. The lazy-module failure regression intentionally produces React's caught-error log.
The first lint/type/test attempts could not access the existing uv cache within the filesystem
sandbox; approved reruns completed all checks. These polish changes remain local and uncommitted.
