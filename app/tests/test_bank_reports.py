from datetime import datetime
from modules.bank.reports import classify_rows, month_range


def _row(tanggal, jenis, jumlah, keterangan, source="manual", pam_record_id=None, rid=1):
    return {
        "id": rid, "tanggal": tanggal, "jenis": jenis, "jumlah": jumlah,
        "keterangan": keterangan, "source": source, "pam_record_id": pam_record_id,
    }


def test_classify_rows_excludes_setoran_awal_case_insensitive():
    rows = [
        _row("2025-11-17", "pemasukan", 1500000, "Setoran Awal - 17 Nov 2025"),
        _row("2025-11-20", "pemasukan", 2000, "setoran awal lain"),
        _row("2025-11-24", "pemasukan", 2000000000, "AGRI - PT Cipta Inti"),
    ]
    result = classify_rows(rows)
    assert result["penerimaan"] == {"AGRI - PT Cipta Inti": {"2025-11": 2000000000}}
    assert result["bank"] == {}
    assert result["sahabat_etf"] == {}


def test_classify_rows_pam_rows_go_to_sahabat_etf_grouped_by_name():
    rows = [
        _row("2026-07-09", "pengeluaran", 5320346, "Budi Widjaja", source="pam", pam_record_id=302),
        _row("2026-01-19", "pengeluaran", 7602533, "Budi Widjaja", source="pam", pam_record_id=837),
    ]
    result = classify_rows(rows)
    assert result["sahabat_etf"] == {
        "Budi Widjaja": {"2026-07": 5320346, "2026-01": 7602533}
    }


def test_classify_rows_bank_admin_bunga_nets_pengeluaran_minus_pemasukan():
    rows = [
        _row("2025-12-15", "pengeluaran", 2500, "Bank Admin & Bunga"),
        _row("2025-12-23", "pemasukan", 511742, "Bank Admin & Bunga"),
    ]
    result = classify_rows(rows)
    assert result["bank"] == {"Bunga dan Admin": {"2025-12": 2500 - 511742}}


def test_classify_rows_bank_admin_bunga_matches_case_insensitively():
    rows = [_row("2026-01-05", "pengeluaran", 30000, "bank admin & bunga")]
    result = classify_rows(rows)
    assert result["bank"] == {"Bunga dan Admin": {"2026-01": 30000}}


def test_classify_rows_manual_pemasukan_falls_back_to_penerimaan():
    rows = [_row("2026-01-22", "pemasukan", 4000000000, "APP - PT Tirta Pasific Unity")]
    result = classify_rows(rows)
    assert result["penerimaan"] == {"APP - PT Tirta Pasific Unity": {"2026-01": 4000000000}}


def test_classify_rows_manual_pengeluaran_falls_back_to_bank():
    rows = [_row("2026-01-30", "pengeluaran", 3500000000, "Penempatan RD")]
    result = classify_rows(rows)
    assert result["bank"] == {"Penempatan RD": {"2026-01": 3500000000}}


def test_classify_rows_blank_keterangan_grouped_as_tanpa_keterangan():
    rows = [_row("2026-01-05", "pengeluaran", 1000, "")]
    result = classify_rows(rows)
    assert result["bank"] == {"(Tanpa Keterangan)": {"2026-01": 1000}}


def test_month_range_from_earliest_eligible_to_today():
    rows = [
        _row("2025-11-17", "pemasukan", 1500000, "Setoran Awal - 17 Nov 2025"),
        _row("2025-12-15", "pengeluaran", 2500, "Bank Admin & Bunga"),
    ]
    months = month_range(rows, today=datetime(2026, 3, 1))
    assert months == ["2025-12", "2026-01", "2026-02", "2026-03"]


def test_month_range_empty_data_falls_back_to_current_month():
    months = month_range([], today=datetime(2026, 7, 15))
    assert months == ["2026-07"]


def test_month_range_all_setoran_awal_falls_back_to_current_month():
    rows = [_row("2025-11-17", "pemasukan", 1500000, "Setoran Awal")]
    months = month_range(rows, today=datetime(2026, 7, 15))
    assert months == ["2026-07"]
