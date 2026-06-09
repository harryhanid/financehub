# Company Select — Full Split Screen Design

**Date:** 2026-06-09  
**Status:** Approved

## Overview

Replace the current card grid on `/select-company` with a full-viewport split layout. Each company occupies exactly half the screen — clicking anywhere on a half selects that company. Zero cursor-aiming required.

## Layout

Two panels fill `100dvh × 100vw` side by side via `display: flex`. A 1px semi-transparent divider sits between them. A "FINANCE HUB" badge is pinned to the top-center — placed as the first child **inside** `.cs-split` (which has `position: relative`), so the badge's `position: absolute` resolves against the split container.

On mobile (`≤600px`) the panels stack vertically (top = SMT, bottom = ETF) and the badge is hidden.

## Visual Style

| Element | SMT | ETF |
|---------|-----|-----|
| Background | `linear-gradient(150deg, #1a3252, #2d5a8e, #1e4d7a)` | `linear-gradient(150deg, #2e1650, #5c2d91, #3d1a6e)` |
| Icon | 🏢 (72px) | 🏛️ (72px) |
| Name | "Sinar Mas Tjipta" | "Eka Tjipta Foundation" |
| Code badge | SMT | ETF |

Each panel content is centered vertically and horizontally. Text is white; the code badge uses a frosted-glass pill (`rgba(255,255,255,.12)` background, `rgba(255,255,255,.15)` border).

## Interaction

- **Hover**: panel brightens via `filter: brightness(1.12)` + a subtle "Pilih →" label fades in at the bottom of the panel.
- **Click**: submits the existing `<form method="POST">` with `name="company_id"` — no backend changes needed.
- **Transition**: `filter` and `opacity/transform` on 0.18s ease.

## Dark Mode

Both panels use their own gradient backgrounds regardless of the app theme — no additional dark-mode overrides needed.

## Files to Change

| File | Change |
|------|--------|
| `app/templates/company_select.html` | Full rewrite of the page body |
| `app/static/css/style.css` | Replace `.select-wrap`, `.company-grid`, `.company-card`, `.company-icon`, `.company-name`, `.company-code` with new `.cs-split`, `.cs-panel`, `.cs-panel-smt`, `.cs-panel-etf`, `.cs-divider`, `.cs-badge`, `.cs-icon`, `.cs-name`, `.cs-code`, `.cs-hint` classes. Remove old dark-mode overrides for these selectors. |

## What Does Not Change

- Route (`/select-company` GET + POST), session logic, redirect behavior — untouched.
- Font (`Figtree`) and CSS variables (`--accent`, etc.) — still imported via `base`/`style.css`.
- All other pages and components.
