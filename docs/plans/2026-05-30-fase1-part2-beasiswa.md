# Finance Hub Fase 1 — Part 2: Beasiswa Module

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementasi Beasiswa module lengkap — Siswa CRUD (dengan auto-generate kode), Budget input batch, Payment input batch (auto-draft ke PAM), dan Rekap dengan export CSV + PDF.

**Architecture:** Blueprint `beasiswa` dengan 3 layer: `service.py` (query SQLite), `routes.py` (HTML pages), `api.py` (REST JSON). Template `templates/beasiswa/index.html` dengan 4 tab: Siswa / Budget / Payment / Rekap.

**Tech Stack:** Flask Blueprint, SQLite (parameterized queries), reportlab (PDF), Python csv module

**Prerequisite:** Part 1 sudah selesai — app.py, database.py, auth/middleware.py sudah ada di `C:\Financehub\app\`

---

## File Structure (Part 2 additions)

```
C:\Financehub\app\
├── modules/
│   └── beasiswa/
│       ├── __init__.py
│       ├── routes.py           ← HTML: /beasiswa, tabs Siswa/Budget/Payment/Rekap
│       ├── api.py              ← REST JSON: /api/v1/beasiswa/*
│       └── service.py          ← Query SQLite: get_siswa, add_siswa, get_budget, dll
├── templates/
│   └── beasiswa/
│       └── index.html          ← 4 tab: Siswa / Budget / Payment / Rekap
└── tests/
    ├── test_beasiswa_service.py
    └── test_beasiswa_routes.py
```

---

## Task 1: beasiswa/service.py

**Files:**
- Create: `C:\Financehub\app\modules\beasiswa\__init__.py` (kosong)
- Create: `C:\Financehub\app\modules\beasiswa\service.py`
- Test: `C:\Financehub\app\tests\test_beasiswa_service.py`

- [ ] **Step 1: Tulis tests/test_beasiswa_service.py dulu**

```python
# C:\Financehub\app\tests\test_beasiswa_service.py
import os, sys, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config
config.DB_PATH = os.path.join(os.path.dirname(__file__), "test_finance_hub.db")

from database import init_db, get_conn
from modules.beasiswa.service import (
    generate_kode_siswa, get_siswa_list, add_siswa, update_siswa,
    add_budget_batch, add_payment_batch, get_rekap,
    get_sisa_budget
)

COMPANY_ID = 2  # ETF

@pytest.fixture(autouse=True)
def clean_db():
    if os.path.exists(config.DB_PATH):
        os.remove(config.DB_PATH)
    init_db()
    yield
    if os.path.exists(config.DB_PATH):
        os.remove(config.DB_PATH)

# ── generate_kode_siswa ──────────────────────────────────────────────
def test_generate_kode_s1_2025_first():
    kode = generate_kode_siswa("S1", 2025, COMPANY_ID)
    assert kode == "1250001"

def test_generate_kode_s2_2024():
    kode = generate_kode_siswa("S2", 2024, COMPANY_ID)
    assert kode == "2240001"

def test_generate_kode_increments():
    add_siswa(COMPANY_ID, {"code": "1250001", "nama": "Andi", "jenjang": "S1",
        "angkatan": 2025, "program": "SMART", "fakultas": "", "universitas": "",
        "bank": "", "norek": "", "namarek": "", "referensi": "",
        "status": "Aktif", "catatan": ""})
    kode = generate_kode_siswa("S1", 2025, COMPANY_ID)
    assert kode == "1250002"

# ── add_siswa / get_siswa_list ────────────────────────────────────────
def test_add_siswa_success():
    result = add_siswa(COMPANY_ID, {
        "code": "1250001", "nama": "Budi Santoso", "jenjang": "S1",
        "angkatan": 2025, "program": "SMART", "fakultas": "Teknik",
        "universitas": "UI", "bank": "BCA", "norek": "1234567890",
        "namarek": "Budi Santoso", "referensi": "AGRI",
        "status": "Aktif", "catatan": "Test"
    })
    assert result["ok"] is True

def test_add_siswa_duplicate_code():
    data = {"code": "1250001", "nama": "X", "jenjang": "S1", "angkatan": 2025,
            "program": "SMART", "fakultas": "", "universitas": "", "bank": "",
            "norek": "", "namarek": "", "referensi": "", "status": "Aktif", "catatan": ""}
    add_siswa(COMPANY_ID, data)
    result = add_siswa(COMPANY_ID, data)
    assert result["ok"] is False
    assert "sudah ada" in result["pesan"]

def test_get_siswa_list_returns_all():
    add_siswa(COMPANY_ID, {"code": "1250001", "nama": "A", "jenjang": "S1",
        "angkatan": 2025, "program": "SMART", "fakultas": "", "universitas": "",
        "bank": "", "norek": "", "namarek": "", "referensi": "",
        "status": "Aktif", "catatan": ""})
    rows = get_siswa_list(COMPANY_ID)
    assert len(rows) == 1
    assert rows[0]["nama"] == "A"

def test_get_siswa_list_isolated_by_company():
    add_siswa(COMPANY_ID, {"code": "1250001", "nama": "ETF Siswa", "jenjang": "S1",
        "angkatan": 2025, "program": "SMART", "fakultas": "", "universitas": "",
        "bank": "", "norek": "", "namarek": "", "referensi": "",
        "status": "Aktif", "catatan": ""})
    # SMT company_id = 1
    rows = get_siswa_list(1)
    assert len(rows) == 0

# ── budget ────────────────────────────────────────────────────────────
def test_add_budget_batch():
    add_siswa(COMPANY_ID, {"code": "1250001", "nama": "A", "jenjang": "S1",
        "angkatan": 2025, "program": "SMART", "fakultas": "", "universitas": "",
        "bank": "", "norek": "", "namarek": "", "referensi": "",
        "status": "Aktif", "catatan": ""})
    result = add_budget_batch(COMPANY_ID, "1250001", "2025-01-15", "AGRI", [
        {"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 5000000},
        {"cat1": "By Tunjangan",  "cat2": "Semester 1", "amount": 2000000},
    ])
    assert result["ok"] is True
    assert result["saved"] == 2

def test_add_budget_batch_skips_zero_amount():
    add_siswa(COMPANY_ID, {"code": "1250001", "nama": "A", "jenjang": "S1",
        "angkatan": 2025, "program": "SMART", "fakultas": "", "universitas": "",
        "bank": "", "norek": "", "namarek": "", "referensi": "",
        "status": "Aktif", "catatan": ""})
    result = add_budget_batch(COMPANY_ID, "1250001", "2025-01-15", "AGRI", [
        {"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 0},
    ])
    assert result["saved"] == 0

# ── payment ───────────────────────────────────────────────────────────
def test_add_payment_batch_creates_draft():
    add_siswa(COMPANY_ID, {"code": "1250001", "nama": "A", "jenjang": "S1",
        "angkatan": 2025, "program": "SMART", "fakultas": "", "universitas": "",
        "bank": "", "norek": "", "namarek": "", "referensi": "",
        "status": "Aktif", "catatan": ""})
    result = add_payment_batch(COMPANY_ID, "1250001", "2025-06-01", "AGRI",
        "PT. SMART Tbk", [
            {"cat1": "By Pendidikan", "cat2": "Semester 2", "cat3": "", "cat4": "", "amount": 5000000},
        ])
    assert result["ok"] is True
    conn = get_conn()
    row = conn.execute(
        "SELECT status FROM payment_beasiswa WHERE company_id = ? AND siswa_code = ?",
        (COMPANY_ID, "1250001")
    ).fetchone()
    conn.close()
    assert row["status"] == "draft"

# ── rekap / sisa budget ───────────────────────────────────────────────
def test_get_rekap_empty():
    rows = get_rekap(COMPANY_ID)
    assert rows == []

def test_get_sisa_budget():
    add_siswa(COMPANY_ID, {"code": "1250001", "nama": "A", "jenjang": "S1",
        "angkatan": 2025, "program": "SMART", "fakultas": "", "universitas": "",
        "bank": "", "norek": "", "namarek": "", "referensi": "",
        "status": "Aktif", "catatan": ""})
    add_budget_batch(COMPANY_ID, "1250001", "2025-01-15", "AGRI", [
        {"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 10000000},
    ])
    add_payment_batch(COMPANY_ID, "1250001", "2025-06-01", "AGRI", "PT. SMART Tbk", [
        {"cat1": "By Pendidikan", "cat2": "Semester 1", "cat3": "", "cat4": "", "amount": 4000000},
    ])
    sisa = get_sisa_budget(COMPANY_ID, "1250001")
    assert sisa["total_budget"]  == 10000000
    assert sisa["total_payment"] == 4000000
    assert sisa["total_sisa"]    == 6000000
```

- [ ] **Step 2: Jalankan test — pastikan FAIL**

```bash
cd C:\Financehub\app
pytest tests/test_beasiswa_service.py -v
```

Expected: `ERROR — ModuleNotFoundError: No module named 'modules.beasiswa.service'`

- [ ] **Step 3: Buat __init__.py kosong**

```bash
type nul > modules\beasiswa\__init__.py
```

- [ ] **Step 4: Tulis modules/beasiswa/service.py**

```python
# C:\Financehub\app\modules\beasiswa\service.py
from datetime import datetime
from database import get_conn
import config


def _ts():
    return datetime.now().isoformat(timespec="seconds")


# ── KODE SISWA ────────────────────────────────────────────────────────

def generate_kode_siswa(jenjang: str, angkatan: int, company_id: int) -> str:
    """
    Port dari VBA GenerateKodeSiswa.
    Format: [kodeJenjang][2digitTahun][4digitUrutan]
    Contoh: S1, angkatan 2025 → prefix '125' → '1250001'
    """
    kode_j  = config.KODE_JENJANG.get(jenjang.strip(), "0")
    tahun2  = str(angkatan)[-2:]
    prefix  = kode_j + tahun2  # 3 karakter, contoh: "125"

    conn    = get_conn()
    rows    = conn.execute(
        "SELECT code FROM siswa WHERE company_id = ? AND code LIKE ?",
        (company_id, prefix + "%")
    ).fetchall()
    conn.close()

    max_urut = 0
    for row in rows:
        kode = str(row["code"])
        if len(kode) >= 7:
            try:
                urut = int(kode[3:7])
                if urut > max_urut:
                    max_urut = urut
            except ValueError:
                pass

    return prefix + str(max_urut + 1).zfill(4)


# ── SISWA ─────────────────────────────────────────────────────────────

def get_siswa_list(company_id: int, search: str = "", status: str = "", program: str = "") -> list:
    """Return list semua siswa untuk company, opsional filter."""
    sql    = "SELECT * FROM siswa WHERE company_id = ?"
    params = [company_id]
    if search:
        sql    += " AND (nama LIKE ? OR code LIKE ?)"
        params += [f"%{search}%", f"%{search}%"]
    if status:
        sql    += " AND status = ?"
        params += [status]
    if program:
        sql    += " AND program = ?"
        params += [program]
    sql += " ORDER BY created_at DESC"

    conn = get_conn()
    rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
    conn.close()
    return rows


def get_siswa_detail(company_id: int, code: str) -> dict | None:
    conn = get_conn()
    row  = conn.execute(
        "SELECT * FROM siswa WHERE company_id = ? AND code = ?",
        (company_id, code)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def add_siswa(company_id: int, data: dict) -> dict:
    """Tambah siswa baru. Return {"ok": bool, "pesan": str}."""
    code = (data.get("code") or "").strip()
    nama = (data.get("nama") or "").strip()
    if not code or not nama:
        return {"ok": False, "pesan": "Code dan nama wajib diisi."}

    conn = get_conn()
    existing = conn.execute(
        "SELECT id FROM siswa WHERE company_id = ? AND code = ?",
        (company_id, code)
    ).fetchone()
    if existing:
        conn.close()
        return {"ok": False, "pesan": f"Code '{code}' sudah ada di database."}

    ipk_sem  = [float(data.get(f"ipk_sem{i}", 0) or 0) for i in range(1, 11)]
    ipk_pen  = [float(data.get(f"ipk_pen{i}", 0) or 0) for i in range(1, 4)]

    conn.execute(
        """INSERT INTO siswa
           (company_id, code, nama, jenjang, angkatan, program, fakultas, universitas,
            bank, norek, namarek, referensi,
            ipk_sem1, ipk_sem2, ipk_sem3, ipk_sem4, ipk_sem5,
            ipk_sem6, ipk_sem7, ipk_sem8, ipk_sem9, ipk_sem10,
            ipk_pen1, ipk_pen2, ipk_pen3,
            status, catatan, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (company_id, code, nama,
         data.get("jenjang", ""), data.get("angkatan") or None,
         data.get("program", ""), data.get("fakultas", ""), data.get("universitas", ""),
         data.get("bank", ""), data.get("norek", ""), data.get("namarek", ""),
         data.get("referensi", ""),
         *ipk_sem, *ipk_pen,
         data.get("status", "Aktif"), data.get("catatan", ""),
         _ts())
    )
    conn.commit()
    conn.close()
    return {"ok": True, "pesan": f"Siswa '{nama}' berhasil ditambahkan."}


def update_siswa(company_id: int, code: str, data: dict) -> dict:
    """Update data siswa. Return {"ok": bool, "pesan": str}."""
    conn     = get_conn()
    existing = conn.execute(
        "SELECT id FROM siswa WHERE company_id = ? AND code = ?",
        (company_id, code)
    ).fetchone()
    if not existing:
        conn.close()
        return {"ok": False, "pesan": f"Siswa '{code}' tidak ditemukan."}

    ipk_sem = [float(data.get(f"ipk_sem{i}", 0) or 0) for i in range(1, 11)]
    ipk_pen = [float(data.get(f"ipk_pen{i}", 0) or 0) for i in range(1, 4)]

    conn.execute(
        """UPDATE siswa SET
           nama=?, jenjang=?, angkatan=?, program=?, fakultas=?, universitas=?,
           bank=?, norek=?, namarek=?, referensi=?,
           ipk_sem1=?, ipk_sem2=?, ipk_sem3=?, ipk_sem4=?, ipk_sem5=?,
           ipk_sem6=?, ipk_sem7=?, ipk_sem8=?, ipk_sem9=?, ipk_sem10=?,
           ipk_pen1=?, ipk_pen2=?, ipk_pen3=?,
           status=?, catatan=?, updated_at=?
           WHERE company_id=? AND code=?""",
        (data.get("nama", ""), data.get("jenjang", ""), data.get("angkatan") or None,
         data.get("program", ""), data.get("fakultas", ""), data.get("universitas", ""),
         data.get("bank", ""), data.get("norek", ""), data.get("namarek", ""),
         data.get("referensi", ""),
         *ipk_sem, *ipk_pen,
         data.get("status", "Aktif"), data.get("catatan", ""),
         _ts(), company_id, code)
    )
    conn.commit()
    conn.close()
    return {"ok": True, "pesan": f"Data siswa '{code}' berhasil diupdate."}


# ── BUDGET ────────────────────────────────────────────────────────────

def add_budget_batch(company_id: int, siswa_code: str, tanggal: str,
                     pillar: str, items: list) -> dict:
    """
    Simpan batch budget rows.
    items: [{"cat1": str, "cat2": str, "amount": float}]
    """
    conn  = get_conn()
    saved = 0
    for item in items:
        try:
            amount = float(str(item.get("amount", 0)).replace(",", ""))
        except (ValueError, TypeError):
            amount = 0
        if amount <= 0:
            continue
        conn.execute(
            "INSERT INTO budget_beasiswa (company_id, siswa_code, cat1, cat2, tanggal, amount, pillar) "
            "VALUES (?,?,?,?,?,?,?)",
            (company_id, siswa_code,
             item.get("cat1", ""), item.get("cat2", ""),
             tanggal, amount, pillar)
        )
        saved += 1

    if saved == 0:
        conn.close()
        return {"ok": False, "pesan": "Tidak ada item dengan amount > 0."}

    conn.commit()
    conn.close()
    return {"ok": True, "pesan": f"{saved} baris budget berhasil disimpan.", "saved": saved}


def get_budget(company_id: int, siswa_code: str) -> dict:
    """Return budget rows + totals per cat1 + grand total."""
    conn = get_conn()
    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM budget_beasiswa WHERE company_id=? AND siswa_code=? ORDER BY tanggal",
        (company_id, siswa_code)
    ).fetchall()]
    conn.close()

    totals = {}
    grand  = 0.0
    for r in rows:
        totals[r["cat1"]] = totals.get(r["cat1"], 0) + r["amount"]
        grand += r["amount"]

    return {"rows": rows, "totals": totals, "grand": grand}


# ── PAYMENT ───────────────────────────────────────────────────────────

def add_payment_batch(company_id: int, siswa_code: str, tanggal: str,
                      pillar: str, perusahaan: str, items: list) -> dict:
    """
    Simpan batch payment rows dengan status='draft'.
    items: [{"cat1","cat2","cat3","cat4","amount"}]
    """
    conn  = get_conn()
    saved = 0
    for item in items:
        try:
            amount = float(str(item.get("amount", 0)).replace(",", ""))
        except (ValueError, TypeError):
            amount = 0
        if amount <= 0:
            continue
        conn.execute(
            """INSERT INTO payment_beasiswa
               (company_id, siswa_code, cat1, cat2, tanggal, amount,
                pillar, perusahaan, cat3, cat4, status)
               VALUES (?,?,?,?,?,?,?,?,?,?,'draft')""",
            (company_id, siswa_code,
             item.get("cat1", ""), item.get("cat2", ""),
             tanggal, amount, pillar, perusahaan,
             item.get("cat3", ""), item.get("cat4", ""))
        )
        saved += 1

    if saved == 0:
        conn.close()
        return {"ok": False, "pesan": "Tidak ada item dengan amount > 0."}

    conn.commit()
    conn.close()
    return {"ok": True, "pesan": f"{saved} payment berhasil disimpan (status: draft).", "saved": saved}


def get_payment(company_id: int, siswa_code: str = "", status: str = "") -> list:
    sql    = "SELECT pb.*, s.nama FROM payment_beasiswa pb LEFT JOIN siswa s ON s.company_id=pb.company_id AND s.code=pb.siswa_code WHERE pb.company_id=?"
    params = [company_id]
    if siswa_code:
        sql    += " AND pb.siswa_code=?"
        params += [siswa_code]
    if status:
        sql    += " AND pb.status=?"
        params += [status]
    sql += " ORDER BY pb.tanggal DESC"
    conn = get_conn()
    rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
    conn.close()
    return rows


# ── SISA BUDGET ───────────────────────────────────────────────────────

def get_sisa_budget(company_id: int, siswa_code: str) -> dict:
    """SUMIF budget vs payment per cat1 untuk satu siswa."""
    conn = get_conn()

    bgt = {}
    for r in conn.execute(
        "SELECT cat1, SUM(amount) as total FROM budget_beasiswa "
        "WHERE company_id=? AND siswa_code=? GROUP BY cat1",
        (company_id, siswa_code)
    ).fetchall():
        bgt[r["cat1"]] = r["total"]

    pay = {}
    for r in conn.execute(
        "SELECT cat1, SUM(amount) as total FROM payment_beasiswa "
        "WHERE company_id=? AND siswa_code=? GROUP BY cat1",
        (company_id, siswa_code)
    ).fetchall():
        pay[r["cat1"]] = r["total"]

    conn.close()

    all_cats     = set(list(bgt.keys()) + list(pay.keys()))
    sisa         = {c: bgt.get(c, 0) - pay.get(c, 0) for c in all_cats}
    total_budget  = sum(bgt.values())
    total_payment = sum(pay.values())

    return {
        "budget":        bgt,
        "payment":       pay,
        "sisa":          sisa,
        "total_budget":  total_budget,
        "total_payment": total_payment,
        "total_sisa":    total_budget - total_payment,
    }


# ── REKAP ─────────────────────────────────────────────────────────────

def get_rekap(company_id: int, program: str = "", pillar: str = "",
              status: str = "") -> list:
    """
    Return list rekap per siswa: {code, nama, program, status, total_budget, total_payment, sisa}.
    """
    sql    = "SELECT * FROM siswa WHERE company_id=?"
    params = [company_id]
    if program:
        sql    += " AND program=?"
        params += [program]
    if status:
        sql    += " AND status=?"
        params += [status]
    sql += " ORDER BY nama"

    conn  = get_conn()
    siswa = conn.execute(sql, params).fetchall()

    # Bulk SUMIF budget
    bgt_map = {}
    for r in conn.execute(
        "SELECT siswa_code, SUM(amount) as t FROM budget_beasiswa WHERE company_id=? GROUP BY siswa_code",
        (company_id,)
    ).fetchall():
        bgt_map[r["siswa_code"]] = r["t"]

    # Bulk SUMIF payment, optional filter pillar
    pay_sql    = "SELECT siswa_code, SUM(amount) as t FROM payment_beasiswa WHERE company_id=?"
    pay_params = [company_id]
    if pillar:
        pay_sql    += " AND pillar=?"
        pay_params += [pillar]
    pay_sql += " GROUP BY siswa_code"

    pay_map = {}
    for r in conn.execute(pay_sql, pay_params).fetchall():
        pay_map[r["siswa_code"]] = r["t"]

    conn.close()

    result = []
    for s in siswa:
        code     = s["code"]
        total_b  = bgt_map.get(code, 0)
        total_p  = pay_map.get(code, 0)
        result.append({
            "code":          code,
            "nama":          s["nama"],
            "jenjang":       s["jenjang"],
            "angkatan":      s["angkatan"],
            "program":       s["program"],
            "status":        s["status"],
            "total_budget":  total_b,
            "total_payment": total_p,
            "sisa":          total_b - total_p,
        })
    return result
```

- [ ] **Step 5: Jalankan test — pastikan PASS**

```bash
cd C:\Financehub\app
pytest tests/test_beasiswa_service.py -v
```

Expected: semua test PASS (14+ tests).

- [ ] **Step 6: Commit**

```bash
git add app/modules/beasiswa/__init__.py app/modules/beasiswa/service.py app/tests/test_beasiswa_service.py
git commit -m "feat: beasiswa service.py — siswa CRUD, budget, payment, rekap queries"
```

---

## Task 2: beasiswa/routes.py (HTML)

**Files:**
- Create: `C:\Financehub\app\modules\beasiswa\routes.py`

- [ ] **Step 1: Tulis modules/beasiswa/routes.py**

```python
# C:\Financehub\app\modules\beasiswa\routes.py
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session
from flask_jwt_extended import get_jwt
from auth.middleware import jwt_html_required, role_required, html_role_required
from modules.beasiswa.service import (
    generate_kode_siswa, get_siswa_list, get_siswa_detail,
    add_siswa, update_siswa, add_budget_batch, get_budget,
    add_payment_batch, get_payment, get_sisa_budget, get_rekap
)
import config

bp = Blueprint("beasiswa", __name__, url_prefix="/beasiswa")


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


def _company_id():
    return session.get("company_id")


@bp.route("/")
@jwt_html_required
def index():
    if not _company_id():
        return redirect(url_for("dashboard.select_company"))
    siswa_list = get_siswa_list(_company_id())
    return render_template(
        "beasiswa/index.html",
        siswa_list=siswa_list,
        jenjang=config.JENJANG,
        program=config.PROGRAM,
        status_siswa=config.STATUS_SISWA,
        pillar=config.PILLAR,
        cat1_bgt=config.CAT1_BGT,
        cat2_sem=config.CAT2_SEM,
        perusahaan=config.PERUSAHAAN,
        active_page="beasiswa",
        **_ctx()
    )


# ── SISWA CRUD (JSON endpoints untuk form di halaman index) ───────────

@bp.route("/siswa/generate-kode")
@role_required("requester", "verificator", "releaser")
def siswa_generate_kode():
    jenjang  = request.args.get("jenjang", "").strip()
    angkatan = request.args.get("angkatan", "").strip()
    if not jenjang or not angkatan.isdigit() or len(angkatan) != 4:
        return jsonify({"ok": False, "pesan": "Jenjang dan angkatan (4 digit) wajib diisi."})
    kode = generate_kode_siswa(jenjang, int(angkatan), _company_id())
    return jsonify({"ok": True, "kode": kode})


@bp.route("/siswa/tambah", methods=["POST"])
@role_required("requester", "verificator")
def siswa_tambah():
    data   = request.get_json(force=True)
    result = add_siswa(_company_id(), data)
    return jsonify(result)


@bp.route("/siswa/<code>")
@role_required("requester", "verificator", "releaser")
def siswa_detail(code):
    row = get_siswa_detail(_company_id(), code)
    if not row:
        return jsonify({"ok": False, "pesan": "Tidak ditemukan."})
    return jsonify({"ok": True, "data": row})


@bp.route("/siswa/<code>/update", methods=["POST"])
@role_required("requester", "verificator")
def siswa_update(code):
    data   = request.get_json(force=True)
    result = update_siswa(_company_id(), code, data)
    return jsonify(result)


@bp.route("/siswa/<code>/sisa-budget")
@role_required("requester", "verificator", "releaser")
def siswa_sisa_budget(code):
    sisa = get_sisa_budget(_company_id(), code)
    return jsonify({"ok": True, **sisa})


# ── BUDGET ────────────────────────────────────────────────────────────

@bp.route("/budget/siswa/<code>")
@role_required("requester", "verificator", "releaser")
def budget_by_siswa(code):
    result = get_budget(_company_id(), code)
    siswa  = get_siswa_detail(_company_id(), code)
    return jsonify({"ok": True, "nama": siswa["nama"] if siswa else "", **result})


@bp.route("/budget/tambah", methods=["POST"])
@role_required("requester", "verificator")
def budget_tambah():
    data   = request.get_json(force=True)
    code   = (data.get("code") or "").strip()
    tgl    = data.get("tanggal", "")
    pillar = data.get("pillar", "")
    items  = data.get("items", [])
    if not code:
        return jsonify({"ok": False, "pesan": "Code siswa wajib diisi."})
    result = add_budget_batch(_company_id(), code, tgl, pillar, items)
    return jsonify(result)


# ── PAYMENT ───────────────────────────────────────────────────────────

@bp.route("/payment/tambah", methods=["POST"])
@role_required("requester")
def payment_tambah():
    data       = request.get_json(force=True)
    code       = (data.get("code") or "").strip()
    tgl        = data.get("tanggal", "")
    pillar     = data.get("pillar", "")
    perusahaan = data.get("perusahaan", "")
    items      = data.get("items", [])
    if not code:
        return jsonify({"ok": False, "pesan": "Code siswa wajib diisi."})
    result = add_payment_batch(_company_id(), code, tgl, pillar, perusahaan, items)
    return jsonify(result)


# ── REKAP ─────────────────────────────────────────────────────────────

@bp.route("/rekap/data")
@role_required("requester", "verificator", "releaser")
def rekap_data():
    program = request.args.get("program", "")
    pillar  = request.args.get("pillar", "")
    status  = request.args.get("status", "")
    rows    = get_rekap(_company_id(), program=program, pillar=pillar, status=status)
    return jsonify({"ok": True, "rows": rows})


@bp.route("/rekap/export/csv")
@role_required("requester", "verificator", "releaser")
def rekap_export_csv():
    import csv, io
    from flask import Response
    program = request.args.get("program", "")
    pillar  = request.args.get("pillar", "")
    status  = request.args.get("status", "")
    rows    = get_rekap(_company_id(), program=program, pillar=pillar, status=status)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Code", "Nama", "Jenjang", "Angkatan", "Program",
                     "Status", "Total Budget", "Total Payment", "Sisa"])
    for r in rows:
        writer.writerow([
            r["code"], r["nama"], r["jenjang"], r["angkatan"], r["program"],
            r["status"],
            r["total_budget"], r["total_payment"], r["sisa"]
        ])
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=rekap_beasiswa.csv"}
    )


@bp.route("/rekap/export/pdf")
@role_required("requester", "verificator", "releaser")
def rekap_export_pdf():
    from flask import send_file
    import io
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import cm

    program = request.args.get("program", "")
    pillar  = request.args.get("pillar", "")
    status  = request.args.get("status", "")
    rows    = get_rekap(_company_id(), program=program, pillar=pillar, status=status)

    buffer = io.BytesIO()
    doc    = SimpleDocTemplate(buffer, pagesize=landscape(A4),
                               leftMargin=1.5*cm, rightMargin=1.5*cm,
                               topMargin=1.5*cm, bottomMargin=1.5*cm)
    styles = getSampleStyleSheet()
    elements = []

    # Title
    elements.append(Paragraph(
        f"Rekap Beasiswa — {session.get('company_name', '')}",
        styles["Title"]
    ))
    elements.append(Spacer(1, 0.4*cm))

    # Table
    header = ["No", "Code", "Nama", "Jenjang", "Program", "Status",
              "Budget", "Payment", "Sisa"]
    data_rows = [header]
    for i, r in enumerate(rows, 1):
        def fmt(n): return f"{n:,.0f}"
        data_rows.append([
            i, r["code"], r["nama"], r["jenjang"], r["program"], r["status"],
            fmt(r["total_budget"]), fmt(r["total_payment"]), fmt(r["sisa"])
        ])

    if rows:
        total_b = sum(r["total_budget"] for r in rows)
        total_p = sum(r["total_payment"] for r in rows)
        data_rows.append(["", "", "TOTAL", "", "", "",
                          f"{total_b:,.0f}", f"{total_p:,.0f}", f"{total_b-total_p:,.0f}"])

    tbl = Table(data_rows, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#1a56db")),
        ("TEXTCOLOR",  (0,0), (-1,0), colors.white),
        ("FONTNAME",   (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",   (0,0), (-1,-1), 8),
        ("ALIGN",      (6,0), (-1,-1), "RIGHT"),
        ("GRID",       (0,0), (-1,-1), 0.5, colors.HexColor("#e5e7eb")),
        ("BACKGROUND", (0,-1), (-1,-1), colors.HexColor("#f3f4f6")),
        ("FONTNAME",   (0,-1), (-1,-1), "Helvetica-Bold"),
        ("ROWBACKGROUNDS", (0,1), (-1,-2), [colors.white, colors.HexColor("#f8fafc")]),
    ]))
    elements.append(tbl)

    doc.build(elements)
    buffer.seek(0)
    return send_file(buffer, mimetype="application/pdf",
                     download_name="rekap_beasiswa.pdf", as_attachment=True)
```

- [ ] **Step 2: Update app.py — register beasiswa blueprint**

Tambahkan baris ini di `create_app()` dalam `app.py`, setelah baris register dashboard blueprint:

```python
    from modules.beasiswa.routes import bp as beasiswa_bp
    app.register_blueprint(beasiswa_bp)
```

- [ ] **Step 3: Jalankan app dan test manual**

```bash
cd C:\Financehub\app
python app.py
```

Buka `http://localhost:8080/beasiswa` — harus tampil halaman dengan 4 tab (template belum ada, jadi error 404 template — itu normal, dikerjakan di Task 3).

- [ ] **Step 4: Commit**

```bash
git add app/modules/beasiswa/routes.py app/app.py
git commit -m "feat: beasiswa routes.py — HTML + JSON endpoints untuk siswa/budget/payment/rekap"
```

---

## Task 3: Template Beasiswa (4 Tab)

**Files:**
- Create: `C:\Financehub\app\templates\beasiswa\index.html`

- [ ] **Step 1: Buat folder templates/beasiswa/**

```bash
mkdir templates\beasiswa
```

- [ ] **Step 2: Tulis templates/beasiswa/index.html**

```html
<!-- C:\Financehub\app\templates\beasiswa\index.html -->
{% extends "base.html" %}
{% block title %}Beasiswa{% endblock %}

{% block content %}
<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1.25rem">
  <h1 style="font-size:1.25rem; font-weight:700">🎓 Beasiswa — {{ company_name }}</h1>
</div>

<div data-tabs>
  <div class="tabs">
    <button class="tab-btn" data-tab="tab-siswa">Data Siswa</button>
    <button class="tab-btn" data-tab="tab-budget">Budget</button>
    <button class="tab-btn" data-tab="tab-payment">Payment</button>
    <button class="tab-btn" data-tab="tab-rekap">Rekap</button>
  </div>

  <!-- ═══════════════════════════════════════════════════════════ TAB SISWA -->
  <div class="tab-panel" id="tab-siswa">
    <div style="display:flex; gap:.75rem; margin-bottom:1rem; flex-wrap:wrap; align-items:center">
      <input type="text" id="siswa-search" placeholder="Cari nama/kode..." style="width:220px" oninput="filterSiswa()">
      <select id="siswa-filter-status" onchange="filterSiswa()" style="width:140px">
        <option value="">Semua Status</option>
        {% for s in status_siswa %}<option value="{{ s }}">{{ s }}</option>{% endfor %}
      </select>
      {% if current_role in ['requester','verificator'] %}
      <button class="btn btn-primary btn-sm" onclick="openModal('modal-siswa-tambah')">+ Tambah Siswa</button>
      {% endif %}
    </div>

    <div class="table-wrap">
      <table id="siswa-table">
        <thead>
          <tr>
            <th>Code</th><th>Nama</th><th>Jenjang</th><th>Angkatan</th>
            <th>Program</th><th>Universitas</th><th>Status</th><th>Aksi</th>
          </tr>
        </thead>
        <tbody>
          {% for s in siswa_list %}
          <tr data-search="{{ s.nama|lower }} {{ s.code|lower }}" data-status="{{ s.status }}">
            <td><code>{{ s.code }}</code></td>
            <td>{{ s.nama }}</td>
            <td>{{ s.jenjang }}</td>
            <td>{{ s.angkatan }}</td>
            <td>{{ s.program }}</td>
            <td>{{ s.universitas }}</td>
            <td>
              <span class="badge {% if s.status=='Aktif' %}badge-green{% elif s.status=='lulus' %}badge-blue{% else %}badge-red{% endif %}">
                {{ s.status }}
              </span>
            </td>
            <td>
              <button class="btn btn-secondary btn-sm" onclick="openEditSiswa('{{ s.code }}')">Edit</button>
              <button class="btn btn-secondary btn-sm" onclick="openBudgetSiswa('{{ s.code }}', '{{ s.nama }}')">Sisa</button>
            </td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
  </div>

  <!-- ════════════════════════════════════════════════════════════ TAB BUDGET -->
  <div class="tab-panel" id="tab-budget">
    <div class="card">
      <div class="card-title">Input Budget</div>
      <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:.75rem; margin-bottom:1rem">
        <div class="form-group">
          <label>Siswa</label>
          <select id="bgt-siswa">
            <option value="">-- Pilih Siswa --</option>
            {% for s in siswa_list %}
            <option value="{{ s.code }}">{{ s.code }} — {{ s.nama }}</option>
            {% endfor %}
          </select>
        </div>
        <div class="form-group">
          <label>Tanggal</label>
          <input type="date" id="bgt-tgl">
        </div>
        <div class="form-group">
          <label>Pillar</label>
          <select id="bgt-pillar">
            <option value="">-- Pillar --</option>
            {% for p in pillar %}<option value="{{ p }}">{{ p }}</option>{% endfor %}
          </select>
        </div>
      </div>

      <div id="bgt-items">
        <div class="bgt-row" style="display:grid; grid-template-columns:1fr 1fr 1fr auto; gap:.5rem; margin-bottom:.5rem; align-items:end">
          <div class="form-group" style="margin:0">
            <label>Kategori 1</label>
            <select class="bgt-cat1">
              {% for c in cat1_bgt %}<option value="{{ c }}">{{ c }}</option>{% endfor %}
            </select>
          </div>
          <div class="form-group" style="margin:0">
            <label>Kategori 2</label>
            <select class="bgt-cat2">
              {% for c in cat2_sem %}<option value="{{ c }}">{{ c }}</option>{% endfor %}
            </select>
          </div>
          <div class="form-group" style="margin:0">
            <label>Amount</label>
            <input type="number" class="bgt-amount" placeholder="0" min="0">
          </div>
          <button class="btn btn-secondary btn-sm" onclick="removeBgtRow(this)">✕</button>
        </div>
      </div>
      <div style="display:flex; gap:.5rem; margin-top:.5rem">
        <button class="btn btn-secondary btn-sm" onclick="addBgtRow()">+ Baris</button>
        <button class="btn btn-primary" onclick="saveBudget()">💾 Simpan Budget</button>
      </div>
    </div>

    <!-- Sisa budget per siswa -->
    <div class="card" id="bgt-sisa-card" style="display:none">
      <div class="card-title">Sisa Budget — <span id="bgt-sisa-nama"></span></div>
      <div class="table-wrap">
        <table id="bgt-sisa-table">
          <thead><tr><th>Kategori</th><th class="num-right">Budget</th><th class="num-right">Payment</th><th class="num-right">Sisa</th></tr></thead>
          <tbody></tbody>
          <tfoot><tr><th>Total</th><th class="num-right" id="bgt-total-b"></th><th class="num-right" id="bgt-total-p"></th><th class="num-right" id="bgt-total-s"></th></tr></tfoot>
        </table>
      </div>
    </div>
  </div>

  <!-- ══════════════════════════════════════════════════════════ TAB PAYMENT -->
  <div class="tab-panel" id="tab-payment">
    {% if current_role == 'requester' %}
    <div class="card">
      <div class="card-title">Input Payment</div>
      <div style="display:grid; grid-template-columns:1fr 1fr 1fr 1fr; gap:.75rem; margin-bottom:1rem">
        <div class="form-group">
          <label>Siswa</label>
          <select id="pay-siswa">
            <option value="">-- Pilih Siswa --</option>
            {% for s in siswa_list %}
            <option value="{{ s.code }}">{{ s.code }} — {{ s.nama }}</option>
            {% endfor %}
          </select>
        </div>
        <div class="form-group">
          <label>Tanggal</label>
          <input type="date" id="pay-tgl">
        </div>
        <div class="form-group">
          <label>Pillar</label>
          <select id="pay-pillar">
            <option value="">-- Pillar --</option>
            {% for p in pillar %}<option value="{{ p }}">{{ p }}</option>{% endfor %}
          </select>
        </div>
        <div class="form-group">
          <label>Perusahaan</label>
          <select id="pay-perusahaan">
            <option value="">-- Perusahaan --</option>
            {% for p in perusahaan %}<option value="{{ p }}">{{ p }}</option>{% endfor %}
          </select>
        </div>
      </div>

      <div id="pay-items">
        <div class="pay-row" style="display:grid; grid-template-columns:1fr 1fr 1fr auto; gap:.5rem; margin-bottom:.5rem; align-items:end">
          <div class="form-group" style="margin:0"><label>Cat 1</label>
            <select class="pay-cat1">{% for c in cat1_bgt %}<option value="{{ c }}">{{ c }}</option>{% endfor %}</select>
          </div>
          <div class="form-group" style="margin:0"><label>Cat 2</label>
            <select class="pay-cat2">{% for c in cat2_sem %}<option value="{{ c }}">{{ c }}</option>{% endfor %}</select>
          </div>
          <div class="form-group" style="margin:0"><label>Amount</label>
            <input type="number" class="pay-amount" placeholder="0" min="0">
          </div>
          <button class="btn btn-secondary btn-sm" onclick="removePayRow(this)">✕</button>
        </div>
      </div>
      <div style="display:flex; gap:.5rem; margin-top:.5rem">
        <button class="btn btn-secondary btn-sm" onclick="addPayRow()">+ Baris</button>
        <button class="btn btn-primary" onclick="savePayment()">💾 Simpan Payment</button>
      </div>
    </div>
    {% endif %}

    <!-- List payment -->
    <div class="card">
      <div class="card-title">Daftar Payment</div>
      <div id="pay-list-wrap">
        <p style="color:var(--text-muted); font-size:.875rem">Pilih siswa untuk lihat payment.</p>
      </div>
    </div>
  </div>

  <!-- ══════════════════════════════════════════════════════════ TAB REKAP -->
  <div class="tab-panel" id="tab-rekap">
    <div style="display:flex; gap:.75rem; margin-bottom:1rem; flex-wrap:wrap; align-items:flex-end">
      <div class="form-group" style="margin:0; min-width:160px">
        <label>Program</label>
        <select id="rekap-program" onchange="loadRekap()">
          <option value="">Semua Program</option>
          {% for p in program %}<option value="{{ p }}">{{ p }}</option>{% endfor %}
        </select>
      </div>
      <div class="form-group" style="margin:0; min-width:140px">
        <label>Pillar</label>
        <select id="rekap-pillar" onchange="loadRekap()">
          <option value="">Semua Pillar</option>
          {% for p in pillar %}<option value="{{ p }}">{{ p }}</option>{% endfor %}
        </select>
      </div>
      <div class="form-group" style="margin:0; min-width:140px">
        <label>Status</label>
        <select id="rekap-status" onchange="loadRekap()">
          <option value="">Semua Status</option>
          {% for s in status_siswa %}<option value="{{ s }}">{{ s }}</option>{% endfor %}
        </select>
      </div>
      <a id="btn-export-csv" href="#" class="btn btn-secondary" onclick="exportRekap('csv')">📥 CSV</a>
      <a id="btn-export-pdf" href="#" class="btn btn-secondary" onclick="exportRekap('pdf')">📄 PDF</a>
    </div>

    <div class="table-wrap">
      <table>
        <thead>
          <tr><th>Code</th><th>Nama</th><th>Jenjang</th><th>Program</th><th>Status</th>
          <th class="num-right">Budget</th><th class="num-right">Payment</th><th class="num-right">Sisa</th></tr>
        </thead>
        <tbody id="rekap-tbody"></tbody>
        <tfoot>
          <tr>
            <td colspan="5"><strong>Total</strong></td>
            <td class="num-right" id="rekap-total-b"></td>
            <td class="num-right" id="rekap-total-p"></td>
            <td class="num-right" id="rekap-total-s"></td>
          </tr>
        </tfoot>
      </table>
    </div>
  </div>
</div>

<!-- ══════════════════════════════════════════════════ MODAL: Tambah Siswa -->
<div class="modal-overlay" id="modal-siswa-tambah">
  <div class="modal" style="width:min(700px,95vw)">
    <div class="modal-header">
      <span class="modal-title" id="siswa-modal-title">Tambah Siswa Baru</span>
      <button class="modal-close" onclick="closeModal('modal-siswa-tambah')">✕</button>
    </div>
    <div style="display:grid; grid-template-columns:1fr 1fr; gap:.75rem">
      <div class="form-group">
        <label>Jenjang</label>
        <select id="s-jenjang" onchange="genKode()">
          {% for j in jenjang %}<option value="{{ j }}">{{ j }}</option>{% endfor %}
        </select>
      </div>
      <div class="form-group">
        <label>Angkatan (tahun)</label>
        <input type="number" id="s-angkatan" placeholder="2025" min="2000" max="2099" onchange="genKode()">
      </div>
      <div class="form-group">
        <label>Code Siswa (auto-generate)</label>
        <input type="text" id="s-code" placeholder="Pilih jenjang + angkatan dulu" readonly style="background:#f3f4f6">
      </div>
      <div class="form-group">
        <label>Nama Lengkap</label>
        <input type="text" id="s-nama" placeholder="Nama lengkap">
      </div>
      <div class="form-group">
        <label>Program</label>
        <select id="s-program">
          {% for p in program %}<option value="{{ p }}">{{ p }}</option>{% endfor %}
        </select>
      </div>
      <div class="form-group">
        <label>Status</label>
        <select id="s-status">
          {% for s in status_siswa %}<option value="{{ s }}">{{ s }}</option>{% endfor %}
        </select>
      </div>
      <div class="form-group">
        <label>Fakultas</label>
        <input type="text" id="s-fakultas" placeholder="Nama Fakultas">
      </div>
      <div class="form-group">
        <label>Universitas</label>
        <input type="text" id="s-universitas" placeholder="Nama Universitas">
      </div>
      <div class="form-group">
        <label>Bank</label>
        <input type="text" id="s-bank" placeholder="BCA / BNI / ...">
      </div>
      <div class="form-group">
        <label>No. Rekening</label>
        <input type="text" id="s-norek" placeholder="Nomor rekening">
      </div>
      <div class="form-group">
        <label>Nama Rekening</label>
        <input type="text" id="s-namarek" placeholder="Nama pemilik rekening">
      </div>
      <div class="form-group">
        <label>Referensi</label>
        <input type="text" id="s-referensi" placeholder="Referensi / sumber">
      </div>
    </div>
    <div class="form-group">
      <label>Catatan</label>
      <textarea id="s-catatan" rows="2" placeholder="Catatan bebas"></textarea>
    </div>
    <div style="display:flex; gap:.75rem; margin-top:.75rem; justify-content:flex-end">
      <button class="btn btn-secondary" onclick="closeModal('modal-siswa-tambah')">Batal</button>
      <button class="btn btn-primary" id="btn-simpan-siswa" onclick="simpanSiswa()">💾 Simpan</button>
    </div>
  </div>
</div>

<!-- ══════════════════════════════════════════════ MODAL: Sisa Budget Siswa -->
<div class="modal-overlay" id="modal-sisa">
  <div class="modal">
    <div class="modal-header">
      <span class="modal-title">Sisa Budget — <span id="sisa-modal-nama"></span></span>
      <button class="modal-close" onclick="closeModal('modal-sisa')">✕</button>
    </div>
    <div class="table-wrap">
      <table>
        <thead><tr><th>Kategori</th><th class="num-right">Budget</th><th class="num-right">Payment</th><th class="num-right">Sisa</th></tr></thead>
        <tbody id="sisa-modal-body"></tbody>
        <tfoot>
          <tr>
            <th>Total</th>
            <th class="num-right" id="sisa-total-b"></th>
            <th class="num-right" id="sisa-total-p"></th>
            <th class="num-right" id="sisa-total-s"></th>
          </tr>
        </tfoot>
      </table>
    </div>
  </div>
</div>
{% endblock %}

{% block scripts %}
<script>
const ROLE = "{{ current_role }}";

// ── Filter tabel siswa ────────────────────────────────────────────────
function filterSiswa() {
  const q      = document.getElementById("siswa-search").value.toLowerCase();
  const status = document.getElementById("siswa-filter-status").value;
  document.querySelectorAll("#siswa-table tbody tr").forEach(tr => {
    const matchQ = !q || tr.dataset.search.includes(q);
    const matchS = !status || tr.dataset.status === status;
    tr.style.display = (matchQ && matchS) ? "" : "none";
  });
}

// ── Auto-generate kode siswa ──────────────────────────────────────────
let _genDebounce;
async function genKode() {
  clearTimeout(_genDebounce);
  const jenjang  = document.getElementById("s-jenjang").value;
  const angkatan = document.getElementById("s-angkatan").value;
  if (!jenjang || !angkatan || angkatan.length !== 4) return;
  _genDebounce = setTimeout(async () => {
    const r    = await apiFetch(`/beasiswa/siswa/generate-kode?jenjang=${jenjang}&angkatan=${angkatan}`);
    const data = await r.json();
    if (data.ok) document.getElementById("s-code").value = data.kode;
  }, 400);
}

// ── Simpan siswa ──────────────────────────────────────────────────────
let _editMode = false;
let _editCode = "";

async function simpanSiswa() {
  const payload = {
    code: document.getElementById("s-code").value,
    nama: document.getElementById("s-nama").value,
    jenjang: document.getElementById("s-jenjang").value,
    angkatan: parseInt(document.getElementById("s-angkatan").value) || null,
    program: document.getElementById("s-program").value,
    fakultas: document.getElementById("s-fakultas").value,
    universitas: document.getElementById("s-universitas").value,
    bank: document.getElementById("s-bank").value,
    norek: document.getElementById("s-norek").value,
    namarek: document.getElementById("s-namarek").value,
    referensi: document.getElementById("s-referensi").value,
    status: document.getElementById("s-status").value,
    catatan: document.getElementById("s-catatan").value,
  };

  const url  = _editMode ? `/beasiswa/siswa/${_editCode}/update` : "/beasiswa/siswa/tambah";
  const resp = await apiFetch(url, { method: "POST", body: JSON.stringify(payload) });
  const data = await resp.json();

  if (data.ok) {
    showToast(data.pesan);
    closeModal("modal-siswa-tambah");
    setTimeout(() => location.reload(), 800);
  } else {
    showToast(data.pesan, "error");
  }
}

async function openEditSiswa(code) {
  const r    = await apiFetch(`/beasiswa/siswa/${code}`);
  const data = await r.json();
  if (!data.ok) { showToast("Gagal load data", "error"); return; }
  const s = data.data;
  _editMode = true; _editCode = code;
  document.getElementById("siswa-modal-title").textContent = `Edit Siswa — ${code}`;
  document.getElementById("s-code").value       = s.code;
  document.getElementById("s-jenjang").value    = s.jenjang || "";
  document.getElementById("s-angkatan").value   = s.angkatan || "";
  document.getElementById("s-nama").value       = s.nama;
  document.getElementById("s-program").value    = s.program || "";
  document.getElementById("s-status").value     = s.status;
  document.getElementById("s-fakultas").value   = s.fakultas || "";
  document.getElementById("s-universitas").value = s.universitas || "";
  document.getElementById("s-bank").value       = s.bank || "";
  document.getElementById("s-norek").value      = s.norek || "";
  document.getElementById("s-namarek").value    = s.namarek || "";
  document.getElementById("s-referensi").value  = s.referensi || "";
  document.getElementById("s-catatan").value    = s.catatan || "";
  openModal("modal-siswa-tambah");
}

async function openBudgetSiswa(code, nama) {
  document.getElementById("sisa-modal-nama").textContent = nama;
  const r    = await apiFetch(`/beasiswa/siswa/${code}/sisa-budget`);
  const data = await r.json();
  const all  = {...data.budget};
  Object.keys(data.payment).forEach(k => { if (!all[k]) all[k] = 0; });

  const tbody = document.getElementById("sisa-modal-body");
  tbody.innerHTML = Object.entries(all).map(([cat, b]) => {
    const p = data.payment[cat] || 0;
    const s = b - p;
    return `<tr>
      <td>${cat}</td>
      <td class="num-right">${fmtRupiah(b)}</td>
      <td class="num-right">${fmtRupiah(p)}</td>
      <td class="num-right" style="color:${s<0?'var(--danger)':'inherit'}">${fmtRupiah(s)}</td>
    </tr>`;
  }).join("");
  document.getElementById("sisa-total-b").textContent = fmtRupiah(data.total_budget);
  document.getElementById("sisa-total-p").textContent = fmtRupiah(data.total_payment);
  document.getElementById("sisa-total-s").textContent = fmtRupiah(data.total_sisa);
  openModal("modal-sisa");
}

// ── Budget input ──────────────────────────────────────────────────────
function addBgtRow() {
  const container = document.getElementById("bgt-items");
  const div       = document.createElement("div");
  div.className   = "bgt-row";
  div.style.cssText = "display:grid; grid-template-columns:1fr 1fr 1fr auto; gap:.5rem; margin-bottom:.5rem; align-items:end";
  div.innerHTML = `
    <div class="form-group" style="margin:0"><select class="bgt-cat1">
      ${{{ cat1_bgt | tojson }}.map(c => `<option value="${c}">${c}</option>`).join("")}
    </select></div>
    <div class="form-group" style="margin:0"><select class="bgt-cat2">
      ${{{ cat2_sem | tojson }}.map(c => `<option value="${c}">${c}</option>`).join("")}
    </select></div>
    <div class="form-group" style="margin:0"><input type="number" class="bgt-amount" placeholder="0" min="0"></div>
    <button class="btn btn-secondary btn-sm" onclick="removeBgtRow(this)">✕</button>`;
  container.appendChild(div);
}
function removeBgtRow(btn) { btn.closest(".bgt-row").remove(); }

async function saveBudget() {
  const code   = document.getElementById("bgt-siswa").value;
  const tgl    = document.getElementById("bgt-tgl").value;
  const pillar = document.getElementById("bgt-pillar").value;
  if (!code || !tgl || !pillar) {
    showToast("Pilih siswa, tanggal, dan pillar terlebih dahulu.", "error"); return;
  }
  const items = [...document.querySelectorAll(".bgt-row")].map(row => ({
    cat1: row.querySelector(".bgt-cat1").value,
    cat2: row.querySelector(".bgt-cat2").value,
    amount: parseFloat(row.querySelector(".bgt-amount").value) || 0,
  }));
  const resp = await apiFetch("/beasiswa/budget/tambah", {
    method: "POST", body: JSON.stringify({ code, tanggal: tgl, pillar, items })
  });
  const data = await resp.json();
  showToast(data.pesan, data.ok ? "success" : "error");
}

// ── Payment input ─────────────────────────────────────────────────────
function addPayRow() {
  const container = document.getElementById("pay-items");
  const div       = document.createElement("div");
  div.className   = "pay-row";
  div.style.cssText = "display:grid; grid-template-columns:1fr 1fr 1fr auto; gap:.5rem; margin-bottom:.5rem; align-items:end";
  div.innerHTML = `
    <div class="form-group" style="margin:0"><select class="pay-cat1">
      ${{{ cat1_bgt | tojson }}.map(c => `<option value="${c}">${c}</option>`).join("")}
    </select></div>
    <div class="form-group" style="margin:0"><select class="pay-cat2">
      ${{{ cat2_sem | tojson }}.map(c => `<option value="${c}">${c}</option>`).join("")}
    </select></div>
    <div class="form-group" style="margin:0"><input type="number" class="pay-amount" placeholder="0" min="0"></div>
    <button class="btn btn-secondary btn-sm" onclick="removePayRow(this)">✕</button>`;
  container.appendChild(div);
}
function removePayRow(btn) { btn.closest(".pay-row").remove(); }

async function savePayment() {
  const code       = document.getElementById("pay-siswa").value;
  const tgl        = document.getElementById("pay-tgl").value;
  const pillar     = document.getElementById("pay-pillar").value;
  const perusahaan = document.getElementById("pay-perusahaan").value;
  if (!code || !tgl || !pillar || !perusahaan) {
    showToast("Semua field wajib diisi.", "error"); return;
  }
  const items = [...document.querySelectorAll(".pay-row")].map(row => ({
    cat1: row.querySelector(".pay-cat1").value,
    cat2: row.querySelector(".pay-cat2").value,
    cat3: "", cat4: "",
    amount: parseFloat(row.querySelector(".pay-amount").value) || 0,
  }));
  const resp = await apiFetch("/beasiswa/payment/tambah", {
    method: "POST", body: JSON.stringify({ code, tanggal: tgl, pillar, perusahaan, items })
  });
  const data = await resp.json();
  showToast(data.pesan, data.ok ? "success" : "error");
}

// ── Rekap ─────────────────────────────────────────────────────────────
async function loadRekap() {
  const program = document.getElementById("rekap-program").value;
  const pillar  = document.getElementById("rekap-pillar").value;
  const status  = document.getElementById("rekap-status").value;
  const params  = new URLSearchParams({ program, pillar, status });
  const resp    = await apiFetch(`/beasiswa/rekap/data?${params}`);
  const data    = await resp.json();
  if (!data.ok) return;

  const tbody = document.getElementById("rekap-tbody");
  tbody.innerHTML = data.rows.map(r => `<tr>
    <td><code>${r.code}</code></td>
    <td>${r.nama}</td>
    <td>${r.jenjang || ""}</td>
    <td>${r.program || ""}</td>
    <td><span class="badge ${r.status==='Aktif'?'badge-green':r.status==='lulus'?'badge-blue':'badge-red'}">${r.status}</span></td>
    <td class="num-right">${fmtRupiah(r.total_budget)}</td>
    <td class="num-right">${fmtRupiah(r.total_payment)}</td>
    <td class="num-right" style="color:${r.sisa<0?'var(--danger)':'inherit'}">${fmtRupiah(r.sisa)}</td>
  </tr>`).join("");

  const totB = data.rows.reduce((s,r) => s+r.total_budget,  0);
  const totP = data.rows.reduce((s,r) => s+r.total_payment, 0);
  document.getElementById("rekap-total-b").textContent = fmtRupiah(totB);
  document.getElementById("rekap-total-p").textContent = fmtRupiah(totP);
  document.getElementById("rekap-total-s").textContent = fmtRupiah(totB - totP);
}

function exportRekap(fmt) {
  const program = document.getElementById("rekap-program").value;
  const pillar  = document.getElementById("rekap-pillar").value;
  const status  = document.getElementById("rekap-status").value;
  const params  = new URLSearchParams({ program, pillar, status });
  window.location.href = `/beasiswa/rekap/export/${fmt}?${params}`;
}

// Init
document.addEventListener("DOMContentLoaded", loadRekap);
</script>
{% endblock %}
```

- [ ] **Step 3: Test manual — buka browser**

```bash
cd C:\Financehub\app
python app.py
```

Buka `http://localhost:8080/beasiswa`:
- Harus muncul 4 tab: Data Siswa, Budget, Payment, Rekap
- Tab Siswa: klik "Tambah Siswa", pilih jenjang S1 + angkatan 2025 → code harus auto-generate "1250001"
- Isi nama, program, simpan → siswa muncul di tabel
- Tab Budget: pilih siswa, isi tanggal + pillar + baris budget → simpan → toast sukses
- Tab Rekap: harus muncul baris siswa dengan angka budget

- [ ] **Step 4: Commit**

```bash
git add app/templates/beasiswa/ app/modules/beasiswa/routes.py
git commit -m "feat: beasiswa templates — 4 tab Siswa/Budget/Payment/Rekap lengkap"
```

---

**Part 2 selesai.** Beasiswa module lengkap: Siswa CRUD dengan auto-generate kode, Budget batch input, Payment batch input (status draft), Rekap dengan filter + CSV + PDF export. Lanjut ke Part 3: Payment Memo + User Management.
