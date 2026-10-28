import re

with open('C:/Financehub/app/modules/beasiswa/routes.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the duplicate angkatans_str blocks
content = re.sub(r'(angkatans_str = request\.args\.get\("angkatans", ""\)\n\s*angkatans = \[a for a in angkatans_str\.split\(","\) if a\]\n\s*)+', r'\1', content)

with open('C:/Financehub/app/modules/beasiswa/routes.py', 'w', encoding='utf-8') as f:
    f.write(content)
