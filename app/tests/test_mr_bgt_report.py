from datetime import date

import pytest

from modules.management_report.bgt_report import (build_bgt_report, clean_category, month_of,
                                                   pick_period)


def row(coa, category, description, mm1, bgt=0.0, pta=0.0, act=0.0, yy=26, mm=None):
    return dict(coa=coa, mm=mm if mm is not None else mm1, yy=yy, cc="AAA", category=category,
                activity="Operational", description=description, pta=pta, custom="1",
                mm1=mm1, act=act, bgt=bgt)


ROWS = [
    row("70105120", "01 - Rental, Tax", "Rent", 1, bgt=10, act=4),
    row("70105120", "01 - Rental, Tax", "Rent", 9, bgt=6),
    row("70106100", "02 - Transport", "Taxi", 2, bgt=3, pta=1),
    row("27004100", "21 - Office Furniture & Fixture", "Chair", 2, bgt=5, pta=2),
]


def test_clean_category_drops_the_number_prefix():
    assert clean_category("01 - Rental, Tax & License Expense") == "Rental, Tax & License Expense"
    assert clean_category("Plain") == "Plain"
    assert clean_category(None) == "(no category)"


def test_month_of_prefers_mm1_then_mm():
    assert month_of({"mm1": 4, "mm": 5}) == 4
    assert month_of({"mm1": None, "mm": 5}) == 5
    assert month_of({"mm1": 0, "mm": None}) is None


def test_period_priority_mm_then_meta_then_latest_act_then_12():
    assert pick_period(ROWS, 26, 8, "2026-03-31") == 8
    assert pick_period(ROWS, 26, None, "2026-03-31") == 3
    assert pick_period(ROWS, 26, None, "2025-03-31") == 1          # meta year differs -> latest month with ACT
    assert pick_period(ROWS, 26, None, None) == 1
    assert pick_period([row("1", "c", "d", 2, bgt=1)], 26, None, None) == 12


def test_out_of_range_mm_is_ignored():
    for bad in (0, 13, -1):
        assert pick_period(ROWS, 26, bad, "2026-03-31") == pick_period(ROWS, 26, None, "2026-03-31") == 3
        assert pick_period(ROWS, 26, bad, None) == 1
    assert build_bgt_report(ROWS, None, 13)["period"] == 1


def test_structure_levels_categories_and_details():
    rep = build_bgt_report(ROWS, None, 8)
    assert rep["has_data"] and rep["year"] == 26 and rep["year4"] == 2026 and rep["period"] == 8
    assert rep["period_date"] == date(2026, 8, 31)
    assert [l["label"] for l in rep["levels"]] == ["OPEX", "CAPEX"]
    opex, capex = rep["levels"]
    assert [c["label"] for c in opex["categories"]] == ["Rental, Tax", "Transport"]
    assert [c["label"] for c in capex["categories"]] == ["Office Furniture & Fixture"]
    rental = opex["categories"][0]
    assert [d["text"] for d in rental["details"]] == [
        "- Bgt 2026 : Rent Month : 1", "- Bgt 2026 : Rent Month : 9", "- Act 2026 : Rent Month : 1"]
    d1, d9, a1 = rental["details"]
    assert (d1["coa"], d1["d"], d1["e"], d1["f"], d1["i"]) == ("70105120", 10, 10, None, None)
    assert (d9["d"], d9["e"]) == (6, 0)                              # month 9 is after the period
    assert (a1["d"], a1["e"], a1["f"], a1["i"]) == (None, None, None, 4)


def test_metrics_full_year_ytd_and_percentages():
    rep = build_bgt_report(ROWS, None, 8)
    m = rep["levels"][0]["m"]
    assert (m["d"], m["e"], m["f"], m["g"], m["i"]) == (19, 13, 1, 14, 4)
    assert m["j"] == -10 and m["k"] == pytest.approx(-10 / 14)
    assert m["m"] == 15 and m["n"] == pytest.approx(15 / 19)
    cat = rep["levels"][0]["categories"][0]["m"]
    assert (cat["d"], cat["e"], cat["f"], cat["i"]) == (16, 10, 0, 4)
    capex = rep["levels"][1]["m"]
    assert (capex["d"], capex["e"], capex["f"], capex["g"], capex["i"], capex["j"], capex["m"]) == (5, 5, 2, 7, 0, -7, 5)


def test_zero_divisors_give_none():
    rep = build_bgt_report([row("70105120", "01 - A", "x", 1, act=3)], None, 1)
    m = rep["levels"][0]["m"]
    assert m["d"] == 0 and m["g"] == 0 and m["k"] is None and m["n"] is None


def test_other_years_are_ignored_and_default_year_is_latest():
    rows = ROWS + [row("70105120", "01 - Rental, Tax", "Old", 1, bgt=99, yy=25)]
    rep = build_bgt_report(rows, None, 8)
    assert rep["year"] == 26 and rep["levels"][0]["m"]["d"] == 19
    assert build_bgt_report(rows, 25, 8)["levels"][0]["m"]["d"] == 99


def test_empty_rows_give_no_levels():
    rep = build_bgt_report([], None, None)
    assert rep["has_data"] is False and rep["levels"] == [] and rep["period"] is None
    assert rep["period_date"] is None and rep["year"] is None


def test_description_that_already_has_the_prefix_is_not_prefixed_again():
    # In the real Append the description already reads '- Bgt 2026 : <text> Month : n'
    rows = [row("70104400", "01 - A", "- Bgt 2026 : Freight Insurance Month : 9", 9, bgt=1.3),
            row("70104400", "01 - A", "- Pta 2026 : Booth Month : 7", 7, pta=2.0),
            row("70104400", "01 - A", "- Act 2026 : Biaya Gaji : 5 (DPP)", 3, act=4.0),
            row("70104400", "01 - A", "Plain text", 2, bgt=1.0)]
    texts = [d["text"] for d in build_bgt_report(rows, None, 9)["levels"][0]["categories"][0]["details"]]
    assert texts == ["- Bgt 2026 : Plain text Month : 2", "- Bgt 2026 : Freight Insurance Month : 9",
                     "- Pta 2026 : Booth Month : 7", "- Act 2026 : Biaya Gaji : 5 (DPP)"]
