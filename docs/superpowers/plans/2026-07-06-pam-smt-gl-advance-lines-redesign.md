# PAM SMT Input Redesign (GL/Advance Itemized Lines) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the flat "Others" PAM input form for Sinar Mas Tjipta (SMT, `company_id=1`) with an itemized multi-row GL/Advance transaction table, drop the redundant "Tipe PAM" selector, and rename the SMT list tab to "PAM List".

**Architecture:** New `coa_pam` lookup table (seeded from `COA.xlsx`) drives a per-row "Jenis Biaya" picker that auto-fills MR classification + GL Account. New `pam_transaction_lines` table holds the itemized financial breakdown per PAM (separate from the existing `smt_pam_lines`/`advance_pam_lines` SLA-tracking tables, untouched). Routing (GL→pillar SMT, Advance→pillar ADVANCE) moves from the removed "Tipe PAM" dropdown into the existing "Transaksi" dropdown, reusing the existing `_IPAY_PAM_PREFIX`/`_VALID_PILLARS` maps in `service.py` unchanged. Print Memo auto-checks "Type of Request" from the saved lines' `tipe_dokumen`.

**Tech Stack:** Flask, SQLite (raw SQL, no ORM), Jinja2, vanilla JS, pytest.

**Full design reference:** `docs/superpowers/specs/2026-07-06-pam-smt-gl-advance-lines-redesign-design.md`

## Global Constraints

- ETF pillar behavior (AGRI/APP/LAND/SETF/ENERGY, `save_others_payment`, `/ipay/save-others`) must NOT be touched — additive/SMT-only changes only.
- No changes to `smt_pam_lines` / `advance_pam_lines` (SLA-tracking) or the Advance→SMT realization cascade — `pam_transaction_lines` is a new, separate table linked by `pam_id`.
- `_IPAY_PAM_PREFIX` / `_VALID_PILLARS` in `service.py` already map `"smt"→"SMT"` and `"advance"→"SMT"` (shared numbering sequence) — do not change these; only change what feeds the `tab`/`type` value on the frontend.
- Bugfix in scope: frontend `_PAM_RE` regex must accept `SMT` (currently only `ETF|APP|LAND|SETF`), since real SMT PAM numbers are `PAM-XXX-SMT-MM-YYYY` (confirmed by `test_smt_pam.py`).
- Budget Monitoring `budget_realisasi` integration is OUT OF SCOPE for this plan — `cost_center`/`budget_activity` fields are stored but not written to `budget_master`/`budget_realisasi`.
- No JS test framework exists in this repo — frontend tasks are verified manually via the running dev server, not pytest.

---

### Task 1: Data model — `coa_pam` + `pam_transaction_lines` tables, COA-PAM seed data

**Files:**
- Modify: `app/config.py` (append after line 151, end of `PAM_APPROVED_BY_2`)
- Modify: `app/database.py:204` (DDL string — insert 2 new `CREATE TABLE` blocks right after the `vendors` table definition, lines 199-204)
- Modify: `app/database.py:621` (inside `migrate_db()` — insert idempotent `CREATE TABLE IF NOT EXISTS` + seed block right after the existing `coa` table block, lines 609-621)
- Modify: `app/database.py:1169` (inside `init_db()` — insert `coa_pam` seed loop right after the existing `coa` seed loop, lines 1165-1169)
- Test: `app/tests/test_coa_pam.py` (new)

**Interfaces:**
- Produces: table `coa_pam(id, klasifikasi_sr, klasifikasi_mr, coa_advance, coa_expense)`.
- Produces: table `pam_transaction_lines(id, pam_id, coa_pam_id, klasifikasi_sr, klasifikasi_mr, gl_account, tipe_dokumen, no_invoice, dpp, ppn, total_amount, cost_center, budget_activity, keterangan, created_at, updated_at)`.
- Produces: `config.COA_PAM_SEED` — list of 44 `(klasifikasi_sr, klasifikasi_mr, coa_advance, coa_expense)` tuples, `coa_advance` is `None` where not applicable.

- [ ] **Step 1: Write the failing test**

Create `app/tests/test_coa_pam.py`:

```python
import os, sys, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config
config.DB_PATH = os.path.join(os.path.dirname(__file__), "test_coa_pam.db")

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


def test_coa_pam_table_exists_with_expected_columns():
    conn = get_conn()
    cols = _columns(conn, "coa_pam")
    conn.close()
    for col in ["id", "klasifikasi_sr", "klasifikasi_mr", "coa_advance", "coa_expense"]:
        assert col in cols, f"Missing column: {col}"


def test_coa_pam_seeded_with_44_rows():
    conn = get_conn()
    count = conn.execute("SELECT COUNT(*) AS n FROM coa_pam").fetchone()["n"]
    conn.close()
    assert count == 44


def test_coa_pam_beasiswa_row_values():
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM coa_pam WHERE klasifikasi_sr = 'Beasiswa'"
    ).fetchone()
    conn.close()
    assert row is not None
    assert row["klasifikasi_mr"] == "Scholarship Expense"
    assert row["coa_advance"] is None
    assert row["coa_expense"] == "70110230"


def test_coa_pam_advance_row_has_coa_advance_code():
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM coa_pam WHERE klasifikasi_sr = 'Advance for Training'"
    ).fetchone()
    conn.close()
    assert row is not None
    assert row["coa_advance"] == "16001300"
    assert row["coa_expense"] == "70110200"


def test_pam_transaction_lines_table_exists_with_expected_columns():
    conn = get_conn()
    cols = _columns(conn, "pam_transaction_lines")
    conn.close()
    expected = [
        "id", "pam_id", "coa_pam_id", "klasifikasi_sr", "klasifikasi_mr",
        "gl_account", "tipe_dokumen", "no_invoice", "dpp", "ppn",
        "total_amount", "cost_center", "budget_activity", "keterangan",
        "created_at", "updated_at",
    ]
    for col in expected:
        assert col in cols, f"Missing column: {col}"


def test_pam_transaction_lines_cascades_on_pam_delete():
    conn = get_conn()
    conn.execute(
        """INSERT INTO pam_records
           (company_id, pam_no, pam_date, requestors_name, keterangan,
            total_amount, due_date, pillar, source, status)
           VALUES (1,'PAM-999-SMT-07-2026','2026-07-06','Jany Turkanda','Test',
                   100000,'2026-08-06','SMT','gl','open')"""
    )
    pam_id = conn.execute(
        "SELECT id FROM pam_records WHERE pam_no='PAM-999-SMT-07-2026'"
    ).fetchone()["id"]
    conn.execute(
        """INSERT INTO pam_transaction_lines
           (pam_id, klasifikasi_sr, klasifikasi_mr, gl_account, dpp, ppn, total_amount)
           VALUES (?,'Beasiswa','Scholarship Expense','70110230',100000,0,100000)""",
        (pam_id,)
    )
    conn.commit()
    conn.execute("DELETE FROM pam_records WHERE id=?", (pam_id,))
    conn.commit()
    remaining = conn.execute(
        "SELECT COUNT(*) AS n FROM pam_transaction_lines WHERE pam_id=?", (pam_id,)
    ).fetchone()["n"]
    conn.close()
    assert remaining == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd app && python -m pytest tests/test_coa_pam.py -v`
Expected: FAIL — `coa_pam`/`pam_transaction_lines` tables don't exist yet (`sqlite3.OperationalError: no such table`).

- [ ] **Step 3: Add `COA_PAM_SEED` to `config.py`**

In `app/config.py`, after line 151 (`PAM_APPROVED_BY_2 = "Tenti Kidjo"`), add:

```python

# COA-PAM lookup — SMT GL/Advance "Jenis Biaya" classification (Statutory Report /
# Management Report labels) + the GL code to use depending on Transaksi type.
# Seed data from C:\Users\25010160\Downloads\COA.xlsx (44 rows).
# Tuple shape: (klasifikasi_sr, klasifikasi_mr, coa_advance, coa_expense)
# coa_advance is None where the row only applies to GL (Expense) transactions.
COA_PAM_SEED = [
    ("Beasiswa", "Scholarship Expense", None, "70110230"),
    ("Biaya Listrik", "Electrical Expense", None, "70103200"),
    ("Biaya Organisasi Profesional", "Biaya Organisasi Profesional", None, "70110110"),
    ("Consumption", "Office Consumption", None, "70107600"),
    ("CSR", "CSR Expense", None, "70110220"),
    ("Entertainment", "Entertainment Expense", None, "70107200"),
    ("Equipment", "Office Equipment Expense", None, "70108100"),
    ("Fotocopy", "Biaya Fotocopy", None, "70108110"),
    ("Gift", "Gift Expense", None, "70119310"),
    ("Iklan Media Cetak / Digital", "Biaya Iklan Media Cetak", None, "70004113"),
    ("Iklan Media Digital", "Biaya Iklan Media Digital", None, "70004113"),
    ("Iklan Metro TV", "Biaya Spot Iklan TV & Radio", None, "70004111"),
    ("Jasa Advokasi", "Biaya Jasa Konsultan – Affiliasi", None, "70111132"),
    ("Jasa Konsultan", "Consultant Fee", None, "70111130"),
    ("Link Net", "Communication Expense - 3rd Party", None, "70109100"),
    ("Local Transport", "Local Transportation Expense", None, "70106100"),
    ("Majalah", "Biaya Langganan Majalah", None, "70110400"),
    ("Memberhip International", "Professional International Organization Expense", None, "70110100"),
    ("Membership National", "Professional National Organization Expense", None, "70110110"),
    ("Office Supplies", "Office Supplies", None, "70108100"),
    ("Perbaikan Perabot", "Repair And Maintenance Expense (Material)", None, "70101114"),
    ("Perdin Dalam Negeri", "Local Travel Expense", None, "70106200"),
    ("Perdin Luar Negeri", "Overseas Travel Expense", None, "70106300"),
    ("Piutang Lainnya", "Other Receivable", None, "13001710"),
    ("Rapimnas Kadin daftar acara", "Local Conference Expense", None, "70110500"),
    ("Saham", "Pernyertaan Saham dengan Metode Biaya", None, "25001100"),
    ("Sewa Kendaraan dan Perlengkapan", "Equipment Rent Expense - 3rd Party", None, "70105120"),
    ("Sewa Peralatan", "Equipment Rent Expense - 3rd P", None, "70105120"),
    ("Sponsor", "Sponsorship Expense", None, "70107800"),
    ("Sumbangan", "Social Donation Expense", None, "70107500"),
    ("Advance Others - Sponsor", "Advance Others", "15000900", "70107800"),
    ("Advance Perdin - Perdin Lokal", "Advance Perdin", "16001100", "70106200"),
    ("Advance for Training", "Advance Training", "16001300", "70110200"),
    ("Advance Others - CSR", "Advance Others", "15000900", "70110220"),
    ("Advance Others - Office Equipment", "Advance Others", "15000900", "70108100"),
    ("Advance Uang Muka Lainnya", "Advance Uang Muka Lainnya", "16001810", "70108100"),
    ("Advance Uang Muka Lainnya - Vendor", "Advance Uang Muka Lainnya - Vendor", "16001800", "70108100"),
    ("Advance Uang Muka Lainnya - Karyawan", "Advance Uang Muka Lainnya - Karyawan", "16001810", "70108100"),
    ("Advance Others - Jasa Konsultan", "Advance Others - Jasa Konsultan", "16001810", "70111130"),
    ("Advance Others - Sewa Kendaraan dan Perlengkapan", "Advance Others - Equipment Rent Expense - 3rd Party", "16001810", "70105120"),
    ("Advance - CSR", "Advance Uang Muka CSR", "16001810", "70110220"),
    ("Advance Others - Ceremonial exp", "Advance Others - Ceremonial exp", "16001810", "70101700"),
    ("Advance Membership Organisasi Nasional", "Advance Membership Organisasi Nasional", "15000900", "70110110"),
    ("Advance Others - Biaya Promosi Iklan", "Advance Others", "15000900", "70004110"),
]
```

- [ ] **Step 4: Add the two `CREATE TABLE` blocks to the `DDL` string**

In `app/database.py`, right after the `vendors` table closes (line 204, `);`), insert:

```sql

CREATE TABLE IF NOT EXISTS coa_pam (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    klasifikasi_sr  TEXT NOT NULL,
    klasifikasi_mr  TEXT NOT NULL,
    coa_advance     TEXT,
    coa_expense     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS pam_transaction_lines (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    pam_id          INTEGER NOT NULL REFERENCES pam_records(id) ON DELETE CASCADE,
    coa_pam_id      INTEGER REFERENCES coa_pam(id),
    klasifikasi_sr  TEXT,
    klasifikasi_mr  TEXT,
    gl_account      TEXT,
    tipe_dokumen    TEXT,
    no_invoice      TEXT,
    dpp             REAL DEFAULT 0,
    ppn             REAL DEFAULT 0,
    total_amount    REAL DEFAULT 0,
    cost_center     TEXT,
    budget_activity TEXT,
    keterangan      TEXT,
    created_at      TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at      TEXT
);
CREATE INDEX IF NOT EXISTS idx_pam_transaction_lines_pam_id ON pam_transaction_lines(pam_id);
```

- [ ] **Step 5: Add the idempotent migration block inside `migrate_db()`**

In `app/database.py`, right after the existing `coa` table block ends (line 621, matching the pattern at lines 609-621), insert:

```python

    # coa_pam table (new) — SMT GL/Advance "Jenis Biaya" lookup
    try:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS coa_pam ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "klasifikasi_sr TEXT NOT NULL,"
            "klasifikasi_mr TEXT NOT NULL,"
            "coa_advance TEXT,"
            "coa_expense TEXT NOT NULL)"
        )
        for sr, mr, adv, exp in config.COA_PAM_SEED:
            conn.execute(
                "INSERT OR IGNORE INTO coa_pam (klasifikasi_sr, klasifikasi_mr, coa_advance, coa_expense) "
                "VALUES (?, ?, ?, ?)",
                (sr, mr, adv, exp)
            )
        conn.commit()
    except Exception:
        pass

    # pam_transaction_lines table (new) — itemized financial breakdown per PAM
    try:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS pam_transaction_lines ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "pam_id INTEGER NOT NULL REFERENCES pam_records(id) ON DELETE CASCADE,"
            "coa_pam_id INTEGER REFERENCES coa_pam(id),"
            "klasifikasi_sr TEXT, klasifikasi_mr TEXT, gl_account TEXT,"
            "tipe_dokumen TEXT, no_invoice TEXT,"
            "dpp REAL DEFAULT 0, ppn REAL DEFAULT 0, total_amount REAL DEFAULT 0,"
            "cost_center TEXT, budget_activity TEXT, keterangan TEXT,"
            "created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_pam_transaction_lines_pam_id "
            "ON pam_transaction_lines(pam_id)"
        )
        conn.commit()
    except Exception:
        pass
```

- [ ] **Step 6: Add the seed loop inside `init_db()`**

In `app/database.py`, right after the existing `coa` seed loop (lines 1165-1169), insert:

```python

    for sr, mr, adv, exp in config.COA_PAM_SEED:
        conn.execute(
            "INSERT OR IGNORE INTO coa_pam (klasifikasi_sr, klasifikasi_mr, coa_advance, coa_expense) "
            "VALUES (?, ?, ?, ?)",
            (sr, mr, adv, exp)
        )
```

- [ ] **Step 7: Run test to verify it passes**

Run: `cd app && python -m pytest tests/test_coa_pam.py -v`
Expected: PASS (5 tests)

- [ ] **Step 8: Commit**

```bash
git add app/config.py app/database.py app/tests/test_coa_pam.py
git commit -m "feat: add coa_pam and pam_transaction_lines tables for SMT PAM redesign"
```

---

### Task 2: Service layer — `get_coa_pam_list`, `get_pam_transaction_lines`, `save_smt_pam_transaction`

**Files:**
- Modify: `app/modules/payment_memo/service.py` (add functions near `get_coa_list`, line 810-816, and near `save_others_payment`, lines 587-631)
- Test: `app/tests/test_pam_smt_lines_service.py` (new)

**Interfaces:**
- Consumes: `config.COA_PAM_SEED` (Task 1), `_add_one_month`, `_ts`, `get_conn`, `config.PAM_DEFAULT_REQUESTOR` (all already in `service.py`).
- Produces: `get_coa_pam_list(search: str = "") -> list[dict]` — each dict has `id, klasifikasi_sr, klasifikasi_mr, coa_advance, coa_expense`.
- Produces: `get_pam_transaction_lines(pam_id: int) -> list[dict]`.
- Produces: `save_smt_pam_transaction(company_id: int, company_code: str, data: dict) -> dict` — `data` shape: `{tanggal, pam_no, perusahaan, pillar, transaksi: "gl"|"advance", rows: [{coa_pam_id, klasifikasi_sr, klasifikasi_mr, gl_account, tipe_dokumen, no_invoice, dpp, ppn, cost_center, budget_activity, keterangan}]}`. Returns `{"ok": bool, "pesan": str, "pam_no": str}` on success, `{"ok": False, "pesan": str}` on validation failure.

- [ ] **Step 1: Write the failing tests**

Create `app/tests/test_pam_smt_lines_service.py`:

```python
import os, sys, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config
config.DB_PATH = os.path.join(os.path.dirname(__file__), "test_pam_smt_lines_service.db")

from database import init_db, get_conn
from modules.payment_memo.service import (
    get_coa_pam_list, get_pam_transaction_lines, save_smt_pam_transaction,
)

SMT_COMPANY_ID = 1


@pytest.fixture(autouse=True)
def clean_db():
    if os.path.exists(config.DB_PATH):
        os.remove(config.DB_PATH)
    init_db()
    yield
    if os.path.exists(config.DB_PATH):
        os.remove(config.DB_PATH)


def test_get_coa_pam_list_returns_all_when_no_search():
    rows = get_coa_pam_list()
    assert len(rows) == 44
    assert rows[0]["klasifikasi_sr"]


def test_get_coa_pam_list_filters_by_search():
    rows = get_coa_pam_list("Beasiswa")
    assert len(rows) == 1
    assert rows[0]["klasifikasi_mr"] == "Scholarship Expense"


def _coa_pam_id(sr):
    conn = get_conn()
    row = conn.execute(
        "SELECT id, coa_expense, coa_advance FROM coa_pam WHERE klasifikasi_sr=?", (sr,)
    ).fetchone()
    conn.close()
    return dict(row)


def test_save_smt_pam_transaction_gl_sums_lines_into_header():
    coa = _coa_pam_id("Beasiswa")
    data = {
        "tanggal": "2026-07-06", "pam_no": "PAM-100-SMT-07-2026",
        "perusahaan": "PT. Sinar Mas Tjipta", "pillar": "SMT", "transaksi": "gl",
        "rows": [
            {"coa_pam_id": coa["id"], "klasifikasi_sr": "Beasiswa",
             "klasifikasi_mr": "Scholarship Expense", "gl_account": coa["coa_expense"],
             "tipe_dokumen": "Invoice Payment – Non PO Invoice", "no_invoice": "INV-001",
             "dpp": 1000000, "ppn": 110000, "cost_center": "POCCOM",
             "budget_activity": "Program A", "keterangan": "Baris 1"},
            {"coa_pam_id": coa["id"], "klasifikasi_sr": "Beasiswa",
             "klasifikasi_mr": "Scholarship Expense", "gl_account": coa["coa_expense"],
             "tipe_dokumen": "Invoice Payment – Non PO Invoice", "no_invoice": "INV-002",
             "dpp": 500000, "ppn": 0, "cost_center": "TFOPEX",
             "budget_activity": "Program B", "keterangan": "Baris 2"},
        ],
    }
    result = save_smt_pam_transaction(SMT_COMPANY_ID, "SMT", data)
    assert result["ok"] is True
    assert result["pam_no"] == "PAM-100-SMT-07-2026"

    conn = get_conn()
    header = conn.execute(
        "SELECT * FROM pam_records WHERE pam_no='PAM-100-SMT-07-2026'"
    ).fetchone()
    conn.close()
    assert header["total_amount"] == 1610000
    assert header["dpp"] == 1500000
    assert header["ppn"] == 110000
    assert header["pillar"] == "SMT"

    lines = get_pam_transaction_lines(header["id"])
    assert len(lines) == 2
    assert {l["cost_center"] for l in lines} == {"POCCOM", "TFOPEX"}
    assert lines[0]["gl_account"] == coa["coa_expense"]


def test_save_smt_pam_transaction_advance_uses_coa_advance_gl():
    coa = _coa_pam_id("Advance for Training")
    data = {
        "tanggal": "2026-07-06", "pam_no": "PAM-101-SMT-07-2026",
        "perusahaan": "PT. Sinar Mas Tjipta", "pillar": "ADVANCE", "transaksi": "advance",
        "rows": [
            {"coa_pam_id": coa["id"], "klasifikasi_sr": "Advance for Training",
             "klasifikasi_mr": "Advance Training", "gl_account": coa["coa_advance"],
             "tipe_dokumen": "Employee Advance / Reimbursement (Fund Transfer)",
             "no_invoice": "", "dpp": 2000000, "ppn": 0, "cost_center": "POITEC",
             "budget_activity": "Training Q3", "keterangan": "Advance training"},
        ],
    }
    result = save_smt_pam_transaction(SMT_COMPANY_ID, "SMT", data)
    assert result["ok"] is True

    conn = get_conn()
    header = conn.execute(
        "SELECT * FROM pam_records WHERE pam_no='PAM-101-SMT-07-2026'"
    ).fetchone()
    conn.close()
    assert header["pillar"] == "ADVANCE"
    lines = get_pam_transaction_lines(header["id"])
    assert lines[0]["gl_account"] == coa["coa_advance"]


def test_save_smt_pam_transaction_rejects_no_rows():
    result = save_smt_pam_transaction(SMT_COMPANY_ID, "SMT", {
        "tanggal": "2026-07-06", "pam_no": "PAM-102-SMT-07-2026",
        "perusahaan": "PT. Sinar Mas Tjipta", "pillar": "SMT", "transaksi": "gl",
        "rows": [],
    })
    assert result["ok"] is False


def test_save_smt_pam_transaction_rejects_row_missing_klasifikasi_sr():
    result = save_smt_pam_transaction(SMT_COMPANY_ID, "SMT", {
        "tanggal": "2026-07-06", "pam_no": "PAM-103-SMT-07-2026",
        "perusahaan": "PT. Sinar Mas Tjipta", "pillar": "SMT", "transaksi": "gl",
        "rows": [{"klasifikasi_sr": "", "dpp": 1000, "keterangan": "x"}],
    })
    assert result["ok"] is False


def test_save_smt_pam_transaction_rejects_row_with_zero_dpp():
    result = save_smt_pam_transaction(SMT_COMPANY_ID, "SMT", {
        "tanggal": "2026-07-06", "pam_no": "PAM-104-SMT-07-2026",
        "perusahaan": "PT. Sinar Mas Tjipta", "pillar": "SMT", "transaksi": "gl",
        "rows": [{"klasifikasi_sr": "Beasiswa", "dpp": 0, "keterangan": "x"}],
    })
    assert result["ok"] is False


def test_save_smt_pam_transaction_rejects_row_missing_keterangan():
    result = save_smt_pam_transaction(SMT_COMPANY_ID, "SMT", {
        "tanggal": "2026-07-06", "pam_no": "PAM-105-SMT-07-2026",
        "perusahaan": "PT. Sinar Mas Tjipta", "pillar": "SMT", "transaksi": "gl",
        "rows": [{"klasifikasi_sr": "Beasiswa", "dpp": 1000, "keterangan": ""}],
    })
    assert result["ok"] is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd app && python -m pytest tests/test_pam_smt_lines_service.py -v`
Expected: FAIL — `ImportError: cannot import name 'get_coa_pam_list'` (functions don't exist yet).

- [ ] **Step 3: Implement the service functions**

In `app/modules/payment_memo/service.py`, right after `get_coa_list` (lines 810-816), add:

```python

def get_coa_pam_list(search: str = "") -> list:
    conn = get_conn()
    if search:
        rows = conn.execute(
            """SELECT * FROM coa_pam
               WHERE klasifikasi_sr LIKE ? OR klasifikasi_mr LIKE ?
               ORDER BY klasifikasi_sr""",
            (f"%{search}%", f"%{search}%")
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM coa_pam ORDER BY klasifikasi_sr").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_pam_transaction_lines(pam_id: int) -> list:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM pam_transaction_lines WHERE pam_id=? ORDER BY id", (pam_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
```

Then, right after `save_others_payment` (which ends at line 631, right before `def save_pa_payment`), add:

```python

def save_smt_pam_transaction(company_id: int, company_code: str, data: dict) -> dict:
    """Itemized GL/Advance PAM save for SMT — replaces save_others_payment for
    company SMT only. ETF keeps using save_others_payment unchanged."""
    tanggal    = data.get("tanggal") or _ts()[:10]
    pam_no     = (data.get("pam_no") or "").strip()
    perusahaan = data.get("perusahaan") or ""
    pillar     = (data.get("pillar") or "").upper()
    transaksi  = (data.get("transaksi") or "gl").lower()
    rows       = data.get("rows") or []

    if not pam_no:
        return {"ok": False, "pesan": "No. PAM wajib diisi."}
    if not rows:
        return {"ok": False, "pesan": "Minimal 1 baris transaksi."}

    for row in rows:
        if not (row.get("klasifikasi_sr") or "").strip():
            return {"ok": False, "pesan": "Setiap baris wajib memilih Jenis Biaya (SR)."}
        try:
            dpp = float(row.get("dpp") or 0)
        except (TypeError, ValueError):
            dpp = 0
        if dpp <= 0:
            return {"ok": False, "pesan": "Setiap baris wajib DPP lebih dari 0."}
        if not (row.get("keterangan") or "").strip():
            return {"ok": False, "pesan": "Setiap baris wajib diisi Keterangan."}

    conn = get_conn()
    try:
        grand_dpp = 0.0
        grand_ppn = 0.0
        line_data = []
        for row in rows:
            dpp = float(row.get("dpp") or 0)
            ppn = float(row.get("ppn") or 0)
            grand_dpp += dpp
            grand_ppn += ppn
            line_data.append((row, dpp, ppn, dpp + ppn))
        grand_total = grand_dpp + grand_ppn

        due_date = _add_one_month(tanggal)
        cur = conn.execute(
            """INSERT INTO pam_records
               (company_id, pam_no, pam_date, requestors_name, keterangan,
                total_amount, due_date, pillar, source, pt,
                mata_uang, dpp, ppn, status, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (company_id, pam_no, tanggal,
             config.PAM_DEFAULT_REQUESTOR, "Lihat rincian baris",
             grand_total, due_date, pillar, transaksi, perusahaan,
             "IDR", grand_dpp, grand_ppn, "open", _ts())
        )
        pam_id = cur.lastrowid

        for row, dpp, ppn, total in line_data:
            conn.execute(
                """INSERT INTO pam_transaction_lines
                   (pam_id, coa_pam_id, klasifikasi_sr, klasifikasi_mr, gl_account,
                    tipe_dokumen, no_invoice, dpp, ppn, total_amount,
                    cost_center, budget_activity, keterangan, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (pam_id, row.get("coa_pam_id"), row.get("klasifikasi_sr"),
                 row.get("klasifikasi_mr"), row.get("gl_account"),
                 row.get("tipe_dokumen"), row.get("no_invoice"),
                 dpp, ppn, total, row.get("cost_center"),
                 row.get("budget_activity"), row.get("keterangan"), _ts())
            )
        conn.commit()
    except Exception as e:
        conn.rollback()
        conn.close()
        return {"ok": False, "pesan": f"Gagal menyimpan: {e}"}

    conn.close()
    return {"ok": True, "pesan": f"PAM {pam_no} berhasil dibuat.", "pam_no": pam_no}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd app && python -m pytest tests/test_pam_smt_lines_service.py -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Run full existing suite to check for regressions**

Run: `cd app && python -m pytest tests/ -v`
Expected: PASS (no regressions — `save_others_payment` and everything else untouched)

- [ ] **Step 6: Commit**

```bash
git add app/modules/payment_memo/service.py app/tests/test_pam_smt_lines_service.py
git commit -m "feat: add save_smt_pam_transaction service with itemized GL/Advance lines"
```

---

### Task 3: Routes — save endpoint, PAM detail extension, index() context

**Files:**
- Modify: `app/modules/payment_memo/routes.py:8` (import list — add `get_coa_pam_list`, `save_smt_pam_transaction`, `get_pam_transaction_lines`)
- Modify: `app/modules/payment_memo/routes.py:54-83` (`index()` — add `coa_pam_list=get_coa_pam_list()` to `render_template` context)
- Modify: `app/modules/payment_memo/routes.py:188-197` (`get_pam_detail_route` — attach `transaction_lines`)
- Modify: `app/modules/payment_memo/routes.py:672-679` (add new route `POST /ipay/save-smt-lines` right after `ipay_save_others`)
- Test: `app/tests/test_pam_smt_lines_routes.py` (new)

**Interfaces:**
- Consumes: `get_coa_pam_list`, `save_smt_pam_transaction`, `get_pam_transaction_lines` (Task 2).
- Produces: `POST /payment-memo/ipay/save-smt-lines` — body matches `save_smt_pam_transaction`'s `data` shape, returns its result JSON.
- Produces: `GET /payment-memo/pam/<id>/detail` response now includes `"transaction_lines": [...]`.
- Produces: `index()` template context now includes `coa_pam_list` (list of dicts, same shape as `get_coa_pam_list()`).

- [ ] **Step 1: Write the failing tests**

Create `app/tests/test_pam_smt_lines_routes.py`. This reuses the `app`/`client`/`clean_db`
fixtures already defined globally in `app/tests/conftest.py` — do not redefine them locally.
Login/company-select follows the exact pattern from `app/tests/test_payment_memo_open_pam.py`
(`POST /auth/login` sets an httponly cookie the Flask test client persists automatically;
`POST /select-company` with form data, not JSON):

```python
# app/tests/test_pam_smt_lines_routes.py
from database import get_conn


def _login(client):
    client.post("/auth/login", json={"username": "admin", "password": "Admin@123"})


def _select_smt_company(client):
    client.post("/select-company", data={"company_id": "1"})


def _coa_pam_row(sr):
    conn = get_conn()
    row = conn.execute(
        "SELECT id, coa_expense FROM coa_pam WHERE klasifikasi_sr=?", (sr,)
    ).fetchone()
    conn.close()
    return dict(row)


def test_save_smt_lines_route_creates_pam(client):
    _login(client)
    _select_smt_company(client)
    coa = _coa_pam_row("Beasiswa")
    resp = client.post("/payment-memo/ipay/save-smt-lines", json={
        "tanggal": "2026-07-06", "pam_no": "PAM-200-SMT-07-2026",
        "perusahaan": "PT. Sinar Mas Tjipta", "pillar": "SMT", "transaksi": "gl",
        "rows": [{"coa_pam_id": coa["id"], "klasifikasi_sr": "Beasiswa",
                   "klasifikasi_mr": "Scholarship Expense", "gl_account": coa["coa_expense"],
                   "tipe_dokumen": "Invoice Payment – Non PO Invoice", "no_invoice": "INV-1",
                   "dpp": 100000, "ppn": 0, "cost_center": "POCCOM",
                   "budget_activity": "A", "keterangan": "Test"}],
    })
    data = resp.get_json()
    assert data["ok"] is True
    assert data["pam_no"] == "PAM-200-SMT-07-2026"


def test_pam_detail_route_includes_transaction_lines(client):
    _login(client)
    _select_smt_company(client)
    coa = _coa_pam_row("Beasiswa")
    client.post("/payment-memo/ipay/save-smt-lines", json={
        "tanggal": "2026-07-06", "pam_no": "PAM-201-SMT-07-2026",
        "perusahaan": "PT. Sinar Mas Tjipta", "pillar": "SMT", "transaksi": "gl",
        "rows": [{"coa_pam_id": coa["id"], "klasifikasi_sr": "Beasiswa",
                   "klasifikasi_mr": "Scholarship Expense", "gl_account": coa["coa_expense"],
                   "tipe_dokumen": "Downpayment to vendor", "no_invoice": "",
                   "dpp": 100000, "ppn": 0, "cost_center": "POCCOM",
                   "budget_activity": "A", "keterangan": "Test"}],
    })
    conn = get_conn()
    pam_id = conn.execute(
        "SELECT id FROM pam_records WHERE pam_no='PAM-201-SMT-07-2026'"
    ).fetchone()["id"]
    conn.close()

    resp = client.get(f"/payment-memo/pam/{pam_id}/detail")
    data = resp.get_json()
    assert data["ok"] is True
    assert len(data["data"]["transaction_lines"]) == 1
    assert data["data"]["transaction_lines"][0]["tipe_dokumen"] == "Downpayment to vendor"


def test_index_route_still_renders_for_smt_company(client):
    # coa_pam_list is passed into the render_template context in this task,
    # but the template doesn't consume it as a JS global until Task 6 — so
    # this only asserts the route still renders successfully with the new
    # context kwarg added, not that the data appears in the HTML yet.
    _login(client)
    _select_smt_company(client)
    resp = client.get("/payment-memo/")
    assert resp.status_code == 200
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd app && python -m pytest tests/test_pam_smt_lines_routes.py -v`
Expected: FAIL — 404 on `/ipay/save-smt-lines` (route doesn't exist), `KeyError: 'transaction_lines'`.

- [ ] **Step 3: Update imports**

In `app/modules/payment_memo/routes.py`, in the import block (lines 5-27), change line 8 from:

```python
    get_pam_list, get_coa_list, update_pam_gl_account,
```

to:

```python
    get_pam_list, get_coa_list, update_pam_gl_account,
    get_coa_pam_list, save_smt_pam_transaction, get_pam_transaction_lines,
```

- [ ] **Step 4: Extend `index()` context**

In `app/modules/payment_memo/routes.py`, in `index()` (line 62-83), add `coa_pam_list=get_coa_pam_list(),` to the `render_template(...)` call (right after the existing `vendor_list=get_vendors(),` line 74):

```python
        vendor_list=get_vendors(),
        coa_pam_list=get_coa_pam_list(),
```

- [ ] **Step 5: Extend `get_pam_detail_route`**

In `app/modules/payment_memo/routes.py`, change lines 188-197 from:

```python
@bp.route("/pam/<int:pam_id>/detail")
@jwt_html_required
def get_pam_detail_route(pam_id):
    company_id = session.get("company_id", 0)
    detail = get_pam_detail(pam_id, company_id)
    if not detail:
        return jsonify({"ok": False, "pesan": "PAM record tidak ditemukan."}), 404
    detail["payments"] = get_pam_payments(detail["pam_no"], company_id)
    detail["payments_detail"] = get_pam_payments_detail(detail["pam_no"], company_id)
    return jsonify({"ok": True, "data": detail})
```

to:

```python
@bp.route("/pam/<int:pam_id>/detail")
@jwt_html_required
def get_pam_detail_route(pam_id):
    company_id = session.get("company_id", 0)
    detail = get_pam_detail(pam_id, company_id)
    if not detail:
        return jsonify({"ok": False, "pesan": "PAM record tidak ditemukan."}), 404
    detail["payments"] = get_pam_payments(detail["pam_no"], company_id)
    detail["payments_detail"] = get_pam_payments_detail(detail["pam_no"], company_id)
    detail["transaction_lines"] = get_pam_transaction_lines(pam_id)
    return jsonify({"ok": True, "data": detail})
```

- [ ] **Step 6: Add the new save route**

In `app/modules/payment_memo/routes.py`, right after `ipay_save_others` (lines 672-679), add:

```python

@bp.route("/ipay/save-smt-lines", methods=["POST"])
@jwt_html_required
def ipay_save_smt_lines():
    data         = request.get_json(force=True) or {}
    company_id   = session.get("company_id", 0)
    company_code = session.get("company_code", "SMT")
    result = save_smt_pam_transaction(company_id, company_code, data)
    return jsonify(result)
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `cd app && python -m pytest tests/test_pam_smt_lines_routes.py -v`
Expected: PASS (3 tests)

- [ ] **Step 8: Run full existing suite to check for regressions**

Run: `cd app && python -m pytest tests/ -v`
Expected: PASS

- [ ] **Step 9: Commit**

```bash
git add app/modules/payment_memo/routes.py app/tests/test_pam_smt_lines_routes.py
git commit -m "feat: add /ipay/save-smt-lines route and expose transaction_lines on PAM detail"
```

---

### Task 4: Frontend — tab rename, drop Tipe PAM, Transaksi → GL/Advance, PAM regex bugfix

**Files:**
- Modify: `app/templates/payment_memo/index.html:97` (tab label)
- Modify: `app/templates/payment_memo/index.html:157-185` (Tipe PAM hide, Transaksi options)
- Modify: `app/templates/payment_memo/index.html:3449` (`_PAM_RE`)
- Modify: `app/templates/payment_memo/index.html:3400-3430` (`ipayReset` default tx for SMT)
- Modify: `app/templates/payment_memo/index.html:3519-3536` (`ipayOnTxChange` — add SMT type-sync + new panel key)

**Interfaces:**
- Produces: JS function `_smtSyncTypeFromTx()` — called from `ipayOnTxChange()` when `COMPANY_CODE === "SMT"`. Later tasks (5, 6) may extend it but must not rename it.
- Consumes (guarded, safe if not yet defined): `smtLinesRecalcGlAccounts()` (defined in Task 6).

- [ ] **Step 1: Rename the tab label**

In `app/templates/payment_memo/index.html`, change line 97 from:

```html
    <button class="tab-btn" data-tab="tab-smt" onclick="loadSMT()">SMT</button>
```

to:

```html
    <button class="tab-btn" data-tab="tab-smt" onclick="loadSMT()">PAM List</button>
```

- [ ] **Step 2: Hide "Tipe PAM" for SMT and change "Transaksi" options**

In `app/templates/payment_memo/index.html`, replace the entire block from the header grid open tag (line 157, `<div style="display:grid;grid-template-columns:120px 150px...`) through that grid's closing `</div>` (line 211, right before the second grid `<div style="display:grid;grid-template-columns:200px 1fr...` touched in Task 5) with:

```html
    <div style="display:grid;grid-template-columns:{{ '160px 160px minmax(200px,1fr) 180px' if company_code == 'SMT' else '120px 150px 160px minmax(200px,1fr) 180px' }};gap:.75rem;margin-bottom:.5rem;align-items:end;max-width:980px">
      {% if company_code == 'SMT' %}
      <select id="ipay-type" style="display:none">
        <option value="smt">SMT</option>
        <option value="advance">Advance</option>
      </select>
      {% else %}
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
      {% endif %}
      <div class="form-group" style="margin:0">
        <label>Transaksi</label>
        <select id="ipay-tx" onchange="ipayOnTxChange()"
                style="width:100%;border:1.5px solid #10b981;color:#065f46;font-weight:700;background:#ecfdf5">
          {% if company_code == 'SMT' %}
          <option value="gl">GL</option>
          <option value="advance">Advance</option>
          {% else %}
          {% for tx in transaksi_types %}
          <option value="{{ tx|lower|replace(' ','_') }}">{{ tx }}</option>
          {% endfor %}
          {% endif %}
        </select>
      </div>
      <div class="form-group" style="margin:0">
        <label>Tanggal</label>
        <input type="date" id="ipay-tgl" onchange="ipayFetchNextPamNo()">
      </div>
      <div class="form-group" style="margin:0">
        <label>No. PAM
          <span id="ipay-pam-type-badge" style="font-size:.65rem;color:#10b981;font-weight:400">(auto AGRI)</span>
          <span id="ipay-pam-manual-badge" style="display:none;font-size:.65rem;color:#f59e0b;font-weight:600;margin-left:.25rem">(manual)</span>
        </label>
        <input type="text" id="ipay-pam-full" placeholder="Memuat..."
               style="font-family:monospace;font-weight:700;color:#1d4ed8;border:1.5px solid #93c5fd;background:#f0f9ff"
               oninput="ipayValidatePamNo()"
               onblur="ipayCheckPamCollision()">
        <div id="ipay-pam-hint" style="display:none;font-size:.68rem;color:#dc2626;margin-top:.2rem"></div>
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

For SMT, the visible grid items are Transaksi, Tanggal, No. PAM, Perusahaan (4 items — the hidden `<select id="ipay-type">` has `display:none` so it is not a grid item and consumes no track), matching the 4-track `grid-template-columns` defined above for the SMT branch. For non-SMT (ETF), it's the original 5 visible items matching the original 5-track definition — unchanged behavior.

- [ ] **Step 3: Fix `_PAM_RE` to accept `SMT`**

In `app/templates/payment_memo/index.html`, change line 3449 from:

```js
const _PAM_RE = /^PAM-\d{3}-(ETF|APP|LAND|SETF)-\d{2}-\d{4}$/;
```

to:

```js
const _PAM_RE = /^PAM-\d{3}-(ETF|APP|LAND|SETF|SMT)-\d{2}-\d{4}$/;
```

- [ ] **Step 4: Fix `ipayReset()`'s default Transaksi value for SMT**

In `app/templates/payment_memo/index.html`, change lines 3400-3406 from:

```js
function ipayReset() {
  const txEl = document.getElementById("ipay-tx");
  // SMT/Advance only ever offer "others" in the Transaksi dropdown (see
  // the Jinja branch above) — "beasiswa" isn't a valid option there, so
  // resetting to it would leave the select on no option and show the
  // wrong panel via ipayOnTxChange()'s "|| 'beasiswa'" fallback.
  if (txEl) { txEl.value = (COMPANY_CODE === "SMT") ? "others" : "beasiswa"; ipayOnTxChange(); }
```

to:

```js
function ipayReset() {
  const txEl = document.getElementById("ipay-tx");
  // SMT offers "gl"/"advance" in the Transaksi dropdown (see the Jinja
  // branch above) — "beasiswa" isn't a valid option there, so resetting to
  // it would leave the select on no option and show the wrong panel via
  // ipayOnTxChange()'s "|| 'beasiswa'" fallback.
  if (txEl) { txEl.value = (COMPANY_CODE === "SMT") ? "gl" : "beasiswa"; ipayOnTxChange(); }
```

- [ ] **Step 5: Wire `ipayOnTxChange()` to derive the hidden Tipe PAM value from Transaksi**

In `app/templates/payment_memo/index.html`, change lines 3519-3536 from:

```js
function ipayOnTxChange() {
  const tx = document.getElementById("ipay-tx")?.value || "beasiswa";
  const panels = {
    "beasiswa":    "#ipay-panel-beasiswa",
    "klaim_medis": "#ipay-panel-klaim",
    "tagihan":     "#ipay-panel-others",
    "etf":         "#ipay-panel-others",
    "sponsor":     "#ipay-panel-others",
    "others":      "#ipay-panel-others",
  };
  ["#ipay-panel-beasiswa","#ipay-panel-klaim","#ipay-panel-others"].forEach(id => {
    const el = document.querySelector(id);
    if (el) el.style.display = "none";
  });
  const target = panels[tx] || "#ipay-panel-beasiswa";
  const el = document.querySelector(target);
  if (el) el.style.display = "";
}
```

to:

```js
function _smtSyncTypeFromTx() {
  const tx     = document.getElementById("ipay-tx")?.value || "gl";
  const typeEl = document.getElementById("ipay-type");
  const type   = (tx === "advance") ? "advance" : "smt";
  if (typeEl) typeEl.value = type;
  const lbl = _IPAY_LABEL[type] || type.toUpperCase();
  const badge = document.getElementById("ipay-pam-type-badge");
  if (badge) badge.textContent = `(auto ${lbl})`;
  const saveBtn = document.getElementById("ipay-save-btn");
  if (saveBtn) saveBtn.textContent = `\u{1F4BE} Simpan PAM ${lbl}`;
  const pillarEl = document.getElementById("ipay-pillar");
  if (pillarEl) pillarEl.value = type.toUpperCase();
  ipayFetchNextPamNo();
  if (typeof smtLinesRecalcGlAccounts === "function") smtLinesRecalcGlAccounts();
}

function ipayOnTxChange() {
  const tx = document.getElementById("ipay-tx")?.value || "beasiswa";
  if (COMPANY_CODE === "SMT") _smtSyncTypeFromTx();
  const panels = {
    "beasiswa":    "#ipay-panel-beasiswa",
    "klaim_medis": "#ipay-panel-klaim",
    "tagihan":     "#ipay-panel-others",
    "etf":         "#ipay-panel-others",
    "sponsor":     "#ipay-panel-others",
    "others":      "#ipay-panel-others",
    "gl":          "#ipay-panel-smt-lines",
    "advance":     "#ipay-panel-smt-lines",
  };
  ["#ipay-panel-beasiswa","#ipay-panel-klaim","#ipay-panel-others","#ipay-panel-smt-lines"].forEach(id => {
    const el = document.querySelector(id);
    if (el) el.style.display = "none";
  });
  const target = panels[tx] || "#ipay-panel-beasiswa";
  const el = document.querySelector(target);
  if (el) el.style.display = "";
}
```

*(`#ipay-panel-smt-lines` doesn't exist yet — it's created in Task 6. Referencing it here via `document.querySelector` is safe: `querySelector` on a nonexistent selector just returns `null`, and the `if (el)` guard skips it — no error, matches the existing `if (typeof klaimReset === "function")` defensive style already used elsewhere in this file at line 3427.)*

- [ ] **Step 6: Manual verification**

Run the dev server (`preview_start` or `python app/run.py`), log in as `admin`, select company **Sinar Mas Tjipta**, open **Payment Memo**:

1. Confirm the tab that used to say "SMT" now says **"PAM List"** and still opens the same list view.
2. Open the **Input** tab. Confirm there is **no visible "Tipe PAM" dropdown**.
3. Confirm **"Transaksi"** shows exactly two options: **GL** and **Advance**.
4. Manually type a valid SMT-format PAM number (e.g. `PAM-999-SMT-07-2026`) into the No. PAM field — confirm it is **not** rejected (border should NOT turn red, no "Format: PAM-054-ETF-06-2026" hint).
5. Switch Transaksi between GL and Advance — confirm the auto-badge next to "No. PAM" changes between `(auto SMT)` and `(auto Advance)`, and the Pillar box updates to `SMT`/`ADVANCE` accordingly.

- [ ] **Step 7: Commit**

```bash
git add app/templates/payment_memo/index.html
git commit -m "feat: rename SMT tab to PAM List, drop Tipe PAM selector, GL/Advance Transaksi"
```

---

### Task 5: Frontend — header "CC" box (vendor cost center, auto-fill)

**Files:**
- Modify: `app/templates/payment_memo/index.html:212-223` (header grid — add CC box)
- Modify: `app/templates/payment_memo/index.html:3251-3274` (`ipayVendorSearch` / `_vendorSuggRender` usage — populate CC on vendor select)
- Modify: `app/templates/payment_memo/index.html:3400-3430` (`ipayReset` — clear CC box)

**Interfaces:**
- Produces: DOM element `#ipay-cc` (readonly input, same visual pattern as `#ipay-pillar`).
- Consumes: `vendor.cost_center` (already present in every object returned by `get_vendors()` / `VENDOR_LIST`, per `app/modules/beasiswa/service.py:15-27`).

- [ ] **Step 1: Add the CC box to the header grid**

In `app/templates/payment_memo/index.html`, change lines 212-223 from:

```html
    <div style="display:grid;grid-template-columns:200px 1fr;gap:.75rem;margin-bottom:1rem;align-items:end;max-width:900px">
      <div class="form-group" style="margin:0">
        <label>Pillar</label>
        <input type="text" id="ipay-pillar" readonly placeholder="Auto dari vendor"
               style="background:#f3f4f6;cursor:default;color:#374151;font-weight:600">
      </div>
      <div class="form-group" style="margin:0">
        <label>Catatan Payment <span style="font-size:.65rem;color:var(--text-muted);font-weight:400">(tampil di tab PAM)</span></label>
        <input type="text" id="ipay-catatan" placeholder="Opsional — muncul di kolom Catatan PAM tab"
               style="border:1px solid #93c5fd;background:#fafeff">
      </div>
    </div>
```

to:

```html
    <div style="display:grid;grid-template-columns:200px 140px 1fr;gap:.75rem;margin-bottom:1rem;align-items:end;max-width:900px">
      <div class="form-group" style="margin:0">
        <label>Pillar</label>
        <input type="text" id="ipay-pillar" readonly placeholder="Auto dari vendor"
               style="background:#f3f4f6;cursor:default;color:#374151;font-weight:600">
      </div>
      <div class="form-group" style="margin:0">
        <label>CC</label>
        <input type="text" id="ipay-cc" readonly placeholder="Auto dari vendor"
               style="background:#f3f4f6;cursor:default;color:#374151;font-weight:600">
      </div>
      <div class="form-group" style="margin:0">
        <label>Catatan Payment <span style="font-size:.65rem;color:var(--text-muted);font-weight:400">(tampil di tab PAM)</span></label>
        <input type="text" id="ipay-catatan" placeholder="Opsional — muncul di kolom Catatan PAM tab"
               style="border:1px solid #93c5fd;background:#fafeff">
      </div>
    </div>
```

- [ ] **Step 2: Populate `#ipay-cc` when a vendor is selected**

In `app/templates/payment_memo/index.html`, find `function ipayVendorSearch()` (around line 3251) and `_vendorSuggRender` (around line 3227). Locate the `onSelect` callback passed to `_vendorSuggRender` inside `ipayVendorSearch` (near line 3263-3272):

```js
  _vendorSuggRender(hits, sugg, v => {
```

Immediately inside that callback (wherever `ipay-pillar`'s `.value` is currently being set from the vendor object `v`), add a line setting `#ipay-cc` from `v.cost_center`:

```js
  _vendorSuggRender(hits, sugg, v => {
    document.getElementById("ipay-cc").value = v.cost_center || "";
    // ... existing pillar-setting logic stays exactly as-is below this line
```

*(Read the exact existing callback body at that location before editing — the comment at line 3267 ("don't let the vendor's own (ETF-pillar) tag...") indicates SMT company already special-cases pillar assignment there; add the `ipay-cc` line without altering that existing logic.)*

- [ ] **Step 3: Clear `#ipay-cc` on reset**

In `app/templates/payment_memo/index.html`, in `ipayReset()` (the function touched in Task 4 Step 4), add a line clearing the CC box next to where `ipay-perusahaan` is cleared (line 3410-3411):

```js
  document.getElementById("ipay-perusahaan-search").value = "";
  document.getElementById("ipay-perusahaan").value = "";
  document.getElementById("ipay-cc").value = "";
```

- [ ] **Step 4: Manual verification**

On the Input tab for SMT company: search and select a vendor that has a known `cost_center` in the `vendors` table (e.g. one of the seeded `PT. Forestalestari Dwikarya` etc. — check `VENDOR_SEED` in `database.py` for a vendor+cost_center pair actually seeded for SMT's session). Confirm the new **"CC"** box auto-fills with that vendor's cost center immediately after selecting it, and clears when "+ Tambah Baris"/reset is triggered via a fresh Input tab load.

- [ ] **Step 5: Commit**

```bash
git add app/templates/payment_memo/index.html
git commit -m "feat: add auto-filled CC (vendor cost center) box to PAM Input header"
```

---

### Task 6: Frontend — GL/Advance itemized lines table (Jenis Biaya picker, GL auto, save wiring)

**Files:**
- Modify: `app/templates/payment_memo/index.html` (new panel HTML after `#ipay-panel-others`, ~line 345; new JS block after `ipaySaveOthers`, ~line 4344; `index()` context already provides `coa_pam_list` from Task 3)

**Interfaces:**
- Consumes: `COA_PAM_LIST` (new JS global, from `coa_pam_list` template context, Task 3), `POST /payment-memo/ipay/save-smt-lines` (Task 3).
- Produces: `smtLinesAddRow()`, `smtLinesReset()`, `smtLinesUpdateTotal()`, `smtLinesRecalcGlAccounts()` (referenced by Task 4's `_smtSyncTypeFromTx`), `ipaySaveSmtLines()`.

- [ ] **Step 1: Expose `COA_PAM_LIST` as a JS global**

In `app/templates/payment_memo/index.html`, right after line 1171 (`const SISWA_LIST  = {{ siswa_list | tojson }};`), add:

```js
const COA_PAM_LIST = {{ coa_pam_list | tojson }};
const SMT_PAM_COST_CENTERS = [
  "POCCOM","POEAMR","POICOM","POITDC","POSPON","TFOPEX","POCFAD","POOFFM",
  "POCPRO","POCSOS","POSMED","POITEC","POSENG","POSKHU - DF","POSKHU - JB",
  "POSKHU - LS","POSKHU - YP","POEDIR","POMDIN","POMDEX","PORLIT","TFDPLA",
  "TFECEM","TFEGGM","TFEDIR","TFEDUC","TFSCHO","TFSHSE","TFVOED","TFKHAR","TFFCON",
];
const SMT_PAM_TIPE_DOKUMEN = [
  "Downpayment to vendor",
  "Invoice Payment – Non PO Invoice",
  "Employee Advance / Reimbursement (Fund Transfer)",
];
```

- [ ] **Step 2: Add the new panel HTML**

In `app/templates/payment_memo/index.html`, right after the closing `</div>{# end ipay-panel-others #}` (line 345), add:

```html

{# ── Panel SMT Lines (GL / Advance itemized) ── #}
<div id="ipay-panel-smt-lines" style="display:none">
  <div class="table-wrap">
    <table id="smt-lines-table" style="min-width:1500px">
      <thead>
        <tr>
          <th style="min-width:200px">Jenis Biaya (SR)</th>
          <th style="min-width:200px">Jenis Biaya (MR)</th>
          <th style="min-width:110px">GL Account</th>
          <th style="min-width:220px">Tipe Dokumen</th>
          <th style="min-width:120px">No. Invoice</th>
          <th style="min-width:120px">DPP</th>
          <th style="min-width:100px">PPN</th>
          <th style="min-width:120px">Total</th>
          <th style="min-width:130px">Cost Center</th>
          <th style="min-width:150px">Budget Activity</th>
          <th style="min-width:200px">Keterangan</th>
          <th style="width:32px"></th>
        </tr>
      </thead>
      <tbody id="smt-lines-tbody">
        <tr id="smt-lines-empty-row">
          <td colspan="12" style="text-align:center;color:var(--text-muted)">Klik + Tambah Baris untuk mulai input.</td>
        </tr>
      </tbody>
      <tfoot>
        <tr>
          <td colspan="7" style="text-align:right;padding-right:.75rem;font-weight:600;font-size:.875rem">Total Amount:</td>
          <td id="smt-lines-total-amt" class="num-right" style="font-weight:700;color:#1a56db;white-space:nowrap">Rp 0</td>
          <td colspan="4"></td>
        </tr>
      </tfoot>
    </table>
  </div>
  <div style="display:flex;gap:.5rem;margin-top:.75rem;align-items:center">
    <button class="btn btn-secondary btn-sm" onclick="smtLinesAddRow()">+ Tambah Baris</button>
    <button id="smt-lines-save-btn" class="btn btn-primary" onclick="ipaySaveSmtLines()">
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" style="margin-right:.35rem;vertical-align:-.1em"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg>
      Simpan PAM
    </button>
  </div>
</div>{# end ipay-panel-smt-lines #}
```

- [ ] **Step 3: Add the JS logic**

In `app/templates/payment_memo/index.html`, right after `ipaySaveOthers()` ends (line 4344, right before the `// ── Input Klaim tab ──` comment), add:

```js
// ── Input SMT Lines (GL/Advance itemized) tab ────────────────────────────
let _smtLinesRowId = 0;

function smtLinesReset() {
  document.getElementById("smt-lines-tbody").innerHTML =
    `<tr id="smt-lines-empty-row"><td colspan="12" style="text-align:center;color:var(--text-muted)">Klik + Tambah Baris untuk mulai input.</td></tr>`;
  const el = document.getElementById("smt-lines-total-amt");
  if (el) el.textContent = "Rp 0";
  _smtLinesRowId = 0;
}

function smtLinesUpdateTotal() {
  let total = 0;
  document.getElementById("smt-lines-tbody").querySelectorAll("tr[data-rid]").forEach(tr => {
    total += (parseFloat(tr._inpDpp.value) || 0) + (parseFloat(tr._inpPpn.value) || 0);
  });
  const el = document.getElementById("smt-lines-total-amt");
  if (el) el.textContent = "Rp " + new Intl.NumberFormat("id-ID").format(total);
}

function _smtLinesUpdateRowTotal(tr) {
  const dpp = parseFloat(tr._inpDpp.value) || 0;
  const ppn = parseFloat(tr._inpPpn.value) || 0;
  tr._totalCell.textContent = "Rp " + new Intl.NumberFormat("id-ID").format(dpp + ppn);
  smtLinesUpdateTotal();
}

function _smtLinesGlAccountFor(coaRow) {
  const tx = document.getElementById("ipay-tx")?.value || "gl";
  if (!coaRow) return "";
  return (tx === "advance") ? (coaRow.coa_advance || "") : (coaRow.coa_expense || "");
}

function smtLinesRecalcGlAccounts() {
  document.getElementById("smt-lines-tbody").querySelectorAll("tr[data-rid]").forEach(tr => {
    if (!tr.dataset.coaPamId) return;
    const coaRow = COA_PAM_LIST.find(c => String(c.id) === tr.dataset.coaPamId);
    tr._inpGl.value = _smtLinesGlAccountFor(coaRow);
  });
}

function smtLinesAddRow() {
  const empty = document.getElementById("smt-lines-empty-row");
  if (empty) empty.remove();
  const rid = ++_smtLinesRowId;
  const tr = document.createElement("tr");
  tr.dataset.rid = rid;

  function td(child) { const d = document.createElement("td"); d.appendChild(child); return d; }
  function textInp(placeholder) {
    const i = document.createElement("input");
    i.type = "text"; i.placeholder = placeholder || "";
    i.style.cssText = "width:100%;box-sizing:border-box";
    return i;
  }
  function numInp() {
    const i = document.createElement("input");
    i.type = "number"; i.min = "0"; i.placeholder = "0";
    i.style.cssText = "width:100%;box-sizing:border-box;text-align:right";
    return i;
  }
  function selInp(options, placeholder) {
    const s = document.createElement("select");
    s.style.cssText = "width:100%;box-sizing:border-box";
    s.innerHTML = `<option value="">${placeholder}</option>` +
      options.map(o => `<option value="${o}">${o}</option>`).join("");
    return s;
  }

  // Jenis Biaya (SR) — search input + suggestion list
  const srWrap = document.createElement("div");
  srWrap.style.cssText = "position:relative";
  const srInp = textInp("Cari jenis biaya...");
  srInp.autocomplete = "off";
  const srSugg = document.createElement("div");
  srSugg.style.cssText = "display:none;position:fixed;z-index:9999;background:#fff;border:1px solid #93c5fd;border-radius:.375rem;max-height:240px;overflow-y:auto;box-shadow:0 6px 20px rgba(0,0,0,.15)";
  document.body.appendChild(srSugg);
  srInp.addEventListener("input", () => {
    const q = srInp.value.toLowerCase().trim();
    tr.dataset.coaPamId = "";
    if (!q) { srSugg.style.display = "none"; return; }
    const hits = COA_PAM_LIST.filter(c => c.klasifikasi_sr.toLowerCase().includes(q)).slice(0, 15);
    if (!hits.length) { srSugg.style.display = "none"; return; }
    srSugg.innerHTML = "";
    hits.forEach(c => {
      const d = document.createElement("div");
      d.style.cssText = "padding:6px 10px;cursor:pointer;font-size:12px;border-bottom:1px solid #f3f4f6";
      d.textContent = c.klasifikasi_sr;
      d.addEventListener("mousedown", () => {
        srInp.value = c.klasifikasi_sr;
        tr.dataset.coaPamId = String(c.id);
        tr._inpMr.value = c.klasifikasi_mr;
        tr._inpGl.value = _smtLinesGlAccountFor(c);
        srSugg.style.display = "none";
      });
      srSugg.appendChild(d);
    });
    const r = srInp.getBoundingClientRect();
    srSugg.style.top = (r.bottom + 2) + "px"; srSugg.style.left = r.left + "px"; srSugg.style.width = r.width + "px";
    srSugg.style.display = "block";
  });
  srInp.addEventListener("blur", () => setTimeout(() => { srSugg.style.display = "none"; }, 200));
  srWrap.appendChild(srInp);

  const mrInp = textInp("(auto)");
  const glInp = textInp("(auto)"); glInp.readOnly = true; glInp.style.background = "#f3f4f6";
  const tipeSel = selInp(SMT_PAM_TIPE_DOKUMEN, "— Tipe Dokumen —");
  const invInp = textInp("No. Invoice");
  const dppInp = numInp();
  const ppnInp = numInp();
  const totalCell = document.createElement("div");
  totalCell.style.cssText = "text-align:right;font-weight:700;color:#1a56db;white-space:nowrap";
  totalCell.textContent = "Rp 0";
  const ccSel = selInp(SMT_PAM_COST_CENTERS, "— Cost Center —");
  const activityInp = textInp("Budget Activity");
  const ketInp = textInp("Keterangan");

  dppInp.addEventListener("input", () => _smtLinesUpdateRowTotal(tr));
  ppnInp.addEventListener("input", () => _smtLinesUpdateRowTotal(tr));

  const delBtn = document.createElement("button");
  delBtn.className = "btn btn-sm"; delBtn.style.cssText = "background:#ef4444;color:#fff;padding:2px 8px";
  delBtn.textContent = "✕";
  delBtn.addEventListener("click", () => {
    srSugg.remove(); tr.remove();
    if (!document.getElementById("smt-lines-tbody").querySelector("tr[data-rid]")) smtLinesReset();
    smtLinesUpdateTotal();
  });

  tr._inpSr = srInp; tr._inpMr = mrInp; tr._inpGl = glInp; tr._inpDpp = dppInp; tr._inpPpn = ppnInp; tr._totalCell = totalCell;
  const totalTd = document.createElement("td"); totalTd.appendChild(totalCell);
  [td(srWrap), td(mrInp), td(glInp), td(tipeSel), td(invInp), td(dppInp), td(ppnInp),
   totalTd, td(ccSel), td(activityInp), td(ketInp), td(delBtn)]
    .forEach(cell => tr.appendChild(cell));

  tr._selTipe = tipeSel; tr._inpInv = invInp; tr._selCc = ccSel; tr._inpActivity = activityInp; tr._inpKet = ketInp;
  document.getElementById("smt-lines-tbody").appendChild(tr);
}

async function ipaySaveSmtLines() {
  if (!await confirmModal("Simpan PAM ini?")) return;

  const tanggal    = document.getElementById("ipay-tgl").value;
  const pam_no     = document.getElementById("ipay-pam-full").value.trim();
  const perusahaan = document.getElementById("ipay-perusahaan").value;
  const pillar     = document.getElementById("ipay-pillar").value;
  const transaksi  = document.getElementById("ipay-tx")?.value || "gl";

  if (!tanggal || !pam_no || pam_no === "Memuat...") {
    showToast("Tanggal dan No. PAM wajib ada.", "error"); return;
  }

  const rows = [...document.getElementById("smt-lines-tbody").querySelectorAll("tr[data-rid]")].map(tr => ({
    coa_pam_id:      tr.dataset.coaPamId ? parseInt(tr.dataset.coaPamId, 10) : null,
    klasifikasi_sr:  tr._inpSr.value,
    klasifikasi_mr:  tr._inpMr.value,
    gl_account:      tr._inpGl.value,
    tipe_dokumen:    tr._selTipe.value,
    no_invoice:      tr._inpInv.value,
    dpp:             parseFloat(tr._inpDpp.value) || 0,
    ppn:             parseFloat(tr._inpPpn.value) || 0,
    cost_center:     tr._selCc.value,
    budget_activity: tr._inpActivity.value,
    keterangan:      tr._inpKet.value,
  }));

  if (!rows.length) { showToast("Minimal 1 baris transaksi.", "error"); return; }
  if (rows.some(r => !r.klasifikasi_sr)) { showToast("Setiap baris wajib memilih Jenis Biaya.", "error"); return; }
  if (rows.some(r => r.dpp <= 0)) { showToast("Setiap baris wajib DPP lebih dari 0.", "error"); return; }
  if (rows.some(r => !r.keterangan.trim())) { showToast("Setiap baris wajib diisi Keterangan.", "error"); return; }

  const btn = document.getElementById("smt-lines-save-btn");
  if (btn) btn.disabled = true;
  showLoading("Menyimpan PAM...");
  let res;
  try {
    res = await apiFetch("/payment-memo/ipay/save-smt-lines", {
      method: "POST",
      body: JSON.stringify({ tanggal, pam_no, perusahaan, pillar, transaksi, rows })
    });
  } finally {
    hideLoading();
    if (btn) btn.disabled = false;
  }
  if (!res) return;
  const data = await res.json();
  showToast(data.pesan, data.ok ? "success" : "error");
  if (data.ok) {
    smtLinesReset();
    ipayReset();
    document.querySelector('[data-tab="tab-smt"]')?.click();
  }
}
```

- [ ] **Step 4: Wire `smtLinesReset()` into `ipayReset()`**

In `app/templates/payment_memo/index.html`, in `ipayReset()` (touched in Tasks 4-5), add a guarded call next to the existing `if (typeof othersReset === "function") othersReset();` line (line 3428):

```js
  if (typeof othersReset === "function") othersReset();
  if (typeof smtLinesReset === "function") smtLinesReset();
```

- [ ] **Step 5: Manual verification**

On the Input tab for SMT company:

1. Select **Transaksi = GL**. Click "+ Tambah Baris" twice. In row 1, type "Beasiswa" into Jenis Biaya (SR), select the suggestion — confirm MR auto-fills "Scholarship Expense" and GL Account auto-fills "70110230". Fill DPP=1000000, PPN=110000 — confirm row Total shows "Rp 1.110.000" and footer total updates.
2. Fill row 2 similarly with a different Jenis Biaya, Cost Center, Budget Activity, Keterangan.
3. Fill Tanggal, wait for No. PAM to auto-populate, select a Perusahaan (vendor).
4. Click "Simpan PAM", confirm the modal, verify success toast and that it navigates to the "PAM List" tab showing the new PAM.
5. Switch to **Transaksi = Advance**, pick a Jenis Biaya from the "Advance ..." rows (e.g. "Advance for Training") — confirm GL Account auto-fills from `coa_advance` (e.g. "16001300"), not `coa_expense`.
6. Confirm ETF company flows (Beasiswa/Klaim Medis/AGRI tabs) are visually and functionally unaffected.

- [ ] **Step 6: Commit**

```bash
git add app/templates/payment_memo/index.html
git commit -m "feat: add itemized GL/Advance lines table for SMT PAM input"
```

---

### Task 7: Frontend — Print Memo auto-checklist "Type of Request" from `tipe_dokumen`

**Files:**
- Modify: `app/templates/payment_memo/index.html:2953-2957` (`cbRow` usage — compute `checked` from `p.transaction_lines`)

**Interfaces:**
- Consumes: `p.transaction_lines` (now present on every `dmSelectPAM` fetch, from Task 3's `get_pam_detail_route` change).

- [ ] **Step 1: Compute the checkbox consensus and use it**

In `app/templates/payment_memo/index.html`, inside `dmRenderForm(p)`, find the three `cbRow(...)` calls (lines 2999-3001):

```js
    ${cbRow('dm-f-type-dp',  'Downpayment to vendor', false)}
    ${cbRow('dm-f-type-inv', 'Invoice Payment – Non PO Invoice', true)}
    ${cbRow('dm-f-type-adv', 'Employee Advance / Reimbursement (Fund Transfer)', false)}
```

Replace with:

```js
    ${cbRow('dm-f-type-dp',  'Downpayment to vendor', _dmTipeDokumenConsensus(p) === 'Downpayment to vendor')}
    ${cbRow('dm-f-type-inv', 'Invoice Payment – Non PO Invoice', _dmTipeDokumenConsensus(p) === 'Invoice Payment – Non PO Invoice')}
    ${cbRow('dm-f-type-adv', 'Employee Advance / Reimbursement (Fund Transfer)', _dmTipeDokumenConsensus(p) === 'Employee Advance / Reimbursement (Fund Transfer)')}
```

Then, right before `function dmRenderForm(p) {` (line 2934), add the helper function:

```js
function _dmTipeDokumenConsensus(p) {
  const lines = p.transaction_lines || [];
  const values = [...new Set(lines.map(l => l.tipe_dokumen).filter(Boolean))];
  return values.length === 1 ? values[0] : null;
}

```

- [ ] **Step 2: Manual verification**

Open the "Print Memo" tab, search for the PAM created in Task 6's manual verification (all lines sharing the same Tipe Dokumen). Confirm the matching "Type of Request" checkbox is pre-checked automatically. Create a second test PAM with two lines using **different** Tipe Dokumen values, confirm none of the three checkboxes are pre-checked for that one (user must pick manually, unchanged from today's behavior).

- [ ] **Step 3: Commit**

```bash
git add app/templates/payment_memo/index.html
git commit -m "feat: auto-check Print Memo Type of Request from PAM line tipe_dokumen"
```

---

### Task 8: Full regression pass

**Files:** none (verification only)

- [ ] **Step 1: Run the full backend test suite**

Run: `cd app && python -m pytest tests/ -v`
Expected: PASS — all existing tests plus the new ones from Tasks 1-3, zero regressions.

- [ ] **Step 2: Manual end-to-end walkthrough**

Using the running dev server:
1. SMT company: create one GL PAM and one Advance PAM through the full Input flow (multi-row, vendor CC auto-fill, Jenis Biaya auto-fill), confirm both appear correctly in "PAM List" with correct pillar/total, and Print Memo auto-checklists correctly for each.
2. ETF company: confirm Beasiswa, Klaim Medis, and AGRI/APP/LAND/SETF/ENERGY tabs and their Input flows are all unchanged and working (spot-check one save in each).
3. Confirm exporting Excel from the "PAM List" tab still works (unaffected by this change).

- [ ] **Step 3: Commit (if any fixups were needed)**

```bash
git add -A
git commit -m "fix: regression fixups from PAM SMT redesign end-to-end pass"
```

*(Skip this commit if step 2 required no code changes.)*
