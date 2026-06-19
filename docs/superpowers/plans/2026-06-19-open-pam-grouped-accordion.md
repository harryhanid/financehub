# Open PAM Grouped Accordion — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the flat Jinja loop in the Open PAM tab with a JS-rendered grouped accordion — one master row per PAM number, expandable inline to show per-item detail rows.

**Architecture:** Client-side only — the Python route already passes `drafts` (flat list of `payment_beasiswa` rows with `status='open'`) to the template; a new `const OPEN_PAM_DRAFTS` constant exposes this to JS; `renderOpenPAM()` groups and renders the accordion on page load. No backend changes (no new routes, no service changes).

**Tech Stack:** Vanilla JS, Jinja2 template (Flask), SQLite via existing service layer, pytest for route render test.

---

## File Map

| File | Change |
|---|---|
| `app/templates/payment_memo/index.html` | Primary: replace Jinja `tbody` loop (lines 50–75), update `thead` (lines 41–47), remove Jinja `tfoot` (lines 77–88), add `const OPEN_PAM_DRAFTS` after line 1068, rewrite `toggleAllDrafts`, add CSS, add 6 JS functions, add memo bar HTML |
| `app/tests/test_payment_memo_open_pam.py` | New: route render test verifying `OPEN_PAM_DRAFTS` exists in response body |

---

## Baseline

Before starting, confirm:
```
cd C:\Financehub
python -m pytest app/tests/ -q 2>&1 | tail -5
```
Expected: `221 passed, 1 failed` (`test_get_next_pam_no_sml_uses_sml_prefix` — pre-existing, skip).

---

### Task 1: Add `OPEN_PAM_DRAFTS` data injection + route render test

**Files:**
- Create: `app/tests/test_payment_memo_open_pam.py`
- Modify: `app/templates/payment_memo/index.html:1068`

- [ ] **Step 1: Write the failing test**

Create `app/tests/test_payment_memo_open_pam.py`:

```python
# app/tests/test_payment_memo_open_pam.py


def _login(client):
    r = client.post("/auth/login", json={"username": "admin", "password": "Admin@123"})
    return r


def _select_company(client):
    client.post("/select-company", data={"company_id": "2"})


def test_open_pam_page_exposes_drafts_json(client):
    """Open PAM tab must contain OPEN_PAM_DRAFTS JS constant for client-side grouping."""
    _login(client)
    _select_company(client)
    resp = client.get("/payment-memo/")
    assert resp.status_code == 200
    assert b"OPEN_PAM_DRAFTS" in resp.data
```

- [ ] **Step 2: Run test to confirm it fails**

```
cd C:\Financehub
python -m pytest app/tests/test_payment_memo_open_pam.py::test_open_pam_page_exposes_drafts_json -v
```

Expected: `FAILED — AssertionError` (string not yet in template)

- [ ] **Step 3: Add `const OPEN_PAM_DRAFTS` to template**

In `app/templates/payment_memo/index.html`, find the constants block around line 1068:

```javascript
const SPESIALISASI_LIST = SPESIALISASI_MEDICAL;
```

Add the new constant immediately after that line:

```javascript
const OPEN_PAM_DRAFTS = {{ drafts | tojson }};
```

- [ ] **Step 4: Run test to confirm it passes**

```
python -m pytest app/tests/test_payment_memo_open_pam.py::test_open_pam_page_exposes_drafts_json -v
```

Expected: `PASSED`

- [ ] **Step 5: Commit**

```bash
git add app/tests/test_payment_memo_open_pam.py app/templates/payment_memo/index.html
git commit -m "feat: expose OPEN_PAM_DRAFTS constant for client-side accordion grouping"
```

---

### Task 2: Add CSS for accordion styles

**Files:**
- Modify: `app/templates/payment_memo/index.html` — find the `<style>` block (search for `{% block styles %}` or a bare `<style>` tag in the file) and append before its closing `</style>`

- [ ] **Step 1: Find the CSS insertion point**

```bash
grep -n "<style\|{% block styles" app/templates/payment_memo/index.html | head -5
```

Use that line as anchor. Add the following CSS block just before the `</style>` closing tag (or at the end of the styles block).

- [ ] **Step 2: Add accordion CSS**

```css
/* ── Open PAM accordion ── */
.pam-master-row { cursor: pointer; }
.pam-master-row:hover { background: var(--hover-bg, #f8fafc); }
.pam-detail-row { display: none; background: #f8fafc; }
.pam-detail-row.expanded { display: table-row; }
.pam-toggle { font-size: .75rem; color: var(--text-muted); margin-right: .25rem; user-select: none; }
.badge-agri  { background: #fef3c7; color: #92400e; border: 1px solid #d97706; border-radius: .25rem; padding: .1rem .35rem; }
.badge-app   { background: #ede9fe; color: #4c1d95; border: 1px solid #7c3aed; border-radius: .25rem; padding: .1rem .35rem; }
.badge-land  { background: #d1fae5; color: #064e3b; border: 1px solid #059669; border-radius: .25rem; padding: .1rem .35rem; }
.badge-setf  { background: #cffafe; color: #164e63; border: 1px solid #0891b2; border-radius: .25rem; padding: .1rem .35rem; }
.pam-unassigned-row { background: #fef3c7 !important; }
#pam-memo-bar {
  display: none;
  position: sticky;
  bottom: 0;
  background: #1e40af;
  color: #fff;
  padding: .6rem 1rem;
  border-radius: .5rem .5rem 0 0;
  margin-top: .75rem;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}
#pam-memo-bar.visible { display: flex; }
```

- [ ] **Step 3: Commit**

```bash
git add app/templates/payment_memo/index.html
git commit -m "feat: add CSS for open PAM accordion rows, pillar badges, memo bar"
```

---

### Task 3: Add JS helper functions

**Files:**
- Modify: `app/templates/payment_memo/index.html` — add after `function toggleAllDrafts` (around line 1079)

- [ ] **Step 1: Add three helpers after `toggleAllDrafts`**

```javascript
function groupDraftsByPAM(drafts) {
  const groups = {};
  const UNASSIGNED = '__unassigned__';
  drafts.forEach(function(d) {
    var key = (d.pam && d.pam !== '--') ? d.pam : UNASSIGNED;
    if (!groups[key]) groups[key] = { pam: key, items: [], total: 0, minDate: d.tanggal };
    groups[key].items.push(d);
    groups[key].total += d.amount;
    if (d.tanggal < groups[key].minDate) groups[key].minDate = d.tanggal;
  });
  var keys = Object.keys(groups).filter(function(k) { return k !== UNASSIGNED; }).sort();
  if (groups[UNASSIGNED]) keys.push(UNASSIGNED);
  return keys.map(function(k) { return groups[k]; });
}

function buildKeterangan(items, max) {
  max = max || 3;
  var names = items.map(function(d) { return d.nama || d.siswa_code || '--'; });
  if (names.length <= max) return names.join(', ');
  return names.slice(0, max).join(', ') + ' (+' + (names.length - max) + ' lagi)';
}

function getPillarFromPamNo(pamNo) {
  if (!pamNo || pamNo === '--') return null;
  var prefix = pamNo.split('/')[0].toUpperCase();
  var map = { AGRI: 'agri', APP: 'app', LAND: 'land', SML: 'land', SETF: 'setf' };
  return map[prefix] || null;
}
```

- [ ] **Step 2: Commit**

```bash
git add app/templates/payment_memo/index.html
git commit -m "feat: add groupDraftsByPAM, buildKeterangan, getPillarFromPamNo helpers"
```

---

### Task 4: Add `togglePAMRow` and `renderOpenPAM`

**Files:**
- Modify: `app/templates/payment_memo/index.html` — add after the three helpers from Task 3

- [ ] **Step 1: Add `togglePAMRow`**

```javascript
function togglePAMRow(key) {
  var escaped = CSS.escape(key);
  var detailRows = document.querySelectorAll('.pam-detail-row[data-pam-key="' + escaped + '"]');
  var toggle = document.querySelector('.pam-toggle[data-pam-key="' + escaped + '"]');
  var isOpen = detailRows.length > 0 && detailRows[0].classList.contains('expanded');
  detailRows.forEach(function(r) { r.classList.toggle('expanded', !isOpen); });
  if (toggle) toggle.textContent = isOpen ? '▶' : '▼';
}
```

- [ ] **Step 2: Add `renderOpenPAM`**

```javascript
function renderOpenPAM(drafts) {
  var tbody = document.getElementById('open-pam-tbody');
  if (!tbody) return;
  if (!drafts || drafts.length === 0) {
    tbody.innerHTML = '<tr><td colspan="9" style="text-align:center;color:var(--text-muted);padding:2rem">Tidak ada payment draft.</td></tr>';
    return;
  }
  var groups = groupDraftsByPAM(drafts);
  var grandTotal = 0;
  var html = '';

  groups.forEach(function(g) {
    var isUnassigned = g.pam === '__unassigned__';
    var pamLabel = isUnassigned ? '— Belum di-assign —' : g.pam;
    var pillar = isUnassigned ? null : getPillarFromPamNo(g.pam);
    var badgeHtml = pillar
      ? '<span class="badge badge-' + pillar + '" style="font-size:.7rem">' + pillar.toUpperCase() + '</span>'
      : '<span class="badge badge-gray" style="font-size:.7rem">—</span>';
    var keterangan = buildKeterangan(g.items, 3);
    var masterClass = isUnassigned ? 'pam-master-row pam-unassigned-row' : 'pam-master-row';
    var pamKeyAttr = esc(g.pam);

    // Hidden per-item checkboxes keep memo-creation data in DOM
    var hiddenChecks = g.items.map(function(d) {
      return '<input type="checkbox" class="draft-check" style="display:none"' +
        ' data-id="' + d.id + '"' +
        ' data-desc="' + esc((d.cat1 || '') + ' / ' + (d.cat2 || '') + ' -- ' + (d.siswa_code || '')) + '"' +
        ' data-amount="' + d.amount + '"' +
        ' data-vendor="' + esc(d.namarek || d.nama || '') + '"' +
        ' data-bank="' + esc((d.bank || '') + ' ' + (d.norek || '')) + '"' +
        ' data-pam-group="' + pamKeyAttr + '">';
    }).join('');

    html += '<tr class="' + masterClass + '"' +
      ' data-pam-key="' + pamKeyAttr + '"' +
      ' onclick="togglePAMRow(this.dataset.pamKey)">' +
      '<td>' +
        '<input type="checkbox" class="pam-check"' +
        ' data-pam-key="' + pamKeyAttr + '"' +
        ' onclick="event.stopPropagation()" onchange="pamCbChange(this)">' +
        hiddenChecks +
      '</td>' +
      '<td><span class="pam-toggle" data-pam-key="' + pamKeyAttr + '">▶</span></td>' +
      '<td><code style="font-size:.8rem;color:#2563eb">' + esc(pamLabel) + '</code></td>' +
      '<td>' + badgeHtml + '</td>' +
      '<td>' + esc(g.minDate || '--') + '</td>' +
      '<td style="max-width:220px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="' + esc(buildKeterangan(g.items, 100)) + '">' + esc(keterangan) + '</td>' +
      '<td style="text-align:center">' + g.items.length + '</td>' +
      '<td class="num-right">' + fmtRupiah(g.total) + '</td>' +
      '<td><span class="badge badge-gray" style="font-size:.75rem">Open</span></td>' +
      '</tr>';
    grandTotal += g.total;

    // One detail row per item (hidden, expanded on toggle)
    g.items.forEach(function(d) {
      html += '<tr class="pam-detail-row" data-pam-key="' + pamKeyAttr + '">' +
        '<td></td><td></td>' +
        '<td><code style="font-size:.75rem">' + esc(d.siswa_code || '--') + '</code></td>' +
        '<td>' + esc(d.nama || '--') + '</td>' +
        '<td>' + esc((d.cat1 || '') + ' / ' + (d.cat2 || '')) + '</td>' +
        '<td>' + esc(d.tanggal || '--') + '</td>' +
        '<td></td>' +
        '<td class="num-right">' + fmtRupiah(d.amount) + '</td>' +
        '<td style="white-space:nowrap">' +
          '<button class="btn btn-secondary btn-sm" onclick="openEditDraft(' + d.id + ');event.stopPropagation()">Edit</button> ' +
          '<button class="btn btn-danger btn-sm" onclick="deleteDraft(' + d.id + ');event.stopPropagation()">Hapus</button>' +
        '</td>' +
        '</tr>';
    });
  });

  // Grand total row
  html += '<tr style="background:#f1f5f9;font-weight:700">' +
    '<td colspan="7" style="text-align:right;padding:.5rem .75rem">Grand Total</td>' +
    '<td class="num-right" style="padding:.5rem .75rem">' + fmtRupiah(grandTotal) + '</td>' +
    '<td></td></tr>';

  tbody.innerHTML = html;
}
```

- [ ] **Step 3: Commit**

```bash
git add app/templates/payment_memo/index.html
git commit -m "feat: add togglePAMRow and renderOpenPAM accordion renderer"
```

---

### Task 5: Add checkbox propagation functions and update `toggleAllDrafts`

**Files:**
- Modify: `app/templates/payment_memo/index.html:1076–1078`

- [ ] **Step 1: Replace `toggleAllDrafts` and add `pamCbChange` + `updatePamMemoBar`**

Replace the existing `toggleAllDrafts` (lines 1076–1078):
```javascript
function toggleAllDrafts(cb) {
  document.querySelectorAll(".draft-check").forEach(c => { c.checked = cb.checked; });
}
```

With:
```javascript
function toggleAllDrafts(cb) {
  document.querySelectorAll('.pam-check').forEach(function(pc) {
    pc.checked = cb.checked;
    var key = pc.dataset.pamKey;
    document.querySelectorAll('.draft-check[data-pam-group="' + key + '"]')
      .forEach(function(c) { c.checked = cb.checked; });
  });
  updatePamMemoBar();
}

function pamCbChange(pamCb) {
  var key = pamCb.dataset.pamKey;
  document.querySelectorAll('.draft-check[data-pam-group="' + key + '"]')
    .forEach(function(c) { c.checked = pamCb.checked; });
  updatePamMemoBar();
}

function updatePamMemoBar() {
  var bar = document.getElementById('pam-memo-bar');
  if (!bar) return;
  var checked = document.querySelectorAll('.pam-check:checked');
  var countEl = bar.querySelector('.pam-memo-count');
  if (checked.length > 0) {
    bar.classList.add('visible');
    if (countEl) countEl.textContent = checked.length + ' PAM dipilih';
  } else {
    bar.classList.remove('visible');
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add app/templates/payment_memo/index.html
git commit -m "feat: add pamCbChange, updatePamMemoBar; update toggleAllDrafts for PAM grouping"
```

---

### Task 6: Replace Jinja table structure + add memo bar + call `renderOpenPAM`

This is the main structural change. Replace lines 41–91 of `#tab-draft-pay`'s table and add the memo bar.

**Files:**
- Modify: `app/templates/payment_memo/index.html:41–91`

- [ ] **Step 1: Replace the table section (lines 41–91)**

Replace this entire block (from `<table>` through `</table>` including the Jinja `tfoot`):

```html
      <table>
        <thead>
          <tr>
            <th><input type="checkbox" id="select-all-drafts" onchange="toggleAllDrafts(this)"></th>
            <th>Code</th><th>Nama Siswa</th><th>Kategori</th><th>Tanggal</th>
            <th>PAM No</th><th>Perusahaan</th><th class="num-right">Amount</th><th>Status</th>
            <th>Aksi</th>
          </tr>
        </thead>
        <tbody>
          {% for d in drafts %}
          ...10 columns of <tr>...
          {% else %}
          <tr><td colspan="10"...>...</td></tr>
          {% endfor %}
        </tbody>
        {% if drafts %}
        <tfoot>
          <tr style="background:#f1f5f9; font-weight:700;">
            ...
          </tr>
        </tfoot>
        {% endif %}
      </table>
```

With the new structure (9 columns — no Perusahaan column, add toggle + Keterangan + Jml):

```html
      <table>
        <thead>
          <tr>
            <th><input type="checkbox" id="select-all-drafts" onchange="toggleAllDrafts(this)"></th>
            <th></th>
            <th>PAM No</th>
            <th>Pillar</th>
            <th>Tanggal</th>
            <th>Keterangan (Nama)</th>
            <th class="num-right">Jml</th>
            <th class="num-right">Total</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody id="open-pam-tbody">
          <tr><td colspan="9" style="text-align:center;color:var(--text-muted);padding:2rem">
            <span style="opacity:.5">Memuat…</span>
          </td></tr>
        </tbody>
      </table>
```

- [ ] **Step 2: Add memo bar after `.table-wrap` closing div**

The `.table-wrap` div closes at the original line 90 (`</div>`). After `</div>` (end of `.table-wrap`) and before `</div>` (end of `#tab-draft-pay`), insert:

```html
    <div id="pam-memo-bar">
      <span class="pam-memo-count">0 PAM dipilih</span>
      <span style="font-size:.85rem;opacity:.85">— centang PAM untuk buat memo</span>
      <button class="btn btn-secondary btn-sm"
              style="background:#fff;color:#1e40af;border:none;margin-left:auto"
              onclick="document.getElementById('select-all-drafts').checked=false;toggleAllDrafts({checked:false})">
        Batal
      </button>
    </div>
```

- [ ] **Step 3: Add `renderOpenPAM` init call at end of `<script>` block**

Find the last few lines of the `<script>` block (just before the closing `</script>` tag) and append:

```javascript
// Render Open PAM accordion on page load
renderOpenPAM(OPEN_PAM_DRAFTS);
```

- [ ] **Step 4: Run the full test suite**

```
python -m pytest app/tests/ -q 2>&1 | tail -10
```

Expected: `222 passed, 1 failed` (the pre-existing SML prefix test).

- [ ] **Step 5: Commit**

```bash
git add app/templates/payment_memo/index.html
git commit -m "feat: replace flat Jinja loop with JS accordion in Open PAM tab"
```

---

### Task 7: Manual smoke test + final commit

- [ ] **Step 1: Start Flask server**

```
cd C:\Financehub
python run.py
```

Open `http://localhost:5000/payment-memo/` in the browser.

- [ ] **Step 2: Smoke test checklist**

Check each item:
- [ ] Open PAM tab shows master rows (one per PAM number)
- [ ] Clicking a master row expands detail rows inline; clicking again collapses
- [ ] Toggle icon changes `▶` → `▼` on expand
- [ ] Pillar badge shows correct color (AGRI=amber, APP=purple, LAND=green, SETF=cyan)
- [ ] Keterangan column shows student names, truncated at 3 with `(+N lagi)`
- [ ] Items without PAM appear in a separate `⚠ Belum di-assign` group at the bottom
- [ ] Checking a PAM checkbox shows the `#pam-memo-bar` at the bottom
- [ ] Unchecking all PAMs hides the memo bar
- [ ] "Select All" header checkbox checks/unchecks all PAM checkboxes
- [ ] Edit button in detail row opens the edit modal (calls `openEditDraft()`)
- [ ] Hapus button in detail row shows confirmation and deletes (calls `deleteDraft()`)
- [ ] Empty state shows "Tidak ada payment draft." when no drafts exist
- [ ] Grand total row appears at bottom of table

- [ ] **Step 3: Run final test suite**

```
python -m pytest app/tests/ -v 2>&1 | tail -20
```

Expected: `222 passed, 1 failed`

- [ ] **Step 4: Final commit**

```bash
git add app/templates/payment_memo/index.html app/tests/test_payment_memo_open_pam.py
git commit -m "test: smoke test passed — open PAM accordion complete"
```

---

## Edge Case Reference

| Kasus | Handling (dalam `renderOpenPAM`) |
|---|---|
| `drafts` kosong | Early return, render "Tidak ada payment draft." |
| PAM No null / `''` / `'--'` | Key = `__unassigned__`, masuk grup "Belum di-assign" |
| Nama siswa null | Fallback ke `siswa_code`, lalu `'--'` |
| PAM hanya 1 item | Render normal — expand tetap menampilkan 1 detail row |
| PAM No yang tidak dikenal prefix-nya | `getPillarFromPamNo` return null → badge `—` abu-abu |
| Semua items punya PAM No | Grup "Belum di-assign" tidak muncul |
