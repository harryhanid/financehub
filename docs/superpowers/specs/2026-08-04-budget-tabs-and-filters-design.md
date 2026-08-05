# Budget Module — Unified Tab Navigation & Master/Realisasi Filters — Design

## Problem

Budget's 4 pages (Dashboard, Kelola Budget, Kelola Realisasi,
Carryover/Tambahan — each its own route/template, same architecture family
as Sponsorship) have never been migrated to the unified-header pattern
already shipped for Sponsorship, Beasiswa, Bank, and Payment
Application/Memo:

- No `use_unified_header=True` anywhere in `modules/budget/routes.py` and no
  `{% block module_tabs %}` in any of the 4 templates — confirmed via
  `grep`. Switching between these 4 pages today means going back to
  Dashboard's toolbar links (`master_list.html`/`realisasi_list.html`/
  `carryover.html` have no way to reach each other directly) or using
  Alt+K. Alt+←/→ doesn't work here (`pressTabStep` needs `.tabs .tab-btn`
  elements, which don't exist on these pages).
- Kelola Budget and Kelola Realisasi have no filter UI at all — but their
  service functions (`list_budgets`/`count_budgets`/`list_realisasi`/
  `count_realisasi`) already fully support filtering by company, dept,
  year, category, and activity via a shared helper,
  `_apply_common_filters()` (`service.py:44-60`), used against both
  `budget_master` and `budget_realisasi` (both tables have all 5 columns —
  confirmed via schema). The routes (`master_list`/`realisasi_list`) only
  ever read one of the five (`company`) from the query string; the other
  four are silently never wired up. This is the same "backend ready,
  frontend missing" shape as the Dashboard insights fix (2026-08-04,
  separate spec) — the capability already exists, it just isn't exposed.

## Decisions (confirmed with user)

- Carryover/Tambahan is explicitly **out of scope** for filtering in this
  spec — `budget_carryover_logs` has no company/dept/category/activity
  columns of its own (only a `budget_id` FK to `budget_master`), so
  filtering it needs a join that doesn't exist yet. It's a separate,
  larger piece of work. This spec gives Carryover the tab-nav migration
  only, same as the other 3 pages.
- Style/mechanism for both the tab bar and the filter panel follow the
  exact pattern already built for Sponsorship's Data/Outstanding pages
  this session — which is itself just the shared, generic mechanism
  Beasiswa already uses (`.tabs`/`.tab-btn` for navigation,
  `.filter-bar.collapsible` for filters, opened via the global "F" key
  handler in `app.js` — no per-page JS needed for either). Verified: no
  page in this codebase currently has a *visible* click-to-open filter
  button (an earlier assumption that Beasiswa had one was checked against
  the current file and found incorrect) — every filter panel today opens
  via "F" only, so Budget matches that same behavior, not something extra.

## Design

### Part A — Unified tab navigation (all 4 pages)

Add a shared partial, `templates/budget/_tabs.html`:

```html
<div class="tabs" style="margin-bottom:0">
  <a class="tab-btn{{ ' active' if active_tab == 'dashboard' else '' }}" href="{{ url_for('budget.index') }}">Dashboard</a>
  <a class="tab-btn{{ ' active' if active_tab == 'master' else '' }}" href="{{ url_for('budget.master_list') }}">Kelola Budget</a>
  <a class="tab-btn{{ ' active' if active_tab == 'realisasi' else '' }}" href="{{ url_for('budget.realisasi_list') }}">Kelola Realisasi</a>
  <a class="tab-btn{{ ' active' if active_tab == 'carryover' else '' }}" href="{{ url_for('budget.carryover_page') }}">Carryover / Tambahan</a>
</div>
```

Each of `dashboard.html`, `master_list.html`, `realisasi_list.html`,
`carryover.html` gains:

```html
{% block module_tabs %}
{% include "budget/_tabs.html" with context %}
{% endblock %}
```

Each route (`index`, `master_list`, `realisasi_list`, `carryover_page` —
all in `modules/budget/routes.py`) gains `use_unified_header=True` and an
`active_tab` value (`"dashboard"`/`"master"`/`"realisasi"`/`"carryover"`
respectively) in its `render_template()` call. This is the exact same
2-part change already applied to Sponsorship (`use_unified_header` flag +
`active_tab` + shared toolbar partial), so the module switcher, Alt+←/→
tab-stepping, and visual style all come for free — no new JS, no new CSS.

Dashboard's toolbar (`dashboard.html:22-24`) drops its 3 now-redundant
links (`Kelola Budget`/`Kelola Realisasi`/`Carryover / Tambahan`) — they'd
duplicate the new header tabs.

### Part B — Filters for Kelola Budget & Kelola Realisasi

**Routes.** `master_list()` and `realisasi_list()` (`routes.py:54-64`,
`:99-109`) replace their current one-line `company = request.args.get(...)`
with the existing `_filters_from_query()` (already defined at
`routes.py:144-153` for Dashboard's own use — reused verbatim, not
reimplemented). Its return includes `periodMode`/`periodMonth`, which
`_apply_common_filters()` never reads — harmless extra keys, not filtered
out, since passing them through costs nothing and keeps this a single
shared parsing function instead of two similar-but-different ones.

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

(`realisasi_list()` gets the identical treatment, `active_tab="realisasi"`,
rendering `realisasi_list.html`.) `count_budgets`/`list_budgets`/
`count_realisasi`/`list_realisasi` are unchanged — they already accept a
`filters` dict exactly like the one `_filters_from_query()` produces,
confirmed via `_apply_common_filters()`'s key checks
(`company`/`dept`/`year`/`category`/`activity`).

**Template — filter bar.** Both `master_list.html` and
`realisasi_list.html` gain, right after `<h1>`:

```html
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
```

(`id="bm-filter-bar"` for Master, `id="br-filter-bar"` for Realisasi — each
just needs *a* stable id; `getActiveFilterPanel()` doesn't care what it is,
only that `.filter-bar.collapsible` resolves to exactly one element per
page, which it does here.) Submitting via `onchange` on each `<select>`
matches Sponsorship's Data tab filter form exactly — full page reload,
server re-renders with the new filter applied, no client-side JS needed.

**Pagination links preserve all 5 filters,** not just `company` as today.
Replace the existing `{% if filter_company %}&company={{ filter_company }}{% endif %}`
pagination-link suffix in both templates with the same query-string-building
Jinja block already used in Sponsorship's `data.html`:

```html
{% set query_str = [] %}
{% for k, v in filters.items() %}
  {% if v and k in ('company', 'dept', 'year', 'category', 'activity') %}
    {% set _ = query_str.append(k ~ '=' ~ v|urlencode) %}
  {% endif %}
{% endfor %}
{% set filter_qs = ('&' ~ query_str|join('&')) if query_str else '' %}
<a class="budget-btn {% if page <= 1 %}disabled{% endif %}" href="?page={{ page - 1 }}{{ filter_qs }}">‹ Prev</a>
<a class="budget-btn {% if page >= total_pages %}disabled{% endif %}" href="?page={{ page + 1 }}{{ filter_qs }}">Next ›</a>
```

(The `k in (...)` guard skips `periodMode`/`periodMonth` even though
they're present in `filters` — they're Dashboard-only concepts, not
meaningful pagination state here.)

## Testing

- Route test: each of the 4 Budget pages (`/budget/`, `/budget/master`,
  `/budget/realisasi`, `/budget/carryover`) returns 200 and its response
  contains all 4 tab labels ("Kelola Budget", "Kelola Realisasi",
  "Carryover / Tambahan", "Dashboard") plus the module-switcher trigger
  markup (`fh-mod-trigger`, matching how the Sponsorship header-nav fix
  was verified).
- Route test: `GET /budget/master?company=PO&category=X` returns only
  rows matching both filters (seed 2+ budgets across companies/categories
  first) — proves the route now actually applies all 5 filters, not just
  `company`.
- Route test: same as above for `/budget/realisasi`.
- Route test: pagination links on a filtered `/budget/master` page
  preserve the active filters in their `href` (regex/substring check for
  `company=PO` etc. in the Prev/Next link markup).
- Manual: open each of the 4 Budget pages, confirm the header tab bar
  matches Sponsorship's/Beasiswa's visual style, confirm Alt+←/→ steps
  between all 4. On Kelola Budget/Realisasi, press "F", confirm the filter
  panel opens; select a Company/Dept/Year/Category/Activity, confirm the
  table re-filters and the URL reflects the selection; confirm Prev/Next
  (if more than one page of results) keep the filter applied.

## Out of Scope

- Any filter capability for Carryover/Tambahan — deferred to a separate
  spec once a join-based filter design exists for that table.
- Any change to `_apply_common_filters`, `list_budgets`, `count_budgets`,
  `list_realisasi`, `count_realisasi`, or `_filters_from_query` — all
  already correct and reused as-is.
- Any visual/insight change to the Budget Dashboard itself — covered by
  the separate 2026-08-04 Budget Dashboard missing-insights spec/plan.
- A visible click-to-open filter toggle button — this app has none
  anywhere today; Budget's filters open via "F" only, matching every
  other module's actual current behavior.
