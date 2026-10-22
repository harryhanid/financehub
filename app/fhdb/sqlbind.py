"""Ganti placeholder `?` (gaya sqlite3) dengan literal SQL Postgres yang di-quote aman, dan pecah script SQL."""
import datetime
import decimal
from typing import Sequence

from psycopg2.extensions import adapt

from .errors import ProgrammingError


def _literal(v) -> str:
    if v is None:
        return "NULL"
    if isinstance(v, bool):  # sebelum int: bool adalah subclass int; sqlite menyimpan True sebagai 1
        return str(int(v))
    if isinstance(v, (bytes, bytearray, memoryview)):
        raise ProgrammingError("bytes params tidak didukung")
    if isinstance(v, datetime.datetime):  # sebelum date: datetime adalah subclass date
        v = v.isoformat(" ")
    elif isinstance(v, datetime.date):
        v = v.isoformat()
    if isinstance(v, str):
        # Bukan adapt(): tanpa koneksi psycopg2 menganggap standard_conforming_strings=off dan
        # menggandakan backslash ('a\\b'), yang di Postgres modern (on) jadi data rusak.
        if "\x00" in v:
            raise ProgrammingError("teks berisi karakter NUL tidak didukung Postgres")
        return "'" + v.replace("'", "''") + "'"
    if isinstance(v, (int, float, decimal.Decimal)):
        return adapt(v).getquoted().decode("ascii")
    raise ProgrammingError(f"tipe parameter tidak didukung: {type(v).__name__}")


def _scan(sql: str):
    """Yield (kind, text): kind 'code' | 'str' | 'ident' | 'comment'. Literal/komentar utuh satu potong."""
    i, n, start = 0, len(sql), 0
    while i < n:
        c = sql[i]
        if c in ("'", '"'):
            if i > start:
                yield "code", sql[start:i]
            j = i + 1
            while True:
                k = sql.find(c, j)
                if k == -1:
                    j = n
                    break
                if k + 1 < n and sql[k + 1] == c:  # quote ganda = escape
                    j = k + 2
                    continue
                j = k + 1
                break
            yield ("str" if c == "'" else "ident"), sql[i:j]
            i = start = j
        elif c == "-" and sql.startswith("--", i):
            if i > start:
                yield "code", sql[start:i]
            k = sql.find("\n", i)
            j = n if k == -1 else k
            yield "comment", sql[i:j]
            i = start = j
        elif c == "/" and sql.startswith("/*", i):
            if i > start:
                yield "code", sql[start:i]
            k = sql.find("*/", i + 2)
            j = n if k == -1 else k + 2
            yield "comment", sql[i:j]
            i = start = j
        else:
            i += 1
    if start < n:
        yield "code", sql[start:]


def bind(sql: str, params: Sequence | None) -> str:
    params = () if params is None else params
    if isinstance(params, (str, bytes, dict)):
        raise ProgrammingError("params harus berupa sequence (tuple/list)")
    params = list(params)
    out, idx = [], 0
    for kind, text in _scan(sql):
        if kind != "code" or "?" not in text:
            out.append(text)
            continue
        pieces = text.split("?")
        out.append(pieces[0])
        for rest in pieces[1:]:
            if idx >= len(params):
                idx += 1
                out.append(rest)
                continue
            out.append(_literal(params[idx]))
            out.append(rest)
            idx += 1
    if idx != len(params):
        raise ProgrammingError(
            f"Incorrect number of bindings supplied. The current statement uses {idx}, "
            f"and there are {len(params)} supplied."
        )
    return "".join(out)


def split_script(script: str) -> list[str]:
    """Pecah script di `;` di luar literal/komentar. Komentar dibuang; potongan kosong dilewati."""
    stmts, cur = [], []
    for kind, text in _scan(script):
        if kind == "comment":
            cur.append(" " if text.startswith("/*") else "")
            continue
        if kind != "code":
            cur.append(text)
            continue
        parts = text.split(";")
        cur.append(parts[0])
        for p in parts[1:]:
            stmts.append("".join(cur))
            cur = [p]
    stmts.append("".join(cur))
    return [s.strip() for s in stmts if s.strip()]
