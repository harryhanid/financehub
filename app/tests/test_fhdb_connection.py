"""Test fhdb.connection: objek mirip sqlite3 di atas fh_exec (PgBackend lokal, schema financehub_test)."""
import sqlite3

import pytest


# --- dari brief Task 5 ---

def test_execute_fetch_row_access(conn):
    conn.execute('insert into t ("Nama", jumlah) values (?, ?)', ("Budi", 1.5))
    row = conn.execute('select id, "Nama", jumlah from t').fetchone()
    assert row[1] == "Budi" and row["Nama"] == "Budi" and dict(row)["jumlah"] == 1.5
    assert row.keys() == ["id", "Nama", "jumlah"]

def test_row_key_case_insensitive_fallback(conn):
    row = conn.execute("select 5 as Total").fetchone()   # Postgres: key 'total'
    assert row["Total"] == 5 and row["total"] == 5

def test_lastrowid_from_insert(conn):
    cur = conn.execute('insert into t ("Nama") values (?)', ("x",))
    assert isinstance(cur.lastrowid, int) and cur.lastrowid > 0

def test_lastrowid_none_for_table_without_id(conn):
    conn.execute("create table if not exists noid (k text primary key)")
    assert conn.execute("insert into noid values (?)", ("a",)).lastrowid is None

def test_executemany_is_one_atomic_call(conn, fhdb_stats):
    with pytest.raises(sqlite3.IntegrityError):
        conn.executemany('insert into t ("Nama") values (?)', [("a",), (None,)])
    assert conn.execute('select count(*) from t where "Nama" = ?', ("a",)).fetchone()[0] == 0
    assert fhdb_stats.calls == 2   # executemany + select

def test_rollback_after_write_logs_warning(conn, caplog):
    conn.execute('insert into t ("Nama") values (?)', ("w",))
    conn.rollback()
    assert "rollback" in caplog.text.lower()

def test_pragma_table_info_emulated(conn):
    cols = [r[1] for r in conn.execute("PRAGMA table_info(t)")]
    assert cols == ["id", "Nama", "jumlah"]

def test_pragma_foreign_keys_is_noop(conn):
    conn.execute("PRAGMA foreign_keys = ON")


# --- tambahan di luar brief ---

def test_row_positional_tuple_len_and_missing_key(conn):
    row = conn.execute("select 1 as a, 'x' as b").fetchone()
    assert tuple(row) == (1, "x") and len(row) == 2 and row[-1] == "x" and row[0:1] == (1,)
    with pytest.raises(IndexError):
        row["nope"]
    with pytest.raises(IndexError):
        row[5]

def test_row_exact_key_wins_over_case_insensitive(conn):
    row = conn.execute('select 1 as "a", 2 as "A"').fetchone()
    assert row["a"] == 1 and row["A"] == 2

def test_insert_without_returning_exposes_no_rows_and_rowcount(conn):
    cur = conn.execute('insert into t ("Nama") values (?), (?)', ("a", "b"))
    assert cur.fetchall() == [] and cur.description is None
    assert cur.rowcount == 2 and cur.lastrowid == 2

def test_insert_with_trailing_comment_and_semicolon(conn):
    cur = conn.execute('insert into t ("Nama") values (?); -- catatan', ("a",))
    assert cur.lastrowid == 1

def test_insert_with_explicit_returning_keeps_rows(conn):
    cur = conn.execute('insert into t ("Nama") values (?) returning "Nama", id', ("a",))
    assert cur.fetchone()["Nama"] == "a" and cur.lastrowid == 1

def test_insert_returning_word_in_literal_still_gets_lastrowid(conn):
    cur = conn.execute("insert into t (\"Nama\") values ('returning')")
    assert cur.lastrowid == 1 and cur.fetchall() == []

def test_update_rowcount_and_select_rowcount(conn):
    conn.executemany('insert into t ("Nama") values (?)', [("a",), ("b",), ("c",)])
    assert conn.execute('update t set jumlah = ? where "Nama" <> ?', (1, "a")).rowcount == 2
    assert conn.execute("select * from t").rowcount == -1

def test_executemany_rowcount_sum_and_lastrowid(conn, fhdb_stats):
    cur = conn.executemany('insert into t ("Nama") values (?)', [("a",), ("b",)])
    assert cur.rowcount == 2 and cur.lastrowid == 2 and fhdb_stats.calls == 1

def test_executemany_empty_makes_no_call(conn, fhdb_stats):
    cur = conn.executemany('insert into t ("Nama") values (?)', [])
    assert cur.rowcount == 0 and fhdb_stats.calls == 0

def test_executescript_one_call_and_skips_pragma(conn, fhdb_stats):
    conn.executescript("""
        PRAGMA foreign_keys = ON;
        -- komentar; dengan titik koma
        insert into t ("Nama") values ('s;1');
        insert into t ("Nama") values ('s2');
    """)
    assert fhdb_stats.calls == 1
    assert [r[0] for r in conn.execute('select "Nama" from t order by id')] == ["s;1", "s2"]

def test_batch_is_one_atomic_call(conn, fhdb_stats):
    curs = conn.batch([('insert into t ("Nama") values (?)', ("a",)),
                       ('select count(*) as n from t', ()),
                       ("PRAGMA table_info(t)", ())])
    assert fhdb_stats.calls == 1
    assert curs[0].lastrowid == 1 and curs[1].fetchone()["n"] == 1
    assert [r["name"] for r in curs[2]] == ["id", "Nama", "jumlah"]
    with pytest.raises(sqlite3.IntegrityError):
        conn.batch([('insert into t ("Nama") values (?)', ("b",)),
                    ('insert into t ("Nama") values (?)', (None,))])
    assert conn.execute("select count(*) from t").fetchone()[0] == 1

def test_pragma_table_info_columns(conn):
    rows = conn.execute("PRAGMA table_info('t')").fetchall()
    assert rows[0].keys() == ["cid", "name", "type", "notnull", "dflt_value", "pk"]
    by_name = {r["name"]: r for r in rows}
    assert [r["cid"] for r in rows] == [0, 1, 2]
    assert by_name["id"]["pk"] == 1 and by_name["Nama"]["pk"] == 0
    assert by_name["Nama"]["notnull"] == 1 and by_name["jumlah"]["notnull"] == 0
    assert by_name["Nama"]["type"] == "text"

def test_pragma_table_info_unknown_table_is_empty(conn):
    assert conn.execute("PRAGMA table_info(tidak_ada)").fetchall() == []

def test_pragma_is_noop_without_call(conn, fhdb_stats):
    assert conn.execute("PRAGMA journal_mode=WAL").fetchall() == []
    assert fhdb_stats.calls == 0

def test_commit_noop_and_rollback_without_write_is_silent(conn, caplog):
    conn.execute('insert into t ("Nama") values (?)', ("w",))
    conn.commit()
    conn.execute("select 1")
    conn.rollback()
    assert "rollback" not in caplog.text.lower()

def test_fetchmany_iteration_and_description(conn):
    conn.executemany('insert into t ("Nama") values (?)', [("a",), ("b",), ("c",)])
    cur = conn.execute('select id, "Nama" from t order by id')
    assert [d[0] for d in cur.description] == ["id", "Nama"]
    assert [r[1] for r in cur.fetchmany(2)] == ["a", "b"]
    assert cur.fetchone()[1] == "c" and cur.fetchone() is None and cur.fetchall() == []

def test_cursor_method_execute(conn):
    cur = conn.cursor()
    assert cur.execute("select 7 as x").fetchone()["x"] == 7

def test_closed_connection_raises(conn):
    conn.close()
    with pytest.raises(sqlite3.ProgrammingError):
        conn.execute("select 1")

def test_error_maps_to_sqlite_classes(conn):
    with pytest.raises(sqlite3.DatabaseError):
        conn.execute("select * from tabel_tidak_ada")

def test_context_manager(conn):
    with conn as c:
        c.execute('insert into t ("Nama") values (?)', ("ctx",))
    assert conn.execute("select count(*) from t").fetchone()[0] == 1

def test_get_conn_pg(monkeypatch, pg_dsn, fhdb_stats):
    import config
    import fhdb
    monkeypatch.setattr(config, "DB_BACKEND", "pg")
    monkeypatch.setattr(config, "FH_PG_DSN", pg_dsn)
    monkeypatch.setattr(config, "DB_SCHEMA", "financehub_test")
    c = fhdb.get_conn()
    assert c.execute("select current_schema() as s").fetchone()["s"] == "financehub_test"
    assert fhdb_stats.calls == 1

def test_get_conn_rejects_unknown_backend(monkeypatch):
    import config
    import fhdb
    monkeypatch.setattr(config, "DB_BACKEND", "sqlite")
    with pytest.raises(ValueError):
        fhdb.get_conn()

def test_config_new_settings_exist():
    import config
    for name in ("DB_BACKEND", "DB_SCHEMA", "SUPABASE_URL", "SUPABASE_SERVICE_KEY", "FH_PG_DSN"):
        assert hasattr(config, name)
