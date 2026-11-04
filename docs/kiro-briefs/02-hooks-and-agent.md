# Session 2: Hooks and a custom agent that really run

Read AGENTS.md and Kiro's current documentation for agent hooks and custom agents (use your own tools
to find them; do not rely on memory of the format). Create only configurations that Kiro actually loads.

## Build
1. **Custom agent** in `.kiro/agents/` (a "ghostshift-reviewer"): scoped tools, a prompt that reviews diffs
   against AGENTS.md rules (no eval, no `any`, no silent excepts, no logging source content, immutability
   of sources/playbooks), read-only tools plus the ability to run `make lint` and tests.
2. **Hooks** (2 to 3, genuinely triggered):
   - After edits under `services/api/app/engine/**`, run the engine test subset and report failures.
   - After edits to `fixtures/**` or `.kiro/**`, run `python3 scripts/submission_audit.py` and surface FAIL lines.
   - Before commit or at agent stop, run a check that `.kiro/` is not ignored and no secrets are staged.
   Use the existing `scripts/submission_audit.py`; add small scripts under `scripts/hooks/` only if needed,
   each with a test.
3. Prove each one executes: trigger it in a real session, quote the actual hook output into
   `docs/kiro-evidence.md` under a new dated section. If a hook cannot be made to fire, say so and remove it.

## Done means
Every file you add is loaded by Kiro and exercised at least once; the evidence section states exactly
what fired and what the output was; `make lint typecheck test` still pass.
