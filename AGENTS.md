# GhostShift development rules

The product brief is docs/PRD.md. Milestones 0 and 1 are complete and verified.
The Milestone 2 engine core is also verified: Kiro authored the initial specs/engine/tests, and
Codex made separately attributed review corrections. See docs/ENGINE_REVIEW.md and docs/kiro-evidence.md.
Milestone 3 persistence/replay/fork/report APIs and Simulation Room are verified and integrated by Codex
around the existing engine. See docs/PERSISTED_REHEARSALS.md.
Milestone 4 adds manual rule authoring, human review, immutable source/playbook revisions, proposals
and explicitly unapproved proposed-policy replay/comparison. See docs/POLICY_REVIEW.md.
Milestone 5 adds tested request/write limits, anonymous database isolation, expiry/retention, quota
handling, backup restoration checks, Caddy production-path tests and deployment/CI configuration.
See docs/PUBLIC_DEMO.md and docs/DEPLOYMENT.md. Local Docker runtime, restart persistence and expiry
cleanup are now verified; target-server deployment/TLS verification remains. See docs/RELEASE_READINESS.md.
Milestone 6 adds library/search, custom scenarios, version history, Replay Lab, action-step editing,
PDF text/page provenance, onboarding and portable comparison reports. See docs/PRODUCT_COMPLETION.md.
Public hosting is deferred until after November 5, 2026 at the user’s request. Local release
verification and a local narrated recording are complete. No new engine or Kiro session changes.
Kiro credits: on 2026-11-05 the user authorized real Kiro work for Kiroween (Kiro-authored source-studio and
replay-lab specs, tested hooks, MCP use, custom agents). Still do not launch a Kiro model session
without the user running or approving it each time; request the free hackathon credits first.
Record every session in docs/kiro-evidence.md with exact attribution (Kiro vs Codex vs Claude Code).
Never present hand-written config as Kiro usage, and never claim a hook ran unless it did in Kiro.

- React/TypeScript/Vite frontend in apps/web; FastAPI/Pydantic v2/SQLAlchemy backend in services/api.
- API prefix /api. Routes orchestrate services; presentation components do not interpret policy.
- Graph data comes from API responses validated with Zod. Never draw a fixture graph directly in React.
- Conditions are declarative data. Never use eval or user-authored executable expressions.
- Validate destination IDs and source references against the associated document.
- Original source records and approved playbooks are immutable. Changes create new records/versions.
- Evidence references locate text; they do not establish human approval. Seeded rules remain drafts.
- Keep .kiro/ in Git. These initial steering notes are authored by Codex, not Kiro usage evidence.
- Kiro owns substantial subsequent simulation, events, replay, branching, and reports implementation.
- No fabricated endpoints, success responses, test results, or development evidence.
- No LLM dependency, authentication system, or microservices in this milestone.
- Avoid TypeScript any, silent exception handling, and logging uploaded source content.
- Use semantic controls, keyboard access, visible focus, and reduced motion.
- Run make lint, make typecheck, make test, and make e2e for changes affecting the vertical slice.
- Keep package-lock.json and uv.lock in version control. Use npm ci / uv sync --locked.
- Use migrations for schema changes. Never create tables automatically in production startup.
- Public write limits, isolation and retention are locally verified. Do not claim public hosting or
  publish a judge URL before target-server Docker/TLS and deployment acceptance checks pass.
- Public mode uses one API instance, signed temporary workspaces and a clean, explicitly prepared
  template. Never seed public scopes from the private development database or weaken history guards.
