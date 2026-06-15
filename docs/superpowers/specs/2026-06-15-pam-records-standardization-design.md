# PAM Records Standardization — Design Spec
**Date:** 2026-06-15
**Status:** Approved

## Overview

Standarisasi tabel `pam_records` sebagai pusat data Payment Approval Memo (PAM) untuk semua pillar (AGRI, APP, LAND, SETF). Setiap pillar mendapat table lines terpisah yang relational ke `pam_records` untuk tracking workflow kolom U–AC.

Menu SML diganti menjadi LAND.

---

## 1. Schema Changes

### 1a. `pam_records` — Tambah Kolom

Kolom yang sudah ada **tidak diubah**. Tambah via `ALTER TABLE`:

```sql
ALTER TABLE pam_records ADD COLUMN mata_uang TEXT DEFAULT 'IDR';
ALTER TABLE pam_records ADD COLUMN dpp       INTEGER DEFAULT 0;
ALTER TABLE pam_records ADD COLUMN ppn       INTEGER DEFAULT 0;
ALTER TABLE pam_records ADD COLUMN pillar    TEXT;
-- pillar values: 'AGRI' | 'APP' | 'LAND' | 'SETF'
```

**Full column list `pam_records` (post-migration):**

| Col | Name | Type | Notes |
|-----|------|------|-------|
| A | id | INTEGER PK | |
| B | company_id | INTEGER FK | |
| C | pam_no | TEXT UNIQUE | |
| D | pam_date | TEXT | |
| E | gl_account | TEXT | default '70110230' |
| F | cost_center | TEXT | |
| G | pt | TEXT | nama PT/vendor |
| H | requestors_name | TEXT | default 'Jany Turkanda' |
| I | keterangan | TEXT | |
| J | mata_uang | TEXT | default 'IDR' — **NEW** |
| K | dpp | INTEGER | default 0 — **NEW** |
| L | ppn | INTEGER | default 0 — **NEW** |
| M | total_amount | REAL | |
| N | due_date | TEXT | |
| O | status | TEXT | 'open' / 'on_process' / 'complete' |
| P | created_at | TEXT | |
| Q | updated_at | TEXT | |
| R | tanggal_bayar | TEXT | |
| S | source | TEXT | default 'beasiswa' |
| T | pillar | TEXT | 'AGRI'/'APP'/'LAND'/'SETF' — **NEW** |

---

### 1b. 4 Table Lines Baru (satu per pillar)

Semua mulai dengan schema identik (APP format dari Excel). Tiap pillar dapat di-ALTER secara independen nanti.

```sql
CREATE TABLE agri_pam_lines (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    pam_id             INTEGER NOT NULL REFERENCES pam_records(id) ON DELETE CASCADE,
    no_vendor          TEXT,
    nama_vendor        TEXT,
    tgl_terima_doc     TEXT,
    tgl_proses         TEXT,
    tgl_verifikasi_tax TEXT,
    tgl_approval_1     TEXT,
    tgl_approval_2     TEXT,
    tgl_approval_3     TEXT,
    tgl_kirim          TEXT,
    created_at         TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at         TEXT
);

-- identik untuk:
CREATE TABLE app_pam_lines  (...);
CREATE TABLE land_pam_lines (...);
CREATE TABLE setf_pam_lines (...);
```

**Constraint:** 1 PAM = 1 baris di lines table (karena 1 PAM = 1 vendor).

---

## 2. Menu Mapping

| Menu Tab | pillar filter | Lines Table | Query JOIN |
|----------|--------------|-------------|-----------|
| AGRI | `pillar = 'AGRI'` | `agri_pam_lines` | LEFT JOIN agri_pam_lines |
| APP | `pillar = 'APP'` | `app_pam_lines` | LEFT JOIN app_pam_lines |
| LAND *(ganti SML)* | `pillar = 'LAND'` | `land_pam_lines` | LEFT JOIN land_pam_lines |
| SETF | `pillar = 'SETF'` | `setf_pam_lines` | LEFT JOIN setf_pam_lines |

---

## 3. Display Columns per Tab

### Header (dari `pam_records`)

| # | DB Column | UI Label |
|---|-----------|----------|
| 1 | pam_no | No. PAM |
| 2 | pam_date | Tanggal PAM |
| 3 | gl_account | GL Account |
| 4 | cost_center | Cost Center |
| 5 | pt | PT |
| 6 | requestors_name | Requestor |
| 7 | keterangan | Keterangan |
| 8 | mata_uang | Mata Uang |
| 9 | dpp | DPP |
| 10 | ppn | PPN |
| 11 | total_amount | Total |
| 12 | due_date | Due Date |
| 13 | status | Status |
| 14 | tanggal_bayar | Tgl Bayar |
| 15 | source | Source |

### Lines (dari `{pillar}_pam_lines`) — label awal semua pillar sama

| # | DB Column | UI Label |
|---|-----------|----------|
| 16 | no_vendor | No. Vendor |
| 17 | nama_vendor | Nama Vendor |
| 18 | tgl_terima_doc | Terima Dok |
| 19 | tgl_proses | Proses |
| 20 | tgl_verifikasi_tax | Verifikasi Tax |
| 21 | tgl_approval_1 | Approval 1 |
| 22 | tgl_approval_2 | Approval 2 |
| 23 | tgl_approval_3 | Approval 3 |
| 24 | tgl_kirim | Kirim |

---

## 4. Query Pattern (per tab)

```sql
-- Contoh: AGRI tab
SELECT pr.*,
       al.no_vendor, al.nama_vendor,
       al.tgl_terima_doc, al.tgl_proses, al.tgl_verifikasi_tax,
       al.tgl_approval_1, al.tgl_approval_2, al.tgl_approval_3, al.tgl_kirim
FROM pam_records pr
LEFT JOIN agri_pam_lines al ON al.pam_id = pr.id
WHERE pr.company_id = ? AND pr.pillar = 'AGRI'
ORDER BY pr.pam_date DESC
```

`LEFT JOIN` digunakan agar PAM yang belum punya lines record tetap tampil dan bisa di-edit.

---

## 5. Data Migration Plan

### Step 1 — Schema migration (safe, via migrate_db in database.py)
- ALTER TABLE pam_records: tambah mata_uang, dpp, ppn, pillar
- CREATE TABLE IF NOT EXISTS: agri_pam_lines, app_pam_lines, land_pam_lines, setf_pam_lines

### Step 2 — Import Excel → pam_records
- Source: `query_1-2026-06-15_85459.xlsx` (277 rows)
- Kolom A–T → INSERT OR REPLACE INTO pam_records
- pam_records data lama yang belum punya pillar: inferensi dari cost_center (AGRI vendors sudah diketahui dari VENDOR_SEED)

### Step 3 — Import kolom U–AC → lines tables
- Per baris Excel: buat 1 baris di `{pillar}_pam_lines` dengan pam_id hasil Step 2
- Baris dengan U–AC semua NULL tetap dibuat (agar record lines ada untuk di-edit via UI)
- Logic: `INSERT OR IGNORE` (jika pam_id sudah punya lines, skip)

### Step 4 — Update label SML → LAND di UI
- Tab label: "SML" → "LAND"
- Filter: `pillar = 'LAND'` (bukan 'SML')

### Data yang tidak terpengaruh
- `fiori_pa`, `app_pa`, `sml_pa`, `etf_pa`, `setf_pa` — PA tables, tetap ada
- `payment_beasiswa`, `payment_memo` — tidak diubah
- Semua kolom existing di `pam_records` — tidak dihapus

---

## 6. Future Customization

Tiap pillar dapat di-customize kolom lines-nya secara independen:
```sql
-- Contoh: nanti AGRI perlu kolom tambahan
ALTER TABLE agri_pam_lines ADD COLUMN tgl_khusus_agri TEXT;
-- Tidak mempengaruhi app_pam_lines, land_pam_lines, setf_pam_lines
```

---

## Out of Scope (not in this spec)

- Customisasi label/kolom AGRI, LAND, SETF (dilakukan terpisah nanti per request)
- Input form / edit modal per tab (UI detail dikerjakan di implementation phase)
- Export Excel per tab dengan kolom lines baru
