# FLOW Beasiswa — Laporan Siswa PDF Redesign

## Problem

The "Report Siswa" PDF export (Eka Tjipta Foundation → Beasiswa → Report
Siswa → download PDF) is a plain, generic-looking ReportLab document:
no branding, a bare title, and tables styled with stock blue/green header
fills. It doesn't reflect FLOW's established visual identity (the
cobalt→cyan flow-line mark, Figtree typography, clean letterhead treatment
already used on the login/company-select screens).

## Goal

Redesign this one PDF's visual styling — letterhead header with the real
FLOW mark, on-brand typography and accent colors, cleaner table
treatment — while keeping its content and structure exactly as-is (same
sections, same data, same fields). This is a styling pass, not a content
change.

## Scope

- **In scope:** the PDF branch of `GET /beasiswa/laporan/siswa/<code>/export/pdf`
  (`laporan_export()` in `app/modules/beasiswa/routes.py:611-796`) — this
  is the only export the "Report Siswa" tab's PDF button produces.
- **Out of scope:** the CSV branch of the same route (unchanged), and every
  other PDF export in the app (Budget, Payment, Rekap Beasiswa) — none of
  those were part of this ask; restyling them is a separate, future
  decision if wanted.

## Design (visual direction approved via visual companion)

Clean letterhead style — light background (this is a printed/official
document, not a themed app screen, so it does not use FLOW's dark-mode
palette): white page, near-black ink, FLOW's brand colors used only as
accents (icon fill, section rule, table header/accent tints), Figtree for
all text, DM Mono for small metadata labels — matching the type pairing
already established on `company_select.html`.

### Header (letterhead)

Top of page: the real FLOW mark (26×26, cobalt→cyan gradient square,
white two-line flow icon — see Technical Approach for exactly how this
renders, since it must match the live app's mark pixel-for-pixel, not an
approximation) + "FLOW" wordmark, with the company name and print date
right-aligned on the same line. A 2px dark rule underneath separates the
letterhead from the report body.

### Title block

Report title ("Laporan Siswa") in large bold type, directly below the
letterhead. Student name + code as a smaller monospace subtitle line
underneath (e.g. "Angelberta Marta Liwun · 4250015").

### Data Siswa (student info table)

Same 2-column label/value layout as today, restyled: light-grey uppercase
mono labels, hairline row separators instead of solid grid lines, no cell
background fills.

### IPK (unchanged content, restyled)

Same section as today (semester + penelitian scores, only rendered when
present) — restyled to match the same section-title treatment (small
bold uppercase heading with a left accent rule) used for every other
section below, and the same hairline-table look as the info table.

### Rekapitulasi per Kategori

Section title with a 3px cobalt left-accent rule (this treatment — small
bold uppercase title, cobalt rule on the left — is reused for every
section heading from here down, replacing today's plain `Heading2`).
Table: dark header row (near-black, not the current bright blue), white
text, zebra-striped body rows, a highlighted total row (light cobalt
tint background, cobalt text) — same red-for-negative-selisih logic as
today, colors unchanged (still `#dc2626`).

### Detail Budget / Detail Payment

Same section-title treatment. Table headers use a light tint of their
existing identity color instead of a solid fill — Budget keeps a
blue-family header (light cobalt tint background, cobalt text, cobalt
underline), Payment keeps its distinct green family (light green tint,
green text, green underline) — preserving today's visual distinction
between the two tables while making both feel like the same design
system instead of two different hardcoded colors. Body rows keep
zebra-striping; the bold total footer row is unchanged in behavior.

### Footer

Page number only, right-aligned, small grey mono text. **No repeated
"FLOW — Financial Ledger and Operational Workspace" tagline** — that
would be redundant branding when the mark and wordmark already appear in
the letterhead (explicit correction after the first visual draft, which
did include it).

## Technical Approach

- **Stays on ReportLab** — no new PDF library. This is a styling change
  inside the existing `SimpleDocTemplate`/Platypus flow, not a rewrite.
- **FLOW mark asset:** rather than hand-translating the mark's SVG bezier
  paths into ReportLab drawing code (fragile, easy to drift from the
  live app's version), add one pre-rendered PNG of the mark
  (transparent background, the cobalt→cyan gradient square with the
  white two-line flow icon baked in, generated once at a fixed size
  large enough to stay crisp when placed at 26×26pt — e.g. 260×260px) as
  a new static asset at `app/static/img/flow-mark.png`, and place it via
  a Platypus `Image` flowable in the header. This is the only way to get
  a true gradient fill in the PDF without hand-rolling PDF gradient
  drawing code, and it guarantees the mark matches the live app exactly
  since it's rendered from the same source shape once, not reimplemented.
- **Fonts:** register real Figtree (Regular, Medium/600, Bold/700,
  ExtraBold/800) and DM Mono (Regular, Medium/500) TTF files via
  `reportlab.pdfmetrics.registerFont`/`registerFontFamily`, bundled at
  `app/static/fonts/` (Google Fonts, open license, same families already
  loaded as webfonts elsewhere in the app — no new font choice, just
  making the existing brand fonts available to ReportLab). This is a new
  capability for this codebase — no PDF export currently registers a
  custom font, all default to ReportLab's built-in Helvetica family.
  Every `styles["..."]`/`cell_style`/`label_style` font name in
  `laporan_export()`'s PDF branch changes from Helvetica-family names to
  the registered Figtree/DM Mono family names; point sizes stay as
  close to today's as legibility allows (some may need a small bump —
  Figtree renders slightly smaller than Helvetica at the same point size).
- **Colors:** reuse the exact hex values already established elsewhere in
  the app rather than inventing new ones — cobalt `#5B8CFF`, cyan
  `#22D3EE`, near-black ink `#0F1220` / `#1e293b` (table header fill,
  matching the letterhead rule color), existing negative-selisih red
  `#dc2626` (unchanged), existing green-family payment-table accent
  (derive from the current `#065f46` header, lightened for the new tint
  treatment).
- **No true CSS-style gradient fills in ReportLab table cells** — the
  gradient is confined to the pre-rendered PNG mark; every other "cobalt"
  surface in the redesign (rules, tints, header fills) uses a flat cobalt
  or near-black color, not a gradient, since ReportLab's native gradient
  support is limited to canvas-level drawing and not worth the
  complexity for flat table/rule fills.
- Everything data-related in `laporan_export()` (the `get_laporan_siswa()`
  call, the `data["..."]` structure, every field pulled from `s`/
  `cat_summary`/`budget_rows`/`payment_rows`) is untouched — this plan
  only replaces the `styles`/`TableStyle`/`Paragraph`/layout code between
  `buf = io.BytesIO()` and `doc.build(elems)`.

## Testing

- No automated PDF-rendering test exists in this codebase today, and this
  is a pure visual/styling change — verified manually: download the PDF
  for a real ETF student (one with IPK data and one without, to confirm
  the conditional IPK section still renders correctly either way; one
  with a negative selisih category, to confirm the red highlight still
  triggers) and visually compare against the approved mockup direction.
- Confirm the CSV export at the same route is byte-identical to before
  (this plan never touches that branch).

## Out of Scope

- Any other PDF export in the app (Budget, Payment, Rekap Beasiswa) —
  not part of this redesign.
- Any change to the report's data, fields, or the underlying
  `get_laporan_siswa()` query.
- Any change to the CSV export branch of the same route.
- A true vector/gradient re-implementation of the FLOW mark inside
  ReportLab — the pre-rendered PNG approach is the final answer, not a
  placeholder for future vector work.
