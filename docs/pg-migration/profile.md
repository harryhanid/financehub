# Profil SQLite

Jumlah tabel: 62

## Perlu perhatian

### Kolom dengan >1 jenis nilai non-null

| Tabel | Kolom | Tipe deklarasi | Jenis nilai |
|---|---|---|---|
| pam_records | dpp | INTEGER | {'integer': 893, 'real': 1} |
| pam_records | ppn | INTEGER | {'integer': 891, 'real': 3} |

### Kolom tanggal dengan format `other`

| Tabel | Kolom | Format | Contoh (maks 5, 30 karakter) |
|---|---|---|---|
| app_pa | pa_received_by_po_fin | {'empty': 18, 'other': 3, 'YYYY-MM-DD': 6} | - |
| app_pa | approval_by_htj_2 | {'empty': 18, 'other': 1, 'YYYY-MM-DD': 2} | - |
| sponsorship_transaksi | tanggal_payment | {'empty': 8, 'other': 27, 'YYYY-MM-DD': 771} | 16 Jun & 24 Jun 20; 21 Dec 20; AGRI : 21 Jul 2023 SML : 15 Au; CANCEL; Carry Over |

### Foreign key dengan baris orphan (dicatat manual dari generate_schema.py, 2026-10-22)

FK ini dibuat `NOT VALID` di `app/db_migrations/0002_schema.sql`; data tidak dihapus.
Override tipe dari generator: `pam_records.dpp` dan `pam_records.ppn` → `double precision` (R7).

| Tabel | Kolom | Referensi | Baris orphan |
|---|---|---|---|
| refresh_tokens | user_id | users(id) | 2 |

## Detail per tabel

### GLETF

| Kolom | Deklarasi | Jenis | Null | Format tanggal |
|---|---|---|---|---|
| id | INTEGER | {'integer': 2038} | 0 | - |
| entry_no | INTEGER | {'integer': 2038} | 0 | - |
| source_type | TEXT | {'text': 2038} | 0 | - |
| acc_statutory | TEXT | {'text': 2038} | 0 | - |
| acc_statutory_desc | TEXT | {'text': 2038} | 0 | - |
| acc_management | TEXT | {'text': 2038} | 0 | - |
| acc_management_desc | TEXT | {'text': 2038} | 0 | - |
| id_no | TEXT | {'text': 2038} | 0 | - |
| tgl | TEXT | {'text': 2038} | 0 | {'YYYY-MM-DD': 2038} |
| memo | TEXT | {'text': 2038} | 0 | - |
| debit | REAL | {'real': 2038} | 0 | - |
| credit | REAL | {'real': 2038} | 0 | - |
| job_name | TEXT | {'text': 2038} | 0 | - |
| job_desc | TEXT | {'text': 2038} | 0 | - |
| pph_non_pph | TEXT | {'text': 2038} | 0 | - |
| budget_activity | TEXT | {'text': 2038} | 0 | - |
| customer_vendor | TEXT | {'text': 2038} | 0 | - |
| allocation_memo | TEXT | {'text': 2038} | 0 | - |
| event | TEXT | {'text': 2038} | 0 | - |
| qty_awal | REAL | {'real': 2038} | 0 | - |
| qty_akhir | REAL | {'real': 2038} | 0 | - |
| uom | TEXT | {'text': 2038} | 0 | - |
| nama_item | TEXT | {'text': 2038} | 0 | - |
| harga_satuan | REAL | {'real': 2038} | 0 | - |
| ket1 | TEXT | {'text': 2038} | 0 | - |
| ket2 | TEXT | {'text': 2038} | 0 | - |
| ket3 | TEXT | {'text': 2038} | 0 | - |
| ket4 | TEXT | {'text': 2038} | 0 | - |
| ket5 | TEXT | {'text': 2038} | 0 | - |
| ket6 | TEXT | {'text': 2038} | 0 | - |
| ket7 | TEXT | {'text': 2038} | 0 | - |
| ket8 | TEXT | {'text': 2038} | 0 | - |
| ket9 | TEXT | {'text': 2038} | 0 | - |
| ket10 | TEXT | {'text': 2038} | 0 | - |
| ket11 | TEXT | {'text': 2038} | 0 | - |
| ket12 | TEXT | {'text': 2038} | 0 | - |
| ket13 | TEXT | {'text': 2038} | 0 | - |
| ket14 | TEXT | {'text': 2038} | 0 | - |
| ket15 | TEXT | {'text': 2038} | 0 | - |
| ket16 | TEXT | {'text': 2038} | 0 | - |
| ket17 | TEXT | {'text': 2038} | 0 | - |
| ket18 | TEXT | {'text': 2038} | 0 | - |
| ket19 | TEXT | {'text': 2038} | 0 | - |
| ket20 | TEXT | {'text': 2038} | 0 | - |
| debit_credit | REAL | {'real': 2038} | 0 | - |
| period | TEXT | {'text': 2038} | 0 | - |
| category_expense | TEXT | {'text': 2038} | 0 | - |
| category_lk | TEXT | {'text': 2038} | 0 | - |
| category_spt | TEXT | {'text': 2038} | 0 | - |
| accrual_actual | TEXT | {'text': 2038} | 0 | - |
| pph | TEXT | {'text': 2038} | 0 | - |
| sub_category | TEXT | {'text': 2038} | 0 | - |

### GLETF_legacy

| Kolom | Deklarasi | Jenis | Null | Format tanggal |
|---|---|---|---|---|
| id | INTEGER | {} | 0 | - |
| entry_no | INTEGER | {} | 0 | - |
| source_type | TEXT | {} | 0 | - |
| acc_statutory | TEXT | {} | 0 | - |
| acc_statutory_desc | TEXT | {} | 0 | - |
| acc_management | TEXT | {} | 0 | - |
| acc_management_desc | TEXT | {} | 0 | - |
| id_no | TEXT | {} | 0 | - |
| tgl | TEXT | {} | 0 | - |
| memo | TEXT | {} | 0 | - |
| debit | REAL | {} | 0 | - |
| credit | REAL | {} | 0 | - |
| job_name | TEXT | {} | 0 | - |
| job_desc | TEXT | {} | 0 | - |
| budget_activity | TEXT | {} | 0 | - |
| customer_vendor | TEXT | {} | 0 | - |
| allocation_memo | TEXT | {} | 0 | - |
| event | TEXT | {} | 0 | - |
| qty_awal | REAL | {} | 0 | - |
| qty_akhir | REAL | {} | 0 | - |
| uom | TEXT | {} | 0 | - |
| nama_item | TEXT | {} | 0 | - |
| harga_satuan | REAL | {} | 0 | - |
| ket1 | TEXT | {} | 0 | - |
| ket2 | TEXT | {} | 0 | - |

### GLSETF

| Kolom | Deklarasi | Jenis | Null | Format tanggal |
|---|---|---|---|---|
| id | INTEGER | {'integer': 146} | 0 | - |
| entry_no | INTEGER | {'integer': 146} | 0 | - |
| source_type | TEXT | {'text': 146} | 0 | - |
| acc_statutory | TEXT | {'text': 146} | 0 | - |
| acc_statutory_desc | TEXT | {'text': 146} | 0 | - |
| acc_management | TEXT | {'text': 146} | 0 | - |
| acc_management_desc | TEXT | {'text': 146} | 0 | - |
| id_no | TEXT | {'text': 146} | 0 | - |
| tgl | TEXT | {'text': 146} | 0 | {'YYYY-MM-DD': 146} |
| memo | TEXT | {'text': 146} | 0 | - |
| debit | REAL | {'real': 146} | 0 | - |
| credit | REAL | {'real': 146} | 0 | - |
| job_name | TEXT | {'text': 146} | 0 | - |
| job_desc | TEXT | {'text': 146} | 0 | - |
| pph_non_pph | TEXT | {'text': 146} | 0 | - |
| budget_activity | TEXT | {'text': 146} | 0 | - |
| customer_vendor | TEXT | {'text': 146} | 0 | - |
| allocation_memo | TEXT | {'text': 146} | 0 | - |
| event | TEXT | {'text': 146} | 0 | - |
| qty_awal | REAL | {'real': 146} | 0 | - |
| qty_akhir | REAL | {'real': 146} | 0 | - |
| uom | TEXT | {'text': 146} | 0 | - |
| nama_item | TEXT | {'text': 146} | 0 | - |
| harga_satuan | REAL | {'real': 146} | 0 | - |
| ket1 | TEXT | {'text': 146} | 0 | - |
| ket2 | TEXT | {'text': 146} | 0 | - |
| ket3 | TEXT | {'text': 146} | 0 | - |
| ket4 | TEXT | {'text': 146} | 0 | - |
| ket5 | TEXT | {'text': 146} | 0 | - |
| ket6 | TEXT | {'text': 146} | 0 | - |
| ket7 | TEXT | {'text': 146} | 0 | - |
| ket8 | TEXT | {'text': 146} | 0 | - |
| ket9 | TEXT | {'text': 146} | 0 | - |
| ket10 | TEXT | {'text': 146} | 0 | - |
| ket11 | TEXT | {'text': 146} | 0 | - |
| ket12 | TEXT | {'text': 146} | 0 | - |
| ket13 | TEXT | {'text': 146} | 0 | - |
| ket14 | TEXT | {'text': 146} | 0 | - |
| ket15 | TEXT | {'text': 146} | 0 | - |
| ket16 | TEXT | {'text': 146} | 0 | - |
| ket17 | TEXT | {'text': 146} | 0 | - |
| ket18 | TEXT | {'text': 146} | 0 | - |
| ket19 | TEXT | {'text': 146} | 0 | - |
| ket20 | TEXT | {'text': 146} | 0 | - |
| debit_credit | REAL | {'real': 146} | 0 | - |
| period | TEXT | {'text': 146} | 0 | - |
| category_expense | TEXT | {'text': 146} | 0 | - |
| category_lk | TEXT | {'text': 146} | 0 | - |
| category_spt | TEXT | {'text': 146} | 0 | - |
| accrual_actual | TEXT | {'text': 146} | 0 | - |
| pph | TEXT | {'text': 146} | 0 | - |
| sub_category | TEXT | {'text': 146} | 0 | - |

### GLSETF_legacy

| Kolom | Deklarasi | Jenis | Null | Format tanggal |
|---|---|---|---|---|
| id | INTEGER | {} | 0 | - |
| entry_no | INTEGER | {} | 0 | - |
| source_type | TEXT | {} | 0 | - |
| acc_statutory | TEXT | {} | 0 | - |
| acc_statutory_desc | TEXT | {} | 0 | - |
| acc_management | TEXT | {} | 0 | - |
| acc_management_desc | TEXT | {} | 0 | - |
| id_no | TEXT | {} | 0 | - |
| tgl | TEXT | {} | 0 | - |
| memo | TEXT | {} | 0 | - |
| debit | REAL | {} | 0 | - |
| credit | REAL | {} | 0 | - |
| job_name | TEXT | {} | 0 | - |
| job_desc | TEXT | {} | 0 | - |
| budget_activity | TEXT | {} | 0 | - |
| customer_vendor | TEXT | {} | 0 | - |
| allocation_memo | TEXT | {} | 0 | - |
| event | TEXT | {} | 0 | - |
| qty_awal | REAL | {} | 0 | - |
| qty_akhir | REAL | {} | 0 | - |
| uom | TEXT | {} | 0 | - |
| nama_item | TEXT | {} | 0 | - |
| harga_satuan | REAL | {} | 0 | - |
| ket1 | TEXT | {} | 0 | - |
| ket2 | TEXT | {} | 0 | - |

### GLSMT

| Kolom | Deklarasi | Jenis | Null | Format tanggal |
|---|---|---|---|---|
| id | INTEGER | {'integer': 8898} | 0 | - |
| entry_no | INTEGER | {'integer': 8898} | 0 | - |
| source_type | TEXT | {'text': 8898} | 0 | - |
| acc_statutory | TEXT | {'text': 8898} | 0 | - |
| acc_statutory_desc | TEXT | {'text': 8898} | 0 | - |
| acc_management | TEXT | {'text': 8898} | 0 | - |
| acc_management_desc | TEXT | {'text': 8898} | 0 | - |
| id_no | TEXT | {'text': 8898} | 0 | - |
| tgl | TEXT | {'text': 8898} | 0 | {'YYYY-MM-DD': 8898} |
| memo | TEXT | {'text': 8898} | 0 | - |
| debit | REAL | {'real': 8898} | 0 | - |
| credit | REAL | {'real': 8898} | 0 | - |
| job_name | TEXT | {'text': 8898} | 0 | - |
| job_desc | TEXT | {'text': 8898} | 0 | - |
| pph_non_pph | TEXT | {'text': 8898} | 0 | - |
| budget_activity | TEXT | {'text': 8898} | 0 | - |
| customer_vendor | TEXT | {'text': 8898} | 0 | - |
| allocation_memo | TEXT | {'text': 8898} | 0 | - |
| event | TEXT | {'text': 8898} | 0 | - |
| qty_awal | REAL | {'real': 8898} | 0 | - |
| qty_akhir | REAL | {'real': 8898} | 0 | - |
| uom | TEXT | {'text': 8898} | 0 | - |
| nama_item | TEXT | {'text': 8898} | 0 | - |
| harga_satuan | REAL | {'real': 8898} | 0 | - |
| ket1 | TEXT | {'text': 8898} | 0 | - |
| ket2 | TEXT | {'text': 8898} | 0 | - |
| ket3 | TEXT | {'text': 8898} | 0 | - |
| ket4 | TEXT | {'text': 8898} | 0 | - |
| ket5 | TEXT | {'text': 8898} | 0 | - |
| ket6 | TEXT | {'text': 8898} | 0 | - |
| ket7 | TEXT | {'text': 8898} | 0 | - |
| ket8 | TEXT | {'text': 8898} | 0 | - |
| ket9 | TEXT | {'text': 8898} | 0 | - |
| ket10 | TEXT | {'text': 8898} | 0 | - |
| ket11 | TEXT | {'text': 8898} | 0 | - |
| ket12 | TEXT | {'text': 8898} | 0 | - |
| ket13 | TEXT | {'text': 8898} | 0 | - |
| ket14 | TEXT | {'text': 8898} | 0 | - |
| ket15 | TEXT | {'text': 8898} | 0 | - |
| ket16 | TEXT | {'text': 8898} | 0 | - |
| ket17 | TEXT | {'text': 8898} | 0 | - |
| ket18 | TEXT | {'text': 8898} | 0 | - |
| ket19 | TEXT | {'text': 8898} | 0 | - |
| ket20 | TEXT | {'text': 8898} | 0 | - |
| debit_credit | REAL | {'real': 8898} | 0 | - |
| period | TEXT | {'text': 8898} | 0 | - |
| category_expense | TEXT | {'text': 8898} | 0 | - |
| category_lk | TEXT | {'text': 8898} | 0 | - |
| category_spt | TEXT | {'text': 8898} | 0 | - |
| accrual_actual | TEXT | {'text': 8898} | 0 | - |
| pph | TEXT | {'text': 8898} | 0 | - |
| sub_category | TEXT | {'text': 8898} | 0 | - |

### GLSMT_legacy

| Kolom | Deklarasi | Jenis | Null | Format tanggal |
|---|---|---|---|---|
| id | INTEGER | {'integer': 13258} | 0 | - |
| entry_no | INTEGER | {'integer': 13258} | 0 | - |
| source_type | TEXT | {'text': 13258} | 0 | - |
| acc_statutory | TEXT | {'text': 13258} | 0 | - |
| acc_statutory_desc | TEXT | {'text': 13258} | 0 | - |
| acc_management | TEXT | {'text': 13258} | 0 | - |
| acc_management_desc | TEXT | {'text': 13258} | 0 | - |
| id_no | TEXT | {'text': 13258} | 0 | - |
| tgl | TEXT | {'text': 13258} | 0 | {'YYYY-MM-DD': 13258} |
| memo | TEXT | {'text': 13258} | 0 | - |
| debit | REAL | {'real': 13258} | 0 | - |
| credit | REAL | {'real': 13258} | 0 | - |
| job_name | TEXT | {'text': 13258} | 0 | - |
| job_desc | TEXT | {'text': 13258} | 0 | - |
| budget_activity | TEXT | {'text': 13258} | 0 | - |
| customer_vendor | TEXT | {'text': 13258} | 0 | - |
| allocation_memo | TEXT | {'text': 13258} | 0 | - |
| event | TEXT | {'text': 13258} | 0 | - |
| qty_awal | REAL | {'real': 13258} | 0 | - |
| qty_akhir | REAL | {'real': 13258} | 0 | - |
| uom | TEXT | {'text': 13258} | 0 | - |
| nama_item | TEXT | {'text': 13258} | 0 | - |
| harga_satuan | REAL | {'real': 13258} | 0 | - |
| ket1 | TEXT | {'text': 13258} | 0 | - |
| ket2 | TEXT | {'text': 13258} | 0 | - |

### advance_pam_lines

| Kolom | Deklarasi | Jenis | Null | Format tanggal |
|---|---|---|---|---|
| id | INTEGER | {} | 0 | - |
| pam_id | INTEGER | {} | 0 | - |
| no_vendor | TEXT | {} | 0 | - |
| nama_vendor | TEXT | {} | 0 | - |
| tgl_received | TEXT | {} | 0 | - |
| tgl_a0 | TEXT | {} | 0 | - |
| tgl_a1 | TEXT | {} | 0 | - |
| tgl_a2 | TEXT | {} | 0 | - |
| tgl_a3 | TEXT | {} | 0 | - |
| tgl_a4 | TEXT | {} | 0 | - |
| tgl_paid | TEXT | {} | 0 | - |
| created_at | TEXT | {} | 0 | - |
| updated_at | TEXT | {} | 0 | - |

### agri_pam_lines

| Kolom | Deklarasi | Jenis | Null | Format tanggal |
|---|---|---|---|---|
| id | INTEGER | {'integer': 169} | 0 | - |
| pam_id | INTEGER | {'integer': 169} | 0 | - |
| no_vendor | TEXT | {'null': 169} | 169 | - |
| nama_vendor | TEXT | {'null': 169} | 169 | - |
| tgl_terima_doc | TEXT | {'null': 169} | 169 | - |
| tgl_proses | TEXT | {'null': 169} | 169 | - |
| tgl_verifikasi_tax | TEXT | {'null': 169} | 169 | - |
| tgl_approval_1 | TEXT | {'null': 169} | 169 | - |
| tgl_approval_2 | TEXT | {'null': 169} | 169 | - |
| tgl_approval_3 | TEXT | {'null': 169} | 169 | - |
| tgl_kirim | TEXT | {'null': 169} | 169 | - |
| created_at | TEXT | {'text': 169} | 0 | {'YYYY-MM-DD HH:MM:SS': 169} |
| updated_at | TEXT | {'null': 169} | 169 | - |

### app_pa

| Kolom | Deklarasi | Jenis | Null | Format tanggal |
|---|---|---|---|---|
| id | INTEGER | {'integer': 339} | 0 | - |
| company_id | INTEGER | {'integer': 339} | 0 | - |
| pa_number | TEXT | {'text': 339} | 0 | - |
| tgl_payment_application | TEXT | {'null': 55, 'text': 284} | 55 | {'YYYY-MM-DD': 284} |
| tgl_surat_pengajuan | TEXT | {'null': 7, 'text': 332} | 7 | {'YYYY-MM-DD': 332} |
| doc_received_by_educ | TEXT | {'null': 25, 'text': 314} | 25 | {'YYYY-MM-DD': 314} |
| received_pa_from_educ | TEXT | {'null': 1, 'text': 338} | 1 | {'YYYY-MM-DD': 338} |
| checked_by_fincon | TEXT | {'null': 9, 'text': 330} | 9 | {'empty': 2, 'YYYY-MM-DD': 328} |
| approved_by_htj_1 | TEXT | {'null': 9, 'text': 330} | 9 | {'empty': 2, 'YYYY-MM-DD': 328} |
| send_pa_back_to_educ | TEXT | {'null': 10, 'text': 329} | 10 | {'empty': 3, 'YYYY-MM-DD': 326} |
| pa_received_by_po_fin | TEXT | {'null': 312, 'text': 27} | 312 | {'empty': 18, 'other': 3, 'YYYY-MM-DD': 6} |
| approval_by_htj_2 | TEXT | {'null': 318, 'text': 21} | 318 | {'empty': 18, 'other': 1, 'YYYY-MM-DD': 2} |
| nomor_pam | TEXT | {'null': 294, 'text': 45} | 294 | - |
| tanggal_bayar | TEXT | {'null': 263, 'text': 76} | 263 | {'empty': 1, 'YYYY-MM-DD': 75} |
| keterangan | TEXT | {'null': 221, 'text': 118} | 221 | - |
| status | TEXT | {'text': 339} | 0 | - |
| created_at | TEXT | {'text': 339} | 0 | {'YYYY-MM-DD HH:MM:SS': 339} |
| updated_at | TEXT | {'null': 260, 'text': 79} | 260 | {'YYYY-MM-DD HH:MM:SS': 79} |
| route | TEXT | {'text': 339} | 0 | - |
| reject_reason | TEXT | {'null': 338, 'text': 1} | 338 | - |
| attachment_file_id | TEXT | {'null': 333, 'text': 6} | 333 | - |
| klasifikasi | TEXT | {'text': 339} | 0 | - |

### app_pa_lines

| Kolom | Deklarasi | Jenis | Null | Format tanggal |
|---|---|---|---|---|
| id | INTEGER | {'integer': 367} | 0 | - |
| pa_id | INTEGER | {'integer': 367} | 0 | - |
| student_id | INTEGER | {'integer': 367} | 0 | - |
| jenis_pembayaran | TEXT | {'text': 367} | 0 | - |
| semester | TEXT | {'text': 367} | 0 | - |
| tahun_ajaran | TEXT | {'text': 367} | 0 | - |
| ipk_sem_sebelumnya | REAL | {'real': 367} | 0 | - |
| jumlah_pembayaran | INTEGER | {'integer': 367} | 0 | - |
| route | TEXT | {'null': 307, 'text': 60} | 307 | - |

### app_pam_lines

| Kolom | Deklarasi | Jenis | Null | Format tanggal |
|---|---|---|---|---|
| id | INTEGER | {'integer': 106} | 0 | - |
| pam_id | INTEGER | {'integer': 106} | 0 | - |
| no_vendor | TEXT | {'null': 8, 'text': 98} | 8 | - |
| nama_vendor | TEXT | {'null': 8, 'text': 98} | 8 | - |
| tgl_terima_doc | TEXT | {'text': 106} | 0 | {'YYYY-MM-DD': 106} |
| tgl_proses | TEXT | {'text': 106} | 0 | {'YYYY-MM-DD': 106} |
| tgl_verifikasi_tax | TEXT | {'null': 67, 'text': 39} | 67 | {'YYYY-MM-DD': 39} |
| tgl_approval_1 | TEXT | {'text': 106} | 0 | {'YYYY-MM-DD': 106} |
| tgl_approval_2 | TEXT | {'null': 66, 'text': 40} | 66 | {'YYYY-MM-DD': 40} |
| tgl_approval_3 | TEXT | {'null': 106} | 106 | - |
| tgl_kirim | TEXT | {'null': 1, 'text': 105} | 1 | {'YYYY-MM-DD': 105} |
| created_at | TEXT | {'text': 106} | 0 | {'YYYY-MM-DD HH:MM:SS': 106} |
| updated_at | TEXT | {'text': 106} | 0 | {'YYYY-MM-DD HH:MM:SS': 106} |

### bank_setf

| Kolom | Deklarasi | Jenis | Null | Format tanggal |
|---|---|---|---|---|
| id | INTEGER | {'integer': 74} | 0 | - |
| company_id | INTEGER | {'integer': 74} | 0 | - |
| tanggal | TEXT | {'text': 74} | 0 | {'YYYY-MM-DD': 74} |
| jenis | TEXT | {'text': 74} | 0 | - |
| jumlah | REAL | {'real': 74} | 0 | - |
| keterangan | TEXT | {'text': 74} | 0 | - |
| source | TEXT | {'text': 74} | 0 | - |
| pam_record_id | INTEGER | {'integer': 27, 'null': 47} | 47 | - |
| created_at | TEXT | {'text': 74} | 0 | {'YYYY-MM-DD HH:MM:SS': 74} |
| updated_at | TEXT | {'null': 43, 'text': 31} | 43 | {'YYYY-MM-DD HH:MM:SS': 31} |

### budget_beasiswa

| Kolom | Deklarasi | Jenis | Null | Format tanggal |
|---|---|---|---|---|
| id | INTEGER | {'integer': 4369} | 0 | - |
| company_id | INTEGER | {'integer': 4369} | 0 | - |
| siswa_code | TEXT | {'text': 4369} | 0 | - |
| cat1 | TEXT | {'text': 4369} | 0 | - |
| cat2 | TEXT | {'text': 4369} | 0 | - |
| tanggal | TEXT | {'text': 4369} | 0 | {'YYYY-MM-DD': 4369} |
| amount | REAL | {'real': 4369} | 0 | - |
| pillar | TEXT | {'text': 4369} | 0 | - |
| created_at | TEXT | {'text': 4369} | 0 | {'YYYY-MM-DD HH:MM:SS': 4369} |
| tgl_expired | TEXT | {'null': 4362, 'text': 7} | 4362 | {'YYYY-MM-DD': 7} |

### budget_beasiswa_requests

| Kolom | Deklarasi | Jenis | Null | Format tanggal |
|---|---|---|---|---|
| id | INTEGER | {'integer': 23} | 0 | - |
| company_id | INTEGER | {'integer': 23} | 0 | - |
| siswa_code | TEXT | {'text': 23} | 0 | - |
| action_type | TEXT | {'text': 23} | 0 | - |
| budget_id | INTEGER | {'integer': 3, 'null': 20} | 20 | - |
| cat1 | TEXT | {'text': 23} | 0 | - |
| cat2 | TEXT | {'text': 23} | 0 | - |
| tanggal | TEXT | {'text': 23} | 0 | {'YYYY-MM-DD': 23} |
| amount | REAL | {'real': 23} | 0 | - |
| pillar | TEXT | {'text': 23} | 0 | - |
| tgl_expired | TEXT | {'null': 18, 'text': 5} | 18 | {'YYYY-MM-DD': 5} |
| status | TEXT | {'text': 23} | 0 | - |
| reject_reason | TEXT | {'null': 22, 'text': 1} | 22 | - |
| created_by | TEXT | {'text': 23} | 0 | - |
| created_at | TEXT | {'text': 23} | 0 | {'YYYY-MM-DD HH:MM:SS': 23} |
| processed_by | TEXT | {'text': 23} | 0 | - |
| processed_at | TEXT | {'text': 23} | 0 | {'YYYY-MM-DD HH:MM:SS': 23} |
| batch_id | TEXT | {'text': 23} | 0 | - |

### budget_carryover_logs

| Kolom | Deklarasi | Jenis | Null | Format tanggal |
|---|---|---|---|---|
| id | INTEGER | {} | 0 | - |
| budget_id | TEXT | {} | 0 | - |
| requested_by | TEXT | {} | 0 | - |
| request_date | TEXT | {} | 0 | - |
| status | TEXT | {} | 0 | - |
| approval_date | TEXT | {} | 0 | - |
| extension_months | INTEGER | {} | 0 | - |
| reason | TEXT | {} | 0 | - |
| approved_by | TEXT | {} | 0 | - |
| type | TEXT | {} | 0 | - |
| additional_amount | REAL | {} | 0 | - |

### budget_master

| Kolom | Deklarasi | Jenis | Null | Format tanggal |
|---|---|---|---|---|
| id | TEXT | {'text': 3458} | 0 | - |
| mm | INTEGER | {'integer': 3458} | 0 | - |
| yy | INTEGER | {'integer': 3458} | 0 | - |
| company | TEXT | {'text': 3458} | 0 | - |
| dept | TEXT | {'text': 3458} | 0 | - |
| gl_account | TEXT | {'text': 3458} | 0 | - |
| gl_description | TEXT | {'text': 3458} | 0 | - |
| budget_category | TEXT | {'text': 3458} | 0 | - |
| activity | TEXT | {'text': 3458} | 0 | - |
| description | TEXT | {'text': 3458} | 0 | - |
| amount | REAL | {'real': 3458} | 0 | - |
| deadline | TEXT | {'text': 3458} | 0 | {'YYYY-MM-DD': 3458} |
| created_at | TEXT | {'text': 3458} | 0 | {'YYYY-MM-DD HH:MM:SS': 3458} |
| updated_at | TEXT | {'null': 3458} | 3458 | - |

### budget_realisasi

| Kolom | Deklarasi | Jenis | Null | Format tanggal |
|---|---|---|---|---|
| trx_id | TEXT | {} | 0 | - |
| budget_id | TEXT | {} | 0 | - |
| mm | INTEGER | {} | 0 | - |
| yy | INTEGER | {} | 0 | - |
| company | TEXT | {} | 0 | - |
| dept | TEXT | {} | 0 | - |
| gl_account | TEXT | {} | 0 | - |
| gl_description | TEXT | {} | 0 | - |
| budget_category | TEXT | {} | 0 | - |
| activity | TEXT | {} | 0 | - |
| description | TEXT | {} | 0 | - |
| amount | REAL | {} | 0 | - |
| tanggal_realisasi | TEXT | {} | 0 | - |
| created_at | TEXT | {} | 0 | - |

### coa

| Kolom | Deklarasi | Jenis | Null | Format tanggal |
|---|---|---|---|---|
| gl_code | TEXT | {'text': 14} | 0 | - |
| gl_name | TEXT | {'text': 14} | 0 | - |
| is_active | INTEGER | {'integer': 14} | 0 | - |

### coa_pam

| Kolom | Deklarasi | Jenis | Null | Format tanggal |
|---|---|---|---|---|
| id | INTEGER | {'integer': 44} | 0 | - |
| klasifikasi_sr | TEXT | {'text': 44} | 0 | - |
| klasifikasi_mr | TEXT | {'text': 44} | 0 | - |
| coa_advance | TEXT | {'null': 30, 'text': 14} | 30 | - |
| coa_expense | TEXT | {'text': 44} | 0 | - |

### companies

| Kolom | Deklarasi | Jenis | Null | Format tanggal |
|---|---|---|---|---|
| id | INTEGER | {'integer': 2} | 0 | - |
| code | TEXT | {'text': 2} | 0 | - |
| name | TEXT | {'text': 2} | 0 | - |

### energy_pa

| Kolom | Deklarasi | Jenis | Null | Format tanggal |
|---|---|---|---|---|
| id | INTEGER | {'integer': 5} | 0 | - |
| company_id | INTEGER | {'integer': 5} | 0 | - |
| pa_number | TEXT | {'text': 5} | 0 | - |
| tgl_payment_application | TEXT | {'text': 5} | 0 | {'YYYY-MM-DD': 5} |
| tgl_surat_pengajuan | TEXT | {'text': 5} | 0 | {'YYYY-MM-DD': 5} |
| doc_received_by_educ | TEXT | {'text': 5} | 0 | {'YYYY-MM-DD': 5} |
| received_pa_from_educ | TEXT | {'text': 5} | 0 | {'YYYY-MM-DD': 5} |
| checked_by_fincon | TEXT | {'null': 2, 'text': 3} | 2 | {'empty': 1, 'YYYY-MM-DD': 2} |
| approved_by_htj_1 | TEXT | {'null': 2, 'text': 3} | 2 | {'empty': 1, 'YYYY-MM-DD': 2} |
| send_pa_back_to_educ | TEXT | {'null': 2, 'text': 3} | 2 | {'empty': 1, 'YYYY-MM-DD': 2} |
| pa_received_by_po_fin | TEXT | {'null': 3, 'text': 2} | 3 | - |
| approval_by_htj_2 | TEXT | {'null': 3, 'text': 2} | 3 | - |
| nomor_pam | TEXT | {'null': 3, 'text': 2} | 3 | - |
| tanggal_bayar | TEXT | {'null': 3, 'text': 2} | 3 | {'empty': 2} |
| keterangan | TEXT | {'text': 5} | 0 | - |
| no_pa | TEXT | {'null': 5} | 5 | - |
| category | TEXT | {'null': 5} | 5 | - |
| categori_1 | TEXT | {'null': 5} | 5 | - |
| nomor_vendor | TEXT | {'null': 5} | 5 | - |
| nama_vendor | TEXT | {'null': 5} | 5 | - |
| mata_uang | TEXT | {'text': 5} | 0 | - |
| dpp | INTEGER | {'integer': 5} | 0 | - |
| ppn | INTEGER | {'integer': 5} | 0 | - |
| total | INTEGER | {'integer': 5} | 0 | - |
| terima_document | TEXT | {'null': 5} | 5 | - |
| input_aspiro | TEXT | {'null': 5} | 5 | - |
| verifikasi_tax | TEXT | {'null': 5} | 5 | - |
| approval_1 | TEXT | {'null': 5} | 5 | - |
| approval_2 | TEXT | {'null': 5} | 5 | - |
| approval_3 | TEXT | {'null': 5} | 5 | - |
| kirim_aspiro | TEXT | {'null': 5} | 5 | - |
| paid | TEXT | {'null': 5} | 5 | - |
| status | TEXT | {'text': 5} | 0 | - |
| created_at | TEXT | {'text': 5} | 0 | {'YYYY-MM-DD HH:MM:SS': 5} |
| updated_at | TEXT | {'null': 2, 'text': 3} | 2 | {'YYYY-MM-DD HH:MM:SS': 3} |
| reject_reason | TEXT | {'null': 5} | 5 | - |
| route | TEXT | {'text': 5} | 0 | - |
| attachment_file_id | TEXT | {'null': 5} | 5 | - |
| klasifikasi | TEXT | {'text': 5} | 0 | - |

### energy_pa_lines

| Kolom | Deklarasi | Jenis | Null | Format tanggal |
|---|---|---|---|---|
| id | INTEGER | {'integer': 6} | 0 | - |
| pa_id | INTEGER | {'integer': 6} | 0 | - |
| student_id | INTEGER | {'integer': 6} | 0 | - |
| jenis_pembayaran | TEXT | {'text': 6} | 0 | - |
| semester | TEXT | {'text': 6} | 0 | - |
| tahun_ajaran | TEXT | {'text': 6} | 0 | - |
| ipk_sem_sebelumnya | REAL | {'real': 6} | 0 | - |
| jumlah_pembayaran | INTEGER | {'integer': 6} | 0 | - |
| route | TEXT | {'text': 6} | 0 | - |

### energy_pam_lines

| Kolom | Deklarasi | Jenis | Null | Format tanggal |
|---|---|---|---|---|
| id | INTEGER | {} | 0 | - |
| pam_id | INTEGER | {} | 0 | - |
| no_vendor | TEXT | {} | 0 | - |
| nama_vendor | TEXT | {} | 0 | - |
| tgl_terima_doc | TEXT | {} | 0 | - |
| tgl_proses | TEXT | {} | 0 | - |
| tgl_verifikasi_tax | TEXT | {} | 0 | - |
| tgl_approval_1 | TEXT | {} | 0 | - |
| tgl_approval_2 | TEXT | {} | 0 | - |
| tgl_approval_3 | TEXT | {} | 0 | - |
| tgl_kirim | TEXT | {} | 0 | - |
| created_at | TEXT | {} | 0 | - |
| updated_at | TEXT | {} | 0 | - |

### etf_pa

| Kolom | Deklarasi | Jenis | Null | Format tanggal |
|---|---|---|---|---|
| id | INTEGER | {'integer': 584} | 0 | - |
| company_id | INTEGER | {'integer': 584} | 0 | - |
| pa_number | TEXT | {'text': 584} | 0 | - |
| tgl_payment_application | TEXT | {'text': 584} | 0 | {'YYYY-MM-DD': 584} |
| tgl_surat_pengajuan | TEXT | {'null': 8, 'text': 576} | 8 | {'YYYY-MM-DD': 576} |
| doc_received_by_educ | TEXT | {'null': 2, 'text': 582} | 2 | {'YYYY-MM-DD': 582} |
| received_pa_from_educ | TEXT | {'text': 584} | 0 | {'YYYY-MM-DD': 584} |
| checked_by_fincon | TEXT | {'null': 4, 'text': 580} | 4 | {'empty': 4, 'YYYY-MM-DD': 576} |
| approved_by_htj_1 | TEXT | {'null': 4, 'text': 580} | 4 | {'empty': 4, 'YYYY-MM-DD': 576} |
| send_pa_back_to_educ | TEXT | {'null': 5, 'text': 579} | 5 | {'empty': 4, 'YYYY-MM-DD': 575} |
| pa_received_by_po_fin | TEXT | {'null': 12, 'text': 572} | 12 | {'empty': 8, 'YYYY-MM-DD': 564} |
| approval_by_htj_2 | TEXT | {'null': 33, 'text': 551} | 33 | {'empty': 14, 'YYYY-MM-DD': 537} |
| nomor_pam | TEXT | {'null': 16, 'text': 568} | 16 | - |
| tanggal_bayar | TEXT | {'null': 30, 'text': 554} | 30 | {'empty': 17, 'YYYY-MM-DD': 537} |
| keterangan | TEXT | {'null': 84, 'text': 500} | 84 | - |
| status | TEXT | {'text': 584} | 0 | - |
| created_at | TEXT | {'text': 584} | 0 | {'YYYY-MM-DD': 342, 'YYYY-MM-DD HH:MM:SS': 242} |
| updated_at | TEXT | {'null': 2, 'text': 582} | 2 | {'YYYY-MM-DD': 260, 'YYYY-MM-DD HH:MM:SS': 322} |
| route | TEXT | {'text': 584} | 0 | - |
| reject_reason | TEXT | {'null': 583, 'text': 1} | 583 | - |
| attachment_file_id | TEXT | {'null': 558, 'text': 26} | 558 | - |
| klasifikasi | TEXT | {'text': 584} | 0 | - |

### etf_pa_lines

| Kolom | Deklarasi | Jenis | Null | Format tanggal |
|---|---|---|---|---|
| id | INTEGER | {'integer': 694} | 0 | - |
| pa_id | INTEGER | {'integer': 694} | 0 | - |
| student_id | INTEGER | {'integer': 694} | 0 | - |
| jenis_pembayaran | TEXT | {'text': 694} | 0 | - |
| semester | TEXT | {'text': 694} | 0 | - |
| tahun_ajaran | TEXT | {'text': 694} | 0 | - |
| ipk_sem_sebelumnya | REAL | {'real': 694} | 0 | - |
| jumlah_pembayaran | INTEGER | {'integer': 694} | 0 | - |
| route | TEXT | {'null': 374, 'text': 320} | 374 | - |

### fiori_pa

| Kolom | Deklarasi | Jenis | Null | Format tanggal |
|---|---|---|---|---|
| id | INTEGER | {'integer': 103} | 0 | - |
| no_pa | TEXT | {'text': 103} | 0 | - |
| category | TEXT | {'text': 103} | 0 | - |
| keterangan | TEXT | {'text': 103} | 0 | - |
| categori_1 | TEXT | {'null': 45, 'text': 58} | 45 | - |
| nomor_vendor | TEXT | {'null': 7, 'text': 96} | 7 | - |
| nama_vendor | TEXT | {'null': 7, 'text': 96} | 7 | - |
| mata_uang | TEXT | {'text': 103} | 0 | - |
| dpp | INTEGER | {'integer': 103} | 0 | - |
| ppn | INTEGER | {'integer': 103} | 0 | - |
| total | INTEGER | {'integer': 103} | 0 | - |
| terima_document | TEXT | {'text': 103} | 0 | {'YYYY-MM-DD': 103} |
| input_aspiro | TEXT | {'text': 103} | 0 | {'YYYY-MM-DD': 103} |
| verifikasi_tax | TEXT | {'null': 64, 'text': 39} | 64 | {'YYYY-MM-DD': 39} |
| approval_1 | TEXT | {'text': 103} | 0 | {'YYYY-MM-DD': 103} |
| approval_2 | TEXT | {'null': 63, 'text': 40} | 63 | {'YYYY-MM-DD': 40} |
| approval_3 | TEXT | {'null': 103} | 103 | - |
| kirim_aspiro | TEXT | {'null': 1, 'text': 102} | 1 | {'YYYY-MM-DD': 102} |
| paid | TEXT | {'null': 20, 'text': 83} | 20 | {'YYYY-MM-DD': 83} |
| created_at | TEXT | {'text': 103} | 0 | {'YYYY-MM-DD HH:MM:SS': 103} |
| status | TEXT | {'text': 103} | 0 | - |

### gl_category_lk

| Kolom | Deklarasi | Jenis | Null | Format tanggal |
|---|---|---|---|---|
| category_lk | TEXT | {'text': 18} | 0 | - |
| statement | TEXT | {'text': 18} | 0 | - |
| kind | TEXT | {'text': 18} | 0 | - |
| seq | INTEGER | {'integer': 18} | 0 | - |
| label | TEXT | {'text': 18} | 0 | - |
| needs_spt | INTEGER | {'integer': 18} | 0 | - |

### gl_category_map

| Kolom | Deklarasi | Jenis | Null | Format tanggal |
|---|---|---|---|---|
| source | TEXT | {'text': 511} | 0 | - |
| account | TEXT | {'text': 511} | 0 | - |
| categories_expense | TEXT | {'text': 511} | 0 | - |
| category_lk | TEXT | {'text': 511} | 0 | - |
| category_spt | TEXT | {'text': 511} | 0 | - |

### gl_category_sync_log

| Kolom | Deklarasi | Jenis | Null | Format tanggal |
|---|---|---|---|---|
| id | INTEGER | {'integer': 1} | 0 | - |
| synced_at | TEXT | {'text': 1} | 0 | {'YYYY-MM-DD HH:MM:SS': 1} |
| synced_by | TEXT | {'text': 1} | 0 | - |
| filename | TEXT | {'text': 1} | 0 | - |
| content_hash | TEXT | {'text': 1} | 0 | - |
| rows_smt | INTEGER | {'integer': 1} | 0 | - |
| rows_etf | INTEGER | {'integer': 1} | 0 | - |

### gl_cc_map

| Kolom | Deklarasi | Jenis | Null | Format tanggal |
|---|---|---|---|---|
| cost_center | TEXT | {'text': 89} | 0 | - |
| total_cc | TEXT | {'text': 89} | 0 | - |
| seq | INTEGER | {'integer': 89} | 0 | - |
| description | TEXT | {'text': 89} | 0 | - |

### gl_coa_map

| Kolom | Deklarasi | Jenis | Null | Format tanggal |
|---|---|---|---|---|
| source | TEXT | {'text': 396} | 0 | - |
| account | TEXT | {'text': 396} | 0 | - |
| coa_ho | TEXT | {'text': 396} | 0 | - |
| category | TEXT | {'text': 396} | 0 | - |
| code | TEXT | {'text': 396} | 0 | - |

### gl_coa_sync_log

| Kolom | Deklarasi | Jenis | Null | Format tanggal |
|---|---|---|---|---|
| id | INTEGER | {'integer': 2} | 0 | - |
| synced_at | TEXT | {'text': 2} | 0 | {'YYYY-MM-DD HH:MM:SS': 2} |
| synced_by | TEXT | {'text': 2} | 0 | - |
| filename | TEXT | {'text': 2} | 0 | - |
| content_hash | TEXT | {'text': 2} | 0 | - |
| rows_smt | INTEGER | {'integer': 2} | 0 | - |
| rows_etf | INTEGER | {'integer': 2} | 0 | - |
| rows_cc | INTEGER | {'integer': 2} | 0 | - |

### gl_mapping_meta

| Kolom | Deklarasi | Jenis | Null | Format tanggal |
|---|---|---|---|---|
| key | TEXT | {'text': 1} | 0 | - |
| value | TEXT | {'text': 1} | 0 | - |

### gl_pph_alias

| Kolom | Deklarasi | Jenis | Null | Format tanggal |
|---|---|---|---|---|
| alias | TEXT | {'text': 4} | 0 | - |
| pph_type | TEXT | {'text': 4} | 0 | - |

### gl_sync_log

| Kolom | Deklarasi | Jenis | Null | Format tanggal |
|---|---|---|---|---|
| id | INTEGER | {'integer': 4} | 0 | - |
| entity | TEXT | {'text': 4} | 0 | - |
| synced_at | TEXT | {'text': 4} | 0 | {'YYYY-MM-DD HH:MM:SS': 4} |
| synced_by | TEXT | {'text': 4} | 0 | - |
| filename | TEXT | {'text': 4} | 0 | - |
| content_hash | TEXT | {'text': 4} | 0 | - |
| rows_before | INTEGER | {'integer': 4} | 0 | - |
| rows_after | INTEGER | {'integer': 4} | 0 | - |
| total_debit | REAL | {'real': 4} | 0 | - |
| total_credit | REAL | {'real': 4} | 0 | - |
| dropped | INTEGER | {'integer': 4} | 0 | - |
| summary | TEXT | {'text': 4} | 0 | - |
| year | INTEGER | {'null': 4} | 4 | - |

### gl_transactions

| Kolom | Deklarasi | Jenis | Null | Format tanggal |
|---|---|---|---|---|
| id_gl | INTEGER | {} | 0 | - |
| company_code | TEXT | {} | 0 | - |
| x | INTEGER | {} | 0 | - |
| x1 | TEXT | {} | 0 | - |
| account_statutory | TEXT | {} | 0 | - |
| desc_account_statutory | TEXT | {} | 0 | - |
| account_management | TEXT | {} | 0 | - |
| desc_account_management | TEXT | {} | 0 | - |
| transaction_id | TEXT | {} | 0 | - |
| tanggal | TEXT | {} | 0 | - |
| memo | TEXT | {} | 0 | - |
| debit | REAL | {} | 0 | - |
| credit | INTEGER | {} | 0 | - |
| job_name | TEXT | {} | 0 | - |
| job_description | TEXT | {} | 0 | - |
| pph_non_pph | REAL | {} | 0 | - |
| budget_activity | TEXT | {} | 0 | - |
| customer_vendor | TEXT | {} | 0 | - |
| allocation_memo | TEXT | {} | 0 | - |
| event | REAL | {} | 0 | - |
| qty_awal | REAL | {} | 0 | - |
| qty_akhir | REAL | {} | 0 | - |
| uom | REAL | {} | 0 | - |
| nama_item | REAL | {} | 0 | - |
| harga_satuan | REAL | {} | 0 | - |
| keterangan_1 | REAL | {} | 0 | - |
| keterangan_2 | REAL | {} | 0 | - |
| keterangan_3 | REAL | {} | 0 | - |
| keterangan_4 | REAL | {} | 0 | - |
| keterangan_5 | REAL | {} | 0 | - |
| keterangan_6 | REAL | {} | 0 | - |
| keterangan_7 | REAL | {} | 0 | - |
| keterangan_8 | REAL | {} | 0 | - |
| keterangan_9 | REAL | {} | 0 | - |
| keterangan_10 | REAL | {} | 0 | - |
| keterangan_11 | REAL | {} | 0 | - |
| keterangan_12 | REAL | {} | 0 | - |
| keterangan_13 | REAL | {} | 0 | - |
| keterangan_14 | REAL | {} | 0 | - |
| keterangan_15 | REAL | {} | 0 | - |
| keterangan_16 | REAL | {} | 0 | - |
| keterangan_17 | REAL | {} | 0 | - |
| keterangan_18 | REAL | {} | 0 | - |
| keterangan_19 | REAL | {} | 0 | - |
| keterangan_20 | REAL | {} | 0 | - |
| debit_credit | INTEGER | {} | 0 | - |
| period | INTEGER | {} | 0 | - |
| categories_expense | TEXT | {} | 0 | - |
| category_lk | TEXT | {} | 0 | - |
| category_spt | TEXT | {} | 0 | - |
| accrual_actual | TEXT | {} | 0 | - |
| pph | REAL | {} | 0 | - |
| sub_category | REAL | {} | 0 | - |

### klaim_medical

| Kolom | Deklarasi | Jenis | Null | Format tanggal |
|---|---|---|---|---|
| id | INTEGER | {'integer': 22} | 0 | - |
| company_id | INTEGER | {'integer': 22} | 0 | - |
| siswa_code | TEXT | {'text': 22} | 0 | - |
| pam | TEXT | {'text': 22} | 0 | - |
| tanggal | TEXT | {'text': 22} | 0 | {'YYYY-MM-DD': 22} |
| amount | REAL | {'real': 22} | 0 | - |
| perawatan | TEXT | {'text': 22} | 0 | - |
| kelas | TEXT | {'text': 22} | 0 | - |
| rumah_sakit | TEXT | {'text': 22} | 0 | - |
| diagnosa | TEXT | {'text': 22} | 0 | - |
| spesialisasi | TEXT | {'text': 22} | 0 | - |
| pillar | TEXT | {'text': 22} | 0 | - |
| perusahaan | TEXT | {'text': 22} | 0 | - |
| payment_id | INTEGER | {'integer': 22} | 0 | - |
| created_at | TEXT | {'text': 22} | 0 | {'YYYY-MM-DD HH:MM:SS': 22} |
| klasifikasi_pam | TEXT | {'null': 20, 'text': 2} | 20 | - |

### land_pam_lines

| Kolom | Deklarasi | Jenis | Null | Format tanggal |
|---|---|---|---|---|
| id | INTEGER | {} | 0 | - |
| pam_id | INTEGER | {} | 0 | - |
| no_vendor | TEXT | {} | 0 | - |
| nama_vendor | TEXT | {} | 0 | - |
| tgl_terima_doc | TEXT | {} | 0 | - |
| tgl_proses | TEXT | {} | 0 | - |
| tgl_verifikasi_tax | TEXT | {} | 0 | - |
| tgl_approval_1 | TEXT | {} | 0 | - |
| tgl_approval_2 | TEXT | {} | 0 | - |
| tgl_approval_3 | TEXT | {} | 0 | - |
| tgl_kirim | TEXT | {} | 0 | - |
| created_at | TEXT | {} | 0 | - |
| updated_at | TEXT | {} | 0 | - |

### mr_append

| Kolom | Deklarasi | Jenis | Null | Format tanggal |
|---|---|---|---|---|
| id | INTEGER | {'integer': 62572} | 0 | - |
| upload_id | INTEGER | {'integer': 62572} | 0 | - |
| coa | TEXT | {'text': 62572} | 0 | - |
| mm | INTEGER | {'integer': 62572} | 0 | - |
| yy | INTEGER | {'integer': 62572} | 0 | - |
| cc | TEXT | {'text': 62572} | 0 | - |
| category | TEXT | {'text': 62572} | 0 | - |
| activity | TEXT | {'text': 62572} | 0 | - |
| description | TEXT | {'text': 62572} | 0 | - |
| pta | REAL | {'real': 62572} | 0 | - |
| custom | TEXT | {'text': 62572} | 0 | - |
| mm1 | INTEGER | {'integer': 62572} | 0 | - |
| act | REAL | {'real': 62572} | 0 | - |
| bgt | REAL | {'real': 62572} | 0 | - |

### mr_upload

| Kolom | Deklarasi | Jenis | Null | Format tanggal |
|---|---|---|---|---|
| id | INTEGER | {'integer': 7} | 0 | - |
| company_id | INTEGER | {'integer': 7} | 0 | - |
| filename | TEXT | {'text': 7} | 0 | - |
| uploaded_by | TEXT | {'text': 7} | 0 | - |
| uploaded_at | TEXT | {'text': 7} | 0 | {'YYYY-MM-DD HH:MM:SS': 7} |
| row_count | INTEGER | {'integer': 7} | 0 | - |
| is_active | INTEGER | {'integer': 7} | 0 | - |
| purged | INTEGER | {'integer': 7} | 0 | - |
| content_hash | TEXT | {'null': 1, 'text': 6} | 1 | - |
| change_summary | TEXT | {'null': 1, 'text': 6} | 1 | - |
| meta | TEXT | {'null': 2, 'text': 5} | 2 | - |

### pam_records

| Kolom | Deklarasi | Jenis | Null | Format tanggal |
|---|---|---|---|---|
| id | INTEGER | {'integer': 894} | 0 | - |
| company_id | INTEGER | {'integer': 894} | 0 | - |
| pam_no | TEXT | {'text': 894} | 0 | - |
| pam_date | TEXT | {'text': 894} | 0 | {'YYYY-MM-DD': 894} |
| gl_account | TEXT | {'text': 894} | 0 | - |
| cost_center | TEXT | {'null': 126, 'text': 768} | 126 | - |
| pt | TEXT | {'text': 894} | 0 | - |
| requestors_name | TEXT | {'text': 894} | 0 | - |
| keterangan | TEXT | {'null': 13, 'text': 881} | 13 | - |
| total_amount | REAL | {'real': 894} | 0 | - |
| due_date | TEXT | {'text': 894} | 0 | {'YYYY-MM-DD': 894} |
| status | TEXT | {'text': 894} | 0 | - |
| created_at | TEXT | {'null': 105, 'text': 789} | 105 | {'YYYY-MM-DD': 178, 'YYYY-MM-DD HH:MM:SS': 611} |
| updated_at | TEXT | {'null': 200, 'text': 694} | 200 | {'YYYY-MM-DD': 98, 'YYYY-MM-DD HH:MM:SS': 596} |
| tanggal_bayar | TEXT | {'null': 165, 'text': 729} | 165 | {'YYYY-MM-DD': 729} |
| source | TEXT | {'text': 894} | 0 | - |
| mata_uang | TEXT | {'text': 894} | 0 | - |
| dpp | INTEGER | {'integer': 893, 'real': 1} | 0 | - |
| ppn | INTEGER | {'integer': 891, 'real': 3} | 0 | - |
| pillar | TEXT | {'text': 894} | 0 | - |
| others | INTEGER | {'integer': 894} | 0 | - |
| reject_reason | TEXT | {'null': 894} | 894 | - |
| attachment_file_id | TEXT | {'null': 879, 'text': 15} | 879 | - |
| klasifikasi | TEXT | {'text': 894} | 0 | - |

### pam_transaction_lines

| Kolom | Deklarasi | Jenis | Null | Format tanggal |
|---|---|---|---|---|
| id | INTEGER | {'integer': 664} | 0 | - |
| pam_id | INTEGER | {'integer': 664} | 0 | - |
| coa_pam_id | INTEGER | {'integer': 2, 'null': 662} | 662 | - |
| klasifikasi_sr | TEXT | {'text': 664} | 0 | - |
| klasifikasi_mr | TEXT | {'text': 664} | 0 | - |
| gl_account | TEXT | {'text': 664} | 0 | - |
| tipe_dokumen | TEXT | {'text': 664} | 0 | - |
| no_invoice | TEXT | {'text': 664} | 0 | - |
| dpp | REAL | {'real': 664} | 0 | - |
| ppn | REAL | {'real': 664} | 0 | - |
| total_amount | REAL | {'real': 664} | 0 | - |
| cost_center | TEXT | {'text': 664} | 0 | - |
| budget_activity | TEXT | {'text': 664} | 0 | - |
| keterangan | TEXT | {'text': 664} | 0 | - |
| created_at | TEXT | {'text': 664} | 0 | {'YYYY-MM-DD HH:MM:SS': 664} |
| updated_at | TEXT | {'null': 664} | 664 | - |
| vendor | TEXT | {'text': 664} | 0 | - |
| others | REAL | {'real': 664} | 0 | - |
| klasifikasi_pam | TEXT | {'null': 664} | 664 | - |

### payment_application

| Kolom | Deklarasi | Jenis | Null | Format tanggal |
|---|---|---|---|---|
| id | INTEGER | {} | 0 | - |
| company_id | INTEGER | {} | 0 | - |
| memo_id | INTEGER | {} | 0 | - |
| application_number | TEXT | {} | 0 | - |
| submitted_at | TEXT | {} | 0 | - |
| target_payment_date | TEXT | {} | 0 | - |
| actual_payment_date | TEXT | {} | 0 | - |
| status | TEXT | {} | 0 | - |
| tat_days | INTEGER | {} | 0 | - |
| notes | TEXT | {} | 0 | - |
| created_at | TEXT | {} | 0 | - |

### payment_beasiswa

| Kolom | Deklarasi | Jenis | Null | Format tanggal |
|---|---|---|---|---|
| id | INTEGER | {'integer': 10085} | 0 | - |
| company_id | INTEGER | {'integer': 10085} | 0 | - |
| siswa_code | TEXT | {'text': 10085} | 0 | - |
| cat1 | TEXT | {'text': 10085} | 0 | - |
| cat2 | TEXT | {'text': 10085} | 0 | - |
| tanggal | TEXT | {'text': 10085} | 0 | {'YYYY-MM-DD': 10085} |
| amount | REAL | {'real': 10085} | 0 | - |
| pillar | TEXT | {'text': 10085} | 0 | - |
| pam | TEXT | {'null': 3228, 'text': 6857} | 3228 | - |
| perusahaan | TEXT | {'null': 9182, 'text': 903} | 9182 | - |
| cat3 | TEXT | {'null': 9659, 'text': 426} | 9659 | - |
| cat4 | TEXT | {'null': 9662, 'text': 423} | 9662 | - |
| memo_id | INTEGER | {'null': 10085} | 10085 | - |
| status | TEXT | {'text': 10085} | 0 | - |
| created_at | TEXT | {'null': 16, 'text': 10069} | 16 | {'YYYY-MM-DD': 9627, 'YYYY-MM-DD HH:MM:SS': 442} |
| tgl_pengajuan | TEXT | {'null': 9306, 'text': 779} | 9306 | {'YYYY-MM-DD': 779} |
| tgl_receive | TEXT | {'null': 9308, 'text': 777} | 9308 | {'YYYY-MM-DD': 777} |
| tgl_pa | TEXT | {'null': 9308, 'text': 777} | 9308 | {'YYYY-MM-DD': 777} |
| tgl_final | TEXT | {'null': 9308, 'text': 777} | 9308 | {'YYYY-MM-DD': 777} |
| tgl_retur | TEXT | {'null': 10084, 'text': 1} | 10084 | {'YYYY-MM-DD': 1} |
| tgl_final6 | TEXT | {'null': 9863, 'text': 222} | 9863 | {'YYYY-MM-DD': 222} |
| tgl_proses | TEXT | {'null': 9863, 'text': 222} | 9863 | {'YYYY-MM-DD': 222} |
| SLA_Date_2_HT | TEXT | {'null': 9865, 'text': 220} | 9865 | {'YYYY-MM-DD': 220} |
| SLA_Date_3_YK | TEXT | {'null': 10061, 'text': 24} | 10061 | {'YYYY-MM-DD': 24} |
| SLA_Date_4_AK | TEXT | {'null': 10085} | 10085 | - |
| SLA_Date_5_PD | TEXT | {'null': 10085} | 10085 | - |
| SLA_Date_6_C2 | TEXT | {'null': 10081, 'text': 4} | 10081 | {'YYYY-MM-DD': 4} |
| SLA_Date_7_MSIG | TEXT | {'null': 10085} | 10085 | - |
| tgl_A-GS_APP | TEXT | {'null': 10085} | 10085 | - |
| tgl_A-HJK_APP | TEXT | {'null': 10085} | 10085 | - |
| tgl_ASPIRO_APP | TEXT | {'null': 10085} | 10085 | - |
| tgl_Paid_APP | TEXT | {'null': 10017, 'text': 68} | 10017 | {'YYYY-MM-DD': 68} |
| etf_pa_line_id | INTEGER | {'integer': 481, 'null': 9604} | 9604 | - |
| tgl_Paid_LAND | TEXT | {'null': 10085} | 10085 | - |
| tgl_Paid_ENERGY | TEXT | {'null': 10085} | 10085 | - |
| tgl_Paid_SETF | TEXT | {'null': 10057, 'text': 28} | 10057 | {'YYYY-MM-DD': 28} |
| SLA_Date_1_LL | TEXT | {'null': 10085} | 10085 | - |
| advance_amount | REAL | {'null': 10085} | 10085 | - |
| realized_amount | REAL | {'null': 10085} | 10085 | - |
| tgl_realisasi | TEXT | {'null': 10085} | 10085 | - |
| reject_reason | TEXT | {'null': 10085} | 10085 | - |
| klasifikasi_pam | TEXT | {'null': 10080, 'text': 5} | 10080 | - |
| klasifikasi_pa | TEXT | {'text': 10085} | 0 | - |

### payment_memo

| Kolom | Deklarasi | Jenis | Null | Format tanggal |
|---|---|---|---|---|
| id | INTEGER | {} | 0 | - |
| company_id | INTEGER | {} | 0 | - |
| memo_number | TEXT | {} | 0 | - |
| tanggal | TEXT | {} | 0 | - |
| total_amount | REAL | {} | 0 | - |
| status | TEXT | {} | 0 | - |
| notes | TEXT | {} | 0 | - |
| created_by | TEXT | {} | 0 | - |
| approved_by | TEXT | {} | 0 | - |
| approved_at | TEXT | {} | 0 | - |
| created_at | TEXT | {} | 0 | - |
| updated_at | TEXT | {} | 0 | - |
| tanggal_bayar | TEXT | {} | 0 | - |

### payment_memo_items

| Kolom | Deklarasi | Jenis | Null | Format tanggal |
|---|---|---|---|---|
| id | INTEGER | {} | 0 | - |
| memo_id | INTEGER | {} | 0 | - |
| source_module | TEXT | {} | 0 | - |
| source_id | INTEGER | {} | 0 | - |
| description | TEXT | {} | 0 | - |
| amount | REAL | {} | 0 | - |
| vendor | TEXT | {} | 0 | - |
| bank_account | TEXT | {} | 0 | - |

### refresh_tokens

| Kolom | Deklarasi | Jenis | Null | Format tanggal |
|---|---|---|---|---|
| id | INTEGER | {'integer': 1706} | 0 | - |
| user_id | INTEGER | {'integer': 1706} | 0 | - |
| token_hash | TEXT | {'text': 1706} | 0 | - |
| expires_at | TEXT | {'text': 1706} | 0 | {'YYYY-MM-DD HH:MM:SS': 1706} |
| revoked | INTEGER | {'integer': 1706} | 0 | - |
| created_at | TEXT | {'text': 1706} | 0 | {'YYYY-MM-DD HH:MM:SS': 1706} |

### rekam_medis

| Kolom | Deklarasi | Jenis | Null | Format tanggal |
|---|---|---|---|---|
| id | INTEGER | {} | 0 | - |
| company_id | INTEGER | {} | 0 | - |
| payment_id | INTEGER | {} | 0 | - |
| siswa_code | TEXT | {} | 0 | - |
| kelas | TEXT | {} | 0 | - |
| rumah_sakit | TEXT | {} | 0 | - |
| diagnosa | TEXT | {} | 0 | - |
| spesialisasi | TEXT | {} | 0 | - |
| catatan | TEXT | {} | 0 | - |
| created_at | TEXT | {} | 0 | - |

### setf_pa

| Kolom | Deklarasi | Jenis | Null | Format tanggal |
|---|---|---|---|---|
| id | INTEGER | {'integer': 29} | 0 | - |
| company_id | INTEGER | {'integer': 29} | 0 | - |
| pa_number | TEXT | {'text': 29} | 0 | - |
| tgl_payment_application | TEXT | {'text': 29} | 0 | {'YYYY-MM-DD': 29} |
| tgl_surat_pengajuan | TEXT | {'text': 29} | 0 | {'YYYY-MM-DD': 29} |
| doc_received_by_educ | TEXT | {'null': 13, 'text': 16} | 13 | {'empty': 6, 'YYYY-MM-DD': 10} |
| received_pa_from_educ | TEXT | {'null': 13, 'text': 16} | 13 | {'empty': 6, 'YYYY-MM-DD': 10} |
| checked_by_fincon | TEXT | {'null': 13, 'text': 16} | 13 | {'empty': 7, 'YYYY-MM-DD': 9} |
| approved_by_htj_1 | TEXT | {'null': 13, 'text': 16} | 13 | {'empty': 7, 'YYYY-MM-DD': 9} |
| send_pa_back_to_educ | TEXT | {'null': 13, 'text': 16} | 13 | {'empty': 7, 'YYYY-MM-DD': 9} |
| pa_received_by_po_fin | TEXT | {'null': 10, 'text': 19} | 10 | {'empty': 10, 'YYYY-MM-DD': 9} |
| approval_by_htj_2 | TEXT | {'null': 15, 'text': 14} | 15 | - |
| nomor_pam | TEXT | {'text': 29} | 0 | - |
| tanggal_bayar | TEXT | {'text': 29} | 0 | {'YYYY-MM-DD': 29} |
| keterangan | TEXT | {'null': 1, 'text': 28} | 1 | - |
| status | TEXT | {'text': 29} | 0 | - |
| created_at | TEXT | {'text': 29} | 0 | {'YYYY-MM-DD HH:MM:SS': 29} |
| updated_at | TEXT | {'null': 13, 'text': 16} | 13 | {'YYYY-MM-DD HH:MM:SS': 16} |
| route | TEXT | {'text': 29} | 0 | - |
| reject_reason | TEXT | {'null': 29} | 29 | - |
| attachment_file_id | TEXT | {'null': 25, 'text': 4} | 25 | - |
| klasifikasi | TEXT | {'text': 29} | 0 | - |

### setf_pa_lines

| Kolom | Deklarasi | Jenis | Null | Format tanggal |
|---|---|---|---|---|
| id | INTEGER | {'integer': 31} | 0 | - |
| pa_id | INTEGER | {'integer': 31} | 0 | - |
| student_id | INTEGER | {'integer': 31} | 0 | - |
| jenis_pembayaran | TEXT | {'text': 31} | 0 | - |
| semester | TEXT | {'null': 3, 'text': 28} | 3 | - |
| tahun_ajaran | TEXT | {'null': 7, 'text': 24} | 7 | - |
| ipk_sem_sebelumnya | REAL | {'real': 31} | 0 | - |
| jumlah_pembayaran | REAL | {'real': 31} | 0 | - |
| route | TEXT | {'null': 2, 'text': 29} | 2 | - |

### setf_pam_lines

| Kolom | Deklarasi | Jenis | Null | Format tanggal |
|---|---|---|---|---|
| id | INTEGER | {} | 0 | - |
| pam_id | INTEGER | {} | 0 | - |
| no_vendor | TEXT | {} | 0 | - |
| nama_vendor | TEXT | {} | 0 | - |
| tgl_terima_doc | TEXT | {} | 0 | - |
| tgl_proses | TEXT | {} | 0 | - |
| tgl_verifikasi_tax | TEXT | {} | 0 | - |
| tgl_approval_1 | TEXT | {} | 0 | - |
| tgl_approval_2 | TEXT | {} | 0 | - |
| tgl_approval_3 | TEXT | {} | 0 | - |
| tgl_kirim | TEXT | {} | 0 | - |
| created_at | TEXT | {} | 0 | - |
| updated_at | TEXT | {} | 0 | - |

### siswa

| Kolom | Deklarasi | Jenis | Null | Format tanggal |
|---|---|---|---|---|
| id | INTEGER | {'integer': 1521} | 0 | - |
| company_id | INTEGER | {'integer': 1521} | 0 | - |
| code | TEXT | {'text': 1521} | 0 | - |
| nama | TEXT | {'text': 1521} | 0 | - |
| jenjang | TEXT | {'text': 1521} | 0 | - |
| angkatan | INTEGER | {'integer': 1521} | 0 | - |
| program | TEXT | {'text': 1521} | 0 | - |
| fakultas | TEXT | {'text': 1521} | 0 | - |
| universitas | TEXT | {'text': 1521} | 0 | - |
| bank | TEXT | {'text': 1521} | 0 | - |
| norek | TEXT | {'text': 1521} | 0 | - |
| namarek | TEXT | {'text': 1521} | 0 | - |
| referensi | TEXT | {'text': 1521} | 0 | - |
| ipk_sem1 | REAL | {'real': 1521} | 0 | - |
| ipk_sem2 | REAL | {'real': 1521} | 0 | - |
| ipk_sem3 | REAL | {'real': 1521} | 0 | - |
| ipk_sem4 | REAL | {'real': 1521} | 0 | - |
| ipk_sem5 | REAL | {'real': 1521} | 0 | - |
| ipk_sem6 | REAL | {'real': 1521} | 0 | - |
| ipk_sem7 | REAL | {'real': 1521} | 0 | - |
| ipk_sem8 | REAL | {'real': 1521} | 0 | - |
| ipk_sem9 | REAL | {'real': 1521} | 0 | - |
| ipk_sem10 | REAL | {'real': 1521} | 0 | - |
| ipk_pen1 | REAL | {'real': 1521} | 0 | - |
| ipk_pen2 | REAL | {'real': 1521} | 0 | - |
| ipk_pen3 | REAL | {'real': 1521} | 0 | - |
| status | TEXT | {'text': 1521} | 0 | - |
| catatan | TEXT | {'text': 1521} | 0 | - |
| created_at | TEXT | {'text': 1521} | 0 | {'YYYY-MM-DD HH:MM:SS': 1521} |
| updated_at | TEXT | {'null': 208, 'text': 1313} | 208 | {'empty': 1087, 'YYYY-MM-DD HH:MM:SS': 226} |
| catatan_budget | TEXT | {'text': 1521} | 0 | - |
| catatan_payment | TEXT | {'text': 1521} | 0 | - |
| angkatan_kuliah | TEXT | {'text': 1521} | 0 | - |
| prodi | TEXT | {'text': 1521} | 0 | - |
| region | TEXT | {'text': 1521} | 0 | - |
| country | TEXT | {'text': 1521} | 0 | - |
| group_setf | TEXT | {'null': 1184, 'text': 337} | 1184 | - |
| tanggal_lahir | TEXT | {'text': 1521} | 0 | {'empty': 1356, 'YYYY-MM-DD': 164, 'DD/MM/YYYY': 1} |

### sml_pa

| Kolom | Deklarasi | Jenis | Null | Format tanggal |
|---|---|---|---|---|
| id | INTEGER | {'integer': 36} | 0 | - |
| company_id | INTEGER | {'integer': 36} | 0 | - |
| pa_number | TEXT | {'text': 36} | 0 | - |
| tgl_payment_application | TEXT | {'null': 1, 'text': 35} | 1 | {'YYYY-MM-DD': 35} |
| tgl_surat_pengajuan | TEXT | {'text': 36} | 0 | {'YYYY-MM-DD': 36} |
| doc_received_by_educ | TEXT | {'text': 36} | 0 | {'YYYY-MM-DD': 36} |
| received_pa_from_educ | TEXT | {'text': 36} | 0 | {'YYYY-MM-DD': 36} |
| checked_by_fincon | TEXT | {'text': 36} | 0 | {'YYYY-MM-DD': 36} |
| approved_by_htj_1 | TEXT | {'text': 36} | 0 | {'YYYY-MM-DD': 36} |
| send_pa_back_to_educ | TEXT | {'text': 36} | 0 | {'YYYY-MM-DD': 36} |
| pa_received_by_po_fin | TEXT | {'null': 9, 'text': 27} | 9 | {'YYYY-MM-DD': 27} |
| approval_by_htj_2 | TEXT | {'null': 9, 'text': 27} | 9 | {'YYYY-MM-DD': 27} |
| nomor_pam | TEXT | {'null': 8, 'text': 28} | 8 | - |
| tanggal_bayar | TEXT | {'null': 21, 'text': 15} | 21 | {'empty': 11, 'YYYY-MM-DD': 4} |
| keterangan | TEXT | {'text': 36} | 0 | - |
| status | TEXT | {'text': 36} | 0 | - |
| created_at | TEXT | {'text': 36} | 0 | {'YYYY-MM-DD HH:MM:SS': 36} |
| updated_at | TEXT | {'null': 18, 'text': 18} | 18 | {'YYYY-MM-DD HH:MM:SS': 18} |
| no_pa | TEXT | {'null': 36} | 36 | - |
| category | TEXT | {'null': 36} | 36 | - |
| categori_1 | TEXT | {'null': 36} | 36 | - |
| nomor_vendor | TEXT | {'null': 36} | 36 | - |
| nama_vendor | TEXT | {'null': 36} | 36 | - |
| mata_uang | TEXT | {'text': 36} | 0 | - |
| dpp | INTEGER | {'integer': 36} | 0 | - |
| ppn | INTEGER | {'integer': 36} | 0 | - |
| total | INTEGER | {'integer': 36} | 0 | - |
| terima_document | TEXT | {'null': 36} | 36 | - |
| input_aspiro | TEXT | {'null': 36} | 36 | - |
| verifikasi_tax | TEXT | {'null': 36} | 36 | - |
| approval_1 | TEXT | {'null': 36} | 36 | - |
| approval_2 | TEXT | {'null': 36} | 36 | - |
| approval_3 | TEXT | {'null': 36} | 36 | - |
| kirim_aspiro | TEXT | {'null': 36} | 36 | - |
| paid | TEXT | {'null': 36} | 36 | - |
| route | TEXT | {'text': 36} | 0 | - |
| reject_reason | TEXT | {'null': 35, 'text': 1} | 35 | - |
| attachment_file_id | TEXT | {'null': 31, 'text': 5} | 31 | - |
| klasifikasi | TEXT | {'text': 36} | 0 | - |

### sml_pa_lines

| Kolom | Deklarasi | Jenis | Null | Format tanggal |
|---|---|---|---|---|
| id | INTEGER | {'integer': 37} | 0 | - |
| pa_id | INTEGER | {'integer': 37} | 0 | - |
| student_id | INTEGER | {'integer': 37} | 0 | - |
| jenis_pembayaran | TEXT | {'text': 37} | 0 | - |
| semester | TEXT | {'text': 37} | 0 | - |
| tahun_ajaran | TEXT | {'text': 37} | 0 | - |
| ipk_sem_sebelumnya | REAL | {'real': 37} | 0 | - |
| jumlah_pembayaran | INTEGER | {'integer': 37} | 0 | - |
| route | TEXT | {'null': 19, 'text': 18} | 19 | - |

### sml_pa_vendor

| Kolom | Deklarasi | Jenis | Null | Format tanggal |
|---|---|---|---|---|
| id | INTEGER | {} | 0 | - |
| no_pa | TEXT | {} | 0 | - |
| category | TEXT | {} | 0 | - |
| keterangan | TEXT | {} | 0 | - |
| categori_1 | TEXT | {} | 0 | - |
| nomor_vendor | TEXT | {} | 0 | - |
| nama_vendor | TEXT | {} | 0 | - |
| mata_uang | TEXT | {} | 0 | - |
| dpp | INTEGER | {} | 0 | - |
| ppn | INTEGER | {} | 0 | - |
| total | INTEGER | {} | 0 | - |
| terima_document | TEXT | {} | 0 | - |
| input_aspiro | TEXT | {} | 0 | - |
| verifikasi_tax | TEXT | {} | 0 | - |
| approval_1 | TEXT | {} | 0 | - |
| approval_2 | TEXT | {} | 0 | - |
| approval_3 | TEXT | {} | 0 | - |
| kirim_aspiro | TEXT | {} | 0 | - |
| paid | TEXT | {} | 0 | - |
| created_at | TEXT | {} | 0 | - |
| status | TEXT | {} | 0 | - |

### smt_pam_lines

| Kolom | Deklarasi | Jenis | Null | Format tanggal |
|---|---|---|---|---|
| id | INTEGER | {'integer': 507} | 0 | - |
| pam_id | INTEGER | {'integer': 507} | 0 | - |
| no_vendor | TEXT | {'null': 507} | 507 | - |
| nama_vendor | TEXT | {'null': 507} | 507 | - |
| tgl_terima_doc | TEXT | {'null': 507} | 507 | - |
| tgl_proses | TEXT | {'null': 507} | 507 | - |
| tgl_verifikasi_tax | TEXT | {'null': 507} | 507 | - |
| tgl_approval_1 | TEXT | {'null': 507} | 507 | - |
| tgl_approval_2 | TEXT | {'null': 507} | 507 | - |
| tgl_approval_3 | TEXT | {'null': 507} | 507 | - |
| tgl_kirim | TEXT | {'null': 507} | 507 | - |
| tgl_realisasi | TEXT | {'null': 507} | 507 | - |
| created_at | TEXT | {'text': 507} | 0 | {'YYYY-MM-DD HH:MM:SS': 507} |
| updated_at | TEXT | {'null': 507} | 507 | - |
| tgl_received | TEXT | {'text': 507} | 0 | {'YYYY-MM-DD': 507} |
| tgl_a0 | TEXT | {'null': 4, 'text': 503} | 4 | {'YYYY-MM-DD': 503} |
| tgl_a1 | TEXT | {'null': 4, 'text': 503} | 4 | {'YYYY-MM-DD': 503} |
| tgl_a2 | TEXT | {'null': 4, 'text': 503} | 4 | {'YYYY-MM-DD': 503} |
| tgl_a3 | TEXT | {'null': 7, 'text': 500} | 7 | {'YYYY-MM-DD': 500} |
| tgl_a4 | TEXT | {'null': 8, 'text': 499} | 8 | {'YYYY-MM-DD': 499} |
| tgl_paid | TEXT | {'null': 507} | 507 | - |

### sop_documents

| Kolom | Deklarasi | Jenis | Null | Format tanggal |
|---|---|---|---|---|
| id | INTEGER | {'integer': 65} | 0 | - |
| modul | TEXT | {'text': 65} | 0 | - |
| kode | TEXT | {'null': 8, 'text': 57} | 8 | - |
| nama | TEXT | {'text': 65} | 0 | - |
| status | TEXT | {'text': 65} | 0 | - |
| perlu_verifikasi_count | INTEGER | {'integer': 65} | 0 | - |
| file_path | TEXT | {'null': 8, 'text': 57} | 8 | - |
| catatan | TEXT | {'null': 57, 'text': 8} | 57 | - |
| uploaded_by | TEXT | {'null': 65} | 65 | - |
| uploaded_at | TEXT | {'null': 65} | 65 | - |
| created_at | TEXT | {'text': 65} | 0 | {'YYYY-MM-DD HH:MM:SS': 65} |

### sop_upload_history

| Kolom | Deklarasi | Jenis | Null | Format tanggal |
|---|---|---|---|---|
| id | INTEGER | {} | 0 | - |
| sop_id | INTEGER | {} | 0 | - |
| uploaded_by | TEXT | {} | 0 | - |
| uploaded_at | TEXT | {} | 0 | - |
| catatan | TEXT | {} | 0 | - |

### sponsorship_perusahaan

| Kolom | Deklarasi | Jenis | Null | Format tanggal |
|---|---|---|---|---|
| cat1 | TEXT | {'text': 59} | 0 | - |
| cat2 | TEXT | {'text': 59} | 0 | - |
| cat3 | TEXT | {'text': 59} | 0 | - |

### sponsorship_transaksi

| Kolom | Deklarasi | Jenis | Null | Format tanggal |
|---|---|---|---|---|
| id | INTEGER | {'integer': 1039} | 0 | - |
| company_id | INTEGER | {'integer': 1039} | 0 | - |
| cat | TEXT | {'text': 1039} | 0 | - |
| description | TEXT | {'text': 1039} | 0 | - |
| tanggal_form_sponsor | TEXT | {'text': 1039} | 0 | {'YYYY-MM-DD': 1039} |
| tanggal_payment | TEXT | {'null': 233, 'text': 806} | 233 | {'empty': 8, 'other': 27, 'YYYY-MM-DD': 771} |
| cat1 | TEXT | {'text': 1039} | 0 | - |
| cat2 | TEXT | {'text': 1039} | 0 | - |
| cat3 | TEXT | {'text': 1039} | 0 | - |
| lembaga_perorangan | TEXT | {'text': 1039} | 0 | - |
| perihal | TEXT | {'null': 1, 'text': 1038} | 1 | - |
| amount_request | REAL | {'real': 1039} | 0 | - |
| reff | TEXT | {'null': 875, 'text': 164} | 875 | - |
| status | TEXT | {'null': 781, 'text': 258} | 781 | - |
| cat4 | TEXT | {'text': 1039} | 0 | - |
| coa | TEXT | {'text': 1039} | 0 | - |
| cc_total | TEXT | {'text': 1039} | 0 | - |
| cc | TEXT | {'text': 1039} | 0 | - |
| source | TEXT | {'text': 1039} | 0 | - |
| created_at | TEXT | {'text': 1039} | 0 | {'YYYY-MM-DD HH:MM:SS': 1039} |
| updated_at | TEXT | {'null': 1014, 'text': 25} | 1014 | {'YYYY-MM-DD HH:MM:SS': 25} |

### users

| Kolom | Deklarasi | Jenis | Null | Format tanggal |
|---|---|---|---|---|
| id | INTEGER | {'integer': 8} | 0 | - |
| username | TEXT | {'text': 8} | 0 | - |
| password_hash | TEXT | {'text': 8} | 0 | - |
| role | TEXT | {'text': 8} | 0 | - |
| is_active | INTEGER | {'integer': 8} | 0 | - |
| must_change_pw | INTEGER | {'integer': 8} | 0 | - |
| created_at | TEXT | {'text': 8} | 0 | {'YYYY-MM-DD HH:MM:SS': 8} |
| last_login | TEXT | {'null': 1, 'text': 7} | 1 | {'YYYY-MM-DD HH:MM:SS': 7} |

### vendors

| Kolom | Deklarasi | Jenis | Null | Format tanggal |
|---|---|---|---|---|
| id | INTEGER | {'integer': 611} | 0 | - |
| name | TEXT | {'text': 611} | 0 | - |
| pillar | TEXT | {'text': 611} | 0 | - |
| cost_center | TEXT | {'text': 611} | 0 | - |
| Bank_Account_Name | TEXT | {'text': 611} | 0 | - |
| Bank_Name | TEXT | {'text': 611} | 0 | - |
| Bank_Account_Number | TEXT | {'text': 611} | 0 | - |
| Swift_Code | TEXT | {'text': 611} | 0 | - |

