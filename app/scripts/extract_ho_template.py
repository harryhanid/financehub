"""Extract the layout of sheet 'BGT HO Report per CC' into ho_template.json.

Run on the master workbook whenever the HO template in Excel changes
(for example a new GL account):

    python scripts/extract_ho_template.py "C:\\path\\Management Report - MASTER.xlsb"

Excel (desktop) must be installed: formulas cannot be read from .xlsb otherwise.
The workbook is copied first and opened read-only with macros disabled; nothing is saved.
"""
import json
import os
import re
import shutil
import sys
import tempfile

import win32com.client

SHEET = "BGT HO Report per CC"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                   "modules", "management_report", "ho_template.json")

# Row bounds of the three blocks in the Excel sheet (1-based, inclusive).
SECTIONS = [
    {"key": "capex", "title_row": 5, "first": 8, "last": 43},
    {"key": "opex", "title_row": 51, "first": 54, "last": 263},
    {"key": "summary", "title_row": 271, "first": 275, "last": 298},
]
_REF = re.compile(r"\$?D\$?(\d+)(?::\$?D\$?(\d+))?")


def _text(v):
    return "" if v is None else str(v).strip()


def _code(v):
    if isinstance(v, (int, float)) and float(v).is_integer():
        return str(int(v))
    return None


def _refs(formula: str, row_kinds: dict) -> list:
    """Row numbers a '=SUM(D72:D83,D100:D104)' / '=D70+D107' formula adds up.

    Ranges are expanded to the rows that carry a value (account/total rows)."""
    out = []
    for m in _REF.finditer(formula):
        lo, hi = int(m.group(1)), int(m.group(2) or m.group(1))
        out.extend(r for r in range(lo, hi + 1) if row_kinds.get(r) in ("account", "total"))
    return out


def extract(path: str) -> dict:
    xl = win32com.client.DispatchEx("Excel.Application")
    xl.Visible = False
    xl.DisplayAlerts = False
    xl.EnableEvents = False
    xl.AutomationSecurity = 3                      # msoAutomationSecurityForceDisable
    wb = xl.Workbooks.Open(os.path.abspath(path), 0, True)
    try:
        ws = wb.Worksheets.Item(SHEET)
        cell = lambda r, c: ws.Cells(r, c)
        out = {"org": _text(cell(1, 1).Value2), "location": _text(cell(2, 1).Value2),
               "sections": []}
        for sec in SECTIONS:
            rows, kinds = [], {}
            for r in range(sec["first"], sec["last"] + 1):
                a, b = cell(r, 1).Value2, cell(r, 2).Value2
                formula = _text(cell(r, 4).Formula)
                note = _text(cell(r, 7).Value2) or None
                if sec["key"] == "summary":
                    if formula.startswith("="):
                        kinds[r] = "total"
                        rows.append({"id": r, "type": "total", "nomor": _text(a),
                                     "label": _text(b), "formula": formula})
                    continue
                if _code(a) and formula.upper().startswith("=XLOOKUP("):
                    kinds[r] = "account"
                    rows.append({"id": r, "type": "account", "code": _code(a),
                                 "label": _text(b), "note": note})
                elif _text(a) and formula.startswith("="):
                    kinds[r] = "total"
                    rows.append({"id": r, "type": "total", "label": _text(a), "formula": formula})
                elif _text(a):
                    rows.append({"id": r, "type": "group", "label": _text(a)})
            out["sections"].append({"key": sec["key"],
                                    "title": _text(cell(sec["title_row"], 1).Value2),
                                    "rows": rows, "_kinds": kinds})
        # Summary rows refer to rows of the opex block: resolve once all blocks are known.
        all_kinds = {}
        for s in out["sections"]:
            all_kinds.update(s["_kinds"])
        for s in out["sections"]:
            for row in s["rows"]:
                if row["type"] == "total":
                    row["of"] = _refs(row.pop("formula"), all_kinds)
            del s["_kinds"]
        # Excel hard-codes a year in the summary title; Flow renders the data year instead.
        for s in out["sections"]:
            if s["key"] == "summary":
                s["title"] = re.sub(r"^Budget\s+\d{4}\s*-\s*", "", s["title"])
        return out
    finally:
        wb.Close(False)
        xl.Quit()


def main(argv):
    if len(argv) != 2:
        sys.exit(__doc__)
    tmp = os.path.join(tempfile.mkdtemp(), "master_copy.xlsb")
    shutil.copyfile(argv[1], tmp)                  # never touch the original while Excel has it
    data = extract(tmp)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    n_acc = sum(1 for s in data["sections"] for r in s["rows"] if r["type"] == "account")
    print(f"wrote {os.path.normpath(OUT)}: {n_acc} accounts")


if __name__ == "__main__":
    main(sys.argv)
