import re

with open('C:/Financehub/app/modules/beasiswa/routes.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add get_distinct_angkatan to import
content = content.replace("get_distinct_universitas", "get_distinct_universitas, get_distinct_angkatan")

# Add to render_template
content = content.replace(
    "universitas_list=get_distinct_universitas(_cid()) if not wrong_company else [],",
    "universitas_list=get_distinct_universitas(_cid()) if not wrong_company else [],\n        angkatan_list=get_distinct_angkatan(_cid()) if not wrong_company else [],"
)

with open('C:/Financehub/app/modules/beasiswa/routes.py', 'w', encoding='utf-8') as f:
    f.write(content)
