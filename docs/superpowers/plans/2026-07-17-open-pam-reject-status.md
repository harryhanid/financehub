# Open PAM Reject Status Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a "Reject" action (per-student and per-PAM-group) to the Open PAM tab that preserves data with `status='rejected'` instead of deleting it, and cascades the linked PA record to `status='rejected'` too (terminal, not reusable) — instead of today's "Hapus"/"Cancel" actions, which permanently delete the data and revert the PA back to `open`.

**Architecture:** Two new service functions (`reject_student_from_pam`, `reject_pam_record`) that mirror the exact control flow of the existing `remove_student_from_pam` / `cancel_pam_record`, swapping `DELETE` for `UPDATE ... SET status='rejected'`. A new `reject_reason TEXT` column is added to 7 tables via the existing idempotent migration pattern. Because rejected rows now persist instead of disappearing, 4 pre-existing "does this PA still have an active payment?" queries must be patched to exclude `status='rejected'` rows, or a rejected sibling would incorrectly block a PA from reverting to `open` later.

**Tech Stack:** Flask + SQLite (raw SQL, no ORM), Jinja2 templates with inline vanilla JS, pytest.

**Spec:** `docs/superpowers/specs/2026-07-17-open-pam-reject-status-design.md`

## Global Constraints

- Status value is exactly the lowercase string `rejected` (matches existing `open`/`on_process`/`complete`/`partial` convention — no other casing).
- `reject_reason` is always optional/nullable — never required at the database layer.
- No "reopen"/"un-reject" action is built in this plan (confirmed final via UI, per spec).
- Every new SQL query must be scoped by `company_id` (matches every existing query in these files — this codebase is multi-tenant per company).
- Follow TDD: write the failing test, run it, confirm the failure reason, implement, run again, confirm pass, commit.

---

## Task 1: Schema — add `reject_reason` column to 7 tables

**Files:**
- Modify: `app/database.py` (inside `migrate_db()`, right before the `conn.close()` at the end of that function — currently line 1296)
- Test: `app/tests/test_pam_pa_cascade.py` (new test, alongside the existing `test_payment_beasiswa_has_tgl_paid_columns` schema test at line 423)

**Interfaces:**
- Produces: every one of `payment_beasiswa`, `pam_records`, `etf_pa`, `app_pa`, `sml_pa`, `energy_pa`, `setf_pa` has a nullable `reject_reason TEXT` column after `init_db()` runs. No function signature changes.

- [ ] **Step 1: Write the failing test**

Add to `app/tests/test_pam_pa_cascade.py`, right after `test_payment_beasiswa_has_tgl_paid_columns` (after line 429):

```python
def test_reject_reason_column_exists_on_all_relevant_tables():
    conn = get_conn()
    for tbl in ("payment_beasiswa", "pam_records", "etf_pa", "app_pa",
                "sml_pa", "energy_pa", "setf_pa"):
        cols = [row[1] for row in conn.execute(f"PRAGMA table_info({tbl})").fetchall()]
        assert "reject_reason" in cols, f"Missing reject_reason in {tbl}"
    conn.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd app && python -m pytest tests/test_pam_pa_cascade.py::test_reject_reason_column_exists_on_all_relevant_tables -v`
Expected: FAIL — `AssertionError: Missing reject_reason in payment_beasiswa`

- [ ] **Step 3: Add the migration**

In `app/database.py`, find the end of `migrate_db()` (currently these are the last lines of the function, right before it closes the connection):

```python
    conn.commit()

    conn.close()


def init_db():
```

Replace with:

```python
    conn.commit()

    # reject_reason — optional free-text note captured when a payment/PAM/PA is
    # rejected (2026-07-17). Nullable on every table that can carry a
    # status='rejected' row.
    for _tbl in ("payment_beasiswa", "pam_records", "etf_pa", "app_pa",
                 "sml_pa", "energy_pa", "setf_pa"):
        try:
            conn.execute(f"ALTER TABLE {_tbl} ADD COLUMN reject_reason TEXT")
            conn.commit()
        except Exception:
            pass

    conn.close()


def init_db():
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd app && python -m pytest tests/test_pam_pa_cascade.py::test_reject_reason_column_exists_on_all_relevant_tables -v`
Expected: PASS

- [ ] **Step 5: Run the full test suite to check for regressions**

Run: `cd app && python -m pytest tests/test_pam_pa_cascade.py -v`
Expected: all tests PASS (this file's fixture rebuilds the DB from scratch on every test via `init_db()`, so every test now includes the new column — no other test asserts an exact column list, so nothing should break)

- [ ] **Step 6: Commit**

```bash
git add app/database.py app/tests/test_pam_pa_cascade.py
git commit -m "feat: add reject_reason column for Open PAM reject status"
```

---

## Task 2: Patch the 4 "PA still has an active payment" checks to exclude rejected rows

**Files:**
- Modify: `app/modules/beasiswa/service.py:752-757` (inside `delete_payment_row`)
- Modify: `app/modules/beasiswa/service.py:821-826` (inside `delete_payment_beasiswa`)
- Modify: `app/modules/payment_memo/service.py:1173-1178` (inside `cancel_pam_record`)
- Modify: `app/modules/payment_memo/service.py:1267-1272` (inside `remove_student_from_pam`)
- Test: `app/tests/test_beasiswa_service.py` (2 new tests), `app/tests/test_pam_remove_student.py` (1 new test), `app/tests/test_pam_pa_cascade.py` (1 new test)

**Interfaces:**
- Consumes: nothing new — this task only changes the `WHERE` clause of 4 existing internal queries. No function signature changes.
- Produces: from Task 3 onward, any `payment_beasiswa` row with `status='rejected'` is treated as inactive by every "is this PA still referenced?" check in the codebase.

This task exists because Task 3/4 will start creating `status='rejected'` rows that persist. Landing this patch **first**, with its own regression tests using a manually-inserted `status='rejected'` row (simulating what Task 3/4 will produce), means Task 3/4 can rely on correct PA-reversion behavior from the start.

- [ ] **Step 1: Write the failing tests**

Add to `app/tests/test_beasiswa_service.py`, at the end of the file:

```python
def test_delete_payment_row_excludes_rejected_sibling_when_reverting_pa():
    """One PA has 2 lines. Line B's payment_beasiswa row is already
    status='rejected' (simulating the future reject feature). Deleting line
    A's payment (the last *active* one) must still revert the PA to 'open' —
    the rejected sibling must not be counted as 'still active'."""
    from modules.beasiswa.service import delete_payment_row
    conn = get_conn()
    sid, pa_id, line_a = _seed_siswa_and_pa(conn, COMPANY_ID)
    cur = conn.execute(
        "INSERT INTO etf_pa_lines (pa_id, student_id, jenis_pembayaran, jumlah_pembayaran) VALUES (?,?,?,?)",
        (pa_id, sid, "By Pendidikan", 2000000)
    )
    line_b = cur.lastrowid
    conn.execute("UPDATE etf_pa SET status='on_process' WHERE id=?", (pa_id,))
    conn.execute(
        """INSERT INTO payment_beasiswa
           (company_id, siswa_code, cat1, cat2, tanggal, amount, pillar,
            perusahaan, etf_pa_line_id, status)
           VALUES (?,?,?,?,?,?,?,?,?,'open')""",
        (COMPANY_ID, "1250001", "By Pendidikan", "Semester 1", "2026-07-01",
         5000000, "AGRI", "PT ABC", line_a)
    )
    row_a_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.execute(
        """INSERT INTO payment_beasiswa
           (company_id, siswa_code, cat1, cat2, tanggal, amount, pillar,
            perusahaan, etf_pa_line_id, status)
           VALUES (?,?,?,?,?,?,?,?,?,'rejected')""",
        (COMPANY_ID, "1250001", "By Pendidikan", "Semester 2", "2026-07-01",
         2000000, "AGRI", "PT ABC", line_b)
    )
    conn.commit()
    conn.close()

    result = delete_payment_row(COMPANY_ID, row_a_id)
    assert result["ok"] is True

    conn = get_conn()
    pa = conn.execute("SELECT status FROM etf_pa WHERE id=?", (pa_id,)).fetchone()
    conn.close()
    assert pa["status"] == "open", \
        f"PA should revert to open (rejected sibling doesn't count as active), got '{pa['status']}'"


def test_delete_payment_beasiswa_excludes_rejected_sibling_when_reverting_pa():
    """Same as above, exercised through delete_payment_beasiswa instead of
    delete_payment_row (the two functions duplicate this cascade separately)."""
    conn = get_conn()
    sid, pa_id, line_a = _seed_siswa_and_pa(conn, COMPANY_ID)
    cur = conn.execute(
        "INSERT INTO etf_pa_lines (pa_id, student_id, jenis_pembayaran, jumlah_pembayaran) VALUES (?,?,?,?)",
        (pa_id, sid, "By Pendidikan", 2000000)
    )
    line_b = cur.lastrowid
    conn.execute("UPDATE etf_pa SET status='on_process' WHERE id=?", (pa_id,))
    conn.execute(
        """INSERT INTO payment_beasiswa
           (company_id, siswa_code, cat1, cat2, tanggal, amount, pillar,
            perusahaan, etf_pa_line_id, status)
           VALUES (?,?,?,?,?,?,?,?,?,'open')""",
        (COMPANY_ID, "1250001", "By Pendidikan", "Semester 1", "2026-07-01",
         5000000, "AGRI", "PT ABC", line_a)
    )
    row_a_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.execute(
        """INSERT INTO payment_beasiswa
           (company_id, siswa_code, cat1, cat2, tanggal, amount, pillar,
            perusahaan, etf_pa_line_id, status)
           VALUES (?,?,?,?,?,?,?,?,?,'rejected')""",
        (COMPANY_ID, "1250001", "By Pendidikan", "Semester 2", "2026-07-01",
         2000000, "AGRI", "PT ABC", line_b)
    )
    conn.commit()
    conn.close()

    result = delete_payment_beasiswa(row_a_id, COMPANY_ID)
    assert result["ok"] is True

    conn = get_conn()
    pa = conn.execute("SELECT status FROM etf_pa WHERE id=?", (pa_id,)).fetchone()
    conn.close()
    assert pa["status"] == "open", \
        f"PA should revert to open (rejected sibling doesn't count as active), got '{pa['status']}'"
```

Add `delete_payment_row` to the import block at the top of `app/tests/test_beasiswa_service.py` (line 8-14):

```python
from modules.beasiswa.service import (
    generate_kode_siswa, get_siswa_list, add_siswa, update_siswa,
    add_budget_batch, add_payment_batch, get_rekap, get_sisa_budget,
    add_klaim_multi, get_klaim_list, delete_klaim_row,
    add_payment_multi, get_budget_list, get_payment_list,
    delete_payment_beasiswa, delete_payment_row, update_payment_row,
)
```

Add to `app/tests/test_pam_remove_student.py`, at the end of the file:

```python
def test_remove_student_excludes_rejected_sibling_when_reverting_pa():
    """One PA has 2 lines under DIFFERENT pam_no groups. Line B's payment is
    already status='rejected'. Removing line A's payment (the last active one
    for this PA) must still revert the PA to open."""
    conn = get_conn()
    sid1 = _insert_siswa(conn, "1250001")
    sid2 = _insert_siswa(conn, "1250002")
    pam_no_A = _insert_pam(conn, "PAM-ETF-06-2026-001", total=5_000_000)

    cur = conn.execute(
        """INSERT INTO etf_pa
           (company_id, pa_number, tgl_payment_application, status, nomor_pam, created_at)
           VALUES (?,?,?,?,?,?)""",
        (COMPANY_ID, "PA/ETF/001/2026", "2026-06-01", "on_process", pam_no_A, _ts())
    )
    pa_id = cur.lastrowid
    cur2 = conn.execute(
        "INSERT INTO etf_pa_lines (pa_id, student_id, jenis_pembayaran, jumlah_pembayaran) VALUES (?,?,?,?)",
        (pa_id, sid1, "By Pendidikan", 5_000_000)
    )
    line_A = cur2.lastrowid
    cur3 = conn.execute(
        "INSERT INTO etf_pa_lines (pa_id, student_id, jenis_pembayaran, jumlah_pembayaran) VALUES (?,?,?,?)",
        (pa_id, sid2, "By Pendidikan", 5_000_000)
    )
    line_B = cur3.lastrowid

    pb_A = _insert_payment_beasiswa(conn, pam_no_A, line_A, "1250001")
    conn.execute(
        """INSERT INTO payment_beasiswa
           (company_id, siswa_code, cat1, cat2, tanggal, amount,
            pillar, perusahaan, pam, etf_pa_line_id, status)
           VALUES (?,?,?,?,?,?,?,?,?,?,'rejected')""",
        (COMPANY_ID, "1250002", "By Pendidikan", "Semester 3",
         "2026-06-01", 5_000_000, "AGRI", "PT. SMART Tbk", None, line_B)
    )
    conn.commit()
    conn.close()

    result = remove_student_from_pam(pb_A, COMPANY_ID)
    assert result["ok"] is True

    conn = get_conn()
    pa = conn.execute("SELECT status, nomor_pam FROM etf_pa WHERE id=?", (pa_id,)).fetchone()
    conn.close()
    assert pa["status"] == "open", \
        f"PA should revert to open (rejected sibling doesn't count as active), got '{pa['status']}'"
    assert pa["nomor_pam"] is None
```

Add to `app/tests/test_pam_pa_cascade.py`, at the end of the file:

```python
def test_cancel_pam_excludes_rejected_sibling_when_reverting_pa():
    """One PA has 2 lines: line_A is under the PAM being cancelled, line_B
    belongs to an already-rejected payment_beasiswa row (no pam_no, simulating
    a rejected line). Cancelling the PAM containing line_A must still revert
    the PA to open — the rejected row must not count as still-active."""
    conn = get_conn()
    sid = _insert_siswa(conn)
    pa_id, line_a = _insert_pa(conn, "etf_pa", "etf_pa_lines", "ETF", sid, "on_process")
    cur = conn.execute(
        "INSERT INTO etf_pa_lines (pa_id, student_id, jenis_pembayaran, jumlah_pembayaran) VALUES (?,?,?,?)",
        (pa_id, sid, "By Pendidikan", 2_000_000)
    )
    line_b = cur.lastrowid
    conn.execute(
        """INSERT INTO payment_beasiswa
           (company_id, siswa_code, cat1, cat2, tanggal, amount,
            pillar, perusahaan, etf_pa_line_id, status)
           VALUES (?,?,?,?,?,?,?,?,?,'rejected')""",
        (COMPANY_ID, "1250001", "By Pendidikan", "Semester 2",
         "2026-06-01", 2_000_000, "AGRI", "PT. SMART Tbk", line_b)
    )
    pam_id, _ = _insert_pam_and_link(conn, "etf_pa", "etf_pa_lines", pa_id, line_a)
    conn.close()

    result = cancel_pam_record(pam_id, COMPANY_ID)
    assert result["ok"] is True

    conn = get_conn()
    row = conn.execute("SELECT status, nomor_pam FROM etf_pa WHERE id=?", (pa_id,)).fetchone()
    conn.close()
    assert row["status"] == "open", \
        f"PA should revert to open (rejected sibling doesn't count as active), got '{row['status']}'"
    assert row["nomor_pam"] is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd app && python -m pytest tests/test_beasiswa_service.py::test_delete_payment_row_excludes_rejected_sibling_when_reverting_pa tests/test_beasiswa_service.py::test_delete_payment_beasiswa_excludes_rejected_sibling_when_reverting_pa tests/test_pam_remove_student.py::test_remove_student_excludes_rejected_sibling_when_reverting_pa tests/test_pam_pa_cascade.py::test_cancel_pam_excludes_rejected_sibling_when_reverting_pa -v`
Expected: all 4 FAIL with `assert 'on_process' == 'open'` (the rejected sibling is currently miscounted as active, so the PA doesn't revert)

- [ ] **Step 3: Patch the 4 queries**

In `app/modules/beasiswa/service.py`, inside `delete_payment_row` (around line 752-757):

```python
                remaining_pa = conn.execute(
                    f"""SELECT COUNT(*) FROM payment_beasiswa pb
                           JOIN {lines_tbl} el ON el.id = pb.etf_pa_line_id
                           WHERE el.pa_id=? AND pb.company_id=?""",
                    (pa_id, company_id)
                ).fetchone()[0]
```

Replace with:

```python
                remaining_pa = conn.execute(
                    f"""SELECT COUNT(*) FROM payment_beasiswa pb
                           JOIN {lines_tbl} el ON el.id = pb.etf_pa_line_id
                           WHERE el.pa_id=? AND pb.company_id=? AND pb.status != 'rejected'""",
                    (pa_id, company_id)
                ).fetchone()[0]
```

Inside `delete_payment_beasiswa` (around line 821-826), the identical block:

```python
                remaining_pa = conn.execute(
                    f"""SELECT COUNT(*) FROM payment_beasiswa pb
                           JOIN {lines_tbl} el ON el.id = pb.etf_pa_line_id
                           WHERE el.pa_id=? AND pb.company_id=?""",
                    (pa_id, company_id)
                ).fetchone()[0]
```

Replace with the same `AND pb.status != 'rejected'` addition:

```python
                remaining_pa = conn.execute(
                    f"""SELECT COUNT(*) FROM payment_beasiswa pb
                           JOIN {lines_tbl} el ON el.id = pb.etf_pa_line_id
                           WHERE el.pa_id=? AND pb.company_id=? AND pb.status != 'rejected'""",
                    (pa_id, company_id)
                ).fetchone()[0]
```

In `app/modules/payment_memo/service.py`, inside `cancel_pam_record` (around line 1173-1178):

```python
                    remaining = conn.execute(
                        f"""SELECT COUNT(*) FROM payment_beasiswa pb
                               JOIN {lines_tbl} el ON el.id = pb.etf_pa_line_id
                               WHERE el.pa_id=? AND pb.company_id=?""",
                        (pa_id_inner, company_id)
                    ).fetchone()[0]
```

Replace with:

```python
                    remaining = conn.execute(
                        f"""SELECT COUNT(*) FROM payment_beasiswa pb
                               JOIN {lines_tbl} el ON el.id = pb.etf_pa_line_id
                               WHERE el.pa_id=? AND pb.company_id=? AND pb.status != 'rejected'""",
                        (pa_id_inner, company_id)
                    ).fetchone()[0]
```

Inside `remove_student_from_pam` (around line 1267-1272):

```python
            still_has_payment = conn.execute(
                f"""SELECT COUNT(*) FROM payment_beasiswa pb
                    JOIN {lines_tbl} el ON el.id = pb.etf_pa_line_id
                    WHERE el.pa_id=? AND pb.company_id=?""",
                (pa_id, company_id)
            ).fetchone()[0]
```

Replace with:

```python
            still_has_payment = conn.execute(
                f"""SELECT COUNT(*) FROM payment_beasiswa pb
                    JOIN {lines_tbl} el ON el.id = pb.etf_pa_line_id
                    WHERE el.pa_id=? AND pb.company_id=? AND pb.status != 'rejected'""",
                (pa_id, company_id)
            ).fetchone()[0]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd app && python -m pytest tests/test_beasiswa_service.py::test_delete_payment_row_excludes_rejected_sibling_when_reverting_pa tests/test_beasiswa_service.py::test_delete_payment_beasiswa_excludes_rejected_sibling_when_reverting_pa tests/test_pam_remove_student.py::test_remove_student_excludes_rejected_sibling_when_reverting_pa tests/test_pam_pa_cascade.py::test_cancel_pam_excludes_rejected_sibling_when_reverting_pa -v`
Expected: all 4 PASS

- [ ] **Step 5: Run the full affected test files to check for regressions**

Run: `cd app && python -m pytest tests/test_beasiswa_service.py tests/test_pam_remove_student.py tests/test_pam_pa_cascade.py -v`
Expected: all PASS (existing tests never insert a `status='rejected'` row, so `pb.status != 'rejected'` never excludes anything they rely on — this is purely additive)

- [ ] **Step 6: Commit**

```bash
git add app/modules/beasiswa/service.py app/modules/payment_memo/service.py \
        app/tests/test_beasiswa_service.py app/tests/test_pam_remove_student.py \
        app/tests/test_pam_pa_cascade.py
git commit -m "fix: exclude rejected payment_beasiswa rows from PA active-payment checks"
```

---

## Task 3: `reject_student_from_pam()` service function

**Files:**
- Modify: `app/modules/payment_memo/service.py` (new function, inserted after `remove_student_from_pam` ends, currently line 1283 — right before `def get_pam_detail`)
- Test: `app/tests/test_pam_remove_student.py` (new tests)

**Interfaces:**
- Consumes: `_ts()` (already defined in `payment_memo/service.py`, returns an ISO timestamp string), `get_conn()` (from `database.py`)
- Produces: `reject_student_from_pam(payment_beasiswa_id: int, company_id: int, reason: str | None = None) -> dict` returning `{"ok": bool, "pesan": str}` — consumed by Task 5's route.

- [ ] **Step 1: Write the failing tests**

Add to `app/tests/test_pam_remove_student.py`, at the end of the file (after the test added in Task 2):

```python
def test_reject_one_of_many_students():
    """Reject 1 siswa dari PAM yang punya 3 siswa:
    - payment_beasiswa row TETAP ADA, status berubah jadi 'rejected'
    - pam_records.total_amount direcalculate ke 10jt (tidak menghitung yang rejected)
    - pam_records.status TETAP 'open' (masih ada 2 siswa aktif)
    - etf_pa siswa tersebut di-set 'rejected' (bukan 'open')
    - 2 siswa lain tidak berubah
    """
    from modules.payment_memo.service import reject_student_from_pam
    conn = get_conn()
    sid1 = _insert_siswa(conn, "1250001")
    sid2 = _insert_siswa(conn, "1250002")
    sid3 = _insert_siswa(conn, "1250003")
    pam_no = _insert_pam(conn, total=15_000_000)

    pa1_id, line1_id = _insert_etf_pa_with_line(conn, "PA/ETF/001/2026", pam_no, sid1)
    pa2_id, line2_id = _insert_etf_pa_with_line(conn, "PA/ETF/002/2026", pam_no, sid2)
    pa3_id, line3_id = _insert_etf_pa_with_line(conn, "PA/ETF/003/2026", pam_no, sid3)

    pb1_id = _insert_payment_beasiswa(conn, pam_no, line1_id, "1250001")
    _insert_payment_beasiswa(conn, pam_no, line2_id, "1250002")
    _insert_payment_beasiswa(conn, pam_no, line3_id, "1250003")
    conn.close()

    result = reject_student_from_pam(pb1_id, COMPANY_ID, reason="Data ganda")
    assert result["ok"] is True

    conn = get_conn()
    pb = conn.execute(
        "SELECT status, reject_reason FROM payment_beasiswa WHERE id=?", (pb1_id,)
    ).fetchone()
    assert pb is not None, "payment_beasiswa row harus tetap ada"
    assert pb["status"] == "rejected"
    assert pb["reject_reason"] == "Data ganda"

    pam = conn.execute(
        "SELECT total_amount, status FROM pam_records WHERE pam_no=? AND company_id=?",
        (pam_no, COMPANY_ID)
    ).fetchone()
    assert pam["total_amount"] == 10_000_000, \
        f"total_amount expected 10000000 (excludes rejected row), got {pam['total_amount']}"
    assert pam["status"] == "open"

    pa1 = conn.execute("SELECT status, nomor_pam FROM etf_pa WHERE id=?", (pa1_id,)).fetchone()
    assert pa1["status"] == "rejected", f"etf_pa 1 status expected 'rejected', got '{pa1['status']}'"

    pa2 = conn.execute("SELECT status FROM etf_pa WHERE id=?", (pa2_id,)).fetchone()
    assert pa2["status"] == "on_process"
    pa3 = conn.execute("SELECT status FROM etf_pa WHERE id=?", (pa3_id,)).fetchone()
    assert pa3["status"] == "on_process"
    conn.close()


def test_reject_last_student_marks_pam_rejected():
    """Reject siswa terakhir dalam PAM:
    - payment_beasiswa row status='rejected' (masih ada)
    - pam_records.status juga jadi 'rejected' (tidak ada sisa siswa aktif)
    - etf_pa di-set 'rejected'
    """
    from modules.payment_memo.service import reject_student_from_pam
    conn = get_conn()
    sid = _insert_siswa(conn)
    pam_no = _insert_pam(conn, total=5_000_000)
    pa_id, line_id = _insert_etf_pa_with_line(conn, "PA/ETF/001/2026", pam_no, sid)
    pb_id = _insert_payment_beasiswa(conn, pam_no, line_id)
    conn.close()

    result = reject_student_from_pam(pb_id, COMPANY_ID)
    assert result["ok"] is True

    conn = get_conn()
    pb = conn.execute("SELECT status FROM payment_beasiswa WHERE id=?", (pb_id,)).fetchone()
    assert pb["status"] == "rejected"

    pam = conn.execute(
        "SELECT status FROM pam_records WHERE pam_no=? AND company_id=?",
        (pam_no, COMPANY_ID)
    ).fetchone()
    assert pam is not None, "pam_records harus tetap ada (tidak dihapus)"
    assert pam["status"] == "rejected"

    pa = conn.execute("SELECT status FROM etf_pa WHERE id=?", (pa_id,)).fetchone()
    assert pa["status"] == "rejected"
    conn.close()


def test_reject_blocked_if_pam_not_open():
    """Jika pam_records.status != 'open', reject ditolak dan tidak ada perubahan DB."""
    from modules.payment_memo.service import reject_student_from_pam
    conn = get_conn()
    sid = _insert_siswa(conn)
    pam_no = _insert_pam(conn, total=5_000_000, status="on_process")
    pa_id, line_id = _insert_etf_pa_with_line(conn, "PA/ETF/001/2026", pam_no, sid)
    pb_id = _insert_payment_beasiswa(conn, pam_no, line_id)
    conn.close()

    result = reject_student_from_pam(pb_id, COMPANY_ID)
    assert result["ok"] is False

    conn = get_conn()
    pb = conn.execute("SELECT status FROM payment_beasiswa WHERE id=?", (pb_id,)).fetchone()
    assert pb["status"] == "open", "payment_beasiswa seharusnya tidak berubah"
    conn.close()


def test_reject_pa_not_rejected_if_has_other_active_payment():
    """Jika PA punya 2 line, dan line lain masih punya payment_beasiswa aktif,
    PA tidak di-reject saat salah satu payment di-reject."""
    from modules.payment_memo.service import reject_student_from_pam
    conn = get_conn()
    sid1 = _insert_siswa(conn, "1250001")
    sid2 = _insert_siswa(conn, "1250002")
    pam_no_A = _insert_pam(conn, "PAM-ETF-06-2026-001", total=10_000_000)
    pam_no_B = _insert_pam(conn, "PAM-ETF-06-2026-002", total=5_000_000)

    cur = conn.execute(
        """INSERT INTO etf_pa
           (company_id, pa_number, tgl_payment_application, status, nomor_pam, created_at)
           VALUES (?,?,?,?,?,?)""",
        (COMPANY_ID, "PA/ETF/001/2026", "2026-06-01", "on_process", pam_no_A, _ts())
    )
    pa_id = cur.lastrowid
    cur2 = conn.execute(
        "INSERT INTO etf_pa_lines (pa_id, student_id, jenis_pembayaran, jumlah_pembayaran) VALUES (?,?,?,?)",
        (pa_id, sid1, "By Pendidikan", 5_000_000)
    )
    line_A = cur2.lastrowid
    cur3 = conn.execute(
        "INSERT INTO etf_pa_lines (pa_id, student_id, jenis_pembayaran, jumlah_pembayaran) VALUES (?,?,?,?)",
        (pa_id, sid2, "By Pendidikan", 5_000_000)
    )
    line_B = cur3.lastrowid

    pb_A = _insert_payment_beasiswa(conn, pam_no_A, line_A, "1250001")
    _insert_payment_beasiswa(conn, pam_no_B, line_B, "1250002")
    conn.commit()
    conn.close()

    result = reject_student_from_pam(pb_A, COMPANY_ID)
    assert result["ok"] is True

    conn = get_conn()
    pa = conn.execute("SELECT status FROM etf_pa WHERE id=?", (pa_id,)).fetchone()
    assert pa["status"] == "on_process", \
        f"etf_pa status seharusnya tetap 'on_process', got '{pa['status']}'"
    conn.close()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd app && python -m pytest tests/test_pam_remove_student.py -k test_reject -v`
Expected: all 4 FAIL with `ImportError: cannot import name 'reject_student_from_pam'`

- [ ] **Step 3: Implement `reject_student_from_pam`**

In `app/modules/payment_memo/service.py`, insert this new function right after `remove_student_from_pam` ends (after line 1283, before `def get_pam_detail`):

```python
def reject_student_from_pam(payment_beasiswa_id: int, company_id: int, reason: str | None = None) -> dict:
    """Reject satu siswa dari Open PAM — sama seperti remove_student_from_pam,
    tapi data DIPERTAHANKAN (status='rejected') alih-alih di-DELETE:
    1. UPDATE payment_beasiswa SET status='rejected' (bukan DELETE)
    2. Recalculate pam_records.total_amount dari sisa baris non-rejected
       (atau set pam_records.status='rejected' jika tidak ada sisa yang aktif)
    3. Set PA terkait ke 'rejected' jika tidak ada payment aktif tersisa
       (bukan revert ke 'open')
    """
    conn = get_conn()
    now = _ts()

    pb = conn.execute(
        "SELECT id, pam, etf_pa_line_id, amount FROM payment_beasiswa WHERE id=? AND company_id=?",
        (payment_beasiswa_id, company_id)
    ).fetchone()
    if not pb:
        conn.close()
        return {"ok": False, "pesan": "Payment tidak ditemukan."}

    pam_no  = pb["pam"]
    line_id = pb["etf_pa_line_id"]

    pam_rec = conn.execute(
        "SELECT id, status FROM pam_records WHERE pam_no=? AND company_id=?",
        (pam_no, company_id)
    ).fetchone()
    if not pam_rec:
        conn.close()
        return {"ok": False, "pesan": "PAM tidak ditemukan."}
    if pam_rec["status"] != "open":
        conn.close()
        return {"ok": False, "pesan": "PAM sudah diproses, tidak dapat mengubah siswa."}

    conn.execute(
        "UPDATE payment_beasiswa SET status='rejected', reject_reason=? WHERE id=? AND company_id=?",
        (reason, payment_beasiswa_id, company_id)
    )

    remaining_active = conn.execute(
        "SELECT COUNT(*) FROM payment_beasiswa WHERE pam=? AND company_id=? AND status != 'rejected'",
        (pam_no, company_id)
    ).fetchone()[0]

    if remaining_active == 0:
        conn.execute(
            "UPDATE pam_records SET status='rejected', reject_reason=?, updated_at=? WHERE pam_no=? AND company_id=?",
            (reason, now, pam_no, company_id)
        )
    else:
        new_total = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM payment_beasiswa WHERE pam=? AND company_id=? AND status != 'rejected'",
            (pam_no, company_id)
        ).fetchone()[0]
        conn.execute(
            "UPDATE pam_records SET total_amount=?, updated_at=? WHERE pam_no=? AND company_id=?",
            (new_total, now, pam_no, company_id)
        )

    if line_id:
        for lines_tbl, pa_tbl in [
            ("etf_pa_lines",    "etf_pa"),
            ("app_pa_lines",    "app_pa"),
            ("sml_pa_lines",    "sml_pa"),
            ("energy_pa_lines", "energy_pa"),
            ("setf_pa_lines",   "setf_pa"),
        ]:
            pa_row = conn.execute(
                f"SELECT pa_id FROM {lines_tbl} WHERE id=?", (line_id,)
            ).fetchone()
            if not pa_row:
                continue
            pa_id = pa_row[0]
            still_has_payment = conn.execute(
                f"""SELECT COUNT(*) FROM payment_beasiswa pb
                    JOIN {lines_tbl} el ON el.id = pb.etf_pa_line_id
                    WHERE el.pa_id=? AND pb.company_id=? AND pb.status != 'rejected'""",
                (pa_id, company_id)
            ).fetchone()[0]
            if still_has_payment == 0:
                conn.execute(
                    f"UPDATE {pa_tbl} SET status='rejected', reject_reason=?, updated_at=? "
                    f"WHERE id=? AND company_id=?",
                    (reason, now, pa_id, company_id)
                )
            break  # line_id hanya bisa ada di satu PA table

    conn.commit()
    conn.close()
    return {"ok": True, "pesan": "Siswa berhasil di-reject dari PAM."}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd app && python -m pytest tests/test_pam_remove_student.py -k test_reject -v`
Expected: all 4 PASS

- [ ] **Step 5: Run the full file to check for regressions**

Run: `cd app && python -m pytest tests/test_pam_remove_student.py -v`
Expected: all PASS (9 tests total: 4 original `test_remove_*`, 1 from Task 2, and 4 new `test_reject_*` from this task)

- [ ] **Step 6: Commit**

```bash
git add app/modules/payment_memo/service.py app/tests/test_pam_remove_student.py
git commit -m "feat: add reject_student_from_pam service function"
```

---

## Task 4: `reject_pam_record()` service function

**Files:**
- Modify: `app/modules/payment_memo/service.py` (new function, inserted right after `cancel_pam_record` ends — currently line 1189, before the blank line preceding `def remove_student_from_pam`)
- Test: `app/tests/test_pam_pa_cascade.py` (new tests)

**Interfaces:**
- Consumes: `_ts()`, `get_conn()` (same as Task 3)
- Produces: `reject_pam_record(pam_id: int, company_id: int, reason: str | None = None) -> dict` returning `{"ok": bool, "pesan": str}` — consumed by Task 5's route.

- [ ] **Step 1: Write the failing tests**

Add to `app/tests/test_pam_pa_cascade.py`, at the end of the file (after the Task 2 regression test):

```python
def test_reject_pam_etf_agri_marks_pa_rejected():
    """source='etf_agri' flow: reject_pam_record must set etf_pa.status='rejected'
    directly (not go through the payment_beasiswa cascade) and keep pam_records
    (not delete it), with status='rejected'."""
    from modules.payment_memo.service import reject_pam_record
    conn = get_conn()
    pam_no = "PAM-001-ETF-06-2026"
    conn.execute(
        """INSERT INTO pam_records
           (company_id, pam_no, pam_date, total_amount, status, source, created_at)
           VALUES (?,?,?,?,?,?,?)""",
        (COMPANY_ID, pam_no, "2026-06-08", 5000000, "open", "etf_agri", _ts())
    )
    pam_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.execute(
        """INSERT INTO etf_pa (company_id, pa_number, tgl_payment_application, status, nomor_pam, created_at)
           VALUES (?,?,?,?,?,?)""",
        (COMPANY_ID, "PA/ETF/001/2026", "2026-06-01", "on_process", pam_no, _ts())
    )
    pa_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()
    conn.close()

    result = reject_pam_record(pam_id, COMPANY_ID, reason="Salah input")
    assert result["ok"] is True

    conn = get_conn()
    pam = conn.execute(
        "SELECT status, reject_reason FROM pam_records WHERE id=?", (pam_id,)
    ).fetchone()
    assert pam is not None, "pam_records harus tetap ada"
    assert pam["status"] == "rejected"
    assert pam["reject_reason"] == "Salah input"

    pa = conn.execute("SELECT status FROM etf_pa WHERE id=?", (pa_id,)).fetchone()
    assert pa["status"] == "rejected"
    conn.close()


def test_reject_pam_beasiswa_marks_all_rows_rejected():
    """source='beasiswa' flow (multi-student group): reject_pam_record must set
    every payment_beasiswa row under that pam_no to 'rejected' (not delete),
    pam_records to 'rejected', and the linked PA to 'rejected'."""
    from modules.payment_memo.service import reject_pam_record
    conn = get_conn()
    sid1 = _insert_siswa(conn)
    pam_id, pa_id = _insert_pam_beasiswa(conn, "app_pa", "app_pa_lines", "APP", "APP", sid1)
    conn.close()

    result = reject_pam_record(pam_id, COMPANY_ID, reason="Vendor batal")
    assert result["ok"] is True

    conn = get_conn()
    pam = conn.execute("SELECT status FROM pam_records WHERE id=?", (pam_id,)).fetchone()
    assert pam["status"] == "rejected"

    pb = conn.execute(
        "SELECT status, reject_reason FROM payment_beasiswa WHERE pam=?",
        ("PAM-APP-06-2026-001",)
    ).fetchone()
    assert pb["status"] == "rejected"
    assert pb["reject_reason"] == "Vendor batal"

    pa = conn.execute("SELECT status FROM app_pa WHERE id=?", (pa_id,)).fetchone()
    assert pa["status"] == "rejected"
    conn.close()


def test_reject_pam_beasiswa_pa_not_rejected_if_other_active_line_elsewhere():
    """PA has 2 lines across 2 different PAM groups. Rejecting one PAM must not
    reject the shared PA if the other PAM's line is still active."""
    from modules.payment_memo.service import reject_pam_record
    conn = get_conn()
    sid1 = _insert_siswa(conn)
    conn.execute(
        "INSERT INTO siswa (company_id, code, nama) VALUES (?,?,?)",
        (COMPANY_ID, "1250099", "Siswa Lain")
    )
    sid2 = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()

    cur = conn.execute(
        "INSERT INTO app_pa (company_id, pa_number, tgl_payment_application, status, created_at) VALUES (?,?,?,?,?)",
        (COMPANY_ID, "PA/APP/shared/2026", "2026-06-01", "on_process", _ts())
    )
    pa_id = cur.lastrowid
    cur2 = conn.execute(
        "INSERT INTO app_pa_lines (pa_id, student_id, jenis_pembayaran, jumlah_pembayaran) VALUES (?,?,?,?)",
        (pa_id, sid1, "By Pendidikan", 5_000_000)
    )
    line_A = cur2.lastrowid
    cur3 = conn.execute(
        "INSERT INTO app_pa_lines (pa_id, student_id, jenis_pembayaran, jumlah_pembayaran) VALUES (?,?,?,?)",
        (pa_id, sid2, "By Pendidikan", 3_000_000)
    )
    line_B = cur3.lastrowid

    pam_no_A = "PAM-APP-06-2026-A"
    cur4 = conn.execute(
        """INSERT INTO pam_records
           (company_id, pam_no, pam_date, total_amount, pillar, source, status, created_at)
           VALUES (?,?,?,?,?,'beasiswa','open',?)""",
        (COMPANY_ID, pam_no_A, "2026-06-08", 5_000_000, "APP", _ts())
    )
    pam_id_A = cur4.lastrowid
    conn.execute(
        """INSERT INTO payment_beasiswa
           (company_id, siswa_code, cat1, cat2, tanggal, amount,
            pillar, perusahaan, pam, etf_pa_line_id, status)
           VALUES (?,?,?,?,?,?,?,?,?,?,'open')""",
        (COMPANY_ID, "1250001", "By Pendidikan", "Semester 3",
         "2026-06-01", 5_000_000, "APP", "PT. SMART Tbk", pam_no_A, line_A)
    )

    pam_no_B = "PAM-APP-06-2026-B"
    conn.execute(
        """INSERT INTO pam_records
           (company_id, pam_no, pam_date, total_amount, pillar, source, status, created_at)
           VALUES (?,?,?,?,?,'beasiswa','open',?)""",
        (COMPANY_ID, pam_no_B, "2026-06-08", 3_000_000, "APP", _ts())
    )
    conn.execute(
        """INSERT INTO payment_beasiswa
           (company_id, siswa_code, cat1, cat2, tanggal, amount,
            pillar, perusahaan, pam, etf_pa_line_id, status)
           VALUES (?,?,?,?,?,?,?,?,?,?,'open')""",
        (COMPANY_ID, "1250099", "By Pendidikan", "Semester 3",
         "2026-06-01", 3_000_000, "APP", "PT. SMART Tbk", pam_no_B, line_B)
    )
    conn.commit()
    conn.close()

    result = reject_pam_record(pam_id_A, COMPANY_ID)
    assert result["ok"] is True

    conn = get_conn()
    pa = conn.execute("SELECT status FROM app_pa WHERE id=?", (pa_id,)).fetchone()
    conn.close()
    assert pa["status"] == "on_process", \
        f"shared PA must stay on_process (PAM-B's line is still active), got '{pa['status']}'"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd app && python -m pytest tests/test_pam_pa_cascade.py -k test_reject_pam -v`
Expected: all 3 FAIL with `ImportError: cannot import name 'reject_pam_record'` (it isn't imported yet at module level in this test file — the tests call it via inline `from modules.payment_memo.service import reject_pam_record`, matching this file's existing pattern of local imports for functions added later, e.g. `set_pam_complete_cascade` at line 264)

- [ ] **Step 3: Implement `reject_pam_record`**

In `app/modules/payment_memo/service.py`, insert this new function right after `cancel_pam_record` ends (after line 1189, before `def remove_student_from_pam`):

```python
def reject_pam_record(pam_id: int, company_id: int, reason: str | None = None) -> dict:
    """Reject satu PAM group secara keseluruhan — sama seperti cancel_pam_record,
    tapi data DIPERTAHANKAN (status='rejected') alih-alih di-DELETE."""
    conn = get_conn()
    pam = conn.execute(
        "SELECT pam_no, source FROM pam_records WHERE id=? AND company_id=?", (pam_id, company_id)
    ).fetchone()
    if not pam:
        conn.close()
        return {"ok": False, "pesan": "PAM record tidak ditemukan."}
    pam_no = pam["pam_no"]
    source = pam["source"] or "beasiswa"

    now = _ts()

    if source == "etf_agri":
        conn.execute(
            """UPDATE etf_pa SET status='rejected', reject_reason=?, updated_at=?
               WHERE nomor_pam=? AND company_id=?""",
            (reason, now, pam_no, company_id)
        )
        conn.execute(
            "UPDATE pam_records SET status='rejected', reject_reason=?, updated_at=? WHERE id=? AND company_id=?",
            (reason, now, pam_id, company_id)
        )
    else:
        lines = conn.execute(
            "SELECT DISTINCT etf_pa_line_id FROM payment_beasiswa WHERE pam=? AND company_id=? AND etf_pa_line_id IS NOT NULL",
            (pam_no, company_id)
        ).fetchall()
        line_ids = [r[0] for r in lines]

        conn.execute(
            "UPDATE payment_beasiswa SET status='rejected', reject_reason=? WHERE pam=? AND company_id=?",
            (reason, pam_no, company_id)
        )
        conn.execute(
            "UPDATE pam_records SET status='rejected', reject_reason=?, updated_at=? WHERE id=? AND company_id=?",
            (reason, now, pam_id, company_id)
        )

        if line_ids:
            ph = ",".join("?" * len(line_ids))
            for lines_tbl, pa_tbl in [
                ("etf_pa_lines",    "etf_pa"),
                ("app_pa_lines",    "app_pa"),
                ("sml_pa_lines",    "sml_pa"),
                ("energy_pa_lines", "energy_pa"),
                ("setf_pa_lines",   "setf_pa"),
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
                               WHERE el.pa_id=? AND pb.company_id=? AND pb.status != 'rejected'""",
                        (pa_id_inner, company_id)
                    ).fetchone()[0]
                    if remaining == 0:
                        conn.execute(
                            f"UPDATE {pa_tbl} SET status='rejected', reject_reason=?, updated_at=? "
                            f"WHERE id=? AND company_id=?",
                            (reason, now, pa_id_inner, company_id)
                        )

    conn.commit()
    conn.close()
    return {"ok": True, "pesan": f"PAM {pam_no} berhasil di-reject."}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd app && python -m pytest tests/test_pam_pa_cascade.py -k test_reject_pam -v`
Expected: all 3 PASS

- [ ] **Step 5: Run the full file to check for regressions**

Run: `cd app && python -m pytest tests/test_pam_pa_cascade.py -v`
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add app/modules/payment_memo/service.py app/tests/test_pam_pa_cascade.py
git commit -m "feat: add reject_pam_record service function"
```

---

## Task 5: Routes for the two new reject endpoints

**Files:**
- Modify: `app/modules/payment_memo/routes.py`
- Test: `app/tests/test_memo_api.py` (check existing pattern first — see Step 1)

**Interfaces:**
- Consumes: `reject_student_from_pam` (Task 3), `reject_pam_record` (Task 4)
- Produces: `POST /payment-memo/pam/reject-student` (JSON body `{"payment_beasiswa_id": int, "reason": str|null}`), `POST /payment-memo/pam/<int:pam_id>/reject` (JSON body `{"reason": str|null}`) — both consumed by Task 6/7's frontend JS.

- [ ] **Step 1: Check existing route test conventions**

Run: `grep -n "remove-student\|def test_" app/tests/test_memo_api.py | head -20`

If `test_memo_api.py` already has an HTTP-level test hitting `/payment-memo/pam/remove-student`, follow that exact fixture/client pattern for the two new routes below. If it does not test that route at the HTTP layer (route tests in this codebase are frequently skipped in favor of testing the service layer directly, since routes are thin wrappers), skip route-level tests for this task — the service-layer tests in Tasks 3/4 already cover the actual logic, and the routes below are a direct 1:1 pass-through with no branching logic of their own (nothing new to test at this layer).

- [ ] **Step 2: Add the two routes**

In `app/modules/payment_memo/routes.py`, add `reject_student_from_pam, reject_pam_record,` to the import block (the line that currently reads `delete_payment_beasiswa, cancel_pam_record, remove_student_from_pam,`):

```python
    delete_payment_beasiswa, cancel_pam_record, remove_student_from_pam,
    reject_student_from_pam, reject_pam_record,
```

Add this route right after `pam_remove_student_route` (after line 271, before the next route):

```python
@bp.route("/pam/reject-student", methods=["POST"])
@jwt_html_required
def pam_reject_student_route():
    data = request.get_json() or {}
    payment_beasiswa_id = data.get("payment_beasiswa_id")
    if not payment_beasiswa_id:
        return jsonify({"ok": False, "pesan": "payment_beasiswa_id diperlukan."})
    reason = data.get("reason") or None
    result = reject_student_from_pam(int(payment_beasiswa_id), session.get("company_id", 0), reason)
    return jsonify(result)
```

Add this route right after `cancel_pam_route` (after line 333, before `update_gl_account`):

```python
@bp.route("/pam/<int:pam_id>/reject", methods=["POST"])
@jwt_html_required
def reject_pam_route(pam_id):
    data = request.get_json() or {}
    reason = data.get("reason") or None
    result = reject_pam_record(pam_id, session.get("company_id", 0), reason)
    return jsonify(result)
```

- [ ] **Step 3: Sanity-check the app boots and routes register**

Run: `cd app && python -c "from app import create_app; app = create_app(); print([r.rule for r in app.url_map.iter_rules() if 'reject' in r.rule])"`
Expected output includes both new rules:
```
['/payment-memo/pam/reject-student', '/payment-memo/pam/<int:pam_id>/reject']
```

- [ ] **Step 4: Run the full payment_memo test suite to check for regressions**

Run: `cd app && python -m pytest tests/ -k "pam or memo" -v --no-header -p no:cacheprovider 2>&1 | tail -60`

(Run each affected file individually if the combined run shows unrelated `PermissionError`s from shared test-DB file locking — this is a known pre-existing test-isolation issue in this suite, unrelated to this change; confirm by running `test_pam_remove_student.py`, `test_pam_pa_cascade.py`, and `test_memo_api.py` each on their own and checking they pass standalone.)

Expected: all PASS in isolation.

- [ ] **Step 5: Commit**

```bash
git add app/modules/payment_memo/routes.py
git commit -m "feat: add reject-student and reject PAM routes"
```

---

## Task 6: Frontend — per-student "Reject" button

**Files:**
- Modify: `app/templates/payment_memo/index.html:1712-1714` (detail-row button markup, inside the `renderOpenPAM` per-item template string)
- Modify: `app/templates/payment_memo/index.html` (new `rejectStudentFromPAM` JS function, right after `removeStudentFromPAM` — currently ends at line 3604)

**Interfaces:**
- Consumes: `confirmModal` (global, defined in `base.html`), `apiFetch` (global), `showLoading`/`hideLoading`/`showToast` (globals), `esc()` (global) — all already used identically by `removeStudentFromPAM`
- Produces: clicking "Reject" on a detail row calls `POST /payment-memo/pam/reject-student` (Task 5)

- [ ] **Step 1: Add the button to the detail-row markup**

In `app/templates/payment_memo/index.html`, find (line 1711-1714):

```javascript
        '<td style="white-space:nowrap">' +
          '<button class="btn btn-secondary btn-sm" onclick="openEditDraft(' + d.id + ');event.stopPropagation()">Edit</button> ' +
          '<button class="btn btn-danger btn-sm" onclick="removeStudentFromPAM(' + d.id + ', ' + JSON.stringify(esc(d.nama || d.siswa_code || '')).replace(/"/g, '&quot;') + ');event.stopPropagation()">Hapus</button>' +
        '</td>' +
```

Replace with:

```javascript
        '<td style="white-space:nowrap">' +
          '<button class="btn btn-secondary btn-sm" onclick="openEditDraft(' + d.id + ');event.stopPropagation()">Edit</button> ' +
          '<button class="btn btn-danger btn-sm" onclick="removeStudentFromPAM(' + d.id + ', ' + JSON.stringify(esc(d.nama || d.siswa_code || '')).replace(/"/g, '&quot;') + ');event.stopPropagation()">Hapus</button> ' +
          '<button class="btn btn-danger btn-sm" style="background:#7c2d12" onclick="rejectStudentFromPAM(' + d.id + ', ' + JSON.stringify(esc(d.nama || d.siswa_code || '')).replace(/"/g, '&quot;') + ');event.stopPropagation()">Reject</button>' +
        '</td>' +
```

- [ ] **Step 2: Add the `rejectStudentFromPAM` JS function**

In `app/templates/payment_memo/index.html`, right after `removeStudentFromPAM` ends (after line 3604, the closing `}` of that function):

```javascript
// ── Reject student from Open PAM ──────────────────────────────────────────────
async function rejectStudentFromPAM(paymentBeasiswaId, namaLabel) {
  const label = namaLabel || 'siswa ini';
  if (!await confirmModal(
    'Reject ' + label + ' dari PAM ini?\nData akan disimpan dengan status Rejected (tidak dihapus), dan PA terkait tidak bisa dipakai lagi.',
    { type: 'danger', confirmText: 'Reject' }
  )) return;
  const reason = prompt('Alasan reject (opsional):');
  if (reason === null) return;
  showLoading("Merejek dari PAM...");
  try {
    const res = await apiFetch('/payment-memo/pam/reject-student', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ payment_beasiswa_id: paymentBeasiswaId, reason: reason || null })
    });
    if (!res) return;
    const data = await res.json();
    showToast(data.pesan, data.ok ? 'success' : 'error');
    if (data.ok) {
      setTimeout(() => location.reload(), 800);
    }
  } finally {
    hideLoading();
  }
}
```

- [ ] **Step 3: Manual verification (no automated frontend test harness in this codebase)**

Start the dev server: `cd app && python -m flask --app app:create_app run --port 5052 --debug` (or reuse the `financehub-5052` launch config)

Log in, go to Payment Approval Memo → Open PAM, expand a multi-student PAM group, click "Reject" on one student, confirm the dialog, optionally type a reason, confirm. Expected: success toast, page reloads, that student's row is gone from the Open PAM list (its `payment_beasiswa.status` is now `'rejected'`, and `get_draft_payments()` only shows `status='open'`), while the other students in the same group remain visible and unaffected. Then navigate to the pillar tab matching that student's pillar (e.g. AGRI) and confirm the row now appears with the badge from Task 8.

- [ ] **Step 4: Commit**

```bash
git add app/templates/payment_memo/index.html
git commit -m "feat: add per-student Reject button to Open PAM detail rows"
```

---

## Task 7: Frontend — per-group "Reject" button in `#pam-memo-bar`

**Files:**
- Modify: `app/templates/payment_memo/index.html:219-229` (`#pam-memo-bar` markup)
- Modify: `app/templates/payment_memo/index.html` (new `rejectOpenPamGroups` JS function, right after `submitOpenPamPaid` ends)

**Interfaces:**
- Consumes: same globals as Task 6, plus reads `.pam-check:checked` (existing checkbox mechanism already populated by `renderOpenPAM`/`updatePamMemoBar`)
- Produces: clicking "Reject" in the memo bar calls `POST /payment-memo/pam/<id>/reject` once per checked **group** (Task 5's second route)

Scope note: this only rejects whole PAM-header groups selected via `.pam-check:checked` (mirroring `cancelPAM`'s existing whole-group scope) — it does not extend to the finer-grained per-line `.draft-check:checked` selection that `submitOpenPamPaid` also supports for partial completion. A user who wants to reject one specific line already has the Task 6 per-row button for exactly that; bulk-rejecting individual lines was not part of the approved spec and is left out of this plan.

- [ ] **Step 1: Add the button to `#pam-memo-bar`**

In `app/templates/payment_memo/index.html`, find (line 219-229):

```html
    <div id="pam-memo-bar">
      <span class="pam-memo-count">0 PAM dipilih</span>
      <span style="font-size:.85rem;opacity:.85">— centang PAM untuk set tanggal paid</span>
      <input type="date" id="open-pam-paid-date" class="dm-inp" style="max-width:150px; background:#fff; padding:.25rem; border-radius:.25rem; margin-left:auto" required>
      <button class="btn btn-success btn-sm" onclick="submitOpenPamPaid()">Mark Complete</button>
      <button class="btn btn-secondary btn-sm"
              style="background:#fff;color:#1e40af;border:none;"
              onclick="document.getElementById('select-all-drafts').checked=false;toggleAllDrafts({checked:false})">
        Batal
      </button>
    </div>
```

Replace with:

```html
    <div id="pam-memo-bar">
      <span class="pam-memo-count">0 PAM dipilih</span>
      <span style="font-size:.85rem;opacity:.85">— centang PAM untuk set tanggal paid</span>
      <input type="date" id="open-pam-paid-date" class="dm-inp" style="max-width:150px; background:#fff; padding:.25rem; border-radius:.25rem; margin-left:auto" required>
      <button class="btn btn-success btn-sm" onclick="submitOpenPamPaid()">Mark Complete</button>
      <button class="btn btn-danger btn-sm" style="background:#7c2d12" onclick="rejectOpenPamGroups()">Reject</button>
      <button class="btn btn-secondary btn-sm"
              style="background:#fff;color:#1e40af;border:none;"
              onclick="document.getElementById('select-all-drafts').checked=false;toggleAllDrafts({checked:false})">
        Batal
      </button>
    </div>
```

- [ ] **Step 2: Add the `rejectOpenPamGroups` JS function**

Find where `submitOpenPamPaid` ends (the `}` closing the function whose body starts at line 1492 — locate it by searching for the next blank line before `function groupDraftsByPAM`). Insert this new function right after that closing `}`:

```javascript
async function rejectOpenPamGroups() {
  var pamIds = [];
  document.querySelectorAll('.pam-check:checked').forEach(function(cb) {
    var pamKey = cb.dataset.pamKey;
    if (pamKey && pamKey !== '__unassigned__') pamIds.push(pamKey);
  });
  if (pamIds.length === 0) {
    alert("Pilih minimal 1 PAM group untuk di-reject (centang di kolom paling kiri).");
    return;
  }
  if (!await confirmModal(
    "Reject " + pamIds.length + " PAM group?\nData akan disimpan dengan status Rejected (tidak dihapus), dan PA terkait tidak bisa dipakai lagi.",
    { type: 'danger', confirmText: 'Reject' }
  )) return;
  const reason = prompt('Alasan reject (opsional):');
  if (reason === null) return;

  showLoading("Merejek PAM...");
  try {
    var okCount = 0, msgs = [];
    for (const pamKey of pamIds) {
      const detailRow = document.querySelector('.pam-check[data-pam-key="' + CSS.escape(pamKey) + '"]');
      const pamIdAttr = detailRow ? detailRow.closest('tr').dataset.pamRecordId : null;
      if (!pamIdAttr) continue;
      const res = await apiFetch('/payment-memo/pam/' + pamIdAttr + '/reject', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason: reason || null })
      });
      if (!res) continue;
      const data = await res.json();
      if (data.ok) okCount++;
      msgs.push(data.pesan);
    }
    showToast(msgs.join(' | '), okCount > 0 ? 'success' : 'error');
    if (okCount > 0) window.location.reload();
  } finally {
    hideLoading();
  }
}
```

- [ ] **Step 3: Add `data-pam-record-id` to the group header row so the JS above can resolve `pamKey` → `pam_id`**

`reject_pam_record` (Task 4) takes a `pam_id` (the `pam_records.id`), but `.pam-check` checkboxes only carry `pamKey` (the `pam_no` string) — the group row currently has no `pam_records.id` anywhere in its dataset, and `get_draft_payments()` does not currently SELECT it either (only `pr.pillar, pr.due_date, pr.status AS pam_status` are pulled from the join — see `app/modules/payment_memo/service.py:32-44`). Three changes thread it through: add `pr.id AS pam_record_id` to that SELECT, carry it through `groupDraftsByPAM` (the function that builds the `g` group object) via `if (!groups[key].pamRecordId && d.pam_record_id) groups[key].pamRecordId = d.pam_record_id;`, and render it as `data-pam-record-id="' + (g.pamRecordId || '') + '"` on the group row's `<tr class="' + masterClass + '"` element (search `renderOpenPAM` for `html += '<tr class="' + masterClass + '"'`). Step 2's JS already reads `detailRow.closest('tr').dataset.pamRecordId` against this attribute.

Concretely, in `app/modules/payment_memo/service.py`, `get_draft_payments()` (currently lines 32-60):

```python
    rows = [dict(r) for r in conn.execute(
        """SELECT pb.*, s.nama, s.bank, s.norek, s.namarek, 'beasiswa' AS _type,
                  pr.pillar, pr.due_date, pr.status AS pam_status
           FROM payment_beasiswa pb
           LEFT JOIN siswa s  ON s.company_id  = pb.company_id AND s.code   = pb.siswa_code
           LEFT JOIN pam_records pr ON pr.pam_no = pb.pam AND pr.company_id = pb.company_id
           WHERE pb.company_id = ? AND pb.status = 'open'
           ORDER BY pb.tanggal DESC""",
        (company_id,)
    ).fetchall()]
```

Change to add `pr.id AS pam_record_id`:

```python
    rows = [dict(r) for r in conn.execute(
        """SELECT pb.*, s.nama, s.bank, s.norek, s.namarek, 'beasiswa' AS _type,
                  pr.id AS pam_record_id, pr.pillar, pr.due_date, pr.status AS pam_status
           FROM payment_beasiswa pb
           LEFT JOIN siswa s  ON s.company_id  = pb.company_id AND s.code   = pb.siswa_code
           LEFT JOIN pam_records pr ON pr.pam_no = pb.pam AND pr.company_id = pb.company_id
           WHERE pb.company_id = ? AND pb.status = 'open'
           ORDER BY pb.tanggal DESC""",
        (company_id,)
    ).fetchall()]
```

In `app/templates/payment_memo/index.html`, `groupDraftsByPAM` (currently around line 1553-1564):

```javascript
function groupDraftsByPAM(drafts) {
  const groups = {};
  const UNASSIGNED = '__unassigned__';
  drafts.forEach(function(d) {
    var key = (d.pam && d.pam !== '--') ? d.pam : UNASSIGNED;
    if (!groups[key]) groups[key] = { pam: key, items: [], total: 0, minDate: d.tanggal, pillar: d.pillar || null, dueDate: d.due_date || null, status: d.pam_status || null };
    groups[key].items.push(d);
    groups[key].total += d.amount;
    if (d.tanggal < groups[key].minDate) groups[key].minDate = d.tanggal;
    if (!groups[key].pillar && d.pillar) groups[key].pillar = d.pillar;
    if (!groups[key].dueDate && d.due_date) groups[key].dueDate = d.due_date;
```

Change to also carry `pamRecordId`:

```javascript
function groupDraftsByPAM(drafts) {
  const groups = {};
  const UNASSIGNED = '__unassigned__';
  drafts.forEach(function(d) {
    var key = (d.pam && d.pam !== '--') ? d.pam : UNASSIGNED;
    if (!groups[key]) groups[key] = { pam: key, items: [], total: 0, minDate: d.tanggal, pillar: d.pillar || null, dueDate: d.due_date || null, status: d.pam_status || null, pamRecordId: d.pam_record_id || null };
    groups[key].items.push(d);
    groups[key].total += d.amount;
    if (d.tanggal < groups[key].minDate) groups[key].minDate = d.tanggal;
    if (!groups[key].pillar && d.pillar) groups[key].pillar = d.pillar;
    if (!groups[key].dueDate && d.due_date) groups[key].dueDate = d.due_date;
    if (!groups[key].pamRecordId && d.pam_record_id) groups[key].pamRecordId = d.pam_record_id;
```

In `renderOpenPAM`, find the group row's opening tag (search for `html += '<tr class="' + masterClass + '"'`) — it currently reads:

```javascript
    html += '<tr class="' + masterClass + '"' +
      ' data-pam-key="' + pamKeyAttr + '"' +
      ' onclick="togglePAMRow(this.dataset.pamKey)">' +
```

Change to add the new attribute:

```javascript
    html += '<tr class="' + masterClass + '"' +
      ' data-pam-key="' + pamKeyAttr + '"' +
      ' data-pam-record-id="' + (g.pamRecordId || '') + '"' +
      ' onclick="togglePAMRow(this.dataset.pamKey)">' +
```

And update the checkbox inside that same row (search for `class="pam-check"`) so `.closest('tr')` in Step 2's JS resolves correctly — no change needed there since the checkbox is already inside this `<tr>`; `.closest('tr')` will pick up the `data-pam-record-id` we just added to the row.

- [ ] **Step 4: Run the affected backend test to confirm the SELECT change didn't break anything**

Run: `cd app && python -m pytest tests/test_payment_memo_service.py -k draft -v`
Expected: PASS (the new `pr.id AS pam_record_id` column is purely additive to the SELECT — no existing test asserts an exact key set on the returned dicts)

- [ ] **Step 5: Manual verification**

Start the dev server, go to Open PAM, tick 1-2 PAM-group checkboxes (not the per-line ones inside an expanded group), click "Reject" in the bottom bar, confirm, optionally add a reason. Expected: success toast, page reloads, those PAM groups disappear from Open PAM entirely (all their rows are `status='rejected'`), and reappear in their pillar tab with the Rejected badge.

- [ ] **Step 6: Commit**

```bash
git add app/templates/payment_memo/index.html app/modules/payment_memo/service.py
git commit -m "feat: add per-group Reject action to Open PAM memo bar"
```

---

## Task 8: Frontend — status badge + filter dropdowns in `payment_memo/index.html`

**Files:**
- Modify: `app/templates/payment_memo/index.html` (`_statusBadge` function, currently line 2890-2899)
- Modify: `app/templates/payment_memo/index.html` (7 status filter `<select>` elements, lines 510-517, 623-630, 727-734, 809-816, 914-919, 976-983, 1048-1054)

**Interfaces:**
- Consumes: nothing new
- Produces: any row with `status='rejected'` (from Tasks 3/4/6/7) now renders with a red "rejected" badge and is filterable via each pillar tab's status dropdown.

- [ ] **Step 1: Add the `rejected` entry to `_statusBadge`**

In `app/templates/payment_memo/index.html`, find (line 2890-2896):

```javascript
function _statusBadge(status) {
  const styles = {
    open:       'background:#fef3c7;color:#92400e;border:1px solid #d97706',
    on_process: 'background:#dbeafe;color:#1e40af;border:1px solid #3b82f6',
    partial:    'background:#fef9c3;color:#854d0e;border:1px solid #eab308',
    complete:   'background:#d1fae5;color:#065f46;border:1px solid #059669',
  };
```

Replace with:

```javascript
function _statusBadge(status) {
  const styles = {
    open:       'background:#fef3c7;color:#92400e;border:1px solid #d97706',
    on_process: 'background:#dbeafe;color:#1e40af;border:1px solid #3b82f6',
    partial:    'background:#fef9c3;color:#854d0e;border:1px solid #eab308',
    complete:   'background:#d1fae5;color:#065f46;border:1px solid #059669',
    rejected:   'background:#fef2f2;color:#991b1b;border:1px solid #fecaca',
  };
```

- [ ] **Step 2: Add `<option value="rejected">Rejected</option>` to each of the 7 status filters**

In `app/templates/payment_memo/index.html`, each of these 7 blocks needs one new `<option>` line appended right before its closing `</select>`. Find each by its `id`:

`#pam-filter-status` (line 510-517):
```html
      <select id="pam-filter-status" onchange="loadPAMDebounced()"
              style="padding:4px 6px;border:1px solid #d1d5db;border-radius:5px;font-size:11px;width:90px">
        <option value="">Semua Status</option>
        <option value="open">Open</option>
        <option value="on_process">On Process</option>
        <option value="partial">Partial</option>
        <option value="complete">Complete</option>
      </select>
```
becomes (added line before `</select>`):
```html
      <select id="pam-filter-status" onchange="loadPAMDebounced()"
              style="padding:4px 6px;border:1px solid #d1d5db;border-radius:5px;font-size:11px;width:90px">
        <option value="">Semua Status</option>
        <option value="open">Open</option>
        <option value="on_process">On Process</option>
        <option value="partial">Partial</option>
        <option value="complete">Complete</option>
        <option value="rejected">Rejected</option>
      </select>
```

Apply the exact same one-line addition (`<option value="rejected">Rejected</option>` right before `</select>`) to:
- `#fiori-filter-status` (line 623-630, same 4 existing options)
- `#sml-filter-status` (line 727-734, same 4 existing options)
- `#smt-filter-status` (line 809-816, same 4 existing options)
- `#setf-filter-status` (line 976-983, same 4 existing options)

For `#advance-filter-status` (line 914-919, only has `open`/`on_process`):
```html
      <select id="advance-filter-status" onchange="loadAdvanceDebounced()"
              style="padding:4px 6px;border:1px solid #d1d5db;border-radius:5px;font-size:11px;width:90px">
        <option value="">Semua Status</option>
        <option value="open">Open</option>
        <option value="on_process">On Process</option>
      </select>
```
becomes:
```html
      <select id="advance-filter-status" onchange="loadAdvanceDebounced()"
              style="padding:4px 6px;border:1px solid #d1d5db;border-radius:5px;font-size:11px;width:90px">
        <option value="">Semua Status</option>
        <option value="open">Open</option>
        <option value="on_process">On Process</option>
        <option value="rejected">Rejected</option>
      </select>
```

For `#pa-advance-filter-status` (line 1048-1054, has `open`/`paid`/`complete`):
```html
      <select id="pa-advance-filter-status" onchange="loadPaAdvanceDebounced()"
              style="padding:4px 6px;border:1px solid #d1d5db;border-radius:5px;font-size:11px;width:90px">
        <option value="">Semua Status</option>
        <option value="open">Open</option>
        <option value="paid">Paid</option>
        <option value="complete">Complete</option>
      </select>
```
becomes:
```html
      <select id="pa-advance-filter-status" onchange="loadPaAdvanceDebounced()"
              style="padding:4px 6px;border:1px solid #d1d5db;border-radius:5px;font-size:11px;width:90px">
        <option value="">Semua Status</option>
        <option value="open">Open</option>
        <option value="paid">Paid</option>
        <option value="complete">Complete</option>
        <option value="rejected">Rejected</option>
      </select>
```

- [ ] **Step 3: Manual verification**

After Task 6/7 produce at least one `status='rejected'` row, open the matching pillar tab (e.g. AGRI if the rejected item's pillar is AGRI), confirm the row is visible with a red "rejected" badge in the Status column, then select "Rejected" in that tab's status filter dropdown and confirm only rejected rows remain.

- [ ] **Step 4: Commit**

```bash
git add app/templates/payment_memo/index.html
git commit -m "feat: add rejected status badge and filter option across pillar tabs"
```

---

## Task 9: Frontend — badge + filter dropdowns in `etf_payment_application/index.html`

**Files:**
- Modify: `app/templates/etf_payment_application/index.html:486` (Jinja badge class logic)
- Modify: `app/templates/etf_payment_application/index.html:1271` (JS badge class logic)
- Modify: `app/templates/etf_payment_application/index.html:210-213` (server-rendered Jinja filter, PA list page)
- Modify: `app/templates/etf_payment_application/index.html:558-564` (`#sf-status` JS filter)
- Modify: `app/templates/etf_payment_application/index.html:774-780` (`#adv-status` JS filter)

**Interfaces:** none — purely presentational, reuses the existing `.badge-red` CSS class (already defined in `app/static/css/style.css:675`, already dark-mode-safe via CSS variables).

Scope note: the `#edit-status` dropdown (line 906-911, inside the "Edit PA" modal that lets someone manually set a PA's status) is intentionally **not** given a `rejected` option — manually flipping a PA to `rejected` through that generic editor would bypass the reject cascade entirely (the linked `payment_beasiswa`/`pam_records` rows would stay whatever they were), leaving an inconsistent state. `rejected` should only ever be reached through Task 6/7's reject actions.

- [ ] **Step 1: Add `rejected` to the Jinja badge logic (line 486)**

Find:

```html
          <span class="badge {% if r.status == 'complete' %}badge-green{% elif r.status == 'on_process' or r.status == 'partial' %}badge-yellow{% elif r.status == 'open' %}badge-blue{% else %}badge-gray{% endif %}">
```

Replace with:

```html
          <span class="badge {% if r.status == 'complete' %}badge-green{% elif r.status == 'on_process' or r.status == 'partial' %}badge-yellow{% elif r.status == 'open' %}badge-blue{% elif r.status == 'rejected' %}badge-red{% else %}badge-gray{% endif %}">
```

- [ ] **Step 2: Add `rejected` to the JS badge logic (line 1271)**

Find:

```javascript
          const cls = value === "complete" ? "badge-green" : value === "on_process" ? "badge-yellow" : value === "open" ? "badge-blue" : "badge-gray";
```

Replace with:

```javascript
          const cls = value === "complete" ? "badge-green" : value === "on_process" ? "badge-yellow" : value === "open" ? "badge-blue" : value === "rejected" ? "badge-red" : "badge-gray";
```

- [ ] **Step 3: Add `rejected` option to the 3 filter dropdowns**

Find (line 208-213):

```html
    <option value="">Semua Status</option>
    <option value="active" {% if active_sf == 'active' %}selected{% endif %}>Open + On Process</option>
    <option value="open" {% if active_sf == 'open' %}selected{% endif %}>Open</option>
    <option value="on_process" {% if active_sf == 'on_process' %}selected{% endif %}>On Process</option>
    <option value="complete" {% if active_sf == 'complete' %}selected{% endif %}>Complete</option>
```

Replace with:

```html
    <option value="">Semua Status</option>
    <option value="active" {% if active_sf == 'active' %}selected{% endif %}>Open + On Process</option>
    <option value="open" {% if active_sf == 'open' %}selected{% endif %}>Open</option>
    <option value="on_process" {% if active_sf == 'on_process' %}selected{% endif %}>On Process</option>
    <option value="complete" {% if active_sf == 'complete' %}selected{% endif %}>Complete</option>
    <option value="rejected" {% if active_sf == 'rejected' %}selected{% endif %}>Rejected</option>
```

Find (line 557-564, `#sf-status`):

```html
    <select id="sf-status" onchange="renderSummary()" style="font-size:.82rem">
      <option value="active" selected>Open & On Process</option>
      <option value="">Semua</option>
      <option value="open">Open</option>
      <option value="on_process">On Process</option>
      <option value="complete">Complete</option>
    </select>
```

Replace with:

```html
    <select id="sf-status" onchange="renderSummary()" style="font-size:.82rem">
      <option value="active" selected>Open & On Process</option>
      <option value="">Semua</option>
      <option value="open">Open</option>
      <option value="on_process">On Process</option>
      <option value="complete">Complete</option>
      <option value="rejected">Rejected</option>
    </select>
```

Find (line 772-780, `#adv-status`):

```html
    <select id="adv-status" onchange="renderAdvance()" style="font-size:.82rem">
      <option value="">Semua</option>
      <option value="open">Open</option>
      <option value="on_process">On Process</option>
      <option value="paid">Paid (Menunggu Realisasi)</option>
      <option value="complete">Complete</option>
```

Replace with:

```html
    <select id="adv-status" onchange="renderAdvance()" style="font-size:.82rem">
      <option value="">Semua</option>
      <option value="open">Open</option>
      <option value="on_process">On Process</option>
      <option value="paid">Paid (Menunggu Realisasi)</option>
      <option value="complete">Complete</option>
      <option value="rejected">Rejected</option>
```

(Leave the closing `</select>` on its existing line untouched — only the option list above it changes.)

- [ ] **Step 4: Manual verification**

Navigate to the ETF Payment Application module, filter by "Rejected" in each of the 3 dropdowns touched above, and confirm a PA rejected via Task 6/7 shows up with the red badge.

- [ ] **Step 5: Commit**

```bash
git add app/templates/etf_payment_application/index.html
git commit -m "feat: add rejected badge and filter option to PA list"
```

---

## Final Verification

- [ ] Run the complete test suite one file at a time (avoids the pre-existing shared-DB `PermissionError` flakiness when running combined):

```bash
cd app
python -m pytest tests/test_pam_pa_cascade.py -v
python -m pytest tests/test_pam_remove_student.py -v
python -m pytest tests/test_beasiswa_service.py -v
python -m pytest tests/test_pam_service.py -v
python -m pytest tests/test_payment_memo_service.py -v
```

Expected: all PASS.

- [ ] Full manual walkthrough: reject one student from a multi-student PAM group (Task 6), reject a whole single-student PAM group via the memo bar (Task 7), confirm both disappear from Open PAM and reappear with the Rejected badge in their pillar tab (Task 8) and, for AGRI, in the ETF Payment Application PA list (Task 9). Confirm the previously-broken scenario from Task 2 no longer applies: reject one sibling, then delete ("Hapus") the last remaining active sibling in the same group, and confirm the shared PA correctly reverts to `open`.
