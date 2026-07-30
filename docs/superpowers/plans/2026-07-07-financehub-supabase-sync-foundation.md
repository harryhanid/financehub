# FinanceHub Supabase Sync Foundation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bangun sync satu-arah SQLite → Supabase Postgres dari nol (belum pernah ada di codebase — lihat [`docs/superpowers/specs/2026-07-07-financehub-hybrid-cloud-failover-design.md`](../specs/2026-07-07-financehub-hybrid-cloud-failover-design.md) §1), sehingga data FinanceHub bisa direplikasi ke Postgres untuk reporting dan jadi fondasi Fase 2+ (cloud standby untuk failover).

**Architecture:** Generic `sync_table()` function yang bisa dipakai untuk tabel manapun, dengan 2 mode: `full` (resync semua baris tiap kali, untuk tabel referensi kecil) dan `timestamp` (WHERE kolom timestamp > sync terakhir, untuk tabel besar). Daftar tabel yang disync dikonfigurasi di satu file (`sync_config.py`), dijalankan lewat APScheduler yang sudah ada di `app.py` (job baru di samping `scheduled_backup_job` yang sudah ada), tiap 5 menit. Riwayat sync dicatat di tabel `central.sync_log` di Postgres supaya tahu kapan sync terakhir per tabel.

**Tech Stack:** Flask (sudah ada), `psycopg2-binary` (driver Postgres, baru), `python-dotenv` (load `.env`, baru), `APScheduler` (sudah dipakai untuk backup job), `pytest` (sudah ada, mock `psycopg2` untuk unit test tanpa Postgres asli).

## Global Constraints

- Semua dependency baru HARUS terpasang lewat `pip install` — TIDAK ADA binary/installer eksternal (lihat spec §4.1: laptop server memblokir download dari GitHub Releases).
- Sync HARUS gagal secara graceful kalau `SUPABASE_DB_URL` belum di-set — jangan sampai bikin `run_production.py` crash saat start hanya karena kredensial cloud belum dikonfigurasi (pola yang sama dengan `zeroconf`/`apscheduler` di `run_production.py`/`app.py`).
- Kolom `password_hash` di tabel `users` HARUS ikut disync (spec FR6) — tetap dalam bentuk hash `bcrypt`, jangan pernah didekripsi/diplaintext-kan.
- Semua upsert HARUS idempotent by primary key (`id`) — aman dijalankan berulang tanpa duplikat (spec FR8).
- File baru ditaruh di `app/sync/` (mengikuti struktur yang sudah direncanakan di desain sync 2026-06-24).

---

### Task 1: Config & Dependencies untuk Koneksi Postgres

**Files:**
- Modify: `app/requirements.txt`
- Modify: `app/config.py`
- Create: `.env.example` (di root `C:\Financehub`)
- Create: `app/tests/test_config_supabase.py`

**Interfaces:**
- Produces: `config.SUPABASE_DB_URL` (str atau `None`) — dipakai semua task berikutnya untuk tahu apakah sync boleh jalan.

- [ ] **Step 1: Tambah dependency ke `requirements.txt`**

Tambahkan 2 baris di akhir `app/requirements.txt`:

```
psycopg2-binary>=2.9
python-dotenv>=1.0
```

- [ ] **Step 2: Install dependency**

Run: `pip install --user -r app/requirements.txt`
Expected: `psycopg2-binary` dan `python-dotenv` terpasang tanpa error (murni dari PyPI, tidak ada binary eksternal).

- [ ] **Step 3: Tulis test yang gagal untuk `config.SUPABASE_DB_URL`**

Buat file baru `app/tests/test_config_supabase.py`:

```python
# app/tests/test_config_supabase.py
import os
import importlib


def test_supabase_db_url_none_when_env_not_set(monkeypatch):
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)
    import config
    importlib.reload(config)
    assert config.SUPABASE_DB_URL is None


def test_supabase_db_url_reads_env(monkeypatch):
    monkeypatch.setenv("SUPABASE_DB_URL", "postgresql://user:pass@host:5432/postgres")
    import config
    importlib.reload(config)
    assert config.SUPABASE_DB_URL == "postgresql://user:pass@host:5432/postgres"
```

- [ ] **Step 4: Jalankan test, pastikan gagal**

Run: `pytest app/tests/test_config_supabase.py -v`
Expected: FAIL — `AttributeError: module 'config' has no attribute 'SUPABASE_DB_URL'`

- [ ] **Step 5: Load `.env` dan tambahkan `SUPABASE_DB_URL` ke `config.py`**

Di `app/config.py`, tambahkan import `load_dotenv` di baris paling atas (setelah `import os` dan `import secrets`, sebelum `BASE_DIR = ...`), supaya `.env` di root project otomatis terbaca ke `os.environ` tanpa Harry perlu set environment variable manual tiap buka terminal baru:

```python
import os
import secrets
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
```

(`load_dotenv` aman dipanggil walau file `.env` belum ada — tidak melempar error, cuma tidak melakukan apa-apa.)

Lalu tambahkan di bagian bawah file (setelah `COA_PAM_SEED`):

```python
# --- Supabase sync (opsional — sync di-skip kalau tidak di-set) ---
SUPABASE_DB_URL = os.environ.get("SUPABASE_DB_URL")  # postgresql://...
```

- [ ] **Step 6: Jalankan test, pastikan lulus**

Run: `pytest app/tests/test_config_supabase.py -v`
Expected: PASS (2 passed)

- [ ] **Step 7: Buat `.env.example` di root project**

Buat file baru `C:\Financehub\.env.example`:

```
# Supabase Postgres — connection string langsung (bukan REST API), dari Supabase dashboard > Settings > Database
SUPABASE_DB_URL=postgresql://postgres:[password]@[project-ref].supabase.co:5432/postgres

# JWT secret FinanceHub (sudah ada, taruh di sini juga supaya satu tempat)
FH_JWT_SECRET=
```

- [ ] **Step 8: Commit**

```bash
git add app/requirements.txt app/config.py app/tests/test_config_supabase.py .env.example
git commit -m "feat(sync): add SUPABASE_DB_URL config, skip gracefully when unset"
```

---

### Task 2: Skema Postgres — DDL Idempotent

**Files:**
- Create: `scripts/setup_supabase_schema.py`
- Create: `app/tests/test_setup_supabase_schema.py`

**Interfaces:**
- Consumes: `config.SUPABASE_DB_URL` dari Task 1
- Produces: `setup_supabase_schema.SCHEMA_DDL` (str, daftar statement SQL) — dipakai Task 2 sendiri dan sebagai dokumentasi skema untuk task berikutnya

- [ ] **Step 1: Tulis test yang gagal untuk isi DDL**

Buat `app/tests/test_setup_supabase_schema.py` (di root, bukan `app/tests`, karena script-nya juga di root — sesuaikan path):

```python
# tests/test_setup_supabase_schema.py
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.setup_supabase_schema import SCHEMA_DDL


def test_schema_ddl_creates_financehub_and_central_schemas():
    assert "CREATE SCHEMA IF NOT EXISTS financehub" in SCHEMA_DDL
    assert "CREATE SCHEMA IF NOT EXISTS central" in SCHEMA_DDL


def test_schema_ddl_has_companies_table():
    assert "CREATE TABLE IF NOT EXISTS financehub.companies" in SCHEMA_DDL


def test_schema_ddl_has_users_table_with_password_hash():
    assert "CREATE TABLE IF NOT EXISTS financehub.users" in SCHEMA_DDL
    assert "password_hash" in SCHEMA_DDL


def test_schema_ddl_has_budget_master_table():
    assert "CREATE TABLE IF NOT EXISTS financehub.budget_master" in SCHEMA_DDL


def test_schema_ddl_has_sync_log_table():
    assert "CREATE TABLE IF NOT EXISTS central.sync_log" in SCHEMA_DDL
```

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `pytest tests/test_setup_supabase_schema.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts'`

- [ ] **Step 3: Buat `scripts/setup_supabase_schema.py`**

Buat file baru `C:\Financehub\scripts\setup_supabase_schema.py` (skema kolom dicocokkan dengan `app/database.py` tabel `companies`, `users`, `budget_master`):

```python
# scripts/setup_supabase_schema.py
"""
Jalankan sekali (atau berkali-kali, idempotent) untuk membuat skema di Supabase Postgres.
Usage: python scripts/setup_supabase_schema.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

SCHEMA_DDL = """
CREATE SCHEMA IF NOT EXISTS financehub;
CREATE SCHEMA IF NOT EXISTS central;

CREATE TABLE IF NOT EXISTS financehub.companies (
    id   INTEGER PRIMARY KEY,
    code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS financehub.users (
    id             INTEGER PRIMARY KEY,
    username       TEXT UNIQUE NOT NULL,
    password_hash  TEXT NOT NULL,
    role           TEXT NOT NULL DEFAULT 'requester',
    is_active      INTEGER DEFAULT 1,
    must_change_pw INTEGER DEFAULT 1,
    created_at     TEXT,
    last_login     TEXT
);

CREATE TABLE IF NOT EXISTS financehub.budget_master (
    id              TEXT PRIMARY KEY,
    mm              INTEGER NOT NULL,
    yy              INTEGER NOT NULL,
    company         TEXT NOT NULL,
    dept            TEXT,
    gl_account      TEXT,
    gl_description  TEXT,
    budget_category TEXT,
    activity        TEXT,
    description     TEXT,
    amount          REAL DEFAULT 0,
    deadline        TEXT,
    created_at      TEXT,
    updated_at      TEXT
);

CREATE TABLE IF NOT EXISTS central.sync_log (
    id           SERIAL PRIMARY KEY,
    table_name   TEXT NOT NULL,
    last_sync_at TIMESTAMPTZ,
    rows_synced  INTEGER,
    status       TEXT,
    error_msg    TEXT,
    synced_at    TIMESTAMPTZ DEFAULT NOW()
);
"""


def apply_schema(pg_conn):
    with pg_conn.cursor() as cur:
        cur.execute(SCHEMA_DDL)
    pg_conn.commit()


if __name__ == "__main__":
    import psycopg2
    import config

    if not config.SUPABASE_DB_URL:
        print("SUPABASE_DB_URL belum di-set — set dulu di .env atau environment variable.")
        raise SystemExit(1)

    conn = psycopg2.connect(config.SUPABASE_DB_URL)
    apply_schema(conn)
    conn.close()
    print("Skema Supabase berhasil dibuat/diverifikasi.")
```

- [ ] **Step 4: Jalankan test, pastikan lulus**

Run: `pytest tests/test_setup_supabase_schema.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add scripts/setup_supabase_schema.py tests/test_setup_supabase_schema.py
git commit -m "feat(sync): add idempotent Supabase schema DDL script"
```

---

### Task 3: Generic Sync Function — Baca dari SQLite

**Files:**
- Create: `app/sync/__init__.py`
- Create: `app/sync/supabase_sync.py`
- Create: `app/tests/test_supabase_sync_fetch.py`

**Interfaces:**
- Consumes: koneksi `sqlite3.Connection` (dari `database.get_conn()`, `row_factory=sqlite3.Row`)
- Produces: `supabase_sync.fetch_rows_to_sync(sqlite_conn, table, mode, ts_col, since) -> list[dict]` — dipakai Task 4 (`sync_table`) dan Task 5 (`run_sync_all`)

- [ ] **Step 1: Buat `app/sync/__init__.py` kosong**

```python
# app/sync/__init__.py
```

- [ ] **Step 2: Tulis test yang gagal untuk `fetch_rows_to_sync`**

Buat `app/tests/test_supabase_sync_fetch.py`:

```python
# app/tests/test_supabase_sync_fetch.py
import sqlite3
import pytest
from sync.supabase_sync import fetch_rows_to_sync


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("CREATE TABLE companies (id INTEGER PRIMARY KEY, code TEXT, name TEXT)")
    c.execute("INSERT INTO companies VALUES (1, 'SMT', 'Sinar Mas Tjipta')")
    c.execute("INSERT INTO companies VALUES (2, 'ETF', 'Eka Tjipta Foundation')")
    c.execute("CREATE TABLE budget_master (id TEXT PRIMARY KEY, amount REAL, updated_at TEXT)")
    c.execute("INSERT INTO budget_master VALUES ('B1', 100.0, '2026-07-01T00:00:00')")
    c.execute("INSERT INTO budget_master VALUES ('B2', 200.0, '2026-07-05T00:00:00')")
    c.commit()
    return c


def test_fetch_full_mode_returns_all_rows(conn):
    rows = fetch_rows_to_sync(conn, "companies", mode="full", ts_col=None, since=None)
    assert len(rows) == 2
    assert rows[0]["code"] == "SMT"


def test_fetch_timestamp_mode_filters_by_since(conn):
    rows = fetch_rows_to_sync(conn, "budget_master", mode="timestamp", ts_col="updated_at", since="2026-07-03T00:00:00")
    assert len(rows) == 1
    assert rows[0]["id"] == "B2"


def test_fetch_timestamp_mode_returns_all_when_since_none(conn):
    rows = fetch_rows_to_sync(conn, "budget_master", mode="timestamp", ts_col="updated_at", since=None)
    assert len(rows) == 2


def test_fetch_returns_list_of_plain_dicts(conn):
    rows = fetch_rows_to_sync(conn, "companies", mode="full", ts_col=None, since=None)
    assert isinstance(rows[0], dict)
    assert rows[0] == {"id": 1, "code": "SMT", "name": "Sinar Mas Tjipta"}
```

- [ ] **Step 3: Jalankan test, pastikan gagal**

Run: `pytest app/tests/test_supabase_sync_fetch.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'sync'` (atau `ImportError: cannot import name 'fetch_rows_to_sync'`)

- [ ] **Step 4: Implementasi `fetch_rows_to_sync` di `app/sync/supabase_sync.py`**

```python
# app/sync/supabase_sync.py


def fetch_rows_to_sync(sqlite_conn, table, mode, ts_col, since):
    """Ambil baris dari SQLite yang perlu disync.

    mode="full": ambil semua baris (tabel referensi kecil, mis. companies).
    mode="timestamp": ambil baris dengan ts_col > since (incremental atau insert-only,
        tergantung ts_col yang dipilih caller — "updated_at" atau "created_at").
    """
    if mode == "full":
        cur = sqlite_conn.execute(f"SELECT * FROM {table}")
    elif mode == "timestamp":
        if since:
            cur = sqlite_conn.execute(f"SELECT * FROM {table} WHERE {ts_col} > ?", (since,))
        else:
            cur = sqlite_conn.execute(f"SELECT * FROM {table}")
    else:
        raise ValueError(f"Unknown sync mode: {mode}")
    return [dict(row) for row in cur.fetchall()]
```

- [ ] **Step 5: Jalankan test, pastikan lulus**

Run: `pytest app/tests/test_supabase_sync_fetch.py -v`
Expected: PASS (4 passed)

- [ ] **Step 6: Commit**

```bash
git add app/sync/__init__.py app/sync/supabase_sync.py app/tests/test_supabase_sync_fetch.py
git commit -m "feat(sync): add fetch_rows_to_sync — read changed rows from SQLite"
```

---

### Task 4: Generic Sync Function — Upsert ke Postgres

**Files:**
- Modify: `app/sync/supabase_sync.py`
- Create: `app/tests/test_supabase_sync_upsert.py`

**Interfaces:**
- Consumes: `fetch_rows_to_sync` dari Task 3
- Produces: `supabase_sync.upsert_rows(pg_conn, table, rows, key_col) -> int` dan `supabase_sync.sync_table(sqlite_conn, pg_conn, table, key_col, mode, ts_col, since) -> int` — dipakai Task 5 (`run_sync_all`)

- [ ] **Step 1: Tulis test yang gagal untuk `upsert_rows`**

Buat `app/tests/test_supabase_sync_upsert.py`:

```python
# app/tests/test_supabase_sync_upsert.py
from unittest.mock import MagicMock, patch
from sync.supabase_sync import upsert_rows, sync_table


def test_upsert_rows_returns_zero_for_empty_list():
    pg_conn = MagicMock()
    assert upsert_rows(pg_conn, "companies", [], "id") == 0
    pg_conn.cursor.assert_not_called()


@patch("sync.supabase_sync.execute_values")
def test_upsert_rows_builds_insert_on_conflict_sql(mock_execute_values):
    pg_conn = MagicMock()
    rows = [
        {"id": 1, "code": "SMT", "name": "Sinar Mas Tjipta"},
        {"id": 2, "code": "ETF", "name": "Eka Tjipta Foundation"},
    ]

    n = upsert_rows(pg_conn, "companies", rows, "id")

    assert n == 2
    mock_execute_values.assert_called_once()
    call_args = mock_execute_values.call_args
    sql_used = call_args[0][1]
    assert "INSERT INTO financehub.companies" in sql_used
    assert "ON CONFLICT (id) DO UPDATE SET code=EXCLUDED.code, name=EXCLUDED.name" in sql_used
    values_used = call_args[0][2]
    assert values_used == [[1, "SMT", "Sinar Mas Tjipta"], [2, "ETF", "Eka Tjipta Foundation"]]
    pg_conn.commit.assert_called_once()


@patch("sync.supabase_sync.upsert_rows")
def test_sync_table_calls_fetch_then_upsert(mock_upsert):
    import sqlite3
    sqlite_conn = sqlite3.connect(":memory:")
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_conn.execute("CREATE TABLE companies (id INTEGER PRIMARY KEY, code TEXT)")
    sqlite_conn.execute("INSERT INTO companies VALUES (1, 'SMT')")
    sqlite_conn.commit()
    mock_upsert.return_value = 1
    pg_conn = MagicMock()

    n = sync_table(sqlite_conn, pg_conn, "companies", key_col="id", mode="full", ts_col=None, since=None)

    assert n == 1
    mock_upsert.assert_called_once()
    args = mock_upsert.call_args[0]
    assert args[0] is pg_conn
    assert args[1] == "companies"
    assert args[2] == [{"id": 1, "code": "SMT"}]
    assert args[3] == "id"
```

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `pytest app/tests/test_supabase_sync_upsert.py -v`
Expected: FAIL — `ImportError: cannot import name 'upsert_rows'`

- [ ] **Step 3: Implementasi `upsert_rows` dan `sync_table` di `app/sync/supabase_sync.py`**

Tambahkan di akhir `app/sync/supabase_sync.py`:

```python
from psycopg2.extras import execute_values


def upsert_rows(pg_conn, table, rows, key_col):
    """Upsert rows ke financehub.<table> di Postgres, idempotent by key_col."""
    if not rows:
        return 0
    columns = list(rows[0].keys())
    values = [[row[c] for c in columns] for row in rows]
    update_cols = [c for c in columns if c != key_col]
    set_clause = ", ".join(f"{c}=EXCLUDED.{c}" for c in update_cols)
    sql = (
        f"INSERT INTO financehub.{table} ({', '.join(columns)}) VALUES %s "
        f"ON CONFLICT ({key_col}) DO UPDATE SET {set_clause}"
    )
    with pg_conn.cursor() as cur:
        execute_values(cur, sql, values)
    pg_conn.commit()
    return len(rows)


def sync_table(sqlite_conn, pg_conn, table, key_col="id", mode="timestamp", ts_col="updated_at", since=None):
    """Sync satu tabel dari SQLite ke Postgres. Return jumlah baris yang disync."""
    rows = fetch_rows_to_sync(sqlite_conn, table, mode, ts_col, since)
    return upsert_rows(pg_conn, table, rows, key_col)
```

- [ ] **Step 4: Jalankan test, pastikan lulus**

Run: `pytest app/tests/test_supabase_sync_upsert.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add app/sync/supabase_sync.py app/tests/test_supabase_sync_upsert.py
git commit -m "feat(sync): add upsert_rows and sync_table — write to Postgres"
```

---

### Task 5: Sync Config + `run_sync_all` + Riwayat Sync

**Files:**
- Create: `app/sync/sync_config.py`
- Modify: `app/sync/supabase_sync.py`
- Create: `app/tests/test_supabase_sync_run_all.py`

**Interfaces:**
- Consumes: `sync_table` dari Task 4
- Produces: `supabase_sync.run_sync_all(sqlite_conn, pg_conn) -> dict` — dipakai Task 6 (scheduler job)

- [ ] **Step 1: Buat `app/sync/sync_config.py`**

```python
# app/sync/sync_config.py
"""Daftar tabel yang disync SQLite -> Supabase.

mode="full": resync semua baris tiap kali (tabel referensi kecil).
mode="timestamp": incremental berdasarkan ts_col ("updated_at" untuk tabel yang
    di-update, "created_at" untuk tabel insert-only seperti payment_beasiswa).

Untuk menambah tabel baru ke sync scope, tambahkan entry di list ini —
tidak perlu mengubah kode sync itu sendiri.
"""

SYNC_TABLES = [
    {"table": "companies", "key_col": "id", "mode": "full"},
    {"table": "users", "key_col": "id", "mode": "timestamp", "ts_col": "created_at"},
    {"table": "budget_master", "key_col": "id", "mode": "timestamp", "ts_col": "updated_at"},
]
```

- [ ] **Step 2: Tulis test yang gagal untuk `run_sync_all`**

Buat `app/tests/test_supabase_sync_run_all.py`:

```python
# app/tests/test_supabase_sync_run_all.py
import sqlite3
from unittest.mock import MagicMock, patch
from sync.supabase_sync import run_sync_all


def make_sqlite_conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("CREATE TABLE companies (id INTEGER PRIMARY KEY, code TEXT)")
    c.execute("INSERT INTO companies VALUES (1, 'SMT')")
    c.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT, password_hash TEXT, created_at TEXT)")
    c.execute("INSERT INTO users VALUES (1, 'admin', 'hash123', '2026-07-01T00:00:00')")
    c.execute("CREATE TABLE budget_master (id TEXT PRIMARY KEY, amount REAL, updated_at TEXT)")
    c.execute("INSERT INTO budget_master VALUES ('B1', 100.0, '2026-07-01T00:00:00')")
    c.commit()
    return c


@patch("sync.supabase_sync.record_sync")
@patch("sync.supabase_sync.get_last_sync", return_value=None)
@patch("sync.supabase_sync.upsert_rows")
def test_run_sync_all_syncs_every_configured_table(mock_upsert, mock_get_last_sync, mock_record_sync):
    mock_upsert.side_effect = [1, 1, 1]
    sqlite_conn = make_sqlite_conn()
    pg_conn = MagicMock()

    results = run_sync_all(sqlite_conn, pg_conn)

    assert results == {"companies": 1, "users": 1, "budget_master": 1}
    assert mock_upsert.call_count == 3
    assert mock_record_sync.call_count == 3


@patch("sync.supabase_sync.record_sync")
@patch("sync.supabase_sync.get_last_sync", return_value=None)
@patch("sync.supabase_sync.upsert_rows")
def test_run_sync_all_syncs_password_hash_column(mock_upsert, mock_get_last_sync, mock_record_sync):
    sqlite_conn = make_sqlite_conn()
    pg_conn = MagicMock()

    run_sync_all(sqlite_conn, pg_conn)

    users_call = [c for c in mock_upsert.call_args_list if c[0][1] == "users"][0]
    synced_rows = users_call[0][2]
    assert synced_rows[0]["password_hash"] == "hash123"


@patch("sync.supabase_sync.record_sync")
@patch("sync.supabase_sync.get_last_sync", return_value=None)
@patch("sync.supabase_sync.upsert_rows", side_effect=Exception("connection lost"))
def test_run_sync_all_continues_after_one_table_fails(mock_upsert, mock_get_last_sync, mock_record_sync):
    sqlite_conn = make_sqlite_conn()
    pg_conn = MagicMock()

    results = run_sync_all(sqlite_conn, pg_conn)

    assert all(str(v).startswith("error:") for v in results.values())
    assert mock_record_sync.call_count == 3
    error_calls = [c for c in mock_record_sync.call_args_list if c[0][2] == "error"]
    assert len(error_calls) == 3
```

- [ ] **Step 3: Jalankan test, pastikan gagal**

Run: `pytest app/tests/test_supabase_sync_run_all.py -v`
Expected: FAIL — `ImportError: cannot import name 'run_sync_all'`

- [ ] **Step 4: Implementasi `get_last_sync`, `record_sync`, `run_sync_all` di `app/sync/supabase_sync.py`**

Tambahkan import di bagian atas `app/sync/supabase_sync.py`:

```python
from sync.sync_config import SYNC_TABLES
```

Tambahkan di akhir `app/sync/supabase_sync.py`:

```python
def get_last_sync(pg_conn, table):
    with pg_conn.cursor() as cur:
        cur.execute(
            "SELECT last_sync_at FROM central.sync_log WHERE table_name=%s "
            "ORDER BY synced_at DESC LIMIT 1",
            (table,),
        )
        row = cur.fetchone()
    return row[0] if row else None


def record_sync(pg_conn, table, rows_synced, status, error_msg=None):
    with pg_conn.cursor() as cur:
        cur.execute(
            "INSERT INTO central.sync_log (table_name, last_sync_at, rows_synced, status, error_msg) "
            "VALUES (%s, NOW(), %s, %s, %s)",
            (table, rows_synced, status, error_msg),
        )
    pg_conn.commit()


def run_sync_all(sqlite_conn, pg_conn):
    """Sync semua tabel di SYNC_TABLES. Return dict {table: rows_synced atau 'error: <msg>'}."""
    results = {}
    for cfg in SYNC_TABLES:
        table = cfg["table"]
        try:
            since = None if cfg["mode"] == "full" else get_last_sync(pg_conn, table)
            n = sync_table(
                sqlite_conn, pg_conn, table,
                key_col=cfg["key_col"], mode=cfg["mode"],
                ts_col=cfg.get("ts_col", "updated_at"), since=since,
            )
            record_sync(pg_conn, table, n, "success")
            results[table] = n
        except Exception as e:
            record_sync(pg_conn, table, 0, "error", str(e))
            results[table] = f"error: {e}"
    return results
```

- [ ] **Step 5: Jalankan test, pastikan lulus**

Run: `pytest app/tests/test_supabase_sync_run_all.py -v`
Expected: PASS (3 passed)

- [ ] **Step 6: Commit**

```bash
git add app/sync/sync_config.py app/sync/supabase_sync.py app/tests/test_supabase_sync_run_all.py
git commit -m "feat(sync): add run_sync_all with per-table error isolation and sync_log tracking"
```

---

### Task 6: Wire ke APScheduler (jalan tiap 5 menit)

**Files:**
- Modify: `app/app.py`
- Create: `app/tests/test_sync_scheduler_wiring.py`

**Interfaces:**
- Consumes: `run_sync_all` dari Task 5, `config.SUPABASE_DB_URL` dari Task 1

- [ ] **Step 1: Tulis test yang gagal untuk graceful skip**

Buat `app/tests/test_sync_scheduler_wiring.py`:

```python
# app/tests/test_sync_scheduler_wiring.py
from unittest.mock import patch


def test_app_boots_without_supabase_configured(monkeypatch):
    """create_app() tidak boleh crash walau SUPABASE_DB_URL belum di-set."""
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)
    import config
    import importlib
    importlib.reload(config)

    from app import create_app
    app = create_app(testing=False)
    assert app is not None


@patch("sync.supabase_sync.run_sync_all")
@patch("psycopg2.connect")
def test_scheduled_sync_job_skipped_when_no_supabase_url(mock_connect, mock_run_sync_all, monkeypatch):
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)
    import config
    import importlib
    importlib.reload(config)

    from app import scheduled_sync_job
    scheduled_sync_job()

    mock_connect.assert_not_called()
    mock_run_sync_all.assert_not_called()
```

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `pytest app/tests/test_sync_scheduler_wiring.py -v`
Expected: FAIL — `ImportError: cannot import name 'scheduled_sync_job' from 'app'`

- [ ] **Step 3: Tambahkan `scheduled_sync_job` dan job scheduler di `app/app.py`**

Di `app/app.py`, tambahkan fungsi baru di level module (sebelum `create_app`, setelah import):

```python
def scheduled_sync_job():
    """Sync SQLite -> Supabase. Skip diam-diam kalau SUPABASE_DB_URL belum di-set."""
    import config
    if not config.SUPABASE_DB_URL:
        return
    import psycopg2
    from database import get_conn
    from sync.supabase_sync import run_sync_all

    sqlite_conn = get_conn()
    pg_conn = psycopg2.connect(config.SUPABASE_DB_URL)
    try:
        run_sync_all(sqlite_conn, pg_conn)
    finally:
        sqlite_conn.close()
        pg_conn.close()
```

Lalu di dalam `create_app`, di blok `if not testing:` (setelah `scheduler.add_job(func=scheduled_backup_job, ...)` yang sudah ada, sebelum `scheduler.start()`), tambahkan job baru:

```python
                scheduler.add_job(func=scheduled_sync_job, trigger="interval", minutes=5)
```

Baris di sekitarnya (untuk konteks, JANGAN duplikasi — cuma tambahkan 1 baris baru setelah baris `scheduler.add_job(func=scheduled_backup_job, ...)` yang sudah ada):

```python
                scheduler = BackgroundScheduler()

                def scheduled_backup_job():
                    with app.app_context():
                        run_excel_backups()

                # Run at 17:00 on Mon-Fri
                scheduler.add_job(func=scheduled_backup_job, trigger="cron", day_of_week="mon-fri", hour=17, minute=0)
                scheduler.add_job(func=scheduled_sync_job, trigger="interval", minutes=5)
                scheduler.start()
```

- [ ] **Step 4: Jalankan test, pastikan lulus**

Run: `pytest app/tests/test_sync_scheduler_wiring.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Jalankan seluruh test suite untuk regresi**

Run: `pytest app/tests/ -v`
Expected: semua test PASS (termasuk yang sudah ada sebelumnya — tidak ada regresi)

- [ ] **Step 6: Commit**

```bash
git add app/app.py app/tests/test_sync_scheduler_wiring.py
git commit -m "feat(sync): wire scheduled_sync_job into APScheduler, 5-minute interval"
```

---

### Task 7: Verifikasi Manual (Harry) — Setup Supabase Project

Task ini BUKAN kode — checklist manual untuk Harry karena implementer tidak punya akses ke akun Supabase asli.

- [ ] **Step 1:** Buat project Supabase baru (atau pakai yang sudah ada) di [supabase.com](https://supabase.com), tier Free
- [ ] **Step 2:** Salin connection string dari Supabase dashboard → Settings → Database → Connection string (mode "URI", bukan "Session pooler") — jangan lupa ganti `[YOUR-PASSWORD]` dengan password project
- [ ] **Step 3:** Buat file `.env` di `C:\Financehub` (bukan `.env.example`) berisi:
  ```
  SUPABASE_DB_URL=postgresql://postgres:<password-asli>@<project-ref>.supabase.co:5432/postgres
  ```
- [ ] **Step 4:** Jalankan `python scripts/setup_supabase_schema.py` — pastikan output "Skema Supabase berhasil dibuat/diverifikasi."
- [ ] **Step 5:** Jalankan `run_production.py` seperti biasa, tunggu 5 menit, cek Supabase Table Editor → tabel `financehub.companies`, `financehub.users`, `financehub.budget_master` — pastikan data muncul
- [ ] **Step 6:** Cek tabel `central.sync_log` — pastikan ada baris dengan `status='success'` untuk tiap tabel
- [ ] **Step 7:** Konfirmasi ke implementer/lanjutkan ke Fase 2 (DB abstraction layer + cloud app) kalau semua di atas berhasil

---

## Catatan untuk Fase Berikutnya

Plan ini HANYA mencakup **Fase 1** dari rollout plan di spec (§14). Fase 2–6 (DB abstraction layer, WebSocket relay, reverse sync, admin override, email notification, end-to-end drill) adalah pekerjaan besar yang terpisah — terutama **DB abstraction layer** yang menyentuh ~5.000 baris raw SQL SQLite-spesifik di 6 module service (lihat spec §10). Masing-masing sebaiknya jadi plan implementasi tersendiri, bukan disatukan ke plan ini, supaya setiap plan tetap punya deliverable yang bisa dites independen.

`SYNC_TABLES` di `app/sync/sync_config.py` baru mencakup 3 tabel (`companies`, `users`, `budget_master`) sebagai bukti konsep generic sync function-nya bekerja. Menambah tabel lain (mis. `pam_records`, `payment_beasiswa`, modul `sahabat_etf`/`bank`/`sponsorship` yang sudah ada di codebase tapi belum ada di spec asli) tinggal menambah entry ke list itu — tidak perlu mengubah `supabase_sync.py`.
