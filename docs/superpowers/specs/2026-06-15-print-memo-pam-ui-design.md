# Print Memo PAM — UI & Export Improvements Design

**Tanggal:** 2026-06-15
**Modul:** `app/modules/payment_memo/` + `app/templates/payment_memo/index.html`
**Status:** Approved

---

## Latar Belakang

Tampilan form Print Memo PAM perlu diperbaiki di 7 area:
1. Bank details di form UI saat ini hardcode "Terlampir" — harus pakai data siswa aktual
2. Detail PAM table di form UI belum punya kolom Jenjang Studi
3. Excel PAM NEW: tanda titik-dua (`:`) belum center-aligned
4. Excel PAM NEW: Vendor Name / Bank fields belum wrap_text
5. Excel Rangkuman PAM: format angka `#,##0` bukan Rp Accounting
6. Excel Detail PAM: format angka `#,##0` bukan Rp Accounting
7. PDF Detail PAM: belum ada kolom Jenjang Studi

---

## Files yang Diubah

| File | Area |
|------|------|
| `app/templates/payment_memo/index.html` | Area 1, Area 2 |
| `app/modules/payment_memo/exports.py` | Area 3, 4, 5, 6, 7 |

Tidak ada perubahan di `service.py`, `routes.py`, atau database schema.

---

## Area 1 — Form UI: Bank Details dari Data Siswa

**Lokasi:** `dmRenderForm()` (sekitar baris 2517–2562)

**Data source:** `_dmPayments` array sudah punya field `namarek`, `bank`, `norek` dari JOIN siswa di `get_pam_payments()`.

**Perubahan:** Tambah 3 variabel setelah `vendorNames`:

```javascript
const bankAccountNames = [...new Set(
  _dmPayments.map(pb => (pb.namarek || '').trim()).filter(Boolean)
)].join(', ') || 'Terlampir';

const bankNames = [...new Set(
  _dmPayments.map(pb => (pb.bank || '').trim()).filter(Boolean)
)].join(', ') || 'Terlampir';

const bankAccountNos = [...new Set(
  _dmPayments.map(pb => (pb.norek || '').trim()).filter(Boolean)
)].join(', ') || 'Terlampir';
```

Ubah input bank di baris 2560–2562:
```javascript
// SEBELUM
${field('Bank Account Name',   inp('dm-f-bank-name', 'Terlampir'))}
${field('Bank Name',           inp('dm-f-bank',      'Terlampir'))}
${field('Bank Account Number', inp('dm-f-bank-no',   'Terlampir'))}

// SESUDAH
${field('Bank Account Name',   inp('dm-f-bank-name', bankAccountNames))}
${field('Bank Name',           inp('dm-f-bank',      bankNames))}
${field('Bank Account Number', inp('dm-f-bank-no',   bankAccountNos))}
```

**Efek ke PDF & Excel:** `collectDmFields()` membaca DOM inputs dan mengirim ke backend. `export_pam_pdf_custom` menggunakan `_maybe_terlampir(data.get("bank_account_name"))` dan `export_pam_excel_custom` menggunakan `data.get("bank_account_name", "Terlampir")` — keduanya otomatis mendapat real data. Tidak ada perubahan di backend.

---

## Area 2 — Form UI: Kolom Jenjang di Detail PAM Table

**Lokasi:** `dmRenderDetailPAM()` (sekitar baris 2697–2762)

**Data source:** `_dmPaymentsDetail` sudah punya field `jenjang` dari `get_pam_payments_detail()`.

**Perubahan:**

Headers — tambah `'Jenjang Studi'` setelah `'Nama Siswa'`:
```javascript
// SEBELUM (12 kolom)
const hdrs = ['No','Nama Siswa','Keterangan','By Pendidikan','By Tunjangan','By Penelitian','Total Pbyran','Bank','No. Rekening','Sisa Pend','Sisa Tunj','Sisa Riset'];
const aligns = ['center','left','left','right','right','right','right','left','left','right','right','right'];

// SESUDAH (13 kolom)
const hdrs = ['No','Nama Siswa','Jenjang Studi','Keterangan','By Pendidikan','By Tunjangan','By Penelitian','Total Pbyran','Bank','No. Rekening','Sisa Pend','Sisa Tunj','Sisa Riset'];
const aligns = ['center','left','center','left','right','right','right','right','left','left','right','right','right'];
```

Data rows — tambah sel jenjang dengan rowspan setelah sel Nama Siswa (hanya di `idx === 0` block):
```javascript
<td style="padding:5px 7px;font-size:11px;text-align:center;${bTop}"${rs}>${esc(siswa.jenjang||'')}</td>
```

Footer TOTAL — ubah colspan:
```javascript
// SEBELUM
<td colspan="6" ...>TOTAL</td>

// SESUDAH
<td colspan="7" ...>TOTAL</td>
```

---

## Area 3 — Excel PAM NEW: Colon Center Aligned

**Lokasi:** `export_pam_excel_custom()` (sekitar baris 1295–1402)

**Konstanta:** `_C = Alignment(horizontal="center", vertical="center", wrap_text=True)` sudah ada.

**Perubahan:**
- E4, E5, E6, E7, E8: tambah `align=_C`
- H19, H20, H21, H22: ubah dari `align=_R` → `align=_C`
- H25, H26, H27: tambah `align=_C`

O4 dan O5 sudah `align=_R` → biarkan.

---

## Area 4 — Excel PAM NEW: Wrap Text untuk Vendor/Bank Name

**Lokasi:** `export_pam_excel_custom()` (baris 1367, 1392, 1397)

Ubah alignment sel I19, I25, I26 dari `align=_L` ke wrap_text:
```python
_WL = Alignment(horizontal="left", vertical="center", wrap_text=True)
```

Terapkan:
- I19 (Vendor Name): `align=_WL`
- I25 (Bank Account Name): `align=_WL`
- I26 (Bank Name): `align=_WL`

---

## Area 5 — Excel Rangkuman PAM: Rp Accounting Format

**Lokasi:** Fungsi `_write_data2`, `_write_tot2`, dan Grand Total row di `export_pam_excel_custom()` (baris ~1558, 1574, 1621)

Format baru:
```python
_RP_FMT = '_-"Rp"* #,##0_-;\\-"Rp"* #,##0_-;_-"Rp"* "-"_-;_-@_-'
```

Ganti semua:
```python
ws2.cell(row, 8).number_format = '#,##0'
```
dengan:
```python
ws2.cell(row, 8).number_format = _RP_FMT
```

---

## Area 6 — Excel Detail PAM: Rp Accounting Format

**Lokasi:** `_build_detail_sheet()` (baris 563)

```python
# SEBELUM
_nfmt = '#,##0'

# SESUDAH
_nfmt = '_-"Rp"* #,##0_-;\\-"Rp"* #,##0_-;_-"Rp"* "-"_-;_-@_-'
```

Grand total row di baris 764 sudah pakai `c.number_format = _nfmt` → otomatis ikut.

Kolom JENJANG STUDI di Excel Detail PAM sudah ada (baris 664/712 di exports.py) — tidak perlu ditambah.

---

## Area 7 — PDF Detail PAM: Kolom Jenjang Studi

**Lokasi:** `_build_detail_pdf_table()` (baris 255–316)

**Perubahan col_w** — kurangi Nama Siswa 3.8→3.0cm, tambah 1.5cm jenjang:
```python
# SEBELUM (11 kolom, total ~25.7cm)
col_w = [0.6*cm, 3.8*cm, 3.2*cm, 2.4*cm, 2.4*cm, 2.4*cm,
         2.5*cm, 3.0*cm, 1.8*cm, 1.8*cm, 1.8*cm]

# SESUDAH (12 kolom, total ~26.9cm)
col_w = [0.6*cm, 3.0*cm, 1.5*cm, 3.2*cm, 2.4*cm, 2.4*cm, 2.4*cm,
         2.5*cm, 3.0*cm, 1.8*cm, 1.8*cm, 1.8*cm]
```

**Header** — tambah `"Jenjang\nStudi"` di posisi 2:
```python
hdrs = [_p(h, _s7h) for h in [
    "No", "Nama Siswa", "Jenjang\nStudi", "Keterangan",
    "By\nPend", "By\nTunj", "By\nRiset",
    "Total\nPbyran", "No. Rekening",
    "Sisa\nPend", "Sisa\nTunj", "Sisa\nRiset",
]]
```

**Data rows** — tambah sel jenjang setelah Nama Siswa (hanya di baris pertama siswa):
```python
_p((siswa.get("jenjang") or "") if first else "", _s7c),
```

**TableStyle ALIGN** — update column indices (setelah tambah kolom di posisi 2):
```python
# SEBELUM
("ALIGN", (3, 0), (6, -1), "RIGHT"),   # By Pend..Total
("ALIGN", (8, 0), (10, -1), "RIGHT"),   # Sisa kolom

# SESUDAH
("ALIGN", (4, 0), (7, -1), "RIGHT"),   # By Pend..Total (geser +1)
("ALIGN", (9, 0), (11, -1), "RIGHT"),   # Sisa kolom (geser +1)
```

Grand total row — tambah satu sel kosong untuk kolom jenjang (total row sekarang 12 kolom):
```python
rows.append([_p("", _s7)] * 7 + [
    _p(f"{grand_total:,.0f}", ...),
] + [_p("", _s7)] * 4)
# (sebelumnya: 6 kosong + 1 total + 4 kosong)
```

---

## Edge Cases

- **Semua namarek kosong:** `bankAccountNames = 'Terlampir'` (fallback)
- **Siswa tanpa jenjang:** `siswa.jenjang || ''` → kolom kosong (bukan error)
- **PAM tanpa payments:** `_dmPayments = []` → semua bank fields = 'Terlampir'
- **_RP_FMT di Rangkuman:** konstanta `_RP_FMT` didefinisikan lokal di `export_pam_excel_custom` (bukan modul-level) agar tidak konflik

---

## Self-Review

**Placeholder scan:** Tidak ada TBD atau TODO.

**Internal consistency:** `_RP_FMT` dipakai di Area 5 saja. `_build_detail_sheet` pakai `_nfmt` variabel lokal (Area 6). Keduanya format string yang sama.

**Scope check:** 2 file, 7 area terdefinisi jelas. Tidak ada scope creep.

**Ambiguity check:** PDF jenjang column — diputuskan masuk scope karena user minta "PDF export: update to match UI changes."
