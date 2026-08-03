path_service = r"C:\Financehub\app\modules\sponsorship\service.py"
with open(path_service, "r", encoding="utf-8") as f:
    service = f.read()

import re

old_block = """    # Status Chart
    status_totals = {}
    for r in rows:
        s = r["status"] or "Unknown"
        status_totals[s] = status_totals.get(s, 0) + r["amount_request"]
    status_chart = [{"status": k, "amount": v} for k, v in status_totals.items()]

    return {"""

new_block = """    # Status Chart
    status_totals = {}
    for r in rows:
        s = r["status"] or "Unknown"
        status_totals[s] = status_totals.get(s, 0) + r["amount_request"]
    status_chart = [{"status": k, "amount": v} for k, v in status_totals.items()]

    # Cat Mix (Sponsorship vs CSR Gedung)
    cat_totals = {c: 0.0 for c in config.SPONSORSHIP_CAT}
    for r in rows:
        if r["cat"] in cat_totals:
            cat_totals[r["cat"]] += r["amount_request"]
    cat_mix = [{"cat": c, "amount": cat_totals[c]} for c in config.SPONSORSHIP_CAT]

    # YoY Growth
    year_totals = {}
    for r in rows:
        y = r["tanggal_form_sponsor"][:4]
        if y:
            year_totals[y] = year_totals.get(y, 0.0) + r["amount_request"]
    yoy_growth = []
    prev_amount = None
    for y in sorted(year_totals):
        amount = year_totals[y]
        if prev_amount is None or prev_amount == 0:
            growth_pct = None
        else:
            growth_pct = (amount - prev_amount) / prev_amount * 100
        yoy_growth.append({"year": y, "amount": amount, "growth_pct": growth_pct})
        prev_amount = amount

    return {"""

service = service.replace(old_block, new_block)
service = service.replace(
"""        "statusChart": status_chart,
    }""",
"""        "statusChart": status_chart,
        "catMix": cat_mix,
        "yoyGrowth": yoy_growth,
    }"""
)

with open(path_service, "w", encoding="utf-8") as f:
    f.write(service)


path_tests = r"C:\Financehub\app\tests\test_sponsorship_dashboard_service.py"
with open(path_tests, "r", encoding="utf-8") as f:
    ts = f.read()

new_tests = """
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
"""
if "def test_dashboard_cat_mix" not in ts:
    ts += new_tests
    with open(path_tests, "w", encoding="utf-8") as f:
        f.write(ts)

print("done task 2")
