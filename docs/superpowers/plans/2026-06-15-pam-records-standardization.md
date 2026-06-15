# PAM Records Standardization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Standarisasi `pam_records` sebagai sumber data tunggal untuk semua tab PAM (AGRI/APP/LAND/SETF), dengan 4 relational lines tables per pillar, rename SML→LAND, dan import data dari Excel.

**Architecture:** `pam_records` ditambah kolom `mata_uang`, `dpp`, `ppn`, `pillar`. Tiap pillar punya table lines sendiri (`agri_pam_lines`, `app_pam_lines`, `land_pam_lines`, `setf_pam_lines`) yang relational ke `pam_records.id`. Service function `get_pam_by_pillar` JOIN kedua table. UI tabs masing-masing memanggil endpoint yang sama dengan parameter pillar berbeda.

**Tech Stack:** Python/Flask, SQLite, openpyxl (migration script), Jinja2 template

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `app/database.py` | Modify | ALTER TABLE + CREATE TABLE 4 lines tables |
| `app/modules/payment_memo/service.py` | Modify | Tambah `get_pam_by_pillar`, `upsert_pam_lines` |
| `app/modules/payment_memo/routes.py` | Modify | Tambah 2 route baru (GET by-pillar, PATCH lines) |
| `app/templates/payment_memo/index.html` | Modify | Rename SML→LAND, update tabs, kolom baru |
| `scripts/migrate_pam_excel.py` | Create | One-time import Excel → pam_records + lines |
| `app/tests/test_pam_standardization.py` | Create | Tests T1–T3 |

---

## Task 1: Schema Migration

**Files:**
- Modify: `app/database.py` (function `migrate_db`, baris ~662)
- Test: `app/tests/test_pam_standardization.py` (baru)

- [ ] **Step 1: Tulis test yang akan gagal**

Buat file `app/tests/test_pam_standardization.py`:

```python
import os, sys, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config
config.DB_PATH = os.path.join(os.path.dirname(__file__), "test_pam_std.db")

from database import init_db, get_conn

@pytest.fixture(autouse=True)
def clean_db():
    if os.path.exists(config.DB_PATH):
        os.remove(config.DB_PATH)
    init_db()
    yield
    if os.path.exists(config.DB_PATH):
        os.remove(config.DB_PATH)


def _columns(conn, table):
    return [r["name"] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]


def test_pam_records_has_new_columns():
    conn = get_conn()
    cols = _columns(conn, "pam_records")
    conn.close()
    assert "mata_uang" in cols
    assert "dpp"       in cols
    assert "ppn"       in cols
    assert "pillar"    in cols


def test_agri_pam_lines_table_exists():
    conn = get_conn()
    cols = _columns(conn, "agri_pam_lines")
    conn.close()
    expected = ["id", "pam_id", "no_vendor", "nama_vendor",
                "tgl_terima_doc", "tgl_proses", "tgl_verifikasi_tax",
                "tgl_approval_1", "tgl_approval_2", "tgl_approval_3",
                "tgl_kirim", "created_at", "updated_at"]
    for col in expected:
        assert col in cols, f"Missing column: {col}"


def test_app_pam_lines_table_exists():
    conn = get_conn()
    cols = _columns(conn, "app_pam_lines")
    conn.close()
    assert "pam_id" in cols
    assert "tgl_approval_1" in cols


def test_land_pam_lines_table_exists():
    conn = get_conn()
    cols = _columns(conn, "land_pam_lines")
    conn.close()
    assert "pam_id" in cols
    assert "tgl_kirim" in cols


def test_setf_pam_lines_table_exists():
    conn = get_conn()
    cols = _columns(conn, "setf_pam_lines")
    conn.close()
    assert "pam_id" in cols
    assert "tgl_verifikasi_tax" in cols
```

- [ ] **Step 2: Jalankan test, verifikasi FAIL**

```
cd C:\Financehub\app
pytest tests/test_pam_standardization.py -v
```
Expected: 5 tests FAIL (`OperationalError: no such table` atau `AssertionError`)

- [ ] **Step 3: Implementasi — tambah ke `migrate_db()` di `app/database.py`**

Cari blok `# pam_records — add tanggal_bayar and source if missing` (baris ~662) dan tambah setelah blok itu:

```python
    # pam_records — add standardization columns (mata_uang, dpp, ppn, pillar)
    for col_def in [
        "mata_uang TEXT DEFAULT 'IDR'",
        "dpp       INTEGER DEFAULT 0",
        "ppn       INTEGER DEFAULT 0",
        "pillar    TEXT",
    ]:
        try:
            conn.execute(f"ALTER TABLE pam_records ADD COLUMN {col_def}")
            conn.commit()
        except Exception:
            pass

    # pam lines tables per pillar (all identical schema initially)
    _PAM_LINES_DDL = """
        CREATE TABLE IF NOT EXISTS {tbl} (
            id                 INTEGER PRIMARY KEY AUTOINCREMENT,
            pam_id             INTEGER NOT NULL REFERENCES pam_records(id) ON DELETE CASCADE,
            no_vendor          TEXT,
            nama_vendor        TEXT,
            tgl_terima_doc     TEXT,
            tgl_proses         TEXT,
            tgl_verifikasi_tax TEXT,
            tgl_approval_1     TEXT,
            tgl_approval_2     TEXT,
            tgl_approval_3     TEXT,
            tgl_kirim          TEXT,
            created_at         TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at         TEXT
        )"""
    for tbl in ["agri_pam_lines", "app_pam_lines", "land_pam_lines", "setf_pam_lines"]:
        try:
            conn.execute(_PAM_LINES_DDL.format(tbl=tbl))
            conn.commit()
        except Exception:
            pass
    for tbl in ["agri_pam_lines", "app_pam_lines", "land_pam_lines", "setf_pam_lines"]:
        try:
            conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{tbl}_pam ON {tbl}(pam_id)")
            conn.commit()
        except Exception:
            pass
```

- [ ] **Step 4: Jalankan test, verifikasi PASS**

```
cd C:\Financehub\app
pytest tests/test_pam_standardization.py -v
```
Expected: 5 tests PASS

- [ ] **Step 5: Commit**

```
git add app/database.py app/tests/test_pam_standardization.py
git commit -m "feat: add pam_records pillar columns + 4 per-pillar lines tables"
```

---

## Task 2: Service Functions

**Files:**
- Modify: `app/modules/payment_memo/service.py`
- Test: `app/tests/test_pam_standardization.py`

- [ ] **Step 1: Tambah tests ke `app/tests/test_pam_standardization.py`**

Append di akhir file:

```python
# ── Task 2: Service ─────────────────────────────────────────────────────────

from modules.payment_memo.service import get_pam_by_pillar, upsert_pam_lines

COMPANY_ID = 2


def _seed_pam(conn, pam_no, pillar):
    conn.execute(
        """INSERT INTO pam_records
           (company_id, pam_no, pam_date, gl_account, cost_center, pt,
            requestors_name, keterangan, mata_uang, dpp, ppn,
            total_amount, due_date, status, source, pillar)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (COMPANY_ID, pam_no, "2026-06-01", "70110230", "1008C1POFF",
         "PT. SMART Tbk", "Jany Turkanda", "Test",
         "IDR", 9000000, 0, 9000000, "2026-06-30", "open", "beasiswa", pillar)
    )
    conn.commit()
    return conn.execute(
        "SELECT id FROM pam_records WHERE pam_no=?", (pam_no,)
    ).fetchone()["id"]


def test_get_pam_by_pillar_returns_correct_rows():
    conn = get_conn()
    _seed_pam(conn, "PAM-001-ETF-06-2026", "AGRI")
    _seed_pam(conn, "PAM-002-ETF-06-2026", "APP")
    conn.close()

    rows = get_pam_by_pillar(COMPANY_ID, "AGRI")
    assert len(rows) == 1
    assert rows[0]["pam_no"] == "PAM-001-ETF-06-2026"
    assert rows[0]["pillar"] == "AGRI"


def test_get_pam_by_pillar_includes_lines_columns():
    conn = get_conn()
    pam_id = _seed_pam(conn, "PAM-003-ETF-06-2026", "APP")
    conn.execute(
        """INSERT INTO app_pam_lines (pam_id, no_vendor, nama_vendor, tgl_approval_1)
           VALUES (?,?,?,?)""",
        (pam_id, "V-001", "PT. Maju", "2026-06-05")
    )
    conn.commit()
    conn.close()

    rows = get_pam_by_pillar(COMPANY_ID, "APP")
    assert len(rows) == 1
    assert rows[0]["no_vendor"]      == "V-001"
    assert rows[0]["nama_vendor"]    == "PT. Maju"
    assert rows[0]["tgl_approval_1"] == "2026-06-05"


def test_get_pam_by_pillar_left_join_no_lines_shows_row():
    conn = get_conn()
    _seed_pam(conn, "PAM-004-ETF-06-2026", "LAND")
    conn.close()

    rows = get_pam_by_pillar(COMPANY_ID, "LAND")
    assert len(rows) == 1
    assert rows[0]["pam_no"]    == "PAM-004-ETF-06-2026"
    assert rows[0]["no_vendor"] is None   # no lines row yet


def test_upsert_pam_lines_inserts_new():
    conn = get_conn()
    pam_id = _seed_pam(conn, "PAM-005-ETF-06-2026", "AGRI")
    conn.close()

    result = upsert_pam_lines(pam_id, "AGRI", {
        "no_vendor": "V-002",
        "nama_vendor": "PT. Agro",
        "tgl_terima_doc": "2026-06-02",
    }, COMPANY_ID)
    assert result["ok"] is True

    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM agri_pam_lines WHERE pam_id=?", (pam_id,)
    ).fetchone()
    conn.close()
    assert row is not None
    assert row["no_vendor"]      == "V-002"
    assert row["tgl_terima_doc"] == "2026-06-02"


def test_upsert_pam_lines_updates_existing():
    conn = get_conn()
    pam_id = _seed_pam(conn, "PAM-006-ETF-06-2026", "SETF")
    conn.execute(
        "INSERT INTO setf_pam_lines (pam_id, no_vendor) VALUES (?,?)",
        (pam_id, "OLD-001")
    )
    conn.commit()
    conn.close()

    result = upsert_pam_lines(pam_id, "SETF", {"no_vendor": "NEW-001"}, COMPANY_ID)
    assert result["ok"] is True

    conn = get_conn()
    row = conn.execute(
        "SELECT no_vendor FROM setf_pam_lines WHERE pam_id=?", (pam_id,)
    ).fetchone()
    conn.close()
    assert row["no_vendor"] == "NEW-001"


def test_upsert_pam_lines_invalid_pillar():
    result = upsert_pam_lines(1, "UNKNOWN", {"no_vendor": "X"}, COMPANY_ID)
    assert result["ok"] is False


def test_upsert_pam_lines_wrong_company_rejected():
    conn = get_conn()
    pam_id = _seed_pam(conn, "PAM-007-ETF-06-2026", "APP")
    conn.close()

    result = upsert_pam_lines(pam_id, "APP", {"no_vendor": "X"}, company_id=99)
    assert result["ok"] is False
```

- [ ] **Step 2: Jalankan, verifikasi FAIL**

```
cd C:\Financehub\app
pytest tests/test_pam_standardization.py::test_get_pam_by_pillar_returns_correct_rows -v
```
Expected: FAIL (`ImportError` atau `AttributeError`)

- [ ] **Step 3: Implementasi di `app/modules/payment_memo/service.py`**

Cari baris `_IPAY_PAM_PREFIX = {` (baris ~228) dan tambah konstanta di atasnya:

```python
_VALID_PILLARS = {"AGRI", "APP", "LAND", "SETF"}
_PILLAR_LINES_TABLE = {
    "AGRI": "agri_pam_lines",
    "APP":  "app_pam_lines",
    "LAND": "land_pam_lines",
    "SETF": "setf_pam_lines",
}
```

Tambah dua fungsi baru setelah konstanta tersebut:

```python
def get_pam_by_pillar(company_id: int, pillar: str,
                      search: str = "", bulan: str = "", tahun: str = "") -> list:
    """Return pam_records LEFT JOIN {pillar}_pam_lines filtered by pillar."""
    if pillar not in _VALID_PILLARS:
        return []
    tbl = _PILLAR_LINES_TABLE[pillar]
    sql = f"""
        SELECT pr.*,
               pl.id         AS lines_id,
               pl.no_vendor, pl.nama_vendor,
               pl.tgl_terima_doc, pl.tgl_proses, pl.tgl_verifikasi_tax,
               pl.tgl_approval_1, pl.tgl_approval_2, pl.tgl_approval_3,
               pl.tgl_kirim
        FROM pam_records pr
        LEFT JOIN {tbl} pl ON pl.pam_id = pr.id
        WHERE pr.company_id = ? AND pr.pillar = ?
    """
    params = [company_id, pillar]
    if search:
        q       = f"%{search}%"
        sql    += " AND (pr.pam_no LIKE ? OR pr.pt LIKE ? OR pr.keterangan LIKE ?)"
        params += [q, q, q]
    if bulan:
        sql    += " AND strftime('%m', pr.pam_date) = ?"
        params += [bulan.zfill(2)]
    if tahun:
        sql    += " AND strftime('%Y', pr.pam_date) = ?"
        params += [tahun]
    sql += " ORDER BY pr.pam_date DESC"
    conn = get_conn()
    rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
    conn.close()
    return rows


def upsert_pam_lines(pam_id: int, pillar: str, data: dict, company_id: int) -> dict:
    """Insert or update one lines row for the given pam_id and pillar."""
    if pillar not in _VALID_PILLARS:
        return {"ok": False, "pesan": f"Pillar tidak valid: {pillar}"}
    tbl = _PILLAR_LINES_TABLE[pillar]
    ALLOWED = {"no_vendor", "nama_vendor", "tgl_terima_doc", "tgl_proses",
               "tgl_verifikasi_tax", "tgl_approval_1", "tgl_approval_2",
               "tgl_approval_3", "tgl_kirim"}
    fields = {k: v for k, v in data.items() if k in ALLOWED}
    if not fields:
        return {"ok": False, "pesan": "Tidak ada field yang valid."}
    conn = get_conn()
    # verify PAM belongs to company
    pam = conn.execute(
        "SELECT id FROM pam_records WHERE id=? AND company_id=?",
        (pam_id, company_id)
    ).fetchone()
    if not pam:
        conn.close()
        return {"ok": False, "pesan": "PAM tidak ditemukan."}
    existing = conn.execute(
        f"SELECT id FROM {tbl} WHERE pam_id=?", (pam_id,)
    ).fetchone()
    now = _ts()
    if existing:
        set_clause = ", ".join(f"{k}=?" for k in fields)
        vals       = list(fields.values()) + [now, pam_id]
        conn.execute(
            f"UPDATE {tbl} SET {set_clause}, updated_at=? WHERE pam_id=?", vals
        )
    else:
        cols = ", ".join(["pam_id"] + list(fields.keys()) + ["created_at"])
        ph   = ", ".join(["?"] * (len(fields) + 2))
        vals = [pam_id] + list(fields.values()) + [now]
        conn.execute(f"INSERT INTO {tbl} ({cols}) VALUES ({ph})", vals)
    conn.commit()
    conn.close()
    return {"ok": True}
```

- [ ] **Step 4: Jalankan semua tests, verifikasi PASS**

```
cd C:\Financehub\app
pytest tests/test_pam_standardization.py -v
```
Expected: semua tests PASS

- [ ] **Step 5: Pastikan tests lama tidak rusak**

```
cd C:\Financehub\app
pytest tests/test_pam_service.py -v
```
Expected: semua PASS

- [ ] **Step 6: Commit**

```
git add app/modules/payment_memo/service.py app/tests/test_pam_standardization.py
git commit -m "feat: add get_pam_by_pillar and upsert_pam_lines service functions"
```

---

## Task 3: Routes

**Files:**
- Modify: `app/modules/payment_memo/routes.py`

- [ ] **Step 1: Tambah import di `app/modules/payment_memo/routes.py`**

Cari baris import service functions (baris ~6) dan tambah `get_pam_by_pillar, upsert_pam_lines` ke list import:

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
    set_memo_tanggal_bayar,
    get_fiori_list, bulk_update_fiori_dates,
    update_fiori_status, cancel_fiori_record,
    get_fiori_detail, update_fiori_record,
    get_sml_list, bulk_update_sml_dates,
    update_sml_status, cancel_sml_record,
    get_open_etf_pa_for_pam, create_pam_from_etf_pa, set_pam_tanggal_bayar_agri,
    get_next_pam_no, save_pa_payment, check_pam_no_exists,
    get_pam_by_pillar, upsert_pam_lines,
)
```

- [ ] **Step 2: Tambah 2 route baru di `routes.py`**

Tambah setelah route `/sml/<int:record_id>/cancel` (baris ~540):

```python
# ── PAM by-pillar endpoints (standardized) ──────────────────────────────────

@bp.route("/by-pillar/<pillar>")
@jwt_html_required
def pam_by_pillar(pillar):
    """Return pam_records + lines for the given pillar (AGRI/APP/LAND/SETF)."""
    company_id = session.get("company_id")
    search     = request.args.get("search", "").strip()
    bulan      = request.args.get("bulan", "").strip()
    tahun      = request.args.get("tahun", "").strip()
    rows       = get_pam_by_pillar(company_id, pillar.upper(), search, bulan, tahun)
    return jsonify({"ok": True, "rows": rows})


@bp.route("/pam/<int:pam_id>/lines", methods=["PATCH"])
@jwt_html_required
def update_pam_lines(pam_id):
    """Upsert lines row (U-AC columns) for a single PAM record."""
    company_id = session.get("company_id")
    data       = request.get_json(force=True) or {}
    pillar     = data.pop("pillar", "").upper()
    result     = upsert_pam_lines(pam_id, pillar, data, company_id)
    return jsonify(result)
```

- [ ] **Step 3: Smoke-test route dengan curl (atau start server manual)**

```
cd C:\Financehub\app
python run.py
```

Buka browser / curl (dengan valid JWT cookie):
```
GET /payment-memo/by-pillar/AGRI
```
Expected: `{"ok": true, "rows": [...]}`

Jika server tidak bisa distart sekarang, skip ke Step 4 dan lakukan smoke-test setelah Task 5.

- [ ] **Step 4: Commit**

```
git add app/modules/payment_memo/routes.py
git commit -m "feat: add GET /by-pillar/<pillar> and PATCH /pam/<id>/lines routes"
```

---

## Task 4: Migration Script (Excel → DB)

**Files:**
- Create: `scripts/migrate_pam_excel.py`

- [ ] **Step 1: Verifikasi lokasi Excel**

```
ls "C:\Users\25010160\Downloads\query_1-2026-06-15_85459.xlsx"
```
Expected: file ada

- [ ] **Step 2: Buat `scripts/migrate_pam_excel.py`**

```python
"""
One-time migration: import pam_records + pam_lines dari Excel.

Usage:
    cd C:\Financehub\app
    python ..\scripts\migrate_pam_excel.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__) + "/../app")
import config
# jalankan dengan DB production
# config.DB_PATH sudah default ke financehub.db

import openpyxl
from database import get_conn, migrate_db

EXCEL_PATH = r"C:\Users\25010160\Downloads\query_1-2026-06-15_85459.xlsx"

_PILLAR_LINES_TABLE = {
    "AGRI": "agri_pam_lines",
    "APP":  "app_pam_lines",
    "LAND": "land_pam_lines",
    "SETF": "setf_pam_lines",
}

def _val(v):
    """Return None for empty/None values."""
    if v is None or v == "":
        return None
    return v


def migrate():
    # Pastikan schema sudah up-to-date
    migrate_db()

    wb = openpyxl.load_workbook(EXCEL_PATH)
    ws = wb.active

    conn = get_conn()
    inserted = 0
    updated  = 0
    lines_created = 0

    for row in ws.iter_rows(min_row=2, values_only=True):
        # Columns A-T (index 0-19)
        (_, company_id, pam_no, pam_date, gl_account, cost_center, pt,
         requestors_name, keterangan, mata_uang, dpp, ppn, total_amount,
         due_date, status, created_at, updated_at, tanggal_bayar, source,
         pillar) = row[:20]

        # Skip rows with no pam_no
        if not pam_no:
            continue

        pillar = (pillar or "").strip().upper()
        if pillar not in _PILLAR_LINES_TABLE:
            print(f"  SKIP {pam_no}: pillar '{pillar}' tidak dikenal")
            continue

        # Columns U-AC (index 20-28)
        line_cols = row[20:29]  # U(20)..AC(28)
        (no_vendor, nama_vendor, tgl_terima_doc, tgl_proses,
         tgl_verifikasi_tax, tgl_approval_1, tgl_approval_2,
         tgl_approval_3, tgl_kirim) = line_cols

        # INSERT OR REPLACE pam_records
        existing = conn.execute(
            "SELECT id FROM pam_records WHERE pam_no=?", (pam_no,)
        ).fetchone()

        if existing:
            conn.execute(
                """UPDATE pam_records SET
                   company_id=?, pam_date=?, gl_account=?, cost_center=?, pt=?,
                   requestors_name=?, keterangan=?, mata_uang=?, dpp=?, ppn=?,
                   total_amount=?, due_date=?, status=?, created_at=?,
                   updated_at=?, tanggal_bayar=?, source=?, pillar=?
                   WHERE pam_no=?""",
                (_val(company_id), _val(pam_date), _val(gl_account),
                 _val(cost_center), _val(pt), _val(requestors_name),
                 _val(keterangan), _val(mata_uang) or "IDR",
                 _val(dpp) or 0, _val(ppn) or 0,
                 _val(total_amount) or 0, _val(due_date),
                 _val(status) or "open", _val(created_at), _val(updated_at),
                 _val(tanggal_bayar), _val(source) or "beasiswa", pillar,
                 pam_no)
            )
            pam_id = existing["id"]
            updated += 1
        else:
            cur = conn.execute(
                """INSERT INTO pam_records
                   (company_id, pam_no, pam_date, gl_account, cost_center, pt,
                    requestors_name, keterangan, mata_uang, dpp, ppn,
                    total_amount, due_date, status, created_at, updated_at,
                    tanggal_bayar, source, pillar)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (_val(company_id), pam_no, _val(pam_date), _val(gl_account) or "70110230",
                 _val(cost_center), _val(pt), _val(requestors_name) or "Jany Turkanda",
                 _val(keterangan), _val(mata_uang) or "IDR",
                 _val(dpp) or 0, _val(ppn) or 0,
                 _val(total_amount) or 0, _val(due_date),
                 _val(status) or "open", _val(created_at), _val(updated_at),
                 _val(tanggal_bayar), _val(source) or "beasiswa", pillar)
            )
            pam_id = cur.lastrowid
            inserted += 1

        # Upsert lines row
        tbl = _PILLAR_LINES_TABLE[pillar]
        existing_line = conn.execute(
            f"SELECT id FROM {tbl} WHERE pam_id=?", (pam_id,)
        ).fetchone()

        if existing_line:
            conn.execute(
                f"""UPDATE {tbl} SET
                    no_vendor=?, nama_vendor=?, tgl_terima_doc=?, tgl_proses=?,
                    tgl_verifikasi_tax=?, tgl_approval_1=?, tgl_approval_2=?,
                    tgl_approval_3=?, tgl_kirim=?
                    WHERE pam_id=?""",
                (_val(no_vendor), _val(nama_vendor), _val(tgl_terima_doc),
                 _val(tgl_proses), _val(tgl_verifikasi_tax), _val(tgl_approval_1),
                 _val(tgl_approval_2), _val(tgl_approval_3), _val(tgl_kirim),
                 pam_id)
            )
        else:
            conn.execute(
                f"""INSERT INTO {tbl}
                    (pam_id, no_vendor, nama_vendor, tgl_terima_doc, tgl_proses,
                     tgl_verifikasi_tax, tgl_approval_1, tgl_approval_2,
                     tgl_approval_3, tgl_kirim)
                    VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (pam_id, _val(no_vendor), _val(nama_vendor), _val(tgl_terima_doc),
                 _val(tgl_proses), _val(tgl_verifikasi_tax), _val(tgl_approval_1),
                 _val(tgl_approval_2), _val(tgl_approval_3), _val(tgl_kirim))
            )
            lines_created += 1

    conn.commit()
    conn.close()
    print(f"Migration selesai:")
    print(f"  pam_records inserted: {inserted}")
    print(f"  pam_records updated:  {updated}")
    print(f"  pam_lines created:    {lines_created}")


if __name__ == "__main__":
    migrate()
```

- [ ] **Step 3: Backup DB sebelum run**

```
cd C:\Financehub\app
python -c "import shutil; shutil.copy('financehub.db', 'financehub.db.bak_pam_std_20260615')"
```

- [ ] **Step 4: Jalankan migration script**

```
cd C:\Financehub\app
python ..\scripts\migrate_pam_excel.py
```
Expected output:
```
Migration selesai:
  pam_records inserted: X
  pam_records updated:  Y
  pam_lines created:    Z
```

- [ ] **Step 5: Verifikasi hasil**

```
cd C:\Financehub\app
python -c "
from database import get_conn
conn = get_conn()
print('pam_records total:', conn.execute('SELECT COUNT(*) FROM pam_records').fetchone()[0])
print('pillar AGRI:', conn.execute(\"SELECT COUNT(*) FROM pam_records WHERE pillar='AGRI'\").fetchone()[0])
print('pillar APP:', conn.execute(\"SELECT COUNT(*) FROM pam_records WHERE pillar='APP'\").fetchone()[0])
print('pillar LAND:', conn.execute(\"SELECT COUNT(*) FROM pam_records WHERE pillar='LAND'\").fetchone()[0])
print('pillar SETF:', conn.execute(\"SELECT COUNT(*) FROM pam_records WHERE pillar='SETF'\").fetchone()[0])
print('agri_pam_lines:', conn.execute('SELECT COUNT(*) FROM agri_pam_lines').fetchone()[0])
print('app_pam_lines:', conn.execute('SELECT COUNT(*) FROM app_pam_lines').fetchone()[0])
conn.close()
"
```
Expected: count sesuai dengan jumlah baris di Excel per pillar.

- [ ] **Step 6: Commit**

```
git add scripts/migrate_pam_excel.py
git commit -m "feat: add Excel-to-SQLite migration script for pam_records standardization"
```

---

## Task 5: UI Update

**Files:**
- Modify: `app/templates/payment_memo/index.html`

- [ ] **Step 1: Rename SML → LAND di tab navigation**

Di `index.html`, cari tab label SML (biasanya dalam bentuk `<button` atau `<li` dengan teks "SML") dan ganti menjadi "LAND":

```html
<!-- Sebelum -->
<button ... data-tab="sml">SML</button>
<!-- Sesudah -->
<button ... data-tab="land">LAND</button>
```

Juga update semua atribut `data-tab="sml"` dan referensi ID seperti `id="tab-sml"`, `id="table-sml"` → ganti "sml" → "land" secara konsisten di seluruh file.

- [ ] **Step 2: Update JavaScript fetch untuk semua 4 tab**

Cari fungsi JavaScript yang memuat data tab AGRI/APP/SML/SETF (biasanya berisi fetch ke `/payment-memo/fiori` atau `/payment-memo/sml`). Ganti semua dengan endpoint baru:

```javascript
// Fungsi generik fetch per pillar
function loadPillarTab(pillar, search = "", bulan = "", tahun = "") {
    const params = new URLSearchParams({ search, bulan, tahun });
    fetch(`/payment-memo/by-pillar/${pillar}?${params}`, {
        headers: { "Authorization": "Bearer " + getJwt() }
    })
    .then(r => r.json())
    .then(data => {
        if (data.ok) renderPillarTable(pillar, data.rows);
    });
}

// Panggil saat tab aktif
// AGRI: loadPillarTab("AGRI")
// APP:  loadPillarTab("APP")
// LAND: loadPillarTab("LAND")   ← sebelumnya SML
// SETF: loadPillarTab("SETF")
```

- [ ] **Step 3: Update render table untuk tampilkan kolom baru**

Fungsi `renderPillarTable` (atau render function per tab) perlu menampilkan kolom:

Header (dari `pam_records`): `pam_no`, `pam_date`, `pt`, `keterangan`, `mata_uang`, `dpp`, `ppn`, `total_amount`, `due_date`, `status`, `tanggal_bayar`

Lines (dari pam_lines): `no_vendor`, `nama_vendor`, `tgl_terima_doc`, `tgl_proses`, `tgl_verifikasi_tax`, `tgl_approval_1`, `tgl_approval_2`, `tgl_approval_3`, `tgl_kirim`

```javascript
function renderPillarTable(pillar, rows) {
    const tbodyId = `tbody-${pillar.toLowerCase()}`;
    const tbody = document.getElementById(tbodyId);
    tbody.innerHTML = rows.map(r => `
        <tr data-pam-id="${r.id}" data-pillar="${pillar}">
            <td>${r.pam_no || ""}</td>
            <td>${r.pam_date || ""}</td>
            <td>${r.pt || ""}</td>
            <td>${r.keterangan || ""}</td>
            <td>${r.mata_uang || "IDR"}</td>
            <td>${(r.dpp || 0).toLocaleString("id-ID")}</td>
            <td>${(r.ppn || 0).toLocaleString("id-ID")}</td>
            <td>${(r.total_amount || 0).toLocaleString("id-ID")}</td>
            <td>${r.due_date || ""}</td>
            <td><span class="badge status-${r.status}">${r.status || ""}</span></td>
            <td>${r.tanggal_bayar || ""}</td>
            <td class="lines-cell" data-field="no_vendor">${r.no_vendor || ""}</td>
            <td class="lines-cell" data-field="nama_vendor">${r.nama_vendor || ""}</td>
            <td class="lines-cell date-cell" data-field="tgl_terima_doc">${r.tgl_terima_doc || ""}</td>
            <td class="lines-cell date-cell" data-field="tgl_proses">${r.tgl_proses || ""}</td>
            <td class="lines-cell date-cell" data-field="tgl_verifikasi_tax">${r.tgl_verifikasi_tax || ""}</td>
            <td class="lines-cell date-cell" data-field="tgl_approval_1">${r.tgl_approval_1 || ""}</td>
            <td class="lines-cell date-cell" data-field="tgl_approval_2">${r.tgl_approval_2 || ""}</td>
            <td class="lines-cell date-cell" data-field="tgl_approval_3">${r.tgl_approval_3 || ""}</td>
            <td class="lines-cell date-cell" data-field="tgl_kirim">${r.tgl_kirim || ""}</td>
        </tr>
    `).join("");
    attachLinesCellHandlers(pillar);
}
```

- [ ] **Step 4: Tambah handler inline-edit untuk lines date cells**

```javascript
function attachLinesCellHandlers(pillar) {
    document.querySelectorAll(`#tbody-${pillar.toLowerCase()} .date-cell`).forEach(cell => {
        cell.addEventListener("click", function () {
            if (this.querySelector("input")) return;
            const field   = this.dataset.field;
            const pamId   = this.closest("tr").dataset.pamId;
            const current = this.textContent.trim();
            const input   = document.createElement("input");
            input.type    = "date";
            input.value   = current;
            input.className = "form-control form-control-sm";
            this.innerHTML = "";
            this.appendChild(input);
            input.focus();
            input.addEventListener("blur", function () {
                const newVal = this.value;
                fetch(`/payment-memo/pam/${pamId}/lines`, {
                    method: "PATCH",
                    headers: {
                        "Content-Type": "application/json",
                        "Authorization": "Bearer " + getJwt()
                    },
                    body: JSON.stringify({ pillar, [field]: newVal })
                })
                .then(r => r.json())
                .then(res => {
                    cell.textContent = res.ok ? newVal : current;
                });
            });
        });
    });
}
```

- [ ] **Step 5: Update `<thead>` tiap tab dengan kolom baru**

Setiap tab (AGRI/APP/LAND/SETF) perlu `<thead>` yang sama:

```html
<thead>
  <tr>
    <th>No. PAM</th>
    <th>Tgl PAM</th>
    <th>PT</th>
    <th>Keterangan</th>
    <th>Mata Uang</th>
    <th>DPP</th>
    <th>PPN</th>
    <th>Total</th>
    <th>Due Date</th>
    <th>Status</th>
    <th>Tgl Bayar</th>
    <th>No. Vendor</th>
    <th>Nama Vendor</th>
    <th>Terima Dok</th>
    <th>Proses</th>
    <th>Verifikasi Tax</th>
    <th>Approval 1</th>
    <th>Approval 2</th>
    <th>Approval 3</th>
    <th>Kirim</th>
  </tr>
</thead>
<tbody id="tbody-agri"></tbody>  <!-- ganti suffix per tab -->
```

- [ ] **Step 6: Panggil `loadPillarTab` saat tab aktif**

Tambah event listener di tab click handler:

```javascript
document.querySelectorAll("[data-tab]").forEach(btn => {
    btn.addEventListener("click", function () {
        const tab = this.dataset.tab.toUpperCase();
        if (["AGRI", "APP", "LAND", "SETF"].includes(tab)) {
            loadPillarTab(tab);
        }
    });
});
// Auto-load tab pertama yang aktif
loadPillarTab("AGRI");
```

- [ ] **Step 7: Test di browser**

Buka `http://localhost:5000/payment-memo`, pilih company ETF.
- Tab AGRI: harus menampilkan data dari pam_records pillar='AGRI' + agri_pam_lines
- Tab APP: data dari pillar='APP' + app_pam_lines
- Tab LAND: muncul (sebelumnya SML), data dari pillar='LAND' + land_pam_lines
- Tab SETF: data dari pillar='SETF' + setf_pam_lines
- Click cell date: input date muncul, blur → PATCH ke server → cell terupdate

- [ ] **Step 8: Commit**

```
git add app/templates/payment_memo/index.html
git commit -m "feat: update payment_memo tabs to use pillar-based PAM data, rename SML to LAND"
```

---

## Checklist Spec Coverage

- [x] T1: Tambah `mata_uang`, `dpp`, `ppn`, `pillar` ke `pam_records`
- [x] T1: Create 4 pam_lines tables (agri/app/land/setf)
- [x] T2: Service `get_pam_by_pillar` dengan LEFT JOIN
- [x] T2: Service `upsert_pam_lines` INSERT/UPDATE
- [x] T3: GET `/by-pillar/<pillar>` route
- [x] T3: PATCH `/pam/<id>/lines` route
- [x] T4: Migration script Excel → pam_records + lines
- [x] T5: UI tabs AGRI/APP/LAND/SETF menggunakan endpoint baru
- [x] T5: SML tab rename → LAND
- [x] T5: Kolom A-S + U-AC ditampilkan per tab
- [x] T5: Inline edit untuk lines date columns
