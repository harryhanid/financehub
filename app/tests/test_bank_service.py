from database import get_conn
from modules.bank.service import get_setf_rows, split_by_status


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


def test_get_setf_rows_filters_pillar_and_company():
    _insert_pam(2, "PAM-SETF-1", "SETF", "open", 1000000)
    _insert_pam(2, "PAM-AGRI-1", "AGRI", "open", 500000)
    _insert_pam(1, "PAM-SETF-OTHER-CO", "SETF", "open", 700000)
    rows = get_setf_rows(2)
    assert len(rows) == 1
    assert rows[0]["pam_no"] == "PAM-SETF-1"


def test_split_by_status_separates_open_and_complete():
    _insert_pam(2, "PAM-OPEN", "SETF", "open", 1000000)
    _insert_pam(2, "PAM-PROC", "SETF", "on_process", 500000)
    _insert_pam(2, "PAM-DONE", "SETF", "complete", 300000, tanggal_bayar="2026-06-10")
    rows = get_setf_rows(2)
    open_rows, complete_rows = split_by_status(rows)
    assert {r["pam_no"] for r in open_rows} == {"PAM-OPEN", "PAM-PROC"}
    assert [r["pam_no"] for r in complete_rows] == ["PAM-DONE"]


def test_split_by_status_sorts_complete_by_tanggal_bayar_with_pam_date_fallback():
    _insert_pam(2, "PAM-A", "SETF", "complete", 100, pam_date="2026-01-01", tanggal_bayar="2026-06-15")
    _insert_pam(2, "PAM-B", "SETF", "complete", 200, pam_date="2026-02-01", tanggal_bayar="2026-06-01")
    _insert_pam(2, "PAM-C", "SETF", "complete", 300, pam_date="2026-03-01", tanggal_bayar=None)
    rows = get_setf_rows(2)
    _, complete_rows = split_by_status(rows)
    # PAM-C has no tanggal_bayar so falls back to pam_date 2026-03-01,
    # which sorts before PAM-B's 2026-06-01 and PAM-A's 2026-06-15.
    assert [r["pam_no"] for r in complete_rows] == ["PAM-C", "PAM-B", "PAM-A"]


def test_split_by_status_sorts_open_by_pam_date():
    _insert_pam(2, "PAM-LATER", "SETF", "open", 100, pam_date="2026-06-01")
    _insert_pam(2, "PAM-EARLIER", "SETF", "open", 200, pam_date="2026-01-01")
    rows = get_setf_rows(2)
    open_rows, _ = split_by_status(rows)
    assert [r["pam_no"] for r in open_rows] == ["PAM-EARLIER", "PAM-LATER"]


from modules.bank.service import compute_running_balance


def _row(total_amount, date="2026-06-01"):
    return {"pam_no": "X", "total_amount": total_amount, "_date": date}


def test_compute_running_balance_empty():
    result = compute_running_balance([])
    assert result["rows"] == []
    assert result["saldo_current"] == 0
    assert result["total_pemasukan"] == 0
    assert result["total_pengeluaran"] == 0


def test_compute_running_balance_mixed_pemasukan_pengeluaran():
    # -5,000,000 = pemasukan (saldo awal), then two pengeluaran
    rows = [_row(-5000000, "2026-06-01"), _row(2000000, "2026-06-05"), _row(1000000, "2026-06-10")]
    result = compute_running_balance(rows)
    assert result["rows"][0]["pemasukan"] == 5000000
    assert result["rows"][0]["pengeluaran"] == 0
    assert result["rows"][0]["saldo_berjalan"] == 5000000
    assert result["rows"][1]["pengeluaran"] == 2000000
    assert result["rows"][1]["saldo_berjalan"] == 3000000
    assert result["rows"][2]["saldo_berjalan"] == 2000000
    assert result["saldo_current"] == 2000000
    assert result["total_pemasukan"] == 5000000
    assert result["total_pengeluaran"] == 3000000


def test_compute_running_balance_zero_amount_row_is_neutral():
    rows = [_row(1000000), _row(0), _row(-500000)]
    result = compute_running_balance(rows)
    assert result["rows"][1]["pemasukan"] == 0
    assert result["rows"][1]["pengeluaran"] == 0
    assert result["rows"][1]["saldo_berjalan"] == result["rows"][0]["saldo_berjalan"]
    assert result["saldo_current"] == -500000
    assert result["total_pemasukan"] == 500000
    assert result["total_pengeluaran"] == 1000000


from datetime import datetime
from modules.bank.service import get_available_years, resolve_period, filter_period


def test_get_available_years_returns_distinct_years_desc():
    _insert_pam(2, "PAM-1", "SETF", "complete", 100, tanggal_bayar="2025-03-01")
    _insert_pam(2, "PAM-2", "SETF", "complete", 200, tanggal_bayar="2026-01-01")
    _insert_pam(2, "PAM-3", "SETF", "complete", 300, tanggal_bayar="2026-07-01")
    _insert_pam(2, "PAM-4", "SETF", "open", 400)  # open, no tanggal_bayar -> excluded
    years = get_available_years(2)
    assert years == [2026, 2025]


def test_get_available_years_empty_when_no_complete_transactions():
    assert get_available_years(2) == []


def test_resolve_period_defaults_to_today_when_both_params_absent():
    today = datetime(2026, 7, 14)
    bulan, tahun = resolve_period(None, None, today=today)
    assert (bulan, tahun) == (7, 2026)


def test_resolve_period_sentinel_all_means_no_filter():
    bulan, tahun = resolve_period("all", "all")
    assert (bulan, tahun) == (None, None)


def test_resolve_period_parses_explicit_values():
    bulan, tahun = resolve_period("3", "2025")
    assert (bulan, tahun) == (3, 2025)


def test_filter_period_no_filter_returns_all_rows():
    rows = [{"_date": "2026-06-01"}, {"_date": "2026-07-01"}]
    assert filter_period(rows, None, None) == rows


def test_filter_period_by_bulan_only():
    rows = [{"_date": "2025-07-01"}, {"_date": "2026-07-01"}, {"_date": "2026-08-01"}]
    result = filter_period(rows, 7, None)
    assert result == [{"_date": "2025-07-01"}, {"_date": "2026-07-01"}]


def test_filter_period_by_tahun_only():
    rows = [{"_date": "2025-07-01"}, {"_date": "2026-07-01"}, {"_date": "2026-08-01"}]
    result = filter_period(rows, None, 2026)
    assert result == [{"_date": "2026-07-01"}, {"_date": "2026-08-01"}]


def test_filter_period_by_bulan_and_tahun():
    rows = [{"_date": "2025-07-01"}, {"_date": "2026-07-01"}, {"_date": "2026-08-01"}]
    result = filter_period(rows, 7, 2026)
    assert result == [{"_date": "2026-07-01"}]


from modules.bank.service import sync_pam_to_bank_setf


def test_sync_pam_to_bank_setf_inserts_pengeluaran_row():
    conn = get_conn()
    conn.execute(
        """INSERT INTO pam_records
           (company_id, pam_no, pam_date, keterangan, total_amount, status, pillar, tanggal_bayar, created_at)
           VALUES (2, 'PAM-SYNC-1', '2026-07-01', 'Beasiswa test', 2000000, 'complete', 'SETF', '2026-07-05', datetime('now'))"""
    )
    pam_id = conn.execute("SELECT id FROM pam_records WHERE pam_no='PAM-SYNC-1'").fetchone()["id"]
    conn.commit()
    conn.close()

    sync_pam_to_bank_setf(pam_id)

    conn = get_conn()
    row = conn.execute("SELECT * FROM bank_setf WHERE pam_record_id=?", (pam_id,)).fetchone()
    conn.close()
    row = dict(row)
    assert row["jenis"] == "pengeluaran"
    assert row["jumlah"] == 2000000
    assert row["source"] == "pam"
    assert row["tanggal"] == "2026-07-05"
    assert row["company_id"] == 2


def test_sync_pam_to_bank_setf_skips_non_setf_pillar():
    conn = get_conn()
    conn.execute(
        """INSERT INTO pam_records
           (company_id, pam_no, pam_date, keterangan, total_amount, status, pillar, tanggal_bayar, created_at)
           VALUES (2, 'PAM-SYNC-2', '2026-07-01', 'AGRI test', 3000000, 'complete', 'AGRI', '2026-07-05', datetime('now'))"""
    )
    pam_id = conn.execute("SELECT id FROM pam_records WHERE pam_no='PAM-SYNC-2'").fetchone()["id"]
    conn.commit()
    conn.close()

    sync_pam_to_bank_setf(pam_id)

    conn = get_conn()
    row = conn.execute("SELECT * FROM bank_setf WHERE pam_record_id=?", (pam_id,)).fetchone()
    conn.close()
    assert row is None


def test_sync_pam_to_bank_setf_is_idempotent():
    conn = get_conn()
    conn.execute(
        """INSERT INTO pam_records
           (company_id, pam_no, pam_date, keterangan, total_amount, status, pillar, tanggal_bayar, created_at)
           VALUES (2, 'PAM-SYNC-3', '2026-07-01', 'Test', 1500000, 'complete', 'SETF', '2026-07-05', datetime('now'))"""
    )
    pam_id = conn.execute("SELECT id FROM pam_records WHERE pam_no='PAM-SYNC-3'").fetchone()["id"]
    conn.commit()
    conn.close()

    sync_pam_to_bank_setf(pam_id)
    sync_pam_to_bank_setf(pam_id)

    conn = get_conn()
    rows = conn.execute("SELECT * FROM bank_setf WHERE pam_record_id=?", (pam_id,)).fetchall()
    conn.close()
    assert len(rows) == 1


def test_sync_pam_to_bank_setf_falls_back_to_pam_date_when_no_tanggal_bayar():
    conn = get_conn()
    conn.execute(
        """INSERT INTO pam_records
           (company_id, pam_no, pam_date, keterangan, total_amount, status, pillar, tanggal_bayar, created_at)
           VALUES (2, 'PAM-SYNC-4', '2026-06-20', 'Test', 800000, 'complete', 'SETF', NULL, datetime('now'))"""
    )
    pam_id = conn.execute("SELECT id FROM pam_records WHERE pam_no='PAM-SYNC-4'").fetchone()["id"]
    conn.commit()
    conn.close()

    sync_pam_to_bank_setf(pam_id)

    conn = get_conn()
    row = dict(conn.execute("SELECT * FROM bank_setf WHERE pam_record_id=?", (pam_id,)).fetchone())
    conn.close()
    assert row["tanggal"] == "2026-06-20"
