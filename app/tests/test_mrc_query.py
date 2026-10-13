from modules.management_report import combine_query as cq


def row(i, cc="AAA", source="SMT", mm=1, act=1.0, dc=1000000.0, **kw):
    r = {"coa": "70108100", "mm": mm, "yy": 2026, "cc": cc, "category": "10 - X", "activity": "Act",
         "description": f"row {i}", "custom": "3", "mm1": mm, "pta": 0.0, "bgt": 0.0, "act": act,
         "source": source, "account": "6-1810", "unmapped": False, "id_no": f"GJ-{i}", "tgl": "2026-01-15",
         "allocation_memo": f"memo {i}", "debit_credit": dc, "cost_center2": "$X", "cc0": "26", "cc1": 1,
         "bc1": "-10-", "new_code": f"A26-1-10-{i}", "cc_unmapped": False}
    r.update(kw)
    return r


ROWS = [row(i, cc="AAA" if i % 2 else "BBB", source=("SMT", "ETF", "Sponsor")[i % 3]) for i in range(1, 251)]


def test_list_ccs_sorted_unique():
    assert cq.list_ccs(ROWS) == ["AAA", "BBB"]


def test_pagination_keeps_build_order():
    r = cq.query_data(ROWS, page=1)
    assert r["total"] == 250 and r["pages"] == 3 and [x["id_no"] for x in r["rows"]][:3] == ["GJ-1", "GJ-2", "GJ-3"]
    assert len(cq.query_data(ROWS, page=3)["rows"]) == 50
    assert cq.query_data(ROWS, page=999)["page"] == 3 and cq.query_data(ROWS, page=0)["page"] == 1


def test_source_filter_and_invalid_source():
    sponsor = cq.query_data(ROWS, source="Sponsor")
    assert sponsor["total"] == sum(1 for r in ROWS if r["source"] == "Sponsor")
    assert cq.query_data(ROWS, source="NOPE")["total"] == 250 and cq.query_data(ROWS, source="")["total"] == 250


def test_search_fields_and_cc_filter():
    assert cq.query_data(ROWS, q="GJ-17")["total"] == 11            # GJ-17, GJ-170..GJ-179
    assert cq.query_data(ROWS, q="a26-1-10-25")["total"] == 2       # new_code, case-insensitive: A26-1-10-25 and ...-250
    assert cq.query_data(ROWS, q="memo 250")["total"] == 1          # allocation_memo
    assert cq.query_data(ROWS, cc="AAA")["total"] == 125
    assert cq.query_data(ROWS, q="no-such")["rows"] == []


def test_totals_follow_the_filter_and_never_negative_zero():
    r = cq.query_data([row(1, act=0.3, dc=300000.0), row(2, act=-0.1, dc=-100000.0), row(3, act=-0.2, dc=-200000.0)])
    assert r["sum_act"] == 0.0 and str(r["sum_act"]) == "0.0" and r["sum_dc"] == 0.0 and str(r["sum_dc"]) == "0.0"


def test_empty():
    r = cq.query_data([])
    assert r["total"] == 0 and r["pages"] == 1 and r["sum_act"] == 0.0 and r["sum_dc"] == 0.0
