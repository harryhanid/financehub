# ETF PA Summary View — Design Spec
**Date:** 2026-06-18
**Status:** Approved

## Overview

Tambah tabel `pa_summary` sebagai SQL VIEW yang mengagregasi data dari `etf_pa`, `etf_pa_lines`, dan `siswa` per `pa_number`. Ditampilkan sebagai tab baru di halaman ETF PA.

## Background

Data `etf_pa` saat ini memiliki UNIQUE constraint pada `pa_number`, padahal satu `pa_number` bisa memiliki banyak baris (beda `nomor_pam` / beda siswa / beda pembayaran). Arsitektur data yang benar adalah:

```
pa_summary  (1 row per pa_number)
    └── etf_pa  (many rows per pa_number)
            └── etf_pa_lines  (1 row per siswa per etf_pa)
```

## Schema Changes

### 1. Drop UNIQUE constraint pada `etf_pa.pa_number`

SQLite tidak support `ALTER TABLE DROP CONSTRAINT`. Solusi: recreate tabel tanpa constraint.

```sql
-- Step 1: rename existing table
ALTER TABLE etf_pa RENAME TO etf_pa_old;

-- Step 2: create new without UNIQUE on pa_number
CREATE TABLE etf_pa (
    id                       INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id               INTEGER NOT NULL REFERENCES companies(id),
    pa_number                TEXT NOT NULL,            -- no UNIQUE
    tgl_payment_application  TEXT,
    tgl_surat_pengajuan      TEXT,
    doc_received_by_educ     TEXT,
    received_pa_from_educ    TEXT,
    checked_by_fincon        TEXT,
    approved_by_htj_1        TEXT,
    send_pa_back_to_educ     TEXT,
    pa_received_by_po_fin    TEXT,
    approval_by_htj_2        TEXT,
    nomor_pam                TEXT,
    tanggal_bayar            TEXT,
    keterangan               TEXT,
    status                   TEXT NOT NULL DEFAULT 'draft',
    created_at               TEXT NOT NULL,
    updated_at               TEXT
);

-- Step 3: copy data
INSERT INTO etf_pa SELECT * FROM etf_pa_old;

-- Step 4: drop old
DROP TABLE etf_pa_old;
```

### 2. CREATE VIEW pa_summary

```sql
CREATE VIEW pa_summary AS
SELECT
    e.pa_number,
    GROUP_CONCAT(DISTINCT e.tgl_payment_application)  AS tgl_payment_application,
    GROUP_CONCAT(DISTINCT e.nomor_pam)                AS nomor_pam,
    GROUP_CONCAT(DISTINCT s.nama)                     AS nama_student,
    GROUP_CONCAT(DISTINCT l.jenis_pembayaran)         AS jenis_pembayaran,
    GROUP_CONCAT(DISTINCT l.semester)                 AS semester,
    SUM(l.jumlah_pembayaran)                          AS jumlah_pembayaran,
    GROUP_CONCAT(DISTINCT e.status)                   AS status,
    GROUP_CONCAT(DISTINCT e.tanggal_bayar)            AS tanggal_bayar,
    GROUP_CONCAT(DISTINCT e.keterangan)               AS keterangan
FROM etf_pa e
LEFT JOIN etf_pa_lines l ON l.pa_id = e.id
LEFT JOIN siswa s ON s.id = l.student_id
GROUP BY e.pa_number;
```

## Backend

### Route

`GET /etf-pa/summary` — query view `pa_summary`, return JSON list.

```python
@bp.route('/summary')
def etf_pa_summary():
    rows = db.execute('SELECT * FROM pa_summary ORDER BY pa_number').fetchall()
    return jsonify([dict(r) for r in rows])
```

### database.py DDL sync

Tambah DDL `pa_summary` VIEW ke fungsi `init_db()` / `sync_schema()` agar view otomatis terbuat di environment baru.

## Frontend

### Tab baru "PA Summary" di halaman ETF PA

Tab ditambahkan setelah tab existing (PA List / PA Input). Tampilan: tabel dengan kolom:

| # | PA Number | Tgl PA | Nomor PAM | Nama Student | Jenis Pembayaran | Semester | Total (IDR) | Status | Tgl Bayar | Keterangan |
|---|---|---|---|---|---|---|---|---|---|---|

- Field multi-value (nama_student, nomor_pam, dll.) ditampilkan sebagai comma-separated text di cell.
- Kolom `jumlah_pembayaran` diformat sebagai angka ribuan (IDR).
- Default sort: `pa_number` ascending.
- Search/filter: minimal filter by `pa_number`.

## Import Flow (prerequisite)

Sebelum membuat VIEW, lakukan:
1. Drop UNIQUE constraint (`etf_pa` recreate)
2. Import 2161 baris `etf_pa` dari Excel
3. Import 2228 baris `etf_pa_lines` dari Excel
4. Baru buat VIEW `pa_summary`

## Implementation Order

1. Migrate `etf_pa` schema (drop UNIQUE, recreate table)
2. Import `etf_pa` + `etf_pa_lines` dari Excel
3. `CREATE VIEW pa_summary`
4. Update `database.py`
5. Add route `GET /etf-pa/summary`
6. Add tab + table UI di ETF PA page
