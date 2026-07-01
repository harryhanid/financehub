# tests/test_budget_dashboard.py
from datetime import datetime, timedelta
from modules.budget.service import (
    format_currency, create_budget, create_realisasi, _build_budget_data,
    calculate_summary, group_budget_vs_realized, group_by_month,
    group_by_company, group_by_status,
    analyze_expired_budgets, get_carryover_data, analyze_compliance,
    generate_notifications, get_dashboard_data, get_available_years,
    get_available_categories, get_available_departments, get_available_activities,
    update_budget,
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


def test_analyze_expired_budgets_counts_and_buckets():
    b = create_budget({"company": "PO", "dept": "Finance", "mm": 1, "yy": 2020, "amount": 1000000})
    # force an already-past deadline
    yesterday = (datetime.now() - timedelta(days=5)).date().isoformat()
    conn = __import__("database").get_conn()
    conn.execute("UPDATE budget_master SET deadline=? WHERE id=?", (yesterday, b["id"]))
    conn.commit()
    conn.close()
    data = _build_budget_data({"year": "2020"})
    result = analyze_expired_budgets(data)
    assert result["totalExpired"] == 1
    assert result["ageBuckets"]["recent"] == 1


def test_get_dashboard_data_has_all_expected_keys():
    _seed_two_budgets()
    payload = get_dashboard_data({"year": "ALL"})
    for key in [
        "summary", "monthlyChart", "deptChart", "activityChart", "companyChart",
        "categoryChart", "statusChart", "expiredAnalysis", "complianceData",
        "notifications", "transactions", "realizations", "carryovers",
    ]:
        assert key in payload


def test_analyze_compliance_with_no_requests():
    result = analyze_compliance([], [])
    assert result["complianceRate"] == "100.0"
    assert result["totalRequests"] == 0


def test_generate_notifications_flags_near_limit():
    # Use next month to ensure deadline is in the future relative to today (2026-07-01)
    now = datetime.now()
    total_months = now.year * 12 + (now.month - 1) + 1
    year = total_months // 12
    month = total_months % 12 + 1

    b = create_budget({"company": "PO", "dept": "Finance", "mm": month, "yy": year, "amount": 1000000})
    realisasi_date = f"{year:04d}-{month:02d}-10"
    create_realisasi({"budget_id": b["id"], "amount": 950000, "tanggal_realisasi": realisasi_date})
    data = _build_budget_data({"year": str(year)})
    notifications = generate_notifications(data)
    assert any(n["title"] == "Near Budget Limit" for n in notifications)


def test_get_available_years_returns_sorted_desc():
    create_budget({"company": "PO", "dept": "Finance", "mm": 1, "yy": 2025, "amount": 100})
    create_budget({"company": "PO", "dept": "Finance", "mm": 1, "yy": 2026, "amount": 100})
    years = get_available_years()
    assert years[0] == "2026"


def test_get_available_categories_departments_activities():
    create_budget({
        "company": "PO", "dept": "Marketing", "mm": 1, "yy": 2026,
        "budget_category": "OpEx", "activity": "Ad Campaign", "amount": 100,
    })
    assert "Marketing" in get_available_departments()
    assert "OpEx" in get_available_categories()
    assert "Ad Campaign" in get_available_activities()
