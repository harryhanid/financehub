# FLOW Company Select to Dashboard Transition Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the seamless-flow narrative one hop further — the FLOW wordmark morphs from company-select into Dashboard's navbar via View Transitions, and Dashboard follows dark mode on a genuine first visit.

**Architecture:** Two small, independent additions: (1) `company_select.html`'s existing click-handling JS gets one unconditional `localStorage` write so Dashboard's *already-existing* theme-detection script in `base.html` picks up dark mode on next load, with zero changes to `base.html` itself; (2) `dashboard/index.html` gets its own scoped `{% block head %}` with the `@view-transition` opt-in and a `view-transition-name` matching company-select's existing `.wordmark` name — scoped to this one template so no other module's navigation is affected.

**Tech Stack:** Flask + Jinja2, vanilla JS, CSS View Transitions API (`@view-transition`, `view-transition-name`).

## Global Constraints

- Spec: `docs/superpowers/specs/2026-07-28-flow-company-select-to-dashboard-transition-design.md`
- Never override a theme the user already explicitly chose — only set `fh-theme` to `'dark'` when `localStorage.getItem('fh-theme')` is falsy (unset).
- The dark-mode-continuity write must run for every click on a company panel, including when `prefers-reduced-motion: reduce` is set — the existing click-flourish listener in `company_select.html` is skipped entirely under reduced motion (its whole registration is behind an early `if (reduceMotion) return;`), so the new write must NOT be placed inside that same gated listener.
- `@view-transition` and `view-transition-name: flow-wordmark` go **only** inside `dashboard/index.html`'s own `{% block head %}` — never into `base.html` or `static/css/style.css`. This is the only thing that keeps the transition scoped to this one page pair instead of leaking into every other module's navigation.
- No ambient chart, accent-flash, or other new visual element on Dashboard.
- No change to `/select-company` POST route logic or session handling.

---

### Task 1: Dark-mode continuity + wordmark View Transition

**Files:**
- Modify: `C:\Financehub\app\templates\company_select.html:259-280` (the existing `<script>` block)
- Modify: `C:\Financehub\app\templates\dashboard\index.html:1-3` (add a `{% block head %}`)
- Test: `C:\Financehub\app\tests\test_dashboard.py` (new test)

**Interfaces:**
- This task doesn't produce anything a later task consumes — it's the only task in this plan.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_dashboard.py`:

```python
def test_dashboard_page_opts_into_view_transitions(client):
    login(client)
    select_etf(client)
    resp = client.get("/dashboard")
    html = resp.data.decode()
    assert "@view-transition" in html
    assert "view-transition-name: flow-wordmark" in html
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_dashboard.py -v -k view_transitions`
Expected: FAIL (dashboard/index.html has no `{% block head %}` yet, so neither string appears in the response)

- [ ] **Step 3: Add the dark-mode-continuity write to company_select.html**

In `templates/company_select.html`, replace:

```html
    btn.addEventListener('mouseenter', function () { document.body.classList.add('branch-hover-' + code); });
    btn.addEventListener('mouseleave', function () { document.body.classList.remove('branch-hover-' + code); });
    btn.addEventListener('focus', function () { document.body.classList.add('branch-hover-' + code); });
    btn.addEventListener('blur', function () { document.body.classList.remove('branch-hover-' + code); });

    if (reduceMotion) return;
```

with:

```html
    btn.addEventListener('mouseenter', function () { document.body.classList.add('branch-hover-' + code); });
    btn.addEventListener('mouseleave', function () { document.body.classList.remove('branch-hover-' + code); });
    btn.addEventListener('focus', function () { document.body.classList.add('branch-hover-' + code); });
    btn.addEventListener('blur', function () { document.body.classList.remove('branch-hover-' + code); });

    // Runs unconditionally (not gated by reduceMotion below) -- Dashboard's
    // existing theme-detection script in base.html reads this on next load.
    // Never overrides a theme the user already explicitly chose.
    btn.addEventListener('click', function () {
      if (!localStorage.getItem('fh-theme')) localStorage.setItem('fh-theme', 'dark');
    });

    if (reduceMotion) return;
```

- [ ] **Step 4: Add the scoped View Transitions head block to dashboard/index.html**

In `templates/dashboard/index.html`, replace:

```html
{% extends "base.html" %}
{% block title %}Dashboard{% endblock %}
{% block content %}
```

with:

```html
{% extends "base.html" %}
{% block title %}Dashboard{% endblock %}
{% block head %}
<style>
  /* Scoped to this template only -- do not move to base.html or
     static/css/style.css. Keeps the View Transition limited to
     company-select -> dashboard, not every module navigation. */
  @view-transition {
    navigation: auto;
  }
  .navbar-brand {
    view-transition-name: flow-wordmark;
  }
</style>
{% endblock %}
{% block content %}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_dashboard.py -v -k view_transitions`
Expected: PASS

- [ ] **Step 6: Run the full branding + dashboard test suites to check for regressions**

Run: `pytest tests/test_dashboard.py tests/test_branding.py -v`
Expected: all pass, no new failures. This change touches no route logic, so nothing outside these two test files can be affected.

- [ ] **Step 7: Commit**

```bash
git add app/templates/company_select.html app/templates/dashboard/index.html app/tests/test_dashboard.py
git commit -m "feat: continue seamless flow into Dashboard (wordmark morph + dark-mode-on-first-visit)"
```

---

## Self-Review

**Spec coverage:**
- Dark/light continuity (unconditional write, never overrides existing choice) → Step 3.
- Wordmark-only visual continuation via View Transitions → Step 4.
- Narrow scoping to `dashboard/index.html` only, no `base.html`/`style.css` change → Step 4 (explicitly commented in the code itself as a guardrail against future drift).
- No ambient chart/accent-flash/other new element → nothing in this plan adds one.
- No route/session changes → nothing in this plan touches `modules/dashboard/routes.py`.

**Placeholder scan:** No TBD/TODO; every step has complete before/after code.

**Type/consistency check:** `view-transition-name: flow-wordmark` in Step 4 matches the name already present on `.wordmark` in `company_select.html` (unchanged by this plan, confirmed in the spec's Architecture section) — both sides of the transition use the identical string.
