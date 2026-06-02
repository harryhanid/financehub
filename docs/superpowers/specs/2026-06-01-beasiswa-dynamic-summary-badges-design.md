# Design: Dynamic Summary Badges — Beasiswa Data Budget & Data Payment

**Date:** 2026-06-01  
**Status:** Approved  
**Files:** `app/modules/beasiswa/service.py`, `app/templates/beasiswa/index.html`

---

## Problem

The summary badge cards at the top of the **Data Budget** and **Data Payment** tabs (By Pendidikan, By Tunjangan, By Penelitian, By Medical, Total) always display company-wide global totals regardless of active search/filter. They are not reactive.

Root cause: both `loadBudgetList()` and `loadPaymentList()` call `loadSummary()`, which fetches `/beasiswa/summary` — an endpoint with no filter parameters that aggregates all rows for the company.

The `get_budget_list()` service already returns `totals` (budget by cat1, filtered), but this is ignored; `loadSummary()` overwrites it with global data.

---

## Goal

When a user searches/filters in either tab, the 5 badge cards update to show subtotals that exactly match the currently displayed rows — both the Budget column and the Payment column, and therefore the Selisih.

Filter scope: all active filters (search/name, cat1, pillar, bulan, tahun, program) apply identically to both the budget aggregation and the payment aggregation shown in the badges.

---

## Solution: Enriched List Response (Option A)

### Backend — `app/modules/beasiswa/service.py`

**`get_budget_list()`**

After computing the existing `totals` (budget by cat1), add a second aggregation query targeting `payment_beasiswa` with identical filter conditions:

```python
pay_sql = (
    "SELECT pb.cat1, SUM(pb.amount) AS total FROM payment_beasiswa pb "
    "LEFT JOIN siswa s ON s.company_id=pb.company_id AND s.code=pb.siswa_code "
    "WHERE pb.company_id=?"
)
pay_params = [company_id]
# apply: search, cat1, pillar, program, bulan, tahun (same logic as budget SQL)
pay_sql += " GROUP BY pb.cat1"
payment_totals = {r[0]: r[1] for r in conn.execute(pay_sql, pay_params).fetchall()}
payment_grand  = sum(payment_totals.values())
```

Return dict gains two new keys: `payment_totals` and `payment_grand`.

**`get_payment_list()`**

Symmetric: add a budget aggregation query targeting `budget_beasiswa` with identical filter conditions. Return `budget_totals` and `budget_grand`.

No new endpoints. No route changes.

---

### Frontend — `app/templates/beasiswa/index.html`

**New helper** `_renderTabSummary(prefix, bgtTotals, payTotals)`:

- Iterates 4 categories (By Pendidikan → pend, By Tunjangan → tunj, By Penelitian → penel, By Medical → med)
- Sets `${prefix}-sum-${pfx}-b/p/s` for each category
- Sets `${prefix}-sum-tot-b/p/s` for the Total card
- Colors selisih red (`var(--danger)`) when negative

**`loadBudgetList()`** (line ~919):
- Replace `loadSummary()` with `_renderTabSummary('bgt', d.totals, d.payment_totals)`

**`loadPaymentList()`** (line ~1363):
- Replace `loadSummary()` with `_renderTabSummary('pay', d.budget_totals, d.totals)`

**`_bgtAfterSave()`** (line ~1122):
- Remove standalone `loadSummary()` call; badge update is handled by `loadBudgetList()` which is called immediately after

---

## Data Flow Summary

```
loadBudgetList(filters)
  → GET /beasiswa/budget/list?{filters}
  ← { rows, total, totals (budget/cat1), payment_totals (payment/cat1, same filters) }
  → _renderTabSummary('bgt', d.totals, d.payment_totals)
     updates bgt-sum-pend/tunj/penel/med/tot -b/-p/-s

loadPaymentList(filters)
  → GET /beasiswa/payment/list?{filters}
  ← { rows, total, totals (payment/cat1), budget_totals (budget/cat1, same filters) }
  → _renderTabSummary('pay', d.budget_totals, d.totals)
     updates pay-sum-pend/tunj/penel/med/tot -b/-p/-s
```

---

## Scope

- **In scope:** Dynamic badge update in Data Budget and Data Payment tabs
- **Out of scope:** Data Siswa tab rekap, Input Budget/Payment tabs, exports, API routes

---

## Test Criteria

1. Open Data Budget with no filter → badges show same totals as before
2. Search by name → badges update to show only that siswa's budget + payment
3. Filter by Bulan=Maret → badges show only March totals for both budget and payment
4. Filter cat1=By Pendidikan → both Budget and Payment in badge reflect only Pendidikan
5. Same checks on Data Payment tab
