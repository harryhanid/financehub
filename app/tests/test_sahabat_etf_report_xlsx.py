import io
import openpyxl
from modules.sahabat_etf.report_xlsx import build_report_workbook


def _empty_metrics():
    return {"plafon": 0.0, "klaim": 0.0, "dibayar": 0.0, "saldo": 0.0}


def _sample_data():
    empty_total = {"cur": _empty_metrics(), "cum": _empty_metrics()}
    return {
        "report_year": 2026,
        "sections": [
            {"key": "PENDIDIKAN", "label": "PENDIDIKAN", "groups": [], "total": empty_total, "recap": []},
            {"key": "KESEHATAN", "label": "KESEHATAN", "groups": [], "total": empty_total, "recap": []},
        ],
        "combined_total": empty_total,
        "combined_recap": [],
        "grand_total": empty_total,
        "pillar_breakdown": [],
    }


def test_build_report_workbook_writes_title_and_unit_note():
    xlsx_bytes = build_report_workbook(_sample_data())
    wb = openpyxl.load_workbook(io.BytesIO(xlsx_bytes))
    ws = wb.active
    assert ws["B1"].value.startswith("REPORT PER ")
    assert ws["O1"].value == "(Rp, Dalam Jutaan)"


def test_build_report_workbook_writes_column_header_labels():
    xlsx_bytes = build_report_workbook(_sample_data())
    wb = openpyxl.load_workbook(io.BytesIO(xlsx_bytes))
    ws = wb.active
    assert ws["B3"].value == "Deskripsi"
    assert ws["C3"].value == "Periode"
    assert ws["F3"].value == "Pillar"
    assert ws["G3"].value == "TAHUN 2026"
    assert ws["K3"].value == "S/D TAHUN 2026"
    assert ws["O3"].value == "Catatan"
    assert ws["G4"].value == "Plafon"
    assert ws["H4"].value == "Klaim"
    assert ws["I4"].value == "Dibayar"
    assert ws["J4"].value == "Saldo"
