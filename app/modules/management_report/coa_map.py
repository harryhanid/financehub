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
_CODE_COL = 10                                    # 'Code', e.g. '-10-'
_EXPECTED_HEADER = {1: "COA SMT", 3: "COA ETF", 6: "COA HO", 9: "CATEGORIES 2", 10: "Code"}
CC_SHEET_NAME = "CC"
_CC_HEADER_ROW = 1
_CC_EXPECTED_HEADER = {1: "Cost Center", 2: "Cost Center Description", 3: "Cost Center TOTAL"}
_CC_SEQ_COL = 5
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


def _code(v) -> str:
    if isinstance(v, (int, float)):
        return ""                                  # numeric 0 / stray numbers are not a code
    return _text(v)


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
        code = _code(_cell(r, _CODE_COL))
        for source, col in _SOURCE_COL.items():
            account = _text(_cell(r, col))
            if account and (source, account) not in seen:
                seen.add((source, account))
                rows.append({"source": source, "account": account,
                             "coa_ho": coa_ho, "category": category, "code": code})
    return rows


def _seq(v) -> int:
    if isinstance(v, bool):
        return 0
    if isinstance(v, (int, float)):
        try:
            return int(v)
        except (ValueError, OverflowError):        # nan / inf
            return 0
    return 0


def normalise_cc(sheet_rows) -> list:
    if len(sheet_rows) <= _CC_HEADER_ROW:
        raise CoaParseError(f"Sheet '{CC_SHEET_NAME}' kosong.")
    header = sheet_rows[_CC_HEADER_ROW]
    for pos, label in _CC_EXPECTED_HEADER.items():
        actual = " ".join(str(_cell(header, pos) or "").split()).lower()
        if actual != label.lower():
            raise CoaParseError(
                f"Header sheet '{CC_SHEET_NAME}' tidak sesuai: kolom {pos + 1} harus '{label}'.")
    rows, seen = [], set()
    for r in sheet_rows[_CC_HEADER_ROW + 1:]:
        cc = _text(_cell(r, 1))
        if not cc or cc in seen:
            continue
        seen.add(cc)
        rows.append({"cost_center": cc, "total_cc": _text(_cell(r, 3)),
                     "seq": _seq(_cell(r, _CC_SEQ_COL)), "description": _text(_cell(r, 2))})
    return rows


def _read_sheets(fileobj, names, *normalisers):
    """Open the workbook once; return each sheet in `names` passed through its normaliser.
    Any failure other than CoaParseError is wrapped in CoaParseError."""
    try:
        wb = open_workbook(fileobj)
    except Exception as e:
        raise CoaParseError(f"File tidak bisa dibaca sebagai .xlsb: {e}") from e
    try:
        with wb:
            raw = []
            for name in names:
                if name not in wb.sheets:
                    raise CoaParseError(f"Sheet '{name}' tidak ditemukan di file.")
                with wb.get_sheet(name) as sh:
                    raw.append([[c.v for c in r] for r in sh.rows()])
        return tuple(fn(r) for fn, r in zip(normalisers, raw))
    except CoaParseError:
        raise
    except Exception as e:
        raise CoaParseError(f"File tidak bisa dibaca: {e}") from e


def read_coa_sheet(fileobj) -> list:
    return _read_sheets(fileobj, [SHEET_NAME], lambda r: normalise_coa(r))[0]


def read_mapping_sheets(fileobj) -> tuple:
    """Read sheets COA and CC from one workbook open -> (coa_rows, cc_rows)."""
    return _read_sheets(fileobj, [SHEET_NAME, CC_SHEET_NAME],
                        lambda r: normalise_coa(r), lambda r: normalise_cc(r))


_DDL = """
CREATE TABLE IF NOT EXISTS gl_coa_map (
    source   TEXT NOT NULL,
    account  TEXT NOT NULL,
    coa_ho   TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT '',
    code     TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (source, account)
);
CREATE TABLE IF NOT EXISTS gl_cc_map (
    cost_center TEXT PRIMARY KEY,
    total_cc    TEXT NOT NULL DEFAULT '',
    seq         INTEGER NOT NULL DEFAULT 0,
    description TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS gl_coa_sync_log (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    synced_at    TEXT,
    synced_by    TEXT,
    filename     TEXT,
    content_hash TEXT,
    rows_smt     INTEGER DEFAULT 0,
    rows_etf     INTEGER DEFAULT 0,
    rows_cc      INTEGER DEFAULT 0
);
"""


def _add_column_if_missing(conn, table, column, ddl) -> None:
    cols = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
    if column not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")


def ensure_schema(conn) -> None:
    conn.executescript(_DDL)
    _add_column_if_missing(conn, "gl_coa_map", "code", "TEXT NOT NULL DEFAULT ''")
    _add_column_if_missing(conn, "gl_coa_sync_log", "rows_cc", "INTEGER DEFAULT 0")
    conn.commit()


def compute_hash(rows, cc_rows=()) -> str:
    lines = sorted(json.dumps(["coa", r["source"], r["account"], r["coa_ho"], r["category"],
                               r.get("code", "")], ensure_ascii=False) for r in rows)
    lines += sorted(json.dumps(["cc", r["cost_center"], r["total_cc"], r["seq"],
                                r["description"]], ensure_ascii=False) for r in cc_rows)
    h = hashlib.sha256()
    for line in lines:
        h.update(line.encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()


def get_map() -> dict:
    conn = get_conn()
    try:
        ensure_schema(conn)
        return {(r["source"], r["account"]): (r["coa_ho"], r["category"], r["code"])
                for r in conn.execute(
                    "SELECT source, account, coa_ho, category, code FROM gl_coa_map")}
    finally:
        conn.close()


def get_cc_map() -> dict:
    conn = get_conn()
    try:
        ensure_schema(conn)
        return {r["cost_center"]: {"total": r["total_cc"], "seq": r["seq"],
                                   "description": r["description"]}
                for r in conn.execute(
                    "SELECT cost_center, total_cc, seq, description FROM gl_cc_map")}
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


def _count_rows() -> tuple:
    conn = get_conn()
    try:
        ensure_schema(conn)
        return (conn.execute("SELECT COUNT(*) FROM gl_coa_map").fetchone()[0],
                conn.execute("SELECT COUNT(*) FROM gl_cc_map").fetchone()[0])
    finally:
        conn.close()


def sync_coa(filename, user, rows, cc_rows=()) -> dict:
    """Replace both mappings unless identical to the last sync (and still in the tables)."""
    rows, cc_rows = list(rows), list(cc_rows)
    content_hash = compute_hash(rows, cc_rows)
    n_smt = sum(1 for r in rows if r["source"] == "SMT")
    n_etf = len(rows) - n_smt
    n_cc = len(cc_rows)
    last = last_sync()
    if (last and last["content_hash"] == content_hash
            and _count_rows() == (last["rows_smt"] + last["rows_etf"], last["rows_cc"] or 0)):
        return {"changed": False, "rows_smt": n_smt, "rows_etf": n_etf, "rows_cc": n_cc}
    conn = get_conn()
    try:
        ensure_schema(conn)
        try:
            conn.execute("DELETE FROM gl_coa_map")
            conn.execute("DELETE FROM gl_cc_map")
            conn.executemany(
                "INSERT INTO gl_coa_map (source, account, coa_ho, category, code) "
                "VALUES (?,?,?,?,?)",
                [(r["source"], r["account"], r["coa_ho"], r["category"], r.get("code", ""))
                 for r in rows])
            conn.executemany(
                "INSERT INTO gl_cc_map (cost_center, total_cc, seq, description) VALUES (?,?,?,?)",
                [(r["cost_center"], r["total_cc"], r["seq"], r["description"]) for r in cc_rows])
            conn.execute(
                "INSERT INTO gl_coa_sync_log (synced_at, synced_by, filename, content_hash, "
                "rows_smt, rows_etf, rows_cc) VALUES (?,?,?,?,?,?,?)",
                (datetime.now().isoformat(timespec="seconds"), user, filename, content_hash,
                 n_smt, n_etf, n_cc))
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    finally:
        conn.close()
    return {"changed": True, "rows_smt": n_smt, "rows_etf": n_etf, "rows_cc": n_cc}


def list_syncs(limit=10) -> list:
    """Newest sync-log rows first; rows_cc of old rows (NULL) is reported as 0."""
    limit = max(1, limit)
    conn = get_conn()
    try:
        ensure_schema(conn)
        out = []
        for r in conn.execute("SELECT * FROM gl_coa_sync_log ORDER BY id DESC LIMIT ?", (limit,)):
            d = dict(r)
            d["rows_cc"] = d["rows_cc"] or 0
            out.append(d)
        return out
    finally:
        conn.close()


def _page(rows, page, per_page) -> dict:
    per_page = max(1, per_page)
    total = len(rows)
    pages = max(1, -(-total // per_page))
    page = min(max(1, page), pages)
    start = (page - 1) * per_page
    return {"rows": rows[start:start + per_page], "total": total, "page": page,
            "pages": pages, "per_page": per_page}


def search_coa(source=None, q=None, page=1, per_page=100) -> dict:
    needle = (q or "").strip().lower()
    rows = []
    for (src, account), (coa_ho, category, code) in sorted(get_map().items()):
        if source in ("SMT", "ETF") and src != source:
            continue
        if needle and not any(needle in f.lower() for f in (account, coa_ho, category, code)):
            continue
        rows.append({"source": src, "account": account, "coa_ho": coa_ho,
                     "category": category, "code": code})
    return _page(rows, page, per_page)


def search_cc(q=None, page=1, per_page=100) -> dict:
    needle = (q or "").strip().lower()
    rows = []
    for cc, v in sorted(get_cc_map().items()):
        if needle and not any(needle in f.lower() for f in
                              (cc, v["total"], v["description"], str(v["seq"]))):
            continue
        rows.append({"cost_center": cc, "total_cc": v["total"], "seq": v["seq"],
                     "description": v["description"]})
    return _page(rows, page, per_page)
