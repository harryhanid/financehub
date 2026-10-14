# tests/test_gl_service.py
from modules.general_ledger import service as svc
from tests.test_gl_sync import mkrow


def seed():
    rows = [
        mkrow(entry_no=1, id_no="GJ-1", tgl="2026-01-02", debit=100.0, credit=0.0,
              acc_statutory="6-1810", job_name="POCFAD", memo="Zoom"),
        mkrow(entry_no=2, id_no="GJ-1", tgl="2026-01-02", debit=0.0, credit=100.0,
              acc_statutory="2-1110", job_name="POCFAD", memo="Zoom"),
        mkrow(entry_no=3, id_no="BK-7", tgl="2026-03-10", debit=50.0, credit=0.0,
              acc_statutory="6-2190", job_name="POITEC", memo="100% diskon_promo"),
    ]
    for r in rows:
        r["acc_management"] = r["acc_statutory"]
    svc.replace_year("smt", 2026, rows, dict(synced_by="u", filename="f", content_hash="h", rows_before=0,
                                      rows_after=3, total_debit=150.0, total_credit=100.0,
                                      dropped=0, summary={}))


def q(**f):
    return svc.query_rows("smt", f)


def test_no_filter_returns_all_ordered_with_totals():
    seed()
    r = q()
    assert r["total"] == 3 and [x["entry_no"] for x in r["rows"]] == [1, 2, 3]
    assert r["sum_debit"] == 150.0 and r["sum_credit"] == 100.0
    assert r["page"] == 1 and r["pages"] == 1


def test_filters():
    seed()
    assert q(date_from="2026-02-01")["total"] == 1
    assert q(date_to="2026-01-31")["total"] == 2
    assert q(acc="2-1110")["total"] == 1
    assert q(job="poit")["total"] == 1
    assert q(q="GJ-1")["total"] == 2
    assert q(q="zoom", job="POCFAD", acc="6-1810")["total"] == 1


def test_filtered_totals_follow_the_filter():
    seed()
    r = q(job="POCFAD")
    assert r["sum_debit"] == 100.0 and r["sum_credit"] == 100.0


def test_like_wildcards_are_literal():
    seed()
    assert q(q="%")["total"] == 1            # only the memo containing a literal '%'
    assert q(q="_")["total"] == 1            # only the memo containing a literal '_'
    assert q(q="no-such-text")["total"] == 0


def test_pagination_and_clamping():
    svc.replace_year("smt", 2026, [mkrow(entry_no=i, id_no=f"X-{i}") for i in range(1, 251)],
                    dict(synced_by="u", filename="f", content_hash="h", rows_before=0,
                         rows_after=250, total_debit=0, total_credit=0, dropped=0, summary={}))
    p1 = svc.query_rows("smt", {}, page=1)
    assert p1["pages"] == 3 and len(p1["rows"]) == 100
    assert len(svc.query_rows("smt", {}, page=3)["rows"]) == 50
    assert svc.query_rows("smt", {}, page=999)["page"] == 3
    assert svc.query_rows("smt", {}, page=0)["page"] == 1


def test_empty_table():
    r = svc.query_rows("etf", {})
    assert r["total"] == 0 and r["rows"] == [] and r["pages"] == 1 and r["sum_debit"] == 0


def test_year_filter_and_totals():
    seed()
    svc.replace_year("smt", 2025, [mkrow(entry_no=9, id_no="OLD", tgl="2025-06-06", debit=7.0)],
                     dict(synced_by="u", filename="f", content_hash="h25", rows_before=0, rows_after=1,
                          total_debit=7.0, total_credit=0, dropped=0, summary={}))
    assert q()["total"] == 4
    r = q(year=2025)
    assert r["total"] == 1 and r["sum_debit"] == 7.0
    assert q(year=2026)["total"] == 3
    assert q(year=2026, job="POITEC")["total"] == 1


def test_load_mr_source_defaults_to_the_latest_year():
    log = dict(synced_by="u", filename="f", content_hash="h", rows_before=0, rows_after=1,
               total_debit=0, total_credit=0, dropped=0, summary={})
    svc.replace_year("smt", 2025, [mkrow(id_no="OLD", tgl="2025-06-06", debit_credit=1.0)], log)
    svc.replace_year("smt", 2026, [mkrow(id_no="NEW", tgl="2026-06-06", debit_credit=2.0)], log)
    assert [r["id_no"] for r in svc.load_mr_source("smt")] == ["NEW"]
    assert [r["id_no"] for r in svc.load_mr_source("smt", 2025)] == ["OLD"]
    assert svc.load_mr_source("etf") == []


def test_account_totals_groups_by_account_and_year():
    log = dict(synced_by="u", filename="f", content_hash="h", rows_before=0, rows_after=1,
               total_debit=0, total_credit=0, dropped=0, summary={})
    svc.replace_year("smt", 2025, [mkrow(acc_statutory="6-1", tgl="2025-02-02", debit_credit=9.0)], log)
    svc.replace_year("smt", 2026, [
        mkrow(acc_statutory="6-1", tgl="2026-01-02", debit_credit=10.0),
        mkrow(acc_statutory="6-1", tgl="2026-01-03", debit_credit=-4.0),
        mkrow(acc_statutory="6-2", tgl="2026-01-04", debit_credit=1.0)], log)
    assert svc.account_totals("smt", 2026) == [{"account": "6-1", "n": 2, "amount": 6.0},
                                               {"account": "6-2", "n": 1, "amount": 1.0}]
    assert svc.account_totals("smt", 2025) == [{"account": "6-1", "n": 1, "amount": 9.0}]
    assert svc.account_totals("etf", 2026) == []


def test_load_lines_returns_the_year_with_ids_and_classification_columns():
    log = dict(synced_by="u", filename="f", content_hash="h", rows_before=0, rows_after=1,
               total_debit=0, total_credit=0, dropped=0, summary={})
    svc.replace_year("smt", 2025, [mkrow(id_no="OLD", tgl="2025-02-02")], log)
    svc.replace_year("smt", 2026, [
        mkrow(id_no="A", tgl="2026-01-02", debit=5.0, credit=0.0, debit_credit=5.0, category_lk="Beban Operasional",
              category_spt="BIAYA LAINNYA", pph_non_pph="PPh 21", accrual_actual="Actual"),
        mkrow(id_no="B", tgl="2026-01-03")], log)
    lines = svc.load_lines("smt", 2026)
    assert [l["id_no"] for l in lines] == ["A", "B"]
    first = lines[0]
    assert isinstance(first["id"], int) and first["debit"] == 5.0
    assert (first["category_lk"], first["category_spt"], first["pph_non_pph"], first["accrual_actual"]) == \
           ("Beban Operasional", "BIAYA LAINNYA", "PPh 21", "Actual")
    assert set(first) == {"id", "tgl", "id_no", "acc_statutory", "acc_management", "job_name", "memo",
                          "debit", "credit", "debit_credit", "category_lk", "category_spt",
                          "pph_non_pph", "accrual_actual"}
    assert svc.load_lines("smt", 2024) == [] and svc.load_lines("etf", 2026) == []
