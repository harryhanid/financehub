# Design: Excel Import Script untuk PAM AGRI & Open PAM

**Date:** 2026-06-17
**Status:** Approved
**Scope:** Script Python standalone untuk sync perubahan Excel → SQLite (satu arah)

---

## Latar Belakang

User melakukan export data dari tab **Open PAM** dan **AGRI** di modul Payment Approval Memo,
mengedit langsung di Excel (update status, tanggal paid, PAM No, perusahaan; hapus baris),
lalu ingin sync perubahan itu kembali ke SQLite dan tampilan app.

---

## Tabel yang Terlibat

| File Excel | Tabel Utama | Tabel Cascade |
|------------|-------------|---------------|
| `PAM_AGRI_*.xlsx` | `pam_records` | `payment_beasiswa`, `etf_pa`, `app_pa`, `sml_pa`, `setf_pa` |
| `Open_PAM_*.xlsx` | `payment_beasiswa` | — |

---

## Script

**File:** `tmp_import_excel.py` (di root project, bukan bagian modul permanen)

**Mode run:**
```
python tmp_import_excel.py            # dry-run — tampilkan diff, tidak ada yang berubah
python tmp_import_excel.py --apply    # apply semua perubahan ke SQLite
```

---

## Flow

```
1. Backup DB → finance_hub.db.bak_import_YYYYMMDD_HHMMSS
2. Baca PAM_AGRI Excel  → process_pam_agri(dry_run)
3. Baca Open_PAM Excel  → process_open_pam(dry_run)
4. Tampilkan ringkasan (update/rename/delete/skip per tabel)
5. Jika --apply: jalankan semua dalam 1 DB transaction (rollback jika error)
```

Path Excel hardcoded di konstanta di atas script:
```python
PAM_AGRI_FILE = r"C:\Users\25010160\Downloads\PAM_AGRI_20260617_1111.xlsx"
OPEN_PAM_FILE = r"C:\Users\25010160\Downloads\Open_PAM_20260617_1111.xlsx"
```

---

## PAM AGRI — `pam_records`

### Matching Key
**PAM No** (kolom `pam_no`) — primary identifier.

### Operasi

| Kondisi | Aksi | Detail |
|---------|------|--------|
| PAM No ada di Excel & DB, field berubah | **UPDATE** | Update `status`, `tanggal_bayar` |
| PAM No di Excel tidak ada di DB, tapi `pam_date` + `total_amount` cocok dengan DB row yang "hilang" | **RENAME** | Update `pam_no` + cascade ke `payment_beasiswa.pam`, `etf_pa/app_pa/sml_pa/setf_pa.nomor_pam` |
| PAM No ada di DB tapi **tidak ada di Excel** (baris dihapus user) | **DELETE** | Panggil `cancel_pam_record()` — revert PA ke open, bersihkan `payment_beasiswa` |
| PAM No di Excel tidak ada di DB & tidak ada auto-detect rename | **SKIP + warning** | Ditampilkan ke user, tidak diproses |

### Field yang Di-update dari Excel
| Kolom Excel | Field DB | Catatan |
|-------------|----------|---------|
| `Status` | `pam_records.status` | Nilai: open / on_process / complete |
| `Tgl Paid` | `pam_records.tanggal_bayar` | Di-update apa adanya dari Excel; status ikut kolom Status |
| `PAM No` | `pam_records.pam_no` | Hanya jika terdeteksi sebagai rename |

### Auto-detect Rename
Jika PAM No di Excel tidak ada di DB, cari DB row yang:
- `pam_date` sama
- `total_amount` sama (toleransi ±0.01 untuk float)
- Tidak ada di Excel (candidate "deleted")

Jika ditemukan tepat 1 match → treat sebagai **RENAME**.
Jika ditemukan >1 atau 0 → **SKIP + warning**, user handle manual via app.

---

## Open PAM — `payment_beasiswa`

### Matching Key
Composite: **(siswa_code, cat1, cat2, tanggal, amount)**
(field `id` tidak di-export, jadi matching pakai kombinasi 5 field ini)

### Operasi

| Kondisi | Aksi |
|---------|------|
| Match ditemukan, field berubah | **UPDATE** `pam`, `perusahaan`, `status` |
| Ada di DB tapi **tidak ada di Excel** | **DELETE** via `DELETE FROM payment_beasiswa WHERE id=?` |
| Tidak ada match di DB | **SKIP + warning** |

### Field yang Di-update dari Excel
| Kolom Excel | Field DB |
|-------------|----------|
| `PAM No` | `payment_beasiswa.pam` |
| `Perusahaan` | `payment_beasiswa.perusahaan` |
| `Status` | `payment_beasiswa.status` |

---

## Dry-run Output Format

```
============================================================
DRY-RUN MODE — tidak ada perubahan yang disimpan
============================================================

=== PAM AGRI (pam_records) ===
[UPDATE]  PAM-057-ETF-06-2026         status: on_process → complete | tgl_paid: 2026-06-15
[RENAME]  PAM-057-AGRI-06-2026     →  PAM-057-ETF-06-2026 (cascade 4 tabel)
[DELETE]  PAM-002-APP-06-2026         (3 payment_beasiswa di-revert ke open)
[SKIP ⚠] PAM-099-ETF-06-2025         → tidak ditemukan di DB, tidak bisa di-match

=== OPEN PAM (payment_beasiswa) ===
[UPDATE]  2250234 | By Tunjangan | 2026-06-15 : pam=PAM-057-ETF, status=on_process
[DELETE]  4240012 | By Tunjangan | 2026-06-15

------------------------------------------------------------
Ringkasan:
  pam_records  : 1 update, 1 rename, 1 delete, 1 skip
  payment_beasiswa: 1 update, 1 delete

Jalankan dengan --apply untuk menerapkan perubahan.
============================================================
```

---

## Safety

- **Backup wajib** sebelum apply — file `.bak_import_YYYYMMDD_HHMMSS`
- Semua operasi dalam **satu transaction** — jika error di tengah jalan, rollback total
- Dry-run tidak menyentuh DB sama sekali
- SKIP rows tidak dihapus/diubah — hanya dilaporkan
- Cascade delete pakai `cancel_pam_record()` yang sudah ada (tested)
- Cascade rename pakai `update_pam_and_application()` yang sudah ada (tested)

---

## Batasan (Out of Scope)

- Tidak menambah record baru ke DB (insert)
- Tidak sync balik APP-specific (`fiori_pa`) atau LAND-specific (`sml_pa`) dari file ini
- Tidak ada UI di app — script terminal saja
- Tidak handle jika user me-rename PAM No yang sudah pernah di-rename sebelumnya (multi-hop rename)
