# Company Select Split Screen Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the `/select-company` card grid with a fullscreen split layout — two gradient panels, click anywhere on a half to select that company.

**Architecture:** Pure CSS + HTML change. Two `<form>` elements each containing a full-height `<button>` panel sit side-by-side in a flex container that fills `100dvh`. No backend changes.

**Tech Stack:** Jinja2 template, plain CSS, existing Flask routes.

---

## File Map

| File | Action |
|------|--------|
| `app/static/css/style.css` | Replace old Company Select block (lines ~563-585) with new `.cs-*` classes; remove 3 dark-mode override lines (~742-745) |
| `app/templates/company_select.html` | Full rewrite — split layout with two form/button panels |

---

### Task 1: Replace CSS — Company Select block

**Files:**
- Modify: `app/static/css/style.css`

- [ ] **Step 1: Locate and replace the old Company Select CSS block**

Find this exact block in `app/static/css/style.css`:

```css
/* ── Company Select ──────────────────────────────────── */
.select-wrap {
  min-height: 100dvh; display: flex; align-items: center; justify-content: center;
  background: var(--sl-50);
}
.company-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(190px, 1fr));
  gap: .875rem; margin-top: 1.375rem;
}
.company-card {
  background: #FFF; border: 1px solid var(--sl-200);
  border-radius: var(--r-lg);
  padding: 1.5rem 1.25rem; text-align: center;
  cursor: pointer; color: var(--sl-900);
  transition: border-color .12s, box-shadow .12s;
}
.company-card:hover {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-surface);
}
.company-icon { font-size: 1.5rem; margin-bottom: .625rem; }
.company-name { font-size: .9375rem; font-weight: 600; color: var(--sl-900); }
.company-code { font-size: .75rem; color: var(--sl-500); margin-top: .1875rem; }
```

Replace it with:

```css
/* ── Company Select (Split Screen) ──────────────────── */
.cs-split {
  display: flex; height: 100dvh; width: 100vw; overflow: hidden; position: relative;
}
.cs-form { flex: 1; display: flex; }
.cs-badge {
  position: absolute; top: 0; left: 50%; transform: translateX(-50%);
  background: rgba(255,255,255,.08); backdrop-filter: blur(8px);
  border: 1px solid rgba(255,255,255,.12);
  color: rgba(255,255,255,.7); font-family: 'Figtree', sans-serif;
  font-size: .75rem; font-weight: 600; letter-spacing: .8px;
  padding: .5rem 1.25rem; border-radius: 0 0 .875rem .875rem;
  white-space: nowrap; z-index: 10; pointer-events: none;
}
.cs-panel {
  flex: 1; display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  gap: 1.25rem; padding: 2rem; cursor: pointer;
  border: none; outline: none; color: #fff;
  transition: filter .18s ease; position: relative;
}
.cs-panel:hover { filter: brightness(1.12); }
.cs-panel:hover .cs-hint { opacity: 1; transform: translateX(0); }
.cs-panel-smt { background: linear-gradient(150deg, #1a3252, #2d5a8e, #1e4d7a); }
.cs-panel-etf { background: linear-gradient(150deg, #2e1650, #5c2d91, #3d1a6e); }
.cs-divider { width: 1px; background: rgba(255,255,255,.12); flex-shrink: 0; }
.cs-icon { font-size: 4.5rem; line-height: 1; filter: drop-shadow(0 4px 16px rgba(0,0,0,.3)); }
.cs-name { font-size: 1.375rem; font-weight: 700; text-align: center; line-height: 1.3; letter-spacing: .2px; }
.cs-code {
  font-size: .8125rem; font-weight: 600; color: rgba(255,255,255,.6);
  background: rgba(255,255,255,.12); border: 1px solid rgba(255,255,255,.15);
  border-radius: .5rem; padding: .25rem .875rem; letter-spacing: 1px;
}
.cs-hint {
  position: absolute; bottom: 2.5rem;
  font-size: .8125rem; color: rgba(255,255,255,.5);
  opacity: 0; transform: translateX(-6px);
  transition: opacity .18s, transform .18s;
  letter-spacing: .5px; pointer-events: none;
}
@media (max-width: 600px) {
  .cs-split { flex-direction: column; }
  .cs-badge { display: none; }
  .cs-icon { font-size: 3.5rem; }
  .cs-name { font-size: 1.125rem; }
}
```

- [ ] **Step 2: Remove the dark-mode company select overrides**

Find and delete these 4 lines in `app/static/css/style.css` (in the Dark section near the bottom):

```css
/* Dark: company select */
[data-theme="dark"] .select-wrap { background: var(--bg); }
[data-theme="dark"] .company-card { background: var(--card); border-color: var(--border); color: var(--sl-900); }
[data-theme="dark"] .company-card:hover { border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-surface); }
```

Replace with nothing (delete entirely) — the new panels carry their own gradient regardless of theme.

- [ ] **Step 3: Commit**

```bash
git add app/static/css/style.css
git commit -m "style: replace company-select card grid with cs-split classes"
```

---

### Task 2: Rewrite company_select.html

**Files:**
- Modify: `app/templates/company_select.html`

- [ ] **Step 1: Replace the entire file content**

Replace the full content of `app/templates/company_select.html` with:

```html
<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Pilih Perusahaan — Finance Hub</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Figtree:wght@400;500;600;700&family=DM+Mono:wght@400;500&display=swap">
  <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
</head>
<body>
<div class="cs-badge">FINANCE HUB</div>
<div class="cs-split">
  {% for c in companies %}
  {% if not loop.first %}<div class="cs-divider"></div>{% endif %}
  <form method="POST" action="/select-company" class="cs-form">
    <button type="submit" name="company_id" value="{{ c.id }}"
            class="cs-panel cs-panel-{{ c.code | lower }}">
      <div class="cs-icon">{{ '🏢' if c.code == 'SMT' else '🏛️' }}</div>
      <div class="cs-name">{{ c.name }}</div>
      <div class="cs-code">{{ c.code }}</div>
      <div class="cs-hint">Pilih →</div>
    </button>
  </form>
  {% endfor %}
</div>
</body>
</html>
```

- [ ] **Step 2: Commit**

```bash
git add app/templates/company_select.html
git commit -m "feat: company select fullscreen split layout"
```

---

### Task 3: Run existing tests

**Files:**
- Test: `app/tests/test_dashboard.py`

- [ ] **Step 1: Run the dashboard test suite**

```bash
cd app && python -m pytest tests/test_dashboard.py -v
```

Expected output — all 5 tests pass:

```
tests/test_dashboard.py::test_dashboard_redirect_without_login PASSED
tests/test_dashboard.py::test_select_company_page_requires_login PASSED
tests/test_dashboard.py::test_select_company_after_login PASSED
tests/test_dashboard.py::test_dashboard_after_company_selection PASSED
tests/test_dashboard.py::test_dashboard_shows_etf_stats PASSED
```

`test_select_company_after_login` checks `b"Pilih" in resp.data` — this still passes because `<div class="cs-hint">Pilih →</div>` is in the new template.

- [ ] **Step 2: Open the app and verify visually**

Navigate to `http://localhost:8080/select-company`. Confirm:
- Two full-height colored panels fill the screen
- "FINANCE HUB" badge appears centered at the top
- Hovering either panel brightens it and shows "Pilih →" at the bottom
- Clicking either panel lands on the dashboard with the correct company selected
- On narrow viewport (≤600px) the panels stack top/bottom
