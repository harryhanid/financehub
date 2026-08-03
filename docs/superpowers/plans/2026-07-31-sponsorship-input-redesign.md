# Sponsorship Input Form Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure the Sponsorship Input page and its mirror-field Edit modal from a flat, un-styled 17-field `<label>` stack into a grouped 2-column grid with a collapsed "Lanjutan" section for the 4 rarely-changed administrative fields — pure visual restructuring, zero field `id`/JS changes.

**Architecture:** New CSS rules added to the existing `sponsorship.css` (module-scoped, no blast radius elsewhere). `input.html`'s `#sp-input-form` and `data.html`'s `#sp-edit-form` each get their `<label>` stack replaced by the new grouped-grid markup, keeping every existing `id`, Jinja loop, and hidden input exactly as-is.

**Tech Stack:** Flask + Jinja2 template, plain CSS (no build step), existing vanilla JS in `sponsorship.js` untouched.

**Spec:** `docs/superpowers/specs/2026-07-31-sponsorship-input-redesign-design.md`

## Global Constraints

- Zero changes to any field `id` (`sp-in-*` / `sp-ed-*`) — `sponsorship.js` reads every field by id and must not need any edit.
- Zero changes to `sponsorship.js`, `dashboard.html`, `outstanding.html`, `report.html`.
- COA/CC Total/CC/Source stay fully editable (not read-only) — just moved into a collapsed `<details>` "Lanjutan" section, closed by default.
- New CSS lives in `app/static/css/sponsorship.css` (confirmed used only by this module's 5 pages) — reuses the existing `--bg-card`/`--border-color`/`--text-primary`/`--text-secondary`/`--text-muted`/`--radius-md`/`--bg-muted` tokens already available on `.budget-page`, no new tokens.
- No frontend test framework in this codebase — verification is app-boot + force-render + structural grep-checks.

---

## Task 1: Add the new form CSS to `sponsorship.css`

**Files:**
- Modify: `app/static/css/sponsorship.css` (append at end of file)

**Interfaces:**
- Produces: CSS classes `.sp-form-card`, `.sp-form-section-title` (+ `.sp-form-section-title-divider`), `.sp-form-grid`, `.sp-form-field` (+ `.sp-form-span2`), `.sp-form-advanced` — consumed by Task 2 (`input.html`) and Task 3 (`data.html`).

- [ ] **Step 1: Append the CSS**

In `app/static/css/sponsorship.css`, append this block at the end of the file (after the existing `.sp-report-pct-row` rule):

```css

/* ── Input / Edit form redesign ──────────────────────────────────────────── */
.sp-form-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 1.25rem 1.5rem;
}
.sp-form-section-title {
  font-size: 0.72rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-secondary);
  margin-bottom: 0.75rem;
}
.sp-form-section-title.sp-form-section-title-divider {
  margin-top: 1rem;
  padding-top: 0.75rem;
  border-top: 1px solid var(--border-color);
}
.sp-form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0 1rem;
}
.sp-form-field {
  margin-bottom: 0.7rem;
}
.sp-form-field.sp-form-span2 {
  grid-column: span 2;
}
.sp-form-field label {
  display: block;
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 0.25rem;
}
.sp-form-field input,
.sp-form-field select {
  width: 100%;
  box-sizing: border-box;
  padding: 0.45rem 0.6rem;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  font-size: 0.85rem;
  background: var(--bg-card);
  color: var(--text-primary);
}
.sp-form-field input[readonly] {
  background: var(--bg-muted);
  color: var(--text-muted);
}

/* Lanjutan (COA/CC Total/CC/Source) disclosure */
.sp-form-advanced {
  margin-top: 0.75rem;
}
.sp-form-advanced > summary {
  cursor: pointer;
  font-size: 0.8rem;
  color: var(--text-muted);
  font-weight: 600;
  list-style: none;
}
.sp-form-advanced > summary::-webkit-details-marker { display: none; }
.sp-form-advanced > summary::before {
  content: "▸ ";
}
.sp-form-advanced[open] > summary::before {
  content: "▾ ";
}
.sp-form-advanced .sp-form-grid {
  grid-template-columns: 1fr;
  margin-top: 0.6rem;
}
```

- [ ] **Step 2: Confirm the file is still valid CSS**

Run: `cd app && python3 -c "print(open('static/css/sponsorship.css', encoding='utf-8').read().count('{') == open('static/css/sponsorship.css', encoding='utf-8').read().count('}'))"`
Expected: `True`

- [ ] **Step 3: Commit**

```bash
git add app/static/css/sponsorship.css
git commit -m "feat: add grouped-form CSS for Sponsorship Input/Edit redesign"
```

---

## Task 2: Restructure `input.html`'s form

**Files:**
- Modify: `app/templates/sponsorship/input.html:16-47`

**Interfaces:**
- Consumes: CSS classes from Task 1.
- Produces: no change to any `id` — `sponsorshipInputSubmit()` in `sponsorship.js` continues to work unmodified.

- [ ] **Step 1: Replace the form markup**

In `app/templates/sponsorship/input.html`, find (lines 16-47):

```html
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
```

Replace with:

```html
  <form id="sp-input-form" class="sp-form-card">
    <div class="sp-form-section-title">Kategori Transaksi</div>
    <div class="sp-form-grid">
      <div class="sp-form-field">
        <label>Cat</label>
        <select id="sp-in-cat">{% for c in cat_choices %}<option value="{{ c }}">{{ c }}</option>{% endfor %}</select>
      </div>
      <div class="sp-form-field">
        <label>Description</label>
        <select id="sp-in-description">{% for d in description_choices %}<option value="{{ d }}">{{ d }}</option>{% endfor %}</select>
      </div>
      <div class="sp-form-field sp-form-span2">
        <label>Cat1 (Perusahaan)</label>
        <input type="text" id="sp-in-cat1-search" placeholder="Cari perusahaan...">
        <input type="hidden" id="sp-in-cat1">
        <div id="sp-in-cat1-results" class="sp-autocomplete-results"></div>
      </div>
      <div class="sp-form-field">
        <label>Cat2</label>
        <input type="text" id="sp-in-cat2" readonly>
      </div>
      <div class="sp-form-field">
        <label>Cat3 (Pillar)</label>
        <input type="text" id="sp-in-cat3" readonly>
      </div>
      <div class="sp-form-field sp-form-span2">
        <label>Cat4</label>
        <select id="sp-in-cat4"><option value="">(blank)</option>{% for c in cat4_choices %}<option value="{{ c }}">{{ c }}</option>{% endfor %}</select>
      </div>
    </div>

    <div class="sp-form-section-title sp-form-section-title-divider">Detail &amp; Tanggal</div>
    <div class="sp-form-grid">
      <div class="sp-form-field sp-form-span2">
        <label>Lembaga/Perorangan</label>
        <input type="text" id="sp-in-lembaga" list="sp-lembaga-datalist" autocomplete="off">
        <datalist id="sp-lembaga-datalist"></datalist>
      </div>
      <div class="sp-form-field">
        <label>Tanggal Form Sponsor</label>
        <input type="date" id="sp-in-tanggal-form">
      </div>
      <div class="sp-form-field">
        <label>Tanggal Payment</label>
        <input type="date" id="sp-in-tanggal-payment">
      </div>
      <div class="sp-form-field sp-form-span2">
        <label>Perihal</label>
        <input type="text" id="sp-in-perihal">
      </div>
      <div class="sp-form-field">
        <label>Amount Request</label>
        <input type="number" id="sp-in-amount" min="0">
      </div>
      <div class="sp-form-field">
        <label>Reff</label>
        <input type="text" id="sp-in-reff">
      </div>
      <div class="sp-form-field sp-form-span2">
        <label>Status</label>
        <input type="text" id="sp-in-status">
      </div>
    </div>

    <details class="sp-form-advanced">
      <summary>Lanjutan (COA, CC Total, CC, Source)</summary>
      <div class="sp-form-grid">
        <div class="sp-form-field sp-form-span2">
          <label>COA</label>
          <input type="text" id="sp-in-coa" value="701078002">
        </div>
        <div class="sp-form-field sp-form-span2">
          <label>CC Total</label>
          <input type="text" id="sp-in-cc-total" value="SMT - Corporate Communication">
        </div>
        <div class="sp-form-field sp-form-span2">
          <label>CC</label>
          <input type="text" id="sp-in-cc" value="POSPON">
        </div>
        <div class="sp-form-field sp-form-span2">
          <label>Source</label>
          <input type="text" id="sp-in-source" value="Sponsor">
        </div>
      </div>
    </details>
  </form>
```

- [ ] **Step 2: App-boot and force-render sanity check**

Run:
```bash
cd app && python -c "
from app import create_app
app = create_app()
print('APP_BOOT_OK')
"
```
Expected: `APP_BOOT_OK`, no exceptions.

- [ ] **Step 3: Grep-confirm every field id survived the restructure**

Run:
```bash
cd app && for id in sp-in-cat sp-in-description sp-in-cat1-search sp-in-cat1 sp-in-cat1-results sp-in-cat2 sp-in-cat3 sp-in-cat4 sp-in-lembaga sp-lembaga-datalist sp-in-tanggal-form sp-in-tanggal-payment sp-in-perihal sp-in-amount sp-in-reff sp-in-status sp-in-coa sp-in-cc-total sp-in-cc sp-in-source; do
  count=$(grep -c "id=\"$id\"" templates/sponsorship/input.html)
  if [ "$count" != "1" ]; then echo "MISMATCH: $id appears $count times"; fi
done
echo "CHECK_DONE"
```
Expected: `CHECK_DONE` with no `MISMATCH` lines printed above it.

- [ ] **Step 4: Grep-confirm `sponsorship.js` has zero diff**

Run: `cd /c/Financehub && git diff --stat app/static/js/sponsorship.js`
Expected: empty output (this task touches no JS).

- [ ] **Step 5: Commit**

```bash
git add app/templates/sponsorship/input.html
git commit -m "feat: restructure Sponsorship Input form into grouped grid layout"
```

---

## Task 3: Restructure `data.html`'s Edit modal form

**Files:**
- Modify: `app/templates/sponsorship/data.html:112-143`

**Interfaces:**
- Consumes: CSS classes from Task 1.
- Produces: no change to any `id` — `sponsorshipDataSave()` in `sponsorship.js` continues to work unmodified.

**Note on field order:** the Edit modal's current field order is `Lembaga → Tanggal Form Sponsor → Perihal → Amount → Tanggal Payment → Reff → Status` — different from Input's `Lembaga → Tanggal Form Sponsor → Tanggal Payment → Perihal → Amount → Reff → Status`. In a 2-column grid where `Lembaga`/`Perihal`/`Status` are full-width (`span2`) and the rest are half-width, Edit's native order leaves a gap (a lone half-width field stranded next to a forced-full-width one). This task reorders the Edit modal's fields to match Input's grid-clean order — this only changes visual/tab order, not any `id`, value, or JS behavior, so `sponsorshipDataSave()` (which reads every field by `id`, not by position) needs no change.

- [ ] **Step 1: Replace the modal form markup**

In `app/templates/sponsorship/data.html`, find (lines 112-143):

```html
        <form id="sp-edit-form">
          <input type="hidden" id="sp-ed-id">
          <label>Cat
            <select id="sp-ed-cat">{% for c in cat_choices %}<option value="{{ c }}">{{ c }}</option>{% endfor %}</select>
          </label>
          <label>Description
            <select id="sp-ed-description">{% for d in description_choices %}<option value="{{ d }}">{{ d }}</option>{% endfor %}</select>
          </label>
          <label>Cat1 (Perusahaan)
            <input type="text" id="sp-ed-cat1-search" placeholder="Cari perusahaan...">
            <input type="hidden" id="sp-ed-cat1">
            <div id="sp-ed-cat1-results" class="sp-autocomplete-results"></div>
          </label>
          <label>Cat2 <input type="text" id="sp-ed-cat2" readonly></label>
          <label>Cat3 (Pillar) <input type="text" id="sp-ed-cat3" readonly></label>
          <label>Cat4
            <select id="sp-ed-cat4"><option value="">(blank)</option>{% for c in cat4_choices %}<option value="{{ c }}">{{ c }}</option>{% endfor %}</select>
          </label>
          <label>Lembaga/Perorangan
            <input type="text" id="sp-ed-lembaga" list="sp-lembaga-datalist" autocomplete="off">
          </label>
          <label>Tanggal Form Sponsor <input type="date" id="sp-ed-tanggal-form"></label>
          <label>Perihal <input type="text" id="sp-ed-perihal"></label>
          <label>Amount Request <input type="number" id="sp-ed-amount" min="0"></label>
          <label>Tanggal Payment <input type="date" id="sp-ed-tanggal-payment"></label>
          <label>Reff <input type="text" id="sp-ed-reff"></label>
          <label>Status <input type="text" id="sp-ed-status"></label>
          <label>COA <input type="text" id="sp-ed-coa"></label>
          <label>CC Total <input type="text" id="sp-ed-cc-total"></label>
          <label>CC <input type="text" id="sp-ed-cc"></label>
          <label>Source <input type="text" id="sp-ed-source"></label>
        </form>
```

Replace with:

```html
        <form id="sp-edit-form" class="sp-form-card">
          <input type="hidden" id="sp-ed-id">
          <div class="sp-form-section-title">Kategori Transaksi</div>
          <div class="sp-form-grid">
            <div class="sp-form-field">
              <label>Cat</label>
              <select id="sp-ed-cat">{% for c in cat_choices %}<option value="{{ c }}">{{ c }}</option>{% endfor %}</select>
            </div>
            <div class="sp-form-field">
              <label>Description</label>
              <select id="sp-ed-description">{% for d in description_choices %}<option value="{{ d }}">{{ d }}</option>{% endfor %}</select>
            </div>
            <div class="sp-form-field sp-form-span2">
              <label>Cat1 (Perusahaan)</label>
              <input type="text" id="sp-ed-cat1-search" placeholder="Cari perusahaan...">
              <input type="hidden" id="sp-ed-cat1">
              <div id="sp-ed-cat1-results" class="sp-autocomplete-results"></div>
            </div>
            <div class="sp-form-field">
              <label>Cat2</label>
              <input type="text" id="sp-ed-cat2" readonly>
            </div>
            <div class="sp-form-field">
              <label>Cat3 (Pillar)</label>
              <input type="text" id="sp-ed-cat3" readonly>
            </div>
            <div class="sp-form-field sp-form-span2">
              <label>Cat4</label>
              <select id="sp-ed-cat4"><option value="">(blank)</option>{% for c in cat4_choices %}<option value="{{ c }}">{{ c }}</option>{% endfor %}</select>
            </div>
          </div>

          <div class="sp-form-section-title sp-form-section-title-divider">Detail &amp; Tanggal</div>
          <div class="sp-form-grid">
            <div class="sp-form-field sp-form-span2">
              <label>Lembaga/Perorangan</label>
              <input type="text" id="sp-ed-lembaga" list="sp-lembaga-datalist" autocomplete="off">
            </div>
            <div class="sp-form-field">
              <label>Tanggal Form Sponsor</label>
              <input type="date" id="sp-ed-tanggal-form">
            </div>
            <div class="sp-form-field">
              <label>Tanggal Payment</label>
              <input type="date" id="sp-ed-tanggal-payment">
            </div>
            <div class="sp-form-field sp-form-span2">
              <label>Perihal</label>
              <input type="text" id="sp-ed-perihal">
            </div>
            <div class="sp-form-field">
              <label>Amount Request</label>
              <input type="number" id="sp-ed-amount" min="0">
            </div>
            <div class="sp-form-field">
              <label>Reff</label>
              <input type="text" id="sp-ed-reff">
            </div>
            <div class="sp-form-field sp-form-span2">
              <label>Status</label>
              <input type="text" id="sp-ed-status">
            </div>
          </div>

          <details class="sp-form-advanced">
            <summary>Lanjutan (COA, CC Total, CC, Source)</summary>
            <div class="sp-form-grid">
              <div class="sp-form-field sp-form-span2">
                <label>COA</label>
                <input type="text" id="sp-ed-coa">
              </div>
              <div class="sp-form-field sp-form-span2">
                <label>CC Total</label>
                <input type="text" id="sp-ed-cc-total">
              </div>
              <div class="sp-form-field sp-form-span2">
                <label>CC</label>
                <input type="text" id="sp-ed-cc">
              </div>
              <div class="sp-form-field sp-form-span2">
                <label>Source</label>
                <input type="text" id="sp-ed-source">
              </div>
            </div>
          </details>
        </form>
```

Note the `sp-ed-*` fields keep their original bare (no `value=`) attributes exactly as before — the Edit modal is always populated from an existing record via JS (`sponsorshipDataSave`'s counterpart populate function), never pre-filled with hardcoded defaults like the Input form is.

- [ ] **Step 2: App-boot and force-render sanity check**

Run:
```bash
cd app && python -c "
from app import create_app
app = create_app()
print('APP_BOOT_OK')
"
```
Expected: `APP_BOOT_OK`, no exceptions.

- [ ] **Step 3: Grep-confirm every field id survived the restructure**

Run:
```bash
cd app && for id in sp-ed-id sp-ed-cat sp-ed-description sp-ed-cat1-search sp-ed-cat1 sp-ed-cat1-results sp-ed-cat2 sp-ed-cat3 sp-ed-cat4 sp-ed-lembaga sp-ed-tanggal-form sp-ed-tanggal-payment sp-ed-perihal sp-ed-amount sp-ed-reff sp-ed-status sp-ed-coa sp-ed-cc-total sp-ed-cc sp-ed-source; do
  count=$(grep -c "id=\"$id\"" templates/sponsorship/data.html)
  if [ "$count" != "1" ]; then echo "MISMATCH: $id appears $count times"; fi
done
echo "CHECK_DONE"
```
Expected: `CHECK_DONE` with no `MISMATCH` lines printed above it.

- [ ] **Step 4: Grep-confirm `sponsorship.js` has zero diff**

Run: `cd /c/Financehub && git diff --stat app/static/js/sponsorship.js`
Expected: empty output.

- [ ] **Step 5: Commit**

```bash
git add app/templates/sponsorship/data.html
git commit -m "feat: restructure Sponsorship Edit modal into grouped grid layout"
```

---

## Task 4: Final verification — zero blast radius + regression

**Files:**
- None modified (verification only)

**Interfaces:**
- Consumes: everything from Tasks 1-3

- [ ] **Step 1: Confirm zero blast radius on the other 3 module pages**

Run:
```bash
cd /c/Financehub && git diff --stat HEAD~3 -- app/templates/sponsorship/dashboard.html app/templates/sponsorship/outstanding.html app/templates/sponsorship/report.html app/static/js/sponsorship.js
```
Expected: empty output.

- [ ] **Step 2: Force-render both pages end-to-end**

Run:
```bash
cd app && python -c "
from app import create_app
app = create_app()
app.config['TESTING'] = True
with app.test_client() as c:
    with c.session_transaction() as sess:
        sess['user'] = 'test'
        sess['company_id'] = 2
        sess['role'] = 'admin'
    r1 = c.get('/sponsorship/input')
    r2 = c.get('/sponsorship/data')
    print('INPUT_STATUS', r1.status_code)
    print('DATA_STATUS', r2.status_code)
"
```
Expected: both `200`. If either instead redirects (fake session insufficient for this app's auth), confirm no 500/Jinja traceback in the output instead — that's the actual thing this check guards against.

- [ ] **Step 3: Full Python regression suite**

Run: `cd app && python -m pytest tests/ -k "sponsorship" -q`
Expected: all pass (no backend code was touched in any of the 3 tasks, so this should be unaffected either way — run as a standard sanity check).

- [ ] **Step 4: Manual browser check (if a preview session is available)**

Navigate to `/sponsorship/input`, confirm: two labeled groups render side-by-side in a 2-column grid, "Lanjutan" starts collapsed and expands on click showing COA/CC Total/CC/Source with their pre-filled defaults intact, Cat2/Cat3 render with the muted readonly background. Repeat on `/sponsorship/data` by opening the Edit modal on any row, confirming the same layout plus that existing field values populate correctly into the new markup. Skip this step if no preview/browser session is available — do not block on it.
