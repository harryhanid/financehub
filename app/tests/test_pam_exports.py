# tests/test_pam_exports.py
import os, sys, io, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config
config.DB_PATH = os.path.join(os.path.dirname(__file__), "test_finance_hub.db")

from database import init_db, get_conn
from modules.payment_memo.exports import export_pam_pdf

COMPANY_ID   = 2
COMPANY_CODE = "ETF"

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
        """INSERT INTO pam_records
           (company_id, pam_no, pam_date, gl_account, cost_center, pt,
            requestors_name, keterangan, total_amount, due_date, status, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,'draft',?)""",
        (COMPANY_ID, "PAM-001-ETF-05-2026", "2026-05-26", "70110230",
         "1008C1POFF", "PT. SMART Tbk", "Jany Turkanda",
         "Harry Santoso", 5000000, "2026-06-26", "2026-05-26T10:00:00")
    )
    conn.execute(
        """INSERT INTO siswa (company_id, code, nama, bank, norek, namarek,
           jenjang, program, status)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (COMPANY_ID, "S001", "Harry Santoso", "BCA", "1234567890",
         "Harry Santoso", "S1", "SMART", "Aktif")
    )
    conn.execute(
        """INSERT INTO payment_beasiswa
           (company_id, siswa_code, cat1, cat2, tanggal, amount,
            pillar, perusahaan, pam, status)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (COMPANY_ID, "S001", "General", "Sem 1", "2026-05-26",
         5000000, "ETF", "PT. SMART Tbk", "PAM-001-ETF-05-2026", "draft")
    )
    conn.commit()
    conn.close()


def test_export_pam_pdf_returns_bytes():
    result = export_pam_pdf(1, COMPANY_ID, "Hong Tjhin", "Tenti Kidjo")
    assert isinstance(result, bytes)
    assert len(result) > 1000
    assert result[:4] == b'%PDF'


def test_export_pam_pdf_not_found_raises():
    with pytest.raises(ValueError, match="PAM record tidak ditemukan"):
        export_pam_pdf(999, COMPANY_ID, "A", "B")


from modules.payment_memo.exports import export_pam_excel
import zipfile


def test_export_pam_excel_returns_bytes():
    result = export_pam_excel(1, COMPANY_ID, "Hong Tjhin", "Tenti Kidjo")
    assert isinstance(result, bytes)
    assert len(result) > 500
    assert zipfile.is_zipfile(io.BytesIO(result))


def test_export_pam_excel_has_two_sheets():
    import openpyxl
    result = export_pam_excel(1, COMPANY_ID, "Hong Tjhin", "Tenti Kidjo")
    wb = openpyxl.load_workbook(io.BytesIO(result))
    assert wb.sheetnames == ["PAM", "Lampiran"]


def test_export_pam_excel_pam_no_in_sheet():
    import openpyxl
    result = export_pam_excel(1, COMPANY_ID, "Hong Tjhin", "Tenti Kidjo")
    wb = openpyxl.load_workbook(io.BytesIO(result))
    ws = wb["PAM"]
    values = [ws.cell(r, c).value for r in range(1, 30) for c in range(1, 10)]
    assert "PAM-001-ETF-05-2026" in values


def test_export_pam_excel_not_found_raises():
    with pytest.raises(ValueError, match="PAM record tidak ditemukan"):
        export_pam_excel(999, COMPANY_ID, "A", "B")
