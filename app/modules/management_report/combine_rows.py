"""Management Report GL Combine: build Append1-format rows from GL SMT, GL ETF and Sponsorship rows.

Mirrors the 'TransferDataGLCombineFinalFix' macro and the GL Combine sheet of
Management Report - MASTER.xlsb. Pure functions: no database access.
"""
from collections import namedtuple
from datetime import date
from decimal import Decimal, ROUND_HALF_EVEN

import config

UNMAPPED = "(Belum dipetakan)"
_MIO = Decimal(1000000)
_TENTH = Decimal("0.1")
_ELIGIBLE_PREFIX = "6789"

MrBuild = namedtuple("MrBuild", "rows skipped_date")


def excel_round_mio(amount) -> float:
    """(Debit - Credit) in rupiah -> Rp Mio, 1 decimal, ties to even like Append1.

    Normalised to 15 significant digits first, like Excel, so float noise cannot break a tie.
    """
    d = Decimal(format(float(amount), ".15g")) / _MIO
    return float(d.quantize(_TENTH, rounding=ROUND_HALF_EVEN)) + 0.0      # + 0.0 turns -0.0 into 0.0


def _parse_date(value):
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def build_combine_rows(source_rows: dict, coa_map: dict, cc_map: dict = None) -> MrBuild:
    """Rows in GL Combine / Append1 shape from GL SMT, GL ETF and Sponsorship (in that order).
    `new_code` numbers run per (cc0, cc1, bc1) over ALL built rows, so apply any filter afterwards."""
    cc_map = cc_map or {}
    rows, skipped = [], 0
    counters = {}
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
            coa, category, *rest = coa_map.get((source, account), ("", ""))
            bc1 = rest[0] if rest else ""
            memo = r.get("allocation_memo") or ""
            cc = str(r.get("job_name") or "").strip()
            cc_entry = cc_map.get(cc) or {}
            seq = int(cc_entry.get("seq") or 0)
            total = cc_entry.get("total") or ""
            cc0 = f"{d.year % 100:02d}"
            group = (cc0, seq, bc1)
            counters[group] = counters.get(group, 0) + 1
            rows.append({
                "coa": coa, "mm": d.month, "yy": d.year,
                "cc": cc,
                "category": category or UNMAPPED,
                "activity": str(r.get("budget_activity") or "").strip(),
                "description": f"- Act {d.year} : {memo} Month : {d.month}",
                "custom": "3", "mm1": d.month, "pta": 0.0, "bgt": 0.0,
                "act": excel_round_mio(amount), "source": source, "account": account,
                "unmapped": not category,
                "id_no": str(r.get("id_no") or "").strip(), "tgl": d.isoformat(),
                "allocation_memo": memo, "debit_credit": float(amount),
                "cost_center2": total, "cc0": cc0, "cc1": seq, "bc1": bc1,
                "new_code": f"A{cc0}-{seq}{bc1}{counters[group]}",
                "cc_unmapped": not total,
            })

    for r in source_rows.get("Sponsor", []):
        d = _parse_date(r.get("tgl"))
        if d is None:
            skipped += 1
            continue
        amount = float(r.get("amount") or 0.0)
        coa = str(r.get("coa") or "").strip() or config.MR_SPONSOR_ACCOUNT
        cc = str(r.get("cc") or "").strip() or config.MR_SPONSOR_COST_CENTER
        memo = r.get("perihal") or ""
        cc_entry = cc_map.get(cc) or {}
        seq = int(cc_entry.get("seq") or 0)
        total = cc_entry.get("total") or ""
        cc0 = f"{d.year % 100:02d}"
        group = (cc0, seq, "")
        counters[group] = counters.get(group, 0) + 1
        rows.append({
            "coa": coa, "mm": d.month, "yy": d.year, "cc": cc, "category": "", "activity": "",
            "description": f"- Act {d.year} : {memo} Month : {d.month}",
            "custom": "3", "mm1": d.month, "pta": 0.0, "bgt": 0.0,
            "act": excel_round_mio(amount), "source": config.MR_SPONSOR_SOURCE, "account": coa,
            "unmapped": False, "id_no": "", "tgl": d.isoformat(), "allocation_memo": memo,
            "debit_credit": amount, "cost_center2": total, "cc0": cc0, "cc1": seq, "bc1": "",
            "new_code": f"A{cc0}-{seq}{counters[group]}", "cc_unmapped": not total,
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


def unmapped_cc_summary(rows) -> list:
    """Cost centres without a COST CENTER2 (absent from sheet CC or empty total), with their row counts."""
    out = {}
    for r in rows:
        if r["cc_unmapped"]:
            out[r["cc"]] = out.get(r["cc"], 0) + 1
    return [{"cc": cc, "rows": n} for cc, n in sorted(out.items())]


def period_options(rows) -> dict:
    months = {}
    for r in rows:
        months.setdefault(r["yy"], set()).add(r["mm"])
    return {"yys": sorted(months), "months": {y: sorted(m) for y, m in months.items()}}


def apply_cutoff(rows, yy, mm) -> list:
    """Cumulative cutoff: the selected year, January up to and including month `mm`."""
    return [r for r in rows if r["yy"] == yy and r["mm"] <= mm]
