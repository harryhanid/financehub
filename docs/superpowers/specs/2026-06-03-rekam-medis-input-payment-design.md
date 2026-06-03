# Rekam Medis — Input Payment Integration

**Date:** 2026-06-03  
**Scope:** Input Payment tab (Payment Approval Memo) — tambah Data Medis saat cat1=By Medical

---

## Overview

Ketika user menginput row di tab **Input Payment** dengan `cat1 = "By Medical"` dan `cat2 ∈ ["Rawat Jalan", "Rawat Inap"]`, section **Data Medis** wajib diisi sebelum bisa disimpan. Data ini disimpan ke tabel baru `rekam_medis` dengan FK ke `payment_beasiswa.id`.

Input Klaim akan dihapus di task terpisah dan tidak termasuk scope ini.

---

## UI Behavior

### Pola: Expand Chevron (Option C)

- Setiap row di tabel Input Payment yang memiliki `cat1 = "By Medical"` mendapatkan section **Data Medis** yang auto-expand di bawah row-nya.
- Trigger expand: saat user memilih cat1 = "By Medical" **dan** cat2 = "Rawat Jalan" atau "Rawat Inap".
- Trigger collapse: saat cat1 atau cat2 diubah ke nilai lain → section disembunyikan dan data dihapus dari row.
- Tombol ▲/▼ di kolom aksi untuk toggle manual.
- Row non-medical tidak memiliki section ini sama sekali.

### Warning State

Jika row By Medical di-collapse sebelum data diisi, muncul bar merah:
> "⚠️ Data Medis belum diisi — klik ▲ untuk expand dan isi data"

### Validasi saat Simpan

Saat user klik "💾 Simpan Payment":
1. Setiap row dengan `cat1 = "By Medical"` dicek apakah Data Medis sudah terisi.
2. Field wajib: **Kelas, Rumah Sakit, Diagnosa, Spesialisasi**.
3. Field opsional: **Catatan**.
4. Jika ada row yang belum lengkap → simpan ditolak, toast error, row bersangkutan di-highlight merah.

---

## Fields Data Medis

| Field | Tipe | Wajib | Pilihan / Format |
|---|---|---|---|
| Kelas | Dropdown | Ya | Rawat Jalan, Emergency, Basic/Kelas 3, Standard/Kelas 2, Deluxe/Kelas 1, VIP, VVIP, SVIP |
| Rumah Sakit | Text input | Ya | Free text |
| Diagnosa | Text input | Ya | Free text |
| Spesialisasi | Dropdown | Ya | Internal Medicine, Cardiology, Orthopaedy, Obstetric & Gynaecology, Pediatrics, Pulmonology, Neurology, Neurosurgeon, General Surgery, ENT, Dermatovenerology, Psychiatry, Opthalmology, Plastic Surgery, General Practionist, Dentistry |
| Catatan | Text input | Tidak | Free text |

---

## Database

### Tabel Baru: `rekam_medis`

```sql
CREATE TABLE IF NOT EXISTS rekam_medis (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id   INTEGER NOT NULL,
    payment_id   INTEGER NOT NULL REFERENCES payment_beasiswa(id),
    siswa_code   TEXT NOT NULL,
    kelas        TEXT NOT NULL,
    rumah_sakit  TEXT NOT NULL,
    diagnosa     TEXT NOT NULL,
    spesialisasi TEXT NOT NULL,
    catatan      TEXT,
    created_at   TEXT DEFAULT CURRENT_TIMESTAMP
);
```

### Relasi

- `rekam_medis.payment_id → payment_beasiswa.id` (1:1 per row By Medical)
- Disimpan dalam satu transaksi bersamaan dengan `payment_beasiswa`
- Jika `payment_beasiswa` dihapus → `rekam_medis` ikut dihapus (cascade atau manual delete)

---

## Backend

### Modifikasi: `/beasiswa/payment/tambah-multi` (POST)

Payload per row diperluas dengan field `rekam_medis` opsional:

```json
{
  "tanggal": "2026-06-03",
  "pillar": "AGRI",
  "perusahaan": "PT ABC",
  "pam": "PAM-001-ETF-06-2026",
  "rows": [
    {
      "siswa_code": "ETF-002",
      "cat1": "By Medical",
      "cat2": "Rawat Inap",
      "amount": 3200000,
      "rekam_medis": {
        "kelas": "Standard/Kelas 2",
        "rumah_sakit": "RS Siloam Jakarta",
        "diagnosa": "Demam Berdarah",
        "spesialisasi": "Internal Medicine",
        "catatan": ""
      }
    }
  ]
}
```

Service `tambah_payment_multi()`:
- Jika row `cat1 = "By Medical"` dan `rekam_medis` tidak ada atau field wajib kosong → return error (backend validation sebagai safeguard).
- Setelah insert `payment_beasiswa` → insert `rekam_medis` dengan `payment_id = last_insert_rowid()`.
- Semua dalam satu transaksi (`BEGIN / COMMIT`).

### Tidak ada endpoint baru

Data Medis dikirim embedded dalam payload `tambah-multi` yang sudah ada — tidak perlu endpoint terpisah.

---

## Frontend (payment_memo/index.html)

### Perubahan di `ipayAddRow()`

1. Tambah property `tr._rekamMedis = { kelas:'', rumah_sakit:'', diagnosa:'', spesialisasi:'', catatan:'' }` per row.
2. Tambah DOM section Data Medis (hidden by default) di bawah row — sebagai `<tr class="ipay-medis-row">` dengan `colspan` penuh.
3. Section berisi form 4+1 field sesuai spec di atas.
4. Event listener di cat1 select dan cat2 drop:
   - Jika `cat1 = "By Medical"` AND `cat2 ∈ ["Rawat Jalan", "Rawat Inap"]` → show & expand section.
   - Selain itu → hide section, clear values.

### Perubahan di `ipaySave()`

Sebelum POST, validasi tiap row:
```js
if (row.cat1 === "By Medical") {
  const m = tr._getMedisData(); // baca dari DOM
  if (!m.kelas || !m.rumah_sakit || !m.diagnosa || !m.spesialisasi) {
    // highlight row, tampilkan toast, abort
  }
  row.rekam_medis = m;
}
```

---

## Tidak Berubah

- Tab Input Klaim — akan dihapus di task terpisah.
- Tabel `klaim_medical` — tidak disentuh.
- Semua tab lain di Payment Approval Memo.
- Service beasiswa lainnya.
