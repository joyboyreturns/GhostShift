# Cinematic incident experience

Codex implementation, November 3, 2026. Reuses the existing engine and APIs; no engine changes,
new migrations, LLM services, or Kiro sessions.

## Walkthrough

Home → **Start your shift** → read **The last dry hour** briefing → acknowledge the fictional,
unapproved model → **Start rehearsal**. Choose escalation. The engine applies the actual weather
inject and stops at the uncovered rain/capacity decision. Use **Next update** or **Show all updates**
to inspect recorded dispatches. These controls never advance the engine or withhold the active decision.

The finding links directly to source evidence, Replay Lab, and an unapproved proposal form. Enter
your own rationale and action using **Add choice for current facts**. Review its conditions and
destination, save, acknowledge, rehearse, and compare with the preserved parent. The comparison
shows actual findings and the first differing recorded choice. Export the existing comparison JSON
or print the report. Completion establishes only that these modeled inputs reach the modeled end.

Customer Support has a shorter authored briefing and a real overlap reveal. Own-procedure scenarios
use the same command room with neutral event-derived text. **Inspect conditions & history** switches
to the detailed presentation; `?view=incident|inspect` survives refresh. Run URLs remain compatible.

## Data and authority

- Authored copy is presentation metadata, selected using the catalog's exact scenario, version and
  document identity. Proposed/custom versions fall back to neutral text. No narrative metadata
  contains graphs, choices, outcome values, authority or policy evaluation.
- Dispatches come from durable session events. Fact changes compare consecutive snapshots,
  including the initial scenario facts for the first event. Future injects are not narrated early.
- The Night Market capacity guard is explicitly identified as a modeled assumption. Citations
  locate source text; they cannot approve that interpretation or a proposed response.
- Branches use actual parent IDs from the session/library APIs. The map includes current, available
  parent, and loaded children/siblings; **Load older runs** pages discovery in batches of 50.
  Missing parent details are described as unavailable. No disconnected roots are joined together.
- Choice writes retain expected revisions. Errors preserve the decision and restore server state.
  Forks preserve parent inputs; policy proposals are separately recomputed and remain unapproved.
- The debrief and comparisons use API results. There are no invented real-world impacts, risk scores,
  probabilities, countdowns or implied policy approval.

## Presentation

Desktop pairs dispatches with current facts and the active decision. Mobile stacks them and supplies
an active-decision jump link. Source, proposal and decision anchors are keyboard accessible. Event
history remains available with checkpoint forks. Accessible status text announces the active decision.

Audio defaults off and is generated locally with Web Audio only on a user-requested next update.
Unavailable audio produces a visible text notice and does not block playback or decisions. Reduced
motion disables dispatch entrance animation. No browser storage is required: view preference lives
in the URL and presentation playback resets on refresh or changing views; rehearsal state remains
server-owned. Authored atmosphere is identified as fictional in the briefing.

See VALIDATION.md for actual checks and screenshots/README.md for local captures. Target-server
Docker, HTTPS and hosted acceptance remain pending. See submission-draft.md for recording material.
