# tests/test_export_excel.py
import os, sys, io, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config
config.DB_PATH = os.path.join(os.path.dirname(__file__), "test_finance_hub.db")

from database import init_db, get_conn

COMPANY_ID = 2

@pytest.fixture(autouse=True)
def clean_db():
    if os.path.exists(config.DB_PATH):
        os.remove(config.DB_PATH)
    init_db()
    _seed()
    yield
    if os.path.exists(config.DB_PATH):
        os.remove(config.DB_PATH)


def _seed():
    conn = get_conn()
    conn.execute(
        """INSERT INTO siswa (company_id, code, nama, bank, norek, namarek, jenjang, program, status)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (COMPANY_ID, "S001", "Budi Santoso", "BCA", "111", "Budi", "S1", "SMART", "Aktif")
    )
    conn.execute(
        """INSERT INTO payment_beasiswa
           (company_id, siswa_code, cat1, cat2, tanggal, amount, pillar, perusahaan, status)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (COMPANY_ID, "S001", "Tuition", "Sem 1", "2026-05-01", 5000000, "ETF", "PT ABC", "open")
    )
    conn.commit()
    conn.close()


def test_export_open_pam_returns_xlsx():
    from modules.payment_memo.exports import export_open_pam_excel
    result = export_open_pam_excel(COMPANY_ID)
    assert isinstance(result, bytes)
    assert len(result) > 500
    # xlsx magic bytes: PK (zip)
    assert result[:2] == b'PK'


def test_export_open_pam_empty_company():
    from modules.payment_memo.exports import export_open_pam_excel
    result = export_open_pam_excel(9999)
    assert isinstance(result, bytes)
    assert result[:2] == b'PK'
