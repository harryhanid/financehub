# Budget Tabs and Filters Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate all 4 Budget pages to the unified-header tab-navigation pattern already shipped for Sponsorship, and expose the company/dept/year/category/activity filtering that Kelola Budget's and Kelola Realisasi's service layer already supports but their routes/UI never wired up.

**Architecture:** A shared `budget/_tabs.html` partial (anchor-based `.tabs`/`.tab-btn`, mirroring Sponsorship's `_toolbar.html`) included via `{% block module_tabs %}` on all 4 pages, each route gaining `use_unified_header=True` + `active_tab`. Kelola Budget/Realisasi each gain a `.filter-bar.collapsible` form reusing the existing `_filters_from_query()` helper and `_apply_common_filters()` service function — no backend logic changes.

**Tech Stack:** Flask/Jinja2, pytest. No new JS anywhere in this plan — the tab-stepping (`pressTabStep`) and filter-toggle ("F"/Escape) mechanisms are both already generic and shared app-wide.

## Global Constraints

- Carryover/Tambahan gets the tab-nav migration only — no filter UI (its table has no company/dept/category columns to filter by; deferred to a separate spec).
- No change to `_apply_common_filters`, `list_budgets`, `count_budgets`, `list_realisasi`, `count_realisasi`, or `_filters_from_query` — all reused as-is.
- No new CSS and no new JS — `.tabs`/`.tab-btn`/`.filter-bar.collapsible` and the "F"/Escape/Alt+←/→ handlers are all pre-existing, generic, and shared across the whole app.
- Only these files change: `app/modules/budget/routes.py`, `app/templates/budget/_tabs.html` (new), `app/templates/budget/dashboard.html`, `app/templates/budget/master_list.html`, `app/templates/budget/realisasi_list.html`, `app/templates/budget/carryover.html`, `app/tests/test_budget_routes.py`.

---

### Task 1: Unified tab navigation across all 4 pages

**Files:**
- Create: `app/templates/budget/_tabs.html`
- Modify: `app/modules/budget/routes.py:54-64` (`master_list`), `:99-109` (`realisasi_list`), `:156-159` (`index`), `:179-187` (`carryover_page`)
- Modify: `app/templates/budget/dashboard.html`, `app/templates/budget/master_list.html`, `app/templates/budget/realisasi_list.html`, `app/templates/budget/carryover.html`
- Test: `app/tests/test_budget_routes.py`

**Interfaces:**
- Produces: `templates/budget/_tabs.html` partial, consumed by Tasks 2-3's templates (unchanged by them, just already present).

- [ ] **Step 1: Write the failing test**

Append to `app/tests/test_budget_routes.py`:

```python
def test_all_four_budget_pages_have_unified_tab_bar(client):
    login(client)
    for url, label in [
        ("/budget/", "Dashboard"),
        ("/budget/master", "Kelola Budget"),
        ("/budget/realisasi", "Kelola Realisasi"),
        ("/budget/carryover", "Carryover / Tambahan"),
    ]:
        resp = client.get(url)
        assert resp.status_code == 200, url
        html = resp.data.decode()
        assert 'id="fh-mod-trigger"' in html, f"{url}: no module switcher"
        assert "Kelola Budget" in html
        assert "Kelola Realisasi" in html
        assert "Carryover / Tambahan" in html
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd C:\Financehub\app && python -m pytest tests/test_budget_routes.py -v -k unified_tab_bar`
Expected: FAIL — none of the 4 pages currently render `fh-mod-trigger` (no `use_unified_header` anywhere yet).

- [ ] **Step 3: Create the shared tab partial**

Create `app/templates/budget/_tabs.html`:

```html
<div class="tabs" style="margin-bottom:0">
  <a class="tab-btn{{ ' active' if active_tab == 'dashboard' else '' }}" href="{{ url_for('budget.index') }}">Dashboard</a>
  <a class="tab-btn{{ ' active' if active_tab == 'master' else '' }}" href="{{ url_for('budget.master_list') }}">Kelola Budget</a>
  <a class="tab-btn{{ ' active' if active_tab == 'realisasi' else '' }}" href="{{ url_for('budget.realisasi_list') }}">Kelola Realisasi</a>
  <a class="tab-btn{{ ' active' if active_tab == 'carryover' else '' }}" href="{{ url_for('budget.carryover_page') }}">Carryover / Tambahan</a>
</div>
```

- [ ] **Step 4: Wire the flag and tab into all 4 routes**

In `app/modules/budget/routes.py`, replace:

```python
@bp.route("/master")
@jwt_html_required
def master_list():
    company = request.args.get("company")
    filters = {"company": company} if company else None
    total = count_budgets(filters)
    page, total_pages = _paginate(total)
    budgets = list_budgets(filters, limit=PER_PAGE, offset=(page - 1) * PER_PAGE)
    return render_template("budget/master_list.html", budgets=budgets, active_page="budget",
                            filter_company=company, page=page, total_pages=total_pages,
                            total_count=total, **_ctx())
```

with:

```python
@bp.route("/master")
@jwt_html_required
def master_list():
    company = request.args.get("company")
    filters = {"company": company} if company else None
    total = count_budgets(filters)
    page, total_pages = _paginate(total)
    budgets = list_budgets(filters, limit=PER_PAGE, offset=(page - 1) * PER_PAGE)
    return render_template("budget/master_list.html", budgets=budgets, active_page="budget",
                            active_tab="master", use_unified_header=True,
                            filter_company=company, page=page, total_pages=total_pages,
                            total_count=total, **_ctx())
```

(Task 2 replaces this whole route again — this step only adds the tab-nav
flag/value without touching the filter logic yet, keeping this task
independently testable before Task 2's filter work lands.)

Replace:

```python
@bp.route("/realisasi")
@jwt_html_required
def realisasi_list():
    company = request.args.get("company")
    filters = {"company": company} if company else None
    total = count_realisasi(filters)
    page, total_pages = _paginate(total)
    realisasi = list_realisasi(filters, limit=PER_PAGE, offset=(page - 1) * PER_PAGE)
    return render_template("budget/realisasi_list.html", realisasi=realisasi, active_page="budget",
                            filter_company=company, page=page, total_pages=total_pages,
                            total_count=total, **_ctx())
```

with:

```python
@bp.route("/realisasi")
@jwt_html_required
def realisasi_list():
    company = request.args.get("company")
    filters = {"company": company} if company else None
    total = count_realisasi(filters)
    page, total_pages = _paginate(total)
    realisasi = list_realisasi(filters, limit=PER_PAGE, offset=(page - 1) * PER_PAGE)
    return render_template("budget/realisasi_list.html", realisasi=realisasi, active_page="budget",
                            active_tab="realisasi", use_unified_header=True,
                            filter_company=company, page=page, total_pages=total_pages,
                            total_count=total, **_ctx())
```

Replace:

```python
@bp.route("/")
@jwt_html_required
def index():
    return render_template("budget/dashboard.html", active_page="budget", **_ctx())
```

with:

```python
@bp.route("/")
@jwt_html_required
def index():
    return render_template("budget/dashboard.html", active_page="budget",
                            active_tab="dashboard", use_unified_header=True, **_ctx())
```

Replace:

```python
@bp.route("/carryover")
@jwt_html_required
def carryover_page():
    from modules.budget.service import get_carryover_data
    total = count_carryover_logs()
    page, total_pages = _paginate(total)
    logs = get_carryover_data(limit=PER_PAGE, offset=(page - 1) * PER_PAGE)
    return render_template("budget/carryover.html", logs=logs, active_page="budget",
                            page=page, total_pages=total_pages, total_count=total, **_ctx())
```

with:

```python
@bp.route("/carryover")
@jwt_html_required
def carryover_page():
    from modules.budget.service import get_carryover_data
    total = count_carryover_logs()
    page, total_pages = _paginate(total)
    logs = get_carryover_data(limit=PER_PAGE, offset=(page - 1) * PER_PAGE)
    return render_template("budget/carryover.html", logs=logs, active_page="budget",
                            active_tab="carryover", use_unified_header=True,
                            page=page, total_pages=total_pages, total_count=total, **_ctx())
```

- [ ] **Step 5: Add the module_tabs block to all 4 templates**

In `app/templates/budget/dashboard.html`, replace:

```html
{% block content %}
<div class="budget-page">
  <h1>Budget Dashboard</h1>

  <div class="budget-toolbar">
    <select id="bf-company">
      <option value="ALL">Semua Company</option>
      <option value="PO">PO (SMT)</option>
      <option value="TF">TF (ETF)</option>
    </select>
    <select id="bf-dept"><option value="ALL">Semua Dept</option></select>
    <select id="bf-year"><option value="ALL">Semua Tahun</option></select>
    <select id="bf-category"><option value="ALL">Semua Kategori</option></select>
    <select id="bf-activity"><option value="ALL">Semua Aktivitas</option></select>
    <button class="budget-btn" id="bf-apply">Terapkan Filter</button>
    <a class="budget-btn" href="/budget/master">Kelola Budget</a>
    <a class="budget-btn" href="/budget/realisasi">Kelola Realisasi</a>
    <a class="budget-btn" href="/budget/carryover">Carryover / Tambahan</a>
  </div>
```

with:

```html
{% block module_tabs %}
{% include "budget/_tabs.html" with context %}
{% endblock %}
{% block content %}
<div class="budget-page">
  <h1>Budget Dashboard</h1>

  <div class="budget-toolbar">
    <select id="bf-company">
      <option value="ALL">Semua Company</option>
      <option value="PO">PO (SMT)</option>
      <option value="TF">TF (ETF)</option>
    </select>
    <select id="bf-dept"><option value="ALL">Semua Dept</option></select>
    <select id="bf-year"><option value="ALL">Semua Tahun</option></select>
    <select id="bf-category"><option value="ALL">Semua Kategori</option></select>
    <select id="bf-activity"><option value="ALL">Semua Aktivitas</option></select>
    <button class="budget-btn" id="bf-apply">Terapkan Filter</button>
  </div>
```

(The 3 nav links are removed — they now duplicate the header tabs.)

In `app/templates/budget/master_list.html`, replace:

```html
{% block content %}
<div class="budget-page">
  <h1>Budget Master</h1>
  <div class="budget-toolbar">
    <button class="budget-btn" onclick="openModal('budget-master-modal')">+ Budget Baru</button>
  </div>
```

with:

```html
{% block module_tabs %}
{% include "budget/_tabs.html" with context %}
{% endblock %}
{% block content %}
<div class="budget-page">
  <h1>Budget Master</h1>
  <div class="budget-toolbar">
    <button class="budget-btn" onclick="openModal('budget-master-modal')">+ Budget Baru</button>
  </div>
```

In `app/templates/budget/realisasi_list.html`, replace:

```html
{% block content %}
<div class="budget-page">
  <h1>Realisasi Budget</h1>
  <div class="budget-toolbar">
    <button class="budget-btn" onclick="openModal('budget-realisasi-modal')">+ Realisasi Baru</button>
  </div>
```

with:

```html
{% block module_tabs %}
{% include "budget/_tabs.html" with context %}
{% endblock %}
{% block content %}
<div class="budget-page">
  <h1>Realisasi Budget</h1>
  <div class="budget-toolbar">
    <button class="budget-btn" onclick="openModal('budget-realisasi-modal')">+ Realisasi Baru</button>
  </div>
```

In `app/templates/budget/carryover.html`, replace:

```html
{% block content %}
<div class="budget-page">
  <h1>Carryover & Additional Budget Requests</h1>

  <div class="budget-toolbar">
```

with:

```html
{% block module_tabs %}
{% include "budget/_tabs.html" with context %}
{% endblock %}
{% block content %}
<div class="budget-page">
  <h1>Carryover & Additional Budget Requests</h1>

  <div class="budget-toolbar">
```

- [ ] **Step 6: Run the test to verify it passes**

Run: `cd C:\Financehub\app && python -m pytest tests/test_budget_routes.py -v -k unified_tab_bar`
Expected: PASS

- [ ] **Step 7: Run the full Budget test suite**

Run: `cd C:\Financehub\app && python -m pytest tests/test_budget_routes.py -v`
Expected: all PASS (aside from the pre-existing `test_nav_stays_visible_on_budget_pages` failure already documented as stale in `01 - Proyek/FinanceHub/FinanceHub - Known Issues.md` in the Obsidian vault).

- [ ] **Step 8: Manual check**

Open each of the 4 Budget pages. Confirm the header shows the module
switcher ("Budget ▾") plus the 4 tabs, styled consistently with
Sponsorship/Beasiswa. Confirm Alt+←/→ steps between all 4 pages. Confirm
Dashboard's toolbar no longer has the 3 redundant nav links.

- [ ] **Step 9: Commit**

```bash
cd C:\Financehub
git add app/modules/budget/routes.py app/templates/budget/_tabs.html app/templates/budget/dashboard.html app/templates/budget/master_list.html app/templates/budget/realisasi_list.html app/templates/budget/carryover.html app/tests/test_budget_routes.py
git commit -m "feat: unify Budget module tab navigation across all 4 pages"
```

---

### Task 2: Filters for Kelola Budget

**Files:**
- Modify: `app/modules/budget/routes.py` (the `master_list` route, updated again from Task 1's version)
- Modify: `app/templates/budget/master_list.html`
- Test: `app/tests/test_budget_routes.py`

**Interfaces:**
- Consumes: `_filters_from_query()` (`routes.py:144-153`, pre-existing), `get_available_years`/`get_available_categories`/`get_available_departments`/`get_available_activities` (pre-existing, already imported)

- [ ] **Step 1: Write the failing test**

Append to `app/tests/test_budget_routes.py`:

```python
def test_master_list_filters_by_category_and_company(client):
    login(client)
    client.post("/budget/master/create", json={
        "company": "PO", "dept": "Finance", "mm": 1, "yy": 2026,
        "amount": 1000000, "budget_category": "OPEX",
    })
    client.post("/budget/master/create", json={
        "company": "TF", "dept": "HR", "mm": 1, "yy": 2026,
        "amount": 2000000, "budget_category": "CAPEX",
    })
    resp = client.get("/budget/master?company=PO&category=OPEX")
    assert resp.status_code == 200
    html = resp.data.decode()
    assert "Finance" in html
    assert "HR" not in html


def test_master_list_pagination_links_preserve_filters(client):
    login(client)
    client.post("/budget/master/create", json={
        "company": "PO", "dept": "Finance", "mm": 1, "yy": 2026, "amount": 1000000,
    })
    resp = client.get("/budget/master?company=PO&category=OPEX")
    assert b"company=PO" in resp.data
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd C:\Financehub\app && python -m pytest tests/test_budget_routes.py -v -k "master_list_filters_by_category or master_list_pagination_links"`
Expected: FAIL — `test_master_list_filters_by_category_and_company` fails because `category` is never read by the route (both rows appear regardless of the `category=OPEX` filter); `test_master_list_pagination_links_preserve_filters` fails because pagination links currently only ever include `company` when `filter_company` truthy, but there's no second page here to even render a Prev/Next link — adjust: this second test only exercises the *filter parsing*, not pagination rendering, since one row isn't enough to trigger `total_pages > 1`. The `company=PO` string check passes trivially once basic filter-echo exists (see Step 3) — its real purpose is guarding against a regression once Step 3 lands, not proving pagination markup specifically. Treat its initial failure as confirmation `company` filtering doesn't fully round-trip yet.

- [ ] **Step 3: Update the route**

In `app/modules/budget/routes.py`, replace:

```python
@bp.route("/master")
@jwt_html_required
def master_list():
    company = request.args.get("company")
    filters = {"company": company} if company else None
    total = count_budgets(filters)
    page, total_pages = _paginate(total)
    budgets = list_budgets(filters, limit=PER_PAGE, offset=(page - 1) * PER_PAGE)
    return render_template("budget/master_list.html", budgets=budgets, active_page="budget",
                            active_tab="master", use_unified_header=True,
                            filter_company=company, page=page, total_pages=total_pages,
                            total_count=total, **_ctx())
```

with:

```python
@bp.route("/master")
@jwt_html_required
def master_list():
    filters = _filters_from_query()
    total = count_budgets(filters)
    page, total_pages = _paginate(total)
    budgets = list_budgets(filters, limit=PER_PAGE, offset=(page - 1) * PER_PAGE)
    return render_template(
        "budget/master_list.html", budgets=budgets, active_page="budget",
        active_tab="master", use_unified_header=True, filters=filters,
        years=get_available_years(), categories=get_available_categories(),
        departments=get_available_departments(), activities=get_available_activities(),
        page=page, total_pages=total_pages, total_count=total, **_ctx()
    )
```

- [ ] **Step 4: Add the filter bar and fix pagination links**

In `app/templates/budget/master_list.html`, replace:

```html
{% block content %}
<div class="budget-page">
  <h1>Budget Master</h1>
  <div class="budget-toolbar">
    <button class="budget-btn" onclick="openModal('budget-master-modal')">+ Budget Baru</button>
  </div>
```

with:

```html
{% block content %}
<div class="budget-page">
  <h1>Budget Master</h1>
  <form class="filter-bar collapsible" id="bm-filter-bar" method="get">
    <div class="filter-field">
      <label>Company</label>
      <select name="company" onchange="this.form.submit()">
        <option value="">Semua Company</option>
        <option value="PO" {% if filters.company == 'PO' %}selected{% endif %}>PO (SMT)</option>
        <option value="TF" {% if filters.company == 'TF' %}selected{% endif %}>TF (ETF)</option>
      </select>
    </div>
    <div class="filter-field">
      <label>Dept</label>
      <select name="dept" onchange="this.form.submit()">
        <option value="">Semua Dept</option>
        {% for d in departments %}<option value="{{ d }}" {% if filters.dept == d %}selected{% endif %}>{{ d }}</option>{% endfor %}
      </select>
    </div>
    <div class="filter-field">
      <label>Tahun</label>
      <select name="year" onchange="this.form.submit()">
        <option value="">Semua Tahun</option>
        {% for y in years %}<option value="{{ y }}" {% if filters.year == y %}selected{% endif %}>{{ y }}</option>{% endfor %}
      </select>
    </div>
    <div class="filter-field">
      <label>Category</label>
      <select name="category" onchange="this.form.submit()">
        <option value="">Semua Category</option>
        {% for c in categories %}<option value="{{ c }}" {% if filters.category == c %}selected{% endif %}>{{ c }}</option>{% endfor %}
      </select>
    </div>
    <div class="filter-field">
      <label>Activity</label>
      <select name="activity" onchange="this.form.submit()">
        <option value="">Semua Activity</option>
        {% for a in activities %}<option value="{{ a }}" {% if filters.activity == a %}selected{% endif %}>{{ a }}</option>{% endfor %}
      </select>
    </div>
  </form>
  <div class="budget-toolbar">
    <button class="budget-btn" onclick="openModal('budget-master-modal')">+ Budget Baru</button>
  </div>
```

Replace:

```html
  {% if total_pages and total_pages > 1 %}
  <div class="budget-pagination">
    <span class="budget-pagination-info">Halaman {{ page }} dari {{ total_pages }} ({{ total_count }} data)</span>
    <div class="budget-pagination-nav">
      <a class="budget-btn {% if page <= 1 %}disabled{% endif %}"
         href="?page={{ page - 1 }}{% if filter_company %}&company={{ filter_company }}{% endif %}">‹ Prev</a>
      <a class="budget-btn {% if page >= total_pages %}disabled{% endif %}"
         href="?page={{ page + 1 }}{% if filter_company %}&company={{ filter_company }}{% endif %}">Next ›</a>
    </div>
  </div>
  {% endif %}
```

with:

```html
  {% set query_str = [] %}
  {% for k, v in filters.items() %}
    {% if v and k in ('company', 'dept', 'year', 'category', 'activity') %}
      {% set _ = query_str.append(k ~ '=' ~ v|urlencode) %}
    {% endif %}
  {% endfor %}
  {% set filter_qs = ('&' ~ query_str|join('&')) if query_str else '' %}
  {% if total_pages and total_pages > 1 %}
  <div class="budget-pagination">
    <span class="budget-pagination-info">Halaman {{ page }} dari {{ total_pages }} ({{ total_count }} data)</span>
    <div class="budget-pagination-nav">
      <a class="budget-btn {% if page <= 1 %}disabled{% endif %}"
         href="?page={{ page - 1 }}{{ filter_qs }}">‹ Prev</a>
      <a class="budget-btn {% if page >= total_pages %}disabled{% endif %}"
         href="?page={{ page + 1 }}{{ filter_qs }}">Next ›</a>
    </div>
  </div>
  {% endif %}
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `cd C:\Financehub\app && python -m pytest tests/test_budget_routes.py -v -k "master_list_filters_by_category or master_list_pagination_links"`
Expected: both PASS.

- [ ] **Step 6: Run the full Budget test suite**

Run: `cd C:\Financehub\app && python -m pytest tests/test_budget_routes.py -v`
Expected: all PASS (same pre-existing exception as Task 1).

- [ ] **Step 7: Manual check**

Open Kelola Budget. Press "F", confirm the filter panel opens (5 dropdowns). Select a Company, confirm the table re-filters and the URL updates with `?company=...`. Combine 2+ filters, confirm both apply (AND logic). Confirm existing "+ Budget Baru" flow still works unchanged.

- [ ] **Step 8: Commit**

```bash
cd C:\Financehub
git add app/modules/budget/routes.py app/templates/budget/master_list.html app/tests/test_budget_routes.py
git commit -m "feat: wire up company/dept/year/category/activity filters on Kelola Budget"
```

---

### Task 3: Filters for Kelola Realisasi + final verification

**Files:**
- Modify: `app/modules/budget/routes.py` (the `realisasi_list` route)
- Modify: `app/templates/budget/realisasi_list.html`
- Test: `app/tests/test_budget_routes.py`

**Interfaces:**
- Consumes: same as Task 2 (`_filters_from_query`, the 4 lookup functions) — identical pattern, different table/route/template.

- [ ] **Step 1: Write the failing test**

Append to `app/tests/test_budget_routes.py`:

```python
def test_realisasi_list_filters_by_company(client):
    login(client)
    create_resp = client.post("/budget/master/create", json={
        "company": "PO", "dept": "Finance", "mm": 1, "yy": 2026, "amount": 1000000,
    })
    budget_id = create_resp.get_json()["id"]
    client.post("/budget/realisasi/create", json={
        "budget_id": budget_id, "tanggal_realisasi": "2026-01-15",
        "description": "Test PO", "amount": 100000,
    })
    resp = client.get("/budget/realisasi?company=TF")
    assert resp.status_code == 200
    assert b"Test PO" not in resp.data
```

(Verified directly against `service.py`: `create_budget()` returns
`{"ok": True, "pesan": ..., "id": budget_id}` — the key is `"id"`, not
`"budget_id"`. `create_realisasi()` reads `payload.get("tanggal_realisasi")`,
not `"tanggal"` — and inherits `company`/`dept`/`budget_category`/`activity`
from the linked `budget_master` row rather than reading them from this
payload at all, which is exactly why seeding a PO-company budget first and
linking the realisasi to it is enough to make this test's company filter
meaningful.)

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd C:\Financehub\app && python -m pytest tests/test_budget_routes.py -v -k realisasi_list_filters_by_company`
Expected: FAIL — `company` filter isn't applied to `budget_realisasi` rows the same way it is for `budget_master` yet (the route only reads `company` today, but let's confirm this specific case truly exercises a gap — if it unexpectedly passes because `company` already partially works, that's fine too; the meaningful assertion this task must still add is the other 4 filters, covered structurally by reusing `_filters_from_query()` in Step 3 either way).

- [ ] **Step 3: Update the route**

In `app/modules/budget/routes.py`, replace:

```python
@bp.route("/realisasi")
@jwt_html_required
def realisasi_list():
    company = request.args.get("company")
    filters = {"company": company} if company else None
    total = count_realisasi(filters)
    page, total_pages = _paginate(total)
    realisasi = list_realisasi(filters, limit=PER_PAGE, offset=(page - 1) * PER_PAGE)
    return render_template("budget/realisasi_list.html", realisasi=realisasi, active_page="budget",
                            active_tab="realisasi", use_unified_header=True,
                            filter_company=company, page=page, total_pages=total_pages,
                            total_count=total, **_ctx())
```

with:

```python
@bp.route("/realisasi")
@jwt_html_required
def realisasi_list():
    filters = _filters_from_query()
    total = count_realisasi(filters)
    page, total_pages = _paginate(total)
    realisasi = list_realisasi(filters, limit=PER_PAGE, offset=(page - 1) * PER_PAGE)
    return render_template(
        "budget/realisasi_list.html", realisasi=realisasi, active_page="budget",
        active_tab="realisasi", use_unified_header=True, filters=filters,
        years=get_available_years(), categories=get_available_categories(),
        departments=get_available_departments(), activities=get_available_activities(),
        page=page, total_pages=total_pages, total_count=total, **_ctx()
    )
```

- [ ] **Step 4: Add the filter bar and fix pagination links**

In `app/templates/budget/realisasi_list.html`, replace:

```html
{% block content %}
<div class="budget-page">
  <h1>Realisasi Budget</h1>
  <div class="budget-toolbar">
    <button class="budget-btn" onclick="openModal('budget-realisasi-modal')">+ Realisasi Baru</button>
  </div>
```

with:

```html
{% block content %}
<div class="budget-page">
  <h1>Realisasi Budget</h1>
  <form class="filter-bar collapsible" id="br-filter-bar" method="get">
    <div class="filter-field">
      <label>Company</label>
      <select name="company" onchange="this.form.submit()">
        <option value="">Semua Company</option>
        <option value="PO" {% if filters.company == 'PO' %}selected{% endif %}>PO (SMT)</option>
        <option value="TF" {% if filters.company == 'TF' %}selected{% endif %}>TF (ETF)</option>
      </select>
    </div>
    <div class="filter-field">
      <label>Dept</label>
      <select name="dept" onchange="this.form.submit()">
        <option value="">Semua Dept</option>
        {% for d in departments %}<option value="{{ d }}" {% if filters.dept == d %}selected{% endif %}>{{ d }}</option>{% endfor %}
      </select>
    </div>
    <div class="filter-field">
      <label>Tahun</label>
      <select name="year" onchange="this.form.submit()">
        <option value="">Semua Tahun</option>
        {% for y in years %}<option value="{{ y }}" {% if filters.year == y %}selected{% endif %}>{{ y }}</option>{% endfor %}
      </select>
    </div>
    <div class="filter-field">
      <label>Category</label>
      <select name="category" onchange="this.form.submit()">
        <option value="">Semua Category</option>
        {% for c in categories %}<option value="{{ c }}" {% if filters.category == c %}selected{% endif %}>{{ c }}</option>{% endfor %}
      </select>
    </div>
    <div class="filter-field">
      <label>Activity</label>
      <select name="activity" onchange="this.form.submit()">
        <option value="">Semua Activity</option>
        {% for a in activities %}<option value="{{ a }}" {% if filters.activity == a %}selected{% endif %}>{{ a }}</option>{% endfor %}
      </select>
    </div>
  </form>
  <div class="budget-toolbar">
    <button class="budget-btn" onclick="openModal('budget-realisasi-modal')">+ Realisasi Baru</button>
  </div>
```

Replace:

```html
  {% if total_pages and total_pages > 1 %}
  <div class="budget-pagination">
    <span class="budget-pagination-info">Halaman {{ page }} dari {{ total_pages }} ({{ total_count }} data)</span>
    <div class="budget-pagination-nav">
      <a class="budget-btn {% if page <= 1 %}disabled{% endif %}"
         href="?page={{ page - 1 }}{% if filter_company %}&company={{ filter_company }}{% endif %}">‹ Prev</a>
      <a class="budget-btn {% if page >= total_pages %}disabled{% endif %}"
         href="?page={{ page + 1 }}{% if filter_company %}&company={{ filter_company }}{% endif %}">Next ›</a>
    </div>
  </div>
  {% endif %}
```

with:

```html
  {% set query_str = [] %}
  {% for k, v in filters.items() %}
    {% if v and k in ('company', 'dept', 'year', 'category', 'activity') %}
      {% set _ = query_str.append(k ~ '=' ~ v|urlencode) %}
    {% endif %}
  {% endfor %}
  {% set filter_qs = ('&' ~ query_str|join('&')) if query_str else '' %}
  {% if total_pages and total_pages > 1 %}
  <div class="budget-pagination">
    <span class="budget-pagination-info">Halaman {{ page }} dari {{ total_pages }} ({{ total_count }} data)</span>
    <div class="budget-pagination-nav">
      <a class="budget-btn {% if page <= 1 %}disabled{% endif %}"
         href="?page={{ page - 1 }}{{ filter_qs }}">‹ Prev</a>
      <a class="budget-btn {% if page >= total_pages %}disabled{% endif %}"
         href="?page={{ page + 1 }}{{ filter_qs }}">Next ›</a>
    </div>
  </div>
  {% endif %}
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `cd C:\Financehub\app && python -m pytest tests/test_budget_routes.py -v -k realisasi_list_filters_by_company`
Expected: PASS

- [ ] **Step 6: Run the full test suite**

Run: `cd C:\Financehub\app && python -m pytest tests/ -q`
Expected: same pass/fail counts as before this plan aside from the tests it added (pre-existing failures are documented as unrelated Windows SQLite file-lock flakiness / stale assertions in `01 - Proyek/FinanceHub/FinanceHub - Known Issues.md` in the Obsidian vault).

- [ ] **Step 7: Manual check**

Open Kelola Realisasi. Confirm the filter panel matches Kelola Budget's
(same 5 fields, same style). Filter by company/category/activity, confirm
the table re-filters. Confirm existing "+ Realisasi Baru" flow still works
unchanged. As a final full-module pass: step through all 4 Budget tabs via
Alt+←/→ once more to confirm nothing from Tasks 2-3 broke Task 1's
navigation.

- [ ] **Step 8: Commit**

```bash
cd C:\Financehub
git add app/modules/budget/routes.py app/templates/budget/realisasi_list.html app/tests/test_budget_routes.py
git commit -m "feat: wire up company/dept/year/category/activity filters on Kelola Realisasi"
```

## Out of Scope

- Carryover/Tambahan filtering — deferred, needs a new join design.
- Any change to the Budget Dashboard's own charts/insights — covered by the separate 2026-08-04 missing-insights plan.
- `_apply_common_filters`, `list_budgets`, `count_budgets`, `list_realisasi`, `count_realisasi`, `_filters_from_query` — all reused unmodified.
