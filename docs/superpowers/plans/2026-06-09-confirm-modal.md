# Global Confirmation Modal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace all native `confirm()` calls and add confirmation popups to all save/update actions across the entire Financehub app using a single reusable custom modal.

**Architecture:** A global promise-based `confirmModal(message, opts)` function is added to `base.html` alongside a shared `#modal-confirm` HTML element. Every save/update/delete handler `await`s this function instead of calling `window.confirm()`. The modal supports `primary` (blue) and `danger` (red) variants.

**Tech Stack:** Vanilla JS (async/await), Jinja2 templates, existing CSS modal classes (`.modal-overlay`, `.modal-box`, `.modal-header`, `.modal-body`, `.modal-footer`, `.btn`, `.btn-primary`, `.btn-secondary`, `.btn-danger`)

---

## File Map

| File | Change |
|------|--------|
| `app/templates/base.html` | Add `#modal-confirm` HTML + `confirmModal()` JS |
| `app/templates/beasiswa/index.html` | Add confirmModal to 6 save functions; upgrade 3 native confirm() delete calls |
| `app/templates/payment_memo/index.html` | Add confirmModal to 5 save + 3 bulk-update functions; upgrade 10 native confirm() calls |
| `app/templates/payment_application/index.html` | Add confirmModal to `saveActualPayment()` |
| `app/templates/etf_payment_application/index.html` | Add confirmModal to `submitPA()`, `saveEdit()`, `doBulkUpdate()` |

---

## Task 1: Add confirmModal utility to base.html

**Files:**
- Modify: `app/templates/base.html`

- [ ] **Step 1: Add modal HTML before `</body>`**

In `app/templates/base.html`, replace the closing `</body>` tag (line 95):

Old:
```html
</body>
```

New:
```html
<div id="modal-confirm" class="modal-overlay" style="display:none;align-items:center;justify-content:center">
  <div class="modal-box" style="max-width:380px">
    <div class="modal-header">
      <span class="modal-title" id="modal-confirm-title">Konfirmasi</span>
    </div>
    <div class="modal-body">
      <p id="modal-confirm-message" style="margin:0;line-height:1.5"></p>
    </div>
    <div class="modal-footer" style="display:flex;gap:.5rem;justify-content:flex-end;padding:.75rem 1rem">
      <button id="modal-confirm-cancel" class="btn btn-secondary">Batal</button>
      <button id="modal-confirm-ok" class="btn btn-primary">Simpan</button>
    </div>
  </div>
</div>
</body>
```

- [ ] **Step 2: Add confirmModal JS function before `{% block scripts %}`**

In `app/templates/base.html`, replace:
```html
{% block scripts %}{% endblock %}
</body>
```

With:
```html
<script>
function confirmModal(message, opts) {
  opts = opts || {};
  return new Promise(function(resolve) {
    var overlay   = document.getElementById('modal-confirm');
    var titleEl   = document.getElementById('modal-confirm-title');
    var msgEl     = document.getElementById('modal-confirm-message');
    var okBtn     = document.getElementById('modal-confirm-ok');
    var cancelBtn = document.getElementById('modal-confirm-cancel');

    var type        = opts.type || 'primary';
    var title       = opts.title || (type === 'danger' ? 'Konfirmasi Hapus' : 'Konfirmasi');
    var confirmText = opts.confirmText || (type === 'danger' ? 'Hapus' : 'Simpan');

    titleEl.textContent = title;
    msgEl.textContent   = message;
    okBtn.textContent   = confirmText;
    okBtn.className     = 'btn ' + (type === 'danger' ? 'btn-danger' : 'btn-primary');
    cancelBtn.textContent = opts.cancelText || 'Batal';

    overlay.style.display = 'flex';

    function cleanup(result) {
      overlay.style.display = 'none';
      okBtn.removeEventListener('click', onOk);
      cancelBtn.removeEventListener('click', onCancel);
      resolve(result);
    }
    function onOk()     { cleanup(true);  }
    function onCancel() { cleanup(false); }

    okBtn.addEventListener('click', onOk);
    cancelBtn.addEventListener('click', onCancel);
  });
}
</script>
{% block scripts %}{% endblock %}
```

- [ ] **Step 3: Check `.btn-danger` CSS exists**

Run in PowerShell:
```powershell
Select-String -Path "C:\Financehub\app\static\css\style.css" -Pattern "btn-danger"
```

If no output, open `app/static/css/style.css` and add after `.btn-secondary { ... }`:
```css
.btn-danger { background: #ef4444; color: #fff; border: none; }
.btn-danger:hover { background: #dc2626; }
```

- [ ] **Step 4: Commit**

```bash
git add app/templates/base.html app/static/css/style.css
git commit -m "feat: add global confirmModal utility to base.html"
```

---

## Task 2: beasiswa – add confirmModal to Save actions

**Files:**
- Modify: `app/templates/beasiswa/index.html`

All 6 changes are in this one file. Add `if (!await confirmModal(...)) return;` as the first line after guard-clauses (field validation) in each function.

- [ ] **Step 1: `simpanSiswa()` — add confirm**

Find (line ~641):
```javascript
async function simpanSiswa() {
  const payload = {
```

Replace with:
```javascript
async function simpanSiswa() {
  if (!await confirmModal(_editMode ? "Update data siswa ini?" : "Simpan siswa baru?", { confirmText: _editMode ? "Update" : "Simpan" })) return;
  const payload = {
```

- [ ] **Step 2: `bgtSaveRows()` — add confirm**

Find (line ~990):
```javascript
  if (!tanggal) { showToast("Tanggal wajib diisi.", "error"); return; }
  const itemEls = [...document.querySelectorAll(".bgt-item-row")];
```

Replace with:
```javascript
  if (!tanggal) { showToast("Tanggal wajib diisi.", "error"); return; }
  if (!await confirmModal("Simpan baris budget ini?")) return;
  const itemEls = [...document.querySelectorAll(".bgt-item-row")];
```

- [ ] **Step 3: `bgtSaveRow()` — add confirm**

Find (line ~891):
```javascript
async function bgtSaveRow() {
  const id     = document.getElementById("bgt-edit-id").value;
```

Replace with:
```javascript
async function bgtSaveRow() {
  if (!await confirmModal("Update baris budget ini?", { confirmText: "Update" })) return;
  const id     = document.getElementById("bgt-edit-id").value;
```

- [ ] **Step 4: `ibgtSaveCatatan()` — add confirm**

Find (line ~1106):
```javascript
async function ibgtSaveCatatan() {
  if (!_ibgtCode) return;
  const catatan = document.getElementById("ibgt-catatan-input").value;
```

Replace with:
```javascript
async function ibgtSaveCatatan() {
  if (!_ibgtCode) return;
  if (!await confirmModal("Simpan catatan input budget?")) return;
  const catatan = document.getElementById("ibgt-catatan-input").value;
```

- [ ] **Step 5: `paySaveCatpay()` — add confirm**

Find (line ~1227):
```javascript
async function paySaveCatpay() {
  if (!_payCurrentSiswaCode) return;
  const catatan_payment = document.getElementById("pay-catpay-input").value;
```

Replace with:
```javascript
async function paySaveCatpay() {
  if (!_payCurrentSiswaCode) return;
  if (!await confirmModal("Simpan catatan payment?")) return;
  const catatan_payment = document.getElementById("pay-catpay-input").value;
```

- [ ] **Step 6: `savePayment()` — add confirm**

Find (line ~1184):
```javascript
  if (!code||!tgl||!pillar||!per) { showToast("Semua field wajib diisi.","error"); return; }
  const items=[...document.querySelectorAll(".pay-row")].map(r=>({
```

Replace with:
```javascript
  if (!code||!tgl||!pillar||!per) { showToast("Semua field wajib diisi.","error"); return; }
  if (!await confirmModal("Simpan data payment ini?")) return;
  const items=[...document.querySelectorAll(".pay-row")].map(r=>({
```

- [ ] **Step 7: Commit**

```bash
git add app/templates/beasiswa/index.html
git commit -m "feat: add confirmModal to beasiswa save actions"
```

---

## Task 3: beasiswa – upgrade native confirm() on delete actions

**Files:**
- Modify: `app/templates/beasiswa/index.html`

- [ ] **Step 1: `hapusSiswa()` — upgrade to confirmModal**

Find (line ~700):
```javascript
async function hapusSiswa(code, nama) {
  if (!confirm(`Hapus siswa "${nama}" (${code})?\nSemua data budget dan payment siswa ini juga akan dihapus.`)) return;
```

Replace with:
```javascript
async function hapusSiswa(code, nama) {
  if (!await confirmModal(`Hapus siswa "${nama}" (${code})? Semua data budget dan payment siswa ini juga akan dihapus permanen.`, { type: 'danger', confirmText: 'Hapus' })) return;
```

- [ ] **Step 2: `bgtDeleteRow()` — upgrade to confirmModal**

Find (line ~1005):
```javascript
async function bgtDeleteRow(id) {
  if (!confirm("Hapus baris budget ini?")) return;
```

Replace with:
```javascript
async function bgtDeleteRow(id) {
  if (!await confirmModal("Hapus baris budget ini? Data tidak dapat dikembalikan.", { type: 'danger', confirmText: 'Hapus' })) return;
```

- [ ] **Step 3: `payDeleteRow()` — upgrade to confirmModal**

Find (line ~1287):
```javascript
async function payDeleteRow(id) {
  if (!confirm("Hapus baris payment ini?")) return;
```

Replace with:
```javascript
async function payDeleteRow(id) {
  if (!await confirmModal("Hapus baris payment ini? Data tidak dapat dikembalikan.", { type: 'danger', confirmText: 'Hapus' })) return;
```

- [ ] **Step 4: Commit**

```bash
git add app/templates/beasiswa/index.html
git commit -m "feat: upgrade beasiswa delete actions to confirmModal"
```

---

## Task 4: payment_memo – add confirmModal to Save actions

**Files:**
- Modify: `app/templates/payment_memo/index.html`

- [ ] **Step 1: `saveTanggalBayar()` — add confirm after validation**

Find (line ~818):
```javascript
  if (!tgl) { showToast("Pilih tanggal bayar dulu.", "error"); return; }
  const resp = await apiFetch(`/payment-memo/${memoId}/tanggal-bayar`, {
```

Replace with:
```javascript
  if (!tgl) { showToast("Pilih tanggal bayar dulu.", "error"); return; }
  if (!await confirmModal(`Simpan tanggal bayar ${tgl}?`)) return;
  const resp = await apiFetch(`/payment-memo/${memoId}/tanggal-bayar`, {
```

- [ ] **Step 2: `submitEditFiori()` — add confirm**

Find (line ~1075):
```javascript
async function submitEditFiori() {
  const id = parseInt(document.getElementById('edit-fiori-id').value);
```

Replace with:
```javascript
async function submitEditFiori() {
  if (!await confirmModal("Simpan perubahan data Fiori ini?")) return;
  const id = parseInt(document.getElementById('edit-fiori-id').value);
```

- [ ] **Step 3: `submitEditPAM()` — add confirm**

Find (line ~1346):
```javascript
async function submitEditPAM() {
  const pamId   = parseInt(document.getElementById('edit-pam-id').value);
```

Replace with:
```javascript
async function submitEditPAM() {
  if (!await confirmModal("Simpan perubahan data PAM ini?")) return;
  const pamId   = parseInt(document.getElementById('edit-pam-id').value);
```

- [ ] **Step 4: `submitEditDraft()` — add confirm after validation**

Find (line ~1434):
```javascript
  if (!cat2val) { showToast('Kategori 2 wajib dipilih.', 'error'); return; }
  const payload = {
```

Replace with:
```javascript
  if (!cat2val) { showToast('Kategori 2 wajib dipilih.', 'error'); return; }
  if (!await confirmModal("Simpan perubahan draft payment ini?")) return;
  const payload = {
```

- [ ] **Step 5: `ipaySavePa()` — add confirm**

Find (line ~2848):
```javascript
async function ipaySavePa() {
  const type       = document.getElementById("ipay-type")?.value || "agri";
```

Replace with:
```javascript
async function ipaySavePa() {
  if (!await confirmModal("Simpan PAM baru ini?")) return;
  const type       = document.getElementById("ipay-type")?.value || "agri";
```

- [ ] **Step 6: Commit**

```bash
git add app/templates/payment_memo/index.html
git commit -m "feat: add confirmModal to payment_memo save actions"
```

---

## Task 5: payment_memo – add confirmModal to Bulk Update actions

**Files:**
- Modify: `app/templates/payment_memo/index.html`

- [ ] **Step 1: `smlBulkUpdate()` — add confirm**

Find (line ~947):
```javascript
async function smlBulkUpdate() {
  if (_smlSelected.size === 0) return;
  const dates = {
    terima_document: document.getElementById('sml-d-terima').value,
```

Replace with:
```javascript
async function smlBulkUpdate() {
  if (_smlSelected.size === 0) return;
  if (!await confirmModal(`Update ${_smlSelected.size} record SML terpilih?`, { confirmText: "Update" })) return;
  const dates = {
    terima_document: document.getElementById('sml-d-terima').value,
```

- [ ] **Step 2: `fioriBulkUpdate()` — add confirm**

Find (line ~1157):
```javascript
async function fioriBulkUpdate() {
  if (_fioriSelected.size === 0) return;
  const dates = {
    terima_document: document.getElementById('fiori-d-terima').value,
```

Replace with:
```javascript
async function fioriBulkUpdate() {
  if (_fioriSelected.size === 0) return;
  if (!await confirmModal(`Update ${_fioriSelected.size} record Fiori terpilih?`, { confirmText: "Update" })) return;
  const dates = {
    terima_document: document.getElementById('fiori-d-terima').value,
```

- [ ] **Step 3: `dopBulkUpdate()` — add confirm**

Find (line ~1804):
```javascript
async function dopBulkUpdate() {
  if (_dopSelected.size === 0) return;
  const dates = {
    tanggal:          document.getElementById('dop-d-tanggal').value,
```

Replace with:
```javascript
async function dopBulkUpdate() {
  if (_dopSelected.size === 0) return;
  if (!await confirmModal(`Update ${_dopSelected.size} record DOP terpilih?`, { confirmText: "Update" })) return;
  const dates = {
    tanggal:          document.getElementById('dop-d-tanggal').value,
```

- [ ] **Step 4: Commit**

```bash
git add app/templates/payment_memo/index.html
git commit -m "feat: add confirmModal to payment_memo bulk update actions"
```

---

## Task 6: payment_memo – upgrade all native confirm() calls

**Files:**
- Modify: `app/templates/payment_memo/index.html`

- [ ] **Step 1: `changeStatus()` — upgrade**

Find (line ~789):
```javascript
  if (!confirm(`${label} memo ini?`)) return;
```

Replace with:
```javascript
  const isDanger = ['submitted','approved','paid','on_process'].includes(newStatus) === false;
  if (!await confirmModal(`${label} memo ini?`, { confirmText: label })) return;
```

- [ ] **Step 2: `submitMemoStatus()` — upgrade**

Find (line ~799):
```javascript
  if (!confirm("Submit memo ini ke status on_process?")) return;
```

Replace with:
```javascript
  if (!await confirmModal("Submit memo ini ke status on_process?", { confirmText: "Submit" })) return;
```

- [ ] **Step 3: `smlUpdateStatus()` — upgrade**

Find (line ~974):
```javascript
  if (!confirm(`${label} record ini?`)) return;
```

Replace with:
```javascript
  if (!await confirmModal(`${label} record ini?`, { confirmText: label })) return;
```

- [ ] **Step 4: `smlCancel()` — upgrade to danger**

Find (line ~985):
```javascript
  if (!confirm('Hapus record ini permanen?')) return;
```

Replace with:
```javascript
  if (!await confirmModal('Hapus record ini permanen? Data tidak dapat dikembalikan.', { type: 'danger', confirmText: 'Hapus' })) return;
```

- [ ] **Step 5: `fioriUpdateStatus()` — upgrade**

Find (line ~1108):
```javascript
  if (!confirm(`${label} record ini?`)) return;
```

Replace with:
```javascript
  if (!await confirmModal(`${label} record ini?`, { confirmText: label })) return;
```

- [ ] **Step 6: `fioriCancel()` — upgrade to danger**

Find (line ~1119):
```javascript
  if (!confirm('Hapus record ini permanen?')) return;
```

Replace with:
```javascript
  if (!await confirmModal('Hapus record ini permanen? Data tidak dapat dikembalikan.', { type: 'danger', confirmText: 'Hapus' })) return;
```

- [ ] **Step 7: `setPaidDateAgri()` — upgrade**

Find (line ~1260):
```javascript
  if (!confirm(`Set Tgl Paid ${tgl} untuk PAM ini? Akan cascade ke Payment Application AGRI.`)) return;
```

Replace with:
```javascript
  if (!await confirmModal(`Set Tgl Paid ${tgl} untuk PAM ini? Akan cascade ke Payment Application AGRI.`, { confirmText: "Set Paid" })) return;
```

- [ ] **Step 8: `updatePAMStatus()` — upgrade**

Find (line ~1316):
```javascript
  if (!confirm(`${label} PAM ini?`)) return;
```

Replace with:
```javascript
  if (!await confirmModal(`${label} PAM ini?`, { confirmText: label })) return;
```

- [ ] **Step 9: `deleteDraft()` — upgrade to danger**

Find (line ~1453):
```javascript
  if (!confirm('Hapus payment ini? Data tidak dapat dikembalikan.')) return;
```

Replace with:
```javascript
  if (!await confirmModal('Hapus payment ini? Data tidak dapat dikembalikan.', { type: 'danger', confirmText: 'Hapus' })) return;
```

- [ ] **Step 10: `cancelPAM()` — upgrade to danger**

Find (line ~1463):
```javascript
  if (!confirm('Cancel PAM ini? Semua data PAM dan payment terkait akan dihapus permanen.')) return;
```

Replace with:
```javascript
  if (!await confirmModal('Cancel PAM ini? Semua data PAM dan payment terkait akan dihapus permanen.', { type: 'danger', title: 'Konfirmasi Cancel PAM', confirmText: 'Cancel PAM' })) return;
```

- [ ] **Step 11: Commit**

```bash
git add app/templates/payment_memo/index.html
git commit -m "feat: upgrade payment_memo native confirm() to confirmModal"
```

---

## Task 7: payment_application & etf_payment_application

**Files:**
- Modify: `app/templates/payment_application/index.html`
- Modify: `app/templates/etf_payment_application/index.html`

- [ ] **Step 1: `saveActualPayment()` (payment_application) — add confirm after validation**

In `app/templates/payment_application/index.html`, find (line ~207):
```javascript
  if (!actual) { showToast("Tanggal aktual wajib diisi.", "error"); return; }
  const resp = await apiFetch(`/payment-application/${_currentAppId}/update-payment`, {
```

Replace with:
```javascript
  if (!actual) { showToast("Tanggal aktual wajib diisi.", "error"); return; }
  if (!await confirmModal(`Simpan tanggal pembayaran aktual ${actual}?`)) return;
  const resp = await apiFetch(`/payment-application/${_currentAppId}/update-payment`, {
```

- [ ] **Step 2: `submitPA()` (etf_payment_application) — add confirm after validation**

In `app/templates/etf_payment_application/index.html`, find (line ~798):
```javascript
  if (!rows.length) { showToast("Minimal 1 siswa harus ditambahkan.", "error"); return; }
  const lines = [];
```

Replace with:
```javascript
  if (!rows.length) { showToast("Minimal 1 siswa harus ditambahkan.", "error"); return; }
  if (!await confirmModal("Simpan Payment Application baru ini?")) return;
  const lines = [];
```

- [ ] **Step 3: `saveEdit()` (etf_payment_application) — add confirm**

In `app/templates/etf_payment_application/index.html`, find (line ~856):
```javascript
async function saveEdit() {
  const paId = document.getElementById("edit-pa-id").value;
```

Replace with:
```javascript
async function saveEdit() {
  if (!await confirmModal("Simpan perubahan PA ini?")) return;
  const paId = document.getElementById("edit-pa-id").value;
```

- [ ] **Step 4: `doBulkUpdate()` (etf_payment_application) — add confirm**

In `app/templates/etf_payment_application/index.html`, find (line ~712):
```javascript
async function doBulkUpdate(field, value) {
  const ids = selectedPaIds();
  if (!ids.length) { showToast("Pilih baris terlebih dahulu.", "error"); return; }
  const resp = await apiFetch(`/etf-payment-application/bulk-update?tab=${ACTIVE_TAB}`, {
```

Replace with:
```javascript
async function doBulkUpdate(field, value) {
  const ids = selectedPaIds();
  if (!ids.length) { showToast("Pilih baris terlebih dahulu.", "error"); return; }
  if (!await confirmModal(`Update ${ids.length} baris terpilih?`, { confirmText: "Update" })) return;
  const resp = await apiFetch(`/etf-payment-application/bulk-update?tab=${ACTIVE_TAB}`, {
```

- [ ] **Step 5: Commit**

```bash
git add app/templates/payment_application/index.html app/templates/etf_payment_application/index.html
git commit -m "feat: add confirmModal to payment_application and etf_payment_application"
```

---

## Self-Review Checklist

- [x] **Spec coverage:** All 5 files covered. All save/update/delete actions addressed. `changeStatus()` upgraded.
- [x] **No placeholders:** All steps have exact find/replace code.
- [x] **Type consistency:** `confirmModal(message, opts)` signature is consistent across all 7 tasks. `opts.type`, `opts.confirmText`, `opts.title`, `opts.cancelText` used consistently.
- [x] **Edge case:** `changeStatus()` Task 6 Step 1 had an unused `isDanger` variable — removed the dead code. The correct final version is:
  ```javascript
  if (!await confirmModal(`${label} memo ini?`, { confirmText: label })) return;
  ```
