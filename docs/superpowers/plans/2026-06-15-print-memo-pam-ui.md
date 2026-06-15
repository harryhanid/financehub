# Print Memo PAM UI & Export Improvements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Perbaiki form Print Memo PAM: bank detail fields pakai data siswa aktual; tambah kolom Jenjang Studi di Detail PAM (UI + PDF); Excel pakai format Rp Accounting dan colon center-aligned dengan wrap_text.

**Architecture:** Perubahan di 2 file. Template HTML/JS untuk form UI (Tasks 1–2, tidak ada pytest). `exports.py` untuk Excel & PDF (Tasks 3–6, pakai pytest dengan openpyxl + ReportLab). Tests baru di `tests/test_print_memo_exports.py`.

**Tech Stack:** Python, openpyxl, ReportLab, Flask, SQLite, pytest, monkeypatch

---

## File yang Diubah

| File | Task | Aksi |
|------|------|------|
| `app/templates/payment_memo/index.html` | 1, 2 | Modify |
| `app/modules/payment_memo/exports.py` | 3, 4, 5, 6 | Modify |
| `tests/test_print_memo_exports.py` | 3, 4, 5, 6 | Create |

---

### Task 1: Template — Form Bank Details dari Data Siswa (Area 1)

**Files:**
- Modify: `app/templates/payment_memo/index.html` (~baris 2517–2562)

*Tidak ada pytest untuk perubahan HTML/JS — verifikasi manual.*

- [ ] **Step 1: Tambah variabel bankAccountNames, bankNames, bankAccountNos**

Buka `app/templates/payment_memo/index.html`. Cari blok ini (sekitar baris 2517):

```javascript
  const vendorNames = [...new Set(
    _dmPayments.map(pb => (pb.nama || pb.siswa_code || '').trim()).filter(Boolean)
  )].join(', ') || 'Terlampir';
```

Tambahkan langsung setelahnya:

```javascript
  const bankAccountNames = [...new Set(
    _dmPayments.map(pb => (pb.namarek || '').trim()).filter(Boolean)
  )].join(', ') || 'Terlampir';
  const bankNames = [...new Set(
    _dmPayments.map(pb => (pb.bank || '').trim()).filter(Boolean)
  )].join(', ') || 'Terlampir';
  const bankAccountNos = [...new Set(
    _dmPayments.map(pb => (pb.norek || '').trim()).filter(Boolean)
  )].join(', ') || 'Terlampir';
```

- [ ] **Step 2: Ganti hardcode 'Terlampir' di 3 bank input fields**

Cari blok ini (sekitar baris 2560):

```javascript
    ${field('Bank Account Name',   inp('dm-f-bank-name', 'Terlampir'))}
    ${field('Bank Name',           inp('dm-f-bank',      'Terlampir'))}
    ${field('Bank Account Number', inp('dm-f-bank-no',   'Terlampir'))}
```

Ganti dengan:

```javascript
    ${field('Bank Account Name',   inp('dm-f-bank-name', bankAccountNames))}
    ${field('Bank Name',           inp('dm-f-bank',      bankNames))}
    ${field('Bank Account Number', inp('dm-f-bank-no',   bankAccountNos))}
```

- [ ] **Step 3: Verifikasi manual**

Jalankan app, buka Print Memo, pilih PAM. Pastikan:
- Field Bank Account Name, Bank Name, Bank Account Number menampilkan data siswa (comma-separated) bukan "Terlampir"
- Jika PAM tidak punya data bank (norek/bank/namarek kosong), field tetap fallback ke "Terlampir"

- [ ] **Step 4: Commit**

```bash
git add app/templates/payment_memo/index.html
git commit -m "feat: populate bank detail fields from siswa data in Print Memo form"
```

---

### Task 2: Template — Kolom Jenjang di Detail PAM Table (Area 2)

**Files:**
- Modify: `app/templates/payment_memo/index.html` (~baris 2697–2762)

*Tidak ada pytest untuk perubahan HTML/JS — verifikasi manual.*

- [ ] **Step 1: Tambah Jenjang Studi ke headers dan aligns**

Cari baris ini (sekitar baris 2701):

```javascript
  const hdrs = ['No','Nama Siswa','Keterangan','By Pendidikan','By Tunjangan','By Penelitian','Total Pbyran','Bank','No. Rekening','Sisa Pend','Sisa Tunj','Sisa Riset'];
  const aligns = ['center','left','left','right','right','right','right','left','left','right','right','right'];
```

Ganti dengan (tambah `'Jenjang Studi'` setelah `'Nama Siswa'` dan `'center'` setelah `'left'` kedua):

```javascript
  const hdrs = ['No','Nama Siswa','Jenjang Studi','Keterangan','By Pendidikan','By Tunjangan','By Penelitian','Total Pbyran','Bank','No. Rekening','Sisa Pend','Sisa Tunj','Sisa Riset'];
  const aligns = ['center','left','center','left','right','right','right','right','left','left','right','right','right'];
```

- [ ] **Step 2: Tambah sel jenjang di first-row block**

Cari blok `if (idx === 0)` yang berisi baris ini:

```javascript
          <td style="padding:5px 7px;font-size:11px;${bTop}border-right:1px solid #e2e8f0"${rs}>${esc(siswa.nama||siswa.siswa_code||'')}</td>
          ${td(esc(pr.keterangan||''))}
```

Tambahkan satu baris di antara keduanya:

```javascript
          <td style="padding:5px 7px;font-size:11px;${bTop}border-right:1px solid #e2e8f0"${rs}>${esc(siswa.nama||siswa.siswa_code||'')}</td>
          <td style="padding:5px 7px;font-size:11px;text-align:center;${bTop}"${rs}>${esc(siswa.jenjang||'')}</td>
          ${td(esc(pr.keterangan||''))}
```

- [ ] **Step 3: Update colspan footer TOTAL**

Cari baris ini di footer (sekitar baris 2755):

```javascript
          <td colspan="6" style="padding:6px 8px;font-size:11px;text-align:right;border-top:1.5px solid #1e3a5f">TOTAL</td>
```

Ganti `colspan="6"` dengan `colspan="7"`:

```javascript
          <td colspan="7" style="padding:6px 8px;font-size:11px;text-align:right;border-top:1.5px solid #1e3a5f">TOTAL</td>
```

- [ ] **Step 4: Verifikasi manual**

Buka Detail PAM di form Print Memo. Pastikan:
- Kolom "Jenjang Studi" muncul setelah "Nama Siswa"
- Nilai jenjang (S1/S2/S3/dll) tampil di setiap baris siswa dengan rowspan yang benar
- Baris TOTAL di footer lurus (tidak geser)

- [ ] **Step 5: Commit**

```bash
git add app/templates/payment_memo/index.html
git commit -m "feat: add Jenjang Studi column to Detail PAM table in Print Memo form"
```

---

### Task 3: Excel PAM NEW — Colon Center Aligned + Wrap Text (Areas 3 & 4)

**Files:**
- Modify: `app/modules/payment_memo/exports.py` (fungsi `export_pam_excel_custom`, ~baris 1255–1402)
- Create: `tests/test_print_memo_exports.py`

- [ ] **Step 1: Buat file test dan tulis failing tests**

Buat `tests/test_print_memo_exports.py`:

```python
import io
import openpyxl
import pytest

_RP_FMT = '_-"Rp"* #,##0_-;\\-"Rp"* #,##0_-;_-"Rp"* "-"_-;_-@_-'


def _data():
    return {
        "pam_no": "PAM-TEST", "pam_date": "2026-06-15",
        "requestors_name": "Tester", "department": "-",
        "cost_center": "CC-001", "gl_account": "GL-001",
        "so_sc": "", "pt": "PT TEST",
        "bu_corporate": True, "bu_upstream": False, "bu_downstream": False,
        "type_invoice": True, "type_downpayment": False, "type_advance": False,
        "vendor_name": "Budi Santoso, Ali Rahman",
        "invoice_memo_no": "-",
        "total_amount": 5_000_000,
        "due_date": "2026-07-01",
        "bank_account_name": "Budi Santoso, Ali Rahman",
        "bank_name": "BNI, BCA",
        "bank_account_no": "111, 222",
        "approved_by_1": "Mgr", "approved_by_2": "Dir",
        "company_id": 1,
    }


def _payments():
    return [
        {"siswa_code": "S2A", "nama": "Ali", "bank": "BCA", "norek": "222",
         "namarek": "Ali Rahman", "jenjang": "S2", "amount": 2_000_000,
         "cat1": "By Pendidikan", "cat2": None, "tanggal": "2026-06-01"},
        {"siswa_code": "S1A", "nama": "Budi", "bank": "BNI", "norek": "111",
         "namarek": "Budi Santoso", "jenjang": "S1", "amount": 3_000_000,
         "cat1": "By Pendidikan", "cat2": None, "tanggal": "2026-06-01"},
    ]


def test_excel_pam_new_colons_center_aligned(monkeypatch):
    from app.modules.payment_memo import exports
    monkeypatch.setattr(exports, "get_pam_payments_detail", lambda *a: [])

    result = exports.export_pam_excel_custom(_data(), _payments())
    wb = openpyxl.load_workbook(io.BytesIO(result))
    ws = wb["PAM NEW"]

    for row in [4, 5, 6, 7, 8]:
        assert ws[f"E{row}"].alignment.horizontal == "center", f"E{row} colon not center"
    for row in [19, 20, 21, 22]:
        assert ws[f"H{row}"].alignment.horizontal == "center", f"H{row} colon not center"
    for row in [25, 26, 27]:
        assert ws[f"H{row}"].alignment.horizontal == "center", f"H{row} colon not center"


def test_excel_pam_new_vendor_bank_wrap_text(monkeypatch):
    from app.modules.payment_memo import exports
    monkeypatch.setattr(exports, "get_pam_payments_detail", lambda *a: [])

    result = exports.export_pam_excel_custom(_data(), _payments())
    wb = openpyxl.load_workbook(io.BytesIO(result))
    ws = wb["PAM NEW"]

    assert ws["I19"].alignment.wrap_text is True, "I19 vendor name: wrap_text harus True"
    assert ws["I25"].alignment.wrap_text is True, "I25 bank account name: wrap_text harus True"
    assert ws["I26"].alignment.wrap_text is True, "I26 bank name: wrap_text harus True"
```

- [ ] **Step 2: Jalankan test — pastikan FAIL**

```
cd C:\Financehub
python -m pytest tests/test_print_memo_exports.py::test_excel_pam_new_colons_center_aligned tests/test_print_memo_exports.py::test_excel_pam_new_vendor_bank_wrap_text -v
```

Expected: `FAILED` — karena colons belum center-aligned dan belum ada wrap_text.

- [ ] **Step 3: Tambah `_WL` alignment di `export_pam_excel_custom`**

Buka `app/modules/payment_memo/exports.py`. Cari blok alignment constants di dalam `export_pam_excel_custom` (sekitar baris 1257):

```python
    _C    = Alignment(horizontal="center", vertical="center", wrap_text=True)
    _CN   = Alignment(horizontal="center", vertical="center", wrap_text=False)
    _L    = Alignment(horizontal="left",   vertical="center")
    _R    = Alignment(horizontal="right",  vertical="center")
```

Tambahkan `_WL` setelah `_L`:

```python
    _C    = Alignment(horizontal="center", vertical="center", wrap_text=True)
    _CN   = Alignment(horizontal="center", vertical="center", wrap_text=False)
    _L    = Alignment(horizontal="left",   vertical="center")
    _WL   = Alignment(horizontal="left",   vertical="center", wrap_text=True)
    _R    = Alignment(horizontal="right",  vertical="center")
```

- [ ] **Step 4: Center-align E4–E8 colons**

Cari 5 baris ini (sekitar baris 1296–1327):

```python
    _set("E4", ":")
```
```python
    _set("E5", ":")
```
```python
    _set("E6", ":")
```
```python
    _set("E7", ":")
```
```python
    _set("E8", ":")
```

Ganti masing-masing dengan:

```python
    _set("E4", ":", align=_C)
```
```python
    _set("E5", ":", align=_C)
```
```python
    _set("E6", ":", align=_C)
```
```python
    _set("E7", ":", align=_C)
```
```python
    _set("E8", ":", align=_C)
```

- [ ] **Step 5: Center-align H19–H22 colons (ubah dari _R ke _C)**

Cari 4 baris ini (sekitar baris 1366–1383):

```python
    _set("H19", ":",                                    align=_R)
```
```python
    _set("H20", ":",                                    align=_R)
```
```python
    _set("H21", ":",                                    align=_R)
```
```python
    _set("H22", ":",                                    align=_R)
```

Ganti masing-masing `align=_R` → `align=_C`:

```python
    _set("H19", ":",                                    align=_C)
```
```python
    _set("H20", ":",                                    align=_C)
```
```python
    _set("H21", ":",                                    align=_C)
```
```python
    _set("H22", ":",                                    align=_C)
```

- [ ] **Step 6: Center-align H25–H27 colons**

Cari 3 baris ini (sekitar baris 1391–1401):

```python
    _set("H25", ":")
```
```python
    _set("H26", ":")
```
```python
    _set("H27", ":")
```

Ganti masing-masing:

```python
    _set("H25", ":", align=_C)
```
```python
    _set("H26", ":", align=_C)
```
```python
    _set("H27", ":", align=_C)
```

- [ ] **Step 7: Tambah wrap_text ke I19, I25, I26**

Cari baris ini (sekitar baris 1367):

```python
    _set("I19", data.get("vendor_name", "Terlampir"),  align=_L)
```

Ganti dengan:

```python
    _set("I19", data.get("vendor_name", "Terlampir"),  align=_WL)
```

Cari baris ini (sekitar baris 1392):

```python
    _set("I25", data.get("bank_account_name", "Terlampir"), align=_L)
```

Ganti dengan:

```python
    _set("I25", data.get("bank_account_name", "Terlampir"), align=_WL)
```

Cari baris ini (sekitar baris 1397):

```python
    _set("I26", data.get("bank_name", "Terlampir"),   align=_L)
```

Ganti dengan:

```python
    _set("I26", data.get("bank_name", "Terlampir"),   align=_WL)
```

- [ ] **Step 8: Jalankan tests — pastikan PASS**

```
python -m pytest tests/test_print_memo_exports.py::test_excel_pam_new_colons_center_aligned tests/test_print_memo_exports.py::test_excel_pam_new_vendor_bank_wrap_text -v
```

Expected: `2 passed`

- [ ] **Step 9: Pastikan existing tests tidak rusak**

```
python -m pytest tests/ -v --tb=short
```

Expected: semua test pass.

- [ ] **Step 10: Commit**

```bash
git add app/modules/payment_memo/exports.py tests/test_print_memo_exports.py
git commit -m "feat: center-align colons and add wrap_text to vendor/bank cells in Excel PAM NEW"
```

---

### Task 4: Excel Rangkuman PAM — Rp Accounting Format (Area 5)

**Files:**
- Modify: `app/modules/payment_memo/exports.py` (dalam fungsi `export_pam_excel_custom`, seksi Rangkuman PAM ~baris 1426–1621)
- Modify: `tests/test_print_memo_exports.py` (tambah test baru di bagian bawah)

- [ ] **Step 1: Tulis failing test**

Tambahkan di bagian bawah `tests/test_print_memo_exports.py`:

```python
def test_rangkuman_rp_accounting_format(monkeypatch):
    """Amount cells di Rangkuman PAM harus pakai Rp Accounting number format."""
    from app.modules.payment_memo import exports
    monkeypatch.setattr(exports, "get_pam_payments_detail", lambda *a: [])

    result = exports.export_pam_excel_custom(_data(), _payments())
    wb = openpyxl.load_workbook(io.BytesIO(result))
    ws2 = wb["Rangkuman PAM"]

    # Data row 1 di row 8 (header di row 6-7), col 8 = amount
    assert ws2.cell(8, 8).number_format == _RP_FMT, "data row: bukan Rp Accounting format"
    # Total row di row 10 (2 data rows + total)
    assert ws2.cell(10, 8).number_format == _RP_FMT, "total row: bukan Rp Accounting format"
```

- [ ] **Step 2: Jalankan test — pastikan FAIL**

```
python -m pytest tests/test_print_memo_exports.py::test_rangkuman_rp_accounting_format -v
```

Expected: `FAILED` — karena saat ini format `'#,##0'`.

- [ ] **Step 3: Tambah konstanta `_RP_FMT` di seksi Rangkuman PAM**

Buka `app/modules/payment_memo/exports.py`. Cari komentar ini (sekitar baris 1426):

```python
    # ── Sheet 2: Rangkuman PAM (Book8 format) ─────────────────────────────────
    ws2 = wb.create_sheet("Rangkuman PAM")
```

Tambahkan `_RP_FMT` tepat setelah baris `ws2 = wb.create_sheet("Rangkuman PAM")`:

```python
    # ── Sheet 2: Rangkuman PAM (Book8 format) ─────────────────────────────────
    ws2 = wb.create_sheet("Rangkuman PAM")
    _RP_FMT = '_-"Rp"* #,##0_-;\\-"Rp"* #,##0_-;_-"Rp"* "-"_-;_-@_-'
```

- [ ] **Step 4: Ganti `'#,##0'` di `_write_data2`**

Cari baris ini di dalam nested function `_write_data2` (sekitar baris 1558):

```python
        ws2.cell(row, 8).number_format = '#,##0'
```

Ganti dengan:

```python
        ws2.cell(row, 8).number_format = _RP_FMT
```

- [ ] **Step 5: Ganti `'#,##0'` di `_write_tot2`**

Cari baris ini di dalam nested function `_write_tot2` (sekitar baris 1574):

```python
        ws2.cell(row, 8).number_format = '#,##0'
```

Ganti dengan:

```python
        ws2.cell(row, 8).number_format = _RP_FMT
```

- [ ] **Step 6: Ganti `'#,##0'` di Grand Total row**

Cari baris ini di blok grand total (sekitar baris 1621):

```python
        ws2.cell(_cur2, 8).number_format = '#,##0'
```

Ganti dengan:

```python
        ws2.cell(_cur2, 8).number_format = _RP_FMT
```

- [ ] **Step 7: Jalankan test — pastikan PASS**

```
python -m pytest tests/test_print_memo_exports.py::test_rangkuman_rp_accounting_format -v
```

Expected: `PASS`

- [ ] **Step 8: Jalankan seluruh tests**

```
python -m pytest tests/ -v --tb=short
```

Expected: semua pass.

- [ ] **Step 9: Commit**

```bash
git add app/modules/payment_memo/exports.py tests/test_print_memo_exports.py
git commit -m "feat: use Rp Accounting number format in Rangkuman PAM Excel sheet"
```

---

### Task 5: Excel Detail PAM — Rp Accounting Format (Area 6)

**Files:**
- Modify: `app/modules/payment_memo/exports.py` (fungsi `_build_detail_sheet`, baris 563)
- Modify: `tests/test_print_memo_exports.py` (tambah test baru)

- [ ] **Step 1: Tulis failing test**

Tambahkan di bagian bawah `tests/test_print_memo_exports.py`:

```python
def test_detail_sheet_rp_accounting_format():
    """Amount cells di Detail PAM sheet harus pakai Rp Accounting format."""
    import openpyxl as _xl
    from app.modules.payment_memo.exports import _build_detail_sheet

    wb = _xl.Workbook()
    ws = wb.active
    pam = {"pam_no": "PAM-TEST", "pam_date": "2026-06-15",
           "cost_center": "CC", "gl_account": "GL"}
    detail = [{
        "no": 1, "siswa_code": "S001", "nama": "Budi", "angkatan": "2020",
        "jenjang": "S1", "program": "Teknik", "universitas": "UI",
        "fakultas": "FT", "bank": "BNI", "norek": "111", "namarek": "Budi",
        "total_pembayaran": 3_000_000.0, "sisa_pendidikan": 0.0,
        "sisa_tunjangan": 0.0, "sisa_penelitian": 0.0,
        "rows": [{"keterangan": "By Pendidikan",
                  "pendidikan": 3_000_000.0, "tunjangan": 0.0, "penelitian": 0.0}],
    }]

    _build_detail_sheet(ws, pam, detail)

    # Data row dimulai row 7, col 14 = total_pembayaran
    assert ws.cell(7, 14).number_format == _RP_FMT, "total_pembayaran: bukan Rp Accounting"
    # Col 11 = pendidikan amount
    assert ws.cell(7, 11).number_format == _RP_FMT, "pendidikan: bukan Rp Accounting"
    # Grand total row 8, col 14
    assert ws.cell(8, 14).number_format == _RP_FMT, "grand total: bukan Rp Accounting"
```

- [ ] **Step 2: Jalankan test — pastikan FAIL**

```
python -m pytest tests/test_print_memo_exports.py::test_detail_sheet_rp_accounting_format -v
```

Expected: `FAILED` — karena `_nfmt = '#,##0'`.

- [ ] **Step 3: Ubah konstanta `_nfmt` di `_build_detail_sheet`**

Buka `app/modules/payment_memo/exports.py`. Cari baris ini di awal `_build_detail_sheet` (baris 563):

```python
    _nfmt = '#,##0'
```

Ganti dengan:

```python
    _nfmt = '_-"Rp"* #,##0_-;\\-"Rp"* #,##0_-;_-"Rp"* "-"_-;_-@_-'
```

*(Semua `_data(r, c, val, ha=..., fmt=_nfmt)` dan grand total row secara otomatis ikut format baru.)*

- [ ] **Step 4: Jalankan test — pastikan PASS**

```
python -m pytest tests/test_print_memo_exports.py::test_detail_sheet_rp_accounting_format -v
```

Expected: `PASS`

- [ ] **Step 5: Jalankan seluruh tests**

```
python -m pytest tests/ -v --tb=short
```

Expected: semua pass.

- [ ] **Step 6: Commit**

```bash
git add app/modules/payment_memo/exports.py tests/test_print_memo_exports.py
git commit -m "feat: use Rp Accounting number format in Detail PAM Excel sheet"
```

---

### Task 6: PDF Detail PAM — Kolom Jenjang Studi (Area 7)

**Files:**
- Modify: `app/modules/payment_memo/exports.py` (fungsi `_build_detail_pdf_table`, baris 255–316)
- Modify: `tests/test_print_memo_exports.py` (tambah test baru)

- [ ] **Step 1: Tulis failing test**

Tambahkan di bagian bawah `tests/test_print_memo_exports.py`:

```python
def test_pdf_detail_has_12_columns():
    """PDF Detail PAM table harus punya 12 kolom (tambah Jenjang Studi, sebelumnya 11)."""
    from app.modules.payment_memo.exports import _build_detail_pdf_table

    detail = [{
        "no": 1, "siswa_code": "S001", "nama": "Budi",
        "jenjang": "S2", "total_pembayaran": 5_000_000.0,
        "sisa_pendidikan": 0.0, "sisa_tunjangan": 0.0, "sisa_penelitian": 0.0,
        "norek": "111",
        "rows": [{"keterangan": "By Pendidikan",
                  "pendidikan": 5_000_000.0, "tunjangan": 0.0, "penelitian": 0.0}],
    }]

    table = _build_detail_pdf_table(detail)
    assert len(table._colWidths) == 12, f"Expected 12 cols, got {len(table._colWidths)}"

def test_pdf_detail_data_row_has_12_cells():
    """Setiap data row harus punya 12 cell (sama dengan jumlah kolom)."""
    from app.modules.payment_memo.exports import _build_detail_pdf_table

    detail = [{
        "no": 1, "siswa_code": "S001", "nama": "Budi",
        "jenjang": "S1", "total_pembayaran": 3_000_000.0,
        "sisa_pendidikan": 0.0, "sisa_tunjangan": 0.0, "sisa_penelitian": 0.0,
        "norek": "222",
        "rows": [{"keterangan": "By Pendidikan",
                  "pendidikan": 3_000_000.0, "tunjangan": 0.0, "penelitian": 0.0}],
    }]

    table = _build_detail_pdf_table(detail)
    # Row 0 = header, row 1 = first data row
    assert len(table._cellvalues[1]) == 12, f"Expected 12 cells in data row, got {len(table._cellvalues[1])}"
```

- [ ] **Step 2: Jalankan test — pastikan FAIL**

```
python -m pytest tests/test_print_memo_exports.py::test_pdf_detail_has_12_columns tests/test_print_memo_exports.py::test_pdf_detail_data_row_has_12_cells -v
```

Expected: `FAILED` — karena saat ini 11 kolom.

- [ ] **Step 3: Ubah `col_w` di `_build_detail_pdf_table`**

Buka `app/modules/payment_memo/exports.py`. Cari baris ini (sekitar baris 264):

```python
    col_w = [0.6*cm, 3.8*cm, 3.2*cm, 2.4*cm, 2.4*cm, 2.4*cm,
             2.5*cm, 3.0*cm, 1.8*cm, 1.8*cm, 1.8*cm]
```

Ganti dengan (kurangi Nama Siswa 3.8→3.0cm, tambah 1.5cm untuk jenjang di posisi 2):

```python
    col_w = [0.6*cm, 3.0*cm, 1.5*cm, 3.2*cm, 2.4*cm, 2.4*cm, 2.4*cm,
             2.5*cm, 3.0*cm, 1.8*cm, 1.8*cm, 1.8*cm]
```

- [ ] **Step 4: Tambah header "Jenjang Studi"**

Cari blok `hdrs` (sekitar baris 267):

```python
    hdrs = [_p(h, _s7h) for h in [
        "No", "Nama Siswa", "Keterangan",
        "By\nPend", "By\nTunj", "By\nRiset",
        "Total\nPbyran", "No. Rekening",
        "Sisa\nPend", "Sisa\nTunj", "Sisa\nRiset",
    ]]
```

Ganti dengan:

```python
    hdrs = [_p(h, _s7h) for h in [
        "No", "Nama Siswa", "Jenjang\nStudi", "Keterangan",
        "By\nPend", "By\nTunj", "By\nRiset",
        "Total\nPbyran", "No. Rekening",
        "Sisa\nPend", "Sisa\nTunj", "Sisa\nRiset",
    ]]
```

- [ ] **Step 5: Tambah sel jenjang di data row loop**

Cari blok ini di dalam loop `for siswa in detail:` (sekitar baris 281):

```python
            rows.append([
                _p(str(siswa["no"]) if first else "", _s7c),
                _p((siswa.get("nama") or siswa.get("siswa_code") or "") if first else "", _s7),
                _p(pr.get("keterangan") or "", _s7),
                _p(f"{pr['pendidikan']:,.0f}" if pr.get("pendidikan") else "", _s7r),
```

Tambahkan baris jenjang setelah Nama Siswa:

```python
            rows.append([
                _p(str(siswa["no"]) if first else "", _s7c),
                _p((siswa.get("nama") or siswa.get("siswa_code") or "") if first else "", _s7),
                _p((siswa.get("jenjang") or "") if first else "", _s7c),
                _p(pr.get("keterangan") or "", _s7),
                _p(f"{pr['pendidikan']:,.0f}" if pr.get("pendidikan") else "", _s7r),
```

- [ ] **Step 6: Update grand total row — tambah satu sel kosong**

Cari blok grand total row (sekitar baris 295):

```python
    rows.append([_p("", _s7)] * 6 + [
        _p(f"{grand_total:,.0f}",
           _style("gtv7", fontName="Helvetica-Bold", fontSize=7, alignment=2,
                  textColor=colors.HexColor("#1e293b"))),
    ] + [_p("", _s7)] * 4)
```

Ganti `* 6` dengan `* 7` (tambah 1 sel untuk kolom jenjang):

```python
    rows.append([_p("", _s7)] * 7 + [
        _p(f"{grand_total:,.0f}",
           _style("gtv7", fontName="Helvetica-Bold", fontSize=7, alignment=2,
                  textColor=colors.HexColor("#1e293b"))),
    ] + [_p("", _s7)] * 4)
```

- [ ] **Step 7: Update TableStyle ALIGN commands**

Cari blok `TableStyle` (sekitar baris 301):

```python
        ("ALIGN",         (0, 0), (0, -1),  "CENTER"),
        ("ALIGN",         (3, 0), (6, -1),  "RIGHT"),
        ("ALIGN",         (8, 0), (10, -1), "RIGHT"),
```

Ganti dengan (shift +1 untuk kolom setelah jenjang, tambah center untuk kolom jenjang di index 2):

```python
        ("ALIGN",         (0, 0), (0, -1),  "CENTER"),
        ("ALIGN",         (2, 0), (2, -1),  "CENTER"),
        ("ALIGN",         (4, 0), (7, -1),  "RIGHT"),
        ("ALIGN",         (9, 0), (11, -1), "RIGHT"),
```

- [ ] **Step 8: Jalankan tests — pastikan PASS**

```
python -m pytest tests/test_print_memo_exports.py::test_pdf_detail_has_12_columns tests/test_print_memo_exports.py::test_pdf_detail_data_row_has_12_cells -v
```

Expected: `2 passed`

- [ ] **Step 9: Jalankan seluruh test suite**

```
python -m pytest tests/ -v --tb=short
```

Expected: semua pass (target: 14+ tests pass, tidak ada yang baru gagal).

- [ ] **Step 10: Commit**

```bash
git add app/modules/payment_memo/exports.py tests/test_print_memo_exports.py
git commit -m "feat: add Jenjang Studi column to PDF Detail PAM table"
```

---

## Self-Review

**1. Spec coverage:**
- ✅ Area 1 (Bank details from data) → Task 1
- ✅ Area 2 (Jenjang column UI) → Task 2
- ✅ Area 3 (Colon center-aligned) → Task 3
- ✅ Area 4 (Wrap text vendor/bank) → Task 3
- ✅ Area 5 (Rangkuman Rp Accounting) → Task 4
- ✅ Area 6 (Detail Rp Accounting) → Task 5
- ✅ Area 7 (PDF Detail jenjang col) → Task 6

**2. Placeholder scan:** Tidak ada TBD atau TODO.

**3. Type consistency:**
- `_RP_FMT` di test file dan di `_build_detail_sheet` menggunakan string yang identik.
- `_WL` didefinisikan dan langsung digunakan di Task 3 (tidak ada referensi di task lain).
- `_nfmt` adalah variable lokal di `_build_detail_sheet` — tidak konflik dengan `_RP_FMT` di `export_pam_excel_custom`.
