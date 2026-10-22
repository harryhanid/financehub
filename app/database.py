# database.py -- akses database FinanceHub lewat fhdb (Supabase Postgres, schema config.DB_SCHEMA).
#
# Skema TIDAK lagi dibuat/dimigrasi saat app start: DDL ada di app/db_migrations/*.sql dan diterapkan
# dengan scripts/pg_migrate/apply_migrations.py. init_db() hanya menulis seed referensi (idempoten).
from fhdb import get_conn
from fhdb.seed import VENDOR_SEED, seed_reference_data

__all__ = ["get_conn", "init_db", "VENDOR_SEED"]


def init_db():
    conn = get_conn()
    try:
        seed_reference_data(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()
    print("Seed referensi selesai.")
