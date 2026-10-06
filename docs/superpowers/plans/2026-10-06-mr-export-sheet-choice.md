# Management Report export sheet choice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox syntax.

**Goal:** One "Export semua CC (ZIP)" button (the "tanpa Append" button is removed) and "Export CC ini"; clicking either opens a popover to choose Sheet 1 saja / Sheet 1 + 2 / Semua, then downloads with `sheets=1|12|123`.

**Architecture:** `routes._sheets()` parses the choice; `export_one` / `export_all` build the HO report and Append rows only when requested (the workbook builders already skip sheets passed as `None`). A shared popover in `index.html` intercepts clicks on the two anchors and navigates to their (filter-aware) href plus `sheets=`.

**Spec:** `docs/superpowers/specs/2026-10-06-mr-export-sheet-choice-design.md`

## Global Constraints
- Do NOT run git add/commit/stash/checkout for code files (the tree has the user's uncommitted work); edit with Edit/Write only; never touch port 8081; keep each file's line endings (templates/routes/tests here are LF).
- Missing/invalid `sheets` = all sheets (old behaviour). Legacy `append=0` on export-all = `12` when `sheets` is absent.
- ZIP file name: `Management Report <date>.zip`, `... sheet 1.zip`, `... sheet 1-2.zip`. Single CC file stays `<CC>.xlsx`.
- localStorage access wrapped in try/catch; the page must work without it.
- Run tests from `C:\Financehub\app`.

## Task 1: Sheet choice (backend + popover)

**Files:** modify `app/modules/management_report/routes.py`, `app/templates/management_report/index.html`; tests `app/tests/test_mr_exports.py`.

- [ ] **Step 1: Tests first** in `tests/test_mr_exports.py`: replace `test_export_all_without_append_sheet` and the `mr-export-all-lite` assertions in `test_index_has_a_second_export_all_button_without_append` (and any test using `append=0`/`tanpa Append` except the one that proves legacy `append=0`), using the `seeded` fixture (CC TFKHAR/POSKHU have data, company 2):
  - single CC `GET /management-report/export?cc=TFKHAR&sheets=1` -> sheetnames `["BGT Report per CC"]`; `sheets=12` -> `["BGT Report per CC", "BGT HO Report per CC"]`; `sheets=123` and no `sheets` and `sheets=bogus` -> all three names incl. `"Append"`; file name `TFKHAR.xlsx` in all cases.
  - ZIP `GET /management-report/export-all?mm=3&sheets=1` -> every workbook has only sheet 1 and `Content-Disposition` contains `sheet 1.zip` but not `sheet 1-2`; `sheets=12` -> two sheets and `sheet 1-2.zip`; no `sheets` -> three sheets and no `sheet ` suffix; legacy `append=0` -> two sheets and `sheet 1-2.zip`; `sheets=1&append=0` -> `sheets` wins (one sheet).
  - the page `GET /management-report/` has `id="mr-export-all"` once, no `mr-export-all-lite` and no `tanpa Append`, an element `id="mr-export-pop"` with three radios `value="1"`, `value="12"`, `value="123"` (the last `checked`) and buttons `id="mr-export-go"` / `id="mr-export-cancel"`.
  Run them and see them fail.
- [ ] **Step 2: Backend** in `routes.py`. Add above `export_one`:

```python
def _sheets() -> str:
    """Sheets to export: '1', '12' or '123' (default; the legacy append=0 means '12')."""
    value = request.args.get("sheets")
    if value in ("1", "12", "123"):
        return value
    return "12" if request.args.get("append") == "0" else "123"
```
  In `export_one`: `sheets = _sheets()`, `ho = ho_report.build_ho_report(...) if "2" in sheets else None`, `append_rows = service.query_append(...)["rows"] if "3" in sheets else None`. In `export_all`: replace `with_append` by `sheets = _sheets()`; compute `ho_by_cc[cc]` only `if "2" in sheets` and `append_by_cc[cc]` only `if "3" in sheets`; file name suffix `{"1": " sheet 1", "12": " sheet 1-2", "123": ""}[sheets]`. Keep every other behaviour (404 gates, filters).
- [ ] **Step 3: Template/JS** in `index.html`:
  - Remove the `mr-export-all-lite` anchor, its `const` (`exportAllLite`) and the `exportAllLite.href = ...` line in `refresh()`.
  - Make `.mr-actions` `position:relative` and add the popover as the last child of `.mr-actions`:

```html
<div id="mr-export-pop" class="budget-card mr-export-pop" hidden role="dialog" aria-label="Pilih sheet untuk diexport">
  <div class="mr-export-title">Sheet yang diunduh</div>
  <label><input type="radio" name="mr-export-sheets" value="1"> Sheet 1 saja (BGT Report per CC)</label>
  <label><input type="radio" name="mr-export-sheets" value="12"> Sheet 1 + 2 (+ BGT HO Report per CC)</label>
  <label><input type="radio" name="mr-export-sheets" value="123" checked> Semua (Sheet 1 + 2 + 3 Append)</label>
  <div class="mr-export-actions">
    <button type="button" class="budget-btn" id="mr-export-go">Download</button>
    <button type="button" class="budget-btn" id="mr-export-cancel">Batal</button>
  </div>
</div>
```
  - CSS: `.mr-export-pop { position:absolute; top:100%; right:0; z-index:30; min-width:300px; padding:.75rem; margin-top:.4rem; display:flex; flex-direction:column; gap:.4rem; }`, `.mr-export-pop[hidden] { display:none !important; }`, `.mr-export-pop label { display:flex; gap:.5rem; align-items:center; cursor:pointer; }`, `.mr-export-pop input[type=radio] { width:auto !important; flex:none; margin:0; }`, `.mr-export-title { font-weight:700; }`, `.mr-export-actions { display:flex; gap:.5rem; justify-content:flex-end; margin-top:.25rem; }`.
  - JS inside the filters IIFE (after the `exportOne`/`exportAll` constants):

```js
  /* Export buttons ask which sheets to download; the anchors' hrefs (refreshed with the filters) get `sheets=`. */
  const pop = document.getElementById('mr-export-pop'), popGo = document.getElementById('mr-export-go'),
        popCancel = document.getElementById('mr-export-cancel');
  const SHEETS_KEY = 'mrExportSheets';
  let popFor = null;
  function closePop() { pop.hidden = true; popFor = null; }
  function openPop(a) {
    popFor = a;
    try {
      const saved = localStorage.getItem(SHEETS_KEY), r = saved && pop.querySelector('input[value="' + saved + '"]');
      if (r) r.checked = true;
    } catch (e) { /* no storage: keep the default */ }
    pop.hidden = false;
  }
  [exportOne, exportAll].forEach(a => a.addEventListener('click', e => {
    e.preventDefault();
    if (!pop.hidden && popFor === a) closePop(); else openPop(a);
  }));
  popGo.addEventListener('click', () => {
    const v = pop.querySelector('input[name="mr-export-sheets"]:checked').value, href = popFor.href;
    try { localStorage.setItem(SHEETS_KEY, v); } catch (e) { /* ignore */ }
    closePop();
    location.href = href + (href.includes('?') ? '&' : '?') + 'sheets=' + v;
  });
  popCancel.addEventListener('click', closePop);
  document.addEventListener('click', e => {
    if (!pop.hidden && !pop.contains(e.target) && !exportOne.contains(e.target) && !exportAll.contains(e.target)) closePop();
  });
  document.addEventListener('keydown', e => { if (e.key === 'Escape') closePop(); });
```
- [ ] **Step 4: Verify**: `python -m pytest tests/test_mr_exports.py tests/test_mr_routes.py -q` all pass; extract the inline `<script>` (replace Jinja `{{ ... }}` with a placeholder) and run `node --check`; run `python -m pytest tests/test_mr_bgt_report.py tests/test_mr_bgt_exports.py tests/test_mr_ho_report.py tests/test_mr_report.py tests/test_mr_service.py tests/test_dashboard.py -q`.
- [ ] **Step 5: Report** to `C:\Financehub\.superpowers\sdd\task-6-report.md` (no commit).
