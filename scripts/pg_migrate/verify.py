"""Bandingkan SQLite FinanceHub dengan schema Postgres hasil load_data.py: jumlah baris per tabel dan
`round(sum(col), 2)` per kolom numerik (zero tolerance). Kosong = lulus.

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
from load_data import ALLOWED_SCHEMAS, check_schema, qi, snapshot, source_tables, target_columns  # noqa: E402

NUMERIC_TYPES = ("bigint", "integer", "smallint", "double precision", "real", "numeric")
ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MONEY_OUT = ROOT / "docs" / "pg-migration" / "money-columns.txt"


@dataclass(frozen=True)
class Mismatch:
    table: str
    column: str | None  # None = jumlah baris
    sqlite: object
    pg: object


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


def verify(sqlite_path, backend, schema, columns=None) -> list[Mismatch]:
    check_schema(schema)
    tcols = target_columns(backend, schema)

    def collect(sq):
        tables = source_tables(sq)
        cols = columns if columns is not None else _numeric_cols(tables, tcols)
        by_table = {t: [c for tt, c in cols if tt == t] for t in tables}
        src = {}
        for t in tables:
            exprs = ["count(*)"] + [f"sum({qi(c)})" for c in by_table[t]]
            src[t] = list(sq.execute(f"select {', '.join(exprs)} from {qi(t)}").fetchone())
        return tables, by_table, src

    tables, by_table, src = _with_source(sqlite_path, collect)
    missing = [t for t in tables if t not in tcols]
    out = [Mismatch(t, None, src[t][0], None) for t in missing]
    present = [t for t in tables if t in tcols]
    stmts = []
    for t in present:
        exprs = ["count(*)"] + [f"sum({qi(c)})" for c in by_table[t]]
        stmts.append(f"select {', '.join(exprs)} from {qi(t)}")
    results = backend.execute_batch(stmts, schema) if stmts else []
    for t, res in zip(present, results):
        pg = res["rows"][0]
        if int(pg[0]) != int(src[t][0]):
            out.append(Mismatch(t, None, src[t][0], pg[0]))
        for i, c in enumerate(by_table[t], start=1):
            a, b = _norm(src[t][i]), _norm(pg[i])
            if a != b:
                out.append(Mismatch(t, c, a, b))
    return out


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
        print(f"MISMATCH {m.table}.{m.column or '<rows>'}: sqlite={m.sqlite} pg={m.pg}")
    print(f"{len(mm)} mismatch")
    sys.exit(1 if mm else 0)


if __name__ == "__main__":
    main()
