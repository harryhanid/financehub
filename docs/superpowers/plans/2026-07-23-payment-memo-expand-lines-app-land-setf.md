# Payment Memo Expand-Lines Parity (APP/LAND/SETF) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the APP, LAND, and SETF pillar tabs in Payment Approval Memo the same "click a row to expand its per-student lines" behavior that already exists on the AGRI tab.

**Architecture:** AGRI's existing `agriToggleExpand()` / `agriFetchBeasiswaLines()` pair already calls a pillar-agnostic backend endpoint (`GET /payment-memo/pam/<id>/beasiswa-lines`, backed by `get_pam_beasiswa_lines()`, which queries by `pam_id` with no pillar restriction). No backend changes are needed. Each of the three tabs gets its own dedicated toggle/fetch function pair (matching the codebase's existing per-tab convention — each tab already has its own debounced loader, its own selection state, its own `#<tab>-tbody`), reusing the same backend call. Clicking a row whose `source === 'beasiswa'` inserts read-only detail rows directly below it (siswa code, nama, cat1/cat2, amount) — mirroring AGRI's detail-row insertion mechanism, without AGRI's per-line checkbox/bulk-select machinery (that's tied to AGRI's own bulk-action bar and is out of scope here — this plan only replicates the *view* behavior that was actually requested).

**Tech Stack:** Flask + Jinja2 templates with inline vanilla JS (no build step, no frontend test framework — this codebase's frontend has no automated test harness; verification is manual/structural, matching how prior template-only tasks in this codebase were verified).

**Spec:** No separate design doc — this plan itself is the spec, derived directly from reading the existing AGRI reference implementation in `app/templates/payment_memo/index.html`.

## Global Constraints

- Row is only expandable when `r.source === 'beasiswa'` — non-beasiswa rows (APP has `etf`/`others`/`sponsor`/`tagihan`; SETF has `klaim_medis`/`others`) render exactly as they do today, no expand arrow, no `onclick`.
- Reuse the existing backend endpoint `GET /payment-memo/pam/<int:pam_id>/beasiswa-lines` (`app/modules/payment_memo/routes.py:207-217`) and its response shape `{"ok": bool, "rows": [...], "total": number}` — do not add new routes or new backend functions.
- Detail rows are **read-only display only** — no checkboxes, no bulk-select, no line-level actions. This is a deliberate scope cut from AGRI's fuller implementation (AGRI's `agriToggleCheckbox`/`_pamBeasiswaSelected` feed AGRI's own bulk-action bar; wiring the other three tabs into their own distinct bulk-action bars is a separate, unscoped feature).
- No new `<thead>` columns and no colspan changes to any table's existing "no data" / loading empty-state row — the expand arrow is embedded into an existing cell (APP already has a leading checkbox cell to embed into; LAND and SETF have no leading cell, so the arrow prefixes directly into their first data cell, PAM No).
- Each task is self-contained to one tab's existing "// ── TAB ──" code block in `app/templates/payment_memo/index.html` — the three tasks touch non-overlapping line ranges and can be done in parallel.
- No automated frontend tests exist in this codebase for template/JS changes. Verification per task: (1) a Flask app-boot sanity check, (2) grep-based structural checks (brace/paren/backtick balance on the new JS, correct occurrence counts), (3) a full regression run of the existing Python test suite to confirm nothing server-side broke (none of these tasks touch Python, so this should be a no-op confirmation).
- Match the existing code's exact formatting conventions per tab (indentation, inline `style=` attribute conventions, `esc()`/`fmtRupiah()` helper usage) — these already exist as globals, do not redefine them.

---

## Task 1: APP tab — expand-to-lines on beasiswa-source rows

**Files:**
- Modify: `app/templates/payment_memo/index.html:2626-2655` (`loadFIORI()` row template, inside the `.map()`)
- Modify: `app/templates/payment_memo/index.html` (new `fioriToggleExpand`/`fioriFetchBeasiswaLines` functions, added directly after `loadFIORI()` ends — currently ends at line 2657)

**Interfaces:**
- Consumes: `apiFetch` (global, in `base.html`), `esc()` (global), `fmtRupiah()` (global) — same globals AGRI's `agriFetchBeasiswaLines` already uses; `GET /payment-memo/pam/<id>/beasiswa-lines` (existing route)
- Produces: clicking a `source==='beasiswa'` row in the APP table inserts/removes detail `<tr class="fiori-detail-rows" data-pam-id="...">` elements directly after that row

- [ ] **Step 1: Add the expand arrow + row onclick to the APP row template**

In `app/templates/payment_memo/index.html`, find the `loadFIORI()` row template (currently lines 2626-2655):

```javascript
  tbody.innerHTML = data.rows.map((r, i) => `
    <tr class="fiori-row" style="background:${i % 2 === 0 ? '#fff' : '#f8fafc'};">
      <td class="f0" style="padding:6px 8px;text-align:center;background:${i%2===0?'#fff':'#f8fafc'}"><input type="checkbox" class="fiori-cb" data-id="${r.id}" style="cursor:pointer;vertical-align:middle" onchange="fioriToggleCb(this)"></td>
      <td class="f1" style="padding:6px 8px;font-weight:600;font-family:monospace;font-size:11px;white-space:nowrap;background:${i%2===0?'#fff':'#f8fafc'}">${esc(r.pam_no)}</td>
```

Replace with:

```javascript
  tbody.innerHTML = data.rows.map((r, i) => `
    <tr class="fiori-row" data-pam-id="${r.id}" style="background:${i % 2 === 0 ? '#fff' : '#f8fafc'};"
      ${r.source === 'beasiswa' ? `onclick="fioriToggleExpand(this.querySelector('.fiori-toggle'),${r.id})"` : ''}>
      <td class="f0" style="padding:6px 8px;text-align:center;background:${i%2===0?'#fff':'#f8fafc'}"><input type="checkbox" class="fiori-cb" data-id="${r.id}" style="cursor:pointer;vertical-align:middle" onclick="event.stopPropagation()" onchange="fioriToggleCb(this)">${r.source === 'beasiswa' ? `<span class="fiori-toggle" style="cursor:pointer;font-size:1rem;color:#3b82f6;font-weight:700;vertical-align:middle;margin-left:4px" onclick="fioriToggleExpand(this,${r.id});event.stopPropagation()">&#9658;</span>` : ''}</td>
      <td class="f1" style="padding:6px 8px;font-weight:600;font-family:monospace;font-size:11px;white-space:nowrap;background:${i%2===0?'#fff':'#f8fafc'}">${esc(r.pam_no)}</td>
```

Leave every other line inside the `.map()` template unchanged (from `<td class="f2"...` at pam_date through the closing `</tr>`).

- [ ] **Step 2: Add the `fioriToggleExpand`/`fioriFetchBeasiswaLines` functions**

In `app/templates/payment_memo/index.html`, right after `loadFIORI()` ends (the closing `}` after `makeSortable('fiori-table');`, currently line 2657), insert:

```javascript
let _fioriBeasiswaCache = {};

function fioriToggleExpand(toggleEl, pamId) {
  const masterTr = toggleEl.closest('tr');
  const existing = document.querySelectorAll(`.fiori-detail-rows[data-pam-id="${pamId}"]`);
  if (existing.length) {
    const nowHidden = existing[0].style.display === 'none';
    existing.forEach(tr => { tr.style.display = nowHidden ? '' : 'none'; });
    toggleEl.innerHTML = nowHidden ? '&#9660;' : '&#9658;';
    return;
  }
  fioriFetchBeasiswaLines(masterTr, toggleEl, pamId);
}

async function fioriFetchBeasiswaLines(masterTr, toggleEl, pamId) {
  if (_fioriBeasiswaCache[pamId] === 'loading') return;
  _fioriBeasiswaCache[pamId] = 'loading';

  const loadingTr = document.createElement('tr');
  loadingTr.classList.add('fiori-detail-rows');
  loadingTr.dataset.pamId = pamId;
  loadingTr.innerHTML = '<td colspan="26" style="padding:8px 36px;font-size:11px;color:#94a3b8;">Memuat detail beasiswa…</td>';
  masterTr.insertAdjacentElement('afterend', loadingTr);

  const res = await apiFetch(`/payment-memo/pam/${pamId}/beasiswa-lines`);
  loadingTr.remove();

  if (!res) {
    _fioriBeasiswaCache[pamId] = null;
    const errTr = document.createElement('tr');
    errTr.classList.add('fiori-detail-rows');
    errTr.dataset.pamId = pamId;
    errTr.innerHTML = '<td colspan="26" style="padding:8px 36px;font-size:11px;color:#ef4444;background:#fff5f5;">Gagal memuat detail beasiswa.</td>';
    masterTr.insertAdjacentElement('afterend', errTr);
    return;
  }

  const data = await res.json();
  if (!data.ok) {
    _fioriBeasiswaCache[pamId] = null;
    const errTr = document.createElement('tr');
    errTr.classList.add('fiori-detail-rows');
    errTr.dataset.pamId = pamId;
    errTr.innerHTML = `<td colspan="26" style="padding:8px 36px;font-size:11px;color:#ef4444;background:#fff5f5;">${esc(data.pesan || 'Gagal memuat.')}</td>`;
    masterTr.insertAdjacentElement('afterend', errTr);
    return;
  }

  _fioriBeasiswaCache[pamId] = data.rows;

  if (!data.rows.length) {
    const emptyTr = document.createElement('tr');
    emptyTr.classList.add('fiori-detail-rows');
    emptyTr.dataset.pamId = pamId;
    emptyTr.innerHTML = '<td colspan="26" style="padding:8px 36px;font-size:11px;color:#94a3b8;font-style:italic;">Tidak ada data beasiswa untuk PAM ini.</td>';
    masterTr.insertAdjacentElement('afterend', emptyTr);
    toggleEl.innerHTML = '&#9660;';
    return;
  }

  [...data.rows].reverse().forEach(r => {
    const tr = document.createElement('tr');
    tr.classList.add('fiori-detail-rows');
    tr.dataset.pamId = pamId;
    tr.innerHTML =
      `<td style="padding:4px 8px;vertical-align:middle"></td>` +
      `<td style="padding:4px 6px;font-size:10px;font-family:monospace;color:#94a3b8;white-space:nowrap;vertical-align:middle">${esc(r.siswa_code || '')}</td>` +
      `<td style="padding:4px 8px;font-size:11px;font-weight:600;white-space:nowrap;vertical-align:middle">${esc(r.nama || '—')}</td>` +
      `<td style="padding:4px 8px;font-size:11px;color:var(--text-muted);vertical-align:middle">${esc(r.cat1 || '')}${r.cat2 ? ' · ' + esc(r.cat2) : ''}</td>` +
      `<td style="padding:4px 8px;font-size:11px;font-weight:700;color:#1a56db;vertical-align:middle;background:#f0f9ff;white-space:nowrap">${fmtRupiah(r.amount)}</td>` +
      `<td colspan="21" style="padding:4px 8px;vertical-align:middle"></td>`;
    masterTr.insertAdjacentElement('afterend', tr);
  });

  toggleEl.innerHTML = '&#9660;';
}
```

- [ ] **Step 3: App-boot sanity check**

Run: `cd app && python -c "from app import create_app; create_app(); print('APP_BOOT_OK')"`
Expected: `APP_BOOT_OK`, no exceptions.

- [ ] **Step 4: Structural verification**

Run: `cd app && python3 -c "
import re
src = open('templates/payment_memo/index.html', encoding='utf-8').read()
fn = re.search(r'function fioriFetchBeasiswaLines.*?\n}\n', src, re.S).group(0)
assert fn.count('{') == fn.count('}'), 'brace mismatch in fioriFetchBeasiswaLines'
assert fn.count('(') == fn.count(')'), 'paren mismatch in fioriFetchBeasiswaLines'
assert src.count('fioriToggleExpand') >= 3, 'expected onclick wiring + function def + recursive call'
print('STRUCTURAL_OK')
"`
Expected: `STRUCTURAL_OK`.

- [ ] **Step 5: Run the Python regression suite to confirm no server-side breakage**

Run: `cd app && python -m pytest tests/test_pam_pa_cascade.py tests/test_pam_remove_student.py tests/test_beasiswa_service.py tests/test_payment_memo_service.py -q`
Expected: same pass/fail counts as before this task (this task touches no Python) — the 3 pre-existing failures (`test_set_pam_complete_cascade_advance_pillar_sets_paid_not_complete`, `test_set_pam_complete_cascade_syncs_setf_to_bank_setf`, `test_update_pam_status_syncs_setf_to_bank_setf_when_completed`) are expected and unrelated.

- [ ] **Step 6: Commit**

```bash
git add app/templates/payment_memo/index.html
git commit -m "feat: add expand-to-lines on beasiswa-source rows in APP tab"
```

---

## Task 2: LAND tab — expand-to-lines on beasiswa-source rows

**Files:**
- Modify: `app/templates/payment_memo/index.html:1908-1936` (`loadSML()` row template, inside the `.map()`)
- Modify: `app/templates/payment_memo/index.html` (new `smlToggleExpand`/`smlFetchBeasiswaLines` functions, added directly after `loadSML()` ends — currently line 1938)

**Interfaces:**
- Consumes: same globals as Task 1; `GET /payment-memo/pam/<id>/beasiswa-lines`
- Produces: clicking a `source==='beasiswa'` row in the LAND table inserts/removes detail `<tr class="sml-detail-rows" data-pam-id="...">` elements directly after that row

LAND's table (`#sml-table`) has **no leading checkbox column** (25 columns total, all data columns — confirmed by the existing empty-state `colspan="25"` at line 1903 and the table's own `<thead>`, which starts directly with "PAM No"). Unlike Task 1, the expand arrow prefixes directly into the first data cell (PAM No) rather than into a dedicated leading cell.

- [ ] **Step 1: Add the expand arrow + row onclick to the LAND row template**

In `app/templates/payment_memo/index.html`, find the `loadSML()` row template (currently lines 1908-1936):

```javascript
  tbody.innerHTML = data.rows.map((r, i) => `
    <tr style="background:${i % 2 === 0 ? '#fff' : '#f8fafc'};">
      <td style="padding:6px 8px;font-weight:600;font-family:monospace;font-size:11px;white-space:nowrap">${esc(r.pam_no)}</td>
```

Replace with:

```javascript
  tbody.innerHTML = data.rows.map((r, i) => `
    <tr data-pam-id="${r.id}" style="background:${i % 2 === 0 ? '#fff' : '#f8fafc'};"
      ${r.source === 'beasiswa' ? `onclick="smlToggleExpand(this.querySelector('.sml-toggle'),${r.id})"` : ''}>
      <td style="padding:6px 8px;font-weight:600;font-family:monospace;font-size:11px;white-space:nowrap">${r.source === 'beasiswa' ? `<span class="sml-toggle" style="cursor:pointer;font-size:1rem;color:#3b82f6;font-weight:700;vertical-align:middle;margin-right:4px" onclick="smlToggleExpand(this,${r.id});event.stopPropagation()">&#9658;</span>` : ''}${esc(r.pam_no)}</td>
```

Leave every other line inside the `.map()` template unchanged (from the Tgl PAM `<td>` through the closing `</tr>`).

- [ ] **Step 2: Add the `smlToggleExpand`/`smlFetchBeasiswaLines` functions**

In `app/templates/payment_memo/index.html`, right after `loadSML()` ends (the closing `}` after `makeSortable('sml-table');`, currently line 1938), insert:

```javascript
let _smlBeasiswaCache = {};

function smlToggleExpand(toggleEl, pamId) {
  const masterTr = toggleEl.closest('tr');
  const existing = document.querySelectorAll(`.sml-detail-rows[data-pam-id="${pamId}"]`);
  if (existing.length) {
    const nowHidden = existing[0].style.display === 'none';
    existing.forEach(tr => { tr.style.display = nowHidden ? '' : 'none'; });
    toggleEl.innerHTML = nowHidden ? '&#9660;' : '&#9658;';
    return;
  }
  smlFetchBeasiswaLines(masterTr, toggleEl, pamId);
}

async function smlFetchBeasiswaLines(masterTr, toggleEl, pamId) {
  if (_smlBeasiswaCache[pamId] === 'loading') return;
  _smlBeasiswaCache[pamId] = 'loading';

  const loadingTr = document.createElement('tr');
  loadingTr.classList.add('sml-detail-rows');
  loadingTr.dataset.pamId = pamId;
  loadingTr.innerHTML = '<td colspan="25" style="padding:8px 36px;font-size:11px;color:#94a3b8;">Memuat detail beasiswa…</td>';
  masterTr.insertAdjacentElement('afterend', loadingTr);

  const res = await apiFetch(`/payment-memo/pam/${pamId}/beasiswa-lines`);
  loadingTr.remove();

  if (!res) {
    _smlBeasiswaCache[pamId] = null;
    const errTr = document.createElement('tr');
    errTr.classList.add('sml-detail-rows');
    errTr.dataset.pamId = pamId;
    errTr.innerHTML = '<td colspan="25" style="padding:8px 36px;font-size:11px;color:#ef4444;background:#fff5f5;">Gagal memuat detail beasiswa.</td>';
    masterTr.insertAdjacentElement('afterend', errTr);
    return;
  }

  const data = await res.json();
  if (!data.ok) {
    _smlBeasiswaCache[pamId] = null;
    const errTr = document.createElement('tr');
    errTr.classList.add('sml-detail-rows');
    errTr.dataset.pamId = pamId;
    errTr.innerHTML = `<td colspan="25" style="padding:8px 36px;font-size:11px;color:#ef4444;background:#fff5f5;">${esc(data.pesan || 'Gagal memuat.')}</td>`;
    masterTr.insertAdjacentElement('afterend', errTr);
    return;
  }

  _smlBeasiswaCache[pamId] = data.rows;

  if (!data.rows.length) {
    const emptyTr = document.createElement('tr');
    emptyTr.classList.add('sml-detail-rows');
    emptyTr.dataset.pamId = pamId;
    emptyTr.innerHTML = '<td colspan="25" style="padding:8px 36px;font-size:11px;color:#94a3b8;font-style:italic;">Tidak ada data beasiswa untuk PAM ini.</td>';
    masterTr.insertAdjacentElement('afterend', emptyTr);
    toggleEl.innerHTML = '&#9660;';
    return;
  }

  [...data.rows].reverse().forEach(r => {
    const tr = document.createElement('tr');
    tr.classList.add('sml-detail-rows');
    tr.dataset.pamId = pamId;
    tr.innerHTML =
      `<td style="padding:4px 6px;font-size:10px;font-family:monospace;color:#94a3b8;white-space:nowrap;vertical-align:middle">${esc(r.siswa_code || '')}</td>` +
      `<td style="padding:4px 8px;font-size:11px;font-weight:600;white-space:nowrap;vertical-align:middle">${esc(r.nama || '—')}</td>` +
      `<td style="padding:4px 8px;font-size:11px;color:var(--text-muted);vertical-align:middle">${esc(r.cat1 || '')}${r.cat2 ? ' · ' + esc(r.cat2) : ''}</td>` +
      `<td style="padding:4px 8px;font-size:11px;font-weight:700;color:#1a56db;vertical-align:middle;background:#f0f9ff;white-space:nowrap">${fmtRupiah(r.amount)}</td>` +
      `<td colspan="21" style="padding:4px 8px;vertical-align:middle"></td>`;
    masterTr.insertAdjacentElement('afterend', tr);
  });

  toggleEl.innerHTML = '&#9660;';
}
```

- [ ] **Step 3: App-boot sanity check**

Run: `cd app && python -c "from app import create_app; create_app(); print('APP_BOOT_OK')"`
Expected: `APP_BOOT_OK`, no exceptions.

- [ ] **Step 4: Structural verification**

Run: `cd app && python3 -c "
import re
src = open('templates/payment_memo/index.html', encoding='utf-8').read()
fn = re.search(r'function smlFetchBeasiswaLines.*?\n}\n', src, re.S).group(0)
assert fn.count('{') == fn.count('}'), 'brace mismatch in smlFetchBeasiswaLines'
assert fn.count('(') == fn.count(')'), 'paren mismatch in smlFetchBeasiswaLines'
assert src.count('smlToggleExpand') >= 3, 'expected onclick wiring + function def + recursive call'
print('STRUCTURAL_OK')
"`
Expected: `STRUCTURAL_OK`.

- [ ] **Step 5: Run the Python regression suite to confirm no server-side breakage**

Run: `cd app && python -m pytest tests/test_pam_pa_cascade.py tests/test_pam_remove_student.py tests/test_beasiswa_service.py tests/test_payment_memo_service.py -q`
Expected: same pass/fail counts as before this task — the 3 pre-existing failures are expected and unrelated.

- [ ] **Step 6: Commit**

```bash
git add app/templates/payment_memo/index.html
git commit -m "feat: add expand-to-lines on beasiswa-source rows in LAND tab"
```

---

## Task 3: SETF tab — expand-to-lines on beasiswa-source rows

**Files:**
- Modify: `app/templates/payment_memo/index.html` (`loadSETF()` row template, inside the `.map()` at line ~2115 — verify by locating `async function loadSETF()`)
- Modify: `app/templates/payment_memo/index.html` (new `setfToggleExpand`/`setfFetchBeasiswaLines` functions, added directly after `loadSETF()` ends — the `}` after `makeSortable('setf-table');`, line ~2136)

**Interfaces:**
- Consumes: same globals as Task 1; `GET /payment-memo/pam/<id>/beasiswa-lines`
- Produces: clicking a `source==='beasiswa'` row in the SETF table inserts/removes detail `<tr class="setf-detail-rows" data-pam-id="...">` elements directly after that row

SETF's table (`#setf-table`) has **no leading checkbox column** (16 columns total — confirmed by the existing empty-state `colspan="16"` in `loadSETF()`). Same "prefix into first data cell" approach as Task 2 (LAND).

**Disambiguation note (line numbers are approximate — Tasks 1 & 2 shifted them):** the 3-line snippet (map + plain `<tr>` + PAM No `<td>`) is NOT unique — after Tasks 1 & 2 modified the APP and LAND row templates, this exact plain-`<tr>` pattern still appears in BOTH `loadSETF()` (the target) and `loadAdvance()` (the `_plDate(r.id,'ADVANCE',…)` block, further down). They diverge only at the 3rd data cell: SETF's is `gl_account`, ADVANCE's is `pt`. The edit below therefore includes two extra trailing context lines (`pam_date` + `gl_account`), kept unchanged, to anchor uniquely on the SETF block. Confirm you are inside `loadSETF()` before editing.

- [ ] **Step 1: Add the expand arrow + row onclick to the SETF row template**

In `app/templates/payment_memo/index.html`, inside `loadSETF()`, find (anchored on the `gl_account` cell to stay unique to SETF):

```javascript
  tbody.innerHTML = data.rows.map((r, i) => `
    <tr style="background:${i % 2 === 0 ? '#fff' : '#f8fafc'};">
      <td style="padding:6px 8px;font-weight:600;font-family:monospace;font-size:11px;white-space:nowrap">${esc(r.pam_no)}</td>
      <td style="padding:6px 8px;white-space:nowrap">${esc(r.pam_date || '-')}</td>
      <td style="padding:6px 8px;font-family:monospace;font-size:11px">${esc(r.gl_account || '-')}</td>
```

Replace with (only the `<tr>` and PAM No `<td>` change; the `pam_date` and `gl_account` lines are reproduced unchanged as anchors):

```javascript
  tbody.innerHTML = data.rows.map((r, i) => `
    <tr data-pam-id="${r.id}" style="background:${i % 2 === 0 ? '#fff' : '#f8fafc'};"
      ${r.source === 'beasiswa' ? `onclick="setfToggleExpand(this.querySelector('.setf-toggle'),${r.id})"` : ''}>
      <td style="padding:6px 8px;font-weight:600;font-family:monospace;font-size:11px;white-space:nowrap">${r.source === 'beasiswa' ? `<span class="setf-toggle" style="cursor:pointer;font-size:1rem;color:#3b82f6;font-weight:700;vertical-align:middle;margin-right:4px" onclick="setfToggleExpand(this,${r.id});event.stopPropagation()">&#9658;</span>` : ''}${esc(r.pam_no)}</td>
      <td style="padding:6px 8px;white-space:nowrap">${esc(r.pam_date || '-')}</td>
      <td style="padding:6px 8px;font-family:monospace;font-size:11px">${esc(r.gl_account || '-')}</td>
```

Leave every other line inside the `.map()` template unchanged (from the Cost Center `<td>` through the closing `</tr>`).

- [ ] **Step 2: Add the `setfToggleExpand`/`setfFetchBeasiswaLines` functions**

In `app/templates/payment_memo/index.html`, right after `loadSETF()` ends (the closing `}` after `makeSortable('setf-table');`, line ~2136), insert:

```javascript
let _setfBeasiswaCache = {};

function setfToggleExpand(toggleEl, pamId) {
  const masterTr = toggleEl.closest('tr');
  const existing = document.querySelectorAll(`.setf-detail-rows[data-pam-id="${pamId}"]`);
  if (existing.length) {
    const nowHidden = existing[0].style.display === 'none';
    existing.forEach(tr => { tr.style.display = nowHidden ? '' : 'none'; });
    toggleEl.innerHTML = nowHidden ? '&#9660;' : '&#9658;';
    return;
  }
  setfFetchBeasiswaLines(masterTr, toggleEl, pamId);
}

async function setfFetchBeasiswaLines(masterTr, toggleEl, pamId) {
  if (_setfBeasiswaCache[pamId] === 'loading') return;
  _setfBeasiswaCache[pamId] = 'loading';

  const loadingTr = document.createElement('tr');
  loadingTr.classList.add('setf-detail-rows');
  loadingTr.dataset.pamId = pamId;
  loadingTr.innerHTML = '<td colspan="16" style="padding:8px 36px;font-size:11px;color:#94a3b8;">Memuat detail beasiswa…</td>';
  masterTr.insertAdjacentElement('afterend', loadingTr);

  const res = await apiFetch(`/payment-memo/pam/${pamId}/beasiswa-lines`);
  loadingTr.remove();

  if (!res) {
    _setfBeasiswaCache[pamId] = null;
    const errTr = document.createElement('tr');
    errTr.classList.add('setf-detail-rows');
    errTr.dataset.pamId = pamId;
    errTr.innerHTML = '<td colspan="16" style="padding:8px 36px;font-size:11px;color:#ef4444;background:#fff5f5;">Gagal memuat detail beasiswa.</td>';
    masterTr.insertAdjacentElement('afterend', errTr);
    return;
  }

  const data = await res.json();
  if (!data.ok) {
    _setfBeasiswaCache[pamId] = null;
    const errTr = document.createElement('tr');
    errTr.classList.add('setf-detail-rows');
    errTr.dataset.pamId = pamId;
    errTr.innerHTML = `<td colspan="16" style="padding:8px 36px;font-size:11px;color:#ef4444;background:#fff5f5;">${esc(data.pesan || 'Gagal memuat.')}</td>`;
    masterTr.insertAdjacentElement('afterend', errTr);
    return;
  }

  _setfBeasiswaCache[pamId] = data.rows;

  if (!data.rows.length) {
    const emptyTr = document.createElement('tr');
    emptyTr.classList.add('setf-detail-rows');
    emptyTr.dataset.pamId = pamId;
    emptyTr.innerHTML = '<td colspan="16" style="padding:8px 36px;font-size:11px;color:#94a3b8;font-style:italic;">Tidak ada data beasiswa untuk PAM ini.</td>';
    masterTr.insertAdjacentElement('afterend', emptyTr);
    toggleEl.innerHTML = '&#9660;';
    return;
  }

  [...data.rows].reverse().forEach(r => {
    const tr = document.createElement('tr');
    tr.classList.add('setf-detail-rows');
    tr.dataset.pamId = pamId;
    tr.innerHTML =
      `<td style="padding:4px 6px;font-size:10px;font-family:monospace;color:#94a3b8;white-space:nowrap;vertical-align:middle">${esc(r.siswa_code || '')}</td>` +
      `<td style="padding:4px 8px;font-size:11px;font-weight:600;white-space:nowrap;vertical-align:middle">${esc(r.nama || '—')}</td>` +
      `<td style="padding:4px 8px;font-size:11px;color:var(--text-muted);vertical-align:middle">${esc(r.cat1 || '')}${r.cat2 ? ' · ' + esc(r.cat2) : ''}</td>` +
      `<td style="padding:4px 8px;font-size:11px;font-weight:700;color:#1a56db;vertical-align:middle;background:#f0f9ff;white-space:nowrap">${fmtRupiah(r.amount)}</td>` +
      `<td colspan="12" style="padding:4px 8px;vertical-align:middle"></td>`;
    masterTr.insertAdjacentElement('afterend', tr);
  });

  toggleEl.innerHTML = '&#9660;';
}
```

- [ ] **Step 3: App-boot sanity check**

Run: `cd app && python -c "from app import create_app; create_app(); print('APP_BOOT_OK')"`
Expected: `APP_BOOT_OK`, no exceptions.

- [ ] **Step 4: Structural verification**

Run: `cd app && python3 -c "
import re
src = open('templates/payment_memo/index.html', encoding='utf-8').read()
fn = re.search(r'function setfFetchBeasiswaLines.*?\n}\n', src, re.S).group(0)
assert fn.count('{') == fn.count('}'), 'brace mismatch in setfFetchBeasiswaLines'
assert fn.count('(') == fn.count(')'), 'paren mismatch in setfFetchBeasiswaLines'
assert src.count('setfToggleExpand') >= 3, 'expected onclick wiring + function def + recursive call'
print('STRUCTURAL_OK')
"`
Expected: `STRUCTURAL_OK`.

- [ ] **Step 5: Run the Python regression suite to confirm no server-side breakage**

Run: `cd app && python -m pytest tests/test_pam_pa_cascade.py tests/test_pam_remove_student.py tests/test_beasiswa_service.py tests/test_payment_memo_service.py -q`
Expected: same pass/fail counts as before this task — the 3 pre-existing failures are expected and unrelated.

- [ ] **Step 6: Commit**

```bash
git add app/templates/payment_memo/index.html
git commit -m "feat: add expand-to-lines on beasiswa-source rows in SETF tab"
```

---

## Final Verification

- [ ] Run the full regression suite once more after all 3 tasks: `cd app && python -m pytest tests/test_pam_pa_cascade.py tests/test_pam_remove_student.py tests/test_beasiswa_service.py tests/test_payment_memo_service.py -q` — same result as the individual task runs.
- [ ] Grep-confirm exactly 3 new toggle/fetch function pairs exist and none collide in name: `grep -c "^function fioriToggleExpand\|^function smlToggleExpand\|^function setfToggleExpand" app/templates/payment_memo/index.html` → expect `3`.
- [ ] Manual walkthrough (when a browser session is available): open Payment Approval Memo → APP tab, click a `source=beasiswa` row (e.g. one of the 65 live beasiswa-source APP PAMs), confirm it expands to show student lines matching AGRI's behavior; repeat for SETF (12 live beasiswa-source records); LAND has no live data yet, so confirm only that a `source=beasiswa` row (if manually seeded) expands without a console error.
