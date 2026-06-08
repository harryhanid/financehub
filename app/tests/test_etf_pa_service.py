# tests/test_etf_pa_service.py
import os, sys, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config
config.DB_PATH = os.path.join(os.path.dirname(__file__), "test_etf_pa.db")

from database import init_db, get_conn
from modules.etf_payment_application.service import (
    get_pa_list, create_pa, update_pa, get_pa_lines,
    get_siswa_autocomplete,
)

COMPANY_ID = 2  # ETF

@pytest.fixture(autouse=True)
def clean_db():
    if os.path.exists(config.DB_PATH):
        os.remove(config.DB_PATH)
    init_db()
    _seed()
    yield
    if os.path.exists(config.DB_PATH):
        os.remove(config.DB_PATH)


def _seed():
    conn = get_conn()
    conn.execute(
        """INSERT INTO siswa (company_id, code, nama, jenjang, angkatan,
           program, fakultas, universitas, status,
           ipk_sem1, ipk_sem2)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (COMPANY_ID, "1230001", "Budi Santoso", "S1", 2023,
         "SMART", "Teknik", "Univ. Indonesia", "Aktif", 3.5, 3.6)
    )
    conn.execute(
        """INSERT INTO siswa (company_id, code, nama, jenjang, angkatan,
           program, fakultas, universitas, status,
           ipk_sem1)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (COMPANY_ID, "2230001", "Ani Wijaya", "S2", 2023,
         "Polri", "Hukum", "Univ. Gajah Mada", "Aktif", 3.8)
    )
    conn.commit()
    conn.close()


def _student_id(code: str) -> int:
    conn = get_conn()
    row = conn.execute("SELECT id FROM siswa WHERE code=?", (code,)).fetchone()
    conn.close()
    return row["id"]


# --- create_pa ---

def test_create_pa_success():
    sid = _student_id("1230001")
    result = create_pa(COMPANY_ID, {
        "tgl_payment_application": "2026-06-01",
        "tgl_surat_pengajuan": "2026-06-01",
        "keterangan": "Test PA",
    }, [
        {"student_id": sid, "jenis_pembayaran": "By Pendidikan",
         "semester": "Semester 3", "tahun_ajaran": "2025/2026",
         "ipk_sem_sebelumnya": 3.6, "jumlah_pembayaran": 5000000}
    ])
    assert result["ok"] is True
    assert result["pa_number"].startswith("PA/ETF/001/")


def test_create_pa_no_lines_fails():
    result = create_pa(COMPANY_ID, {"tgl_payment_application": "2026-06-01"}, [])
    assert result["ok"] is False
    assert "Minimal" in result["pesan"]


def test_create_pa_invalid_student_fails():
    result = create_pa(COMPANY_ID, {"tgl_payment_application": "2026-06-01"}, [
        {"student_id": 9999, "jenis_pembayaran": "By Pendidikan",
         "semester": "Semester 1", "tahun_ajaran": "2024/2025",
         "ipk_sem_sebelumnya": 3.5, "jumlah_pembayaran": 1000000}
    ])
    assert result["ok"] is False


def test_create_pa_multi_lines():
    s1 = _student_id("1230001")
    s2 = _student_id("2230001")
    result = create_pa(COMPANY_ID, {"tgl_payment_application": "2026-06-01"}, [
        {"student_id": s1, "jenis_pembayaran": "By Pendidikan",
         "semester": "Semester 3", "tahun_ajaran": "2025/2026",
         "ipk_sem_sebelumnya": 3.6, "jumlah_pembayaran": 5000000},
        {"student_id": s2, "jenis_pembayaran": "By Tunjangan",
         "semester": "Semester 1", "tahun_ajaran": "2025/2026",
         "ipk_sem_sebelumnya": 3.8, "jumlah_pembayaran": 2000000},
    ])
    assert result["ok"] is True
    lines = get_pa_lines(result["pa_id"], COMPANY_ID)
    assert len(lines) == 2


def test_pa_number_increments():
    sid = _student_id("1230001")
    line = [{"student_id": sid, "jenis_pembayaran": "By Pendidikan",
             "semester": "Semester 1", "tahun_ajaran": "2024/2025",
             "ipk_sem_sebelumnya": 3.5, "jumlah_pembayaran": 1000000}]
    r1 = create_pa(COMPANY_ID, {"tgl_payment_application": "2026-06-01"}, line)
    r2 = create_pa(COMPANY_ID, {"tgl_payment_application": "2026-06-02"}, line)
    assert r1["pa_number"].endswith("/001/2026")
    assert r2["pa_number"].endswith("/002/2026")


# --- get_pa_list ---

def test_get_pa_list_aggregates():
    s1 = _student_id("1230001")
    s2 = _student_id("2230001")
    create_pa(COMPANY_ID, {"tgl_payment_application": "2026-06-01"}, [
        {"student_id": s1, "jenis_pembayaran": "By Pendidikan",
         "semester": "Semester 3", "tahun_ajaran": "2025/2026",
         "ipk_sem_sebelumnya": 3.6, "jumlah_pembayaran": 5000000},
        {"student_id": s2, "jenis_pembayaran": "By Tunjangan",
         "semester": "Semester 1", "tahun_ajaran": "2025/2026",
         "ipk_sem_sebelumnya": 3.8, "jumlah_pembayaran": 2000000},
    ])
    rows = get_pa_list(COMPANY_ID)
    assert len(rows) == 1
    assert rows[0]["jml_siswa"] == 2
    assert rows[0]["total_bayar"] == 7000000


# --- update_pa ---

def test_update_pa_status_on_process_generates_pam():
    sid = _student_id("1230001")
    r = create_pa(COMPANY_ID, {"tgl_payment_application": "2026-06-01"}, [
        {"student_id": sid, "jenis_pembayaran": "By Pendidikan",
         "semester": "Semester 3", "tahun_ajaran": "2025/2026",
         "ipk_sem_sebelumnya": 3.6, "jumlah_pembayaran": 5000000}
    ])
    upd = update_pa(r["pa_id"], COMPANY_ID, {
        "status": "on_process",
        "tgl_payment_application": "2026-06-01",
    })
    assert upd["ok"] is True
    assert upd["nomor_pam"] is not None
    assert "ETF" in upd["nomor_pam"]


def test_update_pa_status_complete():
    sid = _student_id("1230001")
    r = create_pa(COMPANY_ID, {"tgl_payment_application": "2026-06-01"}, [
        {"student_id": sid, "jenis_pembayaran": "By Pendidikan",
         "semester": "Semester 3", "tahun_ajaran": "2025/2026",
         "ipk_sem_sebelumnya": 3.6, "jumlah_pembayaran": 5000000}
    ])
    update_pa(r["pa_id"], COMPANY_ID, {"status": "on_process", "tgl_payment_application": "2026-06-01"})
    upd2 = update_pa(r["pa_id"], COMPANY_ID, {
        "status": "complete",
        "tanggal_bayar": "2026-06-15",
        "tgl_payment_application": "2026-06-01",
    })
    assert upd2["ok"] is True
    rows = get_pa_list(COMPANY_ID)
    assert rows[0]["status"] == "complete"


def test_update_pa_not_found():
    upd = update_pa(9999, COMPANY_ID, {"status": "on_process"})
    assert upd["ok"] is False


# --- get_siswa_autocomplete ---

def test_get_siswa_autocomplete():
    results = get_siswa_autocomplete(COMPANY_ID, "Budi")
    assert len(results) == 1
    assert results[0]["nama"] == "Budi Santoso"
    assert results[0]["ipk_terakhir"] == 3.6


def test_get_siswa_autocomplete_empty():
    results = get_siswa_autocomplete(COMPANY_ID, "ZZZ_tidak_ada")
    assert results == []


from modules.etf_payment_application.service import (
    get_draft_siswa, get_draft_lines_for_siswa,
)


def _make_pa(conn, company_id: int, siswa_id: int, status: str) -> tuple:
    """Insert one etf_pa + one line. Returns (pa_id, line_id)."""
    from datetime import datetime
    ts = datetime.now().isoformat(timespec="seconds")
    cur = conn.execute(
        """INSERT INTO etf_pa
           (company_id, pa_number, tgl_payment_application, status, created_at)
           VALUES (?,?,?,?,?)""",
        (company_id, f"PA/ETF/{status[:2].upper()}/001/2026", "2026-06-01", status, ts)
    )
    pa_id = cur.lastrowid
    cur2 = conn.execute(
        """INSERT INTO etf_pa_lines
           (pa_id, student_id, jenis_pembayaran, jumlah_pembayaran)
           VALUES (?,?,?,?)""",
        (pa_id, siswa_id, "By Pendidikan", 5000000)
    )
    conn.commit()
    return pa_id, cur2.lastrowid


def test_get_draft_siswa_open_only():
    """Only 'open' PA records must appear in student search."""
    conn = get_conn()
    sid = _student_id("1230001")
    _make_pa(conn, COMPANY_ID, sid, "open")
    conn.close()
    results = get_draft_siswa(COMPANY_ID, "Budi")
    assert len(results) == 1
    assert results[0]["code"] == "1230001"


def test_get_draft_siswa_excludes_draft():
    """'draft' PA records must NOT appear — only 'open' is valid."""
    conn = get_conn()
    sid = _student_id("1230001")
    _make_pa(conn, COMPANY_ID, sid, "draft")
    conn.close()
    results = get_draft_siswa(COMPANY_ID, "Budi")
    assert results == [], "draft PA should be excluded from student search"


def test_get_draft_siswa_excludes_on_process():
    conn = get_conn()
    sid = _student_id("1230001")
    _make_pa(conn, COMPANY_ID, sid, "on_process")
    conn.close()
    results = get_draft_siswa(COMPANY_ID, "Budi")
    assert results == []


def test_get_draft_lines_open_only():
    conn = get_conn()
    sid = _student_id("1230001")
    pa_id, line_id = _make_pa(conn, COMPANY_ID, sid, "open")
    conn.close()
    lines = get_draft_lines_for_siswa(COMPANY_ID, sid)
    assert len(lines) == 1
    assert lines[0]["line_id"] == line_id


def test_get_draft_lines_excludes_draft():
    conn = get_conn()
    sid = _student_id("1230001")
    _make_pa(conn, COMPANY_ID, sid, "draft")
    conn.close()
    lines = get_draft_lines_for_siswa(COMPANY_ID, sid)
    assert lines == [], "draft PA lines should be excluded"
