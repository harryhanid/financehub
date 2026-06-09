# Spec: Editable No. PAM di Input PA

**Date:** 2026-06-09
**Module:** `payment_memo` — tab Input PA
**Status:** Approved

---

## Goal

Field **No. PAM** di panel Input PA saat ini `readonly` (auto-generate dari tipe + tanggal).
User perlu bisa override nilai tersebut secara manual, dengan tetap menjaga format valid dan mencegah collision dengan nomor yang sudah ada.

---

## Behavior

### Auto-generate (default)
- Saat Tipe PAM atau Tanggal berubah → `ipayFetchNextPamNo()` dipanggil → field diisi nilai auto, badge "(manual)" tidak muncul, style normal (border biru muda).
- Ini identik dengan behavior saat ini.

### Manual edit
- User dapat mengetik langsung di field No. PAM.
- Saat nilai berubah dari auto-generated → label menampilkan badge kecil **(manual)** dan border berubah oranye (`#f59e0b`).
- Saat tipe/tanggal berubah → nilai di-overwrite kembali ke auto, badge hilang, style kembali normal.

---

## Validation

### Format (real-time, saat `input` event)
- Regex: `^PAM-\d{3}-(AGRI|APP|SML|SETF)-\d{2}-\d{4}$`
- Contoh valid: `PAM-054-AGRI-06-2026`
- Jika tidak match: border merah, hint text di bawah field: *"Format: PAM-054-AGRI-06-2026"*, tombol Simpan di-disable.
- Jika format OK: hint hilang, lanjut ke collision check.

### Collision check (saat `blur` dari field)
- Hanya dijalankan jika format valid.
- Call `GET /payment-memo/pam/check?pam_no=<value>` (JWT required).
- Jika `exists: true`: border merah, hint *"PAM ini sudah terdaftar"*, tombol Simpan di-disable.
- Jika `exists: false`: border hijau sebentar, hint hilang, tombol Simpan aktif.

### Guard di `ipaySavePa()`
- Cek state field: jika format salah → `showToast("No. PAM tidak valid.", "error"); return`.
- Jika field dalam state "manual" (belum blur): jalankan collision check dulu (await), baru lanjut simpan.
- Jika collision check return `exists: true`: abort dengan toast error.

---

## Backend

### Endpoint baru
```
GET /payment-memo/pam/check?pam_no=<str>
```
- Auth: `@jwt_html_required`
- Read-only, tidak mengubah data.
- Query: `SELECT 1 FROM pam_records WHERE pam_no=? AND company_id=?`
- Response: `{"ok": true, "exists": true|false}`

### Service function baru
```python
def check_pam_no_exists(company_id: int, pam_no: str) -> dict:
    conn = get_conn()
    row = conn.execute(
        "SELECT 1 FROM pam_records WHERE pam_no=? AND company_id=?",
        (pam_no, company_id)
    ).fetchone()
    conn.close()
    return {"ok": True, "exists": row is not None}
```

---

## Files Changed

| File | Perubahan |
|------|-----------|
| `app/templates/payment_memo/index.html` | Remove `readonly` dari `ipay-pam-full`; ubah style; tambah hint div `ipay-pam-hint`; tambah JS `ipayValidatePamNo()`, `ipayCheckPamCollision()`, update `ipayOnTypeChange()` dan `ipaySavePa()` |
| `app/modules/payment_memo/routes.py` | Tambah route `GET /pam/check` |
| `app/modules/payment_memo/service.py` | Tambah `check_pam_no_exists()` |

---

## UI States Summary

| State | Border | Badge | Hint | Simpan btn |
|-------|--------|-------|------|-----------|
| Auto (default) | biru muda | — | — | enabled |
| Manual (valid, unchecked) | oranye | (manual) | — | enabled* |
| Manual (format error) | merah | (manual) | "Format: PAM-054-..." | disabled |
| Manual (collision) | merah | (manual) | "PAM sudah terdaftar" | disabled |
| Manual (valid, checked OK) | hijau | (manual) | — | enabled |

*enabled tapi collision check akan dijalankan saat blur sebelum submit bisa berhasil.

---

## Out of Scope

- Tidak ada perubahan pada `save_pa_payment()` di service.
- Tidak ada perubahan schema DB.
- Tidak ada history/audit trail untuk PAM number yang di-override manual.
