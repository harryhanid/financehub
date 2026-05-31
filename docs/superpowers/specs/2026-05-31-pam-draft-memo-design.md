# Design: PAM Draft Memo — Print-Ready Format (Book6.xlsx Standard)

**Date:** 2026-05-31
**Module:** Finance Hub ETF — Payment Approval Memo (PAM)
**Status:** Approved

---

## Summary

Add a **"Draft Memo" tab** to the Payment Memo page. The user selects a PAM No from a search dropdown, sees a live preview of the standard PAM document (exact Book6.xlsx layout), edits the "Approved by" names if needed, then exports to **PDF** (2 pages) or **Excel** (2 sheets).

---

## UX Flow

```
User opens Payment Memo page
  └─► Clicks tab "Draft Memo" (tab 4)
        ├─► Types in PAM No search → dropdown shows matching PAM records
        ├─► Selects a PAM → form preview renders with data from pam_records
        ├─► (Optional) edits "Approved by" field(s)
        └─► Clicks ↓ PDF or ↓ Excel → file downloads
```

---

## UI Changes — `templates/payment_memo/index.html`

### New tab: "Draft Memo"

Added as tab 4 after "PAM Records". Contains:

1. **Selector bar**
   - Debounced text input — calls `GET /payment-memo/pam?search=<query>` (existing API)
   - Dropdown renders matching rows: `PAM No — PT — Rp total`
   - Selecting a row fetches `GET /payment-memo/pam/<id>/detail` and renders the form

2. **Approved by bar** (shown once a PAM is selected)
   - Two text inputs pre-filled from template vars `pam_approved_by_1`, `pam_approved_by_2`
   - Small note: "(dari config, bisa diubah)"
   - `↓ PDF` and `↓ Excel` buttons aligned right

3. **Form preview** (JS-rendered, read-only)
   Reproduces exact Book6.xlsx structure:

   | Section | Content |
   |---|---|
   | Title row | "PAYMENT APPROVAL MEMO" |
   | Field grid (2-col) | PAM No / Cost Center / Date / GL Account / Requestor's Name / SO SC / Department / Company |
   | Business Unit | Checkboxes: Upstream / Downstream / **Corporate ✓** (static) |
   | Type of Request | Checkboxes: Downpayment / **Invoice Payment – Non PO Invoice ✓** / Employee Advance (static) |
   | Invoice Information | Vendor Name: **Terlampir** / Invoice Amount: `total_amount` / Expected Due Date: `due_date` / Invoice No: "-" |
   | Vendor Bank Account | Bank Account Name / Bank Name / Bank Account Number: all **Terlampir** |
   | Signature block | Request by: `requestors_name` / Approved by: 2 names / Checked by (QA): blank |

4. **Footer note** — "Lampiran jadwal siswa: halaman 2 di PDF / sheet 2 di Excel"

---

## Backend — New Service Functions (`modules/payment_memo/service.py`)

### `get_pam_payments(pam_no: str, company_id: int) → list`

```python
SELECT pb.*, s.nama, s.bank, s.norek, s.namarek
FROM payment_beasiswa pb
LEFT JOIN siswa s ON s.company_id = pb.company_id AND s.code = pb.siswa_code
WHERE pb.pam = ? AND pb.company_id = ?
ORDER BY pb.id
```

Returns list of dicts for the student schedule (lampiran).

---

### `export_pam_pdf(pam_id, company_id, approved_by_1, approved_by_2) → bytes`

Generates a 2-page PDF via **ReportLab**.

**Page 1 — PAM Form**

Reproduces Book6.xlsx layout:
- Blue header row: "PAYMENT APPROVAL MEMO" (gold bottom border)
- Two-column field grid with labels + values from `pam_records`
- Section headers (gray background): "Business Unit", "Type of Request", "Invoice Information", "Vendor Bank Account Details"
- Checkbox rows: `[ ]` / `[V]` using Unicode or drawn rectangles
- Signature block: 2 columns (Request by / Approved by), then Checked by (QA) full-width

**Page 2 — Lampiran Jadwal Pembayaran**

- Header: "Lampiran — Jadwal Pembayaran Beasiswa" with PAM No + PT + Date subtitle
- Table columns: No / Nama Siswa / Bank / No. Rekening / Atas Nama / Kategori / Kode / Amount (Rp)
- Footer row: TOTAL
- Data from `get_pam_payments()`

---

### `export_pam_excel(pam_id, company_id, approved_by_1, approved_by_2) → bytes`

Generates a 2-sheet `.xlsx` via **openpyxl**.

**Sheet 1 "PAM"** — reproduces Book6.xlsx structure exactly:
- Merged cells matching original (A1:Q1, B2:Q2, etc.)
- Field values filled from `pam_records`
- "V" marker placed in correct cells for Business Unit (Corporate) and Type of Request (Non PO Invoice)
- "Terlampir" for vendor/bank fields
- Signature names filled in

**Sheet 2 "Lampiran"** — student schedule table:
- Same columns as PDF page 2
- Auto-width columns, header row styled blue+white
- Footer total row

---

## Backend — New Routes (`modules/payment_memo/routes.py`)

```
GET /payment-memo/pam/<int:pam_id>/export/pdf
    Query params: approved_by_1 (str), approved_by_2 (str)
    Auth: requester, verificator, releaser
    Returns: application/pdf download

GET /payment-memo/pam/<int:pam_id>/export/excel
    Query params: approved_by_1 (str), approved_by_2 (str)
    Auth: requester, verificator, releaser
    Returns: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet download
```

Both routes:
1. Validate `pam_id` belongs to `session["company_id"]`
2. Pass `approved_by_1/2` through to service (fallback to `config.PAM_APPROVED_BY_1/2` if blank)
3. Return `send_file(io.BytesIO(bytes), ...)` with appropriate MIME type and filename `PAM-{pam_no}.pdf/.xlsx`

---

## Config Changes (`config.py`)

```python
PAM_APPROVED_BY_1 = "Hong Tjhin"
PAM_APPROVED_BY_2 = "Tenti Kidjo"
```

These are passed to the `index.html` template via the existing `index()` route so JS can pre-fill the Approved by inputs.

---

## Data Mapping: `pam_records` → PAM Form Fields

| PAM Form Field | Source |
|---|---|
| PAM No. | `pam_no` |
| Date | `pam_date` (formatted DD MMM YYYY) |
| Requestor's Name | `requestors_name` |
| Department | static `"-"` |
| Company | `pt` |
| Cost Center | `cost_center` |
| GL Account | `gl_account` |
| SO / SC | static `""` |
| Business Unit | static: Corporate ✓ |
| Type of Request | static: Non PO Invoice ✓ |
| Vendor Name | static `"Terlampir"` |
| Invoice / Memo Number | static `"-"` |
| Invoice Amount | `total_amount` (formatted Rp X,XXX,XXX) |
| Expected Due Date | `due_date` (formatted DD MMM YYYY) |
| Bank Account Name/Number | static `"Terlampir"` |
| Approved by 1 | `approved_by_1` param (default config) |
| Approved by 2 | `approved_by_2` param (default config) |

---

## Files Changed

| File | Change |
|---|---|
| `config.py` | Add `PAM_APPROVED_BY_1`, `PAM_APPROVED_BY_2` |
| `modules/payment_memo/service.py` | Add `get_pam_payments()`, `export_pam_pdf()`, `export_pam_excel()` |
| `modules/payment_memo/routes.py` | Add 2 export routes; pass config defaults to template |
| `templates/payment_memo/index.html` | Add "Draft Memo" tab (HTML + JS) |

---

## Testing

- `get_pam_payments()` returns correct students for a PAM No
- `export_pam_pdf()` returns non-empty bytes with correct 2-page structure
- `export_pam_excel()` returns valid xlsx with 2 sheets, correct field values
- Approved by fallback: blank param → uses config default
- Route auth: all 3 roles can access export; 404 if pam_id not in company

---

## Out of Scope

- Saving "Approved by" overrides to DB — user edits them per-export only
- Email/send functionality
- PAM status change on export
