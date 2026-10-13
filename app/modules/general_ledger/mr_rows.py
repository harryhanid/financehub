"""General Ledger MR: build Management Report (Append1 format) rows from GL SMT / GL ETF rows.

Mirrors the 'TransferDataGLCombineFinalFix' macro and the GL Combine sheet of
Management Report - MASTER.xlsb. Pure functions: no database access.
"""
from collections import namedtuple
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

UNMAPPED = "(Belum dipetakan)"
_MIO = Decimal(1000000)
_TENTH = Decimal("0.1")
_ELIGIBLE_PREFIX = "6789"

MrBuild = namedtuple("MrBuild", "rows skipped_date")


def excel_round_mio(amount) -> float:
    """(Debit - Credit) in rupiah -> Rp Mio, 1 decimal, ties away from zero like Excel's ROUND."""
    d = Decimal(str(float(amount))) / _MIO
    return float(d.quantize(_TENTH, rounding=ROUND_HALF_UP)) + 0.0      # + 0.0 turns -0.0 into 0.0


def _parse_date(value):
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def build_mr_rows(source_rows: dict, coa_map: dict) -> MrBuild:
    rows, skipped = [], 0
    for source in ("SMT", "ETF"):
        for r in source_rows.get(source, []):
            account = str(r.get("acc_management") or "").strip()
            amount = r.get("debit_credit") or 0.0
            if not account or account[0] not in _ELIGIBLE_PREFIX or not amount:
                continue
            d = _parse_date(r.get("tgl"))
            if d is None:
                skipped += 1
                continue
            coa, category = coa_map.get((source, account), ("", ""))
            memo = r.get("allocation_memo") or ""
            rows.append({
                "coa": coa, "mm": d.month, "yy": d.year,
                "cc": str(r.get("job_name") or "").strip(),
                "category": category or UNMAPPED,
                "activity": str(r.get("budget_activity") or "").strip(),
                "description": f"- Act {d.year} : {memo} Month : {d.month}",
                "custom": "3", "mm1": d.month, "pta": 0.0, "bgt": 0.0,
                "act": excel_round_mio(amount), "source": source, "account": account,
                "unmapped": not category,
            })
    return MrBuild(rows, skipped)


def unmapped_summary(rows) -> list:
    out = {}
    for r in rows:
        if r["unmapped"]:
            e = out.setdefault((r["source"], r["account"]),
                               {"source": r["source"], "account": r["account"], "rows": 0, "act": 0.0})
            e["rows"] += 1
            e["act"] = round(e["act"] + r["act"], 6)
    return sorted(out.values(), key=lambda e: (e["source"], e["account"]))


def period_options(rows) -> dict:
    months = {}
    for r in rows:
        months.setdefault(r["yy"], set()).add(r["mm"])
    return {"yys": sorted(months), "months": {y: sorted(m) for y, m in months.items()}}


def apply_cutoff(rows, yy, mm) -> list:
    """Cumulative cutoff: the selected year, January up to and including month `mm`."""
    return [r for r in rows if r["yy"] == yy and r["mm"] <= mm]
