# Design: FLOW Company Select — Branching Chart Transition

**Date:** 2026-07-27
**Module:** FLOW — Company Select page (`/select-company`)
**Status:** Approved

---

## Summary

`templates/company_select.html` currently looks disconnected from the rest of FLOW's identity: two large gradient panels (unrelated blue/purple, not the FLOW accent tokens) with generic emoji icons (🏢/🏛️), no animation, and no visual relationship to the login page that immediately precedes it. This design replaces it with a page that continues the login page's ambient ledger chart rather than starting fresh: the same two chart lines (cobalt "primary", cyan "shadow") that flow across the login background visually branch apart on this page — one curving toward the Sinar Mas Tjipta selection, the other toward Eka Tjipta Foundation — turning the "pick a company" moment into a literal fork in the data-flow visual, instead of a generic card grid.

Reached via visual brainstorming (3 initial card-style directions compared live in-browser — Minimal Mono, Ledger Rows, Split Panel Evolved — all rejected as too standard; a fourth direction, animated branching chart lines, was mocked up live with real CSS/SVG animation and approved).

Scope is strictly **login → company select**. The dashboard and every page after company selection keep their existing light/dark-toggle system, untouched — this is not extended further into the app.

---

## Decisions

| Question | Decision |
|---|---|
| Core visual concept | The login page's two ambient chart lines (`.chart-primary` cobalt, `.chart-shadow` cyan) do not stay flat/horizontal on this page — they curve and diverge into two branches, each leading toward one company's selection panel. A traveling dot continues along each branch (same mechanic as login) and pulses/lands at its destination panel. |
| Color-to-company mapping | Sinar Mas Tjipta = cobalt (primary line, matches `company_id=1`, listed first in `config.COMPANIES`). Eka Tjipta Foundation = cyan (shadow line, `company_id=2`). |
| Card treatment | Minimal glass panel (existing FLOW card idiom: translucent fill, hairline border, soft radius) — no emoji, no unrelated gradient background. The branching line arriving at the panel, plus a small pulsing landing-dot matching that line's color, is the primary visual distinguisher between the two — not icon or color-block choice. |
| Hover interaction | Hovering a panel brightens/thickens that panel's line and dims the other line slightly, reinforcing "this line = this choice." |
| Click interaction | On click, before the form submits: a short (~150–200ms) flourish — the chosen line flashes brighter and its traveling dot briefly speeds up — then the native form POST proceeds to `/select-company` as today. |
| Transition mechanism | `@view-transition { navigation: auto }` added to both `login.html` and `company_select.html`. Elements meant to feel continuous (wordmark, ambient chart container) share matching `view-transition-name` values across both pages, so supporting browsers (Chrome/Edge) cross-fade+glide them instead of a hard cut. Browsers without support silently fall back to a normal instant navigation — no polyfill, no broken states. |
| Scope boundary | Company Select → Dashboard transition is unchanged (standard page load). Dashboard's own light/dark toggle system is untouched. |
| Reduced motion | Same policy as login: `prefers-reduced-motion: reduce` freezes the shadow-breathe/hover-brighten animations and hides the traveling dots (lines remain visible, static). View Transitions still fire (browsers already respect the OS reduced-motion setting for these natively) but the custom line/dot choreography described above is frozen. |

---

## Architecture

### File changes

**Modify `C:\Financehub\app\templates\company_select.html`** (currently a bare 30-line template with two `.cs-panel` gradient buttons):

1. Replace the `<body>` markup with a structure mirroring login's canvas: noise texture, breathing orbs (reuse login's `.orb`/`.orb-1`/`.orb-2`), and a full-page ambient SVG — but with the **branching** path shapes instead of login's flat horizontal curves. The primary path starts at the same edge/height where login's primary path exits the viewport (so the two pages' lines feel like one continuous stroke across the page boundary) and curves down toward the left panel; the shadow path does the same toward the right panel.
2. Two glass panels (`.cs-company-panel` or similar, reusing the existing card idiom's translucent-fill/hairline-border/radius tokens) replace `.cs-panel-smt`/`.cs-panel-etf`. Each panel: company name, company code as a small mono caption, no icon/emoji. A small `.cs-landing-dot` matching that panel's line color, with the same pulse animation used in the login-continuity mockup.
3. `<form>`/`<button type="submit">` structure stays as today (native POST to `/select-company`, no client-side routing) — only the visual treatment inside the button changes.
4. JS: a `hover`/`focus` listener per panel toggles a class (e.g. `.branch-active-smt` / `.branch-active-etf` on a shared ancestor) that CSS uses to brighten/thicken the hovered line and dim the other (`filter`/`opacity`/`stroke-width` transition, all GPU-friendly properties). A `click` listener on each button prevents default, plays the ~150–200ms flourish (adds a `.branch-firing` class triggering a CSS transition/animation), then calls `form.requestSubmit()` (or `submit()`) after the flourish's duration via `setTimeout`.
5. Add `@view-transition { navigation: auto; }` to this page's `<style>` block (mirrors the same rule to be added to `login.html`). Assign `view-transition-name: flow-wordmark` to the wordmark element and `view-transition-name: flow-ambient` to the chart SVG container in **both** `login.html` and `company_select.html` — same names, so the browser treats them as the same persistent element across the navigation.

**Modify `C:\Financehub\app\templates\login.html`:**

6. Add the same `@view-transition { navigation: auto; }` rule and the two matching `view-transition-name` values (`flow-wordmark` on the wordmark, `flow-ambient` on `.chart-ambient`) — no other change to login's existing ambient chart from the prior design (`2026-07-27-flow-login-ambient-ledger-chart-design.md`).

**Modify `C:\Financehub\app\static\css\style.css`:** no change — this page keeps its own inline `<style>` block, matching the existing pattern where `login.html` and `company_select.html` are self-contained documents (company_select.html currently links `style.css` for its old `.cs-*` classes; those rules become dead once the panels are restyled inline and should be removed from `style.css` in the same change to avoid leaving orphaned CSS).

### Non-goals

- No change to `/select-company` POST route logic, session handling, or `config.COMPANIES` data.
- No change to the Dashboard or any page reachable after company selection.
- Not a general-purpose "page transition system" — the `view-transition-name` values are specific to these two pages' shared elements, not a reusable framework for the rest of the app.
- Not extending the branching-chart motif to any other page.

---

## Testing

No backend/logic changes — `/select-company` POST behavior, `company_id`/`company_code`/`company_name` session assignment are unaffected, so existing tests (`tests/test_dashboard.py::test_select_company_after_login`, etc.) should continue passing unmodified. New coverage needed:

- A rendering test (Flask test client) asserting `/select-company` still contains a submit button per company with the correct `value="{{ c.id }}"`, and that the old `.cs-panel-smt`/`.cs-panel-etf`/emoji markup is gone.
- Manual/visual verification (browser): desktop and mobile widths, no horizontal overflow; hover brightens the correct line per panel; click on each panel navigates to the correct company (verify via the resulting `company_code` in the next page, e.g. dashboard title or company selector text); `prefers-reduced-motion` freezes dot/breathe animations without hiding the lines themselves; View Transition cross-fade visible in a Chrome/Edge browser (informal check — not asserted in automated tests, no polyfill needed since unsupported browsers degrade to a normal navigation with no error).

## Out of Scope

- Any change to Dashboard's visual system or theme.
- A shared/reusable view-transition helper for other page pairs in the app.
- Real per-company branding beyond the cobalt/cyan line-color mapping (no company logos, no additional company-specific imagery).
