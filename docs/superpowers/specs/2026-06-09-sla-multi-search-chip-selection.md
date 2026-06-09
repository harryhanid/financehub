# SLA Tab — Multi-Search Chip Selection

**Date:** 2026-06-09  
**Module:** Payment Memo → Tab SLA (Days of PAM)  
**File:** `app/templates/payment_memo/index.html`

## Problem

User dapat menandai (tick) baris di tab SLA, lalu mengganti search query (by nama atau PAM no). Baris yang sudah di-tick dari search sebelumnya tidak tampil di hasil search baru, sehingga user tidak tahu mana saja yang sudah terpilih. Kondisi ini bermasalah karena tick dari berbagai search dikumpulkan menjadi satu batch update.

## Solution

Tambahkan **chips row** tepat di bawah toolbar search. Setiap baris yang di-tick menghasilkan satu chip bertuliskan `Nama / Cat1`. Chips row persisten lintas perubahan search/filter — user selalu bisa melihat seluruh selection saat ini tanpa perlu mengganti search kembali.

## Visual Layout

```
[ Search... ] [ PAM No ▾ ] [ Bulan ▾ ] [ Tahun ▾ ]  [ Update Terpilih (N) ]
─────────────────────────────────────────────────────────────────────────────
● Terpilih: [Budi Santoso · Kuliah ✕] [Dewi Rahayu · Kuliah ✕]  Hapus semua
─────────────────────────────────────────────────────────────────────────────
☐ | Nama          | PAM No       | Cat 1   | Tgl Pengajuan | ...
```

Chips row hanya tampil saat ada ≥ 1 baris terpilih. Tidak ada space yang terbuang saat tidak ada selection.

## Chip Format

`Nama Siswa · Cat1 ✕`

Contoh: `Budi Santoso · Kuliah ✕`

- Nama: identifier utama yang sudah familiar bagi user
- Cat1: disambiguator jika nama sama di kategori berbeda
- ✕: tombol de-select inline

## Overflow Handling

- Chips 1–6: tampil semua
- Chips > 6: tampil 5 chip + badge `+N lagi ▾`
- Klik `+N lagi ▾` → expand inline, badge berganti `▲ sembunyikan`

## Behavior

| Aksi | Hasil |
|------|-------|
| Centang baris di tabel | Row background biru (`#eff6ff`), chip baru muncul, counter "Update Terpilih (N)" naik |
| Uncentang baris di tabel | Row kembali putih, chip hilang, counter turun |
| Klik ✕ pada chip | Chip hilang, baris (jika tampil di search saat ini) auto uncentang, counter turun |
| Ganti search/filter | Chips tetap. Baris terpilih yang muncul di search baru = tetap biru + tercentang |
| Klik "Hapus semua" | Semua selection clear, chips row hilang, counter → 0 |
| Klik "Update Terpilih (N)" | Bulk update semua N baris. Setelah berhasil: chips row hilang, counter reset ke 0 |

## Row Highlight

Baris yang terpilih (ada di selection set) selalu diberi background `#eff6ff` dan teks nama biru `#1d4ed8` + font-weight 600, selama baris itu tampil di search apapun. Ini memberi konteks visual kedua di samping chips.

## Chips Row Styling

```css
/* chips row container */
background: #eff6ff;
border-bottom: 1px solid #bfdbfe;
padding: 5px 10px;
display: flex; gap: 5px; align-items: center; flex-wrap: wrap;

/* individual chip */
background: #1d4ed8; color: #fff;
border-radius: 99px;
padding: 2px 9px;
font-size: 11px;

/* overflow badge "+N lagi" */
background: #dbeafe; color: #1d4ed8;
border: 1px solid #93c5fd;
border-radius: 99px; padding: 2px 9px; font-size: 11px;
```

## Implementation Scope

**File yang diubah: `app/templates/payment_memo/index.html`** — JS-only, tidak ada perubahan backend.

### State baru

```js
// sudah ada
const _dopSelected = new Set();          // Set of record IDs

// baru — menyimpan label chip agar tetap bisa dirender setelah row ter-filter keluar
const _dopSelectionMeta = new Map();     // id → { nama, cat1 }
```

### Perubahan pada fungsi yang sudah ada

1. **`dopRenderRows(rows)` — hapus `_dopSelected.clear()` (line ~1548)**  
   Ganti dengan: re-apply checked state + row highlight untuk setiap row yang ID-nya ada di `_dopSelected`.  
   Template row perlu menambah conditional `checked` dan class `dop-row-selected` (background `#eff6ff`, nama biru).

2. **`dopToggleCb(cb)`** — setelah add/delete dari `_dopSelected`, tambah/hapus juga dari `_dopSelectionMeta`. Data nama+cat1 diambil dari `data-nama` / `data-cat1` attribute baris tabel. Panggil `dopRenderChips()` setelah `_dopUpdateInfo()`.

3. **`dopToggleSelectAll(masterCb)`** — sama, sync `_dopSelectionMeta`, panggil `dopRenderChips()`.

4. **`dopBulkUpdate()` — setelah berhasil** — clear `_dopSelected`, clear `_dopSelectionMeta`, panggil `dopRenderChips()`.

5. **`dopClearSearch()` (tombol Bersihkan)** — tidak clear selection; hanya clear search input. Behaviour ini TIDAK berubah.

### Fungsi baru

6. **`dopRenderChips()`** — render chips row `#dop-chips-row` berdasarkan `_dopSelectionMeta`.  
   - Jika `_dopSelected.size === 0` → sembunyikan chips row.  
   - Jika 1–6 chip → tampil semua.  
   - Jika > 6 → tampil 5 chip pertama + badge `+N lagi ▾` (toggle expand inline).

7. **`dopRemoveChip(id)`** — hapus dari `_dopSelected` + `_dopSelectionMeta`. Jika row masih ada di tabel, uncheck checkboxnya. Panggil `_dopUpdateInfo()` + `dopRenderChips()`.

8. **`dopClearAllChips()`** — clear keduanya, uncheck semua `.dop-cb`, panggil `_dopUpdateInfo()` + `dopRenderChips()`.

### HTML baru

Tambahkan `<div id="dop-chips-row">` tepat di bawah div toolbar search (sebelum `<div style="overflow-x:auto">`). Hidden by default (`display:none`).

## Out of Scope

- Tidak ada perubahan backend/API
- Tidak ada persistence ke localStorage (selection reset saat tab reload)
- Tidak menyentuh tab lain (AGRI, APP, SML, Input)
