import os, sys, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config
config.DB_PATH = os.path.join(os.path.dirname(__file__), "test_sla.db")

from database import init_db, get_conn
from modules.payment_memo.service import get_days_of_pam

COMPANY_ID = 2  # ETF

@pytest.fixture(autouse=True)
def clean_db():
    if os.path.exists(config.DB_PATH):
        os.remove(config.DB_PATH)
    init_db()
    _seed(get_conn())
    yield
    if os.path.exists(config.DB_PATH):
        os.remove(config.DB_PATH)

def _seed(conn):
    conn.execute("INSERT INTO siswa (company_id, code, nama) VALUES (?,?,?)",
                 (COMPANY_ID, "S001", "Budi Santoso"))
    conn.execute("INSERT INTO siswa (company_id, code, nama) VALUES (?,?,?)",
                 (COMPANY_ID, "S002", "Siti Rahayu"))
    conn.execute("INSERT INTO pam_records (company_id, pam_no, source, status, created_at) VALUES (?,?,?,?,?)",
                 (COMPANY_ID, "PAM-001-AGRI", "etf_agri", "open", "2026-01-01"))
    conn.execute("INSERT INTO pam_records (company_id, pam_no, source, status, created_at) VALUES (?,?,?,?,?)",
                 (COMPANY_ID, "PAM-002-AGRI", "etf_agri", "open", "2026-01-02"))
    conn.execute("INSERT INTO pam_records (company_id, pam_no, source, status, created_at) VALUES (?,?,?,?,?)",
                 (COMPANY_ID, "PAM-003-APP",  "etf_app",  "open", "2026-01-03"))
    # AGRI unpaid
    conn.execute(
        "INSERT INTO payment_beasiswa (company_id, siswa_code, pam, tanggal, amount, status) VALUES (?,?,?,?,?,?)",
        (COMPANY_ID, "S001", "PAM-001-AGRI", "2026-01-01", 5000000, "open"))
    # AGRI paid
    conn.execute(
        "INSERT INTO payment_beasiswa (company_id, siswa_code, pam, tanggal, amount, status, \"tgl_Paid_AGRI\") VALUES (?,?,?,?,?,?,?)",
        (COMPANY_ID, "S002", "PAM-002-AGRI", "2026-01-02", 3000000, "open", "2026-02-01"))
    # APP unpaid
    conn.execute(
        "INSERT INTO payment_beasiswa (company_id, siswa_code, pam, tanggal, amount, status) VALUES (?,?,?,?,?,?)",
        (COMPANY_ID, "S001", "PAM-003-APP", "2026-01-03", 2000000, "open"))
    conn.commit()
    conn.close()


def test_default_returns_agri_unpaid_only():
    result = get_days_of_pam(COMPANY_ID)
    assert result["total"] == 1
    assert len(result["rows"]) == 1
    assert result["rows"][0]["pam_no"] == "PAM-001-AGRI"


def test_paid_only_false_returns_all_agri():
    result = get_days_of_pam(COMPANY_ID, paid_only=False)
    assert result["total"] == 2
    pam_nos = {r["pam_no"] for r in result["rows"]}
    assert pam_nos == {"PAM-001-AGRI", "PAM-002-AGRI"}


def test_source_app_returns_app_records():
    result = get_days_of_pam(COMPANY_ID, source="APP", paid_only=False)
    assert result["total"] == 1
    assert result["rows"][0]["pam_no"] == "PAM-003-APP"


def test_source_app_unpaid_excludes_nothing_extra():
    result = get_days_of_pam(COMPANY_ID, source="APP", paid_only=True)
    assert result["total"] == 1  # APP row has no tgl_Paid_APP set


def test_pam_search_filter():
    result = get_days_of_pam(COMPANY_ID, source="AGRI", paid_only=False, pam="PAM-002")
    assert result["total"] == 1
    assert result["rows"][0]["pam_no"] == "PAM-002-AGRI"


def test_nama_search_filter():
    result = get_days_of_pam(COMPANY_ID, source="AGRI", paid_only=False, nama="budi")
    assert result["total"] == 1
    assert result["rows"][0]["siswa_code"] == "S001"


def test_pagination_limit():
    result = get_days_of_pam(COMPANY_ID, source="AGRI", paid_only=False, limit=1, offset=0)
    assert result["total"] == 2
    assert len(result["rows"]) == 1


def test_pagination_offset():
    result = get_days_of_pam(COMPANY_ID, source="AGRI", paid_only=False, limit=1, offset=1)
    assert result["total"] == 2
    assert len(result["rows"]) == 1


def test_unknown_source_defaults_to_agri():
    result = get_days_of_pam(COMPANY_ID, source="UNKNOWN", paid_only=False)
    assert result["total"] == 2  # falls back to AGRI


def test_different_company_isolated():
    result = get_days_of_pam(company_id=1, source="AGRI", paid_only=False)
    assert result["total"] == 0
