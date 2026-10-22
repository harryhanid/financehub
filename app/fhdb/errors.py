"""Kelas error fhdb. Subclass sqlite3.* supaya `except sqlite3.IntegrityError` di kode lama tetap menangkapnya."""
import sqlite3


class DatabaseError(sqlite3.DatabaseError):
    def __init__(self, message: str = "", sqlstate: str | None = None):
        super().__init__(message)
        self.sqlstate = sqlstate


class IntegrityError(DatabaseError, sqlite3.IntegrityError):
    pass


class OperationalError(DatabaseError, sqlite3.OperationalError):
    pass


class ProgrammingError(DatabaseError, sqlite3.ProgrammingError):
    pass


def from_sqlstate(code: str | None, message: str, http_status: int | None = None) -> DatabaseError:
    """Petakan SQLSTATE (atau status HTTP) ke kelas error fhdb. Pesan memuat SQLSTATE + message."""
    code = code or ""
    text = f"[{code}] {message}" if code else message
    if code.startswith("23"):
        cls = IntegrityError
    elif code.startswith("42"):
        cls = ProgrammingError
    elif code == "57014" or code.startswith("08"):
        cls = OperationalError
    elif http_status is not None and http_status >= 500:
        cls = OperationalError
    else:
        cls = DatabaseError
    return cls(text, sqlstate=code or None)
