# FinanceHub — ETF Payment Application: Route GL vs Advance — Design

Status: Approved (brainstorming)
Tanggal: 2026-07-07
Builds on: `2026-07-06-smt-pam-advance-design.md` (pola pillar `ADVANCE` + tabel `advance_pam_lines`
yang dipakai ulang di sini)

## Latar Belakang

Modul ETF Payment Application (tab bar: `Open PA, Input, AGRI, APP, LAND, SETF`) saat ini hanya
punya satu jalur pencatatan: baris PA (siswa/vendor) ditarik di Input → langsung jadi `pam_records`
dengan pillar sesuai asalnya (AGRI/APP/LAND/SETF) via `save_pa_payment`.

Kebutuhan baru: sebagian pembayaran sebenarnya adalah **uang muka (advance)** — dibayar duluan
sebelum nilai final diketahui — dan baru "direalisasi" (dikoreksi ke nilai aktual) belakangan. Ini
butuh jalur ketiga di antara "belum dibayar" dan "selesai": *dibayar tapi masih quarantine*.

Pola ini **sudah dibangun untuk company SMT** (`2026-07-06-smt-pam-advance-design.md`): pillar
`ADVANCE` yang quarantine sebuah PAM sampai direalisasi, baru pindah pillar. Bedanya, SMT bersifat
free-type (tidak terhubung ke PA) dan tidak punya konsep selisih — begitu `tgl_paid` diisi, langsung
dianggap selesai. ETF butuh versi yang terhubung ke PA (per-baris siswa/vendor) dan punya langkah
rekonsiliasi eksplisit (input nilai aktual + hitung selisih) sebelum ditutup.

## Approach

Reuse maksimal infrastruktur yang sudah ada, bukan bikin modul paralel:

- Pillar `"ADVANCE"` dan tabel `advance_pam_lines` **sudah ada** (dibuat untuk SMT) — dipakai ulang
  apa adanya untuk tracking tanggal proses vendor per PAM Advance ETF.
- PA header+lines (`etf_pa`/`app_pa`/`sml_pa`/`setf_pa` + `*_pa_lines`) **tidak berubah** — tetap
  satu-satunya sumber baris siswa/vendor.
- `save_pa_payment` **tidak ditulis ulang** — dipanggil dengan pillar tujuan `"ADVANCE"` (bukan
  pillar asli) ketika Route = Advance. Ini otomatis mewarisi seluruh perbaikan bug FK/status yang
  sudah ada di fungsi ini untuk keempat pillar ETF.

Dua alternatif yang dipertimbangkan dan ditolak:
- **Tabel PA baru khusus Advance** (`advance_pa` + `advance_pa_lines`, mirror `etf_pa`) — ditolak
  karena field granularitas Advance sama persis dengan PA yang sudah ada (1 baris = 1 siswa/vendor),
  jadi duplikasi skema tanpa manfaat. Juga akan butuh tab "Open PA Advance" terpisah yang membingungkan
  alur yang sudah dikenal user.
- **Selisih memicu PAM susulan otomatis** (pelunasan kekurangan / piutang kelebihan bayar) — ditolak
  untuk fase ini karena butuh alur PAM baru + tracking piutang yang jauh lebih kompleks. Realisasi
  cukup meng-update `pam_records`/`payment_beasiswa` yang sudah ada secara in-place.

## 1. Data Model

### Kolom baru di PA-lines (`etf_pa_lines`, `app_pa_lines`, `sml_pa_lines`, `setf_pa_lines`)
```sql
ALTER TABLE etf_pa_lines  ADD COLUMN route TEXT;  -- 'gl' | 'advance' | NULL (belum dipilih)
ALTER TABLE app_pa_lines  ADD COLUMN route TEXT;
ALTER TABLE sml_pa_lines  ADD COLUMN route TEXT;
ALTER TABLE setf_pa_lines ADD COLUMN route TEXT;
```
Kolom helper murni untuk tampilan di tab **Open PA** — tidak dipakai untuk logika apa pun selain
filter/tampilan. Diisi otomatis oleh `save_pa_payment` saat baris itu ditarik ke Input.

### Kolom baru di `payment_beasiswa`
```sql
ALTER TABLE payment_beasiswa ADD COLUMN advance_amount  REAL;  -- snapshot amount saat route=advance
ALTER TABLE payment_beasiswa ADD COLUMN realized_amount REAL;  -- diisi saat realisasi
ALTER TABLE payment_beasiswa ADD COLUMN tgl_realisasi   TEXT;
```
Ketiga kolom ini **NULL** untuk baris route GL (termasuk beasiswa normal) — GL dianggap realized
instan sejak awal, tidak ada tahap quarantine.

`payment_beasiswa.pillar` **tetap** menyimpan pillar tujuan asli (AGRI/APP/LAND/SETF) — tidak pernah
ditulis `"ADVANCE"`. Yang berubah jadi `"ADVANCE"` hanya `pam_records.pillar` (header), sehingga saat
realisasi selesai, pillar asli tinggal dibaca dari `payment_beasiswa.pillar` milik baris-baris PAM
itu — tidak perlu kolom baru untuk menyimpan "target pillar".

`advance_pam_lines` (sudah ada dari pola SMT) dipakai apa adanya untuk tracking vendor + tanggal
proses per PAM Advance ETF — tidak ada perubahan skema di tabel ini.

## 2. Status Flow

`pam_records.status` **tidak berubah** — tetap 2-state (`open`/`on_process` → `complete` via
`set_pam_complete_cascade` yang sudah ada, dipanggil apa adanya saat PAM Advance dibayar).

Level status Advance yang sebenarnya (dibayar vs sudah direalisasi) dibaca dari
`payment_beasiswa.status`, yang mendapat 1 nilai baru `'paid'` di antara `on_process` dan
`complete`:

| Tahap | `pam_records.pillar` | `pam_records.status` | `payment_beasiswa.status` |
|---|---|---|---|
| Route=Advance dipilih & disimpan | `ADVANCE` | `open` | `open` |
| Ditarik ke PAM di Input | `ADVANCE` | `open`/`on_process` | `on_process` |
| PAM dibayar (`tanggal_bayar` diisi) | `ADVANCE` | `complete` | `paid` *(baru)* |
| Realisasi disimpan (close) | pillar asli (`AGRI`/`APP`/`LAND`/`SETF`) | `complete` | `complete` |

`set_pam_complete_cascade` perlu 1 penyesuaian kecil: untuk baris dengan `pillar` header
`"ADVANCE"`, set `payment_beasiswa.status='paid'` (bukan `'complete'` langsung) — baris non-Advance
tidak berubah perilakunya.

## 3. Realisasi & Close

Aksi baru `realize_advance_payment(payment_id, realized_amount, tgl_realisasi, company_id)`:
1. Validasi: baris `payment_beasiswa` harus berstatus `'paid'` dan `pillar` bukan `NULL`.
2. Update baris: `realized_amount`, `tgl_realisasi`, `amount = realized_amount`, `status='complete'`.
3. Selisih = `advance_amount - realized_amount` — dihitung on-the-fly saat ditampilkan (tidak
   disimpan sebagai kolom terpisah, cukup derived dari 2 kolom yang sudah ada).
4. Cek: jika semua baris `payment_beasiswa` dengan `pam=<pam_no milik payment ini>` sudah
   `status='complete'`, maka `pam_records.pillar` untuk PAM itu di-update dari `"ADVANCE"` ke
   pillar asli (dibaca dari `payment_beasiswa.pillar` baris-baris itu — harus seragam per PAM,
   karena `save_pa_payment` sudah membatasi 1 PAM = 1 tab/pillar sejak awal).
5. Jika PAM berisi baris dari route campuran (kasusnya tidak mungkin terjadi, karena Route dipilih
   di level Input sebelum baris ditarik — 1 PAM = 1 Route), tidak perlu ditangani.

## 4. UI

**Tab bar** (company ETF): `Open PA | Advance | Input | AGRI | APP | LAND | SETF` — tab baru
**Advance**, mirror pola tab SETF (search, filter bulan/tahun/status, bulk-update tanggal), dengan
tambahan:
- Filter status: `Belum Dibayar` (`open`/`on_process`) / `Sudah Dibayar - Menunggu Realisasi`
  (`paid`) / `Selesai` (`complete`) — dibaca dari `payment_beasiswa.status`.
- Baris `status='paid'` dapat tombol **"Realisasi"** → modal kecil isi `realized_amount` +
  `tgl_realisasi`, menampilkan selisih real-time saat diketik.

**Tab Open PA**: tambah kolom **Route** (`GL`/`Advance`/`—`) di tabel per baris.

**Tab Input**: tambah radio/dropdown **"Route"** (`GL` default, `Advance`) di panel input yang
sudah ada. Pilih Advance → `save_pa_payment` dipanggil dengan pillar tujuan `"ADVANCE"`, dan setiap
baris PA yang dipilih diberi `route='advance'` + `advance_amount=<amount baris>`. Pilih GL → jalur
existing, tidak berubah, `route='gl'` dicatat untuk visibilitas Open PA.

## 5. Backend/API Changes

- `modules/beasiswa/service.py::insert_payment_rows` — tambah param `route` (default `"gl"`),
  dipakai untuk set kolom `route` di PA-lines dan `advance_amount` di `payment_beasiswa` saat
  `route="advance"`.
- `modules/payment_memo/service.py::save_pa_payment` — terima `route` dari request body, teruskan
  ke `insert_payment_rows`; kalau `route="advance"`, pillar `pam_records` yang dibuat jadi
  `"ADVANCE"` (bukan `data.get("pillar")` seperti sekarang).
- `modules/payment_memo/service.py::set_pam_complete_cascade` — untuk pam dengan pillar header
  `"ADVANCE"`, set `payment_beasiswa.status='paid'` alih-alih `'complete'`.
- Fungsi baru `realize_advance_payment(payment_id, realized_amount, tgl_realisasi, company_id)` di
  `modules/payment_memo/service.py` — lihat §3.
- Route baru: `POST /payment-memo/advance/<payment_id>/realize`.
- `get_pam_by_pillar` / tab Advance: query `payment_beasiswa` join `pam_records` filter
  `pam_records.pillar='ADVANCE'`, tampilkan status per baris dari `payment_beasiswa.status`.

## 6. Testing (TDD, mengikuti pola pytest yang sudah ada)

- `insert_payment_rows` dengan `route="advance"`: PA-line `route` ter-set, `payment_beasiswa.pillar`
  tetap pillar asli, `advance_amount` ter-set, `pam_records` (via `save_pa_payment`) pillar-nya
  `"ADVANCE"`.
- `insert_payment_rows` dengan `route="gl"` (default, regresi): perilaku sekarang tidak berubah,
  `advance_amount`/`realized_amount`/`tgl_realisasi` tetap NULL.
- `set_pam_complete_cascade` pada PAM pillar `ADVANCE`: `payment_beasiswa.status` jadi `'paid'`,
  bukan `'complete'`; `pam_records.pillar` tetap `ADVANCE` (belum pindah).
- `realize_advance_payment`: update amount/status benar, selisih dihitung benar, dan
  `pam_records.pillar` pindah ke pillar asli setelah SEMUA baris PAM itu `complete`.
- `realize_advance_payment` dipanggil sebelum status `'paid'` (mis. masih `open`) → ditolak.
- Regresi: seluruh test `save_pa_payment`/`insert_payment_rows` existing (termasuk 6 test SETF FK
  dari sesi sebelumnya) tetap hijau — route default `"gl"` tidak boleh mengubah perilaku lama.

## Out of Scope

- PAM susulan otomatis untuk selisih (kurang/lebih bayar) — realisasi hanya update in-place, tidak
  membuat transaksi baru.
- Advance untuk company SMT tidak disentuh — tetap pakai `advance_pam_lines` versi free-type yang
  sudah ada, tidak digabung dengan alur PA-linked ini.
- Print Memo / Export Excel untuk PAM pillar `ADVANCE` di ETF — reuse mekanisme generic yang sudah
  pillar-agnostic (sama seperti disebutkan di spec SMT), tidak perlu perubahan kode tambahan di luar
  memastikan `ADVANCE` masuk daftar pillar yang valid untuk company ETF juga.
