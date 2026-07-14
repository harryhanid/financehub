# FinanceHub Dashboard Module Tab Bar Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a visible tab bar of the 7 active modules to the Dashboard page (`/dashboard`) so users can navigate to any module directly, without relying only on the Alt+K command palette.

**Architecture:** Pure server-rendered addition. `modules/dashboard/routes.py` builds a static list of `(name, url)` pairs via `url_for()` and passes it to the template; `templates/dashboard/index.html` renders it as `.tab-btn` links inside the existing `.tabs`/`.page-toolbar` CSS (already used by Beasiswa — no new CSS). No changes to `base.html`, `app.js`, or the command palette.

**Tech Stack:** Flask, Jinja2, pytest (existing `client` fixture in `tests/conftest.py`).

## Global Constraints

- Scoped to the Dashboard page only — do NOT touch `base.html`, the global navbar, `app.js`, or the command palette (`FH_MODULES`). Those are out of scope per the design doc.
- No new CSS — reuse `.tabs`, `.tab-btn`, `.tab-btn.active`, `.page-toolbar` exactly as defined in `static/css/style.css` (already used by `templates/beasiswa/index.html`).
- Coming-soon modules (Account Payable, Advance, Petty Cash, Sponsorship) must NOT appear in this tab bar.
- Tab links must use `url_for()` in the Python route, never hardcoded path strings, so they can't drift from actual blueprint routes.
- Reference spec: `docs/superpowers/specs/2026-07-15-financehub-dashboard-module-tabs-design.md`

---

### Task 1: Add module tab bar to Dashboard page

**Files:**
- Modify: `app/modules/dashboard/routes.py:1-81` (add `DASHBOARD_TABS` list + `modules` context var in `index()`)
- Modify: `app/templates/dashboard/index.html:1-8` (wrap title in `.page-toolbar`, add `.tabs` row)
- Test: `app/tests/test_dashboard.py`

**Interfaces:**
- Produces: `modules/dashboard/routes.py` module-level constant `DASHBOARD_TABS: list[tuple[str, str]]` (label, Flask endpoint name pairs) — not consumed elsewhere, purely local to this view.
- Produces: `index()` passes `modules` to `render_template` as `list[dict]`, each `{"name": str, "url": str}` — consumed only by `templates/dashboard/index.html`.

- [ ] **Step 1: Write the failing test**

Append to `app/tests/test_dashboard.py`:

```python
def test_dashboard_shows_module_tabs(client):
    login(client)
    select_etf(client)
    resp = client.get("/dashboard")
    html = resp.data.decode()
    assert 'class="tab-btn active" href="/dashboard"' in html
    for label, href in [
        ("Beasiswa", "/beasiswa/"),
        ("Payment Approval Memo", "/payment-memo/"),
        ("Payment Application", "/etf-payment-application/"),
        ("Budget", "/budget/"),
        ("Bank", "/bank/"),
        ("Users", "/users/"),
    ]:
        assert f'href="{href}"' in html
        assert label in html
    assert "Account Payable" not in html
    assert "Coming Soon" not in html
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd C:\Financehub\app && python -m pytest tests/test_dashboard.py::test_dashboard_shows_module_tabs -v`
Expected: FAIL — `assert 'class="tab-btn active" href="/dashboard"' in html` raises `AssertionError` (tab markup doesn't exist yet).

- [ ] **Step 3: Add `DASHBOARD_TABS` and pass `modules` to the template**

In `app/modules/dashboard/routes.py`, add this module-level constant right after the existing `bp = Blueprint("dashboard", __name__)` line (line 9):

```python
DASHBOARD_TABS = [
    ("Dashboard",             "dashboard.index"),
    ("Beasiswa",              "beasiswa.index"),
    ("Payment Approval Memo", "payment_memo.index"),
    ("Payment Application",   "etf_payment_application.index"),
    ("Budget",                "budget.index"),
    ("Bank",                  "bank.index"),
    ("Users",                 "users.index"),
]
```

Then change the `index()` view's `render_template` call (currently lines 80-81):

```python
    return render_template("dashboard/index.html", stats=stats, dash=dash,
                           active_page="dashboard", **get_ctx())
```

to:

```python
    modules = [{"name": name, "url": url_for(endpoint)} for name, endpoint in DASHBOARD_TABS]
    return render_template("dashboard/index.html", stats=stats, dash=dash,
                           modules=modules, active_page="dashboard", **get_ctx())
```

- [ ] **Step 4: Render the tab bar in the template**

In `app/templates/dashboard/index.html`, replace lines 4-8:

```html
<div class="page-header">
  <div>
    <h1 class="page-title">Dashboard</h1>
  </div>
</div>
```

with:

```html
<div class="page-header">
  <div class="page-toolbar">
    <h1 class="page-title" style="margin-bottom:0">Dashboard</h1>
    <div class="tabs" style="margin-bottom:0">
      {% for m in modules %}
      <a class="tab-btn{{ ' active' if m.name == 'Dashboard' else '' }}" href="{{ m.url }}">{{ m.name }}</a>
      {% endfor %}
    </div>
  </div>
</div>
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd C:\Financehub\app && python -m pytest tests/test_dashboard.py::test_dashboard_shows_module_tabs -v`
Expected: PASS

- [ ] **Step 6: Run the full dashboard test file to check for regressions**

Run: `cd C:\Financehub\app && python -m pytest tests/test_dashboard.py -v`
Expected: All tests PASS (`test_dashboard_redirect_without_login`, `test_select_company_page_requires_login`, `test_select_company_after_login`, `test_dashboard_after_company_selection`, `test_dashboard_shows_etf_stats`, `test_dashboard_shows_module_tabs`)

- [ ] **Step 7: Commit**

```bash
cd C:\Financehub
git add app/modules/dashboard/routes.py app/templates/dashboard/index.html app/tests/test_dashboard.py
git commit -m "feat: add module tab bar to Dashboard page"
```

---

### Task 2: Manual verification in browser

**Files:** none (verification only)

- [ ] **Step 1: Start the dev server**

Run: `cd C:\Financehub\app && python run.py` (or confirm it's already running at `http://localhost:8081`)

- [ ] **Step 2: Load the Dashboard and check the tab bar**

Open `http://localhost:8081/dashboard` in a browser, logged in with company ETF selected.

Expected:
- A row of 7 pill-shaped tabs appears next to the "Dashboard" title: Dashboard, Beasiswa, Payment Approval Memo, Payment Application, Budget, Bank, Users
- "Dashboard" tab is highlighted (blue gradient background, matches `.tab-btn.active` style already used in Beasiswa)
- No "Account Payable" / "Advance" / "Petty Cash" / "Sponsorship" tabs present

- [ ] **Step 3: Click through each tab**

Click "Beasiswa" → lands on `/beasiswa/`. Click browser back, click "Payment Approval Memo" → lands on `/payment-memo/`. Repeat for "Payment Application", "Budget", "Bank", "Users" — each must land on its module's index page without a 404 or redirect loop.

- [ ] **Step 4: Check dark mode**

Toggle dark mode (moon icon in navbar). Confirm the tab bar colors adapt correctly (uses existing CSS variables, should require no extra work).

- [ ] **Step 5: Check narrow viewport**

Resize the browser window to ~400px wide (or use devtools device toolbar). Confirm the tab row wraps to a second line instead of overflowing horizontally.
