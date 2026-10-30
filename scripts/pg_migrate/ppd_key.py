"""Buat atau cabut kunci API PR Portal (public.ppd_keys, app/db_migrations_prportal/0001_ppd_api.sql).

Usage:
  python scripts/pg_migrate/ppd_key.py --schema prportal_staging --label "PR Portal staging"
  python scripts/pg_migrate/ppd_key.py --schema prportal --label "PR Portal prod"
  python scripts/pg_migrate/ppd_key.py --revoke "PR Portal staging"

Kunci baru = secrets.token_urlsafe(32). Yang dikirim ke database HANYA sha256 hex-nya (sama dengan
encode(sha256(convert_to(p_key,'UTF8')),'hex') di fungsi public.ppd_*). Kunci asli dicetak SEKALI ke
stdout untuk ditempel ke Script Property FLOW_PPD_KEY di PR Portal; tidak disimpan di mana pun.

Backend default http: SUPABASE_URL / SUPABASE_SERVICE_KEY dari environment Flow (app/.env lewat
python-dotenv, sama dengan apply_migrations.py). Nilainya tidak pernah dicetak.
"""
import argparse
import hashlib
import os
import secrets
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[2] / "app"
sys.path.insert(0, str(APP_DIR))

from fhdb.sqlbind import bind  # noqa: E402

# prportal_test sengaja tidak bisa dipilih dari CLI (test memakai create_key langsung).
CLI_SCHEMAS = ("prportal", "prportal_staging")
ALLOWED_SCHEMAS = ("prportal", "prportal_staging", "prportal_test")
# fh_exec hanya menerima schema financehub*; statement memakai nama bertingkat public.ppd_keys,
# jadi schema eksekusi ini tidak memengaruhi hasil.
EXEC_SCHEMA = "financehub"


def _check_schema(schema):
    if schema not in ALLOWED_SCHEMAS:
        raise ValueError(f"schema {schema!r} tidak diizinkan")


def key_hash(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def create_key(backend, schema: str, label: str, exec_schema: str = EXEC_SCHEMA) -> str:
    """Buat kunci baru, simpan hash-nya untuk `schema`; kembalikan kunci asli (jangan di-log)."""
    _check_schema(schema)
    if not label or not label.strip():
        raise ValueError("label wajib diisi")
    key = secrets.token_urlsafe(32)
    stmt = bind("insert into public.ppd_keys (key_hash, schema_name, label) values (?, ?, ?)",
                (key_hash(key), schema, label.strip()))
    backend.execute_batch([stmt], exec_schema)
    return key


def revoke_key(backend, label: str, exec_schema: str = EXEC_SCHEMA) -> int:
    """Cabut semua kunci aktif dengan label ini; kembalikan jumlah yang dicabut."""
    stmt = bind("update public.ppd_keys set revoked_at = now() where label = ? and revoked_at is null",
                (label.strip(),))
    res = backend.execute_batch([stmt], exec_schema)
    return int(res[0].get("rowcount", 0)) if res else 0


def _make_backend(args, ap):
    from fhdb.backends import HttpBackend, PgBackend

    if args.backend == "pg":
        if not args.dsn:
            ap.error("--dsn (atau env FH_PG_DSN) wajib untuk backend pg")
        return PgBackend(args.dsn)
    from dotenv import load_dotenv

    load_dotenv(APP_DIR / ".env")
    url, key = os.environ.get("SUPABASE_URL", ""), os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not url or not key:
        sys.exit("SUPABASE_URL / SUPABASE_SERVICE_KEY belum di-set (app/.env)")
    return HttpBackend(url, key)


def main(argv=None, backend=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--schema", choices=CLI_SCHEMAS, help="schema PR Portal yang diakses kunci (untuk --label)")
    grp = ap.add_mutually_exclusive_group(required=True)
    grp.add_argument("--label", help="nama kunci baru (mis. 'PR Portal staging')")
    grp.add_argument("--revoke", metavar="LABEL", help="cabut semua kunci aktif berlabel ini")
    ap.add_argument("--backend", default="http", choices=("http", "pg"))
    ap.add_argument("--dsn", default=os.environ.get("FH_PG_DSN", ""), help="backend pg (default: env FH_PG_DSN)")
    args = ap.parse_args(argv)
    if args.label is not None and not args.schema:
        ap.error("--schema wajib bersama --label")

    if backend is None:
        backend = _make_backend(args, ap)
    try:
        if args.revoke is not None:
            n = revoke_key(backend, args.revoke)
            print(f"Dicabut: {n} kunci aktif berlabel {args.revoke!r}.")
            return
        key = create_key(backend, args.schema, args.label)
    finally:
        backend.close()
    print(f"Kunci PR Portal untuk schema {args.schema} (label {args.label.strip()!r}) dibuat.")
    print("Tempel baris berikut ke Script Property FLOW_PPD_KEY di proyek Apps Script PR Portal")
    print("(Project Settings > Script Properties). Kunci TIDAK ditampilkan lagi dan tidak disimpan:")
    print()
    print(f"FLOW_PPD_KEY={key}")
    print()
    print("Isi Script Property cukup nilainya (bagian sesudah 'FLOW_PPD_KEY=').")


if __name__ == "__main__":
    main()
