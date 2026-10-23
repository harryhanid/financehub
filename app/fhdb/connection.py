"""Objek mirip `sqlite3` (Connection / Cursor / Row) di atas `public.fh_exec`.

Satu panggilan backend = satu transaksi. Tidak ada transaksi lintas panggilan:
- `commit()` tidak melakukan apa-apa (tiap panggilan sudah ter-commit);
- `rollback()` tidak bisa membatalkan tulisan sebelumnya, hanya mencatat warning;
- `executemany`, `executescript`, dan `batch` mengirim semua statement dalam SATU panggilan
  sehingga atomik.

`?` diganti literal oleh `sqlbind.bind`. Nilai tidak dikonversi (timestamp dll. apa adanya).
"""
import logging
import re
import threading
import time
from typing import Iterable, Sequence

from .errors import ProgrammingError
from .sqlbind import _literal, _scan, bind, split_script

logger = logging.getLogger("fhdb")


class _Stats(threading.local):
    """Statistik panggilan backend per thread: jumlah, total detik, dan panggilan terlama."""

    def __init__(self):
        self.calls = 0
        self.seconds = 0.0
        self.max_seconds = 0.0


stats = _Stats()


def reset_stats() -> None:
    stats.calls = 0
    stats.seconds = 0.0
    stats.max_seconds = 0.0


# ---------------------------------------------------------------------------- Row

class Row:
    """Mirip `sqlite3.Row`: akses posisi, akses nama (exact dulu, lalu case-insensitive), dict(row)."""

    __slots__ = ("_keys", "_values")

    def __init__(self, keys: Sequence[str], values: Sequence):
        self._keys = tuple(keys)
        self._values = tuple(values)

    def keys(self) -> list[str]:
        return list(self._keys)

    def _index(self, key: str) -> int:
        try:
            return self._keys.index(key)
        except ValueError:
            pass
        low = key.lower()
        for i, k in enumerate(self._keys):
            if k.lower() == low:
                return i
        raise IndexError("No item with that key")

    def __getitem__(self, key):
        if isinstance(key, str):
            return self._values[self._index(key)]
        return self._values[key]

    def __len__(self):
        return len(self._values)

    def __iter__(self):
        return iter(self._values)

    def __eq__(self, other):
        if isinstance(other, Row):
            return self._keys == other._keys and self._values == other._values
        return NotImplemented

    def __hash__(self):
        return hash((self._keys, self._values))

    def __repr__(self):
        return f"Row({dict(zip(self._keys, self._values))!r})"


# ---------------------------------------------------------------------------- Cursor

class Cursor:
    arraysize = 1

    def __init__(self, connection: "Connection"):
        self.connection = connection
        self._reset()

    def _reset(self):
        self._columns: list[str] | None = None
        self._rows: list[Row] = []
        self._pos = 0
        self.rowcount = -1
        self.lastrowid: int | None = None

    def _load(self, columns, rows, rowcount, lastrowid):
        self._columns = list(columns) if columns is not None else None
        self._rows = [Row(self._columns, r) for r in rows] if columns is not None else []
        self._pos = 0
        self.rowcount = rowcount
        self.lastrowid = lastrowid
        return self

    @property
    def description(self):
        if self._columns is None:
            return None
        return tuple((c, None, None, None, None, None, None) for c in self._columns)

    def fetchone(self) -> Row | None:
        if self._pos >= len(self._rows):
            return None
        row = self._rows[self._pos]
        self._pos += 1
        return row

    def fetchmany(self, size: int | None = None) -> list[Row]:
        size = self.arraysize if size is None else size
        out = self._rows[self._pos:self._pos + size]
        self._pos += len(out)
        return out

    def fetchall(self) -> list[Row]:
        out = self._rows[self._pos:]
        self._pos = len(self._rows)
        return out

    def __iter__(self):
        while True:
            row = self.fetchone()
            if row is None:
                return
            yield row

    def execute(self, sql: str, params: Sequence = ()) -> "Cursor":
        self.connection._run([(sql, params)], [self])
        return self

    def executemany(self, sql: str, seq: Iterable[Sequence]) -> "Cursor":
        self.connection._executemany_into(self, sql, seq)
        return self

    def executescript(self, script: str) -> "Cursor":
        self.connection._executescript_into(self, script)
        return self

    def close(self):
        self._reset()


# ---------------------------------------------------------------------------- statement plan

_PRAGMA_TABLE_INFO = re.compile(
    r"""^\s*pragma\s+table_info\s*\(\s*["'`\[]?([^"'`\])]+?)["'`\]]?\s*\)\s*;?\s*$""",
    re.IGNORECASE | re.DOTALL,
)
_RETURNING = re.compile(r"\breturning\b", re.IGNORECASE)
_WRITE_WORDS = re.compile(r"\b(insert|update|delete|merge)\b", re.IGNORECASE)
_READ_FIRST = {"select", "values", "explain", "show", "table"}

_TABLE_INFO_SQL = (
    "select (c.ordinal_position - 1)::int as cid, c.column_name::text as name, "
    "c.data_type::text as type, (c.is_nullable = 'NO')::int as notnull, "
    "c.column_default::text as dflt_value, "
    "coalesce((select k.n::int from pg_index i "
    "cross join lateral unnest(i.indkey::int2[]) with ordinality as k(attnum, n) "
    "join pg_attribute a on a.attrelid = i.indrelid and a.attnum = k.attnum "
    "where i.indisprimary and i.indrelid = format('%I.%I', c.table_schema, c.table_name)::regclass "
    "and a.attname = c.column_name), 0) as pk "
    "from information_schema.columns c "
    "where c.table_schema = current_schema() and c.table_name = "
    "(case when exists (select 1 from information_schema.columns x "
    "where x.table_schema = current_schema() and x.table_name = {name}) "
    "then {name} else lower({name}) end) "
    "order by c.ordinal_position"
)


def _code_text(sql: str) -> str:
    """Hanya potongan kode (tanpa literal, identifier ber-quote, dan komentar)."""
    return " ".join(text for kind, text in _scan(sql) if kind == "code")


def _first_word(sql: str) -> str:
    m = re.match(r"\s*([A-Za-z_]+)", _code_text(sql))
    return m.group(1).lower() if m else ""


def _strip_tail(sql: str) -> str:
    """Buang komentar dan `;` di akhir supaya teks bisa disambung (mis. `RETURNING *`)."""
    out = []
    for kind, text in _scan(sql):
        if kind == "comment":
            out.append(" ")
        else:
            out.append(text)
    s = "".join(out).rstrip()
    while s.endswith(";"):
        s = s[:-1].rstrip()
    return s


class _Plan:
    """Satu statement siap kirim. kind: 'noop' | 'rows' (tampilkan baris) | 'insert_auto' | 'write'."""

    __slots__ = ("stmt", "kind", "is_write")

    def __init__(self, stmt: str | None, kind: str, is_write: bool):
        self.stmt, self.kind, self.is_write = stmt, kind, is_write


def _plan(sql: str, params: Sequence | None) -> _Plan:
    first = _first_word(sql)
    if first == "pragma":
        m = _PRAGMA_TABLE_INFO.match(sql)
        if m:
            return _Plan(_TABLE_INFO_SQL.format(name=_literal(m.group(1).strip())), "rows", False)
        return _Plan(None, "noop", False)
    stmt = bind(sql, params)
    code = _code_text(stmt)
    has_returning = bool(_RETURNING.search(code))
    if first in _READ_FIRST or (first == "with" and not _WRITE_WORDS.search(code)):
        return _Plan(stmt, "rows", False)
    if first == "insert" and not has_returning:
        return _Plan(_strip_tail(stmt) + " RETURNING *", "insert_auto", True)
    return _Plan(stmt, "rows" if has_returning else "write", True)


def _lastrowid(columns, rows) -> int | None:
    if not rows or not columns or "id" not in columns:
        return None
    v = rows[-1][columns.index("id")]
    return v if isinstance(v, int) and not isinstance(v, bool) else None


# ---------------------------------------------------------------------------- Connection

class Connection:
    def __init__(self, backend, schema: str):
        self._backend = backend
        self._schema = schema
        self._closed = False
        self._dirty = False  # ada tulisan sejak commit/rollback terakhir
        self.row_factory = None  # diterima demi kompatibilitas (`conn.row_factory = sqlite3.Row`)

    def __repr__(self):
        return f"Connection(backend={self._backend!r}, schema={self._schema!r})"

    def _check_open(self):
        if self._closed:
            raise ProgrammingError("Cannot operate on a closed database.")

    def _send(self, plans: list[_Plan]) -> list[dict | None]:
        """Kirim semua plan non-noop dalam satu panggilan; hasil sejajar dengan `plans` (None = noop)."""
        stmts = [p.stmt for p in plans if p.kind != "noop"]
        results: list = []
        if stmts:
            stats.calls += 1
            t0 = time.perf_counter()
            try:
                results = self._backend.execute_batch(stmts, self._schema)
            finally:
                dt = time.perf_counter() - t0
                stats.seconds += dt
                if dt > stats.max_seconds:
                    stats.max_seconds = dt
        if any(p.is_write for p in plans):
            self._dirty = True
        it = iter(results)
        return [None if p.kind == "noop" else next(it) for p in plans]

    @staticmethod
    def _fill(cur: Cursor, plan: _Plan, res: dict | None) -> Cursor:
        if res is None:
            return cur._load(None, [], -1, None)
        columns, rows = res.get("columns"), res.get("rows") or []
        if plan.kind == "insert_auto":
            return cur._load(None, [], len(rows), _lastrowid(columns, rows))
        if "rowcount" in res:
            return cur._load(None, [], res["rowcount"], None)
        if plan.is_write:  # tulisan dengan RETURNING eksplisit
            return cur._load(columns, rows, len(rows), _lastrowid(columns, rows))
        return cur._load(columns, rows, -1, None)

    def _run(self, items: list[tuple[str, Sequence]], cursors: list[Cursor]) -> list[Cursor]:
        self._check_open()
        plans = [_plan(sql, params) for sql, params in items]
        for cur, plan, res in zip(cursors, plans, self._send(plans)):
            self._fill(cur, plan, res)
        return cursors

    # --- API sqlite3 ---

    def cursor(self) -> Cursor:
        self._check_open()
        return Cursor(self)

    def execute(self, sql: str, params: Sequence = ()) -> Cursor:
        return self._run([(sql, params)], [Cursor(self)])[0]

    def batch(self, items: list[tuple[str, Sequence]]) -> list[Cursor]:
        """Semua item dalam SATU panggilan backend (atomik)."""
        items = list(items)
        return self._run(items, [Cursor(self) for _ in items])

    def _executemany_into(self, cur: Cursor, sql: str, seq: Iterable[Sequence]) -> Cursor:
        self._check_open()
        plans = [_plan(sql, params) for params in seq]
        results = self._send(plans)
        rowcount, lastrowid = 0, None
        tmp = Cursor(self)
        for plan, res in zip(plans, results):
            self._fill(tmp, plan, res)
            if tmp.rowcount > 0:
                rowcount += tmp.rowcount
            if tmp.lastrowid is not None:
                lastrowid = tmp.lastrowid
        return cur._load(None, [], rowcount, lastrowid)

    def executemany(self, sql: str, seq: Iterable[Sequence]) -> Cursor:
        return self._executemany_into(Cursor(self), sql, seq)

    def _executescript_into(self, cur: Cursor, script: str) -> Cursor:
        self._check_open()
        plans = []
        for stmt in split_script(script):
            if _first_word(stmt) == "pragma":
                continue
            # Script tidak di-bind (sama seperti sqlite3.executescript): `?` dibiarkan apa adanya.
            plans.append(_Plan(stmt, "write", _first_word(stmt) not in _READ_FIRST))
        self._send(plans)
        return cur._load(None, [], -1, None)

    def executescript(self, script: str) -> Cursor:
        return self._executescript_into(Cursor(self), script)

    def commit(self) -> None:
        self._dirty = False

    def rollback(self) -> None:
        if self._dirty:
            logger.warning("rollback setelah tulisan: tidak bisa dibatalkan (HTTPS autocommit)")
        self._dirty = False

    def close(self) -> None:
        self._closed = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type is None:
            self.commit()
        else:
            self.rollback()
        return False
