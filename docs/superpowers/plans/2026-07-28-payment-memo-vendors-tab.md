# Vendors Tab in Payment Approval Memo — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a "Vendors" tab inside the existing Payment Approval Memo module so any logged-in user can search, add, and edit vendor records (the `vendors` table backing the "Perusahaan" field used throughout this module and Beasiswa) — no more editing the database directly to add a missing company.

**Architecture:** No new blueprint or module. Three new service functions in `modules/payment_memo/service.py`, three new routes in `modules/payment_memo/routes.py`, and one new tab (button + panel + JS) in `templates/payment_memo/index.html`, following the exact conventions already used by the PA Advance tab (`.filter-bar.collapsible`, `.pillar-table-wrap` table, `skeletonRows()`/`esc()`/`showToast()` JS helpers). `beasiswa/service.py`'s existing `get_vendors()` (used by the Input tab's vendor autocomplete) is untouched.

**Tech Stack:** Flask + Jinja2, vanilla JS, sqlite3, pytest + Flask test client. No new dependencies.

## Global Constraints

- Design spec: `docs/superpowers/specs/2026-07-28-payment-memo-vendors-tab-design.md` — every task below implements a section of it.
- No changes to the `vendors` table schema (`id`, `name`, `pillar`, `cost_center` — already exists, already has ~600 seeded rows).
- No changes to `beasiswa/service.py`'s `get_vendors()` or the Input tab's vendor autocomplete.
- Pillar is a fixed dropdown with exactly 4 options: `AGRI`, `APP`, `LAND`, `SETF` — no blank/placeholder option in the add/edit form, no legacy values (`NON PILLAR`, `NON ALLOCATED`, `-`) offered.
- `name` must be non-empty and unique — both `add_vendor` and `update_vendor` must catch the DB's uniqueness violation and return `{"ok": False, "pesan": "Nama vendor sudah terdaftar."}` instead of raising/500ing.
- No admin gate — every route uses `@jwt_html_required` only, matching every other route already in `modules/payment_memo/routes.py`.
- Dev server (template/static auto-reload — `index.html` is a template, `app.js`/`style.css` are static and need a hard browser refresh):
  ```
  cd C:\Financehub\app && C:\Users\25010160\AppData\Local\Python\pythoncore-3.14-64\python.exe -m flask --app app:create_app run --port 5051 --debug
  ```
  Login credentials for manual verification: username `admin`, password `Admin@123` (first-run default per `README.md`) — if already changed on the target environment, ask the user for current credentials rather than guessing.
- This checkout may have substantial uncommitted WIP from another concurrent session in these same files. Before staging any commit: run `git status --porcelain` and confirm you're staging only the exact lines this task added — the earlier work in this same file (Sahabat ETF tab, dark-mode fix, LAND-pillar fix) hit this repeatedly; if a hunk contains unrelated pre-existing changes on the same line, stage via `git apply --cached` on a hand-extracted patch rather than `git add` the whole file, and document what got swept in.

---

### Task 1: Vendor service functions + tests

**Files:**
- Modify: `C:\Financehub\app\modules\payment_memo\service.py` (add `import sqlite3` near the top; append 3 functions at the end of the file, after `get_pam_beasiswa_lines` at line 2838)
- Test: `C:\Financehub\app\tests\test_pam_service.py` (append)

**Interfaces:**
- Produces: `list_vendors(search: str = "") -> list[dict]` (each dict: `id`, `name`, `pillar`, `cost_center`), `add_vendor(name: str, pillar: str, cost_center: str = "") -> dict` (`{"ok": bool, "pesan": str}`, plus `"id"` on success), `update_vendor(vendor_id: int, name: str, pillar: str, cost_center: str = "") -> dict` (`{"ok": bool, "pesan": str}`). Consumed by Task 2's routes.

- [ ] **Step 1: Write the failing tests**

Append to `C:\Financehub\app\tests\test_pam_service.py` (add `list_vendors, add_vendor, update_vendor` to the existing `from modules.payment_memo.service import (...)` block at the top of the file):

```python
def test_list_vendors_returns_seeded_rows():
    rows = list_vendors()
    assert len(rows) > 0
    assert all(set(r.keys()) >= {"id", "name", "pillar", "cost_center"} for r in rows)


def test_list_vendors_filters_by_search():
    all_rows = list_vendors()
    target = all_rows[0]["name"]
    rows = list_vendors(search=target[:5])
    assert any(r["name"] == target for r in rows)


def test_add_vendor_success():
    result = add_vendor("PT Vendor Baru Test", "LAND", "9999C1POFF")
    assert result["ok"] is True
    assert "id" in result
    rows = list_vendors(search="PT Vendor Baru Test")
    assert len(rows) == 1
    assert rows[0]["pillar"] == "LAND"
    assert rows[0]["cost_center"] == "9999C1POFF"


def test_add_vendor_duplicate_name_rejected():
    add_vendor("PT Duplikat Test", "AGRI", "")
    result = add_vendor("PT Duplikat Test", "APP", "")
    assert result["ok"] is False
    assert "sudah terdaftar" in result["pesan"]
    # confirm the second attempt did not overwrite the first
    rows = list_vendors(search="PT Duplikat Test")
    assert len(rows) == 1
    assert rows[0]["pillar"] == "AGRI"


def test_add_vendor_requires_name_and_pillar():
    assert add_vendor("", "AGRI", "")["ok"] is False
    assert add_vendor("PT Tanpa Pillar", "", "")["ok"] is False


def test_update_vendor_success():
    added = add_vendor("PT Update Test", "APP", "1111C1POFF")
    result = update_vendor(added["id"], "PT Update Test Renamed", "SETF", "2222C1POFF")
    assert result["ok"] is True
    rows = list_vendors(search="PT Update Test Renamed")
    assert len(rows) == 1
    assert rows[0]["pillar"] == "SETF"
    assert rows[0]["cost_center"] == "2222C1POFF"


def test_update_vendor_duplicate_name_rejected():
    a = add_vendor("PT Update A", "AGRI", "")
    add_vendor("PT Update B", "AGRI", "")
    result = update_vendor(a["id"], "PT Update B", "AGRI", "")
    assert result["ok"] is False
    assert "sudah terdaftar" in result["pesan"]


def test_update_vendor_same_name_noop_allowed():
    added = add_vendor("PT Update Self", "AGRI", "")
    result = update_vendor(added["id"], "PT Update Self", "LAND", "changed-cc")
    assert result["ok"] is True
    rows = list_vendors(search="PT Update Self")
    assert rows[0]["pillar"] == "LAND"
    assert rows[0]["cost_center"] == "changed-cc"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd C:\Financehub\app && pytest tests/test_pam_service.py -v -k vendor`
Expected: FAIL with `ImportError` (the functions don't exist yet).

- [ ] **Step 3: Add `import sqlite3`**

In `C:\Financehub\app\modules\payment_memo\service.py`, at the top of the file (current imports are `re`, `calendar`, `config`, `datetime`, `get_conn`, `sync_pam_to_bank_setf`), add:

```python
import sqlite3
```

- [ ] **Step 4: Implement the three functions**

Append to the end of `C:\Financehub\app\modules\payment_memo\service.py` (after `get_pam_beasiswa_lines`, currently ending at line 2838):

```python


def list_vendors(search: str = "") -> list:
    conn = get_conn()
    if search:
        rows = conn.execute(
            "SELECT id, name, pillar, cost_center FROM vendors WHERE name LIKE ? ORDER BY name",
            (f"%{search}%",)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, name, pillar, cost_center FROM vendors ORDER BY name"
        ).fetchall()
    conn.close()
    return [{"id": r["id"], "name": r["name"], "pillar": r["pillar"], "cost_center": r["cost_center"] or ""} for r in rows]


def add_vendor(name: str, pillar: str, cost_center: str = "") -> dict:
    name = (name or "").strip()
    pillar = (pillar or "").strip()
    if not name:
        return {"ok": False, "pesan": "Nama vendor wajib diisi."}
    if not pillar:
        return {"ok": False, "pesan": "Pillar wajib dipilih."}
    conn = get_conn()
    try:
        cur = conn.execute(
            "INSERT INTO vendors (name, pillar, cost_center) VALUES (?, ?, ?)",
            (name, pillar, (cost_center or "").strip())
        )
        conn.commit()
        return {"ok": True, "pesan": f"Vendor {name} berhasil ditambahkan.", "id": cur.lastrowid}
    except sqlite3.IntegrityError:
        conn.rollback()
        return {"ok": False, "pesan": "Nama vendor sudah terdaftar."}
    finally:
        conn.close()


def update_vendor(vendor_id: int, name: str, pillar: str, cost_center: str = "") -> dict:
    name = (name or "").strip()
    pillar = (pillar or "").strip()
    if not name:
        return {"ok": False, "pesan": "Nama vendor wajib diisi."}
    if not pillar:
        return {"ok": False, "pesan": "Pillar wajib dipilih."}
    conn = get_conn()
    try:
        conn.execute(
            "UPDATE vendors SET name = ?, pillar = ?, cost_center = ? WHERE id = ?",
            (name, pillar, (cost_center or "").strip(), vendor_id)
        )
        conn.commit()
        return {"ok": True, "pesan": f"Vendor {name} berhasil diperbarui."}
    except sqlite3.IntegrityError:
        conn.rollback()
        return {"ok": False, "pesan": "Nama vendor sudah terdaftar."}
    finally:
        conn.close()
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd C:\Financehub\app && pytest tests/test_pam_service.py -v -k vendor`
Expected: PASS (8 passed).

- [ ] **Step 6: Run the full service test file to check for regressions**

Run: `cd C:\Financehub\app && pytest tests/test_pam_service.py -v`
Expected: same pass count as before plus the 8 new tests, no failures.

- [ ] **Step 7: Commit**

```bash
cd C:\Financehub
git add app/modules/payment_memo/service.py app/tests/test_pam_service.py
git commit -m "feat: add vendor list/add/update service functions"
```

---

### Task 2: Vendor routes + tests

**Files:**
- Modify: `C:\Financehub\app\modules\payment_memo\routes.py:5-30` (import block), append 3 routes after line 781 (`open_pam_mark_lines_complete`, currently the last route in the file)
- Test: `C:\Financehub\app\tests\test_payment_memo_vendors.py` (new file)

**Interfaces:**
- Consumes: `list_vendors`, `add_vendor`, `update_vendor` from Task 1.
- Produces: `GET /payment-memo/vendors?search=`, `POST /payment-memo/vendors/add`, `POST /payment-memo/vendors/<int:vendor_id>/edit` — consumed by Task 3's JS.

- [ ] **Step 1: Write the failing tests**

Create `C:\Financehub\app\tests\test_payment_memo_vendors.py`:

```python
# tests/test_payment_memo_vendors.py

def login(client):
    return client.post("/auth/login", json={"username": "admin", "password": "Admin@123"})


def select_etf(client):
    client.post("/select-company", data={"company_id": "2"})


def test_vendors_list_requires_login(client):
    resp = client.get("/payment-memo/vendors")
    assert resp.status_code == 302


def test_vendors_list_returns_rows(client):
    login(client)
    select_etf(client)
    resp = client.get("/payment-memo/vendors")
    data = resp.get_json()
    assert data["ok"] is True
    assert len(data["rows"]) > 0
    assert "id" in data["rows"][0]


def test_vendors_list_search_filters(client):
    login(client)
    select_etf(client)
    add = client.post("/payment-memo/vendors/add", json={"name": "PT Route Search Test", "pillar": "AGRI", "cost_center": ""})
    assert add.get_json()["ok"] is True
    resp = client.get("/payment-memo/vendors?search=Route Search")
    data = resp.get_json()
    assert len(data["rows"]) == 1
    assert data["rows"][0]["name"] == "PT Route Search Test"


def test_vendors_add_success(client):
    login(client)
    select_etf(client)
    resp = client.post("/payment-memo/vendors/add", json={"name": "PT Route Add Test", "pillar": "LAND", "cost_center": "1234C1POFF"})
    data = resp.get_json()
    assert data["ok"] is True
    assert "id" in data


def test_vendors_add_duplicate_rejected(client):
    login(client)
    select_etf(client)
    client.post("/payment-memo/vendors/add", json={"name": "PT Route Dup Test", "pillar": "AGRI", "cost_center": ""})
    resp = client.post("/payment-memo/vendors/add", json={"name": "PT Route Dup Test", "pillar": "APP", "cost_center": ""})
    data = resp.get_json()
    assert data["ok"] is False
    assert "sudah terdaftar" in data["pesan"]


def test_vendors_edit_success(client):
    login(client)
    select_etf(client)
    added = client.post("/payment-memo/vendors/add", json={"name": "PT Route Edit Test", "pillar": "APP", "cost_center": ""}).get_json()
    resp = client.post(f"/payment-memo/vendors/{added['id']}/edit", json={"name": "PT Route Edit Test Renamed", "pillar": "SETF", "cost_center": "9999C1POFF"})
    data = resp.get_json()
    assert data["ok"] is True
    list_resp = client.get("/payment-memo/vendors?search=Route Edit Test Renamed")
    rows = list_resp.get_json()["rows"]
    assert len(rows) == 1
    assert rows[0]["pillar"] == "SETF"


def test_vendors_edit_duplicate_rejected(client):
    login(client)
    select_etf(client)
    a = client.post("/payment-memo/vendors/add", json={"name": "PT Route Edit A", "pillar": "AGRI", "cost_center": ""}).get_json()
    client.post("/payment-memo/vendors/add", json={"name": "PT Route Edit B", "pillar": "AGRI", "cost_center": ""})
    resp = client.post(f"/payment-memo/vendors/{a['id']}/edit", json={"name": "PT Route Edit B", "pillar": "AGRI", "cost_center": ""})
    data = resp.get_json()
    assert data["ok"] is False
    assert "sudah terdaftar" in data["pesan"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd C:\Financehub\app && pytest tests/test_payment_memo_vendors.py -v`
Expected: FAIL (404s — routes don't exist yet).

- [ ] **Step 3: Add the import and the three routes**

In `C:\Financehub\app\modules\payment_memo\routes.py`, leave the existing `from modules.payment_memo.service import (...)` block (lines 5-30) completely unmodified. Immediately after its closing `)` (i.e., directly after line 30, before the `from modules.payment_memo.exports import (...)` block that currently starts at line 31), insert a new, separate import line:

```python
from modules.payment_memo.service import list_vendors, add_vendor, update_vendor
```

Then append these 3 routes at the end of `C:\Financehub\app\modules\payment_memo\routes.py` (after `open_pam_mark_lines_complete`, currently ending at line 781):

```python


@bp.route("/vendors")
@jwt_html_required
def vendors_list():
    search = request.args.get("search", "").strip()
    return jsonify({"ok": True, "rows": list_vendors(search)})


@bp.route("/vendors/add", methods=["POST"])
@jwt_html_required
def vendors_add():
    data = request.get_json(force=True) or {}
    return jsonify(add_vendor(data.get("name", ""), data.get("pillar", ""), data.get("cost_center", "")))


@bp.route("/vendors/<int:vendor_id>/edit", methods=["POST"])
@jwt_html_required
def vendors_edit(vendor_id):
    data = request.get_json(force=True) or {}
    return jsonify(update_vendor(vendor_id, data.get("name", ""), data.get("pillar", ""), data.get("cost_center", "")))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd C:\Financehub\app && pytest tests/test_payment_memo_vendors.py -v`
Expected: PASS (8 passed).

- [ ] **Step 5: Run the full payment_memo test suite to check for regressions**

Run: `cd C:\Financehub\app && pytest tests/test_pam_service.py tests/test_payment_memo_ipay.py tests/test_payment_memo_vendors.py -v`
Expected: all passing, no new failures.

- [ ] **Step 6: Commit**

```bash
cd C:\Financehub
git add app/modules/payment_memo/routes.py app/tests/test_payment_memo_vendors.py
git commit -m "feat: add vendor list/add/edit routes to Payment Approval Memo"
```

---

### Task 3: Vendors tab UI

**Files:**
- Modify: `C:\Financehub\app\templates\payment_memo\index.html` (tab button in the `.tabs` bar, new tab-panel, new JS functions)

**Interfaces:**
- Consumes: `GET /payment-memo/vendors`, `POST /payment-memo/vendors/add`, `POST /payment-memo/vendors/<id>/edit` from Task 2. `esc()`, `showToast()`, `skeletonRows()`, `apiFetch()` (all already defined earlier in this same file).

This task has no automated test — this codebase has no JS test framework, and every other tab in this file was verified the same way (manual browser check). Steps 1-2 are the implementation; Step 3 is the manual verification the "test" would otherwise be.

- [ ] **Step 1: Add the tab button and panel**

In `C:\Financehub\app\templates\payment_memo\index.html`, find this line in the `.tabs` bar (currently line 167):

```html
      <button class="tab-btn" data-tab="tab-pa-advance" onclick="loadPaAdvance()">Advance</button>
```

and insert immediately after it:

```html
      <button class="tab-btn" data-tab="tab-vendors" onclick="loadVendors()">Vendors</button>
```

Then find the closing of the `tab-pa-advance` panel (currently lines 1093-1096):

```html
    </div>
  </div>

  <!-- Format Memo Tab -->
  <div class="tab-panel" id="tab-draft-memo">
```

and insert a new tab-panel between `tab-pa-advance`'s closing `</div>` and the `<!-- Format Memo Tab -->` comment:

```html
    </div>
  </div>

  <!-- Vendors Tab -->
  <div class="tab-panel" id="tab-vendors">
    <div id="pam-filter-vendors" class="filter-bar collapsible" style="align-items:center;gap:6px">
      <input id="vendors-search" type="text" placeholder="Cari nama vendor..."
             style="padding:4px 8px;border:1px solid #d1d5db;border-radius:5px;font-size:12px;width:220px;"
             oninput="loadVendorsDebounced()">
      <select id="vendors-filter-pillar" onchange="loadVendorsDebounced()"
              style="padding:4px 6px;border:1px solid #d1d5db;border-radius:5px;font-size:11px;width:100px">
        <option value="">Semua Pillar</option>
        <option value="AGRI">AGRI</option>
        <option value="APP">APP</option>
        <option value="LAND">LAND</option>
        <option value="SETF">SETF</option>
      </select>
      <span id="vendors-count" style="font-size:11px;color:var(--text-muted)"></span>
    </div>
    <div style="display:flex;align-items:end;gap:8px;margin-bottom:10px;flex-wrap:wrap">
      <div class="form-group" style="margin:0">
        <label style="font-size:.72rem;font-weight:600">Nama Vendor</label>
        <input id="vendors-add-name" type="text" placeholder="Nama perusahaan..." style="font-size:.82rem">
      </div>
      <div class="form-group" style="margin:0">
        <label style="font-size:.72rem;font-weight:600">Pillar</label>
        <select id="vendors-add-pillar" style="font-size:.82rem">
          <option value="AGRI">AGRI</option>
          <option value="APP">APP</option>
          <option value="LAND">LAND</option>
          <option value="SETF">SETF</option>
        </select>
      </div>
      <div class="form-group" style="margin:0">
        <label style="font-size:.72rem;font-weight:600">Cost Center</label>
        <input id="vendors-add-cc" type="text" placeholder="Opsional" style="font-size:.82rem">
      </div>
      <button class="btn btn-primary btn-sm" onclick="addVendor()">+ Tambah Vendor</button>
    </div>
    <div class="pillar-table-wrap">
      <table id="vendors-table" style="min-width:700px;border-collapse:collapse;font-size:12px;">
        <thead class="thead-primary">
          <tr>
            <th style="padding:7px 8px;">Nama</th>
            <th style="padding:7px 8px;white-space:nowrap">Pillar</th>
            <th style="padding:7px 8px;white-space:nowrap">Cost Center</th>
            <th style="padding:7px 8px;white-space:nowrap">Aksi</th>
          </tr>
        </thead>
        <tbody id="vendors-tbody">
          <tr><td colspan="4" style="text-align:center;padding:20px;color:var(--text-muted);">Memuat...</td></tr>
        </tbody>
      </table>
    </div>
  </div>

  <!-- Format Memo Tab -->
  <div class="tab-panel" id="tab-draft-memo">
```

- [ ] **Step 2: Add the JS functions**

Find `async function loadPaAdvance()` in the `<script>` block of this same file. Its final lines currently read:

```js
      <td style="padding:6px 8px">${r.status === 'paid'
        ? `<button class="btn btn-sm btn-primary" onclick="openRealizeModal(${r.id}, ${r.advance_amount})">Realisasi</button>`
        : '-'}</td>
    </tr>`).join('');
}

async function submitRealize(paymentId, realizedAmount, tglRealisasi) {
```

Insert the new functions between `loadPaAdvance()`'s closing `}` and `async function submitRealize(...)`:

```js

let _vendorsDebounce;
function loadVendorsDebounced() { clearTimeout(_vendorsDebounce); _vendorsDebounce = setTimeout(loadVendors, 300); }

async function loadVendors() {
  const search = (document.getElementById('vendors-search')?.value || '').trim();
  const pillar = (document.getElementById('vendors-filter-pillar')?.value || '');
  const tbody = document.getElementById('vendors-tbody');
  tbody.innerHTML = skeletonRows(4);
  const res = await apiFetch('/payment-memo/vendors?' + new URLSearchParams({ search }));
  if (!res) return;
  const data = await res.json();
  const count = document.getElementById('vendors-count');
  let rows = data.rows || [];
  if (pillar) rows = rows.filter(r => r.pillar === pillar);
  if (!rows.length) {
    tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;padding:20px;color:var(--text-muted);">Tidak ada vendor.</td></tr>';
    if (count) count.textContent = '';
    return;
  }
  if (count) count.textContent = rows.length + ' vendor';
  tbody.innerHTML = rows.map((r, i) => `
    <tr data-vendor-id="${r.id}" style="background:${i % 2 === 0 ? 'var(--card)' : 'var(--bg)'}">
      <td style="padding:6px 8px" class="vendors-cell-name">${esc(r.name)}</td>
      <td style="padding:6px 8px" class="vendors-cell-pillar">${esc(r.pillar)}</td>
      <td style="padding:6px 8px" class="vendors-cell-cc">${esc(r.cost_center || '-')}</td>
      <td style="padding:6px 8px"><button class="btn btn-secondary btn-sm" onclick="vendorsStartEdit(${r.id})">Edit</button></td>
    </tr>
  `).join('');
}

async function addVendor() {
  const name = document.getElementById('vendors-add-name').value.trim();
  const pillar = document.getElementById('vendors-add-pillar').value;
  const cost_center = document.getElementById('vendors-add-cc').value.trim();
  if (!name) { showToast('Nama vendor wajib diisi.', 'error'); return; }
  const res = await apiFetch('/payment-memo/vendors/add', { method: 'POST', body: JSON.stringify({ name, pillar, cost_center }) });
  if (!res) return;
  const data = await res.json();
  showToast(data.pesan, data.ok ? 'success' : 'error');
  if (data.ok) {
    document.getElementById('vendors-add-name').value = '';
    document.getElementById('vendors-add-cc').value = '';
    loadVendors();
  }
}

function vendorsStartEdit(vendorId) {
  const tr = document.querySelector(`#vendors-tbody tr[data-vendor-id="${vendorId}"]`);
  if (!tr) return;
  const nameCell = tr.querySelector('.vendors-cell-name');
  const pillarCell = tr.querySelector('.vendors-cell-pillar');
  const ccCell = tr.querySelector('.vendors-cell-cc');
  const actionCell = tr.lastElementChild;
  const currentName = nameCell.textContent;
  const currentPillar = pillarCell.textContent;
  const currentCc = ccCell.textContent === '-' ? '' : ccCell.textContent;
  nameCell.innerHTML = `<input type="text" value="${esc(currentName)}" style="width:100%;font-size:12px" class="vendors-edit-name">`;
  pillarCell.innerHTML = `<select style="font-size:12px" class="vendors-edit-pillar">` +
    ['AGRI', 'APP', 'LAND', 'SETF'].map(p => `<option value="${p}" ${p === currentPillar ? 'selected' : ''}>${p}</option>`).join('') +
    `</select>`;
  ccCell.innerHTML = `<input type="text" value="${esc(currentCc)}" style="width:100%;font-size:12px" class="vendors-edit-cc">`;
  actionCell.innerHTML = `<button class="btn btn-primary btn-sm" onclick="vendorsSaveEdit(${vendorId})">Simpan</button> <button class="btn btn-secondary btn-sm" onclick="loadVendors()">Batal</button>`;
}

async function vendorsSaveEdit(vendorId) {
  const tr = document.querySelector(`#vendors-tbody tr[data-vendor-id="${vendorId}"]`);
  if (!tr) return;
  const name = tr.querySelector('.vendors-edit-name').value.trim();
  const pillar = tr.querySelector('.vendors-edit-pillar').value;
  const cost_center = tr.querySelector('.vendors-edit-cc').value.trim();
  const res = await apiFetch(`/payment-memo/vendors/${vendorId}/edit`, { method: 'POST', body: JSON.stringify({ name, pillar, cost_center }) });
  if (!res) return;
  const data = await res.json();
  showToast(data.pesan, data.ok ? 'success' : 'error');
  if (data.ok) loadVendors();
}
```

- [ ] **Step 3: Manual verification**

Start the dev server (see Global Constraints), log in, go to `/payment-memo/` (or press Alt+→ repeatedly from any tab until reaching it), click the "Vendors" tab (or press `F` after clicking it to confirm the search box auto-focuses, per the earlier auto-focus fix).

Confirm:
1. The table loads with the existing ~600 seeded vendors, sorted by name.
2. Type a partial vendor name in the search box — the list filters to matching rows.
3. Select a pillar in the filter dropdown — the list filters further to that pillar only.
4. Fill in the "add vendor" form with a new unique name (e.g. "PT Manual Test Vendor"), pillar `LAND`, leave cost center blank, click "+ Tambah Vendor" — confirm a success toast, the form clears, and the new row appears in the table without a page reload.
5. Try adding a vendor with the exact same name again — confirm an error toast ("Nama vendor sudah terdaftar.") and no duplicate row appears.
6. Click "Edit" on the row you just added — confirm the row's cells become an editable name input, pillar dropdown, and cost-center input, with "Simpan"/"Batal" buttons.
7. Change the cost center to some value and click "Simpan" — confirm a success toast and the row now shows the new cost center (reload the page to also confirm it persisted server-side, not just client-side).
8. Click "Edit" on a *different* existing row and try renaming it to the name of the vendor you added in step 4 — confirm an error toast and the row's original name is unchanged after clicking "Batal".
9. Switch to the "Input" tab, search "Perusahaan" for "PT Manual Test Vendor" (the vendor added in step 4) — confirm it appears in the autocomplete, proving `list_vendors()` (Vendors tab) and `get_vendors()` (Input tab autocomplete) read the same table and stay in sync with no extra wiring.
10. Toggle dark mode — confirm the Vendors table's row striping is theme-aware (uses `var(--card)`/`var(--bg)`, matching the fix already applied to every other pillar table in this file).

- [ ] **Step 4: Commit**

```bash
cd C:\Financehub
git add app/templates/payment_memo/index.html
git commit -m "feat: add Vendors tab to Payment Approval Memo"
```

---

## Self-Review

**Spec coverage:**
- Where it lives (new tab, not separate module) → Task 3.
- Access control (no admin gate) → Task 2 (`@jwt_html_required` only, matching Global Constraints).
- 3 existing fields only, pillar dropdown restricted to AGRI/APP/LAND/SETF → Tasks 1-3 (backend accepts any string but the only UI path to call it, built in Task 3, only ever sends those 4 values; backend validation is presence-only, matching "no schema/enum enforcement needed since the UI is the only writer" — acceptable per YAGNI, the spec doesn't require server-side enum enforcement).
- Name uniqueness with friendly error → Task 1 (`sqlite3.IntegrityError` handling) + Task 2 (route tests) + Task 3 (manual verification steps 5 and 8).
- Edit support → Task 1 (`update_vendor`) + Task 2 (route) + Task 3 (inline edit UI).
- Search with inherited `F`-key auto-focus → Task 3 (uses the existing `.filter-bar.collapsible` convention, no new code needed for the auto-focus itself).
- `get_vendors()` untouched, both stay in sync → Task 3 Step 3's verification step 9 explicitly checks this.

**Placeholder scan:** No TBD/TODO; every step has complete, runnable code.

**Type/name consistency check:** `list_vendors()`'s dict shape (`id`, `name`, `pillar`, `cost_center`) is produced once in Task 1 and consumed identically by Task 2's route (`jsonify({"ok": True, "rows": list_vendors(search)})`) and Task 3's JS (`r.id`, `r.name`, `r.pillar`, `r.cost_center`). `add_vendor`/`update_vendor`'s `{"ok": bool, "pesan": str}` return shape is consistent across Task 1's tests, Task 2's routes and tests, and Task 3's `showToast(data.pesan, data.ok ? 'success' : 'error')` calls. Pillar dropdown's 4 option values (`AGRI`/`APP`/`LAND`/`SETF`) are identical across the add form, the edit-in-place `<select>`, and the filter dropdown in Task 3.
