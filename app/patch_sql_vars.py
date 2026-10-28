import re

with open('C:/Financehub/app/modules/beasiswa/service.py', 'r', encoding='utf-8') as f:
    content = f.read()

# I will find every jenjang_sql, jenjang_params = _jenjang_filter_sql(jenjangs, "s.jenjang")
# and safely append ngkatan_sql, angkatan_params = _angkatan_filter_sql(angkatans, "s.angkatan") right after it
# ONLY if it doesn't already have it.
content = re.sub(
    r'(jenjang_sql, jenjang_params = _jenjang_filter_sql\(jenjangs, "s\.jenjang"\))(?!\s*angkatan_sql)',
    r'\1\n    angkatan_sql, angkatan_params = _angkatan_filter_sql(angkatans, "s.angkatan")',
    content
)

with open('C:/Financehub/app/modules/beasiswa/service.py', 'w', encoding='utf-8') as f:
    f.write(content)
