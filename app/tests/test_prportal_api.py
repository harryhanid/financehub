# tests/test_prportal_api.py -- API publik PR Portal (migrasi 0007): public.prp_* berkunci (public.prp_keys).
import hashlib
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database import get_conn
from tests.test_prportal_fn import _budget, _payload, _siswa, _std_lines, _std_siswa

KEY = "kunci-uji-prportal-0123456789abcdefghijklmnop"
KEY_REVOKED = "kunci-uji-dicabut-0123456789abcdefghijklmnop"


def _hash(k):
    return hashlib.sha256(k.encode("utf-8")).hexdigest()


def _exec(sql, params=()):
    conn = get_conn()
    try:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur
    finally:
        conn.close()


@pytest.fixture
def keys():
    """Kunci uji di public.prp_keys (clean_db hanya membersihkan financehub_test): hapus saat teardown."""
    hashes = [_hash(KEY), _hash(KEY_REVOKED)]
    _exec("DELETE FROM public.prp_keys WHERE key_hash IN (?, ?)", hashes)
    _exec("INSERT INTO public.prp_keys (key_hash, schema_name, label) VALUES (?, 'financehub_test', 'uji aktif')",
          (hashes[0],))
    _exec("INSERT INTO public.prp_keys (key_hash, schema_name, label, revoked_at)"
          " VALUES (?, 'financehub_test', 'uji dicabut', now())", (hashes[1],))
    yield
    _exec("DELETE FROM public.prp_keys WHERE key_hash IN (?, ?)", hashes)


_CALLS = {
    "prp_search_siswa": ("SELECT public.prp_search_siswa(?, ?)::text", ("zed",)),
    "prp_budget_siswa": ("SELECT public.prp_budget_siswa(?, ?)::text", ("S1",)),
    "prp_submit_pa": ("SELECT public.prp_submit_pa(?, ?::jsonb)::text", (json.dumps({"jenis": "agri"}),)),
    "prp_pa_for_print": ("SELECT public.prp_pa_for_print(?, ?, ?)::text", ("ETF-0001", "a@b.test")),
}


def _call(name, key, *args):
    sql, default = _CALLS[name]
    conn = get_conn()
    try:
        v = conn.execute(sql, (key, *(args or default))).fetchone()[0]
        return None if v is None else json.loads(v)
    finally:
        conn.close()


@pytest.mark.parametrize("name", list(_CALLS))
@pytest.mark.parametrize("key", ["salah", "", None, _hash(KEY)])
def test_api_wrong_key_rejected(keys, name, key):
    with pytest.raises(Exception) as ei:
        _call(name, key)
    assert "42501" in str(ei.value)
    assert "kunci tidak valid" in str(ei.value)


@pytest.mark.parametrize("name", list(_CALLS))
def test_api_revoked_key_rejected(keys, name):
    with pytest.raises(Exception) as ei:
        _call(name, KEY_REVOKED)
    assert "42501" in str(ei.value)


def test_api_routes_to_key_schema(keys):
    _siswa("S1", "Zed Aktif")
    _budget("S1")
    res = _call("prp_search_siswa", KEY, "zed")
    assert [r["code"] for r in res] == ["S1"]
    bud = _call("prp_budget_siswa", KEY, "S1")
    assert bud is not None and "123-456-7890" not in json.dumps(bud)


def test_api_submit_roundtrip(keys):
    _std_siswa("T1")
    res = _call("prp_submit_pa", KEY, json.dumps(_payload("T1", _std_lines("T1"))))
    assert res["ok"] is True, res
    conn = get_conn()
    try:
        row = conn.execute("SELECT pa_number, source FROM financehub_test.etf_pa").fetchone()
    finally:
        conn.close()
    assert row["pa_number"] == res["pa_number"]
    printed = _call("prp_pa_for_print", KEY, res["pa_number"], "harry@sinarmas.test")
    assert printed is not None


def test_api_key_schema_check_constraint():
    with pytest.raises(Exception) as ei:
        _exec("INSERT INTO public.prp_keys (key_hash, schema_name, label) VALUES ('x', 'pg_catalog', 'jahat')")
    assert "23514" in str(ei.value)


def test_api_functions_not_executable_by_public(fhdb_schema):
    """EXECUTE default PUBLIC dicabut dari keempat wrapper dan helper; prp_keys tanpa hak PUBLIC + RLS on."""
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT p.proname, p.prosecdef, p.proconfig::text AS cfg,"
            " has_function_privilege('public', p.oid, 'EXECUTE') AS pub"
            " FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace"
            " WHERE n.nspname = 'public' AND p.proname LIKE 'prp\\_%'").fetchall()
        rls = conn.execute("SELECT relrowsecurity FROM pg_class WHERE oid = 'public.prp_keys'::regclass").fetchone()[0]
    finally:
        conn.close()
    by = {r["proname"]: r for r in rows}
    for fn in ("prp_search_siswa", "prp_budget_siswa", "prp_submit_pa", "prp_pa_for_print", "prp_key_schema"):
        assert fn in by, fn
        assert by[fn]["prosecdef"] is True, fn
        assert by[fn]["pub"] is False, fn
        assert "search_path=public, pg_temp" in by[fn]["cfg"], fn
    assert rls is True


def test_api_anon_role_can_only_call_wrappers(keys, pg_dsn):
    """Simulasi role Supabase lokal: buat anon/authenticated, terapkan ulang 0007 (grant bersyarat aktif),
    lalu sebagai anon: wrapper jalan dengan kunci, tetapi prp_keys, helper, fn_prp_* internal, dan fh_exec ditolak."""
    import psycopg2
    from tests.fhdb_fixtures import MIGRATIONS_DIR

    _siswa("S1", "Zed Aktif")
    _budget("S1")
    with open(os.path.join(MIGRATIONS_DIR, "0007_prportal_api.sql"), encoding="utf-8") as f:
        sql0007 = f.read()
    conn = psycopg2.connect(pg_dsn)
    conn.autocommit = True
    cur = conn.cursor()
    created = []
    try:
        for r in ("anon", "authenticated"):
            cur.execute("select 1 from pg_roles where rolname = %s", (r,))
            if not cur.fetchone():
                cur.execute(f"create role {r} nologin")
                created.append(r)
        # Simulasi default privileges Supabase: anon/authenticated dapat hak atas objek baru di public.
        cur.execute("grant usage on schema public to anon, authenticated")
        cur.execute("grant all on table public.prp_keys to anon, authenticated")
        cur.execute(sql0007)

        def as_anon(q, args=()):
            cur.execute("begin")
            try:
                cur.execute("set local role anon")
                cur.execute(q, args)
                return cur.fetchone()[0]
            finally:
                cur.execute("rollback")

        assert [r["code"] for r in json.loads(as_anon(
            "select public.prp_search_siswa(%s, %s)::text", (KEY, "zed")))] == ["S1"]
        for q, args in [
            ("select count(*) from public.prp_keys", ()),
            ("select public.prp_key_schema(%s)", (KEY,)),
            ("select financehub_test.fn_prp_search_siswa(%s)::text", ("zed",)),
            ("select public.fh_exec('[\"select 1\"]'::jsonb, 'financehub_test')", ()),
        ]:
            with pytest.raises(psycopg2.Error) as ei:
                as_anon(q, args)
            assert ei.value.pgcode == "42501", (q, ei.value.pgcode)
        with pytest.raises(psycopg2.Error) as ei:
            as_anon("select public.prp_search_siswa(%s, %s)::text", ("salah", "zed"))
        assert ei.value.pgcode == "42501"
    finally:
        for r in ("anon", "authenticated"):
            cur.execute("select 1 from pg_roles where rolname = %s", (r,))
            if cur.fetchone():
                cur.execute(f"revoke all on table public.prp_keys from {r}")
                cur.execute(f"revoke usage on schema public from {r}")
        for r in created:
            cur.execute(f"drop owned by {r}")
            cur.execute(f"drop role {r}")
        conn.close()
