from modules.sponsorship.service import seed_perusahaan, create_transaksi, get_dashboard_data

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


def test_dashboard_summary_totals(app):
    _seed()
    create_transaksi(SMT, _payload(amount_request=1000000))
    create_transaksi(SMT, _payload(amount_request=2000000, cat1="IKPP", description="Media"))
    data = get_dashboard_data(SMT)
    assert data["summary"]["total_amount"] == 3000000
    assert data["summary"]["total_count"] == 2


def test_dashboard_monthly_chart(app):
    _seed()
    create_transaksi(SMT, _payload(tanggal_form_sponsor="2026-01-10", amount_request=500))
    create_transaksi(SMT, _payload(tanggal_form_sponsor="2026-02-20", amount_request=700))
    data = get_dashboard_data(SMT)
    months = {row["month"]: row["amount"] for row in data["monthlyChart"]}
    assert months["2026-01"] == 500
    assert months["2026-02"] == 700


def test_dashboard_pillar_chart_covers_all_four_pillars(app):
    _seed()
    create_transaksi(SMT, _payload(cat1="SMART", amount_request=1000))  # AGRI
    data = get_dashboard_data(SMT)
    pillars = {row["pillar"]: row["amount"] for row in data["pillarChart"]}
    assert pillars["AGRI"] == 1000
    assert pillars["APP"] == 0
    assert pillars["ENERGY & FINANCE"] == 0
    assert pillars["PROPERTY"] == 0


def test_dashboard_description_chart(app):
    _seed()
    create_transaksi(SMT, _payload(description="Sosial", amount_request=1000))
    create_transaksi(SMT, _payload(description="Media", amount_request=500, cat1="IKPP"))
    data = get_dashboard_data(SMT)
    desc = {row["description"]: row["amount"] for row in data["descriptionChart"]}
    assert desc["Sosial"] == 1000
    assert desc["Media"] == 500
    assert desc["Akademisi"] == 0  # untouched categories still present at 0


def test_dashboard_respects_company_scope(app):
    _seed()
    create_transaksi(SMT, _payload(amount_request=1000))
    create_transaksi(2, _payload(amount_request=99999))
    data = get_dashboard_data(SMT)
    assert data["summary"]["total_amount"] == 1000


def test_dashboard_respects_filters(app):
    _seed()
    create_transaksi(SMT, _payload(tanggal_form_sponsor="2025-06-01", amount_request=1000))
    create_transaksi(SMT, _payload(tanggal_form_sponsor="2026-06-01", amount_request=2000))
    data = get_dashboard_data(SMT, filters={"tahun": "2026"})
    assert data["summary"]["total_amount"] == 2000

def test_dashboard_cat_mix_splits_sponsorship_and_csr_gedung(app):
    _seed()
    create_transaksi(SMT, _payload(cat="Sponsorship", cat1="SMART", amount_request=1000))
    create_transaksi(SMT, _payload(cat="CSR Gedung", cat1="IKPP", amount_request=2000))
    data = get_dashboard_data(SMT)
    mix = {row["cat"]: row["amount"] for row in data["catMix"]}
    assert mix["Sponsorship"] == 1000
    assert mix["CSR Gedung"] == 2000


def test_dashboard_yoy_growth_computes_percent_change(app):
    _seed()
    create_transaksi(SMT, _payload(tanggal_form_sponsor="2024-03-01", amount_request=1000))
    create_transaksi(SMT, _payload(tanggal_form_sponsor="2025-03-01", amount_request=1500))
    create_transaksi(SMT, _payload(tanggal_form_sponsor="2026-03-01", amount_request=1200))
    data = get_dashboard_data(SMT)
    rows = {row["year"]: row for row in data["yoyGrowth"]}
    assert rows["2024"]["amount"] == 1000
    assert rows["2024"]["growth_pct"] is None
    assert rows["2025"]["amount"] == 1500
    assert round(rows["2025"]["growth_pct"], 2) == 50.0
    assert rows["2026"]["amount"] == 1200
    assert round(rows["2026"]["growth_pct"], 2) == -20.0


def test_dashboard_yoy_growth_empty_when_no_data(app):
    _seed()
    data = get_dashboard_data(SMT)
    assert data["yoyGrowth"] == []


def test_dashboard_cat4_mix_splits_include_and_exclude(app):
    _seed()
    create_transaksi(SMT, _payload(cat1="SMART", cat4="Include", amount_request=1000))
    create_transaksi(SMT, _payload(cat1="IKPP", cat4="Exclude", amount_request=2000))
    data = get_dashboard_data(SMT)
    mix = {row["cat4"]: row["amount"] for row in data["cat4Mix"]}
    assert mix["Include"] == 1000
    assert mix["Exclude"] == 2000


def test_dashboard_cat4_mix_ignores_blank_cat4(app):
    _seed()
    create_transaksi(SMT, _payload(cat1="SMART", amount_request=1000))  # no cat4 set
    data = get_dashboard_data(SMT)
    mix = {row["cat4"]: row["amount"] for row in data["cat4Mix"]}
    assert mix["Include"] == 0
    assert mix["Exclude"] == 0
