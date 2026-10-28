"""Salin finance_hub.db (SQLite) ke Postgres Supabase (project Flow).

Default = DRY-RUN: hanya membaca SQLite, TIDAK konek ke Supabase.
    python scripts/sqlite_to_supabase.py                 # dry-run
    python scripts/sqlite_to_supabase.py --apply         # tulis ke Supabase
    python scripts/sqlite_to_supabase.py --apply --replace   # timpa tabel yang sudah ada

Butuh FLOW_DATABASE_URL di C:\\Financehub\\app\\.env (connection string Postgres dari
Supabase > Connect > Session pooler). Rahasia: jangan dibagikan, jangan di-commit.

Sumber SQLite hanya dibaca (snapshot via backup API), file aslinya tidak diubah.
"""
import argparse
import csv
import io
import os
import re
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

SRC_DB = r"C:\Financehub\app\finance_hub.db"
ENV_FILE = r"C:\Financehub\app\.env"
SCHEMA = "financehub"
SKIP_DEFAULT = {"refresh_tokens", "users"}  # token sesi + hash password
CHUNK = 20000

# View SQLite diterjemahkan manual (GROUP_CONCAT(DISTINCT x) -> string_agg(DISTINCT x::text, ',')).
VIEWS = {
    "pa_summary": """
CREATE OR REPLACE VIEW pa_summary AS
SELECT
    e.company_id,
    e.pa_number,
    string_agg(DISTINCT e.tgl_payment_application::text, ',') AS tgl_payment_application,
    string_agg(DISTINCT e.nomor_pam::text, ',')               AS nomor_pam,
    string_agg(DISTINCT s.nama::text, ',')                    AS nama_student,
    string_agg(DISTINCT l.jenis_pembayaran::text, ',')        AS jenis_pembayaran,
    string_agg(DISTINCT l.semester::text, ',')                AS semester,
    SUM(l.jumlah_pembayaran)                                  AS jumlah_pembayaran,
    string_agg(DISTINCT e.status::text, ',')                  AS status,
    string_agg(DISTINCT e.tanggal_bayar::text, ',')           AS tanggal_bayar,
    string_agg(DISTINCT e.keterangan::text, ',')              AS keterangan
FROM etf_pa e
LEFT JOIN etf_pa_lines l ON l.pa_id = e.id
LEFT JOIN siswa s ON s.id = l.student_id
GROUP BY e.company_id, e.pa_number
""",
}


def ident(name):
    return re.sub(r"[^a-z0-9_]", "_", name.lower())


def q(name):
    return '"' + name.replace('"', '""') + '"'


def fq(pg_table):
    return f"{q(SCHEMA)}.{q(pg_table)}"


def snapshot(src):
    tmpdir = Path(tempfile.mkdtemp(prefix="fh_snap_"))
    dst_path = tmpdir / "snapshot.db"
    s = sqlite3.connect(f"file:{Path(src).as_posix()}?mode=ro", uri=True)
    d = sqlite3.connect(dst_path)
    s.backup(d)
    d.close()
    s.close()
    return tmpdir, dst_path


def pick_type(decl, kinds):
    """Tentukan tipe Postgres dari tipe deklarasi + tipe nilai yang benar-benar ada."""
    d = (decl or "").upper()
    nonnull = kinds - {"null"}
    if not nonnull:
        if "INT" in d:
            return "bigint", None
        if any(k in d for k in ("REAL", "FLOA", "DOUB", "NUMERIC", "DECIMAL")):
            return "double precision", None
        return "text", None
    if nonnull == {"blob"}:
        return "bytea", None
    if "INT" in d:
        if nonnull <= {"integer"}:
            return "bigint", None
        if nonnull <= {"integer", "real"}:
            return "double precision", "INTEGER berisi desimal -> double precision"
        return "text", f"INTEGER berisi {sorted(nonnull)} -> text"
    if any(k in d for k in ("REAL", "FLOA", "DOUB", "NUMERIC", "DECIMAL")):
        if nonnull <= {"integer", "real"}:
            return "double precision", None
        return "text", f"REAL berisi {sorted(nonnull)} -> text"
    if nonnull <= {"text"}:
        return "text", None
    return "text", f"{d or 'tanpa tipe'} berisi {sorted(nonnull)} -> text"


def pg_default(dflt, pgtype, warns, where):
    if dflt is None:
        return None
    s = dflt.strip()
    while s.startswith("(") and s.endswith(")"):
        s = s[1:-1].strip()
    if s.upper() == "NULL":
        return None
    if re.fullmatch(r"-?\d+(\.\d+)?", s):
        return f"'{s}'" if pgtype == "text" else s
    if re.fullmatch(r"'(?:[^']|'')*'", s):
        return s
    low = s.lower().replace(" ", "")
    if pgtype == "text" and (low == "current_timestamp" or low.startswith("datetime('now'")):
        zone = "Asia/Jakarta" if "localtime" in low else "utc"
        return f"to_char(now() at time zone '{zone}', 'YYYY-MM-DD HH24:MI:SS')"
    if pgtype == "text" and low.startswith("date('now'"):
        zone = "Asia/Jakarta" if "localtime" in low else "utc"
        return f"to_char(now() at time zone '{zone}', 'YYYY-MM-DD')"
    warns.append(f"{where}: default '{dflt}' tidak diterjemahkan (dilewati)")
    return None


def analyze(conn, table, warns):
    info = conn.execute(f"PRAGMA table_info({q(table)})").fetchall()
    cols, seen = [], set()
    for _cid, name, decl, notnull, dflt, pk in info:
        pg = ident(name)
        if pg in seen:
            raise RuntimeError(f"{table}: nama kolom bentrok setelah dinormalisasi: {pg}")
        seen.add(pg)
        kinds = {r[0] for r in conn.execute(f"SELECT DISTINCT typeof({q(name)}) FROM {q(table)}")}
        pgtype, note = pick_type(decl, kinds)
        if note:
            warns.append(f"{table}.{name}: {note}")
        cols.append({
            "name": name, "pg": pg, "decl": (decl or "").upper(), "pgtype": pgtype,
            "notnull": bool(notnull), "pk": pk,
            "default": pg_default(dflt, pgtype, warns, f"{table}.{name}"),
        })
    pkcols = sorted([c for c in cols if c["pk"]], key=lambda c: c["pk"])
    for c in pkcols:
        n = conn.execute(f"SELECT count(*) FROM {q(table)} WHERE {q(c['name'])} IS NULL").fetchone()[0]
        if n:
            warns.append(f"{table}: PK {c['name']} berisi {n} NULL -> PRIMARY KEY dilewati")
            pkcols = []
            break
    rows = conn.execute(f"SELECT count(*) FROM {q(table)}").fetchone()[0]
    return {"name": table, "pg": ident(table), "cols": cols, "pk": pkcols, "rows": rows}


def create_sql(t):
    parts = []
    identity = (len(t["pk"]) == 1 and t["pk"][0]["decl"] == "INTEGER"
                and t["pk"][0]["pgtype"] == "bigint")
    for c in t["cols"]:
        d = f"{q(c['pg'])} {c['pgtype']}"
        if identity and c is t["pk"][0]:
            d += " GENERATED BY DEFAULT AS IDENTITY"
        if c["notnull"] and not c["pk"]:
            d += " NOT NULL"
        if c["default"] is not None:
            d += f" DEFAULT {c['default']}"
        parts.append(d)
    if t["pk"]:
        parts.append("PRIMARY KEY (" + ", ".join(q(c["pg"]) for c in t["pk"]) + ")")
    t["identity"] = identity
    return f"CREATE TABLE {fq(t['pg'])} (\n  " + ",\n  ".join(parts) + "\n)"


def cell(v, pgtype):
    if v is None:
        return r"\N"
    if isinstance(v, (bytes, bytearray)):
        return "\\x" + bytes(v).hex()
    if pgtype == "text":
        v = str(v)
        return v.replace("\x00", "") if "\x00" in v else v
    return v


def copy_table(sq, cur, t):
    sel = ", ".join(q(c["name"]) for c in t["cols"])
    dest = ", ".join(q(c["pg"]) for c in t["cols"])
    sql = f"COPY {fq(t['pg'])} ({dest}) FROM STDIN WITH (FORMAT csv, NULL '\\N')"
    types = [c["pgtype"] for c in t["cols"]]
    src = sq.execute(f"SELECT {sel} FROM {q(t['name'])}")
    total = 0
    while True:
        batch = src.fetchmany(CHUNK)
        if not batch:
            break
        buf = io.StringIO()
        w = csv.writer(buf, lineterminator="\n")
        for row in batch:
            w.writerow([cell(v, ty) for v, ty in zip(row, types)])
        buf.seek(0)
        cur.copy_expert(sql, buf)
        total += len(batch)
    return total


def verify(sq, cur, t):
    nums = [c for c in t["cols"] if c["pgtype"] in ("bigint", "double precision")]
    sel_s = ", ".join(["count(*)"] + [f"sum({q(c['name'])})" for c in nums])
    sel_p = ", ".join(["count(*)"] + [f"sum({q(c['pg'])})::float8" for c in nums])
    a = sq.execute(f"SELECT {sel_s} FROM {q(t['name'])}").fetchone()
    cur.execute(f"SELECT {sel_p} FROM {fq(t['pg'])}")
    b = cur.fetchone()
    if a[0] != b[0]:
        return f"jumlah baris beda: sqlite={a[0]} pg={b[0]}"
    for c, x, y in zip(nums, a[1:], b[1:]):
        x = float(x or 0)
        y = float(y or 0)
        if abs(x - y) > 1e-6 * max(1.0, abs(x)):
            return f"SUM({c['name']}) beda: sqlite={x} pg={y}"
    return None


def post_load(sq, conn, cur, tables, fails, warns):
    names = {t["name"]: t for t in tables}
    used = set()

    def run(label, sql):
        try:
            cur.execute(sql)
            conn.commit()
        except Exception as e:
            conn.rollback()
            warns.append(f"{label}: {str(e).splitlines()[0]}")

    for t in tables:
        if t["name"] in fails:
            continue
        for _seq, iname, uniq, origin, partial in [r[:5] for r in
                sq.execute(f"PRAGMA index_list({q(t['name'])})").fetchall()]:
            if origin == "pk":
                continue
            cols = [r[2] for r in sq.execute(f"PRAGMA index_info({q(iname)})").fetchall()]
            if partial or any(c is None for c in cols):
                warns.append(f"index {iname}: partial/ekspresi, dilewati")
                continue
            base = f"{t['pg']}_{'_'.join(ident(c) for c in cols)}_{'u' if uniq else 'i'}"[:58]
            nm, n = base, 1
            while nm in used:
                n += 1
                nm = f"{base}{n}"
            used.add(nm)
            run(f"index {iname}",
                f"CREATE {'UNIQUE ' if uniq else ''}INDEX {q(nm)} ON {fq(t['pg'])} ("
                + ", ".join(q(ident(c)) for c in cols) + ")")
        fks = {}
        for r in sq.execute(f"PRAGMA foreign_key_list({q(t['name'])})").fetchall():
            fks.setdefault(r[0], []).append(r)
        for rows in fks.values():
            parent = names.get(rows[0][2])
            if parent is None or parent["name"] in fails:
                warns.append(f"FK {t['name']} -> {rows[0][2]}: tabel induk tidak ikut disalin, dilewati")
                continue
            child_cols = [ident(r[3]) for r in rows]
            parent_cols = ([ident(r[4]) for r in rows] if rows[0][4]
                           else [c["pg"] for c in parent["pk"]])
            act = rows[0][6].upper()
            on_del = f" ON DELETE {act}" if act in ("CASCADE", "SET NULL", "SET DEFAULT", "RESTRICT") else ""
            run(f"FK {t['name']} -> {parent['name']}",
                f"ALTER TABLE {fq(t['pg'])} ADD FOREIGN KEY ("
                + ", ".join(q(c) for c in child_cols) + f") REFERENCES {fq(parent['pg'])} ("
                + ", ".join(q(c) for c in parent_cols) + f"){on_del} NOT VALID")
        if t.get("identity"):
            col = t["pk"][0]["pg"]
            run(f"identity {t['name']}",
                f"SELECT setval(pg_get_serial_sequence('{q(SCHEMA)}.{q(t['pg'])}', '{col}'), "
                f"COALESCE((SELECT max({q(col)}) FROM {fq(t['pg'])}), 1), "
                f"(SELECT max({q(col)}) FROM {fq(t['pg'])}) IS NOT NULL)")
        run(f"RLS {t['name']}", f"ALTER TABLE {fq(t['pg'])} ENABLE ROW LEVEL SECURITY")
    for vname, vsql in VIEWS.items():
        run(f"view {vname}", f"SET search_path TO {q(SCHEMA)}; {vsql}")
    run("revoke", f"REVOKE ALL ON SCHEMA {q(SCHEMA)} FROM anon, authenticated")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="tulis ke Supabase (default: dry-run)")
    ap.add_argument("--replace", action="store_true", help="DROP tabel yang sudah ada lalu buat ulang")
    ap.add_argument("--include", default="", help="tabel yang biasanya dilewati, mis. users")
    ap.add_argument("--only", default="", help="hanya tabel ini (pisah koma)")
    args = ap.parse_args()

    skip = SKIP_DEFAULT - {x.strip() for x in args.include.split(",") if x.strip()}
    only = {x.strip() for x in args.only.split(",") if x.strip()}
    warns, fails = [], {}
    tmpdir, snap = snapshot(SRC_DB)
    try:
        sq = sqlite3.connect(snap)
        names = [r[0] for r in sq.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        tables, pgnames = [], set()
        for n in names:
            if n in skip or (only and n not in only):
                continue
            t = analyze(sq, n, warns)
            if t["pg"] in pgnames:
                raise RuntimeError(f"nama tabel bentrok setelah dinormalisasi: {t['pg']}")
            pgnames.add(t["pg"])
            create_sql(t)
            tables.append(t)

        total = sum(t["rows"] for t in tables)
        print(f"Snapshot OK. {len(tables)} tabel, {total} baris. Dilewati: {sorted(skip & set(names))}")
        for t in tables:
            print(f"  {t['pg']:28} {t['rows']:7} baris  {len(t['cols']):3} kolom")

        if not args.apply:
            print("\nDRY-RUN selesai (Supabase tidak disentuh).")
        else:
            import psycopg2
            from dotenv import load_dotenv
            load_dotenv(ENV_FILE)
            url = os.environ.get("FLOW_DATABASE_URL")
            if not url:
                sys.exit(f"FLOW_DATABASE_URL belum ada di {ENV_FILE}")
            conn = psycopg2.connect(url, connect_timeout=20)
            cur = conn.cursor()
            cur.execute(f"CREATE SCHEMA IF NOT EXISTS {q(SCHEMA)}")
            conn.commit()
            for t in tables:
                try:
                    cur.execute("SELECT to_regclass(%s)", (f"{q(SCHEMA)}.{q(t['pg'])}",))
                    exists = cur.fetchone()[0] is not None
                    if exists and not args.replace:
                        raise RuntimeError("tabel sudah ada (pakai --replace untuk menimpa)")
                    if exists:
                        cur.execute(f"DROP TABLE {fq(t['pg'])} CASCADE")
                    cur.execute(create_sql(t))
                    n = copy_table(sq, cur, t)
                    conn.commit()
                    print(f"  disalin {t['pg']}: {n} baris")
                except Exception as e:
                    conn.rollback()
                    fails[t["name"]] = str(e).splitlines()[0]
                    print(f"  GAGAL {t['pg']}: {fails[t['name']]}")
            post_load(sq, conn, cur, tables, fails, warns)
            print("\nVerifikasi (jumlah baris + SUM kolom numerik):")
            bad = 0
            for t in tables:
                if t["name"] in fails:
                    continue
                msg = verify(sq, cur, t)
                if msg:
                    bad += 1
                    print(f"  BEDA {t['pg']}: {msg}")
            ok = len(tables) - len(fails) - bad
            print(f"  {ok} tabel cocok, {bad} beda, {len(fails)} gagal")
            conn.close()
    finally:
        try:
            sq.close()
        except Exception:
            pass
        shutil.rmtree(tmpdir, ignore_errors=True)

    if warns:
        print(f"\nCatatan ({len(warns)}):")
        for w in warns:
            print("  -", w)


if __name__ == "__main__":
    main()
