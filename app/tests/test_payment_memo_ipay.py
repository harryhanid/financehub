# tests/test_payment_memo_ipay.py
import os, sys, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config
config.DB_PATH = os.path.join(os.path.dirname(__file__), "test_payment_memo_ipay.db")

from database import init_db
from modules.etf_payment_application.service import VALID_TABS, _TAB_CFG, _tbls


@pytest.fixture(autouse=True)
def clean_db():
    if os.path.exists(config.DB_PATH):
        os.remove(config.DB_PATH)
    init_db()
    yield
    if os.path.exists(config.DB_PATH):
        os.remove(config.DB_PATH)


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
