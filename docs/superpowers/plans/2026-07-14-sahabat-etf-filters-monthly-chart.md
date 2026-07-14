# Sahabat ETF — Filter Tahun/Pillar & Chart Bulanan — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tambah filter tahun (multi-select) dan pillar (single-select) ke dashboard `/beasiswa/sahabat`, plus chart bar bulanan (budget vs realisasi per bulan) menggantikan chart per-siswa yang sekarang, ditambah tabel perbandingan realisasi per-bulan-per-tahun untuk kasus multi-tahun.

**Architecture:** Extend service functions (`modules/sahabat_etf/service.py`) yang sudah ada dengan parameter opsional `years`/`pillar` (backward-compatible — tanpa parameter = behavior lama, 26 test existing tetap hijau), tambah 3 fungsi baru (`get_available_years`, `get_available_pillars`, `get_monthly_breakdown`). API/export routes terima query param `?years=2025,2026&pillar=SETF`. Frontend: filter bar baru (checkbox tahun + dropdown pillar) yang auto-apply `onchange`, re-fetch semua data via 1 fungsi terpusat.

**Tech Stack:** Python 3.14, Flask, SQLite, pytest, vanilla JS + Jinja2, Chart.js 4.4.4 (sudah dipakai modul ini).

## Global Constraints

- Working directory semua command shell di plan ini: `C:\Financehub\app` (jalankan `pytest` dari situ).
- Filter tahun diterapkan **independen per tabel sumber**: baris `budget_beasiswa` difilter dari `budget.tanggal`-nya sendiri, baris `payment_beasiswa` dari `payment.tanggal`-nya sendiri — via `strftime('%Y', tanggal) IN (...)`.
- Filter pillar **HANYA memengaruhi baris `payment_beasiswa`** (`pillar = ?`). `budget_beasiswa` juga punya kolom `pillar` tapi **sengaja tidak dipakai** untuk filter di iterasi ini — budget selalu tampil apa adanya walau filter pillar aktif.
- Semua parameter baru (`years`, `pillar`) di service functions **opsional, default `None`** — tanpa argumen harus balik ke behavior lama persis, supaya 26 test existing modul ini tetap hijau tanpa perubahan.
- `get_monthly_breakdown`: `chart_year` = tahun **terbesar/terbaru** dari `years` yang dikirim. 12 bucket bulan (Jan-Des) **wajib zero-fill** — selalu ada 12 entri walau nilainya 0, tidak boleh ada bulan yang hilang dari list.
- Semua route baru/berubah tetap di balik `@jwt_html_required` + `@etf_company_required` (decorator sudah ada di `routes.py`, reuse langsung — jangan diubah).
- CSV export (`/export/summary`, `/export/detail`) **wajib ikut filter aktif** — pakai fungsi service yang sama persis dengan endpoint API, bukan logic terpisah.
- UI: checkbox tahun **multi-select**, default hanya tahun terbaru tercentang. Dropdown pillar **single-select**, default "Semua Pillar" (value kosong). Interaksi **auto-apply** `onchange`, tanpa tombol submit — konsisten dengan pola filter existing di `templates/beasiswa/index.html` (`pay-filter-pillar`, `pay-filter-tahun`, dst).
- Full spec: `docs/superpowers/specs/2026-07-14-sahabat-etf-filters-monthly-chart-design.md`.

---

### Task 1: Service — `get_available_years` & `get_available_pillars`

**Files:**
- Modify: `modules/sahabat_etf/service.py`
- Test: `tests/test_sahabat_etf_service.py`

**Interfaces:**
- Produces: `get_available_years(company_id: int) -> list[int]` (sorted ascending), `get_available_pillars(company_id: int) -> list[str]` (sorted ascending). Dipakai Task 6 (`index()` route, untuk render pilihan filter di template).

- [ ] **Step 1: Tulis test yang gagal**

Tambahkan ke `tests/test_sahabat_etf_service.py` (update baris import paling atas dulu):

Old string:
```python
from modules.sahabat_etf.service import (
    get_siswa_summary, get_kategori_breakdown, get_siswa_detail, get_all_transactions,
)
```

New string:
```python
from modules.sahabat_etf.service import (
    get_siswa_summary, get_kategori_breakdown, get_siswa_detail, get_all_transactions,
    get_available_years, get_available_pillars,
)
```

Lalu tambahkan di akhir file:

```python
def test_get_available_years_returns_sorted_distinct_years():
    _add_siswa("9990040", "Siswa Tahun")
    add_budget_batch(COMPANY_ID, "9990040", "2025-03-10", "SETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 1000000}])
    add_payment_batch(COMPANY_ID, "9990040", "2026-01-15", "SETF", "ETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 500000}])

    years = get_available_years(COMPANY_ID)
    assert years == [2025, 2026]


def test_get_available_years_excludes_other_program():
    _add_siswa("9990041", "Siswa Lain", program="SMART")
    add_budget_batch(COMPANY_ID, "9990041", "2019-01-01", "SETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 1000000}])
    years = get_available_years(COMPANY_ID)
    assert years == []


def test_get_available_pillars_returns_sorted_distinct_pillars():
    _add_siswa("9990050", "Siswa Pillar")
    add_payment_batch(COMPANY_ID, "9990050", "2026-01-15", "APP", "ETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 500000}])
    add_payment_batch(COMPANY_ID, "9990050", "2026-02-15", "SETF", "ETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 500000}])

    pillars = get_available_pillars(COMPANY_ID)
    assert pillars == ["APP", "SETF"]


def test_get_available_pillars_excludes_other_program():
    _add_siswa("9990051", "Siswa Pillar Lain Program", program="SMART")
    add_payment_batch(COMPANY_ID, "9990051", "2026-01-15", "AGRI", "ETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 500000}])
    pillars = get_available_pillars(COMPANY_ID)
    assert pillars == []
```

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `pytest tests/test_sahabat_etf_service.py -k "available_years or available_pillars" -v`
Expected: FAIL dengan `ImportError: cannot import name 'get_available_years'`

- [ ] **Step 3: Tambahkan kedua fungsi ke `modules/sahabat_etf/service.py`**

```python
def get_available_years(company_id: int) -> list:
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT DISTINCT strftime('%Y', b.tanggal) AS y
        FROM budget_beasiswa b
        JOIN siswa s ON s.code = b.siswa_code AND s.company_id = b.company_id
        WHERE b.company_id = ? AND s.program = ? AND b.tanggal IS NOT NULL AND b.tanggal != ''
        UNION
        SELECT DISTINCT strftime('%Y', p.tanggal) AS y
        FROM payment_beasiswa p
        JOIN siswa s ON s.code = p.siswa_code AND s.company_id = p.company_id
        WHERE p.company_id = ? AND s.program = ? AND p.tanggal IS NOT NULL AND p.tanggal != ''
        """,
        (company_id, PROGRAM_NAME, company_id, PROGRAM_NAME),
    ).fetchall()
    conn.close()
    return sorted({int(r["y"]) for r in rows if r["y"]})


def get_available_pillars(company_id: int) -> list:
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT DISTINCT p.pillar
        FROM payment_beasiswa p
        JOIN siswa s ON s.code = p.siswa_code AND s.company_id = p.company_id
        WHERE p.company_id = ? AND s.program = ? AND p.pillar IS NOT NULL AND p.pillar != ''
        ORDER BY p.pillar
        """,
        (company_id, PROGRAM_NAME),
    ).fetchall()
    conn.close()
    return [r["pillar"] for r in rows]
```

- [ ] **Step 4: Jalankan test, pastikan PASS**

Run: `pytest tests/test_sahabat_etf_service.py -v`
Expected: 14 passed (10 lama + 4 baru)

- [ ] **Step 5: Commit**

```bash
git add modules/sahabat_etf/service.py tests/test_sahabat_etf_service.py
git commit -m "feat: add get_available_years and get_available_pillars for Sahabat ETF filters"
```

---

### Task 2: Service — extend `get_siswa_summary` dengan filter `years`/`pillar`

**Files:**
- Modify: `modules/sahabat_etf/service.py`
- Test: `tests/test_sahabat_etf_service.py`

**Interfaces:**
- Produces: helper baru `_year_filter_sql(years, column) -> tuple[str, list]` (private, dipakai ulang Task 3/4/5). `get_siswa_summary(company_id, years=None, pillar=None)` — signature berubah, semua caller lama (Task 1 modul dasar) tetap valid karena parameter baru opsional.
- Consumes: tidak ada dependency baru.

- [ ] **Step 1: Tulis test yang gagal**

Tambahkan ke `tests/test_sahabat_etf_service.py`:

```python
def test_get_siswa_summary_filters_by_year():
    _add_siswa("9990060", "Siswa Multi Tahun")
    add_budget_batch(COMPANY_ID, "9990060", "2025-01-10", "SETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 2000000}])
    add_budget_batch(COMPANY_ID, "9990060", "2026-01-10", "SETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 3000000}])
    add_payment_batch(COMPANY_ID, "9990060", "2026-01-15", "SETF", "ETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 1000000}])
    _mark_complete("9990060")

    rows = get_siswa_summary(COMPANY_ID, years=[2026])
    assert len(rows) == 1
    assert rows[0]["budget_total"] == 3000000
    assert rows[0]["realisasi_total"] == 1000000


def test_get_siswa_summary_filters_by_pillar():
    _add_siswa("9990061", "Siswa Pillar Filter")
    add_payment_batch(COMPANY_ID, "9990061", "2026-01-15", "APP", "ETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 1000000}])
    add_payment_batch(COMPANY_ID, "9990061", "2026-01-20", "SETF", "ETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 2000000}])
    _mark_complete("9990061")

    rows = get_siswa_summary(COMPANY_ID, pillar="SETF")
    assert rows[0]["realisasi_total"] == 2000000


def test_get_siswa_summary_pillar_does_not_affect_budget():
    _add_siswa("9990063", "Siswa Budget Tak Terpengaruh Pillar")
    add_budget_batch(COMPANY_ID, "9990063", "2026-01-10", "SETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 5000000}])
    add_payment_batch(COMPANY_ID, "9990063", "2026-01-15", "APP", "ETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 1000000}])
    _mark_complete("9990063")

    rows = get_siswa_summary(COMPANY_ID, pillar="SETF")
    # budget tetap 5jt (tidak ikut difilter pillar) walau tidak ada payment SETF sama sekali
    assert rows[0]["budget_total"] == 5000000
    assert rows[0]["realisasi_total"] == 0


def test_get_siswa_summary_without_filters_unchanged():
    _add_siswa("9990062", "Siswa Default")
    add_budget_batch(COMPANY_ID, "9990062", "2026-01-10", "SETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 5000000}])
    rows = get_siswa_summary(COMPANY_ID)
    assert rows[0]["budget_total"] == 5000000
```

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `pytest tests/test_sahabat_etf_service.py -k "filters_by_year or filters_by_pillar or pillar_does_not_affect_budget or without_filters_unchanged" -v`
Expected: FAIL — `TypeError: get_siswa_summary() got an unexpected keyword argument 'years'`

- [ ] **Step 3: Tambahkan helper `_year_filter_sql` dan ubah `get_siswa_summary`**

Old string (helper + fungsi lama, dari awal file sampai akhir `get_siswa_summary`):
```python
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
        budget = float(r["budget_total"] or 0)
        realisasi = float(r["realisasi_total"] or 0)
        result.append({
            "siswa_code":      r["code"],
            "nama":            r["nama"],
            "jenjang":         r["jenjang"],
            "angkatan":        r["angkatan"],
            "status":          r["status"],
            "budget_total":    budget,
            "payment_total":   float(r["payment_total"] or 0),
            "realisasi_total": realisasi,
            "sisa_budget":     budget - realisasi,
        })
    return result
```

New string:
```python
from database import get_conn

PROGRAM_NAME = "Sahabat ETF"


def _year_filter_sql(years, column):
    if not years:
        return "", []
    placeholders = ",".join("?" for _ in years)
    return f" AND strftime('%Y', {column}) IN ({placeholders})", [str(y) for y in years]


def get_siswa_summary(company_id: int, years: list = None, pillar: str = None) -> list:
    conn = get_conn()
    budget_year_sql, budget_year_params = _year_filter_sql(years, "tanggal")
    payment_year_sql, payment_year_params = _year_filter_sql(years, "tanggal")
    pillar_sql, pillar_params = (" AND pillar = ?", [pillar]) if pillar else ("", [])

    rows = conn.execute(
        f"""
        SELECT s.code, s.nama, s.jenjang, s.angkatan, s.status,
               COALESCE(b.budget_total, 0)    AS budget_total,
               COALESCE(p.payment_total, 0)   AS payment_total,
               COALESCE(p.realisasi_total, 0) AS realisasi_total
        FROM siswa s
        LEFT JOIN (
            SELECT siswa_code, SUM(amount) AS budget_total
            FROM budget_beasiswa
            WHERE company_id = ?{budget_year_sql}
            GROUP BY siswa_code
        ) b ON b.siswa_code = s.code
        LEFT JOIN (
            SELECT siswa_code,
                   SUM(amount) AS payment_total,
                   SUM(CASE WHEN status = 'complete' THEN amount ELSE 0 END) AS realisasi_total
            FROM payment_beasiswa
            WHERE company_id = ?{payment_year_sql}{pillar_sql}
            GROUP BY siswa_code
        ) p ON p.siswa_code = s.code
        WHERE s.company_id = ? AND s.program = ?
        ORDER BY s.nama
        """,
        [company_id, *budget_year_params, company_id, *payment_year_params, *pillar_params,
         company_id, PROGRAM_NAME],
    ).fetchall()
    conn.close()

    result = []
    for r in rows:
        budget = float(r["budget_total"] or 0)
        realisasi = float(r["realisasi_total"] or 0)
        result.append({
            "siswa_code":      r["code"],
            "nama":            r["nama"],
            "jenjang":         r["jenjang"],
            "angkatan":        r["angkatan"],
            "status":          r["status"],
            "budget_total":    budget,
            "payment_total":   float(r["payment_total"] or 0),
            "realisasi_total": realisasi,
            "sisa_budget":     budget - realisasi,
        })
    return result
```

- [ ] **Step 4: Jalankan test, pastikan PASS**

Run: `pytest tests/test_sahabat_etf_service.py -v`
Expected: 18 passed (14 dari Task 1 + 4 baru)

- [ ] **Step 5: Commit**

```bash
git add modules/sahabat_etf/service.py tests/test_sahabat_etf_service.py
git commit -m "feat: add years/pillar filter to get_siswa_summary"
```

---

### Task 3: Service — extend `get_kategori_breakdown` dengan filter `years`/`pillar`

**Files:**
- Modify: `modules/sahabat_etf/service.py`
- Test: `tests/test_sahabat_etf_service.py`

**Interfaces:**
- Consumes: `_year_filter_sql` (Task 2), `get_siswa_summary(company_id, years, pillar)` (Task 2, dipanggil ulang untuk `over_budget` — supaya alert ikut filter yang sama).
- Produces: `get_kategori_breakdown(company_id, years=None, pillar=None)` — signature berubah, backward-compatible.

- [ ] **Step 1: Tulis test yang gagal**

Tambahkan ke `tests/test_sahabat_etf_service.py`:

```python
def test_get_kategori_breakdown_filters_by_year():
    _add_siswa("9990070", "Siswa Kategori Tahun")
    add_budget_batch(COMPANY_ID, "9990070", "2025-01-10", "SETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 1000000}])
    add_budget_batch(COMPANY_ID, "9990070", "2026-01-10", "SETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 2000000}])

    result = get_kategori_breakdown(COMPANY_ID, years=[2026])
    by_cat = {k["cat1"]: k for k in result["kategori"]}
    assert by_cat["By Pendidikan"]["budget"] == 2000000


def test_get_kategori_breakdown_filters_by_pillar():
    _add_siswa("9990071", "Siswa Kategori Pillar")
    add_payment_batch(COMPANY_ID, "9990071", "2026-01-15", "APP", "ETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 1000000}])
    add_payment_batch(COMPANY_ID, "9990071", "2026-01-20", "SETF", "ETF",
        [{"cat1": "By Tunjangan", "cat2": "Semester 1", "amount": 500000}])
    _mark_complete("9990071")

    result = get_kategori_breakdown(COMPANY_ID, pillar="SETF")
    by_cat = {k["cat1"]: k for k in result["kategori"]}
    assert "By Tunjangan" in by_cat
    assert "By Pendidikan" not in by_cat


def test_get_kategori_breakdown_over_budget_respects_filters():
    _add_siswa("9990072", "Siswa Over Filtered")
    add_budget_batch(COMPANY_ID, "9990072", "2026-01-10", "SETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 1000000}])
    add_payment_batch(COMPANY_ID, "9990072", "2025-01-15", "SETF", "ETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 5000000}])
    _mark_complete("9990072")

    # Tanpa filter: realisasi (5jt, tahun 2025) > budget (1jt, tahun 2026) -> over budget
    result_all = get_kategori_breakdown(COMPANY_ID)
    assert len(result_all["over_budget"]) == 1

    # Filter tahun 2026 saja: realisasi 2025 tidak ikut terhitung -> tidak over budget
    result_2026 = get_kategori_breakdown(COMPANY_ID, years=[2026])
    assert result_2026["over_budget"] == []
```

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `pytest tests/test_sahabat_etf_service.py -k "kategori_breakdown_filters or over_budget_respects" -v`
Expected: FAIL — `TypeError: get_kategori_breakdown() got an unexpected keyword argument 'years'`

- [ ] **Step 3: Ubah `get_kategori_breakdown` di `modules/sahabat_etf/service.py`**

Old string:
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
        kategori.setdefault(cat1, {"cat1": cat1, "budget": 0.0, "payment": 0.0, "realisasi": 0.0})
        kategori[cat1]["budget"] += float(r["total"] or 0)
    for r in payment_rows:
        cat1 = r["cat1"] or "(Tanpa Kategori)"
        kategori.setdefault(cat1, {"cat1": cat1, "budget": 0.0, "payment": 0.0, "realisasi": 0.0})
        kategori[cat1]["payment"] += float(r["total"] or 0)
        kategori[cat1]["realisasi"] += float(r["realisasi"] or 0)

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

New string:
```python
def get_kategori_breakdown(company_id: int, years: list = None, pillar: str = None) -> dict:
    conn = get_conn()
    budget_year_sql, budget_year_params = _year_filter_sql(years, "b.tanggal")
    payment_year_sql, payment_year_params = _year_filter_sql(years, "p.tanggal")
    pillar_sql, pillar_params = (" AND p.pillar = ?", [pillar]) if pillar else ("", [])

    budget_rows = conn.execute(
        f"""
        SELECT b.cat1, SUM(b.amount) AS total
        FROM budget_beasiswa b
        JOIN siswa s ON s.code = b.siswa_code AND s.company_id = b.company_id
        WHERE b.company_id = ? AND s.program = ?{budget_year_sql}
        GROUP BY b.cat1
        """,
        [company_id, PROGRAM_NAME, *budget_year_params],
    ).fetchall()
    payment_rows = conn.execute(
        f"""
        SELECT p.cat1,
               SUM(p.amount) AS total,
               SUM(CASE WHEN p.status = 'complete' THEN p.amount ELSE 0 END) AS realisasi
        FROM payment_beasiswa p
        JOIN siswa s ON s.code = p.siswa_code AND s.company_id = p.company_id
        WHERE p.company_id = ? AND s.program = ?{payment_year_sql}{pillar_sql}
        GROUP BY p.cat1
        """,
        [company_id, PROGRAM_NAME, *payment_year_params, *pillar_params],
    ).fetchall()
    conn.close()

    kategori = {}
    for r in budget_rows:
        cat1 = r["cat1"] or "(Tanpa Kategori)"
        kategori.setdefault(cat1, {"cat1": cat1, "budget": 0.0, "payment": 0.0, "realisasi": 0.0})
        kategori[cat1]["budget"] += float(r["total"] or 0)
    for r in payment_rows:
        cat1 = r["cat1"] or "(Tanpa Kategori)"
        kategori.setdefault(cat1, {"cat1": cat1, "budget": 0.0, "payment": 0.0, "realisasi": 0.0})
        kategori[cat1]["payment"] += float(r["total"] or 0)
        kategori[cat1]["realisasi"] += float(r["realisasi"] or 0)

    over_budget = [
        {
            "siswa_code":      s["siswa_code"],
            "nama":            s["nama"],
            "budget_total":    s["budget_total"],
            "realisasi_total": s["realisasi_total"],
            "selisih":         s["realisasi_total"] - s["budget_total"],
        }
        for s in get_siswa_summary(company_id, years, pillar)
        if s["realisasi_total"] > s["budget_total"]
    ]

    return {"kategori": list(kategori.values()), "over_budget": over_budget}
```

- [ ] **Step 4: Jalankan test, pastikan PASS**

Run: `pytest tests/test_sahabat_etf_service.py -v`
Expected: 21 passed (18 dari Task 2 + 3 baru)

- [ ] **Step 5: Commit**

```bash
git add modules/sahabat_etf/service.py tests/test_sahabat_etf_service.py
git commit -m "feat: add years/pillar filter to get_kategori_breakdown, alert respects filters"
```

---

### Task 4: Service — extend `get_all_transactions` dengan filter `years`/`pillar`

**Files:**
- Modify: `modules/sahabat_etf/service.py`
- Test: `tests/test_sahabat_etf_service.py`

**Interfaces:**
- Consumes: `_year_filter_sql` (Task 2).
- Produces: `get_all_transactions(company_id, years=None, pillar=None)` — dipakai Task 7 (export/detail route).

- [ ] **Step 1: Tulis test yang gagal**

```python
def test_get_all_transactions_filters_by_year_and_pillar():
    _add_siswa("9990080", "Siswa Export Filter")
    add_budget_batch(COMPANY_ID, "9990080", "2025-01-10", "SETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 1000000}])
    add_budget_batch(COMPANY_ID, "9990080", "2026-01-10", "SETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 2000000}])
    add_payment_batch(COMPANY_ID, "9990080", "2026-01-15", "APP", "ETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 500000}])
    add_payment_batch(COMPANY_ID, "9990080", "2026-01-20", "SETF", "ETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 700000}])

    rows = get_all_transactions(COMPANY_ID, years=[2026], pillar="SETF")
    assert len(rows) == 2  # 1 budget baris 2026 (pillar tidak memfilter budget) + 1 payment pillar SETF 2026
    sumbers = {(r["sumber"], r["amount"]) for r in rows}
    assert ("Budget", 2000000) in sumbers
    assert ("Payment", 700000) in sumbers
```

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `pytest tests/test_sahabat_etf_service.py -k filters_by_year_and_pillar -v`
Expected: FAIL — `TypeError: get_all_transactions() got an unexpected keyword argument 'years'`

- [ ] **Step 3: Ubah `get_all_transactions` di `modules/sahabat_etf/service.py`**

Old string:
```python
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

New string:
```python
def get_all_transactions(company_id: int, years: list = None, pillar: str = None) -> list:
    conn = get_conn()
    budget_year_sql, budget_year_params = _year_filter_sql(years, "b.tanggal")
    payment_year_sql, payment_year_params = _year_filter_sql(years, "p.tanggal")
    pillar_sql, pillar_params = (" AND p.pillar = ?", [pillar]) if pillar else ("", [])

    budget_rows = conn.execute(
        f"""
        SELECT s.code AS siswa_code, s.nama, b.tanggal, b.cat1, b.cat2, b.amount
        FROM budget_beasiswa b
        JOIN siswa s ON s.code = b.siswa_code AND s.company_id = b.company_id
        WHERE b.company_id = ? AND s.program = ?{budget_year_sql}
        ORDER BY s.nama, b.tanggal
        """,
        [company_id, PROGRAM_NAME, *budget_year_params],
    ).fetchall()
    payment_rows = conn.execute(
        f"""
        SELECT s.code AS siswa_code, s.nama, p.tanggal, p.cat1, p.cat2, p.amount, p.status
        FROM payment_beasiswa p
        JOIN siswa s ON s.code = p.siswa_code AND s.company_id = p.company_id
        WHERE p.company_id = ? AND s.program = ?{payment_year_sql}{pillar_sql}
        ORDER BY s.nama, p.tanggal
        """,
        [company_id, PROGRAM_NAME, *payment_year_params, *pillar_params],
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
Expected: 22 passed

- [ ] **Step 5: Commit**

```bash
git add modules/sahabat_etf/service.py tests/test_sahabat_etf_service.py
git commit -m "feat: add years/pillar filter to get_all_transactions"
```

---

### Task 5: Service — fungsi baru `get_monthly_breakdown`

**Files:**
- Modify: `modules/sahabat_etf/service.py`
- Test: `tests/test_sahabat_etf_service.py`

**Interfaces:**
- Produces: `get_monthly_breakdown(company_id: int, years: list = None, pillar: str = None) -> dict` dengan shape:
  `{"chart_year": int|None, "months": [{"bulan": 1..12, "budget": float, "realisasi": float}, ...] (selalu 12 entri), "comparison": [{"bulan": 1..12, "per_tahun": {"2025": float, "2026": float, ...}}, ...] (selalu 12 entri)}`.
  Dipakai Task 6 (route `/api/monthly`).

- [ ] **Step 1: Tulis test yang gagal**

```python
def test_get_monthly_breakdown_zero_fills_all_12_months():
    _add_siswa("9990090", "Siswa Bulanan")
    add_budget_batch(COMPANY_ID, "9990090", "2026-03-10", "SETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 1000000}])

    result = get_monthly_breakdown(COMPANY_ID, years=[2026])
    assert len(result["months"]) == 12
    assert result["months"][2]["bulan"] == 3
    assert result["months"][2]["budget"] == 1000000
    assert result["months"][0]["budget"] == 0.0  # Januari, tidak ada data


def test_get_monthly_breakdown_uses_latest_year_for_chart():
    _add_siswa("9990091", "Siswa Multi Tahun Bulanan")
    add_budget_batch(COMPANY_ID, "9990091", "2025-05-10", "SETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 9999999}])
    add_budget_batch(COMPANY_ID, "9990091", "2026-05-10", "SETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 1500000}])

    result = get_monthly_breakdown(COMPANY_ID, years=[2025, 2026])
    assert result["chart_year"] == 2026
    assert result["months"][4]["budget"] == 1500000  # Mei tahun 2026, bukan 2025


def test_get_monthly_breakdown_comparison_covers_all_selected_years():
    _add_siswa("9990092", "Siswa Banding Tahun")
    add_payment_batch(COMPANY_ID, "9990092", "2025-06-10", "SETF", "ETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 700000}])
    add_payment_batch(COMPANY_ID, "9990092", "2026-06-10", "SETF", "ETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 900000}])
    _mark_complete("9990092")

    result = get_monthly_breakdown(COMPANY_ID, years=[2025, 2026])
    juni = result["comparison"][5]
    assert juni["bulan"] == 6
    assert juni["per_tahun"]["2025"] == 700000
    assert juni["per_tahun"]["2026"] == 900000


def test_get_monthly_breakdown_filters_by_pillar():
    _add_siswa("9990093", "Siswa Bulanan Pillar")
    add_payment_batch(COMPANY_ID, "9990093", "2026-07-10", "APP", "ETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 400000}])
    add_payment_batch(COMPANY_ID, "9990093", "2026-07-15", "SETF", "ETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 600000}])
    _mark_complete("9990093")

    result = get_monthly_breakdown(COMPANY_ID, years=[2026], pillar="SETF")
    juli = result["months"][6]
    assert juli["realisasi"] == 600000


def test_get_monthly_breakdown_empty_years_returns_empty_structure():
    result = get_monthly_breakdown(COMPANY_ID, years=[])
    assert result == {"chart_year": None, "months": [], "comparison": []}
```

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `pytest tests/test_sahabat_etf_service.py -k monthly_breakdown -v`
Expected: FAIL — `ImportError: cannot import name 'get_monthly_breakdown'`

- [ ] **Step 3: Update baris import di top file test, lalu tambahkan fungsi ke `modules/sahabat_etf/service.py`**

Update baris import di `tests/test_sahabat_etf_service.py`:

Old string:
```python
from modules.sahabat_etf.service import (
    get_siswa_summary, get_kategori_breakdown, get_siswa_detail, get_all_transactions,
    get_available_years, get_available_pillars,
)
```

New string:
```python
from modules.sahabat_etf.service import (
    get_siswa_summary, get_kategori_breakdown, get_siswa_detail, get_all_transactions,
    get_available_years, get_available_pillars, get_monthly_breakdown,
)
```

Tambahkan di akhir `modules/sahabat_etf/service.py`:

```python
def get_monthly_breakdown(company_id: int, years: list = None, pillar: str = None) -> dict:
    if not years:
        return {"chart_year": None, "months": [], "comparison": []}

    chart_year = max(years)
    conn = get_conn()

    budget_rows = conn.execute(
        """
        SELECT CAST(strftime('%m', b.tanggal) AS INTEGER) AS bulan, SUM(b.amount) AS total
        FROM budget_beasiswa b
        JOIN siswa s ON s.code = b.siswa_code AND s.company_id = b.company_id
        WHERE b.company_id = ? AND s.program = ? AND strftime('%Y', b.tanggal) = ?
        GROUP BY bulan
        """,
        (company_id, PROGRAM_NAME, str(chart_year)),
    ).fetchall()

    pillar_sql, pillar_params = (" AND p.pillar = ?", [pillar]) if pillar else ("", [])
    year_placeholders = ",".join("?" for _ in years)
    realisasi_rows = conn.execute(
        f"""
        SELECT strftime('%Y', p.tanggal) AS tahun, CAST(strftime('%m', p.tanggal) AS INTEGER) AS bulan,
               SUM(p.amount) AS total
        FROM payment_beasiswa p
        JOIN siswa s ON s.code = p.siswa_code AND s.company_id = p.company_id
        WHERE p.company_id = ? AND s.program = ? AND p.status = 'complete'
              AND strftime('%Y', p.tanggal) IN ({year_placeholders}){pillar_sql}
        GROUP BY tahun, bulan
        """,
        [company_id, PROGRAM_NAME, *[str(y) for y in years], *pillar_params],
    ).fetchall()
    conn.close()

    budget_by_month = {r["bulan"]: float(r["total"] or 0) for r in budget_rows}
    realisasi_by_year_month = {}
    for r in realisasi_rows:
        realisasi_by_year_month.setdefault(r["tahun"], {})[r["bulan"]] = float(r["total"] or 0)

    months = [
        {
            "bulan": m,
            "budget": budget_by_month.get(m, 0.0),
            "realisasi": realisasi_by_year_month.get(str(chart_year), {}).get(m, 0.0),
        }
        for m in range(1, 13)
    ]
    comparison = [
        {
            "bulan": m,
            "per_tahun": {str(y): realisasi_by_year_month.get(str(y), {}).get(m, 0.0) for y in years},
        }
        for m in range(1, 13)
    ]
    return {"chart_year": chart_year, "months": months, "comparison": comparison}
```

- [ ] **Step 4: Jalankan test, pastikan PASS**

Run: `pytest tests/test_sahabat_etf_service.py -v`
Expected: 27 passed

- [ ] **Step 5: Commit**

```bash
git add modules/sahabat_etf/service.py tests/test_sahabat_etf_service.py
git commit -m "feat: add get_monthly_breakdown with zero-fill and multi-year comparison"
```

---

### Task 6: Routes — `_parse_filters`, wire `years`/`pillar` ke `/api/summary`+`/api/breakdown`, route baru `/api/monthly`, `index()` kirim opsi filter

**Files:**
- Modify: `modules/sahabat_etf/routes.py`
- Test: `tests/test_sahabat_etf_routes.py`

**Interfaces:**
- Consumes: `get_available_years`, `get_available_pillars` (Task 1), `get_siswa_summary`, `get_kategori_breakdown` (Task 2/3, sudah terima `years`/`pillar`), `get_monthly_breakdown` (Task 5).
- Produces: helper `_parse_filters() -> tuple[list|None, str|None]` (dipakai ulang Task 7). Context var `available_years`, `available_pillars` di `index()` — dipakai Task 8 (template).

- [ ] **Step 1: Tulis test yang gagal**

Tambahkan ke `tests/test_sahabat_etf_routes.py`:

> **Catatan:** test untuk elemen `setf-year-cb` di HTML **belum** ditulis di sini — markup-nya baru ada di Task 8 (template). Menulisnya sekarang akan gagal terus sampai Task 8 selesai, bukan RED->GREEN yang valid untuk task ini. Test itu ditambahkan di Task 8, bersamaan dengan perubahan template-nya.

```python
def test_api_summary_respects_years_query_param(client):
    login(client)
    _select_etf(client)
    client.post("/beasiswa/siswa/tambah", json={
        "code": "9992001", "nama": "Siswa Filter Tahun", "jenjang": "S1", "angkatan": 2024,
        "program": "Sahabat ETF", "fakultas": "", "universitas": "", "bank": "",
        "norek": "", "namarek": "", "referensi": "", "status": "Aktif", "catatan": "",
    })
    client.post("/beasiswa/budget/tambah", json={"code": "9992001", "tanggal": "2025-01-10",
        "pillar": "SETF", "items": [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 1000000}]})
    client.post("/beasiswa/budget/tambah", json={"code": "9992001", "tanggal": "2026-01-10",
        "pillar": "SETF", "items": [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 2000000}]})

    resp = client.get("/beasiswa/sahabat/api/summary?years=2026")
    data = resp.get_json()
    assert data["rows"][0]["budget_total"] == 2000000


def test_api_breakdown_respects_pillar_query_param(client):
    login(client)
    _select_etf(client)
    client.post("/beasiswa/siswa/tambah", json={
        "code": "9992002", "nama": "Siswa Breakdown Pillar", "jenjang": "S1", "angkatan": 2024,
        "program": "Sahabat ETF", "fakultas": "", "universitas": "", "bank": "",
        "norek": "", "namarek": "", "referensi": "", "status": "Aktif", "catatan": "",
    })
    client.post("/beasiswa/payment/tambah", json={"code": "9992002", "tanggal": "2026-01-15",
        "pillar": "SETF", "perusahaan": "ETF",
        "items": [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 500000}]})

    resp = client.get("/beasiswa/sahabat/api/breakdown?pillar=APP")
    data = resp.get_json()
    assert data["kategori"] == []


def test_api_monthly_requires_years_param(client):
    login(client)
    _select_etf(client)
    resp = client.get("/beasiswa/sahabat/api/monthly")
    assert resp.status_code == 400


def test_api_monthly_returns_chart_year_and_months(client):
    login(client)
    _select_etf(client)
    client.post("/beasiswa/siswa/tambah", json={
        "code": "9992003", "nama": "Siswa Bulanan Route", "jenjang": "S1", "angkatan": 2024,
        "program": "Sahabat ETF", "fakultas": "", "universitas": "", "bank": "",
        "norek": "", "namarek": "", "referensi": "", "status": "Aktif", "catatan": "",
    })
    client.post("/beasiswa/budget/tambah", json={"code": "9992003", "tanggal": "2026-04-10",
        "pillar": "SETF", "items": [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 800000}]})

    resp = client.get("/beasiswa/sahabat/api/monthly?years=2026")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["chart_year"] == 2026
    assert len(data["months"]) == 12


def test_api_monthly_returns_403_for_non_etf_company(client):
    login(client)
    _select_smt(client)
    resp = client.get("/beasiswa/sahabat/api/monthly?years=2026")
    assert resp.status_code == 403
```

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `pytest tests/test_sahabat_etf_routes.py -k "respects_years or respects_pillar or api_monthly" -v`
Expected: FAIL — `TypeError: get_kategori_breakdown() takes 1 to 3 positional arguments but ...` untuk test filter (route belum parse query param), route `/api/monthly` 404 untuk test monthly

- [ ] **Step 3: Update `modules/sahabat_etf/routes.py`**

Update baris import:

Old string:
```python
from functools import wraps
from flask import Blueprint, render_template, session, jsonify
from flask_jwt_extended import get_jwt
from auth.middleware import jwt_html_required
from modules.sahabat_etf.service import (
    get_siswa_summary, get_kategori_breakdown, get_siswa_detail, get_all_transactions,
)
```

New string:
```python
from functools import wraps
from flask import Blueprint, render_template, session, jsonify, request
from flask_jwt_extended import get_jwt
from auth.middleware import jwt_html_required
from modules.sahabat_etf.service import (
    get_siswa_summary, get_kategori_breakdown, get_siswa_detail, get_all_transactions,
    get_available_years, get_available_pillars, get_monthly_breakdown,
)
```

Tambahkan helper `_parse_filters` setelah `_cid()`:

Old string:
```python
def _cid():
    return session.get("company_id")


def etf_company_required(f):
```

New string:
```python
def _cid():
    return session.get("company_id")


def _parse_filters():
    years_param = request.args.get("years", "")
    years = [int(y) for y in years_param.split(",") if y.strip().isdigit()] if years_param else None
    pillar = request.args.get("pillar") or None
    return years, pillar


def etf_company_required(f):
```

Ubah `index()`:

Old string:
```python
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

New string:
```python
@bp.route("/")
@jwt_html_required
def index():
    cid = _cid()
    return render_template(
        "sahabat_etf/index.html",
        active_page="sahabat_etf",
        wrong_company=(session.get("company_code") != "ETF"),
        available_years=get_available_years(cid),
        available_pillars=get_available_pillars(cid),
        **_ctx(),
    )
```

Ubah `api_summary()` dan `api_breakdown()`, lalu tambahkan `api_monthly()`:

Old string:
```python
@bp.route("/api/summary")
@jwt_html_required
@etf_company_required
def api_summary():
    return jsonify({"rows": get_siswa_summary(_cid())})


@bp.route("/api/breakdown")
@jwt_html_required
@etf_company_required
def api_breakdown():
    return jsonify(get_kategori_breakdown(_cid()))
```

New string:
```python
@bp.route("/api/summary")
@jwt_html_required
@etf_company_required
def api_summary():
    years, pillar = _parse_filters()
    return jsonify({"rows": get_siswa_summary(_cid(), years, pillar)})


@bp.route("/api/breakdown")
@jwt_html_required
@etf_company_required
def api_breakdown():
    years, pillar = _parse_filters()
    return jsonify(get_kategori_breakdown(_cid(), years, pillar))


@bp.route("/api/monthly")
@jwt_html_required
@etf_company_required
def api_monthly():
    years, pillar = _parse_filters()
    if not years:
        return jsonify({"ok": False, "pesan": "Parameter years wajib diisi."}), 400
    return jsonify(get_monthly_breakdown(_cid(), years, pillar))
```

- [ ] **Step 4: Jalankan test, pastikan PASS**

Run: `pytest tests/test_sahabat_etf_routes.py -v`
Expected: 21 passed (16 lama + 5 baru). Kalau kena `PermissionError` teardown flake (pre-existing, dikonfirmasi di sesi sebelumnya) — `rm -f tests/test_finance_hub.db` lalu ulangi, atau jalankan test satu-satu.

- [ ] **Step 5: Commit**

```bash
git add modules/sahabat_etf/routes.py tests/test_sahabat_etf_routes.py
git commit -m "feat: wire years/pillar filters into API routes, add /api/monthly"
```

---

### Task 7: Routes — wire `years`/`pillar` ke `/export/summary` & `/export/detail`

**Files:**
- Modify: `modules/sahabat_etf/routes.py`
- Test: `tests/test_sahabat_etf_routes.py`

**Interfaces:**
- Consumes: `_parse_filters` (Task 6), `get_siswa_summary`, `get_all_transactions` (sudah terima `years`/`pillar`).

- [ ] **Step 1: Tulis test yang gagal**

```python
def test_export_summary_respects_year_filter(client):
    login(client)
    _select_etf(client)
    client.post("/beasiswa/siswa/tambah", json={
        "code": "9992010", "nama": "Siswa Export Tahun", "jenjang": "S1", "angkatan": 2024,
        "program": "Sahabat ETF", "fakultas": "", "universitas": "", "bank": "",
        "norek": "", "namarek": "", "referensi": "", "status": "Aktif", "catatan": "",
    })
    client.post("/beasiswa/budget/tambah", json={"code": "9992010", "tanggal": "2025-01-10",
        "pillar": "SETF", "items": [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 1000000}]})
    client.post("/beasiswa/budget/tambah", json={"code": "9992010", "tanggal": "2026-01-10",
        "pillar": "SETF", "items": [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 2000000}]})

    resp = client.get("/beasiswa/sahabat/export/summary?years=2026")
    assert b"2000000.0" in resp.data
    assert b"1000000.0" not in resp.data


def test_export_detail_respects_pillar_filter(client):
    login(client)
    _select_etf(client)
    client.post("/beasiswa/siswa/tambah", json={
        "code": "9992011", "nama": "Siswa Export Pillar", "jenjang": "S1", "angkatan": 2024,
        "program": "Sahabat ETF", "fakultas": "", "universitas": "", "bank": "",
        "norek": "", "namarek": "", "referensi": "", "status": "Aktif", "catatan": "",
    })
    client.post("/beasiswa/payment/tambah", json={"code": "9992011", "tanggal": "2026-01-15",
        "pillar": "APP", "perusahaan": "ETF",
        "items": [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 400000}]})
    client.post("/beasiswa/payment/tambah", json={"code": "9992011", "tanggal": "2026-01-20",
        "pillar": "SETF", "perusahaan": "ETF",
        "items": [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 600000}]})

    resp = client.get("/beasiswa/sahabat/export/detail?pillar=SETF")
    assert b"600000.0" in resp.data
    assert b"400000.0" not in resp.data
```

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `pytest tests/test_sahabat_etf_routes.py -k "export_summary_respects or export_detail_respects" -v`
Expected: FAIL — export masih mengembalikan semua data tanpa filter

- [ ] **Step 3: Ubah `export_summary()` dan `export_detail()` di `modules/sahabat_etf/routes.py`**

Old string:
```python
@bp.route("/export/summary")
@jwt_html_required
@etf_company_required
def export_summary():
    import csv, io
    from flask import Response
    rows = get_siswa_summary(_cid())
    out = io.StringIO()
```

New string:
```python
@bp.route("/export/summary")
@jwt_html_required
@etf_company_required
def export_summary():
    import csv, io
    from flask import Response
    years, pillar = _parse_filters()
    rows = get_siswa_summary(_cid(), years, pillar)
    out = io.StringIO()
```

Old string:
```python
@bp.route("/export/detail")
@jwt_html_required
@etf_company_required
def export_detail():
    import csv, io
    from flask import Response
    rows = get_all_transactions(_cid())
    out = io.StringIO()
```

New string:
```python
@bp.route("/export/detail")
@jwt_html_required
@etf_company_required
def export_detail():
    import csv, io
    from flask import Response
    years, pillar = _parse_filters()
    rows = get_all_transactions(_cid(), years, pillar)
    out = io.StringIO()
```

- [ ] **Step 4: Jalankan test, pastikan PASS**

Run: `pytest tests/test_sahabat_etf_routes.py -v`
Expected: 23 passed

- [ ] **Step 5: Commit**

```bash
git add modules/sahabat_etf/routes.py tests/test_sahabat_etf_routes.py
git commit -m "feat: wire years/pillar filters into CSV export routes"
```

---

### Task 8: Template — filter bar, rename chart per-siswa → chart bulanan, tabel perbandingan bulanan

**Files:**
- Modify: `templates/sahabat_etf/index.html`
- Test: `tests/test_sahabat_etf_routes.py`

**Interfaces:**
- Consumes: `available_years`, `available_pillars` (Task 6, context var dari `index()`).
- Produces: DOM contract baru untuk Task 9 (JS): container `#setf-filter-tahun` isi checkbox `.setf-year-cb` (value = tahun), `#setf-filter-pillar` (select), canvas `#chart-bulanan` (rename dari `#chart-siswa`), tabel `#setf-monthly-table` dengan `<tr id="setf-monthly-thead-row">` di `<thead>` dan `<tbody>` di dalamnya, link `#setf-export-summary`/`#setf-export-detail` (id baru di toolbar export, dipakai JS untuk nempel query string filter).

- [ ] **Step 1: Update test existing yang assert `chart-siswa`, tambah test baru**

Old string di `tests/test_sahabat_etf_routes.py`:
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

New string:
```python
def test_index_contains_dashboard_elements_for_etf_company(client):
    login(client)
    _select_etf(client)
    resp = client.get("/beasiswa/sahabat/")
    assert resp.status_code == 200
    for expected in (b"setf-summary", b"chart-bulanan", b"chart-kategori",
                      b"setf-table", b"setf-alert-card", b"export/summary", b"export/detail",
                      b"setf-filter-pillar", b"setf-monthly-table"):
        assert expected in resp.data, f"missing {expected!r} in response"


def test_index_shows_year_filter_checkbox_when_data_exists(client):
    login(client)
    _select_etf(client)
    client.post("/beasiswa/siswa/tambah", json={
        "code": "9992020", "nama": "Siswa Filter UI", "jenjang": "S1", "angkatan": 2024,
        "program": "Sahabat ETF", "fakultas": "", "universitas": "", "bank": "",
        "norek": "", "namarek": "", "referensi": "", "status": "Aktif", "catatan": "",
    })
    client.post("/beasiswa/budget/tambah", json={"code": "9992020", "tanggal": "2026-01-10",
        "pillar": "SETF", "items": [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 1000000}]})

    resp = client.get("/beasiswa/sahabat/")
    assert b'class="setf-year-cb"' in resp.data
    assert b"2026" in resp.data
```

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `pytest tests/test_sahabat_etf_routes.py -k "dashboard_elements or year_filter_checkbox" -v`
Expected: FAIL — `chart-bulanan`, `setf-monthly-table`, `setf-year-cb` belum ada di template

- [ ] **Step 3: Ganti isi `{% else %}` block di `templates/sahabat_etf/index.html`**

Old string:
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
```

New string:
```html
  {% else %}
  <div class="filter-bar">
    <div class="filter-field">
      <label>Tahun</label>
      <div id="setf-filter-tahun">
        {% for y in available_years %}
        <label style="display:inline-flex;align-items:center;gap:.25rem;margin-right:.75rem;font-weight:400">
          <input type="checkbox" class="setf-year-cb" value="{{ y }}" {% if loop.last %}checked{% endif %}>
          {{ y }}
        </label>
        {% endfor %}
      </div>
    </div>
    <div class="filter-field">
      <label>Pillar</label>
      <select id="setf-filter-pillar">
        <option value="">Semua Pillar</option>
        {% for p in available_pillars %}<option value="{{ p }}">{{ p }}</option>{% endfor %}
      </select>
    </div>
  </div>

  <div class="budget-toolbar">
    <a class="budget-btn" id="setf-export-summary" href="{{ url_for('sahabat_etf.export_summary') }}">Export Ringkasan (CSV)</a>
    <a class="budget-btn" id="setf-export-detail" href="{{ url_for('sahabat_etf.export_detail') }}">Export Detail Transaksi (CSV)</a>
  </div>

  <div class="budget-summary-grid" id="setf-summary"></div>

  <div class="budget-card" id="setf-alert-card" style="display:none">
    <h3>Siswa Over-Budget</h3>
    <ul id="setf-alert-list"></ul>
  </div>

  <div class="budget-chart-grid">
    <div class="budget-chart-card"><h3>Budget vs Realisasi per Bulan</h3><canvas id="chart-bulanan"></canvas></div>
    <div class="budget-chart-card"><h3>Realisasi per Kategori</h3><canvas id="chart-kategori"></canvas></div>
  </div>

  <div class="table-wrap">
    <h3>Perbandingan Realisasi per Bulan per Tahun</h3>
    <table id="setf-monthly-table">
      <thead><tr id="setf-monthly-thead-row"><th>Bulan</th></tr></thead>
      <tbody><tr><td style="text-align:center;color:var(--text-muted)">Memuat data...</td></tr></tbody>
    </table>
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
```

- [ ] **Step 4: Jalankan test, pastikan PASS**

Run: `pytest tests/test_sahabat_etf_routes.py -v`
Expected: 24 passed (elemen baru ada, `chart-siswa` sudah tergantikan `chart-bulanan`)

- [ ] **Step 5: Commit**

```bash
git add templates/sahabat_etf/index.html tests/test_sahabat_etf_routes.py
git commit -m "feat: add filter bar and monthly comparison table markup to Sahabat ETF dashboard"
```

---

### Task 9: Frontend JS — filter state, re-fetch terpusat, chart bulanan, tabel perbandingan

**Files:**
- Modify: `static/js/sahabat_etf.js`

**Interfaces:**
- Consumes: `GET /api/summary`, `GET /api/breakdown`, `GET /api/monthly` (semua terima `?years=`/`?pillar=`, Task 6); DOM ids dari Task 8 (`.setf-year-cb`, `#setf-filter-pillar`, `#chart-bulanan`, `#setf-monthly-table` + `#setf-monthly-thead-row`, `#setf-export-summary`/`#setf-export-detail`); global `fmtRupiah`/`showToast` (sudah dipakai fungsi lama di file ini).
- Produces: `initSahabatEtf()` (tetap dipanggil `DOMContentLoaded` dari template, tidak berubah wiring-nya) memanggil `setfApplyFilters()` sebagai render pertama, lalu ulang tiap filter berubah.

- [ ] **Step 1: Tulis ulang `static/js/sahabat_etf.js` lengkap**

Old string (seluruh file):
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

New string (seluruh file):
```javascript
// static/js/sahabat_etf.js
let setfCharts = {};
const SETF_BULAN_LABEL = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"];

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

function setfRenderMonthlyChart(months) {
  setfRenderBarChart("chart-bulanan", months.map(function (m) { return SETF_BULAN_LABEL[m.bulan - 1]; }), [
    { label: "Budget", data: months.map(function (m) { return m.budget; }), backgroundColor: "#6366f1" },
    { label: "Realisasi", data: months.map(function (m) { return m.realisasi; }), backgroundColor: "#818cf8" },
  ]);
}

function setfRenderMonthlyTable(comparison, years) {
  const theadRow = document.getElementById("setf-monthly-thead-row");
  theadRow.innerHTML = "<th>Bulan</th>" + years.map(function (y) { return "<th>" + y + "</th>"; }).join("");

  const tbody = document.querySelector("#setf-monthly-table tbody");
  if (!comparison.length) {
    tbody.innerHTML = '<tr><td colspan="' + (years.length + 1) + '" style="text-align:center;color:var(--text-muted)">Pilih minimal 1 tahun.</td></tr>';
    return;
  }
  tbody.innerHTML = comparison.map(function (row) {
    const cells = years.map(function (y) { return "<td>" + fmtRupiah(row.per_tahun[y] || 0) + "</td>"; }).join("");
    return "<tr><td>" + SETF_BULAN_LABEL[row.bulan - 1] + "</td>" + cells + "</tr>";
  }).join("");
}

function setfGetSelectedFilters() {
  const years = Array.from(document.querySelectorAll(".setf-year-cb:checked")).map(function (cb) { return cb.value; });
  const pillar = document.getElementById("setf-filter-pillar").value;
  return { years: years, pillar: pillar };
}

function setfBuildQueryString(filters) {
  const params = new URLSearchParams();
  if (filters.years.length) params.set("years", filters.years.join(","));
  if (filters.pillar) params.set("pillar", filters.pillar);
  return params.toString();
}

function setfUpdateExportLinks(qs) {
  const summaryLink = document.getElementById("setf-export-summary");
  const detailLink = document.getElementById("setf-export-detail");
  const baseSummary = summaryLink.href.split("?")[0];
  const baseDetail = detailLink.href.split("?")[0];
  summaryLink.href = qs ? baseSummary + "?" + qs : baseSummary;
  detailLink.href = qs ? baseDetail + "?" + qs : baseDetail;
}

function setfApplyFilters() {
  const filters = setfGetSelectedFilters();
  const qs = setfBuildQueryString(filters);
  setfUpdateExportLinks(qs);

  fetch("/beasiswa/sahabat/api/summary" + (qs ? "?" + qs : ""))
    .then(function (r) { return r.json(); })
    .then(function (data) {
      setfRenderSummaryCards(data.rows);
      setfRenderTable(data.rows);
    })
    .catch(function () { showToast("Gagal memuat ringkasan siswa.", "error"); });

  fetch("/beasiswa/sahabat/api/breakdown" + (qs ? "?" + qs : ""))
    .then(function (r) { return r.json(); })
    .then(function (data) {
      setfRenderDoughnutChart("chart-kategori",
        data.kategori.map(function (k) { return k.cat1; }),
        data.kategori.map(function (k) { return k.realisasi; }),
        ["#6366f1", "#818cf8", "#f97316", "#06b6d4", "#10b981", "#f59e0b"]);
      setfRenderAlert(data.over_budget);
    })
    .catch(function () { showToast("Gagal memuat breakdown kategori.", "error"); });

  if (filters.years.length) {
    fetch("/beasiswa/sahabat/api/monthly?" + qs)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        setfRenderMonthlyChart(data.months);
        setfRenderMonthlyTable(data.comparison, filters.years);
      })
      .catch(function () { showToast("Gagal memuat data bulanan.", "error"); });
  } else {
    if (setfCharts["chart-bulanan"]) { setfCharts["chart-bulanan"].destroy(); delete setfCharts["chart-bulanan"]; }
    setfRenderMonthlyTable([], []);
  }
}

function initSahabatEtf() {
  document.querySelectorAll(".setf-year-cb").forEach(function (cb) {
    cb.addEventListener("change", setfApplyFilters);
  });
  const pillarSelect = document.getElementById("setf-filter-pillar");
  if (pillarSelect) pillarSelect.addEventListener("change", setfApplyFilters);
  setfApplyFilters();
}
```

- [ ] **Step 2: Jalankan full test suite modul (regression check — JS tidak menyentuh Python, tapi pastikan tidak ada yang rusak)**

Run: `pytest tests/test_sahabat_etf_routes.py tests/test_sahabat_etf_service.py -v`
Expected: 51 passed (24 routes + 27 service)

- [ ] **Step 3: Verifikasi manual di browser**

Jalankan server dev (worktree terisolasi, port bebas — lihat `.claude/launch.json` pola `financehub-*-worktree` yang sudah ada), login, pilih company **Eka Tjipta Foundation (ETF)**, buka `/beasiswa/sahabat`, cek:
- Filter bar tampil: checkbox tahun (dari data live) dengan tahun terbaru sudah tercentang default, dropdown pillar dengan opsi APP/FINANCE/SETF + "Semua Pillar"
- Chart kiri sekarang "Budget vs Realisasi per Bulan" (12 bar Jan-Des), bukan lagi per-siswa
- Centang/lepas checkbox tahun lain → semua bagian (card, 2 chart, tabel perbandingan bulanan, tabel siswa) re-fetch otomatis tanpa reload halaman
- Ganti dropdown pillar → data ikut menyempit (khususnya realisasi/kategori/tabel bulanan), budget di tabel siswa TIDAK ikut menyempit
- Centang 2+ tahun → chart bulanan tetap 1 tahun (yang termuda/terbaru dari yang dicentang), tabel perbandingan di bawahnya menampilkan kolom terpisah per tahun yang dicentang
- Lepas semua centang tahun → chart bulanan kosong/hilang, tabel bilang "Pilih minimal 1 tahun", TIDAK error di console
- Klik tombol export (kedua-duanya) saat filter aktif → file CSV yang ke-download isinya sesuai filter yang lagi aktif di layar
- Company SMT → tetap notice "Ganti Company" seperti sebelumnya (tidak berubah)

- [ ] **Step 4: Commit**

```bash
git add static/js/sahabat_etf.js
git commit -m "feat: wire filter UI to monthly chart, comparison table, and export links"
```

---

### Task 10: Regression check — full test suite

**Files:** (tidak ada file baru — verifikasi saja)

- [ ] **Step 1: Jalankan seluruh test suite project**

Run: `pytest tests/ -v`
Expected: modul Sahabat ETF (51 test) semua hijau. Environment ini punya flake pre-existing (SQLite file-lock di Windows, dikonfirmasi sesi sebelumnya reproduce di `master` yang belum disentuh) yang bikin batch run penuh gagal massal di teardown — kalau itu terjadi, jalankan test satu-satu atau per-file untuk verifikasi assertion-level, bandingkan hasil FAILED (bukan ERROR) terhadap baseline `master` sebelum branch ini untuk pastikan bukan regresi baru.

- [ ] **Step 2: Kalau semua hijau (di luar flake environment yang sudah dikonfirmasi pre-existing), tidak perlu commit tambahan — plan selesai**

---

## Ringkasan File Baru/Modifikasi

| File | Aksi |
|---|---|
| `modules/sahabat_etf/service.py` | Modify (3 fungsi extended + 3 fungsi baru) |
| `modules/sahabat_etf/routes.py` | Modify (helper baru + 2 route diubah + 1 route baru + export routes diubah) |
| `templates/sahabat_etf/index.html` | Modify (filter bar, rename chart, tabel bulanan baru) |
| `static/js/sahabat_etf.js` | Modify (rewrite penuh — filter state, re-fetch terpusat, chart+tabel bulanan) |
| `tests/test_sahabat_etf_service.py` | Modify (17 test baru) |
| `tests/test_sahabat_etf_routes.py` | Modify (8 test baru + 1 test lama diupdate) |
