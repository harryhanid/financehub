# Command Palette Navigation — Implementation Design

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the overflowing horizontal navbar with a clean command palette (Ctrl+K) that scales as new modules are added, while keeping the company (PT) name always visible in the header.

**Architecture:** Pure frontend — static module registry in `app.js`, command palette HTML injected into `base.html`, styles in `style.css`. No backend changes.

**Tech Stack:** Vanilla JS (no library), CSS variables (existing design system), localStorage for recently-visited tracking.

---

## Global Constraints

- No new JS libraries or npm dependencies
- All CSS must use existing `--card`, `--border`, `--accent`, `--sl-*` variables for automatic dark/light mode support
- Keyboard: `Ctrl+K` opens, `↑↓` navigates, `Enter` selects, `Esc` closes
- Must work on all existing page templates without individual changes (logic lives in `base.html` + `app.js`)
- Recently visited: localStorage key `fh_recent_modules`, max 5 stored, show top 3 in palette default state
- Coming-soon modules: appear in search results grayed-out with "Coming Soon" badge, non-clickable
- Company name (PT selector) stays in navbar — click still opens `/select-company`

---

## Section 1: Navbar Layout Change

**Before:**
```
[FH] Finance Hub / Eka Tjipta Foundation | Dashboard Beasiswa Payment Memo ... Budget | ☀ admin → Keluar
```

**After:**
```
[FH] Finance Hub / Eka Tjipta Foundation                    [🔍 Cari modul  Ctrl+K]  ☀  admin  → Keluar
```

**Changes to `base.html`:**
- Remove entire `<nav class="navbar-links">` block (lines 33–53)
- Add search trigger button `#fh-cmd-btn` between company area and user controls
- Add command palette HTML `#fh-cmd-ov` (overlay + modal) before `</body>`

**Changes to `style.css`:**
- Remove `.navbar-links`, `.navbar-link`, `.navbar-sep` rules
- Add `.fh-cmd-btn` (search trigger) styles
- Add `#fh-cmd-ov`, `.fh-cmd-modal`, `.fh-cmd-input`, `.fh-cmd-results`, `.fh-cmd-item`, `.fh-cmd-item.active`, `.fh-cmd-item.disabled`, `.fh-cmd-section` styles
- Full dark mode support via existing CSS variables

---

## Section 2: Command Palette UX

### Default state (no query typed):
```
┌─────────────────────────────────────────┐
│  🔍  Cari modul...                  Esc │
├─────────────────────────────────────────┤
│  TERAKHIR DIKUNJUNGI                    │
│  ▸ Payment Application                  │
│  ▸ Beasiswa                             │
├─────────────────────────────────────────┤
│  SEMUA MODUL                            │
│  ▸ Dashboard                            │
│  ▸ Beasiswa                             │
│  ▸ Payment Approval Memo                │
│  ▸ Payment Application                  │
│  ▸ Budget                               │
│  ▸ Users                                │
│  ─────────────────────────────          │
│  ▸ Bank              [Coming Soon]      │
│  ▸ Account Payable   [Coming Soon]      │
│  ▸ Advance           [Coming Soon]      │
│  ▸ Petty Cash        [Coming Soon]      │
│  ▸ Sponsorship       [Coming Soon]      │
└─────────────────────────────────────────┘
```

### With query (e.g. "pay"):
```
┌─────────────────────────────────────────┐
│  🔍  pay                            Esc │
├─────────────────────────────────────────┤
│  HASIL PENCARIAN                        │
│  ▸ Payment Approval Memo   ← highlighted│
│  ▸ Payment Application                  │
│  ▸ Account Payable  [Coming Soon]       │
└─────────────────────────────────────────┘
```

### Behavior rules:
- Search: `module.name.toLowerCase().includes(query.toLowerCase())` — simple substring match
- Coming-soon items: always visible in search results, cursor `not-allowed`, click does nothing
- "Terakhir Dikunjungi" section: hidden when user is typing (replaced by "Hasil Pencarian")
- First active result is auto-highlighted on open and on each keystroke
- Clicking backdrop closes palette
- `window.location.href = url` for navigation (simple, consistent with existing codebase)

---

## Section 3: Module Registry

Defined as a constant in `app.js`. Adding a new module = add one object:

```javascript
const FH_MODULES = [
  { name: "Dashboard",             url: "/dashboard",               active: true  },
  { name: "Beasiswa",              url: "/beasiswa",                active: true  },
  { name: "Payment Approval Memo", url: "/payment-memo",            active: true  },
  { name: "Payment Application",   url: "/etf-payment-application", active: true  },
  { name: "Budget",                url: "/budget/",                 active: true  },
  { name: "Users",                 url: "/users",                   active: true  },
  { name: "Bank",                  url: null,                       active: false },
  { name: "Account Payable",       url: null,                       active: false },
  { name: "Advance",               url: null,                       active: false },
  { name: "Petty Cash",            url: null,                       active: false },
  { name: "Sponsorship",           url: null,                       active: false },
];
```

---

## Section 4: Recently Visited Tracking

- On every `DOMContentLoaded`: read `data-module` attribute from `<body>` (set per-template via Jinja `active_page`), push to localStorage array, dedupe, cap at 5
- `base.html` passes `active_page` → `<body data-module="{{ active_page or '' }}">`
- Module name lookup: map `active_page` value → display name using `FH_MODULES`
- `initCommandPalette()` called once in `app.js` `DOMContentLoaded`

---

## Section 5: Page Title Cleanup

All templates that show `-- {{ company_name }}` in the `<h1>` should be stripped — the company name is always visible in the navbar.

**Affected:** `templates/payment_memo/index.html` line 119 (only occurrence currently).

Change: `Payment Approval Memo -- {{ company_name }}` → `Payment Approval Memo`

---

## Files Changed

| File | Change |
|---|---|
| `app/templates/base.html` | Remove `<nav class="navbar-links">`, add `#fh-cmd-btn`, add `#fh-cmd-ov` HTML, add `data-module` to `<body>` |
| `app/static/css/style.css` | Remove navbar-links CSS, add command palette CSS |
| `app/static/js/app.js` | Add `FH_MODULES` registry, `initCommandPalette()`, recently-visited logic |
| `app/templates/payment_memo/index.html` | Strip `-- {{ company_name }}` from h1 |
