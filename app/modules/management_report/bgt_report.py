"""Management Report: data of sheet 'BGT Report per CC' (OPEX/CAPEX -> category -> Append lines)."""
import calendar
import re
from datetime import date

_PREFIX = re.compile(r"^\s*\d+\s*-\s*")
_KINDS = (("Bgt", "bgt", "d"), ("Pta", "pta", "f"), ("Act", "act", "i"))


def clean_category(name) -> str:
    return _PREFIX.sub("", name or "").strip() or "(no category)"


def month_of(row):
    return row.get("mm1") or row.get("mm") or None


def _full_year(yy):
    if yy is None:
        return None
    return yy + 2000 if yy < 100 else yy


def pick_year(rows, yy):
    if yy is not None:
        return yy
    years = [r["yy"] for r in rows if r.get("yy") is not None]
    return max(years) if years else None


def pick_period(rows, year, mm, meta_period) -> int:
    """mm filter, else the snapshot's report period (same year), else the latest month with ACT, else 12."""
    if mm is not None and 1 <= int(mm) <= 12:
        return int(mm)
    if meta_period and year is not None:
        try:
            y, m = int(str(meta_period)[:4]), int(str(meta_period)[5:7])
        except ValueError:
            y = m = 0
        if y == _full_year(year) and 1 <= m <= 12:
            return m
    months = [month_of(r) for r in rows
              if r.get("yy") == year and (r.get("act") or 0) != 0 and month_of(r)]
    return max(months) if months else 12


def _metrics(d, e, f, i) -> dict:
    g = e + f
    j = i - g
    m = d - i
    return {"d": d, "e": e, "f": f, "g": g, "i": i, "j": j,
            "k": j / g if g else None, "m": m, "n": m / d if d else None}


def _sum(items) -> dict:
    t = {k: 0.0 for k in "defi"}
    for it in items:
        for k in t:
            t[k] += it[k] or 0
    return _metrics(t["d"], t["e"], t["f"], t["i"])


def _details(rows, year4, period):
    out = []
    for kind_no, (kind, field, col) in enumerate(_KINDS):
        for r in sorted(rows, key=lambda r: (str(r.get("coa") or ""), month_of(r) or 0,
                                             (r.get("description") or "").lower())):
            amount = r.get(field) or 0
            if amount == 0:
                continue
            month = month_of(r)
            within = month is None or month <= period
            desc = (r.get("description") or "").strip()
            if re.match(rf"^-\s*{kind}\b", desc, re.I):
                text = desc                              # the Append text already reads '- Bgt 2026 : ... Month : n'
            else:
                text = f"- {kind} {year4 or ''} : {desc}"
                if r.get("mm1"):
                    text += f" Month : {r['mm1']}"
            d = {"coa": r.get("coa"), "text": text, "d": None, "e": None, "f": None, "i": None}
            d[col] = amount if (col == "d" or within) else 0.0
            if col == "d":
                d["e"] = amount if within else 0.0
            out.append((kind_no, d))
    return [d for _, d in out]


def build_bgt_report(rows, yy=None, mm=None, meta_period=None) -> dict:
    empty = {"has_data": False, "year": None, "year4": None, "period": None,
             "period_date": None, "levels": []}
    year = pick_year(rows, yy)
    rows = [r for r in rows if year is None or r.get("yy") == year]
    if not rows:
        return empty
    period = pick_period(rows, year, mm, meta_period)
    year4 = _full_year(year)

    by_level = {"OPEX": {}, "CAPEX": {}}
    for r in sorted(rows, key=lambda r: str(r.get("category") or "").lower()):
        level = "CAPEX" if str(r.get("coa") or "").startswith("27") else "OPEX"
        by_level[level].setdefault(r.get("category") or "", []).append(r)

    levels = []
    for label in ("OPEX", "CAPEX"):
        cats = []
        for category, cat_rows in by_level[label].items():
            details = _details(cat_rows, year4, period)
            cats.append({"label": clean_category(category), "m": _sum(details), "details": details})
        if cats:
            levels.append({"label": label, "m": _sum(c["m"] for c in cats), "categories": cats})
    last_day = calendar.monthrange(year4, period)[1] if year4 else None
    return {"has_data": True, "year": year, "year4": year4, "period": period,
            "period_date": date(year4, period, last_day) if year4 else None, "levels": levels}
