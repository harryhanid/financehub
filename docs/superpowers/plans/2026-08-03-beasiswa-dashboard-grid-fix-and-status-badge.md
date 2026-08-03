# Beasiswa Dashboard Grid Gap Fix & Latest-Transactions Status Badge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix empty grid cells left by odd-count card rows in the Beasiswa Dashboard's Grafik section, and make "20 Transaksi Terakhir" show payments of every status (not just `complete`) with a small status badge per row.

**Architecture:** A single generic CSS rule (`:nth-child(odd):last-child`) fixes the grid gap for every current and future odd-count row, with zero markup changes. The status-badge change removes a `WHERE` clause in one service function, adds one column to one table, and adds one small render helper in JS — reusing the exact badge markup already used elsewhere in this same template.

**Tech Stack:** Flask + Jinja2 template with inline vanilla JS, plain CSS (no build step) — unchanged from the prior Beasiswa Dashboard redesigns this follows.

**Spec:** `docs/superpowers/specs/2026-08-03-beasiswa-dashboard-grid-fix-and-status-badge-design.md`

## Global Constraints

- Zero changes to any card's data/chart logic other than "20 Transaksi Terakhir" — the CSS fix is layout-only and applies globally via one generic selector.
- The `rejected` status (and any other status without an explicit badge entry) falls back to plain text — matching the existing Data Payment tab's own `BADGE[r.status] || r.status` fallback behavior. Do not invent new styling for it.
- No frontend test framework exists in this codebase — verification for the CSS and template/JS pieces is app-boot + force-render (real test-DB login) + structural checks, matching the pattern established in the prior Beasiswa Dashboard redesign plans. The backend service change gets a real pytest test.
- Badge column goes at the END of the "20 Transaksi Terakhir" row (after "Realisasi"), matching the Data Payment tab's own column ordering.

---

## Task 1: Fix empty grid cells (CSS)

**Files:**
- Modify: `app/static/css/beasiswa_dashboard.css:25-29`

**Interfaces:**
- Produces: no new class — a new rule scoped to the existing `.beasiswa-dash-grafik-grid` selector, used implicitly by every card in every panel.

- [ ] **Step 1: Confirm current state before editing**

Run: `cd app && sed -n '25,29p' static/css/beasiswa_dashboard.css`
Expected output:
```css
.beasiswa-dash-grafik-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 1rem;
}
```

- [ ] **Step 2: Add the gap-fix rule immediately after this block**

Insert directly after the closing `}` of `.beasiswa-dash-grafik-grid` (i.e. after line 29), before the following `.beasiswa-dash-grafik-grid .beasiswa-dash-chart-card` rule:

```css
/* A lone trailing card in an otherwise-paired row (odd position AND last
   child) spans both columns instead of leaving the second column empty. */
.beasiswa-dash-grafik-grid > *:nth-child(odd):last-child {
  grid-column: 1 / -1;
}
```

- [ ] **Step 3: Confirm braces are balanced (catches a truncated paste)**

Run: `cd app && python3 -c "s = open('static/css/beasiswa_dashboard.css', encoding='utf-8').read(); print(s.count('{') == s.count('}'))"`
Expected: `True`

- [ ] **Step 4: Confirm the new rule is present exactly once**

Run: `cd app && grep -c "nth-child(odd):last-child" static/css/beasiswa_dashboard.css`
Expected: `1`

- [ ] **Step 5: Commit**

```bash
cd /c/Financehub
git add app/static/css/beasiswa_dashboard.css
git commit -m "fix: prevent empty grid cell when a Beasiswa Dashboard card row has an odd count"
```

---

## Task 2: Show all payment statuses in "20 Transaksi Terakhir" with a badge

**Files:**
- Modify: `app/modules/beasiswa/service.py:1382-1408` (`get_dashboard_latest_payments`)
- Modify: `app/templates/beasiswa/index.html:189-199` (`dash-latest-payments-table` thead/fallback row)
- Modify: `app/static/js/dashboard_beasiswa.js:365-380` (`dashRenderLatestPaymentsTable`), `:406` (skeleton call)
- Test: `app/tests/test_beasiswa_service.py`

**Interfaces:**
- Consumes: `_add_siswa_a()`, `add_payment_batch(company_id, siswa_code, tanggal, pillar, perusahaan, items)`, `COMPANY_ID` (existing test helpers/constants in `test_beasiswa_service.py`).
- Produces: `get_dashboard_latest_payments(...)` return-dict rows now include a `"status"` key (in addition to the existing `tanggal`, `nama`, `cat1`, `cat2`, `amount` keys) — no signature change, no other behavior change.

- [ ] **Step 1: Write the failing test**

Add to `app/tests/test_beasiswa_service.py` (add `get_dashboard_latest_payments` to the existing `from modules.beasiswa.service import (...)` block at the top of the file):

```python
def test_get_dashboard_latest_payments_includes_open_status():
    _add_siswa_a()
    add_payment_batch(COMPANY_ID, "1250001", "2026-01-15", "AGRI", "PT. SMART Tbk", [
        {"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 2000000},
    ])
    # status default 'open' -- not marked complete

    rows = get_dashboard_latest_payments(COMPANY_ID)
    assert len(rows) == 1
    assert rows[0]["status"] == "open"
    assert rows[0]["amount"] == 2000000


def test_get_dashboard_latest_payments_includes_both_open_and_complete():
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

    rows = get_dashboard_latest_payments(COMPANY_ID)
    statuses = sorted(r["status"] for r in rows)
    assert statuses == ["complete", "open"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd app && python -m pytest tests/test_beasiswa_service.py -k dashboard_latest_payments -v`
Expected: FAIL — `test_get_dashboard_latest_payments_includes_open_status` fails with `KeyError: 'status'` (the field doesn't exist yet), and `test_get_dashboard_latest_payments_includes_both_open_and_complete` fails with `assert ['complete'] == ['complete', 'open']` (the `open` row is filtered out by the current query).

- [ ] **Step 3: Update `get_dashboard_latest_payments` in `app/modules/beasiswa/service.py`**

Find (lines 1395-1405):

```python
    rows = conn.execute(
        f"""
        SELECT p.tanggal, s.nama, p.cat1, p.cat2, p.amount
        FROM payment_beasiswa p
        JOIN siswa s ON s.code = p.siswa_code AND s.company_id = p.company_id
        WHERE p.company_id = ? AND p.status = 'complete'{payment_year_sql}{pillar_sql}{program_sql}{jenjang_sql}
        ORDER BY p.tanggal DESC, p.id DESC
        LIMIT ?
        """,
        [company_id, *payment_year_params, *pillar_params, *program_params, *jenjang_params, limit],
    ).fetchall()
```

Replace with:

```python
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
```

(Only the `SELECT` column list gains `p.status`, and `AND p.status = 'complete'` is removed from the `WHERE` clause — every filter/param/order/limit is unchanged.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd app && python -m pytest tests/test_beasiswa_service.py -k dashboard_latest_payments -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Run the full service test file to confirm no regressions**

Run: `cd app && python -m pytest tests/test_beasiswa_service.py -v`
Expected: all tests PASS (no regressions — this query change only widens the result set and adds a column, no existing test asserted the old `complete`-only filtering behavior)

- [ ] **Step 6: Add the Status column to the table in `app/templates/beasiswa/index.html`**

Find (lines 189-199):

```html
                    <table id="dash-latest-payments-table">
                      <thead>
                        <tr>
                          <th>Tanggal</th>
                          <th>Nama</th>
                          <th>Kategori</th>
                          <th>Kategori 2</th>
                          <th class="num-right">Realisasi</th>
                        </tr>
                      </thead>
                      <tbody><tr><td colspan="5" style="text-align:center;color:var(--text-muted)">Memuat data...</td></tr></tbody>
                    </table>
```

Replace with:

```html
                    <table id="dash-latest-payments-table">
                      <thead>
                        <tr>
                          <th>Tanggal</th>
                          <th>Nama</th>
                          <th>Kategori</th>
                          <th>Kategori 2</th>
                          <th class="num-right">Realisasi</th>
                          <th>Status</th>
                        </tr>
                      </thead>
                      <tbody><tr><td colspan="6" style="text-align:center;color:var(--text-muted)">Memuat data...</td></tr></tbody>
                    </table>
```

- [ ] **Step 7: Add the status badge helper and render it in `app/static/js/dashboard_beasiswa.js`**

Find (lines 365-380):

```javascript
function dashRenderLatestPaymentsTable(rows) {
  const tbody = document.querySelector("#dash-latest-payments-table tbody");
  if (!rows || !rows.length) {
    tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--text-muted)">Belum ada transaksi.</td></tr>';
    return;
  }
  tbody.innerHTML = rows.map(function (r) {
    return "<tr>" +
      "<td>" + r.tanggal + "</td>" +
      "<td>" + r.nama + "</td>" +
      "<td>" + dashCatBadge(r.cat1) + "</td>" +
      "<td>" + (r.cat2 || "") + "</td>" +
      '<td class="num-right">' + dashFmtJutaan(r.amount) + "</td>" +
      "</tr>";
  }).join("");
}
```

Replace with:

```javascript
const DASH_PAYMENT_STATUS_BADGE = {
  open:     '<span style="background:#fef3c7;color:#d97706;padding:2px 8px;border-radius:99px;font-size:.72rem;font-weight:600">Open</span>',
  complete: '<span style="background:#dbeafe;color:#1d4ed8;padding:2px 8px;border-radius:99px;font-size:.72rem;font-weight:600">Complete</span>',
};
function dashPaymentStatusBadge(status) {
  return DASH_PAYMENT_STATUS_BADGE[status] || status || "";
}

function dashRenderLatestPaymentsTable(rows) {
  const tbody = document.querySelector("#dash-latest-payments-table tbody");
  if (!rows || !rows.length) {
    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--text-muted)">Belum ada transaksi.</td></tr>';
    return;
  }
  tbody.innerHTML = rows.map(function (r) {
    return "<tr>" +
      "<td>" + r.tanggal + "</td>" +
      "<td>" + r.nama + "</td>" +
      "<td>" + dashCatBadge(r.cat1) + "</td>" +
      "<td>" + (r.cat2 || "") + "</td>" +
      '<td class="num-right">' + dashFmtJutaan(r.amount) + "</td>" +
      "<td>" + dashPaymentStatusBadge(r.status) + "</td>" +
      "</tr>";
  }).join("");
}
```

- [ ] **Step 8: Update the skeleton-row column count in `dashApplyFilters()`**

Find (line 406):

```javascript
  document.querySelector("#dash-latest-payments-table tbody").innerHTML = skeletonRows(5, 5);
```

Replace with:

```javascript
  document.querySelector("#dash-latest-payments-table tbody").innerHTML = skeletonRows(5, 6);
```

- [ ] **Step 9: App-boot sanity check**

Run:
```bash
cd app && python -c "
from app import create_app
app = create_app()
print('APP_BOOT_OK')
"
```
Expected: `APP_BOOT_OK`.

- [ ] **Step 10: Force-render and verify the new structure**

Run:
```bash
cd app && python -c "
import os, sys
sys.path.insert(0, '.')
import config
config.DB_PATH = os.path.join('tests', 'test_dash_status_badge_render.db')
if os.path.exists(config.DB_PATH): os.remove(config.DB_PATH)
from database import init_db
init_db()
from app import create_app
app = create_app(testing=True)
client = app.test_client()
login = client.post('/auth/login', json={'username':'admin','password':'Admin@123'})
assert login.get_json()['ok'], login.get_json()
client.post('/select-company', data={'company_id': 2})
resp = client.get('/beasiswa/')
print('STATUS', resp.status_code)
body = resp.data.decode('utf-8', errors='replace')
print('Status column header present:', '<th>Status</th>' in body)
print('colspan=6 fallback present:', 'colspan=\"6\"' in body)
print('colspan=5 fallback gone:', 'colspan=\"5\"' not in body.split('id=\"dash-latest-payments-table\"')[1][:400])
os.remove(config.DB_PATH)
"
```
Expected: `STATUS 200`; `Status column header present: True`; `colspan=6 fallback present: True`; `colspan=5 fallback gone: True`.

- [ ] **Step 11: Structural check — badge helper exists and old status filter is gone**

Run:
```bash
cd app && python3 -c "
src = open('static/js/dashboard_beasiswa.js', encoding='utf-8').read()
assert 'function dashPaymentStatusBadge' in src
assert 'DASH_PAYMENT_STATUS_BADGE' in src
assert src.count('function dashRenderLatestPaymentsTable') == 1
print('JS_STRUCTURAL_OK')
"
```
Expected: `JS_STRUCTURAL_OK`.

Run: `cd app && grep -c "p.status = 'complete'" modules/beasiswa/service.py`
Expected: `0` (the removed filter doesn't appear anywhere else in the file with this exact text — confirms it's gone from `get_dashboard_latest_payments` and wasn't duplicated elsewhere by mistake)

- [ ] **Step 12: Commit**

```bash
cd /c/Financehub
git add app/modules/beasiswa/service.py app/templates/beasiswa/index.html app/static/js/dashboard_beasiswa.js app/tests/test_beasiswa_service.py
git commit -m "feat: show all payment statuses with a badge in Beasiswa Dashboard's 20 Transaksi Terakhir"
```

---

## Task 3: Final verification

**Files:**
- None modified (verification only)

**Interfaces:**
- Consumes: everything from Tasks 1-2

- [ ] **Step 1: Full Python regression suite**

Run: `cd app && python -m pytest tests/test_beasiswa_service.py tests/test_beasiswa_routes.py -v`
Expected: all tests pass (no backend changes outside `get_dashboard_latest_payments`, which Task 2 already verified in isolation).

- [ ] **Step 2: Manual browser check (if a preview session with non-production data is available)**

Navigate to the Beasiswa Dashboard tab. Confirm: no visibly empty grid cell remains anywhere in the Grafik section (Trend, Breakdown Realisasi, Detail Transaksi panels all look fully filled); "20 Transaksi Terakhir" shows a Status column with amber "Open" / blue "Complete" badges; a payment entered via the Data Payment tab but not yet marked complete now appears here with an "Open" badge. Skip this step if no preview/browser session with non-production data is available — do not block on it.

- [ ] **Step 3: Confirm zero blast radius outside the Beasiswa Dashboard**

Run: `cd /c/Financehub && git diff --stat HEAD~3 -- app/templates/sahabat_etf/index.html app/templates/budget/dashboard.html app/static/css/budget.css`

(Adjust `HEAD~3` if the actual number of commits from this plan's Tasks 1-2 differs.)

Expected: empty output for all 3 files, evaluated against **committed** state only.
