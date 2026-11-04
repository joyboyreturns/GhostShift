# Local release quality review — November 4, 2026

Codex reviewed and refined the existing product under the user's chosen direction: restrained
Kiroween presentation and a full local release audit. No engine, API contract, schema, dependency,
Kiro artifact or deployment configuration changed. No Kiro session, publication or upload ran.

## Findings resolved

| Finding | Final behavior |
| --- | --- |
| Authoring fields could change while their earlier values were being saved. | Scenario, proposal, review, source-snapshot and draft-revision controls lock during their saves. Source/revision/approval writes also lock the other controls in that review workspace. Failed saves preserve entries. |
| Source edits could sit beside a draft save that still used the previous saved source. | Unsaved text blocks saving the draft; a visible message offers save-snapshot guidance or explicit discard. The message stays visible when the source editor closes. New snapshots still clear old citations. |
| Numeric/boolean membership operands suggested text facts. | Homogeneous lists suggest the matching scalar type. Empty/mixed lists suggest text, with the existing explicit type selector available. No values are coerced or invented. |
| Source Studio's Retry omitted the scenario request that could cause its error screen. | Retry includes the scenario list and avoids fetching a source without its playbook. Evidence, saved-model and review-record failures also offer local retries. Replay Lab no longer repeats the saved-run error twice. |
| Persistent artwork and motion competed with working content; entry fades could capture dim content. | No shared flying bats, graveyard footer, Studio cobweb, brand bob, entry fade, animated graph edges or repeating warning pulse. Static landing artwork and clearer labels retain the identity. Working-page status glows are reduced. |
| Missing-page copy and release summaries were stale. | Direct missing-page/loading language, current test counts, current screenshots and an explicit record of the remaining verification boundaries. |

## Audit and acceptance evidence

Reviewed existing source/model/scenario flows, API validation boundaries, immutable source and
approval handling, persisted choices, replay/fork/proposal comparisons, report evidence, PDF
isolation, error recovery and setup commands. Existing integration/property tests exercise the
data-integrity and concurrency invariants; the verified engine remains unchanged.

- `make lint`: Ruff, formatting, ESLint and Prettier pass.
- `make typecheck`: strict mypy and TypeScript pass.
- `make test`: **154 backend and 24 frontend tests pass**.
- `make e2e`: **31 Chromium tests pass**, with two workers and no retries. These include the
  real custom-procedure journey, both demo findings, approval/revisions, PDF provenance, saved
  runs, deterministic replay, parent isolation, unapproved proposals and parsed JSON downloads.
- Four new browser regressions cover scalar membership facts and failed/in-flight scenario saves;
  unsaved/failed/in-flight source snapshots and preservation of the original source; scenario-list
  recovery; and missing-record/missing-page recovery. One unit test covers membership type hints.
- Responsive journey checks cover ten routes at **360, 390, 768 and 1440 px**, heading/skip-link
  focus, reduced motion and page overflow. Phone/tablet/desktop and print-media captures were inspected.
- A supplemental seven-route Chromium check passes at **720 CSS px with DPR 2**, the reflow
  dimensions of a 1440px display at 200% browser zoom. It verifies overflow and keyboard skip
  access. This emulates layout dimensions; it does not operate the browser's native zoom control.
  Its JSON and captures are local under `artifacts/quality-review/`.
- `make e2e-public`: production Vite build and **one loopback Caddy/API browser test pass**,
  including separate visitor workspaces and the actual proposal workflow.

Native browser tests used a newly migrated database under a dedicated `/private/tmp/ghostshift-quality.*`
directory. Public-mode tests prepared their own clean template and disposable visitor workspaces.
The private development database was not used. Current screenshots are in `docs/screenshots/`;
additional captures and traces are local Playwright artifacts.

The first five-worker run had two long-journey timeouts; both pass with the explicit two-worker
configuration without raised timeouts or retries. A new source regression initially used an exact
implicit-label lookup that included textarea content; it now locates the textbox by accessible name.
The focused regressions and subsequent complete suite pass. Lint initially required access to the
existing uv cache; approved runs completed the checks.

## Boundaries

This is a local product review, not a guarantee of zero defects or a comprehensive security or
accessibility certification. Verification used the installed locked dependency environments and
Chromium; no fresh-machine, Safari, Firefox, assistive-technology or physical-printer certification
is claimed. The known Starlette/httpx test-client deprecation remains; changing backend dependencies
was unnecessary for these fixes. Prior Docker restart/expiry evidence is unchanged; no new container
run was needed because the deployment and backend paths did not change.
Development browser logs can still emit React Flow's transient container-size warning during
route/media transitions; graph rendering and interaction checks pass. The lazy-module recovery
test intentionally logs React's caught load error.

Sources and conditions still require human interpretation. Draft fixtures and proposal experiments
remain unapproved. No new feature scope, OCR, authentication, collaboration or runtime AI was added.
The existing local narrated recording demonstrates the same workflow with the earlier visual theme;
it was retained, not rerecorded or uploaded. Public hosting and target-server/TLS acceptance remain
deferred and unclaimed.
