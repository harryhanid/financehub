# ETF Payment Application — Design Spec

**Date:** 2026-06-02
**Status:** Approved
**Author:** Brainstorming session

---

## 1. Overview

Modul baru **ETF Payment Application** untuk mencatat, melacak, dan memonitor pengajuan pembayaran beasiswa Eka Tjipta Foundation (ETF). Berbeda dari modul `payment_application` yang sudah ada (berbasis per-memo), modul ini:

- Satu PA bisa mencakup **beberapa siswa** sekaligus (header + lines)
- Alur: **PA dibuat dulu → PAM auto-generate** saat status berubah ke On Process
- 7 SLA tracking dates per PA (bukan per siswa)
- Status manual, semua role bisa update (untuk sementara, tanpa role restriction)

---

## 2. Data Model

### Tabel `etf_pa` (header)

| Kolom | Tipe | Keterangan |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `company_id` | INTEGER | FK → company (ETF) |
| `pa_number` | TEXT UNIQUE | Auto-generate: `PA/ETF/001/2025` |
| `tgl_payment_application` | TEXT | Input date (YYYY-MM-DD) |
| `tgl_surat_pengajuan` | TEXT | Input date |
| `doc_received_by_educ` | TEXT | SLA date 1 |
| `received_pa_from_educ` | TEXT | SLA date 2 |
| `checked_by_fincon` | TEXT | SLA date 3 |
| `approved_by_htj_1` | TEXT | SLA date 4 — APPROVED PAK HTj (pertama) |
| `send_pa_back_to_educ` | TEXT | SLA date 5 |
| `pa_received_by_po_fin` | TEXT | SLA date 6 |
| `approval_by_htj_2` | TEXT | SLA date 7 — APPROVAL BY PAK HTj (final) |
| `nomor_pam` | TEXT | Auto-generate saat status → `on_process`; format `SEQ-ETF-MM-YYYY` |
| `tanggal_bayar` | TEXT | Input date |
| `keterangan` | TEXT | Free-text notes |
| `status` | TEXT | `draft` / `on_process` / `complete` |
| `created_at` | TEXT | ISO timestamp |
| `updated_at` | TEXT | ISO timestamp |

**PA number format:** `PA/ETF/{SEQ:03d}/{YEAR}` — sequence di-reset per tahun per company.

**PAM number format:** `{SEQ:03d}-ETF-{MM}-{YYYY}` — sequence global per company, diambil dari counter `pam_records` yang sudah ada atau counter tersendiri.

### Tabel `etf_pa_lines` (per siswa)

| Kolom | Tipe | Keterangan |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `pa_id` | INTEGER | FK → `etf_pa.id` ON DELETE CASCADE |
| `student_id` | INTEGER | FK → tabel beasiswa students |
| `jenis_pembayaran` | TEXT | Dropdown Kategori 1 (By Pendidikan, By Tunjangan, dll) |
| `semester` | TEXT | Dropdown Kategori 2 |
| `tahun_ajaran` | TEXT | Input: format `YYYY/YYYY` |
| `ipk_sem_sebelumnya` | REAL | Auto-fill dari data siswa saat input, disimpan snapshot |
| `jumlah_pembayaran` | INTEGER | Jumlah dalam Rupiah |

**Kolom relational (tidak disimpan, di-JOIN via student table saat query):**
`nama`, `status_pb`, `instansi_pendidikan`, `angkatan_etf`, `angkatan_kuliah`, `jenjang_pendidikan`, `program_beasiswa`, `fakultas`, `program_studi`

---

## 3. File Structure

```
app/modules/etf_payment_application/
    __init__.py
    routes.py       — Blueprint, URL prefix: /etf-payment-application
    service.py      — DB logic: get_list, create_pa, update_pa, update_status
    api.py          — JSON API endpoints (opsional, untuk integrasi)

app/templates/etf_payment_application/
    index.html      — Daftar PA + tombol buat baru

app/static/js/
    etf_pa.js       — Form logic: autocomplete siswa, dynamic rows, submit
```

---

## 4. UI Design

### 4.1 Halaman Index — Daftar PA

- Header: judul + tombol **"+ Buat PA Baru"** (semua role)
- Tabel: **satu PA = satu baris** (collapsed). Kolom lines di-aggregate:
  - PA Number | Jml Siswa | Total Bayar | Tgl PA | Tgl Surat Pengajuan | Doc Recv Educ | Recv PA from Educ | Checked Fincon | Approved HTj | Send Back Educ | PA Recv PO Fin | Approval HTj | Nomor PAM | Tgl Bayar | Keterangan | **Status**
- "Jml Siswa" = COUNT lines, "Total Bayar" = SUM jumlah_pembayaran semua lines
- Kolom PA Number di-sticky (freeze kiri)
- Badge status: Draft (gray) / On Process (yellow) / Complete (green)
- Klik baris → expand inline atau modal detail untuk lihat daftar siswa dalam PA tersebut
- Tombol **Edit** per baris → buka modal edit SLA dates + status

### 4.2 Modal Buat PA Baru

**Header section:**
- Tgl Payment Application (date, required)
- Tgl Surat Pengajuan (date)
- Keterangan (textarea)

**Lines section:**
- Dynamic rows dengan "+ Tambah Baris"
- Per baris: autocomplete nama siswa → auto-fill (Status PB, Instansi, Angkatan, Jenjang, Program, Fakultas, Jurusan, IPK terakhir)
- Input per baris: Jenis Pembayaran (dropdown cat1), Semester (dropdown cat2), Tahun Ajaran, Jumlah
- Tombol hapus baris (❌)
- Minimal 1 baris wajib

**Simpan** → status default `draft`

### 4.3 Modal Edit PA

- Update semua 7 SLA dates (date inputs)
- Update Nomor PAM, Tanggal Bayar, Keterangan
- Update Status (dropdown: Draft / On Process / Complete)
  - Saat status diubah ke `on_process` dan `nomor_pam` belum ada → sistem auto-generate
- Tidak bisa edit siswa/lines setelah PA dibuat (untuk integritas data)

---

## 5. Service Logic

### `get_pa_list(company_id)` → list
Query `etf_pa` + aggregate dari `etf_pa_lines` (COUNT siswa, SUM jumlah). Return satu dict per PA header.

### `get_pa_lines(pa_id, company_id)` → list
Query `etf_pa_lines` JOIN students untuk satu PA. Return flat rows per siswa (untuk modal detail).

### `create_pa(company_id, header, lines)` → dict
1. Validate minimal 1 line
2. Generate `pa_number`
3. Insert `etf_pa`
4. Insert semua `etf_pa_lines` (snapshot `ipk_sem_sebelumnya` dari student)
5. Return `{ok, pa_id, pa_number}`

### `update_pa(pa_id, company_id, data)` → dict
1. Update semua fields yang dikirim (SLA dates, keterangan, tanggal bayar, status, nomor_pam)
2. Jika `status == 'on_process'` dan `nomor_pam` belum ada → auto-generate
3. Set `updated_at`

### PAM number generation
```python
count = SELECT COUNT(*) FROM etf_pa WHERE nomor_pam IS NOT NULL AND company_id=? AND strftime('%Y-%m', ...) = current month
nomor_pam = f"{count+1:03d}-ETF-{MM}-{YYYY}"
```

---

## 6. Navigation

Tambahkan link **"ETF Payment Application"** di sidebar `base.html`, di bawah "Payment Application" yang sudah ada. Active page: `etf_payment_app`.

Register Blueprint di `app/__init__.py`:
```python
from modules.etf_payment_application.routes import bp as etf_pa_bp
app.register_blueprint(etf_pa_bp)
```

---

## 7. Database Migration

Tambahkan di `database.py` fungsi `create_tables()`:

```sql
CREATE TABLE IF NOT EXISTS etf_pa (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    pa_number TEXT UNIQUE NOT NULL,
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
    status TEXT NOT NULL DEFAULT 'draft',
    created_at TEXT NOT NULL,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS etf_pa_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pa_id INTEGER NOT NULL REFERENCES etf_pa(id) ON DELETE CASCADE,
    student_id INTEGER NOT NULL,
    jenis_pembayaran TEXT,
    semester TEXT,
    tahun_ajaran TEXT,
    ipk_sem_sebelumnya REAL,
    jumlah_pembayaran INTEGER
);
```

---

## 8. Out of Scope (v1)

- Role restriction untuk status update (buka semua untuk sementara)
- Export PDF/Excel untuk ETF PA (bisa ditambah di fase berikutnya)
- Edit lines setelah PA dibuat
- Filter/search di halaman daftar PA (bisa ditambah nanti)
