def login(client, username="admin", password="Admin@123"):
    return client.post("/auth/login", json={"username": username, "password": password})


def _select_smt(client):
    client.post("/select-company", data={"company_id": "1"})


def _select_etf(client):
    client.post("/select-company", data={"company_id": "2"})

def _seed_siswa_with_long_fields(company_id: int = 2, code: str = "1250099") -> None:
    """Seed one siswa with deliberately long text fields plus one budget row
    with a long category name, so the Laporan Siswa PDF's Data Siswa, IPK, and
    Rekapitulasi per Kategori tables all have long text to wrap."""
    from database import get_conn
    conn = get_conn()
    conn.execute(
        """INSERT INTO siswa
           (company_id, code, nama, jenjang, angkatan, program,
            fakultas, universitas, bank, norek, namarek, referensi,
            catatan, ipk_sem1, status)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (company_id, code, "Siswa Uji Panjang", "S1", 2025, "SMART",
         "Fakultas Teknik Informatika dan Ilmu Komputer Terapan",
         "Universitas Pembangunan Nasional Veteran Jakarta Kampus Utama",
         "Bank Sinarmas", "1234567890",
         "Siswa Uji Panjang Dengan Nama Rekening Yang Sangat Panjang Sekali",
         "Ref-001",
         "Catatan ini ditulis sangat panjang untuk memastikan tabel Data Siswa "
         "benar-benar mem-wrap teks dan tidak menembus kolom di sebelahnya "
         "seperti yang dilaporkan pengguna.",
         3.75, "Aktif")
    )
    conn.execute(
        """INSERT INTO budget_beasiswa
           (company_id, siswa_code, cat1, cat2, tanggal, amount, pillar)
           VALUES (?,?,?,?,?,?,?)""",
        (company_id, code,
         "Kategori Budget Dengan Nama Yang Sangat Panjang Sekali Untuk Uji Wrap",
         "By Pendaftaran", "2026-01-01", 5000000, "AGRI")
    )
    conn.commit()
    conn.close()

def test_laporan_export_pdf_with_long_text_fields_renders_ok(client):
    _seed_siswa_with_long_fields()
    login(client)
    _select_etf(client)
    resp = client.get("/beasiswa/laporan/siswa/1250099/export/pdf")
    assert resp.status_code == 200
    assert resp.data[:4] == b"%PDF"


def test_index_renders_for_etf(client):
    login(client)
    _select_etf(client)
    resp = client.get("/beasiswa/")
    assert resp.status_code == 200
    assert b"Beasiswa" in resp.data
    assert b"Ganti Company" not in resp.data


def test_index_shows_wrong_company_notice_for_smt(client):
    login(client)
    _select_smt(client)
    resp = client.get("/beasiswa/")
    assert resp.status_code == 200
    assert b"Ganti Company" in resp.data


def test_siswa_generate_kode_rejects_non_etf(client):
    login(client)
    _select_smt(client)
    resp = client.get("/beasiswa/siswa/generate-kode?jenjang=S1&angkatan=2026")
    assert resp.status_code == 403


def test_siswa_tambah_rejects_non_etf(client):
    login(client)
    _select_smt(client)
    resp = client.post("/beasiswa/siswa/tambah", json={})
    assert resp.status_code == 403


def test_siswa_detail_rejects_non_etf(client):
    login(client)
    _select_smt(client)
    resp = client.get("/beasiswa/siswa/S001")
    assert resp.status_code == 403


def test_budget_tambah_rejects_non_etf(client):
    login(client)
    _select_smt(client)
    resp = client.post("/beasiswa/budget/tambah", json={"code": "S001"})
    assert resp.status_code == 403


def test_payment_tambah_rejects_non_etf(client):
    login(client)
    _select_smt(client)
    resp = client.post("/beasiswa/payment/tambah", json={"code": "S001"})
    assert resp.status_code == 403


def test_klaim_tambah_multi_rejects_non_etf(client):
    login(client)
    _select_smt(client)
    resp = client.post("/beasiswa/klaim/tambah-multi", json={"rows": [{}]})
    assert resp.status_code == 403


def test_financial_summary_rejects_non_etf(client):
    login(client)
    _select_smt(client)
    resp = client.get("/beasiswa/summary")
    assert resp.status_code == 403


def test_budget_export_csv_rejects_non_etf(client):
    login(client)
    _select_smt(client)
    resp = client.get("/beasiswa/budget/export/csv")
    assert resp.status_code == 403


def test_rekap_data_rejects_non_etf(client):
    login(client)
    _select_smt(client)
    resp = client.get("/beasiswa/rekap/data")
    assert resp.status_code == 403


def test_api_dashboard_summary_rejects_non_etf(client):
    login(client)
    _select_smt(client)
    resp = client.get("/beasiswa/api/dashboard/summary")
    assert resp.status_code == 403


def test_financial_summary_ok_for_etf(client):
    login(client)
    _select_etf(client)
    resp = client.get("/beasiswa/summary")
    assert resp.status_code == 200
    assert resp.get_json()["ok"] is True


def test_vendor_list_api_not_gated_by_company(client):
    # `vendors` is a global lookup table, not scoped by company_id — it is
    # intentionally excluded from the ETF-only guard (see etf_company_required
    # docstring in modules/beasiswa/routes.py).
    login(client)
    _select_smt(client)
    resp = client.get("/beasiswa/vendors")
    assert resp.status_code == 200


def test_budget_export_pdf_returns_pdf(client):
    from tests.test_beasiswa_routes import login, _select_etf
    login(client)
    _select_etf(client)
    resp = client.get("/beasiswa/budget/export/pdf")
    assert resp.status_code == 200
    assert resp.data[:4] == b"%PDF"


def test_payment_export_pdf_returns_pdf(client):
    from tests.test_beasiswa_routes import login, _select_etf
    login(client)
    _select_etf(client)
    resp = client.get("/beasiswa/payment/export/pdf")
    assert resp.status_code == 200
    assert resp.data[:4] == b"%PDF"


def test_rekap_export_pdf_returns_pdf(client):
    from tests.test_beasiswa_routes import login, _select_etf
    login(client)
    _select_etf(client)
    resp = client.get("/beasiswa/rekap/export/pdf")
    assert resp.status_code == 200
    assert resp.data[:4] == b"%PDF"


def test_budget_siswa_export_pdf_does_not_crash(client):
    from tests.test_beasiswa_routes import login, _select_etf
    login(client)
    _select_etf(client)
    resp = client.get("/beasiswa/budget/siswa/NOTFOUND/export/pdf")
    assert resp.status_code in (200, 404)
    if resp.status_code == 200:
        assert resp.data[:4] == b"%PDF"


def test_laporan_export_pdf_does_not_crash(client):
    from tests.test_beasiswa_routes import login, _select_etf
    login(client)
    _select_etf(client)
    resp = client.get("/beasiswa/laporan/siswa/NOTFOUND/export/pdf")
    assert resp.status_code in (200, 404)
    if resp.status_code == 200:
        assert resp.data[:4] == b"%PDF"


def test_dashboard_tab_still_has_filter_chips_after_refactor(client):
    login(client)
    _select_etf(client)
    resp = client.get("/beasiswa/")
    assert resp.status_code == 200
    assert resp.data.count(b"beasiswa-dash-filter-chip") >= 4  # Tahun/Pillar/Program/Jenjang


def test_sahabat_etf_filters_use_chip_pattern(client):
    login(client)
    _select_etf(client)
    resp = client.get("/beasiswa/")
    assert resp.status_code == 200
    html = resp.data.decode()
    # The Sahabat ETF year/pillar filters should now render as chips...
    setf_section_start = html.index('id="tab-sahabat"')
    setf_section = html[setf_section_start:setf_section_start + 4000]
    assert "beasiswa-dash-filter-chip" in setf_section
    # ...and the old standalone "Pilih Semua" button should be gone.
    assert "setf-year-select-all" not in html


def test_setf_family_table_and_chart_ids_appear_exactly_once(client):
    login(client)
    _select_etf(client)
    resp = client.get("/beasiswa/")
    assert resp.status_code == 200
    html = resp.data.decode()
    assert html.count('id="setf-family-table"') == 1
    assert html.count('id="chart-keluarga"') == 1
    # The other Detail Tabel table must still be present.
    assert 'id="setf-table"' in html


def test_dashboard_api_summary_parses_statuses_csv(client):
    from unittest.mock import patch
    from tests.test_beasiswa_routes import login, _select_etf
    login(client)
    _select_etf(client)
    with patch("modules.beasiswa.routes.get_dashboard_summary") as mock_func:
        mock_func.return_value = []
        resp = client.get("/beasiswa/api/dashboard/summary?statuses=open,complete")
        assert resp.status_code == 200
        assert mock_func.call_count == 1
        assert mock_func.call_args[0][5] == ["open", "complete"]

def test_dashboard_api_breakdown_parses_statuses_csv(client):
    from unittest.mock import patch
    from tests.test_beasiswa_routes import login, _select_etf
    login(client)
    _select_etf(client)
    with patch("modules.beasiswa.routes.get_dashboard_breakdown") as mock_func:
        mock_func.return_value = {}
        resp = client.get("/beasiswa/api/dashboard/breakdown?statuses=open")
        assert resp.status_code == 200
        assert mock_func.call_count == 1
        assert mock_func.call_args[0][5] == ["open"]

def test_dashboard_api_monthly_parses_statuses_csv(client):
    from unittest.mock import patch
    from tests.test_beasiswa_routes import login, _select_etf
    login(client)
    _select_etf(client)
    with patch("modules.beasiswa.routes.get_dashboard_monthly") as mock_func:
        mock_func.return_value = {}
        resp = client.get("/beasiswa/api/dashboard/monthly?statuses=complete")
        assert resp.status_code == 200
        assert mock_func.call_count == 1
        assert mock_func.call_args[0][5] == ["complete"]

def test_dashboard_api_latest_payments_parses_statuses_csv(client):
    from unittest.mock import patch
    from tests.test_beasiswa_routes import login, _select_etf
    login(client)
    _select_etf(client)
    with patch("modules.beasiswa.routes.get_dashboard_latest_payments") as mock_func:
        mock_func.return_value = []
        resp = client.get("/beasiswa/api/dashboard/latest_payments?statuses=open,complete")
        assert resp.status_code == 200
        assert mock_func.call_count == 1
        assert mock_func.call_args[0][5] == ["open", "complete"]

def test_dashboard_api_program_summary_parses_statuses_csv(client):
    from unittest.mock import patch
    from tests.test_beasiswa_routes import login, _select_etf
    login(client)
    _select_etf(client)
    with patch("modules.beasiswa.routes.get_dashboard_program_summary") as mock_func:
        mock_func.return_value = []
        resp = client.get("/beasiswa/api/dashboard/program_summary?statuses=open")
        assert resp.status_code == 200
        assert mock_func.call_count == 1
        assert mock_func.call_args[0][5] == ["open"]

def test_dashboard_api_pillar_yearly_parses_statuses_csv(client):
    from unittest.mock import patch
    from tests.test_beasiswa_routes import login, _select_etf
    login(client)
    _select_etf(client)
    with patch("modules.beasiswa.routes.get_dashboard_pillar_yearly") as mock_func:
        mock_func.return_value = []
        resp = client.get("/beasiswa/api/dashboard/pillar_yearly?statuses=open,complete")
        assert resp.status_code == 200
        assert mock_func.call_count == 1
        assert mock_func.call_args[0][4] == ["open", "complete"]
