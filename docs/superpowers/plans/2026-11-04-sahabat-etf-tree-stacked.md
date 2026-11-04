# Sahabat ETF Tree Query — Kartu Bertumpuk Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ganti tree ECharts di tab Tree Query dengan tampilan kartu bertumpuk (G1 horizontal, G2+ vertikal), fokus satu keluarga saat pencarian, dan Export PDF berkop logo FLOW + waktu cetak.

**Architecture:** Logika murni (indeks tree, pencarian fokus, baris kolom, format waktu, pemotongan halaman) di satu modul `setf_tree_model.js` yang bisa dites dengan `node --test`. Renderer DOM (`setf_tree_view.js`) memakai model itu dan CSS sendiri. `sahabat_etf.js` hanya menyambungkan tombol yang sudah ada (`searchTree`, `resetTreeQuery`, `zoomTreeQuery`, `adjustSpacing`, `exportTreePDF`) ke renderer baru.

**Tech Stack:** Flask templates, vanilla JS, `node --test` (Node 24, tanpa dependensi baru) untuk logika murni, pytest untuk template, jsPDF + html2canvas dari cdnjs untuk PDF.

**Spec:** `docs/superpowers/specs/2026-11-04-sahabat-etf-tree-stacked-design.md`

## Global Constraints

- Hanya tab Tree Query yang berubah; ECharts tetap dimuat untuk tab lain (`beasiswa/index.html:37`, `sahabat_etf/public_index.html:14`).
- Kontrak data `/beasiswa/sahabat/tree-data` tidak berubah: node `{id, code, name, partners[], children[], parent_partner_id?, tanggal_lahir, catatan}`; akar = id satu huruf.
- Generasi: akar = 0 (tanpa label), G1 = anak langsung akar; partner tidak menambah generasi.
- Warna wajib: biru untuk jalur, kuning untuk hasil pencarian.
- Teks UI Bahasa Indonesia; format cetak persis `Dicetak: 04 Nov 2026 11:23 WIB`.
- Logo = `app/static/img/flow-mark.png`.
- Data pribadi (tanggal lahir, catatan) hanya di tooltip kartu.
- Tidak ada commit/push tanpa permintaan pengguna di luar yang dicantumkan plan ini; Task terakhir yang meng-commit hanya bila pengguna mengizinkan.

## Review Focus

- Query kosong / hanya spasi: kembali ke tampilan awal, bukan "tidak ada hasil".
- Query tanpa hasil: pesan "Tidak ada hasil" dan tombol Reset tetap jalan, tampilan tidak kosong tanpa penjelasan.
- Hasil di nama partner, bukan nama orang: baris partner yang disorot, rantai tetap lengkap.
- Hasil = akar (mis. "Eka"): akar tampil dengan G1-nya, tidak error.
- Hasil di beberapa keluarga: semua keluarga itu tampil, "Menampilkan N dari M keluarga" benar.
- Saudara tersembunyi tetap terjangkau lewat chip "+ N saudara".
- Konten tinggi: PDF > 1 halaman terpotong benar, kepala di setiap halaman.
- Nama sangat panjang / tanpa partner / tanpa tanggal lahir: kartu tidak pecah.

---

### Task 1: Model — indeks tree dan pencarian fokus

**Files:**
- Create: `app/static/js/setf_tree_model.js`
- Test: `app/tests_js/setf_tree_model.test.js`

**Interfaces:**
- Produces (CommonJS `module.exports` dan `window.SetfTreeModel`):
  - `indexTree(roots: Node[]): { byId: Map<string,{node:Node,parentId:string|null,gen:number}>, rootIds: string[] }`
  - `nameMatches(node: Node, q: string): { self: boolean, partnerIds: string[] }` (q sudah lower-case, sebagian, tak peka huruf)
  - `searchFocus(roots: Node[], query: string): null | { families: FocusNode[], shownFamilies: number, totalFamilies: number }`
  - `FocusNode = { node: Node, gen: number, isHit: boolean, partnerHitIds: string[], hiddenSiblings: number, children: FocusNode[] }`

- [ ] **Step 1: Tulis tes gagal** di `app/tests_js/setf_tree_model.test.js` (`node:test` + `node:assert/strict`), dengan fixture dua akar: `A` (Eka) → `A1` (Trini) → [`A1.1` Oei Tjie Goen (partner `A1.1.A` Wenny), `A1.2` Oei Hoei Beng (partner `A1.2.A` Tan Teng Hong) → `A1.2.A.1` Winata Tanuwijaya (parent_partner_id `A1.2.A`, partner `A1.2.A.1.A` Erna) → `A1.2.A.1.A.1` Olivia]; `A` juga punya `A2` (Mellie); akar `B` (Hea Sitaba) → `B1` Giok. Tes:
  - `indexTree gen`: `byId.get('A1.2.A.1').gen === 3`, `parentId === 'A1.2'`, `byId.get('A').gen === 0`, `rootIds` deep-equals `['A','B']`.
  - `searchFocus null untuk query kosong`: `searchFocus(roots,'   ') === null`.
  - `searchFocus rantai`: `'WINATA'` → `shownFamilies 1`, `totalFamilies 2`, rantai id dari `families[0]` mengikuti `children[0]` = `['A','A1','A1.2','A1.2.A.1']`; node `A1` `hiddenSiblings === 1` (A2 tersembunyi), `A1.2` `hiddenSiblings === 1` (A1.1); `A1.2.A.1` `isHit === true` dan `children` kosong.
  - `searchFocus partner`: `'erna'` → hit `A1.2.A.1` dengan `partnerHitIds` `['A1.2.A.1.A']`, `isHit === false`.
  - `searchFocus partner induk`: `'tan teng'` → hit di `A1.2` dengan `partnerHitIds ['A1.2.A']`.
  - `searchFocus akar`: `'eka'` → `families[0].node.id === 'A'`, `isHit true`, `children.map(c=>c.node.id)` = `['A1','A2']` semuanya `isHit false`.
  - `searchFocus tanpa hasil`: `'zzz'` → `families` kosong, `shownFamilies 0`, `totalFamilies 2`.
  - `searchFocus banyak keluarga`: query `'g'` yang cocok di A dan B (mis. "Giok", "Tjie Goen") → `shownFamilies 2`.

- [ ] **Step 2: Jalankan tes, pastikan gagal.** Run: `node --test app/tests_js/` (dari `C:\FinanceHub`). Expected: FAIL (modul tidak ada).

- [ ] **Step 3: Implementasi** ketiga fungsi di `setf_tree_model.js`. Ekspor ganda: `if (typeof module !== 'undefined') module.exports = api; else window.SetfTreeModel = api;`. `searchFocus` memangkas rekursif: simpan hanya anak yang berada di rantai ke hasil, hitung `hiddenSiblings = anak induk − anak terjaga`; node hasil tidak membawa anak, kecuali akar hasil yang membawa semua anak langsungnya (tak-hasil, tanpa cucu).

- [ ] **Step 4: Jalankan tes, pastikan lolos.** Run: `node --test app/tests_js/`. Expected: PASS semua.

- [ ] **Step 5: Commit** (bila pengguna mengizinkan): `git add app/static/js/setf_tree_model.js app/tests_js/setf_tree_model.test.js` ; pesan `feat(sahabat-etf): model tree — indeks dan pencarian fokus`.

---

### Task 2: Model — kolom tampilan awal, buka/tutup, lencana dan penggaris

**Files:**
- Modify: `app/static/js/setf_tree_model.js`
- Test: `app/tests_js/setf_tree_model.test.js`

**Interfaces:**
- Consumes: `indexTree` dari Task 1.
- Produces:
  - `toggleOpen(openIds: Set<string>, id: string): Set<string>` (mengembalikan Set baru)
  - `buildColumns(roots: Node[], openIds: Set<string>): RootBlock[]`
  - `RootBlock = { root: Node, columns: Column[] }`, `Column = { g1: Row, rows: Row[] }`
  - `Row = { id: string, node: Node, gen: number, indent: number, hasChildren: boolean, childCount: number, open: boolean, badge: string|null, ruler: string|null }`
  - `focusRows(families: FocusNode[]): FocusBlock[]`, `FocusBlock = { root: Row, chain: Row[], hits: string[] }` (tiap `chain` Row berpenggaris `ruler = 'G'+gen` untuk gen ≥ 1; `badge` hanya untuk kelompok anak hasil berisi ≥ 2 kartu)

- [ ] **Step 1: Tulis tes gagal** (fixture Task 1, ditambah `A1.3` dan `A1.4` pada A1):
  - `buildColumns default`: untuk akar `A`, `columns.map(c=>c.g1.id)` = `['A1','A2']`; `columns[0].rows.map(r=>r.id)` = `['A1.1','A1.2','A1.3','A1.4']`; baris `A1.2` `hasChildren true`, `childCount 1`, `open false`, `indent 0`.
  - `buildColumns buka`: `openIds = new Set(['A1.2'])` → urutan baris `['A1.1','A1.2','A1.2.A.1','A1.3','A1.4']`, `A1.2.A.1` `indent 1`.
  - `lencana`: baris pertama tiap kelompok saudara ≥ 2 kartu punya `badge` `'G2'` (A1 punya 4 kartu); kelompok 1 kartu (kolom `A2` hanya `A2.1`) `badge === null`; kelompok buka `A1.2.A.1` (1 kartu) `badge === null`; bila `A1.2` punya 2 anak, kelompoknya `badge 'G3'`.
  - `penggaris`: `columns[0].g1.ruler === 'G1'`; semua `rows[*].ruler === null`.
  - `toggleOpen`: tidak memutasi Set asal; panggil dua kali mengembalikan isi semula.
  - `focusRows`: dari `searchFocus(roots,'winata')` → satu `FocusBlock` dengan `root.id === 'A'` dan `root.ruler === null`; `chain.map(r=>r.id)` = `['A1','A1.2','A1.2.A.1']` dan `chain.map(r=>r.ruler)` = `['G1','G2','G3']`; `hits` = `['A1.2.A.1']`.

- [ ] **Step 2: Jalankan tes, pastikan gagal.** Run: `node --test app/tests_js/`. Expected: FAIL (fungsi belum ada).

- [ ] **Step 3: Implementasi** ketiga fungsi. Kedalaman buka default: kartu gen 2 (G2) terlihat, gen ≥ 3 hanya terlihat bila id induknya ada di `openIds`; `indent` = gen − 2 untuk kartu. Lencana ditetapkan per kelompok saudara (`'G'+gen`) pada baris pertama kelompok bila anggota ≥ 2.

- [ ] **Step 4: Jalankan tes, pastikan lolos.** Run: `node --test app/tests_js/`. Expected: PASS.

- [ ] **Step 5: Commit** (bila diizinkan): `feat(sahabat-etf): model tree — kolom, buka/tutup, lencana dan penggaris`.

---

### Task 3: Model — waktu cetak dan pemotongan halaman PDF

**Files:**
- Modify: `app/static/js/setf_tree_model.js`
- Test: `app/tests_js/setf_tree_model.test.js`

**Interfaces:**
- Produces:
  - `formatPrintStamp(date: Date): string` → `"Dicetak: 04 Nov 2026 11:23 WIB"` (WIB = UTC+7 tetap, bulan singkat Indonesia: Jan Feb Mar Apr Mei Jun Jul Agu Sep Okt Nov Des)
  - `slicePages(contentW: number, contentH: number, opt: {pageW:number,pageH:number,margin:number,headerH:number}): { scale: number, slices: {sy:number, sh:number}[] }` (satuan mm untuk opt; piksel untuk konten; `scale` mm per piksel; tiap halaman memuat kepala setinggi `headerH`)

- [ ] **Step 1: Tulis tes gagal:**
  - `formatPrintStamp(new Date('2026-11-04T04:23:00Z')) === 'Dicetak: 04 Nov 2026 11:23 WIB'`
  - lintas tengah malam: `new Date('2026-12-31T18:05:00Z')` → `'Dicetak: 01 Jan 2027 01:05 WIB'`
  - `slicePages(500,1000,{pageW:210,pageH:297,margin:10,headerH:20})`: `scale === 0.38`, `slices` = `[{sy:0,sh:676},{sy:676,sh:324}]`
  - konten pendek `slicePages(500,300,...)` → satu slice `{sy:0,sh:300}`.

- [ ] **Step 2: Jalankan tes, pastikan gagal.** Run: `node --test app/tests_js/`. Expected: FAIL.

- [ ] **Step 3: Implementasi** kedua fungsi (`scale = (pageW − 2·margin)/contentW`; tinggi pakai per halaman = `floor((pageH − 2·margin − headerH)/scale)`).

- [ ] **Step 4: Jalankan tes, pastikan lolos.** Run: `node --test app/tests_js/`. Expected: PASS.

- [ ] **Step 5: Commit** (bila diizinkan): `feat(sahabat-etf): helper waktu cetak dan pemotongan halaman PDF`.

---

### Task 4: Renderer DOM, CSS, dan sambungan ke tab

**Files:**
- Create: `app/static/js/setf_tree_view.js`, `app/static/css/sahabat_tree.css`
- Modify: `app/static/js/sahabat_etf.js` (blok tree: `treeChartInstance`, `initTreeQuery` `2476`, `renderTree` `2550`, `searchTree` `2883`, `zoomTreeQuery`, `adjustSpacing`, `resetTreeQuery`, `assignGenerations`, `expandPathToName`, `foldChildren`, klik handler drill-down), `app/templates/sahabat_etf/_panel.html:440-442`, `app/templates/beasiswa/index.html:1034`, `app/templates/sahabat_etf/index.html:8`, `app/templates/sahabat_etf/public_index.html:45`
- Test: `app/tests/test_sahabat_etf_routes.py`

**Interfaces:**
- Consumes: `window.SetfTreeModel` (Task 1–2).
- Produces (`window.SetfTreeView`):
  - `mount(container: HTMLElement, roots: Node[]): void`
  - `renderDefault(): void`, `renderFocus(query: string): void`, `reset(): void`
  - `setTextScale(mult: number): void`, `setSpacing(mult: number): void` (CSS variable `--tree-font` dan `--tree-gap`/`--tree-indent`)
  - `getExportElement(): HTMLElement` (elemen konten tree untuk ditangkap)

- [ ] **Step 1: Tulis tes gagal pytest** di `test_sahabat_etf_routes.py`: setelah login+pilih ETF (helper `login`, `_select_etf`), `GET` halaman beasiswa tab sahabat dan assert body memuat `js/setf_tree_model.js`, `js/setf_tree_view.js`, `css/sahabat_tree.css`, serta elemen `id="tree-stack"` dan tidak lagi `id="tree-chart"`. Run: `pytest app/tests/test_sahabat_etf_routes.py -k tree -v`. Expected: FAIL.

- [ ] **Step 2: Implementasi markup:** di `_panel.html` ganti `<div id="tree-chart" ...>` dengan `<div id="tree-stack"></div>` di dalam `#tree-wrapper`; tambah `<link>` CSS dan tiga `<script>` (model, view, lalu `sahabat_etf.js`) di `beasiswa/index.html`, `sahabat_etf/index.html`, `sahabat_etf/public_index.html`; tambah baris status `<div id="tree-status">` di atas wrapper untuk "Menampilkan N dari M keluarga · Tampilkan semua" dan pesan "Tidak ada hasil".

- [ ] **Step 3: Implementasi renderer** di `setf_tree_view.js` dan gaya di `sahabat_tree.css` mengikuti mockup yang disetujui: kotak G1 berjajar; kartu G2+ bertumpuk dengan garis penghubung kiri; kartu berpanah ▸/▾ dan jumlah anak; penggaris kiri sticky 48px berlatar `#f1f5f9` (label `G1`, `G2`, … biru `#2563eb`); jalur biru (`#3b82f6` pada border, `#eff6ff` latar), hasil kuning (`#f59e0b` border, `#fef3c7` latar); chip "+ N saudara" pada kartu jalur yang `hiddenSiblings > 0` (klik menampilkan saudara di tempat); tooltip (`title` atau elemen hover) berisi tanggal lahir dan catatan kartu serta partnernya; partner ditulis di dalam kartu "Nama (Partner X)". Klik kartu → `toggleOpen` lalu render ulang tanpa menggeser scroll.

- [ ] **Step 4: Sambungkan `sahabat_etf.js`:** `initTreeQuery` mengambil `/beasiswa/sahabat/tree-data`, mengisi datalist nama (nama orang dan partner), memanggil `SetfTreeView.mount`; `searchTree` → `renderFocus(query)` (query kosong → `renderDefault`); `resetTreeQuery` mengosongkan input dan `reset()`; `zoomTreeQuery(ratio)` → `setTextScale`; `adjustSpacing(delta)` → `setSpacing`; hapus semua kode ECharts khusus tree dan fungsi tak terpakai (`assignGenerations`, `expandPathToName`, `foldChildren`, `applyInitialDepth`, handler drill-down, `treeChartInstance`). Jangan menghapus pemakaian `echarts` di fungsi tab lain.

- [ ] **Step 5: Jalankan tes.** Run: `pytest app/tests/test_sahabat_etf_routes.py -k tree -v` dan `node --test app/tests_js/`. Expected: PASS. Lalu verifikasi di browser (preview `financehub`, port 5051, login modul Sahabat): tampilan awal kolom bertumpuk tanpa gulir horizontal besar; klik kartu G2 membuka turunan ke bawah; cari "winata" menampilkan satu keluarga dengan rantai A › A1 › A1.2 › A1.2.A.1, saudara tersembunyi, chip "+ N saudara" berfungsi; Reset kembali; tidak ada error konsol.

- [ ] **Step 6: Commit** (bila diizinkan): `feat(sahabat-etf): tree query kartu bertumpuk menggantikan ECharts`.

---

### Task 5: Export PDF berkop FLOW

**Files:**
- Modify: `app/static/js/sahabat_etf.js` (`exportTreePDF` `2945`)

**Interfaces:**
- Consumes: `SetfTreeModel.formatPrintStamp`, `SetfTreeModel.slicePages`, `SetfTreeView.getExportElement`; jsPDF (sudah dimuat dinamis) dan html2canvas `https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js` (dimuat dinamis bila belum ada).

- [ ] **Step 1: Implementasi:** `exportTreePDF()` menangkap elemen ekspor dengan `html2canvas(el, {scale: 2, backgroundColor: '#fff'})` (tanpa kolom penggaris yang sticky bila bergeser: pastikan `scrollLeft` direset 0 selama tangkapan); gambar logo `/static/img/flow-mark.png` dimuat sebagai data URL; PDF A4 (orientasi portrait bila tinggi > lebar), margin 10 mm, kepala di setiap halaman: logo kiri, "Flow - Beasiswa Sahabat ETF — Tree Query" dan `formatPrintStamp(new Date())` kanan; isi dipotong dengan `slicePages` ke beberapa halaman; simpan `Sahabat_ETF_Tree.pdf`; toast sukses/gagal seperti sekarang.

- [ ] **Step 2: Verifikasi manual** di preview: klik Export PDF pada tampilan awal dan pada hasil pencarian; PDF terunduh, kepala memuat logo dan "Dicetak: <tanggal/jam sekarang> WIB", isi mengikuti layar (cabang terbuka, fokus pencarian), PDF > 1 halaman terpotong tanpa kartu hilang. Jalankan `node --test app/tests_js/` dan `pytest app/tests/test_sahabat_etf_routes.py -v`; Expected: PASS.

- [ ] **Step 3: Commit** (bila diizinkan): `feat(sahabat-etf): export PDF tree berkop logo FLOW dan waktu cetak`.

---

### Task 6: Verifikasi akhir dan dokumen

**Files:**
- Modify: `docs/superpowers/specs/2026-11-04-sahabat-etf-tree-stacked-design.md` (tidak perlu bila tidak ada perubahan), `docs/superpowers/plans/2026-11-04-sahabat-etf-tree-stacked.md`

- [ ] **Step 1:** Jalankan seluruh `node --test app/tests_js/` dan `pytest app/tests/test_sahabat_etf_routes.py app/tests/test_sahabat_etf_service.py -v`. Expected: PASS.
- [ ] **Step 2:** Periksa tab Dashboard/Laporan/Diagram di preview tidak berubah dan tidak ada galat konsol; periksa akses publik (`/beasiswa/sahabat/login`, kata sandi modul) menampilkan Tree Query yang sama.
- [ ] **Step 3:** Commit dokumen spec dan plan (bila diizinkan): `docs: spesifikasi dan rencana tree kartu bertumpuk`. Push dan rilis ("Update FLOW") hanya bila pengguna meminta; keluarga C baru terlihat di produksi setelah rilis.
