"""Dua backend dengan semantik identik: satu panggilan `execute_batch` = satu panggilan
`public.fh_exec(stmts jsonb, schema text)` = satu transaksi.

- HttpBackend: PostgREST RPC lewat HTTPS (produksi; jaringan kantor hanya mengizinkan HTTPS).
- PgBackend: psycopg2 langsung (test, Postgres lokal).

Result = {"columns": list[str], "rows": list[list]}  (statement yang mengembalikan baris)
       | {"rowcount": int}                            (statement lain)
"""
import http.client
import json
import socket
import threading
from urllib.parse import urlparse

from .errors import DatabaseError, OperationalError, from_sqlstate

Result = dict


def parse_results(text: str) -> list[Result]:
    """Parse teks hasil fh_exec. object_pairs_hook=list menjaga urutan kolom dan nama kolom kembar."""
    items = json.loads(text, object_pairs_hook=list)
    out: list[Result] = []
    for pairs in items:
        d = dict(pairs)
        if "rowcount" in d:
            out.append({"rowcount": int(d["rowcount"])})
            continue
        rows = d.get("rows") or []
        if rows:
            columns = [k for k, _ in rows[0]]
            out.append({"columns": columns, "rows": [[v for _, v in row] for row in rows]})
        else:
            out.append({"columns": list(d.get("columns") or []), "rows": []})
    return out


class HttpBackend:
    def __init__(self, url: str, key: str, timeout: float = 30.0):
        u = urlparse(url)
        if u.scheme != "https" or not u.hostname:
            raise ValueError("HttpBackend butuh URL https://<host>")
        self._host = u.hostname
        self._port = u.port
        self._path = (u.path.rstrip("/") or "") + "/rest/v1/rpc/fh_exec"
        self._timeout = timeout
        self._headers = {"apikey": key, "Content-Type": "application/json", "Accept": "application/json"}
        if key.startswith("eyJ"):  # key lama (JWT) juga dikirim sebagai Bearer
            self._headers["Authorization"] = f"Bearer {key}"
        self._local = threading.local()

    def __repr__(self):  # jangan pernah tampilkan key
        return f"HttpBackend(host={self._host!r})"

    def _conn(self) -> http.client.HTTPSConnection:
        conn = getattr(self._local, "conn", None)
        # Buat ulang SEBELUM mengirim kalau koneksi belum ada / sudah ditutup server.
        if conn is None or conn.sock is None:
            if conn is not None:
                conn.close()
            conn = http.client.HTTPSConnection(self._host, self._port, timeout=self._timeout)
            self._local.conn = conn
        return conn

    def _drop_conn(self):
        conn = getattr(self._local, "conn", None)
        self._local.conn = None
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass

    def close(self):
        self._drop_conn()

    def execute_batch(self, stmts: list[str], schema: str) -> list[Result]:
        body = json.dumps({"stmts": list(stmts), "schema": schema})
        conn = self._conn()
        try:
            conn.request("POST", self._path, body=body, headers=self._headers)
            resp = conn.getresponse()
            data = resp.read()
            status = resp.status
        except (socket.timeout, TimeoutError) as e:
            self._drop_conn()
            raise OperationalError(f"fh_exec HTTP timeout setelah {self._timeout}s") from e
        except (ConnectionError, OSError, http.client.HTTPException) as e:
            self._drop_conn()
            raise OperationalError(f"fh_exec HTTP koneksi gagal: {type(e).__name__}") from e

        text = data.decode("utf-8") if data else ""
        if status == 200:
            try:
                payload = json.loads(text)  # PostgREST: fungsi returns text -> string JSON
                return parse_results(payload if isinstance(payload, str) else json.dumps(payload))
            except (ValueError, TypeError) as e:
                raise DatabaseError(f"fh_exec: respons tidak valid (HTTP 200): {text[:200]!r}") from e

        try:
            err = json.loads(text)
        except ValueError:
            err = None
        if isinstance(err, dict):
            message = str(err.get("message") or "")
            for extra in ("details", "hint"):
                if err.get(extra):
                    message += f" ({extra}: {err[extra]})"
            raise from_sqlstate(err.get("code"), f"HTTP {status}: {message}", http_status=status)
        raise from_sqlstate(None, f"fh_exec HTTP {status}: {text[:200]!r}", http_status=status)


class PgBackend:
    def __init__(self, dsn: str):
        self._dsn = dsn
        self._local = threading.local()

    def __repr__(self):
        return "PgBackend()"

    def _conn(self):
        import psycopg2

        conn = getattr(self._local, "conn", None)
        if conn is None or conn.closed:
            try:
                conn = psycopg2.connect(self._dsn)
            except psycopg2.Error as e:
                raise _map_pg_error(e) from e
            conn.autocommit = False
            self._local.conn = conn
        return conn

    def close(self):
        conn = getattr(self._local, "conn", None)
        self._local.conn = None
        if conn is not None and not conn.closed:
            conn.close()

    def execute_batch(self, stmts: list[str], schema: str) -> list[Result]:
        import psycopg2

        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute("select public.fh_exec(%s::jsonb, %s)", (json.dumps(list(stmts)), schema))
                text = cur.fetchone()[0]
            conn.commit()
        except psycopg2.Error as e:
            if not conn.closed:
                try:
                    conn.rollback()
                except psycopg2.Error:
                    pass
            raise _map_pg_error(e) from e
        return parse_results(text)


def _map_pg_error(e) -> DatabaseError:
    import psycopg2

    code = getattr(e, "pgcode", None)
    diag = getattr(e, "diag", None)
    message = (getattr(diag, "message_primary", None) or str(e)).strip()
    if not code and isinstance(e, (psycopg2.OperationalError, psycopg2.InterfaceError)):
        return OperationalError(message)
    return from_sqlstate(code, message)
