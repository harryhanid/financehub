# modules/management_report/category_map.py
"""Account -> category mapping used by SPT Badan (and shown in the Pemetaan menu).

M1 account categories come from the 'COA' sheet of GL - MASTER.xlsb; M2 (Kategori LK list) and
M3 (PPh type aliases) are maintained in the app. Every change bumps a mapping version."""
import hashlib
import json
import re
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
"""


DEFAULT_ALIASES = {"pph21": "PPh 21", "pph23": "PPh 23", "pph4(2)": "PPh 4(2)", "nonpph": "Non PPh"}


def ensure_schema(conn) -> None:
    conn.executescript(_DDL)
    conn.execute("INSERT OR IGNORE INTO gl_mapping_meta (key, value) VALUES ('version', '1')")
    conn.executemany("INSERT OR IGNORE INTO gl_pph_alias (alias, pph_type) VALUES (?, ?)",
                     list(DEFAULT_ALIASES.items()))
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
