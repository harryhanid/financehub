# Beasiswa Dashboard Status Filter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a multi-select "Status" filter (Open / Complete) to the Beasiswa dashboard, wired through all 6 dashboard API endpoints and every chart/table they feed.

**Architecture:** A new `_status_filter_sql()` SQL-fragment helper (identical shape to the existing `_pillar_filter_sql`/`_program_filter_sql`/`_jenjang_filter_sql`) threads a `statuses: list` param through the 3 functions that filter `payment_beasiswa` via a WHERE clause, and a sibling `_status_case_sql()` threads it through the 2 functions that compute realisasi via `SUM(CASE WHEN status = 'complete' THEN amount ELSE 0 END)` (they need realisasi gated by status while an unconditional total stays ungated, in the same query). Routes parse a new `statuses` query param, defaulting to `['complete']` only when the param key is entirely absent (preserving today's behavior for any caller not yet passing it) — every other case (explicit empty, one value, both values) passes through untouched. The frontend gains one more filter chip, wired exactly like the existing three.

**Tech Stack:** Flask, sqlite3 (raw SQL, no ORM), vanilla JS, Jinja2.

## Global Constraints

- Status options are exactly `open` and `complete` — no other values (spec: `docs/superpowers/specs/2026-08-11-beasiswa-dashboard-status-filter-design.md`).
- Default checked state in the UI: `complete` only. `open` starts unchecked.
- Service-layer functions: `statuses=None` (or `[]`) means **no restriction** (matches the existing convention for years/pillars/programs/jenjangs) — this is a Python-level default, not the UI default.
- Route-layer functions: `statuses` query param **entirely absent** → pass `['complete']` to the service function (preserves today's hardcoded behavior for direct API callers). Query param **present but empty** → pass `[]` (no restriction), same as the other filters.
- No schema/migration changes.
- `budget_beasiswa` queries are untouched — that table has no `status` column.

---

### Task 1: SQL helpers + the 3 WHERE-clause dashboard functions

**Files:**
- Modify: `app/modules/beasiswa/service.py:1140-1163` (helpers), `:1319-1379` (`get_dashboard_monthly`), `:1382-1408` (`get_dashboard_latest_payments`), `:1426-1461` (`get_dashboard_pillar_yearly`)
- Test: `app/tests/test_beasiswa_service.py`

**Interfaces:**
- Produces: `_status_filter_sql(statuses, column) -> (str, list)` — same signature shape as `_pillar_filter_sql`. Consumed by this task's 3 functions and (via Task 2's `_status_case_sql`, which is a sibling, not built on this one) unrelated to Task 2.
- Produces: `get_dashboard_monthly(company_id, years=None, pillars=None, programs=None, jenjangs=None, statuses=None)`, `get_dashboard_latest_payments(company_id, years=None, pillars=None, programs=None, jenjangs=None, statuses=None, limit=20)`, `get_dashboard_pillar_yearly(company_id, pillars=None, programs=None, jenjangs=None, statuses=None)` — the trailing `statuses` kwarg is new; existing callers that don't pass it are unaffected (defaults to `None` = no restriction, same as omitting any other filter).

- [ ] **Step 1: Write the failing tests**

Add to `app/tests/test_beasiswa_service.py`. First extend the import block at the top of the file (line 8-15) to add the 3 new functions under test (only add names not already imported — `get_dashboard_monthly` and `get_dashboard_latest_payments` are already imported; add `get_dashboard_pillar_yearly`):

```python
from modules.beasiswa.service import (
    generate_kode_siswa, get_siswa_list, add_siswa, update_siswa,
    add_budget_batch, add_payment_batch, get_rekap, get_sisa_budget,
    add_klaim_multi, get_klaim_list, delete_klaim_row,
    add_payment_multi, get_budget_list, get_payment_list,
    delete_payment_beasiswa, delete_payment_row, update_payment_row,
    get_dashboard_monthly, get_dashboard_latest_payments,
    get_dashboard_pillar_yearly,
)
```

Then append these tests at the end of the file:

```python
def test_get_dashboard_monthly_statuses_none_includes_all_statuses():
    """Python-level default: statuses=None means no restriction, same as
    every other dashboard filter dimension when omitted."""
    _add_siswa_a()
    conn = get_conn()
    conn.execute(
        "INSERT INTO payment_beasiswa (company_id, siswa_code, cat1, cat2, tanggal, amount, pillar, status) "
        "VALUES (?,?,?,?,?,?,?,'open')",
        (COMPANY_ID, "1250001", "By Pendidikan", "Semester 1", "2026-03-15", 1_500_000, "AGRI")
    )
    conn.execute(
        "INSERT INTO payment_beasiswa (company_id, siswa_code, cat1, cat2, tanggal, amount, pillar, status) "
        "VALUES (?,?,?,?,?,?,?,'complete')",
        (COMPANY_ID, "1250001", "By Pendidikan", "Semester 1", "2026-03-16", 2_000_000, "AGRI")
    )
    conn.commit()
    conn.close()

    result = get_dashboard_monthly(COMPANY_ID, years=[2026])
    march = next(m for m in result["months"] if m["bulan"] == 3)
    assert march["realisasi"] == 3_500_000, "no statuses filter given -> both open and complete count"


def test_get_dashboard_monthly_statuses_complete_only_excludes_open():
    _add_siswa_a()
    conn = get_conn()
    conn.execute(
        "INSERT INTO payment_beasiswa (company_id, siswa_code, cat1, cat2, tanggal, amount, pillar, status) "
        "VALUES (?,?,?,?,?,?,?,'open')",
        (COMPANY_ID, "1250001", "By Pendidikan", "Semester 1", "2026-03-15", 1_500_000, "AGRI")
    )
    conn.execute(
        "INSERT INTO payment_beasiswa (company_id, siswa_code, cat1, cat2, tanggal, amount, pillar, status) "
        "VALUES (?,?,?,?,?,?,?,'complete')",
        (COMPANY_ID, "1250001", "By Pendidikan", "Semester 1", "2026-03-16", 2_000_000, "AGRI")
    )
    conn.commit()
    conn.close()

    result = get_dashboard_monthly(COMPANY_ID, years=[2026], statuses=["complete"])
    march = next(m for m in result["months"] if m["bulan"] == 3)
    assert march["realisasi"] == 2_000_000


def test_get_dashboard_latest_payments_statuses_filters_to_selection():
    _add_siswa_a()
    add_payment_batch(COMPANY_ID, "1250001", "2026-01-15", "AGRI", "PT. SMART Tbk", [
        {"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 1000000},
    ])
    add_payment_batch(COMPANY_ID, "1250001", "2026-01-16", "AGRI", "PT. SMART Tbk", [
        {"cat1": "By Pendidikan", "cat2": "Semester 2", "amount": 3000000},
    ])
    conn = get_conn()
    conn.execute("UPDATE payment_beasiswa SET status='complete' WHERE company_id=? AND amount=?",
                 (COMPANY_ID, 3000000))
    conn.commit()
    conn.close()

    rows = get_dashboard_latest_payments(COMPANY_ID, statuses=["complete"])
    assert len(rows) == 1
    assert rows[0]["status"] == "complete"
    assert rows[0]["amount"] == 3000000


def test_get_dashboard_pillar_yearly_statuses_complete_only_excludes_open():
    _add_siswa_a()
    conn = get_conn()
    conn.execute(
        "INSERT INTO payment_beasiswa (company_id, siswa_code, cat1, cat2, tanggal, amount, pillar, status) "
        "VALUES (?,?,?,?,?,?,?,'open')",
        (COMPANY_ID, "1250001", "By Pendidikan", "Semester 1", "2026-03-15", 5_000_000, "AGRI")
    )
    conn.execute(
        "INSERT INTO payment_beasiswa (company_id, siswa_code, cat1, cat2, tanggal, amount, pillar, status) "
        "VALUES (?,?,?,?,?,?,?,'complete')",
        (COMPANY_ID, "1250001", "By Pendidikan", "Semester 1", "2026-03-16", 2_000_000, "AGRI")
    )
    conn.commit()
    conn.close()

    result = get_dashboard_pillar_yearly(COMPANY_ID, statuses=["complete"])
    row_2026 = next(r for r in result if r["tahun"] == 2026)
    assert row_2026["pillars"]["AGRI"] == 2_000_000
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd app && python -m pytest tests/test_beasiswa_service.py -k "statuses" -v`
Expected: FAIL — `TypeError: get_dashboard_monthly() got an unexpected keyword argument 'statuses'` (and similarly for the other two functions).

- [ ] **Step 3: Add the `_status_filter_sql` helper**

In `app/modules/beasiswa/service.py`, right after `_jenjang_filter_sql` (ends at line 1163, blank line at 1163), add:

```python
def _status_filter_sql(statuses, column):
    if not statuses:
        return "", []
    placeholders = ",".join("?" for _ in statuses)
    return f" AND {column} IN ({placeholders})", list(statuses)
```

- [ ] **Step 4: Thread `statuses` through `get_dashboard_monthly`**

Current (`app/modules/beasiswa/service.py:1319-1355`):

```python
def get_dashboard_monthly(company_id: int, years: list = None, pillars: list = None, programs: list = None, jenjangs: list = None) -> dict:
    if not years:
        return {"chart_year": None, "months": [], "comparison": []}

    chart_year = max(years)
    years_to_fetch = set(years)
    years_to_fetch.add(chart_year - 1)
    conn = get_conn()

    pillar_sql, pillar_params = _pillar_filter_sql(pillars, "p.pillar")
    program_sql, program_params = _program_filter_sql(programs, "s.program")
    jenjang_sql, jenjang_params = _jenjang_filter_sql(jenjangs, "s.jenjang")

    budget_rows = conn.execute(
        f"""
        SELECT CAST(strftime('%m', b.tanggal) AS INTEGER) AS bulan, SUM(b.amount) AS total
        FROM budget_beasiswa b
        JOIN siswa s ON s.code = b.siswa_code AND s.company_id = b.company_id
        WHERE b.company_id = ? AND strftime('%Y', b.tanggal) = ?{program_sql}{jenjang_sql}
        GROUP BY bulan
        """,
        [company_id, str(chart_year), *program_params, *jenjang_params],
    ).fetchall()

    year_placeholders = ",".join("?" for _ in years_to_fetch)
    realisasi_rows = conn.execute(
        f"""
        SELECT strftime('%Y', p.tanggal) AS tahun, CAST(strftime('%m', p.tanggal) AS INTEGER) AS bulan,
               SUM(p.amount) AS total
        FROM payment_beasiswa p
        JOIN siswa s ON s.code = p.siswa_code AND s.company_id = p.company_id
        WHERE p.company_id = ? AND p.status = 'complete'
              AND strftime('%Y', p.tanggal) IN ({year_placeholders}){pillar_sql}{program_sql}{jenjang_sql}
        GROUP BY tahun, bulan
        """,
        [company_id, *[str(y) for y in years_to_fetch], *pillar_params, *program_params, *jenjang_params],
    ).fetchall()
    conn.close()
```

Change to (only the signature, the `status_sql`/`status_params` line, and the realisasi query's WHERE clause + params change — everything else is identical):

```python
def get_dashboard_monthly(company_id: int, years: list = None, pillars: list = None, programs: list = None, jenjangs: list = None, statuses: list = None) -> dict:
    if not years:
        return {"chart_year": None, "months": [], "comparison": []}

    chart_year = max(years)
    years_to_fetch = set(years)
    years_to_fetch.add(chart_year - 1)
    conn = get_conn()

    pillar_sql, pillar_params = _pillar_filter_sql(pillars, "p.pillar")
    program_sql, program_params = _program_filter_sql(programs, "s.program")
    jenjang_sql, jenjang_params = _jenjang_filter_sql(jenjangs, "s.jenjang")
    status_sql, status_params = _status_filter_sql(statuses, "p.status")

    budget_rows = conn.execute(
        f"""
        SELECT CAST(strftime('%m', b.tanggal) AS INTEGER) AS bulan, SUM(b.amount) AS total
        FROM budget_beasiswa b
        JOIN siswa s ON s.code = b.siswa_code AND s.company_id = b.company_id
        WHERE b.company_id = ? AND strftime('%Y', b.tanggal) = ?{program_sql}{jenjang_sql}
        GROUP BY bulan
        """,
        [company_id, str(chart_year), *program_params, *jenjang_params],
    ).fetchall()

    year_placeholders = ",".join("?" for _ in years_to_fetch)
    realisasi_rows = conn.execute(
        f"""
        SELECT strftime('%Y', p.tanggal) AS tahun, CAST(strftime('%m', p.tanggal) AS INTEGER) AS bulan,
               SUM(p.amount) AS total
        FROM payment_beasiswa p
        JOIN siswa s ON s.code = p.siswa_code AND s.company_id = p.company_id
        WHERE p.company_id = ?
              AND strftime('%Y', p.tanggal) IN ({year_placeholders}){pillar_sql}{program_sql}{jenjang_sql}{status_sql}
        GROUP BY tahun, bulan
        """,
        [company_id, *[str(y) for y in years_to_fetch], *pillar_params, *program_params, *jenjang_params, *status_params],
    ).fetchall()
    conn.close()
```

Note the hardcoded `AND p.status = 'complete'` is removed from the WHERE clause entirely — it's replaced by `{status_sql}`, which itself returns `""` (no restriction) when `statuses` is `None`/falsy. This is the one place in this function where behavior changes when called with no `statuses` arg: today it always implicitly restricts to `complete`; after this change it does not, matching every other filter dimension's "omitted = no restriction" convention. (The route layer, in Task 3, is what preserves the current UI-visible default.)

- [ ] **Step 5: Thread `statuses` through `get_dashboard_latest_payments`**

Current (`app/modules/beasiswa/service.py:1382-1408`):

```python
def get_dashboard_latest_payments(company_id: int, years: list = None, pillars: list = None, programs: list = None, jenjangs: list = None, limit: int = 20) -> list:
    conn = get_conn()
    payment_year_sql, payment_year_params = _year_filter_sql(years, "p.tanggal")
    pillar_sql, pillar_params = _pillar_filter_sql(pillars, "p.pillar")
    program_sql, program_params = _program_filter_sql(programs, "s.program")
    jenjang_sql, jenjang_params = _jenjang_filter_sql(jenjangs, "s.jenjang")
    program_sql, program_params = _program_filter_sql(programs, "s.program")
    jenjang_sql, jenjang_params = _jenjang_filter_sql(jenjangs, "s.jenjang")
    program_sql, program_params = _program_filter_sql(programs, "s.program")
    jenjang_sql, jenjang_params = _jenjang_filter_sql(jenjangs, "s.jenjang")
    program_sql, program_params = _program_filter_sql(programs, "s.program")
    jenjang_sql, jenjang_params = _jenjang_filter_sql(jenjangs, "s.jenjang")

    rows = conn.execute(
        f"""
        SELECT p.tanggal, s.nama, p.cat1, p.cat2, p.amount, p.status
        FROM payment_beasiswa p
        JOIN siswa s ON s.code = p.siswa_code AND s.company_id = p.company_id
        WHERE p.company_id = ?{payment_year_sql}{pillar_sql}{program_sql}{jenjang_sql}
        ORDER BY p.tanggal DESC, p.id DESC
        LIMIT ?
        """,
        [company_id, *payment_year_params, *pillar_params, *program_params, *jenjang_params, limit],
    ).fetchall()
    conn.close()

    return [dict(r) for r in rows]
```

The repeated `program_sql`/`jenjang_sql` reassignments above are pre-existing dead code (each line just overwrites the previous with an identical value) — leave them as-is, not in scope for this change. Add the `statuses` param and one new helper call, and splice `{status_sql}` into the WHERE clause and `*status_params` into the params list:

```python
def get_dashboard_latest_payments(company_id: int, years: list = None, pillars: list = None, programs: list = None, jenjangs: list = None, statuses: list = None, limit: int = 20) -> list:
    conn = get_conn()
    payment_year_sql, payment_year_params = _year_filter_sql(years, "p.tanggal")
    pillar_sql, pillar_params = _pillar_filter_sql(pillars, "p.pillar")
    program_sql, program_params = _program_filter_sql(programs, "s.program")
    jenjang_sql, jenjang_params = _jenjang_filter_sql(jenjangs, "s.jenjang")
    program_sql, program_params = _program_filter_sql(programs, "s.program")
    jenjang_sql, jenjang_params = _jenjang_filter_sql(jenjangs, "s.jenjang")
    program_sql, program_params = _program_filter_sql(programs, "s.program")
    jenjang_sql, jenjang_params = _jenjang_filter_sql(jenjangs, "s.jenjang")
    program_sql, program_params = _program_filter_sql(programs, "s.program")
    jenjang_sql, jenjang_params = _jenjang_filter_sql(jenjangs, "s.jenjang")
    status_sql, status_params = _status_filter_sql(statuses, "p.status")

    rows = conn.execute(
        f"""
        SELECT p.tanggal, s.nama, p.cat1, p.cat2, p.amount, p.status
        FROM payment_beasiswa p
        JOIN siswa s ON s.code = p.siswa_code AND s.company_id = p.company_id
        WHERE p.company_id = ?{payment_year_sql}{pillar_sql}{program_sql}{jenjang_sql}{status_sql}
        ORDER BY p.tanggal DESC, p.id DESC
        LIMIT ?
        """,
        [company_id, *payment_year_params, *pillar_params, *program_params, *jenjang_params, *status_params, limit],
    ).fetchall()
    conn.close()

    return [dict(r) for r in rows]
```

- [ ] **Step 6: Thread `statuses` through `get_dashboard_pillar_yearly`**

Current (`app/modules/beasiswa/service.py:1426-1461`):

```python
def get_dashboard_pillar_yearly(company_id: int, pillars: list = None, programs: list = None, jenjangs: list = None) -> list:
    conn = get_conn()
    pillar_sql, pillar_params = _pillar_filter_sql(pillars, "p.pillar")
    program_sql, program_params = _program_filter_sql(programs, "s.program")
    jenjang_sql, jenjang_params = _jenjang_filter_sql(jenjangs, "s.jenjang")
    program_sql, program_params = _program_filter_sql(programs, "s.program")
    jenjang_sql, jenjang_params = _jenjang_filter_sql(jenjangs, "s.jenjang")
    program_sql, program_params = _program_filter_sql(programs, "s.program")
    jenjang_sql, jenjang_params = _jenjang_filter_sql(jenjangs, "s.jenjang")
    program_sql, program_params = _program_filter_sql(programs, "s.program")
    jenjang_sql, jenjang_params = _jenjang_filter_sql(jenjangs, "s.jenjang")
    rows = conn.execute(
        f"""
        SELECT strftime('%Y', p.tanggal) AS tahun, p.pillar, SUM(p.amount) AS realisasi
        FROM payment_beasiswa p
        JOIN siswa s ON s.code = p.siswa_code AND s.company_id = p.company_id
        WHERE p.company_id = ? AND p.status = 'complete'
              AND p.tanggal IS NOT NULL AND p.tanggal != ''{pillar_sql}{program_sql}{jenjang_sql}
        GROUP BY tahun, p.pillar
        ORDER BY tahun DESC, p.pillar ASC
        """,
        [company_id, *pillar_params, *program_params, *jenjang_params],
    ).fetchall()
    conn.close()
```

Same treatment — remove the hardcoded `AND p.status = 'complete'`, add `_status_filter_sql`, splice in:

```python
def get_dashboard_pillar_yearly(company_id: int, pillars: list = None, programs: list = None, jenjangs: list = None, statuses: list = None) -> list:
    conn = get_conn()
    pillar_sql, pillar_params = _pillar_filter_sql(pillars, "p.pillar")
    program_sql, program_params = _program_filter_sql(programs, "s.program")
    jenjang_sql, jenjang_params = _jenjang_filter_sql(jenjangs, "s.jenjang")
    program_sql, program_params = _program_filter_sql(programs, "s.program")
    jenjang_sql, jenjang_params = _jenjang_filter_sql(jenjangs, "s.jenjang")
    program_sql, program_params = _program_filter_sql(programs, "s.program")
    jenjang_sql, jenjang_params = _jenjang_filter_sql(jenjangs, "s.jenjang")
    program_sql, program_params = _program_filter_sql(programs, "s.program")
    jenjang_sql, jenjang_params = _jenjang_filter_sql(jenjangs, "s.jenjang")
    status_sql, status_params = _status_filter_sql(statuses, "p.status")
    rows = conn.execute(
        f"""
        SELECT strftime('%Y', p.tanggal) AS tahun, p.pillar, SUM(p.amount) AS realisasi
        FROM payment_beasiswa p
        JOIN siswa s ON s.code = p.siswa_code AND s.company_id = p.company_id
        WHERE p.company_id = ?
              AND p.tanggal IS NOT NULL AND p.tanggal != ''{pillar_sql}{program_sql}{jenjang_sql}{status_sql}
        GROUP BY tahun, p.pillar
        ORDER BY tahun DESC, p.pillar ASC
        """,
        [company_id, *pillar_params, *program_params, *jenjang_params, *status_params],
    ).fetchall()
    conn.close()
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `cd app && python -m pytest tests/test_beasiswa_service.py -k "statuses or dashboard_monthly or dashboard_latest_payments" -v`
Expected: PASS — all new tests, and `test_get_dashboard_monthly_does_not_crash_and_applies_program_filter`, `test_get_dashboard_latest_payments_includes_open_status`, `test_get_dashboard_latest_payments_includes_both_open_and_complete` (unmodified — they call with no `statuses` arg, which now means "no restriction", the same result they already asserted).

- [ ] **Step 8: Commit**

```bash
git add app/modules/beasiswa/service.py app/tests/test_beasiswa_service.py
git commit -m "feat: add statuses filter to monthly/latest_payments/pillar_yearly dashboard queries"
```

---

### Task 2: the 2 CASE-clause dashboard functions + program_summary cascade

**Files:**
- Modify: `app/modules/beasiswa/service.py:1165-1217` (`get_dashboard_summary`), `:1220-1316` (`get_dashboard_breakdown`), `:1411-1423` (`get_dashboard_program_summary`)
- Test: `app/tests/test_beasiswa_service.py`

**Interfaces:**
- Consumes: none from Task 1 (this task's helper, `_status_case_sql`, is independent of Task 1's `_status_filter_sql` — different SQL shape, same input contract).
- Produces: `_status_case_sql(statuses, column) -> (str, list)` — returns a boolean SQL fragment (`"{column} IN (?,?)"` or `"1=1"` when `statuses` is empty) plus its params, meant to be spliced into `CASE WHEN {frag} THEN amount ELSE 0 END`. Produces `get_dashboard_summary(..., statuses=None)`, `get_dashboard_breakdown(..., statuses=None)`, `get_dashboard_program_summary(..., statuses=None)` — same "None = no restriction" convention as Task 1.

- [ ] **Step 1: Write the failing tests**

Add to `app/tests/test_beasiswa_service.py`, and add `get_dashboard_summary, get_dashboard_breakdown, get_dashboard_program_summary` to the import block (same block edited in Task 1 Step 1 — if Task 1 already ran, just extend the existing import tuple further):

```python
def test_get_dashboard_summary_statuses_complete_only_excludes_open_from_realisasi():
    _add_siswa_a()
    conn = get_conn()
    conn.execute(
        "INSERT INTO payment_beasiswa (company_id, siswa_code, cat1, cat2, tanggal, amount, pillar, status) "
        "VALUES (?,?,?,?,?,?,?,'open')",
        (COMPANY_ID, "1250001", "By Pendidikan", "Semester 1", "2026-03-15", 1_000_000, "AGRI")
    )
    conn.execute(
        "INSERT INTO payment_beasiswa (company_id, siswa_code, cat1, cat2, tanggal, amount, pillar, status) "
        "VALUES (?,?,?,?,?,?,?,'complete')",
        (COMPANY_ID, "1250001", "By Pendidikan", "Semester 1", "2026-03-16", 4_000_000, "AGRI")
    )
    conn.commit()
    conn.close()

    result = get_dashboard_summary(COMPANY_ID, statuses=["complete"])
    row = next(r for r in result if r["siswa_code"] == "1250001")
    assert row["realisasi_total"] == 4_000_000
    assert row["payment_total"] == 5_000_000, "payment_total stays unconditional (all statuses), only realisasi is gated"


def test_get_dashboard_summary_statuses_none_includes_all_in_realisasi():
    _add_siswa_a()
    conn = get_conn()
    conn.execute(
        "INSERT INTO payment_beasiswa (company_id, siswa_code, cat1, cat2, tanggal, amount, pillar, status) "
        "VALUES (?,?,?,?,?,?,?,'open')",
        (COMPANY_ID, "1250001", "By Pendidikan", "Semester 1", "2026-03-15", 1_000_000, "AGRI")
    )
    conn.commit()
    conn.close()

    result = get_dashboard_summary(COMPANY_ID)
    row = next(r for r in result if r["siswa_code"] == "1250001")
    assert row["realisasi_total"] == 1_000_000, "no statuses filter given -> open counts toward realisasi too"


def test_get_dashboard_breakdown_statuses_complete_only_excludes_open():
    _add_siswa_a()
    conn = get_conn()
    conn.execute(
        "INSERT INTO payment_beasiswa (company_id, siswa_code, cat1, cat2, tanggal, amount, pillar, status) "
        "VALUES (?,?,?,?,?,?,?,'open')",
        (COMPANY_ID, "1250001", "By Pendidikan", "Semester 1", "2026-03-15", 1_000_000, "AGRI")
    )
    conn.execute(
        "INSERT INTO payment_beasiswa (company_id, siswa_code, cat1, cat2, tanggal, amount, pillar, status) "
        "VALUES (?,?,?,?,?,?,?,'complete')",
        (COMPANY_ID, "1250001", "By Pendidikan", "Semester 1", "2026-03-16", 4_000_000, "AGRI")
    )
    conn.commit()
    conn.close()

    result = get_dashboard_breakdown(COMPANY_ID, statuses=["complete"])
    row = next(k for k in result["kategori"] if k["cat1"] == "By Pendidikan")
    assert row["realisasi"] == 4_000_000
    assert row["payment"] == 5_000_000


def test_get_dashboard_program_summary_statuses_pass_through():
    _add_siswa_a()  # program="SMART"
    conn = get_conn()
    conn.execute(
        "INSERT INTO payment_beasiswa (company_id, siswa_code, cat1, cat2, tanggal, amount, pillar, status) "
        "VALUES (?,?,?,?,?,?,?,'open')",
        (COMPANY_ID, "1250001", "By Pendidikan", "Semester 1", "2026-03-15", 1_000_000, "AGRI")
    )
    conn.commit()
    conn.close()

    result = get_dashboard_program_summary(COMPANY_ID, statuses=["complete"])
    row = next(p for p in result if p["program"] == "SMART")
    assert row["realisasi"] == 0.0, "open row must not count when statuses=['complete']"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd app && python -m pytest tests/test_beasiswa_service.py -k "dashboard_summary_statuses or dashboard_breakdown_statuses or dashboard_program_summary_statuses" -v`
Expected: FAIL — `TypeError: get_dashboard_summary() got an unexpected keyword argument 'statuses'` (and similarly for the other two).

- [ ] **Step 3: Add the `_status_case_sql` helper**

Directly below `_status_filter_sql` (added in Task 1 Step 3 — if Task 1 hasn't run yet in this session, add both helpers together right after `_jenjang_filter_sql`):

```python
def _status_case_sql(statuses, column):
    if not statuses:
        return "1=1", []
    placeholders = ",".join("?" for _ in statuses)
    return f"{column} IN ({placeholders})", list(statuses)
```

- [ ] **Step 4: Thread `statuses` through `get_dashboard_summary`**

Current (`app/modules/beasiswa/service.py:1165-1198`):

```python
def get_dashboard_summary(company_id: int, years: list = None, pillars: list = None, programs: list = None, jenjangs: list = None) -> list:
    conn = get_conn()
    budget_year_sql, budget_year_params = _year_filter_sql(years, "tanggal")
    payment_year_sql, payment_year_params = _year_filter_sql(years, "tanggal")
    pillar_sql, pillar_params = _pillar_filter_sql(pillars, "pillar")
    program_sql, program_params = _program_filter_sql(programs, "s.program")
    jenjang_sql, jenjang_params = _jenjang_filter_sql(jenjangs, "s.jenjang")

    rows = conn.execute(
        f"""
        SELECT s.code, s.nama, s.jenjang, s.angkatan, s.program, s.status,
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
        WHERE s.company_id = ?{program_sql}{jenjang_sql}
        ORDER BY s.nama
        """,
        [company_id, *budget_year_params, company_id, *payment_year_params, *pillar_params, company_id, *program_params, *jenjang_params],
    ).fetchall()
    conn.close()
```

Change to (signature, one new helper call, the `CASE WHEN` fragment, and the params list — note the params for the `CASE WHEN`'s own placeholders must be inserted at the point in the flat params list matching where `status_case_frag`'s `?`s appear in the query, i.e. right after `payment_year_params`/`pillar_params` inside that same subquery, before the outer `company_id`/`program_params`/`jenjang_params`):

```python
def get_dashboard_summary(company_id: int, years: list = None, pillars: list = None, programs: list = None, jenjangs: list = None, statuses: list = None) -> list:
    conn = get_conn()
    budget_year_sql, budget_year_params = _year_filter_sql(years, "tanggal")
    payment_year_sql, payment_year_params = _year_filter_sql(years, "tanggal")
    pillar_sql, pillar_params = _pillar_filter_sql(pillars, "pillar")
    program_sql, program_params = _program_filter_sql(programs, "s.program")
    jenjang_sql, jenjang_params = _jenjang_filter_sql(jenjangs, "s.jenjang")
    status_case_frag, status_case_params = _status_case_sql(statuses, "status")

    rows = conn.execute(
        f"""
        SELECT s.code, s.nama, s.jenjang, s.angkatan, s.program, s.status,
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
                   SUM(CASE WHEN {status_case_frag} THEN amount ELSE 0 END) AS realisasi_total
            FROM payment_beasiswa
            WHERE company_id = ?{payment_year_sql}{pillar_sql}
            GROUP BY siswa_code
        ) p ON p.siswa_code = s.code
        WHERE s.company_id = ?{program_sql}{jenjang_sql}
        ORDER BY s.nama
        """,
        [company_id, *budget_year_params, *status_case_params, company_id, *payment_year_params, *pillar_params, company_id, *program_params, *jenjang_params],
    ).fetchall()
    conn.close()
```

Note `status_case_params` is inserted right after `budget_year_params` in the flat list — SQLite substitutes `?` placeholders strictly in the order they appear in the *rendered* SQL text, and `{status_case_frag}` (inside the `CASE WHEN`) textually appears before the second `company_id`'s `?` in the `payment_beasiswa` subquery, but *after* the whole `budget_beasiswa` subquery (which has its own single `?` + `budget_year_params`). Placeholder order in the query, left to right: `budget_beasiswa`'s `company_id` (1) → `budget_year_sql`'s `?`s → `payment_beasiswa` subquery's `CASE WHEN`'s `?`s (inside `status_case_frag`) → that subquery's own `company_id` (2) → `payment_year_sql`'s `?`s → `pillar_sql`'s `?`s → outer `WHERE s.company_id = ?` (3) → `program_sql`'s `?`s → `jenjang_sql`'s `?`s. The params list above follows exactly that order.

- [ ] **Step 5: Thread `statuses` through `get_dashboard_breakdown`**

Current (`app/modules/beasiswa/service.py:1220-1280`), two `CASE WHEN p.status = 'complete'` sites (`payment_rows` query and `payment_jenjang_rows` query) plus the internal call to `get_dashboard_summary` for `over_budget`:

```python
def get_dashboard_breakdown(company_id: int, years: list = None, pillars: list = None, programs: list = None, jenjangs: list = None) -> dict:
    conn = get_conn()
    budget_year_sql, budget_year_params = _year_filter_sql(years, "b.tanggal")
    payment_year_sql, payment_year_params = _year_filter_sql(years, "p.tanggal")
    pillar_sql, pillar_params = _pillar_filter_sql(pillars, "p.pillar")
    program_sql, program_params = _program_filter_sql(programs, "s.program")
    jenjang_sql, jenjang_params = _jenjang_filter_sql(jenjangs, "s.jenjang")
    program_sql, program_params = _program_filter_sql(programs, "s.program")
    jenjang_sql, jenjang_params = _jenjang_filter_sql(jenjangs, "s.jenjang")
    program_sql, program_params = _program_filter_sql(programs, "s.program")
    jenjang_sql, jenjang_params = _jenjang_filter_sql(jenjangs, "s.jenjang")
    program_sql, program_params = _program_filter_sql(programs, "s.program")
    jenjang_sql, jenjang_params = _jenjang_filter_sql(jenjangs, "s.jenjang")

    budget_rows = conn.execute(
        f"""
        SELECT b.cat1, SUM(b.amount) AS total
        FROM budget_beasiswa b
        JOIN siswa s ON s.code = b.siswa_code AND s.company_id = b.company_id
        WHERE b.company_id = ?{budget_year_sql}{program_sql}{jenjang_sql}
        GROUP BY b.cat1
        """,
        [company_id, *budget_year_params, *program_params, *jenjang_params],
    ).fetchall()
    payment_rows = conn.execute(
        f"""
        SELECT p.cat1,
               SUM(p.amount) AS total,
               SUM(CASE WHEN p.status = 'complete' THEN p.amount ELSE 0 END) AS realisasi
        FROM payment_beasiswa p
        JOIN siswa s ON s.code = p.siswa_code AND s.company_id = p.company_id
        WHERE p.company_id = ?{payment_year_sql}{pillar_sql}{program_sql}{jenjang_sql}
        GROUP BY p.cat1
        """,
        [company_id, *payment_year_params, *pillar_params, *program_params, *jenjang_params],
    ).fetchall()

    budget_jenjang_rows = conn.execute(
        f"""
        SELECT s.jenjang, SUM(b.amount) AS total
        FROM budget_beasiswa b
        JOIN siswa s ON s.code = b.siswa_code AND s.company_id = b.company_id
        WHERE b.company_id = ?{budget_year_sql}{program_sql}{jenjang_sql}
        GROUP BY s.jenjang
        """,
        [company_id, *budget_year_params, *program_params, *jenjang_params],
    ).fetchall()

    payment_jenjang_rows = conn.execute(
        f"""
        SELECT s.jenjang,
               SUM(p.amount) AS total,
               SUM(CASE WHEN p.status = 'complete' THEN p.amount ELSE 0 END) AS realisasi
        FROM payment_beasiswa p
        JOIN siswa s ON s.code = p.siswa_code AND s.company_id = p.company_id
        WHERE p.company_id = ?{payment_year_sql}{pillar_sql}{program_sql}{jenjang_sql}
        GROUP BY s.jenjang
        """,
        [company_id, *payment_year_params, *pillar_params, *program_params, *jenjang_params],
    ).fetchall()
    conn.close()
```

Change: add `status_case_frag, status_case_params = _status_case_sql(statuses, "p.status")` once near the top (after the existing filter-helper calls), splice `{status_case_frag}` into both `CASE WHEN` sites, and prepend `*status_case_params` to both queries' params lists. SQLite binds `?` placeholders in strict left-to-right textual order, and in both queries the `CASE WHEN {status_case_frag}` sits inside the `SELECT` clause, which textually precedes the `WHERE` clause — so `status_case_params` must come *before* `company_id` and the rest of the `WHERE`-clause params, not after:

```python
def get_dashboard_breakdown(company_id: int, years: list = None, pillars: list = None, programs: list = None, jenjangs: list = None, statuses: list = None) -> dict:
    conn = get_conn()
    budget_year_sql, budget_year_params = _year_filter_sql(years, "b.tanggal")
    payment_year_sql, payment_year_params = _year_filter_sql(years, "p.tanggal")
    pillar_sql, pillar_params = _pillar_filter_sql(pillars, "p.pillar")
    program_sql, program_params = _program_filter_sql(programs, "s.program")
    jenjang_sql, jenjang_params = _jenjang_filter_sql(jenjangs, "s.jenjang")
    program_sql, program_params = _program_filter_sql(programs, "s.program")
    jenjang_sql, jenjang_params = _jenjang_filter_sql(jenjangs, "s.jenjang")
    program_sql, program_params = _program_filter_sql(programs, "s.program")
    jenjang_sql, jenjang_params = _jenjang_filter_sql(jenjangs, "s.jenjang")
    program_sql, program_params = _program_filter_sql(programs, "s.program")
    jenjang_sql, jenjang_params = _jenjang_filter_sql(jenjangs, "s.jenjang")
    status_case_frag, status_case_params = _status_case_sql(statuses, "p.status")

    budget_rows = conn.execute(
        f"""
        SELECT b.cat1, SUM(b.amount) AS total
        FROM budget_beasiswa b
        JOIN siswa s ON s.code = b.siswa_code AND s.company_id = b.company_id
        WHERE b.company_id = ?{budget_year_sql}{program_sql}{jenjang_sql}
        GROUP BY b.cat1
        """,
        [company_id, *budget_year_params, *program_params, *jenjang_params],
    ).fetchall()
    payment_rows = conn.execute(
        f"""
        SELECT p.cat1,
               SUM(p.amount) AS total,
               SUM(CASE WHEN {status_case_frag} THEN p.amount ELSE 0 END) AS realisasi
        FROM payment_beasiswa p
        JOIN siswa s ON s.code = p.siswa_code AND s.company_id = p.company_id
        WHERE p.company_id = ?{payment_year_sql}{pillar_sql}{program_sql}{jenjang_sql}
        GROUP BY p.cat1
        """,
        [*status_case_params, company_id, *payment_year_params, *pillar_params, *program_params, *jenjang_params],
    ).fetchall()

    budget_jenjang_rows = conn.execute(
        f"""
        SELECT s.jenjang, SUM(b.amount) AS total
        FROM budget_beasiswa b
        JOIN siswa s ON s.code = b.siswa_code AND s.company_id = b.company_id
        WHERE b.company_id = ?{budget_year_sql}{program_sql}{jenjang_sql}
        GROUP BY s.jenjang
        """,
        [company_id, *budget_year_params, *program_params, *jenjang_params],
    ).fetchall()

    payment_jenjang_rows = conn.execute(
        f"""
        SELECT s.jenjang,
               SUM(p.amount) AS total,
               SUM(CASE WHEN {status_case_frag} THEN p.amount ELSE 0 END) AS realisasi
        FROM payment_beasiswa p
        JOIN siswa s ON s.code = p.siswa_code AND s.company_id = p.company_id
        WHERE p.company_id = ?{payment_year_sql}{pillar_sql}{program_sql}{jenjang_sql}
        GROUP BY s.jenjang
        """,
        [*status_case_params, company_id, *payment_year_params, *pillar_params, *program_params, *jenjang_params],
    ).fetchall()
    conn.close()
```

Further down in the same function (`app/modules/beasiswa/service.py:1304-1314`), the `over_budget` comprehension calls `get_dashboard_summary`:

```python
    over_budget = [
        {
            "siswa_code":      s["siswa_code"],
            "nama":            s["nama"],
            "budget_total":    s["budget_total"],
            "realisasi_total": s["realisasi_total"],
            "selisih":         s["realisasi_total"] - s["budget_total"],
        }
        for s in get_dashboard_summary(company_id, years, pillars, programs, jenjangs)
        if s["realisasi_total"] > s["budget_total"]
    ]
```

Change the call to pass `statuses` through:

```python
        for s in get_dashboard_summary(company_id, years, pillars, programs, jenjangs, statuses)
```

- [ ] **Step 6: Thread `statuses` through `get_dashboard_program_summary`**

Current (`app/modules/beasiswa/service.py:1411-1423`):

```python
def get_dashboard_program_summary(company_id: int, years: list = None, pillars: list = None, programs: list = None, jenjangs: list = None) -> list:
    summary = get_dashboard_summary(company_id, years, pillars, programs, jenjangs)
```

Change to:

```python
def get_dashboard_program_summary(company_id: int, years: list = None, pillars: list = None, programs: list = None, jenjangs: list = None, statuses: list = None) -> list:
    summary = get_dashboard_summary(company_id, years, pillars, programs, jenjangs, statuses)
```

(The rest of the function is unchanged — it only aggregates the already-status-filtered `realisasi_total` field from `summary`.)

- [ ] **Step 7: Run tests to verify they pass**

Run: `cd app && python -m pytest tests/test_beasiswa_service.py -k "dashboard_summary or dashboard_breakdown or dashboard_program_summary" -v`
Expected: PASS — all new tests plus any pre-existing tests matching that filter.

- [ ] **Step 8: Commit**

```bash
git add app/modules/beasiswa/service.py app/tests/test_beasiswa_service.py
git commit -m "feat: add statuses filter to summary/breakdown/program_summary dashboard queries"
```

---

### Task 3: Route layer — parse `statuses` query param on all 6 endpoints

**Files:**
- Modify: `app/modules/beasiswa/routes.py:992-1077`
- Test: `app/tests/test_beasiswa_routes.py`

**Interfaces:**
- Consumes: all 6 `get_dashboard_*` functions from Tasks 1-2, each now accepting a trailing `statuses` kwarg.
- Produces: each route now defaults to `statuses=['complete']` when the `statuses` query key is entirely absent from the request, and to whatever comma-split list results otherwise (including `[]` for an explicit-but-empty value) — this is the one place in the whole feature where `['complete']` is chosen as a default, matching today's UI-visible behavior.

- [ ] **Step 1: Write the failing tests**

Add to `app/tests/test_beasiswa_routes.py` (uses the file's existing `login`/`_select_etf` helpers and `client` fixture):

```python
def _seed_dashboard_payment(company_id, code, amount, status):
    from database import get_conn
    conn = get_conn()
    conn.execute(
        """INSERT INTO siswa (company_id, code, nama, jenjang, angkatan, program, status)
           VALUES (?,?,?,?,?,?,?)""",
        (company_id, code, "Siswa Status Filter", "S1", 2025, "SMART", "Aktif")
    )
    conn.execute(
        """INSERT INTO payment_beasiswa
           (company_id, siswa_code, cat1, cat2, tanggal, amount, pillar, status)
           VALUES (?,?,?,?,?,?,?,?)""",
        (company_id, code, "By Pendidikan", "Semester 1", "2026-03-15", amount, "AGRI", status)
    )
    conn.commit()
    conn.close()


def test_api_dashboard_summary_statuses_absent_defaults_to_complete_only(client):
    login(client)
    _select_etf(client)
    _seed_dashboard_payment(2, "1250777", 1_000_000, "open")
    resp = client.get("/beasiswa/api/dashboard/summary")
    assert resp.status_code == 200
    row = next(r for r in resp.get_json()["data"] if r["siswa_code"] == "1250777")
    assert row["realisasi_total"] == 0.0, "statuses param absent -> route defaults to complete-only"


def test_api_dashboard_summary_statuses_explicit_empty_means_no_restriction(client):
    login(client)
    _select_etf(client)
    _seed_dashboard_payment(2, "1250778", 1_000_000, "open")
    resp = client.get("/beasiswa/api/dashboard/summary?statuses=")
    assert resp.status_code == 200
    row = next(r for r in resp.get_json()["data"] if r["siswa_code"] == "1250778")
    assert row["realisasi_total"] == 1_000_000, "statuses explicitly empty -> no restriction, open counts"


def test_api_dashboard_summary_statuses_open_only(client):
    login(client)
    _select_etf(client)
    _seed_dashboard_payment(2, "1250779", 5_000_000, "open")
    resp = client.get("/beasiswa/api/dashboard/summary?statuses=open")
    assert resp.status_code == 200
    row = next(r for r in resp.get_json()["data"] if r["siswa_code"] == "1250779")
    assert row["realisasi_total"] == 5_000_000


def test_api_dashboard_latest_payments_statuses_param_round_trips(client):
    login(client)
    _select_etf(client)
    _seed_dashboard_payment(2, "1250780", 2_000_000, "open")
    resp = client.get("/beasiswa/api/dashboard/latest_payments?statuses=open,complete")
    assert resp.status_code == 200
    codes = [r["nama"] for r in resp.get_json()["data"]]
    assert "Siswa Status Filter" in codes
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd app && python -m pytest tests/test_beasiswa_routes.py -k "statuses" -v`
Expected: FAIL — `test_api_dashboard_summary_statuses_absent_defaults_to_complete_only` fails because the route doesn't apply any status default yet (today's route always calls the service with no `statuses` arg at all, which after Tasks 1-2 means "no restriction", so the open row would incorrectly show `realisasi_total == 1_000_000` instead of the expected `0.0`).

- [ ] **Step 3: Update all 6 routes**

In `app/modules/beasiswa/routes.py`, each of the 6 handlers (`api_dashboard_summary`, `api_dashboard_breakdown`, `api_dashboard_monthly`, `api_dashboard_latest_payments`, `api_dashboard_program_summary`, `api_dashboard_pillar_yearly`) gets the same two changes: one new block to parse `statuses`, and `statuses` added as the last positional arg to the service call.

`api_dashboard_summary` (`:992-1004`) — current:

```python
@bp.route("/api/dashboard/summary")
@jwt_html_required
@etf_company_required
def api_dashboard_summary():
    years_str = request.args.get("years", "")
    pillars_str = request.args.get("pillars", "")
    years = [int(y) for y in years_str.split(",")] if years_str else []
    pillars = [p for p in pillars_str.split(",") if p]
    programs_str = request.args.get("programs", "")
    jenjangs_str = request.args.get("jenjangs", "")
    programs = [p for p in programs_str.split(",") if p]
    jenjangs = [j for j in jenjangs_str.split(",") if j]
    return jsonify({"ok": True, "data": get_dashboard_summary(_cid(), years, pillars, programs, jenjangs)})
```

New:

```python
@bp.route("/api/dashboard/summary")
@jwt_html_required
@etf_company_required
def api_dashboard_summary():
    years_str = request.args.get("years", "")
    pillars_str = request.args.get("pillars", "")
    years = [int(y) for y in years_str.split(",")] if years_str else []
    pillars = [p for p in pillars_str.split(",") if p]
    programs_str = request.args.get("programs", "")
    jenjangs_str = request.args.get("jenjangs", "")
    programs = [p for p in programs_str.split(",") if p]
    jenjangs = [j for j in jenjangs_str.split(",") if j]
    statuses_str = request.args.get("statuses")
    statuses = ["complete"] if statuses_str is None else [s for s in statuses_str.split(",") if s]
    return jsonify({"ok": True, "data": get_dashboard_summary(_cid(), years, pillars, programs, jenjangs, statuses)})
```

Apply the identical `statuses_str`/`statuses` block (unchanged in every route — `request.args.get("statuses")` with no default, so it's `None` when the key is absent, `""` when present-but-blank) plus the trailing `statuses` arg to the other 5 handlers the same way:

`api_dashboard_breakdown` (`:1007-1019`):

```python
@bp.route("/api/dashboard/breakdown")
@jwt_html_required
@etf_company_required
def api_dashboard_breakdown():
    years_str = request.args.get("years", "")
    pillars_str = request.args.get("pillars", "")
    years = [int(y) for y in years_str.split(",")] if years_str else []
    pillars = [p for p in pillars_str.split(",") if p]
    programs_str = request.args.get("programs", "")
    jenjangs_str = request.args.get("jenjangs", "")
    programs = [p for p in programs_str.split(",") if p]
    jenjangs = [j for j in jenjangs_str.split(",") if j]
    statuses_str = request.args.get("statuses")
    statuses = ["complete"] if statuses_str is None else [s for s in statuses_str.split(",") if s]
    return jsonify({"ok": True, "data": get_dashboard_breakdown(_cid(), years, pillars, programs, jenjangs, statuses)})
```

`api_dashboard_monthly` (`:1022-1034`):

```python
@bp.route("/api/dashboard/monthly")
@jwt_html_required
@etf_company_required
def api_dashboard_monthly():
    years_str = request.args.get("years", "")
    pillars_str = request.args.get("pillars", "")
    years = [int(y) for y in years_str.split(",")] if years_str else []
    pillars = [p for p in pillars_str.split(",") if p]
    programs_str = request.args.get("programs", "")
    jenjangs_str = request.args.get("jenjangs", "")
    programs = [p for p in programs_str.split(",") if p]
    jenjangs = [j for j in jenjangs_str.split(",") if j]
    statuses_str = request.args.get("statuses")
    statuses = ["complete"] if statuses_str is None else [s for s in statuses_str.split(",") if s]
    return jsonify({"ok": True, "data": get_dashboard_monthly(_cid(), years, pillars, programs, jenjangs, statuses)})
```

`api_dashboard_latest_payments` (`:1037-1049`):

```python
@bp.route("/api/dashboard/latest_payments")
@jwt_html_required
@etf_company_required
def api_dashboard_latest_payments():
    years_str = request.args.get("years", "")
    pillars_str = request.args.get("pillars", "")
    years = [int(y) for y in years_str.split(",")] if years_str else []
    pillars = [p for p in pillars_str.split(",") if p]
    programs_str = request.args.get("programs", "")
    jenjangs_str = request.args.get("jenjangs", "")
    programs = [p for p in programs_str.split(",") if p]
    jenjangs = [j for j in jenjangs_str.split(",") if j]
    statuses_str = request.args.get("statuses")
    statuses = ["complete"] if statuses_str is None else [s for s in statuses_str.split(",") if s]
    return jsonify({"ok": True, "data": get_dashboard_latest_payments(_cid(), years, pillars, programs, jenjangs, statuses)})
```

`api_dashboard_program_summary` (`:1052-1064`):

```python
@bp.route("/api/dashboard/program_summary")
@jwt_html_required
@etf_company_required
def api_dashboard_program_summary():
    years_str = request.args.get("years", "")
    pillars_str = request.args.get("pillars", "")
    years = [int(y) for y in years_str.split(",")] if years_str else []
    pillars = [p for p in pillars_str.split(",") if p]
    programs_str = request.args.get("programs", "")
    jenjangs_str = request.args.get("jenjangs", "")
    programs = [p for p in programs_str.split(",") if p]
    jenjangs = [j for j in jenjangs_str.split(",") if j]
    statuses_str = request.args.get("statuses")
    statuses = ["complete"] if statuses_str is None else [s for s in statuses_str.split(",") if s]
    return jsonify({"ok": True, "data": get_dashboard_program_summary(_cid(), years, pillars, programs, jenjangs, statuses)})
```

`api_dashboard_pillar_yearly` (`:1067-1077`, no `years` param on this one — leave that as-is):

```python
@bp.route("/api/dashboard/pillar_yearly")
@jwt_html_required
@etf_company_required
def api_dashboard_pillar_yearly():
    pillars_str = request.args.get("pillars", "")
    pillars = [p for p in pillars_str.split(",") if p]
    programs_str = request.args.get("programs", "")
    jenjangs_str = request.args.get("jenjangs", "")
    programs = [p for p in programs_str.split(",") if p]
    jenjangs = [j for j in jenjangs_str.split(",") if j]
    statuses_str = request.args.get("statuses")
    statuses = ["complete"] if statuses_str is None else [s for s in statuses_str.split(",") if s]
    return jsonify({"ok": True, "data": get_dashboard_pillar_yearly(_cid(), pillars, programs, jenjangs, statuses)})
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd app && python -m pytest tests/test_beasiswa_routes.py -k "statuses" -v`
Expected: PASS.

- [ ] **Step 5: Run the full beasiswa test suite to check for regressions**

Run: `cd app && python -m pytest tests/test_beasiswa_service.py tests/test_beasiswa_routes.py -v`
Expected: all PASS, including every dashboard-related test written before this plan (they call routes/functions with no `statuses` arg or query param, which now resolves to the same `['complete']`-only behavior they already assumed).

- [ ] **Step 6: Commit**

```bash
git add app/modules/beasiswa/routes.py app/tests/test_beasiswa_routes.py
git commit -m "feat: parse statuses query param on all 6 beasiswa dashboard routes"
```

---

### Task 4: Frontend — Status filter chip + JS wiring

**Files:**
- Modify: `app/templates/beasiswa/index.html:91-107` (insert new chip right after the existing "Jenjang Studi" chip, before its closing `</div>` of `.beasiswa-dash-filterbar`)
- Modify: `app/static/js/dashboard_beasiswa.js:391-406`

**Interfaces:**
- Consumes: routes from Task 3 (`statuses` query param on all 6 dashboard endpoints).
- Produces: nothing consumed by later tasks — this is the last task.

- [ ] **Step 1: Add the Status filter chip to the template**

In `app/templates/beasiswa/index.html`, immediately after the "Jenjang Studi" chip closes (the `</div>` at line 106, which closes the 4th `.beasiswa-dash-filter-chip`, itself right before the `</div>` at line 107 that closes `.beasiswa-dash-filterbar`), insert a 5th chip. Current end of the filter bar (`:100-107`):

```html
                <div class="panel-opts" id="dash-filter-jenjang">
                  {% for j in jenjang %}
                  <label><input type="checkbox" class="dash-jenjang-cb" value="{{ j }}" checked> {{ j }}</label>
                  {% endfor %}
                </div>
              </div>
            </div>
          </div>
```

New (adds the Status chip between the Jenjang chip and the filter bar's closing `</div>`):

```html
                <div class="panel-opts" id="dash-filter-jenjang">
                  {% for j in jenjang %}
                  <label><input type="checkbox" class="dash-jenjang-cb" value="{{ j }}" checked> {{ j }}</label>
                  {% endfor %}
                </div>
              </div>
            </div>

            <div class="beasiswa-dash-filter-chip">
              <span class="lbl">Status</span>
              <span class="val">Complete</span>
              <span class="caret">▾</span>
              <div class="beasiswa-dash-filter-panel">
                <div class="panel-head">
                  <button type="button" data-act="all">Semua</button>
                  <button type="button" data-act="none">Kosongkan</button>
                </div>
                <div class="panel-opts" id="dash-filter-status">
                  <label><input type="checkbox" class="dash-status-cb" value="open"> Open</label>
                  <label><input type="checkbox" class="dash-status-cb" value="complete" checked> Complete</label>
                </div>
              </div>
            </div>
          </div>
```

This is a static two-option list (`open`/`complete`, per the spec — no server-driven loop needed, unlike Pillar/Program/Jenjang which come from `{% for %}` over a Jinja variable), so no route/view-function change is needed to supply new template variables.

- [ ] **Step 2: Wire the checkboxes into the filter-collection and query-string functions**

Current (`app/static/js/dashboard_beasiswa.js:391-406`):

```javascript
function dashGetSelectedFilters() {
  const years = Array.from(document.querySelectorAll(".dash-year-cb:checked")).map(function (cb) { return cb.value; });
  const pillars = Array.from(document.querySelectorAll(".dash-pillar-cb:checked")).map(function (cb) { return cb.value; });
  const programs = Array.from(document.querySelectorAll(".dash-program-cb:checked")).map(function (cb) { return cb.value; });
  const jenjangs = Array.from(document.querySelectorAll(".dash-jenjang-cb:checked")).map(function (cb) { return cb.value; });
  return { years: years, pillars: pillars, programs: programs, jenjangs: jenjangs };
}

function dashBuildQueryString(filters) {
  const params = new URLSearchParams();
  if (filters.years.length) params.set("years", filters.years.join(","));
  if (filters.pillars.length) params.set("pillars", filters.pillars.join(","));
  if (filters.programs && filters.programs.length) params.set("programs", filters.programs.join(","));
  if (filters.jenjangs && filters.jenjangs.length) params.set("jenjangs", filters.jenjangs.join(","));
  return params.toString();
}
```

New:

```javascript
function dashGetSelectedFilters() {
  const years = Array.from(document.querySelectorAll(".dash-year-cb:checked")).map(function (cb) { return cb.value; });
  const pillars = Array.from(document.querySelectorAll(".dash-pillar-cb:checked")).map(function (cb) { return cb.value; });
  const programs = Array.from(document.querySelectorAll(".dash-program-cb:checked")).map(function (cb) { return cb.value; });
  const jenjangs = Array.from(document.querySelectorAll(".dash-jenjang-cb:checked")).map(function (cb) { return cb.value; });
  const statuses = Array.from(document.querySelectorAll(".dash-status-cb:checked")).map(function (cb) { return cb.value; });
  return { years: years, pillars: pillars, programs: programs, jenjangs: jenjangs, statuses: statuses };
}

function dashBuildQueryString(filters) {
  const params = new URLSearchParams();
  if (filters.years.length) params.set("years", filters.years.join(","));
  if (filters.pillars.length) params.set("pillars", filters.pillars.join(","));
  if (filters.programs && filters.programs.length) params.set("programs", filters.programs.join(","));
  if (filters.jenjangs && filters.jenjangs.length) params.set("jenjangs", filters.jenjangs.join(","));
  if (filters.statuses && filters.statuses.length) params.set("statuses", filters.statuses.join(","));
  return params.toString();
}
```

Note: if every status checkbox is unchecked (user clicks "Kosongkan" on the Status chip), `filters.statuses` is `[]`, so `dashBuildQueryString` omits the `statuses` param entirely from the URL — which the route layer (Task 3) then reads as `statuses_str is None` and defaults to `['complete']`, NOT "no restriction" as the spec intends for an explicit empty selection. This is an existing, accepted quirk shared with every other filter chip on this dashboard (unchecking all Pillar/Program/Jenjang boxes has the identical effect: the param is omitted from the URL, not sent as empty, so the backend can't distinguish "user cleared everything" from "user never touched this filter"). Not introduced by this task, not a regression — matches current behavior for the other 3 chips exactly. Out of scope to fix here (would require changing `dashBuildQueryString`'s omit-when-empty convention for all 4 filters, which is a separate, broader change).

The existing "Semua"/"Kosongkan" panel-header buttons and the chip's collapsed-state label (`<span class="val">`) are wired generically by shared dashboard JS that already handles this pattern for the other 3 chips (checking `.panel-opts input[type=checkbox]` under the clicked chip, and re-deriving the `<span class="val">` summary text from however many boxes are checked) — verify this generic wiring picks up the new `#dash-filter-status` panel automatically (it should, since it's selector-based on the chip DOM structure, not a hardcoded list of chip IDs); no JS change needed for those two behaviors unless verification in Step 3 shows otherwise.

- [ ] **Step 3: Manual verification**

Start the dev server, open the Beasiswa dashboard, and confirm:
1. The "Status" chip appears after "Jenjang Studi", showing "Complete" as its collapsed summary, with only "Complete" checked when the panel is opened.
2. Clicking "Semua" checks both Open and Complete; clicking "Kosongkan" unchecks both; both trigger a data refresh (same as the existing chips).
3. Checking "Open" in addition to "Complete" changes the Realisasi figures (Trend per Bulan, summary cards, breakdown tables) to include `open`-status payments — numbers should increase or stay the same, never decrease, versus the Complete-only default.
4. Reloading the page resets the Status chip back to Complete-only (no persistence, per spec's Out of Scope).

- [ ] **Step 4: Commit**

```bash
git add app/templates/beasiswa/index.html app/static/js/dashboard_beasiswa.js
git commit -m "feat: add Status filter chip to Beasiswa dashboard UI"
```
