# FinanceHub UI — Navigation & Quick Win Improvements

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** (1) Replace overflowing horizontal navbar with a clean command palette (Ctrl+K). (2) Implement three high-impact Quick Win UX improvements: skeleton loading, sortable columns, sticky filter bar.

**Architecture:** Pure frontend — no backend changes. All logic in `base.html`, `app.js`, `style.css`, and per-module templates where needed.

**Tech Stack:** Vanilla JS (no library), CSS variables (existing design system), localStorage for recently-visited and density preferences.

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

---

## Section 6: Skeleton Loading

Replace all "Memuat data..." / "Memuat…" text placeholders with animated skeleton rows while API fetches are in progress.

### Shared helper in `app.js`:

```javascript
function skeletonRows(cols, count = 6) {
  return Array(count).fill(0).map(() =>
    `<tr class="fh-skel-row">${
      Array(cols).fill(0).map((_, i) =>
        `<td><div class="fh-skel" style="width:${55 + (i * 17) % 35}%"></div></td>`
      ).join('')
    }</tr>`
  ).join('');
}
```

Call before every API fetch that renders into a `<tbody>`:
```javascript
tbody.innerHTML = skeletonRows(N_COLS);        // show skeleton
const data = await apiFetch(url);              // fetch
tbody.innerHTML = data.ok ? renderRows(data)   // replace with real data
                          : emptyState();
```

### CSS in `style.css`:

```css
.fh-skel {
  height: 11px; border-radius: 4px;
  background: linear-gradient(90deg, var(--bg-muted) 25%, var(--border) 50%, var(--bg-muted) 75%);
  background-size: 200% 100%;
  animation: fh-shimmer 1.2s ease-in-out infinite;
}
@keyframes fh-shimmer { 0% { background-position: 200% 0 } 100% { background-position: -200% 0 } }
.fh-skel-row td { padding: 10px 8px; }
```

### Apply to these `<tbody>` elements:
- `#pam-tbody` (AGRI Open PAM) — N=11 cols
- `#fiori-tbody` (APP) — N=11 cols
- `#sml-tbody` (LAND) — N=11 cols
- `#setf-tbody` (SETF) — N=11 cols
- `#beasiswa-tbody` (Beasiswa) — check actual col count

---

## Section 7: Sortable Column Headers

Click any `<th>` in pillar tables to sort by that column. Clicking again reverses direction.

### Implementation pattern (shared, applied per-table):

```javascript
function makeSortable(tbody, getRows, colDefs) {
  // colDefs: array of { key, numeric }
  let sortCol = null, sortAsc = true;

  document.querySelectorAll('#my-table thead th[data-sort]').forEach((th, i) => {
    th.style.cursor = 'pointer';
    th.addEventListener('click', () => {
      if (sortCol === i) sortAsc = !sortAsc; else { sortCol = i; sortAsc = true; }
      // update ▲▼ indicators on all th
      document.querySelectorAll('#my-table thead th[data-sort]').forEach((h, j) => {
        h.dataset.sortDir = j === sortCol ? (sortAsc ? 'asc' : 'desc') : '';
      });
      const rows = getRows();
      const { key, numeric } = colDefs[i];
      rows.sort((a, b) => {
        const va = numeric ? (+a[key] || 0) : (a[key] || '').toLowerCase();
        const vb = numeric ? (+b[key] || 0) : (b[key] || '').toLowerCase();
        return sortAsc ? (va > vb ? 1 : -1) : (va < vb ? 1 : -1);
      });
      tbody.innerHTML = rows.map(renderRow).join('');
    });
  });
}
```

### CSS in `style.css`:

```css
th[data-sort] { user-select: none; }
th[data-sort]::after { content: ' ⇅'; opacity: .3; font-size: .7em; }
th[data-sort-dir="asc"]::after  { content: ' ▲'; opacity: 1; color: var(--accent-text); }
th[data-sort-dir="desc"]::after { content: ' ▼'; opacity: 1; color: var(--accent-text); }
```

### Apply `data-sort` attribute to sortable `<th>` in:
- AGRI Open PAM table: `pam_date`, `total_amount`, `due_date`
- SETF table: `pam_date`, `total_amount`, `due_date`
- APP (FIORI) table: `pam_date`, `total_amount`
- LAND (SML) table: `pam_date`, `total_amount`
- Beasiswa table: columns as appropriate

---

## Section 8: Sticky Filter Bar

Filter row menempel di top viewport saat user scroll ke bawah di tabel panjang.

### CSS in `style.css` (single rule, applies globally):

```css
.filter-bar {
  position: sticky;
  top: var(--navbar-h, 52px);
  z-index: 10;
  background: var(--bg);           /* cover scrolled table content */
  border-bottom: 1px solid var(--border);
  padding-bottom: .5rem;
}
```

### Verify `.filter-bar` class is used on filter wrappers in:
- `payment_memo/index.html` — AGRI, APP, LAND, SETF tabs each have a `.filter-bar` div (confirm or add class)
- `etf_payment_application/index.html` — filter row above Open PA table
- `beasiswa/index.html` — filter row

If any filter wrapper lacks `.filter-bar` class, add it. No JS needed — pure CSS.

---

## Files Changed

| File | Change |
|---|---|
| `app/templates/base.html` | Remove `<nav class="navbar-links">`, add `#fh-cmd-btn`, add `#fh-cmd-ov` HTML, add `data-module` to `<body>` |
| `app/static/css/style.css` | Remove navbar-links CSS; add command palette CSS; add `.fh-skel`/`@keyframes fh-shimmer`; add `th[data-sort]` sort indicators; add `.filter-bar` sticky rule |
| `app/static/js/app.js` | Add `FH_MODULES` registry, `initCommandPalette()`, recently-visited logic; add `skeletonRows()` shared helper; add `makeSortable()` helper |
| `app/templates/payment_memo/index.html` | Strip `-- {{ company_name }}` from h1; add skeleton before each pillar fetch; add `data-sort` to sortable `<th>`; confirm `.filter-bar` class on filter wrappers |
| `app/templates/etf_payment_application/index.html` | Add skeleton before Open PA fetch; add `data-sort` to PA NUMBER, TGL PA, TOTAL columns; confirm `.filter-bar` |
| `app/templates/beasiswa/index.html` | Add skeleton before table fetch; confirm `.filter-bar` |
