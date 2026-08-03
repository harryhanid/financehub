# FLOW Beasiswa — Laporan Siswa PDF Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restyle the Report Siswa PDF (`GET /beasiswa/laporan/siswa/<code>/export/pdf`) into a FLOW-branded letterhead document — same content, same data, new visual design — per `docs/superpowers/specs/2026-08-03-flow-beasiswa-laporan-siswa-pdf-redesign-design.md`.

**Architecture:** One new static asset (a pre-rendered PNG of the FLOW mark, generated once by a script this plan includes and validates) plus a full restyle of the existing `if fmt == "pdf":` block in `laporan_export()` — same ReportLab `SimpleDocTemplate`/Platypus flow, same data extraction, new `TableStyle`s, new section-header helper, a letterhead header table, and a page-number footer via a canvas callback (the current PDF has no footer at all — this is the one net-new structural element, not a restyle of something pre-existing).

**Tech Stack:** Flask, ReportLab (already a dependency), Pillow (already installed, used only to generate the one-time PNG asset). No new dependencies.

## Global Constraints

- Fonts stay Helvetica (ReportLab's built-in family) — bundling the real Figtree/DM Mono TTF files was ruled out for this plan (no network access to fetch them in this environment); see the spec's Technical Approach and Out of Scope.
- No true gradient fills inside ReportLab tables/rules — the gradient is confined to the pre-rendered PNG mark; every other cobalt/near-black surface uses a flat color.
- Brand colors are exact hex values already used elsewhere in the app: cobalt `#5B8CFF`, cyan `#22D3EE` (mark gradient only), ink `#0F1220`/`#1e293b`, existing negative-selisih red `#dc2626` (unchanged from today), existing payment-table green family derived from `#065f46`.
- Only the `if fmt == "pdf":` branch of `laporan_export()` changes. The `if fmt == "csv":` branch immediately above it, the data-fetching call (`get_laporan_siswa`) above both branches, and every other route in this file are untouched.
- **Shared checkout hazard:** `app/modules/beasiswa/routes.py` has uncommitted concurrent-session changes as of plan-writing (a `format_rupiah` import and matching call-site changes in *other* export functions — `budget_siswa_export`, `budget_export_pdf`, `payment_export_pdf` — none of which touch `laporan_export()`). Run `git status --porcelain -- app/modules/beasiswa/routes.py` and `git diff -- app/modules/beasiswa/routes.py` before editing. Never `git add -A`/`git add .`, never `git stash`, never `git checkout <path>`. If unrelated WIP overlaps a hunk you need to change, hand-extract your intended hunk into a standalone patch and stage it with `git apply --check --cached` then `git apply --cached` instead of a blind `git add`.
- Every code snippet below was checked against the current content of `app/modules/beasiswa/routes.py` at plan-writing time (which already includes the concurrent session's `format_rupiah`-import WIP). Confirm current line numbers with `grep -n` before editing.

---

### Task 1: Generate and commit the FLOW mark PNG asset

**Files:**
- Create: `app/static/img/flow-mark.png` (new binary asset)
- Create (temporary, not committed): a one-off generator script — write it anywhere convenient (e.g. the repo root or a scratch path), run it once, then discard it; only the resulting PNG is committed.

**Interfaces:**
- Produces: `app/static/img/flow-mark.png`, a 260×260px transparent-background PNG — cobalt→cyan (135°) gradient rounded square with the FLOW two-line flow-icon in white, matching `company_select.html`'s `.wordmark-icon` SVG (`M1.5 10.2c1.6-3.2 3.6-3.2 5 0s3.4 3.2 5 0s2.5-4 2.5-4` at `stroke-width:1.5`, and `M1.5 5.8c1.6-3.2 3.6-3.2 5 0s3.4 3.2 5 0` at `stroke-width:1`, `opacity:0.55`, both white, viewBox 0 0 16 16) exactly. Consumed by Task 2 via a ReportLab `Image` flowable.

- [ ] **Step 1: Write and run the generator script**

This script was written and visually validated during plan-writing (rendered output confirmed to match the live app's mark: rounded gradient square, two white flow-line curves, correct opacity on the second line). Write it to a scratch file and run it once with `python3 <path>`:

```python
"""Generate a pre-rendered PNG of the FLOW mark (gradient rounded-square +
two-line flow icon), matching company_select.html's wordmark-icon SVG
exactly (16x16 viewBox), for embedding in the redesigned Beasiswa Laporan
Siswa PDF via a ReportLab Image flowable.

Renders at SUPERSAMPLE x the final pixel size, then LANCZOS-downsamples,
for clean anti-aliased edges/curves.
"""
import re
from PIL import Image, ImageDraw

# ── Exact source paths (company_select.html .wordmark-icon svg, viewBox 0 0 16 16) ──
PATH_1 = "M1.5 10.2c1.6-3.2 3.6-3.2 5 0s3.4 3.2 5 0s2.5-4 2.5-4"
PATH_2 = "M1.5 5.8c1.6-3.2 3.6-3.2 5 0s3.4 3.2 5 0"
VIEWBOX = 16.0

STROKE_1_WIDTH = 1.5   # SVG units, from stroke-width="1.5"
STROKE_2_WIDTH = 1.0   # from stroke-width="1"
STROKE_2_OPACITY = 0.55

FINAL_SIZE = 260        # px, final PNG size (10x a 26pt PDF placement)
SUPERSAMPLE = 4
CANVAS = FINAL_SIZE * SUPERSAMPLE
SCALE = CANVAS / VIEWBOX

CORNER_RADIUS_RATIO = 10 / 34  # from .wordmark-icon { width:34px; border-radius:10px }
CORNER_RADIUS = int(CANVAS * CORNER_RADIUS_RATIO)

COBALT = (91, 140, 255)   # #5B8CFF
CYAN   = (34, 211, 238)   # #22D3EE


def parse_path(path, scale):
    """Tiny parser for the subset of SVG path commands these two flow-line
    paths actually use: M (absolute moveto), c (relative cubic bezier,
    repeatable), s (relative smooth cubic bezier, repeatable). Returns a
    list of (x, y) points in canvas space, densely sampled along every
    cubic segment for a smooth polyline."""
    tokens = re.findall(r'[Mcs]|-?\d*\.?\d+', path)
    i = 0
    cmd = None
    cur = (0.0, 0.0)
    prev_cp2 = None
    points = []

    def cubic_points(p0, p1, p2, p3, n=24):
        pts = []
        for step in range(n + 1):
            t = step / n
            mt = 1 - t
            x = (mt**3) * p0[0] + 3 * (mt**2) * t * p1[0] + 3 * mt * (t**2) * p2[0] + (t**3) * p3[0]
            y = (mt**3) * p0[1] + 3 * (mt**2) * t * p1[1] + 3 * mt * (t**2) * p2[1] + (t**3) * p3[1]
            pts.append((x, y))
        return pts

    while i < len(tokens):
        tok = tokens[i]
        if tok in ('M', 'c', 's'):
            cmd = tok
            i += 1
            continue
        if cmd == 'M':
            x, y = float(tokens[i]), float(tokens[i + 1])
            cur = (x, y)
            points.append(cur)
            i += 2
            prev_cp2 = None
        elif cmd == 'c':
            dx1, dy1, dx2, dy2, dx, dy = (float(tokens[i + k]) for k in range(6))
            cp1 = (cur[0] + dx1, cur[1] + dy1)
            cp2 = (cur[0] + dx2, cur[1] + dy2)
            end = (cur[0] + dx, cur[1] + dy)
            points.extend(cubic_points(cur, cp1, cp2, end)[1:])
            prev_cp2 = cp2
            cur = end
            i += 6
        elif cmd == 's':
            dx2, dy2, dx, dy = (float(tokens[i + k]) for k in range(4))
            cp2 = (cur[0] + dx2, cur[1] + dy2)
            end = (cur[0] + dx, cur[1] + dy)
            cp1 = (2 * cur[0] - prev_cp2[0], 2 * cur[1] - prev_cp2[1]) if prev_cp2 else cur
            points.extend(cubic_points(cur, cp1, cp2, end)[1:])
            prev_cp2 = cp2
            cur = end
            i += 4
        else:
            i += 1

    return [(px * scale, py * scale) for px, py in points]


def rounded_mask(size, radius):
    mask = Image.new('L', (size, size), 0)
    d = ImageDraw.Draw(mask)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=255)
    return mask


def gradient_135(size, c1, c2):
    """Linear gradient top-left -> bottom-right (CSS 135deg)."""
    grad = Image.new('RGB', (size, size))
    px = grad.load()
    for y in range(size):
        for x in range(size):
            t = (x + y) / (2 * (size - 1))
            r = int(c1[0] + (c2[0] - c1[0]) * t)
            g = int(c1[1] + (c2[1] - c1[1]) * t)
            b = int(c1[2] + (c2[2] - c1[2]) * t)
            px[x, y] = (r, g, b)
    return grad


def main():
    bg = gradient_135(CANVAS, COBALT, CYAN).convert('RGBA')
    mask = rounded_mask(CANVAS, CORNER_RADIUS)
    canvas = Image.new('RGBA', (CANVAS, CANVAS), (0, 0, 0, 0))
    canvas.paste(bg, (0, 0), mask)

    line_layer = Image.new('RGBA', (CANVAS, CANVAS), (0, 0, 0, 0))
    draw = ImageDraw.Draw(line_layer)

    pts1 = parse_path(PATH_1, SCALE)
    draw.line(pts1, fill=(255, 255, 255, 255), width=int(STROKE_1_WIDTH * SCALE), joint='curve')
    for p in (pts1[0], pts1[-1]):
        r = int(STROKE_1_WIDTH * SCALE / 2)
        draw.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=(255, 255, 255, 255))

    pts2 = parse_path(PATH_2, SCALE)
    alpha2 = int(255 * STROKE_2_OPACITY)
    draw.line(pts2, fill=(255, 255, 255, alpha2), width=int(STROKE_2_WIDTH * SCALE), joint='curve')
    for p in (pts2[0], pts2[-1]):
        r = int(STROKE_2_WIDTH * SCALE / 2)
        draw.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=(255, 255, 255, alpha2))

    combined = Image.alpha_composite(canvas, line_layer)
    final = combined.resize((FINAL_SIZE, FINAL_SIZE), Image.LANCZOS)

    import os
    out_path = os.path.join(os.path.dirname(__file__), "flow-mark.png")
    final.save(out_path)
    print("Saved", out_path, final.size)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Move the output into place and verify visually**

Move the generated `flow-mark.png` to `app/static/img/flow-mark.png` (create the `img/` directory if it doesn't exist). Open the PNG and confirm by eye: a rounded square with a cobalt(top-left)-to-cyan(bottom-right) gradient, containing two horizontal white wavy lines (one bold/solid, one thinner and semi-transparent above it) — matching the FLOW mark seen elsewhere in the app (e.g. `app/templates/company_select.html`'s wordmark icon, or the running app's login page).

- [ ] **Step 3: Commit**

```bash
git add app/static/img/flow-mark.png
git commit -m "feat: add pre-rendered FLOW mark PNG for PDF letterhead"
```

---

### Task 2: Restyle `laporan_export()`'s PDF branch

**Files:**
- Modify: `app/modules/beasiswa/routes.py` — the `if fmt == "pdf":` block inside `laporan_export()` (currently lines 611-796).

**Interfaces:**
- Consumes: `app/static/img/flow-mark.png` from Task 1.
- Consumes (unchanged): `data` (the dict returned by `get_laporan_siswa(_cid(), code)`, already computed above this block — `data["siswa"]`/`s`, `data["cat_summary"]`, `data["budget_rows"]`, `data["payment_rows"]`, `data["total_budget"]`, `data["total_payment"]`, `data["total_sisa"]`), `format_rupiah` (already imported at the top of this file per the concurrent session's in-flight WIP — reuse it, do not re-import).

**Note:** re-check `git status --porcelain -- app/modules/beasiswa/routes.py` immediately before editing — see Global Constraints.

- [ ] **Step 1: Replace the entire PDF branch**

Replace (current lines 611-796, the full `if fmt == "pdf":` block through its `return send_file(...)`):

```python
    if fmt == "pdf":
        import io
        from flask import send_file
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet

        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4,
                                leftMargin=1.5*cm, rightMargin=1.5*cm,
                                topMargin=1.5*cm, bottomMargin=1.5*cm)
        styles = getSampleStyleSheet()

        # Text wrapping style for tables
        cell_style = styles["Normal"].clone('cell_style')
        cell_style.fontSize = 8
        cell_style.leading = 10
        cell_style.wordWrap = 'CJK'

        label_style = cell_style.clone('label_style')
        label_style.fontName = 'Helvetica-Bold'

        def wrap_row(row, is_header=False, is_footer=False):
            wrapped = []
            for item in row:
                if is_header or is_footer:
                    wrapped.append(item)
                else:
                    wrapped.append(Paragraph(str(item), cell_style) if item else "")
            return wrapped

        elems = [Paragraph(f"Laporan Siswa — {s.get('nama','')} ({s.get('code','')})", styles["Title"]),
                 Paragraph(session.get("company_name", ""), styles["Normal"]),
                 Spacer(1, 0.4*cm)]

        # Student info table (2-column label/value pairs)
        elems.append(Paragraph("Data Siswa", styles["Heading2"]))

        def _lv_row(label1, value1, label2, value2):
            return [
                Paragraph(str(label1), label_style),
                Paragraph(str(value1), cell_style) if value1 else "",
                Paragraph(str(label2), label_style) if label2 else "",
                Paragraph(str(value2), cell_style) if value2 else "",
            ]

        info_rows = [
            _lv_row("Kode Siswa", s.get("code",""),          "Status", s.get("status","")),
            _lv_row("Nama",       s.get("nama",""),           "Program", s.get("program","")),
            _lv_row("Jenjang",    s.get("jenjang",""),        "Angkatan", str(s.get("angkatan",""))),
            _lv_row("Universitas",s.get("universitas",""),    "Fakultas", s.get("fakultas","")),
            _lv_row("Bank",       s.get("bank",""),           "No. Rekening", s.get("norek","")),
            _lv_row("Nama Rek.",  s.get("namarek",""),        "Referensi", s.get("referensi","")),
        ]
        if s.get("catatan"):
            info_rows.append(_lv_row("Catatan", s.get("catatan",""), "", ""))
        info_tbl = Table(info_rows, colWidths=[2.5*cm, 5.5*cm, 2.5*cm, 6.5*cm])
        info_tbl.setStyle(TableStyle([
            ("FONTSIZE",   (0,0), (-1,-1), 8),
            ("BACKGROUND", (0,0), (0,-1), colors.HexColor("#f3f4f6")),
            ("BACKGROUND", (2,0), (2,-1), colors.HexColor("#f3f4f6")),
            ("GRID",       (0,0), (-1,-1), 0.5, colors.HexColor("#e5e7eb")),
            ("VALIGN",     (0,0), (-1,-1), "MIDDLE"),
            ("TOPPADDING", (0,0), (-1,-1), 4),
            ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ]))
        elems += [info_tbl, Spacer(1, 0.3*cm)]

        # IPK section
        ipk_sems = [(i, s.get(f"ipk_sem{i}")) for i in range(1,11) if s.get(f"ipk_sem{i}")]
        ipk_pens = [(i, s.get(f"ipk_pen{i}")) for i in range(1,4) if s.get(f"ipk_pen{i}")]
        if ipk_sems or ipk_pens:
            elems.append(Paragraph("IPK", styles["Heading2"]))
            ipk_rows = []
            if ipk_sems:
                ipk_rows.append(["IPK Semester"] + [f"Sem {i}: {float(v):.2f}" for i, v in ipk_sems])
            if ipk_pens:
                ipk_rows.append(["IPK Penelitian"] + [f"Tahap {i}: {float(v):.2f}" for i, v in ipk_pens])
            max_cols = max(len(r) for r in ipk_rows)
            for r in ipk_rows:
                while len(r) < max_cols:
                    r.append("")
            ipk_rows = [
                [Paragraph(str(row[0]), label_style)] +
                [Paragraph(str(v), cell_style) if v else "" for v in row[1:]]
                for row in ipk_rows
            ]
            ipk_tbl = Table(ipk_rows)
            ipk_tbl.setStyle(TableStyle([
                ("FONTSIZE",   (0,0), (-1,-1), 8),
                ("BACKGROUND", (0,0), (0,-1), colors.HexColor("#f3f4f6")),
                ("GRID",       (0,0), (-1,-1), 0.5, colors.HexColor("#e5e7eb")),
                ("TOPPADDING", (0,0), (-1,-1), 3),
                ("BOTTOMPADDING", (0,0), (-1,-1), 3),
            ]))
            elems += [ipk_tbl, Spacer(1, 0.3*cm)]

        # Summary table
        elems.append(Paragraph("Rekapitulasi per Kategori", styles["Heading2"]))
        sum_data = [["Kategori", "Budget (Rp)", "Payment (Rp)", "Selisih (Rp)"]]
        for c in data["cat_summary"]:
            kategori_cell = Paragraph(str(c["cat1"]), cell_style) if c["cat1"] else ""
            sum_data.append([kategori_cell, format_rupiah(c['budget'], prefix=""), format_rupiah(c['payment'], prefix=""), format_rupiah(c['sisa'], prefix="")])
        sum_data.append(["TOTAL", f"{data['total_budget']:,.0f}",
                         f"{data['total_payment']:,.0f}", f"{data['total_sisa']:,.0f}"])
        st = Table(sum_data, colWidths=[5*cm, 4*cm, 4*cm, 4*cm])
        neg_rows = [i+1 for i, c in enumerate(data["cat_summary"]) if c["sisa"] < 0]
        ts = TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#1a56db")),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTNAME", (0,-1), (-1,-1), "Helvetica-Bold"),
            ("BACKGROUND", (0,-1), (-1,-1), colors.HexColor("#f3f4f6")),
            ("ALIGN", (1,0), (-1,-1), "RIGHT"),
            ("FONTSIZE", (0,0), (-1,-1), 8),
            ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#e5e7eb")),
        ])
        tb = data["total_sisa"]
        if tb < 0:
            ts.add("TEXTCOLOR", (3,-1), (3,-1), colors.HexColor("#dc2626"))
        for ri in neg_rows:
            ts.add("TEXTCOLOR", (3,ri), (3,ri), colors.HexColor("#dc2626"))
        st.setStyle(ts)
        elems += [st, Spacer(1, 0.4*cm)]

        # Budget detail
        elems.append(Paragraph("Detail Budget", styles["Heading2"]))
        bgt_headers = ["Kategori 1", "Kategori 2", "Tanggal", "Pillar", "Amount (Rp)"]
        bgt_data = [wrap_row(bgt_headers, is_header=True)]
        bgt_total = 0
        for r in data["budget_rows"]:
            a = r.get("amount", 0); bgt_total += a
            bgt_data.append(wrap_row([r.get("cat1",""), r.get("cat2",""), r.get("tanggal",""),
                             r.get("pillar",""), format_rupiah(a, prefix="")]))
        if data["budget_rows"]:
            bgt_data.append(wrap_row(["", "TOTAL", "", "", format_rupiah(bgt_total, prefix="")], is_footer=True))
        bt = Table(bgt_data, colWidths=[3.5*cm, 4*cm, 2.5*cm, 3*cm, 4*cm], repeatRows=1)
        bt.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#1a56db")),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTNAME", (0,-1), (-1,-1), "Helvetica-Bold"),
            ("BACKGROUND", (0,-1), (-1,-1), colors.HexColor("#f3f4f6")),
            ("ALIGN", (4,0), (-1,-1), "RIGHT"),
            ("FONTSIZE", (0,0), (-1,-1), 8),
            ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#e5e7eb")),
            ("ROWBACKGROUNDS", (0,1), (-1,-2), [colors.white, colors.HexColor("#f8fafc")]),
            ("VALIGN", (0,0), (-1,-1), "TOP"),
        ]))
        elems += [bt, Spacer(1, 0.4*cm)]

        # Payment detail
        elems.append(Paragraph("Detail Payment", styles["Heading2"]))
        pay_headers = ["Kategori 1", "Kategori 2", "Tanggal", "PAM", "Pillar", "Amount (Rp)", "Status"]
        pay_data = [wrap_row(pay_headers, is_header=True)]
        pay_total = 0
        for r in data["payment_rows"]:
            a = r.get("amount", 0); pay_total += a
            pay_data.append(wrap_row([r.get("cat1",""), r.get("cat2",""), r.get("tanggal",""),
                             r.get("pam",""), r.get("pillar",""),
                             format_rupiah(a, prefix=""), r.get("status","")]))
        if data["payment_rows"]:
            pay_data.append(wrap_row(["", "TOTAL", "", "", "", format_rupiah(pay_total, prefix=""), ""], is_footer=True))
        
        # Adjust column widths to distribute the removed 2.5cm
        pt = Table(pay_data, colWidths=[2.8*cm, 3.2*cm, 2.0*cm, 3.5*cm, 2.0*cm, 2.5*cm, 1.8*cm], repeatRows=1)
        pt.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#065f46")),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTNAME", (0,-1), (-1,-1), "Helvetica-Bold"),
            ("BACKGROUND", (0,-1), (-1,-1), colors.HexColor("#f3f4f6")),
            ("ALIGN", (5,0), (-1,-1), "RIGHT"),
            ("FONTSIZE", (0,0), (-1,-1), 8),
            ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#e5e7eb")),
            ("ROWBACKGROUNDS", (0,1), (-1,-2), [colors.white, colors.HexColor("#f8fafc")]),
            ("VALIGN", (0,0), (-1,-1), "TOP"),
        ]))
        elems.append(pt)

        doc.build(elems)
        buf.seek(0)
        return send_file(buf, mimetype="application/pdf",
                         download_name=f"laporan_{code}.pdf", as_attachment=True)
```

with:

```python
    if fmt == "pdf":
        import io, os
        from datetime import date as _date
        from flask import send_file
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.enums import TA_RIGHT

        # ── FLOW brand palette (exact hex values used elsewhere in the app) ──
        COBALT      = colors.HexColor("#5B8CFF")
        INK_DARK    = colors.HexColor("#0F1220")
        INK         = colors.HexColor("#1e293b")
        MUTED       = colors.HexColor("#64748b")
        HAIRLINE    = colors.HexColor("#f1f5f9")
        COBALT_TINT = colors.HexColor("#eff6ff")
        GREEN       = colors.HexColor("#047857")
        GREEN_TINT  = colors.HexColor("#ecfdf5")
        GREEN_LINE  = colors.HexColor("#10b981")
        NEGATIVE    = colors.HexColor("#dc2626")
        FLOW_MARK_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "static", "img", "flow-mark.png")

        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4,
                                leftMargin=1.5*cm, rightMargin=1.5*cm,
                                topMargin=1.5*cm, bottomMargin=1.5*cm)
        styles = getSampleStyleSheet()

        # Text wrapping style for tables
        cell_style = styles["Normal"].clone('cell_style')
        cell_style.fontSize = 8
        cell_style.leading = 10
        cell_style.wordWrap = 'CJK'

        label_style = cell_style.clone('label_style')
        label_style.fontName = 'Helvetica-Bold'
        label_style.fontSize = 7
        label_style.textColor = MUTED

        def wrap_row(row, is_header=False, is_footer=False):
            wrapped = []
            for item in row:
                if is_header or is_footer:
                    wrapped.append(item)
                else:
                    wrapped.append(Paragraph(str(item), cell_style) if item else "")
            return wrapped

        def _lv_row(label1, value1, label2, value2):
            return [
                Paragraph(str(label1).upper(), label_style),
                Paragraph(str(value1), cell_style) if value1 else "",
                Paragraph(str(label2).upper(), label_style) if label2 else "",
                Paragraph(str(value2), cell_style) if value2 else "",
            ]

        section_title_style = styles["Normal"].clone('section_title')
        section_title_style.fontName = 'Helvetica-Bold'
        section_title_style.fontSize = 9
        section_title_style.textColor = INK

        def section_header(text, accent=COBALT):
            """Small bold uppercase heading with a left accent rule."""
            tbl = Table([[Paragraph(text.upper(), section_title_style)]])
            tbl.setStyle(TableStyle([
                ("LINEBEFORE", (0,0), (0,0), 2.5, accent),
                ("LEFTPADDING", (0,0), (0,0), 8),
                ("TOPPADDING", (0,0), (-1,-1), 0),
                ("BOTTOMPADDING", (0,0), (-1,-1), 4),
            ]))
            return tbl

        # ── Letterhead ──────────────────────────────────────────────────
        brand_style = styles["Normal"].clone('brand_style')
        brand_style.fontName = 'Helvetica-Bold'
        brand_style.fontSize = 13
        brand_style.textColor = INK_DARK

        company_style = styles["Normal"].clone('company_style')
        company_style.fontSize = 8
        company_style.textColor = MUTED
        company_style.alignment = TA_RIGHT
        company_style.leading = 11

        try:
            mark = Image(FLOW_MARK_PATH, width=18, height=18)
        except Exception:
            mark = ""

        header_tbl = Table(
            [[mark, Paragraph("FLOW", brand_style),
              Paragraph(f"{session.get('company_name','')}<br/>Dicetak {_date.today().strftime('%d %B %Y')}", company_style)]],
            colWidths=[1.2*cm, 3*cm, None],
        )
        header_tbl.setStyle(TableStyle([
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("LINEBELOW", (0,0), (-1,-1), 1.4, INK_DARK),
            ("TOPPADDING", (0,0), (-1,-1), 0),
            ("BOTTOMPADDING", (0,0), (-1,-1), 8),
            ("LEFTPADDING", (0,0), (0,0), 0),
        ]))

        title_style = styles["Normal"].clone('report_title')
        title_style.fontName = 'Helvetica-Bold'
        title_style.fontSize = 16
        title_style.textColor = INK_DARK
        title_style.spaceBefore = 12
        title_style.spaceAfter = 2

        subtitle_style = styles["Normal"].clone('report_subtitle')
        subtitle_style.fontSize = 9
        subtitle_style.textColor = MUTED
        subtitle_style.spaceAfter = 14

        elems = [
            header_tbl,
            Paragraph("Laporan Siswa", title_style),
            Paragraph(f"{s.get('nama','')} &middot; {s.get('code','')}", subtitle_style),
        ]

        # Student info table (2-column label/value pairs)
        elems.append(section_header("Data Siswa"))
        info_rows = [
            _lv_row("Kode Siswa", s.get("code",""),          "Status", s.get("status","")),
            _lv_row("Nama",       s.get("nama",""),           "Program", s.get("program","")),
            _lv_row("Jenjang",    s.get("jenjang",""),        "Angkatan", str(s.get("angkatan",""))),
            _lv_row("Universitas",s.get("universitas",""),    "Fakultas", s.get("fakultas","")),
            _lv_row("Bank",       s.get("bank",""),           "No. Rekening", s.get("norek","")),
            _lv_row("Nama Rek.",  s.get("namarek",""),        "Referensi", s.get("referensi","")),
        ]
        if s.get("catatan"):
            info_rows.append(_lv_row("Catatan", s.get("catatan",""), "", ""))
        info_tbl = Table(info_rows, colWidths=[2.5*cm, 5.5*cm, 2.5*cm, 6.5*cm])
        info_tbl.setStyle(TableStyle([
            ("FONTSIZE",   (0,0), (-1,-1), 8),
            ("LINEBELOW",  (0,0), (-1,-1), 0.5, HAIRLINE),
            ("VALIGN",     (0,0), (-1,-1), "MIDDLE"),
            ("TOPPADDING", (0,0), (-1,-1), 4),
            ("BOTTOMPADDING", (0,0), (-1,-1), 4),
            ("LEFTPADDING", (0,0), (0,-1), 0),
        ]))
        elems += [info_tbl, Spacer(1, 0.5*cm)]

        # IPK section
        ipk_sems = [(i, s.get(f"ipk_sem{i}")) for i in range(1,11) if s.get(f"ipk_sem{i}")]
        ipk_pens = [(i, s.get(f"ipk_pen{i}")) for i in range(1,4) if s.get(f"ipk_pen{i}")]
        if ipk_sems or ipk_pens:
            elems.append(section_header("IPK"))
            ipk_rows = []
            if ipk_sems:
                ipk_rows.append(["IPK Semester"] + [f"Sem {i}: {float(v):.2f}" for i, v in ipk_sems])
            if ipk_pens:
                ipk_rows.append(["IPK Penelitian"] + [f"Tahap {i}: {float(v):.2f}" for i, v in ipk_pens])
            max_cols = max(len(r) for r in ipk_rows)
            for r in ipk_rows:
                while len(r) < max_cols:
                    r.append("")
            ipk_rows = [
                [Paragraph(str(row[0]).upper(), label_style)] +
                [Paragraph(str(v), cell_style) if v else "" for v in row[1:]]
                for row in ipk_rows
            ]
            ipk_tbl = Table(ipk_rows)
            ipk_tbl.setStyle(TableStyle([
                ("FONTSIZE",   (0,0), (-1,-1), 8),
                ("LINEBELOW",  (0,0), (-1,-1), 0.5, HAIRLINE),
                ("TOPPADDING", (0,0), (-1,-1), 3),
                ("BOTTOMPADDING", (0,0), (-1,-1), 3),
                ("LEFTPADDING", (0,0), (0,-1), 0),
            ]))
            elems += [ipk_tbl, Spacer(1, 0.5*cm)]

        # Summary table
        elems.append(section_header("Rekapitulasi per Kategori"))
        sum_data = [["Kategori", "Budget (Rp)", "Payment (Rp)", "Selisih (Rp)"]]
        for c in data["cat_summary"]:
            kategori_cell = Paragraph(str(c["cat1"]), cell_style) if c["cat1"] else ""
            sum_data.append([kategori_cell, format_rupiah(c['budget'], prefix=""), format_rupiah(c['payment'], prefix=""), format_rupiah(c['sisa'], prefix="")])
        sum_data.append(["TOTAL", f"{data['total_budget']:,.0f}",
                         f"{data['total_payment']:,.0f}", f"{data['total_sisa']:,.0f}"])
        st = Table(sum_data, colWidths=[5*cm, 4*cm, 4*cm, 4*cm])
        neg_rows = [i+1 for i, c in enumerate(data["cat_summary"]) if c["sisa"] < 0]
        ts = TableStyle([
            ("BACKGROUND", (0,0), (-1,0), INK_DARK),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE", (0,0), (-1,0), 7.5),
            ("FONTNAME", (0,-1), (-1,-1), "Helvetica-Bold"),
            ("BACKGROUND", (0,-1), (-1,-1), COBALT_TINT),
            ("TEXTCOLOR", (0,-1), (-1,-1), COBALT),
            ("ALIGN", (1,0), (-1,-1), "RIGHT"),
            ("FONTSIZE", (0,1), (-1,-1), 8),
            ("LINEBELOW", (0,1), (-1,-2), 0.5, HAIRLINE),
            ("ROWBACKGROUNDS", (0,1), (-1,-2), [colors.white, HAIRLINE]),
            ("TOPPADDING", (0,0), (-1,-1), 5),
            ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ])
        tb = data["total_sisa"]
        if tb < 0:
            ts.add("TEXTCOLOR", (3,-1), (3,-1), NEGATIVE)
        for ri in neg_rows:
            ts.add("TEXTCOLOR", (3,ri), (3,ri), NEGATIVE)
        st.setStyle(ts)
        elems += [st, Spacer(1, 0.5*cm)]

        # Budget detail
        elems.append(section_header("Detail Budget"))
        bgt_headers = ["Kategori 1", "Kategori 2", "Tanggal", "Pillar", "Amount (Rp)"]
        bgt_data = [wrap_row(bgt_headers, is_header=True)]
        bgt_total = 0
        for r in data["budget_rows"]:
            a = r.get("amount", 0); bgt_total += a
            bgt_data.append(wrap_row([r.get("cat1",""), r.get("cat2",""), r.get("tanggal",""),
                             r.get("pillar",""), format_rupiah(a, prefix="")]))
        if data["budget_rows"]:
            bgt_data.append(wrap_row(["", "TOTAL", "", "", format_rupiah(bgt_total, prefix="")], is_footer=True))
        bt = Table(bgt_data, colWidths=[3.5*cm, 4*cm, 2.5*cm, 3*cm, 4*cm], repeatRows=1)
        bt.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), COBALT_TINT),
            ("TEXTCOLOR", (0,0), (-1,0), COBALT),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE", (0,0), (-1,0), 7.5),
            ("LINEBELOW", (0,0), (-1,0), 1.2, COBALT),
            ("FONTNAME", (0,-1), (-1,-1), "Helvetica-Bold"),
            ("BACKGROUND", (0,-1), (-1,-1), HAIRLINE),
            ("ALIGN", (4,0), (-1,-1), "RIGHT"),
            ("FONTSIZE", (0,1), (-1,-1), 8),
            ("LINEBELOW", (0,1), (-1,-2), 0.5, HAIRLINE),
            ("ROWBACKGROUNDS", (0,1), (-1,-2), [colors.white, HAIRLINE]),
            ("VALIGN", (0,0), (-1,-1), "TOP"),
            ("TOPPADDING", (0,0), (-1,-1), 4),
            ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ]))
        elems += [bt, Spacer(1, 0.5*cm)]

        # Payment detail
        elems.append(section_header("Detail Payment", accent=GREEN))
        pay_headers = ["Kategori 1", "Kategori 2", "Tanggal", "PAM", "Pillar", "Amount (Rp)", "Status"]
        pay_data = [wrap_row(pay_headers, is_header=True)]
        pay_total = 0
        for r in data["payment_rows"]:
            a = r.get("amount", 0); pay_total += a
            pay_data.append(wrap_row([r.get("cat1",""), r.get("cat2",""), r.get("tanggal",""),
                             r.get("pam",""), r.get("pillar",""),
                             format_rupiah(a, prefix=""), r.get("status","")]))
        if data["payment_rows"]:
            pay_data.append(wrap_row(["", "TOTAL", "", "", "", format_rupiah(pay_total, prefix=""), ""], is_footer=True))

        pt = Table(pay_data, colWidths=[2.8*cm, 3.2*cm, 2.0*cm, 3.5*cm, 2.0*cm, 2.5*cm, 1.8*cm], repeatRows=1)
        pt.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), GREEN_TINT),
            ("TEXTCOLOR", (0,0), (-1,0), GREEN),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE", (0,0), (-1,0), 7.5),
            ("LINEBELOW", (0,0), (-1,0), 1.2, GREEN_LINE),
            ("FONTNAME", (0,-1), (-1,-1), "Helvetica-Bold"),
            ("BACKGROUND", (0,-1), (-1,-1), HAIRLINE),
            ("ALIGN", (5,0), (-1,-1), "RIGHT"),
            ("FONTSIZE", (0,1), (-1,-1), 8),
            ("LINEBELOW", (0,1), (-1,-2), 0.5, HAIRLINE),
            ("ROWBACKGROUNDS", (0,1), (-1,-2), [colors.white, HAIRLINE]),
            ("VALIGN", (0,0), (-1,-1), "TOP"),
            ("TOPPADDING", (0,0), (-1,-1), 4),
            ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ]))
        elems.append(pt)

        def _draw_footer(canvas_obj, doc_obj):
            canvas_obj.saveState()
            canvas_obj.setFont("Helvetica", 7)
            canvas_obj.setFillColor(MUTED)
            canvas_obj.drawRightString(A4[0] - 1.5*cm, 1*cm, f"Halaman {doc_obj.page}")
            canvas_obj.restoreState()

        doc.build(elems, onFirstPage=_draw_footer, onLaterPages=_draw_footer)
        buf.seek(0)
        return send_file(buf, mimetype="application/pdf",
                         download_name=f"laporan_{code}.pdf", as_attachment=True)
```

- [ ] **Step 2: Manual verify**

Run the Flask dev server (`config.DB_PATH` pointed at a scratch copy of the database, per this project's established disposable-verification pattern — never test against the real `finance_hub.db`), log in, select Eka Tjipta Foundation, and download the PDF for:
1. A student with IPK data and both budget and payment rows — confirm the letterhead (mark + FLOW + company name + date), title, all sections, the dark-header summary table with the cobalt total row, and the cobalt-tinted Budget table / green-tinted Payment table headers all render correctly, and the page-number footer appears at the bottom.
2. A student with no IPK data — confirm the IPK section is skipped entirely (no empty heading).
3. A student with at least one category where `selisih < 0` — confirm that cell still renders in red (`#dc2626`, unchanged from today).
4. A student whose budget/payment rows span more than one page — confirm the footer's page number increments correctly and table headers repeat on the new page (`repeatRows=1` preserved).
5. Confirm the CSV export for the same student (`.../export/csv`) is unaffected — byte-identical content to before this change.

- [ ] **Step 3: Commit**

```bash
git add app/modules/beasiswa/routes.py
git commit -m "feat: restyle Laporan Siswa PDF with FLOW letterhead branding"
```

---

### Task 3: Final review

**Files:** None (verification only).

- [ ] **Step 1: Re-read the diff against the spec**

Review the cumulative diff from Tasks 1-2 against
`docs/superpowers/specs/2026-08-03-flow-beasiswa-laporan-siswa-pdf-redesign-design.md`
— confirm every design decision (letterhead layout, section-header
treatment, dark summary header + cobalt total row, tinted Budget/Payment
headers, page-number-only footer, Helvetica fallback, PNG mark asset) is
reflected in the actual code, that the CSV branch and every other PDF
export in the app are untouched, and that no unrelated concurrent-session
WIP (the `format_rupiah` changes in other export functions) got swept
into either commit.
