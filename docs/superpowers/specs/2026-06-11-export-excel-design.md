# Export to Excel — Payment Tabs

**Tanggal:** 2026-06-11
**Status:** Approved
**Scope:** 3 halaman, 7 tab, 6 route baru

---

## Latar Belakang

Tiga halaman di Finance Hub memiliki tabel data dengan filter, tetapi belum semua mendukung export ke Excel yang mencerminkan data yang sedang tampil di layar setelah filter diterapkan:

- **ETF Payment Application** — sudah punya tombol export, tetapi filter aktif (status, nama, dll.) tidak diteruskan ke endpoint export sehingga selalu mengekspor semua data.
- **Payment Approval Memo** — tidak ada bulk export sama sekali di semua tab (Open PAM, AGRI, APP, SML, SLA).
- **Payment Application** — tidak ada export sama sekali.

---

## Tujuan

Menambahkan tombol "↓ Export Excel" di setiap tab yang mengekspor **tepat baris yang sedang tampil** sesuai filter atas (search/bulan/tahun/status) yang sedang aktif.

Sub-filter kolom (input tanggal di sub-header tabel) **tidak** ikut filter export — hanya filter atas saja.

---

## Pendekatan

**Server-side export** menggunakan `openpyxl`, konsisten dengan pola yang sudah ada di ETF export. Tombol export mengirim parameter filter aktif sebagai query string ke endpoint GET baru. Server query dengan filter yang sama, generate `.xlsx`, kirim ke browser sebagai file download.

---

## UI

### Penempatan Tombol

Tombol `↓ Export Excel` ditempatkan di sebelah kanan filter bar masing-masing tab, menggunakan class `btn btn-success btn-sm`.

Label tombol menampilkan jumlah baris aktif secara dinamis setelah data dimuat:
> `↓ Export Excel (42 baris)`

Jumlah baris diambil dari counter yang sudah ada (misalnya `sml-count`, `fiori-count`) atau dihitung dari response API.

### ETF Payment Application

Tombol yang sudah ada (`↓ Export Excel`) diubah dari link statis menjadi fungsi JS yang membaca nilai filter saat ini dan membuka URL export dengan query params.

---

## Arsitektur

### Route Baru

#### Payment Memo (Blueprint: `payment_memo`, prefix `/payment-memo`)

| Tab | Method | Path | Query Params |
|-----|--------|------|--------------|
| Open PAM | GET | `/export/open-pam` | *(tidak perlu, data statis dari session)* |
| AGRI | GET | `/export/pam` | `search`, `bulan`, `tahun`, `source` |
| APP  | GET | `/export/fiori` | `search`, `bulan`, `tahun` |
| SML  | GET | `/export/sml` | `search`, `bulan`, `tahun` |
| SLA  | GET | `/export/sla` | `pam`, `nama` |

#### Payment Application (Blueprint: `payment_application`, prefix `/payment-application`)

| Method | Path | Query Params |
|--------|------|--------------|
| GET | `/export` | `month`, `year` |

#### ETF Payment Application (Blueprint: `etf_payment_application`, prefix `/etf-payment-application`)

Route `/export-excel` sudah ada — dimodifikasi agar menerima dan meneruskan semua filter params yang ada.

Catatan: filter di ETF PA bersifat **campuran** — `sf` (status) menyebabkan page reload (server-side), sedangkan `nama`, `jenjang`, `program`, `angkatan`, `jenis`, `pam`, `bulan_pa`, `tahun_pa` adalah filter client-side (JS hide/show baris tanpa reload). Oleh karena itu:
- Tombol export diubah dari link statis menjadi **fungsi JS** `exportETFExcel()` yang membaca semua nilai filter aktif dari DOM dan membuka URL export dengan semua params tersebut sebagai query string
- Backend `export_pa_excel` dimodifikasi untuk menerima dan menerapkan semua params ini sebagai filter SQL/Python

Query params yang diteruskan:
- `tab` (sudah ada)
- `sf` (status: open/on_process/complete/active)
- `nama`, `jenjang`, `program`, `angkatan`, `jenis`, `pam`, `bulan_pa`, `tahun_pa`

### Service Functions Baru

Setiap route memanggil fungsi service baru di file yang sesuai:

| Fungsi | File | Deskripsi |
|--------|------|-----------|
| `export_open_pam_excel(company_id)` | `payment_memo/service.py` atau `exports.py` | Ambil draft payments (status open), generate xlsx |
| `export_pam_tab_excel(company_id, search, bulan, tahun, source)` | `payment_memo/service.py` atau `exports.py` | Reuse query `get_pam_list`, generate xlsx |
| `export_fiori_excel(company_id, search, bulan, tahun)` | `payment_memo/service.py` atau `exports.py` | Reuse query `get_fiori_list`, generate xlsx |
| `export_sml_excel(company_id, search, bulan, tahun)` | `payment_memo/service.py` atau `exports.py` | Reuse query `get_sml_list`, generate xlsx |
| `export_sla_excel(company_id, pam, nama)` | `payment_memo/service.py` atau `exports.py` | Reuse query `get_days_of_pam`, generate xlsx |
| `export_application_excel(company_id, month, year)` | `payment_application/service.py` | Reuse query `get_applications`, generate xlsx |
| `export_pa_excel` (modifikasi) | `etf_payment_application/service.py` | Tambah parameter filter yang sudah ada |

Semua fungsi export ditempatkan di `exports.py` yang sudah ada (payment_memo) atau dibuat `exports.py` baru per module.

---

## Format File Excel

Semua file mengikuti pola yang sudah ada di `export_pa_excel`:

| Properti | Nilai |
|----------|-------|
| Header row | Bold putih, background navy `#1E3A5F` |
| Row tinggi header | 32px |
| Auto-filter | Aktif di seluruh kolom |
| Freeze pane | A2 (baris header tetap saat scroll) |
| Border | Thin border semua sel |
| Font data | Size 9 |

### Nama File

Format: `{TAB}_{YYYY-MM-DD_HHMM}.xlsx`

Contoh:
- `Open_PAM_2026-06-11_0930.xlsx`
- `PAM_AGRI_2026-06-11_0930.xlsx`
- `PAM_APP_2026-06-11_0930.xlsx`
- `PAM_SML_2026-06-11_0930.xlsx`
- `PAM_SLA_2026-06-11_0930.xlsx`
- `Payment_Application_2026-06-11_0930.xlsx`
- `ETF_PA_AGRI_2026-06-11_0930.xlsx` (sudah ada, dipertahankan)

---

## Kolom per Tab

### Open PAM (tab-draft-pay)

Kolom: Code, Nama Siswa, Kategori 1, Kategori 2, Tanggal, PAM No, Perusahaan, Amount, Status

### AGRI (tab-pam)

Kolom: PAM No, PAM Date, PT, Cost Center, GL Account, Requestor, Catatan Payment, Total (Rp), Due Date, Tgl Paid, Status

### APP / FIORI (tab-fiori)

Kolom: NO PA, Category, Keterangan, Cat 1, Nama Vendor, Total (Rp), Terima Doc, Input Aspiro, Verifikasi Tax, Approval 1, Approval 2, Kirim Aspiro, Paid, Status

### SML (tab-sml)

Kolom: NO PA, Category, Keterangan, Cat 1, Nama Vendor, Total (Rp), Terima Doc, Input Aspiro, Verifikasi Tax, Approval 1, Approval 2, Kirim Aspiro, Paid, Status

### SLA / Days of PAM (tab-days-of-pam)

Kolom: Siswa Code, Nama Siswa, PAM NO, Cat 1, Cat 2, Perusahaan, Pillar, Amount, Tanggal, Tgl Pengajuan, Tgl Receive, Tgl PA, Tgl Final, tgl_retur, tgl_final6, tgl_proses, tgl_HT_AGRI, tgl_Yurike_AGRI, tgl_Aditya_AGRI, tgl_Pedy_AGRI, tgl_C2_AGRI, tgl_MSIG_AGRI, tgl_Paid_AGRI, tgl_A-GS_APP, tgl_A-HJK_APP, tgl_ASPIRO_APP, tgl_Paid_APP

### Payment Application

Kolom: No. Application, Memo, Tgl Pengajuan, Target Bayar, Aktual Bayar, Total (Rp), TAT (hari kerja), Status

---

## File yang Dimodifikasi / Dibuat

| File | Aksi |
|------|------|
| `app/modules/payment_memo/exports.py` | Tambah 5 fungsi export baru |
| `app/modules/payment_memo/routes.py` | Tambah 5 route GET export |
| `app/modules/payment_application/service.py` | Tambah fungsi `export_application_excel` |
| `app/modules/payment_application/routes.py` | Tambah 1 route GET `/export` |
| `app/modules/etf_payment_application/service.py` | Modifikasi `export_pa_excel` agar terima semua filter params |
| `app/modules/etf_payment_application/routes.py` | Modifikasi `export_excel` agar teruskan filter params ke service |
| `app/templates/payment_memo/index.html` | Tambah 5 tombol export + JS handler |
| `app/templates/payment_application/index.html` | Tambah 1 tombol export |
| `app/templates/etf_payment_application/index.html` | Ubah link export jadi JS function yang sertakan filter params |

---

## Yang Tidak Diubah

- Sub-filter kolom (input tanggal di sub-header tabel) tidak mempengaruhi export
- Format PDF, per-row Excel (existing) tidak diubah
- Struktur database tidak berubah
