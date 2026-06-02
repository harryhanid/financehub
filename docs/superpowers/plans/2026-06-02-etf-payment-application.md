# ETF Payment Application Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Buat modul ETF Payment Application — PA header + lines per siswa, SLA date tracking, PAM auto-generate saat status → On Process.

**Architecture:** Dua tabel baru (`etf_pa` + `etf_pa_lines`) ditambahkan via `migrate_db()`. Service layer di `modules/etf_payment_application/service.py`, routes di `routes.py`, template satu halaman dengan collapsed list + modal buat/edit. Blueprint didaftarkan di `app.py`, sidebar link di `base.html` khusus company ETF.

**Tech Stack:** Python Flask, SQLite via `database.get_conn()`, Jinja2, vanilla JS (same pattern as existing modules), pytest untuk tests.

---

## File Map

| Aksi | File |
|---|---|
| Modify | `app/database.py` — tambah DDL + migrate block untuk `etf_pa` dan `etf_pa_lines` |
| Create | `app/modules/etf_payment_application/__init__.py` |
| Create | `app/modules/etf_payment_application/service.py` |
| Create | `app/modules/etf_payment_application/routes.py` |
| Create | `app/templates/etf_payment_application/index.html` |
| Modify | `app/app.py` — register blueprint |
| Modify | `app/templates/base.html` — sidebar link |
| Create | `app/tests/test_etf_pa_service.py` |

---

## Task 1: Database Migration

**Files:**
- Modify: `app/database.py`

- [ ] **Step 1: Tambahkan DDL ke konstanta `DDL` di `database.py`**

Di akhir string `DDL` (sebelum penutup `"""`), tambahkan:

```python
CREATE TABLE IF NOT EXISTS etf_pa (
    id                       INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id               INTEGER NOT NULL REFERENCES companies(id),
    pa_number                TEXT UNIQUE NOT NULL,
    tgl_payment_application  TEXT,
    tgl_surat_pengajuan      TEXT,
    doc_received_by_educ     TEXT,
    received_pa_from_educ    TEXT,
    checked_by_fincon        TEXT,
    approved_by_htj_1        TEXT,
    send_pa_back_to_educ     TEXT,
    pa_received_by_po_fin    TEXT,
    approval_by_htj_2        TEXT,
    nomor_pam                TEXT,
    tanggal_bayar            TEXT,
    keterangan               TEXT,
    status                   TEXT NOT NULL DEFAULT 'draft',
    created_at               TEXT NOT NULL,
    updated_at               TEXT
);

CREATE TABLE IF NOT EXISTS etf_pa_lines (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    pa_id                INTEGER NOT NULL REFERENCES etf_pa(id) ON DELETE CASCADE,
    student_id           INTEGER NOT NULL REFERENCES siswa(id),
    jenis_pembayaran     TEXT,
    semester             TEXT,
    tahun_ajaran         TEXT,
    ipk_sem_sebelumnya   REAL,
    jumlah_pembayaran    INTEGER DEFAULT 0
);
```

- [ ] **Step 2: Tambahkan migrate block di fungsi `migrate_db()`**

Di akhir fungsi `migrate_db()`, sebelum `conn.close()`:

```python
    # etf_pa + etf_pa_lines tables
    try:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS etf_pa (
                id                       INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id               INTEGER NOT NULL,
                pa_number                TEXT UNIQUE NOT NULL,
                tgl_payment_application  TEXT,
                tgl_surat_pengajuan      TEXT,
                doc_received_by_educ     TEXT,
                received_pa_from_educ    TEXT,
                checked_by_fincon        TEXT,
                approved_by_htj_1        TEXT,
                send_pa_back_to_educ     TEXT,
                pa_received_by_po_fin    TEXT,
                approval_by_htj_2        TEXT,
                nomor_pam                TEXT,
                tanggal_bayar            TEXT,
                keterangan               TEXT,
                status                   TEXT NOT NULL DEFAULT 'draft',
                created_at               TEXT NOT NULL,
                updated_at               TEXT)"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS etf_pa_lines (
                id                   INTEGER PRIMARY KEY AUTOINCREMENT,
                pa_id                INTEGER NOT NULL REFERENCES etf_pa(id) ON DELETE CASCADE,
                student_id           INTEGER NOT NULL,
                jenis_pembayaran     TEXT,
                semester             TEXT,
                tahun_ajaran         TEXT,
                ipk_sem_sebelumnya   REAL,
                jumlah_pembayaran    INTEGER DEFAULT 0)"""
        )
        conn.commit()
    except Exception:
        pass
```

- [ ] **Step 3: Verifikasi tabel terbuat**

```bash
cd C:\Financehub\app
python -c "from database import init_db; init_db(); from database import get_conn; c=get_conn(); print([r[0] for r in c.execute(\"SELECT name FROM sqlite_master WHERE type='table'\").fetchall()])"
```

Expected output includes: `etf_pa`, `etf_pa_lines`

- [ ] **Step 4: Commit**

```bash
git add app/database.py
git commit -m "feat(etf-pa): add etf_pa and etf_pa_lines tables to DDL and migrate_db"
```

---

## Task 2: Service Layer

**Files:**
- Create: `app/modules/etf_payment_application/__init__.py`
- Create: `app/modules/etf_payment_application/service.py`

- [ ] **Step 1: Buat `__init__.py` kosong**

```python
```
(file kosong)

- [ ] **Step 2: Tulis `service.py`**

```python
# modules/etf_payment_application/service.py
from datetime import datetime
from database import get_conn


def _ts():
    return datetime.now().isoformat(timespec="seconds")


def _latest_ipk(siswa_row: dict) -> float:
    """Return IPK sem terakhir yang tidak nol dari data siswa."""
    for i in range(10, 0, -1):
        val = siswa_row.get(f"ipk_sem{i}") or 0
        if val:
            return float(val)
    return 0.0


def get_siswa_autocomplete(company_id: int, q: str) -> list:
    """Return list siswa untuk autocomplete input (nama + id)."""
    conn = get_conn()
    rows = conn.execute(
        """SELECT id, code, nama, jenjang, angkatan, program, fakultas,
                  universitas, status,
                  ipk_sem1, ipk_sem2, ipk_sem3, ipk_sem4, ipk_sem5,
                  ipk_sem6, ipk_sem7, ipk_sem8, ipk_sem9, ipk_sem10
           FROM siswa
           WHERE company_id=? AND (nama LIKE ? OR code LIKE ?)
           ORDER BY nama LIMIT 20""",
        (company_id, f"%{q}%", f"%{q}%")
    ).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["ipk_terakhir"] = _latest_ipk(d)
        result.append(d)
    return result


def _gen_pa_number(company_id: int, conn) -> str:
    year = datetime.now().strftime("%Y")
    count = conn.execute(
        "SELECT COUNT(*) FROM etf_pa WHERE company_id=?", (company_id,)
    ).fetchone()[0]
    return f"PA/ETF/{count + 1:03d}/{year}"


def _gen_nomor_pam(company_id: int, conn) -> str:
    now = datetime.now()
    mm   = now.strftime("%m")
    yyyy = now.strftime("%Y")
    count = conn.execute(
        """SELECT COUNT(*) FROM etf_pa
           WHERE company_id=? AND nomor_pam IS NOT NULL
           AND strftime('%Y-%m', created_at)=?""",
        (company_id, f"{yyyy}-{mm}")
    ).fetchone()[0]
    return f"{count + 1:03d}-ETF-{mm}-{yyyy}"


def get_pa_list(company_id: int) -> list:
    """Return satu row per PA header, dengan aggregate count siswa dan total bayar."""
    conn = get_conn()
    rows = conn.execute(
        """SELECT p.*,
                  COUNT(l.id)          AS jml_siswa,
                  COALESCE(SUM(l.jumlah_pembayaran), 0) AS total_bayar
           FROM etf_pa p
           LEFT JOIN etf_pa_lines l ON l.pa_id = p.id
           WHERE p.company_id=?
           GROUP BY p.id
           ORDER BY p.created_at DESC""",
        (company_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_pa_lines(pa_id: int, company_id: int) -> list:
    """Return semua lines untuk satu PA, dengan data siswa di-JOIN."""
    conn = get_conn()
    rows = conn.execute(
        """SELECT l.*,
                  s.nama, s.code AS siswa_code, s.status AS status_pb,
                  s.universitas AS instansi_pendidikan,
                  s.angkatan AS angkatan_etf,
                  s.jenjang AS jenjang_pendidikan,
                  s.program AS program_beasiswa,
                  s.fakultas
           FROM etf_pa_lines l
           JOIN siswa s ON s.id = l.student_id
           JOIN etf_pa p ON p.id = l.pa_id
           WHERE l.pa_id=? AND p.company_id=?
           ORDER BY l.id""",
        (pa_id, company_id)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_pa(company_id: int, header: dict, lines: list) -> dict:
    """
    header keys: tgl_payment_application, tgl_surat_pengajuan, keterangan
    lines items: {student_id, jenis_pembayaran, semester, tahun_ajaran,
                  ipk_sem_sebelumnya, jumlah_pembayaran}
    """
    if not lines:
        return {"ok": False, "pesan": "Minimal 1 siswa harus diisi."}

    conn = get_conn()
    # validate all student_id belong to company
    for line in lines:
        sid = line.get("student_id")
        row = conn.execute(
            "SELECT id FROM siswa WHERE id=? AND company_id=?", (sid, company_id)
        ).fetchone()
        if not row:
            conn.close()
            return {"ok": False, "pesan": f"Siswa ID {sid} tidak ditemukan."}

    pa_number = _gen_pa_number(company_id, conn)
    ts = _ts()
    cur = conn.execute(
        """INSERT INTO etf_pa
           (company_id, pa_number, tgl_payment_application, tgl_surat_pengajuan,
            keterangan, status, created_at)
           VALUES (?,?,?,?,?,'draft',?)""",
        (company_id, pa_number,
         header.get("tgl_payment_application", ""),
         header.get("tgl_surat_pengajuan", ""),
         header.get("keterangan", ""),
         ts)
    )
    pa_id = cur.lastrowid

    for line in lines:
        conn.execute(
            """INSERT INTO etf_pa_lines
               (pa_id, student_id, jenis_pembayaran, semester,
                tahun_ajaran, ipk_sem_sebelumnya, jumlah_pembayaran)
               VALUES (?,?,?,?,?,?,?)""",
            (pa_id,
             line.get("student_id"),
             line.get("jenis_pembayaran", ""),
             line.get("semester", ""),
             line.get("tahun_ajaran", ""),
             line.get("ipk_sem_sebelumnya") or 0,
             line.get("jumlah_pembayaran") or 0)
        )

    conn.commit()
    conn.close()
    return {"ok": True, "pa_id": pa_id, "pa_number": pa_number,
            "pesan": f"Payment Application {pa_number} berhasil dibuat."}


def update_pa(pa_id: int, company_id: int, data: dict) -> dict:
    """
    Update SLA dates, keterangan, tanggal_bayar, nomor_pam, status.
    Jika status → on_process dan nomor_pam belum ada, auto-generate.
    """
    conn = get_conn()
    row = conn.execute(
        "SELECT id, status, nomor_pam FROM etf_pa WHERE id=? AND company_id=?",
        (pa_id, company_id)
    ).fetchone()
    if not row:
        conn.close()
        return {"ok": False, "pesan": "PA tidak ditemukan."}

    new_status  = data.get("status", row["status"])
    nomor_pam   = data.get("nomor_pam") or row["nomor_pam"]

    # auto-generate PAM number when transitioning to on_process
    if new_status == "on_process" and not nomor_pam:
        nomor_pam = _gen_nomor_pam(company_id, conn)

    conn.execute(
        """UPDATE etf_pa SET
            tgl_payment_application = ?,
            tgl_surat_pengajuan     = ?,
            doc_received_by_educ    = ?,
            received_pa_from_educ   = ?,
            checked_by_fincon       = ?,
            approved_by_htj_1       = ?,
            send_pa_back_to_educ    = ?,
            pa_received_by_po_fin   = ?,
            approval_by_htj_2       = ?,
            nomor_pam               = ?,
            tanggal_bayar           = ?,
            keterangan              = ?,
            status                  = ?,
            updated_at              = ?
           WHERE id=? AND company_id=?""",
        (data.get("tgl_payment_application", ""),
         data.get("tgl_surat_pengajuan", ""),
         data.get("doc_received_by_educ", ""),
         data.get("received_pa_from_educ", ""),
         data.get("checked_by_fincon", ""),
         data.get("approved_by_htj_1", ""),
         data.get("send_pa_back_to_educ", ""),
         data.get("pa_received_by_po_fin", ""),
         data.get("approval_by_htj_2", ""),
         nomor_pam,
         data.get("tanggal_bayar", ""),
         data.get("keterangan", ""),
         new_status,
         _ts(), pa_id, company_id)
    )
    conn.commit()
    conn.close()

    msg = f"PA berhasil diupdate."
    if new_status == "on_process" and nomor_pam and not row["nomor_pam"]:
        msg = f"PA pindah ke On Process. Nomor PAM: {nomor_pam}"
    return {"ok": True, "pesan": msg, "nomor_pam": nomor_pam}
```

- [ ] **Step 3: Commit**

```bash
git add app/modules/etf_payment_application/
git commit -m "feat(etf-pa): add service layer (get_pa_list, create_pa, update_pa, get_pa_lines)"
```

---

## Task 3: Tests

**Files:**
- Create: `app/tests/test_etf_pa_service.py`

- [ ] **Step 1: Tulis test file**

```python
# tests/test_etf_pa_service.py
import os, sys, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config
config.DB_PATH = os.path.join(os.path.dirname(__file__), "test_etf_pa.db")

from database import init_db, get_conn
from modules.etf_payment_application.service import (
    get_pa_list, create_pa, update_pa, get_pa_lines,
    get_siswa_autocomplete,
)

COMPANY_ID = 2  # ETF

@pytest.fixture(autouse=True)
def clean_db():
    if os.path.exists(config.DB_PATH):
        os.remove(config.DB_PATH)
    init_db()
    _seed()
    yield
    if os.path.exists(config.DB_PATH):
        os.remove(config.DB_PATH)


def _seed():
    conn = get_conn()
    conn.execute(
        """INSERT INTO siswa (company_id, code, nama, jenjang, angkatan,
           program, fakultas, universitas, status,
           ipk_sem1, ipk_sem2)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (COMPANY_ID, "1230001", "Budi Santoso", "S1", 2023,
         "SMART", "Teknik", "Univ. Indonesia", "Aktif", 3.5, 3.6)
    )
    conn.execute(
        """INSERT INTO siswa (company_id, code, nama, jenjang, angkatan,
           program, fakultas, universitas, status,
           ipk_sem1)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (COMPANY_ID, "2230001", "Ani Wijaya", "S2", 2023,
         "Polri", "Hukum", "Univ. Gajah Mada", "Aktif", 3.8)
    )
    conn.commit()
    conn.close()


def _student_id(code: str) -> int:
    conn = get_conn()
    row = conn.execute("SELECT id FROM siswa WHERE code=?", (code,)).fetchone()
    conn.close()
    return row["id"]


# --- create_pa ---

def test_create_pa_success():
    sid = _student_id("1230001")
    result = create_pa(COMPANY_ID, {
        "tgl_payment_application": "2026-06-01",
        "tgl_surat_pengajuan": "2026-06-01",
        "keterangan": "Test PA",
    }, [
        {"student_id": sid, "jenis_pembayaran": "By Pendidikan",
         "semester": "Semester 3", "tahun_ajaran": "2025/2026",
         "ipk_sem_sebelumnya": 3.6, "jumlah_pembayaran": 5000000}
    ])
    assert result["ok"] is True
    assert result["pa_number"].startswith("PA/ETF/001/")


def test_create_pa_no_lines_fails():
    result = create_pa(COMPANY_ID, {"tgl_payment_application": "2026-06-01"}, [])
    assert result["ok"] is False
    assert "Minimal" in result["pesan"]


def test_create_pa_invalid_student_fails():
    result = create_pa(COMPANY_ID, {"tgl_payment_application": "2026-06-01"}, [
        {"student_id": 9999, "jenis_pembayaran": "By Pendidikan",
         "semester": "Semester 1", "tahun_ajaran": "2024/2025",
         "ipk_sem_sebelumnya": 3.5, "jumlah_pembayaran": 1000000}
    ])
    assert result["ok"] is False


def test_create_pa_multi_lines():
    s1 = _student_id("1230001")
    s2 = _student_id("2230001")
    result = create_pa(COMPANY_ID, {"tgl_payment_application": "2026-06-01"}, [
        {"student_id": s1, "jenis_pembayaran": "By Pendidikan",
         "semester": "Semester 3", "tahun_ajaran": "2025/2026",
         "ipk_sem_sebelumnya": 3.6, "jumlah_pembayaran": 5000000},
        {"student_id": s2, "jenis_pembayaran": "By Tunjangan",
         "semester": "Semester 1", "tahun_ajaran": "2025/2026",
         "ipk_sem_sebelumnya": 3.8, "jumlah_pembayaran": 2000000},
    ])
    assert result["ok"] is True
    lines = get_pa_lines(result["pa_id"], COMPANY_ID)
    assert len(lines) == 2


def test_pa_number_increments():
    sid = _student_id("1230001")
    line = [{"student_id": sid, "jenis_pembayaran": "By Pendidikan",
             "semester": "Semester 1", "tahun_ajaran": "2024/2025",
             "ipk_sem_sebelumnya": 3.5, "jumlah_pembayaran": 1000000}]
    r1 = create_pa(COMPANY_ID, {"tgl_payment_application": "2026-06-01"}, line)
    r2 = create_pa(COMPANY_ID, {"tgl_payment_application": "2026-06-02"}, line)
    assert r1["pa_number"].endswith("/001/2026")
    assert r2["pa_number"].endswith("/002/2026")


# --- get_pa_list ---

def test_get_pa_list_aggregates():
    s1 = _student_id("1230001")
    s2 = _student_id("2230001")
    create_pa(COMPANY_ID, {"tgl_payment_application": "2026-06-01"}, [
        {"student_id": s1, "jenis_pembayaran": "By Pendidikan",
         "semester": "Semester 3", "tahun_ajaran": "2025/2026",
         "ipk_sem_sebelumnya": 3.6, "jumlah_pembayaran": 5000000},
        {"student_id": s2, "jenis_pembayaran": "By Tunjangan",
         "semester": "Semester 1", "tahun_ajaran": "2025/2026",
         "ipk_sem_sebelumnya": 3.8, "jumlah_pembayaran": 2000000},
    ])
    rows = get_pa_list(COMPANY_ID)
    assert len(rows) == 1
    assert rows[0]["jml_siswa"] == 2
    assert rows[0]["total_bayar"] == 7000000


# --- update_pa ---

def test_update_pa_status_on_process_generates_pam():
    sid = _student_id("1230001")
    r = create_pa(COMPANY_ID, {"tgl_payment_application": "2026-06-01"}, [
        {"student_id": sid, "jenis_pembayaran": "By Pendidikan",
         "semester": "Semester 3", "tahun_ajaran": "2025/2026",
         "ipk_sem_sebelumnya": 3.6, "jumlah_pembayaran": 5000000}
    ])
    upd = update_pa(r["pa_id"], COMPANY_ID, {
        "status": "on_process",
        "tgl_payment_application": "2026-06-01",
    })
    assert upd["ok"] is True
    assert upd["nomor_pam"] is not None
    assert "ETF" in upd["nomor_pam"]


def test_update_pa_status_complete():
    sid = _student_id("1230001")
    r = create_pa(COMPANY_ID, {"tgl_payment_application": "2026-06-01"}, [
        {"student_id": sid, "jenis_pembayaran": "By Pendidikan",
         "semester": "Semester 3", "tahun_ajaran": "2025/2026",
         "ipk_sem_sebelumnya": 3.6, "jumlah_pembayaran": 5000000}
    ])
    update_pa(r["pa_id"], COMPANY_ID, {"status": "on_process", "tgl_payment_application": "2026-06-01"})
    upd2 = update_pa(r["pa_id"], COMPANY_ID, {
        "status": "complete",
        "tanggal_bayar": "2026-06-15",
        "tgl_payment_application": "2026-06-01",
    })
    assert upd2["ok"] is True
    rows = get_pa_list(COMPANY_ID)
    assert rows[0]["status"] == "complete"


def test_update_pa_not_found():
    upd = update_pa(9999, COMPANY_ID, {"status": "on_process"})
    assert upd["ok"] is False


# --- get_siswa_autocomplete ---

def test_get_siswa_autocomplete():
    results = get_siswa_autocomplete(COMPANY_ID, "Budi")
    assert len(results) == 1
    assert results[0]["nama"] == "Budi Santoso"
    assert results[0]["ipk_terakhir"] == 3.6


def test_get_siswa_autocomplete_empty():
    results = get_siswa_autocomplete(COMPANY_ID, "ZZZ_tidak_ada")
    assert results == []
```

- [ ] **Step 2: Jalankan test — pastikan FAIL dulu (sebelum service ada)**

```bash
cd C:\Financehub\app
python -m pytest tests/test_etf_pa_service.py -v 2>&1 | head -30
```

Expected: semua test PASS karena service sudah dibuat di Task 2. Jika ada error, perbaiki di service.py.

- [ ] **Step 3: Jalankan semua test untuk cek regresi**

```bash
cd C:\Financehub\app
python -m pytest tests/ -v --tb=short 2>&1 | tail -20
```

Expected: semua test lama tetap PASS.

- [ ] **Step 4: Commit**

```bash
git add app/tests/test_etf_pa_service.py
git commit -m "test(etf-pa): add service tests (create, update, list, autocomplete)"
```

---

## Task 4: Routes Blueprint

**Files:**
- Create: `app/modules/etf_payment_application/routes.py`

- [ ] **Step 1: Tulis `routes.py`**

```python
# modules/etf_payment_application/routes.py
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session
from flask_jwt_extended import get_jwt
from auth.middleware import jwt_html_required
from modules.etf_payment_application.service import (
    get_pa_list, create_pa, update_pa, get_pa_lines, get_siswa_autocomplete,
)
import config

bp = Blueprint("etf_payment_application", __name__, url_prefix="/etf-payment-application")


def _ctx():
    try:
        claims = get_jwt()
        return {
            "current_user": claims.get("username", ""),
            "current_role": claims.get("role", ""),
            "company_id":   session.get("company_id"),
            "company_code": session.get("company_code"),
            "company_name": session.get("company_name"),
        }
    except Exception:
        return {}


@bp.route("/")
@jwt_html_required
def index():
    if not session.get("company_id"):
        return redirect(url_for("dashboard.select_company"))
    company_id = session["company_id"]
    pa_list = get_pa_list(company_id)
    return render_template(
        "etf_payment_application/index.html",
        pa_list=pa_list,
        cat1=config.CAT1_BGT,
        cat2_sem=config.CAT2_SEM,
        active_page="etf_payment_app",
        **_ctx(),
    )


@bp.route("/siswa-search")
@jwt_html_required
def siswa_search():
    q          = request.args.get("q", "")
    company_id = session.get("company_id")
    return jsonify(get_siswa_autocomplete(company_id, q))


@bp.route("/create", methods=["POST"])
@jwt_html_required
def create():
    company_id = session.get("company_id")
    data       = request.get_json(force=True)
    header = {
        "tgl_payment_application": data.get("tgl_payment_application", ""),
        "tgl_surat_pengajuan":     data.get("tgl_surat_pengajuan", ""),
        "keterangan":              data.get("keterangan", ""),
    }
    lines = data.get("lines", [])
    return jsonify(create_pa(company_id, header, lines))


@bp.route("/<int:pa_id>/update", methods=["POST"])
@jwt_html_required
def update(pa_id):
    company_id = session.get("company_id")
    data       = request.get_json(force=True)
    return jsonify(update_pa(pa_id, company_id, data))


@bp.route("/<int:pa_id>/lines")
@jwt_html_required
def lines(pa_id):
    company_id = session.get("company_id")
    return jsonify(get_pa_lines(pa_id, company_id))
```

- [ ] **Step 2: Commit**

```bash
git add app/modules/etf_payment_application/routes.py
git commit -m "feat(etf-pa): add routes blueprint (index, create, update, lines, siswa-search)"
```

---

## Task 5: Register Blueprint + Sidebar

**Files:**
- Modify: `app/app.py`
- Modify: `app/templates/base.html`

- [ ] **Step 1: Register blueprint di `app.py`**

Setelah baris `app.register_blueprint(payapp_bp)` (sekitar baris 37), tambahkan:

```python
    from modules.etf_payment_application.routes import bp as etf_pa_bp
    app.register_blueprint(etf_pa_bp)
```

- [ ] **Step 2: Tambahkan sidebar link di `base.html`**

Cari blok `{% if co == 'ETF' %}` (sekitar baris 44). Di dalam blok ETF, setelah link Beasiswa, tambahkan:

```html
    <a href="/etf-payment-application" {% if active_page == 'etf_payment_app' %}class="active"{% endif %}>
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>
      ETF Payment Application
    </a>
```

- [ ] **Step 3: Commit**

```bash
git add app/app.py app/templates/base.html
git commit -m "feat(etf-pa): register blueprint and add sidebar link for ETF"
```

---

## Task 6: Template

**Files:**
- Create: `app/templates/etf_payment_application/index.html`

- [ ] **Step 1: Buat direktori dan tulis template**

```html
{% extends "base.html" %}
{% block title %}ETF Payment Application{% endblock %}

{% block content %}
<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1.25rem">
  <h1 style="font-size:1.25rem; font-weight:700">ETF Payment Application — {{ company_name }}</h1>
  <button class="btn btn-primary" onclick="openModal('modal-buat-pa')">+ Buat PA Baru</button>
</div>

<div class="table-wrap">
  <table>
    <thead>
      <tr>
        <th style="min-width:140px">No. PA</th>
        <th class="num-right">Jml Siswa</th>
        <th class="num-right">Total Bayar</th>
        <th>Tgl PA</th>
        <th>Tgl Surat</th>
        <th>Doc Recv Educ</th>
        <th>Recv PA Educ</th>
        <th>Checked Fincon</th>
        <th>Approved HTj</th>
        <th>Send Back Educ</th>
        <th>PA Recv PO Fin</th>
        <th>Approval HTj</th>
        <th>Nomor PAM</th>
        <th>Tgl Bayar</th>
        <th>Keterangan</th>
        <th>Status</th>
        <th>Aksi</th>
      </tr>
    </thead>
    <tbody>
      {% for pa in pa_list %}
      <tr>
        <td><code>{{ pa.pa_number }}</code></td>
        <td class="num-right">{{ pa.jml_siswa }}</td>
        <td class="num-right">Rp {{ "{:,.0f}".format(pa.total_bayar) }}</td>
        <td>{{ pa.tgl_payment_application or '--' }}</td>
        <td>{{ pa.tgl_surat_pengajuan or '--' }}</td>
        <td>{{ pa.doc_received_by_educ or '--' }}</td>
        <td>{{ pa.received_pa_from_educ or '--' }}</td>
        <td>{{ pa.checked_by_fincon or '--' }}</td>
        <td>{{ pa.approved_by_htj_1 or '--' }}</td>
        <td>{{ pa.send_pa_back_to_educ or '--' }}</td>
        <td>{{ pa.pa_received_by_po_fin or '--' }}</td>
        <td>{{ pa.approval_by_htj_2 or '--' }}</td>
        <td>{{ pa.nomor_pam or '--' }}</td>
        <td>{{ pa.tanggal_bayar or '--' }}</td>
        <td style="max-width:180px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap" title="{{ pa.keterangan or '' }}">
          {{ pa.keterangan or '--' }}
        </td>
        <td>
          <span class="badge {% if pa.status == 'complete' %}badge-green{% elif pa.status == 'on_process' %}badge-yellow{% else %}badge-gray{% endif %}">
            {{ pa.status | replace('_', ' ') | title }}
          </span>
        </td>
        <td style="white-space:nowrap">
          <button class="btn btn-secondary btn-sm" onclick="loadLines({{ pa.id }}, '{{ pa.pa_number }}')">Detail</button>
          <button class="btn btn-primary btn-sm" onclick="openEdit({{ pa.id }}, {{ pa | tojson | e }})">Edit</button>
        </td>
      </tr>
      {% else %}
      <tr><td colspan="17" style="text-align:center; color:var(--text-muted); padding:2rem">
        Belum ada payment application ETF.
      </td></tr>
      {% endfor %}
    </tbody>
  </table>
</div>

{# Modal Buat PA Baru #}
<div class="modal-overlay" id="modal-buat-pa">
  <div class="modal" style="max-width:680px; width:95%">
    <div class="modal-header">
      <span class="modal-title">Buat ETF Payment Application Baru</span>
      <button class="modal-close" onclick="closeModal('modal-buat-pa')">x</button>
    </div>

    <div style="display:grid; grid-template-columns:1fr 1fr; gap:.75rem">
      <div class="form-group">
        <label>Tgl Payment Application</label>
        <input type="date" id="pa-tgl-app">
      </div>
      <div class="form-group">
        <label>Tgl Surat Pengajuan</label>
        <input type="date" id="pa-tgl-surat">
      </div>
    </div>
    <div class="form-group">
      <label>Keterangan</label>
      <input type="text" id="pa-keterangan" placeholder="Opsional">
    </div>

    <div style="display:flex; justify-content:space-between; align-items:center; margin:.75rem 0 .5rem">
      <strong style="font-size:.875rem">Daftar Siswa</strong>
      <button class="btn btn-secondary btn-sm" onclick="addLine()">+ Tambah Baris</button>
    </div>
    <div id="pa-lines-container"></div>

    <div style="display:flex; gap:.75rem; justify-content:flex-end; margin-top:1rem">
      <button class="btn btn-secondary" onclick="closeModal('modal-buat-pa')">Batal</button>
      <button class="btn btn-primary" onclick="submitPA()">Simpan PA</button>
    </div>
  </div>
</div>

{# Modal Edit PA #}
<div class="modal-overlay" id="modal-edit-pa">
  <div class="modal" style="max-width:640px; width:95%">
    <div class="modal-header">
      <span class="modal-title" id="edit-pa-title">Edit PA</span>
      <button class="modal-close" onclick="closeModal('modal-edit-pa')">x</button>
    </div>
    <input type="hidden" id="edit-pa-id">

    <div style="display:grid; grid-template-columns:1fr 1fr; gap:.75rem">
      <div class="form-group"><label>Tgl PA</label><input type="date" id="edit-tgl-app"></div>
      <div class="form-group"><label>Tgl Surat Pengajuan</label><input type="date" id="edit-tgl-surat"></div>
      <div class="form-group"><label>Doc Recv by Educ</label><input type="date" id="edit-doc-recv"></div>
      <div class="form-group"><label>Recv PA from Educ</label><input type="date" id="edit-recv-pa"></div>
      <div class="form-group"><label>Checked by Fincon</label><input type="date" id="edit-checked"></div>
      <div class="form-group"><label>Approved by HTj (1)</label><input type="date" id="edit-approved1"></div>
      <div class="form-group"><label>Send PA Back to Educ</label><input type="date" id="edit-send-back"></div>
      <div class="form-group"><label>PA Recv by PO Fin</label><input type="date" id="edit-recv-po"></div>
      <div class="form-group"><label>Approval by HTj (final)</label><input type="date" id="edit-approval2"></div>
      <div class="form-group"><label>Tanggal Bayar</label><input type="date" id="edit-tgl-bayar"></div>
    </div>
    <div style="display:grid; grid-template-columns:1fr 1fr; gap:.75rem">
      <div class="form-group">
        <label>Nomor PAM</label>
        <input type="text" id="edit-nomor-pam" placeholder="Auto-generate saat On Process">
      </div>
      <div class="form-group">
        <label>Status</label>
        <select id="edit-status">
          <option value="draft">Draft</option>
          <option value="on_process">On Process</option>
          <option value="complete">Complete</option>
        </select>
      </div>
    </div>
    <div class="form-group">
      <label>Keterangan</label>
      <input type="text" id="edit-keterangan">
    </div>

    <div style="display:flex; gap:.75rem; justify-content:flex-end; margin-top:1rem">
      <button class="btn btn-secondary" onclick="closeModal('modal-edit-pa')">Batal</button>
      <button class="btn btn-primary" onclick="saveEdit()">Simpan</button>
    </div>
  </div>
</div>

{# Modal Detail Lines #}
<div class="modal-overlay" id="modal-detail-pa">
  <div class="modal" style="max-width:760px; width:95%">
    <div class="modal-header">
      <span class="modal-title" id="detail-pa-title">Detail Siswa</span>
      <button class="modal-close" onclick="closeModal('modal-detail-pa')">x</button>
    </div>
    <div class="table-wrap" id="detail-lines-table" style="max-height:400px; overflow-y:auto"></div>
  </div>
</div>

{# Template row untuk lines input #}
<template id="line-template">
  <div class="pa-line-row" style="border:1px solid var(--border); border-radius:6px; padding:.75rem; margin-bottom:.5rem; position:relative">
    <button type="button" onclick="removeLine(this)" style="position:absolute; top:.5rem; right:.5rem; background:none; border:none; cursor:pointer; color:var(--text-muted); font-size:1rem">✕</button>
    <div style="display:grid; grid-template-columns:2fr 1fr 1fr; gap:.5rem; margin-bottom:.5rem">
      <div class="form-group" style="margin:0">
        <label>Nama Siswa</label>
        <input type="text" class="siswa-search-input" placeholder="Cari nama..." autocomplete="off">
        <input type="hidden" class="siswa-id-input">
        <div class="siswa-suggestions" style="display:none; position:absolute; background:#fff; border:1px solid var(--border); border-radius:4px; z-index:100; max-height:200px; overflow-y:auto; width:280px"></div>
      </div>
      <div class="form-group" style="margin:0">
        <label>Jenis Bayar</label>
        <select class="jenis-bayar-input">
          <option value="">-- Pilih --</option>
          {% for c in cat1 %}<option value="{{ c }}">{{ c }}</option>{% endfor %}
        </select>
      </div>
      <div class="form-group" style="margin:0">
        <label>Semester</label>
        <select class="semester-input">
          <option value="">-- Pilih --</option>
          {% for c in cat2_sem %}<option value="{{ c }}">{{ c }}</option>{% endfor %}
        </select>
      </div>
    </div>
    <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:.5rem">
      <div class="form-group" style="margin:0">
        <label>Tahun Ajaran</label>
        <input type="text" class="tahun-ajaran-input" placeholder="2024/2025">
      </div>
      <div class="form-group" style="margin:0">
        <label>IPK Sem Sblmnya</label>
        <input type="number" class="ipk-input" step="0.01" min="0" max="4" readonly style="background:var(--bg-muted)">
      </div>
      <div class="form-group" style="margin:0">
        <label>Jumlah (Rp)</label>
        <input type="number" class="jumlah-input" placeholder="0" min="0">
      </div>
    </div>
    <div class="siswa-info" style="font-size:.75rem; color:var(--text-muted); margin-top:.4rem"></div>
  </div>
</template>
{% endblock %}

{% block scripts %}
<script>
// ─── Autocomplete Siswa ──────────────────────────────────────────────────────
function setupAutocomplete(row) {
  const searchInput = row.querySelector(".siswa-search-input");
  const idInput     = row.querySelector(".siswa-id-input");
  const suggestions = row.querySelector(".siswa-suggestions");
  const ipkInput    = row.querySelector(".ipk-input");
  const infoDiv     = row.querySelector(".siswa-info");

  let debounce;
  searchInput.addEventListener("input", () => {
    clearTimeout(debounce);
    const q = searchInput.value.trim();
    if (q.length < 2) { suggestions.style.display = "none"; return; }
    debounce = setTimeout(async () => {
      const resp = await apiFetch(`/etf-payment-application/siswa-search?q=${encodeURIComponent(q)}`);
      const data = await resp.json();
      suggestions.innerHTML = "";
      if (!data.length) { suggestions.style.display = "none"; return; }
      data.forEach(s => {
        const item = document.createElement("div");
        item.style.cssText = "padding:.4rem .6rem; cursor:pointer; font-size:.8rem; border-bottom:1px solid var(--border)";
        item.textContent = `${s.nama} (${s.code}) — ${s.jenjang} ${s.angkatan}`;
        item.onmousedown = () => {
          searchInput.value      = s.nama;
          idInput.value          = s.id;
          ipkInput.value         = s.ipk_terakhir || 0;
          infoDiv.textContent    = `${s.universitas || ''} | ${s.program || ''} | ${s.fakultas || ''} | Status: ${s.status}`;
          suggestions.style.display = "none";
        };
        suggestions.appendChild(item);
      });
      suggestions.style.display = "block";
    }, 300);
  });
  searchInput.addEventListener("blur", () => setTimeout(() => { suggestions.style.display = "none"; }, 200));
}

// ─── Lines Management ─────────────────────────────────────────────────────────
function addLine() {
  const tpl = document.getElementById("line-template").content.cloneNode(true);
  const row = tpl.querySelector(".pa-line-row");
  document.getElementById("pa-lines-container").appendChild(tpl);
  setupAutocomplete(document.getElementById("pa-lines-container").lastElementChild);
}

function removeLine(btn) {
  btn.closest(".pa-line-row").remove();
}

// ─── Submit PA ────────────────────────────────────────────────────────────────
async function submitPA() {
  const tglApp   = document.getElementById("pa-tgl-app").value;
  if (!tglApp) { showToast("Tgl Payment Application wajib diisi.", "error"); return; }

  const rows = document.querySelectorAll("#pa-lines-container .pa-line-row");
  if (!rows.length) { showToast("Minimal 1 siswa harus ditambahkan.", "error"); return; }

  const lines = [];
  for (const row of rows) {
    const sid = row.querySelector(".siswa-id-input").value;
    if (!sid)  { showToast("Pilih siswa untuk semua baris.", "error"); return; }
    lines.push({
      student_id:          parseInt(sid),
      jenis_pembayaran:    row.querySelector(".jenis-bayar-input").value,
      semester:            row.querySelector(".semester-input").value,
      tahun_ajaran:        row.querySelector(".tahun-ajaran-input").value,
      ipk_sem_sebelumnya:  parseFloat(row.querySelector(".ipk-input").value) || 0,
      jumlah_pembayaran:   parseInt(row.querySelector(".jumlah-input").value) || 0,
    });
  }

  const resp = await apiFetch("/etf-payment-application/create", {
    method: "POST",
    body: JSON.stringify({
      tgl_payment_application: tglApp,
      tgl_surat_pengajuan:     document.getElementById("pa-tgl-surat").value,
      keterangan:              document.getElementById("pa-keterangan").value,
      lines,
    })
  });
  const data = await resp.json();
  showToast(data.pesan, data.ok ? "success" : "error");
  if (data.ok) { closeModal("modal-buat-pa"); setTimeout(() => location.reload(), 800); }
}

// ─── Edit PA ─────────────────────────────────────────────────────────────────
function openEdit(paId, pa) {
  document.getElementById("edit-pa-id").value       = paId;
  document.getElementById("edit-pa-title").textContent = `Edit PA: ${pa.pa_number}`;
  document.getElementById("edit-tgl-app").value     = pa.tgl_payment_application || "";
  document.getElementById("edit-tgl-surat").value   = pa.tgl_surat_pengajuan || "";
  document.getElementById("edit-doc-recv").value    = pa.doc_received_by_educ || "";
  document.getElementById("edit-recv-pa").value     = pa.received_pa_from_educ || "";
  document.getElementById("edit-checked").value     = pa.checked_by_fincon || "";
  document.getElementById("edit-approved1").value   = pa.approved_by_htj_1 || "";
  document.getElementById("edit-send-back").value   = pa.send_pa_back_to_educ || "";
  document.getElementById("edit-recv-po").value     = pa.pa_received_by_po_fin || "";
  document.getElementById("edit-approval2").value   = pa.approval_by_htj_2 || "";
  document.getElementById("edit-nomor-pam").value   = pa.nomor_pam || "";
  document.getElementById("edit-tgl-bayar").value   = pa.tanggal_bayar || "";
  document.getElementById("edit-keterangan").value  = pa.keterangan || "";
  document.getElementById("edit-status").value      = pa.status || "draft";
  openModal("modal-edit-pa");
}

async function saveEdit() {
  const paId = document.getElementById("edit-pa-id").value;
  const payload = {
    tgl_payment_application: document.getElementById("edit-tgl-app").value,
    tgl_surat_pengajuan:     document.getElementById("edit-tgl-surat").value,
    doc_received_by_educ:    document.getElementById("edit-doc-recv").value,
    received_pa_from_educ:   document.getElementById("edit-recv-pa").value,
    checked_by_fincon:       document.getElementById("edit-checked").value,
    approved_by_htj_1:       document.getElementById("edit-approved1").value,
    send_pa_back_to_educ:    document.getElementById("edit-send-back").value,
    pa_received_by_po_fin:   document.getElementById("edit-recv-po").value,
    approval_by_htj_2:       document.getElementById("edit-approval2").value,
    nomor_pam:               document.getElementById("edit-nomor-pam").value,
    tanggal_bayar:           document.getElementById("edit-tgl-bayar").value,
    keterangan:              document.getElementById("edit-keterangan").value,
    status:                  document.getElementById("edit-status").value,
  };
  const resp = await apiFetch(`/etf-payment-application/${paId}/update`, {
    method: "POST", body: JSON.stringify(payload)
  });
  const data = await resp.json();
  showToast(data.pesan, data.ok ? "success" : "error");
  if (data.ok) { closeModal("modal-edit-pa"); setTimeout(() => location.reload(), 800); }
}

// ─── Detail Lines ─────────────────────────────────────────────────────────────
async function loadLines(paId, paNumber) {
  document.getElementById("detail-pa-title").textContent = `Detail Siswa — ${paNumber}`;
  document.getElementById("detail-lines-table").innerHTML = "<p style='padding:1rem'>Memuat...</p>";
  openModal("modal-detail-pa");

  const resp = await apiFetch(`/etf-payment-application/${paId}/lines`);
  const lines = await resp.json();
  if (!lines.length) {
    document.getElementById("detail-lines-table").innerHTML = "<p style='padding:1rem; color:var(--text-muted)'>Tidak ada data siswa.</p>";
    return;
  }
  const cols = ["nama","status_pb","instansi_pendidikan","angkatan_etf","jenjang_pendidikan","program_beasiswa","fakultas","jenis_pembayaran","semester","tahun_ajaran","ipk_sem_sebelumnya","jumlah_pembayaran"];
  const heads = ["Nama","Status","Instansi","Angkatan","Jenjang","Program","Fakultas","Jenis Bayar","Semester","Thn Ajaran","IPK","Jumlah (Rp)"];
  let html = "<table><thead><tr>" + heads.map(h=>`<th>${h}</th>`).join("") + "</tr></thead><tbody>";
  lines.forEach(l => {
    html += "<tr>" + cols.map(c => {
      const v = l[c] ?? "--";
      if (c === "jumlah_pembayaran") return `<td class="num-right">Rp ${Number(v).toLocaleString("id-ID")}</td>`;
      return `<td>${v}</td>`;
    }).join("") + "</tr>";
  });
  html += "</tbody></table>";
  document.getElementById("detail-lines-table").innerHTML = html;
}

// Init: buka dengan 1 baris default
window.addEventListener("DOMContentLoaded", () => {
  document.getElementById("modal-buat-pa").addEventListener("shown", addLine);
});

// Pastikan ada 1 baris saat modal dibuka
const origOpen = window.openModal;
window.openModal = function(id) {
  if (id === "modal-buat-pa") {
    document.getElementById("pa-lines-container").innerHTML = "";
    document.getElementById("pa-tgl-app").value    = "";
    document.getElementById("pa-tgl-surat").value  = "";
    document.getElementById("pa-keterangan").value = "";
    addLine();
  }
  origOpen(id);
};
</script>
{% endblock %}
```

- [ ] **Step 2: Commit**

```bash
git add app/templates/etf_payment_application/index.html
git commit -m "feat(etf-pa): add index template with create/edit/detail modals"
```

---

## Task 7: Verifikasi End-to-End

- [ ] **Step 1: Jalankan semua test**

```bash
cd C:\Financehub\app
python -m pytest tests/ -v --tb=short
```

Expected: semua PASS, tidak ada regresi.

- [ ] **Step 2: Jalankan server dan cek halaman**

```bash
cd C:\Financehub\app
python -m flask --app app run --port 8080
```

Buka browser → login → pilih company ETF → cek sidebar ada "ETF Payment Application" → klik → halaman muncul tanpa error.

- [ ] **Step 3: Test create PA**

- Klik "+ Buat PA Baru"
- Isi Tgl PA, tambah 1 baris siswa via autocomplete
- Simpan → PA muncul di tabel dengan status Draft

- [ ] **Step 4: Test edit + status change**

- Klik Edit pada PA yang baru dibuat
- Ubah Status ke "On Process" → Simpan
- Nomor PAM otomatis muncul di kolom Nomor PAM

- [ ] **Step 5: Final commit**

```bash
git add .
git commit -m "feat(etf-pa): complete ETF Payment Application module v1"
```
