# tests/test_gl_mr_report.py
from modules.general_ledger import mr_report as rep
from modules.general_ledger.mr_rows import UNMAPPED


def mr(category="10 - Office", cc="AAA", mm=1, description="d", act=1.0, activity="Act",
       custom="3", source="SMT", bgt=0.0, pta=0.0, id_no="GJ-1", new_code="A26-1-10-1",
       allocation_memo="memo"):
    return {"coa": "70108100", "mm": mm, "yy": 2026, "cc": cc, "category": category,
            "activity": activity, "description": description, "custom": custom, "mm1": mm,
            "pta": pta, "bgt": bgt, "act": act, "source": source, "account": "6-1810",
            "unmapped": category == UNMAPPED, "id_no": id_no, "new_code": new_code,
            "allocation_memo": allocation_memo}


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
    assert r["grand"]["act"] == 16.5


def test_cost_center_filter():
    r = rep.build_report(ROWS, "BBB")
    assert [g["category"] for g in r["groups"]] == ["10 - Office"] and r["grand"]["act"] == 2.0 and r["cc"] == "BBB"
    empty = rep.build_report(ROWS, "ZZZ")
    assert empty["has_data"] is False and empty["groups"] == [] and empty["grand"]["act"] == 0.0


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


def test_totals_netting_to_zero_are_never_negative_zero():
    import math
    rows = [mr(act=0.3), mr(act=-0.1), mr(act=-0.2)]
    r = rep.build_report(rows)
    vals = [r["groups"][0]["lines"][0]["act"], r["groups"][0]["total"], r["grand"]["act"]]
    for v in vals:
        assert abs(v) < 1e-9 and math.copysign(1, v) > 0, v
    assert math.copysign(1, rep.query_data(rows)["sum_act"]) > 0


def test_report_metrics_for_gl_only_data():
    r = rep.build_report(ROWS)
    office = r["groups"][1]
    line = office["lines"][0]
    assert (line["bgt"], line["pta"], line["available"], line["act"], line["diff"], line["pct"]) == (
        0.0, 0.0, 0.0, 3.0, 3.0, None)
    for node in (office, r["groups"][0], r["grand"]):
        assert (node["bgt"], node["pta"], node["available"]) == (0.0, 0.0, 0.0)
        assert node["diff"] == node["act"] and node["pct"] is None
    assert r["grand"]["act"] == 16.5 and r["grand"]["diff"] == 16.5 and r["grand"]["pct"] is None
    assert office["act"] == 3.5


def test_report_metrics_with_budget_and_percentage():
    rows = [mr(act=6.0, bgt=10.0, pta=2.0), mr(act=1.0, bgt=0.0, pta=0.0, description="e")]
    r = rep.build_report(rows)
    g = r["groups"][0]
    first = [l for l in g["lines"] if l["description"] == "d"][0]
    assert (first["bgt"], first["pta"], first["available"], first["act"], first["diff"]) == (
        10.0, 2.0, 12.0, 6.0, -6.0)
    assert first["pct"] == -50.0                       # diff / available * 100
    assert (g["bgt"], g["pta"], g["available"], g["act"], g["diff"], g["pct"]) == (
        10.0, 2.0, 12.0, 7.0, -5.0, round(-5.0 / 12.0 * 100, 6))
    assert r["grand"]["available"] == 12.0 and r["grand"]["diff"] == -5.0


def test_report_metrics_never_negative_zero():
    import math
    r = rep.build_report([mr(act=0.3), mr(act=-0.1), mr(act=-0.2)])
    for node in (r["groups"][0]["lines"][0], r["groups"][0], r["grand"]):
        for k in ("bgt", "pta", "available", "act", "diff"):
            assert math.copysign(1, node[k]) > 0, (k, node[k])


def test_data_keeps_build_order_not_a_resort():
    rows = [mr(mm=2, source="ETF", cc="ZZZ", description="z", id_no="X1"),
            mr(mm=1, source="SMT", cc="AAA", description="a", id_no="X2"),
            mr(mm=2, source="SMT", cc="MMM", description="m", id_no="X3")]
    assert [r["id_no"] for r in rep.query_data(rows)["rows"]] == ["X1", "X2", "X3"]


def test_data_search_covers_id_new_code_and_allocation_memo():
    rows = [mr(id_no="GJ-0042", new_code="A26-16-10-1", allocation_memo="Zoom", description="x"),
            mr(id_no="GJ-0099", new_code="A26-3-20-7", allocation_memo="ATK", description="y")]
    assert [r["id_no"] for r in rep.query_data(rows, q="gj-0042")["rows"]] == ["GJ-0042"]
    assert [r["id_no"] for r in rep.query_data(rows, q="A26-3-20")["rows"]] == ["GJ-0099"]
    assert [r["id_no"] for r in rep.query_data(rows, q="zoom")["rows"]] == ["GJ-0042"]
    assert rep.query_data(rows, q="GJ-")["total"] == 2
