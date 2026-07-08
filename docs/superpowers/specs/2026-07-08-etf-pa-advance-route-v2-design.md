# FinanceHub — ETF Payment Application: Route GL vs Advance — Design v2 (koreksi alur)

Status: Approved (brainstorming)
Tanggal: 2026-07-08
Supersedes: `2026-07-07-etf-pa-advance-route-design.md` (v1) — v1 sudah diimplementasikan &
di-merge ke master (branch `etf-pa-advance-route`, commit `8d9b9f5..ba3565b`), tapi salah
menaruh Route selector + tab Advance di modul **Payment Memo** alih-alih di modul
**ETF Payment Application**, dan salah menaruh titik keputusan Route di waktu *tarik ke PAM*
padahal seharusnya di waktu *create PA*. Dokumen ini mengoreksi alur tersebut.

## Apa yang Salah di v1

v1 menaruh:
- Dropdown Route (`#ipay-route`) di panel **Input** modul **Payment Memo** (`/payment-memo`,
  `templates/payment_memo/index.html`) — dipilih manual setiap kali PA ditarik ke PAM.
- Tab **Advance** baru (`tab-pa-advance`) juga di modul **Payment Memo**.
- Kolom Route di tabel AGRI/APP/LAND/SETF milik modul **ETF Payment Application**
  (`templates/etf_payment_application/index.html`) — bagian ini kebetulan sudah benar
  lokasinya, tapi datanya kosong sampai baris ditarik ke PAM (karena Route baru diketahui
  saat itu, bukan saat PA dibuat).

Masalah bisnisnya: Route (GL vs Advance) itu keputusan yang melekat pada **PA itu sendiri**
saat dibuat (siswa/vendor ini dibayar advance atau bukan sudah diketahui sejak PA diajukan),
bukan keputusan yang dibuat ulang setiap kali PA itu ditarik ke pembayaran. v1 menaruh titik
keputusan di tempat yang salah.

## Approach

Reuse total infrastruktur backend v1 yang sudah benar (Task 4/5/7: cascade status
`payment_beasiswa.status='paid'`, `get_advance_payments`, route `/advance/list` &
`/advance/<id>/realize`) — bagian ini murni soal *pembayaran PAM Advance yang sudah ditarik*,
tidak bergantung pada di mana Route dipilih. Yang dikoreksi hanya: (1) kapan/di mana Route
dipilih, (2) kolom Route pindah level ke PA header, (3) tab Advance baru ditambahkan di modul
yang benar, (4) realisasi diperluas untuk ikut menutup PA header.

## 1. Data Model

### Kolom baru di PA header (`etf_pa`, `app_pa`, `sml_pa`, `setf_pa`)
```sql
ALTER TABLE etf_pa  ADD COLUMN route TEXT DEFAULT 'gl';  -- 'gl' | 'advance'
ALTER TABLE app_pa  ADD COLUMN route TEXT DEFAULT 'gl';
ALTER TABLE sml_pa  ADD COLUMN route TEXT DEFAULT 'gl';
ALTER TABLE setf_pa ADD COLUMN route TEXT DEFAULT 'gl';
```
Ini jadi **sumber kebenaran** Route — dipilih sekali saat `create_pa`, tidak berubah lagi
setelahnya (1 PA = 1 route, konsisten seumur hidup PA itu).

### Kolom `route` di `*_pa_lines` (sudah ada dari v1) — tetap dipakai
Tidak dihapus. Fungsi berubah jadi **salinan denormalized** dari `route` header, di-stamp
otomatis oleh `create_pa()` ke setiap baris saat PA dibuat (bukan lagi diisi belakangan oleh
`save_pa_payment` saat ditarik). Tujuannya murni supaya kolom Route yang sudah tampil di
tabel AGRI/APP/LAND/SETF (v1 Task 8) tidak perlu dirombak tampilannya.

### Kolom di `payment_beasiswa` (sudah ada dari v1) — tidak berubah
`advance_amount`, `realized_amount`, `tgl_realisasi` tetap seperti v1. `etf_pa_line_id`
(kolom lama, dipakai generic lintas pillar meski namanya menyebut "etf") tetap jadi kunci
untuk melacak balik ke baris PA asal saat realisasi.

## 2. Status Flow

### PA header (`etf_pa.status` dst.) — status baru `'paid'`
| Tahap | route='gl' (tidak berubah) | route='advance' (baru) |
|---|---|---|
| PA dibuat | `open` | `open` |
| Ditarik ke PAM | `on_process` | `on_process` |
| PAM dibayar (`tanggal_bayar` diisi) | `complete` (langsung) | **`paid`** (baru — menunggu realisasi) |
| Realisasi disimpan | — (tidak ada tahap ini) | `complete` |

`set_pam_complete_cascade` (backend v1, tidak berubah logic-nya) sudah menghasilkan
`payment_beasiswa.status='paid'` untuk PAM pillar `ADVANCE`. Yang ditambah di v2: saat itu
juga, cascade men-set PA header terkait jadi `status='paid'` (bukan `'complete'`) — ini murni
penyesuaian di titik yang sama, bukan alur baru.

### `pam_records` / `payment_beasiswa` — tidak berubah dari v1
Tabel status flow §2 di spec v1 (baris 74-92) tetap berlaku apa adanya.

## 3. Alur Create PA (modul ETF Payment Application → tab Input)

Form "Buat Payment Application Baru" (`templates/etf_payment_application/index.html`, bagian
`{% elif active_tab == 'input' %}`) dapat 1 field baru:

```html
<div>
  <label>Route</label>
  <select id="pa-route">
    <option value="gl" selected>GL</option>
    <option value="advance">Advance</option>
  </select>
</div>
```

`create_pa(company_id, header, lines, tab, route="gl")` — param baru, default `"gl"`
(regresi aman). Disimpan ke `{pa_tbl}.route` header, dan di-stamp ke setiap
`{lines_tbl}.route` saat INSERT baris (menggantikan perilaku v1 yang meninggalkan kolom ini
NULL sampai ditarik).

## 4. Tab "Advance" Baru (modul ETF Payment Application)

Tab baru sejajar `Open PA | Advance | Input | AGRI | APP | LAND | SETF` (nambah 1 entry di
loop Jinja tab bar, `templates/etf_payment_application/index.html` baris ~230).

**Scope: company-wide lintas 4 pillar** (UNION `etf_pa`+`app_pa`+`sml_pa`+`setf_pa`, masing2
join `*_pa_lines`+`siswa`), 1 tabel dengan kolom **Pillar** (AGRI/APP/LAND/SETF) buat bedain
asalnya. Filter status: `Open` (belum ditarik) / `On Process` (sudah ditarik, belum dibayar) /
`Paid` (sudah dibayar, menunggu realisasi) / `Complete` (selesai) — baca dari `{pa_tbl}.status`.

Backend: fungsi baru `get_pa_advance_list(company_id, status_filter="")` di
`modules/etf_payment_application/service.py`, query UNION ALL ke 4 pasang tabel via
`_TAB_CFG`, filter `WHERE route='advance'`. Route baru: `GET /etf-payment-application/advance-list`.

## 5. Alur Tarik ke PAM (modul Payment Memo → Input)

- **Dropdown `#ipay-route` dihapus** dari `templates/payment_memo/index.html` (v1 Task 8
  menambahkannya, sekarang dihapus lagi — Route bukan lagi keputusan di titik ini).
- `save_pa_payment` **tidak lagi baca `data.get("route")` dari request body**. Sebagai
  gantinya: setelah resolve `line_ids` dari `rows` (kode existing baris ~830), query
  `SELECT DISTINCT route FROM {lines_tbl} WHERE id IN (...)` untuk dapat route asli dari
  PA-nya.
  - Kalau hasilnya lebih dari 1 nilai distinct (campuran gl+advance) → **tolak**,
    `{"ok": False, "pesan": "Baris yang dipilih berasal dari PA dengan route berbeda (GL dan Advance tidak bisa digabung dalam satu PAM). Pisahkan submission-nya."}`.
  - Kalau seragam → itulah `route` yang dipakai untuk `insert_payment_rows(..., route=route)`
    dan `pillar_for_pam` (logic sisanya sama seperti v1).
- `insert_payment_rows` (Task 2 v1, `modules/beasiswa/service.py`) — **tidak berubah**,
  signature `route` param-nya tetap sama, cuma sekarang dipanggil dengan nilai yang di-derive,
  bukan dari input manual user.
- Baris lama di `save_pa_payment` (§4 langkah 4 v1) yang melakukan
  `UPDATE {lines_tbl} SET route=? WHERE id IN (...)` saat PA ditarik **dihapus** — sekarang
  jadi no-op berbahaya (bisa menimpa route asli kalau ada bug di derivasi), karena `route`
  sudah final sejak `create_pa()`. Tarik PA tidak lagi menulis kolom `route` sama sekali.

## 6. Realisasi — Extend `realize_advance_payment`

Fungsi yang sudah ada (`modules/payment_memo/service.py`) diperluas, bukan dibuat ulang.
Tambahan di akhir fungsi (setelah update `payment_beasiswa` + cek `pam_records.pillar`):

1. Resolve pillar & lines_tbl/pa_tbl dari `payment_beasiswa.pillar` milik baris yang
   direalisasi (pakai `_TAB_CFG`/mapping pillar→tab yang sama seperti `save_pa_payment`).
2. `UPDATE {lines_tbl} SET jumlah_pembayaran=? WHERE id=?` — pakai `payment_beasiswa.etf_pa_line_id`,
   angka = `realized_amount`.
3. Setelah update baris, cek: kalau **semua** baris `{lines_tbl}` milik `pa_id` yang sama
   sudah tidak berstatus advance-pending (via join balik ke `payment_beasiswa` yang sudah
   `complete`), `UPDATE {pa_tbl} SET status='complete' WHERE id=?`.
   - Simplifikasi: karena 1 PA = 1 route = ditarik ke 1 PAM (§5 di atas menjamin ini), maka
     "semua baris PA itu complete" ekuivalen dengan "PAM yang menaunginya sudah selesai
     direalisasi seluruhnya" — reuse pengecekan `remaining == 0` yang sudah ada di fungsi ini
     untuk `pam_records.pillar`, tinggal tambah 1 UPDATE lagi ke `{pa_tbl}` di percabangan yang
     sama.

## 7. Yang TIDAK Berubah dari v1

- `modules/beasiswa/service.py::insert_payment_rows` — signature & snapshot `advance_amount`
  sama persis.
- `set_pam_complete_cascade` — logic `payment_beasiswa.status='paid'` untuk pillar `ADVANCE`
  sama persis (cuma ditambah 1 UPDATE ke PA header sesuai §2).
- `get_advance_payments` + route `/payment-memo/advance/list` — tetap berlaku apa adanya,
  ini view di level `payment_beasiswa` (setelah ditarik ke PAM), bukan level PA.
- Tab **Advance** yang sudah ada di modul **Payment Memo** (`tab-pa-advance`,
  `loadPaAdvance()`) — **tetap ada**, tidak dihapus. Ini tempat tombol "Realisasi" ditekan
  (level pembayaran/PAM, muncul setelah `status='paid'`). Tab Advance baru di ETF Payment
  Application (§4) adalah level PA (tracking sebelum & sesudah ditarik) — sudut pandang beda,
  saling melengkapi.
- Route `/payment-memo/advance/<id>/realize` — tetap endpoint yang sama, cuma implementasi
  `realize_advance_payment` di baliknya diperluas (§6).

## 8. Migration Notes

Belum ada data produksi yang lewat alur v1 (fitur baru merge ke master, belum dipakai user
untuk transaksi riil) — tidak perlu backfill data lama. `route` kolom baru di PA header
default `'gl'`, PA lama otomatis dianggap GL (aman).

## 9. Testing

- Regresi: seluruh test v1 (`test_advance_route_schema.py`, `test_pam_service.py`,
  `test_pam_pa_cascade.py`, `test_memo_api.py`) tetap hijau untuk jalur `route='gl'`.
- Baru: `create_pa(..., route="advance")` → header + semua baris ter-stamp `route='advance'`.
- Baru: `save_pa_payment` menolak submission dengan baris campuran route gl+advance dari PA
  berbeda.
- Baru: `save_pa_payment` derive route dari PA (bukan dari request body) — kirim
  `data.get("route")` yang salah/kosong, hasil tetap ikut PA asli.
- Baru: `set_pam_complete_cascade` untuk PAM pillar `ADVANCE` juga men-set PA header terkait
  jadi `status='paid'`.
- Baru: `realize_advance_payment` meng-update `jumlah_pembayaran` baris PA ke angka realized,
  dan `{pa_tbl}.status` jadi `'complete'` setelah semua baris PAM-nya realized.
- Baru: `get_pa_advance_list` — union lintas 4 pillar, filter status, filter route='advance'.

## Out of Scope (tetap sama seperti v1)

- Tidak ada follow-up PAM otomatis untuk selisih (piutang/kekurangan bayar).
- Tidak ada tabel PA baru khusus Advance — reuse skema PA yang sudah ada.
