import pytest
from database import get_conn
from modules.sponsorship.service import (
    list_perusahaan, get_perusahaan, seed_perusahaan, get_lembaga_suggestions,
    create_transaksi, get_transaksi, update_transaksi, list_transaksi,
    count_transaksi, get_available_years,
)

SMT = 1


def _seed_one_perusahaan():
    seed_perusahaan([("SMART", "AGRI", "AGRI"), ("IKPP", "APP", "APP")])


def test_seed_and_list_perusahaan(app):
    n = seed_perusahaan([("SMART", "AGRI", "AGRI"), ("IKPP", "APP", "APP")])
    assert n == 2
    rows = list_perusahaan()
    assert {"cat1": "SMART", "cat2": "AGRI", "cat3": "AGRI"} in rows
    assert len(rows) == 2


def test_seed_perusahaan_is_idempotent(app):
    seed_perusahaan([("SMART", "AGRI", "AGRI")])
    n = seed_perusahaan([("SMART", "AGRI", "AGRI")])
    assert n == 0
    assert len(list_perusahaan()) == 1


def test_get_perusahaan_found_and_missing(app):
    _seed_one_perusahaan()
    assert get_perusahaan("SMART") == {"cat1": "SMART", "cat2": "AGRI", "cat3": "AGRI"}
    assert get_perusahaan("NOT-THERE") is None


def _valid_payload(**overrides):
    payload = {
        "cat": "Sponsorship",
        "description": "Sosial",
        "tanggal_form_sponsor": "2026-01-15",
        "cat1": "SMART",
        "lembaga_perorangan": "Yayasan Test",
        "amount_request": 5000000,
    }
    payload.update(overrides)
    return payload


def test_create_transaksi_success(app):
    _seed_one_perusahaan()
    result = create_transaksi(SMT, _valid_payload())
    assert result["ok"] is True
    assert result["id"] is not None
    row = get_transaksi(result["id"])
    assert row["cat1"] == "SMART"
    assert row["cat2"] == "AGRI"
    assert row["cat3"] == "AGRI"
    assert row["coa"] == "701078002"
    assert row["agri_amount"] == 5000000
    assert row["app_amount"] == 0
    assert row["energy_finance_amount"] == 0
    assert row["property_amount"] == 0


def test_create_transaksi_rejects_invalid_cat(app):
    _seed_one_perusahaan()
    result = create_transaksi(SMT, _valid_payload(cat="Not A Valid Cat"))
    assert result["ok"] is False
    assert "Cat" in result["pesan"]


def test_create_transaksi_rejects_invalid_description(app):
    _seed_one_perusahaan()
    result = create_transaksi(SMT, _valid_payload(description="Bukan Kategori"))
    assert result["ok"] is False


def test_create_transaksi_rejects_unknown_cat1(app):
    _seed_one_perusahaan()
    result = create_transaksi(SMT, _valid_payload(cat1="Perusahaan Fiktif"))
    assert result["ok"] is False
    assert "Cat1" in result["pesan"]


def test_create_transaksi_allows_zero_amount(app):
    _seed_one_perusahaan()
    result = create_transaksi(SMT, _valid_payload(amount_request=0))
    assert result["ok"] is True


def test_create_transaksi_allows_blank_cat4_and_dates(app):
    _seed_one_perusahaan()
    result = create_transaksi(SMT, _valid_payload())
    row = get_transaksi(result["id"])
    assert row["cat4"] is None
    assert row["tanggal_payment"] is None


def test_get_lembaga_suggestions_returns_distinct(app):
    _seed_one_perusahaan()
    create_transaksi(SMT, _valid_payload(lembaga_perorangan="Yayasan A"))
    create_transaksi(SMT, _valid_payload(lembaga_perorangan="Yayasan A"))
    create_transaksi(SMT, _valid_payload(lembaga_perorangan="Yayasan B"))
    suggestions = get_lembaga_suggestions(SMT)
    assert sorted(suggestions) == ["Yayasan A", "Yayasan B"]


def test_update_transaksi_success(app):
    _seed_one_perusahaan()
    created = create_transaksi(SMT, _valid_payload())
    result = update_transaksi(created["id"], {"perihal": "Updated perihal", "amount_request": 9999})
    assert result["ok"] is True
    row = get_transaksi(created["id"])
    assert row["perihal"] == "Updated perihal"
    assert row["amount_request"] == 9999
    assert row["updated_at"] is not None


def test_update_transaksi_not_found(app):
    result = update_transaksi(99999, {"perihal": "x"})
    assert result["ok"] is False


def test_list_and_count_transaksi_filters_by_company(app):
    _seed_one_perusahaan()
    create_transaksi(SMT, _valid_payload())
    create_transaksi(2, _valid_payload())  # different company
    assert count_transaksi(SMT) == 1
    rows = list_transaksi(SMT)
    assert len(rows) == 1
    assert count_transaksi(2) == 1


def test_list_transaksi_filter_by_cat3(app):
    _seed_one_perusahaan()
    seed_perusahaan([("PT KUNCIRANMAS SEJATI", "Property", "PROPERTY")])
    create_transaksi(SMT, _valid_payload())  # cat1=SMART -> AGRI
    create_transaksi(SMT, _valid_payload(cat1="PT KUNCIRANMAS SEJATI"))
    rows = list_transaksi(SMT, filters={"cat3": "PROPERTY"})
    assert len(rows) == 1
    assert rows[0]["cat1"] == "PT KUNCIRANMAS SEJATI"


def test_list_transaksi_filter_by_status(app):
    _seed_one_perusahaan()
    created_done = create_transaksi(SMT, _valid_payload())
    update_transaksi(created_done["id"], {"status": "Done"})
    created_pending = create_transaksi(SMT, _valid_payload())
    update_transaksi(created_pending["id"], {"status": "Menunggu Approval"})
    rows = list_transaksi(SMT, filters={"status": "Done"})
    assert len(rows) == 1
    assert rows[0]["id"] == created_done["id"]


def test_list_transaksi_pagination(app):
    _seed_one_perusahaan()
    for _ in range(5):
        create_transaksi(SMT, _valid_payload())
    page1 = list_transaksi(SMT, limit=2, offset=0)
    page2 = list_transaksi(SMT, limit=2, offset=2)
    assert len(page1) == 2
    assert len(page2) == 2
    assert page1[0]["id"] != page2[0]["id"]


def test_get_available_years(app):
    _seed_one_perusahaan()
    create_transaksi(SMT, _valid_payload(tanggal_form_sponsor="2025-06-01"))
    create_transaksi(SMT, _valid_payload(tanggal_form_sponsor="2026-01-01"))
    assert get_available_years(SMT) == ["2026", "2025"]
