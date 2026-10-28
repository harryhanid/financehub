import re

with open('C:/Financehub/app/templates/beasiswa/approval.html', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    "ctx.current_role in ['BC', 'Admin', 'admin']",
    "(ctx.current_role in ['BC', 'Admin', 'admin'] or ctx.current_user == 'admin')"
)

with open('C:/Financehub/app/templates/beasiswa/approval.html', 'w', encoding='utf-8') as f:
    f.write(content)
