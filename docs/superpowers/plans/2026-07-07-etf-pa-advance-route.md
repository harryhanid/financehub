# ETF PA Route GL vs Advance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let ETF Payment Application Input route a payment as `GL` (today's behavior) or `Advance`
(quarantined under pillar `ADVANCE` until an explicit realization step corrects the amount and
returns it to its original pillar).

**Architecture:** Reuse the existing `ADVANCE` pillar + `advance_pam_lines` table (already shipped
for SMT) and the existing `save_pa_payment` / `insert_payment_rows` / `set_pam_complete_cascade`
functions — extend them with a `route` parameter instead of writing parallel code paths. Add 3 new
columns (`advance_amount`, `realized_amount`, `tgl_realisasi`) to `payment_beasiswa` and 1 column
(`route`) to each `*_pa_lines` table. Add 2 new backend functions (`get_advance_payments`,
`realize_advance_payment`) and 2 new routes for the Advance tab.

**Tech Stack:** Python 3.14, Flask, SQLite (WAL mode), pytest, vanilla JS/Jinja2 templates.

## Global Constraints

- Route default is always `"gl"` — every existing caller of `insert_payment_rows`/`save_pa_payment`
  that doesn't pass `route` must behave exactly as today (regression tests required per task).
- `payment_beasiswa.pillar` always stores the real target pillar (AGRI/APP/LAND/SETF) — it is
  **never** set to `"ADVANCE"`. Only `pam_records.pillar` becomes `"ADVANCE"` while quarantined.
- `pam_records.status` keeps its existing 2-state flow (`open`/`on_process` → `complete`). Do not
  add new values there — the Advance-specific "paid but not realized" state lives on
  `payment_beasiswa.status` only.
- No new PA-header table. No automatic follow-up PAM for selisih (variance) — realization only
  updates existing rows in place.
- Full spec: `docs/superpowers/specs/2026-07-07-etf-pa-advance-route-design.md`.

---

### Task 1: Schema — `route` column on PA-lines, 3 new columns on `payment_beasiswa`

**Files:**
- Modify: `app/database.py` (inside `migrate_db()`, near the other `payment_beasiswa`
  `ALTER TABLE ... ADD COLUMN` calls around line 525-536)
- Test: `app/tests/test_advance_route_schema.py` (new)

**Interfaces:**
- Produces: columns `etf_pa_lines.route`, `app_pa_lines.route`, `sml_pa_lines.route`,
  `setf_pa_lines.route` (all `TEXT`, nullable); `payment_beasiswa.advance_amount` (`REAL`,
  nullable), `payment_beasiswa.realized_amount` (`REAL`, nullable),
  `payment_beasiswa.tgl_realisasi` (`TEXT`, nullable).

- [ ] **Step 1: Write the failing test**

```python
# app/tests/test_advance_route_schema.py
import os, sys, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config
config.DB_PATH = os.path.join(os.path.dirname(__file__), "test_advance_schema.db")

from database import init_db, get_conn


@pytest.fixture(autouse=True)
def clean_db():
    if os.path.exists(config.DB_PATH):
        os.remove(config.DB_PATH)
    init_db()
    yield
    if os.path.exists(config.DB_PATH):
        os.remove(config.DB_PATH)


@pytest.mark.parametrize("table", ["etf_pa_lines", "app_pa_lines", "sml_pa_lines", "setf_pa_lines"])
def test_pa_lines_have_route_column(table):
    conn = get_conn()
    cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    conn.close()
    assert "route" in cols, f"{table} missing 'route' column"


def test_payment_beasiswa_has_advance_realization_columns():
    conn = get_conn()
    cols = [r[1] for r in conn.execute("PRAGMA table_info(payment_beasiswa)").fetchall()]
    conn.close()
    assert "advance_amount"  in cols
    assert "realized_amount" in cols
    assert "tgl_realisasi"   in cols


def test_migrate_db_idempotent_for_new_columns():
    """Running migrate_db() twice must not raise (columns already exist on 2nd run)."""
    from database import migrate_db
    migrate_db()
    migrate_db()
    conn = get_conn()
    cols = [r[1] for r in conn.execute("PRAGMA table_info(payment_beasiswa)").fetchall()]
    conn.close()
    assert "advance_amount" in cols
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd app && python -m pytest tests/test_advance_route_schema.py -v`
Expected: FAIL — `assert "route" in cols` / `assert "advance_amount" in cols` (columns don't exist yet).

- [ ] **Step 3: Add the migration**

In `app/database.py`, inside `migrate_db()`, add (near the other `payment_beasiswa` column
migrations, e.g. right after the `etf_pa_line_id` FK-strip block):

```python
    for pa_lines_tbl in ["etf_pa_lines", "app_pa_lines", "sml_pa_lines", "setf_pa_lines"]:
        try:
            conn.execute(f"ALTER TABLE {pa_lines_tbl} ADD COLUMN route TEXT")
            conn.commit()
        except Exception:
            pass
    for col in ["advance_amount", "realized_amount"]:
        try:
            conn.execute(f"ALTER TABLE payment_beasiswa ADD COLUMN {col} REAL")
            conn.commit()
        except Exception:
            pass
    try:
        conn.execute("ALTER TABLE payment_beasiswa ADD COLUMN tgl_realisasi TEXT")
        conn.commit()
    except Exception:
        pass
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd app && python -m pytest tests/test_advance_route_schema.py -v`
Expected: 6 passed (4 parametrized + 2).

- [ ] **Step 5: Commit**

```bash
cd /c/Financehub
git add app/database.py app/tests/test_advance_route_schema.py
git commit -m "feat: add route + advance realization columns to PA schema"
```

---

### Task 2: `insert_payment_rows` accepts a `route` param, snapshots `advance_amount`

**Files:**
- Modify: `app/modules/beasiswa/service.py:337` (`insert_payment_rows` signature + INSERT statement)
- Test: `app/tests/test_pam_service.py` (append)

**Interfaces:**
- Consumes: nothing new from other tasks.
- Produces: `insert_payment_rows(conn, company_id, company_code, tanggal, pillar, perusahaan, rows, route="gl")`
  — new optional 8th positional/keyword param, default `"gl"` (regression-safe). When
  `route == "advance"`, each inserted `payment_beasiswa` row gets `advance_amount = amount`
  (its own per-row amount, not the header total). When `route == "gl"` (default),
  `advance_amount` stays `NULL`.

- [ ] **Step 1: Write the failing test**

```python
# append to app/tests/test_pam_service.py

def test_insert_payment_rows_advance_route_sets_advance_amount():
    from modules.beasiswa.service import insert_payment_rows
    conn = get_conn()
    rows = [{"siswa_code": "S001", "cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 5_000_000}]
    result = insert_payment_rows(conn, COMPANY_ID, COMPANY_CODE, "2026-07-07", "AGRI", "PT. ABC",
                                  rows, route="advance")
    conn.commit()
    assert result["ok"] is True
    row = conn.execute(
        "SELECT advance_amount, realized_amount, pillar FROM payment_beasiswa WHERE id=?",
        (result["payment_ids"][0],)
    ).fetchone()
    conn.close()
    assert row["advance_amount"]  == 5_000_000
    assert row["realized_amount"] is None
    assert row["pillar"]          == "AGRI"   # target pillar unchanged, never "ADVANCE" here


def test_insert_payment_rows_default_route_gl_leaves_advance_amount_null():
    from modules.beasiswa.service import insert_payment_rows
    conn = get_conn()
    rows = [{"siswa_code": "S001", "cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 5_000_000}]
    result = insert_payment_rows(conn, COMPANY_ID, COMPANY_CODE, "2026-07-07", "AGRI", "PT. ABC", rows)
    conn.commit()
    row = conn.execute(
        "SELECT advance_amount FROM payment_beasiswa WHERE id=?", (result["payment_ids"][0],)
    ).fetchone()
    conn.close()
    assert row["advance_amount"] is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd app && python -m pytest tests/test_pam_service.py -k advance_route -v`
Expected: FAIL — `TypeError: insert_payment_rows() got an unexpected keyword argument 'route'`.

- [ ] **Step 3: Implement**

In `app/modules/beasiswa/service.py`, change the signature (line 337-339):

```python
def insert_payment_rows(conn, company_id: int, company_code: str,
                        tanggal: str, pillar: str, perusahaan: str,
                        rows: list, route: str = "gl") -> dict:
```

Then in the per-row INSERT (the `INSERT INTO payment_beasiswa` block, currently columns
`...,etf_pa_line_id,status`), add `advance_amount` to the column list and values:

```python
        cur = conn.execute(
            """INSERT INTO payment_beasiswa
               (company_id,siswa_code,cat1,cat2,tanggal,amount,pillar,perusahaan,
                tgl_pengajuan,tgl_receive,tgl_pa,tgl_final,cat3,cat4,etf_pa_line_id,
                advance_amount,status)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'open')""",
            (company_id, siswa_code,
             row.get("cat1", ""), row.get("cat2", ""),
             tanggal, amount, pillar, perusahaan,
             row.get("tgl_pengajuan", ""), row.get("tgl_receive", ""),
             row.get("tgl_pa", ""),        row.get("tgl_final", ""),
             row.get("cat3", ""),          row.get("cat4", ""),
             etf_pa_line_id,
             amount if route == "advance" else None)
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd app && python -m pytest tests/test_pam_service.py -v`
Expected: all pass, including the 2 new tests and every pre-existing test in that file (regression check).

- [ ] **Step 5: Commit**

```bash
cd /c/Financehub
git add app/modules/beasiswa/service.py app/tests/test_pam_service.py
git commit -m "feat: insert_payment_rows accepts route param, snapshots advance_amount"
```

---

### Task 3: `save_pa_payment` routes to pillar `ADVANCE` and tags PA-lines with `route`

**Files:**
- Modify: `app/modules/payment_memo/service.py:711` (`save_pa_payment`)
- Test: `app/tests/test_pam_service.py` (append)

**Interfaces:**
- Consumes: `insert_payment_rows(..., route=...)` from Task 2.
- Produces: `save_pa_payment(company_id, company_code, data)` now reads `data.get("route", "gl")`.
  When `route == "advance"`: the `pam_records` row created gets `pillar="ADVANCE"` (not the tab's
  real pillar), and every `*_pa_lines` row touched gets `route='advance'`. When `route == "gl"`
  (default, unchanged behavior): `pam_records.pillar` = the real pillar as today, and PA-lines get
  `route='gl'`.

- [ ] **Step 1: Write the failing test**

```python
# append to app/tests/test_pam_service.py

def test_save_pa_payment_route_advance_quarantines_pam_records():
    from modules.payment_memo.service import save_pa_payment
    result = save_pa_payment(COMPANY_ID, COMPANY_CODE, {
        "tab":        "agri",
        "route":      "advance",
        "tanggal":    "2026-07-07",
        "pam_no":     "PAM-001-ETF-07-2026",
        "keterangan": "Advance test",
        "perusahaan": "PT. ABC",
        "pillar":     "AGRI",
        "rows":       [{"siswa_code": "S001", "cat1": "By Pendidikan",
                        "cat2": "Semester 1", "amount": 2_000_000}],
    })
    assert result["ok"] is True
    conn = get_conn()
    pam = conn.execute(
        "SELECT pillar FROM pam_records WHERE company_id=? AND pam_no=?",
        (COMPANY_ID, "PAM-001-ETF-07-2026")
    ).fetchone()
    pb = conn.execute(
        "SELECT pillar, advance_amount FROM payment_beasiswa WHERE pam=?",
        ("PAM-001-ETF-07-2026",)
    ).fetchone()
    conn.close()
    assert pam["pillar"] == "ADVANCE"
    assert pb["pillar"]  == "AGRI"          # target pillar preserved on the line
    assert pb["advance_amount"] == 2_000_000


def test_save_pa_payment_route_gl_default_unchanged():
    from modules.payment_memo.service import save_pa_payment
    result = save_pa_payment(COMPANY_ID, COMPANY_CODE, {
        "tab":        "agri",
        "tanggal":    "2026-07-07",
        "pam_no":     "PAM-002-ETF-07-2026",
        "keterangan": "GL test",
        "perusahaan": "PT. ABC",
        "pillar":     "AGRI",
        "rows":       [{"siswa_code": "S001", "cat1": "By Pendidikan",
                        "cat2": "Semester 1", "amount": 1_000_000}],
    })
    assert result["ok"] is True
    conn = get_conn()
    pam = conn.execute(
        "SELECT pillar FROM pam_records WHERE company_id=? AND pam_no=?",
        (COMPANY_ID, "PAM-002-ETF-07-2026")
    ).fetchone()
    conn.close()
    assert pam["pillar"] == "AGRI"


def test_save_pa_payment_advance_tags_pa_lines_route():
    from modules.payment_memo.service import save_pa_payment
    conn = get_conn()
    conn.execute(
        "INSERT INTO siswa (company_id, code, nama) VALUES (?,?,?)",
        (COMPANY_ID, "S010", "Test Siswa")
    )
    sid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.execute(
        "INSERT INTO etf_pa (company_id, pa_number, status, created_at) VALUES (?,?,?,?)",
        (COMPANY_ID, "PA/TEST/001/2026", "on_process", "2026-07-07T00:00:00")
    )
    pa_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.execute(
        "INSERT INTO etf_pa_lines (pa_id, student_id, jenis_pembayaran, jumlah_pembayaran) VALUES (?,?,?,?)",
        (pa_id, sid, "By Pendidikan", 3_000_000)
    )
    line_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()
    conn.close()

    result = save_pa_payment(COMPANY_ID, COMPANY_CODE, {
        "tab": "agri", "route": "advance", "tanggal": "2026-07-07",
        "pam_no": "PAM-003-ETF-07-2026", "keterangan": "x",
        "perusahaan": "PT. ABC", "pillar": "AGRI",
        "rows": [{"siswa_code": "S010", "cat1": "By Pendidikan", "cat2": "Semester 1",
                  "amount": 3_000_000, "etf_pa_line_id": line_id}],
    })
    assert result["ok"] is True

    conn = get_conn()
    line = conn.execute("SELECT route FROM etf_pa_lines WHERE id=?", (line_id,)).fetchone()
    conn.close()
    assert line["route"] == "advance"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd app && python -m pytest tests/test_pam_service.py -k "route_advance or route_gl_default or advance_tags" -v`
Expected: FAIL — `pam["pillar"] == "ADVANCE"` fails (currently `"AGRI"`), because `route` is
ignored by `save_pa_payment` today.

- [ ] **Step 3: Implement**

In `app/modules/payment_memo/service.py`, in `save_pa_payment` (line ~711), after the existing
`rows = data.get("rows") or []` line, add:

```python
    route = (data.get("route") or "gl").lower()
```

Change the `insert_payment_rows` call to pass `route`:

```python
        ins = insert_payment_rows(conn, company_id, company_code,
                                  tanggal, pillar, perusahaan, rows, route=route)
```

Change the `pam_records` INSERT to use `pillar_for_pam` instead of the raw `pillar`:

```python
        pillar_for_pam = "ADVANCE" if route == "advance" else pillar
```

(add this line right before the `INSERT INTO pam_records` block), then replace the `pillar` value
in that INSERT's parameter tuple with `pillar_for_pam` — the INSERT currently is:

```python
        conn.execute(
            """INSERT INTO pam_records
               (company_id, pam_no, pam_date, requestors_name, keterangan,
                total_amount, dpp, ppn, due_date, pillar, source,
                pt, cost_center, status, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,'open',?)""",
            (company_id, pam_no, tanggal,
             config.PAM_DEFAULT_REQUESTOR, keterangan,
             total, total, 0.0,
             due_date, pillar_for_pam, "beasiswa",
             perusahaan, cost_center, _ts())
        )
```

Finally, in step 4 of the existing function (the block that does
`UPDATE {pa_tbl} SET nomor_pam=?, status='on_process' WHERE id IN (...)`), add one more UPDATE
right after it, still inside the `if line_ids:` block:

```python
            conn.execute(
                f"UPDATE {lines_tbl} SET route=? WHERE id IN ({ph})",
                [route] + list(line_ids)
            )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd app && python -m pytest tests/test_pam_service.py -v`
Expected: all pass (new tests + full regression of the file, including the existing
`test_save_pa_payment_*` tests).

- [ ] **Step 5: Commit**

```bash
cd /c/Financehub
git add app/modules/payment_memo/service.py app/tests/test_pam_service.py
git commit -m "feat: save_pa_payment routes ADVANCE pillar and tags PA-lines route"
```

---

### Task 4: `set_pam_complete_cascade` sets `payment_beasiswa.status='paid'` for ADVANCE pillar

**Files:**
- Modify: `app/modules/payment_memo/service.py:2153` (`set_pam_complete_cascade`)
- Test: `app/tests/test_pam_pa_cascade.py` (append)

**Interfaces:**
- Consumes: nothing new.
- Produces: no signature change — same `set_pam_complete_cascade(pam_id, tanggal_bayar, company_id)`.
  Behavior change: when the PAM's `pam_records.pillar == "ADVANCE"`, the cascaded
  `payment_beasiswa.status` becomes `"paid"` instead of `"complete"`. `pam_records.status` still
  becomes `"complete"` as before (unchanged) — this is intentional per the spec's status table
  (header finishes its own 2-state flow; the per-line Advance state lives on `payment_beasiswa`).

- [ ] **Step 1: Write the failing test**

```python
# append to app/tests/test_pam_pa_cascade.py

def test_set_pam_complete_cascade_advance_pillar_sets_paid_not_complete():
    from modules.payment_memo.service import save_pa_payment, set_pam_complete_cascade
    result = save_pa_payment(COMPANY_ID, COMPANY_CODE, {
        "tab": "agri", "route": "advance", "tanggal": "2026-07-07",
        "pam_no": "PAM-010-ETF-07-2026", "keterangan": "adv",
        "perusahaan": "PT. ABC", "pillar": "AGRI",
        "rows": [{"siswa_code": "S001", "cat1": "By Pendidikan", "cat2": "Semester 1",
                  "amount": 4_000_000}],
    })
    assert result["ok"] is True

    conn = get_conn()
    pam_id = conn.execute(
        "SELECT id FROM pam_records WHERE company_id=? AND pam_no=?",
        (COMPANY_ID, "PAM-010-ETF-07-2026")
    ).fetchone()["id"]
    conn.close()

    cascade = set_pam_complete_cascade(pam_id, "2026-07-10", COMPANY_ID)
    assert cascade["ok"] is True

    conn = get_conn()
    pam = conn.execute("SELECT status, pillar FROM pam_records WHERE id=?", (pam_id,)).fetchone()
    pb  = conn.execute(
        "SELECT status FROM payment_beasiswa WHERE pam=?", ("PAM-010-ETF-07-2026",)
    ).fetchone()
    conn.close()

    assert pam["status"] == "complete"   # header flow unchanged
    assert pam["pillar"] == "ADVANCE"    # not yet moved — realization hasn't happened
    assert pb["status"]  == "paid"       # NOT 'complete' — quarantined until realize
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd app && python -m pytest tests/test_pam_pa_cascade.py -k advance_pillar_sets_paid -v`
Expected: FAIL — `assert pb["status"] == "paid"` fails, actual is `"complete"`.

- [ ] **Step 3: Implement**

In `app/modules/payment_memo/service.py`, inside `set_pam_complete_cascade`, find the `else` branch
(cascade to `payment_beasiswa` for the beasiswa iPay flow, around line 2190-2204):

```python
    else:
        pillar   = pam.get("pillar") or ""
        paid_col = _BEASISWA_PAID_COL.get(pillar)
        if paid_col:
            conn.execute(
                f'UPDATE payment_beasiswa SET status=\'complete\', "{paid_col}"=? '
                f'WHERE pam=? AND company_id=?',
                (tanggal_bayar, pam_no, company_id)
            )
        else:
            conn.execute(
                "UPDATE payment_beasiswa SET status='complete' WHERE pam=? AND company_id=?",
                (pam_no, company_id)
            )
```

Replace it with:

```python
    else:
        pillar = pam.get("pillar") or ""
        if pillar == "ADVANCE":
            conn.execute(
                "UPDATE payment_beasiswa SET status='paid' WHERE pam=? AND company_id=?",
                (pam_no, company_id)
            )
        else:
            paid_col = _BEASISWA_PAID_COL.get(pillar)
            if paid_col:
                conn.execute(
                    f'UPDATE payment_beasiswa SET status=\'complete\', "{paid_col}"=? '
                    f'WHERE pam=? AND company_id=?',
                    (tanggal_bayar, pam_no, company_id)
                )
            else:
                conn.execute(
                    "UPDATE payment_beasiswa SET status='complete' WHERE pam=? AND company_id=?",
                    (pam_no, company_id)
                )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd app && python -m pytest tests/test_pam_pa_cascade.py -v`
Expected: all pass, including every pre-existing cascade test in the file (AGRI/APP/LAND/ENERGY/SETF
cascades must be completely unaffected).

- [ ] **Step 5: Commit**

```bash
cd /c/Financehub
git add app/modules/payment_memo/service.py app/tests/test_pam_pa_cascade.py
git commit -m "fix: set_pam_complete_cascade marks ADVANCE lines paid, not complete"
```

---

### Task 5: `get_advance_payments` — per-line query for the Advance tab

**Files:**
- Modify: `app/modules/payment_memo/service.py` (new function, place near `get_pam_by_pillar` at line 298)
- Test: `app/tests/test_pam_service.py` (append)

**Interfaces:**
- Consumes: nothing new.
- Produces: `get_advance_payments(company_id: int, status: str = "", search: str = "", bulan: str = "", tahun: str = "") -> list`.
  Returns one dict per `payment_beasiswa` row currently quarantined under a PAM with
  `pam_records.pillar == 'ADVANCE'`, with keys from `payment_beasiswa.*` plus `nama` (student name)
  and `pam_date` (from `pam_records`). This is per-line (unlike `get_pam_by_pillar`, which is
  per-header) because realization happens one `payment_beasiswa` row at a time.

- [ ] **Step 1: Write the failing test**

```python
# append to app/tests/test_pam_service.py

def test_get_advance_payments_returns_quarantined_lines_only():
    from modules.payment_memo.service import save_pa_payment, get_advance_payments
    save_pa_payment(COMPANY_ID, COMPANY_CODE, {
        "tab": "agri", "route": "advance", "tanggal": "2026-07-07",
        "pam_no": "PAM-020-ETF-07-2026", "keterangan": "adv",
        "perusahaan": "PT. ABC", "pillar": "AGRI",
        "rows": [{"siswa_code": "S001", "cat1": "By Pendidikan", "cat2": "Semester 1",
                  "amount": 2_500_000}],
    })
    save_pa_payment(COMPANY_ID, COMPANY_CODE, {
        "tab": "agri", "tanggal": "2026-07-07",   # route=gl (default) — must NOT show up
        "pam_no": "PAM-021-ETF-07-2026", "keterangan": "gl",
        "perusahaan": "PT. ABC", "pillar": "AGRI",
        "rows": [{"siswa_code": "S001", "cat1": "By Pendidikan", "cat2": "Semester 1",
                  "amount": 1_000_000}],
    })
    rows = get_advance_payments(COMPANY_ID)
    assert len(rows) == 1
    assert rows[0]["pam"]    == "PAM-020-ETF-07-2026"
    assert rows[0]["amount"] == 2_500_000


def test_get_advance_payments_filters_by_status():
    from modules.payment_memo.service import save_pa_payment, get_advance_payments
    save_pa_payment(COMPANY_ID, COMPANY_CODE, {
        "tab": "agri", "route": "advance", "tanggal": "2026-07-07",
        "pam_no": "PAM-022-ETF-07-2026", "keterangan": "adv",
        "perusahaan": "PT. ABC", "pillar": "AGRI",
        "rows": [{"siswa_code": "S001", "cat1": "By Pendidikan", "cat2": "Semester 1",
                  "amount": 1_500_000}],
    })
    assert get_advance_payments(COMPANY_ID, status="open") != []
    assert get_advance_payments(COMPANY_ID, status="paid") == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd app && python -m pytest tests/test_pam_service.py -k get_advance_payments -v`
Expected: FAIL — `ImportError: cannot import name 'get_advance_payments'`.

- [ ] **Step 3: Implement**

Add to `app/modules/payment_memo/service.py`, near `get_pam_by_pillar`:

```python
def get_advance_payments(company_id: int, status: str = "", search: str = "",
                         bulan: str = "", tahun: str = "") -> list:
    """Per-line view of payment_beasiswa rows quarantined under pillar ADVANCE."""
    sql = """
        SELECT pb.*, s.nama, pr.pam_date
        FROM payment_beasiswa pb
        JOIN pam_records pr ON pr.pam_no = pb.pam AND pr.company_id = pb.company_id
        LEFT JOIN siswa s ON s.company_id = pb.company_id AND s.code = pb.siswa_code
        WHERE pb.company_id = ? AND pr.pillar = 'ADVANCE'
    """
    params = [company_id]
    if status:
        sql    += " AND pb.status = ?"
        params += [status]
    if search:
        q       = f"%{search}%"
        sql    += " AND (pb.pam LIKE ? OR s.nama LIKE ?)"
        params += [q, q]
    if bulan:
        sql    += " AND strftime('%m', pb.tanggal) = ?"
        params += [bulan.zfill(2)]
    if tahun:
        sql    += " AND strftime('%Y', pb.tanggal) = ?"
        params += [tahun]
    sql += " ORDER BY pb.tanggal DESC"
    conn = get_conn()
    rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
    conn.close()
    return rows
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd app && python -m pytest tests/test_pam_service.py -v`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
cd /c/Financehub
git add app/modules/payment_memo/service.py app/tests/test_pam_service.py
git commit -m "feat: add get_advance_payments per-line query for Advance tab"
```

---

### Task 6: `realize_advance_payment` — realization + pillar close cascade

**Files:**
- Modify: `app/modules/payment_memo/service.py` (new function, near `set_pam_complete_cascade`)
- Test: `app/tests/test_pam_pa_cascade.py` (append)

**Interfaces:**
- Consumes: `payment_beasiswa` rows produced by Tasks 2/3 (must have `status='paid'` from Task 4's
  cascade and a non-NULL `advance_amount` from Task 2).
- Produces: `realize_advance_payment(payment_id: int, realized_amount: float, tgl_realisasi: str, company_id: int) -> dict`.
  Returns `{"ok": True, "pesan": ..., "selisih": <float>}` on success, or
  `{"ok": False, "pesan": "..."}` on validation failure. Updates the target row's `amount`,
  `realized_amount`, `tgl_realisasi`, `status='complete'`; once every `payment_beasiswa` row
  sharing that `pam` is `complete`, updates `pam_records.pillar` from `"ADVANCE"` to the row's own
  `payment_beasiswa.pillar` (the original target pillar).

- [ ] **Step 1: Write the failing test**

```python
# append to app/tests/test_pam_pa_cascade.py

def _setup_paid_advance(pam_no="PAM-030-ETF-07-2026", amount=3_000_000):
    """Helper: create + pay one Advance payment_beasiswa row. Returns (payment_id, pam_id)."""
    from modules.payment_memo.service import save_pa_payment, set_pam_complete_cascade
    save_pa_payment(COMPANY_ID, COMPANY_CODE, {
        "tab": "agri", "route": "advance", "tanggal": "2026-07-07",
        "pam_no": pam_no, "keterangan": "adv",
        "perusahaan": "PT. ABC", "pillar": "AGRI",
        "rows": [{"siswa_code": "S001", "cat1": "By Pendidikan", "cat2": "Semester 1",
                  "amount": amount}],
    })
    conn = get_conn()
    pam_id     = conn.execute(
        "SELECT id FROM pam_records WHERE company_id=? AND pam_no=?", (COMPANY_ID, pam_no)
    ).fetchone()["id"]
    payment_id = conn.execute(
        "SELECT id FROM payment_beasiswa WHERE pam=?", (pam_no,)
    ).fetchone()["id"]
    conn.close()
    set_pam_complete_cascade(pam_id, "2026-07-10", COMPANY_ID)
    return payment_id, pam_id


def test_realize_advance_payment_updates_amount_and_closes_pillar():
    from modules.payment_memo.service import realize_advance_payment
    payment_id, pam_id = _setup_paid_advance()

    result = realize_advance_payment(payment_id, 2_700_000, "2026-07-20", COMPANY_ID)
    assert result["ok"] is True
    assert result["selisih"] == 300_000   # 3_000_000 advance - 2_700_000 realized

    conn = get_conn()
    pb  = conn.execute(
        "SELECT amount, realized_amount, tgl_realisasi, status FROM payment_beasiswa WHERE id=?",
        (payment_id,)
    ).fetchone()
    pam = conn.execute("SELECT pillar FROM pam_records WHERE id=?", (pam_id,)).fetchone()
    conn.close()

    assert pb["amount"]          == 2_700_000
    assert pb["realized_amount"] == 2_700_000
    assert pb["tgl_realisasi"]   == "2026-07-20"
    assert pb["status"]          == "complete"
    assert pam["pillar"]         == "AGRI"   # moved out of ADVANCE


def test_realize_advance_payment_rejects_not_yet_paid():
    from modules.payment_memo.service import save_pa_payment, realize_advance_payment
    save_pa_payment(COMPANY_ID, COMPANY_CODE, {
        "tab": "agri", "route": "advance", "tanggal": "2026-07-07",
        "pam_no": "PAM-031-ETF-07-2026", "keterangan": "adv",
        "perusahaan": "PT. ABC", "pillar": "AGRI",
        "rows": [{"siswa_code": "S001", "cat1": "By Pendidikan", "cat2": "Semester 1",
                  "amount": 1_000_000}],
    })
    conn = get_conn()
    payment_id = conn.execute(
        "SELECT id FROM payment_beasiswa WHERE pam=?", ("PAM-031-ETF-07-2026",)
    ).fetchone()["id"]
    conn.close()

    result = realize_advance_payment(payment_id, 900_000, "2026-07-20", COMPANY_ID)
    assert result["ok"] is False


def test_realize_advance_payment_rejects_non_advance_row():
    from modules.payment_memo.service import save_pa_payment, realize_advance_payment
    save_pa_payment(COMPANY_ID, COMPANY_CODE, {
        "tab": "agri", "tanggal": "2026-07-07",   # route=gl
        "pam_no": "PAM-032-ETF-07-2026", "keterangan": "gl",
        "perusahaan": "PT. ABC", "pillar": "AGRI",
        "rows": [{"siswa_code": "S001", "cat1": "By Pendidikan", "cat2": "Semester 1",
                  "amount": 1_000_000}],
    })
    conn = get_conn()
    payment_id = conn.execute(
        "SELECT id FROM payment_beasiswa WHERE pam=?", ("PAM-032-ETF-07-2026",)
    ).fetchone()["id"]
    conn.close()

    result = realize_advance_payment(payment_id, 900_000, "2026-07-20", COMPANY_ID)
    assert result["ok"] is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd app && python -m pytest tests/test_pam_pa_cascade.py -k realize_advance_payment -v`
Expected: FAIL — `ImportError: cannot import name 'realize_advance_payment'`.

- [ ] **Step 3: Implement**

Add to `app/modules/payment_memo/service.py`, near `set_pam_complete_cascade`:

```python
def realize_advance_payment(payment_id: int, realized_amount, tgl_realisasi: str,
                            company_id: int) -> dict:
    if not tgl_realisasi:
        return {"ok": False, "pesan": "Tanggal realisasi wajib diisi."}
    try:
        realized_amount = float(realized_amount)
    except (TypeError, ValueError):
        return {"ok": False, "pesan": "Realized amount tidak valid."}
    if realized_amount <= 0:
        return {"ok": False, "pesan": "Realized amount harus > 0."}

    conn = get_conn()
    row = conn.execute(
        "SELECT id, pam, pillar, status, advance_amount FROM payment_beasiswa "
        "WHERE id=? AND company_id=?",
        (payment_id, company_id)
    ).fetchone()
    if not row:
        conn.close()
        return {"ok": False, "pesan": "Payment tidak ditemukan."}
    if row["advance_amount"] is None:
        conn.close()
        return {"ok": False, "pesan": "Baris ini bukan payment Advance."}
    if row["status"] != "paid":
        conn.close()
        return {"ok": False, "pesan": "Payment belum berstatus 'paid', tidak bisa direalisasi."}

    pam_no        = row["pam"]
    target_pillar = row["pillar"]
    selisih       = row["advance_amount"] - realized_amount
    ts            = _ts()

    conn.execute(
        """UPDATE payment_beasiswa
           SET realized_amount=?, tgl_realisasi=?, amount=?, status='complete'
           WHERE id=?""",
        (realized_amount, tgl_realisasi, realized_amount, payment_id)
    )

    remaining = conn.execute(
        "SELECT COUNT(*) FROM payment_beasiswa WHERE pam=? AND company_id=? AND status != 'complete'",
        (pam_no, company_id)
    ).fetchone()[0]
    if remaining == 0:
        conn.execute(
            "UPDATE pam_records SET pillar=?, updated_at=? WHERE pam_no=? AND company_id=?",
            (target_pillar, ts, pam_no, company_id)
        )

    conn.commit()
    conn.close()
    return {"ok": True, "pesan": "Realisasi tersimpan.", "selisih": selisih}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd app && python -m pytest tests/test_pam_pa_cascade.py -v`
Expected: all pass, full file regression-clean.

- [ ] **Step 5: Commit**

```bash
cd /c/Financehub
git add app/modules/payment_memo/service.py app/tests/test_pam_pa_cascade.py
git commit -m "feat: add realize_advance_payment with pillar close cascade"
```

---

### Task 7: Routes — list Advance payments, realize one

**Files:**
- Modify: `app/modules/payment_memo/routes.py` (add 2 routes near `ipay_save_pa`, line 646)
- Test: `app/tests/test_memo_api.py` (append)

**Interfaces:**
- Consumes: `get_advance_payments` (Task 5), `realize_advance_payment` (Task 6).
- Produces: `GET /payment-memo/advance/list?status=&search=&bulan=&tahun=` →
  `{"ok": true, "rows": [...]}`. `POST /payment-memo/advance/<int:payment_id>/realize` with JSON
  body `{"realized_amount": <number>, "tgl_realisasi": "YYYY-MM-DD"}` →
  `{"ok": true, "pesan": ..., "selisih": <number>}` or `{"ok": false, "pesan": ...}`.

**Note:** `test_payment_memo_ipay.py` only has service-layer tests today (no Flask test client
usage). Route-level tests in this codebase live in `test_memo_api.py` instead, using the global
`client` fixture from `tests/conftest.py` (JWT bearer token from `/auth/login` + `company_id` set
via `client.session_transaction()`). Add these 2 tests to `test_memo_api.py` to follow that
established convention, rather than inventing a new pattern in `test_payment_memo_ipay.py`.

- [ ] **Step 1: Write the failing test**

```python
# append to app/tests/test_memo_api.py

def test_advance_list_route_returns_ok(client):
    token = _login(client)
    with client.session_transaction() as sess:
        sess["company_id"] = 2
    rv = client.get("/payment-memo/advance/list",
                    headers={"Authorization": f"Bearer {token}"})
    assert rv.status_code == 200
    assert rv.get_json()["ok"] is True
    assert rv.get_json()["rows"] == []


def test_advance_realize_route_rejects_missing_body(client):
    token = _login(client)
    with client.session_transaction() as sess:
        sess["company_id"] = 2
    rv = client.post("/payment-memo/advance/999999/realize", json={},
                     headers={"Authorization": f"Bearer {token}"})
    assert rv.status_code == 200
    assert rv.get_json()["ok"] is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd app && python -m pytest tests/test_memo_api.py -k advance -v`
Expected: FAIL — 404 Not Found (routes don't exist yet).

- [ ] **Step 3: Implement**

Add to `app/modules/payment_memo/routes.py`, near `ipay_save_pa` (line 646), and add the two new
functions to the import line at the top of the file (`from .service import ..., get_advance_payments, realize_advance_payment`):

```python
@bp.route("/advance/list")
@jwt_html_required
def advance_list():
    company_id = session.get("company_id")
    if not company_id:
        return jsonify({"ok": False, "pesan": "Company belum dipilih."}), 400
    status = request.args.get("status", "").strip()
    search = request.args.get("search", "").strip()
    bulan  = request.args.get("bulan", "").strip()
    tahun  = request.args.get("tahun", "").strip()
    rows   = get_advance_payments(company_id, status, search, bulan, tahun)
    return jsonify({"ok": True, "rows": rows})


@bp.route("/advance/<int:payment_id>/realize", methods=["POST"])
@jwt_html_required
def advance_realize(payment_id):
    company_id      = session.get("company_id", 0)
    data            = request.get_json(force=True) or {}
    realized_amount = data.get("realized_amount")
    tgl_realisasi   = data.get("tgl_realisasi", "")
    result = realize_advance_payment(payment_id, realized_amount, tgl_realisasi, company_id)
    return jsonify(result)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd app && python -m pytest tests/test_memo_api.py -v`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
cd /c/Financehub
git add app/modules/payment_memo/routes.py app/tests/test_memo_api.py
git commit -m "feat: add /advance/list and /advance/<id>/realize routes"
```

---

### Task 8: Frontend — Open PA route column, Input route selector, Advance tab

**Files:**
- Modify: `app/templates/etf_payment_application/index.html` (Open PA table — add Route column)
- Modify: `app/templates/payment_memo/index.html` (Input panel — add Route selector; new Advance
  tab mirroring the SETF tab)

**Interfaces:**
- Consumes: `/payment-memo/advance/list` and `/payment-memo/advance/<id>/realize` (Task 7).
- Produces: no new backend interfaces — this is the last task in the plan.

This task is UI-only glue over the endpoints built in Tasks 1-7; there is no new business logic to
unit-test here (verify manually per the steps below, per this repo's convention of not writing
Selenium/Playwright tests for template-rendered admin UI).

- [ ] **Step 1: Add Route column to Open PA table**

In `app/templates/etf_payment_application/index.html`, find the table header row for the Open PA
list (search for the `<thead>` in the Open PA tab section) and add one `<th>Route</th>` column.
In the row-rendering JS for that table, add a `<td>${esc(r.route || '-')}</td>` cell reading the
`route` field that now comes back from the PA-lines rows (already exposed via the existing
`etf_pa`/`app_pa`/`sml_pa`/`setf_pa` list endpoints, since `SELECT *` on the joined lines table
picks up the new column automatically — no backend change needed for this column to appear).

- [ ] **Step 2: Add Route selector to the Input panel**

In `app/templates/payment_memo/index.html`, find the Input panel's header fields (near the
existing "Pillar" readonly box, search for `id="ipay-pillar"`). Add a new select:

```html
<div>
  <label style="font-size:11px;color:var(--text-muted);display:block;margin-bottom:2px;">Route</label>
  <select id="ipay-route" style="width:100%;padding:6px 8px;border:1px solid var(--border);border-radius:6px;">
    <option value="gl" selected>GL</option>
    <option value="advance">Advance</option>
  </select>
</div>
```

In the JS function that builds the save payload for `save_pa_payment` (search for the fetch call to
`/payment-memo/ipay/save-pa`), add `route: document.getElementById('ipay-route')?.value || 'gl'` to
the JSON body being sent.

- [ ] **Step 3: Add the Advance tab (mirror the SETF tab)**

In `app/templates/payment_memo/index.html`:
1. Add a tab button next to the existing SETF button (near line 99):
   `<button class="tab-btn" data-tab="tab-advance" onclick="loadAdvance()">Advance</button>`
2. Copy the `<!-- SETF Tab -->` panel block (search for that comment, around line 624) into a new
   `<!-- Advance Tab -->` panel with `id="tab-advance"`, renaming element ids from `setf-*` to
   `advance-*` (search bar, bulan/tahun/status filters, tbody id `advance-tbody`, count id
   `advance-count`). Keep the same columns as SETF (PAM No, Date, GL, CC, PT, Requestor,
   Keterangan, Mata Uang, DPP, PPN, Total, Due Date, Status, Tanggal Bayar) plus 2 new columns:
   **Advance Amount**, **Realized Amount**, and a **Realisasi** action column with a button shown
   only when `r.status === 'paid'`.
3. Add the JS functions (near `loadSETF`, line 1805):

```javascript
let _advanceDebounce;
function loadAdvanceDebounced() { clearTimeout(_advanceDebounce); _advanceDebounce = setTimeout(loadAdvance, 300); }
async function loadAdvance() {
  const status = (document.getElementById('advance-filter-status')?.value || '');
  const search = (document.getElementById('advance-search')?.value || '').trim();
  const bulan  = (document.getElementById('advance-filter-bulan')?.value || '');
  const tahun  = (document.getElementById('advance-filter-tahun')?.value || '');
  const params = new URLSearchParams({ status, search, bulan, tahun });
  const tbody  = document.getElementById('advance-tbody');
  tbody.innerHTML = skeletonRows(15);
  const res  = await apiFetch('/payment-memo/advance/list?' + params);
  if (!res) return;
  const data = await res.json();
  if (!data.ok || !data.rows.length) {
    tbody.innerHTML = '<tr><td colspan="10" style="text-align:center;padding:20px;color:var(--text-muted);">Belum ada data Advance.</td></tr>';
    return;
  }
  tbody.innerHTML = data.rows.map(r => `
    <tr>
      <td style="padding:6px 8px;font-family:monospace;font-size:11px">${esc(r.pam)}</td>
      <td style="padding:6px 8px">${esc(r.nama || '-')}</td>
      <td style="padding:6px 8px;text-align:right">${fmtRupiah(r.advance_amount)}</td>
      <td style="padding:6px 8px;text-align:right">${fmtRupiah(r.realized_amount)}</td>
      <td style="padding:6px 8px">${esc(r.status)}</td>
      <td style="padding:6px 8px">${r.status === 'paid'
        ? `<button class="btn btn-sm btn-primary" onclick="openRealizeModal(${r.id}, ${r.advance_amount})">Realisasi</button>`
        : '-'}</td>
    </tr>`).join('');
}

async function submitRealize(paymentId, realizedAmount, tglRealisasi) {
  const res = await apiFetch(`/payment-memo/advance/${paymentId}/realize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ realized_amount: realizedAmount, tgl_realisasi: tglRealisasi }),
  });
  if (!res) return;
  const data = await res.json();
  if (!data.ok) { alert(data.pesan); return; }
  alert(`Realisasi tersimpan. Selisih: ${fmtRupiah(data.selisih)}`);
  loadAdvance();
}
```

Add `openRealizeModal` next to `submitRealize` — a `prompt()`-based implementation for this first
pass (a full modal dialog matching the rest of the app's styling is a follow-up polish item, not
required for the feature to function):

```javascript
function openRealizeModal(paymentId, advanceAmount) {
  const realizedStr = prompt(`Advance amount: ${fmtRupiah(advanceAmount)}\nMasukkan realized amount:`);
  if (realizedStr === null) return;
  const realizedAmount = parseFloat(realizedStr.replace(/[^0-9.]/g, ''));
  if (!realizedAmount || realizedAmount <= 0) { alert('Realized amount tidak valid.'); return; }
  const tglRealisasi = prompt('Tanggal realisasi (YYYY-MM-DD):', new Date().toISOString().slice(0, 10));
  if (!tglRealisasi) return;
  submitRealize(paymentId, realizedAmount, tglRealisasi);
}
```

- [ ] **Step 4: Manual verification**

Start the dev server (`preview_start` or `python run_production.py`), log in as ETF, and walk the
full lifecycle by hand:
1. Open PA → confirm the new Route column renders (shows `-` for existing rows).
2. Input → select Route=Advance, pick a PA line, save → confirm PAM appears with pillar `ADVANCE`
   (check via `/payment-memo/by-pillar/ADVANCE`) and NOT in its original pillar tab.
3. Open the Advance tab → confirm the line shows with status `open`, no Realisasi button.
4. Set `tanggal_bayar` on that PAM (existing "set paid" UI) → reload Advance tab → status should
   now be `paid` with a Realisasi button visible.
5. Click Realisasi, enter a different amount → confirm selisih is shown, and the line disappears
   from the Advance tab.
6. Open the original pillar's tab (e.g. AGRI) → confirm the PAM now appears there with the realized
   amount.

- [ ] **Step 5: Commit**

```bash
cd /c/Financehub
git add app/templates/etf_payment_application/index.html app/templates/payment_memo/index.html
git commit -m "feat: Route selector, Advance tab, and realization UI for ETF PA"
```
