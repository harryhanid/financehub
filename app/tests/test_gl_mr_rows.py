# tests/test_gl_mr_rows.py
import pytest

from modules.general_ledger import mr_rows as mr
from modules.general_ledger import service as svc
from tests.test_gl_sync import mkrow

CMAP = {("SMT", "6-1810"): ("70108100", "10 - Office Supplies And Equipment Expense"),
        ("ETF", "6-2190"): ("70119100", "20 - Others"),
        ("SMT", "6-1111"): ("70100000", "")}


def g(acc="6-1810", tgl="2026-01-15", memo="Zoom", amount=-957910.0, job="POITEC",
      activity="SMT - IT"):
    return {"acc_management": acc, "tgl": tgl, "allocation_memo": memo,
            "budget_activity": activity, "job_name": job, "debit_credit": amount}


def build(smt=(), etf=()):
    return mr.build_mr_rows({"SMT": list(smt), "ETF": list(etf)}, CMAP)


def test_row_fields_follow_the_macro_and_gl_combine_mapping():
    res = build(smt=[g()])
    assert res.skipped_date == 0
    assert res.rows == [{
        "coa": "70108100", "mm": 1, "yy": 2026, "cc": "POITEC",
        "category": "10 - Office Supplies And Equipment Expense", "activity": "SMT - IT",
        "description": "- Act 2026 : Zoom Month : 1", "custom": "3", "mm1": 1,
        "pta": 0.0, "bgt": 0.0, "act": -1.0, "source": "SMT", "account": "6-1810",
        "unmapped": False}]


def test_only_accounts_starting_6_to_9_with_a_nonzero_amount_are_kept():
    smt = [g("1-1160"), g("2-1110"), g("6-1810"), g("7-1000"), g("8-1000"), g("9-1000"),
           g(""), g(None), g("6-1810", amount=0.0), g("6-1810", amount=None)]
    res = build(smt=smt)
    assert [r["account"] for r in res.rows] == ["6-1810", "7-1000", "8-1000", "9-1000"]


def test_etf_rows_use_the_etf_column_of_the_mapping():
    res = build(etf=[g("6-2190", amount=30000.0)])
    assert res.rows[0]["coa"] == "70119100" and res.rows[0]["source"] == "ETF"
    assert res.rows[0]["category"] == "20 - Others"
    smt_side = build(smt=[g("6-2190", amount=30000.0)])       # ETF-only account seen from SMT
    assert smt_side.rows[0]["unmapped"] is True


@pytest.mark.parametrize("amount,expected", [
    (957910.0, 1.0), (-957910.0, -1.0), (50000.0, 0.0), (-50000.0, 0.0), (150000.0, 0.2),
    (250000.0, 0.2), (350000.0, 0.4), (-250000.0, -0.2), (3250000.0, 3.2), (49999.0, 0.0),
    (51000.0, 0.1), (2450000.0000000005, 2.4), (-95818918.0, -95.8), (1500000000.0, 1500.0)])
def test_append1_rounding_half_to_even(amount, expected):
    assert mr.excel_round_mio(amount) == expected


def test_rounding_never_returns_negative_zero():
    assert str(mr.excel_round_mio(-49999.0)) == "0.0"
    assert str(mr.excel_round_mio(-50000.0)) == "0.0"


def test_unmapped_account_is_kept_and_summarised():
    res = build(smt=[g("6-9999", amount=2000000.0), g("6-9999", amount=1000000.0), g()])
    unmapped = [r for r in res.rows if r["unmapped"]]
    assert {r["category"] for r in unmapped} == {mr.UNMAPPED}
    assert all(r["coa"] == "" for r in unmapped)
    assert mr.unmapped_summary(res.rows) == [
        {"source": "SMT", "account": "6-9999", "rows": 2, "act": 3.0}]


def test_mapping_without_category_counts_as_unmapped_but_keeps_coa():
    res = build(smt=[g("6-1111", amount=1000000.0)])
    assert res.rows[0]["coa"] == "70100000"
    assert res.rows[0]["category"] == mr.UNMAPPED and res.rows[0]["unmapped"] is True


def test_rows_with_invalid_date_are_skipped_and_counted():
    res = build(smt=[g(tgl=None), g(tgl="garbage"), g(tgl="2026-02-03")])
    assert len(res.rows) == 1 and res.skipped_date == 2


def mrow(yy, mm):
    return build(smt=[g(tgl=f"{yy}-{mm:02d}-10")]).rows[0]


def test_period_options_and_cumulative_cutoff():
    rows = [mrow(2025, 12), mrow(2026, 1), mrow(2026, 2), mrow(2026, 3)]
    assert mr.period_options(rows) == {"yys": [2025, 2026], "months": {2025: [12], 2026: [1, 2, 3]}}
    assert [(r["yy"], r["mm"]) for r in mr.apply_cutoff(rows, 2026, 2)] == [(2026, 1), (2026, 2)]
    assert mr.apply_cutoff(rows, 2026, 12) == rows[1:]
    assert mr.apply_cutoff(rows, 1999, 12) == []
    assert mr.period_options([]) == {"yys": [], "months": {}}


def test_load_mr_source_returns_only_amount_rows_with_needed_columns():
    log = dict(synced_by="u", filename="f", content_hash="h", rows_before=0, rows_after=2,
               total_debit=0, total_credit=0, dropped=0, summary={})
    svc.replace_all("smt", [
        mkrow(acc_management="6-1810", debit_credit=5.0, allocation_memo="m",
              budget_activity="b", job_name="J"),
        mkrow(id_no="Z", debit_credit=0.0)], log)
    rows = svc.load_mr_source("smt")
    assert rows == [{"acc_management": "6-1810", "tgl": "2026-01-02", "allocation_memo": "m",
                     "budget_activity": "b", "job_name": "J", "debit_credit": 5.0}]
    assert svc.load_mr_source("etf") == []
