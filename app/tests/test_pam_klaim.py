import os, sys, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config
config.DB_PATH = os.path.join(os.path.dirname(__file__), "test_finance_hub.db")

from database import init_db, get_conn
from modules.payment_memo.service import get_siswa_medical

COMPANY_ID = 2

@pytest.fixture(autouse=True)
def clean_db():
    if os.path.exists(config.DB_PATH):
        os.remove(config.DB_PATH)
    init_db()
    conn = get_conn()
    conn.execute("INSERT INTO siswa (company_id,code,nama) VALUES (?,?,?)", (COMPANY_ID, "M001", "Ani Medical"))
    conn.execute("INSERT INTO siswa (company_id,code,nama) VALUES (?,?,?)", (COMPANY_ID, "M002", "Budi Edu"))
    conn.execute("INSERT INTO budget_beasiswa (company_id,siswa_code,cat1,cat2,tanggal,amount) VALUES (?,?,?,?,?,?)",
                 (COMPANY_ID, "M001", "By Medical", "Rawat Inap", "2026-01-01", 5000000))
    conn.execute("INSERT INTO budget_beasiswa (company_id,siswa_code,cat1,cat2,tanggal,amount) VALUES (?,?,?,?,?,?)",
                 (COMPANY_ID, "M002", "By Pendidikan", "Semester 1", "2026-01-01", 10000000))
    conn.commit()
    conn.close()
    yield
    if os.path.exists(config.DB_PATH):
        os.remove(config.DB_PATH)


def test_get_siswa_medical_returns_only_medical():
    rows = get_siswa_medical(COMPANY_ID)
    codes = [r["code"] for r in rows]
    assert "M001" in codes
    assert "M002" not in codes


def test_get_siswa_medical_search_filters():
    rows = get_siswa_medical(COMPANY_ID, search="Ani")
    assert len(rows) == 1
    assert rows[0]["code"] == "M001"


def test_get_siswa_medical_includes_budget_amount():
    rows = get_siswa_medical(COMPANY_ID)
    assert rows[0]["medical_budget"] == 5000000
    assert rows[0]["spent_amount"] == 0
