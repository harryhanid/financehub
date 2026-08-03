# Design: PAM Print Memo — Show Namarek (Bank Account Name) Instead of Nama

**Date:** 2026-08-03
**Module:** Finance Hub — Eka Tjipta Foundation / Payment Approval Memo (PAM) / Print Memo
**Status:** Approved

---

## Summary

In the Print Memo screen's "Rangkuman PAM" (PAM summary), the student's own name (`nama`) is shown instead of the bank account holder name (`namarek`) in two of the three places that display it. Investigation found the actual scope is narrower than initially assumed:

1. **On-screen "▶ Rangkuman PAM" preview** (`dmRenderLampiran()`, `templates/payment_memo/index.html:4247`) — **bug confirmed.** Builds its display value from `pb.nama` only; `pb.namarek` is available on the object (the backing API, `get_pam_payments()`, already selects `s.namarek`) but is never read.
2. **PDF export** (`export_pam_pdf_custom`, the function actually wired to the Print Memo screen's "↓ PDF" button via `POST /payment-memo/pam/<id>/export/pdf-custom`) — **already correct.** Uses `pb["namarek"]` (`exports.py:512`) via the shared `_group_payments_by_siswa()` helper, which already computes `namarek` with a `namarek → nama → siswa_code` fallback chain (`exports.py:436`).
3. **Excel export** (`export_pam_excel_custom`, wired to the "↓ Excel" button via `POST /payment-memo/pam/<id>/export/excel-custom`) — **bug confirmed.** Its own "Rangkuman PAM" sheet section calls `_group_payments_by_siswa()` too (so the correctly-computed `namarek` field exists on every row), but the two places that write the name column (`exports.py:1818` and `exports.py:1836`) read `_pb2["nama"]` instead of `_pb2["namarek"]` — despite the column header literally being labeled "NAMA REKENING" (two-row header "NAMA " / "REKENING", written a few lines above each call site).

(There is a separate, older `export_pam_excel`/`export_pam_pdf` pair of functions in the same file that already handle `namarek` correctly throughout — those are not wired to the Print Memo screen's buttons and are out of scope here; they're mentioned only because reading them is what confirmed the fallback convention this fix should match.)

## Decisions

| Question | Decision |
|---|---|
| Scope | Exactly 3 line-level fixes: 1 in `templates/payment_memo/index.html` (on-screen preview), 2 in `modules/payment_memo/exports.py` (Excel export) — same file/function for both Excel fixes |
| PDF export | No change — already correct, confirmed by reading `export_pam_pdf_custom` and its shared helper |
| Fallback behavior | Match the existing convention exactly: `namarek` → `nama` → `siswa_code`, already implemented correctly in `_group_payments_by_siswa()` (used by both the PDF export and the buggy Excel export) and in every other "Rangkuman PAM"-adjacent code path in this file |
| Column header text | Unchanged — "Nama Siswa" (on-screen table) and "NAMA REKENING" (Excel sheet) stay as-is; only the underlying value changes to match what the headers already promise |

---

## Architecture

### File changes

- **Modify:** `app/templates/payment_memo/index.html:4247` — `dmRenderLampiran()`'s `groupMap` construction.
- **Modify:** `app/modules/payment_memo/exports.py:1818` and `:1836` — `export_pam_excel_custom()`'s two `_write_data2(...)` call sites.

No backend route changes, no changes to `get_pam_payments()` or `_group_payments_by_siswa()` (both already return/compute the correct `namarek` field — the bug is purely in code that has the right data available and reads the wrong key).

### On-screen preview fix

In `dmRenderLampiran()`, find:

```javascript
groupMap[key] = { nama: pb.nama || pb.siswa_code || '', bank: pb.bank || '', norek: pb.norek || '', amount: 0 };
```

Change to:

```javascript
groupMap[key] = { nama: pb.namarek || pb.nama || pb.siswa_code || '', bank: pb.bank || '', norek: pb.norek || '', amount: 0 };
```

(The object's own `nama` property name is unchanged — only what's stored in it changes — so the render loop that reads `pb.nama` a few lines later needs no further edit.)

### Excel export fix

In `export_pam_excel_custom()`, both call sites change identically — `_pb2["nama"]` → `_pb2["namarek"]`:

```python
_write_data2(_cur2, _i2, _pb2["namarek"], _pb2["bank"], _pb2["norek"],
             _pb2["amount"], sz=12)
```
```python
_write_data2(_cur2, _i2, _pb2["namarek"], _pb2["bank"], _pb2["norek"],
             _pb2["amount"], sz=10)
```

`_pb2` in both loops is already an entry from `_group_payments_by_siswa(payments)`, which guarantees a `namarek` key is present with the correct fallback already applied — no new fallback logic needed at the call site.

---

## Testing

- **On-screen preview:** no JS test framework exists in this codebase — verify by tracing the code path (confirmed above) rather than an automated test; optionally a manual browser check if a preview session with non-production data is available (open a PAM in Print Memo, expand "Rangkuman PAM", confirm the name column shows the bank account name for a student whose `namarek` differs from their `nama`).
- **Excel export:** add a pytest test to `app/tests/test_pam_exports.py` (already covers `export_pam_excel_custom` — confirmed present in this file) that builds a synthetic PAM with a student whose `nama` and `namarek` differ, calls `export_pam_excel_custom`, reads the resulting workbook's "Rangkuman PAM" sheet with openpyxl, and asserts the name cell equals the `namarek` value, not `nama`.
- Full Python regression suite run once at the end — no other backend logic changes in this task.

## Out of Scope

- The older `export_pam_excel`/`export_pam_pdf` functions — already correct, not wired to the Print Memo screen, not touched.
- Any change to `get_pam_payments()`, `get_pam_payments_detail()`, or `_group_payments_by_siswa()` — all three already compute/return the correct data.
- The SMT/"Nama Karyawan" logic branch in `dmRenderLampiran()` (vendor/invoice-based, not siswa/namarek-based) — unrelated data model, not touched.
- Any UI/label wording changes — headers already correctly say "Nama Siswa" / "NAMA REKENING"; only the underlying value was wrong.
