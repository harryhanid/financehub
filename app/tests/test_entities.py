# tests/test_entities.py -- tabel entities per perusahaan, tabel PA entitas baru (sm, ef), penomoran dengan prefix dari entities.
import importlib.util
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import config
from database import get_conn
from tests.test_prportal_fn import _std_siswa, _std_lines, _payload, _submit, _yyyy

SMT, ETF = 1, 2

EXPECTED = {
    SMT: [("AGRI", "agri", "etf_pa", "SMT", "AGRI"), ("APP", "app", "app_pa", "APP", "APP"), ("LAND", "sml", "sml_pa", "LAND", "LAND"),
          ("EFIN", "energy", "energy_pa", "EFIN", "EFIN"), ("SMT", "sm", "sm_pa", "SM", "SMT")],
    ETF: [("AGRI", "agri", "etf_pa", "ETF", "AGRI"), ("APP", "app", "app_pa", "APP", "APP"), ("LAND", "sml", "sml_pa", "LAND", "LAND"),
          ("EFIN", "energy", "energy_pa", "EFIN", "EFIN"), ("SETF", "setf", "setf_pa", "SETF", "SETF"), ("ETF", "ef", "ef_pa", "EF", "ETF")],
}


def _q(sql, params=()):
    conn = get_conn()
    try:
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


def _next(tbl, company, prefix, year="2026"):
    conn = get_conn()
    try:
        return conn.execute("SELECT fn_etf_pa_next_pa_number(?, ?, ?, ?) AS n", (tbl, company, prefix, year)).fetchone()["n"]
    finally:
        conn.close()


def test_entities_seed_matches_decision_table():
    for company, expected in EXPECTED.items():
        rows = _q("SELECT code, tab_key, pa_table, pa_prefix, pillar, lines_table FROM entities WHERE company_id=? ORDER BY urutan", (company,))
        assert [(r["code"], r["tab_key"], r["pa_table"], r["pa_prefix"], r["pillar"]) for r in rows] == expected
        assert all(r["lines_table"] == r["pa_table"] + "_lines" for r in rows)
    assert _q("SELECT count(*) AS n FROM entities")[0]["n"] == 11


def test_new_tables_clone_columns_and_are_empty():
    def cols(t):
        return [r["column_name"] for r in _q("SELECT column_name FROM information_schema.columns WHERE table_schema=? AND table_name=? ORDER BY ordinal_position", (config.DB_SCHEMA, t))]
    for new in ("sm_pa", "ef_pa"):
        assert cols(new) == cols("etf_pa") and cols(new)
        assert _q(f"SELECT count(*) AS n FROM {new}")[0]["n"] == 0
    for new in ("sm_pa_lines", "ef_pa_lines"):
        assert cols(new) == cols("etf_pa_lines") and cols(new)
    rls = _q("SELECT relname, relrowsecurity FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname=? AND relname IN ('sm_pa','sm_pa_lines','ef_pa','ef_pa_lines')", (config.DB_SCHEMA,))
    assert len(rls) == 4 and all(r["relrowsecurity"] for r in rls)


def test_next_number_accepts_new_tables_and_rejects_unknown():
    assert _next("sm_pa", SMT, "SM") == "PA/SM/001/2026"
    assert _next("ef_pa", ETF, "EF") == "PA/EF/001/2026"
    with pytest.raises(Exception):
        _next("users", ETF, "X")
    with pytest.raises(Exception):
        _next(None, ETF, "X")


def test_sm_numbering_per_company_starts_at_001_and_increments():
    conn = get_conn()
    try:
        conn.execute("INSERT INTO sm_pa (company_id, pa_number, created_at) VALUES (?, ?, ?)", (SMT, "PA/SM/001/2026", "2026-01-01T00:00:00"))
        conn.commit()
    finally:
        conn.close()
    assert _next("sm_pa", SMT, "SM") == "PA/SM/002/2026"
    assert _next("sm_pa", ETF, "SM") == "PA/SM/001/2026", "perusahaan lain dihitung terpisah"


def test_land_continues_after_existing_sml_rows():
    conn = get_conn()
    try:
        for i in range(1, 4):
            conn.execute("INSERT INTO sml_pa (company_id, pa_number, created_at) VALUES (?, ?, ?)", (ETF, f"PA/SML/00{i}/2026", "2026-01-01T00:00:00"))
        conn.commit()
    finally:
        conn.close()
    assert _next("sml_pa", ETF, "LAND") == "PA/LAND/004/2026"


def test_entity_prefix_and_company_of_cost_center():
    def one(sql, p=()):
        return _q(sql, p)[0][0]
    assert one("SELECT fn_prp_entity_prefix(?, ?)", (SMT, "agri")) == "SMT"
    assert one("SELECT fn_prp_entity_prefix(?, ?)", (SMT, "sm")) == "SM"
    assert one("SELECT fn_prp_entity_prefix(?, ?)", (ETF, "ef")) == "EF"
    assert one("SELECT fn_prp_entity_prefix(?, ?)", (ETF, "sml")) == "LAND"
    assert one("SELECT fn_prp_entity_prefix(?, ?)", (ETF, "sm")) is None, "tab bukan milik perusahaan"
    assert one("SELECT fn_prp_entity_prefix(?, ?)", (SMT, "setf")) is None
    assert one("SELECT fn_prp_company_of_cost_center(?)", ("POOFFM",)) == SMT
    assert one("SELECT fn_prp_company_of_cost_center(?)", ("tfscho",)) == ETF
    for bad in ("XX1", "", None, "  ", "P", "T"):
        assert one("SELECT fn_prp_company_of_cost_center(?)", (bad,)) is None, repr(bad)


@pytest.mark.parametrize("jenis,prefix", [("agri", "ETF"), ("sml", "LAND"), ("energy", "EFIN"), ("app", "APP"), ("setf", "SETF")])
def test_submit_pa_uses_entity_prefix(jenis, prefix):
    _std_siswa("E1")
    res = _submit(_payload("E1", _std_lines("E1"), jenis=jenis))
    assert res["ok"] is True, res
    assert res["pa_number"] == f"PA/{prefix}/001/{_yyyy()}"


def test_migration_is_idempotent(fhdb_schema):
    from tests.fhdb_fixtures import MIGRATIONS_DIR
    spec = importlib.util.spec_from_file_location(
        "apply_migrations", os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "pg_migrate", "apply_migrations.py"))
    am = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(am)
    path = os.path.join(MIGRATIONS_DIR, "0008_entities.sql")
    am.apply(fhdb_schema, config.DB_SCHEMA, [path])
    am.apply(fhdb_schema, config.DB_SCHEMA, [path])
    assert _q("SELECT count(*) AS n FROM entities")[0]["n"] == 11
    assert [r["pa_prefix"] for r in _q("SELECT pa_prefix FROM entities WHERE company_id=? AND tab_key='sml'", (ETF,))] == ["LAND"]
