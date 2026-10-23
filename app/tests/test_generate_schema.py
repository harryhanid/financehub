"""Generator skema Postgres (scripts/pg_migrate/generate_schema.py), runner migrasi
(scripts/pg_migrate/apply_migrations.py) dan fungsi kompatibilitas 0002b_compat.sql."""
import importlib.util
import sqlite3
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PG_MIGRATE = ROOT / "scripts" / "pg_migrate"
MIGRATIONS = ROOT / "app" / "db_migrations"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, PG_MIGRATE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_gen = _load("generate_schema")
generate = _gen.generate
apply_migrations = _load("apply_migrations")
COMPAT_SQL = (MIGRATIONS / "0002b_compat.sql").read_text(encoding="utf-8") if (
    MIGRATIONS / "0002b_compat.sql").exists() else ""


def _make_db(path, script, rows=()):
    c = sqlite3.connect(path)
    c.executescript(script)
    for sql, params in rows:
        c.execute(sql, params)
    c.commit()
    c.close()
    return str(path)


def test_generated_schema_is_faithful(tmp_path, pg_raw):
    import sqlite3
    db = tmp_path / "s.db"; c = sqlite3.connect(db)
    c.executescript('''
      create table companies (id INTEGER PRIMARY KEY, code TEXT UNIQUE NOT NULL, name TEXT NOT NULL);
      create table pb (id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER NOT NULL REFERENCES companies(id),
                       "SLA_Date_2_HT" TEXT, "tgl_A-GS_APP" TEXT, jumlah REAL DEFAULT 0, status TEXT DEFAULT 'open');
      create index idx_pb_status on pb(status);
      create view v as select id, status from pb;''')
    c.close()
    sql = generate(str(db)).replace("{{schema}}", "gen_t")
    pg_raw.execute("create schema gen_t"); pg_raw.execute(sql)
    cols = pg_raw.columns("gen_t", "pb")   # list[(name, data_type, is_identity, default)]
    assert [n for n, *_ in cols] == ["id", "company_id", "SLA_Date_2_HT", "tgl_A-GS_APP", "jumlah", "status"]
    assert cols[0][1:3] == ("bigint", "YES")
    assert cols[4][1] == "double precision" and cols[5][3].startswith("'open'")
    assert pg_raw.index_exists("gen_t", "idx_pb_status") and pg_raw.view_exists("gen_t", "v")


def test_integer_column_with_real_values_maps_to_double(tmp_path, pg_raw):
    """R7: kolom INTEGER yang berisi nilai real -> double precision (tanpa pemotongan), tercatat di komentar."""
    db = _make_db(tmp_path / "r7.db",
                  "create table pam (id INTEGER PRIMARY KEY AUTOINCREMENT, dpp INTEGER, ppn INTEGER, kode INTEGER);",
                  [("insert into pam (dpp, ppn, kode) values (?, ?, ?)", (1000, 110, 7)),
                   ("insert into pam (dpp, ppn, kode) values (?, ?, ?)", (1234.5, 135.8, "A-01"))])
    sql = generate(db)
    assert "pam.dpp" in sql and "pam.kode" in sql  # override dicatat di komentar
    pg_raw.execute("create schema gen_t"); pg_raw.execute(sql.replace("{{schema}}", "gen_t"))
    types = {n: t for n, t, *_ in pg_raw.columns("gen_t", "pam")}
    assert types == {"id": "bigint", "dpp": "double precision", "ppn": "double precision", "kode": "text"}


def test_pam_records_others_forced_double_precision(tmp_path, pg_raw):
    """R53: pam_records.others INTEGER tanpa nilai real di data tetap double precision (kode menulis float)."""
    db = _make_db(tmp_path / "r53.db",
                  "create table pam_records (id INTEGER PRIMARY KEY AUTOINCREMENT, dpp INTEGER, others INTEGER DEFAULT 0);",
                  [("insert into pam_records (dpp, others) values (?, ?)", (1000, 5))])
    sql = generate(db)
    assert "pam_records.others: double precision" in sql  # override dicatat di komentar
    pg_raw.execute("create schema gen_t"); pg_raw.execute(sql.replace("{{schema}}", "gen_t"))
    types = {n: t for n, t, *_ in pg_raw.columns("gen_t", "pam_records")}
    assert types == {"id": "bigint", "dpp": "bigint", "others": "double precision"}


def test_constraints_defaults_and_orphan_fk_not_valid(tmp_path, pg_raw):
    db = _make_db(tmp_path / "c.db", '''
      create table users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL);
      create table tok (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        jenis TEXT NOT NULL CHECK (jenis IN ('a', 'b')), created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        n INTEGER DEFAULT 0, note TEXT DEFAULT NULL);
      create table m (source TEXT NOT NULL, account TEXT NOT NULL, v TEXT, PRIMARY KEY (source, account),
                      UNIQUE (v, source));
      create unique index ux_tok_jenis on tok(user_id, jenis);''',
                  [("insert into users (username) values (?)", ("u1",)),
                   ("insert into tok (user_id, jenis) values (?, ?)", (1, "a")),
                   ("insert into tok (user_id, jenis) values (?, ?)", (99, "b"))])  # orphan
    sql = generate(db)
    assert "not valid" in sql.lower()
    pg_raw.execute("create schema gen_t"); pg_raw.execute(sql.replace("{{schema}}", "gen_t"))
    assert pg_raw.scalar(
        "select convalidated from pg_constraint where contype='f' and conrelid='gen_t.tok'::regclass") is False
    assert pg_raw.scalar(
        "select confdeltype from pg_constraint where contype='f' and conrelid='gen_t.tok'::regclass") == "c"
    pg_raw.execute("insert into gen_t.users (username) values ('x')")
    pg_raw.execute("insert into gen_t.tok (user_id, jenis) values (1, 'a')")
    assert pg_raw.scalar("select created_at ~ '^\\d{4}-\\d{2}-\\d{2} \\d{2}:\\d{2}:\\d{2}$' from gen_t.tok") is True
    assert pg_raw.scalar("select n from gen_t.tok") == 0
    import psycopg2
    with pytest.raises(psycopg2.errors.CheckViolation):
        pg_raw.execute("insert into gen_t.tok (user_id, jenis) values (1, 'zzz')")
    with pytest.raises(psycopg2.errors.UniqueViolation):
        pg_raw.execute("insert into gen_t.tok (user_id, jenis) values (1, 'a')")
    with pytest.raises(psycopg2.errors.UniqueViolation):
        pg_raw.execute("insert into gen_t.users (username) values ('x')")
    with pytest.raises(psycopg2.errors.ForeignKeyViolation):
        pg_raw.execute("insert into gen_t.tok (user_id, jenis) values (12345, 'b')")
    pk = pg_raw.scalar("select array_agg(a.attname::text order by a.attname) from pg_index i join pg_attribute a "
                       "on a.attrelid=i.indrelid and a.attnum = any(i.indkey) "
                       "where i.indrelid='gen_t.m'::regclass and i.indisprimary")
    assert pk == ["account", "source"]
    assert pg_raw.scalar("select count(*) from pg_constraint where contype='u' "
                         "and conrelid='gen_t.m'::regclass") == 1


def test_apply_migrations_substitutes_schema(tmp_path, pg_backend):
    f = tmp_path / "0099_x.sql"
    f.write_text("-- komentar; dengan titik koma\n"
                 "create table {{schema}}._apply_t (id bigint primary key, s text default 'a;b');\n"
                 "insert into {{schema}}._apply_t (id) values (1);\n", encoding="utf-8")
    try:
        apply_migrations.apply(pg_backend, "financehub_test", [f])
        res = pg_backend.execute_batch(["select s from financehub_test._apply_t"], "financehub_test")
        assert res[0]["rows"] == [["a;b"]]
    finally:
        pg_backend.execute_batch(["drop table if exists financehub_test._apply_t"], "financehub_test")


def test_apply_migrations_rejects_unknown_schema(tmp_path, pg_backend):
    f = tmp_path / "0099_x.sql"
    f.write_text("select 1;", encoding="utf-8")
    with pytest.raises(ValueError):
        apply_migrations.apply(pg_backend, "public", [f])


def test_apply_migrations_fh_exec_file_runs_directly_on_pg(pg_backend):
    # 0001 membuat fungsi di public: lewat psycopg2 langsung (bukan fh_exec), idempoten (create or replace).
    apply_migrations.apply(pg_backend, "financehub_test", [MIGRATIONS / "0001_fh_exec.sql"])
    res = pg_backend.execute_batch(["select 1 as x"], "financehub_test")
    assert res[0]["rows"] == [[1]]


def test_fh_strftime_matches_sqlite(pg_raw):
    import sqlite3
    pg_raw.execute(COMPAT_SQL.replace("{{schema}}", "public"))
    lite = sqlite3.connect(":memory:")
    for fmt, x in [("%Y", "2025-03-15"), ("%Y-%m", "2025-03-15 10:20:30"), ("%m", "2025-12-01"),
                   ("%d/%m/%Y", "2025-03-15"), ("%Y", "15/03/2025"), ("%Y", ""), ("%Y", None)]:
        expected = lite.execute("select strftime(?, ?)", (fmt, x)).fetchone()[0]
        assert pg_raw.scalar("select public.fh_strftime(%s, %s)", (fmt, x)) == expected, (fmt, x)


def test_fh_strftime_more_specifiers_match_sqlite(pg_raw):
    import sqlite3
    pg_raw.execute(COMPAT_SQL.replace("{{schema}}", "public"))
    lite = sqlite3.connect(":memory:")
    for fmt, x in [("%H:%M:%S", "2025-03-15 10:20:30"), ("%H:%M:%S", "2025-03-15"), ("%j", "2024-12-31"),
                   ("%w", "2025-03-16"), ("%w %j", "2025-03-15T08:09:10.123"), ("%Y-%m-%d", "2025-02-30"),
                   ("%Y", "2025-13-01"), ("%Y", "2025-03-15xyz"), ("Tahun %Y", "2025-03-15 10:20"),
                   (None, "2025-03-15")]:
        expected = lite.execute("select strftime(?, ?)", (fmt, x)).fetchone()[0]
        assert pg_raw.scalar("select public.fh_strftime(%s, %s)", (fmt, x)) == expected, (fmt, x)


# Versi fungsi SQL sebelum Task 21 (lambat di Supabase); acuan bahwa versi plpgsql tidak mengubah hasil.
_FH_STRFTIME_SQLFN = """
create or replace function public.fh_strftime_sqlfn(fmt text, x text)
returns text
language sql
immutable
return (
    select case when t.ts is null or fmt is null then null else
        replace(replace(replace(replace(replace(replace(replace(replace(fmt,
            '%Y', lpad(extract(year from t.ts)::int::text, 4, '0')),
            '%m', lpad(extract(month from t.ts)::int::text, 2, '0')),
            '%d', lpad(extract(day from t.ts)::int::text, 2, '0')),
            '%H', lpad(extract(hour from t.ts)::int::text, 2, '0')),
            '%M', lpad(extract(minute from t.ts)::int::text, 2, '0')),
            '%S', lpad(floor(extract(second from t.ts))::int::text, 2, '0')),
            '%j', lpad((t.ts::date - make_date(extract(year from t.ts)::int, 1, 1) + 1)::text, 3, '0')),
            '%w', extract(dow from t.ts)::int::text)
    end
    from (select regexp_match(x, '^(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{2}):(\d{2})(?::(\d{2})(?:\.\d+)?)?)?\s*$') as m) r
    cross join lateral (
        select case
            when r.m is null then null
            when r.m[1]::int < 1 or r.m[2]::int not between 1 and 12 or r.m[3]::int not between 1 and 31
                 or coalesce(r.m[4], '0')::int > 24 or coalesce(r.m[5], '0')::int > 59
                 or coalesce(r.m[6], '0')::int > 59 then null
            else (make_date(r.m[1]::int, r.m[2]::int, 1) + (r.m[3]::int - 1))
                 + make_interval(hours => coalesce(r.m[4], '0')::int,
                                 mins => coalesce(r.m[5], '0')::int,
                                 secs => coalesce(r.m[6], '0')::int)
        end as ts
    ) t
)
"""


def test_fh_strftime_plpgsql_matches_previous_sql_function(pg_raw):
    """Task 21: fh_strftime ditulis ulang sebagai plpgsql (cepat); hasil harus sama persis dengan versi
    SQL sebelumnya untuk semua input (termasuk kasus yang memang beda dari SQLite, mis. tahun 0000)."""
    import itertools
    import sqlite3
    pg_raw.execute(COMPAT_SQL.replace("{{schema}}", "public"))
    lite = sqlite3.connect(":memory:")
    dates = ["2025-01-31", "2024-02-29", "2025-02-29", "2025-04-31", "2025-12-31", "2025-00-10",
             "2025-13-01", "2025-01-00", "2025-01-32", "0000-01-01", "0001-01-01", "1999-12-31",
             "2025-03-15 10:20", "2025-03-15T08:09:10.123", "2025-12-31 24:00", "2025-12-31 23:59:59",
             "2025-03-15 25:00", "2025-03-15 10:60", "2025-03-15 10:20:60", "2025-03-15  ", "2025-3-15",
             "15/03/2025", "", " 2025-03-15", "2025-03-15x", None]
    fmts = ["%Y", "%m", "%d", "%Y-%m", "%Y-%m-%d", "%H:%M:%S", "%j", "%w", "%d/%m/%Y", "x", "", None]
    pg_raw.execute(_FH_STRFTIME_SQLFN)
    for fmt, x in itertools.product(fmts, dates):
        expected = pg_raw.scalar("select public.fh_strftime_sqlfn(%s, %s)", (fmt, x))
        assert pg_raw.scalar("select public.fh_strftime(%s, %s)", (fmt, x)) == expected, (fmt, x)
        if x not in ("0000-01-01", "2025-12-31 24:00"):   # beda dari SQLite sejak awal (bukan Task 21)
            assert expected == lite.execute("select strftime(?, ?)", (fmt, x)).fetchone()[0], (fmt, x)


def test_text_columns_use_binary_collation(tmp_path, pg_raw):
    """R28: kolom text memakai COLLATE "C" -> urutan byte seperti BINARY di SQLite."""
    db = _make_db(tmp_path / "coll.db",
                  "create table t (id INTEGER PRIMARY KEY, nama TEXT UNIQUE);",
                  [("insert into t (nama) values (?)", (v,)) for v in ("a", "b", "B")])
    sql = generate(db).replace("{{schema}}", "gen_coll")
    pg_raw.execute("create schema gen_coll"); pg_raw.execute(sql)
    assert pg_raw.scalar(
        "select collation_name from information_schema.columns "
        "where table_schema='gen_coll' and table_name='t' and column_name='nama'") == "C"
    for v in ("a", "b", "B"):
        pg_raw.execute("insert into gen_coll.t (nama) values (%s)", (v,))
    assert pg_raw.scalar(
        "select string_agg(nama, ',' order by nama) from gen_coll.t") == "B,a,b"
