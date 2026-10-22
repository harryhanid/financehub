"""Bandingkan SQLite FinanceHub dengan schema Postgres hasil load_data.py: jumlah baris per tabel dan
jumlah (sum) per kolom numerik dibulatkan 2 desimal (zero tolerance). Kosong = lulus.

Penjumlahan tidak bergantung urutan (R39): nilai kolom diambil dari kedua sisi (Postgres per halaman,
fhdb.paging) lalu dijumlah di Python -- kolom integer eksak (int), kolom float dengan math.fsum -- dan
dibandingkan setelah Decimal 2 desimal ROUND_HALF_UP. `sum()` SQL tidak dipakai: Postgres menjumlah
float8 naif menurut urutan heap, SQLite (>= 3.43) terkompensasi, hasilnya bisa beda di sen.

Teks: per tabel satu checksum sha256 atas SEMUA kolom target bertipe text/varchar/char, dihitung di
Python dari nilai yang diambil di kedua sisi (SQLite lewat sqlite3 + convert(), Postgres per halaman lewat
fhdb.paging). Baris diurutkan di Python menurut primary key Postgres (tabel tanpa pk: kolom teks lalu
seluruh baris), jadi urutan/collation database tidak berpengaruh. NULL dan '' berbeda. Mismatch dilaporkan
per tabel dengan kunci baris pertama yang berbeda (row_key). Tabel yang jumlah barisnya sudah beda tidak
dicek teksnya (mismatch baris sudah dilaporkan).

Kolom yang dibandingkan (R35): SEMUA kolom target bertipe bigint/integer/smallint/double precision/real/
numeric di setiap tabel sumber (kecuali refresh_tokens), selain kolom `id`, kolom identity, dan kolom yang
namanya berakhiran `_id`. Daftar final dicetak dan ditulis ke --money-out.

Usage:
  python scripts/pg_migrate/verify.py --sqlite C:/FinanceHub/app/finance_hub.db \\
      --backend pg --dsn postgresql://postgres@127.0.0.1:54340/postgres --schema financehub_test \\
      [--money-out docs/pg-migration/money-columns.txt]
Exit code 1 kalau ada mismatch.
"""
import argparse
import hashlib
import json
import math
import os
import shutil
import sqlite3
import sys
import tempfile
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import load_data  # noqa: E402
from load_data import (ALLOWED_SCHEMAS, FLOAT_TYPES, INT_TYPES, TEXT_TYPES, check_schema, convert, qi,  # noqa: E402
                       snapshot, source_columns, source_tables, target_columns)

from fhdb import paging  # noqa: E402  (APP_DIR sudah di sys.path lewat load_data)
from fhdb.sqlbind import bind  # noqa: E402

NUMERIC_TYPES = ("bigint", "integer", "smallint", "double precision", "real", "numeric")
TEXT_CHECK = "<text checksum>"
ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MONEY_OUT = ROOT / "docs" / "pg-migration" / "money-columns.txt"


@dataclass(frozen=True)
class Mismatch:
    table: str
    column: str | None  # None = jumlah baris
    sqlite: object
    pg: object
    row_key: tuple | None = None  # checksum teks: kunci baris pertama yang berbeda


def _numeric_cols(tables, tcols) -> list[tuple[str, str]]:
    out = []
    for t in tables:
        for col, (dtype, ident) in tcols.get(t, {}).items():
            low = col.lower()
            if dtype in NUMERIC_TYPES and not ident and low != "id" and not low.endswith("_id"):
                out.append((t, col))
    return out


def _with_source(sqlite_path, fn):
    tmpdir = tempfile.mkdtemp(prefix="fh_verify_")
    try:
        sq = sqlite3.connect(snapshot(sqlite_path, tmpdir))
        try:
            return fn(sq)
        finally:
            sq.close()
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def numeric_columns(sqlite_path, backend, schema) -> list[tuple[str, str]]:
    check_schema(schema)
    tables = _with_source(sqlite_path, source_tables)
    return _numeric_cols(tables, target_columns(backend, schema))


def _norm(v):
    """round(sum, 2) dengan aturan yang sama untuk kedua sisi: sum mentah (float -> repr shortest
    round-trip, int/Decimal apa adanya) -> Decimal 2 desimal ROUND_HALF_UP. None = tabel kosong / NULL.

    Pembulatan tidak dilakukan di SQL: di Postgres `round(sum(x)::numeric, 2)` salah karena float8::numeric
    hanya menyimpan 15 digit signifikan (465986724616.1347 -> 465986724616.135 -> .14, SQLite -> .13).
    """
    if v is None:
        return None
    return Decimal(repr(v) if isinstance(v, float) else str(v)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def sum_values(values, dtype: str):
    """Jumlah tak bergantung urutan; None dilewati, tanpa nilai -> None (seperti SQL sum).
    Kolom integer: int eksak. Kolom float: math.fsum (hasil dibulatkan benar). numeric: Decimal eksak."""
    vals = [v for v in values if v is not None]
    if not vals:
        return None
    if dtype in INT_TYPES:
        return sum(int(v) for v in vals)
    if dtype == "numeric":
        return sum(Decimal(repr(v) if isinstance(v, float) else str(v)) for v in vals)
    if dtype in FLOAT_TYPES:
        return math.fsum(float(v) for v in vals)
    raise ValueError(f"tipe {dtype!r} bukan numerik")


def pg_run(backend, schema):
    """`run(sql, params) -> rows` untuk fhdb.paging di atas backend (satu panggilan per halaman)."""
    return lambda sql, params: backend.execute_batch([bind(sql, params)], schema)[0]["rows"]


def pg_stats(backend, schema, by_table, tcols) -> dict[str, tuple[int, list]]:
    """{tabel: (jumlah baris, [sum per kolom by_table[t]])} dari Postgres; nilai diambil per halaman."""
    tables = list(by_table)
    if not tables:
        return {}
    run = pg_run(backend, schema)
    res = backend.execute_batch([f"select count(*) from {qi(t)}" for t in tables], schema)
    counts = {t: int(r["rows"][0][0]) for t, r in zip(tables, res)}
    pks = paging.primary_keys(run, schema) if any(by_table.values()) else {}
    out = {}
    for t in tables:
        cols = by_table[t]
        sums = []
        if cols:
            cols_vals = [[] for _ in cols]
            for row in paging.iter_rows(run, t, cols, pks.get(t, []), list(tcols[t])):
                for i, v in enumerate(row):
                    cols_vals[i].append(v)
            sums = [sum_values(vs, tcols[t][c][0]) for c, vs in zip(cols, cols_vals)]
        out[t] = (counts[t], sums)
    return out


def _canon(v, dtype):
    """Nilai kanonik untuk kunci/encoding: angka float -> repr(float) (int/float sama), lainnya apa adanya."""
    if v is None:
        return None
    if dtype in FLOAT_TYPES:
        return repr(float(v))
    if dtype in INT_TYPES:
        return int(v)
    return v


def _enc(values) -> str:
    return json.dumps(list(values), ensure_ascii=False, separators=(",", ":"))


def _sort_part(v):
    return (0, "", "") if v is None else (1, type(v).__name__, v)


def text_plan(tcols, pks, table, src_cols=None):
    """(kolom diambil, indeks kunci, indeks teks, dtypes) atau None kalau tabel tanpa kolom teks."""
    cols = [c for c in tcols[table] if src_cols is None or c in src_cols]
    text = [c for c in cols if tcols[table][c][0] in TEXT_TYPES]
    if not text:
        return None
    pk = [c for c in pks.get(table, []) if c in cols]
    return cols, pk, text


def text_rows(rows, cols, pk, text, dtypes):
    """[(sort key, kunci baris, digest baris)] urut; rows = list nilai sesuai cols (sudah dikonversi)."""
    ki = [cols.index(c) for c in pk]
    ti = [cols.index(c) for c in text]
    out = []
    for r in rows:
        canon = [_canon(v, d) for v, d in zip(r, dtypes)]
        texts = [canon[i] for i in ti]
        if ki:
            key = tuple(canon[i] for i in ki)
            sort = tuple(_sort_part(v) for v in key)
        else:  # tanpa pk: kolom teks dulu, lalu seluruh baris
            key = tuple(canon)
            sort = (tuple(_sort_part(v) for v in texts), _enc(canon))
        out.append((sort, key, hashlib.sha256(_enc(texts).encode("utf-8")).hexdigest()))
    out.sort(key=lambda x: x[0])
    return out


def text_checksum(trows) -> str:
    h = hashlib.sha256()
    for _, _, d in trows:
        h.update(d.encode("ascii"))
    return h.hexdigest()


def compare_text(table, src_rows, pg_rows) -> Mismatch | None:
    a, b = text_checksum(src_rows), text_checksum(pg_rows)
    if a == b:
        return None
    key = None
    for x, y in zip(src_rows, pg_rows):
        if x[1:] != y[1:]:
            key = x[1]
            break
    else:
        longer = src_rows if len(src_rows) > len(pg_rows) else pg_rows
        key = longer[min(len(src_rows), len(pg_rows))][1]
    return Mismatch(table, TEXT_CHECK, a, b, key)


def compare(expected: dict, actual: dict, by_table) -> list[Mismatch]:
    """expected/actual: {tabel: (rows, [sum per kolom])}; tabel yang tidak ada di actual -> mismatch baris."""
    out = []
    for t, (n, sums) in expected.items():
        if t not in actual:
            out.append(Mismatch(t, None, n, None))
            continue
        pn, psums = actual[t]
        if int(pn) != int(n):
            out.append(Mismatch(t, None, n, pn))
        for c, a, b in zip(by_table[t], sums, psums):
            a, b = _norm(a), _norm(b)
            if a != b:
                out.append(Mismatch(t, c, a, b))
    return out


def verify(sqlite_path, backend, schema, columns=None) -> list[Mismatch]:
    check_schema(schema)
    tcols = target_columns(backend, schema)

    def collect(sq):
        tables = source_tables(sq)
        cols = columns if columns is not None else _numeric_cols(tables, tcols)
        by_table = {t: [c for tt, c in cols if tt == t] for t in tables}
        src = {}
        for t in tables:
            n = sq.execute(f"select count(*) from {qi(t)}").fetchone()[0]
            sums = []
            for c in by_table[t]:
                dtype = tcols[t][c][0]
                vals = (convert(v, dtype, f"{t}.{c}") for (v,) in sq.execute(f"select {qi(c)} from {qi(t)}"))
                sums.append(sum_values(vals, dtype))
            src[t] = (n, sums)
        return by_table, src

    pks = paging.primary_keys(pg_run(backend, schema), schema)

    def collect_text(sq):
        out = {}
        for t in source_tables(sq):
            if t not in tcols:
                continue
            plan = text_plan(tcols, pks, t, set(source_columns(sq, t)))
            if plan is None:
                continue
            cols, pk, text = plan
            dtypes = [tcols[t][c][0] for c in cols]
            rows = ([convert(v, d, f"{t}.{c}") for v, d, c in zip(r, dtypes, cols)]
                    for r in sq.execute(f"select {', '.join(qi(c) for c in cols)} from {qi(t)}"))
            out[t] = (plan, dtypes, text_rows(rows, cols, pk, text, dtypes))
        return out

    by_table, src = _with_source(sqlite_path, collect)
    present = {t: by_table[t] for t in by_table if t in tcols}
    actual = pg_stats(backend, schema, present, tcols)
    mm = compare(src, actual, by_table)
    count_bad = {m.table for m in mm if m.column is None}
    run = pg_run(backend, schema)
    for t, ((cols, pk, text), dtypes, src_rows) in sorted(_with_source(sqlite_path, collect_text).items()):
        if t in count_bad:
            continue
        pg_rows = text_rows(paging.iter_rows(run, t, cols, pks.get(t, []), list(tcols[t])), cols, pk, text, dtypes)
        m = compare_text(t, src_rows, pg_rows)
        if m:
            mm.append(m)
    return mm


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sqlite", required=True)
    ap.add_argument("--schema", required=True, choices=ALLOWED_SCHEMAS)
    ap.add_argument("--backend", required=True, choices=("pg", "http"))
    ap.add_argument("--dsn", default=os.environ.get("FH_PG_DSN", ""))
    ap.add_argument("--money-out", default=None,
                    help=f"tulis daftar kolom numerik yang dibandingkan (mis. {DEFAULT_MONEY_OUT})")
    args = ap.parse_args(argv)
    backend = load_data.make_backend(args.backend, args.dsn)
    try:
        cols = numeric_columns(args.sqlite, backend, args.schema)
        print(f"Kolom numerik dibandingkan ({len(cols)}):")
        for t, c in cols:
            print(f"  {t}.{c}")
        if args.money_out:
            header = (f"# Numeric columns compared by scripts/pg_migrate/verify.py ({len(cols)} kolom; DIHASILKAN)",
                      f"# Tipe target: {', '.join(NUMERIC_TYPES)}; kecuali `id`, identity, dan `*_id`")
            lines = list(header) + [f"{t}.{c}" for t, c in cols]
            Path(args.money_out).write_text("\n".join(lines) + "\n", encoding="utf-8")
        mm = verify(args.sqlite, backend, args.schema, columns=cols)
    finally:
        backend.close()
    for m in mm:
        key = f" baris pertama berbeda={m.row_key!r}" if m.row_key is not None else ""
        print(f"MISMATCH {m.table}.{m.column or '<rows>'}: sqlite={m.sqlite} pg={m.pg}{key}")
    print(f"{len(mm)} mismatch")
    sys.exit(1 if mm else 0)


if __name__ == "__main__":
    main()
