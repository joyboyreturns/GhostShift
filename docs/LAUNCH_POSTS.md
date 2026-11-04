# Blog and social drafts (not published)

Publish only after the facts below are true. Bonus prizes need a genuine third-party blog post and a
social post that **begins with `#KiroweenHackathon26`**; both must contain original insight, not promotion.
Replace every `[FILL]` with something that actually happened. Delete a paragraph rather than invent it.

## Social post (draft, under 500 characters)

#KiroweenHackathon26 [FILL: one concrete thing you learned using Kiro, e.g. what a hook caught or how a
spec changed a design decision]. I'm building GhostShift: rehearse a procedure against a deterministic
engine and it stops where the document has no answer, instead of guessing. [FILL: link to app or repo]

## Blog outline

1. **The problem:** procedures read as complete until two ordinary problems happen together (late vendor,
   rain, full indoor space). The missing instruction is the "ghost path".
2. **The idea:** treat a human procedure like code: source-linked decision graph, deterministic engine,
   append-only ledger, replay and forks. It refuses to invent an answer; unapproved fixes stay experiments.
3. **Architecture:** FastAPI/Pydantic engine, declarative conditions (no eval), event ledger with state
   hashes, React/Zod front end, public-mode workspace isolation. Include one diagram.
4. **How Kiro was used (true only):** the engine spec and tests from the first session and the bug they
   caught; `[FILL: ghost-scan spec session outcome]`; `[FILL: hooks that fired, with their real output]`;
   `[FILL: MCP rehearsal session]`. State what Codex and Claude Code did separately.
5. **Challenges:** replay needs pinned inputs, not just a seed; a cited rule can still be an unsupported
   interpretation; throttling ended the first Kiro session. `[FILL: new ones]`
6. **What's next:** keep clearly separate from what works today.
Mention that the post is part of the Kiroween 2026 hackathon and include the public URL in the Devpost form.
