# FinanceHub Dashboard — Module Tab Bar

**Goal:** Add a visible tab bar of the 7 active modules to the Dashboard page, so users can jump into a module directly instead of relying only on the Alt+K command palette.

**Architecture:** Pure server-rendered addition — no backend logic, no new CSS, no changes to `base.html`/`app.js`/command palette. Reuses the existing `.tabs` / `.tab-btn` / `.page-toolbar` styles already used by Beasiswa (`templates/beasiswa/index.html`).

**Non-goal:** This does NOT bring back the old global navbar module links. Those were deliberately removed 2026-07-02 (`2026-07-02-command-palette-nav-design.md`) to fix navbar overflow, replaced by the command palette (Alt+K) and the per-page title dropdown (`initTitleDropdown()` in `app.js`, unaffected by this change). This tab bar is scoped to the Dashboard page only.

---

## Scope

7 active modules, in this order:

| Tab label | Endpoint | URL |
|---|---|---|
| Dashboard | `dashboard.index` | `/dashboard` |
| Beasiswa | `beasiswa.index` | `/beasiswa/` |
| Payment Approval Memo | `payment_memo.index` | `/payment-memo/` |
| Payment Application | `etf_payment_application.index` | `/etf-payment-application/` |
| Budget | `budget.index` | `/budget/` |
| Bank | `bank.index` | `/bank/` |
| Users | `users.index` | `/users/` |

- "Dashboard" tab always renders with `.active` class (current page).
- Coming-soon modules (Account Payable, Advance, Petty Cash, Sponsorship) are **excluded** — still reachable via Alt+K only, same as today.
- Tabs are plain `<a>` navigation links (no client-side panel switching) — clicking one navigates to that module's page, same pattern as the existing "Sahabat ETF ↗" link inside Beasiswa's tab row.

---

## Implementation

### `modules/dashboard/routes.py`

In the `index()` view, build a small list and pass it to the template:

```python
DASHBOARD_TABS = [
    ("Dashboard",               "dashboard.index"),
    ("Beasiswa",                "beasiswa.index"),
    ("Payment Approval Memo",   "payment_memo.index"),
    ("Payment Application",     "etf_payment_application.index"),
    ("Budget",                  "budget.index"),
    ("Bank",                    "bank.index"),
    ("Users",                   "users.index"),
]
```

Pass to template as:

```python
modules=[{"name": name, "url": url_for(endpoint)} for name, endpoint in DASHBOARD_TABS]
```

Using `url_for()` (not hardcoded strings) means the tab bar can't drift out of sync if a route path ever changes.

### `templates/dashboard/index.html`

Wrap the existing `<h1 class="page-title">Dashboard</h1>` in the same `.page-header` / `.page-toolbar` + `.tabs` structure Beasiswa uses:

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

No new CSS — `.tabs`, `.tab-btn`, `.tab-btn.active`, `.page-toolbar` already exist in `style.css` (used by Beasiswa) and already wrap on narrow viewports (`flex-wrap: wrap`), so no overflow risk.

---

## Files Changed

| File | Change |
|---|---|
| `app/modules/dashboard/routes.py` | Add `DASHBOARD_TABS` list, build `modules` context var in `index()`, pass to template |
| `app/templates/dashboard/index.html` | Wrap page title in `.page-toolbar`, add `.tabs`/`.tab-btn` row from `modules` |

---

## Testing

No new backend logic to unit test (static list + `url_for`, no DB/conditionals). Verify manually against the running dev server (`localhost:8081`):
- Dashboard shows 7 tabs, "Dashboard" highlighted active
- Each tab navigates to the correct module page
- Layout holds in both light and dark mode (reuses existing CSS vars, should be automatic)
- Layout wraps cleanly on a narrow viewport instead of overflowing
