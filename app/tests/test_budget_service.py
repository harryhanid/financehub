# tests/test_budget_service.py
from modules.budget.service import (
    generate_budget_id, compute_deadline, list_budgets, get_budget,
    create_budget, update_budget, delete_budget,
)


def test_compute_deadline_within_same_year():
    assert compute_deadline(1, 2026) == "2026-03-31"


def test_compute_deadline_rolls_into_next_year():
    assert compute_deadline(11, 2026) == "2027-01-31"


def test_generate_budget_id_format():
    bid = generate_budget_id("PO", "Finance", 1, 2026)
    parts = bid.split("-")
    assert parts[0] == "PO"
    assert parts[1] == "FINA"
    assert parts[2] == "26"
    assert parts[3] == "01"
    assert len(parts[4]) <= 5


def test_generate_budget_id_empty_dept_falls_back_to_xxx():
    bid = generate_budget_id("TF", "", 1, 2026)
    assert bid.split("-")[1] == "XXX"


def test_create_budget_success():
    result = create_budget({
        "company": "PO", "dept": "Finance", "mm": 1, "yy": 2026,
        "gl_account": "70110230", "gl_description": "Scholarship Expense",
        "budget_category": "OpEx", "activity": "Audit Fee",
        "description": "Annual audit", "amount": 50000000,
    })
    assert result["ok"] is True
    assert result["id"].startswith("PO-FINA-26-01-")


def test_create_budget_rejects_invalid_company():
    result = create_budget({"company": "XX", "dept": "Finance", "mm": 1, "yy": 2026, "amount": 100})
    assert result["ok"] is False
    assert "Company" in result["pesan"]


def test_create_budget_rejects_invalid_month():
    result = create_budget({"company": "PO", "dept": "Finance", "mm": 13, "yy": 2026, "amount": 100})
    assert result["ok"] is False


def test_get_budget_returns_created_row():
    created = create_budget({"company": "TF", "dept": "HR", "mm": 2, "yy": 2026, "amount": 25000000})
    fetched = get_budget(created["id"])
    assert fetched is not None
    assert fetched["company"] == "TF"
    assert fetched["amount"] == 25000000


def test_get_budget_missing_returns_none():
    assert get_budget("DOES-NOT-EXIST") is None


def test_list_budgets_filters_by_company():
    create_budget({"company": "PO", "dept": "IT", "mm": 3, "yy": 2026, "amount": 1000})
    create_budget({"company": "TF", "dept": "IT", "mm": 3, "yy": 2026, "amount": 2000})
    rows = list_budgets({"company": "PO"})
    assert all(r["company"] == "PO" for r in rows)
    assert len(rows) >= 1


def test_update_budget_recomputes_deadline():
    created = create_budget({"company": "PO", "dept": "Finance", "mm": 1, "yy": 2026, "amount": 100})
    result = update_budget(created["id"], {"mm": 5, "yy": 2026, "amount": 200})
    assert result["ok"] is True
    updated = get_budget(created["id"])
    assert updated["deadline"] == compute_deadline(5, 2026)
    assert updated["amount"] == 200


def test_update_budget_missing_returns_error():
    result = update_budget("DOES-NOT-EXIST", {"amount": 100})
    assert result["ok"] is False


def test_delete_budget_removes_row():
    created = create_budget({"company": "PO", "dept": "Finance", "mm": 1, "yy": 2026, "amount": 100})
    result = delete_budget(created["id"])
    assert result["ok"] is True
    assert get_budget(created["id"]) is None


def test_delete_budget_missing_returns_error():
    result = delete_budget("DOES-NOT-EXIST")
    assert result["ok"] is False
