# Modul Sahabat ETF — Filter Tahun/Pillar & Chart Bulanan — Design

> **Status: APPROVED (user sign-off 2026-07-14, brainstorm session).** Implementation plan not yet written. Do not start implementation before that.
>
> Follow-up terhadap [2026-07-14-sahabat-etf-module-design.md](2026-07-14-sahabat-etf-module-design.md) — modul dasarnya sudah merged ke `master` (commit gabungan, branch `feat-sahabat-etf-module`, 9 task TDD + 1 security fix di final review).

## Context / Why

Modul Sahabat ETF (`/beasiswa/sahabat`) sudah live: summary cards, bar chart budget-vs-realisasi per siswa, donut chart realisasi per kategori, alert over-budget, tabel per-siswa, export CSV (summary + detail). Semuanya menampilkan **agregat sepanjang masa** (all-time), tanpa filter.

User butuh 2 tambahan:
1. Filter/visualisasi realisasi pembayaran berdasarkan **tahun payment** — data live ternyata multi-tahun (payment tersebar dari **2020-03-10 sampai 2026-07-13**, 61 baris).
2. Filter berdasarkan **kolom `pillar`** di `payment_beasiswa` — meski kolom ini secara resmi "tidak reliable" sebagai penanda pillar ETF PA baku (dicatat di spec modul dasar), data live untuk siswa Sahabat ETF ternyata punya 3 nilai berbeda: `APP` (15), `FINANCE` (24), `SETF` (22) — jadi tetap ada variasi yang bisa difilter, meski labelnya bukan taksonomi pillar yang bersih.

Plus 1 kebutuhan baru yang muncul saat brainstorm: chart bar bulanan (budget vs realisasi per bulan), menggantikan chart per-siswa yang sekarang.

## Research Findings (diverifikasi terhadap `finance_hub.db` live, 2026-07-14)

**Distribusi `pillar`** untuk payment siswa Sahabat ETF: `APP`=15, `FINANCE`=24, `SETF`=22 baris. Tidak hardcode — opsi dropdown diambil dinamis dari `DISTINCT pillar`.

**Rentang tanggal payment**: 2020-03-10 s/d 2026-07-13. Rentang tahun cukup lebar (7 tahun) — filter tahun jadi genuinely berguna, bukan cuma nice-to-have.

## Design — Section 1: Data & Backend (✅ approved)

**Perubahan service functions** (`modules/sahabat_etf/service.py`), semuanya **backward-compatible** (parameter baru opsional, default `None` = behavior lama, tidak breaking 26 test existing):

- `get_siswa_summary(company_id, years: list[int] = None, pillar: str = None)`
- `get_kategori_breakdown(company_id, years=None, pillar=None)`
- `get_all_transactions(company_id, years=None, pillar=None)`
- `get_siswa_detail` — **tidak diubah** (scope-nya 1 siswa spesifik, bukan agregat lintas populasi; filter tahun/pillar tidak relevan di level ini)

**Cara filter tahun diterapkan**: independen per tabel sumber — baris `budget_beasiswa` difilter dari `budget.tanggal`-nya sendiri, baris `payment_beasiswa` difilter dari `payment.tanggal`-nya sendiri (bukan disamakan ke satu tanggal acuan). `years` adalah list (multi-select), jadi filter pakai `strftime('%Y', tanggal) IN (?, ?, ...)`.

**Cara filter pillar diterapkan**: `payment_beasiswa.pillar = ?` — filter ini **hanya memengaruhi baris payment/realisasi** (sesuai permintaan awal: "filter kategori Realisasi payment berdasarkan pillar"). Koreksi riset: `budget_beasiswa` **juga** punya kolom `pillar` (`AGRI`=27, `APP`=13, `FINANCE`=15, `SETF`=23 baris untuk siswa Sahabat ETF) — tapi sengaja **tidak** dipakai untuk filter budget di iterasi ini, scope-nya memang cuma realisasi payment. Budget tetap tampil apa adanya, tidak ikut menyempit walau filter pillar aktif.

**Konsekuensi ke alert over-budget**: `over_budget` di `get_kategori_breakdown` dihitung dari `get_siswa_summary(company_id, years, pillar)` — otomatis ikut ter-filter. Artinya alert jadi "over-budget untuk kombinasi tahun+pillar yang sedang difilter", bukan sepanjang masa. Behavior ini disetujui user secara implisit (tidak ada keberatan saat didiskusikan).

**Fungsi baru** `get_monthly_breakdown(company_id, years: list[int], pillar: str = None) -> dict`:
- Return shape: `{"chart_year": int, "months": [{"bulan": 1..12, "budget": float, "realisasi": float}, ...], "comparison": [{"bulan": 1..12, "per_tahun": {"2025": float, "2026": float, ...}}, ...]}`
- `chart_year` = tahun **terbaru (termuda)** dari `years` yang dipilih — dipakai untuk 12 bucket `months` (chart bar).
- `comparison` = realisasi-only, per bulan, per **semua** tahun di `years` (untuk tabel banding).
- **Zero-fill wajib**: 12 bucket Jan-Des selalu ada di kedua struktur, walau nilainya 0 — supaya bentuk chart/tabel konsisten, tidak ada bulan yang hilang.
- `budget` dihitung dari `budget.tanggal` di `chart_year`; `realisasi` dari `payment.tanggal` berstatus `complete` di tahun terkait.

**API routes** (`modules/sahabat_etf/routes.py`):
- `/api/summary`, `/api/breakdown` — tambah query param opsional `?years=2025,2026&pillar=SETF`, diteruskan ke service function terkait. Tanpa param = behavior lama (semua data).
- `/api/detail/<code>` — **tidak berubah** (lihat alasan di atas).
- `/api/monthly` — route baru, wajib param `years` (comma-separated tahun terpilih), opsional `pillar`.
- `/export/summary`, `/export/detail` — tambah query param yang sama, diteruskan ke service function yang sama persis dengan `/api/*` — jadi CSV otomatis konsisten dengan apa yang sedang ditampilkan di layar.
- Semua route baru/berubah tetap di balik `@jwt_html_required` + `@etf_company_required` (decorator yang sudah ada dari security fix modul dasar, dipakai ulang tanpa perubahan).

## Design — Section 2: UI Layout (✅ approved)

**Filter bar baru** — ditaruh di atas summary cards (bawah breadcrumb, dekat toolbar export):
- Checkbox list tahun (opsi dinamis dari data, multi-select/tick, default: hanya tahun terbaru tercentang)
- Dropdown pillar (opsi dinamis dari data, single-select, default "Semua Pillar")
- **Interaksi auto-apply** (`onchange`, tanpa tombol submit) — konsisten dengan pola filter existing di `templates/beasiswa/index.html` (`pay-filter-pillar`, `pay-filter-tahun`, dst, semua sudah pakai pola ini).

**Perubahan chart grid:**
- Chart kiri: ~~"Budget vs Realisasi per Siswa"~~ → **"Budget vs Realisasi per Bulan"** — bar chart 12 bulan (Jan-Des) untuk `chart_year` (tahun terbaru dari yang dicentang).
- Chart kanan: "Realisasi per Kategori" (donut) — tetap ada, sekarang ikut ter-filter tahun+pillar.
- **Tabel baru** di bawah chart grid: **"Perbandingan Realisasi per Bulan per Tahun"** — baris = Bulan (Jan-Des), kolom = 1 kolom per tahun yang dicentang (realisasi-only, bukan budget). Ini yang menangani kasus multi-tahun dicentang — chart tetap simpel (1 tahun), tabel yang menampung perbandingan lintas tahun.

**Tidak berubah**: 5 summary card, alert over-budget card, tabel per-siswa existing, 2 tombol export CSV (cuma URL-nya nempel query string filter aktif).

**Re-fetch behavior**: tiap filter berubah → 1 fungsi terpusat (mis. `setfApplyFilters()`) re-fetch `/api/summary`, `/api/breakdown`, `/api/monthly` sekaligus, lalu render ulang semua bagian yang bergantung. Mirror pola `initSahabatEtf()` yang sudah ada, dibungkus supaya bisa dipanggil ulang saat filter berubah (bukan cuma sekali saat page load).

## Design — Section 3: Testing (✅ approved)

- `test_sahabat_etf_service.py`: tambah test per fungsi yang di-extend (`get_siswa_summary`, `get_kategori_breakdown`, `get_all_transactions`) — filter tahun tunggal, filter pillar tunggal, kombinasi, dan **tanpa filter = behavior lama tidak berubah** (regression guard eksplisit).
- Test baru untuk `get_monthly_breakdown`: zero-fill 12 bulan walau kosong, `chart_year` = tahun terbaru yang benar saat multi-year dipilih, struktur `comparison` benar untuk multi-tahun.
- `test_sahabat_etf_routes.py`: query param di 3 API + 2 export route, route `/api/monthly` baru (termasuk guard `etf_company_required` tetap berlaku — reuse, tidak diubah), dan sebuah test memverifikasi CSV export benar-benar berubah isinya sesuai filter yang dikirim.
- Regresi: 26 test existing modul ini harus tetap hijau (parameter baru semuanya opsional).

## Out of Scope (iterasi ini)

Rekomendasi tambahan yang dibahas saat brainstorming tapi **tidak** masuk scope ini (bisa jadi iterasi berikutnya kalau dibutuhkan):
- Drill-down detail per siswa di UI (klik nama → panel detail transaksi mentah) — backend (`/api/detail/<code>`) sudah ada dari modul dasar, tinggal disambung ke UI kapan pun dibutuhkan.
- Search nama siswa di tabel (client-side).
- Filter status siswa (Aktif/Non-aktif).
- Breakdown per-jenjang studi.
- Sistem notifikasi persisten untuk alert over-budget (tetap computed-on-load).

## Next Steps

1. ~~User sign-off pada spec ini~~ — done, 2026-07-14 (brainstorm session, approved section-by-section).
2. Spec self-review: pending.
3. Invoke skill `writing-plans` untuk buat implementation plan. Jangan mulai implementasi sebelum itu.
