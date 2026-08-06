import pytest
from database import get_conn
from modules.sponsorship.service import (
    list_perusahaan, get_perusahaan, seed_perusahaan, get_lembaga_suggestions,
    create_transaksi, get_transaksi, update_transaksi, list_transaksi,
    count_transaksi, get_available_years,
    create_perusahaan, update_perusahaan, delete_perusahaan,
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


def test_update_transaksi_rejects_unknown_cat1(app):
    _seed_one_perusahaan()
    created = create_transaksi(SMT, _valid_payload())
    result = update_transaksi(created["id"], {"cat1": "Perusahaan Fiktif"})
    assert result["ok"] is False
    row = get_transaksi(created["id"])
    assert row["cat1"] == "SMART"  # unchanged


def test_update_transaksi_recomputes_cat2_cat3_on_cat1_change(app):
    _seed_one_perusahaan()
    seed_perusahaan([("PT KUNCIRANMAS SEJATI", "Property", "PROPERTY")])
    created = create_transaksi(SMT, _valid_payload())  # cat1=SMART -> AGRI
    result = update_transaksi(created["id"], {"cat1": "PT KUNCIRANMAS SEJATI"})
    assert result["ok"] is True
    row = get_transaksi(created["id"])
    assert row["cat1"] == "PT KUNCIRANMAS SEJATI"
    assert row["cat2"] == "Property"
    assert row["cat3"] == "PROPERTY"


def test_update_transaksi_rejects_invalid_cat(app):
    _seed_one_perusahaan()
    created = create_transaksi(SMT, _valid_payload())
    result = update_transaksi(created["id"], {"cat": "Not Valid"})
    assert result["ok"] is False


def test_update_transaksi_coerces_amount_to_float(app):
    _seed_one_perusahaan()
    created = create_transaksi(SMT, _valid_payload())
    result = update_transaksi(created["id"], {"amount_request": "12345"})
    assert result["ok"] is True
    row = get_transaksi(created["id"])
    assert row["amount_request"] == 12345.0


def test_update_transaksi_rejects_invalid_amount(app):
    _seed_one_perusahaan()
    created = create_transaksi(SMT, _valid_payload())
    result = update_transaksi(created["id"], {"amount_request": "not-a-number"})
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

def test_list_transaksi_filter_by_cat3_list(app):
    _seed_one_perusahaan()
    seed_perusahaan([("PT KUNCIRANMAS SEJATI", "Property", "PROPERTY")])
    create_transaksi(SMT, _valid_payload())  # cat1=SMART -> AGRI
    create_transaksi(SMT, _valid_payload(cat1="PT KUNCIRANMAS SEJATI"))
    rows = list_transaksi(SMT, filters={"cat3": ["PROPERTY", "AGRI"]})
    assert len(rows) == 2
    rows_single = list_transaksi(SMT, filters={"cat3": ["PROPERTY"]})
    assert len(rows_single) == 1
    assert rows_single[0]["cat1"] == "PT KUNCIRANMAS SEJATI"


def test_list_transaksi_filter_by_cat_list(app):
    _seed_one_perusahaan()
    create_transaksi(SMT, _valid_payload(cat="Sponsorship"))
    create_transaksi(SMT, _valid_payload(cat="CSR Gedung"))
    rows = list_transaksi(SMT, filters={"cat": ["Sponsorship", "CSR Gedung"]})
    assert len(rows) == 2
    rows_single = list_transaksi(SMT, filters={"cat": ["CSR Gedung"]})
    assert len(rows_single) == 1
    assert rows_single[0]["cat"] == "CSR Gedung"


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


def test_update_transaksi_ignores_direct_cat2_cat3_without_cat1(app):
    _seed_one_perusahaan()
    created = create_transaksi(SMT, _valid_payload())  # cat1=SMART -> cat2=AGRI, cat3=AGRI
    result = update_transaksi(created["id"], {"cat2": "TOTALLY_MADE_UP_CAT2", "cat3": "FAKE_PILLAR"})
    assert result["ok"] is True  # update succeeds (no other fields to reject), but ignores cat2/cat3
    row = get_transaksi(created["id"])
    assert row["cat2"] == "AGRI"  # unchanged — cat2/cat3 cannot be set directly
    assert row["cat3"] == "AGRI"


def test_get_transaksi_with_company_id_returns_none_for_wrong_company(app):
    _seed_one_perusahaan()
    created = create_transaksi(SMT, _valid_payload())
    assert get_transaksi(created["id"], company_id=2) is None
    assert get_transaksi(created["id"], company_id=SMT) is not None


def test_update_transaksi_with_company_id_rejects_wrong_company(app):
    _seed_one_perusahaan()
    created = create_transaksi(SMT, _valid_payload())
    result = update_transaksi(created["id"], {"perihal": "hacked"}, company_id=2)
    assert result["ok"] is False
    row = get_transaksi(created["id"])
    assert row["perihal"] != "hacked"


def test_update_transaksi_allows_unchanged_cat1_not_in_lookup(app):
    _seed_one_perusahaan()  # only seeds SMART
    conn_test_id = create_transaksi(SMT, _valid_payload())["id"]
    # Simulate a migrated row with a cat1 not in the lookup table (bypass validation like migrate.py does)
    from database import get_conn
    conn = get_conn()
    conn.execute("UPDATE sponsorship_transaksi SET cat1 = 'TAPIAN', cat2 = 'AGRI', cat3 = 'AGRI' WHERE id = ?", (conn_test_id,))
    conn.commit()
    conn.close()
    # Now edit an unrelated field, sending the unchanged cat1 (as the real modal does)
    result = update_transaksi(conn_test_id, {"cat1": "TAPIAN", "perihal": "Fixed typo"})
    assert result["ok"] is True
    row = get_transaksi(conn_test_id)
    assert row["perihal"] == "Fixed typo"
    assert row["cat1"] == "TAPIAN"
    assert row["cat2"] == "AGRI"


def test_update_transaksi_still_rejects_actual_cat1_change_to_unknown(app):
    _seed_one_perusahaan()
    created = create_transaksi(SMT, _valid_payload())
    result = update_transaksi(created["id"], {"cat1": "Perusahaan Fiktif"})
    assert result["ok"] is False


def test_create_perusahaan_success(app):
    result = create_perusahaan("SMART", "AGRI", "AGRI")
    assert result["ok"] is True
    assert get_perusahaan("SMART") == {"cat1": "SMART", "cat2": "AGRI", "cat3": "AGRI"}


def test_create_perusahaan_rejects_duplicate_cat1(app):
    create_perusahaan("SMART", "AGRI", "AGRI")
    result = create_perusahaan("SMART", "AGRI", "APP")
    assert result["ok"] is False
    assert "sudah terdaftar" in result["pesan"]
    assert get_perusahaan("SMART")["cat3"] == "AGRI"


def test_create_perusahaan_rejects_invalid_cat3(app):
    result = create_perusahaan("SMART", "AGRI", "NOT-A-PILLAR")
    assert result["ok"] is False
    assert get_perusahaan("SMART") is None


def test_create_perusahaan_rejects_blank_fields(app):
    assert create_perusahaan("", "AGRI", "AGRI")["ok"] is False
    assert create_perusahaan("SMART", "", "AGRI")["ok"] is False
    assert create_perusahaan("SMART", "AGRI", "")["ok"] is False


def test_update_perusahaan_success(app):
    create_perusahaan("SMART", "AGRI", "AGRI")
    result = update_perusahaan("SMART", "Mining", "PROPERTY")
    assert result["ok"] is True
    assert get_perusahaan("SMART") == {"cat1": "SMART", "cat2": "Mining", "cat3": "PROPERTY"}


def test_update_perusahaan_not_found(app):
    result = update_perusahaan("NOT-THERE", "AGRI", "AGRI")
    assert result["ok"] is False


def test_update_perusahaan_rejects_invalid_cat3(app):
    create_perusahaan("SMART", "AGRI", "AGRI")
    result = update_perusahaan("SMART", "AGRI", "NOT-A-PILLAR")
    assert result["ok"] is False
    assert get_perusahaan("SMART")["cat3"] == "AGRI"


def test_delete_perusahaan_success(app):
    create_perusahaan("SMART", "AGRI", "AGRI")
    result = delete_perusahaan("SMART")
    assert result["ok"] is True
    assert get_perusahaan("SMART") is None


def test_delete_perusahaan_not_found(app):
    result = delete_perusahaan("NOT-THERE")
    assert result["ok"] is False


def test_delete_perusahaan_does_not_affect_existing_transaksi_snapshot(app):
    create_perusahaan("SMART", "AGRI", "AGRI")
    created = create_transaksi(1, _valid_payload(cat1="SMART"))
    delete_perusahaan("SMART")
    row = get_transaksi(created["id"])
    assert row["cat1"] == "SMART"
    assert row["cat2"] == "AGRI"
    assert row["cat3"] == "AGRI"

