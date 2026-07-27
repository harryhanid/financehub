# Design: FLOW Login — Full-Page Ambient Ledger Chart Background

**Date:** 2026-07-27
**Module:** Finance Hub → FLOW — Login page
**Status:** Approved

---

## Summary

The login page's current decorative background (two dashed/dotted wave-lines confined to a desktop-only left brand panel, added in an earlier session) is replaced with a single full-page ambient background element: two smooth, continuous trend-line curves — styled like a financial line chart, not literal dots — spanning the entire viewport behind everything, including behind the login card itself. This is a refinement of the animated login-landing work already shipped in `templates/login.html` (split-screen layout, entrance choreography, breathing orbs); this spec covers only the ambient background motif, not those other pieces.

Reached via visual brainstorming (3 initial directions compared live in-browser: Ledger Curve, Depth Waves, Constellation Ledger → user picked Ledger Curve → refined to a 2-line "Primary + Shadow" variant → confirmed the placement should be full-page/behind-everything rather than confined to the left panel).

---

## Decisions

| Question | Decision |
|---|---|
| Visual motif | Two smooth bezier curves resembling financial trend lines — a bold "primary" line and a fainter "shadow" line — not dots, not literal candlesticks. |
| Colors | Stay inside the existing FLOW accent duo — primary in solid Cobalt (`#5B8CFF`), shadow in solid Cyan (`#22D3EE`). No new hues introduced. |
| Motion | No dash-array "marching ants" (the thing the user explicitly rejected). Primary line's shape is static; a small glowing dot travels along it in a slow loop (~7s), like a live ticker. Shadow line's shape is static; it breathes in opacity (~10–14s cycle) — same motion language already used by the page's background orbs, not a new pattern. |
| Placement | Full-page, `position: fixed`, behind every other element (same stacking context as the existing `.orb` elements) — not confined to the desktop-only left brand panel. Visible on **all breakpoints**, including mobile, since it's now a page-wide ambient layer rather than a brand-panel decoration. |
| Login card readability | Card keeps its existing solid/opaque surface (`--surface: #0F1220`). The chart lines are only faintly visible around/behind the card's edges, never competing with form text. No change to card contrast. |
| Old brand-panel-only flow visual | Fully removed (the `.brand-flow` SVG + its `flow-drift`/dash-array CSS from the current `login.html`) and replaced by this new full-page version. |

---

## Architecture

### File changes

**Modify `C:\Financehub\app\templates\login.html`:**

1. Remove the existing `.brand-flow` SVG element (inside `.brand-panel`) and its associated CSS (`.brand-flow`, `.brand-flow path`, `@keyframes flow-drift`, and the `nth-child` duration/direction overrides for the old 3-line version).
2. Add a new full-page ambient SVG, sibling to the existing `.orb` divs, same `z-index: 0` fixed-background stacking context. Insert it immediately **after** both `.orb` divs in DOM order (orbs paint first/underneath, the crisp chart lines paint on top of the soft blur — reversing this order would make the lines look muddied through the orbs' `blur(120px)` filter). It contains:
   - A `<defs>` block with two `<linearGradient>`-free solid strokes (no gradient needed since each line is a single flat color, unlike the wordmark icon).
   - Primary path: `M-100,340 C100,260 220,360 380,300 C540,240 620,340 780,270 C940,200 1020,300 1180,220 C1340,140 1420,240 1700,160` — stroke `#5B8CFF`, `stroke-width: 2.2`, `stroke-linecap: round`, plus a closed variant of the same path (`L1700,500 L-100,500 Z`) filled with a vertical gradient (`#5B8CFF` at 14% opacity fading to 0) for the area-fill.
   - Shadow path: `M-100,300 C120,420 280,180 440,340 C600,460 680,200 840,320 C960,400 1080,180 1240,300 C1360,380 1480,160 1700,280` — stroke `#22D3EE`, `stroke-width: 1.2`, opacity `0.35`.
   - A `<circle r="4" fill="#5B8CFF">` with an `<animateMotion>` (7s, `repeatCount="indefinite"`) along the primary path, plus a second larger circle (`r="9"`, opacity `0.25`) with the same motion for the glow halo.
   - `viewBox="0 0 1600 500"` with `preserveAspectRatio="xMidYMid slice"` so the curve shape stays proportionally consistent across viewports (cropped like `background-size: cover`, never stretched/distorted) from mobile through ultra-wide desktop.
3. Add the shadow-line breathing animation as a new `@keyframes` (reusing the existing `breathe-1`/`breathe-2` naming convention, e.g. `chart-shadow-breathe`), applied only to the shadow `<path>`.
4. The SVG element gets `position: fixed; inset: 0; z-index: 0; pointer-events: none; width: 100%; height: 100%;` — same layer as `.orb-1`/`.orb-2`.
5. No changes to `.brand-panel`'s own wordmark/tagline content — those stay exactly as shipped. Only the decorative flow-lines move out of the panel and become page-wide.

### Non-goals

- No change to the split-screen layout, entrance choreography, or breathing orbs already shipped.
- No change to `doLogin()`, form fields, or any auth logic.
- No change to any other page (`base.html`, `company_select.html`, etc.) — this is login-page-only.
- Not extending this motif to the dashboard or any authenticated page.

---

## Testing

No backend/logic changes, so no new pytest coverage is needed (the existing `tests/test_branding.py` suite already asserts the page renders with FLOW branding intact — those assertions are unaffected by a pure CSS/SVG background change). Verification is visual:
- Browser check at mobile (375px), tablet, and desktop (≥1024px) widths — confirm the chart is visible full-page at every size, the card stays readable, and no horizontal overflow is introduced.
- Confirm via `document.getAnimations()` (or equivalent) that the new dot-travel and shadow-breathe animations are actually running, not just declared.
- Confirm `prefers-reduced-motion: reduce` still freezes all motion (the existing reduced-motion media query in `login.html` already lists `.orb`; extend it to cover the new chart elements too).

## Out of Scope

- Applying this ambient chart motif anywhere outside the login page.
- Any data-driven/real chart (this remains purely decorative, no real numbers).
- Further mockup iterations beyond the "Primary + Shadow" direction already approved.
