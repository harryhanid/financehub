# Finance Hub — Product Requirements Document (PRD)

**Date / Tanggal:** 2026-05-30
**Version / Versi:** 1.1
**Status:** Updated — Fase 1 Implemented
**Author:** Generated via brainstorming session

**Changelog:**

| Versi | Tanggal | Perubahan |
|---|---|---|
| 1.0 | 2026-05-30 | Draft awal |
| 1.1 | 2026-05-30 | Update post-implementation: Beasiswa tabs, multi-student Input Payment, SLA tracking, Laporan Siswa, data migrasi Excel |

---

## Table of Contents / Daftar Isi

1. [Executive Summary / Ringkasan Eksekutif](#1-executive-summary--ringkasan-eksekutif)
2. [Problem Statement / Latar Belakang & Tujuan](#2-problem-statement--latar-belakang--tujuan)
3. [User Profile / Profil Pengguna](#3-user-profile--profil-pengguna)
4. [User Journey Flows / Alur Pengguna](#4-user-journey-flows--alur-pengguna)
5. [System Architecture / Arsitektur Sistem](#5-system-architecture--arsitektur-sistem)
6. [Module Catalog / Katalog Modul](#6-module-catalog--katalog-modul)
7. [Beasiswa Module — Spesifikasi Detail](#7-beasiswa-module--spesifikasi-detail)
8. [Payment Approval Memo — Spesifikasi Detail](#8-payment-approval-memo--spesifikasi-detail)
9. [Data Architecture / Model Data](#9-data-architecture--model-data)
10. [API Specification / Spesifikasi API](#10-api-specification--spesifikasi-api)
11. [Security & Access Control / Keamanan & Kontrol Akses](#11-security--access-control--keamanan--kontrol-akses)
12. [Non-Functional Requirements / Batasan & Risiko](#12-non-functional-requirements--batasan--risiko)
13. [Roadmap & Phasing / Peta Jalan](#13-roadmap--phasing--peta-jalan)

---

## 1. Executive Summary / Ringkasan Eksekutif

**Finance Hub** adalah sistem manajemen keuangan internal berbasis web untuk **Account Payable, Petty Cash, Beasiswa, dan proses pembayaran** yang dijalankan secara lokal (localhost/LAN). Sistem ini dirancang sebagai **platform multi-perusahaan** yang dapat menampung sub-modul finansial dari dua entitas: **Sinar Mas Tjipta** dan **Eka Tjipta Foundation**.

### Key Facts

| Item | Detail |
|---|---|
| Platform | Python Flask Web App (localhost / LAN) |
| Database | SQLite (file-based, zero setup) |
| Frontend | Jinja2 HTML Templates (vanilla HTML/CSS/JS) |
| Auth | JWT (JSON Web Token) via flask-jwt-extended |
| Multi-Company | Sinar Mas Tjipta, Eka Tjipta Foundation |
| User Type | 3 role: Requester, Verificator, Releaser |
| PDF Export | reportlab |
| REST API | JSON endpoints (`/api/v1/`) untuk integrasi sistem induk |
| Deployment | Localhost / LAN, tidak memerlukan internet atau cloud |

---

## 2. Problem Statement / Latar Belakang & Tujuan

### 2.1 Masalah Sebelumnya

Sebelum Finance Hub, pengelolaan keuangan dilakukan dengan:
- File Excel terpisah per modul, tersimpan di shared folder lokal (`Y:/`) tanpa kontrol akses.
- Tidak ada audit trail — tidak diketahui siapa yang mengubah data dan kapan.
- File lock conflict ketika Excel dibuka oleh lebih dari satu orang bersamaan.
- Proses pembayaran (Payment Approval Memo) dilakukan manual — tidak ada rekap otomatis lintas modul.
- Data Sinar Mas Tjipta dan Eka Tjipta Foundation tidak terpisah secara sistematis.

### 2.2 Solusi

Finance Hub menyediakan:
1. **Portal terpusat** — semua transaksi finansial diinput dan dikelola via web app.
2. **Multi-company support** — data SMT dan ETF terisolasi secara penuh di database.
3. **Auth berbasis JWT** — hanya user yang login yang dapat mengakses sistem.
4. **Payment Approval Memo otomatis** — rekap pembayaran dari semua sub-modul dikumpulkan, diajukan, dan dimonitor dalam satu tempat.
5. **REST API** — Finance Hub siap diintegrasikan ke platform induk manapun via JSON API.
6. **Export PDF & CSV** — laporan dapat diunduh untuk kebutuhan approval dan arsip.

### 2.3 Tujuan Sistem

| Tujuan | Indikator Keberhasilan |
|---|---|
| Digitalisasi data keuangan | 100% input via web, tidak ada Excel manual |
| Isolasi data antar perusahaan | Query apapun selalu difilter per `company_id` |
| Kontrol akses | Tidak ada halaman yang dapat diakses tanpa login |
| Payment approval terkonsolidasi | Semua pembayaran dari semua modul masuk ke Payment Approval Memo |
| Integrasi-ready | Semua operasi tersedia via REST API JSON |

### 2.4 Non-Tujuan (Out of Scope v1.0)

- Integrasi ERP eksternal (SAP, Oracle, dll).
- Notifikasi email/WhatsApp otomatis.
- Multi-level approval workflow (approval satu tahap saja di v1.0).
- Mobile native app.
- Modul Bank, Account Payable, Advance, Petty Cash, Sponsorship (Coming Soon).

---

## 3. User Profile / Profil Pengguna

Finance Hub v1.0 memiliki **3 role user** dengan permission berbeda.

### 3.1 Role Definitions

| Role | Siapa | Akses Utama |
|---|---|---|
| **Requester** | Staff keuangan / operator input data | Input data, lihat laporan |
| **Verificator** | Supervisor / checker | Review, verifikasi, buat memo |
| **Releaser** | Finance manager / approver final | Release pembayaran, manage users |

### 3.2 Permission Matrix

| Aksi | Requester | Verificator | Releaser |
|---|---|---|---|
| **Beasiswa** | | | |
| Input data siswa (tambah/edit) | ✅ | ✅ | ❌ |
| Input budget | ✅ | ✅ | ❌ |
| Input payment | ✅ | ❌ | ❌ |
| Lihat rekap & export CSV/PDF | ✅ | ✅ | ✅ |
| **Payment Approval Memo** | | | |
| Lihat daftar draft payment | ✅ | ✅ | ✅ |
| Buat memo baru | ❌ | ✅ | ❌ |
| Verifikasi / approve memo | ❌ | ✅ | ❌ |
| Release / mark as Paid | ❌ | ❌ | ✅ |
| Export PDF memo | ❌ | ✅ | ✅ |
| **Payment Application** | | | |
| Lihat monitoring status | ✅ | ✅ | ✅ |
| Update actual payment date | ❌ | ❌ | ✅ |
| **User Management** | | | |
| Tambah/nonaktifkan user | ❌ | ❌ | ✅ |
| **Dashboard** | ✅ | ✅ | ✅ |

### 3.3 User Management

- **Bootstrap:** Saat pertama kali aplikasi dijalankan, sistem otomatis membuat akun `admin` dengan role `releaser` dan password default.
- **First login:** User wajib ganti password default sebelum dapat mengakses modul manapun.
- **Tambah user:** User dengan role Releaser dapat menambah user baru dan assign role-nya.
- **Nonaktif user:** User dapat di-nonaktifkan tanpa dihapus (data audit tetap terjaga).

---

## 4. User Journey Flows / Alur Pengguna

### 4.1 Alur Login & Company Selection

```
Buka http://localhost:8080
    → Redirect ke /login (jika belum punya token)
    → Input username + password
    → Verifikasi JWT → redirect ke /select-company
    → Pilih perusahaan: [Sinar Mas Tjipta] | [Eka Tjipta Foundation]
    → Masuk ke Dashboard perusahaan yang dipilih
    → Session menyimpan company aktif selama token valid
```

### 4.2 Alur Input Beasiswa (ETF)

```
Dashboard ETF
    → Menu: Beasiswa
    → Tab: Data Siswa
        → Cari Siswa (search nama/kode/jenjang/angkatan/program/univ/fak)
        → Filter: Program / Pillar / Status
        → Tambah Siswa Baru (auto-generate kode, isi IPK per sem/penelitian)
        → Lihat kolom Budget / Payment / Sisa per siswa
        → Klik Update | Hapus | Lihat Sisa Budget

    → Tab: Input Budget
        → Pilih siswa via autocomplete
        → Isi: Tanggal, Pillar, batch item (Cat1 / Cat2 / Amount)
        → "+ Baris" untuk tambah item
        → Simpan → tabel budget per siswa muncul

    → Tab: Data Budget
        → Filter: Kata Kunci / Kategori 1 / Pillar / Bulan / Tahun / Program
        → Edit / Hapus baris individual
        → Export CSV | Export PDF

    → Tab: Input Payment  [NEW]
        → Isi header: Tanggal, PAM (auto-format PAM-XXX-MM-YYYY), Pillar, Perusahaan
        → "+ Tambah Baris" untuk setiap siswa yang dibayar:
            → Cari siswa via autocomplete
            → Pilih Kategori 1, Kategori 2, isi Amount
            → Isi 4 tanggal SLA (opsional): Tgl Pengajuan, Tgl Receive, Tgl PA, Tgl Final
        → "Simpan Payment" → semua baris tersimpan sebagai draft

    → Tab: Data Payment
        → Summary cards per kategori: Budget / Payment / Selisih
        → Filter: Kata Kunci / Kategori 1 / Pillar / Bulan / Tahun / Program / Status
        → Hapus baris (status draft saja)
        → Export CSV | Export PDF

    → Tab: Report Siswa
        → Pilih siswa via autocomplete
        → Tampilkan: data lengkap siswa, IPK, rekap per kategori
        → Detail tabel budget + detail tabel payment
        → Export CSV | Export PDF
```

### 4.3 Alur Payment Approval Memo

```
Dashboard [SMT | ETF]
    → Menu: Payment Approval Memo
    → Lihat daftar payment draft dari semua modul
    → Pilih payment yang akan diajukan → tambahkan ke Memo baru
    → Generate Memo Number (PAM/ETF/2026/001)
    → Print / Export PDF memo untuk approval
    → Update status: Draft → Submitted → Approved → Paid
```

### 4.4 Alur Ganti Perusahaan

```
Dari halaman manapun
    → Klik nama perusahaan di header/navbar
    → Pilih perusahaan lain
    → Semua data di semua halaman otomatis refresh ke perusahaan baru
```

---

## 5. System Architecture / Arsitektur Sistem

### 5.1 Struktur Folder Aplikasi

```
finance_hub/
├── app.py                      ← Flask entry point, register blueprints
├── config.py                   ← DB_PATH, JWT_SECRET, company list, constants
├── database.py                 ← init SQLite, CREATE TABLE IF NOT EXISTS
├── auth/
│   ├── routes.py               ← POST /auth/login, /auth/refresh, /auth/logout
│   │                              POST /auth/change-password
│   └── middleware.py           ← @jwt_required decorator
├── modules/
│   ├── beasiswa/
│   │   ├── routes.py           ← HTML routes: /beasiswa, /beasiswa/siswa, dll
│   │   ├── api.py              ← REST API: /api/v1/beasiswa/*
│   │   └── service.py          ← business logic (query SQLite)
│   ├── payment_memo/
│   │   ├── routes.py           ← HTML routes: /payment-memo
│   │   ├── api.py              ← REST API: /api/v1/payment-memo/*
│   │   └── service.py          ← aggregate dari semua modul
│   ├── payment_application/
│   │   ├── routes.py           ← HTML routes: /payment-application
│   │   └── service.py
│   └── [coming_soon]/          ← bank, account_payable, advance, pettycash, sponsorship
├── templates/
│   ├── base.html               ← layout utama (navbar, company switcher, footer)
│   ├── login.html
│   ├── company_select.html
│   ├── dashboard.html          ← dashboard per perusahaan
│   ├── beasiswa/
│   │   └── index.html          ← tabs: Data Siswa / Input Budget / Data Budget /
│   │                                       Input Payment / Data Payment / Report Siswa
│   ├── payment_memo/
│   │   └── index.html
│   └── payment_application/
│       └── index.html
├── static/
│   ├── css/style.css
│   └── js/app.js
├── finance_hub.db              ← SQLite, auto-created saat pertama run
└── requirements.txt
```

### 5.2 Tech Stack

| Layer | Teknologi | Keterangan |
|---|---|---|
| Backend | Python 3.9+ / Flask | Framework web |
| Database | SQLite (built-in Python) | Zero setup, file-based |
| Auth | flask-jwt-extended | JWT access + refresh token |
| Password | bcrypt | Hashing aman |
| PDF | reportlab | Generate laporan PDF |
| Frontend | Jinja2 + vanilla JS | Server-side rendering |
| HTTP | Flask dev server / waitress | Localhost / LAN |

### 5.3 Dependencies (requirements.txt)

```
flask>=3.0
flask-jwt-extended>=4.6
bcrypt>=4.0
reportlab>=4.0
flask-cors>=4.0
waitress>=3.0       # production WSGI server untuk Windows LAN
```

---

## 6. Module Catalog / Katalog Modul

### 6.1 Sinar Mas Tjipta

| Modul | Status v1.0 | Deskripsi |
|---|---|---|
| Dashboard | ✅ Implemented | Statistik ringkas SMT |
| Bank | 🔜 Coming Soon | Manajemen rekening bank |
| Account Payable | 🔜 Coming Soon | Hutang & pembayaran ke vendor |
| Advance | 🔜 Coming Soon | Uang muka karyawan/proyek |
| Petty Cash | 🔜 Coming Soon | Kas kecil operasional |
| Sponsorship | 🔜 Coming Soon | Pengelolaan sponsorship |
| Payment Approval Memo | ✅ Implemented | Agregat pembayaran, print memo, approval tracking |
| Payment Application | ✅ Implemented | Monitoring status pengajuan & TAT |

### 6.2 Eka Tjipta Foundation

| Modul | Status v1.0 | Deskripsi |
|---|---|---|
| Dashboard | ✅ Implemented | Statistik ringkas ETF |
| Bank | 🔜 Coming Soon | Manajemen rekening bank |
| Account Payable | 🔜 Coming Soon | Hutang & pembayaran ke vendor |
| Advance | 🔜 Coming Soon | Uang muka |
| Petty Cash | 🔜 Coming Soon | Kas kecil |
| Beasiswa | ✅ Implemented | Manajemen penerima beasiswa, budget, payment, rekap |
| Payment Approval Memo | ✅ Implemented | Agregat dari Beasiswa (+ modul lain setelah ready) |
| Payment Application | ✅ Implemented | Monitoring status pengajuan & TAT |

---

## 7. Beasiswa Module — Spesifikasi Detail

### 7.1 Sub-Halaman / Tab

| Tab | Fungsi | Status |
|---|---|---|
| Data Siswa | List semua siswa + rekap Budget/Payment/Sisa, tambah/edit/hapus siswa, search & filter | ✅ |
| Input Budget | Pilih siswa via autocomplete, batch input alokasi per kategori/semester | ✅ |
| Data Budget | Tabel semua budget dengan filter (Kategori 1, Pillar, Bulan, Tahun, Program) + export CSV/PDF | ✅ |
| Input Payment | Multi-siswa: tambah baris per siswa, tiap baris pilih siswa, kat1, kat2, amount, 4 tanggal SLA | ✅ |
| Data Payment | Tabel semua payment dengan filter + summary cards (Pendidikan/Tunjangan/Penelitian/Medical/Total) + export CSV/PDF | ✅ |
| Report Siswa | Laporan per siswa: data detail, IPK, rekap per kategori, detail budget & payment, export CSV/PDF | ✅ |

### 7.2 Data Siswa — Field Lengkap

| Field | Tipe | Keterangan |
|---|---|---|
| Code | TEXT (unique) | Kode unik siswa |
| Nama | TEXT | Nama lengkap |
| Jenjang | ENUM | SD/SMA/SMA, S1, S2, S3, SETF |
| Angkatan | INTEGER | Tahun angkatan |
| Program | ENUM | Kejaksaan, Polri, Tjipta Siswa Mandiri, dll (15 program) |
| Fakultas | TEXT | Nama fakultas |
| Universitas | TEXT | Nama universitas |
| Bank | TEXT | Nama bank |
| No. Rekening | TEXT | Nomor rekening |
| Nama Rekening | TEXT | Nama pemilik rekening |
| Referensi | TEXT | Referensi/sumber |
| IPK Sem 1–10 | REAL | IPK per semester |
| IPK Penelitian 1–3 | REAL | IPK penelitian (untuk S2/S3) |
| Status | ENUM | Aktif, lulus, gugur, undur diri |
| Catatan | TEXT | Catatan bebas |

### 7.3 Budget — Field

| Field | Keterangan |
|---|---|
| Code Siswa | FK ke tabel siswa |
| Kategori 1 | Dropdown: By Pendidikan / By Tunjangan / By Penelitian / By Medical |
| Kategori 2 | Dropdown searchable 32+ opsi (semester, tahap, dll) |
| Tanggal | Tanggal alokasi |
| Amount | Nominal budget |
| Pillar | 7 pillar perusahaan |

### 7.4 Payment — Field

| Field | Keterangan |
|---|---|
| Code Siswa | FK ke tabel siswa |
| Kategori 1 & 2 | Sama dengan budget |
| Tanggal | Tanggal pembayaran |
| Amount | Nominal dibayarkan |
| Pillar | Shared per sesi input |
| PAM | Auto-format `PAM-{seq}-{MM}-{YYYY}`, diisi saat input |
| Perusahaan | 47+ perusahaan dalam grup Sinar Mas |
| Kategori 3 & 4 | Opsional — kategori tambahan |
| **Tgl Pengajuan** | *(TAT Date 1)* Tanggal pengajuan ke finance |
| **Tgl Receive** | *(TAT Date 2)* Tanggal finance menerima berkas |
| **Tgl PA** | *(TAT Date 3)* Tanggal Payment Application terbit |
| **Tgl Final** | *(TAT Date 4)* Tanggal pembayaran terealisasi |
| Memo ID | Link ke Payment Approval Memo (opsional) |
| Status | draft → approved |

### 7.5 Input Payment — Multi-Student Flow

Tab **Input Payment** menggantikan keterbatasan form lama (satu siswa per submit). Alur baru:

```
1. User isi header: Tanggal, PAM (urutan + auto-suffix MM-YYYY), Pillar, Perusahaan
2. Klik "+ Tambah Baris":
   - Input siswa: autocomplete dari daftar siswa aktif
   - Pilih Kategori 1 → Kategori 2 → input Amount
   - Isi 4 tanggal SLA (semua opsional, bisa diisi bertahap)
3. Ulangi untuk setiap siswa yang akan dibayar
4. Klik "Simpan" → semua baris tersimpan ke payment_beasiswa dengan status "draft"
```

Satu submit = banyak siswa, satu PAM, satu batch SLA tracking.

### 7.6 Data Siswa — Field Lengkap

| Field | Tipe | Keterangan |
|---|---|---|
| Code | TEXT (unique) | Auto-generated: `[kode_jenjang][YY][seq4]` |
| Nama | TEXT | Nama lengkap |
| Jenjang | ENUM | SD/SMP/SMA, S1, S2, S3, SETF |
| Angkatan | INTEGER | Tahun angkatan |
| Program | ENUM | 15 program beasiswa |
| Fakultas | TEXT | Nama fakultas |
| Universitas | TEXT | Nama universitas |
| Bank | TEXT | Nama bank |
| No. Rekening | TEXT | Nomor rekening |
| Nama Rekening | TEXT | Nama pemilik rekening |
| Referensi | TEXT | Referensi/sumber |
| IPK Sem 1–10 | REAL | IPK per semester |
| IPK Penelitian 1–3 | REAL | IPK penelitian (untuk S2/S3) |
| Status | ENUM | Aktif, lulus, gugur, undur diri |
| Catatan | TEXT | Catatan bebas |

### 7.7 Rekap & Report — Filter & Export

**Tab Data Siswa (Rekap):**

| Filter | Nilai |
|---|---|
| Cari kata kunci | Nama atau kode siswa |
| Program | Dropdown 15 program |
| Pillar | Dropdown 7 pillar |
| Status Siswa | Aktif / lulus / gugur / undur diri |

**Tab Report Siswa:**

| Konten | Detail |
|---|---|
| Info siswa | Semua field termasuk IPK |
| Summary per kategori | Budget vs Payment vs Sisa |
| Detail budget rows | Semua transaksi budget |
| Detail payment rows | Semua transaksi payment + status |

| Export | Format | Tersedia Di |
|---|---|---|
| CSV | Excel-compatible | Data Budget, Data Payment, Data Siswa, Report Siswa |
| PDF | reportlab A4 | Data Budget, Data Payment, Data Siswa, Report Siswa |

### 7.8 Data Migrated (Fase 1)

| Sumber | Tabel | Jumlah Record |
|---|---|---|
| DbSiswa (Excel) | siswa | 1,269 siswa |
| DbBudget (Excel) | budget_beasiswa | 3,859 baris |
| DbPayment (Excel) | payment_beasiswa | 9,567 baris |
| **Total** | | **~14,700 record** |

---

## 8. Payment Approval Memo — Spesifikasi Detail

### 8.1 Fungsi Utama

Payment Approval Memo (PAM) adalah **hub agregasi pembayaran** yang mengumpulkan data payment dari semua sub-modul aktif dan mengkonsolidasikannya menjadi satu dokumen memo pengajuan pembayaran ke vendor.

### 8.2 Alur PAM

```
Payment diinput di sub-modul (Beasiswa / AP / Advance / dll)
    → Entry otomatis masuk sebagai "draft" di PAM
    → Operator review daftar draft payment
    → Operator buat Memo baru → pilih item yang akan diajukan
    → Sistem generate Memo Number: PAM/{COMPANY_CODE}/{YYYY}/{SEQ}
        Contoh: PAM/ETF/2026/001, PAM/SMT/2026/015
    → Print / Export PDF memo untuk approval atasan
    → Update status Memo: Draft → Submitted → Approved → Paid
```

### 8.3 Status Payment Item

| Status | Keterangan |
|---|---|
| draft | Payment baru diinput di sub-modul, belum dimasukkan ke memo |
| in_memo | Sudah dimasukkan ke memo, menunggu approval |
| approved | Memo telah disetujui atasan |
| paid | Pembayaran telah dilakukan/dicairkan |

### 8.4 Memo PDF — Konten

- Header: logo / nama perusahaan, nomor memo, tanggal
- Tabel item: No, Nama Penerima, Bank/Rekening, Keterangan, Amount
- Sub-total per modul sumber
- Total keseluruhan
- Kolom tanda tangan: Dibuat oleh / Disetujui oleh / Tanggal

---

## 9. Data Architecture / Model Data

### 9.1 ERD Ringkas

```
companies (1) ──< siswa (N)
companies (1) ──< budget_beasiswa (N)
companies (1) ──< payment_beasiswa (N)
companies (1) ──< payment_memo (N)
payment_memo (1) ──< payment_memo_items (N)
payment_memo (1) ──< payment_application (N)
payment_beasiswa (N) >── payment_memo (1)
```

### 9.2 DDL Lengkap

```sql
-- Core
CREATE TABLE IF NOT EXISTS companies (
    id   INTEGER PRIMARY KEY,
    code TEXT UNIQUE NOT NULL,   -- 'SMT', 'ETF'
    name TEXT NOT NULL           -- 'Sinar Mas Tjipta', 'Eka Tjipta Foundation'
);

CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL DEFAULT 'requester',  -- 'requester', 'verificator', 'releaser'
    is_active     INTEGER DEFAULT 1,
    must_change_pw INTEGER DEFAULT 1,
    created_at    TEXT DEFAULT CURRENT_TIMESTAMP,
    last_login    TEXT
);

CREATE TABLE IF NOT EXISTS refresh_tokens (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER REFERENCES users(id),
    token_hash TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    revoked    INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Beasiswa
CREATE TABLE IF NOT EXISTS siswa (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id  INTEGER NOT NULL REFERENCES companies(id),
    code        TEXT NOT NULL,
    nama        TEXT NOT NULL,
    jenjang     TEXT,
    angkatan    INTEGER,
    program     TEXT,
    fakultas    TEXT,
    universitas TEXT,
    bank        TEXT,
    norek       TEXT,
    namarek     TEXT,
    referensi   TEXT,
    ipk_sem1    REAL DEFAULT 0, ipk_sem2  REAL DEFAULT 0,
    ipk_sem3    REAL DEFAULT 0, ipk_sem4  REAL DEFAULT 0,
    ipk_sem5    REAL DEFAULT 0, ipk_sem6  REAL DEFAULT 0,
    ipk_sem7    REAL DEFAULT 0, ipk_sem8  REAL DEFAULT 0,
    ipk_sem9    REAL DEFAULT 0, ipk_sem10 REAL DEFAULT 0,
    ipk_pen1    REAL DEFAULT 0, ipk_pen2  REAL DEFAULT 0,
    ipk_pen3    REAL DEFAULT 0,
    status      TEXT DEFAULT 'Aktif',
    catatan     TEXT,
    created_at  TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at  TEXT,
    UNIQUE(company_id, code)
);

CREATE TABLE IF NOT EXISTS budget_beasiswa (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL REFERENCES companies(id),
    siswa_code TEXT NOT NULL,
    cat1       TEXT,
    cat2       TEXT,
    tanggal    TEXT,
    amount     REAL DEFAULT 0,
    pillar     TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS payment_beasiswa (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id     INTEGER NOT NULL REFERENCES companies(id),
    siswa_code     TEXT NOT NULL,
    cat1           TEXT,
    cat2           TEXT,
    tanggal        TEXT,
    amount         REAL DEFAULT 0,
    pillar         TEXT,
    pam            TEXT,            -- format: PAM-{seq}-{MM}-{YYYY}
    perusahaan     TEXT,
    cat3           TEXT,
    cat4           TEXT,
    tgl_pengajuan  TEXT,            -- TAT Date 1: tanggal pengajuan ke finance
    tgl_receive    TEXT,            -- TAT Date 2: tanggal finance menerima berkas
    tgl_pa         TEXT,            -- TAT Date 3: tanggal Payment Application terbit
    tgl_final      TEXT,            -- TAT Date 4: tanggal realisasi pembayaran
    memo_id        INTEGER REFERENCES payment_memo(id),
    status         TEXT DEFAULT 'draft',
    created_at     TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Payment Memo
CREATE TABLE IF NOT EXISTS payment_memo (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id  INTEGER NOT NULL REFERENCES companies(id),
    memo_number TEXT UNIQUE,
    tanggal     TEXT,
    total_amount REAL DEFAULT 0,
    status      TEXT DEFAULT 'draft',
    notes       TEXT,
    created_by  TEXT,
    approved_by TEXT,
    approved_at TEXT,
    created_at  TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at  TEXT
);

CREATE TABLE IF NOT EXISTS payment_memo_items (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    memo_id       INTEGER NOT NULL REFERENCES payment_memo(id),
    source_module TEXT NOT NULL,   -- 'beasiswa', 'account_payable', 'advance', 'sponsorship'
    source_id     INTEGER NOT NULL,
    description   TEXT,
    amount        REAL DEFAULT 0,
    vendor        TEXT,
    bank_account  TEXT
);

-- Payment Application (monitoring)
CREATE TABLE IF NOT EXISTS payment_application (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id          INTEGER NOT NULL REFERENCES companies(id),
    memo_id             INTEGER NOT NULL REFERENCES payment_memo(id),
    application_number  TEXT UNIQUE,
    submitted_at        TEXT,
    target_payment_date TEXT,
    actual_payment_date TEXT,
    status              TEXT DEFAULT 'pending',
    tat_days            INTEGER,
    notes               TEXT,
    created_at          TEXT DEFAULT CURRENT_TIMESTAMP
);
```

---

## 10. API Specification / Spesifikasi API

Semua endpoint `/api/v1/*` memerlukan header:
```
Authorization: Bearer <access_token>
```

### 10.1 Auth Endpoints (Public)

| Method | Path | Request Body | Response |
|---|---|---|---|
| POST | `/api/auth/login` | `{username, password}` | `{access_token, refresh_token}` |
| POST | `/api/auth/refresh` | `{refresh_token}` | `{access_token}` |
| POST | `/api/auth/logout` | `{refresh_token}` | `{ok: true}` |
| POST | `/api/auth/change-password` | `{old_password, new_password}` | `{ok: true}` |

### 10.2 Beasiswa Endpoints

| Method | Path | Query Params | Keterangan |
|---|---|---|---|
| GET | `/api/v1/siswa` | `search`, `status`, `program`, `company` | List siswa |
| GET | `/api/v1/siswa/<code>` | — | Detail 1 siswa |
| POST | `/api/v1/siswa` | — | Tambah siswa |
| PUT | `/api/v1/siswa/<code>` | — | Update siswa |
| GET | `/api/v1/budget` | `code`, `pillar`, `company` | List budget |
| POST | `/api/v1/budget` | — | Tambah budget |
| GET | `/api/v1/payment` | `code`, `pillar`, `status`, `company` | List payment |
| POST | `/api/v1/payment` | — | Tambah payment 1 siswa (legacy, status: draft) |
| POST | `/beasiswa/payment/tambah-multi` | — | Tambah payment multi-siswa + SLA dates (status: draft) |
| GET | `/api/v1/rekap` | `company`, `program`, `pillar`, `status` | Summary per siswa |
| GET | `/api/v1/rekap/export/csv` | (same) | Download CSV |
| GET | `/api/v1/rekap/export/pdf` | (same) | Download PDF |
| GET | `/api/v1/dashboard` | `company` | Angka agregat |

### 10.3 Payment Memo Endpoints

| Method | Path | Keterangan |
|---|---|---|
| GET | `/api/v1/payment-memo` | List semua memo per company |
| POST | `/api/v1/payment-memo` | Buat memo baru |
| GET | `/api/v1/payment-memo/<id>` | Detail memo + items |
| PUT | `/api/v1/payment-memo/<id>/status` | Update status memo |
| GET | `/api/v1/payment-memo/<id>/export/pdf` | Download PDF memo |
| GET | `/api/v1/payment-draft` | List payment draft (belum di-memo) per company |

### 10.4 Standard Response Format

```json
{
  "ok": true,
  "data": { ... },
  "pesan": "Keterangan sukses atau error",
  "detail": "Stack trace (hanya saat error, dev mode)"
}
```

---

## 11. Security & Access Control / Keamanan & Kontrol Akses

### 11.1 Authentication Flow

```
1. User POST /api/auth/login → sistem verifikasi password dengan bcrypt
2. Jika valid → generate:
   - access_token: JWT, expire 1 jam, payload: {user_id, username, company_active}
   - refresh_token: JWT, expire 7 hari, di-store hash-nya di tabel refresh_tokens
3. Setiap request API → middleware decode access_token
4. Token expire → client gunakan refresh_token untuk dapat access_token baru
5. Logout → revoke refresh_token di database
```

### 11.2 Password Policy

- Minimum 8 karakter
- Wajib ganti password default saat first login
- Password di-hash dengan bcrypt (cost factor 12)
- Password lama tidak boleh sama dengan password baru

### 11.3 Company Data Isolation

- Semua tabel data bisnis memiliki kolom `company_id`
- Setiap query **wajib** menyertakan `WHERE company_id = ?` dari session aktif
- Tidak ada endpoint yang mengembalikan data lintas perusahaan
- Company aktif disimpan di JWT payload — tidak bisa dimanipulasi client

### 11.4 API Security

- CORS dikonfigurasi hanya untuk origin yang diizinkan (localhost / IP LAN)
- Rate limiting: maksimal 10 request/detik per IP (via Flask-Limiter, coming soon)
- Semua input divalidasi sebelum dieksekusi ke SQLite (parameterized query — tidak ada string concatenation di SQL)

---

## 12. Non-Functional Requirements / Batasan & Risiko

### 12.1 Performance

| Metrik | Target |
|---|---|
| Waktu load halaman | < 2 detik pada LAN |
| Response API | < 500ms untuk query normal |
| Concurrent users | 10–20 user (SQLite write lock per transaksi) |
| Ukuran database | Estimasi < 100MB untuk 5 tahun data |

### 12.2 Deployment & Availability

**Model: Centralized Server (Laptop)**

```
[Laptop Server — selalu nyala saat jam kerja]
  └── python app.py  (Flask + waitress)
  └── finance_hub.db (SQLite, lokal di laptop server)

[User lain] ──browser──→ http://[IP-laptop]:8080
```

- Flask dijalankan di laptop yang berperan sebagai server (terhubung ke WiFi/LAN kantor).
- Semua user lain cukup buka browser dan akses via IP laptop server.
- Laptop server **tidak boleh sleep/hibernate** saat jam kerja.
- Tidak ada SLA formal — downtime = restart Python/Flask.
- **Backup:** copy file `finance_hub.db` ke Y:/ shared folder secara berkala (manual atau Windows Task Scheduler). Y:/ digunakan sebagai backup destination, **bukan** sebagai lokasi database aktif.
- IP laptop bisa berubah — rekomendasikan IT set static IP atau catat IP aktif.

### 12.3 Risiko & Mitigasi

| Risiko | Dampak | Mitigasi |
|---|---|---|
| File `finance_hub.db` terhapus / corrupt | Kehilangan semua data | Backup harian otomatis ke folder lain; instruksi backup di README |
| SQLite write lock jika concurrent write tinggi | Operasi simpan lambat | Acceptable untuk 10–20 user; jika perlu scale gunakan PostgreSQL di versi berikutnya |
| JWT secret bocor | Semua token bisa dipalsukan | Simpan JWT secret di environment variable, bukan di kode |
| Windows machine mati | Sistem tidak accessible | Jalankan di mesin yang selalu on; pertimbangkan UPS |

### 12.4 Browser Support

- Chrome / Edge (modern) — primary target
- Firefox — supported
- Internet Explorer — tidak didukung

---

## 13. Roadmap & Phasing / Peta Jalan

### Fase 1 — Foundation (v1.0) — ✅ COMPLETE

**Scope:** App shell, auth, company selector, dashboard, modul Beasiswa (ETF), Payment Approval Memo, Payment Application.

**Test coverage: 56/56 tests pass**

| Deliverable | Status | Catatan |
|---|---|---|
| Flask app structure | ✅ | Blueprint-based, 5 modul terdaftar |
| SQLite init + migration | ✅ | `init_db()` + `migrate_db()` untuk ALTER TABLE backward-compatible |
| Auth (JWT) | ✅ | Login, logout, refresh, ganti password, first-login gate |
| Company Selector | ✅ | Landing page pilih SMT / ETF |
| Dashboard | ✅ | Widget: total siswa, total budget, total payment per company |
| **Modul Beasiswa — Data Siswa** | ✅ | CRUD + search 7 kolom + IPK sem 1–10 + IPK penelitian 1–3 + delete cascade |
| **Modul Beasiswa — Input Budget** | ✅ | Autocomplete siswa, batch input Cat1/Cat2/Amount, pillar per sesi |
| **Modul Beasiswa — Data Budget** | ✅ | Filter lengkap, summary cards, edit/hapus baris, export CSV/PDF |
| **Modul Beasiswa — Input Payment** | ✅ | Multi-siswa per submit, PAM auto-format, 4 SLA dates (TAT tracking) |
| **Modul Beasiswa — Data Payment** | ✅ | Filter lengkap, summary cards per kategori, export CSV/PDF |
| **Modul Beasiswa — Report Siswa** | ✅ | Detail per siswa + IPK + rekap + budget/payment detail, export CSV/PDF |
| **Data Migration Excel → SQLite** | ✅ | 1,269 siswa, 3,859 budget, 9,567 payment (~14,700 record) |
| Payment Approval Memo | ✅ | List draft payment, buat memo, update status, export PDF |
| Payment Application | ✅ | List memo, update actual payment date, hitung TAT |
| REST API (`/api/v1/`) | ✅ | Semua operasi Beasiswa + PAM tersedia via JSON API |
| Coming Soon pages | ✅ | Placeholder UI untuk modul Bank, AP, Advance, Pettycash, Sponsorship |
| Production server | ✅ | `run_production.py` via waitress, startup validation |

### Fase 2 — Modul Tambahan (v1.x)

Dikerjakan setelah Fase 1 selesai dan stabil. Urutan prioritas:

1. **Account Payable** (SMT + ETF) — modul paling kritikal setelah Beasiswa
2. **Advance** (SMT + ETF)
3. **Petty Cash** (SMT + ETF)
4. **Sponsorship** (SMT only)
5. **Bank** (SMT + ETF)

### Fase 3 — Enhancement (v2.0)

- Notifikasi in-app (bell icon) saat memo baru dibuat
- Dashboard charts (Chart.js) — tren pembayaran per bulan
- Audit log — siapa mengubah apa dan kapan
- Multi-level approval untuk PAM (jika diperlukan)
- Migrasi ke PostgreSQL jika concurrent user meningkat signifikan

---

*Document generated: 2026-05-30 | Finance Hub PRD v1.1 — Updated post Fase 1 implementation*
