# FinanceHub Navigation & Quick Wins Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace overflowing navbar links with a Ctrl+K command palette, and add three UX quick wins: skeleton loading, sortable column headers, and sticky filter bars.

**Architecture:** Pure frontend — zero backend changes. All shared logic lives in `app/static/css/style.css` and `app/static/js/app.js`. Per-module templates receive only HTML attribute additions (no new JS logic per template). Tasks are ordered so each builds on the last without conflicts.

**Tech Stack:** Vanilla JS (no new libraries), CSS custom properties (existing `--card`, `--border`, `--accent`, `--sl-*`), localStorage for recently-visited state.

## Global Constraints

- No new JS libraries or npm dependencies
- All CSS must use existing CSS variables (`--card`, `--bg-muted`, `--accent`, `--sl-*`, `--border`, `--text-muted`) for dark/light mode support — no hardcoded hex colors
- Command palette keyboard: `Ctrl+K` opens, `↑↓` navigates active items, `Enter` selects, `Esc` closes
- `data-sort` attribute on `<th>` holds the **column index** (0-based integer), not a field name — DOM-based sort
- `data-sort-type="num"` on numeric columns; omit for text/date (lexicographic sort works for YYYY-MM-DD)
- Recently visited: localStorage key `fh_recent_modules`, max 5 stored, show top 3 in default palette state
- Coming-soon modules appear grayed-out with "Coming Soon" badge — non-clickable, but visible in search results
- Company name stays in navbar; `<nav class="navbar-links">` block is removed; `{% if company_name %}` conditions preserved
- `#pa-page-header` in etf_payment_application already has `position:sticky` — do not add `.filter-bar` there

---

## File Structure

| File | Changes |
|---|---|
| `app/static/css/style.css` | Remove `.navbar-links`/`.navbar-link` rules; add command palette CSS; add skeleton shimmer; add sort indicators; add `.filter-bar` |
| `app/static/js/app.js` | Add `FH_MODULES`, `initCommandPalette()`, `skeletonRows()`, `makeSortable()`; update `DOMContentLoaded` |
| `app/templates/base.html` | Add `data-module` to `<body>`; remove `<nav class="navbar-links">` block; add `#fh-cmd-btn` button; add `#fh-cmd-ov` overlay |
| `app/templates/payment_memo/index.html` | Strip `-- {{ company_name }}` from h1; add `skeletonRows()` call + `makeSortable()` call to 4 load functions; add `data-sort` to `<th>` in 4 tables; add `filter-bar` class to 4 filter divs |
| `app/templates/beasiswa/index.html` | Add `skeletonRows()` to `loadPaymentList()`; add `filter-bar` class to payment filter div |
| `app/templates/etf_payment_application/index.html` | Add `data-sort` to 3 `<th>` in `#pa-table` |

---

## Task 1: CSS — Remove navbar-links, add command palette + quick wins CSS

**Files:**
- Modify: `app/static/css/style.css` (lines 138–163 are the navbar-links rules to remove)

**Interfaces:**
- Produces: `.fh-cmd-btn`, `#fh-cmd-ov`, `.fh-cmd-modal`, `.fh-cmd-input`, `.fh-cmd-results`, `.fh-cmd-item`, `.fh-cmd-item.active`, `.fh-cmd-item.disabled`, `.fh-cmd-section`, `.fh-cmd-sep`, `.fh-cmd-badge`, `.fh-cmd-empty`, `.fh-skel`, `.fh-skel-row`, `@keyframes fh-shimmer`, `th[data-sort]`, `th[data-sort-dir]`, `.filter-bar` CSS classes — consumed by Tasks 2–5

- [ ] **Step 1: Remove `.navbar-links` block in `style.css`**

Find and delete lines 138–163 (the entire `/* ── Navbar links */` block):

```css
/* ── Navbar links ────────────────────────────────────── */
.navbar-links {
  display: flex; align-items: center; gap: .125rem;
  flex-wrap: nowrap; overflow-x: auto;
}
.navbar-link {
  font-size: .775rem; font-weight: 500;
  color: var(--sl-500);
  padding: .3rem .5rem;
  border-radius: var(--r-sm);
  white-space: nowrap;
  transition: color .1s, background .1s;
  border-bottom: 2px solid transparent;
}
.navbar-link:hover { color: var(--sl-800); background: var(--sl-100); }
.navbar-link.active {
  color: var(--accent-text);
  font-weight: 600;
  border-bottom-color: var(--accent);
  background: var(--accent-surface);
}
.navbar-link.coming-soon {
  opacity: .35;
  pointer-events: none;
  cursor: default;
}
```

- [ ] **Step 2: Add command palette CSS after the `.btn-logout` block**

Append after line 136 (after `.btn-logout:hover { ... }` and before `/* ── Main layout */`):

```css
/* ── Command Palette Search Button ─────────────────────── */
.fh-cmd-btn {
  margin-left: auto;
  display: flex; align-items: center; gap: .4rem;
  background: var(--sl-100);
  border: 1px solid var(--sl-200);
  border-radius: var(--r-md);
  color: var(--sl-500);
  font-size: .775rem; font-weight: 500;
  padding: .275rem .625rem;
  cursor: pointer;
  font-family: inherit;
  transition: background .12s, border-color .12s, color .12s;
  white-space: nowrap;
}
.fh-cmd-btn:hover { background: var(--sl-200); color: var(--sl-700); border-color: var(--sl-300); }
.fh-cmd-btn kbd {
  font-size: .65rem; padding: .1rem .3rem;
  background: var(--sl-200); border: 1px solid var(--sl-300);
  border-radius: 3px; color: var(--sl-500);
  font-family: var(--mono);
}

/* ── Command Palette Overlay ────────────────────────────── */
#fh-cmd-ov {
  display: none;
  position: fixed; inset: 0;
  background: rgba(15,23,42,.45);
  z-index: 9000;
  align-items: flex-start; justify-content: center;
  padding-top: 88px;
}
#fh-cmd-ov.open { display: flex; }

.fh-cmd-modal {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--r-xl);
  box-shadow: var(--sh-lg);
  width: min(500px, calc(100vw - 2rem));
  overflow: hidden;
}

.fh-cmd-header {
  display: flex; align-items: center; gap: .625rem;
  padding: .75rem 1rem;
  border-bottom: 1px solid var(--border);
  color: var(--text-muted);
}
.fh-cmd-header svg { flex-shrink: 0; }
.fh-cmd-header kbd {
  margin-left: auto; font-size: .65rem; padding: .1rem .35rem;
  background: var(--bg-muted); border: 1px solid var(--border);
  border-radius: 3px; color: var(--text-muted);
  font-family: var(--mono); white-space: nowrap;
}

#fh-cmd-input {
  flex: 1; border: none; outline: none;
  background: transparent; color: var(--ink);
  font-size: .9rem; font-family: inherit;
}

#fh-cmd-results {
  max-height: 360px;
  overflow-y: auto;
  padding: .375rem 0;
}

.fh-cmd-section {
  font-size: .675rem; font-weight: 700;
  letter-spacing: .06em; text-transform: uppercase;
  color: var(--text-muted);
  padding: .5rem 1rem .25rem;
}

.fh-cmd-item {
  display: flex; align-items: center; justify-content: space-between;
  padding: .5rem 1rem;
  cursor: pointer;
  font-size: .85rem;
  color: var(--ink);
  gap: .5rem;
  transition: background .08s;
}
.fh-cmd-item:hover,
.fh-cmd-item.active { background: var(--accent-surface); color: var(--accent-text); }
.fh-cmd-item.disabled {
  opacity: .45; cursor: not-allowed;
}
.fh-cmd-item.disabled:hover,
.fh-cmd-item.disabled.active { background: transparent; color: var(--ink); opacity: .45; }

.fh-cmd-badge {
  font-size: .65rem; font-weight: 600;
  background: var(--bg-muted); color: var(--text-muted);
  border: 1px solid var(--border);
  border-radius: 99px; padding: .1rem .45rem;
  white-space: nowrap; flex-shrink: 0;
}

.fh-cmd-sep {
  height: 1px; background: var(--border); margin: .375rem .75rem;
}

.fh-cmd-empty {
  padding: 1.25rem 1rem;
  text-align: center;
  color: var(--text-muted);
  font-size: .85rem;
}

/* ── Skeleton loading ───────────────────────────────────── */
.fh-skel {
  height: 11px; border-radius: 4px;
  background: linear-gradient(90deg, var(--bg-muted) 25%, var(--border) 50%, var(--bg-muted) 75%);
  background-size: 200% 100%;
  animation: fh-shimmer 1.2s ease-in-out infinite;
}
@keyframes fh-shimmer {
  0%   { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
.fh-skel-row td { padding: 10px 8px; }

/* ── Sortable column headers ────────────────────────────── */
th[data-sort] { user-select: none; }
th[data-sort]::after { content: ' ⇅'; opacity: .3; font-size: .7em; }
th[data-sort-dir="asc"]::after  { content: ' ▲'; opacity: 1; color: var(--accent-text); }
th[data-sort-dir="desc"]::after { content: ' ▼'; opacity: 1; color: var(--accent-text); }

/* ── Sticky filter bar ──────────────────────────────────── */
.filter-bar {
  position: sticky;
  top: var(--navbar-h, 52px);
  z-index: 10;
  background: var(--bg);
  border-bottom: 1px solid var(--border);
  padding-bottom: .5rem;
  margin-bottom: 0 !important;
}
```

- [ ] **Step 3: Verify CSS renders correctly**

Open `http://localhost:5000` in browser. Confirm:
- Navbar no longer shows horizontal nav links (the company name and logout button remain)
- No JS errors in console
- Dark mode still works (toggle with sun/moon button)

Expected: Clean navbar with just `[FH] Finance Hub / Eka Tjipta Foundation ... ☀ admin → Keluar` and nothing between company name and user controls yet (the `#fh-cmd-btn` is added in T3).

- [ ] **Step 4: Commit**

```bash
git add app/static/css/style.css
git commit -m "feat: remove navbar-links CSS, add command palette + quick-win CSS"
```

---

## Task 2: JS — FH_MODULES, initCommandPalette(), skeletonRows(), makeSortable()

**Files:**
- Modify: `app/static/js/app.js`

**Interfaces:**
- Consumes: DOM elements `#fh-cmd-ov`, `#fh-cmd-input`, `#fh-cmd-results`, `#fh-cmd-btn` (added in Task 3)
- Produces:
  - `FH_MODULES` — array, used by `initCommandPalette()`
  - `initCommandPalette()` — call once in `DOMContentLoaded`
  - `skeletonRows(cols, count?)` → `string` (HTML) — call before API fetch in Tasks 4–5
  - `makeSortable(tableId)` — call after tbody is populated in Tasks 4–5

- [ ] **Step 1: Add FH_MODULES + helper constants at top of `app.js` (before `apiFetch`)**

Insert at line 1 (before all existing code):

```javascript
/* ── Module registry ──────────────────────────────────── */
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
const FH_RECENT_KEY = 'fh_recent_modules';

function _fhGetRecent() {
  try { return JSON.parse(localStorage.getItem(FH_RECENT_KEY) || '[]'); } catch (e) { return []; }
}
function _fhRecordVisit(url) {
  if (!url) return;
  var recent = _fhGetRecent().filter(function(u) { return u !== url; });
  recent.unshift(url);
  localStorage.setItem(FH_RECENT_KEY, JSON.stringify(recent.slice(0, 5)));
}

```

- [ ] **Step 2: Add `initCommandPalette()` after `_fhRecordVisit` (before `apiFetch`)**

```javascript
function initCommandPalette() {
  /* Record current page in recently-visited */
  var currentMod = FH_MODULES.find(function(m) {
    return m.active && m.url && window.location.pathname.replace(/\/$/, '') === m.url.replace(/\/$/, '');
  });
  if (currentMod) _fhRecordVisit(currentMod.url);

  var ov      = document.getElementById('fh-cmd-ov');
  var input   = document.getElementById('fh-cmd-input');
  var results = document.getElementById('fh-cmd-results');
  var btn     = document.getElementById('fh-cmd-btn');
  if (!ov || !input || !results) return;

  var activeIdx = 0;

  function open() {
    ov.classList.add('open');
    input.value = '';
    render('');
    input.focus();
  }
  function close() {
    ov.classList.remove('open');
  }

  function render(query) {
    results.innerHTML = '';
    query = query.trim().toLowerCase();
    var allItems = [];

    if (!query) {
      var recentUrls  = _fhGetRecent().slice(0, 3);
      var recentMods  = recentUrls.map(function(u) {
        return FH_MODULES.find(function(m) { return m.url === u; });
      }).filter(Boolean);

      if (recentMods.length) {
        results.appendChild(_section('TERAKHIR DIKUNJUNGI'));
        recentMods.forEach(function(m) {
          var el = _item(m);
          results.appendChild(el);
          if (m.active) allItems.push(el);
        });
      }
      results.appendChild(_section('SEMUA MODUL'));
      var active   = FH_MODULES.filter(function(m) { return m.active; });
      var inactive = FH_MODULES.filter(function(m) { return !m.active; });
      active.forEach(function(m) {
        var el = _item(m);
        results.appendChild(el);
        allItems.push(el);
      });
      if (inactive.length) {
        var sep = document.createElement('div');
        sep.className = 'fh-cmd-sep';
        results.appendChild(sep);
        inactive.forEach(function(m) { results.appendChild(_item(m)); });
      }
    } else {
      var matched = FH_MODULES.filter(function(m) {
        return m.name.toLowerCase().indexOf(query) !== -1;
      });
      if (!matched.length) {
        var empty = document.createElement('div');
        empty.className = 'fh-cmd-empty';
        empty.textContent = 'Tidak ada modul ditemukan.';
        results.appendChild(empty);
      } else {
        results.appendChild(_section('HASIL PENCARIAN'));
        matched.forEach(function(m) {
          var el = _item(m);
          results.appendChild(el);
          if (m.active) allItems.push(el);
        });
      }
    }
    setActive(0, allItems);
  }

  function _section(label) {
    var el = document.createElement('div');
    el.className = 'fh-cmd-section';
    el.textContent = label;
    return el;
  }

  function _item(mod) {
    var el = document.createElement('div');
    el.className = 'fh-cmd-item' + (mod.active ? '' : ' disabled');
    el.innerHTML = '<span>' + mod.name + '</span>' +
      (!mod.active ? '<span class="fh-cmd-badge">Coming Soon</span>' : '');
    if (mod.active && mod.url) {
      el.addEventListener('click', function() {
        _fhRecordVisit(mod.url);
        close();
        window.location.href = mod.url;
      });
    }
    return el;
  }

  function getActiveEls() {
    return Array.from(results.querySelectorAll('.fh-cmd-item:not(.disabled)'));
  }

  function setActive(idx, items) {
    items = items || getActiveEls();
    if (!items.length) return;
    activeIdx = Math.max(0, Math.min(idx, items.length - 1));
    items.forEach(function(el, i) { el.classList.toggle('active', i === activeIdx); });
    var active = items[activeIdx];
    if (active) active.scrollIntoView({ block: 'nearest' });
  }

  input.addEventListener('input', function() { render(input.value); });

  document.addEventListener('keydown', function(e) {
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
      e.preventDefault();
      ov.classList.contains('open') ? close() : open();
      return;
    }
    if (!ov.classList.contains('open')) return;
    if (e.key === 'Escape')    { e.preventDefault(); close(); }
    if (e.key === 'ArrowDown') { e.preventDefault(); setActive(activeIdx + 1); }
    if (e.key === 'ArrowUp')   { e.preventDefault(); setActive(activeIdx - 1); }
    if (e.key === 'Enter') {
      e.preventDefault();
      var items = getActiveEls();
      if (items[activeIdx]) items[activeIdx].click();
    }
  });

  ov.addEventListener('click', function(e) { if (e.target === ov) close(); });
  if (btn) btn.addEventListener('click', open);
}

```

- [ ] **Step 3: Add `skeletonRows()` and `makeSortable()` after `initCommandPalette()`**

```javascript
/* ── Skeleton loading ──────────────────────────────────── */
function skeletonRows(cols, count) {
  count = count || 6;
  return Array(count).fill(0).map(function() {
    return '<tr class="fh-skel-row">' +
      Array(cols).fill(0).map(function(_, i) {
        return '<td><div class="fh-skel" style="width:' + (55 + (i * 17) % 35) + '%"></div></td>';
      }).join('') +
      '</tr>';
  }).join('');
}

/* ── Sortable columns (DOM-based) ──────────────────────── */
function makeSortable(tableId) {
  var table = document.getElementById(tableId);
  if (!table || table.dataset.sortable) return;
  table.dataset.sortable = '1';

  var sortCol = -1, sortAsc = true;

  table.querySelectorAll('thead th[data-sort]').forEach(function(th) {
    var colIdx = parseInt(th.dataset.sort, 10);
    var isNum  = th.dataset.sortType === 'num';
    th.style.cursor = 'pointer';
    th.addEventListener('click', function() {
      if (sortCol === colIdx) { sortAsc = !sortAsc; } else { sortCol = colIdx; sortAsc = true; }
      table.querySelectorAll('thead th[data-sort]').forEach(function(h) {
        h.dataset.sortDir = parseInt(h.dataset.sort, 10) === sortCol
          ? (sortAsc ? 'asc' : 'desc') : '';
      });
      var tbody = table.querySelector('tbody');
      var rows  = Array.from(tbody.querySelectorAll('tr:not(.fh-skel-row):not(.pam-detail-row)'));
      rows.sort(function(a, b) {
        var va = (a.cells[colIdx] ? a.cells[colIdx].textContent : '').trim();
        var vb = (b.cells[colIdx] ? b.cells[colIdx].textContent : '').trim();
        var na = isNum ? (parseFloat(va.replace(/[.,\s]/g,'')) || 0) : va.toLowerCase();
        var nb = isNum ? (parseFloat(vb.replace(/[.,\s]/g,'')) || 0) : vb.toLowerCase();
        return sortAsc ? (na > nb ? 1 : -1) : (na < nb ? 1 : -1);
      });
      rows.forEach(function(r) { tbody.appendChild(r); });
    });
  });
}

```

- [ ] **Step 4: Call `initCommandPalette()` in the existing `DOMContentLoaded` handler**

In `app.js`, the `DOMContentLoaded` handler is at the bottom of the file (currently line 146). Add one line at the start of the handler body:

```javascript
document.addEventListener("DOMContentLoaded", () => {
  initCommandPalette();              // ← add this line
  document.querySelectorAll("[data-tabs]").forEach(initTabs);
  document.querySelectorAll(".modal-overlay").forEach(overlay => {
    overlay.addEventListener("click", e => { if (e.target === overlay) overlay.classList.remove("open"); });
  });
  document.querySelectorAll("tbody").forEach(staggerRows);
  document.querySelectorAll(".stat-value[data-count]").forEach(el => animateCounter(el));
});
```

- [ ] **Step 5: Verify in browser console**

Open browser DevTools console. Run:

```javascript
console.log(typeof initCommandPalette, typeof skeletonRows, typeof makeSortable, FH_MODULES.length);
```

Expected output: `function function function 11`

- [ ] **Step 6: Commit**

```bash
git add app/static/js/app.js
git commit -m "feat: add FH_MODULES registry, initCommandPalette, skeletonRows, makeSortable helpers"
```

---

## Task 3: base.html — Navbar restructure

**Files:**
- Modify: `app/templates/base.html`

**Interfaces:**
- Consumes: `.fh-cmd-btn`, `#fh-cmd-ov` CSS (Task 1); `initCommandPalette()` (Task 2)
- Produces: `<body data-module="">` used by `initCommandPalette()` for visit tracking; `#fh-cmd-btn` and `#fh-cmd-ov` required by Task 2 JS

- [ ] **Step 1: Add `data-module` attribute to `<body>` tag**

Change line 16 from:
```html
<body>
```
to:
```html
<body data-module="{{ active_page or '' }}">
```

- [ ] **Step 2: Remove the `<nav class="navbar-links">` block (lines 33–53)**

Remove this entire block:
```html
  {% if company_name %}
  <span class="navbar-sep" style="margin:0 .25rem">|</span>
  {% set co = company_code or '' %}
  <nav class="navbar-links">
    <a href="/dashboard" class="navbar-link {% if active_page == 'dashboard' %}active{% endif %}">Dashboard</a>
    {% if co == 'ETF' %}
    <a href="/beasiswa" class="navbar-link {% if active_page == 'beasiswa' %}active{% endif %}">Beasiswa</a>
    {% endif %}
    <a href="/payment-memo" class="navbar-link {% if active_page == 'payment_memo' %}active{% endif %}">Payment Approval Memo</a>
    {% if co == 'ETF' %}
    <a href="/etf-payment-application" class="navbar-link {% if active_page == 'etf_payment_app' %}active{% endif %}">Payment Application</a>
    {% else %}
    <a href="/payment-application" class="navbar-link {% if active_page == 'payment_app' %}active{% endif %}">Payment Application</a>
    {% endif %}
    <span class="navbar-sep" style="margin:0 .125rem">|</span>
    <a class="navbar-link coming-soon" title="Coming Soon">Bank</a>
    <a class="navbar-link coming-soon" title="Coming Soon">Account Payable</a>
    <a class="navbar-link coming-soon" title="Coming Soon">Advance</a>
    <a class="navbar-link coming-soon" title="Coming Soon">Petty Cash</a>
    <a class="navbar-link coming-soon" title="Coming Soon">Sponsorship</a>
    <a href="/budget/" class="navbar-link {% if active_page == 'budget' %}active{% endif %}">Budget</a>
    <span class="navbar-sep" style="margin:0 .125rem">|</span>
    <a href="/users" class="navbar-link {% if active_page == 'users' %}active{% endif %}">Users</a>
  </nav>
  {% endif %}
```

- [ ] **Step 3: Add `#fh-cmd-btn` in place of the removed block**

After the `{% if company_name %}...navbar-company...{% endif %}` block (after the closing `{% endif %}` of the company name display, i.e. after line 29 in the original), add:

```html
  {% if company_name %}
  <button id="fh-cmd-btn" class="fh-cmd-btn" title="Cari modul (Ctrl+K)">
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
    Cari modul
    <kbd>Ctrl+K</kbd>
  </button>
  {% endif %}
```

The resulting navbar section (between company link and `<span class="navbar-user">`) must look like this in final form:

```html
<nav class="navbar">
  <a class="navbar-brand" href="/">
    <span class="navbar-brand-icon">...</span>
    Finance Hub
  </a>
  {% if company_name %}
  <span class="navbar-sep">/</span>
  <a class="navbar-company" href="/select-company" ...>{{ company_name }}</a>
  {% endif %}
  {% if company_name %}
  <button id="fh-cmd-btn" class="fh-cmd-btn" title="Cari modul (Ctrl+K)">
    <svg ...></svg>
    Cari modul
    <kbd>Ctrl+K</kbd>
  </button>
  {% endif %}
  <span class="navbar-user">...</span>
  <button class="btn-theme-toggle" ...>...</button>
  <button class="btn-logout" ...>Keluar</button>
</nav>
```

Note: The `.fh-cmd-btn` has `margin-left: auto` in its CSS (Task 1), so it pushes to the right side automatically. The `<span class="navbar-user">` after it does NOT have `margin-left: auto` anymore — remove the existing `margin-left: auto` from `.navbar-user` in style.css if it would conflict. (The `.navbar-user` definition at CSS line 115 has `margin-left: auto` — change it to `margin-left: 0` now that `.fh-cmd-btn` has `margin-left: auto`.)

Update `style.css` `.navbar-user`:
```css
.navbar-user {
  /* margin-left: auto; ← removed; .fh-cmd-btn now owns margin-left:auto */
  display: flex; align-items: center; gap: .375rem;
  font-size: .8rem; color: var(--sl-600); font-weight: 500;
}
```

- [ ] **Step 4: Add `#fh-cmd-ov` overlay HTML before `</body>`**

Add before `{% block scripts %}{% endblock %}` (which is at line 152, just before `</body>`):

```html
<!-- ── Command Palette Overlay ─────────────────────────── -->
<div id="fh-cmd-ov">
  <div class="fh-cmd-modal">
    <div class="fh-cmd-header">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
      <input id="fh-cmd-input" type="text" placeholder="Cari modul..." autocomplete="off" spellcheck="false">
      <kbd>Esc</kbd>
    </div>
    <div id="fh-cmd-results"></div>
  </div>
</div>
```

- [ ] **Step 5: Verify command palette in browser**

Refresh `http://localhost:5000/payment-memo`. Confirm:
1. Navbar is clean — `[FH] Finance Hub / Eka Tjipta Foundation   [🔍 Cari modul Ctrl+K]   ☀ admin → Keluar`
2. Press `Ctrl+K` → palette opens with "TERAKHIR DIKUNJUNGI" and "SEMUA MODUL" sections
3. Type "pay" → filters to Payment Approval Memo, Payment Application, Account Payable (Coming Soon)
4. Arrow keys move highlight, Enter navigates
5. Esc closes
6. Coming Soon items appear grayed-out, clicking does nothing

- [ ] **Step 6: Commit**

```bash
git add app/templates/base.html app/static/css/style.css
git commit -m "feat: replace navbar-links with Ctrl+K command palette"
```

---

## Task 4: payment_memo/index.html — h1 cleanup, skeleton, sort, filter-bar

**Files:**
- Modify: `app/templates/payment_memo/index.html`

**Interfaces:**
- Consumes: `skeletonRows()` (Task 2), `makeSortable()` (Task 2), `.filter-bar` CSS (Task 1)

**Context:** Four pillar tabs each have a filter div and a table with a `<tbody>` populated by an async JS function (`loadPAM`, `loadFIORI`, `loadSML`, `loadSETF`). The `loadXxx()` functions are at the bottom of the `{% block scripts %}` in the template (around line 2000+).

Column indices (0-based) for sortable columns per table:
- **AGRI** (`#pam-table`): Tgl PAM = col 2, Total (Rp) = col 11, Due Date = col 12
- **FIORI/APP** (no id — add `id="fiori-table"`): Tgl PAM = col 2, Total (Rp) = col 11, Due Date = col 12
- **SML/LAND** (no id — add `id="sml-table"`): Tgl PAM = col 1, Total (Rp) = col 10, Due Date = col 11
- **SETF** (no id — add `id="setf-table"`): Tgl PAM = col 1, Total (Rp) = col 10, Due Date = col 11

- [ ] **Step 1: Strip `-- {{ company_name }}` from the page h1**

Line 119 currently reads:
```html
  <h1 style="font-size:1.25rem; font-weight:700">Payment Approval Memo -- {{ company_name }}</h1>
```

Change to:
```html
  <h1 style="font-size:1.25rem; font-weight:700">Payment Approval Memo</h1>
```

- [ ] **Step 2: Add `.filter-bar` class to the 4 filter wrapper divs**

Each pillar tab has a filter div as its first child. Add `class="filter-bar"` to each:

**AGRI tab** — line 367:
```html
<!-- BEFORE -->
<div style="display:flex;align-items:center;gap:6px;margin-bottom:10px;flex-wrap:wrap">
<!-- AFTER -->
<div class="filter-bar" style="display:flex;align-items:center;gap:6px;margin-bottom:10px;flex-wrap:wrap;padding-top:.5rem">
```

**APP/FIORI tab** — around line 469:
```html
<!-- BEFORE -->
<div style="display:flex;align-items:center;gap:6px;margin-bottom:10px;flex-wrap:wrap">
  <input id="fiori-search" ...>
<!-- AFTER -->
<div class="filter-bar" style="display:flex;align-items:center;gap:6px;margin-bottom:10px;flex-wrap:wrap;padding-top:.5rem">
  <input id="fiori-search" ...>
```

**SML/LAND tab** — around line 573:
```html
<!-- BEFORE -->
<div style="display:flex;align-items:center;gap:6px;margin-bottom:10px;flex-wrap:wrap">
  <input id="sml-search" ...>
<!-- AFTER -->
<div class="filter-bar" style="display:flex;align-items:center;gap:6px;margin-bottom:10px;flex-wrap:wrap;padding-top:.5rem">
  <input id="sml-search" ...>
```

**SETF tab** — around line 655:
```html
<!-- BEFORE -->
<div style="display:flex;align-items:center;gap:6px;margin-bottom:10px;flex-wrap:wrap">
  <input id="setf-search" ...>
<!-- AFTER -->
<div class="filter-bar" style="display:flex;align-items:center;gap:6px;margin-bottom:10px;flex-wrap:wrap;padding-top:.5rem">
  <input id="setf-search" ...>
```

- [ ] **Step 3: Add `data-sort` to AGRI table (`#pam-table`) th elements**

File: around line 433 (the `<thead>` of `#pam-table`).

Change these three `<th>` elements:

```html
<!-- BEFORE -->
<th class="s2" style="padding:8px 10px;text-align:left;white-space:nowrap">Tgl PAM</th>
<!-- AFTER -->
<th class="s2" style="padding:8px 10px;text-align:left;white-space:nowrap" data-sort="2">Tgl PAM</th>
```

```html
<!-- BEFORE -->
<th style="padding:8px 10px;text-align:right;white-space:nowrap">Total (Rp)</th>
<!-- AFTER -->
<th style="padding:8px 10px;text-align:right;white-space:nowrap" data-sort="11" data-sort-type="num">Total (Rp)</th>
```

```html
<!-- BEFORE -->
<th style="padding:8px 10px;text-align:left;white-space:nowrap">Due Date</th>
<!-- AFTER -->
<th style="padding:8px 10px;text-align:left;white-space:nowrap" data-sort="12">Due Date</th>
```

- [ ] **Step 4: Add `id` + `data-sort` to FIORI table**

The FIORI table (around line 536) has no id. Add it:
```html
<!-- BEFORE -->
<table style="width:100%;border-collapse:collapse;font-size:12px;">
<!-- AFTER -->
<table id="fiori-table" style="width:100%;border-collapse:collapse;font-size:12px;">
```

Then add `data-sort` to FIORI thead `<th>` elements (same col indices as AGRI: 2, 11, 12):

```html
<!-- col 2 -->
<th style="padding:7px 8px;white-space:nowrap" data-sort="2">Tgl PAM</th>
<!-- col 11 -->
<th style="padding:7px 8px;text-align:right;white-space:nowrap" data-sort="11" data-sort-type="num">Total (Rp)</th>
<!-- col 12 -->
<th style="padding:7px 8px;white-space:nowrap" data-sort="12">Due Date</th>
```

- [ ] **Step 5: Add `id` + `data-sort` to SML table**

The SML table (around line 617) has no id. Add it:
```html
<!-- BEFORE -->
<table style="width:100%;border-collapse:collapse;font-size:12px;">
  <thead class="thead-primary">
    <tr>
      <th style="padding:7px 8px;white-space:nowrap">PAM No</th>
      <th style="padding:7px 8px;white-space:nowrap">Tgl PAM</th>
<!-- AFTER -->
<table id="sml-table" style="width:100%;border-collapse:collapse;font-size:12px;">
  <thead class="thead-primary">
    <tr>
      <th style="padding:7px 8px;white-space:nowrap">PAM No</th>
      <th style="padding:7px 8px;white-space:nowrap" data-sort="1">Tgl PAM</th>
```

Add `data-sort` to SML thead (col 1 = Tgl PAM, col 10 = Total (Rp), col 11 = Due Date):

```html
<th style="padding:7px 8px;white-space:nowrap" data-sort="1">Tgl PAM</th>
<th style="padding:7px 8px;text-align:right;white-space:nowrap" data-sort="10" data-sort-type="num">Total (Rp)</th>
<th style="padding:7px 8px;white-space:nowrap" data-sort="11">Due Date</th>
```

- [ ] **Step 6: Add `id` + `data-sort` to SETF table**

The SETF table (around line 697) has no id. Add it and `data-sort` (same indices as SML — col 1, 10, 11):

```html
<table id="setf-table" style="width:100%;border-collapse:collapse;font-size:12px;">
  <thead class="thead-primary">
    <tr>
      <th style="padding:7px 8px;white-space:nowrap">PAM No</th>
      <th style="padding:7px 8px;white-space:nowrap" data-sort="1">Tgl PAM</th>
      ...
      <th style="padding:7px 8px;text-align:right;white-space:nowrap" data-sort="10" data-sort-type="num">Total (Rp)</th>
      <th style="padding:7px 8px;white-space:nowrap" data-sort="11">Due Date</th>
```

- [ ] **Step 7: Add skeleton + makeSortable to `loadPAM()` (AGRI)**

Find `loadPAM()` (around line 2068). Add skeleton before the fetch and `makeSortable` after render:

```javascript
async function loadPAM() {
  await loadCOA();
  const search  = (document.getElementById('pam-search')?.value || '').trim();
  const bulan   = (document.getElementById('pam-filter-bulan')?.value || '');
  const tahun   = (document.getElementById('pam-filter-tahun')?.value || '');
  const status  = (document.getElementById('pam-filter-status')?.value || '');
  const source  = (document.getElementById('pam-filter-source')?.value || '');
  const params  = new URLSearchParams({ search, bulan, tahun, status, source });

  // ← ADD skeleton before fetch
  const tbody  = document.getElementById('pam-tbody');
  tbody.innerHTML = skeletonRows(28);

  const res     = await apiFetch('/payment-memo/by-pillar/AGRI?' + params);
  if (!res) return;
  const data   = await res.json();
  if (!data.ok || !data.rows.length) {
    tbody.innerHTML = '<tr><td colspan="28" style="text-align:center;padding:20px;color:var(--text-muted);">Belum ada PAM record AGRI.</td></tr>';
    return;
  }
  // ... existing render code unchanged ...
  tbody.innerHTML = data.rows.map((r, i) => `...`).join('');
  // ← ADD at end of successful render:
  makeSortable('pam-table');
}
```

The exact change is two insertions:
1. After `const params = new URLSearchParams(...)` and before `const res = await apiFetch(...)`:
   ```javascript
   const tbody  = document.getElementById('pam-tbody');
   tbody.innerHTML = skeletonRows(28);
   ```
   (Note: remove the existing `const tbody = ...` line that appears after the fetch, since we now declare it before)

2. After `tbody.innerHTML = data.rows.map(...).join('');` (the successful render line):
   ```javascript
   makeSortable('pam-table');
   ```

- [ ] **Step 8: Add skeleton + makeSortable to `loadFIORI()` (APP)**

Find `loadFIORI()` (search for `async function loadFIORI`). Apply same pattern:

1. After `const params = new URLSearchParams(...)`, before the `apiFetch` call:
   ```javascript
   const tbody  = document.getElementById('fiori-tbody');
   tbody.innerHTML = skeletonRows(26);
   ```

2. After the main `tbody.innerHTML = data.rows.map(...).join('');` render line:
   ```javascript
   makeSortable('fiori-table');
   ```

- [ ] **Step 9: Add skeleton + makeSortable to `loadSML()` (LAND)**

Find `loadSML()` (around line 1390). Currently at line 1400: `const tbody = document.getElementById('sml-tbody')`. Move this before the fetch and add skeleton:

The existing code is:
```javascript
async function loadSML() {
  const search  = ...
  const params  = new URLSearchParams({ search, bulan, tahun, status, source });
  const res     = await apiFetch('/payment-memo/by-pillar/LAND?' + params);
  if (!res) return;
  const data   = await res.json();
  const tbody  = document.getElementById('sml-tbody');   // ← move this up
  const count  = document.getElementById('sml-count');
```

Change to:
```javascript
async function loadSML() {
  const search  = ...
  const params  = new URLSearchParams({ search, bulan, tahun, status, source });
  const tbody  = document.getElementById('sml-tbody');   // ← moved before fetch
  tbody.innerHTML = skeletonRows(25);                    // ← skeleton
  const res     = await apiFetch('/payment-memo/by-pillar/LAND?' + params);
  if (!res) return;
  const data   = await res.json();
  const count  = document.getElementById('sml-count');
```

After the main `tbody.innerHTML = ...` render line (the successful one), add:
```javascript
makeSortable('sml-table');
```

- [ ] **Step 10: Add skeleton + makeSortable to `loadSETF()` (SETF)**

Find `loadSETF()` (search for `async function loadSETF`). Apply same pattern as SML:
1. Move `const tbody = document.getElementById('setf-tbody')` before the fetch
2. Add `tbody.innerHTML = skeletonRows(25)` after the tbody declaration
3. Add `makeSortable('setf-table')` after the render line

- [ ] **Step 11: Verify in browser**

Navigate to `/payment-memo` → click AGRI tab:
1. Shimmer skeleton appears briefly while data loads
2. Data rows render as normal
3. "Tgl PAM" header shows `⇅` indicator — click it → rows sort ascending, `▲` appears
4. Click again → sorts descending, `▼` appears
5. Click "Total (Rp)" → sorts numerically
6. Filter bar (search inputs + dropdowns) sticks to top of viewport when scrolling down the table
7. `h1` reads "Payment Approval Memo" (no `-- Eka Tjipta Foundation`)

- [ ] **Step 12: Commit**

```bash
git add app/templates/payment_memo/index.html
git commit -m "feat: skeleton loading, sortable cols, sticky filter bars in Payment Memo"
```

---

## Task 5: beasiswa + etf_payment_application — skeleton, filter-bar, sort

**Files:**
- Modify: `app/templates/beasiswa/index.html`
- Modify: `app/templates/etf_payment_application/index.html`

**Interfaces:**
- Consumes: `skeletonRows()` (Task 2), `makeSortable()` (Task 2), `.filter-bar` CSS (Task 1)

### Part A: beasiswa/index.html

**Context:** `loadPaymentList()` at line 1171 already sets `tbody.innerHTML = '<tr><td colspan="12"...>Memuat...</td></tr>'`. Replace with `skeletonRows(12)`. The `#pay-table` has 12 columns. The payment filter is inside `.card` at line 284; add `.filter-bar` class to the filter flex-div.

- [ ] **Step 1: Replace loading text with skeleton in `loadPaymentList()`**

Find (around line 1183):
```javascript
    tbody.innerHTML = `<tr><td colspan="12" style="text-align:center;color:var(--text-muted)">Memuat...</td></tr>`;
```

Replace with:
```javascript
    tbody.innerHTML = skeletonRows(12);
```

- [ ] **Step 2: Add `data-sort` to `#pay-table` `<th>` elements**

The `#pay-table` header (line 343) currently reads:
```html
<thead>
  <tr>
    <th>Kode</th><th>Nama Siswa</th><th>Program</th><th>Kategori 1</th><th>Kategori 2</th>
    <th>Tanggal</th><th>Pillar</th><th class="num-right">Amount</th>
    <th>PAM</th><th>Perusahaan</th><th>Status</th><th>Aksi</th>
  </tr>
</thead>
```

Change to (col 5 = Tanggal, col 7 = Amount):
```html
<thead>
  <tr>
    <th>Kode</th><th>Nama Siswa</th><th>Program</th><th>Kategori 1</th><th>Kategori 2</th>
    <th data-sort="5">Tanggal</th><th>Pillar</th><th class="num-right" data-sort="7" data-sort-type="num">Amount</th>
    <th>PAM</th><th>Perusahaan</th><th>Status</th><th>Aksi</th>
  </tr>
</thead>
```

- [ ] **Step 3: Add `makeSortable` call after `loadPaymentList` renders rows**

In `loadPaymentList()`, after the `tbody.innerHTML = ...` render code (the successful render at the bottom of the setTimeout), add:
```javascript
    makeSortable('pay-table');
```

- [ ] **Step 4: Add `.filter-bar` class to payment filter div in beasiswa**

Find line 284 (the filter row inside `.card` above the payment table):
```html
      <div style="display:flex;gap:.5rem;margin-bottom:.75rem;flex-wrap:wrap;align-items:flex-end">
        <div class="form-group" style="margin:0;flex:1;min-width:200px">
          <label>Cari / Kata Kunci</label>
```

Change to:
```html
      <div class="filter-bar" style="display:flex;gap:.5rem;margin-bottom:.75rem;flex-wrap:wrap;align-items:flex-end;padding-top:.25rem">
        <div class="form-group" style="margin:0;flex:1;min-width:200px">
          <label>Cari / Kata Kunci</label>
```

### Part B: etf_payment_application/index.html

**Context:** The `#pa-table` is server-rendered (Jinja `{% for r in pa_rows %}`). `makeSortable` is called once in DOMContentLoaded — not inside a loadXxx function. Add `data-sort` to 3 columns and call `makeSortable('pa-table')` in this template's `{% block scripts %}`.

Column indices in `#pa-table` (0-based):
- col 1 (s1): No. PA → `data-sort="1"`
- col 13: Tgl PA → `data-sort="13"`
- col 19: Jumlah (Rp) → `data-sort="19" data-sort-type="num"`

- [ ] **Step 5: Add `data-sort` to `#pa-table` `<th>` elements**

Line 418: `<th class="s1">No. PA</th>` → `<th class="s1" data-sort="1">No. PA</th>`

Line 433: `<th>Tgl PA</th>` → `<th data-sort="13">Tgl PA</th>`

Line 439: `<th class="num-right">Jumlah (Rp)</th>` → `<th class="num-right" data-sort="19" data-sort-type="num">Jumlah (Rp)</th>`

- [ ] **Step 6: Call `makeSortable('pa-table')` in this template's scripts block**

At the bottom of `etf_payment_application/index.html`, in `{% block scripts %}`, add before `</script>`:

```javascript
// Sort is DOM-based; call once after server-rendered rows are in the DOM
document.addEventListener('DOMContentLoaded', function() {
  makeSortable('pa-table');
});
```

- [ ] **Step 7: Verify in browser**

1. Navigate to `/beasiswa` → click "Data Payment" tab
   - Shimmer skeleton appears while fetch runs
   - "Tanggal" and "Amount" columns show `⇅` indicator
   - Clicking sorts correctly; amount sorts numerically (ignoring commas)

2. Navigate to `/etf-payment-application`
   - "No. PA", "Tgl PA", "Jumlah" headers show `⇅` indicator
   - Clicking sorts the existing server-rendered rows

3. Sticky filter bar in beasiswa: scroll down the data payment list — filter stays visible at top

- [ ] **Step 8: Commit**

```bash
git add app/templates/beasiswa/index.html app/templates/etf_payment_application/index.html
git commit -m "feat: skeleton + sortable columns in Beasiswa and ETF PA"
```

---

## Self-Review Checklist

### Spec Coverage

| Spec Section | Task |
|---|---|
| Section 1: Navbar layout change (remove links, add cmd-btn) | T3 |
| Section 2: Command palette UX (search, keyboard, sections) | T2 + T3 |
| Section 3: FH_MODULES registry | T2 |
| Section 4: Recently visited tracking | T2 |
| Section 5: Page title cleanup | T4 Step 1 |
| Section 6: Skeleton loading (PAM, FIORI, SML, SETF, Beasiswa) | T4 Steps 7–10, T5 Step 1 |
| Section 7: Sortable columns | T4 Steps 3–6, T5 Steps 2–3, 5–6 |
| Section 8: Sticky filter bar | T1 Step 2 (CSS), T4 Step 2, T5 Step 4 |

### Placeholder Scan
- No TBDs or TODOs remain
- All code shown in full; column indices are exact integers verified from file reads
- All function names are consistent: `initCommandPalette`, `skeletonRows`, `makeSortable`, `_fhRecordVisit`, `_fhGetRecent`

### Type Consistency
- `skeletonRows(cols, count?)` → `string` — consumed by `tbody.innerHTML = skeletonRows(N)`
- `makeSortable(tableId: string)` — takes table element id, guards against re-init with `table.dataset.sortable`
- `_fhRecordVisit(url: string)` / `_fhGetRecent()` → `string[]` — used inside `initCommandPalette()`

---

## Files Changed Summary

| File | Task |
|---|---|
| `app/static/css/style.css` | T1, T3 (navbar-user margin fix) |
| `app/static/js/app.js` | T2 |
| `app/templates/base.html` | T3 |
| `app/templates/payment_memo/index.html` | T4 |
| `app/templates/beasiswa/index.html` | T5-A |
| `app/templates/etf_payment_application/index.html` | T5-B |
