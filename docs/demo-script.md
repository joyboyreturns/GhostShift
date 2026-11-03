# Working-product demo — target 170 seconds

Recording script, not a claim of an uploaded video. Record real actions against a clean fictional
workspace. Rehearse the typing beforehand; preserve visible draft/proposal notices in the recording.

| Time | Screen and actual action | Narration |
| --- | --- | --- |
| 0–15s | Home → Start your shift → Night Market briefing. | “The vendor is late. Rain is coming. The indoor space is full. Your procedure says move indoors. Now what? GhostShift lets an operations coordinator find the missing instruction before a real event does.” |
| 15–35s | Acknowledge draft, start, choose escalation. | “You make real choices against a pinned model of the procedure. Every choice is saved.” |
| 35–55s | Show all dispatch updates. Point to 40 → 85, capacity 0, and the actual uncovered decision. | “The scenario changed. Neither modeled choice covers these facts. GhostShift stops for review.” |
| 55–75s | Inspect source and condition diagnostics. | “This clause says redirect indoors. It never addresses full capacity. This capacity guard is a modeling assumption that still needs review. A citation locates text; it doesn't approve our interpretation.” |
| 75–115s | Test a proposed rule → enter rationale → Add choice for current facts → enter action → inspect destination/conditions → save → acknowledge → rehearse → select action. | “I can test a human-authored proposal. This is an experiment for these exact facts. It stays unapproved, and the original remains intact.” |
| 115–140s | Compare with parent; show original gap and alternate recorded choice; verify replay. | “The same scenario now reaches the modeled end under a proposed rule. That doesn't prove the response is correct. The preserved history makes the change inspectable and reproducible.” |
| 140–155s | Export parent/alternate comparison; download JSON. | “Keep both histories, quoted sources and exact replay inputs in one evidence package.” |
| 155–170s | Guide → Built around a Kiro-authored engine; show genuine specs/contribution record. | “GhostShift stitches source provenance, executable decision rules and branching event history into a playable rehearsal. Kiro authored the initial engine, specs and 60 tests; Codex separately reviewed it and built the product around it. Find the ghost path before your next shift.” |

Suggested fictional experiment: rationale “Test a holding response when indoor capacity is exhausted”;
action “Pause admission and contact venue manager.” This is demo input, not policy advice. The
current-facts shortcut is narrow equality matching, not a general rule repair or approval.

Keep recording below three minutes. If time is tight, trim navigation and explanatory pauses;
do not replace backend execution with staged success screens. Optional cuts must be identified as
cuts and leave the real input/output relationship understandable. Keep sound off for clear narration.

A longer walkthrough can show a same-policy checkpoint fork recording a deviation, the Support
fixture's overlap, custom source import, human review, and PDF provenance. These are not necessary
for the main three-minute story. Use actual local screenshots only; public hosting remains pending.


## Generated local recording

A real 170-second, 1440×1000 production-build recording is available locally at
`artifacts/demo/ghostshift-demo.mp4`, with separate `.srt` captions, measured chapter metadata in
`recording.json`, and the actual downloaded `recorded-comparison.json`. Narration is synthetic
macOS Samantha speech, not a human recording. The movie explicitly describes a local preview,
uses fictional data, and has not been uploaded or submitted. Video/H.264, AAC stereo audio and
optional English captions were verified in the MP4; visual frames were inspected across the journey.

Reproduce on macOS with local `say`, Caddy, installed project dependencies, Playwright Chromium and
FFmpeg: `make record-demo`. Set `FFMPEG_PATH` if FFmpeg is outside PATH. The script creates its own
clean fixture template and temporary workspace, launches loopback API/Caddy, drives real browser
actions, asserts actual outcomes and parent preservation, and removes temporary servers/data.
Narration sentence timings are distributed within measured chapter audio; they are not word-aligned.
The `.srt` file can accompany a YouTube upload. Media artifacts are ignored by Git and Docker.
