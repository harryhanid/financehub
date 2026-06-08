# Input Tab Multi-Type (AGRI/APP/SML/SETF) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign tab Input agar mendukung 4 tipe PAM (AGRI/APP/SML/SETF) via dropdown, dengan PA-data fetch per tipe, PAM number auto-generate per tipe, Catatan Payment tersimpan di `pam_records.keterangan`, dan tampil di tab PAM dengan source filter.

**Architecture:** Dropdown tipe PAM di header Input panel → semua API calls dapat `?tab={type}` → save ke endpoint baru `/payment-memo/ipay/save-pa` → buat `pam_records` (source=etf_{tab}) + `payment_beasiswa` + update PA status → tab PAM menampilkan hasil dengan source filter.

**Tech Stack:** Flask (Python), SQLite, vanilla JS inline di Jinja2 template. Tidak ada library baru.

---

## File Map

| File | Perubahan |
|------|-----------|
| `app/database.py` | Tambah CREATE TABLE setf_pa + setf_pa_lines di migration |
| `app/modules/etf_payment_application/service.py` | Tambah "setf" ke VALID_TABS + _TAB_CFG |
| `app/modules/payment_memo/service.py` | Tambah `get_next_pam_no()`, `save_pa_payment()`, extend `get_pam_list()` |
| `app/modules/payment_memo/routes.py` | Tambah 2 route baru + update route pam list |
| `app/templates/payment_memo/index.html` | Redesign Input panel header, hapus AGRI sub-tab, PAM tab source filter |
| `tests/test_payment_memo_ipay.py` | Test baru untuk service functions |

---

## Task 1 — Database migration: setf_pa + setf_pa_lines

**Files:**
- Modify: `app/database.py`

- [ ] **Step 1: Baca database.py** untuk lihat pola migration yang sudah ada (cari `CREATE TABLE IF NOT EXISTS etf_pa`)

- [ ] **Step 2: Tambah migration setf_pa + setf_pa_lines** setelah blok `sml_pa_lines`. Cari teks `CREATE TABLE IF NOT EXISTS sml_pa_lines` dan sisipkan setelah penutup `);`:

```python
    conn.execute("""
        CREATE TABLE IF NOT EXISTS setf_pa (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            pa_number TEXT NOT NULL,
            tgl_payment_application TEXT,
            tgl_surat_pengajuan TEXT,
            doc_received_by_educ TEXT,
            received_pa_from_educ TEXT,
            checked_by_fincon TEXT,
            approved_by_htj_1 TEXT,
            send_pa_back_to_educ TEXT,
            pa_received_by_po_fin TEXT,
            approval_by_htj_2 TEXT,
            nomor_pam TEXT,
            tanggal_bayar TEXT,
            keterangan TEXT,
            status TEXT DEFAULT 'open',
            created_at TEXT,
            updated_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS setf_pa_lines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pa_id INTEGER NOT NULL REFERENCES setf_pa(id),
            student_id INTEGER NOT NULL REFERENCES siswa(id),
            jenis_pembayaran TEXT,
            semester TEXT,
            tahun_ajaran TEXT,
            ipk_sem_sebelumnya REAL DEFAULT 0,
            jumlah_pembayaran REAL DEFAULT 0
        )
    """)
```

- [ ] **Step 3: Verifikasi migration jalan** — jalankan app sekali dan cek tabel terbuat:
```bash
cd C:\Financehub
python -c "from app.database import init_db; init_db(); import sqlite3; conn=sqlite3.connect('app/finance_hub.db'); print([r[1] for r in conn.execute('PRAGMA table_info(setf_pa)').fetchall()])"
```
Expected output: list kolom termasuk `pa_number`, `nomor_pam`, `status`, dll.

- [ ] **Step 4: Commit**
```bash
git add app/database.py
git commit -m "feat: add setf_pa and setf_pa_lines tables to migration"
```

---

## Task 2 — Backend: extend etf_payment_application untuk SETF

**Files:**
- Modify: `app/modules/etf_payment_application/service.py:5-12`
- Test: `tests/test_payment_memo_ipay.py`

- [ ] **Step 1: Tulis failing test** di `tests/test_payment_memo_ipay.py` (buat file baru jika belum ada):

```python
# tests/test_payment_memo_ipay.py
import pytest
from app.modules.etf_payment_application.service import VALID_TABS, _TAB_CFG, _tbls


def test_setf_in_valid_tabs():
    assert "setf" in VALID_TABS


def test_setf_tab_config():
    pa_tbl, lines_tbl, pa_prefix, pam_prefix = _TAB_CFG["setf"]
    assert pa_tbl == "setf_pa"
    assert lines_tbl == "setf_pa_lines"
    assert pa_prefix == "SETF"
    assert pam_prefix == "SETF"


def test_tbls_setf_resolves():
    pa_tbl, lines_tbl, pa_prefix, pam_prefix = _tbls("setf")
    assert pa_tbl == "setf_pa"
    assert lines_tbl == "setf_pa_lines"
```

- [ ] **Step 2: Jalankan test — verifikasi FAIL**
```bash
cd C:\Financehub
python -m pytest tests/test_payment_memo_ipay.py::test_setf_in_valid_tabs -v
```
Expected: FAIL `assert 'setf' in {'agri', 'app', 'sml'}`

- [ ] **Step 3: Edit `app/modules/etf_payment_application/service.py`** — ganti baris 5–12:

```python
VALID_TABS = {"agri", "app", "sml", "setf"}

# Maps tab → (pa_table, lines_table, pa_number_prefix, pam_prefix)
_TAB_CFG = {
    "agri":  ("etf_pa",  "etf_pa_lines",  "ETF",  "ETF"),
    "app":   ("app_pa",  "app_pa_lines",  "APP",  "APP"),
    "sml":   ("sml_pa",  "sml_pa_lines",  "SML",  "SML"),
    "setf":  ("setf_pa", "setf_pa_lines", "SETF", "SETF"),
}
```

- [ ] **Step 4: Jalankan semua test — verifikasi PASS**
```bash
python -m pytest tests/test_payment_memo_ipay.py -v
```
Expected: 3 PASS

- [ ] **Step 5: Commit**
```bash
git add app/modules/etf_payment_application/service.py tests/test_payment_memo_ipay.py
git commit -m "feat: add setf tab to etf_payment_application VALID_TABS and _TAB_CFG"
```

---

## Task 3 — Backend: `get_next_pam_no` service + route

**Files:**
- Modify: `app/modules/payment_memo/service.py`
- Modify: `app/modules/payment_memo/routes.py`
- Test: `tests/test_payment_memo_ipay.py`

- [ ] **Step 1: Tambah failing test**

```python
# tambah di tests/test_payment_memo_ipay.py
from unittest.mock import patch
from app.modules.payment_memo.service import get_next_pam_no

_PAM_PREFIX_MAP = {
    "agri": "ETF", "app": "APP", "sml": "SML", "setf": "SETF"
}

def test_get_next_pam_no_format():
    """Hasil harus mengikuti pola PAM-NNN-PREFIX-MM-YYYY"""
    import re
    result = get_next_pam_no(company_id=1, company_code="ETF",
                             tab="setf", date_str="2026-06-08")
    assert re.match(r"PAM-\d{3}-SETF-06-2026", result), f"Got: {result}"


def test_get_next_pam_no_uses_prefix():
    result_agri = get_next_pam_no(1, "ETF", "agri", "2026-06-08")
    result_app  = get_next_pam_no(1, "ETF", "app",  "2026-06-08")
    assert "ETF" in result_agri
    assert "APP" in result_app
```

- [ ] **Step 2: Jalankan — verifikasi FAIL**
```bash
python -m pytest tests/test_payment_memo_ipay.py::test_get_next_pam_no_format -v
```

- [ ] **Step 3: Tambah fungsi `get_next_pam_no` di `app/modules/payment_memo/service.py`** — sisipkan setelah `generate_pam_number`:

```python
# Tab → pam_prefix mapping (mirror dari etf_payment_application)
_IPAY_PAM_PREFIX = {
    "agri":  "ETF",
    "app":   "APP",
    "sml":   "SML",
    "setf":  "SETF",
}

def get_next_pam_no(company_id: int, company_code: str,
                    tab: str, date_str: str) -> str:
    """Return next PAM number untuk tipe terpilih, e.g. 'PAM-054-SETF-06-2026'."""
    prefix = _IPAY_PAM_PREFIX.get(tab, company_code)
    year   = date_str[:4]
    month  = date_str[5:7]
    return generate_pam_number(company_id, prefix, year, month)
```

- [ ] **Step 4: Jalankan test — verifikasi PASS**
```bash
python -m pytest tests/test_payment_memo_ipay.py -k "pam_no" -v
```

- [ ] **Step 5: Tambah route di `app/modules/payment_memo/routes.py`** — sisipkan setelah import block:

```python
@bp.route("/ipay/next-pam-no")
@jwt_html_required
def ipay_next_pam_no():
    tab      = request.args.get("tab", "agri").lower()
    date_str = request.args.get("date", datetime.now().strftime("%Y-%m-%d"))
    company_id   = session.get("company_id", 0)
    company_code = session.get("company_code", "ETF")
    pam_no = get_next_pam_no(company_id, company_code, tab, date_str)
    return jsonify({"ok": True, "pam_no": pam_no})
```

Pastikan `datetime` sudah diimport di routes.py (`from datetime import datetime`).

- [ ] **Step 6: Commit**
```bash
git add app/modules/payment_memo/service.py app/modules/payment_memo/routes.py tests/test_payment_memo_ipay.py
git commit -m "feat: add get_next_pam_no service and /ipay/next-pam-no route"
```

---

## Task 4 — Backend: `save_pa_payment` service + route

**Files:**
- Modify: `app/modules/payment_memo/service.py`
- Modify: `app/modules/payment_memo/routes.py`
- Test: `tests/test_payment_memo_ipay.py`

- [ ] **Step 1: Tambah failing test**

```python
# tambah di tests/test_payment_memo_ipay.py
from app.modules.payment_memo.service import save_pa_payment
from app.database import init_db, get_conn


@pytest.fixture(autouse=False)
def fresh_db(tmp_path, monkeypatch):
    """Gunakan in-memory DB sementara untuk test."""
    import app.database as db_module
    test_db = str(tmp_path / "test.db")
    monkeypatch.setattr(db_module, "DB_PATH", test_db)
    # patch get_conn di semua module yang dipakai
    import app.modules.payment_memo.service as pm_svc
    import app.modules.beasiswa.service as bsw_svc
    monkeypatch.setattr(pm_svc, "get_conn",
                        lambda: __import__("sqlite3").connect(test_db))
    monkeypatch.setattr(bsw_svc, "get_conn",
                        lambda: __import__("sqlite3").connect(test_db))
    init_db()
    conn = __import__("sqlite3").connect(test_db)
    # Seed minimal data
    conn.execute("INSERT INTO companies (id,company_code,company_name) VALUES (1,'ETF','ETF Test')")
    conn.execute("INSERT INTO siswa (id,company_id,code,nama,status) VALUES (1,1,'ETF001','Ahmad','Aktif')")
    conn.execute("INSERT INTO setf_pa (id,company_id,pa_number,status) VALUES (1,1,'SETF-2026-001','open')")
    conn.execute("INSERT INTO setf_pa_lines (id,pa_id,student_id,jenis_pembayaran,jumlah_pembayaran) VALUES (1,1,1,'Pendidikan',5000000)")
    conn.commit(); conn.close()
    return test_db


def test_save_pa_payment_creates_pam(fresh_db):
    data = {
        "tab": "setf",
        "tanggal": "2026-06-08",
        "pam_no": "PAM-001-SETF-06-2026",
        "keterangan": "Test catatan",
        "perusahaan": "PT Test",
        "pillar": "ETF",
        "rows": [{
            "siswa_code": "ETF001",
            "etf_pa_line_id": 1,
            "cat1": "Pendidikan", "cat2": "Semester 1",
            "amount": 5000000,
            "tgl_pengajuan": "", "tgl_receive": "",
            "tgl_pa": "", "tgl_final": ""
        }]
    }
    result = save_pa_payment(company_id=1, company_code="ETF", data=data)
    assert result["ok"] is True

    conn = __import__("sqlite3").connect(fresh_db)
    conn.row_factory = __import__("sqlite3").Row
    pam = conn.execute("SELECT * FROM pam_records WHERE pam_no=?",
                       ("PAM-001-SETF-06-2026",)).fetchone()
    assert pam is not None
    assert pam["source"] == "etf_setf"
    assert pam["keterangan"] == "Test catatan"

    pa = conn.execute("SELECT nomor_pam, status FROM setf_pa WHERE id=1").fetchone()
    assert pa["nomor_pam"] == "PAM-001-SETF-06-2026"
    assert pa["status"] == "on_process"
    conn.close()
```

- [ ] **Step 2: Jalankan — verifikasi FAIL**
```bash
python -m pytest tests/test_payment_memo_ipay.py::test_save_pa_payment_creates_pam -v
```

- [ ] **Step 3: Tambah fungsi `save_pa_payment` di `app/modules/payment_memo/service.py`** — sisipkan setelah `get_next_pam_no`:

```python
def save_pa_payment(company_id: int, company_code: str, data: dict) -> dict:
    """
    Unified save untuk Input PA (AGRI/APP/SML/SETF):
    1. Buat pam_records dengan source='etf_{tab}'
    2. Buat payment_beasiswa rows
    3. Update PA header: nomor_pam + status='on_process'
    """
    from app.modules.beasiswa.service import add_payment_multi
    from app.modules.etf_payment_application.service import _TAB_CFG

    tab        = data.get("tab", "agri").lower()
    tanggal    = data.get("tanggal", _ts()[:10])
    pam_no     = (data.get("pam_no") or "").strip()
    keterangan = data.get("keterangan", "")
    perusahaan = data.get("perusahaan", "")
    pillar     = data.get("pillar", "")
    rows       = data.get("rows", [])

    if not pam_no:
        return {"ok": False, "pesan": "No. PAM wajib diisi."}
    if not rows:
        return {"ok": False, "pesan": "Minimal 1 baris siswa."}

    pa_tbl, lines_tbl, _, _ = _TAB_CFG.get(tab, _TAB_CFG["agri"])

    # 1. Buat payment_beasiswa rows
    bsw_result = add_payment_multi(
        company_id, company_code, tanggal, pillar, perusahaan, rows
    )
    if not bsw_result.get("ok"):
        return bsw_result
    payment_ids = bsw_result.get("payment_ids", [])
    total       = bsw_result.get("total", 0.0)

    conn = get_conn()
    try:
        # 2. Link payment_beasiswa → pam_no
        if payment_ids:
            ph = ",".join("?" * len(payment_ids))
            conn.execute(
                f"UPDATE payment_beasiswa SET pam=? WHERE id IN ({ph})",
                [pam_no] + payment_ids
            )

        # 3. Buat pam_records
        due_date = _add_one_month(tanggal)
        conn.execute(
            """INSERT INTO pam_records
               (company_id, pam_no, pam_date, requestors_name, keterangan,
                total_amount, due_date, source, status, created_at)
               VALUES (?,?,?,?,?,?,?,?,'draft',?)""",
            (company_id, pam_no, tanggal,
             company_code, keterangan,
             total, due_date, f"etf_{tab}", _ts())
        )

        # 4. Update PA header: nomor_pam + status='on_process'
        line_ids = [r.get("etf_pa_line_id") for r in rows
                    if r.get("etf_pa_line_id")]
        if line_ids:
            ph = ",".join("?" * len(line_ids))
            pa_ids = [row[0] for row in conn.execute(
                f"SELECT DISTINCT pa_id FROM {lines_tbl} WHERE id IN ({ph})",
                line_ids
            ).fetchall()]
            if pa_ids:
                ph2 = ",".join("?" * len(pa_ids))
                conn.execute(
                    f"UPDATE {pa_tbl} SET nomor_pam=?, status='on_process'"
                    f" WHERE id IN ({ph2}) AND company_id=?",
                    [pam_no] + pa_ids + [company_id]
                )

        conn.commit()
    except Exception as e:
        conn.rollback()
        conn.close()
        return {"ok": False, "pesan": f"Gagal menyimpan: {e}"}
    conn.close()
    return {"ok": True, "pesan": f"PAM {pam_no} berhasil dibuat.", "pam_no": pam_no}
```

- [ ] **Step 4: Jalankan test — verifikasi PASS**
```bash
python -m pytest tests/test_payment_memo_ipay.py -v
```
Expected: semua PASS

- [ ] **Step 5: Tambah route di `app/modules/payment_memo/routes.py`**:

```python
@bp.route("/ipay/save-pa", methods=["POST"])
@jwt_html_required
def ipay_save_pa():
    data         = request.get_json(force=True) or {}
    company_id   = session.get("company_id", 0)
    company_code = session.get("company_code", "ETF")
    result = save_pa_payment(company_id, company_code, data)
    return jsonify(result)
```

Tambah `save_pa_payment` ke import di awal routes.py.

- [ ] **Step 6: Commit**
```bash
git add app/modules/payment_memo/service.py app/modules/payment_memo/routes.py tests/test_payment_memo_ipay.py
git commit -m "feat: add save_pa_payment service and /ipay/save-pa route"
```

---

## Task 5 — Backend: extend `get_pam_list` dengan source filter

**Files:**
- Modify: `app/modules/payment_memo/service.py:277-295`
- Modify: `app/modules/payment_memo/routes.py` (route `/pam`)
- Test: `tests/test_payment_memo_ipay.py`

- [ ] **Step 1: Tambah failing test**

```python
def test_get_pam_list_source_filter(fresh_db):
    from app.modules.payment_memo.service import get_pam_list
    conn = __import__("sqlite3").connect(fresh_db)
    conn.execute(
        "INSERT INTO pam_records (company_id,pam_no,source,status,created_at)"
        " VALUES (1,'PAM-001-ETF-06-2026','etf_agri','draft','2026-06-08')"
    )
    conn.execute(
        "INSERT INTO pam_records (company_id,pam_no,source,status,created_at)"
        " VALUES (1,'PAM-001-APP-06-2026','etf_app','draft','2026-06-08')"
    )
    conn.commit(); conn.close()

    all_rows  = get_pam_list(company_id=1, source="")
    agri_rows = get_pam_list(company_id=1, source="agri")
    app_rows  = get_pam_list(company_id=1, source="app")

    assert len(all_rows) == 2
    assert len(agri_rows) == 1 and agri_rows[0]["pam_no"] == "PAM-001-ETF-06-2026"
    assert len(app_rows)  == 1 and app_rows[0]["pam_no"]  == "PAM-001-APP-06-2026"
```

- [ ] **Step 2: Jalankan — verifikasi FAIL**
```bash
python -m pytest tests/test_payment_memo_ipay.py::test_get_pam_list_source_filter -v
```

- [ ] **Step 3: Edit `get_pam_list` di service.py** — ganti signature dan tambah source filter:

```python
def get_pam_list(company_id: int, search: str = "", bulan: str = "",
                 tahun: str = "", source: str = "") -> list:
    sql    = "SELECT * FROM pam_records WHERE company_id=?"
    params = [company_id]
    if search:
        q       = f"%{search}%"
        sql    += " AND (pam_no LIKE ? OR pt LIKE ? OR keterangan LIKE ?)"
        params += [q, q, q]
    if bulan:
        sql    += " AND strftime('%m', pam_date)=?"
        params += [bulan.zfill(2)]
    if tahun:
        sql    += " AND strftime('%Y', pam_date)=?"
        params += [tahun]
    if source:
        sql    += " AND source LIKE ?"
        params += [f"etf_{source}%"]
    sql += " ORDER BY created_at DESC"
    conn = get_conn()
    rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
    conn.close()
    return rows
```

- [ ] **Step 4: Update route `/pam` di routes.py** — tambah `source` parameter:

Cari `@bp.route("/pam")` dan update handler-nya:
```python
@bp.route("/pam")
@jwt_html_required
def get_pam_list_route():
    company_id = session.get("company_id", 0)
    rows = get_pam_list(
        company_id,
        search=request.args.get("search", ""),
        bulan=request.args.get("bulan", ""),
        tahun=request.args.get("tahun", ""),
        source=request.args.get("source", ""),
    )
    return jsonify({"ok": True, "rows": rows})
```

- [ ] **Step 5: Jalankan semua test**
```bash
python -m pytest tests/test_payment_memo_ipay.py -v
```
Expected: semua PASS

- [ ] **Step 6: Commit**
```bash
git add app/modules/payment_memo/service.py app/modules/payment_memo/routes.py tests/test_payment_memo_ipay.py
git commit -m "feat: add source filter to get_pam_list and PAM list route"
```

---

## Task 6 — Frontend: Hapus AGRI sub-tab, redesign header Input

**Files:**
- Modify: `app/templates/payment_memo/index.html` (lines ~89–222)

- [ ] **Step 1: Baca bagian tab Input** — lines 89–222 di index.html. Pahami struktur sub-tab dan panel AGRI.

- [ ] **Step 2: Hapus sub-tab buttons dan panel AGRI**

Hapus blok berikut (lines ~90–98):
```html
    {# ── sub-tab: Beasiswa | AGRI ── #}
    <div style="display:flex;gap:0;margin-bottom:1rem;border:1px solid var(--border);border-radius:6px;overflow:hidden;width:fit-content">
      <button id="ipay-sub-beasiswa" onclick="ipaySubTab('beasiswa')"
              ...>Beasiswa</button>
      <button id="ipay-sub-agri" onclick="ipaySubTab('agri')"
              ...>AGRI</button>
    </div>
```

Hapus seluruh panel AGRI (lines ~167–221):
```html
    {# ── Panel AGRI ── #}
    <div id="ipay-panel-agri" style="display:none">
      ...
    </div>{# end ipay-panel-agri #}
```

Hapus `style="display:none"` dari div pembungkus panel Beasiswa sehingga langsung visible:
```html
    {# panel Beasiswa sekarang langsung visible #}
    <div id="ipay-panel-beasiswa">
```
→ tidak perlu `style="display:none"` karena sudah tidak ada sub-tab logic.

- [ ] **Step 3: Tambah header baris 1 — Tipe PAM + Tanggal + No.PAM + Perusahaan**

Ganti header grid yang sudah ada (4 kolom: Tanggal, PAM, Perusahaan, Pillar) dengan:

```html
    <div style="display:grid;grid-template-columns:140px 160px minmax(220px,1fr) 200px;gap:.75rem;margin-bottom:.5rem;align-items:end;max-width:900px">
      <div class="form-group" style="margin:0">
        <label>Tipe PAM</label>
        <select id="ipay-type" onchange="ipayOnTypeChange()"
                style="border:1.5px solid #3b82f6;color:#1d4ed8;font-weight:700;background:#eff6ff">
          <option value="agri">AGRI</option>
          <option value="app">APP</option>
          <option value="sml">SML</option>
          <option value="setf">SETF</option>
        </select>
      </div>
      <div class="form-group" style="margin:0">
        <label>Tanggal</label>
        <input type="date" id="ipay-tgl" onchange="ipayFetchNextPamNo()">
      </div>
      <div class="form-group" style="margin:0">
        <label>No. PAM <span id="ipay-pam-type-badge"
               style="font-size:.65rem;color:#10b981;font-weight:400">(auto AGRI)</span></label>
        <input type="text" id="ipay-pam-full" readonly
               placeholder="Memuat..."
               style="font-family:monospace;font-weight:700;color:#1d4ed8;background:#f0f9ff">
      </div>
      <div class="form-group" style="margin:0">
        <label>Perusahaan</label>
        <div style="position:relative">
          <input type="text" id="ipay-perusahaan-search" placeholder="Cari vendor..."
                 autocomplete="off" oninput="ipayVendorSearch()"
                 onblur="setTimeout(()=>document.getElementById('ipay-vendor-sugg').style.display='none',200)">
          <input type="hidden" id="ipay-perusahaan">
          <div id="ipay-vendor-sugg" style="display:none;position:fixed;z-index:9999;background:#fff;border:1px solid #93c5fd;border-radius:.375rem;max-height:260px;overflow-y:auto;box-shadow:0 6px 20px rgba(0,0,0,.15)"></div>
        </div>
      </div>
    </div>
```

- [ ] **Step 4: Tambah header baris 2 — Pillar + Catatan Payment**

Setelah grid di Step 3, sisipkan:
```html
    <div style="display:grid;grid-template-columns:200px 1fr;gap:.75rem;margin-bottom:1rem;align-items:end;max-width:900px">
      <div class="form-group" style="margin:0">
        <label>Pillar</label>
        <input type="text" id="ipay-pillar" readonly placeholder="Auto dari vendor"
               style="background:#f3f4f6;cursor:default;color:#374151;font-weight:600">
      </div>
      <div class="form-group" style="margin:0">
        <label>Catatan Payment
          <span style="font-size:.65rem;color:#6b7280;font-weight:400">(tampil di tab PAM)</span>
        </label>
        <input type="text" id="ipay-catatan" placeholder="Opsional — muncul di kolom Catatan PAM tab"
               style="border:1px solid #93c5fd;background:#fafeff">
      </div>
    </div>
```

- [ ] **Step 5: Hapus field lama** yang sudah dipindah atau tidak lagi relevan:
- Hapus `<input type="hidden" id="ipay-pam-full">` yang lama (sekarang sudah jadi input text)
- Hapus field `id="ipay-pam-seq"` dan preview span `id="ipay-pam-preview"` jika masih ada

- [ ] **Step 6: Update tombol Save** — ganti label dari `💾 Simpan Payment` menjadi dinamis. Beri id:
```html
<button class="btn btn-primary" id="ipay-save-btn" onclick="ipaySavePa()">💾 Simpan PAM AGRI</button>
```

- [ ] **Step 7: Isi tanggal hari ini saat page load** — cari fungsi `ipayReset()` dan tambahkan:
```javascript
function ipayReset() {
  // set tanggal = hari ini
  const today = new Date().toISOString().slice(0, 10);
  document.getElementById('ipay-tgl').value = today;
  // ... sisa reset logic yang sudah ada
```

- [ ] **Step 8: Hapus JS functions AGRI yang tidak terpakai** — cari dan hapus fungsi-fungsi berikut dari JS section template:
  - `function ipaySubTab(tab)` — sub-tab switcher
  - `async function agriLoadOpen()` — load AGRI PA open
  - `async function agriSavePAM()` — save AGRI PAM (diganti `ipaySavePa`)
  - Variable `let _agriRows = []` dan referensinya
  - Baris `if (!isBsw && !_agriRows.length) agriLoadOpen();` di dalam `ipaySubTab` atau `ipayReset`
  
  Jangan hapus `agriToggleAll`, `agriClearSel`, `agriToggleRow` jika masih dipakai di tempat lain — cek dulu dengan search.

- [ ] **Step 9: Commit**
```bash
git add app/templates/payment_memo/index.html
git commit -m "feat: remove AGRI sub-tab, add type dropdown and Catatan Payment to Input header"
```

---

## Task 7 — Frontend: wire type-aware fetch + PAM auto-number + save baru

**Files:**
- Modify: `app/templates/payment_memo/index.html` (JS section)

- [ ] **Step 1: Tambah fungsi `ipayOnTypeChange`** — cari blok JS `function ipayReset()` dan tambahkan sebelumnya:

```javascript
function ipayOnTypeChange() {
  const type = document.getElementById('ipay-type').value.toUpperCase();
  // Update badge label
  document.getElementById('ipay-pam-type-badge').textContent = `(auto ${type})`;
  // Update save button label
  const btn = document.getElementById('ipay-save-btn');
  if (btn) btn.textContent = `💾 Simpan PAM ${type}`;
  // Update siswa search placeholder
  const siswaInps = document.querySelectorAll('#ipay-tbody input[data-siswa-input]');
  // fetch new PAM number
  ipayFetchNextPamNo();
  // Reset semua baris (tipe berubah = PA data berbeda)
  ipayReset();
}

async function ipayFetchNextPamNo() {
  const type = document.getElementById('ipay-type')?.value || 'agri';
  const tgl  = document.getElementById('ipay-tgl')?.value || new Date().toISOString().slice(0,10);
  const pamEl = document.getElementById('ipay-pam-full');
  if (!pamEl) return;
  pamEl.value = 'Memuat...';
  const res = await apiFetch(`/payment-memo/ipay/next-pam-no?tab=${type}&date=${tgl}`);
  if (!res) return;
  const data = await res.json();
  if (data.ok) pamEl.value = data.pam_no;
}
```

- [ ] **Step 2: Panggil `ipayFetchNextPamNo()` saat ipayReset** — cari `function ipayReset()` dan tambahkan di akhir fungsi (setelah baris-baris reset):
```javascript
  ipayFetchNextPamNo();
```

- [ ] **Step 3: Update siswa search** — cari baris `apiFetch('/etf-payment-application/draft-siswa?q=...` dan ubah ke:
```javascript
    const type = document.getElementById('ipay-type')?.value || 'agri';
    apiFetch(`/etf-payment-application/draft-siswa?q=${encodeURIComponent(q)}&tab=${type}`)
```

- [ ] **Step 4: Update draft-lines fetch** — cari `apiFetch('/etf-payment-application/draft-lines?siswa_id=...` dan ubah ke:
```javascript
    const type = document.getElementById('ipay-type')?.value || 'agri';
    apiFetch(`/etf-payment-application/draft-lines?siswa_id=${s.id}&tab=${type}`)
```
Juga update placeholder siswa input saat tipe berubah — cari placeholder `"Cari siswa..."` di `ipayAddRow()`:
```javascript
    siswaInp.placeholder = `Cari siswa (${(document.getElementById('ipay-type')?.value||'agri').toUpperCase()} PA open)...`;
```

- [ ] **Step 5: Tambah fungsi `ipaySavePa`** — sisipkan setelah `async function ipaySave()`:

```javascript
async function ipaySavePa() {
  const type       = document.getElementById('ipay-type')?.value || 'agri';
  const tanggal    = document.getElementById('ipay-tgl').value;
  const pam_no     = document.getElementById('ipay-pam-full').value.trim();
  const keterangan = document.getElementById('ipay-catatan').value.trim();
  const pillar     = document.getElementById('ipay-pillar').value;
  const perusahaan = document.getElementById('ipay-perusahaan').value;

  if (!tanggal || !pam_no || pam_no === 'Memuat...') {
    showToast('Tanggal dan No. PAM wajib ada.', 'error'); return;
  }
  if (!perusahaan) { showToast('Perusahaan wajib diisi.', 'error'); return; }

  const allTrs = [...document.getElementById('ipay-tbody').querySelectorAll('tr[data-rid]')];
  const rows = allTrs.map(tr => ({
    siswa_code:      tr.dataset.siswaCode || '',
    etf_pa_line_id:  tr._hidEtfLineId?.value ? parseInt(tr._hidEtfLineId.value) : null,
    cat1:            tr._cat1Select?.value || '',
    cat2:            tr._cat2Drop?._hid?.value || '',
    amount:          parseFloat(tr._amtInp?.value) || 0,
    tgl_pengajuan:   tr._tgls?.[0]?.value || '',
    tgl_receive:     tr._tgls?.[1]?.value || '',
    tgl_pa:          tr._tgls?.[2]?.value || '',
    tgl_final:       tr._tgls?.[3]?.value || '',
  })).filter(r => r.amount > 0);

  if (!rows.length) { showToast('Minimal 1 baris dengan amount > 0.', 'error'); return; }
  if (rows.some(r => !r.siswa_code)) { showToast('Semua baris harus memilih siswa.', 'error'); return; }

  const res = await apiFetch('/payment-memo/ipay/save-pa', {
    method: 'POST',
    body: JSON.stringify({ tab: type, tanggal, pam_no, keterangan, perusahaan, pillar, rows })
  });
  if (!res) return;
  const data = await res.json();
  showToast(data.pesan, data.ok ? 'success' : 'error');
  if (data.ok) { ipayReset(); loadPAM(); }
}
```

- [ ] **Step 6: Panggil `ipayFetchNextPamNo()` saat tab Input dibuka** — cari tombol tab Input di header:
```html
<button class="tab-btn" data-tab="tab-input-payment" onclick="ipayReset()">Input</button>
```
Sudah oke karena `ipayReset()` sekarang memanggil `ipayFetchNextPamNo()`.

- [ ] **Step 7: Commit**
```bash
git add app/templates/payment_memo/index.html
git commit -m "feat: wire type-aware siswa/PA fetch, PAM auto-number, and ipaySavePa for Input tab"
```

---

## Task 8 — Frontend: source filter + rename kolom di tab PAM

**Files:**
- Modify: `app/templates/payment_memo/index.html` (tab-pam section, lines ~226–275)

- [ ] **Step 1: Baca filter bar di tab-pam** — cari `id="pam-search"` dan lihat struktur filter-bar yang ada.

- [ ] **Step 2: Tambah dropdown source filter** di filter bar PAM. Cari baris dengan `id="pam-filter-tahun"` dan sisipkan setelah select tersebut:

```html
      <select id="pam-filter-source" onchange="loadPAMDebounced()"
              style="padding:6px 10px;border:1px solid #d1d5db;border-radius:6px;font-size:13px">
        <option value="">Semua Tipe</option>
        <option value="agri">AGRI</option>
        <option value="app">APP</option>
        <option value="sml">SML</option>
        <option value="setf">SETF</option>
      </select>
```

- [ ] **Step 3: Update `loadPAM()` untuk kirim source** — cari:
```javascript
  const params = new URLSearchParams({ search, bulan, tahun });
```
Ganti dengan:
```javascript
  const source  = (document.getElementById('pam-filter-source')?.value || '');
  const params  = new URLSearchParams({ search, bulan, tahun, source });
```

- [ ] **Step 4: Rename header kolom** — cari di `<thead>` tab-pam:
```html
<th style="padding:8px 10px;text-align:left;">Keterangan</th>
```
Ganti dengan:
```html
<th style="padding:8px 10px;text-align:left;">Catatan Payment</th>
```

- [ ] **Step 5: Verifikasi manual** — jalankan app, buka tab AGRI:
  1. Filter source = AGRI → hanya PAM dengan source 'etf_agri' muncul
  2. Filter source = APP → PAM dengan source 'etf_app' muncul
  3. Kolom header menampilkan "Catatan Payment"
  4. Data di kolom Catatan Payment menampilkan `keterangan` dari pam_records

```bash
cd C:\Financehub && python run.py
```

- [ ] **Step 6: Commit**
```bash
git add app/templates/payment_memo/index.html
git commit -m "feat: add source filter to PAM tab and rename Keterangan to Catatan Payment"
```

---

## Verifikasi End-to-End

Setelah semua 8 task selesai:

- [ ] Buka tab Input → tipe dropdown tampil (AGRI/APP/SML/SETF)
- [ ] Ganti tipe ke "SETF" → No. PAM berubah ke format `PAM-XXX-SETF-MM-YYYY`
- [ ] Cari siswa → hanya siswa dengan open PA di `setf_pa` muncul
- [ ] Pilih siswa → cat1/cat2/amount/dates auto-fill dari `setf_pa_lines`
- [ ] Isi Catatan Payment → "Tes batch SETF"
- [ ] Klik "💾 Simpan PAM SETF" → toast sukses
- [ ] Buka tab AGRI → filter sumber = SETF → PAM baru muncul dengan Catatan "Tes batch SETF"
- [ ] Cek DB: `setf_pa.nomor_pam` terisi, `status='on_process'`
- [ ] Run all tests: `python -m pytest tests/test_payment_memo_ipay.py -v`
