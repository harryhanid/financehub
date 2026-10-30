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

``--dir`` (default app/db_migrations) picks the migration set; the allowed schemas depend on it:
  app/db_migrations          -> financehub, financehub_staging, financehub_test
  app/db_migrations_prportal -> prportal, prportal_staging, prportal_test   (PR Portal data, API ppd_*)
Files must come from the chosen dir (a file from the other known dir is rejected). The prportal set is
only applied with the pg backend, each file directly through psycopg2 (one implicit transaction per
file): fh_exec only accepts financehub* schemas and 0001_ppd_api.sql creates objects in public. On
Supabase apply it as postgres (SQL Editor / Supabase plugin) with {{schema}} substituted.

  python scripts/pg_migrate/apply_migrations.py --dir app/db_migrations_prportal --schema prportal_test --backend pg --dsn ...
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

PRPORTAL_MIGRATIONS_DIR = APP_DIR / "db_migrations_prportal"
DIR_SCHEMAS = {
    MIGRATIONS_DIR: ("financehub", "financehub_staging", "financehub_test"),
    PRPORTAL_MIGRATIONS_DIR: ("prportal", "prportal_staging", "prportal_test"),
}
ALLOWED_SCHEMAS = DIR_SCHEMAS[MIGRATIONS_DIR]
ALL_SCHEMAS = tuple(s for schemas in DIR_SCHEMAS.values() for s in schemas)
FH_EXEC_FILE = "0001_fh_exec.sql"


def _resolve_dir(dir):
    """None -> app/db_migrations; selain itu harus salah satu dir migrasi yang dikenal."""
    if dir is None:
        return MIGRATIONS_DIR
    d = Path(dir).resolve()
    for known in DIR_SCHEMAS:
        if d == known.resolve():
            return known
    raise ValueError(f"dir migrasi {str(dir)!r} tidak dikenal (hanya {', '.join(str(k) for k in DIR_SCHEMAS)})")


def _check_schema(schema, dir=None):
    """Schema harus termasuk daftar milik dir migrasinya. Mengembalikan dir (Path kanonik)."""
    d = _resolve_dir(dir)
    allowed = DIR_SCHEMAS[d]
    if schema not in allowed:
        raise ValueError(f"schema {schema!r} tidak diizinkan untuk {d.name} (hanya {', '.join(allowed)})")
    return d


def _check_files(files, d):
    """File dari dir migrasi lain yang dikenal ditolak; set prportal hanya menerima file dari dir-nya."""
    for path in files:
        parent = Path(path).resolve().parent
        for known in DIR_SCHEMAS:
            if known != d and parent == known.resolve():
                raise ValueError(f"{Path(path).name} milik {known.name}, bukan {d.name}")
        if d != MIGRATIONS_DIR and parent != d.resolve():
            raise ValueError(f"{Path(path).name} bukan file di {d.name}")


def _run_direct(backend, sql):
    import psycopg2

    conn = psycopg2.connect(backend._dsn)
    try:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(sql)
    finally:
        conn.close()


def apply(backend, schema: str, files: list, dir=None) -> None:
    d = _check_schema(schema, dir)
    _check_files(files, d)
    if d == PRPORTAL_MIGRATIONS_DIR:
        if not isinstance(backend, PgBackend):
            raise ValueError(f"{d.name} hanya lewat backend pg (fh_exec menolak schema prportal*): "
                             "terapkan lewat SQL Editor/plugin Supabase sebagai postgres")
        for path in files:
            path = Path(path)
            _run_direct(backend, path.read_text(encoding="utf-8").replace("{{schema}}", schema))
            print(f"  {path.name}: diterapkan langsung (psycopg2)")
        return
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


def default_files(backend_kind, dir=None):
    d = _resolve_dir(dir)
    files = sorted(d.glob("*.sql"))
    if d == MIGRATIONS_DIR and backend_kind == "http":
        files = [f for f in files if f.name != FH_EXEC_FILE]
    return files


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--schema", required=True, choices=ALL_SCHEMAS)
    ap.add_argument("--backend", required=True, choices=("pg", "http"))
    ap.add_argument("--dsn", default=os.environ.get("FH_PG_DSN", ""), help="pg backend (default: env FH_PG_DSN)")
    ap.add_argument("--dir", default=str(MIGRATIONS_DIR),
                    help="dir migrasi: app/db_migrations (default, financehub*) atau app/db_migrations_prportal (prportal*)")
    ap.add_argument("files", nargs="*", help="file migrasi (default: semua di --dir, urut nama)")
    args = ap.parse_args(argv)

    try:
        mig_dir = _check_schema(args.schema, args.dir)  # sebelum create schema / koneksi apa pun
    except ValueError as e:
        ap.error(str(e))
    if mig_dir == PRPORTAL_MIGRATIONS_DIR and args.backend != "pg":
        ap.error(f"{mig_dir.name} hanya lewat --backend pg; di Supabase terapkan lewat SQL Editor sebagai postgres")
    files = [Path(f) for f in args.files] or default_files(args.backend, mig_dir)
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
        apply(backend, args.schema, files, dir=mig_dir)
    finally:
        backend.close()
    print("Selesai.")


if __name__ == "__main__":
    main()
