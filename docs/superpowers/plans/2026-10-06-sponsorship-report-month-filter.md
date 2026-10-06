# Sponsorship Report: Month Filter - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Bulan (month, from Tgl Form) tick filter to Sponsorship > Report, rename "Refresh" to "Terapkan Filter", keep the applied filter across the four tabs (Include / BIB Include / Exclude / All), and make Export Excel follow the applied filter.

**Architecture:** One new filter key `bulan` in the existing `_apply_filters` (SQL `strftime('%m', tanggal_form_sponsor)`), carried through `get_sponsorship_report`, the two report routes and `export_report_excel` as an optional parameter; the page JS keeps `tahun` and `bulan` in its applied-filter state and builds one query string for both the table and the export.

**Tech Stack:** Flask, SQLite, openpyxl, vanilla JS (`static/js/sponsorship.js`), pytest.

Spec: `docs/superpowers/specs/2026-10-06-sponsorship-report-month-filter-design.md`

## Global Constraints

- Work in `C:\Financehub\app`; run pytest from there. Paths are relative to it unless they start with `docs/`.
- **No git operations** (`add`, `commit`, `stash`, `checkout`, ...) in `C:\Financehub`: the tree holds the user's uncommitted work. Use the Edit tool for existing files, the Write tool for new files, and never Python/shell scripts that rewrite files. Read each region before editing it.
- Only the Sponsorship Report page changes. Dashboard, MR, Data, Outstanding and Input stay as they are.
- Month = the `tanggal_form_sponsor` column (same as the year filter). Values are two-digit strings `'01'..'12'`; `1` and `01` are the same month; anything else is ignored; no month = all months. Tahun and Bulan combine with AND.
- New parameters are optional: existing calls `get_sponsorship_report(SMT, "2026", "all")` and `export_report_excel(SMT, ["2026"], "all")` must keep working and behave exactly as before.
- The first title cell `B1` of the exported workbook stays `RANGKUMAN SPONSORSHIP - in Rp Full Amount` (existing tests assert it); only the section header line that already carries the year gets the months: `RANGKUMAN SPONSORSHIP 2026 (Jan, Feb) - in Rp Full Amount` (no parentheses when no month is selected).
- Known unrelated failure in the existing suite: `tests/test_sponsorship_routes.py::test_input_page_has_cat1_search_and_lembaga_datalist`. Run the Sponsorship test files with `--deselect` for it.
- Sponsorship tests use the `app`/`client` fixtures of `tests/conftest.py`; the Report is SMT-only (`company_id` 1).

## File Structure

| File | Responsibility |
|---|---|
| `modules/sponsorship/service.py` | (modify) month helpers, `bulan` filter, `get_sponsorship_report(..., bulan=None)` |
| `modules/sponsorship/routes.py` | (modify) `_parse_report_params` returns bulan; report-data / export / page pass it |
| `modules/sponsorship/exports.py` | (modify) `export_report_excel(..., bulan=None)` title |
| `templates/sponsorship/report.html` | (modify) Bulan dropdown, button label |
| `static/js/sponsorship.js` | (modify) applied-filter state, params builder, export from state |
| `tests/test_sponsorship_report_service.py`, `test_sponsorship_report_export.py`, `test_sponsorship_routes.py` | (modify) append tests |

---

### Task 1: Service - month filter

**Files:**
- Modify: `modules/sponsorship/service.py`
- Test: `tests/test_sponsorship_report_service.py` (append)

**Interfaces:**
- Produces:
  - `service.MONTH_SHORT` (`["Jan","Feb","Mar","Apr","Mei","Jun","Jul","Agu","Sep","Okt","Nov","Des"]`), `service.MONTH_CHOICES` (`[("01","Januari"), ..., ("12","Desember")]`)
  - `service.normalise_bulan(values) -> list[str]` (sorted, de-duplicated two-digit strings; accepts a list, a single str/int, or None; invalid values dropped)
  - `service.month_label(bulan) -> str` (e.g. `["03","01"]` -> `"Jan, Mar"`; none -> `""`)
  - `_apply_filters(..., filters)` understands `filters["bulan"]`
  - `get_sponsorship_report(company_id, tahun, cat4_mode, bulan=None)`; its result gains `"bulan": [..]` and `"bulan_label": ".."`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_sponsorship_report_service.py` (the file already imports `seed_perusahaan, create_transaksi, update_transaksi, get_sponsorship_report` and defines `SMT`, `_seed()`, `_payload(**overrides)`; add `normalise_bulan, month_label` to that import line):

```python
def _rows(data):
    return sorted(r["lembaga_perorangan"] for s in data["sections"] for r in s["rows"])


def _seed_months():
    _seed()
    for lem, tgl, cat4 in (("Jan Org", "2026-01-15", "Include"), ("Feb Org", "2026-02-10", "Include"),
                           ("Mar Org", "2026-03-05", "Exclude"), ("Jan Excl", "2026-01-20", "Exclude"),
                           ("Jan 2025 Org", "2025-01-20", "Include")):
        create_transaksi(SMT, _payload(lembaga_perorangan=lem, tanggal_form_sponsor=tgl, cat4=cat4))


def test_normalise_bulan_and_month_label():
    assert normalise_bulan(["1", "01", 2, "12", "13", "0", "x", "", None]) == ["01", "02", "12"]
    assert normalise_bulan(None) == [] and normalise_bulan("3") == ["03"] and normalise_bulan(7) == ["07"]
    assert month_label(["03", "01"]) == "Jan, Mar" and month_label([]) == "" and month_label(None) == ""
    assert month_label(["05", "08", "12"]) == "Mei, Agu, Des"


def test_report_month_filter_uses_tgl_form():
    _seed_months()
    data = get_sponsorship_report(SMT, ["2026"], "all", ["01"])
    assert _rows(data) == ["Jan Excl", "Jan Org"]
    assert data["bulan"] == ["01"] and data["bulan_label"] == "Jan"
    assert _rows(get_sponsorship_report(SMT, ["2026"], "all", ["01", "02"])) == ["Feb Org", "Jan Excl", "Jan Org"]
    assert _rows(get_sponsorship_report(SMT, ["2025", "2026"], "all", ["01"])) == \
        ["Jan 2025 Org", "Jan Excl", "Jan Org"]                       # years and months combine with AND


def test_report_without_month_is_unchanged():
    _seed_months()
    data = get_sponsorship_report(SMT, ["2026"], "all")
    assert _rows(data) == ["Feb Org", "Jan Excl", "Jan Org", "Mar Org"]
    assert data["bulan"] == [] and data["bulan_label"] == ""
    assert _rows(get_sponsorship_report(SMT, ["2026"], "all", None)) == _rows(data)


def test_report_month_filter_applies_in_every_cat4_mode():
    _seed_months()
    month = ["01"]
    assert _rows(get_sponsorship_report(SMT, ["2026"], "include", month)) == ["Jan Org"]
    assert _rows(get_sponsorship_report(SMT, ["2026"], "exclude", month)) == ["Jan Excl"]
    assert _rows(get_sponsorship_report(SMT, ["2026"], "all", month)) == ["Jan Excl", "Jan Org"]
    assert _rows(get_sponsorship_report(SMT, ["2026"], "bib_include", month)) == ["Jan Org"]


def test_report_invalid_months_are_ignored():
    _seed_months()
    data = get_sponsorship_report(SMT, ["2026"], "all", ["13", "0", "abc", ""])
    assert data["bulan"] == [] and len(_rows(data)) == 4


def test_report_month_without_matching_rows_is_empty():
    _seed_months()
    data = get_sponsorship_report(SMT, ["2026"], "all", ["12"])
    assert data["sections"] == [] and data["bulan_label"] == "Des"
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_sponsorship_report_service.py -q`
Expected: collection ERROR (`cannot import name 'normalise_bulan'`).

- [ ] **Step 3: Implement**

In `modules/sponsorship/service.py`:

(a) Directly above `def _apply_filters(` add:
```python
MONTH_SHORT = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
MONTH_LONG = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus",
              "September", "Oktober", "November", "Desember"]
MONTH_CHOICES = [(f"{i + 1:02d}", name) for i, name in enumerate(MONTH_LONG)]


def normalise_bulan(values) -> list:
    """Two-digit month strings '01'..'12', sorted and de-duplicated; invalid values are dropped."""
    if values is None:
        return []
    if isinstance(values, (str, int)):
        values = [values]
    out = set()
    for v in values:
        try:
            m = int(str(v).strip())
        except ValueError:
            continue
        if 1 <= m <= 12:
            out.add(f"{m:02d}")
    return sorted(out)


def month_label(bulan) -> str:
    """['03', '01'] -> 'Jan, Mar'; nothing selected -> ''."""
    return ", ".join(MONTH_SHORT[int(m) - 1] for m in normalise_bulan(bulan))


```
(b) In `_apply_filters`, directly before the final `return query, params`, add:
```python
    bulan = normalise_bulan(filters.get("bulan"))
    if bulan:
        placeholders = ",".join(["?"] * len(bulan))
        query += f" AND strftime('%m', tanggal_form_sponsor) IN ({placeholders})"
        params.extend(bulan)
```
(c) Change `def get_sponsorship_report(company_id: int, tahun: list, cat4_mode: str) -> dict:` to `def get_sponsorship_report(company_id: int, tahun: list, cat4_mode: str, bulan=None) -> dict:`; replace the line `    filters = {"tahun": tahun}` (inside that function) with
```python
    bulan = normalise_bulan(bulan)
    filters = {"tahun": tahun}
    if bulan:
        filters["bulan"] = bulan
```
(d) In that function's final `return {...}`, add after `"cat4_mode": cat4_mode,`:
```python
        "bulan": bulan,
        "bulan_label": month_label(bulan),
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/test_sponsorship_report_service.py tests/test_sponsorship_service.py tests/test_sponsorship_dashboard_service.py tests/test_sponsorship_mr_service.py -q`
Expected: all pass.

---

### Task 2: Routes and Excel export

**Files:**
- Modify: `modules/sponsorship/routes.py`
- Modify: `modules/sponsorship/exports.py`
- Test: `tests/test_sponsorship_report_export.py` (append), `tests/test_sponsorship_routes.py` (append)

**Interfaces:**
- Consumes: `service.normalise_bulan`, `service.month_label`, `service.MONTH_CHOICES`, `get_sponsorship_report(..., bulan)` (Task 1).
- Produces: `_parse_report_params()` returns `(tahun, cat4, bulan)`; `/sponsorship/api/report-data?tahun=..&cat4=..&bulan=..&bulan=..`; `/sponsorship/report/export` with the same params (file name `Sponsorship_Report_{cat4}_{years joined by -}[_{months joined by -}].xlsx`); `export_report_excel(company_id, tahun, cat4_mode, bulan=None)`; the report page receives `months=MONTH_CHOICES`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_sponsorship_report_export.py` (it already imports `io`, `openpyxl`, `seed_perusahaan`, `create_transaksi`, `export_report_excel` and defines `SMT`, `_seed`):

```python
def _tx(lem, tgl, cat4="Include"):
    create_transaksi(SMT, {
        "cat": "Sponsorship", "description": "Sosial", "tanggal_form_sponsor": tgl,
        "cat1": "SMART", "lembaga_perorangan": lem, "amount_request": 1000000, "cat4": cat4,
    })


def _values(xls_bytes):
    ws = openpyxl.load_workbook(io.BytesIO(xls_bytes)).active
    return [cell.value for row in ws.iter_rows() for cell in row]


```

```python
def test_export_follows_the_month_filter_and_puts_it_in_the_title(app):
    _seed()
    _tx("Jan Org", "2026-01-15"); _tx("Feb Org", "2026-02-10"); _tx("Mar Org", "2026-03-05")
    values = _values(export_report_excel(SMT, ["2026"], "all", ["01", "02"]))
    assert "RANGKUMAN SPONSORSHIP 2026 (Jan, Feb) - in Rp Full Amount" in values
    assert "Jan Org" in values and "Feb Org" in values and "Mar Org" not in values
    assert "RANGKUMAN SPONSORSHIP - in Rp Full Amount" in values          # the fixed first title cell


def test_export_without_months_keeps_the_title_and_all_rows(app):
    _seed()
    _tx("Jan Org", "2026-01-15"); _tx("Mar Org", "2026-03-05")
    values = _values(export_report_excel(SMT, ["2026"], "all"))
    assert "RANGKUMAN SPONSORSHIP 2026 - in Rp Full Amount" in values
    assert "Jan Org" in values and "Mar Org" in values


def test_export_follows_cat4_mode_together_with_months(app):
    _seed()
    _tx("Jan Incl", "2026-01-15", "Include"); _tx("Jan Excl", "2026-01-16", "Exclude")
    include = _values(export_report_excel(SMT, ["2026"], "include", ["01"]))
    exclude = _values(export_report_excel(SMT, ["2026"], "exclude", ["01"]))
    assert "Jan Incl" in include and "Jan Excl" not in include
    assert "Jan Excl" in exclude and "Jan Incl" not in exclude


def test_export_with_a_month_that_has_no_data_still_generates_a_file(app):
    _seed()
    _tx("Jan Org", "2026-01-15")
    values = _values(export_report_excel(SMT, ["2026"], "all", ["12"]))
    assert "RANGKUMAN SPONSORSHIP 2026 (Des) - in Rp Full Amount" in values
    assert "Jan Org" not in values
```
Append to `tests/test_sponsorship_routes.py` (it already defines `login`, `_select_smt`, `_select_etf`, `_seed`; add `import io` and `import openpyxl` at the top of the file if missing):

```python
def _create(client, lem, tgl, cat4=None):
    payload = {"cat": "Sponsorship", "description": "Sosial", "tanggal_form_sponsor": tgl,
               "cat1": "SMART", "lembaga_perorangan": lem, "amount_request": 1000}
    if cat4:
        payload["cat4"] = cat4
    client.post("/sponsorship/input/create", json=payload)


def _seed_three_months(client):
    login(client)
    _select_smt(client)
    _seed()
    _create(client, "Jan Org", "2026-01-15", "Include")
    _create(client, "Feb Org", "2026-02-10", "Include")
    _create(client, "Mar Org", "2026-03-05", "Exclude")


def _lembaga(data):
    return sorted(r["lembaga_perorangan"] for s in data["sections"] for r in s["rows"])


def test_api_report_data_filters_by_bulan(client):
    _seed_three_months(client)
    data = client.get("/sponsorship/api/report-data?tahun=2026&cat4=all&bulan=01&bulan=02").get_json()
    assert _lembaga(data) == ["Feb Org", "Jan Org"]
    assert data["bulan"] == ["01", "02"] and data["bulan_label"] == "Jan, Feb"
    data = client.get("/sponsorship/api/report-data?tahun=2026&cat4=all&bulan=1").get_json()
    assert data["bulan"] == ["01"] and _lembaga(data) == ["Jan Org"]        # '1' means January


def test_api_report_data_ignores_invalid_bulan(client):
    _seed_three_months(client)
    data = client.get("/sponsorship/api/report-data?tahun=2026&cat4=all&bulan=13&bulan=abc&bulan=0&bulan=").get_json()
    assert data["bulan"] == [] and _lembaga(data) == ["Feb Org", "Jan Org", "Mar Org"]


def test_api_report_data_applies_bulan_in_every_tab_mode(client):
    _seed_three_months(client)
    get = lambda cat4: _lembaga(client.get(f"/sponsorship/api/report-data?tahun=2026&cat4={cat4}&bulan=01&bulan=03").get_json())
    assert get("include") == ["Jan Org"]
    assert get("exclude") == ["Mar Org"]
    assert get("all") == ["Jan Org", "Mar Org"]
    assert get("bib_include") == ["Jan Org"]


def test_export_report_follows_the_applied_filter_and_names_the_file(client):
    _seed_three_months(client)
    resp = client.get("/sponsorship/report/export?tahun=2026&cat4=include&bulan=01&bulan=02")
    assert resp.status_code == 200
    assert "Sponsorship_Report_include_2026_01-02.xlsx" in resp.headers.get("Content-Disposition", "")
    ws = openpyxl.load_workbook(io.BytesIO(resp.data)).active
    values = [c.value for row in ws.iter_rows() for c in row]
    assert "Jan Org" in values and "Feb Org" in values and "Mar Org" not in values
    assert "RANGKUMAN SPONSORSHIP 2026 (Jan, Feb) - in Rp Full Amount" in values


def test_export_report_filename_has_no_month_part_without_bulan(client):
    _seed_three_months(client)
    resp = client.get("/sponsorship/report/export?tahun=2026&cat4=all")
    assert "Sponsorship_Report_all_2026.xlsx" in resp.headers.get("Content-Disposition", "")
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_sponsorship_report_export.py tests/test_sponsorship_routes.py -q --deselect tests/test_sponsorship_routes.py::test_input_page_has_cat1_search_and_lembaga_datalist`
Expected: the new tests FAIL (extra positional argument / `bulan` ignored); all others pass.

- [ ] **Step 3: Routes**

In `modules/sponsorship/routes.py`:

(a) Add `normalise_bulan, MONTH_CHOICES` to the existing `from modules.sponsorship.service import (...)` list (keep the list's style).
(b) Replace `_parse_report_params` with:
```python
def _parse_report_params():
    tahun_vals = request.args.getlist("tahun")
    tahun = [y for y in tahun_vals if y.strip()]
    if not tahun:
        years = get_available_years(_cid())
        tahun = [years[0]] if years else [str(datetime.now().year)]
    cat4 = (request.args.get("cat4") or "all").lower()
    if cat4 not in ("include", "exclude", "all", "bib_include"):
        cat4 = "all"
    bulan = normalise_bulan(request.args.getlist("bulan"))
    return tahun, cat4, bulan
```
(c) `api_report_data`: replace its first two lines
```python
    tahun, cat4 = _parse_report_params()
    data = get_sponsorship_report(_cid(), tahun, cat4)
```
with
```python
    tahun, cat4, bulan = _parse_report_params()
    data = get_sponsorship_report(_cid(), tahun, cat4, bulan)
```
(d) `export_report_route`: replace
```python
    tahun, cat4 = _parse_report_params()
    xls_bytes = export_report_excel(_cid(), tahun, cat4)
    filename = f"Sponsorship_Report_{cat4}_{'-'.join(tahun)}.xlsx"
```
with
```python
    tahun, cat4, bulan = _parse_report_params()
    xls_bytes = export_report_excel(_cid(), tahun, cat4, bulan)
    month_part = f"_{'-'.join(bulan)}" if bulan else ""
    filename = f"Sponsorship_Report_{cat4}_{'-'.join(tahun)}{month_part}.xlsx"
```
(e) In `report_page`, replace `wrong_company=_wrong_company(), years=years, **_ctx())` (the line inside `report_page` only) with `wrong_company=_wrong_company(), years=years, months=MONTH_CHOICES, **_ctx())`.
(f) `_parse_report_params` is also used elsewhere? Run `grep -n "_parse_report_params" modules/sponsorship/routes.py`: only the two routes above call it; if another caller exists, adapt it to the 3-tuple.

- [ ] **Step 4: Export**

In `modules/sponsorship/exports.py`:
(a) Change `def export_report_excel(company_id: int, tahun: str, cat4_mode: str) -> bytes:` to `def export_report_excel(company_id: int, tahun: str, cat4_mode: str, bulan=None) -> bytes:` and `data = get_sponsorship_report(company_id, tahun, cat4_mode)` to `data = get_sponsorship_report(company_id, tahun, cat4_mode, bulan)`.
(b) Replace the line `        ws.append(["", f"RANGKUMAN SPONSORSHIP {data['tahun']} - in Rp Full Amount"])` with
```python
        period = f"{data['tahun']} ({data['bulan_label']})" if data["bulan_label"] else data["tahun"]
        ws.append(["", f"RANGKUMAN SPONSORSHIP {period} - in Rp Full Amount"])
```
(`data["bulan_label"]` is produced by `get_sponsorship_report`; no new import is needed.)

- [ ] **Step 5: Run to verify pass**

Run: `python -m pytest tests/test_sponsorship_report_export.py tests/test_sponsorship_report_service.py tests/test_sponsorship_routes.py tests/test_sponsorship_mr_export.py -q --deselect tests/test_sponsorship_routes.py::test_input_page_has_cat1_search_and_lembaga_datalist`
Expected: all pass.

---

### Task 3: Page - Bulan dropdown, button label, applied-filter JS

**Files:**
- Modify: `templates/sponsorship/report.html`
- Modify: `static/js/sponsorship.js`
- Test: `tests/test_sponsorship_routes.py` (append)

**Interfaces:**
- Consumes: `months` template variable (Task 2), `/sponsorship/api/report-data` and `/sponsorship/report/export` with `bulan` (Task 2).
- Produces: dropdown `#sp-report-bulan-container` with `#sp-report-bulan` (12 checkboxes `name="bulan"` values `01..12`); button `#sp-report-refresh` labelled `Terapkan Filter`; JS state `sponsorshipReportState = {cat4, tahun, bulan}`; helper `_getReportBulan()`, `_sponsorshipReportParams()`; Export builds its URL from the applied state.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_sponsorship_routes.py`:

```python
def test_report_page_has_the_bulan_dropdown_and_terapkan_filter_label(client):
    login(client)
    _select_smt(client)
    html = client.get("/sponsorship/report").data.decode()
    assert 'id="sp-report-bulan-container"' in html and 'id="sp-report-bulan"' in html
    assert html.count('name="bulan"') == 12
    assert 'name="bulan" value="01"' in html and 'name="bulan" value="12"' in html
    assert "Januari" in html and "Desember" in html
    assert ">Terapkan Filter<" in html and ">Refresh<" not in html
    assert 'id="sp-report-refresh"' in html                      # id unchanged
    assert 'name="bulan" value="01" checked' not in html          # no month ticked by default


def test_report_js_exports_from_the_applied_filter_state(client):
    login(client)
    _select_smt(client)
    js = client.get("/static/js/sponsorship.js").data.decode()
    assert "bulan: []" in js and "_getReportBulan" in js and "_sponsorshipReportParams" in js
    export_handler = js.split('getElementById("sp-report-export")')[1][:900]
    assert "_sponsorshipReportParams()" in export_handler          # export uses the applied state
    assert 'params.append("tahun"' not in export_handler           # no hand-rolled query from raw ticks
```
(The second test is a light structural guard; the real check is the browser run in Task 4.)

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_sponsorship_routes.py -q -k "bulan_dropdown or applied_filter_state"`
Expected: both FAIL.

- [ ] **Step 3: Template**

In `templates/sponsorship/report.html`:
(a) Directly after the closing `</div>` of the Tahun block (`<div class="budget-dropdown-check" id="sp-report-tahun-container"> ... </div>`), add:
```html
    <div class="budget-dropdown-check" id="sp-report-bulan-container">
      <button type="button" class="budget-dropdown-btn" onclick="this.nextElementSibling.classList.toggle('show')">
        Bulan <span style="font-size: 0.7em;">▼</span>
      </button>
      <div class="budget-dropdown-content" id="sp-report-bulan">
        {% for num, name in months %}
        <label><input type="checkbox" name="bulan" value="{{ num }}"> {{ name }}</label>
        {% endfor %}
      </div>
    </div>
```
(b) Replace `<button type="button" class="budget-btn" id="sp-report-refresh">Refresh</button>` with `<button type="button" class="budget-btn" id="sp-report-refresh">Terapkan Filter</button>`.

- [ ] **Step 4: JavaScript** (`static/js/sponsorship.js`; read the Report-tab section first)

(a) Replace `let sponsorshipReportState = { cat4: "include", tahun: "" };` with `let sponsorshipReportState = { cat4: "include", tahun: "", bulan: [] };`.
(b) Directly above `  function sponsorshipLoadReport() {` add:
```js
  function _getReportBulan() {
    const cbs = document.querySelectorAll("#sp-report-bulan input[name='bulan']:checked");
    return Array.from(cbs).map(cb => cb.value);
  }

  // One query string for the table and for the export, built from the APPLIED filter state
  // (never from ticks that have not been applied with "Terapkan Filter").
  function _sponsorshipReportParams() {
    const params = new URLSearchParams();
    params.append("cat4", sponsorshipReportState.cat4);
    const selectedTahun = sponsorshipReportState.tahun || [];
    (Array.isArray(selectedTahun) ? selectedTahun : [selectedTahun]).forEach(t => params.append("tahun", t));
    (sponsorshipReportState.bulan || []).forEach(b => params.append("bulan", b));
    return params;
  }

```
(c) In `sponsorshipLoadReport`, replace
```js
    const params = new URLSearchParams();
    params.append("cat4", sponsorshipReportState.cat4);
    const selectedTahun = sponsorshipReportState.tahun || [];
    const tahunArr = Array.isArray(selectedTahun) ? selectedTahun : [selectedTahun];
    tahunArr.forEach(t => params.append("tahun", t));

    apiFetch("/sponsorship/api/report-data?" + params.toString())
```
with
```js
    const params = _sponsorshipReportParams();

    apiFetch("/sponsorship/api/report-data?" + params.toString())
```
(d) In `_sponsorshipRenderReportTable`, replace
```js
    container.innerHTML = '<div class="budget-card"><p>Belum ada data sponsorship untuk tahun ' +
      _sponsorshipEsc(data.tahun) + '.</p></div>';
```
with
```js
    container.innerHTML = '<div class="budget-card"><p>Belum ada data sponsorship untuk tahun ' +
      _sponsorshipEsc(data.tahun) + (data.bulan_label ? ', bulan ' + _sponsorshipEsc(data.bulan_label) : '') +
      '.</p></div>';
```
(e) In the refresh handler, replace
```js
        sponsorshipReportState.tahun = _getReportTahun();
        sponsorshipLoadReport();
```
with
```js
        sponsorshipReportState.tahun = _getReportTahun();
        sponsorshipReportState.bulan = _getReportBulan();
        sponsorshipLoadReport();
```
(f) In the export handler, replace the whole body of the click listener
```js
        sponsorshipReportState.tahun = _getReportTahun();
        const params = new URLSearchParams();
        params.append("cat4", sponsorshipReportState.cat4);
        const selectedTahun = sponsorshipReportState.tahun || [];
        const tahunArr = Array.isArray(selectedTahun) ? selectedTahun : [selectedTahun];
        tahunArr.forEach(t => params.append("tahun", t));
        window.location.href = "/sponsorship/report/export?" + params.toString();
```
with
```js
        // Same filter as the table on screen: the applied state, not the raw ticks.
        if (!sponsorshipReportState.tahun || sponsorshipReportState.tahun.length === 0) {
          sponsorshipReportState.tahun = _getReportTahun();   // before the first load only
        }
        window.location.href = "/sponsorship/report/export?" + _sponsorshipReportParams().toString();
```

- [ ] **Step 5: Run to verify pass**

Run: `python -m pytest tests/test_sponsorship_routes.py tests/test_sponsorship_report_export.py tests/test_sponsorship_report_service.py -q --deselect tests/test_sponsorship_routes.py::test_input_page_has_cat1_search_and_lembaga_datalist`
Expected: all pass.

---

### Task 4: Verification (controller)

- [ ] **Step 1: Browser check** Throwaway instance (port 8090, temp database, company SMT) seeded with sample transactions over several months/years and both cat4 values (via `create_transaksi`): open `/sponsorship/report`; the Bulan dropdown lists Januari-Desember; tick Tahun + two months and press **Terapkan Filter**: the table shows only those months; switch between Include / BIB Include / Exclude / All: the applied filter holds on every tab; tick another month WITHOUT applying, then click Export: the downloaded file equals the table that is on screen (not the pending ticks), file name and title carry the months; apply again and the table changes. No console errors.
- [ ] **Step 2: Regression** `python -m pytest tests/test_sponsorship_*.py -q --deselect tests/test_sponsorship_routes.py::test_input_page_has_cat1_search_and_lembaga_datalist` (all pass) and the Management Report test files still pass.
- [ ] **Step 3: Report to the user** with test results, browser findings, and a reminder that the server must be restarted (templates and static files are cached) and that nothing was committed.
