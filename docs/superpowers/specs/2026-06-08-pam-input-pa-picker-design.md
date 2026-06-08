# Design: PAM Input — PA Picker Sub-Row

**Date:** 2026-06-08  
**File affected:** `app/templates/payment_memo/index.html`

## Problem

Dalam tab Input Payment Memo (Beasiswa), kombinasi nama + Cat1 + Cat2 tidak selalu unik. Satu siswa bisa memiliki beberapa Payment Application (PA) dengan jenis_pembayaran dan semester yang sama tetapi amount berbeda. Saat ini sistem mengambil PA pertama yang ditemukan, yang bisa mengisi data yang salah.

## Solution

Setelah Cat2 dipilih, sistem menghitung jumlah PA yang cocok (student + cat1 + cat2):

- **1 PA match** → auto-fill amount dan dates langsung (behaviour saat ini)
- **2+ PA match** → tampilkan sub-row picker di bawah baris siswa

## Sub-Row Picker

- Berupa `<tr>` dengan `<td colspan="10">` yang berisi mini-table
- Mini-table menampilkan dua kolom: **No PA** | **Amount (Rp)**
- Setiap baris mewakili satu PA yang cocok
- User klik salah satu baris → `_ipayFillLine(tr, line)` dipanggil → sub-row hilang
- Jika user mengubah Cat1 atau Cat2 → sub-row lama dihapus dan dibuat ulang

## Data Source

Data sudah tersedia di `tr._allLines` (di-fetch saat siswa dipilih via `/etf-payment-application/draft-lines`). Kolom yang digunakan:
- `pa_number` — ditampilkan di kolom "No PA"
- `jumlah_pembayaran` — ditampilkan di kolom "Amount (Rp)"
- `line_id`, `tgl_surat_pengajuan`, `doc_received_by_educ`, `tgl_payment_application` — digunakan oleh `_ipayFillLine`

## Changes

### `app/templates/payment_memo/index.html`

1. **Tambah helper `_ipayBuildPickerRow(tr, candidates)`**
   - Input: `tr` (main row), `candidates` (array of matching lines)
   - Build dan return `<tr>` sub-row dengan mini-table
   - Setiap baris mini-table punya click handler: `_ipayFillLine(tr, line)` + `pickerRow.remove()`

2. **Ubah `cat2Drop._hid.addEventListener("change", ...)`**
   - Hapus picker lama jika ada (`tr._paPickerRow?.remove()`)
   - Cari candidates: semua lines yang match (cat1 + cat2 / tahun_ajaran)
   - Jika 1 → `_ipayFillLine` langsung (existing)
   - Jika 2+ → `_ipayBuildPickerRow`, insert setelah `tr`, simpan di `tr._paPickerRow`

3. **Ubah `sCat1.addEventListener("change", ...)`**
   - Tambah `tr._paPickerRow?.remove(); tr._paPickerRow = null;` saat Cat1 berubah

4. **Ubah delete button handler**
   - Tambah `tr._paPickerRow?.remove();` saat baris dihapus

## No Backend Changes

Semua data sudah ada di `_allLines` yang di-fetch saat siswa dipilih. Tidak ada API baru.

## Lifecycle

```
Pilih Siswa → fetch _allLines
  → Pilih Cat1 → filter cat2 options (hapus picker lama)
    → Pilih Cat2 → cari candidates
      → 1 match  → _ipayFillLine()
      → 2+ match → tampilkan PA Picker sub-row
        → User klik PA → _ipayFillLine() + hapus sub-row
```
