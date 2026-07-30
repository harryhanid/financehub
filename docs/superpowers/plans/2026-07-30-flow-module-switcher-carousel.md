# FLOW Module-Switcher Carousel (Alt+Down) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the list-based Alt+Down command palette with an animated, brand-matched card carousel that previews and deep-links each module's sub-tabs, per `docs/superpowers/specs/2026-07-30-flow-module-switcher-carousel-design.md`.

**Architecture:** Two independent layers. (1) Server: each `nav_modules` entry (already company-filtered by `inject_nav_modules()`) gets a `subtabs` list attached, sourced from a small new registry in `dashboard/routes.py`; this is serialized to a JSON `<script>` tag in `base.html`. (2) Client: `initCommandPalette()` in `app.js` is rewritten to read that JSON instead of the static `FH_MODULES` array (fixing a live company-gating bug as a side effect), and its rendering/keyboard logic is rewritten from a scrollable list to a 3-card carousel (prev/active/next) with drag/swipe and arrow-key stepping. The overlay's open/close lifecycle (`#fh-cmd-ov`, Alt+Down trigger, Esc, click-outside) is reused unchanged.

**Tech Stack:** Flask + Jinja2, vanilla JS, existing `style.css`. No new dependencies.

## Global Constraints

- The carousel overlay is a fixed-dark "branded moment" (matches `company_select.html`'s always-dark treatment) — it does **not** adapt to the app's light/dark theme toggle; its own colors are hardcoded hex values, not `--card`/`--bg`-style theme variables, and this is intentional (spec "Visual direction").
- `nav_modules` stays the single source of truth for *which modules exist* — the new `subtabs` data is additive per entry, not a second module registry (spec "Data").
- Payment Approval Memo's sub-tab list depends on `session["company_code"]` exactly like its own header tabs already do (spec "Data").
- Sub-tab click targets reuse the existing `?tab=` deep-link support in `initTabs()` — no new server-side routing logic (spec "Interaction model").
- Untouched: the header's `.fh-mod-dd` click dropdown, Alt+Up (Ganti Perusahaan), Alt+Left/Right (in-module tab stepping), F/Esc filter shortcuts, the "Coming Soon" placeholder entries and their disabled-badge treatment (spec "Out of Scope").
- `prefers-reduced-motion: reduce` disables the glow-pulse/rise animations, matching the existing pattern on `company_select.html` (spec "Testing").
- **Shared checkout hazard:** `app/static/js/app.js` has uncommitted changes from a concurrent session as of plan-writing. Run `git status --porcelain -- app/static/js/app.js` and `git diff -- app/static/js/app.js` before editing it. If unrelated WIP overlaps the lines you need to change, hand-extract your intended hunk into a standalone patch and stage it with `git apply --check --cached` then `git apply --cached` — never a blind `git add` on this file. Never `git add -A`/`git add .`, never `git stash`, never `git checkout <path>`.

## File Structure

- `app/modules/dashboard/routes.py` — gains `MODULE_SUBTABS`, `PAYMENT_MEMO_SUBTABS_SMT`, `PAYMENT_MEMO_SUBTABS_DEFAULT` registries alongside the existing `DASHBOARD_TABS`.
- `app/app.py` — `inject_nav_modules()` attaches a `subtabs` list to each `nav_modules` entry.
- `app/templates/base.html` — adds a JSON `<script>` tag carrying `nav_modules` (with `subtabs`) for the client, and replaces the old `#fh-cmd-ov` modal-list markup with the new carousel markup (search pill, carousel row with arrows, dots, shortcut hint).
- `app/static/js/app.js` — adds `FH_NAV_MODULES` (parsed JSON) and `FH_MODULE_ICONS`; rewrites `initCommandPalette()` from list-rendering to carousel-rendering; keyboard handling switches from Up/Down-selects-row to Left/Right-steps-carousel plus drag/swipe.
- `app/static/css/style.css` — replaces the old `.fh-cmd-modal`/`.fh-cmd-header`/`.fh-cmd-item`/`.fh-cmd-section`/`.fh-cmd-sep` rules with new carousel card/arrow/dots/hint rules.
- `app/tests/test_dashboard.py` — new tests asserting the JSON data's `subtabs` content and company-conditional Payment Approval Memo variant.

---

### Task 1: Server-side sub-tab registry + client data channel

**Files:**
- Modify: `app/modules/dashboard/routes.py:11-20`
- Modify: `app/app.py:66-88`
- Modify: `app/templates/base.html:110-111` (insert JSON script tag before the `app.js` script tag)
- Modify: `app/tests/test_dashboard.py` (add `import json` at top, new tests at end)

**Interfaces:**
- Produces: each `nav_modules` dict entry now has a 4th key, `subtabs` — a list of `{"label": str, "tab": str}` (deep-link via `?tab=`) or `{"label": str, "url": str}` (separate route) entries.
- Produces: `<script type="application/json" id="fh-nav-modules-data">` in `base.html`, containing the full `nav_modules` list (with `subtabs`) as JSON — Task 2's JS reads this by element id.

- [ ] **Step 1: Add the sub-tab registries**

In `app/modules/dashboard/routes.py`, replace (current lines 11-20):

```python
DASHBOARD_TABS = [
    ("Dashboard",             "dashboard.index",               "dashboard"),
    ("Beasiswa",              "beasiswa.index",                "beasiswa"),
    ("Payment Approval Memo", "payment_memo.index",            "payment_memo"),
    ("Payment Application",   "etf_payment_application.index", "etf_payment_app"),
    ("Budget",                "budget.index",                  "budget"),
    ("Bank",                  "bank.index",                    "bank"),
    ("Sponsorship",           "sponsorship.index",             "sponsorship"),
    ("Users",                 "users.index",                   "users"),
]
```

with:

```python
DASHBOARD_TABS = [
    ("Dashboard",             "dashboard.index",               "dashboard"),
    ("Beasiswa",              "beasiswa.index",                "beasiswa"),
    ("Payment Approval Memo", "payment_memo.index",            "payment_memo"),
    ("Payment Application",   "etf_payment_application.index", "etf_payment_app"),
    ("Budget",                "budget.index",                  "budget"),
    ("Bank",                  "bank.index",                    "bank"),
    ("Sponsorship",           "sponsorship.index",             "sponsorship"),
    ("Users",                 "users.index",                   "users"),
]

# Sub-tab previews for the Alt+Down module-switcher carousel. Mirrors each
# module's own {% block module_tabs %} header markup exactly — entries use
# "tab" for the existing ?tab= deep-link (initTabs() in app.js), or "url"
# for modules whose "tabs" are actually separate routes (Budget, Sponsorship).
MODULE_SUBTABS = {
    "dashboard": [],
    "beasiswa": [
        {"label": "Dashboard",     "tab": "dashboard"},
        {"label": "Data Siswa",    "tab": "siswa"},
        {"label": "Data Budget",   "tab": "budget"},
        {"label": "Data Payment",  "tab": "payment"},
        {"label": "Report Siswa",  "tab": "laporan"},
        {"label": "Rekam Medis",   "tab": "rekam"},
        {"label": "Sahabat ETF",   "tab": "sahabat"},
    ],
    "etf_payment_app": [
        {"label": "Open PA", "tab": "summary"},
        {"label": "Advance", "tab": "advance"},
        {"label": "Input",   "tab": "input"},
        {"label": "AGRI",    "tab": "agri"},
        {"label": "APP",     "tab": "app"},
        {"label": "LAND",    "tab": "sml"},
        {"label": "SETF",    "tab": "setf"},
    ],
    "budget": [
        {"label": "Kelola Budget",         "url": "/budget/master"},
        {"label": "Kelola Realisasi",      "url": "/budget/realisasi"},
        {"label": "Carryover / Tambahan",  "url": "/budget/carryover"},
    ],
    "bank": [
        {"label": "Mutasi & Saldo", "tab": "mutasi"},
        {"label": "Open",           "tab": "open"},
    ],
    "sponsorship": [
        {"label": "Dashboard", "url": "/sponsorship/"},
        {"label": "Input",     "url": "/sponsorship/input"},
        {"label": "Data",      "url": "/sponsorship/data"},
        {"label": "Report",    "url": "/sponsorship/report"},
    ],
    "users": [],
}

PAYMENT_MEMO_SUBTABS_SMT = [
    {"label": "Open PAM",   "tab": "draft-pay"},
    {"label": "Input",      "tab": "input-payment"},
    {"label": "PAM List",   "tab": "smt"},
    {"label": "Advance",    "tab": "advance"},
    {"label": "Print Memo", "tab": "draft-memo"},
]
PAYMENT_MEMO_SUBTABS_DEFAULT = [
    {"label": "Open PAM",   "tab": "draft-pay"},
    {"label": "Input",      "tab": "input-payment"},
    {"label": "AGRI",       "tab": "pam"},
    {"label": "APP",        "tab": "fiori"},
    {"label": "LAND",       "tab": "sml"},
    {"label": "SETF",       "tab": "setf"},
    {"label": "Advance",    "tab": "pa-advance"},
    {"label": "Vendors",    "tab": "vendors"},
    {"label": "Print Memo", "tab": "draft-memo"},
]
```

- [ ] **Step 2: Attach `subtabs` to each `nav_modules` entry**

In `app/app.py`, replace (current lines 66-88):

```python
    @app.context_processor
    def inject_nav_modules():
        from modules.dashboard.routes import DASHBOARD_TABS
        from flask_jwt_extended import get_jwt
        from flask import session
        try:
            get_jwt()
        except Exception:
            return {"nav_modules": []}
        # Beasiswa is ETF-only, Sponsorship is SMT-only — hide the module that
        # doesn't apply to the active company instead of showing a dead link.
        company_code = session.get("company_code")
        hidden_keys = set()
        if company_code == "ETF":
            hidden_keys.add("sponsorship")
        elif company_code == "SMT":
            hidden_keys.add("beasiswa")
        nav_modules = [
            {"name": name, "url": url_for(endpoint), "key": key}
            for name, endpoint, key in DASHBOARD_TABS
            if key not in hidden_keys
        ]
        return {"nav_modules": nav_modules}
```

with:

```python
    @app.context_processor
    def inject_nav_modules():
        from modules.dashboard.routes import (
            DASHBOARD_TABS, MODULE_SUBTABS,
            PAYMENT_MEMO_SUBTABS_SMT, PAYMENT_MEMO_SUBTABS_DEFAULT,
        )
        from flask_jwt_extended import get_jwt
        from flask import session
        try:
            get_jwt()
        except Exception:
            return {"nav_modules": []}
        # Beasiswa is ETF-only, Sponsorship is SMT-only — hide the module that
        # doesn't apply to the active company instead of showing a dead link.
        company_code = session.get("company_code")
        hidden_keys = set()
        if company_code == "ETF":
            hidden_keys.add("sponsorship")
        elif company_code == "SMT":
            hidden_keys.add("beasiswa")

        def _subtabs_for(key):
            if key == "payment_memo":
                return PAYMENT_MEMO_SUBTABS_SMT if company_code == "SMT" else PAYMENT_MEMO_SUBTABS_DEFAULT
            return MODULE_SUBTABS.get(key, [])

        nav_modules = [
            {"name": name, "url": url_for(endpoint), "key": key, "subtabs": _subtabs_for(key)}
            for name, endpoint, key in DASHBOARD_TABS
            if key not in hidden_keys
        ]
        return {"nav_modules": nav_modules}
```

- [ ] **Step 3: Serialize `nav_modules` to a JSON script tag for the client**

In `app/templates/base.html`, replace (current lines 110-111):

```html
<script src="{{ url_for('static', filename='js/app.js') }}"></script>
```

with:

```html
<script type="application/json" id="fh-nav-modules-data">{{ nav_modules | tojson }}</script>
<script src="{{ url_for('static', filename='js/app.js') }}"></script>
```

- [ ] **Step 4: Write the failing tests**

In `app/tests/test_dashboard.py`, add `import json` as the very first line, then append at the end of the file:

```python
def _nav_modules(html):
    marker = '<script type="application/json" id="fh-nav-modules-data">'
    start = html.index(marker) + len(marker)
    end = html.index("</script>", start)
    return json.loads(html[start:end])


def test_nav_modules_subtabs_for_etf(client):
    login(client)
    select_etf(client)
    resp = client.get("/dashboard")
    by_key = {m["key"]: m for m in _nav_modules(resp.data.decode())}
    assert "sponsorship" not in by_key
    assert [t["tab"] for t in by_key["beasiswa"]["subtabs"]] == [
        "dashboard", "siswa", "budget", "payment", "laporan", "rekam", "sahabat"
    ]
    assert [t["tab"] for t in by_key["payment_memo"]["subtabs"]] == [
        "draft-pay", "input-payment", "pam", "fiori", "sml", "setf", "pa-advance", "vendors", "draft-memo"
    ]
    assert by_key["dashboard"]["subtabs"] == []
    assert by_key["users"]["subtabs"] == []


def test_nav_modules_subtabs_for_smt(client):
    login(client)
    select_smt(client)
    resp = client.get("/dashboard")
    by_key = {m["key"]: m for m in _nav_modules(resp.data.decode())}
    assert "beasiswa" not in by_key
    assert [t["tab"] for t in by_key["payment_memo"]["subtabs"]] == [
        "draft-pay", "input-payment", "smt", "advance", "draft-memo"
    ]
    assert [t["url"] for t in by_key["sponsorship"]["subtabs"]] == [
        "/sponsorship/", "/sponsorship/input", "/sponsorship/data", "/sponsorship/report"
    ]
    assert [t["url"] for t in by_key["budget"]["subtabs"]] == [
        "/budget/master", "/budget/realisasi", "/budget/carryover"
    ]
```

- [ ] **Step 5: Run the tests**

Run: `cd app && python -m pytest tests/test_dashboard.py -v`
Expected: all tests pass, including the 2 new ones.

- [ ] **Step 6: Commit**

```bash
git add app/modules/dashboard/routes.py app/app.py app/templates/base.html app/tests/test_dashboard.py
git commit -m "feat: add per-module sub-tab registry for the module-switcher carousel"
```

---

### Task 2: Carousel UI (markup, CSS, JS)

**Files:**
- Modify: `app/templates/base.html:170-180` (replace `#fh-cmd-ov` contents)
- Modify: `app/static/css/style.css:262-349` (replace the command-palette CSS block)
- Modify: `app/static/js/app.js:1-14` (add `FH_NAV_MODULES` + `FH_MODULE_ICONS`), `app/static/js/app.js:33-166` (replace `initCommandPalette()`)

**Interfaces:**
- Consumes: `#fh-nav-modules-data` JSON script tag and `nav_modules[].subtabs` from Task 1.
- Consumes (unchanged): `FH_MODULES` (for the 3 "Coming Soon" placeholder entries only), `_fhRecordVisit()`, `getCurrentModule()` (still used by the not-yet-retired `initTitleDropdown()` — this task does not touch that function or its data source).

**Note:** re-check `git status --porcelain -- app/static/js/app.js` immediately before editing — see Global Constraints.

- [ ] **Step 1: Replace the overlay markup in `base.html`**

Replace (current lines 170-180):

```html
<!-- ── Command Palette Overlay ─────────────────────────── -->
<div id="fh-cmd-ov">
  <div class="fh-cmd-modal">
    <div class="fh-cmd-header">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
      <input id="fh-cmd-input" type="text" placeholder="Cari modul..." autocomplete="off" spellcheck="false">
      <kbd>Esc</kbd>
    </div>
    <div id="fh-cmd-results"></div>
  </div>
</div>
```

with:

```html
<!-- ── Module-Switcher Carousel Overlay (Alt+↓) ──────────── -->
<div id="fh-cmd-ov">
  <div class="fh-cmd-search">
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
    <input id="fh-cmd-input" type="text" placeholder="Cari modul..." autocomplete="off" spellcheck="false">
  </div>
  <div class="fh-cmd-carousel">
    <button type="button" id="fh-cmd-prev" class="fh-cmd-arrow" aria-label="Modul sebelumnya">&#8249;</button>
    <div id="fh-cmd-track" class="fh-cmd-track"></div>
    <button type="button" id="fh-cmd-next" class="fh-cmd-arrow" aria-label="Modul berikutnya">&#8250;</button>
  </div>
  <div id="fh-cmd-dots" class="fh-cmd-dots"></div>
  <div class="fh-cmd-hint"><kbd>&#8592;</kbd><kbd>&#8594;</kbd> pindah &middot; geser &middot; <kbd>Enter</kbd> buka &middot; <kbd>Esc</kbd> tutup</div>
</div>
```

- [ ] **Step 2: Replace the command-palette CSS block**

In `app/static/css/style.css`, replace the entire block from the `/* ── Command Palette Overlay ── */` comment through the end of `.fh-cmd-empty` (current lines 262-349):

```css
/* ── Command Palette Overlay ────────────────────────────── */
#fh-cmd-ov {
  display: none;
  position: fixed; inset: 0;
  background: rgba(15,23,42,.45);
  z-index: 9000;
  align-items: flex-start; justify-content: center;
  padding-top: 88px;
}
#fh-cmd-ov.open { display: flex; }

.fh-cmd-modal {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--r-xl);
  box-shadow: var(--sh-lg);
  width: min(500px, calc(100vw - 2rem));
  overflow: hidden;
}

.fh-cmd-header {
  display: flex; align-items: center; gap: .625rem;
  padding: .75rem 1rem;
  border-bottom: 1px solid var(--border);
  color: var(--text-muted);
}
.fh-cmd-header svg { flex-shrink: 0; }
.fh-cmd-header kbd {
  margin-left: auto; font-size: .65rem; padding: .1rem .35rem;
  background: var(--bg-muted); border: 1px solid var(--border);
  border-radius: 3px; color: var(--text-muted);
  font-family: var(--mono); white-space: nowrap;
}

#fh-cmd-input {
  flex: 1; border: none; outline: none;
  background: transparent; color: var(--ink);
  font-size: .9rem; font-family: inherit;
}

#fh-cmd-results {
  max-height: 360px;
  overflow-y: auto;
  padding: .375rem 0;
}

.fh-cmd-section {
  font-size: .675rem; font-weight: 700;
  letter-spacing: .06em; text-transform: uppercase;
  color: var(--text-muted);
  padding: .5rem 1rem .25rem;
}

.fh-cmd-item {
  display: flex; align-items: center; justify-content: space-between;
  padding: .5rem 1rem;
  cursor: pointer;
  font-size: .85rem;
  color: var(--ink);
  gap: .5rem;
  transition: background .08s;
}
.fh-cmd-item:hover,
.fh-cmd-item.active { background: var(--accent-surface); color: var(--accent-text); }
.fh-cmd-item.disabled {
  opacity: .45; cursor: not-allowed;
}
.fh-cmd-item.disabled:hover,
.fh-cmd-item.disabled.active { background: transparent; color: var(--ink); opacity: .45; }

.fh-cmd-badge {
  font-size: .65rem; font-weight: 600;
  background: var(--bg-muted); color: var(--text-muted);
  border: 1px solid var(--border);
  border-radius: 99px; padding: .1rem .45rem;
  white-space: nowrap; flex-shrink: 0;
}

.fh-cmd-sep {
  height: 1px; background: var(--border); margin: .375rem .75rem;
}

.fh-cmd-empty {
  padding: 1.25rem 1rem;
  text-align: center;
  color: var(--text-muted);
  font-size: .85rem;
}
```

with:

```css
/* ── Module-Switcher Carousel Overlay (Alt+↓) ───────────── */
/* Fixed-dark "branded moment" (matches company_select.html) — does NOT   */
/* adapt to the app's light/dark theme toggle; colors below are           */
/* intentionally hardcoded, not --card/--bg theme variables.              */
#fh-cmd-ov {
  display: none;
  position: fixed; inset: 0;
  background: rgba(6,8,15,.68);
  backdrop-filter: blur(4px);
  z-index: 9000;
  flex-direction: column; align-items: center; justify-content: center;
  padding: 1.5rem;
}
#fh-cmd-ov.open { display: flex; }

.fh-cmd-search {
  width: min(320px, 90%);
  margin-bottom: 1.75rem;
  display: flex; align-items: center; gap: .55rem;
  padding: .65rem 1rem;
  border-radius: 12px;
  background: rgba(255,255,255,.045);
  border: 1px solid rgba(255,255,255,.09);
  color: #6f6d85;
  transition: border-color .2s, box-shadow .2s;
}
.fh-cmd-search:focus-within { border-color: rgba(91,140,255,.4); box-shadow: 0 0 0 3px rgba(91,140,255,.1); }
.fh-cmd-search svg { flex-shrink: 0; opacity: .65; }
#fh-cmd-input {
  flex: 1; border: none; outline: none; background: transparent;
  color: #F0EEF8; font-size: .85rem; font-family: inherit;
}
#fh-cmd-input::placeholder { color: #6f6d85; }

.fh-cmd-carousel { display: flex; align-items: center; justify-content: center; gap: 0; width: 100%; max-width: 720px; }

.fh-cmd-arrow {
  width: 34px; height: 34px; border-radius: 50%; flex-shrink: 0; cursor: pointer;
  background: rgba(255,255,255,.045); border: 1px solid rgba(255,255,255,.1);
  color: #9896B0; font-size: 1.1rem; line-height: 1; font-family: inherit;
  display: flex; align-items: center; justify-content: center;
  transition: transform .18s cubic-bezier(.32,.72,0,1), background .18s, border-color .18s, color .18s, box-shadow .18s;
}
.fh-cmd-arrow:hover {
  transform: scale(1.12); color: #fff; border-color: transparent;
  background: linear-gradient(135deg, #5B8CFF, #22D3EE);
  box-shadow: 0 0 18px rgba(91,140,255,.45);
}

.fh-cmd-track {
  flex: 1; min-width: 0;
  display: flex; align-items: center; justify-content: center;
  touch-action: pan-y;
  cursor: grab;
}
.fh-cmd-track:active { cursor: grabbing; }

.fh-cmd-card-outer {
  background: rgba(255,255,255,.03);
  border: 1px solid rgba(255,255,255,.08);
  border-radius: 22px;
  padding: 5px;
}
.fh-cmd-card-inner {
  background: #0F1220;
  border-radius: 18px;
  padding: 1.4rem 1.2rem 1.1rem;
  text-align: center;
  position: relative;
  overflow: hidden;
}

.fh-cmd-card-main {
  width: 220px; z-index: 5; position: relative; flex-shrink: 0;
  animation: fh-cmd-card-rise .5s cubic-bezier(.22,.72,0,1) both;
}
.fh-cmd-card-main .fh-cmd-card-inner::after {
  content: '';
  position: absolute; inset: -18px; z-index: -1;
  background: radial-gradient(ellipse at center, rgba(91,140,255,.28) 0%, transparent 70%);
  animation: fh-cmd-glow-pulse 3.2s ease-in-out infinite;
}
@keyframes fh-cmd-glow-pulse { 0%,100%{opacity:.55;transform:scale(1)} 50%{opacity:.9;transform:scale(1.08)} }
@keyframes fh-cmd-card-rise { from{opacity:0;transform:translateY(18px) scale(.94)} to{opacity:1;transform:translateY(0) scale(1)} }

.fh-cmd-card-side {
  width: 130px; margin: 0 -18px; flex-shrink: 0;
  transform: scale(.82) translateY(6px);
  opacity: .38;
  cursor: pointer;
  transition: transform .3s cubic-bezier(.22,.72,0,1), opacity .3s;
}
.fh-cmd-card-side:hover { opacity: .6; transform: scale(.86) translateY(4px); }
.fh-cmd-card-side .fh-cmd-card-inner { padding: 1rem .9rem; }

.fh-cmd-icon {
  width: 40px; height: 40px; margin: 0 auto .7rem;
  border-radius: 11px;
  background: linear-gradient(135deg, #5B8CFF, #22D3EE);
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 0 20px rgba(91,140,255,.35), inset 0 1px 1px rgba(255,255,255,.25);
}
.fh-cmd-icon svg { width: 19px; height: 19px; }
.fh-cmd-card-side .fh-cmd-icon { width: 32px; height: 32px; opacity: .7; box-shadow: none; }
.fh-cmd-card-side .fh-cmd-icon svg { width: 15px; height: 15px; }

.fh-cmd-card-name { color: #F0EEF8; font-weight: 800; font-size: .95rem; letter-spacing: -.01em; }
.fh-cmd-card-side .fh-cmd-card-name { font-size: .78rem; font-weight: 700; }

.fh-cmd-tabline { height: 1px; background: linear-gradient(90deg, transparent, rgba(255,255,255,.12), transparent); margin: .8rem -1.2rem .6rem; }

.fh-cmd-tab {
  font-size: .68rem; color: #6f6d85; padding: .3rem 0;
  display: flex; align-items: center; gap: .4rem; justify-content: center;
  cursor: pointer; transition: color .12s;
}
.fh-cmd-tab:hover { color: #9896B0; }
.fh-cmd-tab.active { color: #22D3EE; font-weight: 700; }
.fh-cmd-tab.active::before {
  content: ''; width: 4px; height: 4px; border-radius: 50%; background: #22D3EE; box-shadow: 0 0 6px #22D3EE;
  animation: fh-cmd-dot-pulse 1.8s ease-in-out infinite;
}
@keyframes fh-cmd-dot-pulse { 0%,100%{opacity:.6;transform:scale(1)} 50%{opacity:1;transform:scale(1.5)} }

.fh-cmd-badge {
  display: inline-block; margin-top: .5rem;
  font-size: .62rem; font-weight: 600;
  background: rgba(255,255,255,.06); color: #6f6d85;
  border: 1px solid rgba(255,255,255,.1);
  border-radius: 99px; padding: .15rem .5rem;
}

.fh-cmd-dots { display: flex; justify-content: center; gap: .35rem; margin-top: 1.4rem; }
.fh-cmd-dots span { width: 6px; height: 6px; border-radius: 50%; background: rgba(255,255,255,.15); transition: all .25s cubic-bezier(.32,.72,0,1); }
.fh-cmd-dots span.on { background: linear-gradient(90deg,#5B8CFF,#22D3EE); width: 20px; border-radius: 4px; }

.fh-cmd-hint {
  text-align: center; margin-top: 1.1rem;
  color: #4E4D63; font-size: .62rem; font-family: var(--mono); letter-spacing: .06em;
}
.fh-cmd-hint kbd {
  background: rgba(255,255,255,.06); border: 1px solid rgba(255,255,255,.1);
  border-radius: 4px; padding: .1rem .35rem; margin: 0 .15rem; color: #9896B0;
}

.fh-cmd-empty { color: #6f6d85; font-size: .85rem; text-align: center; padding: 2rem 0; }

@media (prefers-reduced-motion: reduce) {
  .fh-cmd-card-main, .fh-cmd-card-main .fh-cmd-card-inner::after, .fh-cmd-tab.active::before {
    animation: none !important;
  }
}
```

- [ ] **Step 3: Add `FH_NAV_MODULES` and `FH_MODULE_ICONS` to `app.js`**

Replace (current lines 1-15, the module registry + recent-key declaration):

```javascript
/* ── Module registry ──────────────────────────────────── */
const FH_MODULES = [
  { name: "Dashboard",             url: "/dashboard",               active: true  },
  { name: "Beasiswa",              url: "/beasiswa",                active: true  },
  { name: "Payment Approval Memo", url: "/payment-memo",            active: true  },
  { name: "Payment Application",   url: "/etf-payment-application", active: true  },
  { name: "Budget",                url: "/budget/",                 active: true  },
  { name: "Users",                 url: "/users",                   active: true  },
  { name: "Bank",                  url: "/bank",                    active: true  },
  { name: "Account Payable",       url: null,                       active: false },
  { name: "Advance",               url: null,                       active: false },
  { name: "Petty Cash",            url: null,                       active: false },
  { name: "Sponsorship",           url: "/sponsorship/",            active: true  },
];
const FH_RECENT_KEY = 'fh_recent_modules';
```

with:

```javascript
/* ── Module registry ──────────────────────────────────── */
const FH_MODULES = [
  { name: "Dashboard",             url: "/dashboard",               active: true  },
  { name: "Beasiswa",              url: "/beasiswa",                active: true  },
  { name: "Payment Approval Memo", url: "/payment-memo",            active: true  },
  { name: "Payment Application",   url: "/etf-payment-application", active: true  },
  { name: "Budget",                url: "/budget/",                 active: true  },
  { name: "Users",                 url: "/users",                   active: true  },
  { name: "Bank",                  url: "/bank",                    active: true  },
  { name: "Account Payable",       url: null,                       active: false },
  { name: "Advance",               url: null,                       active: false },
  { name: "Petty Cash",            url: null,                       active: false },
  { name: "Sponsorship",           url: "/sponsorship/",            active: true  },
];
const FH_RECENT_KEY = 'fh_recent_modules';

// Company-filtered module list + sub-tab previews for the Alt+Down carousel,
// rendered server-side by inject_nav_modules() in app.py — see base.html's
// #fh-nav-modules-data script tag. Read once at load; server always injects
// this tag (nav_modules is always in template context, empty list when
// logged out), so this never needs to re-fetch.
const FH_NAV_MODULES = (function() {
  var el = document.getElementById('fh-nav-modules-data');
  if (!el) return [];
  try { return JSON.parse(el.textContent); } catch (e) { return []; }
})();

// One small flow-line-style icon per real module, keyed by nav_modules' `key`.
const FH_MODULE_ICONS = {
  dashboard: '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
  beasiswa: '<path d="M12 3 2 8l10 5 10-5-10-5Z"/><path d="M6 10.5V16c0 1.5 3 3 6 3s6-1.5 6-3v-5.5"/>',
  payment_memo: '<path d="M6 2h9l4 4v16H6Z"/><path d="M15 2v4h4"/><path d="M9 13l2 2 4-4"/>',
  etf_payment_app: '<path d="M6 2h8l5 5v15H6Z"/><path d="M14 2v5h5"/><path d="M12 12v6M9 15l3-3 3 3"/>',
  budget: '<path d="M12 12V4a8 8 0 0 1 8 8h-8Z"/><circle cx="12" cy="12" r="8"/>',
  bank: '<path d="M3 10l9-6 9 6"/><path d="M5 10v9M9 10v9M15 10v9M19 10v9"/><path d="M3 21h18"/>',
  sponsorship: '<rect x="3" y="8" width="18" height="13" rx="1"/><path d="M3 12h18"/><path d="M12 8v13"/><path d="M12 8c-1.5-4-6-4-6-1s3 1 6 1Zm0 0c1.5-4 6-4 6-1s-3 1-6 1Z"/>',
  users: '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
};
```

- [ ] **Step 4: Rewrite `initCommandPalette()`**

Replace the entire function (current lines 33-166, from `function initCommandPalette() {` through its closing `}` right before `function initTitleDropdown() {`):

```javascript
function initCommandPalette() {
  /* Record current page in recently-visited (kept for possible future use —
     the carousel itself has no "recently visited" section, see spec). */
  var currentMod = getCurrentModule();
  if (currentMod) _fhRecordVisit(currentMod.url);

  var ov       = document.getElementById('fh-cmd-ov');
  var input    = document.getElementById('fh-cmd-input');
  var track    = document.getElementById('fh-cmd-track');
  var dotsEl   = document.getElementById('fh-cmd-dots');
  var prevBtn  = document.getElementById('fh-cmd-prev');
  var nextBtn  = document.getElementById('fh-cmd-next');
  var btn      = document.getElementById('fh-cmd-btn');
  if (!ov || !input || !track || !dotsEl) return;

  var allModules       = _carouselModules();
  var filtered         = allModules;
  var activeIdx        = 0;
  var openCurrentMod   = null;   // the module the user was in when they opened the overlay
  var openCurrentTab   = null;   // its ?tab= value at open time, if any
  var dragStartX       = null;

  function _carouselModules() {
    var comingSoon = FH_MODULES.filter(function(m) { return !m.active; }).map(function(m) {
      return { name: m.name, url: null, key: null, subtabs: [], active: false };
    });
    var real = FH_NAV_MODULES.map(function(m) {
      return { name: m.name, url: m.url, key: m.key, subtabs: m.subtabs || [], active: true };
    });
    return real.concat(comingSoon);
  }

  function _currentNavModule() {
    return FH_NAV_MODULES.find(function(m) {
      return window.location.pathname.replace(/\/$/, '') === m.url.replace(/\/$/, '');
    });
  }

  function open() {
    filtered = allModules;
    openCurrentMod = _currentNavModule();
    openCurrentTab = new URLSearchParams(window.location.search).get('tab');
    activeIdx = 0;
    if (openCurrentMod) {
      var found = filtered.findIndex(function(m) { return m.key === openCurrentMod.key; });
      if (found !== -1) activeIdx = found;
    }
    input.value = '';
    ov.classList.add('open');
    render();
    input.focus();
  }
  function close() {
    ov.classList.remove('open');
  }

  function step(delta) {
    if (!filtered.length) return;
    activeIdx = (activeIdx + delta + filtered.length) % filtered.length;
    render();
  }

  function _openModule(mod) {
    if (!mod || !mod.active || !mod.url) return;
    _fhRecordVisit(mod.url);
    close();
    window.location.href = mod.url;
  }

  function _openSubtab(mod, t) {
    var dest = t.url || (mod.url + (mod.url.indexOf('?') === -1 ? '?' : '&') + 'tab=' + t.tab);
    _fhRecordVisit(mod.url);
    close();
    window.location.href = dest;
  }

  function _isActiveTab(mod, t) {
    if (!openCurrentMod || mod.key !== openCurrentMod.key) return false;
    if (t.url) return window.location.pathname.replace(/\/$/, '') === t.url.replace(/\/$/, '');
    var defaultTab = mod.subtabs.length ? mod.subtabs[0].tab : null;
    return t.tab === (openCurrentTab || defaultTab);
  }

  function _card(mod, isMain) {
    var outer = document.createElement('div');
    outer.className = isMain ? 'fh-cmd-card-main' : 'fh-cmd-card-side';

    var bezel = document.createElement('div');
    bezel.className = 'fh-cmd-card-outer';
    var inner = document.createElement('div');
    inner.className = 'fh-cmd-card-inner';

    if (mod.key) {
      var icon = document.createElement('div');
      icon.className = 'fh-cmd-icon';
      icon.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">' + (FH_MODULE_ICONS[mod.key] || '') + '</svg>';
      inner.appendChild(icon);
    }

    var name = document.createElement('div');
    name.className = 'fh-cmd-card-name';
    name.textContent = mod.name;
    inner.appendChild(name);

    if (!mod.active) {
      var badge = document.createElement('div');
      badge.className = 'fh-cmd-badge';
      badge.textContent = 'Coming Soon';
      inner.appendChild(badge);
    } else if (isMain && mod.subtabs.length) {
      var line = document.createElement('div');
      line.className = 'fh-cmd-tabline';
      inner.appendChild(line);
      mod.subtabs.forEach(function(t) {
        var row = document.createElement('div');
        row.className = 'fh-cmd-tab' + (_isActiveTab(mod, t) ? ' active' : '');
        row.textContent = t.label;
        row.addEventListener('click', function(e) {
          e.stopPropagation();
          _openSubtab(mod, t);
        });
        inner.appendChild(row);
      });
    }

    if (mod.active && mod.url) {
      outer.style.cursor = 'pointer';
      outer.addEventListener('click', function() {
        if (isMain) { _openModule(mod); }
        else { activeIdx = filtered.indexOf(mod); render(); }
      });
    }

    bezel.appendChild(inner);
    outer.appendChild(bezel);
    return outer;
  }

  function render() {
    track.innerHTML = '';
    dotsEl.innerHTML = '';
    if (!filtered.length) {
      var empty = document.createElement('div');
      empty.className = 'fh-cmd-empty';
      empty.textContent = 'Tidak ada modul ditemukan.';
      track.appendChild(empty);
      return;
    }
    activeIdx = Math.max(0, Math.min(activeIdx, filtered.length - 1));
    for (var i = -1; i <= 1; i++) {
      var idx = activeIdx + i;
      if (idx < 0 || idx >= filtered.length) continue;
      track.appendChild(_card(filtered[idx], i === 0));
    }
    filtered.forEach(function(m, i) {
      var dot = document.createElement('span');
      if (i === activeIdx) dot.className = 'on';
      dotsEl.appendChild(dot);
    });
  }

  input.addEventListener('input', function() {
    var q = input.value.trim().toLowerCase();
    filtered = q ? allModules.filter(function(m) { return m.name.toLowerCase().indexOf(q) !== -1; }) : allModules;
    activeIdx = 0;
    render();
  });

  if (prevBtn) prevBtn.addEventListener('click', function() { step(-1); });
  if (nextBtn) nextBtn.addEventListener('click', function() { step(1); });

  track.addEventListener('pointerdown', function(e) { dragStartX = e.clientX; });
  track.addEventListener('pointerup', function(e) {
    if (dragStartX === null) return;
    var dx = e.clientX - dragStartX;
    dragStartX = null;
    if (dx > 40) step(-1); else if (dx < -40) step(1);
  });

  document.addEventListener('keydown', function(e) {
    if (e.altKey && !e.ctrlKey && !e.metaKey && e.key === 'ArrowDown') {
      e.preventDefault();
      ov.classList.contains('open') ? close() : open();
      return;
    }
    if (!ov.classList.contains('open')) return;
    if (e.key === 'Escape')     { e.preventDefault(); close(); }
    if (e.key === 'ArrowLeft')  { e.preventDefault(); step(-1); }
    if (e.key === 'ArrowRight') { e.preventDefault(); step(1); }
    if (e.key === 'Enter') {
      e.preventDefault();
      _openModule(filtered[activeIdx]);
    }
  });

  ov.addEventListener('click', function(e) { if (e.target === ov) close(); });
  if (btn) btn.addEventListener('click', open);
}
```

- [ ] **Step 5: Manual smoke test**

This is an animation/interaction feature with no automated JS test suite in
this project (consistent with prior UI-layer work this session) — verify
manually using the running dev server:

- Open Alt+Down from Dashboard, from Beasiswa, and from Payment Approval
  Memo. Confirm it centers on the module you're currently in.
- Step with `←`/`→` and with mouse-drag on the card row; confirm the dots
  indicator tracks the active card.
- Type in the search box; confirm the carousel re-centers on the first
  match and the dots reflect the filtered count.
- Click a sub-tab row inside the center card (e.g. Payment Approval
  Memo → "Vendors"); confirm it navigates straight to that tab.
- Confirm the currently-open tab (when you opened the carousel from inside
  a module) shows the pulsing accent dot next to its label.
- Log in as an ETF-session user: confirm no "Sponsorship" card ever
  appears, including while filtering. Log in as SMT: confirm no "Beasiswa"
  card appears.
- Confirm `Esc` and click-on-backdrop both close the overlay without
  navigating.
- Toggle the app's light/dark theme with the overlay closed, then reopen
  it — confirm the overlay still renders in its fixed dark styling either
  way (this is intentional, not a bug — see Global Constraints).
- With OS-level "reduce motion" enabled, confirm the glow-pulse and
  active-tab-dot-pulse animations are disabled.

- [ ] **Step 6: Commit**

```bash
git add app/templates/base.html app/static/css/style.css app/static/js/app.js
git commit -m "feat: replace Alt+Down module list with animated card carousel"
```
