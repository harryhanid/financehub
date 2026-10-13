"""General Ledger MR: group MR rows into the report layout and the flat data table.

Pure functions over the row dicts produced by mr_rows.build_mr_rows.
"""
from modules.general_ledger.mr_rows import UNMAPPED


def list_ccs(rows) -> list:
    return sorted({r["cc"] for r in rows if r["cc"]})


def _category_order(category):
    return (category == UNMAPPED, category)           # unmapped always last


def build_report(rows, cc=None) -> dict:
    selected = [r for r in rows if not cc or r["cc"] == cc]
    cats = {}
    for r in selected:
        key = (r["custom"], r["mm1"], r["description"], r["activity"])
        lines = cats.setdefault(r["category"], {})
        lines[key] = lines.get(key, 0.0) + r["act"]
    groups = []
    for category in sorted(cats, key=_category_order):
        lines = [{"custom": k[0], "mm1": k[1], "description": k[2], "activity": k[3],
                  "act": round(v, 6) + 0.0} for k, v in sorted(cats[category].items(),
                                                          key=lambda kv: (kv[0][1], kv[0][2], kv[0][3]))]
        groups.append({"category": category, "lines": lines,
                       "total": round(sum(l["act"] for l in lines), 6) + 0.0})
    return {"has_data": bool(groups), "cc": cc, "groups": groups,
            "grand": round(sum(g["total"] for g in groups), 6) + 0.0}


def query_data(rows, q=None, cc=None, page=1, per_page=100) -> dict:
    needle = (q or "").strip().lower()
    selected = [r for r in rows
                if (not cc or r["cc"] == cc)
                and (not needle or needle in r["description"].lower() or needle in r["cc"].lower()
                     or needle in r["activity"].lower() or needle in r["coa"].lower())]
    selected.sort(key=lambda r: (r["mm"], r["source"], r["cc"], r["description"]))
    total = len(selected)
    pages = max(1, -(-total // per_page))
    page = min(max(1, page), pages)
    return {"rows": selected[(page - 1) * per_page: page * per_page], "total": total,
            "sum_act": round(sum(r["act"] for r in selected), 6) + 0.0,
            "page": page, "pages": pages, "per_page": per_page}
