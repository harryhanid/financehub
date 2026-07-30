# Design System: FLOW — Login Landing (Animated Entry)

## 1. Visual Theme & Atmosphere

A clinical-yet-warm cockpit for an internal financial operations tool, staged as a single confident landing moment rather than a bare form. The canvas is near-black navy with a fine grain texture and two slow-breathing gradient orbs drifting behind the content — the room is dim, precise, and quietly alive before anyone even touches a field. On load, the screen choreographs itself into place: brand mark first, then a flowing signature line draws itself across the panel like data starting to move, then the tagline, then the sign-in card rises in as a sealed vault door. Nothing is static; nothing is loud. Motion is restrained and physical, never bouncy or cartoonish — this is a finance product, not a game.

**Density:** 4 (Daily App Balanced) — mostly negative space, but metadata (SSL note, "Internal" pill) is set in dense monospace to signal precision.
**Variance:** 6 (Offset Asymmetric) — the login card stays centered (correct, standard pattern for auth), but the new left brand panel introduces an asymmetric split at desktop width so the whole screen is no longer a single centered block.
**Motion:** 7 (Fluid CSS bordering Cinematic Choreography) — this is the explicit ask: a real opening sequence, not a fade.

## 2. Color Palette & Roles

Locked to the already-shipped FLOW brand tokens — do not invent new hues, only extend how they're used.

- **Void Navy** (`#06080F`) — Primary canvas background
- **Panel Ink** (`#0F1220`) — Card and raised-surface fill
- **Deep Slate** (`#161927`) — Input field fill, secondary surface
- **Bone White** (`#F0EEF8`) — Primary text (headlines, wordmark, field values)
- **Muted Periwinkle** (`#9896B0`) — Secondary text, labels
- **Whisper Ink** (`#4E4D63`) — Tertiary text, metadata, mono captions
- **Hairline** (`rgba(255,255,255,0.07)`) — Card borders, dividers, 1px structural lines
- **Flow Cobalt → Flow Cyan** (`#5B8CFF → #22D3EE`, dark mode gradient) — The single accent, used ONLY at hero spots: wordmark icon fill, primary button fill, focus ring, flowing signature-line stroke, active/eyebrow dot
- **Alert Coral** (`#FF5757`) — Error state only

(Max 1 accent, already under the 80% saturation ceiling. No purple, no neon glow rings — the existing `box-shadow` glows are soft and tinted to the accent, at low opacity, which is compliant.)

## 3. Typography Rules

- **Display / Wordmark:** `Figtree`, weight 800, track-tight (`-.04em` on the card title, `-.01em` on the wordmark) — hierarchy through weight and color, never oversized shouting text.
- **Body:** `Figtree`, weight 400–600, relaxed leading (1.5), max ~40ch (this is a narrow card, not a paragraph-heavy page).
- **Mono:** `DM Mono` — reserved for metadata only: the "Internal" pill, the uppercase field labels, the SSL footer note, the copyright tagline, and the eyebrow "Sign in" chip. This is the existing, correct pattern — keep it.
- **Banned:** Inter (not in use — good, keep it that way). No serif anywhere; this is a dashboard/software surface.

## 4. Hero / Opening Sequence (the core of this request)

This is a login screen, not a marketing page, so there is no scroll-triggered hero — the entire "hero" IS the load-in choreography. Sequence, staggered by ~60–90ms per beat, spring physics throughout:

1. **Canvas settles first** — grain texture and the two background orbs fade in at 0ms, orbs already mid-breath (don't start them from a dead stop; they should feel like they were always drifting).
2. **Wordmark icon draws in** — the flow-lines SVG icon (`M1.5 10.2c1.6-3.2 3.6-3.2 5 0s3.4 3.2 5 0...`) animates via `stroke-dasharray`/`stroke-dashoffset` as a genuine line-draw (300–400ms), not a fade — this is the signature move since the mark IS a flow line. Icon container's gradient fill crossfades in as the stroke completes.
3. **Wordmark text + "Internal" pill** rise in together (existing `rise` keyframe: translateY 18px → 0, opacity 0 → 1), immediately after the icon draw finishes.
4. **Tagline** ("Financial Ledger and Operational Workspace") rises in ~40ms after the wordmark.
5. **Card shell** rises in as a heavier, slower beat (~80ms stagger, longer duration ~600ms) — it should feel like it has more mass than the wordmark elements, arriving like a sealed panel settling into place, not floating paper.
6. **Card internals cascade** — eyebrow chip → title → subtitle → fields → button, each offset by ~30–40ms, all still using the same rise physics so the whole thing reads as one continuous wave rather than independent pieces.
7. **Footer tagline** (copyright line) is the last thing to settle, ~150ms after the card.

No "scroll to explore" affordance — there is nothing to scroll, this is a single-viewport login. No filler copy.

**Split-screen upgrade (desktop ≥1024px only):** introduce a left brand panel (roughly 45% width) containing the wordmark, tagline, and a large ambient version of the flow-line motif — either the same signature line drawn much larger and looping slowly and continuously in the background (perpetual, not one-shot), or a thin animated data-flow visualization (a few soft cobalt-to-cyan lines drifting horizontally like ledger rows in motion). The login card sits in the right ~55%, vertically centered within its own column. Below 1024px, the brand panel collapses to the existing stacked layout (wordmark → tagline → card, all centered) — this matches the mobile-first collapse rule and avoids a second, competing centered composition at narrow widths.

## 5. Component Stylings

- **Wordmark icon:** 34px rounded-square, gradient fill (`135deg, var(--accent), var(--accent-2))`), soft accent-tinted glow (`0 0 24px var(--accent-glow)`) — already correct, keep as-is, just add the stroke-draw-in entrance described above.
- **Card (double-bezel):** outer translucent shell (`rgba(255,255,255,0.03)`, 1px hairline border, 24px radius) wrapping an inner solid panel (`Panel Ink`, 20px radius) with a 5px gap — this "bezel within a bezel" is the signature card treatment for this product; reuse it for the split-screen's card, don't flatten it to a single layer.
- **Buttons (primary/login):** flat gradient fill, no neon outer glow — the existing soft tinted shadow (`0 4px 20px rgba(79,106,255,0.25)`) is the ceiling, don't push it brighter. Tactile feedback: `-1px` translateY + brighter shadow on hover, `scale(.98)` on active (already implemented correctly — keep).
- **Inputs:** label above (mono, uppercase, tracked), double-bezel shell matching the card treatment, focus state = accent-tinted border + soft ring (already correct). No floating labels.
- **Loading state on submit:** the button already dims to 65% opacity and disables pointer events — acceptable for a single CTA, but consider replacing the flat dim with a subtle inline shimmer sweep across the button fill so the "working" feeling reads as motion, not just reduced opacity.
- **Error state:** existing inline coral banner above the fields, rendered only on failure — correct pattern, no change needed.

## 6. Layout Principles

- Mobile / narrow (<1024px): single centered column exactly as shipped today — wordmark, tagline, card, footer tagline, all vertically stacked and centered. This is the correct pattern for auth at this width; do not force asymmetry here.
- Desktop (≥1024px): asymmetric two-column split — brand panel (~45%) + card column (~55%), full `min-h-[100dvh]` (never `h-screen`), max total width contained at ~1400px centered on very wide monitors so the split doesn't stretch absurdly thin/wide.
- No overlapping elements at any width — the ambient flow-line visual in the brand panel sits fully behind/beside the wordmark text, never crossing through it.
- Grain + orbs stay `position: fixed`, `z-index: 0`, `pointer-events: none` — purely atmospheric, never interactive, never impacting layout flow.

## 7. Motion & Interaction

- **Spring/ease default:** keep the existing `cubic-bezier(.22,.72,0,1)` for rise-ins (already close to spring physics) and `cubic-bezier(.32,.72,0,1)` for interactive transitions (button, focus rings) — consistent easing language across the whole screen, don't introduce a third curve.
- **Perpetual micro-interactions:** the two background orbs should have a slow, continuous drift/breathe loop (subtle scale + position oscillation, 8–14s cycle, `transform`/`opacity` only) — they should never look perfectly static once the entrance sequence finishes. Same for the desktop brand panel's ambient flow-line visual: it loops continuously and quietly, never resolves to a static frame.
- **Staggered orchestration:** the entrance sequence in section 4 is the primary implementation of this — every element's `animation-delay` builds on the previous, producing one continuous wave rather than simultaneous pop-in.
- **Performance:** animate exclusively via `transform` and `opacity` (plus `stroke-dashoffset` for the one-time icon/flow-line draw, which is a vector-safe GPU-friendly property). Never animate `top`/`left`/`width`/`height`. Grain filter stays on the fixed pseudo-element, never re-rendered per frame.

## 8. Anti-Patterns (Banned)

- No emojis anywhere in copy or UI.
- No Inter font — Figtree/DM Mono only, as already shipped.
- No serif fonts anywhere on this screen.
- No pure black — canvas is `#06080F` (Void Navy), never `#000000`.
- No neon/high-saturation outer glows — accent glows stay soft, low-opacity, tinted, exactly like the current button/icon shadows.
- No gradient text on large headers (the card title "Selamat Datang" stays solid Bone White — gradient is reserved for the wordmark icon and CTA fill only).
- No custom mouse cursors.
- No 3-column equal-card layouts (not applicable here, single-form screen).
- No "Scroll to explore" / bouncing chevrons / scroll arrows — this is a non-scrolling single-viewport screen.
- No AI copywriting clichés ("Elevate", "Seamless", "Unleash", "Next-Gen") in any placeholder or button copy — keep the existing plain Indonesian copy ("Selamat Datang", "Masuk ke akun FLOW Anda", "Masuk").
- No broken image links — this screen uses only inline SVG, no photography, so this is moot but stays banned for any future additions.
- No fake round statistics or numbers anywhere on this screen.
