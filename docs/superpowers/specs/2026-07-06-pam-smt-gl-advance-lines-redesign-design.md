# FinanceHub — PAM SMT Input Redesign (GL/Advance Itemized Lines) — Design

Status: Approved (brainstorming)
Tanggal: 2026-07-06
Builds on: `2026-07-06-smt-pam-advance-design.md` (shipped the current SMT + Advance PAM feature this redesign modifies)

## Latar Belakang

`2026-07-06-smt-pam-advance-design.md` menambahkan pillar `SMT`/`ADVANCE` ke modul PAM dengan
input "free-type" — reuse penuh dari Panel Others yang tadinya dibuat untuk ETF (1 entry flat:
Keterangan, Mata Uang, DPP, PPN, Total). Setelah dipakai, form ini kurang detail untuk kebutuhan
approval SMT: tidak ada breakdown jenis biaya, tipe dokumen, no invoice, atau cost center per
department — semuanya cuma satu total per PAM tanpa rincian.

Redesign ini mengganti Panel Others (untuk SMT company saja) dengan tabel itemized multi-baris,
menghilangkan dropdown "Tipe PAM" yang jadi redundan setelah Transaksi (GL/Advance) mengambil alih
peran routing-nya, dan menambah lookup table `coa_pam` dari `COA.xlsx` (Klasifikasi SR/MR + kode GL
Expense/Advance).

Cost Center per baris (departemen: POCCOM, TFOPEX, dst.) dan Budget Activity sengaja dibuat dengan
penamaan yang kompatibel dengan `budget_master.dept` / `budget_master.activity` (module Budget
Monitoring) untuk mempermudah integrasi ke `budget_realisasi` di fase berikutnya — **integrasi live
ke Realisasi TIDAK dikerjakan di fase ini**, hanya field-nya disiapkan.

## Out of Scope (tetap sama seperti spec sebelumnya, plus tambahan)

- Tab **MR (Management Report)** — masih ditunda, tidak dibuat di fase ini.
- **Payment Application (PA) untuk SMT** — tetap free-type, tidak terhubung ke PA.
- **Integrasi ke `budget_realisasi`** — field Cost Center/Budget Activity disiapkan kompatibel,
  tapi PAM save TIDAK menulis ke `budget_realisasi` di fase ini. Menyusul sebagai fase terpisah.
- Normalisasi skema `*_pam_lines` lintas pillar.

## 1. Tab & Label Rename

- Tab `SMT` (`data-tab="tab-smt"`, list view SLA) direname jadi **"PAM List"**. Isi & fungsi
  (`loadSMT()`, filter, kolom SLA) tidak berubah — cuma label tombolnya.
- Dropdown **"Tipe PAM"** (`#ipay-type`) **dihapus dari UI** untuk `company_code == 'SMT'`. Nilai
  yang tadinya dipilih manual (`smt`/`advance`) sekarang diturunkan otomatis dari pilihan
  **Transaksi**. `_IPAY_PAM_PREFIX` dan `_VALID_PILLARS` di backend **tidak berubah** — keduanya
  sudah punya entry `"smt"→"SMT"` dan `"advance"→"SMT"` (shared PAM-number sequence), jadi hanya
  perlu diagram ulang di mana value "smt"/"advance" itu berasal di sisi frontend.
- Dropdown **"Transaksi"** (`#ipay-tx`), untuk company SMT, options-nya jadi:
  - `"gl"` — label **"GL"**
  - `"advance"` — label **"Advance"**
  (menggantikan satu-satunya opsi lama `"others"`.)
  Memilih **GL** → derived type = `"smt"` (pillar `SMT`). Memilih **Advance** → derived type =
  `"advance"` (pillar `ADVANCE`). `ipayOnTxChange()` yang menentukan panel mana yang tampil, dan
  fungsi baru men-set `ipay-type`-equivalent secara internal (variable JS, bukan elemen dropdown)
  sebelum memanggil `ipayFetchNextPamNo()` / save.

## 2. Header Fields

Tanggal, No. PAM, Perusahaan — tidak berubah.

Tambah box readonly baru **"CC"** di header (sebelah Perusahaan, pola sama dengan `#ipay-pillar`
"Auto dari vendor"): begitu vendor dipilih di `ipayVendorSearch()`/`_vendorSuggRender`, isi dari
`vendor.cost_center` (kolom yang sudah ada di tabel `vendors`, tidak perlu migrasi). Ini nilai
Cost Center milik vendor/perusahaan itu sendiri — **bukan** Cost Center departemen yang dipilih per
baris di §3 (dua konsep berbeda, sengaja dipisah).

## 3. Panel Input Baru — Tabel Multi-Baris (GL & Advance)

Panel `#ipay-panel-others` (flat form) diganti, untuk company SMT, dengan panel tabel baru
(pola sama dengan `#ipay-panel-klaim`: header table + tbody dinamis + "+ Tambah Baris" + tfoot
total), dipakai untuk **kedua** Transaksi (GL dan Advance).

Kolom per baris:

| Kolom | Sumber / Perilaku |
|---|---|
| Jenis Biaya (SR) | Search-select ke `coa_pam.klasifikasi_sr` (autocomplete, pola sama `ipayVendorSearch`). Wajib diisi. |
| Jenis Biaya (MR) | Auto-fill dari `coa_pam.klasifikasi_mr` pada baris yang cocok saat SR dipilih — **tetap editable** setelahnya untuk kasus SR≠MR. |
| GL Account | Read-only, auto: `coa_pam.coa_expense` jika Transaksi=GL, `coa_pam.coa_advance` jika Transaksi=Advance. Re-evaluated kalau user ganti Transaksi setelah pilih Jenis Biaya. |
| Tipe Dokumen | Dropdown 3 opsi (sama persis wording checkbox "Type of Request" di Print Memo — lihat §4): `"Downpayment to vendor"`, `"Invoice Payment – Non PO Invoice"`, `"Employee Advance / Reimbursement (Fund Transfer)"`. |
| No. Invoice | Text bebas. |
| DPP | Number, wajib > 0 (aturan sama seperti `save_others_payment` sekarang). |
| PPN | Number, default 0. |
| Total Amount | Read-only, computed `DPP+PPN` per baris. Footer = SUM semua baris. |
| Cost Center | Dropdown 28 kode departemen: `POCCOM, POEAMR, POICOM, POITDC, POSPON, TFOPEX, POCFAD, POOFFM, POCPRO, POCSOS, POSMED, POITEC, POSENG, POSKHU-DF, POSKHU-JB, POSKHU-LS, POSKHU-YP, POEDIR, POMDIN, POMDEX, PORLIT, TFDPLA, TFECEM, TFEGGM, TFEDIR, TFEDUC, TFSCHO, TFSHSE, TFVOED, TFKHAR, TFFCON`. Independen per baris, tidak terhubung ke CC vendor di §2. |
| Budget Activity | Text bebas untuk fase ini (bukan dropdown — daftar activity resmi ada di `budget_master.activity` tapi belum di-lock ke situ; disiapkan schema-compatible untuk integrasi nanti). |
| Keterangan | Text bebas, wajib diisi (aturan sama seperti sekarang). |

Validasi simpan: minimal 1 baris, tiap baris wajib Jenis Biaya (SR) + DPP > 0 + Keterangan.

## 4. Print Memo Linkage

Print Memo ("Format Memo" tab) auto-checklist "Type of Request" (`dm-f-type-dp` / `dm-f-type-inv` /
`dm-f-type-adv`) berdasarkan `tipe_dokumen` yang tersimpan di baris `pam_transaction_lines` milik
PAM yang sedang dibuka:

- Semua baris punya `tipe_dokumen` yang sama → checklist otomatis, tidak perlu diubah manual.
- Baris-baris punya `tipe_dokumen` berbeda (kasus jarang, satu PAM campur beberapa tipe) → tidak
  ada yang di-auto-check, user tetap pilih manual seperti sekarang (tidak ada perubahan behavior
  untuk kasus ini, jadi tidak butuh UI baru untuk menampilkan konflik).

## 5. Data Model

### `coa_pam` (baru — lookup statis, seed dari `COA.xlsx`)
```sql
CREATE TABLE IF NOT EXISTS coa_pam (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    klasifikasi_sr  TEXT NOT NULL,
    klasifikasi_mr  TEXT NOT NULL,
    coa_advance     TEXT,           -- NULL/'-' kalau tidak berlaku untuk Advance
    coa_expense     TEXT NOT NULL
);
```
Diseed idempotent (`INSERT OR IGNORE`, pola sama `VENDOR_SEED`/`COA_LIST`) dengan 44 baris dari
`C:\Users\25010160\Downloads\COA.xlsx` (hardcoded list di `config.py`, mis. `COA_PAM_SEED`).

### `pam_transaction_lines` (baru — breakdown finansial per baris)
```sql
CREATE TABLE IF NOT EXISTS pam_transaction_lines (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    pam_id          INTEGER NOT NULL REFERENCES pam_records(id) ON DELETE CASCADE,
    coa_pam_id      INTEGER REFERENCES coa_pam(id),
    klasifikasi_sr  TEXT,           -- snapshot saat entry (perubahan coa_pam nanti tidak
    klasifikasi_mr  TEXT,           --   mengubah record historis)
    gl_account      TEXT,
    tipe_dokumen    TEXT,
    no_invoice      TEXT,
    dpp             REAL DEFAULT 0,
    ppn             REAL DEFAULT 0,
    total_amount    REAL DEFAULT 0,
    cost_center     TEXT,           -- kode departemen, mis. "POCCOM"
    budget_activity TEXT,
    keterangan      TEXT,
    created_at      TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at      TEXT
);
CREATE INDEX IF NOT EXISTS idx_pam_transaction_lines_pam_id ON pam_transaction_lines(pam_id);
```

Tabel ini **terpisah** dari `smt_pam_lines`/`advance_pam_lines` (SLA-tracking, vendor + tanggal
proses — tidak berubah). `pam_transaction_lines` menyimpan breakdown finansial; `smt_pam_lines`/
`advance_pam_lines` menyimpan progres dokumen. Keduanya terhubung ke `pam_records` yang sama via
`pam_id`, independen satu sama lain.

`pam_records.dpp` / `.ppn` / `.total_amount` untuk PAM SMT (GL & Advance) menjadi **SUM dari
`pam_transaction_lines` milik PAM itu** — pola sama seperti `save_pa_payment` yang sudah menjumlah
baris siswa ke header total.

### Kompatibilitas dengan cascade realisasi Advance→SMT (dari spec sebelumnya)
Cascade `tgl_paid` (Advance) → pindah pillar `ADVANCE`→`SMT` + insert baris baru `smt_pam_lines`
(lihat §1.1 spec sebelumnya) **tidak tersentuh** oleh perubahan ini: `pam_transaction_lines` terikat
ke `pam_id` yang tidak berubah saat cascade jalan, jadi breakdown finansial tetap utuh mengikuti
PAM-nya walau pillar-nya berpindah.

## 6. Backend/API Changes

- `service.py`: fungsi baru `get_coa_pam_list(search="")` (pola sama `get_coa_list`), dan
  `save_smt_pam_transaction(company_id, company_code, data)` menggantikan
  `save_others_payment` **khusus untuk company SMT** (ETF tetap pakai `save_others_payment` yang
  ada, tidak diubah) — insert 1 `pam_records` header + N `pam_transaction_lines` dalam 1 transaction
  SQLite, total header dihitung dari SUM baris.
- Route baru `POST /payment-memo/ipay/save-smt-lines` (menggantikan pemakaian
  `/ipay/save-others` untuk SMT saja — ETF tetap ke endpoint lama).
- `GET /payment-memo/ipay/coa-pam?search=` — endpoint baru untuk autocomplete Jenis Biaya (SR/MR).
- `get_next_pam_no(tab=...)`: **tidak ada perubahan backend** — `tab` yang dikirim tetap `"smt"` /
  `"advance"`, hanya sumbernya di frontend berubah (dari Transaksi, bukan dari Tipe PAM yang
  dihapus).
- **Bugfix sekalian**: `_PAM_RE` di frontend (`/^PAM-\d{3}-(ETF|APP|LAND|SETF)-\d{2}-\d{4}$/`) belum
  mencakup `SMT`, padahal format PAM SMT yang benar (dikonfirmasi oleh `test_smt_pam.py`) adalah
  `PAM-XXX-SMT-MM-YYYY`. Manual override No. PAM untuk company SMT saat ini akan salah ditolak oleh
  validasi client-side. Diperbaiki jadi
  `/^PAM-\d{3}-(ETF|APP|LAND|SETF|SMT)-\d{2}-\d{4}$/` sebagai bagian dari pekerjaan ini karena
  langsung menyentuh alur input yang sama.
- Print Memo data loader (`dm-*` di JS + endpoint pendukungnya) menambah query
  `pam_transaction_lines` by `pam_no` untuk auto-check "Type of Request" (§4).

## 7. Rollout & Testing

- Migration idempotent standar di `database.py` (`CREATE TABLE IF NOT EXISTS` + seed
  `INSERT OR IGNORE`) — tidak menyentuh data `pam_records` SMT yang sudah ada (PAM lama tetap pakai
  total header flat tanpa baris, tetap tampil normal di "PAM List").
- Test baru mengikuti pola pytest yang ada:
  - Schema/seed: `coa_pam` terisi 44 baris, kolom sesuai `COA.xlsx`.
  - Service: `save_smt_pam_transaction` — header total = SUM baris, GL Account terpilih benar sesuai
    Transaksi (GL vs Advance), validasi baris kosong/DPP<=0 ditolak.
  - Route: `POST /ipay/save-smt-lines`, `GET /ipay/coa-pam`.
  - Print Memo: `tipe_dokumen` seragam → checkbox ter-checklist otomatis; `tipe_dokumen` campur →
    tidak ada yang di-checklist (manual seperti sekarang).
  - Regresi: pastikan endpoint lama `save_others_payment`/`/ipay/save-others` untuk company ETF
    tidak terpengaruh sama sekali.
- Tidak ada migrasi data historis — PAM SMT yang sudah dibuat sebelum redesign ini tetap seperti
  apa adanya (tanpa `pam_transaction_lines`), hanya PAM baru yang pakai struktur baru.
