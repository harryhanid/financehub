# modules/spt_badan/service.py
"""SPT Badan: periods, snapshots (atomic) and read queries."""
import json
import sqlite3
from datetime import datetime

from database import get_conn
from modules.general_ledger import service as gl_service
from modules.general_ledger import staging
from modules.management_report import category_map
from modules.spt_badan import classify, controls, income_statement

ENTITIES = {"smt": {"label": "SMT", "source": "SMT"}}
MAX_SNAPSHOTS = 3
MIN_YEAR, MAX_YEAR = 2000, 2100

# Tables: db_migrations/0004_fn_spt_badan.sql (static; the runtime ensure_schema/_DDL is gone).

_LINE_COLS = (("gl_id", "bigint"), ("tgl", 'text collate "C"'), ("id_no", 'text collate "C"'),
              ("acc_statutory", 'text collate "C"'), ("acc_management", 'text collate "C"'),
              ("job_name", 'text collate "C"'), ("memo", 'text collate "C"'),
              ("debit_credit", "double precision"), ("category_lk", 'text collate "C"'),
              ("category_spt", 'text collate "C"'), ("pph_type_raw", 'text collate "C"'),
              ("pph_type", 'text collate "C"'), ("accrual_actual", 'text collate "C"'))
_EXC_COLS = (("gl_id", "bigint"), ("kind", 'text collate "C"'), ("severity", 'text collate "C"'),
             ("account", 'text collate "C"'), ("detail", 'text collate "C"'))
_SID = "currval(pg_get_serial_sequence(quote_ident(current_schema()) || '.\"spt_snapshot\"', 'id'))"


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
        row = conn.execute("SELECT * FROM spt_period WHERE id=?", (period_id,)).fetchone()
        return _period_row(row) if row else None
    finally:
        conn.close()


def list_periods() -> list:
    conn = get_conn()
    try:
        return [_period_row(r) for r in conn.execute(
            "SELECT * FROM spt_period ORDER BY tax_year DESC, entity")]
    finally:
        conn.close()


def _prune(period_id) -> list:
    """Batch items that delete all but the MAX_SNAPSHOTS newest snapshots of the period (children first).

    Run inside the snapshot batch, after the new snapshot is inserted, so it is counted."""
    old = ("SELECT id FROM spt_snapshot WHERE period_id=? ORDER BY id DESC OFFSET ?", (period_id, MAX_SNAPSHOTS))
    items = [(f"DELETE FROM {table} WHERE snapshot_id IN ({old[0]})", old[1])
             for table in ("spt_gl_line", "spt_exception", "spt_control")]
    items.append((f"DELETE FROM spt_snapshot WHERE id IN ({old[0]})", old[1]))
    return items


def take_snapshot(period_id, user) -> int:
    """Classify the period's GL year and store it all in one transaction; returns the snapshot id."""
    period = get_period(period_id)
    if period is None:
        raise KeyError(period_id)
    entity, year = period["entity"], period["tax_year"]
    ent = ENTITIES[entity]
    # Read the freshness markers FIRST: a sync/edit landing mid-snapshot then reads as stale, never as current.
    last = gl_service.last_sync(entity, year)
    gl_hash = last["content_hash"] if last else ""
    map_version = category_map.get_version()
    gl_lines = gl_service.load_lines(entity, year)
    if not gl_lines:
        raise ValueError(f"Tidak ada baris GL {ent['label']} untuk tahun {year}. Sync General Ledger dulu.")

    cmap = category_map.get_category_map()
    lk_list = category_map.get_lk_list()
    aliases = category_map.get_pph_aliases()

    classified, exceptions = [], []
    for line in gl_lines:
        item, found = classify.classify_line(line, ent["source"], cmap, lk_list, aliases)
        classified.append(item)
        exceptions.extend({**e, "gl_id": item["gl_id"], "account": item["acc_statutory"]} for e in found)

    totals, spt_totals = income_statement.aggregate(classified)
    statement = income_statement.build_income_statement(totals, spt_totals, lk_list)
    pnl = {n for n, m in lk_list.items() if m["statement"] == "laba_rugi"}
    pnl_sum = -sum(v for n, v in totals.items() if n in pnl and n != income_statement.TAX)
    total_debit = sum(l["debit"] or 0.0 for l in gl_lines)
    total_credit = sum(l["credit"] or 0.0 for l in gl_lines)
    computed = controls.compute_controls(
        total_debit=total_debit, total_credit=total_credit, line_count=len(classified),
        gl_row_count=gl_service.row_count(entity, year), exceptions=exceptions,
        out_of_year=sum(1 for l in classified if not (l["tgl"] or "").startswith(f"{year}-")),
        statement_pbt=statement["summary"]["pbt"], pnl_sum_excl_tax=pnl_sum)
    dates = sorted(l["tgl"] for l in classified if l["tgl"])

    line_rows = [tuple(l[c] for c, _ in _LINE_COLS) for l in classified]
    exc_rows = [tuple(e[c] for c, _ in _EXC_COLS) for e in exceptions]

    # R21: lines and exceptions (one GL year, ~9k rows) go to staging tables in chunks; ONE batch then
    # swaps the current flag, inserts the snapshot and its children, prunes old snapshots and drops
    # the staging tables. All or nothing; a failure leaves the previous snapshot current.
    conn = get_conn()
    st_lines, st_exc = staging.new_name("spt"), staging.new_name("spt")
    try:
        prune = _prune(period_id)                       # batch items only; run inside the swap batch
        staging.drop_orphans(conn, "spt")
        try:
            staging.create(conn, st_lines, _LINE_COLS)
            staging.create(conn, st_exc, _EXC_COLS)
            n_lines = staging.load(conn, st_lines, [c for c, _ in _LINE_COLS], line_rows)
            n_exc = staging.load(conn, st_exc, [c for c, _ in _EXC_COLS], exc_rows)
            items = [
                # Serialise concurrent snapshots of one period until this batch commits: otherwise two runs
                # can each clear is_current and insert their own current snapshot (two current rows).
                ("SELECT pg_advisory_xact_lock(hashtext(?))", (f"spt:{period_id}",)),
                staging.guard(st_lines, n_lines),
                staging.guard(st_exc, n_exc),
                ("UPDATE spt_snapshot SET is_current=0 WHERE period_id=?", (period_id,)),
                ("INSERT INTO spt_snapshot (period_id, taken_at, taken_by, gl_hash, map_version, row_count, "
                 "total_debit, total_credit, date_min, date_max, is_current) VALUES (?,?,?,?,?,?,?,?,?,?,1) "
                 "RETURNING id",
                 (period_id, _ts(), user, gl_hash, map_version, len(classified), total_debit, total_credit,
                  dates[0] if dates else None, dates[-1] if dates else None)),
                staging.copy("spt_gl_line", st_lines, [c for c, _ in _LINE_COLS], ("snapshot_id",), (_SID,)),
                staging.copy("spt_exception", st_exc, [c for c, _ in _EXC_COLS], ("snapshot_id",), (_SID,)),
            ]
            items += [(f"INSERT INTO spt_control (snapshot_id, code, name, left_value, right_value, diff, "
                       f"status, blocking) VALUES ({_SID},?,?,?,?,?,?,?) RETURNING snapshot_id",
                       (c["code"], c["name"], c["left_value"], c["right_value"], c["diff"], c["status"],
                        c["blocking"])) for c in computed]
            items += prune
            items += [staging.drop(st_lines), staging.drop(st_exc)]
            sid = conn.batch(items)[4].lastrowid   # [lock, guard, guard, update, insert]
        except Exception:
            staging.discard(conn, st_lines)
            staging.discard(conn, st_exc)
            raise
    finally:
        conn.close()
    return sid


def get_current_snapshot(period_id):
    conn = get_conn()
    try:
        row = conn.execute("SELECT * FROM spt_snapshot WHERE period_id=? AND is_current=1",
                           (period_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def list_snapshots(period_id) -> list:
    conn = get_conn()
    try:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM spt_snapshot WHERE period_id=? ORDER BY id DESC", (period_id,))]
    finally:
        conn.close()


def staleness(period, snapshot) -> list:
    reasons = []
    last = gl_service.last_sync(period["entity"], period["tax_year"])
    if snapshot["gl_hash"] != (last["content_hash"] if last else ""):
        reasons.append("GL berubah sejak snapshot")
    if snapshot["map_version"] != category_map.get_version():
        reasons.append("Pemetaan berubah sejak snapshot")
    return reasons


def get_controls(period, snapshot) -> list:
    conn = get_conn()
    try:
        stored = [dict(r) for r in conn.execute(
            "SELECT * FROM spt_control WHERE snapshot_id=?", (snapshot["id"],))]
    finally:
        conn.close()
    stored.append(controls.stale_control(staleness(period, snapshot)))
    return sorted(stored, key=lambda c: c["code"])


def step_statuses(snapshot, ctrls) -> list:
    if snapshot is None:
        return [{"name": n, "status": "belum", "endpoint": e} for n, e in (
            ("Snapshot GL", "spt_badan.detail"), ("Validasi klasifikasi", "spt_badan.exceptions"),
            ("Laba rugi komersial", "spt_badan.income_statement"), ("Kontrol", "spt_badan.controls_page"))]
    by = {c["code"]: c for c in ctrls}

    def worst(*codes):
        sts = [by[c]["status"] for c in codes if c in by]
        return "gagal" if "gagal" in sts else "peringatan" if "peringatan" in sts else "lulus"

    return [
        {"name": "Snapshot GL", "status": worst("C1", "C2", "C5"), "endpoint": "spt_badan.detail"},
        {"name": "Validasi klasifikasi", "status": worst("C3", "C4", "C7", "C9"),
         "endpoint": "spt_badan.exceptions"},
        {"name": "Laba rugi komersial", "status": worst("C6"), "endpoint": "spt_badan.income_statement"},
        {"name": "Kontrol", "status": worst(*by), "endpoint": "spt_badan.controls_page"},
    ]


def income_statement_for(snapshot_id) -> dict:
    conn = get_conn()
    try:
        lines = [{"category_lk": r[0], "category_spt": r[1], "debit_credit": r[2]} for r in conn.execute(
            "SELECT category_lk, category_spt, SUM(debit_credit) FROM spt_gl_line "
            "WHERE snapshot_id=? AND category_lk <> '' GROUP BY category_lk, category_spt", (snapshot_id,))]
    finally:
        conn.close()
    totals, spt_totals = income_statement.aggregate(lines)
    return income_statement.build_income_statement(totals, spt_totals, category_map.get_lk_list())


def _like(text) -> str:
    esc = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{esc}%"


def _paged(total, page, per_page):
    pages = max(1, -(-total // per_page))
    page = min(max(1, page), pages)
    return page, pages, (page - 1) * per_page


def exception_groups(snapshot_id) -> list:
    conn = get_conn()
    try:
        return [dict(r) for r in conn.execute(
            "SELECT kind, severity, account, COUNT(*) AS n FROM spt_exception WHERE snapshot_id=? "
            "GROUP BY kind, severity, account "
            "ORDER BY CASE severity WHEN 'blocker' THEN 0 ELSE 1 END, n DESC, kind, account NULLS FIRST",
            (snapshot_id,))]
    finally:
        conn.close()


def list_exceptions(snapshot_id, kind="", severity="", q="", page=1, per_page=100) -> dict:
    clauses, params = ["e.snapshot_id = ?"], [snapshot_id]
    if kind:
        clauses.append("e.kind = ?"); params.append(kind)
    if severity:
        clauses.append("e.severity = ?"); params.append(severity)
    if q:
        clauses.append("(e.account ILIKE ? ESCAPE '\\' OR l.memo ILIKE ? ESCAPE '\\' OR l.id_no ILIKE ? ESCAPE '\\' "
                       "OR l.job_name ILIKE ? ESCAPE '\\' OR e.detail ILIKE ? ESCAPE '\\')")
        params += [_like(q)] * 5
    where = " AND ".join(clauses)
    base = ("FROM spt_exception e LEFT JOIN spt_gl_line l "
            "ON l.snapshot_id = e.snapshot_id AND l.gl_id = e.gl_id WHERE " + where)
    conn = get_conn()
    try:
        total = conn.execute(f"SELECT COUNT(*) {base}", params).fetchone()[0]
        page, pages, offset = _paged(total, page, per_page)
        rows = [dict(r) for r in conn.execute(
            f"SELECT e.kind, e.severity, e.detail, e.account, l.tgl, l.id_no, l.job_name, l.memo, "
            f"l.debit_credit, l.pph_type_raw {base} "
            f"ORDER BY CASE e.severity WHEN 'blocker' THEN 0 ELSE 1 END, e.kind, e.account NULLS FIRST, l.tgl NULLS FIRST "
            f"LIMIT ? OFFSET ?", params + [per_page, offset])]
    finally:
        conn.close()
    return {"rows": rows, "total": total, "page": page, "pages": pages, "per_page": per_page}


def drill_lines(snapshot_id, cats, spt=None, page=1, per_page=100) -> dict:
    """GL lines behind one statement row: lines of `cats`, and of Category SPT `spt` when it is not None."""
    cats = list(cats or [])
    if not cats:
        return {"rows": [], "total": 0, "amount": 0.0, "page": 1, "pages": 1, "per_page": per_page}
    clauses = ["snapshot_id = ?", "category_lk IN (" + ",".join("?" * len(cats)) + ")"]
    params = [snapshot_id, *cats]
    if spt is not None:
        clauses.append("category_spt = ?"); params.append(spt)
    where = " AND ".join(clauses)
    conn = get_conn()
    try:
        total, amount = conn.execute(
            f"SELECT COUNT(*), COALESCE(SUM(debit_credit), 0) FROM spt_gl_line WHERE {where}", params).fetchone()
        page, pages, offset = _paged(total, page, per_page)
        rows = [dict(r) for r in conn.execute(
            f"SELECT tgl, id_no, acc_statutory, acc_management, job_name, memo, debit_credit, category_lk, "
            f"category_spt, pph_type FROM spt_gl_line WHERE {where} ORDER BY tgl NULLS FIRST, gl_id LIMIT ? OFFSET ?",
            params + [per_page, offset])]
    finally:
        conn.close()
    return {"rows": rows, "total": total, "amount": amount, "page": page, "pages": pages,
            "per_page": per_page}
