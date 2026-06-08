# Input Tab Redesign — AGRI/APP/SML/SETF Multi-Type
## Design Spec

**Date:** 2026-06-08  
**Status:** Approved

---

## Goal
Redesign tab Input di ETF/Payment Approval Memo agar mendukung 4 tipe PAM (AGRI/APP/SML/SETF) via dropdown selector, dengan siswa hanya dari open PA tipe terpilih, PAM number auto-generate per tipe, field "Catatan Payment" tersimpan di `pam_records.keterangan`, dan tampil di tab PAM yang sesuai.

---

## Architecture
- **Single Input panel** — sub-tab `[Beasiswa][AGRI]` dihapus, panel langsung visible. Dropdown Tipe PAM di header row.
- **Type-aware data fetch** — semua endpoint siswa/lines dapat `?tab={type}` untuk routing ke tabel PA yang benar.
- **Unified save endpoint** — `POST /payment-memo/ipay/save-pa` membuat pam_records + payment_beasiswa + update PA status.
- **PAM tab filter** — tab-pam (AGRI) mendapat source filter dropdown sehingga menampilkan PAM per tipe.

---

## Database

### Tabel Baru: `setf_pa`
Identik dengan `etf_pa`:
```sql
CREATE TABLE IF NOT EXISTS setf_pa (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    pa_number TEXT NOT NULL,
    tgl_payment_application TEXT,
    tgl_surat_pengajuan TEXT,
    doc_received_by_educ TEXT,
    received_pa_from_educ TEXT,
    checked_by_fincon TEXT,
    approved_by_htj_1 TEXT,
    send_pa_back_to_educ TEXT,
    pa_received_by_po_fin TEXT,
    approval_by_htj_2 TEXT,
    nomor_pam TEXT,
    tanggal_bayar TEXT,
    keterangan TEXT,
    status TEXT DEFAULT 'open',
    created_at TEXT,
    updated_at TEXT
);
```

### Tabel Baru: `setf_pa_lines`
Identik dengan `etf_pa_lines`:
```sql
CREATE TABLE IF NOT EXISTS setf_pa_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pa_id INTEGER NOT NULL REFERENCES setf_pa(id),
    student_id INTEGER NOT NULL REFERENCES siswa(id),
    jenis_pembayaran TEXT,
    semester TEXT,
    tahun_ajaran TEXT,
    ipk_sem_sebelumnya REAL DEFAULT 0,
    jumlah_pembayaran REAL DEFAULT 0
);
```

### Verifikasi Alignment
`app_pa`, `sml_pa`, `app_pa_lines`, `sml_pa_lines` sudah identik dengan etf_pa/etf_pa_lines — tidak ada perubahan schema.

---

## Backend

### 1. `app/modules/etf_payment_application/service.py`
**Extend `_TAB_CFG`:**
```python
VALID_TABS = {"agri", "app", "sml", "setf"}

_TAB_CFG = {
    "agri":  ("etf_pa",  "etf_pa_lines",  "ETF",  "ETF"),
    "app":   ("app_pa",  "app_pa_lines",  "APP",  "APP"),
    "sml":   ("sml_pa",  "sml_pa_lines",  "SML",  "SML"),
    "setf":  ("setf_pa", "setf_pa_lines", "SETF", "SETF"),
}
```
Semua endpoint yang sudah ada (`draft-siswa`, `draft-lines`, `get-pa-flat`, dll) otomatis support SETF tanpa kode tambahan.

### 2. `app/modules/payment_memo/service.py` — Fungsi Baru

#### `get_next_pam_no(company_id, company_code, tab, date_str)`
- Resolve pam_prefix dari `_TAB_CFG` (atau mapping lokal)
- Panggil `generate_pam_number(company_id, pam_prefix, year, month)`
- Return string pam_no

#### `save_pa_payment(company_id, company_code, data)`
Input `data`:
```json
{
  "tab": "agri",
  "tanggal": "2026-06-08",
  "pam_no": "PAM-054-ETF-06-2026",
  "keterangan": "Catatan opsional",
  "perusahaan": "PT XYZ",
  "pillar": "ETF",
  "rows": [
    {
      "siswa_code": "ETF001",
      "etf_pa_line_id": 42,
      "cat1": "Pendidikan",
      "cat2": "Semester 2",
      "amount": 5000000,
      "tgl_pengajuan": "2026-06-01",
      "tgl_receive": "2026-06-03",
      "tgl_pa": "2026-06-05",
      "tgl_final": ""
    }
  ]
}
```

Logika:
1. Buat `pam_records` entry dengan `source = f"etf_{tab}"` (misal `etf_agri`, `etf_app`, dst.)
2. Untuk tiap row: buat `payment_beasiswa` row dengan `memo_id` NULL (pakai `etf_pa_line_id` untuk link)
3. Untuk tiap unique `etf_pa_line_id`: ambil `pa_id` dari lines table → update PA header: `nomor_pam = pam_no`, `status = 'on_process'`
4. PA table ditentukan dari `tab` via `_TAB_CFG`

### 3. `app/modules/payment_memo/routes.py` — Route Baru

```
GET  /payment-memo/ipay/next-pam-no?tab={type}&date={YYYY-MM-DD}
POST /payment-memo/ipay/save-pa
```

### 4. `app/modules/payment_memo/service.py` — `get_pam_list` Extension
Tambah parameter `source` (opsional):
```python
def get_pam_list(company_id, search="", bulan="", tahun="", source=""):
    ...
    if source:
        sql += " AND source LIKE ?"
        params += [f"etf_{source}%"]
```

---

## Frontend

### `app/templates/payment_memo/index.html`

#### A. Hapus sub-tab `[Beasiswa][AGRI]`
- Hapus div wrapper `display:flex` dengan tombol sub-tab
- Hapus `id="ipay-panel-agri"` div (panel AGRI lama) sepenuhnya
- Panel Beasiswa (`id="ipay-panel-beasiswa"`) langsung visible tanpa wrapper sub-tab

#### B. Header Input Panel — Baris 1
```
[Tipe PAM ▾ AGRI]  [Tanggal: 08/06/2026]  [No.PAM: PAM-054-ETF-06-2026 (readonly)]  [Perusahaan: cari...]
```
- Tipe PAM: `<select id="ipay-type">` dengan options AGRI/APP/SML/SETF
- No. PAM: readonly, auto-fetch dari `/ipay/next-pam-no?tab={type}&date={tgl}`
- Fetch dipicu saat type atau tanggal berubah

#### C. Header Input Panel — Baris 2
```
[Pillar: auto readonly]  [Catatan Payment: input teks lebar]
```
- `id="ipay-catatan"` — disimpan ke `pam_records.keterangan`

#### D. Siswa Search
- URL: `/etf-payment-application/draft-siswa?q=...&tab={ipay-type.value}`
- Hint di placeholder: "Cari siswa (PA {TYPE} open)..."

#### E. Draft Lines Fetch
- URL: `/etf-payment-application/draft-lines?siswa_id={id}&tab={ipay-type.value}`

#### F. Tombol Save
- Label: `"💾 Simpan PAM ${type.toUpperCase()}"`  — berubah saat type berubah
- POST ke `/payment-memo/ipay/save-pa`
- Payload: `{ tab, tanggal, pam_no, keterangan, perusahaan, pillar, rows }`

#### G. Tab PAM (tab-pam) — Source Filter
Tambah dropdown filter di filter bar:
```html
<select id="pam-filter-source" onchange="loadPAMDebounced()">
  <option value="">Semua Tipe</option>
  <option value="agri">AGRI</option>
  <option value="app">APP</option>
  <option value="sml">SML</option>
  <option value="setf">SETF</option>
</select>
```
- `loadPAM()` kirim `source` ke `/payment-memo/pam?...&source={val}`
- Rename header kolom "Keterangan" → "Catatan Payment"

---

## Data Flow (End-to-End)

```
User pilih tipe "APP"
→ No.PAM auto: GET /ipay/next-pam-no?tab=app&date=2026-06-08
← "PAM-012-APP-06-2026"

User ketik nama siswa
→ GET /etf-payment-application/draft-siswa?q=budi&tab=app
← hanya siswa dengan open app_pa

User pilih siswa → pilih cat1 → pilih cat2
→ GET /etf-payment-application/draft-lines?siswa_id=5&tab=app
← app_pa_lines: amount/dates auto-fill

User isi Catatan: "Batch APP Juni 2026"

User klik "💾 Simpan PAM APP"
→ POST /payment-memo/ipay/save-pa
  {tab:"app", pam_no:"PAM-012-APP-06-2026", keterangan:"Batch APP Juni 2026", rows:[...]}

Backend:
  1. INSERT pam_records (source='etf_app', keterangan='Batch APP Juni 2026')
  2. INSERT payment_beasiswa (per row)
  3. UPDATE app_pa SET nomor_pam='PAM-012-APP-06-2026', status='on_process'

User buka tab AGRI → filter source=APP
← PAM-012-APP-06-2026 muncul dengan Catatan Payment "Batch APP Juni 2026"
```

---

## Out of Scope (→ Spec B)
- SLA tab redesign dengan sub-type AGRI/APP/SML/SETF
- Payment Application halaman SETF (UI untuk input/kelola setf_pa records)
- Cascade paid-date untuk APP/SML/SETF (saat ini hanya AGRI yang punya cascade logic)
