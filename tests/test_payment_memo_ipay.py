# tests/test_payment_memo_ipay.py
import pytest
from app.modules.etf_payment_application.service import VALID_TABS, _TAB_CFG, _tbls


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


import sqlite3 as _sq3
import os as _os


def _make_pam_db(path):
    conn = _sq3.connect(path)
    conn.execute("""
        CREATE TABLE pam_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            pam_no TEXT NOT NULL,
            pam_date TEXT,
            requestors_name TEXT,
            keterangan TEXT,
            total_amount REAL DEFAULT 0,
            due_date TEXT,
            source TEXT,
            status TEXT DEFAULT 'draft',
            created_at TEXT
        )
    """)
    conn.execute(
        "INSERT INTO pam_records (company_id, pam_no, source) VALUES (1, 'PAM-001-AGRI-06-2026', 'agri')"
    )
    conn.commit()
    conn.close()
    return path


def test_check_pam_no_exists_true(monkeypatch, tmp_path):
    db_path = str(tmp_path / "test.db")
    _make_pam_db(db_path)
    from app.modules.payment_memo import service as service_mod
    def _fake_conn():
        c = _sq3.connect(db_path)
        c.row_factory = _sq3.Row
        return c
    monkeypatch.setattr(service_mod, "get_conn", _fake_conn)
    result = service_mod.check_pam_no_exists(1, "PAM-001-AGRI-06-2026")
    assert result == {"ok": True, "exists": True}


def test_check_pam_no_exists_false(monkeypatch, tmp_path):
    db_path = str(tmp_path / "test.db")
    _make_pam_db(db_path)
    from app.modules.payment_memo import service as service_mod
    def _fake_conn():
        c = _sq3.connect(db_path)
        c.row_factory = _sq3.Row
        return c
    monkeypatch.setattr(service_mod, "get_conn", _fake_conn)
    result = service_mod.check_pam_no_exists(1, "PAM-099-AGRI-06-2026")
    assert result == {"ok": True, "exists": False}


def test_check_pam_no_wrong_company(monkeypatch, tmp_path):
    db_path = str(tmp_path / "test.db")
    _make_pam_db(db_path)
    from app.modules.payment_memo import service as service_mod
    def _fake_conn():
        c = _sq3.connect(db_path)
        c.row_factory = _sq3.Row
        return c
    monkeypatch.setattr(service_mod, "get_conn", _fake_conn)
    result = service_mod.check_pam_no_exists(99, "PAM-001-AGRI-06-2026")
    assert result == {"ok": True, "exists": False}
