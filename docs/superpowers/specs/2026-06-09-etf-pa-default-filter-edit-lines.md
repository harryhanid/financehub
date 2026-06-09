# Spec: ETF PA Default Filter + Edit Line Fields

**Date:** 2026-06-09
**Module:** `etf_payment_application`
**Status:** Approved

---

## Goal

1. **Default filter:** Halaman ETF PA (AGRI/APP/SML/SETF) menampilkan Open + On Process secara default. Complete disembunyikan kecuali user aktif memilih filter.
2. **Edit line fields:** Modal edit PA dapat mengedit field per-line siswa: Jenis Bayar, Semester, Tahun Ajaran, IPK Sblmnya, Jumlah (Rp).

---

## Feature 1 — Default Filter Open + On Process

### Route (`app/modules/etf_payment_application/routes.py`)

- `sf` default berubah dari `""` ke `"active"`
- Validasi: `sf not in ("open", "on_process", "complete", "active", "")` → reset ke `"active"`

```python
sf = request.args.get("sf", "active").lower()
if sf not in ("open", "on_process", "complete", "active", ""):
    sf = "active"
pa_rows = get_pa_flat(company_id, tab, sf)
```

### Service (`app/modules/etf_payment_application/service.py`)

`get_pa_flat()` diperluas untuk mendukung `status_filter == "active"`:

```python
if status_filter == "active":
    extra_where = " AND LOWER(p.status) IN ('open', 'on_process')"
elif status_filter:
    extra_where = " AND LOWER(p.status)=?"
    params.append(status_filter.lower())
```

### Template — Dropdown filter status (`app/templates/etf_payment_application/index.html`)

Dropdown `#f-status` diubah isinya:

```html
<option value="">Semua</option>
<option value="active">Open + On Process</option>
<option value="open">Open</option>
<option value="on_process">On Process</option>
<option value="complete">Complete</option>
```

Default `selected` logic: `{% if active_sf == 'active' %}selected{% endif %}` pada opsi "Open + On Process".

`statusFilterChanged()` tidak perlu diubah — sudah handle redirect URL dengan value apapun.

---

## Feature 2 — Edit Line Fields di Modal

### Template HTML changes (`app/templates/etf_payment_application/index.html`)

**1. Tambah `data-line-id` ke setiap `<tr>`:**

```html
<tr data-pa-id="{{ r.pa_id }}"
    data-line-id="{{ r.line_id }}"
    ...>
```

**2. Ubah tombol Edit — pass `line_id` juga:**

```html
<button ... onclick="openEditById({{ r.pa_id }}, {{ r.line_id }})">Edit</button>
```

**3. Tambah hidden input `edit-line-id` di modal:**

```html
<input type="hidden" id="edit-line-id">
```

**4. Tambah 5 field baru di `modal-edit-pa` (setelah grid tanggal):**

```html
<div style="display:grid; grid-template-columns:1fr 1fr; gap:.75rem; margin-top:.5rem">
  <div class="form-group">
    <label>Jenis Bayar</label>
    <select id="edit-jenis-bayar">
      <option value="">-- Pilih --</option>
      {% for c in cat1 %}<option value="{{ c }}">{{ c }}</option>{% endfor %}
    </select>
  </div>
  <div class="form-group">
    <label>Semester</label>
    <select id="edit-semester">
      <option value="">-- Pilih --</option>
      {% for c in cat2_sem %}<option value="{{ c }}">{{ c }}</option>{% endfor %}
    </select>
  </div>
  <div class="form-group">
    <label>Tahun Ajaran</label>
    <input type="text" id="edit-tahun-ajaran" placeholder="2024/2025">
  </div>
  <div class="form-group">
    <label>IPK Sblmnya</label>
    <input type="number" id="edit-ipk" step="0.01" min="0" max="4">
  </div>
</div>
<div class="form-group">
  <label>Jumlah (Rp)</label>
  <input type="number" id="edit-jumlah" min="0">
</div>
```

### JavaScript changes (`app/templates/etf_payment_application/index.html`)

**`openEditById(paId, lineId)` — tambah parameter `lineId`:**

```javascript
async function openEditById(paId, lineId) {
  // ... existing header load via /header ...
  document.getElementById("edit-line-id").value = lineId || "";

  // Load line data
  const linesResp = await apiFetch(`/etf-payment-application/${paId}/lines?tab=${ACTIVE_TAB}`);
  if (linesResp) {
    const lines = await linesResp.json();
    const line = lines.find(l => l.id === lineId);
    if (line) {
      document.getElementById("edit-jenis-bayar").value  = line.jenis_pembayaran || "";
      document.getElementById("edit-semester").value     = line.semester || "";
      document.getElementById("edit-tahun-ajaran").value = line.tahun_ajaran || "";
      document.getElementById("edit-ipk").value          = line.ipk_sem_sebelumnya || "";
      document.getElementById("edit-jumlah").value       = line.jumlah_pembayaran || "";
    }
    // If line not found: line fields remain empty — modal still opens normally
  }
  openModal("modal-edit-pa");
}
```

**`saveEdit()` — tambah line fields ke payload:**

```javascript
const payload = {
  // ... existing header fields ...
  line_id:             parseInt(document.getElementById("edit-line-id").value) || null,
  jenis_pembayaran:    document.getElementById("edit-jenis-bayar").value,
  semester:            document.getElementById("edit-semester").value,
  tahun_ajaran:        document.getElementById("edit-tahun-ajaran").value,
  ipk_sem_sebelumnya:  parseFloat(document.getElementById("edit-ipk").value) || 0,
  jumlah_pembayaran:   parseFloat(document.getElementById("edit-jumlah").value) || 0,
};
```

### Service change (`app/modules/etf_payment_application/service.py`)

`update_pa()` — setelah update header, jika `data.get("line_id")` ada:

```python
line_id = data.get("line_id")
if line_id:
    conn.execute(
        f"""UPDATE {lines_tbl} SET
             jenis_pembayaran   = ?,
             semester           = ?,
             tahun_ajaran       = ?,
             ipk_sem_sebelumnya = ?,
             jumlah_pembayaran  = ?
            WHERE id=? AND pa_id=?""",
        (data.get("jenis_pembayaran", ""),
         data.get("semester", ""),
         data.get("tahun_ajaran", ""),
         data.get("ipk_sem_sebelumnya") or 0,
         data.get("jumlah_pembayaran") or 0,
         line_id, pa_id)
    )
```

`lines_tbl` diambil dari `_tbls(tab)` — sudah di-unpack di awal `update_pa()` (perlu update unpack dari `pa_tbl, _, _, pam_prefix` ke `pa_tbl, lines_tbl, _, pam_prefix`).

---

## Files Changed

| File | Perubahan |
|------|-----------|
| `app/modules/etf_payment_application/routes.py` | Default `sf="active"`, validasi tambah `"active"` |
| `app/modules/etf_payment_application/service.py` | `get_pa_flat` cabang "active"; `update_pa` update line jika `line_id` ada; unpack `lines_tbl` |
| `app/templates/etf_payment_application/index.html` | Dropdown filter; `data-line-id` di `<tr>`; tombol Edit; hidden input; 5 field baru di modal; update `openEditById` dan `saveEdit` |

---

## Out of Scope

- Tidak ada perubahan pada bulk update
- Tidak ada audit trail untuk line edits
- Tidak ada validasi uniqueness Tahun Ajaran / Semester
- Tab SETF mengikuti pola yang sama (kode sudah cover via `_tbls(tab)`)
