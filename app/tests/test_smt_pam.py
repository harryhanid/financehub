import os, sys, pytest, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config
config.DB_PATH = os.path.join(os.path.dirname(__file__), "test_smt_pam.db")

from database import init_db, get_conn

SMT_COMPANY_ID = 1


@pytest.fixture(autouse=True)
def clean_db():
    # Cleanup before test
    if os.path.exists(config.DB_PATH):
        time.sleep(0.1)
        try:
            os.remove(config.DB_PATH)
        except PermissionError:
            pass
    init_db()
    yield
    # Cleanup after test
    if os.path.exists(config.DB_PATH):
        time.sleep(0.1)  # Allow WAL mode to release lock
        try:
            os.remove(config.DB_PATH)
        except PermissionError:
            pass  # WAL journal may still be held on Windows


def _columns(conn, table):
    return [r["name"] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]


def test_smt_pam_lines_table_exists():
    conn = get_conn()
    cols = _columns(conn, "smt_pam_lines")
    conn.close()
    expected = ["id", "pam_id", "no_vendor", "nama_vendor",
                "tgl_terima_doc", "tgl_proses", "tgl_verifikasi_tax",
                "tgl_approval_1", "tgl_approval_2", "tgl_approval_3",
                "tgl_kirim", "tgl_realisasi", "created_at", "updated_at"]
    for col in expected:
        assert col in cols, f"Missing column: {col}"


def test_advance_pam_lines_table_exists():
    conn = get_conn()
    cols = _columns(conn, "advance_pam_lines")
    conn.close()
    expected = ["id", "pam_id", "no_vendor", "nama_vendor",
                "tgl_received", "tgl_a0", "tgl_a1", "tgl_a2", "tgl_a3",
                "tgl_a4", "tgl_paid", "created_at", "updated_at"]
    for col in expected:
        assert col in cols, f"Missing column: {col}"
