# PAM SLA Tab Redesign

**Date:** 2026-06-11  
**Module:** `payment_memo` → tab SLA (Days of PAM)  
**Status:** Approved for implementation

---

## Problem

Tab SLA saat ini punya dua masalah yang saling bertentangan:

1. **Tampil semua → lemot.** `get_days_of_pam()` fetch semua ribuan rows dari DB, lalu filter di Python.
2. **Tidak tampil semua → terasa kosong.** User buka tab, tidak ada data terlihat, harus search dulu.

Use case utama: lihat overview record yang **belum paid**, lalu bulk-update tanggalnya.

---

## Design

### Default Behaviour

Tab buka → langsung tampilkan **100 record pertama** yang `tgl_Paid IS NULL` untuk source **AGRI**.  
Tidak perlu search dulu. Data selalu ada saat tab dibuka.

Info row count ditampilkan: `"Menampilkan 100 dari 247 record belum paid (AGRI)"`

### Filter Bar

```
[ AGRI ✓ ]  [ APP ]  [ SML ]  [ SETF ]      ☑ Belum Paid saja
  [Cari PAM No...]  [Cari Nama...]  [🔍 Cari]  [Bersihkan]
```

- **Source toggle** (AGRI / APP / SML / SETF): mengubah source filter dan kolom tanggal yang ditampilkan
- **"Belum Paid saja"** checkbox: default ON. Dimatikan untuk lihat semua record termasuk yang sudah paid
- Search PAM No dan Nama tetap ada sebagai filter tambahan, combine dengan source + paid filter
- Filter kolom (cat1, cat2, perusahaan, pillar) tetap di subheader tabel — client-side filter pada visible rows

### Kolom per Source

Kolom tetap (semua source):  
`Siswa Code · Nama · PAM No · Cat1 · Cat2 · Perusahaan · Pillar · Amount · Tanggal · Tgl Pengajuan · Tgl Receive · Tgl PA · Tgl Final · Tgl Retur · Tgl Final6 · Tgl Proses`

Kolom source-specific:

| Source | Kolom tambahan |
|--------|----------------|
| AGRI   | tgl_HT_AGRI · tgl_Yurike_AGRI · tgl_Aditya_AGRI · tgl_Pedy_AGRI · tgl_C2_AGRI · tgl_MSIG_AGRI · **tgl_Paid_AGRI** |
| APP    | tgl_A-GS_APP · tgl_A-HJK_APP · tgl_ASPIRO_APP · **tgl_Paid_APP** |
| SML    | TBD — konfirmasi nama kolom paid di DB |
| SETF   | TBD — konfirmasi nama kolom paid di DB |

Saat source berganti, kolom source lama disembunyikan, kolom source baru ditampilkan.

### Load-More

- Tabel render 100 row pertama
- Tombol **"Muat 100 lagi (masih X)"** muncul di bawah tabel jika masih ada data
- Load-more **append** ke tabel (tidak replace), agar selection `_dopSelected` tetap intact
- Request berikutnya pakai `offset=100`, `offset=200`, dst.

### Empty States

| Kondisi | Pesan |
|---------|-------|
| Loading | Spinner di area tabel |
| 0 hasil dengan paid_only=true | "Tidak ada record [SOURCE] yang belum paid." |
| 0 hasil dengan paid_only=false | "Tidak ada data untuk filter ini." |
| 0 hasil search | "Tidak ada hasil untuk pencarian ini." |
| Semua sudah paid | "Semua record [SOURCE] sudah paid! 🎉" |

### Bulk Update

Alur tidak berubah: centang baris → isi tanggal → klik "Update Terpilih".  
Perubahan: setelah update sukses, tabel **re-fetch otomatis** dengan filter aktif yang sama (source + paid_only + search terms).

---

## Backend Changes

### `get_days_of_pam()` — refactor signature

```python
def get_days_of_pam(
    company_id: int,
    source: str = "AGRI",
    paid_only: bool = True,
    pam: str = None,
    nama: str = None,
    limit: int = 100,
    offset: int = 0,
) -> dict:  # returns {"rows": [...], "total": int}
```

**Source diperoleh dari JOIN `pam_records`** (bukan kolom di `payment_beasiswa`):
```
payment_beasiswa.pam = pam_records.pam_no
pam_records.source ∈ { 'etf_agri', 'etf_app', 'beasiswa' }
```

**Mapping source UI → pam_records.source & kolom paid:**
```python
_SOURCE_MAP = {
    "AGRI": {"pr_source": "etf_agri", "paid_col": "tgl_Paid_AGRI"},
    "APP":  {"pr_source": "etf_app",  "paid_col": "tgl_Paid_APP"},
    # SML, SETF: belum ada kolom tgl_Paid_SML/SETF di payment_beasiswa
    # → MVP: scope AGRI dan APP saja; SML/SETF ditambahkan bila kolom sudah ada
}
```

**SQL pattern:**
```sql
SELECT pb.id, pb.siswa_code, s.nama, pb.pam AS pam_no, ...
FROM payment_beasiswa pb
LEFT JOIN siswa s ON s.company_id = pb.company_id AND s.code = pb.siswa_code
JOIN pam_records pr ON pr.pam_no = pb.pam AND pr.company_id = pb.company_id
WHERE pb.company_id = :company_id
  AND pr.source = :pr_source           -- filter source via pam_records
  AND (:paid_only = 0 OR pb."tgl_Paid_AGRI" IS NULL)  -- paid filter (kolom dinamis per source)
  AND (:pam = '' OR pb.pam LIKE :pam_like)
  AND (:nama = '' OR LOWER(s.nama) LIKE :nama_like)
  AND pb.pam IS NOT NULL AND pb.pam != ''
ORDER BY pb.tanggal DESC
LIMIT :limit OFFSET :offset
```

Total count dihitung dengan query COUNT terpisah (pakai filter yang sama tanpa LIMIT/OFFSET).

### Endpoint `/days-of-pam/search` — update params

**Sebelum:** `?pam=&nama=`  
**Sesudah:** `?source=AGRI&paid_only=1&pam=&nama=&offset=0`

**Response:**
```json
{
  "ok": true,
  "rows": [...],
  "total": 247,
  "offset": 0,
  "limit": 100
}
```

### Endpoint baru: `/days-of-pam/default`

`GET /payment-memo/days-of-pam/default?source=AGRI`

Dipanggil saat tab pertama dibuka. Equivalent ke search dengan `paid_only=1, offset=0`.  
Bisa juga digabung ke `/search` dengan default params — tidak perlu endpoint terpisah.

---

## Frontend Changes (`index.html`)

### Komponen baru
- Source toggle pills (AGRI/APP/SML/SETF) — di atas filter bar
- Checkbox "Belum Paid saja" — di sebelah kanan source toggle
- Info count label — `"Menampilkan X dari Y record belum paid (AGRI)"`
- Load-more button — di bawah `#dop-tbody`

### Logika diubah
- `dopTabOpened()`: langsung panggil `_dopFetch` dengan default params (AGRI, paid_only=true, offset=0)
- `_dopFetch(qs)`: tambah support `offset` di URL, mode append vs replace
- `dopRenderRows(rows, append=false)`: kalau `append=true`, innerHTML += bukan =
- Kolom tabel: render kolom source-specific secara dinamis (atau toggle visibility via CSS class)

### Logika tidak berubah
- `_dopSelected`, `_dopSelectionMeta`, chip selection system
- `dopBulkUpdate()` — hanya tambahkan re-fetch setelah sukses
- `bulk_update_dates()` di backend — tidak berubah
- `get_days_of_pam_candidates()` — tidak berubah

---

## Out of Scope

- Visualisasi SLA (chart, heatmap) — bisa jadi fitur terpisah
- Export SLA ke Excel — sudah ada di modul lain
- Notifikasi overdue otomatis

---

## Open Questions

1. Nama kolom paid untuk source SML dan SETF — apakah akan ditambahkan kolom `tgl_Paid_SML` dan `tgl_Paid_SETF` ke `payment_beasiswa`, atau SML/SETF punya alur SLA yang berbeda?
2. Apakah `pam_records` untuk semua record SML/SETF sudah ada di DB (source='etf_sml'/'etf_setf'), atau data SML/SETF tidak melalui `pam_records`?

**Resolved:**
- Source filter: JOIN `pam_records` via `pb.pam = pr.pam_no`, filter `pr.source`
- Source values: `etf_agri` (AGRI), `etf_app` (APP)
- MVP scope: AGRI dan APP saja; SML/SETF masuk setelah kolom tgl_Paid-nya dikonfirmasi
