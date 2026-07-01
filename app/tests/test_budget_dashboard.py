# tests/test_budget_dashboard.py
from datetime import datetime
from modules.budget.service import (
    format_currency, create_budget, create_realisasi, _build_budget_data,
    calculate_summary, group_budget_vs_realized, group_by_month,
    group_by_company, group_by_status,
)


def test_format_currency():
    assert format_currency(0) == "Rp 0"
    assert format_currency(1500000) == "Rp 1.500.000"
    assert format_currency(None) == "Rp 0"


def _seed_two_budgets():
    """Seed fixture with relative dates: next month and month-after-next from today.
    This keeps tests valid regardless of when they run."""
    now = datetime.now()
    # Calculate next month (month 1) using manual month arithmetic
    total_months_m1 = now.year * 12 + (now.month - 1) + 1
    month1_year = total_months_m1 // 12
    month1_month = total_months_m1 % 12 + 1

    # Calculate month after next (month 2)
    total_months_m2 = now.year * 12 + (now.month - 1) + 2
    month2_year = total_months_m2 // 12
    month2_month = total_months_m2 % 12 + 1

    b1 = create_budget({
        "company": "PO", "dept": "Finance", "mm": month1_month, "yy": month1_year,
        "budget_category": "OpEx", "activity": "Audit Fee", "amount": 1000000,
    })
    b2 = create_budget({
        "company": "TF", "dept": "IT", "mm": month2_month, "yy": month2_year,
        "budget_category": "CapEx", "activity": "Server Upgrade", "amount": 2000000,
    })
    # Realisasi dates: 10th of each seeded month
    realisasi_date1 = f"{month1_year:04d}-{month1_month:02d}-10"
    realisasi_date2 = f"{month2_year:04d}-{month2_month:02d}-10"
    create_realisasi({"budget_id": b1["id"], "amount": 400000, "tanggal_realisasi": realisasi_date1})
    create_realisasi({"budget_id": b2["id"], "amount": 500000, "tanggal_realisasi": realisasi_date2})
    return b1, b2


def test_build_budget_data_computes_realized_and_balance():
    b1, b2 = _seed_two_budgets()
    data = _build_budget_data({"year": "ALL"})
    row1 = next(d for d in data if d["id"] == b1["id"])
    assert row1["realized"] == 400000
    assert row1["balance"] == 600000
    assert row1["utilizationRate"] == 40.0


def test_build_budget_data_filters_by_company():
    _seed_two_budgets()
    data = _build_budget_data({"company": "PO", "year": "ALL"})
    assert all(d["company"] == "PO" for d in data)


def test_calculate_summary_totals():
    _seed_two_budgets()
    data = _build_budget_data({"year": "ALL"})
    summary = calculate_summary(data)
    assert summary["totalBudget"] == 3000000
    assert summary["totalRealized"] == 900000
    assert summary["remaining"] == 2100000
    assert summary["formatted"]["totalBudget"] == "Rp 3.000.000"


def test_group_budget_vs_realized_by_activity():
    _seed_two_budgets()
    data = _build_budget_data({"year": "ALL"})
    grouped = group_budget_vs_realized(data, "activity")
    assert "Audit Fee" in grouped["labels"]
    assert "Server Upgrade" in grouped["labels"]
    assert len(grouped["budget"]) == len(grouped["labels"])


def test_group_by_month_places_amount_in_correct_index():
    _seed_two_budgets()
    now = datetime.now()
    # Calculate next month (month 1) using manual month arithmetic
    total_months_m1 = now.year * 12 + (now.month - 1) + 1
    month1_year = total_months_m1 // 12
    month1_month = total_months_m1 % 12 + 1

    # Calculate month after next (month 2)
    total_months_m2 = now.year * 12 + (now.month - 1) + 2
    month2_year = total_months_m2 // 12
    month2_month = total_months_m2 % 12 + 1

    month1_idx = month1_month - 1  # Convert to 0-indexed
    month2_idx = month2_month - 1

    data = _build_budget_data({"year": "ALL"})
    grouped = group_by_month(data)
    assert grouped["budget"][month1_idx] == 1000000
    assert grouped["budget"][month2_idx] == 2000000


def test_group_by_company_splits_po_tf():
    _seed_two_budgets()
    data = _build_budget_data({"year": "ALL"})
    grouped = group_by_company(data)
    assert grouped["labels"] == ["PO", "TF"]
    assert grouped["budget"] == [1000000, 2000000]


def test_group_by_status_counts_active_by_default():
    _seed_two_budgets()
    data = _build_budget_data({"year": "ALL"})
    grouped = group_by_status(data)
    assert dict(zip(grouped["labels"], grouped["values"]))["Active"] == 2
