# Visual design: "haunted command center"

## Current direction — November 4, 2026

The local release quality pass keeps the Kiroween identity with a calmer working surface.
Landing artwork is static; the shared shell no longer includes flying bats, corner artwork on
working pages, or a graveyard footer. The Studio corner cobweb is removed. Brand bobbing,
route fade-ins, graph-edge motion and the repeating warning pulse are removed. Loading indicators
retain restrained motion and respect reduced-motion preferences. Dispatch arrivals remain brief,
user-triggered transitions. Working-page badges, navigation and fact/report values use less glow.

Loading and missing-page messages use direct language. The landing page retains the ghost-path
illustration and outcome tombstones, with clearer workflow labels and fewer decorative pieces.
Keyboard focus, status colours, draft/proposal notices, citations and print content remain intact.
The earlier design record below describes the original overhaul; this section supersedes its
global-decoration and animation descriptions. See [QUALITY_REVIEW.md](QUALITY_REVIEW.md).

## Original overhaul

November 3, 2026. The Kiroween visual overhaul is presentation only: no engine, API, schema or
persistence code changed, and no Kiro model session was used. Earlier Kiro and Codex
contributions keep their attribution (see kiro-evidence.md and ENGINE_REVIEW.md).

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
| `--pumpkin` / `--candle` | `#FF8A3D` / `#FFD36B` | Decorative only (pumpkins, candle glow) |

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
6. `styles/decor.css`: Halloween artwork, plus the custom checkbox and disabled-button refinements.

## Halloween artwork

`apps/web/src/components/decor/Spooky.tsx` provides hand-drawn inline SVG pieces: `Bat` (flapping
wings), `Pumpkin` (jack-o'-lantern with a flickering candle face), `Cobweb`, `Spider` (dangling on a
thread), `Tombstone`, `Moon` and `Graveyard` (a skyline silhouette above the footer). Every piece
is `aria-hidden`, carries no product data, is hidden in print and stops animating under reduced motion.
They appear in:

- the global backdrop: moon, corner cobwebs and occasional flying bats;
- the header chip, a pumpkin;
- the landing page: bats and pumpkins around the illustration, a spider over the feature cards,
  and the "graveyard of missing rules" section. Its tombstones describe the three engine outcomes
  (uncovered path, potential overlap, deviation) in the same truthful terms the product uses;
- the Source Studio workbench, a cobweb in the corner;
- the 404 page, a tombstone with a peeking ghost;
- every page, the graveyard skyline above the footer.

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
