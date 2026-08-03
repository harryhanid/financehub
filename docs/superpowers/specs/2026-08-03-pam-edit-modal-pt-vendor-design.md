# PAM Edit Modal — Add PT/Vendor Field — Design

## Problem

The "Edit" action on PAM rows (AGRI/APP/LAND/SETF tabs, and every other pillar
tab — they all share one modal) opens `modal-edit-pam`, which lets a user
edit No. PAM, Keterangan, Requestor Name, Total Amount, PAM Date, Due Date,
Tanggal Paid, and Notes — but has no field for **PT/Vendor** at all.

This isn't just a missing UI field: `service.py`'s `update_pam_and_application()`
whitelists exactly 6 columns it will write —

```python
_PAM_FIELDS = ("keterangan", "requestors_name", "total_amount", "due_date",
               "pam_date", "tanggal_bayar")
```

— `pt` (the column storing PT/Vendor) isn't in this list, so even if the
frontend sent it today, the backend would silently ignore it. `get_pam_detail()`
already returns `pt` (it does `SELECT * FROM pam_records`), so the data is
available — it's just never surfaced or accepted for editing.

## Decisions (confirmed with user)

Editing PT also updates Cost Center automatically, matching PAM-creation
behavior (the Input form's "CC" field is `readonly`, auto-filled from the
selected vendor) — Cost Center is never a manually-typed value anywhere else
in this app, and the edit modal keeps that invariant rather than introducing
a way for PT and Cost Center to drift out of sync.

## Design

### Reuse the existing vendor-autocomplete pattern, not a new widget

The Input form's "Perusahaan" field (`ipay-perusahaan-search`,
`index.html:4318-4345`) already does exactly this: search-as-you-type against
`VENDOR_LIST` (a `{name, cost_center, pillar}` array — sourced from
`get_vendors()`, rendered into the page at `index.html:1404`), select a hit,
which fills a hidden field with the vendor name and a readonly field with its
cost center. `_vendorSuggRender(hits, suggEl, onSelect)` (`index.html:4294-4309`)
is the shared rendering helper already used by 2+ of these search widgets —
the new one in the edit modal is a 3rd caller, not a new implementation.

### Modal changes (`modal-edit-pam`, `index.html:1204-1255`)

Add a new field group (placed right after "No. PAM", before "Keterangan" —
PT is core identifying info for a PAM, same tier as No. PAM):

```html
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
```

The Cost Center display is read-only text, not an input — matching the Input
form's `ipay-cc` (readonly, "Auto dari vendor") and the confirmed decision
that Cost Center is never directly typed.

### JS changes (`index.html`)

New function `editPamPtSearch()`, mirroring `ipayPerusahaanSearch()` exactly
but writing into the edit-modal's own element ids and updating the Cost
Center *display* (not a form field):

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
```

`openEditPAM()` (`index.html:3701-3719`) gains, alongside its existing field
population:

```javascript
document.getElementById('edit-pam-pt-search').value = r.pt || '';
document.getElementById('edit-pam-pt').value = r.pt || '';
document.getElementById('edit-pam-cost-center').value = r.cost_center || '';
document.getElementById('edit-pam-cc-display').textContent = 'Cost Center: ' + (r.cost_center || '—');
```

`submitEditPAM()` (`index.html:3721-3745`) adds two keys to the `pam` object
in its payload:

```javascript
pt:           document.getElementById('edit-pam-pt').value.trim() || null,
cost_center:  document.getElementById('edit-pam-cost-center').value.trim() || null,
```

### Backend change (`service.py:1810-1811`)

```python
_PAM_FIELDS = ("keterangan", "requestors_name", "total_amount", "due_date",
               "pam_date", "tanggal_bayar", "pt", "cost_center")
```

No other change to `update_pam_and_application()` — it already loops
`_PAM_FIELDS` generically and builds the `UPDATE` from whichever keys are
present and non-`None` in `pam_data` (`service.py:1815-1817`), so adding these
two names to the tuple is sufficient; no new branching logic needed.

## Scope

Applies uniformly to every pillar tab (AGRI/APP/LAND/SETF, and SMT's PAM
List/Advance) — they all render rows via the shared `openEditPAM(pamId)` and
`modal-edit-pam`, so this is one change, not one per pillar.

## Testing

- Route test for `update_pam_and_application`/the `/payment-memo/pam/<id>/edit`
  endpoint: submit a payload with `pt` and `cost_center` set, assert both
  persist on the `pam_records` row.
- Route test confirming `get_pam_detail` already returns `pt`/`cost_center`
  (no change needed there, but worth a regression assertion since this spec
  now depends on it).
- Manual: open Edit on a PAM row in each of AGRI/APP/LAND/SETF, search and
  select a different vendor, confirm the Cost Center display updates to that
  vendor's cost center, save, reopen the same PAM and confirm both persisted.

## Out of Scope

- Adding a Cost Center *input* field — it stays derived-only, matching every
  other place Cost Center appears in this app.
- Any change to the Vendors tab, `list_vendors`/`add_vendor`/`update_vendor`,
  or the `vendors` table itself — this only consumes the existing `VENDOR_LIST`
  the Input form already uses.
- Any change to `_vendorSuggRender`, `_vendorPos`, or the other 2 existing
  callers of the vendor-autocomplete pattern.
