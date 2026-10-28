import re

with open('C:/Financehub/app/modules/beasiswa/service.py', 'r', encoding='utf-8') as f:
    content = f.read()

# I need to insert *angkatan_params,  right after *jenjang_params,  inside the query parameters.
# The parameters arrays are like: [..., *jenjang_params, ...] or [..., *jenjang_params]
content = content.replace('*jenjang_params,', '*jenjang_params, *angkatan_params,')
content = content.replace('*jenjang_params]', '*jenjang_params, *angkatan_params]')

with open('C:/Financehub/app/modules/beasiswa/service.py', 'w', encoding='utf-8') as f:
    f.write(content)
