"""Muat snapshot SQLite FinanceHub ke schema Postgres (skema dari app/db_migrations sudah diterapkan).

Usage:
  python scripts/pg_migrate/load_data.py --sqlite C:/FinanceHub/app/finance_hub.db \\
      --backend pg --dsn postgresql://postgres@127.0.0.1:54340/postgres --schema financehub_test
  python scripts/pg_migrate/load_data.py --sqlite ... --backend http --schema financehub_staging

Alur `load()`:
1. Snapshot: `sqlite3.backup` dari sumber (dibuka read-only) ke file sementara; sumber tidak pernah ditulis.
2. Baca kolom target (information_schema) dan FK target (pg_constraint). Semua tabel sumber kecuali
   `refresh_tokens` harus ada di target, semua kolom sumber harus ada di tabel target.
3. Cek orphan per FK target (di snapshot). Ada orphan -> OrphanError, belum ada yang ditulis.
4. Bangun semua INSERT (literal via fhdb.sqlbind) dengan konversi nilai ke tipe kolom target tanpa
   kehilangan nilai (angka di kolom text -> teks; teks angka di kolom bigint/double -> angka; nilai yang
   tidak bisa dikonversi tanpa rugi -> ValueError). Belum ada yang ditulis.
5. Satu panggilan: `TRUNCATE <semua tabel> RESTART IDENTITY CASCADE`.
6. INSERT per chunk (default 500 baris, dipotong lebih kecil kalau teks SQL > MAX_STMT_BYTES), satu
   statement per panggilan, tabel diurutkan induk dulu (FK dicek per statement).
7. Satu panggilan: `setval(pg_get_serial_sequence(...), coalesce(max(id),0)+1, false)` per kolom identity.

Langkah 5-7 tidak satu transaksi: kalau gagal di tengah, jalankan ulang (langkah 5 mengosongkan lagi).
Catatan: TRUNCATE ... CASCADE ikut mengosongkan refresh_tokens (FK ke users) -- sesi login lama hangus.
"""
import argparse
import math
import os
import shutil
import sqlite3
import sys
import tempfile
import time
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[2] / "app"
sys.path.insert(0, str(APP_DIR))

from fhdb.sqlbind import bind  # noqa: E402

ALLOWED_SCHEMAS = ("financehub", "financehub_staging", "financehub_test")
SKIP_TABLES = ("refresh_tokens",)
MAX_STMT_BYTES = 256_000  # jauh di bawah ~1 MB per panggilan HTTPS

INT_TYPES = ("bigint", "integer", "smallint")
FLOAT_TYPES = ("double precision", "real", "numeric")
TEXT_TYPES = ("text", "character varying", "character")


class OrphanError(Exception):
    pass


def check_schema(schema):
    if schema not in ALLOWED_SCHEMAS:
        raise ValueError(f"schema {schema!r} tidak diizinkan (hanya {', '.join(ALLOWED_SCHEMAS)})")


def qi(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def snapshot(sqlite_path: str, dest_dir: str) -> str:
    """Salin konsisten database sumber (dibuka read-only) ke file di dest_dir lewat sqlite3.backup."""
    if not os.path.exists(sqlite_path):
        raise FileNotFoundError(sqlite_path)
    dest = os.path.join(dest_dir, "snapshot.db")
    src = sqlite3.connect(f"file:{Path(sqlite_path).resolve().as_posix()}?mode=ro", uri=True)
    try:
        dst = sqlite3.connect(dest)
        try:
            src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()
    return dest


def source_tables(sq) -> list[str]:
    rows = sq.execute(
        "select name from sqlite_master where type='table' and name not like 'sqlite_%' order by name").fetchall()
    return [r[0] for r in rows if r[0] not in SKIP_TABLES]


def source_columns(sq, table) -> list[str]:
    return [r[1] for r in sq.execute(f"pragma table_info({qi(table)})").fetchall()]


def target_columns(backend, schema) -> dict[str, dict[str, tuple[str, bool]]]:
    """{table: {column: (data_type, is_identity)}} untuk tabel dasar schema target."""
    res = backend.execute_batch([bind(
        "select c.table_name, c.column_name, c.data_type, c.is_identity "
        "from information_schema.columns c join information_schema.tables t "
        "on t.table_schema = c.table_schema and t.table_name = c.table_name "
        "where c.table_schema = ? and t.table_type = 'BASE TABLE' order by c.table_name, c.ordinal_position",
        (schema,))], schema)[0]
    out: dict = {}
    for table, col, dtype, ident in res["rows"]:
        out.setdefault(table, {})[col] = (dtype, ident == "YES")
    return out


def target_fks(backend, schema) -> list[dict]:
    """FK satu kolom di schema target: child, col, parent, pcol, validated."""
    res = backend.execute_batch([bind(
        "select cl.relname, a.attname, pl.relname, pa.attname, con.convalidated, "
        "array_length(con.conkey, 1) "
        "from pg_constraint con "
        "join pg_namespace n on n.oid = con.connamespace "
        "join pg_class cl on cl.oid = con.conrelid "
        "join pg_class pl on pl.oid = con.confrelid "
        "join pg_attribute a on a.attrelid = con.conrelid and a.attnum = con.conkey[1] "
        "join pg_attribute pa on pa.attrelid = con.confrelid and pa.attnum = con.confkey[1] "
        "where con.contype = 'f' and n.nspname = ? order by cl.relname, a.attname",
        (schema,))], schema)[0]
    fks = []
    for child, col, parent, pcol, validated, nkeys in res["rows"]:
        if nkeys != 1:
            raise NotImplementedError(f"FK multi-kolom {child}.{col} belum didukung")
        fks.append({"child": child, "col": col, "parent": parent, "pcol": pcol, "validated": bool(validated)})
    return fks


def find_orphans(sq, tables, fks) -> list[str]:
    """Pesan per FK yang punya baris orphan di snapshot (hanya FK antar tabel yang dimuat)."""
    loaded = set(tables)
    problems = []
    for fk in fks:
        if fk["child"] not in loaded:
            continue
        if fk["parent"] not in loaded:
            problems.append(f"{fk['child']}.{fk['col']} -> {fk['parent']}: tabel induk tidak ada di sumber")
            continue
        n = sq.execute(
            f"select count(*) from {qi(fk['child'])} c where c.{qi(fk['col'])} is not null and not exists "
            f"(select 1 from {qi(fk['parent'])} p where p.{qi(fk['pcol'])} = c.{qi(fk['col'])})").fetchone()[0]
        if n:
            kind = "VALID" if fk["validated"] else "NOT VALID (insert tetap ditolak)"
            problems.append(f"{fk['child']}.{fk['col']} -> {fk['parent']}({fk['pcol']}) [{kind}]: {n} baris orphan")
    return problems


def convert(value, dtype: str, where: str):
    """Konversi nilai SQLite ke tipe kolom target tanpa kehilangan nilai; ValueError kalau tidak bisa."""
    if value is None:
        return None
    if isinstance(value, (bytes, bytearray, memoryview)):
        raise ValueError(f"{where}: BLOB tidak didukung")
    if dtype in TEXT_TYPES:
        if isinstance(value, str):
            return value
        return str(value) if isinstance(value, int) else repr(float(value))
    if dtype in INT_TYPES:
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            if math.isfinite(value) and value.is_integer():
                return int(value)
            raise ValueError(f"{where}: {value!r} bukan bilangan bulat (kolom {dtype})")
        s = value.strip()
        try:
            return int(s)
        except ValueError:
            pass
        try:
            f = float(s)
        except ValueError:
            raise ValueError(f"{where}: teks {value!r} bukan angka (kolom {dtype})") from None
        if math.isfinite(f) and f.is_integer() and abs(f) < 2 ** 53:
            return int(f)
        raise ValueError(f"{where}: teks {value!r} bukan bilangan bulat (kolom {dtype})")
    if dtype in FLOAT_TYPES:
        if isinstance(value, (int, float)):
            return value
        try:
            return float(value.strip())
        except ValueError:
            raise ValueError(f"{where}: teks {value!r} bukan angka (kolom {dtype})") from None
    raise ValueError(f"{where}: tipe target {dtype!r} tidak didukung loader")


def insert_order(tables, fks) -> list[str]:
    """Urutan topologis: tabel induk sebelum anak (FK dicek per statement)."""
    loaded = set(tables)
    deps = {t: set() for t in tables}
    for fk in fks:
        if fk["child"] in loaded and fk["parent"] in loaded and fk["child"] != fk["parent"]:
            deps[fk["child"]].add(fk["parent"])
    order, done = [], set()
    while len(order) < len(tables):
        ready = sorted(t for t in tables if t not in done and deps[t] <= done)
        if not ready:
            raise ValueError(f"siklus FK di antara: {sorted(set(tables) - done)}")
        order.extend(ready)
        done.update(ready)
    return order


def build_inserts(sq, table, cols, types, chunk) -> tuple[list[str], int]:
    head = f"insert into {qi(table)} ({', '.join(qi(c) for c in cols)}) values "
    row_sql = "(" + ", ".join("?" for _ in cols) + ")"
    has_rowid = True
    try:
        cur = sq.execute(f"select {', '.join(qi(c) for c in cols)} from {qi(table)} order by rowid")
    except sqlite3.OperationalError:
        has_rowid = False
    if not has_rowid:
        cur = sq.execute(f"select {', '.join(qi(c) for c in cols)} from {qi(table)}")
    stmts, parts, size, n = [], [], len(head), 0
    for row in cur:
        n += 1
        vals = [convert(v, types[i], f"{table}.{cols[i]} (baris {n})") for i, v in enumerate(row)]
        lit = bind(row_sql, vals)
        nbytes = len(lit.encode("utf-8")) + 2
        if parts and (len(parts) >= chunk or size + nbytes > MAX_STMT_BYTES):
            stmts.append(head + ", ".join(parts))
            parts, size = [], len(head)
        parts.append(lit)
        size += nbytes
    if parts:
        stmts.append(head + ", ".join(parts))
    return stmts, n


def load(sqlite_path: str, backend, schema: str, chunk: int = 500, log=None) -> dict[str, int]:
    check_schema(schema)
    log = log or (lambda msg: None)
    tmpdir = tempfile.mkdtemp(prefix="fh_load_")
    try:
        snap = snapshot(sqlite_path, tmpdir)
        sq = sqlite3.connect(snap)
        try:
            tables = source_tables(sq)
            tcols = target_columns(backend, schema)
            missing = [t for t in tables if t not in tcols]
            if missing:
                raise ValueError(f"tabel sumber tidak ada di schema {schema}: {missing}")
            fks = target_fks(backend, schema)
            problems = find_orphans(sq, tables, fks)
            if problems:
                raise OrphanError("baris orphan terhadap FK target (data tidak dihapus, tidak ada yang ditulis):\n  "
                                  + "\n  ".join(problems))
            plan, counts = [], {}
            for t in insert_order(tables, fks):
                cols = source_columns(sq, t)
                extra = [c for c in cols if c not in tcols[t]]
                if extra:
                    raise ValueError(f"kolom sumber {t}.{extra} tidak ada di target")
                stmts, n = build_inserts(sq, t, cols, [tcols[t][c][0] for c in cols], chunk)
                plan.append((t, stmts))
                counts[t] = n
        finally:
            sq.close()
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    log(f"truncate {len(tables)} tabel")
    backend.execute_batch(
        [f"truncate {', '.join(qi(t) for t in sorted(tables))} restart identity cascade"], schema)
    for t, stmts in plan:
        for s in stmts:
            backend.execute_batch([s], schema)
        log(f"  {t}: {counts[t]} baris, {len(stmts)} panggilan")
    seq = []
    for t in sorted(tables):
        for col, (_dtype, ident) in tcols[t].items():
            if ident:
                seq.append(
                    f"select setval(pg_get_serial_sequence({bind('?', (qi(schema) + '.' + qi(t),))}, "
                    f"{bind('?', (col,))}), coalesce(max({qi(col)}), 0) + 1, false) from {qi(t)}")
    if seq:
        backend.execute_batch(seq, schema)
    log(f"setval {len(seq)} identity")
    return counts


def make_backend(kind, dsn):
    from fhdb.backends import HttpBackend, PgBackend

    if kind == "pg":
        if not dsn:
            sys.exit("--dsn (atau env FH_PG_DSN) wajib untuk backend pg")
        return PgBackend(dsn)
    from dotenv import load_dotenv

    load_dotenv(APP_DIR / ".env")
    url, key = os.environ.get("SUPABASE_URL", ""), os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not url or not key:
        sys.exit("SUPABASE_URL / SUPABASE_SERVICE_KEY belum di-set (app/.env)")
    return HttpBackend(url, key, timeout=120.0)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sqlite", required=True)
    ap.add_argument("--schema", required=True, choices=ALLOWED_SCHEMAS)
    ap.add_argument("--backend", required=True, choices=("pg", "http"))
    ap.add_argument("--dsn", default=os.environ.get("FH_PG_DSN", ""))
    ap.add_argument("--chunk", type=int, default=500)
    args = ap.parse_args(argv)
    backend = make_backend(args.backend, args.dsn)
    t0 = time.perf_counter()
    try:
        counts = load(args.sqlite, backend, args.schema, chunk=args.chunk, log=print)
    finally:
        backend.close()
    print(f"Selesai: {len(counts)} tabel, {sum(counts.values())} baris, {time.perf_counter() - t0:.1f} detik")


if __name__ == "__main__":
    main()
