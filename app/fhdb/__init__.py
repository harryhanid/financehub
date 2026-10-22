"""fhdb: akses database FinanceHub lewat `public.fh_exec` dengan API mirip sqlite3."""
import threading

from .connection import Connection, Cursor, Row, reset_stats, stats
from .errors import DatabaseError, IntegrityError, OperationalError, ProgrammingError

__all__ = [
    "Connection", "Cursor", "Row", "get_conn", "stats", "reset_stats",
    "DatabaseError", "IntegrityError", "OperationalError", "ProgrammingError",
]

_backends: dict = {}
_backends_lock = threading.Lock()


def _backend():
    import config

    kind = config.DB_BACKEND
    if kind == "http":
        key = ("http", config.SUPABASE_URL)
    elif kind == "pg":
        key = ("pg", config.FH_PG_DSN)
    else:
        raise ValueError(f"DB_BACKEND tidak didukung fhdb: {kind!r} (harus 'http' atau 'pg')")
    with _backends_lock:
        b = _backends.get(key)
        if b is None:
            from .backends import HttpBackend, PgBackend

            if kind == "http":
                if not (config.SUPABASE_URL and config.SUPABASE_SERVICE_KEY):
                    raise ValueError("SUPABASE_URL / SUPABASE_SERVICE_KEY belum di-set")
                b = HttpBackend(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
            else:
                if not config.FH_PG_DSN:
                    raise ValueError("FH_PG_DSN belum di-set")
                b = PgBackend(config.FH_PG_DSN)
            _backends[key] = b
        return b


def get_conn() -> Connection:
    """Connection baru; backend (per proses, koneksi per thread) dipilih dari config.DB_BACKEND."""
    import config

    return Connection(_backend(), config.DB_SCHEMA)
