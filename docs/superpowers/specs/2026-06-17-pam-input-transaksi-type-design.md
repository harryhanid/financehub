# PAM Input — Transaksi Type Redesign

**Date:** 2026-06-17
**Module:** Payment Approval Memo → Tab Input
**Status:** Approved for implementation

---

## Overview

Redesign tab Input PAM untuk mendukung tiga tipe transaksi berbeda: **Beasiswa** (existing, unchanged), **Klaim Medis** (new — with medical data and cat3 breakdown), dan **Others** (Tagihan/ETF/Sponsor/Others — simple single-entry).

Perubahan utama: tambah dropdown `Transaksi` di header Input tab, dan tiga panel HTML yang di-show/hide sesuai pilihan.

---

## Architecture

### Header Input Tab

Header row ditambah satu field `Transaksi` setelah `Tipe PAM`:

```
[Tipe PAM: AGRI▼]  [Transaksi: Beasiswa▼]  [Tanggal]  [No. PAM (auto)]  [Perusahaan]
[Pillar (auto)]    [Catatan]
```

Dropdown `Transaksi` options:
- Beasiswa
- Klaim Medis
- Tagihan
- ETF
- Sponsor
- Others

### Panel Switching

Handler `ipayOnTxChange()` show/hide tiga panel:

| Transaksi | Panel ID | Save function |
|---|---|---|
| Beasiswa | `#ipay-panel-beasiswa` | `ipaySavePa()` (unchanged) |
| Klaim Medis | `#ipay-panel-klaim` | `ipaySaveKlaim()` (new) |
| Tagihan / ETF / Sponsor / Others | `#ipay-panel-others` | `ipaySaveOthers()` (new) |

`ipayReset()` direset juga saat Transaksi berubah — clear rows, reset total.

---

## Database Changes

### Tabel Baru: `rekam_medis`

```sql
CREATE TABLE rekam_medis (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id          INTEGER NOT NULL,
    payment_beasiswa_id INTEGER NOT NULL,   -- FK → payment_beasiswa.id
    pam_no              TEXT NOT NULL,
    siswa_code          TEXT NOT NULL,
    cat3                TEXT NOT NULL,      -- Alkes/Kamar/Obat/dst
    kelas               TEXT,               -- Basic/VIP/VVIP/dst
    rumah_sakit         TEXT,
    diagnosa            TEXT,
    spesialisasi        TEXT,
    tanggal             TEXT,
    amount              REAL NOT NULL DEFAULT 0,
    created_at          TEXT NOT NULL
);
```

### Tidak ada perubahan schema existing

`payment_beasiswa` dan `pam_records` tidak berubah strukturnya. `pam_records.source` menerima nilai baru `"klaim_medis"` selain nilai existing.

---

## Panel Beasiswa

**Tidak berubah sama sekali.** Existing code (`#ipay-panel-beasiswa`, `ipaySavePa()`, `/ipay/save-pa`) tetap dipakai apa adanya.

---

## Panel Klaim Medis

### Struktur Tabel (flat rows, grouped by siswa)

Kolom tabel:

| Kolom | Input type | Keterangan |
|---|---|---|
| Siswa | Search autocomplete | Filter hanya siswa dengan `budget_beasiswa.cat1 = 'By Medical'` |
| Cat2 | Select | Rawat Inap / Rawat Jalan |
| Kelas | Select | Basic / Deluxe / Emergency / Rawat Jalan / Standard / VIP / VVIP / SVIP |
| Rumah Sakit | Text input | Free text |
| Diagnosa | Text input | Free text |
| Spesialisasi | Select | 15 spesialisasi (lihat list di bawah) |
| Cat3 | Select | 8 item (lihat list di bawah) |
| Amount | Number input | Amount per cat3 item |
| Sisa Budget | Read-only | Auto-calc dari budget_beasiswa − payment_beasiswa (cat1=By Medical) |
| Tanggal | Date input | Per cat3 item |
| Aksi | Button | Delete baris |

**Row structure:**
- **Siswa row** (baris pertama per siswa): semua kolom terisi, termasuk data medis (Kelas, RS, Diagnosa, Spesialisasi) dan cat3 item pertama.
- **Cat3 continuation rows**: kolom Siswa s/d Spesialisasi di-span/kosong dengan label "↳ [nama siswa] — cat3 tambahan". Hanya Cat3, Amount, Tanggal yang editable.
- **Add row**: tombol `+ cat3 untuk [Nama Siswa]` muncul setelah tiap grup siswa.

### Cat3 Options

```
Alkes | Kamar | Konsultasi dan Visit | Laboratorium | Obat |
Radiologi | Sewa Alat Rumah Sakit | Tindakan Dokter
```

### Spesialisasi Options

```
Internal Medicine | Cardiology | Orthopaedy | Obstetric & Gynaecology |
Pediatrics | Pulmonology | Neurology | Neurosurgeon | General Surgery |
ENT | Dermatovenerology | Psychiatry | Opthalmology | Plastic Surgery |
General Practitioner | Dentistry
```

### Siswa Search Filter

Endpoint GET `/payment-memo/ipay/siswa-medical` mengembalikan siswa yang memiliki minimal satu baris di `budget_beasiswa` dengan `cat1 = 'By Medical'` dan `company_id` yang sesuai. Autocomplete search by nama / code.

### Save Flow — Klaim Medis

Payload `POST /payment-memo/ipay/save-klaim`:

```json
{
  "tab": "agri",
  "tanggal": "2026-06-17",
  "pam_no": "PAM-054-MED-06-2026",
  "perusahaan": "RS Siloam",
  "keterangan": "...",
  "pillar": "AGRI",
  "rows": [
    {
      "siswa_code": "A001",
      "cat2": "Rawat Inap",
      "kelas": "VIP",
      "rumah_sakit": "RS Siloam",
      "diagnosa": "Demam Typoid",
      "spesialisasi": "General Practitioner",
      "cat3_items": [
        { "cat3": "Kamar", "amount": 3000000, "tanggal": "2026-06-10" },
        { "cat3": "Obat", "amount": 500000, "tanggal": "2026-06-10" }
      ]
    }
  ]
}
```

Service `save_klaim_payment(company_id, company_code, data)` di `payment_memo/service.py`:

1. Validasi: rows tidak kosong, tiap row ada siswa_code dan minimal 1 cat3_item dengan amount > 0.
2. Untuk setiap row:
   - INSERT `payment_beasiswa`: `cat1="By Medical"`, `cat2=row.cat2`, `amount=SUM(cat3_items.amount)`, `pillar`, `pam=pam_no`, `perusahaan`, `siswa_code`, `tanggal`, `status="open"`
   - Untuk setiap cat3_item: INSERT `rekam_medis` dengan `payment_beasiswa_id`, `pam_no`, `siswa_code`, `cat3`, `kelas`, `rumah_sakit`, `diagnosa`, `spesialisasi`, `tanggal`, `amount`
3. INSERT satu `pam_records`: `total_amount=SUM(semua row amounts)`, `source="klaim_medis"`, `pam_no`, `pam_date=tanggal`, `requestors_name=company_code`, `keterangan`, `pillar`, `status="open"`
4. Commit semua dalam satu transaksi DB.

---

## Panel Others (Tagihan / ETF / Sponsor / Others)

### Form Fields

Form satu entri, tidak ada tabel multi-baris:

| Field | Input type | Keterangan |
|---|---|---|
| Keterangan | Text input | Free text, wajib diisi |
| Mata Uang | Select | IDR / USD |
| DPP | Number input | Free input |
| PPN | Number input | Free input |
| Total | Read-only display | Auto = DPP + PPN, update on input |

Header (Tipe PAM, Transaksi, Tanggal, No. PAM, Perusahaan, Pillar, Catatan) sama seperti panel lain.

### Save Flow — Others

Payload `POST /payment-memo/ipay/save-others`:

```json
{
  "tab": "agri",
  "transaksi": "tagihan",
  "tanggal": "2026-06-17",
  "pam_no": "PAM-055-ETF-06-2026",
  "perusahaan": "PT. Telkom Indonesia",
  "keterangan": "Tagihan internet kantor...",
  "pillar": "AGRI",
  "mata_uang": "IDR",
  "dpp": 5000000,
  "ppn": 550000
}
```

Service `save_others_payment(company_id, company_code, data)` di `payment_memo/service.py`:

1. Validasi: keterangan tidak kosong, dpp > 0.
2. `total = dpp + ppn`
3. INSERT satu `pam_records`: `pam_no`, `pam_date=tanggal`, `requestors_name=company_code`, `keterangan`, `total_amount=total`, `mata_uang`, `dpp`, `ppn`, `pillar`, `source=transaksi` (nilai: tagihan/etf/sponsor/others), `status="open"`, `pt=perusahaan` (kolom `pt` di pam_records dipakai untuk menyimpan nama vendor/perusahaan).
4. Tidak ada insert ke `payment_beasiswa`.

---

## PAM Records Tab — Filter Source

Tambah option `klaim_medis` ke semua dropdown filter source di tab AGRI, APP, LAND, SETF:

```html
<option value="klaim_medis">Klaim Medis</option>
```

---

## Backend Summary

### File yang Dimodifikasi

| File | Perubahan |
|---|---|
| `app/templates/payment_memo/index.html` | Tambah dropdown Transaksi di header; tambah `#ipay-panel-klaim` dan `#ipay-panel-others`; handler `ipayOnTxChange()`; fungsi `ipaySaveKlaim()` dan `ipaySaveOthers()`; filter source option klaim_medis |
| `app/modules/payment_memo/service.py` | Tambah `save_klaim_payment()`, `save_others_payment()`, `get_siswa_medical()` |
| `app/modules/payment_memo/routes.py` | Tambah route `POST /ipay/save-klaim`, `POST /ipay/save-others`, `GET /ipay/siswa-medical` |

### File Baru

| File | Keterangan |
|---|---|
| DB migration script | CREATE TABLE rekam_medis |

---

## Out of Scope (fase ini)

- Edit/delete rekam_medis dari UI
- Report / export Klaim Medis breakdown
- Integrasi rekam_medis ke Print Memo
- Multi-baris untuk tipe Others
- Pengembangan ETF Transaksi (bedakan dari ETF PA yang sudah ada)
