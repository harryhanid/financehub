# Days of PAM — Lazy-Load Enhancement Spec

**Date:** 2026-06-01
**Module:** FinanceHub / ETF / Payment Approval Memo
**Feature:** Lazy-load Days of PAM tab (AJAX on-demand fetch)
**Prior Spec:** `docs/superpowers/specs/2026-05-31-days-of-pam-design.md`

---

## Problem

The original Days of PAM implementation embeds all `dop_rows` in the page at load time via
`get_days_of_pam(company_id)` + `DOP_DATA = {{ dop_rows | tojson }}`. When the dataset is large
(hundreds of payment rows), this makes the `/payment-memo/` page noticeably slow even when the user
never opens the Days of PAM tab. All DB work and DOM work is wasted for every page load.

---

## Goal

Zero DB cost at page load for Days of PAM. Data only fetched when the user actively interacts with
the tab — specifically when they pick a value from one of the autocomplete dropdowns.

---

## Approved Approach: Lazy-Load on Tab Interaction

### UX Flow

```
1. User clicks "Days of PAM" tab
       → fetch /days-of-pam/candidates once (lightweight)
       → candidates cached in JS array

2. User types in "PAM No" or "Nama" search box
       → filter candidates in-memory to build dropdown suggestions

3. User picks a suggestion from dropdown
       → immediately POST/GET /days-of-pam/search?pam=X (or &nama=Y)
       → response rows rendered into <tbody>
       → table becomes visible
       → bulk-select/update controls become active
```

No "Tampilkan Semua" button. Table is invisible until a selection is made from the autocomplete.

---

## Backend Changes

### `service.py` — two functions

#### Keep unchanged: `get_days_of_pam(company_id)`
Used internally (still needed by `bulk_update_dates`). Not called from `index()` anymore.

#### Add: `get_days_of_pam_candidates(company_id: int) -> list`

```python
# Lightweight — returns only the 3 fields needed for autocomplete
SELECT DISTINCT
    pb.pam         AS pam_no,
    pb.siswa_code,
    s.nama
FROM payment_beasiswa pb
LEFT JOIN siswa s ON s.company_id = pb.company_id AND s.code = pb.siswa_code
WHERE pb.company_id = ?
  AND pb.pam IS NOT NULL
  AND pb.pam != ''
ORDER BY pb.pam
```

Returns `[{"pam_no": "...", "siswa_code": "...", "nama": "..."}, ...]`.

#### Keep unchanged: `bulk_update_dates(ids, dates, company_id)`

---

### `routes.py` — three changes

#### 1. Remove `dop_rows` from `index()`

```python
# BEFORE
dop_rows = get_days_of_pam(company_id)
return render_template("payment_memo/index.html", ..., dop_rows=dop_rows, ...)

# AFTER
return render_template("payment_memo/index.html", ...)
# dop_rows removed entirely
```

#### 2. Add GET `/days-of-pam/candidates`

```
GET /payment-memo/days-of-pam/candidates
Auth: @role_required("requester", "verificator", "releaser")
Response: {"ok": true, "candidates": [...]}
```

Returns `get_days_of_pam_candidates(company_id)`. Called once on first tab open; JS caches result.

#### 3. Add GET `/days-of-pam/search`

```
GET /payment-memo/days-of-pam/search?pam=PAM-001-ETF-05-2026
GET /payment-memo/days-of-pam/search?nama=Budi
Auth: @role_required("requester", "verificator", "releaser")
Response: {"ok": true, "rows": [...]}
```

Calls `get_days_of_pam(company_id)` but filtered server-side:
- `?pam=X` — WHERE pb.pam = X (exact match on pam_no from autocomplete)
- `?nama=Y` — WHERE LOWER(s.nama) LIKE '%y%' (substring, case-insensitive)
- Both params present: AND combination

Returns full row dicts (same schema as original `dop_rows`).

---

## Frontend Changes (`index.html`)

### Remove

- `{% for r in dop_rows %}` loop inside `<tbody>`
- `DOP_DATA = {{ dop_rows | tojson }};` script variable
- All client-side filter logic that iterated DOP_DATA array

### Add / Replace

#### Tab click handler

```javascript
let _dopCandidates = null;  // cached after first fetch
let _dopLoaded    = false;  // tab opened at least once

async function dopTabOpened() {
    if (_dopLoaded) return;
    _dopLoaded = true;
    const r = await apiFetch("/payment-memo/days-of-pam/candidates");
    if (r.ok) _dopCandidates = r.candidates;
}
```

Wire to existing tab-switch logic: `dopTabOpened()` fires when "Days of PAM" tab is clicked.

#### Autocomplete (same 2 inputs: PAM No, Nama)

`dopSrchInput(type)` builds suggestions from `_dopCandidates` in-memory (no AJAX per keypress).

#### On pick from dropdown → fetch rows

```javascript
async function dopPickSugg(type, value) {
    // fill input, hide dropdown
    const qs = type === "pam"  ? `pam=${encodeURIComponent(value)}`
                               : `nama=${encodeURIComponent(value)}`;
    const r = await apiFetch(`/payment-memo/days-of-pam/search?${qs}`);
    if (r.ok) dopRenderRows(r.rows);
}
```

#### `dopRenderRows(rows)`

Builds `<tr>` elements from JSON array and inserts into `<tbody id="dop-tbody">`.
Makes tbody visible, hides placeholder `#dop-ph`.
Resets `_dopSelected` Set. Calls `_dopUpdateInfo()`.

#### "Cari" fallback button

Visible button next to search inputs. Clicking it reads current input values and calls
`/days-of-pam/search?pam=...&nama=...` manually — handles the case where a user types a partial
string and presses Cari without picking from the autocomplete dropdown.

#### Secondary subheader filters

Remain as client-side filters on the rendered rows (Cat1, Cat2, Perusahaan, Pillar, Siswa Code).
These still filter the already-loaded `<tr>` elements — no extra AJAX.

#### Bulk update

`dopBulkUpdate()` unchanged — still POSTs to `/payment-memo/days-of-pam/bulk-update`.
After successful update, re-fetches the current search to refresh rows.

---

## Data Flow Diagram

```
Page load              → NO DB query for Days of PAM
Tab click              → GET /days-of-pam/candidates  (tiny, once)
User types in search   → filter _dopCandidates in memory (no AJAX)
User picks suggestion  → GET /days-of-pam/search?pam=X
                       → dopRenderRows(rows) → tbody visible
User adjusts filters   → client-side hide/show existing <tr>
User bulk-updates      → POST /days-of-pam/bulk-update
                       → re-GET /days-of-pam/search (refresh)
```

---

## Tests

Existing tests remain valid:
- `test_days_of_pam_bulk_update_ok` — POST `/days-of-pam/bulk-update`
- `test_days_of_pam_bulk_update_no_session`
- `test_days_of_pam_bulk_update_invalid_ids`

New tests to add in `test_memo_api.py`:

| Test | Endpoint | Assertion |
|------|----------|-----------|
| `test_get_dop_candidates_empty` | GET `/days-of-pam/candidates` | `ok=True, candidates=[]` |
| `test_get_dop_candidates_with_data` | seed row + GET `/days-of-pam/candidates` | 1 candidate with correct pam_no |
| `test_dop_search_by_pam` | seed row + GET `/days-of-pam/search?pam=PAM-001-ETF-05-2026` | 1 row returned |
| `test_dop_search_by_nama` | seed row + GET `/days-of-pam/search?nama=Budi` | 1 row returned |
| `test_dop_search_no_match` | GET `/days-of-pam/search?pam=NOPE` | `ok=True, rows=[]` |

---

## Files Modified

| File | Change |
|------|--------|
| `app/modules/payment_memo/service.py` | +`get_days_of_pam_candidates()` |
| `app/modules/payment_memo/routes.py` | remove `dop_rows` from `index()`, +2 GET routes |
| `app/templates/payment_memo/index.html` | remove Jinja loop + DOP_DATA embed, rewrite JS |
| `app/tests/test_memo_api.py` | +5 new tests |

No new files created.

---

## Out of Scope

- Pagination of search results (dataset expected to be manageable per PAM/nama pick)
- Server-side secondary filtering (Cat1/Cat2/etc. remain client-side on loaded rows)
- Sorting (not requested)
- Export of Days of PAM view (not requested)
