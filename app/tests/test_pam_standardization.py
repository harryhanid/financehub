import os, sys, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config
config.DB_PATH = os.path.join(os.path.dirname(__file__), "test_pam_std.db")

from database import init_db, get_conn

@pytest.fixture(autouse=True)
def clean_db():
    if os.path.exists(config.DB_PATH):
        os.remove(config.DB_PATH)
    init_db()
    yield
    if os.path.exists(config.DB_PATH):
        os.remove(config.DB_PATH)


def _columns(conn, table):
    return [r["name"] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]


def test_pam_records_has_new_columns():
    conn = get_conn()
    cols = _columns(conn, "pam_records")
    conn.close()
    assert "mata_uang" in cols
    assert "dpp"       in cols
    assert "ppn"       in cols
    assert "pillar"    in cols


def test_agri_pam_lines_table_exists():
    conn = get_conn()
    cols = _columns(conn, "agri_pam_lines")
    conn.close()
    expected = ["id", "pam_id", "no_vendor", "nama_vendor",
                "tgl_terima_doc", "tgl_proses", "tgl_verifikasi_tax",
                "tgl_approval_1", "tgl_approval_2", "tgl_approval_3",
                "tgl_kirim", "created_at", "updated_at"]
    for col in expected:
        assert col in cols, f"Missing column: {col}"


def test_app_pam_lines_table_exists():
    conn = get_conn()
    cols = _columns(conn, "app_pam_lines")
    conn.close()
    assert "pam_id" in cols
    assert "tgl_approval_1" in cols


def test_land_pam_lines_table_exists():
    conn = get_conn()
    cols = _columns(conn, "land_pam_lines")
    conn.close()
    assert "pam_id" in cols
    assert "tgl_kirim" in cols


def test_setf_pam_lines_table_exists():
    conn = get_conn()
    cols = _columns(conn, "setf_pam_lines")
    conn.close()
    assert "pam_id" in cols
    assert "tgl_verifikasi_tax" in cols
