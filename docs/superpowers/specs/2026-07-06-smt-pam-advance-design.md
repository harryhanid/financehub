# FinanceHub — PAM (Payment Approval Memo) untuk SMT + Sub-Modul Advance — Design

Status: Approved (brainstorming)
Tanggal: 2026-07-06

## Latar Belakang

Modul `payment_memo` (PAM) saat ini 100% melayani ETF (`company_id=2`) — 287 baris `pam_records`,
semua ber-pillar AGRI/APP/LAND/SETF (masing-masing punya tabel `*_pam_lines` sendiri: vendor +
7-tahap tanggal proses s/d kirim). SMT (`company_id=1`) belum pernah punya data PAM.

SMT butuh PAM dengan struktur modul: **Open PAM, Input, SMT, Advance, MR, Print Memo**.

Scope fase ini: **Open PAM, Input, SMT, Advance, Print Memo**. Tab **MR (Management Report)**
sengaja **ditunda** — sama datanya dengan tab SMT, tapi kolom tampilannya ikut standar laporan
manajemen yang belum difinalkan; akan dikerjakan sebagai fase terpisah setelah PAM SMT + Advance
selesai. Payment Application (PA) untuk SMT juga di luar scope — akan dikembangkan terpisah setelah
ini; input SMT/Advance di fase ini bersifat **free-type** (tidak menarik data dari PA), sama seperti
alur "Others" yang sudah ada di ETF.

## Approach

Mirror pola pillar yang sudah ada di `payment_memo` (opsi A dari 3 opsi yang dibahas): tambah pillar
baru `"SMT"` dan `"ADVANCE"`, pakai ulang seluruh infrastruktur generic yang sudah company-agnostic
(status flow `open→on_process→complete`, pembuatan memo, PDF export per-memo, alur input "Others").
Tidak menyentuh kode ETF yang sudah live — risiko regresi minimal.

Dua alternatif yang dipertimbangkan dan ditolak:
- Normalisasi semua pillar (termasuk ETF) ke satu tabel `pam_lines` generic — lebih bersih tapi
  butuh migrasi 287 baris data ETF live + ubah semua query/JS yang sudah jalan; risiko jauh lebih
  besar dari yang diperlukan scope ini.
- Modul terpisah `modules/smt_payment_memo/` — duplikasi route/status-flow/export yang sudah generic
  tanpa manfaat, dan Open PAM/pembuatan memo saat ini mengasumsikan satu modul PAM per company session.

## 1. Data Model

Tidak ada perubahan skema `pam_records` — cukup memakai 2 nilai `pillar` baru: `"SMT"` dan
`"ADVANCE"`.

### `smt_pam_lines` (baru — struktur `setf_pam_lines` + 1 kolom tambahan)
```
id                 INTEGER PK
pam_id             INTEGER  -- FK ke pam_records.id
no_vendor          TEXT
nama_vendor        TEXT
tgl_terima_doc     TEXT
tgl_proses         TEXT
tgl_verifikasi_tax TEXT
tgl_approval_1     TEXT
tgl_approval_2     TEXT
tgl_approval_3     TEXT
tgl_kirim          TEXT
tgl_realisasi      TEXT   -- hanya terisi untuk record yang berasal dari konversi Advance (lihat §1.1)
created_at         TEXT DEFAULT CURRENT_TIMESTAMP
updated_at         TEXT
```

### `advance_pam_lines` (baru — tahapan custom Advance)
```
id             INTEGER PK
pam_id         INTEGER  -- FK ke pam_records.id
no_vendor      TEXT
nama_vendor    TEXT
tgl_received   TEXT   -- Tanggal Received
tgl_a0         TEXT   -- A0 - S-JT
tgl_a1         TEXT   -- A1 - S-FS
tgl_a2         TEXT   -- A2 - S-YK
tgl_a3         TEXT   -- A3 - S-LL
tgl_a4         TEXT   -- A4 - A-LL
tgl_paid       TEXT   -- Tanggal Paid (= realisasi)
created_at     TEXT DEFAULT CURRENT_TIMESTAMP
updated_at     TEXT
```
`Tanggal PAM` tidak diduplikasi — sudah ada di `pam_records.pam_date`.

### 1.1 Realisasi Advance → konversi ke pillar SMT
Model status sederhana: `pam_records.status` mengikuti flow yang sama dengan pillar lain
(`open → on_process → complete`).

"Realized" bukan cuma perubahan status — begitu user mengisi `tgl_paid` di `advance_pam_lines`
(lewat tab Advance), sistem otomatis menjalankan cascade (mirror pola `set_pam_complete_cascade`
yang sudah ada, tapi dengan efek tambahan pindah pillar):

1. `pam_records.pillar` untuk record itu diubah dari `"ADVANCE"` → `"SMT"`.
2. Baris baru dibuat di `smt_pam_lines` untuk `pam_id` yang sama: `no_vendor`/`nama_vendor` di-carry
   dari baris `advance_pam_lines` lama, `tgl_realisasi` diisi dari nilai `tgl_paid` tadi, 7 kolom
   tanggal standar SMT (`tgl_terima_doc` s/d `tgl_kirim`) dimulai **kosong** — proses tahap SMT
   berjalan dari awal setelah advance realized.
3. `pam_records.status` di-set `'complete'`.
4. Baris `advance_pam_lines` lama **tidak dihapus** — tetap tersimpan sebagai arsip/riwayat, tapi
   tidak lagi muncul di tab Advance karena `pam_records.pillar` sudah `"SMT"` (query `get_pam_by_pillar`
   filter berdasarkan `pillar` saat ini, bukan riwayat).

Efek UI: record yang baru saja realized otomatis "pindah" dari tab Advance ke tab SMT pada saat
tab di-reload, dengan `tgl_realisasi` terlihat sebagai kolom tambahan di tab SMT untuk membedakannya
dari record SMT yang dari awal memang di-input sebagai `"SMT"` (yang `tgl_realisasi`-nya NULL).

## 2. Input Flow

- Dropdown **"Tipe PAM"** (`#ipay-type`) untuk session company SMT menampilkan `SMT`, `Advance`
  (bukan AGRI/APP/LAND/SETF).
- Pakai ulang **Panel Others** (keterangan, mata uang, DPP, PPN) dan service `save_others_payment`
  tanpa perubahan — pillar yang dikirim jadi `"SMT"` atau `"ADVANCE"` sesuai pilihan Tipe PAM.
  Field vendor (`no_vendor`/`nama_vendor`) tetap terisi dari selector "Perusahaan" (vendor search)
  yang sudah ada di header Input, sama seperti pillar lain.
- Nomor PAM: tambah entry baru di `_IPAY_PAM_PREFIX`: `"smt": "SMT"`, `"advance": "SMT"` (prefix
  nomor Advance sama dengan SMT — keduanya berbagi urutan penomoran yang sama).
- `_PILLAR_LINES_TABLE` / `_VALID_PILLARS` di `service.py` ditambah:
  `"SMT": "smt_pam_lines"`, `"ADVANCE": "advance_pam_lines"`.

## 3. Tab UI Baru

- **Tab SMT**: mirror persis tab SETF (`loadSETF()` → `loadSMT()`) — search, filter bulan/tahun/
  status/source, tabel dengan 7 kolom tanggal + bulk-update tanggal (mirror `_plDate` helper).
- **Tab Advance**: pola tab sama, tapi kolom tanggal custom 7 kolom (Received, A0–A4, Paid) +
  badge status outstanding (kalau `tgl_paid` kosong) / realized (kalau terisi).
- Tab **SMT**, **Advance**, dan **Print Memo** (versi SMT) hanya dirender kalau
  `session.company_code == 'SMT'`. Tab **AGRI/APP/LAND/SETF** tetap hanya untuk `company_code ==
  'ETF'`. Tab **MR tidak dibuat di fase ini**.
- Template `payment_memo/index.html` menambah percabangan `{% if company_code == 'SMT' %}` di
  bagian render tab-bar (baris ~94-100) dan panel Input Tipe-PAM dropdown, alih-alih menampilkan
  keduanya sekaligus.

## 4. Print Memo & Export

- Print Memo (PDF per-memo, `export_pam_pdf_custom`) sudah generic berdasarkan `pam_id` — jalan
  otomatis untuk pillar SMT/ADVANCE tanpa perubahan kode.
- Export Excel bulk per-pillar (mirror `export_sml_excel`) ditambah 2 fungsi baru:
  `export_smt_excel` (7 kolom sama seperti SETF) dan `export_advance_excel` (7 kolom custom Advance
  + kolom status outstanding/realized).

## Out of Scope

- Tab **MR (Management Report)** — fase terpisah setelah PAM SMT + Advance rampung.
- **Payment Application (PA) untuk SMT** — dikembangkan terpisah, tidak terhubung ke Input SMT/
  Advance di fase ini (free-type only).
- Normalisasi skema `*_pam_lines` lintas pillar (lihat "Approach" di atas).
