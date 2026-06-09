# tests/test_payment_memo_ipay.py
import os, sys, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from modules.etf_payment_application.service import VALID_TABS, _TAB_CFG, _tbls


def test_setf_in_valid_tabs():
    assert "setf" in VALID_TABS


def test_setf_tab_config():
    pa_tbl, lines_tbl, pa_prefix, pam_prefix = _TAB_CFG["setf"]
    assert pa_tbl == "setf_pa"
    assert lines_tbl == "setf_pa_lines"
    assert pa_prefix == "SETF"
    assert pam_prefix == "SETF"


def test_tbls_setf_resolves():
    pa_tbl, lines_tbl, pa_prefix, pam_prefix = _tbls("setf")
    assert pa_tbl == "setf_pa"
    assert lines_tbl == "setf_pa_lines"


import re
from modules.payment_memo.service import get_next_pam_no


def test_get_next_pam_no_agri_format():
    """AGRI uses ETF prefix → PAM-NNN-ETF-MM-YYYY"""
    result = get_next_pam_no(company_id=1, company_code="ETF",
                             tab="agri", date_str="2026-06-08")
    assert re.match(r"PAM-\d{3}-ETF-06-2026", result), f"Got: {result}"


def test_get_next_pam_no_setf_format():
    """SETF uses SETF prefix → PAM-NNN-SETF-MM-YYYY"""
    result = get_next_pam_no(company_id=1, company_code="ETF",
                             tab="setf", date_str="2026-06-08")
    assert re.match(r"PAM-\d{3}-SETF-06-2026", result), f"Got: {result}"


def test_get_next_pam_no_app_uses_app_prefix():
    result = get_next_pam_no(company_id=1, company_code="ETF",
                             tab="app", date_str="2026-06-08")
    assert "APP" in result, f"Got: {result}"


def test_get_next_pam_no_sml_uses_sml_prefix():
    result = get_next_pam_no(company_id=1, company_code="ETF",
                             tab="sml", date_str="2026-06-08")
    assert "SML" in result, f"Got: {result}"


from modules.payment_memo.service import save_pa_payment


def test_save_pa_payment_missing_pam_no():
    result = save_pa_payment(
        company_id=1, company_code="ETF",
        data={"tab": "setf", "tanggal": "2026-06-08", "pam_no": "",
              "rows": [{"siswa_code": "ETF001", "amount": 100}]}
    )
    assert result["ok"] is False
    assert "PAM" in result["pesan"]


def test_save_pa_payment_no_rows():
    result = save_pa_payment(
        company_id=1, company_code="ETF",
        data={"tab": "agri", "tanggal": "2026-06-08",
              "pam_no": "PAM-001-ETF-06-2026", "rows": []}
    )
    assert result["ok"] is False


def test_get_pam_list_source_filter(tmp_path, monkeypatch):
    """source='agri' returns only etf_agri records, source='' returns all."""
    import sqlite3
    from modules.payment_memo import service as pm_svc
    db = str(tmp_path / "t.db")
    def _get_conn():
        c = sqlite3.connect(db)
        c.row_factory = sqlite3.Row
        return c
    monkeypatch.setattr(pm_svc, "get_conn", _get_conn)
    conn = sqlite3.connect(db)
    conn.execute("""CREATE TABLE pam_records (
        id INTEGER PRIMARY KEY, company_id INTEGER,
        pam_no TEXT, source TEXT, status TEXT, created_at TEXT,
        pam_date TEXT, pt TEXT, keterangan TEXT, gl_account TEXT,
        cost_center TEXT, requestors_name TEXT, total_amount REAL,
        due_date TEXT, tanggal_bayar TEXT
    )""")
    conn.execute("INSERT INTO pam_records (company_id,pam_no,source,status,created_at) VALUES (1,'PAM-001-ETF-06-2026','etf_agri','open','2026-06-08')")
    conn.execute("INSERT INTO pam_records (company_id,pam_no,source,status,created_at) VALUES (1,'PAM-001-APP-06-2026','etf_app','open','2026-06-08')")
    conn.commit(); conn.close()

    from modules.payment_memo.service import get_pam_list
    all_rows  = get_pam_list(company_id=1)
    agri_rows = get_pam_list(company_id=1, source="agri")
    app_rows  = get_pam_list(company_id=1, source="app")

    assert len(all_rows) == 2
    assert len(agri_rows) == 1 and agri_rows[0]["pam_no"] == "PAM-001-ETF-06-2026"
    assert len(app_rows)  == 1 and app_rows[0]["pam_no"]  == "PAM-001-APP-06-2026"
