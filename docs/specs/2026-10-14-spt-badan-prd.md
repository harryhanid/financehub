# SPT Tahunan PPh Badan — Product Requirements Document (PRD)

**Tanggal:** 2026-10-14
**Versi:** 0.4 (draft untuk review; semua mapping SPT dipusatkan di menu Pemetaan Management Report, Bagian 14.11)
**Modul:** `app/modules/spt_badan/` (baru), di dalam FLOW
**Entitas awal:** Sinar Mas Tjipta (SMT). ETF/SETF di fase berikutnya.
**Tahun uji:** TP 2026 (data GL Jan–Sep 2026, hasil berstatus *simulasi YTD*). TP 2025 menyusul setelah GL 2025 di-sync.
**Sumber analisis:** folder kerja `Y:\Seagate\Dicky\2025\1325\SPT 2025\SMT` (Tahun Pajak 2025, dilaporkan 22 April 2026 via Coretax)

---

## 1. Ringkasan

Saat ini SPT Tahunan PPh Badan disusun dari **rantai 7 workbook Excel** yang saling terhubung lewat link eksternal (total sekitar 100 MB). Urutan kerjanya tidak tertulis, file dari 2019–2024 masih menjadi dependensi, dan data GL harus di-copy-paste dari MYOB/GL setiap tahun.

Modul **SPT Badan** di FLOW menggantikan rantai itu dengan satu alur terpandu:

1. mengambil GL tahun pajak langsung dari modul **General Ledger** FLOW (bukan upload TB/GL manual),
2. memakai **pemetaan akun** dari modul Management Report/GL (Category LK, Category SPT, jenis PPh),
3. menghitung Laporan Keuangan, rekonsiliasi fiskal, PKP dan PPh terutang secara otomatis,
4. menghasilkan lampiran dan lembar isian untuk Coretax, dengan kontrol dan audit trail di tiap langkah.

## 2. Masalah (kondisi sekarang / as-is)

| # | Masalah | Bukti dari kertas kerja |
|---|---|---|
| P1 | Alur sirkular dan tidak terdokumentasi | File 01 membaca 02 dan 07; 02 dan 07 membaca balik 01 |
| P2 | Dependensi usang dan tidak portabel | File 02 masih menunjuk ke `Management Report 1319`, `Statutory Report - MASTER.xlsb`, `Tommy\MYOB\2019`, `C:\Users\79800017\Downloads\...` |
| P3 | Copy-paste GL/TB tiap tahun | File 11 `TB SMT 2025 - SPT` berisi sheet GL 2020 sampai 2025 yang disalin manual |
| P4 | Mapping tersebar dan sebagian hardcode | VLOOKUP berantai ke COA/Lookup; nilai manual seperti `AA10 = 10.000.000.000`, `E13 = 15.2216*1000000` |
| P5 | Banyak versi, tidak jelas yang final | 3 versi TB, 4 versi Fin Statement, 2 versi 1771 |
| P6 | Angka antar tempat tidak konsisten | Penghasilan neto fiskal: Coretax 6.395.119.807 vs workbook 6.395.118.000. Blok "Perhitungan 1771" memuat skenario fasilitas Pasal 31E (PPh 1,359 M) padahal yang dilaporkan memakai tarif umum 22% (PPh 1.406.926.180) |
| P7 | Kontrol manual | Crosscheck ada tersebar di kolom samping tiap sheet, tidak ada ringkasan lulus/gagal |
| P8 | Tidak ada jejak perubahan | File final dan perubahan setelah lapor (mis. "Update PPh 25", 22 Jul 2026) tidak terpisah |

## 3. Tujuan dan bukan tujuan

**Tujuan**
- G1. Hasil hitung SPT TP 2025 SMT **identik** dengan yang sudah dilaporkan (Bagian 10.1, golden test). Sampai GL 2025 tersedia, alur diuji dengan TP 2026 memakai kontrol internal (Bagian 10.2).
- G2. Tidak ada copy-paste GL: sumber data tunggal adalah modul General Ledger.
- G3. Satu sumber pemetaan akun, dikelola di FLOW, bukan di sheet.
- G4. Setiap angka SPT bisa ditelusuri (drill-down) sampai baris GL.
- G5. Tahun pajak baru bisa dikerjakan dengan mengubah parameter, bukan menyalin workbook.

**Bukan tujuan (fase ini)**
- Submit/e-Filing otomatis ke Coretax (hanya menghasilkan lembar isian dan PDF pendukung).
- Pengganti sistem akuntansi atau MYOB.
- Lampiran transfer pricing (10A–10D) dan CbCR (hanya disimpan sebagai input manual/lampiran).
- Entitas ETF/SETF (menyusul setelah SMT lulus golden test).

## 4. Pengguna

| Peran | Kebutuhan |
|---|---|
| **Preparer pajak/akuntan** | Menjalankan langkah, memberi koreksi fiskal, melihat selisih |
| **Reviewer (Finance Manager)** | Melihat ringkasan kontrol, drill-down, menyetujui versi final |
| **Admin** | Mengelola pemetaan, parameter tahun pajak, mengunci periode |

Akses mengikuti sistem role FLOW yang ada (`auth/middleware.py`), aksi tulis oleh admin atau preparer, finalisasi oleh reviewer.

## 5. Alur kerja kertas kerja saat ini (as-is)

```
MYOB/GL ─► [11 TB SMT - SPT]  GL 2025, GL SPT, TB SPT, sd2025
                │
Sources: Pajak 2025 (PPh21/23/4(2)/PPN/PPh25), Rekap RD, LR accrue vs non-accrue
                │
                ▼
[02 Fin Statement]  GL Before Accrue + GL Accrue DQ ─► GL After Accrue ─► GL
   tiap baris GL diberi Category LK + Category SPT lewat VLOOKUP ke COA
   penyesuaian: GL Sewa, GL Selisih, GL Service, ELIM, GL PPh Ditanggung PT
                │  ─► LAPORAN KEUANGAN (neraca + laba rugi)
                ├─► [07 Rincian SPT]  GL dipecah DPP / PPh 21,23,4(2) / Non-PPh
                ├─► List Account Changes ─► Summary (reklas 11 pos biaya)
                ├─► [04 Bunga Bank]   ├─► [05 Fixed Assets]
                ▼
[01 Formulir 1771]  II (rincian HPP+biaya) ─► I (neto fiskal) ─► Perhitungan (PKP, PPh)
                │
                ▼
[03 Lampiran Khusus] 1A, 2A, 3A, 4A, 5A, 6A, 7A, 8A-1..8
                │
                ▼
SPT Coretax (PDF) + Neraca & LK (PDF)
```

## 6. Alur target (to-be) — langkah terpandu

Modul menyediakan **wizard 10 langkah** per (entitas, tahun pajak). Tiap langkah punya status (`Belum`, `Berjalan`, `Perlu review`, `Lulus`), kontrol otomatis, dan hanya bisa dilanjutkan bila kontrol wajib lulus.

```mermaid
flowchart TD
  A[0. Buat Periode SPT<br/>entitas + tahun pajak + parameter] --> B[1. Tarik GL tahun pajak<br/>dari modul General Ledger]
  B --> C[2. Validasi pemetaan akun<br/>Category LK/SPT, jenis PPh]
  C --> D[3. Penyesuaian akrual & reklas<br/>GL Accrue, Sewa, Selisih, Service, ELIM]
  D --> E[4. Laporan Keuangan<br/>neraca + laba rugi + crosscheck]
  E --> F[5. Rekonsiliasi pajak dipotong<br/>PPh 21/23/4(2)/PPN vs GL]
  F --> G[6. Rincian 1771-II<br/>reklas 11 pos biaya, HPP vs Biaya Usaha]
  G --> H[7. Koreksi fiskal 1771-I<br/>positif/negatif + penyusutan fiskal + final]
  H --> I[8. PKP & PPh terutang<br/>tarif, kredit pajak, PPh 25]
  I --> J[9. Lampiran khusus<br/>1A, 3A, 4A, 8A dst.]
  J --> K[10. Review, kunci versi, ekspor<br/>lembar Coretax + PDF + paket arsip]
```

### 6.1 Rincian langkah

| # | Langkah | Input | Proses otomatis | Input manual | Output | Kontrol wajib |
|---|---|---|---|---|---|---|
| 0 | Periode SPT | Entitas, TP, tanggal buku, NPWP/identitas | Salin parameter dari TP sebelumnya | Identitas WP, kuasa, KLU | Record periode | Identitas lengkap |
| 1 | Tarik GL | `GLSMT/GLETF/GLSETF` (tabel modul GL) untuk 1 Jan–31 Des TP | Filter tanggal, snapshot dengan hash isi | Saldo awal (RE tahun lalu) bila belum ada | Snapshot GL terkunci per versi | Total debit = total kredit; jumlah baris sama dengan modul GL; tidak ada baris di luar TP |
| 2 | Validasi klasifikasi GL | Kolom GL: `category_lk`, `category_spt`, `pph_non_pph`, `accrual_actual` | Normalkan nilai (huruf besar/kecil, alias), tandai baris biaya tanpa Category SPT, jenis PPh bernilai tidak valid (mis. kode cost center) | Koreksi di sumber (GL/pemetaan) lalu sync ulang | Daftar pengecualian klasifikasi = 0 | Semua baris laba rugi punya Category SPT; semua `pph_non_pph` ∈ nilai baku |
| 3 | Penyesuaian & reklas *(accrue ditunda)* | Snapshot GL, GL Sewa/Selisih/Service, eliminasi | **Fase awal:** hanya jurnal penyesuaian manual dan eliminasi. Aturan accrue (GL Accrue DQ, DPP accrue tahun lalu) ditambahkan kemudian | Jurnal penyesuaian khusus (dengan keterangan) | GL setelah penyesuaian | Total penyesuaian tercatat; selisih nol |
| 4 | Laporan Keuangan | GL setelah penyesuaian | Agregasi per Category LK; saldo awal neraca dari TP lalu | Penyesuaian khusus SPT (mis. eliminasi) | Neraca + laba rugi | Neraca seimbang; cocok dengan Statutory/laporan keuangan (selisih ditampilkan) |
| 5 | Rekonsiliasi pajak | Data pajak (PPh 21/23/4(2)/PPN/PPh 25), GL akun pajak | Pecah DPP/PPh per masa dan jenis, cocokkan dengan GL | Impor bukti potong/ekspor Coretax | Rekap per masa, kredit pajak, selisih | DPP & PPh per jenis cocok dengan GL (toleransi dapat diatur) |
| 6 | Rincian 1771-II | GL setelah penyesuaian + pemetaan | Reklas ke 11 pos biaya, pisah HPP dan Biaya Usaha Lainnya, biaya luar usaha | Reklas khusus | Formulir 1771-II | `Σ 1771-II = Laporan Laba Rugi` (HPP, biaya usaha, luar usaha) |
| 7 | Koreksi fiskal 1771-I | LK, rincian 1771-II, register aset, daftar biaya non-deductible | Hitung penyusutan komersial vs fiskal, PPh ditanggung PT, bunga/final dipisah | Sumbangan, representasi, sanksi, dll. dengan dasar | Formulir 1771-I, neto fiskal | Setiap koreksi punya keterangan dan dasar; total positif/negatif tampil |
| 8 | PKP & PPh | Neto fiskal, kompensasi rugi, kredit pajak, PPh 25 | Hitung PKP (dibulatkan ribuan), tarif Pasal 17 atau Pasal 31E sesuai pilihan, kurang/lebih bayar | Pilihan tarif, fasilitas | Perhitungan 1771 | Pilihan tarif eksplisit dan dicatat alasannya |
| 9 | Lampiran khusus | Hasil langkah 1–8, aset tetap, bunga/RD | Isi Lampiran 1A, 3A, 4A, 8A dst. dari data | Lampiran yang butuh isian manual | Set lampiran | Setiap lampiran wajib terisi atau ditandai "tidak berlaku" |
| 10 | Review & ekspor | Seluruh hasil | Rekap kontrol, perbandingan dengan versi sebelumnya, kunci versi | Persetujuan reviewer | Lembar isian Coretax, PDF LK, paket arsip (xlsx + PDF) | Semua kontrol wajib lulus; reviewer menyetujui |

## 7. Kebutuhan fungsional

**Sumber data**
- FR-01. Modul membaca GL dari tabel modul General Ledger (`GLSMT`, `GLETF`, `GLSETF`). **Tidak ada** upload TB/GL terpisah. Penyimpanan GL bersifat **multi-tahun** pada tabel yang sama; tahun berjalan di-sync berkala, tahun lampau tetap tersimpan. Tahun pajak dipilih dari rentang `tgl`.
- FR-02. Saat langkah 1 dijalankan, sistem menyimpan **snapshot** (hash isi + jumlah baris + total) agar hasil SPT tidak berubah bila GL disinkronkan ulang. Bila GL berubah setelah snapshot, tampilkan banner "GL berubah, jalankan ulang dari langkah 1".
- FR-03. **Category SPT, Category LK, jenis PPh (`pph_non_pph`) dan `accrual_actual` dibaca dari kolom GL** (sudah ada di tabel `GLSMT/GLETF/GLSETF`). Modul SPT tidak menghitung ulang klasifikasi, tetapi **memvalidasi** dan **menormalkan** nilainya (lihat Bagian 9). Pemetaan akun di modul Pemetaan dipakai sebagai pembanding/pelengkap, bukan sumber kedua.

**Perhitungan**
- FR-04. Laporan Keuangan dibentuk dari agregasi Category LK; saldo awal neraca dari penutupan tahun pajak sebelumnya (bukan VLOOKUP ke file lama).
- FR-05. Rekonsiliasi pajak per masa (Jan–Des) dan jenis (PPh 21, 23, 4(2), PPN), menampilkan DPP, PPh, selisih dengan GL.
- FR-06. 1771-II dan 1771-I dihasilkan dari data, bukan diketik; setiap sel dapat di-drill-down sampai baris GL.
- FR-07. Koreksi fiskal manual disimpan sebagai entri (`jenis`, `pos 1771-I`, `jumlah`, `keterangan`, `dasar`, `dibuat oleh`), dengan lampiran dokumen opsional.
- FR-08. Penyusutan fiskal dihitung dari register aset (golongan, masa manfaat, metode) dan dibandingkan dengan penyusutan komersial.
- FR-09. Perhitungan PKP dan PPh mendukung tarif Pasal 17 dan Pasal 31E; **pilihan tarif harus eksplisit**. Untuk Pasal 31E, sistem memvalidasi syarat peredaran bruto (≤ Rp50 miliar) sebelum mengizinkan.
- FR-10. Kredit pajak (PPh 22/23/24), PPh 25 dan hasil kurang/lebih bayar dihitung dan dibandingkan dengan data bukti potong.

**Kontrol dan audit**
- FR-11. Setiap langkah punya daftar kontrol dengan status lulus/gagal, nilai kiri/kanan, selisih, dan toleransi. Halaman ringkasan menampilkan semuanya.
- FR-12. **Versi dan penguncian**: periode dapat dikunci sebagai versi final; perubahan sesudahnya menjadi versi baru (Versi 2, pembetulan) dengan perbandingan angka terhadap versi sebelumnya.
- FR-13. Log aktivitas: siapa mengubah apa dan kapan (koreksi, pilihan tarif, penguncian).

**Ekspor**
- FR-14. Ekspor lembar isian per bagian Coretax (induk A–J, Lampiran 1, 3, 4, 8 dst.) dalam xlsx, dengan urutan kolom sama dengan layar Coretax.
- FR-15. Ekspor Laporan Keuangan (neraca + laba rugi) ke PDF dan xlsx dengan format yang sekarang dipakai.
- FR-16. Paket arsip per versi: seluruh xlsx hasil, PDF, daftar kontrol, dan log perubahan.

## 8. Model data (usulan)

| Tabel | Isi | Kunci |
|---|---|---|
| `spt_period` | Entitas, tahun pajak, status, versi aktif, identitas WP, parameter | `(entity, tax_year)` |
| `spt_version` | Versi 1, 2, ... dengan status (draft / final / pembetulan), pembuat, waktu | `period_id, no` |
| `spt_gl_snapshot` | Hash GL, jumlah baris, total debit/kredit, versi pemetaan | `version_id` |
| `spt_gl_line` | Salinan baris GL terpilih + hasil klasifikasi (category_lk, category_spt, jenis_pph, accrual) | `snapshot_id` |
| `spt_adjustment` | Jurnal penyesuaian/reklas (akrual, ELIM, sewa) dengan keterangan | `version_id` |
| `spt_tax_withheld` | Data pajak dipotong per masa (jenis, DPP, PPh, bukti potong) | `version_id` |
| `spt_fiscal_correction` | Koreksi fiskal positif/negatif per pos 1771-I | `version_id` |
| `spt_asset_fiscal` | Register aset + penyusutan komersial dan fiskal | `version_id` |
| `spt_result` | Nilai hasil tiap sel formulir (kode sel, nilai, asal) untuk drill-down dan ekspor | `version_id, form, cell` |
| `spt_control` | Hasil kontrol per langkah (nama, kiri, kanan, selisih, status) | `version_id` |
| `spt_activity_log` | Log aktivitas | — |

Konvensi mengikuti modul lain: tabel di `finance_hub.db`, `ensure_schema(conn)`, backup sebelum migrasi (lihat pola `finance_hub.db.bak-*`).

## 9. Ketergantungan pada pekerjaan yang sedang berjalan

Hasil pemeriksaan database FLOW (14 Okt 2026), setelah jawaban pemilik proses:

| Temuan | Dampak | Tindakan |
|---|---|---|
| Tabel `GLSMT` baru berisi **2026-01-01 s.d. 2026-09-30** (8.898 baris); GL 2025 belum ada | SPT TP 2025 belum bisa dijalankan | Sync GL 2025 ke tabel yang sama. Karena penyimpanan multi-tahun, sync **tidak boleh** menghapus tahun lain: ganti penuh per tahun atau per rentang tanggal, bukan `DELETE FROM` seluruh tabel seperti sekarang (`general_ledger/service.py:replace_all`) |
| `category_spt` kosong pada 4.528 dari 8.898 baris | **Wajar.** Seluruhnya akun neraca (kas, aktiva lancar lain, hutang usaha, hutang pajak, akumulasi penyusutan, piutang lain-lain, uang muka, aktiva tetap) dan pendapatan jasa; tidak butuh Category SPT. Semua baris biaya sudah terisi | Aturan validasi: wajib hanya untuk baris dengan `category_lk` laba rugi (HPP, Beban Operasional, Pendapatan/Beban Lainnya, Bunga Jasa Giro, Income Tax Expense) |
| `pph_non_pph` tidak bersih: ada `POSENG`, `$POITEC`, `TFKHAR`, `$POCSOS`, `$TFECEM` (kode cost center masuk kolom PPh), variasi huruf (`non pph`, `pph 23`), dan kosong pada 833 baris BIAYA LAINNYA, 593 baris penyusutan, 269 baris transportasi | DPP/PPh per jenis akan salah bila dipakai apa adanya | Langkah 2 menormalkan ke nilai baku {`PPh 21`, `PPh 23`, `PPh 4(2)`, `Non PPh`} dan menandai sisanya sebagai pengecualian. Perbaikan permanen di sumber (GL - MASTER) |
| Kolom `pph` hampir kosong (hanya 8 baris `PPh 23`) | Tidak bisa dipakai | Pakai `pph_non_pph` sebagai jenis PPh; kolom `pph` diabaikan sampai ada definisi |
| `accrual_actual` sudah ada (Accrual 1.454, Actual 7.444); `source_type` memuat jurnal accrue (mis. `GJ - Acrue`) | Dasar untuk aturan accrue nanti | Aturan accrue ditunda ke fase tersendiri (F2b); lihat Bagian 12 |
| `gl_cc_map` kosong (0 baris) | Reklas HPP vs Biaya Usaha Lainnya bergantung pada cost center | Isi pemetaan cost center di modul Pemetaan, atau tetapkan bahwa reklas memakai kolom GL lain |

Bagian lain yang bukan GL dan perlu sumber baru: data pajak dipotong (`Pajak 2025.xlsx`, saat ini file Excel dengan link ke `Downloads` pribadi), register aset (`05 List of Fixed Assets`), rekap bunga bank dan reksa dana. Rencana awal: impor xlsx/CSV dengan validasi; integrasi langsung menyusul.

## 10. Kriteria penerimaan

### 10.1 Golden test TP 2025 SMT (menunggu GL 2025)

Hasil modul untuk SMT TP 2025 harus sama dengan SPT yang **telah dilaporkan** (Coretax 22 Apr 2026, `2025 - SPT Badan - Coretax - SINAR MAS TJIPTA.pdf`) dan `NERACA & LAPORAN KEUANGAN SMT 2025.pdf`:

| Pos | Nilai acuan |
|---|---|
| Pendapatan bersih | 69.300.075.000 |
| Harga pokok penjualan | 52.988.703.528 |
| Biaya operasional | 9.944.506.104 |
| Laba operasional | 6.366.865.368 |
| Pendapatan (beban) lain bersih | 1.635.181.103 |
| Laba sebelum pajak | 8.002.046.471 |
| Penghasilan neto fiskal (Coretax induk, angka 4/7) | 6.395.119.807 |
| Penghasilan kena pajak (angka 9) | 6.395.119.000 |
| Tarif | Pasal 17 ayat (1) huruf b (22%) |
| PPh terutang (angka 12) | 1.406.926.180 |
| Kredit pajak (angka 13) | 1.386.001.500 |
| Angsuran PPh 25 (angka 14) | 14.272.802 |
| PPh kurang bayar (angka 17) | 6.651.878 |
| Total aktiva / total kewajiban+ekuitas | 24.730.953.663 |

Catatan: nilai penghasilan neto fiskal di workbook `Perhitungan 1771` (6.395.118.000) berbeda Rp1.807 dari yang dilaporkan, dan file `02 ... Update PPh 25` diubah 22 Jul 2026 setelah pelaporan. Yang dipakai sebagai acuan adalah **angka yang dilaporkan**. Selisih ini perlu dijelaskan pemilik proses (lihat Bagian 12).

### 10.2 Uji TP 2026 (simulasi YTD, berlaku sekarang)

Tahun 2026 belum penuh dan belum ada SPT yang dilaporkan, sehingga tidak ada angka acuan eksternal. Kebenaran diuji lewat kontrol internal:
- Total debit = total kredit pada snapshot GL; jumlah baris dan total sama dengan modul GL pada tahun itu.
- Setiap baris HPP/biaya punya Category SPT; setiap `category_lk` dikenali (laba rugi atau neraca).
- Laba rugi komersial YTD sama dengan jumlah `debit_credit` GL untuk kategori laba rugi.
- Setiap angka laporan dapat di-drill-down ke baris GL, dan jumlah baris drill-down sama dengan angka yang ditampilkan.
- Hasil ditandai **Simulasi YTD (Jan–Sep 2026)**, bukan SPT final.

### 10.3 Kriteria tambahan
- Seluruh kontrol wajib lulus tanpa override.
- Setiap angka induk dapat di-drill-down ke baris GL.
- Waktu hitung ulang penuh untuk 1 tahun pajak < 60 detik.

## 11. Fase pengerjaan (usulan)

| Fase | Isi | Hasil |
|---|---|---|
| **F0** | Prasyarat: GL 2025 ada di modul GL (sync multi-tahun yang tidak menimpa tahun lain); cost center terpetakan | Data siap |
| **F1** | Periode SPT, snapshot GL, validasi klasifikasi, laba rugi komersial YTD, halaman kontrol (langkah 0–2 dan bagian laba rugi langkah 4). Desain di Bagian 14 | Angka laba rugi 2026 yang dapat ditelusuri |
| **F2** | Penyesuaian manual, Laporan Keuangan, 1771-II (langkah 3, 4, 6) | LK cocok dengan PDF |
| **F2b** | Aturan accrue (GL Accrue DQ, DPP accrue tahun lalu) | Replikasi akrual workbook; ditentukan kemudian |
| **F3** | Rekonsiliasi pajak, koreksi fiskal, PKP/PPh (langkah 5, 7, 8) | Induk SPT cocok dengan Coretax |
| **F4** | Lampiran khusus, penyusutan fiskal, ekspor, penguncian versi (langkah 9, 10) | Paket final |
| **F5** | Ulangi untuk ETF/SETF, tahun pajak berikutnya | Multi-entitas |

## 12. Keputusan dan pertanyaan terbuka

**Sudah diputuskan (14 Okt 2026)**
- D1. Penyimpanan GL **multi-tahun** pada tabel yang sama; tahun berjalan di-sync berkala.
- D2. Category SPT dan jenis PPh **sudah ada di kolom GL**. Sejak 14 Okt 2026 (sore), seluruh mapping kategori dipusatkan di menu Pemetaan Management Report dan SPT membacanya dari sana (Bagian 14.11); kolom GL hanya dibandingkan.
- D3. Aturan accrue **ditunda**; ditentukan nanti sebagai F2b.

**Masih terbuka**
1. **Perbaikan `pph_non_pph` di sumber.** Siapa yang membersihkan kode cost center dan nilai kosong di GL - MASTER, atau cukup dinormalkan oleh modul SPT?
2. **Baris biaya tanpa jenis PPh** (kosong): apakah diperlakukan sebagai `Non PPh`, atau memang harus diisi per transaksi?
3. **Selisih Rp1.807** antara Perhitungan 1771 dan angka Coretax: pembulatan sengaja atau perbedaan versi file?
4. **Pasal 31E**: sheet menghitung skenario fasilitas, padahal peredaran bruto Rp69,3–70,9 miliar (> Rp50 miliar) dan yang dilaporkan memakai tarif umum. Konfirmasi bahwa skenario itu tidak dipakai.
5. **Koreksi fiskal** TP 2025 hanya sumbangan Rp32,11 juta dan PPh ditanggung PT. Apakah memang tidak ada koreksi lain (representasi, natura)?
6. **Sumber data pajak dipotong** (`Pajak 2025.xlsx`): berasal dari ekspor Coretax? Bisa diimpor langsung?
7. **Lampiran** yang wajib untuk SMT (1A, 3A, 4A, 8A dst.): daftar final untuk menentukan cakupan F4.
8. **Peran**: siapa preparer, reviewer, penandatangan per entitas?
9. ~~Cost center~~: `gl_cc_map` sekarang terisi 89 baris; masih perlu dipastikan kelengkapannya untuk F2.
10. **Sumber sync Pemetaan** untuk kolom kategori: `Category LK` / `Category SPT` ada di sheet `COA` milik `GL - MASTER.xlsb`, sedangkan Pemetaan sekarang membaca `Management Report - MASTER.xlsb`. Sync dari dua file, atau satu file saja (mana)?
11. **Nilai `TBA`** pada `Category LK` / `Category SPT`: diperlakukan sebagai belum dipetakan (usulan), atau ada makna lain?

## 13. Risiko

| Risiko | Mitigasi |
|---|---|
| Aturan perpajakan berubah antar tahun (tarif, lampiran Coretax) | Parameter per tahun pajak, aturan ditulis sebagai data, bukan kode |
| Pemetaan akun belum lengkap menghasilkan angka salah | Langkah 2 memblokir bila ada akun bersaldo yang belum terpetakan |
| GL berubah setelah SPT dihitung | Snapshot berhash, banner peringatan, versi terkunci |
| Selisih kecil (pembulatan) membuat kontrol selalu gagal | Toleransi per kontrol, tampilkan selisih dan alasannya |
| Format Coretax berubah | Ekspor dipisah dalam lapisan template yang mudah diganti |
| Satu orang memegang seluruh pengetahuan proses | Alur wizard dan log aktivitas mendokumentasikan proses |

## 14. Desain F1 (TP 2026, simulasi YTD)

### 14.1 Ruang lingkup F1
1. Periode SPT per (entitas, tahun pajak) beserta parameter dan identitas WP.
2. Snapshot GL tahun pajak dari tabel modul General Ledger, dengan hash dan peringatan bila GL berubah sesudahnya.
3. Validasi dan normalisasi klasifikasi (`category_lk`, `category_spt`, `pph_non_pph`) dengan daftar pengecualian.
4. Laporan laba rugi komersial YTD dari `category_lk`, dengan drill-down ke baris GL.
5. Halaman ringkasan kontrol per langkah.

Di luar F1: neraca, akrual, rekonsiliasi pajak, 1771-II/I, PKP, lampiran, ekspor, penyusutan fiskal.

### 14.2 Modul dan akses
- Paket baru `app/modules/spt_badan/`: `routes.py`, `service.py` (periode, snapshot, kontrol), `classify.py` (normalisasi dan validasi, fungsi murni), `income_statement.py` (agregasi laba rugi, fungsi murni), dengan test terpisah.
- Terdaftar di `app.py` dan daftar modul dashboard (`modules/dashboard/routes.py`) dengan label "SPT Badan".
- Akses F1: lihat untuk pengguna login; buat periode, ambil snapshot dan ubah parameter hanya admin (`json_admin_required`), mengikuti General Ledger. Peran preparer/reviewer ditunda sampai F4.
- Entitas F1 hanya SMT; struktur menerima ETF/SETF tanpa perubahan skema.
- **Semua mapping yang dibutuhkan SPT dipusatkan di menu Pemetaan Management Report** (`/management-report/pemetaan`) dan dibaca dari sana; modul SPT tidak menyimpan daftar kategori sendiri (Bagian 14.11).

### 14.3 Tabel F1 (`finance_hub.db`, `ensure_schema`, backup sebelum migrasi pertama)

| Tabel | Kolom utama |
|---|---|
| `spt_period` | `id`, `entity`, `tax_year`, `status` (`draft`), `label` (mis. "Simulasi YTD"), `params` (JSON: identitas WP, KLU, periode pembukuan), `created_at`, `created_by`; unik `(entity, tax_year)` |
| `spt_snapshot` | `id`, `period_id`, `taken_at`, `taken_by`, `gl_hash` (hash isi sync GL terakhir tahun itu), `row_count`, `total_debit`, `total_credit`, `date_min`, `date_max`, `is_current` |
| `spt_gl_line` | `snapshot_id`, `gl_id`, `tgl`, `id_no`, `acc_statutory`, `acc_management`, `job_name`, `memo`, `debit_credit`, `category_lk`, `category_spt`, `pph_type_raw`, `pph_type` (hasil normalisasi), `accrual_actual` |
| `spt_exception` | `snapshot_id`, `gl_id`, `kind`, `severity` (`blocker` / `warning`), `detail` |
| `spt_control` | `snapshot_id`, `code`, `name`, `left_value`, `right_value`, `diff`, `status` (`lulus` / `gagal` / `peringatan`), `blocking` |

Snapshot lama disimpan paling banyak 3 per periode; hanya satu yang `is_current`. Snapshot baru menandai yang lama non-aktif dan tidak mengubah GL.

### 14.4 Alur snapshot
1. Admin menekan **Ambil snapshot GL**.
2. Sistem membaca baris GL entitas pada tahun pajak, menghitung total serta tanggal awal/akhir, dan mengambil `content_hash` sync GL terakhir untuk tahun itu (`gl_sync_log`).
3. Setiap baris diklasifikasikan memakai Pemetaan (14.5), dicek, lalu disimpan ke `spt_gl_line`, `spt_exception`, dan `spt_control` dalam satu transaksi. Gagal di tengah tidak meninggalkan snapshot setengah jadi.
4. Bila sync GL tahun itu berubah setelah snapshot (hash berbeda), halaman periode menampilkan banner **"GL berubah sejak snapshot, ambil snapshot ulang"** dan hasil ditandai usang.

### 14.5 Normalisasi dan validasi klasifikasi
Aturan berupa fungsi murni di `classify.py`, diuji tanpa database.

**Jenis PPh (`pph_non_pph` → `pph_type`)**: pangkas spasi dan abaikan huruf besar/kecil.

| Nilai mentah | Hasil |
|---|---|
| `PPh 21`, `pph 21` | `PPh 21` |
| `PPh 23`, `pph 23` | `PPh 23` |
| `PPh 4(2)`, `pph 4 (2)`, `PPh4(2)` | `PPh 4(2)` |
| `Non PPh`, `non pph`, `non-pph` | `Non PPh` |
| kosong, pada baris biaya | pengecualian `pph_kosong` (**warning**), `pph_type` dikosongkan |
| kode lain (mis. `POSENG`, `$POITEC`, `TFKHAR`) | pengecualian `pph_bukan_jenis` (**warning**), `pph_type` dikosongkan |
| kosong, pada baris neraca/pendapatan | diabaikan |

Pengecualian PPh berstatus *warning* karena sumbernya (GL - MASTER) belum bersih dan penanganan baris kosong masih terbuka (Bagian 12 no. 1–2). F2 (rekonsiliasi pajak) menaikkannya menjadi *blocker*.

**Kategori (bersumber dari Pemetaan)**
- Klasifikasi baris GL = hasil *lookup* akun (`acc_statutory`, per sumber SMT/ETF) ke Pemetaan: `category_lk`, `category_spt`, `categories_expense`. Nilai pada kolom GL tidak dipakai sebagai sumber, hanya dibandingkan (kontrol C9).
- Apakah suatu `category_lk` termasuk **Neraca** atau **Laba rugi**, urutan tampil, dan labelnya diambil dari daftar *Kategori LK* di Pemetaan (14.11), bukan dari kode.
- Akun yang tidak ada di Pemetaan, atau bernilai kosong / `TBA` / `tba` → pengecualian `akun_belum_dipetakan` (**blocker**).
- `category_lk` yang ada di Pemetaan tetapi belum ada di daftar *Kategori LK* → pengecualian `category_lk_tidak_dikenal` (**blocker**).
- Baris dengan `category_lk` berjenis Laba rugi bukan Pendapatan/Bunga/Income tax (yaitu HPP, Beban Operasional, Pendapatan (Beban) Lainnya) dan `category_spt` kosong atau `TBA` → pengecualian `category_spt_kosong` (**blocker**).
- Pengecekan nyata terhadap `GL - MASTER.xlsb` (sheet COA, 592 akun): `Category LK` terisi di 511 akun, `Category SPT` di 267 akun, dan sebagian bernilai `TBA`. Untuk 8.898 baris GL SMT 2026, hasil lookup akun **cocok 100%** dengan kolom GL.

### 14.6 Laba rugi komersial YTD
Agregasi dari `spt_gl_line` snapshot aktif. Pendapatan ditampilkan positif (−`debit_credit`), beban positif (+`debit_credit`).

| Baris | Sumber |
|---|---|
| Pendapatan bersih | `Jasa Konsultasi & Advokasi` |
| Harga pokok penjualan | `HARGA POKOK PENJUALAN` |
| Laba kotor | pendapatan − HPP |
| Biaya operasional | `Beban Operasional` |
| Laba operasional | laba kotor − biaya operasional |
| Pendapatan (beban) lainnya | `Pendapatan (Beban) Lainnya` |
| Bunga jasa giro | `Bunga Jasa Giro` |
| Laba sebelum pajak | laba operasional + lainnya + bunga |
| Income tax expense | `Income Tax Expense` |
| Laba bersih | laba sebelum pajak − income tax expense |

Struktur dan label mengikuti `LAPORAN KEUANGAN` di workbook (lihat `NERACA & LAPORAN KEUANGAN SMT 2025.pdf`); pengelompokan baris diambil dari daftar *Kategori LK* di Pemetaan. Rincian HPP dan biaya per `category_spt` tampil sebagai sub-baris. Klik angka membuka daftar baris GL pembentuknya (filter kategori, paginasi), dengan total yang sama persis.

### 14.7 Kontrol F1

| Kode | Kontrol | Sifat |
|---|---|---|
| C1 | Total debit = total kredit pada snapshot (toleransi Rp1) | blocker |
| C2 | Jumlah baris dan total snapshot = baris dan total modul GL pada tahun itu | blocker |
| C3 | Semua akun bersaldo terpetakan dan `category_lk`-nya dikenal (tanpa kosong / `TBA`) | blocker |
| C4 | Tidak ada baris HPP/biaya tanpa `category_spt` | blocker |
| C5 | Semua tanggal snapshot berada di tahun pajak | blocker |
| C6 | Laba sebelum pajak = jumlah negatif `debit_credit` baris laba rugi sebelum income tax | blocker |
| C7 | Jenis PPh bersih (tanpa `pph_kosong` / `pph_bukan_jenis`) | peringatan |
| C8 | Snapshot masih sesuai sync GL terakhir (hash) | peringatan |
| C9 | `category_lk` / `category_spt` pada baris GL = hasil Pemetaan | peringatan |

### 14.8 Tampilan
- `GET /spt-badan/`: daftar periode dan tombol **Buat periode** (admin).
- `GET /spt-badan/<id>`: ringkasan langkah (status per langkah), banner usang, kartu ringkasan (baris GL, rentang tanggal, laba sebelum pajak), tombol **Ambil snapshot GL**.
- `GET /spt-badan/<id>/pengecualian`: daftar pengecualian dengan filter jenis, tingkat, dan pencarian; dapat diunduh xlsx untuk dikirim ke pemilik sumber GL.
- `GET /spt-badan/<id>/laba-rugi`: laporan laba rugi + drill-down.
- `GET /spt-badan/<id>/kontrol`: tabel kontrol C1–C9.
- Gaya mengikuti modul lain (unified header, tab modul, paginasi dinamis).

### 14.9 Pengujian
- `classify.py` dan `income_statement.py`: unit test murni (tabel nilai mentah → hasil, tanda pendapatan/beban, label baris).
- Servis: snapshot atomik (gagal di tengah tidak menyisakan data), snapshot ulang menonaktifkan yang lama, deteksi usang saat sync GL berubah, batas 3 snapshot.
- Route: akses admin vs non-admin, validasi tahun/entitas, 404 periode tidak ada.
- Integrasi: periode SMT 2026 dari data uji kecil, kontrol C1–C9 dihitung benar; total drill-down = angka laporan.

### 14.10 Risiko khusus F1
- Pengecualian `pph_*` jumlahnya besar (±2.200 baris kosong) dan dapat membanjiri tampilan; daftar dikelompokkan per akun dan job, bukan hanya per baris.
- Bergantung pada label kategori dari sumber yang belum bersih: perubahan label di GL - MASTER membuat C3 gagal; ini disengaja agar terdeteksi.
- Angka 2026 tidak dapat diverifikasi eksternal; label **Simulasi YTD** wajib tampil di setiap halaman dan ekspor.

### 14.11 Kebutuhan pada menu Pemetaan Management Report

Menu Pemetaan (`/management-report/pemetaan`) menjadi **satu-satunya tempat** mapping yang dipakai SPT. Saat ini menu itu hanya memuat akun → `coa_ho`, `category` (CATEGORIES 2), `code`, dan cost center, dibaca dari sheet `COA` dan `CC` pada `Management Report - MASTER.xlsb`. Yang perlu ditambahkan:

| # | Mapping | Isi | Sumber data | Pengelolaan |
|---|---|---|---|---|
| M1 | **Akun → kategori** | Tambah kolom `category_lk`, `category_spt`, `categories_expense` pada `gl_coa_map` (kunci: sumber SMT/ETF + akun) | Sheet `COA` pada `GL - MASTER.xlsb` (kolom *CATEGORIES EXPENSE (6-****)*, *Category LK*, *Category SPT*). Sheet `COA` pada `Management Report - MASTER.xlsb` tidak memuat kolom ini | Sync dari Excel, mengikuti pola sync Pemetaan yang ada |
| M2 | **Kategori LK → laporan** | Daftar nilai `category_lk` dengan jenis laporan (Neraca / Laba rugi), urutan, label, dan sifat (pendapatan / beban / lainnya) | Nilai berbeda dari M1 (±20 nilai, termasuk `Laba (Rugi) ditahan`, `MODAL SAHAM`, `AKTIVA TIDAK LANCAR LAINNYA`, `PIUTANG LAIN-LAIN PIHAK BERELASI`, `TBA`) | Daftar awal diisi otomatis dari M1; jenis laporan, urutan, dan sifat diatur di aplikasi |
| M3 | **Jenis PPh** | Nilai baku {`PPh 21`, `PPh 23`, `PPh 4(2)`, `Non PPh`} dan tabel alias (`non pph`, `pph 23`, ...) | Tidak ada di Excel | Diatur di aplikasi; alias baru ditambahkan dari daftar pengecualian SPT |
| M4 | **Cost center** | Sudah ada (`gl_cc_map`, 89 baris); dipakai F2 untuk reklas HPP vs Biaya Usaha Lainnya | Sheet `CC` | Sync Excel (tetap) |

Dampak pada Pemetaan:
- Sync Pemetaan perlu membaca `COA` dari `GL - MASTER.xlsb` (atau menerima dua file). Keputusan sumber ada di Bagian 12 no. 10.
- Panel "belum terpetakan" yang sudah ada diperluas: akun bersaldo tanpa `category_lk` / `category_spt` (atau bernilai `TBA`) ikut tampil, sehingga mapping yang kurang dikerjakan di satu tempat.
- Pemetaan versi sinkron dicatat pada setiap snapshot SPT (`gl_coa_sync_log.id`), agar hasil SPT dapat dilacak ke versi mapping yang dipakai.
- Perubahan mapping setelah snapshot membuat snapshot ditandai usang (kontrol C8 diperluas: hash GL **dan** versi Pemetaan).

Pekerjaan Pemetaan ini adalah **prasyarat F1** dan dikerjakan sebagai bagian F0.
