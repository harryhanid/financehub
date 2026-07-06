import os, sys, pytest, sqlite3
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config
config.DB_PATH = os.path.join(os.path.dirname(__file__), "test_coa_pam.db")

from database import init_db, get_conn


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
            pass


def _columns(conn, table):
    return [r["name"] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]


def test_coa_pam_table_exists_with_expected_columns():
    conn = get_conn()
    cols = _columns(conn, "coa_pam")
    conn.close()
    for col in ["id", "klasifikasi_sr", "klasifikasi_mr", "coa_advance", "coa_expense"]:
        assert col in cols, f"Missing column: {col}"


def test_coa_pam_seeded_with_44_rows():
    conn = get_conn()
    count = conn.execute("SELECT COUNT(*) AS n FROM coa_pam").fetchone()["n"]
    conn.close()
    assert count == 44


def test_coa_pam_beasiswa_row_values():
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM coa_pam WHERE klasifikasi_sr = 'Beasiswa'"
    ).fetchone()
    conn.close()
    assert row is not None
    assert row["klasifikasi_mr"] == "Scholarship Expense"
    assert row["coa_advance"] is None
    assert row["coa_expense"] == "70110230"


def test_coa_pam_advance_row_has_coa_advance_code():
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM coa_pam WHERE klasifikasi_sr = 'Advance for Training'"
    ).fetchone()
    conn.close()
    assert row is not None
    assert row["coa_advance"] == "16001300"
    assert row["coa_expense"] == "70110200"


def test_pam_transaction_lines_table_exists_with_expected_columns():
    conn = get_conn()
    cols = _columns(conn, "pam_transaction_lines")
    conn.close()
    expected = [
        "id", "pam_id", "coa_pam_id", "klasifikasi_sr", "klasifikasi_mr",
        "gl_account", "tipe_dokumen", "no_invoice", "dpp", "ppn",
        "total_amount", "cost_center", "budget_activity", "keterangan",
        "created_at", "updated_at",
    ]
    for col in expected:
        assert col in cols, f"Missing column: {col}"


def test_pam_transaction_lines_cascades_on_pam_delete():
    conn = get_conn()
    conn.execute(
        """INSERT INTO pam_records
           (company_id, pam_no, pam_date, requestors_name, keterangan,
            total_amount, due_date, pillar, source, status)
           VALUES (1,'PAM-999-SMT-07-2026','2026-07-06','Jany Turkanda','Test',
                   100000,'2026-08-06','SMT','gl','open')"""
    )
    pam_id = conn.execute(
        "SELECT id FROM pam_records WHERE pam_no='PAM-999-SMT-07-2026'"
    ).fetchone()["id"]
    conn.execute(
        """INSERT INTO pam_transaction_lines
           (pam_id, klasifikasi_sr, klasifikasi_mr, gl_account, dpp, ppn, total_amount)
           VALUES (?,'Beasiswa','Scholarship Expense','70110230',100000,0,100000)""",
        (pam_id,)
    )
    conn.commit()
    conn.execute("DELETE FROM pam_records WHERE id=?", (pam_id,))
    conn.commit()
    remaining = conn.execute(
        "SELECT COUNT(*) AS n FROM pam_transaction_lines WHERE pam_id=?", (pam_id,)
    ).fetchone()["n"]
    conn.close()
    assert remaining == 0
