"""General Ledger MR: group MR rows into the report layout and the flat data table.

Pure functions over the row dicts produced by mr_rows.build_mr_rows.
"""
from modules.management_report.combine_rows import UNMAPPED


def list_ccs(rows) -> list:
    return sorted({r["cc"] for r in rows if r["cc"]})


def _category_order(category):
    return (category == UNMAPPED, category)           # unmapped always last


def _clean(v):
    return round(v, 6) + 0.0                          # + 0.0 turns -0.0 into 0.0


def _metrics(bgt, pta, act) -> dict:
    """Per-line figures of the sheet Report: available = BGT + PTA, diff = ACT - available."""
    bgt, pta, act = _clean(bgt), _clean(pta), _clean(act)
    available = _clean(bgt + pta)
    diff = _clean(act - available)
    pct = _clean(diff / available * 100) if available else None       # blank, never divide by zero
    return {"bgt": bgt, "pta": pta, "available": available, "act": act, "diff": diff, "pct": pct}


def build_report(rows, cc=None) -> dict:
    selected = [r for r in rows if not cc or r["cc"] == cc]
    cats = {}
    for r in selected:
        key = (r["custom"], r["mm1"], r["description"], r["activity"])
        lines = cats.setdefault(r["category"], {})
        acc = lines.setdefault(key, [0.0, 0.0, 0.0])
        acc[0] += r.get("bgt") or 0.0
        acc[1] += r.get("pta") or 0.0
        acc[2] += r["act"]
    groups, tot = [], [0.0, 0.0, 0.0]
    for category in sorted(cats, key=_category_order):
        lines, gsum = [], [0.0, 0.0, 0.0]
        for k, v in sorted(cats[category].items(), key=lambda kv: (kv[0][1], kv[0][2], kv[0][3])):
            lines.append({"custom": k[0], "mm1": k[1], "description": k[2], "activity": k[3],
                          **_metrics(*v)})
            gsum = [a + b for a, b in zip(gsum, v)]
        groups.append({"category": category, "lines": lines, **_metrics(*gsum),
                       "total": _clean(gsum[2])})
        tot = [a + b for a, b in zip(tot, gsum)]
    return {"has_data": bool(groups), "cc": cc, "groups": groups, "grand": _metrics(*tot)}


def query_data(rows, q=None, cc=None, page=1, per_page=100) -> dict:
    needle = (q or "").strip().lower()
    selected = [r for r in rows
                if (not cc or r["cc"] == cc)
                and (not needle or needle in r["description"].lower() or needle in r["cc"].lower()
                     or needle in r["activity"].lower() or needle in r["coa"].lower()
                     or needle in r["id_no"].lower() or needle in r["new_code"].lower()
                     or needle in r["allocation_memo"].lower())]            # keeps build order (GL SMT, then ETF)
    total = len(selected)
    pages = max(1, -(-total // per_page))
    page = min(max(1, page), pages)
    return {"rows": selected[(page - 1) * per_page: page * per_page], "total": total,
            "sum_act": round(sum(r["act"] for r in selected), 6) + 0.0,
            "page": page, "pages": pages, "per_page": per_page}
