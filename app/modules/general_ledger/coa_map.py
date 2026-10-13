"""General Ledger MR: account -> COA HO / category mapping from the 'COA' sheet of
Management Report - MASTER.xlsb."""
import hashlib
import json
import re
from datetime import datetime

from pyxlsb import open_workbook

from database import get_conn

SHEET_NAME = "COA"
_HEADER_ROW = 1                                   # 0-based; row 0 is a numbering row
_SOURCE_COL = {"SMT": 1, "ETF": 3}                # COA SMT, COA ETF
_COA_HO_COL = 6
_CATEGORY_COL = 9                                 # CATEGORIES 2, already shaped like ' 10 - Office ... '
_EXPECTED_HEADER = {1: "COA SMT", 3: "COA ETF", 6: "COA HO", 9: "CATEGORIES 2"}
_ERR = re.compile(r"^0x[0-9A-Fa-f]{1,2}$")        # how pyxlsb shows an Excel error cell


class CoaParseError(ValueError):
    """Raised with a user-facing message when the COA sheet cannot be used."""


def _text(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    s = str(v).strip()
    return "" if _ERR.match(s) else s


def _coa_ho(v):
    if isinstance(v, (int, float)):
        return str(int(v)) if v else None
    s = _text(v)
    return s if s.isdigit() else None


def _cell(row, i):
    return row[i] if i < len(row) else None


def normalise_coa(sheet_rows) -> list:
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
        coa_ho = _coa_ho(_cell(r, _COA_HO_COL))
        if coa_ho is None:
            continue
        category = _text(_cell(r, _CATEGORY_COL))
        for source, col in _SOURCE_COL.items():
            account = _text(_cell(r, col))
            if account and (source, account) not in seen:
                seen.add((source, account))
                rows.append({"source": source, "account": account,
                             "coa_ho": coa_ho, "category": category})
    return rows


def read_coa_sheet(fileobj) -> list:
    try:
        wb = open_workbook(fileobj)
    except Exception as e:
        raise CoaParseError(f"File tidak bisa dibaca sebagai .xlsb: {e}") from e
    try:
        with wb:
            if SHEET_NAME not in wb.sheets:
                raise CoaParseError(f"Sheet '{SHEET_NAME}' tidak ditemukan di file.")
            with wb.get_sheet(SHEET_NAME) as sh:
                return normalise_coa([[c.v for c in r] for r in sh.rows()])
    except CoaParseError:
        raise
    except Exception as e:
        raise CoaParseError(f"File tidak bisa dibaca: {e}") from e


_DDL = """
CREATE TABLE IF NOT EXISTS gl_coa_map (
    source   TEXT NOT NULL,
    account  TEXT NOT NULL,
    coa_ho   TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (source, account)
);
CREATE TABLE IF NOT EXISTS gl_coa_sync_log (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    synced_at    TEXT,
    synced_by    TEXT,
    filename     TEXT,
    content_hash TEXT,
    rows_smt     INTEGER DEFAULT 0,
    rows_etf     INTEGER DEFAULT 0
);
"""


def ensure_schema(conn) -> None:
    conn.executescript(_DDL)
    conn.commit()


def compute_hash(rows) -> str:
    lines = sorted(json.dumps([r["source"], r["account"], r["coa_ho"], r["category"]],
                              ensure_ascii=False) for r in rows)
    h = hashlib.sha256()
    for line in lines:
        h.update(line.encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()


def get_map() -> dict:
    conn = get_conn()
    try:
        ensure_schema(conn)
        return {(r["source"], r["account"]): (r["coa_ho"], r["category"])
                for r in conn.execute("SELECT source, account, coa_ho, category FROM gl_coa_map")}
    finally:
        conn.close()


def last_sync():
    conn = get_conn()
    try:
        ensure_schema(conn)
        row = conn.execute("SELECT * FROM gl_coa_sync_log ORDER BY id DESC LIMIT 1").fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def _count_rows() -> int:
    conn = get_conn()
    try:
        ensure_schema(conn)
        return conn.execute("SELECT COUNT(*) FROM gl_coa_map").fetchone()[0]
    finally:
        conn.close()


def sync_coa(filename, user, rows) -> dict:
    """Replace the mapping with `rows` unless identical to the last sync (and still in the table)."""
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
            conn.execute("DELETE FROM gl_coa_map")
            conn.executemany(
                "INSERT INTO gl_coa_map (source, account, coa_ho, category) VALUES (?,?,?,?)",
                [(r["source"], r["account"], r["coa_ho"], r["category"]) for r in rows])
            conn.execute(
                "INSERT INTO gl_coa_sync_log (synced_at, synced_by, filename, content_hash, "
                "rows_smt, rows_etf) VALUES (?,?,?,?,?,?)",
                (datetime.now().isoformat(timespec="seconds"), user, filename, content_hash,
                 n_smt, n_etf))
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    finally:
        conn.close()
    return {"changed": True, "rows_smt": n_smt, "rows_etf": n_etf}
