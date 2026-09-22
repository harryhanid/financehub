with open('app/modules/sahabat_etf/service.py', 'r', encoding='utf-8') as f:
    c = f.read()

old_member_logic = """        for code in existing_codes:
            row = by_code[code]
            nama = row["nama"]
            cats = kategori_map.get(code, set())
            if nama in by_nama:
                by_nama[nama]["realisasi"] += row["realisasi_total"]
                by_nama[nama]["budget"] += row["budget_total"]
                by_nama[nama]["_kategori_set"] |= cats
            else:
                member = {"nama": nama, "realisasi": row["realisasi_total"], "budget": row["budget_total"], "_kategori_set": set(cats)}
                by_nama[nama] = member
                members.append(member)"""

new_member_logic = """        for code in existing_codes:
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
                members.append(member)"""

c = c.replace(old_member_logic, new_member_logic)
with open('app/modules/sahabat_etf/service.py', 'w', encoding='utf-8') as f:
    f.write(c)

print("service.py patched")
