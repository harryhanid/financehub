# tests/test_beasiswa_service.py
import os, sys, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config
config.DB_PATH = os.path.join(os.path.dirname(__file__), "test_finance_hub.db")

from database import init_db, get_conn
from modules.beasiswa.service import (
    generate_kode_siswa, get_siswa_list, add_siswa, update_siswa,
    add_budget_batch, add_payment_batch, get_rekap, get_sisa_budget,
    add_klaim_multi, get_klaim_list, delete_klaim_row,
    add_payment_multi, get_budget_list, get_payment_list,
)

COMPANY_ID = 2  # ETF

@pytest.fixture(autouse=True)
def clean_db():
    if os.path.exists(config.DB_PATH):
        os.remove(config.DB_PATH)
    init_db()
    yield
    if os.path.exists(config.DB_PATH):
        os.remove(config.DB_PATH)

def test_generate_kode_s1_2025_first():
    kode = generate_kode_siswa("S1", 2025, COMPANY_ID)
    assert kode == "1250001"

def test_generate_kode_s2_2024():
    kode = generate_kode_siswa("S2", 2024, COMPANY_ID)
    assert kode == "2240001"

def test_generate_kode_increments():
    add_siswa(COMPANY_ID, {"code": "1250001", "nama": "Andi", "jenjang": "S1",
        "angkatan": 2025, "program": "SMART", "fakultas": "", "universitas": "",
        "bank": "", "norek": "", "namarek": "", "referensi": "",
        "status": "Aktif", "catatan": ""})
    kode = generate_kode_siswa("S1", 2025, COMPANY_ID)
    assert kode == "1250002"

def test_add_siswa_success():
    result = add_siswa(COMPANY_ID, {
        "code": "1250001", "nama": "Budi Santoso", "jenjang": "S1",
        "angkatan": 2025, "program": "SMART", "fakultas": "Teknik",
        "universitas": "UI", "bank": "BCA", "norek": "1234567890",
        "namarek": "Budi Santoso", "referensi": "AGRI",
        "status": "Aktif", "catatan": "Test"
    })
    assert result["ok"] is True

def test_add_siswa_duplicate_code():
    data = {"code": "1250001", "nama": "X", "jenjang": "S1", "angkatan": 2025,
            "program": "SMART", "fakultas": "", "universitas": "", "bank": "",
            "norek": "", "namarek": "", "referensi": "", "status": "Aktif", "catatan": ""}
    add_siswa(COMPANY_ID, data)
    result = add_siswa(COMPANY_ID, data)
    assert result["ok"] is False
    assert "sudah ada" in result["pesan"]

def test_get_siswa_list_returns_all():
    add_siswa(COMPANY_ID, {"code": "1250001", "nama": "A", "jenjang": "S1",
        "angkatan": 2025, "program": "SMART", "fakultas": "", "universitas": "",
        "bank": "", "norek": "", "namarek": "", "referensi": "",
        "status": "Aktif", "catatan": ""})
    rows = get_siswa_list(COMPANY_ID)
    assert len(rows) == 1
    assert rows[0]["nama"] == "A"

def test_get_siswa_list_isolated_by_company():
    add_siswa(COMPANY_ID, {"code": "1250001", "nama": "ETF Siswa", "jenjang": "S1",
        "angkatan": 2025, "program": "SMART", "fakultas": "", "universitas": "",
        "bank": "", "norek": "", "namarek": "", "referensi": "",
        "status": "Aktif", "catatan": ""})
    rows = get_siswa_list(1)  # SMT
    assert len(rows) == 0

def test_add_budget_batch():
    add_siswa(COMPANY_ID, {"code": "1250001", "nama": "A", "jenjang": "S1",
        "angkatan": 2025, "program": "SMART", "fakultas": "", "universitas": "",
        "bank": "", "norek": "", "namarek": "", "referensi": "",
        "status": "Aktif", "catatan": ""})
    result = add_budget_batch(COMPANY_ID, "1250001", "2025-01-15", "AGRI", [
        {"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 5000000},
        {"cat1": "By Tunjangan",  "cat2": "Semester 1", "amount": 2000000},
    ])
    assert result["ok"] is True
    assert result["saved"] == 2

def test_add_budget_batch_skips_zero_amount():
    add_siswa(COMPANY_ID, {"code": "1250001", "nama": "A", "jenjang": "S1",
        "angkatan": 2025, "program": "SMART", "fakultas": "", "universitas": "",
        "bank": "", "norek": "", "namarek": "", "referensi": "",
        "status": "Aktif", "catatan": ""})
    result = add_budget_batch(COMPANY_ID, "1250001", "2025-01-15", "AGRI", [
        {"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 0},
    ])
    assert result["saved"] == 0

def test_add_payment_batch_creates_draft():
    add_siswa(COMPANY_ID, {"code": "1250001", "nama": "A", "jenjang": "S1",
        "angkatan": 2025, "program": "SMART", "fakultas": "", "universitas": "",
        "bank": "", "norek": "", "namarek": "", "referensi": "",
        "status": "Aktif", "catatan": ""})
    result = add_payment_batch(COMPANY_ID, "1250001", "2025-06-01", "AGRI",
        "PT. SMART Tbk", [
            {"cat1": "By Pendidikan", "cat2": "Semester 2", "cat3": "", "cat4": "", "amount": 5000000},
        ])
    assert result["ok"] is True
    conn = get_conn()
    row = conn.execute(
        "SELECT status FROM payment_beasiswa WHERE company_id=? AND siswa_code=?",
        (COMPANY_ID, "1250001")
    ).fetchone()
    conn.close()
    assert row["status"] == "draft"

def test_get_rekap_empty():
    rows = get_rekap(COMPANY_ID)
    assert rows == []

def test_get_sisa_budget():
    add_siswa(COMPANY_ID, {"code": "1250001", "nama": "A", "jenjang": "S1",
        "angkatan": 2025, "program": "SMART", "fakultas": "", "universitas": "",
        "bank": "", "norek": "", "namarek": "", "referensi": "",
        "status": "Aktif", "catatan": ""})
    add_budget_batch(COMPANY_ID, "1250001", "2025-01-15", "AGRI", [
        {"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 10000000},
    ])
    add_payment_batch(COMPANY_ID, "1250001", "2025-06-01", "AGRI", "PT. SMART Tbk", [
        {"cat1": "By Pendidikan", "cat2": "Semester 1", "cat3": "", "cat4": "", "amount": 4000000},
    ])
    sisa = get_sisa_budget(COMPANY_ID, "1250001")
    assert sisa["total_budget"]  == 10000000
    assert sisa["total_payment"] == 4000000
    assert sisa["total_sisa"]    == 6000000


# ── Klaim Medical ──────────────────────────────────────────────────────────────

def _add_siswa_a():
    add_siswa(COMPANY_ID, {"code": "1250001", "nama": "Andi", "jenjang": "S1",
        "angkatan": 2025, "program": "SMART", "fakultas": "", "universitas": "",
        "bank": "", "norek": "", "namarek": "", "referensi": "",
        "status": "Aktif", "catatan": ""})

def test_add_klaim_multi_saves_klaim_and_payment():
    _add_siswa_a()
    result = add_klaim_multi(COMPANY_ID, "PAM-001", "AGRI", "PT. SMART Tbk", [
        {"siswa_code": "1250001", "tanggal": "2026-01-15", "amount": 3000000,
         "perawatan": "Rawat Jalan", "kelas": "", "rumah_sakit": "RS ABC",
         "diagnosa": "Flu", "spesialisasi": "Umum"},
    ])
    assert result["ok"] is True
    assert result["saved"] == 1
    conn = get_conn()
    km = conn.execute("SELECT * FROM klaim_medical WHERE company_id=?", (COMPANY_ID,)).fetchone()
    assert km is not None
    assert km["siswa_code"] == "1250001"
    assert km["perawatan"] == "Rawat Jalan"
    assert km["rumah_sakit"] == "RS ABC"
    assert km["payment_id"] is not None
    pay = conn.execute("SELECT * FROM payment_beasiswa WHERE id=?", (km["payment_id"],)).fetchone()
    assert pay["cat1"] == "By Medical"
    assert pay["cat2"] == "Rawat Jalan"
    assert pay["amount"] == 3000000
    assert pay["status"] == "draft"
    conn.close()

def test_add_klaim_multi_skips_zero_amount():
    _add_siswa_a()
    result = add_klaim_multi(COMPANY_ID, "PAM-001", "AGRI", "PT. SMART Tbk", [
        {"siswa_code": "1250001", "tanggal": "2026-01-15", "amount": 0,
         "perawatan": "Rawat Inap", "kelas": "", "rumah_sakit": "", "diagnosa": "", "spesialisasi": ""},
    ])
    assert result["ok"] is False
    assert result["saved"] == 0

def test_add_klaim_multi_skips_empty_siswa():
    _add_siswa_a()
    result = add_klaim_multi(COMPANY_ID, "PAM-001", "AGRI", "PT. SMART Tbk", [
        {"siswa_code": "", "tanggal": "2026-01-15", "amount": 1000000,
         "perawatan": "Rawat Jalan", "kelas": "", "rumah_sakit": "", "diagnosa": "", "spesialisasi": ""},
    ])
    assert result["ok"] is False
    assert result["saved"] == 0

def test_get_klaim_list_returns_rows():
    _add_siswa_a()
    add_klaim_multi(COMPANY_ID, "PAM-001", "AGRI", "PT. SMART Tbk", [
        {"siswa_code": "1250001", "tanggal": "2026-01-15", "amount": 2500000,
         "perawatan": "Rawat Inap", "kelas": "Kelas 1", "rumah_sakit": "RS XYZ",
         "diagnosa": "Demam", "spesialisasi": "Penyakit Dalam"},
    ])
    data = get_klaim_list(COMPANY_ID)
    assert data["total"] == 1
    assert data["grand"] == 2500000
    assert data["rows"][0]["rumah_sakit"] == "RS XYZ"
    assert data["rows"][0]["nama"] == "Andi"

def test_get_klaim_list_filter_perawatan():
    _add_siswa_a()
    add_klaim_multi(COMPANY_ID, "PAM-001", "AGRI", "PT. SMART Tbk", [
        {"siswa_code": "1250001", "tanggal": "2026-01-15", "amount": 1000000,
         "perawatan": "Rawat Jalan", "kelas": "", "rumah_sakit": "", "diagnosa": "", "spesialisasi": ""},
        {"siswa_code": "1250001", "tanggal": "2026-02-10", "amount": 5000000,
         "perawatan": "Rawat Inap", "kelas": "", "rumah_sakit": "", "diagnosa": "", "spesialisasi": ""},
    ])
    data = get_klaim_list(COMPANY_ID, perawatan="Rawat Inap")
    assert data["total"] == 1
    assert data["grand"] == 5000000

def test_delete_klaim_row_removes_klaim_and_payment():
    _add_siswa_a()
    add_klaim_multi(COMPANY_ID, "PAM-001", "AGRI", "PT. SMART Tbk", [
        {"siswa_code": "1250001", "tanggal": "2026-01-15", "amount": 1500000,
         "perawatan": "Rawat Jalan", "kelas": "", "rumah_sakit": "", "diagnosa": "", "spesialisasi": ""},
    ])
    conn = get_conn()
    km = conn.execute("SELECT id, payment_id FROM klaim_medical WHERE company_id=?", (COMPANY_ID,)).fetchone()
    conn.close()
    result = delete_klaim_row(COMPANY_ID, km["id"])
    assert result["ok"] is True
    conn = get_conn()
    assert conn.execute("SELECT id FROM klaim_medical WHERE id=?", (km["id"],)).fetchone() is None
    assert conn.execute("SELECT id FROM payment_beasiswa WHERE id=?", (km["payment_id"],)).fetchone() is None
    conn.close()

def test_delete_klaim_row_not_found():
    result = delete_klaim_row(COMPANY_ID, 99999)
    assert result["ok"] is False


def test_add_payment_multi_creates_pam_record():
    # Seed two siswa
    add_siswa(COMPANY_ID, {
        "code": "1250001", "nama": "Harry Santoso", "jenjang": "S1",
        "angkatan": 2025, "program": "SMART", "fakultas": "Teknik",
        "universitas": "UI", "bank": "BCA", "norek": "111", "namarek": "Harry",
        "referensi": "", "status": "Aktif", "catatan": "",
    })
    add_siswa(COMPANY_ID, {
        "code": "1250002", "nama": "Joni Pratama", "jenjang": "S1",
        "angkatan": 2025, "program": "SMART", "fakultas": "Ekonomi",
        "universitas": "UGM", "bank": "BNI", "norek": "222", "namarek": "Joni",
        "referensi": "", "status": "Aktif", "catatan": "",
    })

    rows = [
        {"siswa_code": "1250001", "cat1": "By Pendidikan", "cat2": "Semester 1",
         "amount": "3000000", "cat3": "", "cat4": "",
         "tgl_pengajuan": "", "tgl_receive": "", "tgl_pa": "", "tgl_final": ""},
        {"siswa_code": "1250002", "cat1": "By Pendidikan", "cat2": "Semester 1",
         "amount": "3500000", "cat3": "", "cat4": "",
         "tgl_pengajuan": "", "tgl_receive": "", "tgl_pa": "", "tgl_final": ""},
    ]

    result = add_payment_multi(
        company_id=COMPANY_ID,
        company_code="ETF",
        tanggal="2026-05-31",
        pillar="AGRI",
        perusahaan="PT. SMART Tbk",
        rows=rows,
    )

    assert result["ok"] is True
    assert result["saved"] == 2
    assert "pam_no" in result
    assert result["pam_no"].startswith("PAM-") and "ETF" in result["pam_no"]

    conn = get_conn()
    pam = conn.execute(
        "SELECT * FROM pam_records WHERE pam_no=?", (result["pam_no"],)
    ).fetchone()
    assert pam is not None
    assert pam["gl_account"]  == "70110230"
    assert pam["cost_center"] == "1008C1POFF"
    assert "Harry" in pam["keterangan"]
    assert "Joni"  in pam["keterangan"]
    assert pam["total_amount"] == 6500000.0
    assert pam["due_date"]     == "2026-06-30"

    # payment_beasiswa rows must have pam set
    pb_rows = conn.execute(
        "SELECT pam FROM payment_beasiswa WHERE company_id=?", (COMPANY_ID,)
    ).fetchall()
    conn.close()
    for pb in pb_rows:
        assert pb["pam"] == result["pam_no"]


def test_add_payment_multi_zero_rows_no_pam():
    rows = [
        {"siswa_code": "X001", "cat1": "By Pendidikan", "cat2": "Semester 1",
         "amount": "0", "cat3": "", "cat4": "",
         "tgl_pengajuan": "", "tgl_receive": "", "tgl_pa": "", "tgl_final": ""},
    ]
    result = add_payment_multi(
        company_id=COMPANY_ID, company_code="ETF",
        tanggal="2026-05-31", pillar="AGRI",
        perusahaan="PT. SMART Tbk", rows=rows,
    )
    assert result["ok"] is False
    conn = get_conn()
    count = conn.execute("SELECT COUNT(*) FROM pam_records").fetchone()[0]
    conn.close()
    assert count == 0   # No PAM created when no valid rows


# ── get_budget_list cross-tab payment_totals ───────────────────────────────────

def _seed_budi():
    """Helper: adds siswa Budi with budget + payment rows."""
    add_siswa(COMPANY_ID, {
        "code": "1250001", "nama": "Budi Santoso", "jenjang": "S1",
        "angkatan": 2025, "program": "SMART", "fakultas": "", "universitas": "",
        "bank": "", "norek": "", "namarek": "", "referensi": "",
        "status": "Aktif", "catatan": "",
    })
    add_budget_batch(COMPANY_ID, "1250001", "2025-03-10", "AGRI", [
        {"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 8000000},
        {"cat1": "By Tunjangan",  "cat2": "Bulanan",    "amount": 2000000},
    ])
    add_payment_batch(COMPANY_ID, "1250001", "2025-03-15", "AGRI", "PT. SMART Tbk", [
        {"cat1": "By Pendidikan", "cat2": "Semester 1", "cat3": "", "cat4": "", "amount": 5000000},
    ])


def test_get_budget_list_returns_payment_totals():
    _seed_budi()
    result = get_budget_list(COMPANY_ID)
    assert "payment_totals" in result
    assert result["payment_totals"].get("By Pendidikan") == 5000000
    assert result["payment_grand"] == 5000000


def test_get_budget_list_payment_totals_filtered_by_search():
    _seed_budi()
    # Add another siswa with payment that should NOT appear
    add_siswa(COMPANY_ID, {
        "code": "1250002", "nama": "Rina Wati", "jenjang": "S1",
        "angkatan": 2025, "program": "SMART", "fakultas": "", "universitas": "",
        "bank": "", "norek": "", "namarek": "", "referensi": "",
        "status": "Aktif", "catatan": "",
    })
    add_payment_batch(COMPANY_ID, "1250002", "2025-03-20", "AGRI", "PT. SMART Tbk", [
        {"cat1": "By Pendidikan", "cat2": "Semester 1", "cat3": "", "cat4": "", "amount": 3000000},
    ])
    # Filter by Budi's name only
    result = get_budget_list(COMPANY_ID, search="Budi")
    assert result["payment_totals"].get("By Pendidikan") == 5000000
    assert result["payment_grand"] == 5000000
