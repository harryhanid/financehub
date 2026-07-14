# Modul Sahabat ETF — UI/UX Redesign (Layout, Stat Cards, Drill-down, Konsistensi) — Design

> **Status: APPROVED (user sign-off 2026-07-14, brainstorm session — visual companion untuk layout/stat-card/drill-down, terminal untuk sisanya).** Implementation plan belum ditulis. Jangan mulai implementasi sebelum itu.
>
> Follow-up terhadap [2026-07-14-sahabat-etf-module-design.md](2026-07-14-sahabat-etf-module-design.md) (modul dasar) dan [2026-07-14-sahabat-etf-filters-monthly-chart-design.md](2026-07-14-sahabat-etf-filters-monthly-chart-design.md) (filter tahun/pillar + chart bulanan) — keduanya sudah live.

## Context / Why

Audit langsung ke kode aktual (`app/templates/beasiswa/index.html:442-538`, `app/static/css/budget.css`, `app/static/js/sahabat_etf.js`) — bukan cuma dokumen — menemukan 8 masalah UI/UX di tab Sahabat ETF:

1. Halaman satu scroll panjang tanpa hierarki — tabel utama "Rincian per Anggota" terkubur di paling bawah
2. `.budget-chart-card` dipakai buat chart beneran DAN tabel polos (pillar table, 10 transaksi terakhir) — bahasa visual ga konsisten
3. Chart statis, ga ada drill-down
4. Palet warna chart beda-beda per chart, ga ada mapping kategori↔warna yang konsisten
5. Warna legend/axis Chart.js di-hardcode buat dark mode (`sahabat_etf.js` — `#e2e8f0`, `#94a3b8`), padahal `budget.css` support light mode juga
6. Loading state masih teks "Memuat data..." — padahal `skeletonRows()` helper + `.fh-skel`/`.skeleton` CSS sudah ada di codebase (`app/static/js/app.js:244`, `style.css:749`), dipakai di modul lain
7. Filter Tahun (checkbox multi-select) vs Pillar (dropdown single-select) — dua pola interaksi berbeda untuk 2 filter yang konsepnya sama
8. Stat card grid `auto-fit minmax(200px,1fr)` — pola yang di [[Design System Cobalt]] audit sendiri ditandai *BANNED/High severity*

## Design — Section 1: Struktur Halaman (✅ approved)

Ubah dari 1 scroll panjang jadi **3 accordion section** di dalam tab Sahabat ETF yang sama (bukan sub-tab terpisah — chart & tabel pendukungnya harus tetap kelihatan bareng):

- **"Ringkasan & Alert"** — expanded by default. Isi: filter bar, summary stat cards, alert over-budget card.
- **"Grafik"** — expanded by default. Isi **hanya chart beneran**: chart Bulanan, chart Tahunan, chart Kategori (donut) — chart Kategori **tetap didampingi** `setf-kategori-table`-nya persis seperti sekarang (canvas + tabel referensi bersebelahan), karena itu pasangan langsung satu chart, bukan tabel numpang.
- **"Detail Tabel"** — **collapsed by default**. Isi 4 tabel yang sebelumnya numpang di grid chart-card: `setf-pillar-table`, `setf-latest-payments-table` (10 Transaksi Terakhir), `setf-monthly-table` (Perbandingan Bulanan), dan `setf-table` (Rincian per Anggota).

State expand/collapse **tidak** dipersist ke localStorage — selalu reset ke default tiap reload (YAGNI, bukan kebutuhan yang diminta).

## Design — Section 2: Stat Cards (✅ approved)

Grid **tetap equal-width** (`auto-fit minmax(200px,1fr)`, 4 kartu) — ini **deviasi sengaja** dari rekomendasi Design System Cobalt (asymmetric grid), dipilih user karena lebih rapi. Dicatat eksplisit di sini supaya ga dikira kelupaan pas ada audit desain berikutnya.

Kartu **"Total Realisasi"** dikasih standout via **garis aksen kiri** (`border-left: 3px solid #818cf8`) + warna angka jadi indigo terang (`#a5b4fc`) — reuse token indigo yang sudah ada di `budget.css` (`--accent-glow: rgba(99,102,241,...)`), bukan warna baru. Kartu **"Over-Budget"** tetap pakai styling danger-merah kondisional yang sudah ada (`badge-status-*` classes), tidak berubah.

## Design — Section 3: Drill-down (✅ approved)

Klik pada chart **auto-expand accordion "Detail Tabel"** (kalau lagi collapsed) + auto-scroll ke situ + highlight/filter tabel yang paling relevan — reuse tabel yang sudah ada, bukan komponen baru:

- **Klik bar/slice Chart Kategori** → filter `setf-latest-payments-table` (10 Transaksi Terakhir) ke kategori yang diklik. Tabel ini sudah punya kolom Kategori, tapi endpoint-nya sekarang cuma return top-10 latest overall — **butuh extend backend**: parameter opsional `kategori` di endpoint yang mem-backing tabel ini, dan naikkan limit row (mis. dari 10 jadi ~30) saat filter aktif supaya hasil filter ga percuma cuma nyisa dikit. Pola extend-nya sama seperti `years`/`pillar` di spec filter sebelumnya (parameter opsional, default None = behavior lama).
- **Klik bar Chart Bulanan/Tahunan** → **highlight** (bukan filter — datanya memang sudah tampil semua) baris/kolom yang cocok di `setf-monthly-table` (Perbandingan Realisasi per Bulan per Tahun). Ini murni frontend (scroll + temporary highlight class), tidak butuh backend.
- Pillar (`setf-pillar-table`) tidak punya chart pendampingnya sekarang, jadi tidak masuk trigger drill-down.

## Design — Section 4: Filter Pillar → Checkbox Multi-select (✅ approved)

**Supersedes** keputusan single-select dropdown di [2026-07-14-sahabat-etf-filters-monthly-chart-design.md](2026-07-14-sahabat-etf-filters-monthly-chart-design.md) Section 2 — sekarang Pillar jadi checkbox multi-select (`.setf-pillar-cb`), pola & markup mengikuti `.setf-year-cb` yang sudah ada persis. Alasan: user bisa banding beberapa pillar sekaligus, dan 2 filter yang konsepnya sama (kategori) jadi konsisten cara pakainya.

Backend: service functions (`get_siswa_summary`, `get_kategori_breakdown`, `get_all_transactions`) yang sekarang terima `pillar: str = None` (single value) diubah jadi terima list (`pillars: list[str] = None`), query `pillar IN (?, ...)` — sama polanya dengan bagaimana `years` sudah jadi list sebelumnya. Semantik filter **tidak berubah**: tetap cuma mempengaruhi baris `payment_beasiswa` (realisasi), `budget_beasiswa` tetap tampil apa adanya seperti keputusan sebelumnya.

## Design — Section 5: Palet Warna & Theme-aware Chart Colors (✅ approved)

- Satu palet kategorikal 6-warna (reuse array yang sudah ada di `sahabat_etf.js:313`) dijadikan **konstanta bernama** (`SETF_CATEGORY_COLORS`), di-mapping **per nama kategori/pillar** (bukan per index array) — supaya kategori yang sama selalu warna sama di semua chart, walau urutan datanya beda-beda tiap fetch.
- Warna legend/axis Chart.js yang sekarang hardcode (`#e2e8f0`, `#94a3b8`, `#475569`) diganti baca dari CSS custom property yang sudah ada di `style.css` (mis. `var(--text-muted)`) via `getComputedStyle(document.documentElement)` saat render chart — supaya otomatis adaptif ke `[data-theme="dark"]`. Kalau app sudah punya event/listener buat theme toggle, reuse itu untuk re-render chart pas tema berganti; kalau belum ada, cukup baca ulang saat chart di-render ulang (refetch/filter change) — tidak perlu live-update di tengah toggle kalau itu belum jadi pola yang ada di modul lain.

## Design — Section 6: Skeleton Loader (✅ approved)

Ganti semua placeholder teks "Memuat data..." di tabel-tabel Sahabat ETF dengan `skeletonRows(cols, count)` (`app/static/js/app.js:244`) — reuse helper yang sudah dipakai modul Payment Memo, bukan bikin baru. Untuk stat card (bukan tabel), pakai `.fh-skel`/`.skeleton` class yang sudah ada di `style.css:749` sebagai shimmer block di dalam `.val` selama data belum masuk.

## Testing

- Extend `test_sahabat_etf_service.py` / `test_sahabat_etf_routes.py`: filter kategori di endpoint transaksi (baru), `pillars` sebagai list (ganti dari single `pillar`, termasuk regression guard "tanpa filter = behavior lama"), guard `etf_company_required` tetap berlaku di route yang di-extend.
- 26 test existing modul ini harus tetap hijau.
- Manual browser verification checklist (project ini tidak punya test JS): accordion expand/collapse, drill-down klik kategori & bulan/tahun, filter pillar checkbox (single & multi), skeleton muncul lalu ke-replace data asli, warna chart legible di light & dark mode.

## Out of Scope (iterasi ini)

- Drill-down per-siswa (klik nama di Rincian per Anggota → buka detail transaksi mentah via `/api/detail/<code>`) — sudah dicatat out-of-scope di spec filter sebelumnya, tetap dideferred.
- Retrofit pola accordion/drill-down/palet yang sama ke Beasiswa Dashboard BI (belum dibangun) — dicatat sebagai referensi desain untuk nanti, bukan scope kerja sekarang.
- Persist state accordion (localStorage) antar reload.
- Perubahan ke modul Budget Monitoring lain (`budget.css` dipakai bersama, tapi semua perubahan di sini di-scope ke selector spesifik Sahabat ETF).

## Next Steps

1. ~~User sign-off~~ — done, 2026-07-14 (brainstorm section-by-section, visual companion untuk layout/stat-card/drill-down + terminal untuk sisanya).
2. Spec self-review: selesai (lihat commit ini — placeholder scan, konsistensi antar-section, dan supersede eksplisit terhadap spec filter sebelumnya sudah dicek).
3. Invoke skill `writing-plans` untuk bikin implementation plan. Jangan mulai implementasi sebelum itu.
