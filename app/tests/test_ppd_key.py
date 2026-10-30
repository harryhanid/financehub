# tests/test_ppd_key.py -- scripts/pg_migrate/ppd_key.py: buat/cabut kunci API PR Portal (public.ppd_keys).
import hashlib
import importlib.util
import os
import re

import pytest

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SCRIPT = os.path.join(APP_DIR, "..", "scripts", "pg_migrate", "ppd_key.py")
PRPORTAL_DIR = os.path.join(APP_DIR, "db_migrations_prportal")
PRPORTAL_FILES = [os.path.join(PRPORTAL_DIR, f) for f in ("0001_ppd_api.sql", "0002_schema_base.sql")]
EXEC = "financehub_test"  # schema eksekusi fh_exec yang ada di Postgres test lokal
LABEL = "uji ppd_key"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture()
def keys(fhdb_schema, pg_dsn):
    """public.ppd_keys ada (migrasi prportal diterapkan); baris berlabel uji dibersihkan sebelum/sesudah."""
    import psycopg2

    am = _load("apply_migrations_ppdkey", os.path.join(APP_DIR, "..", "scripts", "pg_migrate", "apply_migrations.py"))
    am.apply(fhdb_schema, "prportal_test", PRPORTAL_FILES, dir=PRPORTAL_DIR)
    conn = psycopg2.connect(pg_dsn)
    conn.autocommit = True

    def q(sql, params=None):
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall() if cur.description else None

    q("delete from public.ppd_keys where label = %s", (LABEL,))
    try:
        yield q
    finally:
        q("delete from public.ppd_keys where label = %s", (LABEL,))
        q("drop schema if exists prportal_test cascade")
        conn.close()


def test_create_key_stores_only_hash(fhdb_schema, keys):
    mod = _load("ppd_key", _SCRIPT)
    key = mod.create_key(fhdb_schema, "prportal_test", LABEL, exec_schema=EXEC)
    assert len(key) >= 40
    h = hashlib.sha256(key.encode("utf-8")).hexdigest()
    assert mod.key_hash(key) == h
    rows = keys("select key_hash, schema_name, label, revoked_at from public.ppd_keys where label = %s", (LABEL,))
    assert len(rows) == 1 and rows[0][:3] == (h, "prportal_test", LABEL) and rows[0][3] is None
    assert keys("select count(*) from public.ppd_keys where key_hash = %s", (key,))[0][0] == 0
    assert key not in repr(keys("select * from public.ppd_keys where label = %s", (LABEL,)))


def test_revoke_sets_revoked_at(fhdb_schema, keys):
    mod = _load("ppd_key", _SCRIPT)
    mod.create_key(fhdb_schema, "prportal_test", LABEL, exec_schema=EXEC)
    assert mod.revoke_key(fhdb_schema, LABEL, exec_schema=EXEC) == 1
    assert keys("select revoked_at is not null from public.ppd_keys where label = %s", (LABEL,))[0][0] is True
    assert mod.revoke_key(fhdb_schema, LABEL, exec_schema=EXEC) == 0  # sudah dicabut


def test_cli_rejects_test_schema():
    mod = _load("ppd_key", _SCRIPT)
    with pytest.raises(SystemExit) as ei:
        mod.main(["--schema", "prportal_test", "--label", "x"], backend=object())
    assert ei.value.code != 0


def test_cli_prints_key_once_and_requires_action(capsys):
    mod = _load("ppd_key", _SCRIPT)

    class FB:
        calls = []

        def execute_batch(self, stmts, schema):
            self.calls.append((stmts, schema))
            return [{"rowcount": 1}]

        def close(self):
            pass

    fb = FB()
    mod.main(["--schema", "prportal_staging", "--label", "PR Portal staging"], backend=fb)
    out = capsys.readouterr().out
    key = re.search(r"^PRDB_KEY=(\S+)$", out, re.M).group(1)
    assert out.count(key) == 1 and key not in repr(fb.calls)
    with pytest.raises(SystemExit):
        mod.main(["--schema", "prportal"], backend=fb)
