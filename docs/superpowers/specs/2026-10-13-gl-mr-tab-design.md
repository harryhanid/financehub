# General Ledger: Tab MR (Management Report dari GL SMT + GL ETF)

Tanggal: 2026-10-13

## Tujuan

Tab baru **MR** di menu General Ledger (sejajar GL SMT, GL ETF, GL SETF) menampilkan data GL SMT dan GL ETF dalam format tabel Management Report, dengan filter **cutoff bulan** berdasarkan kolom Date GL. Logikanya meniru macro `GL.bas` (`TransferDataGLCombineFinalFix`) dan sheet `GL Combine` di `Management Report - MASTER.xlsb`.

## Hasil analisis macro dan workbook

Sumber: `Y:\Seagate\Management Report\2026\0926\Management Report - MASTER harry.xlsb`.

- Macro mengambil 7 kolom dari tabel GLSMT dan GLETF: Account Management (kolom 5), ID# (7), Date (8), Allocation Memo (17), Budget Activity (15), Job Name (12), DEBIT - CREDIT (44). Label sumber `SMT`/`ETF` ditambahkan.
- Filter macro: Account Management diawali `6`, `7`, `8`, atau `9`, dan DEBIT - CREDIT tidak nol/kosong.
- Rumus di sheet `GL Combine` melengkapi kolom turunan. Barisnya menjadi baris `Append1` dengan Custom = `3`.
- Pemetaan, diverifikasi terhadap data nyata (5.338 grup memo cocok, tanpa selisih):

| Kolom Append1 | Asal |
|---|---|
| COA | COA HO, dicari dari sheet `COA` lewat Account Management (SMT lewat kolom "COA SMT", ETF lewat kolom "COA ETF") |
| MM, YY | Bulan dan tahun dari Date |
| CC, CC.1 | Job Name |
| Category | "CATEGORIES 2" dari sheet `COA`, mis. " 10 - Office Supplies And Equipment Expense " |
| Activity | Budget Activity |
| Description | `- Act {tahun} : {Allocation Memo} Month : {bulan}` |
| PTA, BGT | 0 |
| Custom | `3` |
| MM.1 | Bulan |
| ACT | (Debit - Credit) / 1.000.000, **dibulatkan 1 desimal per baris** (Excel, setengah menjauhi nol) |

- `GL Combine` juga memuat sumber lain (PAM, Sponsor, Others, BMGSQ). Itu di luar scope.
- Pemetaan akun ke COA HO dan kategori hanya ada di sheet `COA` workbook MR. Aplikasi belum punya (tabel `coa` yang ada hanya kode dan nama).

## Keputusan

- Pemetaan COA disync dari workbook MR (upload .xlsb), bukan diketik manual.
- Format tampilan: **Report** (per Cost Center, per kategori) dan **Data** (tabel datar `Append1`) dalam satu tab.
- Cutoff: **kumulatif**, Januari sampai bulan terpilih pada tahun terpilih.
- Builder laporan milik modul GL sendiri. Modul `management_report` tidak diimpor karena belum ter-commit dan terikat ke snapshot `mr_upload`.
- Baris MR **dihitung saat halaman dibuka** dari tabel GLSMT/GLETF dan tabel pemetaan, tidak disimpan. Hasil otomatis konsisten setelah sync GL atau sync COA.
- Di luar scope: export Excel, sumber PAM/Sponsor/Others, BGT dan PTA.

## Struktur

Tambahan di `app/modules/general_ledger/`:

- `coa_map.py`: baca sheet `COA` dari .xlsb (`read_coa_sheet`), simpan, hash, dan log sync COA.
- `mr_rows.py`: bentuk baris MR dari baris GL dan pemetaan (`build_mr_rows`), pembulatan Excel, filter macro, dan filter cutoff.
- `mr_report.py`: kelompokkan baris MR menjadi laporan per Cost Center dan kategori.
- `routes.py` bertambah: halaman tab MR dan endpoint sync COA. Template baru `templates/general_ledger/mr.html`.

Rute:

- `GET /general-ledger/mr?yy=&mm=&cc=&view=report|data&page=&q=`
- `POST /general-ledger/mr/sync-coa`: hanya admin, menerima .xlsb.

Rute `/general-ledger/<entity>` yang sudah ada tetap hanya menerima `smt|etf|setf`. `mr` didaftarkan sebelum rute dinamis.

## Data

Tabel baru:

- `gl_coa_map`: `source` (`SMT`/`ETF`), `account`, `coa_ho`, `category`. Kunci unik (`source`, `account`). Kalau akun yang sama muncul di beberapa baris sheet, baris pertama dipakai.
- `gl_coa_sync_log`: waktu, user, nama file, hash isi, jumlah baris per sumber.

Sheet `COA` dibaca per posisi kolom: COA SMT (kolom 1), COA ETF (3), COA HO (6), CATEGORIES 2 (9), dengan header di baris kedua. Baris tanpa COA HO diabaikan. Header diperiksa. Kalau tidak cocok, pesan galat jelas.

Sync COA memakai pola sync GL: hash sama berarti "Sudah sinkron" dan tabel tidak disentuh. Hash berbeda berarti pemetaan diganti penuh dalam satu transaksi dan satu baris log ditulis. Kegagalan tidak boleh meninggalkan data setengah jadi.

## Pembentukan baris MR

Untuk tiap baris GLSMT dan GLETF dengan `acc_management` diawali `6`, `7`, `8`, atau `9` dan `debit_credit` tidak nol:

- `coa`: pemetaan (`source`, `acc_management`) ke `coa_ho`.
- `yy`, `mm`: dari `tgl` (ISO `YYYY-MM-DD`). Baris tanpa tanggal valid dilewati dan dihitung.
- `cc`: `job_name`. `activity`: `budget_activity`. `category`: dari pemetaan.
- `description`: `- Act {yy 4 digit} : {allocation_memo} Month : {mm}`.
- `custom`: `3`. `mm1`: `mm`. `pta`, `bgt`: 0. `source`: `SMT`/`ETF`.
- `act`: `debit_credit / 1.000.000` dibulatkan 1 desimal, setengah menjauhi nol, menggunakan `Decimal` dengan `ROUND_HALF_UP` pada nilai yang sudah dinormalkan (menghindari galat float).

Akun yang tidak ada di pemetaan: baris tetap dibentuk dengan `coa` kosong dan `category` `(Belum dipetakan)`. Banner peringatan menampilkan jumlah baris, total ACT, dan contoh akunnya.

Cutoff kumulatif: `yy == tahun terpilih` dan `mm <= bulan terpilih`. Daftar tahun dan bulan di dropdown berasal dari tanggal yang ada di GL. Bulan hanya yang ada datanya pada tahun itu. Default: tahun dan bulan terbaru yang ada data.

## Laporan

- Filter: Tahun, Bulan cutoff, Cost Center (default "All Cost Center", yaitu semua CC digabung per kategori).
- Tampilan **Report**: dikelompokkan per kategori (urut kode kategori), tiap kategori berisi baris detail `(Custom, MM.1, Description, Activity)` dengan ACT dijumlahkan, subtotal kategori, dan grand total. Satuan Rp Mio, 1 desimal, format angka Indonesia. Kolom BGT dan PTA tidak ditampilkan. Hanya **ACT** yang terisi.
- Tampilan **Data**: tabel datar kolom `Append1` (COA, MM, YY, CC, Category, Activity, Description, Custom, MM.1, ACT) ditambah Sumber. Paginasi di server, 100 baris per halaman, pencarian pada Description dan CC, serta filter yang sama dengan Report.
- Keadaan kosong: bila pemetaan COA belum disync, halaman menampilkan petunjuk untuk sync COA lebih dulu. Bila GL belum disync, menampilkan petunjuk untuk sync GL.
- Tombol sync COA hanya muncul untuk admin.

## Pengujian (pytest)

- Parser sheet `COA`: pemetaan kolom, baris tanpa COA HO diabaikan, header salah memberi galat, baris pertama menang untuk akun duplikat.
- `mr_rows`: filter akun 6-9 dan nonzero, pembulatan setengah menjauhi nol (termasuk negatif dan nilai batas seperti 0,05), format Description, cutoff kumulatif, tanggal tidak valid, akun belum dipetakan.
- `mr_report`: pengelompokan, subtotal, grand total, dan filter CC.
- Sync COA: hash sama berarti tidak berubah, berbeda berarti diganti, kegagalan tidak merusak data lama.
- Route: login wajib, non-admin tidak boleh sync COA (403), file bukan .xlsb ditolak (400), halaman memakai parameter yang tidak valid tanpa error 500, dan tab MR tampil di menu.
- File asli (dilewati bila file tidak ada): total ACT per (CC, kategori, bulan) hasil bentukan dibandingkan dengan baris SMT/ETF di `Append1` workbook MR. `GL - MASTER.xlsb` dan `GL Combine` bisa berbeda tanggal, jadi selisih dilaporkan dan dianalisis, tidak ditutupi dengan toleransi.
