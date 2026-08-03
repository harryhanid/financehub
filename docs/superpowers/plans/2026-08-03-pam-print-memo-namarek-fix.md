# PAM Print Memo Namarek Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Print Memo screen's on-screen "Rangkuman PAM" preview and its Excel export both show the bank account holder name (`namarek`) instead of the student's own name (`nama`), matching what their column headers already say and what the PDF export (already correct) does.

**Architecture:** Two isolated one-line-logic fixes in two different files/languages — a JS object-construction fix in the Print Memo template, and a dict-key fix at two call sites in the Excel export function. Neither touches the data layer (`get_pam_payments()`, `_group_payments_by_siswa()`), which already computes the correct `namarek` value with fallback.

**Tech Stack:** Flask + Jinja2 template with inline vanilla JS; Python + openpyxl for the Excel export.

**Spec:** `docs/superpowers/specs/2026-08-03-pam-print-memo-namarek-fix-design.md`

## Global Constraints

- Fallback chain everywhere in this fix: `namarek` → `nama` → `siswa_code` (or, at the Excel call sites, just `namarek` directly, since `_group_payments_by_siswa()` has already applied that exact fallback chain before this code ever sees the dict).
- No change to `get_pam_payments()`, `_group_payments_by_siswa()`, or any column header text — only the value read/displayed changes.
- No change to `export_pam_pdf_custom`, `export_pam_excel` (the older, unwired function), or `export_pam_pdf` — already correct or out of scope.

---

## Task 1: Fix on-screen "Rangkuman PAM" preview

**Files:**
- Modify: `app/templates/payment_memo/index.html:4247`

**Interfaces:**
- Consumes: `pb.namarek` — already present on every object in the `payments` array passed into `dmRenderLampiran()` (sourced from `get_pam_payments()`, which selects `s.namarek`; confirmed in the design spec's investigation).
- Produces: no other function's interface changes — `dmRenderLampiran()`'s return value (an HTML string) and its later `pb.nama` read (a few lines below, in the row-rendering loop) are unaffected because the object's key name (`nama`) doesn't change, only what's stored in it.

- [ ] **Step 1: Confirm current state before editing**

Run: `cd app && sed -n '4247p' templates/payment_memo/index.html`
Expected output:
```
      groupMap[key] = { nama: pb.nama || pb.siswa_code || '', bank: pb.bank || '', norek: pb.norek || '', amount: 0 };
```

- [ ] **Step 2: Fix the line**

Replace line 4247:

```javascript
    groupMap[key] = { nama: pb.nama || pb.siswa_code || '', bank: pb.bank || '', norek: pb.norek || '', amount: 0 };
```

with:

```javascript
    groupMap[key] = { nama: pb.namarek || pb.nama || pb.siswa_code || '', bank: pb.bank || '', norek: pb.norek || '', amount: 0 };
```

- [ ] **Step 3: App-boot sanity check**

Run:
```bash
cd app && python -c "
from app import create_app
app = create_app()
print('APP_BOOT_OK')
"
```
Expected: `APP_BOOT_OK` (this confirms the Jinja/Flask app still loads; the edit is inside a `<script>` block so this mainly guards against an accidental syntax break elsewhere in the file during the edit).

- [ ] **Step 4: Confirm the fix landed and the old buggy form is gone**

Run: `cd app && grep -n "nama: pb.namarek || pb.nama || pb.siswa_code" templates/payment_memo/index.html`
Expected: one match, at the line you just edited.

Run: `cd app && grep -n "nama: pb.nama || pb.siswa_code || ''" templates/payment_memo/index.html`
Expected: no output (the old, buggy line no longer exists anywhere in the file).

- [ ] **Step 5: Commit**

```bash
cd /c/Financehub
git add app/templates/payment_memo/index.html
git commit -m "fix: show namarek instead of nama in PAM Print Memo on-screen Rangkuman preview"
```

---

## Task 2: Fix Excel export ("Rangkuman PAM" sheet)

**Files:**
- Modify: `app/modules/payment_memo/exports.py:1818` and `:1836` (`export_pam_excel_custom`)
- Test: `app/tests/test_pam_exports.py`

**Interfaces:**
- Consumes: `_pb2["namarek"]` — already present on every dict yielded by `_group_payments_by_siswa(payments)` (confirmed: that helper always sets `"namarek": pb.get("namarek") or pb.get("nama") or pb.get("siswa_code", "")` on every grouped entry).
- Produces: no signature change to `export_pam_excel_custom(data: dict, payments: list) -> bytes` — only the value written into the "Rangkuman PAM" sheet's name column changes.

- [ ] **Step 1: Write the failing test**

Add to `app/tests/test_pam_exports.py`, after the existing `test_export_pam_excel_custom_approved_by_in_sheet` test:

```python
def test_export_pam_excel_custom_rangkuman_shows_namarek_not_nama():
    import openpyxl, io as _io
    payments = [
        {"siswa_code": "S002", "nama": "Budi Siswa", "bank": "BCA",
         "norek": "9876543210", "namarek": "Ibu Budi Rekening",
         "cat1": "General", "cat2": "Sem 1", "amount": 2000000},
    ]
    result = export_pam_excel_custom(_CUSTOM_DATA, payments)
    wb = openpyxl.load_workbook(_io.BytesIO(result))
    ws = wb["Rangkuman PAM"]
    values = [ws.cell(r, 4).value for r in range(1, 20)]
    assert "Ibu Budi Rekening" in values
    assert "Budi Siswa" not in values
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd app && python -m pytest tests/test_pam_exports.py -k rangkuman_shows_namarek -v`
Expected: FAIL — `assert "Budi Siswa" not in values` fails, because the sheet currently contains `"Budi Siswa"` (the bug) and not `"Ibu Budi Rekening"`.

- [ ] **Step 3: Fix both call sites in `export_pam_excel_custom`**

Find (line 1818):

```python
        _write_data2(_cur2, _i2, _pb2["nama"], _pb2["bank"], _pb2["norek"],
                     _pb2["amount"], sz=12)
```

Replace with:

```python
        _write_data2(_cur2, _i2, _pb2["namarek"], _pb2["bank"], _pb2["norek"],
                     _pb2["amount"], sz=12)
```

Find (line 1836):

```python
            _write_data2(_cur2, _i2, _pb2["nama"], _pb2["bank"], _pb2["norek"],
                         _pb2["amount"], sz=10)
```

Replace with:

```python
            _write_data2(_cur2, _i2, _pb2["namarek"], _pb2["bank"], _pb2["norek"],
                         _pb2["amount"], sz=10)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd app && python -m pytest tests/test_pam_exports.py -k rangkuman_shows_namarek -v`
Expected: PASS

- [ ] **Step 5: Run the full PAM exports test file to confirm no regressions**

Run: `cd app && python -m pytest tests/test_pam_exports.py -v`
Expected: all tests PASS, including the pre-existing `test_export_pam_excel_custom_returns_xlsx`, `test_export_pam_excel_custom_has_two_sheets`, `test_export_pam_excel_custom_pam_no_in_sheet`, `test_export_pam_excel_custom_approved_by_in_sheet` (none of these assert on the name column, so none should be affected by this change).

- [ ] **Step 6: Confirm no other `_pb2["nama"]` reads remain in this function**

Run: `cd app && grep -n '_pb2\["nama"\]' modules/payment_memo/exports.py`
Expected: no output (both call sites now read `_pb2["namarek"]`; the earlier `_check` line at `exports.py:1289` reads `_pb2.get("namarek")`/`.get("nama")` for university-keyword detection, which is a different, unrelated read — not a `_pb2["nama"]` reference in the exact form searched here).

- [ ] **Step 7: Commit**

```bash
cd /c/Financehub
git add app/modules/payment_memo/exports.py app/tests/test_pam_exports.py
git commit -m "fix: show namarek instead of nama in PAM Print Memo Excel export's Rangkuman sheet"
```

---

## Task 3: Final verification

**Files:**
- None modified (verification only)

**Interfaces:**
- Consumes: everything from Tasks 1-2

- [ ] **Step 1: Full payment_memo test suite**

Run: `cd app && python -m pytest tests/test_pam_exports.py tests/test_memo_api.py -v`
Expected: all tests pass (Task 2's fix only changes which dict key is read at 2 call sites already covered by Task 2's own test; Task 1 has no backend test surface).

- [ ] **Step 2: Manual browser check (if a preview session with non-production data is available)**

Open Print Memo, select a PAM with at least one student whose `namarek` differs from their `nama`. Expand "▶ Rangkuman PAM" and confirm the name column shows the bank account name. Click "↓ Excel", open the downloaded file's "Rangkuman PAM" sheet, and confirm the same. Click "↓ PDF" and confirm it already showed the bank account name (no change expected there). Skip this step if no preview/browser session with non-production data is available — do not block on it.
