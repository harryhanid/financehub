# tests/test_budget_exports.py
from datetime import datetime
from modules.budget.service import create_budget, create_realisasi
from modules.budget.exports import (
    export_transactions_csv, export_realization_csv, export_department_report_csv,
    export_expired_report_csv, export_compliance_report_csv,
)


def _seed():
    """Seed fixture with a budget in the next month to keep deadline in the future."""
    now = datetime.now()
    # Calculate next month using manual month arithmetic
    total_months = now.year * 12 + (now.month - 1) + 1
    year = total_months // 12
    month = total_months % 12 + 1

    b = create_budget({
        "company": "PO", "dept": "Finance", "mm": month, "yy": year,
        "budget_category": "OpEx", "activity": "Audit Fee", "amount": 1000000,
    })
    # Realisasi date: 10th of the seeded month
    realisasi_date = f"{year:04d}-{month:02d}-10"
    create_realisasi({"budget_id": b["id"], "amount": 400000, "tanggal_realisasi": realisasi_date})
    return b


def test_export_transactions_csv_has_header_and_row():
    _seed()
    csv_bytes = export_transactions_csv({"year": "ALL"})
    text = csv_bytes.decode("utf-8-sig")
    lines = text.strip().split("\n")
    assert lines[0].startswith("Budget ID,Company,Dept")
    assert len(lines) >= 2


def test_export_realization_csv_has_header_and_row():
    _seed()
    csv_bytes = export_realization_csv({"year": "ALL"})
    text = csv_bytes.decode("utf-8-sig")
    assert text.startswith("Trx ID,Budget ID,Date")
    assert "400000" in text


def test_export_department_report_csv_aggregates_by_dept():
    _seed()
    csv_bytes = export_department_report_csv({"year": "ALL"})
    text = csv_bytes.decode("utf-8-sig")
    assert "Finance" in text
    assert "1000000" in text


def test_export_expired_report_csv_only_includes_expired():
    _seed()
    csv_bytes = export_expired_report_csv({"year": "ALL"})
    text = csv_bytes.decode("utf-8-sig")
    lines = text.strip().split("\n")
    assert lines[0].startswith("Budget ID,Company,Dept")
    assert len(lines) == 1  # header only, nothing expired yet


def test_export_compliance_report_csv_header_only_when_no_requests():
    _seed()
    csv_bytes = export_compliance_report_csv({"year": "ALL"})
    text = csv_bytes.decode("utf-8-sig")
    assert text.strip().split("\n")[0].startswith("Budget ID,Type,Requested By")
