# Audit: Mark Complete Cascade di Open PAM

**Tanggal:** 2026-06-22  
**Scope:** Alur `bulk_complete_pams` → `set_pam_tanggal_bayar_agri` — apakah semua tabel terdampak ter-update dengan benar saat user mark complete di tab Open PAM?

---

## 1. Alur Lengkap

```
[UI] submitOpenPamPaid()
  → POST /payment-memo/open-pam/mark-complete
  → open_pam_mark_complete()  [routes.py]
  → bulk_complete_pams(company_id, pams, tanggal_bayar)  [service.py:1815]
      for each pam_no in pams:
          row = SELECT id FROM pam_records WHERE pam_no=?
          if row:
              set_pam_tanggal_bayar_agri(row.id, tanggal_bayar, company_id)
```

### `set_pam_tanggal_bayar_agri` (service.py:1831)

```
Step 1:  UPDATE pam_records
         SET tanggal_bayar=?, status='complete'
         WHERE id=?
                                                ← berlaku untuk SEMUA source

Step 2:  IF source == 'etf_agri':
           UPDATE etf_pa
           SET tanggal_bayar=?, status='complete'
           WHERE nomor_pam=? AND company_id=?
                                                ← hanya untuk AGRI ETF PA-only flow

Step 3:  ELSE:
           UPDATE payment_beasiswa
           SET status='complete'
           WHERE pam=? AND company_id=?

           line_ids = SELECT DISTINCT etf_pa_line_id
                      FROM payment_beasiswa
                      WHERE pam=? AND etf_pa_line_id IS NOT NULL

           IF line_ids:
             for (lines_tbl, pa_tbl) in all 5 pillars:
               UPDATE {pa_tbl}
               SET tanggal_bayar=?, status='complete'
               WHERE id IN (
                 SELECT pa_id FROM {lines_tbl}
                 WHERE id IN (line_ids)
               ) AND company_id=?
                                                ← untuk beasiswa iPay flow
```

---

## 2. Status Per Tabel

| Tabel | Diupdate? | Kondisi |
|---|---|---|
| `pam_records` | ✅ Selalu | `tanggal_bayar` + `status='complete'` |
| `payment_beasiswa` | ✅ Ya | Hanya jika `source != 'etf_agri'`; field `status='complete'` saja (tidak ada kolom `tanggal_bayar`) |
| `etf_pa` | ✅ Ya (2 jalur) | Jalur 1: source='etf_agri' via `nomor_pam`. Jalur 2: beasiswa iPay via `etf_pa_line_id` |
| `app_pa` | ✅ Conditional | Hanya jika beasiswa iPay dan `etf_pa_line_id` diisi |
| `sml_pa` | ✅ Conditional | Sama |
| `energy_pa` | ✅ Conditional | Sama |
| `setf_pa` | ✅ Conditional | Sama |

---

## 3. Gap yang Ditemukan

### Gap 1 — "Others" PAMs tidak tampil di Open PAM (MEDIUM)

**Root cause:** `get_draft_payments` hanya query `payment_beasiswa WHERE status='open'`. PAM dari flow `tagihan`/`sponsor`/`save_others_payment` hanya membuat entri di `pam_records`, **tanpa** baris di `payment_beasiswa`. Akibatnya, PAM jenis ini tidak pernah muncul di accordion Open PAM.

**Dampak:** User tidak bisa mark-complete PAM jenis "others" dari tab Open PAM. Mereka harus manage via masing-masing tab pillar (AGRI/APP/LAND/ENERGY/SETF).

**Status:** Perilaku ini mungkin disengaja (flow yang berbeda). Perlu konfirmasi apakah jenis PAM ini harus bisa di-mark dari Open PAM.

---

### Gap 2 — Nama fungsi menyesatkan (LOW)

`set_pam_tanggal_bayar_agri` dipanggil oleh `bulk_complete_pams` untuk **semua pillar**, tapi namanya mengindikasikan AGRI-only. Docstring-nya juga hanya menyebut source='etf_agri'.

**Dampak:** Confusion saat maintenance — developer berikutnya mungkin takut memanggil fungsi ini untuk non-AGRI.

**Fix yang disarankan:** Rename ke `set_pam_complete_cascade` dan update docstring.

---

### Gap 3 — Klaim Medis tidak cascade ke PA (EXPECTED)

Untuk PAM dengan source `klaim_medis`, `payment_beasiswa.etf_pa_line_id` bernilai NULL (klaim tidak berasal dari PA). Cascade ke PA tables tidak terjadi — ini **benar secara logika**.

**Status:** Tidak perlu diperbaiki.

---

### Gap 4 — Double-connection di `bulk_complete_pams` (LOW)

`bulk_complete_pams` membuka `conn` sendiri untuk SELECT, kemudian memanggil `set_pam_tanggal_bayar_agri` yang membuka `conn` baru untuk UPDATE. Dengan SQLite WAL mode, ini aman tapi kurang efisien.

**Dampak:** Minimal dalam praktek, tapi bisa jadi bottleneck saat batch besar (>20 PAMs).

---

## 4. Rekomendasi Fix

### Fix Prioritas Tinggi: None
Cascade saat ini sudah bekerja dengan benar untuk flow utama (beasiswa iPay semua pillar).

### Fix Prioritas Medium
1. **Gap 1** — Tentukan apakah "others" PAMs harus bisa di-mark dari Open PAM. Jika ya, tambahkan `pam_records`-only fallback di `get_draft_payments`.

### Fix Prioritas Low (cosmetic)
2. **Gap 2** — Rename fungsi + update docstring.
3. **Gap 4** — Refactor `bulk_complete_pams` agar reuse satu koneksi yang sama.

---

## 5. Kesimpulan

Cascade **sudah benar** untuk semua flow yang tampil di Open PAM (beasiswa iPay semua pillar + AGRI ETF). Tidak ada data loss atau silent skip pada happy path. Satu-satunya area yang perlu keputusan adalah apakah PAM tipe "others" perlu bisa di-mark dari Open PAM.
