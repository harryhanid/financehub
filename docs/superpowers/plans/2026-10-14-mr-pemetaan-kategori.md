# MR Pemetaan Kategori (F0) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tambah ke menu Pemetaan Management Report tiga mapping yang dibutuhkan SPT Badan: akun → kategori (M1), daftar Kategori LK (M2), dan jenis PPh baku + alias (M3), lengkap dengan panel akun yang belum dipetakan dan nomor versi mapping.

**Architecture:** Modul baru `category_map.py` di paket `management_report` dengan tabel sendiri (`gl_category_map`, `gl_category_lk`, `gl_pph_alias`, `gl_category_sync_log`, `gl_mapping_meta`), sehingga sync Pemetaan COA & CC yang sudah ada (`coa_map.py`) tidak diubah. M1 disinkronkan dari sheet `COA` milik `GL - MASTER.xlsb`; M2 dan M3 dikelola di aplikasi. Setiap perubahan menaikkan `version` mapping. Halaman baru `/management-report/pemetaan/kategori` menjadi tab "Kategori SPT".

**Tech Stack:** Python 3 / Flask, SQLite (`database.get_conn`), `pyxlsb`, Jinja2, pytest.

**Spec:** `docs/specs/2026-10-14-spt-badan-prd.md` (Bagian 14.5 dan 14.11)

## Global Constraints

- Tidak mengubah `coa_map.py`, tabel `gl_coa_map`/`gl_cc_map`, atau route Pemetaan yang sudah ada.
- Sumber M1 adalah sheet `COA` pada `GL - MASTER.xlsb`: kolom indeks 1 `COA SMT`, 3 `COA ETF`, 12 `CATEGORIES EXPENSE (6-****)`, 13 `Category LK`, 14 `Category SPT`; baris header di indeks 1.
- Nilai `TBA` / `tba` dinormalkan menjadi `TBA` dan dianggap *belum dipetakan*; angka 0 dan sel error (`0x..`) dianggap kosong.
- Hanya admin (`json_admin_required`) yang boleh sync dan mengubah mapping; semua pengguna login boleh melihat (`jwt_html_required`).
- Jenis PPh baku persis: `PPh 21`, `PPh 23`, `PPh 4(2)`, `Non PPh`.
- Bahasa pesan antarmuka: Indonesia. Kode, nama tabel, dan komentar: Inggris.
- Test memakai database uji otomatis (fixture `clean_db` di `tests/conftest.py`); jangan menyentuh `finance_hub.db`.

## Review Focus

- File `.xlsb` tanpa sheet `COA` atau dengan header berbeda → pesan jelas, mapping lama tidak berubah (Task 1 dan Task 4).
- Akun yang sama di SMT dan ETF dengan kategori berbeda → tersimpan terpisah per sumber (Task 1).
- Sync ulang tidak menghapus edit manual Kategori LK dan alias PPh (Task 2).
- `tba` huruf kecil dan angka `0.0` pada kolom kategori (Task 1).
- Non-admin mencoba sync/ubah → 403 dan data tidak berubah (Task 4).

---

## File Structure

| File | Aksi | Tanggung jawab |
|---|---|---|
| `app/modules/management_report/category_map.py` | Create | Parse sheet COA, skema, sync M1, daftar LK (M2), alias PPh (M3), versi mapping, pencarian, daftar akun belum dipetakan |
| `app/modules/general_ledger/service.py` | Modify | Tambah `account_totals(entity, year)` |
| `app/modules/management_report/routes.py` | Modify | Route halaman dan aksi Kategori SPT |
| `app/templates/management_report/kategori.html` | Create | Halaman Kategori SPT |
| `app/templates/management_report/_linktabs.html` | Modify | Tab "Kategori SPT" |
| `app/tests/test_mrc_category_map.py` | Create | Test parse, sync, LK, alias, unmapped |
| `app/tests/test_mrc_category_routes.py` | Create | Test route dan halaman |
| `app/tests/test_gl_service.py` | Modify | Test `account_totals` |

---

### Task 1: Parse sheet COA dan sync M1

**Files:**
- Create: `app/modules/management_report/category_map.py`
- Test: `app/tests/test_mrc_category_map.py`

**Interfaces:**
- Consumes: `modules.management_report.coa_map` → `CoaParseError`, `_read_sheets(fileobj, names, *normalisers)`, `_text(v)`, `_cell(row, i)`; `database.get_conn`.
- Produces (dipakai Task 2–4 dan Plan SPT):
  - `UNMAPPED_TOKEN = "TBA"`, `PPH_TYPES = ("PPh 21", "PPh 23", "PPh 4(2)", "Non PPh")`
  - `is_unmapped(value: str) -> bool`
  - `normalise_categories(sheet_rows: list) -> list[dict]` — dict berisi `source, account, categories_expense, category_lk, category_spt`
  - `read_category_sheet(fileobj) -> list[dict]`
  - `ensure_schema(conn) -> None`
  - `sync_categories(filename: str, user: str, rows: list) -> dict` — `{"changed": bool, "rows_smt": int, "rows_etf": int}`
  - `get_category_map() -> dict[(source, account)] -> {"categories_expense", "category_lk", "category_spt"}`
  - `last_sync() -> dict | None`, `list_syncs(limit=10) -> list[dict]`
  - `get_version() -> int`

- [ ] **Step 1: Write the failing tests**

Create `app/tests/test_mrc_category_map.py`:

```python
# tests/test_mrc_category_map.py
import pytest

from modules.management_report import category_map as cm
from modules.management_report.coa_map import CoaParseError

HEADER = [None, "COA SMT", "Description", "COA ETF", "Description", "FROM :", "COA HO",
          "Sub Account", "CATEGORIES", "CATEGORIES 2", None, "BUDGET CATEGORY",
          "CATEGORIES EXPENSE (6-****)", "Category LK", "Category SPT"]


def row(smt=None, etf=None, exp=None, lk=None, spt=None):
    r = [None] * 15
    r[1], r[3], r[12], r[13], r[14] = smt, etf, exp, lk, spt
    return r


def sheet(*rows):
    return [[None] * 15, HEADER, *rows]


def as_map(rows):
    return {(r["source"], r["account"]): (r["categories_expense"], r["category_lk"], r["category_spt"])
            for r in rows}


# ---------- parse ----------

def test_maps_smt_and_etf_accounts_with_stripped_categories():
    rows = cm.normalise_categories(sheet(
        row("6-1810", None, " Office Supplies And Equipment Expense ", "Beban Operasional", "BIAYA LAINNYA"),
        row("6-1720", "6-2150", "Entertainment & Gift Expense", "HARGA POKOK PENJUALAN", "BIAYA LAINNYA")))
    assert as_map(rows) == {
        ("SMT", "6-1810"): ("Office Supplies And Equipment Expense", "Beban Operasional", "BIAYA LAINNYA"),
        ("SMT", "6-1720"): ("Entertainment & Gift Expense", "HARGA POKOK PENJUALAN", "BIAYA LAINNYA"),
        ("ETF", "6-2150"): ("Entertainment & Gift Expense", "HARGA POKOK PENJUALAN", "BIAYA LAINNYA"),
    }


def test_same_account_in_smt_and_etf_keeps_separate_categories():
    rows = cm.normalise_categories(sheet(
        row("6-1000", None, "", "Beban Operasional", "BIAYA LAINNYA"),
        row(None, "6-1000", "", "HARGA POKOK PENJUALAN", "BIAYA TRANSPORTASI")))
    assert as_map(rows) == {
        ("SMT", "6-1000"): ("", "Beban Operasional", "BIAYA LAINNYA"),
        ("ETF", "6-1000"): ("", "HARGA POKOK PENJUALAN", "BIAYA TRANSPORTASI"),
    }


def test_tba_is_normalised_and_zero_or_error_cells_are_empty():
    rows = cm.normalise_categories(sheet(
        row("6-1", None, "tba", "tba", "TBA"),
        row("6-2", None, 0.0, 0.0, "0x2a"),
        row("6-3", None, None, None, None)))
    # 6-2 (all cells 0 / error) and 6-3 (all empty) carry no category at all, so they are skipped
    assert as_map(rows) == {("SMT", "6-1"): ("TBA", "TBA", "TBA")}


def test_rows_without_any_account_are_skipped_and_duplicates_keep_first():
    rows = cm.normalise_categories(sheet(
        row(None, None, "x", "Beban Operasional", "BIAYA LAINNYA"),
        row("6-1", None, "a", "Beban Operasional", "BIAYA LAINNYA"),
        row("6-1", None, "b", "HARGA POKOK PENJUALAN", "BIAYA SEWA")))
    assert as_map(rows) == {("SMT", "6-1"): ("a", "Beban Operasional", "BIAYA LAINNYA")}


def test_numeric_account_is_text():
    rows = cm.normalise_categories(sheet(row(61810.0, None, "", "Beban Operasional", "BIAYA LAINNYA")))
    assert [r["account"] for r in rows] == ["61810"]


def test_wrong_header_or_empty_sheet_raises():
    bad = list(HEADER)
    bad[13] = "Kategori"
    with pytest.raises(CoaParseError, match="Category LK"):
        cm.normalise_categories([[None] * 15, bad])
    with pytest.raises(CoaParseError, match="kosong"):
        cm.normalise_categories([[None] * 15])


def test_is_unmapped():
    assert cm.is_unmapped("") and cm.is_unmapped("TBA") and cm.is_unmapped(" tba ")
    assert not cm.is_unmapped("BIAYA LAINNYA")


# ---------- storage ----------

RO = cm.normalise_categories(sheet(row("6-1810", None, "Office", "Beban Operasional", "BIAYA LAINNYA")))


def test_sync_stores_logs_and_second_identical_sync_is_unchanged():
    out = cm.sync_categories("GL - MASTER.xlsb", "admin", RO)
    assert out == {"changed": True, "rows_smt": 1, "rows_etf": 0}
    assert cm.get_category_map()[("SMT", "6-1810")] == {
        "categories_expense": "Office", "category_lk": "Beban Operasional", "category_spt": "BIAYA LAINNYA"}
    assert cm.last_sync()["filename"] == "GL - MASTER.xlsb"
    again = cm.sync_categories("GL - MASTER.xlsb", "admin", RO)
    assert again["changed"] is False and len(cm.list_syncs()) == 1


def test_sync_replaces_previous_rows_and_bumps_version():
    cm.sync_categories("a.xlsb", "admin", RO)
    v1 = cm.get_version()
    other = cm.normalise_categories(sheet(row("6-2000", None, "", "HARGA POKOK PENJUALAN", "BIAYA SEWA")))
    cm.sync_categories("b.xlsb", "admin", other)
    assert list(cm.get_category_map()) == [("SMT", "6-2000")]
    assert cm.get_version() == v1 + 1
    assert [s["filename"] for s in cm.list_syncs()] == ["b.xlsb", "a.xlsb"]


def test_failed_sync_keeps_previous_mapping():
    cm.sync_categories("a.xlsb", "admin", RO)
    with pytest.raises(KeyError):
        cm.sync_categories("b.xlsb", "admin", [{"source": "SMT", "account": "x"}])
    assert list(cm.get_category_map()) == [("SMT", "6-1810")]
    assert cm.last_sync()["filename"] == "a.xlsb"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd app && python -m pytest tests/test_mrc_category_map.py -q -p no:cacheprovider -W ignore`
Expected: FAIL / ERROR — `ModuleNotFoundError: No module named 'modules.management_report.category_map'`

- [ ] **Step 3: Write the implementation**

Create `app/modules/management_report/category_map.py`:

```python
# modules/management_report/category_map.py
"""Account -> category mapping used by SPT Badan (and shown in the Pemetaan menu).

M1 account categories come from the 'COA' sheet of GL - MASTER.xlsb; M2 (Kategori LK list) and
M3 (PPh type aliases) are maintained in the app. Every change bumps a mapping version."""
import hashlib
import json
from datetime import datetime

from database import get_conn
from modules.management_report.coa_map import CoaParseError, _cell, _read_sheets, _text

SHEET_NAME = "COA"
_HEADER_ROW = 1                                   # 0-based; row 0 is a numbering row
_SOURCE_COL = {"SMT": 1, "ETF": 3}                # COA SMT, COA ETF
_EXPENSE_COL, _LK_COL, _SPT_COL = 12, 13, 14
_EXPECTED_HEADER = {1: "COA SMT", 3: "COA ETF", 12: "CATEGORIES EXPENSE (6-****)",
                    13: "Category LK", 14: "Category SPT"}
UNMAPPED_TOKEN = "TBA"
PPH_TYPES = ("PPh 21", "PPh 23", "PPh 4(2)", "Non PPh")


def is_unmapped(value) -> bool:
    v = str(value or "").strip()
    return v == "" or v.upper() == UNMAPPED_TOKEN


def _clean(v) -> str:
    if isinstance(v, (int, float)) and not isinstance(v, bool) and v == 0:
        return ""                                    # numeric 0 in the sheet means "no value"
    return _text(v)


def _category(v) -> str:
    c = _clean(v)
    return UNMAPPED_TOKEN if c.upper() == UNMAPPED_TOKEN else c


def normalise_categories(sheet_rows) -> list:
    if len(sheet_rows) <= _HEADER_ROW:
        raise CoaParseError(f"Sheet '{SHEET_NAME}' kosong.")
    header = sheet_rows[_HEADER_ROW]
    for pos, label in _EXPECTED_HEADER.items():
        actual = " ".join(str(_cell(header, pos) or "").split()).lower()
        if actual != label.lower():
            raise CoaParseError(
                f"Header sheet '{SHEET_NAME}' tidak sesuai: kolom {pos + 1} harus '{label}'.")
    rows, seen = [], set()
    for r in sheet_rows[_HEADER_ROW + 1:]:
        expense = _category(_cell(r, _EXPENSE_COL))
        lk = _category(_cell(r, _LK_COL))
        spt = _category(_cell(r, _SPT_COL))
        if not (expense or lk or spt):
            continue                                  # group/heading accounts carry no category
        for source, col in _SOURCE_COL.items():
            account = _text(_cell(r, col))
            if account and (source, account) not in seen:
                seen.add((source, account))
                rows.append({"source": source, "account": account, "categories_expense": expense,
                             "category_lk": lk, "category_spt": spt})
    return rows


def read_category_sheet(fileobj) -> list:
    return _read_sheets(fileobj, [SHEET_NAME], lambda r: normalise_categories(r))[0]


_DDL = """
CREATE TABLE IF NOT EXISTS gl_category_map (
    source             TEXT NOT NULL,
    account            TEXT NOT NULL,
    categories_expense TEXT NOT NULL DEFAULT '',
    category_lk        TEXT NOT NULL DEFAULT '',
    category_spt       TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (source, account)
);
CREATE TABLE IF NOT EXISTS gl_category_sync_log (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    synced_at    TEXT,
    synced_by    TEXT,
    filename     TEXT,
    content_hash TEXT,
    rows_smt     INTEGER DEFAULT 0,
    rows_etf     INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS gl_mapping_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def ensure_schema(conn) -> None:
    conn.executescript(_DDL)
    conn.execute("INSERT OR IGNORE INTO gl_mapping_meta (key, value) VALUES ('version', '1')")
    conn.commit()


def bump_version(conn) -> None:
    conn.execute("UPDATE gl_mapping_meta SET value = CAST(CAST(value AS INTEGER) + 1 AS TEXT) "
                 "WHERE key = 'version'")


def get_version() -> int:
    conn = get_conn()
    try:
        ensure_schema(conn)
        return int(conn.execute("SELECT value FROM gl_mapping_meta WHERE key='version'").fetchone()[0])
    finally:
        conn.close()


def compute_hash(rows) -> str:
    lines = sorted(json.dumps([r["source"], r["account"], r["categories_expense"], r["category_lk"],
                               r["category_spt"]], ensure_ascii=False) for r in rows)
    h = hashlib.sha256()
    for line in lines:
        h.update(line.encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()


def get_category_map() -> dict:
    conn = get_conn()
    try:
        ensure_schema(conn)
        return {(r["source"], r["account"]): {"categories_expense": r["categories_expense"],
                                              "category_lk": r["category_lk"],
                                              "category_spt": r["category_spt"]}
                for r in conn.execute("SELECT * FROM gl_category_map")}
    finally:
        conn.close()


def last_sync():
    conn = get_conn()
    try:
        ensure_schema(conn)
        row = conn.execute("SELECT * FROM gl_category_sync_log ORDER BY id DESC LIMIT 1").fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def list_syncs(limit=10) -> list:
    conn = get_conn()
    try:
        ensure_schema(conn)
        return [dict(r) for r in conn.execute(
            "SELECT * FROM gl_category_sync_log ORDER BY id DESC LIMIT ?", (max(1, limit),))]
    finally:
        conn.close()


def _count_rows() -> int:
    conn = get_conn()
    try:
        ensure_schema(conn)
        return conn.execute("SELECT COUNT(*) FROM gl_category_map").fetchone()[0]
    finally:
        conn.close()


def _on_synced(conn, rows) -> None:
    """Hook run inside the sync transaction after the map was replaced (extended in Task 2)."""


def sync_categories(filename, user, rows) -> dict:
    """Replace the account->category map unless identical to the last sync (and still in the table)."""
    rows = list(rows)
    content_hash = compute_hash(rows)
    n_smt = sum(1 for r in rows if r["source"] == "SMT")
    n_etf = len(rows) - n_smt
    last = last_sync()
    if (last and last["content_hash"] == content_hash
            and _count_rows() == last["rows_smt"] + last["rows_etf"]):
        return {"changed": False, "rows_smt": n_smt, "rows_etf": n_etf}
    conn = get_conn()
    try:
        ensure_schema(conn)
        try:
            conn.execute("DELETE FROM gl_category_map")
            conn.executemany(
                "INSERT INTO gl_category_map (source, account, categories_expense, category_lk, "
                "category_spt) VALUES (?,?,?,?,?)",
                [(r["source"], r["account"], r["categories_expense"], r["category_lk"],
                  r["category_spt"]) for r in rows])
            _on_synced(conn, rows)
            conn.execute(
                "INSERT INTO gl_category_sync_log (synced_at, synced_by, filename, content_hash, "
                "rows_smt, rows_etf) VALUES (?,?,?,?,?,?)",
                (datetime.now().isoformat(timespec="seconds"), user, filename, content_hash,
                 n_smt, n_etf))
            bump_version(conn)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    finally:
        conn.close()
    return {"changed": True, "rows_smt": n_smt, "rows_etf": n_etf}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd app && python -m pytest tests/test_mrc_category_map.py -q -p no:cacheprovider -W ignore`
Expected: PASS (semua test Task 1)

- [ ] **Step 5: Commit**

```bash
git add app/modules/management_report/category_map.py app/tests/test_mrc_category_map.py
git commit -m "feat(mr): account category mapping (M1) parsed from GL - MASTER COA sheet

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Daftar Kategori LK (M2) dan alias jenis PPh (M3)

**Files:**
- Modify: `app/modules/management_report/category_map.py`
- Test: `app/tests/test_mrc_category_map.py`

**Interfaces:**
- Consumes (Task 1): `ensure_schema`, `bump_version`, `get_conn`, `_on_synced` hook, `sync_categories`, `PPH_TYPES`.
- Produces:
  - `DEFAULT_LK` (dict nama → `(statement, kind, seq, needs_spt)`)
  - `get_lk_list() -> dict[str, dict]` urut `seq, name`; dict berisi `statement, kind, seq, label, needs_spt`
  - `update_lk(name, statement, kind, seq, label, needs_spt) -> None` (raise `KeyError` bila nama tidak ada, `ValueError` bila nilai tidak valid)
  - `alias_key(raw) -> str`
  - `get_pph_aliases() -> dict[str, str]` (kunci = `alias_key`)
  - `add_pph_alias(alias, pph_type) -> str` (mengembalikan kunci), `delete_pph_alias(key) -> None`
  - Setiap perubahan memanggil `bump_version`.

- [ ] **Step 1: Write the failing tests**

Tambahkan di akhir `app/tests/test_mrc_category_map.py`:

```python
# ---------- M2: Kategori LK ----------

def _rows_with(*lks):
    return cm.normalise_categories(sheet(*[row(f"6-{i}", None, "", lk, "BIAYA LAINNYA")
                                          for i, lk in enumerate(lks, 1)]))


def test_sync_seeds_lk_list_with_defaults_and_skips_tba_and_empty():
    cm.sync_categories("a", "u", _rows_with("Beban Operasional", "Kategori Baru", "tba"))
    lk = cm.get_lk_list()
    assert set(lk) == {"Beban Operasional", "Kategori Baru"}
    bo = lk["Beban Operasional"]
    assert (bo["statement"], bo["kind"], bo["needs_spt"]) == ("laba_rugi", "beban", 1)
    assert lk["Kategori Baru"]["statement"] == "" and lk["Kategori Baru"]["label"] == "Kategori Baru"


def test_known_defaults_cover_pnl_and_balance_sheet_categories():
    assert cm.DEFAULT_LK["Jasa Konsultasi & Advokasi"][:2] == ("laba_rugi", "pendapatan")
    assert cm.DEFAULT_LK["HUTANG PAJAK"][0] == "neraca"
    assert cm.DEFAULT_LK["MODAL SAHAM"][0] == "neraca"
    assert cm.DEFAULT_LK["Income Tax Expense"][:2] == ("laba_rugi", "beban")


def test_resync_keeps_manual_lk_edits():
    cm.sync_categories("a", "u", _rows_with("Kategori Baru"))
    cm.update_lk("Kategori Baru", statement="neraca", kind="lainnya", seq=50, label="Baru", needs_spt=0)
    cm.sync_categories("b", "u", _rows_with("Kategori Baru", "Beban Operasional"))
    lk = cm.get_lk_list()["Kategori Baru"]
    assert (lk["statement"], lk["kind"], lk["seq"], lk["label"]) == ("neraca", "lainnya", 50, "Baru")


def test_lk_list_is_ordered_by_seq_then_name():
    cm.sync_categories("a", "u", _rows_with("Beban Operasional", "HARGA POKOK PENJUALAN", "Zeta", "Alfa"))
    assert list(cm.get_lk_list())[:2] == ["HARGA POKOK PENJUALAN", "Beban Operasional"]
    assert list(cm.get_lk_list())[2:] == ["Alfa", "Zeta"]          # unknown ones share seq 999


def test_update_lk_validates_and_bumps_version():
    cm.sync_categories("a", "u", _rows_with("Kategori Baru"))
    v = cm.get_version()
    with pytest.raises(ValueError):
        cm.update_lk("Kategori Baru", statement="salah", kind="", seq=1, label="x", needs_spt=0)
    with pytest.raises(ValueError):
        cm.update_lk("Kategori Baru", statement="neraca", kind="salah", seq=1, label="x", needs_spt=0)
    with pytest.raises(ValueError):
        cm.update_lk("Kategori Baru", statement="neraca", kind="", seq="abc", label="x", needs_spt=0)
    with pytest.raises(KeyError):
        cm.update_lk("tidak ada", statement="neraca", kind="", seq=1, label="x", needs_spt=0)
    assert cm.get_version() == v                                     # nothing changed
    cm.update_lk("Kategori Baru", statement="neraca", kind="", seq=3, label=" Baru ", needs_spt=1)
    got = cm.get_lk_list()["Kategori Baru"]
    assert (got["statement"], got["seq"], got["label"], got["needs_spt"]) == ("neraca", 3, "Baru", 1)
    assert cm.get_version() == v + 1


# ---------- M3: alias jenis PPh ----------

def test_alias_key_ignores_case_spaces_and_dashes():
    assert cm.alias_key(" PPh 4 (2) ") == "pph4(2)"
    assert cm.alias_key("non-PPH") == "nonpph"
    assert cm.alias_key("Non  PPh") == "nonpph"


def test_default_aliases_cover_the_four_types():
    assert cm.get_pph_aliases() == {"pph21": "PPh 21", "pph23": "PPh 23",
                                    "pph4(2)": "PPh 4(2)", "nonpph": "Non PPh"}


def test_add_and_delete_alias_bump_version():
    v = cm.get_version()
    key = cm.add_pph_alias("PPh 4 ayat 2", "PPh 4(2)")
    assert key == "pph4ayat2" and cm.get_pph_aliases()[key] == "PPh 4(2)"
    assert cm.get_version() == v + 1
    cm.delete_pph_alias(key)
    assert key not in cm.get_pph_aliases() and cm.get_version() == v + 2


def test_alias_validation_and_default_alias_is_protected():
    for bad_alias, bad_type in (("", "PPh 21"), ("  ", "PPh 21"), ("x", "PPh 99")):
        with pytest.raises(ValueError):
            cm.add_pph_alias(bad_alias, bad_type)
    with pytest.raises(ValueError):
        cm.delete_pph_alias("pph21")
    assert "pph21" in cm.get_pph_aliases()
    with pytest.raises(KeyError):
        cm.delete_pph_alias("tidak-ada")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd app && python -m pytest tests/test_mrc_category_map.py -q -p no:cacheprovider -W ignore`
Expected: FAIL — `AttributeError: module ... has no attribute 'get_lk_list'` (dan sejenisnya)

- [ ] **Step 3: Write the implementation**

Di `category_map.py`, tambahkan `import re` di baris import teratas, tambahkan DDL dua tabel ke `_DDL`, ganti hook `_on_synced`, dan tambahkan fungsi di akhir.

Tambahkan ke string `_DDL` (sebelum penutup `"""`):

```sql
CREATE TABLE IF NOT EXISTS gl_category_lk (
    category_lk TEXT PRIMARY KEY,
    statement   TEXT NOT NULL DEFAULT '',
    kind        TEXT NOT NULL DEFAULT '',
    seq         INTEGER NOT NULL DEFAULT 999,
    label       TEXT NOT NULL DEFAULT '',
    needs_spt   INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS gl_pph_alias (
    alias    TEXT PRIMARY KEY,
    pph_type TEXT NOT NULL
);
```

Ubah `ensure_schema` agar menyemai alias baku:

```python
DEFAULT_ALIASES = {"pph21": "PPh 21", "pph23": "PPh 23", "pph4(2)": "PPh 4(2)", "nonpph": "Non PPh"}


def ensure_schema(conn) -> None:
    conn.executescript(_DDL)
    conn.execute("INSERT OR IGNORE INTO gl_mapping_meta (key, value) VALUES ('version', '1')")
    conn.executemany("INSERT OR IGNORE INTO gl_pph_alias (alias, pph_type) VALUES (?, ?)",
                     list(DEFAULT_ALIASES.items()))
    conn.commit()
```

Ganti hook `_on_synced` dan tambahkan sisa fungsi:

```python
STATEMENTS = ("neraca", "laba_rugi")
KINDS = ("pendapatan", "beban", "lainnya")

# name -> (statement, kind, seq, needs_spt); unknown names are seeded with statement '' and seq 999
DEFAULT_LK = {
    "KAS DAN SETARA KAS": ("neraca", "lainnya", 1, 0),
    "PIUTANG LAIN-LAIN PIHAK KETIGA": ("neraca", "lainnya", 2, 0),
    "PIUTANG LAIN-LAIN PIHAK BERELASI": ("neraca", "lainnya", 3, 0),
    "UANG MUKA PEMBELIAN": ("neraca", "lainnya", 4, 0),
    "AKTIVA LANCAR LAINNYA": ("neraca", "lainnya", 5, 0),
    "AKTIVA TETAP LAINNYA": ("neraca", "lainnya", 6, 0),
    "AKUMULASI PENYUSUTAN": ("neraca", "lainnya", 7, 0),
    "AKTIVA TIDAK LANCAR LAINNYA": ("neraca", "lainnya", 8, 0),
    "HUTANG USAHA PIHAK KETIGA": ("neraca", "lainnya", 9, 0),
    "HUTANG PAJAK": ("neraca", "lainnya", 10, 0),
    "MODAL SAHAM": ("neraca", "lainnya", 11, 0),
    "Laba (Rugi) ditahan": ("neraca", "lainnya", 12, 0),
    "Jasa Konsultasi & Advokasi": ("laba_rugi", "pendapatan", 1, 0),
    "HARGA POKOK PENJUALAN": ("laba_rugi", "beban", 2, 1),
    "Beban Operasional": ("laba_rugi", "beban", 3, 1),
    "Pendapatan (Beban) Lainnya": ("laba_rugi", "lainnya", 4, 1),
    "Bunga Jasa Giro": ("laba_rugi", "lainnya", 5, 0),
    "Income Tax Expense": ("laba_rugi", "beban", 6, 0),
}


def _on_synced(conn, rows) -> None:
    """Seed the Kategori LK list with every category seen in the sheet; never overwrite edits."""
    for name in sorted({r["category_lk"] for r in rows if not is_unmapped(r["category_lk"])}):
        statement, kind, seq, needs_spt = DEFAULT_LK.get(name, ("", "", 999, 0))
        conn.execute("INSERT OR IGNORE INTO gl_category_lk (category_lk, statement, kind, seq, label, "
                     "needs_spt) VALUES (?,?,?,?,?,?)", (name, statement, kind, seq, name, needs_spt))


def get_lk_list() -> dict:
    conn = get_conn()
    try:
        ensure_schema(conn)
        return {r["category_lk"]: {"statement": r["statement"], "kind": r["kind"], "seq": r["seq"],
                                   "label": r["label"], "needs_spt": r["needs_spt"]}
                for r in conn.execute("SELECT * FROM gl_category_lk ORDER BY seq, category_lk")}
    finally:
        conn.close()


def update_lk(name, statement, kind, seq, label, needs_spt) -> None:
    if statement not in ("", *STATEMENTS):
        raise ValueError("Jenis laporan harus kosong, 'neraca', atau 'laba_rugi'.")
    if kind not in ("", *KINDS):
        raise ValueError("Sifat harus kosong, 'pendapatan', 'beban', atau 'lainnya'.")
    try:
        seq = int(seq)
    except (TypeError, ValueError):
        raise ValueError("Urutan harus berupa angka.") from None
    conn = get_conn()
    try:
        ensure_schema(conn)
        if not conn.execute("SELECT 1 FROM gl_category_lk WHERE category_lk=?", (name,)).fetchone():
            raise KeyError(name)
        conn.execute("UPDATE gl_category_lk SET statement=?, kind=?, seq=?, label=?, needs_spt=? "
                     "WHERE category_lk=?",
                     (statement, kind, seq, (label or "").strip() or name, 1 if needs_spt else 0, name))
        bump_version(conn)
        conn.commit()
    finally:
        conn.close()


def alias_key(raw) -> str:
    return re.sub(r"[\s\-]+", "", str(raw or "").strip().lower())


def get_pph_aliases() -> dict:
    conn = get_conn()
    try:
        ensure_schema(conn)
        return {r["alias"]: r["pph_type"] for r in conn.execute(
            "SELECT alias, pph_type FROM gl_pph_alias ORDER BY alias")}
    finally:
        conn.close()


def add_pph_alias(alias, pph_type) -> str:
    key = alias_key(alias)
    if not key:
        raise ValueError("Alias tidak boleh kosong.")
    if pph_type not in PPH_TYPES:
        raise ValueError("Jenis PPh harus salah satu dari: " + ", ".join(PPH_TYPES) + ".")
    conn = get_conn()
    try:
        ensure_schema(conn)
        conn.execute("INSERT OR REPLACE INTO gl_pph_alias (alias, pph_type) VALUES (?, ?)", (key, pph_type))
        bump_version(conn)
        conn.commit()
    finally:
        conn.close()
    return key


def delete_pph_alias(key) -> None:
    if key in DEFAULT_ALIASES:
        raise ValueError("Alias baku tidak bisa dihapus.")
    conn = get_conn()
    try:
        ensure_schema(conn)
        cur = conn.execute("DELETE FROM gl_pph_alias WHERE alias=?", (key,))
        if cur.rowcount == 0:
            raise KeyError(key)
        bump_version(conn)
        conn.commit()
    finally:
        conn.close()
```

Pastikan `_on_synced` lama (yang kosong) dihapus agar tidak ada dua definisi.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd app && python -m pytest tests/test_mrc_category_map.py -q -p no:cacheprovider -W ignore`
Expected: PASS (semua test Task 1 dan Task 2)

- [ ] **Step 5: Commit**

```bash
git add app/modules/management_report/category_map.py app/tests/test_mrc_category_map.py
git commit -m "feat(mr): Kategori LK list (M2) and PPh type aliases (M3) with mapping version

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Pencarian akun dan daftar akun belum dipetakan

**Files:**
- Modify: `app/modules/general_ledger/service.py` (tambah di akhir file)
- Modify: `app/modules/management_report/category_map.py`
- Test: `app/tests/test_gl_service.py`, `app/tests/test_mrc_category_map.py`

**Interfaces:**
- Consumes: `general_ledger.service.ENTITIES`, `get_conn`, tabel GL; `category_map.get_category_map`, `get_lk_list`, `is_unmapped`; `coa_map._page(rows, page, per_page)`.
- Produces:
  - `general_ledger.service.account_totals(entity: str, year: int) -> list[dict]` — `{"account": str, "n": int, "amount": float}` urut akun
  - `category_map.search_accounts(source=None, q=None, page=1, per_page=100) -> dict` (bentuk `{"rows","total","page","pages","per_page"}`)
  - `category_map.unmapped_accounts(year: int) -> list[dict]` — `{"source","account","rows","amount","reason"}` urut `abs(amount)` menurun

- [ ] **Step 1: Write the failing tests**

Tambahkan di akhir `app/tests/test_gl_service.py`:

```python
def test_account_totals_groups_by_account_and_year():
    log = dict(synced_by="u", filename="f", content_hash="h", rows_before=0, rows_after=1,
               total_debit=0, total_credit=0, dropped=0, summary={})
    svc.replace_year("smt", 2025, [mkrow(acc_statutory="6-1", tgl="2025-02-02", debit_credit=9.0)], log)
    svc.replace_year("smt", 2026, [
        mkrow(acc_statutory="6-1", tgl="2026-01-02", debit_credit=10.0),
        mkrow(acc_statutory="6-1", tgl="2026-01-03", debit_credit=-4.0),
        mkrow(acc_statutory="6-2", tgl="2026-01-04", debit_credit=1.0)], log)
    assert svc.account_totals("smt", 2026) == [{"account": "6-1", "n": 2, "amount": 6.0},
                                               {"account": "6-2", "n": 1, "amount": 1.0}]
    assert svc.account_totals("smt", 2025) == [{"account": "6-1", "n": 1, "amount": 9.0}]
    assert svc.account_totals("etf", 2026) == []
```

Tambahkan di akhir `app/tests/test_mrc_category_map.py`:

```python
# ---------- search + unmapped ----------

from modules.general_ledger import service as gl_service
from tests.test_gl_sync import mkrow

GL_LOG = dict(synced_by="u", filename="f", content_hash="h", rows_before=0, rows_after=1,
              total_debit=0, total_credit=0, dropped=0, summary={})


def seed_gl(entity, *accounts):
    rows = [mkrow(acc_statutory=a, tgl="2026-01-02", debit_credit=amt) for a, amt in accounts]
    gl_service.replace_year(entity, 2026, rows, GL_LOG)


def test_search_accounts_filters_by_source_and_text_and_pages():
    cm.sync_categories("a", "u", cm.normalise_categories(sheet(
        row("6-1810", "6-2150", "Office", "Beban Operasional", "BIAYA LAINNYA"),
        row("6-1720", None, "Gift", "HARGA POKOK PENJUALAN", "BIAYA SEWA"))))
    assert cm.search_accounts()["total"] == 3
    assert cm.search_accounts("ETF")["total"] == 1
    assert [r["account"] for r in cm.search_accounts(None, "gift")["rows"]] == ["6-1720"]
    assert cm.search_accounts(None, "biaya sewa")["rows"][0]["category_spt"] == "BIAYA SEWA"
    assert cm.search_accounts(None, "", page=99)["page"] == 1


def test_unmapped_accounts_reasons_and_ordering():
    cm.sync_categories("a", "u", cm.normalise_categories(sheet(
        row("6-ok", None, "", "Beban Operasional", "BIAYA LAINNYA"),
        row("6-tba", None, "", "TBA", "TBA"),
        row("6-nospt", None, "", "HARGA POKOK PENJUALAN", "TBA"),
        row("6-noreport", None, "", "Kategori Baru", "BIAYA LAINNYA"),
        row("1-bank", None, "", "KAS DAN SETARA KAS", ""))))
    seed_gl("smt", ("6-ok", 5.0), ("6-tba", 10.0), ("6-nospt", -30.0), ("6-noreport", 2.0),
            ("1-bank", 100.0), ("9-missing", 1.0))
    got = {u["account"]: u for u in cm.unmapped_accounts(2026)}
    assert set(got) == {"6-tba", "6-nospt", "6-noreport", "9-missing"}
    assert got["6-tba"]["reason"] == "Category LK kosong / TBA"
    assert got["6-nospt"]["reason"] == "Category SPT kosong / TBA"
    assert got["6-noreport"]["reason"] == "Category LK belum diatur jenis laporannya"
    assert got["9-missing"]["reason"] == "Akun tidak ada di pemetaan kategori"
    assert got["6-nospt"]["source"] == "SMT" and got["6-nospt"]["rows"] == 1
    assert [u["account"] for u in cm.unmapped_accounts(2026)][0] == "6-nospt"      # biggest |amount| first


def test_unmapped_accounts_is_empty_for_other_years_and_when_everything_is_mapped():
    cm.sync_categories("a", "u", cm.normalise_categories(sheet(
        row("6-ok", None, "", "Beban Operasional", "BIAYA LAINNYA"))))
    seed_gl("smt", ("6-ok", 5.0))
    assert cm.unmapped_accounts(2026) == [] and cm.unmapped_accounts(2025) == []


def test_unmapped_accounts_keeps_smt_and_etf_apart():
    cm.sync_categories("a", "u", cm.normalise_categories(sheet(row("6-x", None, "", "Beban Operasional", "BIAYA LAINNYA"))))
    seed_gl("etf", ("6-x", 5.0))                                   # only SMT knows 6-x
    assert [(u["source"], u["account"]) for u in cm.unmapped_accounts(2026)] == [("ETF", "6-x")]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd app && python -m pytest tests/test_gl_service.py::test_account_totals_groups_by_account_and_year tests/test_mrc_category_map.py -q -p no:cacheprovider -W ignore`
Expected: FAIL — `AttributeError: ... 'account_totals'` / `'search_accounts'`

- [ ] **Step 3: Write the implementation**

Tambahkan di akhir `app/modules/general_ledger/service.py`:

```python
def account_totals(entity, year) -> list:
    """Per statutory account: row count and net amount (debit_credit) for one year."""
    table = ENTITIES[entity]["table"]
    conn = get_conn()
    try:
        ensure_schema(conn)
        return [{"account": r[0], "n": r[1], "amount": r[2]} for r in conn.execute(
            f"SELECT acc_statutory, COUNT(*), COALESCE(SUM(debit_credit), 0) FROM {table} "
            f"WHERE substr(tgl,1,4) = ? GROUP BY acc_statutory ORDER BY acc_statutory",
            (str(int(year)),))]
    finally:
        conn.close()
```

Di `category_map.py`, ubah import menjadi:

```python
from modules.general_ledger import service as gl_service
from modules.management_report.coa_map import CoaParseError, _cell, _page, _read_sheets, _text
```

dan tambahkan di akhir file:

```python
def search_accounts(source=None, q=None, page=1, per_page=100) -> dict:
    needle = (q or "").strip().lower()
    rows = []
    for (src, account), v in sorted(get_category_map().items()):
        if source in ("SMT", "ETF") and src != source:
            continue
        if needle and not any(needle in f.lower() for f in
                              (account, v["categories_expense"], v["category_lk"], v["category_spt"])):
            continue
        rows.append({"source": src, "account": account, **v})
    return _page(rows, page, per_page)


_SOURCES = (("smt", "SMT"), ("etf", "ETF"))


def unmapped_accounts(year) -> list:
    """GL accounts of `year` whose category mapping is missing or incomplete, biggest amount first."""
    cmap, lk = get_category_map(), get_lk_list()
    out = []
    for entity, source in _SOURCES:
        for t in gl_service.account_totals(entity, year):
            entry = cmap.get((source, t["account"]))
            reason = ""
            if entry is None:
                reason = "Akun tidak ada di pemetaan kategori"
            elif is_unmapped(entry["category_lk"]):
                reason = "Category LK kosong / TBA"
            else:
                meta = lk.get(entry["category_lk"])
                if meta is None or not meta["statement"]:
                    reason = "Category LK belum diatur jenis laporannya"
                elif meta["needs_spt"] and is_unmapped(entry["category_spt"]):
                    reason = "Category SPT kosong / TBA"
            if reason:
                out.append({"source": source, "account": t["account"], "rows": t["n"],
                            "amount": t["amount"], "reason": reason})
    out.sort(key=lambda u: -abs(u["amount"]))
    return out
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd app && python -m pytest tests/test_gl_service.py tests/test_mrc_category_map.py -q -p no:cacheprovider -W ignore`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/modules/general_ledger/service.py app/modules/management_report/category_map.py app/tests/test_gl_service.py app/tests/test_mrc_category_map.py
git commit -m "feat(mr): category account search and unmapped-account detection against GL

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Route, halaman, dan tab Kategori SPT

**Files:**
- Modify: `app/modules/management_report/routes.py`
- Create: `app/templates/management_report/kategori.html`
- Modify: `app/templates/management_report/_linktabs.html`
- Test: `app/tests/test_mrc_category_routes.py`

**Interfaces:**
- Consumes (Task 1–3): semua fungsi `category_map`; `gl_service.latest_year(entity)`; helper route yang sudah ada `_ctx()`, `_to_int`, `_page_arg()`; dekorator `jwt_html_required`, `json_admin_required`.
- Produces (HTTP):
  - `GET /management-report/pemetaan/kategori?view=akun|lk|pph&source=&q=&page=&year=` → 200 HTML
  - `POST /management-report/pemetaan/kategori/sync` (multipart `file`) → JSON `{ok, pesan, changed, rows_smt, rows_etf}`
  - `POST /management-report/pemetaan/kategori/lk` (JSON `{name, statement, kind, seq, label, needs_spt}`) → `{ok, pesan}`
  - `POST /management-report/pemetaan/kategori/pph` (JSON `{alias, pph_type}`) → `{ok, pesan, alias}`
  - `DELETE /management-report/pemetaan/kategori/pph/<alias>` → `{ok, pesan}`
  - Elemen HTML ber-id: `mr-cat-sync-btn` (hanya admin), `mr-cat-unmapped`, `mr-cat-table`, `mr-lk-table`, `mr-pph-table`.

- [ ] **Step 1: Write the failing tests**

Create `app/tests/test_mrc_category_routes.py`:

```python
# tests/test_mrc_category_routes.py
import io
import re

import bcrypt

import database
from modules.general_ledger import service as gl_service
from modules.management_report import category_map as cm
from tests.test_gl_sync import mkrow
from tests.test_mrc_category_map import GL_LOG, row, sheet
from tests.test_mrc_routes import login

URL = "/management-report/pemetaan/kategori"


def rows_of(html, table_id):
    block = html.split(f'id="{table_id}"', 1)[1].split("</table>", 1)[0]
    return [[re.sub(r"<.*?>", "", c).strip() for c in re.findall(r"<td[^>]*>(.*?)</td>", r, re.S)]
            for r in re.findall(r"<tr[^>]*>(.*?)</tr>", block, re.S) if "<td" in r]


def seed_map():
    cm.sync_categories("GL - MASTER.xlsb", "admin", cm.normalise_categories(sheet(
        row("6-1810", None, "Office", "Beban Operasional", "BIAYA LAINNYA"),
        row("6-tba", None, "", "TBA", "TBA"))))


def post_sync(client, monkeypatch, rows, name="GL - MASTER.xlsb"):
    monkeypatch.setattr(cm, "read_category_sheet", lambda f: rows)
    return client.post(URL + "/sync", data={"file": (io.BytesIO(b"x"), name)},
                       content_type="multipart/form-data")


def make_requester(client):
    pw = bcrypt.hashpw(b"Req@12345", bcrypt.gensalt(4)).decode()
    conn = database.get_conn()
    conn.execute("INSERT INTO users (username, password_hash, role, must_change_pw) "
                 "VALUES (?, ?, 'requester', 0)", ("req1", pw))
    conn.commit()
    conn.close()
    client.post("/auth/login", json={"username": "req1", "password": "Req@12345"})
    client.post("/select-company", data={"company_id": "2"})


def test_page_requires_login(client):
    r = client.get(URL)
    assert r.status_code == 302 and "/auth/login" in r.headers["Location"]


def test_empty_state_and_tab(client):
    login(client)
    html = client.get(URL).data.decode()
    assert "Kategori SPT" in html and "belum pernah disync" in html.lower()
    assert 'id="mr-cat-sync-btn"' in html


def test_tab_is_present_on_the_existing_pemetaan_page(client):
    login(client)
    assert "/management-report/pemetaan/kategori" in client.get("/management-report/pemetaan").data.decode()


def test_sync_success_then_unchanged(client, monkeypatch):
    login(client)
    rows = cm.normalise_categories(sheet(row("6-1810", None, "Office", "Beban Operasional", "BIAYA LAINNYA")))
    j = post_sync(client, monkeypatch, rows).get_json()
    assert j["ok"] and j["changed"] and "SMT 1 akun" in j["pesan"]
    again = post_sync(client, monkeypatch, rows).get_json()
    assert again["ok"] and again["changed"] is False and "Sudah sinkron" in again["pesan"]
    assert rows_of(client.get(URL).data.decode(), "mr-cat-table") == [
        ["SMT", "6-1810", "Office", "Beban Operasional", "BIAYA LAINNYA"]]


def test_sync_rejects_non_xlsb_missing_file_and_parse_errors_without_touching_data(client, monkeypatch):
    login(client)
    seed_map()
    assert client.post(URL + "/sync", data={}, content_type="multipart/form-data").status_code == 400
    r = client.post(URL + "/sync", data={"file": (io.BytesIO(b"x"), "a.xlsx")},
                    content_type="multipart/form-data")
    assert r.status_code == 400 and "xlsb" in r.get_json()["pesan"]

    from modules.management_report.coa_map import CoaParseError

    def boom(f):
        raise CoaParseError("Sheet 'COA' tidak ditemukan di file.")
    monkeypatch.setattr(cm, "read_category_sheet", boom)
    r = client.post(URL + "/sync", data={"file": (io.BytesIO(b"x"), "a.xlsb")},
                    content_type="multipart/form-data")
    assert r.status_code == 400 and "tidak ditemukan" in r.get_json()["pesan"]
    assert ("SMT", "6-1810") in cm.get_category_map()
    monkeypatch.setattr(cm, "read_category_sheet", lambda f: [])
    r = client.post(URL + "/sync", data={"file": (io.BytesIO(b"x"), "a.xlsb")},
                    content_type="multipart/form-data")
    assert r.status_code == 400


def test_non_admin_can_view_but_not_change_anything(client, monkeypatch):
    seed_map()
    make_requester(client)
    html = client.get(URL).data.decode()
    assert client.get(URL).status_code == 200 and 'id="mr-cat-sync-btn"' not in html
    r = post_sync(client, monkeypatch, [])
    assert r.status_code == 403
    assert client.post(URL + "/lk", json={"name": "Beban Operasional", "statement": "neraca"}).status_code == 403
    assert client.post(URL + "/pph", json={"alias": "x", "pph_type": "PPh 21"}).status_code == 403
    assert client.delete(URL + "/pph/pph21").status_code == 403
    assert cm.get_lk_list()["Beban Operasional"]["statement"] == "laba_rugi"


def test_lk_view_lists_and_updates(client):
    login(client)
    seed_map()
    html = client.get(URL + "?view=lk").data.decode()
    assert [r[0] for r in rows_of(html, "mr-lk-table")] == ["Beban Operasional"]
    r = client.post(URL + "/lk", json={"name": "Beban Operasional", "statement": "neraca", "kind": "lainnya",
                                       "seq": 7, "label": "BO", "needs_spt": False})
    assert r.status_code == 200 and r.get_json()["ok"]
    assert cm.get_lk_list()["Beban Operasional"]["label"] == "BO"
    bad = client.post(URL + "/lk", json={"name": "Beban Operasional", "statement": "salah"})
    assert bad.status_code == 400 and not bad.get_json()["ok"]
    assert client.post(URL + "/lk", json={"name": "tidak ada", "statement": "neraca"}).status_code == 404


def test_pph_alias_add_list_and_delete(client):
    login(client)
    html = client.get(URL + "?view=pph").data.decode()
    assert {r[0] for r in rows_of(html, "mr-pph-table")} >= {"pph21", "pph23", "pph4(2)", "nonpph"}
    r = client.post(URL + "/pph", json={"alias": "PPh 4 ayat 2", "pph_type": "PPh 4(2)"})
    assert r.status_code == 200 and r.get_json()["alias"] == "pph4ayat2"
    assert client.post(URL + "/pph", json={"alias": "", "pph_type": "PPh 21"}).status_code == 400
    assert client.delete(URL + "/pph/pph4ayat2").status_code == 200
    assert client.delete(URL + "/pph/pph21").status_code == 400
    assert client.delete(URL + "/pph/tidak-ada").status_code == 404


def test_unmapped_panel_lists_gl_accounts_without_mapping(client):
    login(client)
    seed_map()
    gl_service.replace_year("smt", 2026, [
        mkrow(acc_statutory="6-1810", tgl="2026-01-02", debit_credit=1.0),
        mkrow(acc_statutory="6-tba", tgl="2026-01-02", debit_credit=2.0),
        mkrow(acc_statutory="9-none", tgl="2026-01-02", debit_credit=3.0)], GL_LOG)
    html = client.get(URL).data.decode()
    accounts = [r[1] for r in rows_of(html, "mr-cat-unmapped")]
    assert accounts == ["9-none", "6-tba"]                       # biggest amount first, mapped one absent
    assert "Akun tidak ada di pemetaan kategori" in html
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd app && python -m pytest tests/test_mrc_category_routes.py -q -p no:cacheprovider -W ignore`
Expected: FAIL — status 404 untuk `/management-report/pemetaan/kategori`

- [ ] **Step 3: Write the implementation**

Di `app/modules/management_report/routes.py`, tambahkan import (di blok import `modules.management_report`):

```python
from modules.general_ledger import service as gl_service
from modules.management_report import category_map
```

Tambahkan route di akhir file:

```python
@bp.route("/pemetaan/kategori")
@jwt_html_required
def category_page():
    view = request.args.get("view") if request.args.get("view") in ("akun", "lk", "pph") else "akun"
    source = request.args.get("source") if request.args.get("source") in ("SMT", "ETF") else ""
    q = (request.args.get("q") or "").strip()
    page = max(1, _page_arg())
    year = _to_int(request.args.get("year")) or gl_service.latest_year("smt") or date.today().year
    last_cat = category_map.last_sync()
    return render_template(
        "management_report/kategori.html",
        active_tab="kategori", view=view, source=source, q=q, year=year,
        data=category_map.search_accounts(source or None, q, page) if view == "akun" else None,
        lk_list=category_map.get_lk_list(), aliases=category_map.get_pph_aliases(),
        default_aliases=category_map.DEFAULT_ALIASES, pph_types=category_map.PPH_TYPES,
        statements=category_map.STATEMENTS, kinds=category_map.KINDS,
        unmapped=category_map.unmapped_accounts(year) if last_cat else [], limit=50,
        last_cat=last_cat, history=category_map.list_syncs(10), version=category_map.get_version(),
        active_page="management_report", use_unified_header=True,
        **_ctx(),
    )


@bp.route("/pemetaan/kategori/sync", methods=["POST"])
@json_admin_required
def category_sync():
    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify({"ok": False, "pesan": "File belum dipilih."}), 400
    if not f.filename.lower().endswith(".xlsb"):
        return jsonify({"ok": False, "pesan": "File harus berformat .xlsb."}), 400
    try:
        rows = category_map.read_category_sheet(io.BytesIO(f.read()))
        if not rows:
            raise coa_map.CoaParseError("Tidak ada kategori akun yang valid di sheet COA.")
    except coa_map.CoaParseError as e:
        return jsonify({"ok": False, "pesan": str(e)}), 400
    try:
        out = category_map.sync_categories(f.filename, get_jwt().get("username", ""), rows)
    except Exception as e:
        return jsonify({"ok": False, "pesan": f"Sync gagal, kategori lama tidak berubah: {e}"}), 500
    counts = f"SMT {out['rows_smt']} akun, ETF {out['rows_etf']} akun"
    pesan = (f"Sudah sinkron: kategori tidak berubah ({counts})." if not out["changed"]
             else f"Sync kategori selesai: {counts}.")
    return jsonify({"ok": True, "pesan": pesan, **out})


@bp.route("/pemetaan/kategori/lk", methods=["POST"])
@json_admin_required
def category_lk_update():
    d = request.get_json(silent=True) or {}
    try:
        category_map.update_lk(d.get("name", ""), d.get("statement", ""), d.get("kind", ""),
                               d.get("seq", 999), d.get("label", ""), bool(d.get("needs_spt")))
    except KeyError:
        return jsonify({"ok": False, "pesan": "Kategori LK tidak ditemukan."}), 404
    except ValueError as e:
        return jsonify({"ok": False, "pesan": str(e)}), 400
    return jsonify({"ok": True, "pesan": "Kategori LK disimpan."})


@bp.route("/pemetaan/kategori/pph", methods=["POST"])
@json_admin_required
def category_pph_add():
    d = request.get_json(silent=True) or {}
    try:
        key = category_map.add_pph_alias(d.get("alias", ""), d.get("pph_type", ""))
    except ValueError as e:
        return jsonify({"ok": False, "pesan": str(e)}), 400
    return jsonify({"ok": True, "pesan": "Alias disimpan.", "alias": key})


@bp.route("/pemetaan/kategori/pph/<alias>", methods=["DELETE"])
@json_admin_required
def category_pph_delete(alias):
    try:
        category_map.delete_pph_alias(alias)
    except KeyError:
        return jsonify({"ok": False, "pesan": "Alias tidak ditemukan."}), 404
    except ValueError as e:
        return jsonify({"ok": False, "pesan": str(e)}), 400
    return jsonify({"ok": True, "pesan": "Alias dihapus."})
```

Di `_linktabs.html`, tambahkan setelah tab Pemetaan:

```html
  <a class="mr-linktab{{ ' active' if active_tab == 'kategori' else '' }}" href="{{ url_for('management_report.category_page') }}">Kategori SPT</a>
```

Create `app/templates/management_report/kategori.html`:

```html
{% extends "base.html" %}
{% block title %}Management Report - Kategori SPT{% endblock %}

{% block head %}
<link rel="stylesheet" href="{{ url_for('static', filename='css/mr_combine.css') }}">
<style>
.mc-table { border-collapse:collapse; width:100%; font-size:.8125rem; white-space:nowrap; }
.mc-table th, .mc-table td { padding:.3rem .5rem; border-bottom:1px solid var(--sl-200); }
.mc-table th { text-align:left; background:var(--sl-50); position:sticky; top:0; }
.mc-table .num { text-align:right; font-variant-numeric:tabular-nums; }
.mc-wrap { overflow:auto; max-height:65vh; }
.mc-muted { color:var(--sl-500); font-size:.8125rem; }
.mc-filter { display:flex; gap:.5rem; flex-wrap:wrap; align-items:flex-end; margin-bottom:.75rem; }
.mc-filter label { display:flex; flex-direction:column; font-size:.75rem; }
.mc-pager { display:flex; align-items:center; gap:.75rem; margin:.6rem 0; }
.mc-warn { margin-bottom:.75rem; padding:.7rem .9rem; font-size:.8125rem; border:1px solid var(--danger); border-radius:8px; }
.mc-section { margin-bottom:1rem; }
.mc-switch { display:inline-block; padding:.3rem .8rem; border:1px solid var(--sl-200); border-radius:999px; font-size:.8rem; text-decoration:none; margin-right:.35rem; }
.mc-switch.active { font-weight:700; border-color:var(--accent); }
.mc-table input[type=text], .mc-table input[type=number], .mc-table select { font-size:.8rem; padding:.15rem .3rem; }
</style>
{% endblock %}

{% block module_tabs %}
{% include "management_report/_linktabs.html" %}
{% endblock %}

{% block content %}
<section class="card mc-section">
  <strong>Kategori akun untuk SPT Badan</strong>
  <div class="mc-muted" style="margin:.25rem 0">
    Versi pemetaan: <b>{{ version }}</b> ·
    {% if last_cat %}Terakhir sync: {{ last_cat.synced_at }} · {{ last_cat.synced_by }} · {{ last_cat.filename }} · SMT {{ last_cat.rows_smt }} akun, ETF {{ last_cat.rows_etf }} akun
    {% else %}Kategori belum pernah disync.{% endif %}
  </div>
  {% if can_manage %}
  <div style="margin:.5rem 0">
    <input type="file" id="mr-cat-file" accept=".xlsb">
    <button class="btn btn-primary btn-sm" id="mr-cat-sync-btn" onclick="mrSyncCategories()">Sync kategori dari GL - MASTER</button>
    <span id="mr-cat-msg" class="mc-muted"></span>
  </div>
  <div class="mc-muted">Pilih file <code>GL - MASTER.xlsb</code>; hanya sheet <b>COA</b> yang dibaca (kolom Category LK, Category SPT, dan CATEGORIES EXPENSE).</div>
  {% endif %}
</section>

{% if last_cat %}
<section class="card mc-section">
  <strong>Akun belum dipetakan (GL {{ year }})</strong>
  {% if unmapped %}
  <div class="mc-warn">{{ unmapped | length }} akun di GL {{ year }} belum lengkap pemetaannya. SPT Badan akan memblokir sampai ini kosong.</div>
  <div class="mc-wrap" style="max-height:40vh">
  <table class="mc-table" id="mr-cat-unmapped">
    <thead><tr><th>Sumber</th><th>Akun</th><th class="num">Baris</th><th class="num">Jumlah (debit − credit)</th><th>Alasan</th></tr></thead>
    <tbody>
    {% for u in unmapped[:limit] %}
    <tr><td>{{ u.source }}</td><td>{{ u.account }}</td><td class="num">{{ u.rows }}</td><td class="num">{{ '{:,.0f}'.format(u.amount).replace(',', '.') }}</td><td>{{ u.reason }}</td></tr>
    {% endfor %}
    </tbody>
  </table>
  </div>
  {% if unmapped | length > limit %}<div class="mc-muted">… dan {{ unmapped | length - limit }} lainnya</div>{% endif %}
  {% else %}
  <div class="mc-muted">Semua akun bersaldo di GL {{ year }} sudah terpetakan.</div>
  {% endif %}
</section>
{% endif %}

<section class="card mc-section">
  <div style="margin:.25rem 0 .5rem">
    <a class="mc-switch{{ ' active' if view == 'akun' else '' }}" href="?view=akun">Akun → Kategori</a>
    <a class="mc-switch{{ ' active' if view == 'lk' else '' }}" href="?view=lk">Kategori LK</a>
    <a class="mc-switch{{ ' active' if view == 'pph' else '' }}" href="?view=pph">Jenis PPh</a>
  </div>

  {% if view == 'akun' %}
  <form class="mc-filter" method="get">
    <input type="hidden" name="view" value="akun">
    <label>Sumber
      <select name="source"><option value="">Semua</option>{% for s in ('SMT', 'ETF') %}<option value="{{ s }}"{{ ' selected' if s == source else '' }}>{{ s }}</option>{% endfor %}</select>
    </label>
    <label>Cari<input type="text" name="q" value="{{ q }}" placeholder="akun / kategori"></label>
    <button class="btn btn-primary btn-sm" type="submit">Terapkan</button>
  </form>
  <div class="mc-muted" style="margin-bottom:.5rem">{{ data.total }} baris</div>
  <div class="mc-wrap">
  <table class="mc-table" id="mr-cat-table">
    <thead><tr><th>Sumber</th><th>Akun</th><th>Categories Expense</th><th>Category LK</th><th>Category SPT</th></tr></thead>
    <tbody>
    {% for r in data.rows %}
    <tr><td>{{ r.source }}</td><td>{{ r.account }}</td><td>{{ r.categories_expense }}</td><td>{{ r.category_lk }}</td><td>{{ r.category_spt }}</td></tr>
    {% else %}
    <tr><td colspan="5" class="mc-muted">Tidak ada baris yang cocok.</td></tr>
    {% endfor %}
    </tbody>
  </table>
  </div>
  <div class="mc-pager">
    {% set qs = request.args.to_dict() %}{% set _ = qs.pop('page', none) %}
    {% if data.page > 1 %}<a class="btn btn-sm" href="?{{ (qs | urlencode) ~ ('&' if qs else '') }}page={{ data.page - 1 }}">&laquo; Sebelumnya</a>{% endif %}
    <span class="mc-muted">Halaman {{ data.page }} dari {{ data.pages }}</span>
    {% if data.page < data.pages %}<a class="btn btn-sm" href="?{{ (qs | urlencode) ~ ('&' if qs else '') }}page={{ data.page + 1 }}">Berikutnya &raquo;</a>{% endif %}
  </div>

  {% elif view == 'lk' %}
  <div class="mc-muted" style="margin-bottom:.5rem">Daftar diisi otomatis dari sync; jenis laporan, sifat, urutan, label, dan kewajiban Category SPT diatur di sini. Kategori tanpa jenis laporan memblokir SPT Badan.</div>
  <div class="mc-wrap">
  <table class="mc-table" id="mr-lk-table">
    <thead><tr><th>Category LK</th><th>Jenis laporan</th><th>Sifat</th><th class="num">Urutan</th><th>Label</th><th>Wajib SPT</th><th></th></tr></thead>
    <tbody>
    {% for name, m in lk_list.items() %}
    <tr data-name="{{ name }}">
      <td>{{ name }}</td>
      <td>{% if can_manage %}<select class="lk-statement"><option value=""></option>{% for s in statements %}<option value="{{ s }}"{{ ' selected' if s == m.statement else '' }}>{{ s }}</option>{% endfor %}</select>{% else %}{{ m.statement }}{% endif %}</td>
      <td>{% if can_manage %}<select class="lk-kind"><option value=""></option>{% for k in kinds %}<option value="{{ k }}"{{ ' selected' if k == m.kind else '' }}>{{ k }}</option>{% endfor %}</select>{% else %}{{ m.kind }}{% endif %}</td>
      <td class="num">{% if can_manage %}<input type="number" class="lk-seq" value="{{ m.seq }}" style="width:5rem">{% else %}{{ m.seq }}{% endif %}</td>
      <td>{% if can_manage %}<input type="text" class="lk-label" value="{{ m.label }}">{% else %}{{ m.label }}{% endif %}</td>
      <td>{% if can_manage %}<input type="checkbox" class="lk-needs"{{ ' checked' if m.needs_spt else '' }}>{% else %}{{ 'ya' if m.needs_spt else '' }}{% endif %}</td>
      <td>{% if can_manage %}<button class="btn btn-sm" onclick="mrSaveLk(this)">Simpan</button> <span class="mc-muted lk-msg"></span>{% endif %}</td>
    </tr>
    {% else %}
    <tr><td colspan="7" class="mc-muted">Belum ada kategori. Sync kategori dari GL - MASTER dulu.</td></tr>
    {% endfor %}
    </tbody>
  </table>
  </div>

  {% else %}
  <div class="mc-muted" style="margin-bottom:.5rem">Nilai kolom PPh di GL dicocokkan ke jenis baku lewat alias (huruf besar/kecil, spasi, dan tanda hubung diabaikan). Alias yang belum dikenal muncul sebagai pengecualian di SPT Badan.</div>
  <div class="mc-wrap" style="max-height:none">
  <table class="mc-table" id="mr-pph-table">
    <thead><tr><th>Alias</th><th>Jenis PPh</th><th></th></tr></thead>
    <tbody>
    {% for alias, t in aliases.items() %}
    <tr><td>{{ alias }}</td><td>{{ t }}</td><td>{% if can_manage and alias not in default_aliases %}<button class="btn btn-sm" onclick="mrDeleteAlias('{{ alias }}')">Hapus</button>{% else %}<span class="mc-muted">{{ 'baku' if alias in default_aliases else '' }}</span>{% endif %}</td></tr>
    {% endfor %}
    </tbody>
  </table>
  </div>
  {% if can_manage %}
  <div class="mc-filter" style="margin-top:.75rem">
    <label>Alias baru<input type="text" id="mr-pph-alias" placeholder="mis. PPh 4 ayat 2"></label>
    <label>Jenis PPh
      <select id="mr-pph-type">{% for t in pph_types %}<option value="{{ t }}">{{ t }}</option>{% endfor %}</select>
    </label>
    <button class="btn btn-primary btn-sm" onclick="mrAddAlias()">Tambah alias</button>
    <span id="mr-pph-msg" class="mc-muted"></span>
  </div>
  {% endif %}
  {% endif %}
</section>
{% endblock %}

{% block scripts %}
{% if can_manage %}
<script>
const MR_CAT = '/management-report/pemetaan/kategori';
async function mrPost(url, body, method) {
  const r = await fetch(url, {method: method || 'POST', credentials: 'same-origin',
    headers: {'Content-Type': 'application/json'}, body: body ? JSON.stringify(body) : undefined});
  let j = {}; try { j = await r.json(); } catch (e) {}
  return {ok: r.ok && j.ok, pesan: j.pesan || (r.ok ? 'Selesai.' : 'Gagal.'), j};
}
async function mrSyncCategories() {
  const f = document.getElementById('mr-cat-file').files[0];
  const msg = document.getElementById('mr-cat-msg');
  if (!f) { msg.textContent = 'Pilih file GL - MASTER.xlsb dulu.'; return; }
  const btn = document.getElementById('mr-cat-sync-btn');
  btn.disabled = true; msg.textContent = 'Menyinkronkan...';
  const fd = new FormData(); fd.append('file', f);
  try {
    const r = await fetch(MR_CAT + '/sync', {method: 'POST', body: fd, credentials: 'same-origin'});
    const j = await r.json();
    msg.textContent = j.pesan || (r.ok ? 'Selesai.' : 'Gagal.');
    if (j.ok && j.changed) setTimeout(() => location.reload(), 1200);
  } catch (e) { msg.textContent = 'Gagal sync: ' + e; }
  btn.disabled = false;
}
async function mrSaveLk(btn) {
  const tr = btn.closest('tr'), msg = tr.querySelector('.lk-msg');
  const res = await mrPost(MR_CAT + '/lk', {
    name: tr.dataset.name, statement: tr.querySelector('.lk-statement').value,
    kind: tr.querySelector('.lk-kind').value, seq: tr.querySelector('.lk-seq').value,
    label: tr.querySelector('.lk-label').value, needs_spt: tr.querySelector('.lk-needs').checked});
  msg.textContent = res.pesan;
}
async function mrAddAlias() {
  const msg = document.getElementById('mr-pph-msg');
  const res = await mrPost(MR_CAT + '/pph', {alias: document.getElementById('mr-pph-alias').value,
                                             pph_type: document.getElementById('mr-pph-type').value});
  msg.textContent = res.pesan;
  if (res.ok) setTimeout(() => location.reload(), 600);
}
async function mrDeleteAlias(alias) {
  const res = await mrPost(MR_CAT + '/pph/' + encodeURIComponent(alias), null, 'DELETE');
  if (res.ok) location.reload(); else alert(res.pesan);
}
</script>
{% endif %}
{% endblock %}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd app && python -m pytest tests/test_mrc_category_routes.py tests/test_mrc_category_map.py tests/test_mrc_mapping.py tests/test_gl_service.py -q -p no:cacheprovider -W ignore`
Expected: PASS (semua; test Pemetaan lama tetap hijau)

- [ ] **Step 5: Commit**

```bash
git add app/modules/management_report/routes.py app/templates/management_report/kategori.html app/templates/management_report/_linktabs.html app/tests/test_mrc_category_routes.py
git commit -m "feat(mr): Kategori SPT tab in Pemetaan (sync, Kategori LK, PPh aliases, unmapped accounts)

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Verifikasi dengan file asli dan regresi

**Files:**
- Test: `app/tests/test_mrc_category_real_file.py`

**Interfaces:**
- Consumes: `category_map.read_category_sheet`, `sync_categories`, `unmapped_accounts`, `get_lk_list`; file `Y:\Seagate\Management Report\2026\0926\GL - MASTER.xlsb` (tes dilewati bila file tidak ada, mengikuti pola `test_gl_real_file.py`).
- Produces: bukti bahwa lookup akun cocok dengan kolom kategori di 8.898 baris GL SMT 2026 (hasil pengecekan manual 14 Okt 2026).

- [ ] **Step 1: Write the test**

Lihat cara `test_gl_real_file.py` melewati test bila file tidak ada (fixture `local_copy`), lalu buat `app/tests/test_mrc_category_real_file.py`:

```python
# tests/test_mrc_category_real_file.py
import os
import shutil

import pytest

from modules.general_ledger import service as gl_service
from modules.general_ledger.parser import read_gl_sheet
from modules.management_report import category_map as cm

SRC = r"Y:\Seagate\Management Report\2026\0926\GL - MASTER.xlsb"
pytestmark = pytest.mark.skipif(not os.path.exists(SRC), reason="GL - MASTER.xlsb not available")


@pytest.fixture(scope="module")
def local_copy(tmp_path_factory):
    dst = tmp_path_factory.mktemp("glmaster") / "GL - MASTER.xlsb"
    shutil.copyfile(SRC, dst)
    return str(dst)


def test_real_coa_sheet_matches_the_categories_on_every_gl_row(local_copy):
    rows = cm.read_category_sheet(local_copy)
    assert len(rows) > 400
    cm.sync_categories("GL - MASTER.xlsb", "test", rows)
    cmap = cm.get_category_map()
    gl = read_gl_sheet(local_copy, "GL SMT")
    mismatch, missing = 0, set()
    for r in gl.rows:
        entry = cmap.get(("SMT", r["acc_statutory"]))
        if entry is None:
            missing.add(r["acc_statutory"])
        elif (entry["category_lk"], entry["category_spt"]) != (r["category_lk"], r["category_spt"]):
            mismatch += 1
    assert mismatch == 0 and not missing


def test_real_sheet_seeds_every_known_lk_with_a_report_type(local_copy):
    cm.sync_categories("GL - MASTER.xlsb", "test", cm.read_category_sheet(local_copy))
    lk = cm.get_lk_list()
    assert lk["Jasa Konsultasi & Advokasi"]["kind"] == "pendapatan"
    assert "TBA" not in lk and "tba" not in lk
    unknown = [n for n, m in lk.items() if not m["statement"]]
    assert unknown == []          # every category in the real sheet has a default report type
```

- [ ] **Step 2: Run the test**

Run: `cd app && python -m pytest tests/test_mrc_category_real_file.py -q -p no:cacheprovider -W ignore`
Expected: PASS. Bila `unknown` tidak kosong, tambahkan kategori yang disebut ke `DEFAULT_LK` di `category_map.py` (statement, kind, seq sesuai sifat kategori) lalu jalankan ulang.

- [ ] **Step 3: Run the Management Report and GL regression**

Run: `cd app && python -m pytest tests/test_gl_*.py tests/test_mr_*.py tests/test_mrc_*.py -q -p no:cacheprovider -W ignore`
Expected: PASS (semua)

- [ ] **Step 4: Commit**

```bash
git add app/tests/test_mrc_category_real_file.py app/modules/management_report/category_map.py
git commit -m "test(mr): verify category mapping against the real GL - MASTER COA sheet

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

## Self-Review

- **Spec coverage:** 14.11 M1 → Task 1; M2 → Task 2 (+ `needs_spt` menggantikan daftar hardcode "HPP/Beban Operasional/Lainnya" di 14.5); M3 → Task 2; panel akun belum dipetakan → Task 3–4; versi mapping → Task 1–2 (dicatat di snapshot oleh Plan SPT); M4 cost center sudah ada dan tidak disentuh. Pertanyaan terbuka no. 10 (sumber sync) diasumsikan: `GL - MASTER.xlsb`, terpisah dari sync Pemetaan COA & CC. No. 11 (`TBA`) diasumsikan = belum dipetakan.
- **Placeholder scan:** tidak ada TBD atau langkah tanpa kode.
- **Type consistency:** `get_category_map` mengembalikan dict berkunci `(source, account)` dengan nilai `{categories_expense, category_lk, category_spt}`; `get_lk_list` bernilai `{statement, kind, seq, label, needs_spt}`; dipakai identik di Task 3 dan 4 serta di Plan SPT.
