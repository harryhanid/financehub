# FLOW Company Select Branching Transition Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the generic emoji/gradient company-select cards with a page that continues the login page's ambient ledger chart — the two chart lines branch toward each company panel — tied to the login page via the View Transitions API for a soft cross-page glide.

**Architecture:** `templates/company_select.html` becomes a self-contained styled document (like `login.html` already is), reusing the same dark-navy token set, noise texture, and breathing orbs, but with its own branching SVG (two diverging bezier paths instead of login's flat horizontal ones) and two glass selection panels. JS toggles hover/click state via body classes that CSS reads to brighten/dim each path. `login.html` gets a matching `@view-transition` rule and shared `view-transition-name`s so supporting browsers glide the wordmark/chart between the two pages instead of a hard cut; unsupported browsers silently fall back to normal navigation.

**Tech Stack:** Flask + Jinja2, vanilla CSS (custom properties, `@view-transition`), vanilla JS, inline SVG/SMIL (`animateMotion`), pytest + Flask test client.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-07-27-flow-company-select-branching-transition-design.md`
- Scope is **login → company select only**. No change to `/select-company` POST route logic, session handling, `config.COMPANIES` data, the Dashboard, or any page reachable after company selection.
- Color mapping is fixed: Sinar Mas Tjipta (`company_id=1`, code `SMT`) = cobalt/primary line `#5B8CFF`. Eka Tjipta Foundation (`company_id=2`, code `ETF`) = cyan/shadow line `#22D3EE`.
- The native `<form method="POST" action="/select-company">` / `<button type="submit" name="company_id" value="{{ c.id }}">` structure must be preserved — only its visual treatment changes. No client-side routing, no fetch-based submission.
- `prefers-reduced-motion: reduce` must freeze the shadow-breathe animation, hide the traveling dots, and skip the click-flourish delay (submit immediately) — same policy already established on `login.html`.
- View Transitions is progressive enhancement only — no polyfill, no browser-detection branching in code; unsupported browsers get a plain instant navigation for free.

---

### Task 1: Rewrite company_select.html with the branching ambient chart

**Files:**
- Modify: `C:\Financehub\app\templates\company_select.html` (full rewrite)
- Modify: `C:\Financehub\app\static\css\style.css:928-975` (delete the old `.cs-*` rules — dead once this page is self-contained)
- Modify: `C:\Financehub\app\tests\test_branding.py:52-59` (`test_company_select_page_shows_flow_badge` references the removed `.cs-badge` markup)
- Test: `C:\Financehub\app\tests\test_branding.py` (updated in place)

**Interfaces:**
- Consumes: `companies` (list of `{"id": int, "code": str, "name": str}`, from `config.COMPANIES` via `modules/dashboard/routes.py:select_company()` — unchanged), `company_name` (optional, from `get_ctx()` — unchanged).
- Produces: nothing new consumed by later tasks except the `.wordmark`/`.chart-ambient` class names and DOM shape that Task 2 targets with `view-transition-name`.

- [ ] **Step 1: Write the failing test**

Replace `test_company_select_page_shows_flow_badge` (lines 52-59) in `tests/test_branding.py`:

```python
def test_company_select_page_shows_flow_branding(client):
    login(client)
    resp = client.get("/select-company")
    html = resp.data.decode()
    assert "<title>Pilih Perusahaan — FLOW</title>" in html
    assert "FINANCE HUB" not in html
    assert 'rel="icon"' in html
    assert '<span class="wordmark-text">FLOW</span>' in html


def test_company_select_page_has_a_panel_per_company(client):
    login(client)
    resp = client.get("/select-company")
    html = resp.data.decode()
    assert 'class="company-panel company-panel-smt"' in html
    assert 'class="company-panel company-panel-etf"' in html
    assert 'name="company_id" value="1"' in html
    assert 'name="company_id" value="2"' in html
    assert "Sinar Mas Tjipta" in html
    assert "Eka Tjipta Foundation" in html
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_branding.py -v -k company_select`
Expected: FAIL (2 failures — old `.cs-badge`/`.cs-panel` markup doesn't match the new assertions yet)

- [ ] **Step 3: Delete the old Company Select CSS**

In `static/css/style.css`, delete lines 928-975 (the entire `/* ── Company Select (Split Screen) ── */` section, from that comment through the closing `}` of its `@media (max-width: 600px)` block):

```css
/* ── Company Select (Split Screen) ──────────────────── */
.cs-split {
  display: flex; height: 100dvh; width: 100vw; overflow: hidden; position: relative;
}
.cs-form { flex: 1; display: flex; }
.cs-badge {
  position: absolute; top: 0; left: 50%; transform: translateX(-50%);
  background: rgba(255,255,255,.08); -webkit-backdrop-filter: blur(8px); backdrop-filter: blur(8px);
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
.cs-panel:focus-visible { outline: 3px solid rgba(255,255,255,.6); outline-offset: -4px; }
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

Leave the blank line that follows (before `/* ── Responsive ── */`) as the section separator.

- [ ] **Step 4: Rewrite company_select.html**

Replace the entire contents of `templates/company_select.html` with:

```html
<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Pilih Perusahaan — FLOW</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Figtree:wght@400;500;600;700;800&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
  <link rel="icon" type="image/svg+xml" href="{{ url_for('static', filename='favicon.svg') }}">
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    :root {
      --bg:        #06080F;
      --surface:   #0F1220;
      --ink:       #F0EEF8;
      --ink-2:     #9896B0;
      --ink-3:     #4E4D63;
      --accent:    #5B8CFF;
      --accent-2:  #22D3EE;
      --font:      'Figtree', system-ui, sans-serif;
      --mono:      'DM Mono', monospace;
    }

    html, body {
      height: 100%;
      background: var(--bg);
      font-family: var(--font);
      color: var(--ink);
      -webkit-font-smoothing: antialiased;
    }

    /* ── Noise ── */
    body::before {
      content: '';
      position: fixed; inset: 0; z-index: 0; pointer-events: none;
      background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.045'/%3E%3C/svg%3E");
      opacity: 0.5;
    }

    /* ── Glow orbs (shared with login) ── */
    .orb {
      position: fixed; pointer-events: none;
      border-radius: 9999px; filter: blur(120px); z-index: 0;
    }
    .orb-1 {
      width: 700px; height: 500px;
      top: -200px; left: 50%; transform: translateX(-50%);
      background: radial-gradient(ellipse, rgba(79,106,255,0.11) 0%, transparent 65%);
      animation: breathe-1 12s ease-in-out infinite;
    }
    .orb-2 {
      width: 400px; height: 400px;
      bottom: -100px; right: 10%;
      background: radial-gradient(ellipse, rgba(123,143,255,0.07) 0%, transparent 65%);
      animation: breathe-2 14s ease-in-out infinite -4s;
    }
    @keyframes breathe-1 {
      0%, 100% { transform: translateX(-50%) scale(1); opacity: 1; }
      50%      { transform: translateX(-50%) scale(1.08); opacity: .85; }
    }
    @keyframes breathe-2 {
      0%, 100% { transform: scale(1); opacity: 1; }
      50%      { transform: scale(1.1); opacity: .8; }
    }

    /* ── Branching ambient chart ── */
    .chart-ambient {
      position: fixed; inset: 0; z-index: 0;
      pointer-events: none;
      width: 100%; height: 100%;
    }
    .chart-primary, .chart-shadow {
      transition: stroke-width .3s ease, opacity .3s ease, filter .3s ease;
    }
    .chart-shadow { animation: chart-shadow-breathe 12s ease-in-out infinite; }
    @keyframes chart-shadow-breathe {
      0%, 100% { opacity: .35; }
      50%      { opacity: .18; }
    }
    @keyframes land-pulse {
      0%, 100% { opacity: .5; transform: scale(1); }
      50%      { opacity: 1; transform: scale(1.6); }
    }

    /* Hover: brighten the hovered company's line, dim the other */
    body.branch-hover-smt .chart-primary { stroke-width: 3.2; opacity: 1; }
    body.branch-hover-smt .chart-shadow  { opacity: .18; }
    body.branch-hover-etf .chart-shadow  { stroke-width: 2.4; opacity: 1; }
    body.branch-hover-etf .chart-primary { opacity: .5; }

    /* Click flourish: brief brighten + glow before the form submits */
    body.branch-firing-smt .chart-primary {
      stroke-width: 4; filter: drop-shadow(0 0 6px rgba(91,140,255,.8));
    }
    body.branch-firing-etf .chart-shadow {
      stroke-width: 3; filter: drop-shadow(0 0 6px rgba(34,211,238,.8));
    }

    @media (prefers-reduced-motion: reduce) {
      .orb, .wordmark-icon, .wordmark, .wordmark-tagline, .company-row,
      .chart-shadow, .chart-primary, .chart-shadow {
        animation: none !important;
        opacity: 1 !important;
      }
      .chart-dot, .chart-dot-glow, .company-landing-dot { display: none; }
    }

    /* ── Wordmark (matches login.html for View Transitions continuity) ── */
    .page {
      position: relative; z-index: 1;
      min-height: 100dvh;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 2rem 1.5rem;
      gap: 2.5rem;
    }

    .wordmark {
      display: flex;
      align-items: center;
      gap: .75rem;
      animation: rise .5s cubic-bezier(.22,.72,0,1) .1s both;
    }

    .wordmark-icon {
      width: 34px; height: 34px;
      border-radius: 10px;
      background: linear-gradient(135deg, var(--accent), var(--accent-2));
      display: flex; align-items: center; justify-content: center;
      box-shadow: 0 0 24px rgba(91,140,255,0.22), inset 0 1px 1px rgba(255,255,255,0.2);
      flex-shrink: 0;
    }
    .wordmark-icon svg { width: 16px; height: 16px; stroke: #fff; fill: none; stroke-width: 2; stroke-linecap: round; }
    .wordmark-text { font-size: .875rem; font-weight: 700; letter-spacing: -.01em; color: var(--ink); }
    .wordmark-pill {
      padding: .2rem .55rem; border-radius: 9999px;
      background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.08);
      font-size: .55rem; font-family: var(--mono); letter-spacing: .15em;
      text-transform: uppercase; color: var(--ink-3);
    }

    @keyframes rise {
      from { opacity: 0; transform: translateY(18px); }
      to   { opacity: 1; transform: translateY(0); }
    }

    .page-title {
      font-size: 1rem; font-weight: 600; color: var(--ink-2);
      text-align: center;
      animation: rise .5s cubic-bezier(.22,.72,0,1) .2s both;
    }

    /* ── Company panels ── */
    .company-row {
      display: flex; flex-direction: column; gap: 1rem;
      width: min(720px, 100%);
      animation: rise .6s cubic-bezier(.22,.72,0,1) .32s both;
    }
    @media (min-width: 640px) {
      .company-row { flex-direction: row; }
    }

    .company-form { flex: 1; display: flex; }

    .company-panel {
      flex: 1; width: 100%;
      background: rgba(255,255,255,0.03);
      border: 1px solid rgba(255,255,255,0.08);
      border-radius: 20px;
      padding: 2rem 1.5rem;
      display: flex; flex-direction: column; align-items: center; gap: .75rem;
      cursor: pointer; color: inherit; font-family: inherit;
      transition: border-color .2s ease, background .2s ease;
    }
    .company-panel:hover { background: rgba(255,255,255,0.05); }
    .company-panel:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
    .company-panel-smt:hover, .company-panel-smt:focus-visible { border-color: rgba(91,140,255,.4); }
    .company-panel-etf:hover, .company-panel-etf:focus-visible { border-color: rgba(34,211,238,.4); }

    .company-landing-dot {
      width: 6px; height: 6px; border-radius: 50%;
      animation: land-pulse 2s ease-in-out infinite;
    }
    .company-panel-smt .company-landing-dot { background: #5B8CFF; box-shadow: 0 0 10px #5B8CFF; }
    .company-panel-etf .company-landing-dot { background: #22D3EE; box-shadow: 0 0 10px #22D3EE; animation-delay: .5s; }

    .company-name { font-size: 1rem; font-weight: 700; color: var(--ink); text-align: center; }
    .company-code {
      font-size: .625rem; font-family: var(--mono); letter-spacing: .1em;
      text-transform: uppercase; color: var(--ink-3);
    }
  </style>
</head>
<body>
  <div class="orb orb-1"></div>
  <div class="orb orb-2"></div>

  <svg class="chart-ambient" viewBox="0 0 1600 700" preserveAspectRatio="xMidYMid slice" fill="none" aria-hidden="true">
    <path class="chart-primary" d="M-100,120 C300,160 500,110 700,180 C820,220 850,280 700,340 C500,415 350,460 300,560 C270,610 290,650 340,680"
      stroke="#5B8CFF" stroke-width="2.2" stroke-linecap="round"/>
    <path class="chart-shadow" d="M-100,180 C300,220 550,160 750,220 C900,260 950,320 850,380 C1050,430 1250,480 1280,580 C1300,625 1280,655 1230,680"
      stroke="#22D3EE" stroke-width="1.2" opacity="0.35"/>
    <circle class="chart-dot-glow" r="9" fill="#5B8CFF" opacity="0.25">
      <animateMotion dur="7s" repeatCount="indefinite" path="M-100,120 C300,160 500,110 700,180 C820,220 850,280 700,340 C500,415 350,460 300,560 C270,610 290,650 340,680"/>
    </circle>
    <circle class="chart-dot" r="4" fill="#5B8CFF">
      <animateMotion dur="7s" repeatCount="indefinite" path="M-100,120 C300,160 500,110 700,180 C820,220 850,280 700,340 C500,415 350,460 300,560 C270,610 290,650 340,680"/>
    </circle>
    <circle class="chart-dot-glow" r="7.5" fill="#22D3EE" opacity="0.22">
      <animateMotion dur="7s" repeatCount="indefinite" path="M-100,180 C300,220 550,160 750,220 C900,260 950,320 850,380 C1050,430 1250,480 1280,580 C1300,625 1280,655 1230,680"/>
    </circle>
    <circle class="chart-dot" r="3.5" fill="#22D3EE">
      <animateMotion dur="7s" repeatCount="indefinite" path="M-100,180 C300,220 550,160 750,220 C900,260 950,320 850,380 C1050,430 1250,480 1280,580 C1300,625 1280,655 1230,680"/>
    </circle>
  </svg>

  <div class="page">
    <div class="wordmark">
      <div class="wordmark-icon">
        <svg viewBox="0 0 16 16" fill="none">
          <path d="M1.5 10.2c1.6-3.2 3.6-3.2 5 0s3.4 3.2 5 0s2.5-4 2.5-4" stroke="#fff" stroke-width="1.5" stroke-linecap="round"/>
          <path d="M1.5 5.8c1.6-3.2 3.6-3.2 5 0s3.4 3.2 5 0" stroke="#fff" stroke-width="1" stroke-linecap="round" opacity="0.55"/>
        </svg>
      </div>
      <span class="wordmark-text">FLOW</span>
      <span class="wordmark-pill">Internal</span>
    </div>

    <div class="page-title">Pilih perusahaan untuk melanjutkan</div>

    <div class="company-row">
      {% for c in companies %}
      <form method="POST" action="/select-company" class="company-form">
        <button type="submit" name="company_id" value="{{ c.id }}"
                class="company-panel company-panel-{{ c.code | lower }}"
                data-code="{{ c.code }}">
          <span class="company-landing-dot"></span>
          <span class="company-name">{{ c.name }}</span>
          <span class="company-code">{{ c.code }}</span>
        </button>
      </form>
      {% endfor %}
    </div>
  </div>

<script>
(function () {
  var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  document.querySelectorAll('.company-panel').forEach(function (btn) {
    var code = btn.dataset.code.toLowerCase();

    btn.addEventListener('mouseenter', function () { document.body.classList.add('branch-hover-' + code); });
    btn.addEventListener('mouseleave', function () { document.body.classList.remove('branch-hover-' + code); });
    btn.addEventListener('focus', function () { document.body.classList.add('branch-hover-' + code); });
    btn.addEventListener('blur', function () { document.body.classList.remove('branch-hover-' + code); });

    if (reduceMotion) return;

    btn.addEventListener('click', function (e) {
      if (btn.dataset.firing) return;
      e.preventDefault();
      btn.dataset.firing = '1';
      document.body.classList.add('branch-firing-' + code);
      setTimeout(function () { btn.form.requestSubmit(btn); }, 180);
    });
  });
})();
</script>
</body>
</html>
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_branding.py -v`
Expected: PASS (all tests in this file pass)

- [ ] **Step 6: Run the full test suite to check for regressions**

Run: `pytest tests/ -q`
Expected: no new failures beyond the existing pre-existing baseline (Windows SQLite file-lock flakiness when running the whole suite together — see `FinanceHub - Known Issues.md` if a baseline count is needed for comparison). Nothing in this change touches routes, sessions, or any file other than the two listed above plus the test file, so a new failure here means something was missed — investigate rather than assume pre-existing.

- [ ] **Step 7: Commit**

```bash
git add app/templates/company_select.html app/static/css/style.css app/tests/test_branding.py
git commit -m "feat: replace company-select cards with branching ambient chart"
```

---

### Task 2: View Transitions API continuity between login and company select

**Files:**
- Modify: `C:\Financehub\app\templates\login.html` (add `@view-transition` + `view-transition-name`s)
- Modify: `C:\Financehub\app\templates\company_select.html` (add `@view-transition` + matching `view-transition-name`s)

**Interfaces:**
- Consumes: `.wordmark` and `.chart-ambient` class names/DOM structure from Task 1 (company_select.html) and the pre-existing equivalents in login.html.

- [ ] **Step 1: Add the View Transition opt-in to login.html**

In `templates/login.html`, inside the `<style>` block, directly after the `:root { ... }` block (before the `html, body { ... }` rule), add:

```css
    @view-transition {
      navigation: auto;
    }
```

- [ ] **Step 2: Tag login.html's shared elements**

In `templates/login.html`, add `view-transition-name` to the wordmark and chart rules. Replace:

```css
    /* ── Top wordmark ── */
    .wordmark {
      display: flex;
      align-items: center;
      gap: .75rem;
      margin-bottom: .6rem;
      animation: rise .5s cubic-bezier(.22,.72,0,1) .32s both;
    }
```

with:

```css
    /* ── Top wordmark ── */
    .wordmark {
      display: flex;
      align-items: center;
      gap: .75rem;
      margin-bottom: .6rem;
      animation: rise .5s cubic-bezier(.22,.72,0,1) .32s both;
      view-transition-name: flow-wordmark;
    }
```

Replace:

```css
    /* ── Ambient ledger chart (full-page, behind everything) ── */
    .chart-ambient {
      position: fixed; inset: 0; z-index: 0;
      pointer-events: none;
      width: 100%; height: 100%;
    }
```

with:

```css
    /* ── Ambient ledger chart (full-page, behind everything) ── */
    .chart-ambient {
      position: fixed; inset: 0; z-index: 0;
      pointer-events: none;
      width: 100%; height: 100%;
      view-transition-name: flow-ambient;
    }
```

- [ ] **Step 3: Add the View Transition opt-in and matching names to company_select.html**

In `templates/company_select.html`, inside the `<style>` block, directly after the `:root { ... }` block, add:

```css
    @view-transition {
      navigation: auto;
    }
```

Then add `view-transition-name: flow-wordmark;` to the `.wordmark` rule and `view-transition-name: flow-ambient;` to the `.chart-ambient` rule, the same way as Step 2 above (same property, same values, matching the login page so the browser treats them as the same persistent element).

- [ ] **Step 4: Verify both pages still render (no CSS syntax errors)**

Run: `pytest tests/test_branding.py -v`
Expected: PASS (all tests still pass — `@view-transition` and `view-transition-name` are additive CSS properties; browsers that don't understand `@view-transition` simply ignore the unknown at-rule, and `view-transition-name` on browsers without View Transitions support is a no-op property, so nothing here can break existing assertions)

- [ ] **Step 5: Commit**

```bash
git add app/templates/login.html app/templates/company_select.html
git commit -m "feat: add View Transitions continuity between login and company select"
```

---

## Self-Review

**Spec coverage:**
- Branching chart replacing flat cards, cobalt→SMT/cyan→ETF mapping, hover brighten/dim, click flourish + delayed submit → Task 1.
- View Transitions API + shared `view-transition-name`s, graceful fallback → Task 2.
- Reduced motion (freeze breathe/hide dots/skip flourish delay) → Task 1 (CSS media query + JS early-return).
- Old `.cs-*` CSS cleanup, existing test update → Task 1.
- Non-goals (no route/session change, no Dashboard change, no reusable transition framework) → nothing in either task touches those areas.

**Placeholder scan:** No TBD/TODO; every step has complete file content or exact before/after CSS blocks.

**Type/consistency check:** `data-code="{{ c.code }}"` (Task 1) is read by both the hover and click JS handlers via `btn.dataset.code.toLowerCase()`, producing `smt`/`etf` consistently used in `branch-hover-*`/`branch-firing-*` class names and the CSS selectors that target them. `.wordmark`/`.chart-ambient` class names in Task 1's company_select.html rewrite match exactly what Task 2 selects in both files.
