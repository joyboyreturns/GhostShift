# Session 4: Source Studio specification (retrospective, disclosed as such)

Same method as session 3 for Source Studio: document import (text, Markdown, text-based PDF with page
provenance), segmentation with stable references, draft rules, human review and approval, immutable
revisions. Replace `.kiro/specs/source-studio/README.md` with real requirements/design/tasks that say
they describe existing behavior. Find gaps (especially PDF edge cases, oversized input, reference
stability) and add tests, with minimal fixes if tests expose bugs. Never log uploaded source content.
`make lint typecheck test` must pass.
