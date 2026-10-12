# General Ledger Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Menu General Ledger punya 3 sub menu (GL SMT, GL ETF, GL SETF) yang menyinkronkan data dari upload `GL - MASTER.xlsb` dan menampilkannya dengan filter dan paginasi.

**Architecture:** Modul `modules/general_ledger/` dipecah jadi `parser.py` (baca sheet .xlsb), `service.py` (skema SQLite, simpan, query viewer), `sync.py` (hash isi + ringkasan perubahan), dan `routes.py` (halaman + endpoint sync). Pola mengikuti `modules/management_report/`, tetapi penyimpanan memakai ganti penuh per entitas ditambah log sync, bukan snapshot.

**Tech Stack:** Flask, SQLite (`database.get_conn`), `pyxlsb` (sudah ada di `requirements.txt`), pytest, template Jinja `base.html`.

**Spec:** `docs/superpowers/specs/2026-10-12-general-ledger-sync-design.md`

## Global Constraints

- Semua path relatif terhadap `C:\Financehub\app` kecuali disebut lain. Perintah dijalankan dari folder itu.
- Working tree sudah kotor oleh perubahan lain. Setiap commit memakai `git add <file spesifik>`, jangan `git add -A` atau `git commit -a`.
- Pesan commit diakhiri baris `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.
- Entitas dan sheet: `smt` = `GL SMT` = tabel `GLSMT`, `etf` = `GL ETF` = `GLETF`, `setf` = `GL SETF` = `GLSETF`. Tabel `GLSME` tidak dipakai dan tidak disentuh.
- Sync hanya untuk admin (`json_admin_required`). Halaman butuh login (`jwt_html_required`).
- File upload harus berakhiran `.xlsb`. Stub Excel COM (`pythoncom`, `win32com`) dihapus.
- Kolom hitungan di kolom 44 sampai 49 sheet Excel tidak disimpan.
- Baris tanpa ID#, tanpa Account Statutory, dan tanpa Account Management dibuang dan dihitung sebagai "dilewati".
- Tes memakai `tests/conftest.py` (DB uji terisolasi). Login uji: `POST /auth/login` admin lalu `POST /select-company`, seperti `login()` di `tests/test_mr_routes.py`.

## Review Focus

- Tabel `GLSMT`/`GLETF`/`GLSETF` sudah ada dengan kolom lain di DB produksi (dibuat `to_sql` oleh stub lama): `ensure_schema` harus membuangnya dan membuat ulang, bukan gagal saat INSERT. Dites di Task 2.
- Nilai sel error Excel (`0x2A`, dst.) di kolom angka dan teks: dianggap kosong/0, sync tidak boleh gagal. Dites di Task 1.
- Teks pencarian berisi `%` atau `_`: harus dicari sebagai teks biasa, bukan wildcard. Dites di Task 3.
- Nomor halaman di luar jangkauan atau bukan angka (`?page=999`, `?page=abc`): kembali ke halaman valid terdekat, tidak error 500. Dites di Task 3 dan 4.
- Upload file bukan .xlsb valid, atau sheet/header tidak ada: pesan galat jelas, status 400, data lama tetap utuh. Dites di Task 4.

---

### Task 1: Parser sheet GL

**Files:**
- Create: `modules/general_ledger/parser.py`
- Test: `tests/test_gl_parser.py`

**Interfaces:**
- Produces: `COLUMNS` (tuple nama kolom hasil parse, urut), `ParseError`, `ParseResult(rows, dropped)`, `normalise_rows(header, raw_rows) -> ParseResult`, `read_gl_sheet(fileobj, sheet_name) -> ParseResult`. Tiap baris adalah `dict` dengan kunci `COLUMNS`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_gl_parser.py
import pytest

from modules.general_ledger import parser as p

HEADER = ["", "x", "x1", "Account\nStatutory", "Description Account \nStatutory",
          "Account\nManagement", "Description Account \nManagement", "ID#", "Date", "Memo",
          "Debit", "Credit", "Job Name", "Job Description", "PPH/Non PPH", "Budget Activity",
          "Customer/ Vendor", "Allocation Memo", "EVENT", "Qty Awal", "Qty Akhir", "UOM",
          "Nama Item", "Harga Satuan", "Keterangan 1", "Keterangan 2"]


def raw(**kw):
    """One raw sheet row aligned to HEADER; unspecified cells are None."""
    pos = {"entry_no": 1, "source_type": 2, "acc_statutory": 3, "acc_statutory_desc": 4,
           "acc_management": 5, "acc_management_desc": 6, "id_no": 7, "tgl": 8, "memo": 9,
           "debit": 10, "credit": 11, "job_name": 12, "job_desc": 13, "budget_activity": 15,
           "customer_vendor": 16, "allocation_memo": 17, "event": 18, "qty_awal": 19,
           "qty_akhir": 20, "uom": 21, "nama_item": 22, "harga_satuan": 23, "ket1": 24,
           "ket2": 25}
    r = [None] * len(HEADER)
    for k, v in kw.items():
        r[pos[k]] = v
    return r


def test_maps_columns_and_converts_values():
    res = p.normalise_rows(HEADER, [raw(
        entry_no=1.0, source_type="GJ - Acrue", acc_statutory="2-1110",
        acc_statutory_desc="Other Payables", acc_management="2-1110", id_no="GJ-00168",
        tgl=46023.0, memo="Reversal", debit=918367069.0, credit=0.0, job_name="POCFAD",
        customer_vendor="Bank Sinarmas", ket1="k1")])
    assert res.dropped == 0 and len(res.rows) == 1
    r = res.rows[0]
    assert set(r) == set(p.COLUMNS)
    assert r["entry_no"] == 1 and r["source_type"] == "GJ - Acrue"
    assert r["acc_statutory"] == "2-1110" and r["id_no"] == "GJ-00168"
    assert r["tgl"] == "2026-01-01"          # Excel serial 46023
    assert r["debit"] == 918367069.0 and r["credit"] == 0.0
    assert r["ket1"] == "k1" and r["ket2"] == ""


def test_missing_cells_become_zero_and_empty_text():
    r = p.normalise_rows(HEADER, [raw(acc_statutory="1-1", id_no="X-1", tgl=46023.0)]).rows[0]
    assert r["debit"] == 0.0 and r["credit"] == 0.0 and r["memo"] == ""


def test_formula_only_rows_are_dropped_and_counted():
    junk = raw(entry_no=3.0, acc_statutory="", acc_management=0.0, memo="Sumbangan - 00 Jan 1900")
    good = raw(acc_statutory="1-1", id_no="X-1", tgl=46023.0, debit=5.0)
    blank = [None] * len(HEADER)
    res = p.normalise_rows(HEADER, [junk, good, blank])
    assert len(res.rows) == 1 and res.dropped == 1        # fully blank rows are not counted


def test_excel_error_cells_are_ignored():
    r = p.normalise_rows(HEADER, [raw(acc_statutory="1-1", id_no="X-1", tgl=46023.0,
                                      debit="0x2A", memo="0x07", ket1="ok")]).rows[0]
    assert r["debit"] == 0.0 and r["memo"] == "" and r["ket1"] == "ok"


def test_text_date_is_kept_and_zero_date_is_none():
    a = p.normalise_rows(HEADER, [raw(acc_statutory="1-1", tgl="2026-02-03")]).rows[0]
    b = p.normalise_rows(HEADER, [raw(acc_statutory="1-1", tgl=0.0)]).rows[0]
    assert a["tgl"] == "2026-02-03" and b["tgl"] is None


def test_missing_required_header_raises():
    bad = [h for h in HEADER if h != "Debit"]
    with pytest.raises(p.ParseError, match="Debit"):
        p.normalise_rows(bad, [])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_gl_parser.py -v`
Expected: FAIL (`ModuleNotFoundError` / `cannot import name 'parser'`)

- [ ] **Step 3: Write minimal implementation**

```python
# modules/general_ledger/parser.py
"""General Ledger: read the GL SMT / GL ETF / GL SETF sheets of GL - MASTER.xlsb."""
import datetime as _dt
import re
from collections import namedtuple

from pyxlsb import open_workbook

COLUMNS = ("entry_no", "source_type", "acc_statutory", "acc_statutory_desc", "acc_management",
           "acc_management_desc", "id_no", "tgl", "memo", "debit", "credit", "job_name",
           "job_desc", "budget_activity", "customer_vendor", "allocation_memo", "event",
           "qty_awal", "qty_akhir", "uom", "nama_item", "harga_satuan", "ket1", "ket2")

# Normalised sheet header (lower case, whitespace collapsed) -> column
_HEADER_MAP = {
    "x": "entry_no", "x1": "source_type",
    "account statutory": "acc_statutory",
    "description account statutory": "acc_statutory_desc",
    "account management": "acc_management",
    "description account management": "acc_management_desc",
    "id#": "id_no", "date": "tgl", "memo": "memo", "debit": "debit", "credit": "credit",
    "job name": "job_name", "job description": "job_desc",
    "budget activity": "budget_activity", "customer/ vendor": "customer_vendor",
    "allocation memo": "allocation_memo", "event": "event",
    "qty awal": "qty_awal", "qty akhir": "qty_akhir", "uom": "uom",
    "nama item": "nama_item", "harga satuan": "harga_satuan",
    "keterangan 1": "ket1", "keterangan 2": "ket2",
}
_REQUIRED = ("account statutory", "account management", "id#", "date", "debit", "credit")
_REAL = {"debit", "credit", "qty_awal", "qty_akhir", "harga_satuan"}
_ERR = re.compile(r"^0x[0-9A-Fa-f]{1,2}$")       # how pyxlsb shows an Excel error cell

ParseResult = namedtuple("ParseResult", "rows dropped")


class ParseError(ValueError):
    """Raised with a user-facing message when the workbook cannot be used."""


def _norm(h) -> str:
    return " ".join(str(h).split()).lower() if h is not None else ""


def _text(v) -> str:
    if v is None or (isinstance(v, (int, float)) and v == 0):
        return ""
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    s = str(v).strip()
    return "" if _ERR.match(s) else s


def _num(v) -> float:
    try:
        return float(v) if v not in (None, "") else 0.0
    except (TypeError, ValueError):
        return 0.0


def _int(v):
    try:
        return int(float(v))
    except (TypeError, ValueError, OverflowError):
        return None


def _date(v):
    if isinstance(v, (int, float)):
        if v <= 0:
            return None
        try:
            return (_dt.date(1899, 12, 30) + _dt.timedelta(days=int(v))).isoformat()
        except OverflowError:
            return None
    s = _text(v)
    return s or None


def normalise_rows(header, raw_rows) -> ParseResult:
    names = [_norm(h) for h in header]
    missing = [h for h in _REQUIRED if h not in names]
    if missing:
        raise ParseError("Kolom tidak ditemukan: " + ", ".join(m.title() for m in missing))
    pos = {}
    for i, n in enumerate(names):
        col = _HEADER_MAP.get(n)
        if col and col not in pos:               # first occurrence wins; later helper columns repeat names
            pos[col] = i

    rows, dropped = [], 0
    for raw in raw_rows:
        if all(v in (None, "") for v in raw):
            continue

        def g(col):
            i = pos.get(col)
            return raw[i] if i is not None and i < len(raw) else None

        row = {}
        for col in COLUMNS:
            v = g(col)
            if col in _REAL:
                row[col] = _num(v)
            elif col == "entry_no":
                row[col] = _int(v)
            elif col == "tgl":
                row[col] = _date(v)
            else:
                row[col] = _text(v)
        if not (row["id_no"] or row["acc_statutory"] or row["acc_management"]):
            dropped += 1
            continue
        rows.append(row)
    return ParseResult(rows, dropped)


def read_gl_sheet(fileobj, sheet_name: str) -> ParseResult:
    try:
        wb = open_workbook(fileobj)
    except Exception as e:
        raise ParseError(f"File tidak bisa dibaca sebagai .xlsb: {e}") from e
    try:
        with wb:
            if sheet_name not in wb.sheets:
                raise ParseError(f"Sheet '{sheet_name}' tidak ditemukan di file.")
            with wb.get_sheet(sheet_name) as sh:
                it = ([c.v for c in r] for r in sh.rows())
                header = None
                for i, vals in enumerate(it):          # row 0 is a control row, header is row 1
                    if i > 4:
                        break
                    names = [_norm(h) for h in vals]
                    if "debit" in names and "credit" in names:
                        header = vals
                        break
                if header is None:
                    raise ParseError(f"Header (Debit/Credit) tidak ditemukan di sheet '{sheet_name}'.")
                return normalise_rows(header, it)
    except ParseError:
        raise
    except Exception as e:
        raise ParseError(f"File tidak bisa dibaca: {e}") from e
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_gl_parser.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add modules/general_ledger/parser.py tests/test_gl_parser.py
git commit -m "feat(gl): parse GL sheets from GL - MASTER.xlsb

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Penyimpanan, hash, dan sync

**Files:**
- Create: `modules/general_ledger/service.py` (skema, simpan, baca, log)
- Create: `modules/general_ledger/sync.py`
- Test: `tests/test_gl_sync.py`

**Interfaces:**
- Consumes: `parser.COLUMNS`.
- Produces dari `service`:
  - `ENTITIES: dict` (kunci `smt|etf|setf`, nilai `{"sheet", "table", "label"}`)
  - `ensure_schema(conn) -> None`
  - `replace_all(entity, rows, log) -> None`, dengan `log` berisi kunci `synced_by, filename, content_hash, rows_before, rows_after, total_debit, total_credit, dropped, summary`
  - `load_rows(entity) -> list[dict]`
  - `last_sync(entity) -> dict | None`
  - `list_syncs(entity, limit=10) -> list[dict]`
- Produces dari `sync`:
  - `compute_hash(rows) -> str`
  - `summarize_changes(old_rows, new_rows) -> dict` dengan kunci `added, removed, changed`
  - `sync_rows(entity, filename, user, rows, dropped=0) -> dict` dengan kunci `changed, rows, total_debit, total_credit, balanced, summary`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_gl_sync.py
import pytest

from database import get_conn
from modules.general_ledger import service as svc
from modules.general_ledger import sync as glsync


def mkrow(**kw):
    base = dict(entry_no=1, source_type="GJ", acc_statutory="6-1810", acc_statutory_desc="Office",
                acc_management="6-1810", acc_management_desc="Office", id_no="GJ-1",
                tgl="2026-01-02", memo="m", debit=10.0, credit=0.0, job_name="POCFAD",
                job_desc="", budget_activity="", customer_vendor="", allocation_memo="",
                event="", qty_awal=0.0, qty_akhir=0.0, uom="", nama_item="",
                harga_satuan=0.0, ket1="", ket2="")
    base.update(kw)
    return base


def rows_a():
    return [mkrow(id_no="GJ-1", debit=10.0, credit=0.0),
            mkrow(id_no="GJ-1", acc_statutory="2-1110", debit=0.0, credit=10.0),
            mkrow(id_no="GJ-2", debit=5.0)]


def table_count(table):
    conn = get_conn()
    try:
        return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    finally:
        conn.close()


# ---------- hash / summary ----------

def test_hash_ignores_order_and_float_noise():
    b = list(reversed(rows_a()))
    b[0]["debit"] = 5.0000000001
    assert glsync.compute_hash(rows_a()) == glsync.compute_hash(b)


def test_hash_changes_when_a_field_changes():
    base = glsync.compute_hash(rows_a())
    for field, value in [("debit", 11.0), ("memo", "x"), ("acc_statutory", "9-9"), ("tgl", "2026-02-02")]:
        changed = rows_a()
        changed[0][field] = value
        assert glsync.compute_hash(changed) != base, field
    assert glsync.compute_hash(rows_a()[:2]) != base


def test_summary_counts_added_removed_changed():
    old = rows_a()
    new = rows_a()
    new[2]["debit"] = 99.0                                   # GJ-2 amount changed
    new.append(mkrow(id_no="GJ-3", memo="new"))               # added
    del new[1]                                                # GJ-1 credit line removed
    s = glsync.summarize_changes(old, new)
    assert (s["added"], s["removed"], s["changed"]) == (1, 1, 1)


# ---------- storage ----------

def test_replace_all_replaces_and_logs():
    log = dict(synced_by="u", filename="a.xlsb", content_hash="h1", rows_before=0, rows_after=3,
               total_debit=15.0, total_credit=10.0, dropped=2, summary={"added": 3})
    svc.replace_all("smt", rows_a(), log)
    assert table_count("GLSMT") == 3
    svc.replace_all("smt", rows_a()[:1], dict(log, content_hash="h2", rows_after=1))
    assert table_count("GLSMT") == 1
    assert svc.last_sync("smt")["content_hash"] == "h2"
    assert [s["content_hash"] for s in svc.list_syncs("smt")] == ["h2", "h1"]
    assert svc.last_sync("etf") is None


def test_failed_replace_keeps_previous_data():
    log = dict(synced_by="u", filename="a.xlsb", content_hash="h1", rows_before=0, rows_after=3,
               total_debit=0, total_credit=0, dropped=0, summary={})
    svc.replace_all("smt", rows_a(), log)
    with pytest.raises(KeyError):
        svc.replace_all("smt", [{"id_no": "only-this"}], dict(log, content_hash="h2"))
    assert table_count("GLSMT") == 3
    assert svc.last_sync("smt")["content_hash"] == "h1"


def test_ensure_schema_rebuilds_legacy_table_with_other_columns():
    conn = get_conn()
    conn.execute("CREATE TABLE GLSMT (account_statutory TEXT, junk TEXT)")
    conn.execute("INSERT INTO GLSMT VALUES ('a','b')")
    conn.commit()
    conn.close()
    svc.replace_all("smt", rows_a(), dict(synced_by="u", filename="a", content_hash="h",
                                          rows_before=0, rows_after=3, total_debit=0,
                                          total_credit=0, dropped=0, summary={}))
    assert table_count("GLSMT") == 3


# ---------- sync_rows ----------

def test_sync_first_time_then_unchanged_then_changed():
    out = glsync.sync_rows("smt", "m.xlsb", "admin", rows_a(), dropped=4)
    assert out["changed"] is True and out["rows"] == 3
    assert out["total_debit"] == 15.0 and out["total_credit"] == 10.0 and out["balanced"] is False
    assert table_count("GLSMT") == 3

    again = glsync.sync_rows("smt", "m.xlsb", "admin", rows_a())
    assert again["changed"] is False
    assert len(svc.list_syncs("smt")) == 1                    # no extra log row

    changed = rows_a()
    changed[2]["memo"] = "edited"
    out = glsync.sync_rows("smt", "m2.xlsb", "admin", changed)
    assert out["changed"] is True
    last = svc.last_sync("smt")
    assert last["rows_before"] == 3 and last["rows_after"] == 3 and last["filename"] == "m2.xlsb"


def test_entities_are_independent():
    glsync.sync_rows("smt", "m.xlsb", "admin", rows_a())
    assert glsync.sync_rows("etf", "m.xlsb", "admin", rows_a())["changed"] is True
    assert table_count("GLETF") == 3 and table_count("GLSETF") == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_gl_sync.py -v`
Expected: FAIL (`cannot import name 'service'`)

- [ ] **Step 3: Write minimal implementation**

```python
# modules/general_ledger/service.py
"""General Ledger: table storage, sync log and viewer queries."""
import json
from datetime import datetime

from database import get_conn
from modules.general_ledger.parser import COLUMNS

ENTITIES = {
    "smt":  {"sheet": "GL SMT",  "table": "GLSMT",  "label": "GL SMT"},
    "etf":  {"sheet": "GL ETF",  "table": "GLETF",  "label": "GL ETF"},
    "setf": {"sheet": "GL SETF", "table": "GLSETF", "label": "GL SETF"},
}

_REAL = {"debit", "credit", "qty_awal", "qty_akhir", "harga_satuan"}
_INT = {"entry_no"}


def _col_type(c):
    return "REAL" if c in _REAL else "INTEGER" if c in _INT else "TEXT"


def _table_ddl(table):
    cols = ",\n    ".join(f"{c} {_col_type(c)}" for c in COLUMNS)
    return (f"CREATE TABLE IF NOT EXISTS {table} (\n    id INTEGER PRIMARY KEY AUTOINCREMENT,\n    {cols}\n);\n"
            f"CREATE INDEX IF NOT EXISTS idx_{table}_tgl ON {table}(tgl);\n"
            f"CREATE INDEX IF NOT EXISTS idx_{table}_acc ON {table}(acc_statutory);")


_LOG_DDL = """
CREATE TABLE IF NOT EXISTS gl_sync_log (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    entity       TEXT NOT NULL,
    synced_at    TEXT,
    synced_by    TEXT,
    filename     TEXT,
    content_hash TEXT,
    rows_before  INTEGER DEFAULT 0,
    rows_after   INTEGER DEFAULT 0,
    total_debit  REAL DEFAULT 0,
    total_credit REAL DEFAULT 0,
    dropped      INTEGER DEFAULT 0,
    summary      TEXT
);
CREATE INDEX IF NOT EXISTS idx_gl_sync_log_entity ON gl_sync_log(entity, id);
"""


def ensure_schema(conn) -> None:
    expected = {"id", *COLUMNS}
    for ent in ENTITIES.values():
        table = ent["table"]
        existing = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
        if existing and existing != expected:
            # Left over from the old pandas to_sql sync with other columns; data is re-synced anyway.
            conn.execute(f"DROP TABLE {table}")
        conn.executescript(_table_ddl(table))
    conn.executescript(_LOG_DDL)
    conn.commit()


def _ts() -> str:
    return datetime.now().isoformat(timespec="seconds")


def replace_all(entity, rows, log) -> None:
    table = ENTITIES[entity]["table"]
    conn = get_conn()
    try:
        ensure_schema(conn)
        try:
            conn.execute(f"DELETE FROM {table}")
            marks = ",".join("?" * len(COLUMNS))
            conn.executemany(
                f"INSERT INTO {table} ({','.join(COLUMNS)}) VALUES ({marks})",
                [tuple(r[c] for c in COLUMNS) for r in rows])
            conn.execute(
                "INSERT INTO gl_sync_log (entity, synced_at, synced_by, filename, content_hash, "
                "rows_before, rows_after, total_debit, total_credit, dropped, summary) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (entity, _ts(), log["synced_by"], log["filename"], log["content_hash"],
                 log["rows_before"], log["rows_after"], log["total_debit"], log["total_credit"],
                 log["dropped"], json.dumps(log["summary"], ensure_ascii=False)))
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    finally:
        conn.close()


def load_rows(entity) -> list:
    table = ENTITIES[entity]["table"]
    conn = get_conn()
    try:
        ensure_schema(conn)
        return [dict(r) for r in conn.execute(f"SELECT {','.join(COLUMNS)} FROM {table}")]
    finally:
        conn.close()


def _log_row(r):
    d = dict(r)
    d["summary"] = json.loads(d["summary"]) if d.get("summary") else {}
    return d


def list_syncs(entity, limit=10) -> list:
    conn = get_conn()
    try:
        ensure_schema(conn)
        cur = conn.execute("SELECT * FROM gl_sync_log WHERE entity=? ORDER BY id DESC LIMIT ?",
                           (entity, limit))
        return [_log_row(r) for r in cur]
    finally:
        conn.close()


def last_sync(entity):
    rows = list_syncs(entity, 1)
    return rows[0] if rows else None
```

```python
# modules/general_ledger/sync.py
"""General Ledger: sync parsed sheet rows into Flow, with change detection."""
import hashlib
import json

from modules.general_ledger import service
from modules.general_ledger.parser import COLUMNS

_KEY = ("id_no", "acc_statutory", "acc_management", "job_name", "memo", "tgl")
_EPS = 1e-6
_BALANCE_TOLERANCE = 1.0


def _norm(v):
    return round(v, 6) if isinstance(v, float) else v


def compute_hash(rows: list) -> str:
    """Order-independent content hash of parsed rows (floats rounded to 6 decimals)."""
    lines = sorted(json.dumps([_norm(r[c]) for c in COLUMNS], ensure_ascii=False) for r in rows)
    h = hashlib.sha256()
    for line in lines:
        h.update(line.encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()


def _aggregate(rows):
    out = {}
    for r in rows:
        acc = out.setdefault(tuple(r[k] for k in _KEY), [0.0, 0.0])
        acc[0] += r["debit"]
        acc[1] += r["credit"]
    return out


def summarize_changes(old_rows: list, new_rows: list) -> dict:
    """Entries added / removed / changed (debit or credit differs), keyed on _KEY."""
    old, new = _aggregate(old_rows), _aggregate(new_rows)
    return {
        "added": sum(1 for k in new if k not in old),
        "removed": sum(1 for k in old if k not in new),
        "changed": sum(1 for k in new if k in old
                       and any(abs(a - b) > _EPS for a, b in zip(new[k], old[k]))),
    }


def sync_rows(entity, filename, user, rows, dropped=0) -> dict:
    """Replace the entity's table with `rows` unless the content is identical to the last sync."""
    content_hash = compute_hash(rows)
    total_debit = sum(r["debit"] for r in rows)
    total_credit = sum(r["credit"] for r in rows)
    base = {"rows": len(rows), "total_debit": total_debit, "total_credit": total_credit,
            "balanced": abs(total_debit - total_credit) <= _BALANCE_TOLERANCE}

    last = service.last_sync(entity)
    if last and last["content_hash"] == content_hash:
        return {"changed": False, "summary": last["summary"], **base}

    old = service.load_rows(entity)
    summary = summarize_changes(old, rows)
    service.replace_all(entity, rows, {
        "synced_by": user, "filename": filename, "content_hash": content_hash,
        "rows_before": len(old), "rows_after": len(rows),
        "total_debit": total_debit, "total_credit": total_credit,
        "dropped": dropped, "summary": summary})
    return {"changed": True, "summary": summary, **base}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_gl_sync.py -v`
Expected: PASS (8 tests)

- [ ] **Step 5: Commit**

```bash
git add modules/general_ledger/service.py modules/general_ledger/sync.py tests/test_gl_sync.py
git commit -m "feat(gl): store GL rows per entity with sync log and change detection

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Query viewer (filter, paginasi, total)

**Files:**
- Modify: `modules/general_ledger/service.py` (tambah `query_rows`)
- Test: `tests/test_gl_service.py`

**Interfaces:**
- Consumes: `service.replace_all`, `ENTITIES`; helper `mkrow` dari `tests/test_gl_sync.py`.
- Produces: `query_rows(entity, filters, page=1, per_page=100) -> dict` dengan kunci `rows` (list of dict), `total` (jumlah baris cocok), `sum_debit`, `sum_credit`, `page`, `pages`, `per_page`. `filters` adalah dict dengan kunci opsional `date_from`, `date_to` (ISO `YYYY-MM-DD`), `acc`, `job`, `q`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_gl_service.py
from modules.general_ledger import service as svc
from tests.test_gl_sync import mkrow


def seed():
    rows = [
        mkrow(entry_no=1, id_no="GJ-1", tgl="2026-01-02", debit=100.0, credit=0.0,
              acc_statutory="6-1810", job_name="POCFAD", memo="Zoom"),
        mkrow(entry_no=2, id_no="GJ-1", tgl="2026-01-02", debit=0.0, credit=100.0,
              acc_statutory="2-1110", job_name="POCFAD", memo="Zoom"),
        mkrow(entry_no=3, id_no="BK-7", tgl="2026-03-10", debit=50.0, credit=0.0,
              acc_statutory="6-2190", job_name="POITEC", memo="100% diskon_promo"),
    ]
    svc.replace_all("smt", rows, dict(synced_by="u", filename="f", content_hash="h", rows_before=0,
                                      rows_after=3, total_debit=150.0, total_credit=100.0,
                                      dropped=0, summary={}))


def q(**f):
    return svc.query_rows("smt", f)


def test_no_filter_returns_all_ordered_with_totals():
    seed()
    r = q()
    assert r["total"] == 3 and [x["entry_no"] for x in r["rows"]] == [1, 2, 3]
    assert r["sum_debit"] == 150.0 and r["sum_credit"] == 100.0
    assert r["page"] == 1 and r["pages"] == 1


def test_filters():
    seed()
    assert q(date_from="2026-02-01")["total"] == 1
    assert q(date_to="2026-01-31")["total"] == 2
    assert q(acc="2-1110")["total"] == 1
    assert q(job="poit")["total"] == 1
    assert q(q="GJ-1")["total"] == 2
    assert q(q="zoom", job="POCFAD", acc="6-1810")["total"] == 1


def test_filtered_totals_follow_the_filter():
    seed()
    r = q(job="POCFAD")
    assert r["sum_debit"] == 100.0 and r["sum_credit"] == 100.0


def test_like_wildcards_are_literal():
    seed()
    assert q(q="%")["total"] == 1            # only the memo containing a literal '%'
    assert q(q="_")["total"] == 1            # only the memo containing a literal '_'
    assert q(q="no-such-text")["total"] == 0


def test_pagination_and_clamping():
    svc.replace_all("smt", [mkrow(entry_no=i, id_no=f"X-{i}") for i in range(1, 251)],
                    dict(synced_by="u", filename="f", content_hash="h", rows_before=0,
                         rows_after=250, total_debit=0, total_credit=0, dropped=0, summary={}))
    p1 = svc.query_rows("smt", {}, page=1)
    assert p1["pages"] == 3 and len(p1["rows"]) == 100
    assert len(svc.query_rows("smt", {}, page=3)["rows"]) == 50
    assert svc.query_rows("smt", {}, page=999)["page"] == 3
    assert svc.query_rows("smt", {}, page=0)["page"] == 1


def test_empty_table():
    r = svc.query_rows("etf", {})
    assert r["total"] == 0 and r["rows"] == [] and r["pages"] == 1 and r["sum_debit"] == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_gl_service.py -v`
Expected: FAIL (`AttributeError: module ... has no attribute 'query_rows'`)

- [ ] **Step 3: Write minimal implementation**

Tambahkan di akhir `modules/general_ledger/service.py`:

```python
def _like(text: str) -> str:
    esc = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{esc}%"


def _where(filters: dict):
    clauses, params = [], []
    if filters.get("date_from"):
        clauses.append("tgl >= ?")
        params.append(filters["date_from"])
    if filters.get("date_to"):
        clauses.append("tgl <= ?")
        params.append(filters["date_to"])
    if filters.get("acc"):
        clauses.append("(acc_statutory LIKE ? ESCAPE '\\' OR acc_management LIKE ? ESCAPE '\\' "
                       "OR acc_statutory_desc LIKE ? ESCAPE '\\' OR acc_management_desc LIKE ? ESCAPE '\\')")
        params += [_like(filters["acc"])] * 4
    if filters.get("job"):
        clauses.append("job_name LIKE ? ESCAPE '\\'")
        params.append(_like(filters["job"]))
    if filters.get("q"):
        clauses.append("(memo LIKE ? ESCAPE '\\' OR id_no LIKE ? ESCAPE '\\')")
        params += [_like(filters["q"])] * 2
    return (" WHERE " + " AND ".join(clauses)) if clauses else "", params


def query_rows(entity, filters, page=1, per_page=100) -> dict:
    table = ENTITIES[entity]["table"]
    where, params = _where(filters or {})
    conn = get_conn()
    try:
        ensure_schema(conn)
        total, sum_debit, sum_credit = conn.execute(
            f"SELECT COUNT(*), COALESCE(SUM(debit),0), COALESCE(SUM(credit),0) FROM {table}{where}",
            params).fetchone()
        pages = max(1, -(-total // per_page))
        page = min(max(1, page), pages)
        rows = [dict(r) for r in conn.execute(
            f"SELECT {','.join(COLUMNS)} FROM {table}{where} "
            f"ORDER BY entry_no, id LIMIT ? OFFSET ?", params + [per_page, (page - 1) * per_page])]
    finally:
        conn.close()
    return {"rows": rows, "total": total, "sum_debit": sum_debit, "sum_credit": sum_credit,
            "page": page, "pages": pages, "per_page": per_page}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_gl_service.py tests/test_gl_sync.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add modules/general_ledger/service.py tests/test_gl_service.py
git commit -m "feat(gl): filterable, paginated GL query with totals

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Routes, template, dan penghapusan stub COM

**Files:**
- Modify (ganti seluruh isi): `modules/general_ledger/routes.py`
- Modify (ganti seluruh isi): `templates/general_ledger/index.html`
- Modify: `static/js/app.js` (tambah ikon `general_ledger` di `FH_MODULE_ICONS`, sekitar baris 35)
- Create: `modules/general_ledger/__init__.py` jika belum ada (cek dulu; kalau ada, biarkan)
- Test: `tests/test_gl_routes.py`

**Interfaces:**
- Consumes: `parser.read_gl_sheet`, `parser.ParseError`, `sync.sync_rows`, `service.ENTITIES`, `service.query_rows`, `service.list_syncs`, `service.last_sync`, `management_report.formatting.id_number`.
- Produces: blueprint `general_ledger` (`url_prefix="/general-ledger"`); endpoint `general_ledger.index` (`GET /general-ledger/`, redirect ke `/general-ledger/smt`), `general_ledger.entity_page` (`GET /general-ledger/<entity>`), `general_ledger.sync_excel` (`POST /general-ledger/<entity>/sync`). `read_gl_sheet` diimpor sebagai nama modul-level di `routes.py` agar bisa di-monkeypatch di tes.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_gl_routes.py
import io

from modules.general_ledger import routes as gl_routes
from modules.general_ledger import service as svc
from modules.general_ledger.parser import ParseError, ParseResult
from tests.test_gl_sync import mkrow


def login(client, user="admin", password="Admin@123"):
    client.post("/auth/login", json={"username": user, "password": password})
    client.post("/select-company", data={"company_id": "2"})


def _sync(client, monkeypatch, rows, dropped=0, entity="smt", name="Master.xlsb"):
    monkeypatch.setattr(gl_routes, "read_gl_sheet", lambda f, sheet: ParseResult(rows, dropped))
    return client.post(f"/general-ledger/{entity}/sync",
                       data={"file": (io.BytesIO(b"x"), name)},
                       content_type="multipart/form-data")


def test_pages_require_login(client):
    for url in ("/general-ledger/", "/general-ledger/smt"):
        resp = client.get(url)
        assert resp.status_code == 302 and "/auth/login" in resp.headers["Location"]


def test_index_redirects_to_smt(client):
    login(client)
    resp = client.get("/general-ledger/")
    assert resp.status_code == 302 and resp.headers["Location"].endswith("/general-ledger/smt")


def test_unknown_entity_is_404(client):
    login(client)
    assert client.get("/general-ledger/xyz").status_code == 404


def test_three_tabs_render_and_empty_state(client):
    login(client)
    html = client.get("/general-ledger/etf").data.decode()
    assert "GL SMT" in html and "GL ETF" in html and "GL SETF" in html
    assert "Belum ada data" in html


def test_sync_success_then_unchanged(client, monkeypatch):
    login(client)
    rows = [mkrow(id_no="GJ-1", debit=10.0), mkrow(id_no="GJ-2", debit=0.0, credit=10.0)]
    r = _sync(client, monkeypatch, rows, dropped=3)
    j = r.get_json()
    assert r.status_code == 200 and j["ok"] and j["changed"] and "2 baris" in j["pesan"]
    assert "3" in j["pesan"]                                   # dropped rows reported
    again = _sync(client, monkeypatch, rows).get_json()
    assert again["ok"] and again["changed"] is False and "Sudah sinkron" in again["pesan"]


def test_sync_warns_when_unbalanced(client, monkeypatch):
    login(client)
    j = _sync(client, monkeypatch, [mkrow(debit=10.0, credit=0.0)]).get_json()
    assert j["ok"] and "tidak balance" in j["pesan"].lower()


def test_synced_data_is_listed_and_filtered(client, monkeypatch):
    login(client)
    _sync(client, monkeypatch, [mkrow(id_no="GJ-1", memo="Zoom langganan"),
                                mkrow(id_no="BK-9", memo="Listrik")])
    html = client.get("/general-ledger/smt").data.decode()
    assert "Zoom langganan" in html and "Listrik" in html
    html = client.get("/general-ledger/smt?q=Listrik").data.decode()
    assert "Listrik" in html and "Zoom langganan" not in html
    assert "Zoom langganan" not in client.get("/general-ledger/etf").data.decode()


def test_bad_page_param_does_not_error(client, monkeypatch):
    login(client)
    _sync(client, monkeypatch, [mkrow()])
    for qs in ("page=999", "page=abc", "page=-3"):
        assert client.get("/general-ledger/smt?" + qs).status_code == 200


def test_sync_rejects_non_xlsb(client):
    login(client)
    r = client.post("/general-ledger/smt/sync",
                    data={"file": (io.BytesIO(b"x"), "a.xlsx")},
                    content_type="multipart/form-data")
    assert r.status_code == 400 and "xlsb" in r.get_json()["pesan"]


def test_sync_without_file_is_400(client):
    login(client)
    r = client.post("/general-ledger/smt/sync", data={}, content_type="multipart/form-data")
    assert r.status_code == 400


def test_parse_error_keeps_old_data(client, monkeypatch):
    login(client)
    _sync(client, monkeypatch, [mkrow(memo="keep me")])

    def boom(f, sheet):
        raise ParseError("Sheet 'GL SMT' tidak ditemukan di file.")
    monkeypatch.setattr(gl_routes, "read_gl_sheet", boom)
    r = client.post("/general-ledger/smt/sync", data={"file": (io.BytesIO(b"x"), "m.xlsb")},
                    content_type="multipart/form-data")
    assert r.status_code == 400 and "tidak ditemukan" in r.get_json()["pesan"]
    assert svc.query_rows("smt", {})["total"] == 1


def test_sync_with_no_valid_rows_is_400(client, monkeypatch):
    login(client)
    r = _sync(client, monkeypatch, [], dropped=5)
    assert r.status_code == 400


def test_sync_unknown_entity_is_404(client):
    login(client)
    r = client.post("/general-ledger/xyz/sync", data={"file": (io.BytesIO(b"x"), "m.xlsb")},
                    content_type="multipart/form-data")
    assert r.status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_gl_routes.py -v`
Expected: FAIL (route `/general-ledger/smt` belum ada, atau `read_gl_sheet` tidak ada di routes)

- [ ] **Step 3: Write minimal implementation**

`modules/general_ledger/routes.py` (ganti seluruh isi):

```python
# modules/general_ledger/routes.py
import io

from flask import Blueprint, abort, jsonify, redirect, render_template, request, url_for
from flask_jwt_extended import get_jwt

from auth.middleware import is_admin, json_admin_required, jwt_html_required
from modules.general_ledger import service
from modules.general_ledger import sync as gl_sync
from modules.general_ledger.parser import ParseError, read_gl_sheet
from modules.management_report.formatting import id_number

bp = Blueprint("general_ledger", __name__, url_prefix="/general-ledger")

bp.add_app_template_filter(lambda v: id_number(v, 0), "gl_num")

_FILTER_KEYS = ("date_from", "date_to", "acc", "job", "q")


def _entity_or_404(entity):
    if entity not in service.ENTITIES:
        abort(404)
    return service.ENTITIES[entity]


def _page():
    try:
        return int(request.args.get("page", 1))
    except (TypeError, ValueError):
        return 1


@bp.route("/", methods=["GET"])
@jwt_html_required
def index():
    return redirect(url_for("general_ledger.entity_page", entity="smt"))


@bp.route("/<entity>", methods=["GET"])
@jwt_html_required
def entity_page(entity):
    ent = _entity_or_404(entity)
    filters = {k: (request.args.get(k) or "").strip() for k in _FILTER_KEYS}
    result = service.query_rows(entity, {k: v for k, v in filters.items() if v}, page=_page())
    try:
        can_manage = is_admin(get_jwt())
    except Exception:
        can_manage = False
    return render_template(
        "general_ledger/index.html",
        entity=entity, ent=ent, entities=service.ENTITIES, filters=filters, result=result,
        last=service.last_sync(entity), syncs=service.list_syncs(entity, 5),
        can_manage=can_manage, active_page="general_ledger", use_unified_header=True,
    )


@bp.route("/<entity>/sync", methods=["POST"])
@json_admin_required
def sync_excel(entity):
    if entity not in service.ENTITIES:
        return jsonify({"ok": False, "pesan": "Entitas tidak dikenal."}), 404
    ent = service.ENTITIES[entity]
    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify({"ok": False, "pesan": "File belum dipilih."}), 400
    if not f.filename.lower().endswith(".xlsb"):
        return jsonify({"ok": False, "pesan": "File harus berformat .xlsb."}), 400
    try:
        result = read_gl_sheet(io.BytesIO(f.read()), ent["sheet"])
        if not result.rows:
            raise ParseError(f"Tidak ada baris data yang valid di sheet {ent['sheet']}.")
    except ParseError as e:
        return jsonify({"ok": False, "pesan": str(e)}), 400
    out = gl_sync.sync_rows(entity, f.filename, get_jwt().get("username", ""),
                            result.rows, result.dropped)
    if not out["changed"]:
        pesan = f"Sudah sinkron: tidak ada perubahan sejak sync terakhir ({out['rows']} baris)."
    else:
        s = out["summary"]
        pesan = (f"Sync {ent['label']} selesai: {out['rows']} baris "
                 f"({s['added']} baru, {s['removed']} dihapus, {s['changed']} berubah; "
                 f"{result.dropped} baris dilewati).")
    if not out["balanced"]:
        pesan += " Peringatan: total Debit dan Credit tidak balance."
    return jsonify({"ok": True, "dropped": result.dropped, "pesan": pesan, **out})
```

`templates/general_ledger/index.html` (ganti seluruh isi):

```html
{% extends "base.html" %}
{% block title %}General Ledger - {{ ent.label }}{% endblock %}

{% block head %}
<style>
.gl-table { border-collapse:collapse; width:100%; font-size:.8125rem; white-space:nowrap; }
.gl-table th, .gl-table td { padding:.3rem .5rem; border-bottom:1px solid var(--sl-200); }
.gl-table th { text-align:left; background:var(--sl-50); position:sticky; top:0; }
.gl-table .num { text-align:right; font-variant-numeric:tabular-nums; }
.gl-wrap { overflow:auto; max-height:65vh; }
.gl-muted { color:var(--sl-500); font-size:.8125rem; }
.gl-cards { display:flex; gap:1rem; flex-wrap:wrap; margin:.5rem 0 1rem; }
.gl-card { padding:.6rem .9rem; border:1px solid var(--sl-200); border-radius:8px; min-width:150px; }
.gl-card b { display:block; font-size:1.05rem; font-variant-numeric:tabular-nums; }
.gl-filter { display:flex; gap:.5rem; flex-wrap:wrap; align-items:flex-end; margin-bottom:.75rem; }
.gl-filter label { display:flex; flex-direction:column; font-size:.75rem; }
.gl-pager { display:flex; align-items:center; gap:.75rem; margin:.6rem 0; }
</style>
{% endblock %}

{% block module_tabs %}
<div class="tabs" style="margin-bottom:0">
  {% for key, e in entities.items() %}
  <a class="tab-btn{{ ' active' if key == entity else '' }}" href="{{ url_for('general_ledger.entity_page', entity=key) }}">{{ e.label }}</a>
  {% endfor %}
</div>
{% endblock %}

{% block content %}
{% set diff = result.sum_debit - result.sum_credit %}
<div class="card" style="margin-bottom:1rem">
  <strong>Sinkronisasi Excel · {{ ent.label }}</strong>
  <div class="gl-muted" style="margin:.25rem 0">
    {% if last %}Terakhir sync: {{ last.synced_at }} · {{ last.synced_by }} · {{ last.filename }} · {{ last.rows_after }} baris
    {% else %}Belum pernah sync.{% endif %}
  </div>
  {% if can_manage %}
  <div style="margin:.5rem 0">
    <input type="file" id="gl-file" accept=".xlsb">
    <button class="btn btn-primary btn-sm" id="gl-sync-btn" onclick="glSync()">Upload &amp; Sync .xlsb</button>
    <span id="gl-sync-msg" class="gl-muted"></span>
  </div>
  <div class="gl-muted">Pilih file <code>GL - MASTER.xlsb</code>; hanya sheet <b>{{ ent.sheet }}</b> yang diproses.</div>
  {% endif %}
</div>

{% if not last and result.total == 0 and not filters.values() | select | list %}
<div class="card">Belum ada data {{ ent.label }}. Upload file GL - MASTER.xlsb untuk memulai.</div>
{% else %}
<div class="gl-cards">
  <div class="gl-card">Baris<b>{{ result.total | gl_num }}</b></div>
  <div class="gl-card">Total Debit<b>{{ result.sum_debit | gl_num }}</b></div>
  <div class="gl-card">Total Credit<b>{{ result.sum_credit | gl_num }}</b></div>
  <div class="gl-card">Selisih<b>{{ diff | gl_num }}</b></div>
</div>

<form class="gl-filter" method="get">
  <label>Dari tanggal<input type="date" name="date_from" value="{{ filters.date_from }}"></label>
  <label>Sampai tanggal<input type="date" name="date_to" value="{{ filters.date_to }}"></label>
  <label>Akun<input type="text" name="acc" value="{{ filters.acc }}" placeholder="kode / nama akun"></label>
  <label>Job Name<input type="text" name="job" value="{{ filters.job }}"></label>
  <label>Memo / ID#<input type="text" name="q" value="{{ filters.q }}"></label>
  <button class="btn btn-primary btn-sm" type="submit">Terapkan</button>
  <a class="btn btn-sm" href="{{ url_for('general_ledger.entity_page', entity=entity) }}">Reset</a>
</form>

<div class="gl-wrap">
<table class="gl-table">
  <thead><tr>
    <th>No</th><th>Tipe</th><th>Acc Statutory</th><th>Deskripsi Statutory</th><th>Acc Management</th>
    <th>ID#</th><th>Tanggal</th><th>Memo</th><th class="num">Debit</th><th class="num">Credit</th>
    <th>Job Name</th><th>Budget Activity</th><th>Customer/Vendor</th><th>Allocation Memo</th>
    <th>Event</th><th>Ket 1</th><th>Ket 2</th>
  </tr></thead>
  <tbody>
  {% for r in result.rows %}
  <tr>
    <td>{{ r.entry_no if r.entry_no is not none else '' }}</td><td>{{ r.source_type }}</td>
    <td>{{ r.acc_statutory }}</td><td>{{ r.acc_statutory_desc }}</td><td>{{ r.acc_management }}</td>
    <td>{{ r.id_no }}</td><td>{{ r.tgl or '' }}</td><td>{{ r.memo }}</td>
    <td class="num">{{ r.debit | gl_num }}</td><td class="num">{{ r.credit | gl_num }}</td>
    <td>{{ r.job_name }}</td><td>{{ r.budget_activity }}</td><td>{{ r.customer_vendor }}</td>
    <td>{{ r.allocation_memo }}</td><td>{{ r.event }}</td><td>{{ r.ket1 }}</td><td>{{ r.ket2 }}</td>
  </tr>
  {% else %}
  <tr><td colspan="17" class="gl-muted">Tidak ada baris yang cocok dengan filter.</td></tr>
  {% endfor %}
  </tbody>
</table>
</div>

<div class="gl-pager">
  {% set qs = request.args.to_dict() %}{% set _ = qs.pop('page', none) %}
  {% if result.page > 1 %}<a class="btn btn-sm" href="?{{ (qs | urlencode) ~ ('&' if qs else '') }}page={{ result.page - 1 }}">&laquo; Sebelumnya</a>{% endif %}
  <span class="gl-muted">Halaman {{ result.page }} dari {{ result.pages }}</span>
  {% if result.page < result.pages %}<a class="btn btn-sm" href="?{{ (qs | urlencode) ~ ('&' if qs else '') }}page={{ result.page + 1 }}">Berikutnya &raquo;</a>{% endif %}
</div>

{% if syncs %}
<details style="margin-top:1rem">
  <summary>Riwayat sync terakhir ({{ syncs | length }})</summary>
  <table class="gl-table" style="max-width:820px; margin-top:.3rem">
    <thead><tr><th>Waktu</th><th>User</th><th>File</th><th class="num">Baris</th><th class="num">Baru</th><th class="num">Dihapus</th><th class="num">Berubah</th></tr></thead>
    <tbody>
    {% for s in syncs %}
    <tr><td>{{ s.synced_at }}</td><td>{{ s.synced_by }}</td><td>{{ s.filename }}</td>
      <td class="num">{{ s.rows_before | gl_num }} → {{ s.rows_after | gl_num }}</td>
      <td class="num">{{ s.summary.added }}</td><td class="num">{{ s.summary.removed }}</td><td class="num">{{ s.summary.changed }}</td></tr>
    {% endfor %}
    </tbody>
  </table>
</details>
{% endif %}
{% endif %}
{% endblock %}

{% block scripts %}
<script>
async function glSync() {
  const f = document.getElementById('gl-file').files[0];
  const msg = document.getElementById('gl-sync-msg');
  if (!f) { msg.textContent = 'Pilih file GL - MASTER.xlsb dulu.'; return; }
  const btn = document.getElementById('gl-sync-btn');
  btn.disabled = true; msg.textContent = 'Menyinkronkan...';
  const fd = new FormData(); fd.append('file', f);
  try {
    const r = await fetch('/general-ledger/{{ entity }}/sync', {method: 'POST', body: fd, credentials: 'same-origin'});
    const j = await r.json();
    msg.textContent = j.pesan || (r.ok ? 'Selesai.' : 'Gagal.');
    if (j.ok && j.changed) setTimeout(() => location.reload(), 1200);
  } catch (e) { msg.textContent = 'Gagal sync: ' + e; }
  btn.disabled = false;
}
</script>
{% endblock %}
```

Sebelum menulis template, cek nama block script di `templates/base.html` (`grep -n "block " templates/base.html`). Kalau namanya bukan `scripts`, pakai nama yang ada (MR memakai bagian script di dalam `content`; ikuti salah satu).

Tambahkan di `static/js/app.js` dalam `FH_MODULE_ICONS`, setelah baris `management_report`:

```javascript
  general_ledger: '<path d="M5 3h11l3 3v15H5Z"/><path d="M8 9h8M8 13h8M8 17h5"/>',
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_gl_routes.py tests/test_gl_service.py tests/test_gl_sync.py tests/test_gl_parser.py tests/test_dashboard.py -v`
Expected: PASS (dashboard memakai endpoint `general_ledger.index`, tetap ada)

- [ ] **Step 5: Smoke test di browser dan commit**

Jalankan aplikasi (lihat cara run yang biasa dipakai di proyek), buka `/general-ledger/`, pastikan 3 tab muncul dan tab aktif ter-highlight, tombol Upload terlihat untuk admin, dan layout tidak rusak.

```bash
git add modules/general_ledger/routes.py templates/general_ledger/index.html static/js/app.js tests/test_gl_routes.py
git commit -m "feat(gl): three GL sub menus with upload sync and filterable viewer

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Uji dengan file GL - MASTER.xlsb asli

**Files:**
- Test: `tests/test_gl_real_file.py`

**Interfaces:**
- Consumes: `parser.read_gl_sheet`, `sync.sync_rows`, `service.query_rows`.

- [ ] **Step 1: Write the test**

```python
# tests/test_gl_real_file.py
"""Runs against the real GL - MASTER.xlsb when it is reachable; skipped otherwise."""
import os
import shutil

import pytest
from pyxlsb import open_workbook

from modules.general_ledger import service as svc
from modules.general_ledger import sync as glsync
from modules.general_ledger.parser import read_gl_sheet

SRC = r"Y:\Seagate\Management Report\2026\0926\GL - MASTER.xlsb"
pytestmark = pytest.mark.skipif(not os.path.exists(SRC), reason="GL - MASTER.xlsb not reachable")


@pytest.fixture(scope="module")
def local_copy(tmp_path_factory):
    dst = tmp_path_factory.mktemp("glmaster") / "gl.xlsb"
    shutil.copy(SRC, dst)                      # the master is usually open in Excel
    return str(dst)


def control_totals(path, sheet):
    with open_workbook(path) as wb, wb.get_sheet(sheet) as sh:
        for row in sh.rows():
            vals = {c.c: c.v for c in row}
            return vals.get(10), vals.get(11)    # control row: total Debit, total Credit


@pytest.mark.parametrize("entity", ["smt", "etf", "setf"])
def test_real_sheet_matches_excel_control_row(local_copy, entity):
    sheet = svc.ENTITIES[entity]["sheet"]
    res = read_gl_sheet(local_copy, sheet)
    assert len(res.rows) > 100
    ctl_debit, ctl_credit = control_totals(local_copy, sheet)
    assert abs(sum(r["debit"] for r in res.rows) - ctl_debit) < 1.0
    assert abs(sum(r["credit"] for r in res.rows) - ctl_credit) < 1.0
    out = glsync.sync_rows(entity, "GL - MASTER.xlsb", "test", res.rows, res.dropped)
    assert out["changed"] and out["balanced"]
    assert svc.query_rows(entity, {})["total"] == len(res.rows)
```

- [ ] **Step 2: Run it**

Run: `python -m pytest tests/test_gl_real_file.py -v`
Expected: PASS untuk 3 entitas, atau SKIPPED jika drive Y: tidak tersedia. Kalau gagal pada total debit/credit, periksa dulu apakah baris yang dibuang parser (`dropped`) membawa nilai Debit/Credit; sesuaikan aturan pembuangan di `parser.normalise_rows` dan tambah tes di `tests/test_gl_parser.py` untuk kasus itu, jangan melonggarkan toleransi.

- [ ] **Step 3: Jalankan seluruh suite GL dan suite terkait**

Run: `python -m pytest tests/test_gl_parser.py tests/test_gl_sync.py tests/test_gl_service.py tests/test_gl_routes.py tests/test_gl_real_file.py tests/test_dashboard.py tests/test_mr_routes.py -q`
Expected: semua PASS

- [ ] **Step 4: Verifikasi manual end-to-end**

Jalankan aplikasi, login sebagai admin, buka tiap tab GL, upload `GL - MASTER.xlsb`, lalu cek: pesan sync benar, jumlah baris dan total sesuai, upload kedua file yang sama menghasilkan "Sudah sinkron", filter dan paginasi bekerja, dan tab entitas lain tetap kosong sampai disinkronkan.

- [ ] **Step 5: Commit**

```bash
git add tests/test_gl_real_file.py
git commit -m "test(gl): verify GL sync against real GL - MASTER.xlsb control totals

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```
