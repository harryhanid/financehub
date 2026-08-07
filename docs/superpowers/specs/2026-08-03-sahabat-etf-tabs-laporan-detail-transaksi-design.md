# Design: Sahabat ETF — Dashboard/Laporan/Detail Transaksi Tabs

**Date:** 2026-08-03
**Module:** Finance Hub — Eka Tjipta Foundation / Beasiswa / Sahabat ETF
**Status:** Approved

---

## Summary

The Sahabat ETF panel (`templates/sahabat_etf/_panel.html`, embedded as the "Sahabat ETF" tab inside Beasiswa, and also reachable standalone at `/beasiswa/sahabat/`) is currently one long scrolling page with 3 accordions (Ringkasan & Alert, Grafik, Detail Tabel per-anggota). It's restructured into 3 top-level tabs inside the panel:

1. **Dashboard** — the existing content, unchanged, just wrapped in a tab panel.
2. **Laporan** — new. An on-screen HTML rendering of the "REPORT PER [tanggal]" report (the same data already used by the existing Excel export), plus the year selector and the "Export Laporan (Excel)" button (moved here from Dashboard's filter bar).
3. **Detail Transaksi** — new. A full on-screen table of every budget + payment transaction for Sahabat ETF (data already available via `get_all_transactions()`, today only reachable as a CSV download), plus the "Export Detail Transaksi (CSV)" button (moved here from Dashboard's toolbar).

Everything reuses existing, already-shipped data functions (`build_report_data()`, `get_all_transactions()`) — this is a UI/routing restructure, not new business logic.

## Decisions

| Question | Decision |
|---|---|
| Laporan tab content | Full on-screen HTML rendering of the report (sections, subtotals, recap, grand total, pillar breakdown) — not just a download-only control panel |
| Dashboard tab content | The 3 existing accordions, unchanged, wrapped as-is — nothing moved out except the two controls below |
| Detail Transaksi filters/columns | Reuse the exact same Tahun/Pillar filter semantics and the exact same column set as the existing CSV export (Sumber, Kode Siswa, Nama, Tanggal, Kategori 1, Kategori 2, Amount, Status) |
| "Tahun Report" selector + "Export Laporan (Excel)" button | Move from Dashboard's Ringkasan filter bar into the new Laporan tab (decluttering Dashboard, and giving the report its own home) |
| "Export Detail Transaksi (CSV)" button | Move from Dashboard's toolbar into the new Detail Transaksi tab |
| Tab-switching mechanism | A new, separately-classed sub-tab widget (`.setf-subtabs` / `.setf-subtab-btn` / `.setf-subtab-panel`) with its own small JS function — **not** a reuse of the site-wide `initTabs()` (`app.js:445`), which queries `.tabs .tab-btn` / `.tab-panel` globally (not scoped to a container) and is already active for Beasiswa's own outer tab bar (which contains the "Sahabat ETF" tab this panel lives inside). Reusing the same classes would double-handle clicks and fight over which panel is active. New classes visually mirror `.tabs`/`.tab-btn` (`style.css:779-802`) via a separate rule set, so it looks identical without sharing a selector. |
| Report HTML styling | Uses this dashboard's existing CSS tokens/classes (`.setf-*`, `.beasiswa-dash-*` conventions already in this file), not a visual copy of the Excel's navy/green cell colors — consistent with the rest of the page, not a pixel clone of the spreadsheet |
| Data/business logic changes | None — `build_report_data()`, `build_report_workbook()`, and `get_all_transactions()` are all reused exactly as they are today; only new thin JSON endpoints and new client-side rendering are added |

---

## Architecture

### File changes

- **Modify:** `app/templates/sahabat_etf/_panel.html` — add a `.setf-subtabs` button bar (Dashboard / Laporan / Detail Transaksi) at the top; wrap the 3 existing accordions in `<div class="setf-subtab-panel active" id="setf-subtab-dashboard">`; add two new empty subtab-panel containers (`setf-subtab-laporan`, `setf-subtab-detail`) to be filled by JS on first activation; move the "Tahun Report" `<select>` + "Export Laporan (Excel)" `<a>` into the Laporan panel's markup; move "Export Detail Transaksi (CSV)" `<a>` into the Detail Transaksi panel's markup.
- **Modify:** `app/static/js/sahabat_etf.js` — add `initSetfSubtabs()` (click-wiring, called from `initSahabatEtf()`); add `setfLoadLaporan(year)` (fetch `/api/report`, render HTML) and `setfRenderLaporan(data)`; add `setfLoadDetailTransaksi(filters)` (fetch `/api/detail`, render HTML) and `setfRenderDetailTransaksi(rows)`.
- **Modify:** `app/static/css/budget.css` (or a Sahabat-ETF-scoped stylesheet, following whatever this file's existing convention is for `.setf-*` classes) — add `.setf-subtabs` / `.setf-subtab-btn` / `.setf-subtab-btn.active` / `.setf-subtab-panel` (hidden unless `.active`) rules, visually matching `.tabs`/`.tab-btn` from `style.css:779-802`; add table/section styling for the Laporan tab's report rendering.
- **Modify:** `app/modules/sahabat_etf/routes.py` — add `GET /api/report?year=<int>` (calls `build_report_data(_cid(), report_year)`, returns it as JSON, guarded by `etf_company_required` like every other route in this file) and `GET /api/detail` (calls `get_all_transactions(_cid(), years, pillars)` with the same query-param parsing already used by `export_detail`, returns JSON).

No changes to `modules/sahabat_etf/service.py` or `modules/sahabat_etf/report_xlsx.py` — both are consumed exactly as they exist today.

### New JSON endpoints

```python
@bp.route("/api/report")
@jwt_html_required
@etf_company_required
def api_report():
    year_param = request.args.get("year", "")
    if not year_param.strip().lstrip("-").isdigit():
        return jsonify({"ok": False, "pesan": "Parameter year wajib berupa angka."}), 400
    return jsonify({"ok": True, "data": build_report_data(_cid(), int(year_param))})


@bp.route("/api/detail")
@jwt_html_required
@etf_company_required
def api_detail():
    years, pillars = _parse_filters()
    return jsonify({"ok": True, "rows": get_all_transactions(_cid(), years, pillars)})
```

(`_parse_filters()` already exists in this file and is reused unchanged — it's the same helper `export_detail` and the other `/api/*` routes already use.)

### Sub-tab widget shape

```html
<div class="setf-subtabs">
  <button class="setf-subtab-btn active" data-subtab="dashboard">Dashboard</button>
  <button class="setf-subtab-btn" data-subtab="laporan">Laporan</button>
  <button class="setf-subtab-btn" data-subtab="detail">Detail Transaksi</button>
</div>
<div class="setf-subtab-panel active" id="setf-subtab-dashboard">...</div>
<div class="setf-subtab-panel" id="setf-subtab-laporan">...</div>
<div class="setf-subtab-panel" id="setf-subtab-detail">...</div>
```

`initSetfSubtabs()` toggles `.active` on the clicked button and the matching `#setf-subtab-{name}` panel, and lazy-loads that tab's data on first activation (Laporan fetches `/api/report` using the currently-selected year; Detail Transaksi fetches `/api/detail` using the currently-checked Tahun/Pillar filters) — data isn't fetched for a tab the user never opens.

### Laporan tab rendering

`setfRenderLaporan(data)` walks the same JSON shape `build_report_data()` already produces (documented in the original `2026-07-15` Sahabat ETF Excel report spec: `sections` → groups → siswa rows/subtotal → section `recap`, plus top-level `combined_total`/`combined_recap`/`grand_total`/`pillar_breakdown`) and builds one HTML `<table>` per section-equivalent, mirroring `report_xlsx.py`'s row ordering (section header → per-group subtotal + siswa rows → section total → recap → combined total → combined recap → grand total → pillar breakdown with "% to total" rows), using this page's own `.setf-*` table styling rather than the Excel's specific colors. Money values are divided by 1,000,000 for display, matching every other value already shown on this dashboard.

### Detail Transaksi tab rendering

`setfRenderDetailTransaksi(rows)` renders one `<table>` row per transaction, columns in this exact order: Sumber, Kode Siswa, Nama, Tanggal, Kategori 1, Kategori 2, Amount, Status — identical column set/order to the existing `export_detail` CSV. No pagination (this module has ~11-12 active students; existing CSV exports and the current "Detail Tabel" accordion are already unpaginated, so this follows the same established pattern).

---

## Testing

- pytest for both new routes: 200 + correct JSON shape for a valid ETF-company session; 403 for a non-ETF company session (`etf_company_required` guard, same pattern as every existing test for this file's other routes); 400 for `/api/report` with a missing/non-numeric `year`.
- App-boot sanity check.
- Force-render `/beasiswa/sahabat/` (or `/beasiswa/?tab=sahabat`) via Flask test client with a real test-DB login — 200 OK, assert the 3 new `setf-subtab-btn`/`setf-subtab-panel` elements are present with the correct `data-subtab`/`id` values, and that the moved controls (`setf-report-year`, `setf-export-report`, `setf-export-detail`) are now inside the correct new panels rather than the old Ringkasan filter bar.
- Structural check: `initSetfSubtabs` does not reference `.tabs`/`.tab-btn`/`.tab-panel` (the site-wide classes) anywhere, confirming no collision with `initTabs()`.
- Manual browser check if a preview session with non-production data is available: click each tab, confirm the right panel shows and data loads; confirm Export Laporan (Excel) and Export Detail Transaksi (CSV) still download correctly from their new tabs.
- Full Python regression suite run once at the end.

## Out of Scope

- Any change to `build_report_data()`, `build_report_workbook()`, `get_all_transactions()`, or the existing `/export/report` and `/export/detail` download routes — all reused unchanged.
- Any change to the Dashboard tab's existing 3 accordions' internal content, charts, or tables.
- Pagination, search, or sorting on the Detail Transaksi table — not requested, and the current data volume doesn't need it (matches the existing unpaginated CSV/Detail Tabel pattern).
- Refactoring `initTabs()` to be reusable/scoped — a new, separate widget is used instead (see Decisions).
