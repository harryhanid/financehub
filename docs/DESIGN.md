# Design System: Finance Hub
> **Verdict**: Complete visual overhaul required — current UI fails premium enterprise standards on typography, motion, color architecture, and component hierarchy.

---

## 0. Audit Findings — Current State vs Target

| Dimension | Current State | Severity | Target |
|-----------|--------------|----------|--------|
| Font | `Inter` | Critical — banned | `Satoshi` + `JetBrains Mono` |
| Navigation | Emojis (⚡🏠🎓📋) | High — anti-pattern | Icon-only SVG or text |
| Navbar | Flat solid `#1a56db` | High | Dark Zinc-950 bar with border-bottom |
| Sidebar | `#1e293b` flat links | Medium | Layered depth with left-indicator rails |
| Stat Cards | `auto-fit minmax` equal grid | High — banned pattern | Asymmetric 2–3 column with label hierarchy |
| Motion | None | High | Staggered mount, spring transitions |
| Numbers | `Inter` proportional | High — cockpit density requires mono | `JetBrains Mono` tabular nums |
| Primary accent | `#1a56db` generic | Medium | `#2D6ADF` Electric Cobalt |
| Login | Centered card, emoji logo | Medium | Dark split layout |
| Loading | None / synchronous | Medium | Skeletal loaders matching layout |

---

## 1. Visual Theme & Atmosphere

**Theme:** *Precision Instrument* — a financial cockpit that earns user trust through restraint, weight, and choreographed information delivery.

**Atmosphere Scores:**
- **Density:** 7/10 — "Cockpit-adjacent" — financial data tables require density, but each surface layer is breathable
- **Variance:** 6/10 — Structured asymmetry: sidebar fixed, content zone uses intentional column breaks
- **Motion:** 7/10 — Cinematic choreography reserved for navigation transitions, data reveals, and metric counters; not decorative

**Mood reference:** Bloomberg Terminal meets Linear meets Stripe Dashboard — dark chrome, tabular precision, confident negative space.

---

## 2. Color Palette & Roles

### Core Surfaces

| Token | Hex | Role |
|-------|-----|------|
| **Ink Black** | `#09090B` | Navbar, Sidebar background, modal overlays |
| **Zinc-900** | `#18181B` | Sidebar hover states, secondary surface |
| **Zinc-800** | `#27272A` | Sidebar active rail, divider regions |
| **Canvas** | `#FAFAFA` | Main content background |
| **Surface White** | `#FFFFFF` | Cards, modals, input fields |
| **Border Subtle** | `#E4E4E7` | Card borders, table row dividers |
| **Border Strong** | `#A1A1AA` | Focus rings pre-accent, selected states |

### Text Hierarchy

| Token | Hex | Role |
|-------|-----|------|
| **Text Primary** | `#09090B` | Headlines, strong values |
| **Text Secondary** | `#3F3F46` | Body copy, descriptions |
| **Text Muted** | `#71717A` | Labels, helper text, table headers |
| **Text Inverse** | `#FAFAFA` | Text on dark surfaces |
| **Text Sidebar** | `#A1A1AA` | Inactive sidebar links |
| **Text Sidebar Active** | `#F4F4F5` | Active sidebar links |

### Accent (Single — Electric Cobalt)

| Token | Hex | Role |
|-------|-----|------|
| **Accent** | `#2D6ADF` | CTAs, active tab indicator, focus rings, links |
| **Accent Hover** | `#1D4ED8` | Button hover state |
| **Accent Surface** | `#EFF6FF` | Accent background tint for badges, highlights |
| **Accent Text** | `#1E40AF` | Text inside accent-tinted surfaces |

> **Rule:** Saturation of `#2D6ADF` is 74% — compliant. Never apply glow, neon shadow, or `box-shadow` with accent color on buttons.

### Semantic Status Colors

| Token | Hex | Use |
|-------|-----|-----|
| **Positive** | `#059669` | Surplus, success, active status |
| **Positive Surface** | `#ECFDF5` | Badge backgrounds |
| **Negative** | `#DC2626` | Deficit, error, rejected |
| **Negative Surface** | `#FEF2F2` | Alert backgrounds |
| **Caution** | `#D97706` | Pending, draft, warning |
| **Caution Surface** | `#FFFBEB` | Caution badge backgrounds |

---

## 3. Typography Rules

### Font Stack

```css
/* Primary — all body, UI, labels */
font-family: 'Satoshi', system-ui, -apple-system, sans-serif;

/* Monospace — ALL financial numbers, codes, IDs */
font-family: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace;
```

> `Inter` is BANNED. `Geist` is the fallback if `Satoshi` is unavailable.

### Type Scale

| Role | Size | Weight | Font | Tracking |
|------|------|--------|------|---------|
| Page Title | `1.25rem` / 20px | 700 | Satoshi | `-0.015em` |
| Section Heading | `1rem` / 16px | 600 | Satoshi | `-0.01em` |
| Card Title | `0.9375rem` / 15px | 600 | Satoshi | `0` |
| Body Default | `0.875rem` / 14px | 400 | Satoshi | `0` |
| Body Small | `0.8125rem` / 13px | 400 | Satoshi | `0` |
| Label / Caption | `0.75rem` / 12px | 500 | Satoshi | `+0.03em` |
| Table Header | `0.6875rem` / 11px | 600 | Satoshi | `+0.06em` (uppercase) |
| **Financial Value Large** | `1.75rem` / 28px | 700 | **JetBrains Mono** | `-0.02em` |
| **Financial Value Medium** | `1.25rem` / 20px | 600 | **JetBrains Mono** | `-0.01em` |
| **Financial Value Small** | `0.875rem` / 14px | 500 | **JetBrains Mono** | `0` |
| **Table Numbers** | `0.8125rem` / 13px | 400 | **JetBrains Mono** | `0` |

### Typography Rules
- All `Rp` currency values, numeric IDs, dates, and percentages → `JetBrains Mono`
- `font-variant-numeric: tabular-nums` on ALL financial tables
- Body text line-height: `1.6`; Headlines: `1.2`
- Max readable line length: 65ch

---

## 4. Component Designs

### 4.1 Navbar

**Current problem:** Solid `#1a56db` bar feels like a generic admin panel.

**Target design:**
```
Background: #09090B (Ink Black)
Height: 56px
Border-bottom: 1px solid #27272A
Logo: Wordmark only — "Finance Hub" in Satoshi 700 + thin slash separator + company name in Satoshi 400 text-muted
Right slot: user chip (avatar initial + name) | divider | logout ghost button
No emojis anywhere
```

**Logo treatment:**
```
Finance Hub  /  PT Energi Tarahan Fajar
[Satoshi 600]    [Satoshi 400 text-muted, smaller]
```

### 4.2 Sidebar

**Current problem:** Flat anchor list, no depth, emoji icons.

**Target design:**
```css
background: #09090B;
width: 220px;
/* Active state */
.sidebar-link.active {
  background: #18181B;
  border-left: 2px solid #2D6ADF; /* accent rail */
  color: #F4F4F5;
  padding-left: calc(1.25rem - 2px); /* compensate border */
}
/* Hover state */
.sidebar-link:hover {
  background: #18181B;
  color: #E4E4E7;
  transition: background 150ms ease, color 150ms ease;
}
/* Section label */
.sidebar-section {
  font-size: 0.6875rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #52525B;
  padding: 1.25rem 1.25rem 0.375rem;
}
/* Coming soon */
.sidebar-link.disabled {
  opacity: 0.35;
  pointer-events: none;
  /* NO strikethrough, NO emoji, just muted */
}
```

Icons: Use `lucide-react` or inline SVG (16×16, `stroke-width: 1.5`). Remove all emoji icons.

### 4.3 Stat Cards (Dashboard)

**Current problem:** `auto-fit minmax` equal 3-column grid — banned pattern.

**Target: Asymmetric KPI Row**
```
Layout: 2 primary KPIs (large) + N secondary KPIs (compact)
Not equal columns — primary KPIs take 1.5× width
```

```css
.kpi-grid {
  display: grid;
  grid-template-columns: 1.5fr 1.5fr repeat(auto-fit, minmax(160px, 1fr));
  gap: 1rem;
}
.kpi-card-primary { /* Large KPI */
  background: #09090B;
  color: #F4F4F5;
  border-radius: 10px;
  padding: 1.5rem;
}
.kpi-card-primary .kpi-value {
  font-family: 'JetBrains Mono', monospace;
  font-size: 2rem;
  font-weight: 700;
  line-height: 1.1;
  /* Animate with counter on mount */
}
.kpi-card-secondary {
  background: #FFFFFF;
  border: 1px solid #E4E4E7;
  border-radius: 10px;
  padding: 1.25rem;
}
```

**Anatomy of a KPI card:**
```
[Label in caps 11px text-muted]
[Value in JetBrains Mono — animated counter]
[Delta badge: ↑ +12% vs last month]  ← optional
```

### 4.4 Buttons

```css
/* Primary CTA */
.btn-primary {
  background: #2D6ADF;
  color: #FFFFFF;
  padding: 0.5rem 1.125rem;
  border-radius: 6px;
  font-size: 0.875rem;
  font-weight: 500;
  border: 1px solid transparent;
  transition: background 150ms ease, transform 80ms ease, box-shadow 150ms ease;
  box-shadow: 0 1px 2px rgba(0,0,0,0.08);
}
.btn-primary:hover { background: #1D4ED8; }
.btn-primary:active {
  transform: translateY(1px);
  box-shadow: none;
  /* Tactile push — no neon glow */
}

/* Ghost / secondary */
.btn-secondary {
  background: transparent;
  color: #3F3F46;
  border: 1px solid #D4D4D8;
  padding: 0.5rem 1.125rem;
}
.btn-secondary:hover { background: #F4F4F5; border-color: #A1A1AA; }

/* Destructive */
.btn-danger {
  background: #DC2626;
  color: #FFF;
  border: 1px solid transparent;
}
/* NO outer glow on any button state */
```

### 4.5 Data Tables

```css
/* Table container */
.table-container {
  border: 1px solid #E4E4E7;
  border-radius: 8px;
  overflow: hidden; /* clips header radius */
}

/* Header row */
thead tr {
  background: #FAFAFA;
  border-bottom: 1px solid #E4E4E7;
}
th {
  font-family: 'Satoshi', sans-serif;
  font-size: 0.6875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: #71717A;
  padding: 0.625rem 0.875rem;
  white-space: nowrap;
}

/* Data rows — staggered mount animation */
tbody tr {
  border-bottom: 1px solid #F4F4F5;
  transition: background 100ms ease;
  /* Stagger via nth-child delay on first render */
  animation: row-slide-in 200ms ease forwards;
  opacity: 0;
  transform: translateY(4px);
}
tbody tr:hover { background: #FAFAFA; }
tbody tr:last-child { border-bottom: none; }

@keyframes row-slide-in {
  to { opacity: 1; transform: translateY(0); }
}

/* Financial cells */
td.num-right {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.8125rem;
  text-align: right;
  font-variant-numeric: tabular-nums;
}

/* Footer totals */
tfoot tr {
  background: #FAFAFA;
  border-top: 2px solid #E4E4E7;
}
tfoot td {
  font-family: 'JetBrains Mono', monospace;
  font-weight: 600;
  font-size: 0.875rem;
}
```

### 4.6 Forms & Inputs

```css
.form-label {
  font-size: 0.75rem;
  font-weight: 600;
  color: #3F3F46;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-bottom: 0.375rem;
}

.form-input {
  background: #FFFFFF;
  border: 1px solid #D4D4D8;
  border-radius: 6px;
  padding: 0.5625rem 0.75rem;
  font-size: 0.875rem;
  color: #09090B;
  transition: border-color 150ms ease, box-shadow 150ms ease;
  width: 100%;
}
.form-input:focus {
  border-color: #2D6ADF;
  box-shadow: 0 0 0 3px rgba(45, 106, 223, 0.12);
  outline: none;
}
.form-input::placeholder { color: #A1A1AA; }
/* Error state */
.form-input.error {
  border-color: #DC2626;
  box-shadow: 0 0 0 3px rgba(220, 38, 38, 0.10);
}
.form-error-text {
  font-size: 0.75rem;
  color: #DC2626;
  margin-top: 0.25rem;
}
```

### 4.7 Tabs

**Current problem:** Flat underline tab with no visual weight.

```css
.tabs {
  display: flex;
  gap: 0;
  border-bottom: 1px solid #E4E4E7;
  margin-bottom: 1.5rem;
}
.tab-btn {
  padding: 0.625rem 1rem;
  font-size: 0.8125rem;
  font-weight: 500;
  color: #71717A;
  border: none;
  background: none;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
  cursor: pointer;
  transition: color 150ms ease, border-color 150ms ease;
  white-space: nowrap;
}
.tab-btn.active {
  color: #09090B;
  border-bottom-color: #2D6ADF;
  font-weight: 600;
}
.tab-btn:hover:not(.active) {
  color: #3F3F46;
  background: #F4F4F5;
  border-radius: 4px 4px 0 0;
}
/* Tab panel transition */
.tab-panel.active {
  animation: tab-fade-in 200ms ease forwards;
}
@keyframes tab-fade-in {
  from { opacity: 0; transform: translateY(3px); }
  to   { opacity: 1; transform: translateY(0); }
}
```

### 4.8 Badges / Status Pills

```css
.badge {
  display: inline-flex;
  align-items: center;
  padding: 0.1875rem 0.5rem;
  border-radius: 9999px;
  font-size: 0.6875rem;
  font-weight: 600;
  letter-spacing: 0.02em;
  text-transform: uppercase;
  white-space: nowrap;
}
/* Tokens */
.badge-active    { background: #ECFDF5; color: #065F46; }
.badge-draft     { background: #FFFBEB; color: #92400E; }
.badge-rejected  { background: #FEF2F2; color: #991B1B; }
.badge-approved  { background: #EFF6FF; color: #1E40AF; }
.badge-inactive  { background: #F4F4F5; color: #52525B; }
```

### 4.9 Modals

```css
.modal-overlay {
  background: rgba(9,9,11,0.65);
  backdrop-filter: blur(4px);
  -webkit-backdrop-filter: blur(4px);
  animation: overlay-in 200ms ease;
}
@keyframes overlay-in {
  from { opacity: 0; }
  to   { opacity: 1; }
}
.modal {
  background: #FFFFFF;
  border-radius: 12px;
  border: 1px solid #E4E4E7;
  padding: 1.75rem;
  width: min(560px, 95vw);
  max-height: 88vh;
  overflow-y: auto;
  box-shadow:
    0 4px 6px rgba(0,0,0,0.04),
    0 20px 60px rgba(0,0,0,0.14);
  animation: modal-spring 250ms cubic-bezier(0.34, 1.56, 0.64, 1);
}
@keyframes modal-spring {
  from { opacity: 0; transform: scale(0.96) translateY(8px); }
  to   { opacity: 1; transform: scale(1) translateY(0); }
}
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.25rem;
  padding-bottom: 1.25rem;
  border-bottom: 1px solid #F4F4F5;
}
.modal-title {
  font-size: 1rem;
  font-weight: 600;
  color: #09090B;
  letter-spacing: -0.01em;
}
```

### 4.10 Login Page

**Current problem:** Centered generic card with emoji logo.

**Target: Dark Split Layout**
```
Left panel (45% width):  Dark #09090B — brand identity, tagline, abstract data visual
Right panel (55% width): White — login form

Left panel content:
  - "Finance Hub" wordmark in Satoshi 700, size 1.75rem
  - Tagline in Satoshi 400 text-muted
  - Abstract SVG illustration: flowing financial data lines / nodes
  - NO emojis
  - Bottom: company tagline in very small muted text

Right panel:
  - "Welcome back" heading Satoshi 700 1.5rem
  - Subtext "Sign in to your account" Satoshi 400 text-muted
  - Form with elevated inputs (slight shadow on focus)
  - Full-width primary CTA "Sign in"
  - NO secondary links/CTAs

Mobile (< 768px): Left panel collapses, right panel full-screen centered
```

### 4.11 Skeletal Loaders

Replace all "Memuat..." text placeholders with dimension-matched skeleton loaders:

```css
@keyframes shimmer {
  0%   { background-position: -400px 0; }
  100% { background-position: 400px 0; }
}
.skeleton {
  background: linear-gradient(
    90deg,
    #F4F4F5 25%,
    #E4E4E7 37%,
    #F4F4F5 63%
  );
  background-size: 800px 100%;
  animation: shimmer 1.4s ease infinite;
  border-radius: 4px;
}
/* Skeleton table row */
.skeleton-row td { padding: 0.75rem 0.875rem; }
.skeleton-cell  { height: 14px; border-radius: 3px; }
.skeleton-cell.wide  { width: 70%; }
.skeleton-cell.narrow { width: 40%; }
.skeleton-cell.num   { width: 80px; margin-left: auto; }
```

---

## 5. Layout Principles

### 5.1 App Shell

```
[Navbar — 56px fixed — Ink Black]
  [Sidebar — 220px fixed left — Ink Black]
  [Main content — margin-left: 220px, padding: 1.75rem]
    max-width: none (full remaining width)
    background: #FAFAFA
```

### 5.2 Page Header Pattern

Every page must follow this structure:
```
[Page Title — Satoshi 700 20px]          [Action buttons — right-aligned]
[Breadcrumb or context — text-muted]

[Content (tabs / table / cards)]
```

No inline `style=""` attributes. All layout via CSS classes.

### 5.3 Card Pattern

Use cards **only** when elevation communicates hierarchy. For high-density data pages (Beasiswa, Payment), prefer bordered containers without box-shadow:

```css
.container-subtle {
  border: 1px solid #E4E4E7;
  border-radius: 8px;
  overflow: hidden;
}
/* vs */
.card-elevated {
  background: #FFFFFF;
  border: 1px solid #E4E4E7;
  border-radius: 10px;
  padding: 1.5rem;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}
```

### 5.4 Sidebar Navigation Order

```
Dashboard

— ETF (conditional) —
  Beasiswa

— Pembayaran —
  Payment Memo
  Payment Application

— Coming Soon —
  Bank, Account Payable, Advance, Petty Cash, Sponsorship

— Admin (role-gated) —
  User Management
```

No horizontal rules as visual dividers. Section labels serve as separators.

---

## 6. Motion & Interaction

### 6.1 Spring Physics Default

```css
/* All transitions use this timing unless specified */
transition-timing-function: cubic-bezier(0.34, 1.56, 0.64, 1); /* spring-out */
/* For exits */
transition-timing-function: cubic-bezier(0.25, 0.1, 0.25, 1);  /* ease-out */
```

### 6.2 Stagger Cascade — Table Rows

```javascript
// On data load, apply staggered animation to each row
tbody.querySelectorAll('tr').forEach((row, i) => {
  row.style.animationDelay = `${i * 30}ms`;
  row.style.animationFillMode = 'both';
});
```

### 6.3 KPI Counter Animation

```javascript
// Animate financial values from 0 to target on mount
function animateCounter(el, target, duration = 800) {
  const start = performance.now();
  const isFloat = String(target).includes('.');
  const update = (now) => {
    const progress = Math.min((now - start) / duration, 1);
    const ease = 1 - Math.pow(1 - progress, 3); // ease-out-cubic
    const current = Math.floor(ease * target);
    el.textContent = new Intl.NumberFormat('id-ID').format(current);
    if (progress < 1) requestAnimationFrame(update);
    else el.textContent = new Intl.NumberFormat('id-ID').format(target);
  };
  requestAnimationFrame(update);
}
```

### 6.4 Page/Tab Transitions

```css
/* Tab content fade-slide (200ms) */
@keyframes tab-in {
  from { opacity: 0; transform: translateY(4px); }
  to   { opacity: 1; transform: translateY(0); }
}

/* Sidebar active indicator slide */
.sidebar-link {
  position: relative;
}
.sidebar-link::before {
  content: '';
  position: absolute;
  left: 0; top: 0; bottom: 0;
  width: 2px;
  background: #2D6ADF;
  border-radius: 0 2px 2px 0;
  transform: scaleY(0);
  transition: transform 200ms cubic-bezier(0.34, 1.56, 0.64, 1);
}
.sidebar-link.active::before { transform: scaleY(1); }
```

### 6.5 Micro-Interactions

| Component | Idle State | Interaction |
|-----------|-----------|-------------|
| Primary button | Resting | Active: `translateY(1px)` — tactile push |
| Sidebar link | Muted text | Hover: `background` slide 150ms |
| Table row | White | Hover: `#FAFAFA` 100ms |
| Input field | Zinc border | Focus: Cobalt border + 3px ring 150ms |
| Tab button | Muted | Active: border-bottom slide + weight change |
| Modal | — | Mount: spring scale from 0.96 |
| Stat card (KPI) | Static value | On mount: counter animation 800ms |

### 6.6 Performance Rules

- Animate **only** via `transform` and `opacity`
- Never animate `width`, `height`, `top`, `left`, `margin`, or `padding`
- Use `will-change: transform` only on elements with active spring animations; remove after animation completes

---

## 7. Anti-Patterns (Banned)

### Typography
- `Inter` font — use `Satoshi`
- Generic serif fonts (`Georgia`, `Times New Roman`, `Garamond`)
- Font size below `0.6875rem` (11px)

### Layout
- Equal 3-column `auto-fit minmax` stat card grids
- Inline `style=""` attributes for layout or colors — use CSS classes
- `calc()` percentage hacks for column widths — use CSS Grid
- `h-screen` — use `min-h-[100dvh]`
- Centered login without brand panel (for desktop)

### Color & Visuals
- Pure black `#000000`
- `#1a56db` generic blue as-is (replace with `#2D6ADF`)
- Neon outer glow (`box-shadow: 0 0 20px rgba(accent, 0.5)`)
- Oversaturated accents (> 80% saturation)
- Purple/violet UI chrome (AI purple aesthetic)
- `filter: brightness()` as sole hover feedback — add `transform` too

### Icons & Imagery
- Emojis in navigation, buttons, labels (⚡🏠🎓📋📊💳🏦👤👥)
- Emoji in brand logo or wordmark
- Generic round avatars with initials as the sole brand element
- Placeholder text like "Memuat..." without skeleton loaders

### Copy & Content
- AI clichés: "Canggih", "Revolusi", "Seamless", "Elevate", "Next-Gen"
- Filler navigation labels like "Coming Soon" as visible UI elements — disable + tooltip only
- Fabricated statistics or fake round numbers (`99.99%`, `100%`)
- `[object Object]` or raw API responses in error states

### Motion
- Linear easing on UI transitions (`transition: all 0.3s linear`)
- Layout-thrashing animations (`height`, `margin`)
- No animation at all on data tables loading (must stagger)
- Instant list mounts with no cascade

---

## 8. Implementation Priority

### Phase 1 — Foundation (Critical, no new features)
1. Replace `Inter` → `Satoshi` + `JetBrains Mono` (Google Fonts CDN)
2. Remove all emoji from navigation and buttons
3. Update navbar: `#1a56db` solid → `#09090B` Ink Black + border-bottom
4. Update sidebar: active state with left `#2D6ADF` rail
5. Update all financial number cells to `JetBrains Mono`

### Phase 2 — Component Polish
6. Replace equal stat grid → asymmetric KPI layout with dark primary cards
7. Add skeletal loaders for all async table loads
8. Refactor table styles: bordered container, new header weight/case
9. Update button states: spring tactile press, no `filter: brightness` only

### Phase 3 — Motion Layer
10. Staggered table row animation on load
11. KPI counter animation on mount
12. Tab transition fade-slide
13. Modal spring mount/dismount
14. Sidebar active indicator slide

### Phase 4 — Login Redesign
15. Split-panel login layout (dark left / white right)
16. Remove emoji from wordmark

---

*Design System: Finance Hub — Generated 2026-05-31*
*Target: Modern Enterprise + Cinematic. Density 7, Variance 6, Motion 7.*
