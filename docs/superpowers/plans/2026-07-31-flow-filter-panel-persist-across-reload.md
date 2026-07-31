# FLOW Filter Panel Persist-Across-Reload Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the collapsible filter panel's open/closed state survive a same-tab `location.reload()` (triggered by ~12 save actions across Beasiswa/Payment Memo/Payment Application), while still closing correctly on `Esc` and on tab switch, per `docs/superpowers/specs/2026-07-31-flow-filter-panel-persist-across-reload-design.md`.

**Architecture:** Add three small helper functions to `app/static/js/app.js` that read/write a `sessionStorage` entry keyed by each filter panel's existing stable `id`. Wire a write-on-open call into the existing `F` keydown handler, a write-on-close call into both existing close paths (`Esc` handler, tab-switch force-close loop), and a restore call into `DOMContentLoaded` — placed *after* `initTabs()` runs, since `initTabs()`'s own auto-activation click synchronously force-closes filter panels as a side effect and would otherwise immediately undo an earlier restore.

**Tech Stack:** Vanilla JS (`app/static/js/app.js`), `sessionStorage` Web API. No new dependencies, no template or backend changes.

## Global Constraints

- Presentation-layer only — no business logic, route, or template changes (spec "What does not change").
- `Esc` and `F` keyboard behavior must remain functionally identical to today, just with a persistence side effect added (spec "What does not change").
- Tab-switch force-closing filter panels must remain unchanged (spec "What does not change").
- Scope is Beasiswa, Payment Memo, and Payment Application only — no other module has a collapsible filter panel to persist (spec "Out of Scope").
- No visible Filter/Full Screen button or badge is being reintroduced (spec "What does not change").

---

### Task 1: Persist filter panel open state via sessionStorage

**Files:**
- Modify: `app/static/js/app.js:472` (tab-switch force-close loop, inside `initTabs()`)
- Modify: `app/static/js/app.js:555-562` (add 3 new functions after `getActiveFilterPanel()`)
- Modify: `app/static/js/app.js:603-610` (`Esc` handler)
- Modify: `app/static/js/app.js:621-631` (`F` handler)
- Modify: `app/static/js/app.js:634-639` (`DOMContentLoaded` listener)

**Interfaces:**
- Consumes: `getActiveFilterPanel()` (existing, `app/static/js/app.js:555`) — returns the currently-relevant `.filter-bar.collapsible` element or `null`.
- Produces: `persistFilterOpen(panel)`, `persistFilterClosed(panel)`, `restoreFilterOpenState()` — no other task/file depends on these; this is a single self-contained change.

Before editing, confirm the file hasn't drifted further since this plan was written (this repo has concurrent sessions actively committing):

- [ ] **Step 1: Confirm current line content matches this plan**

Run: `grep -n "container.querySelectorAll(\".filter-bar.collapsible.open\")\|function getActiveFilterPanel\|document.addEventListener('keydown'\|document.addEventListener(\"DOMContentLoaded\"" app/static/js/app.js`

Expected output (line numbers may drift by a few lines from concurrent commits, but all four patterns must be present and in this relative order — if `getActiveFilterPanel` or the `Esc`/`F` keydown block is missing entirely, STOP and re-derive current line numbers before proceeding, don't guess):

```
472:      container.querySelectorAll(".filter-bar.collapsible.open").forEach(p => p.classList.remove("open"));
555:function getActiveFilterPanel() {
599:document.addEventListener('keydown', e => {
634:document.addEventListener("DOMContentLoaded", () => {
```

- [ ] **Step 2: Add the three persistence helper functions**

Insert immediately after `getActiveFilterPanel()`'s closing brace (after line 562, before the `// Steps the active .tab-btn...` comment on line 564):

```javascript

// sessionStorage-backed persistence for filter panel open/closed state.
// Keyed by the panel's own stable, hand-written id (bsw-filter-siswa,
// pam-filter-pam, pa-filter-panel, etc — no page-identity prefix needed:
// panel ids don't collide across modules, and a stale entry from a panel
// that doesn't exist on the current page is simply never read, since
// restoreFilterOpenState() only ever looks up getActiveFilterPanel()'s
// result). Scoped to sessionStorage (not localStorage) since this is
// transient UI state that should not resurrect in a fresh session days
// later — see docs/superpowers/specs/2026-07-31-flow-filter-panel-persist-across-reload-design.md
function _filterOpenKey(panel) {
  return 'fh-filter-open:' + panel.id;
}
function persistFilterOpen(panel) {
  if (panel && panel.id) sessionStorage.setItem(_filterOpenKey(panel), '1');
}
function persistFilterClosed(panel) {
  if (panel && panel.id) sessionStorage.removeItem(_filterOpenKey(panel));
}
// Called after initTabs() (and its internal auto-activation click, which
// force-closes filter panels as a side effect on every load) has already
// run — restoring before that point would be immediately undone.
function restoreFilterOpenState() {
  const panel = getActiveFilterPanel();
  if (panel && panel.id && sessionStorage.getItem(_filterOpenKey(panel)) === '1') {
    panel.classList.add('open');
  }
}
```

- [ ] **Step 3: Persist on tab-switch close**

Replace (current line 472):

```javascript
      container.querySelectorAll(".filter-bar.collapsible.open").forEach(p => p.classList.remove("open"));
```

with:

```javascript
      container.querySelectorAll(".filter-bar.collapsible.open").forEach(p => {
        p.classList.remove("open");
        persistFilterClosed(p);
      });
```

- [ ] **Step 4: Persist on Esc close**

Replace (current lines 603-610):

```javascript
  if (e.key === 'Escape') {
    const panel = getActiveFilterPanel();
    if (panel && panel.classList.contains('open')) {
      panel.classList.remove('open');
      if (typing) el.blur(); // Also blur the search input if focused
      return;
    }
  }
```

with:

```javascript
  if (e.key === 'Escape') {
    const panel = getActiveFilterPanel();
    if (panel && panel.classList.contains('open')) {
      panel.classList.remove('open');
      persistFilterClosed(panel);
      if (typing) el.blur(); // Also blur the search input if focused
      return;
    }
  }
```

- [ ] **Step 5: Persist on F open**

Replace (current lines 621-631):

```javascript
  } else if (!e.altKey && !e.ctrlKey && !e.metaKey && e.key.toLowerCase() === 'f') {
    e.preventDefault();
    const panel = getActiveFilterPanel();
    if (panel) {
      panel.classList.add('open');
      if (window.matchMedia("(hover: hover) and (pointer: fine)").matches) {
        const searchInput = panel.querySelector('input[type="text"]');
        if (searchInput) searchInput.focus();
      }
    }
  }
```

with:

```javascript
  } else if (!e.altKey && !e.ctrlKey && !e.metaKey && e.key.toLowerCase() === 'f') {
    e.preventDefault();
    const panel = getActiveFilterPanel();
    if (panel) {
      panel.classList.add('open');
      persistFilterOpen(panel);
      if (window.matchMedia("(hover: hover) and (pointer: fine)").matches) {
        const searchInput = panel.querySelector('input[type="text"]');
        if (searchInput) searchInput.focus();
      }
    }
  }
```

- [ ] **Step 6: Restore on page load, after initTabs() has run**

Replace (current lines 634-639):

```javascript
document.addEventListener("DOMContentLoaded", () => {
  initCommandPalette();
  initTitleDropdown();
  initModuleSwitchDropdown();
  initHeaderTabFade();
  document.querySelectorAll("[data-tabs]").forEach(initTabs);
```

with:

```javascript
document.addEventListener("DOMContentLoaded", () => {
  initCommandPalette();
  initTitleDropdown();
  initModuleSwitchDropdown();
  initHeaderTabFade();
  document.querySelectorAll("[data-tabs]").forEach(initTabs);
  restoreFilterOpenState();
```

- [ ] **Step 7: Sanity-check the file is still valid JS**

Run: `cd app && node --check static/js/app.js`
Expected: no output, exit code 0 (Node's `--check` only parses, doesn't execute — no `node_modules`/browser globals needed).

- [ ] **Step 8: Manual verification — Payment Memo (the module with the reported bug)**

There is no automated test covering this (pure client-side DOM/sessionStorage behavior — see spec "Testing"). Start the dev server, log in, select a company, and verify via the running page:

1. Navigate to `/payment-memo`, land on the default "Open PAM" tab.
2. Press `F` — confirm the filter panel opens (visually, and via `document.querySelector('.filter-bar.collapsible.open')` returning non-null in the console).
3. Set any filter value (e.g. type into a search field).
4. Trigger a save action that reloads the page (e.g. "Simpan Tanggal Bayar" on a row, or "Mark Complete" on the Open PAM tab) and confirm it.
5. After the page reloads: confirm the filter panel is **still open** (`document.querySelector('.filter-bar.collapsible.open')` non-null) and the same tab is still active.
6. Press `Esc` — confirm the filter closes, and `sessionStorage.getItem('fh-filter-open:' + <that panel's id>)` returns `null`.
7. Reload the page again (plain `location.reload()`, no save) — confirm the filter panel stays **closed** this time (Esc's close was correctly persisted).
8. Press `F` to reopen, then click a different tab button — confirm the filter closes (existing tab-switch behavior, unchanged), and confirm the sessionStorage entry for the panel you left is cleared.

- [ ] **Step 9: Manual verification — Beasiswa and Payment Application**

Repeat steps 2-5 above (open filter → set value → trigger a reloading save → confirm still open after reload) on:
- `/beasiswa/` — Data Siswa tab (`bsw-filter-siswa`), any save action that reloads (e.g. editing a student record).
- `/etf-payment-application` — any data tab (`pa-filter-panel`), any save action that reloads.

Expected: identical behavior to Payment Memo in both cases.

- [ ] **Step 10: Commit**

```bash
git add app/static/js/app.js
git commit -m "feat: persist filter panel open state across page reload"
```
