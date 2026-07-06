import os, sys, pytest, time, uuid
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config
config.DB_PATH = os.path.join(os.path.dirname(__file__), "test_smt_pam.db")

from database import init_db, get_conn

SMT_COMPANY_ID = 1


@pytest.fixture(autouse=True)
def clean_db():
    # Each test gets its own db file. Relying on deleting a single shared
    # file for isolation is unreliable on Windows: database.migrate_db()
    # (called by init_db()) opens a connection it never closes, so a
    # previous test's handle can still hold tests/test_smt_pam.db locked
    # when the next test's cleanup tries to remove it — causing stale
    # rows to leak across tests (silently, since PermissionError here is
    # swallowed by design). Using a unique path per test sidesteps that
    # leaked-connection issue entirely without touching database.py,
    # which is out of scope for this change.
    base = os.path.join(os.path.dirname(__file__), "test_smt_pam.db")
    config.DB_PATH = f"{base}.{uuid.uuid4().hex}"
    if os.path.exists(config.DB_PATH):
        try:
            os.remove(config.DB_PATH)
        except PermissionError:
            pass
    init_db()
    yield
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


from modules.payment_memo.service import get_pam_by_pillar, upsert_pam_lines, get_next_pam_no


def _seed_pam(conn, pam_no, pillar, company_id=SMT_COMPANY_ID):
    conn.execute(
        """INSERT INTO pam_records
           (company_id, pam_no, pam_date, gl_account, cost_center, pt,
            requestors_name, keterangan, mata_uang, dpp, ppn,
            total_amount, due_date, status, source, pillar)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (company_id, pam_no, "2026-07-01", "70110230", "1008C1POFF",
         "PT. Sinar Mas Tjipta", "Jany Turkanda", "Test",
         "IDR", 9000000, 0, 9000000, "2026-07-31", "open", "others", pillar)
    )
    conn.commit()
    return conn.execute(
        "SELECT id FROM pam_records WHERE pam_no=?", (pam_no,)
    ).fetchone()["id"]


def test_get_pam_by_pillar_smt():
    conn = get_conn()
    _seed_pam(conn, "PAM-001-SMT-07-2026", "SMT")
    conn.close()
    rows = get_pam_by_pillar(SMT_COMPANY_ID, "SMT")
    assert len(rows) == 1
    assert rows[0]["pillar"] == "SMT"
    assert rows[0]["no_vendor"] is None
    assert "tgl_realisasi" in rows[0]


def test_get_pam_by_pillar_advance_has_custom_columns():
    conn = get_conn()
    pam_id = _seed_pam(conn, "PAM-002-SMT-07-2026", "ADVANCE")
    conn.execute(
        """INSERT INTO advance_pam_lines (pam_id, no_vendor, nama_vendor, tgl_received)
           VALUES (?,?,?,?)""",
        (pam_id, "V-100", "PT. Maju Jaya", "2026-07-02")
    )
    conn.commit()
    conn.close()
    rows = get_pam_by_pillar(SMT_COMPANY_ID, "ADVANCE")
    assert len(rows) == 1
    assert rows[0]["no_vendor"]    == "V-100"
    assert rows[0]["nama_vendor"]  == "PT. Maju Jaya"
    assert rows[0]["tgl_received"] == "2026-07-02"
    assert rows[0]["tgl_a0"] is None
    assert rows[0]["tgl_paid"] is None


def test_upsert_pam_lines_smt_standard_fields():
    conn = get_conn()
    pam_id = _seed_pam(conn, "PAM-003-SMT-07-2026", "SMT")
    conn.close()
    result = upsert_pam_lines(pam_id, "SMT", {
        "no_vendor": "V-200", "nama_vendor": "PT. Sentosa",
        "tgl_terima_doc": "2026-07-03"
    }, SMT_COMPANY_ID)
    assert result["ok"] is True
    rows = get_pam_by_pillar(SMT_COMPANY_ID, "SMT")
    assert rows[0]["tgl_terima_doc"] == "2026-07-03"


def test_upsert_pam_lines_advance_custom_fields():
    conn = get_conn()
    pam_id = _seed_pam(conn, "PAM-004-SMT-07-2026", "ADVANCE")
    conn.close()
    result = upsert_pam_lines(pam_id, "ADVANCE", {
        "no_vendor": "V-300", "nama_vendor": "PT. Abadi",
        "tgl_received": "2026-07-04", "tgl_a0": "2026-07-05"
    }, SMT_COMPANY_ID)
    assert result["ok"] is True
    rows = get_pam_by_pillar(SMT_COMPANY_ID, "ADVANCE")
    assert rows[0]["tgl_received"] == "2026-07-04"
    assert rows[0]["tgl_a0"]       == "2026-07-05"


def test_upsert_pam_lines_advance_rejects_standard_field_names():
    conn = get_conn()
    pam_id = _seed_pam(conn, "PAM-005-SMT-07-2026", "ADVANCE")
    conn.close()
    result = upsert_pam_lines(pam_id, "ADVANCE", {
        "tgl_terima_doc": "2026-07-06"  # not a valid Advance field
    }, SMT_COMPANY_ID)
    assert result["ok"] is False


def test_smt_and_advance_share_pam_number_sequence():
    smt_no      = get_next_pam_no(SMT_COMPANY_ID, "SMT", "smt", "2026-07-01")
    advance_no  = get_next_pam_no(SMT_COMPANY_ID, "SMT", "advance", "2026-07-01")
    assert smt_no     == "PAM-001-SMT-07-2026"
    assert advance_no == "PAM-001-SMT-07-2026"  # same prefix, would collide if both were "open" same day — expected, matches confirmed design (shared sequence)
