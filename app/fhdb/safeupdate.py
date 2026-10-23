"""Emulasi pg_safeupdate (Supabase) untuk backend lokal/test.

Supabase memuat ekstensi `pg_safeupdate` untuk request lewat Data API (PostgREST): setiap UPDATE /
DELETE tanpa WHERE ditolak dengan SQLSTATE 21000 ("UPDATE requires a WHERE clause"), juga statement
di dalam fungsi plpgsql / DO block, dan tidak bisa dimatikan. Semua SQL FinanceHub lewat fh_exec di
PostgREST, jadi PgBackend (test, Postgres lokal tanpa ekstensi itu) menolak hal yang sama di sisi
klien supaya pelanggaran ketahuan di test, bukan di produksi. HttpBackend tidak memakai modul ini.

Klien hanya melihat teks statement: UPDATE/DELETE di level atas, di CTE (`WITH d AS (DELETE ...)`)
dan di subquery dicek. Isi body DO / fungsi (string literal) tidak terlihat di sini -- untuk itu
`unguarded_dml(sql, nested=True)` dipakai oleh test yang memindai db_migrations dan body DO yang
dibangun aplikasi.

WHERE yang dihitung hanya WHERE milik statement itu sendiri (kedalaman kurung yang sama, sebelum
statement berakhir); WHERE di dalam string literal, komentar, atau subquery tidak dihitung.
"""
import re

from .errors import from_sqlstate
from .sqlbind import _scan

_TOKEN = re.compile(r"[()\[\];,]|[^\s()\[\];,]+")
# Kata sebelum `update` yang menandakan ini BUKAN statement UPDATE (FOR UPDATE, ON UPDATE CASCADE,
# DO UPDATE SET pada ON CONFLICT -- tidak dicek pg_safeupdate, trigger BEFORE/AFTER UPDATE, GRANT).
_NOT_DML_BEFORE_UPDATE = {"for", "key", "do", "on", "or", "of", "before", "after", "instead", ",",
                          "grant", "revoke", "select", "insert", "delete", "references", "truncate"}
_NOT_DML_BEFORE_DELETE = {"on", "or", "before", "after", "instead", ",", "grant", "revoke",
                          "select", "insert", "update", "references", "truncate"}


def _unescape(lit: str) -> str:
    return lit[1:-1].replace("''", "'") if len(lit) >= 2 else ""


def _tokens(sql: str, nested: bool, strings: list[str]) -> list[str]:
    """Token skeleton (huruf kecil): literal -> '_s_', identifier ber-quote -> '_i_', komentar dibuang.
    Kalau `nested`, isi literal string dikumpulkan ke `strings` (untuk dicek terpisah)."""
    parts = []
    for kind, text in _scan(sql):
        if kind == "code":
            parts.append(text.lower())
        elif kind == "str":
            parts.append(" _s_ ")
            if nested:
                strings.append(_unescape(text))
        elif kind == "ident":
            parts.append(" _i_ ")
        else:
            parts.append(" ")
    return _TOKEN.findall("".join(parts))


def _depths(toks: list[str]) -> list[int]:
    out, d = [], 0
    for t in toks:
        if t in ("(", "["):
            d += 1
            out.append(d)
        elif t in (")", "]"):
            out.append(d)
            d -= 1
        else:
            out.append(d)
    return out


def _is_update_stmt(toks, depths, i) -> bool:
    if i > 0 and toks[i - 1] in _NOT_DML_BEFORE_UPDATE:
        return False
    d = depths[i]
    # update [only] name [ [as] alias ] set  -- `name` boleh schema.tabel atau {{schema}}._i_
    j, seen = i + 1, 0
    while j < len(toks) and seen <= 4:
        t = toks[j]
        if depths[j] != d or t in ("(", ")", ";", ","):
            return False
        if t == "set":
            return seen >= 1
        seen += 1
        j += 1
    return False


def _is_delete_stmt(toks, i) -> bool:
    if i > 0 and toks[i - 1] in _NOT_DML_BEFORE_DELETE:
        return False
    return i + 1 < len(toks) and toks[i + 1] == "from"


def _has_own_where(toks, depths, i) -> bool:
    d = depths[i]
    for j in range(i + 1, len(toks)):
        t = toks[j]
        if t in (")", "]") and depths[j] == d:  # kurung penutup level ini: statement selesai
            return False
        if depths[j] == d and t == ";":
            return False
        if depths[j] == d and t == "where":
            return True
    return False


def unguarded_dml(sql: str, nested: bool = False) -> list[str]:
    """Daftar 'UPDATE'/'DELETE' (dengan potongan konteks) yang tidak punya WHERE sendiri.

    nested=True: isi string literal (body DO / fungsi plpgsql `as '...'`) ikut dicek, rekursif."""
    strings: list[str] = []
    toks = _tokens(sql, nested, strings)
    depths = _depths(toks)
    found = []
    for i, t in enumerate(toks):
        if t == "update" and _is_update_stmt(toks, depths, i):
            kind = "UPDATE"
        elif t == "delete" and _is_delete_stmt(toks, i):
            kind = "DELETE"
        else:
            continue
        if not _has_own_where(toks, depths, i):
            found.append(kind + ": " + " ".join(toks[i:i + 8]))
    for s in strings:
        if re.search(r"\b(update|delete)\b", s, re.IGNORECASE):
            found.extend(unguarded_dml(s, nested=True))
    return found


def check(stmt: str) -> None:
    """Tolak seperti pg_safeupdate: DatabaseError `[21000] UPDATE requires a WHERE clause`."""
    bad = unguarded_dml(stmt)
    if bad:
        kind = bad[0].split(":", 1)[0]
        raise from_sqlstate("21000", f"{kind} requires a WHERE clause "
                                     f"(fhdb: emulasi pg_safeupdate Supabase; {bad[0]})")
