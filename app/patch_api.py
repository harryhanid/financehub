import re

with open('C:/Financehub/app/modules/beasiswa/api.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = re.sub(
    r'add_budget_batch\(cid, body\["siswa_code"\], body\["tanggal"\], body\["pillar"\], items\)',
    r'add_budget_batch(cid, body["siswa_code"], body["tanggal"], body["pillar"], items, get_jwt().get("username", "API"))',
    content
)

with open('C:/Financehub/app/modules/beasiswa/api.py', 'w', encoding='utf-8') as f:
    f.write(content)
