"""Management Report: snapshot storage and report building."""
import json
from datetime import datetime

from database import get_conn

KEEP_SNAPSHOTS = 5

_DDL = """
CREATE TABLE IF NOT EXISTS mr_upload (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id  INTEGER NOT NULL REFERENCES companies(id),
    filename    TEXT,
    uploaded_by TEXT,
    uploaded_at TEXT,
    row_count   INTEGER DEFAULT 0,
    is_active   INTEGER DEFAULT 0,
    purged      INTEGER DEFAULT 0,
    content_hash   TEXT,
    change_summary TEXT,
    meta           TEXT
);
CREATE TABLE IF NOT EXISTS mr_append (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    upload_id   INTEGER NOT NULL REFERENCES mr_upload(id),
    coa         TEXT,
    mm          INTEGER,
    yy          INTEGER,
    cc          TEXT,
    category    TEXT,
    activity    TEXT,
    description TEXT,
    pta         REAL DEFAULT 0,
    custom      TEXT,
    mm1         INTEGER,
    act         REAL DEFAULT 0,
    bgt         REAL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_mr_append_upload_cc ON mr_append(upload_id, cc);
"""


_ROW_FIELDS = ("coa", "mm", "yy", "cc", "category", "activity", "description",
               "pta", "custom", "mm1", "act", "bgt")


def ensure_schema(conn) -> None:
    conn.executescript(_DDL)
    # Databases created before sync was added lack these two columns.
    cols = {r[1] for r in conn.execute("PRAGMA table_info(mr_upload)")}
    for col in ("content_hash", "change_summary", "meta"):
        if col not in cols:
            conn.execute(f"ALTER TABLE mr_upload ADD COLUMN {col} TEXT")
    conn.commit()


def _ts() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _purge_old(conn, company_id: int, keep: int) -> None:
    ids = [r["id"] for r in conn.execute(
        "SELECT id FROM mr_upload WHERE company_id=? AND purged=0 ORDER BY id DESC",
        (company_id,))]
    for uid in ids[keep:]:
        active = conn.execute("SELECT is_active FROM mr_upload WHERE id=?", (uid,)).fetchone()
        if active["is_active"]:
            continue
        conn.execute("DELETE FROM mr_append WHERE upload_id=?", (uid,))
        conn.execute("UPDATE mr_upload SET purged=1 WHERE id=?", (uid,))


def save_upload(company_id: int, filename: str, uploaded_by: str, rows: list,
                keep: int = KEEP_SNAPSHOTS, content_hash: str = None,
                change_summary: dict = None, meta: dict = None) -> int:
    if not rows:
        raise ValueError("Tidak ada baris data yang valid.")
    conn = get_conn()
    try:
        ensure_schema(conn)
        cur = conn.execute(
            "INSERT INTO mr_upload (company_id, filename, uploaded_by, uploaded_at, row_count, "
            "is_active, content_hash, change_summary, meta) VALUES (?,?,?,?,?,0,?,?,?)",
            (company_id, filename, uploaded_by, _ts(), len(rows), content_hash,
             json.dumps(change_summary) if change_summary is not None else None,
             json.dumps(meta) if meta else None))
        upload_id = cur.lastrowid
        conn.executemany(
            "INSERT INTO mr_append (upload_id, coa, mm, yy, cc, category, activity, description, "
            "pta, custom, mm1, act, bgt) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            [(upload_id, r["coa"], r["mm"], r["yy"], r["cc"], r["category"], r["activity"],
              r["description"], r["pta"], r["custom"], r["mm1"], r["act"], r["bgt"])
             for r in rows])
        conn.execute("UPDATE mr_upload SET is_active=0 WHERE company_id=?", (company_id,))
        conn.execute("UPDATE mr_upload SET is_active=1 WHERE id=?", (upload_id,))
        _purge_old(conn, company_id, keep)
        conn.commit()
        return upload_id
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_active_upload_id(company_id: int):
    conn = get_conn()
    try:
        ensure_schema(conn)
        row = conn.execute(
            "SELECT id FROM mr_upload WHERE company_id=? AND is_active=1", (company_id,)).fetchone()
        return row["id"] if row else None
    finally:
        conn.close()


def load_active_rows(company_id: int) -> list:
    """All rows of the active snapshot as dicts keyed like the parser's rows."""
    uid = get_active_upload_id(company_id)
    if uid is None:
        return []
    conn = get_conn()
    try:
        cur = conn.execute(
            f"SELECT {', '.join(_ROW_FIELDS)} FROM mr_append WHERE upload_id=?", (uid,))
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def get_active_hash(company_id: int):
    """Stored content hash of the active snapshot; None if absent (pre-sync snapshots)."""
    conn = get_conn()
    try:
        ensure_schema(conn)
        row = conn.execute(
            "SELECT content_hash FROM mr_upload WHERE company_id=? AND is_active=1",
            (company_id,)).fetchone()
        return row["content_hash"] if row else None
    finally:
        conn.close()


def get_active_summary(company_id: int):
    """Change summary recorded when the active snapshot was synced, or None."""
    conn = get_conn()
    try:
        ensure_schema(conn)
        row = conn.execute(
            "SELECT change_summary FROM mr_upload WHERE company_id=? AND is_active=1",
            (company_id,)).fetchone()
        return json.loads(row["change_summary"]) if row and row["change_summary"] else None
    finally:
        conn.close()


def get_active_meta(company_id: int) -> dict:
    """Metadata read from the master workbook at the last sync (CC descriptions, report period)."""
    empty = {"cc_names": {}, "period": None}
    conn = get_conn()
    try:
        ensure_schema(conn)
        row = conn.execute(
            "SELECT meta FROM mr_upload WHERE company_id=? AND is_active=1", (company_id,)).fetchone()
        if not row or not row["meta"]:
            return empty
        data = json.loads(row["meta"])
        return {"cc_names": data.get("cc_names") or {}, "period": data.get("period")}
    finally:
        conn.close()


def list_uploads(company_id: int) -> list:
    conn = get_conn()
    try:
        ensure_schema(conn)
        rows = conn.execute(
            "SELECT id, filename, uploaded_by, uploaded_at, row_count, is_active, purged "
            "FROM mr_upload WHERE company_id=? ORDER BY id DESC", (company_id,)).fetchall()
        return [{**dict(r), "is_active": bool(r["is_active"]), "purged": bool(r["purged"])}
                for r in rows]
    finally:
        conn.close()


def activate_upload(company_id: int, upload_id: int) -> bool:
    conn = get_conn()
    try:
        ensure_schema(conn)
        row = conn.execute(
            "SELECT id FROM mr_upload WHERE id=? AND company_id=? AND purged=0",
            (upload_id, company_id)).fetchone()
        if not row:
            return False
        conn.execute("UPDATE mr_upload SET is_active=0 WHERE company_id=?", (company_id,))
        conn.execute("UPDATE mr_upload SET is_active=1 WHERE id=?", (upload_id,))
        conn.commit()
        return True
    finally:
        conn.close()


def get_filter_options(company_id: int) -> dict:
    empty = {"ccs": [], "yys": [], "mms": [], "coas": [], "cats": []}
    uid = get_active_upload_id(company_id)
    if uid is None:
        return empty
    conn = get_conn()
    try:
        def distinct(col):
            return [r[0] for r in conn.execute(
                f"SELECT DISTINCT {col} FROM mr_append WHERE upload_id=? AND {col} IS NOT NULL "
                f"ORDER BY {col}", (uid,))]
        return {"ccs": distinct("cc"), "yys": distinct("yy"),
                "mms": distinct("mm"), "coas": distinct("coa"),
                "cats": distinct("category")}
    finally:
        conn.close()


def _metrics(bgt: float, pta: float, act: float) -> dict:
    available = bgt + pta
    diff = act - available
    pct = (diff / available) if available else None
    return {"bgt": round(bgt, 6), "pta": round(pta, 6), "available": round(available, 6),
            "act": round(act, 6), "diff": round(diff, 6),
            "pct": round(pct, 6) if pct is not None else None}


def _where(upload_id: int, cc, yy, mm, coas, cats=None):
    sql, params = "upload_id=?", [upload_id]
    if cc is not None:
        sql += " AND cc=?"
        params.append(cc)
    if yy is not None:
        sql += " AND yy=?"
        params.append(yy)
    if mm is not None:
        sql += " AND mm=?"
        params.append(mm)
    if coas:
        sql += " AND coa IN (%s)" % ",".join("?" * len(coas))
        params.extend(coas)
    if cats:
        sql += " AND category IN (%s)" % ",".join("?" * len(cats))
        params.extend(cats)
    return sql, params


def build_report(company_id: int, cc: str, yy=None, mm=None, coas=None, cats=None) -> dict:
    empty = {"cc": cc, "has_data": False, "groups": [], "grand": _metrics(0, 0, 0)}
    uid = get_active_upload_id(company_id)
    if uid is None:
        return empty
    where, params = _where(uid, cc, yy, mm, coas, cats)
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT category, custom, mm1, description, activity, "
            "SUM(bgt) AS bgt, SUM(pta) AS pta, SUM(act) AS act "
            f"FROM mr_append WHERE {where} "
            "GROUP BY category, custom, mm1, description, activity", params).fetchall()
    finally:
        conn.close()
    if not rows:
        return empty

    rows = sorted(rows, key=lambda r: ((r["category"] or "").lower(), r["custom"] or "",
                                       r["mm1"] or 0, (r["description"] or "").lower(),
                                       (r["activity"] or "").lower()))
    groups, by_cat = [], {}
    for r in rows:
        g = by_cat.get(r["category"])
        if g is None:
            g = {"category": r["category"], "rows": [], "_sum": [0.0, 0.0, 0.0]}
            by_cat[r["category"]] = g
            groups.append(g)
        g["rows"].append({"custom": r["custom"], "mm1": r["mm1"],
                          "description": r["description"], "activity": r["activity"],
                          **_metrics(r["bgt"] or 0, r["pta"] or 0, r["act"] or 0)})
        for i, k in enumerate(("bgt", "pta", "act")):
            g["_sum"][i] += r[k] or 0
    grand = [0.0, 0.0, 0.0]
    for g in groups:
        s = g.pop("_sum")
        g["total"] = _metrics(*s)
        for i in range(3):
            grand[i] += s[i]
    return {"cc": cc, "has_data": True, "groups": groups, "grand": _metrics(*grand)}


def list_ccs_with_data(company_id: int, yy=None, mm=None, coas=None, cats=None) -> list:
    uid = get_active_upload_id(company_id)
    if uid is None:
        return []
    where, params = _where(uid, None, yy, mm, coas, cats)
    conn = get_conn()
    try:
        return [r[0] for r in conn.execute(
            f"SELECT DISTINCT cc FROM mr_append WHERE {where} AND cc IS NOT NULL ORDER BY cc", params)]
    finally:
        conn.close()


def aggregate_by_coa(company_id: int, cc=None, yy=None, mm=None, coas=None, cats=None) -> dict:
    """{coa: (bgt, pta, act)} of the active snapshot; cc=None means all cost centers."""
    uid = get_active_upload_id(company_id)
    if uid is None:
        return {}
    where, params = _where(uid, cc, yy, mm, coas, cats)
    conn = get_conn()
    try:
        cur = conn.execute(
            f"SELECT coa, SUM(bgt), SUM(pta), SUM(act) FROM mr_append WHERE {where} GROUP BY coa",
            params)
        return {r[0]: (r[1] or 0.0, r[2] or 0.0, r[3] or 0.0) for r in cur.fetchall() if r[0]}
    finally:
        conn.close()


_APPEND_COLS = ("coa", "mm", "yy", "cc", "category", "activity", "description",
                "pta", "custom", "mm1", "act", "bgt")


def _like_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def query_append(company_id: int, cc=None, yy=None, mm=None, coas=None, q=None,
                 limit=None, offset=0, cats=None) -> dict:
    """Rows of the active snapshot in sheet-Append1 order, plus the total for the filter.

    `q` is a case-insensitive substring over coa, category, activity and description;
    `limit=None` returns every row that passes the filters."""
    uid = get_active_upload_id(company_id)
    if uid is None:
        return {"rows": [], "total": 0}
    where, params = _where(uid, cc, yy, mm, coas, cats)
    if q:
        like = f"%{_like_escape(q.lower())}%"
        where += (" AND (LOWER(coa) LIKE ? ESCAPE '\\' OR LOWER(category) LIKE ? ESCAPE '\\'"
                  " OR LOWER(activity) LIKE ? ESCAPE '\\' OR LOWER(description) LIKE ? ESCAPE '\\')")
        params = params + [like] * 4
    conn = get_conn()
    try:
        total = conn.execute(f"SELECT COUNT(*) FROM mr_append WHERE {where}", params).fetchone()[0]
        sql = f"SELECT {', '.join(_APPEND_COLS)} FROM mr_append WHERE {where} ORDER BY id"
        args = list(params)
        if limit is not None:
            sql += " LIMIT ? OFFSET ?"
            args += [limit, offset]
        rows = [dict(r) for r in conn.execute(sql, args).fetchall()]
        return {"rows": rows, "total": total}
    finally:
        conn.close()
