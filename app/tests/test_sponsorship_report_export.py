import io
import openpyxl
from modules.sponsorship.service import seed_perusahaan, create_transaksi
from modules.sponsorship.exports import export_report_excel

SMT = 1


def _seed():
    seed_perusahaan([("SMART", "AGRI", "AGRI")])


def test_export_report_excel_has_expected_title(app):
    _seed()
    create_transaksi(SMT, {
        "cat": "Sponsorship", "description": "Sosial",
        "tanggal_form_sponsor": "2026-01-15", "cat1": "SMART",
        "lembaga_perorangan": "Yayasan Test", "amount_request": 1000000,
    })
    xls_bytes = export_report_excel(SMT, ["2026"], "all")
    wb = openpyxl.load_workbook(io.BytesIO(xls_bytes))
    ws = wb.active
    assert ws["B1"].value == "RANGKUMAN SPONSORSHIP - in Rp Full Amount"


def test_export_report_excel_contains_section_and_lembaga(app):
    _seed()
    create_transaksi(SMT, {
        "cat": "Sponsorship", "description": "Sosial",
        "tanggal_form_sponsor": "2026-01-15", "cat1": "SMART",
        "lembaga_perorangan": "Yayasan Test", "amount_request": 1000000,
    })
    xls_bytes = export_report_excel(SMT, ["2026"], "all")
    wb = openpyxl.load_workbook(io.BytesIO(xls_bytes))
    ws = wb.active
    values = [cell.value for row in ws.iter_rows() for cell in row]
    assert "SOSIAL" in values
    assert "Yayasan Test" in values
    assert "TOTAL SPONSORSHIP (ACTUAL)" in values


def test_export_report_excel_empty_data_still_generates_file(app):
    _seed()
    xls_bytes = export_report_excel(SMT, ["2026"], "all")
    wb = openpyxl.load_workbook(io.BytesIO(xls_bytes))
    ws = wb.active
    assert ws["B1"].value == "RANGKUMAN SPONSORSHIP - in Rp Full Amount"
