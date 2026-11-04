# Judge guide

Fictional data only. No account, API key or external service is needed. Whenever the public URL is
published it will be recorded in `docs/submission-links.json` and the Devpost form; until then use the
local setup below (about two minutes with Docker-free tooling: Node 22, Python 3.12, uv).

## Two-minute path (Night Market)

1. Open the app and choose **Start your shift** (Night Market).
2. Acknowledge the draft notice, start, and choose *Escalate to operations lead*.
3. Open **Show all updates**: rain risk rises to 85 and indoor capacity drops to 0.
4. The run **stops**: no modeled rule covers these facts. That is the ghost path. Open the source to see
   the clause ("move indoors") that never addresses a full venue.
5. **Test a proposed rule**, add a choice for the current facts, save, acknowledge that it is unapproved, rehearse it,
   then **Compare** with the parent. The original history is preserved.
6. Verify replay and export the comparison (JSON or print).

A second fixture, Customer Support, stops on an *overlap* (two rules match) instead.

## What to look for

- **Honest engine:** it stops on zero or multiple matches rather than guessing; deviations are recorded.
- **Provenance:** every rule links to quoted source text; citations locate text, they never approve it.
- **Reproducibility:** replay recomputes the state hash from the append-only event ledger.
- **Safety:** conditions are declarative data, never executed code; public mode isolates temporary workspaces.

## Limits (stated plainly)

Rules in the fixtures are seeded drafts; PDFs must be text-based (256 KiB, 20 pages); this is a rehearsal and
documentation-testing tool, not a live emergency system. Public workspaces expire (see the in-app notice).
