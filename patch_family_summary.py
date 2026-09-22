import re

# 1. Update service.py
with open('app/modules/sahabat_etf/service.py', 'r', encoding='utf-8') as f:
    content = f.read()

start = content.find('def get_family_summary')
end = content.find('def get_kategori_breakdown', start)

new_func = """def get_family_summary(company_id: int, years: list = None, pillars: list = None) -> dict:
    conn = get_conn()
    budget_year_sql, budget_year_params = _year_filter_sql(years, "b.tanggal")
    payment_year_sql, payment_year_params = _year_filter_sql(years, "p.tanggal")
    pillar_sql, pillar_params = _pillar_filter_sql(pillars, "p.pillar")
    budget_pillar_sql, budget_pillar_params = _pillar_filter_sql(pillars, "b.pillar")

    budget_rows = conn.execute(
        f\"\"\"
        SELECT b.siswa_code, b.cat1, SUM(b.amount) AS total
        FROM budget_beasiswa b
        JOIN siswa s ON s.code = b.siswa_code AND s.company_id = b.company_id
        WHERE b.company_id = ? AND s.program = ?{budget_year_sql}{budget_pillar_sql}
        GROUP BY b.siswa_code, b.cat1
        \"\"\",
        [company_id, PROGRAM_NAME, *budget_year_params, *budget_pillar_params],
    ).fetchall()

    payment_rows = conn.execute(
        f\"\"\"
        SELECT p.siswa_code, p.cat1,
               SUM(CASE WHEN p.status = 'complete' THEN p.amount ELSE 0 END) AS realisasi
        FROM payment_beasiswa p
        JOIN siswa s ON s.code = p.siswa_code AND s.company_id = p.company_id
        WHERE p.company_id = ? AND s.program = ?{payment_year_sql}{pillar_sql}
        GROUP BY p.siswa_code, p.cat1
        \"\"\",
        [company_id, PROGRAM_NAME, *payment_year_params, *pillar_params],
    ).fetchall()
    conn.close()

    siswa_rows = get_siswa_summary(company_id, years, pillars)
    by_code = {r["siswa_code"]: r for r in siswa_rows}
    kategori_map = _siswa_kategori_map(company_id, years, pillars)

    code_to_family = {code: fk for fk, codes in FAMILY_GROUPS for code in codes}
    groups_order = list(FAMILY_GROUPS)
    non_group_codes = []
    for r in siswa_rows:
        code = r["siswa_code"]
        if code not in code_to_family:
            non_group_codes.append(code)
    
    if non_group_codes:
        groups_order.append(("non_group", non_group_codes))

    families = []
    family_idx = {}
    idx = 0
    for family_key, codes in groups_order:
        existing_codes = [c for c in codes if c in by_code]
        if not existing_codes:
            continue
        members = []
        by_nama = {}
        for code in existing_codes:
            row = by_code[code]
            nama = row["nama"]
            cats = kategori_map.get(code, set())
            realisasi_val = float(row["realisasi_total"] or 0)
            budget_val = float(row["budget_total"] or 0)
            if nama in by_nama:
                by_nama[nama]["realisasi"] += realisasi_val
                by_nama[nama]["budget"] += budget_val
                by_nama[nama]["_kategori_set"] |= cats
            else:
                member = {"nama": nama, "realisasi": realisasi_val, "budget": budget_val, "_kategori_set": set(cats)}
                by_nama[nama] = member
                members.append(member)
        for m in members:
            m["kategori"] = ", ".join(_sort_kategori(m.pop("_kategori_set")))
        families.append({
            "family_key": family_key,
            "members": members,
            "total_realisasi": sum(m["realisasi"] for m in members),
            "total_budget": sum(m["budget"] for m in members),
        })
        family_idx[family_key] = idx
        idx += 1

    for f in families:
        if f["family_key"] == "non_group":
            f["label"] = "Sahabat B.3.5"
        elif f["family_key"].startswith("Sahabat"):
            f["label"] = f["family_key"]
        else:
            f["label"] = f["members"][0]["nama"]

    final_families = [
        {
            "family_key":      f["family_key"],
            "label":           f["label"],
            "total_realisasi": f["total_realisasi"],
            "total_budget": f.get("total_budget", 0),
            "members":         f["members"],
        }
        for f in families
    ]

    kategori_data = {}
    for r in budget_rows:
        cat1 = r["cat1"] or "(Tanpa Kategori)"
        code = r["siswa_code"]
        fk = code_to_family.get(code, "non_group")
        if fk in family_idx:
            kategori_data.setdefault(cat1, {"budget": [0]*len(families), "realisasi": [0]*len(families)})
            kategori_data[cat1]["budget"][family_idx[fk]] += float(r["total"] or 0)

    for r in payment_rows:
        cat1 = r["cat1"] or "(Tanpa Kategori)"
        code = r["siswa_code"]
        fk = code_to_family.get(code, "non_group")
        if fk in family_idx:
            kategori_data.setdefault(cat1, {"budget": [0]*len(families), "realisasi": [0]*len(families)})
            kategori_data[cat1]["realisasi"][family_idx[fk]] += float(r["realisasi"] or 0)

    kategori_series = []
    for cat1 in _sort_kategori(kategori_data.keys()):
        kategori_series.append({
            "name": cat1,
            "budget": kategori_data[cat1]["budget"],
            "realisasi": kategori_data[cat1]["realisasi"]
        })

    return {
        "families": final_families,
        "kategori_series": kategori_series
    }

"""

new_content = content[:start] + new_func + content[end:]
with open('app/modules/sahabat_etf/service.py', 'w', encoding='utf-8') as f:
    f.write(new_content)


# 2. Update routes.py
with open('app/modules/sahabat_etf/routes.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('return jsonify({"families": get_family_summary(_cid(), years, pillars)})', 'return jsonify(get_family_summary(_cid(), years, pillars))')

with open('app/modules/sahabat_etf/routes.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Patch successful!")
