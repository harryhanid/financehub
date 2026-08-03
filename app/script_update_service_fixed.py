path = r"C:\Financehub\app\modules\sponsorship\service.py"
with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Find get_dashboard_data
start_idx = -1
for i, line in enumerate(lines):
    if line.startswith("def get_dashboard_data("):
        start_idx = i
        break

end_idx = -1
for i in range(start_idx + 1, len(lines)):
    if lines[i].startswith("def "):
        end_idx = i
        break

new_func = """def get_dashboard_data(company_id: int, filters: dict = None) -> dict:
    rows = list_transaksi(company_id, filters)

    total_amount = sum(r["amount_request"] for r in rows)
    total_count = len(rows)

    monthly = {}
    for r in rows:
        month = r["tanggal_form_sponsor"][:7]  # 'YYYY-MM'
        monthly[month] = monthly.get(month, 0) + r["amount_request"]
    monthly_chart = [{"month": m, "amount": monthly[m]} for m in sorted(monthly)]

    pillar_totals = {p: 0.0 for p in config.SPONSORSHIP_PILLARS}
    for r in rows:
        if r["cat3"] in pillar_totals:
            pillar_totals[r["cat3"]] += r["amount_request"]
    pillar_chart = [{"pillar": p, "amount": pillar_totals[p]} for p in config.SPONSORSHIP_PILLARS]

    desc_totals = {d: 0.0 for d in config.SPONSORSHIP_DESCRIPTION}
    for r in rows:
        if r["description"] in desc_totals:
            desc_totals[r["description"]] += r["amount_request"]
    description_chart = [{"description": d, "amount": desc_totals[d]} for d in config.SPONSORSHIP_DESCRIPTION]
    
    # New aggregations for the complex dashboard summaries
    desc_pillar_table = []
    desc_year_table = []
    year_pillar_chart = {}
    
    years_set = set()
    for r in rows:
        y = r["tanggal_form_sponsor"][:4]
        if y: years_set.add(y)
    sorted_years = sorted(list(years_set))
    
    for d in config.SPONSORSHIP_DESCRIPTION:
        # Desc vs Pillar
        dp_row = {"description": d, "total": 0.0}
        for p in config.SPONSORSHIP_PILLARS: dp_row[p] = 0.0
        
        # Desc vs Year
        dy_row = {"description": d, "total": 0.0}
        for y in sorted_years: dy_row[y] = 0.0
        
        for r in rows:
            if r["description"] == d:
                amt = r["amount_request"]
                
                # Pillar
                p = r["cat3"]
                if p in config.SPONSORSHIP_PILLARS:
                    dp_row[p] += amt
                dp_row["total"] += amt
                
                # Year
                y = r["tanggal_form_sponsor"][:4]
                if y in sorted_years:
                    dy_row[y] += amt
                dy_row["total"] += amt
                
        desc_pillar_table.append(dp_row)
        desc_year_table.append(dy_row)
        
    for r in rows:
        y = r["tanggal_form_sponsor"][:4]
        p = r["cat3"]
        if y and p in config.SPONSORSHIP_PILLARS:
            if y not in year_pillar_chart:
                year_pillar_chart[y] = {pil: 0.0 for pil in config.SPONSORSHIP_PILLARS}
            year_pillar_chart[y][p] += r["amount_request"]

    # Pillar summary table
    pillar_summary_table = []
    for p in config.SPONSORSHIP_PILLARS:
        amt = pillar_totals[p]
        pct = (amt / total_amount * 100) if total_amount > 0 else 0
        pillar_summary_table.append({"pillar": p, "amount": amt, "pct": pct})
    pillar_summary_table.append({"pillar": "Grand Total", "amount": total_amount, "pct": 100 if total_amount > 0 else 0})

    return {
        "summary": {"total_amount": total_amount, "total_count": total_count},
        "monthlyChart": monthly_chart,
        "pillarChart": pillar_chart,
        "descriptionChart": description_chart,
        "descPillarTable": desc_pillar_table,
        "descYearTable": desc_year_table,
        "yearPillarChart": year_pillar_chart,
        "pillarSummaryTable": pillar_summary_table,
        "sortedYears": sorted_years
    }

"""

lines[start_idx:end_idx] = [new_func + "\n"]

with open(path, "w", encoding="utf-8") as f:
    f.writelines(lines)

print("done")
