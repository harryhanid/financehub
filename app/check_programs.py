import re

with open('C:/Financehub/app/modules/beasiswa/routes.py', 'r', encoding='utf-8') as f:
    content = f.read()

funcs = re.findall(r'(def api_dashboard_.*?\):.*?(?=def api_dashboard_|$))', content, flags=re.DOTALL)
for func in funcs:
    if 'programs = ' not in func:
        print(func.split(':')[0], "IS MISSING programs =")
