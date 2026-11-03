# Local application screenshots

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
