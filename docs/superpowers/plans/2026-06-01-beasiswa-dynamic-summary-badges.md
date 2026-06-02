# Beasiswa Dynamic Summary Badges Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the summary badge cards in Data Budget and Data Payment tabs update dynamically to reflect the currently active search/filter, showing per-category Budget, Payment, and Selisih for only the filtered data.

**Architecture:** Enrich the two list service functions (`get_budget_list`, `get_payment_list`) to return a cross-tab aggregation (payment totals for budget list, budget totals for payment list) using the same filter parameters. The frontend replaces the existing global `loadSummary()` calls with a new `_renderTabSummary()` helper that reads directly from the list response.

**Tech Stack:** Python/SQLite (service layer), Jinja2+vanilla JS (frontend). Tests via pytest with SQLite test DB.

---

## File Map

| File | Change |
|------|--------|
| `app/modules/beasiswa/service.py` | Add `payment_totals`/`payment_grand` to `get_budget_list()`; add `budget_totals`/`budget_grand` to `get_payment_list()` |
| `app/tests/test_beasiswa_service.py` | Add 4 new tests covering the cross-tab aggregations |
| `app/templates/beasiswa/index.html` | Add `_renderTabSummary()` helper; replace 3 `loadSummary()` calls |

No new files. No route changes. No new endpoints.

---

## Task 1: Enrich `get_budget_list()` with payment_totals

**Files:**
- Modify: `app/modules/beasiswa/service.py` (function `get_budget_list`, approx line 396)
- Test: `app/tests/test_beasiswa_service.py`

- [ ] **Step 1: Write the failing tests**

Add these tests to `app/tests/test_beasiswa_service.py`. Import `get_budget_list` at the top alongside existing imports:

```python
from modules.beasiswa.service import (
    generate_kode_siswa, get_siswa_list, add_siswa, update_siswa,
    add_budget_batch, add_payment_batch, get_rekap, get_sisa_budget,
    add_klaim_multi, get_klaim_list, delete_klaim_row,
    add_payment_multi, get_budget_list, get_payment_list,
)
```

Then add at the end of the file:

```python
# ── get_budget_list cross-tab payment_totals ───────────────────────────────────

def _seed_budi():
    """Helper: adds siswa Budi with budget + payment rows."""
    add_siswa(COMPANY_ID, {
        "code": "1250001", "nama": "Budi Santoso", "jenjang": "S1",
        "angkatan": 2025, "program": "SMART", "fakultas": "", "universitas": "",
        "bank": "", "norek": "", "namarek": "", "referensi": "",
        "status": "Aktif", "catatan": "",
    })
    add_budget_batch(COMPANY_ID, "1250001", "2025-03-10", "AGRI", [
        {"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 8000000},
        {"cat1": "By Tunjangan",  "cat2": "Bulanan",    "amount": 2000000},
    ])
    add_payment_batch(COMPANY_ID, "1250001", "2025-03-15", "AGRI", "PT. SMART Tbk", [
        {"cat1": "By Pendidikan", "cat2": "Semester 1", "cat3": "", "cat4": "", "amount": 5000000},
    ])


def test_get_budget_list_returns_payment_totals():
    _seed_budi()
    result = get_budget_list(COMPANY_ID)
    assert "payment_totals" in result
    assert result["payment_totals"].get("By Pendidikan") == 5000000
    assert result["payment_grand"] == 5000000


def test_get_budget_list_payment_totals_filtered_by_search():
    _seed_budi()
    # Add another siswa with payment that should NOT appear
    add_siswa(COMPANY_ID, {
        "code": "1250002", "nama": "Rina Wati", "jenjang": "S1",
        "angkatan": 2025, "program": "SMART", "fakultas": "", "universitas": "",
        "bank": "", "norek": "", "namarek": "", "referensi": "",
        "status": "Aktif", "catatan": "",
    })
    add_payment_batch(COMPANY_ID, "1250002", "2025-03-20", "AGRI", "PT. SMART Tbk", [
        {"cat1": "By Pendidikan", "cat2": "Semester 1", "cat3": "", "cat4": "", "amount": 3000000},
    ])
    # Filter by Budi's name only
    result = get_budget_list(COMPANY_ID, search="Budi")
    assert result["payment_totals"].get("By Pendidikan") == 5000000
    # Rina's 3_000_000 must not be included
    assert result["payment_grand"] == 5000000
```

- [ ] **Step 2: Run tests to verify they fail**

```
cd C:/Financehub/app && python -m pytest tests/test_beasiswa_service.py::test_get_budget_list_returns_payment_totals tests/test_beasiswa_service.py::test_get_budget_list_payment_totals_filtered_by_search -v
```

Expected: FAIL with `KeyError: 'payment_totals'`

- [ ] **Step 3: Add the payment_totals query to `get_budget_list()`**

In `app/modules/beasiswa/service.py`, find `get_budget_list()`. After the line:

```python
    grand  = sum(totals.values())
```

Add the cross-tab payment aggregation before the `rows` query:

```python
    # Cross-tab: payment totals for same filter scope
    pay_sql = (
        "SELECT pb.cat1, SUM(pb.amount) AS total FROM payment_beasiswa pb "
        "LEFT JOIN siswa s ON s.company_id=pb.company_id AND s.code=pb.siswa_code "
        "WHERE pb.company_id=?"
    )
    pay_params = [company_id]
    if search:
        q2 = f"%{search}%"
        pay_sql += (" AND (pb.siswa_code LIKE ? OR s.nama LIKE ? OR pb.cat1 LIKE ?"
                    " OR pb.cat2 LIKE ? OR pb.pillar LIKE ? OR s.program LIKE ?)")
        pay_params += [q2, q2, q2, q2, q2, q2]
    if cat1:
        pay_sql += " AND pb.cat1=?"
        pay_params += [cat1]
    if pillar:
        pay_sql += " AND pb.pillar=?"
        pay_params += [pillar]
    if program:
        pay_sql += " AND s.program=?"
        pay_params += [program]
    if bulan:
        pay_sql += " AND strftime('%m', pb.tanggal) = ?"
        pay_params += [bulan.zfill(2)]
    if tahun:
        pay_sql += " AND strftime('%Y', pb.tanggal) = ?"
        pay_params += [tahun]
    pay_sql += " GROUP BY pb.cat1"
    payment_totals = {r[0]: r[1] for r in conn.execute(pay_sql, pay_params).fetchall()}
    payment_grand  = sum(payment_totals.values())
```

Update the `return` statement at the end of `get_budget_list()` from:

```python
    return {"rows": rows, "total": total, "totals": totals, "grand": grand}
```

to:

```python
    return {
        "rows": rows, "total": total,
        "totals": totals, "grand": grand,
        "payment_totals": payment_totals, "payment_grand": payment_grand,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```
cd C:/Financehub/app && python -m pytest tests/test_beasiswa_service.py::test_get_budget_list_returns_payment_totals tests/test_beasiswa_service.py::test_get_budget_list_payment_totals_filtered_by_search -v
```

Expected: PASS ✓

- [ ] **Step 5: Run full test suite to confirm no regressions**

```
cd C:/Financehub/app && python -m pytest tests/ -v
```

Expected: All existing tests PASS

- [ ] **Step 6: Commit**

```bash
git add app/modules/beasiswa/service.py app/tests/test_beasiswa_service.py
git commit -m "feat(beasiswa): add payment_totals to get_budget_list response"
```

---

## Task 2: Enrich `get_payment_list()` with budget_totals

**Files:**
- Modify: `app/modules/beasiswa/service.py` (function `get_payment_list`, approx line 439)
- Test: `app/tests/test_beasiswa_service.py`

- [ ] **Step 1: Write the failing tests**

Add to `app/tests/test_beasiswa_service.py` after the Task 1 tests:

```python
# ── get_payment_list cross-tab budget_totals ───────────────────────────────────

def test_get_payment_list_returns_budget_totals():
    _seed_budi()
    result = get_payment_list(COMPANY_ID)
    assert "budget_totals" in result
    assert result["budget_totals"].get("By Pendidikan") == 8000000
    assert result["budget_totals"].get("By Tunjangan")  == 2000000
    assert result["budget_grand"] == 10000000


def test_get_payment_list_budget_totals_filtered_by_search():
    _seed_budi()
    # Add another siswa with budget that should NOT appear
    add_siswa(COMPANY_ID, {
        "code": "1250002", "nama": "Rina Wati", "jenjang": "S1",
        "angkatan": 2025, "program": "SMART", "fakultas": "", "universitas": "",
        "bank": "", "norek": "", "namarek": "", "referensi": "",
        "status": "Aktif", "catatan": "",
    })
    add_budget_batch(COMPANY_ID, "1250002", "2025-03-10", "AGRI", [
        {"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 6000000},
    ])
    # Filter by Budi only
    result = get_payment_list(COMPANY_ID, search="Budi")
    assert result["budget_totals"].get("By Pendidikan") == 8000000
    # Rina's 6_000_000 must not be included
    assert result["budget_grand"] == 10000000
```

- [ ] **Step 2: Run tests to verify they fail**

```
cd C:/Financehub/app && python -m pytest tests/test_beasiswa_service.py::test_get_payment_list_returns_budget_totals tests/test_beasiswa_service.py::test_get_payment_list_budget_totals_filtered_by_search -v
```

Expected: FAIL with `KeyError: 'budget_totals'`

- [ ] **Step 3: Add the budget_totals query to `get_payment_list()`**

In `app/modules/beasiswa/service.py`, find `get_payment_list()`. After the line:

```python
    grand  = sum(totals.values())
```

Add the cross-tab budget aggregation before the `rows` query:

```python
    # Cross-tab: budget totals for same filter scope
    bgt_sql = (
        "SELECT bb.cat1, SUM(bb.amount) AS total FROM budget_beasiswa bb "
        "LEFT JOIN siswa s ON s.company_id=bb.company_id AND s.code=bb.siswa_code "
        "WHERE bb.company_id=?"
    )
    bgt_params = [company_id]
    if search:
        q2 = f"%{search}%"
        bgt_sql += (" AND (bb.siswa_code LIKE ? OR s.nama LIKE ? OR bb.cat1 LIKE ?"
                    " OR bb.cat2 LIKE ? OR bb.pillar LIKE ? OR s.program LIKE ?)")
        bgt_params += [q2, q2, q2, q2, q2, q2]
    if cat1:
        bgt_sql += " AND bb.cat1=?"
        bgt_params += [cat1]
    if pillar:
        bgt_sql += " AND bb.pillar=?"
        bgt_params += [pillar]
    if program:
        bgt_sql += " AND s.program=?"
        bgt_params += [program]
    if bulan:
        bgt_sql += " AND strftime('%m', bb.tanggal) = ?"
        bgt_params += [bulan.zfill(2)]
    if tahun:
        bgt_sql += " AND strftime('%Y', bb.tanggal) = ?"
        bgt_params += [tahun]
    bgt_sql += " GROUP BY bb.cat1"
    budget_totals = {r[0]: r[1] for r in conn.execute(bgt_sql, bgt_params).fetchall()}
    budget_grand  = sum(budget_totals.values())
```

Update the `return` statement at the end of `get_payment_list()` from:

```python
    return {"rows": rows, "total": total, "totals": totals, "grand": grand}
```

to:

```python
    return {
        "rows": rows, "total": total,
        "totals": totals, "grand": grand,
        "budget_totals": budget_totals, "budget_grand": budget_grand,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```
cd C:/Financehub/app && python -m pytest tests/test_beasiswa_service.py::test_get_payment_list_returns_budget_totals tests/test_beasiswa_service.py::test_get_payment_list_budget_totals_filtered_by_search -v
```

Expected: PASS ✓

- [ ] **Step 5: Run full test suite**

```
cd C:/Financehub/app && python -m pytest tests/ -v
```

Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add app/modules/beasiswa/service.py app/tests/test_beasiswa_service.py
git commit -m "feat(beasiswa): add budget_totals to get_payment_list response"
```

---

## Task 3: Frontend — _renderTabSummary helper + wiring

**Files:**
- Modify: `app/templates/beasiswa/index.html`

There are no automated tests for vanilla JS in this codebase. Verification is done manually via the running app.

- [ ] **Step 1: Add `_renderTabSummary` helper function**

In `app/templates/beasiswa/index.html`, find the `loadSummary` function (approx line 1401). Insert the new helper **immediately before** `loadSummary`:

```javascript
function _renderTabSummary(prefix, bgtTotals, payTotals) {
  const CATS = [
    { key: "By Pendidikan", pfx: "pend"  },
    { key: "By Tunjangan",  pfx: "tunj"  },
    { key: "By Penelitian", pfx: "penel" },
    { key: "By Medical",    pfx: "med"   },
  ];
  let totB = 0, totP = 0;
  CATS.forEach(({ key, pfx }) => {
    const b = (bgtTotals && bgtTotals[key]) || 0;
    const p = (payTotals && payTotals[key]) || 0;
    document.getElementById(`${prefix}-sum-${pfx}-b`).textContent = fmtRupiah(b);
    document.getElementById(`${prefix}-sum-${pfx}-p`).textContent = fmtRupiah(p);
    const sel = document.getElementById(`${prefix}-sum-${pfx}-s`);
    sel.textContent = fmtRupiah(b - p);
    sel.style.color = (b - p) < 0 ? "var(--danger)" : "";
    totB += b; totP += p;
  });
  document.getElementById(`${prefix}-sum-tot-b`).textContent = fmtRupiah(totB);
  document.getElementById(`${prefix}-sum-tot-p`).textContent = fmtRupiah(totP);
  const totSel = document.getElementById(`${prefix}-sum-tot-s`);
  totSel.textContent = fmtRupiah(totB - totP);
  totSel.style.color = (totB - totP) < 0 ? "var(--danger)" : "";
}
```

- [ ] **Step 2: Wire `loadBudgetList()` to use the helper**

Find in `loadBudgetList()` (approx line 919):

```javascript
    const d = await (await apiFetch(`/beasiswa/budget/list?${params}`)).json();
    loadSummary();
```

Replace `loadSummary()` with:

```javascript
    const d = await (await apiFetch(`/beasiswa/budget/list?${params}`)).json();
    _renderTabSummary('bgt', d.totals, d.payment_totals);
```

- [ ] **Step 3: Wire `loadPaymentList()` to use the helper**

Find in `loadPaymentList()` (approx line 1363):

```javascript
    const d = await (await apiFetch(`/beasiswa/payment/list?${params}`)).json();
    loadSummary();
```

Replace `loadSummary()` with:

```javascript
    const d = await (await apiFetch(`/beasiswa/payment/list?${params}`)).json();
    _renderTabSummary('pay', d.budget_totals, d.totals);
```

- [ ] **Step 4: Remove redundant `loadSummary()` call from `_bgtAfterSave()`**

Find `_bgtAfterSave()` (approx line 1122):

```javascript
async function _bgtAfterSave() {
  loadSummary();
  if (_bgtContext === "input") {
```

Remove only the `loadSummary();` line. Result:

```javascript
async function _bgtAfterSave() {
  if (_bgtContext === "input") {
```

(The badge update will happen naturally when `loadBudgetList()` is called on the next line.)

- [ ] **Step 5: Verify manually**

Start the Flask server:
```
cd C:/Financehub/app && python run.py
```

Open the Beasiswa page. Check:

1. **No filter applied** → badges show totals for all data (same as before)
2. **Data Budget tab → search by siswa name** → badges update: budget total matches rows shown, payment total matches that siswa's payments
3. **Data Budget tab → filter Bulan=Maret** → badges show only March budget + March payment
4. **Data Budget tab → filter cat1=By Pendidikan** → all 4 category badges show their own filtered values; non-Pendidikan categories show 0
5. **Data Payment tab → same checks as above** — badges update using `d.budget_totals` for Budget column
6. **Add/edit/delete a budget row** → after save, Data Budget tab reloads → badges reflect the updated data

- [ ] **Step 6: Commit**

```bash
git add app/templates/beasiswa/index.html
git commit -m "feat(beasiswa): dynamic summary badges reflect active search/filter"
```
