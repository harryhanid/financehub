import os, sys, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config
config.DB_PATH = os.path.join(os.path.dirname(__file__), "test_finance_hub.db")

from database import init_db, get_conn
from modules.payment_memo.service import get_siswa_medical, save_klaim_payment, save_others_payment

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


def test_save_klaim_missing_pam_no():
    result = save_klaim_payment(COMPANY_ID, "ETF", {
        "pam_no": "", "tanggal": "2026-06-17", "rows": []
    })
    assert result["ok"] is False
    assert "PAM" in result["pesan"]


def test_save_klaim_empty_rows():
    result = save_klaim_payment(COMPANY_ID, "ETF", {
        "pam_no": "PAM-001-ETF-06-2026", "tanggal": "2026-06-17", "rows": []
    })
    assert result["ok"] is False


def test_save_klaim_row_without_cat3():
    result = save_klaim_payment(COMPANY_ID, "ETF", {
        "pam_no": "PAM-001-ETF-06-2026",
        "tanggal": "2026-06-17",
        "pillar": "AGRI",
        "perusahaan": "RS Siloam",
        "rows": [{"siswa_code": "M001", "cat2": "Rawat Inap",
                  "kelas": "VIP", "rumah_sakit": "RS A", "diagnosa": "Flu",
                  "spesialisasi": "General Practitioner",
                  "cat3_items": []}]
    })
    assert result["ok"] is False


def _klaim_payload():
    return {
        "tab": "agri",
        "tanggal": "2026-06-17",
        "pam_no": "PAM-001-ETF-06-2026",
        "perusahaan": "RS Siloam",
        "keterangan": "Klaim medis Juni",
        "pillar": "AGRI",
        "rows": [
            {
                "siswa_code": "M001",
                "cat2": "Rawat Inap",
                "kelas": "VIP",
                "rumah_sakit": "RS Siloam",
                "diagnosa": "Demam Typoid",
                "spesialisasi": "General Practitioner",
                "cat3_items": [
                    {"cat3": "Kamar", "amount": 3000000, "tanggal": "2026-06-10"},
                    {"cat3": "Obat",  "amount":  500000, "tanggal": "2026-06-10"},
                ],
            }
        ],
    }


def test_save_klaim_success_creates_pam_record():
    # M001 already inserted by clean_db fixture
    result = save_klaim_payment(COMPANY_ID, "ETF", _klaim_payload())
    assert result["ok"] is True, result.get("pesan")

    conn = get_conn()
    pam = conn.execute("SELECT * FROM pam_records WHERE pam_no=?",
                       ("PAM-001-ETF-06-2026",)).fetchone()
    assert pam is not None
    assert pam["total_amount"] == 3500000
    assert pam["source"] == "klaim_medis"
    conn.close()


def test_save_klaim_success_creates_payment_beasiswa():
    save_klaim_payment(COMPANY_ID, "ETF", _klaim_payload())

    conn = get_conn()
    pb = conn.execute("SELECT * FROM payment_beasiswa WHERE siswa_code=?", ("M001",)).fetchone()
    assert pb is not None
    assert pb["cat1"] == "By Medical"
    assert pb["cat2"] == "Rawat Inap"
    assert pb["amount"] == 3500000
    assert pb["pam"] == "PAM-001-ETF-06-2026"
    conn.close()


def test_save_klaim_success_creates_klaim_medical_rows():
    save_klaim_payment(COMPANY_ID, "ETF", _klaim_payload())

    conn = get_conn()
    items = conn.execute("SELECT * FROM klaim_medical WHERE siswa_code=? ORDER BY id",
                         ("M001",)).fetchall()
    assert len(items) == 2
    assert items[0]["perawatan"] == "Kamar"
    assert items[0]["amount"] == 3000000
    assert items[1]["perawatan"] == "Obat"
    assert items[0]["kelas"] == "VIP"
    assert items[0]["rumah_sakit"] == "RS Siloam"
    conn.close()


def test_save_others_missing_pam_no():
    result = save_others_payment(COMPANY_ID, "ETF", {
        "pam_no": "", "keterangan": "test", "dpp": 1000000
    })
    assert result["ok"] is False
    assert "PAM" in result["pesan"]


def test_save_others_missing_keterangan():
    result = save_others_payment(COMPANY_ID, "ETF", {
        "pam_no": "PAM-002-ETF-06-2026", "keterangan": "", "dpp": 1000000
    })
    assert result["ok"] is False
    assert "Keterangan" in result["pesan"]


def test_save_others_zero_dpp():
    result = save_others_payment(COMPANY_ID, "ETF", {
        "pam_no": "PAM-002-ETF-06-2026", "keterangan": "Tagihan listrik", "dpp": 0
    })
    assert result["ok"] is False


def test_save_others_success_creates_pam_record():
    result = save_others_payment(COMPANY_ID, "ETF", {
        "tab": "agri",
        "pam_no": "PAM-002-ETF-06-2026",
        "tanggal": "2026-06-17",
        "perusahaan": "PT Telkom",
        "keterangan": "Tagihan internet",
        "pillar": "AGRI",
        "transaksi": "tagihan",
        "mata_uang": "IDR",
        "dpp": 5000000,
        "ppn": 550000,
    })
    assert result["ok"] is True, result.get("pesan")

    conn = get_conn()
    pam = conn.execute("SELECT * FROM pam_records WHERE pam_no=?",
                       ("PAM-002-ETF-06-2026",)).fetchone()
    assert pam is not None
    assert pam["source"] == "tagihan"
    assert pam["dpp"] == 5000000
    assert pam["ppn"] == 550000
    assert pam["total_amount"] == 5550000
    assert pam["mata_uang"] == "IDR"
    assert pam["pt"] == "PT Telkom"
    conn.close()


def test_save_others_no_payment_beasiswa():
    save_others_payment(COMPANY_ID, "ETF", {
        "pam_no": "PAM-002-ETF-06-2026",
        "tanggal": "2026-06-17",
        "keterangan": "Tagihan internet",
        "pillar": "AGRI",
        "transaksi": "tagihan",
        "mata_uang": "IDR",
        "dpp": 5000000,
        "ppn": 550000,
    })
    conn = get_conn()
    count = conn.execute("SELECT COUNT(*) FROM payment_beasiswa").fetchone()[0]
    assert count == 0
    conn.close()
