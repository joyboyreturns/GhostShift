# Session 3: Replay Lab specification (retrospective, disclosed as such)

The Replay Lab (apps/web/src/routes/ReplayLab.tsx, services/api session replay/fork/report code) was
implemented before this session. Replace `.kiro/specs/replay-lab/README.md` (a placeholder) with real
`requirements.md`, `design.md` and `tasks.md`. Derive them from the code and tests, and say in the first
lines of each file that they describe existing behavior. Then:
- Identify every requirement without a test and every behavior without a requirement.
- Implement tests (and minimal fixes, if tests expose bugs) for the three most important gaps.
- Mark tasks done only when verified. Record bugs found. Do not change engine semantics.
`make lint typecheck test` must pass.
