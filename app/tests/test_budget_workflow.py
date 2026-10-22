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


# --- Task 10 (atomic-flows.md): approve_* dijalankan sebagai satu fungsi plpgsql -------------------

import pytest
from datetime import datetime
from database import get_conn
from modules.budget.service import _add_months


def _snapshot(budget_id):
    conn = get_conn()
    b = dict(conn.execute("SELECT amount, deadline, updated_at FROM budget_master WHERE id=?",
                          (budget_id,)).fetchone())
    logs = [dict(r) for r in conn.execute(
        "SELECT id, status, approval_date, approved_by, extension_months FROM budget_carryover_logs "
        "WHERE budget_id=? ORDER BY id", (budget_id,)).fetchall()]
    counts = (conn.execute("SELECT COUNT(*) FROM budget_master").fetchone()[0],
              conn.execute("SELECT COUNT(*) FROM budget_carryover_logs").fetchone()[0])
    conn.close()
    return b, logs, counts


def _fail_log_approval():
    """Paksa langkah terakhir (UPDATE log -> Approved) gagal lewat CHECK sementara."""
    conn = get_conn()
    conn.execute("ALTER TABLE budget_carryover_logs ADD CONSTRAINT t10_no_approve "
                 "CHECK (status <> 'Approved') NOT VALID")
    conn.close()


def _drop_fail_log_approval():
    conn = get_conn()
    conn.execute("ALTER TABLE budget_carryover_logs DROP CONSTRAINT IF EXISTS t10_no_approve")
    conn.close()


def test_approve_carryover_atomic_on_failure():
    b = create_budget({"company": "PO", "dept": "Finance", "mm": 1, "yy": 2026, "amount": 1000})
    request_carryover(b["id"], "harry", "reason")
    before = _snapshot(b["id"])
    _fail_log_approval()
    try:
        with pytest.raises(Exception):
            approve_carryover(b["id"], "releaser1", 12)
    finally:
        _drop_fail_log_approval()
    assert _snapshot(b["id"]) == before


def test_approve_additional_budget_atomic_on_failure():
    b = create_budget({"company": "TF", "dept": "IT", "mm": 1, "yy": 2026, "amount": 1000})
    request_additional_budget(b["id"], "harry", 500, "reason")
    before = _snapshot(b["id"])
    _fail_log_approval()
    try:
        with pytest.raises(Exception):
            approve_additional_budget(b["id"], "releaser1", 3)
    finally:
        _drop_fail_log_approval()
    assert _snapshot(b["id"]) == before
    assert get_budget(b["id"])["amount"] == 1000


def test_approve_carryover_deadline_matches_python_add_months():
    """Deadline dihitung di SQL harus sama dengan _add_months Python (termasuk potong akhir bulan)."""
    b = create_budget({"company": "PO", "dept": "Finance", "mm": 11, "yy": 2025, "amount": 1000})
    old = get_budget(b["id"])["deadline"]  # 2026-01-31
    request_carryover(b["id"], "harry", "reason")
    assert approve_carryover(b["id"], "releaser1", 1)["ok"] is True
    upd = get_budget(b["id"])
    assert upd["deadline"] == _add_months(datetime.fromisoformat(old).date(), 1).isoformat() == "2026-02-28"
    conn = get_conn()
    log = conn.execute("SELECT status, extension_months, approved_by FROM budget_carryover_logs "
                       "WHERE budget_id=?", (b["id"],)).fetchone()
    conn.close()
    assert (log["status"], log["extension_months"], log["approved_by"]) == ("Approved", 1, "releaser1")


def test_approve_carryover_null_deadline_uses_today():
    b = create_budget({"company": "PO", "dept": "Finance", "mm": 1, "yy": 2026, "amount": 1000})
    conn = get_conn()
    conn.execute("UPDATE budget_master SET deadline=NULL WHERE id=?", (b["id"],))
    conn.close()
    request_carryover(b["id"], "harry", "reason")
    approve_carryover(b["id"], "releaser1", 2)
    assert get_budget(b["id"])["deadline"] == _add_months(datetime.now().date(), 2).isoformat()


def test_approve_additional_budget_twice_adds_once():
    b = create_budget({"company": "TF", "dept": "IT", "mm": 1, "yy": 2026, "amount": 1000})
    request_additional_budget(b["id"], "harry", 500, "reason")
    first = approve_additional_budget(b["id"], "releaser1", 3)
    second = approve_additional_budget(b["id"], "releaser1", 3)
    assert first["ok"] is True and "500" in first["pesan"]
    assert second["ok"] is False
    upd = get_budget(b["id"])
    assert upd["amount"] == 1500
    assert upd["deadline"] == _add_months(datetime.now().date(), 3).isoformat()


def test_approve_invalid_months_without_pending_returns_message():
    """Faithful: SQLite versi lama baru memanggil int() setelah cek log Pending."""
    b = create_budget({"company": "PO", "dept": "Finance", "mm": 1, "yy": 2026, "amount": 1000})
    assert approve_carryover(b["id"], "r", "abc")["ok"] is False
    assert approve_additional_budget(b["id"], "r", "abc")["ok"] is False
    request_carryover(b["id"], "harry", "reason")
    with pytest.raises(ValueError):
        approve_carryover(b["id"], "r", "abc")
