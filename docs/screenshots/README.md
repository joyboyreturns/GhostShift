# Local application screenshots

All application images below were refreshed November 4, 2026 after the restrained Kiroween
quality pass. Captures use real Chromium journeys against the dedicated disposable quality-review
database, at 1440 px (landing), 1280 px (desktop workflows) and 390 px (mobile). Library shows
fictional saved work produced by the tests. No responses were mocked for these captures. The
historical capture notes below describe earlier image versions. See [quality review](../QUALITY_REVIEW.md).

Recaptured November 3, 2026 after the Kiroween visual overhaul (see ../DESIGN.md). They were taken
with Playwright/Chromium against the real local API and a freshly migrated and seeded SQLite
database, with no mock data. Every procedure and scenario shown is explicitly fictional. These are
actual local application screens, not hosted acceptance evidence. Session IDs belong to disposable
runs. No original uploaded PDF binary is included.

- [Landing page](home.png): the Kiroween hero and workflow overview (decorative illustration).
- [Source Studio](source-studio.png): the real API graph with the weather rule selected and its cited text highlighted.
- [Simulation Room](simulation-room.png): the actual Night Market run stopped on the uncovered rain/capacity path.
- [Simulation Room, mobile](simulation-mobile.png): the same run at 390 px.
- [Session report](session-report.png): actual findings, stats and cited evidence.
- [Replay Lab](replay-lab.png): stored events, checkpoint scrubber and fork control.
- [Comparison report](comparison-report.png): the original run against a forked deviation, with evidence.
- [PDF source](pdf-source.png): extracted fictional text with page and blank-page provenance.
- [Library](library.png): saved rehearsals in a clean workspace.

The browser tests (`make e2e`) also write screenshots under `apps/web/test-results`.


## Incident experience captures — November 3, 2026

The latest real Playwright/Chromium runs refreshed home.png and simulation-room.png, and added:

- [Shift briefing](incident-briefing.png): exact-version Night Market role, fictional scene-setting and real starting facts.
- [Incident view on mobile](incident-mobile.png): Support overlap, source evidence and branch relationships at 390 px with reduced motion.
- [Proposed-policy comparison](incident-comparison.png): actual original uncovered path and the unapproved alternate, including the first differing choice and both source-backed reports.

These use the real local API with the isolated database `/private/tmp/ghostshift-incident-e2e.db`.
The other images above document earlier workflows; simulation-mobile.png is the earlier Night Market
capture. The new incident-mobile.png shows the current mobile presentation. All data is fictional.
The new comparison image captures the report element with sticky navigation and the skip link hidden during capture to prevent browser chrome obscuring report text. No hosted
application, public TLS, physical print or uploaded-video acceptance is implied.
