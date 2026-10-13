"""Management Report: filtering and paging of the GL Combine / Append1 rows (pure functions)."""

SOURCES = ("SMT", "ETF", "Sponsor")
_SEARCH_KEYS = ("description", "cc", "activity", "coa", "id_no", "new_code", "allocation_memo")


def list_ccs(rows) -> list:
    return sorted({r["cc"] for r in rows if r["cc"]})


def filter_source(rows, source) -> list:
    return [r for r in rows if r["source"] == source] if source in SOURCES else list(rows)


def query_data(rows, q=None, cc=None, source=None, page=1, per_page=100) -> dict:
    """Filter, then page. The order of `rows` (the build order) is kept: New Code runs in that order."""
    needle = (q or "").strip().lower()
    selected = [r for r in filter_source(rows, source)
                if (not cc or r["cc"] == cc)
                and (not needle or any(needle in str(r.get(k) or "").lower() for k in _SEARCH_KEYS))]
    total = len(selected)
    pages = max(1, -(-total // per_page))
    page = min(max(1, page), pages)
    return {"rows": selected[(page - 1) * per_page: page * per_page], "total": total,
            "sum_act": round(sum(r["act"] for r in selected), 6) + 0.0,
            "sum_dc": round(sum(r["debit_credit"] for r in selected), 2) + 0.0,
            "page": page, "pages": pages, "per_page": per_page}
