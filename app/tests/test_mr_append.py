from modules.management_report import service as svc
from tests.test_mr_service import mkrow

COLUMNS = ["coa", "mm", "yy", "cc", "category", "activity", "description",
           "pta", "custom", "mm1", "act", "bgt"]


def seed(rows, company=1):
    svc.save_upload(company, "m.xlsb", "u", rows)


def rows3():
    return [
        mkrow(cc="AAA", coa="111", mm=1, yy=26, description="Alpha rent", activity="Ops",
              category="01 - Rental", bgt=1.0),
        mkrow(cc="AAA", coa="222", mm=2, yy=26, description="Beta travel", category="", bgt=2.0),
        mkrow(cc="BBB", coa="111", mm=2, yy=25, description="100% donation_x", category="", bgt=3.0),
    ]


def test_all_rows_come_back_in_insertion_order_with_the_append_columns():
    seed(rows3())
    res = svc.query_append(1)
    assert res["total"] == 3
    assert [r["description"] for r in res["rows"]] == ["Alpha rent", "Beta travel", "100% donation_x"]
    assert list(res["rows"][0]) == COLUMNS
    assert res["rows"][0]["bgt"] == 1.0 and res["rows"][0]["cc"] == "AAA"


def test_filters_cc_year_month_and_coa():
    seed(rows3())
    assert svc.query_append(1, cc="AAA")["total"] == 2
    assert svc.query_append(1, yy=25)["total"] == 1
    assert svc.query_append(1, mm=2)["total"] == 2
    assert svc.query_append(1, coas=["111"])["total"] == 2
    assert svc.query_append(1, coas=["111", "222"])["total"] == 3
    assert svc.query_append(1, coas=[])["total"] == 3                  # empty = no COA filter
    assert svc.query_append(1, cc="AAA", mm=2, coas=["222"])["total"] == 1
    assert svc.query_append(1, cc="NOPE")["rows"] == []


def test_search_is_case_insensitive_over_text_columns_and_wildcards_are_literal():
    seed(rows3())
    q = lambda text: [r["description"] for r in svc.query_append(1, q=text)["rows"]]
    assert q("RENT") == ["Alpha rent"]
    assert q("beta") == ["Beta travel"]
    assert q("01 - rental") == ["Alpha rent"]                         # category
    assert q("ops") == ["Alpha rent"]                                 # activity
    assert len(q("111")) == 2                                         # coa
    assert q("%") == ["100% donation_x"]                              # literal percent sign
    assert q("_x") == ["100% donation_x"]                             # literal underscore
    assert q("zzz") == []


def test_paging_keeps_the_total_of_the_whole_filter():
    seed([mkrow(cc="AAA", description=f"row {i}") for i in range(5)])
    first = svc.query_append(1, limit=2, offset=0)
    assert first["total"] == 5 and [r["description"] for r in first["rows"]] == ["row 0", "row 1"]
    last = svc.query_append(1, limit=2, offset=4)
    assert last["total"] == 5 and [r["description"] for r in last["rows"]] == ["row 4"]
    assert svc.query_append(1, limit=2, offset=10)["rows"] == []


def test_no_snapshot_and_company_isolation():
    assert svc.query_append(1) == {"rows": [], "total": 0}
    seed(rows3(), company=2)
    assert svc.query_append(1) == {"rows": [], "total": 0}
    assert svc.query_append(2)["total"] == 3
    seed([mkrow(cc="NEW", description="only in the new snapshot")], company=2)
    assert [r["cc"] for r in svc.query_append(2)["rows"]] == ["NEW"]   # active snapshot only
