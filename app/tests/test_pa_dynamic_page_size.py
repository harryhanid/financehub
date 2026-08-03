from database import get_conn
from modules.etf_payment_application.service import create_pa

COMPANY_ID = 2  # ETF


def login(client, username="admin", password="Admin@123"):
    return client.post("/auth/login", json={"username": username, "password": password})


def _select_etf(client):
    client.post("/select-company", data={"company_id": "2"})


def _seed_students_and_pas(n):
    conn = get_conn()
    ids = []
    for i in range(n):
        conn.execute(
            "INSERT INTO siswa (company_id, code, nama, jenjang, angkatan, "
            "program, fakultas, universitas, status, ipk_sem1) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (COMPANY_ID, f"900000{i}", f"Siswa {i}", "S1", 2023,
             "SMART", "Teknik", "Univ. Test", "Aktif", 3.5)
        )
        conn.commit()
        row = conn.execute("SELECT id FROM siswa WHERE code=?", (f"900000{i}",)).fetchone()
        ids.append(row["id"])
    conn.close()
    for i, sid in enumerate(ids):
        result = create_pa(COMPANY_ID, {
            "tgl_payment_application": "2026-06-01",
            "tgl_surat_pengajuan": "2026-06-01",
            "keterangan": f"Test PA {i}",
        }, [
            {"student_id": sid, "jenis_pembayaran": "By Pendidikan",
             "semester": "Semester 3", "tahun_ajaran": "2025/2026",
             "ipk_sem_sebelumnya": 3.6, "jumlah_pembayaran": 5000000}
        ], tab="agri")
        assert result["ok"] is True, result


def test_page_size_query_param_controls_slicing(client):
    login(client)
    _select_etf(client)
    _seed_students_and_pas(3)
    resp = client.get("/etf-payment-application/?tab=agri&page_size=2")
    assert resp.status_code == 200
    assert b"halaman 1/2" in resp.data


def test_page_size_defaults_when_absent(client):
    login(client)
    _select_etf(client)
    _seed_students_and_pas(3)
    resp = client.get("/etf-payment-application/?tab=agri")
    assert resp.status_code == 200
    assert b"halaman" not in resp.data  # 3 rows < default 50, pagination hidden


def test_page_size_ignores_invalid_values(client):
    login(client)
    _select_etf(client)
    _seed_students_and_pas(3)
    resp = client.get("/etf-payment-application/?tab=agri&page_size=abc")
    assert resp.status_code == 200
    assert b"halaman" not in resp.data


def test_page_size_clamped_to_max(client):
    login(client)
    _select_etf(client)
    _seed_students_and_pas(3)
    resp = client.get("/etf-payment-application/?tab=agri&page_size=99999")
    assert resp.status_code == 200
    assert b"halaman" not in resp.data
