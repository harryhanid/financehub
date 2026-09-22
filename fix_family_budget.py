import re

file_path = "C:/Financehub/app/modules/sahabat_etf/service.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target = r'if nama in by_nama:\s*by_nama\[nama\]\["realisasi"\] \+= row\["realisasi_total"\]\s*by_nama\[nama\]\["_kategori_set"\] \|= cats\s*else:\s*member = \{"nama": nama, "realisasi": row\["realisasi_total"\], "_kategori_set": set\(cats\)\}\s*by_nama\[nama\] = member\s*members\.append\(member\)'
replacement = """if nama in by_nama:
                by_nama[nama]["realisasi"] += row["realisasi_total"]
                by_nama[nama]["budget"] += row["budget_total"]
                by_nama[nama]["_kategori_set"] |= cats
            else:
                member = {"nama": nama, "realisasi": row["realisasi_total"], "budget": row["budget_total"], "_kategori_set": set(cats)}
                by_nama[nama] = member
                members.append(member)"""
content = re.sub(target, replacement, content)

target2 = r'"total_realisasi": sum\(m\["realisasi"\] for m in members\),'
replacement2 = """"total_realisasi": sum(m["realisasi"] for m in members),
            "total_budget": sum(m["budget"] for m in members),"""
content = re.sub(target2, replacement2, content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
