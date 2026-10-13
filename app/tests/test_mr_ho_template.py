import importlib.util
import os
import re

from modules.management_report.ho_template import load_template

SCRIPT = os.path.join(os.path.dirname(__file__), "..", "scripts", "extract_ho_template.py")


def _rows(tpl):
    return [r for s in tpl["sections"] for r in s["rows"]]


def test_three_sections_and_190_unique_accounts():
    tpl = load_template()
    assert [s["key"] for s in tpl["sections"]] == ["capex", "opex", "summary"]
    accounts = [r for r in _rows(tpl) if r["type"] == "account"]
    assert len(accounts) == 190
    assert len({a["code"] for a in accounts}) == 190
    assert tpl["org"] == "President Office & ETF"
    assert tpl["location"].startswith("Head Office")


def test_row_ids_are_unique_and_every_reference_resolves():
    rows = _rows(load_template())
    ids = [r["id"] for r in rows]
    assert len(ids) == len(set(ids))
    by_id = {r["id"]: r for r in rows}
    for r in rows:
        if r["type"] == "total":
            assert r["of"], r["id"]
            for i in r["of"]:
                assert by_id[i]["type"] in ("account", "total"), (r["id"], i)


def test_known_rows_match_the_excel_sheet():
    by_id = {r["id"]: r for r in _rows(load_template())}
    assert by_id[124]["code"] == "70105120"
    assert by_id[124]["label"] == "Equipment Rent Expense - 3rd Party"
    assert by_id[43]["label"] == "Total Capex" and len(by_id[43]["of"]) == 6
    assert by_id[263]["label"] == "Grand Total included Depreciation" and len(by_id[263]["of"]) == 20
    assert by_id[281]["label"] == "Rent, Tax, and License Expense" and by_id[281]["of"] == [137]
    assert by_id[298]["label"] == "Total" and len(by_id[298]["of"]) == 22


def test_sections_end_with_their_grand_total_and_summary_title_has_no_year():
    tpl = load_template()
    last_total = {s["key"]: [r for r in s["rows"] if r["type"] == "total"][-1]["id"]
                  for s in tpl["sections"]}
    assert last_total == {"capex": 43, "opex": 263, "summary": 298}
    assert not re.search(r"\d{4}", tpl["sections"][2]["title"])


def test_account_notes_are_kept():
    notes = {r["code"] for r in _rows(load_template()) if r["type"] == "account" and r.get("note")}
    assert notes == {"70004113", "701193100", "701078002", "701078003"}


def test_formula_reference_parser():
    spec = importlib.util.spec_from_file_location("extract_ho_template", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    kinds = {r: "account" for r in list(range(72, 84)) + list(range(100, 105))}
    assert mod._refs("=SUM(D72:D83,D100:D104)", kinds) == list(range(72, 84)) + list(range(100, 105))
    assert mod._refs("=D70+D107", {70: "total", 107: "total"}) == [70, 107]
    assert mod._refs("=SUM(D1:D3)", {2: "group"}) == []
