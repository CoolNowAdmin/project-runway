# Runway — DESIGN.md

Locked design direction for every Runway page. Do not invent per-page colours, fonts or spacing; change this file instead.

## Direction
- **Style:** warm editorial real-estate. Real HDB photography, one hunter-green accent, serif headlines, dense content blocks.
- **References:** LVIM Bank (section rhythm, raised middle card), Real Estate Property app (steppers, chips, square icon buttons), Trade Estate / VillaVox boards (photo-led cards, bento product demo).
- **One idea per section.** Hero = Ask Runway. Nothing else competes in the hero.
- **One layout idea per page, one style per site.**

## Colour (one accent)
| Token | Light | Dark | Use |
|---|---|---|---|
| `--page` | `#FDFEFD` | `#0E1714` | page background (body, nav, app bar, composer bar) |
| `--snow` | `#FDFEFD` | `#16211E` | cards, buttons, sheets; text on the green accent |
| `--beige` | `#E7DBC5` | `#3A3327` | chips, soft fills, secondary buttons |
| `--beige-2` | `#F4EDE0` | `#1D2824` | bands, inputs, the assistant's chat bubble, tiles |
| `--beige-deep` | `#C9B892` | `#5E5442` | borders on beige, dashed rule boxes, hand-drawn marks |
| `--green` | `#023933` | `#8DD0B3` | **the accent**: buttons, links, headings, selected states |
| `--green-deep` | `#012A26` | `#ADE0C9` | hover and pressed state of the accent |
| `--green-mid` | `#0F6B4F` | `#86D1A9` | full-CPF chip text only |
| `--ink` | `#14201C` | `#ECE6DA` | body text |
| `--ink-2` | `#4D5A55` | `#B3ADA1` | secondary text (≥4.5:1 on every surface above) |
| `--line` | `#E2D9C8` | `#2C3833` | hairlines |
| `--ok` / `--ok-soft` | `#0F6B4F` / `#DCEBE3` | `#86D1A9` / `#173A2C` | CPF verdict semantics only, never decoration |
| `--part` / `--part-soft` | `#8F5509` / `#F8EAD4` | `#E6B26A` / `#3B2D17` | 〃 |
| `--no` / `--no-soft` | `#4D5A55` / `#EDE6D8` | `#B3ADA1` / `#262E2A` | 〃 |

**Brand surfaces** keep one look in both themes (they are already dark): the hero, the grainy green surfaces, the map hint and toasts.

| Token | Both themes | Use |
|---|---|---|
| `--brand` / `--brand-deep` | `#023933` / `#012A26` | large green surfaces, photo-credit chips, the runway strip |
| `--on-brand` | `#FDFEFD` | text on brand surfaces and photos (lighter tints are mixes of it, never alpha over a photo) |
| `--brand-hi` | `#E7DBC5` | beige accents on brand surfaces: italic headline, scribbles, focus ring, current footer link |
| `--sign` | `#F2C230` | runway markings, the plane and lit windows in the building drawing only |

**Map colours** (`--land`, `--land-edge`, `--pa-line`, `--road`, `--road-edge`, `--block`, `--block-edge`, `--water`, `--mrt-case`) are defined per theme in the stylesheet; the map reads them when it draws and redraws when the theme changes. MRT line, amenity and chart series colours are data colours and stay the same in both themes: in dark mode MRT lines get a light `--mrt-case` casing, because several line colours fall under 3:1 against any dark ground.

Rules: no second accent, no purple, no glowing buttons. Gradients appear in two places: the hero's legibility scrim over the photo (no grain there), and the grainy gradient on green surfaces (footer, question band, green cards): a soft sage glow (25% at its brightest) around a dark disc with still film grain, kept dark enough for snow and beige text at 4.5:1 at the glow's brightest point.

## Dark theme
- Light is the default and the brand's theme. "Dark mode" is a button in the nav (sidebar and drawer) with `aria-pressed`; the choice is kept in the browser under one key, `runway-theme`, and nothing else is ever stored. The attribute `data-theme` is set on `<html>` before the first paint.
- Dark mode only redefines tokens (`:root[data-theme="dark"]`), never component rules. Deep green-black page, slightly lighter cards, warm off-white text, the same single green accent lightened, beige darkened as the secondary fill. On the accent, text uses `--snow`, so a green button is light sage with dark text in dark mode.
- Contrast bars are the same as light: 4.5:1 body and small text, 3:1 large text and essential graphics.

## Type (one pair)
- **Display:** Source Serif 4, 700 (600 for italics). Headline scale: h1 72/1.02, h2 48/1.08, h3 24/1.25, tracking −0.02em on h1/h2. Inner pages: h1 34/1.1, h2 24/1.25, h3 20/1.3. Display is for headings, big numbers and the answer and verdict sentences only; headings are green.
- **Body:** Plus Jakarta Sans for all body and UI text. Two sizes only, in rem so Text size scales them: normal text 17px (`.944rem`, 400) for paragraphs, nav items, inputs, breadcrumbs and messages on every page; small 14px (`.778rem`) for notes, captions and credits. Labels 12/700 in sentence case with no tracking. Buttons and big numbers keep their own sizes.
- **Wordmark only:** Anton (RUNWAY).
- Numbers: `font-variant-numeric: tabular-nums` everywhere a number can change.
- Sentence case for labels and buttons. Caps only for the wordmark. Inner pages size type in rem so Text size "Large" scales them.

## Spacing & shape
- 8px grid. Section padding 80px (desktop) / 48px (phone). Content max-width 1240px, 32px gutters.
- Cards: 20px radius, 1px `--line` border, snow, `corner-shape: squircle` where supported. Buttons 14px radius, squircle: green primary (`--green-deep` on hover and press), 1px `--line` outline secondary, beige secondary. Chips and quick picks 10–12px radius; a selected single choice is green with snow text. Steppers: 46px squares, − outline, + green. Inputs and selects: 50px, beige-2, 14px radius, the chevron from Home. No 2px borders; pills (999px) only for count badges.
- Shadows: `--shadow-card` (`0 1px 2px rgba(1,42,38,.06), 0 16px 40px rgba(1,42,38,.14)`; black in dark mode) on raised cards and on controls that float over the map. No coloured glows.
- Density over whitespace: group related controls inside one card; no floating elements.

## Interaction
- Every target is at least 44×44px (the range slider's 24px track is the one exception). Links inside sentences grow their hit area with vertical padding.
- Focus: a 2px `--green` ring 3px outside the element on every interactive element; `--brand-hi` on brand surfaces. Never `outline: none` without a replacement.
- Motion: 300ms or less, ease-out or ease-in-out (an overshoot curve is fine within 300ms), never linear. Typing, steppers and tab changes get no animation. `prefers-reduced-motion` turns all of it off.
- Every press shows at once: buttons darken while pressed, and anything that waits on the server shows a busy or loading state.

## Navigation
- One left nav on every page, Home included: Home, Map, Shortlist, Trends, Ask, More, then Dark mode and Log in at the foot, with the logo and wordmark on top.
- ≥1024px: a fixed left sidebar, content to its right. "Collapse menu" at its foot folds it to a 76px icon rail (labels become tooltips; a search icon reopens it with the search box focused). The fold is instant and lasts for the visit only: nothing is stored. Below 1024px: a slim top bar with a menu button (top left) that opens the same nav as a drawer from the left over a dimmed scrim. No bottom tab bar.
- The Runway logo (sidebar, rail, top bar) always opens the top of Home.
- The search box carries a magnifier icon.
- Current page: green text on a beige-2 fill with a 2px green edge. More's own pages keep More marked.
- One URL per page (page names only, never user input); Back and Forward follow it.
- Every inner page starts with a breadcrumb (`crumbs()`: Home › … › page, the last crumb plain text). On the map it sits in the town card.
- Site search lives in the nav, under the brand. Long pages (Home, How it works, FAQ, Sources, Privacy, Terms) get a Back to top button 72px above the bottom edge, clear of Streamlit Cloud's badge.
- Loading the map data shows the `.rwload` panel with only the stages the page can observe; never a percentage.

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
1. One accent only? 2. Tabular numbers? 3. No glow / purple / emoji / shouty caps? 4. Squircles on cards and buttons? 5. Hero carries one idea? 6. Photo credits present, on a solid chip? 7. Phone width: menus stack, nothing clipped. 8. Both themes: contrast holds, no hard-coded colour outside the tokens. 9. Targets ≥44px, focus ring visible, motion ≤300ms.
