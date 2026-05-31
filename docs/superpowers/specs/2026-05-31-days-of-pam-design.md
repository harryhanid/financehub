# Days of PAM — Design Spec

**Date:** 2026-05-31
**Module:** FinanceHub / ETF / Payment Approval Memo
**Feature:** Tab baru "Days of PAM" dengan bulk date update

---

## Overview

Tab baru di halaman Payment Approval Memo yang menampilkan seluruh baris `payment_beasiswa` yang sudah memiliki PAM number. User dapat memfilter baris secara real-time (client-side) dan memperbarui field tanggal secara bulk untuk baris-baris yang dipilih.

---

## Data Model

### Sumber Data

Query JOIN antara `payment_beasiswa`, `siswa`, dan (implisit) `pam_records`:

```sql
SELECT pb.id,
       pb.siswa_code,
       s.nama,
       pb.pam         AS pam_no,
       pb.cat1,
       pb.cat2,
       pb.perusahaan,
       pb.pillar,
       pb.amount,
       pb.tanggal,
       pb.tgl_pengajuan,
       pb.tgl_receive,
       pb.tgl_pa,
       pb.tgl_final
FROM payment_beasiswa pb
LEFT JOIN siswa s
       ON s.company_id = pb.company_id AND s.code = pb.siswa_code
WHERE pb.company_id = ?
  AND pb.pam IS NOT NULL
  AND pb.pam != ''
ORDER BY pb.tanggal DESC
```

### Bulk Update Rules

- Target tabel: `payment_beasiswa`
- Hanya field tanggal yang tidak kosong/blank yang di-update (skip jika input kosong)
- Field yang dapat di-update secara bulk: `tanggal`, `tgl_pengajuan`, `tgl_receive`, `tgl_pa`, `tgl_final`
- Validasi: semua `id` yang dikirim harus milik `company_id` yang sama (server-side check)
- Format tanggal: `YYYY-MM-DD`

---

## Backend

### Fungsi Baru di `service.py`

#### `get_days_of_pam(company_id: int) -> list`

Menjalankan query JOIN di atas, mengembalikan list of dict. Dipanggil dari `routes.index()`.

#### `bulk_update_dates(ids: list[int], dates: dict, company_id: int) -> dict`

```python
# dates = {
#   "tanggal": "2026-05-31",    # atau "" jika tidak diisi
#   "tgl_pengajuan": "",
#   "tgl_receive": "2026-05-31",
#   ...
# }
```

- Build SET clause hanya dari key yang nilainya tidak kosong
- Gunakan `WHERE id IN (?) AND company_id = ?` untuk safety
- Return `{"ok": True, "updated": N}` atau `{"ok": False, "pesan": "..."}`

### Perubahan di `routes.py`

#### Extend `index()`

Tambahkan `days_of_pam = get_days_of_pam(session["company_id"])` dan pass ke template.

#### Route Baru

```
POST /payment-memo/days-of-pam/bulk-update
Content-Type: application/json
Body: { "ids": [1, 2, 3], "dates": { "tgl_receive": "2026-05-31", ... } }
Response: { "ok": true, "updated": 3 }
```

Decorator: `@jwt_html_required`, hanya role yang bisa akses payment memo.

---

## Frontend (`index.html`)

### Tab Button

Ditambahkan antara "PAM Records" dan "Draft Memo":

```html
<button class="tab-btn" data-tab="tab-days-of-pam">Days of PAM</button>
```

### Layout Tab Panel (`id="tab-days-of-pam"`)

```
┌─ Filter Bar ────────────────────────────────────────────────────────┐
│ [Siswa Code] [Nama Siswa] [PAM NO] [Cat1] [Cat2] [Perusahaan] [Pillar] [Bersihkan] │
└─────────────────────────────────────────────────────────────────────┘

┌─ Bulk Date Update Bar ──────────────────────────────────────────────┐
│ Tanggal [date▼] Pengajuan [date▼] Receive [date▼] PA [date▼] Final [date▼]  [Update Terpilih (N)] │
└─────────────────────────────────────────────────────────────────────┘

┌─ Tabel ─────────────────────────────────────────────────────────────┐
│ [☐] | Siswa Code | Nama Siswa | PAM NO | Cat1 | Cat2 | Perusahaan   │
│      | Pillar | Amount | Tanggal | Pengajuan | Receive | PA | Final  │
├─────────────────────────────────────────────────────────────────────┤
│ [☐] | ETF-001 | Nama ... | PAM-001-ETF-05-2026 | ...               │
└─────────────────────────────────────────────────────────────────────┘
  [☐ Select All Terfilter]   N baris dipilih | N total baris tampil
```

### JavaScript Behavior

| Aksi | Hasil |
|------|--------|
| Ketik di filter input | `filterDopTable()` — semua row di-filter, `dopSelected` set dikosongkan |
| Klik checkbox row | Toggle ID row masuk/keluar `dopSelected` Set |
| Klik "Select All Terfilter" | Add semua visible row ID ke `dopSelected` |
| Klik "Bersihkan Filter" | Reset semua filter input, tampilkan semua row, reset selection |
| Klik "Update Terpilih" | Kumpulkan `dopSelected` + nilai date inputs → POST AJAX |
| Response sukses | Toast "N baris berhasil diperbarui", reload data tabel |

### Filter Logic

- Filter berjalan pada kolom: siswa_code, nama, pam_no, cat1, cat2, perusahaan, pillar
- Semua filter digabung dengan AND (row tampil hanya jika semua filter cocok)
- Pencocokan case-insensitive `includes()`
- Date columns tidak difilter (hanya untuk bulk-update)

### Update Button Counter

Label tombol update menampilkan jumlah selection aktif: `Update Terpilih (3)`. Disable jika `dopSelected.size === 0`.

---

## Scope (Tidak Termasuk)

- Sorting kolom tabel (tidak diminta)
- Export/download hasil filter (tidak diminta)
- Filter by range tanggal (tidak diminta — date inputs adalah untuk update, bukan filter)
- Edit inline individual baris (tidak diminta)

---

## Files Modified

| File | Perubahan |
|------|-----------|
| `app/modules/payment_memo/service.py` | +`get_days_of_pam()`, +`bulk_update_dates()` |
| `app/modules/payment_memo/routes.py` | extend `index()`, +POST route `bulk-update` |
| `app/templates/payment_memo/index.html` | +tab button, +tab panel, +JS block |

Tidak ada file baru dibuat.
