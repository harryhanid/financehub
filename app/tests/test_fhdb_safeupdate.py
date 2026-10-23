"""R59: Supabase memuat pg_safeupdate -- UPDATE/DELETE tanpa WHERE ditolak (SQLSTATE 21000), juga di
dalam fungsi plpgsql / DO block. PgBackend (test lokal) mengemulasikannya; test ini juga memindai
db_migrations dan body DO yang dibangun aplikasi, yang tidak terlihat oleh guard sisi klien."""
import glob
import os

import pytest

from fhdb import safeupdate
from fhdb.errors import DatabaseError, IntegrityError, OperationalError, ProgrammingError

MIGRATIONS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "db_migrations")


def _bad(sql):
    return safeupdate.unguarded_dml(sql)


# ------------------------------------------------------------------ guard unit tests

@pytest.mark.parametrize("sql", [
    "UPDATE t SET a = 1",
    "update t set a = 1;",
    'UPDATE "Tabel" SET "A" = 1',
    "UPDATE only s.t AS x SET a = 1",
    "DELETE FROM t",
    "delete from s.t;",
    'DELETE FROM "x" -- WHERE id = 1',
    "DELETE FROM t /* where id = 1 */",
    "UPDATE t SET a = 'x WHERE y'",
    "UPDATE t SET a = (SELECT max(b) FROM u WHERE u.id = 1)",
    "DELETE FROM t WHERE_x = 1",
    "UPDATE t SET a = 1 FROM (SELECT id FROM u WHERE u.k = 2) s",
    "DELETE FROM t USING u",
    "WITH x AS (SELECT 1 WHERE true) UPDATE t SET a = 1",
    "WITH x AS (SELECT id FROM u WHERE k = 1) DELETE FROM t",
    "WITH d AS (DELETE FROM t RETURNING id) SELECT count(*) FROM d WHERE true",
    "WITH u AS (UPDATE t SET a = 1 RETURNING id) SELECT * FROM u",
    "INSERT INTO log SELECT * FROM (WITH d AS (DELETE FROM t RETURNING *) SELECT * FROM d) z",
])
def test_unguarded_dml_detected(sql):
    assert _bad(sql), sql


@pytest.mark.parametrize("sql", [
    "UPDATE t SET a = 1 WHERE id = 2",
    "update t set a = 1 where true",
    'UPDATE "Tabel" SET "A" = 1 WHERE "Id" = ?',
    "DELETE FROM t WHERE id IN (SELECT id FROM u)",
    "DELETE FROM t USING u WHERE t.id = u.id",
    "UPDATE t SET a = u.a FROM u WHERE t.id = u.id RETURNING t.id",
    "WITH x AS (SELECT 1) UPDATE t SET a = 1 WHERE id = 1",
    "WITH d AS (DELETE FROM t WHERE id = 1 RETURNING id) SELECT * FROM d",
    "SELECT * FROM t FOR UPDATE",
    "SELECT * FROM t FOR NO KEY UPDATE OF t",
    "INSERT INTO t (id, a) VALUES (1, 2) ON CONFLICT (id) DO UPDATE SET a = excluded.a",
    "SELECT 'DELETE FROM t' AS s",
    'SELECT "update" FROM t',
    "CREATE TABLE t (id bigint REFERENCES u (id) ON DELETE CASCADE ON UPDATE CASCADE)",
    "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA s TO r",
    "TRUNCATE t",
    "DO 'BEGIN INSERT INTO t SELECT * FROM u; END'",
])
def test_guarded_or_not_dml_accepted(sql):
    assert not _bad(sql), sql


def test_nested_finds_dml_inside_do_and_function_bodies():
    do = "do 'begin execute format(''delete from s.%I'', ''t''); end'"
    assert not _bad(do)  # guard sisi klien tidak melihat isi body (string)
    assert safeupdate.unguarded_dml(do, nested=True)
    fn = ("create function f() returns void language plpgsql as '\nbegin\n"
          "  update s.t set a = 1;\n  delete from s.t where id = 1;\nend'")
    found = safeupdate.unguarded_dml(fn, nested=True)
    assert len(found) == 1 and found[0].startswith("UPDATE")
    dollar = "create function f() returns void language plpgsql as $$ begin delete from t; end $$"
    assert safeupdate.unguarded_dml(dollar, nested=True)


def test_check_raises_sqlstate_21000():
    with pytest.raises(DatabaseError) as ei:
        safeupdate.check("UPDATE t SET a = 1")
    e = ei.value
    assert e.sqlstate == "21000"
    assert str(e).startswith("[21000] UPDATE requires a WHERE clause")
    assert not isinstance(e, (IntegrityError, OperationalError, ProgrammingError))
    with pytest.raises(DatabaseError, match=r"^\[21000\] DELETE requires a WHERE clause"):
        safeupdate.check("DELETE FROM t")
    safeupdate.check("DELETE FROM t WHERE true")


def test_pg_backend_rejects_whole_batch_without_writing(pg_backend):
    s = "financehub_test"
    pg_backend.execute_batch(["delete from t where true"], s)
    with pytest.raises(DatabaseError, match=r"^\[21000\] UPDATE requires a WHERE clause"):
        pg_backend.execute_batch(['insert into t ("Nama") values (\'a\')', "update t set jumlah = 1"], s)
    res = pg_backend.execute_batch(["select count(*)::int as n from t"], s)
    assert res[0]["rows"] == [[0]]
    with pytest.raises(DatabaseError, match=r"^\[21000\] DELETE requires a WHERE clause"):
        pg_backend.execute_batch(["delete from t"], s)


def test_http_backend_does_not_use_guard():
    import inspect

    from fhdb.backends import HttpBackend
    assert "safeupdate" not in inspect.getsource(HttpBackend)


# ------------------------------------------------------------------ static scan (nested bodies)

def test_migrations_have_no_update_delete_without_where():
    files = sorted(glob.glob(os.path.join(MIGRATIONS, "*.sql")))
    assert files
    bad = []
    for path in files:
        with open(path, encoding="utf-8") as f:
            for hit in safeupdate.unguarded_dml(f.read(), nested=True):
                bad.append(f"{os.path.basename(path)}: {hit}")
    assert not bad, "UPDATE/DELETE tanpa WHERE (ditolak pg_safeupdate Supabase):\n" + "\n".join(bad)


def test_runtime_do_blocks_have_no_update_delete_without_where():
    import ast

    from modules.general_ledger import staging

    # conftest tidak di-import ulang (efek samping saat import); ambil konstanta _RESET_ALL dari sumbernya.
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "conftest.py"), encoding="utf-8") as f:
        tree = ast.parse(f.read())
    reset_all = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
                     and any(getattr(t, "id", None) == "_RESET_ALL" for t in n.targets))
    bodies = [
        staging.copy("gl_x", "fh_stage_gl_1_ab", ["a", "b"])[0],
        staging.copy("gl_x", "fh_stage_gl_1_ab", ["a"], head_cols=("h",), head_exprs=("'x'",))[0],
        reset_all,
    ]
    bad = [hit for b in bodies for hit in safeupdate.unguarded_dml(b, nested=True)]
    assert not bad, "\n".join(bad)
