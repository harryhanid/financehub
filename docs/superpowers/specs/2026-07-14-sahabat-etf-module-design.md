# Modul Sahabat ETF — Design

> **Status: APPROVED (user sign-off 2026-07-14, brainstorm session).** Implementation plan not yet written. Do not start implementation before that.

## Context / Why

"Sahabat ETF" adalah salah satu program beasiswa (`siswa.program = 'Sahabat ETF'`) yang sudah punya data live di `finance_hub.db` tapi belum punya halaman/dashboard khusus — saat ini datanya cuma bisa dilihat lewat filter manual di tab umum `templates/beasiswa/index.html` (Data Siswa / Data Budget / Data Payment / Report Siswa / Rekam Medis), bercampur dengan 1297 siswa program lain.

Goal: bikin halaman khusus yang (1) menampilkan semua transaksi siswa program Sahabat ETF dalam satu tempat, dan (2) dashboard analisa yang mengumpulkan budget vs payment vs realisasi.

## Research Findings (diverifikasi terhadap `finance_hub.db` live, 2026-07-14)

**Populasi:** 11 siswa dengan `program='Sahabat ETF'` (company_id=2 / ETF), 10 berstatus Aktif, 1 lulus. Jenjang campur: SD, SMA, S1, S2, dan nilai jenjang `'SETF'` (anomali kecil di data, dibiarkan apa adanya — bukan scope perbaikan data di sini).

**Transaksi terkait (join via `siswa_code`, bukan filter `pillar`):**
- `budget_beasiswa`: 59 baris, total ≈ Rp 6.446.624.216
- `payment_beasiswa`: 61 baris, total ≈ Rp 3.359.202.235 (59 baris `status='complete'` ≈ Rp 2.923.534.887, 2 baris `status='open'` ≈ Rp 435.667.348)

**Penting — kolom `pillar` di `payment_beasiswa` TIDAK reliable untuk filter program ini.** Contoh nyata: siswa `1210487` (program Sahabat ETF) punya baris payment dengan `pillar='FINANCE'`, bukan `'SETF'`. `pillar` adalah cost-center/routing tag internal untuk modul PA/PAM lain, bukan penanda program siswa. **Satu-satunya filter yang benar adalah join ke `siswa.program='Sahabat ETF'`.**

**Kolom `realized_amount` / `tgl_realisasi` di `payment_beasiswa` ada di skema tapi 0 baris terisi di seluruh tabel** (bukan cuma untuk Sahabat ETF) — fitur ini belum pernah dipakai alur mana pun. Diputuskan **tidak dipakai**; realisasi didefinisikan dari `status` yang sudah ada (lihat Section 1).

**Pola dashboard yang sudah ada untuk dicontoh:** `modules/budget/` (routes.py + service.py + template terpisah, Chart.js, summary-grid + chart-grid + card notifikasi) — modul ini paling mirip kebutuhan Sahabat ETF dan jadi referensi arsitektur.

**Auth/session pattern (konsisten di semua modul):** `session.get("company_id")` via helper `_cid()`/`_ctx()`, guard `@jwt_html_required`, redirect ke `dashboard.select_company` kalau company belum dipilih.

## Design — Section 1: Arsitektur & Data (✅ approved)

**Struktur modul baru**, isolasi penuh dari `modules/beasiswa/` (bukan tab ke-6 di index.html yang sudah 1726 baris):
- `modules/sahabat_etf/routes.py`, `modules/sahabat_etf/service.py` — blueprint baru, pola sama seperti `modules/budget/`
- `templates/sahabat_etf/index.html` + `static/js/sahabat_etf.js` + CSS (reuse `budget.css` kalau visual cocok, atau file baru kalau tidak)
- URL prefix `/beasiswa/sahabat` — breadcrumb "Eka Tjipta Foundation / Beasiswa / Sahabat ETF", tetap "bernaung" secara URL/nav di bawah Beasiswa meski kode terisolasi
- Entry point: 1 tombol/link baru di toolbar `templates/beasiswa/index.html` (`Sahabat ETF ↗`) — bukan tab-panel baru

**Tidak ada tabel/migrasi baru.** Murni query read dari tabel existing:
- `siswa WHERE program='Sahabat ETF' AND company_id=?`
- `budget_beasiswa` JOIN `siswa` by `siswa_code`
- `payment_beasiswa` JOIN `siswa` by `siswa_code`

**Definisi metrik (dipakai konsisten di semua endpoint):**
- **Budget** = `SUM(budget_beasiswa.amount)` per siswa
- **Payment** = `SUM(payment_beasiswa.amount)` semua status, per siswa
- **Realisasi** = `SUM(payment_beasiswa.amount) WHERE status='complete'`, per siswa
- **Sisa Budget** = Budget − Realisasi
- **Over-budget** = siswa dengan Realisasi > Budget

**Endpoints:**
| Route | Fungsi |
|---|---|
| `GET /beasiswa/sahabat` | Render shell halaman. Guard: company aktif bukan ETF → notice + link ganti company. |
| `GET /beasiswa/sahabat/api/summary` | Per-siswa aggregate (nama, jenjang, angkatan, status, budget/payment/realisasi/sisa) — untuk tabel & chart bar. |
| `GET /beasiswa/sahabat/api/breakdown` | Agregat by `cat1` (Pendidikan/Tunjangan/Wisuda/Penelitian/Medical) untuk chart kategori, + daftar siswa over-budget. |
| `GET /beasiswa/sahabat/api/detail/<siswa_code>` | Raw baris budget + payment untuk 1 siswa (expand-row). |
| `GET /beasiswa/sahabat/export` | Excel (openpyxl), sheet "Summary" + sheet "Detail Transaksi". |

## Design — Section 2: UI Layout, Alert, Export, Testing (✅ approved)

**Scope: read-only + export.** Tambah/edit budget/payment tetap lewat tab Data Budget/Data Payment yang sudah ada di halaman Beasiswa umum — tidak ada logic insert/update duplikat di modul baru ini.

**Layout halaman (single page):**
```
[Breadcrumb: Eka Tjipta Foundation / Beasiswa / Sahabat ETF]
[Toolbar: tombol Export Excel]

[Summary cards]: Total Siswa Aktif | Total Budget | Total Payment | Total Realisasi | Sisa Budget

[Alert card "Siswa Over-Budget"] — hidden kalau tidak ada siswa over-budget

[Chart grid]:
  - Bar chart: Budget vs Realisasi per siswa (11 bar)
  - Donut chart: Realisasi by kategori (cat1)

[Tabel per-siswa]: Nama | Jenjang | Angkatan | Status | Budget | Payment | Realisasi | Sisa
  → klik row = expand detail transaksi mentah (tanggal, cat1/cat2, amount, asal Budget/Payment)
```

**Breakdown dimensi yang dipakai:** per-siswa dan per-kategori (cat1). Breakdown per-tahun dan per-jenjang studi **tidak** termasuk scope ini (bisa ditambah nanti kalau dibutuhkan).

**Snapshot akademik (IPK) sengaja TIDAK dimasukkan** — sudah ada di tab Report Siswa yang existing, tidak diduplikasi di sini. Scope modul ini murni finansial.

**Alert logic:** dihitung on-the-fly di `/api/breakdown` (tidak disimpan ke tabel baru, sama seperti pola notifikasi Budget module) — siswa dengan Realisasi > Budget masuk list alert.

**Export Excel:** reuse pola `openpyxl` yang sudah dipakai di `modules/beasiswa/routes.py` untuk export budget/payment list. 2 sheet: "Summary" (tabel per-siswa) dan "Detail Transaksi" (semua baris budget+payment, dengan kolom sumber). Tidak ada PDF di iterasi ini.

**Error handling:**
- Company aktif bukan ETF → notice + link ganti company (pola existing `dashboard.select_company`)
- 0 siswa Sahabat ETF di company aktif → empty state, bukan error
- Siswa tanpa budget/payment sama sekali → tetap tampil di tabel dengan nilai 0 (list 11 siswa selalu lengkap, tidak hilang)

**Testing:**
- `tests/test_sahabat_etf_service.py` — unit test agregasi (budget/payment/realisasi/sisa per siswa, breakdown cat1, deteksi over-budget) pakai fixture DB kecil (3–4 siswa dummy, campuran status complete/open)
- `tests/test_sahabat_etf_api.py` — integration test endpoint (auth required, company scoping ETF-only, export Excel valid dengan 2 sheet)
- Tidak ada test UI/JS otomatis — konsisten dengan pola testing module lain di project (pytest only; verifikasi JS manual di browser)

## Out of Scope (iterasi ini)

- CRUD budget/payment dari halaman ini (tetap di halaman Beasiswa umum)
- Kolom `realized_amount`/`tgl_realisasi` — tidak dipakai/diisi
- Breakdown per-tahun, per-jenjang studi
- Snapshot akademik/IPK di halaman ini
- Export PDF
- Sistem notifikasi persisten (alert cuma computed-on-load, bukan disimpan/dikirim)

## Next Steps

1. ~~User sign-off pada spec ini~~ — done, 2026-07-14 (brainstorm session, approved section-by-section).
2. Spec self-review: done 2026-07-14 (lihat bawah).
3. Invoke skill `writing-plans` untuk buat implementation plan. Jangan mulai implementasi sebelum itu.
