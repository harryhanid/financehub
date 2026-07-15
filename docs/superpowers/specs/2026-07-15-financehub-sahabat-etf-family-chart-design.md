# Sahabat ETF — Realisasi per Keluarga (Family Chart) — Design Spec

**Date:** 2026-07-15
**Scope:** Modul Sahabat ETF (FinanceHub, Flask, `C:\Financehub`, `modules/sahabat_etf/`) — visualisasi baru di dalam accordion "Detail Tabel" yang mengelompokkan siswa program Sahabat ETF berdasarkan keluarga, menampilkan realisasi per anggota + total per keluarga.
**Status:** Approved for implementation

---

## 1. Problem

Halaman `/beasiswa/sahabat` menampilkan 11 siswa program "Sahabat ETF" sebagai daftar flat di tabel `#setf-table` ("Rincian Budget vs Realisasi per Anggota") — tidak ada cara melihat bahwa beberapa siswa sebenarnya berasal dari keluarga yang sama. User ingin tahu, per keluarga: berapa realisasi (pengeluaran aktual) masing-masing anggota, dan berapa totalnya.

Tidak ada kolom family/keluarga di tabel `siswa` saat ini — data pengelompokan ini murni pengetahuan user, belum ada di database.

## 2. Data — Family Grouping

Pengelompokan di-hardcode di `modules/sahabat_etf/service.py` (bukan kolom DB baru — 11 siswa, jarang berubah, cukup mapping statis di kode):

```python
FAMILY_GROUPS = [
    # (family_key, [siswa_code, ...])
    ("fam1", ["5260002", "1240700", "4220003"]),  # Effendi Widjaja, Cathabell (S1 + record lama SMA)
    ("fam2", ["1240706", "1230684"]),              # Jety Widjaja, Darrell Bright Lie
    ("fam3", ["1260001", "5250001"]),               # Budi Widjaja, Birgitta Jennifer Widjaja
    ("fam4", ["5260003", "5250002"]),               # Burhanuddin Widjaja, Richard Widjaja
    ("fam5", ["5260001"]),                           # Claudia Samaoen (single)
    ("fam6", ["1210487"]),                           # Felicia Tarita Chandra (single)
    ("fam7", ["5230001"]),                           # Joshua Darren Chandra (single)
]
```

Catatan penting: Cathabell Virginia Fernanda Widjaja punya **2 baris `siswa`** (kode `1240700` aktif S1 2024, dan kode `4220003` lulus SMA 2022 — orang yang sama, 2 record historis jenjang). Kedua kode dimasukkan ke `fam1` supaya realisasinya tergabung jadi **1 segmen** di stacked bar (bukan 2 segmen terpisah dengan nama sama).

**Label keluarga** — dihasilkan otomatis dari data, bukan hardcode string:
1. Ambil marga (kata terakhir di `nama`) dari anggota pertama tiap grup.
2. Hitung berapa kali tiap marga muncul di seluruh `FAMILY_GROUPS` (urutan sesuai definisi list di atas).
3. Kalau marga itu muncul lebih dari 1 kali → label `"Keluarga <Marga> <N>"` (N = urutan kemunculan ke berapa, mulai 1). Kalau cuma muncul 1 kali → label `"Keluarga <Marga>"` tanpa angka.

Hasil untuk data saat ini:
| family_key | Label |
|---|---|
| fam1 | Keluarga Widjaja 1 |
| fam2 | Keluarga Widjaja 2 |
| fam3 | Keluarga Widjaja 3 |
| fam4 | Keluarga Widjaja 4 |
| fam5 | Keluarga Samaoen |
| fam6 | Keluarga Chandra 1 |
| fam7 | Keluarga Chandra 2 |

Siswa tunggal (tidak sekeluarga dengan siapapun di program ini) tetap tampil sebagai "keluarga" berisi 1 orang — bukan disembunyikan atau digabung ke grup "Lainnya". Semua 11 siswa selalu punya tepat 1 family_key (tidak ada siswa yang unmapped — kalau ada siswa baru masuk program tanpa entry di `FAMILY_GROUPS`, dia otomatis jadi keluarga sendiri berlabel dari marganya, fallback ini dijelaskan di §5).

## 3. Backend

**`modules/sahabat_etf/service.py`** — fungsi baru `get_family_summary(company_id, years=None, pillars=None)`:

```
1. Panggil get_siswa_summary(company_id, years, pillars) — sumber realisasi per siswa_code, sudah difilter tahun/pillar.
2. Bangun lookup siswa_code -> family_key dari FAMILY_GROUPS.
   - Siswa program Sahabat ETF yang code-nya TIDAK ada di FAMILY_GROUPS manapun -> fallback: family_key = code-nya sendiri (jadi keluarga sendiri).
3. Group baris get_siswa_summary() by family_key.
4. Dalam tiap grup, merge baris dengan `nama` yang sama (kasus Cathabell 2 kode) -> jumlahkan realisasi_total-nya jadi 1 entri member.
5. Hasil per grup: { family_key, label, total_realisasi, members: [{nama, realisasi}, ...] }
   - members diurutkan sesuai urutan kemunculan di FAMILY_GROUPS[family_key] (setelah merge nama-duplikat).
6. Grup diurutkan sesuai urutan definisi FAMILY_GROUPS (fam1..fam7), fallback/unmapped di akhir.
7. Return list of groups.
```

Label dihitung oleh helper terpisah `_family_label(family_key, groups_in_order)` dipanggil dari `get_family_summary`, memakai algoritma §2.

**`modules/sahabat_etf/routes.py`** — endpoint baru, pola identik endpoint `api_*` lain di file ini:

```python
@bp.route("/api/family_summary")
@jwt_html_required
@etf_company_required
def api_family_summary():
    years, pillars = _parse_filters()
    return jsonify({"families": get_family_summary(_cid(), years, pillars)})
```

## 4. Frontend

**Placement** — subsection baru di dalam accordion `#setf-detail-tabel` ("Detail Tabel"), **di atas** tabel `#setf-table` yang sudah ada (bukan accordion terpisah, bukan masuk ke grid "Grafik"):

```html
<div class="setf-accordion-body">
  <div class="table-wrap">
    <h3>Realisasi per Keluarga</h3>
    <canvas id="chart-keluarga"></canvas>
    <div class="setf-compact-scroll">
      <table id="setf-family-table">
        <thead><tr><th>Keluarga</th><th>Nama</th><th class="num-right">Realisasi</th></tr></thead>
        <tbody><tr><td colspan="3" style="text-align:center;color:var(--text-muted)">Memuat data...</td></tr></tbody>
      </table>
    </div>
  </div>

  <div class="table-wrap">
    <h3>Rincian Budget vs Realisasi per Anggota</h3>
    <table id="setf-table"> ... (tidak berubah) ... </table>
  </div>
</div>
```

**`static/js/sahabat_etf.js`**:

- Chart.js **stacked bar**, helper baru `setfRenderStackedBarChart(canvasId, families)` (terpisah dari `setfRenderBarChart` yang sudah ada — tidak diubah, supaya chart lain di halaman ini tidak ikut ter-stacked secara tidak sengaja):
  - `scales.x.stacked = true`, `scales.y.stacked = true`.
  - Labels sumbu-X = `families.map(f => f.label)`.
  - Jumlah dataset = `max(members.length)` di seluruh keluarga (menangani keluarga dengan anggota > 2 di masa depan, bukan di-hardcode 2). Dataset ke-i mewakili "anggota di posisi ke-i" tiap bar; keluarga dengan anggota lebih sedikit dapat nilai 0/null di posisi kosong.
  - Warna segmen dari `SETF_PALETTE` yang sudah ada, cycle per posisi (bukan per nama — posisi konsisten antar bar, warna tiap dataset tetap sama artinya "anggota ke-N dalam keluarga").
  - Tooltip callback custom: tampilkan `nama` anggota sebenarnya (bukan label generik "Anggota 1/2") dengan look up `families[barIndex].members[datasetIndex].nama`, plus nominal via `setfFmtJutaan`.
  - Legend disembunyikan (`plugins.legend.display = false`) — karena dataset per-posisi tidak punya makna universal untuk dijadikan legend; nama anggota sudah cukup jelas lewat tooltip + tabel companion.
- `setfRenderFamilyTable(families)`: render `#setf-family-table` — 1 baris per member (`Keluarga | Nama | Realisasi`), diikuti 1 baris bold per keluarga untuk total (`Keluarga X — Total | | <total_realisasi>`), mengikuti pola visual tabel kategori/pillar yang sudah ada (`setfFmtJutaan` untuk format angka).
- Wiring: di dalam `setfApplyFilters()`, tambahkan fetch ke `/beasiswa/sahabat/api/family_summary` (query string sama seperti fetch lain — reuse `qs` yang sudah dibangun), panggil `setfRenderStackedBarChart` + `setfRenderFamilyTable` di `.then()`. Tambahkan skeleton state untuk `#setf-family-table` di awal `setfApplyFilters()` seperti tabel lain (`skeletonRows(...)`).
- Chart baru didaftarkan di `setfCharts` object yang sudah ada (key `"chart-keluarga"`), otomatis ikut ke-destroy/redraw saat filter berubah atau saat event `fh-theme-changed` — tambahkan `"chart-keluarga"` ke kondisi listener theme-changed yang sudah ada di baris 364-368.

## 5. Error Handling & Edge Cases

- **Siswa baru masuk program tanpa entry di `FAMILY_GROUPS`** → fallback per §3 langkah 2: jadi keluarga sendiri (family_key = kode dia), label dihitung otomatis dari marga (ikut aturan penomoran §2). Tidak error, tidak hilang dari chart.
- **Filter tahun/pillar membuat semua realisasi keluarga jadi 0** → chart tetap render (bar setinggi 0 / kosong), tabel companion tetap tampil semua keluarga dengan nilai Rp 0, bukan disembunyikan — konsisten dengan tabel Kategori/Pillar yang sudah ada (selalu tampilkan semua baris, biar user tahu keluarga itu memang tidak ada transaksi di periode terpilih).
- **Belum ada data siswa Sahabat ETF sama sekali** (kasus ekstrem/DB kosong) → `get_family_summary` return list kosong, chart & tabel tampilkan empty state sama seperti tabel lain di halaman ini ("Belum ada data").
- **Wrong company (bukan ETF)** → sudah di-guard oleh `wrong_company` di HTML level + `etf_company_required` di API level (pola existing, tidak berubah).

## 6. Testing

Ikuti konvensi project (pytest, `app/tests/`, fixture `app`/`client`/`clean_db`):
- Unit test `get_family_summary()`: grouping benar sesuai `FAMILY_GROUPS`, 2 kode Cathabell ter-merge jadi 1 member dengan realisasi terjumlah.
- Unit test label generation: marga berulang dapat suffix angka urut, marga unik tidak dapat suffix.
- Unit test fallback: siswa dengan kode yang tidak ada di `FAMILY_GROUPS` manapun tetap muncul sebagai keluarga sendiri.
- Test filter years/pillars diteruskan dengan benar ke `get_family_summary` (hasil realisasi berubah sesuai filter, sama seperti `get_siswa_summary`).
- Test route `/beasiswa/sahabat/api/family_summary`: guard company ETF, format response `{"families": [...]}`.
- Test total per keluarga = sum realisasi seluruh member di keluarga itu (invariant yang harus selalu benar).

## 7. Out of Scope (versi ini)

- **Kolom `keluarga_id` di tabel `siswa` / UI admin untuk edit grouping** — tetap hardcode di kode untuk versi ini; migrasi ke kolom DB bisa jadi iterasi berikutnya kalau jumlah siswa program ini bertambah signifikan.
- **Toggle budget vs realisasi di chart keluarga** — versi ini realisasi saja (sesuai kebutuhan "pengeluaran"), tidak ada switcher.
- **Drill-down klik bar keluarga → filter tabel transaksi** (seperti drill-down kategori yang sudah ada di chart lain) — tidak diminta, bisa jadi enhancement terpisah nanti.
- **Data label total di atas tiap bar (chart.js datalabels plugin)** — total sudah tersedia di tabel companion, tidak perlu tambah dependency plugin baru untuk versi ini.

## 8. Success Criteria

- [ ] Section "Realisasi per Keluarga" muncul di accordion "Detail Tabel", di atas tabel existing, tidak mengubah section lain
- [ ] Stacked bar chart menampilkan 7 keluarga (4 multi-anggota + 3 single) dengan label sesuai aturan penomoran marga
- [ ] Realisasi Cathabell (2 kode siswa) tergabung jadi 1 segmen di keluarga Widjaja 1, bukan 2 segmen terpisah
- [ ] Tabel companion menampilkan nama + realisasi tiap anggota, plus total per keluarga
- [ ] Chart & tabel keluarga ikut ter-update saat filter Tahun/Pillar di atas halaman diganti
- [ ] Chart ikut redraw saat event `fh-theme-changed` (ganti dark/light mode), konsisten dengan chart lain di halaman
- [ ] Guard company ETF berlaku di endpoint baru (`etf_company_required`)
- [ ] Test suite Sahabat ETF (existing + baru) tetap hijau
