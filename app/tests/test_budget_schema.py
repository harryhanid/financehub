# tests/test_budget_schema.py
from database import get_conn


def test_budget_master_table_exists():
    conn = get_conn()
    cols = {r[1] for r in conn.execute("PRAGMA table_info(budget_master)")}
    conn.close()
    assert cols == {
        "id", "mm", "yy", "company", "dept", "gl_account", "gl_description",
        "budget_category", "activity", "description", "amount", "deadline",
        "created_at", "updated_at",
    }


def test_budget_realisasi_table_exists():
    conn = get_conn()
    cols = {r[1] for r in conn.execute("PRAGMA table_info(budget_realisasi)")}
    conn.close()
    assert cols == {
        "trx_id", "budget_id", "mm", "yy", "company", "dept", "gl_account",
        "gl_description", "budget_category", "activity", "description",
        "amount", "tanggal_realisasi", "created_at",
    }


def test_budget_carryover_logs_table_exists():
    conn = get_conn()
    cols = {r[1] for r in conn.execute("PRAGMA table_info(budget_carryover_logs)")}
    conn.close()
    assert cols == {
        "id", "budget_id", "requested_by", "request_date", "status",
        "approval_date", "extension_months", "reason", "approved_by",
        "type", "additional_amount",
    }


def test_budget_master_id_is_text_primary_key():
    conn = get_conn()
    conn.execute(
        """INSERT INTO budget_master (id, mm, yy, company, dept, amount)
           VALUES ('PO-FIN-26-01-TEST', 1, 2026, 'PO', 'Finance', 1000000)"""
    )
    conn.commit()
    row = conn.execute("SELECT * FROM budget_master WHERE id='PO-FIN-26-01-TEST'").fetchone()
    conn.close()
    assert row["company"] == "PO"


def test_budget_realisasi_references_budget_master():
    conn = get_conn()
    conn.execute(
        """INSERT INTO budget_master (id, mm, yy, company, dept, amount)
           VALUES ('PO-FIN-26-01-TEST2', 1, 2026, 'PO', 'Finance', 1000000)"""
    )
    conn.execute(
        """INSERT INTO budget_realisasi (trx_id, budget_id, amount, tanggal_realisasi)
           VALUES ('TRX-TEST', 'PO-FIN-26-01-TEST2', 500000, '2026-01-15')"""
    )
    conn.commit()
    row = conn.execute("SELECT * FROM budget_realisasi WHERE trx_id='TRX-TEST'").fetchone()
    conn.close()
    assert row["budget_id"] == "PO-FIN-26-01-TEST2"
