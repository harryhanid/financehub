# Sponsorship Table Full-Height Fill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Sponsorship's Data and Outstanding table wrappers fill the remaining viewport height exactly, replacing a stale hardcoded `max-height` with the same JS-driven dynamic sizing already proven on Payment Application's `#pa-scroll-wrap`.

**Architecture:** Both pages' table wrapper gets a page-specific `id="sp-table-wrap"`. One new CSS rule (id-scoped, so no other module is affected) overrides the shared `.budget-table-container` class's stale `max-height`. Each template gets its own inline copy of a `sizeWrap()`-style script that measures the wrapper's actual position and sets its height in pixels, recomputing on load/resize and when the filter bar's height changes.

**Tech Stack:** Flask/Jinja2 templates, vanilla JS, CSS. No backend/route changes.

## Global Constraints

- Only these files change: `app/static/css/sponsorship.css`, `app/templates/sponsorship/data.html`, `app/templates/sponsorship/outstanding.html`, `app/tests/test_sponsorship_routes.py`.
- `.budget-table-container`'s own CSS rule in `budget.css` is not modified — the fix is scoped entirely via the new `#sp-table-wrap` id, so no other module using that class (Budget, Beasiswa, Bank) is affected.
- The Data tab's existing floating pagination (`.floating-pagination`, `initServerPagedDynamicSize`) is not modified.
- Payment Application's `#pa-scroll-wrap` and its sizing script are the reference implementation — read, not modified.

---

### Task 1: Fix the Data tab

**Files:**
- Modify: `app/static/css/sponsorship.css` (append at end, currently 152 lines)
- Modify: `app/templates/sponsorship/data.html:60` (add id) and `:226-234` (add script)
- Test: `app/tests/test_sponsorship_routes.py`

**Interfaces:**
- Produces: CSS rule `#sp-table-wrap { max-height: none; }`, consumed by Task 2 (Outstanding reuses the same id and rule, no further CSS changes needed there).

- [ ] **Step 1: Write the test**

Append to `app/tests/test_sponsorship_routes.py`:

```python
def test_data_page_has_full_height_table_wrap_id(client):
    login(client)
    _select_smt(client)
    resp = client.get("/sponsorship/data")
    assert resp.status_code == 200
    assert b'id="sp-table-wrap"' in resp.data
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd C:\Financehub\app && python -m pytest tests/test_sponsorship_routes.py -v -k full_height_table_wrap`
Expected: FAIL — `assert b'id="sp-table-wrap"' in resp.data` fails, since the id doesn't exist in the template yet.

- [ ] **Step 3: Add the CSS override**

Append to `app/static/css/sponsorship.css` (after its current last line, `.sp-form-advanced .sp-form-grid { ... }`):

```css

/* ── Full-height table wrapper — Data/Outstanding tabs ───────────────────── */
/* Overrides .budget-table-container's stale max-height (budget.css) with a
   JS-driven height instead, matching Payment Application's #pa-scroll-wrap
   technique (etf_payment_application/index.html). An id selector already
   outranks the class rule, so no !important is needed. */
#sp-table-wrap { max-height: none; }
```

- [ ] **Step 4: Add the id to the Data tab's table wrapper**

In `app/templates/sponsorship/data.html`, replace:

```html
  <div class="budget-table-container">
  <table class="budget-table">
```

with:

```html
  <div class="budget-table-container" id="sp-table-wrap">
  <table class="budget-table">
```

- [ ] **Step 5: Add the dynamic-height sizing script**

In `app/templates/sponsorship/data.html`, inside `{% block scripts %}`, replace:

```html
<script>
function exportDataExcel() {
  const form = document.getElementById("sp-data-filter-form");
  const params = new URLSearchParams(new FormData(form));
  window.location.href = "/sponsorship/data/export?" + params.toString();
}
</script>
{% endblock %}
```

with:

```html
<script>
function exportDataExcel() {
  const form = document.getElementById("sp-data-filter-form");
  const params = new URLSearchParams(new FormData(form));
  window.location.href = "/sponsorship/data/export?" + params.toString();
}
</script>

<script>
// ─── Size sp-table-wrap to fill the entire remaining viewport ────────────
// Same technique as #pa-scroll-wrap in etf_payment_application/index.html —
// measure the wrapper's actual position instead of guessing a fixed height,
// so it can't go stale when the layout around it changes.
(function() {
  function sizeWrap() {
    const wrap = document.getElementById('sp-table-wrap');
    if (!wrap) return;
    requestAnimationFrame(() => {
      wrap.style.height = (window.innerHeight - wrap.getBoundingClientRect().top) + 'px';
    });
  }
  window.addEventListener('load', sizeWrap);
  window.addEventListener('resize', sizeWrap);
  document.addEventListener('DOMContentLoaded', sizeWrap);
  document.addEventListener('DOMContentLoaded', () => {
    const filterForm = document.getElementById('sp-data-filter-form');
    if (filterForm && window.ResizeObserver) new ResizeObserver(sizeWrap).observe(filterForm);
  });
})();
</script>
{% endblock %}
```

- [ ] **Step 6: Run the test to verify it passes**

Run: `cd C:\Financehub\app && python -m pytest tests/test_sponsorship_routes.py -v -k full_height_table_wrap`
Expected: PASS

- [ ] **Step 7: Run the full Sponsorship test suite**

Run: `cd C:\Financehub\app && python -m pytest tests/test_sponsorship_routes.py tests/test_sponsorship_dynamic_page_size.py -v`
Expected: all PASS — confirms the id/script addition didn't break the existing dynamic-page-size feature on this same tab.

- [ ] **Step 8: Manual check**

Open Sponsorship → Data with enough rows to fill the screen. Confirm the table wrapper's bottom edge reaches the viewport bottom with no visible gap before the floating pagination pill. Open the filter bar (press `F` or click the filter toggle) and confirm the table wrapper shrinks to still exactly fill the remaining space below it, with no gap. Resize the browser window and confirm it recomputes.

- [ ] **Step 9: Commit**

```bash
cd C:\Financehub
git add app/static/css/sponsorship.css app/templates/sponsorship/data.html app/tests/test_sponsorship_routes.py
git commit -m "fix: make Sponsorship Data table fill viewport height like Payment Application"
```

---

### Task 2: Fix the Outstanding tab

**Files:**
- Modify: `app/templates/sponsorship/outstanding.html:79` (add id) and `:124-130` (add script)
- Test: `app/tests/test_sponsorship_routes.py`

**Interfaces:**
- Consumes: `#sp-table-wrap { max-height: none; }` (Task 1's CSS rule — already applies here too, since it's an id selector and Task 1 didn't scope it to a specific page).

- [ ] **Step 1: Write the test**

Append to `app/tests/test_sponsorship_routes.py`:

```python
def test_outstanding_page_has_full_height_table_wrap_id(client):
    login(client)
    _select_smt(client)
    resp = client.get("/sponsorship/outstanding")
    assert resp.status_code == 200
    assert b'id="sp-table-wrap"' in resp.data
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd C:\Financehub\app && python -m pytest tests/test_sponsorship_routes.py -v -k outstanding_page_has_full_height`
Expected: FAIL — the id doesn't exist in `outstanding.html` yet.

- [ ] **Step 3: Add the id to the Outstanding tab's table wrapper**

In `app/templates/sponsorship/outstanding.html`, replace:

```html
  <div class="budget-table-container">
    <table class="outstanding-table">
```

with:

```html
  <div class="budget-table-container" id="sp-table-wrap">
    <table class="outstanding-table">
```

- [ ] **Step 4: Add the dynamic-height sizing script**

`outstanding.html` has no `{% block scripts %}` — its existing `exportOutstandingExcel()` script is a plain `<script>` tag placed after the content block's `{% endblock %}` (confirmed this renders correctly: `exportOutstandingExcel` appears in the actual page output despite being outside a named block). Follow the same existing convention rather than introducing a `{% block scripts %}` wrapper this file doesn't otherwise use.

Replace:

```html
<script>
function exportOutstandingExcel() {
  const form = document.getElementById("sp-data-filter-form");
  const params = new URLSearchParams(new FormData(form));
  window.location.href = "/sponsorship/outstanding/export?" + params.toString();
}
</script>
```

with:

```html
<script>
function exportOutstandingExcel() {
  const form = document.getElementById("sp-data-filter-form");
  const params = new URLSearchParams(new FormData(form));
  window.location.href = "/sponsorship/outstanding/export?" + params.toString();
}
</script>

<script>
// ─── Size sp-table-wrap to fill the entire remaining viewport ────────────
// Same technique as the Data tab (data.html) and #pa-scroll-wrap in
// etf_payment_application/index.html. Outstanding has no pagination bar,
// so this is the only thing needed to remove the gap at the bottom.
(function() {
  function sizeWrap() {
    const wrap = document.getElementById('sp-table-wrap');
    if (!wrap) return;
    requestAnimationFrame(() => {
      wrap.style.height = (window.innerHeight - wrap.getBoundingClientRect().top) + 'px';
    });
  }
  window.addEventListener('load', sizeWrap);
  window.addEventListener('resize', sizeWrap);
  document.addEventListener('DOMContentLoaded', sizeWrap);
  document.addEventListener('DOMContentLoaded', () => {
    const filterForm = document.getElementById('sp-data-filter-form');
    if (filterForm && window.ResizeObserver) new ResizeObserver(sizeWrap).observe(filterForm);
  });
})();
</script>
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `cd C:\Financehub\app && python -m pytest tests/test_sponsorship_routes.py -v -k outstanding_page_has_full_height`
Expected: PASS

- [ ] **Step 6: Run the full test suite**

Run: `cd C:\Financehub\app && python -m pytest tests/ -q`
Expected: same pass/fail counts as before this plan (pre-existing failures are documented as unrelated Windows SQLite file-lock flakiness in `01 - Proyek/FinanceHub/FinanceHub - Known Issues.md` in the Obsidian vault).

- [ ] **Step 7: Manual check**

Open Sponsorship → Outstanding with enough rows to fill the screen. Confirm the table wrapper's bottom edge reaches the viewport bottom with no gap. Open/close the filter bar and confirm it resizes correctly, same as Task 1's check.

- [ ] **Step 8: Commit**

```bash
cd C:\Financehub
git add app/templates/sponsorship/outstanding.html app/tests/test_sponsorship_routes.py
git commit -m "fix: make Sponsorship Outstanding table fill viewport height like Payment Application"
```

## Out of Scope

- `.budget-table-container`'s shared CSS rule and any other module using it (Budget, Beasiswa, Bank) — may have the same symptom on their own full-bleed tabs, but that's a separate effort.
- The Data tab's pagination mechanism (page size, floating bar styling) — unchanged.
- Payment Application / `#pa-scroll-wrap` — the reference implementation, not modified.
