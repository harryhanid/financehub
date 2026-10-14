# modules/spt_badan/income_statement.py
"""SPT Badan: commercial income statement from classified lines (pure functions)."""
HPP = "HARGA POKOK PENJUALAN"
OPEX = "Beban Operasional"
TAX = "Income Tax Expense"
NO_SPT_LABEL = "(tanpa Category SPT)"


def aggregate(lines):
    """Net debit_credit per Category LK and per (Category LK, Category SPT); unclassified lines are skipped."""
    totals, spt_totals = {}, {}
    for line in lines:
        lk = line["category_lk"]
        if not lk:
            continue
        amount = line["debit_credit"] or 0.0
        totals[lk] = totals.get(lk, 0.0) + amount
        key = (lk, line["category_spt"] or "")
        spt_totals[key] = spt_totals.get(key, 0.0) + amount
    return totals, spt_totals


def _row(key, label, amount, kind, cats=None, spt=None):
    return {"key": key, "label": label, "amount": amount, "kind": kind, "cats": cats, "spt": spt}


def _sub_rows(prefix, cats, spt_totals, sign):
    by_spt = {}
    for (lk, spt), value in spt_totals.items():
        if lk in cats:
            by_spt[spt] = by_spt.get(spt, 0.0) + sign * value
    return [_row(f"{prefix}:{spt}", spt or NO_SPT_LABEL, amount, "sub", list(cats), spt)
            for spt, amount in sorted(by_spt.items(), key=lambda kv: (-kv[1], kv[0]))]


def build_income_statement(totals, spt_totals, lk_list):
    pnl = {name: meta for name, meta in lk_list.items() if meta["statement"] == "laba_rugi"}
    net = lambda names: sum(totals.get(n, 0.0) for n in names)           # noqa: E731
    revenue_cats = [n for n, m in pnl.items() if m["kind"] == "pendapatan"]
    opex_cats = [n for n, m in pnl.items() if m["kind"] == "beban" and n not in (HPP, TAX)]
    other_cats = [n for n, m in pnl.items() if m["kind"] == "lainnya"]
    hpp_cats = [HPP] if HPP in pnl else []
    tax_cats = [TAX] if TAX in pnl else []

    revenue = -net(revenue_cats)
    hpp = net(hpp_cats)
    gross = revenue - hpp
    opex = net(opex_cats)
    operating = gross - opex
    other_rows = [(n, -totals.get(n, 0.0)) for n in other_cats]
    other = sum(v for _, v in other_rows)
    pbt = operating + other
    tax = net(tax_cats)

    rows = [_row("revenue", "Pendapatan bersih", revenue, "item", revenue_cats),
            _row("hpp", "Harga pokok penjualan", hpp, "item", hpp_cats),
            *_sub_rows("hpp", hpp_cats, spt_totals, 1),
            _row("gross", "Laba kotor", gross, "subtotal"),
            _row("opex", "Biaya operasional", opex, "item", opex_cats),
            *_sub_rows("opex", opex_cats, spt_totals, 1),
            _row("operating", "Laba operasional", operating, "subtotal")]
    for name, value in other_rows:
        rows.append(_row(f"other:{name}", pnl[name]["label"] or name, value, "item", [name]))
        rows.extend(_sub_rows(f"other:{name}", [name], spt_totals, -1))
    rows += [_row("pbt", "Laba sebelum pajak penghasilan", pbt, "subtotal"),
             _row("tax", "Income tax expense", tax, "item", tax_cats),
             _row("net", "Laba (rugi) bersih", pbt - tax, "subtotal")]
    summary = {"revenue": revenue, "hpp": hpp, "gross": gross, "opex": opex, "operating": operating,
               "other": other, "pbt": pbt, "tax": tax, "net": pbt - tax}
    return {"rows": rows, "summary": summary}
