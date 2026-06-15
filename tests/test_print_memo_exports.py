import io
import openpyxl
import pytest

_RP_FMT = '_-"Rp"* #,##0_-;\\-"Rp"* #,##0_-;_-"Rp"* "-"_-;_-@_-'


def _data():
    return {
        "pam_no": "PAM-TEST", "pam_date": "2026-06-15",
        "requestors_name": "Tester", "department": "-",
        "cost_center": "CC-001", "gl_account": "GL-001",
        "so_sc": "", "pt": "PT TEST",
        "bu_corporate": True, "bu_upstream": False, "bu_downstream": False,
        "type_invoice": True, "type_downpayment": False, "type_advance": False,
        "vendor_name": "Budi Santoso, Ali Rahman",
        "invoice_memo_no": "-",
        "total_amount": 5_000_000,
        "due_date": "2026-07-01",
        "bank_account_name": "Budi Santoso, Ali Rahman",
        "bank_name": "BNI, BCA",
        "bank_account_no": "111, 222",
        "approved_by_1": "Mgr", "approved_by_2": "Dir",
        "company_id": 1,
    }


def _payments():
    return [
        {"siswa_code": "S2A", "nama": "Ali", "bank": "BCA", "norek": "222",
         "namarek": "Ali Rahman", "jenjang": "S2", "amount": 2_000_000,
         "cat1": "By Pendidikan", "cat2": None, "tanggal": "2026-06-01"},
        {"siswa_code": "S1A", "nama": "Budi", "bank": "BNI", "norek": "111",
         "namarek": "Budi Santoso", "jenjang": "S1", "amount": 3_000_000,
         "cat1": "By Pendidikan", "cat2": None, "tanggal": "2026-06-01"},
    ]


def test_excel_pam_new_colons_center_aligned(monkeypatch):
    from app.modules.payment_memo import exports
    monkeypatch.setattr(exports, "get_pam_payments_detail", lambda *a: [])

    result = exports.export_pam_excel_custom(_data(), _payments())
    wb = openpyxl.load_workbook(io.BytesIO(result))
    ws = wb["PAM NEW"]

    for row in [4, 5, 6, 7, 8]:
        assert ws[f"E{row}"].alignment.horizontal == "center", f"E{row} colon not center"
    for row in [19, 20, 21, 22]:
        assert ws[f"H{row}"].alignment.horizontal == "center", f"H{row} colon not center"
    for row in [25, 26, 27]:
        assert ws[f"H{row}"].alignment.horizontal == "center", f"H{row} colon not center"


def test_excel_pam_new_vendor_bank_wrap_text(monkeypatch):
    from app.modules.payment_memo import exports
    monkeypatch.setattr(exports, "get_pam_payments_detail", lambda *a: [])

    result = exports.export_pam_excel_custom(_data(), _payments())
    wb = openpyxl.load_workbook(io.BytesIO(result))
    ws = wb["PAM NEW"]

    assert ws["I19"].alignment.wrap_text is True, "I19 vendor name: wrap_text harus True"
    assert ws["I25"].alignment.wrap_text is True, "I25 bank account name: wrap_text harus True"
    assert ws["I26"].alignment.wrap_text is True, "I26 bank name: wrap_text harus True"


def test_rangkuman_rp_accounting_format(monkeypatch):
    """Amount cells di Rangkuman PAM harus pakai Rp Accounting number format."""
    from app.modules.payment_memo import exports
    monkeypatch.setattr(exports, "get_pam_payments_detail", lambda *a: [])

    result = exports.export_pam_excel_custom(_data(), _payments())
    wb = openpyxl.load_workbook(io.BytesIO(result))
    ws2 = wb["Rangkuman PAM"]

    # Data row 1 at row 8 (header at rows 6-7), col 8 = amount
    assert ws2.cell(8, 8).number_format == _RP_FMT, "data row: bukan Rp Accounting format"
    # Total row at row 10 (2 data rows + total)
    assert ws2.cell(10, 8).number_format == _RP_FMT, "total row: bukan Rp Accounting format"
