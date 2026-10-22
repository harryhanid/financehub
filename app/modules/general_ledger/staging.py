# modules/general_ledger/staging.py
"""Staging tables for whole-year replace flows (R21: GL replace_year, SPT take_snapshot).

One fhdb call = one transaction, and one HTTPS request cannot carry a whole GL year (~9k rows x 51
columns). So the rows are uploaded in chunks (<= 1000 rows, well under 1 MB of SQL per call) into a
per-run staging table, and ONE batch then swaps them into the target, writes the log and drops the
staging table. A run that fails before that batch leaves at most an orphan staging table: it is
dropped right away when possible, otherwise by the next run (drop_orphans).
"""
import time
import uuid

PREFIX = "fh_stage_"
CHUNK_ROWS = 1000
CHUNK_CHARS = 512 * 1024          # rough SQL size per chunk call; the HTTPS limit is ~1 MB
ORPHAN_AGE_S = 3600               # older staging tables belong to a dead run, not to a concurrent one


def q(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def new_name(kind: str) -> str:
    return f"{PREFIX}{kind}_{int(time.time())}_{uuid.uuid4().hex[:8]}"


def drop_orphans(conn, kind: str) -> None:
    """Drop staging tables of `kind` left by runs that died more than ORPHAN_AGE_S ago."""
    prefix = f"{PREFIX}{kind}_"
    names = [r[0] for r in conn.execute(
        "SELECT tablename::text FROM pg_tables WHERE schemaname = current_schema() "
        "AND left(tablename, ?) = ?", (len(prefix), prefix))]
    now = time.time()
    stale = []
    for n in names:
        try:
            started = int(n[len(prefix):].split("_")[0])
        except ValueError:
            continue
        if now - started > ORPHAN_AGE_S:
            stale.append(n)
    if stale:
        conn.batch([(f"DROP TABLE IF EXISTS {q(n)}", ()) for n in stale])


def create(conn, name: str, columns) -> None:
    """columns: [(column, postgres type)]; a leading "seq" column keeps the upload order."""
    cols = ", ".join(f"{q(c)} {t}" for c, t in columns)
    conn.batch([
        (f"CREATE UNLOGGED TABLE {q(name)} (\"seq\" bigint NOT NULL, {cols})", ()),
        (f"ALTER TABLE {q(name)} ENABLE ROW LEVEL SECURITY", ()),     # R19: tables made at runtime
    ])


def load(conn, name: str, columns, rows) -> int:
    """Insert `rows` (tuples in `columns` order) in chunks; returns the number of rows sent."""
    col_list = ", ".join(q(c) for c in ("seq", *columns))
    marks = "(" + ",".join("?" * (len(columns) + 1)) + ")"
    n = 0
    chunk, params, size = [], [], 0

    def flush():
        if chunk:
            # Explicit tiny RETURNING: fhdb would append RETURNING * (51 columns back per row, R13).
            # (fh_exec wraps the statement in a CTE, so the "WITH ins AS (INSERT ...)" form is refused.)
            conn.execute(f"INSERT INTO {q(name)} ({col_list}) VALUES {','.join(chunk)} RETURNING NULL AS r",
                         params)

    for row in rows:
        n += 1
        chunk.append(marks)
        params.extend((n, *row))
        size += sum(len(str(v)) + 4 for v in row) + 16
        if len(chunk) >= CHUNK_ROWS or size >= CHUNK_CHARS:
            flush()
            chunk, params, size = [], [], 0
    flush()
    return n


def insert_items(table: str, columns, rows, conflict: str = "") -> list:
    """Batch items inserting `rows` (tuples in `columns` order) into `table`, <= CHUNK_ROWS rows per
    multi-row INSERT, each with a tiny explicit RETURNING (R13). For replace-all flows whose rows all
    fit in one request (Management Report COA / category maps); `conflict` e.g. "ON CONFLICT DO NOTHING"."""
    col_list = ", ".join(q(c) for c in columns)
    marks = "(" + ",".join("?" * len(columns)) + ")"
    rows = list(rows)
    items = []
    for i in range(0, len(rows), CHUNK_ROWS):
        chunk = rows[i:i + CHUNK_ROWS]
        params = [v for row in chunk for v in row]
        items.append((f"INSERT INTO {q(table)} ({col_list}) VALUES {','.join([marks] * len(chunk))} "
                      f"{conflict} RETURNING NULL AS r", params))
    return items


def lock(key: str):
    """Batch item (put it FIRST): serialise flows that replace the same slice (Postgres READ
    COMMITTED does not, unlike SQLite's single writer); held until the batch commits."""
    return ("SELECT pg_advisory_xact_lock(hashtext(?))", (key,))


def guard(name: str, expected: int):
    """Batch item that aborts the batch (division by zero) unless staging holds `expected` rows."""
    return (f"SELECT 1 / (CASE WHEN (SELECT count(*) FROM {q(name)}) = ? THEN 1 ELSE 0 END)", (expected,))


def copy(target: str, stage: str, columns, head_cols=(), head_exprs=()):
    """Batch item: INSERT INTO target SELECT ... FROM stage ORDER BY seq, with no result rows (R13).

    Wrapped in a DO block: a plain INSERT would get RETURNING * appended by fhdb (every row back),
    and fh_exec cannot run "WITH ins AS (INSERT ...) SELECT count(*)" because it wraps it in a CTE.
    `head_cols`/`head_exprs`: extra leading target columns filled by SQL expressions (no parameters)."""
    cols = [q(c) for c in columns]
    sql = (f"INSERT INTO {q(target)} ({', '.join([*map(q, head_cols), *cols])}) "
           f"SELECT {', '.join([*head_exprs, *cols])} FROM {q(stage)} ORDER BY \"seq\"")
    return ("DO '" + "BEGIN " + sql.replace("'", "''") + "; END'", ())


def drop(name: str):
    return (f"DROP TABLE IF EXISTS {q(name)}", ())


def discard(conn, name: str) -> None:
    """Best effort after a failed run; drop_orphans catches what this cannot drop."""
    try:
        conn.execute(*drop(name))
    except Exception:
        pass
