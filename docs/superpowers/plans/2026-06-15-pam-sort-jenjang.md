# PAM Sort Jenjang Studi Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Sort baris siswa dalam PAM berdasarkan jenjang studi (S3→S2→S1→lainnya), dengan secondary sort total pembayaran DESC dalam jenjang yang sama — berlaku di form display, PDF, dan Excel.

**Architecture:** Perubahan hanya di `app/modules/payment_memo/service.py`. Tambah konstanta `_JENJANG_SORT`, ubah dua fungsi (`get_pam_payments` dan `get_pam_payments_detail`). Semua consumer (form, PDF, Excel) otomatis mendapat urutan baru karena memanggil kedua fungsi ini.

**Tech Stack:** Python, SQLite (sqlite3), pytest, monkeypatch

---

## File yang Diubah

| File | Aksi |
|------|------|
| `app/modules/payment_memo/service.py` | Modify — tambah konstanta + ubah 2 fungsi |
| `tests/test_payment_memo_sort.py` | Create — test sort behavior |

---

### Task 1: `_JENJANG_SORT` constant + update `get_pam_payments`

**Files:**
- Modify: `app/modules/payment_memo/service.py` (sekitar baris 227 untuk konstanta, baris 674 untuk fungsi)
- Create: `tests/test_payment_memo_sort.py`

- [ ] **Step 1: Buat file test dan tulis failing test untuk `get_pam_payments`**

Buat file `tests/test_payment_memo_sort.py`:

```python
import sqlite3
import pytest


def _make_db(path):
    """DB minimal dengan payment_beasiswa + siswa untuk test sort."""
    conn = sqlite3.connect(path)
    conn.execute("""CREATE TABLE siswa (
        id INTEGER PRIMARY KEY,
        company_id INTEGER, code TEXT, nama TEXT,
        bank TEXT, norek TEXT, namarek TEXT,
        jenjang TEXT, angkatan TEXT, program TEXT,
        universitas TEXT, fakultas TEXT
    )""")
    conn.execute("""CREATE TABLE payment_beasiswa (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER, siswa_code TEXT, pam TEXT,
        cat1 TEXT, cat2 TEXT, amount REAL DEFAULT 0, tanggal TEXT
    )""")
    conn.execute("""CREATE TABLE budget_beasiswa (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER, siswa_code TEXT,
        cat1 TEXT, amount REAL DEFAULT 0
    )""")
    # 4 siswa: S3, S2, S1 (x2 — berbeda total)
    conn.executemany(
        "INSERT INTO siswa VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        [
            (1, 1, "S3A", "Siti",  "BCA",    "111", "Siti",  "S3", "2018", "Kimia",  "ITB", "FMIPA"),
            (2, 1, "S2A", "Budi",  "BNI",    "222", "Budi",  "S2", "2019", "Hukum",  "UGM", "FH"),
            (3, 1, "S1A", "Ali",   "Mandiri","333", "Ali",   "S1", "2020", "Teknik", "UI",  "FT"),
            (4, 1, "S1B", "Dani",  "BRI",    "444", "Dani",  "S1", "2021", "Fisika", "UI",  "FMIPA"),
            (5, 1, "SMA", "Eko",   "Mandiri","555", "Eko",   "SD/SMP/SMA", "2022", "-", "SMA N 1", "-"),
        ]
    )
    # Payments — semua PAM-001 company_id=1
    # S3A = 4_000_000, S2A = 3_000_000, S1A = 5_000_000, S1B = 8_000_000, SMA = 2_000_000
    conn.executemany(
        "INSERT INTO payment_beasiswa (company_id, siswa_code, pam, cat1, amount, tanggal) VALUES (?,?,?,?,?,?)",
        [
            (1, "S3A", "PAM-001", "By Pendidikan", 4_000_000, "2026-01-01"),
            (1, "S2A", "PAM-001", "By Pendidikan", 3_000_000, "2026-01-01"),
            (1, "S1A", "PAM-001", "By Pendidikan", 5_000_000, "2026-01-01"),
            (1, "S1B", "PAM-001", "By Pendidikan", 8_000_000, "2026-01-01"),
            (1, "SMA", "PAM-001", "By Pendidikan", 2_000_000, "2026-01-01"),
        ]
    )
    conn.commit()
    conn.close()
    return path


def _fake_conn_factory(db_path):
    def _conn():
        c = sqlite3.connect(db_path)
        c.row_factory = sqlite3.Row
        return c
    return _conn


# ── get_pam_payments ─────────────────────────────────────────────────────────

def test_get_pam_payments_sorted_by_jenjang(monkeypatch, tmp_path):
    """S3 dulu, lalu S2, lalu S1 (total DESC dalam S1), lalu lainnya."""
    db = str(tmp_path / "t.db")
    _make_db(db)
    from app.modules.payment_memo import service as svc
    monkeypatch.setattr(svc, "get_conn", _fake_conn_factory(db))

    rows = svc.get_pam_payments("PAM-001", 1)

    codes = [r["siswa_code"] for r in rows]
    # S3 dulu, S2, lalu S1B (8jt) sebelum S1A (5jt), lalu SMA
    assert codes == ["S3A", "S2A", "S1B", "S1A", "SMA"]


def test_get_pam_payments_jenjang_field_present(monkeypatch, tmp_path):
    """Setiap row harus punya field jenjang."""
    db = str(tmp_path / "t.db")
    _make_db(db)
    from app.modules.payment_memo import service as svc
    monkeypatch.setattr(svc, "get_conn", _fake_conn_factory(db))

    rows = svc.get_pam_payments("PAM-001", 1)
    assert all("jenjang" in r for r in rows)


def test_get_pam_payments_empty(monkeypatch, tmp_path):
    """PAM yang tidak ada returns list kosong."""
    db = str(tmp_path / "t.db")
    _make_db(db)
    from app.modules.payment_memo import service as svc
    monkeypatch.setattr(svc, "get_conn", _fake_conn_factory(db))

    rows = svc.get_pam_payments("PAM-NOTEXIST", 1)
    assert rows == []
```

- [ ] **Step 2: Jalankan test — pastikan FAIL**

```
cd C:\Financehub
python -m pytest tests/test_payment_memo_sort.py::test_get_pam_payments_sorted_by_jenjang -v
```

Expected: `FAILED` — karena `get_pam_payments` belum sort by jenjang dan belum ada field `jenjang`.

- [ ] **Step 3: Tambah konstanta `_JENJANG_SORT` di `service.py`**

Buka `app/modules/payment_memo/service.py`. Cari blok konstanta di sekitar baris 227 (dekat `_PILLAR_LINES_TABLE`). Tambahkan **setelah** `_VALID_PILLARS`:

```python
_JENJANG_SORT = {"S3": 0, "S2": 1, "S1": 2}
```

- [ ] **Step 4: Update fungsi `get_pam_payments` di `service.py`**

Cari fungsi `get_pam_payments` (sekitar baris 674). Ganti seluruh fungsi dengan:

```python
def get_pam_payments(pam_no: str, company_id: int) -> list:
    from collections import defaultdict
    conn = get_conn()
    rows = [dict(r) for r in conn.execute(
        """SELECT pb.id, pb.siswa_code, pb.cat1, pb.cat2,
                  pb.amount, pb.tanggal,
                  s.nama, s.bank, s.norek, s.namarek, s.jenjang
           FROM payment_beasiswa pb
           LEFT JOIN siswa s
             ON s.company_id = pb.company_id AND s.code = pb.siswa_code
           WHERE pb.pam = ? AND pb.company_id = ?""",
        (pam_no, company_id)
    ).fetchall()]
    conn.close()
    if not rows:
        return rows
    totals: dict = defaultdict(float)
    jenjang_of: dict = {}
    for r in rows:
        code = r.get("siswa_code") or ""
        totals[code] += float(r.get("amount") or 0)
        if code not in jenjang_of:
            jenjang_of[code] = (r.get("jenjang") or "").upper()
    rows.sort(key=lambda r: (
        _JENJANG_SORT.get(jenjang_of.get(r.get("siswa_code") or "", ""), 99),
        -totals.get(r.get("siswa_code") or "", 0.0),
    ))
    return rows
```

- [ ] **Step 5: Jalankan semua test Task 1 — pastikan PASS**

```
python -m pytest tests/test_payment_memo_sort.py::test_get_pam_payments_sorted_by_jenjang tests/test_payment_memo_sort.py::test_get_pam_payments_jenjang_field_present tests/test_payment_memo_sort.py::test_get_pam_payments_empty -v
```

Expected: `3 passed`

- [ ] **Step 6: Pastikan test lama tidak rusak**

```
python -m pytest tests/ -v
```

Expected: semua test lama tetap `PASS`.

- [ ] **Step 7: Commit**

```
git add app/modules/payment_memo/service.py tests/test_payment_memo_sort.py
git commit -m "feat: sort get_pam_payments by jenjang DESC total"
```

---

### Task 2: Update `get_pam_payments_detail`

**Files:**
- Modify: `app/modules/payment_memo/service.py` (fungsi `get_pam_payments_detail`, sekitar baris 691)
- Modify: `tests/test_payment_memo_sort.py` (tambah test baru di bawah)

- [ ] **Step 1: Tambah failing test untuk `get_pam_payments_detail`**

Buka `tests/test_payment_memo_sort.py`. Tambahkan di bagian bawah file:

```python
# ── get_pam_payments_detail ───────────────────────────────────────────────────

def test_get_pam_payments_detail_sorted_by_jenjang(monkeypatch, tmp_path):
    """
    result list harus diurutkan: S3 dulu, S2, lalu S1 (total DESC dalam S1), lalu lainnya.
    Field 'no' harus mengikuti urutan baru (1=S3, 2=S2, 3=S1B, 4=S1A, 5=SMA).
    """
    db = str(tmp_path / "t.db")
    _make_db(db)
    from app.modules.payment_memo import service as svc
    monkeypatch.setattr(svc, "get_conn", _fake_conn_factory(db))

    result = svc.get_pam_payments_detail("PAM-001", 1)

    codes = [r["siswa_code"] for r in result]
    assert codes == ["S3A", "S2A", "S1B", "S1A", "SMA"]


def test_get_pam_payments_detail_no_renumbered(monkeypatch, tmp_path):
    """Field 'no' harus 1,2,3,4,5 sesuai urutan jenjang, bukan urutan DB."""
    db = str(tmp_path / "t.db")
    _make_db(db)
    from app.modules.payment_memo import service as svc
    monkeypatch.setattr(svc, "get_conn", _fake_conn_factory(db))

    result = svc.get_pam_payments_detail("PAM-001", 1)

    nos = [r["no"] for r in result]
    assert nos == [1, 2, 3, 4, 5]


def test_get_pam_payments_detail_empty(monkeypatch, tmp_path):
    """PAM yang tidak ada returns list kosong."""
    db = str(tmp_path / "t.db")
    _make_db(db)
    from app.modules.payment_memo import service as svc
    monkeypatch.setattr(svc, "get_conn", _fake_conn_factory(db))

    result = svc.get_pam_payments_detail("PAM-NOTEXIST", 1)
    assert result == []
```

- [ ] **Step 2: Jalankan test — pastikan FAIL**

```
python -m pytest tests/test_payment_memo_sort.py::test_get_pam_payments_detail_sorted_by_jenjang -v
```

Expected: `FAILED` — karena saat ini `get_pam_payments_detail` ORDER BY `pb.siswa_code, pb.id` dan tidak sort by jenjang.

- [ ] **Step 3: Update fungsi `get_pam_payments_detail` di `service.py`**

Cari fungsi `get_pam_payments_detail` (sekitar baris 691). Ada **dua perubahan**:

**Perubahan 1 — SQL ORDER BY** (baris terakhir SQL query, sekitar baris 702):

Ganti:
```python
           ORDER BY pb.siswa_code, pb.id""",
```

Dengan:
```python
           ORDER BY CASE s.jenjang
               WHEN 'S3' THEN 1
               WHEN 'S2' THEN 2
               WHEN 'S1' THEN 3
               ELSE 99
           END, pb.siswa_code, pb.id""",
```

**Perubahan 2 — sort `result` dan renumber `no`** (tambahkan sebelum `return result`):

Cari baris `return result` di akhir fungsi `get_pam_payments_detail`. Tambahkan **sebelum** return:

```python
    result.sort(key=lambda x: (
        _JENJANG_SORT.get((x.get("jenjang") or "").upper(), 99),
        -float(x.get("total_pembayaran") or 0),
    ))
    for i, item in enumerate(result, 1):
        item["no"] = i
```

- [ ] **Step 4: Jalankan semua test Task 2 — pastikan PASS**

```
python -m pytest tests/test_payment_memo_sort.py::test_get_pam_payments_detail_sorted_by_jenjang tests/test_payment_memo_sort.py::test_get_pam_payments_detail_no_renumbered tests/test_payment_memo_sort.py::test_get_pam_payments_detail_empty -v
```

Expected: `3 passed`

- [ ] **Step 5: Jalankan seluruh test suite**

```
python -m pytest tests/ -v
```

Expected: semua test `PASS`, tidak ada regresi.

- [ ] **Step 6: Commit**

```
git add app/modules/payment_memo/service.py tests/test_payment_memo_sort.py
git commit -m "feat: sort get_pam_payments_detail by jenjang DESC total, renumber no"
```

---

## Self-Review

**Spec coverage:**
- ✅ Sort S3→S2→S1→lainnya: dicover Task 1 + Task 2
- ✅ Secondary sort total DESC: dicover oleh test `S1B(8jt)` sebelum `S1A(5jt)`
- ✅ Form display: otomatis via route yang memanggil kedua fungsi
- ✅ PDF (Rangkuman + Detail): otomatis via `get_pam_payments` + `get_pam_payments_detail`
- ✅ Excel (Rangkuman + Detail): otomatis via fungsi yang sama
- ✅ Edge case NULL jenjang → bucket 99: dicover oleh siswa "SMA" di test (jenjang `SD/SMP/SMA` → `_JENJANG_SORT.get(...)` returns `99`)

**Placeholder scan:** Tidak ada TBD atau TODO.

**Type consistency:** `_JENJANG_SORT` dipakai di Task 1 (step 3) dan Task 2 (step 3) — nama dan tipe dict sama.
