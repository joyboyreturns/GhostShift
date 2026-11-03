# Visual design: "haunted command center"

November 3, 2026. The Kiroween visual overhaul was authored by **Claude Code** (Anthropic) at the
user's request. It is presentation only: no engine, API, schema or persistence code changed, and
no Kiro model session was used. Earlier Kiro and Codex contributions keep their attribution
(see kiro-evidence.md and ENGINE_REVIEW.md).

## Principles

- **Spooky surface, serious substance.** The ghost theme lives in atmosphere, the landing page,
  eyebrows, loading and 404 states. Product statuses and the headings under test use plain,
  truthful language.
- **Colour carries meaning.** Mint means validated evidence or a matching path. Amber means
  review pending, a warning or an uncovered path. Coral means a deviation. Violet is the brand
  colour and marks interactive or navigational elements. Draft and unapproved states stay visibly
  distinct.
- **Decoration is never data.** The landing-page illustration is an abstract, `aria-hidden` SVG
  with no fixture labels. Every real graph is still rendered from validated API responses.

## Tokens

All colours, fonts, radii and glows are CSS custom properties in
`apps/web/src/styles/tokens.css`.

| Token | Value | Use |
| --- | --- | --- |
| `--bg` | `#0A0714` | Page background (midnight violet) |
| `--surface` / `--surface-2` | `#161128` / `#211A3A` | Panels and raised controls |
| `--text` / `--soft` / `--muted` / `--faint` | `#F3F0FA` / `#CDC6E0` / `#AAA2C2` / `#918AAB` | Text hierarchy |
| `--violet` | `#A78BFA` | Brand and interaction |
| `--mint` | `#7CF5C6` | Validated evidence and matching paths |
| `--amber` | `#FFB45C` | Review, warnings and uncovered paths |
| `--coral` | `#FF6B7A` | Deviations |

Typography: Space Grotesk (UI and display) and JetBrains Mono (eyebrows, hashes, conditions).
Both are self-hosted through `@fontsource-variable` packages, so no font is fetched from the
network at runtime.

## Stylesheet layout

`apps/web/src/styles.css` imports these files in order:

1. `styles/tokens.css`: design tokens.
2. `styles/atmosphere.css`: the fixed night-sky backdrop (fog, stars and grain) and keyframes.
3. `styles/base.css`: the original layout rules, with every hard-coded colour replaced by a token.
4. `styles/theme.css`: the Kiroween layer, including glass panels, the pill navigation, badges,
   React Flow node accents by node type, the timeline spine, the replay scrubber and print resets.
5. `styles/home.css`: the landing page.

Class names that Playwright tests depend on (for example `.app-header`, `.proposal-section`,
`.condition-editor`, `.revision-node`, `.library-card`, `.facts-panel`, `.report-finding`) are
unchanged. Restyle them; do not rename them.

## Accessibility

- Measured contrast against `--bg` (and `--surface`): `--text` 17.7:1, `--muted` 8.2:1 (7.6:1),
  `--faint` 6.1:1 (5.6:1), mint 14.9:1, amber 11.3:1, coral 7.3:1 and violet 7.3:1. All exceed
  WCAG AA for normal text.
- Focus is a 2px violet outline plus a soft halo on every interactive element. The skip link is
  kept.
- `prefers-reduced-motion: reduce` turns off every animation and transition: fog, stars, ghost bob,
  edge flow, the stop pulse and route fade-in.
- Print media hides the header, footer and backdrop and renders reports in black on white.
- Mobile (390 px) keeps navigation in a scrollable pill row with no horizontal page overflow.
