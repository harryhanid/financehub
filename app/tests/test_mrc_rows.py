# tests/test_gl_mr_rows.py
import pytest

from modules.management_report import combine_rows as mr
from modules.general_ledger import service as svc
from tests.test_gl_sync import mkrow

CMAP = {("SMT", "6-1810"): ("70108100", "10 - Office Supplies And Equipment Expense", "-10-"),
        ("ETF", "6-2190"): ("70119100", "20 - Others", "-20-"),
        ("SMT", "6-1111"): ("70100000", "", "")}


CCMAP = {"POITEC": {"total": "$POITEC", "seq": 16, "description": "IT"},
         "POCFAD": {"total": "$POCFAD", "seq": 3, "description": "Fin"},
         "PULPP": {"total": "", "seq": 0, "description": "PULP & PAPER"}}


def g(acc="6-1810", tgl="2026-01-15", memo="Zoom", amount=-957910.0, job="POITEC",
      activity="SMT - IT", id_no="GJ-1"):
    return {"id_no": id_no, "acc_management": acc, "tgl": tgl, "allocation_memo": memo,
            "budget_activity": activity, "job_name": job, "debit_credit": amount}


def build(smt=(), etf=()):
    return mr.build_combine_rows({"SMT": list(smt), "ETF": list(etf)}, CMAP, CCMAP)


def test_row_fields_follow_the_macro_and_gl_combine_mapping():
    res = build(smt=[g()])
    assert res.skipped_date == 0
    assert res.rows == [{
        "coa": "70108100", "mm": 1, "yy": 2026, "cc": "POITEC",
        "category": "10 - Office Supplies And Equipment Expense", "activity": "SMT - IT",
        "description": "- Act 2026 : Zoom Month : 1", "custom": "3", "mm1": 1,
        "pta": 0.0, "bgt": 0.0, "act": -1.0, "source": "SMT", "account": "6-1810",
        "unmapped": False,
        "id_no": "GJ-1", "tgl": "2026-01-15", "allocation_memo": "Zoom", "debit_credit": -957910.0,
        "cost_center2": "$POITEC", "cc0": "26", "cc1": 16, "bc1": "-10-",
        "new_code": "A26-16-10-1", "cc_unmapped": False}]


def test_old_two_tuple_map_values_still_work():
    res = mr.build_combine_rows({"SMT": [g()], "ETF": []},
                           {("SMT", "6-1810"): ("70108100", "10 - Office")})
    assert res.rows[0]["coa"] == "70108100" and res.rows[0]["category"] == "10 - Office"


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
    assert rows == [{"id_no": "GJ-1", "acc_management": "6-1810", "tgl": "2026-01-02", "allocation_memo": "m",
                     "budget_activity": "b", "job_name": "J", "debit_credit": 5.0}]
    assert svc.load_mr_source("etf") == []


def test_new_code_running_number_per_group_smt_before_etf():
    res = build(smt=[g(), g(job="POCFAD"), g(), g(acc="6-1111", amount=5e6)],
                etf=[g(acc="6-2190", amount=3e4), g()])     # ETF 6-1810 is unmapped there -> bc1 ""
    codes = [(r["source"], r["cc1"], r["bc1"], r["new_code"]) for r in res.rows]
    assert codes == [("SMT", 16, "-10-", "A26-16-10-1"),
                     ("SMT", 3, "-10-", "A26-3-10-1"),          # other group restarts at 1
                     ("SMT", 16, "-10-", "A26-16-10-2"),        # unaffected by the other group's row
                     ("SMT", 16, "", "A26-161"),                # same cc, empty code is its own group
                     ("ETF", 16, "-20-", "A26-16-20-1"),
                     ("ETF", 16, "", "A26-162")]


def test_new_code_year_is_part_of_the_group():
    res = build(smt=[g(tgl="2025-12-01"), g(tgl="2026-01-01"), g(tgl="2025-12-02")])
    assert [(r["cc0"], r["new_code"]) for r in res.rows] == [
        ("25", "A25-16-10-1"), ("26", "A26-16-10-1"), ("25", "A25-16-10-2")]


def test_new_fields_from_the_source_row():
    r = build(smt=[g(id_no=" GJ-9 ", memo=" Zoom  x ")]).rows[0]
    assert (r["id_no"], r["allocation_memo"], r["tgl"], r["debit_credit"]) == (
        "GJ-9", " Zoom  x ", "2026-01-15", -957910.0)


def test_cost_center_absent_or_empty_total_is_unmapped():
    res = build(smt=[g(job="NOPE"), g(job="PULPP"), g()])
    absent, pulpp, ok = res.rows
    for r in (absent, pulpp):
        assert (r["cost_center2"], r["cc1"], r["cc_unmapped"]) == ("", 0, True)
    assert absent["new_code"] == "A26-0-10-1"
    assert pulpp["new_code"] == "A26-0-10-2"
    assert (ok["cost_center2"], ok["cc1"], ok["cc_unmapped"]) == ("$POITEC", 16, False)


def test_cc_map_is_optional():
    res = mr.build_combine_rows({"SMT": [g()], "ETF": []}, CMAP)
    r = res.rows[0]
    assert (r["cost_center2"], r["cc1"], r["cc_unmapped"], r["new_code"]) == ("", 0, True, "A26-0-10-1")


def test_numbering_is_independent_of_the_cutoff():
    res = build(smt=[g(tgl="2026-01-10"), g(tgl="2026-02-10"), g(tgl="2026-03-10")])
    cut = mr.apply_cutoff(res.rows, 2026, 2)
    assert [r["new_code"] for r in cut] == ["A26-16-10-1", "A26-16-10-2"]
    late = mr.apply_cutoff(build(smt=[g(tgl="2025-12-10"), g(tgl="2026-02-10")]).rows, 2026, 2)
    assert late[0]["new_code"] == "A26-16-10-1"
    # the second row of a group keeps its number even when the first row is cut away
    res2 = build(smt=[g(tgl="2026-03-10"), g(tgl="2026-01-10")])
    assert [r["new_code"] for r in mr.apply_cutoff(res2.rows, 2026, 1)] == ["A26-16-10-2"]


def test_unmapped_cc_summary():
    res = build(smt=[g(job="ZZZ"), g(job="PULPP"), g(job="ZZZ"), g(), g(job="AAA")])
    assert mr.unmapped_cc_summary(res.rows) == [
        {"cc": "AAA", "rows": 1}, {"cc": "PULPP", "rows": 1}, {"cc": "ZZZ", "rows": 2}]
    assert mr.unmapped_cc_summary(build(smt=[g()]).rows) == []


SP = {"tgl": "2026-01-19", "perihal": "Prasasti Membership", "amount": 500000000.0,
      "coa": "701078002", "cc": "POSPON"}
CCMAP_SP = {"POSPON": {"total": "$POCCOM", "seq": 5, "description": "SMT - Sponshorship"}}


def build_all(smt=(), etf=(), sponsor=(), cc_map=None):
    return mr.build_combine_rows({"SMT": list(smt), "ETF": list(etf), "Sponsor": list(sponsor)},
                                 CMAP, CCMAP_SP if cc_map is None else cc_map)


def test_sponsor_row_follows_the_workbook_format():
    res = build_all(sponsor=[SP])
    assert res.skipped_date == 0
    assert res.rows == [{
        "coa": "701078002", "mm": 1, "yy": 2026, "cc": "POSPON", "category": "",
        "activity": "", "description": "- Act 2026 : Prasasti Membership Month : 1",
        "custom": "3", "mm1": 1, "pta": 0.0, "bgt": 0.0, "act": 500.0, "source": "Sponsor",
        "account": "701078002", "unmapped": False, "id_no": "", "tgl": "2026-01-19",
        "allocation_memo": "Prasasti Membership", "debit_credit": 500000000.0,
        "cost_center2": "$POCCOM", "cc0": "26", "cc1": 5, "bc1": "", "new_code": "A26-51",
        "cc_unmapped": False}]


def test_sponsor_new_codes_count_per_year_and_after_gl_rows():
    rows = build_all(
        smt=[g(tgl="2026-01-15")],
        sponsor=[dict(SP, tgl="2026-01-19"), dict(SP, tgl="2026-02-01"), dict(SP, tgl="2027-01-02")]).rows
    assert rows[0]["source"] == "SMT" and rows[0]["new_code"].endswith("-1")
    assert [(r["source"], r["new_code"]) for r in rows[1:]] == [
        ("Sponsor", "A26-51"), ("Sponsor", "A26-52"), ("Sponsor", "A27-51")]


def test_gl_rows_do_not_disturb_sponsor_numbering():
    only = build_all(sponsor=[SP, dict(SP, tgl="2026-03-01")]).rows
    mixed = build_all(smt=[g(), g()], etf=[g("6-2190", amount=30000.0)],
                      sponsor=[SP, dict(SP, tgl="2026-03-01")]).rows
    assert [r["new_code"] for r in only] == ["A26-51", "A26-52"]
    assert [r["new_code"] for r in mixed if r["source"] == "Sponsor"] == ["A26-51", "A26-52"]


def test_sponsor_cost_center_uses_the_cc_mapping_and_flags_when_missing():
    res = build_all(sponsor=[SP], cc_map={})
    assert res.rows[0]["cost_center2"] == "" and res.rows[0]["cc1"] == 0
    assert res.rows[0]["cc_unmapped"] is True


def test_sponsor_blank_coa_and_cc_fall_back_to_config():
    res = build_all(sponsor=[dict(SP, coa="", cc="")])
    assert res.rows[0]["coa"] == "701078002" and res.rows[0]["cc"] == "POSPON"


def test_sponsor_rows_with_invalid_date_are_skipped_and_counted():
    res = build_all(sponsor=[dict(SP, tgl=None), dict(SP, tgl="garbage"), SP])
    assert len(res.rows) == 1 and res.skipped_date == 2


def test_sponsor_empty_perihal_and_zero_amount_are_kept():
    res = build_all(sponsor=[dict(SP, perihal="", amount=0.0)])
    assert res.rows[0]["description"] == "- Act 2026 :  Month : 1" and res.rows[0]["act"] == 0.0
