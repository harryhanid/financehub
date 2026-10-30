# tests/test_ppd_api.py -- API data PR Portal (app/db_migrations_prportal): public.ppd_* berkunci
# (public.ppd_keys) yang hanya menyentuh schema milik kunci (prportal / prportal_staging / prportal_test).
import hashlib
import importlib.util
import json
import os

import pytest

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRPORTAL_DIR = os.path.join(APP_DIR, "db_migrations_prportal")
FINANCEHUB_DIR = os.path.join(APP_DIR, "db_migrations")
PRPORTAL_FILES = [os.path.join(PRPORTAL_DIR, f) for f in ("0001_ppd_api.sql", "0002_schema_base.sql")]

KEY = "kunci-uji-ppd-test-0123456789abcdefghijklmnop"
KEY_STAGING = "kunci-uji-ppd-staging-0123456789abcdefghijklm"
KEY_REVOKED = "kunci-uji-ppd-dicabut-0123456789abcdefghijklm"


def _hash(k):
    return hashlib.sha256(k.encode("utf-8")).hexdigest()


def _load_apply_migrations():
    spec = importlib.util.spec_from_file_location(
        "apply_migrations_ppd",
        os.path.join(APP_DIR, "..", "scripts", "pg_migrate", "apply_migrations.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _Db:
    def __init__(self, dsn):
        import psycopg2

        self.conn = psycopg2.connect(dsn)
        self.conn.autocommit = True

    def execute(self, sql, params=None):
        with self.conn.cursor() as cur:
            cur.execute(sql, params)

    def scalar(self, sql, params=None):
        with self.conn.cursor() as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
        return None if row is None else row[0]


@pytest.fixture(scope="module")
def ppd(pg_dsn):
    """Terapkan 0001+0002 ke prportal_test dan prportal_staging (Postgres test lokal), buat kunci uji."""
    from fhdb.backends import PgBackend

    am = _load_apply_migrations()
    backend = PgBackend(pg_dsn)
    db = _Db(pg_dsn)
    try:
        for schema in ("prportal_test", "prportal_staging"):
            am.apply(backend, schema, PRPORTAL_FILES, dir=PRPORTAL_DIR)
        hashes = [_hash(KEY), _hash(KEY_STAGING), _hash(KEY_REVOKED)]
        db.execute("delete from public.ppd_keys where key_hash = any(%s)", (hashes,))
        db.execute("insert into public.ppd_keys (key_hash, schema_name, label) values (%s, 'prportal_test', 'uji')",
                   (hashes[0],))
        db.execute("insert into public.ppd_keys (key_hash, schema_name, label)"
                   " values (%s, 'prportal_staging', 'uji staging')", (hashes[1],))
        db.execute("insert into public.ppd_keys (key_hash, schema_name, label, revoked_at)"
                   " values (%s, 'prportal_test', 'uji dicabut', now())", (hashes[2],))
        yield db
    finally:
        try:
            if db.scalar("select to_regclass('public.ppd_keys')") is not None:
                db.execute("delete from public.ppd_keys where key_hash = any(%s)",
                           ([_hash(KEY), _hash(KEY_STAGING), _hash(KEY_REVOKED)],))
            db.execute("drop schema if exists prportal_test cascade")
            db.execute("drop schema if exists prportal_staging cascade")
        finally:
            db.conn.close()
            backend.close()


@pytest.fixture
def db(ppd):
    ppd.execute("delete from prportal_test.announcements where true")
    ppd.execute("delete from prportal_staging.announcements where true")
    return ppd


def _rpc(db, fn, *args):
    casts = {
        "ppd_select": "(%s, %s, %s::jsonb, %s, %s)",
        "ppd_upsert": "(%s, %s, %s::jsonb)",
        "ppd_delete": "(%s, %s, %s::jsonb)",
        "ppd_stats": "(%s, %s)",
    }
    if fn == "ppd_select":
        args = (args + ("{}", 1000, 0)[len(args) - 2:]) if len(args) < 5 else args
    params = [json.dumps(a) if isinstance(a, (dict, list)) else a for a in args]
    v = db.scalar(f"select public.{fn}{casts[fn]}::text", params)
    return None if v is None else json.loads(v)


def _rows(n_from=1, n=2, active=(True, False)):
    return [{"timestamp": f"2026-10-0{i}T08:00:00+00:00", "title": f"T{i}", "message": f"M{i}",
             "author": "harry", "active": active[(i - n_from) % len(active)]}
            for i in range(n_from, n_from + n)]


def _err(excinfo):
    e = excinfo.value
    return getattr(e, "pgcode", None), str(e)


def test_select_upsert_roundtrip(db):
    rows = _rows()
    # kirim terbalik: hasil select tetap urut PK
    assert _rpc(db, "ppd_upsert", KEY, "announcements", list(reversed(rows))) == {"upserted": 2}
    got = _rpc(db, "ppd_select", KEY, "announcements")
    assert [r["title"] for r in got] == ["T1", "T2"]
    assert got[0]["active"] is True and got[0]["author"] == "harry"
    changed = dict(rows[0], title="T1 baru")
    assert _rpc(db, "ppd_upsert", KEY, "announcements", [changed]) == {"upserted": 1}
    assert _rpc(db, "ppd_stats", KEY, "announcements") == {
        "rows": 2, "columns": ["timestamp", "title", "message", "author", "active"]}
    got = _rpc(db, "ppd_select", KEY, "announcements")
    assert [r["title"] for r in got] == ["T1 baru", "T2"]


def test_upsert_partial_columns_keeps_others(db):
    _rpc(db, "ppd_upsert", KEY, "announcements", _rows(n=1))
    _rpc(db, "ppd_upsert", KEY, "announcements", [{"timestamp": "2026-10-01T08:00:00+00:00", "active": False}])
    got = _rpc(db, "ppd_select", KEY, "announcements")
    assert got[0]["title"] == "T1" and got[0]["active"] is False


def test_filter_and_paging(db):
    _rpc(db, "ppd_upsert", KEY, "announcements", _rows(n=4, active=(True, False)))  # T1,T3 aktif
    active = _rpc(db, "ppd_select", KEY, "announcements", {"active": True}, 1000, 0)
    assert [r["title"] for r in active] == ["T1", "T3"]
    page = _rpc(db, "ppd_select", KEY, "announcements", {"active": True}, 1, 1)
    assert [r["title"] for r in page] == ["T3"]
    assert _rpc(db, "ppd_select", KEY, "announcements", {"active": True}, 1, 5) == []
    both = _rpc(db, "ppd_select", KEY, "announcements", {"active": False, "author": "harry"}, 1000, 0)
    assert [r["title"] for r in both] == ["T2", "T4"]


def test_select_limit_bounds(db):
    for limit, offset in ((5001, 0), (-1, 0), (10, -1)):
        with pytest.raises(Exception) as ei:
            _rpc(db, "ppd_select", KEY, "announcements", {}, limit, offset)
        assert _err(ei)[0] == "22023"


def test_select_filter_unknown_column_named_in_error(db):
    for col in ("charged_to", "xmin", "ctid"):
        with pytest.raises(Exception) as ei:
            _rpc(db, "ppd_select", KEY, "announcements", {col: 1}, 10, 0)
        code, msg = _err(ei)
        assert code == "42703" and col in msg


def test_delete_by_keys(db):
    rows = _rows()
    _rpc(db, "ppd_upsert", KEY, "announcements", rows)
    res = _rpc(db, "ppd_delete", KEY, "announcements", [rows[0]["timestamp"], "2030-01-01T00:00:00+00:00"])
    assert res == {"deleted": 1}
    assert [r["title"] for r in _rpc(db, "ppd_select", KEY, "announcements")] == ["T2"]
    assert _rpc(db, "ppd_delete", KEY, "announcements", []) == {"deleted": 0}


@pytest.mark.parametrize("table", ["siswa", "financehub.siswa", "announcements; drop table x", "ppd_keys",
                                   "_x", "ppd_x", "Announcements", "", None,
                                   "prportal_staging.announcements", "pg_class", "t"])
@pytest.mark.parametrize("fn", ["ppd_select", "ppd_upsert", "ppd_delete", "ppd_stats"])
def test_table_outside_schema_rejected(db, fn, table):
    args = {"ppd_select": (), "ppd_upsert": ([{"title": "x"}],), "ppd_delete": (["x"],), "ppd_stats": ()}[fn]
    with pytest.raises(Exception) as ei:
        _rpc(db, fn, KEY, table, *args)
    code, msg = _err(ei)
    assert code == "22023", msg
    assert "ppd: tabel tidak dikenal" in msg


def test_upsert_unknown_column_named_in_error(db):
    bad = dict(_rows(n=1)[0], charged_to="X")
    with pytest.raises(Exception) as ei:
        _rpc(db, "ppd_upsert", KEY, "announcements", [bad])
    code, msg = _err(ei)
    assert code == "42703"
    assert "charged_to" in msg
    assert _rpc(db, "ppd_stats", KEY, "announcements")["rows"] == 0


def test_upsert_is_one_transaction(db):
    rows = _rows(n=2)
    rows[1]["active"] = "bukan-boolean"
    with pytest.raises(Exception):
        _rpc(db, "ppd_upsert", KEY, "announcements", rows)
    assert _rpc(db, "ppd_stats", KEY, "announcements")["rows"] == 0


def test_upsert_rejects_non_array(db):
    for bad in ({"title": "x"}, [1, 2], ["x"]):
        with pytest.raises(Exception) as ei:
            _rpc(db, "ppd_upsert", KEY, "announcements", bad)
        assert _err(ei)[0] == "22023"


@pytest.mark.parametrize("key", [KEY_REVOKED, "acak-tidak-terdaftar", "", None, _hash(KEY)])
@pytest.mark.parametrize("fn", ["ppd_select", "ppd_upsert", "ppd_delete", "ppd_stats"])
def test_revoked_key_rejected(db, fn, key):
    args = {"ppd_select": (), "ppd_upsert": (_rows(n=1),), "ppd_delete": (["x"],), "ppd_stats": ()}[fn]
    with pytest.raises(Exception) as ei:
        _rpc(db, fn, key, "announcements", *args)
    code, msg = _err(ei)
    assert code == "42501"
    assert ei.value.diag.message_primary == "ppd: kunci tidak valid"


def test_staging_key_cannot_reach_prod(db):
    # schema lain dengan tabel sama: baris ditulis langsung (bukan lewat API)
    db.execute("insert into prportal_staging.announcements (\"timestamp\", title) values (now(), 'RAHASIA STAGING')")
    _rpc(db, "ppd_upsert", KEY, "announcements", _rows(n=1))
    got = _rpc(db, "ppd_select", KEY, "announcements")
    assert [r["title"] for r in got] == ["T1"]
    assert _rpc(db, "ppd_stats", KEY, "announcements")["rows"] == 1
    assert db.scalar("select count(*) from prportal_staging.announcements") == 1
    assert [r["title"] for r in _rpc(db, "ppd_select", KEY_STAGING, "announcements")] == ["RAHASIA STAGING"]
    # delete dengan kunci test tidak menyentuh staging
    ts = _rpc(db, "ppd_select", KEY_STAGING, "announcements")[0]["timestamp"]
    assert _rpc(db, "ppd_delete", KEY, "announcements", [ts]) == {"deleted": 0}
    assert db.scalar("select count(*) from prportal_staging.announcements") == 1


def test_keys_schema_check_constraint(db):
    for schema in ("financehub", "financehub_test", "public", "pg_catalog"):
        with pytest.raises(Exception) as ei:
            db.execute("insert into public.ppd_keys (key_hash, schema_name, label) values ('x', %s, 'jahat')",
                       (schema,))
        assert _err(ei)[0] == "23514"


def test_functions_security_definer_and_not_public(db):
    rows = {}
    with db.conn.cursor() as cur:
        cur.execute(
            "select p.proname, p.prosecdef, p.proconfig::text, has_function_privilege('public', p.oid, 'EXECUTE')"
            " from pg_proc p join pg_namespace n on n.oid = p.pronamespace"
            " where n.nspname = 'public' and p.proname like 'ppd\\_%'")
        for name, secdef, cfg, pub in cur.fetchall():
            rows[name] = (secdef, cfg, pub)
    assert set(rows) == {"ppd_key_schema", "ppd_check_table", "ppd_check_cols", "ppd_pk_cols",
                         "ppd_select", "ppd_upsert", "ppd_delete", "ppd_stats"}
    for name, (secdef, cfg, pub) in rows.items():
        assert secdef is True, name
        assert "search_path=public, pg_temp" in cfg, (name, cfg)
        assert pub is False, name
    assert db.scalar("select relrowsecurity from pg_class where oid = 'public.ppd_keys'::regclass") is True
    assert db.scalar("select has_table_privilege('public', 'public.ppd_keys', 'SELECT')") is False
    assert db.scalar("select has_schema_privilege('public', 'prportal_test', 'USAGE')") is False


def test_migrations_idempotent(ppd, pg_dsn):
    from fhdb.backends import PgBackend

    am = _load_apply_migrations()
    backend = PgBackend(pg_dsn)
    try:
        ppd.execute("insert into prportal_test.announcements (\"timestamp\", title) values (now(), 'tetap')")
        am.apply(backend, "prportal_test", PRPORTAL_FILES, dir=PRPORTAL_DIR)
        assert ppd.scalar("select count(*) from prportal_test.announcements where title = 'tetap'") == 1
        assert ppd.scalar("select count(*) from public.ppd_keys where key_hash = %s", (_hash(KEY),)) == 1
    finally:
        ppd.execute("delete from prportal_test.announcements where true")
        backend.close()


def test_apply_migrations_dir_schema_guard(pg_backend, tmp_path):
    am = _load_apply_migrations()
    with pytest.raises(ValueError):
        am.apply(pg_backend, "financehub", PRPORTAL_FILES, dir=PRPORTAL_DIR)
    with pytest.raises(ValueError):
        am.apply(pg_backend, "financehub_test", PRPORTAL_FILES, dir=PRPORTAL_DIR)
    with pytest.raises(ValueError):
        am.apply(pg_backend, "prportal_test", PRPORTAL_FILES)  # dir default = app/db_migrations
    with pytest.raises(ValueError):
        am.apply(pg_backend, "prportal_test", PRPORTAL_FILES, dir=FINANCEHUB_DIR)
    with pytest.raises(ValueError):
        am.apply(pg_backend, "prportal_test", PRPORTAL_FILES, dir=str(tmp_path))  # dir tak dikenal


def test_apply_migrations_file_must_match_dir(pg_backend):
    am = _load_apply_migrations()
    # file migrasi FinanceHub tidak boleh diterapkan ke schema prportal, dan sebaliknya
    with pytest.raises(ValueError):
        am.apply(pg_backend, "prportal_test", [os.path.join(FINANCEHUB_DIR, "0002_schema.sql")], dir=PRPORTAL_DIR)
    with pytest.raises(ValueError):
        am.apply(pg_backend, "financehub_test", PRPORTAL_FILES)


def test_apply_migrations_prportal_dir_rejects_http_backend():
    from fhdb.backends import HttpBackend

    am = _load_apply_migrations()
    backend = HttpBackend("https://contoh.invalid", "bukan-kunci")  # tidak pernah dihubungi
    with pytest.raises(ValueError):
        am.apply(backend, "prportal_test", PRPORTAL_FILES, dir=PRPORTAL_DIR)


def test_apply_migrations_cli_dir_default_files():
    am = _load_apply_migrations()
    assert [p.name for p in am.default_files("pg", PRPORTAL_DIR)] == ["0001_ppd_api.sql", "0002_schema_base.sql"]
    assert "0001_fh_exec.sql" in [p.name for p in am.default_files("pg")]


def test_sheet_retry_reachable_via_api(db):
    assert _rpc(db, "ppd_stats", KEY, "sheet_retry") == {
        "rows": 0, "columns": ["id", "module", "sheet_name", "row_key", "payload", "error", "created_at", "done_at"]}
