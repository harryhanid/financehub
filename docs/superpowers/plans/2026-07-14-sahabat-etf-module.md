# Modul Sahabat ETF — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Halaman baru `/beasiswa/sahabat` yang menampilkan semua transaksi siswa program "Sahabat ETF" (11 siswa live) dalam satu tempat, dengan dashboard analisa budget vs payment vs realisasi, breakdown per-siswa dan per-kategori, alert siswa over-budget, dan export CSV.

**Architecture:** Modul Flask baru `modules/sahabat_etf/` (routes.py + service.py), terisolasi penuh dari `modules/beasiswa/`, mengikuti pola `modules/budget/`. Tidak ada tabel/migrasi baru — semua query read dari `siswa`/`budget_beasiswa`/`payment_beasiswa` existing, di-join lewat `siswa_code` dan difilter `siswa.program='Sahabat ETF'` (bukan `pillar`, karena kolom itu tidak reliable untuk program ini — lihat spec). Read-only + export; CRUD tetap di halaman Beasiswa umum. UI reuse `static/css/budget.css` (grid/card classes sudah ada) + Chart.js, data dimuat lewat fetch ke 3 API endpoint JSON setelah page load (pola sama seperti `budget/dashboard.html`).

**Tech Stack:** Python 3.14, Flask, SQLite, pytest, vanilla JS + Jinja2, Chart.js 4.4.4 (CDN, sudah dipakai modul Budget).

## Global Constraints

- Working directory semua command shell di plan ini: `C:\Financehub\app` (jalankan `pytest` dari situ).
- Filter program HARUS via `siswa.program = 'Sahabat ETF'` (join `siswa_code`), TIDAK PERNAH via `payment_beasiswa.pillar` — kolom itu berisi nilai lain (mis. `FINANCE`) untuk siswa program ini (diverifikasi terhadap data live).
- Realisasi = `SUM(payment_beasiswa.amount) WHERE status='complete'`. Kolom `realized_amount`/`tgl_realisasi` TIDAK dipakai (0 baris terisi di seluruh DB, tidak ada alur yang mengisinya).
- Tidak ada endpoint CRUD (create/update/delete) di modul ini — read-only + export saja.
- Full spec: `docs/superpowers/specs/2026-07-14-sahabat-etf-module-design.md`.

**Deviation dari spec (dikonfirmasi saat planning, bukan saat brainstorm):** spec menyebut "Excel (openpyxl)" untuk export. Setelah membaca kode `modules/beasiswa/routes.py`, ternyata **tidak ada satupun export di modul itu yang pakai openpyxl** — kelima tombol export yang sudah ada (`budget_export_csv`, `payment_export_csv`, `rekap_export_csv`, dst) semuanya pakai modul `csv` bawaan Python + `flask.Response`, bukan file `.xlsx`. Plan ini mengikuti pola nyata yang sudah ada di modul (CSV, bukan openpyxl) supaya konsisten dan tidak menambah dependency baru untuk satu fitur saja. Karena CSV tidak punya konsep "sheet", 2-sheet Summary+Detail dari spec dipecah jadi 2 tombol/endpoint export terpisah (`export/summary` dan `export/detail`) — pola ini sudah persis sama dengan bagaimana tab Data Budget dan Data Payment di halaman Beasiswa umum masing-masing punya tombol export sendiri.

---

### Task 1: Blueprint skeleton — routing, guard company, nav entry

**Files:**
- Create: `modules/sahabat_etf/__init__.py` (kosong)
- Create: `modules/sahabat_etf/routes.py`
- Create: `templates/sahabat_etf/index.html`
- Modify: `app.py` (daftarkan blueprint, setelah baris registrasi `budget_bp`)
- Modify: `templates/beasiswa/index.html:19` (tambah link masuk ke halaman baru)
- Test: `tests/test_sahabat_etf_routes.py`

**Interfaces:**
- Produces: blueprint Flask bernama `"sahabat_etf"`, url_prefix `/beasiswa/sahabat`. Route `GET /beasiswa/sahabat/` — dipakai Task 5/6 untuk menambahkan API/export route ke blueprint `bp` yang sama.
- Consumes: `auth.middleware.jwt_html_required` (decorator existing), `session.get("company_id"/"company_code")` (pola existing, sudah dipakai semua modul lain).

- [ ] **Step 1: Buat `modules/sahabat_etf/__init__.py` kosong**

File kosong (0 byte), supaya `modules/sahabat_etf` jadi Python package. Pola sama seperti `modules/budget/__init__.py`.

- [ ] **Step 2: Buat `modules/sahabat_etf/routes.py` — blueprint + index route**

```python
# modules/sahabat_etf/routes.py
from flask import Blueprint, render_template, session
from flask_jwt_extended import get_jwt
from auth.middleware import jwt_html_required

bp = Blueprint("sahabat_etf", __name__, url_prefix="/beasiswa/sahabat")


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


def _cid():
    return session.get("company_id")


@bp.route("/")
@jwt_html_required
def index():
    return render_template(
        "sahabat_etf/index.html",
        active_page="sahabat_etf",
        wrong_company=(session.get("company_code") != "ETF"),
        **_ctx(),
    )
```

- [ ] **Step 3: Buat `templates/sahabat_etf/index.html` — shell minimal (guard company)**

```html
{% extends "base.html" %}
{% block title %}Sahabat ETF{% endblock %}
{% block head %}
<link rel="stylesheet" href="{{ url_for('static', filename='css/budget.css') }}">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js"></script>
{% endblock %}
{% block content %}
<div class="budget-page">
  <h1>Sahabat ETF</h1>
  <p style="color:var(--text-muted);margin-top:-.5rem">Eka Tjipta Foundation / Beasiswa / Sahabat ETF</p>

  {% if wrong_company %}
  <div class="budget-card">
    <h3>Program khusus Eka Tjipta Foundation</h3>
    <p>Halaman ini hanya menampilkan data untuk company ETF. Company aktif Anda saat ini bukan ETF.</p>
    <a class="budget-btn" href="{{ url_for('dashboard.select_company') }}">Ganti Company</a>
  </div>
  {% else %}
  <div id="setf-content"><!-- diisi Task 7 --></div>
  {% endif %}
</div>
{% endblock %}
```

- [ ] **Step 4: Daftarkan blueprint di `app.py`**

Cari blok registrasi `budget_bp` (`from modules.budget.routes import bp as budget_bp` /
`app.register_blueprint(budget_bp)`) dan tambahkan tepat setelahnya:

```python
    from modules.sahabat_etf.routes import bp as sahabat_etf_bp
    app.register_blueprint(sahabat_etf_bp)
```

- [ ] **Step 5: Tambah link masuk di `templates/beasiswa/index.html`**

Old string (baris 19):
```html
      <button class="tab-btn" data-tab="tab-rekam" onclick="loadRekamMedis()">Rekam Medis</button>
    </div>
```

New string:
```html
      <button class="tab-btn" data-tab="tab-rekam" onclick="loadRekamMedis()">Rekam Medis</button>
    </div>
    <a class="tab-btn" href="/beasiswa/sahabat" style="text-decoration:none;display:inline-flex;align-items:center">Sahabat ETF ↗</a>
```

- [ ] **Step 6: Tulis test routing + guard company**

```python
# tests/test_sahabat_etf_routes.py
def login(client, username="admin", password="Admin@123"):
    return client.post("/auth/login", json={"username": username, "password": password})


def _select_etf(client):
    client.post("/select-company", data={"company_id": "2"})


def _select_smt(client):
    client.post("/select-company", data={"company_id": "1"})


def test_index_requires_login(client):
    resp = client.get("/beasiswa/sahabat/")
    assert resp.status_code == 302


def test_index_renders_after_login_and_etf_company(client):
    login(client)
    _select_etf(client)
    resp = client.get("/beasiswa/sahabat/")
    assert resp.status_code == 200
    assert b"Sahabat ETF" in resp.data
    assert b"Ganti Company" not in resp.data


def test_index_shows_wrong_company_notice_for_smt(client):
    login(client)
    _select_smt(client)
    resp = client.get("/beasiswa/sahabat/")
    assert resp.status_code == 200
    assert b"Ganti Company" in resp.data


def test_beasiswa_page_has_link_to_sahabat_etf(client):
    login(client)
    _select_etf(client)
    resp = client.get("/beasiswa/")
    assert b"/beasiswa/sahabat" in resp.data
```

- [ ] **Step 7: Jalankan test, pastikan semua PASS**

Run: `pytest tests/test_sahabat_etf_routes.py -v`
Expected: 4 passed

- [ ] **Step 8: Commit**

```bash
git add modules/sahabat_etf/__init__.py modules/sahabat_etf/routes.py \
        templates/sahabat_etf/index.html app.py templates/beasiswa/index.html \
        tests/test_sahabat_etf_routes.py
git commit -m "feat: scaffold Sahabat ETF module — blueprint, guard, nav entry"
```

---

### Task 2: Service — `get_siswa_summary` (agregat budget/payment/realisasi per siswa)

**Files:**
- Create: `modules/sahabat_etf/service.py`
- Test: `tests/test_sahabat_etf_service.py`

**Interfaces:**
- Consumes: `database.get_conn()` (existing, `sqlite3.Row` row_factory).
- Produces: `get_siswa_summary(company_id: int) -> list[dict]`, tiap dict punya key:
  `siswa_code, nama, jenjang, angkatan, status, budget_total, payment_total, realisasi_total, sisa_budget`
  (semua `*_total`/`sisa_budget` bertipe `float`). Dipakai Task 3 (`get_kategori_breakdown`)
  dan Task 5 (route `/api/summary`).
- Konstanta modul: `PROGRAM_NAME = "Sahabat ETF"` — dipakai semua fungsi service lain di file ini.

- [ ] **Step 1: Tulis test yang gagal**

```python
# tests/test_sahabat_etf_service.py
import os, sys, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config
config.DB_PATH = os.path.join(os.path.dirname(__file__), "test_sahabat_etf.db")

from database import init_db, get_conn
from modules.beasiswa.service import add_siswa, add_budget_batch, add_payment_batch
from modules.sahabat_etf.service import get_siswa_summary

COMPANY_ID = 2  # ETF


@pytest.fixture(autouse=True)
def clean_db():
    if os.path.exists(config.DB_PATH):
        os.remove(config.DB_PATH)
    init_db()
    yield
    if os.path.exists(config.DB_PATH):
        os.remove(config.DB_PATH)


def _add_siswa(code, nama, program="Sahabat ETF", company_id=COMPANY_ID):
    add_siswa(company_id, {
        "code": code, "nama": nama, "jenjang": "S1", "angkatan": 2024,
        "program": program, "fakultas": "", "universitas": "", "bank": "",
        "norek": "", "namarek": "", "referensi": "", "status": "Aktif", "catatan": "",
    })


def _mark_complete(siswa_code):
    conn = get_conn()
    conn.execute("UPDATE payment_beasiswa SET status='complete' WHERE siswa_code=?", (siswa_code,))
    conn.commit()
    conn.close()


def test_get_siswa_summary_aggregates_budget_payment_realisasi():
    _add_siswa("9990001", "Test Siswa")
    add_budget_batch(COMPANY_ID, "9990001", "2026-01-10", "SETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 5000000}])
    add_payment_batch(COMPANY_ID, "9990001", "2026-01-15", "SETF", "ETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 3000000}])
    _mark_complete("9990001")

    rows = get_siswa_summary(COMPANY_ID)
    assert len(rows) == 1
    r = rows[0]
    assert r["nama"] == "Test Siswa"
    assert r["budget_total"] == 5000000
    assert r["payment_total"] == 3000000
    assert r["realisasi_total"] == 3000000
    assert r["sisa_budget"] == 2000000


def test_get_siswa_summary_open_payment_not_counted_as_realisasi():
    _add_siswa("9990002", "Siswa Open")
    add_budget_batch(COMPANY_ID, "9990002", "2026-01-10", "SETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 1000000}])
    add_payment_batch(COMPANY_ID, "9990002", "2026-01-15", "SETF", "ETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 1000000}])
    # status default 'open' — tidak di-mark complete

    r = get_siswa_summary(COMPANY_ID)[0]
    assert r["payment_total"] == 1000000
    assert r["realisasi_total"] == 0
    assert r["sisa_budget"] == 1000000


def test_get_siswa_summary_excludes_other_program():
    _add_siswa("9990003", "Siswa Lain", program="SMART")
    rows = get_siswa_summary(COMPANY_ID)
    assert rows == []


def test_get_siswa_summary_isolated_by_company():
    _add_siswa("9990004", "Siswa SMT", company_id=1)
    rows = get_siswa_summary(COMPANY_ID)  # query company 2 (ETF)
    assert rows == []


def test_get_siswa_summary_includes_siswa_with_no_transactions():
    _add_siswa("9990005", "Siswa Kosong")
    rows = get_siswa_summary(COMPANY_ID)
    assert len(rows) == 1
    assert rows[0]["budget_total"] == 0
    assert rows[0]["payment_total"] == 0
    assert rows[0]["realisasi_total"] == 0
    assert rows[0]["sisa_budget"] == 0
```

- [ ] **Step 2: Jalankan test, pastikan gagal (module belum ada)**

Run: `pytest tests/test_sahabat_etf_service.py -v`
Expected: FAIL dengan `ModuleNotFoundError: No module named 'modules.sahabat_etf.service'`

- [ ] **Step 3: Implementasi `modules/sahabat_etf/service.py`**

```python
# modules/sahabat_etf/service.py
from database import get_conn

PROGRAM_NAME = "Sahabat ETF"


def get_siswa_summary(company_id: int) -> list:
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT s.code, s.nama, s.jenjang, s.angkatan, s.status,
               COALESCE(b.budget_total, 0)    AS budget_total,
               COALESCE(p.payment_total, 0)   AS payment_total,
               COALESCE(p.realisasi_total, 0) AS realisasi_total
        FROM siswa s
        LEFT JOIN (
            SELECT siswa_code, SUM(amount) AS budget_total
            FROM budget_beasiswa
            WHERE company_id = ?
            GROUP BY siswa_code
        ) b ON b.siswa_code = s.code
        LEFT JOIN (
            SELECT siswa_code,
                   SUM(amount) AS payment_total,
                   SUM(CASE WHEN status = 'complete' THEN amount ELSE 0 END) AS realisasi_total
            FROM payment_beasiswa
            WHERE company_id = ?
            GROUP BY siswa_code
        ) p ON p.siswa_code = s.code
        WHERE s.company_id = ? AND s.program = ?
        ORDER BY s.nama
        """,
        (company_id, company_id, company_id, PROGRAM_NAME),
    ).fetchall()
    conn.close()

    result = []
    for r in rows:
        budget = r["budget_total"] or 0
        realisasi = r["realisasi_total"] or 0
        result.append({
            "siswa_code":      r["code"],
            "nama":            r["nama"],
            "jenjang":         r["jenjang"],
            "angkatan":        r["angkatan"],
            "status":          r["status"],
            "budget_total":    budget,
            "payment_total":   r["payment_total"] or 0,
            "realisasi_total": realisasi,
            "sisa_budget":     budget - realisasi,
        })
    return result
```

- [ ] **Step 4: Jalankan test, pastikan PASS**

Run: `pytest tests/test_sahabat_etf_service.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add modules/sahabat_etf/service.py tests/test_sahabat_etf_service.py
git commit -m "feat: add get_siswa_summary for Sahabat ETF module"
```

---

### Task 3: Service — `get_kategori_breakdown` (breakdown cat1 + deteksi over-budget)

**Files:**
- Modify: `modules/sahabat_etf/service.py`
- Test: `tests/test_sahabat_etf_service.py`

**Interfaces:**
- Consumes: `get_siswa_summary(company_id)` (Task 2, dipakai ulang untuk deteksi over-budget — satu sumber kebenaran, tidak dihitung dua kali).
- Produces: `get_kategori_breakdown(company_id: int) -> dict` dengan shape:
  `{"kategori": [{"cat1": str, "budget": float, "payment": float, "realisasi": float}, ...],
    "over_budget": [{"siswa_code": str, "nama": str, "budget_total": float, "realisasi_total": float, "selisih": float}, ...]}`.
  Dipakai Task 5 (route `/api/breakdown`).

- [ ] **Step 1: Tambah test yang gagal**

Tambahkan di `tests/test_sahabat_etf_service.py` (setelah import, tambahkan `get_kategori_breakdown` ke baris import `from modules.sahabat_etf.service import ...`):

```python
from modules.sahabat_etf.service import get_siswa_summary, get_kategori_breakdown


def test_get_kategori_breakdown_groups_by_cat1():
    _add_siswa("9990010", "Siswa Kategori")
    add_budget_batch(COMPANY_ID, "9990010", "2026-01-10", "SETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 5000000},
         {"cat1": "By Tunjangan", "cat2": "Semester 1", "amount": 1000000}])
    add_payment_batch(COMPANY_ID, "9990010", "2026-01-15", "SETF", "ETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 3000000}])
    _mark_complete("9990010")

    result = get_kategori_breakdown(COMPANY_ID)
    by_cat = {k["cat1"]: k for k in result["kategori"]}
    assert by_cat["By Pendidikan"]["budget"] == 5000000
    assert by_cat["By Pendidikan"]["realisasi"] == 3000000
    assert by_cat["By Tunjangan"]["budget"] == 1000000
    assert by_cat["By Tunjangan"]["payment"] == 0
    assert result["over_budget"] == []


def test_get_kategori_breakdown_flags_over_budget_siswa():
    _add_siswa("9990011", "Siswa Over Budget")
    add_budget_batch(COMPANY_ID, "9990011", "2026-01-10", "SETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 1000000}])
    add_payment_batch(COMPANY_ID, "9990011", "2026-01-15", "SETF", "ETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 2000000}])
    _mark_complete("9990011")

    result = get_kategori_breakdown(COMPANY_ID)
    assert len(result["over_budget"]) == 1
    o = result["over_budget"][0]
    assert o["nama"] == "Siswa Over Budget"
    assert o["selisih"] == 1000000
```

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `pytest tests/test_sahabat_etf_service.py -k kategori_breakdown -v`
Expected: FAIL dengan `ImportError: cannot import name 'get_kategori_breakdown'`

- [ ] **Step 3: Tambahkan `get_kategori_breakdown` ke `modules/sahabat_etf/service.py`**

```python
def get_kategori_breakdown(company_id: int) -> dict:
    conn = get_conn()
    budget_rows = conn.execute(
        """
        SELECT b.cat1, SUM(b.amount) AS total
        FROM budget_beasiswa b
        JOIN siswa s ON s.code = b.siswa_code AND s.company_id = b.company_id
        WHERE b.company_id = ? AND s.program = ?
        GROUP BY b.cat1
        """,
        (company_id, PROGRAM_NAME),
    ).fetchall()
    payment_rows = conn.execute(
        """
        SELECT p.cat1,
               SUM(p.amount) AS total,
               SUM(CASE WHEN p.status = 'complete' THEN p.amount ELSE 0 END) AS realisasi
        FROM payment_beasiswa p
        JOIN siswa s ON s.code = p.siswa_code AND s.company_id = p.company_id
        WHERE p.company_id = ? AND s.program = ?
        GROUP BY p.cat1
        """,
        (company_id, PROGRAM_NAME),
    ).fetchall()
    conn.close()

    kategori = {}
    for r in budget_rows:
        cat1 = r["cat1"] or "(Tanpa Kategori)"
        kategori.setdefault(cat1, {"cat1": cat1, "budget": 0, "payment": 0, "realisasi": 0})
        kategori[cat1]["budget"] += r["total"] or 0
    for r in payment_rows:
        cat1 = r["cat1"] or "(Tanpa Kategori)"
        kategori.setdefault(cat1, {"cat1": cat1, "budget": 0, "payment": 0, "realisasi": 0})
        kategori[cat1]["payment"] += r["total"] or 0
        kategori[cat1]["realisasi"] += r["realisasi"] or 0

    over_budget = [
        {
            "siswa_code":      s["siswa_code"],
            "nama":            s["nama"],
            "budget_total":    s["budget_total"],
            "realisasi_total": s["realisasi_total"],
            "selisih":         s["realisasi_total"] - s["budget_total"],
        }
        for s in get_siswa_summary(company_id)
        if s["realisasi_total"] > s["budget_total"]
    ]

    return {"kategori": list(kategori.values()), "over_budget": over_budget}
```

- [ ] **Step 4: Jalankan test, pastikan PASS**

Run: `pytest tests/test_sahabat_etf_service.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add modules/sahabat_etf/service.py tests/test_sahabat_etf_service.py
git commit -m "feat: add get_kategori_breakdown with over-budget detection"
```

---

### Task 4: Service — `get_siswa_detail` & `get_all_transactions` (raw transaksi untuk expand-row & export)

**Files:**
- Modify: `modules/sahabat_etf/service.py`
- Test: `tests/test_sahabat_etf_service.py`

**Interfaces:**
- Produces:
  - `get_siswa_detail(company_id: int, siswa_code: str) -> list[dict]` — raw baris budget+payment untuk 1 siswa, key: `sumber ("Budget"|"Payment"), tanggal, cat1, cat2, amount, status`. Dipakai Task 5 (route `/api/detail/<siswa_code>`).
  - `get_all_transactions(company_id: int) -> list[dict]` — sama seperti di atas tapi untuk SEMUA siswa Sahabat ETF, plus key `siswa_code, nama`. Dipakai Task 6 (export detail CSV).

- [ ] **Step 1: Tambah test yang gagal**

Tambahkan ke `tests/test_sahabat_etf_service.py`:

```python
from modules.sahabat_etf.service import (
    get_siswa_summary, get_kategori_breakdown, get_siswa_detail, get_all_transactions,
)


def test_get_siswa_detail_returns_tagged_rows_sorted_by_date():
    _add_siswa("9990020", "Siswa Detail")
    add_budget_batch(COMPANY_ID, "9990020", "2026-02-01", "SETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 2", "amount": 4000000}])
    add_payment_batch(COMPANY_ID, "9990020", "2026-01-01", "SETF", "ETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 2000000}])

    rows = get_siswa_detail(COMPANY_ID, "9990020")
    assert len(rows) == 2
    assert rows[0]["tanggal"] == "2026-01-01"
    assert rows[0]["sumber"] == "Payment"
    assert rows[1]["tanggal"] == "2026-02-01"
    assert rows[1]["sumber"] == "Budget"


def test_get_siswa_detail_isolated_by_siswa_code():
    _add_siswa("9990021", "Siswa A")
    _add_siswa("9990022", "Siswa B")
    add_budget_batch(COMPANY_ID, "9990021", "2026-01-01", "SETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 1000000}])
    add_budget_batch(COMPANY_ID, "9990022", "2026-01-01", "SETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 2000000}])

    rows = get_siswa_detail(COMPANY_ID, "9990021")
    assert len(rows) == 1
    assert rows[0]["amount"] == 1000000


def test_get_all_transactions_includes_all_sahabat_etf_siswa():
    _add_siswa("9990030", "Siswa A")
    _add_siswa("9990031", "Siswa B")
    _add_siswa("9990032", "Siswa Lain Program", program="SMART")
    add_budget_batch(COMPANY_ID, "9990030", "2026-01-01", "SETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 1000000}])
    add_payment_batch(COMPANY_ID, "9990031", "2026-01-02", "SETF", "ETF",
        [{"cat1": "By Tunjangan", "cat2": "Semester 1", "amount": 500000}])
    add_budget_batch(COMPANY_ID, "9990032", "2026-01-01", "SETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 9999999}])

    rows = get_all_transactions(COMPANY_ID)
    assert len(rows) == 2
    codes = {r["siswa_code"] for r in rows}
    assert codes == {"9990030", "9990031"}
```

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `pytest tests/test_sahabat_etf_service.py -k "siswa_detail or all_transactions" -v`
Expected: FAIL dengan `ImportError`

- [ ] **Step 3: Tambahkan kedua fungsi ke `modules/sahabat_etf/service.py`**

```python
def get_siswa_detail(company_id: int, siswa_code: str) -> list:
    conn = get_conn()
    budget_rows = conn.execute(
        "SELECT tanggal, cat1, cat2, amount FROM budget_beasiswa "
        "WHERE company_id = ? AND siswa_code = ? ORDER BY tanggal",
        (company_id, siswa_code),
    ).fetchall()
    payment_rows = conn.execute(
        "SELECT tanggal, cat1, cat2, amount, status FROM payment_beasiswa "
        "WHERE company_id = ? AND siswa_code = ? ORDER BY tanggal",
        (company_id, siswa_code),
    ).fetchall()
    conn.close()

    rows = []
    for r in budget_rows:
        rows.append({"sumber": "Budget", "tanggal": r["tanggal"], "cat1": r["cat1"],
                     "cat2": r["cat2"], "amount": r["amount"], "status": ""})
    for r in payment_rows:
        rows.append({"sumber": "Payment", "tanggal": r["tanggal"], "cat1": r["cat1"],
                     "cat2": r["cat2"], "amount": r["amount"], "status": r["status"]})
    rows.sort(key=lambda r: r["tanggal"] or "")
    return rows


def get_all_transactions(company_id: int) -> list:
    conn = get_conn()
    budget_rows = conn.execute(
        """
        SELECT s.code AS siswa_code, s.nama, b.tanggal, b.cat1, b.cat2, b.amount
        FROM budget_beasiswa b
        JOIN siswa s ON s.code = b.siswa_code AND s.company_id = b.company_id
        WHERE b.company_id = ? AND s.program = ?
        ORDER BY s.nama, b.tanggal
        """,
        (company_id, PROGRAM_NAME),
    ).fetchall()
    payment_rows = conn.execute(
        """
        SELECT s.code AS siswa_code, s.nama, p.tanggal, p.cat1, p.cat2, p.amount, p.status
        FROM payment_beasiswa p
        JOIN siswa s ON s.code = p.siswa_code AND s.company_id = p.company_id
        WHERE p.company_id = ? AND s.program = ?
        ORDER BY s.nama, p.tanggal
        """,
        (company_id, PROGRAM_NAME),
    ).fetchall()
    conn.close()

    rows = []
    for r in budget_rows:
        rows.append({"sumber": "Budget", "siswa_code": r["siswa_code"], "nama": r["nama"],
                     "tanggal": r["tanggal"], "cat1": r["cat1"], "cat2": r["cat2"],
                     "amount": r["amount"], "status": ""})
    for r in payment_rows:
        rows.append({"sumber": "Payment", "siswa_code": r["siswa_code"], "nama": r["nama"],
                     "tanggal": r["tanggal"], "cat1": r["cat1"], "cat2": r["cat2"],
                     "amount": r["amount"], "status": r["status"]})
    return rows
```

- [ ] **Step 4: Jalankan test, pastikan PASS**

Run: `pytest tests/test_sahabat_etf_service.py -v`
Expected: 10 passed

- [ ] **Step 5: Commit**

```bash
git add modules/sahabat_etf/service.py tests/test_sahabat_etf_service.py
git commit -m "feat: add get_siswa_detail and get_all_transactions"
```

---

### Task 5: Routes — API JSON endpoints (`/api/summary`, `/api/breakdown`, `/api/detail/<code>`)

**Files:**
- Modify: `modules/sahabat_etf/routes.py`
- Test: `tests/test_sahabat_etf_routes.py`

**Interfaces:**
- Consumes: `get_siswa_summary`, `get_kategori_breakdown`, `get_siswa_detail` (Task 2-4).
- Produces: 3 route JSON endpoint di bawah `bp` (prefix `/beasiswa/sahabat`) — dipakai Task 8 (frontend JS fetch).

- [ ] **Step 1: Tulis test yang gagal**

Tambahkan ke `tests/test_sahabat_etf_routes.py`:

```python
def _seed_one_siswa(client):
    # dipanggil setelah login + _select_etf; pakai endpoint Beasiswa yang sudah ada
    # (POST /beasiswa/siswa/tambah -> add_siswa(), lihat modules/beasiswa/routes.py:73-76)
    client.post("/beasiswa/siswa/tambah", json={
        "code": "9991001", "nama": "API Test Siswa", "jenjang": "S1", "angkatan": 2024,
        "program": "Sahabat ETF", "fakultas": "", "universitas": "", "bank": "",
        "norek": "", "namarek": "", "referensi": "", "status": "Aktif", "catatan": "",
    })


def test_api_summary_returns_seeded_siswa(client):
    login(client)
    _select_etf(client)
    _seed_one_siswa(client)
    resp = client.get("/beasiswa/sahabat/api/summary")
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data["rows"]) == 1
    assert data["rows"][0]["nama"] == "API Test Siswa"


def test_api_breakdown_returns_expected_keys(client):
    login(client)
    _select_etf(client)
    _seed_one_siswa(client)
    resp = client.get("/beasiswa/sahabat/api/breakdown")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "kategori" in data
    assert "over_budget" in data


def test_api_detail_returns_empty_for_siswa_with_no_transactions(client):
    login(client)
    _select_etf(client)
    _seed_one_siswa(client)
    resp = client.get("/beasiswa/sahabat/api/detail/9991001")
    assert resp.status_code == 200
    assert resp.get_json()["rows"] == []


def test_api_summary_requires_login(client):
    resp = client.get("/beasiswa/sahabat/api/summary")
    assert resp.status_code == 302
```

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `pytest tests/test_sahabat_etf_routes.py -k api_ -v`
Expected: FAIL dengan 404 (route belum ada)

- [ ] **Step 3: Tambahkan 3 route ke `modules/sahabat_etf/routes.py`**

Tambahkan import `jsonify` di baris import Flask, dan import fungsi service:

```python
from flask import Blueprint, render_template, session, jsonify
from flask_jwt_extended import get_jwt
from auth.middleware import jwt_html_required
from modules.sahabat_etf.service import (
    get_siswa_summary, get_kategori_breakdown, get_siswa_detail,
)
```

Tambahkan di akhir file:

```python
@bp.route("/api/summary")
@jwt_html_required
def api_summary():
    return jsonify({"rows": get_siswa_summary(_cid())})


@bp.route("/api/breakdown")
@jwt_html_required
def api_breakdown():
    return jsonify(get_kategori_breakdown(_cid()))


@bp.route("/api/detail/<siswa_code>")
@jwt_html_required
def api_detail(siswa_code):
    return jsonify({"rows": get_siswa_detail(_cid(), siswa_code)})
```

- [ ] **Step 4: Jalankan test, pastikan PASS**

Run: `pytest tests/test_sahabat_etf_routes.py -v`
Expected: 8 passed

- [ ] **Step 5: Commit**

```bash
git add modules/sahabat_etf/routes.py tests/test_sahabat_etf_routes.py
git commit -m "feat: wire summary/breakdown/detail API routes for Sahabat ETF"
```

---

### Task 6: Routes — export CSV (`/export/summary`, `/export/detail`)

**Files:**
- Modify: `modules/sahabat_etf/routes.py`
- Test: `tests/test_sahabat_etf_routes.py`

**Interfaces:**
- Consumes: `get_siswa_summary`, `get_all_transactions` (Task 2, 4).
- Produces: 2 route CSV download — dipakai Task 7 (tombol export di template).

- [ ] **Step 1: Tulis test yang gagal**

```python
def test_export_summary_returns_csv(client):
    login(client)
    _select_etf(client)
    _seed_one_siswa(client)
    resp = client.get("/beasiswa/sahabat/export/summary")
    assert resp.status_code == 200
    assert resp.headers["Content-Type"].startswith("text/csv")
    assert b"API Test Siswa" in resp.data


def test_export_detail_returns_csv(client):
    login(client)
    _select_etf(client)
    resp = client.get("/beasiswa/sahabat/export/detail")
    assert resp.status_code == 200
    assert resp.headers["Content-Type"].startswith("text/csv")
    assert b"Sumber" in resp.data  # header row
```

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `pytest tests/test_sahabat_etf_routes.py -k export -v`
Expected: FAIL dengan 404

- [ ] **Step 3: Tambahkan `get_all_transactions` ke import, lalu 2 route export**

Update baris import service di `modules/sahabat_etf/routes.py`:

```python
from modules.sahabat_etf.service import (
    get_siswa_summary, get_kategori_breakdown, get_siswa_detail, get_all_transactions,
)
```

Tambahkan di akhir file:

```python
@bp.route("/export/summary")
@jwt_html_required
def export_summary():
    import csv, io
    from flask import Response
    rows = get_siswa_summary(_cid())
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["Kode", "Nama", "Jenjang", "Angkatan", "Status",
                "Budget", "Payment", "Realisasi", "Sisa Budget"])
    for r in rows:
        w.writerow([r["siswa_code"], r["nama"], r["jenjang"], r["angkatan"], r["status"],
                    r["budget_total"], r["payment_total"], r["realisasi_total"], r["sisa_budget"]])
    out.seek(0)
    return Response(out.getvalue(), mimetype="text/csv",
                     headers={"Content-Disposition": "attachment; filename=sahabat_etf_ringkasan.csv"})


@bp.route("/export/detail")
@jwt_html_required
def export_detail():
    import csv, io
    from flask import Response
    rows = get_all_transactions(_cid())
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["Sumber", "Kode Siswa", "Nama", "Tanggal", "Kategori 1", "Kategori 2", "Amount", "Status"])
    for r in rows:
        w.writerow([r["sumber"], r["siswa_code"], r["nama"], r["tanggal"],
                    r["cat1"], r["cat2"], r["amount"], r["status"]])
    out.seek(0)
    return Response(out.getvalue(), mimetype="text/csv",
                     headers={"Content-Disposition": "attachment; filename=sahabat_etf_detail_transaksi.csv"})
```

- [ ] **Step 4: Jalankan test, pastikan PASS**

Run: `pytest tests/test_sahabat_etf_routes.py -v`
Expected: 10 passed

- [ ] **Step 5: Commit**

```bash
git add modules/sahabat_etf/routes.py tests/test_sahabat_etf_routes.py
git commit -m "feat: add CSV export routes for Sahabat ETF summary and detail"
```

---

### Task 7: Template — dashboard markup lengkap (cards, alert, chart, tabel)

**Files:**
- Modify: `templates/sahabat_etf/index.html`
- Test: `tests/test_sahabat_etf_routes.py`

**Interfaces:**
- Consumes: `url_for('sahabat_etf.export_summary')`, `url_for('sahabat_etf.export_detail')` (Task 6).
- Produces: DOM element id yang jadi kontrak untuk Task 8 (JS): `setf-summary`, `setf-alert-card`,
  `setf-alert-list`, `chart-siswa`, `chart-kategori`, `setf-table` (dengan `<tbody>` di dalamnya).

- [ ] **Step 1: Tulis test yang gagal (assert elemen DOM ada)**

```python
def test_index_contains_dashboard_elements_for_etf_company(client):
    login(client)
    _select_etf(client)
    resp = client.get("/beasiswa/sahabat/")
    assert resp.status_code == 200
    for expected in (b"setf-summary", b"chart-siswa", b"chart-kategori",
                      b"setf-table", b"setf-alert-card", b"export/summary", b"export/detail"):
        assert expected in resp.data, f"missing {expected!r} in response"
```

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `pytest tests/test_sahabat_etf_routes.py -k dashboard_elements -v`
Expected: FAIL — elemen belum ada di template

- [ ] **Step 3: Ganti isi `{% else %}` block di `templates/sahabat_etf/index.html`**

Old string:
```html
  {% else %}
  <div id="setf-content"><!-- diisi Task 7 --></div>
  {% endif %}
</div>
{% endblock %}
```

New string:
```html
  {% else %}
  <div class="budget-toolbar">
    <a class="budget-btn" href="{{ url_for('sahabat_etf.export_summary') }}">Export Ringkasan (CSV)</a>
    <a class="budget-btn" href="{{ url_for('sahabat_etf.export_detail') }}">Export Detail Transaksi (CSV)</a>
  </div>

  <div class="budget-summary-grid" id="setf-summary"></div>

  <div class="budget-card" id="setf-alert-card" style="display:none">
    <h3>Siswa Over-Budget</h3>
    <ul id="setf-alert-list"></ul>
  </div>

  <div class="budget-chart-grid">
    <div class="budget-chart-card"><h3>Budget vs Realisasi per Siswa</h3><canvas id="chart-siswa"></canvas></div>
    <div class="budget-chart-card"><h3>Realisasi per Kategori</h3><canvas id="chart-kategori"></canvas></div>
  </div>

  <div class="table-wrap">
    <table id="setf-table">
      <thead>
        <tr><th>Nama</th><th>Jenjang</th><th>Angkatan</th><th>Status</th>
            <th>Budget</th><th>Payment</th><th>Realisasi</th><th>Sisa</th></tr>
      </thead>
      <tbody><tr><td colspan="8" style="text-align:center;color:var(--text-muted)">Memuat data...</td></tr></tbody>
    </table>
  </div>
  {% endif %}
</div>
{% endblock %}
{% block scripts %}
<script src="{{ url_for('static', filename='js/sahabat_etf.js') }}"></script>
{% if not wrong_company %}
<script>document.addEventListener("DOMContentLoaded", initSahabatEtf);</script>
{% endif %}
{% endblock %}
```

- [ ] **Step 4: Buat file `static/js/sahabat_etf.js` kosong (placeholder) supaya `url_for` tidak error**

```javascript
// static/js/sahabat_etf.js
// Diisi Task 8.
function initSahabatEtf() {}
```

- [ ] **Step 5: Jalankan test, pastikan PASS**

Run: `pytest tests/test_sahabat_etf_routes.py -v`
Expected: 11 passed

- [ ] **Step 6: Commit**

```bash
git add templates/sahabat_etf/index.html static/js/sahabat_etf.js tests/test_sahabat_etf_routes.py
git commit -m "feat: build Sahabat ETF dashboard markup (cards, chart, table)"
```

---

### Task 8: Frontend JS — fetch data, render chart/table/alert, verifikasi manual di browser

**Files:**
- Modify: `static/js/sahabat_etf.js`

**Interfaces:**
- Consumes: `GET /beasiswa/sahabat/api/summary`, `GET /beasiswa/sahabat/api/breakdown` (Task 5);
  global helper `fmtRupiah(n)` dan `showToast(msg, type)` dari `static/js/app.js` (sudah dimuat
  global lewat `base.html`); global `Chart` dari CDN Chart.js (sudah di-include Task 1 Step 3).
- Produces: `initSahabatEtf()` — dipanggil `DOMContentLoaded` (sudah di-wire Task 7).

- [ ] **Step 1: Tulis `static/js/sahabat_etf.js` lengkap**

```javascript
// static/js/sahabat_etf.js
let setfCharts = {};

function setfRenderBarChart(canvasId, labels, datasets) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  if (setfCharts[canvasId]) setfCharts[canvasId].destroy();
  setfCharts[canvasId] = new Chart(ctx, {
    type: "bar",
    data: { labels: labels, datasets: datasets },
    options: {
      responsive: true,
      plugins: { legend: { labels: { color: "#e2e8f0" } } },
      scales: {
        x: { ticks: { color: "#94a3b8" }, grid: { color: "rgba(148,163,184,0.1)" } },
        y: { ticks: { color: "#94a3b8" }, grid: { color: "rgba(148,163,184,0.1)" } },
      },
    },
  });
}

function setfRenderDoughnutChart(canvasId, labels, values, colors) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  if (setfCharts[canvasId]) setfCharts[canvasId].destroy();
  setfCharts[canvasId] = new Chart(ctx, {
    type: "doughnut",
    data: { labels: labels, datasets: [{ data: values, backgroundColor: colors }] },
    options: { responsive: true, plugins: { legend: { labels: { color: "#e2e8f0" } } } },
  });
}

function setfRenderSummaryCards(rows) {
  const totalSiswa = rows.filter(function (r) { return r.status === "Aktif"; }).length;
  const totalBudget = rows.reduce(function (s, r) { return s + r.budget_total; }, 0);
  const totalPayment = rows.reduce(function (s, r) { return s + r.payment_total; }, 0);
  const totalRealisasi = rows.reduce(function (s, r) { return s + r.realisasi_total; }, 0);
  const totalSisa = rows.reduce(function (s, r) { return s + r.sisa_budget; }, 0);
  const cards = [
    ["Total Siswa Aktif", totalSiswa],
    ["Total Budget", fmtRupiah(totalBudget)],
    ["Total Payment", fmtRupiah(totalPayment)],
    ["Total Realisasi", fmtRupiah(totalRealisasi)],
    ["Sisa Budget", fmtRupiah(totalSisa)],
  ];
  document.getElementById("setf-summary").innerHTML = cards.map(function (c) {
    return '<div class="budget-stat-card"><div class="label">' + c[0] +
      '</div><div class="value">' + c[1] + "</div></div>";
  }).join("");
}

function setfRenderTable(rows) {
  const tbody = document.querySelector("#setf-table tbody");
  if (!rows.length) {
    tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;color:var(--text-muted)">Belum ada siswa Sahabat ETF.</td></tr>';
    return;
  }
  tbody.innerHTML = rows.map(function (r) {
    return "<tr>" +
      "<td>" + r.nama + "</td>" +
      "<td>" + r.jenjang + "</td>" +
      "<td>" + r.angkatan + "</td>" +
      "<td>" + r.status + "</td>" +
      "<td>" + fmtRupiah(r.budget_total) + "</td>" +
      "<td>" + fmtRupiah(r.payment_total) + "</td>" +
      "<td>" + fmtRupiah(r.realisasi_total) + "</td>" +
      "<td>" + fmtRupiah(r.sisa_budget) + "</td>" +
      "</tr>";
  }).join("");
}

function setfRenderAlert(overBudget) {
  const card = document.getElementById("setf-alert-card");
  const list = document.getElementById("setf-alert-list");
  if (!overBudget.length) {
    card.style.display = "none";
    return;
  }
  card.style.display = "block";
  list.innerHTML = overBudget.map(function (o) {
    return "<li>" + o.nama + " — realisasi melebihi budget sebesar " + fmtRupiah(o.selisih) + "</li>";
  }).join("");
}

function initSahabatEtf() {
  fetch("/beasiswa/sahabat/api/summary")
    .then(function (r) { return r.json(); })
    .then(function (data) {
      const rows = data.rows;
      setfRenderSummaryCards(rows);
      setfRenderTable(rows);
      setfRenderBarChart("chart-siswa", rows.map(function (r) { return r.nama; }), [
        { label: "Budget", data: rows.map(function (r) { return r.budget_total; }), backgroundColor: "#6366f1" },
        { label: "Realisasi", data: rows.map(function (r) { return r.realisasi_total; }), backgroundColor: "#818cf8" },
      ]);
    })
    .catch(function () { showToast("Gagal memuat ringkasan siswa.", "error"); });

  fetch("/beasiswa/sahabat/api/breakdown")
    .then(function (r) { return r.json(); })
    .then(function (data) {
      setfRenderDoughnutChart("chart-kategori",
        data.kategori.map(function (k) { return k.cat1; }),
        data.kategori.map(function (k) { return k.realisasi; }),
        ["#6366f1", "#818cf8", "#f97316", "#06b6d4", "#10b981", "#f59e0b"]);
      setfRenderAlert(data.over_budget);
    })
    .catch(function () { showToast("Gagal memuat breakdown kategori.", "error"); });
}
```

- [ ] **Step 2: Jalankan full test suite modul (regression check JS tidak menyentuh Python, tapi pastikan tidak ada yang rusak)**

Run: `pytest tests/test_sahabat_etf_routes.py tests/test_sahabat_etf_service.py -v`
Expected: 21 passed (11 di `test_sahabat_etf_routes.py` + 10 di `test_sahabat_etf_service.py`)

- [ ] **Step 3: Verifikasi manual di browser**

```bash
python app.py
```

Buka `http://localhost:5000` (atau port sesuai `config.py`), login, pilih company **Eka Tjipta Foundation (ETF)**,
buka `/beasiswa/`, klik link **"Sahabat ETF ↗"** di toolbar tab, cek:
- 5 summary card terisi angka (bukan `NaN`/kosong)
- Tabel berisi 11 baris siswa (data live `finance_hub.db`)
- Chart bar "Budget vs Realisasi per Siswa" tampil dengan 11 bar
- Chart donut "Realisasi per Kategori" tampil
- Card "Siswa Over-Budget" — cek apakah ada yang over-budget di data live, kalau tidak ada card harus hidden
- Klik tombol "Export Ringkasan (CSV)" dan "Export Detail Transaksi (CSV)" — file ke-download, buka di Excel, cek isinya masuk akal
- Pilih company **Sinar Mas Tjipta (SMT)**, buka lagi `/beasiswa/sahabat` — harus tampil notice "Ganti Company", bukan dashboard kosong/error

- [ ] **Step 4: Commit**

```bash
git add static/js/sahabat_etf.js
git commit -m "feat: render Sahabat ETF dashboard charts, table, and over-budget alert"
```

---

### Task 9: Regression check — full test suite

**Files:** (tidak ada file baru — verifikasi saja)

- [ ] **Step 1: Jalankan seluruh test suite project supaya tidak ada modul lain yang keregresi (mis. import path atau blueprint clash)**

Run: `pytest tests/ -v`
Expected: semua test PASS (baseline sebelumnya 221 passed / 1 pre-existing fail
`test_get_next_pam_no_sml_uses_sml_prefix` — TIDAK terkait modul ini, jangan dianggap regresi baru;
kalau ada test lain yang gagal, itu regresi nyata dari perubahan `app.py`/`templates/beasiswa/index.html`
di Task 1 dan harus diperbaiki sebelum lanjut)

- [ ] **Step 2: Kalau semua hijau (selain 1 pre-existing fail di atas), tidak perlu commit tambahan — plan selesai**

---

## Ringkasan File Baru/Modifikasi

| File | Aksi |
|---|---|
| `modules/sahabat_etf/__init__.py` | Baru |
| `modules/sahabat_etf/routes.py` | Baru |
| `modules/sahabat_etf/service.py` | Baru |
| `templates/sahabat_etf/index.html` | Baru |
| `static/js/sahabat_etf.js` | Baru |
| `app.py` | Modify (register blueprint) |
| `templates/beasiswa/index.html` | Modify (1 link masuk) |
| `tests/test_sahabat_etf_routes.py` | Baru |
| `tests/test_sahabat_etf_service.py` | Baru |
