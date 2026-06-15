# PAM — Sort Baris berdasarkan Jenjang Studi

**Tanggal:** 2026-06-15  
**Modul:** `app/modules/payment_memo/`  
**Status:** Approved

---

## Latar Belakang

Saat ini baris siswa dalam tampilan PAM (form, Rangkuman, dan Detail) diurutkan berdasarkan `siswa_code` atau urutan insert database. Permintaan: baris harus diurutkan berdasarkan jenjang studi dari tertinggi ke terendah, dan dalam jenjang yang sama diurutkan berdasarkan total pembayaran terbesar terlebih dahulu.

---

## Urutan Sort yang Diinginkan

| Prioritas | Jenjang | Sort key |
|-----------|---------|----------|
| 1 | S3 | 0 |
| 2 | S2 | 1 |
| 3 | S1 | 2 |
| 4 | SD/SMP/SMA dan lainnya | 99 |

**Secondary sort:** total pembayaran DESC (dalam jenjang yang sama).

---

## Pendekatan: Sort di Python dalam service layer

Semua consumer (form display, PDF, Excel) memanggil dua fungsi yang sama:
- `get_pam_payments` → dipakai untuk Rangkuman PAM
- `get_pam_payments_detail` → dipakai untuk Detail PAM

Dengan men-sort di kedua fungsi ini, seluruh output otomatis konsisten tanpa perlu menyentuh `exports.py`, `routes.py`, atau template.

---

## Perubahan Detail

### File: `app/modules/payment_memo/service.py`

#### Konstanta baru

```python
_JENJANG_SORT = {"S3": 0, "S2": 1, "S1": 2}
```

Ditempatkan di dekat `_PILLAR_LINES_TABLE`. Nilai default untuk jenjang yang tidak terdaftar: `99`.

---

#### Fungsi: `get_pam_payments` (baris ~674)

**Perubahan SQL:** Tambah `s.jenjang` ke SELECT.

**Post-processing Python (setelah fetch):**
1. Hitung total amount per `siswa_code` dari flat rows
2. Sort rows: `key = (_JENJANG_SORT.get(jenjang_of[code], 99), -total_of[code])`

Struktur return value tidak berubah (tetap flat list of dicts). Consumer `_group_payments_by_siswa` memakai `OrderedDict` yang mempertahankan urutan insertion, sehingga Rangkuman PAM otomatis ikut urutan ini.

---

#### Fungsi: `get_pam_payments_detail` (baris ~691)

**Perubahan SQL ORDER BY:** Ubah dari `ORDER BY pb.siswa_code, pb.id` menjadi:

```sql
ORDER BY CASE s.jenjang
    WHEN 'S3' THEN 1
    WHEN 'S2' THEN 2
    WHEN 'S1' THEN 3
    ELSE 99
END, pb.siswa_code, pb.id
```

Ini memastikan `codes = list(dict.fromkeys(...))` sudah terurut per jenjang saat Python membangun dict.

**Post-processing Python (setelah `result` list selesai dibangun):**
```python
result.sort(key=lambda x: (
    _JENJANG_SORT.get((x.get("jenjang") or "").upper(), 99),
    -float(x.get("total_pembayaran") or 0),
))
for i, item in enumerate(result, 1):
    item["no"] = i
```

Sort SQL + Python sort menghasilkan urutan: jenjang → total_pembayaran DESC.  
Renumbering `no` field diperlukan karena nomor urut ditentukan saat build, bukan dari data.

---

## Scope: Tidak Berubah

- `exports.py` — tidak ada perubahan
- `routes.py` — tidak ada perubahan  
- Template HTML / JS — tidak ada perubahan
- Schema database — tidak ada perubahan

---

## Consumer yang Mendapat Efek Otomatis

| Consumer | Fungsi yang dipakai | Status |
|---|---|---|
| Form display (tab Detail PAM) | `get_pam_payments_detail` | ✅ otomatis |
| Form display (tab Rangkuman) | `get_pam_payments` | ✅ otomatis |
| PDF page 2 (Rangkuman PAM) | `get_pam_payments` | ✅ otomatis |
| PDF page 3 (Detail PAM) | `get_pam_payments_detail` | ✅ otomatis |
| Excel sheet "Rangkuman PAM" | `get_pam_payments` | ✅ otomatis |
| Excel sheet "Detail PAM" | `get_pam_payments_detail` | ✅ otomatis |
| `export_pam_pdf_custom` | `get_pam_payments` + `get_pam_payments_detail` | ✅ otomatis |
| `export_pam_excel_custom` | `get_pam_payments` + `get_pam_payments_detail` | ✅ otomatis |

---

## Edge Cases

- **Jenjang NULL atau kosong:** masuk bucket 99 (paling bawah)
- **Semua siswa jenjang sama:** diurutkan total DESC
- **Total sama:** SQL tiebreak `pb.siswa_code, pb.id` (deterministik)
- **Siswa tanpa record di tabel `siswa`** (LEFT JOIN): `jenjang` = NULL → bucket 99
