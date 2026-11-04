# Kiro session briefs

Prepared 2026-11-05 by Claude Code. **None of these sessions has been run.** Each brief is a
self-contained prompt for one real Kiro CLI session. Kiroween scores Kiro use, so these exist to
produce genuine, inspectable Kiro work. They are not evidence of any Kiro usage themselves.

## How to run (you run it; it spends Kiro credits)

1. Redeem the hackathon credits, then `git status` must be clean.
2. `python3 scripts/kiro_session.py <slug> docs/kiro-briefs/<file>.md` (add `--interactive` to
   steer by hand; interactive output is not logged, so copy relevant transcript into the evidence file).
3. Review the diff. Run `make lint typecheck test`. Fix or reject anything wrong; failures go in the evidence
   record, not away.
4. Record attribution in `docs/kiro-evidence.md` (what Kiro wrote, what you or Claude/Codex corrected).
5. Commit with a message that names the session slug.

The runner writes `.kiro/evidence/<date>-<slug>.log` and `.json` (measured metadata only).

## Order and budget (4,000 free credits; actual cost per session is unmeasured, so check after each)

| # | Slug | Brief | Why it matters |
|---|------|-------|----------------|
| 1 | `ghost-scan-spec` | 01-ghost-scan.md | Spec + implementation of a genuinely new capability (innovation + Kiro depth). Largest session. |
| 2 | `kiro-hooks-agent` | 02-hooks-and-agent.md | Hooks and a custom agent that really execute. Required by the rubric to be real. |
| 3 | `replay-lab-spec` | 03-replay-lab-spec.md | Replaces a placeholder spec; retrospective, so disclose that. |
| 4 | `source-studio-spec` | 04-source-studio-spec.md | Replaces a placeholder spec; retrospective, so disclose that. |
| 5 | `mcp-rehearsal` | 05-mcp-rehearsal.md | Kiro uses the GhostShift MCP server on a playbook; produces steering + demo footage. |

If credits run short, do 1, 2 and 5 first. After each session run `python3 scripts/submission_audit.py`.

## Rules every session must follow (copied into each brief)

AGENTS.md rules apply: no eval or executable user expressions, no LLM dependency, no auth system,
no silent exception handling, no logging of uploaded source content, no TypeScript `any`, migrations
for schema changes, Zod validation of API responses, original sources and approved playbooks immutable.
