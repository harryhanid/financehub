# Export to Excel — Payment Tabs — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tambahkan tombol "↓ Export Excel" di 7 tab pada 3 halaman (ETF Payment Application, Payment Approval Memo, Payment Application) yang mengekspor baris sesuai filter atas yang aktif.

**Architecture:** Server-side export via GET endpoint baru; tombol JS membaca nilai filter dari DOM dan membuka URL dengan query params; backend query ulang dengan params yang sama, generate `.xlsx` pakai openpyxl, kirim sebagai file download.

**Tech Stack:** Python/Flask, openpyxl, SQLite, Jinja2 + vanilla JS

---

## File Map

| File | Aksi |
|------|------|
| `app/modules/payment_memo/exports.py` | Tambah `_make_xlsx` helper + 5 fungsi export baru |
| `app/modules/payment_memo/routes.py` | Tambah 5 route GET export + import baru |
| `app/modules/payment_application/service.py` | Tambah `export_application_excel` |
| `app/modules/payment_application/routes.py` | Tambah 1 route GET `/export` + import |
| `app/modules/etf_payment_application/service.py` | Modifikasi `export_pa_excel` — terima semua filter params |
| `app/modules/etf_payment_application/routes.py` | Modifikasi `export_excel` — teruskan filter params ke service |
| `app/templates/payment_memo/index.html` | Tambah 5 tombol export + 5 fungsi JS |
| `app/templates/payment_application/index.html` | Tambah 1 tombol export |
| `app/templates/etf_payment_application/index.html` | Ubah link export → fungsi JS `exportETFExcel()` |
| `app/tests/test_export_excel.py` | File test baru — semua export service + routes |

---

## Task 1: Shared helper `_make_xlsx` + Open PAM export

**Files:**
- Modify: `app/modules/payment_memo/exports.py`
- Modify: `app/modules/payment_memo/routes.py`
- Modify: `app/templates/payment_memo/index.html`
- Create: `app/tests/test_export_excel.py`

### Langkah-langkah

- [ ] **Step 1.1: Tulis test yang gagal**

Buat file `app/tests/test_export_excel.py`:

```python
# tests/test_export_excel.py
import os, sys, io, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config
config.DB_PATH = os.path.join(os.path.dirname(__file__), "test_finance_hub.db")

from database import init_db, get_conn

COMPANY_ID = 2

@pytest.fixture(autouse=True)
def clean_db():
    if os.path.exists(config.DB_PATH):
        os.remove(config.DB_PATH)
    init_db()
    _seed()
    yield
    if os.path.exists(config.DB_PATH):
        os.remove(config.DB_PATH)


def _seed():
    conn = get_conn()
    conn.execute(
        """INSERT INTO siswa (company_id, code, nama, bank, norek, namarek, jenjang, program, status)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (COMPANY_ID, "S001", "Budi Santoso", "BCA", "111", "Budi", "S1", "SMART", "Aktif")
    )
    conn.execute(
        """INSERT INTO payment_beasiswa
           (company_id, siswa_code, cat1, cat2, tanggal, amount, pillar, perusahaan, status)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (COMPANY_ID, "S001", "Tuition", "Sem 1", "2026-05-01", 5000000, "ETF", "PT ABC", "open")
    )
    conn.commit()
    conn.close()


def test_export_open_pam_returns_xlsx():
    from modules.payment_memo.exports import export_open_pam_excel
    result = export_open_pam_excel(COMPANY_ID)
    assert isinstance(result, bytes)
    assert len(result) > 500
    # xlsx magic bytes: PK (zip)
    assert result[:2] == b'PK'


def test_export_open_pam_empty_company():
    from modules.payment_memo.exports import export_open_pam_excel
    result = export_open_pam_excel(9999)
    assert isinstance(result, bytes)
    assert result[:2] == b'PK'
```

- [ ] **Step 1.2: Jalankan test untuk konfirmasi gagal**

```bash
cd app && python -m pytest tests/test_export_excel.py -v
```

Expected: `FAILED` — `ImportError: cannot import name 'export_open_pam_excel'`

- [ ] **Step 1.3: Tambah `_make_xlsx` dan `export_open_pam_excel` ke `exports.py`**

Tambahkan di akhir file `app/modules/payment_memo/exports.py`:

```python

# ── Generic xlsx builder ────────────────────────────────────────────────────
def _make_xlsx(sheet_title: str, col_headers: list, fields: list,
               rows: list, col_widths: list) -> bytes:
    """Buat file xlsx dengan header navy, freeze row 1, auto-filter."""
    import io as _io
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = sheet_title[:31]

    hdr_fill = PatternFill("solid", fgColor="1E3A5F")
    hdr_font = Font(bold=True, color="FFFFFF", size=10)
    thin     = Side(style="thin", color="D1D5DB")
    border   = Border(left=thin, right=thin, top=thin, bottom=thin)

    for col, h in enumerate(col_headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.font      = hdr_font
        cell.fill      = hdr_fill
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border    = border
    ws.row_dimensions[1].height = 32

    for ri, r in enumerate(rows, 2):
        for ci, f in enumerate(fields, 1):
            val  = r.get(f, "") or ""
            cell = ws.cell(row=ri, column=ci, value=val)
            cell.font      = Font(size=9)
            cell.border    = border
            cell.alignment = Alignment(vertical="top")

    for ci, w in enumerate(col_widths, 1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(ci)].width = w

    ws.freeze_panes    = "A2"
    ws.auto_filter.ref = ws.dimensions

    buf = _io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ── Tab export functions ────────────────────────────────────────────────────
def export_open_pam_excel(company_id: int) -> bytes:
    from modules.payment_memo.service import get_draft_payments
    rows    = get_draft_payments(company_id)
    headers = ["Code", "Nama Siswa", "Kategori 1", "Kategori 2", "Tanggal",
               "PAM No", "Perusahaan", "Amount (Rp)", "Status"]
    fields  = ["siswa_code", "nama", "cat1", "cat2", "tanggal",
               "pam", "perusahaan", "amount", "status"]
    widths  = [14, 24, 18, 18, 12, 22, 22, 16, 12]
    return _make_xlsx("Open PAM", headers, fields, rows, widths)
```

- [ ] **Step 1.4: Tambah route Open PAM di `routes.py`**

Di `app/modules/payment_memo/routes.py`, pada baris import paling atas ubah:

```python
from modules.payment_memo.exports import (
    export_pam_pdf, export_pam_excel,
    export_pam_pdf_custom, export_pam_excel_custom,
)
```

menjadi:

```python
from modules.payment_memo.exports import (
    export_pam_pdf, export_pam_excel,
    export_pam_pdf_custom, export_pam_excel_custom,
    export_open_pam_excel,
)
```

Lalu tambah route baru setelah baris `import config, io`:

```python
@bp.route("/export/open-pam")
@jwt_html_required
def export_open_pam_route():
    company_id = session.get("company_id")
    if not company_id:
        return jsonify({"ok": False, "pesan": "Perusahaan belum dipilih."}), 400
    from datetime import datetime
    xls = export_open_pam_excel(company_id)
    fname = f"Open_PAM_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    return send_file(
        io.BytesIO(xls),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        download_name=fname,
        as_attachment=True,
    )
```

- [ ] **Step 1.5: Tambah tombol Export di tab Open PAM**

Di `app/templates/payment_memo/index.html`, cari blok:

```html
  <div class="tab-panel" id="tab-draft-pay">
    <div style="margin-bottom:1rem">
      <span style="font-size:.875rem; color:var(--text-muted)">Daftar payment yang belum diproses (status Open).</span>
    </div>
```

Ubah menjadi:

```html
  <div class="tab-panel" id="tab-draft-pay">
    <div style="margin-bottom:1rem; display:flex; align-items:center; justify-content:space-between; gap:.5rem; flex-wrap:wrap">
      <span style="font-size:.875rem; color:var(--text-muted)">Daftar payment yang belum diproses (status Open).</span>
      <a href="/payment-memo/export/open-pam" class="btn btn-success btn-sm">↓ Export Excel</a>
    </div>
```

- [ ] **Step 1.6: Jalankan test untuk konfirmasi lulus**

```bash
cd app && python -m pytest tests/test_export_excel.py::test_export_open_pam_returns_xlsx tests/test_export_excel.py::test_export_open_pam_empty_company -v
```

Expected: `PASSED`

- [ ] **Step 1.7: Commit**

```bash
git add app/modules/payment_memo/exports.py app/modules/payment_memo/routes.py app/templates/payment_memo/index.html app/tests/test_export_excel.py
git commit -m "feat: add _make_xlsx helper + Open PAM tab export to Excel"
```

---

## Task 2: AGRI tab export

**Files:**
- Modify: `app/modules/payment_memo/exports.py`
- Modify: `app/modules/payment_memo/routes.py`
- Modify: `app/templates/payment_memo/index.html`
- Modify: `app/tests/test_export_excel.py`

- [ ] **Step 2.1: Tambah test AGRI export ke `test_export_excel.py`**

Tambahkan fungsi test berikut ke `app/tests/test_export_excel.py`:

```python
def test_export_pam_tab_returns_xlsx():
    from modules.payment_memo.exports import export_pam_tab_excel
    conn = get_conn()
    conn.execute(
        """INSERT INTO pam_records
           (company_id, pam_no, pam_date, gl_account, cost_center, pt,
            requestors_name, keterangan, total_amount, due_date, status, source, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (COMPANY_ID, "PAM-001-ETF-05-2026", "2026-05-01", "70110230",
         "1008C1", "PT ABC", "User A", "Catatan", 2000000, "2026-06-01",
         "open", "etf_agri", "2026-05-01T10:00:00")
    )
    conn.commit(); conn.close()
    result = export_pam_tab_excel(COMPANY_ID, search="", bulan="05", tahun="2026", source="agri")
    assert isinstance(result, bytes) and result[:2] == b'PK'
```

- [ ] **Step 2.2: Jalankan test untuk konfirmasi gagal**

```bash
cd app && python -m pytest tests/test_export_excel.py::test_export_pam_tab_returns_xlsx -v
```

Expected: `FAILED` — `ImportError: cannot import name 'export_pam_tab_excel'`

- [ ] **Step 2.3: Tambah `export_pam_tab_excel` ke `exports.py`**

Tambahkan di akhir `app/modules/payment_memo/exports.py` (setelah `export_open_pam_excel`):

```python
def export_pam_tab_excel(company_id: int, search: str = "", bulan: str = "",
                          tahun: str = "", source: str = "") -> bytes:
    from modules.payment_memo.service import get_pam_list
    rows    = get_pam_list(company_id, search, bulan, tahun, source)
    headers = ["PAM No", "PAM Date", "PT", "Cost Center", "GL Account",
               "Requestor", "Catatan Payment", "Total (Rp)", "Due Date",
               "Tgl Paid", "Status"]
    fields  = ["pam_no", "pam_date", "pt", "cost_center", "gl_account",
               "requestors_name", "keterangan", "total_amount", "due_date",
               "tanggal_bayar", "status"]
    widths  = [22, 12, 20, 14, 16, 20, 28, 16, 12, 12, 12]
    return _make_xlsx("PAM AGRI", headers, fields, rows, widths)
```

- [ ] **Step 2.4: Tambah route AGRI di `routes.py`**

Update import exports di `app/modules/payment_memo/routes.py`:

```python
from modules.payment_memo.exports import (
    export_pam_pdf, export_pam_excel,
    export_pam_pdf_custom, export_pam_excel_custom,
    export_open_pam_excel, export_pam_tab_excel,
)
```

Tambah route setelah `export_open_pam_route`:

```python
@bp.route("/export/pam")
@jwt_html_required
def export_pam_tab_route():
    company_id = session.get("company_id")
    if not company_id:
        return jsonify({"ok": False, "pesan": "Perusahaan belum dipilih."}), 400
    search = request.args.get("search", "").strip()
    bulan  = request.args.get("bulan",  "").strip()
    tahun  = request.args.get("tahun",  "").strip()
    source = request.args.get("source", "").strip()
    from datetime import datetime
    xls   = export_pam_tab_excel(company_id, search, bulan, tahun, source)
    fname = f"PAM_AGRI_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    return send_file(
        io.BytesIO(xls),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        download_name=fname,
        as_attachment=True,
    )
```

- [ ] **Step 2.5: Tambah tombol Export + JS di tab AGRI**

Di `app/templates/payment_memo/index.html`, cari:

```html
      <select id="pam-filter-source" onchange="loadPAMDebounced()"
              style="padding:6px 10px;border:1px solid #d1d5db;border-radius:6px;font-size:13px;color:#374151">
        <option value="">Semua Tipe</option>
        <option value="agri">AGRI</option>
        <option value="app">APP</option>
        <option value="sml">SML</option>
        <option value="setf">SETF</option>
      </select>
    </div>
```

Ubah menjadi:

```html
      <select id="pam-filter-source" onchange="loadPAMDebounced()"
              style="padding:6px 10px;border:1px solid #d1d5db;border-radius:6px;font-size:13px;color:#374151">
        <option value="">Semua Tipe</option>
        <option value="agri">AGRI</option>
        <option value="app">APP</option>
        <option value="sml">SML</option>
        <option value="setf">SETF</option>
      </select>
      <button class="btn btn-success btn-sm" onclick="exportPamTabExcel()">↓ Export Excel</button>
    </div>
```

Lalu di bagian `<script>` di akhir template (sebelum tag `</script>` penutup), tambahkan:

```javascript
function exportPamTabExcel() {
  const url    = new URL('/payment-memo/export/pam', window.location.origin);
  const search = (document.getElementById('pam-search')?.value || '').trim();
  const bulan  = document.getElementById('pam-filter-bulan')?.value || '';
  const tahun  = document.getElementById('pam-filter-tahun')?.value || '';
  const source = document.getElementById('pam-filter-source')?.value || '';
  if (search) url.searchParams.set('search', search);
  if (bulan)  url.searchParams.set('bulan',  bulan);
  if (tahun)  url.searchParams.set('tahun',  tahun);
  if (source) url.searchParams.set('source', source);
  window.location.href = url.toString();
}
```

- [ ] **Step 2.6: Jalankan test untuk konfirmasi lulus**

```bash
cd app && python -m pytest tests/test_export_excel.py::test_export_pam_tab_returns_xlsx -v
```

Expected: `PASSED`

- [ ] **Step 2.7: Commit**

```bash
git add app/modules/payment_memo/exports.py app/modules/payment_memo/routes.py app/templates/payment_memo/index.html app/tests/test_export_excel.py
git commit -m "feat: add AGRI (PAM) tab export to Excel"
```

---

## Task 3: APP tab export

**Files:**
- Modify: `app/modules/payment_memo/exports.py`
- Modify: `app/modules/payment_memo/routes.py`
- Modify: `app/templates/payment_memo/index.html`
- Modify: `app/tests/test_export_excel.py`

- [ ] **Step 3.1: Tambah test APP export ke `test_export_excel.py`**

```python
def test_export_fiori_returns_xlsx():
    from modules.payment_memo.exports import export_fiori_excel
    conn = get_conn()
    conn.execute(
        """INSERT INTO fiori_pa
           (no_pa, category, keterangan, categori_1, nama_vendor, total,
            terima_document, status)
           VALUES (?,?,?,?,?,?,?,?)""",
        ("APP-001", "General", "Pembayaran A", "Cat1", "PT XYZ",
         3000000, "2026-05-10", "open")
    )
    conn.commit(); conn.close()
    result = export_fiori_excel(search="", bulan="05", tahun="2026")
    assert isinstance(result, bytes) and result[:2] == b'PK'
```

- [ ] **Step 3.2: Jalankan test untuk konfirmasi gagal**

```bash
cd app && python -m pytest tests/test_export_excel.py::test_export_fiori_returns_xlsx -v
```

Expected: `FAILED` — `ImportError: cannot import name 'export_fiori_excel'`

- [ ] **Step 3.3: Tambah `export_fiori_excel` ke `exports.py`**

Tambahkan di akhir `app/modules/payment_memo/exports.py`:

```python
def export_fiori_excel(search: str = "", bulan: str = "", tahun: str = "") -> bytes:
    from modules.payment_memo.service import get_fiori_list
    rows    = get_fiori_list(search, bulan, tahun)
    headers = ["NO PA", "Category", "Keterangan", "Cat 1", "Nama Vendor",
               "Total (Rp)", "Terima Doc", "Input Aspiro", "Verifikasi Tax",
               "Approval 1", "Approval 2", "Kirim Aspiro", "Paid", "Status"]
    fields  = ["no_pa", "category", "keterangan", "categori_1", "nama_vendor",
               "total", "terima_document", "input_aspiro", "verifikasi_tax",
               "approval_1", "approval_2", "kirim_aspiro", "paid", "status"]
    widths  = [16, 12, 28, 12, 24, 14, 12, 12, 12, 12, 12, 12, 12, 12]
    return _make_xlsx("APP (Fiori)", headers, fields, rows, widths)
```

- [ ] **Step 3.4: Tambah route APP di `routes.py`**

Update import exports di `app/modules/payment_memo/routes.py`:

```python
from modules.payment_memo.exports import (
    export_pam_pdf, export_pam_excel,
    export_pam_pdf_custom, export_pam_excel_custom,
    export_open_pam_excel, export_pam_tab_excel,
    export_fiori_excel,
)
```

Tambah route:

```python
@bp.route("/export/fiori")
@jwt_html_required
def export_fiori_route():
    search = request.args.get("search", "").strip()
    bulan  = request.args.get("bulan",  "").strip()
    tahun  = request.args.get("tahun",  "").strip()
    from datetime import datetime
    xls   = export_fiori_excel(search, bulan, tahun)
    fname = f"PAM_APP_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    return send_file(
        io.BytesIO(xls),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        download_name=fname,
        as_attachment=True,
    )
```

- [ ] **Step 3.5: Tambah tombol Export + JS di tab APP**

Di `app/templates/payment_memo/index.html`, cari:

```html
      <button id="fiori-update-btn" class="btn btn-primary btn-sm" onclick="fioriBulkUpdate()" disabled style="opacity:.5">Update Terpilih (0)</button>
      <button class="btn btn-secondary btn-sm" onclick="fioriClearDates()">Reset Tanggal</button>
      <span id="fiori-count" style="font-size:11px;color:#6b7280"></span>
    </div>
```

Ubah menjadi:

```html
      <button id="fiori-update-btn" class="btn btn-primary btn-sm" onclick="fioriBulkUpdate()" disabled style="opacity:.5">Update Terpilih (0)</button>
      <button class="btn btn-secondary btn-sm" onclick="fioriClearDates()">Reset Tanggal</button>
      <button class="btn btn-success btn-sm" onclick="exportFioriExcel()">↓ Export Excel</button>
      <span id="fiori-count" style="font-size:11px;color:#6b7280"></span>
    </div>
```

Tambah fungsi JS di bagian `<script>` akhir template:

```javascript
function exportFioriExcel() {
  const url    = new URL('/payment-memo/export/fiori', window.location.origin);
  const search = (document.getElementById('fiori-search')?.value || '').trim();
  const bulan  = document.getElementById('fiori-filter-bulan')?.value || '';
  const tahun  = document.getElementById('fiori-filter-tahun')?.value || '';
  if (search) url.searchParams.set('search', search);
  if (bulan)  url.searchParams.set('bulan',  bulan);
  if (tahun)  url.searchParams.set('tahun',  tahun);
  window.location.href = url.toString();
}
```

- [ ] **Step 3.6: Jalankan test untuk konfirmasi lulus**

```bash
cd app && python -m pytest tests/test_export_excel.py::test_export_fiori_returns_xlsx -v
```

Expected: `PASSED`

- [ ] **Step 3.7: Commit**

```bash
git add app/modules/payment_memo/exports.py app/modules/payment_memo/routes.py app/templates/payment_memo/index.html app/tests/test_export_excel.py
git commit -m "feat: add APP (Fiori) tab export to Excel"
```

---

## Task 4: SML tab export

**Files:**
- Modify: `app/modules/payment_memo/exports.py`
- Modify: `app/modules/payment_memo/routes.py`
- Modify: `app/templates/payment_memo/index.html`
- Modify: `app/tests/test_export_excel.py`

- [ ] **Step 4.1: Tambah test SML export ke `test_export_excel.py`**

```python
def test_export_sml_returns_xlsx():
    from modules.payment_memo.exports import export_sml_excel
    conn = get_conn()
    conn.execute(
        """INSERT INTO sml_pa
           (no_pa, category, keterangan, categori_1, nama_vendor, total,
            terima_document, status)
           VALUES (?,?,?,?,?,?,?,?)""",
        ("SML-001", "General", "Pembayaran SML", "Cat1", "PT SML",
         4000000, "2026-05-15", "open")
    )
    conn.commit(); conn.close()
    result = export_sml_excel(search="", bulan="05", tahun="2026")
    assert isinstance(result, bytes) and result[:2] == b'PK'
```

- [ ] **Step 4.2: Jalankan test untuk konfirmasi gagal**

```bash
cd app && python -m pytest tests/test_export_excel.py::test_export_sml_returns_xlsx -v
```

Expected: `FAILED` — `ImportError: cannot import name 'export_sml_excel'`

- [ ] **Step 4.3: Tambah `export_sml_excel` ke `exports.py`**

Tambahkan di akhir `app/modules/payment_memo/exports.py`:

```python
def export_sml_excel(search: str = "", bulan: str = "", tahun: str = "") -> bytes:
    from modules.payment_memo.service import get_sml_list
    rows    = get_sml_list(search, bulan, tahun)
    headers = ["NO PA", "Category", "Keterangan", "Cat 1", "Nama Vendor",
               "Total (Rp)", "Terima Doc", "Input Aspiro", "Verifikasi Tax",
               "Approval 1", "Approval 2", "Kirim Aspiro", "Paid", "Status"]
    fields  = ["no_pa", "category", "keterangan", "categori_1", "nama_vendor",
               "total", "terima_document", "input_aspiro", "verifikasi_tax",
               "approval_1", "approval_2", "kirim_aspiro", "paid", "status"]
    widths  = [16, 12, 28, 12, 24, 14, 12, 12, 12, 12, 12, 12, 12, 12]
    return _make_xlsx("SML", headers, fields, rows, widths)
```

- [ ] **Step 4.4: Tambah route SML di `routes.py`**

Update import exports:

```python
from modules.payment_memo.exports import (
    export_pam_pdf, export_pam_excel,
    export_pam_pdf_custom, export_pam_excel_custom,
    export_open_pam_excel, export_pam_tab_excel,
    export_fiori_excel, export_sml_excel,
)
```

Tambah route:

```python
@bp.route("/export/sml")
@jwt_html_required
def export_sml_route():
    search = request.args.get("search", "").strip()
    bulan  = request.args.get("bulan",  "").strip()
    tahun  = request.args.get("tahun",  "").strip()
    from datetime import datetime
    xls   = export_sml_excel(search, bulan, tahun)
    fname = f"PAM_SML_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    return send_file(
        io.BytesIO(xls),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        download_name=fname,
        as_attachment=True,
    )
```

- [ ] **Step 4.5: Tambah tombol Export + JS di tab SML**

Di `app/templates/payment_memo/index.html`, cari:

```html
      <button id="sml-update-btn" class="btn btn-primary btn-sm" onclick="smlBulkUpdate()" disabled style="opacity:.5">Update Terpilih (0)</button>
      <button class="btn btn-secondary btn-sm" onclick="smlClearDates()">Reset Tanggal</button>
      <span id="sml-count" style="font-size:11px;color:#6b7280"></span>
    </div>
```

Ubah menjadi:

```html
      <button id="sml-update-btn" class="btn btn-primary btn-sm" onclick="smlBulkUpdate()" disabled style="opacity:.5">Update Terpilih (0)</button>
      <button class="btn btn-secondary btn-sm" onclick="smlClearDates()">Reset Tanggal</button>
      <button class="btn btn-success btn-sm" onclick="exportSmlExcel()">↓ Export Excel</button>
      <span id="sml-count" style="font-size:11px;color:#6b7280"></span>
    </div>
```

Tambah fungsi JS di bagian `<script>` akhir template:

```javascript
function exportSmlExcel() {
  const url    = new URL('/payment-memo/export/sml', window.location.origin);
  const search = (document.getElementById('sml-search')?.value || '').trim();
  const bulan  = document.getElementById('sml-filter-bulan')?.value || '';
  const tahun  = document.getElementById('sml-filter-tahun')?.value || '';
  if (search) url.searchParams.set('search', search);
  if (bulan)  url.searchParams.set('bulan',  bulan);
  if (tahun)  url.searchParams.set('tahun',  tahun);
  window.location.href = url.toString();
}
```

- [ ] **Step 4.6: Jalankan test untuk konfirmasi lulus**

```bash
cd app && python -m pytest tests/test_export_excel.py::test_export_sml_returns_xlsx -v
```

Expected: `PASSED`

- [ ] **Step 4.7: Commit**

```bash
git add app/modules/payment_memo/exports.py app/modules/payment_memo/routes.py app/templates/payment_memo/index.html app/tests/test_export_excel.py
git commit -m "feat: add SML tab export to Excel"
```

---

## Task 5: SLA tab export

**Files:**
- Modify: `app/modules/payment_memo/exports.py`
- Modify: `app/modules/payment_memo/routes.py`
- Modify: `app/templates/payment_memo/index.html`
- Modify: `app/tests/test_export_excel.py`

- [ ] **Step 5.1: Tambah test SLA export ke `test_export_excel.py`**

```python
def test_export_sla_returns_xlsx():
    from modules.payment_memo.exports import export_sla_excel
    # _seed() sudah memasukkan payment_beasiswa dengan pam=NULL
    # Tambah satu dengan pam terisi
    conn = get_conn()
    conn.execute(
        """UPDATE payment_beasiswa SET pam='PAM-001-ETF-05-2026'
           WHERE company_id=? AND siswa_code='S001'""",
        (COMPANY_ID,)
    )
    conn.commit(); conn.close()
    result = export_sla_excel(COMPANY_ID, pam="PAM-001", nama="")
    assert isinstance(result, bytes) and result[:2] == b'PK'

def test_export_sla_no_filter_returns_xlsx():
    from modules.payment_memo.exports import export_sla_excel
    conn = get_conn()
    conn.execute(
        "UPDATE payment_beasiswa SET pam='PAM-002' WHERE company_id=?",
        (COMPANY_ID,)
    )
    conn.commit(); conn.close()
    result = export_sla_excel(COMPANY_ID)
    assert isinstance(result, bytes) and result[:2] == b'PK'
```

- [ ] **Step 5.2: Jalankan test untuk konfirmasi gagal**

```bash
cd app && python -m pytest tests/test_export_excel.py::test_export_sla_returns_xlsx tests/test_export_excel.py::test_export_sla_no_filter_returns_xlsx -v
```

Expected: `FAILED` — `ImportError: cannot import name 'export_sla_excel'`

- [ ] **Step 5.3: Tambah `export_sla_excel` ke `exports.py`**

Tambahkan di akhir `app/modules/payment_memo/exports.py`:

```python
def export_sla_excel(company_id: int, pam: str = "", nama: str = "") -> bytes:
    from modules.payment_memo.service import get_days_of_pam
    rows = get_days_of_pam(company_id)
    if pam:
        rows = [r for r in rows if pam.lower() in (r.get("pam_no") or "").lower()]
    if nama:
        rows = [r for r in rows if nama.lower() in (r.get("nama") or "").lower()]
    headers = ["Siswa Code", "Nama Siswa", "PAM NO", "Cat 1", "Cat 2", "Perusahaan",
               "Pillar", "Amount (Rp)", "Tanggal", "Tgl Pengajuan", "Tgl Receive",
               "Tgl PA", "Tgl Final", "tgl_retur", "tgl_final6", "tgl_proses",
               "tgl_HT_AGRI", "tgl_Yurike_AGRI", "tgl_Aditya_AGRI", "tgl_Pedy_AGRI",
               "tgl_C2_AGRI", "tgl_MSIG_AGRI", "tgl_Paid_AGRI",
               "tgl_A-GS_APP", "tgl_A-HJK_APP", "tgl_ASPIRO_APP", "tgl_Paid_APP"]
    fields  = ["siswa_code", "nama", "pam_no", "cat1", "cat2", "perusahaan",
               "pillar", "amount", "tanggal", "tgl_pengajuan", "tgl_receive",
               "tgl_pa", "tgl_final", "tgl_retur", "tgl_final6", "tgl_proses",
               "tgl_HT_AGRI", "tgl_Yurike_AGRI", "tgl_Aditya_AGRI", "tgl_Pedy_AGRI",
               "tgl_C2_AGRI", "tgl_MSIG_AGRI", "tgl_Paid_AGRI",
               "tgl_A-GS_APP", "tgl_A-HJK_APP", "tgl_ASPIRO_APP", "tgl_Paid_APP"]
    widths  = [12, 22, 22, 14, 14, 22, 10, 14, 12, 12, 12, 12, 12,
               12, 12, 12, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14]
    return _make_xlsx("SLA", headers, fields, rows, widths)
```

- [ ] **Step 5.4: Tambah route SLA di `routes.py`**

Update import exports:

```python
from modules.payment_memo.exports import (
    export_pam_pdf, export_pam_excel,
    export_pam_pdf_custom, export_pam_excel_custom,
    export_open_pam_excel, export_pam_tab_excel,
    export_fiori_excel, export_sml_excel, export_sla_excel,
)
```

Tambah route:

```python
@bp.route("/export/sla")
@jwt_html_required
def export_sla_route():
    company_id = session.get("company_id")
    if not company_id:
        return jsonify({"ok": False, "pesan": "Perusahaan belum dipilih."}), 400
    pam  = request.args.get("pam",  "").strip()
    nama = request.args.get("nama", "").strip()
    from datetime import datetime
    xls   = export_sla_excel(company_id, pam, nama)
    fname = f"PAM_SLA_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    return send_file(
        io.BytesIO(xls),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        download_name=fname,
        as_attachment=True,
    )
```

- [ ] **Step 5.5: Tambah tombol Export + JS di tab SLA**

Di `app/templates/payment_memo/index.html`, cari:

```html
        <button class="btn btn-success btn-sm" onclick="_dopFetchCurrent()">🔍 Cari</button>
        <button class="btn btn-secondary btn-sm" onclick="dopClearSearch()">Bersihkan</button>
        <button id="dop-update-btn" class="btn btn-primary btn-sm" onclick="dopBulkUpdate()" disabled style="opacity:.5">Update Terpilih (0)</button>
```

Ubah menjadi:

```html
        <button class="btn btn-success btn-sm" onclick="_dopFetchCurrent()">🔍 Cari</button>
        <button class="btn btn-secondary btn-sm" onclick="dopClearSearch()">Bersihkan</button>
        <button class="btn btn-success btn-sm" onclick="exportSlaExcel()">↓ Export Excel</button>
        <button id="dop-update-btn" class="btn btn-primary btn-sm" onclick="dopBulkUpdate()" disabled style="opacity:.5">Update Terpilih (0)</button>
```

Tambah fungsi JS di bagian `<script>` akhir template:

```javascript
function exportSlaExcel() {
  const url  = new URL('/payment-memo/export/sla', window.location.origin);
  const pam  = (document.getElementById('dop-s-pam')?.value  || '').trim();
  const nama = (document.getElementById('dop-s-nama')?.value || '').trim();
  if (pam)  url.searchParams.set('pam',  pam);
  if (nama) url.searchParams.set('nama', nama);
  window.location.href = url.toString();
}
```

- [ ] **Step 5.6: Jalankan test untuk konfirmasi lulus**

```bash
cd app && python -m pytest tests/test_export_excel.py::test_export_sla_returns_xlsx tests/test_export_excel.py::test_export_sla_no_filter_returns_xlsx -v
```

Expected: `PASSED`

- [ ] **Step 5.7: Commit**

```bash
git add app/modules/payment_memo/exports.py app/modules/payment_memo/routes.py app/templates/payment_memo/index.html app/tests/test_export_excel.py
git commit -m "feat: add SLA (Days of PAM) tab export to Excel"
```

---

## Task 6: Payment Application export

**Files:**
- Modify: `app/modules/payment_application/service.py`
- Modify: `app/modules/payment_application/routes.py`
- Modify: `app/templates/payment_application/index.html`
- Modify: `app/tests/test_export_excel.py`

- [ ] **Step 6.1: Tambah test Payment Application export ke `test_export_excel.py`**

```python
def test_export_application_returns_xlsx():
    from modules.payment_application.service import export_application_excel
    conn = get_conn()
    conn.execute(
        """INSERT INTO payment_memo
           (company_id, memo_number, tanggal, total_amount, status, notes, created_by, created_at)
           VALUES (?,?,?,?,?,?,?,?)""",
        (COMPANY_ID, "PAM/ETF/2026/001", "2026-05-01", 5000000,
         "on_process", "", "admin", "2026-05-01T10:00:00")
    )
    memo_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.execute(
        """INSERT INTO payment_application
           (company_id, memo_id, application_number, submitted_at, status, created_at)
           VALUES (?,?,?,?,?,?)""",
        (COMPANY_ID, memo_id, "APP/2/2026/0001", "2026-05-10", "open",
         "2026-05-10T10:00:00")
    )
    conn.commit(); conn.close()
    result = export_application_excel(COMPANY_ID, month=5, year=2026)
    assert isinstance(result, bytes) and result[:2] == b'PK'
```

- [ ] **Step 6.2: Jalankan test untuk konfirmasi gagal**

```bash
cd app && python -m pytest tests/test_export_excel.py::test_export_application_returns_xlsx -v
```

Expected: `FAILED` — `ImportError: cannot import name 'export_application_excel'`

- [ ] **Step 6.3: Tambah `export_application_excel` ke `service.py`**

Tambahkan di akhir `app/modules/payment_application/service.py`:

```python
def export_application_excel(company_id: int, month: int = None, year: int = None) -> bytes:
    import io
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

    rows = get_applications(company_id, month=month, year=year)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Payment Application"

    col_headers = ["No. Application", "Memo", "Tgl Pengajuan", "Target Bayar",
                   "Aktual Bayar", "Total (Rp)", "TAT (hari kerja)", "Status"]
    fields      = ["application_number", "memo_number", "submitted_at",
                   "target_payment_date", "actual_payment_date", "total_amount",
                   "tat_days", "status"]
    col_widths  = [22, 20, 14, 14, 14, 16, 14, 12]

    hdr_fill = PatternFill("solid", fgColor="1E3A5F")
    hdr_font = Font(bold=True, color="FFFFFF", size=10)
    thin     = Side(style="thin", color="D1D5DB")
    border   = Border(left=thin, right=thin, top=thin, bottom=thin)

    for col, h in enumerate(col_headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.font = hdr_font; cell.fill = hdr_fill
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = border
    ws.row_dimensions[1].height = 32

    for ri, r in enumerate(rows, 2):
        for ci, f in enumerate(fields, 1):
            val  = r.get(f, "") or ""
            cell = ws.cell(row=ri, column=ci, value=val)
            cell.font = Font(size=9); cell.border = border
            cell.alignment = Alignment(vertical="top")

    for ci, w in enumerate(col_widths, 1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(ci)].width = w

    ws.freeze_panes    = "A2"
    ws.auto_filter.ref = ws.dimensions

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
```

- [ ] **Step 6.4: Tambah route di `payment_application/routes.py`**

Di `app/modules/payment_application/routes.py`, ubah baris import service:

```python
from modules.payment_application.service import (
    get_applications, create_application, update_actual_payment,
    export_application_excel,
)
```

Tambah import `io` dan `Response` di baris import flask (baris 1):

```python
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session, send_file
import io
```

Tambah route baru setelah route `update_payment`:

```python
@bp.route("/export")
@jwt_html_required
def export_excel():
    company_id = session.get("company_id")
    if not company_id:
        return redirect(url_for("dashboard.select_company"))
    month = request.args.get("month", type=int)
    year  = request.args.get("year",  type=int)
    from datetime import datetime
    xls   = export_application_excel(company_id, month=month, year=year)
    fname = f"Payment_Application_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    return send_file(
        io.BytesIO(xls),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        download_name=fname,
        as_attachment=True,
    )
```

- [ ] **Step 6.5: Tambah tombol Export di template Payment Application**

Di `app/templates/payment_application/index.html`, cari:

```html
<div style="display:flex;align-items:center;gap:12px;margin-bottom:16px;flex-wrap:wrap">
  <form method="get" style="display:flex;align-items:center;gap:12px;flex-wrap:wrap">
```

Ubah menjadi:

```html
<div style="display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:16px;flex-wrap:wrap">
  <form method="get" style="display:flex;align-items:center;gap:12px;flex-wrap:wrap">
```

Cari penutup `</form>` di blok filter tersebut (setelah tag `</form>` yang mengandung select month dan year), lalu tambahkan tombol export setelah `</form>`:

```html
    {% if filter_month or filter_year %}
    <a href="?" class="btn btn-secondary btn-sm pa-filter-reset">Reset</a>
    {% endif %}
  </form>
  <a href="/payment-application/export?month={{ filter_month or '' }}&year={{ filter_year or '' }}"
     class="btn btn-success btn-sm">↓ Export Excel</a>
</div>
```

- [ ] **Step 6.6: Jalankan test untuk konfirmasi lulus**

```bash
cd app && python -m pytest tests/test_export_excel.py::test_export_application_returns_xlsx -v
```

Expected: `PASSED`

- [ ] **Step 6.7: Commit**

```bash
git add app/modules/payment_application/service.py app/modules/payment_application/routes.py app/templates/payment_application/index.html app/tests/test_export_excel.py
git commit -m "feat: add Payment Application export to Excel"
```

---

## Task 7: ETF Payment Application — perbaiki filter-aware export

**Files:**
- Modify: `app/modules/etf_payment_application/service.py`
- Modify: `app/modules/etf_payment_application/routes.py`
- Modify: `app/templates/etf_payment_application/index.html`
- Modify: `app/tests/test_export_excel.py`

- [ ] **Step 7.1: Tambah test ETF PA export dengan filter ke `test_export_excel.py`**

```python
def test_export_etf_pa_with_filters():
    from modules.etf_payment_application.service import export_pa_excel
    conn = get_conn()
    # seed ETF PA data
    conn.execute(
        """INSERT INTO siswa (company_id, code, nama, jenjang, program, status, angkatan, universitas)
           VALUES (?,?,?,?,?,?,?,?)""",
        (COMPANY_ID, "ETF001", "Andi Wijaya", "S1", "SMART", "Aktif", 2022, "UI")
    )
    siswa_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.execute(
        """INSERT INTO etf_pa
           (company_id, pa_number, tgl_payment_application, status, created_at)
           VALUES (?,?,?,?,?)""",
        (COMPANY_ID, "ETF-001-05-2026", "2026-05-10", "open", "2026-05-10T10:00:00")
    )
    pa_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.execute(
        """INSERT INTO etf_pa_lines
           (pa_id, student_id, jenis_pembayaran, jumlah_pembayaran, semester, tahun_ajaran)
           VALUES (?,?,?,?,?,?)""",
        (pa_id, siswa_id, "UKT", 5000000, "1", "2026/2027")
    )
    conn.commit(); conn.close()
    # export tanpa filter — harus ada 1 baris
    result = export_pa_excel(COMPANY_ID, tab="agri", sf="", nama="Andi")
    assert isinstance(result, bytes) and result[:2] == b'PK'
    # export dengan filter nama yang tidak cocok — tetap valid xlsx (0 data)
    result2 = export_pa_excel(COMPANY_ID, tab="agri", sf="", nama="ZZZ_TIDAK_ADA")
    assert isinstance(result2, bytes) and result2[:2] == b'PK'
```

- [ ] **Step 7.2: Jalankan test untuk konfirmasi gagal**

```bash
cd app && python -m pytest tests/test_export_excel.py::test_export_etf_pa_with_filters -v
```

Expected: `FAILED` — `TypeError: export_pa_excel() got an unexpected keyword argument 'nama'`

- [ ] **Step 7.3: Modifikasi `export_pa_excel` di `service.py`**

Di `app/modules/etf_payment_application/service.py`, cari fungsi `export_pa_excel`:

```python
def export_pa_excel(company_id: int, tab: str = "agri") -> bytes:
    import io
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

    rows = get_pa_flat(company_id, tab)
```

Ubah menjadi:

```python
def export_pa_excel(
    company_id: int,
    tab: str = "agri",
    sf: str = "",
    nama: str = "",
    jenjang: str = "",
    program: str = "",
    angkatan: str = "",
    jenis: str = "",
    pam: str = "",
    bulan_pa: str = "",
    tahun_pa: str = "",
) -> bytes:
    import io
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

    rows = get_pa_flat(company_id, tab, sf)
    if nama:
        rows = [r for r in rows if nama.lower() in (r.get("nama") or "").lower()]
    if jenjang:
        rows = [r for r in rows if r.get("jenjang_pendidikan") == jenjang]
    if program:
        rows = [r for r in rows if r.get("program_beasiswa") == program]
    if angkatan:
        rows = [r for r in rows if str(r.get("angkatan_etf") or "") == str(angkatan)]
    if jenis:
        rows = [r for r in rows if r.get("jenis_pembayaran") == jenis]
    if pam:
        rows = [r for r in rows if pam.lower() in (r.get("nomor_pam") or "").lower()]
    if bulan_pa:
        rows = [r for r in rows if (r.get("tgl_payment_application") or "")[5:7] == bulan_pa]
    if tahun_pa:
        rows = [r for r in rows if (r.get("tgl_payment_application") or "")[0:4] == tahun_pa]
```

Baris-baris berikutnya (tab_label, wb, ws, dll.) tidak diubah.

- [ ] **Step 7.4: Modifikasi route `export_excel` di `routes.py`**

Di `app/modules/etf_payment_application/routes.py`, cari:

```python
@bp.route("/export-excel")
@jwt_html_required
def export_excel():
    company_id = session.get("company_id")
    tab = _tab()
    data = export_pa_excel(company_id, tab)
    from datetime import datetime
    fname = f"{tab.upper()}_PA_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
```

Ubah menjadi:

```python
@bp.route("/export-excel")
@jwt_html_required
def export_excel():
    company_id = session.get("company_id")
    tab = _tab()
    data = export_pa_excel(
        company_id, tab,
        sf       = request.args.get("sf",       "").strip(),
        nama     = request.args.get("nama",     "").strip(),
        jenjang  = request.args.get("jenjang",  "").strip(),
        program  = request.args.get("program",  "").strip(),
        angkatan = request.args.get("angkatan", "").strip(),
        jenis    = request.args.get("jenis",    "").strip(),
        pam      = request.args.get("pam",      "").strip(),
        bulan_pa = request.args.get("bulan_pa", "").strip(),
        tahun_pa = request.args.get("tahun_pa", "").strip(),
    )
    from datetime import datetime
    fname = f"ETF_PA_{tab.upper()}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
```

- [ ] **Step 7.5: Ubah tombol export di template ETF PA menjadi fungsi JS**

Di `app/templates/etf_payment_application/index.html`, cari:

```html
    <a href="/etf-payment-application/export-excel?tab={{ active_tab }}" class="btn btn-secondary">↓ Export Excel</a>
```

Ubah menjadi:

```html
    <button class="btn btn-secondary" onclick="exportETFExcel()">↓ Export Excel</button>
```

Tambah fungsi JS berikut di dalam blok `{% block scripts %}` (atau di dekat akhir `<script>` yang sudah ada):

```javascript
function exportETFExcel() {
  const url = new URL('/etf-payment-application/export-excel', window.location.origin);
  url.searchParams.set('tab', '{{ active_tab }}');
  const sf       = document.getElementById('f-status')?.value    || '';
  const nama     = (document.getElementById('f-nama')?.value     || '').trim();
  const jenjang  = document.getElementById('f-jenjang')?.value   || '';
  const program  = document.getElementById('f-program')?.value   || '';
  const angkatan = document.getElementById('f-angkatan')?.value  || '';
  const jenis    = document.getElementById('f-jenis')?.value     || '';
  const pam      = (document.getElementById('f-pam')?.value      || '').trim();
  const bulanPa  = document.getElementById('f-bulan-pa')?.value  || '';
  const tahunPa  = document.getElementById('f-tahun-pa')?.value  || '';
  if (sf)       url.searchParams.set('sf',       sf);
  if (nama)     url.searchParams.set('nama',     nama);
  if (jenjang)  url.searchParams.set('jenjang',  jenjang);
  if (program)  url.searchParams.set('program',  program);
  if (angkatan) url.searchParams.set('angkatan', angkatan);
  if (jenis)    url.searchParams.set('jenis',    jenis);
  if (pam)      url.searchParams.set('pam',      pam);
  if (bulanPa)  url.searchParams.set('bulan_pa', bulanPa);
  if (tahunPa)  url.searchParams.set('tahun_pa', tahunPa);
  window.location.href = url.toString();
}
```

- [ ] **Step 7.6: Jalankan test untuk konfirmasi lulus**

```bash
cd app && python -m pytest tests/test_export_excel.py::test_export_etf_pa_with_filters -v
```

Expected: `PASSED`

- [ ] **Step 7.7: Jalankan semua test export sekaligus**

```bash
cd app && python -m pytest tests/test_export_excel.py -v
```

Expected: semua `PASSED`

- [ ] **Step 7.8: Pastikan tidak ada regresi pada test lain**

```bash
cd app && python -m pytest tests/ -v --tb=short
```

Expected: semua test yang sebelumnya lulus tetap lulus.

- [ ] **Step 7.9: Commit**

```bash
git add app/modules/etf_payment_application/service.py app/modules/etf_payment_application/routes.py app/templates/etf_payment_application/index.html app/tests/test_export_excel.py
git commit -m "feat: fix ETF Payment Application export to respect active filters"
```

---

## Ringkasan Perubahan

| Task | File yang Diubah | Yang Ditambah |
|------|-----------------|---------------|
| 1 | exports.py, routes.py, index.html (memo), test | `_make_xlsx`, `export_open_pam_excel`, route `/export/open-pam`, tombol Open PAM |
| 2 | exports.py, routes.py, index.html (memo), test | `export_pam_tab_excel`, route `/export/pam`, tombol AGRI |
| 3 | exports.py, routes.py, index.html (memo), test | `export_fiori_excel`, route `/export/fiori`, tombol APP |
| 4 | exports.py, routes.py, index.html (memo), test | `export_sml_excel`, route `/export/sml`, tombol SML |
| 5 | exports.py, routes.py, index.html (memo), test | `export_sla_excel`, route `/export/sla`, tombol SLA |
| 6 | service.py (app), routes.py (app), index.html (app), test | `export_application_excel`, route `/export`, tombol Payment App |
| 7 | service.py (etf), routes.py (etf), index.html (etf), test | Modifikasi `export_pa_excel` + route + JS function |
