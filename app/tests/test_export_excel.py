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


def test_export_pam_tab_returns_xlsx():
    from modules.payment_memo.exports import export_pam_tab_excel
    conn = get_conn()
    conn.execute(
        """INSERT INTO pam_records
           (company_id, pam_no, pam_date, gl_account, cost_center, pt,
            requestors_name, keterangan, total_amount, due_date, status, source, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (COMPANY_ID, "PAM-001-ETF-05-2026", "2026-05-01", "70110230",
         "1008C1", "PT ABC", "User A", "Catatan", 2000000, "2026-06-01",
         "open", "etf_agri", "2026-05-01T10:00:00")
    )
    conn.commit(); conn.close()
    result = export_pam_tab_excel(COMPANY_ID, search="", bulan="05", tahun="2026", source="agri")
    assert isinstance(result, bytes) and result[:2] == b'PK'


def test_export_fiori_returns_xlsx():
    from modules.payment_memo.exports import export_fiori_excel
    conn = get_conn()
    conn.execute(
        """INSERT INTO fiori_pa
           (no_pa, category, keterangan, categori_1, nama_vendor, total,
            terima_document, input_aspiro, verifikasi_tax, approval_1, approval_2,
            kirim_aspiro, paid, status)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        ("PA-APP-001", "Vendor", "Keterangan A", "Cat1", "PT Vendor ABC", 5000000,
         "2026-05-10", "2026-05-11", "2026-05-12", "2026-05-13", "2026-05-14",
         "2026-05-15", "2026-05-16", "open")
    )
    conn.commit(); conn.close()
    result = export_fiori_excel(search="", bulan="05", tahun="2026")
    assert isinstance(result, bytes) and result[:2] == b'PK'


def test_export_fiori_empty_returns_xlsx():
    from modules.payment_memo.exports import export_fiori_excel
    result = export_fiori_excel(search="zzz_no_match_at_all")
    assert isinstance(result, bytes)
    assert result[:2] == b'PK'
