# tests/test_gl_mr_report.py
from modules.general_ledger import mr_report as rep
from modules.general_ledger.mr_rows import UNMAPPED


def mr(category="10 - Office", cc="AAA", mm=1, description="d", act=1.0, activity="Act",
       custom="3", source="SMT"):
    return {"coa": "70108100", "mm": mm, "yy": 2026, "cc": cc, "category": category,
            "activity": activity, "description": description, "custom": custom, "mm1": mm,
            "pta": 0.0, "bgt": 0.0, "act": act, "source": source, "account": "6-1810",
            "unmapped": category == UNMAPPED}


ROWS = [mr("10 - Office", "AAA", 1, "d1", 1.0), mr("10 - Office", "BBB", 1, "d1", 2.0),
        mr("10 - Office", "AAA", 2, "d2", 0.5), mr("06 - Gift", "AAA", 1, "g", 4.0),
        mr(UNMAPPED, "AAA", 1, "u", 9.0)]


def test_groups_lines_and_totals():
    r = rep.build_report(ROWS)
    assert r["has_data"] is True and r["cc"] is None
    assert [g["category"] for g in r["groups"]] == ["06 - Gift", "10 - Office", UNMAPPED]
    office = r["groups"][1]
    assert [(l["mm1"], l["description"], l["act"]) for l in office["lines"]] == [
        (1, "d1", 3.0), (2, "d2", 0.5)]
    assert office["total"] == 3.5
    assert r["grand"] == 16.5


def test_cost_center_filter():
    r = rep.build_report(ROWS, "BBB")
    assert [g["category"] for g in r["groups"]] == ["10 - Office"] and r["grand"] == 2.0 and r["cc"] == "BBB"
    empty = rep.build_report(ROWS, "ZZZ")
    assert empty["has_data"] is False and empty["groups"] == [] and empty["grand"] == 0.0


def test_empty_rows():
    assert rep.build_report([])["has_data"] is False


def test_list_ccs_is_sorted_and_unique():
    assert rep.list_ccs(ROWS) == ["AAA", "BBB"]


def many(n=250):
    return [mr(description=f"row {i}", act=1.0, mm=1 + i % 3, cc="AAA" if i % 2 else "BBB")
            for i in range(1, n + 1)]


def test_data_pagination_and_totals():
    r = rep.query_data(many(), page=1)
    assert r["total"] == 250 and r["pages"] == 3 and len(r["rows"]) == 100 and r["sum_act"] == 250.0
    assert len(rep.query_data(many(), page=3)["rows"]) == 50
    assert rep.query_data(many(), page=999)["page"] == 3
    assert rep.query_data(many(), page=0)["page"] == 1


def test_data_search_and_cc_filter():
    assert rep.query_data(many(), q="row 17")["total"] == 11          # row 17 and row 170-179
    assert rep.query_data(many(), q="ROW 17")["total"] == 11          # case-insensitive
    assert rep.query_data(many(), cc="AAA")["total"] == 125
    assert rep.query_data(many(), q="no-such")["rows"] == []


def test_data_empty():
    r = rep.query_data([])
    assert r["total"] == 0 and r["pages"] == 1 and r["sum_act"] == 0.0
