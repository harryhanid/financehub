# FLOW Payment Memo — Persistent Bulk Selection Implementation Plan (AGRI / APP)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** In Payment Memo's AGRI and APP tabs, checking a row/line's bulk-selection checkbox after one search must survive a second search — both tabs currently wipe their selection state on every `loadPAM()`/`loadFIORI()` call.

**Architecture:** Both tabs already hold selection in in-memory JS variables (`_pamBeasiswaSelected`, `_fioriSelected`/`_fioriSelectionMeta`) — Payment Memo never navigates away for search/filter (no page reload to survive, unlike Payment Application), so no `sessionStorage` is needed here. The fix is: (1) stop explicitly clearing those variables on every search, and (2) since the DOM is still fully re-rendered on each search, restore checked/indeterminate visual state from the (now-persistent) variables once rendering completes. AGRI additionally needs a cache-independent name lookup (`_pamBeasiswaSelectionMeta`) because its existing chip-rendering depends on a beasiswa-lines cache that legitimately still gets cleared every search.

**Tech Stack:** Vanilla JS, Jinja2 template. No JS test framework exists in this repo — verified by manual browser check, matching this codebase's established convention for JS-only changes.

## Global Constraints

- Scope is AGRI and APP only. LAND has no live bulk-select UI to fix (see the spec's correction note) and SETF never had one — neither is touched by this plan.
- Selection stays scoped per tab, exactly as today (`_pamBeasiswaSelected` for AGRI, `_fioriSelected`/`_fioriSelectionMeta` for APP — separate variables, no cross-tab sharing built).
- No change to the `bulk-update`/`days-of-pam/bulk-update` API endpoints — only client-side selection bookkeeping changes.
- In-memory JS variables only (no `sessionStorage`/`localStorage`) — Payment Memo's search/filter never reloads the page, so there is nothing to persist across.
- **Shared checkout hazard:** `app/templates/payment_memo/index.html` has uncommitted concurrent-session changes as of plan-writing (a dynamic-pagination-page-size feature and tab full-bleed-layout markup — confirmed via `git diff`, does not overlap the functions this plan touches, but re-verify before editing). Run `git status --porcelain -- app/templates/payment_memo/index.html` and `git diff -- app/templates/payment_memo/index.html` before editing. Never `git add -A`/`git add .`, never `git stash`, never `git checkout <path>`. If unrelated WIP overlaps a hunk you need to change, hand-extract your intended hunk into a standalone patch and stage it with `git apply --check --cached` then `git apply --cached` instead of a blind `git add`.
- Every code snippet below was checked against the current content of `app/templates/payment_memo/index.html` at plan-writing time. Confirm current line numbers with `grep -n` before editing — locate by function/variable name if they've shifted.

---

### Task 1: AGRI — stop wiping selection, decouple chip names, restore visual state

**Files:**
- Modify: `app/templates/payment_memo/index.html` — `loadPAM()` (currently lines 3249-3295), `_agriRenderPage()` (3321-3378), the `_pamBeasiswaCache`/`_pamBeasiswaSelected`/`_pamPendingSelectAll` declarations (3380-3382), `agriFetchBeasiswaLines()` (3396-3484), `agriToggleCheckbox()` (3486-3495), `_agriAllChipsHtml()` (3529-3545), `agriClearAll()` (3617-3627).

**Interfaces:**
- Produces: `_pamBeasiswaSelectionMeta` (`Map<pbId, {pamId, nama}>`) — new module-level variable, consumed only within this file's AGRI functions.

- [ ] **Step 1: Add `_pamBeasiswaSelectionMeta`**

Replace (current lines 3380-3382):

```javascript
let _pamBeasiswaCache = {};
let _pamBeasiswaSelected = {}; // { pamId: Set<pbId> }
let _pamPendingSelectAll = {}; // { pamId: true } saat PAM checkbox diklik sebelum expand
```

with:

```javascript
let _pamBeasiswaCache = {};
let _pamBeasiswaSelected = {}; // { pamId: Set<pbId> }
let _pamPendingSelectAll = {}; // { pamId: true } saat PAM checkbox diklik sebelum expand
// Cache-independent name lookup for chips — _pamBeasiswaCache is legitimately
// cleared on every search (see loadPAM()), but a selected line's chip must
// keep showing its name even after the user searches away from its PAM.
// Populated at the moment a checkbox is checked, from that PAM's just-fetched
// beasiswa-lines data (still present at that moment even if cleared later).
let _pamBeasiswaSelectionMeta = new Map(); // pbId -> { pamId, nama }
```

- [ ] **Step 2: Stop resetting `_pamBeasiswaSelected` in `loadPAM()`**

Replace (current lines 3262-3266):

```javascript
  _pamCache = {};
  _pamBeasiswaCache = {};
  _pamBeasiswaSelected = {};
  _pamPendingSelectAll = {};
  agriUpdateBulkBar();
```

with:

```javascript
  _pamCache = {};
  _pamBeasiswaCache = {};
  _pamPendingSelectAll = {};
  agriUpdateBulkBar();
```

- [ ] **Step 3: Show indeterminate state on master rows with a carried-over selection**

Replace (current lines 3361-3364):

```javascript
  pageRows.forEach(r => {
    const cell = document.getElementById('gl-cell-' + r.id);
    if (cell) cell.appendChild(buildGLDropdown(r.id, r.gl_account));
  });
```

with:

```javascript
  pageRows.forEach(r => {
    const cell = document.getElementById('gl-cell-' + r.id);
    if (cell) cell.appendChild(buildGLDropdown(r.id, r.gl_account));
  });
  // A PAM whose beasiswa lines were partially selected before this search
  // shows its own checkbox as indeterminate even before being expanded —
  // full checked-vs-indeterminate resolution against real sub-rows still
  // only happens once expanded (_syncPamCheckbox()).
  pageRows.forEach(r => {
    if (r.source === 'beasiswa' && _pamBeasiswaSelected[r.id] && _pamBeasiswaSelected[r.id].size > 0) {
      const cb = document.getElementById('pam-cb-' + r.id);
      if (cb) cb.indeterminate = true;
    }
  });
```

- [ ] **Step 4: Restore checked state on normal expand, and populate selection meta**

Replace (current lines 3446-3484):

```javascript
  [...data.rows].reverse().forEach(r => {
    const tr = document.createElement('tr');
    tr.classList.add('agri-detail-rows');
    tr.dataset.pamId = pamId;
    tr.innerHTML =
      `<td class="s0" style="padding:4px 2px;text-align:center;vertical-align:middle">` +
        `<input type="checkbox" data-pb-id="${r.id}" style="cursor:pointer"` +
        ` onchange="agriToggleCheckbox(${pamId}, ${r.id}, this.checked)">` +
      `</td>` +
      `<td class="s1" style="padding:4px 6px;font-size:10px;font-family:monospace;color:#94a3b8;white-space:nowrap;vertical-align:middle">${esc(r.siswa_code || '')}</td>` +
      `<td class="s2" style="padding:4px 8px;font-size:11px;font-weight:600;white-space:nowrap;vertical-align:middle">${esc(r.nama || '—')}</td>` +
      `<td class="s3" style="padding:4px 8px;font-size:11px;color:var(--text-muted);vertical-align:middle">${esc(r.cat1 || '')}${r.cat2 ? ' · ' + esc(r.cat2) : ''}</td>` +
      `<td class="s4" style="padding:4px 8px;font-size:11px;font-weight:700;color:#1a56db;vertical-align:middle;background:#f0f9ff;white-space:nowrap">${fmtRupiah(r.amount)}</td>` +
      `<td colspan="11" style="padding:4px 8px;vertical-align:middle"></td>` +
      `<td style="padding:4px 8px;font-size:11px;white-space:nowrap;vertical-align:middle">${d(r.tgl_pengajuan)}</td>` +
      `<td style="padding:4px 8px;font-size:11px;white-space:nowrap;vertical-align:middle">${d(r.tgl_receive)}</td>` +
      `<td style="padding:4px 8px;font-size:11px;white-space:nowrap;vertical-align:middle">${d(r.tgl_pa)}</td>` +
      `<td style="padding:4px 8px;font-size:11px;white-space:nowrap;vertical-align:middle">${d(r.tgl_final)}</td>` +
      `<td style="padding:4px 8px;font-size:11px;white-space:nowrap;vertical-align:middle;display:none">${d(r.SLA_Date_1_LL)}</td>` +
      `<td style="padding:4px 8px;font-size:11px;white-space:nowrap;vertical-align:middle">${d(r.SLA_Date_2_HT)}</td>` +
      `<td style="padding:4px 8px;font-size:11px;white-space:nowrap;vertical-align:middle">${d(r.SLA_Date_3_YK)}</td>` +
      `<td style="padding:4px 8px;font-size:11px;white-space:nowrap;vertical-align:middle;display:none">${d(r.SLA_Date_4_AK)}</td>` +
      `<td style="padding:4px 8px;font-size:11px;white-space:nowrap;vertical-align:middle;display:none">${d(r.SLA_Date_5_PD)}</td>` +
      `<td style="padding:4px 8px;font-size:11px;white-space:nowrap;vertical-align:middle">${d(r.SLA_Date_6_C2)}</td>` +
      `<td style="padding:4px 8px;font-size:11px;white-space:nowrap;vertical-align:middle;display:none">${d(r.SLA_Date_7_MSIG)}</td>` +
      `<td></td>`;
    masterTr.insertAdjacentElement('afterend', tr);
  });

  toggleEl.innerHTML = '&#9660;';
  if (_pamPendingSelectAll[pamId]) {
    delete _pamPendingSelectAll[pamId];
    if (!_pamBeasiswaSelected[pamId]) _pamBeasiswaSelected[pamId] = new Set();
    document.querySelectorAll(`.agri-detail-rows[data-pam-id="${pamId}"] input[type=checkbox]`)
      .forEach(cb => { cb.checked = true; _pamBeasiswaSelected[pamId].add(parseInt(cb.dataset.pbId)); });
    agriUpdateBulkBar();
    _syncPamCheckbox(pamId);
  }
}
```

with:

```javascript
  [...data.rows].reverse().forEach(r => {
    const tr = document.createElement('tr');
    tr.classList.add('agri-detail-rows');
    tr.dataset.pamId = pamId;
    tr.innerHTML =
      `<td class="s0" style="padding:4px 2px;text-align:center;vertical-align:middle">` +
        `<input type="checkbox" data-pb-id="${r.id}" style="cursor:pointer"` +
        ` onchange="agriToggleCheckbox(${pamId}, ${r.id}, this.checked)">` +
      `</td>` +
      `<td class="s1" style="padding:4px 6px;font-size:10px;font-family:monospace;color:#94a3b8;white-space:nowrap;vertical-align:middle">${esc(r.siswa_code || '')}</td>` +
      `<td class="s2" style="padding:4px 8px;font-size:11px;font-weight:600;white-space:nowrap;vertical-align:middle">${esc(r.nama || '—')}</td>` +
      `<td class="s3" style="padding:4px 8px;font-size:11px;color:var(--text-muted);vertical-align:middle">${esc(r.cat1 || '')}${r.cat2 ? ' · ' + esc(r.cat2) : ''}</td>` +
      `<td class="s4" style="padding:4px 8px;font-size:11px;font-weight:700;color:#1a56db;vertical-align:middle;background:#f0f9ff;white-space:nowrap">${fmtRupiah(r.amount)}</td>` +
      `<td colspan="11" style="padding:4px 8px;vertical-align:middle"></td>` +
      `<td style="padding:4px 8px;font-size:11px;white-space:nowrap;vertical-align:middle">${d(r.tgl_pengajuan)}</td>` +
      `<td style="padding:4px 8px;font-size:11px;white-space:nowrap;vertical-align:middle">${d(r.tgl_receive)}</td>` +
      `<td style="padding:4px 8px;font-size:11px;white-space:nowrap;vertical-align:middle">${d(r.tgl_pa)}</td>` +
      `<td style="padding:4px 8px;font-size:11px;white-space:nowrap;vertical-align:middle">${d(r.tgl_final)}</td>` +
      `<td style="padding:4px 8px;font-size:11px;white-space:nowrap;vertical-align:middle;display:none">${d(r.SLA_Date_1_LL)}</td>` +
      `<td style="padding:4px 8px;font-size:11px;white-space:nowrap;vertical-align:middle">${d(r.SLA_Date_2_HT)}</td>` +
      `<td style="padding:4px 8px;font-size:11px;white-space:nowrap;vertical-align:middle">${d(r.SLA_Date_3_YK)}</td>` +
      `<td style="padding:4px 8px;font-size:11px;white-space:nowrap;vertical-align:middle;display:none">${d(r.SLA_Date_4_AK)}</td>` +
      `<td style="padding:4px 8px;font-size:11px;white-space:nowrap;vertical-align:middle;display:none">${d(r.SLA_Date_5_PD)}</td>` +
      `<td style="padding:4px 8px;font-size:11px;white-space:nowrap;vertical-align:middle">${d(r.SLA_Date_6_C2)}</td>` +
      `<td style="padding:4px 8px;font-size:11px;white-space:nowrap;vertical-align:middle;display:none">${d(r.SLA_Date_7_MSIG)}</td>` +
      `<td></td>`;
    masterTr.insertAdjacentElement('afterend', tr);
    // A normal (not "select all children") partial selection made in a
    // previous search carries over — restore this row's checked state.
    if (_pamBeasiswaSelected[pamId] && _pamBeasiswaSelected[pamId].has(r.id)) {
      const cb = tr.querySelector('input[type=checkbox]');
      if (cb) cb.checked = true;
    }
  });

  toggleEl.innerHTML = '&#9660;';
  if (_pamPendingSelectAll[pamId]) {
    delete _pamPendingSelectAll[pamId];
    if (!_pamBeasiswaSelected[pamId]) _pamBeasiswaSelected[pamId] = new Set();
    document.querySelectorAll(`.agri-detail-rows[data-pam-id="${pamId}"] input[type=checkbox]`)
      .forEach(cb => {
        cb.checked = true;
        const pbId = parseInt(cb.dataset.pbId);
        _pamBeasiswaSelected[pamId].add(pbId);
        const row = data.rows.find(x => x.id === pbId);
        _pamBeasiswaSelectionMeta.set(pbId, { pamId, nama: row ? (row.nama || row.siswa_code || String(pbId)) : String(pbId) });
      });
    agriUpdateBulkBar();
    _syncPamCheckbox(pamId);
  }
}
```

- [ ] **Step 5: Populate/remove selection meta on manual checkbox toggle**

Replace (current lines 3486-3495):

```javascript
function agriToggleCheckbox(pamId, pbId, checked) {
  if (!_pamBeasiswaSelected[pamId]) _pamBeasiswaSelected[pamId] = new Set();
  if (checked) {
    _pamBeasiswaSelected[pamId].add(pbId);
  } else {
    _pamBeasiswaSelected[pamId].delete(pbId);
  }
  agriUpdateBulkBar();
  _syncPamCheckbox(pamId);
}
```

with:

```javascript
function agriToggleCheckbox(pamId, pbId, checked) {
  if (!_pamBeasiswaSelected[pamId]) _pamBeasiswaSelected[pamId] = new Set();
  if (checked) {
    _pamBeasiswaSelected[pamId].add(pbId);
    const cached = _pamBeasiswaCache[pamId];
    const row = Array.isArray(cached) ? cached.find(r => r.id === pbId) : null;
    _pamBeasiswaSelectionMeta.set(pbId, { pamId, nama: row ? (row.nama || row.siswa_code || String(pbId)) : String(pbId) });
  } else {
    _pamBeasiswaSelected[pamId].delete(pbId);
    _pamBeasiswaSelectionMeta.delete(pbId);
  }
  agriUpdateBulkBar();
  _syncPamCheckbox(pamId);
}
```

- [ ] **Step 6: Read chip names from the meta map instead of the (possibly-cleared) cache**

Replace (current lines 3529-3545):

```javascript
function _agriAllChipsHtml() {
  let html = '';
  for (const [pamIdStr, sel] of Object.entries(_pamBeasiswaSelected)) {
    if (!sel || sel.size === 0) continue;
    const pamId = parseInt(pamIdStr);
    const rows = _pamBeasiswaCache[pamId];
    if (!rows || !Array.isArray(rows)) continue;
    rows.filter(r => sel.has(r.id)).forEach(r => {
      const name = esc(r.nama || r.siswa_code || String(r.id));
      html += `<span style="background:#f59e0b;color:#fff;border-radius:99px;padding:2px 9px;font-size:11px;` +
              `display:inline-flex;align-items:center;gap:3px;white-space:nowrap">` +
              `${name}<span onclick="agriRemovePaChip(${pamId},${r.id})" ` +
              `style="cursor:pointer;margin-left:3px;opacity:.85;font-size:10px" title="Hapus dari pilihan">✕</span></span>`;
    });
  }
  return html;
}
```

with:

```javascript
function _agriAllChipsHtml() {
  let html = '';
  for (const [pbId, meta] of _pamBeasiswaSelectionMeta.entries()) {
    html += `<span style="background:#f59e0b;color:#fff;border-radius:99px;padding:2px 9px;font-size:11px;` +
            `display:inline-flex;align-items:center;gap:3px;white-space:nowrap">` +
            `${esc(meta.nama)}<span onclick="agriRemovePaChip(${meta.pamId},${pbId})" ` +
            `style="cursor:pointer;margin-left:3px;opacity:.85;font-size:10px" title="Hapus dari pilihan">✕</span></span>`;
  }
  return html;
}
```

(`agriRemovePaChip` needs no change — it already calls `agriToggleCheckbox(pamId, pbId, false)`, which Step 5 already made responsible for deleting the meta entry too.)

- [ ] **Step 7: Clear selection meta in `agriClearAll()`**

Replace (current lines 3617-3627):

```javascript
function agriClearAll() {
  for (const [pamIdStr, sel] of Object.entries(_pamBeasiswaSelected)) {
    if (!sel || sel.size === 0) continue;
    const pamId = parseInt(pamIdStr);
    sel.clear();
    document.querySelectorAll(`.agri-detail-rows[data-pam-id="${pamId}"] input[type=checkbox]`)
      .forEach(cb => { cb.checked = false; });
    _syncPamCheckbox(pamId);
  }
  agriUpdateBulkBar();
}
```

with:

```javascript
function agriClearAll() {
  for (const [pamIdStr, sel] of Object.entries(_pamBeasiswaSelected)) {
    if (!sel || sel.size === 0) continue;
    const pamId = parseInt(pamIdStr);
    sel.clear();
    document.querySelectorAll(`.agri-detail-rows[data-pam-id="${pamId}"] input[type=checkbox]`)
      .forEach(cb => { cb.checked = false; });
    _syncPamCheckbox(pamId);
  }
  _pamBeasiswaSelectionMeta.clear();
  agriUpdateBulkBar();
}
```

- [ ] **Step 8: Manual verify**

Run the Flask dev server, log in, select a company with AGRI data, open Payment Approval Memo → AGRI tab (needs a PAM with 2+ beasiswa lines, and ideally 2+ PAMs).
1. Expand a PAM, check one of its beasiswa lines. Confirm a chip appears with the student's name and the PAM checkbox becomes indeterminate.
2. Search for a different PAM No (so the first PAM's row disappears from the table). Confirm the chip from step 1 is STILL shown.
3. Clear the search so the first PAM reappears. Confirm its master checkbox shows indeterminate again (collapsed), and expanding it shows the previously-checked line still checked.
4. With that line still checked, check the master PAM checkbox for a *different, not-yet-expanded* PAM (triggers the pending-select-all path) — expand it and confirm ALL its lines are checked and chips appear for each with correct names.
5. Use "✕ Batal" — confirm all chips clear, all checkboxes (expanded or not) reset, and repeating step 1 works cleanly afterward (no stale meta).
6. Use the bulk date-fill controls with a multi-PAM selection spanning two searches — confirm the success toast reports the correct total count.

- [ ] **Step 9: Commit**

```bash
git add app/templates/payment_memo/index.html
git commit -m "fix: persist AGRI bulk-selection across name searches in Payment Approval Memo"
```

---

### Task 2: APP (FIORI) — stop wiping selection, restore checkbox visual state

**Files:**
- Modify: `app/templates/payment_memo/index.html` — `loadFIORI()` (currently lines 2764-2816).

**Interfaces:**
- Consumes: `_fioriSelected` (`Set<id>`), `_fioriSelectionMeta` (`Map<id, {label}>`) — both already exist, unchanged shape.

**Note:** re-check `git status --porcelain -- app/templates/payment_memo/index.html` before editing — same shared-checkout hazard as Task 1, and this task's edits land in a different region of the same file.

- [ ] **Step 1: Stop clearing selection on every search, and restore checked/highlight state at render time**

Replace (current lines 2764-2816):

```javascript
async function loadFIORI() {
  const search  = (document.getElementById('fiori-search')?.value || '').trim();
  const bulan   = (document.getElementById('fiori-filter-bulan')?.value || '');
  const tahun   = (document.getElementById('fiori-filter-tahun')?.value || '');
  const status  = (document.getElementById('fiori-filter-status')?.value || '');
  const source  = (document.getElementById('fiori-filter-source')?.value || '');
  const params  = new URLSearchParams({ search, bulan, tahun, status, source });
  const tbody  = document.getElementById('fiori-tbody');
  tbody.innerHTML = skeletonRows(26);
  const res     = await apiFetch('/payment-memo/by-pillar/APP?' + params);
  if (!res) return;
  const data   = await res.json();
  const count  = document.getElementById('fiori-count');
  _fioriSelected.clear();
  _fioriSelectionMeta.clear();
  fioriUpdateBulkBar();
  if (!data.ok || !data.rows.length) {
    tbody.innerHTML = '<tr><td colspan="26" style="text-align:center;padding:20px;color:var(--text-muted);">Belum ada data APP.</td></tr>';
    if (count) count.textContent = '';
    return;
  }
  if (count) count.textContent = data.rows.length + ' baris';
  tbody.innerHTML = data.rows.map((r, i) => `
    <tr class="fiori-row" data-pam-id="${r.id}" style="background:${i % 2 === 0 ? 'var(--card)' : 'var(--bg)'};"
      ${r.source === 'beasiswa' ? `onclick="fioriToggleExpand(this.querySelector('.fiori-toggle'),${r.id})"` : ''}>
      <td style="padding:6px 8px;text-align:center"><input type="checkbox" class="fiori-cb" data-id="${r.id}" style="cursor:pointer;vertical-align:middle" onclick="event.stopPropagation()" onchange="fioriToggleCb(this)">${r.source === 'beasiswa' ? `<span class="fiori-toggle" style="cursor:pointer;font-size:1rem;color:#3b82f6;font-weight:700;vertical-align:middle;margin-left:4px" onclick="fioriToggleExpand(this,${r.id});event.stopPropagation()">&#9658;</span>` : ''}</td>
      <td style="padding:6px 8px;font-weight:600;font-family:monospace;font-size:11px;white-space:nowrap">${esc(r.pam_no)}</td>
      <td style="padding:6px 8px;white-space:nowrap">${esc(r.pam_date || '-')}</td>
      <td style="padding:6px 8px;font-family:monospace;font-size:11px">${esc(r.gl_account || '-')}</td>
      <td style="padding:6px 8px">${esc(r.requestors_name || '-')}</td>
      <td style="padding:6px 8px;max-width:160px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${esc(r.keterangan||'')}">${esc(r.keterangan || '-')}</td>
      <td style="padding:6px 8px">${esc(r.mata_uang || 'IDR')}</td>
      <td style="padding:6px 8px;text-align:right">${fmtRupiah(r.dpp)}</td>
      <td style="padding:6px 8px;text-align:right">${fmtRupiah(r.ppn)}</td>
      <td style="padding:6px 8px;text-align:right;font-weight:600">${fmtRupiah(r.total_amount)}</td>
      <td style="padding:6px 8px;white-space:nowrap">${esc(r.due_date || '-')}</td>
      <td style="padding:6px 8px">${_statusBadge(r.status)}</td>
      <td style="padding:6px 8px;white-space:nowrap">${esc(r.tanggal_bayar || '-')}</td>
      <td style="padding:6px 8px">${esc(r.source || '-')}</td>
      <td style="padding:6px 8px">${esc(r.no_vendor || '-')}</td>
      <td style="padding:6px 8px">${esc(r.nama_vendor || '-')}</td>
      ${_plDate(r.id,'APP','tgl_terima_doc',r.tgl_terima_doc)}
      ${_plDate(r.id,'APP','tgl_proses',r.tgl_proses)}
      ${_plDate(r.id,'APP','tgl_verifikasi_tax',r.tgl_verifikasi_tax)}
      ${_plDate(r.id,'APP','tgl_approval_1',r.tgl_approval_1)}
      ${_plDate(r.id,'APP','tgl_approval_2',r.tgl_approval_2)}
      ${_plDate(r.id,'APP','tgl_approval_3',r.tgl_approval_3)}
      ${_plDate(r.id,'APP','tgl_kirim',r.tgl_kirim)}
      <td style="padding:6px 8px">${_aksiCell(r)}</td>
    </tr>
  `).join('');
  makeSortable('fiori-table');
}
```

with:

```javascript
async function loadFIORI() {
  const search  = (document.getElementById('fiori-search')?.value || '').trim();
  const bulan   = (document.getElementById('fiori-filter-bulan')?.value || '');
  const tahun   = (document.getElementById('fiori-filter-tahun')?.value || '');
  const status  = (document.getElementById('fiori-filter-status')?.value || '');
  const source  = (document.getElementById('fiori-filter-source')?.value || '');
  const params  = new URLSearchParams({ search, bulan, tahun, status, source });
  const tbody  = document.getElementById('fiori-tbody');
  tbody.innerHTML = skeletonRows(26);
  const res     = await apiFetch('/payment-memo/by-pillar/APP?' + params);
  if (!res) return;
  const data   = await res.json();
  const count  = document.getElementById('fiori-count');
  fioriUpdateBulkBar();
  if (!data.ok || !data.rows.length) {
    tbody.innerHTML = '<tr><td colspan="26" style="text-align:center;padding:20px;color:var(--text-muted);">Belum ada data APP.</td></tr>';
    if (count) count.textContent = '';
    return;
  }
  if (count) count.textContent = data.rows.length + ' baris';
  tbody.innerHTML = data.rows.map((r, i) => {
    const isSel = _fioriSelected.has(r.id);
    return `
    <tr class="fiori-row" data-pam-id="${r.id}" style="background:${isSel ? '#eff6ff' : (i % 2 === 0 ? 'var(--card)' : 'var(--bg)')};"
      ${r.source === 'beasiswa' ? `onclick="fioriToggleExpand(this.querySelector('.fiori-toggle'),${r.id})"` : ''}>
      <td style="padding:6px 8px;text-align:center"><input type="checkbox" class="fiori-cb" data-id="${r.id}" ${isSel ? 'checked' : ''} style="cursor:pointer;vertical-align:middle" onclick="event.stopPropagation()" onchange="fioriToggleCb(this)">${r.source === 'beasiswa' ? `<span class="fiori-toggle" style="cursor:pointer;font-size:1rem;color:#3b82f6;font-weight:700;vertical-align:middle;margin-left:4px" onclick="fioriToggleExpand(this,${r.id});event.stopPropagation()">&#9658;</span>` : ''}</td>
      <td style="padding:6px 8px;font-weight:600;font-family:monospace;font-size:11px;white-space:nowrap">${esc(r.pam_no)}</td>
      <td style="padding:6px 8px;white-space:nowrap">${esc(r.pam_date || '-')}</td>
      <td style="padding:6px 8px;font-family:monospace;font-size:11px">${esc(r.gl_account || '-')}</td>
      <td style="padding:6px 8px">${esc(r.requestors_name || '-')}</td>
      <td style="padding:6px 8px;max-width:160px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${esc(r.keterangan||'')}">${esc(r.keterangan || '-')}</td>
      <td style="padding:6px 8px">${esc(r.mata_uang || 'IDR')}</td>
      <td style="padding:6px 8px;text-align:right">${fmtRupiah(r.dpp)}</td>
      <td style="padding:6px 8px;text-align:right">${fmtRupiah(r.ppn)}</td>
      <td style="padding:6px 8px;text-align:right;font-weight:600">${fmtRupiah(r.total_amount)}</td>
      <td style="padding:6px 8px;white-space:nowrap">${esc(r.due_date || '-')}</td>
      <td style="padding:6px 8px">${_statusBadge(r.status)}</td>
      <td style="padding:6px 8px;white-space:nowrap">${esc(r.tanggal_bayar || '-')}</td>
      <td style="padding:6px 8px">${esc(r.source || '-')}</td>
      <td style="padding:6px 8px">${esc(r.no_vendor || '-')}</td>
      <td style="padding:6px 8px">${esc(r.nama_vendor || '-')}</td>
      ${_plDate(r.id,'APP','tgl_terima_doc',r.tgl_terima_doc)}
      ${_plDate(r.id,'APP','tgl_proses',r.tgl_proses)}
      ${_plDate(r.id,'APP','tgl_verifikasi_tax',r.tgl_verifikasi_tax)}
      ${_plDate(r.id,'APP','tgl_approval_1',r.tgl_approval_1)}
      ${_plDate(r.id,'APP','tgl_approval_2',r.tgl_approval_2)}
      ${_plDate(r.id,'APP','tgl_approval_3',r.tgl_approval_3)}
      ${_plDate(r.id,'APP','tgl_kirim',r.tgl_kirim)}
      <td style="padding:6px 8px">${_aksiCell(r)}</td>
    </tr>
  `;
  }).join('');
  makeSortable('fiori-table');
}
```

(Only two substantive changes from the original: the two `_fioriSelected.clear()`/`_fioriSelectionMeta.clear()` lines are removed, and the `.map((r, i) => \`...\`)` arrow function is changed to a block body that computes `isSel` once and uses it for both the row's background and the checkbox's `checked` attribute. `fioriClearAllSelection()` — the manual "batal" button, elsewhere in the file — is untouched and still the only place besides a successful bulk update that clears these variables.)

- [ ] **Step 2: Manual verify**

Using the same running dev server, open Payment Approval Memo → APP tab (needs 2+ existing PAM records).
1. Search a PAM No, check its row. Confirm the row highlights blue and a chip appears.
2. Change the search so that row disappears. Confirm the chip is STILL shown.
3. Clear the search so the row reappears. Confirm it is still checked AND still highlighted blue (not just checked-but-unstyled).
4. Use "Batalkan Pilihan" (`fioriClearAllSelection`) — confirm it still clears everything as before.
5. Re-select 2 rows across two different searches, then run a bulk date-fill — confirm both rows update correctly.

- [ ] **Step 3: Commit**

```bash
git add app/templates/payment_memo/index.html
git commit -m "fix: persist APP bulk-selection across name searches in Payment Approval Memo"
```

---

### Task 3: Final review

**Files:** None (verification only).

- [ ] **Step 1: Re-read the diff against the spec**

Review the cumulative diff from Tasks 1-2 against `docs/superpowers/specs/2026-08-03-flow-payment-memo-persistent-bulk-selection-design.md` (including its LAND-scope correction) — confirm every design decision (AGRI's selection-meta map, APP's flat restore, LAND/SETF untouched, no `sessionStorage`, no API changes) is reflected in the actual code, and that no unrelated concurrent-session WIP got swept into either commit.

- [ ] **Step 2: Cross-tab independence check**

With a selection active on AGRI, switch to the APP tab and confirm it shows no AGRI-derived state (and vice versa) — confirms the two tabs' selection variables never interact, matching the "no cross-tab sharing" constraint.
