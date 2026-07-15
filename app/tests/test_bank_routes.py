from datetime import datetime
from database import get_conn


def login(client, username="admin", password="Admin@123"):
    return client.post("/auth/login", json={"username": username, "password": password})


def _select_etf(client):
    client.post("/select-company", data={"company_id": "2"})


def _insert_pam(company_id, pam_no, pillar, status, total_amount,
                 pam_date="2026-06-01", tanggal_bayar=None, keterangan="Test"):
    conn = get_conn()
    conn.execute(
        """INSERT INTO pam_records
           (company_id, pam_no, pam_date, keterangan, total_amount, status, pillar, tanggal_bayar, created_at)
           VALUES (?,?,?,?,?,?,?,?,datetime('now'))""",
        (company_id, pam_no, pam_date, keterangan, total_amount, status, pillar, tanggal_bayar),
    )
    conn.commit()
    conn.close()


def test_index_requires_login(client):
    resp = client.get("/bank/")
    assert resp.status_code == 302


def test_index_renders_after_login(client):
    login(client)
    _select_etf(client)
    resp = client.get("/bank/")
    assert resp.status_code == 200
    assert b"Bank Sahabat ETF" in resp.data


def _insert_bank_setf(company_id, tanggal, jenis, jumlah, keterangan="Test", source="manual", pam_record_id=None):
    conn = get_conn()
    conn.execute(
        "INSERT INTO bank_setf (company_id, tanggal, jenis, jumlah, keterangan, source, pam_record_id) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (company_id, tanggal, jenis, jumlah, keterangan, source, pam_record_id),
    )
    conn.commit()
    conn.close()


def test_index_shows_summary_cards_and_saldo(client):
    login(client)
    _select_etf(client)
    _insert_bank_setf(2, "2020-07-01", "pemasukan", 5000000, keterangan="PAM-IN")
    _insert_bank_setf(2, "2020-07-05", "pengeluaran", 2000000, keterangan="PAM-OUT")
    resp = client.get("/bank/?bulan=all&tahun=all")
    assert resp.status_code == 200
    assert b"Saldo Saat Ini" in resp.data
    assert b"3000000" in resp.data
    assert b"PAM-IN" in resp.data
    assert b"PAM-OUT" in resp.data


def test_index_filters_table_by_selected_period(client):
    login(client)
    _select_etf(client)
    _insert_bank_setf(2, "2026-07-01", "pengeluaran", 1000000, keterangan="PAM-JUL")
    _insert_bank_setf(2, "2026-08-01", "pengeluaran", 2000000, keterangan="PAM-AUG")
    resp = client.get("/bank/?bulan=7&tahun=2026")
    assert b"PAM-JUL" in resp.data
    assert b"PAM-AUG" not in resp.data


def test_index_summary_cards_unaffected_by_filter(client):
    login(client)
    _select_etf(client)
    _insert_bank_setf(2, "2026-07-01", "pemasukan", 1000000, keterangan="PAM-JUL")
    _insert_bank_setf(2, "2026-08-01", "pemasukan", 2000000, keterangan="PAM-AUG")
    resp = client.get("/bank/?bulan=7&tahun=2026")
    assert b"3000000" in resp.data  # total pemasukan = 1jt + 2jt regardless of filter


def test_index_empty_period_shows_specific_empty_state(client):
    login(client)
    _select_etf(client)
    _insert_bank_setf(2, "2026-08-01", "pengeluaran", 1000000, keterangan="PAM-AUG")
    resp = client.get("/bank/?bulan=1&tahun=2026")
    assert "Belum ada mutasi pada periode ini".encode() in resp.data


def test_index_filter_all_shows_full_history(client):
    login(client)
    _select_etf(client)
    _insert_bank_setf(2, "2026-07-01", "pengeluaran", 1000000, keterangan="PAM-JUL")
    _insert_bank_setf(2, "2026-08-01", "pengeluaran", 2000000, keterangan="PAM-AUG")
    resp = client.get("/bank/?bulan=all&tahun=all")
    assert b"PAM-JUL" in resp.data
    assert b"PAM-AUG" in resp.data


def test_index_defaults_to_current_month_and_year(client):
    login(client)
    _select_etf(client)
    now = datetime.now()
    date_str = f"{now.year:04d}-{now.month:02d}-15"
    _insert_bank_setf(2, date_str, "pengeluaran", 1000000, keterangan="PAM-NOW")
    _insert_bank_setf(2, "2020-01-01", "pengeluaran", 500000, keterangan="PAM-OLD")
    resp = client.get("/bank/")
    assert resp.status_code == 200
    assert b"PAM-NOW" in resp.data
    assert b"PAM-OLD" not in resp.data


def test_index_does_not_leak_other_pillar_or_company_data(client):
    login(client)
    _select_etf(client)
    _insert_bank_setf(1, "2020-01-01", "pengeluaran", 1000000, keterangan="PAM-SMT")
    resp = client.get("/bank/?bulan=all&tahun=all")
    assert b"PAM-SMT" not in resp.data


def test_index_open_tab_shows_only_pending_status(client):
    login(client)
    _select_etf(client)
    _insert_pam(2, "PAM-PEND", "SETF", "open", 1500000, pam_date="2026-05-01")
    _insert_pam(2, "PAM-PROC", "SETF", "on_process", 800000, pam_date="2026-05-02")
    resp = client.get("/bank/")
    assert b"PAM-PEND" in resp.data
    assert b"PAM-PROC" in resp.data


def test_index_open_tab_has_no_mark_complete_action(client):
    login(client)
    _select_etf(client)
    _insert_pam(2, "PAM-PEND", "SETF", "open", 1500000, pam_date="2026-05-01")
    resp = client.get("/bank/")
    assert b"mark-complete" not in resp.data


def test_index_has_two_tabs_wired_for_js_switching(client):
    login(client)
    _select_etf(client)
    resp = client.get("/bank/")
    assert b"data-tabs" in resp.data
    assert resp.data.count(b'class="tab-btn"') == 2


def test_add_transaksi_route_creates_row(client):
    login(client)
    _select_etf(client)
    resp = client.post("/bank/transaksi", json={
        "tanggal": "2026-07-14", "jenis": "pemasukan", "jumlah": 1000000, "keterangan": "Transfer awal"
    })
    assert resp.status_code == 200
    assert resp.get_json()["ok"] is True
    detail = client.get("/bank/?bulan=all&tahun=all")
    assert b"Transfer awal" in detail.data


def test_add_transaksi_route_rejects_invalid_jenis(client):
    login(client)
    _select_etf(client)
    resp = client.post("/bank/transaksi", json={
        "tanggal": "2026-07-14", "jenis": "invalid", "jumlah": 1000, "keterangan": "X"
    })
    assert resp.get_json()["ok"] is False


def test_update_transaksi_route_modifies_row(client):
    login(client)
    _select_etf(client)
    _insert_bank_setf(2, "2026-07-14", "pemasukan", 1000000, keterangan="Original")
    conn = get_conn()
    row_id = conn.execute("SELECT id FROM bank_setf WHERE keterangan='Original'").fetchone()["id"]
    conn.close()
    resp = client.post(f"/bank/transaksi/{row_id}/update", json={
        "tanggal": "2026-07-15", "jenis": "pengeluaran", "jumlah": 500000, "keterangan": "Updated"
    })
    assert resp.get_json()["ok"] is True
    detail = client.get("/bank/?bulan=all&tahun=all")
    assert b"Updated" in detail.data


def test_delete_transaksi_route_removes_row(client):
    login(client)
    _select_etf(client)
    _insert_bank_setf(2, "2026-07-14", "pemasukan", 1000000, keterangan="To delete")
    conn = get_conn()
    row_id = conn.execute("SELECT id FROM bank_setf WHERE keterangan='To delete'").fetchone()["id"]
    conn.close()
    resp = client.post(f"/bank/transaksi/{row_id}/delete")
    assert resp.get_json()["ok"] is True
    detail = client.get("/bank/?bulan=all&tahun=all")
    assert b"To delete" not in detail.data


def test_export_laporan_mutasi_requires_login(client):
    resp = client.get("/bank/export-laporan-mutasi")
    assert resp.status_code == 302


def test_export_laporan_mutasi_returns_xlsx(client):
    login(client)
    _select_etf(client)
    _insert_bank_setf(2, "2026-07-01", "pemasukan", 1000000, keterangan="AGRI - PT Cipta Inti")
    resp = client.get("/bank/export-laporan-mutasi")
    assert resp.status_code == 200
    assert resp.headers["Content-Type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert resp.headers["Content-Disposition"].startswith("attachment")


def test_index_has_export_laporan_mutasi_button(client):
    login(client)
    _select_etf(client)
    resp = client.get("/bank/")
    assert b"Export Laporan Mutasi" in resp.data
    assert b"/bank/export-laporan-mutasi" in resp.data
