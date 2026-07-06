# SMT PAM (SMT + Advance pillars) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Payment Approval Memo (PAM) support for Sinar Mas Tjipta (SMT, `company_id=1`) — two new pillars, `SMT` and `ADVANCE`, inside the existing `payment_memo` module — including the Advance→SMT realization cascade.

**Architecture:** Mirror the existing ETF pillar pattern (AGRI/APP/LAND/SETF) exactly: two new `*_pam_lines` tables, two new `pillar` values reusing all existing generic infrastructure (status flow, memo creation, PDF/Excel export, free-type "Others" input), and two new company-conditional tabs in `payment_memo/index.html`. One new piece of business logic: filling `tgl_paid` on an `ADVANCE` record cascades it into the `SMT` pillar.

**Tech Stack:** Flask, SQLite (raw SQL, no ORM), Jinja2, vanilla JS, pytest.

**Full design reference:** `docs/superpowers/specs/2026-07-06-smt-pam-advance-design.md`

## Global Constraints

- No changes to `pam_records` schema — only two new `pillar` values (`"SMT"`, `"ADVANCE"`).
- Do not touch ETF pillar behavior (AGRI/APP/LAND/SETF) — additive changes only.
- Advance prefix for PAM numbering is `"SMT"` (shares the same numbering sequence as the SMT tab, not a separate `"ADV"` sequence).
- Advance realization (`tgl_paid` filled) must flip `pam_records.pillar` from `"ADVANCE"` to `"SMT"`, create a new `smt_pam_lines` row (vendor carried over, `tgl_realisasi` = the `tgl_paid` value, 7 standard date columns empty), set `pam_records.status = 'complete'`, and leave the old `advance_pam_lines` row in place as an archive (never deleted).
- Tab **MR** and **PA for SMT** are out of scope for this plan.

---

### Task 1: Schema — `smt_pam_lines` and `advance_pam_lines` tables

**Files:**
- Modify: `app/database.py:308-322` (insert two new `CREATE TABLE` blocks + 2 indexes right after the existing pillar tables)
- Test: `app/tests/test_smt_pam.py` (new)

**Interfaces:**
- Produces: tables `smt_pam_lines` (columns: `id, pam_id, no_vendor, nama_vendor, tgl_terima_doc, tgl_proses, tgl_verifikasi_tax, tgl_approval_1, tgl_approval_2, tgl_approval_3, tgl_kirim, tgl_realisasi, created_at, updated_at`) and `advance_pam_lines` (columns: `id, pam_id, no_vendor, nama_vendor, tgl_received, tgl_a0, tgl_a1, tgl_a2, tgl_a3, tgl_a4, tgl_paid, created_at, updated_at`).

- [ ] **Step 1: Write the failing test**

Create `app/tests/test_smt_pam.py`:

```python
import os, sys, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config
config.DB_PATH = os.path.join(os.path.dirname(__file__), "test_smt_pam.db")

from database import init_db, get_conn

SMT_COMPANY_ID = 1


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


def test_smt_pam_lines_table_exists():
    conn = get_conn()
    cols = _columns(conn, "smt_pam_lines")
    conn.close()
    expected = ["id", "pam_id", "no_vendor", "nama_vendor",
                "tgl_terima_doc", "tgl_proses", "tgl_verifikasi_tax",
                "tgl_approval_1", "tgl_approval_2", "tgl_approval_3",
                "tgl_kirim", "tgl_realisasi", "created_at", "updated_at"]
    for col in expected:
        assert col in cols, f"Missing column: {col}"


def test_advance_pam_lines_table_exists():
    conn = get_conn()
    cols = _columns(conn, "advance_pam_lines")
    conn.close()
    expected = ["id", "pam_id", "no_vendor", "nama_vendor",
                "tgl_received", "tgl_a0", "tgl_a1", "tgl_a2", "tgl_a3",
                "tgl_a4", "tgl_paid", "created_at", "updated_at"]
    for col in expected:
        assert col in cols, f"Missing column: {col}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd app && python -m pytest tests/test_smt_pam.py -v`
Expected: FAIL — `sqlite3.OperationalError: no such table: smt_pam_lines`

- [ ] **Step 3: Add the tables to the DDL**

In `app/database.py`, right after the closing `);` of `setf_pam_lines` (line 322, immediately before `CREATE TABLE IF NOT EXISTS energy_pam_lines`), insert:

```sql
CREATE TABLE IF NOT EXISTS smt_pam_lines (
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
    tgl_realisasi      TEXT,
    created_at         TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at         TEXT
);

CREATE TABLE IF NOT EXISTS advance_pam_lines (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    pam_id         INTEGER NOT NULL REFERENCES pam_records(id) ON DELETE CASCADE,
    no_vendor      TEXT,
    nama_vendor    TEXT,
    tgl_received   TEXT,
    tgl_a0         TEXT,
    tgl_a1         TEXT,
    tgl_a2         TEXT,
    tgl_a3         TEXT,
    tgl_a4         TEXT,
    tgl_paid       TEXT,
    created_at     TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at     TEXT
);
```

Then, right after the existing index block (after line 393's `CREATE INDEX IF NOT EXISTS idx_energy_pam_lines_pam ...`), add:

```sql
CREATE INDEX IF NOT EXISTS idx_smt_pam_lines_pam      ON smt_pam_lines(pam_id);
CREATE INDEX IF NOT EXISTS idx_advance_pam_lines_pam  ON advance_pam_lines(pam_id);
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd app && python -m pytest tests/test_smt_pam.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add app/database.py app/tests/test_smt_pam.py
git commit -m "feat: add smt_pam_lines and advance_pam_lines tables"
```

---

### Task 2: Service layer — pillar registries + dynamic lines columns

**Files:**
- Modify: `app/modules/payment_memo/service.py:246-268` (`_PILLAR_LINES_TABLE`, `_IPAY_PAM_PREFIX`)
- Modify: `app/modules/payment_memo/service.py:272-335` (`get_pam_by_pillar`)
- Modify: `app/modules/payment_memo/service.py:336-373` (`upsert_pam_lines` — ALLOWED fields become pillar-aware)
- Test: `app/tests/test_smt_pam.py` (append)

**Interfaces:**
- Consumes: `_VALID_PILLARS` (derived from `_PILLAR_LINES_TABLE` keys, existing pattern), `get_conn()`, `_ts()` (existing helpers in `service.py`).
- Produces: `get_pam_by_pillar(company_id, pillar, ...) -> list` now works for `"SMT"` and `"ADVANCE"` (previously only AGRI/APP/LAND/SETF). `upsert_pam_lines(pam_id, pillar, data, company_id) -> dict` now accepts Advance's custom field names when `pillar == "ADVANCE"`.

- [ ] **Step 1: Write the failing tests**

Append to `app/tests/test_smt_pam.py`:

```python
from modules.payment_memo.service import get_pam_by_pillar, upsert_pam_lines, get_next_pam_no


def _seed_pam(conn, pam_no, pillar, company_id=SMT_COMPANY_ID):
    conn.execute(
        """INSERT INTO pam_records
           (company_id, pam_no, pam_date, gl_account, cost_center, pt,
            requestors_name, keterangan, mata_uang, dpp, ppn,
            total_amount, due_date, status, source, pillar)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (company_id, pam_no, "2026-07-01", "70110230", "1008C1POFF",
         "PT. Sinar Mas Tjipta", "Jany Turkanda", "Test",
         "IDR", 9000000, 0, 9000000, "2026-07-31", "open", "others", pillar)
    )
    conn.commit()
    return conn.execute(
        "SELECT id FROM pam_records WHERE pam_no=?", (pam_no,)
    ).fetchone()["id"]


def test_get_pam_by_pillar_smt():
    conn = get_conn()
    _seed_pam(conn, "PAM-001-SMT-07-2026", "SMT")
    conn.close()
    rows = get_pam_by_pillar(SMT_COMPANY_ID, "SMT")
    assert len(rows) == 1
    assert rows[0]["pillar"] == "SMT"
    assert rows[0]["no_vendor"] is None
    assert "tgl_realisasi" in rows[0]


def test_get_pam_by_pillar_advance_has_custom_columns():
    conn = get_conn()
    pam_id = _seed_pam(conn, "PAM-002-SMT-07-2026", "ADVANCE")
    conn.execute(
        """INSERT INTO advance_pam_lines (pam_id, no_vendor, nama_vendor, tgl_received)
           VALUES (?,?,?,?)""",
        (pam_id, "V-100", "PT. Maju Jaya", "2026-07-02")
    )
    conn.commit()
    conn.close()
    rows = get_pam_by_pillar(SMT_COMPANY_ID, "ADVANCE")
    assert len(rows) == 1
    assert rows[0]["no_vendor"]    == "V-100"
    assert rows[0]["nama_vendor"]  == "PT. Maju Jaya"
    assert rows[0]["tgl_received"] == "2026-07-02"
    assert rows[0]["tgl_a0"] is None
    assert rows[0]["tgl_paid"] is None


def test_upsert_pam_lines_smt_standard_fields():
    conn = get_conn()
    pam_id = _seed_pam(conn, "PAM-003-SMT-07-2026", "SMT")
    conn.close()
    result = upsert_pam_lines(pam_id, "SMT", {
        "no_vendor": "V-200", "nama_vendor": "PT. Sentosa",
        "tgl_terima_doc": "2026-07-03"
    }, SMT_COMPANY_ID)
    assert result["ok"] is True
    rows = get_pam_by_pillar(SMT_COMPANY_ID, "SMT")
    assert rows[0]["tgl_terima_doc"] == "2026-07-03"


def test_upsert_pam_lines_advance_custom_fields():
    conn = get_conn()
    pam_id = _seed_pam(conn, "PAM-004-SMT-07-2026", "ADVANCE")
    conn.close()
    result = upsert_pam_lines(pam_id, "ADVANCE", {
        "no_vendor": "V-300", "nama_vendor": "PT. Abadi",
        "tgl_received": "2026-07-04", "tgl_a0": "2026-07-05"
    }, SMT_COMPANY_ID)
    assert result["ok"] is True
    rows = get_pam_by_pillar(SMT_COMPANY_ID, "ADVANCE")
    assert rows[0]["tgl_received"] == "2026-07-04"
    assert rows[0]["tgl_a0"]       == "2026-07-05"


def test_upsert_pam_lines_advance_rejects_standard_field_names():
    conn = get_conn()
    pam_id = _seed_pam(conn, "PAM-005-SMT-07-2026", "ADVANCE")
    conn.close()
    result = upsert_pam_lines(pam_id, "ADVANCE", {
        "tgl_terima_doc": "2026-07-06"  # not a valid Advance field
    }, SMT_COMPANY_ID)
    assert result["ok"] is False


def test_smt_and_advance_share_pam_number_sequence():
    smt_no      = get_next_pam_no(SMT_COMPANY_ID, "SMT", "smt", "2026-07-01")
    advance_no  = get_next_pam_no(SMT_COMPANY_ID, "SMT", "advance", "2026-07-01")
    assert smt_no     == "PAM-001-SMT-07-2026"
    assert advance_no == "PAM-001-SMT-07-2026"  # same prefix, would collide if both were "open" same day — expected, matches confirmed design (shared sequence)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd app && python -m pytest tests/test_smt_pam.py -v`
Expected: FAIL — `get_pam_by_pillar` returns `[]` for `"SMT"`/`"ADVANCE"` (not in `_VALID_PILLARS` yet), `upsert_pam_lines` returns `{"ok": False, "pesan": "Pillar tidak valid: SMT"}`.

- [ ] **Step 3: Register the new pillars**

In `app/modules/payment_memo/service.py`, replace:

```python
_PILLAR_LINES_TABLE = {
    "AGRI":   "agri_pam_lines",
    "APP":    "app_pam_lines",
    "LAND":   "land_pam_lines",
    "SETF":   "setf_pam_lines",
}
_VALID_PILLARS = set(_PILLAR_LINES_TABLE)
```

with:

```python
_PILLAR_LINES_TABLE = {
    "AGRI":     "agri_pam_lines",
    "APP":      "app_pam_lines",
    "LAND":     "land_pam_lines",
    "SETF":     "setf_pam_lines",
    "SMT":      "smt_pam_lines",
    "ADVANCE":  "advance_pam_lines",
}
_VALID_PILLARS = set(_PILLAR_LINES_TABLE)

_STANDARD_LINE_FIELDS = [
    "no_vendor", "nama_vendor", "tgl_terima_doc", "tgl_proses",
    "tgl_verifikasi_tax", "tgl_approval_1", "tgl_approval_2",
    "tgl_approval_3", "tgl_kirim",
]
_ADVANCE_LINE_FIELDS = [
    "no_vendor", "nama_vendor", "tgl_received", "tgl_a0", "tgl_a1",
    "tgl_a2", "tgl_a3", "tgl_a4", "tgl_paid",
]
# Columns SELECTed per pillar in get_pam_by_pillar (SMT adds tgl_realisasi,
# which is system-set only — see _PILLAR_ALLOWED_FIELDS below, it is
# deliberately NOT user-editable via upsert_pam_lines).
_PILLAR_SELECT_FIELDS = {
    "ADVANCE": _ADVANCE_LINE_FIELDS,
    "SMT":     _STANDARD_LINE_FIELDS + ["tgl_realisasi"],
}
# Columns upsert_pam_lines is allowed to write per pillar.
_PILLAR_ALLOWED_FIELDS = {
    "ADVANCE": set(_ADVANCE_LINE_FIELDS),
}
_DEFAULT_ALLOWED_FIELDS = set(_STANDARD_LINE_FIELDS)
```

And update `_IPAY_PAM_PREFIX`:

```python
_IPAY_PAM_PREFIX = {
    "agri":     "ETF",
    "app":      "APP",
    "sml":      "LAND",
    "setf":     "SETF",
    "smt":      "SMT",
    "advance":  "SMT",
}
```

- [ ] **Step 4: Make `get_pam_by_pillar` build its lines columns per pillar**

Replace the `get_pam_by_pillar` function body's SELECT construction. Find:

```python
    tbl = _PILLAR_LINES_TABLE[pillar]
    sql = f"""
        SELECT pr.*,
               pl.id         AS lines_id,
               pl.no_vendor, pl.nama_vendor,
               pl.tgl_terima_doc, pl.tgl_proses, pl.tgl_verifikasi_tax,
               pl.tgl_approval_1, pl.tgl_approval_2, pl.tgl_approval_3,
               pl.tgl_kirim,
               sla.sub_total,
```

Replace with:

```python
    tbl         = _PILLAR_LINES_TABLE[pillar]
    line_fields = _PILLAR_SELECT_FIELDS.get(pillar, _STANDARD_LINE_FIELDS)
    line_select = ", ".join(f"pl.{f}" for f in line_fields)
    sql = f"""
        SELECT pr.*,
               pl.id         AS lines_id,
               {line_select},
               sla.sub_total,
```

(The rest of the function — the `sla` subquery, `WHERE pr.company_id = ? AND pr.pillar = ?`, and filter appending — is unchanged.)

- [ ] **Step 5: Make `upsert_pam_lines` use pillar-aware ALLOWED fields**

Find in `upsert_pam_lines`:

```python
    tbl = _PILLAR_LINES_TABLE[pillar]
    ALLOWED = {"no_vendor", "nama_vendor", "tgl_terima_doc", "tgl_proses",
               "tgl_verifikasi_tax", "tgl_approval_1", "tgl_approval_2",
               "tgl_approval_3", "tgl_kirim"}
    fields = {k: v for k, v in data.items() if k in ALLOWED}
```

Replace with:

```python
    tbl = _PILLAR_LINES_TABLE[pillar]
    ALLOWED = _PILLAR_ALLOWED_FIELDS.get(pillar, _DEFAULT_ALLOWED_FIELDS)
    fields = {k: v for k, v in data.items() if k in ALLOWED}
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd app && python -m pytest tests/test_smt_pam.py -v`
Expected: PASS (8 tests — the 2 from Task 1 plus 6 new ones)

- [ ] **Step 7: Run the full existing PAM test suite to confirm no regression**

Run: `cd app && python -m pytest tests/test_pam_standardization.py -v`
Expected: PASS (all existing tests still pass — AGRI/APP/LAND/SETF untouched)

- [ ] **Step 8: Commit**

```bash
git add app/modules/payment_memo/service.py app/tests/test_smt_pam.py
git commit -m "feat: register SMT/ADVANCE pillars with pillar-aware lines columns"
```

---

### Task 3: Service layer — Advance realization cascade

**Files:**
- Modify: `app/modules/payment_memo/service.py` (`upsert_pam_lines` — add cascade call; new `_convert_advance_to_smt` helper)
- Test: `app/tests/test_smt_pam.py` (append)

**Interfaces:**
- Consumes: `_convert_advance_to_smt(conn, pam_id, tgl_realisasi, now)` — internal helper, called only from `upsert_pam_lines`.
- Produces: filling `tgl_paid` via `upsert_pam_lines(pam_id, "ADVANCE", {"tgl_paid": "<date>"}, company_id)` now also flips `pam_records.pillar` to `"SMT"`, sets `status='complete'`, and inserts a `smt_pam_lines` row with `tgl_realisasi` set.

- [ ] **Step 1: Write the failing test**

Append to `app/tests/test_smt_pam.py`:

```python
def test_advance_realization_converts_to_smt():
    conn = get_conn()
    pam_id = _seed_pam(conn, "PAM-006-SMT-07-2026", "ADVANCE")
    conn.execute(
        """INSERT INTO advance_pam_lines (pam_id, no_vendor, nama_vendor, tgl_received)
           VALUES (?,?,?,?)""",
        (pam_id, "V-400", "PT. Karya Mandiri", "2026-07-01")
    )
    conn.commit()
    conn.close()

    result = upsert_pam_lines(pam_id, "ADVANCE", {"tgl_paid": "2026-07-10"}, SMT_COMPANY_ID)
    assert result["ok"] is True

    conn = get_conn()
    pr = conn.execute(
        "SELECT pillar, status FROM pam_records WHERE id=?", (pam_id,)
    ).fetchone()
    assert pr["pillar"] == "SMT"
    assert pr["status"] == "complete"

    smt_line = conn.execute(
        "SELECT no_vendor, nama_vendor, tgl_realisasi, tgl_terima_doc FROM smt_pam_lines WHERE pam_id=?",
        (pam_id,)
    ).fetchone()
    assert smt_line is not None
    assert smt_line["no_vendor"]     == "V-400"
    assert smt_line["nama_vendor"]   == "PT. Karya Mandiri"
    assert smt_line["tgl_realisasi"] == "2026-07-10"
    assert smt_line["tgl_terima_doc"] is None  # standard SMT stages start empty

    # Old advance_pam_lines row is archived, not deleted
    adv_line = conn.execute(
        "SELECT tgl_received, tgl_paid FROM advance_pam_lines WHERE pam_id=?", (pam_id,)
    ).fetchone()
    assert adv_line is not None
    assert adv_line["tgl_received"] == "2026-07-01"
    assert adv_line["tgl_paid"]     == "2026-07-10"
    conn.close()

    # Record no longer shows up under ADVANCE pillar queries
    rows = get_pam_by_pillar(SMT_COMPANY_ID, "ADVANCE")
    assert rows == []

    # ...but does show up under SMT pillar queries
    rows = get_pam_by_pillar(SMT_COMPANY_ID, "SMT")
    assert len(rows) == 1
    assert rows[0]["pam_no"] == "PAM-006-SMT-07-2026"


def test_advance_partial_update_without_tgl_paid_does_not_convert():
    conn = get_conn()
    pam_id = _seed_pam(conn, "PAM-007-SMT-07-2026", "ADVANCE")
    conn.close()
    result = upsert_pam_lines(pam_id, "ADVANCE", {"tgl_received": "2026-07-01"}, SMT_COMPANY_ID)
    assert result["ok"] is True
    conn = get_conn()
    pr = conn.execute("SELECT pillar, status FROM pam_records WHERE id=?", (pam_id,)).fetchone()
    conn.close()
    assert pr["pillar"] == "ADVANCE"
    assert pr["status"] == "open"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd app && python -m pytest tests/test_smt_pam.py -v -k conversion or realization`

Actually run the whole file since `-k` needs a real match:
Run: `cd app && python -m pytest tests/test_smt_pam.py::test_advance_realization_converts_to_smt -v`
Expected: FAIL — `pillar` stays `"ADVANCE"`, no `smt_pam_lines` row is created.

- [ ] **Step 3: Implement the cascade**

In `app/modules/payment_memo/service.py`, find the end of `upsert_pam_lines`:

```python
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

Replace with:

```python
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

    if pillar == "ADVANCE" and fields.get("tgl_paid"):
        _convert_advance_to_smt(conn, pam_id, fields["tgl_paid"], now)

    conn.commit()
    conn.close()
    return {"ok": True}


def _convert_advance_to_smt(conn, pam_id: int, tgl_realisasi: str, now: str) -> None:
    """Advance realized (tgl_paid filled) -> flip pillar to SMT.

    Carries vendor into a fresh smt_pam_lines row (7 standard stage dates
    start empty, tgl_realisasi records when the advance was realized).
    The old advance_pam_lines row is left in place as an archive — it is
    simply no longer reachable via get_pam_by_pillar('ADVANCE') once the
    pillar flips, since that query filters by pam_records.pillar.
    """
    adv = conn.execute(
        "SELECT no_vendor, nama_vendor FROM advance_pam_lines WHERE pam_id=?",
        (pam_id,)
    ).fetchone()
    no_vendor   = adv["no_vendor"]   if adv else None
    nama_vendor = adv["nama_vendor"] if adv else None
    conn.execute(
        "UPDATE pam_records SET pillar='SMT', status='complete', updated_at=? WHERE id=?",
        (now, pam_id)
    )
    conn.execute(
        """INSERT INTO smt_pam_lines (pam_id, no_vendor, nama_vendor, tgl_realisasi, created_at)
           VALUES (?,?,?,?,?)""",
        (pam_id, no_vendor, nama_vendor, tgl_realisasi, now)
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd app && python -m pytest tests/test_smt_pam.py -v`
Expected: PASS (all 10 tests)

- [ ] **Step 5: Run the full existing PAM test suite to confirm no regression**

Run: `cd app && python -m pytest tests/test_pam_standardization.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add app/modules/payment_memo/service.py app/tests/test_smt_pam.py
git commit -m "feat: cascade Advance realization (tgl_paid) into SMT pillar"
```

---

### Task 4: Template — company-conditional tab bar and Input form

**Files:**
- Modify: `app/templates/payment_memo/index.html:94-100` (tab bar)
- Modify: `app/templates/payment_memo/index.html:154-161` (Tipe PAM dropdown)
- Modify: `app/templates/payment_memo/index.html:164-170` (Transaksi dropdown)
- Modify: `app/templates/payment_memo/index.html` (JS: `_IPAY_LABEL`, `ipayOnTypeChange`, `ipayVendorSearch`)

**Interfaces:**
- Consumes: `company_code` (already passed into the template via `_ctx()` in `routes.py`), `COMPANY_CODE` JS constant (already defined at line 1019: `const COMPANY_CODE = "{{ company_code }}";`).
- Produces: for `company_code == 'SMT'`, tab bar shows Open PAM / Input / SMT / Advance / Print Memo (no AGRI/APP/LAND/SETF); Input's Tipe PAM dropdown shows SMT/Advance; Transaksi dropdown is locked to "Others" only; the Pillar field is driven directly by the Tipe PAM selection instead of vendor auto-fill.

- [ ] **Step 1: Branch the tab bar**

Replace (lines 93-101):

```html
  <div class="tabs">
    <button class="tab-btn" data-tab="tab-draft-pay">Open PAM ({{ drafts|length }})</button>
    <button class="tab-btn" data-tab="tab-input-payment" onclick="ipayReset()">Input</button>
    <button class="tab-btn" data-tab="tab-pam" onclick="loadPAM()">AGRI</button>
    <button class="tab-btn" data-tab="tab-fiori" onclick="loadFIORI()">APP</button>
    <button class="tab-btn" data-tab="tab-sml" onclick="loadSML()">LAND</button>
    <button class="tab-btn" data-tab="tab-setf" onclick="loadSETF()">SETF</button>
    <button class="tab-btn" data-tab="tab-draft-memo">Print Memo</button>
  </div>
```

with:

```html
  <div class="tabs">
    <button class="tab-btn" data-tab="tab-draft-pay">Open PAM ({{ drafts|length }})</button>
    <button class="tab-btn" data-tab="tab-input-payment" onclick="ipayReset()">Input</button>
    {% if company_code == 'SMT' %}
    <button class="tab-btn" data-tab="tab-smt" onclick="loadSMT()">SMT</button>
    <button class="tab-btn" data-tab="tab-advance" onclick="loadAdvance()">Advance</button>
    {% else %}
    <button class="tab-btn" data-tab="tab-pam" onclick="loadPAM()">AGRI</button>
    <button class="tab-btn" data-tab="tab-fiori" onclick="loadFIORI()">APP</button>
    <button class="tab-btn" data-tab="tab-sml" onclick="loadSML()">LAND</button>
    <button class="tab-btn" data-tab="tab-setf" onclick="loadSETF()">SETF</button>
    {% endif %}
    <button class="tab-btn" data-tab="tab-draft-memo">Print Memo</button>
  </div>
```

Note: the SMT branch uses a distinct `data-tab="tab-smt"` / `onclick="loadSMT()"` — it must **not** reuse `id="tab-pam"` / `loadPAM()`, since that panel and function are hardcoded to the `"AGRI"` pillar and its frozen-column CSS (`#pam-table`). Task 5 adds the matching `#tab-smt` panel and `loadSMT()` function.

- [ ] **Step 2: Branch the Tipe PAM dropdown**

Replace (lines 154-161):

```html
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
```

with:

```html
      <div class="form-group" style="margin:0">
        <label>Tipe PAM</label>
        <select id="ipay-type" onchange="ipayOnTypeChange()"
                style="width:100%;border:1.5px solid #3b82f6;color:#1d4ed8;font-weight:700;background:#eff6ff">
          {% if company_code == 'SMT' %}
          <option value="smt">SMT</option>
          <option value="advance">Advance</option>
          {% else %}
          <option value="agri">AGRI</option>
          <option value="app">APP</option>
          <option value="sml">LAND</option>
          <option value="setf">SETF</option>
          {% endif %}
        </select>
      </div>
```

- [ ] **Step 3: Lock the Transaksi dropdown to "Others" for SMT**

Replace (lines 164-170):

```html
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

with:

```html
      <div class="form-group" style="margin:0">
        <label>Transaksi</label>
        <select id="ipay-tx" onchange="ipayOnTxChange()"
                style="width:100%;border:1.5px solid #10b981;color:#065f46;font-weight:700;background:#ecfdf5">
          {% if company_code == 'SMT' %}
          <option value="others">Others</option>
          {% else %}
          {% for tx in transaksi_types %}
          <option value="{{ tx|lower|replace(' ','_') }}">{{ tx }}</option>
          {% endfor %}
          {% endif %}
        </select>
      </div>
```

(SMT's Input is free-type only — Beasiswa/Klaim Medis are ETF-specific concepts backed by student/PA tables that don't apply to SMT. Locking to "Others" routes every SMT save through the existing `save_others_payment` free-type flow, matching the confirmed design.)

- [ ] **Step 4: Update `_IPAY_LABEL` and wire Tipe PAM directly to Pillar for SMT**

Find (around line 3235):

```javascript
const _IPAY_LABEL = { agri: 'AGRI', app: 'APP', sml: 'LAND', setf: 'SETF' };
```

Replace with:

```javascript
const _IPAY_LABEL = { agri: 'AGRI', app: 'APP', sml: 'LAND', setf: 'SETF', smt: 'SMT', advance: 'Advance' };
```

Find `ipayOnTypeChange` (around line 3236):

```javascript
function ipayOnTypeChange() {
  const type  = document.getElementById("ipay-type")?.value || "agri";
  const lbl   = _IPAY_LABEL[type] || type.toUpperCase();
  const badge = document.getElementById("ipay-pam-type-badge");
  if (badge) badge.textContent = `(auto ${lbl})`;
  const saveBtn = document.getElementById("ipay-save-btn");
  if (saveBtn) saveBtn.textContent = `\u{1F4BE} Simpan PAM ${lbl}`;
  ipayReset();
}
```

Replace with:

```javascript
function ipayOnTypeChange() {
  const type  = document.getElementById("ipay-type")?.value || "agri";
  const lbl   = _IPAY_LABEL[type] || type.toUpperCase();
  const badge = document.getElementById("ipay-pam-type-badge");
  if (badge) badge.textContent = `(auto ${lbl})`;
  const saveBtn = document.getElementById("ipay-save-btn");
  if (saveBtn) saveBtn.textContent = `\u{1F4BE} Simpan PAM ${lbl}`;
  // SMT/Advance are free-type: pillar comes directly from the Tipe PAM
  // choice, not from vendor auto-fill (see ipayVendorSearch below) —
  // there is no per-vendor pillar tagging concept for SMT's flow.
  if (COMPANY_CODE === "SMT") {
    const pillarEl = document.getElementById("ipay-pillar");
    if (pillarEl) pillarEl.value = type.toUpperCase();
  }
  ipayReset();
}
```

Find `ipayVendorSearch` (around line 2999):

```javascript
function ipayVendorSearch() {
  const inp  = document.getElementById("ipay-perusahaan-search");
  const sugg = document.getElementById("ipay-vendor-sugg");
  const q    = inp.value.toLowerCase().trim();
  if (!q) { sugg.style.display="none"; document.getElementById("ipay-perusahaan").value=""; document.getElementById("ipay-pillar").value=""; return; }
  const hits = VENDOR_LIST.filter(v => v.name.toLowerCase().includes(q)).slice(0,15);
  if (!hits.length) { sugg.style.display="none"; return; }
  _vendorSuggRender(hits, sugg, v => {
    document.getElementById("ipay-perusahaan-search").value = v.name;
    document.getElementById("ipay-perusahaan").value = v.name;
    document.getElementById("ipay-pillar").value = v.pillar;
    sugg.style.display = "none";
  });
  _vendorPos(inp, sugg); sugg.style.display = "block";
}
```

Replace with:

```javascript
function ipayVendorSearch() {
  const inp  = document.getElementById("ipay-perusahaan-search");
  const sugg = document.getElementById("ipay-vendor-sugg");
  const q    = inp.value.toLowerCase().trim();
  if (!q) {
    sugg.style.display="none";
    document.getElementById("ipay-perusahaan").value="";
    if (COMPANY_CODE !== "SMT") document.getElementById("ipay-pillar").value="";
    return;
  }
  const hits = VENDOR_LIST.filter(v => v.name.toLowerCase().includes(q)).slice(0,15);
  if (!hits.length) { sugg.style.display="none"; return; }
  _vendorSuggRender(hits, sugg, v => {
    document.getElementById("ipay-perusahaan-search").value = v.name;
    document.getElementById("ipay-perusahaan").value = v.name;
    // SMT/Advance: pillar stays whatever Tipe PAM set it to (see
    // ipayOnTypeChange) — don't let the vendor's own (ETF-pillar) tag
    // clobber it.
    if (COMPANY_CODE !== "SMT") document.getElementById("ipay-pillar").value = v.pillar;
    sugg.style.display = "none";
  });
  _vendorPos(inp, sugg); sugg.style.display = "block";
}
```

- [ ] **Step 5: Manual check (no automated test for template branching — verified in Task 7)**

This task only touches Jinja/JS wiring; defer functional verification to Task 7's browser walkthrough.

- [ ] **Step 6: Commit**

```bash
git add app/templates/payment_memo/index.html
git commit -m "feat: SMT-conditional tab bar and Input form (Tipe PAM, Transaksi, pillar wiring)"
```

---

### Task 5: Template — SMT tab panel

**Files:**
- Modify: `app/templates/payment_memo/index.html` (new `tab-smt` panel, placed where `tab-pam` currently sits, since Task 4 already repointed the SMT tab button to `data-tab="tab-smt"` / `onclick="loadSMT()"`)
- Modify: `app/templates/payment_memo/index.html` (JS: new `loadSMT()` function, `exportPillarExcel` prefix map)

Since the existing `tab-pam` panel (AGRI) is large (frozen-column CSS, bulk-bar, accordion detail rows) and none of that applies to SMT, **do not reuse it** — add a separate, simple panel mirroring the SETF tab exactly (search/filter/table/inline-edit, no frozen columns, no bulk bar), consistent with the spec's "mirror tab SETF" decision.

**Interfaces:**
- Consumes: `apiFetch`, `esc`, `fmtRupiah`, `skeletonRows`, `makeSortable`, `_statusBadge`, `_plDate`, `_aksiCell` (all existing shared helpers already used by `loadSETF`).
- Produces: `loadSMT()` (global function), `loadSMTDebounced()` (global function), tab panel `#tab-smt`.

- [ ] **Step 1: Add the `tab-smt` panel HTML**

Immediately before the `<!-- SETF Tab -->` block (i.e., right after the `tab-input-payment` panel's closing `</div>`, in the same position the AGRI/`tab-pam` panel currently occupies when `company_code != 'SMT'` — for `company_code == 'SMT'` this new block renders instead), add:

```html
  {% if company_code == 'SMT' %}
  <!-- SMT Tab -->
  <div class="tab-panel" id="tab-smt">
    <div class="filter-bar" style="display:flex;align-items:center;gap:6px;margin-bottom:10px;flex-wrap:wrap;padding-top:.5rem">
      <input id="smt-search" type="text" placeholder="Cari PAM No / PT / Keterangan..."
             style="padding:4px 8px;border:1px solid #d1d5db;border-radius:5px;font-size:12px;width:220px;"
             oninput="loadSMTDebounced()">
      <select id="smt-filter-bulan" onchange="loadSMTDebounced()"
              style="padding:4px 6px;border:1px solid #d1d5db;border-radius:5px;font-size:12px;width:80px">
        <option value="">Bulan</option>
        <option value="01">Jan</option><option value="02">Feb</option>
        <option value="03">Mar</option><option value="04">Apr</option>
        <option value="05">Mei</option><option value="06">Jun</option>
        <option value="07">Jul</option><option value="08">Agu</option>
        <option value="09">Sep</option><option value="10">Okt</option>
        <option value="11">Nov</option><option value="12">Des</option>
      </select>
      <select id="smt-filter-tahun" onchange="loadSMTDebounced()"
              style="padding:4px 6px;border:1px solid #d1d5db;border-radius:5px;font-size:12px;width:76px">
        <option value="">Tahun</option>
        <option value="2024">2024</option><option value="2025">2025</option>
        <option value="2026">2026</option><option value="2027">2027</option>
      </select>
      <select id="smt-filter-status" onchange="loadSMTDebounced()"
              style="padding:4px 6px;border:1px solid #d1d5db;border-radius:5px;font-size:11px;width:90px">
        <option value="">Semua Status</option>
        <option value="open">Open</option>
        <option value="on_process">On Process</option>
        <option value="complete">Complete</option>
      </select>
      <select id="smt-filter-source" onchange="loadSMTDebounced()"
              style="padding:4px 6px;border:1px solid #d1d5db;border-radius:5px;font-size:11px;width:90px">
        <option value="">Semua Source</option>
        <option value="others">Others</option>
      </select>
      <button class="btn btn-success btn-sm" onclick="exportPillarExcel('SMT')">&#8595; Export Excel</button>
      <span id="smt-count" style="font-size:11px;color:var(--text-muted)"></span>
    </div>
    <div class="pillar-table-wrap">
      <table id="smt-table" style="width:100%;border-collapse:collapse;font-size:12px;">
        <thead class="thead-primary">
          <tr>
            <th style="padding:7px 8px;white-space:nowrap">PAM No</th>
            <th style="padding:7px 8px;white-space:nowrap" data-sort="1">Tgl PAM</th>
            <th style="padding:7px 8px;white-space:nowrap">GL Account</th>
            <th style="padding:7px 8px;white-space:nowrap">Cost Center</th>
            <th style="padding:7px 8px;">PT</th>
            <th style="padding:7px 8px;">Requestor</th>
            <th style="padding:7px 8px;min-width:160px;">Keterangan</th>
            <th style="padding:7px 8px;white-space:nowrap">Mata Uang</th>
            <th style="padding:7px 8px;text-align:right;">DPP</th>
            <th style="padding:7px 8px;text-align:right;">PPN</th>
            <th style="padding:7px 8px;text-align:right;white-space:nowrap" data-sort="10" data-sort-type="num">Total (Rp)</th>
            <th style="padding:7px 8px;white-space:nowrap" data-sort="11">Due Date</th>
            <th style="padding:7px 8px;">Status</th>
            <th style="padding:7px 8px;white-space:nowrap">Tgl Bayar</th>
            <th style="padding:7px 8px;">Source</th>
            <th style="padding:7px 8px;white-space:nowrap">No. Vendor</th>
            <th style="padding:7px 8px;min-width:140px;">Nama Vendor</th>
            <th style="padding:7px 8px;white-space:nowrap">Terima Dok</th>
            <th style="padding:7px 8px;white-space:nowrap">Proses</th>
            <th style="padding:7px 8px;white-space:nowrap">Verif Tax</th>
            <th style="padding:7px 8px;white-space:nowrap">App 1</th>
            <th style="padding:7px 8px;white-space:nowrap">App 2</th>
            <th style="padding:7px 8px;white-space:nowrap">App 3</th>
            <th style="padding:7px 8px;white-space:nowrap">Kirim</th>
            <th style="padding:7px 8px;white-space:nowrap">Tgl Realisasi</th>
            <th style="padding:7px 8px;">Aksi</th>
          </tr>
        </thead>
        <tbody id="smt-tbody">
          <tr><td colspan="26" style="text-align:center;padding:20px;color:var(--text-muted);">Belum ada data SMT.</td></tr>
        </tbody>
      </table>
    </div>
  </div>
```

Do **not** add a closing `{% endif %}` yet — leave the `{% if company_code == 'SMT' %}` block open. Task 6 appends the Advance panel directly after this `</div>` and closes the block with a single `{% endif %}` there.

- [ ] **Step 2: Add `loadSMT()` JS**

Add right after the existing `loadSETF()` function:

```javascript
function loadSMTDebounced() { clearTimeout(_smtDebounce); _smtDebounce = setTimeout(loadSMT, 300); }
let _smtDebounce;
async function loadSMT() {
  const search  = (document.getElementById('smt-search')?.value || '').trim();
  const bulan   = (document.getElementById('smt-filter-bulan')?.value || '');
  const tahun   = (document.getElementById('smt-filter-tahun')?.value || '');
  const status  = (document.getElementById('smt-filter-status')?.value || '');
  const source  = (document.getElementById('smt-filter-source')?.value || '');
  const params  = new URLSearchParams({ search, bulan, tahun, status, source });
  const tbody  = document.getElementById('smt-tbody');
  tbody.innerHTML = skeletonRows(26);
  const res     = await apiFetch('/payment-memo/by-pillar/SMT?' + params);
  if (!res) return;
  const data   = await res.json();
  const count  = document.getElementById('smt-count');
  if (!data.ok || !data.rows.length) {
    tbody.innerHTML = '<tr><td colspan="26" style="text-align:center;padding:20px;color:var(--text-muted);">Belum ada data SMT.</td></tr>';
    if (count) count.textContent = '';
    return;
  }
  if (count) count.textContent = data.rows.length + ' baris';
  tbody.innerHTML = data.rows.map((r, i) => `
    <tr style="background:${i % 2 === 0 ? '#fff' : '#f8fafc'};">
      <td style="padding:6px 8px;font-weight:600;font-family:monospace;font-size:11px;white-space:nowrap">${esc(r.pam_no)}</td>
      <td style="padding:6px 8px;white-space:nowrap">${esc(r.pam_date || '-')}</td>
      <td style="padding:6px 8px;font-family:monospace;font-size:11px">${esc(r.gl_account || '-')}</td>
      <td style="padding:6px 8px;font-family:monospace;font-size:11px">${esc(r.cost_center || '-')}</td>
      <td style="padding:6px 8px">${esc(r.pt || '-')}</td>
      <td style="padding:6px 8px">${esc(r.requestors_name || '-')}</td>
      <td style="padding:6px 8px;max-width:160px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${esc(r.keterangan||'')}">${esc(r.keterangan || '-')}</td>
      <td style="padding:6px 8px">${esc(r.mata_uang || 'IDR')}</td>
      <td style="padding:6px 8px;text-align:right">${fmtRupiah(r.dpp)}</td>
      <td style="padding:6px 8px;text-align:right">${fmtRupiah(r.ppn)}</td>
      <td style="padding:6px 8px;text-align:right;font-weight:600">${fmtRupiah(r.total_amount)}</td>
      <td style="padding:6px 8px;white-space:nowrap">${esc(r.due_date || '-')}</td>
      <td style="padding:6px 8px">${_statusBadge(r.status)}</td>
      <td style="padding:6px 8px;white-space:nowrap">${esc(r.tanggal_bayar || '-')}</td>
      <td style="padding:6px 8px">${esc(r.source || '-')}</td>
      <td style="padding:6px 8px">${esc(r.no_vendor || '-')}</td>
      <td style="padding:6px 8px">${esc(r.nama_vendor || '-')}</td>
      ${_plDate(r.id,'SMT','tgl_terima_doc',r.tgl_terima_doc)}
      ${_plDate(r.id,'SMT','tgl_proses',r.tgl_proses)}
      ${_plDate(r.id,'SMT','tgl_verifikasi_tax',r.tgl_verifikasi_tax)}
      ${_plDate(r.id,'SMT','tgl_approval_1',r.tgl_approval_1)}
      ${_plDate(r.id,'SMT','tgl_approval_2',r.tgl_approval_2)}
      ${_plDate(r.id,'SMT','tgl_approval_3',r.tgl_approval_3)}
      ${_plDate(r.id,'SMT','tgl_kirim',r.tgl_kirim)}
      <td style="padding:6px 8px;white-space:nowrap;color:${r.tgl_realisasi ? 'var(--text)' : 'var(--text-muted)'}">${esc(r.tgl_realisasi || '-')}</td>
      <td style="padding:6px 8px">${_aksiCell(r)}</td>
    </tr>
  `).join('');
  makeSortable('smt-table');
}
```

(`tgl_realisasi` is rendered as plain text, not via `_plDate` — it is system-set by the Advance cascade only, never manually editable from the SMT tab, per the spec.)

- [ ] **Step 3: Wire `exportPillarExcel`**

Find:

```javascript
function exportPillarExcel(pillar) {
  const prefix = { AGRI: 'pam', APP: 'fiori', LAND: 'sml', SETF: 'setf' }[pillar] || 'pam';
```

Replace with:

```javascript
function exportPillarExcel(pillar) {
  const prefix = { AGRI: 'pam', APP: 'fiori', LAND: 'sml', SETF: 'setf', SMT: 'smt', ADVANCE: 'advance' }[pillar] || 'pam';
```

- [ ] **Step 4: Commit**

```bash
git add app/templates/payment_memo/index.html
git commit -m "feat: add SMT tab panel (loadSMT, mirrors SETF)"
```

---

### Task 6: Template — Advance tab panel

**Files:**
- Modify: `app/templates/payment_memo/index.html` (new `tab-advance` panel + `loadAdvance()` JS)

**Interfaces:**
- Consumes: same shared helpers as Task 5.
- Produces: `loadAdvance()` (global function), tab panel `#tab-advance`.

- [ ] **Step 1: Add the `tab-advance` panel HTML**

Add immediately after the `tab-smt` panel's closing `</div>` from Task 5 (still inside the `{% if company_code == 'SMT' %}` block — extend that same `{% if %}` rather than opening a new one):

```html
  <!-- Advance Tab -->
  <div class="tab-panel" id="tab-advance">
    <div class="filter-bar" style="display:flex;align-items:center;gap:6px;margin-bottom:10px;flex-wrap:wrap;padding-top:.5rem">
      <input id="advance-search" type="text" placeholder="Cari PAM No / PT / Keterangan..."
             style="padding:4px 8px;border:1px solid #d1d5db;border-radius:5px;font-size:12px;width:220px;"
             oninput="loadAdvanceDebounced()">
      <select id="advance-filter-bulan" onchange="loadAdvanceDebounced()"
              style="padding:4px 6px;border:1px solid #d1d5db;border-radius:5px;font-size:12px;width:80px">
        <option value="">Bulan</option>
        <option value="01">Jan</option><option value="02">Feb</option>
        <option value="03">Mar</option><option value="04">Apr</option>
        <option value="05">Mei</option><option value="06">Jun</option>
        <option value="07">Jul</option><option value="08">Agu</option>
        <option value="09">Sep</option><option value="10">Okt</option>
        <option value="11">Nov</option><option value="12">Des</option>
      </select>
      <select id="advance-filter-tahun" onchange="loadAdvanceDebounced()"
              style="padding:4px 6px;border:1px solid #d1d5db;border-radius:5px;font-size:12px;width:76px">
        <option value="">Tahun</option>
        <option value="2024">2024</option><option value="2025">2025</option>
        <option value="2026">2026</option><option value="2027">2027</option>
      </select>
      <select id="advance-filter-status" onchange="loadAdvanceDebounced()"
              style="padding:4px 6px;border:1px solid #d1d5db;border-radius:5px;font-size:11px;width:90px">
        <option value="">Semua Status</option>
        <option value="open">Open</option>
        <option value="on_process">On Process</option>
      </select>
      <button class="btn btn-success btn-sm" onclick="exportPillarExcel('ADVANCE')">&#8595; Export Excel</button>
      <span id="advance-count" style="font-size:11px;color:var(--text-muted)"></span>
    </div>
    <div class="pillar-table-wrap">
      <table id="advance-table" style="width:100%;border-collapse:collapse;font-size:12px;">
        <thead class="thead-primary">
          <tr>
            <th style="padding:7px 8px;white-space:nowrap">PAM No</th>
            <th style="padding:7px 8px;white-space:nowrap" data-sort="1">Tgl PAM</th>
            <th style="padding:7px 8px;">PT</th>
            <th style="padding:7px 8px;">Requestor</th>
            <th style="padding:7px 8px;min-width:160px;">Keterangan</th>
            <th style="padding:7px 8px;text-align:right;white-space:nowrap" data-sort="5" data-sort-type="num">Total (Rp)</th>
            <th style="padding:7px 8px;">Status</th>
            <th style="padding:7px 8px;white-space:nowrap">No. Vendor</th>
            <th style="padding:7px 8px;min-width:140px;">Nama Vendor</th>
            <th style="padding:7px 8px;white-space:nowrap">Received</th>
            <th style="padding:7px 8px;white-space:nowrap">A0 - S-JT</th>
            <th style="padding:7px 8px;white-space:nowrap">A1 - S-FS</th>
            <th style="padding:7px 8px;white-space:nowrap">A2 - S-YK</th>
            <th style="padding:7px 8px;white-space:nowrap">A3 - S-LL</th>
            <th style="padding:7px 8px;white-space:nowrap">A4 - A-LL</th>
            <th style="padding:7px 8px;white-space:nowrap">Paid</th>
            <th style="padding:7px 8px;">Aksi</th>
          </tr>
        </thead>
        <tbody id="advance-tbody">
          <tr><td colspan="17" style="text-align:center;padding:20px;color:var(--text-muted);">Belum ada data Advance.</td></tr>
        </tbody>
      </table>
    </div>
  </div>
  {% endif %}
```

The trailing `{% endif %}` closes the `{% if company_code == 'SMT' %}` block that Task 5 Step 1 opened and deliberately left open.

- [ ] **Step 2: Add `loadAdvance()` JS**

Add right after `loadSMT()`:

```javascript
function loadAdvanceDebounced() { clearTimeout(_advanceDebounce); _advanceDebounce = setTimeout(loadAdvance, 300); }
let _advanceDebounce;
async function loadAdvance() {
  const search  = (document.getElementById('advance-search')?.value || '').trim();
  const bulan   = (document.getElementById('advance-filter-bulan')?.value || '');
  const tahun   = (document.getElementById('advance-filter-tahun')?.value || '');
  const status  = (document.getElementById('advance-filter-status')?.value || '');
  const params  = new URLSearchParams({ search, bulan, tahun, status });
  const tbody  = document.getElementById('advance-tbody');
  tbody.innerHTML = skeletonRows(17);
  const res     = await apiFetch('/payment-memo/by-pillar/ADVANCE?' + params);
  if (!res) return;
  const data   = await res.json();
  const count  = document.getElementById('advance-count');
  if (!data.ok || !data.rows.length) {
    tbody.innerHTML = '<tr><td colspan="17" style="text-align:center;padding:20px;color:var(--text-muted);">Belum ada data Advance.</td></tr>';
    if (count) count.textContent = '';
    return;
  }
  if (count) count.textContent = data.rows.length + ' baris';
  tbody.innerHTML = data.rows.map((r, i) => `
    <tr style="background:${i % 2 === 0 ? '#fff' : '#f8fafc'};">
      <td style="padding:6px 8px;font-weight:600;font-family:monospace;font-size:11px;white-space:nowrap">${esc(r.pam_no)}</td>
      <td style="padding:6px 8px;white-space:nowrap">${esc(r.pam_date || '-')}</td>
      <td style="padding:6px 8px">${esc(r.pt || '-')}</td>
      <td style="padding:6px 8px">${esc(r.requestors_name || '-')}</td>
      <td style="padding:6px 8px;max-width:160px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${esc(r.keterangan||'')}">${esc(r.keterangan || '-')}</td>
      <td style="padding:6px 8px;text-align:right;font-weight:600">${fmtRupiah(r.total_amount)}</td>
      <td style="padding:6px 8px">${_statusBadge(r.status)}</td>
      <td style="padding:6px 8px">${esc(r.no_vendor || '-')}</td>
      <td style="padding:6px 8px">${esc(r.nama_vendor || '-')}</td>
      ${_plDate(r.id,'ADVANCE','tgl_received',r.tgl_received)}
      ${_plDate(r.id,'ADVANCE','tgl_a0',r.tgl_a0)}
      ${_plDate(r.id,'ADVANCE','tgl_a1',r.tgl_a1)}
      ${_plDate(r.id,'ADVANCE','tgl_a2',r.tgl_a2)}
      ${_plDate(r.id,'ADVANCE','tgl_a3',r.tgl_a3)}
      ${_plDate(r.id,'ADVANCE','tgl_a4',r.tgl_a4)}
      ${_plDate(r.id,'ADVANCE','tgl_paid',r.tgl_paid)}
      <td style="padding:6px 8px">${_aksiCell(r)}</td>
    </tr>
  `).join('');
  makeSortable('advance-table');
}
```

(Filling `tgl_paid` here calls the existing generic `PATCH /payment-memo/pam/<id>/lines` endpoint via `_plDate`/`pamLineDateEdit` — no new endpoint needed. That PATCH lands on `upsert_pam_lines`, which now runs the Task 3 cascade. On success, the row disappears from `#advance-tbody` on the next `loadAdvance()` call and shows up under `loadSMT()` instead.)

- [ ] **Step 3: Commit**

```bash
git add app/templates/payment_memo/index.html
git commit -m "feat: add Advance tab panel (loadAdvance, custom 7-stage columns)"
```

---

### Task 7: Manual browser verification

**Files:** none (verification only)

- [ ] **Step 1: Start the dev server and switch session to SMT company**

Start FinanceHub (`financehub` launch config, port from `.claude/launch.json`), log in, and use the company switcher to select **SMT**. Navigate to Payment Approval Memo.

- [ ] **Step 2: Confirm tab bar**

Verify tabs shown are exactly: Open PAM, Input, SMT, Advance, Print Memo (no AGRI/APP/LAND/SETF).

- [ ] **Step 3: Input an SMT record**

Go to Input tab. Confirm Tipe PAM shows SMT/Advance only, Transaksi shows only "Others". Select Tipe PAM = SMT, fill tanggal/vendor/keterangan/DPP, save. Confirm success toast and that PAM No looks like `PAM-001-SMT-<mm>-<yyyy>`.

- [ ] **Step 4: Confirm it appears in Open PAM and SMT tab**

Open the Open PAM tab — the new record should appear (status Open). Open the SMT tab — same record should appear via `loadSMT()`, with vendor/date columns editable inline.

- [ ] **Step 5: Input an Advance record and realize it**

Repeat Input with Tipe PAM = Advance. Confirm it appears in the Advance tab. Click into the "Paid" column, set a date, blur to save. Confirm toast "Tersimpan". Reload the Advance tab — the record should be gone. Reload the SMT tab — the record should now appear, with the 7 standard date columns empty and "Tgl Realisasi" populated with the date just entered.

- [ ] **Step 6: Confirm exports work**

Click "Export Excel" on both the SMT and Advance tabs — confirm a `.xlsx` downloads without a server error (check `preview_network`/server logs for a 200 on `/payment-memo/export/pam?pillar=SMT` and `?pillar=ADVANCE`).

- [ ] **Step 7: Confirm Print Memo works**

Go to Print Memo tab, search the SMT PAM No created in Step 3, confirm the memo preview renders and PDF export succeeds.

- [ ] **Step 8: Switch back to ETF and confirm no regression**

Switch company back to ETF. Confirm tab bar reverts to Open PAM/Input/AGRI/APP/LAND/SETF/Print Memo, and that an existing AGRI record still loads correctly in its tab (frozen columns, bulk bar, etc. all intact).

- [ ] **Step 9: Run full test suite one more time**

Run: `cd app && python -m pytest -v`
Expected: PASS (no regressions across the whole app)

- [ ] **Step 10: Commit any fixes found during manual verification**

If Steps 2-8 surface issues, fix them, re-verify, and commit with a message describing what was found (e.g. `fix: <what broke> found during SMT PAM browser verification`).
