import re

with open('C:/Financehub/app/modules/beasiswa/routes.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    '''programs_str = request.args.get("programs", "")
    jenjangs_str = request.args.get("jenjangs", "")
    jenjangs = [j for j in jenjangs_str.split(",") if j]''',
    '''programs_str = request.args.get("programs", "")
    programs = [p for p in programs_str.split(",") if p]
    jenjangs_str = request.args.get("jenjangs", "")
    jenjangs = [j for j in jenjangs_str.split(",") if j]'''
)

with open('C:/Financehub/app/modules/beasiswa/routes.py', 'w', encoding='utf-8') as f:
    f.write(content)
