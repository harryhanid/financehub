# modules/spt_badan/service.py
"""SPT Badan: periods, snapshots (atomic) and read queries."""
import json
import sqlite3
from datetime import datetime

from database import get_conn

ENTITIES = {"smt": {"label": "SMT", "source": "SMT"}}
MAX_SNAPSHOTS = 3
MIN_YEAR, MAX_YEAR = 2000, 2100

_DDL = """
CREATE TABLE IF NOT EXISTS spt_period (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    entity     TEXT NOT NULL,
    tax_year   INTEGER NOT NULL,
    status     TEXT NOT NULL DEFAULT 'draft',
    label      TEXT NOT NULL DEFAULT '',
    params     TEXT NOT NULL DEFAULT '{}',
    created_at TEXT,
    created_by TEXT,
    UNIQUE (entity, tax_year)
);
CREATE TABLE IF NOT EXISTS spt_snapshot (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    period_id     INTEGER NOT NULL REFERENCES spt_period(id),
    taken_at      TEXT,
    taken_by      TEXT,
    gl_hash       TEXT NOT NULL DEFAULT '',
    map_version   INTEGER NOT NULL DEFAULT 0,
    row_count     INTEGER NOT NULL DEFAULT 0,
    total_debit   REAL NOT NULL DEFAULT 0,
    total_credit  REAL NOT NULL DEFAULT 0,
    date_min      TEXT,
    date_max      TEXT,
    is_current    INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_spt_snapshot_period ON spt_snapshot(period_id, is_current);
CREATE TABLE IF NOT EXISTS spt_gl_line (
    snapshot_id    INTEGER NOT NULL,
    gl_id          INTEGER NOT NULL,
    tgl            TEXT,
    id_no          TEXT,
    acc_statutory  TEXT,
    acc_management TEXT,
    job_name       TEXT,
    memo           TEXT,
    debit_credit   REAL,
    category_lk    TEXT,
    category_spt   TEXT,
    pph_type_raw   TEXT,
    pph_type       TEXT,
    accrual_actual TEXT,
    PRIMARY KEY (snapshot_id, gl_id)
);
CREATE INDEX IF NOT EXISTS idx_spt_line_cat ON spt_gl_line(snapshot_id, category_lk, category_spt);
CREATE TABLE IF NOT EXISTS spt_exception (
    snapshot_id INTEGER NOT NULL,
    gl_id       INTEGER NOT NULL,
    kind        TEXT NOT NULL,
    severity    TEXT NOT NULL,
    account     TEXT,
    detail      TEXT
);
CREATE INDEX IF NOT EXISTS idx_spt_exc_snapshot ON spt_exception(snapshot_id, kind);
CREATE TABLE IF NOT EXISTS spt_control (
    snapshot_id INTEGER NOT NULL,
    code        TEXT NOT NULL,
    name        TEXT NOT NULL,
    left_value  REAL,
    right_value REAL,
    diff        REAL,
    status      TEXT NOT NULL,
    blocking    INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (snapshot_id, code)
);
"""


def ensure_schema(conn) -> None:
    conn.executescript(_DDL)
    conn.commit()


def _ts() -> str:
    return datetime.now().isoformat(timespec="seconds")


def create_period(entity, tax_year, user, label="Simulasi YTD", params=None) -> int:
    if entity not in ENTITIES:
        raise ValueError("Entitas belum didukung.")
    try:
        year = int(tax_year)
    except (TypeError, ValueError):
        raise ValueError(f"Tahun pajak harus berupa angka {MIN_YEAR}-{MAX_YEAR}.") from None
    if not MIN_YEAR <= year <= MAX_YEAR:
        raise ValueError(f"Tahun pajak harus antara {MIN_YEAR} dan {MAX_YEAR}.")
    conn = get_conn()
    try:
        ensure_schema(conn)
        try:
            cur = conn.execute(
                "INSERT INTO spt_period (entity, tax_year, status, label, params, created_at, created_by) "
                "VALUES (?,?,?,?,?,?,?)",
                (entity, year, "draft", (label or "").strip(), json.dumps(params or {}, ensure_ascii=False),
                 _ts(), user))
            conn.commit()
        except sqlite3.IntegrityError:
            conn.rollback()
            raise ValueError(f"Periode {ENTITIES[entity]['label']} {year} sudah ada.") from None
        return cur.lastrowid
    finally:
        conn.close()


def _period_row(r):
    d = dict(r)
    d["params"] = json.loads(d["params"]) if d.get("params") else {}
    return d


def get_period(period_id):
    conn = get_conn()
    try:
        ensure_schema(conn)
        row = conn.execute("SELECT * FROM spt_period WHERE id=?", (period_id,)).fetchone()
        return _period_row(row) if row else None
    finally:
        conn.close()


def list_periods() -> list:
    conn = get_conn()
    try:
        ensure_schema(conn)
        return [_period_row(r) for r in conn.execute(
            "SELECT * FROM spt_period ORDER BY tax_year DESC, entity")]
    finally:
        conn.close()
