# Runway — DESIGN.md

Locked design direction for every Runway page. Do not invent per-page colours, fonts or spacing; change this file instead.

## Direction
- **Style:** warm editorial real-estate. Real HDB photography, one hunter-green accent, serif headlines, dense content blocks.
- **References:** LVIM Bank (section rhythm, raised middle card), Real Estate Property app (steppers, chips, square icon buttons), Trade Estate / VillaVox boards (photo-led cards, bento product demo).
- **One idea per section.** Hero = Ask Runway. Nothing else competes in the hero.
- **One layout idea per page, one style per site.**

## Colour (one accent)
| Token | Hex | Use |
|---|---|---|
| `--snow` | `#FDFEFD` | page background, cards |
| `--beige` | `#E7DBC5` | section bands, chips, soft fills |
| `--beige-2` | `#F4EDE0` | lighter beige for alternating bands |
| `--beige-deep` | `#C9B892` | borders on beige, hand-drawn marks |
| `--green` | `#023933` | **the accent**: buttons, links, headlines on light, active states |
| `--green-deep` | `#012A26` | hero gradient start, footer |
| `--green-mid` | `#0F6B4F` | "Online" dot and full-CPF chip text only |
| `--ink` | `#14201C` | body text |
| `--ink-2` | `#4D5A55` | secondary text (≥4.5:1 on snow/beige) |
| `--line` | `#E2D9C8` | hairlines |
| `--ok` / `--part` | `#0F6B4F` / `#8F5509` | CPF verdict semantics only, never decoration |

Rules: no second accent, no purple, no glowing buttons. Gradients appear in two places: the hero's legibility scrim over the photo (no grain there), and the grainy gradient on green surfaces (footer, question band, green cards): a soft sage glow around a dark disc with still film grain, kept dark enough for snow and beige text.

## Type (one pair)
- **Display:** Source Serif 4, 700 (600 for italics). Headline scale: h1 72/1.02, h2 48/1.08, h3 24/1.25, tracking −0.02em on h1/h2.
- **Body:** Plus Jakarta Sans. Body 17/1.6, small 14/1.5, caption 12/1.4 with 0.08em tracking.
- **Wordmark only:** Anton (RUNWAY).
- Numbers: `font-variant-numeric: tabular-nums` everywhere a number can change.
- Sentence case for labels and buttons. Caps only for the wordmark and tiny eyebrow labels.

## Spacing & shape
- 8px grid. Section padding 80px (desktop) / 48px (phone). Content max-width 1240px, 32px gutters.
- Cards: 20px radius, `corner-shape: squircle` where supported. Buttons 14px radius, squircle. Pills 999px.
- Shadows: `0 1px 2px rgba(1,42,38,.06), 0 12px 32px rgba(1,42,38,.10)`. No coloured glows.
- Density over whitespace: group related controls inside one card; no floating elements.

## Icons
- One set: 24px viewBox, 2px stroke, round caps, `currentColor`. No emoji. Logo mark is the diamond-runway SVG.

## Imagery
- Real photos only, from Wikimedia Commons with credit: Punggol Waterway (CC BY-SA), Toa Payoh (CC BY-SA 2.0), Woodlands Ave 4 (Slivester, CC BY-SA 2.5).
- Hero treatment: the real photo + one soft green-deep scrim for legibility (left to right, with a short bottom fade). No grain, no thermal gradient, no parallax or drift.

## Human touch
- One hand-drawn element per page: the scribbled underline under the hero headline and the sketched arrow on the chat card. Keep it to one or two, never a theme.

## Copy (from lead review, Nov 2026)
- Headline: "Less lease, less CPF: what buyers need to know."
- Subhead: "How much CPF you can use for a flat depends on the years left on its lease and your age."
- Section 01 is "The gist"; use *hinges* / *discover* / "– too late".
- Verdict format: "Remaining lease 55 years · 43 years to 95. The flat has 55 lease years left — the youngest buyer turns 95 in 43 years. With 12 years to spare, CPF can be used up to the Valuation Limit, and the HDB loan is up to 75%."
- Ask section: "Have more questions? Ask Runway." Suggested: "Why is your CPF usage reduced?", "What happens if your partner is the younger buyer?", "What is the 20-year minimum lease about?"
- Replace "calculated in the ordinary way" with "The figures come from the rule itself, not from the AI."

## Pre-ship pass
1. One accent only? 2. Tabular numbers? 3. No glow / purple / emoji / shouty caps? 4. Squircles on cards and buttons? 5. Hero carries one idea? 6. Photo credits present? 7. Phone width: menus stack, nothing clipped.
