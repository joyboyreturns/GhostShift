# Release readiness — November 4, 2026

The product and submission preparation are complete locally. No public application URL, uploaded
YouTube video, entrant eligibility declaration, or final Devpost submission is claimed.

## Completed

- Cinematic incident experience with exact-version fictional briefings, real event dispatches, source
  diagnostics, branch relationships, unapproved experiments, comparisons and portable evidence.
- Native checks: lint, strict types, 154 backend tests, 24 frontend tests, 31 development browser tests
  and the production-built Caddy public-workspace browser journey. See VALIDATION.md.
- Local quality review: restrained Kiroween presentation, locked authoring fields during saves,
  explicit unsaved-source handling, correctly typed membership facts, working scenario-list retry,
  and refreshed application screenshots. See [QUALITY_REVIEW.md](QUALITY_REVIEW.md).
- Actual production Docker builds and browser verification, including unchanged documents/sessions
  after restarting API/Caddy and real token expiry/database cleanup with a short allowed TTL.
  [Machine-readable evidence](evidence/container-validation.json) records Docker 29.5.2 and the tested
  Linux/arm64 image identifiers. Disposable containers and test volumes were removed afterward.
- Repeatable `make e2e-containers` harness and GitHub Actions step. CI tests the runner's architecture
  separately. The published code passed the full GitHub pipeline on Linux/amd64, including
  container restart/expiry checks and dependency audits. See [CI container evidence](evidence/container-ci-validation.json).
  Neither environment certifies the eventual public host or its TLS configuration.
- Local narrated MP4 (2:50), optional English captions, recorded comparison JSON and measured chapter
  metadata under `artifacts/demo/`. Captured real browser actions; synthetic narration is disclosed.
  Media stays out of Git. See demo-script.md to reproduce or re-record with a human narrator.
- Submission write-up, genuine Kiro contribution record, screenshots and final-host acceptance checklist.

## Deferred public launch — after November 5, 2026

Public hosting is explicitly deferred until after November 5 at the user’s request. The requested
video deliverable is a local narrated recording; no upload is authorized or performed in this pass.

1. After that date, configure the intended SSH server and domain. No target or deploy environment is configured in
   this repository; the unrelated saved SSH alias is not assumed to be the deployment server.
2. Deploy and verify Docker on that target, actual DNS/HTTPS, secure cookies, persistence, isolation,
   limits and retention. Only then use its URL in the submission. See DEPLOYMENT.md.
3. Review the local video, upload it to the entrant's YouTube channel as public, and verify playback,
   captions and duration at the published link. No YouTube upload credentials/workflow are configured.
4. The entrant must personally verify eligibility, category choice and final claims, then submit the
   real app/repository/video links before the official deadline. GhostShift cannot attest these facts
   for the entrant. See submission-checklist.md and submission-draft.md.

The public repository already exists at https://github.com/joyboyreturns/GhostShift. The incident experience and release tooling were published as commit `9db8ab6`. CI results for
that code are available at https://github.com/joyboyreturns/GhostShift/actions/runs/41629026438.
The run completed successfully. The subsequent documentation-only commit records these results
and the user’s hosting deferral; it changes no tested application or deployment code.
