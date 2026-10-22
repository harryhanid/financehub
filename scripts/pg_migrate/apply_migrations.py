"""Apply app/db_migrations/*.sql to a FinanceHub schema.

Usage:
  python scripts/pg_migrate/apply_migrations.py --schema financehub_staging --backend http
  python scripts/pg_migrate/apply_migrations.py --schema financehub_test --backend pg --dsn postgresql://...

Each file: ``{{schema}}`` substituted, split with fhdb.sqlbind.split_script, run in ONE
``execute_batch`` (= one fh_exec call = one transaction).

Exception: ``0001_fh_exec.sql`` creates ``public.fh_exec`` itself. With the http backend it is NOT
applied here (apply it via the Supabase SQL Editor / Supabase plugin). With PgBackend it is executed
directly through psycopg2. The pg backend also creates the schema if missing; with http the schema
must already exist.

Migrations are not tracked: 0002_schema.sql is meant for an empty schema.
"""
import argparse
import os
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[2] / "app"
MIGRATIONS_DIR = APP_DIR / "db_migrations"
sys.path.insert(0, str(APP_DIR))

from fhdb.backends import HttpBackend, PgBackend  # noqa: E402
from fhdb.sqlbind import split_script  # noqa: E402

ALLOWED_SCHEMAS = ("financehub", "financehub_staging", "financehub_test")
FH_EXEC_FILE = "0001_fh_exec.sql"


def _check_schema(schema):
    if schema not in ALLOWED_SCHEMAS:
        raise ValueError(f"schema {schema!r} tidak diizinkan (hanya {', '.join(ALLOWED_SCHEMAS)})")


def _run_direct(backend, sql):
    import psycopg2

    conn = psycopg2.connect(backend._dsn)
    try:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(sql)
    finally:
        conn.close()


def apply(backend, schema: str, files: list) -> None:
    _check_schema(schema)
    for path in files:
        path = Path(path)
        text = path.read_text(encoding="utf-8")
        if path.name == FH_EXEC_FILE:
            if not isinstance(backend, PgBackend):
                raise ValueError(f"{FH_EXEC_FILE} membuat fungsi di public: terapkan lewat SQL Editor/plugin Supabase")
            _run_direct(backend, text)
            print(f"  {path.name}: diterapkan langsung (psycopg2)")
            continue
        stmts = split_script(text.replace("{{schema}}", schema))
        if stmts:
            backend.execute_batch(stmts, schema)
        print(f"  {path.name}: {len(stmts)} statement")


def default_files(backend_kind):
    files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    if backend_kind == "http":
        files = [f for f in files if f.name != FH_EXEC_FILE]
    return files


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--schema", required=True, choices=ALLOWED_SCHEMAS)
    ap.add_argument("--backend", required=True, choices=("pg", "http"))
    ap.add_argument("--dsn", default=os.environ.get("FH_PG_DSN", ""), help="pg backend (default: env FH_PG_DSN)")
    ap.add_argument("files", nargs="*", help="file migrasi (default: semua di app/db_migrations, urut nama)")
    args = ap.parse_args(argv)

    files = [Path(f) for f in args.files] or default_files(args.backend)
    if args.backend == "pg":
        if not args.dsn:
            ap.error("--dsn (atau env FH_PG_DSN) wajib untuk backend pg")
        backend = PgBackend(args.dsn)
        _run_direct(backend, f'create schema if not exists "{args.schema}"')
    else:
        from dotenv import load_dotenv

        load_dotenv(APP_DIR / ".env")
        url, key = os.environ.get("SUPABASE_URL", ""), os.environ.get("SUPABASE_SERVICE_KEY", "")
        if not url or not key:
            sys.exit("SUPABASE_URL / SUPABASE_SERVICE_KEY belum di-set (app/.env)")
        backend = HttpBackend(url, key)
    try:
        print(f"Schema {args.schema}, backend {args.backend}, {len(files)} file")
        apply(backend, args.schema, files)
    finally:
        backend.close()
    print("Selesai.")


if __name__ == "__main__":
    main()
