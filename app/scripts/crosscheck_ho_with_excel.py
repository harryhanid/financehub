"""Compare Flow's HO Report with Excel's own sheet 'BGT HO Report per CC' for chosen cost centers.

    python scripts/crosscheck_ho_with_excel.py "C:\\path\\Management Report - MASTER.xlsb" POCFAD POOFFM TFEDIR

Excel drives its CC slicer on a copy of the workbook; nothing is saved. Prints one line per CC.
"""
import collections
import io
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import win32com.client                                             # noqa: E402

from modules.management_report.ho_report import compute_ho        # noqa: E402
from modules.management_report.ho_template import load_template   # noqa: E402
from modules.management_report.parser import read_append1         # noqa: E402


def flow_values(rows, cc):
    agg = collections.defaultdict(lambda: [0.0, 0.0, 0.0])
    for r in rows:
        if cc is None or r["cc"] == cc:
            a = agg[r["coa"]]
            a[0] += r["bgt"]
            a[1] += r["pta"]
            a[2] += r["act"]
    out = compute_ho(load_template(), dict(agg))
    return {r["id"]: (r["bgt"], r["pta"], r["act"])
            for s in out["sections"] for r in s["rows"] if "bgt" in r}


def main(argv):
    if len(argv) < 3:
        sys.exit(__doc__)
    master, ccs = argv[1], argv[2:]
    tmp = os.path.join(tempfile.mkdtemp(), "m.xlsb")
    shutil.copyfile(master, tmp)
    with open(tmp, "rb") as f:
        rows = read_append1(io.BytesIO(f.read())).rows
    xl = win32com.client.DispatchEx("Excel.Application")
    xl.Visible = False
    xl.DisplayAlerts = False
    xl.EnableEvents = False
    xl.AutomationSecurity = 3
    wb = xl.Workbooks.Open(tmp, 0, True)
    bad_total = 0
    try:
        ws = wb.Worksheets.Item("BGT HO Report per CC")
        slicer = wb.SlicerCaches.Item("Slicer_CC")
        for cc in ccs:
            slicer.VisibleSlicerItemsList = [f"[Append1__2].[CC].&[{cc}]"]
            xl.Calculate()
            flow = flow_values(rows, cc)
            bad = []
            for rid, vals in flow.items():
                excel = [float(ws.Cells(rid, col).Value2 or 0) for col in (4, 5, 6)]
                if any(abs(a - b) > 1e-3 for a, b in zip(vals, excel)):
                    bad.append((rid, vals, excel))
            bad_total += len(bad)
            print(f"{cc}: {len(flow)} rows compared, {len(bad)} mismatches")
            for rid, vals, excel in bad[:5]:
                print("   row", rid, "flow", vals, "excel", excel)
    finally:
        wb.Close(False)
        xl.Quit()
    sys.exit(1 if bad_total else 0)


if __name__ == "__main__":
    main(sys.argv)
