# Design: Beasiswa Dashboard — Status Filter (Multi-Select)

**Date:** 2026-08-11
**Module:** Finance Hub — Eka Tjipta Foundation / Beasiswa / Dashboard
**Status:** Approved

---

## Summary

The Beasiswa dashboard's Realisasi figures (all charts and tables) are computed from `payment_beasiswa`, and every query currently **hardcodes** `status = 'complete'` — there is no way to see what's still `open` (submitted but not yet paid) alongside what's actually been paid. This adds a **Status** filter chip, following the exact same multi-select checkbox pattern as the existing Tahun/Pillar/Program/Jenjang Studi chips, so users can choose which statuses count toward Realisasi.

## Decisions

| Question | Decision |
|---|---|
| Status options offered | **Open, Complete** only — matches what actually exists in `payment_beasiswa` today (9,709 `complete` / 143 `open` rows; no `rejected`/`paid`/blank rows currently present). Not a fixed enum from other modules' broader status vocabulary — just what this table's data actually has. |
| Default selected state | **Complete only** — preserves today's numbers exactly on first page load. Nothing changes for an existing user until they deliberately check "Open" too. |
| Scope | **Whole dashboard** — one filter bar already controls every chart/table below it (summary cards, Trend per Bulan, Trend per Tahun, breakdown kategori/jenjang, pillar per tahun, program summary, transaksi terbaru). Status joins that same shared filter, not a one-off control on a single chart. |
| Empty selection ("Kosongkan") | No status restriction applied (shows all statuses) — consistent with how Tahun/Pillar/Program/Jenjang already behave when cleared (their SQL helpers omit the filter entirely on an empty list). |
| Missing `statuses` param (API called directly, not through the dashboard UI) | Defaults to `['complete']` — preserves current hardcoded behavior for any caller that doesn't yet know about the new param. |

---

## Architecture

### File changes

- **Modify:** `app/templates/beasiswa/index.html` — add a "Status" filter chip inside `.beasiswa-dash-filterbar` (same markup pattern as the Pillar/Program/Jenjang chips: `<span class="lbl">`, `<div class="beasiswa-dash-filter-panel">` with Semua/Kosongkan buttons, `.panel-opts` checkbox list). Checkboxes get class `dash-status-cb`, values `open` / `complete`. Only `complete` starts `checked`.
- **Modify:** `app/static/js/dashboard_beasiswa.js` — `dashGetSelectedFilters()` reads `.dash-status-cb:checked` into a `statuses` array; `dashBuildQueryString()` appends `statuses=<comma-joined>` when non-empty, same as the other three.
- **Modify:** `app/modules/beasiswa/routes.py` — all 6 dashboard API routes (`summary`, `breakdown`, `monthly`, `latest_payments`, `program_summary`, `pillar_yearly`) parse `request.args.get("statuses", "")`, split on comma, pass through as a `statuses` list to their service function. Absent param → `None` is NOT the same as empty string; routes pass `['complete']` as the default only when the query key is missing entirely (`request.args.get("statuses") is None`), otherwise pass whatever list results from splitting (including an empty list when the key is present but blank).
- **Modify:** `app/modules/beasiswa/service.py`:
  - New helper `_status_filter_sql(statuses, column)` — identical shape to `_pillar_filter_sql`/`_program_filter_sql`/`_jenjang_filter_sql` (`if not statuses: return "", []` else `AND {column} IN (...)`). Used in `get_dashboard_monthly`, `get_dashboard_pillar_yearly`, and `get_dashboard_latest_payments` (the latter gains a status filter for the first time — today it shows every status unfiltered).
  - `get_dashboard_summary` and `get_dashboard_breakdown` don't use a WHERE-level status filter, because each of their queries computes an unconditional total (`payment_total` / `total`, all statuses) side-by-side with a status-gated `realisasi_total` / `realisasi` in the same `SUM(CASE WHEN ... THEN amount ELSE 0 END)` expression. These get a small helper `_status_case_sql(statuses, column)` that returns the SQL fragment `status IN (?,?)` (or `1=1` when `statuses` is empty, meaning "count everything as realisasi") plus its params, spliced into the existing `CASE WHEN {frag} THEN amount ELSE 0 END`.
  - `get_dashboard_program_summary` needs no direct SQL change — it already delegates to `get_dashboard_summary(company_id, years, pillars, programs, jenjangs)`; that call gains a `statuses` argument and passes through.

No schema/migration changes — `payment_beasiswa.status` already exists and is already used everywhere queries currently hardcode `'complete'`.

### Signature changes

All 6 functions gain `statuses: list = None` as a new trailing keyword parameter, appended after `jenjangs` (matches the existing parameter order convention: years, pillars, programs, jenjangs, then the new one):

```python
def get_dashboard_summary(company_id, years=None, pillars=None, programs=None, jenjangs=None, statuses=None) -> list: ...
def get_dashboard_breakdown(company_id, years=None, pillars=None, programs=None, jenjangs=None, statuses=None) -> dict: ...
def get_dashboard_monthly(company_id, years=None, pillars=None, programs=None, jenjangs=None, statuses=None) -> dict: ...
def get_dashboard_latest_payments(company_id, years=None, pillars=None, programs=None, jenjangs=None, statuses=None, limit=20) -> list: ...
def get_dashboard_program_summary(company_id, years=None, pillars=None, programs=None, jenjangs=None, statuses=None) -> list: ...
def get_dashboard_pillar_yearly(company_id, pillars=None, programs=None, jenjangs=None, statuses=None) -> list: ...
```

---

## Testing

- Unit tests for the two new SQL-fragment helpers (`_status_filter_sql`, `_status_case_sql`): empty list → no restriction / `1=1`; one value → single-item `IN`; two values → multi-item `IN` with correct param order.
- Integration tests per dashboard function: seed `payment_beasiswa` rows with a mix of `open` and `complete` status, confirm:
  - `statuses=['complete']` (default) reproduces today's numbers exactly (regression guard — this must not change existing behavior).
  - `statuses=['open']` includes only open-amount totals.
  - `statuses=['open','complete']` includes both.
  - `statuses=[]` (explicit empty / "Kosongkan") includes everything, same as `['open','complete']`.
- `get_dashboard_latest_payments`: confirm a row is excluded when its status isn't in the selected set (new behavior — today this function ignores status entirely).
- Route-level test: query param round-trip (`?statuses=open,complete` parsed correctly; param fully absent still yields `['complete']` default).
- No frontend test framework — verified via the existing structural-check pattern (assert the new `<div class="beasiswa-dash-filter-chip">` / `dash-status-cb` markup is present) plus a manual browser check.

## Out of Scope

- Adding `rejected`/`paid`/other status values to the filter — not present in current `payment_beasiswa` data; can be added later as a one-line change to the checkbox list if/when they start appearing.
- Any change to `budget_beasiswa` queries — that table has no `status` column, budget figures are unaffected by this filter.
- Persisting the user's filter selection (e.g. in localStorage) across page reloads — resets to default (Complete only) every time the dashboard loads, same as the other filters today.
- Any change to the Sahabat ETF module's own dashboard/filters (separate template, out of this spec's scope — this spec covers only the general Beasiswa dashboard at `templates/beasiswa/index.html`).
