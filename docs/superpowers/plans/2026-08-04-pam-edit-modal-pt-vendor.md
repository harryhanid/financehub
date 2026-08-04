# PAM Edit Modal PT/Vendor Field Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let users edit a PAM's PT/Vendor from the shared Edit modal (AGRI/APP/LAND/SETF and every other pillar tab), with Cost Center auto-updating from the selected vendor, matching how PT/Cost Center already work when a PAM is first created.

**Architecture:** Backend: add `pt`/`cost_center` to `update_pam_and_application()`'s existing field whitelist — no new logic, the function already applies whatever's in that tuple generically. Frontend: reuse the Input form's proven vendor-autocomplete pattern (`VENDOR_LIST` + `_vendorSuggRender`) as a 3rd caller, inside the shared edit modal.

**Tech Stack:** Flask/Python (backend), vanilla JS (frontend), pytest.

## Global Constraints

- Cost Center is derived-only in the edit modal — no input field for it, only a read-only display, auto-filled from whichever vendor is selected for PT. This matches the Input form's own `ipay-cc` (readonly, "Auto dari vendor").
- Only these files change: `app/modules/payment_memo/service.py`, `app/templates/payment_memo/index.html`, `app/tests/test_pam_service.py`.
- This is one shared modal (`modal-edit-pam`) used by every pillar tab — one change covers AGRI/APP/LAND/SETF/SMT, no per-pillar duplication.

---

### Task 1: Backend — accept `pt`/`cost_center` in the update whitelist

**Files:**
- Modify: `app/modules/payment_memo/service.py:1810-1811`
- Test: `app/tests/test_pam_service.py`

**Interfaces:**
- Consumes: `create_pam_record`, `update_pam_and_application` (both already exist, imported at the top of `test_pam_service.py`)

- [ ] **Step 1: Write the failing test**

Append to `app/tests/test_pam_service.py`:

```python
def test_update_pam_and_application_accepts_pt_and_cost_center():
    from modules.payment_memo.service import update_pam_and_application
    conn = get_conn()
    pam_no = create_pam_record(conn, COMPANY_ID, COMPANY_CODE, {
        "pam_date": "2026-07-08", "pt": "PT. ABC",
        "requestors_name": "Jany Turkanda", "keterangan": "pt-edit-test",
        "total_amount": 1_000_000, "pillar": "APP",
    })
    conn.commit()
    pam_id = conn.execute(
        "SELECT id FROM pam_records WHERE company_id=? AND pam_no=?",
        (COMPANY_ID, pam_no)
    ).fetchone()["id"]
    conn.close()

    result = update_pam_and_application(
        pam_id,
        {"pt": "PT. Kresna Duta Agroindo", "cost_center": "1101C1POFF"},
        {}, COMPANY_ID
    )
    assert result["ok"] is True

    conn = get_conn()
    row = conn.execute(
        "SELECT pt, cost_center FROM pam_records WHERE id=?", (pam_id,)
    ).fetchone()
    conn.close()
    assert row["pt"] == "PT. Kresna Duta Agroindo"
    assert row["cost_center"] == "1101C1POFF"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd C:\Financehub\app && python -m pytest tests/test_pam_service.py -v -k accepts_pt_and_cost_center`
Expected: FAIL — `row["pt"]` is still `"PT. ABC"` (the original value), since `pt`/`cost_center` aren't in `_PAM_FIELDS` yet and the update silently does nothing to them.

- [ ] **Step 3: Add `pt`/`cost_center` to the whitelist**

In `app/modules/payment_memo/service.py`, replace:

```python
    _PAM_FIELDS = ("keterangan", "requestors_name", "total_amount", "due_date",
                   "pam_date", "tanggal_bayar")
```

with:

```python
    _PAM_FIELDS = ("keterangan", "requestors_name", "total_amount", "due_date",
                   "pam_date", "tanggal_bayar", "pt", "cost_center")
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd C:\Financehub\app && python -m pytest tests/test_pam_service.py -v -k accepts_pt_and_cost_center`
Expected: PASS

- [ ] **Step 5: Run the full PAM service test suite**

Run: `cd C:\Financehub\app && python -m pytest tests/test_pam_service.py -v`
Expected: all PASS — confirms no regression to the other `update_pam_and_application` tests (comma-joined pam_no rejection, etc.).

- [ ] **Step 6: Commit**

```bash
cd C:\Financehub
git add app/modules/payment_memo/service.py app/tests/test_pam_service.py
git commit -m "feat: allow PT/Vendor and Cost Center to be edited on PAM records"
```

---

### Task 2: Frontend — PT/Vendor field in the Edit modal

**Files:**
- Modify: `app/templates/payment_memo/index.html:1204-1255` (modal), `:3701-3745` (`openEditPAM`/`submitEditPAM`)
- Test: `app/tests/test_payment_memo_ipay.py`

**Interfaces:**
- Consumes: `VENDOR_LIST` (`index.html:1404`), `_vendorSuggRender(hits, suggEl, onSelect)` (`index.html:4294-4309`), `_vendorPos(inputEl, suggEl)` (`index.html:4311-4316`) — all pre-existing, unmodified.
- Consumes: `pt`/`cost_center` acceptance in `update_pam_and_application` (Task 1).
- Produces: JS function `editPamPtSearch()`.

- [ ] **Step 1: Write the failing test**

Check `app/tests/test_payment_memo_ipay.py` for its `login`/company-selection helpers (same pattern as every other route test in this repo) and add:

```python
def test_pam_index_page_has_pt_vendor_edit_field(client):
    login(client)
    _select_etf(client)
    resp = client.get("/payment-memo/")
    assert resp.status_code == 200
    assert b'id="edit-pam-pt-search"' in resp.data
    assert b"editPamPtSearch" in resp.data
```

(If `login`/`_select_etf` aren't already defined in this file, copy them from `app/tests/test_sponsorship_routes.py` — same pattern used across this repo's test files.)

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd C:\Financehub\app && python -m pytest tests/test_payment_memo_ipay.py -v -k pt_vendor_edit_field`
Expected: FAIL — neither `edit-pam-pt-search` nor `editPamPtSearch` exist in the page yet.

- [ ] **Step 3: Add the PT/Vendor field to the modal**

In `app/templates/payment_memo/index.html`, replace:

```html
      <div class="form-group" style="grid-column:1/-1">
        <label>No. PAM</label>
        <input type="text" id="edit-pam-no" placeholder="Nomor PAM"
               style="font-family:monospace;font-weight:600;color:#1e40af">
        <p style="font-size:.7rem;color:#f59e0b;margin:.25rem 0 0">⚠️ Mengubah No. PAM akan mengupdate semua referensi terkait (payment beasiswa, ETF/APP/SML PA).</p>
      </div>
      <div class="form-group" style="grid-column:1/-1">
        <label>Keterangan</label>
        <input type="text" id="edit-pam-keterangan" placeholder="Keterangan PAM">
      </div>
```

with:

```html
      <div class="form-group" style="grid-column:1/-1">
        <label>No. PAM</label>
        <input type="text" id="edit-pam-no" placeholder="Nomor PAM"
               style="font-family:monospace;font-weight:600;color:#1e40af">
        <p style="font-size:.7rem;color:#f59e0b;margin:.25rem 0 0">⚠️ Mengubah No. PAM akan mengupdate semua referensi terkait (payment beasiswa, ETF/APP/SML PA).</p>
      </div>
      <div class="form-group" style="grid-column:1/-1;position:relative">
        <label>PT / Vendor</label>
        <input type="text" id="edit-pam-pt-search" placeholder="Cari perusahaan..." autocomplete="off"
               oninput="editPamPtSearch()"
               onblur="setTimeout(()=>document.getElementById('edit-pam-pt-sugg').style.display='none',200)">
        <input type="hidden" id="edit-pam-pt">
        <input type="hidden" id="edit-pam-cost-center">
        <div id="edit-pam-pt-sugg" style="display:none;position:fixed;z-index:9999;background:#fff;border:1px solid #93c5fd;border-radius:.375rem;max-height:260px;overflow-y:auto;box-shadow:0 6px 20px rgba(0,0,0,.15)"></div>
        <p id="edit-pam-cc-display" style="font-size:.7rem;color:var(--text-muted);margin:.25rem 0 0">Cost Center: —</p>
      </div>
      <div class="form-group" style="grid-column:1/-1">
        <label>Keterangan</label>
        <input type="text" id="edit-pam-keterangan" placeholder="Keterangan PAM">
      </div>
```

- [ ] **Step 4: Add `editPamPtSearch()` next to the other vendor-search functions**

In `app/templates/payment_memo/index.html`, replace:

```javascript
function iklaimVendorSearch() {
```

with:

```javascript
function editPamPtSearch() {
  const inp  = document.getElementById("edit-pam-pt-search");
  const sugg = document.getElementById("edit-pam-pt-sugg");
  const q    = inp.value.toLowerCase().trim();
  if (!q) { sugg.style.display = "none"; return; }
  const hits = VENDOR_LIST.filter(v => v.name.toLowerCase().includes(q)).slice(0, 15);
  if (!hits.length) { sugg.style.display = "none"; return; }
  _vendorSuggRender(hits, sugg, v => {
    document.getElementById("edit-pam-pt-search").value = v.name;
    document.getElementById("edit-pam-pt").value = v.name;
    document.getElementById("edit-pam-cost-center").value = v.cost_center || "";
    document.getElementById("edit-pam-cc-display").textContent = "Cost Center: " + (v.cost_center || "—");
    sugg.style.display = "none";
  });
  _vendorPos(inp, sugg); sugg.style.display = "block";
}

function iklaimVendorSearch() {
```

- [ ] **Step 5: Populate the field when the modal opens, and send it on save**

In `openEditPAM()`, replace:

```javascript
  document.getElementById('edit-pam-amount').value        = r.total_amount || 0;
  const app = r.payment_application || {};
```

with:

```javascript
  document.getElementById('edit-pam-amount').value        = r.total_amount || 0;
  document.getElementById('edit-pam-pt-search').value     = r.pt || '';
  document.getElementById('edit-pam-pt').value             = r.pt || '';
  document.getElementById('edit-pam-cost-center').value    = r.cost_center || '';
  document.getElementById('edit-pam-cc-display').textContent = 'Cost Center: ' + (r.cost_center || '—');
  const app = r.payment_application || {};
```

In `submitEditPAM()`, replace:

```javascript
      total_amount:    parseFloat(document.getElementById('edit-pam-amount').value) || 0,
      tanggal_bayar:   document.getElementById('edit-pam-tanggal-bayar').value || null,
    },
```

with:

```javascript
      total_amount:    parseFloat(document.getElementById('edit-pam-amount').value) || 0,
      tanggal_bayar:   document.getElementById('edit-pam-tanggal-bayar').value || null,
      pt:              document.getElementById('edit-pam-pt').value.trim() || null,
      cost_center:     document.getElementById('edit-pam-cost-center').value.trim() || null,
    },
```

- [ ] **Step 6: Run the test to verify it passes**

Run: `cd C:\Financehub\app && python -m pytest tests/test_payment_memo_ipay.py -v -k pt_vendor_edit_field`
Expected: PASS

- [ ] **Step 7: Run the full Input/PAM route test suite**

Run: `cd C:\Financehub\app && python -m pytest tests/test_payment_memo_ipay.py tests/test_pam_service.py -v`
Expected: all PASS.

- [ ] **Step 8: Manual check**

Open Payment Approval Memo for ETF, and for each of AGRI/APP/LAND/SETF: click Edit on a row, confirm the "PT / Vendor" field shows the PAM's current vendor. Type into it, confirm suggestions appear from the vendor list, click one, confirm "Cost Center: ..." updates to that vendor's cost center. Save, reopen the same PAM's Edit modal, confirm the new PT and Cost Center persisted. Repeat once for SMT's PAM List tab to confirm the shared modal works there too.

- [ ] **Step 9: Commit**

```bash
cd C:\Financehub
git add app/templates/payment_memo/index.html app/tests/test_payment_memo_ipay.py
git commit -m "feat: add PT/Vendor field to the shared PAM edit modal"
```

## Out of Scope

- A Cost Center input field — stays derived-only, per the design's confirmed decision.
- Any change to the Vendors tab or the `vendors` table.
- Any change to `_vendorSuggRender`/`_vendorPos` or their other 2 existing callers.
