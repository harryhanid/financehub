# Finance Hub — Product Requirements Document (PRD)

**Date / Tanggal:** 2026-06-01
**Version / Versi:** 1.2
**Status:** Updated — Post Fase 1 + PAM Full Feature + Days of PAM + Dynamic Badges
**Author:** Generated via brainstorming session

**Changelog:**

| Versi | Tanggal | Perubahan |
|---|---|---|
| 1.0 | 2026-05-30 | Draft awal |
| 1.1 | 2026-05-30 | Update post-implementation: Beasiswa tabs, multi-student Input Payment, SLA tracking, Laporan Siswa, data migrasi Excel |
| 1.2 | 2026-06-01 | Tambah: PAM Records + GL Account, Draft Memo (inline editing + PDF/Excel custom export), Days of PAM tab (lazy-load AJAX), Dynamic Summary Badges (filter-aware); Perbandingan sistem Excel lama (DbBeasiswa v2.2.xlsm); test coverage 56 → 127 |

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

Finance Hub menggantikan sistem lama berbasis file **Microsoft Excel VBA Macro (`DbBeasiswa v2.2.xlsm`)** yang dioperasikan secara bersama via shared folder `Y:/`. Perbandingan lengkap sistem lama vs baru tersedia di [Bagian 2.5](#25-perbandingan-sistem-excel-lama-vs-finance-hub).

### Posisi dalam Masterplan Automasi PT Sinar Mas Tjipta

Finance Hub adalah implementasi **Fase 4 (F4) — AP, Tax & Payment** dari *Master Plan Automasi Finance & Office Management* PT Sinar Mas Tjipta. Sistem ini bekerja dalam ekosistem yang lebih besar bersama **PR Portal (F2)** sebagai sistem hulu dan **Accounting Hub (F5)** sebagai sistem hilir.

| Fase | Sistem | Status |
|---|---|---|
| **F1** — Budget & Master Data | Google Sheets / SQL | Ongoing |
| **F2** — Purchasing (Web Portal) | **PR Portal** (Google Apps Script) | Ongoing |
| **F3** — Receiving & Asset Capture | SharePoint / Microsoft Lists | TBA |
| **F4** — AP, Tax & Payment | **Finance Hub** ← *Sistem ini* | Implemented (Beasiswa + PAM) / Coming Soon (AP & Tax) |
| **F5** — Accounting Hub (Posting) | Power Pivot / VBA / Power Query | Ongoing |
| **F6** — Reporting & Analytics | Looker Studio / Excel Dashboard | TBA |

**Alur data terintegrasi:**
```
PR Portal (F2) ──PO approved──▶ Finance Hub (F4) ──journal──▶ Accounting Hub (F5)
                                  ├── 3-Way Match (PO/GR/Invoice)
                                  ├── PPh/PPN Auto-Calculation
                                  ├── Payment Disbursement (CSV batch)
                                  └── PAM → GL Account Posting
```

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
| Excel Export | openpyxl |
| REST API | JSON endpoints (`/api/v1/`) untuk integrasi sistem induk |
| Deployment | Localhost / LAN, tidak memerlukan internet atau cloud |
| Test Coverage | 127 automated tests (pytest) |

---

## 2. Problem Statement / Latar Belakang & Tujuan

### 2.1 Masalah Sebelumnya

Sebelum Finance Hub, pengelolaan keuangan beasiswa dilakukan dengan file Excel VBA Macro (`DbBeasiswa v2.2.xlsm`) yang tersimpan di shared folder lokal (`Y:/`):

- File Excel dibuka bersama-sama → **file lock conflict** ketika lebih dari satu orang membuka file secara bersamaan.
- **Tidak ada autentikasi** — siapapun yang bisa akses `Y:/` dapat membuka, mengubah, bahkan menghapus data.
- **Tidak ada audit trail** — tidak diketahui siapa yang mengubah data dan kapan.
- Pembuatan **Payment Approval Memo** dilakukan manual dengan mengisi sheet `Detail PAM` dan `Rangkuman PAM`, lalu mencetak.
- **PAM Recon** menggunakan PivotTable Excel yang harus di-refresh manual setiap kali ada perubahan data.
- **Days of PAM** (4 tanggal SLA: Pengajuan, Receive, PA, Final) dicatat sebagai kolom Cat3–Cat7 di sheet `DbPayment`, tidak ada validasi format tanggal.
- Data **Medical/Hospital** (`DbHospital`) dikelola dalam sheet terpisah yang tidak terintegrasi otomatis dengan rekap kategori.
- Data Sinar Mas Tjipta dan Eka Tjipta Foundation **tidak terpisah secara sistematis**.

### 2.2 Solusi

Finance Hub menyediakan:

1. **Portal terpusat** — semua transaksi finansial diinput dan dikelola via web app.
2. **Multi-company support** — data SMT dan ETF terisolasi secara penuh di database.
3. **Auth berbasis JWT** — hanya user yang login yang dapat mengakses sistem.
4. **Payment Approval Memo otomatis** — rekap pembayaran dari semua sub-modul dikumpulkan, diajukan, dan dimonitor dalam satu tempat.
5. **Draft Memo dengan inline editing** — memo dapat diedit langsung di browser sebelum diekspor ke PDF/Excel.
6. **Days of PAM tracking** — 4 tanggal SLA diinput langsung saat entry payment, dapat diperbarui bulk via tab khusus.
7. **Dynamic summary badges** — kartu ringkasan Budget/Payment/Selisih di tab Data Budget dan Data Payment secara otomatis mencerminkan filter aktif (bukan lagi data global).
8. **REST API** — Finance Hub siap diintegrasikan ke platform induk manapun via JSON API.
9. **Export PDF & Excel** — laporan dapat diunduh dalam format standar yang sudah disesuaikan dengan format memo perusahaan.

### 2.3 Tujuan Sistem

| Tujuan | Indikator Keberhasilan |
|---|---|
| Digitalisasi data keuangan | 100% input via web, tidak ada Excel manual |
| Isolasi data antar perusahaan | Query apapun selalu difilter per `company_id` |
| Kontrol akses | Tidak ada halaman yang dapat diakses tanpa login |
| Payment approval terkonsolidasi | Semua pembayaran dari semua modul masuk ke Payment Approval Memo |
| Integrasi-ready | Semua operasi tersedia via REST API JSON |

### 2.4 Non-Tujuan (Out of Scope v1.x)

- Integrasi ERP eksternal (SAP, Oracle, dll).
- Notifikasi email/WhatsApp otomatis.
- Multi-level approval workflow (approval satu tahap saja di v1.x).
- Mobile native app.
- Modul Bank, Account Payable, Advance, Petty Cash, Sponsorship (Coming Soon).
- **F2 Purchasing** — sudah ditangani PR Portal (PDO/PTA/PR/PO dengan Google Apps Script).
- **F3 Receiving & Asset Capture** — SharePoint / Microsoft Lists (sistem terpisah, TBA).
- **F5 Accounting Hub** — Power Pivot / VBA Macro (sistem terpisah, ongoing).

---

### 2.5 Perbandingan Sistem Excel Lama vs Finance Hub

Bagian ini menjelaskan cara kerja sistem **DbBeasiswa v2.2.xlsm** (file Excel VBA Macro terakhir yang digunakan) dan perbedaannya dengan Finance Hub.

#### 2.5.1 Struktur Sistem Lama (DbBeasiswa v2.2.xlsm)

File Excel ini menggunakan **VBA Macro dengan 7 tombol navigasi** di sheet `Module`:

| No | Tombol Macro | Sheet Tujuan | Fungsi |
|---|---|---|---|
| 1 | Input Baru Penerima Beasiswa | `DbSiswa` | Form input siswa baru via UserForm VBA |
| 2 | Update data Siswa | `DbSiswa` | Edit data siswa yang sudah ada |
| 3 | Input Budget Beasiswa | `DbBudget` | Input alokasi budget per siswa per kategori |
| 4 | Input Pembayaran | `DbPayment` | Input realisasi pembayaran per siswa |
| 5 | Payment Approval Memo | `Detail PAM` | Generate memo pembayaran untuk dicetak |
| 6 | Input Budget Medical | `DbBudget` | Input alokasi budget klaim Medical |
| 7 | Input Claim Medical | `DbBudget` | Input realisasi klaim Medical |

**Daftar Sheet lengkap:**

| Sheet | Fungsi |
|---|---|
| `Module` | Halaman utama dengan 7 tombol navigasi macro |
| `DbSiswa` | Database siswa (1,269 baris + header) |
| `DbBudget` | Database alokasi budget beasiswa |
| `DbPayment` | Database realisasi pembayaran |
| `DbHospital` | Database klaim Medical/Hospital |
| `PAM Recon` | PivotTable rekonsiliasi PAM — harus di-refresh manual |
| `Detail PAM` | Template memo payment per PAM (satu PAM per halaman cetak) |
| `Rangkuman PAM` | Rangkuman memo PAM untuk dicetak (format tabel: No, Nama, Bank, No Rekening, Total) |
| `Lookup` | Tabel referensi dropdown (program, pillar, kategori, dll) |
| `Family` | Data anggota keluarga siswa |
| `SETF Rek` | Data rekening untuk program SETF |
| `Coretan` | Sheet kerja sementara (scratch pad) |

#### 2.5.2 Keterbatasan Sistem Lama

| Keterbatasan | Detail | Solusi di Finance Hub |
|---|---|---|
| **File lock** | Hanya 1 orang bisa edit, yang lain Read-only | Multi-user concurrent, semua bisa input bersamaan |
| **Tidak ada auth** | Siapapun yang akses `Y:/` bisa ubah data | Login JWT wajib; role-based access per aksi |
| **Tidak ada audit trail** | Tidak diketahui siapa/kapan mengubah data | `created_at` / `updated_at` di semua tabel |
| **PAM manual** | Isi sheet `Detail PAM` manual, cetak lalu scan | Draft Memo otomatis dari data payment; export PDF/Excel standar |
| **PAM Recon manual** | PivotTable harus di-refresh manual | Tabel `pam_records` auto-created saat payment disimpan |
| **Summary tidak real-time** | Pivot/formula perlu refresh manual setelah tiap input | Summary badges update otomatis, filter-aware |
| **Days of PAM ad-hoc** | Tanggal SLA diisi di kolom Cat3–Cat7 tanpa validasi | 4 kolom SLA terstruktur (`tgl_pengajuan`, `tgl_receive`, `tgl_pa`, `tgl_final`) + bulk-update UI |
| **Medical terpisah** | `DbHospital` sheet terpisah, tidak masuk rekap kategori | `By Medical` masuk kategori standar (`cat1`) di tabel `payment_beasiswa` |
| **No export standar** | Print langsung dari Excel, format berbeda-beda | Export PDF (ReportLab) dan Excel (openpyxl) format standar perusahaan |
| **Tidak ada validasi** | Data bisa diisi bebas, tidak ada type checking | Validasi input di service layer, parameterized SQL |
| **Data tidak terisolasi** | Semua perusahaan campur dalam satu file | `company_id` wajib di semua tabel, tidak ada cross-company query |

#### 2.5.3 Fitur Baru yang Tidak Ada di Sistem Lama

| Fitur | Deskripsi |
|---|---|
| **Multi-user concurrent** | 10–20 user bisa input bersamaan tanpa konflik |
| **REST API** | Semua operasi tersedia via JSON API untuk integrasi |
| **PAM Records + GL Account** | Setiap PAM otomatis tercatat dengan nomor GL Account dari Chart of Accounts |
| **Draft Memo inline editing** | Edit nama, total, catatan memo langsung di browser sebelum export |
| **Days of PAM tab** | Tab khusus monitoring 4 tanggal SLA per PAM, bulk-update, search PAM No + Nama |
| **Dynamic summary badges** | Kartu Budget/Payment/Selisih mencerminkan data yang sedang ditampilkan (bukan global) |
| **Laporan per Siswa** | Rekap lengkap per siswa dengan IPK, detail budget, detail payment, export PDF/CSV |
| **Data migrasi** | 14,700+ record dari Excel lama berhasil dimigrasikan ke SQLite |
| **Automated tests** | 127 pytest tests untuk menjamin kebenaran bisnis logic |

---

## 3. User Profile / Profil Pengguna

Finance Hub v1.x memiliki **3 role user** dengan permission berbeda.

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
| **Days of PAM** | | | |
| Lihat tabel Days of PAM | ✅ | ✅ | ✅ |
| Bulk update tanggal SLA | ✅ | ✅ | ✅ |
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
        → Summary badges (Pendidikan/Tunjangan/Penelitian/Medical/Total)
          ★ Badges mencerminkan filter aktif — bukan total global
        → Edit / Hapus baris individual
        → Export CSV | Export PDF

    → Tab: Input Payment
        → Isi header: Tanggal, PAM (auto-format PAM-XXX-ETF-MM-YYYY), Pillar, Perusahaan
        → "+ Tambah Baris" untuk setiap siswa yang dibayar:
            → Cari siswa via autocomplete
            → Pilih Kategori 1, Kategori 2, isi Amount
            → Isi 4 tanggal SLA (opsional): Tgl Pengajuan, Tgl Receive, Tgl PA, Tgl Final
        → "Simpan Payment" → semua baris tersimpan sebagai draft
          ★ PAM record otomatis dibuat di tabel pam_records

    → Tab: Data Payment
        → Summary badges per kategori: Budget / Payment / Selisih
          ★ Badges mencerminkan filter aktif — bukan total global
        → Filter: Kata Kunci / Kategori 1 / Pillar / Bulan / Tahun / Program / Status
        → Hapus baris (status draft saja)
        → Export CSV | Export PDF

    → Tab: Report Siswa
        → Pilih siswa via autocomplete
        → Tampilkan: data lengkap siswa, IPK, rekap per kategori
        → Detail tabel budget + detail tabel payment
        → Export CSV | Export PDF
```

### 4.3 Alur Payment Approval Memo (PAM)

```
Dashboard [SMT | ETF]
    → Menu: Payment Approval Memo
    → Tab: Daftar PAM
        → Lihat semua PAM records (auto-created saat Input Payment)
        → Isi / update GL Account per PAM via dropdown COA
        → Filter per status, tanggal, PAM No

    → Tab: Draft Memo
        → Cari PAM No via autocomplete
        → Preview form memo: No PAM, tanggal, GL Account, Cost Center
        → Edit inline: nama penerima, rekening, catatan, jumlah
        → Lampiran: detail per siswa (collapsible)
        → Export PDF (format standar perusahaan)
        → Export Excel (2 sheet: Rangkuman + Detail)

    → Tab: Days of PAM
        → Search PAM No atau Nama Siswa (search-first, lazy-load)
        → Filter: Bulan, Tahun, Status SLA
        → Pilih baris via checkbox → Bulk update tanggal SLA
        → Tampilkan status keterlambatan per tahap
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
financehub/
├── run.py                      ← waitress production server entry point
├── config.py                   ← DB_PATH, JWT_SECRET, company list, constants, COA_LIST
├── database.py                 ← init SQLite, CREATE TABLE IF NOT EXISTS, seed COA
├── app/
│   ├── __init__.py             ← Flask app factory, register blueprints
│   └── modules/
│       ├── beasiswa/
│       │   ├── routes.py       ← HTML + JSON routes: /beasiswa/*, /beasiswa/payment/tambah-multi
│       │   ├── api.py          ← REST API: /api/v1/beasiswa/*
│       │   └── service.py      ← business logic (siswa CRUD, budget, payment, rekap, DOP, PAM)
│       ├── payment_memo/
│       │   ├── routes.py       ← HTML routes: /payment-memo, PAM records, Draft Memo, DOP
│       │   ├── api.py          ← REST API: /api/v1/payment-memo/*
│       │   ├── service.py      ← aggregate dari semua modul, PAM generation, GL account
│       │   └── exports.py      ← export_pam_pdf(), export_pam_excel(), custom variants
│       ├── payment_application/
│       │   ├── routes.py       ← HTML routes: /payment-application
│       │   └── service.py
│       └── [coming_soon]/      ← bank, account_payable, advance, pettycash, sponsorship
├── templates/
│   ├── base.html               ← layout utama (navbar, company switcher, footer)
│   ├── login.html
│   ├── company_select.html
│   ├── dashboard.html          ← dashboard per perusahaan
│   ├── beasiswa/
│   │   └── index.html          ← tabs: Data Siswa / Input Budget / Data Budget /
│   │                                       Input Payment / Data Payment / Report Siswa
│   ├── payment_memo/
│   │   └── index.html          ← tabs: Daftar PAM / Draft Memo / Days of PAM
│   └── payment_application/
│       └── index.html
├── static/
│   ├── css/style.css
│   └── js/app.js
├── tests/
│   ├── conftest.py             ← pytest fixtures, test DB setup
│   ├── test_beasiswa_service.py
│   ├── test_beasiswa_api.py
│   ├── test_pam_service.py
│   ├── test_pam_exports.py
│   ├── test_payment_memo_service.py
│   ├── test_users_service.py
│   ├── test_auth.py
│   ├── test_dashboard.py
│   └── test_database.py
└── finance_hub.db              ← SQLite, auto-created saat pertama run
```

### 5.2 Tech Stack

| Layer | Teknologi | Keterangan |
|---|---|---|
| Backend | Python 3.9+ / Flask | Framework web |
| Database | SQLite (built-in Python) | Zero setup, file-based |
| Auth | flask-jwt-extended | JWT access + refresh token |
| Password | bcrypt | Hashing aman |
| PDF | reportlab | Generate laporan PDF |
| Excel | openpyxl | Generate laporan Excel (.xlsx) |
| Frontend | Jinja2 + vanilla JS | Server-side rendering |
| HTTP | Flask dev server / waitress | Localhost / LAN |
| Testing | pytest + flask test client | 127 automated tests |

### 5.3 Dependencies (requirements.txt)

```
flask>=3.0
flask-jwt-extended>=4.6
bcrypt>=4.0
reportlab>=4.0
openpyxl>=3.1
flask-cors>=4.0
waitress>=3.0       # production WSGI server untuk Windows LAN
```

---

## 6. Module Catalog / Katalog Modul

### 6.1 Sinar Mas Tjipta

| Modul | Status | Deskripsi |
|---|---|---|
| Dashboard | ✅ Implemented | Statistik ringkas SMT |
| Bank | 🔜 Coming Soon | Manajemen rekening bank |
| Account Payable | 🔜 Coming Soon | Hutang & pembayaran ke vendor |
| Advance | 🔜 Coming Soon | Uang muka karyawan/proyek |
| Petty Cash | 🔜 Coming Soon | Kas kecil operasional |
| Sponsorship | 🔜 Coming Soon | Pengelolaan sponsorship |
| Payment Approval Memo | ✅ Implemented | PAM Records, Draft Memo, Days of PAM, GL Account, PDF/Excel export |
| Payment Application | ✅ Implemented | Monitoring status pengajuan & TAT |

### 6.2 Eka Tjipta Foundation

| Modul | Status | Deskripsi |
|---|---|---|
| Dashboard | ✅ Implemented | Statistik ringkas ETF |
| Bank | 🔜 Coming Soon | Manajemen rekening bank |
| Account Payable | 🔜 Coming Soon | Hutang & pembayaran ke vendor |
| Advance | 🔜 Coming Soon | Uang muka |
| Petty Cash | 🔜 Coming Soon | Kas kecil |
| Beasiswa | ✅ Implemented | Manajemen penerima beasiswa, budget, payment, rekap, dynamic badges |
| Payment Approval Memo | ✅ Implemented | PAM Records, Draft Memo, Days of PAM, GL Account, PDF/Excel export |
| Payment Application | ✅ Implemented | Monitoring status pengajuan & TAT |

---

## 7. Beasiswa Module — Spesifikasi Detail

### 7.1 Sub-Halaman / Tab

| Tab | Fungsi | Status |
|---|---|---|
| Data Siswa | List semua siswa + rekap Budget/Payment/Sisa, tambah/edit/hapus siswa, search & filter | ✅ |
| Input Budget | Pilih siswa via autocomplete, batch input alokasi per kategori/semester | ✅ |
| Data Budget | Tabel semua budget dengan filter + dynamic summary badges (filter-aware) + export CSV/PDF | ✅ |
| Input Payment | Multi-siswa: tambah baris per siswa, tiap baris pilih siswa, kat1, kat2, amount, 4 tanggal SLA | ✅ |
| Data Payment | Tabel semua payment dengan filter + dynamic summary badges (filter-aware) + export CSV/PDF | ✅ |
| Report Siswa | Laporan per siswa: data detail, IPK, rekap per kategori, detail budget & payment, export CSV/PDF | ✅ |

### 7.2 Data Siswa — Field Lengkap

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
| PAM | Auto-format `PAM-{seq}-{COMPANY}-{MM}-{YYYY}`, diisi saat input |
| Perusahaan | 47+ perusahaan dalam grup Sinar Mas |
| Kategori 3 & 4 | Opsional — kategori tambahan |
| **Tgl Pengajuan** | *(SLA Date 1)* Tanggal pengajuan ke finance |
| **Tgl Receive** | *(SLA Date 2)* Tanggal finance menerima berkas |
| **Tgl PA** | *(SLA Date 3)* Tanggal Payment Application terbit |
| **Tgl Final** | *(SLA Date 4)* Tanggal pembayaran terealisasi |
| Memo ID | Link ke Payment Approval Memo (opsional) |
| Status | draft → approved |

### 7.5 Input Payment — Multi-Student Flow

Tab **Input Payment** menggantikan keterbatasan form lama (satu siswa per submit). Alur baru:

```
1. User isi header: Tanggal, PAM (urutan + auto-suffix COMPANY-MM-YYYY), Pillar, Perusahaan
2. Klik "+ Tambah Baris":
   - Input siswa: autocomplete dari daftar siswa aktif
   - Pilih Kategori 1 → Kategori 2 → input Amount
   - Isi 4 tanggal SLA (semua opsional, bisa diisi bertahap)
3. Ulangi untuk setiap siswa yang akan dibayar
4. Klik "Simpan" → semua baris tersimpan ke payment_beasiswa dengan status "draft"
5. PAM record otomatis dibuat di tabel pam_records (atomic transaction)
```

Satu submit = banyak siswa, satu PAM, satu batch SLA tracking.

### 7.6 Dynamic Summary Badges

Tab **Data Budget** dan **Data Payment** menampilkan kartu ringkasan per kategori (Pendidikan, Tunjangan, Penelitian, Medical, Total) dengan 3 nilai: **Budget**, **Payment**, **Selisih**.

**Cara kerja lama (sebelum v1.2):** Badges memanggil endpoint `/beasiswa/summary` yang mengembalikan total global seluruh database — tidak berubah meskipun filter aktif.

**Cara kerja baru (v1.2+):** Ketika `loadBudgetList()` atau `loadPaymentList()` dipanggil (termasuk saat filter/search berubah), response JSON dari list endpoint sudah menyertakan cross-tab aggregation:

- `GET /beasiswa/budget/list` → response kini menyertakan `payment_totals` dan `payment_grand` (aggregate payment untuk scope filter yang sama)
- `GET /beasiswa/payment/list` → response kini menyertakan `budget_totals` dan `budget_grand` (aggregate budget untuk scope filter yang sama)
- Fungsi JS `_renderTabSummary(prefix, bgtTotals, payTotals)` langsung mengisi badge dari response — tidak ada HTTP request tambahan

Dengan demikian, jika user memfilter "Bulan = Maret, Pillar = AGRI", badges menampilkan total Budget dan Payment hanya untuk data yang tampil di tabel.

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

### 7.8 Data Migrated (dari DbBeasiswa v2.2.xlsm)

| Sumber (Sheet Excel) | Tabel SQLite | Jumlah Record |
|---|---|---|
| `DbSiswa` | `siswa` | 1,269 siswa |
| `DbBudget` | `budget_beasiswa` | 3,859 baris |
| `DbPayment` | `payment_beasiswa` | 9,567 baris |
| **Total** | | **~14,700 record** |

---

## 8. Payment Approval Memo — Spesifikasi Detail

### 8.1 Fungsi Utama

Payment Approval Memo (PAM) adalah **hub agregasi pembayaran** yang mengumpulkan data payment dari semua sub-modul aktif dan mengkonsolidasikannya menjadi satu dokumen memo pengajuan pembayaran. Di sistem lama, ini dilakukan manual via sheet Excel `Detail PAM` dan `Rangkuman PAM`. Di Finance Hub, seluruh proses otomatis dari input payment hingga export memo.

### 8.2 Tab Payment Memo Page

| Tab | Fungsi |
|---|---|
| **Daftar PAM** | Tabel semua PAM records, isi/update GL Account per PAM via dropdown COA |
| **Draft Memo** | Cari PAM No, preview + inline edit memo, export PDF / Excel standar |
| **Days of PAM** | Monitoring 4 tanggal SLA per baris payment, bulk-update, filter + search |

### 8.3 Alur PAM End-to-End

```
1. User input payment di Beasiswa → klik "Simpan"
2. Service layer (atomic transaction):
   a. Simpan baris ke payment_beasiswa (status: draft)
   b. Auto-create PAM record di pam_records
      (nomor PAM dari field input, company_id, total amount, tanggal)
3. Tab "Daftar PAM":
   - PAM muncul di tabel dengan kolom: PAM No, Tanggal, Total, GL Account
   - User pilih GL Account dari dropdown COA
   - PATCH /pam/<id>/gl-account → update field gl_account
4. Tab "Draft Memo":
   - Cari PAM No via autocomplete
   - Form preview otomatis terisi: header (No PAM, tanggal, GL, Cost Center),
     tabel siswa (nama, bank, rekening, keterangan, amount)
   - User dapat edit inline: nama memo, catatan, jumlah
   - Lampiran: detail per siswa (collapsible) dengan sub-total per kategori
   - Klik "Export PDF" atau "Export Excel" → file terunduh
5. Tab "Days of PAM":
   - Search by PAM No atau Nama Siswa
   - Centang baris → Bulk update tanggal (Pengajuan/Receive/PA/Final)
```

### 8.4 PAM Records — Field

| Field | Keterangan |
|---|---|
| `pam_no` | Nomor PAM (format: `PAM-{seq}-{COMPANY}-{MM}-{YYYY}`) |
| `company_id` | FK ke companies |
| `tanggal` | Tanggal PAM |
| `total_amount` | Total nominal pembayaran |
| `gl_account` | Kode GL Account (dari tabel `coa`) |
| `created_at` | Timestamp pembuatan |

### 8.5 Chart of Accounts (COA)

Tabel `coa` berisi daftar kode akun GL yang digunakan untuk mengisi field `gl_account` pada PAM record. Data ini di-seed dari konstanta `COA_LIST` di `config.py`.

Contoh kode COA yang digunakan: `70110230` (Biaya Beasiswa Pendidikan), sesuai format yang sudah digunakan di sheet `Detail PAM` dan `Rangkuman PAM` pada file Excel lama.

### 8.6 Days of PAM (DOP) — Monitoring SLA

Tab **Days of PAM** menggantikan pengelolaan tanggal SLA yang sebelumnya dilakukan secara ad-hoc di kolom `Cat3–Cat7` sheet `DbPayment` Excel.

**Fitur:**

| Fitur | Detail |
|---|---|
| **Search-first** | Tabel tidak ditampilkan sampai user memasukkan kata kunci (PAM No atau Nama Siswa) — mencegah load ratusan baris sekaligus |
| **Lazy-load AJAX** | Data dimuat via `GET /payment-memo/dop/candidates?search=` — tidak ada data yang dikirim saat page load |
| **Inline filter** | Filter Bulan, Tahun, Status SLA di subheader row |
| **Checkbox + Bulk update** | Pilih baris → klik "Update Tanggal" → dialog isi 4 tanggal SLA sekaligus |
| **Status visual** | Tanggal terlambat ditandai merah / warna sesuai status |

### 8.7 Export Memo — Format Standar

#### PDF (reportlab)
- **Sheet 1: Rangkuman** — Header (No PAM, tanggal, GL, Cost Center), tabel penerima (No, Nama, Bank, No Rekening, Total), total keseluruhan, kolom tanda tangan
- **Sheet 2: Detail per siswa** — Rincian per baris payment (Nama, Kategori, Amount, SLA dates)

#### Excel (openpyxl, 2 sheet)
- **Sheet 1: Rangkuman PAM** — format identik dengan `Rangkuman PAM` di file Excel lama: header perusahaan, tabel nama–bank–rekening–total, total, kolom tanda tangan
- **Sheet 2: Detail PAM** — format identik dengan `Detail PAM` di file Excel lama: rincian per siswa per PAM No

Draft Memo juga mendukung **custom export** (POST `/payment-memo/export/pdf-custom` dan `/export/excel-custom`) di mana user menyuplai data yang sudah diedit inline — tanpa menyimpan perubahan ke database.

### 8.8 Status Payment Item

| Status | Keterangan |
|---|---|
| `draft` | Payment baru diinput di sub-modul, belum dimasukkan ke memo |
| `in_memo` | Sudah dimasukkan ke memo, menunggu approval |
| `approved` | Memo telah disetujui atasan |
| `paid` | Pembayaran telah dilakukan/dicairkan |

---

## 9. Data Architecture / Model Data

### 9.1 ERD Ringkas

```
companies (1) ──< siswa (N)
companies (1) ──< budget_beasiswa (N)
companies (1) ──< payment_beasiswa (N)
companies (1) ──< payment_memo (N)
companies (1) ──< pam_records (N)
payment_memo (1) ──< payment_memo_items (N)
payment_memo (1) ──< payment_application (N)
payment_beasiswa (N) >── payment_memo (1)
coa (N) ──< pam_records (N)   [via gl_account]
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
    pam            TEXT,            -- format: PAM-{seq}-{COMPANY}-{MM}-{YYYY}
    perusahaan     TEXT,
    cat3           TEXT,
    cat4           TEXT,
    tgl_pengajuan  TEXT,            -- SLA Date 1: tanggal pengajuan ke finance
    tgl_receive    TEXT,            -- SLA Date 2: tanggal finance menerima berkas
    tgl_pa         TEXT,            -- SLA Date 3: tanggal Payment Application terbit
    tgl_final      TEXT,            -- SLA Date 4: tanggal realisasi pembayaran
    memo_id        INTEGER REFERENCES payment_memo(id),
    status         TEXT DEFAULT 'draft',
    created_at     TEXT DEFAULT CURRENT_TIMESTAMP
);

-- PAM Records (auto-created saat add_payment_multi)
CREATE TABLE IF NOT EXISTS pam_records (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id   INTEGER NOT NULL REFERENCES companies(id),
    pam_no       TEXT NOT NULL,
    tanggal      TEXT,
    total_amount REAL DEFAULT 0,
    gl_account   TEXT,
    created_at   TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(company_id, pam_no)
);

-- Chart of Accounts
CREATE TABLE IF NOT EXISTS coa (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL REFERENCES companies(id),
    code       TEXT NOT NULL,
    name       TEXT,
    UNIQUE(company_id, code)
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
| GET | `/beasiswa/budget/list` | `search, cat1, pillar, bulan, tahun, program` | List budget + `payment_totals` + `payment_grand` |
| GET | `/beasiswa/payment/list` | `search, cat1, pillar, bulan, tahun, status, program` | List payment + `budget_totals` + `budget_grand` |
| POST | `/beasiswa/payment/tambah-multi` | — | Tambah payment multi-siswa + SLA dates + auto-create PAM record |
| GET | `/api/v1/siswa` | `search, status, program, company` | List siswa |
| GET | `/api/v1/siswa/<code>` | — | Detail 1 siswa |
| POST | `/api/v1/siswa` | — | Tambah siswa |
| PUT | `/api/v1/siswa/<code>` | — | Update siswa |
| GET | `/api/v1/budget` | `code, pillar, company` | List budget |
| POST | `/api/v1/budget` | — | Tambah budget |
| GET | `/api/v1/payment` | `code, pillar, status, company` | List payment |
| POST | `/api/v1/payment` | — | Tambah payment 1 siswa (legacy) |
| GET | `/api/v1/rekap` | `company, program, pillar, status` | Summary per siswa |
| GET | `/api/v1/rekap/export/csv` | (same) | Download CSV |
| GET | `/api/v1/rekap/export/pdf` | (same) | Download PDF |
| GET | `/api/v1/dashboard` | `company` | Angka agregat |

### 10.3 Payment Memo / PAM Endpoints

| Method | Path | Keterangan |
|---|---|---|
| GET | `/payment-memo/pam` | List semua PAM records per company |
| PATCH | `/payment-memo/pam/<id>/gl-account` | Update GL Account pada PAM record |
| GET | `/payment-memo/coa` | List Chart of Accounts |
| GET | `/payment-memo/pam/<pam_no>/detail` | Detail PAM + daftar payments |
| POST | `/payment-memo/export/pdf` | Export PDF memo standar |
| POST | `/payment-memo/export/excel` | Export Excel memo standar (2 sheet) |
| POST | `/payment-memo/export/pdf-custom` | Export PDF dari data yang sudah diedit inline |
| POST | `/payment-memo/export/excel-custom` | Export Excel dari data yang sudah diedit inline |
| GET | `/payment-memo/dop/candidates` | Search kandidat Days of PAM (lazy-load) |
| GET | `/payment-memo/dop/search` | Filter Days of PAM rows |
| POST | `/payment-memo/dop/bulk-update` | Bulk update 4 tanggal SLA |
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
- IDOR guards: setiap resource divalidasi kepemilikan `company_id` sebelum dikembalikan/dimodifikasi

---

## 12. Non-Functional Requirements / Batasan & Risiko

### 12.1 Performance

| Metrik | Target |
|---|---|
| Waktu load halaman | < 2 detik pada LAN |
| Response API | < 500ms untuk query normal |
| Days of PAM search | Lazy-load AJAX — tidak ada data dikirim saat page load |
| Concurrent users | 10–20 user (SQLite write lock per transaksi) |
| Ukuran database | Estimasi < 100MB untuk 5 tahun data |

### 12.2 Deployment & Availability

**Model: Centralized Server (Laptop)**

```
[Laptop Server — selalu nyala saat jam kerja]
  └── python run.py  (Flask + waitress)
  └── finance_hub.db (SQLite, lokal di laptop server)

[User lain] ──browser──→ http://[IP-laptop]:8080
```

- Flask dijalankan di laptop yang berperan sebagai server (terhubung ke WiFi/LAN kantor).
- Semua user lain cukup buka browser dan akses via IP laptop server.
- Laptop server **tidak boleh sleep/hibernate** saat jam kerja.
- Tidak ada SLA formal — downtime = restart Python/Flask.
- **Backup:** copy file `finance_hub.db` ke `Y:/` shared folder secara berkala (manual atau Windows Task Scheduler). `Y:/` digunakan sebagai backup destination, **bukan** sebagai lokasi database aktif.
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

### Fase 1 — Foundation + PAM Full Feature (v1.x) — ✅ COMPLETE

**Test coverage: 127/127 tests pass**

| Deliverable | Status | Catatan |
|---|---|---|
| Flask app structure | ✅ | Blueprint-based, modul terdaftar |
| SQLite init + migration | ✅ | `init_db()` + `migrate_db()` untuk ALTER TABLE backward-compatible |
| Auth (JWT) | ✅ | Login, logout, refresh, ganti password, first-login gate |
| Company Selector | ✅ | Landing page pilih SMT / ETF |
| Dashboard | ✅ | Widget: total siswa, total budget, total payment per company |
| **Modul Beasiswa — Data Siswa** | ✅ | CRUD + search 7 kolom + IPK sem 1–10 + IPK penelitian 1–3 + delete cascade |
| **Modul Beasiswa — Input Budget** | ✅ | Autocomplete siswa, batch input Cat1/Cat2/Amount, pillar per sesi |
| **Modul Beasiswa — Data Budget** | ✅ | Filter lengkap, dynamic summary badges (filter-aware), edit/hapus baris, export CSV/PDF |
| **Modul Beasiswa — Input Payment** | ✅ | Multi-siswa per submit, PAM auto-format, 4 SLA dates (TAT tracking), auto-create PAM record |
| **Modul Beasiswa — Data Payment** | ✅ | Filter lengkap, dynamic summary badges (filter-aware), export CSV/PDF |
| **Modul Beasiswa — Report Siswa** | ✅ | Detail per siswa + IPK + rekap + budget/payment detail, export CSV/PDF |
| **Data Migration Excel → SQLite** | ✅ | 1,269 siswa, 3,859 budget, 9,567 payment (~14,700 record) dari DbBeasiswa v2.2.xlsm |
| **PAM Records + GL Account** | ✅ | Auto-create PAM record saat input payment; update GL Account via COA dropdown |
| **PAM Draft Memo** | ✅ | Cari PAM, preview form, inline editing, collapsible Lampiran, export PDF+Excel |
| **PAM Custom Export** | ✅ | POST endpoint PDF+Excel dari data yang sudah diedit — ephemeral, tidak disimpan ke DB |
| **Days of PAM tab** | ✅ | Search-first lazy-load, inline filters, checkbox bulk-update 4 tanggal SLA |
| **Dynamic Summary Badges** | ✅ | `get_budget_list()` + `get_payment_list()` menyertakan cross-tab aggregation; `_renderTabSummary()` JS helper |
| Payment Approval Memo | ✅ | List draft payment, buat memo, update status, export PDF |
| Payment Application | ✅ | List memo, update actual payment date, hitung TAT |
| REST API (`/api/v1/`) | ✅ | Semua operasi Beasiswa + PAM tersedia via JSON API |
| Coming Soon pages | ✅ | Placeholder UI untuk modul Bank, AP, Advance, Pettycash, Sponsorship |
| Production server | ✅ | `run.py` via waitress, LAN IP display, startup validation |

### Fase 2 — AP & Tax Core / Masterplan F4 (v2.x)

Finance Hub akan mengimplementasikan inti dari **F4 AP, Tax & Payment** dalam masterplan:

| Deliverable | Masterplan F4 Mapping | Status |
|---|---|---|
| **Account Payable (SMT + ETF)** | Automated 3-Way Match (PO/GR/Invoice) | 🔜 |
| **Digital Invoice Submission Portal** | Digital Invoice Submission [MS Forms equiv.] | 🔜 |
| **Tax Auto-Calculation (PPh/PPN)** | Auto PPh/PPN per vendor NPWP & jenis transaksi | 🔜 |
| **Payment Disbursement** | Batch Payment File (.CSV Export) ke bank | 🔜 |
| **Integrasi PR Portal (F2)** | Receive PO approved dari PR Portal → trigger AP flow | 🔜 |
| **Advance** (SMT + ETF) | Uang muka karyawan/proyek | 🔜 |
| **Petty Cash** (SMT + ETF) | Kas kecil operasional | 🔜 |
| **Sponsorship** (SMT only) | Pengelolaan sponsorship | 🔜 |

### Fase 3 — Integration & Accounting Hub (v3.x)

Integrasi Finance Hub (F4) dengan sistem upstream/downstream dalam masterplan:

- **F2 → F4**: Auto-receive PO yang sudah Completed dari PR Portal sebagai trigger AP
- **F4 → F5**: Export journal entry ke Accounting Hub (Power Pivot / VBA) dalam format CSV/GL
- **Notifikasi in-app** saat memo baru dibuat atau invoice masuk
- **Dashboard charts** (Chart.js) — tren pembayaran per bulan, aging AP
- **Audit log lengkap** — siapa mengubah apa dan kapan
- **Multi-level approval** untuk PAM/AP (jika diperlukan)
- **Tax & e-Bupot Ready Export** — siap untuk pelaporan SPT via DJP Online
- Migrasi ke **PostgreSQL** jika concurrent user meningkat signifikan

---

*Document updated: 2026-06-01 | Finance Hub PRD v1.2 — Post Fase 1 full implementation*
