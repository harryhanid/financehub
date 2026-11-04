# Sahabat ETF Tree Query — tampilan kartu bertumpuk

Tanggal: 2026-11-04
Modul: Beasiswa / Sahabat ETF / Tree Query (`app/static/js/sahabat_etf.js`, `app/modules/sahabat_etf/routes.py` endpoint `/beasiswa/sahabat/tree-data`)

## Latar belakang dan tujuan

Tree Query sekarang digambar dengan ECharts (orientasi atas-bawah). Setelah keluarga C masuk dan tampilan awal membuka G1 dan G2, jumlah G2 yang berjajar horizontal sangat banyak (lebar kanvas puluhan ribu piksel), sehingga tree terlalu besar dan sulit dibaca.

Tujuan: tampilan awal ringkas. G1 tetap berjajar horizontal; G2 ditumpuk vertikal di bawah G1-nya. Membuka turunan G2 juga ke bawah (vertikal), bukan ke samping. Pencarian menunjukkan satu keluarga dengan garis keturunan yang jelas dari akar sampai orang yang dicari.

## Istilah

- Akar keluarga: group satu huruf (A, B, C, ...). Tanpa label generasi.
- G1: anak langsung akar (`A1`, `A2`, ...). G2: `A1.1`, `A1.2`, dst. (G(n) = kedalaman n di bawah akar.)
- Partner: orang dengan huruf di akhir group (`A1.2.A`); ditulis di dalam kartu pasangannya seperti sekarang.
- Data: `/tree-data` sudah mengembalikan struktur `{id, code, name, partners[], children[], tanggal_lahir, catatan}`; akar dideteksi dinamis (sudah dikerjakan, commit 357575c).

## Keputusan yang sudah diambil (oleh pengguna)

1. Tampilan awal G2 = **kartu bertumpuk** (opsi A): kotak G1 berjajar horizontal, di bawah tiap G1 kartu G2 ditumpuk vertikal dengan garis penghubung di kiri.
2. **Klik G2** = turunannya tampil **menjorok ke bawah** tepat di bawah kartu yang diklik (opsi A). Tidak ada perubahan ke tree horizontal.
3. **Pencarian** = tampilan **fokus satu keluarga** (opsi B): hanya keluarga yang berisi hasil yang ditampilkan, dengan tombol "Tampilkan semua". Garis keturunan dari akar paling atas sampai orang yang dicari harus **jelas**. Kartu saudara di sepanjang jalur itu **disembunyikan** (hanya leluhur langsung yang terlihat).
4. Kolom penggaris generasi (G1, G2, ... di kiri, sticky, pemisah putus-putus) dipertahankan.

## Tujuan, bukan-tujuan, anti-tujuan

Tujuan: tinggi/lebar tampilan awal jauh lebih kecil; membuka cabang tidak melebarkan layar; hasil pencarian langsung menunjukkan "siapa leluhur orang ini".

Bukan-tujuan: mengubah data/skema di Supabase; mengubah tab lain (Dashboard, Laporan, Diagram, Detail Transaksi).

Anti-tujuan (dianggap gagal walau teknis jalan): hasil pencarian tidak menunjukkan rantai leluhur utuh dari akar; ada orang yang tidak terjangkau (tidak bisa dibuka/ditemukan); keluarga baru (D, E, ...) tidak tampil.

## Perilaku yang diharapkan

Tampilan awal:
- Satu baris akar (A, B, C, ...) lalu G1 per akar berjajar; G2 default tampil sebagai kartu bertumpuk. Kartu menampilkan nama, kode group, dan partner (format sekarang: "Nama (Partner X)").
- Kartu yang punya turunan diberi penanda bisa dibuka (mis. panah dan jumlah anak).
- Klik kartu G2 (atau lebih dalam): toggle buka/tutup turunannya, menjorok ke bawah. Kolom bertambah tinggi, lebar tetap.

Pencarian (kotak cari + tombol Cari/Reset yang ada; daftar saran nama tetap):
- Cocok sebagian, tidak peka huruf besar/kecil, termasuk nama partner (seperti `expandPathToName` sekarang).
- Hasil tampil di keluarga yang memuatnya saja; jika hasil tersebar di beberapa keluarga, semua keluarga itu tampil.
- Di keluarga itu: rantai dari akar ke hasil ditampilkan berurutan, jalur berwarna, saudara di jalur disembunyikan, hasil disorot; beberapa hasil dalam satu keluarga disorot semuanya.
- Tombol/teks "Menampilkan N dari M keluarga · Tampilkan semua"; Reset mengembalikan tampilan awal.

## Batasan

- Tetap di app Flask + `sahabat_etf.js`; tidak menambah dependensi baru kecuali yang dimuat dari cdnjs seperti jsPDF sekarang.
- Dipakai juga lewat akses publik tab Sahabat (login password modul); jangan merusak itu.
- Data pribadi (tanggal lahir, catatan) tetap hanya muncul di tooltip/detail seperti sekarang.
- Keluarga C hanya ada di database produksi (laptop dev membaca staging); verifikasi dengan data A/B di dev.

## Diserahkan ke pembuat (keputusan saya, bisa diubah)

- ECharts tidak punya tata letak kartu bertumpuk, jadi tampilan ini digambar sendiri (DOM/CSS, bukan canvas ECharts). Library ECharts tidak lagi dipakai untuk tab ini.
- Perilaku klik bawaan sekarang ("drill" ke jalur satu garis lurus, klik lagi naik ke induk) digantikan oleh toggle buka/tutup dan fokus pencarian.
- Zoom teks/jarak dan Export PDF yang ada harus tetap berfungsi: ekspor PDF memakai tangkapan DOM (mis. html2canvas dari cdnjs) menggantikan `treeChartInstance.getDataURL`.
- Tooltip detail (tanggal lahir, catatan, partner) dipertahankan saat kartu di-hover.
- Ukuran kartu, warna, dan animasi buka/tutup: mengikuti gaya yang sudah ditampilkan di mockup (biru untuk jalur, kuning untuk hasil).

## Penandaan generasi (keputusan pengguna 2026-11-04)

- Penggaris di kiri dipakai untuk generasi yang menempati satu baris sendiri: G1 di tampilan awal, dan di mode pencarian setiap leluhur pada rantai (G1, G2, G3, G4, ... sampai orang yang dicari), karena saudara disembunyikan sehingga tiap generasi tepat satu kartu per baris.
- Lencana kecil ("G2", "G3", ...) hanya dipakai pada kelompok kartu yang banyak (tumpukan saudara di bawah satu induk, termasuk cabang yang dibuka) dan pada generasi paling bawah. Generasi yang sudah terbaca dari penggaris tidak diberi lencana lagi.

## Export PDF (tambahan pengguna 2026-11-04)

Hasil export harus seperti cetakan dari FLOW: kepala halaman memuat logo FLOW (logo yang sama dengan header aplikasi) dan tanggal serta jam saat dicetak (zona waktu WIB, mis. "Dicetak: 04 Nov 2026 11:23 WIB"), di atas gambar tree. Tampilan tree yang diexport mengikuti keadaan layar saat ini (cabang terbuka, fokus pencarian).

## Keputusan tambahan (hasil pemeriksaan pembuat)

Sudah terjawab oleh proyek:
- ECharts dipakai juga di tab Dashboard/Laporan/Diagram; library dan helper bersama tetap ada. Hanya kode Tree Query yang diganti.
- Skala: sekitar 232 orang di Sahabat ETF (setelah keluarga C), 2 sampai 3 akar, belasan G1, tidak sampai puluhan G2 per G1. Cukup render DOM biasa, tanpa virtualisasi.

Keputusan saya (bisa diubah):
- Kedalaman G3 dan seterusnya tertutup di tampilan awal; beberapa cabang boleh terbuka bersamaan (state = kumpulan id yang terbuka).
- Di mode pencarian: orang yang dicari tampil dengan anak-anaknya tertutup tapi bisa dibuka; jika hasil adalah nama partner, baris partner di dalam kartu pasangannya yang disorot; jika hasil adalah akar, tampil akar dengan G1-nya.
- Saudara yang disembunyikan di mode pencarian tetap bisa dijangkau: tiap kartu di jalur punya chip kecil "+ N saudara" yang menampilkannya di tempat, selain tombol "Tampilkan semua" dan Reset.
- Export PDF menangkap tampilan saat ini (termasuk cabang yang terbuka dan fokus pencarian), satu halaman panjang yang dipotong per halaman A4.
- Zoom teks mengubah ukuran font kartu; kontrol jarak mengubah celah antar kolom dan lebar indentasi.
- Mockup yang dirujuk ada di sesi brainstorming, bukan di repo; warna wajib hanya biru untuk jalur dan kuning untuk hasil.

## Di luar lingkup / berikutnya

- Menampilkan keluarga C di produksi menunggu rilis ("Update FLOW").
- Perapian data (tanggal lahir 2995, 2026-11-01, duplikat Jety/David) tidak termasuk.

## Revisi 2026-11-04 (tampilan klasik, garis bloodline)

- Tampilan awal: pemilih cabang (A, B, C, ...); tree satu cabang baru tampil setelah dipilih, bukan semua sekaligus.
- Gaya garis (pilihan pengguna, opsi B): garis keturunan tebal biru (3px) dengan simpul bulat di tiap percabangan. Akar di atas, garis siku ke tiap G1, dari G1 turun batang vertikal ke kartu G2, turunan lebih dalam bersarang dengan batangnya sendiri. Mode pencarian memakai garis siku bertangga dari akar ke hasil.
- Export PDF: ruang kosong dipangkas dan konten dipas ke lebar halaman; bila tinggi hanya melebihi satu halaman <= 8%, skala dikecilkan agar muat satu halaman. Export tanpa cabang terpilih dan tanpa pencarian menampilkan pesan.
- Keputusan saya (pengguna hanya memilih "B"): tampilan pencarian ikut memakai garis klasik yang sama.
