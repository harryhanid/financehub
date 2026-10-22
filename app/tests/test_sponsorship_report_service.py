from modules.sponsorship.service import (
    seed_perusahaan, create_transaksi, update_transaksi, get_sponsorship_report,
    normalise_bulan, month_label,
)

SMT = 1


def _seed():
    seed_perusahaan([("SMART", "AGRI", "AGRI"), ("IKPP", "APP", "APP")])


def _payload(**overrides):
    payload = {
        "cat": "Sponsorship", "description": "Sosial",
        "tanggal_form_sponsor": "2026-01-15", "cat1": "SMART",
        "lembaga_perorangan": "Yayasan Test", "amount_request": 1000000,
    }
    payload.update(overrides)
    return payload


def test_report_pivots_amount_into_correct_pillar_column(app):
    _seed()
    create_transaksi(SMT, _payload(cat1="SMART", amount_request=5000000))  # AGRI
    data = get_sponsorship_report(SMT, "2026", "all")
    row = data["sections"][0]["rows"][0]
    assert row["agri_amount"] == 5000000
    assert row["app_amount"] == 0
    assert row["energy_finance_amount"] == 0
    assert row["property_amount"] == 0
    assert row["total"] == 5000000


def test_report_sections_ordered_by_config_description_list(app):
    _seed()
    create_transaksi(SMT, _payload(description="Sosial", amount_request=1000))
    create_transaksi(SMT, _payload(description="Akademisi", amount_request=1000))
    data = get_sponsorship_report(SMT, "2026", "all")
    descriptions = [s["description"] for s in data["sections"]]
    assert descriptions == ["Akademisi", "Sosial"]  # config order, not insertion order


def test_report_hides_sections_with_no_transactions(app):
    _seed()
    create_transaksi(SMT, _payload(description="Sosial", amount_request=1000))
    data = get_sponsorship_report(SMT, "2026", "all")
    descriptions = [s["description"] for s in data["sections"]]
    assert descriptions == ["Sosial"]


def test_report_rows_within_section_sorted_by_total_descending(app):
    _seed()
    create_transaksi(SMT, _payload(description="Sosial", lembaga_perorangan="Kecil", amount_request=100))
    create_transaksi(SMT, _payload(description="Sosial", lembaga_perorangan="Besar", amount_request=9000))
    create_transaksi(SMT, _payload(description="Sosial", lembaga_perorangan="Sedang", amount_request=500))
    data = get_sponsorship_report(SMT, "2026", "all")
    rows = data["sections"][0]["rows"]
    assert [r["lembaga_perorangan"] for r in rows] == ["Besar", "Sedang", "Kecil"]
    assert [r["no"] for r in rows] == [1, 2, 3]


def test_report_cat4_include_only_returns_include_rows(app):
    _seed()
    create_transaksi(SMT, _payload(lembaga_perorangan="A", amount_request=100))  # blank cat4
    inc = create_transaksi(SMT, _payload(lembaga_perorangan="B", amount_request=200))
    update_transaksi(inc["id"], {"cat4": "Include"})
    exc = create_transaksi(SMT, _payload(lembaga_perorangan="C", amount_request=300))
    update_transaksi(exc["id"], {"cat4": "Exclude"})
    data = get_sponsorship_report(SMT, "2026", "include")
    lembaga = [r["lembaga_perorangan"] for r in data["sections"][0]["rows"]]
    assert lembaga == ["B"]


def test_report_cat4_exclude_only_returns_exclude_rows(app):
    _seed()
    inc = create_transaksi(SMT, _payload(lembaga_perorangan="B", amount_request=200))
    update_transaksi(inc["id"], {"cat4": "Include"})
    exc = create_transaksi(SMT, _payload(lembaga_perorangan="C", amount_request=300))
    update_transaksi(exc["id"], {"cat4": "Exclude"})
    data = get_sponsorship_report(SMT, "2026", "exclude")
    lembaga = [r["lembaga_perorangan"] for r in data["sections"][0]["rows"]]
    assert lembaga == ["C"]


def test_report_cat4_all_includes_blank_cat4_rows(app):
    _seed()
    create_transaksi(SMT, _payload(lembaga_perorangan="Blank", amount_request=100))  # blank cat4
    inc = create_transaksi(SMT, _payload(lembaga_perorangan="Inc", amount_request=200))
    update_transaksi(inc["id"], {"cat4": "Include"})
    data_all = get_sponsorship_report(SMT, "2026", "all")
    lembaga_all = {r["lembaga_perorangan"] for r in data_all["sections"][0]["rows"]}
    assert lembaga_all == {"Blank", "Inc"}
    data_include = get_sponsorship_report(SMT, "2026", "include")
    lembaga_inc = {r["lembaga_perorangan"] for r in data_include["sections"][0]["rows"]}
    assert lembaga_inc == {"Inc"}


def test_report_subtotal_and_grand_total(app):
    _seed()
    create_transaksi(SMT, _payload(description="Sosial", cat1="SMART", amount_request=1000))
    create_transaksi(SMT, _payload(description="Sosial", cat1="IKPP", amount_request=2000))
    create_transaksi(SMT, _payload(description="Akademisi", cat1="SMART", amount_request=500))
    data = get_sponsorship_report(SMT, "2026", "all")
    sosial = next(s for s in data["sections"] if s["description"] == "Sosial")
    assert sosial["subtotal"]["total"] == 3000
    assert sosial["subtotal"]["agri_amount"] == 1000
    assert sosial["subtotal"]["app_amount"] == 2000
    assert data["grand_total"]["total"] == 3500


def test_report_pct_allocation_sums_correctly(app):
    _seed()
    create_transaksi(SMT, _payload(cat1="SMART", amount_request=6000))  # AGRI
    create_transaksi(SMT, _payload(cat1="IKPP", amount_request=4000))   # APP
    data = get_sponsorship_report(SMT, "2026", "all")
    pct = data["pct_allocation"]
    assert pct["agri_amount"] == 60
    assert pct["app_amount"] == 40
    assert pct["energy_finance_amount"] == 0
    assert pct["property_amount"] == 0


def test_report_pct_allocation_zero_when_no_data(app):
    _seed()
    data = get_sponsorship_report(SMT, "2026", "all")
    assert data["sections"] == []
    assert data["grand_total"]["total"] == 0
    assert all(v == 0 for v in data["pct_allocation"].values())


def test_report_filters_by_year(app):
    _seed()
    create_transaksi(SMT, _payload(tanggal_form_sponsor="2025-06-01", amount_request=1000))
    create_transaksi(SMT, _payload(tanggal_form_sponsor="2026-06-01", amount_request=2000))
    data = get_sponsorship_report(SMT, "2026", "all")
    assert data["grand_total"]["total"] == 2000


def test_report_respects_company_scope(app):
    _seed()
    create_transaksi(SMT, _payload(amount_request=1000))
    create_transaksi(2, _payload(amount_request=99999))
    data = get_sponsorship_report(SMT, "2026", "all")
    assert data["grand_total"]["total"] == 1000


def test_report_shows_out_of_whitelist_description_as_own_section(app):
    # Simulates a migrated/historical row with a description value that
    # _validate_payload() would reject for new inserts (see service.py:67-68) —
    # spec §8 requires it still appear as its own section, not disappear.
    _seed()
    created = create_transaksi(SMT, _payload(description="Sosial", amount_request=1000))
    from database import get_conn
    conn = get_conn()
    conn.execute("UPDATE sponsorship_transaksi SET description = ? WHERE id = ?",
                 ("Legacy Category Not In List", created["id"]))
    conn.commit()
    conn.close()
    data = get_sponsorship_report(SMT, "2026", "all")
    descriptions = [s["description"] for s in data["sections"]]
    assert "Legacy Category Not In List" in descriptions
    legacy_section = next(s for s in data["sections"] if s["description"] == "Legacy Category Not In List")
    assert legacy_section["subtotal"]["total"] == 1000


def _rows(data):
    return sorted(r["lembaga_perorangan"] for s in data["sections"] for r in s["rows"])


def _seed_months():
    _seed()
    for lem, tgl, cat4 in (("Jan Org", "2026-01-15", "Include"), ("Feb Org", "2026-02-10", "Include"),
                           ("Mar Org", "2026-03-05", "Exclude"), ("Jan Excl", "2026-01-20", "Exclude"),
                           ("Jan 2025 Org", "2025-01-20", "Include")):
        create_transaksi(SMT, _payload(lembaga_perorangan=lem, tanggal_form_sponsor=tgl, cat4=cat4))


def test_normalise_bulan_and_month_label():
    assert normalise_bulan(["1", "01", 2, "12", "13", "0", "x", "", None]) == ["01", "02", "12"]
    assert normalise_bulan(None) == [] and normalise_bulan("3") == ["03"] and normalise_bulan(7) == ["07"]
    assert month_label(["03", "01"]) == "Jan, Mar" and month_label([]) == "" and month_label(None) == ""
    assert month_label(["05", "08", "12"]) == "Mei, Agu, Des"


def test_report_month_filter_uses_tgl_form():
    _seed_months()
    data = get_sponsorship_report(SMT, ["2026"], "all", ["01"])
    assert _rows(data) == ["Jan Excl", "Jan Org"]
    assert data["bulan"] == ["01"] and data["bulan_label"] == "Jan"
    assert _rows(get_sponsorship_report(SMT, ["2026"], "all", ["01", "02"])) == ["Feb Org", "Jan Excl", "Jan Org"]
    assert _rows(get_sponsorship_report(SMT, ["2025", "2026"], "all", ["01"])) == \
        ["Jan 2025 Org", "Jan Excl", "Jan Org"]                       # years and months combine with AND


def test_report_without_month_is_unchanged():
    _seed_months()
    data = get_sponsorship_report(SMT, ["2026"], "all")
    assert _rows(data) == ["Feb Org", "Jan Excl", "Jan Org", "Mar Org"]
    assert data["bulan"] == [] and data["bulan_label"] == ""
    assert _rows(get_sponsorship_report(SMT, ["2026"], "all", None)) == _rows(data)


def test_report_month_filter_applies_in_every_cat4_mode():
    _seed_months()
    month = ["01"]
    assert _rows(get_sponsorship_report(SMT, ["2026"], "include", month)) == ["Jan Org"]
    assert _rows(get_sponsorship_report(SMT, ["2026"], "exclude", month)) == ["Jan Excl"]
    assert _rows(get_sponsorship_report(SMT, ["2026"], "all", month)) == ["Jan Excl", "Jan Org"]
    assert _rows(get_sponsorship_report(SMT, ["2026"], "bib_include", month)) == ["Jan Org"]


def test_report_invalid_months_are_ignored():
    _seed_months()
    data = get_sponsorship_report(SMT, ["2026"], "all", ["13", "0", "abc", ""])
    assert data["bulan"] == [] and len(_rows(data)) == 4


def test_report_month_without_matching_rows_is_empty():
    _seed_months()
    data = get_sponsorship_report(SMT, ["2026"], "all", ["12"])
    assert data["sections"] == [] and data["bulan_label"] == "Des"
