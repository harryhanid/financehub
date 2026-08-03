# FLOW Payment Application — Persistent Bulk Selection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** In Payment Application's AGRI/APP/SML/SETF tabs, checking a row's bulk-selection checkbox after one name search must survive a second name search — currently every filter change is a full page reload that wipes the DOM checkbox state, so only the most recent search's checks are ever seen by bulk actions.

**Architecture:** A `sessionStorage`-backed set of `{id, nama}` per tab (key `fh-pa-selected:<tab>`) becomes the single source of truth for "what's selected." All existing UI (row checkboxes, "select all," the chips row, the bulk-update call, the clear button) reads from and writes to this set instead of scanning the DOM for `:checked` boxes. On each page load, any currently-rendered row whose id is in the set gets its checkbox re-checked.

**Tech Stack:** Vanilla JS, Jinja2 template. No JS test framework exists in this repo — verified by manual browser check, not automated tests (matches the established convention for JS-only changes in this codebase).

## Global Constraints

- Selection scope is per tab (AGRI/APP/SML/SETF each have an independent `sessionStorage` key) — switching tabs does not carry a selection over. Do not build a cross-tab mechanism.
- Selection persists only for the browser tab's session (`sessionStorage`, not `localStorage`) — it should disappear if the tab/browser closes.
- The "Reset" filter button (`resetFilters()`) must NOT be touched — it must continue to only affect filter query params, never the selection.
- All ids are stored and compared as `parseInt`-normalized numbers throughout — the existing code mixes string (`checkbox.value`) and number sources, so every read/write path in this plan explicitly normalizes to avoid silent dedup/lookup failures from `"12" !== 12`.
- Every code snippet below was checked against the current content of `app/templates/etf_payment_application/index.html` at plan-writing time. Confirm current line numbers with `grep -n` before editing, since this file has other pending work in flight — if line numbers have shifted, locate the same function by name and apply the same before/after diff.

---

### Task 1: Persistent selection storage + rewire all consumers

**Files:**
- Modify: `app/templates/etf_payment_application/index.html` — the "─── Checkbox & selection ───" block (currently lines 1169-1239) and its call site in `doBulkUpdate` (currently line 1313).

**Interfaces:**
- Produces: `getSelectedPa(tab)`, `setSelectedPa(tab, list)`, `addSelectedPa(tab, id, nama)`, `removeSelectedPa(tab, id)`, `clearSelectedPa(tab)`, `restorePaSelection()` — all consumed only within this file.
- Consumes: `ACTIVE_TAB` (already defined earlier in the same script block, e.g. `const ACTIVE_TAB = "{{ active_tab }}";`).

- [ ] **Step 1: Add the sessionStorage helpers and `restorePaSelection()`**

Find the existing comment marker (currently line 1169):
```js
// ─── Checkbox & selection ─────────────────────────────────────────────────────
```
Insert immediately BEFORE it:
```js
// ─── Persistent PA selection (sessionStorage, per tab) ─────────────────────
// PA's filters navigate via a full page reload (see navigateWithFilters()),
// which wipes DOM checkbox state. This persists the selection across those
// reloads so bulk-marking survives multiple searches. Scoped per tab.
// See docs/superpowers/specs/2026-08-03-flow-pa-persistent-bulk-selection-design.md
function _paSelectionKey(tab) {
  return 'fh-pa-selected:' + tab;
}
function getSelectedPa(tab) {
  try {
    const raw = sessionStorage.getItem(_paSelectionKey(tab));
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch (e) { return []; }
}
function setSelectedPa(tab, list) {
  try { sessionStorage.setItem(_paSelectionKey(tab), JSON.stringify(list)); } catch (e) {}
}
function addSelectedPa(tab, id, nama) {
  const list = getSelectedPa(tab);
  if (!list.some(e => e.id === id)) {
    list.push({ id, nama });
    setSelectedPa(tab, list);
  }
}
function removeSelectedPa(tab, id) {
  setSelectedPa(tab, getSelectedPa(tab).filter(e => e.id !== id));
}
function clearSelectedPa(tab) {
  try { sessionStorage.removeItem(_paSelectionKey(tab)); } catch (e) {}
}

// Restores checked state on any currently-rendered row whose id is in the
// persisted selection, then syncs the "select all" header checkbox and bulk
// bar. Called once after the table has rendered (see DOMContentLoaded below).
function restorePaSelection() {
  const selected = getSelectedPa(ACTIVE_TAB);
  if (!selected.length) return;
  const ids = new Set(selected.map(e => e.id));
  document.querySelectorAll("#pa-table tbody tr[data-pa-id]").forEach(tr => {
    const id = parseInt(tr.dataset.paId);
    const cb = tr.querySelector(".row-chk");
    if (cb && ids.has(id)) {
      cb.checked = true;
      tr.classList.add("row-sel");
    }
  });
  const all = document.querySelectorAll("#pa-table tbody tr[data-pa-id]:not([style*='none']) .row-chk");
  const checked = [...all].filter(c => c.checked);
  const chkAll = document.getElementById("chk-all");
  if (chkAll) chkAll.checked = checked.length === all.length && all.length > 0;
  updateBulkBar();
}

```

- [ ] **Step 2: Rewire `toggleAll`, `onRowCheck`, `clearSelection` to write through to the persisted set**

Find:
```js
function toggleAll(chk) {
  document.querySelectorAll("#pa-table tbody tr[data-pa-id]:not([style*='none']) .row-chk")
    .forEach(c => { c.checked = chk.checked; c.closest("tr").classList.toggle("row-sel", chk.checked); });
  updateBulkBar();
}
function onRowCheck() {
  const tr = event.target.closest("tr");
  tr.classList.toggle("row-sel", event.target.checked);
  const all  = document.querySelectorAll("#pa-table tbody tr[data-pa-id]:not([style*='none']) .row-chk");
  const checked = [...all].filter(c => c.checked);
  document.getElementById("chk-all").checked = checked.length === all.length && all.length > 0;
  updateBulkBar();
}
function clearSelection() {
  document.querySelectorAll(".row-chk").forEach(c => { c.checked = false; c.closest("tr").classList.remove("row-sel"); });
  document.getElementById("chk-all").checked = false;
  updateBulkBar();
}
```
Replace with:
```js
function toggleAll(chk) {
  document.querySelectorAll("#pa-table tbody tr[data-pa-id]:not([style*='none']) .row-chk")
    .forEach(c => {
      c.checked = chk.checked;
      const tr = c.closest("tr");
      tr.classList.toggle("row-sel", chk.checked);
      const id = parseInt(c.value);
      if (chk.checked) addSelectedPa(ACTIVE_TAB, id, tr.dataset.nama || '');
      else removeSelectedPa(ACTIVE_TAB, id);
    });
  updateBulkBar();
}
function onRowCheck() {
  const tr = event.target.closest("tr");
  tr.classList.toggle("row-sel", event.target.checked);
  const id = parseInt(event.target.value);
  if (event.target.checked) addSelectedPa(ACTIVE_TAB, id, tr.dataset.nama || '');
  else removeSelectedPa(ACTIVE_TAB, id);
  const all  = document.querySelectorAll("#pa-table tbody tr[data-pa-id]:not([style*='none']) .row-chk");
  const checked = [...all].filter(c => c.checked);
  document.getElementById("chk-all").checked = checked.length === all.length && all.length > 0;
  updateBulkBar();
}
function clearSelection() {
  document.querySelectorAll(".row-chk").forEach(c => { c.checked = false; c.closest("tr").classList.remove("row-sel"); });
  document.getElementById("chk-all").checked = false;
  clearSelectedPa(ACTIVE_TAB);
  updateBulkBar();
}
```

- [ ] **Step 3: Rewire `updateBulkBar` to count from the persisted set**

Find:
```js
function updateBulkBar() {
  const sel = document.querySelectorAll(".row-chk:checked");
  const bar = document.getElementById("bulk-bar");
  bar.style.display = sel.length ? "flex" : "none";
  document.getElementById("bulk-count").textContent = `${sel.length} baris dipilih`;
  renderPaChips();
}
```
Replace with:
```js
function updateBulkBar() {
  const sel = getSelectedPa(ACTIVE_TAB);
  const bar = document.getElementById("bulk-bar");
  bar.style.display = sel.length ? "flex" : "none";
  document.getElementById("bulk-count").textContent = `${sel.length} baris dipilih`;
  renderPaChips();
}
```

- [ ] **Step 4: Rewire `renderPaChips` and `expandPaChips` to read from the persisted set**

Find:
```js
function renderPaChips() {
  const container = document.getElementById("pa-chips-row");
  if (!container) return;
  const checked = [...document.querySelectorAll(".row-chk:checked")];
  if (!checked.length) { container.style.display = "none"; return; }
  const LIMIT  = 5;
  const hidden = checked.length > LIMIT + 1 ? checked.slice(LIMIT) : [];
  const shown  = hidden.length ? checked.slice(0, LIMIT) : checked;
  function chipHtml(cb) {
    const id   = cb.value;
    const nama = cb.closest("tr")?.dataset.nama || id;
    return `<span style="background:var(--accent);color:#fff;border-radius:99px;padding:2px 9px;font-size:11px;display:inline-flex;align-items:center;gap:3px;white-space:nowrap">${nama}<span onclick="removePaChip('${id}')" style="cursor:pointer;margin-left:3px;opacity:.8;font-size:10px" title="Hapus dari pilihan">✕</span></span>`;
  }
  let html = `<span style="font-size:10px;color:var(--accent-text);font-weight:700;white-space:nowrap;margin-right:2px">● Tandai:</span>`;
  html += shown.map(chipHtml).join('');
  if (hidden.length) {
    html += `<span id="pa-chips-expand" onclick="expandPaChips()" style="background:var(--accent-surface);color:var(--accent-text);border:1px solid var(--accent-border);border-radius:99px;padding:2px 9px;font-size:11px;cursor:pointer;white-space:nowrap">+${hidden.length} lagi ▾</span>`;
    html += `<span id="pa-chips-hidden" style="display:none">` + hidden.map(chipHtml).join('') + `</span>`;
  }
  container.innerHTML = html;
  container.style.display = "flex";
}

function expandPaChips() {
  const h = document.getElementById("pa-chips-hidden");
  const b = document.getElementById("pa-chips-expand");
  if (!h || !b) return;
  const expanded = h.style.display !== "none";
  h.style.display = expanded ? "none" : "contents";
  b.textContent   = expanded ? `+${document.querySelectorAll(".row-chk:checked").length - 5} lagi ▾` : "▲ sembunyikan";
}
```
Replace with:
```js
function renderPaChips() {
  const container = document.getElementById("pa-chips-row");
  if (!container) return;
  const selected = getSelectedPa(ACTIVE_TAB);
  if (!selected.length) { container.style.display = "none"; return; }
  const LIMIT  = 5;
  const hidden = selected.length > LIMIT + 1 ? selected.slice(LIMIT) : [];
  const shown  = hidden.length ? selected.slice(0, LIMIT) : selected;
  function chipHtml(entry) {
    const nama = entry.nama || entry.id;
    return `<span style="background:var(--accent);color:#fff;border-radius:99px;padding:2px 9px;font-size:11px;display:inline-flex;align-items:center;gap:3px;white-space:nowrap">${nama}<span onclick="removePaChip(${entry.id})" style="cursor:pointer;margin-left:3px;opacity:.8;font-size:10px" title="Hapus dari pilihan">✕</span></span>`;
  }
  let html = `<span style="font-size:10px;color:var(--accent-text);font-weight:700;white-space:nowrap;margin-right:2px">● Tandai:</span>`;
  html += shown.map(chipHtml).join('');
  if (hidden.length) {
    html += `<span id="pa-chips-expand" onclick="expandPaChips()" style="background:var(--accent-surface);color:var(--accent-text);border:1px solid var(--accent-border);border-radius:99px;padding:2px 9px;font-size:11px;cursor:pointer;white-space:nowrap">+${hidden.length} lagi ▾</span>`;
    html += `<span id="pa-chips-hidden" style="display:none">` + hidden.map(chipHtml).join('') + `</span>`;
  }
  container.innerHTML = html;
  container.style.display = "flex";
}

function expandPaChips() {
  const h = document.getElementById("pa-chips-hidden");
  const b = document.getElementById("pa-chips-expand");
  if (!h || !b) return;
  const expanded = h.style.display !== "none";
  h.style.display = expanded ? "none" : "contents";
  b.textContent   = expanded ? `+${getSelectedPa(ACTIVE_TAB).length - 5} lagi ▾` : "▲ sembunyikan";
}
```

- [ ] **Step 5: Rewire `removePaChip` and `selectedPaIds`**

Find:
```js
function removePaChip(paId) {
  const cb = document.querySelector(`.row-chk[value="${paId}"]`);
  if (cb) { cb.checked = false; cb.closest("tr")?.classList.remove("row-sel"); }
  const all     = document.querySelectorAll("#pa-table tbody tr[data-pa-id]:not([style*='none']) .row-chk");
  const checked = [...all].filter(c => c.checked);
  document.getElementById("chk-all").checked = checked.length === all.length && all.length > 0;
  updateBulkBar();
}
function selectedPaIds() {
  const raw = [...document.querySelectorAll(".row-chk:checked")].map(c => parseInt(c.value));
  return [...new Set(raw)];
}
```
Replace with:
```js
function removePaChip(paId) {
  const cb = document.querySelector(`.row-chk[value="${paId}"]`);
  if (cb) { cb.checked = false; cb.closest("tr")?.classList.remove("row-sel"); }
  removeSelectedPa(ACTIVE_TAB, paId);
  const all     = document.querySelectorAll("#pa-table tbody tr[data-pa-id]:not([style*='none']) .row-chk");
  const checked = [...all].filter(c => c.checked);
  document.getElementById("chk-all").checked = checked.length === all.length && all.length > 0;
  updateBulkBar();
}
function selectedPaIds() {
  return getSelectedPa(ACTIVE_TAB).map(e => e.id);
}
```

- [ ] **Step 6: Call `restorePaSelection()` once the table has rendered**

Immediately after the `selectedPaIds()` function (end of the checkbox/selection block), add:
```js
document.addEventListener('DOMContentLoaded', restorePaSelection);
```

- [ ] **Step 7: Manual verify — basic accumulation across searches**

Run the Flask dev server, log in, select ETF company, open Payment Application → AGRI tab (needs 2+ existing PA records; use existing seeded/real data).
1. Search a name in "Cari nama PB", check that row's box. Confirm the chips row shows "● Tandai: <nama>" and the bulk bar appears.
2. Clear the search box and search a different name. Confirm: the first name's chip is STILL shown (even though its row is no longer in the table), and checking the second name's row adds a second chip.
3. Open devtools console: `JSON.parse(sessionStorage.getItem('fh-pa-selected:agri'))` should show both entries.
4. Click "✕ Batalkan Pilihan" — chips and bulk bar disappear, `sessionStorage.getItem('fh-pa-selected:agri')` is `null`.
5. Repeat steps 1-2, then click "Reset" (filter reset) — confirm the chips/selection are UNCHANGED (only the filter inputs cleared), per this plan's constraint that Reset never touches selection.
6. With 2 names selected (rows from different searches), use the bulk-date-fill controls ("Isi Tanggal" or "Hari Ini") and confirm the success toast reports 2 rows updated (not just whatever's currently visible).

- [ ] **Step 8: Commit**

```bash
git add app/templates/etf_payment_application/index.html
git commit -m "feat: persist PA bulk-selection across name searches (sessionStorage, per tab)"
```

---

### Task 2: Regression check across all four tabs

**Files:** None (verification only).

- [ ] **Step 1: Repeat Task 1 Step 7's flow on APP, SML, and SETF tabs**

Each tab uses the same shared JS (keyed by its own `ACTIVE_TAB` value), so verify the `sessionStorage` key differs per tab (`fh-pa-selected:app`, `fh-pa-selected:sml`, `fh-pa-selected:setf`) and that switching from AGRI to APP does NOT show AGRI's chips (confirms the per-tab scope requirement).

- [ ] **Step 2: Confirm "select all" still works correctly**

On a tab with all rows fitting on one page, click the header "select all" checkbox — confirm all rows check and one chip per row appears (up to the existing 5-chip-then-"+N lagi" display limit already in place). Uncheck "select all" — confirm all clear. Then check 2 rows individually, click "select all" — confirm it still results in ALL rows selected (union, not overwrite) and unchecking "select all" removes only the currently-visible rows from the set (not previously-selected rows from a since-changed filter, though in-page toggling won't usually exercise that edge — this step just confirms no regression in the common single-page case).

- [ ] **Step 3: Confirm no interference with the dynamic-pagination-page-size feature (if already implemented)**

If `docs/superpowers/plans/2026-07-31-flow-dynamic-pagination-page-size.md` has already been executed, confirm the one-time calibration reload it introduces on page load does not clear a selection made just before it (selection should survive since it's the same sessionStorage-scoped tab session). If that plan hasn't been executed yet, skip this step.

- [ ] **Step 4: Final review**

Review the diff from Task 1 against `docs/superpowers/specs/2026-08-03-flow-pa-persistent-bulk-selection-design.md` — confirm every design decision (per-tab scope, sessionStorage duration, Reset not clearing selection) is reflected in the actual code.
