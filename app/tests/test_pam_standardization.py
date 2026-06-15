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


# ── Task 2: Service ─────────────────────────────────────────────────────────

from modules.payment_memo.service import get_pam_by_pillar, upsert_pam_lines

COMPANY_ID = 2


def _seed_pam(conn, pam_no, pillar):
    conn.execute(
        """INSERT INTO pam_records
           (company_id, pam_no, pam_date, gl_account, cost_center, pt,
            requestors_name, keterangan, mata_uang, dpp, ppn,
            total_amount, due_date, status, source, pillar)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (COMPANY_ID, pam_no, "2026-06-01", "70110230", "1008C1POFF",
         "PT. SMART Tbk", "Jany Turkanda", "Test",
         "IDR", 9000000, 0, 9000000, "2026-06-30", "open", "beasiswa", pillar)
    )
    conn.commit()
    return conn.execute(
        "SELECT id FROM pam_records WHERE pam_no=?", (pam_no,)
    ).fetchone()["id"]


def test_get_pam_by_pillar_returns_correct_rows():
    conn = get_conn()
    _seed_pam(conn, "PAM-001-ETF-06-2026", "AGRI")
    _seed_pam(conn, "PAM-002-ETF-06-2026", "APP")
    conn.close()

    rows = get_pam_by_pillar(COMPANY_ID, "AGRI")
    assert len(rows) == 1
    assert rows[0]["pam_no"] == "PAM-001-ETF-06-2026"
    assert rows[0]["pillar"] == "AGRI"


def test_get_pam_by_pillar_includes_lines_columns():
    conn = get_conn()
    pam_id = _seed_pam(conn, "PAM-003-ETF-06-2026", "APP")
    conn.execute(
        """INSERT INTO app_pam_lines (pam_id, no_vendor, nama_vendor, tgl_approval_1)
           VALUES (?,?,?,?)""",
        (pam_id, "V-001", "PT. Maju", "2026-06-05")
    )
    conn.commit()
    conn.close()

    rows = get_pam_by_pillar(COMPANY_ID, "APP")
    assert len(rows) == 1
    assert rows[0]["no_vendor"]      == "V-001"
    assert rows[0]["nama_vendor"]    == "PT. Maju"
    assert rows[0]["tgl_approval_1"] == "2026-06-05"


def test_get_pam_by_pillar_left_join_no_lines_shows_row():
    conn = get_conn()
    _seed_pam(conn, "PAM-004-ETF-06-2026", "LAND")
    conn.close()

    rows = get_pam_by_pillar(COMPANY_ID, "LAND")
    assert len(rows) == 1
    assert rows[0]["pam_no"]    == "PAM-004-ETF-06-2026"
    assert rows[0]["no_vendor"] is None   # no lines row yet


def test_upsert_pam_lines_inserts_new():
    conn = get_conn()
    pam_id = _seed_pam(conn, "PAM-005-ETF-06-2026", "AGRI")
    conn.close()

    result = upsert_pam_lines(pam_id, "AGRI", {
        "no_vendor": "V-002",
        "nama_vendor": "PT. Agro",
        "tgl_terima_doc": "2026-06-02",
    }, COMPANY_ID)
    assert result["ok"] is True

    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM agri_pam_lines WHERE pam_id=?", (pam_id,)
    ).fetchone()
    conn.close()
    assert row is not None
    assert row["no_vendor"]      == "V-002"
    assert row["tgl_terima_doc"] == "2026-06-02"


def test_upsert_pam_lines_updates_existing():
    conn = get_conn()
    pam_id = _seed_pam(conn, "PAM-006-ETF-06-2026", "SETF")
    conn.execute(
        "INSERT INTO setf_pam_lines (pam_id, no_vendor) VALUES (?,?)",
        (pam_id, "OLD-001")
    )
    conn.commit()
    conn.close()

    result = upsert_pam_lines(pam_id, "SETF", {"no_vendor": "NEW-001"}, COMPANY_ID)
    assert result["ok"] is True

    conn = get_conn()
    row = conn.execute(
        "SELECT no_vendor FROM setf_pam_lines WHERE pam_id=?", (pam_id,)
    ).fetchone()
    conn.close()
    assert row["no_vendor"] == "NEW-001"


def test_upsert_pam_lines_invalid_pillar():
    result = upsert_pam_lines(1, "UNKNOWN", {"no_vendor": "X"}, COMPANY_ID)
    assert result["ok"] is False


def test_upsert_pam_lines_wrong_company_rejected():
    conn = get_conn()
    pam_id = _seed_pam(conn, "PAM-007-ETF-06-2026", "APP")
    conn.close()

    result = upsert_pam_lines(pam_id, "APP", {"no_vendor": "X"}, company_id=99)
    assert result["ok"] is False
