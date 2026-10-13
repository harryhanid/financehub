# Management Report: GL Combine dan Append1 dari modul GL dan Sponsorship

Tanggal: 2026-10-13

## Tujuan

Modul **Management Report** (MR) membentuk sendiri `GL Combine` dan `Append1` dari data yang sudah ada di aplikasi, tanpa upload Excel:

- **GL SMT** dan **GL ETF**: dibaca dari modul General Ledger.
- **Sponsorship (SMT)**: dibaca dari modul Sponsorship.
- PAM, BMG, dan Others belum ada di alur aplikasi dan diabaikan dulu.

Dua tab baru di modul MR: **GL Combine** (17 kolom seperti sheet) dan **Append1** (13 kolom seperti sheet), dengan filter bulan cutoff kumulatif. Tab MR yang dibuat sebelumnya di modul General Ledger dipindahkan ke sini, dengan sumber ditambah Sponsorship.

## Latar belakang dan temuan data

Acuan: `Y:\Seagate\Management Report\2026\0926\Management Report - MASTER harry.xlsb` (sheet `GL Combine`, `Append1`), `GL - MASTER.xlsb` di folder yang sama, dan database dev.

- Sheet `GL Combine` menggabungkan sumber SMT (4.001 baris), ETF (1.394), PAM (212), Sponsor (85), Others, dan BMGSQ. Seluruhnya menjadi baris `Append1` dengan Custom = `3`.
- Pembentukan baris SMT/ETF (filter akun 6–9 dan DEBIT − CREDIT tidak nol, pemetaan COA/CC, New Code, ACT) sudah dibangun dan diverifikasi pada pekerjaan tab MR modul GL (spec `2026-10-13-gl-mr-tab-design.md`).
- **Sponsorship SMT 2026** di database: 91 transaksi. Jan–Sep persis cocok dengan 85 baris `Sponsor` di workbook per bulan (5, 9, 13, 11, 5, 10, 7, 16, 9). Oktober (6 baris) belum ada di workbook.
- Aturan baris `Sponsor` di workbook (85 baris):
  - Date = `tanggal_form_sponsor`, nominal = `amount_request`, semua status (tanpa filter).
  - Allocation Memo = `perihal` saja (cocok 83 dari 85 baris, 2 sisanya edit manual).
  - Account Management = COA HO = `701078002` (9 digit; `config.py` berisi `70107800`, 8 digit, kemungkinan usang).
  - COST CENTER = `POSPON`, COST CENTER2 = `$POCCOM`, CC1 = 5, BC1 kosong, ID# kosong, Budget Activity kosong.
  - New Code `A26-51`, `A26-52`, … `A26-585` (rumus yang sama dengan sumber lain dengan BC1 kosong).
  - BC (kategori) adalah sel error, sehingga di `Append1` kategorinya kosong.
- Modul Sponsorship sudah punya `get_sponsorship_mr` (tab MR Sponsorship, 17 kolom) dengan aturan berbeda dari workbook: account 8 digit, BC1 `-25-`, kategori "Sponsorship - Non Building", memo gabungan.

## Keputusan

- Struktur: **pindah dan perluas**. Logika pembentuk baris, pemetaan, dan tampilan pindah dari modul GL ke modul MR (`git mv` agar riwayat terjaga). MR membaca data mentah lewat fungsi baca modul GL dan Sponsorship.
- Baris **dihitung saat halaman dibuka**, tidak disimpan.
- Sponsorship mengikuti **format workbook** (bukan spec Sponsorship lama).
- Modul Sponsorship dan konstanta `SPONSORSHIP_MR_*` di `config.py` **tidak diubah**. Aturan baru memakai pengaturan baru `MR_SPONSOR_*`. Akibatnya tab MR Sponsorship dan tab Append1/GL Combine di MR bisa berbeda sampai pengguna memutuskan menyelaraskannya.
- Tab/tampilan **Report hasil bentukan** (dari pekerjaan sebelumnya) tidak ikut dipindah. Tahap berikutnya, tab Report dan HO Report milik modul MR akan membaca Append1 hasil bentukan.
- Tab MR lama di modul General Ledger dihapus. Tab GL SMT, GL ETF, GL SETF tetap.
- **Fitur yang sudah ada di modul MR tetap utuh.** Sync dari upload Excel (`POST /management-report/sync`, snapshot `mr_upload`/`mr_append`, aktivasi snapshot), tab Data Sync, Report, HO Report, dan export BGT tidak diubah perilakunya, tidak dihapus, dan tidak dibuat bergantung pada fitur baru. Fitur baru hanya berupa tab dan halaman baru.
- Modul MR dan tesnya sudah ter-commit sebagai baseline (commit `0ecb2b2`).

## Struktur

Perubahan di `app/modules/management_report/`:

- `coa_map.py` (dipindah dari GL): pemetaan COA/CC dari sheet `COA` dan `CC` workbook MR. Nama tabel tidak berubah (`gl_coa_map`, `gl_cc_map`, `gl_coa_sync_log`), jadi data yang sudah di-sync tetap berlaku.
- `combine_sources.py` (baru): adaptor per sumber, masing-masing mengembalikan baris mentah seragam.
  - `gl_rows(entity)`: membungkus `general_ledger.service.load_mr_source`.
  - `sponsor_rows()`: membaca `sponsorship.service.list_transaksi(company_id_SMT)` (semua tahun, tanpa filter) dengan company SMT dicari dari tabel `companies` berdasarkan kode `SMT`, tanpa angka tetap. Tahun yang diambil: semua tahun yang punya data. Urutan: `tanggal_form_sponsor` naik, lalu `id` naik.
- `combine_rows.py` (dipindah dari `mr_rows.py`, diperluas): membentuk baris GL Combine dari tiga sumber, penomoran New Code, ringkasan belum-dipetakan, opsi periode, dan cutoff.
- `combine_columns.py` (dipindah dari `mr_columns.py`): daftar kolom GL Combine dan Append1 beserta tipe tampilan.
- `routes.py` dan template MR: dua halaman baru dengan bilah tab bersama, `/management-report/gl-combine` dan `/management-report/append1`, ditambah `POST /management-report/gl-combine/sync-mapping` (admin, menerima .xlsb). Tab lama (Data Sync, Report, HO Report) tidak diubah selain bilah tab yang menautkan dua tab baru.
- `config.py`: konstanta cadangan baru `MR_SPONSOR_ACCOUNT = "701078002"`, `MR_SPONSOR_COST_CENTER = "POSPON"`, `MR_SPONSOR_SOURCE = "Sponsor"`, dipakai hanya bila kolom `coa`/`cc` baris Sponsorship kosong. `MR_SPONSOR_COST_CENTER2` dan `MR_SPONSOR_CC1` tidak ada: COST CENTER2 dan CC1 dicari lewat pemetaan CC yang sama dengan GL.

Yang dihapus dari `app/modules/general_ledger/`: `mr_rows.py`, `mr_report.py`, `mr_columns.py`, `coa_map.py` (dipindah atau dihapus), route `/mr` dan `/mr/sync-coa` di `routes.py`, tautan MR di `templates/general_ledger/_tabs.html`, template `mr.html`. Fungsi `service.load_mr_source` tetap di modul GL karena dipakai MR.

## Aturan baris

Semua sumber menghasilkan baris dengan kunci yang sama (kunci yang sudah dipakai: `coa, mm, yy, cc, category, activity, description, custom, mm1, pta, bgt, act, source, account, unmapped, id_no, tgl, allocation_memo, debit_credit, cost_center2, cc0, cc1, bc1, new_code, cc_unmapped`).

- **GL SMT / GL ETF:** tidak berubah dari pekerjaan sebelumnya.
- **Sponsor:** untuk tiap transaksi Sponsorship SMT:
  - `account` = `coa` = kolom `coa` baris Sponsorship (cadangan `MR_SPONSOR_ACCOUNT` bila kosong), `cc` = kolom `cc` baris Sponsorship (cadangan `MR_SPONSOR_COST_CENTER` bila kosong), `cost_center2` dan `cc1` dicari lewat pemetaan CC (sheet `CC`) dengan kunci `cc`, sama seperti baris GL (bila tidak ada: kosong / 0 dan `cc_unmapped` = true), `bc1` = "", `source` = `MR_SPONSOR_SOURCE`.
  - `tgl` = `tanggal_form_sponsor`, `debit_credit` = `amount_request`, `allocation_memo` = `perihal` (apa adanya, boleh kosong), `id_no` = "", `activity` = "", `category` = "" (tampil kosong), `unmapped` = false, `cc_unmapped` mengikuti pemetaan CC.
  - `description` = `- Act {tahun} : {perihal} Month : {bulan}`. ACT = `debit_credit / 1.000.000`, setengah ke genap setelah normalisasi 15 digit signifikan (aturan yang sama dengan GL).
  - Transaksi tanpa tanggal form valid dilewati dan dihitung (`skipped_date`).
- **New Code:** `A{cc0}-{cc1}{bc1}{n}`, `n` adalah hitungan berjalan per grup (`cc0`, `cc1`, `bc1`) dalam urutan bentukan: semua GL SMT, lalu GL ETF, lalu Sponsor, dihitung atas semua baris sebelum filter apa pun (cutoff, CC, Source, pencarian).

## Tampilan

Halaman GL Combine dan Append1 berbagi filter dan bilah tab:

- Filter: Tahun, Cutoff bulan (kumulatif Januari sampai bulan terpilih; hanya bulan yang ada datanya; default tahun dan bulan terbaru), Cost Center, **Source (Semua / SMT / ETF / Sponsor)**, dan pencarian (deskripsi, CC, COA, ID#, New Code, memo).
- GL Combine: 17 kolom persis seperti sheet (Account Management, ID#, Date, Allocation Memo, Budget Activity, COST CENTER, DEBIT - CREDIT, Source, COA HO, COST CENTER2, Month, CC0, CC1, BC1, New Code, Memo, BC).
- Append1: 13 kolom persis seperti sheet (COA, MM, YY dua digit, CC, CC.1, Category, Activity, Description, PTA, Custom, MM.1, ACT, BGT).
- Urutan baris mengikuti urutan bentukan (bukan diurutkan ulang). Paginasi 100 baris per halaman.
- Kartu ringkasan: Periode, Baris, Total (ACT dalam Rp Mio pada Append1, DEBIT - CREDIT pada GL Combine), mengikuti filter dan pencarian.
- Banner: pemetaan perlu disync ulang (sheet CC dan kolom Code belum dimuat), akun belum dipetakan, cost center belum dipetakan (berlaku untuk setiap sumber yang cost center-nya tidak punya COST CENTER2), dan baris dilewati karena tanggal tidak valid (GL dan Sponsor).
- Parameter yang tidak valid (`yy`, `mm`, `page`, `cc`, `source`, `view`) kembali ke nilai default dengan status 200. Nilai yang ditampilkan di-escape.
- Keadaan kosong: pemetaan COA belum ada, atau tidak ada data sumber sama sekali, menampilkan petunjuk.
- Tombol "Sync pemetaan COA & CC" (admin) ada di halaman GL Combine. Hanya admin yang boleh sync.

## Pengujian (pytest)

- **Semua tes MR yang sudah ada (`tests/test_mr_*.py`) harus lulus tanpa diubah.** Itu bukti fitur upload dan tab lama tetap utuh; tes lama hanya boleh diubah bila kontrak tab bar memang berubah dan perubahannya dicatat.
- Tes yang sudah ada untuk `coa_map`, `mr_rows`, `mr_columns`, dan tampilan dipindah dan disesuaikan ke modul baru. Perilaku GL tidak boleh berubah.
- Adaptor `sponsor_rows`: company SMT dicari dari kode, transaksi tahun lain ikut, urutan `tanggal_form_sponsor` lalu `id`, memo = `perihal`, transaksi tanpa tanggal valid dilewati.
- Baris Sponsor: `coa`/`cc` dari baris Sponsorship (cadangan dari `MR_SPONSOR_*`), COST CENTER2 dan CC1 dari pemetaan CC, deskripsi, ACT setengah ke genap, tidak ditandai belum dipetakan.
- Penomoran New Code gabungan: SMT, ETF, lalu Sponsor; grup Sponsor berhitung sendiri per tahun; tidak terpengaruh cutoff, Source, atau pencarian.
- Route: dua halaman baru, filter Source, parameter tidak valid, admin-only sync, tab bar, dan tab MR lama di modul GL sudah tidak ada (404) sementara tab GL SMT/ETF/SETF tetap jalan.
- File asli (dilewati bila Y: tidak terjangkau): 85 baris `Sponsor` di `GL Combine` dibandingkan dengan baris Sponsor bentukan Jan–Sep (jumlah per bulan, tanggal, nominal persis; memo boleh berbeda di 2 baris edit manual; urutan dan New Code dilaporkan). Baris GL dan perbandingan `Append1` dari pekerjaan sebelumnya diperluas ke tiga sumber.

## Risiko dan di luar scope

- Bilah tab modul MR memakai panel JS pada satu halaman, sedangkan dua tab baru adalah halaman terpisah. Plan harus memastikan kedua jenis tab tampil konsisten dan tautan antar tab bekerja.
- Modul MR memanggil fungsi baca modul GL dan Sponsorship (ketergantungan satu arah, baca saja).
- Baris Sponsor Oktober (6 baris) ada di aplikasi tetapi belum di workbook, jadi totalnya berbeda dari Excel sampai workbook diperbarui.
- Di luar scope: PAM, BMG, Others; Report/HO Report membaca Append1 hasil bentukan; export Excel; menyelaraskan tab MR Sponsorship dengan aturan workbook.
