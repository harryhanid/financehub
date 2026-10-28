import re

with open('C:/Financehub/app/modules/beasiswa/routes.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('universitas_list=get_distinct_universitas, get_distinct_angkatan(_cid()) if not wrong_company else [],', 'universitas_list=get_distinct_universitas(_cid()) if not wrong_company else [],')

with open('C:/Financehub/app/modules/beasiswa/routes.py', 'w', encoding='utf-8') as f:
    f.write(content)
