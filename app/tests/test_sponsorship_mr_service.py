from datetime import datetime
from modules.sponsorship.service import seed_perusahaan, create_transaksi, get_sponsorship_mr

SMT = 1


def _seed():
    seed_perusahaan([("SMART", "AGRI", "AGRI"), ("IKPP", "APP", "APP")])


def _payload(**overrides):
    payload = {
        "cat": "Sponsorship", "description": "Sosial",
        "tanggal_form_sponsor": "2026-01-20", "cat1": "SMART",
        "lembaga_perorangan": "Yayasan Test", "perihal": "Bantuan Banjir",
        "amount_request": 25000000,
    }
    payload.update(overrides)
    return payload


def test_mr_maps_all_columns_for_single_row(app):
    _seed()
    create_transaksi(SMT, _payload())
    rows = get_sponsorship_mr(SMT, ["2026"])
    assert len(rows) == 1
    r = rows[0]
    assert r["account_management"] == 70107800
    assert r["id_no"] == ""
    assert r["date"] == datetime(2026, 1, 20)
    assert r["date_display"] == "20-Jan-26"
    assert r["allocation_memo"] == "Sosial - Yayasan Test - Bantuan Banjir"
    assert r["budget_activity"] == ""
    assert r["cost_center"] == "POSPON"
    assert r["debit_credit"] == 25000000
    assert r["source"] == "Sponsor"
    assert r["coa_ho"] == 70107800
    assert r["cost_center2"] == "$POCCOM"
    assert r["month"] == 1
    assert r["cc0"] == "26"
    assert r["cc1"] == 5
    assert r["bc1"] == "-25-"
    assert r["new_code"] == "A26-5-25-1"
    assert r["memo"] == "- Act 2026 : Sosial - Yayasan Test - Bantuan Banjir Month : 1"
    assert r["bc"] == "Sponsorship - Non Building"


def test_mr_allocation_memo_skips_empty_perihal(app):
    _seed()
    create_transaksi(SMT, _payload(perihal=None))
    rows = get_sponsorship_mr(SMT, ["2026"])
    assert rows[0]["allocation_memo"] == "Sosial - Yayasan Test"
    assert rows[0]["memo"] == "- Act 2026 : Sosial - Yayasan Test Month : 1"


def test_mr_new_code_increments_within_same_year(app):
    _seed()
    create_transaksi(SMT, _payload(tanggal_form_sponsor="2026-01-05", lembaga_perorangan="A"))
    create_transaksi(SMT, _payload(tanggal_form_sponsor="2026-01-20", lembaga_perorangan="B"))
    create_transaksi(SMT, _payload(tanggal_form_sponsor="2026-03-01", lembaga_perorangan="C"))
    rows = get_sponsorship_mr(SMT, ["2026"])
    assert [r["new_code"] for r in rows] == ["A26-5-25-1", "A26-5-25-2", "A26-5-25-3"]


def test_mr_new_code_resets_per_year(app):
    _seed()
    create_transaksi(SMT, _payload(tanggal_form_sponsor="2026-01-05", lembaga_perorangan="A"))
    create_transaksi(SMT, _payload(tanggal_form_sponsor="2025-06-01", lembaga_perorangan="B"))
    create_transaksi(SMT, _payload(tanggal_form_sponsor="2026-02-01", lembaga_perorangan="C"))
    create_transaksi(SMT, _payload(tanggal_form_sponsor="2025-07-01", lembaga_perorangan="D"))
    rows = get_sponsorship_mr(SMT, ["2025", "2026"])
    by_lembaga = {r["allocation_memo"].split(" - ")[1]: r["new_code"] for r in rows}
    assert by_lembaga["B"] == "A25-5-25-1"
    assert by_lembaga["D"] == "A25-5-25-2"
    assert by_lembaga["A"] == "A26-5-25-1"
    assert by_lembaga["C"] == "A26-5-25-2"


def test_mr_rows_sorted_by_date_ascending_then_id(app):
    _seed()
    create_transaksi(SMT, _payload(tanggal_form_sponsor="2026-03-01", lembaga_perorangan="Later"))
    create_transaksi(SMT, _payload(tanggal_form_sponsor="2026-01-01", lembaga_perorangan="Earlier1"))
    create_transaksi(SMT, _payload(tanggal_form_sponsor="2026-01-01", lembaga_perorangan="Earlier2"))
    rows = get_sponsorship_mr(SMT, ["2026"])
    order = [r["allocation_memo"].split(" - ")[1] for r in rows]
    assert order == ["Earlier1", "Earlier2", "Later"]


def test_mr_includes_all_rows_regardless_of_cat_or_description(app):
    _seed()
    create_transaksi(SMT, _payload(cat="CSR Gedung", description="Akademisi", lembaga_perorangan="X"))
    create_transaksi(SMT, _payload(cat="Sponsorship", description="Media", lembaga_perorangan="Y"))
    rows = get_sponsorship_mr(SMT, ["2026"])
    assert len(rows) == 2


def test_mr_respects_company_scope(app):
    _seed()
    create_transaksi(SMT, _payload(lembaga_perorangan="SMT Row"))
    create_transaksi(2, _payload(lembaga_perorangan="Other Company Row"))
    rows = get_sponsorship_mr(SMT, ["2026"])
    assert len(rows) == 1
    assert rows[0]["allocation_memo"].split(" - ")[1] == "SMT Row"


def test_mr_filters_by_tahun(app):
    _seed()
    create_transaksi(SMT, _payload(tanggal_form_sponsor="2025-06-01", lembaga_perorangan="Old"))
    create_transaksi(SMT, _payload(tanggal_form_sponsor="2026-06-01", lembaga_perorangan="New"))
    rows = get_sponsorship_mr(SMT, ["2026"])
    assert len(rows) == 1
    assert rows[0]["allocation_memo"].split(" - ")[1] == "New"
