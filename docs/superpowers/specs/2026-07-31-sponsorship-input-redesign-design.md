# Design: Sponsorship Input Form Redesign

**Date:** 2026-07-31
**Module:** Finance Hub — Sub Modul Sponsorship / Input tab + Data tab's Edit modal
**Status:** Approved

---

## Summary

`/sponsorship/input` (and the identical-field Edit modal on `/sponsorship/data`) render their 17 fields as a flat, un-styled vertical stack of `<label>` elements — no grouping, no grid, no `sponsorship.css` rules for the form itself at all (it inherits only the generic `.budget-card` border/shadow). This redesign groups the fields into two labeled clusters inside a single card (2-column grid), and moves 4 rarely-changed administrative fields (COA, CC Total, CC, Source) into a collapsed `<details>` section — without touching any field `id`, any JS behavior, or any other page in the module.

---

## Decisions

| Question | Decision |
|---|---|
| Scope | Both `input.html` (the Input page) and `data.html`'s `#sp-edit-modal` (the Edit modal) — they mirror the same 17 fields, redesigned consistently |
| COA/CC Total/CC/Source | Grouped into a collapsed `<details>` "Lanjutan" section, native HTML disclosure (no extra JS) — stay fully editable, just de-emphasized by default |
| Layout | Single card, 2-column grid, two internal groups separated by a small uppercase section label + divider (not two separate `.budget-card` boxes) |
| CSS file | New rules added directly to the existing `app/static/css/sponsorship.css` — confirmed used only by this module's 5 pages (dashboard/data/input/outstanding/report), so no cross-module blast radius risk (unlike the shared `.budget-*` classes seen in other modules this session) |
| Field ids / JS | Zero changes — `sponsorship.js`'s `sponsorshipInputSubmit()`, `sponsorshipDataSave()`, and the cat1-autocomplete wiring all read by `id`; this is a pure visual restructuring |

---

## Field Grouping

**Group 1 — Kategori Transaksi** (2-col grid; `span2` = full width)
| Field | Width |
|---|---|
| Cat (select) | 1 col |
| Description (select) | 1 col |
| Cat1 — Perusahaan (search input + hidden id + autocomplete results) | span2 |
| Cat2 (readonly, auto-filled from Cat1 selection) | 1 col |
| Cat3 — Pillar (readonly, auto-filled from Cat1 selection) | 1 col |
| Cat4 (select) | span2 |

**Group 2 — Detail & Tanggal**
| Field | Width |
|---|---|
| Lembaga/Perorangan (text + datalist) | span2 |
| Tanggal Form Sponsor (date) | 1 col |
| Tanggal Payment (date) | 1 col |
| Perihal (text) | span2 |
| Amount Request (number) | 1 col |
| Reff (text) | 1 col |
| Status (text) | span2 |

**Group 3 — Lanjutan** (collapsed `<details>`, below the two groups above)
COA, CC Total, CC, Source — same 2-column grid inside, each field full-width (span2) since there are only 4 and pairing them 2-up would look sparse; kept simple as a single column inside the disclosure.

Readonly fields (Cat2, Cat3) get a distinct muted background so they read as "auto-filled, not for typing" rather than just relying on the cursor being blocked.

---

## Architecture

### File changes

- **Modify:** `app/static/css/sponsorship.css` — add new form classes (below).
- **Modify:** `app/templates/sponsorship/input.html` — replace the flat `<label>` stack inside `#sp-input-form` with the grouped/grid structure. Same field `id`s, same `<select>`/`{% for %}` Jinja loops, same hidden inputs — only the wrapping markup and CSS classes change.
- **Modify:** `app/templates/sponsorship/data.html` — same restructuring applied to `#sp-edit-modal`'s `#sp-edit-form` (the `sp-ed-*` ids), lines ~112-143.

No changes to `sponsorship.js`, no changes to `dashboard.html`/`outstanding.html`/`report.html`, no backend/route changes.

### New CSS classes (in `sponsorship.css`)

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

Uses the same `var(--bg-card)`/`var(--border-color)`/`var(--text-primary)`/`var(--text-secondary)`/`var(--text-muted)`/`var(--radius-md)`/`var(--bg-muted)` tokens already defined for `.budget-page` (same pattern established for the Beasiswa Dashboard redesign earlier this session) — no new tokens introduced.

### Markup shape (applies to both `input.html`'s `#sp-input-form` and `data.html`'s `#sp-edit-form`)

```html
<form id="sp-input-form" class="sp-form-card">
  <div class="sp-form-section-title">Kategori Transaksi</div>
  <div class="sp-form-grid">
    <div class="sp-form-field"><label>Cat</label><select id="sp-in-cat">...</select></div>
    <div class="sp-form-field"><label>Description</label><select id="sp-in-description">...</select></div>
    <div class="sp-form-field sp-form-span2">
      <label>Cat1 (Perusahaan)</label>
      <input type="text" id="sp-in-cat1-search" placeholder="Cari perusahaan...">
      <input type="hidden" id="sp-in-cat1">
      <div id="sp-in-cat1-results" class="sp-autocomplete-results"></div>
    </div>
    <div class="sp-form-field"><label>Cat2</label><input type="text" id="sp-in-cat2" readonly></div>
    <div class="sp-form-field"><label>Cat3 (Pillar)</label><input type="text" id="sp-in-cat3" readonly></div>
    <div class="sp-form-field sp-form-span2">
      <label>Cat4</label>
      <select id="sp-in-cat4"><option value="">(blank)</option>...</select>
    </div>
  </div>

  <div class="sp-form-section-title sp-form-section-title-divider">Detail &amp; Tanggal</div>
  <div class="sp-form-grid">
    <div class="sp-form-field sp-form-span2">
      <label>Lembaga/Perorangan</label>
      <input type="text" id="sp-in-lembaga" list="sp-lembaga-datalist" autocomplete="off">
      <datalist id="sp-lembaga-datalist"></datalist>
    </div>
    <div class="sp-form-field"><label>Tanggal Form Sponsor</label><input type="date" id="sp-in-tanggal-form"></div>
    <div class="sp-form-field"><label>Tanggal Payment</label><input type="date" id="sp-in-tanggal-payment"></div>
    <div class="sp-form-field sp-form-span2"><label>Perihal</label><input type="text" id="sp-in-perihal"></div>
    <div class="sp-form-field"><label>Amount Request</label><input type="number" id="sp-in-amount" min="0"></div>
    <div class="sp-form-field"><label>Reff</label><input type="text" id="sp-in-reff"></div>
    <div class="sp-form-field sp-form-span2"><label>Status</label><input type="text" id="sp-in-status"></div>
  </div>

  <details class="sp-form-advanced">
    <summary>Lanjutan (COA, CC Total, CC, Source)</summary>
    <div class="sp-form-grid">
      <div class="sp-form-field sp-form-span2"><label>COA</label><input type="text" id="sp-in-coa" value="701078002"></div>
      <div class="sp-form-field sp-form-span2"><label>CC Total</label><input type="text" id="sp-in-cc-total" value="SMT - Corporate Communication"></div>
      <div class="sp-form-field sp-form-span2"><label>CC</label><input type="text" id="sp-in-cc" value="POSPON"></div>
      <div class="sp-form-field sp-form-span2"><label>Source</label><input type="text" id="sp-in-source" value="Sponsor"></div>
    </div>
  </details>
</form>
```

The Edit modal's version is identical in structure with `sp-ed-*` ids substituted for `sp-in-*` (and no default `value=` attributes on the Lanjutan fields there, since the Edit form is populated from existing record data via JS, not pre-filled defaults — matching current behavior exactly).

---

## Testing

No frontend test framework in this codebase. Verification:

- App-boot sanity check.
- Force-render `/sponsorship/input` and `/sponsorship/data` via Flask test client — 200 OK, no Jinja error.
- Grep-check: every `sp-in-*` id present in the original `input.html` still appears exactly once in the new markup (and same for `sp-ed-*` in `data.html`) — proves the restructuring didn't drop or duplicate a field.
- Grep-check: `sponsorship.js` diff is empty (this task touches zero JS).
- Grep-check: `dashboard.html`/`outstanding.html`/`report.html` diffs are empty (zero blast radius within the module).
- Manual browser check if a preview session is available; skip if not.

## Out of Scope

- Any change to `sponsorship.js` behavior (autocomplete, submit, validation).
- Any change to `dashboard.html`, `outstanding.html`, `report.html`.
- Changing which fields are required/optional, or adding new validation.
- Converting COA/CC Total/CC/Source to read-only — they stay editable, per the Decisions table.
