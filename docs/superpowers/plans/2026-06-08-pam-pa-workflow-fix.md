# PAM ↔ Payment Application Workflow Fix — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix three workflow bugs so that PA records (etf_pa / app_pa / sml_pa) stay in sync with PAM: search only shows 'open' records, PAM creation fills `nomor_pam`, paid date fills `tanggal_bayar` and marks 'complete'.

**Architecture:** All fixes are backend-only. No schema changes to existing tables. Only `database.py` gains new `CREATE TABLE IF NOT EXISTS` blocks to make `app_pa`, `app_pa_lines`, and `sml_pa_lines` available in test DBs. Service logic in three files gets targeted additions.

**Tech Stack:** Python 3, Flask, SQLite (sqlite3), pytest

---

## Files Modified

| File | Change |
|---|---|
| `app/database.py` | Add app_pa, app_pa_lines, sml_pa_lines; fix sml_pa schema; add pam_records columns |
| `app/modules/etf_payment_application/service.py` | Fix status filter in get_draft_siswa + get_draft_lines_for_siswa |
| `app/modules/beasiswa/service.py` | Fill nomor_pam for all 3 PA tables after PAM creation |
| `app/modules/payment_memo/service.py` | Extend tanggal_bayar cascade + cancel revert to app_pa + sml_pa |
| `app/tests/test_etf_pa_service.py` | Add tests for status filter |
| `app/tests/test_beasiswa_service.py` | Add test for nomor_pam cascade |
| `app/tests/test_pam_pa_cascade.py` | New file: tests for tanggal_bayar cascade + cancel revert |

---

## Task 1: Fix migrate_db() — add missing PA tables for test compatibility

**Files:**
- Modify: `app/database.py:441-520` (migrate_db function)

The production DB has `app_pa`, `app_pa_lines`, `sml_pa_lines` and a student-based `sml_pa` (with `company_id`, `pa_number`, `nomor_pam`). The `migrate_db()` function is missing these, so tests can't exercise app_pa / sml_pa paths. Also `pam_records` needs `tanggal_bayar` and `source` columns.

- [ ] **Step 1: Locate the sml_pa block in database.py and replace it**

Find this block (around line 441):
```python
    # sml_pa table
    try:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS sml_pa (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                no_pa           TEXT UNIQUE NOT NULL,
                category        TEXT,
                ...
```

Replace the entire `# sml_pa table` block with:
```python
    # sml_pa table — student-based PA (same schema as etf_pa/app_pa)
    try:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS sml_pa (
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
                status                   TEXT NOT NULL DEFAULT 'open',
                created_at               TEXT NOT NULL,
                updated_at               TEXT)"""
        )
        conn.commit()
    except Exception:
        pass

    # sml_pa_lines table
    try:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS sml_pa_lines (
                id                   INTEGER PRIMARY KEY AUTOINCREMENT,
                pa_id                INTEGER NOT NULL REFERENCES sml_pa(id) ON DELETE CASCADE,
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

    # app_pa table — student-based PA for APP
    try:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS app_pa (
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
                status                   TEXT NOT NULL DEFAULT 'open',
                created_at               TEXT NOT NULL,
                updated_at               TEXT)"""
        )
        conn.commit()
    except Exception:
        pass

    # app_pa_lines table
    try:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS app_pa_lines (
                id                   INTEGER PRIMARY KEY AUTOINCREMENT,
                pa_id                INTEGER NOT NULL REFERENCES app_pa(id) ON DELETE CASCADE,
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

- [ ] **Step 2: Add ALTER TABLE for pam_records missing columns**

After the `app_pa_lines` block (still inside `migrate_db()`), add:
```python
    # pam_records — add tanggal_bayar and source if missing
    for col_def in [
        "tanggal_bayar TEXT",
        "source TEXT DEFAULT 'beasiswa'",
    ]:
        try:
            conn.execute(f"ALTER TABLE pam_records ADD COLUMN {col_def}")
            conn.commit()
        except Exception:
            pass
```

- [ ] **Step 3: Verify migrate_db creates all tables in a fresh DB**

```bash
cd app
python -c "
import config, os
config.DB_PATH = '/tmp/test_migrate.db'
from database import init_db, get_conn
init_db()
conn = get_conn()
tables = [r[0] for r in conn.execute(\"SELECT name FROM sqlite_master WHERE type='table' ORDER BY name\").fetchall()]
print(tables)
assert 'app_pa' in tables
assert 'app_pa_lines' in tables
assert 'sml_pa_lines' in tables
cols = [r[1] for r in conn.execute('PRAGMA table_info(sml_pa)').fetchall()]
assert 'pa_number' in cols, f'sml_pa still has wrong schema: {cols}'
assert 'nomor_pam' in cols
cols_pam = [r[1] for r in conn.execute('PRAGMA table_info(pam_records)').fetchall()]
assert 'tanggal_bayar' in cols_pam
assert 'source' in cols_pam
print('OK')
import os; os.remove('/tmp/test_migrate.db')
"
```

Expected: prints table list ending with `OK`.

- [ ] **Step 4: Commit**

```bash
git add app/database.py
git commit -m "fix: add app_pa, app_pa_lines, sml_pa_lines to migrate_db; fix sml_pa schema; add pam_records columns"
```

---

## Task 2: Fix status filter — show only 'open' PA records in student search

**Files:**
- Modify: `app/modules/etf_payment_application/service.py:175` (`get_draft_siswa`)
- Modify: `app/modules/etf_payment_application/service.py:196` (`get_draft_lines_for_siswa`)
- Test: `app/tests/test_etf_pa_service.py`

- [ ] **Step 1: Write the failing tests**

Add at the bottom of `app/tests/test_etf_pa_service.py`:
```python
from modules.etf_payment_application.service import (
    get_draft_siswa, get_draft_lines_for_siswa,
)


def _make_pa(conn, company_id: int, siswa_id: int, status: str) -> tuple[int, int]:
    """Insert one etf_pa + one line. Returns (pa_id, line_id)."""
    from datetime import datetime
    ts = datetime.now().isoformat(timespec="seconds")
    cur = conn.execute(
        """INSERT INTO etf_pa
           (company_id, pa_number, tgl_payment_application, status, created_at)
           VALUES (?,?,?,?,?)""",
        (company_id, f"PA/ETF/{status[:2]}/001/2026", "2026-06-01", status, ts)
    )
    pa_id = cur.lastrowid
    cur2 = conn.execute(
        """INSERT INTO etf_pa_lines
           (pa_id, student_id, jenis_pembayaran, jumlah_pembayaran)
           VALUES (?,?,?,?)""",
        (pa_id, siswa_id, "By Pendidikan", 5000000)
    )
    conn.commit()
    return pa_id, cur2.lastrowid


def test_get_draft_siswa_open_only():
    """Only 'open' PA records must appear in student search."""
    conn = get_conn()
    sid = _student_id("1230001")
    _make_pa(conn, COMPANY_ID, sid, "open")
    conn.close()

    results = get_draft_siswa(COMPANY_ID, "Budi")
    assert len(results) == 1
    assert results[0]["code"] == "1230001"


def test_get_draft_siswa_excludes_draft():
    """'draft' PA records must NOT appear — only 'open' is valid."""
    conn = get_conn()
    sid = _student_id("1230001")
    _make_pa(conn, COMPANY_ID, sid, "draft")
    conn.close()

    results = get_draft_siswa(COMPANY_ID, "Budi")
    assert results == [], "draft PA should be excluded from student search"


def test_get_draft_siswa_excludes_on_process():
    conn = get_conn()
    sid = _student_id("1230001")
    _make_pa(conn, COMPANY_ID, sid, "on_process")
    conn.close()

    results = get_draft_siswa(COMPANY_ID, "Budi")
    assert results == []


def test_get_draft_lines_open_only():
    conn = get_conn()
    sid = _student_id("1230001")
    pa_id, line_id = _make_pa(conn, COMPANY_ID, sid, "open")
    conn.close()

    lines = get_draft_lines_for_siswa(COMPANY_ID, sid)
    assert len(lines) == 1
    assert lines[0]["line_id"] == line_id


def test_get_draft_lines_excludes_draft():
    conn = get_conn()
    sid = _student_id("1230001")
    _make_pa(conn, COMPANY_ID, sid, "draft")
    conn.close()

    lines = get_draft_lines_for_siswa(COMPANY_ID, sid)
    assert lines == [], "draft PA lines should be excluded"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd app
python -m pytest tests/test_etf_pa_service.py::test_get_draft_siswa_excludes_draft tests/test_etf_pa_service.py::test_get_draft_lines_excludes_draft -v
```

Expected: FAIL (both pass with draft records returned).

- [ ] **Step 3: Apply the fix in service.py**

In `app/modules/etf_payment_application/service.py`, find `get_draft_siswa()` (~line 167):
```python
# BEFORE (line ~175):
            WHERE p.company_id = ? AND LOWER(p.status) IN ('open', 'draft')
```
Change to:
```python
# AFTER:
            WHERE p.company_id = ? AND LOWER(p.status) = 'open'
```

Find `get_draft_lines_for_siswa()` (~line 185):
```python
# BEFORE (line ~196):
            WHERE p.company_id = ? AND LOWER(p.status) IN ('open', 'draft')
              AND l.student_id = ?
```
Change to:
```python
# AFTER:
            WHERE p.company_id = ? AND LOWER(p.status) = 'open'
              AND l.student_id = ?
```

- [ ] **Step 4: Run all new tests and verify they pass**

```bash
cd app
python -m pytest tests/test_etf_pa_service.py -v
```

Expected: All pass including the 5 new tests.

- [ ] **Step 5: Commit**

```bash
git add app/modules/etf_payment_application/service.py \
        app/tests/test_etf_pa_service.py
git commit -m "fix: get_draft_siswa + get_draft_lines only return status='open' PA records"
```

---

## Task 3: Fill nomor_pam in all 3 PA tables when PAM is created

**Files:**
- Modify: `app/modules/beasiswa/service.py:396-434` (`add_payment_multi`)
- Test: `app/tests/test_beasiswa_service.py`

When `add_payment_multi()` runs, it already sets `etf_pa.status='on_process'` for linked PA records but never fills `nomor_pam`. The fix adds nomor_pam writes for all three PA tables after the PAM number is generated.

- [ ] **Step 1: Write the failing test**

Add to `app/tests/test_beasiswa_service.py`:
```python
def _seed_siswa_and_pa(conn, company_id: int) -> tuple[int, int, int]:
    """
    Insert one siswa + one etf_pa + one etf_pa_line.
    Returns (siswa_id, pa_id, line_id).
    """
    from datetime import datetime
    ts = datetime.now().isoformat(timespec="seconds")
    conn.execute(
        """INSERT INTO siswa
           (company_id, code, nama, jenjang, angkatan, program,
            fakultas, universitas, status)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (company_id, "1250001", "Budi Santoso", "S1", 2025,
         "SMART", "Teknik", "UI", "Aktif")
    )
    sid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    cur = conn.execute(
        """INSERT INTO etf_pa
           (company_id, pa_number, tgl_payment_application, status, created_at)
           VALUES (?,?,?,?,?)""",
        (company_id, "PA/ETF/001/2026", "2026-06-01", "open", ts)
    )
    pa_id = cur.lastrowid
    cur2 = conn.execute(
        """INSERT INTO etf_pa_lines
           (pa_id, student_id, jenis_pembayaran, jumlah_pembayaran)
           VALUES (?,?,?,?)""",
        (pa_id, sid, "By Pendidikan", 5000000)
    )
    line_id = cur2.lastrowid
    conn.commit()
    return sid, pa_id, line_id


def test_add_payment_multi_fills_nomor_pam_in_etf_pa():
    """
    After add_payment_multi() succeeds, etf_pa.nomor_pam must be
    filled with the auto-generated PAM number.
    """
    conn = get_conn()
    sid, pa_id, line_id = _seed_siswa_and_pa(conn, COMPANY_ID)
    conn.close()

    result = add_payment_multi(
        COMPANY_ID,
        "ETF",
        "2026-06-08",
        "AGRI",
        "PT. SMART Tbk",
        [{
            "siswa_code": "1250001",
            "cat1": "By Pendidikan",
            "cat2": "Semester 3",
            "amount": 5000000,
            "etf_pa_line_id": line_id,
        }],
    )
    assert result["ok"] is True
    pam_no = result["pam_no"]

    conn = get_conn()
    pa_row = conn.execute(
        "SELECT nomor_pam, status FROM etf_pa WHERE id=?", (pa_id,)
    ).fetchone()
    conn.close()

    assert pa_row["nomor_pam"] == pam_no, (
        f"etf_pa.nomor_pam expected '{pam_no}', got '{pa_row['nomor_pam']}'"
    )
    assert pa_row["status"] == "on_process"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd app
python -m pytest tests/test_beasiswa_service.py::test_add_payment_multi_fills_nomor_pam_in_etf_pa -v
```

Expected: FAIL — `etf_pa.nomor_pam` is None.

- [ ] **Step 3: Apply the fix in add_payment_multi()**

In `app/modules/beasiswa/service.py`, find this block (around line 396):
```python
        if pa_line_ids:
            ph = ",".join("?" * len(pa_line_ids))
            conn.execute(
                f"""UPDATE etf_pa SET status = 'on_process', updated_at = ?
                    WHERE id IN (
                        SELECT DISTINCT pa_id FROM etf_pa_lines WHERE id IN ({ph})
                    ) AND company_id = ? AND status = 'open'""",
                [_ts()] + pa_line_ids + [company_id]
            )
```

Replace with:
```python
        if pa_line_ids:
            ph = ",".join("?" * len(pa_line_ids))
            ts_op = _ts()
            for lines_tbl, pa_tbl in [
                ("etf_pa_lines", "etf_pa"),
                ("app_pa_lines", "app_pa"),
                ("sml_pa_lines", "sml_pa"),
            ]:
                conn.execute(
                    f"""UPDATE {pa_tbl} SET status = 'on_process', updated_at = ?
                        WHERE id IN (
                            SELECT DISTINCT pa_id FROM {lines_tbl} WHERE id IN ({ph})
                        ) AND company_id = ? AND status = 'open'""",
                    [ts_op] + pa_line_ids + [company_id]
                )
```

Then find the `pam_no = create_pam_record(...)` call (around line 421) and add the nomor_pam update immediately after `conn.commit()` — actually place it BEFORE the commit, right after `pam_no = create_pam_record(...)`:

```python
        pam_no = create_pam_record(conn, company_id, company_code, {
            "pam_date":     tanggal,
            "pt":           perusahaan,
            "keterangan":   keterangan,
            "total_amount": total,
            "payment_ids":  payment_ids,
        })

        # ── NEW: fill nomor_pam in all linked PA tables ──────────────
        if pa_line_ids and pam_no:
            ph = ",".join("?" * len(pa_line_ids))
            ts_pam = _ts()
            for lines_tbl, pa_tbl in [
                ("etf_pa_lines", "etf_pa"),
                ("app_pa_lines", "app_pa"),
                ("sml_pa_lines", "sml_pa"),
            ]:
                conn.execute(
                    f"""UPDATE {pa_tbl} SET nomor_pam = ?, updated_at = ?
                        WHERE id IN (
                            SELECT DISTINCT pa_id FROM {lines_tbl} WHERE id IN ({ph})
                        ) AND company_id = ?""",
                    [pam_no, ts_pam] + pa_line_ids + [company_id]
                )
        # ──────────────────────────────────────────────────────────────

        conn.commit()
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd app
python -m pytest tests/test_beasiswa_service.py::test_add_payment_multi_fills_nomor_pam_in_etf_pa -v
```

Expected: PASS.

- [ ] **Step 5: Run full beasiswa test suite to check no regressions**

```bash
cd app
python -m pytest tests/test_beasiswa_service.py -v
```

Expected: All pass.

- [ ] **Step 6: Commit**

```bash
git add app/modules/beasiswa/service.py \
        app/tests/test_beasiswa_service.py
git commit -m "fix: fill nomor_pam in etf_pa/app_pa/sml_pa when Beasiswa PAM is created"
```

---

## Task 4: Extend tanggal_bayar cascade to app_pa + sml_pa

**Files:**
- Modify: `app/modules/payment_memo/service.py:187-204` (`set_memo_tanggal_bayar`)
- Test: `app/tests/test_pam_pa_cascade.py` (new file)

Currently `set_memo_tanggal_bayar()` only cascades `tanggal_bayar + status='complete'` to `etf_pa`. Must also cascade to `app_pa` and `sml_pa`.

- [ ] **Step 1: Create new test file**

Create `app/tests/test_pam_pa_cascade.py`:
```python
# tests/test_pam_pa_cascade.py
"""
Tests for PA status cascade triggered by set_memo_tanggal_bayar and cancel_pam_record.
Covers etf_pa, app_pa, and sml_pa.
"""
import os, sys, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config
config.DB_PATH = os.path.join(os.path.dirname(__file__), "test_cascade.db")

from datetime import datetime
from database import init_db, get_conn
from modules.payment_memo.service import (
    set_memo_tanggal_bayar,
    cancel_pam_record,
    create_pam_from_etf_pa,
)

COMPANY_ID   = 2
COMPANY_CODE = "ETF"


@pytest.fixture(autouse=True)
def clean_db():
    if os.path.exists(config.DB_PATH):
        os.remove(config.DB_PATH)
    init_db()
    yield
    if os.path.exists(config.DB_PATH):
        os.remove(config.DB_PATH)


def _ts():
    return datetime.now().isoformat(timespec="seconds")


def _insert_siswa(conn) -> int:
    conn.execute(
        """INSERT INTO siswa
           (company_id, code, nama, jenjang, angkatan, program,
            fakultas, universitas, status)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (COMPANY_ID, "1250001", "Budi", "S1", 2025,
         "SMART", "Teknik", "UI", "Aktif")
    )
    sid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()
    return sid


def _insert_pa(conn, pa_tbl: str, lines_tbl: str,
               pa_prefix: str, siswa_id: int,
               status: str = "on_process") -> tuple[int, int]:
    """Insert one PA header + one line. Returns (pa_id, line_id)."""
    cur = conn.execute(
        f"""INSERT INTO {pa_tbl}
            (company_id, pa_number, tgl_payment_application, status, created_at)
            VALUES (?,?,?,?,?)""",
        (COMPANY_ID, f"PA/{pa_prefix}/001/2026", "2026-06-01", status, _ts())
    )
    pa_id = cur.lastrowid
    cur2 = conn.execute(
        f"""INSERT INTO {lines_tbl}
            (pa_id, student_id, jenis_pembayaran, jumlah_pembayaran)
            VALUES (?,?,?,?)""",
        (pa_id, siswa_id, "By Pendidikan", 5000000)
    )
    line_id = cur2.lastrowid
    conn.commit()
    return pa_id, line_id


def _insert_memo_and_payment(conn, line_id: int) -> int:
    """Insert payment_memo + payment_beasiswa linked to line_id. Returns memo_id."""
    conn.execute(
        "INSERT INTO payment_memo (company_id, memo_number, status) VALUES (?,?,?)",
        (COMPANY_ID, "PAM/ETF/2026/001", "on_process")
    )
    memo_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.execute(
        """INSERT INTO payment_beasiswa
           (company_id, siswa_code, cat1, cat2, tanggal, amount,
            pillar, perusahaan, memo_id, etf_pa_line_id, status)
           VALUES (?,?,?,?,?,?,?,?,?,?,'in_memo')""",
        (COMPANY_ID, "1250001", "By Pendidikan", "Semester 3",
         "2026-06-01", 5000000, "AGRI", "PT. SMART Tbk",
         memo_id, line_id)
    )
    conn.commit()
    return memo_id


# ── set_memo_tanggal_bayar cascade tests ────────────────────────────────────

def test_tanggal_bayar_cascades_to_etf_pa():
    conn = get_conn()
    sid = _insert_siswa(conn)
    pa_id, line_id = _insert_pa(conn, "etf_pa", "etf_pa_lines", "ETF", sid)
    memo_id = _insert_memo_and_payment(conn, line_id)
    conn.close()

    result = set_memo_tanggal_bayar(memo_id, "2026-06-15", COMPANY_ID)
    assert result["ok"] is True

    conn = get_conn()
    row = conn.execute(
        "SELECT status, tanggal_bayar FROM etf_pa WHERE id=?", (pa_id,)
    ).fetchone()
    conn.close()

    assert row["status"] == "complete"
    assert row["tanggal_bayar"] == "2026-06-15"


def test_tanggal_bayar_cascades_to_app_pa():
    conn = get_conn()
    sid = _insert_siswa(conn)
    pa_id, line_id = _insert_pa(conn, "app_pa", "app_pa_lines", "APP", sid)
    memo_id = _insert_memo_and_payment(conn, line_id)
    conn.close()

    result = set_memo_tanggal_bayar(memo_id, "2026-06-15", COMPANY_ID)
    assert result["ok"] is True

    conn = get_conn()
    row = conn.execute(
        "SELECT status, tanggal_bayar FROM app_pa WHERE id=?", (pa_id,)
    ).fetchone()
    conn.close()

    assert row["status"] == "complete", (
        f"app_pa.status expected 'complete', got '{row['status']}'"
    )
    assert row["tanggal_bayar"] == "2026-06-15"


def test_tanggal_bayar_cascades_to_sml_pa():
    conn = get_conn()
    sid = _insert_siswa(conn)
    pa_id, line_id = _insert_pa(conn, "sml_pa", "sml_pa_lines", "SML", sid)
    memo_id = _insert_memo_and_payment(conn, line_id)
    conn.close()

    result = set_memo_tanggal_bayar(memo_id, "2026-06-15", COMPANY_ID)
    assert result["ok"] is True

    conn = get_conn()
    row = conn.execute(
        "SELECT status, tanggal_bayar FROM sml_pa WHERE id=?", (pa_id,)
    ).fetchone()
    conn.close()

    assert row["status"] == "complete", (
        f"sml_pa.status expected 'complete', got '{row['status']}'"
    )
    assert row["tanggal_bayar"] == "2026-06-15"
```

- [ ] **Step 2: Run tests to verify they fail (app_pa and sml_pa tests)**

```bash
cd app
python -m pytest tests/test_pam_pa_cascade.py::test_tanggal_bayar_cascades_to_app_pa \
                 tests/test_pam_pa_cascade.py::test_tanggal_bayar_cascades_to_sml_pa -v
```

Expected: FAIL — app_pa/sml_pa not updated.

- [ ] **Step 3: Apply the fix in set_memo_tanggal_bayar()**

In `app/modules/payment_memo/service.py`, find this block inside `set_memo_tanggal_bayar()` (~line 186):
```python
    # 3. Cascade ke etf_pa
    lines = conn.execute(
        "SELECT DISTINCT etf_pa_line_id FROM payment_beasiswa WHERE memo_id=? AND etf_pa_line_id IS NOT NULL",
        (memo_id,)
    ).fetchall()
    line_ids = [r[0] for r in lines]

    if line_ids:
        ph = ",".join("?" * len(line_ids))
        conn.execute(
            f"""UPDATE etf_pa SET tanggal_bayar=?, status='complete', updated_at=?
                WHERE id IN (
                    SELECT DISTINCT pa_id FROM etf_pa_lines WHERE id IN ({ph})
                ) AND company_id=?""",
            [tanggal_bayar, now] + line_ids + [company_id]
        )
```

Replace with:
```python
    # 3. Cascade ke semua PA tables yang di-referensi
    lines = conn.execute(
        "SELECT DISTINCT etf_pa_line_id FROM payment_beasiswa WHERE memo_id=? AND etf_pa_line_id IS NOT NULL",
        (memo_id,)
    ).fetchall()
    line_ids = [r[0] for r in lines]

    if line_ids:
        ph = ",".join("?" * len(line_ids))
        for lines_tbl, pa_tbl in [
            ("etf_pa_lines", "etf_pa"),
            ("app_pa_lines", "app_pa"),
            ("sml_pa_lines", "sml_pa"),
        ]:
            conn.execute(
                f"""UPDATE {pa_tbl} SET tanggal_bayar=?, status='complete', updated_at=?
                    WHERE id IN (
                        SELECT DISTINCT pa_id FROM {lines_tbl} WHERE id IN ({ph})
                    ) AND company_id=?""",
                [tanggal_bayar, now] + line_ids + [company_id]
            )
```

- [ ] **Step 4: Run tests to verify all cascade tests pass**

```bash
cd app
python -m pytest tests/test_pam_pa_cascade.py -v -k "tanggal_bayar"
```

Expected: All 3 cascade tests pass.

- [ ] **Step 5: Commit**

```bash
git add app/modules/payment_memo/service.py \
        app/tests/test_pam_pa_cascade.py
git commit -m "fix: extend set_memo_tanggal_bayar cascade to app_pa and sml_pa"
```

---

## Task 5: Extend cancel_pam_record() and delete_payment_row() revert to app_pa + sml_pa

**Files:**
- Modify: `app/modules/payment_memo/service.py:417-448` (`cancel_pam_record` beasiswa branch)
- Modify: `app/modules/beasiswa/service.py:626-680` (`delete_payment_row`)
- Test: `app/tests/test_pam_pa_cascade.py` (add tests)

When a PAM is cancelled or a single payment row is deleted, the linked PA records must revert to `status='open'` and `nomor_pam=NULL`.

- [ ] **Step 1: Add cancel tests to test_pam_pa_cascade.py**

Append to `app/tests/test_pam_pa_cascade.py`:
```python
# ── cancel_pam_record revert tests ──────────────────────────────────────────

def _insert_pam_and_link(conn, pa_tbl: str, lines_tbl: str,
                          pa_id: int, line_id: int) -> tuple[int, str]:
    """Insert pam_records + payment_beasiswa with PAM link. Returns (pam_id, pam_no)."""
    pam_no = "PAM-001-ETF-06-2026"
    cur = conn.execute(
        """INSERT INTO pam_records
           (company_id, pam_no, pam_date, total_amount, status, created_at)
           VALUES (?,?,?,?,?,?)""",
        (COMPANY_ID, pam_no, "2026-06-08", 5000000, "draft", _ts())
    )
    pam_id = cur.lastrowid
    conn.execute(
        f"UPDATE {pa_tbl} SET nomor_pam=?, status='on_process' WHERE id=?",
        (pam_no, pa_id)
    )
    conn.execute(
        """INSERT INTO payment_beasiswa
           (company_id, siswa_code, cat1, cat2, tanggal, amount,
            pillar, perusahaan, pam, etf_pa_line_id, status)
           VALUES (?,?,?,?,?,?,?,?,?,?,'draft')""",
        (COMPANY_ID, "1250001", "By Pendidikan", "Semester 3",
         "2026-06-01", 5000000, "AGRI", "PT. SMART Tbk",
         pam_no, line_id)
    )
    conn.commit()
    return pam_id, pam_no


def test_cancel_pam_reverts_etf_pa():
    conn = get_conn()
    sid = _insert_siswa(conn)
    pa_id, line_id = _insert_pa(conn, "etf_pa", "etf_pa_lines", "ETF", sid, "on_process")
    pam_id, _ = _insert_pam_and_link(conn, "etf_pa", "etf_pa_lines", pa_id, line_id)
    conn.close()

    result = cancel_pam_record(pam_id, COMPANY_ID)
    assert result["ok"] is True

    conn = get_conn()
    row = conn.execute(
        "SELECT status, nomor_pam FROM etf_pa WHERE id=?", (pa_id,)
    ).fetchone()
    conn.close()

    assert row["status"] == "open"
    assert row["nomor_pam"] is None


def test_cancel_pam_reverts_app_pa():
    conn = get_conn()
    sid = _insert_siswa(conn)
    pa_id, line_id = _insert_pa(conn, "app_pa", "app_pa_lines", "APP", sid, "on_process")
    pam_id, _ = _insert_pam_and_link(conn, "app_pa", "app_pa_lines", pa_id, line_id)
    conn.close()

    result = cancel_pam_record(pam_id, COMPANY_ID)
    assert result["ok"] is True

    conn = get_conn()
    row = conn.execute(
        "SELECT status, nomor_pam FROM app_pa WHERE id=?", (pa_id,)
    ).fetchone()
    conn.close()

    assert row["status"] == "open", (
        f"app_pa.status expected 'open', got '{row['status']}'"
    )
    assert row["nomor_pam"] is None


def test_cancel_pam_reverts_sml_pa():
    conn = get_conn()
    sid = _insert_siswa(conn)
    pa_id, line_id = _insert_pa(conn, "sml_pa", "sml_pa_lines", "SML", sid, "on_process")
    pam_id, _ = _insert_pam_and_link(conn, "sml_pa", "sml_pa_lines", pa_id, line_id)
    conn.close()

    result = cancel_pam_record(pam_id, COMPANY_ID)
    assert result["ok"] is True

    conn = get_conn()
    row = conn.execute(
        "SELECT status, nomor_pam FROM sml_pa WHERE id=?", (pa_id,)
    ).fetchone()
    conn.close()

    assert row["status"] == "open", (
        f"sml_pa.status expected 'open', got '{row['status']}'"
    )
    assert row["nomor_pam"] is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd app
python -m pytest tests/test_pam_pa_cascade.py::test_cancel_pam_reverts_app_pa \
                 tests/test_pam_pa_cascade.py::test_cancel_pam_reverts_sml_pa -v
```

Expected: FAIL — app_pa/sml_pa status remains 'on_process'.

- [ ] **Step 3: Fix cancel_pam_record() beasiswa branch**

In `app/modules/payment_memo/service.py`, find the `else:` branch inside `cancel_pam_record()` (~line 416):

```python
    else:
        # Beasiswa flow (existing)
        lines = conn.execute(
            "SELECT DISTINCT etf_pa_line_id FROM payment_beasiswa WHERE pam=? AND company_id=? AND etf_pa_line_id IS NOT NULL",
            (pam_no, company_id)
        ).fetchall()
        line_ids = [r[0] for r in lines]

        conn.execute("DELETE FROM payment_beasiswa WHERE pam=? AND company_id=?", (pam_no, company_id))
        conn.execute("DELETE FROM pam_records WHERE id=? AND company_id=?", (pam_id, company_id))

        # Revert etf_pa ke draft jika tidak ada payment aktif lagi
        if line_ids:
            ph = ",".join("?" * len(line_ids))
            pa_ids = conn.execute(
                f"SELECT DISTINCT pa_id FROM etf_pa_lines WHERE id IN ({ph})", line_ids
            ).fetchall()
            for row in pa_ids:
                pa_id = row[0]
                remaining = conn.execute(
                    """SELECT COUNT(*) FROM payment_beasiswa pb
                       JOIN etf_pa_lines el ON el.id = pb.etf_pa_line_id
                       WHERE el.pa_id=? AND pb.company_id=?""",
                    (pa_id, company_id)
                ).fetchone()[0]
                if remaining == 0:
                    conn.execute(
                        "UPDATE etf_pa SET status='open', updated_at=? WHERE id=? AND company_id=?",
                        (now, pa_id, company_id)
                    )
```

Replace the entire `else:` branch with:
```python
    else:
        # Beasiswa flow
        lines = conn.execute(
            "SELECT DISTINCT etf_pa_line_id FROM payment_beasiswa WHERE pam=? AND company_id=? AND etf_pa_line_id IS NOT NULL",
            (pam_no, company_id)
        ).fetchall()
        line_ids = [r[0] for r in lines]

        conn.execute("DELETE FROM payment_beasiswa WHERE pam=? AND company_id=?", (pam_no, company_id))
        conn.execute("DELETE FROM pam_records WHERE id=? AND company_id=?", (pam_id, company_id))

        # Revert semua PA tables ke open jika tidak ada payment aktif lagi
        if line_ids:
            ph = ",".join("?" * len(line_ids))
            for lines_tbl, pa_tbl in [
                ("etf_pa_lines", "etf_pa"),
                ("app_pa_lines", "app_pa"),
                ("sml_pa_lines", "sml_pa"),
            ]:
                pa_rows = conn.execute(
                    f"SELECT DISTINCT pa_id FROM {lines_tbl} WHERE id IN ({ph})",
                    line_ids
                ).fetchall()
                for row in pa_rows:
                    pa_id_inner = row[0]
                    remaining = conn.execute(
                        f"""SELECT COUNT(*) FROM payment_beasiswa pb
                               JOIN {lines_tbl} el ON el.id = pb.etf_pa_line_id
                               WHERE el.pa_id=? AND pb.company_id=?""",
                        (pa_id_inner, company_id)
                    ).fetchone()[0]
                    if remaining == 0:
                        conn.execute(
                            f"UPDATE {pa_tbl} SET status='open', nomor_pam=NULL, updated_at=? "
                            f"WHERE id=? AND company_id=?",
                            (now, pa_id_inner, company_id)
                        )
```

- [ ] **Step 4: Fix delete_payment_row() in beasiswa/service.py**

In `app/modules/beasiswa/service.py`, find `delete_payment_row()` (~line 626). Find the etf_pa revert block (~line 655):

```python
    if line_id:
        conn.execute(...)
        pa_row = conn.execute(
            "SELECT pa_id FROM etf_pa_lines WHERE id=?", (line_id,)
        ).fetchone()
        if pa_row:
            pa_id = pa_row[0]
            remaining_pa = conn.execute(
                """SELECT COUNT(*) FROM payment_beasiswa pb
                   JOIN etf_pa_lines el ON el.id = pb.etf_pa_line_id
                   WHERE el.pa_id=? AND pb.company_id=?""",
                (pa_id, company_id)
            ).fetchone()[0]
            if remaining_pa == 0:
                from datetime import datetime as _dt
                ...
                conn.execute(
                    "UPDATE etf_pa SET status='open', updated_at=? WHERE id=? AND company_id=?",
```

Replace the `if line_id:` block (the PA revert part only — after deleting the payment row) with:
```python
    if line_id:
        # Revert PA record if no remaining payment rows reference it
        from datetime import datetime as _dt
        _now = _dt.now().isoformat(timespec="seconds")
        for lines_tbl, pa_tbl in [
            ("etf_pa_lines", "etf_pa"),
            ("app_pa_lines", "app_pa"),
            ("sml_pa_lines", "sml_pa"),
        ]:
            pa_row = conn.execute(
                f"SELECT pa_id FROM {lines_tbl} WHERE id=?", (line_id,)
            ).fetchone()
            if pa_row:
                pa_id = pa_row[0]
                remaining_pa = conn.execute(
                    f"""SELECT COUNT(*) FROM payment_beasiswa pb
                           JOIN {lines_tbl} el ON el.id = pb.etf_pa_line_id
                           WHERE el.pa_id=? AND pb.company_id=?""",
                    (pa_id, company_id)
                ).fetchone()[0]
                if remaining_pa == 0:
                    conn.execute(
                        f"UPDATE {pa_tbl} SET status='open', nomor_pam=NULL, updated_at=? "
                        f"WHERE id=? AND company_id=?",
                        (_now, pa_id, company_id)
                    )
```

> **Note:** You will need to read the full `delete_payment_row()` function carefully before editing to locate exactly which lines to replace. The function has pam_records deletion logic mixed in — only replace the PA-revert block, not the pam deletion logic.

- [ ] **Step 5: Run all cascade tests**

```bash
cd app
python -m pytest tests/test_pam_pa_cascade.py -v
```

Expected: All 6 tests pass (3 tanggal_bayar + 3 cancel).

- [ ] **Step 6: Run full test suite**

```bash
cd app
python -m pytest tests/ -v
```

Expected: All tests pass. Zero failures.

- [ ] **Step 7: Commit**

```bash
git add app/modules/payment_memo/service.py \
        app/modules/beasiswa/service.py \
        app/tests/test_pam_pa_cascade.py
git commit -m "fix: extend cancel_pam + delete_payment_row revert to app_pa and sml_pa"
```

---

## Self-Review Checklist

**Spec coverage:**
- [x] Status filter only 'open' → Task 2 (get_draft_siswa + get_draft_lines_for_siswa)
- [x] PAM submit → nomor_pam + on_process in all 3 tables → Task 3
- [x] Paid date cascade → complete + tanggal_bayar in all 3 tables → Task 4
- [x] Cancel revert → open + nomor_pam=NULL in all 3 tables → Task 5

**Placeholder scan:** No TBD/TODO. All code is complete.

**Type consistency:**
- `pa_line_ids` defined in Task 3 block is reused for nomor_pam update in same function — consistent.
- `line_ids` variable in `set_memo_tanggal_bayar` and `cancel_pam_record` — consistent with production variable names.
- `(lines_tbl, pa_tbl)` tuple pattern is consistent across Tasks 3, 4, 5.
