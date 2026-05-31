# Days of PAM Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tambahkan tab "Days of PAM" di halaman Payment Approval Memo yang menampilkan semua `payment_beasiswa` ber-PAM dengan filter real-time dan bulk date update.

**Architecture:** Data diambil dari query JOIN `payment_beasiswa + siswa` saat halaman di-render (Jinja), disimpan ke JS array `DOP_DATA` untuk filter client-side. Bulk update via POST AJAX `/payment-memo/days-of-pam/bulk-update` yang hanya mengupdate field tanggal yang tidak kosong.

**Tech Stack:** Python/Flask, SQLite, Jinja2, vanilla JS (no framework)

**Spec:** `docs/superpowers/specs/2026-05-31-days-of-pam-design.md`

> **Note:** `service.py` (642 lines) dan `index.html` (846 lines) sudah melampaui batas 500 baris proyek. Kedua file ini sudah dalam kondisi demikian sebelum task ini — tambahkan kode secukupnya mengikuti pola yang ada.

---

## File Map

| File | Aksi | Tanggung Jawab |
|------|------|----------------|
| `app/modules/payment_memo/service.py` | Modify | +`get_days_of_pam()`, +`bulk_update_dates()` |
| `app/modules/payment_memo/routes.py` | Modify | extend `index()`, +POST route `days-of-pam/bulk-update` |
| `app/templates/payment_memo/index.html` | Modify | +tab button, +tab panel HTML, +JS block |
| `app/tests/test_pam_service.py` | Modify | +tests for 2 new service functions |
| `app/tests/test_memo_api.py` | Modify | +tests for bulk-update route |

---

## Task 1: Service — `get_days_of_pam()`

**Files:**
- Modify: `app/modules/payment_memo/service.py` (tambah di akhir file, sebelum `export_pam_excel`)
- Test: `app/tests/test_pam_service.py`

- [ ] **Step 1.1: Tulis failing test**

Tambahkan di akhir `app/tests/test_pam_service.py`:

```python
# ── Days of PAM ────────────────────────────────────────────────────────────────

def _seed_payment_with_pam(conn, company_id, siswa_code, pam_no):
    """Helper: insert one payment_beasiswa row that has a pam assigned."""
    conn.execute(
        """INSERT INTO payment_beasiswa
           (company_id, siswa_code, cat1, cat2, tanggal, amount, pillar,
            pam, perusahaan, tgl_pengajuan, tgl_receive, tgl_pa, tgl_final)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (company_id, siswa_code, "Beasiswa", "Semester",
         "2026-05-01", 5000000.0, "AGRI",
         pam_no, "PT. SMART Tbk",
         "2026-05-02", "2026-05-05", "2026-05-10", "2026-05-15")
    )
    conn.commit()


def test_get_days_of_pam_returns_rows_with_pam():
    from modules.payment_memo.service import get_days_of_pam
    conn = get_conn()
    # seed siswa
    conn.execute(
        "INSERT INTO siswa (company_id, code, nama) VALUES (?,?,?)",
        (COMPANY_ID, "S001", "Budi Santoso")
    )
    _seed_payment_with_pam(conn, COMPANY_ID, "S001", "PAM-001-ETF-05-2026")
    # payment without pam should NOT appear
    conn.execute(
        "INSERT INTO payment_beasiswa (company_id, siswa_code, cat1, tanggal, amount) VALUES (?,?,?,?,?)",
        (COMPANY_ID, "S001", "Beasiswa", "2026-05-01", 1000000.0)
    )
    conn.commit()
    conn.close()

    rows = get_days_of_pam(COMPANY_ID)
    assert len(rows) == 1
    r = rows[0]
    assert r["pam_no"]      == "PAM-001-ETF-05-2026"
    assert r["siswa_code"]  == "S001"
    assert r["nama"]        == "Budi Santoso"
    assert r["cat1"]        == "Beasiswa"
    assert r["perusahaan"]  == "PT. SMART Tbk"
    assert r["amount"]      == 5000000.0
    assert r["tgl_receive"] == "2026-05-05"


def test_get_days_of_pam_empty_pam_excluded():
    from modules.payment_memo.service import get_days_of_pam
    conn = get_conn()
    conn.execute(
        "INSERT INTO payment_beasiswa (company_id, siswa_code, cat1, tanggal, amount, pam) VALUES (?,?,?,?,?,?)",
        (COMPANY_ID, "S002", "Beasiswa", "2026-05-01", 1000000.0, "")
    )
    conn.commit()
    conn.close()
    rows = get_days_of_pam(COMPANY_ID)
    assert rows == []


def test_get_days_of_pam_different_company_isolated():
    from modules.payment_memo.service import get_days_of_pam
    conn = get_conn()
    conn.execute(
        "INSERT INTO siswa (company_id, code, nama) VALUES (?,?,?)",
        (COMPANY_ID, "S001", "Budi")
    )
    _seed_payment_with_pam(conn, COMPANY_ID, "S001", "PAM-001-ETF-05-2026")
    conn.close()
    # Company 99 should see nothing
    rows = get_days_of_pam(99)
    assert rows == []
```

- [ ] **Step 1.2: Jalankan test, pastikan FAIL**

```bash
cd C:\Financehub\app
python -m pytest tests/test_pam_service.py::test_get_days_of_pam_returns_rows_with_pam -v
```

Expected: `ImportError` atau `AttributeError: module has no attribute 'get_days_of_pam'`

- [ ] **Step 1.3: Implementasi `get_days_of_pam` di `service.py`**

Tambahkan setelah blok `# ── PAM helpers ─────` (setelah fungsi `get_pam_payments`, sebelum `update_pam_and_application`):

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
```

- [ ] **Step 1.4: Jalankan semua test, pastikan PASS**

```bash
cd C:\Financehub\app
python -m pytest tests/test_pam_service.py -v
```

Expected: semua test PASS (termasuk 3 test baru)

- [ ] **Step 1.5: Commit**

```bash
cd C:\Financehub
git add app/modules/payment_memo/service.py app/tests/test_pam_service.py
git commit -m "feat(days-of-pam): add get_days_of_pam service function"
```

---

## Task 2: Service — `bulk_update_dates()`

**Files:**
- Modify: `app/modules/payment_memo/service.py`
- Test: `app/tests/test_pam_service.py`

- [ ] **Step 2.1: Tulis failing test**

Tambahkan di akhir `app/tests/test_pam_service.py`:

```python
# ── Bulk update dates ─────────────────────────────────────────────────────────

def test_bulk_update_dates_only_filled_fields():
    from modules.payment_memo.service import bulk_update_dates
    conn = get_conn()
    conn.execute(
        "INSERT INTO siswa (company_id, code, nama) VALUES (?,?,?)",
        (COMPANY_ID, "S001", "Budi")
    )
    conn.execute(
        """INSERT INTO payment_beasiswa
           (company_id, siswa_code, cat1, tanggal, amount, pam,
            tgl_pengajuan, tgl_receive, tgl_pa, tgl_final)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (COMPANY_ID, "S001", "Beasiswa", "2026-05-01", 5000000.0,
         "PAM-001-ETF-05-2026", None, None, None, None)
    )
    conn.commit()
    row_id = conn.execute("SELECT id FROM payment_beasiswa WHERE siswa_code='S001'").fetchone()["id"]
    conn.close()

    result = bulk_update_dates(
        ids=[row_id],
        dates={"tgl_receive": "2026-05-10", "tgl_final": ""},
        company_id=COMPANY_ID
    )
    assert result["ok"] is True
    assert result["updated"] == 1

    conn2 = get_conn()
    r = conn2.execute("SELECT * FROM payment_beasiswa WHERE id=?", (row_id,)).fetchone()
    conn2.close()
    assert r["tgl_receive"] == "2026-05-10"
    assert r["tgl_final"]   is None       # empty string → not updated


def test_bulk_update_dates_no_ids_returns_error():
    from modules.payment_memo.service import bulk_update_dates
    result = bulk_update_dates(ids=[], dates={"tgl_receive": "2026-05-10"}, company_id=COMPANY_ID)
    assert result["ok"] is False


def test_bulk_update_dates_no_dates_returns_error():
    from modules.payment_memo.service import bulk_update_dates
    result = bulk_update_dates(ids=[1], dates={}, company_id=COMPANY_ID)
    assert result["ok"] is False


def test_bulk_update_dates_wrong_company_not_updated():
    from modules.payment_memo.service import bulk_update_dates
    conn = get_conn()
    conn.execute(
        "INSERT INTO siswa (company_id, code, nama) VALUES (?,?,?)",
        (COMPANY_ID, "S001", "Budi")
    )
    conn.execute(
        """INSERT INTO payment_beasiswa
           (company_id, siswa_code, cat1, tanggal, amount, pam, tgl_receive)
           VALUES (?,?,?,?,?,?,?)""",
        (COMPANY_ID, "S001", "Beasiswa", "2026-05-01", 5000000.0,
         "PAM-001-ETF-05-2026", "2026-04-01")
    )
    conn.commit()
    row_id = conn.execute("SELECT id FROM payment_beasiswa WHERE siswa_code='S001'").fetchone()["id"]
    conn.close()

    # Try to update with wrong company_id=99
    result = bulk_update_dates(ids=[row_id], dates={"tgl_receive": "2026-05-10"}, company_id=99)
    assert result["updated"] == 0

    conn2 = get_conn()
    r = conn2.execute("SELECT tgl_receive FROM payment_beasiswa WHERE id=?", (row_id,)).fetchone()
    conn2.close()
    assert r["tgl_receive"] == "2026-04-01"   # unchanged
```

- [ ] **Step 2.2: Jalankan test, pastikan FAIL**

```bash
cd C:\Financehub\app
python -m pytest tests/test_pam_service.py::test_bulk_update_dates_only_filled_fields -v
```

Expected: `ImportError` atau `AttributeError`

- [ ] **Step 2.3: Implementasi `bulk_update_dates` di `service.py`**

Tambahkan setelah `get_days_of_pam`:

```python
def bulk_update_dates(ids: list, dates: dict, company_id: int) -> dict:
    _ALLOWED = {"tanggal", "tgl_pengajuan", "tgl_receive", "tgl_pa", "tgl_final"}
    fields = [(k, v) for k, v in dates.items() if k in _ALLOWED and v]
    if not fields:
        return {"ok": False, "pesan": "Tidak ada tanggal yang diisi."}
    if not ids:
        return {"ok": False, "pesan": "Tidak ada baris yang dipilih."}
    set_clause   = ", ".join(f"{k}=?" for k, _ in fields)
    vals         = [v for _, v in fields]
    placeholders = ",".join("?" * len(ids))
    conn = get_conn()
    cur  = conn.execute(
        f"UPDATE payment_beasiswa SET {set_clause}"
        f" WHERE id IN ({placeholders}) AND company_id=?",
        vals + list(ids) + [company_id]
    )
    updated = cur.rowcount
    conn.commit()
    conn.close()
    return {"ok": True, "updated": updated,
            "pesan": f"{updated} baris berhasil diperbarui."}
```

- [ ] **Step 2.4: Jalankan semua test, pastikan PASS**

```bash
cd C:\Financehub\app
python -m pytest tests/test_pam_service.py -v
```

Expected: semua test PASS (termasuk 4 test baru)

- [ ] **Step 2.5: Commit**

```bash
cd C:\Financehub
git add app/modules/payment_memo/service.py app/tests/test_pam_service.py
git commit -m "feat(days-of-pam): add bulk_update_dates service function"
```

---

## Task 3: Routes — extend `index()` + POST route

**Files:**
- Modify: `app/modules/payment_memo/routes.py`
- Modify: `app/modules/payment_memo/service.py` (import line)
- Test: `app/tests/test_memo_api.py`

- [ ] **Step 3.1: Tulis failing test untuk route POST**

Tambahkan di akhir `app/tests/test_memo_api.py`:

```python
# ── Days of PAM route ─────────────────────────────────────────────────────────

def _seed_pam_payment(client):
    """Seed satu payment_beasiswa ber-PAM ke company ETF (id=2)."""
    from database import get_conn
    conn = get_conn()
    conn.execute(
        "INSERT OR IGNORE INTO siswa (company_id, code, nama) VALUES (?,?,?)",
        (2, "S001", "Budi")
    )
    conn.execute(
        """INSERT INTO payment_beasiswa
           (company_id, siswa_code, cat1, tanggal, amount, pam)
           VALUES (?,?,?,?,?,?)""",
        (2, "S001", "Beasiswa", "2026-05-01", 5000000.0, "PAM-001-ETF-05-2026")
    )
    conn.commit()
    row_id = conn.execute(
        "SELECT id FROM payment_beasiswa WHERE siswa_code='S001'"
    ).fetchone()["id"]
    conn.close()
    return row_id


def test_days_of_pam_bulk_update_ok(client):
    token = _login(client)
    with client.session_transaction() as sess:
        sess["company_id"]   = 2
        sess["company_code"] = "ETF"
    row_id = _seed_pam_payment(client)
    r = client.post(
        "/payment-memo/days-of-pam/bulk-update",
        json={"ids": [row_id], "dates": {"tgl_receive": "2026-05-10"}},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 200
    data = r.get_json()
    assert data["ok"] is True
    assert data["updated"] == 1


def test_days_of_pam_bulk_update_no_session(client):
    token = _login(client)
    # no company_id in session
    r = client.post(
        "/payment-memo/days-of-pam/bulk-update",
        json={"ids": [1], "dates": {"tgl_receive": "2026-05-10"}},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 400


def test_days_of_pam_bulk_update_invalid_ids(client):
    token = _login(client)
    with client.session_transaction() as sess:
        sess["company_id"] = 2
    r = client.post(
        "/payment-memo/days-of-pam/bulk-update",
        json={"ids": ["not-an-int"], "dates": {"tgl_receive": "2026-05-10"}},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 400
```

- [ ] **Step 3.2: Jalankan test, pastikan FAIL**

```bash
cd C:\Financehub\app
python -m pytest tests/test_memo_api.py::test_days_of_pam_bulk_update_ok -v
```

Expected: `404` (route belum ada)

- [ ] **Step 3.3: Tambah import di `routes.py`**

Di bagian import atas `routes.py`, tambahkan `get_days_of_pam` dan `bulk_update_dates`:

```python
from modules.payment_memo.service import (
    get_draft_payments, create_memo, get_memo_list, get_memo_detail,
    update_memo_status, export_memo_pdf,
    get_pam_list, get_coa_list, update_pam_gl_account,
    update_pam_status, update_pam_record,
    get_pam_detail, get_pam_payments, update_pam_and_application,
    get_draft_payment_detail, update_draft_and_linked,
    delete_payment_beasiswa, cancel_pam_record,
    get_days_of_pam, bulk_update_dates,
)
```

- [ ] **Step 3.4: Extend `index()` di `routes.py`**

Ganti fungsi `index()` yang ada:

```python
@bp.route("/")
@jwt_html_required
def index():
    if not session.get("company_id"):
        return redirect(url_for("dashboard.select_company"))
    company_id = session["company_id"]
    memos       = get_memo_list(company_id)
    drafts      = get_draft_payments(company_id)
    dop_rows    = get_days_of_pam(company_id)
    return render_template(
        "payment_memo/index.html",
        memos=memos,
        drafts=drafts,
        dop_rows=dop_rows,
        cat1_list=config.CAT1_BGT,
        cat2_list=config.CAT2_SEM,
        active_page="payment_memo",
        pam_approved_by_1=config.PAM_APPROVED_BY_1,
        pam_approved_by_2=config.PAM_APPROVED_BY_2,
        **_ctx()
    )
```

- [ ] **Step 3.5: Tambah POST route di `routes.py`**

Tambahkan setelah route `/pam` yang ada:

```python
@bp.route("/days-of-pam/bulk-update", methods=["POST"])
@role_required("verificator", "releaser")
def days_of_pam_bulk_update():
    company_id = session.get("company_id")
    if not company_id:
        return jsonify({"ok": False, "pesan": "Perusahaan belum dipilih."}), 400
    data  = request.get_json(force=True) or {}
    ids   = data.get("ids", [])
    dates = data.get("dates", {})
    if not isinstance(ids, list) or not all(isinstance(i, int) for i in ids):
        return jsonify({"ok": False, "pesan": "Format ids tidak valid."}), 400
    result = bulk_update_dates(ids, dates, company_id)
    return jsonify(result)
```

- [ ] **Step 3.6: Jalankan semua test, pastikan PASS**

```bash
cd C:\Financehub\app
python -m pytest tests/test_memo_api.py -v
```

Expected: semua test PASS (termasuk 3 test baru)

- [ ] **Step 3.7: Commit**

```bash
cd C:\Financehub
git add app/modules/payment_memo/routes.py app/tests/test_memo_api.py
git commit -m "feat(days-of-pam): extend index route + add bulk-update POST route"
```

---

## Task 4: Template — HTML (Tab button + Panel)

**Files:**
- Modify: `app/templates/payment_memo/index.html`

- [ ] **Step 4.1: Tambah tab button**

Cari baris:
```html
    <button class="tab-btn" data-tab="tab-draft-memo">Draft Memo</button>
```

Tambahkan SEBELUM baris tersebut:
```html
    <button class="tab-btn" data-tab="tab-days-of-pam">Days of PAM</button>
```

- [ ] **Step 4.2: Tambah tab panel HTML**

Cari baris:
```html
  <!-- Draft Memo Tab -->
  <div class="tab-panel" id="tab-draft-memo">
```

Tambahkan SEBELUM baris tersebut (panel baru):

```html
  <!-- Days of PAM Tab -->
  <div class="tab-panel" id="tab-days-of-pam">
    <!-- Filter Bar -->
    <div style="display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:10px;padding:10px;background:#f8fafc;border:1px solid #e2e8f0;border-radius:6px">
      <input id="dop-f-code"       class="dop-filter" type="text" placeholder="Siswa Code"
             style="padding:5px 8px;border:1px solid #d1d5db;border-radius:5px;font-size:12px;width:100px" oninput="dopFilter()">
      <input id="dop-f-nama"       class="dop-filter" type="text" placeholder="Nama Siswa"
             style="padding:5px 8px;border:1px solid #d1d5db;border-radius:5px;font-size:12px;width:130px" oninput="dopFilter()">
      <input id="dop-f-pam"        class="dop-filter" type="text" placeholder="PAM NO"
             style="padding:5px 8px;border:1px solid #d1d5db;border-radius:5px;font-size:12px;width:150px" oninput="dopFilter()">
      <input id="dop-f-cat1"       class="dop-filter" type="text" placeholder="Cat 1"
             style="padding:5px 8px;border:1px solid #d1d5db;border-radius:5px;font-size:12px;width:80px"  oninput="dopFilter()">
      <input id="dop-f-cat2"       class="dop-filter" type="text" placeholder="Cat 2"
             style="padding:5px 8px;border:1px solid #d1d5db;border-radius:5px;font-size:12px;width:80px"  oninput="dopFilter()">
      <input id="dop-f-perusahaan" class="dop-filter" type="text" placeholder="Perusahaan"
             style="padding:5px 8px;border:1px solid #d1d5db;border-radius:5px;font-size:12px;width:150px" oninput="dopFilter()">
      <input id="dop-f-pillar"     class="dop-filter" type="text" placeholder="Pillar"
             style="padding:5px 8px;border:1px solid #d1d5db;border-radius:5px;font-size:12px;width:80px"  oninput="dopFilter()">
      <button onclick="dopClearFilter()"
              style="padding:5px 10px;background:#e5e7eb;border:none;border-radius:5px;font-size:12px;cursor:pointer">
        Bersihkan
      </button>
    </div>

    <!-- Bulk Date Update Bar -->
    <div style="display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:10px;padding:10px;background:#eff6ff;border:1px solid #bfdbfe;border-radius:6px">
      <label style="font-size:11px;font-weight:700;color:#374151;white-space:nowrap">Tanggal:</label>
      <input id="dop-d-tanggal"     type="date" style="border:1px solid #93c5fd;border-radius:4px;padding:4px 6px;font-size:12px">
      <label style="font-size:11px;font-weight:700;color:#374151;white-space:nowrap">Pengajuan:</label>
      <input id="dop-d-pengajuan"   type="date" style="border:1px solid #93c5fd;border-radius:4px;padding:4px 6px;font-size:12px">
      <label style="font-size:11px;font-weight:700;color:#374151;white-space:nowrap">Receive:</label>
      <input id="dop-d-receive"     type="date" style="border:1px solid #93c5fd;border-radius:4px;padding:4px 6px;font-size:12px">
      <label style="font-size:11px;font-weight:700;color:#374151;white-space:nowrap">PA:</label>
      <input id="dop-d-pa"          type="date" style="border:1px solid #93c5fd;border-radius:4px;padding:4px 6px;font-size:12px">
      <label style="font-size:11px;font-weight:700;color:#374151;white-space:nowrap">Final:</label>
      <input id="dop-d-final"       type="date" style="border:1px solid #93c5fd;border-radius:4px;padding:4px 6px;font-size:12px">
      <button id="dop-update-btn" onclick="dopBulkUpdate()" disabled
              style="padding:5px 14px;background:#1d4ed8;color:#fff;border:none;border-radius:5px;font-size:12px;cursor:pointer;font-weight:600;opacity:0.5">
        Update Terpilih (0)
      </button>
    </div>

    <!-- Selection Info + Select All -->
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;font-size:12px;color:#374151">
      <label style="display:flex;align-items:center;gap:4px;cursor:pointer">
        <input type="checkbox" id="dop-select-all" onchange="dopToggleSelectAll(this)">
        Select All Terfilter
      </label>
      <span id="dop-info" style="color:#6b7280">0 dipilih | 0 total</span>
    </div>

    <!-- Table -->
    <div style="overflow-x:auto">
      <table style="width:100%;border-collapse:collapse;font-size:12px">
        <thead>
          <tr style="background:#1e40af;color:#fff">
            <th style="padding:7px 6px;text-align:center;width:32px"></th>
            <th style="padding:7px 8px;text-align:left">Siswa Code</th>
            <th style="padding:7px 8px;text-align:left">Nama Siswa</th>
            <th style="padding:7px 8px;text-align:left">PAM NO</th>
            <th style="padding:7px 8px;text-align:left">Cat 1</th>
            <th style="padding:7px 8px;text-align:left">Cat 2</th>
            <th style="padding:7px 8px;text-align:left">Perusahaan</th>
            <th style="padding:7px 8px;text-align:left">Pillar</th>
            <th style="padding:7px 8px;text-align:right">Amount</th>
            <th style="padding:7px 8px;text-align:left">Tanggal</th>
            <th style="padding:7px 8px;text-align:left">Tgl Pengajuan</th>
            <th style="padding:7px 8px;text-align:left">Tgl Receive</th>
            <th style="padding:7px 8px;text-align:left">Tgl PA</th>
            <th style="padding:7px 8px;text-align:left">Tgl Final</th>
          </tr>
        </thead>
        <tbody id="dop-tbody">
          {% for r in dop_rows %}
          <tr class="dop-row"
              data-id="{{ r.id }}"
              data-code="{{ (r.siswa_code or '')|lower }}"
              data-nama="{{ (r.nama or '')|lower }}"
              data-pam="{{ (r.pam_no or '')|lower }}"
              data-cat1="{{ (r.cat1 or '')|lower }}"
              data-cat2="{{ (r.cat2 or '')|lower }}"
              data-perusahaan="{{ (r.perusahaan or '')|lower }}"
              data-pillar="{{ (r.pillar or '')|lower }}"
              style="border-bottom:1px solid #f1f5f9">
            <td style="padding:6px;text-align:center">
              <input type="checkbox" class="dop-cb" data-id="{{ r.id }}" onchange="dopToggleCb(this)">
            </td>
            <td style="padding:6px 8px">{{ r.siswa_code or '' }}</td>
            <td style="padding:6px 8px">{{ r.nama or '-' }}</td>
            <td style="padding:6px 8px;font-family:monospace;color:#1d4ed8">{{ r.pam_no or '' }}</td>
            <td style="padding:6px 8px">{{ r.cat1 or '' }}</td>
            <td style="padding:6px 8px">{{ r.cat2 or '' }}</td>
            <td style="padding:6px 8px">{{ r.perusahaan or '' }}</td>
            <td style="padding:6px 8px">{{ r.pillar or '' }}</td>
            <td style="padding:6px 8px;text-align:right">Rp {{ "{:,.0f}".format(r.amount or 0) }}</td>
            <td style="padding:6px 8px">{{ r.tanggal or '' }}</td>
            <td style="padding:6px 8px">{{ r.tgl_pengajuan or '' }}</td>
            <td style="padding:6px 8px">{{ r.tgl_receive or '' }}</td>
            <td style="padding:6px 8px">{{ r.tgl_pa or '' }}</td>
            <td style="padding:6px 8px">{{ r.tgl_final or '' }}</td>
          </tr>
          {% else %}
          <tr><td colspan="14" style="padding:20px;text-align:center;color:#6b7280">Belum ada data Days of PAM.</td></tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
  </div>
```

- [ ] **Step 4.3: Jalankan server manual dan buka tab**

```bash
cd C:\Financehub\app
python run.py
```

Buka `http://localhost:8080/payment-memo/` → klik tab "Days of PAM" → pastikan struktur HTML tampil (tabel kosong atau berisi data).

- [ ] **Step 4.4: Commit**

```bash
cd C:\Financehub
git add app/templates/payment_memo/index.html
git commit -m "feat(days-of-pam): add tab button and HTML panel structure"
```

---

## Task 5: Template — JavaScript (filter + select + update)

**Files:**
- Modify: `app/templates/payment_memo/index.html` (bagian `<script>`)

- [ ] **Step 5.1: Tambah JS block Days of PAM**

Cari komentar `// ── Init ─────────────────────────────────────────────────────────────────────` di bagian `<script>`. Tambahkan SEBELUM baris itu:

```javascript
// ── Days of PAM ───────────────────────────────────────────────────────────────
const _dopSelected = new Set();

function dopFilter() {
  const fCode  = document.getElementById('dop-f-code').value.trim().toLowerCase();
  const fNama  = document.getElementById('dop-f-nama').value.trim().toLowerCase();
  const fPam   = document.getElementById('dop-f-pam').value.trim().toLowerCase();
  const fCat1  = document.getElementById('dop-f-cat1').value.trim().toLowerCase();
  const fCat2  = document.getElementById('dop-f-cat2').value.trim().toLowerCase();
  const fPersh = document.getElementById('dop-f-perusahaan').value.trim().toLowerCase();
  const fPill  = document.getElementById('dop-f-pillar').value.trim().toLowerCase();

  _dopSelected.clear();
  document.getElementById('dop-select-all').checked = false;

  let visible = 0;
  document.querySelectorAll('#dop-tbody .dop-row').forEach(row => {
    const match =
      row.dataset.code.includes(fCode) &&
      row.dataset.nama.includes(fNama) &&
      row.dataset.pam.includes(fPam)   &&
      row.dataset.cat1.includes(fCat1) &&
      row.dataset.cat2.includes(fCat2) &&
      row.dataset.perusahaan.includes(fPersh) &&
      row.dataset.pillar.includes(fPill);
    row.style.display = match ? '' : 'none';
    if (match) visible++;
    const cb = row.querySelector('.dop-cb');
    if (cb) cb.checked = false;
  });
  _dopUpdateInfo(visible);
}

function dopClearFilter() {
  document.querySelectorAll('.dop-filter').forEach(el => el.value = '');
  dopFilter();
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
  document.getElementById('dop-info').textContent = `${sel} dipilih | ${totalVisible} total`;
  const btn  = document.getElementById('dop-update-btn');
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
  if (data.ok) setTimeout(() => location.reload(), 800);
}
```

- [ ] **Step 5.2: Daftarkan init di event DOMContentLoaded**

Cari blok `document.addEventListener('DOMContentLoaded', ...)`. Tambahkan baris berikut di dalamnya:

```javascript
  _dopUpdateInfo(document.querySelectorAll('#dop-tbody .dop-row').length);
```

- [ ] **Step 5.3: Test manual filter**

1. Buka `http://localhost:8080/payment-memo/` → klik tab "Days of PAM"
2. Ketik di filter "Pillar" → baris yang tidak cocok tersembunyi
3. Klik "Select All Terfilter" → semua baris terfilter tercentang, counter berubah
4. Klik "Bersihkan" → semua filter reset, semua baris tampil, selection bersih

- [ ] **Step 5.4: Test manual bulk update**

1. Pilih beberapa baris
2. Isi "Tgl Receive" dengan tanggal
3. Klik "Update Terpilih" → harus muncul toast sukses, halaman reload
4. Verifikasi: kolom Tgl Receive baris tersebut sekarang berisi tanggal yang diisi

- [ ] **Step 5.5: Jalankan full test suite**

```bash
cd C:\Financehub\app
python -m pytest tests/ -v
```

Expected: semua test PASS (jumlah total = jumlah sebelumnya + 10 test baru)

- [ ] **Step 5.6: Commit**

```bash
cd C:\Financehub
git add app/templates/payment_memo/index.html
git commit -m "feat(days-of-pam): add client-side filter, checkbox selection, bulk date update JS"
```

---

## Verifikasi Akhir

- [ ] Jalankan `python -m pytest tests/ -v` → semua PASS
- [ ] Buka tab "Days of PAM": tabel tampil dengan data
- [ ] Filter real-time bekerja untuk semua 7 kolom teks
- [ ] Select All hanya memilih baris yang terfilter
- [ ] Update dengan 0 selection: tombol disabled
- [ ] Update tanpa tanggal diisi: toast error
- [ ] Update berhasil: toast sukses + reload + data terbaru tampil
