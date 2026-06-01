# Days of PAM Lazy-Load Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the page-load DB query + embedded JSON with two AJAX endpoints so the Days of PAM tab costs zero DB I/O until the user actively searches.

**Architecture:** Two new GET endpoints (`/candidates` returns lightweight autocomplete data, `/search?pam=|nama=` returns full rows). The template fetches candidates once on tab-open, uses them for in-memory autocomplete, then fetches full rows only when user picks a suggestion or clicks Cari. Secondary column filters remain client-side on the already-rendered rows.

**Tech Stack:** Flask (Blueprint), SQLite (`get_conn()`), vanilla JS (`apiFetch` from `static/js/app.js`), Jinja2 (server renders empty tbody — no more data embed), pytest

---

## File Map

| File | Change |
|------|--------|
| `app/modules/payment_memo/service.py` | Add `get_days_of_pam_candidates()` after line 502 |
| `app/modules/payment_memo/routes.py` | Add import; remove `dop_rows` from `index()`; add 2 GET routes |
| `app/templates/payment_memo/index.html` | Remove Jinja loop + DOP_DATA embed; rewrite DOP JS block; wire tab click |
| `app/tests/test_memo_api.py` | Add 5 new tests for the 2 new endpoints |

No new files.

---

## Task 1: Tests for the two new endpoints (write failing first)

**Files:**
- Modify: `app/tests/test_memo_api.py`

Tests hit `/payment-memo/days-of-pam/candidates` and `/payment-memo/days-of-pam/search`.  
These routes don't exist yet, so every test will return 404 — that's the expected failure.

- [ ] **Step 1: Add 5 tests at the bottom of `test_memo_api.py`**

Append after the last test in the file (after `test_days_of_pam_bulk_update_invalid_ids`):

```python
# ── Days of PAM candidates + search ──────────────────────────────────────────

def _seed_dop_row(company_id=2, pam_no="PAM-001-ETF-05-2026",
                  siswa_code="S099", nama="Harry"):
    """Seed one payment_beasiswa row that has a pam value."""
    from database import get_conn
    conn = get_conn()
    conn.execute(
        "INSERT OR IGNORE INTO siswa (company_id, code, nama) VALUES (?,?,?)",
        (company_id, siswa_code, nama)
    )
    conn.execute(
        """INSERT INTO payment_beasiswa
           (company_id, siswa_code, cat1, tanggal, amount, pam)
           VALUES (?,?,?,?,?,?)""",
        (company_id, siswa_code, "General", "2026-05-01", 3000000.0, pam_no)
    )
    conn.commit()
    conn.close()


def test_get_dop_candidates_empty(client):
    token = _login(client)
    with client.session_transaction() as sess:
        sess["company_id"] = 2
    rv = client.get("/payment-memo/days-of-pam/candidates",
                    headers={"Authorization": f"Bearer {token}"})
    assert rv.status_code == 200
    data = rv.get_json()
    assert data["ok"] is True
    assert data["candidates"] == []


def test_get_dop_candidates_with_data(client):
    _seed_dop_row()
    token = _login(client)
    with client.session_transaction() as sess:
        sess["company_id"] = 2
    rv = client.get("/payment-memo/days-of-pam/candidates",
                    headers={"Authorization": f"Bearer {token}"})
    assert rv.status_code == 200
    data = rv.get_json()
    assert data["ok"] is True
    assert len(data["candidates"]) == 1
    c = data["candidates"][0]
    assert c["pam_no"] == "PAM-001-ETF-05-2026"
    assert c["siswa_code"] == "S099"
    assert c["nama"] == "Harry"


def test_dop_search_by_pam(client):
    _seed_dop_row()
    token = _login(client)
    with client.session_transaction() as sess:
        sess["company_id"] = 2
    rv = client.get(
        "/payment-memo/days-of-pam/search?pam=PAM-001-ETF-05-2026",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert rv.status_code == 200
    data = rv.get_json()
    assert data["ok"] is True
    assert len(data["rows"]) == 1
    assert data["rows"][0]["siswa_code"] == "S099"
    assert data["rows"][0]["pam_no"] == "PAM-001-ETF-05-2026"


def test_dop_search_by_nama(client):
    _seed_dop_row()
    token = _login(client)
    with client.session_transaction() as sess:
        sess["company_id"] = 2
    rv = client.get(
        "/payment-memo/days-of-pam/search?nama=harry",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert rv.status_code == 200
    data = rv.get_json()
    assert data["ok"] is True
    assert len(data["rows"]) == 1
    assert data["rows"][0]["siswa_code"] == "S099"


def test_dop_search_no_match(client):
    _seed_dop_row()
    token = _login(client)
    with client.session_transaction() as sess:
        sess["company_id"] = 2
    rv = client.get(
        "/payment-memo/days-of-pam/search?pam=NOPE-999",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert rv.status_code == 200
    data = rv.get_json()
    assert data["ok"] is True
    assert data["rows"] == []
```

- [ ] **Step 2: Run tests to confirm they all fail with 404**

```
cd C:\Financehub\app
python -m pytest tests/test_memo_api.py::test_get_dop_candidates_empty tests/test_memo_api.py::test_get_dop_candidates_with_data tests/test_memo_api.py::test_dop_search_by_pam tests/test_memo_api.py::test_dop_search_by_nama tests/test_memo_api.py::test_dop_search_no_match -v
```

Expected: 5 FAILED (404 Not Found — routes don't exist yet)

---

## Task 2: Add `get_days_of_pam_candidates()` to service.py

**Files:**
- Modify: `app/modules/payment_memo/service.py` — insert after line 502

- [ ] **Step 1: Insert the new function after `get_days_of_pam()`**

In `service.py`, find the block that ends at line 502 (`return rows`) and is followed by two blank lines and `def bulk_update_dates`. Insert the new function between them:

```python
def get_days_of_pam_candidates(company_id: int) -> list:
    """Lightweight SELECT for autocomplete — only 3 fields, DISTINCT rows."""
    conn = get_conn()
    rows = [dict(r) for r in conn.execute(
        """SELECT DISTINCT
               pb.pam        AS pam_no,
               pb.siswa_code,
               s.nama
           FROM payment_beasiswa pb
           LEFT JOIN siswa s
                  ON s.company_id = pb.company_id AND s.code = pb.siswa_code
           WHERE pb.company_id = ?
             AND pb.pam IS NOT NULL AND pb.pam != ''
           ORDER BY pb.pam""",
        (company_id,)
    ).fetchall()]
    conn.close()
    return rows
```

The result after editing that region of service.py:

```python
def get_days_of_pam(company_id: int) -> list:
    conn = get_conn()
    rows = [dict(r) for r in conn.execute(
        """SELECT pb.id, pb.siswa_code, s.nama,
                  pb.pam        AS pam_no,
                  pb.cat1, pb.cat2, pb.perusahaan, pb.pillar,
                  pb.amount,    pb.tanggal,
                  pb.tgl_pengajuan, pb.tgl_receive,
                  pb.tgl_pa,    pb.tgl_final
           FROM payment_beasiswa pb
           LEFT JOIN siswa s
                  ON s.company_id = pb.company_id AND s.code = pb.siswa_code
           WHERE pb.company_id = ?
             AND pb.pam IS NOT NULL AND pb.pam != ''
           ORDER BY pb.tanggal DESC""",
        (company_id,)
    ).fetchall()]
    conn.close()
    return rows


def get_days_of_pam_candidates(company_id: int) -> list:
    """Lightweight SELECT for autocomplete — only 3 fields, DISTINCT rows."""
    conn = get_conn()
    rows = [dict(r) for r in conn.execute(
        """SELECT DISTINCT
               pb.pam        AS pam_no,
               pb.siswa_code,
               s.nama
           FROM payment_beasiswa pb
           LEFT JOIN siswa s
                  ON s.company_id = pb.company_id AND s.code = pb.siswa_code
           WHERE pb.company_id = ?
             AND pb.pam IS NOT NULL AND pb.pam != ''
           ORDER BY pb.pam""",
        (company_id,)
    ).fetchall()]
    conn.close()
    return rows


def bulk_update_dates(ids: list, dates: dict, company_id: int) -> dict:
    ...
```

- [ ] **Step 2: Verify no syntax errors**

```
cd C:\Financehub\app
python -c "from modules.payment_memo.service import get_days_of_pam_candidates; print('OK')"
```

Expected output: `OK`

---

## Task 3: Add new routes + update `index()` in routes.py

**Files:**
- Modify: `app/modules/payment_memo/routes.py`

Three changes in one file: update import, strip `dop_rows` from `index()`, add 2 routes.

- [ ] **Step 1: Update the import line at the top of routes.py**

Current line 4–14:
```python
from modules.payment_memo.service import (
    get_draft_payments, create_memo, get_memo_list, get_memo_detail,
    update_memo_status, export_memo_pdf,
    get_pam_list, get_coa_list, update_pam_gl_account,
    update_pam_status, update_pam_record,
    get_pam_detail, get_pam_payments, get_pam_payments_detail,
    update_pam_and_application,
    get_draft_payment_detail, update_draft_and_linked,
    delete_payment_beasiswa, cancel_pam_record,
    get_days_of_pam, bulk_update_dates,
)
```

Replace with (adds `get_days_of_pam_candidates`):
```python
from modules.payment_memo.service import (
    get_draft_payments, create_memo, get_memo_list, get_memo_detail,
    update_memo_status, export_memo_pdf,
    get_pam_list, get_coa_list, update_pam_gl_account,
    update_pam_status, update_pam_record,
    get_pam_detail, get_pam_payments, get_pam_payments_detail,
    update_pam_and_application,
    get_draft_payment_detail, update_draft_and_linked,
    delete_payment_beasiswa, cancel_pam_record,
    get_days_of_pam, get_days_of_pam_candidates, bulk_update_dates,
)
```

- [ ] **Step 2: Strip `dop_rows` from `index()`**

Current `index()` function body:
```python
    company_id = session["company_id"]
    memos      = get_memo_list(company_id)
    drafts     = get_draft_payments(company_id)
    dop_rows   = get_days_of_pam(company_id)
    return render_template(
        "payment_memo/index.html",
        memos=memos,
        drafts=drafts,
        dop_rows=dop_rows,
        cat1_list=config.CAT1_BGT,
        ...
    )
```

Replace with (remove the `dop_rows` line and `dop_rows=dop_rows,` kwarg):
```python
    company_id = session["company_id"]
    memos      = get_memo_list(company_id)
    drafts     = get_draft_payments(company_id)
    return render_template(
        "payment_memo/index.html",
        memos=memos,
        drafts=drafts,
        cat1_list=config.CAT1_BGT,
        cat2_list=config.CAT2_SEM,
        active_page="payment_memo",
        pam_approved_by_1=config.PAM_APPROVED_BY_1,
        pam_approved_by_2=config.PAM_APPROVED_BY_2,
        **_ctx()
    )
```

- [ ] **Step 3: Add two new GET routes after `days_of_pam_bulk_update` (around line 265)**

Insert these two routes directly after the `days_of_pam_bulk_update` function and before `cancel_pam_route`:

```python
@bp.route("/days-of-pam/candidates")
@role_required("requester", "verificator", "releaser")
def days_of_pam_candidates_route():
    company_id = session.get("company_id")
    if not company_id:
        return jsonify({"ok": False, "pesan": "Perusahaan belum dipilih."}), 400
    return jsonify({"ok": True, "candidates": get_days_of_pam_candidates(company_id)})


@bp.route("/days-of-pam/search")
@role_required("requester", "verificator", "releaser")
def days_of_pam_search_route():
    company_id = session.get("company_id")
    if not company_id:
        return jsonify({"ok": False, "pesan": "Perusahaan belum dipilih."}), 400
    pam  = request.args.get("pam",  "").strip()
    nama = request.args.get("nama", "").strip().lower()
    if not pam and not nama:
        return jsonify({"ok": True, "rows": []})
    rows = get_days_of_pam(company_id)
    if pam:
        rows = [r for r in rows if r["pam_no"] == pam]
    if nama:
        rows = [r for r in rows if nama in (r["nama"] or "").lower()]
    return jsonify({"ok": True, "rows": rows})
```

- [ ] **Step 4: Run the 5 new tests — they should now pass**

```
cd C:\Financehub\app
python -m pytest tests/test_memo_api.py::test_get_dop_candidates_empty tests/test_memo_api.py::test_get_dop_candidates_with_data tests/test_memo_api.py::test_dop_search_by_pam tests/test_memo_api.py::test_dop_search_by_nama tests/test_memo_api.py::test_dop_search_no_match -v
```

Expected: 5 PASSED

- [ ] **Step 5: Run the full test suite**

```
cd C:\Financehub\app
python -m pytest tests/ -v
```

Expected: all tests pass (119+ green, 0 failures)

- [ ] **Step 6: Commit**

```
cd C:\Financehub
git add app/modules/payment_memo/service.py app/modules/payment_memo/routes.py app/tests/test_memo_api.py
git commit -m "feat: add Days of PAM lazy-load endpoints (candidates + search)"
```

---

## Task 4: Rewrite template — remove Jinja embed, AJAX-driven JS

**Files:**
- Modify: `app/templates/payment_memo/index.html`

This task has four sub-changes:
1. Add `onclick` hook to the Days of PAM tab button
2. Replace the Jinja `{% for r in dop_rows %}` loop with an empty tbody
3. Add a "Cari" button to the search bar
4. Rewrite the entire `// ── Days of PAM ──` JS block

- [ ] **Step 1: Wire tab button to `dopTabOpened()`**

Find the Days of PAM tab button (around line 27):
```html
    <button class="tab-btn" data-tab="tab-days-of-pam">Days of PAM</button>
```

Replace with:
```html
    <button class="tab-btn" data-tab="tab-days-of-pam" onclick="dopTabOpened()">Days of PAM</button>
```

- [ ] **Step 2: Add "Cari" button to the search controls**

Find the search buttons row (around line 201–208). The current block looks like:
```html
      <div style="display:flex;align-items:center;gap:8px;padding-bottom:1px">
        <button onclick="dopClearSearch()"
                style="padding:6px 12px;background:#f1f5f9;border:1px solid #cbd5e1;border-radius:5px;font-size:12px;cursor:pointer">
          🗑 Bersihkan
        </button>
        <button id="dop-update-btn" onclick="dopBulkUpdate()" disabled
                style="padding:6px 14px;background:#1d4ed8;color:#fff;border:none;border-radius:5px;font-size:12px;cursor:pointer;font-weight:600;opacity:0.5">
          Update Terpilih (0)
        </button>
```

Replace with (adds "Cari" button before "Bersihkan"):
```html
      <div style="display:flex;align-items:center;gap:8px;padding-bottom:1px">
        <button onclick="_dopFetchCurrent()"
                style="padding:6px 14px;background:#0f766e;color:#fff;border:none;border-radius:5px;font-size:12px;cursor:pointer;font-weight:600">
          🔍 Cari
        </button>
        <button onclick="dopClearSearch()"
                style="padding:6px 12px;background:#f1f5f9;border:1px solid #cbd5e1;border-radius:5px;font-size:12px;cursor:pointer">
          🗑 Bersihkan
        </button>
        <button id="dop-update-btn" onclick="dopBulkUpdate()" disabled
                style="padding:6px 14px;background:#1d4ed8;color:#fff;border:none;border-radius:5px;font-size:12px;cursor:pointer;font-weight:600;opacity:0.5">
          Update Terpilih (0)
        </button>
```

- [ ] **Step 3: Replace the Jinja tbody loop with an empty tbody**

Find this block (around lines 263–295):
```html
        <tbody id="dop-tbody" style="display:none">
          {% for r in dop_rows %}
          <tr class="dop-row"
              data-id="{{ r.id }}"
              ...multiple lines...
          </tr>
          {% else %}
          <tr><td colspan="14" style="padding:20px;text-align:center;color:#6b7280">Belum ada data Days of PAM.</td></tr>
          {% endfor %}
        </tbody>
```

Replace with:
```html
        <tbody id="dop-tbody" style="display:none">
        </tbody>
```

- [ ] **Step 4: Rewrite the entire Days of PAM JS block**

Find the block that starts with:
```javascript
// ── Days of PAM ───────────────────────────────────────────────────────────────
const DOP_DATA = {{ dop_rows | tojson }};
```

and ends just before:
```javascript
// ── Init ─────────────────────────────────────────────────────────────────────
```

Replace the entire DOP block with:

```javascript
// ── Days of PAM ───────────────────────────────────────────────────────────────
let _dopCandidates  = null;   // cached after first tab open
let _dopLoaded      = false;  // true once candidates fetched
let _dopLastSearchQs = '';    // last search query string (to refresh after bulk update)
const _dopSelected  = new Set();

function _dopReveal() {
  const tb = document.getElementById('dop-tbody');
  const ph = document.getElementById('dop-ph');
  if (tb) tb.style.display = '';
  if (ph) ph.style.display = 'none';
}

function _dopHide() {
  const tb = document.getElementById('dop-tbody');
  const ph = document.getElementById('dop-ph');
  if (tb) tb.style.display = 'none';
  if (ph) ph.style.display = '';
}

async function dopTabOpened() {
  if (_dopLoaded) return;
  _dopLoaded = true;
  const res = await apiFetch('/payment-memo/days-of-pam/candidates');
  if (!res) return;
  const data = await res.json();
  if (data.ok) _dopCandidates = data.candidates;
}

function dopRenderRows(rows) {
  const tb = document.getElementById('dop-tbody');
  if (!tb) return;
  if (!rows.length) {
    tb.innerHTML = '<tr><td colspan="14" style="padding:20px;text-align:center;color:#6b7280">Tidak ada data untuk pencarian ini.</td></tr>';
    _dopReveal();
    _dopUpdateInfo(0);
    return;
  }
  tb.innerHTML = rows.map(r => `
    <tr class="dop-row"
        data-id="${r.id}"
        data-code="${(r.siswa_code||'').toLowerCase()}"
        data-nama="${(r.nama||'').toLowerCase()}"
        data-pam="${(r.pam_no||'').toLowerCase()}"
        data-cat1="${(r.cat1||'').toLowerCase()}"
        data-cat2="${(r.cat2||'').toLowerCase()}"
        data-perusahaan="${(r.perusahaan||'').toLowerCase()}"
        data-pillar="${(r.pillar||'').toLowerCase()}"
        style="border-bottom:1px solid #f1f5f9">
      <td style="padding:6px;text-align:center">
        <input type="checkbox" class="dop-cb" data-id="${r.id}" onchange="dopToggleCb(this)">
      </td>
      <td style="padding:6px 8px">${r.siswa_code||''}</td>
      <td style="padding:6px 8px">${r.nama||'-'}</td>
      <td style="padding:6px 8px;font-family:monospace;color:#1d4ed8">${r.pam_no||''}</td>
      <td style="padding:6px 8px">${r.cat1||''}</td>
      <td style="padding:6px 8px">${r.cat2||''}</td>
      <td style="padding:6px 8px">${r.perusahaan||''}</td>
      <td style="padding:6px 8px">${r.pillar||''}</td>
      <td style="padding:6px 8px;text-align:right">Rp ${new Intl.NumberFormat('id-ID').format(r.amount||0)}</td>
      <td style="padding:6px 8px">${r.tanggal||''}</td>
      <td style="padding:6px 8px">${r.tgl_pengajuan||''}</td>
      <td style="padding:6px 8px">${r.tgl_receive||''}</td>
      <td style="padding:6px 8px">${r.tgl_pa||''}</td>
      <td style="padding:6px 8px">${r.tgl_final||''}</td>
    </tr>`).join('');
  _dopSelected.clear();
  const sa = document.getElementById('dop-select-all');
  if (sa) sa.checked = false;
  _dopReveal();
  _dopUpdateInfo(rows.length);
  // re-apply any active secondary filters
  dopFilter();
}

async function _dopFetch(qs) {
  _dopLastSearchQs = qs;
  const res = await apiFetch(`/payment-memo/days-of-pam/search?${qs}`);
  if (!res) return;
  const data = await res.json();
  if (data.ok) dopRenderRows(data.rows);
  else showToast(data.pesan || 'Gagal memuat data.', 'error');
}

function _dopFetchCurrent() {
  const pam  = (document.getElementById('dop-s-pam')?.value  || '').trim();
  const nama = (document.getElementById('dop-s-nama')?.value || '').trim();
  if (!pam && !nama) { _dopHide(); return; }
  const parts = [];
  if (pam)  parts.push(`pam=${encodeURIComponent(pam)}`);
  if (nama) parts.push(`nama=${encodeURIComponent(nama)}`);
  _dopFetch(parts.join('&'));
}

function dopFilter() {
  // Secondary client-side filter on already-rendered <tr> rows
  const fCode  = (document.getElementById('dop-f-code')?.value       || '').trim().toLowerCase();
  const fCat1  = (document.getElementById('dop-f-cat1')?.value       || '').trim().toLowerCase();
  const fCat2  = (document.getElementById('dop-f-cat2')?.value       || '').trim().toLowerCase();
  const fPersh = (document.getElementById('dop-f-perusahaan')?.value || '').trim().toLowerCase();
  const fPill  = (document.getElementById('dop-f-pillar')?.value     || '').trim().toLowerCase();

  let visible = 0;
  document.querySelectorAll('#dop-tbody .dop-row').forEach(row => {
    const match =
      (!fCode  || row.dataset.code.includes(fCode))           &&
      (!fCat1  || row.dataset.cat1.includes(fCat1))           &&
      (!fCat2  || row.dataset.cat2.includes(fCat2))           &&
      (!fPersh || row.dataset.perusahaan.includes(fPersh))    &&
      (!fPill  || row.dataset.pillar.includes(fPill));
    row.style.display = match ? '' : 'none';
    if (match) visible++;
    // uncheck hidden rows
    if (!match) {
      const cb = row.querySelector('.dop-cb');
      if (cb && cb.checked) { cb.checked = false; _dopSelected.delete(parseInt(cb.dataset.id, 10)); }
    }
  });
  _dopUpdateInfo(visible);
}

function dopSrchInput(type) {
  const inp  = document.getElementById(type === 'pam' ? 'dop-s-pam' : 'dop-s-nama');
  const sugg = document.getElementById(type === 'pam' ? 'dop-sugg-pam' : 'dop-sugg-nama');
  const val  = inp.value.trim().toLowerCase();

  if (!val || !_dopCandidates) { sugg.style.display = 'none'; return; }

  const field = type === 'pam' ? 'pam_no' : 'nama';
  const seen  = new Set();
  const hits  = _dopCandidates.filter(r => {
    const v = (r[field] || '').toLowerCase();
    if (v.includes(val) && !seen.has(r[field])) { seen.add(r[field]); return true; }
    return false;
  }).slice(0, 12);

  sugg.innerHTML = hits.length
    ? hits.map(r => {
        const v = type === 'pam' ? r.pam_no : r.nama;
        const label = type === 'pam'
          ? `<span style="font-family:monospace;font-size:12px">${r.pam_no}</span>`
          : `<span style="font-size:12px">${r.nama}</span>&nbsp;<span style="color:#94a3b8;font-size:11px">(${r.siswa_code})</span>`;
        return `<div onmousedown="dopPickSugg('${type}',${JSON.stringify(v)})"
                     style="padding:7px 10px;cursor:pointer;border-bottom:1px solid #f8fafc"
                     onmouseover="this.style.background='#eff6ff'" onmouseout="this.style.background=''">${label}</div>`;
      }).join('')
    : `<div style="padding:7px 10px;font-size:12px;color:#9ca3af">Tidak ada hasil</div>`;

  sugg.style.display = '';
}

function dopPickSugg(type, value) {
  document.getElementById(type === 'pam' ? 'dop-s-pam' : 'dop-s-nama').value = value;
  document.getElementById(type === 'pam' ? 'dop-sugg-pam' : 'dop-sugg-nama').style.display = 'none';
  _dopFetchCurrent();
}

function dopSrchBlur(type) {
  setTimeout(() => {
    const el = document.getElementById(type === 'pam' ? 'dop-sugg-pam' : 'dop-sugg-nama');
    if (el) el.style.display = 'none';
  }, 200);
}

function dopClearSearch() {
  ['dop-s-pam','dop-s-nama'].forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });
  document.querySelectorAll('.dop-filter').forEach(el => el.value = '');
  _dopSelected.clear();
  _dopLastSearchQs = '';
  const sa = document.getElementById('dop-select-all');
  if (sa) sa.checked = false;
  _dopHide();
  const info = document.getElementById('dop-info');
  if (info) info.textContent = '';
}

function dopToggleCb(cb) {
  const id = parseInt(cb.dataset.id, 10);
  if (cb.checked) _dopSelected.add(id);
  else            _dopSelected.delete(id);
  _dopUpdateInfo();
}

function dopToggleSelectAll(masterCb) {
  document.querySelectorAll('#dop-tbody .dop-row').forEach(row => {
    if (row.style.display === 'none') return;
    const cb = row.querySelector('.dop-cb');
    if (!cb) return;
    cb.checked = masterCb.checked;
    const id = parseInt(cb.dataset.id, 10);
    if (masterCb.checked) _dopSelected.add(id);
    else                  _dopSelected.delete(id);
  });
  _dopUpdateInfo();
}

function _dopUpdateInfo(visibleOverride) {
  const totalVisible = visibleOverride !== undefined
    ? visibleOverride
    : document.querySelectorAll('#dop-tbody .dop-row:not([style*="display: none"])').length;
  const sel  = _dopSelected.size;
  const info = document.getElementById('dop-info');
  if (info) info.textContent = `${sel} dipilih | ${totalVisible} baris`;
  const btn  = document.getElementById('dop-update-btn');
  if (!btn) return;
  btn.textContent = `Update Terpilih (${sel})`;
  btn.disabled    = sel === 0;
  btn.style.opacity = sel === 0 ? '0.5' : '1';
}

async function dopBulkUpdate() {
  if (_dopSelected.size === 0) return;
  const dates = {
    tanggal:       document.getElementById('dop-d-tanggal').value,
    tgl_pengajuan: document.getElementById('dop-d-pengajuan').value,
    tgl_receive:   document.getElementById('dop-d-receive').value,
    tgl_pa:        document.getElementById('dop-d-pa').value,
    tgl_final:     document.getElementById('dop-d-final').value,
  };
  const hasDate = Object.values(dates).some(v => v);
  if (!hasDate) { showToast('Isi minimal satu field tanggal.', 'error'); return; }

  const res  = await apiFetch('/payment-memo/days-of-pam/bulk-update', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ids: [..._dopSelected], dates })
  });
  if (!res) return;
  const data = await res.json();
  showToast(data.pesan, data.ok ? 'success' : 'error');
  if (data.ok && _dopLastSearchQs) {
    // refresh current search results instead of full page reload
    setTimeout(() => _dopFetch(_dopLastSearchQs), 600);
  }
}
```

- [ ] **Step 5: Wire `dopTabOpened()` to the DOMContentLoaded init block**

Find the `// ── Init ──` block (around line 1025):
```javascript
document.addEventListener('DOMContentLoaded', () => {
  const pamBtn = document.querySelector('[data-tab="tab-pam"]');
  if (pamBtn) pamBtn.addEventListener('click', loadPAM);
  // Close cat2 panel on outside click
  ...
});
```

Add one line after the pamBtn listener:
```javascript
document.addEventListener('DOMContentLoaded', () => {
  const pamBtn = document.querySelector('[data-tab="tab-pam"]');
  if (pamBtn) pamBtn.addEventListener('click', loadPAM);
  const dopBtn = document.querySelector('[data-tab="tab-days-of-pam"]');
  if (dopBtn) dopBtn.addEventListener('click', dopTabOpened);
  // Close cat2 panel on outside click
  ...
});
```

Note: `dopTabOpened()` is idempotent — it does nothing on second click because of the `if (_dopLoaded) return` guard. The `onclick="dopTabOpened()"` attribute added in Step 1 and this listener are redundant but harmless. Prefer the listener approach — remove the `onclick` attribute from Step 1 if desired, but leaving both is safe.

- [ ] **Step 6: Run the full test suite**

```
cd C:\Financehub\app
python -m pytest tests/ -v
```

Expected: all tests pass. The template Jinja change (removing `dop_rows` variable) will be caught here if the template still references `dop_rows` anywhere — the test that loads the index page would error with `UndefinedError`.

If you see `jinja2.exceptions.UndefinedError: 'dop_rows' is undefined`, search the template for any remaining `dop_rows` references with:
```
grep -n "dop_rows" app/templates/payment_memo/index.html
```
and remove them.

- [ ] **Step 7: Commit**

```
cd C:\Financehub
git add app/templates/payment_memo/index.html
git commit -m "feat: Days of PAM tab — lazy-load via AJAX, remove page-load DB query"
```

---

## Self-Review

### Spec coverage check

| Spec requirement | Task |
|---|---|
| Remove `dop_rows` from `index()` | Task 3, Step 2 |
| Add `get_days_of_pam_candidates()` | Task 2 |
| Add `GET /days-of-pam/candidates` | Task 3, Step 3 |
| Add `GET /days-of-pam/search?pam=\|nama=` | Task 3, Step 3 |
| Remove Jinja loop from tbody | Task 4, Step 3 |
| Remove `DOP_DATA = {{ dop_rows \| tojson }}` | Task 4, Step 4 |
| `dopTabOpened()` — fetch candidates once | Task 4, Step 4 |
| `dopRenderRows(rows)` — build `<tr>` from JSON | Task 4, Step 4 |
| `dopPickSugg` triggers AJAX fetch (not filter) | Task 4, Step 4 |
| "Cari" button fallback | Task 4, Step 2 |
| Secondary subheader filters remain client-side | Task 4, Step 4 (`dopFilter`) |
| `dopBulkUpdate` re-fetches instead of page reload | Task 4, Step 4 |
| 5 new tests for 2 new endpoints | Task 1 |

All requirements covered. ✓

### Placeholder scan

No TBD, TODO, or incomplete steps found. ✓

### Type consistency

- `_dopCandidates` array: set in `dopTabOpened`, read in `dopSrchInput` ✓
- `_dopLastSearchQs` string: set in `_dopFetch`, read in `dopBulkUpdate` ✓
- `_dopFetchCurrent()` calls `_dopFetch(qs)` — both defined ✓
- `dopRenderRows(rows)` called from `_dopFetch` with `data.rows` — same field name as route returns ✓
- Route returns `{"ok": true, "rows": [...]}` and `{"ok": true, "candidates": [...]}` — matches JS accesses ✓
