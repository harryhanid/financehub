import collections
import io
import os

import pytest

from modules.management_report import service as svc
from modules.management_report.ho_report import build_ho_report, period_label
from modules.management_report.parser import read_append1
from tests.test_mr_service import mkrow

SAMPLE = os.environ.get('MR_SAMPLE_XLSB',
                        r'C:\Users\25010160\Downloads\Management Report - MASTER.xlsb')


def _row(ho, section, row_id):
    sec = next(s for s in ho["sections"] if s["key"] == section)
    return next(r for r in sec["rows"] if r["id"] == row_id)


def seed(rows, meta=None):
    svc.save_upload(1, "m.xlsb", "u", rows, meta=meta)


def test_amounts_are_in_rp_000_and_roll_up_to_totals():
    seed([mkrow(cc="AAA", coa="70105120", bgt=3.2, pta=0.5, act=0.1),
          mkrow(cc="AAA", coa="70106200", bgt=53.3),
          mkrow(cc="AAA", coa="70106400", bgt=36.0)])
    ho = build_ho_report(1, "AAA")
    assert ho["has_data"] is True
    acc = _row(ho, "opex", 124)
    assert (acc["bgt"], acc["pta"], acc["act"]) == (3200.0, 500.0, 100.0)
    assert _row(ho, "opex", 137)["bgt"] == 3200.0           # Total - 701-05-xxx
    assert _row(ho, "opex", 143)["bgt"] == 89300.0          # Total - 701-06-xxx
    assert _row(ho, "opex", 263)["bgt"] == 92500.0 and _row(ho, "opex", 263)["grand"] is True
    assert _row(ho, "summary", 281)["bgt"] == 3200.0        # Rent, Tax, and License Expense
    assert _row(ho, "summary", 282)["bgt"] == 89300.0       # Transport & Travelling Expense
    assert _row(ho, "summary", 298)["bgt"] == 92500.0
    assert ho["unmapped"] == [] and ho["summary_missing"] == []


def test_cost_center_year_and_month_filters_apply_but_not_a_coa_filter():
    seed([mkrow(cc="AAA", coa="70105120", bgt=1.0, mm=1, yy=26),
          mkrow(cc="BBB", coa="70105120", bgt=2.0, mm=2, yy=26),
          mkrow(cc="BBB", coa="70105120", bgt=4.0, mm=2, yy=25)])
    assert _row(build_ho_report(1, "AAA"), "opex", 124)["bgt"] == 1000.0
    assert _row(build_ho_report(1, None), "opex", 124)["bgt"] == 7000.0      # All Cost Center
    assert _row(build_ho_report(1, None, mm=2), "opex", 124)["bgt"] == 6000.0
    assert _row(build_ho_report(1, None, yy=25), "opex", 124)["bgt"] == 4000.0
    assert build_ho_report(1, "AAA", mm=12)["has_data"] is False
    assert build_ho_report(2, "AAA")["has_data"] is False                    # other company


def test_coa_outside_the_template_is_unmapped_and_not_counted():
    seed([mkrow(cc="AAA", coa="71000110", bgt=0.0, act=-97.5), mkrow(cc="AAA", coa="70105120", bgt=1.0)])
    ho = build_ho_report(1, "AAA")
    assert ho["unmapped"] == [{"coa": "71000110", "label": None,
                               "bgt": 0.0, "pta": 0.0, "act": -97500.0}]
    assert _row(ho, "opex", 263)["act"] == 0.0


def test_listed_account_outside_every_group_total_is_unmapped():
    seed([mkrow(cc="AAA", coa="70101300", bgt=2.0)])          # 'Workshop Exp' sits below its group total
    ho = build_ho_report(1, "AAA")
    assert [u["coa"] for u in ho["unmapped"]] == ["70101300"]
    assert ho["unmapped"][0]["label"] == "Workshop Exp"
    assert _row(ho, "opex", 263)["bgt"] == 0.0


def test_account_missing_from_the_summary_is_reported():
    seed([mkrow(cc="AAA", coa="70102114", bgt=12.0, act=5.6),
          mkrow(cc="AAA", coa="70105120", bgt=1.0)])
    ho = build_ho_report(1, "AAA")
    assert _row(ho, "opex", 263)["bgt"] == 13000.0
    assert _row(ho, "summary", 298)["bgt"] == 1000.0
    assert ho["summary_missing"] == [{"coa": "70102114", "label": "NS BPJT TK (JKK & JKM) Allowance",
                                      "bgt": 12000.0, "pta": 0.0, "act": 5600.0}]


def test_titles_period_and_division_come_from_the_sync_metadata():
    seed([mkrow(cc="AAA", coa="70105120", bgt=1.0)],
         meta={"cc_names": {"AAA": "Alpha Unit"}, "period": "2026-08-31"})
    ho = build_ho_report(1, "AAA")
    assert ho["org"] == "President Office & ETF" and ho["location"].startswith("Head Office")
    assert ho["division"] == "Alpha Unit" and ho["period_label"] == "s/d Aug"
    summary = next(s for s in ho["sections"] if s["key"] == "summary")
    assert summary["title"] == "Budget 2026 - Operating Expense Summary (in Rp. 000)"
    assert build_ho_report(1, None)["division"] == "All"
    assert build_ho_report(1, "ZZZ")["division"] == "ZZZ"


def test_year_filter_drives_the_summary_title_and_missing_metadata_is_tolerated():
    seed([mkrow(cc="AAA", coa="70105120", bgt=1.0, yy=25)])
    ho = build_ho_report(1, "AAA", yy=25)
    assert ho["year"] == 2025 and ho["period_label"] == "" and ho["division"] == "AAA"
    summary = next(s for s in ho["sections"] if s["key"] == "summary")
    assert summary["title"].startswith("Budget 2025 - ")


def test_period_label():
    assert period_label("2026-08-31") == "s/d Aug"
    assert period_label("2026-12-01") == "s/d Dec"
    assert period_label(None) == "" and period_label("garbage") == ""


# ---------- real master workbook ----------

@pytest.fixture
def master():
    try:
        with open(SAMPLE, "rb") as f:
            return f.read()
    except OSError:
        pytest.skip("sample master workbook not available")


def _sheet(data, name):
    from pyxlsb import open_workbook
    with open_workbook(io.BytesIO(data)) as wb:
        with wb.get_sheet(name) as sh:
            return [[c.v for c in r] for r in sh.rows()]


def test_every_computed_cell_matches_the_excel_ho_sheet(master):
    report = _sheet(master, "Report")
    cc, yy, mm = report[3][1], report[4][1], report[5][1]       # page filters B4:B6
    rows = read_append1(io.BytesIO(master)).rows
    if yy != "All" or mm != "All" or (cc != "All" and cc not in {r["cc"] for r in rows}):
        pytest.skip("master workbook is filtered by YY/MM or several CCs; reconciliation needs one CC")
    svc.save_upload(1, "m.xlsb", "u", rows)
    ho = build_ho_report(1, None if cc == "All" else cc)
    sheet = _sheet(master, "BGT HO Report per CC")
    checked = 0
    for s in ho["sections"]:
        for r in s["rows"]:
            if "bgt" not in r:
                continue
            expected = [float(v) if isinstance(v, (int, float)) else 0.0
                        for v in sheet[r["id"] - 1][3:6]]        # columns D:F of the Excel row
            assert [r["bgt"], r["pta"], r["act"]] == pytest.approx(expected, abs=1e-3), \
                (s["key"], r["id"], r.get("label"))
            checked += 1
    assert checked >= 240


def test_invariants_hold_for_every_cost_center(master):
    rows = read_append1(io.BytesIO(master)).rows
    svc.save_upload(1, "m.xlsb", "u", rows)
    for cc in sorted({r["cc"] for r in rows}) + [None]:
        raw = collections.defaultdict(float)
        for r in rows:
            if cc is None or r["cc"] == cc:
                for key in ("bgt", "pta", "act"):
                    raw[key] += r[key] * 1000
        ho = build_ho_report(1, cc)
        grand = {s["key"]: next(r for r in s["rows"] if r.get("grand")) for s in ho["sections"]}
        for key in ("bgt", "pta", "act"):
            unmapped = sum(u[key] for u in ho["unmapped"])
            missing = sum(m[key] for m in ho["summary_missing"])
            assert raw[key] == pytest.approx(
                grand["capex"][key] + grand["opex"][key] + unmapped, abs=1e-3), (cc, key)
            assert grand["opex"][key] == pytest.approx(
                grand["summary"][key] + missing, abs=1e-3), (cc, key)
