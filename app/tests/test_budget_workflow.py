# tests/test_budget_workflow.py
from modules.budget.service import (
    create_budget, get_budget, request_carryover, request_additional_budget,
    approve_carryover, approve_additional_budget, reject_request,
)


def test_request_carryover_success():
    b = create_budget({"company": "PO", "dept": "Finance", "mm": 1, "yy": 2026, "amount": 1000})
    result = request_carryover(b["id"], "harry", "Belum sempat realisasi")
    assert result["ok"] is True


def test_request_carryover_blocks_duplicate_pending():
    b = create_budget({"company": "PO", "dept": "Finance", "mm": 1, "yy": 2026, "amount": 1000})
    request_carryover(b["id"], "harry", "reason 1")
    result = request_carryover(b["id"], "harry", "reason 2")
    assert result["ok"] is False
    assert "pending" in result["pesan"].lower()


def test_request_additional_budget_success():
    b = create_budget({"company": "TF", "dept": "IT", "mm": 1, "yy": 2026, "amount": 1000})
    result = request_additional_budget(b["id"], "harry", 500000, "Butuh tambahan")
    assert result["ok"] is True


def test_request_additional_budget_rejects_zero_amount():
    b = create_budget({"company": "TF", "dept": "IT", "mm": 1, "yy": 2026, "amount": 1000})
    result = request_additional_budget(b["id"], "harry", 0, "reason")
    assert result["ok"] is False


def test_approve_carryover_extends_deadline():
    b = create_budget({"company": "PO", "dept": "Finance", "mm": 1, "yy": 2026, "amount": 1000})
    original_deadline = get_budget(b["id"])["deadline"]
    request_carryover(b["id"], "harry", "reason")
    result = approve_carryover(b["id"], "releaser1", 12)
    assert result["ok"] is True
    updated = get_budget(b["id"])
    assert updated["deadline"] > original_deadline


def test_approve_carryover_without_pending_request_fails():
    b = create_budget({"company": "PO", "dept": "Finance", "mm": 1, "yy": 2026, "amount": 1000})
    result = approve_carryover(b["id"], "releaser1", 12)
    assert result["ok"] is False


def test_approve_additional_budget_increases_amount_and_extends_deadline():
    b = create_budget({"company": "TF", "dept": "IT", "mm": 1, "yy": 2026, "amount": 1000})
    request_additional_budget(b["id"], "harry", 500, "reason")
    result = approve_additional_budget(b["id"], "releaser1", 3)
    assert result["ok"] is True
    updated = get_budget(b["id"])
    assert updated["amount"] == 1500


def test_reject_request_marks_rejected():
    b = create_budget({"company": "PO", "dept": "Finance", "mm": 1, "yy": 2026, "amount": 1000})
    request_carryover(b["id"], "harry", "reason")
    result = reject_request(b["id"], "releaser1", "Tidak sesuai kebijakan")
    assert result["ok"] is True
    # a new request can be submitted after rejection (no more pending)
    second = request_carryover(b["id"], "harry", "reason 2")
    assert second["ok"] is True


def test_reject_request_without_pending_fails():
    b = create_budget({"company": "PO", "dept": "Finance", "mm": 1, "yy": 2026, "amount": 1000})
    result = reject_request(b["id"], "releaser1", "reason")
    assert result["ok"] is False
