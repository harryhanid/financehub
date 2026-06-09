import os, sys, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config
config.DB_PATH = os.path.join(os.path.dirname(__file__), "test_finance_hub.db")

from database import init_db, get_conn
from modules.payment_memo.service import (
    generate_memo_number, get_draft_payments, create_memo, update_memo_status,
    get_memo_list, get_memo_detail
)

COMPANY_ID   = 2  # ETF
COMPANY_CODE = "ETF"

@pytest.fixture(autouse=True)
def clean_db():
    if os.path.exists(config.DB_PATH):
        os.remove(config.DB_PATH)
    init_db()
    yield
    if os.path.exists(config.DB_PATH):
        os.remove(config.DB_PATH)

def _add_draft_payment(siswa_code="1250001", amount=5000000):
    conn = get_conn()
    conn.execute(
        "INSERT INTO payment_beasiswa (company_id, siswa_code, cat1, cat2, tanggal, amount, pillar, perusahaan, status) "
        "VALUES (?,?,?,?,?,?,?,?,'open')",
        (COMPANY_ID, siswa_code, "By Pendidikan", "Semester 1", "2025-06-01", amount, "AGRI", "PT. SMART Tbk")
    )
    last_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit(); conn.close()
    return last_id

def test_generate_memo_number_first():
    num = generate_memo_number(COMPANY_ID, COMPANY_CODE, "2025")
    assert num == "PAM/ETF/2025/001"

def test_generate_memo_number_increments():
    conn = get_conn()
    conn.execute("INSERT INTO payment_memo (company_id, memo_number, status) VALUES (?,?,?)",
        (COMPANY_ID, "PAM/ETF/2025/001", "open"))
    conn.execute("INSERT INTO payment_memo (company_id, memo_number, status) VALUES (?,?,?)",
        (COMPANY_ID, "PAM/ETF/2025/002", "open"))
    conn.commit(); conn.close()
    num = generate_memo_number(COMPANY_ID, COMPANY_CODE, "2025")
    assert num == "PAM/ETF/2025/003"

def test_get_draft_payments_empty():
    rows = get_draft_payments(COMPANY_ID)
    assert rows == []

def test_get_draft_payments_returns_draft_only():
    pay_id = _add_draft_payment()
    rows   = get_draft_payments(COMPANY_ID)
    assert len(rows) == 1
    assert rows[0]["id"] == pay_id

def test_create_memo_success():
    pay_id = _add_draft_payment()
    result = create_memo(COMPANY_ID, COMPANY_CODE, "2025-06-10", "Memo test",
                         "admin", [{"source_id": pay_id, "source_module": "beasiswa",
                                    "description": "By Pendidikan Sem 1", "amount": 5000000,
                                    "vendor": "Budi", "bank_account": "BCA 1234"}])
    assert result["ok"] is True
    assert "PAM/ETF" in result["memo_number"]

def test_create_memo_updates_payment_status():
    pay_id = _add_draft_payment()
    create_memo(COMPANY_ID, COMPANY_CODE, "2025-06-10", "", "admin",
                [{"source_id": pay_id, "source_module": "beasiswa",
                  "description": "", "amount": 5000000,
                  "vendor": "", "bank_account": ""}])
    conn = get_conn()
    row  = conn.execute("SELECT status FROM payment_beasiswa WHERE id=?", (pay_id,)).fetchone()
    conn.close()
    assert row["status"] == "on_process"

def test_get_memo_list():
    pay_id = _add_draft_payment()
    create_memo(COMPANY_ID, COMPANY_CODE, "2025-06-10", "", "admin",
                [{"source_id": pay_id, "source_module": "beasiswa",
                  "description": "", "amount": 5000000, "vendor": "", "bank_account": ""}])
    memos = get_memo_list(COMPANY_ID)
    assert len(memos) == 1

def test_update_memo_status_on_process():
    # "approved" status removed — new lifecycle: draft → on_process → complete
    pay_id = _add_draft_payment()
    result = create_memo(COMPANY_ID, COMPANY_CODE, "2025-06-10", "", "admin",
                         [{"source_id": pay_id, "source_module": "beasiswa",
                           "description": "", "amount": 5000000, "vendor": "", "bank_account": ""}])
    memo_id = result["memo_id"]
    upd = update_memo_status(memo_id, "on_process", "manager", company_id=COMPANY_ID)
    assert upd["ok"] is True
    conn = get_conn()
    row  = conn.execute("SELECT status FROM payment_memo WHERE id=?", (memo_id,)).fetchone()
    conn.close()
    assert row["status"] == "on_process"
