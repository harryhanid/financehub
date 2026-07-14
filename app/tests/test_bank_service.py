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
