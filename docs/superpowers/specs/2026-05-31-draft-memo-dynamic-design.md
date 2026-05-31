# Draft Memo — Dynamic Editing & Lampiran UI

**Date:** 2026-05-31
**Scope:** `C:\Financehub\app` — Payment Approval Memo module, Draft Memo tab
**Status:** Approved for implementation

---

## Problem

The Draft Memo tab renders a read-only HTML preview of the PAM form. Only "Approved By 1 & 2" are editable. PDF and Excel exports read directly from the database, so any visual adjustments are impossible. The Lampiran (attachment) section exists in PDF/Excel but has no frontend representation.

---

## Goals

1. All fields in the Draft Memo form are editable inline in the browser.
2. Fields are auto-populated from the database when a PAM is selected.
3. PDF and Excel exports reflect whatever the user has edited (not fresh DB values).
4. A collapsible Lampiran section shows the payment schedule table (read-only).

---

## Non-Goals

- Persisting edits to the database — edits are ephemeral (for export only).
- Editing the Lampiran table — it is informational, data comes from DB.
- Changing the existing GET export routes used by the PAM Records tab.

---

## Architecture

### Data Flow

```
Select PAM → GET /pam/{id}/detail (DB) → dmRenderForm(p)
                                           └─ pre-fills all <input> values
                                           └─ sets checkbox checked state

User edits fields / toggles checkboxes in-browser

Click PDF/Excel → collectDmFields() → POST /pam/{id}/export/pdf-custom
                                        body: { pam_no, pam_date, requestors_name,
                                                department, cost_center, gl_account,
                                                so_sc, pt, bu_upstream, bu_downstream,
                                                bu_corporate, type_downpayment,
                                                type_invoice, type_advance,
                                                vendor_name, invoice_memo_no,
                                                total_amount, due_date,
                                                bank_account_name, bank_name,
                                                bank_account_no,
                                                approved_by_1, approved_by_2 }
                  → backend uses POST body (not DB) to generate file
                  → response blob → browser triggers download
```

### Files Changed

| File | Change |
|---|---|
| `app/templates/payment_memo/index.html` | Rewrite `dmRenderForm()`, `dmExportPDF()`, `dmExportExcel()`, add Lampiran section |
| `app/modules/payment_memo/exports.py` | Add `export_pam_pdf_custom(data, payments)` and `export_pam_excel_custom(data, payments)` |
| `app/modules/payment_memo/routes.py` | Add two POST routes: `pdf-custom` and `excel-custom` |

Existing GET export routes are **not changed**.

---

## Frontend Design

### Inline Input Styling

All editable fields rendered inside the memo table use:

```css
border: none;
background: transparent;
border-bottom: 1px dashed #94a3b8;
font-size: 11px;
font-family: Arial, sans-serif;
width: 100%;
padding: 1px 2px;
outline: none;
```

On `:focus`:
```css
border-bottom: 1.5px solid #3b82f6;
background: #eff6ff;
border-radius: 2px;
```

### Field Inventory

| Field | HTML element | Initial value source |
|---|---|---|
| PAM No | `<input type="text" id="dm-f-pam-no">` | `p.pam_no` |
| Date | `<input type="date" id="dm-f-date">` | `p.pam_date` |
| Requestor's Name | `<input type="text" id="dm-f-requestor">` | `p.requestors_name` |
| Department | `<input type="text" id="dm-f-dept">` | `"-"` |
| Cost Center | `<input type="text" id="dm-f-cc">` | `p.cost_center` |
| GL Account | `<input type="text" id="dm-f-gl">` | `p.gl_account` |
| SO / SC | `<input type="text" id="dm-f-sosc">` | `""` |
| Company | `<input type="text" id="dm-f-company">` | `p.pt` |
| BU Upstream | `<input type="checkbox" id="dm-f-bu-upstream">` | unchecked |
| BU Downstream | `<input type="checkbox" id="dm-f-bu-downstream">` | unchecked |
| BU Corporate | `<input type="checkbox" id="dm-f-bu-corporate">` | checked |
| Type: Downpayment | `<input type="checkbox" id="dm-f-type-dp">` | unchecked |
| Type: Invoice Payment | `<input type="checkbox" id="dm-f-type-inv">` | checked |
| Type: Employee Advance | `<input type="checkbox" id="dm-f-type-adv">` | unchecked |
| Vendor Name | `<input type="text" id="dm-f-vendor">` | `"Terlampir"` |
| Invoice / Memo No | `<input type="text" id="dm-f-inv-no">` | `"-"` |
| Invoice Amount | `<input type="number" id="dm-f-amount">` | `p.total_amount` |
| Expected Due Date | `<input type="date" id="dm-f-due">` | `p.due_date` |
| Bank Account Name | `<input type="text" id="dm-f-bank-name">` | `"Terlampir"` |
| Bank Name | `<input type="text" id="dm-f-bank">` | `"Terlampir"` |
| Bank Account Number | `<input type="text" id="dm-f-bank-no">` | `"Terlampir"` |
| Approved By 1 | `<input type="text" id="dm-f-ab1">` | `PAM_APPROVED_BY_1` |
| Approved By 2 | `<input type="text" id="dm-f-ab2">` | `PAM_APPROVED_BY_2` |

> The existing `#dm-ab1` / `#dm-ab2` inputs outside the form are removed; replaced by the inline ones above.

### collectDmFields()

```javascript
function collectDmFields() {
  return {
    pam_no:           document.getElementById('dm-f-pam-no').value,
    pam_date:         document.getElementById('dm-f-date').value,
    requestors_name:  document.getElementById('dm-f-requestor').value,
    department:       document.getElementById('dm-f-dept').value,
    cost_center:      document.getElementById('dm-f-cc').value,
    gl_account:       document.getElementById('dm-f-gl').value,
    so_sc:            document.getElementById('dm-f-sosc').value,
    pt:               document.getElementById('dm-f-company').value,
    bu_upstream:      document.getElementById('dm-f-bu-upstream').checked,
    bu_downstream:    document.getElementById('dm-f-bu-downstream').checked,
    bu_corporate:     document.getElementById('dm-f-bu-corporate').checked,
    type_downpayment: document.getElementById('dm-f-type-dp').checked,
    type_invoice:     document.getElementById('dm-f-type-inv').checked,
    type_advance:     document.getElementById('dm-f-type-adv').checked,
    vendor_name:      document.getElementById('dm-f-vendor').value,
    invoice_memo_no:  document.getElementById('dm-f-inv-no').value,
    total_amount:     parseFloat(document.getElementById('dm-f-amount').value) || 0,
    due_date:         document.getElementById('dm-f-due').value,
    bank_account_name:document.getElementById('dm-f-bank-name').value,
    bank_name:        document.getElementById('dm-f-bank').value,
    bank_account_no:  document.getElementById('dm-f-bank-no').value,
    approved_by_1:    document.getElementById('dm-f-ab1').value,
    approved_by_2:    document.getElementById('dm-f-ab2').value,
  };
}
```

### Export Functions (POST → Blob)

```javascript
async function dmExportPDF() {
  if (!_dmPamId) { showToast('Pilih PAM No terlebih dahulu.', 'error'); return; }
  const payload = collectDmFields();
  const resp = await apiFetch(`/payment-memo/pam/${_dmPamId}/export/pdf-custom`, {
    method: 'POST', body: JSON.stringify(payload)
  });
  const blob = await resp.blob();
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `PAM_${payload.pam_no || _dmPamId}.pdf`;
  a.click();
  URL.revokeObjectURL(a.href);
}

async function dmExportExcel() {
  if (!_dmPamId) { showToast('Pilih PAM No terlebih dahulu.', 'error'); return; }
  const payload = collectDmFields();
  const resp = await apiFetch(`/payment-memo/pam/${_dmPamId}/export/excel-custom`, {
    method: 'POST', body: JSON.stringify(payload)
  });
  const blob = await resp.blob();
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `PAM_${payload.pam_no || _dmPamId}.xlsx`;
  a.click();
  URL.revokeObjectURL(a.href);
}
```

### Lampiran Section

Rendered below `dm-form-preview` after a PAM is selected:

```html
<div id="dm-lampiran-wrap" style="display:none; margin-top:12px; max-width:860px">
  <button id="dm-lampiran-toggle" onclick="toggleLampiran()"
    style="...dark-blue button style...">
    ▶ Lampiran — Jadwal Pembayaran
  </button>
  <div id="dm-lampiran-body" style="display:none; margin-top:8px">
    <!-- table rendered by dmRenderLampiran(payments) -->
  </div>
</div>
```

`dmRenderLampiran(payments)` outputs the same 8-column table as PDF/Excel Sheet 2:
No | Nama Siswa | Bank | No. Rekening | Atas Nama | Kategori | Kode | Amount (Rp)

`payments` data is fetched in `dmSelectPAM()`. The existing `GET /pam/{id}/detail` route will be **extended** to also return `payments` (list from `get_pam_payments(pam_no, company_id)`) in its JSON response alongside the PAM data. `dmSelectPAM()` stores this as `_dmPayments` and passes it to `dmRenderLampiran(_dmPayments)`. This avoids a second fetch.

---

## Backend Design

### New Routes (`routes.py`)

```python
@bp.route("/pam/<int:pam_id>/export/pdf-custom", methods=["POST"])
def export_pam_pdf_custom_route(pam_id):
    data = request.get_json()
    company_id = session["company_id"]
    pam_no = data.get("pam_no") or ""
    payments = get_pam_payments(pam_no, company_id)
    pdf_bytes = export_pam_pdf_custom(data, payments)
    fname = f"PAM_{pam_no}.pdf"
    return Response(pdf_bytes, mimetype="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{fname}"'})

@bp.route("/pam/<int:pam_id>/export/excel-custom", methods=["POST"])
def export_pam_excel_custom_route(pam_id):
    data = request.get_json()
    company_id = session["company_id"]
    pam_no = data.get("pam_no") or ""
    payments = get_pam_payments(pam_no, company_id)
    xlsx_bytes = export_pam_excel_custom(data, payments)
    fname = f"PAM_{pam_no}.xlsx"
    return Response(xlsx_bytes,
                    mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f'attachment; filename="{fname}"'})
```

### New Export Functions (`exports.py`)

`export_pam_pdf_custom(data: dict, payments: list) -> bytes`
- Identical structure to `export_pam_pdf()` but reads all field values from `data` dict instead of DB
- Checkboxes controlled by boolean keys: `data["bu_corporate"]`, `data["type_invoice"]`, etc.
- `_fmt_date()` handles both `"YYYY-MM-DD"` strings and empty strings

`export_pam_excel_custom(data: dict, payments: list) -> bytes`
- Identical structure to `export_pam_excel()` but reads from `data` dict
- Sheet 1 "PAM NEW": uses `data` values
- Sheet 2 "Lampiran": uses `payments` list (same as current)

The existing `export_pam_pdf()` and `export_pam_excel()` functions are **not modified** — shared helper logic can be extracted into private functions if there is significant duplication.

---

## Checklist

- [ ] `dmRenderForm()` rewrites all static text to inline `<input>` / checkbox elements
- [ ] Checkbox rendering uses actual `<input type="checkbox">` styled consistently
- [ ] `collectDmFields()` gathers all 24 field values
- [ ] `dmExportPDF()` / `dmExportExcel()` use POST + blob download
- [ ] Old `_dmExportUrl()` function removed
- [ ] `#dm-approved-bar` (old approved-by inputs outside form) removed from HTML
- [ ] `export_pam_pdf_custom(data, payments)` added to `exports.py`
- [ ] `export_pam_excel_custom(data, payments)` added to `exports.py`
- [ ] Two POST routes added to `routes.py`
- [ ] Lampiran collapsible section rendered in `dmSelectPAM()`
- [ ] `get_pam_payments` called in the PDF/Excel custom routes
- [ ] `GET /pam/{id}/detail` route extended to include `payments` list in response
- [ ] Existing GET export routes untouched
