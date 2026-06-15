# PAM Workflow Fix — Design Spec
**Date:** 2026-06-15  
**Status:** Approved

## Problem Statement

Tiga masalah pada alur pengajuan PAM (Payment Approval Memo) di modul Input:

1. **Double pam_records bug** — Submit sekali menghasilkan 2 entry di `pam_records`: entry pertama benar (auto-number, total correct), entry kedua salah (user pam_no, total=0). Root cause: `add_payment_multi()` di `beasiswa/service.py` sudah membuat pam_record secara internal, tapi `save_pa_payment()` di `payment_memo/service.py` membuat pam_record lagi karena return dict `add_payment_multi` tidak menyertakan `payment_ids` atau `total`.

2. **Prefix LAND salah** — `_IPAY_PAM_PREFIX["sml"] = "SML"` seharusnya `"LAND"`, sehingga nomor PAM yang di-generate untuk tab LAND masih memakai format lama `PAM-XXX-SML-MM-YYYY`.

3. **Regex frontend tidak sinkron** — `_PAM_RE = /^PAM-\d{3}-(AGRI|APP|SML|SETF)-\d{2}-\d{4}$/` tidak mencocokkan format aktual yang di-generate backend (`ETF|APP|LAND|SETF`).

Bonus:
- Race condition minor di `ipayOnTypeChange()` — memanggil `ipayFetchNextPamNo()` dua kali.
- Tidak ada button-disable sebelum API call di `ipaySavePa()`, memungkinkan double-click submit.

## Format Nomor PAM

| Tipe PAM (UI) | Tab value | Prefix | Contoh |
|---|---|---|---|
| AGRI | `agri` | `ETF` | `PAM-059-ETF-06-2026` |
| APP  | `app`  | `APP` | `PAM-059-APP-06-2026` |
| LAND | `sml`  | `LAND`| `PAM-059-LAND-06-2026` |
| SETF | `setf` | `SETF`| `PAM-059-SETF-06-2026` |

Sequence number diambil +1 dari max existing di `pam_records` untuk prefix + bulan + tahun yang sama. User boleh mengedit angka PAM sebelum submit (tidak dikunci); ada collision check on-blur.

## Solusi: Opsi A — Extract helper `insert_payment_rows()`

Pisahkan logic INSERT payment dari logic CREATE pam_record di `beasiswa/service.py`. Old flow tidak berubah.

## Perubahan

### 1. `app/modules/beasiswa/service.py`

**Tambah fungsi `insert_payment_rows(conn, company_id, company_code, tanggal, pillar, perusahaan, rows)`**

- Melakukan INSERT payment_beasiswa row-by-row
- Validasi rekam_medis untuk kategori "By Medical"
- Update PA status → `on_process` untuk PA yang direferensi
- Return `{"ok": bool, "payment_ids": list[int], "total": float, "pesan": str}`
- Tidak membuat pam_record, tidak commit — caller yang manage transaksi

**Refactor `add_payment_multi`** menjadi wrapper tipis:
1. Buka conn
2. Panggil `insert_payment_rows(conn, ...)`
3. Kumpulkan nama siswa untuk keterangan otomatis
4. Panggil `create_pam_record(conn, ...)` dengan total dan payment_ids
5. Update `nomor_pam` di PA tables
6. Commit, return seperti sekarang

Perilaku `/beasiswa/payment/tambah-multi` (old flow) **tidak berubah**.

### 2. `app/modules/payment_memo/service.py`

**Fix `_IPAY_PAM_PREFIX`:**
```python
_IPAY_PAM_PREFIX = {
    "agri":  "ETF",
    "app":   "APP",
    "sml":   "LAND",   # was "SML"
    "setf":  "SETF",
}
```

**Fix `save_pa_payment`:**
- Ganti pemanggilan `add_payment_multi` dengan `insert_payment_rows`
- Gunakan `payment_ids` dan `total` yang dikembalikan untuk:
  - `UPDATE payment_beasiswa SET pam=pam_no WHERE id IN (...)`
  - `INSERT pam_records (..., total_amount=total, ...)`
  - `UPDATE {pa_tbl} SET nomor_pam=?, status='on_process' WHERE ...`
- Satu transaksi — satu `conn`, satu `commit()`
- Hasil: **hanya 1 pam_record** per submit, total dan payment_ids benar

### 3. `app/templates/payment_memo/index.html`

| Item | Before | After |
|---|---|---|
| `_PAM_RE` regex | `/(AGRI\|APP\|SML\|SETF)/` | `/(ETF\|APP\|LAND\|SETF)/` |
| `ipayOnTypeChange()` | Calls `ipayFetchNextPamNo()` then `ipayReset()` (2x fetch) | Remove standalone call; `ipayReset()` alone sudah memanggil fetch |
| `ipaySavePa()` button guard | Tidak ada disable sebelum API call | `saveBtn.disabled = true` sebelum POST, re-enable di catch/finally |
| Format hint error msg | `PAM-054-AGRI-06-2026` | `PAM-054-ETF-06-2026` |

## Alur Setelah Fix

```
User pilih type AGRI + tanggal
  → GET /ipay/next-pam-no?tab=agri → "PAM-060-ETF-06-2026"
  → Field PAM terisi, bisa diedit bebas
  → On blur: collision check (warn jika sudah ada, tapi tidak dikunci)

User klik 💾 Simpan PAM AGRI
  → confirmModal
  → btn.disabled = true
  → Validasi: format PAM (ETF|APP|LAND|SETF), tanggal, perusahaan, rows
  → POST /payment-memo/ipay/save-pa
      → insert_payment_rows(conn) → {payment_ids:[5,6,7], total:15_000_000}
      → UPDATE payment_beasiswa SET pam="PAM-060-ETF-06-2026" WHERE id IN (5,6,7)
      → INSERT pam_records (pam_no, total=15_000_000, source="etf_agri")   ← 1 record saja
      → UPDATE etf_pa SET nomor_pam=..., status="on_process"
      → conn.commit()
  → toast "PAM PAM-060-ETF-06-2026 berhasil dibuat."
  → ipayReset() → redirect tab AGRI
```

## Test Coverage

- `test_pam_service.py` — tambah test: `save_pa_payment` hanya membuat 1 pam_record, total benar
- `test_payment_memo_service.py` — verifikasi `get_next_pam_no` tab "sml" menghasilkan prefix LAND
- Existing tests tidak berubah (old flow `add_payment_multi` tetap sama)

## Files yang Diubah

1. `app/modules/beasiswa/service.py`
2. `app/modules/payment_memo/service.py`
3. `app/templates/payment_memo/index.html`
4. `app/tests/test_pam_service.py` (tambah test cases)
