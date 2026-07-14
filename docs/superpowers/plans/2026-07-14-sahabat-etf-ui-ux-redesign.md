# Sahabat ETF UI/UX Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the Sahabat ETF dashboard tab (`app/templates/beasiswa/index.html`, `#tab-sahabat-etf`) per [2026-07-14-sahabat-etf-ui-ux-redesign-design.md](../specs/2026-07-14-sahabat-etf-ui-ux-redesign-design.md): accordion layout, stat-card accent, chart drill-down, pillar multi-select, stable category colors, theme-aware chart text, and skeleton loaders.

**Architecture:** No new modules or tables. All changes are inside the existing `sahabat_etf` Flask blueprint (`app/modules/sahabat_etf/`), its Jinja template block, and its two static assets (`sahabat_etf.js`, `budget.css`). Backend changes are additive/renaming parameter changes to existing pure functions; frontend changes are template restructuring + vanilla JS, no new libraries.

**Tech Stack:** Python 3 / Flask / sqlite3 (backend), Jinja2 + vanilla JS + Chart.js v4 + ChartDataLabels (frontend), pytest (backend tests only — this project has no JS test framework, so JS-only tasks end in a manual verification step instead of an automated test, consistent with how the rest of the codebase already handles frontend behavior).

## Global Constraints

- All `pillar: str = None` service parameters become `pillars: list = None` (list, plural) — this is a deliberate breaking rename, not additive. Every call site (service internals, routes, tests) must be updated in the same task that renames the function it belongs to.
- Filter semantics must not change: `pillars` only ever filters `payment_beasiswa` rows; `budget_beasiswa` always shows unfiltered by pillar (already true today, must stay true).
- Existing element IDs (`setf-summary`, `setf-table`, `setf-kategori-table`, `setf-pillar-table`, `setf-latest-payments-table`, `setf-monthly-table`, `setf-alert-card`, `chart-bulanan`, `chart-tahunan`, `chart-kategori`) must not change — only their position in the DOM (which accordion they live in) changes.
- No new npm/pip dependencies.
- Reuse existing helpers instead of inventing new ones: `skeletonRows()` (`app/static/js/app.js:244`), `.fh-skel` (`app/static/css/style.css:318`), `_year_filter_sql()` pattern (`app/modules/sahabat_etf/service.py:6-10`).

## Correction from brainstorm mockups

The visual-companion mockups shown during brainstorming used **illustrative** stat-card names ("Total Budget / Total Realisasi / Sisa Budget / Over-Budget", 4 cards) to make the "standout card" decision easy to see. The **real** `setf-summary` grid (`app/static/js/sahabat_etf.js:95-101`) has **5** cards: Total Anggota Aktif, Total Budget, Total Payment, Total Realisasi, Sisa Budget — there is no "Over-Budget count" stat card (over-budget siswa are listed in the separate `setf-alert-card`, unaffected by this plan). The approved decision ("keep equal grid, give Total Realisasi a left-accent stripe") still applies directly — Task 5 below implements it against the real 5-card set.

---

### Task 1: Pillar filter as a list — service layer

**Files:**
- Modify: `app/modules/sahabat_etf/service.py:6-10` (add helper), `:13-63` (`get_siswa_summary`), `:66-119` (`get_kategori_breakdown`), `:147-184` (`get_all_transactions`), `:223-277` (`get_monthly_breakdown`), `:280-321` (`get_pillar_breakdown`), `:323-340` (`get_latest_payments`), `:342-364` (`get_yearly_breakdown`)
- Test: `app/tests/test_sahabat_etf_service.py:246-269,292-304,323-338,380-390,428-439`

**Interfaces:**
- Produces: `_pillar_filter_sql(pillars: list, column: str) -> tuple[str, list]` — same shape as the existing `_year_filter_sql`. Every `get_*` function in this module now takes `pillars: list = None` instead of `pillar: str = None` (same position in the signature).

- [ ] **Step 1: Write the failing tests (rename existing pillar tests to lists, add a multi-pillar test)**

Edit `app/tests/test_sahabat_etf_service.py`:

Replace line 254:
```python
    rows = get_siswa_summary(COMPANY_ID, pillar="SETF")
```
with:
```python
    rows = get_siswa_summary(COMPANY_ID, pillars=["SETF"])
```

Replace line 266:
```python
    rows = get_siswa_summary(COMPANY_ID, pillar="SETF")
```
with:
```python
    rows = get_siswa_summary(COMPANY_ID, pillars=["SETF"])
```

Replace line 300:
```python
    result = get_kategori_breakdown(COMPANY_ID, pillar="SETF")
```
with:
```python
    result = get_kategori_breakdown(COMPANY_ID, pillars=["SETF"])
```

Replace line 334:
```python
    rows = get_all_transactions(COMPANY_ID, years=[2026], pillar="SETF")
```
with:
```python
    rows = get_all_transactions(COMPANY_ID, years=[2026], pillars=["SETF"])
```

Replace line 388:
```python
    result = get_monthly_breakdown(COMPANY_ID, years=[2026], pillar="SETF")
```
with:
```python
    result = get_monthly_breakdown(COMPANY_ID, years=[2026], pillars=["SETF"])
```

Replace line 436:
```python
    result = get_pillar_breakdown(COMPANY_ID, pillar="SETF")
```
with:
```python
    result = get_pillar_breakdown(COMPANY_ID, pillars=["SETF"])
```

Add a new test at the end of the file:
```python
def test_get_siswa_summary_filters_by_multiple_pillars():
    _add_siswa("9990110", "Siswa Multi Pillar")
    add_payment_batch(COMPANY_ID, "9990110", "2026-01-15", "APP", "ETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 1000000}])
    add_payment_batch(COMPANY_ID, "9990110", "2026-01-20", "SETF", "ETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 2000000}])
    add_payment_batch(COMPANY_ID, "9990110", "2026-01-25", "FINANCE", "ETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 4000000}])
    _mark_complete("9990110")

    rows = get_siswa_summary(COMPANY_ID, pillars=["APP", "SETF"])
    assert rows[0]["realisasi_total"] == 3000000  # APP + SETF, tanpa FINANCE
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd C:\Financehub && python -m pytest app/tests/test_sahabat_etf_service.py -v -k "pillar"`
Expected: FAIL — `TypeError: get_siswa_summary() got an unexpected keyword argument 'pillars'` (and similarly for the other functions).

- [ ] **Step 3: Add `_pillar_filter_sql` helper and migrate all 7 functions**

Edit `app/modules/sahabat_etf/service.py`. Insert right after `_year_filter_sql` (after line 10):
```python
def _pillar_filter_sql(pillars, column):
    if not pillars:
        return "", []
    placeholders = ",".join("?" for _ in pillars)
    return f" AND {column} IN ({placeholders})", list(pillars)
```

In `get_siswa_summary` (line 13), change signature and pillar line:
```python
def get_siswa_summary(company_id: int, years: list = None, pillars: list = None) -> list:
    conn = get_conn()
    budget_year_sql, budget_year_params = _year_filter_sql(years, "tanggal")
    payment_year_sql, payment_year_params = _year_filter_sql(years, "tanggal")
    pillar_sql, pillar_params = _pillar_filter_sql(pillars, "pillar")
```

In `get_kategori_breakdown` (line 66), change signature, pillar line, and the internal call:
```python
def get_kategori_breakdown(company_id: int, years: list = None, pillars: list = None) -> dict:
    conn = get_conn()
    budget_year_sql, budget_year_params = _year_filter_sql(years, "b.tanggal")
    payment_year_sql, payment_year_params = _year_filter_sql(years, "p.tanggal")
    pillar_sql, pillar_params = _pillar_filter_sql(pillars, "p.pillar")
```
And at line 115 change:
```python
        for s in get_siswa_summary(company_id, years, pillar)
```
to:
```python
        for s in get_siswa_summary(company_id, years, pillars)
```

In `get_all_transactions` (line 147):
```python
def get_all_transactions(company_id: int, years: list = None, pillars: list = None) -> list:
    conn = get_conn()
    budget_year_sql, budget_year_params = _year_filter_sql(years, "b.tanggal")
    payment_year_sql, payment_year_params = _year_filter_sql(years, "p.tanggal")
    pillar_sql, pillar_params = _pillar_filter_sql(pillars, "p.pillar")
```

In `get_monthly_breakdown` (line 223), change signature and line 241:
```python
def get_monthly_breakdown(company_id: int, years: list = None, pillars: list = None) -> dict:
```
```python
    pillar_sql, pillar_params = _pillar_filter_sql(pillars, "p.pillar")
```

In `get_pillar_breakdown` (line 280):
```python
def get_pillar_breakdown(company_id: int, years: list = None, pillars: list = None) -> list:
    conn = get_conn()
    budget_year_sql, budget_year_params = _year_filter_sql(years, "b.tanggal")
    payment_year_sql, payment_year_params = _year_filter_sql(years, "p.tanggal")
    pillar_sql, pillar_params = _pillar_filter_sql(pillars, "p.pillar")
```

In `get_latest_payments` (line 323):
```python
def get_latest_payments(company_id: int, years: list = None, pillars: list = None, limit: int = 10) -> list:
    conn = get_conn()
    payment_year_sql, payment_year_params = _year_filter_sql(years, "p.tanggal")
    pillar_sql, pillar_params = _pillar_filter_sql(pillars, "p.pillar")
```

In `get_yearly_breakdown` (line 342):
```python
def get_yearly_breakdown(company_id: int, years: list = None, pillars: list = None) -> list:
    conn = get_conn()
    payment_year_sql, payment_year_params = _year_filter_sql(years, "p.tanggal")
    pillar_sql, pillar_params = _pillar_filter_sql(pillars, "p.pillar")
```

(No other lines in any of these 7 functions change — the `f"""..."""` SQL bodies already interpolate `{pillar_sql}` / execute with `*pillar_params`, which keep working unchanged since `_pillar_filter_sql` returns the same shape as before.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd C:\Financehub && python -m pytest app/tests/test_sahabat_etf_service.py -v`
Expected: all tests PASS (26 existing + 1 new = 27 passed).

- [ ] **Step 5: Commit**

```bash
cd C:/Financehub
git add app/modules/sahabat_etf/service.py app/tests/test_sahabat_etf_service.py
git commit -m "feat(setf): change pillar filter from single value to list across service layer"
```

---

### Task 2: Pillar filter as a list — routes layer

**Files:**
- Modify: `app/modules/sahabat_etf/routes.py:16-20` (`_parse_filters`), and every call site that unpacks its return value (`:42,50-53,61,71,119,136`)
- Test: `app/tests/test_sahabat_etf_routes.py:229,308`

**Interfaces:**
- Consumes: `get_siswa_summary`, `get_kategori_breakdown`, `get_all_transactions`, `get_monthly_breakdown`, `get_pillar_breakdown`, `get_latest_payments`, `get_yearly_breakdown` — all now take `pillars: list = None` (Task 1).
- Produces: `_parse_filters() -> tuple[list|None, list|None]` — query param name is now `pillars` (comma-separated), not `pillar`.

- [ ] **Step 1: Write the failing tests**

Edit `app/tests/test_sahabat_etf_routes.py`. Replace line 229:
```python
    resp = client.get("/beasiswa/sahabat/api/breakdown?pillar=APP")
```
with:
```python
    resp = client.get("/beasiswa/sahabat/api/breakdown?pillars=APP")
```

Replace line 308:
```python
    resp = client.get("/beasiswa/sahabat/export/detail?pillar=SETF")
```
with:
```python
    resp = client.get("/beasiswa/sahabat/export/detail?pillars=SETF")
```

Add a new test at the end of the file:
```python
def test_api_breakdown_respects_multiple_pillars_query_param(client):
    login(client)
    _select_etf(client)
    client.post("/beasiswa/siswa/tambah", json={
        "code": "9992030", "nama": "Siswa Multi Pillar Route", "jenjang": "S1", "angkatan": 2024,
        "program": "Sahabat ETF", "fakultas": "", "universitas": "", "bank": "",
        "norek": "", "namarek": "", "referensi": "", "status": "Aktif", "catatan": "",
    })
    client.post("/beasiswa/payment/tambah", json={"code": "9992030", "tanggal": "2026-01-15",
        "pillar": "APP", "perusahaan": "ETF",
        "items": [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 500000}]})
    client.post("/beasiswa/payment/tambah", json={"code": "9992030", "tanggal": "2026-01-20",
        "pillar": "FINANCE", "perusahaan": "ETF",
        "items": [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 700000}]})

    resp = client.get("/beasiswa/sahabat/api/breakdown?pillars=APP,FINANCE")
    data = resp.get_json()
    by_cat = {k["cat1"]: k for k in data["kategori"]}
    assert by_cat["By Pendidikan"]["realisasi"] == 1200000
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd C:\Financehub && python -m pytest app/tests/test_sahabat_etf_routes.py -v -k "pillar"`
Expected: FAIL — old tests fail because `?pillar=` is no longer read by `_parse_filters` after Step 3, new test fails because it's not wired up yet (run this check again after Step 3's rename to confirm the old-param tests would break, then fix — practically: write test first, then implement, then both pass together in Step 4).

- [ ] **Step 3: Rename `_parse_filters` and every call site**

Edit `app/modules/sahabat_etf/routes.py`. Replace lines 16-20:
```python
def _parse_filters():
    years_param = request.args.get("years", "")
    years = [int(y) for y in years_param.split(",") if y.strip().isdigit()] if years_param else None
    pillar = request.args.get("pillar") or None
    return years, pillar
```
with:
```python
def _parse_filters():
    years_param = request.args.get("years", "")
    years = [int(y) for y in years_param.split(",") if y.strip().isdigit()] if years_param else None
    pillars_param = request.args.get("pillars", "")
    pillars = [p for p in pillars_param.split(",") if p.strip()] if pillars_param else None
    return years, pillars
```

Replace line 42 (`api_summary`):
```python
    years, pillar = _parse_filters()
    return jsonify({"rows": get_siswa_summary(_cid(), years, pillar)})
```
with:
```python
    years, pillars = _parse_filters()
    return jsonify({"rows": get_siswa_summary(_cid(), years, pillars)})
```

Replace lines 50-54 (`api_breakdown`):
```python
    years, pillar = _parse_filters()
    result = get_kategori_breakdown(_cid(), years, pillar)
    result["pillar"] = get_pillar_breakdown(_cid(), years, pillar)
    result["yearly"] = get_yearly_breakdown(_cid(), years, pillar)
    return jsonify(result)
```
with:
```python
    years, pillars = _parse_filters()
    result = get_kategori_breakdown(_cid(), years, pillars)
    result["pillar"] = get_pillar_breakdown(_cid(), years, pillars)
    result["yearly"] = get_yearly_breakdown(_cid(), years, pillars)
    return jsonify(result)
```
(Note: `result["pillar"]` is the *output* key name for the pillar-breakdown data — unrelated to the filter param, do not rename it.)

Replace lines 61-64 (`api_monthly`):
```python
    years, pillar = _parse_filters()
    if not years:
        return jsonify({"ok": False, "pesan": "Parameter years wajib diisi."}), 400
    return jsonify(get_monthly_breakdown(_cid(), years, pillar))
```
with:
```python
    years, pillars = _parse_filters()
    if not years:
        return jsonify({"ok": False, "pesan": "Parameter years wajib diisi."}), 400
    return jsonify(get_monthly_breakdown(_cid(), years, pillars))
```

Replace line 71-72 (`api_latest_payments` — full replacement happens in Task 3; for now just rename the variable):
```python
    years, pillar = _parse_filters()
    return jsonify({"rows": get_latest_payments(_cid(), years, pillar, limit=10)})
```
with:
```python
    years, pillars = _parse_filters()
    return jsonify({"rows": get_latest_payments(_cid(), years, pillars, limit=10)})
```

Replace line 119 (`export_summary`):
```python
    years, pillar = _parse_filters()
    rows = get_siswa_summary(_cid(), years, pillar)
```
with:
```python
    years, pillars = _parse_filters()
    rows = get_siswa_summary(_cid(), years, pillars)
```

Replace line 136 (`export_detail`):
```python
    years, pillar = _parse_filters()
    rows = get_all_transactions(_cid(), years, pillar)
```
with:
```python
    years, pillars = _parse_filters()
    rows = get_all_transactions(_cid(), years, pillars)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd C:\Financehub && python -m pytest app/tests/test_sahabat_etf_routes.py app/tests/test_sahabat_etf_service.py -v`
Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
cd C:/Financehub
git add app/modules/sahabat_etf/routes.py app/tests/test_sahabat_etf_routes.py
git commit -m "feat(setf): parse pillars as comma-separated list in routes, matching service layer"
```

---

### Task 3: Kategori-filterable latest payments (drill-down backend)

**Files:**
- Modify: `app/modules/sahabat_etf/service.py:323-340` (`get_latest_payments`), `app/modules/sahabat_etf/routes.py:67-72` (`api_latest_payments`)
- Test: `app/tests/test_sahabat_etf_service.py`, `app/tests/test_sahabat_etf_routes.py`

**Interfaces:**
- Produces: `get_latest_payments(company_id, years=None, pillars=None, kategori: str = None, limit: int = 10) -> list` — new optional `kategori` param filters `p.cat1 = ?`.
- Route `/api/latest_payments` accepts an optional `?kategori=` query param; when present, the effective `limit` becomes 30 (server picks this, not the client) so a category filter doesn't just re-show the same 10 rows.

- [ ] **Step 1: Write the failing tests**

Add to `app/tests/test_sahabat_etf_service.py`:
```python
def test_get_latest_payments_filters_by_kategori():
    _add_siswa("9990120", "Siswa Latest Kategori")
    add_payment_batch(COMPANY_ID, "9990120", "2026-01-10", "SETF", "ETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 1000000}])
    add_payment_batch(COMPANY_ID, "9990120", "2026-01-11", "SETF", "ETF",
        [{"cat1": "By Tunjangan", "cat2": "Semester 1", "amount": 2000000}])
    _mark_complete("9990120")

    from modules.sahabat_etf.service import get_latest_payments
    rows = get_latest_payments(COMPANY_ID, kategori="By Tunjangan")
    assert len(rows) == 1
    assert rows[0]["amount"] == 2000000
```

Add to `app/tests/test_sahabat_etf_routes.py`:
```python
def test_api_latest_payments_kategori_filter_raises_limit_to_30(client):
    login(client)
    _select_etf(client)
    client.post("/beasiswa/siswa/tambah", json={
        "code": "9992040", "nama": "Siswa Latest 31", "jenjang": "S1", "angkatan": 2024,
        "program": "Sahabat ETF", "fakultas": "", "universitas": "", "bank": "",
        "norek": "", "namarek": "", "referensi": "", "status": "Aktif", "catatan": "",
    })
    for day in range(1, 26):
        client.post("/beasiswa/payment/tambah", json={"code": "9992040", "tanggal": f"2026-01-{day:02d}",
            "pillar": "SETF", "perusahaan": "ETF",
            "items": [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 100000}]})

    resp = client.get("/beasiswa/sahabat/api/latest_payments?kategori=By Pendidikan")
    data = resp.get_json()
    assert len(data["rows"]) == 25  # semua 25 muncul, batas 30 tidak kepotong

    resp_unfiltered = client.get("/beasiswa/sahabat/api/latest_payments")
    assert len(resp_unfiltered.get_json()["rows"]) == 10  # tanpa filter tetap limit 10
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd C:\Financehub && python -m pytest app/tests/test_sahabat_etf_service.py::test_get_latest_payments_filters_by_kategori app/tests/test_sahabat_etf_routes.py::test_api_latest_payments_kategori_filter_raises_limit_to_30 -v`
Expected: FAIL — `TypeError: get_latest_payments() got an unexpected keyword argument 'kategori'`.

- [ ] **Step 3: Implement**

Edit `app/modules/sahabat_etf/service.py`, replace lines 323-340:
```python
def get_latest_payments(company_id: int, years: list = None, pillars: list = None,
                         kategori: str = None, limit: int = 10) -> list:
    conn = get_conn()
    payment_year_sql, payment_year_params = _year_filter_sql(years, "p.tanggal")
    pillar_sql, pillar_params = _pillar_filter_sql(pillars, "p.pillar")
    kategori_sql, kategori_params = (" AND p.cat1 = ?", [kategori]) if kategori else ("", [])

    rows = conn.execute(
        f"""
        SELECT p.tanggal, s.nama, p.cat1, p.amount
        FROM payment_beasiswa p
        JOIN siswa s ON s.code = p.siswa_code AND s.company_id = p.company_id
        WHERE p.company_id = ? AND s.program = ? AND p.status = 'complete'{payment_year_sql}{pillar_sql}{kategori_sql}
        ORDER BY p.tanggal DESC, p.id DESC
        LIMIT ?
        """,
        [company_id, PROGRAM_NAME, *payment_year_params, *pillar_params, *kategori_params, limit],
    ).fetchall()

    return [dict(r) for r in rows]
```

Edit `app/modules/sahabat_etf/routes.py`, replace lines 67-72:
```python
@bp.route("/api/latest_payments")
@jwt_html_required
@etf_company_required
def api_latest_payments():
    years, pillars = _parse_filters()
    return jsonify({"rows": get_latest_payments(_cid(), years, pillars, limit=10)})
```
with:
```python
@bp.route("/api/latest_payments")
@jwt_html_required
@etf_company_required
def api_latest_payments():
    years, pillars = _parse_filters()
    kategori = request.args.get("kategori") or None
    limit = 30 if kategori else 10
    return jsonify({"rows": get_latest_payments(_cid(), years, pillars, kategori=kategori, limit=limit)})
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd C:\Financehub && python -m pytest app/tests/test_sahabat_etf_service.py app/tests/test_sahabat_etf_routes.py -v`
Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
cd C:/Financehub
git add app/modules/sahabat_etf/service.py app/modules/sahabat_etf/routes.py app/tests/test_sahabat_etf_service.py app/tests/test_sahabat_etf_routes.py
git commit -m "feat(setf): add kategori filter to get_latest_payments, raise limit to 30 when filtered"
```

---

### Task 4: Accordion layout — restructure the tab into 3 sections

**Files:**
- Modify: `app/templates/beasiswa/index.html:442-538` (the whole `#tab-sahabat-etf` panel)
- Modify: `app/static/css/budget.css` (append accordion styles)
- Test: `app/tests/test_sahabat_etf_routes.py`

**Interfaces:**
- Produces: `<details id="setf-detail-tabel">` — the element Tasks 9/10's JS will call `.open = true` on and `.scrollIntoView()`.

- [ ] **Step 1: Write the failing test**

Add to `app/tests/test_sahabat_etf_routes.py`:
```python
def test_beasiswa_page_sahabat_etf_detail_tabel_collapsed_by_default(client):
    login(client)
    _select_etf(client)
    resp = client.get("/beasiswa/")
    assert b'<details class="setf-accordion" id="setf-detail-tabel">' in resp.data
    assert b'<details class="setf-accordion" open>' in resp.data
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd C:\Financehub && python -m pytest app/tests/test_sahabat_etf_routes.py::test_beasiswa_page_sahabat_etf_detail_tabel_collapsed_by_default -v`
Expected: FAIL — assertion error, current markup has no `<details>` elements.

- [ ] **Step 3: Restructure the template**

Edit `app/templates/beasiswa/index.html`, replace the entire block from line 442 (`<div class="tab-panel budget-page" id="tab-sahabat-etf">`) to line 539 (its closing `</div>`) with:

```html
  <div class="tab-panel budget-page" id="tab-sahabat-etf">
    {% if setf_wrong_company %}
    <div class="budget-card">
      <h3>Program khusus Eka Tjipta Foundation</h3>
      <p>Tab ini hanya menampilkan data untuk company ETF. Company aktif Anda saat ini bukan ETF.</p>
      <a class="budget-btn" href="{{ url_for('dashboard.select_company') }}">Ganti Company</a>
    </div>
    {% else %}

    <details class="setf-accordion" open>
      <summary>Ringkasan &amp; Alert</summary>
      <div class="setf-accordion-body">
        <div class="filter-bar">
          <div class="filter-field setf-filter-field-wide">
            <label>Tahun</label>
            <button type="button" id="setf-year-select-all" class="btn btn-secondary btn-sm" style="margin-bottom:.375rem">Pilih Semua</button>
            <div id="setf-filter-tahun">
              {% for y in setf_available_years %}
              <label style="display:inline-flex;align-items:center;gap:.25rem;margin-right:.75rem;font-weight:400">
                <input type="checkbox" class="setf-year-cb" value="{{ y }}" checked>
                {{ y }}
              </label>
              {% endfor %}
            </div>
          </div>
          <div class="filter-field">
            <label>Pillar</label>
            <div id="setf-filter-pillar">
              {% for p in setf_available_pillars %}
              <label style="display:inline-flex;align-items:center;gap:.25rem;margin-right:.75rem;font-weight:400">
                <input type="checkbox" class="setf-pillar-cb" value="{{ p }}">
                {{ p }}
              </label>
              {% endfor %}
            </div>
          </div>
        </div>

        <div class="budget-toolbar">
          <a class="budget-btn" id="setf-export-summary" href="{{ url_for('sahabat_etf.export_summary') }}">Export Ringkasan (Excel)</a>
          <a class="budget-btn" id="setf-export-detail" href="{{ url_for('sahabat_etf.export_detail') }}">Export Detail Transaksi (Excel)</a>
        </div>

        <div class="budget-summary-grid" id="setf-summary"></div>

        <div class="budget-card" id="setf-alert-card" style="display:none">
          <h3>Anggota Over-Budget</h3>
          <ul id="setf-alert-list"></ul>
        </div>
      </div>
    </details>

    <details class="setf-accordion" open>
      <summary>Grafik</summary>
      <div class="setf-accordion-body">
        <div class="budget-chart-grid">
          <div class="budget-chart-card"><h3>Realisasi per Bulan</h3><canvas id="chart-bulanan"></canvas></div>
          <div class="budget-chart-card"><h3>Realisasi per Tahun</h3><canvas id="chart-tahunan"></canvas></div>
          <div class="budget-chart-card">
            <h3>Realisasi per Kategori</h3>
            <div class="setf-kategori-flex">
              <canvas id="chart-kategori"></canvas>
              <table id="setf-kategori-table" class="setf-kategori-table">
                <thead><tr><th>Kategori</th><th>Budget</th><th>Realisasi</th><th>Sisa</th></tr></thead>
                <tbody><tr><td colspan="4" style="text-align:center;color:var(--text-muted)">Memuat data...</td></tr></tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </details>

    <details class="setf-accordion" id="setf-detail-tabel">
      <summary>Detail Tabel</summary>
      <div class="setf-accordion-body">
        <div class="budget-chart-card">
          <h3>Realisasi per Pillar</h3>
          <table id="setf-pillar-table">
            <thead><tr><th>Pillar</th><th>Budget</th><th>Realisasi</th><th>Sisa</th></tr></thead>
            <tbody><tr><td colspan="4" style="text-align:center;color:var(--text-muted)">Memuat data...</td></tr></tbody>
          </table>
        </div>

        <div class="budget-chart-card">
          <h3>10 Transaksi Terakhir</h3>
          <div id="setf-drilldown-chip" class="setf-drilldown-chip" style="display:none"></div>
          <table id="setf-latest-payments-table">
            <thead>
              <tr>
                <th>Tanggal</th>
                <th>Nama</th>
                <th>Kategori</th>
                <th class="num-right">Realisasi</th>
              </tr>
            </thead>
            <tbody><tr><td colspan="4" style="text-align:center;color:var(--text-muted)">Memuat data...</td></tr></tbody>
          </table>
        </div>

        <div class="table-wrap">
          <h3>Perbandingan Realisasi per Bulan per Tahun</h3>
          <table id="setf-monthly-table">
            <thead><tr id="setf-monthly-thead-row"><th>Bulan</th></tr></thead>
            <tbody><tr><td style="text-align:center;color:var(--text-muted)">Memuat data...</td></tr></tbody>
          </table>
        </div>

        <div class="table-wrap">
          <h3>Rincian Budget vs Realisasi per Anggota</h3>
          <table id="setf-table">
            <thead>
              <tr><th>Nama</th><th>Jenjang</th><th>Angkatan</th><th>Status</th>
                  <th>Budget</th><th>Payment</th><th>Realisasi</th><th>Sisa</th></tr>
            </thead>
            <tbody><tr><td colspan="8" style="text-align:center;color:var(--text-muted)">Memuat data...</td></tr></tbody>
          </table>
        </div>
      </div>
    </details>
    {% endif %}
  </div>
```

Append to `app/static/css/budget.css`:
```css
.setf-accordion {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  margin-bottom: 1rem;
  overflow: hidden;
}
.setf-accordion > summary {
  cursor: pointer;
  padding: .85rem 1.25rem;
  font-weight: 700;
  color: var(--text-primary);
  list-style: none;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.setf-accordion > summary::-webkit-details-marker { display: none; }
.setf-accordion > summary::after {
  content: "\25BE";
  color: var(--text-secondary);
  transition: transform .15s ease;
}
.setf-accordion:not([open]) > summary::after { transform: rotate(-90deg); }
.setf-accordion-body { padding: 0 1.25rem 1.25rem; }
.setf-drilldown-chip {
  background: var(--accent-glow);
  border: 1px solid var(--border-hover);
  border-radius: 999px;
  padding: .35rem .85rem;
  font-size: .8rem;
  margin-bottom: .75rem;
  display: inline-flex;
  align-items: center;
  gap: .5rem;
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd C:\Financehub && python -m pytest app/tests/test_sahabat_etf_routes.py -v`
Expected: all tests PASS, including `test_beasiswa_page_contains_sahabat_etf_dashboard_elements_for_etf_company` (unchanged IDs) and the new collapsed-by-default test.

- [ ] **Step 5: Commit**

```bash
cd C:/Financehub
git add app/templates/beasiswa/index.html app/static/css/budget.css app/tests/test_sahabat_etf_routes.py
git commit -m "feat(setf): restructure tab into 3 accordion sections (Ringkasan, Grafik, Detail Tabel)"
```

---

### Task 5: Stat card — Total Realisasi accent stripe

**Files:**
- Modify: `app/static/js/sahabat_etf.js:89-106` (`setfRenderSummaryCards`)
- Modify: `app/static/css/budget.css` (append)

**Interfaces:**
- No signature changes — `setfRenderSummaryCards(rows)` keeps the same call site in `setfApplyFilters` (Task 11 will touch the same function again to add a skeleton step first, so leave room above the `cards` array).

- [ ] **Step 1: Implement (no automated test — pure CSS/markup, verified in Task 12's manual pass)**

Edit `app/static/js/sahabat_etf.js`, replace lines 95-105:
```js
  const cards = [
    ["Total Anggota Aktif", totalSiswa],
    ["Total Budget", setfFmtJutaan(totalBudget)],
    ["Total Payment", setfFmtJutaan(totalPayment)],
    ["Total Realisasi", setfFmtJutaan(totalRealisasi)],
    ["Sisa Budget", setfFmtJutaan(totalSisa)],
  ];
  document.getElementById("setf-summary").innerHTML = cards.map(function (c) {
    return '<div class="budget-stat-card"><div class="label">' + c[0] +
      '</div><div class="value">' + c[1] + "</div></div>";
  }).join("");
```
with:
```js
  const cards = [
    ["Total Anggota Aktif", totalSiswa, ""],
    ["Total Budget", setfFmtJutaan(totalBudget), ""],
    ["Total Payment", setfFmtJutaan(totalPayment), ""],
    ["Total Realisasi", setfFmtJutaan(totalRealisasi), " setf-stat-realisasi"],
    ["Sisa Budget", setfFmtJutaan(totalSisa), ""],
  ];
  document.getElementById("setf-summary").innerHTML = cards.map(function (c) {
    return '<div class="budget-stat-card' + c[2] + '"><div class="label">' + c[0] +
      '</div><div class="value">' + c[1] + "</div></div>";
  }).join("");
```

Append to `app/static/css/budget.css`:
```css
.setf-stat-realisasi {
  border-left: 3px solid var(--accent-light);
}
.setf-stat-realisasi .value {
  color: var(--accent-light);
}
```

- [ ] **Step 2: Manual check**

Run: `python run.py`, log in, select company ETF, open tab "Sahabat ETF". Confirm the "Total Realisasi" card has a left indigo stripe and indigo-colored value, while the other 4 cards look unchanged.

- [ ] **Step 3: Commit**

```bash
cd C:/Financehub
git add app/static/js/sahabat_etf.js app/static/css/budget.css
git commit -m "feat(setf): add accent stripe to Total Realisasi stat card"
```

---

### Task 6: Filter Pillar — dropdown to checkbox multi-select

**Files:**
- Modify: `app/static/js/sahabat_etf.js:255-259` (`setfGetSelectedFilters`), `:261-266` (`setfBuildQueryString`), `:349-361` (`loadSahabatEtf` listener wiring)
- Test: `app/tests/test_sahabat_etf_routes.py`

(Template already updated in Task 4 — `#setf-filter-pillar` is now a `<div>` of `.setf-pillar-cb` checkboxes, mirroring `#setf-filter-tahun`.)

**Interfaces:**
- Produces: `setfGetSelectedFilters() -> {years: string[], pillars: string[]}` (was `{years, pillar}` — singular `pillar` string is gone everywhere in JS too).

- [ ] **Step 1: Write the failing test**

Add to `app/tests/test_sahabat_etf_routes.py`:
```python
def test_beasiswa_page_shows_pillar_filter_checkboxes_when_data_exists(client):
    login(client)
    _select_etf(client)
    client.post("/beasiswa/siswa/tambah", json={
        "code": "9992050", "nama": "Siswa Pillar Checkbox", "jenjang": "S1", "angkatan": 2024,
        "program": "Sahabat ETF", "fakultas": "", "universitas": "", "bank": "",
        "norek": "", "namarek": "", "referensi": "", "status": "Aktif", "catatan": "",
    })
    client.post("/beasiswa/payment/tambah", json={"code": "9992050", "tanggal": "2026-01-15",
        "pillar": "SETF", "perusahaan": "ETF",
        "items": [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 500000}]})

    resp = client.get("/beasiswa/")
    assert b'class="setf-pillar-cb"' in resp.data
    assert b"SETF" in resp.data
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd C:\Financehub && python -m pytest app/tests/test_sahabat_etf_routes.py::test_beasiswa_page_shows_pillar_filter_checkboxes_when_data_exists -v`
Expected: this specific test actually already PASSES after Task 4's template change (the checkbox markup was already introduced there). Run it now to confirm — if it passes, that's expected (Task 4 already did the template half of this task); proceed straight to Step 3 for the JS half, which is what's still missing.

- [ ] **Step 3: Update JS to read/build pillar filters as a list**

Edit `app/static/js/sahabat_etf.js`, replace lines 255-259:
```js
function setfGetSelectedFilters() {
  const years = Array.from(document.querySelectorAll(".setf-year-cb:checked")).map(function (cb) { return cb.value; });
  const pillar = document.getElementById("setf-filter-pillar").value;
  return { years: years, pillar: pillar };
}
```
with:
```js
function setfGetSelectedFilters() {
  const years = Array.from(document.querySelectorAll(".setf-year-cb:checked")).map(function (cb) { return cb.value; });
  const pillars = Array.from(document.querySelectorAll(".setf-pillar-cb:checked")).map(function (cb) { return cb.value; });
  return { years: years, pillars: pillars };
}
```

Replace lines 261-266:
```js
function setfBuildQueryString(filters) {
  const params = new URLSearchParams();
  if (filters.years.length) params.set("years", filters.years.join(","));
  if (filters.pillar) params.set("pillar", filters.pillar);
  return params.toString();
}
```
with:
```js
function setfBuildQueryString(filters) {
  const params = new URLSearchParams();
  if (filters.years.length) params.set("years", filters.years.join(","));
  if (filters.pillars.length) params.set("pillars", filters.pillars.join(","));
  return params.toString();
}
```

Replace lines 349-361 (inside `loadSahabatEtf`):
```js
  if (!setfListenersWired) {
    document.querySelectorAll(".setf-year-cb").forEach(function (cb) {
      cb.addEventListener("change", setfApplyFilters);
    });
    document.getElementById("setf-filter-pillar").addEventListener("change", setfApplyFilters);
    const selectAllBtn = document.getElementById("setf-year-select-all");
    if (selectAllBtn) {
      selectAllBtn.addEventListener("click", function () {
        document.querySelectorAll(".setf-year-cb").forEach(function (cb) { cb.checked = true; });
        setfApplyFilters();
      });
    }
    setfListenersWired = true;
  }
```
with:
```js
  if (!setfListenersWired) {
    document.querySelectorAll(".setf-year-cb").forEach(function (cb) {
      cb.addEventListener("change", setfApplyFilters);
    });
    document.querySelectorAll(".setf-pillar-cb").forEach(function (cb) {
      cb.addEventListener("change", setfApplyFilters);
    });
    const selectAllBtn = document.getElementById("setf-year-select-all");
    if (selectAllBtn) {
      selectAllBtn.addEventListener("click", function () {
        document.querySelectorAll(".setf-year-cb").forEach(function (cb) { cb.checked = true; });
        setfApplyFilters();
      });
    }
    setfListenersWired = true;
  }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd C:\Financehub && python -m pytest app/tests/test_sahabat_etf_routes.py -v`
Expected: all tests PASS.

- [ ] **Step 5: Manual check**

`python run.py` → tab Sahabat ETF → tick 2 pillar checkboxes at once → confirm the table/charts refetch and narrow to the union of both pillars (not just the last one clicked).

- [ ] **Step 6: Commit**

```bash
cd C:/Financehub
git add app/static/js/sahabat_etf.js app/tests/test_sahabat_etf_routes.py
git commit -m "feat(setf): read/send pillar filter as multi-select checkboxes instead of single dropdown"
```

---

### Task 7: Stable per-category chart colors

**Files:**
- Modify: `app/static/js/sahabat_etf.js:1-17` (top of file, add palette + resolver), `:294-319` (`setfApplyFilters`'s breakdown fetch)

**Interfaces:**
- Produces: `setfColorForCategory(name: string) -> string` (hex color) — first-seen-order, stable per session across refetches.

- [ ] **Step 1: Implement (no automated test — pure JS color logic, verified visually in Task 12)**

Edit `app/static/js/sahabat_etf.js`, insert after line 3 (`const SETF_BULAN_LABEL = [...]`):
```js
const SETF_PALETTE = ["#6366f1", "#818cf8", "#f97316", "#06b6d4", "#10b981", "#f59e0b"];
const setfCategoryColorMap = {};
function setfColorForCategory(name) {
  if (!setfCategoryColorMap[name]) {
    const idx = Object.keys(setfCategoryColorMap).length % SETF_PALETTE.length;
    setfCategoryColorMap[name] = SETF_PALETTE[idx];
  }
  return setfCategoryColorMap[name];
}
```

Replace lines 310-313 (inside `setfApplyFilters`'s `/api/breakdown` `.then`):
```js
      setfRenderDoughnutChart("chart-kategori",
        data.kategori.map(function (k) { return k.cat1; }),
        data.kategori.map(function (k) { return k.realisasi; }),
        ["#6366f1", "#818cf8", "#f97316", "#06b6d4", "#10b981", "#f59e0b"]);
```
with:
```js
      setfRenderDoughnutChart("chart-kategori",
        data.kategori.map(function (k) { return k.cat1; }),
        data.kategori.map(function (k) { return k.realisasi; }),
        data.kategori.map(function (k) { return setfColorForCategory(k.cat1); }));
```

- [ ] **Step 2: Manual check**

`python run.py` → tab Sahabat ETF → note the color assigned to each kategori in the donut chart → change year/pillar filter so the fetch re-runs and the category order in the response may shift → confirm each kategori name keeps the *same* color as before the filter change.

- [ ] **Step 3: Commit**

```bash
cd C:/Financehub
git add app/static/js/sahabat_etf.js
git commit -m "feat(setf): assign chart colors per category name instead of per array index"
```

---

### Task 8: Theme-aware chart legend/axis colors

**Files:**
- Modify: `app/static/js/sahabat_etf.js:19-87` (`setfRenderBarChart`, `setfRenderDoughnutChart`)
- Modify: `app/templates/base.html:63-73` (`toggleTheme`)

**Interfaces:**
- Produces: `setfThemeColor(cssVarName: string, fallbackHex: string) -> string` — reads a `--text-*` custom property off the nearest `.budget-page` ancestor at render time.
- `window` now fires a `fh-theme-changed` event whenever `toggleTheme()` runs (harmless for every other page — nothing else needs to listen).

- [ ] **Step 1: Implement (no automated test — Chart.js canvas rendering, verified visually in Task 12)**

Edit `app/static/js/sahabat_etf.js`, insert after line 17 (`function setfFmtCompact`):
```js
function setfThemeColor(varName, fallback) {
  const page = document.querySelector(".budget-page");
  const val = page ? getComputedStyle(page).getPropertyValue(varName).trim() : "";
  return val || fallback;
}
```

In `setfRenderBarChart` (around line 26-38), replace:
```js
      plugins: {
        legend: { labels: { color: "#e2e8f0" } },
        datalabels: showDataLabels ? {
          anchor: "end", align: "top", color: "#475569", font: { size: 10 },
          formatter: function (value) { return value ? setfFmtCompact(value) : ""; },
        } : { display: false },
      },
      scales: {
        x: { ticks: { color: "#94a3b8" }, grid: { color: "rgba(148,163,184,0.1)" } },
        y: { ticks: { color: "#94a3b8" }, grid: { color: "rgba(148,163,184,0.1)" } },
      },
```
with:
```js
      plugins: {
        legend: { labels: { color: setfThemeColor("--text-primary", "#e2e8f0") } },
        datalabels: showDataLabels ? {
          anchor: "end", align: "top", color: setfThemeColor("--text-muted", "#475569"), font: { size: 10 },
          formatter: function (value) { return value ? setfFmtCompact(value) : ""; },
        } : { display: false },
      },
      scales: {
        x: { ticks: { color: setfThemeColor("--text-secondary", "#94a3b8") }, grid: { color: "rgba(148,163,184,0.1)" } },
        y: { ticks: { color: setfThemeColor("--text-secondary", "#94a3b8") }, grid: { color: "rgba(148,163,184,0.1)" } },
      },
```

In `setfRenderDoughnutChart` (around line 53-54), replace:
```js
        legend: { position: "right", labels: { color: "#e2e8f0" } },
```
with:
```js
        legend: { position: "right", labels: { color: setfThemeColor("--text-primary", "#e2e8f0") } },
```

Edit `app/templates/base.html`, replace lines 63-73:
```javascript
function toggleTheme() {
  var html = document.documentElement;
  var isDark = html.getAttribute('data-theme') === 'dark';
  if (isDark) {
    html.removeAttribute('data-theme');
    localStorage.setItem('fh-theme', 'light');
  } else {
    html.setAttribute('data-theme', 'dark');
    localStorage.setItem('fh-theme', 'dark');
  }
}
```
with:
```javascript
function toggleTheme() {
  var html = document.documentElement;
  var isDark = html.getAttribute('data-theme') === 'dark';
  if (isDark) {
    html.removeAttribute('data-theme');
    localStorage.setItem('fh-theme', 'light');
  } else {
    html.setAttribute('data-theme', 'dark');
    localStorage.setItem('fh-theme', 'dark');
  }
  window.dispatchEvent(new Event('fh-theme-changed'));
}
```

Add near the bottom of `app/static/js/sahabat_etf.js` (after `loadSahabatEtf`):
```js
window.addEventListener("fh-theme-changed", function () {
  if (setfCharts["chart-kategori"] || setfCharts["chart-bulanan"] || setfCharts["chart-tahunan"]) {
    setfApplyFilters();
  }
});
```

- [ ] **Step 2: Manual check**

`python run.py` → tab Sahabat ETF (charts loaded) → toggle dark/light mode via the navbar button → confirm chart legend/axis text stays legible (dark text on light background in light mode, light text on dark background in dark mode) instead of the old always-light-colored text.

- [ ] **Step 3: Commit**

```bash
cd C:/Financehub
git add app/static/js/sahabat_etf.js app/templates/base.html
git commit -m "feat(setf): make chart legend/axis colors theme-aware instead of hardcoded"
```

---

### Task 9: Drill-down — Kategori chart click filters latest-payments table

**Files:**
- Modify: `app/static/js/sahabat_etf.js` (add drilldown state + functions; modify `setfRenderDoughnutChart`, `setfApplyFilters`)

**Interfaces:**
- Consumes: `/beasiswa/sahabat/api/latest_payments?...&kategori=` (Task 3), `<details id="setf-detail-tabel">` (Task 4), `#setf-drilldown-chip` (Task 4).
- Produces: `setfSetKategoriDrilldown(name)`, `setfClearKategoriDrilldown()` — the latter is called from an inline `onclick` in the rendered chip HTML, so it must stay a global `function`, not scoped.

- [ ] **Step 1: Implement (no automated test — Chart.js click + DOM interaction, verified manually in Task 12)**

Edit `app/static/js/sahabat_etf.js`. Add after the `setfThemeColor` function (Task 8):
```js
let setfActiveKategoriDrilldown = null;

function setfExpandDetailTabel() {
  const details = document.getElementById("setf-detail-tabel");
  if (!details) return;
  if (!details.open) details.open = true;
  details.scrollIntoView({ behavior: "smooth", block: "start" });
}

function setfRenderDrilldownChip() {
  const chip = document.getElementById("setf-drilldown-chip");
  if (!chip) return;
  if (!setfActiveKategoriDrilldown) {
    chip.style.display = "none";
    chip.innerHTML = "";
    return;
  }
  chip.style.display = "inline-flex";
  chip.innerHTML = "Filter aktif: Kategori = " + setfActiveKategoriDrilldown +
    ' <button type="button" class="budget-btn" style="padding:.15rem .6rem;font-size:.72rem" ' +
    'onclick="setfClearKategoriDrilldown()">Hapus filter</button>';
}

function setfRefetchLatestPayments() {
  const filters = setfGetSelectedFilters();
  const params = new URLSearchParams(setfBuildQueryString(filters));
  if (setfActiveKategoriDrilldown) params.set("kategori", setfActiveKategoriDrilldown);
  fetch("/beasiswa/sahabat/api/latest_payments?" + params.toString())
    .then(function (r) { return r.json(); })
    .then(function (data) { setfRenderLatestPaymentsTable(data.rows); })
    .catch(function () { showToast("Gagal memuat 10 transaksi terakhir.", "error"); });
}

function setfSetKategoriDrilldown(kategoriName) {
  setfActiveKategoriDrilldown = kategoriName;
  setfRenderDrilldownChip();
  setfExpandDetailTabel();
  setfRefetchLatestPayments();
}

function setfClearKategoriDrilldown() {
  setfActiveKategoriDrilldown = null;
  setfRenderDrilldownChip();
  setfRefetchLatestPayments();
}
```

In `setfRenderDoughnutChart`, add an `onClick` option. Replace:
```js
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
```
with:
```js
    options: {
      responsive: true,
      maintainAspectRatio: false,
      onClick: function (evt, elements) {
        if (!elements.length) return;
        setfSetKategoriDrilldown(labels[elements[0].index]);
      },
      plugins: {
```

In `setfApplyFilters`, replace the inline `/api/latest_payments` fetch block:
```js
  fetch("/beasiswa/sahabat/api/latest_payments" + (qs ? "?" + qs : ""))
    .then(function (r) { return r.json(); })
    .then(function (data) {
      setfRenderLatestPaymentsTable(data.rows);
    })
    .catch(function () { showToast("Gagal memuat 10 transaksi terakhir.", "error"); });
```
with:
```js
  setfActiveKategoriDrilldown = null;
  setfRenderDrilldownChip();
  setfRefetchLatestPayments();
```

- [ ] **Step 2: Manual check**

`python run.py` → tab Sahabat ETF → click a slice in the Kategori donut chart → confirm: "Detail Tabel" accordion auto-expands and scrolls into view, a chip appears above "10 Transaksi Terakhir" showing the clicked category, and the table narrows to that category (up to 30 rows). Click "Hapus filter" → confirm it reverts to the unfiltered top-10. Change the Tahun/Pillar filter while a drilldown is active → confirm the chip clears (drilldown resets on filter change).

- [ ] **Step 3: Commit**

```bash
cd C:/Financehub
git add app/static/js/sahabat_etf.js
git commit -m "feat(setf): kategori chart click drills down into 10-transaksi-terakhir table"
```

---

### Task 10: Drill-down — Bulanan/Tahunan chart click expands and highlights

**Files:**
- Modify: `app/static/js/sahabat_etf.js:19-41` (`setfRenderBarChart` signature), `:158-172` (`setfRenderMonthlyChart`, `setfRenderYearlyChart`)
- Modify: `app/static/css/budget.css` (append highlight style)

**Interfaces:**
- `setfRenderBarChart(canvasId, labels, datasets, showDataLabels, onBarClick)` — new optional 5th param, a `function(index)` called with the clicked bar's data index.

- [ ] **Step 1: Implement (no automated test — Chart.js click + DOM interaction, verified manually in Task 12)**

Edit `app/static/js/sahabat_etf.js`. Replace the `setfRenderBarChart` signature and body (lines 19-41):
```js
function setfRenderBarChart(canvasId, labels, datasets, showDataLabels) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  if (setfCharts[canvasId]) setfCharts[canvasId].destroy();
  setfCharts[canvasId] = new Chart(ctx, {
    type: "bar",
    data: { labels: labels, datasets: datasets },
    options: {
      responsive: true,
      plugins: {
```
with:
```js
function setfRenderBarChart(canvasId, labels, datasets, showDataLabels, onBarClick) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  if (setfCharts[canvasId]) setfCharts[canvasId].destroy();
  setfCharts[canvasId] = new Chart(ctx, {
    type: "bar",
    data: { labels: labels, datasets: datasets },
    options: {
      responsive: true,
      onClick: function (evt, elements) {
        if (!elements.length || !onBarClick) return;
        onBarClick(elements[0].index);
      },
      plugins: {
```

Add, right after `setfExpandDetailTabel` (from Task 9):
```js
function setfHighlightMonthlyRow(bulanIndex) {
  setfExpandDetailTabel();
  const tbody = document.querySelector("#setf-monthly-table tbody");
  if (!tbody) return;
  const rows = tbody.querySelectorAll("tr");
  rows.forEach(function (tr) { tr.classList.remove("setf-row-highlight"); });
  const target = rows[bulanIndex];
  if (target) {
    target.classList.add("setf-row-highlight");
    target.scrollIntoView({ behavior: "smooth", block: "center" });
  }
}
```

Replace `setfRenderMonthlyChart` (lines 158-162):
```js
function setfRenderMonthlyChart(months) {
  setfRenderBarChart("chart-bulanan", months.map(function (m) { return SETF_BULAN_LABEL[m.bulan - 1]; }), [
    { label: "Realisasi", data: months.map(function (m) { return m.realisasi; }), backgroundColor: "#818cf8" },
  ], true);
}
```
with:
```js
function setfRenderMonthlyChart(months) {
  setfRenderBarChart("chart-bulanan", months.map(function (m) { return SETF_BULAN_LABEL[m.bulan - 1]; }), [
    { label: "Realisasi", data: months.map(function (m) { return m.realisasi; }), backgroundColor: "#818cf8" },
  ], true, setfHighlightMonthlyRow);
}
```

Replace `setfRenderYearlyChart` (lines 164-172):
```js
function setfRenderYearlyChart(yearly) {
  if (!yearly || !yearly.length) {
    if (setfCharts["chart-tahunan"]) { setfCharts["chart-tahunan"].destroy(); delete setfCharts["chart-tahunan"]; }
    return;
  }
  setfRenderBarChart("chart-tahunan", yearly.map(function(y) { return y.tahun; }), [
    { label: "Realisasi", data: yearly.map(function(y) { return y.realisasi; }), backgroundColor: "#10b981" },
  ], true);
}
```
with:
```js
function setfRenderYearlyChart(yearly) {
  if (!yearly || !yearly.length) {
    if (setfCharts["chart-tahunan"]) { setfCharts["chart-tahunan"].destroy(); delete setfCharts["chart-tahunan"]; }
    return;
  }
  setfRenderBarChart("chart-tahunan", yearly.map(function(y) { return y.tahun; }), [
    { label: "Realisasi", data: yearly.map(function(y) { return y.realisasi; }), backgroundColor: "#10b981" },
  ], true, function () { setfExpandDetailTabel(); });
}
```

Append to `app/static/css/budget.css`:
```css
.setf-row-highlight td {
  background: var(--accent-glow);
  outline: 2px solid var(--accent);
  outline-offset: -2px;
}
```

- [ ] **Step 2: Manual check**

`python run.py` → tab Sahabat ETF → click a bar in "Realisasi per Bulan" → confirm "Detail Tabel" expands, scrolls in, and the matching month's row in "Perbandingan Realisasi per Bulan per Tahun" is highlighted. Click a bar in "Realisasi per Tahun" → confirm "Detail Tabel" expands and scrolls in (no highlight expected there — tahunan drill-down is intentionally scope-limited to expand+scroll, not per-column highlighting).

- [ ] **Step 3: Commit**

```bash
cd C:/Financehub
git add app/static/js/sahabat_etf.js app/static/css/budget.css
git commit -m "feat(setf): bulanan/tahunan chart click expands Detail Tabel, bulanan also highlights matching row"
```

---

### Task 11: Skeleton loaders

**Files:**
- Modify: `app/static/js/sahabat_etf.js:89-106` (add `setfRenderSummarySkeleton`), `:294-340` region (`setfApplyFilters`, add skeleton calls before each fetch)

**Interfaces:**
- Consumes: `skeletonRows(cols, count)` (`app/static/js/app.js:244`, already loaded globally via `base.html`), `.fh-skel` (`app/static/css/style.css:318`).

- [ ] **Step 1: Implement (no automated test — pure loading-state JS, verified manually in Task 12)**

Edit `app/static/js/sahabat_etf.js`, add after `setfRenderSummaryCards` (after line 106, before `setfRenderTable`):
```js
function setfRenderSummarySkeleton() {
  document.getElementById("setf-summary").innerHTML = Array(5).fill(0).map(function () {
    return '<div class="budget-stat-card"><div class="label">&nbsp;</div>' +
      '<div class="fh-skel" style="width:70%;height:20px;margin-top:.25rem"></div></div>';
  }).join("");
}
```

Edit `setfApplyFilters` — replace its opening lines:
```js
function setfApplyFilters() {
  const filters = setfGetSelectedFilters();
  const qs = setfBuildQueryString(filters);
  setfUpdateExportLinks(qs);
  setfActiveKategoriDrilldown = null;
  setfRenderDrilldownChip();
  setfRefetchLatestPayments();
```
with:
```js
function setfApplyFilters() {
  const filters = setfGetSelectedFilters();
  const qs = setfBuildQueryString(filters);
  setfUpdateExportLinks(qs);
  setfActiveKategoriDrilldown = null;
  setfRenderDrilldownChip();

  setfRenderSummarySkeleton();
  document.querySelector("#setf-table tbody").innerHTML = skeletonRows(8, 6);
  document.querySelector("#setf-kategori-table tbody").innerHTML = skeletonRows(4, 4);
  document.querySelector("#setf-pillar-table tbody").innerHTML = skeletonRows(4, 4);
  document.querySelector("#setf-latest-payments-table tbody").innerHTML = skeletonRows(4, 6);

  setfRefetchLatestPayments();
```

(Note: `setfRefetchLatestPayments()` replaced the old inline `/api/latest_payments` fetch in Task 9 — this task just adds skeleton rows immediately before it, same call stays.)

The monthly table/chart fetch further down `setfApplyFilters` needs the same treatment since it also starts from a static "Memuat data..." placeholder. Replace:
```js
  if (filters.years.length) {
    fetch("/beasiswa/sahabat/api/monthly?" + qs)
```
with:
```js
  if (filters.years.length) {
    document.querySelector("#setf-monthly-table tbody").innerHTML = skeletonRows(2, 4);
    fetch("/beasiswa/sahabat/api/monthly?" + qs)
```

- [ ] **Step 2: Manual check**

`python run.py` → tab Sahabat ETF → hard-refresh with browser devtools network throttled to "Slow 3G" → confirm each stat card and table briefly shows a shimmering skeleton placeholder instead of "Memuat data..." text, then swaps to real data.

- [ ] **Step 3: Commit**

```bash
cd C:/Financehub
git add app/static/js/sahabat_etf.js
git commit -m "feat(setf): replace text loading placeholders with shimmer skeletons"
```

---

### Task 12: Full regression + manual verification pass

**Files:** none (verification only)

- [ ] **Step 1: Run the full backend test suite**

Run: `cd C:\Financehub && python -m pytest app/tests/ -v`
Expected: all tests pass (existing + all tests added in Tasks 1-4, 6). No regressions in unrelated modules.

- [ ] **Step 2: Manual browser checklist**

`python run.py`, log in, select company ETF, open tab "Sahabat ETF", and confirm each item:

- [ ] Page loads with "Ringkasan & Alert" and "Grafik" expanded, "Detail Tabel" collapsed
- [ ] Ticking/unticking Tahun checkboxes and Pillar checkboxes both refetch and narrow results (multi-select works for both)
- [ ] "Total Realisasi" stat card shows the left accent stripe; other 4 cards unchanged
- [ ] Clicking a Kategori chart slice expands "Detail Tabel", scrolls to it, shows the filter chip, and narrows "10 Transaksi Terakhir"; "Hapus filter" clears it
- [ ] Clicking a Bulanan chart bar expands "Detail Tabel" and highlights the matching row in "Perbandingan Realisasi per Bulan per Tahun"
- [ ] Clicking a Tahunan chart bar expands "Detail Tabel" (no highlight expected)
- [ ] Toggling dark/light mode (navbar button) keeps chart legend/axis text legible in both modes
- [ ] Kategori chart colors stay the same per category name across a filter change
- [ ] Throttling network shows shimmer skeletons (not "Memuat data...") before data loads
- [ ] Export Ringkasan / Export Detail buttons still download correctly with active filters applied
- [ ] Switching to company SMT still shows the "Ganti Company" notice, unaffected by any of the above

- [ ] **Step 3: Commit (only if Step 2 surfaced fixes; otherwise nothing to commit)**

If manual verification found issues, fix them, re-run Step 1, and commit with a message describing the fix. If everything passed as-is, no commit needed for this task.
