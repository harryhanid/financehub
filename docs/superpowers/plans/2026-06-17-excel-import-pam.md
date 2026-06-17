# Excel → SQLite PAM Import Script Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Script Python standalone `tmp_import_excel.py` yang membaca hasil export Excel (PAM AGRI + Open PAM), mendeteksi perubahan (update/rename/delete), menampilkan diff preview, lalu apply ke SQLite dengan cascade yang benar.

**Architecture:** Dua fase — (1) pure matching logic yang bisa ditest tanpa DB, (2) apply functions yang reuse service functions yang sudah ada untuk cascade-safe operations. Dry-run by default, `--apply` flag untuk eksekusi. Backup otomatis sebelum apply.

**Tech Stack:** Python stdlib + openpyxl (sudah ada di project), SQLite via `database.get_conn()`, reuse `modules.payment_memo.service.cancel_pam_record` dan `update_pam_and_application`.

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `tmp_import_excel.py` | Create (root) | Main script: load, match, print_diff, apply, main() |
| `tests/test_import_pam.py` | Create | Unit tests untuk match functions dan normalize helpers |

---

## Task 1: Write Failing Tests untuk Match Functions

**Files:**
- Create: `tests/test_import_pam.py`

- [ ] **Step 1.1: Buat file test dengan fixtures**

```python
# tests/test_import_pam.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from datetime import datetime
import pytest

# akan diimport setelah Task 2
from tmp_import_excel import (
    match_pam_agri, match_open_pam, normalize_date, normalize_amount
)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _pam_db(pam_no, pam_date, total, status, id_):
    return {"id": id_, "pam_no": pam_no, "pam_date": pam_date,
            "total_amount": float(total), "status": status, "tanggal_bayar": None}


def _pam_ex(pam_no, pam_date, total, status, tgl_paid=None):
    return {"PAM No": pam_no, "PAM Date": pam_date, "Total (Rp)": total,
            "Status": status, "Tgl Paid": tgl_paid}


def _pb_db(id_, code, cat1, cat2, tanggal, amount,
           pam="", perusahaan="", status="open"):
    return {"id": id_, "siswa_code": code, "cat1": cat1, "cat2": cat2,
            "tanggal": tanggal, "amount": float(amount),
            "pam": pam, "perusahaan": perusahaan, "status": status}


def _pb_ex(code, cat1, cat2, tanggal, amount,
           pam="", perusahaan="", status="open"):
    return {"Code": code, "Kategori 1": cat1, "Kategori 2": cat2,
            "Tanggal": tanggal, "Amount (Rp)": amount,
            "PAM No": pam, "Perusahaan": perusahaan, "Status": status}


# ── normalize_date ─────────────────────────────────────────────────────────────

def test_normalize_date_string():
    assert normalize_date("2026-06-15") == "2026-06-15"

def test_normalize_date_datetime():
    assert normalize_date(datetime(2026, 6, 15, 10, 30)) == "2026-06-15"

def test_normalize_date_none():
    assert normalize_date(None) is None

def test_normalize_date_long_string():
    assert normalize_date("2026-06-15 00:00:00") == "2026-06-15"


# ── match_pam_agri ─────────────────────────────────────────────────────────────

def test_match_pam_agri_update_status():
    """Row sama PAM No, status berubah on_process → complete + tgl_paid diisi."""
    db = [_pam_db("PAM-001-ETF-06-2026", "2026-06-15", 1_000_000, "on_process", 1)]
    ex = [_pam_ex("PAM-001-ETF-06-2026", "2026-06-15", 1_000_000, "complete", "2026-06-17")]
    r = match_pam_agri(ex, db)
    assert len(r["updates"]) == 1
    assert r["updates"][0][1]["Status"] == "complete"
    assert r["renames"] == []
    assert r["deletes"] == []
    assert r["skips"]   == []

def test_match_pam_agri_no_change():
    """Tidak ada field yang berubah → tidak masuk updates."""
    db = [_pam_db("PAM-001-ETF-06-2026", "2026-06-15", 1_000_000, "on_process", 1)]
    ex = [_pam_ex("PAM-001-ETF-06-2026", "2026-06-15", 1_000_000, "on_process")]
    r = match_pam_agri(ex, db)
    assert r["updates"] == []
    assert r["deletes"] == []
    assert r["renames"] == []
    assert r["skips"]   == []

def test_match_pam_agri_delete():
    """Row ada di DB tapi tidak ada di Excel → DELETE."""
    db = [_pam_db("PAM-001-ETF-06-2026", "2026-06-15", 1_000_000, "on_process", 1)]
    ex = []
    r = match_pam_agri(ex, db)
    assert len(r["deletes"]) == 1
    assert r["deletes"][0]["pam_no"] == "PAM-001-ETF-06-2026"
    assert r["updates"] == []

def test_match_pam_agri_rename():
    """PAM No lama diganti di Excel, tapi pam_date + total_amount sama → auto-RENAME."""
    db = [_pam_db("PAM-001-AGRI-06-2026", "2026-06-15", 1_000_000, "on_process", 1)]
    ex = [_pam_ex("PAM-001-ETF-06-2026",  "2026-06-15", 1_000_000, "on_process")]
    r = match_pam_agri(ex, db)
    assert len(r["renames"]) == 1
    assert r["renames"][0][0]["pam_no"] == "PAM-001-AGRI-06-2026"
    assert r["renames"][0][1]["PAM No"] == "PAM-001-ETF-06-2026"
    assert r["deletes"] == []
    assert r["skips"]   == []

def test_match_pam_agri_skip_ambiguous():
    """Dua DB rows dengan pam_date + total sama → tidak bisa auto-detect → SKIP."""
    db = [
        _pam_db("PAM-001-AGRI-06-2026", "2026-06-15", 1_000_000, "on_process", 1),
        _pam_db("PAM-002-AGRI-06-2026", "2026-06-15", 1_000_000, "on_process", 2),
    ]
    ex = [_pam_ex("PAM-NEW-ETF-06-2026", "2026-06-15", 1_000_000, "on_process")]
    r = match_pam_agri(ex, db)
    assert len(r["skips"])   == 1
    assert len(r["deletes"]) == 2


# ── match_open_pam ─────────────────────────────────────────────────────────────

def test_match_open_pam_update():
    """Composite key cocok, pam + perusahaan + status berubah → UPDATE."""
    db = [_pb_db(1, "2250234", "By Tunjangan", "Semester 2", "2026-06-15", 19_433_500)]
    ex = [_pb_ex("2250234", "By Tunjangan", "Semester 2", "2026-06-15", 19_433_500,
                 pam="PAM-057-ETF-06-2026", perusahaan="PT. SMART Tbk", status="on_process")]
    r = match_open_pam(ex, db)
    assert len(r["updates"]) == 1
    assert r["updates"][0][1]["PAM No"] == "PAM-057-ETF-06-2026"
    assert r["deletes"] == []
    assert r["skips"]   == []

def test_match_open_pam_no_change():
    """Composite key cocok, semua field sama → tidak ada update."""
    db = [_pb_db(1, "2250234", "By Tunjangan", "Semester 2", "2026-06-15", 19_433_500,
                 pam="PAM-056", perusahaan="PT. SMART", status="open")]
    ex = [_pb_ex("2250234", "By Tunjangan", "Semester 2", "2026-06-15", 19_433_500,
                 pam="PAM-056", perusahaan="PT. SMART", status="open")]
    r = match_open_pam(ex, db)
    assert r["updates"] == []
    assert r["deletes"] == []

def test_match_open_pam_delete():
    """Row ada di DB tapi dihapus dari Excel → DELETE."""
    db = [_pb_db(1, "2250234", "By Tunjangan", "Semester 2", "2026-06-15", 19_433_500)]
    ex = []
    r = match_open_pam(ex, db)
    assert len(r["deletes"]) == 1
    assert r["deletes"][0]["siswa_code"] == "2250234"

def test_match_open_pam_skip():
    """Row di Excel tidak ada match di DB → SKIP + warning."""
    db = []
    ex = [_pb_ex("9999999", "By Tunjangan", "Semester 2", "2026-06-15", 5_000_000)]
    r = match_open_pam(ex, db)
    assert len(r["skips"]) == 1
    assert r["updates"] == []
    assert r["deletes"] == []
```

- [ ] **Step 1.2: Jalankan test, pastikan FAIL (modul belum ada)**

```
cd C:\Financehub
pytest tests/test_import_pam.py -v
```

Expected: `ModuleNotFoundError: No module named 'tmp_import_excel'`

---

## Task 2: Implement Match Functions & Normalize Helpers

**Files:**
- Create: `tmp_import_excel.py`

- [ ] **Step 2.1: Buat skeleton script dengan normalize helpers**

```python
# tmp_import_excel.py
"""
Import script: sync perubahan dari Excel → SQLite (PAM AGRI + Open PAM).

Usage:
    python tmp_import_excel.py           # dry-run — lihat diff, tidak ada yang berubah
    python tmp_import_excel.py --apply   # apply perubahan ke SQLite

File Excel dikonfigurasi di konstanta PAM_AGRI_FILE dan OPEN_PAM_FILE di bawah.
"""
import sys
import os
import shutil
import argparse
from datetime import datetime, date

# ── Path setup ──────────────────────────────────────────────────────────────────
_ROOT = os.path.dirname(os.path.abspath(__file__))
_APP  = os.path.join(_ROOT, "app")
sys.path.insert(0, _APP)
os.chdir(_APP)

from database import get_conn  # noqa: E402

# ── Config ──────────────────────────────────────────────────────────────────────
PAM_AGRI_FILE = r"C:\Users\25010160\Downloads\PAM_AGRI_20260617_1111.xlsx"
OPEN_PAM_FILE = r"C:\Users\25010160\Downloads\Open_PAM_20260617_1111.xlsx"
DB_PATH       = os.path.join(_APP, "finance_hub.db")
COMPANY_ID    = 2   # ETF company_id di DB


# ── Normalize helpers ───────────────────────────────────────────────────────────

def normalize_date(val) -> str | None:
    """Return YYYY-MM-DD string atau None."""
    if val is None:
        return None
    if isinstance(val, (datetime, date)):
        return val.strftime("%Y-%m-%d")
    s = str(val).strip()
    return s[:10] if len(s) >= 10 else None


def normalize_amount(val) -> float:
    """Return float, 0.0 jika tidak valid."""
    if val is None:
        return 0.0
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0
```

- [ ] **Step 2.2: Implement `match_pam_agri`**

Tambahkan ke `tmp_import_excel.py` setelah normalize helpers:

```python
# ── Match logic: pam_records ────────────────────────────────────────────────────

def match_pam_agri(excel_rows: list[dict], db_rows: list[dict]) -> dict:
    """
    Bandingkan Excel rows vs DB rows untuk pam_records.

    Returns:
        {
            "updates": [(db_row, excel_row)],   # same PAM No, field berubah
            "renames": [(db_row, excel_row)],   # PAM No beda, auto-detect via date+total
            "deletes": [db_row],                # di DB tapi tidak di Excel
            "skips":   [excel_row],             # di Excel tapi tidak bisa di-match
        }
    """
    db_by_pam    = {r["pam_no"]: r for r in db_rows}
    matched_ids  = set()
    updates, tentative_skips = [], []

    for ex in excel_rows:
        pno = (ex.get("PAM No") or "").strip()
        if not pno:
            continue
        if pno in db_by_pam:
            db = db_by_pam[pno]
            matched_ids.add(db["id"])
            ex_status = (ex.get("Status") or "").strip()
            ex_tgl    = normalize_date(ex.get("Tgl Paid"))
            if ex_status != (db.get("status") or "").strip() or \
               ex_tgl != db.get("tanggal_bayar"):
                updates.append((db, ex))
        else:
            tentative_skips.append(ex)

    # Auto-detect renames: skip row yang tidak match PAM No,
    # cek apakah ada DB row "orphan" (tidak di Excel) dengan pam_date + total_amount sama.
    unmatched_db = [r for r in db_rows if r["id"] not in matched_ids]
    renames, real_skips = [], []

    for ex in tentative_skips:
        ex_date = normalize_date(ex.get("PAM Date"))
        ex_amt  = normalize_amount(ex.get("Total (Rp)"))
        candidates = [
            r for r in unmatched_db
            if normalize_date(r.get("pam_date")) == ex_date
            and abs(normalize_amount(r.get("total_amount")) - ex_amt) < 0.01
        ]
        if len(candidates) == 1:
            db = candidates[0]
            matched_ids.add(db["id"])
            unmatched_db.remove(db)
            renames.append((db, ex))
        else:
            real_skips.append(ex)

    deletes = [r for r in db_rows if r["id"] not in matched_ids]
    return {"updates": updates, "renames": renames,
            "deletes": deletes, "skips": real_skips}
```

- [ ] **Step 2.3: Implement `match_open_pam`**

Tambahkan ke `tmp_import_excel.py`:

```python
# ── Match logic: payment_beasiswa ───────────────────────────────────────────────

def _pb_key(code, cat1, cat2, tanggal, amount) -> tuple:
    """Composite key untuk matching payment_beasiswa."""
    return (
        (code    or "").strip(),
        (cat1    or "").strip(),
        (cat2    or "").strip(),
        normalize_date(tanggal) or "",
        round(normalize_amount(amount), 2),
    )


def match_open_pam(excel_rows: list[dict], db_rows: list[dict]) -> dict:
    """
    Bandingkan Excel rows vs DB rows untuk payment_beasiswa.

    Returns:
        {
            "updates": [(db_row, excel_row)],   # composite key cocok, field berubah
            "deletes": [db_row],                # di DB tapi tidak di Excel
            "skips":   [excel_row],             # di Excel tapi tidak ada match di DB
        }
    """
    db_by_key   = {}
    for r in db_rows:
        k = _pb_key(r["siswa_code"], r["cat1"], r["cat2"], r["tanggal"], r["amount"])
        db_by_key[k] = r

    updates, skips = [], []
    matched_ids    = set()

    for ex in excel_rows:
        k = _pb_key(
            ex.get("Code"), ex.get("Kategori 1"), ex.get("Kategori 2"),
            ex.get("Tanggal"), ex.get("Amount (Rp)")
        )
        if k in db_by_key:
            db = db_by_key[k]
            matched_ids.add(db["id"])
            ex_pam = (ex.get("PAM No")     or "").strip()
            ex_per = (ex.get("Perusahaan") or "").strip()
            ex_st  = (ex.get("Status")     or "").strip()
            if ex_pam != (db.get("pam")        or "").strip() or \
               ex_per != (db.get("perusahaan") or "").strip() or \
               ex_st  != (db.get("status")     or "").strip():
                updates.append((db, ex))
        else:
            skips.append(ex)

    deletes = [r for r in db_rows if r["id"] not in matched_ids]
    return {"updates": updates, "deletes": deletes, "skips": skips}
```

- [ ] **Step 2.4: Jalankan tests, pastikan PASS**

```
cd C:\Financehub
pytest tests/test_import_pam.py -v
```

Expected: semua 13 tests PASS.

- [ ] **Step 2.5: Commit**

```
git add tmp_import_excel.py tests/test_import_pam.py
git commit -m "feat: add Excel→SQLite PAM import script — match functions + tests"
```

---

## Task 3: Implement Load Functions & Print Diff

**Files:**
- Modify: `tmp_import_excel.py`

- [ ] **Step 3.1: Implement `load_pam_agri_excel` dan `load_open_pam_excel`**

Tambahkan ke `tmp_import_excel.py` setelah match functions:

```python
# ── Load functions ──────────────────────────────────────────────────────────────

def load_pam_agri_excel(filepath: str) -> list[dict]:
    """Baca sheet pertama PAM AGRI Excel, return list of dicts."""
    import openpyxl
    wb = openpyxl.load_workbook(filepath, data_only=True)
    ws = wb.active
    headers = [c.value for c in ws[1]]
    rows = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if all(v is None for v in row):
            continue  # skip fully blank rows
        rows.append(dict(zip(headers, row)))
    return rows


def load_open_pam_excel(filepath: str) -> list[dict]:
    """Baca sheet pertama Open PAM Excel, return list of dicts."""
    import openpyxl
    wb = openpyxl.load_workbook(filepath, data_only=True)
    ws = wb.active
    headers = [c.value for c in ws[1]]
    rows = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if all(v is None for v in row):
            continue
        rows.append(dict(zip(headers, row)))
    return rows


def fetch_pam_agri_db(company_id: int) -> list[dict]:
    """Ambil semua pam_records dari DB untuk company_id ini."""
    conn = get_conn()
    rows = [dict(r) for r in conn.execute(
        "SELECT id, pam_no, pam_date, total_amount, status, tanggal_bayar, source "
        "FROM pam_records WHERE company_id=?", (company_id,)
    ).fetchall()]
    conn.close()
    return rows


def fetch_open_pam_db(company_id: int) -> list[dict]:
    """Ambil payment_beasiswa status='open' dari DB.
    Filter status='open' karena Open PAM export hanya mengeksport record open;
    record on_process/complete tidak tersentuh script ini.
    """
    conn = get_conn()
    rows = [dict(r) for r in conn.execute(
        "SELECT id, siswa_code, cat1, cat2, tanggal, amount, pam, perusahaan, status "
        "FROM payment_beasiswa WHERE company_id=? AND status='open'", (company_id,)
    ).fetchall()]
    conn.close()
    return rows
```

- [ ] **Step 3.2: Implement `print_diff`**

Tambahkan ke `tmp_import_excel.py`:

```python
# ── Diff output ─────────────────────────────────────────────────────────────────

def print_diff(pam_result: dict, open_result: dict, dry_run: bool = True) -> None:
    sep = "=" * 66
    mode = "DRY-RUN MODE — tidak ada perubahan yang disimpan" if dry_run \
           else "APPLY MODE — perubahan akan diterapkan"
    print(f"\n{sep}\n{mode}\n{sep}\n")

    # PAM AGRI
    print("=== PAM AGRI (pam_records) ===")
    for db, ex in pam_result["updates"]:
        tgl = normalize_date(ex.get("Tgl Paid")) or "-"
        print(f"[UPDATE]  {db['pam_no']:<30} "
              f"status: {db['status']} → {ex['Status']} | tgl_paid: {tgl}")
    for db, ex in pam_result["renames"]:
        print(f"[RENAME]  {db['pam_no']:<30} → {ex['PAM No']}  (cascade 4 tabel)")
    for db in pam_result["deletes"]:
        print(f"[DELETE]  {db['pam_no']:<30} (cascade cancel_pam_record)")
    for ex in pam_result["skips"]:
        print(f"[SKIP ⚠]  {ex.get('PAM No','?'):<30} → tidak ada match di DB")

    print()

    # Open PAM
    print("=== OPEN PAM (payment_beasiswa) ===")
    for db, ex in open_result["updates"]:
        print(f"[UPDATE]  {db['siswa_code']} | {db['cat2']} | {db['tanggal']} : "
              f"pam={ex.get('PAM No','-')}, "
              f"perusahaan={ex.get('Perusahaan','-')}, "
              f"status={ex.get('Status','-')}")
    for db in open_result["deletes"]:
        print(f"[DELETE]  {db['siswa_code']} | {db['cat1']} | {db['cat2']} | {db['tanggal']}")
    for ex in open_result["skips"]:
        print(f"[SKIP ⚠]  {ex.get('Code','?')} | {ex.get('Kategori 2','?')} "
              f"→ tidak ada match di DB")

    print()
    print("-" * 66)
    pu = len(pam_result["updates"])
    pr = len(pam_result["renames"])
    pd = len(pam_result["deletes"])
    ps = len(pam_result["skips"])
    ou = len(open_result["updates"])
    od = len(open_result["deletes"])
    os_ = len(open_result["skips"])
    print(f"  pam_records      : {pu} update, {pr} rename, {pd} delete, {ps} skip")
    print(f"  payment_beasiswa : {ou} update, {od} delete, {os_} skip")
    if not dry_run:
        print("\nPerubahan diterapkan.")
    else:
        print("\nJalankan dengan --apply untuk menerapkan perubahan.")
    print(sep)
```

- [ ] **Step 3.3: Test dry-run manual dengan file Excel asli**

```
cd C:\Financehub
python tmp_import_excel.py
```

Expected: output diff terformat, tidak ada error. Cek apakah jumlah update/rename/delete masuk akal.

- [ ] **Step 3.4: Commit**

```
git add tmp_import_excel.py
git commit -m "feat: add load, fetch, print_diff functions to import script"
```

---

## Task 4: Implement Apply Functions & Backup

**Files:**
- Modify: `tmp_import_excel.py`

- [ ] **Step 4.1: Implement `backup_db` dan `_ts`**

Tambahkan ke `tmp_import_excel.py` setelah imports:

```python
def _ts() -> str:
    return datetime.now().isoformat(timespec="seconds")


def backup_db() -> str:
    """Copy DB ke file backup, return path backup."""
    ts    = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak   = DB_PATH + f".bak_import_{ts}"
    shutil.copy2(DB_PATH, bak)
    print(f"[BACKUP] {bak}")
    return bak
```

- [ ] **Step 4.2: Implement `apply_pam_agri`**

Tambahkan ke `tmp_import_excel.py`:

```python
# ── Apply functions ─────────────────────────────────────────────────────────────

def apply_pam_agri(result: dict, company_id: int) -> None:
    """Apply updates, renames, deletes ke pam_records."""
    from modules.payment_memo.service import (
        cancel_pam_record, update_pam_and_application
    )

    # 1. UPDATE: status + tanggal_bayar via direct SQL (batch)
    if result["updates"]:
        conn = get_conn()
        try:
            for db, ex in result["updates"]:
                new_status = (ex.get("Status") or "").strip()
                new_tgl    = normalize_date(ex.get("Tgl Paid"))
                conn.execute(
                    "UPDATE pam_records SET status=?, tanggal_bayar=?, updated_at=? "
                    "WHERE id=?",
                    (new_status, new_tgl, _ts(), db["id"])
                )
            conn.commit()
            print(f"  ✓ {len(result['updates'])} pam_records di-UPDATE")
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # 2. RENAME: cascade via update_pam_and_application
    for db, ex in result["renames"]:
        new_pno = (ex.get("PAM No") or "").strip()
        new_st  = (ex.get("Status") or "").strip()
        new_tgl = normalize_date(ex.get("Tgl Paid"))
        pam_data = {"pam_no": new_pno, "status": new_st}
        if new_tgl:
            pam_data["tanggal_bayar"] = new_tgl
        res = update_pam_and_application(db["id"], pam_data, {}, company_id)
        if res.get("ok"):
            print(f"  ✓ RENAME {db['pam_no']} → {new_pno}")
        else:
            print(f"  ✗ RENAME GAGAL {db['pam_no']}: {res.get('pesan')}")

    # 3. DELETE: cascade via cancel_pam_record
    for db in result["deletes"]:
        res = cancel_pam_record(db["id"], company_id)
        if res.get("ok"):
            print(f"  ✓ DELETE {db['pam_no']}")
        else:
            print(f"  ✗ DELETE GAGAL {db['pam_no']}: {res.get('pesan')}")

    # 4. SKIP: hanya warning
    for ex in result["skips"]:
        print(f"  ⚠ SKIP {ex.get('PAM No','?')} — tidak ada match di DB, handle manual")
```

- [ ] **Step 4.3: Implement `apply_open_pam`**

Tambahkan ke `tmp_import_excel.py`:

```python
def apply_open_pam(result: dict, company_id: int) -> None:
    """Apply updates dan deletes ke payment_beasiswa."""
    conn = get_conn()
    try:
        for db, ex in result["updates"]:
            new_pam = (ex.get("PAM No")     or "").strip() or None
            new_per = (ex.get("Perusahaan") or "").strip() or None
            new_st  = (ex.get("Status")     or "").strip()
            conn.execute(
                "UPDATE payment_beasiswa SET pam=?, perusahaan=?, status=? WHERE id=?",
                (new_pam, new_per, new_st, db["id"])
            )
        for db in result["deletes"]:
            conn.execute(
                "DELETE FROM payment_beasiswa WHERE id=? AND company_id=?",
                (db["id"], company_id)
            )
        conn.commit()
        print(f"  ✓ {len(result['updates'])} payment_beasiswa di-UPDATE")
        print(f"  ✓ {len(result['deletes'])} payment_beasiswa di-DELETE")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    for ex in result["skips"]:
        print(f"  ⚠ SKIP {ex.get('Code','?')} | {ex.get('Kategori 2','?')} "
              f"— tidak ada match, handle manual")
```

- [ ] **Step 4.4: Implement `main()`**

Tambahkan ke `tmp_import_excel.py` di bagian bawah:

```python
# ── Main ────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Import PAM Excel → SQLite")
    parser.add_argument("--apply", action="store_true",
                        help="Apply perubahan ke DB (default: dry-run)")
    args = parser.parse_args()
    dry_run = not args.apply

    print("Membaca Excel files...")
    ex_pam  = load_pam_agri_excel(PAM_AGRI_FILE)
    ex_open = load_open_pam_excel(OPEN_PAM_FILE)
    print(f"  PAM AGRI : {len(ex_pam)} baris")
    print(f"  Open PAM : {len(ex_open)} baris")

    print("Membaca data DB...")
    db_pam  = fetch_pam_agri_db(COMPANY_ID)
    db_open = fetch_open_pam_db(COMPANY_ID)
    print(f"  pam_records      : {len(db_pam)} rows")
    print(f"  payment_beasiswa : {len(db_open)} rows")

    print("Menghitung perubahan...")
    pam_result  = match_pam_agri(ex_pam, db_pam)
    open_result = match_open_pam(ex_open, db_open)

    print_diff(pam_result, open_result, dry_run=dry_run)

    if not dry_run:
        backup_db()
        print("\nApplying pam_records...")
        apply_pam_agri(pam_result, COMPANY_ID)
        print("\nApplying payment_beasiswa...")
        apply_open_pam(open_result, COMPANY_ID)
        print("\nSelesai.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4.5: Jalankan dry-run final untuk validasi**

```
cd C:\Financehub
python tmp_import_excel.py
```

Expected: output diff lengkap tanpa error. Periksa:
- Jumlah UPDATE/RENAME/DELETE sesuai ekspektasi
- Tidak ada error import modul
- SKIP rows masuk akal

- [ ] **Step 4.6: Commit**

```
git add tmp_import_excel.py
git commit -m "feat: add apply functions, backup, main() to PAM import script"
```

---

## Task 5: Apply ke DB (End-to-End)

**Files:**
- Run: `tmp_import_excel.py --apply`

- [ ] **Step 5.1: Cek dry-run sekali lagi, konfirmasi output masuk akal**

```
cd C:\Financehub
python tmp_import_excel.py
```

Pastikan:
- Jumlah UPDATE/DELETE logis (tidak ada angka yang aneh)
- Tidak ada SKIP yang seharusnya ter-match
- RENAME terdeteksi dengan benar

- [ ] **Step 5.2: Run dengan --apply**

```
cd C:\Financehub
python tmp_import_excel.py --apply
```

Expected output:
```
[BACKUP] C:\Financehub\app\finance_hub.db.bak_import_20260617_HHMMSS

Applying pam_records...
  ✓ N pam_records di-UPDATE
  ✓ RENAME ...
  ✓ DELETE ...

Applying payment_beasiswa...
  ✓ N payment_beasiswa di-UPDATE
  ✓ N payment_beasiswa di-DELETE

Selesai.
```

- [ ] **Step 5.3: Verifikasi di app**

Buka browser → modul Payment Memo → tab Open PAM dan AGRI.
Pastikan:
- Data yang diubah statusnya sudah ter-update
- Baris yang dihapus sudah tidak ada
- PAM No yang di-rename sudah berubah

- [ ] **Step 5.4: Jalankan test suite**

```
cd C:\Financehub
pytest tests/ -v
```

Expected: semua tests PASS (termasuk 13 tests baru di test_import_pam.py).

- [ ] **Step 5.5: Commit final**

```
git add tests/test_import_pam.py tmp_import_excel.py
git commit -m "feat: complete Excel→SQLite PAM import script — tested and applied"
```
