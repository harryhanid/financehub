"""Baca isi tabel per halaman dengan urutan deterministik (dipakai backup harian dan verify).

`run(sql, params) -> list[list]` adalah satu panggilan baca (fhdb Connection atau backend langsung).
Urutan:
- primary key satu kolom: keyset `where pk > <terakhir> order by pk limit n` (tiap halaman O(n));
- primary key komposit: `order by <kolom pk> limit n offset k`;
- tanpa primary key: `order by <semua kolom> limit n offset k` (baris identik saling tertukar, isinya sama).
Halaman-halaman tidak satu transaksi: tulisan yang terjadi selama pembacaan bisa ikut / tidak ikut.
"""
from typing import Callable, Iterator, Sequence

Run = Callable[[str, Sequence], list]

PAGE_ROWS = 5000
PAGE_CELLS = 200_000  # tabel lebar: halaman diperkecil supaya respons satu panggilan tetap wajar


def qi(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def page_size(ncols: int, page_rows: int = PAGE_ROWS) -> int:
    return max(1, min(page_rows, max(500, PAGE_CELLS // max(1, ncols))))


def table_columns(run: Run, schema: str) -> dict[str, list[tuple[str, str]]]:
    """{tabel: [(kolom, data_type), ...]} urut ordinal, hanya BASE TABLE."""
    rows = run(
        "select c.table_name, c.column_name, c.data_type from information_schema.columns c "
        "join information_schema.tables t on t.table_schema = c.table_schema and t.table_name = c.table_name "
        "where c.table_schema = ? and t.table_type = 'BASE TABLE' order by c.table_name, c.ordinal_position",
        (schema,))
    out: dict = {}
    for table, col, dtype in rows:
        out.setdefault(table, []).append((col, dtype))
    return out


def primary_keys(run: Run, schema: str) -> dict[str, list[str]]:
    """{tabel: [kolom pk urut]}; tabel tanpa pk tidak muncul."""
    rows = run(
        "select c.relname, a.attname from pg_index i "
        "join pg_class c on c.oid = i.indrelid join pg_namespace n on n.oid = c.relnamespace "
        "cross join lateral unnest(i.indkey::int2[]) with ordinality as k(attnum, ord) "
        "join pg_attribute a on a.attrelid = i.indrelid and a.attnum = k.attnum "
        "where i.indisprimary and n.nspname = ? order by c.relname, k.ord",
        (schema,))
    out: dict = {}
    for table, col in rows:
        out.setdefault(table, []).append(col)
    return out


def iter_rows(run: Run, table: str, cols: Sequence[str], pk: Sequence[str], all_cols: Sequence[str],
              page_rows: int = PAGE_ROWS) -> Iterator[list]:
    """Yield baris (list nilai sesuai `cols`) seluruh tabel, halaman demi halaman."""
    cols, pk, all_cols = list(cols), list(pk), list(all_cols)
    n = page_size(len(all_cols), page_rows)
    if len(pk) == 1:
        key = pk[0]
        sel = cols if key in cols else cols + [key]
        ki = sel.index(key)
        head = f"select {', '.join(qi(c) for c in sel)} from {qi(table)}"
        last, first = None, True
        while True:
            if first:
                rows = run(f"{head} order by {qi(key)} limit {n}", ())
            else:
                rows = run(f"{head} where {qi(key)} > ? order by {qi(key)} limit {n}", (last,))
            first = False
            for r in rows:
                yield list(r[:len(cols)])
            if len(rows) < n:
                return
            last = rows[-1][ki]
    order = pk if pk else all_cols
    head = (f"select {', '.join(qi(c) for c in cols)} from {qi(table)} "
            f"order by {', '.join(qi(c) for c in order)}")
    offset = 0
    while True:
        rows = run(f"{head} limit {n} offset {offset}", ())
        for r in rows:
            yield list(r)
        if len(rows) < n:
            return
        offset += n
