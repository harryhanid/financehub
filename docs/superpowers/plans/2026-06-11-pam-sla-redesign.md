# PAM SLA Tab Redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor tab SLA (Days of PAM) dari fetch-all+Python-filter menjadi smart default view — langsung tampil data belum paid, filter source (AGRI/APP) via SQL JOIN, pagination load-more.

**Architecture:** Backend `get_days_of_pam()` menerima params (source, paid_only, pam, nama, limit, offset) dan memfilter di SQL via JOIN `pam_records`. Frontend menggantikan lazy-load pattern dengan auto-load saat tab dibuka, menambah source toggle pills, paid-only checkbox, dan load-more button.

**Tech Stack:** Python/SQLite (backend), Vanilla JS + HTML (frontend), pytest (tests)

**Spec:** `docs/superpowers/specs/2026-06-11-pam-sla-redesign.md`

---

## File Map

| File | Perubahan |
|------|-----------|
| `app/tests/test_payment_memo_sla.py` | **Create** — unit tests untuk `get_days_of_pam()` baru |
| `app/modules/payment_memo/service.py` | **Modify** — refactor `get_days_of_pam()` baris 692–716 |
| `app/modules/payment_memo/routes.py` | **Modify** — update `days_of_pam_search_route()` baris 289–304 |
| `app/templates/payment_memo/index.html` | **Modify** — source toggle HTML, JS state + logic |

---

## Task 1: Tulis tests untuk `get_days_of_pam()` baru

**Files:**
- Create: `app/tests/test_payment_memo_sla.py`

- [ ] **Step 1: Buat file test**

```python
# app/tests/test_payment_memo_sla.py
import os, sys, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config
config.DB_PATH = os.path.join(os.path.dirname(__file__), "test_sla.db")

from database import init_db, get_conn
from modules.payment_memo.service import get_days_of_pam

COMPANY_ID = 2  # ETF

@pytest.fixture(autouse=True)
def clean_db():
    if os.path.exists(config.DB_PATH):
        os.remove(config.DB_PATH)
    init_db()
    _seed(get_conn())
    yield
    if os.path.exists(config.DB_PATH):
        os.remove(config.DB_PATH)

def _seed(conn):
    conn.execute("INSERT INTO siswa (company_id, code, nama) VALUES (?,?,?)",
                 (COMPANY_ID, "S001", "Budi Santoso"))
    conn.execute("INSERT INTO siswa (company_id, code, nama) VALUES (?,?,?)",
                 (COMPANY_ID, "S002", "Siti Rahayu"))
    conn.execute("INSERT INTO pam_records (company_id, pam_no, source, status, created_at) VALUES (?,?,?,?,?)",
                 (COMPANY_ID, "PAM-001-AGRI", "etf_agri", "open", "2026-01-01"))
    conn.execute("INSERT INTO pam_records (company_id, pam_no, source, status, created_at) VALUES (?,?,?,?,?)",
                 (COMPANY_ID, "PAM-002-AGRI", "etf_agri", "open", "2026-01-02"))
    conn.execute("INSERT INTO pam_records (company_id, pam_no, source, status, created_at) VALUES (?,?,?,?,?)",
                 (COMPANY_ID, "PAM-003-APP",  "etf_app",  "open", "2026-01-03"))
    # AGRI unpaid
    conn.execute(
        "INSERT INTO payment_beasiswa (company_id, siswa_code, pam, tanggal, amount, status) VALUES (?,?,?,?,?,?)",
        (COMPANY_ID, "S001", "PAM-001-AGRI", "2026-01-01", 5000000, "open"))
    # AGRI paid
    conn.execute(
        "INSERT INTO payment_beasiswa (company_id, siswa_code, pam, tanggal, amount, status, tgl_Paid_AGRI) VALUES (?,?,?,?,?,?,?)",
        (COMPANY_ID, "S002", "PAM-002-AGRI", "2026-01-02", 3000000, "open", "2026-02-01"))
    # APP unpaid
    conn.execute(
        "INSERT INTO payment_beasiswa (company_id, siswa_code, pam, tanggal, amount, status) VALUES (?,?,?,?,?,?)",
        (COMPANY_ID, "S001", "PAM-003-APP", "2026-01-03", 2000000, "open"))
    conn.commit()
    conn.close()


def test_default_returns_agri_unpaid_only():
    result = get_days_of_pam(COMPANY_ID)
    assert result["total"] == 1
    assert len(result["rows"]) == 1
    assert result["rows"][0]["pam_no"] == "PAM-001-AGRI"


def test_paid_only_false_returns_all_agri():
    result = get_days_of_pam(COMPANY_ID, paid_only=False)
    assert result["total"] == 2
    pam_nos = {r["pam_no"] for r in result["rows"]}
    assert pam_nos == {"PAM-001-AGRI", "PAM-002-AGRI"}


def test_source_app_returns_app_records():
    result = get_days_of_pam(COMPANY_ID, source="APP", paid_only=False)
    assert result["total"] == 1
    assert result["rows"][0]["pam_no"] == "PAM-003-APP"


def test_source_app_unpaid_excludes_nothing_extra():
    result = get_days_of_pam(COMPANY_ID, source="APP", paid_only=True)
    assert result["total"] == 1  # APP row has no tgl_Paid_APP set


def test_pam_search_filter():
    result = get_days_of_pam(COMPANY_ID, source="AGRI", paid_only=False, pam="PAM-002")
    assert result["total"] == 1
    assert result["rows"][0]["pam_no"] == "PAM-002-AGRI"


def test_nama_search_filter():
    result = get_days_of_pam(COMPANY_ID, source="AGRI", paid_only=False, nama="budi")
    assert result["total"] == 1
    assert result["rows"][0]["siswa_code"] == "S001"


def test_pagination_limit():
    result = get_days_of_pam(COMPANY_ID, source="AGRI", paid_only=False, limit=1, offset=0)
    assert result["total"] == 2
    assert len(result["rows"]) == 1


def test_pagination_offset():
    result = get_days_of_pam(COMPANY_ID, source="AGRI", paid_only=False, limit=1, offset=1)
    assert result["total"] == 2
    assert len(result["rows"]) == 1


def test_unknown_source_defaults_to_agri():
    result = get_days_of_pam(COMPANY_ID, source="UNKNOWN", paid_only=False)
    assert result["total"] == 2  # falls back to AGRI


def test_different_company_isolated():
    result = get_days_of_pam(company_id=1, source="AGRI", paid_only=False)
    assert result["total"] == 0
```

- [ ] **Step 2: Jalankan test untuk konfirmasi FAIL**

```
cd app && python -m pytest tests/test_payment_memo_sla.py -v
```

Expected: FAIL — `TypeError` karena `get_days_of_pam` belum menerima parameter baru.

- [ ] **Step 3: Commit test file**

```bash
git add app/tests/test_payment_memo_sla.py
git commit -m "test: add failing tests for get_days_of_pam refactor (source/paid_only/pagination)"
```

---

## Task 2: Refactor `get_days_of_pam()` di service.py

**Files:**
- Modify: `app/modules/payment_memo/service.py` (fungsi `get_days_of_pam`, baris ~692)

- [ ] **Step 1: Ganti seluruh fungsi `get_days_of_pam`**

Temukan dan replace blok berikut (baris 692–716):

```python
def get_days_of_pam(company_id: int) -> list:
    conn = get_conn()
    rows = [dict(r) for r in conn.execute(
        """SELECT pb.id, pb.siswa_code, s.nama,
                  pb.pam        AS pam_no,
                  ...
           WHERE pb.company_id = ?
             AND pb.pam IS NOT NULL AND pb.pam != ''
           ORDER BY pb.tanggal DESC""",
        (company_id,)
    ).fetchall()]
    conn.close()
    return rows
```

Ganti dengan:

```python
_SOURCE_MAP = {
    "AGRI": {"pr_source": "etf_agri", "paid_col": "tgl_Paid_AGRI"},
    "APP":  {"pr_source": "etf_app",  "paid_col": "tgl_Paid_APP"},
}


def get_days_of_pam(
    company_id: int,
    source: str = "AGRI",
    paid_only: bool = True,
    pam: str = None,
    nama: str = None,
    limit: int = 100,
    offset: int = 0,
) -> dict:
    src       = _SOURCE_MAP.get(source.upper(), _SOURCE_MAP["AGRI"])
    pr_source = src["pr_source"]
    paid_col  = src["paid_col"]

    conditions = [
        "pb.company_id = ?",
        "pb.pam IS NOT NULL",
        "pb.pam != ''",
        "pr.source = ?",
    ]
    params = [company_id, pr_source]

    if paid_only:
        conditions.append(f'pb."{paid_col}" IS NULL')
    if pam:
        conditions.append("pb.pam LIKE ?")
        params.append(f"%{pam}%")
    if nama:
        conditions.append("LOWER(s.nama) LIKE ?")
        params.append(f"%{nama.lower()}%")

    where = " AND ".join(conditions)
    base_from = f"""
        FROM payment_beasiswa pb
        LEFT JOIN siswa s
               ON s.company_id = pb.company_id AND s.code = pb.siswa_code
        JOIN pam_records pr
               ON pr.pam_no = pb.pam AND pr.company_id = pb.company_id
        WHERE {where}
    """

    conn  = get_conn()
    total = conn.execute(f"SELECT COUNT(*) {base_from}", params).fetchone()[0]
    rows  = [dict(r) for r in conn.execute(
        f"""SELECT pb.id, pb.siswa_code, s.nama,
                  pb.pam AS pam_no,
                  pb.cat1, pb.cat2, pb.perusahaan, pb.pillar,
                  pb.amount, pb.tanggal,
                  pb.tgl_pengajuan, pb.tgl_receive,
                  pb.tgl_pa, pb.tgl_final,
                  pb.tgl_retur, pb.tgl_final6, pb.tgl_proses,
                  pb.tgl_HT_AGRI, pb.tgl_Yurike_AGRI, pb.tgl_Aditya_AGRI,
                  pb.tgl_Pedy_AGRI, pb.tgl_C2_AGRI, pb.tgl_MSIG_AGRI,
                  pb.tgl_Paid_AGRI,
                  pb."tgl_A-GS_APP", pb."tgl_A-HJK_APP",
                  pb.tgl_ASPIRO_APP, pb.tgl_Paid_APP
           {base_from}
           ORDER BY pb.tanggal DESC
           LIMIT ? OFFSET ?""",
        params + [limit, offset]
    ).fetchall()]
    conn.close()
    return {"rows": rows, "total": total}
```

- [ ] **Step 2: Jalankan test untuk konfirmasi PASS**

```
cd app && python -m pytest tests/test_payment_memo_sla.py -v
```

Expected: semua 10 test PASS.

- [ ] **Step 3: Pastikan test lama tidak rusak**

```
cd app && python -m pytest tests/ -v
```

Expected: semua test PASS (tidak ada regresi).

- [ ] **Step 4: Commit**

```bash
git add app/modules/payment_memo/service.py
git commit -m "refactor: get_days_of_pam — server-side filtering via SQL JOIN pam_records"
```

---

## Task 3: Update route `days_of_pam_search_route()`

**Files:**
- Modify: `app/modules/payment_memo/routes.py` (baris ~289–304)

- [ ] **Step 1: Ganti fungsi route**

Temukan dan replace blok `days_of_pam_search_route`:

```python
@bp.route("/days-of-pam/search")
@jwt_html_required
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
        rows = [r for r in rows if pam.lower() in (r["pam_no"] or "").lower()]
    if nama:
        rows = [r for r in rows if nama in (r["nama"] or "").lower()]
    return jsonify({"ok": True, "rows": rows})
```

Ganti dengan:

```python
@bp.route("/days-of-pam/search")
@jwt_html_required
def days_of_pam_search_route():
    company_id = session.get("company_id")
    if not company_id:
        return jsonify({"ok": False, "pesan": "Perusahaan belum dipilih."}), 400
    source    = request.args.get("source",    "AGRI").strip().upper()
    paid_only = request.args.get("paid_only", "1") == "1"
    pam       = request.args.get("pam",  "").strip() or None
    nama      = request.args.get("nama", "").strip() or None
    offset    = max(0, int(request.args.get("offset", 0) or 0))
    result    = get_days_of_pam(
        company_id, source=source, paid_only=paid_only,
        pam=pam, nama=nama, limit=100, offset=offset
    )
    return jsonify({"ok": True, "rows": result["rows"], "total": result["total"],
                    "limit": 100, "offset": offset})
```

- [ ] **Step 2: Verifikasi import di routes.py sudah include `get_days_of_pam`**

Cek baris `from .service import ...` di atas file — pastikan `get_days_of_pam` sudah ada. Jika belum, tambahkan.

- [ ] **Step 3: Commit**

```bash
git add app/modules/payment_memo/routes.py
git commit -m "refactor: days-of-pam/search endpoint — accept source/paid_only/offset, remove Python filtering"
```

---

## Task 4: Frontend HTML — source toggle, paid-only checkbox, load-more

**Files:**
- Modify: `app/templates/payment_memo/index.html`

- [ ] **Step 1: Tambah source toggle dan paid-only checkbox di atas filter-bar**

Temukan blok `<!-- Days of PAM Tab -->` (sekitar baris 239). Di dalam `<div class="tab-panel" id="tab-days-of-pam">`, **sebelum** `<div class="filter-bar">`, tambahkan:

```html
    <!-- Source toggle + paid-only -->
    <div style="display:flex;align-items:center;gap:8px;padding:8px 10px;border-bottom:1px solid #e5e7eb;flex-wrap:wrap">
      <div id="dop-source-toggle" style="display:flex;gap:4px">
        <button class="dop-src-btn dop-src-active" data-src="AGRI" onclick="dopSetSource('AGRI')"
                style="padding:4px 12px;border:1px solid #2563eb;border-radius:20px;background:#2563eb;color:#fff;font-size:12px;font-weight:600;cursor:pointer">AGRI</button>
        <button class="dop-src-btn" data-src="APP" onclick="dopSetSource('APP')"
                style="padding:4px 12px;border:1px solid #d1d5db;border-radius:20px;background:#fff;color:#374151;font-size:12px;font-weight:600;cursor:pointer">APP</button>
      </div>
      <label style="display:flex;align-items:center;gap:5px;font-size:12px;color:#374151;cursor:pointer;margin-left:8px">
        <input type="checkbox" id="dop-paid-only" checked onchange="dopSetPaidOnly(this.checked)"
               style="cursor:pointer">
        Belum Paid saja
      </label>
      <span id="dop-count-label" style="font-size:11px;color:#6b7280;margin-left:auto"></span>
    </div>
```

- [ ] **Step 2: Tambah load-more button setelah closing `</table>`**

Temukan `</table>` di dalam `#tab-days-of-pam` (setelah `</tbody>`). Tambahkan setelah `</div>` yang menutup `overflow-x:auto`:

```html
    <div id="dop-load-more-wrap" style="display:none;text-align:center;padding:10px">
      <button id="dop-load-more" class="btn btn-secondary btn-sm" onclick="dopLoadMore()" style="font-size:12px">
        Muat 100 lagi
      </button>
    </div>
```

- [ ] **Step 3: Tambah CSS class pada `<th>` kolom AGRI dan APP di `<thead>`**

Di thead, temukan kolom AGRI (dari `tgl_HT_AGRI` s.d. `tgl_Paid_AGRI`) dan kolom APP (`tgl_A-GS_APP` s.d. `tgl_Paid_APP`). Tambahkan `class="dop-col-agri"` ke 7 `<th>` AGRI dan `class="dop-col-app"` ke 4 `<th>` APP.

Contoh perubahan (ulangi pola ini untuk semua 11 kolom source-specific):

```html
<!-- SEBELUM: -->
<th style="padding:7px 8px;text-align:left;white-space:nowrap">tgl_HT_AGRI</th>

<!-- SESUDAH: -->
<th class="dop-col-agri" style="padding:7px 8px;text-align:left;white-space:nowrap">tgl_HT_AGRI</th>
```

Kolom AGRI (tambah `class="dop-col-agri"`):
- `tgl_HT_AGRI`, `tgl_Yurike_AGRI`, `tgl_Aditya_AGRI`, `tgl_Pedy_AGRI`, `tgl_C2_AGRI`, `tgl_MSIG_AGRI`, `tgl_Paid_AGRI`

Kolom APP (tambah `class="dop-col-app"`):
- `tgl_A-GS_APP`, `tgl_A-HJK_APP`, `tgl_ASPIRO_APP`, `tgl_Paid_APP`

Lakukan hal yang sama pada `<td>` di subheader row (yang berisi `<input id="dop-d-ht-agri">` dst).

- [ ] **Step 4: Commit HTML changes**

```bash
git add app/templates/payment_memo/index.html
git commit -m "feat(sla): add source toggle pills, paid-only checkbox, load-more button HTML"
```

---

## Task 5: Frontend JS — state variables + core logic refactor

**Files:**
- Modify: `app/templates/payment_memo/index.html` (seksi JS Days of PAM, ~baris 1679)

- [ ] **Step 1: Ganti blok state variables**

Temukan (sekitar baris 1679–1684):
```javascript
// ── Days of PAM ───────────────────────────────────────────────────────────────
let _dopCandidates  = null;   // cached after first tab open
let _dopLoaded      = false;  // true once candidates fetched
let _dopLastSearchQs = '';    // last search query string (to refresh after bulk update)
const _dopSelected     = new Set();
const _dopSelectionMeta = new Map();  // id → { nama, cat1 }
```

Ganti dengan:
```javascript
// ── Days of PAM ───────────────────────────────────────────────────────────────
let _dopCandidates   = null;
let _dopInitialized  = false;
let _dopSource       = 'AGRI';
let _dopPaidOnly     = true;
let _dopOffset       = 0;
let _dopTotal        = 0;
const _dopSelected      = new Set();
const _dopSelectionMeta = new Map();  // id → { nama, cat1 }
```

- [ ] **Step 2: Ganti `dopTabOpened()`**

Temukan fungsi `dopTabOpened` (sekitar baris 1700):
```javascript
async function dopTabOpened() {
  if (_dopLoaded) return;
  _dopLoaded = true;
  const res = await apiFetch('/payment-memo/days-of-pam/candidates');
  if (!res) return;
  const data = await res.json();
  if (data.ok) _dopCandidates = data.candidates;
}
```

Ganti dengan:
```javascript
async function dopTabOpened() {
  if (_dopInitialized) return;
  _dopInitialized = true;
  const cres = await apiFetch('/payment-memo/days-of-pam/candidates');
  if (cres) { const cd = await cres.json(); if (cd.ok) _dopCandidates = cd.candidates; }
  await _dopFetch(false);
}
```

- [ ] **Step 3: Ganti `_dopFetch()`**

Temukan fungsi `_dopFetch` (sekitar baris 1773):
```javascript
async function _dopFetch(qs) {
  _dopLastSearchQs = qs;
  const res = await apiFetch(`/payment-memo/days-of-pam/search?${qs}`);
  if (!res) return;
  const data = await res.json();
  if (data.ok) dopRenderRows(data.rows);
  else showToast(data.pesan || 'Gagal memuat data.', 'error');
}
```

Ganti dengan:
```javascript
async function _dopFetch(append = false) {
  const pam  = (document.getElementById('dop-s-pam')?.value  || '').trim();
  const nama = (document.getElementById('dop-s-nama')?.value || '').trim();
  const currentOffset = append ? _dopOffset : 0;

  const params = new URLSearchParams({
    source:    _dopSource,
    paid_only: _dopPaidOnly ? '1' : '0',
    offset:    String(currentOffset),
  });
  if (pam)  params.set('pam',  pam);
  if (nama) params.set('nama', nama);

  if (!append) {
    const tb = document.getElementById('dop-tbody');
    if (tb) tb.innerHTML = '<tr><td colspan="28" style="padding:20px;text-align:center;color:#6b7280">Memuat data...</td></tr>';
    _dopReveal();
  }

  const res = await apiFetch(`/payment-memo/days-of-pam/search?${params}`);
  if (!res) return;
  const data = await res.json();
  if (!data.ok) { showToast(data.pesan || 'Gagal memuat data.', 'error'); return; }

  _dopTotal = data.total;
  if (append) _dopOffset += data.rows.length;
  else        _dopOffset  = data.rows.length;

  dopRenderRows(data.rows, append, data.total);
}
```

- [ ] **Step 4: Ganti `dopRenderRows()`**

Temukan fungsi `dopRenderRows` (sekitar baris 1709):
```javascript
function dopRenderRows(rows) {
  ...
}
```

Ganti dengan:
```javascript
function dopRenderRows(rows, append = false, total = 0) {
  const tb = document.getElementById('dop-tbody');
  if (!tb) return;

  if (!append && !rows.length) {
    const msg = _dopPaidOnly
      ? `Tidak ada record ${_dopSource} yang belum paid.`
      : `Tidak ada data untuk filter ini.`;
    tb.innerHTML = `<tr><td colspan="28" style="padding:20px;text-align:center;color:#6b7280">${msg}</td></tr>`;
    _dopReveal();
    _dopUpdateInfo(0);
    _dopUpdateLoadMore(0, total);
    return;
  }

  const html = rows.map(r => {
    const sel = _dopSelected.has(r.id);
    const rowBg  = sel ? 'background:#eff6ff;' : '';
    const nameSt = sel ? 'color:#1d4ed8;font-weight:600;' : '';
    return `
      <tr class="dop-row"
          data-id="${r.id}"
          data-code="${(r.siswa_code||'').toLowerCase()}"
          data-nama="${(r.nama||'').toLowerCase()}"
          data-pam="${(r.pam_no||'').toLowerCase()}"
          data-cat1="${(r.cat1||'').toLowerCase()}"
          data-cat2="${(r.cat2||'').toLowerCase()}"
          data-perusahaan="${(r.perusahaan||'').toLowerCase()}"
          data-pillar="${(r.pillar||'').toLowerCase()}"
          style="border-bottom:1px solid #f1f5f9;${rowBg}">
        <td style="padding:6px;text-align:center">
          <input type="checkbox" class="dop-cb" data-id="${r.id}" ${sel ? 'checked' : ''} onchange="dopToggleCb(this)">
        </td>
        <td style="padding:6px 8px">${r.siswa_code||''}</td>
        <td style="padding:6px 8px;${nameSt}">${r.nama||'-'}</td>
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
        <td style="padding:6px 8px">${r.tgl_retur||''}</td>
        <td style="padding:6px 8px">${r.tgl_final6||''}</td>
        <td style="padding:6px 8px">${r.tgl_proses||''}</td>
        <td class="dop-col-agri" style="padding:6px 8px">${r.tgl_HT_AGRI||''}</td>
        <td class="dop-col-agri" style="padding:6px 8px">${r.tgl_Yurike_AGRI||''}</td>
        <td class="dop-col-agri" style="padding:6px 8px">${r.tgl_Aditya_AGRI||''}</td>
        <td class="dop-col-agri" style="padding:6px 8px">${r.tgl_Pedy_AGRI||''}</td>
        <td class="dop-col-agri" style="padding:6px 8px">${r.tgl_C2_AGRI||''}</td>
        <td class="dop-col-agri" style="padding:6px 8px">${r.tgl_MSIG_AGRI||''}</td>
        <td class="dop-col-agri" style="padding:6px 8px">${r.tgl_Paid_AGRI||''}</td>
        <td class="dop-col-app" style="padding:6px 8px">${r['tgl_A-GS_APP']||''}</td>
        <td class="dop-col-app" style="padding:6px 8px">${r['tgl_A-HJK_APP']||''}</td>
        <td class="dop-col-app" style="padding:6px 8px">${r.tgl_ASPIRO_APP||''}</td>
        <td class="dop-col-app" style="padding:6px 8px">${r.tgl_Paid_APP||''}</td>
      </tr>`;
  }).join('');

  if (append) {
    tb.insertAdjacentHTML('beforeend', html);
  } else {
    tb.innerHTML = html;
    const sa = document.getElementById('dop-select-all');
    if (sa) sa.checked = false;
  }

  _dopApplyColVis();
  _dopReveal();
  const loaded = document.querySelectorAll('#dop-tbody .dop-row').length;
  _dopUpdateInfo(loaded);
  _dopUpdateLoadMore(loaded, total);
  dopFilter();
}
```

- [ ] **Step 5: Ganti `_dopFetchCurrent()` dan `dopClearSearch()`**

Temukan `_dopFetchCurrent` dan `dopClearSearch`, ganti dengan:
```javascript
function _dopFetchCurrent() {
  _dopOffset = 0;
  _dopFetch(false);
}

function dopClearSearch() {
  ['dop-s-pam','dop-s-nama'].forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });
  document.querySelectorAll('.dop-filter').forEach(el => el.value = '');
  _dopSelected.clear();
  _dopSelectionMeta.clear();
  const sa = document.getElementById('dop-select-all');
  if (sa) sa.checked = false;
  dopRenderChips();
  _dopOffset = 0;
  _dopFetch(false);
}
```

- [ ] **Step 6: Tambah fungsi helper baru** (letakkan setelah `_dopHide`):

```javascript
function _dopApplyColVis() {
  document.querySelectorAll('.dop-col-agri').forEach(el => {
    el.style.display = _dopSource === 'AGRI' ? '' : 'none';
  });
  document.querySelectorAll('.dop-col-app').forEach(el => {
    el.style.display = _dopSource === 'APP' ? '' : 'none';
  });
}

function _dopUpdateLoadMore(loaded, total) {
  const wrap = document.getElementById('dop-load-more-wrap');
  const btn  = document.getElementById('dop-load-more');
  if (!wrap || !btn) return;
  const remaining = total - loaded;
  if (remaining > 0) {
    btn.textContent = `Muat 100 lagi (masih ${remaining})`;
    wrap.style.display = '';
  } else {
    wrap.style.display = 'none';
  }
}

function dopSetSource(src) {
  _dopSource = src;
  _dopOffset = 0;
  document.querySelectorAll('.dop-src-btn').forEach(btn => {
    const isActive = btn.dataset.src === src;
    btn.style.background    = isActive ? '#2563eb' : '#fff';
    btn.style.color         = isActive ? '#fff' : '#374151';
    btn.style.borderColor   = isActive ? '#2563eb' : '#d1d5db';
  });
  _dopApplyColVis();
  _dopFetch(false);
}

function dopSetPaidOnly(val) {
  _dopPaidOnly = val;
  _dopOffset   = 0;
  _dopFetch(false);
}

function dopLoadMore() {
  _dopFetch(true);
}
```

- [ ] **Step 7: Update info count label**

Temukan fungsi `_dopUpdateInfo`. Tambahkan update ke count label:

```javascript
function _dopUpdateInfo(visibleOverride) {
  const totalVisible = visibleOverride !== undefined
    ? visibleOverride
    : document.querySelectorAll('#dop-tbody .dop-row:not([style*="display: none"])').length;
  const sel  = _dopSelected.size;
  const info = document.getElementById('dop-info');
  if (info) info.textContent = `${sel} dipilih | ${totalVisible} baris`;

  const countLabel = document.getElementById('dop-count-label');
  if (countLabel && _dopTotal > 0) {
    const paidStr = _dopPaidOnly ? ' belum paid' : '';
    countLabel.textContent = `Menampilkan ${_dopOffset} dari ${_dopTotal} record${paidStr} (${_dopSource})`;
  } else if (countLabel) {
    countLabel.textContent = '';
  }

  const btn = document.getElementById('dop-update-btn');
  if (!btn) return;
  btn.textContent = `Update Terpilih (${sel})`;
  btn.disabled = sel === 0;
  btn.style.opacity = sel === 0 ? '0.5' : '1';
}
```

- [ ] **Step 8: Commit semua JS changes**

```bash
git add app/templates/payment_memo/index.html
git commit -m "feat(sla): refactor JS — auto-load on tab open, source toggle, paid-only, load-more, column visibility"
```

---

## Task 6: Update `dopBulkUpdate()` — auto-refresh setelah update

**Files:**
- Modify: `app/templates/payment_memo/index.html` (fungsi `dopBulkUpdate`, sekitar baris 2012)

- [ ] **Step 1: Ganti bagian success handler di `dopBulkUpdate`**

Temukan blok success setelah `await apiFetch('/payment-memo/days-of-pam/bulk-update', ...)`:

```javascript
  if (data.ok) {
    _dopSelected.clear();
    _dopSelectionMeta.clear();
    dopRenderChips();
    if (_dopLastSearchQs) setTimeout(() => _dopFetch(_dopLastSearchQs), 600);
  }
```

Ganti dengan:
```javascript
  if (data.ok) {
    showToast(data.pesan || 'Berhasil diperbarui.', 'success');
    _dopSelected.clear();
    _dopSelectionMeta.clear();
    dopRenderChips();
    _dopOffset = 0;
    await _dopFetch(false);
  }
```

- [ ] **Step 2: Commit**

```bash
git add app/templates/payment_memo/index.html
git commit -m "feat(sla): auto-refresh table after bulk update with current filter state"
```

---

## Task 7: Verifikasi manual end-to-end

- [ ] **Step 1: Jalankan semua tests**

```
cd app && python -m pytest tests/ -v
```

Expected: semua PASS.

- [ ] **Step 2: Jalankan server dan buka tab SLA**

```
cd app && python main.py
```

Buka browser → login → buka Payment Memo → klik tab **SLA**.

Expected:
- Tab langsung menampilkan data (bukan kosong)
- Source toggle menunjukkan **AGRI** aktif (biru)
- Checkbox **Belum Paid saja** tercentang
- Count label: "Menampilkan X dari Y record belum paid (AGRI)"
- Kolom APP (`tgl_A-GS_APP`, `tgl_A-HJK_APP`, dll) tersembunyi

- [ ] **Step 3: Test source toggle APP**

Klik tombol **APP**.

Expected:
- Data refresh otomatis dengan record APP
- Kolom AGRI tersembunyi, kolom APP muncul
- Count label update ke "(APP)"

- [ ] **Step 4: Test paid-only checkbox**

Uncheck **Belum Paid saja**.

Expected:
- Data refresh, semua record AGRI/APP termasuk yang sudah paid
- Count meningkat

- [ ] **Step 5: Test search + load-more**

Masukkan nama di field "Cari Nama", klik 🔍 Cari.

Expected: data terfilter sesuai nama.

Jika total > 100, tombol "Muat 100 lagi (masih X)" muncul di bawah tabel.
Klik tombol — rows baru append ke bawah, selection yang ada tetap.

- [ ] **Step 6: Test bulk update auto-refresh**

Centang beberapa baris → isi tanggal → klik Update Terpilih.

Expected: setelah sukses, tabel refresh otomatis dengan filter yang sama, baris yang baru di-paid menghilang (karena paid_only=true).

- [ ] **Step 7: Final commit (jika ada fix dari testing)**

```bash
git add app/
git commit -m "fix(sla): post-testing fixes"
```

---

## Checklist Spec Coverage

| Requirement | Task |
|-------------|------|
| Default load belum paid saja | Task 5 (dopTabOpened + _dopFetch) |
| Source toggle AGRI/APP | Task 4 (HTML) + Task 5 (JS dopSetSource) |
| Paid-only checkbox default ON | Task 4 (HTML) + Task 5 (JS dopSetPaidOnly) |
| SQL filter via pam_records JOIN | Task 2 (service) |
| LIMIT/OFFSET pagination | Task 2 (service) + Task 3 (route) |
| Load-more button | Task 4 (HTML) + Task 5 (JS dopLoadMore) |
| Kolom visibility per source | Task 4 (HTML th class) + Task 5 (td class + _dopApplyColVis) |
| Count label | Task 5 (_dopUpdateInfo) |
| Empty states per kondisi | Task 5 (dopRenderRows) |
| Auto-refresh setelah bulk update | Task 6 |
| Selection intact saat load-more | Task 5 (append mode) |
