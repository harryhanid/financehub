# tests/test_beasiswa_service.py
import os, sys, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config
config.DB_PATH = os.path.join(os.path.dirname(__file__), "test_finance_hub.db")

from database import init_db, get_conn
from modules.beasiswa.service import (
    generate_kode_siswa, get_siswa_list, add_siswa, update_siswa,
    add_budget_batch, add_payment_batch, get_rekap, get_sisa_budget
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
