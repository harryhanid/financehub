# tests/test_entities_flow_ui.py -- modul Payment Application Flow: tab, validasi, dan prefix nomor PA per perusahaan (tabel entities).
import os
import re
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database import get_conn
from modules.etf_payment_application.service import create_pa, get_entities, get_pa_flat, valid_tabs

SMT, ETF = 1, 2


def _yyyy():
    return (datetime.now(timezone.utc) + timedelta(hours=7)).strftime("%Y")


def _siswa(company_id, code):
    conn = get_conn()
    try:
        return conn.execute("INSERT INTO siswa (company_id, code, nama, status) VALUES (?,?,?,?) RETURNING id",
                            (company_id, code, "Siswa " + code, "Aktif")).fetchone()["id"]
    finally:
        conn.commit()
        conn.close()


def _create(company_id, tab, code):
    sid = _siswa(company_id, code)
    return create_pa(company_id, {"tgl_payment_application": "2026-11-01"},
                     [{"student_id": sid, "jenis_pembayaran": "By Pendidikan", "jumlah_pembayaran": 1000}], tab)


def _login(client, company_id):
    client.post("/auth/login", json={"username": "admin", "password": "Admin@123"})
    client.post("/select-company", data={"company_id": str(company_id)})


def test_entities_per_company():
    smt = [(e["code"], e["tab_key"], e["pa_prefix"]) for e in get_entities(SMT)]
    etf = [(e["code"], e["tab_key"], e["pa_prefix"]) for e in get_entities(ETF)]
    assert smt == [("AGRI", "agri", "SMT"), ("APP", "app", "APP"), ("LAND", "sml", "LAND"), ("EFIN", "energy", "EFIN"), ("SMT", "sm", "SM")]
    assert etf == [("AGRI", "agri", "ETF"), ("APP", "app", "APP"), ("LAND", "sml", "LAND"), ("EFIN", "energy", "EFIN"),
                   ("SETF", "setf", "SETF"), ("ETF", "ef", "EF")]
    assert get_entities(999) == []


def test_valid_tabs_reject_foreign_entity():
    assert "ef" in valid_tabs(ETF) and "sm" not in valid_tabs(ETF)
    assert "sm" in valid_tabs(SMT) and "ef" not in valid_tabs(SMT) and "setf" not in valid_tabs(SMT)
    assert {"agri", "app", "sml", "energy"} <= valid_tabs(SMT) & valid_tabs(ETF)
    assert valid_tabs(999) == set()


def test_create_pa_numbers_use_company_prefix():
    y = _yyyy()
    assert _create(SMT, "agri", "S1")["pa_number"] == f"PA/SMT/001/{y}"
    assert _create(SMT, "sm", "S2")["pa_number"] == f"PA/SM/001/{y}"
    assert _create(SMT, "sml", "S3")["pa_number"] == f"PA/LAND/001/{y}"
    assert _create(ETF, "ef", "E1")["pa_number"] == f"PA/EF/001/{y}"
    assert _create(ETF, "agri", "E2")["pa_number"] == f"PA/ETF/001/{y}"
    assert _create(ETF, "agri", "E3")["pa_number"] == f"PA/ETF/002/{y}"
    assert _create(ETF, "setf", "E4")["pa_number"] == f"PA/SETF/001/{y}"


def test_lists_isolated_per_company():
    a = _create(SMT, "agri", "S1")
    b = _create(ETF, "agri", "E1")
    smt_nums = [r["pa_number"] for r in get_pa_flat(SMT, "agri", "active")]
    etf_nums = [r["pa_number"] for r in get_pa_flat(ETF, "agri", "active")]
    assert smt_nums == [a["pa_number"]] and etf_nums == [b["pa_number"]]
    assert get_pa_flat(SMT, "ef", "active") == []


def test_index_renders_entity_tabs_for_company(client):
    _login(client, SMT)
    html = client.get("/etf-payment-application/?tab=agri").get_data(as_text=True)
    tabs = re.findall(r'<a href="\?tab=(\w+)[^"]*"\s+class="tab-btn[^"]*"[^>]*>\s*([^<]+?)\s*</a>', html)
    assert [t for t, _ in tabs if t not in ("summary", "advance", "combine", "input")] == ["agri", "app", "sml", "energy", "sm"]
    assert [l for t, l in tabs if t in ("agri", "sm")] == ["AGRI", "SMT"]
    assert {"summary", "advance", "combine"} <= {t for t, _ in tabs}
    _login(client, ETF)
    html = client.get("/etf-payment-application/?tab=agri").get_data(as_text=True)
    tabs = [t for t, _ in re.findall(r'<a href="\?tab=(\w+)[^"]*"\s+class="tab-btn[^"]*"[^>]*>\s*([^<]+?)\s*</a>', html)]
    assert [t for t in tabs if t not in ("summary", "advance", "combine", "input")] == ["agri", "app", "sml", "energy", "setf", "ef"]


def test_foreign_tab_falls_back_not_rendered_for_company(client):
    _login(client, ETF)
    r = client.get("/etf-payment-application/?tab=sm")
    html = r.get_data(as_text=True)
    assert r.status_code == 200 and 'class="tab-btn active"' in html
    assert not re.search(r'<a href="\?tab=sm[^"]*"\s+class="tab-btn active"', html), "tab sm tidak boleh aktif untuk ETF"
    _login(client, SMT)
    html = client.get("/etf-payment-application/?tab=ef").get_data(as_text=True)
    assert not re.search(r'<a href="\?tab=ef[^"]*"\s+class="tab-btn active"', html)
