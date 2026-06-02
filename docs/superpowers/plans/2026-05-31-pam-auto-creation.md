# PAM Auto-Creation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When `add_payment_multi()` is called, automatically create a `pam_records` row within the same atomic transaction — populated with PAM No, GL Account, Cost Center, Keterangan (student names), total amount, and Due Date.

**Architecture:** New `pam_records` table (separate from existing `payment_memo`) is inserted atomically inside `add_payment_multi()`. PAM-specific service functions live in `payment_memo/service.py` and are imported by `beasiswa/service.py`. The Payment Memo page gains a PAM tab showing all PAM records with an editable GL Account dropdown backed by a new `coa` table.

**Tech Stack:** Python 3.11, Flask, SQLite (WAL), Jinja2, vanilla JS fetch API

---

## File Map

| File | Change |
|---|---|
| `app/config.py` | Add `COA_LIST` constant |
| `app/database.py` | Add `pam_records` + `coa` DDL; seed COA in `init_db()`; add migration |
| `app/modules/payment_memo/service.py` | Add: `_add_one_month`, `generate_pam_number`, `create_pam_record`, `get_pam_list`, `get_coa_list`, `update_pam_gl_account` |
| `app/modules/beasiswa/service.py` | Refactor `add_payment_multi()`: remove `pam` param, add `company_code`, call `create_pam_record` |
| `app/modules/beasiswa/routes.py` | Update `payment_tambah_multi` route: pass `company_code`, drop `pam` from payload |
| `app/modules/payment_memo/routes.py` | Add 3 routes: GET `/pam`, POST `/pam/<id>/gl-account`, GET `/coa` |
| `app/templates/payment_memo/index.html` | Add PAM tab: table with GL dropdown, auto-loaded on tab switch |
| `app/tests/test_pam_service.py` | Create: tests for all PAM service functions |
| `app/tests/test_beasiswa_service.py` | Modify: update `add_payment_multi` call + add PAM assertions |

---

## Task 1: COA Config + Database DDL

**Files:**
- Modify: `app/config.py`
- Modify: `app/database.py`

- [ ] **Step 1: Add COA_LIST to config.py**

  Open `app/config.py` and add this block at the end:

  ```python
  # Chart of Accounts — seed data for coa table + GL Account dropdown
  COA_LIST = [
      {"gl_code": "70107800", "gl_name": "Sponsorship Expense"},
      {"gl_code": "70107500", "gl_name": "Social Donation Expense"},
      {"gl_code": "70110220", "gl_name": "CSR Expense"},
      {"gl_code": "70110230", "gl_name": "Scholarship Expense"},
      {"gl_code": "70109100", "gl_name": "Communication Expense - 3rd Party"},
      {"gl_code": "70110100", "gl_name": "Professional International Organization Expense"},
      {"gl_code": "70110110", "gl_name": "Professional National Organization Expense"},
      {"gl_code": "70111130", "gl_name": "Consultant Fee"},
      {"gl_code": "70108100", "gl_name": "Office Equipment Expense"},
      {"gl_code": "70111132", "gl_name": "Biaya Jasa Konsultan – Affiliasi"},
      {"gl_code": "70107200", "gl_name": "Entertainment Expense"},
      {"gl_code": "70119310", "gl_name": "Gift Expense"},
      {"gl_code": "70106300", "gl_name": "Overseas Travel Expense"},
      {"gl_code": "70107600", "gl_name": "Office Consumption"},
  ]

  PAM_DEFAULT_GL       = "70110230"
  PAM_DEFAULT_REQUESTOR = "Jany Turkanda"
  ```

  > Note: 70108100 and 70110110 appeared twice in source data with different names — only the first occurrence is kept since `gl_code` is the primary key.

- [ ] **Step 2: Add DDL to database.py**

  In `app/database.py`, add these two `CREATE TABLE` blocks inside the `DDL` string, after the `klaim_medical` block:

  ```sql
  CREATE TABLE IF NOT EXISTS pam_records (
      id              INTEGER PRIMARY KEY AUTOINCREMENT,
      company_id      INTEGER NOT NULL REFERENCES companies(id),
      pam_no          TEXT UNIQUE NOT NULL,
      pam_date        TEXT,
      gl_account      TEXT DEFAULT '70110230',
      cost_center     TEXT,
      pt              TEXT,
      requestors_name TEXT DEFAULT 'Jany Turkanda',
      keterangan      TEXT,
      total_amount    REAL DEFAULT 0,
      due_date        TEXT,
      status          TEXT DEFAULT 'draft',
      created_at      TEXT DEFAULT CURRENT_TIMESTAMP,
      updated_at      TEXT
  );

  CREATE TABLE IF NOT EXISTS coa (
      gl_code   TEXT PRIMARY KEY,
      gl_name   TEXT NOT NULL,
      is_active INTEGER DEFAULT 1
  );
  ```

- [ ] **Step 3: Seed COA in init_db()**

  In `app/database.py`, inside `init_db()`, after the companies seed loop, add:

  ```python
  for entry in config.COA_LIST:
      conn.execute(
          "INSERT OR IGNORE INTO coa (gl_code, gl_name) VALUES (?, ?)",
          (entry["gl_code"], entry["gl_name"])
      )
  ```

- [ ] **Step 4: Add migration for pam_records and coa**

  In `app/database.py`, inside `migrate_db()`, add at the end:

  ```python
  # pam_records table (new — safe to run on existing DBs)
  try:
      conn.execute(
          """CREATE TABLE IF NOT EXISTS pam_records (
              id              INTEGER PRIMARY KEY AUTOINCREMENT,
              company_id      INTEGER NOT NULL,
              pam_no          TEXT UNIQUE NOT NULL,
              pam_date        TEXT,
              gl_account      TEXT DEFAULT '70110230',
              cost_center     TEXT,
              pt              TEXT,
              requestors_name TEXT DEFAULT 'Jany Turkanda',
              keterangan      TEXT,
              total_amount    REAL DEFAULT 0,
              due_date        TEXT,
              status          TEXT DEFAULT 'draft',
              created_at      TEXT DEFAULT CURRENT_TIMESTAMP,
              updated_at      TEXT)"""
      )
      conn.commit()
  except Exception:
      pass

  # coa table (new)
  try:
      conn.execute(
          "CREATE TABLE IF NOT EXISTS coa (gl_code TEXT PRIMARY KEY, gl_name TEXT NOT NULL, is_active INTEGER DEFAULT 1)"
      )
      for entry in config.COA_LIST:
          conn.execute(
              "INSERT OR IGNORE INTO coa (gl_code, gl_name) VALUES (?, ?)",
              (entry["gl_code"], entry["gl_name"])
          )
      conn.commit()
  except Exception:
      pass
  ```

- [ ] **Step 5: Verify tables created**

  ```bash
  cd C:/Financehub/app
  python -c "
  import config
  config.DB_PATH = '/tmp/verify_test.db'
  from database import init_db, get_conn
  init_db()
  c = get_conn()
  tables = [r[0] for r in c.execute(\"SELECT name FROM sqlite_master WHERE type='table'\").fetchall()]
  print(tables)
  assert 'pam_records' in tables, 'pam_records missing'
  assert 'coa' in tables, 'coa missing'
  coa_count = c.execute('SELECT COUNT(*) FROM coa').fetchone()[0]
  print(f'COA entries: {coa_count}')
  assert coa_count == 14, f'Expected 14, got {coa_count}'
  c.close()
  import os; os.remove('/tmp/verify_test.db')
  print('OK')
  "
  ```

  Expected output:
  ```
  [..., 'pam_records', 'coa']
  COA entries: 14
  OK
  ```

- [ ] **Step 6: Commit**

  ```bash
  git add app/config.py app/database.py
  git commit -m "feat(pam): add pam_records + coa DDL, COA_LIST config, seed COA"
  ```

---

## Task 2: PAM Service Functions + Tests

**Files:**
- Create: `app/tests/test_pam_service.py`
- Modify: `app/modules/payment_memo/service.py`

- [ ] **Step 1: Write failing tests**

  Create `app/tests/test_pam_service.py`:

  ```python
  # tests/test_pam_service.py
  import os, sys, pytest, calendar
  sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
  import config
  config.DB_PATH = os.path.join(os.path.dirname(__file__), "test_finance_hub.db")

  from database import init_db, get_conn
  from modules.payment_memo.service import (
      generate_pam_number, create_pam_record,
      get_pam_list, get_coa_list, update_pam_gl_account,
  )

  COMPANY_ID   = 2   # ETF
  COMPANY_CODE = "ETF"

  @pytest.fixture(autouse=True)
  def clean_db():
      if os.path.exists(config.DB_PATH):
          os.remove(config.DB_PATH)
      init_db()
      yield
      if os.path.exists(config.DB_PATH):
          os.remove(config.DB_PATH)


  def test_generate_pam_number_first():
      conn = get_conn()
      no = generate_pam_number(COMPANY_ID, COMPANY_CODE, "2026", conn)
      conn.close()
      assert no == "PAM/ETF/2026/001"


  def test_generate_pam_number_increments():
      conn = get_conn()
      no1 = generate_pam_number(COMPANY_ID, COMPANY_CODE, "2026", conn)
      conn.execute(
          """INSERT INTO pam_records (company_id, pam_no, pam_date, gl_account,
             cost_center, pt, requestors_name, keterangan, total_amount, due_date)
             VALUES (?,?,?,?,?,?,?,?,?,?)""",
          (COMPANY_ID, no1, "2026-05-31", "70110230", "", "PT. SMART Tbk",
           "Jany Turkanda", "Harry, Joni", 5000000, "2026-06-30")
      )
      conn.commit()
      no2 = generate_pam_number(COMPANY_ID, COMPANY_CODE, "2026", conn)
      conn.close()
      assert no2 == "PAM/ETF/2026/002"


  def test_get_coa_list_returns_14():
      coa = get_coa_list()
      assert len(coa) == 14
      codes = [c["gl_code"] for c in coa]
      assert "70110230" in codes   # default
      assert "70107800" in codes   # Sponsorship


  def test_create_pam_record_inserts_row():
      conn = get_conn()
      pam_no = create_pam_record(conn, COMPANY_ID, COMPANY_CODE, {
          "pam_date":       "2026-05-31",
          "pt":             "PT. SMART Tbk",
          "keterangan":     "Harry, Joni",
          "total_amount":   7500000.0,
          "payment_ids":    [],
      })
      conn.commit()
      row = conn.execute(
          "SELECT * FROM pam_records WHERE pam_no=?", (pam_no,)
      ).fetchone()
      conn.close()
      assert row is not None
      assert row["pam_no"]          == "PAM/ETF/2026/001"
      assert row["gl_account"]      == "70110230"
      assert row["cost_center"]     == "1008C1POFF"   # SMART Tbk
      assert row["requestors_name"] == "Jany Turkanda"
      assert row["keterangan"]      == "Harry, Joni"
      assert row["total_amount"]    == 7500000.0
      assert row["due_date"]        == "2026-06-30"
      assert row["status"]          == "draft"


  def test_create_pam_record_updates_payment_pam_field():
      conn = get_conn()
      # Insert a payment_beasiswa row first
      cur = conn.execute(
          """INSERT INTO payment_beasiswa
             (company_id, siswa_code, cat1, cat2, tanggal, amount, pillar, perusahaan, status)
             VALUES (?,?,?,?,?,?,?,?,?)""",
          (COMPANY_ID, "S001", "By Pendidikan", "Semester 1",
           "2026-05-31", 2000000, "AGRI", "PT. SMART Tbk", "draft")
      )
      payment_id = cur.lastrowid
      pam_no = create_pam_record(conn, COMPANY_ID, COMPANY_CODE, {
          "pam_date":     "2026-05-31",
          "pt":           "PT. SMART Tbk",
          "keterangan":   "Harry",
          "total_amount": 2000000.0,
          "payment_ids":  [payment_id],
      })
      conn.commit()
      pb_row = conn.execute(
          "SELECT pam FROM payment_beasiswa WHERE id=?", (payment_id,)
      ).fetchone()
      conn.close()
      assert pb_row["pam"] == pam_no


  def test_get_pam_list_empty():
      result = get_pam_list(COMPANY_ID)
      assert result == []


  def test_get_pam_list_returns_inserted():
      conn = get_conn()
      create_pam_record(conn, COMPANY_ID, COMPANY_CODE, {
          "pam_date": "2026-05-31", "pt": "PT. SMART Tbk",
          "keterangan": "Harry", "total_amount": 1000000.0, "payment_ids": [],
      })
      conn.commit()
      conn.close()
      rows = get_pam_list(COMPANY_ID)
      assert len(rows) == 1
      assert rows[0]["pam_no"] == "PAM/ETF/2026/001"


  def test_update_pam_gl_account_success():
      conn = get_conn()
      pam_no = create_pam_record(conn, COMPANY_ID, COMPANY_CODE, {
          "pam_date": "2026-05-31", "pt": "PT. SMART Tbk",
          "keterangan": "Harry", "total_amount": 1000000.0, "payment_ids": [],
      })
      conn.commit()
      pam_id = conn.execute(
          "SELECT id FROM pam_records WHERE pam_no=?", (pam_no,)
      ).fetchone()["id"]
      conn.close()
      result = update_pam_gl_account(pam_id, "70107800", COMPANY_ID)
      assert result["ok"] is True
      conn2 = get_conn()
      row = conn2.execute("SELECT gl_account FROM pam_records WHERE id=?", (pam_id,)).fetchone()
      conn2.close()
      assert row["gl_account"] == "70107800"


  def test_update_pam_gl_account_invalid_code():
      conn = get_conn()
      pam_no = create_pam_record(conn, COMPANY_ID, COMPANY_CODE, {
          "pam_date": "2026-05-31", "pt": "PT. SMART Tbk",
          "keterangan": "Harry", "total_amount": 1000000.0, "payment_ids": [],
      })
      conn.commit()
      pam_id = conn.execute(
          "SELECT id FROM pam_records WHERE pam_no=?", (pam_no,)
      ).fetchone()["id"]
      conn.close()
      result = update_pam_gl_account(pam_id, "99999999", COMPANY_ID)
      assert result["ok"] is False
  ```

- [ ] **Step 2: Run tests — expect all to FAIL**

  ```bash
  cd C:/Financehub/app
  python -m pytest tests/test_pam_service.py -v 2>&1 | head -40
  ```

  Expected: `ImportError` or `FAILED` for all tests (functions not yet defined).

- [ ] **Step 3: Add helper + PAM functions to payment_memo/service.py**

  At the top of `app/modules/payment_memo/service.py`, add `import calendar` alongside existing imports.

  Then add these functions **before** `export_memo_pdf` (to keep file under 500 lines, confirm current line count first with `wc -l app/modules/payment_memo/service.py`):

  ```python
  # ── PAM helpers ─────────────────────────────────────────────────────────────

  def _add_one_month(date_str: str) -> str:
      try:
          dt    = datetime.strptime(date_str, "%Y-%m-%d")
          month = dt.month % 12 + 1
          year  = dt.year + (1 if dt.month == 12 else 0)
          day   = min(dt.day, calendar.monthrange(year, month)[1])
          return datetime(year, month, day).strftime("%Y-%m-%d")
      except ValueError:
          return date_str


  def generate_pam_number(company_id: int, company_code: str, year: str,
                          conn=None) -> str:
      prefix   = f"PAM/{company_code}/{year}/"
      pattern  = re.compile(rf"PAM/{re.escape(company_code)}/{re.escape(year)}/(\d+)")
      owns_conn = conn is None
      if owns_conn:
          conn = get_conn()
      rows = conn.execute(
          "SELECT pam_no FROM pam_records WHERE company_id=? AND pam_no LIKE ?",
          (company_id, prefix + "%")
      ).fetchall()
      if owns_conn:
          conn.close()
      max_seq = 0
      for row in rows:
          m = pattern.match(row["pam_no"])
          if m:
              seq = int(m.group(1))
              if seq > max_seq:
                  max_seq = seq
      return f"{prefix}{max_seq + 1:03d}"


  def create_pam_record(conn, company_id: int, company_code: str,
                        data: dict) -> str:
      pam_date    = data.get("pam_date") or _ts()[:10]
      year        = pam_date[:4]
      pam_no      = generate_pam_number(company_id, company_code, year, conn)
      due_date    = _add_one_month(pam_date)
      cost_center = config.COST_CENTER_MAP.get(data.get("pt", ""), "")
      conn.execute(
          """INSERT INTO pam_records
             (company_id, pam_no, pam_date, gl_account, cost_center, pt,
              requestors_name, keterangan, total_amount, due_date, status, created_at)
             VALUES (?,?,?,?,?,?,?,?,?,?,'draft',?)""",
          (company_id, pam_no, pam_date,
           data.get("gl_account", config.PAM_DEFAULT_GL),
           cost_center, data.get("pt", ""),
           data.get("requestors_name", config.PAM_DEFAULT_REQUESTOR),
           data.get("keterangan", ""),
           float(data.get("total_amount", 0)),
           due_date, _ts())
      )
      for pid in data.get("payment_ids", []):
          conn.execute(
              "UPDATE payment_beasiswa SET pam=? WHERE id=?", (pam_no, pid)
          )
      return pam_no


  def get_pam_list(company_id: int, search: str = "", bulan: str = "",
                   tahun: str = "") -> list:
      sql    = "SELECT * FROM pam_records WHERE company_id=?"
      params = [company_id]
      if search:
          q       = f"%{search}%"
          sql    += " AND (pam_no LIKE ? OR pt LIKE ? OR keterangan LIKE ?)"
          params += [q, q, q]
      if bulan:
          sql    += " AND strftime('%m', pam_date)=?"
          params += [bulan.zfill(2)]
      if tahun:
          sql    += " AND strftime('%Y', pam_date)=?"
          params += [tahun]
      sql += " ORDER BY created_at DESC"
      conn = get_conn()
      rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
      conn.close()
      return rows


  def get_coa_list() -> list:
      conn = get_conn()
      rows = [dict(r) for r in conn.execute(
          "SELECT gl_code, gl_name FROM coa WHERE is_active=1 ORDER BY gl_code"
      ).fetchall()]
      conn.close()
      return rows


  def update_pam_gl_account(pam_id: int, gl_account: str,
                             company_id: int) -> dict:
      conn = get_conn()
      # Validate gl_account exists in COA
      coa = conn.execute(
          "SELECT gl_code FROM coa WHERE gl_code=? AND is_active=1", (gl_account,)
      ).fetchone()
      if not coa:
          conn.close()
          return {"ok": False, "pesan": f"GL Account '{gl_account}' tidak ditemukan di COA."}
      row = conn.execute(
          "SELECT id FROM pam_records WHERE id=? AND company_id=?",
          (pam_id, company_id)
      ).fetchone()
      if not row:
          conn.close()
          return {"ok": False, "pesan": "PAM record tidak ditemukan."}
      conn.execute(
          "UPDATE pam_records SET gl_account=?, updated_at=? WHERE id=? AND company_id=?",
          (gl_account, _ts(), pam_id, company_id)
      )
      conn.commit()
      conn.close()
      return {"ok": True, "pesan": f"GL Account diubah ke {gl_account}."}
  ```

  Also add `import config` at the top of `payment_memo/service.py` if not already present.

- [ ] **Step 4: Run tests — expect all to PASS**

  ```bash
  cd C:/Financehub/app
  python -m pytest tests/test_pam_service.py -v
  ```

  Expected:
  ```
  tests/test_pam_service.py::test_generate_pam_number_first PASSED
  tests/test_pam_service.py::test_generate_pam_number_increments PASSED
  tests/test_pam_service.py::test_get_coa_list_returns_14 PASSED
  tests/test_pam_service.py::test_create_pam_record_inserts_row PASSED
  tests/test_pam_service.py::test_create_pam_record_updates_payment_pam_field PASSED
  tests/test_pam_service.py::test_get_pam_list_empty PASSED
  tests/test_pam_service.py::test_get_pam_list_returns_inserted PASSED
  tests/test_pam_service.py::test_update_pam_gl_account_success PASSED
  tests/test_pam_service.py::test_update_pam_gl_account_invalid_code PASSED
  9 passed
  ```

- [ ] **Step 5: Run full test suite — no regressions**

  ```bash
  cd C:/Financehub/app
  python -m pytest --tb=short -q
  ```

  Expected: all existing tests still pass.

- [ ] **Step 6: Commit**

  ```bash
  git add app/modules/payment_memo/service.py app/tests/test_pam_service.py
  git commit -m "feat(pam): PAM service functions (generate_pam_number, create_pam_record, get_pam_list, get_coa_list, update_pam_gl)"
  ```

---

## Task 3: Extend add_payment_multi() + Update Route

**Files:**
- Modify: `app/modules/beasiswa/service.py`
- Modify: `app/modules/beasiswa/routes.py`
- Modify: `app/tests/test_beasiswa_service.py`

- [ ] **Step 1: Update existing test to use new signature + add PAM assertions**

  In `app/tests/test_beasiswa_service.py`, update the import block to add `add_payment_multi`:

  ```python
  from modules.beasiswa.service import (
      generate_kode_siswa, get_siswa_list, add_siswa, update_siswa,
      add_budget_batch, add_payment_batch, add_payment_multi,
      get_rekap, get_sisa_budget,
      add_klaim_multi, get_klaim_list, delete_klaim_row,
  )
  from database import get_conn
  ```

  Add this test function at the end of `test_beasiswa_service.py`:

  ```python
  def test_add_payment_multi_creates_pam_record():
      # Seed a siswa first
      add_siswa(COMPANY_ID, {
          "code": "1250001", "nama": "Harry Santoso", "jenjang": "S1",
          "angkatan": 2025, "program": "SMART", "fakultas": "Teknik",
          "universitas": "UI", "bank": "BCA", "norek": "111", "namarek": "Harry",
          "referensi": "", "status": "Aktif", "catatan": "",
      })
      add_siswa(COMPANY_ID, {
          "code": "1250002", "nama": "Joni Pratama", "jenjang": "S1",
          "angkatan": 2025, "program": "SMART", "fakultas": "Ekonomi",
          "universitas": "UGM", "bank": "BNI", "norek": "222", "namarek": "Joni",
          "referensi": "", "status": "Aktif", "catatan": "",
      })

      rows = [
          {"siswa_code": "1250001", "cat1": "By Pendidikan", "cat2": "Semester 1",
           "amount": "3000000", "cat3": "", "cat4": "",
           "tgl_pengajuan": "", "tgl_receive": "", "tgl_pa": "", "tgl_final": ""},
          {"siswa_code": "1250002", "cat1": "By Pendidikan", "cat2": "Semester 1",
           "amount": "3500000", "cat3": "", "cat4": "",
           "tgl_pengajuan": "", "tgl_receive": "", "tgl_pa": "", "tgl_final": ""},
      ]

      result = add_payment_multi(
          company_id=COMPANY_ID,
          company_code="ETF",
          tanggal="2026-05-31",
          pillar="AGRI",
          perusahaan="PT. SMART Tbk",
          rows=rows,
      )

      assert result["ok"] is True
      assert result["saved"] == 2
      assert "pam_no" in result
      assert result["pam_no"].startswith("PAM/ETF/2026/")

      conn = get_conn()
      pam = conn.execute(
          "SELECT * FROM pam_records WHERE pam_no=?", (result["pam_no"],)
      ).fetchone()
      assert pam is not None
      assert pam["gl_account"]  == "70110230"
      assert pam["cost_center"] == "1008C1POFF"
      assert "Harry" in pam["keterangan"]
      assert "Joni"  in pam["keterangan"]
      assert pam["total_amount"] == 6500000.0
      assert pam["due_date"]     == "2026-06-30"

      # payment_beasiswa rows must have pam set
      pb_rows = conn.execute(
          "SELECT pam FROM payment_beasiswa WHERE company_id=?", (COMPANY_ID,)
      ).fetchall()
      conn.close()
      for pb in pb_rows:
          assert pb["pam"] == result["pam_no"]


  def test_add_payment_multi_zero_rows_no_pam():
      rows = [
          {"siswa_code": "X001", "cat1": "By Pendidikan", "cat2": "Semester 1",
           "amount": "0", "cat3": "", "cat4": "",
           "tgl_pengajuan": "", "tgl_receive": "", "tgl_pa": "", "tgl_final": ""},
      ]
      result = add_payment_multi(
          company_id=COMPANY_ID, company_code="ETF",
          tanggal="2026-05-31", pillar="AGRI",
          perusahaan="PT. SMART Tbk", rows=rows,
      )
      assert result["ok"] is False
      conn = get_conn()
      count = conn.execute("SELECT COUNT(*) FROM pam_records").fetchone()[0]
      conn.close()
      assert count == 0   # No PAM created when no valid rows
  ```

- [ ] **Step 2: Run new tests — expect FAIL**

  ```bash
  cd C:/Financehub/app
  python -m pytest tests/test_beasiswa_service.py::test_add_payment_multi_creates_pam_record tests/test_beasiswa_service.py::test_add_payment_multi_zero_rows_no_pam -v
  ```

  Expected: `FAILED` (wrong number of arguments or missing `company_code`).

- [ ] **Step 3: Refactor add_payment_multi() in beasiswa/service.py**

  Add the import at the top of `app/modules/beasiswa/service.py`:

  ```python
  from modules.payment_memo.service import create_pam_record, generate_pam_number
  ```

  Replace the entire `add_payment_multi` function with:

  ```python
  def add_payment_multi(company_id: int, company_code: str, tanggal: str,
                        pillar: str, perusahaan: str, rows: list) -> dict:
      conn  = get_conn()
      saved = 0
      payment_ids: list[int] = []
      total = 0.0

      try:
          for row in rows:
              try:
                  amount = float(str(row.get("amount", 0)).replace(",", ""))
              except (ValueError, TypeError):
                  amount = 0
              if amount <= 0:
                  continue
              siswa_code = (row.get("siswa_code") or "").strip()
              cur = conn.execute(
                  """INSERT INTO payment_beasiswa
                     (company_id,siswa_code,cat1,cat2,tanggal,amount,pillar,perusahaan,
                      tgl_pengajuan,tgl_receive,tgl_pa,tgl_final,cat3,cat4,status)
                     VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,'draft')""",
                  (company_id, siswa_code,
                   row.get("cat1", ""), row.get("cat2", ""),
                   tanggal, amount, pillar, perusahaan,
                   row.get("tgl_pengajuan", ""), row.get("tgl_receive", ""),
                   row.get("tgl_pa", ""),   row.get("tgl_final", ""),
                   row.get("cat3", ""),     row.get("cat4", ""))
              )
              payment_ids.append(cur.lastrowid)
              total += amount
              saved += 1

          if saved == 0:
              conn.close()
              return {"ok": False, "pesan": "Tidak ada item dengan amount > 0.", "saved": 0}

          # Collect student names for keterangan
          unique_codes = list({
              (row.get("siswa_code") or "").strip()
              for row in rows
              if float(str(row.get("amount", 0)).replace(",", "") or 0) > 0
          })
          name_rows = []
          if unique_codes:
              placeholders = ",".join("?" * len(unique_codes))
              name_rows = conn.execute(
                  f"SELECT nama FROM siswa WHERE company_id=? AND code IN ({placeholders})",
                  [company_id] + unique_codes,
              ).fetchall()
          keterangan = ", ".join(r["nama"] for r in name_rows) if name_rows else ""

          pam_no = create_pam_record(conn, company_id, company_code, {
              "pam_date":     tanggal,
              "pt":           perusahaan,
              "keterangan":   keterangan,
              "total_amount": total,
              "payment_ids":  payment_ids,
          })

          conn.commit()
          return {
              "ok":    True,
              "pesan": f"{saved} payment berhasil disimpan (status: draft).",
              "saved": saved,
              "pam_no": pam_no,
          }

      except Exception as exc:
          conn.rollback()
          return {"ok": False, "pesan": f"Gagal menyimpan payment: {exc}", "saved": 0}
      finally:
          conn.close()
  ```

- [ ] **Step 4: Update the route in beasiswa/routes.py**

  Find the `payment_tambah_multi` route (currently at line ~409). Replace it with:

  ```python
  @bp.route("/payment/tambah-multi", methods=["POST"])
  @role_required("requester")
  def payment_tambah_multi():
      data = request.get_json(force=True) or {}
      rows = data.get("rows", [])
      if not rows:
          return jsonify({"ok": False, "pesan": "Tidak ada baris untuk disimpan."})
      return jsonify(add_payment_multi(
          _cid(),
          session.get("company_code", ""),
          data.get("tanggal", ""),
          data.get("pillar", ""),
          data.get("perusahaan", ""),
          rows,
      ))
  ```

  > Note: `session` is already imported via Flask at the top of routes.py. The `pam` key from the JSON payload is no longer read — the frontend should stop sending it.

- [ ] **Step 5: Run new tests — expect PASS**

  ```bash
  cd C:/Financehub/app
  python -m pytest tests/test_beasiswa_service.py::test_add_payment_multi_creates_pam_record tests/test_beasiswa_service.py::test_add_payment_multi_zero_rows_no_pam -v
  ```

  Expected: both `PASSED`.

- [ ] **Step 6: Run full test suite — no regressions**

  ```bash
  cd C:/Financehub/app
  python -m pytest --tb=short -q
  ```

  Expected: all tests pass.

- [ ] **Step 7: Commit**

  ```bash
  git add app/modules/beasiswa/service.py app/modules/beasiswa/routes.py app/tests/test_beasiswa_service.py
  git commit -m "feat(pam): auto-create PAM record in add_payment_multi() — atomic transaction"
  ```

---

## Task 4: PAM API Routes + Tests

**Files:**
- Modify: `app/modules/payment_memo/routes.py`
- Modify: `app/tests/test_memo_api.py`

- [ ] **Step 1: Write failing API tests**

  Open `app/tests/test_memo_api.py` and add at the end:

  ```python
  # ── PAM API tests ────────────────────────────────────────────────────────────

  def _get_token(client):
      """Helper: log in as admin and return auth header."""
      # Change password first (must_change_pw = 1 on fresh DB)
      client.post("/auth/change-password",
                  json={"old_password": "Admin@123", "new_password": "Test@1234"},
                  headers={"Authorization": "Bearer " + _login_token(client, "Admin@123")})
      token = _login_token(client, "Test@1234")
      return {"Authorization": f"Bearer {token}"}


  def _login_token(client, password):
      rv = client.post("/auth/login", json={"username": "admin", "password": password})
      return rv.get_json()["access_token"]


  def test_get_coa_list(client):
      token = _get_token(client)
      client.post("/auth/select-company", json={"company_id": 2},
                  headers=token)
      rv = client.get("/payment-memo/coa", headers=token)
      assert rv.status_code == 200
      data = rv.get_json()
      assert data["ok"] is True
      assert len(data["coa"]) == 14


  def test_get_pam_list_empty(client):
      token = _get_token(client)
      client.post("/auth/select-company", json={"company_id": 2}, headers=token)
      rv = client.get("/payment-memo/pam", headers=token)
      assert rv.status_code == 200
      data = rv.get_json()
      assert data["ok"] is True
      assert data["rows"] == []


  def test_update_pam_gl_account_via_api(client):
      from modules.payment_memo.service import create_pam_record
      from database import get_conn
      conn = get_conn()
      pam_no = create_pam_record(conn, 2, "ETF", {
          "pam_date": "2026-05-31", "pt": "PT. SMART Tbk",
          "keterangan": "Harry", "total_amount": 1000000.0, "payment_ids": [],
      })
      conn.commit()
      pam_id = conn.execute(
          "SELECT id FROM pam_records WHERE pam_no=?", (pam_no,)
      ).fetchone()["id"]
      conn.close()

      token = _get_token(client)
      client.post("/auth/select-company", json={"company_id": 2}, headers=token)
      rv = client.post(f"/payment-memo/pam/{pam_id}/gl-account",
                       json={"gl_account": "70107800"},
                       headers=token)
      assert rv.status_code == 200
      assert rv.get_json()["ok"] is True
  ```

  > Note: If `_get_token` / `_login_token` helpers already exist in `test_memo_api.py`, reuse them instead of redefining.

- [ ] **Step 2: Run new tests — expect FAIL (routes not yet defined)**

  ```bash
  cd C:/Financehub/app
  python -m pytest tests/test_memo_api.py::test_get_coa_list tests/test_memo_api.py::test_get_pam_list_empty tests/test_memo_api.py::test_update_pam_gl_account_via_api -v
  ```

  Expected: `FAILED` with 404.

- [ ] **Step 3: Add PAM routes to payment_memo/routes.py**

  Update the import at the top of `app/modules/payment_memo/routes.py`:

  ```python
  from modules.payment_memo.service import (
      get_draft_payments, create_memo, get_memo_list, get_memo_detail,
      update_memo_status, export_memo_pdf,
      get_pam_list, get_coa_list, update_pam_gl_account,
  )
  ```

  Add these three routes at the end of the file:

  ```python
  @bp.route("/coa")
  @role_required("requester", "verificator", "releaser")
  def list_coa():
      return jsonify({"ok": True, "coa": get_coa_list()})


  @bp.route("/pam")
  @role_required("requester", "verificator", "releaser")
  def list_pam():
      company_id = session.get("company_id")
      if not company_id:
          return jsonify({"ok": False, "pesan": "Perusahaan belum dipilih."}), 400
      rows = get_pam_list(
          company_id,
          search=request.args.get("search", ""),
          bulan=request.args.get("bulan", ""),
          tahun=request.args.get("tahun", ""),
      )
      return jsonify({"ok": True, "rows": rows})


  @bp.route("/pam/<int:pam_id>/gl-account", methods=["POST"])
  @role_required("verificator", "releaser")
  def update_gl_account(pam_id):
      data       = request.get_json(force=True) or {}
      gl_account = (data.get("gl_account") or "").strip()
      if not gl_account:
          return jsonify({"ok": False, "pesan": "GL Account wajib diisi."}), 400
      result = update_pam_gl_account(pam_id, gl_account, session.get("company_id", 0))
      return jsonify(result)
  ```

- [ ] **Step 4: Run API tests — expect PASS**

  ```bash
  cd C:/Financehub/app
  python -m pytest tests/test_memo_api.py::test_get_coa_list tests/test_memo_api.py::test_get_pam_list_empty tests/test_memo_api.py::test_update_pam_gl_account_via_api -v
  ```

  Expected: all 3 `PASSED`.

- [ ] **Step 5: Run full test suite**

  ```bash
  cd C:/Financehub/app
  python -m pytest --tb=short -q
  ```

  Expected: all tests pass.

- [ ] **Step 6: Commit**

  ```bash
  git add app/modules/payment_memo/routes.py app/tests/test_memo_api.py
  git commit -m "feat(pam): PAM API routes — GET /pam, POST /pam/<id>/gl-account, GET /coa"
  ```

---

## Task 5: Payment Memo Template — PAM Tab

**Files:**
- Modify: `app/templates/payment_memo/index.html`

- [ ] **Step 1: Add PAM tab trigger to existing tab bar**

  In `app/templates/payment_memo/index.html`, find the existing tab navigation (look for `<nav>`, `<ul>`, or buttons that switch tabs). Add a "PAM Records" tab button:

  ```html
  <button class="tab-btn" data-tab="pam" onclick="switchTab('pam')">PAM Records</button>
  ```

  Place it after the last existing tab button.

- [ ] **Step 2: Add PAM tab panel HTML**

  After the last existing tab panel `<div>`, add:

  ```html
  <!-- PAM Records Tab -->
  <div id="tab-pam" class="tab-panel" style="display:none;">
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:16px;">
      <h3 style="margin:0;">Payment Approval Memo (PAM)</h3>
      <input id="pam-search" type="text" placeholder="Cari PAM No / PT / Siswa..."
             class="mock-input" style="width:280px;"
             oninput="loadPAM()">
    </div>

    <div style="overflow-x:auto;">
      <table id="pam-table" style="width:100%;border-collapse:collapse;font-size:13px;">
        <thead>
          <tr style="background:#1e40af;color:#fff;">
            <th style="padding:8px 10px;">PAM No</th>
            <th style="padding:8px 10px;">PAM Date</th>
            <th style="padding:8px 10px;">PT</th>
            <th style="padding:8px 10px;">Cost Center</th>
            <th style="padding:8px 10px;min-width:220px;">GL Account</th>
            <th style="padding:8px 10px;">Requestor</th>
            <th style="padding:8px 10px;">Keterangan</th>
            <th style="padding:8px 10px;text-align:right;">Total (Rp)</th>
            <th style="padding:8px 10px;">Due Date</th>
            <th style="padding:8px 10px;">Status</th>
          </tr>
        </thead>
        <tbody id="pam-tbody">
          <tr><td colspan="10" style="text-align:center;padding:20px;color:#6b7280;">
            Memuat data...
          </td></tr>
        </tbody>
      </table>
    </div>
  </div>
  ```

- [ ] **Step 3: Add JavaScript for PAM tab**

  Inside the `<script>` block at the bottom of the template (or in the page's JS section), add:

  ```javascript
  let coaOptions = [];   // populated once on first PAM tab load

  async function loadCOA() {
    if (coaOptions.length) return;
    const res  = await fetch('/payment-memo/coa');
    const data = await res.json();
    if (data.ok) coaOptions = data.coa;
  }

  function buildGLDropdown(pamId, currentGl) {
    const select = document.createElement('select');
    select.className = 'mock-input';
    select.style.width = '100%';
    select.style.fontSize = '12px';
    coaOptions.forEach(opt => {
      const o = document.createElement('option');
      o.value = opt.gl_code;
      o.textContent = `${opt.gl_code} — ${opt.gl_name}`;
      if (opt.gl_code === currentGl) o.selected = true;
      select.appendChild(o);
    });
    select.onchange = () => updateGL(pamId, select.value);
    return select;
  }

  async function updateGL(pamId, glAccount) {
    const res  = await fetch(`/payment-memo/pam/${pamId}/gl-account`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ gl_account: glAccount }),
    });
    const data = await res.json();
    if (!data.ok) alert('Gagal update GL: ' + data.pesan);
  }

  async function loadPAM() {
    await loadCOA();
    const search = document.getElementById('pam-search')?.value || '';
    const res    = await fetch(`/payment-memo/pam?search=${encodeURIComponent(search)}`);
    const data   = await res.json();
    const tbody  = document.getElementById('pam-tbody');
    if (!data.ok || !data.rows.length) {
      tbody.innerHTML = '<tr><td colspan="10" style="text-align:center;padding:20px;color:#6b7280;">Belum ada PAM record.</td></tr>';
      return;
    }
    tbody.innerHTML = data.rows.map((r, i) => `
      <tr style="background:${i % 2 === 0 ? '#fff' : '#f8fafc'};">
        <td style="padding:7px 10px;font-weight:600;">${r.pam_no}</td>
        <td style="padding:7px 10px;">${r.pam_date || '-'}</td>
        <td style="padding:7px 10px;">${r.pt || '-'}</td>
        <td style="padding:7px 10px;font-family:monospace;font-size:11px;">${r.cost_center || '-'}</td>
        <td style="padding:7px 10px;" id="gl-cell-${r.id}"></td>
        <td style="padding:7px 10px;">${r.requestors_name || '-'}</td>
        <td style="padding:7px 10px;max-width:180px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;"
            title="${r.keterangan || ''}">${r.keterangan || '-'}</td>
        <td style="padding:7px 10px;text-align:right;">${Number(r.total_amount).toLocaleString('id-ID')}</td>
        <td style="padding:7px 10px;">${r.due_date || '-'}</td>
        <td style="padding:7px 10px;">
          <span style="background:${r.status==='draft'?'#fef3c7':r.status==='approved'?'#d1fae5':'#e0e7ff'};
                       padding:2px 8px;border-radius:9999px;font-size:11px;">
            ${r.status}
          </span>
        </td>
      </tr>
    `).join('');

    // Inject GL dropdowns after render
    data.rows.forEach(r => {
      const cell = document.getElementById(`gl-cell-${r.id}`);
      if (cell) cell.appendChild(buildGLDropdown(r.id, r.gl_account));
    });
  }

  // Auto-load PAM when tab is switched to 'pam'
  const _origSwitchTab = typeof switchTab === 'function' ? switchTab : null;
  function switchTab(tab) {
    if (_origSwitchTab) _origSwitchTab(tab);
    // fallback: show/hide panels if no existing switchTab
    document.querySelectorAll('.tab-panel').forEach(p => p.style.display = 'none');
    const panel = document.getElementById(`tab-${tab}`);
    if (panel) panel.style.display = 'block';
    if (tab === 'pam') loadPAM();
  }
  ```

  > **Note:** If the existing template already has a `switchTab` function, integrate the `loadPAM()` call into it instead of wrapping it. The pattern above is a safe fallback.

- [ ] **Step 4: Manual verification**

  Start the development server:

  ```bash
  cd C:/Financehub/app
  python run.py
  ```

  1. Log in → select company ETF
  2. Go to Payment Memo page (`/payment-memo/`)
  3. Click the **PAM Records** tab
  4. Confirm: table loads (empty if no payments submitted yet)
  5. Submit a payment via Beasiswa → Input Payment tab (multi-siswa)
  6. Return to Payment Memo → PAM Records tab → confirm PAM row appears with correct data:
     - PAM No: `PAM/ETF/<year>/<seq>`
     - GL Account dropdown shows 14 options, default selected is `70110230`
     - Cost Center: matches the PT
     - Keterangan: student names comma-joined
     - Due Date: exactly 1 month after PAM Date
  7. Change GL Account via dropdown → confirm no error toast

- [ ] **Step 5: Commit**

  ```bash
  git add app/templates/payment_memo/index.html
  git commit -m "feat(pam): PAM Records tab on Payment Memo page — table + editable GL dropdown"
  ```

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Covered in |
|---|---|
| PAM Date auto from payment input | Task 3 — `pam_date = tanggal` |
| PAM No auto-generated | Task 2 — `generate_pam_number()` |
| GL Account default 70110230, editable dropdown | Task 2 service + Task 4 route + Task 5 template |
| Cost Center from COST_CENTER_MAP[PT] | Task 2 — `create_pam_record()` |
| PT from payment input | Task 3 — `perusahaan` → `data["pt"]` |
| Requestor's Name default 'Jany Turkanda' | Task 2 — `config.PAM_DEFAULT_REQUESTOR` |
| Keterangan = joined student names | Task 3 — name query in `add_payment_multi()` |
| Column2 = total payment | Task 3 — `total` accumulation |
| Due Date = PAM Date + 1 month | Task 2 — `_add_one_month()` |
| COA stored as DB table | Task 1 — `coa` table + seed |
| GL Account saves to COA for journal | Task 1 — `coa` table with all 14 GL codes |
| Atomic transaction | Task 3 — try/except/rollback in `add_payment_multi()` |
| payment_beasiswa.pam auto-filled | Task 2 — `create_pam_record()` UPDATE step |

**No placeholders found.**

**Type consistency confirmed:** `create_pam_record(conn, company_id, company_code, data)` signature matches across Task 2 (definition), Task 3 (call site), and Task 4 test helper.
