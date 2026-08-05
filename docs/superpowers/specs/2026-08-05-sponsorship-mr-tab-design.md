# Sponsorship — MR (Management Report) Tab — Design

## Problem

Sinar Mas Tjipta (SMT) / Sponsorship saat ini punya 4 tab: Dashboard,
Input, Data, Outstanding, Report. Tidak ada satupun yang menghasilkan
format standar "MR" (Management Report) — sebuah baris jurnal per
transaksi sponsorship, 17 kolom tetap, yang saat ini disusun manual di
Excel (lihat contoh yang diberikan user) untuk keperluan upload ke sistem
GL/akuntansi. Setiap transaksi baru di tab Data berarti baris MR baru
harus disusun manual, termasuk nomor urut "New Code" yang formatnya
tergantung tahun.

## Decisions (confirmed with user)

1. **Bentuk tab**: tabel on-screen (server-rendered, pola sama seperti
   Data/Outstanding) + tombol "Export to Excel" — bukan export-only.
2. **Cakupan data**: semua baris `sponsorship_transaksi` company SMT,
   difilter **hanya oleh Tahun** (checkbox multi-select, pola sama seperti
   tab Report / `_parse_report_params()`). Tidak ada filter cat/pillar/
   description/status — MR tidak peduli kategori apapun, semua baris ikut
   selama tahunnya cocok.
3. **Reset nomor urut "New Code"**: reset ke 1 setiap ganti tahun (CC0).
   Kalau user pilih 2 tahun sekaligus (mis. 2025 + 2026), masing-masing
   grup tahun punya nomor urut sendiri mulai dari 1.
4. **Urutan baris**: `tanggal_form_sponsor ASC`, tie-break `id ASC`
   (kronologis tertua dulu — cocok konvensi buku besar/jurnal, beda dari
   default tab Data yang DESC).
5. **Kolom "Month"**: `=MONTH([@Date])` polos, angka 1–12 tanpa leading
   zero. `;1` di formula asli user adalah sisa notasi Excel, bukan bagian
   logika.
6. **Kolom D "Allocation Memo"**: gabungan `description + " - " +
   lembaga_perorangan + " - " + perihal`, bagian yang kosong di-skip
   (tidak menyisakan `" - "` ganda/trailing).
7. **Kolom bertanda "by default"** (ID#, Budget Activity, Account
   Management, COA HO, COST CENTER, COST CENTER2, CC1, BC1, BC): **read-
   only**, murni hasil hitung/konstanta — tidak ada input manual di layar
   MR. Kalau butuh nilai beda per baris, user edit di sumbernya (tab Data)
   atau di file Excel hasil export.
8. Semua kolom dihitung di Python dan ditulis sebagai **nilai final** ke
   Excel (bukan formula live) — konsisten dengan `export_report_excel`,
   `export_data_excel`, `export_outstanding_excel` yang sudah ada di
   `exports.py`.
9. Tidak ada pagination — tampil semua baris sesuai filter tahun,
   konsisten dengan pola Outstanding/Report (bukan pola Data yang
   volumenya tinggi).

## Column Mapping

Dihitung per baris `sponsorship_transaksi`, di dalam service function
baru `get_sponsorship_mr(company_id, tahun: list[str])`:

| # | Kolom | Sumber / Formula |
|---|---|---|
| A | Account Management | konstanta `SPONSORSHIP_MR_ACCOUNT_MANAGEMENT = "70107800"` |
| B | ID# | kosong |
| C | Date | `tanggal_form_sponsor` |
| D | Allocation Memo | `description` + `" - "` + `lembaga_perorangan` + `" - "` + `perihal`, skip bagian kosong |
| E | Budget Activity | kosong |
| F | COST CENTER | konstanta `SPONSORSHIP_MR_COST_CENTER = "POSPON"` |
| G | DEBIT - CREDIT | `amount_request` |
| H | Source | konstanta `SPONSORSHIP_MR_SOURCE = "Sponsor"` |
| I | COA HO | konstanta `SPONSORSHIP_MR_COA_HO = "70107800"` |
| J | COST CENTER2 | konstanta `SPONSORSHIP_MR_COST_CENTER2 = "$POCCOM"` |
| K | Month | `MONTH(Date)` → 1–12 |
| L | CC0 | 2 digit terakhir tahun `Date`, mis. `"26"` |
| M | CC1 | konstanta `SPONSORSHIP_MR_CC1 = "5"` |
| N | BC1 | konstanta `SPONSORSHIP_MR_BC1 = "-25-"` |
| O | New Code | `"A" + CC0 + "-" + CC1 + BC1 + seq` — `seq` reset ke 1 tiap ganti CC0 (tahun), lanjut per urutan baris (keputusan #4) |
| P | Memo | `"- Act " + tahun + " : " + AllocationMemo + " Month : " + Month` |
| Q | BC | konstanta `SPONSORSHIP_MR_BC = "Sponsorship - Non Building"` |

Konstanta A/F/H/I/J/M/N/Q disimpan di `config.py` (pola sama seperti
`SPONSORSHIP_CAT`, `SPONSORSHIP_PILLARS`, dst.), bukan hardcode di
service/exports — supaya gampang diubah kalau kebutuhan berubah.

Contoh hasil (dari input user), untuk validasi implementasi:

```
Account Management | ID# | Date     | Allocation Memo                                              | Budget Activity | COST CENTER |  DEBIT - CREDIT | Source | COA HO   | COST CENTER2 | Month | CC0 | CC1 | BC1  | New Code   | Memo                                                                          | BC
70107800            |     | 20-Jan-26| Partisipasi Pemasangan Lampion dan Lilin Tahun Baru Imlek 2026|                  | POSPON      |      25.000.000 | Sponsor| 70107800 | $POCCOM      | 1     | 26  | 5   | -25- | A26-5-25-1 | - Act 2026 : Partisipasi Pemasangan Lampion dan Lilin Tahun Baru Imlek 2026 Month : 1 | Sponsorship - Non Building
70107800            |     | 20-Jan-26| Prasasti Membership                                          |                  | POSPON      |     500.000.000 | Sponsor| 70107800 | $POCCOM      | 1     | 26  | 5   | -25- | A26-5-25-2 | - Act 2026 : Prasasti Membership Month : 1                                   | Sponsorship - Non Building
```

Catatan: contoh di atas cuma menampilkan `Allocation Memo` sebagai satu
kalimat pendek — kemungkinan karena `description`/`lembaga_perorangan`
kosong untuk baris tersebut di data asli, sehingga concat efektif jatuh
ke `perihal` saja. Logika concat (keputusan #6) tetap menggabungkan
ketiganya kalau semua terisi.

## Architecture

Mengikuti pola modul Sponsorship yang sudah ada (Report/Outstanding),
satu fungsi service dipakai bersama oleh route halaman dan route export
— tidak ada duplikasi logika:

```
routes.py
  mr_page()          → get_sponsorship_mr() → render templates/sponsorship/mr.html
  export_mr_route()  → get_sponsorship_mr() → exports.export_mr_excel()

service.py
  get_sponsorship_mr(company_id, tahun: list[str]) -> list[dict]
    - query sponsorship_transaksi WHERE company_id=? AND strftime('%Y', tanggal_form_sponsor) IN (...)
    - ORDER BY tanggal_form_sponsor ASC, id ASC
    - group by tahun, hitung seq per grup untuk New Code
    - return list of dict, satu dict per baris MR (17 kolom)

exports.py
  export_mr_excel(company_id, tahun) -> bytes
    - panggil get_sponsorship_mr()
    - tulis ke openpyxl Workbook, styling header 3-band (navy A-H, merah I-N, navy O-Q)
```

### Routes (`modules/sponsorship/routes.py`)

- `GET /sponsorship/mr` → `mr_page()`
  - Reuse `_parse_report_params()`-style parsing untuk `tahun` (tanpa
    `cat4`, tidak dipakai di MR) — default ke tahun terbaru yang ada
    data via `get_available_years(_cid())`.
  - Guard company via `wrong_company` flag (pola sama seperti
    Data/Outstanding/Report — halaman tetap render, tapi kosong + notice
    kalau company bukan SMT).
- `GET /sponsorship/mr/export` → `export_mr_route()`
  - `@smt_company_required` — guard eksplisit di route export sendiri
    (bukan cuma di halaman), mengikuti catatan keamanan dari finding
    Bank Sahabat ETF (2026-07-14): guard di index page saja tidak cukup
    untuk endpoint API/export yang bisa diakses langsung.
  - Response `send_file` dengan `download_name=f"Sponsorship_MR_{tahun}.xlsx"`
    (tahun = join tahun terpilih dengan `-`, mis. `2025-2026`).

### Template (`templates/sponsorship/mr.html`)

- Extend `base.html`, include `_toolbar.html` (dengan link baru "MR").
- Filter bar: checkbox Tahun (dropdown multi-select, pola sama seperti
  Report — lihat `budget-dropdown-check`/`.filter-bar`).
- Tabel 17 kolom, render server-side (`{% for r in rows %}`), header
  berwarna 3-band meniru contoh (navy A-H, merah I-N, navy O-Q) supaya
  preview di layar konsisten dengan hasil Excel.
- Tombol "Export to Excel" → `GET /sponsorship/mr/export?tahun=...`.

### Toolbar (`_toolbar.html`)

Tambah 1 link baru setelah "Report":
```html
<a class="tab-btn{{ ' active' if active_tab == 'mr' else '' }}" href="{{ url_for('sponsorship.mr_page') }}">MR</a>
```

### Config (`config.py`)

```python
SPONSORSHIP_MR_ACCOUNT_MANAGEMENT = "70107800"
SPONSORSHIP_MR_COST_CENTER        = "POSPON"
SPONSORSHIP_MR_SOURCE             = "Sponsor"
SPONSORSHIP_MR_COA_HO             = "70107800"
SPONSORSHIP_MR_COST_CENTER2       = "$POCCOM"
SPONSORSHIP_MR_CC1                = "5"
SPONSORSHIP_MR_BC1                = "-25-"
SPONSORSHIP_MR_BC                 = "Sponsorship - Non Building"
```

## Error Handling

- Tahun tanpa data: halaman render tabel kosong + pesan "Tidak ada data
  untuk tahun terpilih" (pola sama seperti Report saat `sections` kosong).
- Company bukan SMT: `wrong_company` notice di halaman; route export
  balas 403 JSON (pola `smt_company_required` yang sudah ada).
- `perihal`/`lembaga_perorangan`/`description` null di DB: `Allocation
  Memo` concat menangani `None` sebagai string kosong (skip, tidak
  menyisipkan "None" literal).

## Testing Plan

Ditulis saat eksekusi plan (TDD — test dulu, baru implementasi), mengikuti
pola test file yang sudah ada untuk Report:

- `tests/test_sponsorship_mr_service.py`
  - Mapping tiap kolom sesuai tabel di atas, untuk baris dengan semua
    field terisi maupun sebagian kosong (`perihal`/`lembaga_perorangan`
    null).
  - Reset nomor urut "New Code" per tahun saat `tahun` filter mencakup
    lebih dari 1 tahun.
  - Urutan baris `tanggal_form_sponsor ASC, id ASC`, termasuk kasus
    tanggal sama (tie-break id).
- `tests/test_sponsorship_mr_export.py`
  - File Excel ke-generate, header 17 kolom benar, jumlah baris cocok
    jumlah transaksi, nilai kolom G (Debit-Credit) dan O (New Code)
    tervalidasi terhadap contoh dari user.
- `tests/test_sponsorship_routes.py` (tambahan case)
  - `GET /sponsorship/mr` dan `/sponsorship/mr/export` ditolak 403 untuk
    company bukan SMT (regresi guard, pola yang sudah ada untuk
    endpoint Sponsorship lain).

## Out of Scope

- Edit manual per baris di layar MR (keputusan #7 — read-only).
- Filter selain Tahun (cat/pillar/description/status) — semua baris ikut
  tanpa syarat lain.
- Import balik dari Excel MR ke `sponsorship_transaksi` (MR murni
  output/laporan, bukan jalur input data).
