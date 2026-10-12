# General Ledger: Sync dari Excel dan 3 Sub Menu

Tanggal: 2026-10-12

## Tujuan

Menu General Ledger punya 3 sub menu (GL SMT, GL ETF, GL SETF). Tiap sub menu menarik data dari sheet yang sama namanya di `GL - MASTER.xlsb` lewat upload file, mengikuti pola sync Management Report, lalu menampilkannya dengan filter dan paginasi.

Sumber contoh: `Y:\Seagate\Management Report\2026\0926\GL - MASTER.xlsb` (sheet GL SMT ~14.500 baris, GL ETF ~2.400, GL SETF ~220).

## Keputusan

- Sync dengan **upload .xlsb**, tanpa Excel COM. Stub lama (`pythoncom`/`win32com`) dihapus.
- Penyimpanan **ganti penuh + log sync**, tanpa snapshot lengkap.
- Tampilan **sync + viewer dengan filter**, tanpa export Excel (di luar scope).
- Tab entitas tidak bergantung pada perusahaan di session.
- Tabel `GLSME` tidak dipakai di scope ini dan datanya tidak dihapus.

## Struktur

Modul `app/modules/general_ledger/`:

- `parser.py`: membaca sheet dengan `pyxlsb`, memetakan kolom berdasarkan header, membuang baris kosong, mengubah serial tanggal Excel menjadi tanggal.
- `sync.py`: hash isi dan ringkasan perubahan, mengikuti `management_report/sync.py`.
- `service.py`: query viewer (filter, paginasi, total) dan log sync.
- `routes.py`: halaman dan API.

Rute:

- `GET /general-ledger/` mengarah ke `/general-ledger/smt`.
- `GET /general-ledger/<smt|etf|setf>`: halaman tab.
- `POST /general-ledger/<smt|etf|setf>/sync`: upload .xlsb, hanya admin (`json_admin_required`).

## Alur sync

1. File diterima, harus berakhiran `.xlsb`.
2. Hanya sheet milik tab itu yang di-parse, sehingga tiap entitas bisa disinkronkan sendiri.
3. Hash isi dibandingkan dengan sync terakhir entitas tersebut.
4. Sama: balasan "Sudah sinkron", tabel tidak disentuh.
5. Berbeda: tabel diganti penuh dalam satu transaksi dan satu baris `gl_sync_log` ditulis. Kegagalan di tengah tidak boleh meninggalkan data setengah jadi.

## Data

Tabel `GLSMT`, `GLETF`, `GLSETF` dengan kolom tetap:

`entry_no`, `source_type` (kolom x1, mis. "GJ - Acrue"), `acc_statutory`, `acc_statutory_desc`, `acc_management`, `acc_management_desc`, `id_no`, `tgl`, `memo`, `debit`, `credit`, `job_name`, `job_desc`, `budget_activity`, `customer_vendor`, `allocation_memo`, `event`, `ket1`, `ket2`. Kolom Qty, UOM, Item, dan Harga Satuan diparse bila ada isinya. Kolom hitungan 44 sampai 49 tidak disimpan.

Tabel `gl_sync_log`: entitas, waktu, user, nama file, hash, baris sebelum dan sesudah, ringkasan tambah/hapus/ubah, total debit, total credit.

Pembersihan: baris tanpa ID# dan tanpa akun yang hanya berisi kolom hitungan (mis. baris 4 dan 7 di GL ETF) dibuang. Jumlahnya dicatat sebagai "dilewati".

Validasi:

- Header wajib (`Account Statutory`, `Date`, `Debit`, `Credit`, dan lainnya) harus ada. Kalau tidak, pesan galat yang jelas.
- Total debit harus sama dengan total credit hasil parse. Kalau berbeda, sync tetap jalan dengan peringatan.

## Tampilan

Tiap tab:

- Header: tombol "Upload & Sync .xlsb" (hanya admin), waktu sync terakhir, user terakhir.
- Kartu ringkasan: jumlah baris, total Debit, total Credit, selisih.
- Filter: rentang tanggal, akun (Statutory atau Management), Job Name, pencarian Memo/ID#.
- Tabel paginasi di server, 100 baris per halaman, Debit dan Credit berformat angka.
- Riwayat sync terakhir ringkas di bawah tabel.
- Mengikuti base template dan header terpadu seperti Management Report.

## Pengujian (pytest, pola `test_mr_*`)

- Parser: pemetaan kolom, pembuangan baris kosong, konversi tanggal, header salah.
- Sync: file sama memberi "tidak berubah", file berbeda memberi ringkasan benar, transaksi gagal tidak meninggalkan data setengah jadi.
- Service dan routes: filter, paginasi, hak akses admin, penolakan file bukan .xlsb.
- Satu uji dengan file asli (dilewati kalau file tidak ada): jumlah baris dan total debit/credit sesuai angka Control di Excel.
