# PAM ↔ Payment Application Workflow Fix

**Date:** 2026-06-08  
**Scope:** Bug fix — sync status & nomor_pam between PAM records and PA tables (etf_pa, app_pa, sml_pa)

---

## Problem Statement

The Payment Approval Memo (PAM) Input workflow has three bugs:

1. **Status filter too broad**: When clicking "Tambah Baris" in the Beasiswa sub-tab and searching for students, the system returns PA records with `status IN ('open', 'draft')`. Only `'open'` records should appear.

2. **nomor_pam not filled on save**: When a Beasiswa PAM is submitted (`Simpan Payment`), the linked PA record (`etf_pa`, `app_pa`, or `sml_pa`) has its `status` set to `'on_process'` correctly, but `nomor_pam` is NOT populated with the auto-generated PAM number.

3. **Partial paid cascade**: `set_memo_tanggal_bayar()` cascades `tanggal_bayar + status='complete'` only to `etf_pa`. The same cascade must also apply to `app_pa` and `sml_pa`.

---

## Status Transitions (After Fix)

```
Tambah Baris → search siswa → ONLY PA with status='open'
        ↓
Simpan Payment (ipaySave)
        ↓
    payment_beasiswa records created (status='draft')
    PA table: status → 'on_process'
    PA table: nomor_pam → [auto-generated PAM number]   ← FIX
        ↓
Isi Tgl Paid (set_memo_tanggal_bayar)
        ↓
    PA table: status → 'complete'
    PA table: tanggal_bayar → [tanggal paid]            ← EXTEND to app_pa + sml_pa

Cancel PAM (cancel_pam_record)
        ↓
    PA table: status → 'open'
    PA table: nomor_pam → NULL                          ← EXTEND to app_pa + sml_pa
```

---

## Files & Changes

### 1. `app/modules/etf_payment_application/service.py`

**`get_draft_siswa()` line ~175:**
```python
# BEFORE
AND LOWER(p.status) IN ('open', 'draft')

# AFTER
AND LOWER(p.status) = 'open'
```

**`get_draft_lines_for_siswa()` line ~196:**
```python
# BEFORE
AND LOWER(p.status) IN ('open', 'draft')

# AFTER
AND LOWER(p.status) = 'open'
```

Both functions already use `_tbls(tab)` so the fix is automatically generic across etf_pa, app_pa, and sml_pa.

---

### 2. `app/modules/beasiswa/service.py` — `add_payment_multi()`

After `pam_no = create_pam_record(...)`, add nomor_pam update for all three PA tables:

```python
# Update nomor_pam for all PA tables linked via etf_pa_line_id
if pa_line_ids and pam_no:
    ph = ",".join("?" * len(pa_line_ids))
    ts_now = _ts()
    for (lines_tbl, pa_tbl) in [
        ("etf_pa_lines", "etf_pa"),
        ("app_pa_lines", "app_pa"),
        ("sml_pa_lines", "sml_pa"),
    ]:
        conn.execute(
            f"""UPDATE {pa_tbl} SET nomor_pam=?, updated_at=?
                WHERE id IN (
                    SELECT DISTINCT pa_id FROM {lines_tbl} WHERE id IN ({ph})
                ) AND company_id=?""",
            [pam_no, ts_now] + pa_line_ids + [company_id]
        )
```

---

### 3. `app/modules/payment_memo/service.py`

**`set_memo_tanggal_bayar()`** — extend cascade to app_pa and sml_pa:

```python
if line_ids:
    ph = ",".join("?" * len(line_ids))
    for (lines_tbl, pa_tbl) in [
        ("etf_pa_lines", "etf_pa"),
        ("app_pa_lines", "app_pa"),
        ("sml_pa_lines", "sml_pa"),
    ]:
        conn.execute(
            f"""UPDATE {pa_tbl} SET tanggal_bayar=?, status='complete', updated_at=?
                WHERE id IN (
                    SELECT DISTINCT pa_id FROM {lines_tbl} WHERE id IN ({ph})
                ) AND company_id=?""",
            [tanggal_bayar, now] + line_ids + [company_id]
        )
```

**`cancel_pam_record()` (beasiswa flow)** — extend revert to app_pa and sml_pa:

```python
if line_ids:
    for (lines_tbl, pa_tbl) in [
        ("etf_pa_lines", "etf_pa"),
        ("app_pa_lines", "app_pa"),
        ("sml_pa_lines", "sml_pa"),
    ]:
        pa_ids = conn.execute(
            f"SELECT DISTINCT pa_id FROM {lines_tbl} WHERE id IN ({ph})", line_ids
        ).fetchall()
        for row in pa_ids:
            pa_id = row[0]
            remaining = conn.execute(...)
            if remaining == 0:
                conn.execute(
                    f"UPDATE {pa_tbl} SET status='open', nomor_pam=NULL, updated_at=? WHERE id=? AND company_id=?",
                    (now, pa_id, company_id)
                )
```

---

## What Is NOT Changed

- AGRI sub-tab PAM creation (`create_pam_from_etf_pa`) — already correct
- `set_pam_tanggal_bayar_agri()` — already correct for AGRI flow
- Frontend (templates) — no changes needed
- Database schema — no migrations required

---

## Risk

Low. All changes are additive UPDATE statements on existing tables. Rows that don't match (wrong line table) produce zero affected rows harmlessly.
