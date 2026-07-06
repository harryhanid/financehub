import os, sys, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config
config.DB_PATH = os.path.join(os.path.dirname(__file__), "test_pam_smt_lines_service.db")

from database import init_db, get_conn
from modules.payment_memo.service import (
    get_coa_pam_list, get_pam_transaction_lines, save_smt_pam_transaction,
)

SMT_COMPANY_ID = 1


@pytest.fixture(autouse=True)
def clean_db():
    if os.path.exists(config.DB_PATH):
        try:
            os.remove(config.DB_PATH)
        except:
            pass
    init_db()
    yield
    if os.path.exists(config.DB_PATH):
        try:
            os.remove(config.DB_PATH)
        except:
            # Pre-existing Windows SQLite connection handle leak during teardown
            pass


def test_get_coa_pam_list_returns_all_when_no_search():
    rows = get_coa_pam_list()
    assert len(rows) == 44
    assert rows[0]["klasifikasi_sr"]


def test_get_coa_pam_list_filters_by_search():
    rows = get_coa_pam_list("Beasiswa")
    assert len(rows) == 1
    assert rows[0]["klasifikasi_mr"] == "Scholarship Expense"


def _coa_pam_id(sr):
    conn = get_conn()
    row = conn.execute(
        "SELECT id, coa_expense, coa_advance FROM coa_pam WHERE klasifikasi_sr=?", (sr,)
    ).fetchone()
    conn.close()
    return dict(row)


def test_save_smt_pam_transaction_gl_sums_lines_into_header():
    coa = _coa_pam_id("Beasiswa")
    data = {
        "tanggal": "2026-07-06", "pam_no": "PAM-100-SMT-07-2026",
        "perusahaan": "PT. Sinar Mas Tjipta", "pillar": "SMT", "transaksi": "gl",
        "rows": [
            {"coa_pam_id": coa["id"], "klasifikasi_sr": "Beasiswa",
             "klasifikasi_mr": "Scholarship Expense", "gl_account": coa["coa_expense"],
             "tipe_dokumen": "Invoice Payment – Non PO Invoice", "no_invoice": "INV-001",
             "dpp": 1000000, "ppn": 110000, "cost_center": "POCCOM",
             "budget_activity": "Program A", "keterangan": "Baris 1"},
            {"coa_pam_id": coa["id"], "klasifikasi_sr": "Beasiswa",
             "klasifikasi_mr": "Scholarship Expense", "gl_account": coa["coa_expense"],
             "tipe_dokumen": "Invoice Payment – Non PO Invoice", "no_invoice": "INV-002",
             "dpp": 500000, "ppn": 0, "cost_center": "TFOPEX",
             "budget_activity": "Program B", "keterangan": "Baris 2"},
        ],
    }
    result = save_smt_pam_transaction(SMT_COMPANY_ID, "SMT", data)
    assert result["ok"] is True
    assert result["pam_no"] == "PAM-100-SMT-07-2026"

    conn = get_conn()
    header = conn.execute(
        "SELECT * FROM pam_records WHERE pam_no='PAM-100-SMT-07-2026'"
    ).fetchone()
    conn.close()
    assert header["total_amount"] == 1610000
    assert header["dpp"] == 1500000
    assert header["ppn"] == 110000
    assert header["pillar"] == "SMT"

    lines = get_pam_transaction_lines(header["id"])
    assert len(lines) == 2
    assert {l["cost_center"] for l in lines} == {"POCCOM", "TFOPEX"}
    assert lines[0]["gl_account"] == coa["coa_expense"]


def test_save_smt_pam_transaction_advance_uses_coa_advance_gl():
    coa = _coa_pam_id("Advance for Training")
    data = {
        "tanggal": "2026-07-06", "pam_no": "PAM-101-SMT-07-2026",
        "perusahaan": "PT. Sinar Mas Tjipta", "pillar": "ADVANCE", "transaksi": "advance",
        "rows": [
            {"coa_pam_id": coa["id"], "klasifikasi_sr": "Advance for Training",
             "klasifikasi_mr": "Advance Training", "gl_account": coa["coa_advance"],
             "tipe_dokumen": "Employee Advance / Reimbursement (Fund Transfer)",
             "no_invoice": "", "dpp": 2000000, "ppn": 0, "cost_center": "POITEC",
             "budget_activity": "Training Q3", "keterangan": "Advance training"},
        ],
    }
    result = save_smt_pam_transaction(SMT_COMPANY_ID, "SMT", data)
    assert result["ok"] is True

    conn = get_conn()
    header = conn.execute(
        "SELECT * FROM pam_records WHERE pam_no='PAM-101-SMT-07-2026'"
    ).fetchone()
    conn.close()
    assert header["pillar"] == "ADVANCE"
    lines = get_pam_transaction_lines(header["id"])
    assert lines[0]["gl_account"] == coa["coa_advance"]


def test_save_smt_pam_transaction_rejects_no_rows():
    result = save_smt_pam_transaction(SMT_COMPANY_ID, "SMT", {
        "tanggal": "2026-07-06", "pam_no": "PAM-102-SMT-07-2026",
        "perusahaan": "PT. Sinar Mas Tjipta", "pillar": "SMT", "transaksi": "gl",
        "rows": [],
    })
    assert result["ok"] is False


def test_save_smt_pam_transaction_rejects_row_missing_klasifikasi_sr():
    result = save_smt_pam_transaction(SMT_COMPANY_ID, "SMT", {
        "tanggal": "2026-07-06", "pam_no": "PAM-103-SMT-07-2026",
        "perusahaan": "PT. Sinar Mas Tjipta", "pillar": "SMT", "transaksi": "gl",
        "rows": [{"klasifikasi_sr": "", "dpp": 1000, "keterangan": "x"}],
    })
    assert result["ok"] is False


def test_save_smt_pam_transaction_rejects_row_with_zero_dpp():
    result = save_smt_pam_transaction(SMT_COMPANY_ID, "SMT", {
        "tanggal": "2026-07-06", "pam_no": "PAM-104-SMT-07-2026",
        "perusahaan": "PT. Sinar Mas Tjipta", "pillar": "SMT", "transaksi": "gl",
        "rows": [{"klasifikasi_sr": "Beasiswa", "dpp": 0, "keterangan": "x"}],
    })
    assert result["ok"] is False


def test_save_smt_pam_transaction_rejects_row_missing_keterangan():
    result = save_smt_pam_transaction(SMT_COMPANY_ID, "SMT", {
        "tanggal": "2026-07-06", "pam_no": "PAM-105-SMT-07-2026",
        "perusahaan": "PT. Sinar Mas Tjipta", "pillar": "SMT", "transaksi": "gl",
        "rows": [{"klasifikasi_sr": "Beasiswa", "dpp": 1000, "keterangan": ""}],
    })
    assert result["ok"] is False
