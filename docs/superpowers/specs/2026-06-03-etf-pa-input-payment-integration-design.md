# ETF PA → Input Payment Integration Design

**Date:** 2026-06-03  
**Status:** Approved

---

## Overview

Menyambungkan workflow ETF Payment Application (etf_pa) ke Input Payment Beasiswa. Saat user menambah baris di Input Payment, mereka dapat memilih siswa dan kategori dari PA yang berstatus `draft`. Data otomatis terisi dari PA, dan status PA berubah seiring proses berjalan.

---

## Status Lifecycle ETF PA

| Event | Status |
|---|---|
| PA dibuat dari menu ETF PA | `draft` |
| Row Input Payment yang mereferensi PA line di-submit | `on_process` |
| `tanggal_bayar` diisi di menu ETF PA | `complete` |

PA yang sudah `on_process` atau `complete` tidak bisa dipanggil lagi di Input Payment.

---

## Database Migration

Tambah 1 kolom di `payment_beasiswa`:

```sql
ALTER TABLE payment_beasiswa ADD COLUMN etf_pa_line_id INTEGER REFERENCES etf_pa_lines(id);
```

Kolom `tgl_pengajuan`, `tgl_receive`, `tgl_pa`, `tgl_final` sudah ada di logika `add_payment_multi` — pastikan juga terdefinisi di DDL `database.py`.

---

## API Endpoints Baru (ETF PA module)

### `GET /etf-pa/draft-siswa?q=<nama>`

Return list siswa yang memiliki minimal 1 PA line di mana PA `status = 'draft'`, untuk autocomplete di Input Payment.

Response:
```json
[
  {"id": 1, "code": "S2401001", "nama": "Andi Pratama", "jenjang": "S2", "universitas": "UI"}
]
```

### `GET /etf-pa/draft-lines?siswa_id=<id>`

Return semua PA lines milik siswa tersebut di mana PA `status = 'draft'`.

Response:
```json
[
  {
    "line_id": 5,
    "pa_id": 3,
    "pa_number": "PA/ETF/003/2026",
    "jenis_pembayaran": "By Pendidikan",
    "jumlah_pembayaran": 15000000,
    "tgl_surat_pengajuan": "2026-05-01",
    "doc_received_by_educ": "2026-05-05",
    "tgl_payment_application": "2026-05-10"
  }
]
```

---

## Perubahan UI — Input Payment Beasiswa (Add Row)

Saat mode ETF di tab Input Payment, baris baru memiliki behavior:

| Field | Sumber | Input |
|---|---|---|
| Nama Siswa | Autocomplete → hanya siswa dengan draft PA | User ketik |
| Kategori 1 | Dropdown dari `jenis_pembayaran` PA lines draft | User pilih |
| Amount | `jumlah_pembayaran` PA line terpilih | Auto-fill (read-only) |
| TGL PENGAJUAN | `tgl_surat_pengajuan` PA header | Auto-fill (read-only) |
| TGL RECEIVE | `doc_received_by_educ` PA header | Auto-fill (read-only) |
| TGL PA | `tgl_payment_application` PA header | Auto-fill (read-only) |
| Kategori 2 | — | Input manual |
| TGL FINAL | — | Input manual |
| `etf_pa_line_id` | Hidden field | Dikirim saat submit |

---

## Perubahan Backend

### `beasiswa/service.py` — `add_payment_multi`

Setelah semua rows di-insert, collect semua `etf_pa_line_id` yang tidak null. Untuk setiap PA unik yang ditemukan lewat line tersebut, jalankan:

```sql
UPDATE etf_pa SET status = 'on_process', updated_at = ? WHERE id = ? AND status = 'draft'
```

Hanya update jika status masih `draft` (guard idempoten).

### `etf_payment_application/service.py` — `update_pa`

Saat `tanggal_bayar` diisi (tidak kosong), force `status = 'complete'` terlepas dari value `status` yang dikirim:

```python
if data.get("tanggal_bayar"):
    new_status = "complete"
```

---

## Guard dan Validasi

- Endpoint `draft-siswa` dan `draft-lines` filter ketat `etf_pa.status = 'draft'`.
- Jika user submit baris dengan `etf_pa_line_id` yang PA-nya sudah bukan `draft`, return error: "PA ini sudah tidak berstatus draft."
- PA `on_process`/`complete` tidak muncul di autocomplete manapun.

---

## Files yang Diubah

| File | Perubahan |
|---|---|
| `app/database.py` | Tambah kolom `etf_pa_line_id` di DDL `payment_beasiswa`; tambah kolom tanggal yang kurang |
| `app/modules/etf_payment_application/service.py` | Tambah `get_draft_siswa()`, `get_draft_lines_for_siswa()`; ubah `update_pa` untuk auto-complete |
| `app/modules/etf_payment_application/routes.py` | Tambah route `/draft-siswa` dan `/draft-lines` |
| `app/modules/beasiswa/service.py` | Update `add_payment_multi` untuk terima `etf_pa_line_id` dan trigger status PA |
| `app/templates/beasiswa/index.html` | Update UI add-row Input Payment untuk ETF flow |
