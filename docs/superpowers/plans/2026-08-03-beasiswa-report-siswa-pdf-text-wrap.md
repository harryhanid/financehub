# Beasiswa Report Siswa PDF Text Wrap Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the "Laporan Siswa" PDF export so long text in the Data Siswa, IPK, and Rekapitulasi per Kategori tables wraps within its cell instead of overflowing into the neighboring cell.

**Architecture:** Convert the plain-string cells in the three affected tables to `Paragraph` flowables (which auto-wrap to column width), reusing the existing `cell_style` already used by the two tables in the same PDF that already wrap correctly (Detail Budget/Detail Payment). A new `label_style` (bold) replaces the `TableStyle FONTNAME` rules that don't work once a cell holds a `Paragraph`.

**Tech Stack:** Flask (Python), `reportlab` (already a dependency), pytest.

## Global Constraints

- Only `app/modules/beasiswa/routes.py` (the `laporan_export` function's `fmt == "pdf"` branch, currently lines 611-779) and `app/tests/test_beasiswa_routes.py` change. No other file.
- The 3 Rupiah columns (Budget/Payment/Selisih) in Rekapitulasi per Kategori, and the header/footer rows of all three tables, stay as plain strings — do not wrap them (wrapping the Rupiah columns would silently break their existing right-alignment, since `TableStyle ALIGN` doesn't affect `Paragraph` cell content the way it does plain strings).
- `wrap_row()` and its existing two call sites (Detail Budget, Detail Payment) are not modified.
- No new PDF-content-inspection tooling — verification of actual wrapped layout is manual (open the generated PDF), matching this codebase's existing precedent of no frontend/PDF test framework.

---

### Task 1: Add regression coverage with a real seeded student

**Files:**
- Modify: `app/tests/test_beasiswa_routes.py`

**Interfaces:**
- Produces: `_seed_siswa_with_long_fields(company_id: int = 2, code: str = "1250099") -> None` — used by Tasks 2-4 to confirm each code change doesn't break PDF generation.

The existing test at `test_beasiswa_routes.py:155-162` (`test_laporan_export_pdf_does_not_crash`) only exercises a nonexistent-student 404 path — it never reaches the `Table`-building code this fix touches. This task adds a second test that seeds a real student with deliberately long field values (the exact kind of data that currently overflows), so Tasks 2-4 have something real to run against.

Note on TDD shape: this task doesn't have a "red" phase — the current code doesn't *crash* on long text, it just renders it badly (a purely visual defect this test framework can't assert on). This test's job is to be the regression guard for Tasks 2-4's code changes, and to give you a real PDF you can open and look at. It's expected to pass both before and after this task — that's correct, not a mistake.

- [ ] **Step 1: Write the test**

Add to `app/tests/test_beasiswa_routes.py` (anywhere after the existing `login`/`_select_etf` helpers near the top of the file):

```python
def _seed_siswa_with_long_fields(company_id: int = 2, code: str = "1250099") -> None:
    """Seed one siswa with deliberately long text fields plus one budget row
    with a long category name, so the Laporan Siswa PDF's Data Siswa, IPK, and
    Rekapitulasi per Kategori tables all have long text to wrap."""
    from database import get_conn
    conn = get_conn()
    conn.execute(
        """INSERT INTO siswa
           (company_id, code, nama, jenjang, angkatan, program,
            fakultas, universitas, bank, norek, namarek, referensi,
            catatan, ipk_sem1, status)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (company_id, code, "Siswa Uji Panjang", "S1", 2025, "SMART",
         "Fakultas Teknik Informatika dan Ilmu Komputer Terapan",
         "Universitas Pembangunan Nasional Veteran Jakarta Kampus Utama",
         "Bank Sinarmas", "1234567890",
         "Siswa Uji Panjang Dengan Nama Rekening Yang Sangat Panjang Sekali",
         "Ref-001",
         "Catatan ini ditulis sangat panjang untuk memastikan tabel Data Siswa "
         "benar-benar mem-wrap teks dan tidak menembus kolom di sebelahnya "
         "seperti yang dilaporkan pengguna.",
         3.75, "Aktif")
    )
    conn.execute(
        """INSERT INTO budget_beasiswa
           (company_id, siswa_code, cat1, cat2, tanggal, amount, pillar)
           VALUES (?,?,?,?,?,?,?)""",
        (company_id, code,
         "Kategori Budget Dengan Nama Yang Sangat Panjang Sekali Untuk Uji Wrap",
         "By Pendaftaran", "2026-01-01", 5000000, "AGRI")
    )
    conn.commit()
    conn.close()


def test_laporan_export_pdf_with_long_text_fields_renders_ok(client):
    _seed_siswa_with_long_fields()
    login(client)
    _select_etf(client)
    resp = client.get("/beasiswa/laporan/siswa/1250099/export/pdf")
    assert resp.status_code == 200
    assert resp.data[:4] == b"%PDF"
```

- [ ] **Step 2: Run the test to confirm it passes**

Run: `cd C:\Financehub\app && python -m pytest tests/test_beasiswa_routes.py -v -k long_text_fields`
Expected: PASS (1 test) — this confirms the seed data and route both work; the PDF is being generated with badly-overflowing text right now, but nothing crashes.

- [ ] **Step 3: Save a copy of the "before" PDF for manual comparison later**

**Important:** this script must redirect `config.DB_PATH` to a scratch file *before* touching the database — without this, it would write test data straight into the real production `finance_hub.db`. `pytest` normally does this redirect for you via `tests/conftest.py`'s `config.DB_PATH = ...` override, but that only runs under pytest; a standalone `python -c` script does not get it for free, so this script sets it manually.

Run:
```bash
cd C:\Financehub\app
python -c "
import config
config.DB_PATH = 'manual_check.db'
from database import init_db
init_db()
from app import create_app
app = create_app(testing=True)
client = app.test_client()
client.post('/auth/login', json={'username': 'admin', 'password': 'Admin@123'})
client.post('/select-company', data={'company_id': '2'})
import tests.test_beasiswa_routes as t
t._seed_siswa_with_long_fields()
resp = client.get('/beasiswa/laporan/siswa/1250099/export/pdf')
open('laporan_before_fix.pdf', 'wb').write(resp.data)
print('saved', len(resp.data), 'bytes')
"
```
Expected: prints `saved <N> bytes`, and `C:\Financehub\app\laporan_before_fix.pdf` exists. Open it and confirm the overflow is visible in Data Siswa (Catatan/Universitas/Nama Rek.), IPK, and Rekapitulasi per Kategori (Kategori column) — this is your "before" reference for Task 4's final comparison. `C:\Financehub\app\manual_check.db` now holds only this scratch data — never the real database.

- [ ] **Step 4: Commit**

```bash
cd C:\Financehub
git add app/tests/test_beasiswa_routes.py
git commit -m "test: add long-text-field regression coverage for Laporan Siswa PDF"
```

---

### Task 2: Relocate the wrap style block, add `label_style`, fix Data Siswa table

**Files:**
- Modify: `app/modules/beasiswa/routes.py:624-653` (style setup) and `:707-720` (old style block location)

**Interfaces:**
- Consumes: `_seed_siswa_with_long_fields`, `test_laporan_export_pdf_with_long_text_fields_renders_ok` (Task 1)
- Produces: `label_style` (bold `Paragraph` style) — consumed by Task 3's IPK table fix.

`cell_style` and `wrap_row()` are currently defined at `routes.py:707-720`, *after* the Data Siswa/IPK/Rekapitulasi tables that this fix needs them in (those tables are built starting at line 630). This task moves that block up to right after `styles = getSampleStyleSheet()` (line 624), adds `label_style` next to it, and fixes the Data Siswa table. It does not touch `wrap_row()` itself or its two existing call sites (Detail Budget/Payment) — moving the block earlier doesn't change what they do.

- [ ] **Step 1: Move `cell_style`/`wrap_row` earlier and add `label_style`**

In `app/modules/beasiswa/routes.py`, replace:

```python
        styles = getSampleStyleSheet()
        elems = [Paragraph(f"Laporan Siswa — {s.get('nama','')} ({s.get('code','')})", styles["Title"]),
                 Paragraph(session.get("company_name", ""), styles["Normal"]),
                 Spacer(1, 0.4*cm)]
```

with:

```python
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
```

- [ ] **Step 2: Remove the now-duplicated old block from its original location**

In the same file, remove this block (now redundant — it's the same code you just moved above):

```python
        # Text wrapping style for tables
        cell_style = styles["Normal"].clone('cell_style')
        cell_style.fontSize = 8
        cell_style.leading = 10
        cell_style.wordWrap = 'CJK'
        
        def wrap_row(row, is_header=False, is_footer=False):
            wrapped = []
            for item in row:
                if is_header or is_footer:
                    wrapped.append(item)
                else:
                    wrapped.append(Paragraph(str(item), cell_style) if item else "")
            return wrapped

```

(It sits between the Rekapitulasi per Kategori table's `elems += [st, Spacer(1, 0.4*cm)]` line and the `# Budget detail` comment. After removing it, those two lines should be directly adjacent.)

- [ ] **Step 3: Fix the Data Siswa table**

Replace:

```python
        elems.append(Paragraph("Data Siswa", styles["Heading2"]))
        info_rows = [
            ["Kode Siswa", s.get("code",""),          "Status", s.get("status","")],
            ["Nama",       s.get("nama",""),           "Program", s.get("program","")],
            ["Jenjang",    s.get("jenjang",""),        "Angkatan", str(s.get("angkatan",""))],
            ["Universitas",s.get("universitas",""),    "Fakultas", s.get("fakultas","")],
            ["Bank",       s.get("bank",""),           "No. Rekening", s.get("norek","")],
            ["Nama Rek.",  s.get("namarek",""),        "Referensi", s.get("referensi","")],
        ]
        if s.get("catatan"):
            info_rows.append(["Catatan", s.get("catatan",""), "", ""])
        info_tbl = Table(info_rows, colWidths=[2.5*cm, 5.5*cm, 2.5*cm, 6.5*cm])
        info_tbl.setStyle(TableStyle([
            ("FONTSIZE",   (0,0), (-1,-1), 8),
            ("FONTNAME",   (0,0), (0,-1), "Helvetica-Bold"),
            ("FONTNAME",   (2,0), (2,-1), "Helvetica-Bold"),
            ("BACKGROUND", (0,0), (0,-1), colors.HexColor("#f3f4f6")),
            ("BACKGROUND", (2,0), (2,-1), colors.HexColor("#f3f4f6")),
            ("GRID",       (0,0), (-1,-1), 0.5, colors.HexColor("#e5e7eb")),
            ("VALIGN",     (0,0), (-1,-1), "MIDDLE"),
            ("TOPPADDING", (0,0), (-1,-1), 4),
            ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ]))
        elems += [info_tbl, Spacer(1, 0.3*cm)]
```

with:

```python
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
```

(The two `FONTNAME` rules for columns 0 and 2 are removed — they had no effect once those columns hold `Paragraph` cells; `label_style`'s own bold font replaces them. `BACKGROUND` for the same columns is kept, since it still works on `Paragraph` cells.)

- [ ] **Step 4: Run the regression test**

Run: `cd C:\Financehub\app && python -m pytest tests/test_beasiswa_routes.py -v -k "laporan"`
Expected: PASS (both `test_laporan_export_pdf_does_not_crash` and `test_laporan_export_pdf_with_long_text_fields_renders_ok`).

- [ ] **Step 5: Manual check**

Run the same one-off script as Task 1 Step 3, but save to a different filename (`laporan_after_task2.pdf`), open it, and confirm: Data Siswa's long Universitas/Nama Rek./Catatan values now wrap within their cells (no overflow into the next column); labels ("Kode Siswa", "Nama", etc.) still render bold with a grey background, same as before.

- [ ] **Step 6: Commit**

```bash
cd C:\Financehub
git add app/modules/beasiswa/routes.py
git commit -m "fix: wrap Data Siswa table text in Laporan Siswa PDF"
```

---

### Task 3: Fix the IPK table

**Files:**
- Modify: `app/modules/beasiswa/routes.py:655-678`

**Interfaces:**
- Consumes: `label_style`, `cell_style` (Task 2)

- [ ] **Step 1: Fix the IPK table**

Replace:

```python
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
            ipk_tbl = Table(ipk_rows)
            ipk_tbl.setStyle(TableStyle([
                ("FONTSIZE",   (0,0), (-1,-1), 8),
                ("FONTNAME",   (0,0), (0,-1), "Helvetica-Bold"),
                ("BACKGROUND", (0,0), (0,-1), colors.HexColor("#f3f4f6")),
                ("GRID",       (0,0), (-1,-1), 0.5, colors.HexColor("#e5e7eb")),
                ("TOPPADDING", (0,0), (-1,-1), 3),
                ("BOTTOMPADDING", (0,0), (-1,-1), 3),
            ]))
            elems += [ipk_tbl, Spacer(1, 0.3*cm)]
```

with:

```python
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
```

(The `FONTNAME` rule for column 0 is removed — superseded by `label_style`.)

- [ ] **Step 2: Run the regression test**

Run: `cd C:\Financehub\app && python -m pytest tests/test_beasiswa_routes.py -v -k "laporan"`
Expected: PASS (both tests, same as Task 2).

- [ ] **Step 3: Manual check**

Regenerate the PDF (same script as before, save as `laporan_after_task3.pdf`) and confirm the IPK table still shows "IPK Semester"/"IPK Penelitian" bold with a grey background, and the values ("Sem 1: 3.75", etc.) render normally.

- [ ] **Step 4: Commit**

```bash
cd C:\Financehub
git add app/modules/beasiswa/routes.py
git commit -m "fix: wrap IPK table text in Laporan Siswa PDF"
```

---

### Task 4: Fix Rekapitulasi per Kategori and final verification

**Files:**
- Modify: `app/modules/beasiswa/routes.py:680-705`

**Interfaces:**
- Consumes: `cell_style` (Task 2)

Only the Kategori column in data rows is wrapped — the header row, the "TOTAL" row, and the 3 Rupiah columns stay as plain strings (see Global Constraints: wrapping the Rupiah columns would break their existing right-alignment).

- [ ] **Step 1: Fix the Kategori column**

Replace:

```python
        # Summary table
        elems.append(Paragraph("Rekapitulasi per Kategori", styles["Heading2"]))
        sum_data = [["Kategori", "Budget (Rp)", "Payment (Rp)", "Selisih (Rp)"]]
        for c in data["cat_summary"]:
            sum_data.append([c["cat1"], format_rupiah(c['budget'], prefix=""), format_rupiah(c['payment'], prefix=""), format_rupiah(c['sisa'], prefix="")])
        sum_data.append(["TOTAL", f"{data['total_budget']:,.0f}",
                         f"{data['total_payment']:,.0f}", f"{data['total_sisa']:,.0f}"])
```

with:

```python
        # Summary table
        elems.append(Paragraph("Rekapitulasi per Kategori", styles["Heading2"]))
        sum_data = [["Kategori", "Budget (Rp)", "Payment (Rp)", "Selisih (Rp)"]]
        for c in data["cat_summary"]:
            kategori_cell = Paragraph(str(c["cat1"]), cell_style) if c["cat1"] else ""
            sum_data.append([kategori_cell, format_rupiah(c['budget'], prefix=""), format_rupiah(c['payment'], prefix=""), format_rupiah(c['sisa'], prefix="")])
        sum_data.append(["TOTAL", f"{data['total_budget']:,.0f}",
                         f"{data['total_payment']:,.0f}", f"{data['total_sisa']:,.0f}"])
```

(Everything below this — `st = Table(sum_data, ...)`, the `TableStyle`, the negative-value red-text logic — is unchanged.)

- [ ] **Step 2: Run the regression test**

Run: `cd C:\Financehub\app && python -m pytest tests/test_beasiswa_routes.py -v -k "laporan"`
Expected: PASS (both tests).

- [ ] **Step 3: Run the full test suite**

Run: `cd C:\Financehub\app && python -m pytest tests/ -q`
Expected: same pass/fail counts as before this plan (any pre-existing failures are documented in `01 - Proyek/FinanceHub/FinanceHub - Known Issues.md` in the Obsidian vault as unrelated Windows SQLite file-lock flakiness).

- [ ] **Step 4: Final manual comparison**

Regenerate the PDF once more (save as `laporan_after_fix.pdf`) and compare side-by-side against `laporan_before_fix.pdf` from Task 1:
- Data Siswa: Catatan/Universitas/Nama Rek. wrap onto multiple lines, no overflow into the next column.
- IPK: unchanged appearance from Task 3's check.
- Rekapitulasi per Kategori: the long Kategori name wraps within its column; the 3 Rupiah columns are still right-aligned; a negative Selisih (if any test data has one) still renders in red.

Delete the scratch files from `C:\Financehub\app\` once the comparison is done — they're manual-verification artifacts, not part of the codebase: the four PDFs (`laporan_before_fix.pdf`, `laporan_after_task2.pdf`, `laporan_after_task3.pdf`, `laporan_after_fix.pdf`) and the scratch database (`manual_check.db`) created by the Task 1 Step 3 script.

- [ ] **Step 5: Commit**

```bash
cd C:\Financehub
git add app/modules/beasiswa/routes.py
git commit -m "fix: wrap Kategori column in Laporan Siswa PDF Rekapitulasi table"
```

## Out of Scope

- Detail Budget/Detail Payment tables and `wrap_row()` — already correct, not touched.
- The CSV export path of the same route.
- PDF exports in any other module.
