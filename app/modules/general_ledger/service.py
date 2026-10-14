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

_REAL = {"debit", "credit", "qty_awal", "qty_akhir", "harga_satuan", "debit_credit"}
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
    year         INTEGER,
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
            # Old pandas to_sql layout (or an older COLUMNS set): keep the data aside, never drop it.
            legacy = f"{table}_legacy"
            conn.execute(f"DROP TABLE IF EXISTS {legacy}")
            conn.execute(f"DROP INDEX IF EXISTS idx_{table}_tgl")
            conn.execute(f"DROP INDEX IF EXISTS idx_{table}_acc")
            conn.execute(f"ALTER TABLE {table} RENAME TO {legacy}")
        conn.executescript(_table_ddl(table))
    conn.executescript(_LOG_DDL)
    if "year" not in {r[1] for r in conn.execute("PRAGMA table_info(gl_sync_log)")}:
        conn.execute("ALTER TABLE gl_sync_log ADD COLUMN year INTEGER")        # logs before multi-year stay NULL
    conn.commit()


def _ts() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _year_of(tgl):
    return str(tgl)[:4] if tgl else ""


def replace_year(entity, year, rows, log) -> None:
    """Replace only the rows dated in `year`; every other year stays untouched."""
    year = int(year)
    if any(_year_of(r["tgl"]) != str(year) for r in rows):
        raise ValueError(f"Semua baris harus bertanggal {year}.")
    table = ENTITIES[entity]["table"]
    conn = get_conn()
    try:
        ensure_schema(conn)
        try:
            conn.execute(f"DELETE FROM {table} WHERE substr(tgl,1,4) = ?", (str(year),))
            marks = ",".join("?" * len(COLUMNS))
            conn.executemany(
                f"INSERT INTO {table} ({','.join(COLUMNS)}) VALUES ({marks})",
                [tuple(r[c] for c in COLUMNS) for r in rows])
            conn.execute(
                "INSERT INTO gl_sync_log (entity, year, synced_at, synced_by, filename, content_hash, "
                "rows_before, rows_after, total_debit, total_credit, dropped, summary) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (entity, year, _ts(), log["synced_by"], log["filename"], log["content_hash"],
                 log["rows_before"], log["rows_after"], log["total_debit"], log["total_credit"],
                 log["dropped"], json.dumps(log["summary"], ensure_ascii=False)))
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    finally:
        conn.close()


def _year_where(year):
    return ("", []) if year is None else (" WHERE substr(tgl,1,4) = ?", [str(int(year))])


def years_with_data(entity) -> list:
    """Years that hold at least one row, newest first."""
    table = ENTITIES[entity]["table"]
    conn = get_conn()
    try:
        ensure_schema(conn)
        cur = conn.execute(f"SELECT DISTINCT substr(tgl,1,4) FROM {table} "
                           f"WHERE tgl IS NOT NULL AND tgl <> '' ORDER BY 1 DESC")
        return [int(r[0]) for r in cur if str(r[0]).isdigit()]
    finally:
        conn.close()


def latest_year(entity):
    years = years_with_data(entity)
    return years[0] if years else None


def row_count(entity, year=None) -> int:
    table = ENTITIES[entity]["table"]
    where, params = _year_where(year)
    conn = get_conn()
    try:
        ensure_schema(conn)
        return conn.execute(f"SELECT COUNT(*) FROM {table}{where}", params).fetchone()[0]
    finally:
        conn.close()


def load_rows(entity, year=None) -> list:
    table = ENTITIES[entity]["table"]
    where, params = _year_where(year)
    conn = get_conn()
    try:
        ensure_schema(conn)
        return [dict(r) for r in conn.execute(
            f"SELECT {','.join(COLUMNS)} FROM {table}{where} ORDER BY id", params)]
    finally:
        conn.close()


def _log_row(r):
    d = dict(r)
    d["summary"] = json.loads(d["summary"]) if d.get("summary") else {}
    return d


def list_syncs(entity, year=None, limit=10) -> list:
    clause, params = ("", [])
    if year is not None:
        clause, params = (" AND year = ?", [int(year)])
    conn = get_conn()
    try:
        ensure_schema(conn)
        cur = conn.execute(f"SELECT * FROM gl_sync_log WHERE entity=?{clause} ORDER BY id DESC LIMIT ?",
                           [entity, *params, limit])
        return [_log_row(r) for r in cur]
    finally:
        conn.close()


def last_sync(entity, year=None):
    rows = list_syncs(entity, year, 1)
    return rows[0] if rows else None


def _like(text: str) -> str:
    esc = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{esc}%"


def _where(filters: dict):
    clauses, params = [], []
    if filters.get("year"):
        clauses.append("substr(tgl,1,4) = ?")
        params.append(str(int(filters["year"])))
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


def load_mr_source(entity, year=None) -> list:
    """GL rows with an amount, reduced to what the MR row builder needs. Year defaults to the latest."""
    year = latest_year(entity) if year is None else year
    if year is None:
        return []
    table = ENTITIES[entity]["table"]
    conn = get_conn()
    try:
        ensure_schema(conn)
        return [dict(r) for r in conn.execute(
            f"SELECT id_no, acc_management, tgl, allocation_memo, budget_activity, job_name, debit_credit "
            f"FROM {table} WHERE debit_credit IS NOT NULL AND debit_credit <> 0 "
            f"AND substr(tgl,1,4) = ? ORDER BY id", (str(int(year)),))]
    finally:
        conn.close()
