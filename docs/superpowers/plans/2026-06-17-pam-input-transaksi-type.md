# PAM Input Transaksi Type Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `Transaksi` type selector to the PAM Input tab that switches between three form panels — Beasiswa (unchanged), Klaim Medis (multi-row siswa with cat3 medical items), and Others (single-entry with DPP/PPN).

**Architecture:** Three hidden HTML panels under `#tab-input-payment`, switched by `ipayOnTxChange()`. Beasiswa panel is existing code, untouched. Klaim Medis uses existing `klaim_medical` table for per-item cat3 breakdown + existing `payment_beasiswa` for per-siswa totals. Others writes only to `pam_records`.

**Tech Stack:** Flask/Python backend (SQLite via `get_conn()`), Jinja2 + vanilla JS frontend, pytest TDD with `conftest.py` clean_db fixture.

---

## File Map

| File | What changes |
|---|---|
| `app/database.py` | Add `source, pillar, mata_uang, dpp, ppn, tanggal_bayar` to `pam_records` DDL |
| `app/config.py` | Add `CAT3_MEDICAL`, `KELAS_MEDICAL`, `SPESIALISASI_MEDICAL` lists |
| `app/modules/payment_memo/service.py` | Add `get_siswa_medical()`, `save_klaim_payment()`, `save_others_payment()` |
| `app/modules/payment_memo/routes.py` | Add 3 new routes; pass new config lists to template |
| `app/templates/payment_memo/index.html` | Transaksi dropdown + panel switch; `#ipay-panel-klaim`; `#ipay-panel-others`; source filter options |
| `app/tests/test_pam_klaim.py` | New test file: `get_siswa_medical`, `save_klaim_payment`, `save_others_payment` |

---

## Task 1: Sync DDL — add missing pam_records columns

The production DB has `source`, `pillar`, `mata_uang`, `dpp`, `ppn`, `tanggal_bayar` on `pam_records` but the DDL used by `init_db()` (and thus the test DB) does not. This causes any service INSERT that uses those columns to fail in tests.

**Files:**
- Modify: `app/database.py` (pam_records DDL, line ~170)

- [ ] **Step 1: Update pam_records DDL**

In `app/database.py`, find the `CREATE TABLE IF NOT EXISTS pam_records` block and replace it with:

```sql
CREATE TABLE IF NOT EXISTS pam_records (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id      INTEGER NOT NULL REFERENCES companies(id),
    pam_no          TEXT UNIQUE NOT NULL,
    pam_date        TEXT,
    gl_account      TEXT DEFAULT '70110230',
    cost_center     TEXT,
    pt              TEXT,
    requestors_name TEXT DEFAULT 'Jany Turkanda',
    keterangan      TEXT,
    total_amount    REAL DEFAULT 0,
    due_date        TEXT,
    status          TEXT DEFAULT 'open',
    source          TEXT,
    pillar          TEXT,
    mata_uang       TEXT DEFAULT 'IDR',
    dpp             REAL DEFAULT 0,
    ppn             REAL DEFAULT 0,
    tanggal_bayar   TEXT,
    created_at      TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at      TEXT
);
```

- [ ] **Step 2: Run existing tests to verify no regression**

```bash
cd app && python -m pytest tests/ -v --tb=short 2>&1 | tail -30
```

Expected: same pass/fail count as before (the one pre-existing failure `test_get_next_pam_no_sml_uses_sml_prefix` is known — LAND prefix, not SML). All other tests pass.

- [ ] **Step 3: Commit**

```bash
git add app/database.py
git commit -m "fix: sync pam_records DDL with production schema (source, pillar, mata_uang, dpp, ppn)"
```

---

## Task 2: Config — add medical list constants

**Files:**
- Modify: `app/config.py`

- [ ] **Step 1: Add three list constants to config.py**

After the `CAT2_SEM` block in `app/config.py`, add:

```python
CAT3_MEDICAL = [
    "Alkes", "Kamar", "Konsultasi dan Visit", "Laboratorium",
    "Obat", "Radiologi", "Sewa Alat Rumah Sakit", "Tindakan Dokter",
]

KELAS_MEDICAL = ["Basic", "Deluxe", "Emergency", "Rawat Jalan", "Standard", "VIP", "VVIP", "SVIP"]

SPESIALISASI_MEDICAL = [
    "Internal Medicine", "Cardiology", "Orthopaedy", "Obstetric & Gynaecology",
    "Pediatrics", "Pulmonology", "Neurology", "Neurosurgeon", "General Surgery",
    "ENT", "Dermatovenerology", "Psychiatry", "Opthalmology", "Plastic Surgery",
    "General Practitioner", "Dentistry",
]

TRANSAKSI_TYPES = ["Beasiswa", "Klaim Medis", "Tagihan", "ETF", "Sponsor", "Others"]
```

- [ ] **Step 2: Verify import**

```bash
cd app && python -c "import config; print(config.CAT3_MEDICAL); print(config.KELAS_MEDICAL)"
```

Expected: prints both lists without error.

- [ ] **Step 3: Commit**

```bash
git add app/config.py
git commit -m "feat: add medical list constants (CAT3_MEDICAL, KELAS_MEDICAL, SPESIALISASI_MEDICAL)"
```

---

## Task 3: Service — `get_siswa_medical()`

Returns siswa that have at least one `budget_beasiswa` row with `cat1='By Medical'`. Used by autocomplete in Klaim Medis panel.

**Files:**
- Modify: `app/modules/payment_memo/service.py`
- Test: `app/tests/test_pam_klaim.py` (create new)

- [ ] **Step 1: Write failing test**

Create `app/tests/test_pam_klaim.py`:

```python
# tests/test_pam_klaim.py
import os, sys, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config
config.DB_PATH = os.path.join(os.path.dirname(__file__), "test_finance_hub.db")

from database import init_db, get_conn
from modules.payment_memo.service import get_siswa_medical

COMPANY_ID = 2

@pytest.fixture(autouse=True)
def clean_db():
    if os.path.exists(config.DB_PATH):
        os.remove(config.DB_PATH)
    init_db()
    conn = get_conn()
    conn.execute("INSERT INTO siswa (company_id,code,nama) VALUES (?,?,?)", (COMPANY_ID, "M001", "Ani Medical"))
    conn.execute("INSERT INTO siswa (company_id,code,nama) VALUES (?,?,?)", (COMPANY_ID, "M002", "Budi Edu"))
    conn.execute("INSERT INTO budget_beasiswa (company_id,siswa_code,cat1,cat2,tanggal,amount) VALUES (?,?,?,?,?,?)",
                 (COMPANY_ID, "M001", "By Medical", "Rawat Inap", "2026-01-01", 5000000))
    conn.execute("INSERT INTO budget_beasiswa (company_id,siswa_code,cat1,cat2,tanggal,amount) VALUES (?,?,?,?,?,?)",
                 (COMPANY_ID, "M002", "By Pendidikan", "Semester 1", "2026-01-01", 10000000))
    conn.commit()
    conn.close()
    yield
    if os.path.exists(config.DB_PATH):
        os.remove(config.DB_PATH)


def test_get_siswa_medical_returns_only_medical():
    rows = get_siswa_medical(COMPANY_ID)
    codes = [r["code"] for r in rows]
    assert "M001" in codes
    assert "M002" not in codes


def test_get_siswa_medical_search_filters():
    rows = get_siswa_medical(COMPANY_ID, search="Ani")
    assert len(rows) == 1
    assert rows[0]["code"] == "M001"


def test_get_siswa_medical_includes_budget_amount():
    rows = get_siswa_medical(COMPANY_ID)
    assert rows[0]["medical_budget"] == 5000000
    assert rows[0]["spent_amount"] == 0   # no payments yet
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd app && python -m pytest tests/test_pam_klaim.py::test_get_siswa_medical_returns_only_medical -v
```

Expected: `FAILED` — `ImportError: cannot import name 'get_siswa_medical'`

- [ ] **Step 3: Implement `get_siswa_medical` in service.py**

In `app/modules/payment_memo/service.py`, add after the existing `get_next_pam_no` function:

```python
def get_siswa_medical(company_id: int, search: str = "") -> list:
    """Return siswa that have budget_beasiswa with cat1='By Medical'.

    Includes medical_budget (total) and spent_amount (paid from payment_beasiswa)
    so callers can compute sisa_budget = medical_budget - spent_amount.
    siswa table has no pillar column; pillar is taken from budget_beasiswa.
    """
    sql = """
        SELECT s.code, s.nama,
               b.pillar AS pillar,
               SUM(b.amount) AS medical_budget,
               COALESCE((
                   SELECT SUM(pb.amount)
                   FROM payment_beasiswa pb
                   WHERE pb.siswa_code = s.code
                     AND pb.company_id = s.company_id
                     AND pb.cat1 = 'By Medical'
               ), 0) AS spent_amount
        FROM siswa s
        JOIN budget_beasiswa b ON b.siswa_code = s.code
                               AND b.company_id = s.company_id
                               AND b.cat1 = 'By Medical'
        WHERE s.company_id = ?
    """
    params: list = [company_id]
    if search:
        sql    += " AND (s.nama LIKE ? OR s.code LIKE ?)"
        params += [f"%{search}%", f"%{search}%"]
    sql += " GROUP BY s.code, s.nama, b.pillar ORDER BY s.nama"
    conn = get_conn()
    rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
    conn.close()
    return rows
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd app && python -m pytest tests/test_pam_klaim.py -k "siswa_medical" -v
```

Expected: 3 PASSED

- [ ] **Step 5: Commit**

```bash
git add app/modules/payment_memo/service.py app/tests/test_pam_klaim.py
git commit -m "feat: get_siswa_medical - filter siswa by By Medical budget"
```

---

## Task 4: Service — `save_klaim_payment()`

Saves a Klaim Medis PAM: one `payment_beasiswa` per siswa (total of cat3 amounts), one `klaim_medical` row per cat3 item, one `pam_records` entry.

**Files:**
- Modify: `app/modules/payment_memo/service.py`
- Modify: `app/tests/test_pam_klaim.py`

- [ ] **Step 1: Write failing tests**

Append to `app/tests/test_pam_klaim.py`:

```python
from modules.payment_memo.service import save_klaim_payment


def test_save_klaim_missing_pam_no():
    result = save_klaim_payment(COMPANY_ID, "ETF", {
        "pam_no": "", "tanggal": "2026-06-17", "rows": []
    })
    assert result["ok"] is False
    assert "PAM" in result["pesan"]


def test_save_klaim_empty_rows():
    result = save_klaim_payment(COMPANY_ID, "ETF", {
        "pam_no": "PAM-001-ETF-06-2026", "tanggal": "2026-06-17", "rows": []
    })
    assert result["ok"] is False


def test_save_klaim_row_without_cat3():
    result = save_klaim_payment(COMPANY_ID, "ETF", {
        "pam_no": "PAM-001-ETF-06-2026",
        "tanggal": "2026-06-17",
        "pillar": "AGRI",
        "perusahaan": "RS Siloam",
        "rows": [{"siswa_code": "M001", "cat2": "Rawat Inap",
                  "kelas": "VIP", "rumah_sakit": "RS A", "diagnosa": "Flu",
                  "spesialisasi": "General Practitioner",
                  "cat3_items": []}]
    })
    assert result["ok"] is False


def _klaim_payload():
    return {
        "tab": "agri",
        "tanggal": "2026-06-17",
        "pam_no": "PAM-001-ETF-06-2026",
        "perusahaan": "RS Siloam",
        "keterangan": "Klaim medis Juni",
        "pillar": "AGRI",
        "rows": [
            {
                "siswa_code": "M001",
                "cat2": "Rawat Inap",
                "kelas": "VIP",
                "rumah_sakit": "RS Siloam",
                "diagnosa": "Demam Typoid",
                "spesialisasi": "General Practitioner",
                "cat3_items": [
                    {"cat3": "Kamar", "amount": 3000000, "tanggal": "2026-06-10"},
                    {"cat3": "Obat",  "amount":  500000, "tanggal": "2026-06-10"},
                ],
            }
        ],
    }


def test_save_klaim_success_creates_pam_record():
    # M001 is already inserted by clean_db fixture
    result = save_klaim_payment(COMPANY_ID, "ETF", _klaim_payload())
    assert result["ok"] is True, result.get("pesan")

    conn = get_conn()
    pam = conn.execute("SELECT * FROM pam_records WHERE pam_no=?",
                       ("PAM-001-ETF-06-2026",)).fetchone()
    assert pam is not None
    assert pam["total_amount"] == 3500000
    assert pam["source"] == "klaim_medis"
    conn.close()


def test_save_klaim_success_creates_payment_beasiswa():
    save_klaim_payment(COMPANY_ID, "ETF", _klaim_payload())

    conn = get_conn()
    pb = conn.execute("SELECT * FROM payment_beasiswa WHERE siswa_code=?", ("M001",)).fetchone()
    assert pb is not None
    assert pb["cat1"] == "By Medical"
    assert pb["cat2"] == "Rawat Inap"
    assert pb["amount"] == 3500000
    assert pb["pam"] == "PAM-001-ETF-06-2026"
    conn.close()


def test_save_klaim_success_creates_klaim_medical_rows():
    save_klaim_payment(COMPANY_ID, "ETF", _klaim_payload())

    conn = get_conn()
    items = conn.execute("SELECT * FROM klaim_medical WHERE siswa_code=? ORDER BY id",
                         ("M001",)).fetchall()
    assert len(items) == 2
    assert items[0]["perawatan"] == "Kamar"
    assert items[0]["amount"] == 3000000
    assert items[1]["perawatan"] == "Obat"
    assert items[0]["kelas"] == "VIP"
    assert items[0]["rumah_sakit"] == "RS Siloam"
    conn.close()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd app && python -m pytest tests/test_pam_klaim.py -k "klaim" -v 2>&1 | head -30
```

Expected: `FAILED` — `ImportError: cannot import name 'save_klaim_payment'`

- [ ] **Step 3: Implement `save_klaim_payment` in service.py**

In `app/modules/payment_memo/service.py`, add after `get_siswa_medical`:

```python
def save_klaim_payment(company_id: int, company_code: str, data: dict) -> dict:
    """Save Klaim Medis PAM: payment_beasiswa + klaim_medical + pam_records."""
    tanggal    = data.get("tanggal") or _ts()[:10]
    pam_no     = (data.get("pam_no") or "").strip()
    keterangan = data.get("keterangan") or ""
    perusahaan = data.get("perusahaan") or ""
    pillar     = data.get("pillar") or ""
    rows       = data.get("rows") or []

    if not pam_no:
        return {"ok": False, "pesan": "No. PAM wajib diisi."}
    if not rows:
        return {"ok": False, "pesan": "Minimal 1 baris siswa."}

    for row in rows:
        if not (row.get("cat3_items") and
                any(float(i.get("amount", 0)) > 0 for i in row["cat3_items"])):
            return {"ok": False,
                    "pesan": f"Siswa {row.get('siswa_code', '?')} harus memiliki minimal 1 cat3 dengan amount > 0."}

    conn = get_conn()
    try:
        grand_total = 0.0
        for row in rows:
            siswa_code  = (row.get("siswa_code") or "").strip()
            cat2        = row.get("cat2") or ""
            kelas       = row.get("kelas") or ""
            rumah_sakit = row.get("rumah_sakit") or ""
            diagnosa    = row.get("diagnosa") or ""
            spesialisasi= row.get("spesialisasi") or ""
            cat3_items  = [i for i in row.get("cat3_items", [])
                           if float(i.get("amount", 0)) > 0]
            row_total   = sum(float(i["amount"]) for i in cat3_items)

            # 1. Insert payment_beasiswa (one per siswa, total of cat3 amounts)
            cur = conn.execute(
                """INSERT INTO payment_beasiswa
                   (company_id, siswa_code, cat1, cat2, tanggal, amount,
                    pillar, perusahaan, pam, status)
                   VALUES (?,?,?,?,?,?,?,?,?,'open')""",
                (company_id, siswa_code, "By Medical", cat2, tanggal,
                 row_total, pillar, perusahaan, pam_no)
            )
            pb_id = cur.lastrowid

            # 2. Insert klaim_medical rows (one per cat3 item)
            for item in cat3_items:
                conn.execute(
                    """INSERT INTO klaim_medical
                       (company_id, siswa_code, pam, tanggal, amount, perawatan,
                        kelas, rumah_sakit, diagnosa, spesialisasi,
                        pillar, perusahaan, payment_id, created_at)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (company_id, siswa_code, pam_no,
                     item.get("tanggal") or tanggal,
                     float(item["amount"]),
                     item.get("cat3") or "",
                     kelas, rumah_sakit, diagnosa, spesialisasi,
                     pillar, perusahaan, pb_id, _ts())
                )
            grand_total += row_total

        # 3. Insert one pam_records entry
        due_date = _add_one_month(tanggal)
        conn.execute(
            """INSERT INTO pam_records
               (company_id, pam_no, pam_date, requestors_name, keterangan,
                total_amount, due_date, pillar, source, status, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (company_id, pam_no, tanggal,
             company_code, keterangan,
             grand_total, due_date, pillar, "klaim_medis", "open", _ts())
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        conn.close()
        return {"ok": False, "pesan": f"Gagal menyimpan: {e}"}

    conn.close()
    return {"ok": True, "pesan": f"PAM Klaim Medis {pam_no} berhasil dibuat.", "pam_no": pam_no}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd app && python -m pytest tests/test_pam_klaim.py -k "klaim" -v
```

Expected: all `klaim` tests PASS.

- [ ] **Step 5: Run full test suite to verify no regression**

```bash
cd app && python -m pytest tests/ --tb=short 2>&1 | tail -10
```

Expected: same baseline pass count.

- [ ] **Step 6: Commit**

```bash
git add app/modules/payment_memo/service.py app/tests/test_pam_klaim.py
git commit -m "feat: save_klaim_payment - klaim medis to payment_beasiswa + klaim_medical + pam_records"
```

---

## Task 5: Service — `save_others_payment()`

Saves non-beasiswa PAM (Tagihan/ETF/Sponsor/Others): only `pam_records`, no `payment_beasiswa`.

**Files:**
- Modify: `app/modules/payment_memo/service.py`
- Modify: `app/tests/test_pam_klaim.py`

- [ ] **Step 1: Write failing tests**

Append to `app/tests/test_pam_klaim.py`:

```python
from modules.payment_memo.service import save_others_payment


def test_save_others_missing_pam_no():
    result = save_others_payment(COMPANY_ID, "ETF", {
        "pam_no": "", "keterangan": "test", "dpp": 1000000
    })
    assert result["ok"] is False
    assert "PAM" in result["pesan"]


def test_save_others_missing_keterangan():
    result = save_others_payment(COMPANY_ID, "ETF", {
        "pam_no": "PAM-002-ETF-06-2026", "keterangan": "", "dpp": 1000000
    })
    assert result["ok"] is False
    assert "Keterangan" in result["pesan"]


def test_save_others_zero_dpp():
    result = save_others_payment(COMPANY_ID, "ETF", {
        "pam_no": "PAM-002-ETF-06-2026", "keterangan": "Tagihan listrik", "dpp": 0
    })
    assert result["ok"] is False


def test_save_others_success_creates_pam_record():
    result = save_others_payment(COMPANY_ID, "ETF", {
        "tab": "agri",
        "pam_no": "PAM-002-ETF-06-2026",
        "tanggal": "2026-06-17",
        "perusahaan": "PT Telkom",
        "keterangan": "Tagihan internet",
        "pillar": "AGRI",
        "transaksi": "tagihan",
        "mata_uang": "IDR",
        "dpp": 5000000,
        "ppn": 550000,
    })
    assert result["ok"] is True, result.get("pesan")

    conn = get_conn()
    pam = conn.execute("SELECT * FROM pam_records WHERE pam_no=?",
                       ("PAM-002-ETF-06-2026",)).fetchone()
    assert pam is not None
    assert pam["source"] == "tagihan"
    assert pam["dpp"] == 5000000
    assert pam["ppn"] == 550000
    assert pam["total_amount"] == 5550000
    assert pam["mata_uang"] == "IDR"
    assert pam["pt"] == "PT Telkom"
    conn.close()


def test_save_others_no_payment_beasiswa():
    save_others_payment(COMPANY_ID, "ETF", {
        "pam_no": "PAM-002-ETF-06-2026",
        "tanggal": "2026-06-17",
        "keterangan": "Tagihan internet",
        "pillar": "AGRI",
        "transaksi": "tagihan",
        "mata_uang": "IDR",
        "dpp": 5000000,
        "ppn": 550000,
    })
    conn = get_conn()
    count = conn.execute("SELECT COUNT(*) FROM payment_beasiswa").fetchone()[0]
    assert count == 0
    conn.close()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd app && python -m pytest tests/test_pam_klaim.py -k "others" -v 2>&1 | head -20
```

Expected: `FAILED` — `ImportError: cannot import name 'save_others_payment'`

- [ ] **Step 3: Implement `save_others_payment` in service.py**

Add after `save_klaim_payment` in `app/modules/payment_memo/service.py`:

```python
def save_others_payment(company_id: int, company_code: str, data: dict) -> dict:
    """Save non-beasiswa PAM (Tagihan/ETF/Sponsor/Others): pam_records only."""
    pam_no     = (data.get("pam_no") or "").strip()
    keterangan = (data.get("keterangan") or "").strip()
    tanggal    = data.get("tanggal") or _ts()[:10]
    perusahaan = data.get("perusahaan") or ""
    pillar     = data.get("pillar") or ""
    transaksi  = (data.get("transaksi") or "others").lower()
    mata_uang  = data.get("mata_uang") or "IDR"

    try:
        dpp = float(data.get("dpp") or 0)
        ppn = float(data.get("ppn") or 0)
    except (ValueError, TypeError):
        dpp, ppn = 0.0, 0.0

    if not pam_no:
        return {"ok": False, "pesan": "No. PAM wajib diisi."}
    if not keterangan:
        return {"ok": False, "pesan": "Keterangan wajib diisi."}
    if dpp <= 0:
        return {"ok": False, "pesan": "DPP harus lebih dari 0."}

    total    = dpp + ppn
    due_date = _add_one_month(tanggal)
    conn     = get_conn()
    try:
        conn.execute(
            """INSERT INTO pam_records
               (company_id, pam_no, pam_date, requestors_name, keterangan,
                total_amount, due_date, pillar, source, pt,
                mata_uang, dpp, ppn, status, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (company_id, pam_no, tanggal,
             company_code, keterangan,
             total, due_date, pillar, transaksi, perusahaan,
             mata_uang, dpp, ppn, "open", _ts())
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        conn.close()
        return {"ok": False, "pesan": f"Gagal menyimpan: {e}"}

    conn.close()
    return {"ok": True, "pesan": f"PAM {pam_no} berhasil dibuat.", "pam_no": pam_no}
```

- [ ] **Step 4: Run all klaim tests to verify they pass**

```bash
cd app && python -m pytest tests/test_pam_klaim.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add app/modules/payment_memo/service.py app/tests/test_pam_klaim.py
git commit -m "feat: save_others_payment - tagihan/etf/sponsor to pam_records only"
```

---

## Task 6: Routes — 3 new endpoints

**Files:**
- Modify: `app/modules/payment_memo/routes.py`

- [ ] **Step 1: Add imports to routes.py**

Find the import block at the top of `app/modules/payment_memo/routes.py` and add the new service functions plus config lists. In the `from modules.payment_memo.service import (...)` block, add:

```python
    get_siswa_medical, save_klaim_payment, save_others_payment,
```

Also add to the `import config` line (already imported), and pass new config lists in the `index()` render — see Step 2.

- [ ] **Step 2: Pass new config lists to the template**

In the `index()` route's `render_template(...)` call, add:

```python
        cat3_medical=config.CAT3_MEDICAL,
        kelas_medical=config.KELAS_MEDICAL,
        spesialisasi_medical=config.SPESIALISASI_MEDICAL,
        transaksi_types=config.TRANSAKSI_TYPES,
```

- [ ] **Step 3: Add the 3 new route handlers**

At the end of `app/modules/payment_memo/routes.py`, add:

```python
@bp.route("/ipay/siswa-medical")
@jwt_html_required
def ipay_siswa_medical():
    company_id = session.get("company_id", 0)
    search     = request.args.get("search", "")
    rows       = get_siswa_medical(company_id, search)
    return jsonify({"ok": True, "rows": rows})


@bp.route("/ipay/save-klaim", methods=["POST"])
@jwt_html_required
def ipay_save_klaim():
    data         = request.get_json(force=True) or {}
    company_id   = session.get("company_id", 0)
    company_code = session.get("company_code", "ETF")
    result = save_klaim_payment(company_id, company_code, data)
    return jsonify(result)


@bp.route("/ipay/save-others", methods=["POST"])
@jwt_html_required
def ipay_save_others():
    data         = request.get_json(force=True) or {}
    company_id   = session.get("company_id", 0)
    company_code = session.get("company_code", "ETF")
    result = save_others_payment(company_id, company_code, data)
    return jsonify(result)
```

- [ ] **Step 4: Verify Flask starts without error**

```bash
cd app && python -c "from app import create_app; app = create_app(); print('OK')"
```

Expected: `OK` printed with no ImportError or route conflict.

- [ ] **Step 5: Commit**

```bash
git add app/modules/payment_memo/routes.py
git commit -m "feat: routes for save-klaim, save-others, siswa-medical endpoints"
```

---

## Task 7: Template — Transaksi dropdown + panel switching

Modifies the existing Input tab header to add the `Transaksi` dropdown and the panel show/hide logic.

**Files:**
- Modify: `app/templates/payment_memo/index.html`

- [ ] **Step 1: Add Transaksi dropdown to the header grid**

Find this line in `index.html` (~line 97):

```html
<div style="display:grid;grid-template-columns:140px 160px minmax(220px,1fr) 200px;gap:.75rem;margin-bottom:.5rem;align-items:end;max-width:900px">
```

Change the grid to add a Transaksi column and insert the select after `#ipay-type`:

```html
<div style="display:grid;grid-template-columns:120px 140px 150px minmax(200px,1fr) 180px;gap:.75rem;margin-bottom:.5rem;align-items:end;max-width:1000px">
  <div class="form-group" style="margin:0">
    <label>Tipe PAM</label>
    <select id="ipay-type" onchange="ipayOnTypeChange()"
            style="width:100%;border:1.5px solid #3b82f6;color:#1d4ed8;font-weight:700;background:#eff6ff">
      <option value="agri">AGRI</option>
      <option value="app">APP</option>
      <option value="sml">LAND</option>
      <option value="setf">SETF</option>
    </select>
  </div>
  <div class="form-group" style="margin:0">
    <label>Transaksi</label>
    <select id="ipay-tx" onchange="ipayOnTxChange()"
            style="width:100%;border:1.5px solid #10b981;color:#065f46;font-weight:700;background:#ecfdf5">
      {% for tx in transaksi_types %}
      <option value="{{ tx|lower|replace(' ','_') }}">{{ tx }}</option>
      {% endfor %}
    </select>
  </div>
```

Then keep the Tanggal, No. PAM, and Perusahaan divs as they are, closing the grid after Perusahaan.

- [ ] **Step 2: Wrap the existing beasiswa table in `#ipay-panel-beasiswa`**

The existing beasiswa form content (from the table down to the save button) is already wrapped in `<div id="ipay-panel-beasiswa">` (check around line 96 in the template). Verify this wrapper exists — if not, add it:

```html
<div id="ipay-panel-beasiswa">
  <!-- existing table + buttons -->
</div>
```

- [ ] **Step 3: Add `ipayOnTxChange()` JS function**

Find the existing `ipayOnTypeChange()` JavaScript function in the template's `<script>` section and add `ipayOnTxChange()` right after it:

```javascript
function ipayOnTxChange() {
  const tx = document.getElementById("ipay-tx")?.value || "beasiswa";
  const panels = {
    "beasiswa":   "#ipay-panel-beasiswa",
    "klaim_medis":"#ipay-panel-klaim",
    "tagihan":    "#ipay-panel-others",
    "etf":        "#ipay-panel-others",
    "sponsor":    "#ipay-panel-others",
    "others":     "#ipay-panel-others",
  };
  ["#ipay-panel-beasiswa","#ipay-panel-klaim","#ipay-panel-others"].forEach(id => {
    const el = document.querySelector(id);
    if (el) el.style.display = "none";
  });
  const target = panels[tx] || "#ipay-panel-beasiswa";
  const el = document.querySelector(target);
  if (el) el.style.display = "";

  // Update save button label
  const labels = {
    "beasiswa":    "Beasiswa",
    "klaim_medis": "Klaim Medis",
    "tagihan":     "Tagihan",
    "etf":         "ETF",
    "sponsor":     "Sponsor",
    "others":      "Others",
  };
  const btn = document.getElementById("ipay-save-btn");
  if (btn) btn.textContent = `💾 Simpan PAM ${labels[tx] || ""}`;
}
```

- [ ] **Step 4: Update `ipayReset()` to hide non-beasiswa panels**

Find `function ipayReset()` in the template and add at the start of it:

```javascript
  // Hide non-beasiswa panels; reset Transaksi to Beasiswa
  const txEl = document.getElementById("ipay-tx");
  if (txEl) { txEl.value = "beasiswa"; ipayOnTxChange(); }
```

- [ ] **Step 5: Commit**

```bash
git add app/templates/payment_memo/index.html
git commit -m "feat: Transaksi dropdown + panel switch in PAM Input tab"
```

---

## Task 8: Template — `#ipay-panel-klaim` HTML + JS

The Klaim Medis panel: flat table with siswa header rows and cat3 continuation rows. Uses `/ipay/siswa-medical` for autocomplete.

**Files:**
- Modify: `app/templates/payment_memo/index.html`

- [ ] **Step 1: Add config constants as JS at the top of the script block**

Find where `CAT1_BGT` and `CAT2_SEM` are defined as JS constants (around line 961 in template). Add:

```javascript
const CAT3_MEDICAL       = {{ cat3_medical | tojson }};
const KELAS_MEDICAL      = {{ kelas_medical | tojson }};
const SPESIALISASI_MEDICAL = {{ spesialisasi_medical | tojson }};
```

- [ ] **Step 2: Add `#ipay-panel-klaim` HTML**

After the closing `</div>{# end ipay-panel-beasiswa #}` tag (around line 180), insert:

```html
{# ── Panel Klaim Medis ── #}
<div id="ipay-panel-klaim" style="display:none">
  <div class="table-wrap">
    <table id="klaim-table" style="min-width:1100px">
      <thead>
        <tr>
          <th style="min-width:180px">Siswa</th>
          <th style="min-width:100px">Cat2</th>
          <th style="min-width:90px">Kelas</th>
          <th style="min-width:130px">Rumah Sakit</th>
          <th style="min-width:130px">Diagnosa</th>
          <th style="min-width:140px">Spesialisasi</th>
          <th style="min-width:140px">Cat3</th>
          <th style="min-width:120px">Amount</th>
          <th style="min-width:110px">Sisa Budget</th>
          <th style="min-width:110px">Tanggal</th>
          <th style="width:32px"></th>
        </tr>
      </thead>
      <tbody id="klaim-tbody">
        <tr id="klaim-empty-row">
          <td colspan="11" style="text-align:center;color:var(--text-muted)">Klik + Tambah Siswa untuk mulai input.</td>
        </tr>
      </tbody>
      <tfoot>
        <tr>
          <td colspan="7" style="text-align:right;padding-right:.75rem;font-weight:600;font-size:.875rem">Total Amount:</td>
          <td id="klaim-total-amt" class="num-right" style="font-weight:700;color:#1a56db;white-space:nowrap">Rp 0</td>
          <td colspan="3"></td>
        </tr>
      </tfoot>
    </table>
  </div>
  <div style="display:flex;gap:.5rem;margin-top:.75rem;align-items:center">
    <button class="btn btn-secondary btn-sm" onclick="klaimAddSiswa()">+ Tambah Siswa</button>
    <button id="klaim-save-btn" class="btn btn-primary" onclick="ipaySaveKlaim()">💾 Simpan PAM Klaim Medis</button>
  </div>
</div>{# end ipay-panel-klaim #}
```

- [ ] **Step 3: Add Klaim Medis JS functions**

In the `<script>` section, add the following JavaScript block. Add it near `ipayAddRow()` to keep related code together.

```javascript
// ── Klaim Medis Panel ─────────────────────────────────────────────────────────
let _klaimRid = 0;

function _klaimMkSelect(opts, placeholder) {
  const sel = document.createElement("select");
  sel.style.cssText = "font-size:10px;width:100%;border:1px solid #d1d5db;border-radius:3px;padding:2px 4px";
  if (placeholder) {
    const ph = document.createElement("option");
    ph.value = ""; ph.textContent = placeholder; ph.disabled = true; ph.selected = true;
    sel.appendChild(ph);
  }
  opts.forEach(o => {
    const opt = document.createElement("option");
    opt.value = o; opt.textContent = o;
    sel.appendChild(opt);
  });
  return sel;
}

function _klaimMkInput(type, placeholder) {
  const inp = document.createElement("input");
  inp.type = type; inp.placeholder = placeholder || "";
  inp.className = "dm-inp";
  if (type === "number") inp.min = "0";
  return inp;
}

function _klaimUpdateTotal() {
  const tbody = document.getElementById("klaim-tbody");
  let total = 0;
  tbody.querySelectorAll("input.klaim-amt").forEach(inp => {
    total += parseFloat(inp.value) || 0;
  });
  document.getElementById("klaim-total-amt").textContent =
    "Rp " + total.toLocaleString("id-ID");
}

async function _klaimFetchSiswabudget(code) {
  // Returns sisa_budget = medical_budget - spent_amount for the given siswa code
  try {
    const res = await apiFetch(`/payment-memo/ipay/siswa-medical?search=${encodeURIComponent(code)}`);
    if (!res) return null;
    const data = await res.json();
    const found = (data.rows || []).find(r => r.code === code);
    if (!found) return null;
    return (found.medical_budget || 0) - (found.spent_amount || 0);
  } catch { return null; }
}

function klaimAddSiswa() {
  const tbody = document.getElementById("klaim-tbody");
  const emptyRow = document.getElementById("klaim-empty-row");
  if (emptyRow) emptyRow.remove();

  const rid = ++_klaimRid;

  // Build siswa header row
  const tr = document.createElement("tr");
  tr.dataset.klaimRid = rid;
  tr.dataset.klaimType = "siswa";
  tr.style.cssText = "background:#fff;border-bottom:1px solid #e2e8f0";

  // Col: Siswa autocomplete
  const tdSiswa = document.createElement("td");
  tdSiswa.style.cssText = "padding:4px 7px;position:relative";
  const inpSiswaSearch = document.createElement("input");
  inpSiswaSearch.type = "text"; inpSiswaSearch.placeholder = "Cari siswa...";
  inpSiswaSearch.className = "dm-inp";
  const inpSiswaCode = document.createElement("input"); inpSiswaCode.type = "hidden";
  const sugg = document.createElement("div");
  sugg.style.cssText = "display:none;position:fixed;z-index:9999;background:#fff;border:1px solid #93c5fd;border-radius:4px;max-height:200px;overflow-y:auto;box-shadow:0 4px 12px rgba(0,0,0,.15)";

  inpSiswaSearch.oninput = async function() {
    const q = this.value.trim();
    if (q.length < 1) { sugg.style.display = "none"; return; }
    const res = await apiFetch(`/payment-memo/ipay/siswa-medical?search=${encodeURIComponent(q)}`);
    if (!res) return;
    const data = await res.json();
    sugg.innerHTML = "";
    (data.rows || []).forEach(s => {
      const d = document.createElement("div");
      d.style.cssText = "padding:5px 8px;cursor:pointer;font-size:11px;border-bottom:1px solid #f3f4f6";
      d.textContent = `${s.nama} (${s.code})`;
      d.onmousedown = async () => {
        inpSiswaSearch.value = `${s.nama} / ${s.code}`;
        inpSiswaCode.value = s.code;
        tr.dataset.siswaCode = s.code;
        sugg.style.display = "none";
        // Update sisa budget on first cat3 row
        const siswaRows = tbody.querySelectorAll(`tr[data-klaim-rid="${rid}"][data-klaim-type="cat3"]`);
        const sisa = await _klaimFetchSiswabudget(s.code);
        if (tr.querySelector(".klaim-budget")) {
          tr.querySelector(".klaim-budget").textContent =
            sisa !== null ? "Rp " + sisa.toLocaleString("id-ID") : "-";
        }
      };
      sugg.appendChild(d);
    });
    sugg.style.display = data.rows?.length ? "block" : "none";
    const rect = inpSiswaSearch.getBoundingClientRect();
    sugg.style.left  = rect.left + "px";
    sugg.style.top   = (rect.bottom + 2) + "px";
    sugg.style.width = Math.max(200, rect.width) + "px";
  };
  inpSiswaSearch.onblur = () => setTimeout(() => { sugg.style.display = "none"; }, 200);

  tdSiswa.appendChild(inpSiswaSearch);
  tdSiswa.appendChild(inpSiswaCode);
  document.body.appendChild(sugg);
  tr._siswaCode  = inpSiswaCode;
  tr._siswaSugg  = sugg;

  // Col: Cat2
  const tdCat2 = document.createElement("td"); tdCat2.style.padding = "4px 7px";
  const selCat2 = _klaimMkSelect(["Rawat Inap","Rawat Jalan"], "Pilih...");
  tdCat2.appendChild(selCat2); tr._cat2 = selCat2;

  // Col: Kelas
  const tdKelas = document.createElement("td"); tdKelas.style.padding = "4px 7px";
  const selKelas = _klaimMkSelect(KELAS_MEDICAL, "Kelas...");
  tdKelas.appendChild(selKelas); tr._kelas = selKelas;

  // Col: Rumah Sakit
  const tdRS = document.createElement("td"); tdRS.style.padding = "4px 7px";
  const inpRS = _klaimMkInput("text", "Rumah Sakit...");
  tdRS.appendChild(inpRS); tr._rs = inpRS;

  // Col: Diagnosa
  const tdDx = document.createElement("td"); tdDx.style.padding = "4px 7px";
  const inpDx = _klaimMkInput("text", "Diagnosa...");
  tdDx.appendChild(inpDx); tr._dx = inpDx;

  // Col: Spesialisasi
  const tdSpes = document.createElement("td"); tdSpes.style.padding = "4px 7px";
  const selSpes = _klaimMkSelect(SPESIALISASI_MEDICAL, "Spesialisasi...");
  tdSpes.appendChild(selSpes); tr._spes = selSpes;

  // Col: Cat3 (first item)
  const tdCat3 = document.createElement("td"); tdCat3.style.padding = "4px 7px";
  const selCat3 = _klaimMkSelect(CAT3_MEDICAL, "Cat3...");
  tdCat3.appendChild(selCat3); tr._cat3 = selCat3;

  // Col: Amount
  const tdAmt = document.createElement("td"); tdAmt.style.padding = "4px 7px";
  const inpAmt = _klaimMkInput("number", "0");
  inpAmt.className += " klaim-amt"; inpAmt.oninput = _klaimUpdateTotal;
  tdAmt.appendChild(inpAmt); tr._amt = inpAmt;

  // Col: Sisa Budget (read-only)
  const tdBudget = document.createElement("td");
  tdBudget.style.cssText = "padding:4px 7px;text-align:right;color:#10b981;font-size:10px;font-weight:600";
  tdBudget.className = "klaim-budget"; tdBudget.textContent = "-";

  // Col: Tanggal
  const tdTgl = document.createElement("td"); tdTgl.style.padding = "4px 7px";
  const inpTgl = _klaimMkInput("date", "");
  inpTgl.value = document.getElementById("ipay-tgl")?.value || "";
  tdTgl.appendChild(inpTgl); tr._tgl = inpTgl;

  // Col: Delete siswa group
  const tdDel = document.createElement("td"); tdDel.style.cssText = "padding:4px 7px;text-align:center";
  const btnDel = document.createElement("button");
  btnDel.textContent = "✕"; btnDel.className = "btn btn-danger btn-sm";
  btnDel.onclick = () => klaimRemoveSiswaGroup(rid);
  tdDel.appendChild(btnDel);

  tr.append(tdSiswa, tdCat2, tdKelas, tdRS, tdDx, tdSpes, tdCat3, tdAmt, tdBudget, tdTgl, tdDel);
  tbody.appendChild(tr);

  // Add Cat3 button row
  const trBtn = document.createElement("tr");
  trBtn.dataset.klaimRid = rid; trBtn.dataset.klaimType = "addcat3";
  trBtn.style.cssText = "background:#f0fdf4;border-bottom:2px solid #6ee7b7";
  const tdBtn = document.createElement("td"); tdBtn.colSpan = 11; tdBtn.style.padding = "3px 7px";
  const btnAddCat3 = document.createElement("button");
  btnAddCat3.className = "btn btn-secondary btn-sm";
  btnAddCat3.style.cssText = "border:1px dashed #10b981;color:#059669;background:none;font-size:9px";
  btnAddCat3.textContent = "+ cat3 tambahan";
  btnAddCat3.onclick = () => klaimAddCat3Row(rid, tr);
  tdBtn.appendChild(btnAddCat3); trBtn.appendChild(tdBtn);
  tbody.appendChild(trBtn);
}

function klaimAddCat3Row(rid, siswaRow) {
  const tbody = document.getElementById("klaim-tbody");
  // Insert before the addcat3 button row for this rid
  const btnRow = tbody.querySelector(`tr[data-klaim-rid="${rid}"][data-klaim-type="addcat3"]`);

  const tr = document.createElement("tr");
  tr.dataset.klaimRid = rid; tr.dataset.klaimType = "cat3";
  tr.style.cssText = "background:#eff6ff;border-bottom:1px solid #dbeafe";

  // Cols 1-6: label spanning siswa info columns
  const tdLabel = document.createElement("td");
  tdLabel.colSpan = 6; tdLabel.style.cssText = "padding:4px 7px;color:#94a3b8;font-size:9px;font-style:italic";
  tdLabel.textContent = "↳ cat3 tambahan";

  // Cat3 select
  const tdCat3 = document.createElement("td"); tdCat3.style.padding = "4px 7px";
  const selCat3 = _klaimMkSelect(CAT3_MEDICAL, "Cat3...");
  selCat3.style.background = "#eff6ff;border-color:#93c5fd";
  tdCat3.appendChild(selCat3); tr._cat3 = selCat3;

  // Amount
  const tdAmt = document.createElement("td"); tdAmt.style.padding = "4px 7px";
  const inpAmt = _klaimMkInput("number", "0");
  inpAmt.className += " klaim-amt"; inpAmt.oninput = _klaimUpdateTotal;
  tdAmt.appendChild(inpAmt); tr._amt = inpAmt;

  // Sisa budget (empty for sub-rows)
  const tdBudget = document.createElement("td"); tdBudget.style.padding = "4px 7px";

  // Tanggal
  const tdTgl = document.createElement("td"); tdTgl.style.padding = "4px 7px";
  const inpTgl = _klaimMkInput("date", "");
  inpTgl.value = document.getElementById("ipay-tgl")?.value || "";
  tdTgl.appendChild(inpTgl); tr._tgl = inpTgl;

  // Delete cat3 row
  const tdDel = document.createElement("td"); tdDel.style.cssText = "padding:4px 7px;text-align:center";
  const btnDel = document.createElement("button");
  btnDel.textContent = "✕"; btnDel.className = "btn btn-danger btn-sm";
  btnDel.onclick = () => { tr.remove(); _klaimUpdateTotal(); };
  tdDel.appendChild(btnDel);

  tr.append(tdLabel, tdCat3, tdAmt, tdBudget, tdTgl, tdDel);
  tbody.insertBefore(tr, btnRow);
}

function klaimRemoveSiswaGroup(rid) {
  document.querySelectorAll(`tr[data-klaim-rid="${rid}"]`).forEach(r => r.remove());
  // Remove floating suggestion div
  const tr = document.querySelector(`tr[data-klaim-rid="${rid}"]`);
  if (tr?._siswaSugg) tr._siswaSugg.remove();
  _klaimUpdateTotal();
  if (!document.getElementById("klaim-tbody").querySelector("tr[data-klaim-rid]")) {
    const empty = document.createElement("tr");
    empty.id = "klaim-empty-row";
    empty.innerHTML = '<td colspan="11" style="text-align:center;color:var(--text-muted)">Klik + Tambah Siswa untuk mulai input.</td>';
    document.getElementById("klaim-tbody").appendChild(empty);
  }
}

function klaimReset() {
  const tbody = document.getElementById("klaim-tbody");
  tbody.innerHTML = '<tr id="klaim-empty-row"><td colspan="11" style="text-align:center;color:var(--text-muted)">Klik + Tambah Siswa untuk mulai input.</td></tr>';
  _klaimRid = 0;
  _klaimUpdateTotal();
}

async function ipaySaveKlaim() {
  if (!await confirmModal("Simpan PAM Klaim Medis ini?")) return;

  const type       = document.getElementById("ipay-type")?.value || "agri";
  const tanggal    = document.getElementById("ipay-tgl").value;
  const pam_no     = document.getElementById("ipay-pam-full").value.trim();
  const keterangan = document.getElementById("ipay-catatan")?.value.trim() || "";
  const pillar     = document.getElementById("ipay-pillar").value;
  const perusahaan = document.getElementById("ipay-perusahaan").value;

  if (!tanggal || !pam_no || pam_no === "Memuat...") {
    showToast("Tanggal dan No. PAM wajib ada.", "error"); return;
  }
  if (!perusahaan) { showToast("Perusahaan wajib diisi.", "error"); return; }

  const tbody = document.getElementById("klaim-tbody");
  const siswaRows = [...tbody.querySelectorAll("tr[data-klaim-type='siswa']")];
  if (!siswaRows.length) { showToast("Minimal 1 siswa.", "error"); return; }

  const rows = [];
  for (const siswaRow of siswaRows) {
    const siswa_code = siswaRow.dataset.siswaCode || siswaRow._siswaCode?.value || "";
    if (!siswa_code) { showToast("Semua baris harus memilih siswa.", "error"); return; }

    const rid = siswaRow.dataset.klaimRid;
    // First cat3 item is on the siswa row itself
    const cat3Items = [];
    const firstAmt = parseFloat(siswaRow._amt?.value) || 0;
    if (firstAmt > 0) {
      cat3Items.push({
        cat3:   siswaRow._cat3?.value || "",
        amount: firstAmt,
        tanggal: siswaRow._tgl?.value || tanggal,
      });
    }
    // Continuation cat3 rows
    tbody.querySelectorAll(`tr[data-klaim-rid="${rid}"][data-klaim-type="cat3"]`).forEach(sub => {
      const amt = parseFloat(sub._amt?.value) || 0;
      if (amt > 0) {
        cat3Items.push({
          cat3:    sub._cat3?.value || "",
          amount:  amt,
          tanggal: sub._tgl?.value || tanggal,
        });
      }
    });
    if (!cat3Items.length) { showToast(`Siswa ${siswa_code} harus ada minimal 1 cat3 dengan amount > 0.`, "error"); return; }

    rows.push({
      siswa_code,
      cat2:         siswaRow._cat2?.value || "",
      kelas:        siswaRow._kelas?.value || "",
      rumah_sakit:  siswaRow._rs?.value || "",
      diagnosa:     siswaRow._dx?.value || "",
      spesialisasi: siswaRow._spes?.value || "",
      cat3_items:   cat3Items,
    });
  }

  const btn = document.getElementById("klaim-save-btn");
  if (btn) btn.disabled = true;
  let res;
  try {
    res = await apiFetch("/payment-memo/ipay/save-klaim", {
      method: "POST",
      body: JSON.stringify({ tab: type, tanggal, pam_no, keterangan, perusahaan, pillar, rows })
    });
  } finally {
    if (btn) btn.disabled = false;
  }
  if (!res) return;
  const data = await res.json();
  showToast(data.pesan, data.ok ? "success" : "error");
  if (data.ok) { klaimReset(); ipayReset(); document.querySelector('[data-tab="tab-pam"]')?.click(); }
}
```

- [ ] **Step 4: Commit**

```bash
git add app/templates/payment_memo/index.html
git commit -m "feat: Klaim Medis panel - multi-row siswa + cat3 items UI and ipaySaveKlaim()"
```

---

## Task 9: Template — `#ipay-panel-others` HTML + JS

Simple single-entry form for Tagihan/ETF/Sponsor/Others.

**Files:**
- Modify: `app/templates/payment_memo/index.html`

- [ ] **Step 1: Add `#ipay-panel-others` HTML**

After `</div>{# end ipay-panel-klaim #}`, add:

```html
{# ── Panel Others (Tagihan / ETF / Sponsor / Others) ── #}
<div id="ipay-panel-others" style="display:none">
  <div style="max-width:700px;padding:8px 0">
    <div style="display:grid;grid-template-columns:1fr 120px;gap:12px;margin-bottom:12px">
      <div class="form-group" style="margin:0">
        <label>Keterangan <span style="color:#ef4444">*</span></label>
        <input type="text" id="others-keterangan" class="dm-inp"
               placeholder="Keterangan transaksi..."
               style="border:none;border-bottom:1.5px solid #93c5fd;background:#f0f9ff">
      </div>
      <div class="form-group" style="margin:0">
        <label>Mata Uang</label>
        <select id="others-mataUang"
                style="width:100%;border:1px solid #d1d5db;border-radius:4px;padding:5px 6px;font-size:12px;font-weight:700">
          <option value="IDR">IDR</option>
          <option value="USD">USD</option>
        </select>
      </div>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px">
      <div class="form-group" style="margin:0">
        <label>DPP <span style="color:#ef4444">*</span></label>
        <input type="number" id="others-dpp" class="dm-inp" placeholder="0"
               min="0" oninput="othersCalcTotal()"
               style="text-align:right">
      </div>
      <div class="form-group" style="margin:0">
        <label>PPN</label>
        <input type="number" id="others-ppn" class="dm-inp" placeholder="0"
               min="0" oninput="othersCalcTotal()"
               style="text-align:right">
      </div>
      <div class="form-group" style="margin:0">
        <label>Total <span style="font-size:.65rem;font-weight:400">(DPP+PPN)</span></label>
        <div id="others-total"
             style="border-bottom:2px solid #1d4ed8;padding:4px 6px;font-size:14px;font-weight:700;color:#1d4ed8;text-align:right;background:#eff6ff;border-radius:2px">
          Rp 0
        </div>
      </div>
    </div>
  </div>
  <div style="display:flex;gap:.5rem;margin-top:.75rem;align-items:center">
    <button id="others-save-btn" class="btn btn-primary" onclick="ipaySaveOthers()">💾 Simpan PAM</button>
  </div>
</div>{# end ipay-panel-others #}
```

- [ ] **Step 2: Add Others JS functions**

In the `<script>` section, add after the Klaim Medis JS block:

```javascript
// ── Others Panel ─────────────────────────────────────────────────────────────
function othersCalcTotal() {
  const dpp = parseFloat(document.getElementById("others-dpp")?.value) || 0;
  const ppn = parseFloat(document.getElementById("others-ppn")?.value) || 0;
  const total = dpp + ppn;
  const el = document.getElementById("others-total");
  if (el) el.textContent = "Rp " + total.toLocaleString("id-ID");
}

function othersReset() {
  ["others-keterangan","others-dpp","others-ppn"].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.value = "";
  });
  const total = document.getElementById("others-total");
  if (total) total.textContent = "Rp 0";
  const mu = document.getElementById("others-mataUang");
  if (mu) mu.value = "IDR";
}

async function ipaySaveOthers() {
  if (!await confirmModal("Simpan PAM ini?")) return;

  const type       = document.getElementById("ipay-type")?.value || "agri";
  const tx         = document.getElementById("ipay-tx")?.value || "tagihan";
  const tanggal    = document.getElementById("ipay-tgl").value;
  const pam_no     = document.getElementById("ipay-pam-full").value.trim();
  const keterangan = document.getElementById("others-keterangan")?.value.trim() || "";
  const pillar     = document.getElementById("ipay-pillar").value;
  const perusahaan = document.getElementById("ipay-perusahaan").value;
  const mata_uang  = document.getElementById("others-mataUang")?.value || "IDR";
  const dpp        = parseFloat(document.getElementById("others-dpp")?.value) || 0;
  const ppn        = parseFloat(document.getElementById("others-ppn")?.value) || 0;

  if (!tanggal || !pam_no || pam_no === "Memuat...") {
    showToast("Tanggal dan No. PAM wajib ada.", "error"); return;
  }
  if (!keterangan) { showToast("Keterangan wajib diisi.", "error"); return; }
  if (dpp <= 0)    { showToast("DPP harus lebih dari 0.", "error"); return; }

  const btn = document.getElementById("others-save-btn");
  if (btn) btn.disabled = true;
  let res;
  try {
    res = await apiFetch("/payment-memo/ipay/save-others", {
      method: "POST",
      body: JSON.stringify({
        tab: type, transaksi: tx, tanggal, pam_no,
        keterangan, perusahaan, pillar, mata_uang, dpp, ppn
      })
    });
  } finally {
    if (btn) btn.disabled = false;
  }
  if (!res) return;
  const data = await res.json();
  showToast(data.pesan, data.ok ? "success" : "error");
  if (data.ok) {
    othersReset();
    ipayReset();
    document.querySelector('[data-tab="tab-pam"]')?.click();
  }
}
```

- [ ] **Step 3: Update `ipayReset()` to also reset Others panel**

Find `function ipayReset()` and add a call to `othersReset()` inside it:

```javascript
  if (typeof othersReset === "function") othersReset();
```

- [ ] **Step 4: Commit**

```bash
git add app/templates/payment_memo/index.html
git commit -m "feat: Others panel - tagihan/ETF/sponsor simple form with ipaySaveOthers()"
```

---

## Task 10: Template — Source filter options + final verification

Add `klaim_medis` to all source filter dropdowns and run final test suite.

**Files:**
- Modify: `app/templates/payment_memo/index.html`

- [ ] **Step 1: Add klaim_medis to all source filter selects**

Find all four `<select id="pam-filter-source"` / similar source filter dropdowns in the AGRI, APP, LAND, SETF tabs. Each has options like:

```html
<option value="beasiswa">Beasiswa</option>
<option value="etf">ETF</option>
```

Add after the beasiswa option in each:

```html
<option value="klaim_medis">Klaim Medis</option>
```

There are 4 tabs with source filters (look for `pam-filter-source`, `fiori-filter-source`, `sml-filter-source`, `setf-filter-source` or equivalent). Add the option to each.

- [ ] **Step 2: Run full test suite**

```bash
cd app && python -m pytest tests/ -v --tb=short 2>&1 | tail -20
```

Expected: all tests in `test_pam_klaim.py` PASS. Overall suite same or better than baseline.

- [ ] **Step 3: Smoke test in browser**

Start the app and manually verify:
1. Go to Payment Memo → Input tab
2. Transaksi dropdown appears with 6 options
3. Select "Klaim Medis" → Klaim Medis panel shows, Beasiswa panel hides
4. Add a siswa — autocomplete shows only siswa with medical budget
5. Add cat3 row — continuation row appears with ↳ label
6. Select "Tagihan" → Others panel shows
7. DPP + PPN auto-computes Total
8. Switch back to "Beasiswa" → existing form unchanged

- [ ] **Step 4: Final commit**

```bash
git add app/templates/payment_memo/index.html
git commit -m "feat: add klaim_medis to source filter dropdowns; complete PAM input transaksi type"
```
