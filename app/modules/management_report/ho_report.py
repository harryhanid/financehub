"""Management Report: HO Report (sheet 'BGT HO Report per CC') computed from the active snapshot."""
from modules.management_report import service
from modules.management_report.ho_template import load_template

_ZERO = (0.0, 0.0, 0.0)
_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def period_label(period_iso) -> str:
    try:
        month = int(str(period_iso)[5:7])
    except (TypeError, ValueError):
        return ""
    return f"s/d {_MONTHS[month - 1]}" if 1 <= month <= 12 else ""


def _accounts_under(row_id, by_id) -> set:
    row = by_id[row_id]
    if row["type"] == "account":
        return {row_id}
    out = set()
    for i in row["of"]:
        out |= _accounts_under(i, by_id)
    return out


def _nonzero(values) -> bool:
    return any(abs(v) > 1e-9 for v in values)


def compute_ho(tpl: dict, agg: dict) -> dict:
    """Fill the template with amounts (x1000, Rp 000) from agg = {coa: (bgt, pta, act)}."""
    by_id = {r["id"]: r for s in tpl["sections"] for r in s["rows"]}
    sections, vals = [], {}
    for s in tpl["sections"]:
        totals = [r["id"] for r in s["rows"] if r["type"] == "total"]
        grand_id = totals[-1] if totals else None
        rows = []
        for r in s["rows"]:
            row = dict(r)
            row.pop("of", None)
            if r["type"] == "account":
                a = agg.get(r["code"], _ZERO)
                vals[r["id"]] = [a[0] * 1000, a[1] * 1000, a[2] * 1000]
            elif r["type"] == "total":
                vals[r["id"]] = [sum(vals[i][k] for i in r["of"]) for k in range(3)]
                row["grand"] = r["id"] == grand_id
            if r["id"] in vals:
                row["bgt"], row["pta"], row["act"] = (round(v, 3) for v in vals[r["id"]])
            rows.append(row)
        sections.append({"key": s["key"], "title": s["title"], "rows": rows, "grand_id": grand_id})

    grand = {s["key"]: s["grand_id"] for s in sections}
    counted = _accounts_under(grand["capex"], by_id) | _accounts_under(grand["opex"], by_id)
    in_summary = _accounts_under(grand["summary"], by_id)
    counted_codes = {by_id[i]["code"] for i in counted}

    unmapped = []                                   # data that no grand total contains
    for coa in sorted(agg):
        a = agg[coa]
        if coa not in counted_codes and _nonzero(a):
            label = next((r["label"] for r in by_id.values()
                          if r["type"] == "account" and r["code"] == coa), None)
            unmapped.append({"coa": coa, "label": label, "bgt": round(a[0] * 1000, 3),
                             "pta": round(a[1] * 1000, 3), "act": round(a[2] * 1000, 3)})

    summary_missing = []                            # in the Opex grand total, in no summary line
    for i in sorted(_accounts_under(grand["opex"], by_id) - in_summary,
                    key=lambda i: by_id[i]["code"]):
        v = vals[i]
        if _nonzero(v):
            summary_missing.append({"coa": by_id[i]["code"], "label": by_id[i]["label"],
                                    "bgt": round(v[0], 3), "pta": round(v[1], 3),
                                    "act": round(v[2], 3)})
    return {"sections": sections, "unmapped": unmapped, "summary_missing": summary_missing}


def _full_year(yy):
    if yy is None:
        return None
    return yy + 2000 if yy < 100 else yy


def build_ho_report(company_id: int, cc=None, yy=None, mm=None, coas=None, cats=None) -> dict:
    """HO Report for the active snapshot; cc=None means All Cost Center. COA and Category filters apply as on the Report tab."""
    tpl = load_template()
    agg = service.aggregate_by_coa(company_id, cc, yy, mm, coas, cats)
    meta = service.get_active_meta(company_id)
    out = compute_ho(tpl, agg)
    year = _full_year(yy)
    if year is None:
        yys = service.get_filter_options(company_id)["yys"]
        year = _full_year(max(yys)) if yys else None
    if year:
        for s in out["sections"]:
            if s["key"] == "summary":
                s["title"] = f"Budget {year} - {s['title']}"
    out.update({
        "has_data": bool(agg),
        "org": tpl["org"],
        "location": tpl["location"],
        "cc": cc,
        "division": "All" if cc is None else meta["cc_names"].get(cc, cc),
        "period_label": period_label(meta.get("period")),
        "year": year,
        "period": meta.get("period"),
    })
    return out
