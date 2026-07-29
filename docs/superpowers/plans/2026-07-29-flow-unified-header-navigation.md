# FLOW Unified Header Navigation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Collapse FLOW's two stacked navigation rows (global navbar + per-module sub-nav) into one context-sensitive header row, per `docs/superpowers/specs/2026-07-29-flow-unified-header-navigation-design.md`.

**Architecture:** `base.html`'s navbar grows a new Jinja branch: on Dashboard it renders the existing flat module list (State A, unchanged); inside any other module it renders a `{{ module_label }} ▾` dropdown trigger (reusing `nav_modules`, no new data source) followed by a new `{% block module_tabs %}` that each module template overrides with its own existing tab markup, unchanged in mechanism (JS-panel buttons, query-param links, or plain links) — only its *location* moves. Each module's Filter/Full Screen toggle buttons relocate from the old header row into a new `.fh-content-toolbar` row in the page content, directly below the header. The whole migration is staged behind a transitional `use_unified_header` context flag so each task ships independently without regressing not-yet-migrated modules; the final task removes the flag once every route sets it.

**Tech Stack:** Flask + Jinja2 templates, vanilla JS (no build step), existing `style.css`/`app.js`. No new dependencies.

## Global Constraints

- Presentation-layer only — no business logic, route behavior, or data changes (spec "What does not change").
- Reuse the existing `nav_modules` context processor / `DASHBOARD_TABS` list as the only data source for both the flat list and the dropdown — do not introduce a second module registry (spec "Module-switch dropdown").
- The Alt+K command palette (`initCommandPalette`, `FH_MODULES`), the Alt+←/→ tab-navigation shortcut (`pressTabStep`), and every `wrong_company` / company-gating guard must keep working identically — untouched by this migration except where explicitly noted (spec "What does not change").
- No tabs are ever hidden behind a "More" menu — horizontal scroll with a trailing fade gradient instead, reusing `.navbar-menu`'s existing `overflow-x:auto` (spec "Scroll & overflow").
- Company name moves to the right of the navbar; the "Cari modul" button becomes icon-only (tooltip still reads "Cari modul (Alt+K)") (spec "State A" example, "Alt+K / command palette").
- **Focus Mode change (approved by user during plan-writing, not in the original spec):** today, entering Focus Mode (`body.fh-focus`) hides the whole navbar but keeps each module's own title+tabs row visible (it lives in page content). Once tabs move into the navbar, hiding the whole navbar would hide tabs too. Approved fix: Focus Mode keeps the navbar visible and instead hides only `.navbar-right` (company/user/theme/logout) — the module dropdown + tabs stay visible and usable while in Focus Mode.
- **Shared checkout hazard:** as of plan-writing, `app/templates/bank/index.html`, `app/templates/budget/carryover.html`, `app/templates/budget/realisasi_list.html`, `app/templates/etf_payment_application/index.html`, and `app/templates/users/index.html` have uncommitted changes from a concurrent session in this same working tree. Before editing any of these files, run `git status --porcelain -- <file>` and `git diff -- <file>`. If unrelated WIP overlaps the lines you need to change, hand-extract your intended hunk into a standalone patch and stage it with `git apply --check --cached` then `git apply --cached` (never a blind `git add` on these files) — do not stash, checkout, or otherwise discard the other session's work.
- Never run `git add -A` / `git add .` in this repository — stage files by exact path only.

## File Structure

- `app/templates/base.html` — grows the navbar's Jinja branching (State A/B/C) and a `navbar-right` wrapper; gains `{% block module_tabs %}`.
- `app/static/css/style.css` — new navbar-right, module-switch-dropdown, header-tab-fade, and `.fh-content-toolbar` rules; reworked Focus Mode rules.
- `app/static/js/app.js` — new `initModuleSwitchDropdown()` and `initHeaderTabFade()`, registered in the existing `DOMContentLoaded` listener.
- `app/modules/dashboard/routes.py`, `app/modules/beasiswa/routes.py`, `app/modules/payment_memo/routes.py`, `app/modules/etf_payment_application/routes.py`, `app/modules/bank/routes.py`, `app/modules/users/routes.py`, `app/modules/sponsorship/routes.py`, `app/modules/budget/routes.py` — each gains `use_unified_header=True` on its `render_template()` call(s) as that module migrates.
- `app/templates/beasiswa/index.html`, `app/templates/payment_memo/index.html`, `app/templates/etf_payment_application/index.html`, `app/templates/bank/index.html`, `app/templates/sponsorship/dashboard.html`, `app/templates/sponsorship/input.html`, `app/templates/sponsorship/data.html`, `app/templates/sponsorship/report.html`, `app/templates/budget/dashboard.html`, `app/templates/budget/master_list.html`, `app/templates/budget/realisasi_list.html`, `app/templates/budget/carryover.html` — each overrides `{% block module_tabs %}` with its existing tab markup (relocated, not rewritten) and moves its Filter/Full Screen actions into a new `.fh-content-toolbar` row.
- `app/templates/users/index.html` — no template edit needed (State C: no tabs to relocate); only its route gains the flag.

---

### Task 1: Shared header foundation (base.html + CSS + JS + Dashboard flag)

**Files:**
- Modify: `app/templates/base.html:18-68`
- Modify: `app/static/css/style.css` (several regions, see steps)
- Modify: `app/static/js/app.js:241` (add two functions), `app/static/js/app.js:532-541` (register them)
- Modify: `app/modules/dashboard/routes.py:91-92`

**Interfaces:**
- Produces: `{% block module_tabs %}{% endblock %}` in `base.html`'s navbar — every later task overrides this in its own template.
- Produces: `use_unified_header` context flag (Jinja, default falsy) — every later task's route sets `use_unified_header=True`.
- Produces: CSS classes `.navbar-right`, `.fh-mod-switch`, `.fh-mod-trigger`, `.fh-mod-chevron`, `.fh-mod-dd`, `.fh-mod-dd-item`, `.fh-content-toolbar`, `.navbar-menu.fh-overflow` — reused by every later task.
- Consumes: existing `nav_modules` (list of `{name, url, key}`) and `active_page` (string), both already injected into every template today.

- [x] **Step 1: Replace the navbar body in `base.html`**

Replace this block (current lines 18-68, from `<nav class="navbar">` through `</nav>`):

```html
<nav class="navbar">
  <a class="navbar-brand" href="/">
    <span class="navbar-brand-icon">
      <svg width="18" height="18" viewBox="0 0 20 20" fill="none">
        <defs>
          <linearGradient id="flow-mark-grad" x1="0" y1="0" x2="20" y2="20" gradientUnits="userSpaceOnUse">
            <stop offset="0" style="stop-color:var(--accent)"/>
            <stop offset="1" style="stop-color:var(--accent-2)"/>
          </linearGradient>
        </defs>
        <path d="M2 13c2-4 4-4 6 0s4 4 6 0s3-5 3-5" stroke="url(#flow-mark-grad)" stroke-width="1.6" stroke-linecap="round"/>
        <path d="M2 8c2-4 4-4 6 0s4 4 6 0" stroke="url(#flow-mark-grad)" stroke-width="1.1" stroke-linecap="round" opacity="0.45"/>
      </svg>
    </span>
    FLOW
  </a>
  {% if company_name %}
  <span class="navbar-sep">/</span>
  <a class="navbar-company" href="/select-company" title="Ganti perusahaan">{{ company_name }}</a>
  {% endif %}
  {% if nav_modules %}
  <div class="navbar-menu">
    {% for m in nav_modules %}
    <a class="navbar-menu-item{{ ' active' if m.key == active_page else '' }}" href="{{ m.url }}">{{ m.name }}</a>
    {% endfor %}
  </div>
  {% endif %}
  {% if company_name %}
  <button id="fh-cmd-btn" class="fh-cmd-btn" title="Cari modul (Alt+K)">
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
    Cari modul
    <kbd>Alt+K</kbd>
  </button>
  {% endif %}
  <span class="navbar-user">
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
    {{ current_user or 'user' }}
  </span>
  <button class="btn-theme-toggle" onclick="toggleTheme()" title="Toggle dark mode" aria-label="Toggle dark mode">
    <svg class="icon-sun" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
    </svg>
    <svg class="icon-moon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
    </svg>
  </button>
  <button class="btn-logout" onclick="doLogout()">
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16,17 21,12 16,7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
    Keluar
  </button>
</nav>
```

with:

```html
<nav class="navbar">
  <a class="navbar-brand" href="/">
    <span class="navbar-brand-icon">
      <svg width="18" height="18" viewBox="0 0 20 20" fill="none">
        <defs>
          <linearGradient id="flow-mark-grad" x1="0" y1="0" x2="20" y2="20" gradientUnits="userSpaceOnUse">
            <stop offset="0" style="stop-color:var(--accent)"/>
            <stop offset="1" style="stop-color:var(--accent-2)"/>
          </linearGradient>
        </defs>
        <path d="M2 13c2-4 4-4 6 0s4 4 6 0s3-5 3-5" stroke="url(#flow-mark-grad)" stroke-width="1.6" stroke-linecap="round"/>
        <path d="M2 8c2-4 4-4 6 0s4 4 6 0" stroke="url(#flow-mark-grad)" stroke-width="1.1" stroke-linecap="round" opacity="0.45"/>
      </svg>
    </span>
    FLOW
  </a>
  {% if nav_modules %}
    {% set show_switcher = use_unified_header and active_page and active_page != 'dashboard' %}
    {% set current_mod = (nav_modules | selectattr('key', 'equalto', active_page) | first) if show_switcher else none %}
    {% if current_mod %}
    <div class="fh-mod-switch">
      <button type="button" id="fh-mod-trigger" class="fh-mod-trigger" aria-haspopup="listbox" aria-expanded="false">
        {{ current_mod.name }}
        <span class="fh-mod-chevron"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg></span>
      </button>
      <div id="fh-mod-dd" class="fh-mod-dd" role="listbox">
        {% for m in nav_modules %}
        <div class="fh-mod-dd-item{{ ' current' if m.key == active_page else '' }}" role="option" {% if m.key != active_page %}data-url="{{ m.url }}"{% endif %}>
          <span>{{ m.name }}</span>
          {% if m.key == active_page %}<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>{% endif %}
        </div>
        {% endfor %}
      </div>
    </div>
    <div class="navbar-menu">
      {% block module_tabs %}{% endblock %}
    </div>
    {% else %}
    <div class="navbar-menu">
      {% for m in nav_modules %}
      <a class="navbar-menu-item{{ ' active' if m.key == active_page else '' }}" href="{{ m.url }}">{{ m.name }}</a>
      {% endfor %}
    </div>
    {% endif %}
  {% endif %}
  <div class="navbar-right">
    {% if company_name %}
    <button id="fh-cmd-btn" class="fh-cmd-btn" title="Cari modul (Alt+K)" aria-label="Cari modul (Alt+K)">
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
    </button>
    <span class="navbar-sep">/</span>
    <a class="navbar-company" href="/select-company" title="Ganti perusahaan">{{ company_name }}</a>
    {% endif %}
    <span class="navbar-user">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
      {{ current_user or 'user' }}
    </span>
    <button class="btn-theme-toggle" onclick="toggleTheme()" title="Toggle dark mode" aria-label="Toggle dark mode">
      <svg class="icon-sun" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
      </svg>
      <svg class="icon-moon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
      </svg>
    </button>
    <button class="btn-logout" onclick="doLogout()">
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16,17 21,12 16,7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
      Keluar
    </button>
  </div>
</nav>
```

Note: when `use_unified_header` is falsy (every module except Dashboard, until its own migration task lands) or `active_page == 'dashboard'`, this renders byte-for-byte the same flat list as before — no visible change for unmigrated pages.

- [x] **Step 2: Add navbar-right, module-switch dropdown, and tab-fade CSS**

In `app/static/css/style.css`, replace this rule (current lines 157-171):

```css
.fh-cmd-btn {
  margin-left: auto;
  display: flex; align-items: center; gap: .4rem;
  background: var(--sl-100);
  border: 1px solid var(--sl-200);
  border-radius: var(--r-md);
  color: var(--sl-500);
  font-size: .775rem; font-weight: 500;
  padding: .275rem .625rem;
  cursor: pointer;
  font-family: inherit;
  transition: background .12s, border-color .12s, color .12s;
  white-space: nowrap;
}
.fh-cmd-btn:hover { background: var(--sl-200); color: var(--sl-700); border-color: var(--sl-300); }
```

with:

```css
.navbar-right {
  margin-left: auto;
  display: flex; align-items: center; gap: .5rem;
  flex-shrink: 0;
}
.fh-cmd-btn {
  display: flex; align-items: center; justify-content: center;
  background: var(--sl-100);
  border: 1px solid var(--sl-200);
  border-radius: var(--r-md);
  color: var(--sl-500);
  padding: .4rem;
  cursor: pointer;
  font-family: inherit;
  transition: background .12s, border-color .12s, color .12s;
}
.fh-cmd-btn:hover { background: var(--sl-200); color: var(--sl-700); border-color: var(--sl-300); }

/* ── Header module-switch dropdown (navbar) ─────────────────────── */
.fh-mod-switch { position: relative; flex-shrink: 0; }
.fh-mod-trigger {
  display: inline-flex; align-items: center; gap: .35rem;
  background: transparent; border: none;
  font-family: inherit; font-size: .875rem; font-weight: 700;
  color: var(--sl-900);
  cursor: pointer;
  border-radius: var(--r-sm);
  padding: .25rem .375rem;
  transition: background .12s;
}
.fh-mod-trigger:hover { background: var(--bg-muted); }
.fh-mod-chevron {
  display: inline-flex;
  color: var(--text-muted);
  transition: transform .15s;
}
.fh-mod-trigger[aria-expanded="true"] .fh-mod-chevron { transform: rotate(180deg); }

.fh-mod-dd {
  display: none;
  position: absolute;
  top: 100%;
  left: 0;
  margin-top: .375rem;
  min-width: 220px;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--r-md);
  box-shadow: var(--sh-lg);
  padding: .375rem 0;
  z-index: 200;
}
.fh-mod-dd.open { display: block; }
.fh-mod-dd-item {
  display: flex; align-items: center; justify-content: space-between;
  padding: .5rem .75rem;
  font-size: .85rem; font-weight: 500;
  color: var(--ink);
  gap: .5rem;
  cursor: pointer;
  transition: background .08s;
}
.fh-mod-dd-item:hover { background: var(--accent-surface); color: var(--accent-text); }
.fh-mod-dd-item.current { cursor: default; font-weight: 700; }
.fh-mod-dd-item.current:hover { background: transparent; color: var(--ink); }
.fh-mod-dd-item svg { flex-shrink: 0; }

/* ── Header tab strip: no-wrap + trailing fade when scrollable ──── */
.navbar-menu { position: relative; }
.navbar-menu .tabs { flex-wrap: nowrap; margin-bottom: 0; }
.navbar-menu.fh-overflow::after {
  content: '';
  position: absolute; top: 0; right: 0; bottom: 0;
  width: 28px;
  background: linear-gradient(to right, rgba(255,255,255,0), #FFF);
  pointer-events: none;
}
[data-theme="dark"] .navbar-menu.fh-overflow::after {
  background: linear-gradient(to right, rgba(15,18,32,0), #0F1220);
}

/* ── Content-area toolbar row (Filter / Full Screen, relocated out  */
/* of the header — see .fh-page-header below) ─────────────────────── */
.fh-content-toolbar {
  display: flex;
  margin-bottom: 1rem;
}
```

- [x] **Step 3: Rework Focus Mode CSS so the navbar (module dropdown + tabs) stays visible**

Replace this block (current lines 635-652):

```css
/* ── Focus / fullscreen mode ────────────────────────────────────── */
/* Applied by adding .fh-focus class to <body>. Hides navbar + filter   */
/* panel only — .page-toolbar (title+tabs) stays visible so users can   */
/* still switch sub-modules without leaving focus mode.                 */
body.fh-focus .navbar {
  height: 0; overflow: hidden; padding: 0; min-height: 0;
  border-bottom: none;
  transition: height .22s ease, padding .22s ease;
}
body:not(.fh-focus) .navbar {
  transition: height .22s ease, padding .22s ease;
}
body.fh-focus .filter-bar.collapsible { display: none !important; }
/* Navbar collapses to 0 height in focus mode — reclaim the space .main  */
/* normally reserves for it, and un-pin .fh-page-header's sticky offset  */
/* (both otherwise still assume a 52px navbar and leave a dead gap).     */
body.fh-focus .main { margin-top: 0; }
body.fh-focus .fh-page-header { top: 0; }
```

with:

```css
/* ── Focus / fullscreen mode ────────────────────────────────────── */
/* Applied by adding .fh-focus class to <body>. Hides the filter panel  */
/* and the navbar's right-hand controls (company/user/theme/logout) —   */
/* the module dropdown + tabs stay visible so users can keep switching  */
/* sub-modules without leaving focus mode.                              */
body.fh-focus .navbar-right { display: none; }
body.fh-focus .filter-bar.collapsible { display: none !important; }
```

- [x] **Step 4: Add the module-switch dropdown JS + tab-fade JS in `app/static/js/app.js`**

Insert immediately after `initTitleDropdown()`'s closing brace (current line 241, right before the `/* ── Skeleton loading ── */` comment):

```javascript
function initModuleSwitchDropdown() {
  var trigger = document.getElementById('fh-mod-trigger');
  var panel   = document.getElementById('fh-mod-dd');
  if (!trigger || !panel) return;

  function open() {
    panel.classList.add('open');
    trigger.setAttribute('aria-expanded', 'true');
  }
  function close() {
    panel.classList.remove('open');
    trigger.setAttribute('aria-expanded', 'false');
  }
  function toggle(e) {
    e.stopPropagation();
    if (panel.classList.contains('open')) close(); else open();
  }

  trigger.addEventListener('click', toggle);
  trigger.addEventListener('keydown', function(e) {
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggle(e); }
    else if (e.key === 'Escape') { close(); }
  });
  panel.querySelectorAll('.fh-mod-dd-item[data-url]').forEach(function(item) {
    item.addEventListener('click', function() {
      window.location.href = item.dataset.url;
    });
  });
  document.addEventListener('click', function(e) {
    if (!trigger.contains(e.target) && !panel.contains(e.target)) close();
  });
}

function initHeaderTabFade() {
  document.querySelectorAll('.navbar-menu').forEach(function(el) {
    function update() {
      var atEnd = el.scrollLeft + el.clientWidth >= el.scrollWidth - 1;
      el.classList.toggle('fh-overflow', el.scrollWidth > el.clientWidth + 1 && !atEnd);
    }
    update();
    el.addEventListener('scroll', update);
    window.addEventListener('resize', update);
  });
}
```

- [x] **Step 5: Register the new init functions**

In `app/static/js/app.js`, replace (current lines 532-535):

```javascript
document.addEventListener("DOMContentLoaded", () => {
  initCommandPalette();
  initTitleDropdown();
  document.querySelectorAll("[data-tabs]").forEach(initTabs);
```

with:

```javascript
document.addEventListener("DOMContentLoaded", () => {
  initCommandPalette();
  initTitleDropdown();
  initModuleSwitchDropdown();
  initHeaderTabFade();
  document.querySelectorAll("[data-tabs]").forEach(initTabs);
```

- [x] **Step 6: Flip the flag for Dashboard**

In `app/modules/dashboard/routes.py`, replace (current lines 91-92):

```python
    return render_template("dashboard/index.html", stats=stats, dash=dash,
                           active_page="dashboard", **get_ctx())
```

with:

```python
    return render_template("dashboard/index.html", stats=stats, dash=dash,
                           active_page="dashboard", use_unified_header=True, **get_ctx())
```

- [x] **Step 7: Run the existing regression suite**

Run: `cd app && python -m pytest tests/test_dashboard.py -v`
Expected: all tests pass unchanged (no route/context assertions reference navbar markup).

- [x] **Step 8: Manual visual check**

Start the dev server (`preview_start` with the project's Flask launch config), log in, and confirm:
- `/dashboard` looks identical to before (flat module list, company name/search icon now on the right).
- Every other module (still unmigrated) also looks identical — `use_unified_header` is unset for them, so they fall through to the old flat-list branch.
- Toggling dark mode still themes the navbar correctly.

- [x] **Step 9: Commit**

```bash
git add app/templates/base.html app/static/css/style.css app/static/js/app.js app/modules/dashboard/routes.py
git commit -m "feat: shared unified-header foundation (base.html, CSS, JS)"
```

---

### Task 2: Migrate Beasiswa

**Files:**
- Modify: `app/templates/beasiswa/index.html:1-45`
- Modify: `app/modules/beasiswa/routes.py:68-82`

**Interfaces:**
- Consumes: `{% block module_tabs %}` from Task 1; `use_unified_header` flag.

- [x] **Step 1: Add the `module_tabs` block override**

In `app/templates/beasiswa/index.html`, insert immediately after the existing `{% block head %}...{% endblock %}` (current lines 3-8), before `{% block content %}`:

```jinja
{% block module_tabs %}
{% if not wrong_company %}
<div class="tabs" style="margin-bottom:0" title="Alt+&#8592; / Alt+&#8594; untuk pindah tab">
  <button class="tab-btn" data-tab="tab-dashboard" onclick="loadDashboard()">Dashboard</button>
  <button class="tab-btn" data-tab="tab-siswa" onclick="loadRekap()">Data Siswa</button>
  <button class="tab-btn" data-tab="tab-budget" onclick="loadBudgetList()">Data Budget</button>
  <button class="tab-btn" data-tab="tab-payment" onclick="loadPaymentList()">Data Payment</button>
  <button class="tab-btn" data-tab="tab-laporan" onclick="lprReset()">Report Siswa</button>
  <button class="tab-btn" data-tab="tab-rekam" onclick="loadRekamMedis()">Rekam Medis</button>
  <button class="tab-btn" data-tab="tab-sahabat" onclick="initSahabatEtf()">Sahabat ETF</button>
</div>
{% endif %}
{% endblock %}
```

- [x] **Step 2: Remove the old header row, relocate Filter/Full Screen**

Replace this block (current lines 19-45):

```html
<div data-tabs>
<div class="fh-page-header">
  <div class="page-toolbar">
    <h1 class="page-title" style="margin-bottom:0">Beasiswa</h1>
    <div class="tabs" style="margin-bottom:0" title="Alt+&#8592; / Alt+&#8594; untuk pindah tab">
      <button class="tab-btn" data-tab="tab-dashboard" onclick="loadDashboard()">Dashboard</button>
      <button class="tab-btn" data-tab="tab-siswa" onclick="loadRekap()">Data Siswa</button>
      <button class="tab-btn" data-tab="tab-budget" onclick="loadBudgetList()">Data Budget</button>
      <button class="tab-btn" data-tab="tab-payment" onclick="loadPaymentList()">Data Payment</button>
      <button class="tab-btn" data-tab="tab-laporan" onclick="lprReset()">Report Siswa</button>
      <button class="tab-btn" data-tab="tab-rekam" onclick="loadRekamMedis()">Rekam Medis</button>
      <button class="tab-btn" data-tab="tab-sahabat" onclick="initSahabatEtf()">Sahabat ETF</button>
    </div>
    <div class="page-toolbar-actions">
      <button id="bsw-filter-toggle" class="btn btn-secondary btn-sm btn-filter-toggle"
              onclick="toggleActiveTabFilter(this.closest('[data-tabs]'), 'bsw-filter-toggle')" title="Tampilkan/sembunyikan filter">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;margin-right:3px"><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/></svg>
        Filter
        <kbd class="fh-kbd">F</kbd>
      </button>
      <button id="bsw-focus-btn" class="btn btn-secondary btn-sm" onclick="enterFocusMode()" title="Sembunyikan filter & navbar">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;margin-right:3px"><path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"/></svg>
        Full Screen
      </button>
    </div>
  </div>
</div>
```

with:

```html
<div data-tabs>
<div class="fh-content-toolbar">
  <div class="page-toolbar-actions">
    <button id="bsw-filter-toggle" class="btn btn-secondary btn-sm btn-filter-toggle"
            onclick="toggleActiveTabFilter(this.closest('[data-tabs]'), 'bsw-filter-toggle')" title="Tampilkan/sembunyikan filter">
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;margin-right:3px"><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/></svg>
      Filter
      <kbd class="fh-kbd">F</kbd>
    </button>
    <button id="bsw-focus-btn" class="btn btn-secondary btn-sm" onclick="enterFocusMode()" title="Sembunyikan filter & navbar">
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;margin-right:3px"><path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"/></svg>
      Full Screen
    </button>
  </div>
</div>
```

(The `<div data-tabs>` wrapper stays open — it still wraps every `.tab-panel` below.)

- [x] **Step 3: Flip the flag**

In `app/modules/beasiswa/routes.py`, find the `render_template(...)` call at line 68 that passes `active_page="beasiswa"` (line 81) and add `use_unified_header=True` as a sibling kwarg on the same call.

- [x] **Step 4: Run the existing regression suite**

Run: `cd app && python -m pytest tests/test_beasiswa_routes.py -v`
Expected: all tests pass unchanged.

- [x] **Step 5: Commit**

```bash
git add app/templates/beasiswa/index.html app/modules/beasiswa/routes.py
git commit -m "feat: migrate Beasiswa to unified header navigation"
```

---

### Task 3: Migrate Payment Approval Memo

**Files:**
- Modify: `app/templates/payment_memo/index.html:1-152`
- Modify: `app/modules/payment_memo/routes.py:66-82`

**Interfaces:**
- Consumes: `{% block module_tabs %}` from Task 1; `use_unified_header` flag.

**Note:** `app/templates/payment_memo/routes.py` and `app/templates/payment_memo/index.html` were heavily touched by earlier work this session (Vendors tab, LAND-pillar fix, dark-mode fix) — re-run `git status --porcelain -- app/templates/payment_memo/index.html app/modules/payment_memo/routes.py` immediately before editing to confirm the file is clean relative to HEAD (it was at plan-writing time) and no new concurrent WIP has landed on these specific lines since.

- [ ] **Step 1: Add the `module_tabs` block override**

In `app/templates/payment_memo/index.html`, find the file's `{% block head %}...{% endblock %}` near the top and insert immediately after it, before `{% block content %}`:

```jinja
{% block module_tabs %}
<div class="tabs" style="margin-bottom:0" title="Alt+&#8592; / Alt+&#8594; untuk pindah tab">
  <button class="tab-btn" data-tab="tab-draft-pay">Open PAM ({{ drafts|length }})</button>
  <button class="tab-btn" data-tab="tab-input-payment" onclick="ipayReset()">Input</button>
  {% if company_code == 'SMT' %}
  <button class="tab-btn" data-tab="tab-smt" onclick="loadSMT()">PAM List</button>
  <button class="tab-btn" data-tab="tab-advance" onclick="loadAdvance()">Advance</button>
  {% else %}
  <button class="tab-btn" data-tab="tab-pam" onclick="loadPAM()">AGRI</button>
  <button class="tab-btn" data-tab="tab-fiori" onclick="loadFIORI()">APP</button>
  <button class="tab-btn" data-tab="tab-sml" onclick="loadSML()">LAND</button>
  <button class="tab-btn" data-tab="tab-setf" onclick="loadSETF()">SETF</button>
  <button class="tab-btn" data-tab="tab-pa-advance" onclick="loadPaAdvance()">Advance</button>
  <button class="tab-btn" data-tab="tab-vendors" onclick="loadVendors()">Vendors</button>
  {% endif %}
  <button class="tab-btn" data-tab="tab-draft-memo">Print Memo</button>
</div>
{% endblock %}
```

- [ ] **Step 2: Remove the old header row, relocate Filter/Full Screen**

Replace this block (current lines 119-152):

```html
<div data-tabs>
<div class="fh-page-header">
  <div class="page-toolbar">
    <h1 style="font-size:1.25rem; font-weight:700; margin-bottom:0">Payment Approval Memo</h1>
    <div class="tabs" style="margin-bottom:0" title="Alt+&#8592; / Alt+&#8594; untuk pindah tab">
      <button class="tab-btn" data-tab="tab-draft-pay">Open PAM ({{ drafts|length }})</button>
      <button class="tab-btn" data-tab="tab-input-payment" onclick="ipayReset()">Input</button>
      {% if company_code == 'SMT' %}
      <button class="tab-btn" data-tab="tab-smt" onclick="loadSMT()">PAM List</button>
      <button class="tab-btn" data-tab="tab-advance" onclick="loadAdvance()">Advance</button>
      {% else %}
      <button class="tab-btn" data-tab="tab-pam" onclick="loadPAM()">AGRI</button>
      <button class="tab-btn" data-tab="tab-fiori" onclick="loadFIORI()">APP</button>
      <button class="tab-btn" data-tab="tab-sml" onclick="loadSML()">LAND</button>
      <button class="tab-btn" data-tab="tab-setf" onclick="loadSETF()">SETF</button>
      <button class="tab-btn" data-tab="tab-pa-advance" onclick="loadPaAdvance()">Advance</button>
      <button class="tab-btn" data-tab="tab-vendors" onclick="loadVendors()">Vendors</button>
      {% endif %}
      <button class="tab-btn" data-tab="tab-draft-memo">Print Memo</button>
    </div>
    <div class="page-toolbar-actions">
      <button id="pam-filter-toggle" class="btn btn-secondary btn-sm btn-filter-toggle"
              onclick="toggleActiveTabFilter(this.closest('[data-tabs]'), 'pam-filter-toggle')" title="Tampilkan/sembunyikan filter">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;margin-right:3px"><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/></svg>
        Filter
        <kbd class="fh-kbd">F</kbd>
      </button>
      <button id="pam-focus-btn" class="btn btn-secondary btn-sm" onclick="enterFocusMode()" title="Sembunyikan filter & navbar">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;margin-right:3px"><path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"/></svg>
        Full Screen
      </button>
    </div>
  </div>
</div>
```

with:

```html
<div data-tabs>
<div class="fh-content-toolbar">
  <div class="page-toolbar-actions">
    <button id="pam-filter-toggle" class="btn btn-secondary btn-sm btn-filter-toggle"
            onclick="toggleActiveTabFilter(this.closest('[data-tabs]'), 'pam-filter-toggle')" title="Tampilkan/sembunyikan filter">
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;margin-right:3px"><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/></svg>
      Filter
      <kbd class="fh-kbd">F</kbd>
    </button>
    <button id="pam-focus-btn" class="btn btn-secondary btn-sm" onclick="enterFocusMode()" title="Sembunyikan filter & navbar">
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;margin-right:3px"><path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"/></svg>
      Full Screen
    </button>
  </div>
</div>
```

- [ ] **Step 3: Flip the flag**

In `app/modules/payment_memo/routes.py`, find the `render_template(...)` call (starts at line 66) that passes `active_page="payment_memo"` (line 74) and add `use_unified_header=True` as a sibling kwarg on the same call.

- [ ] **Step 4: Run the existing regression suite**

Run: `cd app && python -m pytest tests/test_payment_memo_ipay.py tests/test_payment_memo_open_pam.py tests/test_payment_memo_service.py tests/test_payment_memo_sla.py tests/test_payment_memo_vendors.py -v`
Expected: all tests pass unchanged.

- [ ] **Step 5: Commit**

```bash
git add app/templates/payment_memo/index.html app/modules/payment_memo/routes.py
git commit -m "feat: migrate Payment Approval Memo to unified header navigation"
```

---

### Task 4: Migrate Payment Application (`etf_payment_application`)

**Files:**
- Modify: `app/templates/etf_payment_application/index.html:174-200`
- Modify: `app/modules/etf_payment_application/routes.py:103-125`

**Interfaces:**
- Consumes: `{% block module_tabs %}` from Task 1; `use_unified_header` flag.

**Note:** per Global Constraints, re-check `git status --porcelain -- app/templates/etf_payment_application/index.html` before editing — this file has uncommitted concurrent-session WIP as of plan-writing.

- [ ] **Step 1: Add the `module_tabs` block override**

Insert this block right before the line `{# ── Header: title + tabs + actions in one row ── #}` (current line 173):

```jinja
{% block module_tabs %}
<div class="tabs" style="margin-bottom:0" title="Alt+&#8592; / Alt+&#8594; untuk pindah tab">
  {% for t, label in [('summary','Open PA'),('advance','Advance'),('input','Input'),('agri','AGRI'),('app','APP'),('sml','LAND'),('setf','SETF')] %}
  <a href="?tab={{ t }}{% if t != 'input' and active_sf %}&sf={{ active_sf }}{% endif %}"
     class="tab-btn{% if active_tab == t %} active{% endif %}"
     style="text-decoration:none"
  >{{ label }}</a>
  {% endfor %}
</div>
{% endblock %}
```

- [ ] **Step 2: Remove the title+tabs row, relocate Filter/Full Screen**

Replace this block (current lines 174-200 — note the wrapping `<div id="pa-page-header" class="fh-page-header">` does **not** close here; it continues to wrap the filter panel and bulk-action bar below, closing at the existing `</div>{# end pa-page-header #}` near the end of the file — leave that closing tag untouched):

```html
<div id="pa-page-header" class="fh-page-header">
<div class="page-toolbar">
  <h1 class="page-title" style="margin-bottom:0">Payment Application</h1>
  <div class="tabs" style="margin-bottom:0" title="Alt+&#8592; / Alt+&#8594; untuk pindah tab">
    {% for t, label in [('summary','Open PA'),('advance','Advance'),('input','Input'),('agri','AGRI'),('app','APP'),('sml','LAND'),('setf','SETF')] %}
    <a href="?tab={{ t }}{% if t != 'input' and active_sf %}&sf={{ active_sf }}{% endif %}"
       class="tab-btn{% if active_tab == t %} active{% endif %}"
       style="text-decoration:none"
    >{{ label }}</a>
    {% endfor %}
  </div>
  {% if active_tab != 'input' %}
  <div class="page-toolbar-actions">
    <button id="pa-filter-toggle" class="btn btn-secondary btn-sm btn-filter-toggle" onclick="toggleFilterPanel('pa-filter-panel','pa-filter-toggle')" title="Tampilkan/sembunyikan filter">
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;margin-right:3px"><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/></svg>
      Filter
      <kbd class="fh-kbd">F</kbd>
    </button>
    {% if active_tab not in ('summary', 'advance') %}
    <button id="pa-focus-btn" class="btn btn-secondary btn-sm" onclick="enterFocusMode()" title="Sembunyikan filter & navbar">
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;margin-right:3px"><path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"/></svg>
      Full Screen
    </button>
    {% endif %}
  </div>
  {% endif %}
</div>
```

with:

```html
<div id="pa-page-header" class="fh-page-header">
<div class="fh-content-toolbar">
  {% if active_tab != 'input' %}
  <div class="page-toolbar-actions">
    <button id="pa-filter-toggle" class="btn btn-secondary btn-sm btn-filter-toggle" onclick="toggleFilterPanel('pa-filter-panel','pa-filter-toggle')" title="Tampilkan/sembunyikan filter">
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;margin-right:3px"><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/></svg>
      Filter
      <kbd class="fh-kbd">F</kbd>
    </button>
    {% if active_tab not in ('summary', 'advance') %}
    <button id="pa-focus-btn" class="btn btn-secondary btn-sm" onclick="enterFocusMode()" title="Sembunyikan filter & navbar">
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;margin-right:3px"><path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"/></svg>
      Full Screen
    </button>
    {% endif %}
  </div>
  {% endif %}
</div>
```

- [ ] **Step 3: Flip the flag**

In `app/modules/etf_payment_application/routes.py`, find the `render_template(...)` call (starts at line 103) that passes `active_page="etf_payment_app"` (line 125) and add `use_unified_header=True` as a sibling kwarg on the same call.

- [ ] **Step 4: Manual smoke check**

No dedicated route/render test file exists for this module's HTML. Using the running dev server, visit `/etf-payment-application` and confirm: the `Open PA / Advance / Input / AGRI / APP / LAND / SETF` tabs render in the navbar with the correct one highlighted per `?tab=`, the Filter and Full Screen buttons appear in a row below the header, and the bulk-select bar (select a row on a data tab) still appears/disappears correctly without layout breakage.

- [ ] **Step 5: Commit**

```bash
git add app/templates/etf_payment_application/index.html app/modules/etf_payment_application/routes.py
git commit -m "feat: migrate Payment Application to unified header navigation"
```

---

### Task 5: Migrate Bank

**Files:**
- Modify: `app/templates/bank/index.html:1-32`
- Modify: `app/modules/bank/routes.py:54-58`

**Interfaces:**
- Consumes: `{% block module_tabs %}` from Task 1; `use_unified_header` flag.

**Note:** re-check `git status --porcelain -- app/templates/bank/index.html` before editing — this file has uncommitted concurrent-session WIP as of plan-writing.

Bank's `<h1>Bank Sahabat ETF</h1>` sits inside `.bank-header` alongside the Pemasukan/Pengeluaran/Saldo summary cards — it is content, not a redundant navigation title, so it is **not** removed by this task (unlike the `.fh-page-header` title in Tasks 2-4).

- [ ] **Step 1: Add the `module_tabs` block override**

In `app/templates/bank/index.html`, insert immediately after `{% block head %}...{% endblock %}` (current lines 4-6), before `{% block content %}`:

```jinja
{% block module_tabs %}
<div class="tabs">
  <button type="button" class="tab-btn" data-tab="tab-mutasi">Mutasi &amp; Saldo</button>
  <button type="button" class="tab-btn" data-tab="tab-open">Open</button>
</div>
{% endblock %}
```

- [ ] **Step 2: Remove the old in-page tab strip**

Replace (current lines 28-33):

```html
  <div class="bank-tabs" data-tabs>
    <div class="tabs">
      <button type="button" class="tab-btn" data-tab="tab-mutasi">Mutasi & Saldo</button>
      <button type="button" class="tab-btn" data-tab="tab-open">Open</button>
    </div>

    <div class="tab-content">
```

with:

```html
  <div class="bank-tabs" data-tabs>
    <div class="tab-content">
```

- [ ] **Step 3: Flip the flag**

In `app/modules/bank/routes.py`, find the `render_template(...)` call (starts at line 54) that passes `active_page="bank"` (line 56) and add `use_unified_header=True` as a sibling kwarg on the same call.

- [ ] **Step 4: Run the existing regression suite**

Run: `cd app && python -m pytest tests/test_bank_routes.py -v`
Expected: all tests pass unchanged.

- [ ] **Step 5: Commit**

```bash
git add app/templates/bank/index.html app/modules/bank/routes.py
git commit -m "feat: migrate Bank to unified header navigation"
```

---

### Task 6: Migrate Users (State C — bare dropdown, no tabs)

**Files:**
- Modify: `app/modules/users/routes.py:26-27`

**Interfaces:**
- Consumes: `use_unified_header` flag. `{% block module_tabs %}` is intentionally left un-overridden — base.html's default empty block renders the bare `Users ▾` dropdown trigger with no tabs beside it (spec "State C").

Users has no existing tab bar, so no template markup needs to move. Its `<h1 class="page-title">User Management</h1>` sits beside the "+ Tambah User" action button in a plain `.page-header` (not the `.fh-page-header` pattern) — left untouched, same reasoning as Bank.

- [ ] **Step 1: Flip the flag**

In `app/modules/users/routes.py`, replace (current lines 26-27):

```python
    return render_template("users/index.html", users=get_users(),
                           active_page="users", **_ctx())
```

with:

```python
    return render_template("users/index.html", users=get_users(),
                           active_page="users", use_unified_header=True, **_ctx())
```

- [ ] **Step 2: Run the existing regression suite**

Run: `cd app && python -m pytest tests/test_users_routes.py -v`
Expected: all tests pass unchanged.

- [ ] **Step 3: Manual smoke check**

Visit `/users` in the running dev server and confirm the navbar shows a `Users ▾` dropdown trigger with no tabs beside it, and clicking it lists all modules with Users marked current.

- [ ] **Step 4: Commit**

```bash
git add app/modules/users/routes.py
git commit -m "feat: migrate Users to unified header navigation"
```

---

### Task 7: Migrate Sponsorship (4 pages sharing `_toolbar.html`)

**Files:**
- Modify: `app/templates/sponsorship/dashboard.html`, `app/templates/sponsorship/input.html`, `app/templates/sponsorship/data.html`, `app/templates/sponsorship/report.html`
- Modify: `app/modules/sponsorship/routes.py:66,84,118-119,150`

**Interfaces:**
- Consumes: `{% block module_tabs %}` from Task 1; `use_unified_header` flag; existing `app/templates/sponsorship/_toolbar.html` (unmodified — only where it's included changes).

`_toolbar.html`'s tab links read a local `active_tab` Jinja variable. That variable must be `{% set %}` at each template's **root level** (outside any block, right after `{% extends %}`) rather than inside `{% block content %}` — `module_tabs` renders in the navbar, which comes before `{% block content %}` in `base.html`'s output order, so a `{% set %}` living inside `content` would not have executed yet when `module_tabs` needs it. Root-level `{% set %}` statements in a child template execute before the parent dispatches into any block, so this ordering concern doesn't apply there.

- [ ] **Step 1: `app/templates/sponsorship/dashboard.html`**

Replace the full file with:

```jinja
{% extends "base.html" %}
{% set active_tab = "dashboard" %}
{% block title %}Sponsorship Dashboard{% endblock %}
{% block head %}
<link rel="stylesheet" href="{{ url_for('static', filename='css/budget.css') }}">
<link rel="stylesheet" href="{{ url_for('static', filename='css/sponsorship.css') }}">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js"></script>
{% endblock %}
{% block module_tabs %}
{% if not wrong_company %}
{% include "sponsorship/_toolbar.html" with context %}
{% endif %}
{% endblock %}
{% block content %}
<div class="budget-page">
  <h1>Sponsorship — Dashboard</h1>
  {% if wrong_company %}
    {% include "sponsorship/_notice.html" %}
  {% else %}
  <div class="budget-toolbar">
    <select class="sp-dash-filter" data-param="tahun"><option value="">Semua Tahun</option>
      {% for y in years %}<option value="{{ y }}">{{ y }}</option>{% endfor %}
    </select>
    <select class="sp-dash-filter" data-param="cat">
      <option value="">Semua Cat</option>
      {% for c in cat_choices %}<option value="{{ c }}">{{ c }}</option>{% endfor %}
    </select>
    <select class="sp-dash-filter" data-param="cat3">
      <option value="">Semua Pillar</option>
      {% for p in pillar_choices %}<option value="{{ p }}">{{ p }}</option>{% endfor %}
    </select>
  </div>
  <div class="budget-summary-grid" id="sp-summary"></div>
  <div class="budget-chart-grid">
    <div class="budget-chart-card"><h3>Trend Bulanan</h3><canvas id="sp-chart-monthly"></canvas></div>
    <div class="budget-chart-card"><h3>Per Pillar</h3><canvas id="sp-chart-pillar"></canvas></div>
    <div class="budget-chart-card"><h3>Per Kategori</h3><canvas id="sp-chart-description"></canvas></div>
  </div>
  {% endif %}
</div>
{% endblock %}
{% block scripts %}
<script src="{{ url_for('static', filename='js/sponsorship.js') }}"></script>
{% endblock %}
```

(Change from the current file: `{% set active_tab %}` moved to root level; new `module_tabs` block added; the old root-content `{% set active_tab = "dashboard" %}` + `{% include "sponsorship/_toolbar.html" with context %}` lines removed from inside `{% block content %}`.)

- [ ] **Step 2: `app/templates/sponsorship/input.html`**

Replace the full file with:

```jinja
{% extends "base.html" %}
{% set active_tab = "input" %}
{% block title %}Sponsorship Input{% endblock %}
{% block head %}
<link rel="stylesheet" href="{{ url_for('static', filename='css/budget.css') }}">
<link rel="stylesheet" href="{{ url_for('static', filename='css/sponsorship.css') }}">
{% endblock %}
{% block module_tabs %}
{% if not wrong_company %}
{% include "sponsorship/_toolbar.html" with context %}
{% endif %}
{% endblock %}
{% block content %}
<div class="budget-page">
  <h1>Sponsorship — Input</h1>
  {% if wrong_company %}
    {% include "sponsorship/_notice.html" %}
  {% else %}
  <form id="sp-input-form" class="budget-card">
    <label>Cat
      <select id="sp-in-cat">{% for c in cat_choices %}<option value="{{ c }}">{{ c }}</option>{% endfor %}</select>
    </label>
    <label>Description
      <select id="sp-in-description">{% for d in description_choices %}<option value="{{ d }}">{{ d }}</option>{% endfor %}</select>
    </label>
    <label>Cat1 (Perusahaan)
      <input type="text" id="sp-in-cat1-search" placeholder="Cari perusahaan...">
      <input type="hidden" id="sp-in-cat1">
      <div id="sp-in-cat1-results" class="sp-autocomplete-results"></div>
    </label>
    <label>Cat2 <input type="text" id="sp-in-cat2" readonly></label>
    <label>Cat3 (Pillar) <input type="text" id="sp-in-cat3" readonly></label>
    <label>Cat4
      <select id="sp-in-cat4"><option value="">(blank)</option>{% for c in cat4_choices %}<option value="{{ c }}">{{ c }}</option>{% endfor %}</select>
    </label>
    <label>Lembaga/Perorangan
      <input type="text" id="sp-in-lembaga" list="sp-lembaga-datalist" autocomplete="off">
      <datalist id="sp-lembaga-datalist"></datalist>
    </label>
    <label>Tanggal Form Sponsor <input type="date" id="sp-in-tanggal-form"></label>
    <label>Tanggal Payment <input type="date" id="sp-in-tanggal-payment"></label>
    <label>Perihal <input type="text" id="sp-in-perihal"></label>
    <label>Amount Request <input type="number" id="sp-in-amount" min="0"></label>
    <label>Reff <input type="text" id="sp-in-reff"></label>
    <label>Status <input type="text" id="sp-in-status"></label>
    <label>COA <input type="text" id="sp-in-coa" value="701078002"></label>
    <label>CC Total <input type="text" id="sp-in-cc-total" value="SMT - Corporate Communication"></label>
    <label>CC <input type="text" id="sp-in-cc" value="POSPON"></label>
    <label>Source <input type="text" id="sp-in-source" value="Sponsor"></label>
  </form>
  <div class="budget-toolbar">
    <button class="budget-btn" onclick="sponsorshipInputSubmit()">Simpan</button>
  </div>
  {% endif %}
</div>
{% endblock %}
{% block scripts %}
<script src="{{ url_for('static', filename='js/sponsorship.js') }}"></script>
{% endblock %}
```

- [ ] **Step 3: `app/templates/sponsorship/data.html`**

Read the full current file first (it is 122 lines; only its top ~14 lines and the JS/script block need to change). Apply these two edits:

Replace (current lines 1-14):

```jinja
{% extends "base.html" %}
{% block title %}Sponsorship Data{% endblock %}
{% block head %}
<link rel="stylesheet" href="{{ url_for('static', filename='css/budget.css') }}">
<link rel="stylesheet" href="{{ url_for('static', filename='css/sponsorship.css') }}">
{% endblock %}
{% block content %}
<div class="budget-page">
  <h1>Sponsorship — Data</h1>
  {% set active_tab = "data" %}
  {% include "sponsorship/_toolbar.html" with context %}
  {% if wrong_company %}
    {% include "sponsorship/_notice.html" %}
  {% else %}
```

with:

```jinja
{% extends "base.html" %}
{% set active_tab = "data" %}
{% block title %}Sponsorship Data{% endblock %}
{% block head %}
<link rel="stylesheet" href="{{ url_for('static', filename='css/budget.css') }}">
<link rel="stylesheet" href="{{ url_for('static', filename='css/sponsorship.css') }}">
{% endblock %}
{% block module_tabs %}
{% if not wrong_company %}
{% include "sponsorship/_toolbar.html" with context %}
{% endif %}
{% endblock %}
{% block content %}
<div class="budget-page">
  <h1>Sponsorship — Data</h1>
  {% if wrong_company %}
    {% include "sponsorship/_notice.html" %}
  {% else %}
```

Leave the rest of the file (the filter form, table, pagination, `{% endif %}`, closing `</div>`, `{% endblock %}`, and any `{% block scripts %}`) exactly as-is.

- [ ] **Step 4: `app/templates/sponsorship/report.html`**

Replace the full file with:

```jinja
{% extends "base.html" %}
{% set active_tab = "report" %}
{% block title %}Sponsorship Report{% endblock %}
{% block head %}
<link rel="stylesheet" href="{{ url_for('static', filename='css/budget.css') }}">
{% endblock %}
{% block module_tabs %}
{% if not wrong_company %}
{% include "sponsorship/_toolbar.html" with context %}
{% endif %}
{% endblock %}
{% block content %}
<div class="budget-page">
  <h1>Sponsorship — Report</h1>
  {% if wrong_company %}
    {% include "sponsorship/_notice.html" %}
  {% else %}
  <div class="budget-card">
    <h3>Fitur Report akan datang</h3>
    <p>Export dan laporan Sponsorship sedang dalam pengembangan. Coming soon.</p>
  </div>
  {% endif %}
</div>
{% endblock %}
```

- [ ] **Step 5: Flip the flag on all four routes**

In `app/modules/sponsorship/routes.py`, each of the four `render_template(...)` calls (lines 66, 84, 118-119, 150) already passes `active_page="sponsorship"` — add `use_unified_header=True` as a sibling kwarg to each of the four calls.

- [ ] **Step 6: Run the existing regression suite**

Run: `cd app && python -m pytest tests/test_sponsorship_routes.py -v`
Expected: all tests pass unchanged.

- [ ] **Step 7: Commit**

```bash
git add app/templates/sponsorship/dashboard.html app/templates/sponsorship/input.html app/templates/sponsorship/data.html app/templates/sponsorship/report.html app/modules/sponsorship/routes.py
git commit -m "feat: migrate Sponsorship to unified header navigation"
```

---

### Task 8: Migrate Budget (split nav links from filters)

**Files:**
- Modify: `app/templates/budget/dashboard.html`, `app/templates/budget/master_list.html`, `app/templates/budget/realisasi_list.html`, `app/templates/budget/carryover.html`
- Modify: `app/modules/budget/routes.py:62,107,159,186`

**Interfaces:**
- Consumes: `{% block module_tabs %}` from Task 1; `use_unified_header` flag; Flask's globally-available `request` object (used for active-tab detection instead of a Jinja `{% set %}`, since `request.path` needs no root-level-ordering workaround).

**Note:** re-check `git status --porcelain -- app/templates/budget/carryover.html app/templates/budget/realisasi_list.html` before editing — these two files have uncommitted concurrent-session WIP as of plan-writing.

Every Budget page gets the same three-tab strip:

```jinja
{% block module_tabs %}
<div class="tabs" style="margin-bottom:0">
  <a href="{{ url_for('budget.master_list') }}" class="tab-btn{% if request.path == url_for('budget.master_list') %} active{% endif %}">Kelola Budget</a>
  <a href="{{ url_for('budget.realisasi_list') }}" class="tab-btn{% if request.path == url_for('budget.realisasi_list') %} active{% endif %}">Kelola Realisasi</a>
  <a href="{{ url_for('budget.carryover_page') }}" class="tab-btn{% if request.path == url_for('budget.carryover_page') %} active{% endif %}">Carryover / Tambahan</a>
</div>
{% endblock %}
```

(On `dashboard.html` none of these three match `request.path`, so no tab shows active — matching the spec's literal 3-tab set, which does not include Dashboard as a tab.)

- [ ] **Step 1: `app/templates/budget/dashboard.html`**

Replace (current lines 1-25):

```jinja
{% extends "base.html" %}
{% block title %}Budget Dashboard{% endblock %}
{% block head %}
<link rel="stylesheet" href="{{ url_for('static', filename='css/budget.css') }}">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js"></script>
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
    <a class="budget-btn" href="/budget/master">Kelola Budget</a>
    <a class="budget-btn" href="/budget/realisasi">Kelola Realisasi</a>
    <a class="budget-btn" href="/budget/carryover">Carryover / Tambahan</a>
  </div>
```

with:

```jinja
{% extends "base.html" %}
{% block title %}Budget Dashboard{% endblock %}
{% block head %}
<link rel="stylesheet" href="{{ url_for('static', filename='css/budget.css') }}">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js"></script>
{% endblock %}
{% block module_tabs %}
<div class="tabs" style="margin-bottom:0">
  <a href="{{ url_for('budget.master_list') }}" class="tab-btn{% if request.path == url_for('budget.master_list') %} active{% endif %}">Kelola Budget</a>
  <a href="{{ url_for('budget.realisasi_list') }}" class="tab-btn{% if request.path == url_for('budget.realisasi_list') %} active{% endif %}">Kelola Realisasi</a>
  <a href="{{ url_for('budget.carryover_page') }}" class="tab-btn{% if request.path == url_for('budget.carryover_page') %} active{% endif %}">Carryover / Tambahan</a>
</div>
{% endblock %}
{% block content %}
<div class="budget-page">
  <h1>Budget Dashboard</h1>

  <div class="fh-content-toolbar">
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

(The 5 filter selects + "Terapkan Filter" button keep their exact ids/markup — only their wrapping `<div>` class changes from `budget-toolbar` to `fh-content-toolbar`, and the 3 nav links move up into `module_tabs`.)

- [ ] **Step 2: `app/templates/budget/master_list.html`**

Replace (current lines 1-11):

```jinja
{% extends "base.html" %}
{% block title %}Budget Master{% endblock %}
{% block head %}
<link rel="stylesheet" href="{{ url_for('static', filename='css/budget.css') }}">
{% endblock %}
{% block content %}
<div class="budget-page">
  <h1>Budget Master</h1>
  <div class="budget-toolbar">
    <button class="budget-btn" onclick="openModal('budget-master-modal')">+ Budget Baru</button>
  </div>
```

with:

```jinja
{% extends "base.html" %}
{% block title %}Budget Master{% endblock %}
{% block head %}
<link rel="stylesheet" href="{{ url_for('static', filename='css/budget.css') }}">
{% endblock %}
{% block module_tabs %}
<div class="tabs" style="margin-bottom:0">
  <a href="{{ url_for('budget.master_list') }}" class="tab-btn{% if request.path == url_for('budget.master_list') %} active{% endif %}">Kelola Budget</a>
  <a href="{{ url_for('budget.realisasi_list') }}" class="tab-btn{% if request.path == url_for('budget.realisasi_list') %} active{% endif %}">Kelola Realisasi</a>
  <a href="{{ url_for('budget.carryover_page') }}" class="tab-btn{% if request.path == url_for('budget.carryover_page') %} active{% endif %}">Carryover / Tambahan</a>
</div>
{% endblock %}
{% block content %}
<div class="budget-page">
  <h1>Budget Master</h1>
  <div class="fh-content-toolbar">
    <button class="budget-btn" onclick="openModal('budget-master-modal')">+ Budget Baru</button>
  </div>
```

- [ ] **Step 3: `app/templates/budget/realisasi_list.html`**

Replace (current lines 1-11):

```jinja
{% extends "base.html" %}
{% block title %}Realisasi{% endblock %}
{% block head %}
<link rel="stylesheet" href="{{ url_for('static', filename='css/budget.css') }}">
{% endblock %}
{% block content %}
<div class="budget-page">
  <h1>Realisasi Budget</h1>
  <div class="budget-toolbar">
    <button class="budget-btn" onclick="openModal('budget-realisasi-modal')">+ Realisasi Baru</button>
  </div>
```

with:

```jinja
{% extends "base.html" %}
{% block title %}Realisasi{% endblock %}
{% block head %}
<link rel="stylesheet" href="{{ url_for('static', filename='css/budget.css') }}">
{% endblock %}
{% block module_tabs %}
<div class="tabs" style="margin-bottom:0">
  <a href="{{ url_for('budget.master_list') }}" class="tab-btn{% if request.path == url_for('budget.master_list') %} active{% endif %}">Kelola Budget</a>
  <a href="{{ url_for('budget.realisasi_list') }}" class="tab-btn{% if request.path == url_for('budget.realisasi_list') %} active{% endif %}">Kelola Realisasi</a>
  <a href="{{ url_for('budget.carryover_page') }}" class="tab-btn{% if request.path == url_for('budget.carryover_page') %} active{% endif %}">Carryover / Tambahan</a>
</div>
{% endblock %}
{% block content %}
<div class="budget-page">
  <h1>Realisasi Budget</h1>
  <div class="fh-content-toolbar">
    <button class="budget-btn" onclick="openModal('budget-realisasi-modal')">+ Realisasi Baru</button>
  </div>
```

- [ ] **Step 4: `app/templates/budget/carryover.html`**

Replace (current lines 1-16):

```jinja
{% extends "base.html" %}
{% block title %}Carryover & Additional Budget{% endblock %}
{% block head %}
<link rel="stylesheet" href="{{ url_for('static', filename='css/budget.css') }}">
{% endblock %}
{% block content %}
<div class="budget-page">
  <h1>Carryover & Additional Budget Requests</h1>

  <div class="budget-toolbar">
    <input type="text" id="cr-budget-id" placeholder="Budget ID">
    <input type="text" id="cr-reason" placeholder="Alasan">
    <button class="budget-btn" onclick="budgetSubmitCarryover()">Request Carryover</button>
    <input type="number" id="cr-amount" placeholder="Jumlah tambahan" min="0">
    <button class="budget-btn" onclick="budgetSubmitAdditional()">Request Tambahan Anggaran</button>
  </div>
```

with:

```jinja
{% extends "base.html" %}
{% block title %}Carryover & Additional Budget{% endblock %}
{% block head %}
<link rel="stylesheet" href="{{ url_for('static', filename='css/budget.css') }}">
{% endblock %}
{% block module_tabs %}
<div class="tabs" style="margin-bottom:0">
  <a href="{{ url_for('budget.master_list') }}" class="tab-btn{% if request.path == url_for('budget.master_list') %} active{% endif %}">Kelola Budget</a>
  <a href="{{ url_for('budget.realisasi_list') }}" class="tab-btn{% if request.path == url_for('budget.realisasi_list') %} active{% endif %}">Kelola Realisasi</a>
  <a href="{{ url_for('budget.carryover_page') }}" class="tab-btn{% if request.path == url_for('budget.carryover_page') %} active{% endif %}">Carryover / Tambahan</a>
</div>
{% endblock %}
{% block content %}
<div class="budget-page">
  <h1>Carryover & Additional Budget Requests</h1>

  <div class="fh-content-toolbar">
    <input type="text" id="cr-budget-id" placeholder="Budget ID">
    <input type="text" id="cr-reason" placeholder="Alasan">
    <button class="budget-btn" onclick="budgetSubmitCarryover()">Request Carryover</button>
    <input type="number" id="cr-amount" placeholder="Jumlah tambahan" min="0">
    <button class="budget-btn" onclick="budgetSubmitAdditional()">Request Tambahan Anggaran</button>
  </div>
```

- [ ] **Step 5: Flip the flag on all four routes**

In `app/modules/budget/routes.py`, each of the four `render_template(...)` calls that pass `active_page="budget"` (lines 62, 107, 159, 186 — `master_list`, `realisasi_list`, `index`/dashboard, `carryover_page`) — add `use_unified_header=True` as a sibling kwarg to each.

- [ ] **Step 6: Run the existing regression suite**

Run: `cd app && python -m pytest tests/test_budget_routes.py tests/test_budget_dashboard.py -v`
Expected: all tests pass unchanged.

- [ ] **Step 7: Commit**

```bash
git add app/templates/budget/dashboard.html app/templates/budget/master_list.html app/templates/budget/realisasi_list.html app/templates/budget/carryover.html app/modules/budget/routes.py
git commit -m "feat: migrate Budget to unified header navigation"
```

---

### Task 9: Cleanup + full regression pass

**Files:**
- Modify: `app/templates/base.html` (remove the transitional flag/fallback branch)
- Modify: `app/static/js/app.js` (remove `initTitleDropdown()` + its registration)
- Modify: `app/static/css/style.css` (remove `.fh-title-*` rules, the now-dead `.fh-page-header` rule in `budget.css`)
- Modify: every route file touched in Tasks 1-8 (remove the now-unconditional `use_unified_header=True` kwarg)
- Modify: `app/static/css/budget.css:348`

**Interfaces:**
- Consumes: nothing new — this is pure deletion of now-dead transitional code once every module (Tasks 2-8) has migrated.

- [ ] **Step 1: Simplify `base.html`'s navbar branch**

Replace (the block from Task 1, now unconditional):

```jinja
  {% if nav_modules %}
    {% set show_switcher = use_unified_header and active_page and active_page != 'dashboard' %}
    {% set current_mod = (nav_modules | selectattr('key', 'equalto', active_page) | first) if show_switcher else none %}
    {% if current_mod %}
```

with:

```jinja
  {% if nav_modules %}
    {% set current_mod = (nav_modules | selectattr('key', 'equalto', active_page) | first) if (active_page and active_page != 'dashboard') else none %}
    {% if current_mod %}
```

Leave the rest of the branch (the `{% else %}` flat-list fallback, `navbar-right`, etc.) unchanged — it's still needed for the genuine Dashboard/State-A case.

- [ ] **Step 2: Remove `use_unified_header=True` from every route**

In each of these files, remove the `use_unified_header=True,` kwarg (now always true, so the flag is redundant) from the `render_template()` call(s) touched in Tasks 1-8:
`app/modules/dashboard/routes.py`, `app/modules/beasiswa/routes.py`, `app/modules/payment_memo/routes.py`, `app/modules/etf_payment_application/routes.py`, `app/modules/bank/routes.py`, `app/modules/users/routes.py`, `app/modules/sponsorship/routes.py` (4 call sites), `app/modules/budget/routes.py` (4 call sites).

- [ ] **Step 3: Retire `initTitleDropdown()`**

In `app/static/js/app.js`, delete the entire `initTitleDropdown()` function (from `function initTitleDropdown() {` through its matching closing `}`, currently spanning what was lines 168-241 before Task 1's insertions shifted line numbers — locate by function name, not line number).

Then replace (in the `DOMContentLoaded` listener):

```javascript
document.addEventListener("DOMContentLoaded", () => {
  initCommandPalette();
  initTitleDropdown();
  initModuleSwitchDropdown();
  initHeaderTabFade();
  document.querySelectorAll("[data-tabs]").forEach(initTabs);
```

with:

```javascript
document.addEventListener("DOMContentLoaded", () => {
  initCommandPalette();
  initModuleSwitchDropdown();
  initHeaderTabFade();
  document.querySelectorAll("[data-tabs]").forEach(initTabs);
```

- [ ] **Step 4: Remove dead CSS**

In `app/static/css/style.css`, delete the `/* ── Title-click module dropdown ── */` block (the `.fh-title-wrap`, `.fh-title-trigger`, `.fh-title-chevron`, `.fh-title-dd`, `.fh-title-dd-item` rules) — no template references these classes anymore once every module template has removed its content-area `<h1>` module title (Tasks 2-4; Bank/Users never had one wrapped by `initTitleDropdown` in a way that mattered post-migration since their `<h1>` stays but `initTitleDropdown()` itself is gone).

Leave `app/static/css/budget.css:348` (`.fh-page-header { position: static !important; }`) unchanged — do not delete it. `app/templates/etf_payment_application/index.html` still carries `id="pa-page-header" class="fh-page-header"` on its filter/bulk-bar wrapper after Task 4 (only the title+tabs portion moved out, not the element itself), so this print rule is still live.

- [ ] **Step 5: Run the full test suite**

Run: `cd app && python -m pytest -v`
Expected: all tests pass.

- [ ] **Step 6: Full manual regression pass**

Using the running dev server, visit every module and confirm against the spec's three header states:
- `/dashboard` — State A, flat module list.
- `/beasiswa`, `/payment-memo`, `/etf-payment-application`, `/bank`, `/sponsorship/`, `/budget/master` — State B, `{{ module }} ▾` + that module's own tabs, correct one highlighted.
- `/users` — State C, bare `Users ▾` with no tabs.
- Module-switch dropdown: open it from at least 3 different modules, confirm it lists all 8 modules with the current one marked, and clicking another navigates correctly.
- Alt+K palette still opens/searches/navigates identically.
- Alt+←/→ still steps tabs on Beasiswa/Payment Memo/Payment Application.
- `F` still toggles the filter panel on Beasiswa/Payment Memo/Payment Application.
- Full Screen (Focus Mode) on Beasiswa/Payment Memo/Payment Application: navbar (dropdown + tabs) stays visible and clickable; company/user/theme/logout controls hide; filter panel hides; exit button restores everything.
- Narrow a module with many tabs (Payment Approval Memo, 9 tabs) to a narrow viewport and confirm the tab strip scrolls horizontally with a trailing fade, no tabs clipped or hidden behind a menu.
- Dark mode: toggle it on at least Dashboard and one State-B module, confirm the dropdown, tabs, and fade gradient all theme correctly.
- Sponsorship's `wrong_company` notice (log in with a company that isn't ETF and visit `/sponsorship/`) still hides the tabs and shows the notice.

- [ ] **Step 7: Commit**

```bash
git add app/templates/base.html app/static/js/app.js app/static/css/style.css app/static/css/budget.css app/modules/dashboard/routes.py app/modules/beasiswa/routes.py app/modules/payment_memo/routes.py app/modules/etf_payment_application/routes.py app/modules/bank/routes.py app/modules/users/routes.py app/modules/sponsorship/routes.py app/modules/budget/routes.py
git commit -m "chore: retire unified-header migration flag and dead title-dropdown code"
```
