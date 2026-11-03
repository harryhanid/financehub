# tests/test_prportal_vendor.py -- Pembebanan PA lewat Vendor (master Vendors Flow): cari vendor + submit dengan vendor_id
import os, sys, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from database import get_conn
from tests.test_prportal_fn import _siswa, _budget, _payload, _submit

COMPANY_ID = 2


def _vendor(name, pillar, cost_center="CC-V1"):
    conn = get_conn()
    conn.execute('INSERT INTO vendors (name, pillar, cost_center, "Bank_Account_Name", "Bank_Name", "Bank_Account_Number")'
                 " VALUES (?,?,?,?,?,?)", (name, pillar, cost_center, "Rek Rahasia", "BCA", "9988776655"))
    conn.commit()
    vid = conn.execute("SELECT id FROM vendors WHERE name=?", (name,)).fetchone()["id"]
    conn.close()
    return vid


def _search(q):
    conn = get_conn()
    try:
        return json.loads(conn.execute("SELECT fn_prp_search_vendor(?)::text", (q,)).fetchone()[0])
    finally:
        conn.close()


def _one_budget(code="V1"):
    _siswa(code, "Vendor Siswa " + code)
    _budget(code, "By Pendidikan", "Semester 1", amount=5_000_000)
    conn = get_conn()
    bid = conn.execute("SELECT id FROM budget_beasiswa WHERE siswa_code=?", (code,)).fetchone()["id"]
    conn.close()
    return [{"budget_id": bid, "tahun_ajaran": "2026/2027", "jumlah": 1_000_000}]


def test_search_vendor_min_3_and_only_mappable_pillars_and_no_bank_data():
    _vendor("PT. Maju Agri", "AGRI", "CC-AGRI")
    _vendor("PT. Maju Land", "LAND", "")
    _vendor("PT. Maju Biasa", "-", "CC-X")
    _vendor("PT. Maju Nonpillar", "NON PILLAR", "CC-Y")
    assert _search("ma") == []
    res = _search("maju")
    assert [r["name"] for r in res] == ["PT. Maju Agri", "PT. Maju Land"]
    assert res[0]["pillar"] == "AGRI" and res[0]["cost_center"] == "CC-AGRI" and res[0]["jenis"] == "agri"
    assert res[1]["jenis"] == "sml" and res[1]["cost_center"] == ""
    blob = json.dumps(res)
    assert "9988776655" not in blob and "Rek Rahasia" not in blob and "BCA" not in blob


def test_search_vendor_max_10_and_wildcards_literal():
    for i in range(12):
        _vendor("PT. Banyak %02d" % i, "APP")
    assert len(_search("banyak")) == 10
    assert _search("%%%") == []


@pytest.mark.parametrize("pillar,table,prefix", [
    ("AGRI", "etf_pa", "ETF"), ("APP", "app_pa", "APP"), ("LAND", "sml_pa", "SML"),
    ("SETF", "setf_pa", "SETF"), ("EFIN", "energy_pa", "ENERGY"),
])
def test_submit_with_vendor_derives_jenis_and_stores_pembebanan(pillar, table, prefix):
    vid = _vendor("PT. Beban " + pillar, pillar, "CC-" + pillar)
    lines = _one_budget("V" + pillar)
    res = _submit(_payload("V" + pillar, lines, vendor_id=vid, jenis="agri" if pillar != "AGRI" else "app"))
    assert res["ok"] is True, res
    assert res["pa_number"].startswith("PA/%s/" % prefix)
    assert res["pembebanan_pt"] == "PT. Beban " + pillar and res["pembebanan_cost_center"] == "CC-" + pillar
    conn = get_conn()
    try:
        h = conn.execute("SELECT pembebanan_pt, pembebanan_cost_center, cost_center FROM %s WHERE id=?" % table,
                         (res["pa_id"],)).fetchone()
    finally:
        conn.close()
    assert h["pembebanan_pt"] == "PT. Beban " + pillar and h["pembebanan_cost_center"] == "CC-" + pillar
    assert h["cost_center"] == "CC-01"   # cost center pemohon tidak tertimpa


def test_submit_vendor_without_cost_center_stores_null():
    vid = _vendor("PT. Tanpa CC", "LAND", "")
    res = _submit(_payload("V1", _one_budget("V1"), vendor_id=vid))
    assert res["ok"] is True, res
    assert res["pembebanan_cost_center"] is None


@pytest.mark.parametrize("bad", [0, -1, "5", 1.5, True, 999999])
def test_submit_rejects_bad_or_unknown_vendor_without_writes(bad):
    lines = _one_budget("V1")
    res = _submit(_payload("V1", lines, vendor_id=bad))
    assert res["ok"] is False
    conn = get_conn()
    try:
        assert conn.execute("SELECT count(*) AS n FROM etf_pa").fetchone()["n"] == 0
        assert conn.execute("SELECT status FROM budget_beasiswa").fetchone()["status"] == "open"
    finally:
        conn.close()


def test_submit_rejects_vendor_pillar_without_pa_table():
    vid = _vendor("PT. Dash", "-")
    res = _submit(_payload("V1", _one_budget("V1"), vendor_id=vid))
    assert res["ok"] is False and "belum punya pillar PA" in res["pesan"]


def test_submit_without_vendor_still_uses_jenis_and_leaves_pembebanan_null():
    res = _submit(_payload("V1", _one_budget("V1"), jenis="app"))
    assert res["ok"] is True and res["pembebanan_pt"] is None
    assert res["pa_number"].startswith("PA/APP/")
