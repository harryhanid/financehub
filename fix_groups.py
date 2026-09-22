import re

file_path = "C:/Financehub/app/modules/sahabat_etf/service.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target1 = r'    groups_order = list\(FAMILY_GROUPS\)\n    for r in siswa_rows:\n        code = r\["siswa_code"\]\n        if code not in code_to_family:\n            groups_order\.append\(\(code, \[code\]\)\)'
replacement1 = """    groups_order = list(FAMILY_GROUPS)
    non_group_codes = []
    for r in siswa_rows:
        code = r["siswa_code"]
        if code not in code_to_family:
            non_group_codes.append(code)
    
    if non_group_codes:
        groups_order.append(("non_group", non_group_codes))"""
content = re.sub(target1, replacement1, content)

target2 = r'    family_counter = 0\n    for f in families:\n        if len\(f\["members"\]\) > 1:\n            family_counter \+= 1\n            f\["label"\] = f"Sahabat \{family_counter\}"\n        else:\n            f\["label"\] = f\["members"\]\[0\]\["nama"\]'
replacement2 = """    family_counter = 0
    for f in families:
        if f["family_key"] == "non_group":
            f["label"] = "Non Group"
        elif f["family_key"].startswith("fam") or len(f["members"]) > 1:
            family_counter += 1
            f["label"] = f"Sahabat {family_counter}"
        else:
            f["label"] = f["members"][0]["nama"]"""
content = re.sub(target2, replacement2, content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
