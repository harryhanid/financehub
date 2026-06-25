import os, sys, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config
config.DB_PATH = os.path.join(os.path.dirname(__file__), "test_beasiswa_lines.db")

from database import init_db, get_conn
from modules.payment_memo.service import get_pam_beasiswa_lines

COMPANY_ID = 2


@pytest.fixture(autouse=True)
def clean_db():
    if os.path.exists(config.DB_PATH):
        os.remove(config.DB_PATH)
    init_db()
    yield
    import gc
    gc.collect()
    import time
    time.sleep(0.1)
    if os.path.exists(config.DB_PATH):
        try:
            os.remove(config.DB_PATH)
        except PermissionError:
            pass


def _seed(conn):
    """Insert 1 pam_record + 2 siswa + 2 payment_beasiswa rows. Returns pam_id (int)."""
    conn.execute(
        "INSERT INTO pam_records (company_id, pam_no, source, status, created_at) VALUES (?,?,?,?,?)",
        (COMPANY_ID, "PAM-TEST-001", "etf_agri", "open", "2026-01-01"),
    )
    pam_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.execute(
        "INSERT INTO siswa (company_id, code, nama) VALUES (?,?,?)",
        (COMPANY_ID, "S001", "Zara Dewi"),
    )
    conn.execute(
        "INSERT INTO siswa (company_id, code, nama) VALUES (?,?,?)",
        (COMPANY_ID, "S002", "Andi Kurniawan"),
    )
    conn.execute(
        """INSERT INTO payment_beasiswa
           (company_id, siswa_code, pam, tanggal, amount, cat1, cat2, status,
            tgl_pengajuan, tgl_receive, tgl_pa, tgl_final,
            SLA_Date_1_LL, SLA_Date_2_HT, SLA_Date_3_YK, SLA_Date_4_AK,
            SLA_Date_5_PD, SLA_Date_6_C2, SLA_Date_7_MSIG)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (COMPANY_ID, "S001", "PAM-TEST-001", "2026-01-01", 5000000,
         "By Pendidikan", "S1", "open",
         "2026-01-05", "2026-01-10", None, None,
         None, "2026-01-12", None, None, None, None, None),
    )
    conn.execute(
        """INSERT INTO payment_beasiswa
           (company_id, siswa_code, pam, tanggal, amount, cat1, cat2, status,
            tgl_pengajuan, tgl_receive, tgl_pa, tgl_final,
            SLA_Date_1_LL, SLA_Date_2_HT, SLA_Date_3_YK, SLA_Date_4_AK,
            SLA_Date_5_PD, SLA_Date_6_C2, SLA_Date_7_MSIG)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (COMPANY_ID, "S002", "PAM-TEST-001", "2026-01-01", 3000000,
         "By Biaya Hidup", "Bulan 1", "open",
         "2026-01-06", "2026-01-11", "2026-01-15", None,
         "2026-01-11", "2026-01-12", "2026-01-13", None, None, None, None),
    )
    conn.commit()
    conn.close()
    return pam_id


def test_returns_rows():
    conn = get_conn()
    pam_id = _seed(conn)
    rows = get_pam_beasiswa_lines(pam_id, COMPANY_ID)
    assert rows is not None
    assert len(rows) == 2
    names = {r["nama"] for r in rows}
    assert names == {"Zara Dewi", "Andi Kurniawan"}
    amounts = {r["amount"] for r in rows}
    assert amounts == {5000000, 3000000}
    expected_keys = {
        "id", "siswa_code", "nama", "cat1", "cat2", "amount",
        "tgl_pengajuan", "tgl_receive", "tgl_pa", "tgl_final",
        "SLA_Date_1_LL", "SLA_Date_2_HT", "SLA_Date_3_YK", "SLA_Date_4_AK",
        "SLA_Date_5_PD", "SLA_Date_6_C2", "SLA_Date_7_MSIG",
    }
    for row in rows:
        assert expected_keys.issubset(row.keys())


def test_includes_sla_dates():
    conn = get_conn()
    pam_id = _seed(conn)
    rows = get_pam_beasiswa_lines(pam_id, COMPANY_ID)
    assert rows is not None
    for row in rows:
        for col in [
            "tgl_pengajuan", "tgl_receive", "tgl_pa", "tgl_final",
            "SLA_Date_1_LL", "SLA_Date_2_HT", "SLA_Date_3_YK", "SLA_Date_4_AK",
            "SLA_Date_5_PD", "SLA_Date_6_C2", "SLA_Date_7_MSIG",
        ]:
            assert col in row


def test_wrong_company_returns_none():
    conn = get_conn()
    pam_id = _seed(conn)
    result = get_pam_beasiswa_lines(pam_id, company_id=999)
    assert result is None


def test_not_found_returns_none():
    conn = get_conn()
    _seed(conn)
    result = get_pam_beasiswa_lines(pam_id=9999, company_id=COMPANY_ID)
    assert result is None


def test_empty_pam_returns_empty_list():
    conn = get_conn()
    conn.execute(
        "INSERT INTO pam_records (company_id, pam_no, source, status, created_at) VALUES (?,?,?,?,?)",
        (COMPANY_ID, "PAM-EMPTY", "etf_agri", "open", "2026-01-01"),
    )
    pam_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()
    conn.close()
    result = get_pam_beasiswa_lines(pam_id, COMPANY_ID)
    assert result == []


def test_ordered_by_nama():
    conn = get_conn()
    pam_id = _seed(conn)
    rows = get_pam_beasiswa_lines(pam_id, COMPANY_ID)
    assert rows is not None and len(rows) == 2
    assert rows[0]["nama"] == "Andi Kurniawan"
    assert rows[1]["nama"] == "Zara Dewi"


def test_returns_id_field():
    """get_pam_beasiswa_lines harus return field id untuk payload bulk-update."""
    conn = get_conn()
    pam_id = _seed(conn)
    rows = get_pam_beasiswa_lines(pam_id, COMPANY_ID)
    assert rows is not None and len(rows) > 0
    assert all("id" in r for r in rows)
    assert all(isinstance(r["id"], int) for r in rows)
