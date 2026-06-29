# Finance Hub — Product Requirements Document (PRD)

**Date / Tanggal:** 2026-06-19
**Version / Versi:** 1.4
**Status:** Updated — Before/After Methodology, PA→Beasiswa Integration, Pillar-based ETF (AGRI/APP/LAND/SETF), PAM Input Transaksi Types, ETF PA Summary Tab
**Author:** Generated via brainstorming session

**Changelog:**

| Versi | Tanggal | Perubahan |
|---|---|---|
| 1.0 | 2026-05-30 | Draft awal |
| 1.1 | 2026-05-30 | Update post-implementation: Beasiswa tabs, multi-student Input Payment, SLA tracking, Laporan Siswa, data migrasi Excel |
| 1.2 | 2026-06-01 | Tambah: PAM Records + GL Account, Draft Memo (inline editing + PDF/Excel custom export), Days of PAM tab (lazy-load AJAX), Dynamic Summary Badges (filter-aware); Perbandingan sistem Excel lama (DbBeasiswa v2.2.xlsm); test coverage 56 → 127 |
| 1.3 | 2026-06-10 | Tambah: ETF Payment Application (AGRI/APP/SML/SETF), PAM Input Integration (unified save panel), PA Picker sub-row, Editable PAM No. (format validation + collision check), PAM↔PA workflow fix, Status Standardization (open/on_process/complete), Global Confirmation Modal |
| 1.4 | 2026-06-19 | Tambah: Before/After methodology dua sistem (DbBeasiswa.xlsm + PA Excel → Finance Hub); Section 2.6 alur integrasi PA→Beasiswa (data sinkron dari sumber); PAM Input Transaksi Types (Beasiswa/Klaim Medis/Others); pillar-based PAM (AGRI/APP/LAND/SETF) ETF-first → SMT-next; ETF PA Summary tab; test coverage 127 → 222 |

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
9. [ETF Payment Application — Spesifikasi Detail](#9-etf-payment-application--spesifikasi-detail)
10. [Data Architecture / Model Data](#10-data-architecture--model-data)
11. [API Specification / Spesifikasi API](#11-api-specification--spesifikasi-api)
12. [Security & Access Control / Keamanan & Kontrol Akses](#12-security--access-control--keamanan--kontrol-akses)
13. [Non-Functional Requirements / Batasan & Risiko](#13-non-functional-requirements--batasan--risiko)
14. [Roadmap & Phasing / Peta Jalan](#14-roadmap--phasing--peta-jalan)

---

## 1. Executive Summary / Ringkasan Eksekutif

**Finance Hub** adalah sistem manajemen keuangan internal berbasis web untuk **Account Payable, Petty Cash, Beasiswa, dan proses pembayaran** yang dijalankan secara lokal (localhost/LAN). Sistem ini dirancang sebagai **platform multi-perusahaan** yang dapat menampung sub-modul finansial dari dua entitas: **Sinar Mas Tjipta** dan **Eka Tjipta Foundation**.

### Transformasi: Dari Excel ke Python

Finance Hub menggantikan **dua sistem Excel** yang sebelumnya berjalan terpisah dan tidak terhubung:

| Sistem Lama | Digantikan Oleh | Keterangan |
|---|---|---|
| **`DbBeasiswa v2.2.xlsm`** (Excel VBA Macro) | Modul Beasiswa + PAM | Database siswa, budget, payment, PAM — sebelumnya di shared folder `Y:/` |
| **PA Excel manual** (Microsoft Excel) | Modul ETF Payment Application | Tracking Payment Application per siswa — sebelumnya dikelola manual per tipe (AGRI/APP/LAND/SETF) |

Selain mendigitalisasi kedua sistem tersebut secara terpisah, Finance Hub juga **menghubungkan alur PA → Beasiswa** sehingga data Payment Application menjadi sumber tunggal yang sinkron ke Beasiswa dan PAM secara atomik. Penjelasan alur integrasi tersedia di [Bagian 2.6](#26-integrasi-pa--beasiswa--data-sinkron-dari-sumber).

Perbandingan lengkap sistem lama vs baru tersedia di [Bagian 2.5](#25-perbandingan-sistem-excel-lama-vs-finance-hub).

### Posisi dalam Masterplan Automasi PT Sinar Mas Tjipta

Finance Hub adalah implementasi **Fase 4 (F4) — AP, Tax & Payment** dari *Master Plan Automasi Finance & Office Management* PT Sinar Mas Tjipta. Sistem ini bekerja dalam ekosistem yang lebih besar bersama **PR Portal (F2)** sebagai sistem hulu dan **Accounting Hub (F5)** sebagai sistem hilir.

| Fase | Sistem | Status |
|---|---|---|
| **F1** — Budget & Master Data | Google Sheets / SQL | Ongoing |
| **F2** — Purchasing (Web Portal) | **PR Portal** (Google Apps Script) | Ongoing |
| **F3** — Receiving & Asset Capture | SharePoint / Microsoft Lists | TBA |
| **F4** — AP, Tax & Payment | **Finance Hub** ← *Sistem ini* | Implemented (Beasiswa + PAM + ETF PA) / Coming Soon (AP & Tax) |
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
| Test Coverage | 222 automated tests (pytest) — 221 pass, 1 fail |
| Status Model | `open → on_process → complete` (semua modul payment) |

---

## 2. Problem Statement / Latar Belakang & Tujuan

### 2.1 Masalah Sebelumnya

Sebelum Finance Hub, dua proses keuangan utama dikelola secara terpisah dengan Microsoft Excel, masing-masing dengan masalahnya sendiri:

#### Sistem A — Beasiswa (`DbBeasiswa v2.2.xlsm`)

File Excel VBA Macro yang tersimpan di shared folder lokal (`Y:/`):

- File Excel dibuka bersama-sama → **file lock conflict** ketika lebih dari satu orang membuka file secara bersamaan.
- **Tidak ada autentikasi** — siapapun yang bisa akses `Y:/` dapat membuka, mengubah, bahkan menghapus data.
- **Tidak ada audit trail** — tidak diketahui siapa yang mengubah data dan kapan.
- Pembuatan **Payment Approval Memo** dilakukan manual dengan mengisi sheet `Detail PAM` dan `Rangkuman PAM`, lalu mencetak.
- **PAM Recon** menggunakan PivotTable Excel yang harus di-refresh manual setiap kali ada perubahan data.
- **Days of PAM** (4 tanggal SLA: Pengajuan, Receive, PA, Final) dicatat sebagai kolom Cat3–Cat7 di sheet `DbPayment`, tidak ada validasi format tanggal.
- Data **Medical/Hospital** (`DbHospital`) dikelola dalam sheet terpisah yang tidak terintegrasi otomatis dengan rekap kategori.
- Data Sinar Mas Tjipta dan Eka Tjipta Foundation **tidak terpisah secara sistematis**.

#### Sistem B — Payment Application (Excel Manual)

Payment Application (PA) beasiswa ETF dikelola secara manual di Microsoft Excel:

- Tidak ada sistem tracking per tipe PA (AGRI/APP/LAND/SETF) — semuanya dicampur atau dipisahkan manual per file.
- **7 SLA dates** per PA (doc received, PA from educ, checked by fincon, approved, send back, received by fin, approval final) dicatat ad-hoc, tidak terstruktur.
- **Tidak ada link otomatis ke PAM number** — nomor PAM diisi manual setelah PA diproses, rawan salah dan inkonsisten.
- **Tidak ada status tracking** — sulit mengetahui PA mana yang masih open, on_process, atau complete.
- **Data tidak terhubung ke Beasiswa** — saat PA diproses dan dibayar, data pembayaran di Beasiswa harus diinput ulang secara manual (duplikasi entri, rawan desync).
- **Tidak ada summary/agregasi** — rekap per tipe, per periode, atau per pillar harus dibuat manual.

#### Masalah Lintas Sistem

Karena kedua sistem berjalan terpisah, muncul masalah tambahan:
- Input pembayaran **harus dilakukan dua kali**: sekali di PA Excel, sekali lagi di DbBeasiswa — sumber kebenaran tidak jelas.
- **Tidak ada PAM yang otomatis terbentuk** dari PA — staf harus membuat PAM di DbBeasiswa secara manual setelah PA dibuat.
- Rekonsiliasi antara PA Excel dan DbBeasiswa harus dilakukan manual secara berkala.

### 2.2 Solusi

Finance Hub menyediakan:

1. **Portal terpusat** — semua transaksi finansial diinput dan dikelola via web app.
2. **Multi-company support** — data SMT dan ETF terisolasi secara penuh di database.
3. **Auth berbasis JWT** — hanya user yang login yang dapat mengakses sistem.
4. **Payment Approval Memo otomatis** — rekap pembayaran dari semua sub-modul dikumpulkan, diajukan, dan dimonitor dalam satu tempat.
5. **Draft Memo dengan inline editing** — memo dapat diedit langsung di browser sebelum diekspor ke PDF/Excel.
6. **Days of PAM tracking** — 4 tanggal SLA diinput langsung saat entry payment, dapat diperbarui bulk via tab khusus.
7. **Dynamic summary badges** — kartu ringkasan Budget/Payment/Selisih di tab Data Budget dan Data Payment secara otomatis mencerminkan filter aktif (bukan lagi data global).
8. **ETF Payment Application (AGRI/APP/SML/SETF)** — modul khusus untuk mencatat, tracking, dan mengeksekusi Payment Application beasiswa ETF dengan 7 SLA dates per PA dan 4 tipe PAM.
9. **PAM Input Integration** — Input panel terpadu di Payment Memo yang langsung membaca PA open (AGRI/APP/SML/SETF), menghasilkan PAM number otomatis, dan mengupdate status PA secara atomik.
10. **REST API** — Finance Hub siap diintegrasikan ke platform induk manapun via JSON API.
11. **Export PDF & Excel** — laporan dapat diunduh dalam format standar yang sudah disesuaikan dengan format memo perusahaan.
12. **Confirmation Modal** — semua aksi simpan/update/hapus memerlukan konfirmasi user via modal kustom (bukan native browser confirm).

### 2.3 Tujuan Sistem

| Tujuan | Indikator Keberhasilan |
|---|---|
| Digitalisasi data keuangan | 100% input via web, tidak ada Excel manual |
| Isolasi data antar perusahaan | Query apapun selalu difilter per `company_id` |
| Kontrol akses | Tidak ada halaman yang dapat diakses tanpa login |
| Payment approval terkonsolidasi | Semua pembayaran dari semua modul masuk ke Payment Approval Memo |
| ETF PA tracking otomatis | 7 SLA dates per PA tercatat; PAM number auto-generate saat status → on_process |
| Status konsisten | Satu model status untuk semua tabel payment: open → on_process → complete |
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
- Export PDF/Excel untuk halaman ETF Payment Application (fase berikutnya).
- Edit siswa/lines setelah PA dibuat (integritas data).
- Filter/search lanjutan di halaman daftar PA ETF.

---

### 2.5 Perbandingan Sistem Excel Lama vs Finance Hub

Bagian ini menjelaskan cara kerja **dua sistem Excel lama** yang digantikan Finance Hub: (A) `DbBeasiswa v2.2.xlsm` untuk manajemen Beasiswa+PAM, dan (B) PA Excel manual untuk tracking Payment Application.

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
| **ETF PA tidak terstruktur** | Tidak ada tracking PA dengan 7 SLA dates, tidak ada link ke PAM | Modul ETF Payment Application dengan tabel terpisah per tipe |
| **Aksi tanpa konfirmasi** | Simpan/hapus langsung tanpa konfirmasi | Global `confirmModal()` di semua aksi kritis |

#### 2.5.3 Sistem Lama B — PA Excel (Payment Application Manual)

Sebelum Finance Hub, tracking Payment Application dilakukan manual di Microsoft Excel per tipe PA:

| Aspek | Sistem PA Excel | Finance Hub |
|---|---|---|
| **Struktur** | File atau sheet terpisah per tipe (AGRI/APP/LAND/SETF) | Modul ETF Payment Application, 4 tab terpadu |
| **7 SLA dates** | Kolom manual, tidak ada validasi | Field terstruktur per PA header, bulk-update tersedia |
| **Nomor PAM** | Diisi manual, rawan typo/duplikat | Auto-generate saat status → `on_process`; collision check |
| **Status** | Tidak ada / warna cell manual | `open` → `on_process` → `complete` per PA |
| **Link ke Beasiswa** | Tidak ada — harus input ulang di DbBeasiswa | Atomik via `save_pa_payment()` — PA sinkron ke Beasiswa + PAM |
| **Summary per pillar** | Manual PivotTable | Tab AGRI/APP/LAND/SETF + Summary tab dengan `pa_summary` view |
| **Multi-siswa per PA** | Baris manual di sheet | Header + lines model; expand detail siswa inline |
| **Concurrent access** | File lock | Multi-user web app, tidak ada konflik |

#### 2.5.4 Fitur Baru yang Tidak Ada di Sistem Lama

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
| **Automated tests** | 222 pytest tests untuk menjamin kebenaran bisnis logic |
| **ETF Payment Application** | Tracking 4 tipe PA (AGRI/APP/LAND/SETF) dengan 7 SLA dates; auto-link ke PAM number |
| **PAM Input Integration** | Input panel terpadu di Payment Memo untuk semua tipe PA; save atomik ke payment_beasiswa + pam_records + PA update |
| **PA Picker sub-row** | Disambiguation UI saat satu siswa punya >1 PA dengan kategori yang sama |
| **Editable PAM No.** | Override manual PAM number dengan validasi format regex dan collision check real-time |
| **Status standardization** | Satu model status konsisten: `open → on_process → complete` di semua tabel payment |
| **Global confirmation modal** | Modal konfirmasi kustom (promise-based) menggantikan native `window.confirm()` di semua aksi |
| **PAM Input Transaksi Types** | Panel Beasiswa / Klaim Medis (multi-row + CAT3 medical) / Others (tagihan/ETF/sponsor) |
| **ETF PA Summary tab** | `pa_summary` SQL view per tab + filter Tahun PA / Bulan PA / Nama / Status |
| **Pillar-based PAM** | PAM terorganisir per pillar (AGRI/APP/LAND/SETF); sort by jenjang studi |

---

### 2.6 Integrasi PA → Beasiswa — Data Sinkron dari Sumber

Salah satu terobosan utama Finance Hub v1.x adalah **menghubungkan Payment Application dengan Beasiswa** sehingga satu tindakan di PA secara otomatis menciptakan record di Beasiswa dan PAM tanpa input ulang.

#### Before (Dua Sistem Terpisah)

```
[PA Excel]                    [DbBeasiswa.xlsm]
Buat PA → catat 7 SLA dates   ←← (manual duplikasi)
Ubah status manual             Input payment ULANG per siswa
Tulis nomor PAM manual         Buat PAM ULANG di sheet Detail PAM
                               ↑↑ Dua sumber, rawan desync ↑↑
```

#### After (Finance Hub — Terintegrasi)

```
[ETF Payment Application]
Buat PA (AGRI / APP / LAND / SETF)
    └── status: open, 7 SLA dates tercatat

User proses lewat "Input PA" di Payment Memo
    └── Pilih tipe → sistem tampilkan hanya siswa dengan open PA tipe tersebut

"Simpan PAM" → satu klik, atomik:
    ├── INSERT pam_records          → PAM terbentuk otomatis
    ├── INSERT payment_beasiswa     → data Beasiswa terbentuk dari PA (tidak input ulang)
    └── UPDATE {type}_pa            → status → on_process, nomor_pam terisi otomatis

[Beasiswa + PAM]
    └── Data langsung sinkron — sumber tunggal dari PA
```

#### Alur Detail: PA sebagai Sumber Kebenaran

| Langkah | Sistem Lama | Finance Hub |
|---|---|---|
| Buat Payment Application | Isi form Excel, simpan ke sheet | Buat PA via web, tersimpan ke DB dengan 7 SLA dates |
| Proses pembayaran | Input ulang ke DbBeasiswa | Pilih dari PA open di panel Input PA |
| Buat PAM number | Tulis manual di DbBeasiswa | Auto-generate dari sequence + tipe |
| Sinkronisasi data | Manual, rawan desync | Atomik dalam satu transaksi DB |
| Status PA | Tidak ada / manual | `open` → `on_process` → `complete` auto-update |
| Rekap per pillar | Manual PivotTable | Pillar-based tabs (AGRI/APP/LAND/SETF), filter otomatis |

#### PA→PAM Cascade Flow

```
save_pa_payment() — fungsi service, dipanggil dari POST /payment-memo/ipay/save-pa

BEGIN TRANSACTION
  INSERT INTO pam_records (pam_no, source, total, ...)     → PAM terbentuk
  INSERT INTO payment_beasiswa (per siswa, status='open')  → Beasiswa terbentuk
  UPDATE {type}_pa SET
    nomor_pam = pam_no,
    status    = 'on_process'                                → PA terupdate
COMMIT

Jika ROLLBACK → tidak ada record parsial, semua batal bersama.
```

#### Implikasi untuk SMT (Sinar Mas Tjipta)

Saat ini integrasi PA→Beasiswa sudah berjalan untuk **Eka Tjipta Foundation** dengan 4 pillar: AGRI, APP, LAND, SETF.

**Roadmap:** Begitu integrasi ETF stabil, model yang sama akan direplikasi untuk **Sinar Mas Tjipta** — dengan pillar dan tipe PA yang sesuai dengan struktur SMT. Data tetap terisolasi per `company_id`.

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
| Release / mark as Complete | ❌ | ❌ | ✅ |
| Export PDF memo | ❌ | ✅ | ✅ |
| **Payment Application** | | | |
| Lihat monitoring status | ✅ | ✅ | ✅ |
| Update actual payment date | ❌ | ❌ | ✅ |
| **ETF Payment Application** | | | |
| Lihat daftar PA (AGRI/APP/SML/SETF) | ✅ | ✅ | ✅ |
| Buat PA baru | ✅ | ✅ | ✅ |
| Update SLA dates + status PA | ✅ | ✅ | ✅ |
| Bulk update SLA dates | ✅ | ✅ | ✅ |
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
          ★ Aksi update & hapus memerlukan konfirmasi via confirmModal

    → Tab: Input Budget
        → Pilih siswa via autocomplete
        → Isi: Tanggal, Pillar, batch item (Cat1 / Cat2 / Amount)
        → "+ Baris" untuk tambah item
        → Simpan → konfirmasi modal → tabel budget per siswa muncul

    → Tab: Data Budget
        → Filter: Kata Kunci / Kategori 1 / Pillar / Bulan / Tahun / Program
        → Summary badges (Pendidikan/Tunjangan/Penelitian/Medical/Total)
          ★ Badges mencerminkan filter aktif — bukan total global
        → Edit / Hapus baris individual (hapus: danger modal)
        → Export CSV | Export PDF

    → Tab: Input Payment
        → Isi header: Tanggal, PAM (auto-format PAM-XXX-ETF-MM-YYYY), Pillar, Perusahaan
        → "+ Tambah Baris" untuk setiap siswa yang dibayar:
            → Cari siswa via autocomplete
            → Pilih Kategori 1, Kategori 2, isi Amount
            → Isi 4 tanggal SLA (opsional): Tgl Pengajuan, Tgl Receive, Tgl PA, Tgl Final
        → "Simpan Payment" → konfirmasi modal → semua baris tersimpan dengan status "open"
          ★ PAM record otomatis dibuat di tabel pam_records

    → Tab: Data Payment
        → Summary badges per kategori: Budget / Payment / Selisih
          ★ Badges mencerminkan filter aktif — bukan total global
        → Filter: Kata Kunci / Kategori 1 / Pillar / Bulan / Tahun / Program / Status
        → Hapus baris (status open saja, danger modal)
        → Export CSV | Export PDF

    → Tab: Report Siswa
        → Pilih siswa via autocomplete
        → Tampilkan: data lengkap siswa, IPK, rekap per kategori
        → Detail tabel budget + detail tabel payment
        → Export CSV | Export PDF
```

### 4.3 Alur ETF Payment Application (AGRI/APP/SML/SETF)

```
Dashboard ETF
    → Menu: ETF Payment Application
    → Pilih tab: [AGRI] | [APP] | [SML] | [SETF]
    → Daftar PA tipe terpilih (satu baris = satu PA header)
        → Kolom: PA Number, Jml Siswa, Total, 7 SLA dates, Nomor PAM, Tgl Bayar, Status
        → Badge status: Open (abu) / On Process (kuning) / Complete (hijau)
        → Klik baris → expand detail siswa di bawahnya

    → Buat PA Baru (tombol "+ Buat PA Baru")
        → Isi header: Tgl Payment Application, Tgl Surat Pengajuan, Keterangan
        → "+ Tambah Baris" per siswa:
            → Autocomplete nama siswa
            → Auto-fill: Status, Instansi, Jenjang, Program, IPK
            → Pilih Jenis Pembayaran (Cat1), Semester (Cat2), Tahun Ajaran
            → Input Jumlah Pembayaran
        → Simpan PA (status default: open) → konfirmasi modal

    → Edit PA (tombol Edit per baris)
        → Modal edit: update 7 SLA dates, Nomor PAM, Tgl Bayar, Keterangan, Status
        → Saat status → on_process dan nomor_pam kosong → auto-generate PAM number
        → Simpan → konfirmasi modal

    → Bulk Update SLA (pilih checkbox baris → isi field → klik Update)
        → Semua baris terpilih diupdate dengan tanggal yang sama
        → Konfirmasi modal sebelum dieksekusi
```

### 4.4 Alur PAM Input Integration (dari ETF PA ke Payment Memo)

```
Dashboard [ETF]
    → Menu: Payment Approval Memo
    → Tab: Input PA

    → Pilih Tipe PAM: [AGRI ▾] | [APP] | [SML] | [SETF]
    → No. PAM: auto-generate readonly (PAM-054-AGRI-06-2026)
      ★ User dapat override manual → format regex divalidasi real-time
      ★ Saat blur → collision check ke /payment-memo/pam/check
    → Tanggal, Perusahaan, Catatan Payment
    → Pillar: auto-readonly sesuai tipe

    → "+ Tambah Baris":
        → Cari siswa via autocomplete (hanya siswa dengan open PA tipe terpilih)
        → Setelah Cat1 + Cat2 dipilih:
          - 1 PA match → auto-fill Amount, SLA dates
          - 2+ PA match → PA Picker sub-row muncul (mini-table: No PA | Amount)
            → User klik PA → auto-fill → sub-row hilang

    → "Simpan PAM {TYPE}" → konfirmasi modal
      Backend (atomik):
        1. INSERT pam_records (source='etf_{tab}', keterangan)
        2. INSERT payment_beasiswa (per baris, status='open')
        3. UPDATE {tab}_pa SET nomor_pam=?, status='on_process'
```

### 4.5 Alur Payment Approval Memo (PAM)

```
Dashboard [SMT | ETF]
    → Menu: Payment Approval Memo
    → Tab: Daftar PAM
        → Lihat semua PAM records (auto-created saat Input Payment)
        → Filter source (Semua Tipe / AGRI / APP / SML / SETF)
        → Isi / update GL Account per PAM via dropdown COA
        → Kolom "Catatan Payment" dari pam_records.keterangan
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
        → Pilih baris via checkbox → Bulk update tanggal SLA → konfirmasi modal
        → Tampilkan status keterlambatan per tahap
```

### 4.6 Alur Ganti Perusahaan

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
├── run.py                          ← waitress production server entry point
├── config.py                       ← DB_PATH, JWT_SECRET, company list, constants, COA_LIST
├── database.py                     ← init SQLite, CREATE TABLE IF NOT EXISTS, seed COA
├── app/
│   ├── __init__.py                 ← Flask app factory, register blueprints
│   ├── migrate_status.py           ← one-time migration: draft/approved/paid → open/on_process/complete
│   └── modules/
│       ├── beasiswa/
│       │   ├── routes.py           ← HTML + JSON routes: /beasiswa/*, /beasiswa/payment/tambah-multi
│       │   ├── api.py              ← REST API: /api/v1/beasiswa/*
│       │   └── service.py          ← business logic (siswa CRUD, budget, payment, rekap, DOP, PAM)
│       ├── payment_memo/
│       │   ├── routes.py           ← HTML routes: /payment-memo, PAM records, Draft Memo, DOP, ipay/*
│       │   ├── api.py              ← REST API: /api/v1/payment-memo/*
│       │   ├── service.py          ← aggregate dari semua modul, PAM generation, GL account, save_pa_payment
│       │   └── exports.py          ← export_pam_pdf(), export_pam_excel(), custom variants
│       ├── payment_application/
│       │   ├── routes.py           ← HTML routes: /payment-application
│       │   └── service.py
│       ├── etf_payment_application/
│       │   ├── routes.py           ← HTML routes: /etf-payment-application (AGRI/APP/SML/SETF)
│       │   ├── service.py          ← PA CRUD, get_draft_siswa, get_draft_lines, _TAB_CFG
│       │   └── api.py              ← REST API: /api/v1/etf-payment-application/*
│       └── [coming_soon]/          ← bank, account_payable, advance, pettycash, sponsorship
├── templates/
│   ├── base.html                   ← layout utama (navbar, company switcher, confirmModal utility)
│   ├── login.html
│   ├── company_select.html
│   ├── dashboard.html              ← dashboard per perusahaan
│   ├── beasiswa/
│   │   └── index.html              ← tabs: Data Siswa / Input Budget / Data Budget /
│   │                                           Input Payment / Data Payment / Report Siswa
│   ├── payment_memo/
│   │   └── index.html              ← tabs: Daftar PAM / Draft Memo / Days of PAM / Input PA
│   ├── payment_application/
│   │   └── index.html
│   └── etf_payment_application/
│       └── index.html              ← tabs: AGRI / APP / SML / SETF
├── static/
│   ├── css/style.css               ← termasuk .btn-danger, .modal-overlay, .modal-box
│   └── js/app.js
├── tests/
│   ├── conftest.py                 ← pytest fixtures, test DB setup
│   ├── test_beasiswa_service.py
│   ├── test_beasiswa_api.py
│   ├── test_pam_service.py
│   ├── test_pam_exports.py
│   ├── test_payment_memo_service.py
│   ├── test_pam_pa_cascade.py      ← ETF PA → PAM cascade tests
│   ├── test_payment_memo_ipay.py   ← Input PA integration tests
│   ├── test_users_service.py
│   ├── test_auth.py
│   ├── test_dashboard.py
│   └── test_database.py
└── finance_hub.db                  ← SQLite, auto-created saat pertama run
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

### 5.3 confirmModal — Global Confirmation Utility

Semua aksi **simpan / update / hapus** di seluruh modul menggunakan fungsi `confirmModal()` yang didefinisikan di `base.html` dan tersedia global di setiap halaman.

```javascript
// Signature
confirmModal(message, opts) → Promise<boolean>

// opts fields
{
  type: 'primary' | 'danger',   // primary = biru, danger = merah
  title: string,                 // judul modal (default: "Konfirmasi" / "Konfirmasi Hapus")
  confirmText: string,           // label tombol OK (default: "Simpan" / "Hapus")
  cancelText: string             // label tombol batal (default: "Batal")
}

// Penggunaan
if (!await confirmModal("Simpan data ini?")) return;
if (!await confirmModal("Hapus data ini permanen?", { type: 'danger', confirmText: 'Hapus' })) return;
```

Modal menggunakan class CSS yang sudah ada (`.modal-overlay`, `.modal-box`, `.btn-primary`, `.btn-danger`). Tidak ada dependency library eksternal.

### 5.4 Status Model — Standar Semua Modul

Sejak v1.3, semua tabel payment menggunakan satu model status yang konsisten:

```
open  →  on_process  →  complete
```

| Status | Makna | Tabel yang Menggunakan |
|---|---|---|
| `open` | Baru dibuat, belum diproses | payment_beasiswa, payment_memo, pam_records, payment_application, etf_pa, app_pa, sml_pa, setf_pa |
| `on_process` | Terlampir ke memo/PA, sedang diproses | (sama) |
| `complete` | Dibayar / selesai | (sama) |

Migration script `app/migrate_status.py` melakukan konversi satu kali: `draft→open`, `in_memo/approved→on_process`, `paid/completed/completed→complete`.

### 5.5 Dependencies (requirements.txt)

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
| Payment Approval Memo | ✅ Implemented | PAM Records, Draft Memo, Days of PAM, GL Account, Input PA (multi-type), PDF/Excel export |
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
| Payment Approval Memo | ✅ Implemented | PAM Records, Draft Memo, Days of PAM, GL Account, Input PA (AGRI/APP/SML/SETF), PDF/Excel export |
| Payment Application | ✅ Implemented | Monitoring status pengajuan & TAT |
| ETF Payment Application | ✅ Implemented | Tracking PA per tipe (AGRI/APP/SML/SETF) dengan 7 SLA dates; auto-link ke PAM |

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
| Status | `open` → `on_process` → `complete` |

### 7.5 Input Payment — Multi-Student Flow

Tab **Input Payment** menggantikan keterbatasan form lama (satu siswa per submit). Alur baru:

```
1. User isi header: Tanggal, PAM (urutan + auto-suffix COMPANY-MM-YYYY), Pillar, Perusahaan
2. Klik "+ Tambah Baris":
   - Input siswa: autocomplete dari daftar siswa aktif
   - Pilih Kategori 1 → Kategori 2 → input Amount
   - Isi 4 tanggal SLA (semua opsional, bisa diisi bertahap)
3. Ulangi untuk setiap siswa yang akan dibayar
4. Klik "Simpan" → confirmModal → semua baris tersimpan ke payment_beasiswa dengan status "open"
5. PAM record otomatis dibuat di tabel pam_records (atomic transaction)
```

Satu submit = banyak siswa, satu PAM, satu batch SLA tracking.

### 7.6 Dynamic Summary Badges

Tab **Data Budget** dan **Data Payment** menampilkan kartu ringkasan per kategori (Pendidikan, Tunjangan, Penelitian, Medical, Total) dengan 3 nilai: **Budget**, **Payment**, **Selisih**.

Ketika `loadBudgetList()` atau `loadPaymentList()` dipanggil (termasuk saat filter/search berubah), response JSON dari list endpoint menyertakan cross-tab aggregation:

- `GET /beasiswa/budget/list` → response menyertakan `payment_totals` dan `payment_grand`
- `GET /beasiswa/payment/list` → response menyertakan `budget_totals` dan `budget_grand`
- Fungsi JS `_renderTabSummary(prefix, bgtTotals, payTotals)` langsung mengisi badge dari response — tidak ada HTTP request tambahan

Dengan demikian, jika user memfilter "Bulan = Maret, Pillar = AGRI", badges menampilkan total hanya untuk data yang tampil di tabel.

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
| **Daftar PAM** | Tabel semua PAM records, filter per tipe (AGRI/APP/SML/SETF), isi/update GL Account + Catatan Payment |
| **Draft Memo** | Cari PAM No, preview + inline edit memo, export PDF / Excel standar |
| **Days of PAM** | Monitoring 4 tanggal SLA per baris payment, bulk-update (dengan konfirmasi), filter + search |
| **Input PA** | Panel input terpadu untuk AGRI/APP/SML/SETF: pilih tipe → siswa → PA lines → simpan atomik |

### 8.3 Alur PAM End-to-End

```
1. Jalur A — Via Input Payment Beasiswa (tab Beasiswa):
   a. User input payment di Beasiswa → klik "Simpan" → confirmModal
   b. Service layer (atomik):
      - Simpan baris ke payment_beasiswa (status: open)
      - Auto-create PAM record di pam_records
      - Update nomor_pam ke etf_pa/app_pa/sml_pa yang terhubung
   c. PAM muncul di tab "Daftar PAM"

2. Jalur B — Via Input PA (tab Payment Memo → Input PA):
   a. User pilih Tipe PAM (AGRI/APP/SML/SETF)
   b. No. PAM auto-generate → user dapat override manual (validasi format + collision check)
   c. User tambah baris siswa (hanya siswa dengan open PA tipe terpilih)
   d. Saat Cat1+Cat2 dipilih dan >1 PA cocok → PA Picker sub-row muncul untuk disambiguasi
   e. "Simpan PAM {TYPE}" → confirmModal
   f. Backend (atomik):
      - INSERT pam_records (source='etf_{tab}', keterangan)
      - INSERT payment_beasiswa (per baris, status='open')
      - UPDATE {tab}_pa SET nomor_pam=?, status='on_process'

3. Tab "Daftar PAM":
   - PAM muncul di tabel; filter source untuk lihat per tipe
   - User pilih GL Account dari dropdown COA
   - Kolom "Catatan Payment" menampilkan pam_records.keterangan

4. Tab "Draft Memo":
   - Cari PAM No via autocomplete
   - Form preview otomatis terisi: header (No PAM, tanggal, GL, Cost Center),
     tabel siswa (nama, bank, rekening, keterangan, amount)
   - User dapat edit inline; lampiran collapsible per siswa
   - Klik "Export PDF" atau "Export Excel" → file terunduh

5. Status progression:
   open → (masuk ke memo) → on_process → (dibayar) → complete
```

### 8.4 PAM Records — Field

| Field | Keterangan |
|---|---|
| `pam_no` | Nomor PAM (format: `PAM-{seq}-{COMPANY}-{MM}-{YYYY}`) |
| `company_id` | FK ke companies |
| `tanggal` | Tanggal PAM |
| `total_amount` | Total nominal pembayaran |
| `gl_account` | Kode GL Account (dari tabel `coa`) |
| `source` | Sumber PAM: `etf_agri`, `etf_app`, `etf_sml`, `etf_setf`, atau null (beasiswa langsung) |
| `keterangan` | Catatan payment bebas |
| `status` | `open` → `on_process` → `complete` |
| `created_at` | Timestamp pembuatan |

### 8.5 Editable PAM Number

Field No. PAM di panel Input PA mendukung:

| State | Perilaku |
|---|---|
| **Auto (default)** | Readonly; diisi otomatis saat tipe/tanggal berubah; border biru |
| **Manual (mengetik)** | Badge `(manual)` muncul; border oranye |
| **Format error** | Border merah; hint teks "Format: PAM-054-AGRI-06-2026"; tombol Simpan disabled |
| **Collision (sudah ada)** | Border merah; hint "PAM ini sudah terdaftar"; tombol Simpan disabled |
| **Valid (checked OK)** | Border hijau; tombol Simpan aktif |

Collision check: `GET /payment-memo/pam/check?pam_no=<value>` dipanggil saat `blur` dari field.

### 8.6 PA Picker Sub-Row

Saat user memilih Cat1 + Cat2 di panel Input PA dan terdapat **lebih dari 1 PA** yang cocok (student + cat1 + cat2), sistem menampilkan sub-row picker:

```
[baris siswa utama]
  └── [sub-row picker] ← <tr colspan="10">
        No PA          | Amount (Rp)
        PA/ETF/001/2025  | Rp 5.000.000   ← klik → auto-fill + hapus sub-row
        PA/ETF/004/2025  | Rp 6.500.000   ← klik → auto-fill + hapus sub-row
```

Sub-row dihapus otomatis saat user mengubah Cat1 atau menghapus baris siswa.

### 8.7 Chart of Accounts (COA)

Tabel `coa` berisi daftar kode akun GL yang digunakan untuk mengisi field `gl_account` pada PAM record. Data ini di-seed dari konstanta `COA_LIST` di `config.py`.

### 8.8 Days of PAM (DOP) — Monitoring SLA

Tab **Days of PAM** menggantikan pengelolaan tanggal SLA yang sebelumnya dilakukan secara ad-hoc di kolom `Cat3–Cat7` sheet `DbPayment` Excel.

| Fitur | Detail |
|---|---|
| **Search-first** | Tabel tidak ditampilkan sampai user memasukkan kata kunci |
| **Lazy-load AJAX** | Data dimuat via `GET /payment-memo/dop/candidates?search=` |
| **Inline filter** | Filter Bulan, Tahun, Status SLA di subheader row |
| **Checkbox + Bulk update** | Pilih baris → dialog isi 4 tanggal SLA → confirmModal sebelum eksekusi |
| **Status visual** | Tanggal terlambat ditandai merah |

### 8.9 Export Memo — Format Standar

#### PDF (reportlab)
- **Sheet 1: Rangkuman** — Header (No PAM, tanggal, GL, Cost Center), tabel penerima, total, kolom tanda tangan
- **Sheet 2: Detail per siswa** — Rincian per baris payment (Nama, Kategori, Amount, SLA dates)

#### Excel (openpyxl, 2 sheet)
- **Sheet 1: Rangkuman PAM** — Format identik `Rangkuman PAM` file Excel lama
- **Sheet 2: Detail PAM** — Format identik `Detail PAM` file Excel lama

Draft Memo juga mendukung **custom export** (POST `…/export/pdf-custom` dan `…/export/excel-custom`) di mana user menyuplai data yang sudah diedit inline — tanpa menyimpan perubahan ke database.

### 8.10 Status Payment Item

| Status | Keterangan |
|---|---|
| `open` | Payment baru diinput, belum dimasukkan ke memo |
| `on_process` | Sudah dimasukkan ke memo / PA sedang diproses |
| `complete` | Pembayaran telah dilakukan/dicairkan |

---

## 9. ETF Payment Application — Spesifikasi Detail

### 9.1 Overview

Modul **ETF Payment Application** mencatat, melacak, dan memonitor pengajuan pembayaran beasiswa Eka Tjipta Foundation per tipe PA. Berbeda dari modul `payment_application` (berbasis per-memo), modul ini:

- Mendukung **4 tipe PA**: AGRI, APP, SML, SETF — masing-masing dengan tabel DB sendiri
- Satu PA mencakup **beberapa siswa sekaligus** (header + lines)
- Tracking **7 SLA dates** per PA header
- Integrasi langsung ke PAM: `save_pa_payment()` di service membuat pam_records + payment_beasiswa atomik dan mengupdate status PA ke `on_process`

### 9.2 Tipe PA & Tabel yang Digunakan

| Tipe | Tabel Header | Tabel Lines | Prefix PAM |
|---|---|---|---|
| AGRI | `etf_pa` | `etf_pa_lines` | ETF |
| APP | `app_pa` | `app_pa_lines` | APP |
| SML | `sml_pa` | `sml_pa_lines` | SML |
| SETF | `setf_pa` | `setf_pa_lines` | SETF |

Semua tabel identik secara schema. Routing ke tabel yang benar dilakukan via `_TAB_CFG` di `etf_payment_application/service.py`:

```python
_TAB_CFG = {
    "agri":  ("etf_pa",  "etf_pa_lines",  "ETF",  "ETF"),
    "app":   ("app_pa",  "app_pa_lines",  "APP",  "APP"),
    "sml":   ("sml_pa",  "sml_pa_lines",  "SML",  "SML"),
    "setf":  ("setf_pa", "setf_pa_lines", "SETF", "SETF"),
}
```

### 9.3 Data Model — PA Header

| Kolom | Tipe | Keterangan |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `company_id` | INTEGER | FK → company |
| `pa_number` | TEXT UNIQUE | Auto-generate: `PA/ETF/001/2025` (reset per tahun) |
| `tgl_payment_application` | TEXT | Tanggal PA dibuat |
| `tgl_surat_pengajuan` | TEXT | SLA: tanggal surat pengajuan |
| `doc_received_by_educ` | TEXT | SLA Date 1 |
| `received_pa_from_educ` | TEXT | SLA Date 2 |
| `checked_by_fincon` | TEXT | SLA Date 3 |
| `approved_by_htj_1` | TEXT | SLA Date 4 — approval pertama |
| `send_pa_back_to_educ` | TEXT | SLA Date 5 |
| `pa_received_by_po_fin` | TEXT | SLA Date 6 |
| `approval_by_htj_2` | TEXT | SLA Date 7 — approval final |
| `nomor_pam` | TEXT | Auto-fill saat status → `on_process` |
| `tanggal_bayar` | TEXT | Tanggal realisasi pembayaran |
| `keterangan` | TEXT | Catatan bebas |
| `status` | TEXT | `open` / `on_process` / `complete` |
| `created_at` | TEXT | ISO timestamp |
| `updated_at` | TEXT | ISO timestamp |

### 9.4 Data Model — PA Lines (per siswa)

| Kolom | Tipe | Keterangan |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `pa_id` | INTEGER | FK → `{tab}_pa.id` ON DELETE CASCADE |
| `student_id` | INTEGER | FK → tabel siswa |
| `jenis_pembayaran` | TEXT | Kategori 1 (By Pendidikan, dll) |
| `semester` | TEXT | Kategori 2 |
| `tahun_ajaran` | TEXT | Format `YYYY/YYYY` |
| `ipk_sem_sebelumnya` | REAL | Snapshot IPK saat input (tidak berubah jika IPK diupdate) |
| `jumlah_pembayaran` | REAL | Nominal pembayaran dalam Rupiah |

### 9.5 Status Transitions

```
Buat PA Baru → status = 'open'
    ↓
User edit status → 'on_process' (atau via save_pa_payment)
    nomor_pam diisi otomatis jika belum ada
    ↓
User set Tgl Bayar → cascade: status → 'complete', tanggal_bayar diisi
    (cascade juga ke etf_pa, app_pa, sml_pa via set_memo_tanggal_bayar)

Cancel PAM → PA dikembalikan ke 'open', nomor_pam → NULL
    (cascade ke etf_pa, app_pa, sml_pa via cancel_pam_record)
```

### 9.6 Alur Input Panel (dari Payment Memo)

Endpoint yang digunakan oleh panel Input PA di Payment Memo:

```
GET  /etf-payment-application/draft-siswa?q=...&tab={type}
     → Hanya siswa dengan open PA tipe terpilih

GET  /etf-payment-application/draft-lines?siswa_id={id}&tab={type}
     → Lines PA open untuk siswa terpilih (amount, dates, pa_number)

GET  /payment-memo/ipay/next-pam-no?tab={type}&date={YYYY-MM-DD}
     → PAM number berikutnya untuk tipe + bulan

POST /payment-memo/ipay/save-pa
     → Atomik: INSERT pam_records + payment_beasiswa + UPDATE PA status/nomor_pam

GET  /payment-memo/pam/check?pam_no=<str>
     → Cek apakah PAM number sudah terdaftar (collision check)
```

### 9.7 UI — Halaman Daftar PA

- Header: judul + tombol **"+ Buat PA Baru"** (semua role)
- Tab per tipe: `[AGRI] [APP] [SML] [SETF]`
- Tabel: satu baris = satu PA header (aggregated lines)
  - Sticky column: PA Number
  - Kolom: PA Number, Jml Siswa, Total Bayar, 7 SLA dates, Nomor PAM, Tgl Bayar, Keterangan, Status
  - Badge status: Open (abu) / On Process (kuning) / Complete (hijau)
  - Klik baris → expand detail siswa (inline)
  - Tombol Edit per baris → modal SLA + status update
- Bulk update: checkbox + isi tanggal → confirmModal → update

---

## 10. Data Architecture / Model Data

### 10.1 ERD Ringkas

```
companies (1) ──< siswa (N)
companies (1) ──< budget_beasiswa (N)
companies (1) ──< payment_beasiswa (N)
companies (1) ──< payment_memo (N)
companies (1) ──< pam_records (N)
companies (1) ──< etf_pa (N)
companies (1) ──< app_pa (N)
companies (1) ──< sml_pa (N)
companies (1) ──< setf_pa (N)
etf_pa  (1) ──< etf_pa_lines  (N)
app_pa  (1) ──< app_pa_lines  (N)
sml_pa  (1) ──< sml_pa_lines  (N)
setf_pa (1) ──< setf_pa_lines (N)
payment_memo (1) ──< payment_memo_items (N)
payment_memo (1) ──< payment_application (N)
payment_beasiswa (N) >── payment_memo (1)
coa (N) ──< pam_records (N)   [via gl_account]
```

### 10.2 DDL Lengkap

```sql
-- Core
CREATE TABLE IF NOT EXISTS companies (
    id   INTEGER PRIMARY KEY,
    code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    username       TEXT UNIQUE NOT NULL,
    password_hash  TEXT NOT NULL,
    role           TEXT NOT NULL DEFAULT 'requester',
    is_active      INTEGER DEFAULT 1,
    must_change_pw INTEGER DEFAULT 1,
    created_at     TEXT DEFAULT CURRENT_TIMESTAMP,
    last_login     TEXT
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
    pam            TEXT,
    perusahaan     TEXT,
    cat3           TEXT,
    cat4           TEXT,
    tgl_pengajuan  TEXT,
    tgl_receive    TEXT,
    tgl_pa         TEXT,
    tgl_final      TEXT,
    memo_id        INTEGER REFERENCES payment_memo(id),
    status         TEXT DEFAULT 'open',   -- open | on_process | complete
    created_at     TEXT DEFAULT CURRENT_TIMESTAMP
);

-- PAM Records
CREATE TABLE IF NOT EXISTS pam_records (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id   INTEGER NOT NULL REFERENCES companies(id),
    pam_no       TEXT NOT NULL,
    tanggal      TEXT,
    total_amount REAL DEFAULT 0,
    gl_account   TEXT,
    source       TEXT,                    -- 'etf_agri' | 'etf_app' | 'etf_sml' | 'etf_setf' | NULL
    keterangan   TEXT,                    -- catatan payment bebas
    status       TEXT DEFAULT 'open',     -- open | on_process | complete
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
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id   INTEGER NOT NULL REFERENCES companies(id),
    memo_number  TEXT UNIQUE,
    tanggal      TEXT,
    total_amount REAL DEFAULT 0,
    status       TEXT DEFAULT 'open',     -- open | on_process | complete
    notes        TEXT,
    created_by   TEXT,
    approved_by  TEXT,
    approved_at  TEXT,
    created_at   TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at   TEXT
);

CREATE TABLE IF NOT EXISTS payment_memo_items (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    memo_id       INTEGER NOT NULL REFERENCES payment_memo(id),
    source_module TEXT NOT NULL,
    source_id     INTEGER NOT NULL,
    description   TEXT,
    amount        REAL DEFAULT 0,
    vendor        TEXT,
    bank_account  TEXT
);

-- Payment Application
CREATE TABLE IF NOT EXISTS payment_application (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id          INTEGER NOT NULL REFERENCES companies(id),
    memo_id             INTEGER NOT NULL REFERENCES payment_memo(id),
    application_number  TEXT UNIQUE,
    submitted_at        TEXT,
    target_payment_date TEXT,
    actual_payment_date TEXT,
    status              TEXT DEFAULT 'open',   -- open | complete
    tat_days            INTEGER,
    notes               TEXT,
    created_at          TEXT DEFAULT CURRENT_TIMESTAMP
);

-- ETF Payment Application (AGRI)
CREATE TABLE IF NOT EXISTS etf_pa (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id              INTEGER NOT NULL,
    pa_number               TEXT UNIQUE NOT NULL,
    tgl_payment_application TEXT,
    tgl_surat_pengajuan     TEXT,
    doc_received_by_educ    TEXT,
    received_pa_from_educ   TEXT,
    checked_by_fincon       TEXT,
    approved_by_htj_1       TEXT,
    send_pa_back_to_educ    TEXT,
    pa_received_by_po_fin   TEXT,
    approval_by_htj_2       TEXT,
    nomor_pam               TEXT,
    tanggal_bayar           TEXT,
    keterangan              TEXT,
    status                  TEXT NOT NULL DEFAULT 'open',
    created_at              TEXT,
    updated_at              TEXT
);

CREATE TABLE IF NOT EXISTS etf_pa_lines (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    pa_id                INTEGER NOT NULL REFERENCES etf_pa(id) ON DELETE CASCADE,
    student_id           INTEGER NOT NULL,
    jenis_pembayaran     TEXT,
    semester             TEXT,
    tahun_ajaran         TEXT,
    ipk_sem_sebelumnya   REAL DEFAULT 0,
    jumlah_pembayaran    REAL DEFAULT 0
);

-- ETF Payment Application (APP) — identik dengan etf_pa/etf_pa_lines
CREATE TABLE IF NOT EXISTS app_pa  ( /* schema identik etf_pa  */ );
CREATE TABLE IF NOT EXISTS app_pa_lines  ( /* schema identik etf_pa_lines  */ );

-- ETF Payment Application (SML) — identik
CREATE TABLE IF NOT EXISTS sml_pa  ( /* schema identik etf_pa  */ );
CREATE TABLE IF NOT EXISTS sml_pa_lines  ( /* schema identik etf_pa_lines  */ );

-- ETF Payment Application (SETF) — identik
CREATE TABLE IF NOT EXISTS setf_pa  ( /* schema identik etf_pa  */ );
CREATE TABLE IF NOT EXISTS setf_pa_lines  ( /* schema identik etf_pa_lines  */ );
```

---

## 11. API Specification / Spesifikasi API

Semua endpoint `/api/v1/*` memerlukan header:
```
Authorization: Bearer <access_token>
```

### 11.1 Auth Endpoints (Public)

| Method | Path | Request Body | Response |
|---|---|---|---|
| POST | `/api/auth/login` | `{username, password}` | `{access_token, refresh_token}` |
| POST | `/api/auth/refresh` | `{refresh_token}` | `{access_token}` |
| POST | `/api/auth/logout` | `{refresh_token}` | `{ok: true}` |
| POST | `/api/auth/change-password` | `{old_password, new_password}` | `{ok: true}` |

### 11.2 Beasiswa Endpoints

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

### 11.3 Payment Memo / PAM Endpoints

| Method | Path | Keterangan |
|---|---|---|
| GET | `/payment-memo/pam` | List semua PAM records per company; param `source` untuk filter tipe |
| PATCH | `/payment-memo/pam/<id>/gl-account` | Update GL Account pada PAM record |
| GET | `/payment-memo/pam/check` | `?pam_no=<str>` — collision check, return `{exists: bool}` |
| GET | `/payment-memo/coa` | List Chart of Accounts |
| GET | `/payment-memo/pam/<pam_no>/detail` | Detail PAM + daftar payments |
| POST | `/payment-memo/export/pdf` | Export PDF memo standar |
| POST | `/payment-memo/export/excel` | Export Excel memo standar (2 sheet) |
| POST | `/payment-memo/export/pdf-custom` | Export PDF dari data yang sudah diedit inline |
| POST | `/payment-memo/export/excel-custom` | Export Excel dari data yang sudah diedit inline |
| GET | `/payment-memo/dop/candidates` | Search kandidat Days of PAM (lazy-load) |
| GET | `/payment-memo/dop/search` | Filter Days of PAM rows |
| POST | `/payment-memo/dop/bulk-update` | Bulk update 4 tanggal SLA |
| GET | `/payment-memo/ipay/next-pam-no` | `?tab={agri|app|sml|setf}&date=YYYY-MM-DD` — next PAM number untuk tipe |
| POST | `/payment-memo/ipay/save-pa` | Atomik: INSERT pam_records + payment_beasiswa + UPDATE PA status/nomor_pam |
| GET | `/api/v1/payment-memo` | List semua memo per company |
| POST | `/api/v1/payment-memo` | Buat memo baru |
| GET | `/api/v1/payment-memo/<id>` | Detail memo + items |
| PUT | `/api/v1/payment-memo/<id>/status` | Update status memo |
| GET | `/api/v1/payment-memo/<id>/export/pdf` | Download PDF memo |
| GET | `/api/v1/payment-draft` | List payment draft (belum di-memo) per company |

### 11.4 ETF Payment Application Endpoints

| Method | Path | Keterangan |
|---|---|---|
| GET | `/etf-payment-application` | Halaman daftar PA (tab AGRI/APP/SML/SETF) |
| GET | `/etf-payment-application/list` | `?tab={agri|app|sml|setf}` — JSON list PA |
| POST | `/etf-payment-application/create` | `?tab={type}` — buat PA baru |
| PUT | `/etf-payment-application/update/<id>` | `?tab={type}` — update PA (SLA dates, status, dll) |
| POST | `/etf-payment-application/bulk-update` | `?tab={type}` — bulk update field/value untuk banyak PA |
| GET | `/etf-payment-application/draft-siswa` | `?q=...&tab={type}` — autocomplete siswa dengan open PA |
| GET | `/etf-payment-application/draft-lines` | `?siswa_id={id}&tab={type}` — PA lines untuk PA Picker |

### 11.5 Standard Response Format

```json
{
  "ok": true,
  "data": { ... },
  "pesan": "Keterangan sukses atau error",
  "detail": "Stack trace (hanya saat error, dev mode)"
}
```

---

## 12. Security & Access Control / Keamanan & Kontrol Akses

### 12.1 Authentication Flow

```
1. User POST /api/auth/login → sistem verifikasi password dengan bcrypt
2. Jika valid → generate:
   - access_token: JWT, expire 1 jam, payload: {user_id, username, company_active}
   - refresh_token: JWT, expire 7 hari, di-store hash-nya di tabel refresh_tokens
3. Setiap request API → middleware decode access_token
4. Token expire → client gunakan refresh_token untuk dapat access_token baru
5. Logout → revoke refresh_token di database
```

### 12.2 Password Policy

- Minimum 8 karakter
- Wajib ganti password default saat first login
- Password di-hash dengan bcrypt (cost factor 12)
- Password lama tidak boleh sama dengan password baru

### 12.3 Company Data Isolation

- Semua tabel data bisnis memiliki kolom `company_id`
- Setiap query **wajib** menyertakan `WHERE company_id = ?` dari session aktif
- Tidak ada endpoint yang mengembalikan data lintas perusahaan
- Company aktif disimpan di JWT payload — tidak bisa dimanipulasi client

### 12.4 API Security

- CORS dikonfigurasi hanya untuk origin yang diizinkan (localhost / IP LAN)
- Rate limiting: maksimal 10 request/detik per IP (via Flask-Limiter, coming soon)
- Semua input divalidasi sebelum dieksekusi ke SQLite (parameterized query — tidak ada string concatenation di SQL)
- IDOR guards: setiap resource divalidasi kepemilikan `company_id` sebelum dikembalikan/dimodifikasi

---

## 13. Non-Functional Requirements / Batasan & Risiko

### 13.1 Performance

| Metrik | Target |
|---|---|
| Waktu load halaman | < 2 detik pada LAN |
| Response API | < 500ms untuk query normal |
| Days of PAM search | Lazy-load AJAX — tidak ada data dikirim saat page load |
| ETF PA list | Lazy-load per tab; hanya tipe aktif yang di-query |
| Concurrent users | 10–20 user (SQLite write lock per transaksi) |
| Ukuran database | Estimasi < 100MB untuk 5 tahun data |

### 13.2 Deployment & Availability

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
- **Backup:** copy file `finance_hub.db` ke `Y:/` shared folder secara berkala. `Y:/` digunakan sebagai backup destination, **bukan** lokasi database aktif.

### 13.3 Risiko & Mitigasi

| Risiko | Dampak | Mitigasi |
|---|---|---|
| File `finance_hub.db` terhapus / corrupt | Kehilangan semua data | Backup harian otomatis ke folder lain; migrate_status.py selalu backup sebelum migrasi |
| SQLite write lock jika concurrent write tinggi | Operasi simpan lambat | Acceptable untuk 10–20 user; jika perlu scale gunakan PostgreSQL di versi berikutnya |
| JWT secret bocor | Semua token bisa dipalsukan | Simpan JWT secret di environment variable, bukan di kode |
| Windows machine mati | Sistem tidak accessible | Jalankan di mesin yang selalu on; pertimbangkan UPS |
| PAM number collision (manual override) | Duplikat nomor PAM | Collision check real-time via `GET /payment-memo/pam/check`; guard di `save_pa_payment()` |

### 13.4 Browser Support

- Chrome / Edge (modern) — primary target
- Firefox — supported
- Internet Explorer — tidak didukung

---

## 14. Roadmap & Phasing / Peta Jalan

### Fase 1 — Foundation + PAM Full Feature + ETF Payment Application (v1.x) — ✅ COMPLETE

**Test coverage: 221/222 tests pass (1 failing: `test_get_next_pam_no_sml_uses_sml_prefix`)**

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
| **Data Migration Excel → SQLite** | ✅ | 1,269 siswa, 3,859 budget, 9,567 payment (~14,700 record) |
| **PAM Records + GL Account** | ✅ | Auto-create PAM record saat input payment; update GL Account via COA dropdown |
| **PAM Draft Memo** | ✅ | Cari PAM, preview form, inline editing, collapsible Lampiran, export PDF+Excel |
| **PAM Custom Export** | ✅ | POST endpoint PDF+Excel dari data yang sudah diedit — ephemeral |
| **Days of PAM tab** | ✅ | Search-first lazy-load, inline filters, checkbox bulk-update 4 tanggal SLA |
| **Dynamic Summary Badges** | ✅ | Cross-tab aggregation di list endpoints; `_renderTabSummary()` JS helper |
| Payment Approval Memo | ✅ | List draft payment, buat memo, update status, export PDF |
| Payment Application | ✅ | List memo, update actual payment date, hitung TAT |
| REST API (`/api/v1/`) | ✅ | Semua operasi Beasiswa + PAM tersedia via JSON API |
| Coming Soon pages | ✅ | Placeholder UI untuk modul Bank, AP, Advance, Pettycash, Sponsorship |
| Production server | ✅ | `run.py` via waitress, LAN IP display, startup validation |
| **ETF Payment Application (AGRI)** | ✅ | Modul baru: tabel etf_pa + etf_pa_lines, CRUD PA, 7 SLA dates, auto-PAM pada status → on_process |
| **ETF Payment Application (APP/LAND/SETF)** | ✅ | Extend ke app_pa/sml_pa/setf_pa via `_TAB_CFG`; LAND prefix untuk tab SML; semua endpoint generik |
| **PAM Input Integration** | ✅ | Unified Input PA panel di Payment Memo: type selector, auto-PAM no., save atomik, source filter di tab PAM |
| **PA Picker Sub-Row** | ✅ | Disambiguation saat >1 PA cocok (cat1+cat2); mini-table picker, pure frontend |
| **Editable PAM Number** | ✅ | Override manual dengan format regex validation (real-time) + collision check (blur); endpoint `/pam/check` |
| **PAM ↔ PA Workflow Fix** | ✅ | nomor_pam propagasi saat save; cascade paid-date ke app_pa + sml_pa; status filter hanya `open` |
| **Status Standardization** | ✅ | open/on_process/complete di semua tabel; migration script; DEFAULT 'open' di schema |
| **Global Confirmation Modal** | ✅ | `confirmModal()` promise-based di base.html; semua save/update/delete di semua modul |
| **Pillar-based PAM Tabs** | ✅ | Tab AGRI/APP/LAND/SETF di Payment Memo; freeze header + filter Status/Source; sort by jenjang |
| **PAM Input Transaksi Types** | ✅ | Panel Beasiswa / Klaim Medis (multi-row + CAT3) / Others (tagihan/ETF/sponsor) dalam satu Input PA panel |
| **PAM Print Memo Improvements** | ✅ | Bank detail auto-fill, kolom Jenjang Studi, format Rp Accounting, WORKDAY due date di Excel export |
| **Excel→SQLite PAM Import Script** | ✅ | Migrasi legacy PAM records dari Excel ke SQLite; match functions + pytest tests |
| **ETF PA Summary Tab** | ✅ | `pa_summary` SQL view; lazy-load; filter Nama, Status, Tgl PA, Tahun PA, Bulan PA |
| **PA→Beasiswa Integration (ETF)** | ✅ | `save_pa_payment()` atomik: PA menjadi sumber kebenaran tunggal untuk Beasiswa + PAM |

### Fase 1.5 — SMT Pillar-based PA + Beasiswa Integration (v1.x next)

Sebelum masuk ke Fase 2 (AP & Tax), prioritas terdekat adalah **mereplikasi model ETF ke Sinar Mas Tjipta**. Model integrasi PA→Beasiswa sudah proven di ETF; SMT perlu setup tipe PA dan pillar yang sesuai strukturnya.

| Deliverable | Keterangan | Status |
|---|---|---|
| **SMT Payment Application Modul** | Tipe PA + pillar sesuai struktur SMT; model identik dengan ETF PA | 🔜 |
| **PA→Beasiswa Integration (SMT)** | `save_pa_payment()` extend untuk company_id SMT; sumber kebenaran tunggal | 🔜 |
| **Pillar-based PAM (SMT)** | Tab per pillar SMT di Payment Memo; sort + filter identik ETF | 🔜 |
| **Failing test fix** | `test_get_next_pam_no_sml_uses_sml_prefix` — prefix SML/LAND mismatch | 🐛 |

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
| **Export ETF PA (PDF/Excel)** | Laporan PA per tipe | 🔜 |

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

*Document updated: 2026-06-19 | Finance Hub PRD v1.4 — Before/After methodology (DbBeasiswa + PA Excel → Finance Hub); PA→Beasiswa integration flow; Pillar-based ETF (AGRI/APP/LAND/SETF); PAM Transaksi Types; ETF-first → SMT-next roadmap*
