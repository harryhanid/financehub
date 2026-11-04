# tests/test_entities_vendor.py -- Pembebanan PR Portal: vendor disaring per perusahaan (awalan cost center) dari tabel entities.
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from database import get_conn
from tests.test_prportal_fn import _yyyy
from tests.test_prportal_vendor import _vendor, _one_budget
from tests.test_prportal_fn import _payload, _submit

SMT, ETF = 1, 2


def _search(q, cc=None):
    conn = get_conn()
    try:
        return json.loads(conn.execute("SELECT fn_prp_search_vendor(?, ?)::text", (q, cc)).fetchone()[0])
    finally:
        conn.close()


def _scalar(sql, params=()):
    conn = get_conn()
    try:
        return conn.execute(sql, params).fetchone()[0]
    finally:
        conn.close()


@pytest.fixture
def vendors():
    ids = {p: _vendor(f"PT. {p.title()}x", p) for p in ("AGRI", "SETF", "ETF", "SMT", "ENERGY", "EFIN", "LAND", "APP")}
    return ids


def _names(rows):
    return sorted(r["name"] for r in rows)


def _visible(cc):
    return {p for p in ("Agrix", "Setfx", "Etfx", "Smtx", "Energyx", "Efinx", "Landx", "Appx") if _search(p, cc)}


def test_search_vendor_filters_by_company(vendors):
    etf_set = {"Agrix", "Setfx", "Etfx", "Energyx", "Efinx", "Landx", "Appx"}
    assert _visible("TFSCHO") == etf_set and _visible("tffcon") == etf_set
    assert _visible("POOFFM") == {"Agrix", "Smtx", "Energyx", "Efinx", "Landx", "Appx"}
    for none in ("XX1", "", "  "):
        assert _visible(none) == set(), repr(none)
    assert _visible(None) == etf_set, "tanpa cost center = ETF (kompatibilitas panggilan lama)"


def test_search_vendor_returns_jenis_per_company_and_no_bank_data(vendors):
    row = _search("Smtx", "POOFFM")[0]
    assert row["jenis"] == "sm" and row["pillar"] == "SMT" and "Bank_Account_Number" not in row
    assert _search("Etfx", "TFSCHO")[0]["jenis"] == "ef"
    assert _search("Energyx", "TFSCHO")[0]["jenis"] == "energy"
    assert _search("Smtx", "TFSCHO") == [] and _search("Etfx", "POOFFM") == []
    assert _search("ab", "TFSCHO") == [], "min 3 huruf"


def test_pillar_jenis_per_company():
    j = lambda p, c=None: _scalar("SELECT fn_prp_pillar_jenis(?, ?)", (p, c))
    assert j("SMT", SMT) == "sm" and j("SMT", ETF) is None
    assert j("ETF", ETF) == "ef" and j("ETF", SMT) is None
    assert j("SETF", ETF) == "setf" and j("SETF", SMT) is None
    assert j("ENERGY", ETF) == "energy" and j("EFIN", SMT) == "energy"
    assert j("LAND", ETF) == "sml" and j("agri", SMT) == "agri"
    assert j("XYZ", ETF) is None and j(None, ETF) is None
    assert _scalar("SELECT fn_prp_pillar_jenis('AGRI')") == "agri", "pemanggilan lama satu argumen tetap jalan"


def test_submit_pa_rejects_vendor_outside_company_entities():
    vid = _vendor("PT. Milik SMT", "SMT")
    lines = _one_budget("X1")
    res = _submit(_payload("X1", lines, vendor_id=vid))
    assert res["ok"] is False and res["pesan"] == "Vendor tidak termasuk entitas perusahaan Anda."
    unknown = _vendor("PT. Pillar Aneh", "ZZZ")
    res2 = _submit(_payload("X1", lines, vendor_id=unknown))
    assert res2["ok"] is False and "belum punya pillar PA" in res2["pesan"]


def test_submit_pa_with_etf_entity_vendor_uses_ef_table_and_prefix():
    vid = _vendor("PT. Milik ETF", "ETF", "CC-ETF")
    lines = _one_budget("X2")
    res = _submit(_payload("X2", lines, vendor_id=vid))
    assert res["ok"] is True, res
    assert res["pa_number"] == f"PA/EF/001/{_yyyy()}" and res["jenis"] == "ef"
    assert _scalar("SELECT count(*) FROM ef_pa") == 1 and _scalar("SELECT count(*) FROM ef_pa_lines") == 1


def test_vendor_page_pillar_options_include_new_entities(client):
    client.post("/auth/login", json={"username": "admin", "password": "Admin@123"})
    client.post("/select-company", data={"company_id": str(ETF)})
    html = client.get("/payment-memo/").get_data(as_text=True)
    for sel in ("vendors-filter-pillar", "vendors-add-pillar"):
        block = html[html.index('id="%s"' % sel):]
        block = block[:block.index("</select>")]
        for v in ('value="AGRI"', 'value="APP"', 'value="LAND"', 'value="ENERGY"', 'value="SETF"', 'value="SMT"', 'value="ETF"'):
            assert v in block, (sel, v)


def test_vendor_inline_edit_pillar_options_not_hardcoded():
    path = os.path.join(os.path.dirname(__file__), "..", "templates", "payment_memo", "index.html")
    src = open(path, encoding="utf-8").read()
    assert "['AGRI', 'APP', 'LAND', 'ENERGY', 'SETF'].map" not in src, "opsi pillar edit vendor harus dari entities"
    assert "VENDOR_PILLARS" in src
